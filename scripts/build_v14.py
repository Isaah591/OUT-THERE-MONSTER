"""
v14 ("Experimental 10") variation of the OUT THERE monster: mouth curvature and the brow's expression on
v13 (head_v14.py). Opened from v13's file:
- the cranium is rebuilt with three changes only - the upper jaw's edge (irregular, through the upper
  teeth's roots, rising toward the cheek), heavy brow ledges over the sockets, and the sockets tilted
  the sheet's way (inner corners lower) and deeper; every cranium vertex outside those zones stays
  v13's, attributes included (checked below);
- the lower jaw (a swept, hooked tooth row), both rows of teeth (re-seated on the new edges), the gums,
  the mouth's tissue (curved corner webs instead of flat walls) and the pupils (deeper) are rebuilt.
The body, the crown bracket, the torn skull sides, palate and throat, the materials and the cameras are
untouched and checked vertex by vertex against v13 before saving. v13 is kept unchanged
(build_v13.py -> model/out_there_monster_v13.blend).

    python build_v14.py [out.blend]             (with the `bpy` module, Blender 5.0, and scikit-image)
    V14_FAST=1 python build_v14.py out.blend    (coarser voxels for the jaw, for quick checks)

Writes model/out_there_monster_v14.blend.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import build_v7 as B7  # noqa: E402  (stats, shading helpers)
import head_v14 as H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V13 = os.path.join(ROOT, "model", "out_there_monster_v13.blend")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
KEPT_HEAD = ("Crown_Bracket", "Torn_Flesh", "Palate", "Throat")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7-v13
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 76.0                         # starting value; solved from the side panel in head_v14
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG
FAST = bool(os.environ.get("V14_FAST"))
EDGE_ZONE = (-0.14, 0.15, 0.16)             # the upper jaw's edge: cranium z from .. to, y below


def vertices(names):
    out = {}
    for n in names:
        ob = bpy.data.objects[n]
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        out[n] = (co, np.array(ob.matrix_world))
    return out


def zone(p):
    """Which of v14's cranium changes a cranium-space point belongs to: 'eyes' (within 0.08 u of a v13 or
    v14 socket box, or in a brow ledge's reach above it), 'edge' (the face block's lower edge), or None."""
    for (cx, cz), (hw, hh), tilt, depth in H.SOCKETS + H.SOCKETS_V13:
        y0 = float(H.face_y(cx))
        a = np.radians(tilt)
        dx, dz = p[0] - cx, p[2] - cz
        lx, lz = np.cos(a) * dx - np.sin(a) * dz, np.sin(a) * dx + np.cos(a) * dz
        if (abs(lx) <= hw + 0.13 and -hh - 0.08 <= lz <= hh + 0.22 and y0 - 0.25 <= p[1] <= y0 + depth + 0.08):
            return "eyes"
    if EDGE_ZONE[0] <= p[2] <= EDGE_ZONE[1] and p[1] <= EDGE_ZONE[2]:
        return "edge"
    return None


def clearance():
    """Overlap of the lower jaw's parts with the body (the jaw's rear sits inside the neck)."""
    def bvh(n):
        ob = bpy.data.objects[n]
        verts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        return BVHTree.FromPolygons(verts, [p.vertices[:] for p in ob.data.polygons])
    total = 0
    body = {n: bvh(n) for n in ("Torso", "Arm_L_Short", "Arm_R_Long")}
    for a in ("Teeth_Lower", "Gums_Lower", "Mouth_Floor", "Jaw"):
        ta = bvh(a)
        for b, tb in body.items():
            hits = ta.overlap(tb)
            if hits:
                ob = bpy.data.objects[a]
                ys = [ob.data.polygons[i].center.y for i, _ in hits]
                print("  overlap %s / %s: %d pairs, jaw-local y %.2f..%.2f (hinge 0)"
                      % (a, b, len(hits), min(ys), max(ys)))
            total += len(hits)
    print("JAW/TEETH/GUMS/FLOOR-vs-BODY overlapping face pairs:", total)


def build(out):
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=V13)
    before = vertices(BODY_OBJECTS + KEPT_HEAD)
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "bar": obj["Crown_Bracket"].material_slots[0].material,
         "teeth": obj["Teeth_Upper"].material_slots[0].material, "eye": obj["Eyes"].material_slots[0].material,
         "throat": obj["Throat"].material_slots[0].material,
         "tissue": obj["Gums_Upper"].material_slots[0].material}          # v13's (= v10's) materials, unchanged
    col = bpy.data.collections["Head"]
    sk = obj["Cranium"]
    for n in H.MOUTH_OBJECTS:
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    old_sk, new_sk = H.build_head_v14(M, col, sk, HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG,
                                      scale=HEAD_SCALE, fast=FAST)
    print("head %.1fs" % (time.time() - t0))
    from scipy.spatial import cKDTree
    d_new, _ = cKDTree(old_sk).query(new_sk)
    d_old, _ = cKDTree(new_sk).query(old_sk)
    moved = np.r_[new_sk[d_new > 1e-7], old_sk[d_old > 1e-7]]
    zones = [zone(p) for p in moved]
    outside = sum(z is None for z in zones)
    print("CRANIUM: %d -> %d vertices; %d new and %d removed - at the sockets and brows %d, at the upper jaw's "
          "edge %d, elsewhere %d; every other vertex v13's, attributes included"
          % (len(old_sk), len(new_sk), int((d_new > 1e-7).sum()), int((d_old > 1e-7).sum()),
             zones.count("eyes"), zones.count("edge"), outside))
    if outside:
        raise SystemExit("the cranium changed outside the edited zones - not saving")
    B7.soft_shade(("Gums_Upper", "Gums_Lower", "Mouth_Cheek_Flesh", "Mouth_Floor", "Mouth_Inner_Walls", "Jaw_Strands",
                   "Mouth_Corner_Rims"),
                  sharp=60)
    B7.soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=50)
    bpy.context.view_layer.update()
    after = vertices(BODY_OBJECTS + KEPT_HEAD)
    same = {n: np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1]) for n in before}
    print("BODY UNCHANGED (vertex-identical to v13/v12/v11/v10/v9/v8/v7):", all(same[n] for n in BODY_OBJECTS))
    print("KEPT HEAD PARTS UNCHANGED (vertex-identical to v13: %s): %s" % (", ".join(KEPT_HEAD),
                                                                        all(same[n] for n in KEPT_HEAD)))
    if not all(same.values()):
        raise SystemExit("body or kept head parts changed - not saving: %s" % [n for n, v in same.items() if not v])
    clearance()
    B7.stats(bpy.data.collections["MONSTER"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v14.blend"))
