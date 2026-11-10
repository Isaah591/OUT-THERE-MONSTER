"""
V15 ("Experimental 11") anatomy check against the approved sheet. It opens a .blend (V15's, for the
meshes the lengthened teeth must stay clear of), solves the upper jaw edge, the jaw and both rows'
plans as build_v15.py does, lengthens the posterior teeth, and reports what v14_anatomy_check.py does -
the jaw's pose and sweep, the rim's centre line against the sheet's gum lines, the upper jaw's edge,
the brows and sockets, each lower tooth's root and tip in the front and side panels - and, for V15,
each lengthened tooth: its v14 and V15 length and where its tip now projects in the three views.

With renders it draws, as V14's check, the sheet's teeth (cyan upper, magenta lower), mouth outline
(yellow), the solved rim centre line (green) and the points it was fitted to (white) over them; and on a
second overlay per view the lengthened teeth: each one's v14 extent (white, over its V15 extent in
yellow: the yellow beyond the white is what V15 adds).

    python v15_anatomy_check.py <file.blend> [<out_prefix> front=<sheet_front.png> side=<sheet_side.png>
                                              34=<fit34.png>]                        (with `bpy`)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402,F401  (provides mathutils)
from mathutils import Vector  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import build_v7 as B7  # noqa: E402
import build_v15 as BV  # noqa: E402
import head_v15 as H  # noqa: E402

PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550), "side": (1017, 55, 1484, 550)}
CROPS = {"front": (205, 25, 330, 215, 5), "side": (70, 40, 215, 245, 4), "34": (140, 55, 262, 238, 5)}
# the three-quarter panel's upper teeth and mouth outline (read as the others; used only for the overlay)
SHEET34 = {"upper": [((163, 98), (161, 130)), ((169, 100), (168, 128)), ((175, 100), (176, 142)), ((183, 100), (182, 117)),
                     ((189, 100), (188, 158)), ((196, 98), (198, 140)), ((203, 96), (204, 115)), ((209, 94), (210, 138)),
                     ((216, 93), (217, 108)), ((223, 92), (222, 103)), ((229, 90), (229, 108))],
           "mouth": [(158, 97), (238, 92), (240, 110), (238, 150), (232, 180), (222, 198), (210, 205), (190, 205),
                     (178, 198), (172, 185), (165, 160), (160, 130), (158, 100)]}


def plan(path):
    """V15's teeth as build_v15.py plans them, from the meshes of the .blend at `path` (opened)."""
    import contextlib
    import io
    bpy.ops.wm.open_mainfile(filepath=path)
    F = H.Frame(Vector(B7.HEAD_POS), B7.HEAD_ROT, B7.HEAD_SCALE, 76.0, B7.JAW_BROKEN_ROLL_DEG)
    H.U = B7.HEAD_SCALE
    tissue_c = ["Mouth_Inner_Walls", "Mouth_Cheek_Flesh", "Jaw_Strands", "Mouth_Corner_Rims", "Torn_Flesh", "Palate",
                "Throat"]
    solids = {"up": {"c": [BV.bvh(n) for n in ["Cranium"] + tissue_c],
                     "j": [BV.bvh(n) for n in ("Jaw", "Gums_Lower", "Mouth_Floor")]},
              "lo": {"c": [BV.bvh(n) for n in ["Cranium", "Gums_Upper"] + tissue_c],
                     "j": [BV.bvh(n) for n in ("Jaw", "Mouth_Floor")]}}
    with contextlib.redirect_stdout(io.StringIO()):
        H.solve_upper_edge(F)
        H.solve_jaw(F)
        up, lo = H.plan_upper(F), H.plan_lower(F)
    grown = H.lengthen_posterior(F, up, lo, solids)
    return F, up, lo, grown


def front_map(F):
    vg = H.front_uv(F.hw((0.0, H.FRONT_UP, H.GUM_Z)))[1]
    k = (H._front_map(F, H.SHEET_FRONT_CHIN_V) - vg) / (H.SHEET_FRONT_CHIN_V - H.SHEET_FRONT_GUM_V)
    return vg, k


def report(F, up, lo, grown):
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
    v15_shapes(F)
    lengthened_report(F, up, lo, grown)
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


def v15_shapes(F):
    """The curvature (v14's, kept) and V15's brows, in the sheet's px: the tooth row's sweep in the side panel (how far its
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
    for (c, h, tilt, depth), (ov, bh, top_tilt), (ov4, bh4, top4), name in zip(H.SOCKETS, H.BROW, H.BROW_V14,
                                                                                ("right", "left")):
        drop = 2 * h[0] * (math.tan(math.radians(abs(tilt) + H.BROW_DROP)) - math.tan(math.radians(abs(tilt))))
        print("%s socket: inner corner %.1f px lower than the outer (tilt %+.0f deg), %.2f u deep; brow ledge %.2f u "
              "(%.1f cm; v14 %.1f cm) out over it, its top sloping %.0f deg down toward the nose on its inner half "
              "(v14: %.0f deg; its outer half v14's); the lip over the opening's inner top corner %.0f deg steeper "
              "than the socket's edge, %.1f px deep at the inner corner (front panel)"
              % (name, abs(2 * h[0] * math.sin(math.radians(tilt))) * H.U * H.FRONT_CAM[2], tilt, depth, ov,
                 ov * H.U * 100, ov4 * H.U * 100, abs(top_tilt), abs(top4), H.BROW_DROP,
                 drop * H.U * H.FRONT_CAM[2]))


def lengthened_report(F, up, lo, grown):
    """V15's lengthened teeth: v14 -> V15 length (head units; the row's v14 longest for scale) and the tip's
    move in each view (panel px, + = down)."""
    g = {id(t) for t in grown}
    for name, group, tf in (("upper", up, F.hw), ("lower", lo, F.jw)):
        rows = [(i, t) for i, t in enumerate(group) if id(t) in g]
        print("%s row: %d of %d lengthened (v14's longest %.2f u)" % (name, len(rows), len(group),
                                                                       max(t["L0"] for t in group)))
        for i, t in rows:
            L = (t["tip"] - t["root"]).length
            tip4 = t["root"] + t["dir0"] * t["L0"]
            moves = []
            for view, proj in (("front", H.front_uv), ("3/4", H.uv34), ("side", H.side_uv)):
                a, b = proj(tf(tip4)), proj(tf(t["tip"]))
                moves.append("%s %+.0f,%+.0f" % (view, b[0] - a[0], b[1] - a[1]))
            print("  %s%-2d %-6s %s%.2f -> %.2f u (goal %.2f)  tip moves: %s" % (
                name[0].upper(), i, t["src"], ("t %.2f " % t["t"]) if "t" in t else "", t["L0"], L, t["goal"],
                " | ".join(moves)))


def lengthened_overlay(F, up, lo, grown, view, render, out):
    proj = {"front": H.front_uv, "side": H.side_uv, "34": H.uv34}[view]
    b = PANELS[view]
    W, Hh = b[2] - b[0], b[3] - b[1]
    x0, y0, x1, y1, s = CROPS[view]
    im = Image.open(render).convert("RGB").resize((W, Hh), Image.LANCZOS).crop((x0, y0, x1, y1))
    im = im.resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    P = lambda p: ((p[0] - x0) * s, (p[1] - y0) * s)
    g = {id(t) for t in grown}
    for group, tf in ((up, F.hw), (lo, F.jw)):
        for t in group:
            if id(t) not in g:
                continue
            tip4 = t["root"] + t["dir0"] * t["L0"]
            r, a, q = P(proj(tf(t["root"]))), P(proj(tf(tip4))), P(proj(tf(t["tip"])))
            d.line([r, q], fill=(255, 220, 0), width=3)                 # V15's tooth (root -> tip) ...
            d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], fill=(255, 220, 0))
            d.line([r, a], fill=(255, 255, 255), width=3)               # ... over it, v14's
            d.ellipse([a[0] - 3, a[1] - 3, a[0] + 3, a[1] + 3], fill=(255, 255, 255))
    im.save(out)


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
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    F, up, lo, grown = plan(argv[0])
    report(F, up, lo, grown)
    if len(argv) > 2:
        prefix = argv[1]
        for arg in argv[2:]:
            view, path = arg.split("=")
            overlay(F, view, path, "%s_anatomy_%s.png" % (prefix, view))
            lengthened_overlay(F, up, lo, grown, view, path, "%s_lengthened_%s.png" % (prefix, view))
