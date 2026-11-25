"""
Kuarahy · el termo modelado por código (Blender 5.x, bpy + bmesh). Versión 3: diseño industrial.

Un solo modelo para todo: este módulo construye el termo y lo usan
  - exportar.py → kuarahy.glb (web, React Three Fiber) y los GLB de realidad aumentada
  - render.py   → fotos de producto con Cycles y referencias limpias para Buzzy
  - el video de Remotion, que carga el mismo GLB.

Unidades: metros (como glTF). Z hacia arriba, el frente (logo) mira a -Y, la manija va en +X.
Todas las medidas de diseño están en centímetros y se convierten con cm().

Decisiones de diseño (pensando en termos reales de 1 a 1,5 L, sin copiar ninguno):
  - Proporción de termo, no de jarro: 9,4 cm de diámetro y 30 cm de alto (1 L), 38 cm (1,5 L).
  - Base 5 % más ancha que el cuerpo y hombro suave hasta el cuello: estable lleno y sobre el pasto.
  - Manija para toda la mano: agarre vertical de 11,5 cm con goma estriada, 2,9 cm de luz para los
    dedos, tomada con dos aros (uno en el cuello y otro en el cuerpo) en vez de pegada a la pintura.
  - Argolla de acero arriba de la manija, para colgarlo de la mochila o del alambrado de la cancha.
  - Tres tapas: pico cebador (tapita abatible con bisagra a la vista y labio cortagotas), vaso
    (la tapa clásica de los termos de viaje, que sirve de vaso) y mate (vaso con la bombilla guardada).
  - Boca ancha de 6,6 cm: la tapa se desenrosca entera para cargar hielo.
  - Todos los cantos llevan un radio real (0,3 a 4 mm): no hay aristas perfectas de CG.

Piezas (nombres que usa la web para encontrar cada nodo):
  Base, Cuerpo_1L, Cuerpo_15L, Manija_1L, Manija_15L, Logo_1L, Logo_15L, Nombre_1L, Nombre_15L,
  Superior (vacío) → Collar, Tapa_Clasica, Tapa_Pico, Tapa_Mate   (Rosca solo con la boca abierta)
"""
import math
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

AQUI = Path(__file__).resolve().parent
FUENTE = AQUI / "assets" / "BricolageGrotesque-ExtraBold.ttf"

# ---------------------------------------------------------------- medidas (cm)
R = 4.7                      # radio del cuerpo pintado en la parte recta
R_BASE = 4.95                # radio de la base de acero (más ancha: estabilidad)
R_CUELLO = 3.8               # radio del collar de acero
ALTURAS = {"1L": 23.0, "15L": 31.0}   # altura del cuello (donde arranca el collar)
SEGMENTOS = 112              # resolución de la revolución
FACTOR_WEB = 1.0             # construir(para_web=True) lo baja: las piezas lisas no necesitan tantos lados en la web

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


def suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- perfiles con radios reales
def filetear(puntos, radio_def=0.06, pasos=4):
    """Redondea cada esquina de una polilínea 2D (r, z[, radio]) con un arco tangente.
    Así ningún canto queda vivo: el radio por defecto es 0,6 mm."""
    pts = [(p[0], p[1]) for p in puntos]
    radios = [p[2] if len(p) > 2 else radio_def for p in puntos]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[i + 1])
        u, v = a - b, c - b
        if u.length < 1e-6 or v.length < 1e-6 or radios[i] <= 0:
            out.append(pts[i])
            continue
        un, vn = u.normalized(), v.normalized()
        ang = un.angle(vn)
        if ang > math.radians(176):           # casi recto: no hace falta
            out.append(pts[i])
            continue
        t = radios[i] / math.tan(ang / 2)
        t = min(t, 0.45 * u.length, 0.45 * v.length)
        r_eff = t * math.tan(ang / 2)
        p1, p2 = b + un * t, b + vn * t
        bis = (un + vn).normalized()
        centro = b + bis * (r_eff / math.sin(ang / 2))
        a1 = math.atan2(p1.y - centro.y, p1.x - centro.x)
        a2 = math.atan2(p2.y - centro.y, p2.x - centro.x)
        d = (a2 - a1 + math.pi) % math.tau - math.pi
        for k in range(pasos + 1):
            aa = a1 + d * k / pasos
            out.append((centro.x + r_eff * math.cos(aa), centro.y + r_eff * math.sin(aa)))
    out.append(pts[-1])
    return out


def bezier(p0, p1, p2, p3, pasos=12):
    pts = []
    for i in range(pasos + 1):
        t = i / pasos
        m = 1 - t
        pts.append((m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
                    m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]))
    return pts


def arco(cx, cz, r, a0, a1, pasos=8):
    """Puntos de un arco en el plano (radio, z), ángulos en grados."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / pasos)),
             cz + r * math.sin(math.radians(a0 + (a1 - a0) * i / pasos))) for i in range(pasos + 1)]


# ---------------------------------------------------------------- utilidades de malla
def malla_a_objeto(nombre, bm, material=None, suave_=True, angulo_filo=40):
    """Convierte un bmesh en objeto: sombreado suave y filos marcados por ángulo."""
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=cm(0.0008))
    bm.normal_update()
    limite = math.radians(angulo_filo)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > limite:
            e.smooth = False
    for f in bm.faces:
        f.smooth = suave_
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def revolucion(nombre, perfil, material=None, segmentos=SEGMENTOS, angulo_filo=40, deformar=None):
    """Gira un perfil [(radio_cm, z_cm), ...] alrededor de Z. Un radio 0 cierra el polo.
    deformar(v) puede mover los vértices (en cm) antes de pasar a metros: estrías, óvalos, etc."""
    if deformar is None:
        segmentos = max(16, int(segmentos * FACTOR_WEB))
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in perfil]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   steps=segmentos, angle=math.tau, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0002)
    if deformar:
        for v in bm.verts:
            deformar(v)
    for v in bm.verts:
        v.co *= 0.01
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return malla_a_objeto(nombre, bm, material, angulo_filo=angulo_filo)


def catmull(puntos, pasos=8):
    """Curva suave que pasa por todos los puntos (Catmull-Rom)."""
    P = [Vector(p) for p in puntos]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(pasos):
            t = k / pasos
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out


def barrido(nombre, centro, seccion, material=None, cerrado=False, tapas=True, angulo_filo=60, arriba=Vector((0, 1, 0))):
    """Barre una sección cerrada a lo largo de una curva (lista de Vector en cm).
    seccion(t) devuelve [(a, b), ...]: a lo largo de la normal en el plano de la curva y b a lo largo de 'arriba'.
    Sirve para la manija (sección ovalada), la cinta de la argolla y la bombilla (pico aplastado)."""
    bm = bmesh.new()
    n = len(centro)
    anillos = []
    for i, p in enumerate(centro):
        if cerrado:
            tan = (centro[(i + 1) % n] - centro[i - 1]).normalized()
        else:
            tan = (centro[min(i + 1, n - 1)] - centro[max(i - 1, 0)]).normalized()
        b = arriba - tan * arriba.dot(tan)
        b = b.normalized() if b.length > 1e-6 else Vector((0, 0, 1))
        a = tan.cross(b).normalized()
        t = i / (n - 1) if n > 1 else 0
        anillos.append([bm.verts.new(p + a * x + b * y) for x, y in seccion(t)])
    m = len(anillos[0])
    lim = n if cerrado else n - 1
    for i in range(lim):
        r0, r1 = anillos[i], anillos[(i + 1) % n]
        for j in range(m):
            bm.faces.new((r0[j], r0[(j + 1) % m], r1[(j + 1) % m], r1[j]))
    if tapas and not cerrado:
        for anillo, inv in ((anillos[0], True), (anillos[-1], False)):
            c = bm.verts.new(sum((v.co for v in anillo), Vector()) / m)
            for j in range(m):
                tri = (c, anillo[(j + 1) % m], anillo[j]) if inv else (c, anillo[j], anillo[(j + 1) % m])
                bm.faces.new(tri)
    for v in bm.verts:
        v.co *= 0.01
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return malla_a_objeto(nombre, bm, material, angulo_filo=angulo_filo)


def ovalo(ra, rb, n=20):
    return lambda t: [(ra * math.cos(math.tau * k / n), rb * math.sin(math.tau * k / n)) for k in range(n)]


def rectangulo_redondeado(ancho, alto, radio, n_esq=4):
    """Sección de una cinta o un brazo: rectángulo con esquinas redondeadas (cm)."""
    pts = []
    for cx, cy, a0 in ((ancho / 2 - radio, alto / 2 - radio, 0), (-ancho / 2 + radio, alto / 2 - radio, 90),
                       (-ancho / 2 + radio, -alto / 2 + radio, 180), (ancho / 2 - radio, -alto / 2 + radio, 270)):
        for k in range(n_esq + 1):
            a = math.radians(a0 + 90 * k / n_esq)
            pts.append((cx + radio * math.cos(a), cy + radio * math.sin(a)))
    return lambda t: pts


# ---------------------------------------------------------------- materiales
def nodo_principled(mat):
    if hasattr(mat, "use_nodes"):
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
    """Pintura en polvo: cáscara de naranja finita en el relieve y brillo apenas irregular."""
    m = bpy.data.materials.new("Pintura")
    nt, b = nodo_principled(m)
    b.inputs["Base Color"].default_value = hex_lineal(color_hex)
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Roughness"].default_value = 0.5
    if c := entrada(b, "Coat Weight"):
        c.default_value = 0.0 if para_web else 0.1
    if para_web:
        return m
    coord = nt.nodes.new("ShaderNodeTexCoord")
    grano = nt.nodes.new("ShaderNodeTexNoise")          # cáscara de naranja (~0,4 mm)
    grano.inputs["Scale"].default_value = 700.0
    grano.inputs["Detail"].default_value = 3.0
    rel = nt.nodes.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = 0.08
    rel.inputs["Distance"].default_value = 0.00025
    nt.links.new(coord.outputs["Object"], grano.inputs["Vector"])
    nt.links.new(grano.outputs["Fac"], rel.inputs["Height"])
    nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    # manchas muy suaves de uso (huellas): la rugosidad varía entre 0,44 y 0,58
    mancha = nt.nodes.new("ShaderNodeTexNoise")
    mancha.inputs["Scale"].default_value = 9.0
    mancha.inputs["Detail"].default_value = 4.0
    rango = nt.nodes.new("ShaderNodeMapRange")
    rango.inputs["To Min"].default_value = 0.44
    rango.inputs["To Max"].default_value = 0.58
    nt.links.new(coord.outputs["Object"], mancha.inputs["Vector"])
    nt.links.new(mancha.outputs["Fac"], rango.inputs["Value"])
    nt.links.new(rango.outputs["Result"], b.inputs["Roughness"])
    return m


def material_acero(nombre="Acero", rugosidad=0.26, para_web=False, color="#cfd3d7"):
    """Acero inoxidable cepillado en anillos (anisotropía radial alrededor de Z)."""
    m = bpy.data.materials.new(nombre)
    nt, b = nodo_principled(m)
    b.inputs["Base Color"].default_value = hex_lineal(color)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rugosidad
    if para_web:
        return m
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapeo = nt.nodes.new("ShaderNodeMapping")
    mapeo.inputs["Scale"].default_value = (5.0, 5.0, 1400.0)   # rayas finas alrededor del termo
    ruido = nt.nodes.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 4.0
    ruido.inputs["Detail"].default_value = 6.0
    rampa = nt.nodes.new("ShaderNodeMapRange")
    rampa.inputs["To Min"].default_value = rugosidad - 0.06
    rampa.inputs["To Max"].default_value = rugosidad + 0.08
    nt.links.new(coord.outputs["Object"], mapeo.inputs["Vector"])
    nt.links.new(mapeo.outputs["Vector"], ruido.inputs["Vector"])
    nt.links.new(ruido.outputs["Fac"], rampa.inputs["Value"])
    nt.links.new(rampa.outputs["Result"], b.inputs["Roughness"])
    rel = nt.nodes.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = 0.04
    rel.inputs["Distance"].default_value = 0.00005
    nt.links.new(ruido.outputs["Fac"], rel.inputs["Height"])
    nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    if a := entrada(b, "Anisotropic"):
        a.default_value = 0.6
        tang = nt.nodes.new("ShaderNodeTangent")
        tang.direction_type = "RADIAL"
        tang.axis = "Z"
        if t := entrada(b, "Tangent"):
            nt.links.new(tang.outputs["Tangent"], t)
    return m


def material_goma(para_web, nombre="Goma", color="#1d1d1f", rugosidad=0.78):
    m = bpy.data.materials.new(nombre)
    nt, b = nodo_principled(m)
    b.inputs["Base Color"].default_value = hex_lineal(color)
    b.inputs["Roughness"].default_value = rugosidad
    if c := entrada(b, "Specular IOR Level"):
        c.default_value = 0.35
    if not para_web:
        grano = nt.nodes.new("ShaderNodeTexNoise")       # goma mate con textura de molde
        grano.inputs["Scale"].default_value = 2500.0
        rel = nt.nodes.new("ShaderNodeBump")
        rel.inputs["Strength"].default_value = 0.15
        nt.links.new(grano.outputs["Fac"], rel.inputs["Height"])
        nt.links.new(rel.outputs["Normal"], b.inputs["Normal"])
    return m


def materiales(color_hex="#e0518d", para_web=False):
    return {
        "pintura": material_pintura(color_hex, para_web),
        "acero": material_acero("Acero", 0.22, para_web),
        "grabado": material_acero("Grabado", 0.36, para_web, color="#d9dde1"),
        "goma": material_goma(para_web),
        "nombre": material_acero("Nombre", 0.42, True),
    }


# ---------------------------------------------------------------- cuerpo
def r_cuerpo(z, alto):
    """Radio de la pintura a la altura z: base ensanchada, tramo recto y hombro suave."""
    if z < 6.5:
        return R + 0.2 * (1 - suave((z - 1.4) / 5.1))
    return R


def base(mats):
    """Fondo de acero con canto redondeado y pie de goma: más ancho que el cuerpo."""
    perfil = filetear([(0, 0.18), (4.2, 0.18, 0.05), (4.55, 0.02, 0.15), (R_BASE - 0.05, 0.1, 0.3),
                       (R_BASE, 0.9, 0.12), (R_BASE - 0.06, 1.48, 0.06), (4.86, 1.52, 0.03), (0, 1.52)], pasos=5)
    ob = revolucion("Base", perfil, mats["acero"])
    pie = revolucion("Base_Pie", filetear([(0, 0.0), (4.05, 0.0, 0.08), (4.2, 0.2, 0.05), (0, 0.2)]), mats["goma"],
                     segmentos=72)
    pie.parent = ob
    return ob


def cuerpo(nombre, alto, mats):
    """Cuerpo pintado: nace dentro de la base, se ensancha abajo, sube recto y cierra en un hombro suave."""
    h = alto
    perfil = [(0, 1.2), (4.88, 1.2)]
    perfil += [(r_cuerpo(z, h), z) for z in (1.42, 2.2, 3.0, 4.0, 5.0, 6.5)]
    perfil += [(R, z) for z in (h * 0.4, h * 0.7, h - 4.6)]
    perfil += bezier((R, h - 4.6), (R, h - 2.3), (R_CUELLO + 0.35, h - 1.0), (R_CUELLO + 0.02, h - 0.35), 16)[1:]
    perfil += filetear([(R_CUELLO + 0.02, h - 0.35), (R_CUELLO - 0.05, h - 0.2, 0.08), (3.5, h - 0.2), (3.5, h + 0.2),
                        (0, h + 0.2)])[1:]
    return revolucion(nombre, perfil, mats["pintura"])


def collar(alto, mats):
    """Aro de acero del cuello, con la rosca de la boca ancha. La unión con la pintura queda
    marcada por un labio fino, como en un termo de verdad."""
    h = alto
    perfil = filetear([(3.55, h - 0.5), (R_CUELLO + 0.02, h - 0.5, 0.05), (R_CUELLO + 0.06, h - 0.32, 0.08),
                       (R_CUELLO + 0.06, h + 0.62, 0.1), (R_CUELLO - 0.06, h + 0.78, 0.06), (3.42, h + 0.78, 0.04),
                       (3.42, h + 0.2)], pasos=5)
    return revolucion("Collar", perfil, mats["acero"])


def rosca(alto, mats):
    """Cuello con rosca (se ve con la tapa sacada) y el interior de acero de la boca ancha."""
    h = alto + 0.78
    bm = bmesh.new()
    # cuello cilíndrico interior y el borde de la boca
    perfil = filetear([(2.6, h - 9.0), (3.28, h - 9.0), (3.28, h + 1.5, 0.08), (3.36, h + 1.62, 0.05),
                       (3.2, h + 1.62, 0.05), (3.12, h + 1.5), (3.12, h - 9.0)])
    ob = revolucion("Rosca", perfil, mats["acero"], segmentos=96)
    # filete helicoidal: dos vueltas de rosca trapezoidal
    pasos = 160
    vueltas = 2.0
    paso_z = 0.42
    seccion = [(0.0, -0.11), (0.16, -0.05), (0.16, 0.05), (0.0, 0.11)]
    anillos = []
    for i in range(pasos + 1):
        t = i / pasos
        a = math.tau * vueltas * t
        z = h + 0.15 + paso_z * vueltas * t
        rad = Vector((math.cos(a), math.sin(a), 0))
        escala = suave(min(t, 1 - t) * 12)        # la rosca nace y muere en punta
        anillos.append([bm.verts.new(rad * (3.28 + dx * escala) + Vector((0, 0, z + dz * max(escala, 0.2))))
                        for dx, dz in seccion])
    for i in range(pasos):
        for j in range(3):
            bm.faces.new((anillos[i][j], anillos[i][j + 1], anillos[i + 1][j + 1], anillos[i + 1][j]))
    for v in bm.verts:
        v.co *= 0.01
    filete = malla_a_objeto("Rosca_Filete", bm, mats["acero"], angulo_filo=50)
    filete.parent = ob
    return ob


# ---------------------------------------------------------------- tapas
def _tapa_rosca(nombre, base_z, alto, mats, estrias=True):
    """Tapa de rosca de acero con estrías verticales para agarrarla con la mano mojada."""
    b = base_z
    perfil = filetear([(3.5, b + 0.04), (3.9, b + 0.04, 0.12), (3.93, b + alto - 0.5, 0.45), (2.4, b + alto, 0.3),
                       (0, b + alto)], pasos=6)

    def estriar(v):
        r = math.hypot(v.co.x, v.co.y)
        if r < 3.6 or not (b + 0.35 < v.co.z < b + alto - 0.55):
            return
        a = math.atan2(v.co.y, v.co.x)
        k = suave((v.co.z - b - 0.35) / 0.25) * suave((b + alto - 0.55 - v.co.z) / 0.25)
        d = -0.07 * k * (0.5 + 0.5 * math.cos(48 * a)) ** 3
        v.co.x *= (r + d) / r
        v.co.y *= (r + d) / r

    tapa = revolucion(nombre, perfil, mats["acero"], segmentos=192 if estrias else SEGMENTOS,
                      deformar=estriar if estrias else None, angulo_filo=70)
    # junta de goma: la costura entre tapa y collar
    junta = revolucion(f"{nombre}_Junta", filetear([(3.55, b - 0.04), (3.86, b - 0.04, 0.03), (3.86, b + 0.06, 0.03),
                                                    (3.55, b + 0.06)]), mats["goma"], segmentos=72)
    junta.parent = tapa
    return tapa


def tapa_pico(alto, mats, abierta=True):
    """Tapa con pico cebador: el pico tiene un labio cortagotas (el agua se corta limpia y no chorrea
    por afuera) y una tapita abatible con bisagra de tres nudillos a la vista."""
    b = alto + 0.82
    tapa = _tapa_rosca("Tapa_Pico", b, 2.9, mats)
    top = b + 2.9
    # pico: sale del borde del lado opuesto a la manija, inclinado hacia afuera
    pico_pos = Vector((-2.05, 0.0, top - 0.25))
    inclinacion = math.radians(-30)
    perfil = filetear([(0, -0.6), (1.25, -0.6), (1.2, 0.0, 0.35), (0.78, 1.1, 0.3), (0.66, 1.62, 0.04),
                       (0.74, 1.74, 0.02), (0.7, 1.86, 0.03), (0.46, 1.86, 0.03), (0.44, 1.2), (0.44, 0.2), (0, 0.2)],
                      pasos=4)

    def boca_al_bies(v):
        # boca ovalada y cortada al bies: el labio de afuera queda más bajo para cortar el chorro
        v.co.y *= 0.86
        if v.co.z > 1.5:
            v.co.z -= 0.16 * (-v.co.x / 0.74)

    pico = revolucion("Tapa_Pico_Tubo", perfil, mats["acero"], segmentos=56, angulo_filo=55, deformar=boca_al_bies)
    pico.rotation_euler = (0, inclinacion, 0)
    pico.location = pico_pos * 0.01
    pico.parent = tapa

    # bisagra: tres nudillos sobre la tapa, entre el pico y el centro, con el perno a la vista
    eje = Vector((-0.55, 0.0, top + 0.3))
    for i, (y0, y1, mat) in enumerate(((-1.0, -0.38, "acero"), (-0.32, 0.32, "goma"), (0.38, 1.0, "acero"))):
        nud = revolucion(f"Tapa_Pico_Nudillo{i}", filetear([(0, y0), (0.3, y0, 0.06), (0.3, y1, 0.06), (0, y1)]),
                         mats[mat], segmentos=28)
        nud.rotation_euler = (math.radians(90), 0, 0)
        nud.location = eje * 0.01
        nud.parent = tapa
    for s in (-1, 1):
        perno = revolucion(f"Tapa_Pico_Perno{s}", filetear([(0, 0), (0.13, 0, 0.03), (0.13, 0.08, 0.03), (0, 0.1)]),
                           mats["acero"], segmentos=16)
        perno.rotation_euler = (math.radians(-90 * s), 0, 0)
        perno.location = (eje + Vector((0, s * 1.0, 0))) * 0.01
        perno.parent = tapa
    soporte = revolucion("Tapa_Pico_Soporte", filetear([(0, top - 0.05), (1.15, top - 0.05, 0.1), (1.15, top + 0.18, 0.12),
                                                         (0, top + 0.18)]), mats["acero"], segmentos=48)
    soporte.scale = (0.75, 1.0, 1.0)
    soporte.location = (cm(-0.55), 0, 0)
    soporte.parent = tapa

    # tapita de goma: capuchón que calza sobre el pico, unido al nudillo del medio por un brazo
    cap = revolucion("Tapa_Pico_Tapita", filetear([(0, 2.25), (0.92, 2.25, 0.25), (0.98, 1.0, 0.05), (0.84, 0.95, 0.05),
                                                   (0.8, 1.9), (0.5, 1.92, 0.04), (0.47, 1.5, 0.05), (0, 1.48)], pasos=4),
                     mats["goma"], segmentos=40,
                     deformar=lambda v: setattr(v.co, "y", v.co.y * 0.9))
    # el brazo baja por el costado del capuchón hasta el nudillo del medio (en coordenadas del pico)
    brazo = barrido("Tapa_Pico_Brazo", catmull([Vector((0.9, 0, 1.7)), Vector((1.3, 0, 0.9)), Vector((1.57, 0, -0.1))], 6),
                    rectangulo_redondeado(0.22, 0.6, 0.08), mats["goma"])
    pestana = barrido("Tapa_Pico_Pestana", [Vector((-0.8, 0, 2.0)), Vector((-1.35, 0, 2.15))],
                      rectangulo_redondeado(0.2, 1.1, 0.08), mats["goma"])
    # la tapita se arma cerrada sobre el pico y se gira alrededor del eje de la bisagra
    grupo = bpy.data.objects.new("Tapa_Pico_Tapita_Grupo", None)
    bpy.context.scene.collection.objects.link(grupo)
    for p in (cap, brazo, pestana):
        p.parent = grupo
    # de coordenadas del pico (eje local Z) a la tapa
    m_pico = Matrix.Translation(pico_pos * 0.01) @ Matrix.Rotation(inclinacion, 4, "Y")
    giro = math.radians(118 if abierta else 0)
    m_eje = Matrix.Translation(eje * 0.01) @ Matrix.Rotation(giro, 4, "Y") @ Matrix.Translation(-eje * 0.01)
    grupo.matrix_world = m_eje @ m_pico
    grupo.parent = tapa
    grupo.matrix_parent_inverse = tapa.matrix_world.inverted()
    return tapa


def tapa_vaso(nombre, alto, mats, con_bombilla=False):
    """Tapa vaso: se desenrosca y sirve de vaso (la tapa clásica de los termos de viaje).
    Pintada del color del termo, con el borde de acero enrollado abajo.
    La versión mate guarda la bombilla adentro: asoma el pico por un pasante de silicona."""
    b = alto + 0.82
    alto_vaso = 7.4
    perfil = filetear([(3.7, b + 0.35), (4.02, b + 0.35, 0.06), (4.08, b + 0.6, 0.2), (3.92, b + alto_vaso - 0.7, 0.2),
                       (3.86, b + alto_vaso - 0.2, 0.55), (2.2, b + alto_vaso, 0.4), (0, b + alto_vaso)], pasos=6)
    vaso = revolucion(nombre, perfil, mats["pintura"])
    borde = revolucion(f"{nombre}_Borde", filetear([(3.7, b + 0.02), (4.06, b + 0.02, 0.1), (4.1, b + 0.2, 0.08),
                                                     (4.1, b + 0.42, 0.06), (4.0, b + 0.46, 0.04), (3.7, b + 0.46)]),
                       mats["acero"])
    borde.parent = vaso
    junta = revolucion(f"{nombre}_Junta", filetear([(3.55, b - 0.04), (3.86, b - 0.04, 0.03), (3.86, b + 0.04, 0.03),
                                                    (3.55, b + 0.04)]), mats["goma"], segmentos=72)
    junta.parent = vaso
    if con_bombilla:
        top = b + alto_vaso
        pasante = revolucion(f"{nombre}_Pasante", filetear([(0, top - 0.05), (0.85, top - 0.05, 0.06),
                                                             (0.85, top + 0.22, 0.12), (0.5, top + 0.3, 0.05),
                                                             (0, top + 0.3)]), mats["goma"], segmentos=40)
        pasante.location = (cm(-1.3), cm(0.6), 0)
        pasante.parent = vaso
        bom = bombilla(f"{nombre}_Bombilla", mats["acero"], largo=17.0, con_filtro=False)
        bom.rotation_euler = (0, 0, math.radians(-90))
        bom.location = (cm(-1.3), cm(0.6), cm(top + 0.4 - 12.4))   # asoman la virola y el pico (4 cm)
        bom.parent = vaso
    return vaso


# ---------------------------------------------------------------- manija y argolla
def manija(nombre, alto, mats):
    """Manija para agarrar con toda la mano: dos aros abrazan el cuello y el cuerpo, un brazo arriba y otro
    abajo, y el agarre vertical lleva una funda de goma estriada. Arriba tiene la argolla para colgarlo."""
    h = alto
    z_arriba = h + 0.15            # aro del cuello
    z_abajo = z_arriba - 16.55     # aro del cuerpo (justo arriba de donde se ensancha la base)
    x_agarre = 8.6                 # 2,9 cm de luz entre el agarre y el cuerpo
    z_g1, z_g0 = z_arriba - 2.2, z_abajo + 1.8   # tramo recto del agarre (11 cm)

    # aros de los anclajes (mismo color que el termo: parece una sola pieza)
    def aro(nom, z, r_int, alto_aro, espesor):
        return revolucion(nom, filetear([(r_int, z - alto_aro / 2), (r_int + espesor, z - alto_aro / 2 + 0.1, 0.1),
                                         (r_int + espesor, z + alto_aro / 2 - 0.1, 0.1), (r_int, z + alto_aro / 2)], pasos=4),
                          mats["pintura"], segmentos=96)

    sup = aro(f"{nombre}_AroCuello", z_arriba, R_CUELLO + 0.06, 0.95, 0.3)
    # el de abajo es fino y con los bordes en chanfle: abraza el cuerpo sin parecer un cinturón
    inf = aro(f"{nombre}_AroCuerpo", z_abajo, R + 0.005, 1.05, 0.2)

    # marco: brazo de arriba → agarre → brazo de abajo, con sección ovalada (más fina de perfil)
    pts = [Vector((R_CUELLO + 0.25, 0, z_arriba)), Vector((5.6, 0, z_arriba + 0.15)), Vector((7.5, 0, z_arriba - 0.3)),
           Vector((x_agarre, 0, z_g1 + 0.3)), Vector((x_agarre + 0.1, 0, (z_g1 + z_g0) / 2)),
           Vector((x_agarre, 0, z_g0 - 0.3)), Vector((7.4, 0, z_abajo + 0.1)), Vector((R + 0.3, 0, z_abajo))]
    centro = catmull(pts, 10)

    def seccion(t):
        # más grueso en el agarre, se afina hacia los anclajes
        g = 0.82 + 0.18 * suave(1 - abs(t - 0.5) * 2.4)
        return [(1.0 * g * math.cos(math.tau * k / 22), 0.78 * g * math.sin(math.tau * k / 22)) for k in range(22)]

    marco = barrido(nombre, centro, seccion, mats["pintura"], arriba=Vector((0, 1, 0)))
    sup.parent = marco
    inf.parent = marco

    # funda de goma del agarre: estrías horizontales (antideslizante), con forma de dedos suave
    largo = z_g1 - z_g0
    perfil = [(0, 0)]
    n = 90
    for i in range(n + 1):
        z = largo * i / n
        borde = suave(z / 0.6) * suave((largo - z) / 0.6)
        dedos = 0.06 * math.sin(math.pi * 4 * z / largo) ** 2          # cuatro huecos para los dedos
        estria = 0.045 * (0.5 + 0.5 * math.cos(math.tau * z / 0.42))
        perfil.append((0.95 + (0.27 + estria - dedos) * borde, z))
    perfil.append((0, largo))
    funda = revolucion(f"{nombre}_Agarre", perfil, mats["goma"], segmentos=40, angulo_filo=80,
                       deformar=lambda v: setattr(v.co, "y", v.co.y * 0.8))
    funda.location = (cm(x_agarre + 0.05), 0, cm(z_g0))
    funda.parent = marco

    # argolla: oreja sobre el brazo de arriba y una D de acero
    arco_oreja = [Vector((6.5 + 0.55 * math.cos(math.pi * k / 10), 0, z_arriba + 0.7 + 1.05 * math.sin(math.pi * k / 10)))
                  for k in range(11)]
    oreja = barrido(f"{nombre}_Oreja", arco_oreja, rectangulo_redondeado(0.5, 0.9, 0.2), mats["pintura"])
    oreja.parent = marco
    # la argolla pasa por la oreja y cae hacia afuera, como cae de verdad cuando el termo está parado
    pivote = Vector((6.5, 0, z_arriba + 1.22))
    caida = Matrix.Rotation(math.radians(62), 3, "Y")
    d_pts = [pivote + caida @ Vector((0, 1.05 * math.sin(math.tau * k / 32), 1.35 * (1 - math.cos(math.tau * k / 32))))
             for k in range(32)]
    argolla = barrido(f"{nombre}_Argolla", d_pts, ovalo(0.16, 0.16, 12), mats["acero"], cerrado=True,
                      arriba=caida @ Vector((1, 0, 0)))
    argolla.parent = marco
    return marco


# ---------------------------------------------------------------- bombilla
def bombilla(nombre, material, largo=17.0, con_filtro=True):
    """Bombilla de acero: caño de 8 mm, virola labrada, pico aplastado y curvado, filtro de resorte.
    Se arma vertical (pico arriba, eje Z), con el filtro en z = 0."""
    radio = 0.4
    recta = largo - 3.0
    centro = [Vector((0, 0, z)) for z in (0.0, recta * 0.33, recta * 0.66, recta)]
    curva = [Vector((0.9 * (1 - math.cos(a)) * 1.6, 0, recta + 2.9 * math.sin(a)))
             for a in (math.radians(x) for x in (12, 24, 36, 48))]
    centro = catmull(centro + curva, 10)

    def seccion(t):
        # en el último 12 %: el pico se aplasta (1,4 × 0,5) para apoyar los labios
        k = suave((t - 0.84) / 0.16)
        ra = radio * (1 - 0.45 * k)
        rb = radio * (1 + 0.85 * k)
        return [(ra * math.cos(math.tau * i / 18), rb * math.sin(math.tau * i / 18)) for i in range(18)]

    bom = barrido(nombre, centro, seccion, material, arriba=Vector((0, 1, 0)))
    # virola labrada a 4 cm del pico
    perfil = [(0, 0)]
    for i in range(21):
        z = 0.8 * i / 20
        perfil.append((radio + 0.16 + 0.05 * math.cos(math.tau * z / 0.2) * suave(z / 0.1) * suave((0.8 - z) / 0.1), z))
    perfil.append((0, 0.8))
    virola = revolucion(f"{nombre}_Virola", filetear(perfil, 0.02), material, segmentos=36, angulo_filo=70)
    virola.location = (0, 0, cm(recta - 1.6))
    virola.parent = bom
    if con_filtro:
        # filtro de resorte: alambre enrollado sobre los últimos 3,2 cm, con tapón abajo
        n = 220
        espiral = [Vector((0.56 * math.cos(math.tau * 14 * i / n), 0.56 * math.sin(math.tau * 14 * i / n), 0.2 + 3.0 * i / n))
                   for i in range(n + 1)]
        resorte = barrido(f"{nombre}_Resorte", espiral, ovalo(0.075, 0.075, 8), material, arriba=Vector((0, 0, 1)))
        resorte.parent = bom
        tapon = revolucion(f"{nombre}_Tapon", filetear([(0, -0.15), (0.62, -0.15, 0.12), (0.62, 0.25, 0.05), (0, 0.25)]),
                           material, segmentos=28)
        tapon.parent = bom
    return bom


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
    n = 32
    c = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new((0.4 * math.cos(math.tau * i / n), 0.4 * math.sin(math.tau * i / n), 0)) for i in range(n)]
    for i in range(n):
        bm.faces.new((c, ring[i], ring[(i + 1) % n]))
    for k in range(12):
        t = math.tau * k / 12
        d = Vector((math.cos(t), math.sin(t), 0))
        p = Vector((-math.sin(t), math.cos(t), 0))
        pts = []
        for i in range(9):
            a = math.pi / 2 + math.pi * i / 8
            pts.append(d * 1.5 + (d * math.cos(a) + p * math.sin(a)) * 0.11)
        for i in range(9):
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
    zs = [v.co.y for v in me.vertices]
    alto = max(zs) - min(zs)
    esc = alto_letra / alto
    off = (max(zs) + min(zs)) / 2
    tmp_bm = bmesh.new()
    tmp_bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    for v in tmp_bm.verts:
        v.co = Vector((v.co.x * esc, (v.co.y - off) * esc, 0))
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


def z_sol(alto):
    # el logo se mide desde el hombro: así nunca lo pisa el aro de abajo de la manija (en 1 L ni en 1,5 L)
    return alto - 8.7


def logo(nombre, alto, mats, cuerpo_ob=None):
    """Sol y KUARAHY grabados con láser: la pintura se va y queda el acero 0,3 mm más abajo.
    Para las fotos se cava el grabado en la pintura con un booleano (se ven las paredes del corte);
    para la web basta con la figura apenas hundida (pesa mucho menos)."""
    bm = bmesh.new()
    _sol_2d(bm)
    bm2 = bmesh.new()
    _texto_2d(bm2, "KUARAHY", 0.64, 1.04)   # más angosto que en v2: el cuerpo es más fino y la K se perdía en la curva
    me = bpy.data.meshes.new("t")
    for v in bm2.verts:
        v.co.y -= 2.85
    bm2.to_mesh(me)
    bm2.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    for v in bm.verts:
        v.co *= 0.01

    if cuerpo_ob is not None:
        # cortador: la figura extruida desde 0,3 mm adentro hasta 1 mm afuera
        cort = bm.copy()
        _envolver(cort, cm(R) - cm(0.03), cm(z_sol(alto)))
        geom = bmesh.ops.extrude_face_region(cort, geom=cort.faces[:])
        for v in (e for e in geom["geom"] if isinstance(e, bmesh.types.BMVert)):
            v.co += Vector((v.co.x, v.co.y, 0)).normalized() * cm(0.13)
        bmesh.ops.recalc_face_normals(cort, faces=cort.faces)
        cortador = malla_a_objeto(f"{nombre}_Cortador", cort, None, suave_=False)
        mod = cuerpo_ob.modifiers.new("Grabado", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.use_self = True          # las letras se tocan con el sol en el cortador: sin esto se pierde la K
        mod.object = cortador
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        nuevo = bpy.data.meshes.new_from_object(cuerpo_ob.evaluated_get(dg))
        cuerpo_ob.modifiers.remove(mod)
        cuerpo_ob.data = nuevo
        bpy.data.objects.remove(cortador, do_unlink=True)
        _envolver(bm, cm(R) - cm(0.028), cm(z_sol(alto)))
        return malla_a_objeto(nombre, bm, mats["grabado"], suave_=True, angulo_filo=89)

    _envolver(bm, cm(R) + cm(0.012), cm(z_sol(alto)))
    geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for v in (e for e in geom["geom"] if isinstance(e, bmesh.types.BMVert)):
        v.co -= Vector((v.co.x, v.co.y, 0)).normalized() * cm(0.03)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return malla_a_objeto(nombre, bm, mats["grabado"], suave_=False)


# ---------------------------------------------------------------- grabado del nombre (personalizador)
NOMBRE_ARCO = 80.0      # grados que cubre la banda del nombre, centrada en el frente
NOMBRE_ALTO = 1.5       # cm


def z_nombre(alto):
    """Centro de la banda del nombre: debajo de KUARAHY."""
    return z_sol(alto) - 2.85 - 2.3


def banda_nombre(nombre, alto, mats):
    """Banda curva con UV 0..1 sobre el frente: la web le pinta el nombre (CanvasTexture)."""
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    n = 32
    r = cm(R + 0.016)
    zc = cm(z_nombre(alto))
    filas = []
    for dz in (-NOMBRE_ALTO / 2, NOMBRE_ALTO / 2):
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


TAPAS = {"clasica": "Tapa_Clasica", "pico": "Tapa_Pico", "mate": "Tapa_Mate"}


def ocultar(ob, si=True):
    for o in [ob, *ob.children_recursive]:
        o.hide_render = si
        o.hide_viewport = si


def construir(color_hex="#e0518d", tamano="1L", tapa="pico", para_web=False, ambos_tamanos=False,
              boca_abierta=False, pico_abierto=True):
    """Arma el termo.
    ambos_tamanos=True (web): incluye los cuerpos de 1 L y 1,5 L y las tres tapas.
    boca_abierta=True (fotos): sin tapa, se ve la rosca y la boca ancha (para el hielo)."""
    global FACTOR_WEB
    FACTOR_WEB = 0.6 if para_web else 1.0
    mats = materiales(color_hex, para_web)
    raiz = bpy.data.objects.new("Kuarahy", None)
    bpy.context.scene.collection.objects.link(raiz)

    tamanos = ["1L", "15L"] if ambos_tamanos else [tamano]
    for t in tamanos:
        h = ALTURAS[t]
        c = cuerpo(f"Cuerpo_{t}", h, mats)
        piezas = [c, manija(f"Manija_{t}", h, mats), logo(f"Logo_{t}", h, mats, None if para_web else c)]
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
    piezas = [collar(h0, mats), tapa_vaso("Tapa_Clasica", h0, mats), tapa_pico(h0, mats, pico_abierto),
              tapa_vaso("Tapa_Mate", h0, mats, con_bombilla=True)]
    if boca_abierta:
        piezas.append(rosca(h0, mats))
    for ob in piezas:
        ob.parent = sup
    if not ambos_tamanos:
        sup.location.z = cm(ALTURAS[tamano] - h0)
        for clave, nombre in TAPAS.items():
            if boca_abierta or clave != tapa:
                ocultar(bpy.data.objects[nombre])
    return raiz, mats


if __name__ == "__main__":
    limpiar_escena()
    construir()
