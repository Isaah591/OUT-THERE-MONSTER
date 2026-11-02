"""
Side-profile jaw metrics of a built model, from the actual geometry (world y/z = the side view).

    python measure_jaw_profile.py <file.blend>        (with the `bpy` module)

Compare with the sheet's exact side view (landmarks read on a zoomed grid, see
docs/OPENJAW_NOTES.md): lower/upper jaw length ~1.1, opening ~70-72 deg, chin drop ~2.0 x skull
height, front of the lower jaw ~0.6-0.7 upper-jaw lengths behind the snout.
"""
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
sk, jaw = bpy.data.objects["Cranium"], bpy.data.objects["Jaw"]


def wco(ob):
    me = ob.data
    a = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", a)
    a = a.reshape(-1, 3).astype(float)
    M = np.array(ob.matrix_world)
    return a @ M[:3, :3].T + M[:3, 3]


c, j = wco(sk), wco(jaw)
hinge = np.array(jaw.matrix_world.translation)
gum = np.array(sk.matrix_world @ Vector((0, -0.468, 0)))          # front of the upper gum line
crown = np.percentile(c[:, 2], 99.5)
skull_h = crown - gum[2]
snout = c[:, 1].min()
up_len = hinge[1] - snout                                          # hinge -> snout front (horizontal)
tip_i = np.argmin(j[:, 2])
low = j[tip_i]
jd = np.array(jaw.matrix_world.to_3x3() @ Vector((0, -1, 0)))     # jaw axis (hinge -> chin)
sd = np.array(sk.matrix_world.to_3x3() @ Vector((0, -1, 0)))      # skull axis (hinge -> snout)
ang = math.degrees(math.acos(np.clip(np.dot(jd[1:], sd[1:]) / np.linalg.norm(jd[1:]) / np.linalg.norm(sd[1:]), -1, 1)))
front = j[:, 1].min()
low_len = np.linalg.norm((low - hinge)[1:])
print("J skull height %.3f m | upper jaw (hinge->snout) %.3f m | lower jaw (hinge->lowest chin) %.3f m -> ratio %.2f"
      % (skull_h, up_len, low_len, low_len / up_len))
print("J opening angle between the jaws (side view) %.0f deg | chin drop below the upper gum line %.3f m = %.2f x skull height"
      % (ang, gum[2] - low[2], (gum[2] - low[2]) / skull_h))
print("J front of the lower jaw sits %.3f m behind the snout front (%.2f x upper jaw length)"
      % (front - snout, (front - snout) / up_len))
