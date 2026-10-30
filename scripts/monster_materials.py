"""
Procedural Cycles materials for the OUT THERE monster.

All colours are linear. Everything is built from node textures so it can be
baked to image maps for Roblox (see bake_export.py). Mesh attributes drive
placement-specific detail so the materials respond to the geometry:
  "blood"  (point float, 0..1)   old blood around wounds, mouth, stump, rods
  "facet"  (face float, 0..1)    per chiselled plate tint / roughness shift
  "tooth"  (point colour)        R root->tip, G blood amount, B decay, A tint
Ambient occlusion and bevel-normal deviation (both Cycles nodes, both bakeable)
put grime into crevices and wear onto exposed edges.
"""
import bpy


class G:
    """Tiny node-graph helper."""

    def __init__(self, mat):
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.x = 0
        self.out = self.n("ShaderNodeOutputMaterial")
        self.bsdf = self.n("ShaderNodeBsdfPrincipled")
        self.link(self.bsdf.outputs[0], self.out.inputs["Surface"])

    def n(self, kind, **props):
        node = self.nt.nodes.new(kind)
        node.location = (self.x, 0)
        self.x -= 220
        for k, v in props.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def val(self, node, name, v):
        node.inputs[name].default_value = v

    def noise(self, scale, detail=4.0, rough=0.55, coord=None, dims='3D', distortion=0.0):
        t = self.n("ShaderNodeTexNoise", noise_dimensions=dims)
        self.val(t, "Scale", scale)
        self.val(t, "Detail", detail)
        self.val(t, "Roughness", rough)
        self.val(t, "Distortion", distortion)
        if coord is not None:
            self.link(coord, t.inputs["Vector"])
        return t

    def ramp(self, fac, stops):
        r = self.n("ShaderNodeValToRGB")
        el = r.color_ramp.elements
        while len(el) < len(stops):
            el.new(0.5)
        for e, (pos, col) in zip(el, stops):
            e.position = pos
            e.color = (*col, 1.0) if len(col) == 3 else col
        self.link(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    def maprange(self, v, a, b, c=0.0, d=1.0, clamp=True):
        m = self.n("ShaderNodeMapRange", clamp=clamp)
        self.link(v, m.inputs["Value"])
        for name, x in (("From Min", a), ("From Max", b), ("To Min", c), ("To Max", d)):
            m.inputs[name].default_value = x
        return m.outputs["Result"]

    def math(self, op, a, b=None, clamp=False):
        m = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for sock, v in ((m.inputs[0], a), (m.inputs[1], b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                sock.default_value = v
            else:
                self.link(v, sock)
        return m.outputs[0]

    def mix(self, fac, a, b, blend='MIX'):
        m = self.n("ShaderNodeMix", data_type='RGBA', blend_type=blend, clamp_result=True)
        ca, cb = [s for s in m.inputs if s.type == 'RGBA'][:2]
        out = [s for s in m.outputs if s.type == 'RGBA'][0]
        for sock, v in ((m.inputs["Factor"], fac), (ca, a), (cb, b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*v, 1.0)
            else:
                self.link(v, sock)
        return out

    def attr(self, name):
        a = self.n("ShaderNodeAttribute", attribute_name=name, attribute_type='GEOMETRY')
        return a

    def coord(self, kind="Object"):
        return self.n("ShaderNodeTexCoord").outputs[kind]

    def bump(self, height, strength, dist=0.02, normal=None):
        b = self.n("ShaderNodeBump")
        self.val(b, "Strength", strength)
        self.val(b, "Distance", dist)
        self.link(height, b.inputs["Height"])
        if normal is not None:
            self.link(normal, b.inputs["Normal"])
        return b.outputs["Normal"]


def _new(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    return m, G(m)


def ao(g, dist=0.3):
    node = g.n("ShaderNodeAmbientOcclusion", samples=16)
    g.val(node, "Distance", dist)
    return g.math('SUBTRACT', 1.0, node.outputs["AO"])      # 0 open .. 1 occluded


def ao_dark(g, col, amount, dist=0.3, dark=(0.012, 0.007, 0.005)):
    return g.mix(g.math('MULTIPLY', ao(g, dist), amount, clamp=True), col, dark)


def edge_mask(g, radius=0.012, lo=0.97, hi=0.86):
    """1 on convex/exposed edges (bevel normal deviates from the true normal)."""
    bev = g.n("ShaderNodeBevel", samples=6)
    g.val(bev, "Radius", radius)
    geo = g.n("ShaderNodeNewGeometry")
    dot = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT')
    g.link(bev.outputs["Normal"], dot.inputs[0])
    g.link(geo.outputs["Normal"], dot.inputs[1])
    return g.maprange(dot.outputs["Value"], lo, hi)


def world_z(g):
    z = g.n("ShaderNodeSeparateXYZ")
    g.link(g.n("ShaderNodeNewGeometry").outputs["Position"], z.inputs[0])
    return z.outputs["Z"]


def streaks(g, scale=(9.0, 9.0, 0.6)):
    """Vertical grime runs: noise stretched along world Z."""
    mp = g.n("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    g.link(g.n("ShaderNodeNewGeometry").outputs["Position"], mp.inputs["Vector"])
    return g.noise(1.0, 5.0, 0.6, coord=mp.outputs[0]).outputs["Fac"]


def blood_mask(g, strength=1.0):
    """Attribute 'blood' broken up by noise and vertical runs -> old, streaky stains."""
    b = g.attr("blood").outputs["Fac"]
    n = g.noise(5.0, 6.0, 0.6, coord=g.coord(), distortion=0.6).outputs["Fac"]
    run = streaks(g, (14.0, 14.0, 1.2))
    v = g.math('ADD', g.math('MULTIPLY', n, 0.6), g.math('MULTIPLY', run, 0.4))
    streak = g.maprange(g.math('ADD', v, g.math('MULTIPLY', b, 0.6)), 0.62, 0.84)
    return g.math('MULTIPLY', g.math('MULTIPLY', streak, b), strength, clamp=True)


def shell_rust(name="M_Shell_Rust"):
    """Layered, geometry-aware corroded shell."""
    m, g = _new(name)
    co = g.coord()
    facet = g.attr("facet").outputs["Fac"]
    # base iron-oxide brown, each chiselled plate slightly different
    mid = g.noise(4.0, 8.0, 0.62, coord=co).outputs["Fac"]
    base = g.ramp(mid, [(0.30, (0.045, 0.020, 0.010)), (0.50, (0.100, 0.045, 0.021)),
                        (0.72, (0.170, 0.076, 0.034))])
    base = g.mix(g.math('MULTIPLY', facet, 0.35), base, (0.022, 0.012, 0.008))
    base = g.mix(g.math('MULTIPLY', g.math('SUBTRACT', 1.0, facet), 0.18), base, (0.16, 0.078, 0.038))
    # zone A: active flaking rust (orange, rough, raised flakes)
    zA = g.maprange(g.noise(1.1, 4.0, 0.55, coord=co).outputs["Fac"], 0.55, 0.64)
    flake_v = g.n("ShaderNodeTexVoronoi")
    g.val(flake_v, "Scale", 24.0)
    g.link(co, flake_v.inputs["Vector"])
    flakes = g.maprange(flake_v.outputs["Distance"], 0.05, 0.35)
    rustc = g.ramp(g.noise(16.0, 6.0, 0.6, coord=co).outputs["Fac"],
                   [(0.35, (0.070, 0.032, 0.015)), (0.6, (0.13, 0.058, 0.026)), (0.8, (0.18, 0.082, 0.036))])
    col = g.mix(zA, base, rustc)
    # zone B: old dark oxidised scale (near black-brown, a little sheen)
    zB = g.maprange(g.noise(0.8, 3.0, 0.5, coord=co, distortion=0.4).outputs["Fac"], 0.56, 0.66)
    col = g.mix(g.math('MULTIPLY', zB, 0.85), col, (0.018, 0.012, 0.009))
    # fine pits and speckle
    vor = g.n("ShaderNodeTexVoronoi")
    g.val(vor, "Scale", 48.0)
    g.link(co, vor.inputs["Vector"])
    pits = g.maprange(vor.outputs["Distance"], 0.11, 0.0)
    col = g.mix(g.math('MULTIPLY', pits, 0.5), col, (0.014, 0.008, 0.005))
    spk = g.noise(28.0, 4.0, 0.6, coord=co).outputs["Fac"]
    col = g.mix(g.maprange(spk, 0.5, 0.62, 0.0, 0.8), col, (0.02, 0.012, 0.008))
    # dense fine mottling + dark corrosion spotting (multi-scale, R08-level surface density)
    fine = g.noise(65.0, 3.0, 0.6, coord=co).outputs["Fac"]
    col = g.mix(g.maprange(fine, 0.42, 0.62, 0.0, 0.55), col, (0.03, 0.017, 0.011))
    spots = g.noise(9.0, 6.0, 0.7, coord=co, distortion=0.5).outputs["Fac"]
    col = g.mix(g.maprange(spots, 0.6, 0.68, 0.0, 0.75), col, (0.016, 0.010, 0.007))
    # granular, stone-like dark speckle (the R08 "rusted granite" grain)
    dots = g.n("ShaderNodeTexVoronoi")
    g.val(dots, "Scale", 150.0)
    g.link(co, dots.inputs["Vector"])
    grain = g.math('MULTIPLY', g.maprange(dots.outputs["Distance"], 0.22, 0.05),
                   g.maprange(g.noise(20.0, 3.0, coord=co).outputs["Fac"], 0.4, 0.6), clamp=True)
    col = g.mix(g.math('MULTIPLY', grain, 0.7), col, (0.018, 0.010, 0.007))
    # worn exposed edges: rust rubbed thin, lighter and smoother
    edge = g.math('MULTIPLY', edge_mask(g), g.maprange(spk, 0.35, 0.6), clamp=True)
    col = g.mix(g.math('MULTIPLY', edge, 0.5), col, (0.15, 0.085, 0.045))
    # vertical grime runs and dirt creeping up from the ground
    run = g.maprange(streaks(g), 0.5, 0.68, 0.0, 0.55)
    col = g.mix(run, col, (0.020, 0.014, 0.010))
    col = g.mix(g.maprange(world_z(g), 1.0, 0.0, 0.0, 0.6), col, (0.032, 0.025, 0.018))
    # grime packed into crevices and under overhangs
    col = ao_dark(g, col, 1.1, 0.25)
    bl = blood_mask(g)
    col = g.mix(bl, col, (0.040, 0.005, 0.004))
    g.link(col, g.bsdf.inputs["Base Color"])
    rough = g.math('ADD', g.math('MULTIPLY', zA, 0.08), g.maprange(mid, 0.3, 0.8, 0.62, 0.82))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', zB, 0.22))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', edge, 0.2))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', bl, 0.35))
    g.link(rough, g.bsdf.inputs["Roughness"])
    h = g.math('ADD', g.math('MULTIPLY', g.noise(14.0, 8.0, 0.68, coord=co).outputs["Fac"], 0.5),
               g.math('ADD', g.math('MULTIPLY', pits, -0.15), g.math('MULTIPLY', g.math('MULTIPLY', flakes, zA), 0.3)))
    h = g.math('ADD', h, g.math('MULTIPLY', fine, 0.35))
    g.link(g.bump(h, 0.5, 0.012), g.bsdf.inputs["Normal"])
    return m


def shell_edge(name="M_Shell_TornEdge"):
    """Exposed thickness of the torn shell: stratified rust layers, lighter fresh breaks."""
    m, g = _new(name)
    co = g.coord()
    w = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='Z')
    for k, v in (("Scale", 28.0), ("Distortion", 3.0), ("Detail", 3.0)):
        g.val(w, k, v)
    g.link(co, w.inputs["Vector"])
    n = g.noise(12.0, 6.0, 0.6, coord=co).outputs["Fac"]
    f = n
    col = g.ramp(f, [(0.3, (0.07, 0.034, 0.017)), (0.55, (0.17, 0.083, 0.040)),
                     (0.78, (0.27, 0.14, 0.07))])
    col = ao_dark(g, col, 1.1, 0.1)
    col = g.mix(blood_mask(g, 0.9), col, (0.045, 0.006, 0.004))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.val(g.bsdf, "Roughness", 0.85)
    g.link(g.bump(f, 0.5, 0.008), g.bsdf.inputs["Normal"])
    return m


def shell_under(name="M_Shell_Under"):
    """Floor of the peels: the older, darker rust strata under the torn skin."""
    m, g = _new(name)
    co = g.coord()
    n = g.noise(10.0, 6.0, 0.6, coord=co).outputs["Fac"]
    vor = g.n("ShaderNodeTexVoronoi")
    g.val(vor, "Scale", 60.0)
    g.link(co, vor.inputs["Vector"])
    pits = g.maprange(vor.outputs["Distance"], 0.14, 0.0)
    col = g.ramp(n, [(0.3, (0.012, 0.007, 0.005)), (0.6, (0.030, 0.016, 0.009)), (0.85, (0.055, 0.027, 0.014))])
    col = g.mix(g.math('MULTIPLY', pits, 0.6), col, (0.010, 0.006, 0.004))
    col = ao_dark(g, col, 1.0, 0.08)
    col = g.mix(blood_mask(g, 0.8), col, (0.04, 0.006, 0.004))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.val(g.bsdf, "Metallic", 0.05)
    g.link(g.maprange(n, 0.3, 0.8, 0.6, 0.85), g.bsdf.inputs["Roughness"])
    g.link(g.bump(g.math('SUBTRACT', n, pits), 0.5, 0.006), g.bsdf.inputs["Normal"])
    return m


def flesh(name="M_Flesh", dark=1.0):
    """Old, dark, fibrous tissue: dull crimson-brown, blackened in the folds, faint fascia."""
    m, g = _new(name)
    co = g.coord()
    st = g.n("ShaderNodeMapping")
    st.inputs["Scale"].default_value = (16.0, 16.0, 2.2)   # stretched -> fibre streaks
    g.link(co, st.inputs["Vector"])
    fib = g.noise(1.0, 6.0, 0.65, coord=st.outputs[0], distortion=0.3).outputs["Fac"]
    n = g.noise(7.0, 5.0, 0.6, coord=co).outputs["Fac"]
    f = g.math('ADD', g.math('MULTIPLY', fib, 0.65), g.math('MULTIPLY', n, 0.35))
    k = dark
    col = g.ramp(f, [(0.28, (0.018 * k, 0.003 * k, 0.003 * k)), (0.5, (0.055 * k, 0.010 * k, 0.008 * k)),
                     (0.7, (0.088 * k, 0.019 * k, 0.015 * k)), (0.86, (0.115 * k, 0.032 * k, 0.024 * k))])
    nec = g.maprange(g.noise(3.0, 4.0, coord=co).outputs["Fac"], 0.58, 0.68)       # necrotic patches
    col = g.mix(g.math('MULTIPLY', nec, 0.8), col, (0.012 * k, 0.006 * k, 0.005 * k))
    fas = g.maprange(fib, 0.74, 0.82)                                                # pale fascia threads
    col = g.mix(g.math('MULTIPLY', fas, 0.35), col, (0.11 * k, 0.06 * k, 0.045 * k))
    col = ao_dark(g, col, 1.2, 0.06, dark=(0.006, 0.002, 0.002))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.math('ADD', g.maprange(n, 0.3, 0.7, 0.6, 0.82), g.math('MULTIPLY', nec, 0.1)),
           g.bsdf.inputs["Roughness"])
    g.link(g.bump(f, 0.55, 0.01), g.bsdf.inputs["Normal"])
    return m


def gum(name="M_Gum"):
    """Decayed gums: swollen dark meat, blackened necrotic rot, crusted blood."""
    m, g = _new(name)
    co = g.coord()
    n = g.noise(13.0, 6.0, 0.6, coord=co).outputs["Fac"]
    col = g.ramp(n, [(0.3, (0.014, 0.003, 0.003)), (0.55, (0.045, 0.008, 0.007)),
                     (0.8, (0.075, 0.016, 0.012))])
    rot = g.maprange(g.noise(4.0, 4.0, coord=co).outputs["Fac"], 0.52, 0.64)
    col = g.mix(g.math('MULTIPLY', rot, 0.85), col, (0.010, 0.008, 0.006))
    col = g.mix(g.math('MULTIPLY', g.maprange(n, 0.7, 0.85), 0.5), col, (0.10, 0.07, 0.04))   # pus-yellow crust
    col = ao_dark(g, col, 1.2, 0.06, dark=(0.004, 0.002, 0.002))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.math('ADD', g.maprange(n, 0.3, 0.8, 0.35, 0.6), g.math('MULTIPLY', rot, 0.3)),
           g.bsdf.inputs["Roughness"])
    g.link(g.bump(n, 0.6, 0.01), g.bsdf.inputs["Normal"])
    return m


def teeth(name="M_Teeth"):
    """Yellowed bone, decay, dark grime at exposed roots, dried blood running from the gums."""
    m, g = _new(name)
    co = g.coord()
    a = g.attr("tooth")
    t = g.n("ShaderNodeSeparateColor")
    g.link(a.outputs["Color"], t.inputs[0])
    tpos, tblood, tdecay = t.outputs[0], t.outputs[1], t.outputs[2]
    tint = a.outputs["Alpha"]
    n = g.noise(16.0, 6.0, 0.6, coord=co).outputs["Fac"]
    col = g.ramp(n, [(0.3, (0.17, 0.11, 0.04)), (0.6, (0.30, 0.21, 0.08)), (0.85, (0.40, 0.31, 0.14))])
    col = g.mix(g.math('MULTIPLY', tint, 0.55), col, (0.20, 0.12, 0.04))           # per-tooth yellowing
    # root grime and decay pits
    root = g.maprange(tpos, 0.4, 0.0)
    col = g.mix(g.math('MULTIPLY', root, 0.9), col, (0.06, 0.035, 0.014))
    grime = g.maprange(g.noise(22.0, 5.0, coord=co).outputs["Fac"], 0.5, 0.66, 0.0, 0.6)
    col = g.mix(grime, col, (0.09, 0.055, 0.022))
    dec = g.math('MULTIPLY', tdecay, g.maprange(g.noise(9.0, 4.0, coord=co).outputs["Fac"], 0.48, 0.6), clamp=True)
    col = g.mix(dec, col, (0.025, 0.015, 0.007))
    # dried blood creeping down from the gum by a per-tooth amount
    bl = g.maprange(g.math('SUBTRACT', g.math('MULTIPLY', tblood, 0.95), tpos), -0.06, 0.12)
    bl = g.math('MULTIPLY', bl, g.maprange(g.noise(11.0, 5.0, coord=co, distortion=1.0).outputs["Fac"], 0.35, 0.6), clamp=True)
    col = g.mix(bl, col, (0.060, 0.004, 0.003))
    col = ao_dark(g, col, 1.0, 0.06)
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.math('ADD', g.maprange(n, 0.3, 0.8, 0.42, 0.65), g.math('MULTIPLY', dec, 0.25)),
           g.bsdf.inputs["Roughness"])
    g.link(g.bump(n, 0.3, 0.004), g.bsdf.inputs["Normal"])
    return m


def metal_plate(name="M_Metal_Plate"):
    """Dark diamond-tread plate (the original's rod texture) with rust creeping in."""
    m, g = _new(name)
    co = g.coord()
    w1 = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='DIAGONAL', wave_profile='TRI')
    w2 = g.n("ShaderNodeTexWave", wave_type='BANDS', bands_direction='DIAGONAL', wave_profile='TRI')
    for w in (w1, w2):
        g.val(w, "Scale", 9.0)
    rot = g.n("ShaderNodeMapping")
    rot.inputs["Rotation"].default_value = (0, 0, 1.5708)
    g.link(co, rot.inputs["Vector"])
    g.link(co, w1.inputs["Vector"])
    g.link(rot.outputs[0], w2.inputs["Vector"])
    tread = g.maprange(g.math('MULTIPLY', w1.outputs["Fac"], w2.outputs["Fac"]), 0.55, 0.8)
    rustn = g.noise(4.0, 6.0, 0.6, coord=co).outputs["Fac"]
    rust = g.maprange(rustn, 0.25, 0.45)
    col = g.mix(rust, (0.040, 0.040, 0.044), g.ramp(rustn, [(0.4, (0.05, 0.02, 0.01)), (0.8, (0.13, 0.05, 0.02))]))
    col = g.mix(g.math('MULTIPLY', tread, 0.2), col, (0.10, 0.10, 0.105))
    col = ao_dark(g, col, 0.9, 0.1)
    col = g.mix(blood_mask(g, 0.7), col, (0.045, 0.006, 0.004))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.maprange(rust, 0.0, 1.0, 0.85, 0.15), g.bsdf.inputs["Metallic"])
    g.link(g.maprange(rust, 0.0, 1.0, 0.45, 0.9), g.bsdf.inputs["Roughness"])
    g.link(g.bump(tread, 0.6, 0.008), g.bsdf.inputs["Normal"])
    return m


def flat(name, color, rough=0.8, emit=None, strength=0.0):
    m, g = _new(name)
    g.val(g.bsdf, "Base Color", (*color, 1.0))
    g.val(g.bsdf, "Roughness", rough)
    if emit:
        g.val(g.bsdf, "Emission Color", (*emit, 1.0))
        g.val(g.bsdf, "Emission Strength", strength)
    m.diffuse_color = (*color, 1.0)
    return m


def build_all():
    M = {
        "shell": shell_rust(),
        "edge": shell_edge(),
        "under": shell_under(),
        "flesh": flesh(),
        "gum": gum(),
        "teeth": teeth(),
        "metal": metal_plate(),
        "eye": flat("M_Eye_Red", (0.05, 0.0, 0.0), 0.4, emit=(1.0, 0.0, 0.0), strength=3.0),
        "socket": flesh("M_EyeSocket", dark=0.25),
        "cavity": flat("M_MouthCavity", (0.004, 0.0012, 0.001), 0.9),
        "throat": flesh("M_Throat", dark=0.4),
        "tongue": flesh("M_Tongue", dark=0.75),
    }
    M["inner"] = M["gum"]
    M["blood"] = M["flesh"]
    viewport = {"shell": (0.12, 0.045, 0.02), "edge": (0.2, 0.09, 0.04), "under": (0.05, 0.04, 0.035),
                "flesh": (0.1, 0.012, 0.01), "gum": (0.05, 0.01, 0.008), "teeth": (0.45, 0.33, 0.14),
                "metal": (0.05, 0.05, 0.055)}
    for k, c in viewport.items():
        M[k].diffuse_color = (*c, 1.0)
    return M
