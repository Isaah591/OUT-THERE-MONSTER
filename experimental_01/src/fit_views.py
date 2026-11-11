"""Silhouette check of the model against the sheet's three body panels, without rendering.

    bvenv/bin/python experimental_01/src/fit_views.py [out.png]

Projects the model with each view's camera, then reports the IoU with the panel's creature mask
both as framed and after a best-fit shift/scale (so framing and proportions can be told apart).
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import sheet as S, views, preview as PV
from compare import fit_masks


def model_items(out):
    items = []
    for name, (d, mat, sm) in out.items():
        if mat == "rust":
            continue                      # the under-surface carries the silhouette to within ~2 cm
        items.append(dict(V=d["V"], Q=d["Q"], T=d["T"]))
    return items


def check(out, names=("front", "tq", "side"), save=None, cams=None, verbose=True):
    sh = S.load_sheet()
    items = model_items(out)
    tiles, res = [], {}
    for n in names:
        ref = S.panel(n, sh)
        rm = S.creature_mask(ref, label_box=(0, 0, 260, 40))
        cam = (cams or views.VIEWS)[n]
        k = 2
        sil = PV.silhouette(items, cam, (ref.width * k, ref.height * k))
        sil = np.asarray(Image.fromarray((sil * 255).astype(np.uint8)).resize(ref.size, Image.BILINEAR)) > 127
        raw = (sil & rm).sum() / max((sil | rm).sum(), 1)
        iou, placed, prm = fit_masks(rm, sil)
        res[n] = dict(raw=raw, fit=iou, scale=prm[0], shift=(prm[1], prm[2]))
        if verbose:
            print(f"{n:<6} IoU as framed {raw:.3f}   best fit {iou:.3f}  (scale {prm[0]:.3f}, shift {prm[1]:+d},{prm[2]:+d} px)")
        ov = np.zeros(rm.shape + (3,), np.uint8) + 18
        ov[rm & ~sil] = (210, 50, 50)
        ov[sil & ~rm] = (40, 190, 80)
        ov[sil & rm] = (215, 200, 70)
        t = Image.fromarray(ov).resize((ref.width * 2, ref.height * 2), Image.NEAREST)
        ImageDraw.Draw(t).text((8, 8), f"{n}: IoU {raw:.3f} (fit {iou:.3f})", fill=(255, 255, 255))
        tiles.append(t)
    if save:
        W = Image.new("RGB", (sum(t.width for t in tiles), max(t.height for t in tiles)), (12, 12, 13))
        x = 0
        for t in tiles:
            W.paste(t, (x, 0))
            x += t.width
        W.save(save)
    return res


if __name__ == "__main__":
    from model import Model
    import body, head
    m = Model(8)
    body.build_body(m)
    head.build_head(m)
    out = m.generate(verbose=False)
    check(out, save=sys.argv[1] if len(sys.argv) > 1 else None)
