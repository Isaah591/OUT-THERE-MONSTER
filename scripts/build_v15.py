"""
v15 ("Experimental 11") variation of the OUT THERE monster: the posterior teeth lengthened and the brows
made angrier, on v14 (head_v15.py). Opened from v14's file:
- both rows of teeth are planned as v14 plans them, then the teeth further inside the mouth (behind
  the upper front row, along both sides of the upper jaw and at the front row's near end, and from the
  near side of the chin up the lower jaw's arm) are lengthened toward the prominent front teeth's
  length, each to its own length - roots where they were, none crossing another tooth or running into
  bone or tissue; the teeth that do not grow come out as v14's;
- the cranium is rebuilt with brows whose inner halves drop more steeply toward the nose and whose lips
  overhang each socket's inner top corner; every cranium vertex away from the brows and sockets stays
  v14's, attributes included.
Everything else - the jaw and its curvature, the opening, the gums and the mouth's tissue, the pupils,
the body, the materials and the cameras - is v14's, checked vertex by vertex before saving. v14 is kept
unchanged (build_v14.py -> model/out_there_monster_v14.blend).

    python build_v15.py [out.blend]             (with the `bpy` module, Blender 5.0, and scikit-image)

Writes model/out_there_monster_v15.blend.
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
import build_v14 as B14  # noqa: E402  (the cranium's edit zones)
import head_v15 as H  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V14 = os.path.join(ROOT, "model", "out_there_monster_v14.blend")
BODY_OBJECTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_R", "Leg_L", "Bars")
KEPT_HEAD = ("Jaw", "Gums_Upper", "Gums_Lower", "Mouth_Cheek_Flesh", "Mouth_Inner_Walls", "Mouth_Floor", "Jaw_Strands",
             "Mouth_Corner_Rims", "Eyes", "Crown_Bracket", "Torn_Flesh", "Palate", "Throat")
HEAD_SCALE = B7.HEAD_SCALE                  # same mount as v7-v14
HEAD_POS = Vector(B7.HEAD_POS)
HEAD_ROT = B7.HEAD_ROT
JAW_OPEN_DEG = 76.0
JAW_BROKEN_ROLL_DEG = B7.JAW_BROKEN_ROLL_DEG


def vertices(names):
    out = {}
    for n in names:
        ob = bpy.data.objects[n]
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        out[n] = (co, np.array(ob.matrix_world))
    return out


def bvh(name):
    """BVH of an object's mesh in its own local space (cranium space for the parts on the cranium, jaw
    space for those on the jaw)."""
    me = bpy.data.objects[name].data
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons])


def build(out):
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=V14)
    before = vertices(BODY_OBJECTS + KEPT_HEAD)
    obj = bpy.data.objects
    M = {"rust": obj["Cranium"].material_slots[0].material, "teeth": obj["Teeth_Upper"].material_slots[0].material}
    col = bpy.data.collections["Head"]
    sk, jaw = obj["Cranium"], obj["Jaw"]
    H.U = HEAD_SCALE
    F = H.Frame(HEAD_POS, HEAD_ROT, HEAD_SCALE, JAW_OPEN_DEG, JAW_BROKEN_ROLL_DEG)
    H.solve_upper_edge(F)
    old_sk, new_sk = H.rebuild_cranium(M, col, sk)
    from scipy.spatial import cKDTree
    d_new, _ = cKDTree(old_sk).query(new_sk)
    d_old, _ = cKDTree(new_sk).query(old_sk)
    moved = np.r_[new_sk[d_new > 1e-7], old_sk[d_old > 1e-7]]
    zones = [B14.zone(p) for p in moved]
    print("CRANIUM: %d -> %d vertices; %d new and %d removed - at the brows and sockets %d, elsewhere %d; every other "
          "vertex v14's, attributes included" % (len(old_sk), len(new_sk), int((d_new > 1e-7).sum()),
                                                 int((d_old > 1e-7).sum()), zones.count("eyes"), len(zones) - zones.count("eyes")))
    if len(zones) != zones.count("eyes"):
        raise SystemExit("the cranium changed away from the brows and sockets - not saving")
    H.solve_jaw(F)                                       # v14's jaw (kept): its path places the lower teeth
    for n in ("Teeth_Upper", "Teeth_Lower"):
        me = obj[n].data
        obj.remove(obj[n])
        if me.users == 0:
            bpy.data.meshes.remove(me)
    tissue_c = ["Mouth_Inner_Walls", "Mouth_Cheek_Flesh", "Jaw_Strands", "Mouth_Corner_Rims", "Torn_Flesh", "Palate",
                "Throat"]
    solids = {"up": {"c": [bvh(n) for n in ["Cranium"] + tissue_c], "j": [bvh(n) for n in ("Jaw", "Gums_Lower", "Mouth_Floor")]},
              "lo": {"c": [bvh(n) for n in ["Cranium", "Gums_Upper"] + tissue_c], "j": [bvh(n) for n in ("Jaw", "Mouth_Floor")]}}
    H.build_teeth_v15(M, col, sk, jaw, F, solids)
    B7.soft_shade(("Teeth_Upper", "Teeth_Lower"), sharp=50)
    bpy.context.view_layer.update()
    print("teeth %.1fs" % (time.time() - t0))
    after = vertices(BODY_OBJECTS + KEPT_HEAD)
    same = {n: np.array_equal(before[n][0], after[n][0]) and np.array_equal(before[n][1], after[n][1]) for n in before}
    print("BODY UNCHANGED (vertex-identical to v14/v13/.../v7):", all(same[n] for n in BODY_OBJECTS))
    print("KEPT HEAD PARTS UNCHANGED (vertex-identical to v14: the jaw, gums, mouth tissue, pupils, bracket, torn sides, "
          "palate, throat): %s" % all(same[n] for n in KEPT_HEAD))
    if not all(same.values()):
        raise SystemExit("body or kept head parts changed - not saving: %s" % [n for n, v in same.items() if not v])
    B7.stats(bpy.data.collections["MONSTER"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    print("SAVED", out, "%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    build(os.path.abspath(argv[0]) if argv else os.path.join(ROOT, "model", "out_there_monster_v15.blend"))
