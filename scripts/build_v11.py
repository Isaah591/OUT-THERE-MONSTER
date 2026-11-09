"""
v11 variation of the OUT THERE monster: a head-only anatomy correction (head_v11.py). The mouth,
lower jaw and teeth are solved from the approved sheet's own panels - the jaw's pose from the exact
side panel's chin, its asymmetric U from the front panel's mouth outline, every tooth from the
roots and tips read off the front and side panels - instead of being re-styled from an earlier
version's head. The v10 file is opened, its head objects are removed and the new head is built on
the same mount. The body, arms, legs, bars, posture, body materials and cameras are untouched (the
body is checked vertex by vertex against v10 before saving), and the head keeps v10's materials.
v10 is kept unchanged (build_v10.py -> model/out_there_monster_v10.blend).

    python build_v11.py [out.blend]             (with the `bpy` module, Blender 5.0, and scikit-image)
    V11_FAST=1 python build_v11.py out.blend    (coarser voxels, for quick checks)

Writes model/out_there_monster_v11.blend.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import build_v7 as B7  # noqa: E402  (clearance check, stats, shading helpers)
import head_v11 as H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V10 = os.path.join(ROOT, "model", "out_there_monster_v10.blend")
HEAD_OBJECTS = ("Cranium", "Jaw", "Eyes", "Mouth_Cheek_Flesh", "Jaw_Flesh_Floor", "Torn_Flesh", "Jaw_Strands", "Palate",
                "Throat", "Gums_Upper", "Gums_Lower", "Teeth_Upper", "Teeth_Lower", "Crown_Bracket")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7-v10
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 70.0                         # starting value; solved from the side panel's chin in head_v11
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG
FAST = bool(os.environ.get("V11_FAST"))


def body_vertices():
    out = {}
    for n in BODY_OBJECTS:
        ob = bpy.data.objects[n]
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        out[n] = (co, np.array(ob.matrix_world))
    return out


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
    bpy.ops.wm.open_mainfile(filepath=V10)
    before = body_vertices()
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "bar": obj["Crown_Bracket"].material_slots[0].material,
         "teeth": obj["Teeth_Upper"].material_slots[0].material, "eye": obj["Eyes"].material_slots[0].material,
         "throat": obj["Throat"].material_slots[0].material,
         "tissue": obj["Gums_Upper"].material_slots[0].material}          # v10's materials, unchanged
    col = bpy.data.collections["Head"]
    for n in HEAD_OBJECTS:
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    H.build_head(M, col, HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE, fast=FAST)
    print("head %.1fs" % (time.time() - t0))
    B7.soft_shade(("Gums_Upper", "Gums_Lower", "Palate", "Throat", "Mouth_Cheek_Flesh", "Mouth_Floor", "Mouth_Inner_Walls",
                   "Torn_Flesh", "Jaw_Strands"), sharp=60)
    B7.soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=50)
    bpy.context.view_layer.update()
    after = body_vertices()
    same = all(np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1])
               for n in BODY_OBJECTS)
    print("BODY UNCHANGED (vertex-identical to v10/v9/v8/v7):", same)
    if not same:
        raise SystemExit("body changed - not saving")
    clearance()
    B7.stats(bpy.data.collections["MONSTER"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v11.blend"))
