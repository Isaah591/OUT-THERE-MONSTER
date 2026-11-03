"""
Front-view taper of the mouth opening from the geometry: the width of the lower gum line (the
inner edge of the lower jaw's U) and of the lower jaw's outline at fixed fractions of the way
down the opening, as fractions of the skull width.

    python measure_mouth_taper.py <file.blend>        (with the `bpy` module)

The front view looks along -Y, so world X is the width and world Z the height in the image.
Sheet (approved sheet, front panel, read on a 5x grid): the opening narrows from ~0.80 of the
skull width at the upper teeth to ~0.67 halfway down and ~0.48 at the bottom of the U.
"""
import sys

import bpy
import numpy as np

bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])


def wco(name):
    ob = bpy.data.objects[name]
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3).astype(float)
    M = np.array(ob.matrix_world)
    return co @ M[:3, :3].T + M[:3, 3]


sk, jw, gl, gu = wco("Cranium"), wco("Jaw"), wco("Gums_Lower"), wco("Gums_Upper")
skw = np.percentile(sk[:, 0], 99.5) - np.percentile(sk[:, 0], 0.5)
gum_z = bpy.data.objects["Cranium"].matrix_world.translation.z
drop = gum_z - jw[:, 2].min()
print("M skull width %.3f m; upper gum line width %.3f m = %.2f skull widths"
      % (skw, gu[:, 0].max() - gu[:, 0].min(), (gu[:, 0].max() - gu[:, 0].min()) / skw))
for f in (0.15, 0.35, 0.55, 0.75, 0.90):
    z = gum_z - f * drop
    band = jw[np.abs(jw[:, 2] - z) < 0.01]
    gb = gl[np.abs(gl[:, 2] - z) < 0.02]
    jwid = band[:, 0].max() - band[:, 0].min() if len(band) else float("nan")
    gwid = gb[:, 0].max() - gb[:, 0].min() if len(gb) > 3 else float("nan")
    print("M %2.0f%% down the opening: lower gum width %.2f, jaw outline %.2f skull widths" % (f * 100, gwid / skw, jwid / skw))
