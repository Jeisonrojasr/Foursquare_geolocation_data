"""
Paso 1: descargar datos de Foursquare Places API y guardarlos como archivos JSON,
con control de consumo y con la FECHA de la descarga en el nombre del archivo.

Uso:
    export FSQ_API_KEY="tu_service_key"

    python3 descargar_foursquare.py --dry-run                  # zonas de ZONAS, sin llamadas
    python3 descargar_foursquare.py                            # descarga las zonas de ZONAS
    python3 descargar_foursquare.py --cuadricula 66 --dry-run  # calcula, sin llamadas
    python3 descargar_foursquare.py --cuadricula 66            # ~200 llamadas como máximo

--cuadricula N reparte N zonas en una malla sobre Nueva York (ignora ZONAS).
Si se interrumpe, vuelve a correr el mismo comando: se saltan las zonas que
ya se descargaron HOY y se continúa con las pendientes.

Archivos: data/raw/<zona>_<AAAA-MM-DD>_pNN.json
"""
import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = "https://places-api.foursquare.com/places/search"
API_VERSION = "2025-06-17"

# Zonas con nombre (se usan si NO pasas --cuadricula): nombre -> "lat,lon"
ZONAS = {
    "manhattan_sur": "40.7128,-74.0060",
    "midtown": "40.7549,-73.9840",
    "harlem": "40.8116,-73.9465",
    "brooklyn_centro": "40.6928,-73.9903",
    "williamsburg": "40.7081,-73.9571",
    "long_island_city": "40.7447,-73.9485",
}
# Rectángulo para --cuadricula: (lat_min, lat_max, lon_min, lon_max)
BBOX = (40.58, 40.88, -74.04, -73.78)

RADIO_M = 2000         # radio de búsqueda por zona
LIMITE = 50            # resultados por página
MAX_PAGINAS = 3        # tope de páginas (llamadas) por zona

# --- Control de consumo (tu cuenta mostraba 497 llamadas gratuitas restantes) ---
LIMITE_MENSUAL = 450
SALIDA = Path("data/raw")
CONTADOR = Path("data/contador_mensual.json")
LOG = Path("data/llamadas.log")

HOY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def generar_cuadricula(n: int) -> dict:
    """Reparte n puntos en BBOX, con celdas aproximadamente cuadradas."""
    lat_min, lat_max, lon_min, lon_max = BBOX
    alto = (lat_max - lat_min) * 111.0
    ancho = (lon_max - lon_min) * 111.0 * math.cos(math.radians((lat_min + lat_max) / 2))
    filas = max(1, round(math.sqrt(n * alto / ancho)))
    cols = max(1, math.ceil(n / filas))
    zonas = {}
    for i in range(filas):
        for j in range(cols):
            if len(zonas) >= n:
                return zonas
            lat = lat_min + (i + 0.5) * (lat_max - lat_min) / filas
            lon = lon_min + (j + 0.5) * (lon_max - lon_min) / cols
            zonas[f"cuad_{i:02d}_{j:02d}"] = f"{lat:.4f},{lon:.4f}"
    return zonas


def ya_descargada(nombre: str) -> bool:
    return (SALIDA / f"{nombre}_{HOY}_p01.json").exists()


def leer_contador() -> dict:
    return json.loads(CONTADOR.read_text()) if CONTADOR.exists() else {}


def llamadas_del_mes() -> int:
    return leer_contador().get(datetime.now(timezone.utc).strftime("%Y-%m"), 0)


def registrar_llamada(url: str, r: requests.Response) -> None:
    mes = datetime.now(timezone.utc).strftime("%Y-%m")
    c = leer_contador()
    c[mes] = c.get(mes, 0) + 1
    CONTADOR.write_text(json.dumps(c, indent=2))
    limites = {k: v for k, v in r.headers.items() if "ratelimit" in k.lower()}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {r.status_code} {url} {limites}\n")


def descargar_zona(nombre: str, ll: str, headers: dict) -> None:
    params = {"ll": ll, "radius": RADIO_M, "limit": LIMITE}
    url = BASE_URL
    for pagina in range(1, MAX_PAGINAS + 1):
        r = requests.get(url, headers=headers, params=params, timeout=30)
        registrar_llamada(url, r)
        r.raise_for_status()
        datos = r.json()

        archivo = SALIDA / f"{nombre}_{HOY}_p{pagina:02d}.json"
        archivo.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{archivo}  ({len(datos.get('results', []))} lugares) | llamadas este mes: {llamadas_del_mes()}")

        siguiente = r.links.get("next", {}).get("url")
        if not siguiente:
            break
        url, params = siguiente, None
        time.sleep(0.5)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo calcula el consumo máximo")
    ap.add_argument("--cuadricula", type=int, metavar="N",
                    help="usar una malla de N zonas sobre Nueva York en vez de ZONAS")
    args = ap.parse_args()

    zonas = generar_cuadricula(args.cuadricula) if args.cuadricula else ZONAS
    pendientes = {n: ll for n, ll in zonas.items() if not ya_descargada(n)}
    maximo = len(pendientes) * MAX_PAGINAS
    usadas = llamadas_del_mes()
    print(f"Zonas: {len(zonas)} ({len(zonas) - len(pendientes)} ya descargadas hoy, {len(pendientes)} pendientes)")
    print(f"Máximo de llamadas en esta ejecución: {maximo}")
    print(f"Ya usadas este mes (según tu contador): {usadas} | tope configurado: {LIMITE_MENSUAL}")

    if usadas + maximo > LIMITE_MENSUAL:
        raise SystemExit("Esta ejecución podría superar el tope. Reduce N, ZONAS o MAX_PAGINAS.")
    if args.dry_run:
        raise SystemExit("Dry-run: no se hizo ninguna llamada.")

    SALIDA.mkdir(parents=True, exist_ok=True)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {os.environ['FSQ_API_KEY']}",
        "X-Places-Api-Version": API_VERSION,
    }
    for nombre, ll in pendientes.items():
        # No empezar una zona si no caben todas sus páginas dentro del tope
        if llamadas_del_mes() + MAX_PAGINAS > LIMITE_MENSUAL:
            raise SystemExit(f"Tope mensual de {LIMITE_MENSUAL} llamadas cerca. Se detiene.")
        descargar_zona(nombre, ll, headers)
