"""
V12 check of the lower jaw's side silhouette against the approved sheet's exact side panel.

The Jaw mesh of a build is projected into the side panel (orthographic, panel px). Its rear edge
(the rightmost jaw point in each row), its bottom (the lowest point in each column, the chin) and
the lower teeth's root line are compared with the sheet's traced edges (head_v12.SHEET["side_jaw"]).
Also printed: the jaw's angle, hinge to lowest point.

    python v12_jaw_check.py <file.blend> [<file.blend> ...]      (with `bpy`)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import head_v12 as H  # noqa: E402

SIDE = H.SIDE_CAM


def projected(name):
    ob = bpy.data.objects[name]
    M = np.array(ob.matrix_world)
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    w = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    return SIDE[0] + SIDE[2] * w[:, 1], SIDE[1] - SIDE[2] * w[:, 2]


def rear_edge(u, v, vv, band=1.5):
    m = (v >= vv - band) & (v < vv + band)
    return float(u[m].max()) if np.any(m) else np.nan


def check(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    sheet = H.SHEET["side_jaw"]
    u, v = projected("Jaw")
    d_rear = [rear_edge(u, v, sv) - su for su, sv in sheet["rear"]]
    low = max(v)
    lu = float(u[np.argmax(v)])
    # the lower teeth's root line: the base of each lower tooth (its lowest-t vertices, see tusk)
    ob = bpy.data.objects["Teeth_Lower"]
    lay = ob.data.color_attributes.get("tooth")
    t = np.array([c.color[0] for c in lay.data])
    tu, tv = projected("Teeth_Lower")
    roots = np.c_[tu, tv][t < 0.02]
    # distance of each sheet root to the nearest model tooth base, along the jaw
    d_roots = [float(np.min(np.hypot(roots[:, 0] - su, roots[:, 1] - sv))) for su, sv in sheet["roots"]]
    hinge = (186.6, 119.9)
    ang = np.degrees(np.arctan2(low - hinge[1], hinge[0] - lu))
    print("== %s" % os.path.basename(path))
    print("  rear edge vs the sheet's, per traced row (px, + = behind):", [round(x, 1) for x in d_rear])
    print("  rear edge: mean |d| %.1f px" % np.nanmean(np.abs(d_rear)))
    print("  chin: lowest point (%.0f, %.0f) (sheet: (163, 231)); jaw angle hinge -> lowest point %.0f deg (sheet: 78)"
          % (lu, low, ang))
    print("  lower root line: mean distance of the sheet's roots to the nearest tooth base %.1f px" % np.mean(d_roots))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    for p in argv:
        check(p)
