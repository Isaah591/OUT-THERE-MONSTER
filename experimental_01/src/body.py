"""ASTRA R08 body - Experimental Model 01.

Every number below was read off the approved sheet (measure_sheet.py and the panel crops): the
exact side view gives depth and lean, the front view gives widths and the sideways spread of the
limbs, the three-quarter view checks the two against each other.  Units: metres, Z up, the
creature faces -Y, its left is +X (so the very long arm is on -X).  Overall height 2.8 m.
"""
import numpy as np
import kernel as K
from model import wound_on, rod_on

X = np.array([1.0, 0.0, 0.0])

# ---- joints (m) ------------------------------------------------------------------------------
POSE = dict(   # after fit_pose.py (silhouette fit to the sheet's front, three-quarter and side panels)
    lean=36.0,                                   # torso forward lean, degrees (side view)
    hip=[0.005, 0.025, 1.385],
    torso_len=1.09,
    torso_w=0.97, torso_d=0.91,                    # width / depth multipliers
    arm_long=[[-0.555, -0.6, 2.33], [-0.56, -0.605, 2.25], [-0.75, -0.725, 1.855], [-0.98, -0.71, 1.475], [-1.035, -1.075, 0.795], [-1.035, -1.48, 0.105]],
    arm_long_w=0.8, arm_long_d=1.0,
    arm_short=[[0.445, -0.66, 2.335], [0.455, -0.69, 2.2], [0.635, -0.47, 1.69], [0.715, -0.375, 1.305], [0.745, -0.475, 0.93]],
    arm_short_w=0.96, arm_short_d=1.0,
    hipR=[-0.145, -0.02, 1.46], kneeR=[-0.25, -0.465, 0.875], ankR=[-0.24, -0.08, 0.25],
    hipL=[0.18, 0.015, 1.41], kneeL=[0.34, 0.11, 0.915], ankL=[0.475, 0.355, 0.305],
    leg_w=0.92, leg_d=0.84,
    footR=0.6, footL=0.46, toeR=[-0.06, -1.0], toeL=[0.1, -1.0],
    neck_end=[0.04, -0.94, 2.475],
)

BODY = dict(cell=0.017, plate=(0.17, 0.135))


def build_body(m, pose=None):
    rng = m.rng
    Pz = dict(POSE)
    Pz.update(pose or {})
    LEAN = np.radians(Pz["lean"])
    HIP = np.array(Pz["hip"], float)
    TORSO_AX = np.array([0.0, -np.sin(LEAN), np.cos(LEAN)])
    TL = Pz["torso_len"] / 1.15

    def torso_point(s, x=0.0, back=0.0):
        """Point at height s along the torso axis, x sideways, `back` toward the creature's back."""
        bdir = np.cross(TORSO_AX, X)                     # back-up
        return HIP + TORSO_AX * s * TL + X * x + bdir * back
    # ------------------------------------------------------------------ torso
    # broad compact block; its right flank (-X) slopes inward toward the hips (front view)
    ts = [-0.10, 0.08, 0.42, 0.82, 1.06, 1.15]
    hw = [(0.33, 0.25), (0.385, 0.315), (0.40, 0.375), (0.405, 0.405), (0.395, 0.395), (0.31, 0.31)]   # (+x, -x)
    hd = [(0.20, 0.21), (0.255, 0.265), (0.275, 0.295), (0.255, 0.275), (0.225, 0.235), (0.17, 0.18)]  # (back, front)
    P = [torso_point(s) for s in ts]
    halves = [(a[0] * Pz["torso_w"], a[1] * Pz["torso_w"], b[0] * Pz["torso_d"], b[1] * Pz["torso_d"]) for a, b in zip(hw, hd)]
    torso = m.part(K.loft("torso", P, halves, X, chamfer=0.20, rng=rng, jit=0.007), params=BODY)
    wound_on(torso, 0.40, (-0.35, -1, -0.5), 0.10, 0.135, axis=X)            # belly, creature's right
    wound_on(torso, 0.52, (-1, -0.2, 0), 0.17, 0.075)                         # right flank
    wound_on(torso, 0.66, (1, 0.25, 0.1), 0.30, 0.095)                        # left flank, long tear
    wound_on(torso, 0.74, (0.75, -1, -0.6), 0.065, 0.055)                     # chest under left shoulder
    wound_on(torso, 0.30, (0.3, 1, 0.6), 0.12, 0.08)                          # lower back
    wound_on(torso, 0.78, (-0.4, 1, 0.7), 0.10, 0.07)                         # upper back
    wound_on(torso, 0.18, (0.5, -1, -0.6), 0.05, 0.06, axis=X)

    # pelvis block between the thighs
    m.part(K.box("pelvis", (hip_mid := (np.array(Pz["hipR"], float) + np.array(Pz["hipL"], float)) / 2) + np.array([0.0, 0.02, -0.22]), X, (0, 1, 0), (0, 0, 1),
                 (0.105, 0.115, 0.085), rng=rng, jit=0.006, taper=(1.25, 1.2)), params=BODY)

    # ------------------------------------------------------------------ long arm (creature's right)
    A = [np.array(p, float) for p in Pz["arm_long"]]
    ah = [(0.145, 0.175), (0.140, 0.175), (0.128, 0.165), (0.140, 0.175), (0.172, 0.205), (0.205, 0.235)]
    ah = [(a * Pz["arm_long_w"], b * Pz["arm_long_d"]) for a, b in ah]
    larm = m.part(K.loft("arm_long", A, ah, X, chamfer=0.24, rng=rng, jit=0.008, caps=("plate", "plate")), params=BODY)
    wound_on(larm, 0.12, (-0.5, -1, 0.2), 0.13, 0.060)
    wound_on(larm, 0.27, (-0.2, -1, 0), 0.10, 0.052)
    wound_on(larm, 0.42, (-0.35, -1, 0), 0.17, 0.078)
    wound_on(larm, 0.63, (-0.25, -1, 0), 0.23, 0.085)
    wound_on(larm, 0.86, (0.1, -1, 0), 0.13, 0.062)
    wound_on(larm, 0.60, (1, -0.15, 0), 0.31, 0.095, spacing=0.05)            # inner face, seen in the side view
    wound_on(larm, 0.90, (1, 0.2, 0), 0.075, 0.04)
    wound_on(larm, 0.34, (-1, 0.3, 0), 0.12, 0.06)
    # the blunt, hollow-looking end
    co = larm["coarse"]
    endc = co.arrays()[co.rings[-1]].mean(0)
    T = co.frames[0][-1]
    larm["wounds"].add(endc, co.frames[1][-1], 0.15, 0.17, normal=T, strength=1.0)
    larm["wounds"].z[-1]["strands"] = False

    # ------------------------------------------------------------------ short arm (creature's left)
    B = [np.array(p, float) for p in Pz["arm_short"]]
    bh = [(0.140, 0.170), (0.135, 0.168), (0.122, 0.165), (0.145, 0.185), (0.152, 0.198)]
    bh = [(a * Pz["arm_short_w"], b * Pz["arm_short_d"]) for a, b in bh]
    sarm = m.part(K.loft("arm_short", B, bh, X, chamfer=0.24, rng=rng, jit=0.007), params=BODY)
    wound_on(sarm, 0.25, (0.6, -1, 0), 0.12, 0.052)
    wound_on(sarm, 0.70, (1, -0.7, 0), 0.085, 0.046)
    wound_on(sarm, 0.72, (1, 0.3, 0), 0.09, 0.042)
    wound_on(sarm, 0.45, (-0.3, -1, 0), 0.07, 0.04)
    co = sarm["coarse"]
    sarm["wounds"].add(co.arrays()[co.rings[-1]].mean(0), co.frames[1][-1], 0.10, 0.13, normal=co.frames[0][-1])
    sarm["wounds"].z[-1]["strands"] = False

    # ------------------------------------------------------------------ legs
    LW, LD = Pz["leg_w"], Pz["leg_d"]

    def leg(name, hip, knee, ankle, toe_dir, foot_len, sign):
        th = m.part(K.loft(f"thigh_{name}", [hip + (0, 0, 0.06), (hip + knee) / 2 + (0, -0.012, 0), knee + (knee - hip) * 0.04],
                           [(0.118 * LW, 0.150 * LD), (0.112 * LW, 0.145 * LD), (0.108 * LW, 0.140 * LD)], X, chamfer=0.22, rng=rng, jit=0.006), params=BODY)
        k2 = knee + K.unit(hip - knee) * 0.075
        sh = m.part(K.loft(f"shin_{name}", [k2, knee + (ankle - knee) * 0.30, ankle + (ankle - knee) * 0.02],
                           [(0.140 * LW, 0.168 * LD), (0.130 * LW, 0.158 * LD), (0.122 * LW, 0.150 * LD)], X, chamfer=0.22, rng=rng, jit=0.007), params=BODY)
        # foot: ankle block, sloping instep, four block toes
        td = K.unit(np.array([toe_dir[0], toe_dir[1], 0.0]))
        sd = np.cross((0, 0, 1), td) * 1.0
        heel = np.array([ankle[0], ankle[1], 0.0]) - td * 0.10
        fw = 0.150
        Pf = [heel + (0, 0, 0.115), heel + td * 0.21 + (0, 0, 0.105), heel + td * (foot_len - 0.15) + (0, 0, 0.062)]
        fh = [(fw * 0.86, 0.115), (fw, 0.105), (fw * 1.04, 0.062)]
        ft = m.part(K.loft(f"foot_{name}", Pf, fh, sd, chamfer=0.25, rng=rng, jit=0.005), params=BODY)
        # ankle block rising into the shin
        m.part(K.box(f"ankle_{name}", heel + td * 0.07 + (0, 0, 0.225), sd, td, (0, 0, 1), (0.128, 0.150, 0.075),
                     rng=rng, jit=0.006, taper=(0.92, 0.9)), params=BODY)
        n_toe = 4
        tw = 2 * fw * 1.04 / n_toe
        for k in range(n_toe):
            off = (-fw * 1.04 + tw * (k + 0.5))
            ln = 0.150 + 0.022 * rng.random() - 0.012 * abs(k - 1.5)
            c = heel + td * (foot_len - 0.15 + ln / 2 - 0.01) + sd * off + (0, 0, 0.050)
            m.part(K.box(f"toe_{name}{k}", c, sd, td, (0, 0, 1), (tw * 0.44, ln / 2, 0.050), rng=rng, jit=0.004,
                         taper=(0.94, 0.88)), params=BODY)
        return th, sh, ft

    # right leg strides forward, left leg trails (side and three-quarter views)
    hipR, kneeR, ankR = (np.array(Pz[k], float) for k in ("hipR", "kneeR", "ankR"))
    hipL, kneeL, ankL = (np.array(Pz[k], float) for k in ("hipL", "kneeL", "ankL"))
    thR, shR, ftR = leg("R", hipR, kneeR, ankR, Pz["toeR"], Pz["footR"], -1)
    thL, shL, ftL = leg("L", hipL, kneeL, ankL, Pz["toeL"], Pz["footL"], 1)
    wound_on(thR, 0.80, (-0.2, -1, 0.3), 0.085, 0.07)
    wound_on(thR, 0.35, (-1, -0.2, 0), 0.10, 0.05)
    wound_on(shR, 0.42, (0, -1, 0.5), 0.105, 0.06)
    wound_on(shR, 0.80, (-0.6, -1, 0), 0.06, 0.04)
    wound_on(shR, 0.55, (1, 0, 0), 0.11, 0.05)
    wound_on(thL, 0.86, (0.2, -1, 0.2), 0.07, 0.075)
    wound_on(thL, 0.80, (1, 0, 0), 0.075, 0.06)
    wound_on(shL, 0.38, (0.3, -1, 0.4), 0.09, 0.058)
    wound_on(shL, 0.40, (1, 0.2, 0), 0.10, 0.05)
    wound_on(shL, 0.84, (0.5, -1, 0.3), 0.06, 0.04)
    wound_on(shL, 0.80, (1, 0.5, 0), 0.055, 0.04)
    wound_on(ftR, 0.45, (0, 0, 1), 0.07, 0.05)
    wound_on(ftL, 0.40, (0, 0, 1), 0.06, 0.045)

    # ------------------------------------------------------------------ neck (hidden by the head)
    N0 = torso_point(1.02, 0.0, -0.10)
    N1 = np.array(Pz["neck_end"], float)
    m.part(K.loft("neck", [N0, (N0 + N1) / 2 + (0, 0, 0.02), N1], [(0.25, 0.20), (0.235, 0.19), (0.22, 0.18)], X,
                  chamfer=0.25, rng=rng, jit=0.006), params=BODY)

    # ------------------------------------------------------------------ rods (placed on the parts)
    R = lambda part, sx, side, L, r=0.027, tilt=(0, 0, 0): rod_on(m, part, sx, side, L, r, tilt)
    R(torso, 0.95, (0.55, 1, 0.9), 0.42, 0.030, (0.1, -0.1, 0.75))          # behind the left shoulder
    R(torso, 0.80, (0.25, 1, 0.7), 0.30, 0.028, (0, 0.1, 0.25))             # upper back
    R(torso, 0.36, (0.10, 1, 0.7), 0.27, 0.027, (0, 0.2, -0.5))             # lower back
    R(torso, 0.62, (-1, -0.25, 0), 0.25, 0.027, (0, 0, 0.06))               # right flank, upper
    R(torso, 0.36, (-1, -0.35, 0), 0.27, 0.028, (0, -0.1, -0.1))            # right flank, lower
    R(larm, 0.44, (0.2, -1, 0.3), 0.28, 0.027, (0.1, 0, -0.2))              # elbow, pointing forward
    R(larm, 0.74, (-1, -0.7, 0), 0.31, 0.030, (0, 0, 0.3))                  # wrist
    R(larm, 0.88, (-1, -0.1, 0), 0.13, 0.024)
    R(larm, 0.92, (0.2, 1, 0), 0.15, 0.024, (0, 0, -0.2))
    R(sarm, 0.38, (1, 0.05, 0), 0.22, 0.027, (0, 0, 0.1))                   # short arm elbow
    R(shL, 0.45, (0.75, 0.6, 0), 0.19, 0.026, (0, 0, 0.6))                  # left shin
    R(shR, 0.55, (-1, 0, 0), 0.10, 0.022, (0, 0, 0.1))                      # right shin stub
    m.info["neck_end"] = N1
