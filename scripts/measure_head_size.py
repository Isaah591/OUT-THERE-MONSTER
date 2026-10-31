"""
Skull size and placement (world space) of a built model: robust extents of the Cranium mesh.

    python measure_head_size.py <file.blend>         (with the `bpy` module)
"""
import sys

import bpy
import numpy as np

bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
ob = bpy.data.objects["Cranium"]
me = ob.data
co = np.empty(len(me.vertices) * 3, np.float32)
me.vertices.foreach_get("co", co)
M = np.array(ob.matrix_world)
w = co.reshape(-1, 3).astype(float) @ M[:3, :3].T + M[:3, 3]
lo, hi = np.percentile(w, 0.5, axis=0), np.percentile(w, 99.5, axis=0)
gum = ob.matrix_world.translation
print("H skull width %.3f m, depth %.3f m, height above the gum line %.3f m; front y %.3f, back y %.3f, "
      "centre x %.3f, gum line at (%.3f, %.3f, %.3f)"
      % (hi[0] - lo[0], hi[1] - lo[1], hi[2] - gum.z, lo[1], hi[1], (lo[0] + hi[0]) / 2, gum.x, gum.y, gum.z))
