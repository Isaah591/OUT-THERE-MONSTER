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
    lean=39.0,                                   # torso forward lean, degrees (side view)
    hip=[0.005, 0.005, 1.425],
    torso_len=1.11,
    torso_w=0.99, torso_d=0.91,                    # width / depth multipliers
    arm_long=[[-0.575, -0.61, 2.29], [-0.58, -0.64, 2.25], [-0.75, -0.745, 1.855], [-0.98, -0.760, 1.475], [-1.055, -1.065, 0.835], [-1.04, -1.495, 0.125]],
    arm_long_w=0.77, arm_long_d=1.02,
    arm_short=[[0.405, -0.64, 2.435], [0.495, -0.77, 2.14], [0.635, -0.49, 1.67], [0.695, -0.375, 1.325], [0.725, -0.455, 0.93]],
    arm_short_w=0.90, arm_short_d=0.95,
    hipR=[-0.145, -0.30, 1.44], kneeR=[-0.25, -0.485, 0.875], ankR=[-0.24, -0.08, 0.29],
    hipL=[0.18, 0.03, 1.39], kneeL=[0.34, 0.11, 0.915], ankL=[0.455, 0.465, 0.265],
    leg_w=0.92, leg_d=0.84,
    footR=0.6, footL=0.49, toeR=[-0.06, -1.0], toeL=[0.1, -1.0],
    neck_end=[0.04, -0.94, 2.475],
)

BODY = dict(cell=0.017, plate=(0.110, 0.088), chip=0.36, pit=0.011)
TOEP = dict(BODY, layers=((0.003, 0.006, 1.00, 0.00), (0.008, 0.012, 0.45, 0.05)), pit=0.006, plate=(0.07, 0.05))


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
    hw = [(0.31, 0.25), (0.36, 0.315), (0.375, 0.375), (0.385, 0.405), (0.385, 0.395), (0.31, 0.31)]   # (+x, -x)
    hd = [(0.18, 0.20), (0.225, 0.245), (0.275, 0.270), (0.355, 0.285), (0.390, 0.275), (0.300, 0.215)]  # (back, front): hunched upper back, deep chest
    P = [torso_point(s) for s in ts]
    halves = [(a[0] * Pz["torso_w"], a[1] * Pz["torso_w"], b[0] * Pz["torso_d"], b[1] * Pz["torso_d"]) for a, b in zip(hw, hd)]
    torso = m.part(K.loft("torso", P, halves, X, chamfer=0.20, rng=rng, jit=0.007), params=BODY)
    wound_on(torso, 0.42, (-0.35, -1, -0.5), 0.125, 0.165, axis=X)           # belly, creature's right
    wound_on(torso, 0.52, (-1, -0.2, 0), 0.17, 0.075)                         # right flank
    wound_on(torso, 0.66, (1, 0.25, 0.1), 0.30, 0.095)                        # left flank, long tear
    wound_on(torso, 0.74, (0.75, -1, -0.6), 0.065, 0.055)                     # chest under left shoulder
    wound_on(torso, 0.30, (0.3, 1, 0.6), 0.12, 0.08)                          # lower back
    wound_on(torso, 0.78, (-0.4, 1, 0.7), 0.10, 0.07)                         # upper back
    wound_on(torso, 0.18, (0.5, -1, -0.6), 0.05, 0.06, axis=X)

    # pelvis block between the thighs
    m.part(K.box("pelvis", (hip_mid := (np.array(Pz["hipR"], float) + np.array(Pz["hipL"], float)) / 2) + np.array([0.0, 0.02, -0.055]), X, (0, 1, 0), (0, 0, 1),
                 (0.075, 0.085, 0.035), rng=rng, jit=0.006, taper=(1.25, 1.2)), params=BODY)

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
    wound_on(larm, 0.60, (1, -0.15, 0), 0.31, 0.095)                          # inner face, seen in the side view
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
        m.part(K.box(f"ankle_{name}", heel + td * 0.07 + (0, 0, 0.225), td, sd, (0, 0, 1), (0.150, 0.128, 0.075),
                     rng=rng, jit=0.006, taper=(0.9, 0.92)), params=BODY)
        n_toe = 4
        tw = 2 * fw * 1.04 / n_toe
        for k in range(n_toe):
            off = (-fw * 1.04 + tw * (k + 0.5))
            ln = 0.165 + 0.030 * rng.random() - 0.016 * abs(k - 1.5)
            toe_h = 0.046 + 0.010 * rng.random()
            c = heel + td * (foot_len - 0.15 + ln / 2 - 0.02) + sd * off + (0, 0, toe_h)
            m.part(K.box(f"toe_{name}{k}", c, td, sd, (0, 0, 1), (ln / 2, tw * 0.33, toe_h), rng=rng, jit=0.004,
                         taper=(0.80, 0.90)), params=TOEP)
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

    # ------------------------------------------------------------------ neck (hidden by the head)
    # short and high: the head hangs forward off the top of the shoulders, the throat stays open
    import head as HD
    N0 = torso_point(0.95, 0.0, -0.06)
    N1 = HD.Hw(0.0, 0.680, 0.020)
    m.part(K.loft("neck", [N0, (N0 + N1) / 2 + (0, 0, 0.045), N1], [(0.220, 0.245), (0.205, 0.235), (0.195, 0.215)], X,
                  chamfer=0.25, rng=rng, jit=0.006), params=BODY)

    # ------------------------------------------------------------------ rods (placed on the parts)
    R = lambda part, sx, side, L, r=0.027, tilt=(0, 0, 0): rod_on(m, part, sx, side, L, r, tilt)
    R(torso, 1.00, (0.60, 0.25, 1.0), 0.40, 0.030, (0.1, 0.25, 0.3))        # on the left shoulder
    R(torso, 0.72, (0.25, 1, 0.7), 0.27, 0.028, (0, 0.15, 0.35))            # upper back
    R(torso, 0.24, (0.10, 1, 0.7), 0.25, 0.027, (0, 0.3, -0.75))            # lower back, level
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
