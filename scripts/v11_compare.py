"""
Head comparison sheets for the v11 head anatomy correction against the approved sheet, with v10
alongside. All renders use the same cameras as v7-v10 (three-quarter: v7's fitted `fit34` camera; front and exact
side: the sheet's panels as orthographic cameras), at twice the panel resolution, so the sheet and
both versions share one pixel grid.

    python v11_compare.py <renders_dir> <references_dir> <out_dir>

<renders_dir> (model/renders_v11) holds v11_fit34.png, v11_front.png, v11_side.png, v10_fit34.png,
v10_front.png, v10_side.png, the head overlays of measure_head_v8.py (<v10|v11>_head_<view>.png) and the
class maps of measure_mouth_v10.py (<v10|v11>_classes_<front|34>.png). Writes into <out_dir>:
    _v11_head_34.png, _v11_head_front.png, _v11_head_side.png   head close-ups: sheet | v10 | v11
    _v11_vs_34.png, _v11_vs_front.png, _v11_vs_side.png         whole panels: sheet | v11
    _v11_head_silhouettes.png                                   head outlines against the sheet: v10 | v11
    _v11_mouth_classes.png                                      class maps (rust, teeth, voids, tissue): v10 | v11
    _v11_anatomy_overlays.png                                   the sheet's annotated teeth and mouth on v11
                                                                (v11_anatomy_check.py's v11_anatomy_<view>.png)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

R, REFS, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
HEADS = {"front": (190, 0, 350, 180), "34": (120, 20, 305, 240), "side": (60, 20, 250, 250)}   # panel px
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
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + gap * (len(rows) - 1)),
                    (10, 10, 10))
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
    v10 = Image.open(os.path.join(R, "v10_%s.png" % FILES[view])).convert("RGB").resize(sheet.size, Image.LANCZOS)
    v11 = Image.open(os.path.join(R, "v11_%s.png" % FILES[view])).convert("RGB").resize(sheet.size, Image.LANCZOS)
    row([(sheet.crop(c), "APPROVED SHEET - " + NAMES[view]), (v10.crop(c), "V10"), (v11.crop(c), "V11 - SAME VIEW")],
        900).save(os.path.join(OUT, "_v11_head_%s.png" % view))
    row([(sheet, "APPROVED SHEET - " + NAMES[view]), (v11, "V11 - SAME CAMERA")], 990).save(
        os.path.join(OUT, "_v11_vs_%s.png" % view))
ov = lambda v, k: Image.open(os.path.join(R, "%s_head_%s.png" % (v, k))).convert("RGB")
stack([row([(ov(v, k), "%s HEAD vs SHEET - %s" % (v.upper(), NAMES[k])) for k in ("front", "34", "side")], 640)
       for v in ("v10", "v11")]).save(os.path.join(OUT, "_v11_head_silhouettes.png"))
cl = lambda v, k: Image.open(os.path.join(R, "%s_classes_%s.png" % (v, k))).convert("RGB")
stack([row([(cl(v, k), "%s: SHEET | CLASSES | %s | CLASSES - %s" % (v.upper(), v.upper(), NAMES[k]))], 520)
       for k in ("front", "34") for v in ("v10", "v11")]).save(os.path.join(OUT, "_v11_mouth_classes.png"))
an = lambda k: Image.open(os.path.join(R, "v11_anatomy_%s.png" % k)).convert("RGB")
row([(an(k), "SHEET ANATOMY ON V11 - " + NAMES[k]) for k in ("front", "34", "side")], 900).save(
    os.path.join(OUT, "_v11_anatomy_overlays.png"))
print("v11 head comparison sheets written to", OUT)
