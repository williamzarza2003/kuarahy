"""Baja los HDRI de Poly Haven (CC0) que usa render.py. No se versionan porque pesan 8 MB.

Uso: py blender/descargar_assets.py
"""
import urllib.request
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
HDRIS = {
    "noon_grass_2k.hdr": "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/2k/noon_grass_2k.hdr",
    "studio_small_09_1k.hdr": "https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/1k/studio_small_09_1k.hdr",
}

for nombre, url in HDRIS.items():
    destino = ASSETS / nombre
    if destino.exists():
        print(f"{nombre}: ya está")
        continue
    print(f"Bajando {nombre}…")
    urllib.request.urlretrieve(url, destino)
print("Listo.")
