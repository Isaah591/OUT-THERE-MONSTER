"""
Validation sheets for the v6 variation against the approved sheet's three-quarter panel, with v5
alongside (both rendered from the fitted camera `ref34` under STUDIO=sheet, at twice the panel's
resolution, so all three share one pixel grid).

    python v6_compare.py <renders_dir> <references_dir> <silhouette_prefix> <out_dir>

<renders_dir> holds v6_ref34.png, v5_ref34.png and (optional) v6_oj_front.png / v6_oj_side.png;
<silhouette_prefix> is the prefix given to silhouette_ref34.py (its <prefix>_v5_overlay.png and
<prefix>_v6_overlay.png). Writes into <out_dir>:
    _v6_vs_ref34.png          sheet | v5 | v6, whole panel, same camera and pixels
    _v6_vs_ref34_head.png     head crops: sheet | v5 | v6
    _v6_silhouettes.png       silhouette overlays against the sheet: v5 | v6
    _v6_blend.png             sheet and v6 blended 50/50
    _v6_front_side.png        v6 from the front and the exact side (the new pose from other views)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

R, REFS, SIL, OUT = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True)
PANEL34 = (500, 55, 1008, 550)
HEAD = (110, 20, 360, 330)
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
except OSError:
    FONT = ImageFont.load_default()


def labelled(im, text):
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 36), fill=(18, 18, 20))
    d.text((10, 5), text, fill=(235, 235, 235), font=FONT)
    return im


def row(items, h, gap=10):
    ims = []
    for im, text in items:
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        ims.append(labelled(im, text) if text else im)
    out = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), (10, 10, 10))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out


def load(name):
    return Image.open(os.path.join(R, name)).convert("RGB")


sheet = Image.open(os.path.join(REFS, "r08_open_jaw_sheet_v2.webp")).convert("RGB").crop(PANEL34)
big = sheet.resize((sheet.width * 2, sheet.height * 2), Image.LANCZOS)
v5, v6 = load("v5_ref34.png"), load("v6_ref34.png")
row([(big, "APPROVED SHEET - THREE-QUARTER"), (v5, "V5"), (v6, "V6 - SAME CAMERA")], 990).save(
    os.path.join(OUT, "_v6_vs_ref34.png"))
hb = tuple(c * 2 for c in HEAD)
row([(big.crop(hb), "APPROVED SHEET"), (v5.crop(hb), "V5"), (v6.crop(hb), "V6")], 930).save(
    os.path.join(OUT, "_v6_vs_ref34_head.png"))
s5 = Image.open(SIL + "_v5_overlay.png").convert("RGB")
s6 = Image.open(SIL + "_v6_overlay.png").convert("RGB")
row([(s5, "V5 vs SHEET (red: sheet only, blue: model only)"), (s6, "V6 vs SHEET")], 990).save(
    os.path.join(OUT, "_v6_silhouettes.png"))
a = np.asarray(big).astype(float)
b = np.asarray(v6.resize(big.size, Image.LANCZOS)).astype(float)
row([(Image.fromarray(((a + b) / 2).astype(np.uint8)), "SHEET + V6, 50/50")], 990).save(os.path.join(OUT, "_v6_blend.png"))
fs = [n for n in ("v6_oj_front.png", "v6_oj_side.png") if os.path.exists(os.path.join(R, n))]
if fs:
    row([(load(n), "V6 - " + ("FRONT" if "front" in n else "EXACT SIDE")) for n in fs], 900).save(
        os.path.join(OUT, "_v6_front_side.png"))
print("v6 comparison sheets written to", OUT)
