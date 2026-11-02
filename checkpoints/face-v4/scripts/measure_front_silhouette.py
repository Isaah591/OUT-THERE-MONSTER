"""
Front-view silhouette measurements against the ASTRA R08 - MORE OPEN JAW sheet, with overlays.

    python measure_front_silhouette.py <out_dir> [model_front.png]

Masks the warm (rust / tissue / teeth) pixels against the neutral studio, closes cracks, fills
holes, opens away thin rods and spikes, then measures run widths in fixed bands: skull at eye
level, torso below the mouth (rows clear of the arms), long forearm (corrected for its slope).
The bands are set for the sheet's front panel and for the `oj_front` camera; the overlays
(<out_dir>/{sheet,model}_overlay.png) show exactly where every width was taken.
"""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

OUT = sys.argv[1]
REPO = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def body_mask(im, close_r, open_r):
    a = np.asarray(im.convert("RGB")).astype(int)
    m = (a[..., 0] - a[..., 2]) > 12                     # warm rust/tissue/teeth vs neutral grey studio
    m = ndi.binary_closing(m, structure=disk(close_r))   # bridge dark cracks
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    m = lab == (1 + int(np.argmax(ndi.sum(m, lab, range(1, n + 1)))))
    return ndi.binary_opening(m, structure=disk(open_r))   # drop thin rods / spikes


def runs(row):
    d = np.diff(np.concatenate([[0], row.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1) - 1))


def band(m, y0, y1, pick):
    segs = []
    for y in range(y0, y1):
        rs = runs(m[y])
        if rs:
            l, r = pick(rs)
            segs.append((y, l, r))
    return segs


def near(x):
    return lambda rs: min(rs, key=lambda s: 0 if s[0] <= x <= s[1] else min(abs(s[0] - x), abs(s[1] - x)))


def widest_left(xmax):
    return lambda rs: max([s for s in rs if (s[0] + s[1]) / 2 < xmax] or rs, key=lambda s: s[1] - s[0])


def measure(name, im, close_r, open_r, bands):
    m = body_mask(im, close_r, open_r)
    ov = Image.blend(im.convert("RGB"), Image.fromarray((m * 255).astype(np.uint8)).convert("RGB"), 0.25)
    d = ImageDraw.Draw(ov)
    res = {}
    cols = {"skull": (0, 255, 255), "torso": (255, 255, 0), "arm": (255, 0, 255)}
    for key, (y0, y1, pick) in bands.items():
        segs = band(m, y0, y1, pick)
        w = np.array([r - l + 1 for _, l, r in segs], float)
        c = np.array([(l + r) / 2 for _, l, r in segs], float)
        ys = np.array([y for y, _, _ in segs], float)
        slope = np.polyfit(ys, c, 1)[0] if len(segs) > 5 else 0.0
        perp = np.median(w) * np.cos(np.arctan(slope))          # thickness across an inclined limb
        res[key] = (np.median(w), perp, slope)
        print("  %s %s rows %d-%d: widths p10/p50/p90 = %.0f / %.0f / %.0f px"
              % (name, key, y0, y1, np.percentile(w, 10), np.median(w), np.percentile(w, 90)))
        for y, l, r in segs[::3]:
            d.line((l, y, r, y), fill=cols[key], width=1)
    ov.save("%s/%s_overlay.png" % (OUT, name))
    sk, to, ar = res["skull"][0], res["torso"][0], res["arm"][1]
    print("%s: skull %.0f px, torso %.0f px, long forearm %.0f px across (slope %.2f) | skull/torso %.2f, arm/torso %.2f, arm/skull %.2f"
          % (name, sk, to, ar, res["arm"][2], sk / to, ar / to, ar / sk))


sheet = Image.open(REPO + "/references/r08_open_jaw_sheet.webp").convert("RGB").crop((0, 55, 490, 550))
model = Image.open(sys.argv[2] if len(sys.argv) > 2 else REPO + "/model/renders_openjaw/oj_front.png").convert("RGB")
measure("sheet", sheet, 3, 4, {"skull": (28, 46, near(265)), "torso": (186, 240, near(280)),
                               "arm": (300, 400, widest_left(170))})
measure("model", model, 5, 8, {"skull": (140, 182, near(555)), "torso": (420, 540, near(570)),
                               "arm": (650, 850, widest_left(330))})
for name, box in (("sheet", (180, 0, 380, 260)), ("model", (380, 60, 780, 560))):
    im = Image.open("%s/%s_overlay.png" % (OUT, name))
    c = im.crop(box)
    c.resize((c.width * 2, c.height * 2), Image.NEAREST).save("%s/%s_zoom.png" % (OUT, name))
