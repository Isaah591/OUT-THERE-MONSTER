"""
Procedural Cycles materials for the OUT THERE monster.

All colours are linear. Everything is built from node textures so it can be
baked to image maps for Roblox (see bake_export.py). Two mesh attributes drive
placement-specific detail:
  "blood"  (point float, 0..1)   old blood around wounds, mouth, stump, rods
  "tooth"  (point colour)        R = root->tip position, G = blood amount, B = grime amount
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


def ao_dark(g, col, amount, dist=0.3):
    ao = g.n("ShaderNodeAmbientOcclusion", samples=12)
    g.val(ao, "Distance", dist)
    occl = g.math('SUBTRACT', 1.0, ao.outputs["AO"])
    return g.mix(g.math('MULTIPLY', occl, amount, clamp=True), col, (0.012, 0.007, 0.005))


def blood_mask(g, strength=1.0):
    """Attribute 'blood' broken up by noise -> streaky old stains."""
    b = g.attr("blood").outputs["Fac"]
    n = g.noise(5.0, 6.0, 0.6, coord=g.coord(), distortion=0.6).outputs["Fac"]
    streak = g.maprange(g.math('ADD', n, g.math('MULTIPLY', b, 0.55)), 0.62, 0.82)
    return g.math('MULTIPLY', g.math('MULTIPLY', streak, b), strength, clamp=True)


def shell_rust(name="M_Shell_Rust"):
    m, g = _new(name)
    co = g.coord()
    # multi-scale corrosion mottling
    mid = g.noise(4.5, 8.0, 0.62, coord=co).outputs["Fac"]
    col = g.ramp(mid, [(0.32, (0.022, 0.011, 0.007)), (0.46, (0.055, 0.024, 0.012)),
                       (0.60, (0.110, 0.044, 0.019)), (0.76, (0.175, 0.072, 0.030))])
    fine = g.noise(26.0, 4.0, 0.6, coord=co).outputs["Fac"]
    col = g.mix(g.maprange(fine, 0.45, 0.68, 0.0, 0.8), col, (0.026, 0.014, 0.009))
    blot = g.maprange(g.noise(1.3, 4.0, 0.55, coord=co).outputs["Fac"], 0.50, 0.60)
    col = g.mix(g.math('MULTIPLY', blot, 0.75), col, (0.026, 0.016, 0.011))
    # orange rust blooms
    bloom_v = g.n("ShaderNodeTexVoronoi")
    g.val(bloom_v, "Scale", 6.0)
    g.val(bloom_v, "Randomness", 1.0)
    g.link(co, bloom_v.inputs["Vector"])
    bloom = g.math('MULTIPLY', g.maprange(bloom_v.outputs["Distance"], 0.28, 0.05),
                   g.maprange(g.noise(9.0, 4.0, coord=co).outputs["Fac"], 0.45, 0.65), clamp=True)
    col = g.mix(g.math('MULTIPLY', bloom, 0.7), col, (0.20, 0.072, 0.025))
    # fine pitting
    vor = g.n("ShaderNodeTexVoronoi")
    g.val(vor, "Scale", 45.0)
    g.link(co, vor.inputs["Vector"])
    pits = g.maprange(vor.outputs["Distance"], 0.12, 0.0)
    col = g.mix(g.math('MULTIPLY', pits, 0.5), col, (0.018, 0.009, 0.006))
    # mid-scale dark corrosion speckle
    spk = g.noise(11.0, 6.0, 0.65, coord=co).outputs["Fac"]
    col = g.mix(g.maprange(spk, 0.52, 0.64, 0.0, 0.7), col, (0.024, 0.013, 0.009))
    # dirt creeping up from the ground
    z = g.n("ShaderNodeSeparateXYZ")
    g.link(g.n("ShaderNodeNewGeometry").outputs["Position"], z.inputs[0])
    col = g.mix(g.maprange(z.outputs["Z"], 1.1, 0.0, 0.0, 0.55), col, (0.034, 0.026, 0.019))
    # subtle worn high points
    bev = g.n("ShaderNodeBevel", samples=6)
    g.val(bev, "Radius", 0.012)
    geo = g.n("ShaderNodeNewGeometry")
    dot = g.n("ShaderNodeVectorMath", operation='DOT_PRODUCT')
    g.link(bev.outputs["Normal"], dot.inputs[0])
    g.link(geo.outputs["Normal"], dot.inputs[1])
    edge = g.math('MULTIPLY', g.maprange(dot.outputs["Value"], 0.97, 0.85),
                  g.maprange(fine, 0.5, 0.7), clamp=True)
    col = g.mix(g.math('MULTIPLY', edge, 0.35), col, (0.16, 0.075, 0.035))
    col = ao_dark(g, col, 0.95)
    bl = blood_mask(g)
    col = g.mix(bl, col, (0.045, 0.006, 0.004))
    g.link(col, g.bsdf.inputs["Base Color"])
    rough = g.maprange(mid, 0.3, 0.8, 0.75, 0.95)
    g.link(g.math('SUBTRACT', rough, g.math('MULTIPLY', bl, 0.35)), g.bsdf.inputs["Roughness"])
    h = g.math('ADD', g.math('MULTIPLY', g.noise(14.0, 8.0, 0.68, coord=co).outputs["Fac"], 0.8),
               g.math('ADD', g.math('MULTIPLY', pits, -0.5), g.math('MULTIPLY', spk, 0.4)))
    g.link(g.bump(h, 0.45, 0.012), g.bsdf.inputs["Normal"])
    return m


def shell_edge(name="M_Shell_TornEdge"):
    """Exposed thickness of the torn shell: lighter raw corrosion, darker toward flesh."""
    m, g = _new(name)
    co = g.coord()
    n = g.noise(9.0, 6.0, 0.6, coord=co).outputs["Fac"]
    col = g.ramp(n, [(0.35, (0.070, 0.028, 0.014)), (0.55, (0.20, 0.085, 0.036)),
                     (0.75, (0.30, 0.135, 0.060))])
    col = ao_dark(g, col, 1.0, 0.12)
    bl = blood_mask(g, 0.8)
    col = g.mix(bl, col, (0.055, 0.007, 0.005))
    g.link(col, g.bsdf.inputs["Base Color"])
    g.val(g.bsdf, "Roughness", 0.82)
    g.link(g.bump(g.noise(30.0, 6.0, coord=co).outputs["Fac"], 0.5, 0.01), g.bsdf.inputs["Normal"])
    return m


def shell_under(name="M_Shell_Under"):
    """Floor of shallow chips: darker corroded under-layer (no flesh)."""
    m, g = _new(name)
    co = g.coord()
    n = g.noise(12.0, 6.0, 0.6, coord=co).outputs["Fac"]
    col = g.ramp(n, [(0.35, (0.025, 0.012, 0.008)), (0.7, (0.090, 0.036, 0.017))])
    col = ao_dark(g, col, 0.8, 0.1)
    g.link(col, g.bsdf.inputs["Base Color"])
    g.val(g.bsdf, "Roughness", 0.9)
    g.link(g.bump(n, 0.5, 0.01), g.bsdf.inputs["Normal"])
    return m


def flesh(name="M_Flesh", dark=1.0):
    """Old, dark, fibrous tissue - deliberately dull, not fresh and bright."""
    m, g = _new(name)
    co = g.coord()
    st = g.n("ShaderNodeMapping")
    st.inputs["Scale"].default_value = (14.0, 14.0, 2.5)   # stretched -> fibre streaks
    g.link(co, st.inputs["Vector"])
    fib = g.noise(1.0, 6.0, 0.65, coord=st.outputs[0], distortion=0.3).outputs["Fac"]
    n = g.noise(8.0, 5.0, 0.6, coord=co).outputs["Fac"]
    f = g.math('ADD', g.math('MULTIPLY', fib, 0.65), g.math('MULTIPLY', n, 0.35))
    k = dark
    col = g.ramp(f, [(0.3, (0.020 * k, 0.003 * k, 0.003 * k)), (0.5, (0.055 * k, 0.008 * k, 0.007 * k)),
                     (0.7, (0.075 * k, 0.012 * k, 0.010 * k)), (0.85, (0.095 * k, 0.022 * k, 0.017 * k))])
    col = ao_dark(g, col, 1.0, 0.08)
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.maprange(n, 0.3, 0.7, 0.62, 0.85), g.bsdf.inputs["Roughness"])
    g.link(g.bump(f, 0.55, 0.01), g.bsdf.inputs["Normal"])
    return m


def gum(name="M_Gum"):
    m, g = _new(name)
    co = g.coord()
    n = g.noise(14.0, 6.0, 0.6, coord=co).outputs["Fac"]
    col = g.ramp(n, [(0.3, (0.018, 0.003, 0.003)), (0.55, (0.060, 0.010, 0.008)),
                     (0.8, (0.110, 0.022, 0.016))])
    col = ao_dark(g, col, 1.0, 0.08)
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.maprange(n, 0.3, 0.8, 0.35, 0.6), g.bsdf.inputs["Roughness"])
    g.link(g.bump(n, 0.5, 0.01), g.bsdf.inputs["Normal"])
    return m


def teeth(name="M_Teeth"):
    """Yellowed bone; grime + dried blood creeping from the gum line (attribute 'tooth')."""
    m, g = _new(name)
    co = g.coord()
    t = g.n("ShaderNodeSeparateColor")
    g.link(g.attr("tooth").outputs["Color"], t.inputs[0])
    tpos, tblood, tdirt = t.outputs[0], t.outputs[1], t.outputs[2]
    n = g.noise(18.0, 6.0, 0.6, coord=co).outputs["Fac"]
    col = g.ramp(n, [(0.3, (0.30, 0.20, 0.075)), (0.6, (0.46, 0.34, 0.14)), (0.85, (0.55, 0.44, 0.22))])
    # brown grime band near root + random dirty teeth
    root = g.maprange(tpos, 0.45, 0.0)
    dirt = g.math('MAXIMUM', g.math('MULTIPLY', root, 0.85), g.math('MULTIPLY', tdirt, 0.6))
    dirt = g.math('MULTIPLY', dirt, g.maprange(g.noise(7.0, 4.0, coord=co).outputs["Fac"], 0.3, 0.6, 0.6, 1.0), clamp=True)
    col = g.mix(dirt, col, (0.10, 0.055, 0.022))
    # dried blood reaching down the tooth by a per-tooth amount
    reach = g.math('MULTIPLY', tblood, 0.95)
    bl = g.maprange(g.math('SUBTRACT', reach, tpos), -0.05, 0.12)
    bl = g.math('MULTIPLY', bl, g.maprange(g.noise(11.0, 5.0, coord=co, distortion=1.0).outputs["Fac"], 0.35, 0.6), clamp=True)
    col = g.mix(g.math('MULTIPLY', bl, 1.0), col, (0.075, 0.005, 0.003))
    col = ao_dark(g, col, 0.9, 0.06)
    g.link(col, g.bsdf.inputs["Base Color"])
    g.link(g.maprange(n, 0.3, 0.8, 0.45, 0.7), g.bsdf.inputs["Roughness"])
    g.link(g.bump(n, 0.4, 0.005), g.bsdf.inputs["Normal"])
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
    rust = g.maprange(rustn, 0.48, 0.62)
    col = g.mix(rust, (0.045, 0.045, 0.050), g.ramp(rustn, [(0.4, (0.06, 0.024, 0.012)), (0.8, (0.16, 0.06, 0.025))]))
    col = g.mix(g.math('MULTIPLY', tread, 0.4), col, (0.11, 0.11, 0.115))
    col = ao_dark(g, col, 0.8, 0.1)
    bl = blood_mask(g, 0.6)
    col = g.mix(bl, col, (0.05, 0.007, 0.005))
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
        "eye": flat("M_Eye_Red", (0.6, 0.0, 0.0), emit=(1.0, 0.0, 0.0), strength=4.0),
        "socket": flat("M_EyeSocket", (0.006, 0.003, 0.002), 0.9),
        "cavity": flat("M_MouthCavity", (0.004, 0.0012, 0.001), 0.9),
        "throat": flesh("M_Throat", dark=0.45),
    }
    M["inner"] = M["gum"]
    M["blood"] = M["flesh"]
    viewport = {"shell": (0.12, 0.045, 0.02), "edge": (0.2, 0.09, 0.04), "under": (0.05, 0.02, 0.01),
                "flesh": (0.1, 0.012, 0.01), "gum": (0.06, 0.01, 0.008), "teeth": (0.45, 0.33, 0.14),
                "metal": (0.05, 0.05, 0.055)}
    for k, c in viewport.items():
        M[k].diffuse_color = (*c, 1.0)
    return M
