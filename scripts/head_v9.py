"""
v9 head (head reconstruction; head_v8.py and the body are kept unchanged): not a rectangular shell
with a mouth cut into it, but a damaged, irregular skull around an enormous skeletal mouth, after
the approved sheet's three-quarter and exact-side views together.

- cranium: rounder, skull-like sections (not box sections) with the side view's dome profile:
  the forehead climbs from the snout to the crown as one curve (no brow ledge standing in front
  of a low, set-back forehead); the top falls toward the monster's right-front corner (three-
  quarter and front views); the face angles back from a nasal ridge, eye orbits, broken brow;
  stronger fragmentation - rust fragments, plates, planar breaks, wider cracks, chipped edges.
- mouth frame: the upper jaw is a broken bony rim around a vaulted palate (kept below the eye
  sockets), its lower edge jagged and notched between the teeth (breaks go up into the bone);
  behind the snout the gape tears up into both sides of the skull (larger and higher on the left,
  as the side view shows), exposing dark red tissue.
- lower jaw: an elongated skeletal V - longer, thinner, open steeper on the side view's diagonal,
  ending in a narrow point instead of a rounded chin - clearly apart from the upper skull, with a
  deep open trough.
- teeth: 36 (as v8), re-arranged: 16 upper, crowded at the front of the snout with the long
  fangs forward; 20 lower in a long, dense fan along the jaw leaning up and forward, overlapping.
- red tissue (restrained): dark red gums along both jaws, torn webs at the hinges, thin sagging
  strands between the jaws, red exposed flesh in the torn cheeks; the mouth interior stays dark.

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
FAST = False                                # set by build_head (V9_FAST): skip the surface detail
HW = 0.93                                   # nominal head width (units): 0.55 m
FACE_Y = -0.70                              # the face plane (front of the snout)
JAW_LEN, JAW_W = 1.30, 0.66
HINGE = Vector((0.0, 0.60, -0.20))          # under the back of the skull (side view)
DISLOCATE = Vector((0.0, 0.0, -0.05))       # condyles torn out of their sockets: the jaw hangs lower
# Eye sockets as slanted quads in the face plane (x, z; head units): outer-top, inner-top,
# inner-bottom, outer-bottom; depth into the skull, pupil size. High on the face, at the foot of
# the sloping forehead (front view); the left one higher and nearer the midline.
SOCKETS = [([(-0.410, 0.250), (-0.250, 0.230), (-0.255, 0.095), (-0.310, 0.080), (-0.400, 0.090), (-0.420, 0.170)],
            0.090, 1.25),
           ([(0.220, 0.280), (0.040, 0.265), (0.045, 0.135), (0.120, 0.120), (0.210, 0.130), (0.225, 0.210)],
            0.085, 1.15)]
# (irregular six-sided voids, outer-top and inner-top first: the top edges slope down toward the
#  nose; the right socket sits lower and is wider, the left one nearer the midline - front and
#  three-quarter views), set into shallow orbits with a stepped, chipped surround; moderate depth
#  so the tiny red pupils stay visible from the three-quarter view, as in the sheet
EYES = [(sum(p[0] for p in q) / len(q), sum(p[1] for p in q) / len(q), k) for q, _, k in SOCKETS]  # x, z, size


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
SKULL_ROWS = [  # z, +x half-width, -x half-width, front y, back y, exponent - a rounded skull, not a box
    (-0.255, 0.310, 0.320, 0.380, 0.620, 3.0),     # rear block over the hinges (the back drops to the jaw joint)
    (-0.140, 0.350, 0.360, 0.180, 0.670, 3.2),
    (-0.030, 0.360, 0.375, -0.660, 0.690, 3.6),    # upper jaw at the gum line: narrower than the brow
    (0.070, 0.420, 0.435, -0.710, 0.700, 4.0),
    (0.170, 0.455, 0.470, -0.715, 0.700, 4.2),     # cheekbones and sockets: the widest
    (0.260, 0.460, 0.475, -0.700, 0.700, 4.2),
    (0.340, 0.455, 0.470, -0.655, 0.695, 4.0),     # the forehead breaks back...
    (0.420, 0.440, 0.455, -0.560, 0.680, 3.8),
    (0.490, 0.420, 0.430, -0.440, 0.650, 3.5),     # ...into a domed, uneven cranium (side view)
    (0.540, 0.385, 0.395, -0.300, 0.600, 3.2),
    (0.575, 0.330, 0.340, -0.160, 0.510, 2.8),
    (0.595, 0.250, 0.260, -0.030, 0.380, 2.4),     # (reshaped further: _uneven_top)
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
    S.co[:, 0] *= taper(S.co[:, 1] / U, S.co[:, 2] / U)        # narrowing toward the back (plan)
    SC.flatten(S, _m((0.0, -0.712, 0.14)), _m((0.42, 0.08, 0.14)), (0.0, -1.0, 0.03), 0.7)    # broad, flat face
    _uneven_top(S)
    _wedge_face(S)
    _orbits(S)
    _face(S)
    _maxilla(S)
    _torn_cheeks(S, carve=True)
    SC.warp(S, 0.007, 4.5, 61)                                   # lumpy, not a clean block
    SC.push(S, _m((0.36, -0.60, 0.27)), _m((0.07, 0.07, 0.05)), -0.010)                  # dents
    SC.push(S, _m((-0.20, 0.05, 0.48)), _m((0.10, 0.14, 0.05)), -0.008)
    # hard planar breaks: chunks broken off the edges, each a flat facet with a crisp edge
    _cut(S, (0.14, 0.60, 0.46), (0.30, 0.22, 0.14), (0.20, 0.60, 0.78))      # back-top edge, sheared (left)
    _cut(S, (-0.24, 0.60, 0.40), (0.28, 0.22, 0.16), (-0.15, 0.55, 0.82))    # back-top edge (right), lower
    _cut(S, (0.41, -0.47, 0.47), (0.13, 0.18, 0.11), (0.62, -0.42, 0.66))    # front-top corner broken off (left)
    _cut(S, (-0.43, -0.02, 0.31), (0.10, 0.17, 0.11), (-1.0, 0.10, 0.15))    # gouge in the right side
    _cut(S, (0.42, 0.25, 0.25), (0.08, 0.22, 0.13), (1.0, 0.20, 0.20))       # left side sheared off
    _cut(S, (-0.06, -0.60, 0.33), (0.13, 0.10, 0.07), (-0.20, -0.82, 0.54))  # brow, broken plane
    _cut(S, (-0.42, -0.64, 0.20), (0.12, 0.14, 0.30), (-0.74, -0.67, 0.0))   # front-right edge broken off
    _cut(S, (0.42, 0.62, 0.30), (0.12, 0.14, 0.18), (0.60, 0.50, 0.20))      # back corner (left)
    # broken brow corners sticking out (front view: both top corners of the face)
    SC.push(S, _m((-0.45, -0.46, 0.46)), _m((0.05, 0.06, 0.05)), 0.020)
    SC.push(S, _m((0.45, -0.58, 0.42)), _m((0.05, 0.07, 0.05)), 0.022)
    # uneven plates on the top: raised and sunken, irregular in size (crisp steps)
    for xy, r, h in (((-0.22, -0.05), (0.12, 0.10), 0.024), ((0.18, 0.32), (0.10, 0.08), 0.020),
                     ((0.06, 0.10), (0.07, 0.11), 0.014), ((0.30, -0.15), (0.06, 0.07), -0.026),
                     ((-0.05, -0.32), (0.09, 0.06), 0.016), ((-0.30, 0.30), (0.08, 0.10), -0.018),
                     ((0.26, 0.05), (0.05, 0.08), 0.018)):
        _plate(S, xy, r, h)
    _fragments(S, 52, 71)                                       # (seed chosen against the three views' outlines)
    if FAST:
        S.a["socket"] = np.zeros(S.n)
        _sockets(S)
        S.write()
        return sk
    S = _knife_head(S, sk, 230, 65, 0.0120)                     # low-poly: smaller, irregular facets
    _sockets(S)
    _palate(S)
    _torn_cheeks(S, carve=False)                                # exposed red tissue in the torn cheeks
    keep = (S.a["socket"] < 0.5) * (S.a["tissue"] < 0.5) * 1.0
    chunk = SV.crack_network(S, cell=0.058, width=0.0040, depth=0.0048, seed=60, w=keep, tilt=0.050)
    SC.damage(S, _zones(SKULL_DAMAGE["peel"]), _zones(SKULL_DAMAGE["wound"]),
              np.array([0.0, 0.0, 1.0]), seed=66, t1=0.008, t2=0.005, tissue=0.010, lips=0.0,
              w=(S.a["socket"] < 0.5) * 1.0, n_flaps=0, chunk=chunk, jag=0.7)
    _chips(S, 67, amount=1.60, bias=-0.40)                      # recessed chips along the edges (broken outline)
    SV.pits(S, per_m2=24, size=(0.018, 0.038), depth=(0.008, 0.016), seed=69, w=keep)   # deep holes
    SV.pits(S, per_m2=90, size=(0.007, 0.018), depth=(0.003, 0.007), seed=62, w=keep)
    SV.erode(S, amp=0.0018, freq=11.0, seed=63, w=keep)
    SC.blood(S, 68, drips=6, near=0.03)
    SC.finish(S, sk, decimate_ratio=1.0, sharp_deg=6.0)
    return sk


def taper(y, z):
    """Plan taper of the skull (head units): full width over the face, narrowing toward the back,
    more at the top of the cranium than at the jaw joints (three-quarter view: the skull's side
    recedes; the front view sees only the face's width, the side view only the length)."""
    return 1.0 - 0.26 * SC.smoothstep(-0.10, 0.70, y) * (0.5 + 0.5 * SC.smoothstep(0.0, 0.5, z))


ORBITS = [((-0.330, 0.165), (0.150, 0.140), 0.06),     # (centre x, z), radii, recess (head units): a
          ((0.130, 0.200), (0.150, 0.130), 0.05)]     # gentle hollow around each socket, the right deeper


RIDGE_X = -0.09                                # nasal ridge (head units): the face's forward edge


def _wedge_face(S):
    """The face angles back from a central nasal ridge to both sides, like a bow, above the muzzle:
    the side view's front outline is the ridge; the sockets and the face's edges sit back on the
    angled planes (where the three-quarter view puts them); the front view is unchanged."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    face = SC.smoothstep(-0.36, -0.52, y)
    band = SC.smoothstep(0.02, 0.09, z) * SC.smoothstep(0.46, 0.36, z)
    side = SC.smoothstep(0.05, 0.32, np.abs(x - RIDGE_X))
    S.co[:, 1] += 0.16 * side * band * face * U
    S.co[:, 1] += 0.050 * SC.smoothstep(0.19, 0.30, z) * SC.smoothstep(0.46, 0.36, z) * (1.0 - side) * face * U


def _orbits(S):
    """Eye orbits: the face around each socket hollows back a little behind the nasal ridge and
    the brow, so the sockets sit in the skull rather than being cut into a flat plate (the side
    view shows them behind the snout's front). Irregular, broken boundaries."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    face = SC.smoothstep(-0.38, -0.55, y)
    rec = np.zeros(S.n)
    for n_, ((cx, cz), (rx, rz), amt) in enumerate(ORBITS):
        r = np.sqrt(((x - cx) / rx) ** 2 + ((z - cz) / rz) ** 2)
        edge = 1.0 + 0.18 * SC.fbm(SC.Perlin(81 + n_), S.co * 7.0, 2)
        rec = np.maximum(rec, amt * SC.smoothstep(edge, 0.62 * edge, r))
    S.co[:, 1] += rec * face * U


def _maxilla(S):
    """The upper jaw as a broken bony rim: its lower edge (the gum line region) jagged, notched and
    of uneven thickness, chunks missing between the teeth - not a straight slab edge. The breaks go
    up into the bone (at most ~2 cm down), so no chunk of the face hangs below the gum line."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    rim = SC.smoothstep(0.10, -0.02, z) * SC.smoothstep(-0.20, -0.05, z)
    P = SC.Perlin(171)
    jag = 0.020 * np.clip(SC._z(SC.fbm(P, S.co * 9.0, 2)), -1.2, 2.0) + 0.012 * np.sin(11.0 * x + 3.0 * y)
    notch = np.clip(np.sin(23.0 * x + 2.0) * np.sin(17.0 * y - 1.0), 0, 1) ** 3
    S.co[:, 2] += (jag + 0.045 * notch) * rim * U


TORN = [  # (centre x, y, z), radii (x, y, z): the gape torn up into the skull's sides (head units)
    ((0.430, 0.000, 0.130), (0.150, 0.250, 0.220), 0.16),        # left side, larger and higher (side view)
    ((-0.440, 0.040, 0.060), (0.130, 0.190, 0.120), 0.13),       # right side
]


def _torn_cheeks(S, carve):
    """The skull's side walls behind the snout are broken open where the gape tears into them:
    carved inward (carve=True, before the facets) and marked as exposed tissue (carve=False)."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    nrm = S.normals()
    for n_, ((cx, cy, cz), (rx, ry, rz), depth) in enumerate(TORN):
        sx = np.sign(cx)
        r = np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2)
        edge = 1.0 + 0.30 * SC.fbm(SC.Perlin(191 + n_), S.co * 6.0, 2)
        side = (nrm[:, 0] * sx > 0.35)
        f = SC.smoothstep(edge, 0.70 * edge, r) * side
        if carve:
            S.co[:, 0] -= sx * depth * f * U
        else:
            S.a["tissue"] = np.maximum(S.a["tissue"], (f > 0.35) * 1.0)


def _uneven_top(S):
    """The upper skull falls away toward the monster's right-front corner (three-quarter and front
    views: ~0.09 m below the crown there), rises to a crown about two thirds back (side view) and
    drops off at the back: a vertical reshaping of everything above the sockets."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    z0, top = 0.24, 0.57
    w = np.clip((z - z0) / (top - z0), 0.0, 1.0)
    right = SC.smoothstep(0.20, -0.46, x)                       # 0 on the left half, 1 at the right edge
    front = SC.smoothstep(0.55, -0.35, y)                       # strongest over the face, fading backward
    drop = 0.120 * right * (0.15 + 0.85 * front)                # the right-front corner sinks
    crown = 0.030 * np.exp(-((y - 0.22) / 0.30) ** 2) * SC.smoothstep(-0.30, 0.20, x)   # crown, back-left
    back = 0.070 * SC.smoothstep(0.45, 0.72, y)                 # rounded, lower back edge
    brow = 0.025 * SC.smoothstep(-0.10, -0.50, y)               # a lower forehead over the face
    low = 0.045                                                 # the whole upper skull a little lower
    S.co[:, 2] += (crown - drop - back - brow - low) * w * U
    # a fuller forehead (exact side view): the slope from the brow to the crown rises higher over the
    # centre and the left, so the profile climbs as one steady curve; the right-front corner keeps
    # its drop (three-quarter and front views)
    fill = 0.045 * SC.smoothstep(-0.66, -0.50, y) * SC.smoothstep(0.05, -0.12, y) * SC.smoothstep(-0.30, -0.05, x)
    S.co[:, 2] += fill * SC.smoothstep(0.28, 0.40, z) * U


def _fragments(S, n, seed):
    """Rusty fragments built into the upper skull: small blocks of the surface raised or broken
    out with crisp edges, uneven in size and height, so the outline breaks up into chunks (not
    a smooth dome, not a grid of rectangular plates)."""
    r = np.random.default_rng(seed)
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    nrm = S.normals()
    pool = np.flatnonzero((z > 0.28) & (y > -0.62) & (nrm[:, 2] > -0.2))
    lo, hi = np.array([-0.50, -0.60, 0.30]) * U, np.array([0.50, 0.66, 0.72]) * U
    for _ in range(n):              # centred on the surface nearest to a random point (stable under reshaping)
        q = lo + r.random(3) * (hi - lo)
        i = pool[int(np.argmin(((S.co[pool] - q) ** 2).sum(1)))]
        c = S.co[i]
        rad = r.uniform(0.050, 0.120) * U * np.array([r.uniform(0.7, 1.4), r.uniform(0.7, 1.4), r.uniform(0.6, 1.0)])
        d = (S.co - c) / rad
        f = SC.smoothstep(1.0, 0.82, np.sqrt((d * d).sum(1)))
        h = r.choice([-1.0, 1.0, 1.0]) * r.uniform(0.012, 0.030)    # plates standing proud of the outline
        S.co += (f * h)[:, None] * SC.unit(nrm[i])[None]


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
    d = np.maximum(d, 0.012 * np.exp(-((x + 0.09) / 0.09) ** 2 - ((z - 0.26) / 0.06) ** 2))   # brows meet over the nose
    d = np.maximum(d, 0.020 * np.exp(-((x + 0.09) / 0.05) ** 2) * SC.smoothstep(0.03, 0.10, z) * SC.smoothstep(0.27, 0.19, z))
    S.co[:, 1] -= d * front * U
    for cx, cz in ((-0.46, 0.06), (0.31, 0.09)):                 # cheekbones under the outer corners
        cheek = np.exp(-((x - cx) / 0.04) ** 2 - ((z - cz) / 0.04) ** 2)
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
        cx = sum(p[0] for p in quad) / len(quad)
        cz = sum(p[1] for p in quad) / len(quad)
        for a, b in zip(quad, quad[1:] + quad[:1]):              # convex polygon: max of edge distances
            ex, ez = b[0] - a[0], b[1] - a[1]
            L = math.hypot(ex, ez)
            nx, nz = ez / L, -ex / L
            if (cx - a[0]) * nx + (cz - a[1]) * nz > 0:
                nx, nz = -nx, -nz
            dist = np.maximum(dist, (x - a[0]) * nx + (z - a[1]) * nz)
        dist = dist + 0.006 * SC.fbm(SC.Perlin(31 + 7 * n_), S.co * 38.0, 2)           # worn rim
        front = S.co[:, 1] < (FACE_Y + 0.45) * U                 # the face, including the recessed orbits
        # recessed, stepped surround: the face around the socket breaks back in an uneven ring
        ring_w = 0.040 + 0.020 * SC.fbm(SC.Perlin(51 + n_), S.co * 9.0, 2)
        g = SC.snap_iso(S, np.where(front, ring_w - dist, -1.0))
        surround = (g > 0) & (dist > 0)
        S.co[surround, 1] += (0.045 * U) * SC.smoothstep(0.0, 0.02, g[surround])
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
    lift = 0.090 * SC.smoothstep(1.0, 0.45, g) * bottom             # deep vault: the jaw rim stands proud
    # ...but under the face it stays below the eye sockets' floors (a solid maxilla there; the
    # sockets must not break through into the mouth)
    cap = (0.03 + 0.14 * SC.smoothstep(-0.42, -0.12, S.co[:, 1] / U)) * U
    lift = np.clip(np.minimum(S.co[:, 2] + lift, cap) - S.co[:, 2], 0.0, None) * bottom
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
JAW_ROWS = [  # y, +x half-width, -x half-width, up (rim), down, exponent, twist - a long skeletal V
    (0.06, 0.300, 0.330, 0.050, 0.100, 2.6, 0),
    (-0.15, 0.310, 0.385, 0.062, 0.128, 2.8, 2),
    (-0.45, 0.250, 0.360, 0.044, 0.138, 2.8, 5),    # its right side bulges wide, the rim dips
    (-0.75, 0.180, 0.255, 0.066, 0.136, 2.6, 7),
    (-1.00, 0.112, 0.132, 0.046, 0.118, 2.4, 6),
    (-1.250, 0.055, 0.068, 0.036, 0.085, 2.2, 3),   # a narrow point, not a rounded chin
]


def jaw_side(y, sx):
    """Half-width of the lower jaw (head units) at jaw-local y on the side sx (+1 left, -1 right)."""
    ys = [r[0] for r in JAW_ROWS][::-1]
    ws = [r[1] if sx > 0 else r[2] for r in JAW_ROWS][::-1]
    return np.interp(y, ys, ws)


def jaw_half(y):
    return 0.5 * (jaw_side(y, 1) + jaw_side(y, -1))


JAW_DAMAGE = {
    "peel": [((-0.38, -0.12, -0.08), (0.08, 0.20, 0.12), 1.0),    # broken right side near the hinge
             ((0.05, -1.12, -0.18), (0.10, 0.06, 0.12), 0.85),    # chipped chin
             ((0.0, -0.60, -0.26), (0.18, 0.26, 0.06), 0.7),      # underside
             ((0.24, -0.50, -0.04), (0.06, 0.28, 0.05), 0.7),     # torn along the gum line
             ((-0.20, -0.78, -0.04), (0.06, 0.22, 0.05), 0.65)],
    "wound": [((-0.40, -0.10, -0.06), (0.05, 0.08, 0.08), 1.0)],
}


def build_jaw(col, rust, sk, open_deg, roll_deg):
    keys = [{"p": (0.0, y, 0.0), "ws": ws, "wn": wn, "df": up, "db": dn, "e": e, "rot": rot}
            for y, ws, wn, up, dn, e, rot in JAW_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=44, step=0.02, caps=(0.05, 0.04))
    for sx in (-1, 1):                                   # rami rising to the condyles
        ramus = SC.loft([{"p": (sx * 0.290, 0.02, -0.12), "w": 0.034, "d": 0.065, "e": 3.0},
                         {"p": (sx * 0.292, 0.01, -0.03), "w": 0.032, "d": 0.058, "e": 3.0},
                         {"p": (sx * 0.295, 0.00, 0.06), "w": 0.036, "d": 0.052, "e": 2.6}],
                        ref=(0, -1, 0), seg=20, step=0.02, caps=(0.02, 0.04))
        SC.merge_bm(bm, ramus)
    jaw = SC.obj_from_bm("Jaw", bm, col, [rust])
    SC.remesh(jaw, 0.011)
    S = SC.Surf(jaw, U)
    S.smooth(3)
    SC.push(S, _m((0.0, -1.10, -0.10)), _m((0.10, 0.10, 0.06)), -0.008)                 # thin, pointed tip
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
    yy = S.co[:, 1] / U
    inner = np.maximum(np.where(S.co[:, 0] > 0, jaw_side(yy, 1), jaw_side(yy, -1)) - 0.09, 0.035) * U
    g = (np.abs(S.co[:, 0]) / inner) ** 4 + (np.abs(S.co[:, 1] + 0.58 * U) / (0.64 * U)) ** 4
    f = np.where(top, 1.0 - g, -1.0)
    f = SC.snap_iso(S, f)
    inside = f > 0
    depth = 0.085 * np.clip(f, 0, 1) ** 0.35                     # a deep, open trough between the rims
    S.co[:, 2] -= depth * inside
    S.a["tissue"] = np.maximum(S.a["tissue"], inside * 1.0)
    S.a["socket"] = 0.8 * inside                                 # deep in the open mouth: near black


# ---------------------------------------------------------------------------
# Hinges and torn tissue bridging the forced-open wedge
# ---------------------------------------------------------------------------
def hinges_and_tissue(M, col, sk, jaw):
    """Restrained red tissue: a torn web at each hinge reaching forward along the mouth's corner,
    thin sagging strands between the upper and lower jaw, and short dark walls deep at the rear of
    the mouth, so the interior stays dark and open between the jaws (not enclosed)."""
    jm = jaw.matrix_basis                                   # jaw-local -> cranium-local
    mb = bmesh.new()
    P = SC.Perlin(211)
    wr = random.Random(212)
    for sx in (-1, 1):                                      # torn web at the hinge: a fine, slack membrane
        grid = []                                           # with rounded tears and a ragged leading edge
        cols_n, rows_n = 25, 13
        for i in range(cols_n):
            u = i / (cols_n - 1)
            ty = HINGE.y + 0.04 - u * 0.44
            top = Vector((sx * (0.40 * taper(ty, -0.06) - 0.03), ty, -0.06 + 0.03 * u))
            yj = 0.04 - u * 0.44
            bot = jm @ Vector((sx * (jaw_side(yj, sx) + 0.012), yj, -0.03))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                sag = (0.055 + 0.025 * math.sin(3.0 * u + 3.0 * v)) * math.sin(math.pi * v)   # slack, rippled
                p = top.lerp(bot, v) + Vector((sx * sag, 0, -0.02 * math.sin(math.pi * v) * (1.0 - u)))
                row.append(mb.verts.new(p + Vector((sx * wr.uniform(-0.004, 0.004), wr.uniform(-0.006, 0.006),
                                                    wr.uniform(-0.006, 0.006)))))
            grid.append(row)
        cu = np.array([[(i + 0.5) / (cols_n - 1), (j + 0.5) / (rows_n - 1)] for i in range(cols_n - 1)
                       for j in range(rows_n - 1)])
        tear = SC._z(SC.fbm(P, np.c_[cu[:, 0] * 2.6, cu[:, 1] * 1.8, np.full(len(cu), 3.0 * sx)], 3))
        edge = SC._z(SC.fbm(P, np.c_[cu[:, 1] * 2.2, np.full(len(cu), 7.0 + sx), np.zeros(len(cu))], 2))
        for k, (u, v) in enumerate(cu):
            i, j = int(round(u * (cols_n - 1) - 0.5)), int(round(v * (rows_n - 1) - 0.5))
            anchored = v < 0.10 or v > 0.90                     # attached along both jaws
            if u > 0.70 + 0.10 * edge[k] and not (anchored and u < 0.86):
                continue                                       # torn, ragged leading edge
            if not anchored and tear[k] > 0.85 - 0.6 * u:
                continue                                       # rounded tears, more toward the front
            q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
            mb.faces.new(q if sx > 0 else tuple(reversed(q)))
    bmesh.ops.delete(mb, geom=[v for v in mb.verts if not v.link_faces], context='VERTS')
    wall_x, cols_n, rows_n = 0.25, 10, 7                        # dark inner cheek walls, set back in shadow:
    wb = bmesh.new()                                            # the far (right) side spans the whole mouth so
    for sx in (-1, 1):                                          # the open gape reads dark, the near (left) side
        grid = []                                               # only deep at the rear (open, not enclosed)
        span = 1.25 if sx < 0 else 0.45
        for i in range(cols_n):
            u = i / (cols_n - 1) * span
            ty = HINGE.y - 0.04 + u * (-0.20 - HINGE.y + 0.04)
            top = Vector((sx * wall_x * taper(ty, -0.04), ty, -0.04))
            yj = max(0.02 + u * (-0.84 - 0.02), -1.02)
            bot = jm @ Vector((sx * max(jaw_side(yj, sx) - 0.10, 0.05), yj, 0.06))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                p = top.lerp(bot, v)
                sag = math.sin(math.pi * v) * (0.03 + 0.025 * math.sin(7.0 * u + 2.0 * v))      # slack, rippled
                row.append(wb.verts.new(p + Vector((-sx * sag, rng.uniform(-0.010, 0.010), rng.uniform(-0.010, 0.010)))))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                wb.faces.new(q if sx < 0 else tuple(reversed(q)))
    walls = D.bm_object("Mouth_Inner_Walls", wb, col, [M["throat"]], parent=sk)
    sol = walls.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.015
    D.apply_modifiers(walls)
    mem = D.bm_object("Mouth_Corner_Tissue", mb, col, [M["tissue"]], parent=sk)
    sol = mem.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.015
    D.apply_modifiers(mem)
    sb = bmesh.new()                                        # thin sagging strands between the jaws
    for sx in (-1, 1):
        for k, (ty, yj, r0, broken) in enumerate(((0.38, -0.10, 0.020, False), (0.24, -0.26, 0.016, False),
                                                  (0.08, -0.42, 0.014, True), (-0.06, -0.58, 0.012, sx > 0))):
            a = Vector((sx * (0.36 * taper(ty, -0.05) - 0.02), ty, -0.05))
            b = jm @ Vector((sx * (jaw_side(yj, sx) - 0.02), yj, 0.04))
            n = 7
            pts = []
            for i in range(n):
                t = i / (n - 1)
                if broken and t > 0.62:
                    break                                       # snapped: hangs from the upper jaw
                p = a.lerp(b, t) + Vector((sx * 0.03 * math.sin(math.pi * t), rng.uniform(-0.01, 0.01),
                                           -0.06 * math.sin(math.pi * t)))
                pts.append(p)
            D.tube(sb, pts, [r0 * (1.0 - 0.35 * math.sin(math.pi * i / (n - 1))) for i in range(len(pts))], 0,
                   sides=6, jitter=0.30)
    D.bm_object("Jaw_Strands", sb, col, [M["tissue"]], parent=sk)


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
    pts = [Vector((0.02, -0.16, -0.07)), Vector((0.0, -0.40, -0.085)), Vector((-0.03, -0.64, -0.09)),
           Vector((0.02, -0.88, -0.08)), Vector((0.03, -1.06, -0.06))]
    rings = []
    for i, p in enumerate(pts):
        w = (0.13, 0.11, 0.09, 0.065, 0.040)[i]                 # follows the narrower V jaw
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


# Arrangement after the sheet's exact-side and three-quarter views: uneven upper rows crowded at
# the front of the snout with the long fangs forward (a snapped one, gaps of different widths; the
# rear of the upper jaw, where the gape tears into the cheeks, carries none); along the elongated
# jaw a long, crowded fan of teeth leaning up and forward, overlapping. 36 teeth (as v8): 16 upper,
# 20 lower - two moved from the hidden rear of the upper jaw to the lower fan, none added.
# (x along the front, kind, length, width, tilt about x, tilt about y, curl)
UPPER_FRONT = [(-0.335, "fang", 0.54, 0.096, -9, -19, 0.20), (-0.250, "snapped", 0.30, 0.088, 3, 6, 0.04),
               (-0.172, "fang", 0.66, 0.104, -4, -6, 0.12), (-0.098, "fang", 0.44, 0.088, 10, 9, 0.18),
               (-0.020, "fang", 0.72, 0.112, -6, 4, 0.08), (0.074, "fang", 0.38, 0.088, 12, -12, 0.22),
               (0.168, "fang", 0.60, 0.100, -3, 15, 0.14), (0.262, "fang", 0.46, 0.092, 7, 21, 0.18)]
# (y along the side, kind, length, width, tilt about y): crowded behind the front corners
UPPER_SIDES = {1: [(-0.58, "fang", 0.64, 0.098, 12), (-0.47, "fang", 0.50, 0.092, -9), (-0.36, "snapped", 0.30, 0.086, 5),
                   (-0.22, "fang", 0.42, 0.088, -14)],
               -1: [(-0.60, "fang", 0.60, 0.100, -13), (-0.50, "fang", 0.54, 0.094, 7), (-0.38, "fang", 0.46, 0.090, -6),
                    (-0.24, "snapped", 0.30, 0.084, 12)]}
# lower teeth (y along the jaw): a dense fan over the front four fifths of the jaw, uneven gaps and
# lengths, the longest toward the chin
LOWER_SIDES = {1: [(-0.30, "fang", 0.40, 0.086, 9), (-0.41, "fang", 0.52, 0.092, -11), (-0.52, "snapped", 0.34, 0.090, 4),
                   (-0.62, "fang", 0.58, 0.096, -7), (-0.72, "fang", 0.62, 0.100, 13), (-0.82, "fang", 0.54, 0.094, -9),
                   (-0.92, "fang", 0.64, 0.100, 6), (-1.02, "fang", 0.56, 0.094, -12), (-1.11, "fang", 0.50, 0.090, 8)],
               -1: [(-0.26, "fang", 0.42, 0.088, -8), (-0.36, "fang", 0.54, 0.094, 10), (-0.47, "fang", 0.62, 0.100, -14),
                    (-0.57, "fang", 0.50, 0.094, 6), (-0.67, "fang", 0.66, 0.102, -9), (-0.77, "snapped", 0.36, 0.094, 12),
                    (-0.87, "fang", 0.60, 0.098, -5), (-0.97, "fang", 0.64, 0.100, 9), (-1.07, "fang", 0.54, 0.092, -7)]}
LOWER_CHIN = [(0.025, -1.205, "fang", 0.52, 0.090), (-0.035, -1.222, "fang", 0.44, 0.086)]

TOOTH_W, TOOTH_L = 1.06, 0.92                   # long fangs, full at the root (sheet)
FRONT_UP = FACE_Y + 0.085                   # upper gum line just behind the face plane
SIDE_UP = HW / 2 - 0.09                     # and along the sides of the muzzle


def _tilted(d, ax, ay):
    return Matrix.Rotation(math.radians(ay), 3, 'Y') @ (Matrix.Rotation(math.radians(ax), 3, 'X') @ Vector(d))


def gums_and_teeth(M, col, sk, jaw):
    up_z = lambda x: (-0.030 - 0.040 * (abs(x) / 0.36) ** 2 + 0.022 * x / 0.36      # uneven gum line: arches down at the
                      + 0.010 * math.sin(9.0 * x + 1.0))                            # corners, higher on the monster's left
    wall = lambda y, sx=1: jaw_side(y, sx) - 0.060                           # lower gum follows the jaw
    upper_path = ([(SIDE_UP * taper(y, -0.03), y) for y in (0.22, -0.20)] +
                  [(x, FRONT_UP) for x in (SIDE_UP - 0.04, 0.20, 0.05, -0.11, -0.25, -SIDE_UP + 0.04)] +
                  [(-SIDE_UP * taper(y, -0.03), y) for y in (-0.20, 0.22)])
    lys = (-0.06, -0.30, -0.55, -0.80, -1.02, -1.16)
    lower_path = ([(float(wall(y, 1)), y) for y in lys] + [(0.04, -1.215), (0.0, -1.235), (-0.04, -1.215)] +
                  [(-float(wall(y, -1)), y) for y in lys[::-1]])
    for name, path, parent, zf in (("Gums_Upper", upper_path, sk, lambda x: up_z(x) + 0.015),
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
        if name == "Gums_Upper":                                           # dark-red gum / lip band along the rims,
            radii = [rng.uniform(0.022, 0.040) if abs(p.x) > 0.30 else rng.uniform(0.032, 0.050) for p in dense]
        else:                                                              # thin, uneven: not a bead string
            radii = [rng.uniform(0.024, 0.040) for p in dense]
        D.tube(gb, dense, radii, 0, sides=8, jitter=0.25, frame_ref=(0, 0, 1))
        D.bm_object(name, gb, col, [M["tissue"]], parent=parent)

    bm, layer = D.new_tooth_bm()
    for x, kind, L, w, ax, ay, cu in UPPER_FRONT:              # hang down, crooked, uneven
        base = Vector((x, FRONT_UP + rng.uniform(-0.02, 0.012), up_z(x) - 0.005))
        tusk(bm, layer, base, _tilted((0, -0.10, -1), 0.6 * ax, ay), L * TOOTH_L, w * TOOTH_W, kind,
             curl_dir=(0, 1, 0), curl_amt=cu)
    for sx, teeth in UPPER_SIDES.items():
        for y, kind, L, w, ay in teeth:
            base = Vector((sx * SIDE_UP * taper(y, -0.03), y + rng.uniform(-0.012, 0.012), -0.03))
            tusk(bm, layer, base, _tilted((sx * 0.06, -0.06, -1), rng.uniform(-12, 12), ay),
                 L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-sx, 0.3, 0), curl_amt=rng.uniform(0.06, 0.18))
    D.bm_object("Teeth_Upper", bm, col, [M["teeth"]], parent=sk)

    bm, layer = D.new_tooth_bm()
    for sx, teeth in LOWER_SIDES.items():                      # rise from the V sides, leaning inward
        for y, kind, L, w, ay in teeth:
            yy = y + rng.uniform(-0.012, 0.012)
            base = Vector((sx * float(wall(yy, sx)), yy, 0.065))
            tusk(bm, layer, base, _tilted((-sx * 0.30, 0.40, 1), rng.uniform(-14, 14), ay),
                 L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-sx * 0.5, 1.0, 0), curl_amt=rng.uniform(0.06, 0.18))
    for x, y, kind, L, w in LOWER_CHIN:
        tusk(bm, layer, Vector((x, y, 0.065)), _tilted((-x * 0.8, 0.30, 1), rng.uniform(-9, 9), rng.uniform(-9, 9)),
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
    for how, at, tilt, L in (("top", (0.17, 0.54), (0.20, 0.35, 1.0), 0.09),           # on the crown (side view)
                             ("fixed", (0.34, 0.58, 0.45), (0.60, 0.45, 0.80), 0.07)):  # the back-left corner
        if how == "top":                                 # the highest skull point over this plan position
            d2 = (co[:, 0] - at[0]) ** 2 + (co[:, 1] - at[1]) ** 2
            near = np.flatnonzero(d2 < 0.045 ** 2)
            p = Vector(co[int(near[np.argmax(co[near, 2])]) if len(near) else int(np.argmin(d2))])
        else:                                            # set into the corner's side wall (its root is buried)
            p = Vector(at)
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
