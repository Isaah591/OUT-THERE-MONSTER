"""
v7 head (reference accuracy pass; head_v6.py is kept unchanged), built from the approved sheet's
three views rather than by adjusting v6's rounded, helmet-like block:

- cranium: a long, angular box-wedge, as the exact side view shows it (about 0.85 m from the
  snout's front face to the back of the skull, about 0.55 m wide as in the front view, its top
  ~0.34 m above the upper gum line) - a level, flat, broken top; an irregular forehead that
  slopes back in uneven planes from the face; broken corners, chunks and a knob at the back;
  asymmetric damage; recessed rectangular sockets high on the face with tiny red pupils.
- jaw: a long, narrow, V-tapered lower jaw hanging from a hinge under the back of the skull,
  forced open so the chin hangs low in front of the chest (side and three-quarter views).
- teeth: fewer than v6 (36: 19 upper, 17 lower), long upper and lower fangs with uneven gaps,
  lengths, tilts and curvature, one snapped here and there; dark mouth, restrained flesh.

Cranium-local space, head units (1 unit = HEAD_SCALE metres): origin at the middle of the skull's
length at the upper gum line, front -Y, Z up. The jaw is parented to the cranium and pivots at
its own origin (the hinge).
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import monster_detail as D
import sculpt as SC
import surface_v5 as SV

rng = random.Random(77)
U = 0.60                                    # metres per head unit (set by build_head)
FAST = False                                # set by build_head (V7_FAST): skip the surface detail
HW = 0.93                                   # nominal head width (units): 0.55 m
FACE_Y = -0.70                              # the face plane (front of the snout)
JAW_LEN, JAW_W = 1.18, 0.80
HINGE = Vector((0.0, 0.60, -0.20))          # under the back of the skull (side view)
DISLOCATE = Vector((0.0, 0.0, -0.05))       # condyles torn out of their sockets: the jaw hangs lower
# Eye sockets as slanted quads in the face plane (x, z; head units): outer-top, inner-top,
# inner-bottom, outer-bottom; depth into the skull, pupil size. High on the face, at the foot of
# the sloping forehead (front view); the left one higher and nearer the midline.
SOCKETS = [([(-0.405, 0.312), (-0.175, 0.292), (-0.180, 0.152), (-0.398, 0.145)], 0.100, 1.10),
           ([(0.322, 0.352), (0.108, 0.330), (0.112, 0.186), (0.318, 0.178)], 0.095, 1.00)]
EYES = [(sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4, k) for q, _, k in SOCKETS]    # x, z, size


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _m(v):
    """head units -> metres (Surf space)"""
    return np.asarray(v, float) * U


def _zones(zs):
    return [(_m(c), _m(r), s) for c, r, s in zs]


# ---------------------------------------------------------------------------
# Skull
# ---------------------------------------------------------------------------
SKULL_ROWS = [  # z, +x half-width, -x half-width, front y, back y, exponent - a long box-wedge
    (-0.255, 0.335, 0.345, 0.400, 0.630, 3.6),     # rear block over the hinges (the back drops to the jaw joint)
    (-0.140, 0.380, 0.392, 0.200, 0.680, 4.0),
    (-0.030, 0.400, 0.415, -0.660, 0.700, 5.0),    # upper jaw at the gum line
    (0.066, 0.440, 0.455, -0.700, 0.710, 6.0),
    (0.164, 0.455, 0.470, -0.712, 0.712, 6.4),
    (0.250, 0.458, 0.472, -0.690, 0.708, 6.4),     # top of the face: the forehead breaks back steeply...
    (0.333, 0.456, 0.470, -0.630, 0.704, 6.2),
    (0.417, 0.450, 0.464, -0.530, 0.692, 6.0),
    (0.480, 0.440, 0.454, -0.420, 0.672, 5.8),     # ...then flattens out (side view)
    (0.515, 0.425, 0.439, -0.330, 0.640, 5.6),
    (0.538, 0.395, 0.408, -0.230, 0.580, 5.0),     # a level, flat top, its full width kept to the edges
    (0.550, 0.340, 0.352, -0.140, 0.480, 4.2),     # top ~0.34 m above the gum line (blueprint)
]

SKULL_DAMAGE = {   # torn regions, broken corners (embedded, no stacked plates)
    "peel": [((0.42, -0.08, 0.40), (0.10, 0.30, 0.16), 1.0),     # fracture, left side
             ((0.44, 0.05, 0.12), (0.08, 0.32, 0.12), 0.9),       # torn gape along the left side
             ((-0.46, 0.30, 0.26), (0.10, 0.26, 0.14), 0.9),      # right side, behind the cheek
             ((0.08, 0.70, 0.35), (0.20, 0.09, 0.14), 0.85),      # back
             ((-0.30, -0.40, 0.55), (0.14, 0.16, 0.06), 0.85),    # crown, front right
             ((-0.42, -0.62, 0.36), (0.08, 0.08, 0.08), 0.9),     # broken brow corner (right)
             ((0.16, 0.30, 0.56), (0.12, 0.16, 0.05), 0.8)],      # crown, back
    "wound": [((0.44, -0.04, 0.30), (0.07, 0.10, 0.05), 1.0),
              ((-0.46, 0.26, 0.26), (0.04, 0.12, 0.06), 1.0)],
}


def build_skull(col, rust):
    keys = [{"p": (0.0, 0.0, z), "ws": ws, "wn": wn, "df": (yb - yf) / 2, "db": (yb - yf) / 2,
             "oy": -(yf + yb) / 2, "e": e} for z, ws, wn, yf, yb, e in SKULL_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=56, step=0.012, caps=(0.03, 0.02))
    sk = SC.obj_from_bm("Cranium", bm, col, [rust])
    SC.remesh(sk, 0.010)
    S = SC.Surf(sk, U)
    S.smooth(2)
    # a broad, flat face; the forehead above it breaks back in uneven planes (not a dome)
    SC.flatten(S, _m((0.0, -0.712, 0.14)), _m((0.42, 0.08, 0.14)), (0.0, -1.0, 0.03), 0.7)
    _face(S)
    SC.push(S, _m((0.36, -0.62, 0.27)), _m((0.07, 0.07, 0.05)), -0.010)                  # dents
    SC.push(S, _m((-0.20, 0.05, 0.52)), _m((0.10, 0.14, 0.05)), -0.008)
    SC.warp(S, 0.003, 3.0, 61)
    # hard planar breaks: chunks broken off the edges of the block, each a flat facet with a crisp
    # edge (uneven and asymmetric - a damaged block, not a smooth helmet)
    _cut(S, (0.12, 0.60, 0.50), (0.32, 0.22, 0.14), (0.15, 0.55, 0.82))      # back-top edge, sheared (left)
    _cut(S, (-0.22, 0.62, 0.48), (0.30, 0.22, 0.16), (-0.10, 0.50, 0.86))    # back-top edge (right), lower
    _cut(S, (0.40, -0.45, 0.48), (0.15, 0.20, 0.12), (0.60, -0.40, 0.69))    # front-top corner broken off (left)
    _cut(S, (-0.41, 0.25, 0.51), (0.13, 0.24, 0.10), (-0.55, 0.15, 0.82))    # top edge broken (back right)
    _cut(S, (-0.43, -0.05, 0.30), (0.10, 0.17, 0.11), (-1.0, 0.10, 0.15))    # gouge in the right side
    _cut(S, (0.42, 0.25, 0.25), (0.08, 0.22, 0.13), (1.0, 0.20, 0.20))       # left side sheared off
    _cut(S, (-0.10, -0.60, 0.34), (0.15, 0.10, 0.08), (-0.25, -0.80, 0.55))  # brow, broken plane
    _cut(S, (-0.42, -0.66, 0.12), (0.11, 0.13, 0.22), (-0.72, -0.69, 0.0))   # front-right edge broken off
    _cut(S, (-0.44, -0.60, 0.40), (0.12, 0.12, 0.12), (-0.60, -0.50, 0.60))  # brow corner (right)
    _cut(S, (0.42, 0.62, 0.30), (0.12, 0.14, 0.18), (0.60, 0.50, 0.20))      # back corner (left)
    # raised plates and a missing chunk on the flat top (crisp steps)
    _plate(S, (-0.18, -0.05), (0.13, 0.11), 0.024)
    _plate(S, (0.20, 0.33), (0.10, 0.08), 0.018)
    _plate(S, (0.05, 0.12), (0.07, 0.10), 0.012)
    _plate(S, (0.30, -0.15), (0.06, 0.07), -0.026)
    if FAST:
        S.a["socket"] = np.zeros(S.n)
        _sockets(S)
        S.write()
        return sk
    S = _knife_head(S, sk, 120, 65, 0.0095)                     # low-poly: broad, readable planes
    _sockets(S)
    _palate(S)
    keep = (S.a["socket"] < 0.5) * (S.a["tissue"] < 0.5) * 1.0
    chunk = SV.crack_network(S, cell=0.080, width=0.0025, depth=0.0030, seed=60, w=keep, tilt=0.035)
    SC.damage(S, _zones(SKULL_DAMAGE["peel"]), _zones(SKULL_DAMAGE["wound"]),
              np.array([0.0, 0.0, 1.0]), seed=66, t1=0.008, t2=0.005, tissue=0.010, lips=0.0,
              w=(S.a["socket"] < 0.5) * 1.0, n_flaps=0, chunk=chunk, jag=0.7)
    _chips(S, 67, amount=1.35, bias=-0.40)                      # recessed chips along the edges (broken outline)
    SV.pits(S, per_m2=24, size=(0.018, 0.038), depth=(0.008, 0.016), seed=69, w=keep)   # deep holes
    SV.pits(S, per_m2=90, size=(0.007, 0.018), depth=(0.003, 0.007), seed=62, w=keep)
    SV.erode(S, amp=0.0018, freq=11.0, seed=63, w=keep)
    SC.blood(S, 68, drips=6, near=0.03)
    SC.finish(S, sk, decimate_ratio=1.0, sharp_deg=6.0)
    return sk


def _cut(S, center, radius, normal, edge=0.18):
    """Hard planar break (head units): inside the ellipsoid `radius` around `center` (narrow soft
    rim) everything above the plane through `center` is cut down onto it - a crisp flat facet."""
    c, nrm = _m(center), SC.unit(normal)
    d = (S.co - c) / _m(radius)
    f = SC.smoothstep(1.0, 1.0 - edge, np.sqrt((d * d).sum(1)))
    dist = np.maximum((S.co - c) @ nrm, 0.0)
    S.co -= (f * dist)[:, None] * nrm[None]


def _plate(S, xy, radius, height):
    """Raised (or sunken, height < 0) plate on the top: the upward-facing surface inside a
    hard-edged ellipse (x, y; head units) steps up by `height`."""
    nrm = S.normals()
    d = (S.co[:, :2] - _m(xy)) / _m(radius)
    f = SC.smoothstep(1.0, 0.86, np.sqrt((d * d).sum(1))) * SC.smoothstep(0.5, 0.75, nrm[:, 2])
    S.co[:, 2] += f * height * U


def _edge_dist(px, pz, a, b):
    """Signed distance (head units) above the line a->b (a, b: (x, z)), and the position along it."""
    ax, az = a
    bx, bz = b
    tx, tz = bx - ax, bz - az
    L = math.hypot(tx, tz)
    tx, tz = tx / L, tz / L
    u = ((px - ax) * tx + (pz - az) * tz) / L
    return (pz - az) - (px - ax) * (tz / tx), u


def _face(S):
    """Heavy brow ledges over the slanted socket tops meeting low over the nose, a short nasal
    ridge, gaunt hollows under the sockets with cheekbones at their outer corners."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    front = SC.smoothstep(FACE_Y + 0.17, FACE_Y + 0.05, y)       # the face, not the sides or back
    d = np.zeros(S.n)
    for quad, _, _ in SOCKETS:
        (ox, oz), (ix, iz) = quad[0], quad[1]
        h, u = _edge_dist(x, z, (ox, oz), (ix, iz))
        band = np.clip(1 - np.abs(h - 0.035) / 0.055, 0, 1) ** 1.3 * (h > -0.01)
        span = SC.smoothstep(-0.12, 0.05, u) * SC.smoothstep(1.18, 0.95, u)
        d = np.maximum(d, 0.050 * band * span)                    # brow ledge over each socket
    d = np.maximum(d, 0.032 * np.exp(-((x + 0.03) / 0.10) ** 2 - ((z - 0.28) / 0.05) ** 2))
    d = np.maximum(d, 0.020 * np.exp(-((x + 0.03) / 0.05) ** 2) * SC.smoothstep(0.05, 0.12, z) * SC.smoothstep(0.29, 0.21, z))
    S.co[:, 1] -= d * front * U
    for cx in (-0.29, 0.21):                                      # under each socket
        hollow = np.exp(-((x - cx) / 0.07) ** 2 - ((z - 0.09) / 0.045) ** 2)
        S.co[:, 1] += 0.016 * hollow * front * U
    for cx in (-0.42, 0.34):
        cheek = np.exp(-((x - cx) / 0.04) ** 2 - ((z - 0.10) / 0.04) ** 2)
        S.co[:, 1] -= 0.010 * cheek * front * U


def _knife_head(S, ob, faces, seed, jitter):
    S.write()
    SC.lowpoly(ob, faces, jitter=jitter / U, seed=seed, dissolve_deg=4.0, levels=1, remesh_after=0.0050 / U)
    S = SC.Surf(ob, U)
    S.a["socket"] = np.zeros(S.n)
    return S


def _sockets(S):
    """Deep slanted sockets carved straight back into the face (crisp, snapped, chipped rims);
    the floor is deepest under the brow, so the eye sits up in the shadow."""
    sock = np.zeros(S.n)
    x, z = S.co[:, 0] / U, S.co[:, 2] / U
    for n_, (quad, depth, k) in enumerate(SOCKETS):
        dist = np.full(S.n, -1e9)
        cx = sum(p[0] for p in quad) / 4
        cz = sum(p[1] for p in quad) / 4
        for a, b in zip(quad, quad[1:] + quad[:1]):              # convex polygon: max of edge distances
            ex, ez = b[0] - a[0], b[1] - a[1]
            L = math.hypot(ex, ez)
            nx, nz = ez / L, -ex / L
            if (cx - a[0]) * nx + (cz - a[1]) * nz > 0:
                nx, nz = -nx, -nz
            dist = np.maximum(dist, (x - a[0]) * nx + (z - a[1]) * nz)
        dist = dist + 0.006 * SC.fbm(SC.Perlin(31 + 7 * n_), S.co * 38.0, 2)           # worn rim
        front = S.co[:, 1] < (FACE_Y + 0.17) * U
        f = np.where(front, -dist, -1.0)
        f = SC.snap_iso(S, f)
        inside = f > 0
        ztop = max(p[1] for p in quad)
        zbot = min(p[1] for p in quad)
        under_brow = np.clip((z - zbot) / (ztop - zbot), 0, 1)
        dd = (depth * (0.72 + 0.38 * under_brow) + 0.010 * SC.fbm(SC.Perlin(41 + n_), S.co * 25.0, 2)) * U
        S.co[inside, 1] += dd[inside]
        sock = np.maximum(sock, inside * 1.0)
    S.a["socket"] = sock
    S.a_socket_final = sock


PAL_Y, PAL_RX, PAL_RY = -0.22, 0.34, 0.44       # vaulted palate inside the upper gum ring


def _palate(S):
    nrm = S.normals()
    bottom = (nrm[:, 2] < -0.45) & (S.co[:, 2] < 0.03 * U)
    g = (np.abs(S.co[:, 0]) / (PAL_RX * U)) ** 4 + (np.abs(S.co[:, 1] - PAL_Y * U) / (PAL_RY * U)) ** 4
    lift = 0.030 * SC.smoothstep(1.0, 0.45, g) * bottom
    S.co[:, 2] += lift
    S.a["tissue"] = np.maximum(S.a["tissue"], SC.smoothstep(1.05, 0.85, g) * bottom)


def _chips(S, seed, amount=0.6, bias=-0.6):
    k = S.blur(S.curvature(), 2)
    cv = SC.smoothstep(6.0, 28.0, k)
    gate = SC.smoothstep(0.2, 1.0, SC._z(SC.fbm(SC.Perlin(seed), S.co * 6.0, 2)))
    SC.damage(S, [], [], np.array([0.0, 0.0, 1.0]), seed=seed, t1=0.006, t2=0.003, tissue=0.0, lips=0.0,
              extra=amount * cv * gate + bias, tear_amt=0.0, w=(S.a["socket"] < 0.5) * 1.0)   # recessed edge chips


# ---------------------------------------------------------------------------
# Jaw
# ---------------------------------------------------------------------------
JAW_ROWS = [  # y, half-width, up (rim height), down, exponent - wide at the hinge, long, V-tapered, heavy
    (0.06, 0.400, 0.055, 0.160, 3.0),
    (-0.10, 0.395, 0.072, 0.210, 3.2),
    (-0.40, 0.335, 0.052, 0.255, 3.4),
    (-0.70, 0.258, 0.076, 0.275, 3.4),
    (-0.95, 0.180, 0.052, 0.270, 3.2),
    (-1.160, 0.120, 0.062, 0.270, 3.0),       # narrow rounded U at the chin, deep (rounded end cap)
]
JAW_SKEW = (1.05, 0.96)                       # its right side (-X) flares wider, its left side narrower


def jaw_half(y):
    """Half-width of the lower jaw (head units) at jaw-local y."""
    ys = [r[0] for r in JAW_ROWS][::-1]
    ws = [r[1] for r in JAW_ROWS][::-1]
    return np.interp(y, ys, ws)


JAW_DAMAGE = {
    "peel": [((-0.38, -0.12, -0.08), (0.08, 0.20, 0.12), 1.0),    # broken right side near the hinge
             ((0.05, -1.12, -0.18), (0.10, 0.06, 0.12), 0.85),    # chipped chin
             ((0.0, -0.60, -0.26), (0.18, 0.26, 0.06), 0.7),      # underside
             ((0.24, -0.50, -0.04), (0.06, 0.28, 0.05), 0.7),     # torn along the gum line
             ((-0.20, -0.78, -0.04), (0.06, 0.22, 0.05), 0.65)],
    "wound": [((-0.40, -0.10, -0.06), (0.05, 0.08, 0.08), 1.0)],
}


def build_jaw(col, rust, sk, open_deg, roll_deg):
    keys = [{"p": (0.0, y, 0.0), "ws": w * JAW_SKEW[1], "wn": w * JAW_SKEW[0], "df": up, "db": dn, "e": e}
            for y, w, up, dn, e in JAW_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=44, step=0.02, caps=(0.05, 0.10))
    for sx in (-1, 1):                                   # rami rising to the condyles
        ramus = SC.loft([{"p": (sx * 0.340, 0.02, -0.12), "w": 0.034, "d": 0.065, "e": 3.0},
                         {"p": (sx * 0.345, 0.01, -0.03), "w": 0.032, "d": 0.058, "e": 3.0},
                         {"p": (sx * 0.350, 0.00, 0.06), "w": 0.036, "d": 0.052, "e": 2.6}],
                        ref=(0, -1, 0), seg=20, step=0.02, caps=(0.02, 0.04))
        SC.merge_bm(bm, ramus)
    jaw = SC.obj_from_bm("Jaw", bm, col, [rust])
    SC.remesh(jaw, 0.011)
    S = SC.Surf(jaw, U)
    S.smooth(3)
    SC.push(S, _m((0.0, -0.92, -0.17)), _m((0.16, 0.08, 0.10)), 0.010)                  # heavy chin
    SC.push(S, _m((0.27, -0.78, 0.06)), _m((0.08, 0.10, 0.08)), -0.024)                 # a chunk broken out of the rim
    SC.push(S, _m((-0.34, -0.48, 0.06)), _m((0.06, 0.16, 0.06)), 0.012)                 # rim bulging out (right)
    SC.push(S, _m((-0.38, -0.25, -0.16)), _m((0.06, 0.18, 0.12)), -0.008)
    SC.push(S, _m((0.36, -0.45, -0.15)), _m((0.06, 0.12, 0.10)), 0.006)
    SC.warp(S, 0.006, 3.0, 71)
    SC.dents(S, 5, (0.025, 0.05), (0.003, 0.008), 72)
    S.write()
    if not FAST:
        SC.lowpoly(jaw, 300, jitter=0.0040 / U, seed=73, dissolve_deg=4.0, levels=1, remesh_after=0.0050 / U)
        S = SC.Surf(jaw, U)
        _trough(S)
        keep = (S.a["tissue"] < 0.5) * 1.0
        chunk = SV.crack_network(S, cell=0.075, width=0.0035, depth=0.0035, seed=70, w=keep)
        SC.damage(S, _zones(JAW_DAMAGE["peel"]), _zones(JAW_DAMAGE["wound"]), np.array([1.0, 0.0, 0.0]),
                  seed=74, t1=0.008, t2=0.005, tissue=0.010, lips=0.0, w=keep, n_flaps=0, chunk=chunk, jag=0.7)
        SV.pits(S, per_m2=90, size=(0.007, 0.018), depth=(0.003, 0.007), seed=75, w=keep)
        SV.erode(S, amp=0.0018, freq=11.0, seed=76, w=keep)
        S.a_socket_final = np.zeros(S.n)
        rot = Matrix.Rotation(math.radians(open_deg), 3, 'X')
        down_local = rot.inverted() @ Vector((0, 0, -1))
        SC.blood(S, 76, drips=10, near=0.03, down=tuple(down_local))
        SC.finish(S, jaw, decimate_ratio=1.0, sharp_deg=6.0)
    jaw.parent = sk
    jaw.matrix_parent_inverse = Matrix.Identity(4)
    jaw.location = HINGE + DISLOCATE
    jaw.rotation_euler = (math.radians(open_deg), math.radians(-roll_deg), math.radians(1.5))
    bpy.context.view_layer.update()
    return jaw


def _trough(S):
    """Carve the mouth floor between the gum rims (crisp rim, snapped)."""
    nrm = S.normals()
    top = nrm[:, 2] > 0.35
    skew = np.where(S.co[:, 0] > 0, JAW_SKEW[1], JAW_SKEW[0])
    inner = np.maximum(jaw_half(S.co[:, 1] / U) * skew - 0.09, 0.035) * U   # follows the taper (and the skew)
    g = (np.abs(S.co[:, 0]) / inner) ** 4 + (np.abs(S.co[:, 1] + 0.53 * U) / (0.58 * U)) ** 4
    f = np.where(top, 1.0 - g, -1.0)
    f = SC.snap_iso(S, f)
    inside = f > 0
    depth = 0.070 * np.clip(f, 0, 1) ** 0.35
    S.co[:, 2] -= depth * inside
    S.a["tissue"] = np.maximum(S.a["tissue"], inside * 1.0)
    S.a["socket"] = 0.8 * inside                                 # deep in the open mouth: near black


# ---------------------------------------------------------------------------
# Hinges and torn tissue bridging the forced-open wedge
# ---------------------------------------------------------------------------
def hinges_and_tissue(M, col, sk, jaw):
    """Restrained dark tissue: a thin torn web at each hinge (rear of the gape) and a dark inner
    cheek wall over the rear of the mouth, so the interior reads dark, not fleshy."""
    jm = jaw.matrix_basis                                   # jaw-local -> cranium-local
    mb = bmesh.new()
    for sx in (-1, 1):                                      # torn web at the hinge
        grid = []
        cols_n, rows_n = 8, 6
        for i in range(cols_n):
            u = i / (cols_n - 1)
            top = Vector((sx * (HW / 2 - 0.06), HINGE.y + 0.04 - u * 0.48, -0.06 + 0.03 * u))
            yj = 0.04 - u * 0.48
            bot = jm @ Vector((sx * (jaw_half(yj) * (JAW_SKEW[1] if sx > 0 else JAW_SKEW[0]) + 0.012), yj, -0.03))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                sag = (0.030 + 0.012 * math.sin(3.0 * u + 1.3 * j)) * math.sin(math.pi * v)   # slack, rippled
                p = top.lerp(bot, v) + Vector((sx * sag, 0, -0.02 * math.sin(math.pi * v) * (1.0 - u)))
                row.append(mb.verts.new(p + Vector((sx * rng.uniform(-0.008, 0.008), rng.uniform(-0.014, 0.014),
                                                    rng.uniform(-0.014, 0.014)))))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                if i >= cols_n - 3 and 0 < j < rows_n - 2 and rng.random() < 0.45 + 0.25 * (i - cols_n + 3):
                    continue                                   # torn, ragged leading edge
                if 0 < i < cols_n - 3 and 0 < j < rows_n - 2 and rng.random() < 0.08:
                    continue                                   # a few holes
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                mb.faces.new(q if sx > 0 else tuple(reversed(q)))
    wall_x, cols_n, rows_n = 0.25, 10, 7                        # dark inner cheek walls, set back in shadow
    for sx in (-1, 1):
        grid = []
        for i in range(cols_n):
            u = i / (cols_n - 1) * 1.25                         # forward to just behind the front teeth (side view)
            top = Vector((sx * wall_x, HINGE.y - 0.04 + u * (-0.20 - HINGE.y + 0.04), -0.04))
            yj = max(0.02 + u * (-0.84 - 0.02), -1.02)
            bot = jm @ Vector((sx * max(jaw_half(yj) * (JAW_SKEW[1] if sx > 0 else JAW_SKEW[0]) - 0.10, 0.05), yj, 0.06))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                p = top.lerp(bot, v)
                sag = math.sin(math.pi * v) * (0.03 + 0.025 * math.sin(7.0 * u + 2.0 * v))      # slack, rippled
                row.append(mb.verts.new(p + Vector((-sx * sag, rng.uniform(-0.010, 0.010), rng.uniform(-0.010, 0.010)))))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                mb.faces.new(q if sx < 0 else tuple(reversed(q)))
    mem = D.bm_object("Mouth_Corner_Tissue", mb, col, [M["throat"]], parent=sk)
    sol = mem.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.015
    D.apply_modifiers(mem)


def D_skin(bm, profiles, mat):
    rings = [[bm.verts.new(p) for p in prof] for prof in profiles]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


# ---------------------------------------------------------------------------
# Mouth interior, gums and teeth
# ---------------------------------------------------------------------------
def mouth_interior(M, col, sk, jaw):
    pb = bmesh.new()                                     # palate ridges (rugae) on the vault
    for i in range(9):
        y = -0.58 + i * 0.075
        hw = 0.28 - i * 0.008
        pts = [Vector((x, y + 0.02 * math.sin(x * 9 + i), 0.020)) for x in (-hw, -hw / 2, 0, hw / 2, hw)]
        D.tube(pb, pts, [0.012, 0.02, 0.016, 0.02, 0.012], 0, sides=5, jitter=0.25)
    D.bm_object("Palate", pb, col, [M["gum"]], parent=sk)
    gb = bmesh.new()                                     # rotted tongue lying in the jaw trough
    pts = [Vector((0.02, -0.14, -0.05)), Vector((0.0, -0.36, -0.065)), Vector((-0.03, -0.58, -0.07)),
           Vector((0.02, -0.80, -0.06)), Vector((0.04, -0.96, -0.04))]
    rings = []
    for i, p in enumerate(pts):
        w = (0.15, 0.13, 0.11, 0.085, 0.055)[i]                 # follows the V jaw
        h = (0.055, 0.065, 0.06, 0.045, 0.028)[i]
        rings.append([p + Vector((math.cos(a) * w * rng.uniform(0.85, 1.15), 0,
                                  math.sin(a) * h * rng.uniform(0.8, 1.2)))
                      for a in [2 * math.pi * k / 10 for k in range(10)]])
    D_skin(gb, rings, 0)
    bmesh.ops.recalc_face_normals(gb, faces=gb.faces)
    D.bm_object("Tongue", gb, col, [M["tongue"]], parent=jaw)
    tb = bmesh.new()                                     # ribbed throat receding into the body
    path = [Vector((0, 0.30, -0.06)), Vector((0, 0.42, -0.16)), Vector((0, 0.52, -0.28)), Vector((0, 0.58, -0.40))]
    rings = []
    for i, p in enumerate(path):
        for sub in range(3):
            if i == len(path) - 1 and sub:
                break
            q = p if i == len(path) - 1 else p.lerp(path[i + 1], sub / 3)
            r = (0.25 - 0.04 * (i + sub / 3)) * (1.0 if sub % 2 == 0 else 0.86)
            rings.append([q + Vector((math.cos(a) * r, 0, math.sin(a) * r * 0.75))
                          for a in [2 * math.pi * k / 12 for k in range(12)]])
    rr = [[tb.verts.new(p) for p in ring] for ring in rings]
    for a, b in zip(rr, rr[1:]):
        for k in range(12):
            tb.faces.new((a[k], a[(k + 1) % 12], b[(k + 1) % 12], b[k]))
    tb.faces.new(rr[-1])
    bmesh.ops.reverse_faces(tb, faces=tb.faces)
    D.bm_object("Throat", tb, col, [M["throat"]], parent=sk)


def tusk(bm, layer, base, direction, length, width, kind, curl_dir=None, curl_amt=None):
    """Naturally tapered conical fang: round-ish section, full above the gum, narrowing to a sharp
    point, curved toward `curl_dir` by `curl_amt` (fraction of its length). 'snapped' teeth end
    in a tilted fracture. Colour attribute: (t root->tip, blood, decay, tint)."""
    d = Vector(direction).normalized()
    side = Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, d) @ d.orthogonal().normalized()
    fwd = d.cross(side).normalized()
    depth = width * rng.uniform(0.82, 0.95)
    n = 10
    prof = [(math.cos(2 * math.pi * k / n) * width / 2 * rng.uniform(0.96, 1.03),
             math.sin(2 * math.pi * k / n) * depth / 2 * rng.uniform(0.96, 1.03)) for k in range(n)]
    c_dir = Vector(curl_dir) if curl_dir is not None else side
    c_dir = c_dir - d * c_dir.dot(d)
    if c_dir.length < 1e-6:
        c_dir = side
    curl = c_dir.normalized() * length * (curl_amt if curl_amt is not None else rng.uniform(0.07, 0.15))
    cut = rng.uniform(0.55, 0.75) if kind == "snapped" else 1.0
    ts = [-0.15, 0.0, 0.12, 0.26, 0.40, 0.54, 0.68, 0.80, 0.90, 0.96]
    rad = lambda t: (1.0 - max(t, 0.0)) ** 0.80 * (1.0 + 0.08 * math.sin(math.pi * min(max(t, 0.0) / 0.4, 1.0)))
    ts = [t for t in ts if t < cut - 0.02] + ([cut] if cut < 1.0 else [])
    blood = min(1.0, rng.choice([0.0, 0.0, 0.2, 0.35]) * rng.uniform(0.7, 1.2))
    decay, tint = rng.random() ** 1.4, rng.random()
    rings = []
    for t in ts:
        c = Vector(base) + d * length * t + curl * max(t, 0.0) ** 2
        sc = rad(t) if t >= 0 else 0.92
        rings.append([c + side * x * sc + fwd * y * sc for x, y in prof])
    if cut < 1.0:                                               # fracture plane, tilted
        tilt = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)).normalized()
        c = Vector(base) + d * length * cut + curl * cut ** 2
        rings[-1] = [p + d * (p - c).dot(tilt) * rng.uniform(0.5, 1.0) for p in rings[-1]]
    verts = []
    for t, ring in zip(ts, rings):
        row = []
        for p in ring:
            v = bm.verts.new(p)
            v[layer] = (max(t, 0.0), blood, decay, tint)
            row.append(v)
        verts.append(row)
    for ra, rb in zip(verts, verts[1:]):
        for i in range(n):
            bm.faces.new((ra[i], ra[(i + 1) % n], rb[(i + 1) % n], rb[i]))
    bm.faces.new(list(reversed(verts[0])))
    if cut < 1.0:
        bm.faces.new(verts[-1])
        return
    a = bm.verts.new(Vector(base) + d * length + curl)          # sharp point
    a[layer] = (1.0, blood, decay, tint)
    for i in range(n):
        bm.faces.new((verts[-1][i], verts[-1][(i + 1) % n], a))


# Explicit, irregular arrangement after the sheet: long fangs at the front of both jaws, crooked
# medium ones and a few snapped along the sides; uneven gaps (a wide one left of centre on the
# upper row, one on the jaw's left side), uneven lengths, widths, tilts and curls. All rooted in
# the gum lines (no inner row). 36 teeth in all (v6: 40).
# (x along the front, kind, length, width, tilt about x, tilt about y, curl)
UPPER_FRONT = [(-0.318, "fang", 0.50, 0.095, -6, -15, 0.16), (-0.232, "fang", 0.64, 0.106, 5, 8, 0.10),
               (-0.150, "snapped", 0.30, 0.088, 2, 3, 0.05), (-0.074, "fang", 0.58, 0.100, -10, -11, 0.14),
               (0.024, "fang", 0.68, 0.110, 4, 10, 0.08), (0.122, "fang", 0.46, 0.090, 9, -9, 0.18),
               (0.262, "fang", 0.57, 0.098, -5, 14, 0.12)]
# (y along the side, kind, length, width, tilt about y)
UPPER_SIDES = {1: [(-0.52, "fang", 0.52, 0.094, 8), (-0.41, "fang", 0.44, 0.088, -6), (-0.30, "fang", 0.40, 0.086, 3),
                   (-0.13, "snapped", 0.26, 0.080, 4), (0.00, "fang", 0.36, 0.084, -10), (0.16, "fang", 0.28, 0.078, 6)],
               -1: [(-0.54, "fang", 0.56, 0.096, -9), (-0.44, "fang", 0.50, 0.090, 5), (-0.33, "fang", 0.46, 0.088, -4),
                    (-0.20, "fang", 0.38, 0.084, 7), (-0.05, "fang", 0.34, 0.082, 10), (0.12, "snapped", 0.24, 0.078, -3)]}
# lower teeth (y along the jaw): more and longer on the jaw's right side (-X), a gap on its left
LOWER_SIDES = {1: [(-0.24, "fang", 0.30, 0.080, 6), (-0.40, "fang", 0.42, 0.088, -8), (-0.50, "snapped", 0.32, 0.086, 3),
                   (-0.68, "fang", 0.46, 0.090, -4), (-0.80, "fang", 0.52, 0.094, -5), (-0.92, "fang", 0.46, 0.088, 9),
                   (-1.02, "fang", 0.40, 0.086, -6)],
               -1: [(-0.20, "fang", 0.34, 0.082, -6), (-0.32, "fang", 0.46, 0.090, 7), (-0.44, "fang", 0.56, 0.098, -10),
                    (-0.56, "fang", 0.50, 0.094, 4), (-0.66, "fang", 0.44, 0.090, -3), (-0.78, "fang", 0.60, 0.100, -7),
                    (-0.90, "fang", 0.50, 0.092, 6), (-1.00, "fang", 0.44, 0.088, 8)]}
LOWER_CHIN = [(0.055, -1.085, "fang", 0.52, 0.094), (-0.050, -1.100, "fang", 0.44, 0.090)]

TOOTH_W, TOOTH_L = 1.06, 1.00
FRONT_UP = FACE_Y + 0.085                   # upper gum line just behind the face plane
SIDE_UP = HW / 2 - 0.09                     # and along the sides of the muzzle


def _tilted(d, ax, ay):
    return Matrix.Rotation(math.radians(ay), 3, 'Y') @ (Matrix.Rotation(math.radians(ax), 3, 'X') @ Vector(d))


def gums_and_teeth(M, col, sk, jaw):
    up_z = lambda x: -0.025 - 0.040 * (abs(x) / 0.36) ** 2                  # gum line arches down at the corners
    wall = lambda y, sx=1: jaw_half(y) * (JAW_SKEW[1] if sx > 0 else JAW_SKEW[0]) - 0.060   # lower gum follows the jaw
    upper_path = ([(SIDE_UP, y) for y in (0.22, -0.20)] +
                  [(x, FRONT_UP) for x in (SIDE_UP - 0.04, 0.20, 0.05, -0.11, -0.25, -SIDE_UP + 0.04)] +
                  [(-SIDE_UP, y) for y in (-0.20, 0.22)])
    lys = (-0.06, -0.30, -0.55, -0.78, -0.96)
    lower_path = ([(float(wall(y, 1)), y) for y in lys] + [(0.08, -1.075), (0.0, -1.10), (-0.08, -1.075)] +
                  [(-float(wall(y, -1)), y) for y in lys[::-1]])
    for name, path, parent, zf in (("Gums_Upper", upper_path, sk, lambda x: up_z(x)),
                                   ("Gums_Lower", lower_path, jaw, lambda x: 0.06)):
        gb = bmesh.new()
        dense = []
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.04))
            for st in range(steps):
                t = st / steps
                xx, yy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                dense.append(Vector((xx, yy + rng.uniform(-0.008, 0.008), zf(xx) + rng.uniform(-0.012, 0.010))))
        dense.append(Vector((path[-1][0], path[-1][1], zf(path[-1][0]))))
        side = name == "Gums_Upper"
        radii = [rng.uniform(0.015, 0.023) if (side and abs(p.x) > 0.30) else rng.uniform(0.026, 0.036)
                 for p in dense]                                             # thin dark-red gum / lip band
        D.tube(gb, dense, radii, 0, sides=8, jitter=0.25, frame_ref=(0, 0, 1))
        D.bm_object(name, gb, col, [M["gum"]], parent=parent)

    bm, layer = D.new_tooth_bm()
    for x, kind, L, w, ax, ay, cu in UPPER_FRONT:              # hang down, crooked, uneven
        base = Vector((x, FRONT_UP + rng.uniform(-0.02, 0.012), up_z(x) - 0.005))
        tusk(bm, layer, base, _tilted((0, -0.10, -1), 0.6 * ax, ay), L * TOOTH_L, w * TOOTH_W, kind,
             curl_dir=(0, 1, 0), curl_amt=cu)
    for sx, teeth in UPPER_SIDES.items():
        for y, kind, L, w, ay in teeth:
            base = Vector((sx * SIDE_UP, y + rng.uniform(-0.012, 0.012), -0.03))
            tusk(bm, layer, base, _tilted((sx * 0.06, -0.06, -1), rng.uniform(-8, 8), ay),
                 L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-sx, 0.3, 0), curl_amt=rng.uniform(0.06, 0.18))
    D.bm_object("Teeth_Upper", bm, col, [M["teeth"]], parent=sk)

    bm, layer = D.new_tooth_bm()
    for sx, teeth in LOWER_SIDES.items():                      # rise from the V sides, leaning inward
        for y, kind, L, w, ay in teeth:
            yy = y + rng.uniform(-0.012, 0.012)
            base = Vector((sx * float(wall(yy, sx)), yy, 0.065))
            tusk(bm, layer, base, _tilted((-sx * 0.18, 0.30, 1), rng.uniform(-9, 9), ay),
                 L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-sx * 0.5, 1.0, 0), curl_amt=rng.uniform(0.06, 0.18))
    for x, y, kind, L, w in LOWER_CHIN:
        tusk(bm, layer, Vector((x, y, 0.065)), _tilted((-x * 0.8, 0.20, 1), rng.uniform(-9, 9), rng.uniform(-9, 9)),
             L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-x, 1, -0.3))
    D.bm_object("Teeth_Lower", bm, col, [M["teeth"]], parent=jaw)


def eyes(M, col, sk):
    ebm = bmesh.new()
    me = sk.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    sock = SC.get_attr(me, "socket") > 0.5
    for ex, ez, k in EYES:
        tx, tz = ex, ez + 0.01                           # centre of the void, at its back wall
        d = (co[:, 0] - tx) ** 2 + (co[:, 2] - tz) ** 2
        d[~sock] = 1e9
        i = int(np.argmin(d))
        c = Vector(co[i]) + Vector((0, -0.006, 0))
        r = 0.0045 / U * k                               # ~9 mm: a tiny point far inside the void
        bmesh.ops.create_icosphere(ebm, subdivisions=1, radius=r, matrix=Matrix.Translation(c))
    D.bm_object("Eyes", ebm, col, [M["eye"]], parent=sk)


def crown_bracket(col, mat, sk):
    """Two small rusted knobs on the skull's top (front view: near both top corners; side view:
    one at the back)."""
    me = sk.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    bm = bmesh.new()
    for hint, tilt, L in (((0.30, 0.46, 0.55), (0.45, 0.35, 1.0), 0.08), ((-0.38, -0.10, 0.55), (-0.5, -0.1, 1.0), 0.07)):
        i = int(np.argmin(((co - np.array(hint, np.float32)) ** 2).sum(1)))
        p = Vector(co[i])
        d = Vector(tilt).normalized()
        keys = [{"p": tuple(q), "w": 0.045, "d": 0.028, "e": 7.0} for q in (p - d * 0.12, p, p + d * L)]
        SC.merge_bm(bm, SC.loft(keys, ref=(1, 0, 0), seg=20, step=0.012, caps=(0.008, 0.008)))
    ob = SC.obj_from_bm("Crown_Bracket", bm, col, [mat])
    ob.parent = sk
    SC.remesh(ob, 0.006)
    S = SC.Surf(ob, U)
    SC.warp(S, 0.0015, 9.0, 91)
    SC.finish(S, ob, decimate_ratio=0.6, sharp_deg=50.0)
    return ob


def build_head(M, col, location, rotation, open_deg, roll_deg, scale=0.60, fast=False):
    global U, FAST
    U, FAST = scale, fast
    sk = build_skull(col, M["rust"])
    jaw = build_jaw(col, M["rust"], sk, open_deg, roll_deg)
    eyes(M, col, sk)
    hinges_and_tissue(M, col, sk, jaw)
    mouth_interior(M, col, sk, jaw)
    gums_and_teeth(M, col, sk, jaw)
    crown_bracket(col, M["bar"], sk)
    sk.location, sk.rotation_euler = location, rotation
    sk.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    return sk, jaw
