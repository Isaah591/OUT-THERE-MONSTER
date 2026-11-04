"""
Head-only comparison against the approved sheet in its three main views, with the cameras of the
v7/v8 renders held fixed (front and side: the blueprint's orthographic transforms; three-quarter:
v7's fitted FIT34 camera).

    python measure_head_v8.py <out_prefix> <file.blend> [<render_dir>]     (with `bpy`)

Prints, per view: overlap (IoU) of the head box, mean distance between the sheet's and the model's
top outline of the head (and on which side the model lies), and mean distance of the head's
left outline; writes 4x head overlays <prefix>_head_<view>.png (sheet outline yellow, model cyan,
sheet only red, model only blue). With <render_dir> (fit34.png and sheet_front.png rendered by
render_views.py at twice the panel resolution) it also locates the red pupils in the renders and
in the sheet and prints their offsets in panel pixels.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet_views as SV  # noqa: E402

REFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")
FRONT = (284.96, 462.72, 160.0)          # u0 (pelvis x = 0), v0, px/m
SIDE = (309.46, 466.26, 150.19)
CAM34 = [0.43434609482510533, 0.05584576896904435, 22.989318239549853, 252.17536195340818,
         -0.21544024294424785, -0.003560515032204359]
TGT34 = np.array([-0.764, -0.55, 1.45])
BOX = {"front": (200, 0, 335, 170), "side": (60, 20, 240, 245), "34": (130, 25, 290, 230)}
TOP = {"front": (214, 316), "side": (80, 214), "34": (150, 262)}
LEFT = {"front": (12, 60), "side": (60, 100), "34": (55, 100)}
PUPIL_BOX = {"34": (130, 30, 270, 110), "front": (210, 15, 320, 70)}        # panel px
SHEET_PUPILS = {"34": [(170.1, 81.7), (210.5, 76.0)], "front": [(238.6, 45.7), (282.3, 42.6)]}


def project(P, view, W, H):
    if view == "front":
        return FRONT[0] + FRONT[2] * P[:, 0], FRONT[1] - FRONT[2] * P[:, 2]
    if view == "side":
        return SIDE[0] + SIDE[2] * P[:, 1], SIDE[1] - SIDE[2] * P[:, 2]
    return SV.persp_uv(P, CAM34, W, H, TGT34)


def top_outline(m, u0, u1):
    return np.array([(np.flatnonzero(m[:, u])[0] if m[:, u].any() else np.nan) for u in range(u0, u1)], float)


def left_outline(m, v0, v1, u_max):
    return np.array([(np.flatnonzero(m[v, :u_max])[0] if m[v, :u_max].any() else np.nan) for v in range(v0, v1)], float)


def pupils(img2x, box):
    """Red points (pupils) in a 2x image within a panel-px box -> centroids in panel px."""
    a = np.asarray(img2x.convert("RGB")).astype(float)
    x0, y0, x1, y1 = (2 * c for c in box)
    sub = a[y0:y1, x0:x1]
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    lab, n = ndi.label((r > 100) & (r > 2.2 * g) & (r > 2.2 * b))
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        out.append(((xs.mean() + x0) / 2, (ys.mean() + y0) / 2, len(ys)))
    return out


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    prefix, blend = argv[0], argv[1]
    renders = argv[2] if len(argv) > 2 else None
    masks = SV.sheet_masks(REFS)
    P = SV.model_points(blend)
    for view in ("front", "side", "34"):
        ref, panel = masks[view]
        H, W = ref.shape
        mm = SV.splat(*project(P, view, W, H), (H, W))
        x0, y0, x1, y1 = BOX[view]
        dt = top_outline(mm, *TOP[view]) - top_outline(ref, *TOP[view])
        dl = left_outline(mm, *LEFT[view], x1) - left_outline(ref, *LEFT[view], x1)
        print("%-5s head IoU %.3f | top outline %.1f px (model %s) | left outline %.1f px"
              % (view, SV.iou(mm[y0:y1, x0:x1], ref[y0:y1, x0:x1]), np.nanmean(np.abs(dt)),
                 "higher" if np.nanmean(dt) < 0 else "lower", np.nanmean(np.abs(dl))))
        pr, rr, mr = (a[y0:y1, x0:x1] for a in (panel.astype(float), ref, mm))
        ov = pr * 0.55
        ov[rr & ~mr] = ov[rr & ~mr] * 0.5 + np.array([255, 60, 40]) * 0.5
        ov[mr & ~rr] = ov[mr & ~rr] * 0.5 + np.array([40, 120, 255]) * 0.5
        ov[rr & ~ndi.binary_erosion(rr)] = (255, 255, 0)
        ov[mr & ~ndi.binary_erosion(mr)] = (0, 255, 255)
        Image.fromarray(ov.astype(np.uint8)).resize((ov.shape[1] * 4, ov.shape[0] * 4), Image.NEAREST).save(
            "%s_head_%s.png" % (prefix, view))
    if renders:
        # the sheet's pupils (measure_ref34_landmarks.py and the front panel, panel px); the model's are
        # the size-weighted centroid of the red points rendered within 16 px of each
        for view, fname in (("34", "fit34.png"), ("front", "sheet_front.png")):
            pm = pupils(Image.open(os.path.join(renders, fname)), PUPIL_BOX[view])
            line = "%-5s pupils" % view
            for sx, sy in SHEET_PUPILS[view]:
                near = [p for p in pm if (p[0] - sx) ** 2 + (p[1] - sy) ** 2 < 16 ** 2]
                if not near:
                    line += " | sheet (%.0f, %.0f): no pupil within 16 px" % (sx, sy)
                    continue
                w = np.array([p[2] for p in near], float)
                mx = float(np.dot(w, [p[0] for p in near]) / w.sum())
                my = float(np.dot(w, [p[1] for p in near]) / w.sum())
                line += " | sheet (%.0f, %.0f) model (%.0f, %.0f) d (%+.0f, %+.0f)" % (sx, sy, mx, my, mx - sx, my - sy)
            print(line)
