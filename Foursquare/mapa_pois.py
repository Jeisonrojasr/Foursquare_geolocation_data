"""
Mapa interactivo de los POIs descargados (data/raw/*.json).

Uso:
    pip install folium pandas
    python3 mapa_pois.py                  # genera data/mapa_pois.html
    python3 mapa_pois.py --top 12         # más categorías con color propio
    python3 mapa_pois.py --agrupar        # agrupa puntos (útil con miles)

Abre data/mapa_pois.html con doble clic (se ve en el navegador; necesita internet
para cargar el mapa base). Si el mapa base muestra "Access blocked", es la política
de OpenStreetMap con archivos abiertos desde el disco: usa --base esri (por defecto). Cada categoría es una capa que puedes activar o
apagar en el control de arriba a la derecha. También hay una capa de calor.
"""
import argparse
import html
import json
from pathlib import Path

import folium
import pandas as pd
from folium.plugins import HeatMap, MarkerCluster

RAW = Path("data/raw")
SALIDA = Path("data/mapa_pois.html")
BASES = {
    "esri": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
             "Tiles &copy; Esri"),
    "gris": ("https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
             "Tiles &copy; Esri"),
}
PALETA = ["#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#008080",
          "#9a6324", "#f032e6", "#808000", "#000075", "#46c3c3", "#c4a000"]
GRIS = "#8a8a8a"


def cargar() -> pd.DataFrame:
    filas = []
    for archivo in sorted(RAW.glob("*.json")):
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        for l in datos.get("results", []):
            lat, lon = l.get("latitude"), l.get("longitude")
            if lat is None or lon is None:
                continue
            filas.append({
                "id": l.get("fsq_place_id"),
                "nombre": l.get("name") or "(sin nombre)",
                "categoria": (l.get("categories") or [{}])[0].get("name") or "Sin categoría",
                "lat": lat,
                "lon": lon,
            })
    return pd.DataFrame(filas).drop_duplicates("id")


def construir_mapa(df: pd.DataFrame, top: int, agrupar: bool, base: str) -> folium.Map:
    centro = [df["lat"].median(), df["lon"].median()]
    if base == "osm":
        m = folium.Map(location=centro, zoom_start=11, tiles="OpenStreetMap")
    else:
        url, attr = BASES[base]
        m = folium.Map(location=centro, zoom_start=11, tiles=None)
        folium.TileLayer(tiles=url, attr=attr, name="Mapa base").add_to(m)
    m.fit_bounds([[df["lat"].min(), df["lon"].min()], [df["lat"].max(), df["lon"].max()]])

    principales = df["categoria"].value_counts().head(top).index.tolist()
    colores = {c: PALETA[i % len(PALETA)] for i, c in enumerate(principales)}
    df = df.assign(grupo=df["categoria"].where(df["categoria"].isin(principales), "Otras categorías"))

    leyenda = []
    for grupo, sub in df.groupby("grupo"):
        color = colores.get(grupo, GRIS)
        fg = folium.FeatureGroup(name=f"{grupo} ({len(sub)})", show=True)
        destino = MarkerCluster().add_to(fg) if agrupar else fg
        for r in sub.itertuples():
            folium.CircleMarker(
                location=[r.lat, r.lon], radius=4, color=color, weight=1,
                fill=True, fill_color=color, fill_opacity=0.8,
                popup=folium.Popup(f"<b>{html.escape(r.nombre)}</b><br>{html.escape(r.categoria)}", max_width=250),
                tooltip=html.escape(r.nombre),
            ).add_to(destino)
        fg.add_to(m)
        leyenda.append(f'<span style="color:{color}">&#9679;</span> {html.escape(grupo)} ({len(sub)})')

    HeatMap(df[["lat", "lon"]].values.tolist(), name="Densidad (calor)", show=False, radius=12).add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    caja = ('<div style="position:fixed;bottom:20px;left:20px;z-index:9999;background:white;'
            'padding:8px 10px;border:1px solid #bbb;border-radius:6px;font:12px sans-serif;'
            f'max-height:40vh;overflow:auto"><b>{len(df)} POIs únicos</b><br>' + "<br>".join(leyenda) + "</div>")
    m.get_root().html.add_child(folium.Element(caja))
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10, help="categorías con color propio")
    ap.add_argument("--agrupar", action="store_true", help="agrupar marcadores cercanos")
    ap.add_argument("--base", choices=["esri", "gris", "osm"], default="esri",
                    help="mapa base: esri (calles), gris (fondo neutro) u osm (puede bloquear archivos locales)")
    a = ap.parse_args()

    df = cargar()
    if df.empty:
        raise SystemExit("No hay POIs en data/raw/. Corre primero descargar_foursquare.py")
    agrupar = a.agrupar or len(df) > 3000
    if agrupar and not a.agrupar:
        print("Más de 3000 puntos: se agrupan automáticamente para que el mapa sea fluido.")
    m = construir_mapa(df, a.top, agrupar, a.base)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    m.save(SALIDA)
    print(f"{len(df)} POIs únicos -> {SALIDA}")
