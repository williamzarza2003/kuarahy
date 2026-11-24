"""
Kuarahy · fotos de producto con Cycles.

Uso (desde la carpeta del repo):
  blender -b --factory-startup --python blender/render.py -- --escena estudio --color lapacho --calidad final
  blender -b --factory-startup --python blender/render.py -- --escena todas --calidad boceto

Escenas:
  estudio  fondo transparente con sombra de contacto, una por color (para la grilla de colores y el visor)
  hero     el termo con la guampa, la bombilla, hielo y gotas de condensación, con luz dura de mediodía
  macro    detalle del sol grabado y del pico cebador, con poca profundidad de campo
  ambiente sobre una mesa de madera al aire libre, con hielo y yuyos (HDRI de Poly Haven, CC0)

Calidad:
  boceto  mitad de resolución y 24 muestras (para revisar composición, segundos por imagen)
  final   resolución completa y 160 muestras con eliminación de ruido (minutos por imagen en CPU)
"""
import argparse
import math
import random
import sys
import time
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import termo  # noqa: E402
from termo import cm, hex_lineal  # noqa: E402

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "renders"
ASSETS = AQUI / "assets"

CALIDADES = {
    "boceto": {"escala": 50, "muestras": 24},
    "final": {"escala": 100, "muestras": 160},
}


# ---------------------------------------------------------------- escena base
def preparar(ancho, alto, calidad, transparente=False, exposicion=-0.6, fiel=False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    q = CALIDADES[calidad]
    sc.cycles.samples = q["muestras"]
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    sc.cycles.max_bounces = 10
    sc.cycles.transmission_bounces = 10
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = ancho, alto
    sc.render.resolution_percentage = q["escala"]
    sc.render.film_transparent = transparente
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparente else "RGB"
    sc.render.image_settings.color_depth = "8"
    try:
        if fiel:
            # estudio para la grilla de colores: "Standard" respeta el hex de cada pintura;
            # AgX le saca saturación a los colores fuertes en las zonas iluminadas
            sc.view_settings.view_transform = "Standard"
            sc.view_settings.look = "None"
        else:
            sc.view_settings.view_transform = "AgX"
            sc.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass
    sc.view_settings.exposure = exposicion  # AgX lava los colores saturados si la escena viene pasada
    return sc


def mundo_hdri(archivo, fuerza=1.0, rotacion=0.0, visible=True):
    w = bpy.data.worlds.new("Mundo")
    bpy.context.scene.world = w
    if hasattr(w, "use_nodes"):
        w.use_nodes = True
    nt = w.node_tree
    fondo = next(n for n in nt.nodes if n.type == "BACKGROUND")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(ASSETS / archivo), check_existing=True)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Rotation"].default_value[2] = math.radians(rotacion)
    nt.links.new(coord.outputs["Generated"], mapeo.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], fondo.inputs["Color"])
    fondo.inputs["Strength"].default_value = fuerza
    w.cycles_visibility.camera = visible
    return w


def camara(pos, mirar, lente=70, desenfoque=None):
    cam = bpy.data.cameras.new("Camara")
    cam.lens = lente
    cam.sensor_fit = "AUTO"
    ob = bpy.data.objects.new("Camara", cam)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(pos)
    objetivo = bpy.data.objects.new("Objetivo", None)
    bpy.context.scene.collection.objects.link(objetivo)
    objetivo.location = Vector(mirar)
    c = ob.constraints.new("TRACK_TO")
    c.target = objetivo
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    if desenfoque:
        cam.dof.use_dof = True
        cam.dof.focus_object = desenfoque[0]
        cam.dof.aperture_fstop = desenfoque[1]
    bpy.context.scene.camera = ob
    return ob


def luz_area(nombre, pos, mirar, energia, tam=(1.0, 1.0), color=(1, 1, 1)):
    li = bpy.data.lights.new(nombre, "AREA")
    li.shape = "RECTANGLE"
    li.size, li.size_y = tam
    li.energy = energia
    li.color = color
    ob = bpy.data.objects.new(nombre, li)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(pos)
    d = Vector(mirar) - Vector(pos)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def luz_sol(energia, elevacion, azimut, angulo=0.6):
    li = bpy.data.lights.new("Sol", "SUN")
    li.energy = energia
    li.angle = math.radians(angulo)
    li.color = (1.0, 0.96, 0.9)
    ob = bpy.data.objects.new("Sol", li)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90 - elevacion), 0, math.radians(azimut))
    return ob


def material_simple(nombre, color, rugosidad=0.5, **extra):
    m = bpy.data.materials.new(nombre)
    if hasattr(m, "use_nodes"):
        m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = hex_lineal(color) if isinstance(color, str) else color
    b.inputs["Roughness"].default_value = rugosidad
    for k, v in extra.items():
        if k in b.inputs:
            b.inputs[k].default_value = v
    return m


def ciclorama(color, ancho=4.0, fondo=3.0, alto=2.0, radio=0.6, captador=False):
    """Fondo infinito: piso que se curva hacia la pared, sin línea de horizonte."""
    bm = bmesh.new()
    perfil = [(-fondo, 0.0)]
    perfil += [(-radio * math.sin(t) * 0 + (0.8 - radio + radio * math.sin(math.radians(a))), radio - radio * math.cos(math.radians(a)))
               for a, t in ((a, 0) for a in range(0, 91, 6))]
    perfil += [(0.8, alto)]
    filas = []
    for x in (-ancho / 2, ancho / 2):
        filas.append([bm.verts.new((x, y, z)) for y, z in perfil])
    for i in range(len(perfil) - 1):
        bm.faces.new((filas[0][i], filas[1][i], filas[1][i + 1], filas[0][i + 1]))
    for f in bm.faces:
        f.smooth = True
    me = bpy.data.meshes.new("Ciclorama")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Ciclorama", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material_simple("Fondo", color, 0.9))
    if captador:
        ob.is_shadow_catcher = True
    return ob


# ---------------------------------------------------------------- utilería
def guampa(mats, pos=(0, 0, 0), escala=1.0):
    """Guampa de palo santo torneada, con virolas de acero arriba y abajo."""
    madera = bpy.data.materials.new("PaloSanto")
    if hasattr(madera, "use_nodes"):
        madera.use_nodes = True
    nt = madera.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    # veta fina y vertical: ruido estirado a lo alto, con poco contraste (el palo santo es parejo)
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Scale"].default_value = (45.0, 45.0, 3.0)
    onda = nt.nodes.new("ShaderNodeTexNoise")
    onda.inputs["Scale"].default_value = 1.0
    onda.inputs["Detail"].default_value = 6.0
    onda.inputs["Distortion"].default_value = 0.6
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].position = 0.3
    rampa.color_ramp.elements[1].position = 0.72
    rampa.color_ramp.elements[0].color = hex_lineal("#3a3418")
    rampa.color_ramp.elements[1].color = hex_lineal("#82773f")
    nt.links.new(coord.outputs["Object"], mapeo.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], onda.inputs["Vector"])
    nt.links.new(onda.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.08

    perfil = [(0, 0.0), (3.0, 0.0), (3.25, 0.25), (3.35, 1.0), (3.6, 5.0), (3.85, 9.2), (3.85, 9.6),
              (3.45, 9.6), (3.3, 9.0), (3.05, 2.0), (0, 1.6)]
    g = termo.revolucion("Guampa", perfil, madera)
    for z0, z1, r0 in ((0.0, 1.1, 3.38), (8.6, 9.75, 3.92)):
        v = termo.revolucion(f"Virola{z0}", [(r0 - 0.06, z0), (r0 + 0.05, z0 + 0.05), (r0 + 0.07, (z0 + z1) / 2),
                                            (r0 + 0.05, z1 - 0.05), (r0 - 0.06, z1)], mats["acero"], angulo_filo=70)
        v.parent = g
    # la guampa cargada de yerba hasta casi el borde
    yerba = material_simple("Yerba", "#5d6b2c", 0.95)
    ynt = yerba.node_tree
    yb = next(n for n in ynt.nodes if n.type == "BSDF_PRINCIPLED")
    yr = ynt.nodes.new("ShaderNodeTexNoise")
    yr.inputs["Scale"].default_value = 900.0
    yr.inputs["Detail"].default_value = 8.0
    yc = ynt.nodes.new("ShaderNodeValToRGB")
    yc.color_ramp.elements[0].color = hex_lineal("#3e4a1a")
    yc.color_ramp.elements[1].color = hex_lineal("#8f9a52")
    ybump = ynt.nodes.new("ShaderNodeBump")
    ybump.inputs["Strength"].default_value = 0.8
    ynt.links.new(yr.outputs["Fac"], yc.inputs["Fac"])
    ynt.links.new(yc.outputs["Color"], yb.inputs["Base Color"])
    ynt.links.new(yr.outputs["Fac"], ybump.inputs["Height"])
    ynt.links.new(ybump.outputs["Normal"], yb.inputs["Normal"])
    y = termo.revolucion("Yerba", [(0, 8.75), (2.2, 8.65), (3.25, 8.45), (3.2, 8.2), (0, 8.2)], yerba)
    y.parent = g
    # bombilla de acero con el filtro adentro y la boquilla doblada
    pts = [(0.6, 0.4, 2.2), (0.9, 0.5, 8.0), (1.1, 0.55, 13.0), (1.3, 0.6, 15.6), (2.2, 0.6, 16.6)]
    bom = termo.tubo("Bombilla", [(cm(x), cm(y), cm(z)) for x, y, z in pts], cm(0.32), mats["acero"])
    bom.parent = g
    g.location = Vector(pos)
    g.scale = (escala, escala, escala)
    return g


def hielo_material():
    m = bpy.data.materials.new("Hielo")
    if hasattr(m, "use_nodes"):
        m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = hex_lineal("#eaf8ff")
    b.inputs["Roughness"].default_value = 0.08
    b.inputs["IOR"].default_value = 1.31
    for k in ("Transmission Weight", "Transmission"):
        if k in b.inputs:
            b.inputs[k].default_value = 1.0
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 60.0
    rel = nt.nodes.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = 0.25
    nt.links.new(ruido.outputs["Fac"], rel.inputs["Height"])
    nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    return m


def cubos_hielo(n, centro, dispersion, lado=2.2, semilla=7, altura=0.0):
    random.seed(semilla)
    mat = hielo_material()
    obs = []
    for i in range(n):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=cm(lado * random.uniform(0.8, 1.1)))
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=cm(0.35), segments=3, affect="EDGES")
        for v in bm.verts:  # derretido: apenas irregular
            v.co *= 1 + random.uniform(-0.04, 0.04)
        ob = termo.malla_a_objeto(f"Hielo{i}", bm, mat, angulo_filo=70)
        ob.location = Vector(centro) + Vector((random.uniform(-dispersion, dispersion),
                                               random.uniform(-dispersion, dispersion), altura + cm(lado * 0.42)))
        ob.rotation_euler = (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3), random.uniform(0, math.tau))
        obs.append(ob)
    return obs


def gotas(alto, pintura, cantidad=900, semilla=3):
    """Gotas de condensación sobre el frente del cuerpo.
    Material: la misma pintura del termo, "mojada" (brillo y laca a pleno). Como agua con transmisión,
    a esta escala la luz quedaba atrapada y las gotas salían como puntos negros."""
    random.seed(semilla)
    agua = pintura.copy()
    agua.name = "PinturaMojada"
    nt = agua.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for enlace in list(b.inputs["Normal"].links):
        nt.links.remove(enlace)
    b.inputs["Roughness"].default_value = 0.04
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.01
    b.inputs["Specular IOR Level"].default_value = 0.8
    bm = bmesh.new()
    for _ in range(cantidad):
        ang = random.uniform(-1.9, 1.3)             # sobre todo al frente y a la izquierda (no detrás de la manija)
        z = random.uniform(1.8, alto - 2.8)
        r = random.choice((0.025, 0.035, 0.035, 0.05, 0.05, 0.07, 0.1)) * random.uniform(0.8, 1.2)
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=12, v_segments=8, radius=cm(r))
        # media esfera abierta (sin base): la base queda hundida en la pintura
        bmesh.ops.delete(tmp, geom=[v for v in tmp.verts if v.co.y > cm(r) * 0.2], context="VERTS")
        for v in tmp.verts:
            v.co.y *= 0.6                           # achatada contra la pared
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        c = Vector((math.sin(ang), -math.cos(ang), 0))
        rot = Vector((0, -1, 0)).rotation_difference(c)
        for v in tmp.verts:
            # la base queda hundida en la pintura: sin capa de aire debajo, la gota no se ve oscura
            v.co = rot @ v.co + c * cm(termo.R - r * 0.12) + Vector((0, 0, cm(z)))
        me = bpy.data.meshes.new("g")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    return termo.malla_a_objeto("Gotas", bm, agua, angulo_filo=89)


def mesa_madera():
    m = bpy.data.materials.new("Madera")
    if hasattr(m, "use_nodes"):
        m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    onda = nt.nodes.new("ShaderNodeTexWave")
    onda.inputs["Scale"].default_value = 3.0
    onda.inputs["Distortion"].default_value = 9.0
    onda.inputs["Detail"].default_value = 4.0
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    rampa.color_ramp.elements[0].color = hex_lineal("#6b3f22")
    rampa.color_ramp.elements[1].color = hex_lineal("#b07a4b")
    nt.links.new(onda.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    tablas = []
    for i in range(-5, 6):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.004, segments=2, affect="EDGES")
        ob = termo.malla_a_objeto(f"Tabla{i}", bm, m, angulo_filo=60)
        ob.scale = (2.2, 0.135, 0.035)
        ob.location = (0, i * 0.14, -0.0175)
        ob.rotation_euler.z = random.uniform(-0.004, 0.004)
        tablas.append(ob)
    return tablas


def yuyos(centro, semilla=11, ramitos=4):
    """Ramitos de menta y cedrón: tallo y hojas simples, para el fondo desenfocado."""
    random.seed(semilla)
    hoja_mat = material_simple("Hoja", "#3f7a2e", 0.45)
    b = next(n for n in hoja_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for k in ("Subsurface Weight",):
        if k in b.inputs:
            b.inputs[k].default_value = 0.2
    obs = []
    for r in range(ramitos):
        bm = bmesh.new()
        base = Vector(centro) + Vector((random.uniform(-0.08, 0.08), random.uniform(-0.05, 0.05), cm(0.3)))
        direc = Vector((random.uniform(-1, 1), random.uniform(-1, 1), 0)).normalized()
        largo = random.uniform(0.12, 0.18)
        tallo = [base + direc * largo * t + Vector((0, 0, cm(0.25))) for t in (0, 0.5, 1)]
        tl = termo.tubo(f"Tallo{r}", [tuple(p) for p in tallo], cm(0.12), hoja_mat)
        obs.append(tl)
        for i in range(5):
            t = (i + 1) / 6
            p = base + direc * largo * t
            for lado in (-1, 1):
                ancho = cm(random.uniform(2.2, 3.0)) * (1.15 - t * 0.5)
                n = Vector((-direc.y, direc.x, 0)) * lado
                pts = [p, p + n * ancho * 0.6 + direc * ancho * 0.4 + Vector((0, 0, cm(0.25))),
                       p + n * ancho * 1.2 + direc * ancho * 0.1 + Vector((0, 0, cm(0.15))),
                       p + n * ancho * 0.6 - direc * ancho * 0.35 + Vector((0, 0, cm(0.2)))]
                bm.faces.new([bm.verts.new(q) for q in pts])
        ob = termo.malla_a_objeto(f"Yuyo{r}", bm, hoja_mat, angulo_filo=89)
        ob.modifiers.new("espesor", "SOLIDIFY").thickness = cm(0.05)
        obs.append(ob)
    return obs


# ---------------------------------------------------------------- escenas
def escena_estudio(color, calidad, tapa="clasica"):
    termo.limpiar_escena()
    sc = preparar(1200, 1500, calidad, transparente=True, exposicion=-1.1, fiel=True)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", tapa)
    raiz.rotation_euler.z = math.radians(-20)
    ciclorama("#e9e4de", captador=True)
    mundo_hdri("studio_small_09_1k.hdr", 0.35, rotacion=40, visible=False)
    luz_area("Clave", (-0.55, -0.55, 0.65), (0, 0, 0.12), 32, (0.6, 0.9))
    luz_area("Recorte", (0.6, 0.45, 0.45), (0, 0, 0.14), 26, (0.25, 0.9))
    luz_area("Relleno", (0.7, -0.6, 0.15), (0, 0, 0.12), 6, (1.2, 1.2))
    camara((0.0, -0.78, 0.22), (0, 0, 0.128), lente=72)
    return sc, f"estudio-{color}"


def escena_hero(calidad, color="lapacho"):
    termo.limpiar_escena()
    sc = preparar(1920, 1200, calidad, exposicion=-0.25)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", "clasica")
    raiz.rotation_euler.z = math.radians(-24)
    gotas(termo.ALTURAS["1L"], mats["pintura"]).parent = raiz
    ciclorama("#ff5f1f")
    g = guampa(mats, pos=(0.118, -0.085, 0))
    g.rotation_euler.z = math.radians(30)
    cubos_hielo(2, (0.118, -0.085, cm(8.9)), cm(0.9), lado=1.7, altura=0, semilla=2)
    cubos_hielo(3, (-0.085, -0.115, 0), cm(2.8), lado=2.4, semilla=21)
    mundo_hdri("studio_small_09_1k.hdr", 0.35, rotacion=120, visible=False)
    luz_sol(5.0, elevacion=62, azimut=-40, angulo=0.8)     # mediodía: luz dura desde arriba a la izquierda
    luz_area("Rebote", (0.4, -0.7, 0.1), (0.05, 0, 0.12), 18, (1.5, 1.0), color=(1.0, 0.85, 0.75))
    camara((0.05, -0.78, 0.2), (0.03, 0, 0.122), lente=52)
    return sc, f"hero-{color}"


def escena_macro(calidad, color="parana", detalle="grabado"):
    """Dos detalles: el sol grabado con luz rasante, y la tapa con pico cebador."""
    termo.limpiar_escena()
    sc = preparar(1600, 1200, calidad, exposicion=-0.3)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", "pico")
    ciclorama("#0f1d26")
    mundo_hdri("studio_small_09_1k.hdr", 0.8, rotacion=200, visible=False)
    foco = bpy.data.objects.new("Foco", None)
    bpy.context.scene.collection.objects.link(foco)
    if detalle == "grabado":
        raiz.rotation_euler.z = math.radians(12)
        luz_area("Rasante", (-0.32, -0.12, 0.14), (0, 0, 0.11), 22, (0.08, 0.5))   # luz rasante: marca el grabado
        luz_area("Recorte", (0.3, 0.2, 0.3), (0, 0, 0.12), 25, (0.15, 0.6))
        luz_area("Relleno", (0.1, -0.5, 0.15), (0, 0, 0.11), 4, (0.8, 0.8))
        foco.location = (cm(-1.0), cm(-5.0), cm(12.0))
        camara((-0.03, -0.30, 0.13), (cm(-1.0), 0, cm(10.9)), lente=100, desenfoque=(foco, 3.5))
    else:
        raiz.rotation_euler.z = math.radians(-35)
        luz_area("Clave", (-0.3, -0.25, 0.45), (0, 0, 0.23), 14, (0.3, 0.3))
        luz_area("Recorte", (0.25, 0.3, 0.35), (0, 0, 0.23), 30, (0.15, 0.5))
        foco.location = (cm(-2.6), cm(-1.0), cm(23.4))
        camara((-0.13, -0.26, 0.33), (cm(-1.2), 0, cm(22.0)), lente=100, desenfoque=(foco, 4.0))
    return sc, f"macro-{detalle}"


def escena_ambiente(calidad, color="monte"):
    termo.limpiar_escena()
    sc = preparar(1800, 1200, calidad, exposicion=0.15)
    random.seed(5)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", "clasica")
    raiz.rotation_euler.z = math.radians(-24)
    gotas(termo.ALTURAS["1L"], mats["pintura"], cantidad=180).parent = raiz
    mesa_madera()
    g = guampa(mats, pos=(0.15, -0.02, 0))
    g.rotation_euler.z = math.radians(-20)
    cubos_hielo(2, (0.15, -0.02, cm(8.9)), cm(0.8), lado=1.7, semilla=6)   # el hielo va en la guampa
    yuyos((-0.16, 0.06, 0), ramitos=3)
    yuyos((0.26, 0.04, 0), semilla=31, ramitos=2)
    mundo_hdri("noon_grass_2k.hdr", 1.0, rotacion=60, visible=True)
    foco = bpy.data.objects.new("Foco", None)
    bpy.context.scene.collection.objects.link(foco)
    foco.location = (0, -cm(5), cm(11))
    camara((0.12, -0.85, 0.3), (0.02, 0, 0.12), lente=60, desenfoque=(foco, 3.2))
    return sc, f"ambiente-{color}"


def renderizar(sc, nombre, calidad):
    SALIDA.mkdir(exist_ok=True)
    destino = SALIDA / f"{nombre}{'-boceto' if calidad == 'boceto' else ''}.png"
    sc.render.filepath = str(destino)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDER {destino.name} {time.time() - t:.1f}s", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--escena", default="todas", choices=["estudio", "hero", "macro", "ambiente", "todas"])
    p.add_argument("--color", default="todos", choices=["todos", *termo.VARIANTES])
    p.add_argument("--calidad", default="boceto", choices=list(CALIDADES))
    a = p.parse_args(argv)
    colores = list(termo.VARIANTES) if a.color == "todos" else [a.color]
    if a.escena in ("hero", "todas"):
        renderizar(*escena_hero(a.calidad), a.calidad)
    if a.escena in ("macro", "todas"):
        renderizar(*escena_macro(a.calidad, detalle="grabado"), a.calidad)
        renderizar(*escena_macro(a.calidad, detalle="pico"), a.calidad)
    if a.escena in ("ambiente", "todas"):
        renderizar(*escena_ambiente(a.calidad), a.calidad)
    if a.escena in ("estudio", "todas"):
        for c in colores:
            renderizar(*escena_estudio(c, a.calidad), a.calidad)


if __name__ == "__main__":
    main()
