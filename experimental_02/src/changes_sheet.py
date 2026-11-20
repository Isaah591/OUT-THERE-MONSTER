"""Before / after sheet for the two corrections of Experimental Model 02 (right leg, skull).

    bvenv/bin/python experimental_02/src/changes_sheet.py

Model 01's pictures come from experimental_01/renders (the same cameras) and, for the extra skull
views that Model 01 was never rendered from, experimental_02/renders/model01_views (rendered from
experimental_01/model/astra_r08_exp01.blend with this model's render.py; see the README).
The hip crops are cut from the full-figure renders by projecting the same box of space through
each view's camera, so both models are cropped identically.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import views

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
M1 = os.path.join(REPO, "experimental_01", "renders")
M1X = os.path.join(ROOT, "renders", "model01_views")
M2 = os.path.join(ROOT, "renders")
BG = (13, 14, 15)
FG = (236, 236, 232)
DIM = (165, 167, 165)
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, bold=True):
    return ImageFont.truetype(FONT_B if bold else FONT_R, int(size))


def project(view, P, W, H):
    """Pixel position of world point P in a W x H render of `view` (pinhole camera, no roll)."""
    v = views.VIEWS[view]
    pos, tgt = np.asarray(v["pos"], float), np.asarray(v["target"], float)
    f = (tgt - pos) / np.linalg.norm(tgt - pos)
    r = np.cross(f, (0.0, 0.0, 1.0))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    d = np.asarray(P, float) - pos
    z = d @ f
    k = (W / 2) / ((v["width"] / 2) / v["dist"])
    return W / 2 + (d @ r) / z * k, H / 2 - (d @ u) / z * k


def crop_box(view, path, lo, hi, pad=0.04):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    pts = [project(view, (x, y, z), W, H) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    px, py = (x1 - x0) * pad, (y1 - y0) * pad
    return im.crop((int(max(0, x0 - px)), int(max(0, y0 - py)), int(min(W, x1 + px)), int(min(H, y1 + py))))


def label(d, xy, text, size, fill=FG, bold=True):
    d.text((xy[0] + 2, xy[1] + 2), text, font=font(size, bold), fill=(0, 0, 0))
    d.text(xy, text, font=font(size, bold), fill=fill)


def row(pairs, h):
    """[(model01 image, model02 image, caption)] -> list of tiles (each a labelled pair)."""
    tiles = []
    for (a, b, cap) in pairs:
        w = int(round(a.width / a.height * h))
        t = Image.new("RGB", (2 * w + 4, h + 24), BG)
        t.paste(a.resize((w, h), Image.LANCZOS), (0, 24))
        t.paste(b.resize((w, h), Image.LANCZOS), (w + 4, 24))
        d = ImageDraw.Draw(t)
        d.text((4, 3), "MODEL 01  -  " + cap, font=font(13, False), fill=DIM)
        d.text((w + 8, 3), "MODEL 02", font=font(13, True), fill=FG)
        tiles.append(t)
    return tiles


def text_block(width, lines, size=15):
    f = font(size, False)
    out = []
    for ln in lines:
        words, cur = ln.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if f.getlength(t) > width:
                out.append(cur)
                cur = w
            else:
                cur = t
        out.append(cur)
        out.append("")
    return out


def main():
    lo, hi = (-0.62, -0.75, 0.55), (0.72, 0.55, 1.78)       # the hips, thighs and knees
    hips = [(crop_box(v, os.path.join(M1, v + ".png"), lo, hi), crop_box(v, os.path.join(M2, v + ".png"), lo, hi), cap)
            for v, cap in (("front", "FRONT"), ("tq", "THREE-QUARTER"), ("side", "SIDE"))]
    skull = []
    for v, cap in (("hq_r", "FROM THE CREATURE'S RIGHT"), ("hq_l", "FROM ITS LEFT"), ("htop", "FROM ABOVE")):
        p1 = os.path.join(M1X, v + ".png")
        if os.path.exists(p1):
            skull.append((Image.open(p1).convert("RGB"), Image.open(os.path.join(M2, v + ".png")).convert("RGB"), cap))
    skull2 = [(Image.open(os.path.join(M1, v + ".png")).convert("RGB"), Image.open(os.path.join(M2, v + ".png")).convert("RGB"), cap)
              for v, cap in (("head", "HEAD CLOSE-UP"), ("sideclose", "SIDE-ANGLE CLOSE-UP"), ("mouthside", "EXACT SIDE"))]
    H1, H2 = 430, 360
    r1 = row(hips, H1)
    r2 = row(skull, H2) if skull else []
    r3 = row(skull2, H2)
    gap = 14
    W = max(sum(t.width for t in r) + gap * (len(r) - 1) for r in (r1, r2, r3) if r) + 2 * gap
    TW = W - 2 * gap
    t1 = text_block(TW, [
        "PRIORITY 1 - RIGHT LEG.  Model 01 put the creature's right hip 14.5 cm right of the centre line but 30 cm in "
        "front of the hip centre and 5 cm higher than the left one, on a small pelvis box - so the right thigh seemed to grow "
        "out of the groin.  Model 02 rebuilds the structure: the torso ends in a pelvis block 67 cm wide, turned with the "
        "stride; a hip block hangs under each half of it with the hip joint at its centre (22 cm either side of the pelvis "
        "centre, the right one 7 cm ahead of it and the left 7 cm behind with the stride, both at the same height); a small groin block sits between the thighs.  Each "
        "thigh now leaves the underside of its own hip block.  Knees, ankles and feet keep the stance fitted to the sheet "
        "(silhouette overlap 0.80 / 0.74 / 0.77 in front / three-quarter / side)."])
    t2 = text_block(TW, [
        "PRIORITY 2 - SKULL.  Model 01's face was a flat vertical mask (a 7 x 4 grid) with box-shaped brows on a ten-sided "
        "cranium.  Model 02 builds the head from ten horizontal contours, each a rounded outline seen from above, so the face "
        "wraps back into the temples and the forehead slopes up and back (at roughly 40 degrees) into a rounded crown.  On it: a brow "
        "ridge standing 3 cm proud over each socket and dropping toward the nose, a nasal ridge running down to the lip point, "
        "cheekbones, lumps and dents (no two quarters alike), and eleven thick armour slabs raised from the skull surface so "
        "they follow its curve.  The sockets are square windows through 4 cm of armour into black pockets about 9 cm deep.  The "
        "socket sizes, the uneven brows, the pupil positions, the lip line, the jaw rim and the 67 teeth carry over (the rear "
        "upper teeth sit a little further back, on the now-curved jaw edge)."])
    fh = 22
    H = 70 + len(t1) * fh + r1[0].height + 30 + len(t2) * fh + (r2[0].height + gap if r2 else 0) + r3[0].height + 40
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    label(d, (gap, 14), "ASTRA R08 - EXPERIMENTAL MODEL 01  ->  MODEL 02: THE TWO CORRECTIONS", 26)
    d.text((gap, 48), "same cameras, same studio; Model 01 on the left of each pair", font=font(14, False), fill=DIM)
    y = 80
    for ln in t1:
        d.text((gap, y), ln, font=font(15, False), fill=FG)
        y += fh
    x = gap
    for t in r1:
        im.paste(t, (x, y))
        x += t.width + gap
    y += r1[0].height + 30
    for ln in t2:
        d.text((gap, y), ln, font=font(15, False), fill=FG)
        y += fh
    for r in (r2, r3):
        if not r:
            continue
        x = gap + (TW - (sum(t.width for t in r) + gap * (len(r) - 1))) // 2
        for t in r:
            im.paste(t, (x, y))
            x += t.width + gap
        y += r[0].height + gap
    out = os.path.join(M2, "ASTRA_R08_EXP02_vs_EXP01.png")
    im.save(out)
    print("wrote", out, im.size)


if __name__ == "__main__":
    main()
