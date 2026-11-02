"""
v5 head (corrective variation of head_openjaw.py, which is kept unchanged), matched to the
approved sheet's three-quarter view: a unified, rounded, damaged cranium (crown over the front
half, sloping down at the back; flush plates with thin cracks and a slight tilt each, recessed
edge chips, pits and a few deep holes; no stacked plates, bolts or protruding fragments),
rectangular void sockets with tiny dim red pupils far inside, naturally tapered conical fangs in
aged ivory, thin dark-red gums and restrained dark tissue only at the hinges and inner edges.
Head size and position and the 72 deg jaw opening are as in head_openjaw.

Cranium-local space, head units (1 unit = HEAD_SCALE metres): origin at the centre of the upper
gum line, front -Y, Z up. The jaw is parented to the cranium and pivots at its own origin.

Jaw: heavy block tapering to a broad U at the chin (sheet front and three-quarter views), carved
mouth floor, knife facets, the broken right side. It hangs from a hinge about two-thirds of the
way back under the skull, dislocated downward, so the chin sits under the face (sheet side view:
chin ~0.5 skull lengths behind the snout) and the opening is tall; it sags a little to its left.
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
U = 0.633                                   # metres per head unit (set by build_head)
HW, HD = 0.92, 0.98
JAW_LEN, JAW_W = 1.02, 0.82
HINGE = Vector((0.0, 0.18, -0.02))          # ~2/3 back under the skull (sheet side view: chin ~0.5 skull lengths behind the snout)
DISLOCATE = Vector((0.0, 0.010, -0.115))    # condyles torn out of their sockets: the jaw hangs lower
# Eye sockets as slanted trapezoids in the face plane (x, z; head units), outer-top, inner-top,
# inner-bottom, outer-bottom: the top edges slope down toward the nose (a scowl, not a stare), the
# monster's right socket is larger and sits a little lower; depth into the skull.
SOCKETS = [([(-0.349, 0.226), (-0.143, 0.204), (-0.147, 0.066), (-0.343, 0.060)], 0.100, 1.10),
           ([(0.317, 0.232), (0.139, 0.212), (0.143, 0.080), (0.311, 0.076)], 0.095, 1.00)]
# (centres 0.235-0.245 from the midline: ~0.55 skull widths apart, as in the sheet's front view;
#  the earlier placement used the nominal width HW, wider than the actual skull)
EYES = [(sum(p[0] for p in q) / 4, sum(p[1] for p in q) / 4, k) for q, _, k in SOCKETS]    # x, z, size


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _m(v):
    """head units -> metres (Surf space)"""
    return np.asarray(v, float) * U


def _zones(zs):
    return [(_m(c), _m(r), s) for c, r, s in zs]


def ledge(S, z0, amp, out, seed, front=None, gap=0.0):
    """Broken strata ledge: everything above a wavy line around the head steps out by `out`
    (crisp, snapped to the line); `gap` breaks it in places; `front` limits it to y < front."""
    nrm = S.normals()
    nh = nrm.copy()
    nh[:, 2] = 0
    nh = SC.unit(nh)
    side = SC.smoothstep(0.35, 0.75, 1 - np.abs(nrm[:, 2]))
    P = SC.Perlin(seed)
    f = S.co[:, 2] - (z0 + amp * SC.fbm(P, S.co * 7.0, 3))
    f = SC.snap_iso(S, f)
    w = (f > 0) * side * SC.smoothstep(-0.8 + gap, 0.2 + gap, SC._z(SC.fbm(P, S.co * 3.5 + 7.7, 2)) + 1.0)
    if front is not None:
        w *= SC.smoothstep(front + 0.04, front - 0.04, S.co[:, 1])
    S.co += (out * w)[:, None] * nh
    S.a["tear"] = np.maximum(S.a["tear"], 0.5 * (np.abs(f) < 0.004) * w)


# ---------------------------------------------------------------------------
# Skull
# ---------------------------------------------------------------------------
SKULL_ROWS = [  # z, +x half-width, -x half-width, front y, back y, exponent - a rounded, domed cranium
    (-0.03, 0.400, 0.412, -0.470, 0.500, 4.2),     # upper jaw
    (0.08, 0.408, 0.419, -0.480, 0.505, 4.4),
    (0.18, 0.413, 0.424, -0.488, 0.498, 4.4),
    (0.26, 0.416, 0.428, -0.493, 0.478, 4.0),      # broad forehead; the back already rounds off
    (0.31, 0.405, 0.417, -0.490, 0.450, 3.4),
    (0.35, 0.385, 0.396, -0.472, 0.412, 3.0),      # the brow rounds over into the dome
    (0.39, 0.350, 0.360, -0.436, 0.362, 2.7),
    (0.43, 0.296, 0.305, -0.374, 0.292, 2.5),
    (0.46, 0.228, 0.236, -0.300, 0.214, 2.3),
    (0.485, 0.150, 0.156, -0.214, 0.116, 2.1),     # crown over the front half; the back slopes down
]

SKULL_DAMAGE = {   # a few shallow torn regions embedded in the shell (no flesh-heavy wounds)
    "peel": [((0.32, -0.14, 0.42), (0.20, 0.22, 0.12), 0.95),     # fracture, upper left
             ((0.43, -0.22, 0.06), (0.05, 0.18, 0.05), 0.9),      # torn mouth corner (left)
             ((-0.44, 0.18, 0.26), (0.09, 0.18, 0.12), 0.8),      # right side, behind the cheek
             ((0.08, 0.48, 0.30), (0.18, 0.08, 0.12), 0.75)],     # back
    "wound": [((0.36, -0.12, 0.41), (0.07, 0.08, 0.05), 1.0)],
}


def build_skull(col, rust):
    keys = [{"p": (0.0, 0.0, z), "ws": ws, "wn": wn, "df": (yb - yf) / 2, "db": (yb - yf) / 2,
             "oy": -(yf + yb) / 2, "e": e} for z, ws, wn, yf, yb, e in SKULL_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=56, step=0.012, caps=(0.03, 0.04))
    sk = SC.obj_from_bm("Cranium", bm, col, [rust])
    SC.remesh(sk, 0.010)
    S = SC.Surf(sk, U)
    S.smooth(4)
    # a broad, fairly flat face under a rounded brow; everything else stays rounded
    SC.flatten(S, _m((0.0, -0.486, 0.12)), _m((0.40, 0.08, 0.15)), (0.0, -1.0, 0.03), 0.7)
    _face(S)
    # controlled asymmetry: a dent in the left brow corner, two old dents in the dome, slight warp
    SC.push(S, _m((0.36, -0.44, 0.31)), _m((0.07, 0.07, 0.05)), -0.010)
    SC.push(S, _m((-0.20, 0.05, 0.44)), _m((0.10, 0.12, 0.06)), -0.008)
    SC.push(S, _m((0.26, 0.24, 0.40)), _m((0.08, 0.10, 0.08)), -0.006)
    SC.warp(S, 0.003, 3.0, 61)
    S = _knife_head(S, sk, 220, 65, 0.0045)                     # low-poly: broad, readable planes
    _sockets(S)
    _palate(S)
    keep = (S.a["socket"] < 0.5) * (S.a["tissue"] < 0.5) * 1.0
    # flush plates separated by visible dark cracks (integrated, not stacked)
    chunk = SV.crack_network(S, cell=0.080, width=0.0025, depth=0.0030, seed=60, w=keep, tilt=0.035)
    SC.damage(S, _zones(SKULL_DAMAGE["peel"]), _zones(SKULL_DAMAGE["wound"]),
              np.array([0.0, 0.0, 1.0]), seed=66, t1=0.008, t2=0.005, tissue=0.010, lips=0.0,
              w=(S.a["socket"] < 0.5) * 1.0, n_flaps=0, chunk=chunk, jag=0.7)
    _chips(S, 67, amount=1.0, bias=-0.42)                       # recessed chips along the edges (broken outline)
    SV.pits(S, per_m2=14, size=(0.016, 0.032), depth=(0.007, 0.012), seed=69, w=keep)   # a few deep holes
    SV.pits(S, per_m2=90, size=(0.007, 0.018), depth=(0.003, 0.007), seed=62, w=keep)
    SV.erode(S, amp=0.0018, freq=11.0, seed=63, w=keep)
    SC.blood(S, 68, drips=6, near=0.03)
    SC.finish(S, sk, decimate_ratio=1.0, sharp_deg=6.0)
    return sk


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
    """Menacing facial structure (approved sheet), built into the form before the knife facets:
    a heavy brow that follows the slanted socket tops down to a V over the nose, a nasal ridge,
    gaunt cheek hollows under the sockets with cheekbones at their outer corners, and a crest
    along the crown."""
    x, y, z = S.co[:, 0] / U, S.co[:, 1] / U, S.co[:, 2] / U
    front = SC.smoothstep(-0.30, -0.42, y)                       # the face, not the sides or back
    d = np.zeros(S.n)
    for quad, _, _ in SOCKETS:
        (ox, oz), (ix, iz) = quad[0], quad[1]
        h, u = _edge_dist(x, z, (ox, oz), (ix, iz))
        band = np.clip(1 - np.abs(h - 0.035) / 0.055, 0, 1) ** 1.3 * (h > -0.01)
        span = SC.smoothstep(-0.12, 0.05, u) * SC.smoothstep(1.18, 0.95, u)
        d = np.maximum(d, 0.030 * band * span)                    # brow ridge over each socket
    # brows meet low over the nose and run down into a nasal ridge
    d = np.maximum(d, 0.034 * np.exp(-(x / 0.10) ** 2 - ((z - 0.185) / 0.05) ** 2))
    d = np.maximum(d, 0.022 * np.exp(-(x / 0.05) ** 2) * SC.smoothstep(0.0, 0.07, z) * SC.smoothstep(0.21, 0.15, z))
    S.co[:, 1] -= d * front * U
    # gaunt hollows under the sockets, cheekbones under their outer corners
    for sx in (-1, 1):
        hollow = np.exp(-((x - sx * 0.10) / 0.05) ** 2 - ((z - 0.03) / 0.05) ** 2)       # beside the nasal ridge
        cheek = np.exp(-((x - sx * 0.39) / 0.04) ** 2 - ((z - 0.03) / 0.04) ** 2)
        S.co[:, 1] += (0.020 * hollow - 0.012 * cheek) * front * U
    # crest along the crown
    # (no crest: the cranium is a smooth dome)


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
            nx, nz = ez / L, -ex / L                              # outward normal (clockwise in x-z)
            if (cx - a[0]) * nx + (cz - a[1]) * nz > 0:
                nx, nz = -nx, -nz
            dist = np.maximum(dist, (x - a[0]) * nx + (z - a[1]) * nz)
        dist = dist + 0.006 * SC.fbm(SC.Perlin(31 + 7 * n_), S.co * 38.0, 2)           # worn rim
        front = S.co[:, 1] < -0.30 * U
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


def _palate(S):
    """Vaulted palate inside the upper gum ridge (seen through the open mouth)."""
    nrm = S.normals()
    bottom = (nrm[:, 2] < -0.45) & (S.co[:, 2] < 0.03 * U)
    g = (np.abs(S.co[:, 0]) / (0.37 * U)) ** 4 + (np.abs(S.co[:, 1] + 0.05 * U) / (0.40 * U)) ** 4
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
JAW_ROWS = [  # y, half-width, up, down, exponent - heavy jaw, tapering to a broad U at the chin (sheet)
    (0.06, 0.385, 0.050, 0.140, 3.0),
    (-0.09, 0.392, 0.055, 0.195, 3.2),
    (-0.34, 0.376, 0.055, 0.255, 3.4),
    (-0.59, 0.342, 0.055, 0.300, 3.4),
    (-0.82, 0.292, 0.055, 0.310, 3.4),
    (-0.955, 0.228, 0.055, 0.280, 3.4),       # tapering to a rounded U at the chin (rounded end cap)
]


def jaw_half(y):
    """Half-width of the lower jaw (head units) at jaw-local y."""
    ys = [r[0] for r in JAW_ROWS][::-1]
    ws = [r[1] for r in JAW_ROWS][::-1]
    return np.interp(y, ys, ws)
JAW_DAMAGE = {
    "peel": [((-0.41, -0.11, -0.10), (0.08, 0.18, 0.14), 1.0),    # broken right side near the hinge
             ((0.06, -1.03, -0.22), (0.10, 0.06, 0.12), 0.85),    # chipped chin
             ((0.0, -0.53, -0.33), (0.20, 0.23, 0.06), 0.7),      # underside
             ((0.29, -0.47, -0.05), (0.06, 0.26, 0.05), 0.7),     # torn along the gum line
             ((-0.23, -0.66, -0.05), (0.06, 0.22, 0.05), 0.65)],
    "wound": [((-0.44, -0.08, -0.08), (0.05, 0.08, 0.08), 1.0)],
}


def jaw_top(x):
    return 0.055


def build_jaw(col, rust, sk, open_deg, roll_deg):
    keys = [{"p": (0.0, y, 0.0), "w": w, "df": up, "db": dn, "e": e} for y, w, up, dn, e in JAW_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=44, step=0.02, caps=(0.05, 0.11))
    for sx in (-1, 1):                                   # rami rising to the condyles
        ramus = SC.loft([{"p": (sx * 0.360, 0.02, -0.14), "w": 0.034, "d": 0.065, "e": 3.0},
                         {"p": (sx * 0.365, 0.01, -0.05), "w": 0.032, "d": 0.058, "e": 3.0},
                         {"p": (sx * 0.370, 0.00, 0.02), "w": 0.036, "d": 0.052, "e": 2.6}],
                        ref=(0, -1, 0), seg=20, step=0.02, caps=(0.02, 0.04))
        SC.merge_bm(bm, ramus)
    jaw = SC.obj_from_bm("Jaw", bm, col, [rust])
    SC.remesh(jaw, 0.011)
    S = SC.Surf(jaw, U)
    S.smooth(3)
    SC.push(S, _m((0.0, -0.70, -0.20)), _m((0.22, 0.08, 0.12)), 0.010)                  # heavy chin
    SC.push(S, _m((-0.43, -0.25, -0.20)), _m((0.06, 0.18, 0.12)), -0.008)
    SC.push(S, _m((0.43, -0.45, -0.18)), _m((0.06, 0.12, 0.10)), 0.006)
    SC.warp(S, 0.006, 3.0, 71)
    SC.dents(S, 5, (0.025, 0.05), (0.003, 0.008), 72)
    S.write()
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
    inner = np.maximum(jaw_half(S.co[:, 1] / U) - 0.10, 0.04) * U          # follows the V taper
    g = (np.abs(S.co[:, 0]) / inner) ** 4 + (np.abs(S.co[:, 1] + 0.465 * U) / (0.490 * U)) ** 4
    f = np.where(top, 1.0 - g, -1.0)
    f = SC.snap_iso(S, f)
    inside = f > 0
    depth = 0.075 * np.clip(f, 0, 1) ** 0.35
    S.co[:, 2] -= depth * inside
    S.a["tissue"] = np.maximum(S.a["tissue"], inside * 1.0)
    S.a["socket"] = 0.8 * inside                                 # deep in the open mouth: near black


def _chips_jaw(S, seed):
    k = S.blur(S.curvature(), 2)
    cv = SC.smoothstep(6.0, 28.0, k)
    gate = SC.smoothstep(0.2, 1.0, SC._z(SC.fbm(SC.Perlin(seed), S.co * 6.0, 2)))
    SC.damage(S, [], [], np.array([1.0, 0.0, 0.0]), seed=seed, t1=0.006, t2=0.003, tissue=0.0, lips=0.0,
              extra=1.4 * cv * gate - 0.35, tear_amt=0.0, w=(S.a["tissue"] < 0.5) * 1.0)


# ---------------------------------------------------------------------------
# Hinges and torn tissue bridging the forced-open wedge
# ---------------------------------------------------------------------------
def hinges_and_tissue(M, col, sk, jaw):
    """Restrained dark tissue: a thin torn web at each hinge (rear of the wedge) and a dark inner
    cheek wall over the rear half of the mouth, so the interior reads dark, not fleshy. No metal
    hinge parts, no tendon strings."""
    jm = jaw.matrix_basis                                   # jaw-local -> cranium-local
    mb = bmesh.new()
    for sx in (-1, 1):                                      # torn web at the hinge
        grid = []
        cols_n, rows_n = 8, 6
        for i in range(cols_n):
            u = i / (cols_n - 1)
            top = Vector((sx * (HW / 2 - 0.025), HINGE.y + 0.10 - u * 0.34, -0.02))
            yj = 0.10 - u * 0.34
            bot = jm @ Vector((sx * (jaw_half(yj) + 0.012), yj, -0.03))
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
    wall_x, cols_n, rows_n = 0.30, 8, 7                         # dark inner cheek walls, rear half only
    for sx in (-1, 1):
        grid = []
        for i in range(cols_n):
            u = i / (cols_n - 1) * 0.55
            top = Vector((sx * wall_x, HINGE.y + 0.02 + u * (-0.300 - HINGE.y - 0.02), -0.02))
            yj = 0.02 + u * (-0.78 - 0.02)
            bot = jm @ Vector((sx * max(jaw_half(yj) - 0.11, 0.05), yj, 0.07))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                p = top.lerp(bot, v)
                sag = math.sin(math.pi * v) * 0.03
                row.append(mb.verts.new(p + Vector((-sx * sag, rng.uniform(-0.006, 0.006), rng.uniform(-0.006, 0.006)))))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                mb.faces.new(q if sx < 0 else tuple(reversed(q)))
    mem = D.bm_object("Mouth_Corner_Tissue", mb, col, [M["flesh"]], parent=sk)
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
    for i in range(8):
        y = -0.36 + i * 0.07
        hw = 0.27 - i * 0.012
        pts = [Vector((x, y + 0.02 * math.sin(x * 9 + i), 0.020)) for x in (-hw, -hw / 2, 0, hw / 2, hw)]
        D.tube(pb, pts, [0.012, 0.02, 0.016, 0.02, 0.012], 0, sides=5, jitter=0.25)
    D.bm_object("Palate", pb, col, [M["gum"]], parent=sk)
    gb = bmesh.new()                                     # rotted tongue lying in the jaw trough
    pts = [Vector((0.02, -0.12, -0.06)), Vector((0.0, -0.30, -0.075)), Vector((-0.03, -0.48, -0.08)),
           Vector((0.02, -0.66, -0.07)), Vector((0.05, -0.80, -0.05))]
    rings = []
    for i, p in enumerate(pts):
        w = (0.15, 0.14, 0.12, 0.10, 0.07)[i]                   # follows the U jaw
        h = (0.06, 0.07, 0.065, 0.05, 0.03)[i]
        rings.append([p + Vector((math.cos(a) * w * rng.uniform(0.85, 1.15), 0,
                                  math.sin(a) * h * rng.uniform(0.8, 1.2)))
                      for a in [2 * math.pi * k / 10 for k in range(10)]])
    D_skin(gb, rings, 0)
    bmesh.ops.recalc_face_normals(gb, faces=gb.faces)
    D.bm_object("Tongue", gb, col, [M["tongue"]], parent=jaw)
    tb = bmesh.new()                                     # ribbed throat receding into the body
    path = [Vector((0, 0.12, -0.03)), Vector((0, 0.22, -0.13)), Vector((0, 0.30, -0.24)), Vector((0, 0.35, -0.34))]
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


def tusk(bm, layer, base, direction, length, width, kind, curl_dir=None):
    """Naturally tapered conical fang (approved sheet): round-ish section, full above the gum,
    narrowing to a sharp point, gently curved toward `curl_dir`. 'snapped' teeth end in a
    tilted fracture. Colour attribute: (t root->tip, blood, decay, tint)."""
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
    curl = c_dir.normalized() * length * rng.uniform(0.07, 0.15)
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


# Explicit, irregular arrangement after the approved sheet: long upper and lower tusks, medium
# crooked ones, short broken ones and stumps; uneven spacing, widths and tilts; all rooted in the
# existing gum lines (no inner row). (x or y along the gum, kind, length, width, tilt about x, about y)
UPPER_FRONT = [(-0.350, "fang", 0.36, 0.084, -4, -12), (-0.300, "fang", 0.56, 0.101, 5, 6),
               (-0.243, "snapped", 0.42, 0.090, 0, 3), (-0.196, "fang", 0.46, 0.081, -8, -9),
               (-0.132, "fang", 0.60, 0.105, 3, 4), (-0.066, "fang", 0.40, 0.084, 7, -10),
               (0.010, "fang", 0.50, 0.092, -5, 12), (0.078, "fang", 0.62, 0.106, 4, -5),
               (0.140, "snapped", 0.34, 0.087, 0, 2), (0.192, "fang", 0.44, 0.081, 9, 14),
               (0.254, "fang", 0.56, 0.098, -5, -8), (0.328, "fang", 0.40, 0.087, 6, 10)]
UPPER_SIDES = {1: [(-0.24, "fang", 0.40, 0.090), (0.04, "fang", 0.30, 0.078)],
               -1: [(-0.22, "fang", 0.36, 0.084), (0.02, "snapped", 0.30, 0.081)]}
# lower teeth line both sides of the V-shaped jaw (y along the jaw) and meet at the chin;
# shorter near the hinge, longest toward the chin
LOWER_SIDES = {1: [(-0.22, "fang", 0.28, 0.078), (-0.36, "fang", 0.42, 0.087), (-0.49, "snapped", 0.44, 0.090),
                   (-0.61, "fang", 0.56, 0.101), (-0.73, "fang", 0.44, 0.084), (-0.84, "fang", 0.52, 0.095)],
               -1: [(-0.24, "fang", 0.32, 0.081), (-0.38, "fang", 0.40, 0.084), (-0.51, "fang", 0.58, 0.104),
                    (-0.63, "fang", 0.44, 0.087), (-0.74, "snapped", 0.40, 0.087), (-0.85, "fang", 0.50, 0.092)]}
# across the front of the U (x, y): long ones at the chin
LOWER_CHIN = [(0.115, -0.944, "fang", 0.50, 0.092), (-0.010, -0.968, "fang", 0.44, 0.095),
              (-0.125, -0.938, "fang", 0.54, 0.098)]


TOOTH_W, TOOTH_L = 0.96, 0.90       # full cones, a little shorter than the tables (three-quarter match)


def _tilted(d, ax, ay):
    return Matrix.Rotation(math.radians(ay), 3, 'Y') @ (Matrix.Rotation(math.radians(ax), 3, 'X') @ Vector(d))


def gums_and_teeth(M, col, sk, jaw):
    front_up = -0.468 + 0.085
    side_up = HW / 2 - 0.125                                                # teeth row ~0.7-0.8 of the skull width (sheet)
    row_k = 0.88                                                            # front teeth drawn in from the corners
    up_z = lambda x: -0.025 - 0.045 * (abs(x) / 0.36) ** 2                  # gum line arches down at the corners
    wall = lambda y: jaw_half(y) - 0.065                                    # lower gum follows the V
    upper_path = ([(side_up, y) for y in (0.28, -0.10)] +
                  [(x, front_up) for x in (HW / 2 - 0.16, 0.20, 0.05, -0.11, -0.25, -HW / 2 + 0.16)] +
                  [(-side_up, y) for y in (-0.10, 0.28)])
    lys = (-0.06, -0.25, -0.45, -0.65, -0.80)
    lower_path = ([(float(wall(y)), y) for y in lys] + [(0.125, -0.930), (0.0, -0.962), (-0.125, -0.930)] +
                  [(-float(wall(y)), y) for y in lys[::-1]])
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
    for x, kind, L, w, ax, ay in UPPER_FRONT:                  # hang down, crooked, uneven
        x = x * row_k
        base = Vector((x, front_up + rng.uniform(-0.02, 0.012), up_z(x) - 0.005))
        tusk(bm, layer, base, _tilted((0, -0.08, -1), 0.6 * ax, ay), L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(0, 1, 0))
    for sx, teeth in UPPER_SIDES.items():
        for y, kind, L, w in teeth:
            base = Vector((sx * side_up, y + rng.uniform(-0.012, 0.012), -0.03))
            tusk(bm, layer, base, _tilted((sx * 0.04, -0.05, -1), rng.uniform(-6, 6), rng.uniform(-6, 6)),
                 L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-sx, 0.3, 0))
    D.bm_object("Teeth_Upper", bm, col, [M["teeth"]], parent=sk)

    bm, layer = D.new_tooth_bm()
    for sx, teeth in LOWER_SIDES.items():                      # rise from the V sides, leaning inward
        for y, kind, L, w in teeth:
            yy = y + rng.uniform(-0.012, 0.012)
            base = Vector((sx * float(wall(yy)), yy, 0.065))
            tusk(bm, layer, base, _tilted((-sx * 0.16, 1.05, 1), rng.uniform(-7, 7), rng.uniform(-7, 7)),
                 L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-sx * 0.5, 1.0, 0))
    for x, y, kind, L, w in LOWER_CHIN:
        tusk(bm, layer, Vector((x, y, 0.065)), _tilted((-x * 0.6, 1.05, 1), rng.uniform(-8, 8), rng.uniform(-8, 8)),
             L * TOOTH_L, w * TOOTH_W, kind, curl_dir=(-x, 1, -0.3))
    D.bm_object("Teeth_Lower", bm, col, [M["teeth"]], parent=jaw)


def eyes(M, col, sk):
    ebm = bmesh.new()
    for ex, ez, k in EYES:
        # deepest point of the socket floor, found on the sculpted mesh
        me = sk.data
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        sock = SC.get_attr(me, "socket") > 0.5
        tx, tz = ex, ez + 0.01                           # centre of the void, at its back wall
        d = (co[:, 0] - tx) ** 2 + (co[:, 2] - tz) ** 2
        d[~sock] = 1e9
        i = int(np.argmin(d))
        c = Vector(co[i]) + Vector((0, -0.006, 0))
        r = 0.0045 / U * k                               # ~9 mm: a tiny point far inside the void
        bmesh.ops.create_icosphere(ebm, subdivisions=1, radius=r, matrix=Matrix.Translation(c))
    D.bm_object("Eyes", ebm, col, [M["eye"]], parent=sk)


def crown_bracket(col, mat, sk):
    """Two small rusted knobs on the dome (sheet)."""
    me = sk.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    bm = bmesh.new()
    for hint, tilt, L in (((0.30, -0.22, 0.42), (0.5, -0.2, 1.0), 0.07), ((-0.28, -0.06, 0.45), (-0.5, 0.1, 1.0), 0.06)):
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


def build_head(M, col, location, rotation, open_deg, roll_deg, scale=0.60):
    global U
    U = scale
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
