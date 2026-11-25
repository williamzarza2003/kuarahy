"""
Kuarahy · fotos de producto con Cycles.

Uso (desde la carpeta del repo):
  blender -b --factory-startup --python blender/render.py -- --escena estudio --color lapacho --calidad final
  blender -b --factory-startup --python blender/render.py -- --escena todas --calidad boceto

Escenas:
  estudio      fondo transparente con sombra de contacto, una por color (grilla de colores, visor, portada)
  hero         el termo transpirando con el pico abierto, la guampa de palo santo y hielo suelto al lado
  macro        detalle del sol grabado (con las paredes del corte) y del pico cebador
  ambiente     mesa al aire libre: boca ancha abierta con hielo, la tapa al lado y la guampa (HDRI CC0)
  referencias  renders limpios en fondo neutro, cada color y varios ángulos, para usar en Buzzy
               (van a Projects/Audiovisual/editor-video/referencias-kuarahy)

Reglas de utilería: el hielo va en el termo o al lado, nunca en la guampa ni junto a la bombilla.

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
from mathutils import Matrix, Vector

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
def material_palo_santo():
    """Palo santo: verde oliva con vetas finas y oscuras que corren a lo largo de la pieza,
    y laca satinada. Vetas con ondas (bandas) deformadas por ruido, para que no sean rayas perfectas."""
    m = bpy.data.materials.new("PaloSanto")
    if hasattr(m, "use_nodes"):
        m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Scale"].default_value = (90.0, 90.0, 2.2)          # vetas verticales y finas
    ruido_d = nt.nodes.new("ShaderNodeTexNoise")
    ruido_d.inputs["Scale"].default_value = 1.6
    ruido_d.inputs["Detail"].default_value = 3.0
    mezcla = nt.nodes.new("ShaderNodeVectorMath")
    mezcla.operation = "ADD"
    onda = nt.nodes.new("ShaderNodeTexWave")
    onda.wave_type = "BANDS"
    onda.bands_direction = "X"
    onda.inputs["Scale"].default_value = 1.1
    onda.inputs["Distortion"].default_value = 4.0
    onda.inputs["Detail"].default_value = 3.0
    onda.inputs["Detail Scale"].default_value = 1.4
    rampa = nt.nodes.new("ShaderNodeValToRGB")
    els = rampa.color_ramp.elements
    els[0].position, els[0].color = 0.0, hex_lineal("#3a3519")
    els[1].position, els[1].color = 0.4, hex_lineal("#5c5530")
    e = els.new(0.85)
    e.color = hex_lineal("#6f6638")
    poros = nt.nodes.new("ShaderNodeTexNoise")                     # poro fino de la madera
    poros.inputs["Scale"].default_value = 1400.0
    rel = nt.nodes.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = 0.12
    nt.links.new(coord.outputs["Object"], mapeo.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], ruido_d.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], mezcla.inputs[0])
    nt.links.new(ruido_d.outputs["Color"], mezcla.inputs[1])
    nt.links.new(mezcla.outputs["Vector"], onda.inputs["Vector"])
    # segunda veta, más fina y suave, mezclada encima: la madera no tiene rayas parejas
    fina = nt.nodes.new("ShaderNodeTexWave")
    fina.wave_type = "BANDS"
    fina.bands_direction = "X"
    fina.inputs["Scale"].default_value = 4.3
    fina.inputs["Distortion"].default_value = 2.0
    fina.inputs["Detail"].default_value = 2.0
    suma = nt.nodes.new("ShaderNodeMix")
    suma.data_type = "FLOAT"
    suma.inputs["Factor"].default_value = 0.35
    nt.links.new(mezcla.outputs["Vector"], fina.inputs["Vector"])
    nt.links.new(onda.outputs["Fac"], suma.inputs["A"])
    nt.links.new(fina.outputs["Fac"], suma.inputs["B"])
    nt.links.new(suma.outputs["Result"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(poros.outputs["Fac"], rel.inputs["Height"])
    nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.42
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.35
        b.inputs["Coat Roughness"].default_value = 0.25
    return m


def material_yerba():
    m = material_simple("Yerba", "#5d6b2c", 0.95)
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")                      # hojitas y palitos sueltos
    vor.inputs["Scale"].default_value = 520.0
    col = nt.nodes.new("ShaderNodeValToRGB")
    col.color_ramp.elements[0].color = hex_lineal("#2f3a12")
    col.color_ramp.elements[1].color = hex_lineal("#8f9a52")
    e = col.color_ramp.elements.new(0.85)
    e.color = hex_lineal("#c9c08a")                                 # palitos claros
    rel = nt.nodes.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = 0.9
    nt.links.new(vor.outputs["Distance"], col.inputs["Fac"])
    nt.links.new(col.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(vor.outputs["Distance"], rel.inputs["Height"])
    nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    return m


def guampa(mats, pos=(0, 0, 0), giro=0.0, con_bombilla=True):
    """Guampa de palo santo torneada: panza suave, dos surcos de torno, virola de acero arriba
    (con el labio enrollado sobre el borde) y abajo. Cargada de yerba en montañita, sin hielo."""
    madera = material_palo_santo()
    afuera = [(0, 0.0), (2.75, 0.0, 0.25), (3.0, 1.0, 0.3), (3.38, 4.2), (3.5, 8.0), (3.48, 9.2)]
    adentro = [(3.02, 9.2, 0.15), (2.98, 6.0), (2.62, 1.2, 0.4), (0, 1.0)]
    perfil = termo.filetear(afuera + adentro, 0.08, pasos=5)

    def surcos(v):
        r = math.hypot(v.co.x, v.co.y)
        if r > 3.1:
            for zc in (3.1, 3.5):
                d = abs(v.co.z - zc)
                if d < 0.09:
                    k = (1 - d / 0.09) ** 2 * 0.05
                    v.co.x *= (r - k) / r
                    v.co.y *= (r - k) / r

    g = termo.revolucion("Guampa", perfil, madera, deformar=surcos)
    virola_sup = termo.revolucion("Guampa_VirolaSup", termo.filetear(
        [(3.56, 8.45), (3.6, 8.55, 0.05), (3.6, 9.25, 0.06), (3.5, 9.45, 0.12), (3.1, 9.45, 0.1), (2.96, 9.2, 0.05),
         (2.96, 8.9)], pasos=5), mats["acero"])
    virola_inf = termo.revolucion("Guampa_VirolaInf", termo.filetear(
        [(2.7, -0.02), (2.82, -0.02, 0.06), (3.08, 0.9, 0.05), (3.12, 1.05, 0.04), (3.02, 1.12)], pasos=4), mats["acero"])
    for v in (virola_sup, virola_inf):
        v.parent = g
    # yerba en montañita: alta contra un lado, baja donde entra la bombilla
    random.seed(4)
    bm = bmesh.new()
    n_r, n_a = 10, 48

    def zf(rr, a):
        return (8.0 + 0.9 * (0.5 - 0.5 * math.cos(a - 2.6)) * (1 - (rr / 3.2) ** 2)
                + 0.4 * (1 - (rr / 3.0) ** 2) + random.uniform(-0.05, 0.05))

    centro = bm.verts.new((0, 0, zf(0, 0)))
    filas = []
    for i in range(1, n_r + 1):
        rr = 2.95 * i / n_r
        filas.append([bm.verts.new((rr * math.cos(math.tau * j / n_a), rr * math.sin(math.tau * j / n_a),
                                    zf(rr, math.tau * j / n_a))) for j in range(n_a)])
    for j in range(n_a):
        bm.faces.new((centro, filas[0][j], filas[0][(j + 1) % n_a]))
    for i in range(n_r - 1):
        for j in range(n_a):
            bm.faces.new((filas[i][j], filas[i + 1][j], filas[i + 1][(j + 1) % n_a], filas[i][(j + 1) % n_a]))
    for v in bm.verts:
        v.co *= 0.01
    yerba = termo.malla_a_objeto("Yerba", bm, material_yerba(), angulo_filo=89)
    yerba.parent = g
    if con_bombilla:
        bom = termo.bombilla("Bombilla", mats["acero"], largo=17.0)
        bom.rotation_euler = (math.radians(-11), 0, math.radians(-110))
        bom.location = (cm(-0.9), cm(0.5), cm(1.6))
        bom.parent = g
    g.location = Vector(pos)
    g.rotation_euler.z = math.radians(giro)
    return g


def hielo_material():
    m = bpy.data.materials.new("Hielo")
    if hasattr(m, "use_nodes"):
        m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = hex_lineal("#eef9ff")
    b.inputs["Roughness"].default_value = 0.06
    b.inputs["IOR"].default_value = 1.31
    for k in ("Transmission Weight", "Transmission"):
        if k in b.inputs:
            b.inputs[k].default_value = 1.0
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 55.0
    ruido.inputs["Detail"].default_value = 4.0
    rel = nt.nodes.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = 0.3
    nt.links.new(ruido.outputs["Fac"], rel.inputs["Height"])
    nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    return m


def cubos_hielo(posiciones, lado=2.2, semilla=7):
    """Cubitos de hielo de máquina (con un hueco de un lado), apenas derretidos. posiciones en metros."""
    random.seed(semilla)
    mat = hielo_material()
    obs = []
    for i, p in enumerate(posiciones):
        bm = bmesh.new()
        tam = lado * random.uniform(0.85, 1.08)
        bmesh.ops.create_cube(bm, size=cm(tam))
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=cm(0.32), segments=3, affect="EDGES")
        for v in bm.verts:
            v.co *= 1 + random.uniform(-0.035, 0.035)
            if v.co.z > cm(tam * 0.3):                 # el hueco de la cubetera
                v.co.z -= cm(0.25) * (1 - min(1, Vector((v.co.x, v.co.y)).length / cm(tam * 0.45)))
        ob = termo.malla_a_objeto(f"Hielo{i}", bm, mat, angulo_filo=70)
        ob.location = Vector(p)
        ob.rotation_euler = (random.uniform(-0.25, 0.25), random.uniform(-0.25, 0.25), random.uniform(0, math.tau))
        obs.append(ob)
    return obs


def hielo_en_termo(alto, cantidad=7, semilla=12):
    """Cubitos asomando por la boca ancha: el hielo va en el termo, no en la guampa."""
    random.seed(semilla)
    z0 = alto + 0.78 + 1.62 - 0.9
    pos = []
    for k in range(cantidad):
        a = math.tau * k / cantidad + random.uniform(-0.2, 0.2)
        r = 1.6 if k < cantidad - 2 else random.uniform(0, 0.6)
        # los del medio asoman por encima del borde: se ven desde la altura de una mesa
        dz = random.uniform(-0.5, 0.2) + (1.5 if k >= cantidad - 2 else 0.4)
        pos.append((cm(r * math.cos(a)), cm(r * math.sin(a)), cm(z0 + dz)))
    return cubos_hielo(pos, lado=2.0, semilla=semilla)


def gotas(alto, pintura, cantidad=1100, semilla=3):
    """Condensación sobre el frente y la izquierda del cuerpo (la manija queda seca: ahí va la mano).
    Material: la misma pintura del termo, "mojada" (brillo y laca a pleno). Como agua con transmisión,
    a esta escala la luz quedaba atrapada y las gotas salían como puntos negros."""
    random.seed(semilla)
    agua = pintura.copy()
    agua.name = "PinturaMojada"
    nt = agua.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for enlace in list(b.inputs["Normal"].links) + list(b.inputs["Roughness"].links):
        nt.links.remove(enlace)
    b.inputs["Roughness"].default_value = 0.03
    b.inputs["Coat Weight"].default_value = 1.0
    b.inputs["Coat Roughness"].default_value = 0.01
    b.inputs["Specular IOR Level"].default_value = 0.8
    bm = bmesh.new()
    for i in range(cantidad):
        ang = random.uniform(-2.2, 1.2)
        z = random.uniform(2.2, alto - 5.2)
        grande = i % 23 == 0                       # algunas gotas gordas que ya empezaron a correr
        r = (random.uniform(0.12, 0.16) if grande else
             random.choice((0.022, 0.03, 0.03, 0.04, 0.05, 0.06, 0.08))) * random.uniform(0.85, 1.15)
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=12, v_segments=8, radius=cm(r))
        bmesh.ops.delete(tmp, geom=[v for v in tmp.verts if v.co.y > cm(r) * 0.2], context="VERTS")
        for v in tmp.verts:
            v.co.y *= 0.55
            if grande and v.co.z < 0:
                v.co.z *= 1.8                    # gota cayendo: más larga abajo
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        rc = termo.r_cuerpo(z, alto)
        c = Vector((math.sin(ang), -math.cos(ang), 0))
        rot = Vector((0, -1, 0)).rotation_difference(c)
        for v in tmp.verts:
            v.co = rot @ v.co + c * cm(rc - r * 0.12) + Vector((0, 0, cm(z)))
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
    rampa.color_ramp.elements[0].color = hex_lineal("#5a3420")
    rampa.color_ramp.elements[1].color = hex_lineal("#a5703f")
    nt.links.new(onda.outputs["Fac"], rampa.inputs["Fac"])
    nt.links.new(rampa.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.66
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
    """Ramitos de menta'i y cedrón: tallo y hojas simples, para el fondo desenfocado."""
    random.seed(semilla)
    hoja_mat = material_simple("Hoja", "#3f7a2e", 0.45)
    b = next(n for n in hoja_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if "Subsurface Weight" in b.inputs:
        b.inputs["Subsurface Weight"].default_value = 0.2
    obs = []
    for r in range(ramitos):
        bm = bmesh.new()
        base = Vector(centro) + Vector((random.uniform(-0.08, 0.08), random.uniform(-0.05, 0.05), cm(0.3)))
        direc = Vector((random.uniform(-1, 1), random.uniform(-1, 1), 0)).normalized()
        largo = random.uniform(0.12, 0.18)
        tallo = [(base + direc * largo * t + Vector((0, 0, cm(0.25)))) * 100 for t in (0, 0.5, 1)]
        tl = termo.barrido(f"Tallo{r}", termo.catmull(tallo, 6), termo.ovalo(0.12, 0.12, 8), hoja_mat,
                           arriba=Vector((0, 0, 1)))
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


def tapa_en_la_mesa(nombre, pos, giro=0.0):
    """Saca una tapa del termo y la deja parada sobre la mesa (para mostrar la boca ancha abierta)."""
    tapa = bpy.data.objects[nombre]
    termo.ocultar(tapa, False)
    bpy.context.view_layer.update()
    mundo = tapa.matrix_world.copy()
    tapa.parent = None
    base_z = cm(termo.ALTURAS["1L"] + 0.82)
    tapa.matrix_world = Matrix.Translation(Vector(pos)) @ Matrix.Rotation(math.radians(giro), 4, "Z") \
        @ Matrix.Translation((0, 0, -base_z)) @ Matrix.Translation(-mundo.translation) @ mundo
    return tapa


# ---------------------------------------------------------------- escenas
def luces_estudio(alto_obj=0.15):
    luz_area("Clave", (-0.6, -0.6, 0.75), (0, 0, alto_obj), 34, (0.7, 1.1))
    luz_area("Recorte", (0.62, 0.48, 0.6), (0, 0, alto_obj + 0.02), 30, (0.25, 1.0))
    luz_area("Relleno", (0.75, -0.65, 0.22), (0, 0, alto_obj), 7, (1.2, 1.2))
    luz_area("Techo", (0.0, 0.0, 0.95), (0, 0, 0.2), 10, (0.8, 0.8))


def escena_estudio(color, calidad, tapa="pico"):
    """Fondo transparente con sombra de contacto: la grilla de colores, el visor y la portada."""
    termo.limpiar_escena()
    sc = preparar(1200, 1500, calidad, transparente=True, exposicion=-1.15, fiel=True)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", tapa)
    raiz.rotation_euler.z = math.radians(-16)
    ciclorama("#e9e4de", captador=True)
    mundo_hdri("studio_small_09_1k.hdr", 0.35, rotacion=40, visible=False)
    luces_estudio()
    # encuadre ajustado: el termo ocupa ~78 % del alto (en la portada va dentro de un círculo)
    camara((0.0, -0.84, 0.23), (0.012, 0, 0.147), lente=75)
    return sc, f"estudio-{color}"


def escena_referencia(color, calidad, vista, tapa="pico", boca_abierta=False):
    """Referencias limpias para Buzzy: fondo gris neutro, luz pareja, varios ángulos y colores."""
    termo.limpiar_escena()
    sc = preparar(1200, 1500, calidad, exposicion=-1.75, fiel=True)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", tapa, boca_abierta=boca_abierta)
    giros = {"frente": 0, "tres-cuartos": -32, "perfil-manija": -90, "atras": 145, "arriba": -25}
    raiz.rotation_euler.z = math.radians(giros[vista])
    ciclorama("#d7d4cf")
    mundo_hdri("studio_small_09_1k.hdr", 0.45, rotacion=40, visible=False)
    luces_estudio()
    if vista == "arriba":
        camara((0.0, -0.45, 0.55), (0.0, 0, 0.2), lente=75)
    elif tapa in ("clasica", "mate"):
        # la tapa vaso es 4,5 cm más alta y la bombilla de la versión mate asoma otros 4: más aire arriba
        camara((0.0, -0.96, 0.28), (0.008, 0, 0.17), lente=75)
    else:
        camara((0.0, -0.84, 0.25), (0.008 if vista != "perfil-manija" else 0.025, 0, 0.145), lente=75)
    if boca_abierta:
        hielo_en_termo(termo.ALTURAS["1L"])
    nombre = f"ref-{color}-{vista}" + (f"-{tapa}" if tapa != "pico" else "") + ("-boca-abierta" if boca_abierta else "")
    return sc, nombre


def escena_referencia_guampa(calidad):
    """Guampa y bombilla solas, con la bombilla afuera para que se vea el filtro."""
    termo.limpiar_escena()
    sc = preparar(1500, 1200, calidad, exposicion=-1.75, fiel=True)
    mats = termo.materiales("#e0518d")
    g = guampa(mats, pos=(0.0, 0.03, 0), giro=20, con_bombilla=False)
    # la bombilla acostada adelante, de izquierda a derecha: el filtro a la izquierda, el pico a la derecha
    bom = termo.bombilla("BombillaSuelta", mats["acero"], largo=17.0)
    bom.rotation_euler = (math.radians(90), 0, math.radians(80))
    bom.location = (-0.07, -0.05, cm(0.62))
    ciclorama("#d7d4cf")
    mundo_hdri("studio_small_09_1k.hdr", 0.45, rotacion=40, visible=False)
    luces_estudio(0.05)
    camara((0.025, -0.46, 0.26), (0.025, -0.02, 0.035), lente=58)
    return sc, "ref-guampa-y-bombilla"


def escena_hero(calidad, color="lapacho"):
    """Mediodía de enero: el termo transpirando, el pico abierto, la guampa al lado y hielo suelto
    cerca del termo (no en la guampa)."""
    termo.limpiar_escena()
    sc = preparar(1920, 1200, calidad, exposicion=-0.3)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", "pico")
    raiz.rotation_euler.z = math.radians(-22)
    gotas(termo.ALTURAS["1L"], mats["pintura"]).parent = raiz
    ciclorama("#ff5f1f")
    guampa(mats, pos=(0.135, -0.09, 0), giro=200)
    cubos_hielo([(-0.098, -0.105, cm(0.95)), (-0.072, -0.135, cm(0.9)), (-0.118, -0.075, cm(0.92))], lado=2.0, semilla=21)
    mundo_hdri("studio_small_09_1k.hdr", 0.35, rotacion=120, visible=False)
    luz_sol(5.0, elevacion=60, azimut=-40, angulo=0.9)
    luz_area("Rebote", (0.4, -0.7, 0.12), (0.05, 0, 0.14), 18, (1.5, 1.0), color=(1.0, 0.85, 0.75))
    camara((0.04, -0.92, 0.23), (0.03, 0, 0.142), lente=52)
    return sc, f"hero-{color}"


def escena_macro(calidad, color="parana", detalle="grabado"):
    """Dos detalles: el sol grabado con luz rasante (se ven las paredes del corte) y el pico cebador."""
    termo.limpiar_escena()
    sc = preparar(1600, 1200, calidad, exposicion=-0.3)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", "pico")
    ciclorama("#0f1d26")
    mundo_hdri("studio_small_09_1k.hdr", 0.8, rotacion=200, visible=False)
    foco = bpy.data.objects.new("Foco", None)
    bpy.context.scene.collection.objects.link(foco)
    zs = termo.z_sol(termo.ALTURAS["1L"])
    if detalle == "grabado":
        raiz.rotation_euler.z = math.radians(10)
        luz_area("Rasante", (-0.32, -0.12, cm(zs + 3)), (0, 0, cm(zs - 1)), 22, (0.08, 0.5))
        luz_area("Recorte", (0.3, 0.2, 0.3), (0, 0, 0.14), 25, (0.15, 0.6))
        luz_area("Relleno", (0.1, -0.5, 0.15), (0, 0, 0.13), 4, (0.8, 0.8))
        foco.location = (cm(-0.8), cm(-4.7), cm(zs - 1.2))
        camara((-0.03, -0.30, cm(zs + 1.5)), (cm(-0.8), 0, cm(zs - 1.3)), lente=100, desenfoque=(foco, 3.5))
    else:
        raiz.rotation_euler.z = math.radians(-20)
        top = termo.ALTURAS["1L"] + 3.7
        luz_area("Clave", (-0.3, -0.25, cm(top + 22)), (0, 0, cm(top)), 14, (0.3, 0.3))
        luz_area("Recorte", (0.25, 0.3, cm(top + 15)), (0, 0, cm(top)), 30, (0.15, 0.5))
        foco.location = (cm(-1.9), cm(-0.4), cm(top + 0.6))
        camara((-0.17, -0.22, cm(top + 11)), (cm(-1.0), 0, cm(top - 0.2)), lente=100, desenfoque=(foco, 4.5))
    return sc, f"macro-{detalle}"


def escena_ambiente(calidad, color="monte"):
    """Mesa al aire libre: el termo con la boca ancha abierta y cargado de hielo, la tapa al lado,
    la guampa con la bombilla y yuyos desenfocados."""
    termo.limpiar_escena()
    sc = preparar(1800, 1200, calidad, exposicion=0.1)
    random.seed(5)
    raiz, mats = termo.construir(termo.VARIANTES[color], "1L", "pico", boca_abierta=True)
    raiz.rotation_euler.z = math.radians(-26)
    gotas(termo.ALTURAS["1L"], mats["pintura"], cantidad=420).parent = raiz
    hielo_en_termo(termo.ALTURAS["1L"])
    tapa_en_la_mesa("Tapa_Pico", (-0.115, -0.05, 0), giro=70)
    mesa_madera()
    guampa(mats, pos=(0.15, -0.03, 0), giro=160)
    yuyos((-0.18, 0.08, 0), ramitos=3)
    yuyos((0.28, 0.05, 0), semilla=31, ramitos=2)
    mundo_hdri("noon_grass_2k.hdr", 1.0, rotacion=60, visible=True)
    foco = bpy.data.objects.new("Foco", None)
    bpy.context.scene.collection.objects.link(foco)
    foco.location = (0, -cm(5), cm(13))
    camara((0.12, -0.95, 0.36), (0.02, 0, 0.13), lente=60, desenfoque=(foco, 3.2))
    return sc, f"ambiente-{color}"


def renderizar(sc, nombre, calidad, carpeta=None):
    destino_dir = carpeta or SALIDA
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / f"{nombre}{'-boceto' if calidad == 'boceto' else ''}.png"
    sc.render.filepath = str(destino)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"RENDER {destino.name} {time.time() - t:.1f}s", flush=True)


REFERENCIAS = AQUI.parent.parent.parent.parent / "Audiovisual" / "editor-video" / "referencias-kuarahy"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--escena", default="todas",
                   choices=["estudio", "hero", "macro", "ambiente", "referencias", "todas"])
    p.add_argument("--color", default="todos", choices=["todos", *termo.VARIANTES])
    p.add_argument("--calidad", default="boceto", choices=list(CALIDADES))
    p.add_argument("--muestras", type=int, default=0, help="pisa las muestras de la calidad elegida")
    a = p.parse_args(argv)
    colores = list(termo.VARIANTES) if a.color == "todos" else [a.color]

    def r(escena, carpeta=None):
        sc, nombre = escena
        if a.muestras:
            sc.cycles.samples = a.muestras
        renderizar(sc, nombre, a.calidad, carpeta)

    if a.escena in ("hero", "todas"):
        r(escena_hero(a.calidad))
    if a.escena in ("macro", "todas"):
        r(escena_macro(a.calidad, detalle="grabado"))
        r(escena_macro(a.calidad, detalle="pico"))
    if a.escena in ("ambiente", "todas"):
        r(escena_ambiente(a.calidad))
    if a.escena in ("estudio", "todas"):
        for c in colores:
            r(escena_estudio(c, a.calidad))
    if a.escena == "referencias":
        for c in colores:
            for vista in ("frente", "tres-cuartos", "perfil-manija", "atras", "arriba"):
                r(escena_referencia(c, a.calidad, vista), REFERENCIAS)
        r(escena_referencia("lapacho", a.calidad, "tres-cuartos", tapa="clasica"), REFERENCIAS)
        r(escena_referencia("carbon", a.calidad, "tres-cuartos", tapa="mate"), REFERENCIAS)
        r(escena_referencia("parana", a.calidad, "arriba", boca_abierta=True), REFERENCIAS)
        r(escena_referencia_guampa(a.calidad), REFERENCIAS)


if __name__ == "__main__":
    main()
