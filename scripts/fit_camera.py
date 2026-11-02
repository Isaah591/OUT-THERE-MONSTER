"""
Fit a camera to a reference panel by silhouette matching.

    python fit_camera.py <file.blend> <panel.png> <out.json> [x0 y0 x1 y1]   (with the `bpy` module)

The reference panel's monster silhouette is segmented (warm rust / teeth / tissue pixels against
the neutral studio, holes filled, largest component). The model's world-space vertices are
projected through a Blender-style perspective camera (sensor width 36 mm, horizontal fit,
shift in units of the image width) that looks from (azimuth, elevation, distance) at a target,
splatted into a mask and compared by intersection-over-union. Nelder-Mead optimises azimuth,
elevation, distance, focal length and shift; the result is written as a camera location, target,
lens and shift that render_views.py can use, plus the IoU and an overlay image.
"""
import json
import math
import sys

import bpy
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import minimize

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
blend, panel_path, out_path = argv[0], argv[1], argv[2]
REGION = [int(v) for v in argv[3:7]] if len(argv) >= 7 else None     # panel pixels (x0, y0, x1, y1)
bpy.ops.wm.open_mainfile(filepath=blend)

# ---- reference silhouette -------------------------------------------------------------------------
panel = Image.open(panel_path).convert("RGB")
W, H = panel.size
SCALE = 0.5                                          # optimise at half resolution
w, h = int(W * SCALE), int(H * SCALE)
a = np.asarray(panel.resize((w, h), Image.LANCZOS)).astype(int)
warm = ((a[..., 0] - a[..., 2]) > 10) & (a[..., 0] > 38)
warm[: int(0.07 * h), : int(0.75 * w)] = False      # panel title
warm = ndi.binary_closing(warm, structure=np.ones((3, 3)), iterations=2)
warm = ndi.binary_fill_holes(warm)
lab, n = ndi.label(warm)
ref = lab == (1 + int(np.argmax(ndi.sum(warm, lab, range(1, n + 1)))))
ref = ndi.binary_opening(ref, structure=np.ones((2, 2)))

# ---- model points ----------------------------------------------------------------------------------
pts = []
for ob in bpy.data.objects:
    if ob.type != 'MESH' or ob.name == "Ground" or not ob.users_collection:
        continue
    if any(c.name == "STUDIO" for c in ob.users_collection):
        continue
    me = ob.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    M = np.array(ob.matrix_world)
    co = co.reshape(-1, 3).astype(float)
    step = max(1, len(co) // 60000)
    pts.append(co[::step] @ M[:3, :3].T + M[:3, 3])
P = np.concatenate(pts)


def camera_frame(az, el, dist, target):
    t = np.asarray(target, float)
    loc = t + dist * np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    fwd = t - loc
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return loc, fwd, right, up


def project(params, target):
    az, el, dist, lens, sx, sy = params
    loc, fwd, right, up = camera_frame(az, el, dist, target)
    rel = P - loc
    z = rel @ fwd
    ok = z > 0.1
    x = (rel @ right)[ok] / z[ok]
    y = (rel @ up)[ok] / z[ok]
    k = lens / 36.0 * w                               # horizontal sensor fit
    u = w / 2 + (x + sx * 36.0 / lens) * k
    v = h / 2 - (y + sy * 36.0 / lens) * k
    return u, v


def mask_of(params, target):
    u, v = project(params, target)
    m = np.zeros((h, w), bool)
    ui, vi = np.round(u).astype(int), np.round(v).astype(int)
    keep = (ui >= 0) & (ui < w) & (vi >= 0) & (vi < h)
    m[vi[keep], ui[keep]] = True
    m = ndi.binary_dilation(m, iterations=1)
    m = ndi.binary_closing(m, structure=np.ones((3, 3)), iterations=1)
    return ndi.binary_fill_holes(m)


ROI = np.ones((h, w), bool)
if REGION is not None:                               # compare only inside a region (e.g. head + shoulders)
    ROI[:] = False
    x0, y0, x1, y1 = (int(v * SCALE) for v in REGION)
    ROI[y0:y1, x0:x1] = True


def iou(params, target):
    m = mask_of(params, target) & ROI
    r_ = ref & ROI
    inter = (m & r_).sum()
    return inter / max(1, (m | r_).sum())


# initial guess from the existing three-quarter camera (render_views oj_34)
TARGET = np.array([-0.15, -0.55, 1.45])
loc0 = np.array([2.30, -5.80, 2.10])
d0 = loc0 - TARGET
dist0 = np.linalg.norm(d0)
az0 = math.atan2(d0[0], -d0[1])
el0 = math.asin(d0[2] / dist0)
x0 = np.array([az0, el0, dist0, 55.0, 0.0, 0.0])
print("start IoU %.3f" % iou(x0, TARGET))
best = None
for lens0 in (40.0, 55.0, 75.0):
    start = x0.copy()
    start[3] = lens0
    start[2] = dist0 * lens0 / 55.0
    r = minimize(lambda p: -iou(p, TARGET), start, method="Nelder-Mead",
                 options={"maxiter": 900, "xatol": 1e-4, "fatol": 1e-5,
                          "initial_simplex": np.array([start] + [start + np.eye(6)[i] * s for i, s in
                                                                 enumerate((0.08, 0.05, 0.6, 6.0, 0.03, 0.03))])})
    print("lens start %.0f -> IoU %.3f  az %.1f el %.1f dist %.2f lens %.1f shift %.3f %.3f"
          % (lens0, -r.fun, math.degrees(r.x[0]), math.degrees(r.x[1]), r.x[2], r.x[3], r.x[4], r.x[5]))
    if best is None or r.fun < best.fun:
        best = r
az, el, dist, lens, sx, sy = best.x
loc, fwd, right, up = camera_frame(az, el, dist, TARGET)
res = {"location": [float(c) for c in loc], "target": [float(c) for c in TARGET], "lens": float(lens),
       "shift_x": float(sx), "shift_y": float(sy), "resolution": [W, H], "iou": float(-best.fun),
       "azimuth_deg": math.degrees(az), "elevation_deg": math.degrees(el), "distance": float(dist)}
json.dump(res, open(out_path, "w"), indent=2)
m = mask_of(best.x, TARGET)
ov = np.zeros((h, w, 3), np.uint8)
ov[ref] = (200, 60, 60)
ov[m] = (60, 60, 200)
ov[ref & m] = (200, 200, 200)
if REGION is not None:
    ov[~ROI] = ov[~ROI] // 3
Image.fromarray(ov).resize((W, H), Image.NEAREST).save(out_path.replace(".json", "_overlay.png"))
print("FIT", json.dumps(res))
