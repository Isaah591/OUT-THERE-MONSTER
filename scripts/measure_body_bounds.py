"""
Check that two builds share the same body forms, proportions and pose: per-part world-space
extents (robust 0.5 / 99.5 percentiles) and centroids of the torso, arms and legs, and the
differences between the two files.

    python measure_body_bounds.py <a.blend> <b.blend>        (with the `bpy` module)

Surface detail (cracks, pits, erosion, shallow tears) moves vertices by millimetres; a change in
form, proportion or pose moves the extents and centroids by centimetres.
"""
import sys

import bpy
import numpy as np

PARTS = ("Torso", "Arm_R_Long", "Arm_L_Short", "Leg_L", "Leg_R")


def measure(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    out = {}
    for n in PARTS:
        ob = bpy.data.objects[n]
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        M = np.array(ob.matrix_world)
        w = co.reshape(-1, 3).astype(float) @ M[:3, :3].T + M[:3, 3]
        out[n] = (np.percentile(w, 0.5, axis=0), np.percentile(w, 99.5, axis=0), w.mean(0))
    return out


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
A, B = measure(argv[0]), measure(argv[1])
worst = 0.0
print("%-12s %-34s %-34s %s" % ("part", "size A (m)", "size B (m)", "max |diff| of extents / centroid (mm)"))
for n in PARTS:
    lo_a, hi_a, c_a = A[n]
    lo_b, hi_b, c_b = B[n]
    d_ext = max(np.abs(lo_a - lo_b).max(), np.abs(hi_a - hi_b).max()) * 1000
    d_c = np.abs(c_a - c_b).max() * 1000
    worst = max(worst, d_ext, d_c)
    print("%-12s %-34s %-34s %.1f / %.1f" % (n, np.round(hi_a - lo_a, 3), np.round(hi_b - lo_b, 3), d_ext, d_c))
print("LARGEST DIFFERENCE %.1f mm" % worst)
