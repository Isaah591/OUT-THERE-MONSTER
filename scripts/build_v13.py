"""
v13 ("Experimental 09") variation of the OUT THERE monster: a mouth and eye-socket reconstruction on
v12 (head_v13.py). Opened from v12's file:
- the eye sockets are re-cut in the cranium (restore_sockets): small horizontal rectangles around the
  unchanged pupils, without the stepped frame; every cranium vertex away from the sockets stays v12's,
  attributes included (checked below);
- the lower jaw, the lower teeth and gums and the mouth's tissue are rebuilt (build_mouth): the jaw at
  the side panel's own height, its U along the sheet's lower gum line in the front and three-quarter
  panels, narrowing to a narrow chin; the lower teeth on it at v12's size.
The body, the upper jaw (upper teeth and gums), the eyes (pupils), the crown bracket, the torn skull
sides, palate and throat, the materials and the cameras are untouched and checked vertex by vertex
against v12 before saving. v12 is kept unchanged (build_v12.py -> model/out_there_monster_v12.blend).

    python build_v13.py [out.blend]             (with the `bpy` module, Blender 5.0, and scikit-image)
    V13_FAST=1 python build_v13.py out.blend    (coarser voxels for the jaw, for quick checks)

Writes model/out_there_monster_v13.blend.
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
import head_v13 as H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V12 = os.path.join(ROOT, "model", "out_there_monster_v12.blend")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
KEPT_HEAD = ("Eyes", "Crown_Bracket", "Torn_Flesh", "Palate", "Throat", "Teeth_Upper", "Gums_Upper")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7-v12
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 76.0                         # starting value; solved from the side panel in head_v13
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG
FAST = bool(os.environ.get("V13_FAST"))


def vertices(names):
    out = {}
    for n in names:
        ob = bpy.data.objects[n]
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        out[n] = (co, np.array(ob.matrix_world))
    return out


def socket_distance(p):
    """Distance (head units) from cranium-space point p to the nearest eye-socket box, v12's (with its
    stepped frame, 0.03 wider) or v13's, each turned by its tilt in the face plane."""
    best = 9.0
    framed = [(c, (h[0] + 0.03, h[1] + 0.03), t, d) for c, h, t, d in H.SOCKETS_V12]
    for (cx, cz), (hw, hh), tilt, depth in H.SOCKETS + framed:
        y0 = float(H.face_y(cx)) - 0.25
        a = np.radians(tilt)
        dx, dz = p[0] - cx, p[2] - cz
        lx, lz = np.cos(a) * dx - np.sin(a) * dz, np.sin(a) * dx + np.cos(a) * dz     # into the box's frame
        q = np.maximum(np.abs([lx, lz]) - [hw, hh], 0.0)
        qy = max(y0 - p[1], p[1] - (y0 + 0.25 + depth), 0.0)
        best = min(best, float(np.sqrt(q[0] ** 2 + q[1] ** 2 + qy ** 2)))
    return best


SOCKET_REACH = 0.08          # the re-cut may change the plate mosaic this far from a socket (4.8 cm)


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
    bpy.ops.wm.open_mainfile(filepath=V12)
    before = vertices(BODY_OBJECTS + KEPT_HEAD)
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "bar": obj["Crown_Bracket"].material_slots[0].material,
         "teeth": obj["Teeth_Upper"].material_slots[0].material, "eye": obj["Eyes"].material_slots[0].material,
         "throat": obj["Throat"].material_slots[0].material,
         "tissue": obj["Gums_Upper"].material_slots[0].material}          # v12's (= v10's) materials, unchanged
    col = bpy.data.collections["Head"]
    sk = obj["Cranium"]
    old_sk = np.empty(len(sk.data.vertices) * 3, np.float32)
    sk.data.vertices.foreach_get("co", old_sk)
    n_changed, box = H.restore_sockets(M, col, sk)
    new_sk = np.empty(len(sk.data.vertices) * 3, np.float32)
    sk.data.vertices.foreach_get("co", new_sk)
    from scipy.spatial import cKDTree
    old_sk, new_sk = old_sk.reshape(-1, 3), new_sk.reshape(-1, 3)
    d_new, _ = cKDTree(old_sk).query(new_sk)
    d_old, _ = cKDTree(new_sk).query(old_sk)
    moved = np.r_[new_sk[d_new > 1e-7], old_sk[d_old > 1e-7]]
    reach = max(socket_distance(p) for p in moved) if len(moved) else 0.0
    outside = sum(socket_distance(p) > SOCKET_REACH for p in moved)
    print("CRANIUM: %d -> %d vertices; %d new and %d removed, all within %.3f u (%.1f cm) of a socket: %s; "
          "every other vertex v12's, attributes included"
          % (len(old_sk), len(new_sk), int((d_new > 1e-7).sum()), int((d_old > 1e-7).sum()), reach,
             reach * HEAD_SCALE * 100, outside == 0))
    if outside:
        raise SystemExit("the cranium changed away from the sockets - not saving")
    for n in H.MOUTH_OBJECTS:
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    H.build_mouth(M, col, sk, HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE, fast=FAST)
    print("mouth %.1fs" % (time.time() - t0))
    B7.soft_shade(("Gums_Lower", "Mouth_Cheek_Flesh", "Mouth_Floor", "Mouth_Inner_Walls", "Jaw_Strands"), sharp=60)
    B7.soft_shade(("Teeth_Lower",), sharp=50)
    bpy.context.view_layer.update()
    after = vertices(BODY_OBJECTS + KEPT_HEAD)
    same = {n: np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1]) for n in before}
    print("BODY UNCHANGED (vertex-identical to v12/v11/v10/v9/v8/v7):", all(same[n] for n in BODY_OBJECTS))
    print("KEPT HEAD PARTS UNCHANGED (vertex-identical to v12: %s): %s" % (", ".join(KEPT_HEAD),
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
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v13.blend"))
