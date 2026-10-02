"""
Paso 2: leer todos los JSON de data/raw/ y construir series temporales.

Uso:
    pip install pandas matplotlib
    python3 serie_temporal.py

Genera dos tipos de serie (según lo que haya en tus datos):

  A) Entre descargas ("snapshots"): cuántos lugares y de qué categorías hay en
     cada fecha de descarga. Necesita DOS o más descargas en días distintos.
  B) Dentro de una descarga: si los JSON traen campos de fecha por lugar
     (por ejemplo date_created, date_refreshed, date_closed), se grafica el
     crecimiento acumulado de lugares según esas fechas.

OJO con la interpretación de B: date_created es cuándo se registró el lugar
en la base de Foursquare, no cuándo abrió el negocio en la vida real.
Salidas: data/serie_snapshots.csv, data/figuras/*.png
"""
import json
import re
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # guarda PNG sin necesitar ventana gráfica
import matplotlib.pyplot as plt
import pandas as pd

RAW = Path("data/raw")
FIG = Path("data/figuras")
PATRON = re.compile(r"^(?P<zona>.+)_(?P<fecha>\d{4}-\d{2}-\d{2})_p\d+\.json$")


def zona_y_fecha(archivo: Path):
    m = PATRON.match(archivo.name)
    if m:
        return m["zona"], m["fecha"]
    # Archivos antiguos sin fecha en el nombre: usa la fecha de modificación
    zona = archivo.stem.rsplit("_p", 1)[0]
    fecha = datetime.fromtimestamp(archivo.stat().st_mtime).strftime("%Y-%m-%d")
    return zona, fecha


def cargar() -> pd.DataFrame:
    filas = []
    for archivo in sorted(RAW.glob("*.json")):
        zona, fecha = zona_y_fecha(archivo)
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        for lugar in datos.get("results", []):
            fila = {
                "snapshot": fecha,
                "zona": zona,
                "id": lugar.get("fsq_place_id"),
                "nombre": lugar.get("name"),
                "categoria": (lugar.get("categories") or [{}])[0].get("name"),
            }
            # Cualquier campo cuyo nombre contenga "date" (date_created, etc.)
            for k, v in lugar.items():
                if "date" in k.lower():
                    fila[k] = v
            filas.append(fila)
    return pd.DataFrame(filas)


def serie_snapshots(df: pd.DataFrame) -> None:
    por_fecha = df.groupby("snapshot")["id"].nunique().rename("lugares_unicos")
    por_fecha.to_csv("data/serie_snapshots.csv")
    print("\nA) Lugares únicos por fecha de descarga:")
    print(por_fecha.to_string())
    if len(por_fecha) < 2:
        print("   Solo hay UNA fecha de descarga: aún no hay serie entre descargas.")
        print("   Repite la descarga otro día para obtener más puntos.")
        return
    top = df["categoria"].value_counts().head(5).index
    tabla = (df[df["categoria"].isin(top)]
             .groupby(["snapshot", "categoria"])["id"].nunique().unstack(fill_value=0))
    ax = tabla.plot(marker="o", figsize=(9, 5), title="Lugares por categoría y fecha de descarga")
    ax.set_xlabel("Fecha de descarga")
    ax.set_ylabel("Lugares únicos")
    plt.tight_layout()
    plt.savefig(FIG / "serie_snapshots.png", dpi=150)
    plt.close()


def serie_fechas_internas(df: pd.DataFrame) -> None:
    cols = [c for c in df.columns if "date" in c.lower()]
    print("\nB) Campos de fecha encontrados en los JSON:", cols or "ninguno")
    if not cols:
        print("   La respuesta no incluye fechas por lugar; solo se puede usar la serie A.")
        return
    unicos = df.drop_duplicates("id")
    for col in cols:
        f = pd.to_datetime(unicos[col], errors="coerce", utc=True).dt.tz_localize(None).dropna()
        print(f"   {col}: {len(f)} de {len(unicos)} lugares tienen valor "
              f"({f.min().date() if len(f) else '-'} a {f.max().date() if len(f) else '-'})")
        if len(f) < 2:
            continue
        mensual = f.dt.to_period("M").value_counts().sort_index()
        acumulado = mensual.cumsum()
        acumulado.index = acumulado.index.to_timestamp()
        ax = acumulado.plot(figsize=(9, 5), title=f"Lugares acumulados según {col}")
        ax.set_xlabel("Fecha")
        ax.set_ylabel("Lugares acumulados")
        plt.tight_layout()
        plt.savefig(FIG / f"acumulado_{col}.png", dpi=150)
        plt.close()


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    df = cargar()
    if df.empty:
        raise SystemExit("No se encontraron JSON en data/raw/. Corre primero descargar_foursquare.py")
    print(f"{len(df)} filas, {df['id'].nunique()} lugares únicos, "
          f"{df['snapshot'].nunique()} fecha(s) de descarga, {df['zona'].nunique()} zona(s)")
    serie_snapshots(df)
    serie_fechas_internas(df)
    print(f"\nFiguras guardadas en {FIG}/")
