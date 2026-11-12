"""The approved reference sheet: panel rectangles and creature masks.

Everything here is read straight off references/r08_open_jaw_sheet_v2.webp (the sheet attached
to the Experimental Model 02 brief).  Nothing is taken from earlier builds.
"""
import os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHEET = os.path.join(ROOT, "references", "r08_open_jaw_sheet_v2.webp")

# (left, top, right, bottom) of each picture on the sheet, in sheet pixels
PANELS = {
    "front": (0, 52, 490, 548),
    "tq": (498, 52, 1008, 548),
    "side": (1016, 52, 1484, 548),
    "head": (0, 556, 438, 908),
    "jaw_prev": (455, 595, 620, 858),
    "jaw_new": (629, 595, 860, 858),
    "mouth": (878, 595, 1188, 908),
    "sideclose": (1198, 595, 1484, 912),
}


def load_sheet():
    return Image.open(SHEET).convert("RGB")


def panel(name, sheet=None):
    sheet = sheet or load_sheet()
    return sheet.crop(PANELS[name])


def creature_mask(img, label_box=None):
    """Boolean mask of the creature in a panel (rust / tissue / teeth against the grey studio)."""
    a = np.asarray(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    warm = (r - b) > 14          # rust, tissue and ivory are all much redder than the backdrop
    lum = (r + g + b) / 3.0
    m = warm & (lum > 22)
    if label_box is not None:    # the white panel caption
        x0, y0, x1, y1 = label_box
        m[y0:y1, x0:x1] = False
    from scipy import ndimage as ndi
    m = ndi.binary_closing(m, iterations=2)
    # fill pinholes (dark pits, black sockets, mouth) but keep real gaps such as between the legs
    holes = ndi.binary_fill_holes(m) & ~m
    hl, hn = ndi.label(holes)
    if hn:
        hs = ndi.sum(holes, hl, range(1, hn + 1))
        small = [i + 1 for i, a in enumerate(hs) if a < 0.006 * m.size]
        m = m | np.isin(hl, small)
    lab, n = ndi.label(m)
    if n > 1:                    # keep the big component (and anything nearly as big)
        sizes = ndi.sum(m, lab, range(1, n + 1))
        keep = [i + 1 for i, s in enumerate(sizes) if s > 0.02 * sizes.max()]
        m = np.isin(lab, keep)
    return m
