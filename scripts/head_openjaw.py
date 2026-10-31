"""
Head of the OUT THERE monster after the ASTRA R08 - MORE OPEN JAW sheet: the compact R08 skull
with the lower jaw broken open much further - hinged at the rear of the skull, as long as the
skull is deep - and a mouth crowded with long, crooked, faceted fangs.

Cranium-local space, head units (1 unit = HEAD_SCALE metres): origin at the centre of the upper
gum line, front -Y, Z up. The jaw is parented to the cranium and pivots at its own origin.

Skull: compact, asymmetric rounded block (front flatter, crown narrower, back rounded),
irregular broken strata ledges (crown cap, brow over the sockets), dents and warps, large knife
facets, deep square sockets with tiny red eyes, a vaulted palate, a big fracture on the upper
left exposing the rust strata and tissue, structural damage on the back and right side.
Jaw: heavy U-shaped block with rami and condyles, carved mouth floor, knife facets, the broken
right side, chipped chin. It hangs from a dislocated hinge: the condyles have slid down out of
their sockets, so the drop is larger than a clean rotation and torn tissue bridges the gap.
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import monster_detail as D
import sculpt as SC

rng = random.Random(77)
U = 0.633                                   # metres per head unit (set by build_head)
HW, HD = 0.92, 0.98
JAW_LEN, JAW_W = 1.02, 0.82
HINGE = Vector((0.0, 0.40, -0.02))          # at the rear of the skull (the head is thrust ahead)
DISLOCATE = Vector((0.0, 0.010, -0.030))    # condyles torn out of their sockets
EYES = [(-0.225, 0.185, 1.10), (0.215, 0.175, 1.00)]    # x, z, size


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
SKULL_ROWS = [  # z, +x half-width, -x half-width (monster's right fuller), front y, back y, exponent
    # angular wedge (approved sheet): tall at the back, the top slopes down to a hard brow edge that
    # overhangs a steep flat front face; cheeks narrow toward the upper jaw. Same size as before.
    (-0.03, 0.400, 0.412, -0.470, 0.500, 6.0),     # upper jaw
    (0.08, 0.416, 0.428, -0.480, 0.505, 6.5),
    (0.18, 0.430, 0.442, -0.488, 0.508, 6.5),      # cheeks widen toward the brow
    (0.26, 0.438, 0.450, -0.495, 0.506, 6.5),
    (0.31, 0.442, 0.454, -0.530, 0.502, 6.0),      # brow edge, widest, overhanging the sockets
    (0.345, 0.430, 0.441, -0.440, 0.494, 5.5),     # top face begins, sloping back
    (0.40, 0.410, 0.420, -0.240, 0.478, 5.0),
    (0.45, 0.376, 0.385, -0.040, 0.450, 4.5),
    (0.49, 0.322, 0.330, 0.100, 0.400, 4.0),
    (0.515, 0.250, 0.256, 0.180, 0.330, 3.5),      # crown, toward the back
]

SKULL_DAMAGE = {   # fewer, larger, cohesive sections
    "peel": [((0.34, -0.14, 0.43), (0.24, 0.26, 0.15), 1.0),      # big fracture, upper left
             ((0.44, -0.05, 0.28), (0.09, 0.22, 0.16), 0.95),
             ((0.44, -0.22, 0.05), (0.06, 0.22, 0.05), 1.0),      # torn mouth corner (left), along the mouth line
             ((-0.45, 0.18, 0.28), (0.10, 0.20, 0.15), 0.85),     # right side, behind the cheek
             ((0.08, 0.50, 0.33), (0.20, 0.08, 0.13), 0.8),       # back
             ((-0.30, -0.50, 0.31), (0.09, 0.05, 0.05), 0.7)],    # brow chip
    "wound": [((0.38, -0.12, 0.42), (0.12, 0.14, 0.09), 1.0),
              ((0.45, -0.10, 0.30), (0.05, 0.10, 0.08), 1.0),
              ((0.45, -0.22, 0.04), (0.04, 0.16, 0.035), 1.0)],
}


def build_skull(col, rust):
    keys = [{"p": (0.0, 0.0, z), "ws": ws, "wn": wn, "df": (yb - yf) / 2, "db": (yb - yf) / 2,
             "oy": -(yf + yb) / 2, "e": e} for z, ws, wn, yf, yb, e in SKULL_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=56, step=0.012, caps=(0.03, 0.04))
    sk = SC.obj_from_bm("Cranium", bm, col, [rust])
    SC.remesh(sk, 0.010)
    S = SC.Surf(sk, U)
    S.smooth(3)
    # big planes cut with flat trims: flat front face under the brow, sloping top, cheek planes
    # that narrow down into the upper jaw, a hard brow ridge
    SC.flatten(S, _m((0.0, -0.486, 0.12)), _m((0.40, 0.08, 0.15)), (0.0, -1.0, 0.03), 0.95)
    SC.flatten(S, _m((0.0, -0.10, 0.452)), _m((0.36, 0.44, 0.08)), (0.03, -0.30, 1.0), 0.85)
    for sx in (-1, 1):
        SC.flatten(S, _m((sx * 0.430, -0.28, 0.08)), _m((0.06, 0.24, 0.15)), (sx * 1.0, -0.22, -0.20), 0.85)
        SC.flatten(S, _m((sx * 0.440, 0.10, 0.36)), _m((0.06, 0.30, 0.08)), (sx * 1.0, 0.0, 0.55), 0.7)
    SC.push(S, _m((0.0, -0.51, 0.305)), _m((0.40, 0.04, 0.03)), 0.008)              # brow ridge
    # controlled asymmetry: a chunk broken off the left brow corner, two old dents, slight warp
    SC.flatten(S, _m((0.40, -0.48, 0.33)), _m((0.08, 0.08, 0.06)), (0.6, -0.6, 0.55), 1.0)
    SC.push(S, _m((-0.20, 0.05, 0.47)), _m((0.10, 0.12, 0.06)), -0.008)
    SC.push(S, _m((0.30, 0.25, 0.40)), _m((0.08, 0.10, 0.08)), -0.006)
    SC.warp(S, 0.003, 3.0, 61)
    S = _knife_head(S, sk, 170, 65, 0.0045)
    _sockets(S)
    _palate(S)
    chunk = SC.flakes(S, cell=0.06, crack=0.003, depth=0.004, lift=0.0045, tilt=0.10, seed=60,
                      w=(S.a["socket"] < 0.5) * (S.a["tissue"] < 0.5) * 1.0)
    SC.damage(S, _zones(SKULL_DAMAGE["peel"]), _zones(SKULL_DAMAGE["wound"]),
              np.array([0.0, 0.0, 1.0]), seed=66, t1=0.012, t2=0.009, tissue=0.014, lips=0.003,
              w=(S.a["socket"] < 0.5) * 1.0, n_flaps=4, chunk=chunk, jag=0.9)
    _chips(S, 67)
    SC.blood(S, 68, drips=10, near=0.035)
    SC.finish(S, sk, decimate_ratio=1.0, sharp_deg=6.0)
    SC.add_flaps(sk, getattr(S, "flaps", []), 69, unit_=U)
    return sk


def _knife_head(S, ob, faces, seed, jitter):
    S.write()
    SC.lowpoly(ob, faces, jitter=jitter / U, seed=seed, dissolve_deg=4.0, levels=1, remesh_after=0.0050 / U)
    S = SC.Surf(ob, U)
    S.a["socket"] = np.zeros(S.n)
    return S


def _sockets(S):
    """Deep square sockets pushed straight back into the face (crisp, snapped walls)."""
    sock = np.zeros(S.n)
    for ex, ez, k in EYES:
        a, b = 0.082 * k * U, 0.070 * k * U
        dx = (S.co[:, 0] - ex * U) / a
        dz = (S.co[:, 2] - ez * U) / b
        r = np.abs(dx) ** 4.5 + np.abs(dz) ** 4.5
        r = r + 0.22 * SC.fbm(SC.Perlin(int(abs(ex) * 1000) + 5), S.co * 40.0, 2)       # chipped rim
        front = S.co[:, 1] < -0.30 * U
        f = np.where(front, 1.0 - r, -1.0)
        f = SC.snap_iso(S, f)
        inside = f > 0
        depth = 0.050 + 0.006 * np.clip(1 - r, 0, 1)
        S.co[inside, 1] += depth[inside]
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


def _chips(S, seed):
    k = S.blur(S.curvature(), 2)
    cv = SC.smoothstep(6.0, 28.0, k)
    gate = SC.smoothstep(0.2, 1.0, SC._z(SC.fbm(SC.Perlin(seed), S.co * 6.0, 2)))
    SC.damage(S, [], [], np.array([0.0, 0.0, 1.0]), seed=seed, t1=0.006, t2=0.003, tissue=0.0, lips=0.0,
              extra=0.6 * cv * gate - 0.6, tear_amt=0.0, w=(S.a["socket"] < 0.5) * 1.0)   # few, localized chips


# ---------------------------------------------------------------------------
# Jaw
# ---------------------------------------------------------------------------
JAW_ROWS = [  # y, half-width, up, down, exponent - heavy jaw, thickest at the chin
    (0.06, 0.380, 0.050, 0.140, 3.0),
    (-0.09, 0.400, 0.055, 0.195, 3.2),
    (-0.34, 0.405, 0.055, 0.255, 3.4),
    (-0.59, 0.390, 0.055, 0.305, 3.4),
    (-0.80, 0.350, 0.055, 0.325, 3.2),
    (-0.945, 0.270, 0.055, 0.300, 3.0),       # narrower, heavy chin (V-shaped jaw from the front)
]
JAW_DAMAGE = {
    "peel": [((-0.41, -0.11, -0.10), (0.08, 0.18, 0.14), 1.0),    # broken right side near the hinge
             ((0.10, -1.00, -0.22), (0.14, 0.06, 0.12), 0.85),    # chipped chin
             ((0.0, -0.53, -0.33), (0.20, 0.23, 0.06), 0.7),      # underside
             ((0.41, -0.47, -0.05), (0.06, 0.26, 0.05), 0.7),     # torn along the gum line
             ((-0.40, -0.66, -0.05), (0.06, 0.22, 0.05), 0.65)],
    "wound": [((-0.44, -0.08, -0.08), (0.05, 0.08, 0.08), 1.0)],
}


def jaw_top(x):
    return 0.055


def build_jaw(col, rust, sk, open_deg, roll_deg):
    keys = [{"p": (0.0, y, 0.0), "w": w, "df": up, "db": dn, "e": e} for y, w, up, dn, e in JAW_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=44, step=0.02, caps=(0.05, 0.08))
    for sx in (-1, 1):                                   # rami rising to the condyles
        ramus = SC.loft([{"p": (sx * 0.395, 0.02, -0.14), "w": 0.045, "d": 0.075, "e": 3.0},
                         {"p": (sx * 0.405, 0.01, -0.05), "w": 0.042, "d": 0.065, "e": 3.0},
                         {"p": (sx * 0.410, 0.00, 0.02), "w": 0.050, "d": 0.060, "e": 2.6}],
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
    SC.lowpoly(jaw, 330, jitter=0.0045 / U, seed=73, dissolve_deg=4.0, levels=1, remesh_after=0.0050 / U)
    S = SC.Surf(jaw, U)
    _trough(S)
    chunk = SC.flakes(S, cell=0.045, seed=70, w=(S.a["tissue"] < 0.5) * 1.0)
    SC.damage(S, _zones(JAW_DAMAGE["peel"]), _zones(JAW_DAMAGE["wound"]), np.array([1.0, 0.0, 0.0]),
              seed=74, t1=0.011, t2=0.008, tissue=0.012, lips=0.005, w=(S.a["tissue"] < 0.5) * 1.0,
              n_flaps=3, chunk=chunk)
    S.a_socket_final = np.zeros(S.n)
    _chips_jaw(S, 75)
    rot = Matrix.Rotation(math.radians(open_deg), 3, 'X')
    down_local = rot.inverted() @ Vector((0, 0, -1))
    SC.blood(S, 76, drips=10, near=0.03, down=tuple(down_local))
    SC.finish(S, jaw, decimate_ratio=1.0, sharp_deg=6.0)
    SC.add_flaps(jaw, getattr(S, "flaps", []), 77, unit_=U)
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
    g = (np.abs(S.co[:, 0]) / (0.28 * U)) ** 4 + (np.abs(S.co[:, 1] + 0.44 * U) / (0.46 * U)) ** 4
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
    jm = jaw.matrix_basis                                   # jaw-local -> cranium-local
    bm = bmesh.new()
    for sx in (-1, 1):
        broken = sx < 0
        sock_c = HINGE + Vector((sx * (HW / 2 - 0.01), 0, 0))           # empty socket on the skull
        cond_c = jm @ Vector((sx * 0.42, 0.0, 0.02))                    # dislocated condyle
        for c, r0, mat in ((sock_c, 0.085, 1), (cond_c, 0.070, 0)):
            ring = []
            for k in range(9):
                ang = 2 * math.pi * k / 9 + 0.3
                r = r0 * rng.uniform(0.85, 1.1)
                ring.append(Vector((0, math.cos(ang) * r, math.sin(ang) * r)))
            x0, x1 = (0.0, 0.06)
            p0 = [c + Vector((sx * x0, p.y, p.z)) for p in ring]
            p1 = [c + Vector((sx * x1, p.y * 0.86, p.z * 0.86)) for p in ring]
            D_skin(bm, [p0, p1] if sx > 0 else [p1, p0], mat)
        # hinge pin torn out: bent, still jammed in the condyle, pointing at its socket
        a = cond_c + Vector((sx * 0.03, 0, 0))
        b = sock_c + Vector((sx * 0.05, -0.02, -0.03))
        pin = [a, a.lerp(b, 0.5) + Vector((sx * 0.04, 0.0, 0.0)), b if not broken else a.lerp(b, 0.75)]
        rings = [[p + Vector((0, math.cos(t) * 0.02, math.sin(t) * 0.02)) for t in
                  (0, math.pi / 2, math.pi, 1.5 * math.pi)] for p in pin]
        D_skin(bm, rings, 2)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    D.bm_object("Jaw_Hinges", bm, col, [M["rust"], M["under"], M["bar"]], parent=sk)

    # stretched, torn cheek membranes at the rear of the wedge (with tension wrinkles)
    mb = bmesh.new()
    cols_n, rows_n = 9, 7
    for sx in (-1, 1):
        grid = []
        for i in range(cols_n):
            u = i / (cols_n - 1)
            top = Vector((sx * (HW / 2 - 0.06), HINGE.y + 0.03 - u * 0.50, -0.01))
            bot = jm @ Vector((sx * (JAW_W / 2 - 0.05), 0.03 - u * 0.47, 0.03))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                p = top.lerp(bot, v)
                wr = math.sin(math.pi * v) * (0.020 if i % 2 else -0.013)
                p += Vector((sx * wr, 0, 0)) + Vector((rng.uniform(-0.006, 0.006), rng.uniform(-0.01, 0.01), 0))
                row.append(mb.verts.new(p))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                if i == cols_n - 2 and 0 < j < rows_n - 2 and rng.random() < 0.75:
                    continue                                   # torn leading edge
                if i >= 3 and rng.random() < 0.25:
                    continue                                   # holes
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                mb.faces.new(q if sx > 0 else tuple(reversed(q)))
    # inner mouth walls (sheet): wet tissue stretched between the upper and lower gum lines just
    # inside the side teeth, from the hinge to behind the front teeth, so the forced-open mouth reads
    # as a red cavity in profile (not see-through); a few tears near the rear
    wall_x, cols_n, rows_n = 0.30, 11, 8
    for sx in (-1, 1):
        grid = []
        for i in range(cols_n):
            u = i / (cols_n - 1)
            top = Vector((sx * wall_x, HINGE.y + 0.02 + u * (-0.300 - HINGE.y - 0.02), -0.02))
            bot = jm @ Vector((sx * wall_x, 0.02 + u * (-0.78 - 0.02), 0.07))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                p = top.lerp(bot, v)
                sag = math.sin(math.pi * v) * (0.035 + 0.02 * math.sin(7.0 * u + 1.3 * sx))      # bulges into the mouth
                p += Vector((-sx * sag, rng.uniform(-0.008, 0.008), rng.uniform(-0.008, 0.008)))
                row.append(mb.verts.new(p))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                if i < 3 and 1 < j < rows_n - 2 and rng.random() < 0.18:
                    continue                                   # a few tears near the hinge
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                mb.faces.new(q if sx < 0 else tuple(reversed(q)))
    mem = D.bm_object("Mouth_Corner_Tissue", mb, col, [M["flesh"]], parent=sk)
    sol = mem.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.02
    D.apply_modifiers(mem)

    # taut tendons straining across the wedge (one snapped per side), and strings of tissue
    tb = bmesh.new()
    for sx in (-1, 1):
        for i, (ty, by) in enumerate(((-0.08, -0.12), (-0.22, -0.29), (-0.36, -0.45), (-0.50, -0.62))):
            top = Vector((sx * (HW / 2 - 0.07), HINGE.y + ty + rng.uniform(-0.02, 0.02), -0.01))
            bot = jm @ Vector((sx * (JAW_W / 2 - 0.07), by + rng.uniform(-0.03, 0.03), 0.04))
            snapped = i == (1 if sx > 0 else 2)
            pts, radii = [], []
            for k in range(7):
                t = k / 6
                if snapped and t > 0.5:
                    break
                sag = 0.014 * math.sin(math.pi * t) if not snapped else 0.07 * t * t
                pts.append(top.lerp(bot, t) + Vector((sx * 0.012 * math.sin(math.pi * t), -sag * 0.3, -sag)))
                radii.append(rng.uniform(0.016, 0.026) * (1.0 - 0.5 * math.sin(math.pi * t)))
            if snapped:
                radii[-1] *= 0.35
            D.tube(tb, pts, radii, 0, sides=6, jitter=0.2)
    D.bm_object("Mouth_Tendons", tb, col, [M["flesh"]], parent=sk)


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
        w = (0.15, 0.15, 0.13, 0.11, 0.06)[i]
        h = (0.06, 0.07, 0.065, 0.05, 0.03)[i]
        rings.append([p + Vector((math.cos(a) * w * rng.uniform(0.85, 1.15), 0,
                                  math.sin(a) * h * rng.uniform(0.8, 1.2)))
                      for a in [2 * math.pi * k / 10 for k in range(10)]])
    D_skin(gb, rings, 0)
    bmesh.ops.recalc_face_normals(gb, faces=gb.faces)
    D.bm_object("Tongue", gb, col, [M["tongue"]], parent=jaw)
    tb = bmesh.new()                                     # ribbed throat receding into the body
    path = [Vector((0, 0.30, -0.02)), Vector((0, 0.42, -0.14)), Vector((0, 0.52, -0.30)), Vector((0, 0.60, -0.46))]
    rings = []
    for i, p in enumerate(path):
        for sub in range(3):
            if i == len(path) - 1 and sub:
                break
            q = p if i == len(path) - 1 else p.lerp(path[i + 1], sub / 3)
            r = (0.29 - 0.05 * (i + sub / 3)) * (1.0 if sub % 2 == 0 else 0.86)
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
    """Thick, carved conical tusk (approved sheet): fluted section (ridges and grooves running
    along the tooth), wide root tapering to a point, curling toward `curl_dir` (into the mouth).
    'snapped' / 'stump' end in a tilted fracture plane; 'chipped' has a corner knocked off the
    tip. Colour attribute: (t root->tip, blood, decay, tint)."""
    d = Vector(direction).normalized()
    side = Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, d) @ d.orthogonal().normalized()
    fwd = d.cross(side).normalized()
    depth = width * rng.uniform(0.80, 0.95)
    n = 2 * rng.choice([5, 6, 6, 7])                             # ridge / groove pairs
    prof = [(math.cos(2 * math.pi * k / n) * (1.0 if k % 2 == 0 else 0.86) * rng.uniform(0.94, 1.05) * width / 2,
             math.sin(2 * math.pi * k / n) * (1.0 if k % 2 == 0 else 0.86) * rng.uniform(0.94, 1.05) * depth / 2)
            for k in range(n)]
    c_dir = Vector(curl_dir) if curl_dir is not None else side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)
    c_dir = (c_dir - d * c_dir.dot(d)).normalized() + (side * rng.uniform(-0.3, 0.3))
    curl = c_dir.normalized() * length * rng.uniform(0.10, 0.20)
    cut = {"fang": 1.0, "chipped": 1.0, "snapped": rng.uniform(0.5, 0.72), "stump": rng.uniform(0.24, 0.38)}[kind]
    taper = [(-0.18, 0.86), (0.0, 1.0), (0.15, 0.95), (0.32, 0.84), (0.5, 0.69), (0.68, 0.52), (0.84, 0.33),
             (0.95, 0.17)]
    ts = [(t, sc) for t, sc in taper if t < cut - 0.03]
    if cut < 1.0:
        ts.append((cut, float(np.interp(cut, [t for t, _ in taper], [sc for _, sc in taper]))))
    blood = min(1.0, rng.choice([0.0, 0.25, 0.4, 0.55, 0.75]) * rng.uniform(0.7, 1.2))
    decay, tint = rng.random() ** 1.6, rng.random()
    rings = []
    for t, sc in ts:
        c = Vector(base) + d * length * t + curl * max(t, 0.0) ** 2
        rings.append([c + side * x * sc + fwd * y * sc for x, y in prof])
    if cut < 1.0:                                               # fracture plane, tilted
        tilt = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)).normalized()
        c = Vector(base) + d * length * cut + curl * cut ** 2
        rings[-1] = [p + d * (p - c).dot(tilt) * rng.uniform(0.6, 1.2) for p in rings[-1]]
    verts = []
    for (t, _), ring in zip(ts, rings):
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
    apex = Vector(base) + d * length + curl
    if kind == "chipped":                                       # a corner knocked off the tip
        apex = apex - d * length * 0.07 + side * width * 0.18
    a = bm.verts.new(apex)
    a[layer] = (1.0, blood, decay, tint)
    for i in range(n):
        bm.faces.new((verts[-1][i], verts[-1][(i + 1) % n], a))


# Explicit, irregular arrangement after the approved sheet: long upper and lower tusks, medium
# crooked ones, short broken ones and stumps; uneven spacing, widths and tilts; all rooted in the
# existing gum lines (no inner row). (x or y along the gum, kind, length, width, tilt about x, about y)
UPPER_FRONT = [(-0.335, "fang", 0.42, 0.094, -6, 6), (-0.285, "fang", 0.56, 0.122, 3, 5),
               (-0.228, "snapped", 0.50, 0.106, 0, 0), (-0.180, "fang", 0.52, 0.112, -5, 9),
               (-0.125, "fang", 0.58, 0.131, 4, -3), (-0.065, "stump", 0.40, 0.100, 0, 0),
               (-0.015, "fang", 0.58, 0.135, -2, 4), (0.042, "chipped", 0.46, 0.098, 8, -5),
               (0.098, "fang", 0.56, 0.125, 5, 7), (0.150, "fang", 0.50, 0.110, -8, -4),
               (0.205, "snapped", 0.52, 0.106, 4, 2), (0.258, "fang", 0.54, 0.120, -4, 8),
               (0.318, "fang", 0.42, 0.098, 8, 0)]
UPPER_SIDES = {1: [(-0.26, "fang", 0.40, 0.106), (-0.14, "snapped", 0.34, 0.098), (-0.02, "fang", 0.34, 0.092),
                   (0.12, "stump", 0.24, 0.090)],
               -1: [(-0.25, "fang", 0.44, 0.110), (-0.12, "fang", 0.30, 0.090), (0.00, "stump", 0.26, 0.095),
                    (0.13, "snapped", 0.28, 0.090)]}
LOWER_FRONT = [(-0.305, "fang", 0.46, 0.098, 8, -6), (-0.250, "fang", 0.56, 0.119, -5, 9),
               (-0.195, "stump", 0.36, 0.100, 0, 0), (-0.140, "fang", 0.58, 0.128, 6, -4),
               (-0.085, "chipped", 0.48, 0.098, -10, 7), (-0.030, "fang", 0.54, 0.115, 4, -9),
               (0.025, "snapped", 0.54, 0.106, 8, 3), (0.080, "fang", 0.58, 0.130, -6, 6),
               (0.135, "fang", 0.52, 0.110, 10, -7), (0.190, "stump", 0.34, 0.098, 0, 0),
               (0.245, "fang", 0.56, 0.117, -8, 10), (0.300, "fang", 0.46, 0.095, 6, -5)]
LOWER_SIDES = {1: [(-0.74, "fang", 0.40, 0.110), (-0.60, "snapped", 0.40, 0.100), (-0.46, "fang", 0.40, 0.098),
                   (-0.32, "stump", 0.24, 0.092), (-0.20, "fang", 0.30, 0.088)],
               -1: [(-0.73, "fang", 0.40, 0.106), (-0.58, "fang", 0.40, 0.110), (-0.44, "stump", 0.26, 0.092),
                    (-0.30, "snapped", 0.34, 0.092), (-0.18, "fang", 0.28, 0.085)]}


def _tilted(d, ax, ay):
    return Matrix.Rotation(math.radians(ay), 3, 'Y') @ (Matrix.Rotation(math.radians(ax), 3, 'X') @ Vector(d))


def gums_and_teeth(M, col, sk, jaw):
    wall = JAW_W / 2 - 0.065
    front_up = -0.468 + 0.085
    side_up = HW / 2 - 0.08
    upper_path = ([(side_up, y) for y in (0.28, -0.10)] +
                  [(x, front_up) for x in (HW / 2 - 0.12, 0.22, 0.05, -0.12, -0.28, -HW / 2 + 0.12)] +
                  [(-side_up, y) for y in (-0.10, 0.28)])
    front_lo = -JAW_LEN + 0.085
    lo_front = lambda x: front_lo + 0.16 * (abs(x) / wall) ** 2              # V-shaped chin
    lower_path = ([(wall, y) for y in (-0.08, -0.80)] +
                  [(x, lo_front(x)) for x in (wall * 0.62, 0.12, 0.0, -0.12, -wall * 0.62)] +
                  [(-wall, y) for y in (-0.80, -0.08)])
    for name, path, parent, z in (("Gums_Upper", upper_path, sk, -0.025), ("Gums_Lower", lower_path, jaw, 0.06)):
        gb = bmesh.new()
        dense = []
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.04))
            for st in range(steps):
                t = st / steps
                dense.append(Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z)))
        dense.append(Vector((path[-1][0], path[-1][1], z)))
        radii = [rng.uniform(0.046, 0.072) for _ in dense]                   # thick, swollen
        D.tube(gb, dense, radii, 0, sides=8, jitter=0.25, frame_ref=(0, 0, 1))
        for p in dense[::2]:
            bmesh.ops.create_icosphere(gb, subdivisions=2, radius=rng.uniform(0.026, 0.042),
                                       matrix=Matrix.Translation(p + Vector((rng.uniform(-0.03, 0.03),
                                                                             rng.uniform(-0.03, 0.03),
                                                                             rng.uniform(-0.02, 0.02))))
                                       @ Matrix.Diagonal((1.3, 1.0, 0.7, 1)))
        D.bm_object(name, gb, col, [M["gum"]], parent=parent)

    bm, layer = D.new_tooth_bm()
    for x, kind, L, w, ax, ay in UPPER_FRONT:                  # hang down, slightly forward
        base = Vector((x, front_up + 0.004 + rng.uniform(-0.01, 0.01), -0.03))
        tusk(bm, layer, base, _tilted((0, -0.12, -1), 0.6 * ax, ay), L, w, kind, curl_dir=(0, 1, 0))
    for sx, teeth in UPPER_SIDES.items():
        for y, kind, L, w in teeth:
            base = Vector((sx * side_up, y + rng.uniform(-0.012, 0.012), -0.03))
            tusk(bm, layer, base, _tilted((sx * 0.06, -0.05, -1), rng.uniform(-6, 6), rng.uniform(-6, 6)), L, w, kind,
                 curl_dir=(-sx, 0.3, 0))
    D.bm_object("Teeth_Upper", bm, col, [M["teeth"]], parent=sk)

    bm, layer = D.new_tooth_bm()
    for x, kind, L, w, ax, ay in LOWER_FRONT:                  # rise up and slightly forward once forced open
        base = Vector((x, lo_front(x) + 0.004 + rng.uniform(-0.01, 0.01), 0.065))
        tusk(bm, layer, base, _tilted((0, 0.9, 1), ax, ay), L, w, kind, curl_dir=(0, 1, -0.3))
    for sx, teeth in LOWER_SIDES.items():
        for y, kind, L, w in teeth:
            base = Vector((sx * wall, y + rng.uniform(-0.012, 0.012), 0.065))
            tusk(bm, layer, base, _tilted((-sx * 0.06, 1.0, 1), rng.uniform(-6, 6), rng.uniform(-6, 6)), L, w, kind,
                 curl_dir=(-sx, 0.6, 0))
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
        d = (co[:, 0] - ex) ** 2 + (co[:, 2] - ez) ** 2
        d[~sock] = 1e9
        i = int(np.argmin(d))
        c = Vector(co[i]) + Vector((0, -0.010, 0))
        r = 0.0075 * k                                   # tiny red point deep in the socket
        bmesh.ops.create_cube(ebm, size=2 * r, matrix=Matrix.Translation(c))
    D.bm_object("Eyes", ebm, col, [M["eye"]], parent=sk)


def crown_bracket(col, mat, sk):
    """Three short rusted knobs/spikes: the two top corners of the skull and the back (sheet)."""
    me = sk.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    bm = bmesh.new()
    for hint, tilt, L in (((0.38, -0.26, 0.40), (0.6, -0.2, 1.0), 0.10), ((-0.38, -0.24, 0.40), (-0.6, -0.1, 1.0), 0.09),
                          ((0.05, 0.30, 0.52), (0.1, 0.6, 1.0), 0.18)):
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
