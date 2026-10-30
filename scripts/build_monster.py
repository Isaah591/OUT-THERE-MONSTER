"""
OUT THERE monster - procedural Blender builder.

    python build_monster.py [--stage forms|final]      (with the `bpy` module)
    blender -b -P build_monster.py -- [--stage forms|final]

  forms -> model/out_there_monster_forms.blend   (corrected proportions, no surface detail)
  final -> model/out_there_monster.blend         (chiselled shell, wounds, teeth, materials)

Conventions: metres, Z up, the monster faces -Y. Monster's RIGHT side is -X
(the long arm), monster's LEFT side is +X (the short arm).
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import monster_detail as D      # noqa: E402
import monster_materials as MAT  # noqa: E402

OUT_DIR = os.path.join(HERE, "..", "model")

# ---------------------------------------------------------------------------
# Tunable proportions
# ---------------------------------------------------------------------------
JAW_OPEN_DEG = 55.0        # lower jaw hang (checked against the chest below)
JAW_BROKEN_ROLL_DEG = 7.0  # sideways sag of the broken hinge (monster's right lower)
HEAD_POS = Vector((0.02, -0.80, 1.98))  # centre of the cranium base (= upper gum line)
HEAD_PITCH_DEG = -4.0
HEAD_W, HEAD_D, CRANIUM_H = 0.90, 0.79, 0.54
JAW_LEN, JAW_W = 0.81, 0.88

# Limb paths (shared by the forms, the wounds and the rods).
LONG_ARM = [  # (point, width, depth) - upper arm hangs, forearm swings far out to the ground
    ((-0.64, -0.28, 1.97), 0.27, 0.29),
    ((-0.80, -0.40, 1.52), 0.26, 0.28),
    ((-0.93, -0.50, 1.14), 0.27, 0.28),   # elbow (slightly hyper-extended)
    ((-1.00, -0.54, 1.06), 0.30, 0.30),
    ((-1.62, -0.84, 0.48), 0.33, 0.31),
    ((-1.98, -1.02, 0.16), 0.35, 0.30),
    ((-2.10, -1.08, 0.05), 0.33, 0.24),   # club hand, planted flat on the floor
]
SHORT_ARM = [
    ((0.64, -0.28, 2.00), 0.27, 0.29),
    ((0.72, -0.38, 1.70), 0.26, 0.28),
    ((0.80, -0.47, 1.40), 0.27, 0.28),    # elbow
    ((0.82, -0.51, 1.32), 0.29, 0.29),
    ((0.86, -0.62, 0.80), 0.30, 0.28),    # bloody stump end, knee height
]
LEGS = {
    "Leg_R": [((-0.20, 0.16, 1.04), 0.33, 0.35), ((-0.21, 0.02, 0.78), 0.32, 0.34),
              ((-0.17, -0.15, 0.52), 0.30, 0.32), ((-0.19, -0.04, 0.27), 0.27, 0.29),
              ((-0.20, 0.04, 0.12), 0.28, 0.30)],
    "Leg_L": [((0.20, 0.16, 1.04), 0.33, 0.35), ((0.21, 0.04, 0.78), 0.32, 0.34),
              ((0.17, -0.10, 0.55), 0.30, 0.32), ((0.19, -0.02, 0.29), 0.27, 0.29),
              ((0.20, 0.05, 0.12), 0.28, 0.30)],
}

rng = random.Random(7)


# ---------------------------------------------------------------------------
# Scene + geometry helpers
# ---------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def collection(name, parent=None):
    col = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(col)
    return col


def mesh_object(name, bm, col, mats, parent=None, location=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    ob.location = location
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def skin(bm, profiles, cap_start=True, cap_end=True, side_mat=0, cap_mats=(0, 0)):
    rings = [[bm.verts.new(p) for p in prof] for prof in profiles]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])).material_index = side_mat
    if cap_start:
        bm.faces.new(list(reversed(rings[0]))).material_index = cap_mats[0]
    if cap_end:
        bm.faces.new(rings[-1]).material_index = cap_mats[1]
    return rings


def chamfer_rect(w, d, c):
    c = min(c, w * 0.49, d * 0.49)
    hw, hd = w / 2, d / 2
    return [(hw, hd - c), (hw - c, hd), (-hw + c, hd), (-hw, hd - c),
            (-hw, -hd + c), (-hw + c, -hd), (hw - c, -hd), (hw, -hd + c)]


def resample(rings, step):
    if not step:
        return rings
    out = []
    for a, b in zip(rings, rings[1:]):
        pa, pb = Vector(a["p"]), Vector(b["p"])
        k = max(1, math.ceil((pb - pa).length / step))
        for i in range(k):
            t = i / k
            r = {"p": pa.lerp(pb, t)}
            for key in ("w", "d", "ox", "oy", "rot"):
                r[key] = a.get(key, 0.0) * (1 - t) + b.get(key, 0.0) * t
            out.append(r)
    out.append(dict(rings[-1]))
    return out


def frames(points, ref):
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
        out.append((t, side, side.cross(t).normalized()))
    return pts, out


def loft(bm, rings, ref=(0, -1, 0), chamfer=0.22, jitter=0.0, step=None, **kw):
    """Chamfered-box tube through ring dicts {p, w, d, [ox, oy, rot]}: w spans side, d spans fwd."""
    rings = resample(rings, step)
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


def along(path, t):
    """Point at fraction t of a limb path's length."""
    pts = [Vector(p) for p, _, _ in path]
    segs = [(a, b, (b - a).length) for a, b in zip(pts, pts[1:])]
    total = sum(s[2] for s in segs)
    d = t * total
    for a, b, L in segs:
        if d <= L:
            return a.lerp(b, d / L), (b - a).normalized()
        d -= L
    return pts[-1], (pts[-1] - pts[-2]).normalized()


def limb_rings(path):
    return [{"p": p, "w": w, "d": d} for p, w, d in path]


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------
def jaw_h(x):  # deeper at the chin -> rounded U in front view
    return 0.24 + 0.12 * (1 - (x / (JAW_W / 2)) ** 2)


def jaw_front(x):  # rounded front corners in plan
    return -JAW_LEN + 0.14 * (abs(x) / (JAW_W / 2)) ** 2.5


def build_forms(M, detail):
    root = collection("MONSTER")
    C = {k: collection(k, root) for k in ("Head", "Body", "Arms", "Legs", "Hardware")}
    step = 0.12 if detail else None
    parts = {}

    def finish(ob, cell=0.30):
        if detail:
            D.chisel(ob, cell=cell)
        parts[ob.name] = ob
        return ob

    # ------------------------------------------------------------------ TORSO
    # Climber build: broad shoulder girdle and lats, lean ribcage, narrow waist.
    # Spine leans ~25 deg forward; oy < 0 pushes mass back into the upper-back ridge.
    bm = bmesh.new()
    loft(bm, [
        {"p": (0.00, 0.16, 0.95), "w": 0.58, "d": 0.40},
        {"p": (0.00, 0.13, 1.13), "w": 0.54, "d": 0.38},              # narrow waist
        {"p": (0.00, 0.03, 1.34), "w": 0.64, "d": 0.42},
        {"p": (0.00, -0.08, 1.55), "w": 0.84, "d": 0.50, "oy": -0.02},   # lats flare
        {"p": (-0.02, -0.20, 1.77), "w": 1.10, "d": 0.58, "oy": -0.06, "rot": 3},
        {"p": (-0.03, -0.26, 2.00), "w": 1.20, "d": 0.62, "oy": -0.12, "rot": 4},  # shoulder girdle
        {"p": (-0.02, -0.26, 2.22), "w": 0.88, "d": 0.50, "oy": -0.14, "rot": 5},  # trapezius ridge
        {"p": (-0.01, -0.28, 2.36), "w": 0.48, "d": 0.32, "oy": -0.10, "rot": 6},
    ], chamfer=0.16, jitter=0.010, step=step)
    finish(mesh_object("Torso", bm, C["Body"], [M["shell"]]))

    # Neck/trapezius wedge tying the back of the skull into the shoulders (no visible neck).
    bm = bmesh.new()
    loft(bm, [
        {"p": (0.00, -0.22, 1.86), "w": 0.62, "d": 0.42},
        {"p": (0.00, -0.42, 2.06), "w": 0.70, "d": 0.46},
        {"p": (0.01, -0.58, 2.22), "w": 0.66, "d": 0.40},
    ], chamfer=0.2, jitter=0.008, step=step)
    finish(mesh_object("Neck", bm, C["Body"], [M["shell"]]))

    # Deltoid blocks: broad, angular. Long-arm side heavier and slightly dropped.
    bm = bmesh.new()
    loft(bm, [
        {"p": (-0.36, -0.26, 2.08), "w": 0.36, "d": 0.46},
        {"p": (-0.62, -0.27, 2.00), "w": 0.38, "d": 0.46},
        {"p": (-0.76, -0.29, 1.88), "w": 0.28, "d": 0.36},
    ], ref=(0, 0, 1), chamfer=0.22, jitter=0.008)
    loft(bm, [
        {"p": (0.36, -0.26, 2.12), "w": 0.34, "d": 0.44},
        {"p": (0.62, -0.27, 2.07), "w": 0.35, "d": 0.42},
        {"p": (0.75, -0.29, 1.96), "w": 0.27, "d": 0.34},
    ], ref=(0, 0, 1), chamfer=0.22, jitter=0.008)
    finish(mesh_object("Shoulders", bm, C["Body"], [M["shell"]]), cell=0.22)

    # ------------------------------------------------------------------ ARMS
    bm = bmesh.new()
    loft(bm, limb_rings(LONG_ARM), chamfer=0.14, jitter=0.010, step=step)
    arm = finish(mesh_object("Arm_R_Long", bm, C["Arms"], [M["shell"]]))
    D.clamp_to_floor(arm)

    bm = bmesh.new()
    loft(bm, limb_rings(SHORT_ARM), chamfer=0.14, jitter=0.010, step=step, cap_mats=(0, 1))
    finish(mesh_object("Arm_L_Short", bm, C["Arms"], [M["shell"], M["blood"]]))

    # ------------------------------------------------------------------ LEGS
    for name, path in LEGS.items():
        bm = bmesh.new()
        loft(bm, limb_rings(path), chamfer=0.18, jitter=0.008, step=step)
        sx = 1 if path[0][0][0] > 0 else -1
        loft(bm, [   # foot: short wedge pointing forward
            {"p": (0.20 * sx, 0.16, 0.09), "w": 0.31, "d": 0.18},
            {"p": (0.21 * sx, -0.08, 0.08), "w": 0.33, "d": 0.16},
            {"p": (0.22 * sx, -0.28, 0.065), "w": 0.30, "d": 0.12},
        ], ref=(0, 0, 1), chamfer=0.15, jitter=0.006)
        leg = finish(mesh_object(name, bm, C["Legs"], [M["shell"]]), cell=0.24)
        D.clamp_to_floor(leg, 0.0)

    # ------------------------------------------------------------------ HEAD
    hw, hd = HEAD_W, HEAD_D
    bm = bmesh.new()
    loft(bm, [
        {"p": (0, 0, 0.00), "w": hw - 0.04, "d": hd - 0.04},
        {"p": (0, 0, 0.07), "w": hw, "d": hd},
        {"p": (0, 0, 0.34), "w": hw + 0.02, "d": hd + 0.01, "oy": -0.01},
        {"p": (0, 0, 0.50), "w": hw - 0.04, "d": hd - 0.04, "rot": -2},
        {"p": (0.02, 0.02, CRANIUM_H), "w": hw - 0.06, "d": hd - 0.06, "rot": -3},
    ], ref=(0, -1, 0), chamfer=0.20, jitter=0.012, cap_mats=(1, 0))
    cranium = mesh_object("Cranium", bm, C["Head"], [M["shell"], M["inner"]], location=HEAD_POS)
    cranium.rotation_euler = (math.radians(HEAD_PITCH_DEG), 0, math.radians(-2))
    finish(cranium, cell=0.2)

    bm = bmesh.new()
    for (ex, ez, s) in ((-0.25, 0.23, 1.0), (0.18, 0.20, 0.85)):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((ex, -hd / 2 - 0.02, ez))
                              @ Matrix.Diagonal((0.12 * s, 0.24, 0.13 * s, 1)))
    boolean(cranium, mesh_object("_EyeCutter", bm, C["Head"], [M["socket"]], parent=cranium))

    bm = bmesh.new()
    for (ex, ez, r) in ((-0.25, 0.23, 0.017), (0.18, 0.20, 0.014)):
        bmesh.ops.create_cube(bm, size=r * 2, matrix=Matrix.Translation((ex, -hd / 2 + 0.085, ez))
                              @ Matrix.Rotation(0.3, 4, 'Y'))
    mesh_object("Eyes", bm, C["Head"], [M["eye"]], parent=cranium)

    # ------------------------------------------------------------------ JAW
    bm = bmesh.new()
    xs = [-JAW_W / 2, -0.36, -0.22, -0.08, 0.06, 0.20, 0.34, JAW_W / 2]
    profs = []
    for x in xs:
        h, yf = jaw_h(x), jaw_front(x)
        profs.append([Vector(p) for p in (
            (x, 0.06, -0.04), (x, 0.04, 0.0), (x, yf + 0.03, 0.0), (x, yf, -0.07),
            (x, yf + 0.05, -h), (x, yf * 0.5, -h * 0.92), (x, 0.06, -0.20))])
    skin(bm, profs)
    jaw = mesh_object("Jaw", bm, C["Head"], [M["shell"]], parent=cranium,
                      location=(0.0, hd / 2 - 0.12, -0.02))
    finish(jaw, cell=0.2)
    bm = bmesh.new()
    profs = []
    ix = JAW_W / 2 - 0.10
    for x in (-ix, -0.2, 0.0, 0.2, ix):
        h, yf = jaw_h(x), jaw_front(x)
        profs.append([Vector(p) for p in (
            (x, 0.20, 0.3), (x, yf + 0.11, 0.3), (x, yf + 0.11, -h + 0.13),
            (x, yf * 0.5, -h * 0.92 + 0.12), (x, 0.20, -0.10))])
    skin(bm, profs)
    boolean(jaw, mesh_object("_JawCutter", bm, C["Head"], [M["inner"]], parent=jaw))
    jaw.rotation_euler = (math.radians(JAW_OPEN_DEG), math.radians(-JAW_BROKEN_ROLL_DEG), 0)

    build_mouth(M, C, cranium, jaw, detail)

    # Throat: dark back wall so the mouth reads as a deep cavity.
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((0, hd / 2 - 0.12, -0.24))
                          @ Matrix.Diagonal((hw - 0.14, 0.10, 0.50, 1)))
    mesh_object("Throat", bm, C["Head"], [M["throat"]], parent=cranium)

    # Cheek membranes: torn flesh webbing between cranium and the rear of the jaw.
    jaw_m = jaw.matrix_basis
    bm = bmesh.new()
    for sx in (-1, 1):
        top = [Vector((sx * (hw / 2 - 0.05), y, 0.01)) for y in (hd / 2 - 0.12, 0.05, -0.10)]
        bot = [jaw_m @ Vector((sx * (JAW_W / 2 - 0.04), y, -0.02)) for y in (0.0, -0.17, -0.28)]
        vt = [bm.verts.new(v) for v in top]
        vb = [bm.verts.new(v) for v in bot]
        for i in range(2):
            quad = (vt[i], vt[i + 1], vb[i + 1], vb[i])
            bm.faces.new(quad if sx > 0 else tuple(reversed(quad)))
    cheeks = mesh_object("Cheek_Membranes", bm, C["Head"], [M["flesh"]], parent=cranium)
    sol = cheeks.modifiers.new("Thickness", 'SOLIDIFY')
    sol.thickness = 0.03
    D.apply_modifiers(cheeks)
    return C, parts, cranium, jaw


def boolean(target, cutter):
    mod = target.modifiers.new("Cut", 'BOOLEAN')
    mod.operation, mod.object, mod.solver = 'DIFFERENCE', cutter, 'EXACT'
    mod.material_mode = 'TRANSFER'
    D.apply_modifiers(target)
    bpy.data.objects.remove(cutter)


def build_mouth(M, C, cranium, jaw, detail):
    hw, hd = HEAD_W, HEAD_D
    # Upper gum ridge along the front + front half of the sides of the palate.
    upper_path = ([(hw / 2 - 0.07, y, 0) for y in (0.12, -0.10)] +
                  [(x, -hd / 2 + 0.075, 0) for x in (hw / 2 - 0.12, 0.2, 0.0, -0.2, -hw / 2 + 0.12)] +
                  [(-hw / 2 + 0.07, y, 0) for y in (-0.10, 0.12)])
    wall = JAW_W / 2 - 0.05
    lower_path = ([(wall, y, 0) for y in (-0.10, -0.50)] +
                  [(x, jaw_front(x) + 0.06, 0) for x in (wall - 0.08, 0.2, 0.0, -0.2, -wall + 0.08)] +
                  [(-wall, y, 0) for y in (-0.50, -0.10)])
    for name, path, parent, z in (("Gums_Upper", upper_path, cranium, -0.005),
                                  ("Gums_Lower", lower_path, jaw, 0.005)):
        bm = bmesh.new()
        loft(bm, [{"p": (x, y, z), "w": 0.12, "d": 0.075} for x, y, _ in path], ref=(0, 0, 1),
             chamfer=0.35, jitter=0.014, step=0.06)
        mesh_object(name, bm, C["Head"], [M["gum"]], parent=parent)

    # Teeth: huge, crooked, unevenly spaced, chipped and broken. Slot spacing is irregular.
    def slots_front(x0, x1, yfun, outward):
        s, x = [], x0
        while x < x1:
            s.append((Vector((x, yfun(x), 0.0)), outward, True))
            x += rng.uniform(0.05, 0.11)
        return s

    up = slots_front(-hw / 2 + 0.09, hw / 2 - 0.08, lambda x: -hd / 2 + 0.075, Vector((0, -1, 0)))
    for sx in (-1, 1):
        for y in (-0.24, -0.11, 0.03):
            up.append((Vector((sx * (hw / 2 - 0.07), y + rng.uniform(-0.03, 0.03), 0.0)),
                       Vector((sx, 0, 0)), False))
    bm, layer = D.new_tooth_bm()
    D.rng.seed(41)
    D.teeth_row(bm, layer, up, down=(0, 0, -1), out_bias=(0.05, 0.3), lean=(0, 0, 0),
                size={"front_len": (0.16, 0.34), "side_len": (0.10, 0.22)})
    mesh_object("Teeth_Upper", bm, C["Head"], [M["teeth"]], parent=cranium)

    lo = slots_front(-wall + 0.06, wall - 0.04, lambda x: jaw_front(x) + 0.06, Vector((0, -1, 0)))
    for sx in (-1, 1):
        for y in (-0.44, -0.28, -0.14):
            lo.append((Vector((sx * wall, y + rng.uniform(-0.04, 0.04), 0.0)), Vector((sx, 0, 0)), False))
    bm, layer = D.new_tooth_bm()
    # lean back toward the hinge so they stand up-and-forward once the jaw hangs open
    D.teeth_row(bm, layer, lo, down=(0, 0, 1), out_bias=(0.0, 0.25), lean=(0, 0.75, 0),
                size={"front_len": (0.16, 0.32), "side_len": (0.11, 0.22)})
    mesh_object("Teeth_Lower", bm, C["Head"], [M["teeth"]], parent=jaw)


def build_hardware(M, C, parts):
    """Rods are projected onto the finished surface so they stay embedded after edits."""
    bm = bmesh.new()
    cr = parts["Cranium"]
    top_l = D.surface_frame(cr, (0.08, -1.05, 2.8))[0]
    top_r = D.surface_frame(cr, (0.10, -0.55, 2.8))[0]
    a, b = cr.matrix_world @ top_l, cr.matrix_world @ top_r
    flat_bar(bm, [a - Vector((0, 0, 0.12)), a + Vector((0.03, 0.0, 0.42)),
                  b + Vector((0.07, 0.0, 0.45)), b - Vector((0, 0, 0.12))], ref=(1, 0, 0))
    entries = [a, b]

    def spike(part, world_hint, outward, length, tilt=(0, 0, 0)):
        ob = parts[part]
        loc, n, _ = D.surface_frame(ob, world_hint)
        p = ob.matrix_world @ loc
        nw = (ob.matrix_world.to_3x3() @ n).normalized()
        d = (nw + Vector(outward) * 0.6 + Vector(tilt)).normalized()
        flat_bar(bm, [p - d * 0.10, p + d * length], w=0.075, d=0.05)
        entries.append(p)

    la = lambda t, off: along(LONG_ARM, t)[0] + Vector(off)
    sa = lambda t, off: along(SHORT_ARM, t)[0] + Vector(off)
    spike("Cranium", (-0.55, -0.65, 2.32), (-1, 0.6, 0.3), 0.26)
    spike("Torso", (-0.25, 0.20, 2.20), (0, 1, 0.8), 0.40)
    spike("Torso", (0.30, 0.12, 2.10), (0.4, 1, 0.6), 0.32)
    spike("Arm_R_Long", la(0.24, (-0.5, 0, 0)), (-1, 0, 0.3), 0.30)
    spike("Arm_R_Long", la(0.62, (-0.3, 0, 0.5)), (0, 0, 1), 0.28)
    spike("Arm_L_Short", sa(0.25, (0.5, 0, 0)), (1, 0, 0.5), 0.30)
    spike("Arm_L_Short", sa(0.70, (0.5, 0, 0)), (1, 0, 0), 0.22)
    spike("Leg_R", (-0.60, 0.02, 0.80), (-1, 0, 0), 0.28)
    spike("Leg_L", (0.50, 0.10, 0.40), (1, 0.4, 0), 0.18)
    # Bent V-rod jammed into the belly.
    ob = parts["Torso"]
    loc, n, _ = D.surface_frame(ob, (0.05, -0.6, 1.38))
    p = ob.matrix_world @ loc
    nw = n.normalized()
    p1 = p + nw * 0.30 + Vector((-0.04, 0, -0.24))
    flat_bar(bm, [p - nw * 0.10, p1, p1 + Vector((-0.22, -0.03, 0.22))], ref=(0, -1, 0))
    entries.append(p)
    mesh_object("Rods", bm, C["Hardware"], [M["metal"]])
    return entries


# ---------------------------------------------------------------------------
# Damage layout (art-directed; positions are projected onto the surface)
# ---------------------------------------------------------------------------
def damage_pass(M, parts, cranium, jaw, rod_entries):
    blood = []

    def limb_w(path, t, hint, a, b, **kw):
        p, tangent = along(path, t)
        return dict(world=p + Vector(hint) * 0.6, axis=tangent, a=a, b=b, **kw)

    plan = {
        "Arm_R_Long": [limb_w(LONG_ARM, 0.10, (-1, 0, 0.4), 0.11, 0.05, flaps=1),
                       limb_w(LONG_ARM, 0.36, (-0.4, -1, 0), 0.19, 0.075, strands=3, flaps=2),
                       limb_w(LONG_ARM, 0.62, (-1, 0.4, 0.3), 0.16, 0.06, strands=2),
                       limb_w(LONG_ARM, 0.84, (0.2, -1, 0.3), 0.10, 0.05, flaps=1)],
        "Arm_L_Short": [limb_w(SHORT_ARM, 0.42, (1, -0.5, 0), 0.15, 0.07, strands=3, flaps=1),
                        limb_w(SHORT_ARM, 0.80, (0, -1, 0), 0.10, 0.05)],
        "Leg_R": [limb_w(LEGS["Leg_R"], 0.50, (0, -1, 0), 0.14, 0.065, strands=3, flaps=1),
                  limb_w(LEGS["Leg_R"], 0.22, (-1, 0, 0), 0.10, 0.05)],
        "Leg_L": [limb_w(LEGS["Leg_L"], 0.72, (0, -1, 0), 0.17, 0.06, strands=3, flaps=2),
                  limb_w(LEGS["Leg_L"], 0.30, (1, 0.3, 0), 0.09, 0.045)],
        "Torso": [dict(world=(0.40, 0.0, 1.45), axis=(0, 0, 1), a=0.15, b=0.065, strands=3, flaps=1),
                  dict(world=(-0.30, 0.25, 1.95), axis=(0.3, 0, 1), a=0.17, b=0.07, strands=3, flaps=2),
                  dict(world=(0.15, -0.50, 1.50), axis=(0, 0, 1), a=0.09, b=0.045)],
        "Shoulders": [dict(world=(-0.62, -0.27, 2.4), axis=(1, 0, 0), a=0.12, b=0.06, flaps=1)],
        "Cranium": [dict(world=cranium.matrix_world @ Vector((0.50, -0.18, 0.46)), axis=(0, 0, 1),
                         a=0.14, b=0.07, strands=2, flaps=2, depth=0.035)],
        "Jaw": [dict(world=jaw.matrix_world @ Vector((-0.55, -0.42, -0.15)), axis=(0, 1, -1),
                     a=0.11, b=0.05, strands=2, flaps=1, depth=0.03)],
        "Neck": [],
    }
    chips = {"Arm_R_Long": 12, "Arm_L_Short": 7, "Leg_R": 7, "Leg_L": 7, "Torso": 14,
             "Shoulders": 6, "Cranium": 5, "Jaw": 4, "Neck": 4}
    for name, wounds in plan.items():
        D.damage(parts[name], wounds, chips[name], M, blood)

    # Blood sources: mouth rims, stump, rod entries (wound sources were added by damage()).
    for g in ("Gums_Upper", "Gums_Lower"):
        ob = bpy.data.objects[g]
        for v in list(ob.data.vertices)[::6]:
            blood.append((ob.matrix_world @ v.co, 0.16, 3.0))
    blood.append((Vector(SHORT_ARM[-1][0]), 0.40, 1.0))
    for p in rod_entries:
        blood.append((p, 0.12, 3.0))
    for ob in parts.values():
        D.paint_blood(ob, blood, base=0.04)


def check_jaw_clearance():
    def bvh(names):
        verts, polys = [], []
        for n in names:
            ob = bpy.data.objects[n]
            off = len(verts)
            verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
            polys += [[i + off for i in p.vertices] for p in ob.data.polygons]
        return BVHTree.FromPolygons(verts, polys)
    hits = bvh(["Jaw", "Teeth_Lower"]).overlap(bvh(["Torso", "Arm_L_Short", "Arm_R_Long"]))
    print("JAW-vs-BODY overlapping face pairs:", len(hits))
    return len(hits)


def stats():
    tris = 0
    rows = []
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in bpy.data.collections["MONSTER"].all_objects:
        if ob.type == 'MESH':
            m = ob.evaluated_get(dg).to_mesh()
            t = sum(len(p.vertices) - 2 for p in m.polygons)
            ob.evaluated_get(dg).to_mesh_clear()
            rows.append((ob.name, t))
            tris += t
    for n, t in sorted(rows, key=lambda r: -r[1]):
        print("  %-18s %6d tris" % (n, t))
    return tris


def build(stage):
    reset_scene()
    bpy.context.scene.unit_settings.system = 'METRIC'
    detail = stage == "final"
    M = MAT.build_all()
    C, parts, cranium, jaw = build_forms(M, detail)
    bpy.context.view_layer.update()
    rods = build_hardware(M, C, parts)
    if detail:
        damage_pass(M, parts, cranium, jaw, rods)
    bpy.context.view_layer.update()
    check_jaw_clearance()
    print("TRIANGLES", stats())


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "final"
    build(stage)
    os.makedirs(OUT_DIR, exist_ok=True)
    name = "out_there_monster.blend" if stage == "final" else "out_there_monster_forms.blend"
    path = os.path.abspath(os.path.join(OUT_DIR, name))
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)
