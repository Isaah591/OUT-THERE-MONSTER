"""
Tooth coverage of the mouth opening in the front view, sheet vs model, with overlays.

    python measure_teeth_coverage.py <out_dir> <model_front.png> [polygon]

The mouth opening is a polygon read off zoomed landmark grids (upper gum line, mouth corners,
lower gum arc) for the sheet's front panel and for each version of the model's `oj_front`
render; inside it, pale yellow pixels count as teeth and very dark ones as cavity. Overlays:
<out_dir>/teeth_{sheet,model}.png (teeth in green, polygon in magenta).
Polygons: openjaw_v1 = first open-jaw build (57 deg jaw), openjaw_v2 = current (72 deg jaw).
"""
import sys
import numpy as np
from PIL import Image, ImageDraw

OUT, MODEL_FRONT = sys.argv[1], sys.argv[2]
POLY = sys.argv[3] if len(sys.argv) > 3 else "openjaw_v2"
REPO = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
SHEET_POLY = [(228, 57), (302, 57), (305, 80), (300, 110), (293, 135), (285, 148), (255, 151),
              (240, 140), (232, 110), (228, 80)]
MODEL_POLYS = {
    "openjaw_v1": [(480, 207), (652, 207), (655, 260), (645, 320), (628, 370), (600, 393), (530, 393),
                (505, 370), (488, 320), (478, 260)],
    "openjaw_v2": [(490, 207), (648, 207), (650, 260), (645, 320), (635, 360), (612, 385), (520, 385),
              (500, 360), (492, 320), (488, 260)],
}


def coverage(name, im, poly):
    a = np.asarray(im).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    tooth = (g > 0.72 * r) & (r > 90) & ((r - b) > 15)
    mpoly = Image.new("L", im.size, 0)
    ImageDraw.Draw(mpoly).polygon(poly, fill=255)
    inside = np.asarray(mpoly) > 0
    t = (tooth & inside).sum() / inside.sum()
    dark = ((0.3 * r + 0.59 * g + 0.11 * b) < 45) & inside & ~tooth
    ov = np.asarray(im).copy()
    ov[tooth & inside] = (0, 255, 0)
    o = Image.fromarray(ov)
    ImageDraw.Draw(o).line(poly + [poly[0]], fill=(255, 0, 255), width=1)
    o.save("%s/teeth_%s.png" % (OUT, name))
    ys = [p[1] for p in poly]
    print("%s: mouth opening %d px tall, area %d px^2; teeth cover %.0f%%, very dark cavity %.0f%%"
          % (name, max(ys) - min(ys), inside.sum(), 100 * t, 100 * dark.sum() / inside.sum()))


sheet = Image.open(REPO + "/references/r08_open_jaw_sheet.webp").convert("RGB").crop((0, 55, 490, 550))
coverage("sheet", sheet, SHEET_POLY)
coverage("model", Image.open(MODEL_FRONT).convert("RGB"), MODEL_POLYS[POLY])
