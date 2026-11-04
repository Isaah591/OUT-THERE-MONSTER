"""
Validation sheets for the v7 variation against the approved sheet's three main views, with v6
alongside. Every render is at twice the panel's resolution, so sheet and model share one pixel
grid in each view.

    python v7_compare.py <renders_dir> <references_dir> <out_dir>

<renders_dir> (model/renders_v7) holds:
    v7_fit34.png / v6_ref34.png       three-quarter: v7 from the camera fitted to it (render_views.py
                                      `fit34`), v6 from its own fitted camera (`ref34`)
    v7_front.png / v6_front.png       the sheet's front panel as an orthographic camera (`sheet_front`)
    v7_side.png / v6_side.png         the sheet's exact side panel (`sheet_side`)
    sil_<v6|v7>_<front|side|34>.png   silhouette overlays from sheet_views.py (sheet only red,
                                      model only blue)
Writes into <out_dir>:
    _v7_vs_34.png, _v7_vs_front.png, _v7_vs_side.png    sheet | v6 | v7, whole panel
    _v7_heads.png                                       head and mouth close-ups, sheet | v7, three views
    _v7_silhouettes.png                                 overlays against the sheet, v6 (top) | v7 (bottom)
    _v7_blend34.png                                     sheet and v7 blended 50/50 (three-quarter)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

R, REFS, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
HEADS = {"front": (190, 0, 360, 190), "34": (110, 20, 330, 250), "side": (60, 20, 280, 250)}   # panel px
NAMES = {"front": "FRONT", "34": "THREE-QUARTER", "side": "EXACT SIDE"}
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
except OSError:
    FONT = ImageFont.load_default()


def labelled(im, text):
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 34), fill=(18, 18, 20))
    d.text((10, 5), text, fill=(235, 235, 235), font=FONT)
    return im


def row(items, h, gap=10):
    ims = [labelled(im.resize((round(im.width * h / im.height), h), Image.LANCZOS), t) for im, t in items]
    out = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), (10, 10, 10))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def stack(rows, gap=10):
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + gap * (len(rows) - 1)), (10, 10, 10))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + gap
    return out


sheet_img = Image.open(os.path.join(REFS, "r08_open_jaw_sheet_v2.webp")).convert("RGB")
sheet = {k: sheet_img.crop(b).resize(((b[2] - b[0]) * 2, (b[3] - b[1]) * 2), Image.LANCZOS) for k, b in PANELS.items()}
load = lambda n: Image.open(os.path.join(R, n)).convert("RGB")
v7 = {"34": load("v7_fit34.png"), "front": load("v7_front.png"), "side": load("v7_side.png")}
v6 = {"34": load("v6_ref34.png"), "front": load("v6_front.png"), "side": load("v6_side.png")}
for k, fname in (("34", "_v7_vs_34.png"), ("front", "_v7_vs_front.png"), ("side", "_v7_vs_side.png")):
    row([(sheet[k], "APPROVED SHEET - " + NAMES[k]), (v6[k], "V6"), (v7[k], "V7 - SAME VIEW")], 990).save(
        os.path.join(OUT, fname))
heads = []
for k in ("front", "34", "side"):
    c = tuple(v * 2 for v in HEADS[k])
    heads += [(sheet[k].crop(c), "SHEET " + NAMES[k]), (v7[k].resize(sheet[k].size, Image.LANCZOS).crop(c), "V7")]
row(heads, 560).save(os.path.join(OUT, "_v7_heads.png"))
sil = lambda v, k: Image.open(os.path.join(R, "sil_%s_%s.png" % (v, k))).convert("RGB")
stack([row([(sil(v, k), "%s vs SHEET - %s" % (v.upper(), NAMES[k])) for k in ("front", "34", "side")], 700)
       for v in ("v6", "v7")]).save(os.path.join(OUT, "_v7_silhouettes.png"))
a = np.asarray(sheet["34"]).astype(float)
b = np.asarray(v7["34"].resize(sheet["34"].size, Image.LANCZOS)).astype(float)
row([(Image.fromarray(((a + b) / 2).astype(np.uint8)), "SHEET + V7, 50/50 (THREE-QUARTER)")], 990).save(
    os.path.join(OUT, "_v7_blend34.png"))
print("v7 comparison sheets written to", OUT)
