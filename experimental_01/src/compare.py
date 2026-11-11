"""Side-by-side comparison of renders with the approved sheet's panels.

    bvenv/bin/python experimental_01/src/compare.py renders_dir out.png [view ...]

Body views also get a silhouette overlay (sheet = red, model = green, both = yellow) and an IoU
after a best-fit shift and scale of the model picture onto the panel.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import sheet as S
import views


def fit_masks(ref, mod):
    """Scale + shift `mod` (bool) onto `ref` (bool) for the best IoU.  Returns (iou, placed mask, params)."""
    from scipy import ndimage as ndi
    H, W = ref.shape
    ys, xs = np.nonzero(mod)
    yr, xr = np.nonzero(ref)
    if len(ys) == 0:
        return 0.0, np.zeros_like(ref), (1, 0, 0)
    best = (-1, None, None)
    s0 = (yr.max() - yr.min()) / max(ys.max() - ys.min(), 1)
    for s in s0 * np.linspace(0.92, 1.08, 9):
        zm = ndi.zoom(mod.astype(np.float32), s, order=1) > 0.5
        zy, zx = np.nonzero(zm)
        if len(zy) == 0:
            continue
        for dy in (-6, -3, 0, 3, 6):
            oy = (yr.max() - zy.max()) + dy
            for dx in range(-14, 15, 2):
                ox = int(round(xr.mean() - zx.mean())) + dx
                canvas = np.zeros_like(ref)
                y0, x0 = max(oy, 0), max(ox, 0)
                sy, sx = y0 - oy, x0 - ox
                h = min(H - y0, zm.shape[0] - sy)
                w = min(W - x0, zm.shape[1] - sx)
                if h <= 0 or w <= 0:
                    continue
                canvas[y0:y0 + h, x0:x0 + w] = zm[sy:sy + h, sx:sx + w]
                iou = (canvas & ref).sum() / max((canvas | ref).sum(), 1)
                if iou > best[0]:
                    best = (iou, canvas, (s, ox, oy))
    return best


def main(rdir, out, names):
    sh = S.load_sheet()
    rows = []
    Ht = 420
    report = []
    for n in names:
        p = os.path.join(rdir, n + ".png")
        if not os.path.exists(p):
            continue
        mine = Image.open(p).convert("RGB")
        tiles = []
        pn = views.PANEL_OF.get(n)
        if pn:
            ref = S.panel(pn, sh)
            tiles.append(ref.resize((int(ref.width * Ht / ref.height), Ht), Image.LANCZOS))
        tiles.append(mine.resize((int(mine.width * Ht / mine.height), Ht), Image.LANCZOS))
        if pn in ("front", "tq", "side"):
            rm = S.creature_mask(ref, label_box=(0, 0, 260, 40))
            mm = S.creature_mask(mine.resize(ref.size, Image.LANCZOS))
            iou, placed, prm = fit_masks(rm, mm)
            ov = np.zeros(rm.shape + (3,), np.uint8) + 18
            ov[rm & ~placed] = (210, 50, 50)
            ov[placed & ~rm] = (40, 190, 80)
            ov[placed & rm] = (215, 200, 70)
            t = Image.fromarray(ov).resize((int(ref.width * Ht / ref.height), Ht), Image.NEAREST)
            ImageDraw.Draw(t).text((8, 8), f"IoU {iou:.3f}  scale {prm[0]:.3f}", fill=(255, 255, 255))
            tiles.append(t)
            report.append(f"{n}: silhouette IoU {iou:.3f} (scale {prm[0]:.3f}, shift {prm[1]},{prm[2]})")
        W = sum(t.width for t in tiles) + 8 * (len(tiles) - 1)
        row = Image.new("RGB", (W, Ht), (12, 12, 13))
        x = 0
        for t in tiles:
            row.paste(t, (x, 0))
            x += t.width + 8
        ImageDraw.Draw(row).text((6, Ht - 16), n, fill=(255, 255, 255))
        rows.append(row)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height for r in rows) + 8 * (len(rows) - 1)), (12, 12, 13))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 8
    sheet.save(out)
    for r in report:
        print(r)
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:] or ["front", "tq", "side", "head", "mouth", "jawside", "sideclose"])
