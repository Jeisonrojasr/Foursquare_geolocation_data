"""
Paso 2: leer todos los JSON de data/raw/ y convertirlos en una tabla (DataFrame).
"""
import json
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")


def cargar_lugares() -> pd.DataFrame:
    filas = []
    for archivo in sorted(RAW.glob("*.json")):
        zona = archivo.stem.rsplit("_p", 1)[0]  # armenia_quindio_p01 -> armenia_quindio
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        for lugar in datos.get("results", []):
            filas.append(
                {
                    "zona": zona,
                    "id": lugar.get("fsq_place_id"),
                    "nombre": lugar.get("name"),
                    "lat": lugar.get("latitude"),
                    "lon": lugar.get("longitude"),
                    "distancia_m": lugar.get("distance"),
                    "categoria": (lugar.get("categories") or [{}])[0].get("name"),
                }
            )
    return pd.DataFrame(filas).drop_duplicates(subset="id")


if __name__ == "__main__":
    df = cargar_lugares()
    print(f"{len(df)} lugares únicos en {df['zona'].nunique()} zonas\n")
    print(df.head(10).to_string(index=False))
    print("\nCategorías más frecuentes:")
    print(df["categoria"].value_counts().head(10))
    df.to_csv("data/lugares.csv", index=False, encoding="utf-8")
