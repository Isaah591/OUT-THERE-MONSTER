"""
Body of the OUT THERE monster after the ASTRA R08 - MORE OPEN JAW sheet
(references/r08_open_jaw_sheet.webp): a lean, hunched, forward-leaning predator.

Same sculpt pipeline as body_r08.py (sculpt.py): nuanced spline lofts -> remesh -> large-form
brushes -> knife facets -> even re-densify -> rust flake mosaic -> damage that follows the flakes
(torn shell, dark red tissue streaks along the limbs) -> lifted plates -> old blood.

Proportions measured on the sheet relative to the skull width H (~0.53 m): torso ~1.4 H wide,
limbs ~0.5-0.6 H thick, legs ~2.7 H long, overall ~5.6 H. Pose: torso tilted ~30 deg forward,
head thrust ahead of the shoulders, knees bent and splayed, the slim long arm planted on the
ground ahead like a front leg, the short arm hanging forward.

World space, metres, Z up, monster faces -Y, its right (-X) carries the long arm.
"""
import numpy as np
from mathutils import Vector

import bmesh

import sculpt as SC

VOXEL_BASE = 0.011        # base form remesh
VOXEL = 0.0058            # even resolution after the knife facets (flake mosaic, damage)


# ---------------------------------------------------------------------------
# Skeleton / base forms
# ---------------------------------------------------------------------------
TORSO = [  # spine point, +x half-width, -x half-width, front, back, exponent (sections are
           # perpendicular to the spine, which leans ~32 deg forward)
    ((0.000, 0.300, 1.400), 0.340, 0.340, 0.225, 0.235, 3.4),     # pelvis
    ((0.000, 0.220, 1.600), 0.385, 0.382, 0.255, 0.260, 3.8),
    ((0.002, 0.060, 1.880), 0.415, 0.412, 0.275, 0.285, 4.0),     # belly
    ((0.004, -0.180, 2.110), 0.435, 0.430, 0.265, 0.305, 4.0),    # broad chest
    ((0.000, -0.400, 2.300), 0.432, 0.428, 0.232, 0.310, 3.8),    # shoulders, hunched upper back
    ((-0.004, -0.510, 2.410), 0.370, 0.366, 0.165, 0.255, 3.0),   # top
]
NECK = [((0.0, -0.44, 2.26), 0.24, 0.17), ((0.0, -0.64, 2.40), 0.23, 0.17), ((0.0, -0.86, 2.45), 0.22, 0.16)]

LONG_ARM = [  # point, half-width, half-depth, exponent, twist - slim, long, planted far ahead and out
    ((-0.470, -0.400, 2.400), 0.150, 0.145, 2.6, 0),     # shoulder cap
    ((-0.580, -0.430, 2.170), 0.150, 0.145, 4.2, 2),
    ((-0.780, -0.480, 1.880), 0.145, 0.140, 4.2, 4),
    ((-1.050, -0.550, 1.580), 0.156, 0.150, 4.2, 8),     # elbow
    ((-1.160, -0.720, 1.250), 0.155, 0.146, 4.2, 10),
    ((-1.240, -0.920, 0.900), 0.160, 0.148, 4.2, 12),
    ((-1.300, -1.110, 0.560), 0.164, 0.151, 4.2, 14),
    ((-1.340, -1.260, 0.300), 0.169, 0.156, 4.2, 15),
    ((-1.350, -1.340, 0.180), 0.172, 0.158, 4.2, 16),    # blunt end on the ground, far out and ahead
]
SHORT_ARM = [
    ((0.460, -0.400, 2.380), 0.140, 0.138, 2.8, 0),
    ((0.550, -0.440, 2.170), 0.142, 0.138, 4.2, 0),
    ((0.640, -0.500, 1.880), 0.138, 0.132, 4.2, -3),
    ((0.700, -0.550, 1.600), 0.140, 0.134, 4.2, -5),      # elbow
    ((0.740, -0.620, 1.300), 0.136, 0.130, 4.2, -6),
    ((0.760, -0.660, 1.080), 0.133, 0.128, 4.2, -8),      # blunt stump
]
LEGS = {  # crouched: hips back, knees bent well forward, feet back under the hips; splayed
    "Leg_R": [((-0.210, 0.280, 1.460), 0.150, 0.155), ((-0.250, 0.140, 1.220), 0.148, 0.152),
              ((-0.330, -0.100, 0.920), 0.150, 0.155), ((-0.350, -0.160, 0.800), 0.152, 0.158),
              ((-0.355, -0.040, 0.500), 0.138, 0.142), ((-0.360, 0.060, 0.260), 0.132, 0.136),
              ((-0.365, 0.080, 0.100), 0.130, 0.134)],
    "Leg_L": [((0.220, 0.320, 1.460), 0.158, 0.160), ((0.260, 0.240, 1.200), 0.156, 0.158),
              ((0.340, 0.040, 0.900), 0.158, 0.160), ((0.360, 0.000, 0.790), 0.160, 0.162),
              ((0.365, 0.200, 0.500), 0.146, 0.148), ((0.372, 0.380, 0.260), 0.140, 0.142),
              ((0.380, 0.460, 0.100), 0.138, 0.140)],
}


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
        "peel": [((-0.30, -0.36, 2.10), (0.16, 0.12, 0.16), 0.95),      # right chest
                 ((0.38, -0.16, 2.02), (0.10, 0.20, 0.30), 1.0),        # left side, long tear
                 ((-0.38, 0.06, 1.72), (0.10, 0.20, 0.26), 1.0),        # right flank
                 ((0.05, -0.24, 1.72), (0.16, 0.10, 0.14), 0.9),        # belly
                 ((0.10, 0.12, 2.36), (0.18, 0.14, 0.16), 0.9),         # upper back, spikes
                 ((-0.10, 0.42, 1.60), (0.16, 0.10, 0.14), 0.75),
                 ((0.20, -0.06, 1.48), (0.12, 0.10, 0.08), 0.7),
                 ((-0.20, -0.30, 1.95), (0.08, 0.06, 0.20), 0.85)],     # chest streak
        "wound": [((0.39, -0.18, 2.00), (0.05, 0.12, 0.24), 1.0),
                  ((-0.39, 0.04, 1.74), (0.05, 0.12, 0.20), 1.0),
                  ((-0.30, -0.38, 2.08), (0.07, 0.05, 0.08), 1.0),
                  ((-0.20, -0.30, 1.95), (0.04, 0.04, 0.16), 1.0)],
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
FLAPS = {"Torso": 8, "Arm_R_Long": 8, "Arm_L_Short": 5, "Leg_R": 5, "Leg_L": 5}

# Bars: (part, entry hint, direction, length, half width, half depth)
BARS = [
    ("Torso", (0.12, -0.06, 2.46), (0.15, 0.45, 0.88), 0.40, 0.030, 0.019),         # back spikes
    ("Torso", (-0.16, 0.10, 2.32), (-0.25, 0.60, 0.78), 0.32, 0.028, 0.018),
    ("Torso", (0.02, 0.36, 2.08), (0.05, 0.85, 0.55), 0.26, 0.026, 0.017),
    ("Arm_L_Short", (0.50, -0.38, 2.50), (0.25, 0.20, 1.0), 0.30, 0.030, 0.019),     # shoulder spike
    ("Torso", (-0.40, -0.26, 2.00), (-1.0, -0.15, 0.05), 0.24, 0.026, 0.017),        # torso side rods
    ("Torso", (-0.40, -0.02, 1.68), (-1.0, -0.25, -0.05), 0.20, 0.024, 0.016),
    ("Arm_R_Long", tuple(along(LA, 0.70)[0] + np.array([-0.16, 0, 0])), (-1.0, 0.05, 0.25), 0.24, 0.026, 0.017),
    ("Arm_R_Long", tuple(along(LA, 0.86)[0] + np.array([-0.16, 0, 0])), (-1.0, -0.2, -0.1), 0.16, 0.024, 0.016),
    ("Arm_L_Short", tuple(along(SA, 0.50)[0] + np.array([0.14, 0, 0])), (1.0, -0.05, 0.1), 0.20, 0.026, 0.017),
    ("Leg_L", tuple(along(LL, 0.58)[0] + np.array([0.15, 0, 0])), (1.0, -0.1, 0.25), 0.18, 0.024, 0.016),
]
for _part, _hint, *_ in BARS:                      # every bar is driven into its own entry wound
    DAMAGE[_part]["wound"].append((_hint, (0.04, 0.04, 0.05), 1.0))
    DAMAGE[_part]["peel"].append((_hint, (0.08, 0.08, 0.10), 0.95))


# ---------------------------------------------------------------------------
# Part builders
# ---------------------------------------------------------------------------
def _sculpt(S, ob, name, axis, seed, faces, jitter=0.016):
    """knife facets -> even re-densify -> flake mosaic -> damage following the flakes."""
    S.write()
    SC.lowpoly(ob, faces, jitter=jitter, seed=seed, dissolve_deg=5.0, levels=1, remesh_after=VOXEL)
    S = SC.Surf(ob)
    if callable(axis):
        axis = axis(S.co)
    chunk = SC.flakes(S, cell=0.055, crack=0.0035, depth=0.0035, lift=0.005, tilt=0.12, seed=seed + 1)
    d = DAMAGE[name]
    SC.damage(S, d["peel"], d["wound"], axis, seed=seed + 2, n_flaps=FLAPS.get(name, 5), chunk=chunk,
              t1=0.022, t2=0.012, tissue=0.018, lips=0.005, cover=0.42)
    k = S.blur(S.curvature(), 2)
    cv = SC.smoothstep(6.0, 28.0, k)
    gate = SC.smoothstep(0.2, 1.0, SC._z(SC.fbm(SC.Perlin(seed + 3), S.co * 4.0, 2)))
    SC.damage(S, [], [], axis, seed=seed + 4, t1=0.007, t2=0.003, tissue=0.0, lips=0.0,
              extra=1.4 * cv * gate - 0.35, tear_amt=0.0, chunk=chunk)
    SC.blood(S, seed + 5, drips=16)
    SC.finish(S, ob, decimate_ratio=1.0, sharp_deg=25.0)
    SC.add_flaps(ob, getattr(S, "flaps", []), seed + 6)
    return ob


def _base(ob, voxel=VOXEL_BASE):
    SC.remesh(ob, voxel)
    S = SC.Surf(ob)
    S.smooth(4)
    return S


def build_torso(col, mat):
    keys = [{"p": p, "ws": ws, "wn": wn, "df": df, "db": db, "e": e} for p, ws, wn, df, db, e in TORSO]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=48, step=0.02, caps=(0.08, 0.10))
    SC.merge_bm(bm, SC.loft([{"p": p, "w": w, "d": d, "e": 3.0} for p, w, d in NECK],
                            ref=(0, -1, 0), seg=32, step=0.02, caps=(0.04, 0.05)))
    ob = SC.obj_from_bm("Torso", bm, col, [mat])
    S = _base(ob)
    SC.push(S, (0.0, -0.22, 1.80), (0.26, 0.14, 0.22), 0.012)                 # belly
    SC.push(S, (0.0, 0.02, 2.36), (0.30, 0.16, 0.20), 0.020)                  # hunched upper back
    SC.push(S, (0.0, 0.32, 1.92), (0.035, 0.12, 0.40), -0.010)                # spine groove
    SC.push(S, (-0.38, 0.04, 1.90), (0.08, 0.20, 0.30), 0.010)                # asymmetric flanks
    SC.push(S, (0.38, -0.06, 2.10), (0.08, 0.20, 0.22), -0.008)
    for sx in (-1, 1):
        SC.push(S, (sx * 0.38, -0.40, 2.32), (0.09, 0.14, 0.10), -0.016)      # arm sockets
        SC.push(S, (sx * 0.24, -0.30, 2.44), (0.14, 0.16, 0.08), -0.014)      # trapezius slope
    SC.warp(S, 0.010, 1.5, 11)
    SC.dents(S, 8, (0.05, 0.10), (0.006, 0.014), 12)
    return _sculpt(S, ob, "Torso", np.array([0.0, -0.62, 0.78]), 13, 540)


def _limb(col, mat, name, rows, caps):
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=caps, path=True)
    ob = SC.obj_from_bm(name, bm, col, [mat])
    return _base(ob), ob, C, T


def build_long_arm(col, mat):
    S, ob, C, T = _limb(col, mat, "Arm_R_Long", LONG_ARM, (0.10, 0.06))
    SC.flatten(S, (-0.48, -0.40, 2.51), (0.13, 0.13, 0.08), (0.10, -0.05, 1.0), 0.75)     # chiselled cap
    SC.flatten(S, (-0.60, -0.40, 2.43), (0.08, 0.12, 0.08), (-1.0, 0.0, 0.9), 0.8)
    SC.push(S, (-1.19, -0.52, 1.62), (0.08, 0.08, 0.08), 0.012)                         # elbow knob
    SC.push(S, (-0.93, -0.62, 1.52), (0.06, 0.07, 0.08), -0.020)                        # inner elbow notch
    SC.push(S, (-1.44, -1.00, 0.80), (0.06, 0.12, 0.26), 0.008)                         # forearm ridge
    SC.warp(S, 0.010, 1.7, 22)
    SC.dents(S, 9, (0.03, 0.07), (0.005, 0.012), 23)
    _clamp(S)
    return _sculpt(S, ob, "Arm_R_Long", lambda co: SC.path_axes(co, C, T), 24, 380)


def build_short_arm(col, mat):
    S, ob, C, T = _limb(col, mat, "Arm_L_Short", SHORT_ARM, (0.10, 0.035))
    SC.flatten(S, (0.47, -0.40, 2.49), (0.12, 0.12, 0.08), (-0.10, -0.05, 1.0), 0.75)
    SC.flatten(S, (0.58, -0.40, 2.41), (0.08, 0.12, 0.08), (1.0, 0.0, 0.9), 0.8)
    SC.push(S, (0.82, -0.55, 1.62), (0.07, 0.08, 0.10), 0.010)                          # outer elbow
    SC.warp(S, 0.009, 1.8, 32)
    SC.dents(S, 6, (0.03, 0.06), (0.005, 0.011), 33)
    return _sculpt(S, ob, "Arm_L_Short", lambda co: SC.path_axes(co, C, T), 34, 250)


def _foot(x, y_heel, w, seed):
    """Blocky foot with three chunky toes (fused by the remesh, grooves between them)."""
    bm = SC.loft([{"p": (x, y_heel, 0.072), "w": w * 0.92, "df": 0.066, "db": 0.072, "e": 3.4},
                  {"p": (x, y_heel - 0.14, 0.070), "w": w, "df": 0.068, "db": 0.070, "e": 3.6},
                  {"p": (x, y_heel - 0.28, 0.062), "w": w, "df": 0.060, "db": 0.062, "e": 3.6}],
                 ref=(0, -1, 0), seg=32, step=0.02, caps=(0.05, 0.03))
    r = np.random.default_rng(seed)
    tw = w * 2 / 3
    for k in range(3):
        tx = x - w + tw * (k + 0.5)
        tl = r.uniform(0.10, 0.14)
        SC.merge_bm(bm, SC.loft([{"p": (tx, y_heel - 0.26, 0.050), "w": tw * 0.42, "df": 0.046, "db": 0.050, "e": 3.2},
                                 {"p": (tx, y_heel - 0.26 - tl, 0.040), "w": tw * 0.40, "df": 0.036, "db": 0.040, "e": 3.0}],
                                ref=(0, -1, 0), seg=20, step=0.015, caps=(0.01, 0.03)))
    return bm


def build_leg(col, mat, name, seed):
    rows = [(p, w, d, 4.2, (2 if name == "Leg_R" else -3)) for p, w, d in LEGS[name]]
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=(0.04, 0.02), path=True)
    x, y = rows[-1][0][0], rows[-1][0][1]
    SC.merge_bm(bm, _foot(x, y + 0.15, rows[-1][1] + 0.025, seed))
    ob = SC.obj_from_bm(name, bm, col, [mat])
    S = _base(ob, 0.010)
    knee = along(rows, 0.48)[0]
    SC.push(S, tuple(knee + np.array([0, -0.12, 0.0])), (0.10, 0.06, 0.09), 0.012)      # knee cap
    SC.push(S, (x, y, 0.15), (0.16, 0.16, 0.05), -0.008)                                  # ankle
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
