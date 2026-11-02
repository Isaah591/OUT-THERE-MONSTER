"""
Front-view reach of every tooth into the mouth opening, from the geometry.

    python measure_teeth_reach.py <file.blend>        (with the `bpy` module)

The front view looks along -Y, so world Z is the vertical in the image. For each tooth (a mesh
island of Teeth_Upper / Teeth_Lower; the `tooth` colour attribute's R channel runs 0 at the root
to 1 at the tip; the part buried in the gum is excluded) the reach is the vertical distance from
the gum line to the tip, as a fraction of the mouth
opening (front of the upper gum line down to the front of the lower gum line).
Sheet reference (approved sheet, front view, read on a 6x grid): upper teeth reach median ~0.45,
longest ~0.64; lower teeth median ~0.44, longest ~0.60 (they overlap in the middle).
"""
import sys

import bpy  # noqa: I001  (bpy must be imported before bmesh)
import bmesh
import numpy as np

bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])


def islands(name):
    ob = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    lay = bm.verts.layers.float_color.get("tooth")
    M = ob.matrix_world
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, isl = [v], []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index)
            isl.append((list(M @ x.co), x[lay][0]))
            stack.extend(e.other_vert(x) for e in x.link_edges)
        p = np.array([q for q, _ in isl])
        t = np.array([tt for _, tt in isl])
        tip = p[np.argmax(t)]
        base = p[t <= t.min() + 1e-6]                  # the buried ring and the gum-line ring both carry t = 0
        axis = tip - base.mean(0)
        proj = (base - base.mean(0)) @ axis
        out.append((base[proj >= np.median(proj)].mean(0), tip))     # gum-line ring: the one nearer the tip
    return out


def gum_front_z(name):
    ob = bpy.data.objects[name]
    me = ob.data
    co = np.array([list(ob.matrix_world @ v.co) for v in me.vertices])
    front = co[co[:, 1] < np.percentile(co[:, 1], 8)]
    return np.median(front[:, 2])


zu, zl = gum_front_z("Gums_Upper"), gum_front_z("Gums_Lower")
H = zu - zl
for name, sign in (("Teeth_Upper", 1), ("Teeth_Lower", -1)):
    r = np.array([sign * (root[2] - tip[2]) / H for root, tip in islands(name)])
    print("R %s: %d teeth; reach into the opening median %.2f, 75th pct %.2f, longest %.2f"
          % (name, len(r), np.median(r), np.percentile(r, 75), r.max()))
print("R opening (front gum to front gum) %.3f m" % H)
