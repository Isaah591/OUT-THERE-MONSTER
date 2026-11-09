"""
V11 anatomy check against the approved sheet. It solves V11's jaw and tooth plan (as
build_v11.py does, without building meshes) and reports:

- the jaw's pose and asymmetric outline;
- every tooth's root and tip projected into the front panel (on the sheet's own mouth scale) and
  into the side panel, for comparison with the annotations in head_v11.SHEET.

With renders, it also draws the sheet's annotations over them: the teeth as root -> tip lines (cyan
upper, magenta lower), the front panel's mouth outline (yellow), and the side panel's jaw edges
(orange top, red underside).

    python v11_anatomy_check.py [<out_prefix> front=<sheet_front.png> side=<sheet_side.png> 34=<fit34.png>]
                                                   (with `bpy`, for mathutils)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (provides mathutils)
from mathutils import Vector  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import build_v7 as B7  # noqa: E402
import head_v11 as H  # noqa: E402

PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
CROPS = {"front": (205, 45, 330, 215, 5), "side": (70, 40, 215, 240, 4), "34": (140, 50, 260, 235, 5)}
# the three-quarter panel's annotations (read the same way; used only for the overlay)
SHEET34 = {"upper": [((163, 98), (161, 130)), ((169, 100), (168, 128)), ((175, 100), (176, 142)), ((183, 100), (182, 117)),
                     ((189, 100), (188, 158)), ((196, 98), (198, 140)), ((203, 96), (204, 115)), ((209, 94), (210, 138)),
                     ((216, 93), (217, 108)), ((223, 92), (222, 103)), ((229, 90), (229, 108))],
           "mouth": [(158, 97), (238, 92), (240, 110), (238, 150), (232, 180), (222, 198), (210, 205), (190, 205),
                     (178, 198), (172, 185), (165, 160), (160, 130), (158, 100)]}


def plan():
    F = H.Frame(Vector(B7.HEAD_POS), B7.HEAD_ROT, B7.HEAD_SCALE, 70.0, B7.JAW_BROKEN_ROLL_DEG)
    H.U = B7.HEAD_SCALE
    H.solve_jaw(F)
    up, lo = H.plan_teeth(F)
    vg = H.front_uv(F.hw((0.0, H.FRONT_UP, H.GUM_Z)))[1]
    vc = H.front_uv(F.jw((H.JAW["chin_x"], -H.JAW["L"], H.RIM_BOT)))[1]
    k = (vc - vg) / (H.SHEET_FRONT_CHIN_V - H.SHEET_FRONT_GUM_V)
    return F, up, lo, vg, k


def report(F, up, lo, vg, k):
    unmap = lambda v: H.SHEET_FRONT_GUM_V + (v - vg) / k
    print("jaw: open %.1f deg, length %.3f u, chin x %.3f u; front mouth scale %.3f (model gum v %.1f, chin v %.1f)"
          % (H.JAW["open"], H.JAW["L"], H.JAW["chin_x"], k, vg, vg + k * 97))
    print("inner rim, monster's left (+x):", [(round(y, 2), round(x, 2)) for y, x in H.JAW["left"]])
    print("inner rim, monster's right (-x):", [(round(y, 2), round(x, 2)) for y, x in H.JAW["right"]])
    for name, group, tf in (("upper", up, F.hw), ("lower", lo, F.jw)):
        print("%s teeth: %d" % (name, len(group)))
        for t in group:
            r, q = tf(t["root"]), tf(t["tip"])
            fr, fq, sr, sq = H.front_uv(r), H.front_uv(q), H.side_uv(r), H.side_uv(q)
            print("  %-5s length %.2f u, root %.3f u | front root (%.0f, %.0f) tip (%.0f, %.0f) | side root (%.0f, %.0f) "
                  "tip (%.0f, %.0f)" % (t["src"], t["L"], t["w"], fr[0], unmap(fr[1]), fq[0], unmap(fq[1]),
                                        sr[0], sr[1], sq[0], sq[1]))


def overlay(view, render, out, vg, k):
    b = PANELS[view]
    W, Hh = b[2] - b[0], b[3] - b[1]
    x0, y0, x1, y1, s = CROPS[view]
    im = Image.open(render).convert("RGB").resize((W, Hh), Image.LANCZOS).crop((x0, y0, x1, y1))
    im = im.resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    if view == "front":           # the sheet's mouth, mapped onto the model's mouth height
        mv = lambda v: v + (vg - 60.0) if v < 60.0 else vg + (v - 60.0) * k
        teeth = [("upper", H.SHEET["front_upper"]), ("lower", H.SHEET["front_lower"])]
        mouth = [H.SHEET["front_mouth_left"][0]] + H.SHEET["front_mouth_right"] + H.SHEET["front_mouth_left"][::-1]
    elif view == "side":
        mv = lambda v: v
        teeth = [("upper", H.SHEET["side_upper"]), ("lower", H.SHEET["side_lower"])]
        mouth = None
    else:
        mv = lambda v: v
        teeth = [("upper", SHEET34["upper"]), ("lower", H.SHEET["34_lower"])]
        mouth = SHEET34["mouth"]
    P = lambda p: ((p[0] - x0) * s, (mv(p[1]) - y0) * s)
    for kind, group in teeth:
        col = (0, 255, 255) if kind == "upper" else (255, 0, 255)
        for r, t in group:
            d.line([P(r), P(t)], fill=col, width=3)
            c = P(r)
            d.ellipse([c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4], outline=col, width=2)
    if mouth:
        d.line([P(p) for p in mouth] + [P(mouth[0])], fill=(255, 255, 0), width=2)
    im.save(out)


if __name__ == "__main__":
    F, up, lo, vg, k = plan()
    report(F, up, lo, vg, k)
    if len(sys.argv) > 2:
        prefix = sys.argv[1]
        for arg in sys.argv[2:]:
            view, path = arg.split("=")
            overlay(view, path, "%s_anatomy_%s.png" % (prefix, view), vg, k)
