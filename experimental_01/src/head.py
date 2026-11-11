"""ASTRA R08 head - Experimental Model 01 (the defining feature, built from the sheet alone).

Head coordinates (metres): x sideways (+x = the creature's left), b = distance back from the
front of the snout, h = height above the upper jaw line.  The panel readings they come from are
noted next to each block; `HEAD` places the head in the world.

Shape, from the sheet: a broad, low, battered block of a skull - a short vertical mask carrying
two recessed square sockets under heavy sloping brows, a forehead that slopes back to a ridged
crown - over an enormous mouth.  The upper lip dips to a blunt point right of centre; the lower
jaw is a narrow U that hangs almost straight down from under the cheeks and hooks forward at the
chin, its teeth fanning forward and up to meet the long upper fangs.
"""
import numpy as np
import kernel as K

# ---- placement ------------------------------------------------------------------------------
HEAD = dict(origin=np.array([0.030, -1.760, 2.410]), pitch=0.0549, yaw=np.radians(0.0), scale=1.000)

HEADP = dict(cell=0.0115, plate=(0.115, 0.095),
             layers=((0.004, 0.010, 1.00, 0.00), (0.011, 0.018, 0.72, 0.05), (0.019, 0.027, 0.34, 0.10)),
             pit=0.018)
JAWP = dict(HEADP, plate=(0.09, 0.075))


def frame(cfg=HEAD):
    p, y = cfg["pitch"], cfg["yaw"]
    Rx = K.rot_axis((1, 0, 0), -p)                     # nose down for positive pitch
    Rz = K.rot_axis((0, 0, 1), y)
    M = Rz @ Rx
    return M[:, 0] * cfg["scale"], M[:, 1] * cfg["scale"], M[:, 2] * cfg["scale"]   # x, back, up


def Hw(x, b, h, cfg=HEAD):
    ex, eb, eh = frame(cfg)
    return cfg["origin"] + x * ex + b * eb + h * eh


def Hd(x, b, h, cfg=HEAD):
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
COLX = np.array([-0.262, -0.231, -0.128, -0.056, 0.074, 0.199, 0.262])
LIP = np.array([0.004, -0.014, -0.060, -0.092, -0.034, 0.000, 0.016])     # the dip of the upper lip
SOCB = np.array([0.036, 0.024, 0.016, 0.006, 0.030, 0.038, 0.046])        # socket floors
SOCT = np.array([0.150, 0.139, 0.109, 0.098, 0.128, 0.151, 0.158])        # socket tops: inner corners low
BROW = np.array([0.186, 0.188, 0.170, 0.160, 0.176, 0.192, 0.186])        # top of the mask
MASK_B = np.array([0.000, -0.004, -0.014, -0.024, -0.014, -0.004, 0.000]) # centre pushed forward (nose)
MASK_BACK = 0.070
SOCKET_DEPTH = 0.095
# pupils: small, deep, toward the inner-lower corner of each socket
PUPILS = [(-0.164, 0.070), (0.122, 0.084)]


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
    info = []
    for (r, c) in sockets:
        cx = (COLX[c] + COLX[c + 1]) / 2
        ch = (SOCB[c] + SOCB[c + 1] + SOCT[c] + SOCT[c + 1]) / 4
        bk = {}
        for rr in (r, r + 1):
            for cc in (c, c + 1):
                x = cx + (COLX[cc] - cx) * 0.90
                h = ch + (rows[rr][cc] - ch) * 0.90
                bk[(rr, cc)] = co.v(Hw(x, mask_b(COLX[cc], rows[rr][cc]) + SOCKET_DEPTH, h))
        co.f([F[r][c], F[r][c + 1], bk[(r, c + 1)], bk[(r, c)]], kind="socket")
        co.f([F[r + 1][c + 1], F[r + 1][c], bk[(r + 1, c)], bk[(r + 1, c + 1)]], kind="socket")
        co.f([F[r + 1][c], F[r][c], bk[(r, c)], bk[(r + 1, c)]], kind="socket")
        co.f([F[r][c + 1], F[r + 1][c + 1], bk[(r + 1, c + 1)], bk[(r, c + 1)]], kind="socket")
        co.f([bk[(r, c)], bk[(r, c + 1)], bk[(r + 1, c + 1)], bk[(r + 1, c)]], kind="socket")
        info.append((cx, ch))
    return co


# ---- cranium (side view crop: 920 px of gape = 0.69 m; heights x0.83 toward the front view) ---
#        b      wb     wc     hc     wt     ht     wi     hi     hr     hbc
CRAN = [(0.050, 0.262, 0.276, 0.085, 0.262, 0.180, 0.125, 0.204, 0.214, 0.060),
        (0.140, 0.280, 0.298, 0.100, 0.280, 0.218, 0.130, 0.254, 0.268, 0.078),
        (0.280, 0.290, 0.310, 0.110, 0.282, 0.246, 0.130, 0.293, 0.309, 0.082),
        (0.440, 0.290, 0.310, 0.115, 0.272, 0.258, 0.120, 0.313, 0.331, 0.062),
        (0.600, 0.270, 0.292, 0.112, 0.250, 0.244, 0.110, 0.296, 0.312, -0.010),
        (0.710, 0.225, 0.246, 0.102, 0.200, 0.204, 0.090, 0.244, 0.257, 0.004),
        (0.765, 0.160, 0.176, 0.096, 0.140, 0.168, 0.060, 0.193, 0.203, 0.030)]
MOUTH_BACK = 0.50          # the palate ends here; behind it the head is solid


def build_cranium(rng):
    co = K.Coarse("cranium")
    rings = []
    for (b, wb, wc, hc, wt, ht, wi, hi, hr, hbc) in CRAN:
        j = lambda s=0.007: rng.normal(0, s)
        dl = 0.018 if 0.2 < b < 0.5 else 0.0            # dented left temple
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
    co.f(rings[0][::-1], kind="core", tag="front")
    co.f(rings[-1], kind="plate", grain=Hd(1, 0, 0), tag="back")
    return co


# ---- lower jaw rim (front view outline + exact side profile) ---------------------------------
#          x       b       h
RIM = [(-0.250, 0.478, -0.045), (-0.240, 0.474, -0.130), (-0.228, 0.468, -0.215), (-0.206, 0.455, -0.305),
       (-0.176, 0.438, -0.410), (-0.146, 0.418, -0.505), (-0.112, 0.394, -0.590), (-0.070, 0.368, -0.655),
       (-0.020, 0.352, -0.684), (0.045, 0.346, -0.690), (0.105, 0.356, -0.672), (0.152, 0.378, -0.628),
       (0.188, 0.402, -0.560), (0.214, 0.424, -0.475), (0.232, 0.442, -0.375), (0.243, 0.458, -0.270),
       (0.249, 0.470, -0.160), (0.252, 0.478, -0.045)]
RIM = np.array(RIM)


def rim_frames():
    """World points of the rim with (tangent, forward, outward) frames."""
    P = np.array([Hw(*p) for p in RIM])
    T, EX, EY = K.path_frames(P, Hd(0, -1, 0))
    return P, T, EX, EY


def build_lower_jaw(rng):
    P, T, EX, EY = rim_frames()
    n = len(P)
    halves = []
    for i in range(n):
        u = i / (n - 1)
        arm = abs(2 * u - 1)                 # 1 at the hinges, 0 at the chin
        back = 0.095 + 0.070 * arm ** 1.3    # jaw bone is deeper toward the hinge (side view)
        out = 0.048 + 0.028 * arm
        halves.append((0.012, back, out, 0.006))
    co = K.loft("jaw", P, halves, Hd(0, -1, 0), chamfer=0.9, rng=rng, jit=0.004)
    # inner face and its front chamfer are gum; the rest is plated bone
    for fi, tag in enumerate(co.tag):
        if tag in ("side7", "side0", "side6"):
            co.kind[fi] = "gum"
        if tag in ("cap0", "cap1"):
            co.kind[fi] = "core"
    return co


# ---- teeth -----------------------------------------------------------------------------------
# Upper front arc: (x, length, radius, lean forward deg, splay out deg).  Read off the front,
# three-quarter and head close-up panels: long at the right corner, longest at the lip point,
# one thick fang left of centre, shorter toward the left corner.
UPPER_FRONT = [(-0.246, 0.215, 0.027, 4, 9), (-0.214, 0.150, 0.020, 10, 6), (-0.186, 0.262, 0.029, 3, 6),
               (-0.150, 0.165, 0.021, 12, 3), (-0.116, 0.130, 0.022, 2, 2), (-0.080, 0.200, 0.025, 8, 2),
               (-0.044, 0.355, 0.035, 2, -2), (-0.006, 0.150, 0.021, 11, 0), (0.030, 0.212, 0.028, 4, -2),
               (0.074, 0.120, 0.022, 9, -3), (0.124, 0.232, 0.033, 3, -4), (0.168, 0.112, 0.021, 10, -5),
               (0.204, 0.150, 0.023, 4, -8), (0.240, 0.100, 0.020, 6, -10)]
# Upper sides: (side, b, length, radius, splay out deg).  The exact side view shows the rear
# teeth as long as the front ones.
UPPER_SIDE = [(-1, 0.085, 0.250, 0.028, 9), (-1, 0.150, 0.205, 0.025, 12), (-1, 0.215, 0.275, 0.030, 8),
              (-1, 0.285, 0.215, 0.026, 11), (-1, 0.350, 0.170, 0.023, 9), (-1, 0.410, 0.105, 0.020, 12),
              (1, 0.080, 0.215, 0.026, 10), (1, 0.140, 0.285, 0.031, 7), (1, 0.205, 0.330, 0.033, 9),
              (1, 0.275, 0.240, 0.027, 12), (1, 0.345, 0.185, 0.024, 9), (1, 0.410, 0.110, 0.020, 12)]
# Lower teeth: (rim parameter 0..1 from the right hinge round the chin to the left hinge, length,
# radius, elevation above the forward direction deg, lean toward the mouth's middle deg)
LOWER = [(0.075, 0.150, 0.021, 72, 8), (0.135, 0.215, 0.025, 68, 10), (0.195, 0.255, 0.027, 62, 6),
         (0.250, 0.230, 0.025, 66, 12), (0.300, 0.285, 0.029, 58, 8), (0.350, 0.250, 0.026, 60, 14),
         (0.398, 0.300, 0.030, 52, 6), (0.440, 0.235, 0.025, 56, 10), (0.478, 0.310, 0.031, 46, 2),
         (0.512, 0.220, 0.024, 54, 0), (0.545, 0.320, 0.032, 44, -3), (0.580, 0.240, 0.025, 52, -8),
         (0.615, 0.295, 0.029, 50, -6), (0.655, 0.255, 0.026, 58, -12), (0.700, 0.315, 0.031, 56, -8),
         (0.748, 0.270, 0.027, 62, -12), (0.800, 0.300, 0.029, 60, -7), (0.852, 0.240, 0.025, 66, -11),
         (0.902, 0.190, 0.023, 70, -8), (0.945, 0.125, 0.020, 74, -8)]


def rim_point(u):
    P, T, EX, EY = rim_frames()
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    d = u * cum[-1]
    i = int(np.clip(np.searchsorted(cum, d) - 1, 0, len(seg) - 1))
    f = (d - cum[i]) / seg[i]
    return P[i] * (1 - f) + P[i + 1] * f, K.unit(T[i] * (1 - f) + T[i + 1] * f), K.unit(EY[i] * (1 - f) + EY[i + 1] * f)


def build_teeth(m):
    rng = np.random.default_rng(m.seed + 404)
    tb = m.bucket("head_teeth", "tooth")
    roots_u, roots_l = [], []
    dn, fw = Hd(0, 0, -1), Hd(0, -1, 0)
    ex = Hd(1, 0, 0)

    def add(root, d, L, r, bend_dir, bend=0.05):
        V, Q, T, tt = K.tooth(root, d, L, r, rng, bend_dir=bend_dir, bend=bend, sides=6, sink=0.035,
                              flat=rng.uniform(0.68, 0.9), twist=rng.uniform(-0.5, 0.5))
        tb.add(V, Q, T, vattr=dict(t=tt, tone=rng.random()))

    for (x, L, r, lean, splay) in UPPER_FRONT:
        h = lip(x)
        root = Hw(x, mask_b(x, h) + 0.022 + 0.006 * rng.normal(), h + 0.012)
        a = np.radians(lean + rng.normal(0, 2.5))
        # splay is signed toward the corner the tooth sits on (table values already carry the sign)
        d = K.unit(dn + fw * np.tan(a) + ex * np.tan(np.radians(-splay + rng.normal(0, 2.0))))
        add(root, d, L, r, -fw, bend=rng.uniform(0.02, 0.07))
        roots_u.append(root)
    for (sd, b, L, r, splay) in UPPER_SIDE:
        wj = float(np.interp(b, [c[0] for c in CRAN], [c[1] for c in CRAN]))
        root = Hw(sd * (wj - 0.018), b, 0.012)
        d = K.unit(dn + ex * sd * np.tan(np.radians(splay + rng.normal(0, 2.5))) + fw * np.tan(np.radians(rng.normal(3, 4))))
        add(root, d, L, r, -ex * sd, bend=rng.uniform(0.03, 0.08))
        roots_u.append(root)
    up = Hd(0, 0, 1)
    for (u, L, r, elev, lean) in LOWER:
        p, t, out = rim_point(u)
        root = p - out * 0.010 + fw * 0.002
        e = np.radians(elev + rng.normal(0, 3.0))
        d = np.cos(e) * fw + np.sin(e) * up
        d = K.unit(d + ex * np.tan(np.radians(lean + rng.normal(0, 2.5))))
        add(root, d, L, r, up, bend=rng.uniform(0.03, 0.09))
        roots_l.append(root)
    m.info["tooth_roots_upper"] = np.array(roots_u)
    m.info["tooth_roots_lower"] = np.array(roots_l)
    m.info["n_teeth"] = (len(UPPER_FRONT) + len(UPPER_SIDE), len(LOWER))


# ---- soft parts ------------------------------------------------------------------------------

def build_soft(m):
    rng = np.random.default_rng(m.seed + 505)
    gum = m.bucket("head_gums", "gum", smooth=True)
    lin = m.bucket("head_mouth", "mouth", smooth=True)
    # upper gum: round the lip and back along both sides
    pts = []
    for b in (0.44, 0.36, 0.27, 0.18, 0.10):
        wj = float(np.interp(b, [c[0] for c in CRAN], [c[1] for c in CRAN]))
        pts.append((-(wj - 0.016), b, 0.004))
    for x in np.linspace(-0.250, 0.250, 15):
        h = lip(x)
        pts.append((x, mask_b(x, h) + 0.026, h + 0.004))
    for b in (0.10, 0.18, 0.27, 0.36, 0.44):
        wj = float(np.interp(b, [c[0] for c in CRAN], [c[1] for c in CRAN]))
        pts.append(((wj - 0.016), b, 0.004))
    Pg = np.array([Hw(*p) for p in pts])
    Rg = 0.024 + 0.006 * np.sin(np.arange(len(Pg)) * 2.1) + rng.normal(0, 0.002, len(Pg))
    V, Q, T = K.tube(Pg, Rg, sides=8, rng=rng, wob=0.06, xhint=Hd(0, 0, 1))
    gum.add(V, Q, T)
    # lower gum along the rim
    P, Tn, EX, EY = rim_frames()
    Pl = P - EY * 0.012 + EX * 0.004
    Rl = 0.023 + 0.006 * np.sin(np.arange(len(Pl)) * 1.7) + rng.normal(0, 0.002, len(Pl))
    V, Q, T = K.tube(Pl, Rl, sides=8, rng=rng, wob=0.06, xhint=Hd(0, -1, 0))
    gum.add(V, Q, T)
    # gum collars round each root
    for roots, d in ((m.info.get("tooth_roots_upper", []), Hd(0, 0, -1)), (m.info.get("tooth_roots_lower", []), Hd(0, -0.6, 0.8))):
        for r in roots:
            V, Q, T = K.spindle(r + d * 0.006, d, 0.05, 0.034, 0.034, Hd(1, 0, 0), segs=8, rings=5, rng=rng)
            gum.add(V, Q, T)
    # cheek straps: from under the temples down onto the jaw arms (both sides; the left is laid bare)
    for sd in (-1, 1):
        for k, (b0, off) in enumerate(((0.47, 0.0), (0.52, 0.012), (0.44, -0.008))):
            pts = [(sd * 0.268, b0 + 0.02, 0.085), (sd * (0.276 + off), b0, 0.02), (sd * (0.266 + off), b0 - 0.005, -0.06),
                   (sd * 0.252, b0 - 0.012 - 0.02 * k, -0.16), (sd * 0.243, b0 - 0.02 - 0.02 * k, -0.27)]
            V, Q, T = K.tube(np.array([Hw(*p) for p in pts]), [0.020, 0.026, 0.028, 0.024, 0.016], sides=7, rng=rng, wob=0.07,
                             xhint=Hd(0, -1, 0))
            gum.add(V, Q, T)
    # throat sack behind the lower jaw: closes the U from behind
    n = len(P)
    back = P + EX * (-0.105) - EY * 0.004
    spine = np.array([Hw(0.012, 0.600, 0.050 - 0.78 * (1 - abs(2 * i / (n - 1) - 1)) ** 0.9 * 1.0) for i in range(n)])
    # spine runs down the middle: parametrise by height instead of by rim index
    hs = np.array([RIM[i][2] for i in range(n)])
    spine = np.array([Hw(0.012, 0.585 - 0.06 * (hs[i] / -0.69), min(hs[i], 0.03)) for i in range(n)])
    nv = 7
    Vm = []
    for i in range(n):
        for k in range(nv):
            v = k / (nv - 1)
            Vm.append((1 - v) * back[i] + v * spine[i] + Hd(0, 1, 0) * 0.05 * np.sin(np.pi * v))
    Vm = np.array(Vm)
    Qm = []
    for i in range(n - 1):
        for k in range(nv - 1):
            a = i * nv + k
            Qm.append([a, a + 1, a + nv + 1, a + nv])
    lin.add(Vm, np.array(Qm))
    lin.add(Vm, np.array(Qm)[:, ::-1])
    # tongue / throat column in the middle of the mouth (stops the view passing straight through)
    cols = [((-0.050, 0.335, -0.640), (-0.045, 0.375, -0.34), (-0.030, 0.430, -0.06), (-0.02, 0.47, 0.05), 0.058),
            ((0.060, 0.340, -0.640), (0.055, 0.385, -0.33), (0.040, 0.440, -0.06), (0.03, 0.48, 0.05), 0.062),
            ((0.005, 0.300, -0.655), (0.005, 0.345, -0.38), (0.005, 0.405, -0.10), (0.0, 0.45, 0.05), 0.070),
            ((-0.130, 0.400, -0.520), (-0.125, 0.430, -0.30), (-0.11, 0.46, -0.06), (-0.09, 0.49, 0.05), 0.050),
            ((0.150, 0.395, -0.530), (0.145, 0.430, -0.30), (0.13, 0.46, -0.06), (0.10, 0.49, 0.05), 0.050)]
    for (a, b_, c, d, r) in cols:
        V, Q, T = K.tube(np.array([Hw(*a), Hw(*b_), Hw(*c), Hw(*d)]), [r * 0.8, r, r * 0.95, r * 0.7], sides=8, rng=rng,
                         wob=0.05, xhint=Hd(1, 0, 0))
        lin.add(V, Q, T)
    # palate ridges
    for b in (0.12, 0.20, 0.29, 0.38):
        pts = [(-0.21, b, 0.02), (-0.10, b + 0.01, 0.055), (0.0, b + 0.015, 0.066), (0.10, b + 0.01, 0.055), (0.21, b, 0.02)]
        V, Q, T = K.tube(np.array([Hw(*p) for p in pts]), 0.022, sides=6, rng=rng, wob=0.05, xhint=Hd(0, 1, 0))
        lin.add(V, Q, T)


def build_eyes(m):
    pb = m.bucket("head_pupils", "pupil", smooth=True)
    pos = []
    for (x, h) in PUPILS:
        c = Hw(x, mask_b(x, h) + SOCKET_DEPTH - 0.022, h)
        V, Q, T = K.spindle(c, Hd(0, 1, 0), 0.020, 0.010, 0.010, Hd(0, 0, 1), segs=10, rings=6)
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

    # heavy brows: thick slabs over each socket, dropping toward the nose (the glare)
    blk("brow_R", [(-0.285, -0.050, 0.150), (-0.092, -0.058, 0.098), (-0.086, 0.060, 0.112), (-0.290, 0.060, 0.160),
                   (-0.282, -0.036, 0.214), (-0.098, -0.044, 0.176), (-0.092, 0.075, 0.214), (-0.286, 0.075, 0.232)])
    blk("brow_L", [(0.040, -0.056, 0.116), (0.284, -0.048, 0.160), (0.290, 0.060, 0.168), (0.036, 0.060, 0.128),
                   (0.046, -0.042, 0.186), (0.280, -0.034, 0.226), (0.286, 0.075, 0.240), (0.042, 0.075, 0.222)])
    # nose wedge between the eyes, running down into the lip point
    blk("nose", [(-0.108, -0.052, -0.074), (-0.012, -0.050, -0.052), (0.000, 0.040, -0.030), (-0.112, 0.040, -0.048),
                 (-0.100, -0.060, 0.120), (0.046, -0.058, 0.128), (0.050, 0.060, 0.150), (-0.104, 0.060, 0.146)])
    # crown slab along the ridge
    blk("crest", [(-0.105, 0.150, 0.262), (0.125, 0.150, 0.262), (0.115, 0.560, 0.305), (-0.095, 0.560, 0.305),
                  (-0.080, 0.170, 0.296), (0.100, 0.170, 0.296), (0.090, 0.540, 0.352), (-0.070, 0.540, 0.352)])
    # cheek / hinge blocks the jaw hangs from
    blk("cheek_R", [(-0.330, 0.405, -0.150), (-0.240, 0.405, -0.150), (-0.240, 0.650, -0.110), (-0.325, 0.650, -0.110),
                    (-0.335, 0.390, 0.105), (-0.250, 0.390, 0.105), (-0.250, 0.670, 0.120), (-0.320, 0.670, 0.120)])
    chl = blk("cheek_L", [(0.240, 0.405, -0.150), (0.330, 0.405, -0.150), (0.325, 0.650, -0.110), (0.240, 0.650, -0.110),
                          (0.250, 0.390, 0.105), (0.335, 0.390, 0.105), (0.320, 0.670, 0.120), (0.250, 0.670, 0.120)])
    # back-of-head block bridging to the neck
    blk("occiput", [(-0.215, 0.640, -0.150), (0.215, 0.640, -0.150), (0.190, 0.800, -0.100), (-0.190, 0.800, -0.100),
                    (-0.230, 0.640, 0.180), (0.230, 0.640, 0.180), (0.200, 0.810, 0.150), (-0.200, 0.810, 0.150)])

    # the torn left side of the head (side view / side close-up): temple and cheek laid open
    w = cran["wounds"]
    w.add(Hw(0.300, 0.360, 0.130), Hd(0.0, 1.0, 0.25), 0.150, 0.085, normal=Hd(1, 0, 0.25))
    w.z[-1]["spacing"] = 0.036
    w.add(Hw(0.285, 0.520, 0.060), Hd(0, 0.3, -1), 0.100, 0.060, normal=Hd(1, 0, 0))
    w.add(Hw(-0.300, 0.300, 0.150), Hd(0, 1, 0.2), 0.070, 0.045, normal=Hd(-1, 0, 0.2))
    w.add(Hw(0.130, 0.330, 0.300), Hd(0, 1, 0), 0.060, 0.040, normal=Hd(0.3, 0, 1))
    w.add(Hw(-0.150, 0.560, 0.290), Hd(1, 0.4, 0), 0.055, 0.040, normal=Hd(-0.3, 0, 1))
    chl["wounds"].add(Hw(0.332, 0.520, -0.010), Hd(0, 0.2, -1), 0.100, 0.075, normal=Hd(1, 0, 0))
    chl["wounds"].z[-1]["spacing"] = 0.036
    mask["wounds"].add(Hw(-0.262, 0.03, 0.090), Hd(0, 0, 1), 0.035, 0.03, normal=Hd(-1, 0, 0))
    jw = jaw["wounds"]
    p, t, out = rim_point(0.86)
    jw.add(p + out * 0.07 + Hd(0, 1, 0) * 0.07, t, 0.085, 0.045, normal=out)
    p, t, out = rim_point(0.22)
    jw.add(p + out * 0.07 + Hd(0, 1, 0) * 0.06, t, 0.060, 0.035, normal=out)

    build_teeth(m)
    build_soft(m)
    build_eyes(m)

    # rods driven into the skull
    m.add_rod(Hw(-0.255, 0.300, 0.215), Hd(-0.55, 0.0, 1.0), 0.130, 0.026, group=G)
    m.add_rod(Hw(0.085, 0.640, 0.295), Hd(0.10, 0.45, 1.0), 0.170, 0.028, group=G)
    m.add_rod(Hw(0.215, 0.440, 0.240), Hd(0.60, 0.10, 1.0), 0.140, 0.026, group=G)
