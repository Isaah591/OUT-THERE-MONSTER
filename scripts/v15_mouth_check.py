"""
V15 ("Experimental 11") mouth and eye-socket check (v14_mouth_check.py's, on head_v15, with the gap
between the rows measured two ways).

1. See-through (needs the .blend): rays through every pixel of the mouth region from the sheet's front
   and three-quarter cameras; a pixel counts when the ray reaches the body (not a head part) while head
   parts lie 6 px to either side of it - a hole through the mouth into the neck, chest or arm behind.
2. What each camera sees between the jaws (needs the .blend; no lighting involved): of the rays through
   the box between the jaws (GAP_BOX), how many end on a tooth and how many on the mouth's interior -
   its floor, inner walls, throat, palate, the inside of the cranium - the dark the teeth should hide.
3. Eye sockets (needs renders): the dark socket boxes and the red pupils in the front and
   three-quarter renders against the sheet's (panel px).
4. The dark between the jaws (needs renders): in the same box, pixels darker than 0.15 (the dark class
   of measure_mouth_v10.py) and tooth-coloured pixels, render against the sheet.

    python v15_mouth_check.py <file.blend> [front=<sheet_front.png> 34=<fit34.png>]     (with `bpy`)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from PIL import Image  # noqa: E402
from scipy import ndimage  # noqa: E402

import head_v15 as H  # noqa: E402
import measure_mouth_v10 as MM  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join(ROOT, "references", "r08_open_jaw_sheet_v2.webp")
PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550)}
MOUTH_BOX = {"34": (160, 95, 245, 225), "front": (228, 65, 305, 205)}
GAP_BOX = {"34": (150, 95, 245, 205), "front": (228, 62, 305, 185)}         # between the jaws, panel px
SOCKET_WIN = {"front": [(220, 28, 256, 66), (266, 26, 304, 66)], "34": [(150, 62, 182, 100), (192, 56, 232, 96)]}
INTERIOR = ("Mouth_Floor", "Mouth_Inner_Walls", "Throat", "Palate", "Cranium", "Mouth_Cheek_Flesh", "Jaw_Strands",
            "Mouth_Corner_Rims", "Torn_Flesh")


def cameras():
    az, el, dist, lens, sx, sy = H.CAM34
    loc = H.TGT34 + dist * Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    fwd = (H.TGT34 - loc).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd)
    k = lens / 36.0 * H.W34

    def ray34(u, v):
        x = (u - H.W34 / 2) / k - sx * 36.0 / lens
        y = (H.H34 / 2 - v) / k - sy * 36.0 / lens
        return loc, (fwd + right * x + up * y).normalized()

    def rayf(u, v):
        o = Vector(((u - H.FRONT_CAM[0]) / H.FRONT_CAM[2], -12.0, (H.FRONT_CAM[1] - v) / H.FRONT_CAM[2]))
        return o, Vector((0, 1, 0))
    return {"34": ray34, "front": rayf}


def see_through(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    head = set(o.name for o in bpy.data.collections["Head"].all_objects)
    for view, ray in cameras().items():
        x0, y0, x1, y1 = MOUTH_BOX[view]
        bad = []
        for v in np.arange(y0, y1, 1.0):
            for u in np.arange(x0, x1, 1.0):
                hit, _, _, _, ob, _ = scene.ray_cast(dg, *ray(u, v))
                if not hit or ob.name in head:
                    continue
                left, right = scene.ray_cast(dg, *ray(u - 6, v)), scene.ray_cast(dg, *ray(u + 6, v))
                if left[0] and right[0] and left[4].name in head and right[4].name in head:
                    bad.append((int(u), int(v), ob.name))
        print("%-5s see-through px inside the mouth: %d %s" % (view, len(bad), bad[:: max(1, len(bad) // 6)]))


def between_jaws():
    """Rays through the box between the jaws (the file opened by see_through): teeth vs the interior."""
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    for view, ray in cameras().items():
        x0, y0, x1, y1 = GAP_BOX[view]
        teeth = interior = 0
        for v in np.arange(y0, y1, 1.0):
            for u in np.arange(x0, x1, 1.0):
                hit, _, _, _, ob, _ = scene.ray_cast(dg, *ray(u + 0.5, v + 0.5))
                if hit and ob.name.startswith("Teeth"):
                    teeth += 1
                elif hit and ob.name in INTERIOR:
                    interior += 1
        print("%-5s between the jaws (box %s): teeth %d px, mouth interior seen %d px" % (view, GAP_BOX[view], teeth,
                                                                                        interior))


def sockets(im, view):
    a = np.asarray(im, float) / 255.0
    lum = a @ [0.3, 0.59, 0.11]
    red = (a[..., 0] > 0.35) & (a[..., 0] > 2.0 * a[..., 1])
    out = []
    for x0, y0, x1, y1 in SOCKET_WIN[view]:
        m = (lum[y0:y1, x0:x1] < 0.10) | red[y0:y1, x0:x1]
        lab, n = ndimage.label(m)
        if n == 0:
            out.append("none")
            continue
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        hold = [j for j in np.unique(lab[red[y0:y1, x0:x1] & (lab > 0)]) if sizes[j - 1] >= 40]
        # the largest dark blob holding a pupil (the socket), else the largest dark blob
        k = int(max(hold, key=lambda j: sizes[j - 1])) if hold else int(np.argmax(sizes)) + 1
        ys, xs = np.nonzero(lab == k)
        rr = np.nonzero(red[y0:y1, x0:x1] & (lab == k))
        pupil = "(%.0f, %.0f)" % (x0 + rr[1].mean(), y0 + rr[0].mean()) if len(rr[0]) else "hidden"
        out.append("box (%d-%d, %d-%d) %dx%d px, pupil %s" % (x0 + xs.min(), x0 + xs.max(), y0 + ys.min(), y0 + ys.max(),
                                                               xs.max() - xs.min() + 1, ys.max() - ys.min() + 1, pupil))
    return out


def dark_between(view, path):
    x0, y0, x1, y1 = GAP_BOX[view]
    for name, c in (("sheet", MM.sheet_classes(view)[0]), ("model", MM.render_classes(path, view)[0])):
        b = c[y0:y1, x0:x1]
        print("%-5s %-5s between the jaws: dark %d px, teeth %d px (box %d px)" % (view, name, int((b == 3).sum()),
                                                                                  int((b == 2).sum()), b.size))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    see_through(argv[0])
    between_jaws()
    sheet = Image.open(SHEET).convert("RGB")
    for arg in argv[1:]:
        view, path = arg.split("=")
        s = sheet.crop(PANELS[view])
        r = Image.open(path).convert("RGB").resize(s.size, Image.LANCZOS)
        for name, im in (("sheet", s), ("model", r)):
            print("%-5s %-5s sockets (image left, image right): %s" % (view, name, " | ".join(sockets(im, view))))
        dark_between(view, path)
