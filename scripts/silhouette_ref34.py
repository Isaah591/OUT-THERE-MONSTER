"""
Silhouette comparison against the approved sheet's three-quarter panel, from the fitted camera.

    python silhouette_ref34.py <references_dir> <out_prefix> <file.blend> [<file2.blend> ...]   (with `bpy`)

Reference silhouette: the panel (508 x 495) segmented into figure / backdrop. The backdrop is a
smooth neutral gradient, estimated per row from the panel's empty edge columns; figure pixels are
warm (rust, teeth, tissue), dark-warm (shadowed rust and wounds) or clearly off the backdrop and
saturated; then a small opening, a closing, hole filling and the largest component (the panel
title is excluded). The floor is excluded, so the gap between the legs stays open.

Model silhouette: every mesh vertex of the build (studio objects excluded) projected through the
same camera (ref34_camera.py) at twice the panel resolution, dilated, closed, holes filled, and
reduced to the panel's grid.

Prints the overlap (IoU) for the whole figure and for regions (head and jaw, torso, long arm,
short arm, legs) and row-by-row limb extents, and writes <out_prefix>_<name>_overlay.png:
reference only in red, model only in blue, reference outline yellow, model outline cyan.
"""
import os
import sys

import bpy
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref34_camera as RC  # noqa: E402

PANEL34 = (500, 55, 1008, 550)
REGIONS = {"head+jaw": (140, 25, 270, 225), "torso": (195, 50, 350, 280), "long arm": (0, 100, 200, 480),
           "short arm": (290, 90, 440, 340), "legs": (200, 250, 430, 480)}
ROWS = {"long arm": ((0, 172), (200, 250, 300, 350, 400, 440, 460)),
        "short arm": ((340, 445), (240, 280, 300)),
        "leg (screen left)": ((185, 305), (310, 340, 370, 400, 430, 455)),
        "leg (screen right)": ((305, 440), (340, 370, 400, 430, 455))}


def reference_mask(refs):
    a = np.asarray(Image.open(os.path.join(refs, "r08_open_jaw_sheet_v2.webp")).convert("RGB").crop(PANEL34)).astype(float)
    H, W, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(2)
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    bg = np.zeros_like(a)
    for y in range(H):
        bg[y] = np.median(np.concatenate([a[y, 440:500], a[y, 0:8]]), axis=0)
    diff = np.abs(a - bg).sum(2)
    fg = ((r - b > 9) & (r > 30)) | ((r - b > 5) & (r - g > 2) & (lum < 60)) | ((diff > 45) & (sat > 0.18))
    fg[:28, :240] = False
    fg = ndi.binary_opening(fg, structure=np.ones((2, 2)))
    fg = ndi.binary_closing(fg, structure=np.ones((5, 5)), iterations=2)
    fg = ndi.binary_fill_holes(fg)
    lab, n = ndi.label(fg)
    keep = lab == (1 + int(np.argmax(ndi.sum(fg, lab, range(1, n + 1)))))
    return ndi.binary_opening(keep, structure=np.ones((3, 3))), a


def model_mask(blend):
    bpy.ops.wm.open_mainfile(filepath=blend)
    W, H = RC.PANEL
    k = 2
    m = np.zeros((H * k, W * k), bool)
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.users_collection or ob.name == "Ground":
            continue
        if any(c.name == "STUDIO" for c in ob.users_collection):
            continue
        co = np.empty(len(ob.data.vertices) * 3, np.float32)
        ob.data.vertices.foreach_get("co", co)
        M = np.array(ob.matrix_world)
        uv, z = RC.project(co.reshape(-1, 3).astype(float) @ M[:3, :3].T + M[:3, 3])
        ui, vi = np.round(uv[:, 0] * k).astype(int), np.round(uv[:, 1] * k).astype(int)
        ok = (ui >= 0) & (ui < W * k) & (vi >= 0) & (vi < H * k) & (z > 0.1)
        m[vi[ok], ui[ok]] = True
    m = ndi.binary_dilation(m, iterations=1)
    m = ndi.binary_closing(m, structure=np.ones((3, 3)), iterations=2)
    m = ndi.binary_fill_holes(m)
    return m.reshape(H, k, W, k).mean((1, 3)) > 0.5


def iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def runs(row, x0, x1):
    out, start = [], None
    for i, v in enumerate(row[x0:x1]):
        if v and start is None:
            start = i
        if start is not None and (not v or i == x1 - x0 - 1):
            end = i if not v else i + 1
            if end - start >= 4:
                out.append((x0 + start, x0 + end - 1))
            start = None
    return out


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
refs, prefix, blends = argv[0], argv[1], argv[2:]
ref, panel = reference_mask(refs)
for blend in blends:
    name = os.path.splitext(os.path.basename(blend))[0].replace("out_there_monster_", "")   # e.g. "v6"
    mm = model_mask(blend)
    print("%s: IoU whole figure %.3f" % (name, iou(mm, ref)))
    for rk, (x0, y0, x1, y1) in REGIONS.items():
        print("   %-10s IoU %.3f  (model %5d px, reference %5d px)"
              % (rk, iou(mm[y0:y1, x0:x1], ref[y0:y1, x0:x1]), mm[y0:y1, x0:x1].sum(), ref[y0:y1, x0:x1].sum()))
    for rk, ((x0, x1), ys) in ROWS.items():
        print("   %s, extents per row (reference | model):" % rk)
        for y in ys:
            print("      y %3d  %-28s | %s" % (y, runs(ref[y], x0, x1), runs(mm[y], x0, x1)))
    ov = panel * 0.45
    ov[ref & ~mm] = ov[ref & ~mm] * 0.4 + np.array([255, 60, 40]) * 0.6
    ov[mm & ~ref] = ov[mm & ~ref] * 0.4 + np.array([40, 120, 255]) * 0.6
    ov[mm & ref] = ov[mm & ref] * 0.7 + np.array([200, 200, 200]) * 0.3
    ov[ref & ~ndi.binary_erosion(ref)] = (255, 255, 0)
    ov[mm & ~ndi.binary_erosion(mm)] = (0, 255, 255)
    Image.fromarray(ov.astype(np.uint8)).resize((ref.shape[1] * 2, ref.shape[0] * 2), Image.NEAREST).save(
        "%s_%s_overlay.png" % (prefix, name))
