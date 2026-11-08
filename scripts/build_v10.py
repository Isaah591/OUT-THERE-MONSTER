"""
v10 variation of the OUT THERE monster: the approved head replicated from different base shapes
(head_v10.py: a planar, blocky, broken skull; a broad skeletal U jaw; thick faceted fangs; a
flesh-lined mouth), on the unchanged body. The v9 file is opened, its head objects are removed and
the new head is built on the same mount point. The body, arms, legs, bars, posture, body materials
and cameras are untouched (the body is checked vertex by vertex against v9 before saving). v9 is
kept unchanged (build_v9.py -> model/out_there_monster_v9.blend).

    python build_v10.py [out.blend]             (with the `bpy` module, Blender 5.0, and scikit-image)
    V10_FAST=1 python build_v10.py out.blend    (coarser voxels, for quick checks)

Writes model/out_there_monster_v10.blend.
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
import head_v10 as H  # noqa: E402
import materials_r08 as MR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V9 = os.path.join(ROOT, "model", "out_there_monster_v9.blend")
HEAD_OBJECTS = ("Cranium", "Jaw", "Eyes", "Mouth_Corner_Tissue", "Mouth_Inner_Walls", "Jaw_Strands", "Palate",
                "Tongue", "Throat", "Gums_Upper", "Gums_Lower", "Teeth_Upper", "Teeth_Lower", "Crown_Bracket")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7-v9: the neck, the hinge and the jaw's reach are kept
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 64.0                         # as v9: the long jaw on the exact side view's diagonal
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG
FAST = bool(os.environ.get("V10_FAST"))


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
    for a in ("Teeth_Lower", "Gums_Lower", "Jaw_Flesh_Floor", "Jaw"):
        ta = bvh(a)
        for b, tb in body.items():
            hits = ta.overlap(tb)
            if hits:
                ob = bpy.data.objects[a]
                ys = [ob.data.polygons[i].center.y for i, _ in hits]
                print("  overlap %s / %s: %d pairs, jaw-local y %.2f..%.2f (hinge 0, chin -1.30)"
                      % (a, b, len(hits), min(ys), max(ys)))
            total += len(hits)
    print("JAW/TEETH/GUMS/FLOOR-vs-BODY overlapping face pairs:", total)


def build(out):
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=V9)
    before = body_vertices()
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "bar": obj["Crown_Bracket"].material_slots[0].material,
         "teeth": obj["Teeth_Upper"].material_slots[0].material, "eye": obj["Eyes"].material_slots[0].material,
         "throat": obj["Throat"].material_slots[0].material}
    # head-only flesh: dark, wet maroon with little sheen (v9's tissue caught pale highlights)
    M["tissue"] = MR.wet_flesh("M_V10_Flesh", (0.014, 0.0012, 0.0010), (0.036, 0.0028, 0.0024), (0.064, 0.0048, 0.0040),
                               0.55, 0.06)
    col = bpy.data.collections["Head"]
    for n in HEAD_OBJECTS:
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    H.build_head(M, col, HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE, fast=FAST)
    print("head %.1fs" % (time.time() - t0))
    B7.soft_shade(("Gums_Upper", "Gums_Lower", "Palate", "Throat", "Mouth_Cheek_Flesh", "Jaw_Flesh_Floor",
                   "Torn_Flesh", "Jaw_Strands"), sharp=60)
    B7.soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=24)      # faceted fangs
    bpy.context.view_layer.update()
    after = body_vertices()
    same = all(np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1])
               for n in BODY_OBJECTS)
    print("BODY UNCHANGED (vertex-identical to v9/v8/v7):", same)
    if not same:
        raise SystemExit("body changed - not saving")
    clearance()
    B7.stats(bpy.data.collections["MONSTER"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v10.blend"))
