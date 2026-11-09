"""
v12 variation of the OUT THERE monster: a jaw and tooth correction on v11 (head_v12.py). Only the
mouth is rebuilt - the lower jaw, the teeth, the gums and the mouth's tissue:
- the lower jaw's side profile is the exact side panel's (its opening, the tooth row along its front
  edge, its rear edge curving forward into a broken chin);
- every tooth keeps the width, height and lean the sheet shows it with; the upper roots stand at their
  own heights on the broken gum, and the lower teeth point the way the side panel's fan does;
- the tissue is thinner and broken, so the jaw's bone shows between it.
The v11 file is opened, its mouth objects are removed and the new ones are built on v11's cranium. The
body, the rest of the head (cranium, eyes, crown bracket, torn skull sides, palate, throat), the
materials and the cameras are untouched: all of them are checked vertex by vertex against v11 before
saving. v11 is kept unchanged (build_v11.py -> model/out_there_monster_v11.blend).

    python build_v12.py [out.blend]             (with the `bpy` module, Blender 5.0, and scikit-image)
    V12_FAST=1 python build_v12.py out.blend    (coarser voxels, for quick checks)

Writes model/out_there_monster_v12.blend.
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
import head_v12 as H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V11 = os.path.join(ROOT, "model", "out_there_monster_v11.blend")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
KEPT_HEAD = ("Cranium", "Eyes", "Crown_Bracket", "Torn_Flesh", "Palate", "Throat")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7-v11
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 76.0                         # starting value; solved from the side panel in head_v12
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG
FAST = bool(os.environ.get("V12_FAST"))


def vertices(names):
    out = {}
    for n in names:
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
    bpy.ops.wm.open_mainfile(filepath=V11)
    before = vertices(BODY_OBJECTS + KEPT_HEAD)
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "bar": obj["Crown_Bracket"].material_slots[0].material,
         "teeth": obj["Teeth_Upper"].material_slots[0].material, "eye": obj["Eyes"].material_slots[0].material,
         "throat": obj["Throat"].material_slots[0].material,
         "tissue": obj["Gums_Upper"].material_slots[0].material}          # v11's (= v10's) materials, unchanged
    col = bpy.data.collections["Head"]
    for n in H.MOUTH_OBJECTS:
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    H.build_mouth(M, col, obj["Cranium"], HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE,
                  fast=FAST)
    print("mouth %.1fs" % (time.time() - t0))
    B7.soft_shade(("Gums_Upper", "Gums_Lower", "Mouth_Cheek_Flesh", "Mouth_Floor", "Mouth_Inner_Walls", "Jaw_Strands"),
                  sharp=60)
    B7.soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=50)
    bpy.context.view_layer.update()
    after = vertices(BODY_OBJECTS + KEPT_HEAD)
    same = {n: np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1]) for n in before}
    print("BODY UNCHANGED (vertex-identical to v11/v10/v9/v8/v7):", all(same[n] for n in BODY_OBJECTS))
    print("REST OF THE HEAD UNCHANGED (vertex-identical to v11: %s): %s" % (", ".join(KEPT_HEAD),
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
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v12.blend"))
