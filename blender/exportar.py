"""
Kuarahy · exporta el termo para la web y la realidad aumentada.

Uso (desde la carpeta del repo):
  blender -b --factory-startup --python blender/exportar.py
  node blender/optimizar.mjs          # comprime con meshopt y deja todo en public/modelos/

Sale:
  blender/exports/kuarahy.glb                       todos los tamaños y las tres tapas (visor 3D y video)
  blender/exports/kuarahy-<tamano>-<tapa>.glb       una combinación por archivo (realidad aumentada)
  blender/exports/kuarahy-1L-pico.usdz              Quick Look en iPhone, color Lapacho
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import termo  # noqa: E402

SALIDA = Path(__file__).resolve().parent / "exports"
SALIDA.mkdir(exist_ok=True)


def exportar_glb(destino):
    bpy.ops.export_scene.gltf(
        filepath=str(destino),
        export_format="GLB",
        export_yup=True,
        export_apply=True,
        export_texcoords=True,
        export_normals=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        use_visible=True,
    )
    print(f"GLB {destino.name} {destino.stat().st_size / 1024:.0f} KB", flush=True)


def ocultar_no_usadas(tamano, tapa):
    """Deja visible solo una combinación (para los archivos de realidad aumentada)."""
    otro_tam = "15L" if tamano == "1L" else "1L"
    otras_tapas = [n for k, n in termo.TAPAS.items() if k != tapa]
    for nombre in (f"Cuerpo_{otro_tam}", f"Manija_{otro_tam}", f"Logo_{otro_tam}", f"Nombre_{otro_tam}", *otras_tapas):
        ob = bpy.data.objects[nombre]
        for o in [ob, *ob.children_recursive]:
            o.hide_set(True)
            o.hide_render = True
    sup = bpy.data.objects["Superior"]
    sup.location.z = termo.cm(termo.ALTURAS[tamano] - termo.ALTURAS["1L"])


def main():
    # 1) el modelo completo para el visor y el video
    termo.limpiar_escena()
    termo.construir("#e0518d", para_web=True, ambos_tamanos=True)
    exportar_glb(SALIDA / "kuarahy.glb")

    # 2) una combinación por archivo para la realidad aumentada
    for tamano in ("1L", "15L"):
        for tapa in termo.TAPAS:
            termo.limpiar_escena()
            termo.construir("#e0518d", para_web=True, ambos_tamanos=True)
            ocultar_no_usadas(tamano, tapa)
            exportar_glb(SALIDA / f"kuarahy-{tamano}-{tapa}.glb")

    # 3) USDZ para Quick Look (iPhone): 1 L, pico cebador, Lapacho
    termo.limpiar_escena()
    termo.construir("#e0518d", "1L", "pico", para_web=True)
    for o in bpy.data.objects:
        if o.hide_render:
            bpy.data.objects.remove(o, do_unlink=True)
    destino = SALIDA / "kuarahy-1L-pico.usdz"
    try:
        bpy.ops.wm.usd_export(filepath=str(destino), export_materials=True, generate_preview_surface=True)
        print(f"USDZ {destino.name} {destino.stat().st_size / 1024:.0f} KB", flush=True)
    except Exception as e:  # el exportador USD cambia entre versiones: que no frene el resto
        print("USDZ no exportado:", e, flush=True)


if __name__ == "__main__":
    main()
