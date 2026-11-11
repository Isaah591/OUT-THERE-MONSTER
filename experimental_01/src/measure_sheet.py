"""Independent measurements of the approved sheet's three body views.

Run: bvenv/bin/python experimental_01/src/measure_sheet.py
Writes mask overlays to experimental_01/analysis/ and prints row-by-row silhouette extents.
"""
import os, sys, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet as S

OUT = os.path.join(S.ROOT, "experimental_01", "analysis")
os.makedirs(OUT, exist_ok=True)
sh = S.load_sheet()
res = {}
for name in ("front", "tq", "side"):
    im = S.panel(name, sh)
    m = S.creature_mask(im, label_box=(0, 0, 260, 40))
    ys, xs = np.nonzero(m)
    box = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    res[name] = {"box": box, "area": int(m.sum())}
    ov = np.asarray(im).copy()
    edge = m ^ np.roll(m, 1, 0) | m ^ np.roll(m, 1, 1)
    ov[edge] = (0, 255, 120)
    Image.fromarray(ov).resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join(OUT, f"mask_{name}.png"))
    Image.fromarray((m * 255).astype(np.uint8)).save(os.path.join(OUT, f"sil_{name}.png"))
    print(name, "bbox", box, "height px", box[3] - box[1], "width px", box[2] - box[0])
    # horizontal extent of the silhouette every 5 % of the height
    H = box[3] - box[1]
    for f in np.linspace(0, 1, 21):
        y = int(round(box[1] + f * H)); y = min(y, m.shape[0] - 1)
        row = np.nonzero(m[y])[0]
        if len(row) == 0:
            continue
        runs = np.split(row, np.nonzero(np.diff(row) > 2)[0] + 1)
        print(f"   {f:4.2f}  y={y:3d}  " + "  ".join(f"[{r[0]}-{r[-1]}]" for r in runs if len(r) > 2))
json.dump(res, open(os.path.join(OUT, "sheet_boxes.json"), "w"), indent=1)
