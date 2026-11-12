"""Compose the presentation sheet and the comparison sheet for Experimental Model 02.

    bvenv/bin/python experimental_02/src/make_sheets.py [renders_dir]

Writes into the renders folder:
    ASTRA_R08_EXP02_sheet.png        the model's own sheet (same panel order as the approved sheet)
    ASTRA_R08_EXP02_vs_approved.png  every view beside the approved sheet's matching panel
    silhouette_check.png             outline overlays of the three body views (with IoU)
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sheet as S
import views
from compare import fit_masks

BG = (13, 14, 15)
FG = (236, 236, 232)
DIM = (160, 162, 160)
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT_R, size)
    except Exception:
        return ImageFont.load_default()


def fit(im, w, h):
    """Scale and centre-crop to exactly w x h."""
    k = max(w / im.width, h / im.height)
    im = im.resize((max(w, int(round(im.width * k))), max(h, int(round(im.height * k)))), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def label(d, xy, text, size, fill=FG, bold=True, shadow=True):
    f = font(size, bold)
    if shadow:
        d.text((xy[0] + 2, xy[1] + 2), text, font=f, fill=(0, 0, 0))
    d.text(xy, text, font=f, fill=fill)


def model_sheet(rdir, facts, out, k=2):
    W = 1484 * k
    row = [("head", "HEAD CLOSE-UP"), ("mouth", "MOUTH CLOSE-UP"), ("mouthside", "MOUTH - EXACT SIDE PROFILE"),
           ("jawside", "JAW - SIDE ANGLE"), ("sideclose", "SIDE ANGLE CLOSE-UP")]
    ims = [Image.open(os.path.join(rdir, key + ".png")).convert("RGB") for key, _ in row]
    gap = 8 * k
    hh = int((W - gap * (len(ims) - 1)) / sum(i.width / i.height for i in ims))
    H = 556 * k + hh + 16 * k + (30 + 17 * max(len(facts["left"]), len(facts["right"]))) * k
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    label(d, (22 * k, 12 * k), "ASTRA R08 - EXPERIMENTAL MODEL 02", 15 * k)
    label(d, (478 * k, 14 * k), "(INDEPENDENT RECONSTRUCTION, FROM SCRATCH)", 12 * k, fill=DIM)
    d.line([(1016 * k, 28 * k), (1118 * k, 28 * k)], fill=DIM, width=k)
    label(d, (1132 * k, 22 * k), "3D MODEL  /  CYCLES RENDER SHEET", 7 * k, fill=DIM, bold=False, shadow=False)
    top = [("front", "FRONT VIEW", (0, 52, 490, 548)), ("tq", "THREE-QUARTER VIEW", (498, 52, 1008, 548)),
           ("side", "SIDE VIEW (EXACT)", (1016, 52, 1484, 548))]
    for key, text, (x0, y0, x1, y1) in top:
        r = Image.open(os.path.join(rdir, key + ".png")).convert("RGB")
        im.paste(fit(r, (x1 - x0) * k, (y1 - y0) * k), (x0 * k, y0 * k))
        label(d, ((x0 + 20) * k, (y0 + 12) * k), text, 10 * k)
    # close-ups: one row, equal height
    x, y = 0, 556 * k
    for (key, text), r in zip(row, ims):
        w = int(round(r.width / r.height * hh))
        im.paste(fit(r, w, hh), (x, y))
        d.rectangle([x, y, x + w - 1, y + hh - 1], outline=(70, 72, 72), width=1)
        label(d, (x + 10 * k, y + 8 * k), text, int(7.5 * k))
        x += w + gap
    # footer
    y = 556 * k + hh + 16 * k
    label(d, (22 * k, y), "WHAT THIS IS", 10 * k)
    for i, line in enumerate(facts["left"]):
        label(d, (22 * k, y + (22 + 17 * i) * k), u"•  " + line, int(7.2 * k), fill=(214, 214, 210), bold=False, shadow=False)
    d.line([(760 * k, y + 2 * k), (760 * k, H - 14 * k)], fill=(120, 122, 120), width=k)
    label(d, (782 * k, y), "CHECKED AGAINST THE APPROVED SHEET", 10 * k)
    for i, line in enumerate(facts["right"]):
        label(d, (782 * k, y + (22 + 17 * i) * k), u"•  " + line, int(7.2 * k), fill=(214, 214, 210), bold=False, shadow=False)
    im.save(out)
    return im


def versus_sheet(rdir, out, k=1.6):
    sh = S.load_sheet()
    rows = [[("front", "FRONT VIEW"), ("tq", "THREE-QUARTER VIEW"), ("side", "SIDE VIEW (EXACT)")],
            [("head", "HEAD CLOSE-UP"), ("mouth", "MOUTH CLOSE-UP")],
            [("jawside", "JAW - SIDE ANGLE"), ("sideclose", "SIDE ANGLE CLOSE-UP")]]
    Hrow = [int(496 * k * 0.80), int(352 * k * 1.06), int(317 * k * 1.12)]
    pad, gap, head = int(16 * k), int(26 * k), int(46 * k)
    blocks = []
    for r, hrow in zip(rows, Hrow):
        tiles = []
        for key, text in r:
            ref = S.panel(views.PANEL_OF[key], sh)
            mine = Image.open(os.path.join(rdir, key + ".png")).convert("RGB")
            w = int(round(ref.width / ref.height * hrow))
            a, b = fit(ref, w, hrow), fit(mine, w, hrow)
            t = Image.new("RGB", (w * 2 + 4, hrow + int(20 * k)), BG)
            t.paste(a, (0, int(20 * k)))
            t.paste(b, (w + 4, int(20 * k)))
            dd = ImageDraw.Draw(t)
            label(dd, (2, 0), "APPROVED SHEET  -  " + text, int(8 * k), fill=DIM, shadow=False)
            label(dd, (w + 6, 0), "EXPERIMENTAL MODEL 02", int(8 * k), fill=FG, shadow=False)
            tiles.append(t)
        blocks.append(tiles)
    W = max(sum(t.width for t in tiles) + gap * (len(tiles) - 1) for tiles in blocks) + 2 * pad
    H = head + sum(tiles[0].height for tiles in blocks) + gap * (len(blocks) - 1) + pad
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    label(d, (pad, int(10 * k)), "ASTRA R08 - EXPERIMENTAL MODEL 02  vs  THE APPROVED SHEET", int(13 * k))
    label(d, (pad + int(760 * k), int(14 * k)), "same framing, one studio rig turned with the camera", int(8 * k), fill=DIM, bold=False, shadow=False)
    y = head
    for tiles in blocks:
        x = pad + (W - 2 * pad - (sum(t.width for t in tiles) + gap * (len(tiles) - 1))) // 2
        for t in tiles:
            im.paste(t, (x, y))
            x += t.width + gap
        y += tiles[0].height + gap
    im.save(out)
    return im


def silhouette_sheet(rdir, out, k=2):
    sh = S.load_sheet()
    tiles, res = [], {}
    for n, text in (("front", "FRONT"), ("tq", "THREE-QUARTER"), ("side", "SIDE (EXACT)")):
        ref = S.panel(n, sh)
        mine = Image.open(os.path.join(rdir, n + ".png")).convert("RGB").resize(ref.size, Image.LANCZOS)
        rm = S.creature_mask(ref, label_box=(0, 0, 260, 40))
        mm = S.creature_mask(mine)
        raw = (rm & mm).sum() / max((rm | mm).sum(), 1)
        iou, placed, prm = fit_masks(rm, mm)
        res[n] = dict(as_framed=round(float(raw), 3), best_fit=round(float(iou), 3))
        a = np.asarray(ref).astype(np.float32) * 0.50
        a[mm & ~rm] = a[mm & ~rm] * 0.35 + np.array([30, 170, 80]) * 0.65
        a[rm & ~mm] = a[rm & ~mm] * 0.45 + np.array([215, 45, 45]) * 0.55
        e = (mm ^ np.roll(mm, 1, 0)) | (mm ^ np.roll(mm, 1, 1))
        a[e] = (150, 255, 180)
        t = Image.fromarray(a.astype(np.uint8)).resize((ref.width * k, ref.height * k), Image.NEAREST)
        dd = ImageDraw.Draw(t)
        label(dd, (10, ref.height * k - 26 * k), f"{text}: silhouette IoU {raw:.2f}", 9 * k)
        tiles.append(t)
    W = Image.new("RGB", (sum(t.width for t in tiles) + 8 * 2, tiles[0].height + 30 * k), BG)
    d = ImageDraw.Draw(W)
    label(d, (10, 6 * k), "MODEL OUTLINE (pale green) OVER THE APPROVED SHEET   -   red: sheet only, green: model only", 9 * k)
    x = 0
    for t in tiles:
        W.paste(t, (x, 30 * k))
        x += t.width + 8
    W.save(out)
    return res


if __name__ == "__main__":
    rdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(S.ROOT, "experimental_02", "renders")
    an = os.path.join(S.ROOT, "experimental_02", "analysis")
    res = silhouette_sheet(rdir, os.path.join(rdir, "silhouette_check.png"))
    json.dump(res, open(os.path.join(an, "silhouette_iou.json"), "w"), indent=1)
    print("silhouette IoU", res)
    facts_path = os.path.join(an, "facts.json")
    facts = json.load(open(facts_path)) if os.path.exists(facts_path) else dict(left=[], right=[])
    model_sheet(rdir, facts, os.path.join(rdir, "ASTRA_R08_EXP02_sheet.png"))
    versus_sheet(rdir, os.path.join(rdir, "ASTRA_R08_EXP02_vs_approved.png"))
    print("sheets written to", rdir)
