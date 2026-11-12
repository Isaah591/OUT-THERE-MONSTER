"""ASTRA R08 head - Experimental Model 02 (the defining feature, built from the sheet alone).

Head coordinates (metres): x sideways (+x = the creature's left), b = distance back from the
front of the snout, h = height above the upper jaw line.  The panel readings they come from are
noted next to each block; `HEAD` places the head in the world.

Shape, from the sheet: a broad, battered block of a skull - a short vertical mask carrying two
recessed square sockets under heavy brows that drop toward the nose, a forehead that climbs
steeply into a ridged dome - over an enormous mouth.  The upper lip dips to a blunt point right
of centre and its corners sit higher; the lower jaw is a narrow U that hangs almost straight
down from under the cheeks, sweeps inward and hooks forward at the chin.  A wide band of wet red
gum runs round it and up into the torn left cheek.  Long, thick, crooked ivory teeth - front and
rear alike - fill the opening from both jaws.
"""
import numpy as np
import kernel as K

# ---- placement (fit_pose.py, then eased toward the front view's centre line) -----------------
HEAD = dict(origin=np.array([-0.010, -1.760, 2.410]), pitch=0.0549, yaw=np.radians(0.0), scale=0.96)
TOOTH_SLIM = 0.93          # the sheet's teeth are slimmer for their length than the first tables gave

HEADP = dict(cell=0.0105, plate=(0.100, 0.085),
             layers=((0.003, 0.008, 1.00, 0.00), (0.011, 0.017, 0.66, 0.05), (0.019, 0.027, 0.30, 0.10), (0.029, 0.040, 0.11, 0.14)),
             pit=0.012, cavity=0.040, chip=0.36)
JAWP = dict(HEADP, plate=(0.085, 0.07))


def frame(cfg=None):
    cfg = cfg or HEAD
    p, y = cfg["pitch"], cfg["yaw"]
    Rx = K.rot_axis((1, 0, 0), -p)                     # nose down for positive pitch
    Rz = K.rot_axis((0, 0, 1), y)
    M = Rz @ Rx
    return M[:, 0] * cfg["scale"], M[:, 1] * cfg["scale"], M[:, 2] * cfg["scale"]   # x, back, up


def Hw(x, b, h, cfg=None):
    cfg = cfg or HEAD
    ex, eb, eh = frame(cfg)
    return cfg["origin"] + x * ex + b * eb + h * eh


def Hd(x, b, h, cfg=None):
    ex, eb, eh = frame(cfg)
    return K.unit(x * ex + b * eb + h * eh)


def hexa(name, P8, kind="plate", rng=None, jit=0.0, kinds=None):
    """Battered hexahedron from 8 corners: lower ring (-x-b, +x-b, +x+b, -x+b) then upper ring."""
    co = K.Coarse(name)
    P8 = [np.asarray(p, float) + (rng.normal(0, jit, 3) if (rng is not None and jit) else 0) for p in P8]
    i = co.vs(P8)
    ex = K.unit(P8[1] - P8[0])
    ez = K.unit(P8[4] - P8[0])
    kk = dict(bottom=kind, top=kind, front=kind, back=kind, right=kind, left=kind)
    kk.update(kinds or {})
    co.f([i[3], i[2], i[1], i[0]], kind=kk["bottom"], grain=ex, tag="bottom")
    co.f([i[4], i[5], i[6], i[7]], kind=kk["top"], grain=ex, tag="top")
    co.f([i[0], i[1], i[5], i[4]], kind=kk["front"], grain=ex, tag="front")
    co.f([i[2], i[3], i[7], i[6]], kind=kk["back"], grain=ex, tag="back")
    co.f([i[1], i[2], i[6], i[5]], kind=kk["left"], grain=ez, tag="left")       # +x = creature's left
    co.f([i[3], i[0], i[4], i[7]], kind=kk["right"], grain=ez, tag="right")
    return co


# ---- the mask (front view crop: 620 px across the face = 0.52 m) ------------------------------
# columns: mask edge | right socket outer | inner | lip point | left socket inner | outer | mask edge
COLX = np.array([-0.262, -0.235, -0.124, -0.056, 0.070, 0.205, 0.262])
LIP = np.array([0.006, -0.006, -0.024, -0.096, -0.012, 0.004, 0.020])     # the lip stays high under the sockets and dips between them
SOCB = np.array([0.034, 0.021, 0.013, 0.004, 0.026, 0.034, 0.044])        # socket floors
SOCT = np.array([0.158, 0.148, 0.108, 0.096, 0.124, 0.160, 0.168])        # socket tops: inner corners low
BROW = np.array([0.188, 0.190, 0.172, 0.162, 0.178, 0.194, 0.188])        # top of the mask
MASK_B = np.array([0.000, -0.004, -0.014, -0.024, -0.014, -0.004, 0.000]) # centre pushed forward (nose)
MASK_BACK = 0.128
SOCKET_DEPTH = 0.092
# pupils: tiny, deep, toward the inner-lower corner of each socket (not mirrored)
PUPILS = [(-0.168, 0.068), (0.124, 0.084)]
PUPIL_R = 0.0068


def lip(x):
    return float(np.interp(x, COLX, LIP))


def mask_b(x, h):
    return float(np.interp(x, COLX, MASK_B)) + 0.018 * (1.0 - np.clip(h / 0.18, -0.6, 1.0))


def build_mask(rng):
    co = K.Coarse("mask")
    rows = [LIP, SOCB, SOCT, BROW]
    F = [[co.v(Hw(COLX[c], mask_b(COLX[c], rows[r][c]), rows[r][c])) for c in range(7)] for r in range(4)]
    B = [[co.v(Hw(COLX[c], MASK_BACK, rows[r][c])) for c in range(7)] for r in range(4)]
    sockets = {(1, 1), (1, 4)}
    gx = Hd(1, 0, 0)
    for r in range(3):
        for c in range(6):
            if (r, c) in sockets:
                continue
            co.f([F[r][c], F[r][c + 1], F[r + 1][c + 1], F[r + 1][c]], grain=gx, tag="mask_front")
    for c in range(6):
        co.f([F[3][c], F[3][c + 1], B[3][c + 1], B[3][c]], grain=gx, tag="mask_top")
        co.f([F[0][c + 1], F[0][c], B[0][c], B[0][c + 1]], kind="gum", tag="lip")
    for r in range(3):
        co.f([F[r][0], F[r + 1][0], B[r + 1][0], B[r][0]], grain=Hd(0, 0, 1), tag="mask_side")
        co.f([F[r + 1][6], F[r][6], B[r][6], B[r + 1][6]], grain=Hd(0, 0, 1), tag="mask_side")
    for (r, c) in sockets:
        cx = (COLX[c] + COLX[c + 1]) / 2
        ch = (SOCB[c] + SOCB[c + 1] + SOCT[c] + SOCT[c + 1]) / 4
        bk = {}
        for rr in (r, r + 1):
            for cc in (c, c + 1):
                x = cx + (COLX[cc] - cx) * 0.92
                h = ch + (rows[rr][cc] - ch) * 0.92
                bk[(rr, cc)] = co.v(Hw(x, mask_b(COLX[cc], rows[rr][cc]) + SOCKET_DEPTH, h))
        co.f([F[r][c], F[r][c + 1], bk[(r, c + 1)], bk[(r, c)]], kind="socket")
        co.f([F[r + 1][c + 1], F[r + 1][c], bk[(r + 1, c)], bk[(r + 1, c + 1)]], kind="socket")
        co.f([F[r + 1][c], F[r][c], bk[(r, c)], bk[(r + 1, c)]], kind="socket")
        co.f([F[r][c + 1], F[r + 1][c + 1], bk[(r + 1, c + 1)], bk[(r, c + 1)]], kind="socket")
        co.f([bk[(r, c)], bk[(r, c + 1)], bk[(r + 1, c + 1)], bk[(r + 1, c)]], kind="socket")
    return co


# ---- cranium (exact side view and side close-up: steep forehead into a dome) ------------------
#        b      wb     wc     hc     wt     ht     wi     hi     hr     hbc
CRAN = [(0.118, 0.272, 0.290, 0.095, 0.264, 0.218, 0.140, 0.268, 0.282, 0.072),
        (0.180, 0.280, 0.298, 0.102, 0.268, 0.250, 0.150, 0.328, 0.356, 0.078),
        (0.290, 0.288, 0.308, 0.110, 0.268, 0.262, 0.155, 0.356, 0.392, 0.082),
        (0.440, 0.288, 0.308, 0.115, 0.258, 0.262, 0.145, 0.362, 0.400, 0.062),
        (0.600, 0.268, 0.290, 0.112, 0.238, 0.240, 0.130, 0.332, 0.366, -0.010),
        (0.710, 0.225, 0.246, 0.102, 0.196, 0.200, 0.105, 0.272, 0.300, 0.004),
        (0.765, 0.160, 0.176, 0.096, 0.140, 0.160, 0.070, 0.200, 0.220, 0.030)]
MOUTH_BACK = 0.50          # the palate ends here; behind it the head is solid


def jaw_half_width(b):
    return float(np.interp(b, [c[0] for c in CRAN], [c[1] for c in CRAN]))


def build_cranium(rng):
    co = K.Coarse("cranium")
    rings = []
    for (b, wb, wc, hc, wt, ht, wi, hi, hr, hbc) in CRAN:
        j = lambda s=0.007: rng.normal(0, s)
        dl = 0.016 if 0.2 < b < 0.5 else 0.0            # dented left temple
        pts = [(-wb + j(), b, 0.0 + j(0.004)), (-wc + j(), b, hc + j()), (-wt + j(), b, ht + j()),
               (-wi + j(), b, hi + j()), (0.012 + j(), b, hr + j(0.005)), (wi + j(), b, hi + j() - dl * 0.4),
               (wt + j() - dl, b, ht + j() - dl * 0.6), (wc + j() - dl * 0.5, b, hc + j()), (wb + j(), b, 0.0 + j(0.004)),
               (0.0, b, hbc)]
        if b > MOUTH_BACK:                               # underside behind the mouth drops a little
            pts[0] = (pts[0][0], b, -0.03)
            pts[8] = (pts[8][0], b, -0.03)
        rings.append(co.vs([Hw(*p) for p in pts]))
    gb = Hd(0, 1, 0)
    for i in range(len(rings) - 1):
        b0 = CRAN[i][0]
        for jx in range(10):
            a, c = rings[i], rings[i + 1]
            kind = "plate"
            if jx in (8, 9):
                kind = "void" if b0 < MOUTH_BACK else "core"
            co.f([a[jx], a[(jx + 1) % 10], c[(jx + 1) % 10], c[jx]], kind=kind, grain=gb, tag=f"cr{jx}")
    co.f(rings[0][::-1], kind="socket", tag="front")
    co.f(rings[-1], kind="plate", grain=Hd(1, 0, 0), tag="back")
    return co


# ---- lower jaw rim (front view outline + exact side profile): inner edge of the gum band ------
#          x       b       h
RIM = np.array([(-0.236, 0.478, -0.040), (-0.228, 0.474, -0.124), (-0.216, 0.468, -0.208), (-0.196, 0.455, -0.297),
                (-0.168, 0.438, -0.396), (-0.140, 0.417, -0.485), (-0.108, 0.392, -0.568), (-0.068, 0.365, -0.630),
                (-0.020, 0.346, -0.660), (0.042, 0.340, -0.666), (0.100, 0.350, -0.650), (0.146, 0.373, -0.608),
                (0.180, 0.398, -0.542), (0.204, 0.421, -0.458), (0.220, 0.440, -0.362), (0.230, 0.457, -0.260),
                (0.236, 0.470, -0.156), (0.238, 0.478, -0.040)])


def rim_frames():
    """World points of the rim with (tangent, forward, outward) frames."""
    P = np.array([Hw(*p) for p in RIM])
    T, EX, EY = K.path_frames(P, Hd(0, -1, 0))
    return P, T, EX, EY


def band_width(u):
    """Width of the gum band on the front of the jaw: broad up the arms, narrow under the chin,
    broadest on the torn left side (head close-up, mouth interior panels)."""
    arm = abs(2 * u - 1)
    return 0.030 + 0.030 * arm ** 1.2 + (0.008 if u > 0.5 else 0.0) * arm


def build_lower_jaw(rng):
    P, T, EX, EY = rim_frames()
    n = len(P)
    sections = []
    for i in range(n):
        u = i / (n - 1)
        arm = abs(2 * u - 1)                  # 1 at the hinges, 0 at the chin
        D = 0.095 + 0.070 * arm ** 1.3        # the bone is deeper toward the hinge (side view)
        g = band_width(u)
        w = 0.030 + 0.016 * arm               # plated bone outside the gum
        sections.append([(0.000, 0.000), (0.004, g), (-0.014, g + w), (-D, g + w * 0.6), (-D * 0.92, -0.004), (-0.030, -0.008)])
    kinds = ["gum", "plate", "plate", "plate", "gum", "gum"]
    co = K.loft_poly("jaw", P, sections, Hd(0, -1, 0), kinds, rng=rng, jit=0.004)
    return co


# ---- teeth -----------------------------------------------------------------------------------
# Upper front arc: (x, length, radius, lean forward deg, splay deg toward -x).  From the front,
# three-quarter and head close-up panels: long at the right corner, the longest fang at the lip
# point, one thick fang left of centre, uneven in between.
UPPER_FRONT = [(-0.240, 0.235, 0.030, 3, 5), (-0.196, 0.292, 0.033, 2, 3), (-0.150, 0.196, 0.025, 7, 2),
               (-0.108, 0.160, 0.026, 2, 1), (-0.048, 0.385, 0.040, 1, -1), (-0.004, 0.232, 0.026, 7, 0),
               (0.040, 0.345, 0.034, 3, -1), (0.092, 0.262, 0.028, 6, -2), (0.140, 0.300, 0.036, 2, -2),
               (0.190, 0.158, 0.024, 6, -3), (0.236, 0.196, 0.027, 3, -5)]
# Upper sides: (side, b, length, radius, splay out deg).  The exact side view shows the rear teeth
# as long as the front ones, and the brief asks for it.
UPPER_SIDE = [(-1, 0.105, 0.335, 0.033, 5), (-1, 0.195, 0.265, 0.028, 8), (-1, 0.285, 0.345, 0.034, 4), (-1, 0.375, 0.275, 0.029, 7),
              (1, 0.100, 0.275, 0.030, 7), (1, 0.190, 0.340, 0.037, 4), (1, 0.280, 0.275, 0.030, 8), (1, 0.370, 0.285, 0.031, 5)]
# Upper inner row, behind and between the main teeth: (x, b offset, length, radius)
UPPER_INNER = [(-0.218, 0.060, 0.190, 0.021), (-0.128, 0.052, 0.275, 0.024), (-0.026, 0.056, 0.300, 0.025),
               (0.066, 0.052, 0.240, 0.023), (0.166, 0.058, 0.210, 0.022), (0.215, 0.090, 0.165, 0.020),
               (0.108, 0.082, 0.300, 0.026), (0.018, 0.100, 0.320, 0.025), (-0.085, 0.092, 0.300, 0.025), (0.180, 0.108, 0.240, 0.022),
               (-0.150, 0.110, 0.270, 0.024), (0.062, 0.125, 0.320, 0.026), (-0.185, 0.085, 0.255, 0.023)]
# Lower teeth: (rim parameter 0..1 from the right hinge round the chin to the left hinge, length,
# radius, elevation above the forward direction deg, lean toward +x deg)
LOWER = [(0.085, 0.175, 0.024, 76, 10), (0.150, 0.290, 0.029, 74, 13), (0.215, 0.335, 0.032, 71, 11), (0.275, 0.295, 0.028, 73, 15),
         (0.335, 0.360, 0.034, 69, 11), (0.390, 0.315, 0.029, 69, 14), (0.440, 0.372, 0.035, 66, 7), (0.487, 0.300, 0.028, 68, 3),
         (0.530, 0.385, 0.036, 64, -2), (0.575, 0.330, 0.030, 66, -7), (0.620, 0.372, 0.034, 64, -6), (0.668, 0.322, 0.030, 65, -11),
         (0.718, 0.340, 0.035, 60, -8), (0.772, 0.302, 0.031, 64, -11), (0.828, 0.325, 0.033, 62, -7), (0.882, 0.270, 0.028, 67, -10),
         (0.932, 0.175, 0.024, 72, -8)]
# Lower inner row: (rim parameter, length, radius, elevation)
LOWER_INNER = [(0.245, 0.285, 0.023, 78), (0.365, 0.320, 0.025, 76), (0.465, 0.320, 0.026, 76), (0.555, 0.290, 0.025, 72),
               (0.645, 0.255, 0.023, 72), (0.745, 0.235, 0.022, 74), (0.855, 0.200, 0.020, 76),
               (0.420, 0.335, 0.025, 74), (0.510, 0.360, 0.026, 76), (0.600, 0.330, 0.025, 72), (0.555, 0.375, 0.026, 80),
               (0.305, 0.300, 0.024, 78), (0.190, 0.255, 0.022, 80),
               (0.350, 0.395, 0.026, 84), (0.470, 0.405, 0.027, 84), (0.640, 0.370, 0.025, 82),
               (0.265, 0.365, 0.025, 84), (0.405, 0.385, 0.026, 86)]


def rim_point(u):
    P, T, EX, EY = rim_frames()
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    d = u * cum[-1]
    i = int(np.clip(np.searchsorted(cum, d) - 1, 0, len(seg) - 1))
    f = (d - cum[i]) / seg[i]
    return P[i] * (1 - f) + P[i + 1] * f, K.unit(T[i] * (1 - f) + T[i + 1] * f), K.unit(EY[i] * (1 - f) + EY[i + 1] * f)


TOOTH_T = np.array([0.0, 0.10, 0.24, 0.40, 0.56, 0.71, 0.84, 0.94, 1.0])
TOOTH_R = np.array([1.0, 0.99, 0.93, 0.82, 0.67, 0.50, 0.32, 0.15, 0.0])


def tooth_line(sp, n=14):
    """Centre line and radius of a tooth (as kernel.tooth builds it)."""
    t = np.linspace(0, 1, n)
    P = sp["root"][None] + np.outer(t * sp["L"], sp["dir"]) + np.outer(sp["bend"] * sp["L"] * t ** 2, sp["bd"])
    return P, sp["r"] * 1.06 * np.interp(t, TOOTH_T, TOOTH_R)


def tooth_clashes(specs, margin=0.0015, skip=2):
    """Teeth passing through one another above the gum: (i, j, depth, point on i, point on j)."""
    lines = [tooth_line(sp) for sp in specs]
    out = []
    for i in range(len(specs)):
        Pi, Ri = lines[i]
        for j in range(i + 1, len(specs)):
            if np.linalg.norm(specs[i]["root"] - specs[j]["root"]) > specs[i]["L"] + specs[j]["L"]:
                continue
            Pj, Rj = lines[j]
            D = (np.linalg.norm(Pi[:, None] - Pj[None], axis=2) - Ri[:, None] - Rj[None])[skip:, skip:]
            if D.min() < -margin:
                ia, ib = np.unravel_index(D.argmin(), D.shape)
                out.append((i, j, float(-D.min()), Pi[ia + skip], Pj[ib + skip]))
    return out


def relax_teeth(specs, iters=240, max_lean=np.radians(7.5), max_shift=0.026):
    """Ease crowded teeth apart until none passes through another: mostly by sliding the roots
    along the gum (up to max_shift), partly by leaning (up to max_lean from the designed line)."""
    for sp in specs:
        sp.setdefault("dir0", sp["dir"].copy())
        sp.setdefault("root0", sp["root"].copy())
    for _ in range(iters):
        cl = tooth_clashes(specs)
        if not cl:
            break
        for (i, j, depth, pi, pj) in cl:
            n = pi - pj
            n = K.unit(n) if np.linalg.norm(n) > 1e-6 else K.unit(np.cross(specs[i]["dir"], specs[j]["dir"]) + 1e-6)
            for (k, sgn) in ((i, 1.0), (j, -1.0)):
                sp = specs[k]
                side = n - (n @ sp["dir"]) * sp["dir"]
                # slide the root
                r_new = sp["root"] + sgn * side * (0.30 * depth + 0.0004)
                off = r_new - sp["root0"]
                if np.linalg.norm(off) > max_shift:
                    r_new = sp["root0"] + off * (max_shift / np.linalg.norm(off))
                sp["root"] = r_new
                # lean the tooth
                d_new = K.unit(sp["dir"] + sgn * side * (0.25 * depth + 0.0004) / max(sp["L"] * 0.6, 0.05))
                ang = np.arccos(np.clip(d_new @ sp["dir0"], -1, 1))
                if ang > max_lean:
                    ax = np.cross(sp["dir0"], d_new)
                    d_new = K.rot_axis(ax, max_lean) @ sp["dir0"] if np.linalg.norm(ax) > 1e-9 else sp["dir0"]
                sp["dir"] = K.unit(d_new)
                sp["bd"] = K.unit(sp["bd"] - (sp["bd"] @ sp["dir"]) * sp["dir"])
    left = tooth_clashes(specs)
    # anything still touching is two neighbours fused at the base: shorten the smaller one a little
    for (i, j, depth, pi, pj) in left:
        k = i if specs[i]["r"] < specs[j]["r"] else j
        specs[k]["r"] *= max(0.80, 1.0 - depth / max(specs[k]["r"], 1e-3))
    return tooth_clashes(specs)


def build_teeth(m):
    rng = np.random.default_rng(m.seed + 404)
    tb = m.bucket("head_teeth", "tooth")
    gum = m.bucket("head_gums", "gum", smooth=True)
    dn, fw, up, ex = Hd(0, 0, -1), Hd(0, -1, 0), Hd(0, 0, 1), Hd(1, 0, 0)
    specs = []

    def add(root, d, L, r, bend_dir, bend, jaw, sink=0.032):
        # no two teeth stand alike: every one is knocked a few degrees off its line
        k = rng.normal(0, 0.052, 3) * (1.9 if rng.random() < 0.16 else 1.0)
        d = K.unit(d + k - (k @ d) * d)
        bd = np.asarray(bend_dir, float)
        L, r = L * HEAD["scale"], r * HEAD["scale"] * TOOTH_SLIM
        specs.append(dict(root=np.asarray(root, float), dir=d, L=L, r=r, bd=K.unit(bd - (bd @ d) * d), bend=bend, jaw=jaw, sink=sink))

    # upper front arc: neighbours stand at alternate depths in the thick lip, so crowded teeth overlap
    # in the picture without growing through one another
    for i, (x, L, r, lean, splay) in enumerate(UPPER_FRONT):
        h = lip(x)
        root = Hw(x, mask_b(x, h) + (0.030 if i % 2 == 0 else 0.056) + 0.003 * rng.normal(), h - 0.004)
        a = np.radians(lean + rng.normal(0, 2.0))
        d = K.unit(dn + fw * np.tan(a) + ex * np.tan(np.radians(-splay + rng.normal(0, 1.5))))
        add(root, d, L, r, -fw, rng.uniform(0.02, 0.06), "upper", sink=0.010)
    for i, (sd, b, L, r, splay) in enumerate(UPPER_SIDE):
        root = Hw(sd * (jaw_half_width(b) - (0.020 if i % 2 == 0 else 0.042)), b, 0.010)
        d = K.unit(dn + ex * sd * np.tan(np.radians(splay + rng.normal(0, 2.0))) + fw * np.tan(np.radians(rng.normal(3, 3))))
        add(root, d, L, r, -ex * sd, rng.uniform(0.03, 0.07), "upper")
    for (x, db, L, r) in UPPER_INNER:
        h = lip(x)
        root = Hw(x, mask_b(x, h) + 0.046 + db, h - 0.004)
        d = K.unit(dn + fw * np.tan(np.radians(rng.normal(-3, 3))) + ex * np.tan(np.radians(rng.normal(0, 4))))
        add(root, d, L, r, -fw, rng.uniform(0.02, 0.06), "upper", sink=0.010)
    for i, (u, L, r, elev) in enumerate(LOWER_INNER):
        p, t, out = rim_point(u)
        root = p - out * 0.014 - fw * (0.050 if i % 2 else 0.085)
        e = np.radians(elev + rng.normal(0, 3.0))
        d = K.unit(np.cos(e) * fw + np.sin(e) * up + ex * np.tan(np.radians(rng.normal(0, 5))) * (1 if u < 0.5 else -1) * 0.6)
        add(root, d, L, r, up, rng.uniform(0.03, 0.07), "lower")
    for i, (u, L, r, elev, lean) in enumerate(LOWER):
        p, t, out = rim_point(u)
        root = p + out * band_width(u) * (0.22 if i % 2 == 0 else 0.60) + fw * 0.004
        e = np.radians(elev + rng.normal(0, 2.5))
        d = K.unit(np.cos(e) * fw + np.sin(e) * up + ex * np.tan(np.radians(lean + rng.normal(0, 2.0))))
        add(root, d, L, r, up, rng.uniform(0.03, 0.08), "lower")

    before = len(tooth_clashes(specs))
    left = relax_teeth(specs)
    m.info["tooth_clashes"] = (before, len(left), max([c[2] for c in left], default=0.0))

    for sp in specs:
        root, d, L, r = sp["root"], sp["dir"], sp["L"], sp["r"]
        V, Q, T, at = K.tooth(root, d, L, r, rng, bend_dir=sp["bd"], bend=sp["bend"], sides=int(rng.choice([5, 6, 6, 7])),
                              sink=sp["sink"], flat=rng.uniform(0.82, 1.0), twist=rng.uniform(-0.6, 0.6))
        tb.add(V, Q, T, vattr=dict(t=at["t"], ca=at["ca"], sa=at["sa"], tone=rng.random()))
        # the gum rises a little way up each root
        P4 = np.array([root - d * 0.014, root - d * 0.002, root + d * 0.010, root + d * (0.022 + 0.25 * r)])
        V, Q, T = K.tube(P4, [r + 0.001, r + 0.0045, r + 0.003, r + 0.0003], sides=8, rng=rng, wob=0.04, xhint=np.cross(d, ex))
        gum.add(V, Q, T)
        sp["tip"] = root + d * L + sp["bd"] * sp["bend"] * L
    m.info["teeth"] = specs
    m.info["n_teeth"] = (len(UPPER_FRONT) + len(UPPER_SIDE) + len(UPPER_INNER), len(LOWER) + len(LOWER_INNER))


# ---- soft parts ------------------------------------------------------------------------------

def cord(bucket, pts, radii, rng, sides=7, wob=0.07, hint=None, wander=0.0, n=None):
    P = np.array([Hw(*p) for p in pts])
    R = np.broadcast_to(np.asarray(radii, float), (len(P),)).copy()
    if n:
        t0 = np.linspace(0, 1, len(P))
        t1 = np.linspace(0, 1, n)
        P = K.spline(P, n)
        R = np.interp(t1, t0, R)
        if wander:
            ph = rng.uniform(0, 6.28, 3)
            fq = rng.uniform(2.0, 4.5, 3)
            env = np.sin(np.pi * t1) ** 0.6
            for a in range(3):
                P[:, a] += wander * env * np.sin(ph[a] + t1 * fq[a] * np.pi)
            R = R * (0.78 + 0.34 * np.abs(np.sin(ph[0] + t1 * fq[1] * np.pi)) ** 0.8)
    V, Q, T = K.tube(P, R, sides=sides, rng=rng, wob=wob, xhint=Hd(0, -1, 0) if hint is None else hint)
    bucket.add(V, Q, T)


def build_soft(m):
    rng = np.random.default_rng(m.seed + 505)
    gum = m.bucket("head_gums", "gum", smooth=True)
    lin = m.bucket("head_mouth", "mouth", smooth=True)
    # upper gum line: round the lip and back along both sides (the collars sit on it)
    pts = []
    for b in (0.44, 0.36, 0.27, 0.18, 0.10):
        pts.append((-(jaw_half_width(b) - 0.020), b, 0.004))
    for x in np.linspace(-0.250, 0.250, 15):
        h = lip(x)
        pts.append((x, mask_b(x, h) + 0.034, h + 0.006))
    for b in (0.10, 0.18, 0.27, 0.36, 0.44):
        pts.append(((jaw_half_width(b) - 0.020), b, 0.004))
    Rg = 0.030 + 0.004 * np.sin(np.arange(len(pts)) * 2.1)
    cord(gum, pts, Rg, rng, sides=8, wob=0.05, hint=Hd(0, 0, 1), n=40)
    # thick pads of gum behind the lip for the inner rows of upper teeth to stand in
    for db, rad, dh in ((0.085, 0.040, 0.022), (0.140, 0.046, 0.034)):
        pts = [(x, mask_b(x, lip(x)) + 0.034 + db, lip(x) + dh) for x in np.linspace(-0.235, 0.235, 13)]
        cord(gum, pts, rad + 0.004 * np.sin(np.arange(13) * 1.9), rng, sides=8, wob=0.06, hint=Hd(0, 0, 1), n=30)
    # the gum band on the front of the lower jaw: ropes of wet tissue laid side by side
    P, Tn, EX, EY = rim_frames()
    n = len(P)
    # one broad, flattened band of gum the teeth stand in ...
    pts, rad = [], []
    for i in range(n):
        g = band_width(i / (n - 1))
        pts.append(P[i] + EY[i] * g * 0.46 + EX[i] * 0.004)
        rad.append(g * 0.60)
    Pb = K.spline(np.array(pts), 3 * n)
    Rb = np.interp(np.linspace(0, 1, 3 * n), np.linspace(0, 1, n), rad)
    V, Q, T = K.tube(Pb, Rb, sides=10, rng=rng, wob=0.04, xhint=Hd(0, -1, 0), flat=0.45)
    gum.add(V, Q, T)
    # ... with thinner ropes of tissue running along it
    for i in range(1, 3 * n - 1):
        if rng.random() < 0.40:
            g = band_width(i / (3 * n - 1))
            j = min(i // 3, n - 1)
            c = Pb[i] + EY[j] * g * rng.uniform(-0.38, 0.42) + EX[j] * 0.004
            V, Q, T = K.spindle(c, Tn[j] + EY[j] * rng.normal(0, 0.3), g * rng.uniform(0.7, 1.4), g * rng.uniform(0.13, 0.22),
                                g * rng.uniform(0.06, 0.10), EX[j], segs=7, rings=5, rng=rng)
            gum.add(V, Q, T)
    for k, frac in enumerate((0.90,)):
        pts, rad = [], []
        for i in range(n):
            u = i / (n - 1)
            g = band_width(u)
            wv = 0.16 * g * np.sin(i * 1.3 + k * 2.0)
            pts.append(P[i] + EY[i] * (g * frac + wv) + EX[i] * (0.012 + 0.004 * np.sin(i * 0.9 + k)))
            rad.append(g * 0.15 * (1 + 0.25 * np.sin(i * 2.3 + k * 1.7)))
        Pk = K.spline(np.array(pts), 3 * n)
        Rk = np.interp(np.linspace(0, 1, 3 * n), np.linspace(0, 1, n), rad)
        V, Q, T = K.tube(Pk, Rk, sides=6, rng=rng, wob=0.08, xhint=Hd(0, -1, 0))
        gum.add(V, Q, T)
    # torn left cheek: thick sinews from the temple down into the gum band (side close-up); the right
    # side keeps most of its plating and shows only the mouth-corner strap
    for sd, cords in ((1, [((0.300, 0.330, 0.235), (0.312, 0.385, 0.150), (0.305, 0.430, 0.060), (0.290, 0.455, -0.040), (0.275, 0.462, -0.150), 0.026),
                           ((0.292, 0.440, 0.255), (0.318, 0.455, 0.165), (0.322, 0.490, 0.070), (0.305, 0.498, -0.030), (0.288, 0.480, -0.140), 0.030),
                           ((0.296, 0.385, 0.190), (0.300, 0.350, 0.100), (0.292, 0.400, 0.010), (0.280, 0.440, -0.075), (0.268, 0.452, -0.190), 0.022),
                           ((0.286, 0.520, 0.210), (0.318, 0.520, 0.110), (0.318, 0.540, 0.010), (0.304, 0.520, -0.085), (0.290, 0.492, -0.200), 0.024),
                           ((0.280, 0.300, 0.150), (0.288, 0.345, 0.060), (0.280, 0.400, -0.010), (0.268, 0.436, -0.090), (0.258, 0.450, -0.180), 0.018)]),
                      (-1, [((-0.292, 0.440, 0.090), (-0.300, 0.455, 0.020), (-0.290, 0.468, -0.055), (-0.276, 0.470, -0.150), (-0.262, 0.465, -0.240), 0.022),
                            ((-0.288, 0.495, 0.070), (-0.300, 0.500, 0.000), (-0.292, 0.495, -0.080), (-0.280, 0.485, -0.170), (-0.268, 0.474, -0.250), 0.019)])):
        for (*pp, r) in cords:
            cord(gum, pp, [r * 0.75, r, r * 1.05, r * 0.9, r * 0.6], rng, sides=8, wob=0.08, wander=0.014, n=16)
            # a thinner strand twisting round each sinew
            q = [(x + sd * 0.012, b_ + 0.018 * (-1) ** i, h_) for i, (x, b_, h_) in enumerate(pp)]
            cord(gum, q, r * 0.42, rng, sides=6, wob=0.08, wander=0.012, n=16)
    # mouth-corner webs inside the cheeks
    for sd in (-1, 1):
        for k in range(3):
            b0 = 0.40 + 0.035 * k
            cord(gum, [(sd * (jaw_half_width(b0) - 0.03), b0, 0.02), (sd * 0.255, b0 + 0.02, -0.03), (sd * 0.245, 0.468, -0.10)],
                 [0.016, 0.020, 0.014], rng, sides=6)
    # throat sack behind the lower jaw: closes the U from behind (black)
    back = P + EX * (-0.110) - EY * 0.004
    hs = RIM[:, 2]
    spine = np.array([Hw(0.012, 0.590 - 0.06 * (hs[i] / RIM[:, 2].min()), min(hs[i], 0.03)) for i in range(n)])
    nv = 7
    Vm = []
    for i in range(n):
        for k in range(nv):
            v = k / (nv - 1)
            Vm.append((1 - v) * back[i] + v * spine[i] + Hd(0, 1, 0) * 0.05 * np.sin(np.pi * v))
    Vm = np.array(Vm)
    Qm = np.array([[i * nv + k, i * nv + k + 1, (i + 1) * nv + k + 1, (i + 1) * nv + k] for i in range(n - 1) for k in range(nv - 1)])
    lin.add(Vm, Qm)
    lin.add(Vm, Qm[:, ::-1])
    # dark masses in the throat (stop the view passing straight through the open sides)
    cols = [((-0.050, 0.345, -0.600), (-0.045, 0.385, -0.33), (-0.030, 0.440, -0.06), (-0.02, 0.47, 0.05), 0.060),
            ((0.060, 0.350, -0.600), (0.055, 0.395, -0.32), (0.040, 0.445, -0.06), (0.03, 0.48, 0.05), 0.064),
            ((0.005, 0.330, -0.610), (0.005, 0.370, -0.36), (0.005, 0.420, -0.10), (0.0, 0.46, 0.05), 0.070),
            ((-0.130, 0.410, -0.480), (-0.125, 0.440, -0.28), (-0.11, 0.465, -0.06), (-0.09, 0.49, 0.05), 0.052),
            ((0.150, 0.405, -0.490), (0.145, 0.440, -0.28), (0.13, 0.465, -0.06), (0.10, 0.49, 0.05), 0.052),
            ((-0.060, 0.300, -0.560), (-0.070, 0.265, -0.34), (-0.060, 0.235, -0.12), (-0.04, 0.22, 0.05), 0.056),
            ((0.065, 0.305, -0.570), (0.075, 0.275, -0.33), (0.070, 0.245, -0.12), (0.05, 0.23, 0.05), 0.058),
            ((0.000, 0.250, -0.540), (0.005, 0.215, -0.33), (0.000, 0.190, -0.13), (0.0, 0.18, 0.05), 0.050)]
    for (a, b_, c, d, r) in cols:
        cord(lin, [a, b_, c, d], [r * 0.30, r, r * 0.95, r * 0.7], rng, sides=8, wob=0.10, hint=Hd(1, 0, 0), wander=0.012, n=14)


def build_eyes(m):
    pb = m.bucket("head_pupils", "pupil", smooth=True)
    pos = []
    for (x, h) in PUPILS:
        c = Hw(x, mask_b(x, h) + 0.034, h)
        V, Q, T = K.spindle(c, Hd(0, 1, 0), PUPIL_R * 2, PUPIL_R, PUPIL_R, Hd(0, 0, 1), segs=10, rings=6)
        pb.add(V, Q, T)
        pos.append(c)
    m.info["pupils"] = np.array(pos)


# ---- assembly --------------------------------------------------------------------------------

def build_head(m):
    rng = np.random.default_rng(m.seed + 303)
    G = "head"
    cran = m.part(build_cranium(rng), params=HEADP, group=G)
    mask = m.part(build_mask(rng), params=HEADP, group=G)
    jaw = m.part(build_lower_jaw(rng), params=JAWP, group=G)

    def blk(name, P8, **kw):
        return m.part(hexa(name, [Hw(*p) for p in P8], rng=rng, jit=0.004, **kw), params=HEADP, group=G)

    # heavy brows over each socket, dropping toward the nose and hooding the inner corners
    blk("brow_R", [(-0.286, -0.010, 0.162), (-0.098, -0.022, 0.104), (-0.092, 0.110, 0.190), (-0.290, 0.110, 0.226),
                   (-0.284, -0.006, 0.208), (-0.102, -0.018, 0.156), (-0.096, 0.125, 0.280), (-0.286, 0.125, 0.286)],
        kinds=dict(bottom="core"))
    blk("brow_L", [(0.042, -0.022, 0.120), (0.286, -0.010, 0.172), (0.292, 0.110, 0.232), (0.036, 0.110, 0.198),
                   (0.046, -0.018, 0.168), (0.284, -0.006, 0.216), (0.290, 0.125, 0.288), (0.042, 0.125, 0.284)],
        kinds=dict(bottom="core"))
    blk("brow_C", [(-0.104, -0.020, 0.150), (0.050, -0.020, 0.160), (0.046, 0.112, 0.200), (-0.100, 0.112, 0.196),
                   (-0.106, -0.014, 0.176), (0.052, -0.014, 0.186), (0.048, 0.128, 0.292), (-0.102, 0.128, 0.290)],
        kinds=dict(bottom="core", left="core", right="core"))
    # nasal plate between the eyes, running down into the lip point
    blk("nose", [(-0.074, -0.006, -0.090), (-0.040, -0.004, -0.088), (-0.038, 0.030, -0.070), (-0.076, 0.030, -0.072),
                 (-0.096, -0.028, 0.118), (0.038, -0.028, 0.130), (0.042, 0.050, 0.148), (-0.100, 0.050, 0.140)],
        kinds=dict(left="core", right="core"))
    # crown slab along the ridge
    blk("crest_a", [(-0.120, 0.210, 0.335), (0.030, 0.200, 0.350), (0.040, 0.360, 0.385), (-0.110, 0.380, 0.365),
                    (-0.112, 0.214, 0.362), (0.026, 0.206, 0.378), (0.034, 0.352, 0.412), (-0.102, 0.372, 0.392)])
    blk("crest_b", [(0.020, 0.400, 0.384), (0.150, 0.390, 0.352), (0.140, 0.580, 0.336), (0.010, 0.590, 0.366),
                    (0.024, 0.404, 0.412), (0.144, 0.396, 0.380), (0.134, 0.572, 0.362), (0.014, 0.582, 0.392)])
    # cheek / hinge blocks the jaw hangs from
    blk("cheek_R", [(-0.326, 0.410, -0.150), (-0.246, 0.410, -0.150), (-0.246, 0.650, -0.110), (-0.320, 0.650, -0.110),
                    (-0.330, 0.395, 0.105), (-0.252, 0.395, 0.105), (-0.252, 0.670, 0.120), (-0.316, 0.670, 0.120)])
    chl = blk("cheek_L", [(0.246, 0.470, -0.150), (0.326, 0.470, -0.150), (0.320, 0.650, -0.110), (0.246, 0.650, -0.110),
                          (0.252, 0.500, 0.105), (0.330, 0.500, 0.105), (0.316, 0.670, 0.120), (0.252, 0.670, 0.120)])
    # back-of-head block bridging to the neck
    blk("occiput", [(-0.215, 0.640, -0.120), (0.215, 0.640, -0.120), (0.190, 0.800, -0.070), (-0.190, 0.800, -0.070),
                    (-0.230, 0.640, 0.190), (0.230, 0.640, 0.190), (0.200, 0.810, 0.160), (-0.200, 0.810, 0.160)])

    # the torn left side of the head (side view / side close-up): temple and cheek laid open
    w = cran["wounds"]
    w.add(Hw(0.300, 0.410, 0.120), Hd(0.0, 0.25, 1.0), 0.150, 0.090, normal=Hd(1, 0, 0.2))
    w.z[-1]["strands"] = False
    w.add(Hw(0.292, 0.330, 0.200), Hd(0, 1, 0.2), 0.090, 0.050, normal=Hd(1, 0, 0.3))
    w.z[-1]["strands"] = False
    w.add(Hw(-0.300, 0.300, 0.150), Hd(0, 1, 0.2), 0.070, 0.045, normal=Hd(-1, 0, 0.2))
    w.add(Hw(0.130, 0.330, 0.340), Hd(0, 1, 0), 0.060, 0.040, normal=Hd(0.3, 0, 1))
    w.add(Hw(-0.150, 0.560, 0.320), Hd(1, 0.4, 0), 0.055, 0.040, normal=Hd(-0.3, 0, 1))
    chl["wounds"].add(Hw(0.328, 0.500, -0.020), Hd(0, 0.2, -1), 0.110, 0.050, normal=Hd(1, 0, 0))
    chl["wounds"].z[-1]["strands"] = False
    jw = jaw["wounds"]
    for u, L, W in ((0.86, 0.085, 0.040), (0.22, 0.060, 0.032), (0.64, 0.05, 0.03)):
        p, t, out = rim_point(u)
        jw.add(p + out * (band_width(u) + 0.03) + Hd(0, 1, 0) * 0.07, t, L, W, normal=out)
        jw.z[-1]["spacing"] = 0.03

    build_teeth(m)
    build_soft(m)
    build_eyes(m)

    # rods driven into the skull
    m.add_rod(Hw(-0.255, 0.300, 0.240), Hd(-0.55, 0.0, 1.0), 0.130, 0.026, group=G)
    m.add_rod(Hw(0.085, 0.640, 0.330), Hd(0.10, 0.45, 1.0), 0.170, 0.028, group=G)
    m.add_rod(Hw(0.215, 0.440, 0.270), Hd(0.60, 0.10, 1.0), 0.140, 0.026, group=G)
    m.info["head_back"] = Hw(0.0, 0.720, 0.060)
