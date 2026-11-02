"""
Validation sheets for the v5 variation against the approved sheet (ASTRA R08 - MORE OPEN JAW,
references/r08_open_jaw_sheet_v2.webp), with the current (unchanged) open-jaw model alongside.

    python v5_compare.py <v5_renders_dir> <current_renders_dir> <references_dir> <out_dir>

The three-quarter comparisons use the `ref34` camera of render_views.py, fitted to the sheet's
three-quarter panel with fit_camera.py and rendered at exactly twice the panel's resolution,
so the reference panel and the render share one pixel grid (panel pixels are quoted below).
Writes into <out_dir>:
    _v5_vs_ref34.png            sheet three-quarter panel | v5 (whole panel, same pixels)
    _v5_vs_ref34_head.png       head crop: sheet | current model | v5
    _v5_ref34_grid.png          head crop with a panel-pixel grid: sheet | v5 (for measuring)
    _v5_ref34_alignment.png     sheet and v5 blended 50/50, and the sheet's edges drawn on v5
    _v5_vs_ref34_body.png       sheet three-quarter panel | v5 from the whole-figure camera fit
    _v5_vs_front.png            sheet front | current | v5 (oj_front, pose and proportions check)
    _v5_vs_side.png             sheet exact side | current | v5 (oj_side)
    _v5_vs_face.png             sheet face (front) | v5 (oj_face)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

V5, CUR, REFS, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
SHEET = Image.open(os.path.join(REFS, "r08_open_jaw_sheet_v2.webp")).convert("RGB")
PANEL34 = (500, 55, 1008, 550)                 # 508 x 495; ref34 renders at 1016 x 990
PANEL_FRONT, PANEL_SIDE = (0, 55, 490, 550), (1017, 55, 1484, 550)
PANEL_FACE = (196, 52, 334, 222)
HEAD = (110, 20, 360, 330)                     # head crop, panel pixels
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except OSError:
    FONT = SMALL = ImageFont.load_default()


def label(im, text):
    """Pair an image with its caption; the caption is drawn after the image is scaled (row)."""
    return (im, text)


def _draw_label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 36), fill=(18, 18, 20))
    d.text((10, 5), text, fill=(235, 235, 235), font=FONT)
    return im


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def row(items, h, gap=10):
    ims = []
    for it in items:
        im, text = it if isinstance(it, tuple) else (it, None)
        im = fit(im, h)
        ims.append(_draw_label(im, text) if text else im)
    out = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), (10, 10, 10))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def render(d, name):
    return Image.open(os.path.join(d, name + ".png")).convert("RGB")


panel = SHEET.crop(PANEL34)
pw, ph = panel.size
v5_34 = render(V5, "ref34").resize((pw, ph), Image.LANCZOS)          # onto the panel's pixel grid
cur_34 = render(CUR, "ref34").resize((pw, ph), Image.LANCZOS)

# 1. whole panel, same pixels
big = (pw * 2, ph * 2)
row([label(panel.resize(big, Image.LANCZOS), "APPROVED SHEET - THREE-QUARTER"),
     label(render(V5, "ref34"), "V5 - SAME CAMERA (FITTED)")], ph * 2).save(os.path.join(OUT, "_v5_vs_ref34.png"))

# 2. head crop: sheet | current | v5
hs = (750, 930)
crops = [im.crop(HEAD).resize(hs, Image.LANCZOS) for im in (panel, cur_34, v5_34)]
row([label(crops[0], "APPROVED SHEET"), label(crops[1], "CURRENT MODEL (UNCHANGED)"), label(crops[2], "V5 VARIATION")],
    hs[1]).save(os.path.join(OUT, "_v5_vs_ref34_head.png"))

# 3. grid in panel pixels
gbox = (120, 40, 320, 240)
grids = []
for im, t in ((panel, "APPROVED SHEET"), (v5_34, "V5")):
    g = im.crop(gbox).resize((800, 800), Image.LANCZOS)
    d = ImageDraw.Draw(g)
    for i in range(0, 200, 10):
        y = i * 4
        c = (0, 255, 255) if i % 50 == 0 else (60, 95, 95)
        d.line([(0, y), (800, y)], fill=c, width=1)
        d.line([(y, 0), (y, 800)], fill=c, width=1)
        if i % 20 == 0:
            d.text((3, y + 2), str(gbox[1] + i), fill=(255, 255, 0), font=SMALL)
            d.text((y + 3, 20), str(gbox[0] + i), fill=(255, 255, 0), font=SMALL)
    grids.append(label(g, t + " - panel px"))
row(grids, 800).save(os.path.join(OUT, "_v5_ref34_grid.png"))

# 4. alignment: 50/50 blend, and both silhouette outlines (the masks fit_camera.py matches)
def silhouette(im):
    """Warm (rust / teeth / tissue) pixels against the neutral backdrop, closed and filled,
    largest component - the same segmentation fit_camera.py uses."""
    from scipy import ndimage as ndi
    x = np.asarray(im).astype(int)
    warm = ((x[..., 0] - x[..., 2]) > 10) & (x[..., 0] > 38)
    warm[: int(0.07 * x.shape[0]), : int(0.75 * x.shape[1])] = False        # panel title
    warm = ndi.binary_closing(warm, structure=np.ones((3, 3)), iterations=2)
    warm = ndi.binary_fill_holes(warm)
    lab, n = ndi.label(warm)
    return lab == (1 + int(np.argmax(ndi.sum(warm, lab, range(1, n + 1)))))


def outline(mask):
    from scipy import ndimage as ndi
    return mask & ~ndi.binary_erosion(mask, iterations=2)


a = np.asarray(panel.crop(HEAD).resize(hs, Image.LANCZOS)).astype(float)
b = np.asarray(v5_34.crop(HEAD).resize(hs, Image.LANCZOS)).astype(float)
blend = Image.fromarray(((a + b) / 2).astype(np.uint8))
ma = np.asarray(Image.fromarray(silhouette(panel)).crop(HEAD).resize(hs, Image.NEAREST))
mb = np.asarray(Image.fromarray(silhouette(v5_34)).crop(HEAD).resize(hs, Image.NEAREST))
ov = b * 0.55
ov[outline(ma)] = (0, 255, 255)
ov[outline(mb)] = (255, 60, 220)
ov = Image.fromarray(ov.astype(np.uint8))
ImageDraw.Draw(ov).text((10, 44), "cyan: sheet outline   magenta: v5 outline", fill=(235, 235, 235), font=SMALL)
row([label(blend, "SHEET + V5, 50/50"), label(ov, "SILHOUETTE OUTLINES")],
    hs[1]).save(os.path.join(OUT, "_v5_ref34_alignment.png"))

# 5. whole-figure camera fit
row([label(panel.resize(big, Image.LANCZOS), "APPROVED SHEET - THREE-QUARTER"),
     label(render(V5, "ref34_body"), "V5 - WHOLE-FIGURE CAMERA FIT")], ph * 2).save(os.path.join(OUT, "_v5_vs_ref34_body.png"))

# 6. front / side: pose and proportions unchanged, head from the other sheet views
for key, box, name, title in (("oj_front", PANEL_FRONT, "_v5_vs_front.png", "FRONT"),
                              ("oj_side", PANEL_SIDE, "_v5_vs_side.png", "EXACT SIDE")):
    row([label(SHEET.crop(box), "SHEET - " + title), label(render(CUR, key), "CURRENT - " + title),
         label(render(V5, key), "V5 - " + title)], 760).save(os.path.join(OUT, name))

# 7. face, front
row([label(SHEET.crop(PANEL_FACE), "SHEET - FACE, FRONT"), label(render(V5, "oj_face"), "V5 - FACE, FRONT")],
    760).save(os.path.join(OUT, "_v5_vs_face.png"))
print("v5 comparison sheets written to", OUT)
