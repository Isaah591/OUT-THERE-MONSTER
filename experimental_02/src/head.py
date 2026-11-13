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


def Hl(p, cfg=None):
    """World point -> head coordinates (x, b, h)."""
    cfg = cfg or HEAD
    ex, eb, eh = frame(cfg)
    d = (np.asarray(p, float) - cfg["origin"]) / cfg["scale"] ** 2
    return np.array([d @ ex, d @ eb, d @ eh])


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


# ---- the face (front view crop: 620 px across the face = 0.52 m) -------------------------------
# reference columns: face edge | right socket outer | inner | lip point | left socket inner | outer | face edge
COLX = np.array([-0.262, -0.235, -0.124, -0.056, 0.070, 0.205, 0.262])
LIP = np.array([0.006, -0.006, -0.024, -0.096, -0.012, 0.004, 0.020])     # the lip stays high under the sockets and dips between them
SOCB = np.array([0.034, 0.021, 0.013, 0.004, 0.026, 0.034, 0.044])        # socket floors
SOCT = np.array([0.158, 0.148, 0.108, 0.096, 0.124, 0.160, 0.168])        # socket tops: inner corners low
SOCKET_DEPTH = 0.095
# pupils: tiny, deep, toward the inner-lower corner of each socket (not mirrored)
PUPILS = [(-0.168, 0.068), (0.124, 0.084)]
PUPIL_R = 0.0068
PUPIL_DEPTH = 0.058


def lip(x):
    return float(np.interp(x, COLX, LIP))


# ---- skull (Model 02): a stack of horizontal contours, curved in every view -------------------
# Model 01's skull was a flat mask with box slabs on it.  Here every level of the head is a rounded
# outline (a superellipse seen from above), so the face wraps back toward the temples, the brow
# juts over the sockets, the forehead rounds up and back into the dome and the outline is curved
# from the front, the side and above.  The sockets, lip line and pupils keep Model 01's readings.
XS = np.array([-0.270, -0.253, -0.235, -0.180, -0.124, -0.090, -0.056, -0.010, 0.030, 0.070, 0.137, 0.205, 0.232, 0.253, 0.270])
SOCK_COLS = ((2, 4), (9, 11))                                    # ring columns bounding the right / left socket
FB = np.array([-0.50, -0.29, -0.07, 0.15, 0.37, 0.57, 0.75])     # side stations: fraction of the half depth
BX = np.array([0.70, 0.47, 0.235, 0.0, -0.235, -0.47, -0.70])    # back points: fraction of the half width
NEXP = 3.0                                                       # roundness of the outline seen from above
#          height  half-width  front   back      (front / back = depth of the outline on the centre line)
LEVELS = [(0.000, 0.296, 0.006, 0.765),      # jaw edge / lip
          (0.046, 0.303, 0.002, 0.775),      # socket floors
          (0.092, 0.306, 0.002, 0.780),      # socket middles
          (0.138, 0.305, 0.004, 0.780),      # socket tops
          (0.190, 0.299, 0.018, 0.775),      # brow
          (0.242, 0.287, 0.068, 0.768),      # the forehead slopes back at about 35 degrees ...
          (0.292, 0.268, 0.132, 0.752),
          (0.338, 0.240, 0.202, 0.728),
          (0.376, 0.198, 0.276, 0.692),
          (0.402, 0.138, 0.352, 0.634)]      # ... into a broad, rounded crown
SKULL_TOP = (0.006, 0.485, 0.420)
PALATE = (0.0, 0.360, 0.075)
# lumps and dents (x, b, h, radius, amount pushed out): no two quarters of this skull match
LUMPS = [(-0.120, 0.100, 0.270, 0.110, 0.024), (0.140, 0.140, 0.290, 0.100, -0.022), (0.100, 0.520, 0.370, 0.140, 0.020),
         (-0.270, 0.520, 0.220, 0.120, -0.020), (0.290, 0.360, 0.200, 0.120, -0.024), (-0.060, 0.330, 0.380, 0.110, 0.014),
         (0.020, 0.700, 0.250, 0.150, 0.018), (-0.290, 0.200, 0.110, 0.090, 0.012)]
SKULL_C = np.array([0.0, 0.40, 0.12])        # lumps push away from here
REVEAL = 0.044                                # thickness of the armour seen in the socket openings
N_RING = len(XS) + 2 * len(FB) + len(BX)


def _level(h):
    hs = [L[0] for L in LEVELS]
    return tuple(float(np.interp(h, hs, [L[i] for L in LEVELS])) for i in (1, 2, 3))


def _front_b(x, a, bf, bk):
    bc, c = (bf + bk) / 2, (bk - bf) / 2
    t = min(abs(x) / a, 0.999)
    return bc - c * (1 - t ** NEXP) ** (1 / NEXP)


def face_b(x, h):
    """Depth of the skull's front surface at (x, h), before the brow and nose relief."""
    return _front_b(x, *_level(max(h, 0.0)))


mask_b = face_b          # the name the teeth, gums and checks use


def jaw_half_width(b):
    """Half width of the upper jaw edge at depth b."""
    a, bf, bk = _level(0.0)
    bc, c = (bf + bk) / 2, (bk - bf) / 2
    t = min(abs(b - bc) / c, 0.999)
    return a * (1 - t ** NEXP) ** (1 / NEXP)


def _brow_w(x):
    return float(np.exp(-((x + 0.180) / 0.105) ** 4) + np.exp(-((x - 0.137) / 0.115) ** 4))


def build_skull(rng):
    """Returns (coarse skull, {(row, column): face index}) - the map is used to lay armour slabs."""
    co = K.Coarse("skull")
    NF, NS, NB = len(XS), len(FB), len(BX)
    lipx, flo, top = (np.interp(XS, COLX, A) for A in (LIP, SOCB, SOCT))

    def rows(j):
        return [lipx[j], flo[j], (flo[j] + top[j]) / 2, top[j], top[j] + 0.050 + 0.010 * _brow_w(XS[j])]

    side_w = (0.22, 0.07, 0.0, 0.0, 0.0, 0.0, 0.0)
    C = []
    for k, (hs, a, bf, bk) in enumerate(LEVELS):
        bc, c = (bf + bk) / 2, (bk - bf) / 2
        sx = min(1.0, a / LEVELS[0][1])                 # the dome narrows: the columns close up
        ring = []
        for j in range(NF):                             # across the face, right to left
            x = XS[j] * sx
            wf = float(np.clip((0.300 - abs(XS[j])) / 0.060, 0.35, 1.0))
            h = hs + wf * (rows(j)[k] - hs) if k <= 4 else hs
            bb = _front_b(x, a, bf, bk)
            if k <= 5:
                bw = _brow_w(XS[j])
                fwd = bw * (0.0, 0.0, 0.002, 0.014, 0.030, 0.012)[k]                        # brow ridge
                xn = -0.056 + 0.026 * min(max(h, 0.0) / 0.19, 1.0)
                fwd += float(np.exp(-((XS[j] - xn) / 0.042) ** 2)) * (0.020, 0.024, 0.024, 0.020, 0.012, 0.004)[k]   # nose ridge
                if abs(XS[j]) > 0.17:
                    fwd += (0.012, 0.012, 0.004, 0.0, 0.0, 0.0)[k]                          # cheekbones
                if k == 0:
                    fwd += 0.008                                                            # the lip overhangs the teeth
                bb -= fwd
            ring.append([x, bb, h])
        for i, fb in enumerate(FB):                     # left side, front to back
            h = hs + side_w[i] * (rows(NF - 1)[k] - hs) if k <= 4 else hs
            ring.append([a * (1 - abs(fb) ** NEXP) ** (1 / NEXP), bc + fb * c, h])
        for fx in BX:                                   # across the back, left to right
            ring.append([fx * a, bc + c * (1 - abs(fx) ** NEXP) ** (1 / NEXP), hs])
        for i in range(NS - 1, -1, -1):                 # right side, back to front
            fb = FB[i]
            h = hs + side_w[i] * (rows(0)[k] - hs) if k <= 4 else hs
            ring.append([-a * (1 - abs(fb) ** NEXP) ** (1 / NEXP), bc + fb * c, h])
        C.append(np.array(ring))
    C = np.array(C)                                     # (levels, ring points, 3) in head coordinates
    # battering: nothing on this head is true - swell and pinch the outline, dent the left temple
    flat = C.reshape(-1, 3)
    nz = (K.fbm(flat * np.array([1.0, 1.0, 1.4]), 4.2, 3, 71) - 0.5)
    for k in range(len(LEVELS)):
        bc = (LEVELS[k][2] + LEVELS[k][3]) / 2
        for i in range(N_RING):
            x, bb, h = C[k, i]
            face = i < NF and k <= 4
            amp = 0.030 if face else 0.075
            sck = face and (SOCK_COLS[0][0] <= i <= SOCK_COLS[0][1] or SOCK_COLS[1][0] <= i <= SOCK_COLS[1][1]) and 1 <= k <= 3
            if sck:
                amp = 0.010                              # the sockets stay square
            g = 1.0 + amp * 2 * nz[k * N_RING + i]
            x, bb = x * g, bc + (bb - bc) * g
            h += (0.0 if sck else 0.008) * float(rng.normal())
            q = np.array([x, bb, h])
            if not sck:
                for (lx, lb, lh, lr, amt) in LUMPS:
                    d2 = ((q - (lx, lb, lh)) ** 2).sum() / lr ** 2
                    if d2 < 6.0:
                        q = q + K.unit(q - SKULL_C) * amt * np.exp(-d2) * (0.5 if face else 1.0)
            C[k, i] = q
    ids = [[co.v(Hw(*C[k, i])) for i in range(N_RING)] for k in range(len(LEVELS))]
    holes = {(k, i) for k in (1, 2) for (c0, c2) in SOCK_COLS for i in range(c0, c2)}
    grid = {}
    for k in range(len(LEVELS) - 1):
        for i in range(N_RING):
            if (k, i) in holes:
                continue
            j = (i + 1) % N_RING
            grid[(k, i)] = len(co.F)
            co.f([ids[k][i], ids[k][j], ids[k + 1][j], ids[k + 1][i]], patch="skull", tag="skull")
    tp = co.v(Hw(*SKULL_TOP))
    K_ = len(LEVELS) - 1
    for i in range(N_RING):
        co.f([ids[K_][i], ids[K_][(i + 1) % N_RING], tp], patch="skull", tag="crown")
    pal = co.v(Hw(*PALATE))
    for i in range(N_RING):
        co.f([ids[0][(i + 1) % N_RING], ids[0][i], pal], kind="void", tag="palate")
    # sockets: square windows through thick armour - a reveal of thin plating (a part of its own,
    # so the face plates stop square at the opening), then a black pocket
    rims = K.Coarse("socket_rims")
    for si, (c0, c2) in enumerate(SOCK_COLS):
        loop = [(1, c0), (1, c0 + 1), (1, c2), (2, c2), (3, c2), (3, c0 + 1), (3, c0), (2, c0)]
        O = np.array([C[k, i] for (k, i) in loop])
        cen = O.mean(0)
        n = len(loop)
        Ro, Ri, I, B = [], [], [], []
        for pt in O:
            Ro.append(rims.v(Hw(*pt)))
            q = pt + (cen - pt) * 0.05
            q[1] = pt[1] + REVEAL
            Ri.append(rims.v(Hw(*q)))
            I.append(co.v(Hw(*q)))
            q = pt + (cen - pt) * 0.10
            B.append(co.v(Hw(q[0], cen[1] + SOCKET_DEPTH, q[2])))
        for t in range(n):
            u = (t + 1) % n
            rims.f([Ro[t], Ro[u], Ri[u], Ri[t]], patch=f"rim{si}", tag="socket_rim")
            co.f([I[t], I[u], B[u], B[t]], kind="socket", tag="socket_wall")
        co.f(B, kind="socket", tag="socket_back")
    co.rims = rims
    co.grid = grid
    co.ring_ids = ids
    return co


def raise_slab(name, src, faces, t, rng):
    """A thick plate of armour lying on a group of the skull's faces and following their curve."""
    V = src.arrays()
    vn = {}
    for fi in faces:
        n = K.newell(V[src.F[fi]])
        for v in src.F[fi]:
            vn[v] = vn.get(v, 0.0) + n
    co = K.Coarse(name)
    tt = t * (1 + rng.normal(0, 0.07))
    top = {v: co.v(V[v] + K.unit(n) * tt * (1 + rng.normal(0, 0.10))) for v, n in vn.items()}
    base = {v: co.v(V[v] - K.unit(n) * 0.004) for v, n in vn.items()}
    edges = set()
    for fi in faces:
        f = src.F[fi]
        co.f([top[v] for v in f], patch=name, tag="slab_top")
        for k in range(len(f)):
            edges.add((f[k], f[(k + 1) % len(f)]))
    for (a_, b_) in sorted(edges):
        if (b_, a_) not in edges:
            co.f([top[a_], base[a_], base[b_], top[b_]], patch=name, tag="slab_edge")
    return co


# armour slabs on the skull: (name, thickness m, [(row, first column, last column), ...]).  Rows count
# up from the lip (3-4 = the brow band); columns run round the ring: 0-13 across the face from the
# creature's right, 14-21 down its left side, 22-28 across the back, 29-35 up its right side.
SLABS = [("brow_R", 0.036, [(3, 0, 5), (4, 0, 5), (5, 1, 3)]),
         ("brow_L", 0.031, [(3, 8, 13), (4, 9, 13), (5, 10, 12)]),
         ("nasal", 0.022, [(0, 5, 7), (1, 5, 7), (2, 5, 7), (3, 6, 7)]),
         ("forehead_a", 0.027, [(5, 4, 8), (6, 4, 7), (7, 5, 7)]),
         ("forehead_b", 0.024, [(6, 9, 12), (7, 9, 12), (8, 9, 11)]),
         ("zygo_R", 0.025, [(0, 31, 35), (1, 31, 35), (2, 32, 35)]),
         ("zygo_L", 0.022, [(0, 14, 15), (1, 14, 15)]),
         ("temple_R", 0.024, [(3, 30, 33), (4, 30, 34), (5, 31, 33)]),
         ("occiput_a", 0.025, [(2, 22, 27), (3, 22, 27), (4, 23, 26)]),
         ("crown_a", 0.023, [(6, 17, 20), (7, 17, 20), (8, 18, 19)]),
         ("crown_b", 0.026, [(6, 24, 30), (7, 25, 29)])]
# slabs carry broader, flatter plating than the skull under them; the socket reveals a thin skin
SLABP = dict(HEADP, plate=(0.125, 0.105), layers=((0.003, 0.007, 1.00, 0.00), (0.009, 0.014, 0.60, 0.05), (0.016, 0.023, 0.22, 0.10)))
RIMP = dict(HEADP, plate=(0.07, 0.06), layers=((0.002, 0.005, 1.00, 0.00), (0.006, 0.010, 0.35, 0.05)), pit=0.02)


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
UPPER_SIDE = [(-1, 0.170, 0.335, 0.033, 5), (-1, 0.245, 0.265, 0.028, 8), (-1, 0.325, 0.345, 0.034, 4), (-1, 0.405, 0.275, 0.029, 7),
              (1, 0.165, 0.275, 0.030, 7), (1, 0.240, 0.340, 0.037, 4), (1, 0.320, 0.275, 0.030, 8), (1, 0.400, 0.285, 0.031, 5)]
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
    for b in (0.44, 0.36, 0.27, 0.19):
        pts.append((-(jaw_half_width(b) - 0.020), b, 0.004))
    for x in np.linspace(-0.250, 0.250, 15):
        h = lip(x)
        pts.append((x, mask_b(x, h) + 0.034, h + 0.006))
    for b in (0.19, 0.27, 0.36, 0.44):
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
            # on the skull the sinews lie in the torn surface; below it they hang free to the jaw
            pp = [tuple(Hl(on_skull(x_, b_, h_, lift=0.2 * r))) if h_ > 0.035 else (x_, b_, h_) for (x_, b_, h_) in pp]
            cord(gum, pp, [r * 0.62, r * 0.85, r * 0.95, r * 0.85, r * 0.6], rng, sides=8, wob=0.08, wander=0.012, n=16)
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
        c = Hw(x, mask_b(x, h) + PUPIL_DEPTH, h)
        V, Q, T = K.spindle(c, Hd(0, 1, 0), PUPIL_R * 2, PUPIL_R, PUPIL_R, Hd(0, 0, 1), segs=10, rings=6)
        pb.add(V, Q, T)
        pos.append(c)
    m.info["pupils"] = np.array(pos)


# ---- assembly --------------------------------------------------------------------------------

class Surf:
    """Closest point on a coarse mesh's plated faces (sampled): seats wounds, rods and sinews on it."""

    def __init__(self, co, n=7):
        from scipy.spatial import cKDTree
        V = co.arrays()
        P, N = [], []
        for fi, f in enumerate(co.F):
            if co.kind[fi] not in ("plate", "core"):
                continue
            poly = V[f]
            nrm = K.newell(poly)
            if len(f) == 4:
                for u in np.linspace(0, 1, n):
                    for v in np.linspace(0, 1, n):
                        P.append((1 - u) * (1 - v) * poly[0] + u * (1 - v) * poly[1] + u * v * poly[2] + (1 - u) * v * poly[3])
                        N.append(nrm)
            else:
                for u in np.linspace(0, 1, n):
                    for v in np.linspace(0, 1 - u, max(2, int(round(n * (1 - u))))):
                        P.append(poly[0] * (1 - u - v) + poly[1] * u + poly[2] * v)
                        N.append(nrm)
        self.P, self.N = np.array(P), np.array(N)
        self.tree = cKDTree(self.P)

    def __call__(self, p, lift=0.0):
        _, i = self.tree.query(np.asarray(p, float))
        return self.P[i] + self.N[i] * lift, self.N[i]


SKULL_SURF = [None]


def on_skull(x, b, h, lift=0.0):
    """World point on the skull's surface nearest the head-coordinate point (x, b, h)."""
    return SKULL_SURF[0](Hw(x, b, h), lift)[0]


def build_head(m):
    rng = np.random.default_rng(m.seed + 303)
    G = "head"
    sk = build_skull(rng)
    S = Surf(sk)
    SKULL_SURF[0] = S
    # armour slabs: thick broken plates lying on the skull and following its curve
    slabs = []
    for (name, t, spans) in SLABS:
        faces = [sk.grid[(k, i % N_RING)] for (k, c0, c1) in spans for i in range(c0, c1 + 1) if (k, i % N_RING) in sk.grid]
        slabs.append(raise_slab(name, sk, faces, t, rng))
        for fi in faces:
            sk.kind[fi] = "core"                 # hidden under the slab: no plating of its own
    skull = m.part(sk, params=HEADP, group=G)
    m.part(sk.rims, params=RIMP, group=G)
    for co in slabs:
        m.part(co, params=SLABP, group=G)
    jaw = m.part(build_lower_jaw(rng), params=JAWP, group=G)

    def blk(name, P8, **kw):
        return m.part(hexa(name, [Hw(*p) for p in P8], rng=rng, jit=0.004, **kw), params=HEADP, group=G)

    # hinge blocks the jaw hangs from, under the back corners of the skull
    blk("hinge_R", [(-0.326, 0.410, -0.150), (-0.246, 0.410, -0.150), (-0.246, 0.650, -0.110), (-0.320, 0.650, -0.110),
                    (-0.322, 0.395, 0.060), (-0.240, 0.395, 0.060), (-0.240, 0.670, 0.070), (-0.310, 0.670, 0.070)])
    chl = blk("hinge_L", [(0.246, 0.470, -0.150), (0.326, 0.470, -0.150), (0.320, 0.650, -0.110), (0.246, 0.650, -0.110),
                          (0.240, 0.500, 0.060), (0.322, 0.500, 0.060), (0.310, 0.670, 0.070), (0.240, 0.670, 0.070)])
    # back-of-head block bridging to the neck
    blk("occiput", [(-0.215, 0.640, -0.120), (0.215, 0.640, -0.120), (0.190, 0.800, -0.070), (-0.190, 0.800, -0.070),
                    (-0.225, 0.640, 0.150), (0.225, 0.640, 0.150), (0.195, 0.800, 0.130), (-0.195, 0.800, 0.130)])

    # the torn left side of the head (side view / side close-up): temple and cheek laid open
    w = skull["wounds"]

    def tear(x, b, h, axis, L, W, strands=True):
        c, n = S(Hw(x, b, h))
        ax = Hd(*axis)
        w.add(c, K.unit(ax - (ax @ n) * n), L, W, normal=n)
        w.z[-1]["strands"] = strands

    tear(0.300, 0.420, 0.110, (0.0, 0.20, 1.0), 0.125, 0.052, strands=False)
    tear(0.292, 0.350, 0.205, (0, 1, 0.3), 0.070, 0.040, strands=False)
    tear(-0.300, 0.300, 0.150, (0, 1, 0.2), 0.070, 0.045)
    tear(0.130, 0.330, 0.360, (0, 1, 0), 0.060, 0.040)
    tear(-0.150, 0.560, 0.330, (1, 0.4, 0), 0.055, 0.040)
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
    for (x, b, h, d, L, r) in ((-0.255, 0.300, 0.250, (-0.55, 0.0, 1.0), 0.130, 0.026),
                               (0.085, 0.640, 0.330, (0.10, 0.45, 1.0), 0.170, 0.028),
                               (0.215, 0.440, 0.290, (0.60, 0.10, 1.0), 0.140, 0.026)):
        c, n = S(Hw(x, b, h))
        m.add_rod(c - n * 0.015, Hd(*d), L, r, group=G)
    m.info["head_back"] = Hw(0.0, 0.720, 0.060)
