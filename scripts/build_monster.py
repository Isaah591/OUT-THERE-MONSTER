"""
OUT THERE monster - procedural blockout builder.

Run headless:
    python build_monster.py            (with the `bpy` module installed)
    blender -b -P build_monster.py     (with a normal Blender install)

Writes ../blockout/out_there_monster_blockout.blend

Conventions: metres, Z up, the monster faces -Y. Monster's RIGHT side is -X
(the long arm), monster's LEFT side is +X (the short arm).
"""
import math
import os
import random

import bpy
import bmesh
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "blockout")
OUT_BLEND = os.path.join(OUT_DIR, "out_there_monster_blockout.blend")

# ---------------------------------------------------------------------------
# Tunable proportions (the values to adjust during blockout review)
# ---------------------------------------------------------------------------
JAW_OPEN_DEG = 50.0       # how far the lower jaw hangs open
JAW_BROKEN_ROLL_DEG = 7.0  # sideways sag of the broken hinge (monster's right lower)
HEAD_POS = Vector((0.02, -0.86, 1.98))  # centre of the cranium base (= upper gum line)
HEAD_PITCH_DEG = -4.0     # small downward nod
HEAD_W, HEAD_D, CRANIUM_H = 0.96, 0.84, 0.56
JAW_LEN, JAW_W = 0.84, 0.94

rng = random.Random(7)


# ---------------------------------------------------------------------------
# Scene helpers
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def material(name, color, rough=0.8, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    m.diffuse_color = (*color, 1.0)  # viewport solid colour
    return m


def mesh_object(name, bm, col, mats, parent=None, location=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = False  # faceted low-poly look
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.location = location
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def skin(bm, profiles, cap_start=True, cap_end=True, side_mat=0, cap_mats=(0, 0)):
    """Bridge a list of equal-length closed point loops into a solid."""
    rings = [[bm.verts.new(p) for p in prof] for prof in profiles]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            f = bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
            f.material_index = side_mat
    if cap_start:
        f = bm.faces.new(list(reversed(rings[0])))
        f.material_index = cap_mats[0]
    if cap_end:
        f = bm.faces.new(rings[-1])
        f.material_index = cap_mats[1]
    return rings


def chamfer_rect(w, d, c):
    c = min(c, w * 0.49, d * 0.49)
    hw, hd = w / 2, d / 2
    return [(hw, hd - c), (hw - c, hd), (-hw + c, hd), (-hw, hd - c),
            (-hw, -hd + c), (-hw + c, -hd), (hw - c, -hd), (hw, -hd + c)]


def frames(points, ref):
    """Per-point (tangent, side, fwd) frames along a polyline (mitred)."""
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts)):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i] - pts[i - 1]).normalized() + (pts[i + 1] - pts[i]).normalized()
        t.normalize()
        r = Vector(ref)
        if abs(t.dot(r.normalized())) > 0.97:
            r = Vector((0, 0, 1))
        side = t.cross(r).normalized()
        fwd = side.cross(t).normalized()
        out.append((t, side, fwd))
    return pts, out


def loft(bm, rings, ref=(0, -1, 0), chamfer=0.22, jitter=0.0, **kw):
    """rings: list of dicts {p, w, d, [ox, oy, rot]}. w spans `side`, d spans `fwd`.
    Builds a chamfered-box tube - the core 'blocky but connected' limb primitive."""
    pts, frs = frames([r["p"] for r in rings], ref)
    profiles = []
    for r, p, (t, side, fwd) in zip(rings, pts, frs):
        sec = chamfer_rect(r["w"], r["d"], chamfer * min(r["w"], r["d"]))
        rot = math.radians(r.get("rot", 0.0))
        cr, sr = math.cos(rot), math.sin(rot)
        centre = p + side * r.get("ox", 0.0) + fwd * r.get("oy", 0.0)
        prof = []
        for (x, y) in sec:
            x, y = x * cr - y * sr, x * sr + y * cr
            v = centre + side * x + fwd * y
            if jitter:
                v += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * jitter
            prof.append(v)
        profiles.append(prof)
    return skin(bm, profiles, **kw)


def flat_bar(bm, points, w=0.085, d=0.035, ref=(0, 0, 1)):
    loft(bm, [{"p": p, "w": w, "d": d} for p in points], ref=ref, chamfer=0.0)


def tooth(bm, base, direction, length, w, d, lean_axis=None, taper=0.55, twist=0.0):
    """Plank-like tapered tooth from `base` along `direction`."""
    dvec = Vector(direction).normalized()
    ref = Vector((0, -1, 0)) if abs(dvec.y) < 0.9 else Vector((1, 0, 0))
    side = dvec.cross(ref).normalized()
    fwd = side.cross(dvec).normalized()
    rot = Matrix.Rotation(math.radians(twist), 3, dvec)
    side, fwd = rot @ side, rot @ fwd
    base = Vector(base) - dvec * 0.04  # sink root into the gum
    tip = base + dvec * length
    tipshift = side * rng.uniform(-0.25, 0.25) * w
    profs = []
    for c, s in ((base, 1.0), (base + dvec * length * 0.55, 0.92), (tip + tipshift, taper)):
        profs.append([c + side * x * s + fwd * y * s for x, y in
                      [(w / 2, d / 2), (-w / 2, d / 2), (-w / 2, -d / 2), (w / 2, -d / 2)]])
    skin(bm, profs)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build():
    reset_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'

    root = collection("MONSTER")
    c_head = collection("Head", root)
    c_body = collection("Body", root)
    c_arms = collection("Arms", root)
    c_legs = collection("Legs", root)
    c_hw = collection("Hardware", root)

    M = {
        "shell": material("M_Shell_Rust", (0.095, 0.036, 0.018), rough=0.85),
        "flesh": material("M_Flesh", (0.16, 0.022, 0.016), rough=0.6),
        "gum": material("M_Gum", (0.06, 0.012, 0.009), rough=0.55),
        "cavity": material("M_MouthCavity", (0.004, 0.0015, 0.001), rough=0.9),
        "teeth": material("M_Teeth", (0.42, 0.30, 0.12), rough=0.7),
        "metal": material("M_Metal_Plate", (0.05, 0.05, 0.055), rough=0.45, metal=0.85),
        "eye": material("M_Eye_Red", (0.6, 0.0, 0.0), emit=(1.0, 0.0, 0.0), emit_strength=3.0),
        "socket": material("M_EyeSocket", (0.01, 0.004, 0.003), rough=0.9),
        "blood": material("M_DriedBlood", (0.16, 0.012, 0.01), rough=0.5),
        "inner": material("M_MouthInterior", (0.016, 0.004, 0.003), rough=0.6),
    }

    # ------------------------------------------------------------------ TORSO
    # Spine leans ~25 deg forward; back hump rises to roughly head-top height.
    # (oy offsets are along the forward axis: negative pushes mass back into the hump)
    bm = bmesh.new()
    loft(bm, [
        {"p": (0.00, 0.20, 0.92), "w": 0.84, "d": 0.56},
        {"p": (0.00, 0.17, 1.12), "w": 0.90, "d": 0.62},
        {"p": (0.00, 0.06, 1.38), "w": 0.92, "d": 0.64, "oy": -0.02},
        {"p": (0.00, -0.10, 1.62), "w": 1.00, "d": 0.80, "oy": 0.00},
        {"p": (-0.03, -0.26, 1.86), "w": 1.18, "d": 0.90, "oy": -0.08, "rot": 4},
        {"p": (-0.03, -0.32, 2.16), "w": 1.08, "d": 0.88, "oy": -0.10, "rot": 4},
        {"p": (-0.02, -0.30, 2.42), "w": 0.80, "d": 0.60, "oy": -0.04, "rot": 6},
    ], chamfer=0.25, jitter=0.012)
    mesh_object("Torso", bm, c_body, [M["shell"]])

    # Shoulder masses - the long-arm side is heavier and slightly dropped.
    bm = bmesh.new()
    loft(bm, [
        {"p": (-0.30, -0.28, 2.02), "w": 0.50, "d": 0.62},
        {"p": (-0.58, -0.28, 1.94), "w": 0.52, "d": 0.62},
        {"p": (-0.74, -0.30, 1.86), "w": 0.40, "d": 0.52},
    ], ref=(0, 0, 1), chamfer=0.3, jitter=0.01)
    loft(bm, [
        {"p": (0.30, -0.28, 2.04), "w": 0.44, "d": 0.56},
        {"p": (0.56, -0.28, 2.00), "w": 0.44, "d": 0.54},
        {"p": (0.70, -0.30, 1.94), "w": 0.36, "d": 0.46},
    ], ref=(0, 0, 1), chamfer=0.3, jitter=0.01)
    mesh_object("Shoulders", bm, c_body, [M["shell"]])

    # ------------------------------------------------------------------ ARMS
    # Long arm (monster's right, -X): reaches forward/out to the ground.
    bm = bmesh.new()
    loft(bm, [
        {"p": (-0.58, -0.28, 1.98), "w": 0.38, "d": 0.40},
        {"p": (-0.80, -0.41, 1.53), "w": 0.37, "d": 0.39},
        {"p": (-1.02, -0.54, 1.08), "w": 0.38, "d": 0.39},   # elbow
        {"p": (-1.10, -0.60, 0.98), "w": 0.45, "d": 0.43},   # forearm steps up in mass
        {"p": (-1.72, -1.10, 0.22), "w": 0.48, "d": 0.45},
        {"p": (-1.84, -1.20, 0.05), "w": 0.46, "d": 0.38},   # club hand on ground
    ], chamfer=0.12, jitter=0.012)
    mesh_object("Arm_R_Long", bm, c_arms, [M["shell"]])

    # Short arm (monster's left, +X): hangs to about knee height.
    bm = bmesh.new()
    loft(bm, [
        {"p": (0.58, -0.28, 2.00), "w": 0.38, "d": 0.40},
        {"p": (0.68, -0.38, 1.65), "w": 0.37, "d": 0.39},
        {"p": (0.78, -0.48, 1.30), "w": 0.38, "d": 0.39},   # elbow
        {"p": (0.80, -0.52, 1.22), "w": 0.41, "d": 0.40},
        {"p": (0.84, -0.62, 0.58), "w": 0.42, "d": 0.38},   # bloody stump end
    ], chamfer=0.12, jitter=0.012, cap_mats=(0, 1))
    mesh_object("Arm_L_Short", bm, c_arms, [M["shell"], M["blood"]])

    # ------------------------------------------------------------------ LEGS
    for name, sx, knee_y, bend in (("Leg_R", -1, -0.16, 0.0), ("Leg_L", 1, -0.10, 0.03)):
        bm = bmesh.new()
        loft(bm, [
            {"p": (0.25 * sx, 0.20, 1.06), "w": 0.42, "d": 0.46},
            {"p": (0.25 * sx, 0.05, 0.80), "w": 0.42, "d": 0.44},
            {"p": (0.20 * sx, knee_y, 0.52 + bend), "w": 0.40, "d": 0.42},   # knee
            {"p": (0.22 * sx, -0.02, 0.26), "w": 0.37, "d": 0.38},
            {"p": (0.24 * sx, 0.06, 0.10), "w": 0.38, "d": 0.40},
        ], chamfer=0.2, jitter=0.01, cap_end=False)
        # foot: short wedge pointing forward
        loft(bm, [
            {"p": (0.24 * sx, 0.14, 0.11), "w": 0.40, "d": 0.20},
            {"p": (0.25 * sx, -0.10, 0.09), "w": 0.42, "d": 0.18},
            {"p": (0.26 * sx, -0.30, 0.07), "w": 0.38, "d": 0.14},
        ], ref=(0, 0, 1), chamfer=0.15, jitter=0.008)
        mesh_object(name, bm, c_legs, [M["shell"]])

    # ------------------------------------------------------------------ HEAD
    # Cranium is compact: no snout. Local origin = centre of the upper gum line.
    hw, hd = HEAD_W, HEAD_D
    bm = bmesh.new()
    loft(bm, [
        {"p": (0, 0, 0.00), "w": hw - 0.04, "d": hd - 0.04},
        {"p": (0, 0, 0.07), "w": hw, "d": hd},
        {"p": (0, 0, 0.34), "w": hw + 0.02, "d": hd + 0.01, "oy": -0.01},
        {"p": (0, 0, 0.50), "w": hw - 0.04, "d": hd - 0.04, "rot": -2},
        {"p": (0.02, 0.02, CRANIUM_H), "w": hw - 0.06, "d": hd - 0.06, "rot": -3},
    ], ref=(0, -1, 0), chamfer=0.20, jitter=0.012, cap_mats=(1, 0))
    cranium = mesh_object("Cranium", bm, c_head, [M["shell"], M["inner"]], location=HEAD_POS)
    cranium.rotation_euler = (math.radians(HEAD_PITCH_DEG), 0, math.radians(-2))

    # Recessed eye sockets: boolean-cut, cutter material transfers to socket walls.
    bm = bmesh.new()
    for (ex, ez, s) in ((-0.26, 0.23, 1.0), (0.19, 0.20, 0.85)):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((ex, -hd / 2 - 0.02, ez))
                              @ Matrix.Diagonal((0.11 * s, 0.20, 0.13 * s, 1)))
    cutter = mesh_object("_EyeCutter", bm, c_head, [M["socket"]], parent=cranium)
    mod = cranium.modifiers.new("EyeSockets", 'BOOLEAN')
    mod.operation, mod.object, mod.solver = 'DIFFERENCE', cutter, 'EXACT'
    mod.material_mode = 'TRANSFER'
    apply_modifiers(cranium)
    bpy.data.objects.remove(cutter)

    bm = bmesh.new()
    for (ex, ez, r) in ((-0.26, 0.23, 0.024), (0.19, 0.20, 0.019)):
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r,
                                   matrix=Matrix.Translation((ex, -hd / 2 + 0.07, ez)))
    mesh_object("Eyes", bm, c_head, [M["eye"]], parent=cranium)

    # Upper teeth: big crooked planks hanging from the front + front half of sides.
    bm = bmesh.new()
    upper_slots = []
    x = -hw / 2 + 0.07
    while x < hw / 2 - 0.06:
        upper_slots.append(("front", x))
        x += rng.uniform(0.065, 0.11)
    for sx in (-1, 1):
        for y in (-0.22, -0.08, 0.06):
            upper_slots.append(("side", (sx, y + rng.uniform(-0.03, 0.03))))
    for kind, v in upper_slots:
        if kind == "front":
            base = Vector((v, -hd / 2 + 0.07, 0.0))
            out = Vector((0, -0.25, 0))
            L = rng.uniform(0.17, 0.33)
        else:
            sx, y = v
            base = Vector((sx * (hw / 2 - 0.08), y, 0.0))
            out = Vector((sx * 0.2, 0, 0))
            L = rng.uniform(0.12, 0.24)
        d = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.15, 0.15), -1)) + out
        tooth(bm, base, d, L, rng.uniform(0.05, 0.085), rng.uniform(0.04, 0.06),
              twist=rng.uniform(-25, 25), taper=rng.uniform(0.35, 0.7))
    mesh_object("Teeth_Upper", bm, c_head, [M["teeth"]], parent=cranium)

    # ------------------------------------------------------------------ JAW
    # Heavy lower jaw on a broken hinge near the back of the cranium base.
    # Mesh is in jaw-local space: hinge at origin, jaw extends to -Y, rim at z=0.
    def jaw_h(x):  # deeper at the chin -> rounded U in front view
        return 0.24 + 0.12 * (1 - (x / (JAW_W / 2)) ** 2)

    def jaw_front(x):  # rounded front corners in plan
        return -JAW_LEN + 0.14 * (abs(x) / (JAW_W / 2)) ** 2.5

    bm = bmesh.new()
    xs = [-JAW_W / 2, -0.36, -0.22, -0.08, 0.06, 0.20, 0.34, JAW_W / 2]
    profs = []
    for x in xs:
        h, yf = jaw_h(x), jaw_front(x)
        profs.append([Vector(p) for p in (
            (x, 0.06, -0.04), (x, 0.04, 0.0), (x, yf + 0.03, 0.0), (x, yf, -0.07),
            (x, yf + 0.05, -h), (x, yf * 0.5, -h * 0.92), (x, 0.06, -0.20))])
    skin(bm, profs)
    jaw = mesh_object("Jaw", bm, c_head, [M["shell"]], parent=cranium,
                      location=(0.0, hd / 2 - 0.12, -0.02))

    # Hollow the jaw into a trough (interior material transfers onto the cut faces).
    bm = bmesh.new()
    profs = []
    ix = JAW_W / 2 - 0.10
    for x in (-ix, -0.2, 0.0, 0.2, ix):
        h, yf = jaw_h(x), jaw_front(x)
        profs.append([Vector(p) for p in (
            (x, 0.20, 0.3), (x, yf + 0.11, 0.3), (x, yf + 0.11, -h + 0.13),
            (x, yf * 0.5, -h * 0.92 + 0.12), (x, 0.20, -0.10))])
    skin(bm, profs)
    jcut = mesh_object("_JawCutter", bm, c_head, [M["inner"]], parent=jaw)
    mod = jaw.modifiers.new("Trough", 'BOOLEAN')
    mod.operation, mod.object, mod.solver = 'DIFFERENCE', jcut, 'EXACT'
    mod.material_mode = 'TRANSFER'
    apply_modifiers(jaw)
    bpy.data.objects.remove(jcut)

    jaw.rotation_euler = (math.radians(JAW_OPEN_DEG), math.radians(-JAW_BROKEN_ROLL_DEG), 0)

    # Lower teeth ride on the jaw rim (parented, so they follow the hinge).
    bm = bmesh.new()
    wall = JAW_W / 2 - 0.05
    x = -wall + 0.03
    slots = []
    while x < wall - 0.02:
        slots.append(("front", x))
        x += rng.uniform(0.07, 0.12)
    for sx in (-1, 1):
        for y in (-0.42, -0.26):
            slots.append(("side", (sx, y + rng.uniform(-0.04, 0.04))))
    for kind, v in slots:
        if kind == "front":
            base = Vector((v, jaw_front(v) + 0.055, 0.0))
            out = Vector((0, 0.05, 0))
            L = rng.uniform(0.15, 0.30)
        else:
            sx, y = v
            base = Vector((sx * wall, y, 0.0))
            out = Vector((sx * 0.25, 0, 0))
            L = rng.uniform(0.12, 0.22)
        d = Vector((rng.uniform(-0.35, 0.35), rng.uniform(0.45, 0.75), 1)) + out
        tooth(bm, base, d, L, rng.uniform(0.05, 0.085), rng.uniform(0.04, 0.06),
              twist=rng.uniform(-30, 30), taper=rng.uniform(0.35, 0.7))
    mesh_object("Teeth_Lower", bm, c_head, [M["teeth"]], parent=jaw)

    # Throat: dark back wall so the mouth reads as a deep cavity, not a see-through gap.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, hd / 2 - 0.22, -0.22))
                          @ Matrix.Diagonal((hw - 0.14, 0.10, 0.44, 1)))
    mesh_object("Throat", bm, c_head, [M["cavity"]], parent=cranium)

    # Cheek membranes: torn flesh webbing between cranium and the rear of the jaw.
    jaw_m = jaw.matrix_basis  # jaw-local -> cranium-local
    bm = bmesh.new()
    for sx in (-1, 1):
        top = [Vector((sx * (hw / 2 - 0.05), y, 0.01)) for y in (hd / 2 - 0.12, 0.05, -0.12)]
        bot = [jaw_m @ Vector((sx * (JAW_W / 2 - 0.04), y, -0.02)) for y in (0.0, -0.17, -0.30)]
        vt = [bm.verts.new(v) for v in top]
        vb = [bm.verts.new(v) for v in bot]
        for i in range(2):
            quad = (vt[i], vt[i + 1], vb[i + 1], vb[i])
            bm.faces.new(quad if sx > 0 else tuple(reversed(quad)))
    cheeks = mesh_object("Cheek_Membranes", bm, c_head, [M["flesh"]], parent=cranium)
    sol = cheeks.modifiers.new("Thickness", 'SOLIDIFY')
    sol.thickness = 0.03

    # ------------------------------------------------------------------ HARDWARE
    hw_bm = bmesh.new()
    # Staple bracket over the head (reads as a single tall rod from the front).
    flat_bar(hw_bm, [(0.06, -1.10, 2.30), (0.10, -1.08, 2.92), (0.16, -0.62, 3.00),
                     (0.10, -0.58, 2.40)], ref=(1, 0, 0))
    spikes = [
        ((-0.40, -0.80, 2.34), (-0.60, -0.58, 2.50)),   # head, right side, raked back
        ((-0.20, -0.02, 2.30), (-0.30, 0.22, 2.68)),    # upper back
        ((0.28, -0.08, 2.28), (0.45, 0.14, 2.60)),      # upper back
        ((-0.92, -0.48, 1.30), (-1.20, -0.48, 1.42)),   # long upper arm
        ((-1.45, -0.90, 0.58), (-1.55, -0.95, 0.85)),   # long forearm
        ((0.86, -0.42, 1.55), (1.15, -0.40, 1.75)),     # short arm
        ((0.92, -0.58, 1.02), (1.12, -0.58, 1.06)),     # short forearm
        ((-0.38, 0.05, 0.78), (-0.66, 0.02, 0.80)),     # right thigh
    ]
    for a, b in spikes:
        flat_bar(hw_bm, [a, b], w=0.08, d=0.06)
    # Bent V-rod jammed into the belly.
    flat_bar(hw_bm, [(0.05, -0.30, 1.42), (-0.10, -0.62, 1.14), (-0.30, -0.66, 1.34)],
             ref=(0, -1, 0))
    mesh_object("Rods", hw_bm, c_hw, [M["metal"]])

    return M


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    bpy.data.meshes.remove(old)


def stats():
    tris = 0
    for ob in bpy.data.collections["MONSTER"].all_objects:
        if ob.type == 'MESH':
            ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
            m = ev.to_mesh()
            t = sum(len(p.vertices) - 2 for p in m.polygons)
            ev.to_mesh_clear()
            tris += t
    return tris


if __name__ == "__main__":
    build()
    os.makedirs(OUT_DIR, exist_ok=True)
    print("TRIANGLES", stats())
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(OUT_BLEND))
    print("SAVED", os.path.abspath(OUT_BLEND))
