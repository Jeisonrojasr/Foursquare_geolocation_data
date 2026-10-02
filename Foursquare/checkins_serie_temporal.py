"""
Series temporales de CHECK-INS por lugar (venue) y por usuario.

Funciona con el dataset público de Yang et al. (Foursquare NYC / Tokio,
abril 2012 - febrero 2013), archivo dataset_TSMC2014_NYC.txt (TSV, sin cabecera):
  userId, venueId, venueCategoryId, venueCategory, lat, lon, tzOffsetMin, utcTimestamp

Uso:
    pip install pandas matplotlib
    python3 checkins_serie_temporal.py --archivo data/dataset_TSMC2014_NYC.txt
    python3 checkins_serie_temporal.py --archivo ... --venue 49bbd6c0f964a520f4531fe3
    python3 checkins_serie_temporal.py --archivo ... --usuario 479

Salidas: data/checkins/*.png y data/checkins/*.csv
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SALIDA = Path("data/checkins")
COLS = ["user_id", "venue_id", "cat_id", "categoria", "lat", "lon", "tz_min", "utc"]


def cargar(archivo: str) -> pd.DataFrame:
    df = pd.read_csv(archivo, sep="\t", header=None, names=COLS, encoding="latin-1")
    # Formato: "Tue Apr 03 18:00:09 +0000 2012"
    df["utc"] = pd.to_datetime(df["utc"], format="%a %b %d %H:%M:%S %z %Y", utc=True)
    # Hora local = UTC + desfase en minutos del lugar
    df["local"] = (df["utc"] + pd.to_timedelta(df["tz_min"], unit="m")).dt.tz_localize(None)
    return df


def guardar(nombre: str) -> None:
    plt.tight_layout()
    plt.savefig(SALIDA / nombre, dpi=150)
    plt.close()


def serie_global(df: pd.DataFrame) -> None:
    diario = df.set_index("local").resample("D").size().rename("checkins")
    diario.to_csv(SALIDA / "checkins_diario.csv")
    ax = diario.plot(figsize=(10, 4), title="Check-ins por día (todos los lugares)")
    ax.set_ylabel("Check-ins")
    guardar("global_diario.png")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4))
    df.groupby(df["local"].dt.hour).size().plot(kind="bar", ax=a1, title="Por hora local del día")
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    s = df.groupby(df["local"].dt.dayofweek).size()
    s.index = [dias[i] for i in s.index]
    s.plot(kind="bar", ax=a2, title="Por día de la semana")
    guardar("global_perfiles.png")


def serie_venues(df: pd.DataFrame, venue: str | None, top: int) -> None:
    ids = [venue] if venue else df["venue_id"].value_counts().head(top).index.tolist()
    sem = (df[df["venue_id"].isin(ids)].set_index("local")
           .groupby("venue_id").resample("W").size().unstack(0).fillna(0))
    # Etiqueta con la categoría del lugar
    etiqueta = df.drop_duplicates("venue_id").set_index("venue_id")["categoria"]
    sem.columns = [f"{c[:6]}… ({etiqueta.get(c, '?')})" for c in sem.columns]
    sem.to_csv(SALIDA / "checkins_venues_semanal.csv")
    ax = sem.plot(figsize=(10, 4.5), title="Check-ins semanales por lugar")
    ax.set_ylabel("Check-ins por semana")
    guardar("venues_semanal.png")


def serie_usuarios(df: pd.DataFrame, usuario: int | None, top: int) -> None:
    ids = [usuario] if usuario is not None else df["user_id"].value_counts().head(top).index.tolist()
    sem = (df[df["user_id"].isin(ids)].set_index("local")
           .groupby("user_id").resample("W").size().unstack(0).fillna(0))
    sem.columns = [f"usuario {c}" for c in sem.columns]
    sem.to_csv(SALIDA / "checkins_usuarios_semanal.csv")
    ax = sem.plot(figsize=(10, 4.5), title="Check-ins semanales por usuario")
    ax.set_ylabel("Check-ins por semana")
    guardar("usuarios_semanal.png")


def cruce_con_api(df: pd.DataFrame) -> None:
    """Cuántos venue_id del dataset aparecen en tu descarga de la API de Places."""
    csv = Path("data/lugares.csv")
    if not csv.exists():
        return
    api = set(pd.read_csv(csv)["id"].astype(str))
    en_ambos = api & set(df["venue_id"].astype(str))
    print(f"\nCruce con tu descarga de la API: {len(en_ambos)} de {len(api)} lugares "
          f"aparecen también en el dataset de check-ins.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivo", required=True)
    ap.add_argument("--venue", help="ID de un lugar concreto")
    ap.add_argument("--usuario", type=int, help="ID de un usuario concreto")
    ap.add_argument("--top", type=int, default=5, help="cuántos lugares/usuarios mostrar")
    a = ap.parse_args()

    SALIDA.mkdir(parents=True, exist_ok=True)
    df = cargar(a.archivo)
    print(f"{len(df)} check-ins, {df['user_id'].nunique()} usuarios, "
          f"{df['venue_id'].nunique()} lugares, "
          f"del {df['local'].min().date()} al {df['local'].max().date()}")
    serie_global(df)
    serie_venues(df, a.venue, a.top)
    serie_usuarios(df, a.usuario, a.top)
    cruce_con_api(df)
    print(f"\nFiguras y CSV en {SALIDA}/")
