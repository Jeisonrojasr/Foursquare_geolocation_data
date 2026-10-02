"""
Orquestador: corre todo el proceso con UN comando, en el orden correcto.

Etapas (cada una es uno de tus scripts):
  1. descarga   descargar_foursquare.py      (SOLO si pasas --descargar; gasta cuota)
  2. tabla      leer_json_foursquare.py      -> data/lugares.csv
  3. serie      serie_temporal.py            -> data/figuras/, data/serie_snapshots.csv
  4. checkins   checkins_serie_temporal.py   -> data/checkins/   (si encuentra el dataset)
  5. mapa       mapa_pois.py                 -> data/mapa_pois.html

Uso:
    python3 ejecutar_pipeline.py                        # etapas 2-5 con los JSON que ya tienes (no gasta cuota)
    python3 ejecutar_pipeline.py --descargar --cuadricula 66 --dry-run   # solo calcula consumo y termina
    python3 ejecutar_pipeline.py --descargar --cuadricula 66             # descarga y luego corre todo
    python3 ejecutar_pipeline.py --saltar mapa,checkins                  # omite etapas
    python3 ejecutar_pipeline.py --checkins ruta/al/dataset.txt          # ruta explícita

Por seguridad, la descarga NUNCA se ejecuta si no la pides con --descargar.
Resumen y tiempos quedan en data/pipeline.log.
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
os.chdir(AQUI)  # los scripts usan rutas relativas (data/...)
RAW = Path("data/raw")
LOG = Path("data/pipeline.log")


def buscar_checkins(explicito: str | None) -> Path | None:
    if explicito:
        p = Path(explicito)
        return p if p.exists() else None
    for carpeta in (Path("data"), Path(".")):
        for p in sorted(carpeta.glob("dataset_TSMC2014_NYC*.txt")):
            return p
    return None


def correr(nombre: str, script: str, args: list[str]) -> tuple[str, str, float]:
    if not Path(script).exists():
        return nombre, f"OMITIDA (falta {script})", 0.0
    inicio = time.time()
    r = subprocess.run([sys.executable, script, *args])
    seg = time.time() - inicio
    return nombre, ("OK" if r.returncode == 0 else f"ERROR (código {r.returncode})"), seg


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--descargar", action="store_true", help="incluir la descarga desde la API (gasta cuota)")
    ap.add_argument("--cuadricula", type=int, metavar="N", help="con --descargar: usar malla de N zonas")
    ap.add_argument("--dry-run", action="store_true", help="con --descargar: solo calcula consumo y termina")
    ap.add_argument("--checkins", metavar="RUTA", help="ruta del dataset de check-ins (si no, se busca sola)")
    ap.add_argument("--saltar", default="", help="etapas a omitir, separadas por coma: descarga,tabla,serie,checkins,mapa")
    a = ap.parse_args()
    saltar = {s.strip() for s in a.saltar.split(",") if s.strip()}
    resumen: list[tuple[str, str, float]] = []

    # --- 1. Descarga (opt-in) ---
    if a.descargar and "descarga" not in saltar:
        if not a.dry_run and not os.environ.get("FSQ_API_KEY"):
            sys.exit('Falta la clave. Haz primero: export FSQ_API_KEY="TU_CLAVE"')
        args = []
        if a.cuadricula:
            args += ["--cuadricula", str(a.cuadricula)]
        if a.dry_run:
            args += ["--dry-run"]
        nombre, estado, seg = correr("descarga", "descargar_foursquare.py", args)
        resumen.append((nombre, estado, seg))
        if a.dry_run:
            # El script de descarga sale con código 1 a propósito en dry-run: no es un error.
            print("\nDry-run terminado. No se ejecutaron más etapas.")
            return
        if not estado.startswith("OK"):
            print("\nLa descarga falló: se detiene el proceso para no trabajar con datos incompletos.")
            sys.exit(1)

    # --- Etapas que necesitan JSON ---
    hay_json = RAW.exists() and any(RAW.glob("*.json"))
    for nombre, script in (("tabla", "leer_json_foursquare.py"), ("serie", "serie_temporal.py"), ("mapa", "mapa_pois.py")):
        if nombre in saltar:
            continue
        if not hay_json:
            resumen.append((nombre, "OMITIDA (no hay JSON en data/raw/; usa --descargar)", 0.0))
            continue
        Path("data").mkdir(exist_ok=True)
        print(f"\n=== Etapa: {nombre} ===")
        resumen.append(correr(nombre, script, []))

    # --- Check-ins (dataset público) ---
    if "checkins" not in saltar:
        ds = buscar_checkins(a.checkins)
        if ds is None:
            resumen.append(("checkins", "OMITIDA (no encontré dataset_TSMC2014_NYC*.txt en data/ ni en la carpeta)", 0.0))
        else:
            print(f"\n=== Etapa: checkins ({ds}) ===")
            resumen.append(correr("checkins", "checkins_serie_temporal.py", ["--archivo", str(ds)]))

    # --- Resumen ---
    lineas = [f"{datetime.now():%Y-%m-%d %H:%M:%S} — resumen del pipeline"]
    lineas += [f"  {n:<9} {e}" + (f"  ({s:.1f} s)" if s else "") for n, e, s in resumen]
    texto = "\n".join(lineas)
    print("\n" + texto)
    Path("data").mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(texto + "\n")
    if any(e.startswith("ERROR") for _, e, _ in resumen):
        sys.exit(1)


if __name__ == "__main__":
    main()
