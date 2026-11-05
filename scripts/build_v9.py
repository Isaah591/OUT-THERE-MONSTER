"""
v9 variation of the OUT THERE monster: a head reconstruction on the unchanged body. The v8 file is
opened, its head objects are removed and a new head is built from head_v9.py on the same mount
point (a damaged, irregular skull around an enormous skeletal mouth, with an elongated lower jaw
on the exact side view's diagonal and restrained red tissue). The body, arms, legs, bars, posture,
body materials and cameras are untouched (the body is checked vertex by vertex against v8 before
saving). v8 is kept unchanged (build_v8.py -> model/out_there_monster_v8.blend).

    python build_v9.py [out.blend]             (with the `bpy` module, Blender 5.0)
    V9_FAST=1 python build_v9.py out.blend     (head base forms only, for quick silhouette checks)

Writes model/out_there_monster_v9.blend.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_v7 as B7  # noqa: E402  (clearance check, stats, shading helpers)
import head_v9 as H  # noqa: E402
import materials_r08 as MR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V8 = os.path.join(ROOT, "model", "out_there_monster_v8.blend")
HEAD_OBJECTS = ("Cranium", "Jaw", "Eyes", "Mouth_Corner_Tissue", "Palate", "Tongue", "Throat", "Gums_Upper",
                "Gums_Lower", "Teeth_Upper", "Teeth_Lower", "Crown_Bracket")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7: the neck, the hinge and the jaw's reach are kept
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 64.0                         # the elongated jaw on the exact side view's diagonal (v8: 53)
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG
FAST = bool(os.environ.get("V9_FAST"))


def body_vertices():
    out = {}
    for n in BODY_OBJECTS:
        ob = bpy.data.objects[n]
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        out[n] = (co, np.array(ob.matrix_world))
    return out


def build(out):
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=V8)
    before = body_vertices()
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "bar": obj["Crown_Bracket"].material_slots[0].material,
         "teeth": obj["Teeth_Upper"].material_slots[0].material, "eye": obj["Eyes"].material_slots[0].material,
         "gum": obj["Gums_Upper"].material_slots[0].material, "flesh": obj["Mouth_Corner_Tissue"].material_slots[0].material,
         "tongue": obj["Tongue"].material_slots[0].material, "throat": obj["Throat"].material_slots[0].material}
    M["tissue"] = MR.wet_flesh("M_V9_Tissue", (0.020, 0.0020, 0.0016), (0.058, 0.0055, 0.0045), (0.115, 0.0105, 0.0085),
                               0.50, 0.20)             # restrained dark maroon, not pink (head only)
    col = bpy.data.collections["Head"]
    for n in HEAD_OBJECTS:
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    H.build_head(M, col, HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE, fast=FAST)
    print("head %.1fs" % (time.time() - t0))
    B7.soft_shade(("Gums_Upper", "Gums_Lower", "Tongue", "Palate", "Throat", "Mouth_Corner_Tissue", "Jaw_Strands",
                   "Mouth_Inner_Walls"),
                  sharp=60)
    B7.soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=70)
    bpy.context.view_layer.update()
    after = body_vertices()
    same = all(np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1])
               for n in BODY_OBJECTS)
    print("BODY UNCHANGED (vertex-identical to v8/v7):", same)
    if not same:
        raise SystemExit("body changed - not saving")
    B7.clearance()
    B7.stats(bpy.data.collections["MONSTER"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v9.blend"))
