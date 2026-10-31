"""
Print the monster's key proportions from a .blend (world space, metres).

    python measure_proportions.py <file.blend>
"""
import sys

import bpy
from mathutils import Vector


def world_verts(name):
    ob = bpy.data.objects[name]
    return [ob.matrix_world @ v.co for v in ob.data.vertices]


def extent(names, axis):
    vals = [v[axis] for n in names for v in world_verts(n)]
    return min(vals), max(vals)


def main():
    blend = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else sys.argv[1]
    bpy.ops.wm.open_mainfile(filepath=blend)
    z0, ztop = extent(["Cranium", "Torso", "Leg_R", "Leg_L"], 2)
    skull_lo, skull_hi = extent(["Cranium"], 2)
    jaw_lo, _ = extent(["Jaw", "Teeth_Lower"], 2)
    hx0, hx1 = extent(["Cranium"], 0)
    sx0, sx1 = extent(["Torso"], 0)
    t_lo, t_hi = extent(["Torso"], 2)
    _, hip = extent(["Leg_R", "Leg_L"], 2)
    gum = bpy.data.objects["Cranium"].matrix_world.translation.z
    la_x0, _ = extent(["Arm_R_Long"], 0)
    la_z0, la_z1 = extent(["Arm_R_Long"], 2)
    sa_z0, sa_z1 = extent(["Arm_L_Short"], 2)
    H = ztop - z0
    head_h = skull_hi - jaw_lo
    rows = [
        ("overall height (feet -> top of skull/hump)", H),
        ("skull top", skull_hi),
        ("upper gum line", gum),
        ("skull height (gum line -> top)", skull_hi - gum),
        ("jaw drop (gum line -> lowest jaw/teeth)", gum - jaw_lo),
        ("head + open jaw height", head_h),
        ("  ... as fraction of overall height", head_h / H),
        ("head width", hx1 - hx0),
        ("shoulder span (torso incl. deltoids)", sx1 - sx0),
        ("  ... head width / shoulder span", (hx1 - hx0) / (sx1 - sx0)),
        ("torso height (pelvis -> upper-back ridge)", t_hi - t_lo),
        ("hip height (leg length)", hip),
        ("  ... leg length / overall height", hip / H),
        ("chest visible below the jaw (jaw bottom -> pelvis)", max(0.0, jaw_lo - t_lo)),
        ("long arm: lowest point / furthest reach x", la_z0),
        ("long arm reach out from body centre (x)", -la_x0),
        ("short arm: lowest point (z)", sa_z0),
    ]
    for k, v in rows:
        print("  %-52s %6.2f" % (k, v))


if __name__ == "__main__":
    main()
