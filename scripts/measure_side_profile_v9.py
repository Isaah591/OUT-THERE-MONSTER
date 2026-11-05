"""
Exact-side head profile against the approved sheet, with the side camera held fixed (the
blueprint's orthographic transform, as in measure_head_v8.py):

- the front of the head per row (forehead, brow and snout outline), sheet vs model;
- the top of the head per column;
- the lower jaw: its lowest point and the angle below horizontal of the line from the jaw's
  hinge to that point, for the model and for the sheet (the sheet's chin is the lowest point of
  its silhouette under the head, measured from the same hinge).

    python measure_side_profile_v9.py <file.blend> [<file.blend> ...]     (with `bpy`)

All positions are side-panel pixels (150.19 px per metre); d = model - sheet.
"""
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet_views as SV  # noqa: E402

REFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")
SIDE = (309.46, 466.26, 150.19)                  # u0, v0, px/m (u = u0 + s * y, v = v0 - s * z)
ROWS = range(40, 90, 5)                          # forehead and snout (v, panel px)
COLS = range(90, 230, 10)                        # top of the head (u, panel px)
CHIN_BOX = (110, 150, 190, 250)                  # u0, v0, u1, v1: the chin, clear of the chest


def side_uv(P):
    return SIDE[0] + SIDE[2] * P[:, 1], SIDE[1] - SIDE[2] * P[:, 2]


def world(name):
    ob = bpy.data.objects[name]
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    M = np.array(ob.matrix_world)
    return co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3], ob


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ref = SV.sheet_masks(REFS)["side"][0]
    H, W = ref.shape
    sub = ref[CHIN_BOX[1]:CHIN_BOX[3], CHIN_BOX[0]:CHIN_BOX[2]]
    vs, us = np.nonzero(sub)
    k = np.argmax(vs)
    sheet_chin = (us[k] + CHIN_BOX[0], vs[k] + CHIN_BOX[1])
    for blend in argv:
        P = SV.model_points(blend)                     # opens the file
        mm = SV.splat(*side_uv(P), (H, W))
        jaw, jo = world("Jaw")
        hu, hv = side_uv(np.array(jo.matrix_world)[:3, 3][None])
        ju, jv = side_uv(jaw)
        i = np.argmax(jv)
        ang = lambda u, v: math.degrees(math.atan2(v - hv[0], hu[0] - u))
        print("== %s" % os.path.basename(blend))
        df = []
        for v in ROWS:
            r, m = np.flatnonzero(ref[v, :240]), np.flatnonzero(mm[v, :240])
            if len(r) and len(m):
                df.append(m[0] - r[0])
        dt = []
        for u in COLS:
            r, m = np.flatnonzero(ref[:250, u]), np.flatnonzero(mm[:250, u])
            if len(r) and len(m):
                dt.append(m[0] - r[0])
        print("  front of the head, rows v %d-%d: d %s  mean |d| %.1f px" % (ROWS[0], ROWS[-1], df, np.mean(np.abs(df))))
        print("  top of the head, columns u %d-%d: d %s  mean |d| %.1f px" % (COLS[0], COLS[-1], dt, np.mean(np.abs(dt))))
        print("  jaw: hinge (%.0f, %.0f), lowest point (%.0f, %.0f) at %.0f deg below horizontal; sheet's chin "
              "(%d, %d) at %.0f deg" % (hu[0], hv[0], ju[i], jv[i], ang(ju[i], jv[i]), *sheet_chin, ang(*sheet_chin)))
        tu, tv = side_uv(world("Teeth_Lower")[0])
        print("  lower teeth: lowest point (%.0f, %.0f)" % (tu[np.argmax(tv)], tv.max()))
