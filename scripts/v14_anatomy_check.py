"""
V14 ("Experimental 10") anatomy check against the approved sheet. It solves V14's upper jaw edge, jaw
and lower-tooth plan (as build_v14.py does, without building meshes) and reports the jaw's pose and
sweep, the rim's centre line (where the lower teeth stand) against the sheet's lower gum line in the
front and three-quarter panels, the upper jaw's edge against the sheet's upper roots, the brows and
sockets, and each lower tooth's root and tip in the front and side panels.

With renders, it draws over them: the sheet's teeth as root -> tip lines (cyan upper, magenta lower),
the sheet's mouth outline (yellow), the solved rim centre line (green) and the sheet points it was
fitted to (white). The front and three-quarter panels draw the mouth shorter than the side panel, so
their heights in the mouth are mapped onto the model's mouth (gum line to chin), as the build does.

    python v14_anatomy_check.py [<out_prefix> front=<sheet_front.png> side=<sheet_side.png> 34=<fit34.png>]
                                                   (with `bpy`, for mathutils)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (provides mathutils)
from mathutils import Vector  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import build_v7 as B7  # noqa: E402
import head_v14 as H  # noqa: E402

PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
CROPS = {"front": (205, 25, 330, 215, 5), "side": (70, 40, 215, 245, 4), "34": (140, 55, 262, 238, 5)}
# the three-quarter panel's upper teeth and mouth outline (read as the others; used only for the overlay)
SHEET34 = {"upper": [((163, 98), (161, 130)), ((169, 100), (168, 128)), ((175, 100), (176, 142)), ((183, 100), (182, 117)),
                     ((189, 100), (188, 158)), ((196, 98), (198, 140)), ((203, 96), (204, 115)), ((209, 94), (210, 138)),
                     ((216, 93), (217, 108)), ((223, 92), (222, 103)), ((229, 90), (229, 108))],
           "mouth": [(158, 97), (238, 92), (240, 110), (238, 150), (232, 180), (222, 198), (210, 205), (190, 205),
                     (178, 198), (172, 185), (165, 160), (160, 130), (158, 100)]}


def plan():
    F = H.Frame(Vector(B7.HEAD_POS), B7.HEAD_ROT, B7.HEAD_SCALE, 76.0, B7.JAW_BROKEN_ROLL_DEG)
    H.U = B7.HEAD_SCALE
    H.solve_upper_edge(F)
    H.solve_jaw(F)
    lo = H.plan_lower(F)
    return F, lo


def front_map(F):
    vg = H.front_uv(F.hw((0.0, H.FRONT_UP, H.GUM_Z)))[1]
    k = (H._front_map(F, H.SHEET_FRONT_CHIN_V) - vg) / (H.SHEET_FRONT_CHIN_V - H.SHEET_FRONT_GUM_V)
    return vg, k


def report(F, lo):
    vg, k = front_map(F)
    unmap = lambda v: H.SHEET_FRONT_GUM_V + (v - vg) / k
    print("jaw: open %.1f deg, length %.3f u (tooth row %.3f), chin x %.3f u; front mouth scale %.3f (model gum v %.1f, "
          "chin v %.1f; sheet 60, 157)" % (H.JAW["open"], H.JAW["L"], H.JAW["L_top"], H.JAW["chin_x"], k, vg, vg + k * 97))
    gum = np.mean([H.side_uv(F.hw((x,) + H.gum_front(x)))[1] for x in np.linspace(H.UP_RIGHT_X, H.UP_LEFT_X, 9)])
    row = H.side_uv(F.jw((H.JAW["chin_x"], -H.JAW["L_top"], float(H._top(-H.JAW["L_top"])))))
    sheet_gum = np.mean([rv for (ru, rv), _ in H.SHEET["side_upper"] if ru < 109])
    print("side view: the jaw at the side panel's own height (the upper gum of v11's skull, kept, is %.1f px higher than "
          "the panel's); gape, upper gum -> end of the lower tooth row: %.0f px (sheet: %.0f)"
          % (-H.JAW["gum_offset"], row[1] - gum, H.SHEET["side_jaw"]["roots"][-1][1] - sheet_gum))
    # the rim's centre line against the sheet points it was fitted to, in each panel's px
    P = H.jaw_path()
    for name, proj, src in (("front", H.front_uv, ("front_line", "front_root")), ("3/4", H.uv34, ("34_root",))):
        line = np.array([proj(F.jw((x, y, float(H._top(y))))) for x, y, _ in
                         [(*H._path_at(P, t)[:2], 0) for t in np.linspace(0.0, 1.0, 400)]])
        d = []
        for x, y, s in H.JAW["samples"]:
            if s in src:
                q = proj(F.jw((x, y, float(H._top(y)))))
                d.append(float(np.min(np.hypot(line[:, 0] - q[0], line[:, 1] - q[1]))))
        print("rim centre line vs the sheet's %s gum line: mean %.1f px, max %.1f px (%d points)"
              % (name, np.mean(d), np.max(d), len(d)))
    teeth_vs_panels(F, lo)
    v14_shapes(F)
    print("lower teeth: %d" % len(lo))
    for t in lo:
        r, q = F.jw(t["root"]), F.jw(t["tip"])
        fr, fq, sr, sq = H.front_uv(r), H.front_uv(q), H.side_uv(r), H.side_uv(q)
        print("  %-5s length %.2f u, root %.3f u | front (sheet scale) root (%.0f, %.0f) tip (%.0f, %.0f) | side root "
              "(%.0f, %.0f) tip (%.0f, %.0f)" % (t["src"], t["L"], t["w"], fr[0], unmap(fr[1]), fq[0], unmap(fq[1]),
                                                 sr[0], sr[1], sq[0], sq[1]))


def teeth_vs_panels(F, lo):
    """Each of the sheet's lower teeth in the side and three-quarter panels against the model tooth whose
    root projects nearest to it: root and tip distance (px) and the lean in the image (deg, + = the
    model's leans further left/forward)."""
    import math
    out = {}
    front = [(r, t) for r, t, _ in H.SHEET["front_lower"]]
    for name, proj, sheet, mv in (("front", H.front_uv, front, lambda v: H._front_map(F, v)),
                                  ("side", H.side_uv, H.SHEET["side_lower"], lambda v: v),
                                  ("3/4", H.uv34, H.SHEET["34_lower"], lambda v: H._map34(F, v))):
        mr = [proj(F.jw(t["root"])) for t in lo]
        mt = [proj(F.jw(t["tip"])) for t in lo]
        dr, dt, da = [], [], []
        for (ru, rv), (tu, tv) in sheet:
            r = (ru, mv(rv))
            q = (tu, mv(tv))
            i = int(np.argmin([math.hypot(a[0] - r[0], a[1] - r[1]) for a in mr]))
            dr.append(math.hypot(mr[i][0] - r[0], mr[i][1] - r[1]))
            dt.append(math.hypot(mt[i][0] - q[0], mt[i][1] - q[1]))
            a_s = math.degrees(math.atan2(q[0] - r[0], r[1] - q[1]))
            a_m = math.degrees(math.atan2(mt[i][0] - mr[i][0], mr[i][1] - mt[i][1]))
            da.append(a_s - a_m)
        print("lower teeth vs the %s panel (%d): root %.1f px, tip %.1f px, lean %+.1f deg (mean), |lean| %.1f deg"
              % (name, len(sheet), np.mean(dr), np.mean(dt), np.mean(da), np.mean(np.abs(da))))
        out[name] = (np.mean(dr), np.mean(dt), np.mean(da), np.mean(np.abs(da)))
    return out


def v14_shapes(F):
    """V14's curvature and brows, in the sheet's px: the tooth row's sweep in the side panel (how far its
    middle stands back from the straight line between its ends, and how far the chin's end curls
    forward of it), the upper jaw's edge across the front panel against the sheet's upper roots, and the
    sockets' and brows' slopes."""
    import math
    ys = np.linspace(-H.JAW_ROW0, -H.JAW["L_top"], 60)
    x = 0.25
    row = np.array([H.side_uv(F.jw((x, y, float(H._top(y))))) for y in ys])
    flat = np.array([H.side_uv(F.jw((x, y, float(H.JAW["top"])))) for y in ys])
    a, b = row[0], row[-1]
    d = (row - a) @ np.array([-(b - a)[1], (b - a)[0]]) / np.linalg.norm(b - a)
    print("side: the tooth row sweeps back by up to %.1f px from the straight line between its ends (v13's was "
          "straight: %.1f px) and curls %.1f px forward at the chin's end"
          % (abs(d.min()), 0.0, np.max(np.abs(row[-10:, 0] - flat[-10:, 0]))))
    xs = np.linspace(H.UP_RIGHT_X, H.UP_LEFT_X, 80)
    vv = np.array([H.front_uv(F.hw((x_, *H.gum_front(x_))))[1] for x_ in xs])
    sheet = [rv for (ru, rv), _, _ in H.SHEET["front_upper"]]
    print("front: the upper jaw's edge varies by %.1f px across the mouth (v13: a level cut, the gum's 1.9 px "
          "wobble); the sheet's upper roots by %.1f px" % (vv.max() - vv.min(), max(sheet) - min(sheet)))
    for (c, h, tilt, depth), (ov, bh, top_tilt), name in zip(H.SOCKETS, H.BROW, ("right", "left")):
        print("%s socket: inner corner %.1f px lower than the outer (tilt %+.0f deg), %.2f u deep; brow ledge %.2f u "
              "(%.1f cm) out over it, its top sloping %.0f deg down toward the nose"
              % (name, abs(2 * h[0] * math.sin(math.radians(tilt))) * H.U * H.FRONT_CAM[2], tilt, depth, ov,
                 ov * H.U * 100, abs(top_tilt)))


def overlay(F, view, render, out):
    b = PANELS[view]
    W, Hh = b[2] - b[0], b[3] - b[1]
    x0, y0, x1, y1, s = CROPS[view]
    im = Image.open(render).convert("RGB").resize((W, Hh), Image.LANCZOS).crop((x0, y0, x1, y1))
    im = im.resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    vg, k = front_map(F)
    if view == "front":           # the sheet's mouth, mapped onto the model's mouth height
        mv = lambda v: v + (vg - 60.0) if v < 60.0 else vg + (v - 60.0) * k
        teeth = [("upper", H.SHEET["front_upper"] + H.SHEET["front_upper_behind"]), ("lower", H.SHEET["front_lower"])]
        mouth = [H.SHEET["front_mouth_left"][0]] + H.SHEET["front_mouth_right"] + H.SHEET["front_mouth_left"][::-1]
        proj, src = H.front_uv, ("front_line", "front_root")
    elif view == "side":
        mv = lambda v: v
        teeth = [("upper", H.SHEET["side_upper"]), ("lower", H.SHEET["side_lower"])]
        mouth, proj, src = None, H.side_uv, ()
    else:
        mv = lambda v: v if v < H.SHEET_34_GUM_V else H._map34(F, v)
        teeth = [("upper", SHEET34["upper"]), ("lower", H.SHEET["34_lower"])]
        mouth, proj, src = SHEET34["mouth"], H.uv34, ("34_root",)
    Pp = lambda p: ((p[0] - x0) * s, (mv(p[1]) - y0) * s)
    Pm = lambda p: ((p[0] - x0) * s, (p[1] - y0) * s)
    for kind, group in teeth:
        col = (0, 255, 255) if kind == "upper" else (255, 0, 255)
        for r, t, *_ in group:
            d.line([Pp(r), Pp(t)], fill=col, width=3)
            c = Pp(r)
            d.ellipse([c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4], outline=col, width=2)
    if mouth:
        d.line([Pp(p) for p in mouth] + [Pp(mouth[0])], fill=(255, 255, 0), width=2)
    P = H.jaw_path()
    line = [Pm(proj(F.jw((x, y, float(H._top(y)))))) for x, y, _ in P]
    d.line(line, fill=(0, 255, 0), width=3)
    for x, y, sname in H.JAW["samples"]:
        if sname in src:
            c = Pm(proj(F.jw((x, y, float(H._top(y))))))
            d.ellipse([c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3], fill=(255, 255, 255))
    im.save(out)


if __name__ == "__main__":
    F, lo = plan()
    report(F, lo)
    if len(sys.argv) > 2:
        prefix = sys.argv[1]
        for arg in sys.argv[2:]:
            view, path = arg.split("=")
            overlay(F, view, path, "%s_anatomy_%s.png" % (prefix, view))
