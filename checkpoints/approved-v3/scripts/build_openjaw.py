"""
Build of the OUT THERE monster after the ASTRA R08 - MORE OPEN JAW sheet
(references/r08_open_jaw_sheet.webp): lean hunched predator, slim long arm planted ahead,
compact skull with the lower jaw broken far open, crowded crooked fangs, rust flake mosaic.

    python build_openjaw.py                   (with the `bpy` module, Blender 5.0)
    blender -b -P build_openjaw.py

Writes model/out_there_monster_openjaw.blend.
"""
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import body_openjaw as B  # noqa: E402
import head_openjaw as H  # noqa: E402
import materials_r08 as MR  # noqa: E402
import monster_materials as MM  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEAD_SCALE = 0.60                           # compact skull, ~0.55 m wide (sheet: ~0.7 x torso width)
HEAD_POS = Vector((0.0, -1.16, 2.48))       # centre of the upper gum line, low and thrust ahead
HEAD_ROT = (math.radians(-4.0), math.radians(-2.0), math.radians(-2.0))
JAW_OPEN_DEG = 72.0                         # lower jaw broken open ~72 deg about its rear hinge (sheet profile)
JAW_BROKEN_ROLL_DEG = 5.0                   # sideways sag of the broken right hinge


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
    M["rust"], M["bar"] = MR.openjaw_rust(), MR.r08_bar()
    M["teeth"] = MR.openjaw_teeth()
    M["gum"] = MR.wet_flesh("M_OJ_Gum", (0.025, 0.002, 0.002), (0.075, 0.006, 0.006), (0.150, 0.016, 0.013), 0.22, 0.5)
    M["flesh"] = MR.wet_flesh("M_OJ_Flesh", (0.022, 0.002, 0.002), (0.065, 0.006, 0.006), (0.125, 0.014, 0.012), 0.32, 0.4)
    M["tongue"] = MR.wet_flesh("M_OJ_Tongue", (0.005, 0.001, 0.001), (0.014, 0.002, 0.002), (0.030, 0.005, 0.004), 0.75, 0.12)
    M["throat"] = MR.wet_flesh("M_OJ_Throat", (0.003, 0.001, 0.001), (0.010, 0.002, 0.002), (0.022, 0.004, 0.003), 0.7, 0.12)
    parts = B.build_body(C["Body"], M["rust"], M["bar"])
    C["Body"].objects.unlink(parts["Bars"])
    C["Hardware"].objects.link(parts["Bars"])
    print("body %.1fs" % (time.time() - t0))
    H.build_head(M, C["Head"], HEAD_POS, HEAD_ROT, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG, scale=HEAD_SCALE)
    print("head %.1fs" % (time.time() - t0))
    soft_shade(("Gums_Upper", "Gums_Lower", "Tongue", "Palate", "Throat", "Mouth_Corner_Tissue",
                "Mouth_Tendons"), sharp=60)
    soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=40)
    bpy.context.view_layer.update()
    clearance()
    stats(root)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_openjaw.blend"))
