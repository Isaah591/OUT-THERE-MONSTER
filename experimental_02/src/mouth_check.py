"""How full of teeth is the mouth?  (The brief: the teeth occupy almost the whole opening, with
very little uninterrupted dark space between the upper and lower rows.)

    bvenv/bin/python experimental_02/src/mouth_check.py renders_dir [out.png]

For each head view the mouth opening (upper lip line + lower jaw rim, projected with that view's
camera) is cut out of the render and its pixels are sorted into teeth / gum and tissue / dark.
The same sort is run on the sheet's head close-up and front view inside outlines read off the
sheet, for comparison.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import sheet as S, views, preview as PV, head


def classes(rgb):
    a = np.asarray(rgb).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.30 * r + 0.59 * g + 0.11 * b
    tooth = (g > 0.56 * r) & (b < 0.80 * g) & (lum > 88) & (r > 115)
    red = (r > 1.75 * g) & (r > 38) & ~tooth
    dark = (lum < 30) & ~tooth & ~red
    return tooth, red, dark


def opening_polygon(view):
    """Mouth opening in picture coordinates for one of our views."""
    cam = views.VIEWS[view]
    w, h = cam["size"]
    xs = np.linspace(-0.250, 0.250, 21)
    upper = [head.Hw(x, head.mask_b(x, head.lip(x)) + 0.02, head.lip(x)) for x in xs]
    rim = [head.Hw(*p) for p in head.RIM]
    az = cam.get("az", 0.0)
    if az > 50:      # side-on: front of the upper jaw, back along the near side, down the near arm of the rim to the chin
        near = [head.Hw(head.jaw_half_width(b), b, 0.0) for b in (0.12, 0.22, 0.32, 0.42)]
        poly = [upper[10]] + near + rim[::-1][:len(rim) // 2 + 1] + [head.Hw(0.0, 0.0, -0.35)]
    else:
        poly = upper + rim[::-1]
    xy, z = PV.project(np.array(poly), cam, (w, h))
    return xy, (w, h)


REF_OUTLINES = {   # mouth opening outlines read off the sheet (panel pixels)
    "head": [(104, 125), (140, 140), (160, 144), (175, 135), (212, 118), (250, 110), (282, 105), (295, 150), (310, 200), (308, 238),
             (295, 275), (270, 308), (225, 333), (170, 335), (160, 275), (130, 225), (110, 175)],
    "front_head": [(227, 110), (238, 113), (250, 117), (256, 119), (267, 114), (287, 110), (300, 108), (300, 140), (299, 172), (295, 185),
                   (287, 207), (267, 212), (249, 206), (241, 185), (233, 155), (230, 135)],
}


def measure(img, poly, size):
    im = img.convert("RGB").resize(size, Image.LANCZOS)
    mk = Image.new("L", size, 0)
    ImageDraw.Draw(mk).polygon([tuple(p) for p in poly], fill=255)
    m = np.asarray(mk) > 0
    tooth, red, dark = classes(im)
    n = max(m.sum(), 1)
    lab, k = ndi.label(dark & m)
    big = max(ndi.sum(dark & m, lab, range(1, k + 1))) if k else 0
    return dict(teeth=(tooth & m).sum() / n, tissue=(red & m).sum() / n, dark=(dark & m).sum() / n, largest_dark=big / n), m, (tooth, red, dark)


if __name__ == "__main__":
    rdir = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    sh = S.load_sheet()
    rows = []
    print(f"{'picture':<26}{'teeth':>8}{'tissue':>8}{'dark':>8}{'largest dark patch':>20}")
    refs = {"head": S.panel("head", sh), "front_head": S.panel("front", sh)}
    tiles = []
    for name, poly in REF_OUTLINES.items():
        im = refs[name]
        r, m, cl = measure(im, poly, im.size)
        print(f"{'sheet: ' + name:<26}{r['teeth']:>8.1%}{r['tissue']:>8.1%}{r['dark']:>8.1%}{r['largest_dark']:>20.1%}")
        tiles.append((im, poly, "sheet " + name))
    for v in ("head", "mouth", "front", "tq", "hfront", "mouthside"):
        p = os.path.join(rdir, v + ".png")
        if not os.path.exists(p):
            continue
        im = Image.open(p)
        poly, size = opening_polygon(v)
        k = im.width / size[0]
        r, m, cl = measure(im, poly * k, im.size)
        print(f"{'model: ' + v:<26}{r['teeth']:>8.1%}{r['tissue']:>8.1%}{r['dark']:>8.1%}{r['largest_dark']:>20.1%}")
        tiles.append((im.convert("RGB"), poly * k, "model " + v))
    if out:
        H = 360
        ims = []
        for im, poly, label in tiles:
            im = im.copy()
            d = ImageDraw.Draw(im)
            pts = [tuple(p) for p in poly]
            d.line(pts + [pts[0]], fill=(80, 255, 140), width=max(1, im.width // 300))
            im = im.resize((int(im.width * H / im.height), H), Image.LANCZOS)
            ImageDraw.Draw(im).text((6, 6), label, fill=(255, 255, 255))
            ims.append(im)
        W = Image.new("RGB", (sum(i.width for i in ims) + 6 * len(ims), H), (12, 12, 13))
        x = 0
        for i in ims:
            W.paste(i, (x, 0)); x += i.width + 6
        W.save(out)
