"""
Blueprint reconstruction of the approved sheet's skeleton from its three views.

    python sheet_blueprint.py [R_forward|L_forward]

Joint landmarks were read on gridded crops of the sheet's FRONT, SIDE (EXACT) and THREE-QUARTER
panels (panel pixels). A joint least-squares solve then finds one 3D position per joint plus the
three cameras that best explain all the views at once: front and side as orthographic views
(scale and offset; the front scale fixes the size), the three-quarter view as a perspective
camera (azimuth, elevation, distance, focal length, lens shift). The floor is z = 0 at the toes.
Residuals per view and per joint show where the sheet's views agree and where they do not.

The side view does not say which leg is the near one: "R_forward" (default) assumes the monster's
right foot is the forward one, "L_forward" the opposite; the smaller residual decides.
"""
import json
import math
import os
import sys

import numpy as np
from scipy.optimize import least_squares

# ---- landmarks (panel pixels): front (u, v) | side (u, v) | three-quarter (u, v); None = not visible
#  front: monster facing the viewer, its right on the left; side: from its left, facing left
J = {
    "head_top":    ((263, 20), (160, 44), (205, 42)),
    "snout":       ((263, 58), (86, 102), (200, 99)),       # front-centre of the upper gum line
    "chin":        ((270, 155), (152, 228), (205, 210)),
    "eye_R":       ((245, 43), None, (170, 82)),
    "eye_L":       ((288, 40), None, (210, 76)),
    "hinge":       (None, (205, 125), None),
    "shoulder_R":  ((192, 108), (268, 118), None),          # long arm (hidden behind the head in 3/4)
    "shoulder_L":  ((350, 112), (272, 115), (322, 118)),    # short arm
    "hump":        (None, (295, 68), (300, 62)),
    "hip_R":       ((248, 262), None, (262, 272)),
    "hip_L":       ((322, 262), None, (318, 272)),
    "pelvis":      ((285, 262), (362, 298), None),
    "la_elbow":    ((135, 205), (245, 250), (112, 250)),
    "la_wrist":    ((99, 380), (175, 400), (68, 410)),
    "la_club":     ((96, 478), (145, 478), (60, 477)),
    "sa_elbow":    ((380, 205), (295, 215), (360, 205)),
    "sa_end":      ((395, 325), (310, 322), (398, 318)),
    "knee_R":      ((245, 340), None, (235, 338)),
    "knee_L":      ((338, 338), None, (350, 340)),
    "ankle_R":     ((240, 430), None, (272, 428)),
    "ankle_L":     ((352, 428), None, (393, 430)),
    "toe_R":       ((235, 462), None, (220, 463)),
    "toe_L":       ((356, 462), None, (392, 478)),
}
SIDE_LEGS = {  # side view: forward leg (image left) and back leg
    "fwd": {"knee": (318, 345), "ankle": (330, 430), "toe": (285, 466)},
    "back": {"knee": (405, 342), "ankle": (425, 430), "toe": (395, 468)},
}
W_VIEW = {"front": 1.0, "side": 1.0, "34": 1.5}
PANEL_WH = {"front": (490, 495), "side": (467, 495), "34": (508, 495)}
TARGET = np.array([-0.15, -0.55, 1.45])
S_FRONT = 160.0                      # px per metre in the front panel (sets the size: skull ~0.52 m wide)


def setup(mode):
    j = {k: list(v) for k, v in J.items()}
    fwd, back = ("R", "L") if mode == "R_forward" else ("L", "R")
    for part in ("knee", "ankle", "toe"):
        j["%s_%s" % (part, fwd)][1] = SIDE_LEGS["fwd"][part]
        j["%s_%s" % (part, back)][1] = SIDE_LEGS["back"][part]
    return j


def persp(P, c, view="34"):
    az, el, dist, lens, sx, sy = c
    W, H = PANEL_WH[view]
    loc = TARGET + dist * np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    fwd = (TARGET - loc) / np.linalg.norm(TARGET - loc)
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = P - loc
    z = rel @ fwd
    x, y = (rel @ right) / z, (rel @ up) / z
    k = lens / 36.0 * W
    return np.stack([W / 2 + (x + sx * 36.0 / lens) * k, H / 2 - (y + sy * 36.0 / lens) * k], -1)


def solve(mode):
    j = setup(mode)
    names = list(j)
    n = len(names)
    # initial guess: from the front (x, z) and side (y) with rough scales
    P0 = []
    for k in names:
        f, s_, q = j[k]
        x = (f[0] - 278) / S_FRONT if f else 0.0
        z = (462 - f[1]) / S_FRONT if f else (468 - s_[1]) / S_FRONT
        y = (s_[0] - 312) / S_FRONT if s_ else -0.4
        P0.append((x, y, z))
    P0 = np.array(P0, float)
    cam0 = np.array([math.radians(28), math.radians(9), 5.5, 60.0, -0.05, -0.015])
    side0 = np.array([S_FRONT, 312.0, 468.0])
    front0 = np.array([278.0, 462.0])
    x0 = np.concatenate([P0.ravel(), front0, side0, cam0])

    def unpack(x):
        P = x[:3 * n].reshape(n, 3)
        u0f, v0f = x[3 * n:3 * n + 2]
        ss, u0s, v0s = x[3 * n + 2:3 * n + 5]
        cam = x[3 * n + 5:]
        return P, (u0f, v0f), (ss, u0s, v0s), cam

    def res(x):
        P, (u0f, v0f), (ss, u0s, v0s), cam = unpack(x)
        r = []
        Q = persp(P, cam)
        for i, k in enumerate(names):
            f, s_, q = j[k]
            if f:
                r += [W_VIEW["front"] * (u0f + S_FRONT * P[i, 0] - f[0]), W_VIEW["front"] * (v0f - S_FRONT * P[i, 2] - f[1])]
            if s_:
                r += [W_VIEW["side"] * (u0s + ss * P[i, 1] - s_[0]), W_VIEW["side"] * (v0s - ss * P[i, 2] - s_[1])]
            if q:
                r += [W_VIEW["34"] * (Q[i, 0] - q[0]), W_VIEW["34"] * (Q[i, 1] - q[1])]
        for k in ("toe_R", "toe_L"):                       # the toes stand on the floor
            r.append(20.0 * P[names.index(k), 2])
        r.append(2.0 * P[names.index("pelvis"), 0])      # gauge: x = 0 at the pelvis
        r.append(2.0 * (P[names.index("pelvis"), 1] - 0.30))   # gauge: pelvis at y = 0.30 (as v5)
        # weak anatomical ties for joints that only one view sees in depth
        g = lambda a: P[names.index(a)]
        r.append(4.0 * (g("hinge")[0] - g("snout")[0]))                      # hinge on the head's midline
        for e in ("eye_R", "eye_L"):
            r.append(6.0 * (g(e)[1] - (g("snout")[1] + 0.06)))               # eyes just behind the snout front
        for h in ("hip_R", "hip_L"):
            r.append(3.0 * (g(h)[1] - g("pelvis")[1]))                       # hips level with the pelvis in depth
        r.append(3.0 * (g("head_top")[0] - g("snout")[0]))
        return np.array(r)

    lo = np.full_like(x0, -np.inf)
    hi = np.full_like(x0, np.inf)
    lo[-6:] = [math.radians(-10), math.radians(-10), 2.5, 20.0, -0.5, -0.5]      # plausible camera
    hi[-6:] = [math.radians(60), math.radians(40), 25.0, 250.0, 0.5, 0.5]
    sol = least_squares(res, x0, loss="soft_l1", f_scale=6.0, max_nfev=20000, bounds=(lo, hi))
    P, fr, sd, cam = unpack(sol.x)
    # per-view residuals
    Q = persp(P, cam)
    rep = {}
    for i, k in enumerate(names):
        f, s_, q = j[k]
        e = {}
        if f:
            e["front"] = float(np.hypot(fr[0] + S_FRONT * P[i, 0] - f[0], fr[1] - S_FRONT * P[i, 2] - f[1]))
        if s_:
            e["side"] = float(np.hypot(sd[1] + sd[0] * P[i, 1] - s_[0], sd[2] - sd[0] * P[i, 2] - s_[1]))
        if q:
            e["34"] = float(np.hypot(Q[i, 0] - q[0], Q[i, 1] - q[1]))
        rep[k] = e
    return names, P, fr, sd, cam, rep, sol.cost


if __name__ == "__main__":
    modes = sys.argv[1:] or ["R_forward", "L_forward"]
    for mode in modes:
        names, P, fr, sd, cam, rep, cost = solve(mode)
        print("== %s: cost %.0f" % (mode, cost))
        print("   side scale %.1f px/m (front %.0f); three-quarter camera az %.1f el %.1f dist %.2f lens %.1f shift %.3f %.3f"
              % (sd[0], S_FRONT, math.degrees(cam[0]), math.degrees(cam[1]), cam[2], cam[3], cam[4], cam[5]))
        for v in ("front", "side", "34"):
            errs = [e[v] for e in rep.values() if v in e]
            print("   %-5s mean residual %.1f px, max %.1f px" % (v, np.mean(errs), np.max(errs)))
        for k, p in zip(names, P):
            print("   %-11s %s   residuals %s" % (k, np.round(p, 3), {a: round(b, 1) for a, b in rep[k].items()}))
        json.dump({"mode": mode, "joints": {k: [float(c) for c in p] for k, p in zip(names, P)},
                   "camera34": [float(c) for c in cam], "side": [float(c) for c in sd], "front": [float(c) for c in fr]},
                  open(os.path.join(os.environ.get("BLUEPRINT_OUT", "."), "sheet_blueprint_%s.json" % mode), "w"),
                  indent=1)
