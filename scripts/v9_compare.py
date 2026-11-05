"""
Head comparison sheets for the v9 head reconstruction against the approved sheet, with v8
alongside. All renders use the same cameras as v7/v8 (three-quarter: v7's fitted `fit34` camera;
exact side and front: the sheet's panels as orthographic cameras), at twice the panel resolution,
so the sheet and both versions share one pixel grid.

    python v9_compare.py <renders_dir> <references_dir> <out_dir>

<renders_dir> (model/renders_v9) holds v9_fit34.png, v9_side.png, v9_front.png, v8_fit34.png,
v8_side.png, v8_front.png and the head overlays of measure_head_v8.py (<v8|v9>_head_<view>.png).
Writes into <out_dir>:
    _v9_head_34.png, _v9_head_side.png, _v9_head_front.png    head close-ups: sheet | v8 | v9
    _v9_vs_34.png, _v9_vs_side.png                             whole panels: sheet | v9
    _v9_head_silhouettes.png                                   head outlines against the sheet: v8 | v9
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

R, REFS, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
HEADS = {"front": (195, 0, 345, 175), "34": (125, 25, 300, 235), "side": (60, 20, 250, 250)}   # panel px
NAMES = {"front": "FRONT", "34": "THREE-QUARTER", "side": "EXACT SIDE"}
FILES = {"front": "front", "34": "fit34", "side": "side"}
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
for view in ("34", "front", "side"):
    b = PANELS[view]
    sheet = sheet_img.crop(b).resize(((b[2] - b[0]) * 2, (b[3] - b[1]) * 2), Image.LANCZOS)
    c = tuple(v * 2 for v in HEADS[view])
    v8 = Image.open(os.path.join(R, "v8_%s.png" % FILES[view])).convert("RGB").resize(sheet.size, Image.LANCZOS)
    v9 = Image.open(os.path.join(R, "v9_%s.png" % FILES[view])).convert("RGB").resize(sheet.size, Image.LANCZOS)
    row([(sheet.crop(c), "APPROVED SHEET - " + NAMES[view]), (v8.crop(c), "V8"), (v9.crop(c), "V9 - SAME VIEW")],
        900).save(os.path.join(OUT, "_v9_head_%s.png" % view))
    if view in ("34", "side"):
        row([(sheet, "APPROVED SHEET - " + NAMES[view]), (v9, "V9 - SAME CAMERA")], 990).save(
            os.path.join(OUT, "_v9_vs_%s.png" % view))
ov = lambda v, k: Image.open(os.path.join(R, "%s_head_%s.png" % (v, k))).convert("RGB")
stack([row([(ov(v, k), "%s HEAD vs SHEET - %s" % (v.upper(), NAMES[k])) for k in ("34", "side", "front")], 640)
       for v in ("v8", "v9")]).save(os.path.join(OUT, "_v9_head_silhouettes.png"))
print("v9 head comparison sheets written to", OUT)
