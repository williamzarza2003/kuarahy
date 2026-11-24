"""
Kuarahy · el termo modelado por código (Blender 5.x, bpy + bmesh).

Un solo modelo para todo: este módulo construye el termo y lo usan
  - exportar.py → kuarahy.glb (web, React Three Fiber) y kuarahy.usdz (AR en iPhone)
  - render.py   → fotos de producto con Cycles
  - el video de Remotion, que carga el mismo GLB.

Unidades: metros (como glTF). Z hacia arriba, el frente del termo (logo) mira a -Y.
Todas las medidas de diseño están en centímetros y se convierten con cm().

Piezas (nombres que la web usa para encontrar cada nodo):
  Base, Cuerpo_1L, Cuerpo_15L, Manija_1L, Manija_15L, Logo_1L, Logo_15L,
  Superior (vacío) → Collar, Tapa_Clasica, Tapa_Pico
"""
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

AQUI = Path(__file__).resolve().parent
FUENTE = AQUI / "assets" / "BricolageGrotesque-ExtraBold.ttf"

# ---------------------------------------------------------------- medidas (cm)
R = 5.0                      # radio del cuerpo pintado
ALTURAS = {"1L": 20.0, "15L": 26.5}   # altura del cuerpo pintado (borde superior)
SEGMENTOS = 96               # resolución de la revolución

# Colores del paisaje paraguayo (los mismos de src/data/variantes.ts)
VARIANTES = {
    "lapacho": "#e0518d",
    "siesta": "#ea5a1c",
    "parana": "#1d6ea3",
    "monte": "#2d7451",
    "carbon": "#2a2d33",
}


def cm(v):
    return v * 0.01


def hex_lineal(h, alfa=1.0):
    """#rrggbb (sRGB) → color lineal para Blender."""
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (*lin, alfa)


# ---------------------------------------------------------------- utilidades de malla
def malla_a_objeto(nombre, bm, material=None, suave=True, angulo_filo=40):
    """Convierte un bmesh en objeto: sombreado suave y filos marcados por ángulo."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=cm(0.001))
    bm.normal_update()
    limite = math.radians(angulo_filo)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > limite:
            e.smooth = False
    for f in bm.faces:
        f.smooth = suave
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def revolucion(nombre, perfil, material=None, segmentos=SEGMENTOS, angulo_filo=40):
    """Gira un perfil [(radio_cm, z_cm), ...] alrededor de Z. Un radio 0 cierra el polo."""
    bm = bmesh.new()
    verts = [bm.verts.new((cm(r), 0.0, cm(z))) for r, z in perfil]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   steps=segmentos, angle=math.tau, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=cm(0.002))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return malla_a_objeto(nombre, bm, material, angulo_filo=angulo_filo)


def arco(cx, cz, r, a0, a1, pasos=8):
    """Puntos de un arco en el plano (radio, z), ángulos en grados."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / pasos)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / pasos))) for i in range(pasos + 1)]


def tubo(nombre, puntos, radio, material=None, resolucion=10, cerrado=False):
    """Un tubo redondo que sigue una curva (manija, asa, bombilla)."""
    cu = bpy.data.curves.new(nombre, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radio
    cu.bevel_resolution = resolucion // 2
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(puntos) - 1)
    for p, (x, y, z) in zip(sp.points, puntos):
        p.co = (x, y, z, 1)
    sp.order_u = min(4, len(puntos))
    sp.use_endpoint_u = True
    sp.use_cyclic_u = cerrado
    sp.resolution_u = 16
    tmp = bpy.data.objects.new(nombre + "_curva", cu)
    bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    return malla_a_objeto(nombre, bm, material, angulo_filo=60)


# ---------------------------------------------------------------- materiales
def nodo_principled(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    return nt, bsdf


def entrada(bsdf, *nombres):
    """Busca la entrada por nombre (los nombres cambiaron entre versiones de Blender)."""
    for n in nombres:
        if n in bsdf.inputs:
            return bsdf.inputs[n]
    return None


def material_pintura(color_hex, para_web):
    m = bpy.data.materials.new("Pintura")
    nt, b = nodo_principled(m)
    b.inputs["Base Color"].default_value = hex_lineal(color_hex)
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Roughness"].default_value = 0.52
    if c := entrada(b, "Coat Weight"):
        c.default_value = 0.0 if para_web else 0.12
    if not para_web:
        # pintura en polvo: grano muy fino en el relieve y la rugosidad
        ruido = nt.nodes.new("ShaderNodeTexNoise")
        ruido.inputs["Scale"].default_value = 1800.0
        ruido.inputs["Detail"].default_value = 2.0
        rel = nt.nodes.new("ShaderNodeBump")
        rel.inputs["Strength"].default_value = 0.035
        rel.inputs["Distance"].default_value = 0.0002
        nt.links.new(ruido.outputs["Fac"], rel.inputs["Height"])
        nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    return m


def material_acero(nombre="Acero", rugosidad=0.26, para_web=False):
    m = bpy.data.materials.new(nombre)
    nt, b = nodo_principled(m)
    b.inputs["Base Color"].default_value = hex_lineal("#cfd3d7")
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rugosidad
    if not para_web:
        # cepillado horizontal: rayas finas alrededor del termo (ruido estirado en Z)
        coord = nt.nodes.new("ShaderNodeTexCoord")
        mapeo = nt.nodes.new("ShaderNodeMapping")
        mapeo.inputs["Scale"].default_value = (6.0, 6.0, 1600.0)
        ruido = nt.nodes.new("ShaderNodeTexNoise")
        ruido.inputs["Scale"].default_value = 4.0
        ruido.inputs["Detail"].default_value = 6.0
        rampa = nt.nodes.new("ShaderNodeMapRange")
        rampa.inputs["To Min"].default_value = rugosidad - 0.07
        rampa.inputs["To Max"].default_value = rugosidad + 0.09
        nt.links.new(coord.outputs["Object"], mapeo.inputs["Vector"])
        nt.links.new(mapeo.outputs["Vector"], ruido.inputs["Vector"])
        nt.links.new(ruido.outputs["Fac"], rampa.inputs["Value"])
        nt.links.new(rampa.outputs["Result"], b.inputs["Roughness"])
        if a := entrada(b, "Anisotropic"):
            a.default_value = 0.55
            tang = nt.nodes.new("ShaderNodeTangent")
            tang.direction_type = "RADIAL"
            tang.axis = "Z"
            if t := entrada(b, "Tangent"):
                nt.links.new(tang.outputs["Tangent"], t)
    return m


def material_goma(para_web):
    m = bpy.data.materials.new("Goma")
    _, b = nodo_principled(m)
    b.inputs["Base Color"].default_value = hex_lineal("#1c1c1e")
    b.inputs["Roughness"].default_value = 0.82
    return m


def materiales(color_hex="#e0518d", para_web=False):
    return {
        "pintura": material_pintura(color_hex, para_web),
        "acero": material_acero("Acero", 0.24, para_web),
        "grabado": material_acero("Grabado", 0.42, para_web),
        "goma": material_goma(para_web),
        "nombre": material_acero("Nombre", 0.42, True),
    }


# ---------------------------------------------------------------- piezas
def base(mats):
    perfil = [(0, 0.12), (4.2, 0.12), (4.55, 0.0), (4.78, 0.08), (4.93, 0.35),
              (4.96, 0.8), (4.96, 1.12), (4.86, 1.22), (0, 1.22)]
    ob = revolucion("Base", perfil, mats["acero"])
    # pie de goma antideslizante
    pie = revolucion("Base_Pie", [(0, 0.0), (4.1, 0.0), (4.3, 0.06), (4.3, 0.14), (0, 0.14)], mats["goma"])
    pie.parent = ob
    return ob


def cuerpo(nombre, alto, mats):
    """Cuerpo pintado: arranca sobre la base, hombro redondeado y cuello bajo el collar."""
    h = alto
    perfil = [(0, 1.0), (4.84, 1.0), (4.94, 1.12), (5.0, 1.35)]
    perfil += [(R, z) for z in (2.0, h * 0.35, h * 0.7)]
    perfil += arco(R - 0.55, h - 0.65, 0.55, 0, 90, 8)          # hombro chico: el cuerpo sube recto
    perfil += [(4.4, h - 0.1), (4.4, h + 0.2), (0, h + 0.2)]
    return revolucion(nombre, perfil, mats["pintura"])


def collar(alto, mats):
    h = alto
    perfil = [(4.3, h - 0.28), (4.7, h - 0.28), (4.8, h - 0.18), (4.8, h + 0.74),
              (4.72, h + 0.85), (4.0, h + 0.85), (4.0, h - 0.1)]
    return revolucion("Collar", perfil, mats["acero"])


def tapa_clasica(alto, mats):
    h = alto + 0.85
    perfil = [(0, h), (4.76, h), (4.86, h + 0.1)]
    perfil += [(4.86, h + 1.85)] + arco(4.3, h + 1.85, 0.56, 0, 90, 8)[1:]
    perfil += [(1.4, h + 2.45), (0, h + 2.48)]
    tapa = revolucion("Tapa_Clasica", perfil, mats["acero"])
    # banda de goma para agarrar la tapa
    banda = revolucion("Tapa_Clasica_Banda", [(4.84, h + 0.45), (4.96, h + 0.5), (4.96, h + 1.45), (4.84, h + 1.5)],
                       mats["goma"], angulo_filo=80)
    banda.parent = tapa
    # asa plegable de acero sobre la tapa
    top = h + 2.42
    pts = [(-3.3, 0, top - 0.15), (-3.25, 0, top + 1.3), (-1.9, 0, top + 2.5),
           (0, 0, top + 2.75), (1.9, 0, top + 2.5), (3.25, 0, top + 1.3), (3.3, 0, top - 0.15)]
    asa = tubo("Tapa_Clasica_Asa", [(cm(x), cm(y), cm(z)) for x, y, z in pts], cm(0.32), mats["acero"])
    asa.parent = tapa
    for s in (-1, 1):  # bisagras
        bis = revolucion(f"Tapa_Clasica_Bisagra{'I' if s < 0 else 'D'}",
                         [(0, -0.35), (0.42, -0.35), (0.5, -0.25), (0.5, 0.25), (0.42, 0.35), (0, 0.35)],
                         mats["acero"], segmentos=24)
        bis.rotation_euler = (0, math.radians(90), 0)
        bis.location = (cm(s * 3.3), 0, cm(top - 0.1))
        bis.parent = tapa
    return tapa


def tapa_pico(alto, mats):
    """Tapa con pico cebador: sirve el agua de a poco sobre la guampa, con una mano."""
    h = alto + 0.85
    perfil = [(0, h), (4.76, h), (4.86, h + 0.1), (4.86, h + 1.45)] + arco(4.3, h + 1.45, 0.56, 0, 90, 8)[1:]
    perfil += [(0, h + 2.05)]
    tapa = revolucion("Tapa_Pico", perfil, mats["acero"])
    banda = revolucion("Tapa_Pico_Banda", [(4.84, h + 0.4), (4.96, h + 0.45), (4.96, h + 1.2), (4.84, h + 1.25)],
                       mats["goma"], angulo_filo=80)
    banda.parent = tapa
    # pico cebador: boca cónica que nace de la tapa, inclinada hacia afuera (lado opuesto a la manija)
    top = h + 2.05
    pico = revolucion("Tapa_Pico_Tubo",
                      [(0, -0.3), (1.05, -0.3), (1.05, 0.15), (0.72, 1.45), (0.66, 1.62), (0.5, 1.62),
                       (0.5, 0.2), (0, 0.2)],
                      mats["acero"], segmentos=48, angulo_filo=50)
    pico.rotation_euler = (0, math.radians(-34), 0)
    pico.location = (cm(-3.0), 0, cm(top - 0.15))
    pico.parent = tapa
    # tapita de goma del pico, abierta y apoyada sobre la tapa, unida por una tira
    tapita = revolucion("Tapa_Pico_Tapita",
                        [(0, 0.0), (0.82, 0.0), (0.86, 0.12), (0.86, 0.32), (0.76, 0.4), (0, 0.4)],
                        mats["goma"], segmentos=40)
    tapita.location = (cm(-1.1), cm(-1.6), cm(top - 0.02))
    tapita.parent = tapa
    tira = tubo("Tapa_Pico_Tira", [(cm(-2.2), cm(-0.6), cm(top + 0.05)), (cm(-1.7), cm(-1.2), cm(top + 0.12)),
                                    (cm(-1.3), cm(-1.5), cm(top + 0.12))], cm(0.14), mats["goma"])
    tira.parent = tapa
    # botón de apertura
    # botón de apertura: alargado y bajo, para que no se confunda con la tapita
    boton = revolucion("Tapa_Pico_Boton", [(0, 0), (0.55, 0), (0.6, 0.15), (0.5, 0.26), (0, 0.28)], mats["goma"], segmentos=32)
    boton.scale = (1.8, 1.0, 1.0)
    boton.location = (cm(1.8), 0, cm(top - 0.05))
    boton.parent = tapa
    return tapa


def manija(nombre, alto, mats):
    """Manija lateral en C, pintada del color del termo, sobre el lado +X."""
    arriba, abajo = alto - 3.4, 4.4
    x0, x1 = R - 0.35, R + 3.1
    pts = [(x0, 0, arriba), (x0 + 0.9, 0, arriba + 0.05), (x1 - 0.5, 0, arriba - 0.1), (x1, 0, arriba - 1.0),
           (x1 + 0.08, 0, (arriba + abajo) / 2), (x1, 0, abajo + 1.0), (x1 - 0.5, 0, abajo + 0.1),
           (x0 + 0.9, 0, abajo - 0.05), (x0, 0, abajo)]
    ob = tubo(nombre, [(cm(x), cm(y), cm(z)) for x, y, z in pts], cm(0.78), mats["pintura"])
    # anclajes de acero contra el cuerpo
    for i, z in enumerate((arriba, abajo)):
        an = revolucion(f"{nombre}_Anclaje{i}", [(0, 0), (0.95, 0), (0.95, 0.5), (0.8, 0.62), (0, 0.62)],
                        mats["acero"], segmentos=32)
        an.rotation_euler = (0, math.radians(90), 0)
        an.location = (cm(R - 0.25), 0, cm(z))
        an.parent = ob
    return ob


# ---------------------------------------------------------------- logo grabado
def _envolver(bm, radio, z_centro):
    """Lleva una figura plana (x = ancho, y = alto) a la superficie del cilindro, mirando a -Y."""
    for v in bm.verts:
        u, w = v.co.x, v.co.y
        ang = u / radio
        v.co = Vector((radio * math.sin(ang), -radio * math.cos(ang), z_centro + w))


def _sol_2d(bm):
    """Sol de la marca: anillo, 12 rayos y centro (en cm, plano XY)."""
    def anillo(r0, r1, n=64):
        a = [bm.verts.new((r0 * math.cos(t), r0 * math.sin(t), 0)) for t in (math.tau * i / n for i in range(n))]
        b = [bm.verts.new((r1 * math.cos(t), r1 * math.sin(t), 0)) for t in (math.tau * i / n for i in range(n))]
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    anillo(0.98, 1.2)
    # centro
    n = 32
    c = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new((0.4 * math.cos(math.tau * i / n), 0.4 * math.sin(math.tau * i / n), 0)) for i in range(n)]
    for i in range(n):
        bm.faces.new((c, ring[i], ring[(i + 1) % n]))
    # rayos con punta redondeada (cápsulas)
    for k in range(12):
        t = math.tau * k / 12
        d = Vector((math.cos(t), math.sin(t), 0))
        p = Vector((-math.sin(t), math.cos(t), 0))
        pts = []
        for i in range(9):  # semicírculo interior
            a = math.pi / 2 + math.pi * i / 8
            pts.append(d * 1.5 + (d * math.cos(a) + p * math.sin(a)) * 0.11)
        for i in range(9):  # semicírculo exterior
            a = -math.pi / 2 + math.pi * i / 8
            pts.append(d * 1.95 + (d * math.cos(a) + p * math.sin(a)) * 0.11)
        bm.faces.new([bm.verts.new(q) for q in pts])


def _texto_2d(bm, texto, alto_letra, espaciado):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = texto
    if FUENTE.exists():
        cu.font = bpy.data.fonts.load(str(FUENTE), check_existing=True)
    cu.size = 1.0
    cu.space_character = espaciado
    cu.align_x = "CENTER"
    cu.resolution_u = 6
    tmp = bpy.data.objects.new("txt", cu)
    bpy.context.scene.collection.objects.link(tmp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp)
    bpy.data.curves.remove(cu)
    # escala a la altura de mayúscula pedida
    zs = [v.co.y for v in me.vertices]
    alto = max(zs) - min(zs)
    esc = alto_letra / alto
    off = (max(zs) + min(zs)) / 2
    tmp_bm = bmesh.new()
    tmp_bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    for v in tmp_bm.verts:
        v.co = Vector((v.co.x * esc, (v.co.y - off) * esc, 0))
    # subdividir para que la curva del cilindro no corte las letras anchas
    bmesh.ops.triangulate(tmp_bm, faces=tmp_bm.faces)
    for _ in range(2):
        largas = [e for e in tmp_bm.edges if e.calc_length() > 0.25]
        if largas:
            bmesh.ops.subdivide_edges(tmp_bm, edges=largas, cuts=1, use_grid_fill=False)
            bmesh.ops.triangulate(tmp_bm, faces=tmp_bm.faces)
    tmp_me = bpy.data.meshes.new("t")
    tmp_bm.to_mesh(tmp_me)
    tmp_bm.free()
    bm.from_mesh(tmp_me)
    bpy.data.meshes.remove(tmp_me)


def logo(nombre, alto, mats):
    """Sol y KUARAHY grabados con láser: la pintura se va y queda el acero, apenas hundido."""
    z_sol = alto * 0.60
    bm = bmesh.new()
    _sol_2d(bm)
    bm2 = bmesh.new()
    _texto_2d(bm2, "KUARAHY", 0.72, 1.12)
    # unir: el texto va 2,85 cm por debajo del centro del sol
    me = bpy.data.meshes.new("t")
    for v in bm2.verts:
        v.co.y -= 2.85
    bm2.to_mesh(me)
    bm2.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    # la figura se dibujó en cm: pasar a metros y envolverla sobre el cuerpo, apenas por fuera
    for v in bm.verts:
        v.co *= 0.01
    _envolver(bm, cm(R) + cm(0.012), cm(z_sol))
    return _logo_objeto(nombre, bm, mats)


def _logo_objeto(nombre, bm, mats):
    # espesor mínimo hacia adentro, para que se lea como un grabado y no flote sobre la pintura
    geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    nuevos = [e for e in geom["geom"] if isinstance(e, bmesh.types.BMVert)]
    for v in nuevos:
        radial = Vector((v.co.x, v.co.y, 0)).normalized()
        v.co -= radial * cm(0.03)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return malla_a_objeto(nombre, bm, mats["grabado"], suave=False)


# ---------------------------------------------------------------- grabado del nombre (personalizador)
NOMBRE_ARCO = 80.0      # grados que cubre la banda del nombre, centrada en el frente
NOMBRE_ALTO = 1.5       # cm


def z_nombre(alto):
    """Centro de la banda del nombre: debajo de KUARAHY."""
    return alto * 0.60 - 2.85 - 2.3


def banda_nombre(nombre, alto, mats):
    """Banda curva con UV 0..1 sobre el frente: la web le pinta el nombre (CanvasTexture).
    Va apenas por fuera del logo para no pelearse con la pintura."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    n = 32
    r = cm(R + 0.016)
    zc = cm(z_nombre(alto))
    filas = []
    for j, dz in enumerate((-NOMBRE_ALTO / 2, NOMBRE_ALTO / 2)):
        fila = []
        for i in range(n + 1):
            ang = math.radians(-NOMBRE_ARCO / 2 + NOMBRE_ARCO * i / n)
            fila.append(bm.verts.new((r * math.sin(ang), -r * math.cos(ang), zc + cm(dz))))
        filas.append(fila)
    for i in range(n):
        f = bm.faces.new((filas[0][i], filas[0][i + 1], filas[1][i + 1], filas[1][i]))
        for loop, (u, v) in zip(f.loops, ((i / n, 0), ((i + 1) / n, 0), ((i + 1) / n, 1), (i / n, 1))):
            loop[uv].uv = (u, v)
    return malla_a_objeto(nombre, bm, mats["nombre"], angulo_filo=89)


# ---------------------------------------------------------------- armado
def limpiar_escena():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coleccion in (bpy.data.meshes, bpy.data.materials, bpy.data.curves, bpy.data.lights, bpy.data.cameras,
                      bpy.data.images, bpy.data.worlds, bpy.data.node_groups):
        for b in list(coleccion):
            if b.users == 0:
                coleccion.remove(b)


def construir(color_hex="#e0518d", tamano="1L", tapa="clasica", para_web=False, ambos_tamanos=False):
    """Arma el termo. Con ambos_tamanos=True (para la web) incluye los cuerpos de 1 L y 1,5 L."""
    mats = materiales(color_hex, para_web)
    raiz = bpy.data.objects.new("Kuarahy", None)
    bpy.context.scene.collection.objects.link(raiz)

    tamanos = ["1L", "15L"] if ambos_tamanos else [tamano]
    for t in tamanos:
        h = ALTURAS[t]
        piezas = [cuerpo(f"Cuerpo_{t}", h, mats), manija(f"Manija_{t}", h, mats), logo(f"Logo_{t}", h, mats)]
        if para_web:
            piezas.append(banda_nombre(f"Nombre_{t}", h, mats))
        for ob in piezas:
            ob.parent = raiz
    b = base(mats)
    b.parent = raiz

    # la parte de arriba se arma a la altura de 1 L; para 1,5 L se sube entera
    h0 = ALTURAS["1L"]
    sup = bpy.data.objects.new("Superior", None)
    bpy.context.scene.collection.objects.link(sup)
    sup.parent = raiz
    for ob in (collar(h0, mats), tapa_clasica(h0, mats), tapa_pico(h0, mats)):
        ob.parent = sup
    if not ambos_tamanos:
        sup.location.z = cm(ALTURAS[tamano] - h0)
        bpy.data.objects["Tapa_Clasica" if tapa == "pico" else "Tapa_Pico"].hide_render = True
        bpy.data.objects["Tapa_Clasica" if tapa == "pico" else "Tapa_Pico"].hide_viewport = True
        for hijo in bpy.data.objects["Tapa_Clasica" if tapa == "pico" else "Tapa_Pico"].children_recursive:
            hijo.hide_render = hijo.hide_viewport = True
    return raiz, mats


if __name__ == "__main__":
    limpiar_escena()
    construir()
