"""
Landmarks in the approved sheet's three-quarter panel vs a model render from the fitted `ref34`
camera (render_views.py), on the same pixel grid (panel pixels, 508 x 495).

    python measure_ref34_landmarks.py <references_dir> <ref34.png> [<other_ref34.png> ...]

Measured automatically (no hand tuning per image):
  pupils       red glowing point inside a dark void, searched in a window around each socket
  skull top    top of the cranium over the forehead columns 178-200 (clear of the crown knobs)
  teeth        ivory pixels (hue 19-40 on PIL's 0-255 scale, bright, saturated) in the mouth
               region: bounding box, lowest tooth pixel, and the area in panel pixels
The mouth outline and the lower jaw's U are read on the gridded sheet (_v5_ref34_grid.png),
because the painting's jaw blends into the body.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

REFS, RENDERS = sys.argv[1], sys.argv[2:]
PANEL34 = (500, 55, 1008, 550)
HEAD = (130, 30, 280, 120)          # pupils and skull top live here (panel px)
MOUTH = (140, 85, 270, 225)         # teeth region (panel px)


def load_panel():
    return np.asarray(Image.open(os.path.join(REFS, "r08_open_jaw_sheet_v2.webp")).convert("RGB").crop(PANEL34))


def load_render(p):
    return np.asarray(Image.open(p).convert("RGB").resize((508, 495), Image.LANCZOS))


SOCKET_WINDOWS = [(150, 60, 188, 100), (192, 52, 236, 96)]     # panel px around each eye socket


def pupils(x):
    """The red glowing point in each eye socket: within a window around each socket, strongly red
    pixels whose 9x9 neighbourhood is dark (the void), red-weighted centroid of the largest cluster."""
    out = []
    for x0, y0, x1, y1 in SOCKET_WINDOWS:
        a = x[y0:y1, x0:x1].astype(float)
        dark = ndi.uniform_filter(a.mean(2), 9) < 70
        red = (a[..., 0] > 90) & (a[..., 0] > 2.0 * a[..., 1]) & (a[..., 0] > 2.0 * a[..., 2]) & dark
        lab, n = ndi.label(ndi.binary_dilation(red, iterations=1))
        best = None
        for i in range(1, n + 1):
            ys, xs = np.nonzero((lab == i) & red)
            if best is None or len(xs) > best[2]:
                w = a[ys, xs, 0]
                best = ((xs * w).sum() / w.sum() + x0, (ys * w).sum() / w.sum() + y0, len(xs))
        out.append(best if best else (float("nan"), float("nan"), 0))
    return out


def skull_top(x):
    """Top of the cranium over the forehead (panel columns 178-200, clear of the crown knobs)."""
    a = x.astype(int)
    warm = ((a[..., 0] - a[..., 2]) > 10) & (a[..., 0] > 38)
    warm = ndi.binary_opening(warm, structure=np.ones((5, 5)))
    rows = np.nonzero(warm[:, 178:200].sum(1) >= 15)[0]               # most of the columns are skull
    rows = rows[rows > 20]                                             # below the panel title
    return int(rows.min()) if len(rows) else -1


def teeth(x):
    x0, y0, x1, y1 = MOUTH
    sub = x[y0:y1, x0:x1]
    hsv = np.asarray(Image.fromarray(sub).convert("HSV")).astype(int)
    m = (hsv[..., 0] >= 19) & (hsv[..., 0] <= 40) & (hsv[..., 2] >= 105) & (hsv[..., 1] >= 60)
    m = ndi.binary_opening(m, structure=np.ones((2, 2)))
    ys, xs = np.nonzero(m)
    return (xs.min() + x0, ys.min() + y0, xs.max() + x0, ys.max() + y0), int(m.sum())


rows = [("sheet", load_panel())] + [(os.path.basename(os.path.dirname(os.path.abspath(p))) + "/" + os.path.basename(p),
                                     load_render(p)) for p in RENDERS]
for name, img in rows:
    pp = pupils(img)
    tb, ta = teeth(img)
    print("%-28s pupils %s | skull top y %d | teeth box x %d-%d, y %d-%d (lowest tooth y %d) | teeth area %d px"
          % (name, ", ".join("(%.1f, %.1f)" % (px, py) for px, py, _ in pp), skull_top(img),
             tb[0], tb[2], tb[1], tb[3], tb[3], ta))
