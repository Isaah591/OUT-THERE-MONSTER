"""
The approved sheet's three main views as blueprints: figure silhouettes of the FRONT, SIDE (EXACT)
and THREE-QUARTER panels, and cameras that map a model into each panel's pixels.

    python sheet_views.py <references_dir> <out_prefix> <file.blend> [...]      (with `bpy`)

Front and side are treated as orthographic views (front: looking along +Y, the monster's right on
the left; side: from +X, the monster facing left); each gets a scale and an offset fitted to the
model (silhouette overlap, Nelder-Mead), so only the shapes are compared, not the framing. The
three-quarter view uses a perspective camera fitted the same way (azimuth, elevation, distance,
focal length, lens shift; several starts from 46 mm to a near-orthographic 250 mm), printed as a
FIT34 string that render_views.py's `fit34` view accepts. Model silhouettes are the projected
vertices plus samples on large triangles (thin sheets count). Prints the overlap (IoU) per view and
per region and writes outline overlays <out_prefix>_<name>_<view>.png (sheet only red, model only
blue).
"""
import math
import os
import sys

import bpy
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import minimize

PANELS = {"front": (0, 55, 490, 550), "side": (1017, 55, 1484, 550), "34": (500, 55, 1008, 550)}


TITLES = {"front": (150, 30), "side": (200, 30), "34": (240, 28)}   # panel titles (width, height) at the top left


def segment(a, view):
    """Figure vs painted backdrop (as silhouette_ref34.py), floor excluded; enclosed holes are
    filled unless they show the backdrop (warm or clearly off-backdrop holes are the figure)."""
    a = a.astype(float)
    H, W, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a.mean(2)
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1)
    bg = np.zeros_like(a)
    edge_cols = np.r_[0:8, W - 50:W]
    for y in range(H):
        bg[y] = np.median(a[y, edge_cols], axis=0)
    diff = np.abs(a - bg).sum(2)
    fg = ((r - b > 9) & (r > 30)) | ((r - b > 5) & (r - g > 2) & (lum < 60)) | ((diff > 45) & (sat > 0.18))
    tw, th = TITLES[view]
    fg[:th, :tw] = False                                                # panel title (not the head)
    fg = ndi.binary_opening(fg, structure=np.ones((2, 2)))
    fg = ndi.binary_closing(fg, structure=np.ones((5, 5)), iterations=2)
    holes, nh = ndi.label(ndi.binary_fill_holes(fg) & ~fg)
    for i in range(1, nh + 1):                    # fill enclosed holes, except backdrop seen through the
        h = holes == i                            # figure (the gap between the legs in the side view, under
        if np.median((r - b)[h]) > 4 or np.median(diff[h]) > 35:      # an armpit, between the teeth)
            fg |= h
    lab, n = ndi.label(fg)
    keep = lab == (1 + int(np.argmax(ndi.sum(fg, lab, range(1, n + 1)))))
    return ndi.binary_opening(keep, structure=np.ones((3, 3)))


def sheet_masks(refs):
    sheet = Image.open(os.path.join(refs, "r08_open_jaw_sheet_v2.webp")).convert("RGB")
    out = {}
    for k, box in PANELS.items():
        a = np.asarray(sheet.crop(box))
        out[k] = (segment(a, k), a)
    return out


def model_points(blend, step=1, spacing=0.006):
    """World-space points covering every mesh of the build (studio objects excluded): the vertices
    plus random samples on triangles larger than spacing^2, so thin, sparse sheets (cheek tissue,
    gums) count as surfaces, not as scattered vertices."""
    bpy.ops.wm.open_mainfile(filepath=blend)
    rng = np.random.default_rng(0)
    pts = []
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or not ob.users_collection or ob.name == "Ground":
            continue
        if any(c.name == "STUDIO" for c in ob.users_collection):
            continue
        me = ob.data
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        M = np.array(ob.matrix_world)
        co = co.reshape(-1, 3).astype(float) @ M[:3, :3].T + M[:3, 3]
        pts.append(co[::step])
        me.calc_loop_triangles()
        tri = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tri)
        A, B, C = (co[tri.reshape(-1, 3)[:, i]] for i in range(3))
        k = np.floor(0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1) / spacing ** 2).astype(int)
        idx = np.repeat(np.arange(len(k)), k)
        if len(idx):
            r1, r2 = rng.random(len(idx)), rng.random(len(idx))
            flip = r1 + r2 > 1
            r1[flip], r2[flip] = 1 - r1[flip], 1 - r2[flip]
            pts.append(A[idx] + (B[idx] - A[idx]) * r1[:, None] + (C[idx] - A[idx]) * r2[:, None])
    return np.concatenate(pts)


def splat(u, v, shape, k=2):
    H, W = shape
    m = np.zeros((H * k, W * k), bool)
    ui, vi = np.round(u * k).astype(int), np.round(v * k).astype(int)
    ok = (ui >= 0) & (ui < W * k) & (vi >= 0) & (vi < H * k)
    m[vi[ok], ui[ok]] = True
    m = ndi.binary_dilation(m, iterations=1)
    m = ndi.binary_closing(m, structure=np.ones((3, 3)), iterations=2)
    m = ndi.binary_fill_holes(m)
    return m.reshape(H, k, W, k).mean((1, 3)) > 0.5


def iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def ortho_uv(P, view, s, u0, v0):
    if view == "front":                       # looking along +Y: x right, z up
        return u0 + s * P[:, 0], v0 - s * P[:, 2]
    return u0 + s * P[:, 1], v0 - s * P[:, 2]   # side, from +X: y right (front to the left), z up


def fit_ortho(P, ref, view):
    H, W = ref.shape
    Ps = P[::max(1, len(P) // 120000)]
    ys, xs = np.nonzero(ref)
    h_ref = ys.max() - ys.min()
    h_mod = Ps[:, 2].max() - Ps[:, 2].min()
    s0 = h_ref / max(h_mod, 1e-6)
    horiz = Ps[:, 0] if view == "front" else Ps[:, 1]
    u00 = xs.mean() - s0 * horiz.mean()
    v00 = ys.max() + s0 * Ps[:, 2].min()

    def f(p):
        u, v = ortho_uv(Ps, view, *p)
        return -iou(splat(u, v, (H, W), 1), ref)
    best = None
    for ds in (0.92, 1.0, 1.08):
        x0 = np.array([s0 * ds, u00, v00])
        r = minimize(f, x0, method="Nelder-Mead",
                     options={"maxiter": 300, "xatol": 0.05, "fatol": 1e-4,
                              "initial_simplex": [x0, x0 + [s0 * 0.04, 0, 0], x0 + [0, 6, 0], x0 + [0, 0, 6]]})
        if best is None or r.fun < best.fun:
            best = r
    return best.x, -best.fun


TARGET = np.array([-0.15, -0.55, 1.45])


def persp_uv(P, p, W, H, target=TARGET):
    az, el, dist, lens, sx, sy = p
    t = np.asarray(target, float)
    loc = t + dist * np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    fwd = (t - loc) / np.linalg.norm(t - loc)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = P - loc
    z = rel @ fwd
    x, y = (rel @ right) / z, (rel @ up) / z
    k = lens / 36.0 * W
    return W / 2 + (x + sx * 36.0 / lens) * k, H / 2 - (y + sy * 36.0 / lens) * k


# starts for the three-quarter fit: (azimuth deg, elevation deg, lens mm); the distance keeps the
# framing (4.6 m at 46 mm), the lens shift is set so the model's silhouette centre lands on the
# sheet's. Short lenses (the earlier ref34 family) and long, near-orthographic ones are all tried.
STARTS34 = ((23.5, 9.0, 46.0), (30.0, 9.0, 55.0), (36.0, 9.0, 70.0), (24.0, 5.0, 120.0), (24.0, 4.0, 250.0))


def fit_persp(P, ref, target=TARGET):
    H, W = ref.shape
    Ps = P[::max(1, len(P) // 120000)]
    ys, xs = np.nonzero(ref)

    def f(p):
        u, v = persp_uv(Ps, p, W, H, target)
        return -iou(splat(u, v, (H, W), 1), ref)
    best = None
    for az0, el0, lens0 in STARTS34:
        x0 = np.array([math.radians(az0), math.radians(el0), 4.6 * lens0 / 46.0, lens0, 0.0, 0.0])
        u, v = persp_uv(Ps, x0, W, H, target)
        x0[2] *= (v.max() - v.min()) / max(1.0, ys.max() - ys.min())        # match the figure's height
        u, v = persp_uv(Ps, x0, W, H, target)
        x0[4] = (xs.mean() - u.mean()) / W                                   # and its centre
        x0[5] = -(ys.mean() - v.mean()) / W
        steps = (0.08, 0.05, 0.08 * x0[2], 0.12 * lens0, 0.03, 0.03)
        r = minimize(f, x0, method="Nelder-Mead",
                     options={"maxiter": 700, "xatol": 1e-4, "fatol": 1e-5,
                              "initial_simplex": [x0] + [x0 + np.eye(6)[i] * d for i, d in enumerate(steps)]})
        if best is None or r.fun < best.fun:
            best = r
    return best.x, -best.fun


def overlay(panel, ref, mm, path):
    ov = panel.astype(float) * 0.45
    ov[ref & ~mm] = ov[ref & ~mm] * 0.4 + np.array([255, 60, 40]) * 0.6
    ov[mm & ~ref] = ov[mm & ~ref] * 0.4 + np.array([40, 120, 255]) * 0.6
    ov[mm & ref] = ov[mm & ref] * 0.7 + np.array([200, 200, 200]) * 0.3
    ov[ref & ~ndi.binary_erosion(ref)] = (255, 255, 0)
    ov[mm & ~ndi.binary_erosion(mm)] = (0, 255, 255)
    Image.fromarray(ov.astype(np.uint8)).resize((ref.shape[1] * 2, ref.shape[0] * 2), Image.NEAREST).save(path)


REGIONS = {  # panel-pixel boxes per view
    "front": {"head+jaw": (205, 0, 330, 165), "torso": (200, 80, 370, 275), "long arm": (40, 80, 215, 495),
              "short arm": (340, 80, 445, 340), "legs": (195, 255, 400, 495)},
    "side": {"head+jaw": (60, 20, 232, 240), "torso": (220, 60, 420, 300), "long arm": (80, 230, 262, 495),
             "legs": (262, 300, 470, 495)},
    "34": {"head+jaw": (140, 25, 270, 225), "torso": (195, 50, 350, 280), "long arm": (0, 100, 200, 480),
           "short arm": (290, 90, 440, 340), "legs": (200, 250, 430, 480)},
}


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    refs, prefix, blends = argv[0], argv[1], argv[2:]
    masks = sheet_masks(refs)
    for blend in blends:
        name = os.path.splitext(os.path.basename(blend))[0].replace("out_there_monster_", "")
        P = model_points(blend)
        print(name + ":")
        for view in ("front", "side", "34"):
            ref, panel = masks[view]
            H, W = ref.shape
            if view == "34":
                p, sc = fit_persp(P, ref)
                u, v = persp_uv(P, p, W, H)
                extra = "  (az %.1f el %.1f dist %.2f lens %.0f; FIT34=%s)" % (
                    math.degrees(p[0]), math.degrees(p[1]), p[2], p[3],
                    ",".join("%.6g" % c for c in list(p) + list(TARGET)))
            else:
                p, sc = fit_ortho(P, ref, view)
                u, v = ortho_uv(P, view, *p)
                extra = "  (%.1f px/m)" % p[0]
            mm = splat(u, v, (H, W))
            line = "   %-5s IoU %.3f |" % (view, iou(mm, ref))
            for rk, (x0, y0, x1, y1) in REGIONS[view].items():
                line += " %s %.3f" % (rk, iou(mm[y0:y1, x0:x1], ref[y0:y1, x0:x1]))
            print(line + extra)
            overlay(panel, ref, mm, "%s_%s_%s.png" % (prefix, name, view))
