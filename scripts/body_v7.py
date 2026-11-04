"""
v7 body (reference accuracy pass; body_v6.py is kept unchanged): built from the approved sheet as
a modelling blueprint - its FRONT, SIDE (EXACT) and THREE-QUARTER views together - instead of
adjusting v6.

Dimensions were measured on the sheet's silhouettes in metres (sheet_blueprint.py gives one scale
and offset per view: front 160 px/m, side 150.2 px/m) and joints were taken from the joint
three-view solve (data/sheet_blueprint_R_forward.json, centred on the pelvis):

- torso: horizontal slices whose width is the front view's and whose depth is the side view's
  (back profile measured; the front measured where the arms do not hide it), so the lean, the
  hunch, the chest under the neck and the narrow waist come from the sheet, not from a pose rig;
- long arm: shoulder -> elbow -> wrist -> club through the solved joints, centreline from the
  front view (x) and the side view (y); a slim upper arm and a long, flat, plank-like forearm
  (narrow from the front, deep from the side) flaring into a club whose end lies flat on the floor;
- short arm: hanging from the left shoulder, ending above the knee, as in the front view;
- legs: straight-ish from the front (no wide splay), the right foot forward under the body and
  the left leg trailing back (side view); thinner than v6, broad blocky feet.

World space, metres, Z up, the monster faces -Y, its right (-X) carries the long arm.
V7_FAST=1 skips the surface detail (knife facets, cracks, damage) for quick silhouette checks.
"""
import os

import numpy as np
from mathutils import Vector

import bmesh

import sculpt as SC
import surface_v5 as SV

VOXEL_BASE = 0.011        # base form remesh
VOXEL = 0.0058            # even resolution after the knife facets (flake mosaic, damage)
FAST = bool(os.environ.get("V7_FAST"))


# ---------------------------------------------------------------------------
# Blueprint (metres; x from the front view, y from the side view, z shared)
# ---------------------------------------------------------------------------
# z, x_min, x_max, y_front, y_back, exponent. Width: front view (-0.33..0.35 at the waist,
# -0.43..0.36 at z 1.6, shoulders hidden by the arms); back: side view; front: side view at
# z <= 1.4 and z >= 1.9 (in between it hides behind the long arm).
TORSO_ROWS = [
    (1.23, -0.250, 0.250, -0.120, 0.520, 2.2),     # crotch (front and side views: the legs part at z ~1.2)
    (1.30, -0.335, 0.345, -0.205, 0.585, 2.3),
    (1.38, -0.355, 0.350, -0.215, 0.575, 2.2),     # groin: the side view shows its front at y -0.20 here...
    (1.47, -0.380, 0.355, -0.340, 0.565, 2.1),     # ...and the belly swelling forward above it (behind the arm)
    (1.60, -0.425, 0.365, -0.440, 0.550, 2.2),     # an egg-shaped, leaning barrel rather than a box
    (1.75, -0.445, 0.390, -0.500, 0.445, 2.3),
    (1.90, -0.455, 0.420, -0.530, 0.350, 2.6),     # under the long arm's armpit (front view gap)
    (2.05, -0.500, 0.440, -0.590, 0.265, 2.6),     # rounded off at the back corners (three-quarter view)
    (2.20, -0.530, 0.440, -0.600, 0.180, 2.7),
    (2.32, -0.490, 0.420, -0.595, 0.100, 2.8),
    (2.41, -0.380, 0.360, -0.560, 0.020, 2.7),     # the left shoulder rides a little higher
    (2.46, -0.230, 0.170, -0.470, -0.080, 2.5),    # top of the hump, below the head (side view)
]
# neck: from the front of the torso's top to the back of the skull (short, thick)
NECK = [((-0.05, -0.40, 2.28), 0.22, 0.17), ((-0.08, -0.58, 2.33), 0.22, 0.16), ((-0.10, -0.74, 2.36), 0.21, 0.15)]

# limbs: (point, half-width (side to side), half-depth (front to back), exponent, twist)
LONG_ARM = [
    ((-0.590, -0.360, 2.300), 0.135, 0.135, 2.8, 0),      # shoulder (inside the torso's side)
    ((-0.705, -0.380, 2.050), 0.130, 0.130, 3.0, 2),
    ((-0.845, -0.400, 1.780), 0.126, 0.132, 3.0, 4),      # slim upper arm
    ((-0.990, -0.415, 1.500), 0.132, 0.160, 2.6, 6),      # elbow
    ((-1.075, -0.500, 1.220), 0.142, 0.200, 2.0, 8),      # long, flattened forearm with an elliptical
    ((-1.115, -0.640, 0.950), 0.148, 0.210, 2.0, 9),      # section: narrow from the front, deep from
    ((-1.140, -0.810, 0.660), 0.162, 0.220, 2.1, 10),     # the side, slim on the diagonal (all three views)
    ((-1.150, -0.960, 0.400), 0.188, 0.245, 2.3, 10),     # club
    ((-1.160, -1.060, 0.120), 0.212, 0.280, 2.5, 10),
    ((-1.165, -1.100, -0.040), 0.214, 0.290, 2.5, 10),    # end, cut flat on the floor
]
SHORT_ARM = [
    ((0.410, -0.380, 2.250), 0.132, 0.130, 2.8, 0),       # left shoulder
    ((0.510, -0.300, 2.000), 0.128, 0.126, 3.0, -2),
    ((0.590, -0.150, 1.680), 0.132, 0.132, 2.8, -4),      # elbow
    ((0.650, -0.030, 1.300), 0.136, 0.140, 2.8, -6),
    ((0.700, 0.060, 0.970), 0.140, 0.142, 3.0, -8),       # blunt end above the knee
]
HIPS = {"Leg_R": np.array([-0.220, 0.080, 1.300]), "Leg_L": np.array([0.225, 0.400, 1.300])}   # the stride
KNEES = {"Leg_R": np.array([-0.300, -0.090, 0.840]), "Leg_L": np.array([0.300, 0.560, 0.800])}    # opens at the hips
ANKLES = {"Leg_R": np.array([-0.250, 0.280, 0.220]), "Leg_L": np.array([0.400, 0.800, 0.220])}
FEET = {  # heel, toe tips on the floor (the foot lies flat between)
    "Leg_R": (np.array([-0.250, 0.460, 0.0]), np.array([-0.300, -0.220, 0.0])),     # forward, under the body
    "Leg_L": (np.array([0.410, 1.010, 0.0]), np.array([0.430, 0.560, 0.0])),        # trailing back
}
FOOT_W = {"Leg_R": 0.150, "Leg_L": 0.148}           # broad feet (half-widths), front view ~0.3 m


def _sharpen(rows, joints, frac=0.14):
    """Angular bends: extra keys just before and after each joint (index into rows), so the
    smooth loft turns sharply there instead of curving through it."""
    out = []
    for i, r in enumerate(rows):
        if i in joints:
            for j, f in ((i - 1, frac), (i + 1, frac)):
                p0, p1 = np.asarray(r[0]), np.asarray(rows[j][0])
                q = p0 + (p1 - p0) * f
                key = (tuple(float(c) for c in q), r[1] + (rows[j][1] - r[1]) * f, r[2] + (rows[j][2] - r[2]) * f,
                       r[3], r[4] + (rows[j][4] - r[4]) * f)
                if j < i:
                    out.append(key)
                else:
                    out += [r, key]
            continue
        out.append(r)
    return out


LONG_ARM = _sharpen(LONG_ARM, [3])                   # elbow
SHORT_ARM = _sharpen(SHORT_ARM, [2])


def _leg_rows(name):
    h, k, a = HIPS[name], KNEES[name], ANKLES[name]
    pts = [h, h + (k - h) * 0.5, k, k + (a - k) * 0.5, a]
    w = (0.135, 0.130, 0.128, 0.120, 0.118)
    d = (0.145, 0.150, 0.160, 0.135, 0.128)
    return _sharpen([(tuple(float(c) for c in p), ww, dd, 4.0, 0) for p, ww, dd in zip(pts, w, d)], [2])


LEGS = {n: _leg_rows(n) for n in HIPS}
TOES = FEET


def limb_keys(rows):
    return [{"p": p, "w": w, "d": d, "e": e, "rot": r} for p, w, d, e, r in rows]


def along(rows, t):
    """Point and tangent at arc-length fraction t of a key path."""
    P = np.array([r[0] for r in rows], float)
    L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    s = t * L[-1]
    i = min(int(np.searchsorted(L, s, side="right")) - 1, len(P) - 2)
    u = (s - L[i]) / max(L[i + 1] - L[i], 1e-9)
    return P[i] + (P[i + 1] - P[i]) * u, SC.unit(P[i + 1] - P[i])


def on(rows, t, side, r_along=0.20, r_across=0.10, s=1.0, off=0.2):
    """Damage zone on a limb at fraction t, on the side given by `side` (world direction)."""
    p, tan = along(rows, t)
    d = np.asarray(side, float)
    d = SC.unit(d - (d @ tan) * tan)
    radii = np.abs(tan) * r_along + (1 - np.abs(tan)) * r_across
    return (tuple(p + d * off), tuple(np.maximum(radii, r_across * 0.8)), s)


# ---------------------------------------------------------------------------
# Damage map (after the sheet: red streaks along the limbs, torn torso sides, belly)
# ---------------------------------------------------------------------------
LA, SA, LR, LL = LONG_ARM, SHORT_ARM, LEGS["Leg_R"], LEGS["Leg_L"]
OUT_R, OUT_L, FRONT, BACK = (-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0)
DAMAGE = {
    "Torso": {
        "peel": [((-0.34, -0.42, 2.02), (0.16, 0.12, 0.16), 0.95),      # right chest
                 ((0.40, -0.10, 1.95), (0.10, 0.20, 0.30), 1.0),        # left side, long tear
                 ((-0.36, 0.10, 1.62), (0.10, 0.20, 0.26), 1.0),        # right flank
                 ((0.02, -0.34, 1.55), (0.16, 0.10, 0.14), 0.9),        # belly
                 ((0.08, -0.12, 2.42), (0.18, 0.14, 0.12), 0.9),        # upper back, spikes
                 ((-0.10, 0.50, 1.55), (0.16, 0.10, 0.14), 0.75),
                 ((0.20, -0.16, 1.32), (0.12, 0.10, 0.08), 0.7),
                 ((-0.22, -0.52, 1.90), (0.08, 0.06, 0.20), 0.85)],     # chest streak
        "wound": [((0.41, -0.12, 1.93), (0.05, 0.12, 0.24), 1.0),
                  ((-0.37, 0.08, 1.64), (0.05, 0.12, 0.20), 1.0),
                  ((-0.34, -0.44, 2.00), (0.07, 0.05, 0.08), 1.0),
                  ((-0.22, -0.54, 1.88), (0.04, 0.04, 0.16), 1.0)],
    },
    "Arm_R_Long": {
        "peel": [on(LA, 0.04, (0, 0, 1), 0.10, 0.10, 0.8, 0.10),
                 on(LA, 0.20, OUT_R, 0.22, 0.10, 0.95), on(LA, 0.33, FRONT, 0.18, 0.09, 0.8),
                 on(LA, 0.42, OUT_R, 0.20, 0.12, 1.0), on(LA, 0.55, FRONT, 0.24, 0.09, 0.95),
                 on(LA, 0.66, OUT_R, 0.26, 0.10, 1.0), on(LA, 0.78, (1, -1, 0), 0.22, 0.09, 0.85),
                 on(LA, 0.90, FRONT, 0.18, 0.10, 0.9), on(LA, 1.00, (0, -0.5, -1), 0.10, 0.16, 0.9)],
        "wound": [on(LA, 0.42, OUT_R, 0.14, 0.05, 1.0), on(LA, 0.60, FRONT, 0.20, 0.045, 1.0),
                  on(LA, 0.70, OUT_R, 0.16, 0.05, 1.0), on(LA, 1.00, (0, -0.5, -1), 0.05, 0.10, 1.0)],
    },
    "Arm_L_Short": {
        "peel": [on(SA, 0.12, OUT_L, 0.18, 0.10, 0.85), on(SA, 0.35, FRONT, 0.20, 0.09, 0.9),
                 on(SA, 0.55, OUT_L, 0.22, 0.10, 1.0), on(SA, 0.80, FRONT, 0.18, 0.09, 0.9),
                 on(SA, 1.00, (0, -0.4, -1), 0.08, 0.14, 0.9)],
        "wound": [on(SA, 0.55, OUT_L, 0.16, 0.045, 1.0), on(SA, 0.35, FRONT, 0.14, 0.04, 1.0),
                  on(SA, 1.00, (0, -0.4, -1), 0.04, 0.09, 1.0)],
    },
    "Leg_R": {
        "peel": [on(LR, 0.15, FRONT, 0.20, 0.09, 0.85), on(LR, 0.38, OUT_R, 0.20, 0.09, 0.9),
                 on(LR, 0.50, FRONT, 0.22, 0.10, 1.0), on(LR, 0.72, FRONT, 0.20, 0.09, 0.9),
                 on(LR, 0.85, OUT_R, 0.14, 0.08, 0.7)],
        "wound": [on(LR, 0.50, FRONT, 0.16, 0.04, 1.0), on(LR, 0.72, FRONT, 0.12, 0.035, 1.0)],
    },
    "Leg_L": {
        "peel": [on(LL, 0.18, OUT_L, 0.20, 0.09, 0.85), on(LL, 0.45, FRONT, 0.22, 0.10, 1.0),
                 on(LL, 0.60, OUT_L, 0.18, 0.09, 0.9), on(LL, 0.80, FRONT, 0.18, 0.09, 0.85)],
        "wound": [on(LL, 0.45, FRONT, 0.16, 0.04, 1.0), on(LL, 0.62, OUT_L, 0.10, 0.035, 1.0)],
    },
}

# Bars: (part, entry hint, direction, length, half width, half depth) - the sheet's rods, same
# count as v6, moved to where the three views show them
BARS = [
    ("Torso", (0.04, -0.26, 2.46), (0.10, 0.30, 1.0), 0.26, 0.030, 0.019),          # spike on the hump
    ("Torso", (-0.12, 0.06, 2.36), (-0.25, 0.65, 0.72), 0.24, 0.028, 0.018),         # back spikes
    ("Torso", (0.04, 0.40, 1.92), (0.05, 0.85, 0.50), 0.26, 0.026, 0.017),
    ("Arm_L_Short", (0.38, -0.30, 2.34), (0.25, -0.15, 1.0), 0.15, 0.030, 0.019),    # shoulder spike
    ("Torso", (-0.44, -0.30, 1.56), (-1.0, -0.15, 0.05), 0.22, 0.026, 0.017),        # torso side rods
    ("Torso", (0.10, 0.55, 1.66), (0.10, 1.0, 0.0), 0.12, 0.024, 0.016),
    ("Arm_R_Long", tuple(along(LA, 0.79)[0] + np.array([-0.16, 0, 0])), (-1.0, 0.05, 0.25), 0.24, 0.026, 0.017),
    ("Arm_R_Long", tuple(along(LA, 0.92)[0] + np.array([-0.18, 0, 0])), (-1.0, -0.2, -0.1), 0.16, 0.024, 0.016),
    ("Arm_L_Short", tuple(along(SA, 0.42)[0] + np.array([0.14, 0, 0])), (1.0, -0.05, 0.1), 0.20, 0.026, 0.017),
    ("Leg_L", tuple(along(LL, 0.62)[0] + np.array([0.13, 0, 0])), (1.0, 0.3, 0.25), 0.18, 0.024, 0.016),
]
for _part, _hint, *_ in BARS:                      # every bar is driven into its own entry wound
    DAMAGE[_part]["wound"].append((_hint, (0.04, 0.04, 0.05), 1.0))
    DAMAGE[_part]["peel"].append((_hint, (0.08, 0.08, 0.10), 0.95))


# ---------------------------------------------------------------------------
# Part builders
# ---------------------------------------------------------------------------
def _sculpt(S, ob, name, axis, seed, faces, jitter=0.016):
    """knife facets -> even re-densify -> thin crack network -> embedded damage -> pits, erosion."""
    S.write()
    if FAST:
        return ob
    SC.lowpoly(ob, faces, jitter=jitter, seed=seed, dissolve_deg=5.0, levels=1, remesh_after=VOXEL)
    S = SC.Surf(ob)
    if callable(axis):
        axis = axis(S.co)
    chunk = SV.crack_network(S, cell=0.085, width=0.0024, depth=0.0028, seed=seed + 1, tilt=0.03)
    d = DAMAGE[name]
    wounds = [(c, tuple(np.asarray(r) * 1.00), st) for c, r, st in d["wound"]]
    peels = [(c, tuple(np.asarray(r) * 1.08), st) for c, r, st in d["peel"]]
    SC.damage(S, peels, wounds, axis, seed=seed + 2, n_flaps=0, chunk=chunk,
              t1=0.016, t2=0.010, tissue=0.016, lips=0.0, cover=0.08, jag=1.0)
    keep = (S.a["tissue"] < 0.5) * 1.0
    SV.pits(S, per_m2=70, size=(0.008, 0.024), depth=(0.003, 0.008), seed=seed + 3, w=keep)
    SV.erode(S, amp=0.0022, freq=8.0, seed=seed + 4, w=keep)
    SC.blood(S, seed + 5, drips=10)
    SC.finish(S, ob, decimate_ratio=1.0, sharp_deg=25.0)
    return ob


def _base(ob, voxel=VOXEL_BASE):
    SC.remesh(ob, voxel)
    S = SC.Surf(ob)
    S.smooth(4)
    return S


def build_torso(col, mat):
    keys = [{"p": (0.0, 0.0, z), "ws": x1 - (x0 + x1) / 2, "wn": (x0 + x1) / 2 - x0,
             "df": (yb - yf) / 2, "db": (yb - yf) / 2, "ox": (x0 + x1) / 2, "oy": -(yf + yb) / 2, "e": e}
            for z, x0, x1, yf, yb, e in TORSO_ROWS]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=56, step=0.02, caps=(0.06, 0.04))
    SC.merge_bm(bm, SC.loft([{"p": p, "w": w, "d": d, "e": 3.0} for p, w, d in NECK],
                            ref=(0, -1, 0), seg=32, step=0.02, caps=(0.04, 0.05)))
    ob = SC.obj_from_bm("Torso", bm, col, [mat])
    S = _base(ob)
    SC.push(S, (0.0, 0.40, 1.85), (0.035, 0.12, 0.40), -0.010)                # spine groove
    SC.push(S, (-0.36, 0.08, 1.80), (0.08, 0.20, 0.30), 0.010)                # asymmetric flanks
    SC.push(S, (0.36, -0.10, 1.98), (0.08, 0.20, 0.22), -0.010)
    SC.push(S, (0.30, -0.40, 2.36), (0.14, 0.16, 0.10), 0.018)                # left shoulder mass, hump
    SC.push(S, (-0.40, -0.40, 2.30), (0.12, 0.16, 0.10), -0.014)              # right shoulder slopes off
    SC.push(S, (0.10, -0.38, 1.55), (0.20, 0.10, 0.16), -0.010)               # a lean, sunken belly front
    SC.warp(S, 0.010, 1.5, 11)
    SC.dents(S, 8, (0.05, 0.10), (0.006, 0.014), 12)
    return _sculpt(S, ob, "Torso", np.array([0.0, -0.70, 0.71]), 13, 540)


def _limb(col, mat, name, rows, caps):
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=caps, path=True)
    ob = SC.obj_from_bm(name, bm, col, [mat])
    return _base(ob), ob, C, T


def build_long_arm(col, mat):
    S, ob, C, T = _limb(col, mat, "Arm_R_Long", LONG_ARM, (0.10, 0.0))
    P = [np.asarray(r[0]) for r in LONG_ARM]
    SC.flatten(S, tuple(P[0] + (0, 0, 0.10)), (0.12, 0.12, 0.08), (0.10, -0.05, 1.0), 0.75)  # chiselled cap
    SC.flatten(S, tuple(P[0] + (-0.10, 0, 0.02)), (0.08, 0.11, 0.08), (-1.0, 0.0, 0.9), 0.8)
    SC.push(S, tuple(P[4] + (-0.06, 0.08, 0.02)), (0.07, 0.07, 0.07), 0.016)              # bony elbow, angular bend
    SC.push(S, tuple(P[4] + (0.06, -0.08, -0.02)), (0.05, 0.06, 0.07), -0.018)            # inner elbow notch
    SC.push(S, tuple(P[7] + (-0.10, 0.0, 0.0)), (0.05, 0.10, 0.22), 0.008)                # forearm ridge
    SC.push(S, tuple(P[2] + (0.05, -0.05, 0.0)), (0.05, 0.08, 0.16), -0.012)              # wasted upper arm
    SC.push(S, tuple(P[8] + (0.07, 0.04, 0.0)), (0.05, 0.06, 0.14), -0.010)
    SC.warp(S, 0.010, 1.7, 22)
    SC.dents(S, 9, (0.03, 0.07), (0.005, 0.012), 23)
    _clamp(S)
    return _sculpt(S, ob, "Arm_R_Long", lambda co: SC.path_axes(co, C, T), 24, 380)


def build_short_arm(col, mat):
    S, ob, C, T = _limb(col, mat, "Arm_L_Short", SHORT_ARM, (0.10, 0.05))
    P = [np.asarray(r[0]) for r in SHORT_ARM]
    SC.flatten(S, tuple(P[0] + (0, 0, 0.10)), (0.11, 0.11, 0.08), (-0.10, -0.05, 1.0), 0.75)
    SC.flatten(S, tuple(P[0] + (0.10, 0, 0.02)), (0.08, 0.11, 0.08), (1.0, 0.0, 0.9), 0.8)
    SC.push(S, tuple(P[3] + (0.08, 0.05, 0.0)), (0.06, 0.07, 0.09), 0.014)                # outer elbow
    SC.push(S, tuple(P[5] + (-0.05, -0.04, 0.0)), (0.05, 0.06, 0.12), -0.010)             # wasted forearm
    SC.warp(S, 0.009, 1.8, 32)
    SC.dents(S, 6, (0.03, 0.06), (0.005, 0.011), 33)
    return _sculpt(S, ob, "Arm_L_Short", lambda co: SC.path_axes(co, C, T), 34, 250)


def _foot(heel_pt, toe, w, seed):
    """Broad, blocky foot with short square toe blocks, lying flat on the floor from its heel to its
    toe tips (the toes fuse in the remesh, grooves stay between them)."""
    a = np.array([heel_pt[0], heel_pt[1], 0.0])
    t = np.array([toe[0], toe[1], 0.0])
    f = SC.unit(t - a)
    side = np.array([-f[1], f[0], 0.0])
    heel = a + f * 0.04
    body = np.linalg.norm(t - heel) - 0.08                        # short toes take the last ~8 cm

    def P(u, h, o=0.0):
        return tuple(heel + f * u + side * o + np.array([0.0, 0.0, h]))
    bm = SC.loft([{"p": P(0.0, 0.105), "w": w * 0.92, "df": 0.105, "db": 0.105, "e": 4.4},   # tall heel block
                  {"p": P(body * 0.45, 0.090), "w": w, "df": 0.088, "db": 0.090, "e": 4.6},
                  {"p": P(body, 0.062), "w": w * 1.04, "df": 0.060, "db": 0.062, "e": 4.6}],  # low at the toes
                 ref=(0, 0, 1), seg=32, step=0.02, caps=(0.04, 0.02))
    r = np.random.default_rng(seed)
    nt = 4
    tw = 2 * w * 1.04 / nt
    for k in range(nt):
        o = -w * 1.04 + tw * (k + 0.5)
        tl = r.uniform(0.06, 0.10)
        h = r.uniform(0.042, 0.054)
        SC.merge_bm(bm, SC.loft([{"p": P(body - 0.03, h, o), "w": tw * 0.46, "df": h - 0.004, "db": h, "e": 4.0},
                                 {"p": P(body - 0.03 + tl, h * 0.9, o), "w": tw * 0.44,
                                  "df": h * 0.86, "db": h * 0.9, "e": 4.0}],
                                ref=(0, 0, 1), seg=20, step=0.015, caps=(0.01, 0.015)))
    return bm


def build_leg(col, mat, name, seed):
    rows = [(p, w, d, e, (2 if name == "Leg_R" else -3)) for p, w, d, e, _ in LEGS[name]]
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=(0.04, 0.02), path=True)
    SC.merge_bm(bm, _foot(*FEET[name], FOOT_W[name], seed))
    ob = SC.obj_from_bm(name, bm, col, [mat])
    S = _base(ob, 0.010)
    hip, knee, ankle = HIPS[name], KNEES[name], ANKLES[name]
    b = SC.unit(SC.unit(knee - hip) - SC.unit(ankle - knee))      # the way the knee juts out
    if not np.all(np.isfinite(b)) or np.linalg.norm(b) < 0.5:
        b = np.array([0.0, -1.0, 0.0])
    SC.push(S, tuple(knee + b * 0.11), (0.10, 0.10, 0.10), 0.016)                      # bony knee
    SC.push(S, (ankle[0], ankle[1], 0.15), (0.15, 0.15, 0.05), -0.008)                  # ankle
    SC.warp(S, 0.008, 1.9, seed)
    SC.dents(S, 5, (0.03, 0.06), (0.004, 0.010), seed + 1)
    _clamp(S)
    return _sculpt(S, ob, name, lambda co: SC.path_axes(co, C, T), seed + 2, 230)


def _clamp(S):
    S.co[:, 2] = np.maximum(S.co[:, 2], 0.004)


# ---------------------------------------------------------------------------
# Bars
# ---------------------------------------------------------------------------
def nearest_surface(ob, p):
    me = ob.data
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    i = int(np.argmin(((co - np.asarray(p, np.float32)) ** 2).sum(1)))
    v = me.vertices[i]
    return Vector(v.co), Vector(v.normal)


def build_bars(col, mat, parts):
    bm_all = bmesh.new()
    for part, hint, direction, length, hw, hd in BARS:
        p, nrm = nearest_surface(parts[part], hint)
        d = (Vector(direction).normalized() * 0.75 + nrm * 0.25).normalized()
        pts = [p - d * 0.12, p, p + d * length]
        keys = [{"p": tuple(q), "w": hw, "d": hd, "e": 7.0} for q in pts]
        SC.merge_bm(bm_all, SC.loft(keys, ref=(0, 0, 1) if abs(d.z) < 0.8 else (1, 0, 0), seg=24,
                                    step=0.012, caps=(0.006, 0.008)))
    ob = SC.obj_from_bm("Bars", bm_all, col, [mat])
    SC.remesh(ob, 0.0035)
    S = SC.Surf(ob)
    S.smooth(2)
    SC.warp(S, 0.002, 9.0, 81)
    SC.dents(S, 30, (0.008, 0.02), (0.001, 0.003), 82)
    SC.finish(S, ob, decimate_ratio=0.5, sharp_deg=50.0)
    return ob


def build_body(col, mat, bar_mat):
    parts = {"Torso": build_torso(col, mat),
             "Arm_R_Long": build_long_arm(col, mat),
             "Arm_L_Short": build_short_arm(col, mat),
             "Leg_R": build_leg(col, mat, "Leg_R", 41),
             "Leg_L": build_leg(col, mat, "Leg_L", 51)}
    parts["Bars"] = build_bars(col, bar_mat, parts)
    return parts
