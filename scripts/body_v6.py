"""
v6 body (corrective proportional variation; body_v5.py is kept unchanged): the pose and the limb
proportions are taken from the approved sheet's three-quarter panel, which is the authority.

Every limb centreline was read on the gridded panel (panel pixels, 508 x 495) and put back into
3D on the lines of sight of the fitted three-quarter camera (ref34_camera.py): the feet and the
long arm's club stand on the floor where the panel shows them, joints that attach to the torso
keep their place, the depths in between are interpolated, and each knee sits on its line of
sight with equal thigh and shin lengths. From that camera every limb centreline therefore lies on
the reference's; thickness is set separately (slimmer, more irregular arms).

Changes against v5: torso longer with a narrower waist, tilted further forward, a heavier,
asymmetric hunched upper back (left shoulder high, right shoulder dropping), a leaner chest;
long arm slimmer, abducted at the shoulder and hanging almost straight down to a club on the
floor; short arm slimmer and angled out; legs bent and splayed to an uneven stance (the left leg
planted far out to the side, the right foot forward under the body); broad, damaged feet turned
with the legs. Same sculpt and surface pipeline as v5.

World space, metres, Z up, monster faces -Y, its right (-X) carries the long arm.
"""
import numpy as np
from mathutils import Vector

import bmesh

import ref34_camera as RC
import sculpt as SC
import surface_v5 as SV

VOXEL_BASE = 0.011        # base form remesh
VOXEL = 0.0058            # even resolution after the knife facets (flake mosaic, damage)


# ---------------------------------------------------------------------------
# Pose from the reference (three-quarter panel, fitted camera)
# ---------------------------------------------------------------------------
def _depth(p):
    return float((np.asarray(p, float) - RC.LOC) @ RC.FWD)


def _chain(start3d, pix, end3d):
    """3D points on the lines of sight of the panel pixels `pix`; their depth runs from start3d's
    to end3d's in proportion to the distance travelled along the image path."""
    uv0 = RC.project([start3d])[0][0]
    uv1 = RC.project([end3d])[0][0]
    pts = [np.asarray(uv0)] + [np.asarray(q, float) for q in pix] + [np.asarray(uv1)]
    seg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    t = seg / seg[-1]
    d0, d1 = _depth(start3d), _depth(end3d)
    return [RC.at_depth(u, v, d0 + (d1 - d0) * tt) for (u, v), tt in zip(pts[1:-1], t[1:-1])]


def _knee(hip, knee_pix, ankle, length):
    """The knee on its line of sight such that thigh + shin = `length` (a bent leg of fixed
    length); of the two solutions the one with the more even thigh and shin."""
    o, d = RC.ray(*knee_pix)
    h, a = np.asarray(hip, float), np.asarray(ankle, float)
    f = lambda s_: np.linalg.norm(o + s_ * d - h) + np.linalg.norm(o + s_ * d - a) - length
    ss = np.linspace(2.0, 9.0, 1401)
    fs = np.array([f(x) for x in ss])
    roots = []
    for i in np.flatnonzero(np.sign(fs[:-1]) != np.sign(fs[1:])):
        lo, hi = ss[i], ss[i + 1]
        for _ in range(50):
            mid = (lo + hi) / 2
            if np.sign(f(mid)) == np.sign(f(lo)):
                lo = mid
            else:
                hi = mid
        k = o + lo * d
        roots.append((abs(np.linalg.norm(k - h) - np.linalg.norm(k - a)), k))
    if not roots:                                   # leg too short to reach: straight leg
        return h + (a - h) * 0.5
    return min(roots, key=lambda r: r[0])[1]


# panel-pixel landmarks read on the gridded reference panel
# (centrelines = middles of the reference silhouette's runs on those rows; refmask in v6 notes)
LA_PIX = [(149, 170), (137, 200), (110, 250), (96, 300), (81, 350), (70, 400), (62, 438)]   # long arm
LA_CLUB = (60, 477)                     # bottom of the club on the floor
SA_PIX = [(338, 160), (358, 205), (380, 250), (391, 280)]                       # short arm centreline
SA_END = (396, 312)                     # centre of the short arm's blunt end
LEG_PIX = {   # thigh points, knee, shin points
    "Leg_R": ([(255, 295)], (235, 338), [(248, 370), (261, 400)]),
    "Leg_L": ([(338, 302)], (350, 340), [(366, 370), (380, 400)]),
}
FEET_PIX = {  # where each foot meets the floor in the panel: heel, toe tips (the foot lies flat between)
    "Leg_R": ((300, 458), (220, 463)),       # turned out to its right, a long block across the view
    "Leg_L": ((403, 447), (392, 478)),       # pointing at the viewer
}
HIPS = {"Leg_R": np.array([-0.215, 0.240, 1.290]), "Leg_L": np.array([0.305, 0.300, 1.270])}
LEG_LEN = {"Leg_R": 1.60, "Leg_L": 1.64}          # hip -> knee -> ankle (v5: 1.54)
LA_SHOULDER = np.array([-0.480, -0.470, 2.300])     # right shoulder drops
SA_SHOULDER = np.array([0.470, -0.450, 2.420])      # left shoulder rides high


def _club_end():
    g = RC.on_plane_z(*LA_CLUB, 0.0)                 # the club's lowest edge touches the floor
    return g + np.array([0.0, 0.0, 0.165])


def _short_arm_end():
    return RC.at_depth(*SA_END, _depth(SA_SHOULDER) - 0.16)


TORSO = [  # spine point, +x half-width, -x half-width, front, back, exponent (sections are
           # perpendicular to the spine, which leans ~41 deg forward)
    ((0.000, 0.300, 1.230), 0.300, 0.298, 0.212, 0.222, 3.2),     # pelvis, lower: a longer torso
    ((0.020, 0.225, 1.450), 0.372, 0.318, 0.236, 0.246, 3.0),     # narrow waist (fuller on the left flank)
    ((0.050, 0.030, 1.780), 0.520, 0.380, 0.312, 0.300, 2.8),     # heavy rounded belly, swelling to its left
    ((0.040, -0.230, 2.060), 0.505, 0.412, 0.262, 0.345, 3.0),    # chest under a heavy back
    ((0.020, -0.490, 2.250), 0.470, 0.400, 0.200, 0.352, 3.2),    # hunched upper back, left side broader
    ((0.000, -0.640, 2.330), 0.382, 0.340, 0.142, 0.272, 3.0),    # top
]
NECK = [((0.0, -0.52, 2.22), 0.24, 0.17), ((0.0, -0.70, 2.36), 0.23, 0.17), ((0.0, -0.88, 2.43), 0.22, 0.16)]


def _rows(points, widths, depths, exps, twists):
    return [(tuple(float(c) for c in p), w, d, e, r) for p, w, d, e, r in zip(points, widths, depths, exps, twists)]


_LA_PTS = [LA_SHOULDER, LA_SHOULDER + np.array([-0.13, -0.03, -0.03])]
_LA_PTS += _chain(_LA_PTS[-1], LA_PIX, _club_end()) + [_club_end()]
LONG_ARM = _rows(_LA_PTS,   # long and bony, uneven along its length, flaring into a heavy blunt club
                 [0.140, 0.136, 0.132, 0.140, 0.146, 0.136, 0.150, 0.180, 0.208, 0.226],
                 [0.134, 0.128, 0.124, 0.134, 0.138, 0.128, 0.142, 0.170, 0.196, 0.214],
                 [2.6, 3.8, 3.8, 4.0, 3.6, 3.8, 3.8, 4.0, 4.0, 4.0],
                 [0, 3, 6, 9, 10, 12, 14, 15, 16, 16])
_SA_PTS = [SA_SHOULDER, SA_SHOULDER + np.array([0.05, -0.01, -0.12])]
_SA_PTS += _chain(_SA_PTS[-1], SA_PIX, _short_arm_end()) + [_short_arm_end()]
SHORT_ARM = _rows(_SA_PTS,
                  [0.142, 0.140, 0.134, 0.142, 0.136, 0.140, 0.152],
                  [0.136, 0.132, 0.126, 0.134, 0.128, 0.132, 0.144],
                  [2.8, 3.8, 3.8, 4.0, 3.6, 3.8, 3.8],
                  [0, 0, -3, -5, -6, -7, -8])


def _leg(name):
    thigh, knee_pix, shin = LEG_PIX[name]
    hip = HIPS[name]
    heel, toe = (RC.on_plane_z(u, v, 0.0) for u, v in FEET_PIX[name])
    ankle = heel + (toe - heel) * 0.28 + np.array([0.0, 0.0, 0.13])        # above the back of the foot
    knee = _knee(hip, knee_pix, ankle, LEG_LEN[name])
    pts = [hip] + _chain(hip, thigh, knee) + [knee] + _chain(knee, shin, ankle) + [ankle]
    return pts, (heel, toe)


FOOT_W = {"Leg_R": 0.205, "Leg_L": 0.185}          # broad feet (half-widths)
LEGS, TOES = {}, {}
for _n, _w in (("Leg_R", (0.168, 0.158, 0.156, 0.142, 0.136, 0.134)),
               ("Leg_L", (0.164, 0.156, 0.154, 0.140, 0.134, 0.132))):
    _pts, TOES[_n] = _leg(_n)
    LEGS[_n] = [(tuple(float(c) for c in p), w, w + 0.004) for p, w in zip(_pts, _w)]


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
FLAPS = {"Torso": 0, "Arm_R_Long": 0, "Arm_L_Short": 0, "Leg_R": 0, "Leg_L": 0}      # no lifted plates

# Bars: (part, entry hint, direction, length, half width, half depth)
BARS = [
    ("Torso", (0.12, -0.06, 2.46), (0.30, 0.45, 0.80), 0.27, 0.030, 0.019),         # back spikes
    ("Torso", (-0.16, 0.10, 2.32), (-0.25, 0.60, 0.78), 0.24, 0.028, 0.018),
    ("Torso", (0.02, 0.36, 2.08), (0.05, 0.85, 0.55), 0.26, 0.026, 0.017),
    ("Arm_L_Short", (0.50, -0.38, 2.50), (0.25, 0.20, 1.0), 0.22, 0.030, 0.019),     # shoulder spike
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
    """knife facets -> even re-densify -> thin crack network -> embedded damage -> pits, erosion."""
    S.write()
    SC.lowpoly(ob, faces, jitter=jitter, seed=seed, dissolve_deg=5.0, levels=1, remesh_after=VOXEL)
    S = SC.Surf(ob)
    if callable(axis):
        axis = axis(S.co)
    chunk = SV.crack_network(S, cell=0.085, width=0.0024, depth=0.0028, seed=seed + 1, tilt=0.03)
    d = DAMAGE[name]
    wounds = [(c, tuple(np.asarray(r) * 1.00), st) for c, r, st in d["wound"]]
    peels = [(c, tuple(np.asarray(r) * 1.08), st) for c, r, st in d["peel"]]          # larger, irregular torn regions
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
    keys = [{"p": p, "ws": ws, "wn": wn, "df": df, "db": db, "e": e} for p, ws, wn, df, db, e in TORSO]
    bm = SC.loft(keys, ref=(0, -1, 0), seg=48, step=0.02, caps=(0.08, 0.10))
    SC.merge_bm(bm, SC.loft([{"p": p, "w": w, "d": d, "e": 3.0} for p, w, d in NECK],
                            ref=(0, -1, 0), seg=32, step=0.02, caps=(0.04, 0.05)))
    ob = SC.obj_from_bm("Torso", bm, col, [mat])
    S = _base(ob)
    SC.push(S, (0.12, -0.30, 1.80), (0.28, 0.16, 0.24), 0.034)                # big round belly, off-centre
    SC.push(S, (0.10, -0.04, 2.34), (0.32, 0.18, 0.20), 0.032)                # heavy hunched upper back, off-centre
    SC.push(S, (0.0, 0.28, 1.92), (0.035, 0.12, 0.40), -0.010)                # spine groove
    SC.push(S, (-0.36, 0.04, 1.86), (0.08, 0.20, 0.30), 0.010)                # asymmetric flanks
    SC.push(S, (0.36, -0.08, 2.06), (0.08, 0.20, 0.22), -0.008)
    SC.push(S, (0.38, -0.40, 2.42), (0.15, 0.16, 0.11), 0.032)                # left shoulder rides high
    SC.push(S, (-0.36, -0.44, 2.36), (0.14, 0.16, 0.10), -0.022)              # right shoulder drops
    for sx in (-1, 1):
        SC.push(S, (sx * 0.40, -0.46, 2.27), (0.09, 0.14, 0.10), -0.016)      # arm sockets
        SC.push(S, (sx * 0.24, -0.36, 2.40), (0.14, 0.16, 0.08), -0.014)      # trapezius slope
    SC.warp(S, 0.010, 1.5, 11)
    SC.dents(S, 8, (0.05, 0.10), (0.006, 0.014), 12)
    return _sculpt(S, ob, "Torso", np.array([0.0, -0.62, 0.78]), 13, 540)


def _limb(col, mat, name, rows, caps):
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=caps, path=True)
    ob = SC.obj_from_bm(name, bm, col, [mat])
    return _base(ob), ob, C, T


def build_long_arm(col, mat):
    S, ob, C, T = _limb(col, mat, "Arm_R_Long", LONG_ARM, (0.10, 0.03))
    P = [np.asarray(r[0]) for r in LONG_ARM]
    SC.flatten(S, tuple(P[0] + (0, 0, 0.11)), (0.12, 0.12, 0.08), (0.10, -0.05, 1.0), 0.75)  # chiselled cap
    SC.flatten(S, tuple(P[0] + (-0.11, 0, 0.03)), (0.08, 0.11, 0.08), (-1.0, 0.0, 0.9), 0.8)
    SC.push(S, tuple(P[4] + (-0.07, 0.07, 0.03)), (0.07, 0.07, 0.07), 0.014)              # bony elbow knob
    SC.push(S, tuple(P[4] + (0.06, -0.06, -0.02)), (0.05, 0.06, 0.07), -0.018)            # inner elbow notch
    SC.push(S, tuple(P[6] + (-0.09, 0.0, 0.0)), (0.05, 0.10, 0.22), 0.008)                # forearm ridge
    SC.push(S, tuple(P[3] + (0.05, -0.05, 0.0)), (0.05, 0.08, 0.16), -0.012)              # wasted upper arm
    SC.push(S, tuple(P[7] + (0.06, 0.04, 0.0)), (0.05, 0.06, 0.14), -0.010)
    SC.warp(S, 0.010, 1.7, 22)
    SC.dents(S, 9, (0.03, 0.07), (0.005, 0.012), 23)
    _clamp(S)
    return _sculpt(S, ob, "Arm_R_Long", lambda co: SC.path_axes(co, C, T), 24, 380)


def build_short_arm(col, mat):
    S, ob, C, T = _limb(col, mat, "Arm_L_Short", SHORT_ARM, (0.10, 0.035))
    P = [np.asarray(r[0]) for r in SHORT_ARM]
    SC.flatten(S, tuple(P[0] + (0, 0, 0.10)), (0.11, 0.11, 0.08), (-0.10, -0.05, 1.0), 0.75)
    SC.flatten(S, tuple(P[0] + (0.10, 0, 0.02)), (0.08, 0.11, 0.08), (1.0, 0.0, 0.9), 0.8)
    SC.push(S, tuple(P[3] + (0.09, 0.05, 0.0)), (0.06, 0.07, 0.09), 0.012)                # outer elbow
    SC.push(S, tuple(P[4] + (-0.05, -0.04, 0.0)), (0.05, 0.06, 0.12), -0.010)             # wasted forearm
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
    bm = SC.loft([{"p": P(0.0, 0.090), "w": w * 0.92, "df": 0.086, "db": 0.090, "e": 4.4},
                  {"p": P(body * 0.5, 0.090), "w": w, "df": 0.088, "db": 0.090, "e": 4.6},
                  {"p": P(body, 0.080), "w": w * 1.04, "df": 0.078, "db": 0.080, "e": 4.6}],
                 ref=(0, 0, 1), seg=32, step=0.02, caps=(0.04, 0.02))
    r = np.random.default_rng(seed)
    nt = 4 if w > 0.175 else 3
    tw = 2 * w * 1.04 / nt
    for k in range(nt):
        o = -w * 1.04 + tw * (k + 0.5)
        tl = r.uniform(0.06, 0.10)
        h = r.uniform(0.050, 0.064)
        SC.merge_bm(bm, SC.loft([{"p": P(body - 0.03, h, o), "w": tw * 0.46, "df": h - 0.004, "db": h, "e": 4.0},
                                 {"p": P(body - 0.03 + tl, h * 0.9, o), "w": tw * 0.44,
                                  "df": h * 0.86, "db": h * 0.9, "e": 4.0}],
                                ref=(0, 0, 1), seg=20, step=0.015, caps=(0.01, 0.015)))
    return bm


def build_leg(col, mat, name, seed):
    rows = [(p, w, d, 4.2, (2 if name == "Leg_R" else -3)) for p, w, d in LEGS[name]]
    bm, C, T = SC.loft(limb_keys(rows), ref=(0, -1, 0), seg=40, step=0.02, caps=(0.04, 0.02), path=True)
    ankle = np.asarray(rows[-1][0])
    SC.merge_bm(bm, _foot(*TOES[name], FOOT_W[name], seed))
    ob = SC.obj_from_bm(name, bm, col, [mat])
    S = _base(ob, 0.010)
    hip, knee = np.asarray(rows[0][0]), np.asarray(rows[2][0])
    b = SC.unit(SC.unit(knee - hip) - SC.unit(ankle - knee))      # the way the knee juts out
    if not np.all(np.isfinite(b)) or np.linalg.norm(b) < 0.5:
        b = np.array([0.0, -1.0, 0.0])
    SC.push(S, tuple(knee + b * 0.11), (0.10, 0.10, 0.10), 0.014)                      # bony knee
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
