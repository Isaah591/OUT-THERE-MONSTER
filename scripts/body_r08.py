"""
Body of the OUT THERE monster, rebuilt as sculpted meshes after the Astra R08 sheet.

Each part is a nuanced spline loft (varying superellipse sections, twist, asymmetric
half-extents), voxel-remeshed into a dense even surface, then sculpted with
`sculpt.py`: large-form brushes and dents -> knife facets -> R08 damage map (layered
bark peels, shallow fibrous tissue, chipped edges, entry wounds for the bars) -> old blood.

World space, metres, Z up, monster faces -Y, its right (-X) carries the long arm.
"""
import math

import bmesh
import numpy as np
from mathutils import Vector

import sculpt as SC

VOXEL = 0.0065


# ---------------------------------------------------------------------------
# Base forms (R08 proportions measured on the sheet; see README)
# ---------------------------------------------------------------------------
def torso_keys():
    cy = 0.04                                   # spine line
    rings = [  # z, front y, back y, half-width (+x / -x), exponent, x drift
        (1.06, -0.17, 0.26, 0.40, 0.40, 3.0, 0.000),
        (1.12, -0.21, 0.29, 0.435, 0.43, 3.2, 0.000),
        (1.30, -0.235, 0.305, 0.455, 0.452, 3.4, 0.002),
        (1.55, -0.248, 0.31, 0.468, 0.462, 3.4, 0.004),
        (1.80, -0.228, 0.315, 0.472, 0.470, 3.5, 0.004),
        (2.02, -0.13, 0.322, 0.478, 0.474, 3.6, 0.002),    # upper chest recedes behind the jaw
        (2.20, -0.035, 0.318, 0.472, 0.470, 3.6, 0.000),
        (2.34, 0.005, 0.302, 0.458, 0.452, 3.3, -0.004),
        (2.43, 0.02, 0.262, 0.415, 0.40, 2.9, -0.006),
        (2.48, 0.04, 0.20, 0.33, 0.31, 2.5, -0.006),
    ]
    return [{"p": (dx, cy, z), "ws": ws, "wn": wn, "df": cy - fy, "db": by - cy, "e": e}
            for z, fy, by, ws, wn, e, dx in rings]


LONG_ARM_KEYS = [  # point, half-width, half-depth, exponent, twist
    ((-0.600, -0.070, 2.430), 0.195, 0.185, 2.6, 0),
    ((-0.640, -0.080, 2.300), 0.205, 0.195, 3.0, 0),
    ((-0.720, -0.100, 2.050), 0.200, 0.190, 3.2, 3),
    ((-0.800, -0.120, 1.820), 0.198, 0.185, 3.3, 5),
    ((-0.920, -0.150, 1.550), 0.205, 0.190, 3.3, 6),
    ((-0.970, -0.180, 1.400), 0.215, 0.195, 3.2, 8),     # elbow
    ((-0.965, -0.270, 1.200), 0.218, 0.190, 3.4, 10),
    ((-0.950, -0.360, 0.980), 0.225, 0.190, 3.5, 12),
    ((-0.920, -0.480, 0.740), 0.230, 0.195, 3.6, 14),
    ((-0.890, -0.600, 0.500), 0.235, 0.200, 3.6, 15),
    ((-0.878, -0.690, 0.330), 0.248, 0.222, 3.4, 16),    # flared, heavy club end
    ((-0.872, -0.760, 0.180), 0.258, 0.236, 3.0, 16),
]
SHORT_ARM_KEYS = [
    ((0.590, -0.050, 2.400), 0.180, 0.180, 2.8, 0),
    ((0.610, -0.050, 2.250), 0.185, 0.180, 3.0, 0),
    ((0.640, -0.055, 1.950), 0.178, 0.172, 3.3, -3),
    ((0.670, -0.060, 1.650), 0.176, 0.170, 3.4, -5),     # slight elbow bulge
    ((0.700, -0.070, 1.350), 0.172, 0.165, 3.4, -6),
    ((0.730, -0.075, 1.050), 0.168, 0.162, 3.4, -7),
    ((0.755, -0.080, 0.800), 0.165, 0.160, 3.2, -8),     # blunt stump
]
LEG_KEYS = {
    "Leg_R": [((-0.200, 0.030, 1.200), 0.168, 0.180), ((-0.200, 0.010, 1.000), 0.166, 0.178),
              ((-0.200, -0.020, 0.760), 0.172, 0.186), ((-0.200, -0.030, 0.620), 0.165, 0.180),
              ((-0.205, -0.020, 0.400), 0.156, 0.170), ((-0.205, 0.000, 0.200), 0.152, 0.165),
              ((-0.205, 0.010, 0.090), 0.150, 0.160)],
    "Leg_L": [((0.300, 0.030, 1.200), 0.182, 0.186), ((0.302, 0.010, 1.000), 0.180, 0.184),
              ((0.304, -0.025, 0.760), 0.188, 0.190), ((0.305, -0.035, 0.620), 0.180, 0.185),
              ((0.305, -0.020, 0.400), 0.172, 0.176), ((0.305, 0.000, 0.200), 0.168, 0.172),
              ((0.305, 0.010, 0.090), 0.166, 0.168)],
}


def limb_keys(rows):
    return [{"p": p, "w": w, "d": d, "e": e, "rot": r} for p, w, d, e, r in rows]


# ---------------------------------------------------------------------------
# R08 damage map (zone centres are snapped onto the surface)
#   (centre, radii, strength)
# ---------------------------------------------------------------------------
DAMAGE = {
    "Torso": {
        "peel": [((-0.28, -0.25, 2.02), (0.18, 0.12, 0.16), 0.9),      # right upper chest
                 ((-0.20, -0.26, 1.62), (0.13, 0.10, 0.14), 0.95),     # belly, bracket entry
                 ((0.45, -0.16, 2.10), (0.12, 0.17, 0.34), 1.0),       # left side at the shoulder
                 ((0.22, 0.33, 2.28), (0.17, 0.12, 0.15), 0.95),       # upper back, spike entry
                 ((-0.15, 0.33, 1.45), (0.20, 0.10, 0.15), 0.8),       # lower back
                 ((0.48, 0.05, 1.50), (0.10, 0.17, 0.20), 0.6),        # left flank
                 ((-0.48, 0.02, 1.78), (0.10, 0.17, 0.19), 0.75),      # right flank
                 ((-0.30, 0.10, 2.46), (0.15, 0.15, 0.10), 0.7),       # top, right trapezius
                 ((0.05, 0.30, 1.12), (0.22, 0.10, 0.08), 0.7)],       # back hem
        "wound": [((0.44, -0.18, 2.14), (0.07, 0.10, 0.22), 1.0),      # deep vertical wound
                  ((-0.20, -0.26, 1.63), (0.06, 0.05, 0.07), 1.0),
                  ((0.22, 0.33, 2.29), (0.06, 0.06, 0.06), 1.0)],
    },
    "Arm_R_Long": {
        "peel": [((-0.64, -0.05, 2.50), (0.15, 0.15, 0.10), 0.85),     # shoulder cap
                 ((-0.66, -0.26, 2.25), (0.10, 0.10, 0.14), 0.6),      # cap front
                 ((-0.88, -0.10, 1.95), (0.13, 0.15, 0.26), 0.9),      # upper arm, outer
                 ((-1.17, -0.15, 1.42), (0.20, 0.20, 0.28), 1.0),      # elbow (outer/back)
                 ((-0.97, -0.05, 1.30), (0.15, 0.15, 0.22), 0.9),      # elbow back
                 ((-1.15, -0.45, 0.86), (0.15, 0.17, 0.32), 1.0),      # forearm outer
                 ((-0.92, -0.62, 1.02), (0.17, 0.12, 0.20), 0.8),      # forearm front
                 ((-0.90, -0.80, 0.45), (0.16, 0.12, 0.18), 0.75),     # forearm front, low
                 ((-0.68, -0.52, 0.70), (0.12, 0.14, 0.20), 0.7),      # forearm inner
                 ((-0.87, -0.80, 0.10), (0.24, 0.24, 0.08), 0.9)],     # club end
        "wound": [((-1.18, -0.12, 1.38), (0.06, 0.07, 0.13), 1.0),
                  ((-1.16, -0.46, 0.86), (0.06, 0.07, 0.12), 1.0),     # forearm bar entry
                  ((-0.87, -0.80, 0.08), (0.13, 0.13, 0.05), 1.0)],    # dark end face
    },
    "Arm_L_Short": {
        "peel": [((0.80, -0.05, 2.12), (0.12, 0.15, 0.20), 0.8),
                 ((0.86, -0.15, 1.35), (0.15, 0.16, 0.36), 1.0),       # heavy lower half
                 ((0.64, -0.24, 1.90), (0.12, 0.12, 0.17), 0.7),
                 ((0.93, -0.07, 1.50), (0.10, 0.10, 0.12), 0.95),      # bar entry
                 ((0.72, -0.25, 1.05), (0.12, 0.10, 0.18), 0.75),
                 ((0.76, -0.08, 0.66), (0.22, 0.22, 0.08), 0.9)],      # stump
        "wound": [((0.88, -0.12, 1.25), (0.06, 0.06, 0.15), 1.0),
                  ((0.93, -0.07, 1.50), (0.05, 0.05, 0.06), 1.0),
                  ((0.76, -0.08, 0.64), (0.12, 0.12, 0.05), 1.0)],     # dark stump face
    },
    "Leg_R": {
        "peel": [((-0.20, -0.23, 0.64), (0.20, 0.10, 0.26), 1.0),      # knee
                 ((-0.20, -0.20, 0.82), (0.22, 0.14, 0.07), 0.9),      # band break above the knee
                 ((-0.20, -0.20, 0.47), (0.22, 0.14, 0.07), 0.85),     # band break below the knee
                 ((-0.30, -0.16, 0.30), (0.13, 0.12, 0.15), 0.8),      # shin
                 ((-0.37, -0.02, 0.96), (0.10, 0.15, 0.18), 0.7),      # thigh outer
                 ((-0.20, 0.20, 0.55), (0.15, 0.10, 0.18), 0.65),      # calf
                 ((-0.12, -0.20, 0.98), (0.10, 0.08, 0.10), 0.55)],
        "wound": [((-0.20, -0.22, 0.60), (0.04, 0.06, 0.16), 1.0)],    # vertical fibrous slit
    },
    "Leg_L": {
        "peel": [((0.31, -0.23, 0.72), (0.21, 0.10, 0.28), 1.0),       # knee
                 ((0.31, -0.20, 0.90), (0.23, 0.14, 0.07), 0.9),
                 ((0.31, -0.20, 0.55), (0.23, 0.14, 0.07), 0.85),
                 ((0.48, -0.06, 0.42), (0.10, 0.12, 0.13), 0.95),      # shin bar entry
                 ((0.24, -0.21, 1.00), (0.12, 0.10, 0.15), 0.7),
                 ((0.40, 0.18, 0.80), (0.12, 0.12, 0.18), 0.65),
                 ((0.30, -0.20, 0.30), (0.12, 0.10, 0.12), 0.6)],
        "wound": [((0.33, -0.22, 0.68), (0.045, 0.06, 0.17), 1.0),
                  ((0.48, -0.06, 0.42), (0.04, 0.05, 0.06), 1.0)],
    },
}


FLAPS = {"Torso": 9, "Arm_R_Long": 9, "Arm_L_Short": 6, "Leg_R": 6, "Leg_L": 6}


# ---------------------------------------------------------------------------
# Hardware (flat rusted bars) - (part, entry hint, direction, length, half w, half d, bend)
# ---------------------------------------------------------------------------
BARS = [
    ("Torso", (0.22, 0.33, 2.29), (0.18, 0.55, 0.82), 0.42, 0.036, 0.022, None),   # back spike
    ("Arm_R_Long", (-1.16, -0.46, 0.86), (-0.95, -0.25, 0.15), 0.20, 0.034, 0.020, None),  # forearm
    ("Arm_L_Short", (0.93, -0.07, 1.50), (1.0, -0.05, 0.08), 0.20, 0.032, 0.020, None),   # short arm
    ("Leg_L", (0.48, -0.06, 0.42), (1.0, -0.10, 0.02), 0.20, 0.032, 0.020, None),         # shin
    ("Torso", (-0.20, -0.26, 1.63), (0.18, -0.95, -0.12), 0.40, 0.034, 0.020,             # belly hook
     (0.22, (-0.10, -0.20, 0.95), 0.26)),
]


# ---------------------------------------------------------------------------
# Part builders
# ---------------------------------------------------------------------------
def _finish_part(S, ob, name, axis, seed, dec=1.0, chips=0.6):
    d = DAMAGE[name]
    SC.damage(S, d["peel"], d["wound"], axis, seed=seed, n_flaps=FLAPS.get(name, 6))
    # chipped convex edges and corners (small knocks of the shell, R08's broken bevels)
    k = S.blur(S.curvature(), 2)
    cv = SC.smoothstep(6.0, 28.0, k)
    gate = SC.smoothstep(0.2, 1.0, SC._z(SC.fbm(SC.Perlin(seed + 49), S.co * 4.0, 2)))
    SC.damage(S, [], [], axis, seed=seed + 50, t1=0.008, t2=0.004, tissue=0.0, lips=0.0,
              extra=chips * 2.4 * cv * gate - 0.35, tear_amt=0.0)
    SC.blood(S, seed + 70, drips=18)
    SC.finish(S, ob, decimate_ratio=dec, sharp_deg=6.0)
    SC.add_flaps(ob, getattr(S, "flaps", []), seed + 90)
    return ob


def _base(ob, voxel=0.011):
    """Smooth base form: remesh the loft into an even surface for the large-form brushes."""
    SC.remesh(ob, voxel)
    S = SC.Surf(ob)
    S.smooth(4)
    return S


def _knife(S, ob, faces, seed, jitter=0.019):
    """Large knife facets (low-poly sculpt) re-densified for the damage pass."""
    S.write()
    SC.lowpoly(ob, faces, jitter=jitter, seed=seed, dissolve_deg=4.0, levels=4)
    return SC.Surf(ob)


def build_torso(col, mat):
    bm = SC.loft(torso_keys(), ref=(0, -1, 0), seg=48, step=0.02, caps=(0.07, 0.10))
    # short hidden neck block tying the back of the skull into the torso top (fused by the remesh)
    SC.merge_bm(bm, SC.loft([{"p": (0.0, 0.10, 2.30), "w": 0.23, "d": 0.15, "e": 3.0},
                             {"p": (0.0, -0.05, 2.52), "w": 0.22, "d": 0.14, "e": 3.0}],
                            ref=(0, -1, 0), seg=32, step=0.02, caps=(0.04, 0.04)))
    ob = SC.obj_from_bm("Torso", bm, col, [mat])
    S = _base(ob)
    # large forms: belly and chest planes, hunched upper back, spine groove, shoulder sockets
    SC.push(S, (0.0, -0.26, 1.52), (0.30, 0.15, 0.24), 0.014)
    SC.flatten(S, (0.0, -0.20, 1.92), (0.36, 0.2, 0.16), (0.05, -1, 0.35), 0.5)
    SC.push(S, (0.04, 0.33, 2.16), (0.36, 0.16, 0.24), 0.022)
    SC.push(S, (0.0, 0.34, 1.72), (0.035, 0.10, 0.42), -0.010)
    SC.push(S, (-0.48, 0.0, 1.70), (0.10, 0.25, 0.30), 0.012)
    SC.push(S, (0.48, 0.0, 1.95), (0.10, 0.25, 0.22), -0.010)
    for sx in (-1, 1):
        SC.push(S, (sx * 0.30, 0.10, 2.47), (0.16, 0.18, 0.08), -0.020)      # trapezius slope
        SC.push(S, (sx * 0.46, -0.05, 2.30), (0.10, 0.16, 0.12), -0.018)     # arm sockets
    SC.push(S, (0.0, -0.05, 1.08), (0.40, 0.30, 0.05), -0.010)               # hem rolls under
    SC.warp(S, 0.012, 1.4, 11)
    SC.dents(S, 9, (0.05, 0.11), (0.006, 0.016), 12)
    S = _knife(S, ob, 560, 13)
    return _finish_part(S, ob, "Torso", np.array([0.0, 0.0, 1.0]), seed=15)


def build_limb(col, mat, name, rows, caps, top_flat=None):
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=caps, path=True)
    ob = SC.obj_from_bm(name, bm, col, [mat])
    S = _base(ob)
    if top_flat is not None:                                # chiselled shoulder cap top
        c, r_, nrm = top_flat
        SC.flatten(S, c, r_, nrm, 0.75)
    return S, ob, C, T


def build_long_arm(col, mat):
    S, ob, C, T = build_limb(col, mat, "Arm_R_Long", LONG_ARM_KEYS, (0.13, 0.07),
                             top_flat=((-0.62, -0.07, 2.50), (0.16, 0.16, 0.10), (0.15, 0.0, 1.0)))
    SC.flatten(S, (-0.76, -0.07, 2.40), (0.10, 0.16, 0.10), (-1.0, 0.0, 0.9), 0.9)   # outer chamfer
    SC.flatten(S, (-0.62, -0.22, 2.40), (0.14, 0.08, 0.10), (0.1, -1.0, 0.8), 0.8)   # front chamfer
    SC.push(S, (-0.44, -0.06, 2.36), (0.06, 0.14, 0.10), 0.016)            # cap leans onto the torso
    SC.push(S, (-0.78, -0.30, 1.42), (0.07, 0.08, 0.10), -0.030)           # notch at the inner elbow
    SC.push(S, (-1.12, -0.05, 1.45), (0.10, 0.10, 0.10), 0.016)            # elbow knob
    SC.push(S, (-1.10, -0.52, 0.70), (0.08, 0.16, 0.30), 0.012)            # forearm outer swell
    SC.push(S, (-0.88, -0.86, 0.14), (0.20, 0.10, 0.10), 0.010)            # blunt club front
    SC.warp(S, 0.012, 1.6, 22)
    SC.dents(S, 10, (0.04, 0.09), (0.006, 0.016), 23)
    S = _knife(S, ob, 400, 24)
    axis = SC.path_axes(S.co, C, T)
    return _finish_part(S, ob, "Arm_R_Long", axis, seed=26)


def build_short_arm(col, mat):
    S, ob, C, T = build_limb(col, mat, "Arm_L_Short", SHORT_ARM_KEYS, (0.12, 0.035),
                             top_flat=((0.60, -0.05, 2.47), (0.15, 0.15, 0.10), (-0.12, 0.0, 1.0)))
    SC.flatten(S, (0.74, -0.05, 2.37), (0.09, 0.15, 0.10), (1.0, 0.0, 0.85), 0.9)    # outer chamfer
    SC.flatten(S, (0.60, -0.19, 2.37), (0.13, 0.08, 0.10), (-0.1, -1.0, 0.8), 0.8)   # front chamfer
    SC.push(S, (0.43, -0.05, 2.34), (0.05, 0.13, 0.09), 0.014)
    SC.push(S, (0.84, -0.06, 1.66), (0.08, 0.10, 0.14), 0.012)             # outer elbow
    SC.push(S, (0.70, -0.24, 1.20), (0.08, 0.05, 0.20), -0.008)
    SC.warp(S, 0.011, 1.7, 32)
    SC.dents(S, 7, (0.04, 0.08), (0.006, 0.014), 33)
    S = _knife(S, ob, 260, 34)
    axis = SC.path_axes(S.co, C, T)
    return _finish_part(S, ob, "Arm_L_Short", axis, seed=36)


def build_leg(col, mat, name, seed):
    rows = [(p, w, d, 3.3, (2 if name == "Leg_R" else -3)) for p, w, d in LEG_KEYS[name]]
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=(0.04, 0.02), path=True)
    x = rows[-1][0][0]
    fw = rows[-1][1] + 0.025
    foot = SC.loft([{"p": (x, 0.17, 0.07), "w": fw * 0.94, "df": 0.064, "db": 0.07, "e": 3.4},
                    {"p": (x, 0.02, 0.068), "w": fw, "df": 0.066, "db": 0.07, "e": 3.6},
                    {"p": (x, -0.16, 0.062), "w": fw, "df": 0.06, "db": 0.064, "e": 3.6},
                    {"p": (x, -0.28, 0.055), "w": fw * 0.93, "df": 0.05, "db": 0.058, "e": 3.2}],
                   ref=(0, -1, 0), seg=36, step=0.02, caps=(0.05, 0.06))
    SC.merge_bm(bm, foot)
    ob = SC.obj_from_bm(name, bm, col, [mat])
    S = _base(ob, 0.010)
    sx = 1 if name == "Leg_L" else -1
    SC.push(S, (x, -0.21, 0.70), (0.12, 0.06, 0.10), 0.012)                # knee cap
    SC.push(S, (x + sx * 0.10, 0.15, 0.85), (0.08, 0.08, 0.20), 0.008)     # back of thigh
    SC.push(S, (x, -0.03, 0.14), (0.20, 0.20, 0.05), -0.010)               # ankle
    SC.warp(S, 0.010, 1.8, seed)
    SC.dents(S, 6, (0.04, 0.08), (0.005, 0.012), seed + 1)
    S.co[:, 2] = np.maximum(S.co[:, 2], 0.0)
    S = _knife(S, ob, 250, seed + 2)
    S.co[:, 2] = np.maximum(S.co[:, 2], 0.0)                               # flat sole
    axis = SC.path_axes(S.co, C, T)
    return _finish_part(S, ob, name, axis, seed=seed + 4)


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
    for part, hint, direction, length, hw, hd, bend in BARS:
        p, nrm = nearest_surface(parts[part], hint)
        d = (Vector(direction).normalized() * 0.75 + nrm * 0.25).normalized()
        pts = [p - d * 0.12, p, p + d * length]
        if bend is not None:
            frac, bdir, blen = bend
            pts = [p - d * 0.12, p, p + d * length * frac + d * length * (1 - frac) * 0.3,
                   p + d * length + Vector(bdir).normalized() * blen * 0.4,
                   p + d * length + Vector(bdir).normalized() * blen]
        keys = [{"p": tuple(q), "w": hw, "d": hd, "e": 7.0, "rot": 0} for q in pts]
        bm = SC.loft(keys, ref=(0, 0, 1) if abs(d.z) < 0.8 else (1, 0, 0), seg=24, step=0.012,
                     caps=(0.006, 0.008))
        SC.merge_bm(bm_all, bm)
        tip = pts[-1]
        for k in range(2):                                  # rivet heads near the free end
            off = (Vector(pts[-1]) - Vector(pts[-2])).normalized() * (-0.05 - 0.07 * k)
            rv = SC.box_blob(tuple(Vector(tip) + off + Vector((0, 0, hd * 0.9))), (0.026, 0.026, 0.014),
                             e=2.2, seg=12, rings=6)
            SC.merge_bm(bm_all, rv)
    ob = SC.obj_from_bm("Bars", bm_all, col, [mat])
    SC.remesh(ob, 0.0035)
    S = SC.Surf(ob)
    S.smooth(2)
    SC.warp(S, 0.002, 9.0, 81)
    SC.dents(S, 30, (0.008, 0.02), (0.001, 0.003), 82)
    SC.facets(S, 0.05, 0.5, tilt=4, seed=83)
    return SC.finish(S, ob, decimate_ratio=0.5, sharp_deg=50.0)


def build_body(col, mat, bar_mat):
    parts = {"Torso": build_torso(col, mat),
             "Arm_R_Long": build_long_arm(col, mat),
             "Arm_L_Short": build_short_arm(col, mat),
             "Leg_R": build_leg(col, mat, "Leg_R", 41),
             "Leg_L": build_leg(col, mat, "Leg_L", 51)}
    parts["Bars"] = build_bars(col, bar_mat, parts)
    return parts
