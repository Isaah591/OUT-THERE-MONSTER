"""Blender side of Experimental Model 01: meshes from numpy, materials, studio, cameras, renders.
Written from scratch for this model (Blender 5 as the `bpy` module, Cycles on the CPU)."""
import math
import numpy as np
import bpy
from mathutils import Vector


# ----------------------------------------------------------------------------- scene / meshes


def new_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    return sc


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def add_mesh(name, data, material=None, smooth=False, coll="ASTRA_R08"):
    """data: dict(V, Q, T, vattr, fattr) as produced by kernel.MeshOut.finish()."""
    V = np.asarray(data["V"], np.float32)
    Q = np.asarray(data.get("Q", np.zeros((0, 4))), np.int32).reshape(-1, 4)
    T = np.asarray(data.get("T", np.zeros((0, 3))), np.int32).reshape(-1, 3)
    me = bpy.data.meshes.new(name)
    nq, nt = len(Q), len(T)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.reshape(-1))
    me.loops.add(nq * 4 + nt * 3)
    me.loops.foreach_set("vertex_index", np.concatenate([Q.reshape(-1), T.reshape(-1)]))
    me.polygons.add(nq + nt)
    starts = np.concatenate([np.arange(nq) * 4, nq * 4 + np.arange(nt) * 3]).astype(np.int32)
    totals = np.concatenate([np.full(nq, 4), np.full(nt, 3)]).astype(np.int32)
    me.polygons.foreach_set("loop_start", starts)
    me.polygons.foreach_set("loop_total", totals)
    me.update(calc_edges=True)
    me.validate(verbose=False)
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(nq + nt, bool))
    for k, a in (data.get("vattr") or {}).items():
        at = me.attributes.new(k, "FLOAT", "POINT")
        at.data.foreach_set("value", np.asarray(a, np.float32))
    for k, a in (data.get("fattr") or {}).items():
        at = me.attributes.new(k, "FLOAT", "FACE")
        at.data.foreach_set("value", np.asarray(a, np.float32))
    ob = bpy.data.objects.new(name, me)
    collection(coll).objects.link(ob)
    if material is not None:
        me.materials.append(material)
    return ob


# ----------------------------------------------------------------------------- node helpers


class NT:
    """Tiny helper for building shader node trees."""

    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.x = 0

    def node(self, kind, **props):
        n = self.nt.nodes.new(kind)
        self.x -= 180
        n.location = (self.x, 0)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def val(self, v):
        n = self.node("ShaderNodeValue")
        n.outputs[0].default_value = v
        return n.outputs[0]

    def rgb(self, c):
        n = self.node("ShaderNodeRGB")
        n.outputs[0].default_value = (c[0], c[1], c[2], 1.0)
        return n.outputs[0]

    def attr(self, name, out="Fac"):
        n = self.node("ShaderNodeAttribute", attribute_name=name)
        return n.outputs[out]

    def _set(self, sock, v):
        if hasattr(v, "is_output") or isinstance(v, bpy.types.NodeSocket):
            self.link(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.node("ShaderNodeMath", operation=op)
        n.use_clamp = clamp
        self._set(n.inputs[0], a)
        if b is not None:
            self._set(n.inputs[1], b)
        if c is not None:
            self._set(n.inputs[2], c)
        return n.outputs[0]

    def sstep(self, e0, e1, x):
        """smoothstep(e0, e1, x); e0 > e1 gives the falling version."""
        n = self.node("ShaderNodeMapRange", interpolation_type="SMOOTHSTEP")
        lo, hi, a, b = (e0, e1, 0.0, 1.0) if e0 <= e1 else (e1, e0, 1.0, 0.0)
        self._set(n.inputs["Value"], x)
        n.inputs["From Min"].default_value = lo
        n.inputs["From Max"].default_value = hi
        n.inputs["To Min"].default_value = a
        n.inputs["To Max"].default_value = b
        return n.outputs["Result"]

    def mix(self, fac, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        ins = {s.identifier: s for s in n.inputs}
        self._set(ins["Factor_Float"], fac)
        for key, v in (("A_Color", a), ("B_Color", b)):
            if isinstance(v, (tuple, list)):
                ins[key].default_value = (v[0], v[1], v[2], 1.0)
            else:
                self.link(v, ins[key])
        return {s.identifier: s for s in n.outputs}["Result_Color"]

    def mixf(self, fac, a, b):
        n = self.node("ShaderNodeMix", data_type="FLOAT")
        ins = {s.identifier: s for s in n.inputs}
        self._set(ins["Factor_Float"], fac)
        self._set(ins["A_Float"], a)
        self._set(ins["B_Float"], b)
        return {s.identifier: s for s in n.outputs}["Result_Float"]

    def ramp(self, fac, stops, interp="LINEAR"):
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for e, (p, c) in zip(cr.elements, stops):
            e.position = p
            e.color = (c[0], c[1], c[2], 1.0)
        self._set(n.inputs[0], fac)
        return n.outputs[0]

    def coords(self, scale=(1, 1, 1), obj=True):
        tc = self.node("ShaderNodeTexCoord")
        mp = self.node("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        self.link(tc.outputs["Object" if obj else "Generated"], mp.inputs["Vector"])
        return mp.outputs["Vector"]

    def noise(self, vec, scale, detail=3.0, rough=0.55, out="Fac"):
        n = self.node("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        if vec is not None:
            self.link(vec, n.inputs["Vector"])
        return n.outputs[out]

    def voronoi(self, vec, scale, feature="F1", out="Distance", rand=1.0):
        n = self.node("ShaderNodeTexVoronoi", feature=feature)
        n.inputs["Scale"].default_value = scale
        n.inputs["Randomness"].default_value = rand
        if vec is not None:
            self.link(vec, n.inputs["Vector"])
        return n.outputs[out]

    def bump(self, height, strength=0.3, dist=0.01, normal=None):
        n = self.node("ShaderNodeBump")
        n.inputs["Strength"].default_value = strength
        n.inputs["Distance"].default_value = dist
        self.link(height, n.inputs["Height"])
        if normal is not None:
            self.link(normal, n.inputs["Normal"])
        return n.outputs["Normal"]

    def principled(self, **kw):
        n = self.node("ShaderNodeBsdfPrincipled")
        for k, v in kw.items():
            self._set(n.inputs[k], v)
        self.link(n.outputs[0], self.out.inputs["Surface"])
        return n


# ----------------------------------------------------------------------------- materials

RUST_DEEP = (0.010, 0.0038, 0.0020)
RUST_DARK = (0.030, 0.0100, 0.0045)
RUST_MID = (0.082, 0.0270, 0.0095)
RUST_WARM = (0.165, 0.0540, 0.0150)
RUST_ORANGE = (0.360, 0.1150, 0.0230)
RUST_TAN = (0.250, 0.1150, 0.0450)


def mat_rust(name="R08_RustPlates"):
    """Weathered rust armour: every slab has its own tone; the surface is mottled at several
    scales (dark scabs, orange bloom, pale flecks), pitted and grainy; torn edges are oxidised
    bright orange; side walls and the faint net of plate lines are dark."""
    m = NT(name)
    co = m.coords()
    tone = m.attr("tone")
    wall = m.attr("wall")
    layer = m.attr("layer")
    rim = m.attr("rim")
    big = m.noise(co, 1.7, 4.0, 0.62)
    mid = m.noise(co, 7.5, 5.0, 0.66)
    sml = m.noise(co, 31.0, 4.0, 0.68)
    fine = m.noise(co, 150.0, 3.0, 0.72)
    # where on the rust ramp this spot sits: slab tone + mottling at three scales
    t = m.math("ADD", m.math("MULTIPLY", tone, 0.42), m.math("MULTIPLY", big, 0.26))
    t = m.math("ADD", t, m.math("MULTIPLY", mid, 0.42))
    t = m.math("ADD", t, m.math("MULTIPLY", m.math("SUBTRACT", sml, 0.5), 0.36))
    t = m.math("ADD", t, m.math("MULTIPLY", m.math("SUBTRACT", fine, 0.5), 0.16))
    base = m.ramp(t, [(0.30, RUST_DEEP), (0.43, RUST_DARK), (0.56, RUST_MID), (0.70, RUST_WARM), (0.86, RUST_ORANGE), (0.98, RUST_TAN)])
    # dark scabs and orange bloom
    scab = m.sstep(0.56, 0.70, m.noise(co, 4.6, 4.0, 0.7))
    base = m.mix(m.math("MULTIPLY", scab, 0.42), base, RUST_DARK)
    bloom = m.sstep(0.60, 0.76, m.noise(m.coords((1.0, 1.0, 0.45)), 11.0, 3.0, 0.6))
    base = m.mix(m.math("MULTIPLY", bloom, 0.40), base, RUST_ORANGE)
    # pits (dark, sunk) and pale flecks
    pit = m.voronoi(co, 62.0)
    pitm = m.sstep(0.17, 0.07, pit)
    base = m.mix(m.math("MULTIPLY", pitm, 0.80), base, RUST_DEEP)
    fleck = m.math("GREATER_THAN", m.noise(co, 240.0, 2.0, 0.6), 0.71)
    base = m.mix(m.math("MULTIPLY", fleck, 0.30), base, RUST_TAN)
    # a faint net of plate lines (the sheet's small tiles) - dark seams, slightly raised cells
    edge = m.voronoi(co, 19.0, feature="DISTANCE_TO_EDGE")
    seam = m.math("MULTIPLY", m.sstep(0.020, 0.003, edge), m.sstep(0.35, 0.60, m.noise(co, 9.0, 2.0, 0.5)))
    base = m.mix(m.math("MULTIPLY", seam, 0.55), base, RUST_DEEP)
    # torn edges of each slab: oxidised orange, broken up
    rimf = m.math("MULTIPLY", m.math("POWER", rim, 1.6), m.math("ADD", 0.30, m.math("MULTIPLY", sml, 0.9)), clamp=True)
    base = m.mix(m.math("MULTIPLY", rimf, 0.82), base, RUST_ORANGE)
    base = m.mix(m.math("MULTIPLY", layer, 0.045), base, RUST_TAN)
    base = m.mix(m.math("MULTIPLY", wall, 0.85), base, RUST_DEEP)
    # relief
    h = m.math("ADD", m.math("MULTIPLY", fine, 0.55), m.math("MULTIPLY", sml, 0.70))
    h = m.math("ADD", h, m.math("MULTIPLY", mid, 0.50))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", pitm, 0.90))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", seam, 0.45))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", scab, 0.25))
    nrm = m.bump(h, 0.85, 0.012)
    rough = m.math("ADD", 0.78, m.math("MULTIPLY", fine, 0.20))
    p = m.principled(**{"Base Color": base, "Roughness": rough, "Normal": nrm})
    p.inputs["Specular IOR Level"].default_value = 0.26
    return m.mat


def mat_under(name="R08_Under"):
    """What shows between and beneath the plates: dark grime, wet dark-red tissue in the wounds,
    black eye sockets, gum / mouth lining (by the `kind` attribute)."""
    m = NT(name)
    co = m.coords()
    wound = m.attr("wound")
    kind = m.attr("kind")
    n1 = m.noise(co, 26.0, 3.0, 0.6)
    fib = m.noise(m.coords((7.0, 7.0, 60.0)), 3.0, 3.0, 0.6)
    grime = m.mix(n1, (0.004, 0.002, 0.0015), (0.018, 0.008, 0.005))
    tissue = m.mix(fib, (0.028, 0.002, 0.004), (0.130, 0.010, 0.012))
    w = m.sstep(0.25, 0.7, wound)
    is_t = m.math("COMPARE", kind, 1.0, 0.25)
    is_g = m.math("COMPARE", kind, 2.0, 0.25)
    is_s = m.math("COMPARE", kind, 3.0, 0.25)
    is_v = m.math("COMPARE", kind, 4.0, 0.25)
    col = m.mix(w, grime, tissue)
    col = m.mix(is_t, col, tissue)
    col = m.mix(is_g, col, m.mix(fib, (0.060, 0.004, 0.007), (0.200, 0.018, 0.022)))
    col = m.mix(is_s, col, (0.0015, 0.001, 0.001))
    col = m.mix(is_v, col, (0.0025, 0.0006, 0.0008))
    wet = m.math("MAXIMUM", m.math("MAXIMUM", w, is_t), is_g)
    rough = m.mixf(wet, 0.92, 0.30)
    rough = m.mixf(m.math("MAXIMUM", is_s, is_v), rough, 1.0)
    nrm = m.bump(m.math("ADD", fib, m.math("MULTIPLY", n1, 0.5)), 0.5, 0.01)
    p = m.principled(**{"Base Color": col, "Roughness": rough, "Normal": nrm})
    p.inputs["Specular IOR Level"].default_value = 0.5
    return m.mat


def mat_muscle(name="R08_Muscle"):
    m = NT(name)
    co = m.coords()
    n1 = m.noise(co, 30.0, 3.0, 0.6)
    n2 = m.noise(co, 150.0, 2.0, 0.6)
    col = m.ramp(n1, [(0.25, (0.032, 0.002, 0.004)), (0.55, (0.115, 0.008, 0.012)), (0.85, (0.210, 0.020, 0.022))])
    nrm = m.bump(m.math("ADD", n1, m.math("MULTIPLY", n2, 0.3)), 0.35, 0.008)
    p = m.principled(**{"Base Color": col, "Roughness": 0.40, "Normal": nrm})
    p.inputs["Specular IOR Level"].default_value = 0.5
    p.inputs["Coat Weight"].default_value = 0.20
    p.inputs["Coat Roughness"].default_value = 0.28
    return m.mat


def mat_gum(name="R08_Gum"):
    m = NT(name)
    co = m.coords()
    n1 = m.noise(co, 38.0, 3.0, 0.6)
    n2 = m.noise(co, 9.0, 2.0, 0.5)
    col = m.ramp(m.math("ADD", m.math("MULTIPLY", n1, 0.6), m.math("MULTIPLY", n2, 0.4)),
                 [(0.25, (0.026, 0.0018, 0.0045)), (0.55, (0.092, 0.0070, 0.012)), (0.85, (0.165, 0.016, 0.021))])
    nrm = m.bump(n1, 0.4, 0.008)
    p = m.principled(**{"Base Color": col, "Roughness": 0.33, "Normal": nrm})
    p.inputs["Specular IOR Level"].default_value = 0.5
    p.inputs["Coat Weight"].default_value = 0.28
    p.inputs["Coat Roughness"].default_value = 0.22
    return m.mat


def mat_mouth(name="R08_MouthLining"):
    """Deep mouth interior: black, with only a faint dark-red sheen."""
    m = NT(name)
    co = m.coords()
    n1 = m.noise(co, 9.0, 2.0, 0.5)
    col = m.mix(n1, (0.0010, 0.0003, 0.0004), (0.0080, 0.0009, 0.0014))
    p = m.principled(**{"Base Color": col, "Roughness": 0.62})
    p.inputs["Specular IOR Level"].default_value = 0.30
    return m.mat


def mat_tooth(name="R08_Teeth"):
    """Dirty yellowed ivory: paler mid-length, brown staining at the gum, in grooves and streaks."""
    m = NT(name)
    co = m.coords()
    t = m.attr("t")
    tone = m.attr("tone")
    streak = m.noise(m.coords((55.0, 55.0, 7.0)), 1.0, 3.0, 0.65)
    blot = m.noise(co, 60.0, 3.0, 0.6)
    fine = m.noise(co, 320.0, 2.0, 0.6)
    ivory = m.mix(tone, (0.300, 0.180, 0.052), (0.470, 0.305, 0.104))
    stain = (0.078, 0.032, 0.009)
    # stained root, slightly darker tip
    root = m.sstep(0.30, 0.0, t)
    tip = m.sstep(0.80, 1.0, t)
    s = m.math("ADD", m.math("MULTIPLY", root, 0.85), m.math("MULTIPLY", tip, 0.30))
    s = m.math("ADD", s, m.math("MULTIPLY", m.sstep(0.46, 0.70, streak), 0.58))
    s = m.math("ADD", s, m.math("MULTIPLY", m.sstep(0.55, 0.74, blot), 0.42), clamp=True)
    col = m.mix(s, ivory, stain)
    col = m.mix(m.math("MULTIPLY", m.math("LESS_THAN", m.voronoi(co, 210.0), 0.12), 0.5), col, (0.10, 0.05, 0.02))
    nrm = m.bump(m.math("ADD", streak, m.math("MULTIPLY", fine, 0.4)), 0.22, 0.006)
    p = m.principled(**{"Base Color": col, "Roughness": 0.52, "Normal": nrm})
    p.inputs["Specular IOR Level"].default_value = 0.38
    return m.mat


def mat_rod(name="R08_Rods"):
    m = NT(name)
    co = m.coords()
    n1 = m.noise(co, 18.0, 4.0, 0.6)
    n2 = m.noise(co, 90.0, 3.0, 0.7)
    col = m.ramp(m.math("ADD", m.math("MULTIPLY", n1, 0.7), m.math("MULTIPLY", n2, 0.3)),
                 [(0.25, (0.045, 0.018, 0.009)), (0.5, (0.150, 0.058, 0.024)), (0.75, (0.260, 0.105, 0.040)), (0.95, (0.38, 0.17, 0.06))])
    nrm = m.bump(m.math("ADD", n1, n2), 0.35, 0.008)
    p = m.principled(**{"Base Color": col, "Roughness": 0.74, "Normal": nrm})
    p.inputs["Specular IOR Level"].default_value = 0.3
    return m.mat


def mat_pupil(name="R08_Pupil", strength=3.2):
    m = NT(name)
    n = m.node("ShaderNodeEmission")
    n.inputs["Color"].default_value = (1.0, 0.060, 0.008, 1.0)
    n.inputs["Strength"].default_value = strength
    m.link(n.outputs[0], m.out.inputs["Surface"])
    return m.mat


def mat_floor(name="Studio_Floor"):
    m = NT(name)
    p = m.principled(**{"Base Color": (0.085, 0.090, 0.095, 1.0), "Roughness": 0.66})
    p.inputs["Specular IOR Level"].default_value = 0.25
    return m.mat


# ----------------------------------------------------------------------------- studio


RIG_PIVOT = (0.0, -0.55, 0.0)


def studio(sc, k=1.0):
    """Dark charcoal studio as on the sheet: seamless floor / backdrop, soft key from the upper
    front-left of the camera, cool fill from the right, warm rim.  Everything hangs from one
    empty (StudioRig); render.py turns it with the camera, so each view is lit the same way."""
    co = collection("Studio")
    rig = bpy.data.objects.new("StudioRig", None)
    rig.location = RIG_PIVOT
    co.objects.link(rig)
    V, Q = [], []
    S = 40.0
    y0, R, n = 7.5, 5.0, 12
    prof = [(-S, 0.0), (y0, 0.0)]
    for i in range(1, n + 1):
        a = (math.pi / 2) * i / n
        prof.append((y0 + R * math.sin(a), R - R * math.cos(a)))
    prof.append((y0 + R, 30.0))
    for (y, z) in prof:
        V.append((-S, y, z))
        V.append((S, y, z))
    for i in range(len(prof) - 1):
        Q.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    ob = add_mesh("Studio_Backdrop", dict(V=np.array(V), Q=np.array(Q)), mat_floor(), smooth=True, coll="Studio")
    ob.parent = rig
    sc.world = bpy.data.worlds.new("StudioWorld")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.038, 0.042, 1.0)
    bg.inputs[1].default_value = 1.0

    def area(name, loc, target, size, energy, color=(1, 1, 1)):
        L = bpy.data.lights.new(name, "AREA")
        L.shape = "RECTANGLE"
        L.size, L.size_y = size
        L.energy = energy * k
        L.color = color
        o = bpy.data.objects.new(name, L)
        o.location = Vector(loc)
        d = Vector(target) - Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        co.objects.link(o)
        o.parent = rig
        return o

    # positions are relative to the pivot; the camera sits on -Y of the rig
    area("Key", (-4.6, -5.6, 6.2), (0, 0.0, 1.5), (4.0, 4.0), 600, (1.0, 0.965, 0.92))
    area("Fill", (5.2, -6.0, 2.0), (0, 0.0, 1.4), (6, 5), 240, (0.86, 0.92, 1.0))
    area("Front", (0.0, -8.0, 1.2), (0, 0.0, 1.4), (5, 4), 190, (1.0, 0.97, 0.94))
    area("Rim", (3.4, 5.6, 5.4), (0, 0.0, 1.6), (3, 3), 260, (1.0, 0.90, 0.78))
    area("Top", (0.0, -0.5, 8.5), (0, 0.0, 1.2), (7, 7), 100, (0.95, 0.97, 1.0))
    area("Back", (0.0, 3.0, 2.6), (0, 12.0, 3.2), (9, 4), 120, (0.80, 0.88, 1.0))
    return rig


def aim_studio(az_deg):
    """Turn the light rig and backdrop to face a camera at azimuth az (turntable lighting)."""
    rig = bpy.data.objects.get("StudioRig")
    if rig is not None:
        rig.rotation_euler = (0.0, 0.0, math.radians(az_deg))


def setup_cycles(sc, samples=64, res=(1000, 1000)):
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    try:
        sc.view_settings.look = "Medium High Contrast"
    except Exception:
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.threads_mode = "AUTO"


def camera(sc, name, pos, target, lens=110.0, sensor=36.0, roll=0.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.sensor_width = sensor
    cam.sensor_fit = "HORIZONTAL"
    cam.clip_start = 0.05
    cam.clip_end = 200
    o = bpy.data.objects.get(name)
    if o is not None:
        bpy.data.objects.remove(o)
    o = bpy.data.objects.new(name, cam)
    o.location = pos
    d = Vector(target) - Vector(pos)
    q = d.to_track_quat("-Z", "Y")
    o.rotation_euler = q.to_euler()
    if roll:
        o.rotation_euler.rotate_axis("Z", roll)
    collection("Cameras").objects.link(o)
    return o


def render(sc, cam_obj, path, res=None, samples=None):
    sc.camera = cam_obj
    if res is not None:
        sc.render.resolution_x, sc.render.resolution_y = res
    if samples is not None:
        sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
