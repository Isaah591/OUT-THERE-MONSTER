"""
v7 variation of the OUT THERE monster: a reference accuracy pass in which the approved sheet is
the modelling blueprint - its front, exact side and three-quarter views together, measured in
metres (sheet_blueprint.py, sheet_views.py). The body is rebuilt from the views' widths, depths
and solved joints (body_v7.py), the head is rebuilt as the long, angular box skull with the
V-tapered hanging jaw the views show (head_v7.py). v6 is kept unchanged
(build_v6.py -> model/out_there_monster_v6.blend).

    python build_v7.py [out.blend]             (with the `bpy` module, Blender 5.0)
    V7_FAST=1 python build_v7.py out.blend     (base forms only, for quick silhouette checks)

Writes model/out_there_monster_v7.blend.
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import body_v7 as B  # noqa: E402
import head_v7 as H  # noqa: E402
import materials_r08 as MR  # noqa: E402
import monster_materials as MM  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD_SCALE = 0.60                           # head unit: the skull is 1.42 units (0.85 m) long, 0.93 (0.55 m) wide
HEAD_POS = Vector((-0.090, -1.070, 2.45))   # middle of the skull at the upper gum line: front view, the head sits
                                            # ~0.1 m to the monster's right; side view, snout front at y ~-1.5;
                                            # nudged toward the three-quarter view's position (a compromise)
HEAD_ROT = (math.radians(0.0), math.radians(-2.0), math.radians(4.0))   # snout turned a little to its left (3/4 view)
JAW_OPEN_DEG = 53.0                         # the chin hangs low in front of the chest (lowest point z ~1.63)
JAW_BROKEN_ROLL_DEG = -3.0                  # slight sideways sag toward the left hinge
FAST = bool(os.environ.get("V7_FAST"))


def collection(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def soft_shade(names, sharp=None):
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        ob.data.shade_smooth()
        if sharp:
            ob.data.set_sharp_from_angle(angle=math.radians(sharp))


def clearance():
    def bvh(n):
        ob = bpy.data.objects[n]
        verts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        return BVHTree.FromPolygons(verts, [p.vertices[:] for p in ob.data.polygons])
    total = 0
    body = {n: bvh(n) for n in ("Torso", "Arm_L_Short", "Arm_R_Long")}
    for a in ("Teeth_Lower", "Gums_Lower", "Tongue", "Jaw"):
        ta = bvh(a)
        for b, tb in body.items():
            hits = ta.overlap(tb)
            if hits:
                ob = bpy.data.objects[a]
                ys = [ob.data.polygons[i].center.y for i, _ in hits]
                print("  overlap %s / %s: %d pairs, local y %.2f..%.2f (hinge 0, chin -%.2f)"
                      % (a, b, len(hits), min(ys), max(ys), H.JAW_LEN))
            total += len(hits)
    print("JAW/TEETH/GUMS/TONGUE-vs-BODY overlapping face pairs:", total)


def stats(root):
    rows, tris = [], 0
    for ob in root.all_objects:
        if ob.type == 'MESH':
            t = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            rows.append((ob.name, t))
            tris += t
    for n, t in sorted(rows, key=lambda r: -r[1]):
        print("  %-22s %8d tris" % (n, t))
    print("TRIANGLES", tris)


def build(out):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    root = collection("MONSTER")
    C = {k: collection(k, root) for k in ("Head", "Body", "Hardware")}
    M = MM.build_all()
    M["rust"], M["bar"] = MR.v6_rust(), MR.r08_bar()
    M["teeth"] = MR.v6_teeth()
    M["eye"] = MR.v5_eye()
    M["gum"] = MR.wet_flesh("M_V5_Gum", (0.024, 0.003, 0.003), (0.060, 0.007, 0.006), (0.115, 0.014, 0.012), 0.50, 0.25)
    M["flesh"] = MR.wet_flesh("M_V5_Flesh", (0.010, 0.001, 0.001), (0.028, 0.003, 0.003), (0.055, 0.007, 0.006), 0.75, 0.10)
    M["tongue"] = MR.wet_flesh("M_OJ_Tongue", (0.005, 0.001, 0.001), (0.014, 0.002, 0.002), (0.030, 0.005, 0.004), 0.75, 0.12)
    M["throat"] = MR.wet_flesh("M_OJ_Throat", (0.003, 0.001, 0.001), (0.010, 0.002, 0.002), (0.022, 0.004, 0.003), 0.7, 0.12)
    parts = B.build_body(C["Body"], M["rust"], M["bar"])
    C["Body"].objects.unlink(parts["Bars"])
    C["Hardware"].objects.link(parts["Bars"])
    print("body %.1fs" % (time.time() - t0))
    H.build_head(M, C["Head"], HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE, fast=FAST)
    print("head %.1fs" % (time.time() - t0))
    soft_shade(("Gums_Upper", "Gums_Lower", "Tongue", "Palate", "Throat", "Mouth_Corner_Tissue",
                "Mouth_Tendons"), sharp=60)
    soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=70)                 # round, smooth fangs
    bpy.context.view_layer.update()
    clearance()
    stats(root)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v7.blend"))
