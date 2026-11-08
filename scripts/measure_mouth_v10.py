"""
Interior head features against the approved sheet, in the front and three-quarter views (the
silhouette tools only see the outline). The sheet's panel and a model render (render_views.py at
twice the panel resolution, same cameras) are both classified pixel by pixel into rust, teeth
(ivory), dark voids and red tissue; from those class maps it reports:

- the eye sockets (dark boxes in the face, panel px),
- the mouth region (teeth + voids + tissue under the face): its top, bottom, width per row and its
  overlap (IoU) with the sheet's,
- teeth and red-tissue areas,

and writes an analysis image per view: sheet | sheet classes | render | render classes.

    python measure_mouth_v10.py <out_prefix> front=<sheet_front.png> 34=<fit34.png>    (no bpy needed)
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")

PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
HEADS = {"front": (190, 0, 350, 180), "34": (120, 20, 305, 240), "side": (60, 20, 250, 250)}   # panel px
FACE = {"front": (215, 25, 315, 60), "34": (150, 50, 260, 100)}                               # socket search
MOUTH = {"front": (205, 55, 330, 175), "34": (140, 85, 265, 230)}                             # mouth search
COL = np.array([(25, 25, 30), (150, 85, 45), (240, 220, 160), (0, 0, 0), (200, 20, 30)], np.uint8)


def hsv(a):
    a = a / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6.0
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0)
    return h, s, mx


def classify(rgb, fig):
    """0 background, 1 rust, 2 teeth (ivory), 3 dark void, 4 red tissue."""
    h, s, v = hsv(rgb.astype(float))
    c = np.where(fig, 1, 0)
    c = np.where(fig & (v > 0.45) & (h > 0.065) & (h < 0.17) & (s < 0.62), 2, c)
    dark = fig & (v < 0.15)
    c = np.where(dark, 3, c)
    c = np.where(fig & ~dark & ((h < 0.03) | (h > 0.95)) & (s > 0.45) & (v < 0.62), 4, c)
    return c


def sheet_classes(view):
    import sheet_views as SV
    fig, panel = SV.sheet_masks(REFS)[view]
    return classify(panel, fig), panel


def render_classes(path, view):
    b = PANELS[view]
    W, H = b[2] - b[0], b[3] - b[1]
    im = np.asarray(Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS)).astype(float)
    bgc = np.median(np.concatenate([im[:8].reshape(-1, 3), im[:, :8].reshape(-1, 3)]), axis=0)
    fig = np.abs(im - bgc).max(-1) > 12
    return classify(im, fig), im


def features(c, view):
    out = {}
    fx0, fy0, fx1, fy1 = FACE[view]
    lab, n = ndi.label(ndi.binary_opening((c == 3)[fy0:fy1, fx0:fx1], iterations=1))
    socks = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(ys) >= 12:
            socks.append((int(xs.min() + fx0), int(ys.min() + fy0), int(xs.max() + fx0), int(ys.max() + fy0), len(ys)))
    out["sockets"] = sorted(socks, key=lambda s: -s[4])[:2]
    mx0, my0, mx1, my1 = MOUTH[view]
    m = ndi.binary_closing(np.isin(c, (2, 3, 4))[my0:my1, mx0:mx1], iterations=2)
    lab, n = ndi.label(m)
    if n:
        m = ndi.binary_fill_holes(lab == (1 + int(np.argmax(ndi.sum(m, lab, range(1, n + 1))))))
    out["rows"] = [(y + my0, int(np.flatnonzero(m[y]).min() + mx0), int(np.flatnonzero(m[y]).max() + mx0))
                   for y in range(m.shape[0]) if m[y].sum() > 2]
    ys = np.nonzero(m)[0]
    out["top"], out["bottom"] = (int(ys.min() + my0), int(ys.max() + my0)) if len(ys) else (None, None)
    out["mask"] = m
    out["teeth"] = int((c == 2)[my0:my1, mx0:mx1].sum())
    out["red"] = int((c == 4)[my0:my1, mx0:mx1].sum())
    return out


def report(name, f):
    print("  %-6s sockets (x0, y0, x1, y1, area): %s" % (name, f["sockets"]))
    print("  %-6s mouth rows %s..%s | teeth %d px, red tissue %d px" % (name, f["top"], f["bottom"], f["teeth"], f["red"]))
    rows = [r for r in f["rows"] if (r[0] - f["rows"][0][0]) % 10 == 0] if f["rows"] else []
    print("  %-6s mouth width per row: %s" % (name, "  ".join("%d:%d" % (y, b - a) for y, a, b in rows)))


if __name__ == "__main__":
    prefix = sys.argv[1]
    for arg in sys.argv[2:]:
        view, path = arg.split("=")
        sc, sp = sheet_classes(view)
        rc, rim = render_classes(path, view)
        print("== %s (%s)" % (view, os.path.basename(path)))
        fs, fm = features(sc, view), features(rc, view)
        report("sheet", fs)
        report("model", fm)
        a, b = fs["mask"], fm["mask"]
        print("  mouth-region IoU %.3f" % ((a & b).sum() / max((a | b).sum(), 1)))
        x0, y0, x1, y1 = HEADS[view]
        tiles = [sp[y0:y1, x0:x1].astype(np.uint8), COL[sc[y0:y1, x0:x1]], rim[y0:y1, x0:x1].astype(np.uint8),
                 COL[rc[y0:y1, x0:x1]]]
        row = np.concatenate([np.pad(t, ((0, 0), (0, 4), (0, 0))) for t in tiles], axis=1)
        Image.fromarray(row).resize((row.shape[1] * 3, row.shape[0] * 3), Image.NEAREST).save(
            "%s_classes_%s.png" % (prefix, view))
