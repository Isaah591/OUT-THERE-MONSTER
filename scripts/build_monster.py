"""
OUT THERE monster - procedural Blender builder (v2: deterioration / realism pass).

    python build_monster.py [--stage forms|final]      (with the `bpy` module)
    blender -b -P build_monster.py -- [--stage forms|final]

  forms -> model/out_there_monster_forms.blend   (shapes only, no damage)
  final -> model/out_there_monster.blend         (full detail)

Conventions: metres, Z up, the monster faces -Y. Monster's RIGHT side is -X
(the long arm), monster's LEFT side is +X (the short arm).
Modules: monster_head (skull/jaw/mouth), monster_detail (geometry ops, damage, teeth),
monster_materials (procedural shaders).
"""
import math
import os
import random
import sys

import bpy
import bmesh
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import monster_detail as D      # noqa: E402
import monster_head as H        # noqa: E402
import monster_materials as MAT  # noqa: E402

OUT_DIR = os.path.join(HERE, "..", "model")

# ---------------------------------------------------------------------------
# Tunable proportions
# ---------------------------------------------------------------------------
# ---- R08-faithful proportions (measured from references/r08_reference_sheet_primary.webp,
# overall height 2.8 m => ~0.0051 m per sheet pixel). The ONLY intended deviation from R08
# is the lower jaw: forced / broken open into a Pac-Man-like wedge around its rear hinge.
JAW_OPEN_DEG = 58.0        # lower jaw forced far past a natural range (R08 is nearly closed)
JAW_BROKEN_ROLL_DEG = 5.0  # sideways sag of the broken hinge (monster's right lower)
HEAD_SCALE = 0.633         # head built at reference size, scaled to R08's 0.57 m width
HEAD_POS = Vector((0.0, -0.44, 2.48))   # centre of the upper gum line: head sits on the torso top
HEAD_ROT = (math.radians(-9.0), math.radians(-2.0), math.radians(-2.0))  # forward nod, as in R08's side view

# Limb paths (shared by the forms, the wounds and the rods): (point, width, depth)
LONG_ARM = [   # monster's right: hangs out to the elbow, forearm reaches forward to the floor
    ((-0.66, -0.12, 2.42), 0.36, 0.38),   # shoulder block top
    ((-0.70, -0.13, 2.28), 0.37, 0.39),
    ((-0.84, -0.17, 1.86), 0.36, 0.37),
    ((-0.98, -0.22, 1.44), 0.36, 0.36),   # elbow
    ((-0.98, -0.40, 1.00), 0.38, 0.37),   # heavy forearm
    ((-0.95, -0.65, 0.50), 0.39, 0.37),
    ((-0.93, -0.80, 0.20), 0.40, 0.36),
    ((-0.92, -0.86, 0.04), 0.37, 0.30),   # club hand resting on the floor
]
SHORT_ARM = [  # monster's left: a straight slab hanging to just above the knee
    ((0.62, -0.18, 2.39), 0.32, 0.34),    # shoulder block top
    ((0.64, -0.18, 2.24), 0.33, 0.35),
    ((0.69, -0.20, 1.70), 0.31, 0.32),
    ((0.73, -0.21, 1.25), 0.31, 0.31),
    ((0.77, -0.22, 0.76), 0.30, 0.30),    # bloody stump end
]
LEGS = {   # thick straight blocks, slight stance asymmetry
    "Leg_R": [((-0.20, 0.00, 1.18), 0.33, 0.36), ((-0.20, -0.02, 0.86), 0.33, 0.35),
              ((-0.20, -0.03, 0.56), 0.32, 0.34), ((-0.20, 0.00, 0.12), 0.31, 0.33)],
    "Leg_L": [((0.24, 0.00, 1.18), 0.37, 0.38), ((0.25, -0.02, 0.86), 0.36, 0.37),
              ((0.25, -0.04, 0.56), 0.35, 0.36), ((0.25, 0.00, 0.12), 0.34, 0.35)],
}
SPINE = [(0.0, 0.02, 1.10), (0.0, 0.03, 1.50), (0.0, 0.04, 1.90), (0.0, 0.05, 2.30)]

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


def mesh_object(name, bm, col, mats, parent=None):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return D.bm_object(name, bm, col, mats, parent)


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


def section(w, d, c):
    """12-point chamfered box section (corners chamfered, side midpoints free to kink)."""
    c = min(c, w * 0.45, d * 0.45)
    hw, hd = w / 2, d / 2
    return [(hw, hd - c), (hw - c, hd), (0.0, hd), (-hw + c, hd), (-hw, hd - c), (-hw, 0.0),
            (-hw, -hd + c), (-hw + c, -hd), (0.0, -hd), (hw - c, -hd), (hw, -hd + c), (hw, 0.0)]


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


def loft(bm, rings, ref=(0, -1, 0), chamfer=0.22, irreg=0.0, step=None, seed=0.0, **kw):
    """Chamfered-box tube through ring dicts {p, w, d, [ox, oy, rot]}.
    irreg: coherent radial bulge/dent amount (noise sampled at each vertex position)."""
    rings = resample(rings, step)
    pts, frs = frames([r["p"] for r in rings], ref)
    off = Vector((seed * 3.7, seed * 1.3 + 4, seed * 2.9 + 8))
    profiles = []
    for r, p, (t, side, fwd) in zip(rings, pts, frs):
        sec = section(r["w"], r["d"], chamfer * min(r["w"], r["d"]))
        rot = math.radians(r.get("rot", 0.0))
        cr, sr = math.cos(rot), math.sin(rot)
        centre = p + side * r.get("ox", 0.0) + fwd * r.get("oy", 0.0)
        prof = []
        for (x, y) in sec:
            x, y = x * cr - y * sr, x * sr + y * cr
            v = centre + side * x + fwd * y
            if irreg:
                k = 1 + irreg * (noise.noise(v * 2.3 + off) + 0.5 * noise.noise(v * 5.5 + off))
                v = centre + (v - centre) * k
            prof.append(v)
        profiles.append(prof)
    return skin(bm, profiles, **kw)


def flat_bar(bm, points, w=0.085, d=0.035, ref=(0, 0, 1)):
    pts, frs = frames(points, ref)
    profs = []
    for p, (t, side, fwd) in zip(pts, frs):
        profs.append([p + side * x + fwd * y for x, y in
                      ((w / 2, d / 2), (-w / 2, d / 2), (-w / 2, -d / 2), (w / 2, -d / 2))])
    skin(bm, profs)


def along(path, t):
    pts = [Vector(p) for p, _, _ in path]
    segs = [(a, b, (b - a).length) for a, b in zip(pts, pts[1:])]
    d = t * sum(s[2] for s in segs)
    for a, b, L in segs:
        if d <= L:
            return a.lerp(b, d / L), (b - a).normalized()
        d -= L
    return pts[-1], (pts[-1] - pts[-2]).normalized()


def limb_rings(path):
    return [{"p": p, "w": w, "d": d} for p, w, d in path]


# ---------------------------------------------------------------------------
# Body
# ---------------------------------------------------------------------------
def build_body(M, C, detail):
    step = 0.11 if detail else None
    ir = (lambda a: a) if detail else (lambda a: 0.0)
    parts = {}

    # Torso (R08): a big, near-vertical, slightly tapered box with a rounded upper back.
    # The upper front recedes a little behind the jaw (hidden in front view) so the forced-open
    # lower jaw has room to hang in front of the chest.
    bm = bmesh.new()
    loft(bm, [
        {"p": (0.00, 0.02, 1.10), "w": 0.80, "d": 0.48},
        {"p": (0.00, 0.02, 1.28), "w": 0.84, "d": 0.50},
        {"p": (0.00, 0.03, 1.70), "w": 0.88, "d": 0.52},
        {"p": (0.00, 0.09, 2.02), "w": 0.91, "d": 0.48},
        {"p": (0.00, 0.12, 2.28), "w": 0.90, "d": 0.44},
        {"p": (0.00, 0.12, 2.40), "w": 0.80, "d": 0.38},
    ], chamfer=0.14, irreg=ir(0.03), step=step, seed=1)
    torso = mesh_object("Torso", bm, C["Body"], [M["shell"]])
    pieces = []
    bm = bmesh.new()   # short hidden neck block tying the back of the skull into the torso top
    loft(bm, [{"p": (0.00, 0.08, 2.30), "w": 0.46, "d": 0.30},
              {"p": (0.00, -0.12, 2.52), "w": 0.44, "d": 0.28}], chamfer=0.2, irreg=ir(0.03), seed=2)
    pieces.append(mesh_object("_neck", bm, C["Body"], [M["shell"]]))
    if False:   # v3: simple structure - no vertebra knobs / scapula plates
        # bony structure pushing through the shell: vertebra knobs and scapula plates
        bm = bmesh.new()
        for t in (0.32, 0.42, 0.52, 0.62, 0.72, 0.82):
            f = t * (len(SPINE) - 1)
            k = int(f)
            p = Vector(SPINE[k]).lerp(Vector(SPINE[min(k + 1, len(SPINE) - 1)]), f - k)
            back = Vector((0, 1, 0.35)).normalized()
            base = p + back * (0.20 + 0.10 * t)
            s = rng.uniform(0.05, 0.075)
            loft(bm, [{"p": base, "w": s * 1.3, "d": s},
                      {"p": base + back * 0.08 * rng.uniform(0.8, 1.3), "w": s * 0.5, "d": s * 0.4}],
                 ref=(0, 0, 1), chamfer=0.1)
        for sx, z, tilt in ((-1, 1.98, 4.0), (1, 2.06, -2.0)):     # asymmetric scapulae
            c = Vector((sx * 0.30, 0.06, z))
            loft(bm, [{"p": c + Vector((0, -0.04, 0.13)), "w": 0.20, "d": 0.08},
                      {"p": c + Vector((sx * 0.04, 0.03, 0.0)), "w": 0.26, "d": 0.11, "rot": tilt},
                      {"p": c + Vector((sx * 0.08, -0.01, -0.16)), "w": 0.10, "d": 0.06}],
                 ref=(0, -1, 0), chamfer=0.25)
        pieces.append(mesh_object("_bones", bm, C["Body"], [M["shell"]]))
    bpy.context.view_layer.update()
    D.union(torso, pieces)
    if detail:
        D.chisel(torso, level=0, plate=0.01, lump=0.012)
        D.deform(torso, 0.012, 1.8, seed=1)
        D.facet_cuts(torso, 14, M, size=(0.3, 0.5), depth=(0.0, 0.01), tilt=(3, 8))
    parts["Torso"] = torso

    for name, path, seed in (("Arm_R_Long", LONG_ARM, 5), ("Arm_L_Short", SHORT_ARM, 6)):
        bm = bmesh.new()
        loft(bm, limb_rings(path), chamfer=0.12, irreg=ir(0.035), step=step, seed=seed,
             cap_mats=(0, 1) if name == "Arm_L_Short" else (0, 0))
        ob = mesh_object(name, bm, C["Arms"], [M["shell"], M["flesh"]])
        if detail:
            D.chisel(ob, level=0, plate=0.01, lump=0.01)
            D.deform(ob, 0.01, 2.0, seed=seed)
            D.facet_cuts(ob, 10 if name == "Arm_R_Long" else 6, M, size=(0.3, 0.5), depth=(0.0, 0.01), tilt=(3, 8))
        D.clamp_to_floor(ob)
        parts[name] = ob

    for name, path in LEGS.items():
        seed = 7 if name == "Leg_R" else 8
        bm = bmesh.new()
        loft(bm, limb_rings(path), chamfer=0.13, irreg=ir(0.035), step=step, seed=seed)
        fx = path[-1][0][0]
        fw = path[-1][1] + 0.05
        loft(bm, [{"p": (fx, 0.14, 0.07), "w": fw, "d": 0.14},      # blocky foot
                  {"p": (fx, -0.10, 0.065), "w": fw, "d": 0.13},
                  {"p": (fx, -0.27, 0.055), "w": fw - 0.03, "d": 0.11}],
             ref=(0, 0, 1), chamfer=0.15, irreg=ir(0.03), seed=seed + 10)
        ob = mesh_object(name, bm, C["Legs"], [M["shell"]])
        if detail:
            D.chisel(ob, level=0, plate=0.01, lump=0.01)
            D.deform(ob, 0.01, 2.0, seed=seed)
            D.facet_cuts(ob, 6, M, size=(0.3, 0.5), depth=(0.0, 0.01), tilt=(3, 8),
                         weight=lambda w: 0.0 if w.z < 0.2 else 1.0)   # spare the feet
        D.clamp_to_floor(ob, 0.0)
        parts[name] = ob
    return parts


def build_hardware(M, C, parts, extra_bars):
    """Rods are projected onto the finished surface so they stay embedded."""
    bm = bmesh.new()
    cr = parts["Cranium"]
    top_l = D.surface_frame(cr, cr.matrix_world @ Vector((0.06, -0.26, 0.9)))[0]
    top_r = D.surface_frame(cr, cr.matrix_world @ Vector((0.08, 0.22, 0.9)))[0]
    a, b = cr.matrix_world @ top_l, cr.matrix_world @ top_r
    hs = HEAD_SCALE   # small staple bracket on the crown (R08: ~0.15 m tall)
    flat_bar(bm, [a - Vector((0, 0, 0.12 * hs)), a + Vector((0.0, 0.0, 0.24 * hs)),
                  b + Vector((0.03, 0.0, 0.25 * hs)), b - Vector((0, 0, 0.12 * hs))], w=0.06, d=0.03,
             ref=(1, 0, 0))
    entries = [a, b]

    def spike(part, world_hint, outward, length):
        ob = parts[part]
        loc, n, _ = D.surface_frame(ob, world_hint)
        p = ob.matrix_world @ loc
        nw = (ob.matrix_world.to_3x3() @ n).normalized()
        d = (nw + Vector(outward) * 0.6).normalized()
        flat_bar(bm, [p - d * 0.10, p + d * length], w=0.075, d=0.05)
        entries.append(p)

    la = lambda t, off: along(LONG_ARM, t)[0] + Vector(off)
    sa = lambda t, off: along(SHORT_ARM, t)[0] + Vector(off)
    spike("Torso", (0.30, 0.40, 2.30), (0.2, 1, 1.0), 0.30)            # back of left shoulder
    spike("Arm_R_Long", la(0.72, (0, -0.5, 0.2)), (0, -1, 0.6), 0.22)   # forearm stub, forward
    spike("Arm_R_Long", la(0.40, (-0.5, 0, 0)), (-1, 0, 0.2), 0.16)     # outer elbow stub
    spike("Arm_L_Short", sa(0.40, (0.5, 0, 0)), (1, 0, 0.1), 0.18)      # short-arm side stub
    spike("Leg_L", (0.60, -0.02, 0.50), (1, 0, 0), 0.20)               # shin stub
    ob = parts["Torso"]                     # bent hook rod jammed into the belly
    loc, n, _ = D.surface_frame(ob, (-0.05, -0.6, 1.62))
    p = ob.matrix_world @ loc
    p1 = p + n * 0.42 + Vector((-0.12, 0, -0.12))
    flat_bar(bm, [p - n * 0.10, p1, p1 + Vector((-0.04, -0.03, 0.24))], ref=(0, -1, 0))
    entries.append(p)
    for p0, p1 in extra_bars:              # rods driven into wounds
        flat_bar(bm, [p0, p1], w=0.07, d=0.045)
        entries.append(p0)
    mesh_object("Rods", bm, C["Hardware"], [M["metal"]])
    return entries


# ---------------------------------------------------------------------------
# Damage layout (art-directed; positions are projected onto the surface)
# ---------------------------------------------------------------------------
def damage_pass(M, parts, sk, jaw):
    blood, bars = [], []

    def lw(path, t, hint, a, b, **kw):
        """Wound on a limb: ray-cast from outside, along -hint, onto the limb at fraction t
        (a nearest-point search from far away can land on the wrong face, e.g. the foot)."""
        p, tangent = along(path, t)
        h = Vector(hint)
        h = (h - tangent * h.dot(tangent)).normalized()
        return dict(world=p + h * 0.5, ray=(p + h * 0.8, -h), axis=tangent, a=a, b=b, **kw)

    LA, SA, LR, LL = LONG_ARM, SHORT_ARM, LEGS["Leg_R"], LEGS["Leg_L"]
    # Localized, believable damage (R08 sheet): torn rust strata on the limbs - heaviest on
    # forearms, knees and shins - and on the torso sides; the chest front stays mostly
    # intact. Only a few shallow flesh tears, at stress points.
    tears = {
        "Arm_R_Long": [lw(LA, 0.36, (-0.4, -1, 0), 0.16, 0.055, shards=4),
                       lw(LA, 0.72, (-1, 0.3, 0.3), 0.14, 0.05, shards=4)],
        "Arm_L_Short": [lw(SA, 0.48, (1, -0.5, 0), 0.13, 0.05, shards=4)],
        "Leg_R": [lw(LR, 0.50, (0, -1, 0), 0.14, 0.05, shards=4)],
        "Leg_L": [lw(LL, 0.68, (0, -1, 0.1), 0.18, 0.055, shards=5)],
        "Torso": [dict(world=(-0.66, -0.26, 2.52), axis=(1, 0, 0.3), a=0.21, b=0.09, shards=4, rod=0.3),
                  dict(world=(0.40, -0.02, 1.74), axis=(0, 0, 1), a=0.15, b=0.055, shards=4)],
        "Cranium": [dict(world=sk.matrix_world @ Vector((0.40, -0.30, 0.10)), axis=(0, 0, 1),
                         a=0.11, b=0.05, shards=5, depth=0.035)],
        "Jaw": [],
    }
    peels = {
        "Arm_R_Long": [lw(LA, 0.12, (-1, 0, 0.4), 0.126, 0.154), lw(LA, 0.52, (0, 1, 0), 0.112, 0.182),
                       lw(LA, 0.62, (0.3, -1, 0.4), 0.126, 0.168), lw(LA, 0.86, (-1, 0, 0.2), 0.140, 0.168),
                       lw(LA, 0.94, (0.3, -1, 0.2), 0.112, 0.140)],
        "Arm_L_Short": [lw(SA, 0.22, (1, 0, 0.3), 0.112, 0.140), lw(SA, 0.70, (0.4, -1, 0), 0.126, 0.154),
                        lw(SA, 0.88, (1, 0.4, 0), 0.112, 0.140)],
        "Leg_R": [lw(LR, 0.28, (-1, 0, 0), 0.112, 0.154), lw(LR, 0.72, (0, -1, 0), 0.126, 0.154),
                  lw(LR, 0.78, (-1, 0.3, 0), 0.112, 0.140)],
        "Leg_L": [lw(LL, 0.30, (1, 0.3, 0), 0.112, 0.154), lw(LL, 0.48, (0, 1, 0), 0.112, 0.154),
                  lw(LL, 0.80, (1, -1, 0), 0.112, 0.140)],
        "Torso": [dict(world=(-0.52, -0.12, 1.95), axis=(0, 0, 1), a=0.196, b=0.140),
                  dict(world=(0.50, -0.32, 2.15), axis=(0, 0, 1), a=0.168, b=0.126),
                  dict(world=(-0.05, 0.32, 1.62), axis=(1, 0, 0), a=0.210, b=0.126),
                  dict(world=(0.20, -0.34, 1.36), axis=(1, 0, 0), a=0.140, b=0.098)],
        "Cranium": [dict(world=sk.matrix_world @ Vector((0.30, -0.25, 0.56)), axis=(1, 0, 0), a=0.168, b=0.112),
                    dict(world=sk.matrix_world @ Vector((-0.44, -0.05, 0.30)), axis=(0, 1, 0), a=0.140, b=0.098)],
        "Jaw": [dict(world=jaw.matrix_world @ Vector((0.15, -0.85, -0.25)), axis=(1, 0, 0), a=0.168, b=0.098)],
    }
    chips = {k: 0 for k in tears}
    for name in tears:
        D.damage(parts[name], tears[name], peels[name], chips[name], M, blood, bars)

    # blood sources: mouth (drips run down the chin and onto the chest), stump
    for g in ("Gums_Upper", "Gums_Lower"):
        ob = bpy.data.objects[g]
        for v in list(ob.data.vertices)[::10]:
            blood.append((ob.matrix_world @ v.co, 0.16, 3.0))
    for x in (-0.3, -0.05, 0.2):
        blood.append((jaw.matrix_world @ Vector((x, H.jaw_front(x), -0.05)), 0.22, 4.0))
    blood.append((Vector(SHORT_ARM[-1][0]), 0.40, 1.0))
    return blood, bars


def check_jaw_clearance():
    def bvh(names):
        verts, polys = [], []
        for n in names:
            ob = bpy.data.objects[n]
            off = len(verts)
            verts += [ob.matrix_world @ v.co for v in ob.data.vertices]
            polys += [[i + off for i in p.vertices] for p in ob.data.polygons]
        return BVHTree.FromPolygons(verts, polys)
    total = 0
    for a in ("Teeth_Lower", "Gums_Lower", "Tongue", "Jaw"):
        for b in ("Torso", "Arm_L_Short", "Arm_R_Long"):
            ob = bpy.data.objects[a]
            hits = bvh([a]).overlap(bvh([b]))
            if hits:
                ys = [ob.data.polygons[i].center.y for i, _ in hits]
                print("  overlap %s / %s: %d pairs, jaw-local y %.2f..%.2f (hinge at 0, chin at -%.2f)"
                      % (a, b, len(hits), min(ys), max(ys), H.JAW_LEN))
            total += len(hits)
    print("JAW/TEETH/GUMS/TONGUE-vs-BODY overlapping face pairs:", total)
    return total


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
        print("  %-20s %6d tris" % (n, t))
    return tris


def build(stage):
    reset_scene()
    bpy.context.scene.unit_settings.system = 'METRIC'
    detail = stage == "final"
    M = MAT.build_all()
    root = collection("MONSTER")
    C = {k: collection(k, root) for k in ("Head", "Body", "Arms", "Legs", "Hardware")}
    parts = build_body(M, C, detail)
    sk, jaw, _ = H.build_head(M, C["Head"], HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG,
                              scale=HEAD_SCALE)
    parts["Cranium"], parts["Jaw"] = sk, jaw
    bpy.context.view_layer.update()
    blood, bars = damage_pass(M, parts, sk, jaw) if detail else ([], [])
    entries = build_hardware(M, C, parts, bars)
    for p in entries:
        blood.append((p, 0.12, 3.0))
    if detail:
        for ob in parts.values():
            D.dissolve_planar(ob)
        for ob in list(parts.values()) + [bpy.data.objects["Jaw_Hinges"]]:
            D.paint_blood(ob, blood, base=0.03)
            D.facet_attr(ob)
    for name in ("Mouth_Corner_Tissue", "Mouth_Tendons", "Tongue", "Gums_Upper",
                 "Gums_Lower", "Palate", "Throat", "Teeth_Upper", "Teeth_Lower"):
        D.smooth_organic(bpy.data.objects[name], range(8),
                         sharp_angle=42 if name.startswith(("Teeth", "Gums")) else None)
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
