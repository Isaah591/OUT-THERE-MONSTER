"""
Head comparison sheets for v15 ("Experimental 11": the posterior teeth lengthened, the brows angrier)
against the approved sheet, with v14 alongside. All renders use the same cameras as v7-v14 (three-
quarter: v7's fitted `fit34` camera; front and exact side: the sheet's panels as orthographic cameras),
at twice the panel resolution, so the sheet and both versions share one pixel grid. The side view is
also rendered with one more light on the camera's side (render_views.py, SIDE_KEY=700), as the sheet's
side panel is lit: under the three-quarter rig alone the lower jaw's outer face is in shadow.

    python v15_compare.py <renders_dir> <references_dir> <out_dir>

<renders_dir> (model/renders_v15) holds, for v14 and v15 (prefix v14_ / v15_):
    <v>_fit34.png, <v>_front.png, <v>_side.png        the sheet's three views
    <v>_side_lit.png                                   exact side with the side light
    <v>_nt_fit34.png, <v>_nt_front.png, <v>_nt_side_lit.png   the same with the teeth and pupils hidden
    <v>_head_<view>.png                                head outlines against the sheet (measure_head_v8.py)
    v15_anatomy_<view>.png                             v15_anatomy_check.py's overlays
    v15_lengthened_<view>.png                          v15_anatomy_check.py's lengthened-teeth overlays
Writes into <out_dir>:
    _v15_head_34.png, _v15_head_front.png, _v15_head_side.png    head close-ups: sheet | v14 | v15
    _v15_side_lit.png                                            exact side, side light: sheet | v14 | v15
    _v15_mouth_34.png, _v15_mouth_front.png, _v15_mouth_side.png the mouth closer still (side: side light)
    _v15_lengthened.png                                          the lengthened teeth, three views: each
                                                                 one's v14 extent (white) and what v15
                                                                 adds (yellow)
    _v15_teeth_hidden.png                                        teeth and pupils hidden, three views:
                                                                 sheet | v14 | v15 (the jaws and the
                                                                 opening are v14's; the brows changed)
    _v15_eyes.png                                                the eyes: sheet | v14 | v15, with and
                                                                 without the pupils
    _v15_vs_34.png, _v15_vs_front.png, _v15_vs_side.png          whole panels: sheet | v15
    _v15_head_silhouettes.png                                    head outlines against the sheet: v14 | v15
    _v15_anatomy_overlays.png                                    the sheet's annotations on v15
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

R, REFS, OUT = sys.argv[1:4]
os.makedirs(OUT, exist_ok=True)
PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
HEADS = {"front": (190, 0, 350, 215), "34": (120, 20, 305, 240), "side": (60, 20, 250, 250)}    # panel px
MOUTHS = {"front": (212, 40, 322, 212), "34": (140, 75, 262, 232), "side": (70, 85, 215, 245)}
EYES = {"front": (215, 20, 310, 75), "34": (145, 50, 235, 102)}
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


def sheet(view):
    b = PANELS[view]
    return sheet_img.crop(b).resize(((b[2] - b[0]) * 2, (b[3] - b[1]) * 2), Image.LANCZOS)


def render(name, size):
    return Image.open(os.path.join(R, name)).convert("RGB").resize(size, Image.LANCZOS)


c2 = lambda box: tuple(v * 2 for v in box)
for view in ("34", "front", "side"):
    s = sheet(view)
    v14, v15 = (render("%s_%s.png" % (v, FILES[view]), s.size) for v in ("v14", "v15"))
    c = c2(HEADS[view])
    row([(s.crop(c), "APPROVED SHEET - " + NAMES[view]), (v14.crop(c), "V14"), (v15.crop(c), "V15 - SAME VIEW")],
        900).save(os.path.join(OUT, "_v15_head_%s.png" % view))
    m = c2(MOUTHS[view])
    if view == "side":                   # the jaw's outer face needs the side light
        v14, v15 = (render("%s_side_lit.png" % v, s.size) for v in ("v14", "v15"))
    row([(s.crop(m), "SHEET - MOUTH, " + NAMES[view]), (v14.crop(m), "V14"), (v15.crop(m), "V15")], 900).save(
        os.path.join(OUT, "_v15_mouth_%s.png" % view))
    v15 = render("v15_%s.png" % FILES[view], s.size)
    row([(s, "APPROVED SHEET - " + NAMES[view]), (v15, "V15 - SAME CAMERA")], 990).save(
        os.path.join(OUT, "_v15_vs_%s.png" % view))
s = sheet("side")
c = c2(HEADS["side"])
row([(s.crop(c), "APPROVED SHEET - EXACT SIDE"), (render("v14_side_lit.png", s.size).crop(c), "V14 - SIDE LIGHT"),
     (render("v15_side_lit.png", s.size).crop(c), "V15 - SIDE LIGHT")], 900).save(os.path.join(OUT, "_v15_side_lit.png"))
rows = []
for view, f in (("front", "front"), ("34", "fit34"), ("side", "side_lit")):
    s = sheet(view)
    c = c2(HEADS[view])
    rows.append(row([(s.crop(c), "SHEET - " + NAMES[view]),
                     (render("v14_nt_%s.png" % f, s.size).crop(c), "V14 - NO TEETH, NO PUPILS"),
                     (render("v15_nt_%s.png" % f, s.size).crop(c), "V15 - NO TEETH, NO PUPILS")], 700))
stack(rows).save(os.path.join(OUT, "_v15_teeth_hidden.png"))
rows = []
for view in ("front", "34"):
    s = sheet(view)
    c = c2(EYES[view])
    f = FILES[view]
    rows.append(row([(s.crop(c), "SHEET - EYES, " + NAMES[view]),
                     (render("v14_%s.png" % f, s.size).crop(c), "V14"), (render("v15_%s.png" % f, s.size).crop(c), "V15"),
                     (render("v14_nt_%s.png" % f, s.size).crop(c), "V14 NO PUPILS"),
                     (render("v15_nt_%s.png" % f, s.size).crop(c), "V15 NO PUPILS")], 360))
stack(rows).save(os.path.join(OUT, "_v15_eyes.png"))
ov = lambda v, k: Image.open(os.path.join(R, "%s_head_%s.png" % (v, k))).convert("RGB")
stack([row([(ov(v, k), "%s HEAD vs SHEET - %s" % (v.upper(), NAMES[k])) for k in ("front", "34", "side")], 640)
       for v in ("v14", "v15")]).save(os.path.join(OUT, "_v15_head_silhouettes.png"))
ln = lambda k: Image.open(os.path.join(R, "v15_lengthened_%s.png" % k)).convert("RGB")
row([(ln(k), "%s: WHITE V14, YELLOW V15" % NAMES[k]) for k in ("front", "34", "side")],
    900).save(os.path.join(OUT, "_v15_lengthened.png"))
an = lambda k: Image.open(os.path.join(R, "v15_anatomy_%s.png" % k)).convert("RGB")
row([(an(k), "SHEET ANATOMY ON V15 - " + NAMES[k]) for k in ("front", "34", "side")], 900).save(
    os.path.join(OUT, "_v15_anatomy_overlays.png"))
print("v15 head comparison sheets written to", OUT)
