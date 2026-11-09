"""
v11 head (head anatomy correction; head_v10.py and the body are kept unchanged). The mouth, lower
jaw and teeth are solved from the approved sheet's own panels (SHEET: every tooth's root and tip,
the front panel's mouth outline, the side panel's jaw and chin), not re-styled from v10's head:

- cranium: v10's planar, broken skull (blocks_v10), with the upper jaw's edge raised 0.06 units so
  the eye sockets sit just above the upper teeth, as in the front and three-quarter panels.
- lower jaw (solve_jaw): hinged under the cheek, ahead of the neck. Its opening and length put the
  chin on the side panel's jaw line; its inner rim is solved, side by side, to project onto the
  front panel's asymmetric mouth outline. A thin, uneven bony rim with a lobed gum along its top;
  the chin's right corner broken off.
- teeth (plan_teeth): 16 upper - the front panel's 10, 3 long ones behind the right corner and 3
  short ones at the left corner (side panel) - and 18 lower - the front panel's crowded bundle of
  14 and 4 from the side panel's fan, in two rows where crowded. The short teeth at the chin point
  forward, the tall ones stand up behind them. Cigar-shaped, twisted fangs; none passes through
  another (_separate).
- tissue: gums, torn cheek bands at the gape, dark-red inner cheek walls set back in the mouth, a
  dark tissue floor, strands and palate ridges; black only deep in the throat.

Space: the cranium's local space in head units (1 unit = HEAD_SCALE metres), origin at the middle
of the skull's length at the upper gum line, front -Y, Z up; the jaw is parented to the cranium and
pivots at its own origin (the hinge), extending along its -Y.
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

import blocks_v10 as B
import monster_detail as D
import sculpt as SC

rng = random.Random(1010)
U = 0.60
FAST = False
HINGE = Vector((0.0, 0.42, -0.22))      # side panel: the jaw hangs from under the cheek, ahead of the neck
DISLOCATE = Vector((0.0, 0.0, -0.02))
FACE_Y = -0.70                       # the face plate
RIDGE_X = 0.07                       # the crest of the forehead and crown (front view: off-centre peak)
NOSE_X = -0.09                       # the face's vertical nasal ridge between the sockets
SLOPE_L, SLOPE_R = 0.30, 0.65        # how fast the face recedes from it to the left and to the right


def face_y(x):
    """The face plate's depth at x (the wedge)."""
    return FACE_Y + np.where(np.asarray(x) > NOSE_X, SLOPE_L, SLOPE_R) * np.abs(np.asarray(x) - NOSE_X)
GUM_Z = 0.005                        # the face plate's lower edge (upper gum line): front and 3/4 panels
                                     # put it higher than v10 (sockets just above the teeth)

# Eye sockets: square holes in the face plate (x, z centre; half width, half height; tilt in the
# face plane, degrees; depth into the skull). Positions as v8/v9 (three-quarter view's pupils).
SOCKETS = [((-0.336, 0.165), (0.082, 0.083), -7.0, 0.150),      # the monster's right: lower, outer
           ((0.133, 0.203), (0.090, 0.078), 6.0, 0.140)]        # left: higher, nearer the midline
EYES = [(c[0], c[1], k) for (c, _, _, _), k in zip(SOCKETS, (1.25, 1.15))]


def _bounds_skull():
    return (-0.66, -0.86, -0.42), (0.66, 0.86, 0.86)


# ---------------------------------------------------------------------------
# Cranium
# ---------------------------------------------------------------------------
def skull_base(G):
    P = lambda n, p: B.plane(G, n, p)
    planes = [
        P((0, -1, 0), (0, FACE_Y, 0)),                          # face plate (vertical)
        P((SLOPE_L, -1, 0), (NOSE_X, FACE_Y, 0)),               # ...angled back from the nasal ridge:
        P((-SLOPE_R, -1, 0), (NOSE_X, FACE_Y, 0)),              #    the right half steeply (three-quarter view)
        P((0, -1, 0.40), (0, FACE_Y, 0.21)),                    # brow, leaning back
        P((0.0, -0.47, 0.88), (RIDGE_X, -0.635, 0.350)),        # forehead: a straight brow line (3/4 view)
        P((0.34, 0.02, 0.94), (RIDGE_X, 0.10, 0.575)),          # crown, left half: a gable rising to the
        P((-0.36, 0.02, 0.93), (RIDGE_X, 0.10, 0.575)),         # off-centre ridge (front view's peak)
        P((1, 0.10, 0.06), (0.455, -0.30, 0.10)),               # left side (narrowing to the back)
        P((-1, 0.10, 0.06), (-0.500, -0.10, 0.10)),             # right side, widest behind the face...
        P((-1, -0.35, 0.06), (-0.500, -0.10, 0.10)),            # ...narrowing to the front: the right socket
                                                                #    opens at the face's corner (close-up)
        P((0.70, 0.05, 0.71), (0.43, 0.0, 0.470)),              # left top edge, small chamfer
        P((-0.70, 0.05, 0.71), (-0.44, 0.0, 0.420)),            # right top edge
        P((0, 1, 0), (0, 0.70, 0)),                             # back
        P((0, 0.966, 0.258), (0, 0.615, 0.62)),                 # back of the crown, steep
        P((-0.30, -0.30, 0.90), (-0.40, -0.40, 0.44)),          # right-front corner drops
        P((0.75, -0.66, 0.0), (0.40, -0.66, 0.0)),              # front-left vertical corner, cut
        P((-0.75, -0.66, 0.0), (-0.41, -0.67, 0.0)),            # front-right vertical corner
        P((0.55, -0.45, -0.70), (0.38, -0.66, GUM_Z + 0.03)),    # lower face corners, cut back
        P((-0.55, -0.45, -0.70), (-0.38, -0.66, GUM_Z + 0.03)),
    ]
    front = B.inter(*planes, P((0, 0, -1), (0, 0, GUM_Z)))     # the face block down to the gum line
    # the rear block over the jaw hinges reaches lower, sloping up toward the face
    rear = B.inter(*planes, P((0, 0, -1), (0, 0.6, -0.27)), P((0, -0.62, -0.78), (0, 0.10, -0.06)))
    return B.union(front, rear)


def _socket_boxes(G, grow=0.0, depth_add=0.0, front_only=None):
    out = []
    for (cx, cz), (hw, hh), tilt, depth in SOCKETS:
        d = depth + depth_add if front_only is None else front_only
        R = B.rot(0.0, tilt, 0.0)
        cy = float(face_y(cx)) - 0.25 + (d + 0.25) / 2
        out.append(B.box(G, (cx, cy, cz), (hw + grow, (d + 0.25) / 2, hh + grow), R))
    return B.union(*out)


# hard breaks: stepped notches knocked out of the edges (centre, half extents, rotation x/y/z deg)
NOTCHES = [((-0.46, -0.62, 0.34), (0.07, 0.06, 0.05), (0, 0, 8)),      # right brow corner
           ((-0.30, -0.62, 0.40), (0.06, 0.05, 0.04), (0, 5, 0)),
           ((0.42, -0.58, 0.38), (0.08, 0.07, 0.06), (0, 0, -6)),      # left brow corner
           ((0.30, -0.50, 0.46), (0.05, 0.06, 0.04), (8, 0, 0)),
           ((-0.10, -0.64, 0.30), (0.05, 0.04, 0.03), (0, 0, 0)),      # brow over the nose
           ((-0.44, -0.20, 0.47), (0.06, 0.09, 0.05), (0, 0, 0)),      # right top edge, stepped
           ((-0.45, 0.18, 0.44), (0.05, 0.07, 0.06), (0, 0, 10)),
           ((0.44, -0.30, 0.50), (0.05, 0.08, 0.05), (0, 0, 0)),       # left top edge
           ((0.44, 0.30, 0.47), (0.06, 0.06, 0.05), (0, 0, -8)),
           ((-0.20, 0.66, 0.53), (0.10, 0.06, 0.06), (0, 0, 0)),       # back of the crown
           ((0.24, 0.68, 0.46), (0.08, 0.06, 0.07), (0, 0, 0)),
           ((0.46, 0.62, 0.20), (0.06, 0.08, 0.07), (0, 0, 0)),        # back corners
           ((-0.48, 0.60, 0.26), (0.06, 0.08, 0.08), (0, 0, 0)),
           ((-0.46, -0.62, 0.02), (0.06, 0.06, 0.06), (0, 0, 0)),      # cheek corners at the gum line
           ((0.43, -0.60, -0.02), (0.05, 0.07, 0.05), (0, 0, 0)),
           ((0.05, -0.70, -0.05), (0.06, 0.04, 0.03), (0, 0, 0)),      # gum line, broken
           ((-0.22, -0.70, -0.06), (0.04, 0.03, 0.03), (0, 0, 0))]
# proud chunks breaking the outline (centre, half extents, rotation)
CHUNKS = [((-0.44, -0.30, 0.44), (0.055, 0.06, 0.06), (0, 0, 6)),          # right top corner, broken up
          ((-0.30, -0.05, 0.53), (0.06, 0.05, 0.035), (0, 0, 12)),
          ((0.28, 0.08, 0.55), (0.05, 0.07, 0.035), (0, 6, -8)),
          ((-0.44, -0.47, 0.38), (0.05, 0.05, 0.045), (0, 0, 0)),         # right brow corner chunk
          ((0.43, -0.53, 0.43), (0.05, 0.05, 0.045), (0, 0, 15)),         # left brow corner chunk
          ((0.10, 0.42, 0.58), (0.07, 0.05, 0.03), (0, 0, 5))]
# torn cheeks: the gape torn up into the skull's sides, onto red flesh
TEARS = [((0.47, -0.17, 0.27), (0.09, 0.065, 0.10), (34, 0, 0)),     # left side: a stepped diagonal tear from
         ((0.47, -0.06, 0.15), (0.09, 0.075, 0.10), (28, 0, 0)),     # behind the brow down to the hinge
         ((0.47, 0.06, 0.04), (0.09, 0.070, 0.09), (40, 0, 0)),
         ((0.47, 0.15, -0.04), (0.09, 0.055, 0.06), (18, 0, 0)),
         ((-0.49, 0.04, 0.08), (0.08, 0.065, 0.09), (30, 0, 0)),     # right side, smaller
         ((-0.49, -0.05, 0.17), (0.08, 0.045, 0.06), (20, 0, 0))]


def skull_sdf(G):
    F = skull_base(G)
    for c, h, r in CHUNKS:
        F = B.union(F, B.inter(B.box(G, c, h, B.rot(*r)), skull_base(G) - 0.06))
    sock = _socket_boxes(G)
    rim = _socket_boxes(G, grow=0.030, front_only=0.035)      # a stepped frame around each socket
    F = B.sub(F, sock, rim)
    for c, h, r in NOTCHES:
        F = B.sub(F, B.box(G, c, h, B.rot(*r)))
    tear = B.union(*[B.box(G, c, h, B.rot(*r)) for c, h, r in TEARS])
    F = B.sub(F, tear)
    # vaulted palate: the face block hollowed from below behind the front rim
    pal = B.box(G, (0.0, -0.20, GUM_Z - 0.02), (0.30, 0.36, 0.085), B.rot(0, 0, 0))
    F = B.sub(F, pal)
    return F, sock, tear, pal


def build_skull(col, M):
    lo, hi = _bounds_skull()
    G = B.Grid(lo, hi, 0.010 if not FAST else 0.016)
    F, sock, tear, pal = skull_sdf(G)
    keep = (sock > 0.02) & (tear > 0.02) & (pal > 0.02)
    F, tid, val, seam, hole = B.tiles(G, F, size=0.078, seed=11, raised=(0.0, 0.026), sunken=(-0.018, 0.0),
                                      p_sunk=0.34, p_missing=0.13, missing=-0.045, tilt=0.14, seam=0.0060,
                                      seam_depth=0.012, wobble=0.020, mask=keep)
    sk = B.to_object("Cranium", F, G, col, [M["rust"]])
    S = SC.Surf(sk, U)
    co = S.co / U
    S.a["socket"] = (B.sample(G, sock, co) < 0.012) * 1.0
    S.a["tissue"] = np.maximum((B.sample(G, tear, co) < 0.015) * 1.0, (B.sample(G, pal, co) < 0.012) * 0.8)
    S.a["flake"] = B.sample(G, val, co) ** 2.0                  # plate tones, mostly dark (the sheet's skull)
    S.a["crack"] = np.clip(B.sample(G, seam, co) * 1.4, 0, 1)
    S.a["pit"] = B.sample(G, hole, co)
    S.a_socket_final = S.a["socket"]
    if not FAST:
        SC.blood(S, 68, drips=5, near=0.03)
    SC.finish(S, sk, decimate_ratio=1.0, sharp_deg=30.0)
    return sk


# ---------------------------------------------------------------------------
# The approved sheet's mouth anatomy, read off its front, three-quarter and exact-side panels
# (panel px): each tooth as root -> tip, the mouth's outline, the lower jaw's edges
# ---------------------------------------------------------------------------
SHEET = {
    "front_upper": [((231, 60), (231, 80)), ((239, 62), (237, 92)), ((247, 63), (246, 84)), ((252, 64), (251, 76)),
                    ((259, 62), (258, 110)), ((266, 64), (265, 80)), ((272, 62), (271, 88)), ((279, 61), (278, 72)),
                    ((286, 60), (284, 88)), ((293, 60), (292, 71))],
    # lower row, re-read on sharpened 11-12x gridded zooms: a crowded bundle fanning from the chin -
    # the monster's right group leans outward 6-14 deg, the middle stands upright, the left side leans
    # in a little; the tall teeth behind the chin reach about half-way up the mouth
    "front_lower": [((248, 146), (241, 105)), ((253, 151), (245, 113)), ((256, 153), (250, 115)), ((261, 149), (255, 109)),
                    ((265, 146), (261, 111)), ((262, 154), (257, 131)), ((269, 154), (268, 135)), ((275, 153), (275, 118)),
                    ((279, 153), (278, 132)), ((283, 147), (282, 118)), ((288, 139), (285, 105)), ((293, 128), (290, 96)),
                    ((296, 119), (295, 92)), ((298, 109), (297, 88))],
    "front_mouth_left": [(232, 62), (235, 80), (237, 100), (238, 120), (241, 138), (246, 147), (252, 153), (260, 157)],
    "front_mouth_right": [(300, 60), (301, 85), (298, 100), (295, 120), (290, 135), (283, 146), (275, 153), (268, 156)],
    "side_upper": [((90, 106), (91, 135)), ((96, 107), (98, 140)), ((104, 107), (106, 157)), ((111, 106), (115, 143)),
                   ((117, 106), (120, 172)), ((123, 105), (126, 150)), ((129, 104), (132, 127)), ((134, 103), (135, 120))],
    "side_lower": [((148, 218), (128, 205)), ((150, 210), (124, 192)), ((152, 200), (122, 180)), ((155, 190), (130, 165)),
                   ((158, 180), (138, 150)), ((160, 170), (142, 143)), ((163, 160), (152, 135)), ((166, 150), (160, 128)),
                   ((168, 140), (162, 120)), ((170, 130), (165, 110))],
    "34_lower": [((186, 199), (178, 167)), ((191, 200), (181, 157)), ((196, 201), (189, 152)), ((201, 202), (195, 150)),
                 ((206, 202), (205, 181)), ((212, 202), (210, 158)), ((219, 201), (220, 158)), ((227, 192), (226, 134)),
                 ((232, 176), (230, 125)), ((237, 160), (235, 124))],
    "34_gum_v": 96.0, "34_chin_v": 206.0,
    "side_chin": (154.5, 218),        # on the side panel's jaw line, 8 px short of its chin (see notes)
}
FRONT_CAM = (284.96, 462.72, 160.0)     # sheet front panel: u = u0 + s * x, v = v0 - s * z (world metres)
SIDE_CAM = (309.46, 466.26, 150.19)     # sheet side panel: u = u0 + s * y, v = v0 - s * z
SHEET_FRONT_GUM_V, SHEET_FRONT_CHIN_V = 60.0, 157.0
# The front panel draws the mouth shorter than the side and three-quarter panels (gum line to chin
# 0.61 m against 0.81 and 0.70 m): its vertical positions in the mouth are mapped linearly between
# the model's gum line and chin; its horizontal positions are used as they are.


class Frame:
    """Transforms of the head being built: cranium-local -> world, jaw-local -> cranium-local."""

    def __init__(self, location, rotation, scale, open_deg, roll_deg):
        self.C = Matrix.LocRotScale(Vector(location), Euler(rotation), Vector((scale, scale, scale)))
        self.Ci = self.C.inverted()
        self.set_jaw(open_deg, roll_deg)

    def set_jaw(self, open_deg, roll_deg):
        self.open_deg, self.roll_deg = open_deg, roll_deg
        self.J = Matrix.LocRotScale(HINGE + DISLOCATE, Euler((math.radians(open_deg), math.radians(-roll_deg),
                                                             math.radians(1.5))), Vector((1, 1, 1)))
        self.Ji = self.J.inverted()

    def jw(self, p):                     # jaw-local -> world
        return self.C @ (self.J @ Vector(p))

    def hw(self, p):                     # cranium-local -> world
        return self.C @ Vector(p)

    def wj(self, p):                     # world -> jaw-local
        return self.Ji @ (self.Ci @ Vector(p))

    def wh(self, p):                     # world -> cranium-local
        return self.Ci @ Vector(p)


CAM34 = (0.43434609482510533, 0.05584576896904435, 22.989318239549853, 252.17536195340818,
         -0.21544024294424785, -0.003560515032204359)          # v7's fitted three-quarter camera
TGT34, W34, H34 = Vector((-0.764, -0.55, 1.45)), 508, 495


def uv34(w):
    az, el, dist, lens, sx, sy = CAM34
    loc = TGT34 + dist * Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
    fwd = (TGT34 - loc).normalized()
    right = fwd.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(fwd)
    rel = Vector(w) - loc
    z = rel.dot(fwd)
    k = lens / 36.0 * W34
    return W34 / 2 + (rel.dot(right) / z + sx * 36.0 / lens) * k, H34 / 2 - (rel.dot(up) / z + sy * 36.0 / lens) * k


def front_uv(w):
    return FRONT_CAM[0] + FRONT_CAM[2] * w.x, FRONT_CAM[1] - FRONT_CAM[2] * w.z


def side_uv(w):
    return SIDE_CAM[0] + SIDE_CAM[2] * w.y, SIDE_CAM[1] - SIDE_CAM[2] * w.z


# ---------------------------------------------------------------------------
# Lower jaw: a skeletal, asymmetric U solved from the sheet (jaw-local: hinge at the origin, chin -Y)
# ---------------------------------------------------------------------------
RIM_W = 0.105                     # width of the bony rim (the bar seen in the side view)
RIM_TOP, RIM_BOT = 0.040, -0.100  # its top (gum side) and underside, jaw-local z
JAW = {}                          # solved: "L" chin distance, "left"/"right" inner-edge tables, "path"


def _fit_jaw_pose(F):
    """Opening angle and length so the chin's lowest point lands on the side panel's chin."""
    tu, tv = SHEET["side_chin"]
    best = None
    for od in np.arange(62.0, 80.01, 0.25):
        F.set_jaw(od, F.roll_deg)
        for L in np.arange(1.05, 1.45, 0.005):
            u, v = side_uv(F.jw((0.0, -L, RIM_BOT)))
            e = (u - tu) ** 2 + (v - tv) ** 2
            if best is None or e < best[0]:
                best = (e, od, L)
    F.set_jaw(best[1], F.roll_deg)
    return best[1], best[2]


def _front_map(F, v_sheet):
    """Sheet front-panel v in the mouth -> model front-view v (gum line to chin, linear)."""
    vg = front_uv(F.hw((0.0, FRONT_UP, GUM_Z)))[1]
    vc = front_uv(F.jw((JAW["chin_x"], -JAW["L"], RIM_BOT)))[1]
    return vg + (v_sheet - SHEET_FRONT_GUM_V) * (vc - vg) / (SHEET_FRONT_CHIN_V - SHEET_FRONT_GUM_V)


def _solve_edge(F, pts, side):
    """The jaw's inner rim edge on one side, from the front panel's mouth outline: for each outline
    point, the jaw-local y whose rim top projects to its (mapped) height, and the x that projects to
    its horizontal position."""
    out = []
    for us, vs in pts:
        vm = _front_map(F, vs)
        x = side * 0.32
        lo_, hi_ = -JAW["L"] - 0.05, 0.10
        vlo, vhi = front_uv(F.jw((x, lo_, RIM_TOP)))[1], front_uv(F.jw((x, hi_, RIM_TOP)))[1]
        if not (min(vlo, vhi) <= vm <= max(vlo, vhi)):
            continue                                   # above the hinge: the cheek, not the jaw
        for _ in range(3):
            a, b = lo_, hi_
            for _ in range(40):
                m = 0.5 * (a + b)
                vmid = front_uv(F.jw((x, m, RIM_TOP)))[1]
                if (vmid > vm) == (vlo > vm):
                    a = m
                else:
                    b = m
            y = 0.5 * (a + b)
            xw_target = (us - FRONT_CAM[0]) / FRONT_CAM[2]
            w0, w1 = F.jw((x, y, RIM_TOP)).x, F.jw((x + 0.1, y, RIM_TOP)).x
            x = x + (xw_target - w0) * 0.1 / (w1 - w0)
        out.append((y, x))
    return sorted(out)


def solve_jaw(F):
    """Fit the jaw: pose from the side panel's chin, plan shape from the front panel's mouth outline."""
    od, L = _fit_jaw_pose(F)
    JAW["open"], JAW["L"] = od, L
    JAW["chin_x"] = -0.10
    left = _solve_edge(F, SHEET["front_mouth_right"], +1)     # sheet's image right = the monster's left (+x)
    right = _solve_edge(F, SHEET["front_mouth_left"], -1)
    JAW["left"], JAW["right"] = left, right
    # chin x: where the two edges meet at the front
    JAW["chin_x"] = 0.5 * (left[0][1] + right[0][1]) if left and right else -0.10
    # rim centre line, rear left -> chin -> rear right; the inner edges pushed out by half a rim
    def side_pts(edge, s):
        ys = [y for y, _ in edge]
        xs = [x for _, x in edge]
        rear = [(xs[-1] + s * 0.02, 0.06)] if ys[-1] < 0.0 else []
        return [(x + s * RIM_W / 2, y) for y, x in edge if y > -L + 0.22] + [(x + s * RIM_W / 2, y) for x, y in rear]
    lp = side_pts(left, 1)[::-1]                               # rear -> front
    rp = side_pts(right, -1)
    cx = JAW["chin_x"]
    xl, yl = lp[-1]
    xr, yr = rp[0]
    yc = -L + RIM_W / 2 + 0.01                                 # the chin's rim centre line at the front
    arc = []
    for a in np.linspace(0.0, math.pi, 13)[1:-1]:              # an uneven arc through the off-centre chin
        c = math.cos(a)
        x = cx + (xl - cx) * c if c >= 0 else cx + (cx - xr) * c
        y0 = yl + (yr - yl) * a / math.pi
        arc.append((x, y0 + (yc - y0) * math.sin(a)))
    pts = np.array(lp + arc + rp, float)
    seg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    JAW["path"] = np.c_[pts, seg / seg[-1]]
    return JAW


def jaw_path():
    return JAW["path"]


def _rim_params(t, x, y):
    """Rim width, top and underside at path parameter t (0..1, chin near 0.5): uneven along the jaw
    (the left rim dips where it is broken, the chin is thicker, the rear rises toward the hinge)."""
    t = np.asarray(t, float)
    f = 1.0 - np.abs(t - 0.5) * 2.0
    w = RIM_W * (1.0 + 0.10 * np.sin(9.0 * t + 1.0) + 0.12 * f)
    top = RIM_TOP + 0.012 * np.sin(13.0 * t) - 0.030 * np.exp(-((t - 0.30) / 0.06) ** 2)
    bot = RIM_BOT - 0.025 * f - 0.012 * np.sin(7.0 * t + 2.0)
    return w, top, bot


def jaw_sdf(G):
    P = jaw_path()
    X, Y = G.X, G.Y
    best = np.full(X.shape, 9.0, np.float32)
    tb = np.zeros(X.shape, np.float32)
    for (ax_, ay, ta), (bx, by, tb_) in zip(P[:-1], P[1:]):
        ex, ey = bx - ax_, by - ay
        L2 = ex * ex + ey * ey
        t = np.clip(((X - ax_) * ex + (Y - ay) * ey) / L2, 0, 1)
        d = np.sqrt((X - ax_ - t * ex) ** 2 + (Y - ay - t * ey) ** 2)
        closer = d < best
        best = np.where(closer, d, best)
        tb = np.where(closer, ta + t * (tb_ - ta), tb)
    w, top, bot = _rim_params(tb, X, Y)
    rim = np.maximum(np.maximum(best - w / 2, G.Z - top), bot - G.Z).astype(np.float32)
    F = rim
    ends = (P[0], P[-1])
    for (ex_, ey_, _), s in zip(ends, (1, -1)):            # rami rising to the torn-out condyles
        F = B.union(F, B.box(G, (ex_, ey_ + 0.01, -0.02), (0.055, 0.06, 0.10), B.rot(0, s * 6, 0)))
    for c, h, r in JAW_CHUNKS:
        F = B.union(F, B.inter(B.box(G, c, h, B.rot(*r)), rim - 0.04))
    for c, h, r in JAW_NOTCHES:
        F = B.sub(F, B.box(G, c, h, B.rot(*r)))
    return F


# breaks in the jaw (jaw-local; placed relative to the solved outline in build_jaw)
JAW_NOTCHES = []
JAW_CHUNKS = []


def _jaw_breaks():
    """Damage placed on the solved jaw: the chin's right corner broken off, the left rim broken down,
    chips out of the underside, a blocky lump on the right side."""
    P = jaw_path()
    at = lambda t: _path_at(P, t)
    out_n, out_c = [], []
    x, y, _, n = at(0.62)                                     # chin's right corner
    out_n.append(((x - 0.02, y - 0.03, 0.02), (0.07, 0.06, 0.05), (0, 0, 20)))
    x, y, _, n = at(0.30)                                     # left rim broken down
    out_n.append(((x - n[0] * 0.02, y, 0.05), (0.05, 0.09, 0.04), (0, 0, 0)))
    for t, dz in ((0.18, -0.12), (0.44, -0.13), (0.78, -0.12)):
        x, y, _, n = at(t)
        out_n.append(((x - n[0] * 0.04, y - n[1] * 0.04, dz), (0.05, 0.06, 0.04), (0, 0, 10)))
    x, y, _, n = at(0.80)                                     # lump on the right side
    out_c.append(((x - n[0] * 0.05, y - n[1] * 0.05, -0.03), (0.04, 0.09, 0.06), (0, 0, 4)))
    x, y, _, n = at(0.52)
    out_c.append(((x - n[0] * 0.04, y - n[1] * 0.04, -0.05), (0.05, 0.05, 0.05), (0, 0, 12)))
    return out_n, out_c


def build_jaw(col, M, sk, F):
    global JAW_NOTCHES, JAW_CHUNKS
    JAW_NOTCHES, JAW_CHUNKS = _jaw_breaks()
    P = jaw_path()
    lo = (P[:, 0].min() - 0.15, P[:, 1].min() - 0.12, -0.32)
    hi = (P[:, 0].max() + 0.15, max(P[:, 1].max(), 0.06) + 0.12, 0.20)
    G = B.Grid(lo, hi, 0.009 if not FAST else 0.015)
    Fd = jaw_sdf(G)
    Fd, tid, val, seam, hole = B.tiles(G, Fd, size=0.062, seed=21, shell=0.05, raised=(0.0, 0.018),
                                       sunken=(-0.014, 0.0), p_sunk=0.30, p_missing=0.07, missing=-0.030,
                                       tilt=0.12, seam=0.0055, seam_depth=0.008, wobble=0.012)
    jaw = B.to_object("Jaw", Fd, G, col, [M["rust"]])
    S = SC.Surf(jaw, U)
    co = S.co / U
    S.a["flake"] = B.sample(G, val, co) ** 2.0
    S.a["crack"] = np.clip(B.sample(G, seam, co) * 1.4, 0, 1)
    S.a["pit"] = B.sample(G, hole, co)
    S.a["socket"] = np.zeros(S.n)
    S.a_socket_final = S.a["socket"]
    if not FAST:
        rot = Matrix.Rotation(math.radians(F.open_deg), 3, 'X')
        SC.blood(S, 76, drips=6, near=0.03, down=tuple(rot.inverted() @ Vector((0, 0, -1))))
    SC.finish(S, jaw, decimate_ratio=1.0, sharp_deg=30.0)
    jaw.parent = sk
    jaw.matrix_parent_inverse = Matrix.Identity(4)
    jaw.location = HINGE + DISLOCATE
    jaw.rotation_euler = (math.radians(F.open_deg), math.radians(-F.roll_deg), math.radians(1.5))
    bpy.context.view_layer.update()
    return jaw


# ---------------------------------------------------------------------------
# Teeth: slender, uneven fangs placed where the sheet shows them
# ---------------------------------------------------------------------------
def tusk(bm, layer, base, direction, length, width, kind, curl_dir=None, curl_amt=None, sides=9):
    """Organic fang: a full root tapering to a sharp point along a gentle curve toward `curl_dir`,
    slightly flattened and twisted; 'snapped' teeth end in a tilted fracture.
    Colour attribute: (t root->tip, blood, decay, tint)."""
    d = Vector(direction).normalized()
    side = Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, d) @ d.orthogonal().normalized()
    fwd = d.cross(side).normalized()
    depth = width * rng.uniform(0.78, 0.92)
    n = sides
    prof = [(math.cos(2 * math.pi * k / n) * width / 2 * rng.uniform(0.95, 1.05),
             math.sin(2 * math.pi * k / n) * depth / 2 * rng.uniform(0.95, 1.05)) for k in range(n)]
    c_dir = Vector(curl_dir) if curl_dir is not None else side
    c_dir = c_dir - d * c_dir.dot(d)
    if c_dir.length < 1e-6:
        c_dir = side
    curl = c_dir.normalized() * length * (curl_amt if curl_amt is not None else rng.uniform(0.05, 0.12))
    cut = rng.uniform(0.62, 0.82) if kind == "snapped" else 1.0
    ts = [-0.16, 0.0, 0.10, 0.22, 0.36, 0.50, 0.64, 0.77, 0.88, 0.95]
    # the sheet's fangs are cigar-shaped: full through the lower half, then tapering to a sharp point
    rad = lambda t: TOOTH_RAD(max(t, 0.0)) * (1.0 + 0.05 * math.sin(math.pi * min(max(t, 0.0) / 0.35, 1.0)))
    ts = [t for t in ts if t < cut - 0.02] + ([cut] if cut < 1.0 else [])
    blood = min(1.0, rng.choice([0.0, 0.0, 0.0, 0.2, 0.3]) * rng.uniform(0.7, 1.2))
    decay, tint = rng.random() ** 1.6, rng.random()
    twist = rng.uniform(-0.3, 0.3)
    rings = []
    for t in ts:
        c = Vector(base) + d * length * t + curl * max(t, 0.0) ** 2
        sc = rad(t) if t >= 0 else 0.97
        a = twist * max(t, 0.0)
        rings.append([c + side * (x * math.cos(a) - y * math.sin(a)) * sc + fwd * (x * math.sin(a) + y * math.cos(a)) * sc
                      for x, y in prof])
    if cut < 1.0:
        tilt = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)).normalized()
        c = Vector(base) + d * length * cut + curl * cut ** 2
        rings[-1] = [p + d * (p - c).dot(tilt) * rng.uniform(0.4, 0.8) for p in rings[-1]]
    verts = []
    for t, ring in zip(ts, rings):
        row = []
        for p in ring:
            v = bm.verts.new(p)
            v[layer] = (max(t, 0.0), blood, decay, tint)
            row.append(v)
        verts.append(row)
    for ra, rb in zip(verts, verts[1:]):
        for i in range(n):
            bm.faces.new((ra[i], ra[(i + 1) % n], rb[(i + 1) % n], rb[i]))
    bm.faces.new(list(reversed(verts[0])))
    if cut < 1.0:
        bm.faces.new(verts[-1])
        return
    a = bm.verts.new(Vector(base) + d * length + curl)
    a[layer] = (1.0, blood, decay, tint)
    for i in range(n):
        bm.faces.new((verts[-1][i], verts[-1][(i + 1) % n], a))


UP_LEN_K, LO_LEN_K = 1.40, 1.40           # front-panel tooth lengths -> model (side 1.4x, 3/4 1.2x, front mapping 1.32x)
LO_FWD_MAX = 0.18                         # lower teeth: forward reach at most the side panel's fan (0.13-0.20 m)


def _lower_lean(f, rise):
    """Forward lean (forward / rise) of a lower tooth; f = 0 at the hinge end, 1 at the chin, rise in m.
    The side panel's fan leans forward at the chin and steepens up the jaw; the front and three-quarter
    panels show the tall teeth behind the chin standing upright. So the short teeth at the chin point
    forward, the tall ones stand up."""
    return (0.15 + 0.85 * f * f) * min(max((0.46 - rise) / 0.22, 0.5), 1.6)


FRONT_UP = FACE_Y + 0.065                 # the upper gum line just behind the face plate...
UP_LEFT_X, UP_RIGHT_X = 0.29, -0.43       # ...and along the sides of the (off-centre) mouth


def gum_front(x):
    """The upper jaw's broken lower edge across the front: (y, z) at x (cranium-local)."""
    return float(face_y(x)) + 0.065, GUM_Z - 0.008 + 0.012 * math.sin(11.0 * x + 1.0)


def _path_at(P, t):
    """Point, unit tangent and inward normal (toward the U's inside) on the jaw path at parameter t."""
    i = int(np.clip(np.searchsorted(P[:, 2], t) - 1, 0, len(P) - 2))
    a, b = P[i], P[i + 1]
    f = (t - a[2]) / max(b[2] - a[2], 1e-9)
    x, y = a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])
    tx, ty = b[0] - a[0], b[1] - a[1]
    L = math.hypot(tx, ty)
    tx, ty = tx / L, ty / L
    return x, y, (tx, ty), (ty, -tx)


def _rim_point(P, t, inward=0.02, dz=0.0):
    x, y, tan, n = _path_at(P, t)
    _, top, _ = _rim_params(t, x, y)
    return Vector((x + n[0] * inward, y + n[1] * inward, float(top) + dz)), n


def _tooth_width(L, lower=False):
    """Root width (head units): cigar-shaped fangs that stay full through their lower half. The
    sheet's fangs measure 3-5 cm in the front panel, whose mouth is drawn 1.3 times shorter than the
    model's (see SHEET); the crowded lower teeth get proportionally more width to read alike
    (5-6.5 cm), the upper row 4-6 cm."""
    if lower:
        return (0.060 + 0.060 * L) * rng.uniform(0.88, 1.12)
    return (0.050 + 0.055 * L) * rng.uniform(0.88, 1.12)


def _stagger_rows(teeth, back=0.036, front=0.032):
    """Where the bundle is crowded (roots closer than the teeth are wide), the teeth stand in two rows
    on the gum. Which row comes from the front panel: a root that reads higher there sits further
    back on the rim (the jaw hangs open, so 'back' is 'up' in that view); teeth not read off the
    front panel alternate."""
    g = sorted(teeth, key=lambda t: t["t"])
    crowded = [any((g[i]["root"] - g[j]["root"]).length < 0.5 * (g[i]["w"] + g[j]["w"])
                   for j in (i - 1, i + 1) if 0 <= j < len(g)) for i in range(len(g))]
    read = [t["rv"] for t, c in zip(g, crowded) if c and "rv" in t]
    med = sorted(read)[len(read) // 2] if read else 0.0
    for i, t in enumerate(g):
        if not crowded[i]:
            continue
        is_back = (t["rv"] < med) if "rv" in t else (i % 2 == 0)
        nv = Vector((t["n"][0], t["n"][1], 0.0))
        off = back if is_back else -front
        t["root"], t["tip"] = t["root"] + nv * off, t["tip"] + nv * off


def _spread_on_rim(P, teeth, gap=0.042):
    """Roots read off the front panel crowd closer than the teeth are wide where the sheet's bundle
    overlaps: spread them along the rim to at least `gap` apart (order kept, a few mm each), the tip
    moving with the root."""
    xy = P[:, :2]
    total = float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))
    g = sorted(teeth, key=lambda t: t["t"])
    s_ = [t["t"] * total for t in g]
    for _ in range(60):
        for i in range(len(g) - 1):
            d = s_[i + 1] - s_[i]
            if d < gap:
                s_[i] -= 0.5 * (gap - d)
                s_[i + 1] += 0.5 * (gap - d)
    for t, si in zip(g, s_):
        tn = float(np.clip(si / total, 0.02, 0.98))
        root, n = _rim_point(P, tn)
        root.z = t["root"].z
        shift = root - t["root"]
        t["root"], t["tip"], t["t"], t["n"] = t["root"] + shift, t["tip"] + shift, tn, n


TOOTH_RAD = lambda t: (1.0 - t ** 1.5) ** 0.72         # the fangs' cigar profile (radius / root radius)
T_VISIBLE = 0.15                                       # the part of a tooth (root -> tip) above the gum


def _overlap(a, b, n=14):
    """Deepest interpenetration of two teeth's visible parts (> 0: they intersect), with the axis
    points where it happens (on a, on b) and a's parameter there."""
    best = (-9.0, None, None, 0.0)
    ts = np.linspace(T_VISIBLE, 0.95, n)
    da, db = a["tip"] - a["root"], b["tip"] - b["root"]
    pb = [(b["root"] + db * tb, 0.53 * b["w"] * TOOTH_RAD(tb)) for tb in ts]      # +6%: the profile's swell
    for ta in ts:
        p = a["root"] + da * ta
        ra = 0.53 * a["w"] * TOOTH_RAD(ta)
        for q, rb in pb:
            o = ra + rb - (p - q).length
            if o > best[0]:
                best = (o, p, q, ta)
    return best


def _separate(teeth, iters=120, max_move=0.15, max_slide=0.04, tol=0.002, view=None):
    """Teeth must never pass through each other. For each pair whose visible parts (above the gum)
    intersect, the shorter tooth is moved, in this order of preference:
    - where they meet near the roots: the roots are staggered on the gum (the taller behind) or slid
      apart along the rim, at most `max_slide`;
    - otherwise its tip is moved away, at most `max_move` in all: rotated about the root, or, given
      the front view's line of sight `view`, shifted mostly along it so the front panel's reading
      holds;
    - where roots stay crowded at the gum line, the teeth are made a little slimmer (to 60%).
    So they crowd and overlap in view without intersecting. Returns the deepest remaining
    interpenetration (head units)."""
    for t in teeth:
        t["moved"], t["slid"] = 0.0, 0.0
    worst = 0.0
    for _ in range(iters):
        worst = 0.0
        for i in range(len(teeth)):
            for j in range(i + 1, len(teeth)):
                a, b = teeth[i], teeth[j]
                if (a["root"] - b["root"]).length > 0.5 * (a["L"] + b["L"]) + a["w"] + b["w"]:
                    continue
                o = _overlap(a, b)[0]
                if o <= tol:
                    continue
                worst = max(worst, o)
                m, o_ = (a, b) if a["L"] < b["L"] else (b, a)
                if m["moved"] >= max_move:
                    m, o_ = o_, m
                    if m["moved"] >= max_move:
                        continue
                om, pm, qm, tm = _overlap(m, o_)
                if (tm < 0.4 or m["moved"] >= max_move) and any("n" in t and t["slid"] < max_slide for t in (m, o_)):
                    # roots crowded closer than the teeth are wide: stagger them on the gum (the taller
                    # tooth behind, the shorter in front) or slide them apart along the rim, whichever
                    # parts the roots most
                    s_ = m if ("n" in m and m["slid"] < max_slide) else o_
                    r_ = o_ if s_ is m else m
                    nv = Vector((s_["n"][0], s_["n"][1], 0.0))
                    tv = Vector((-s_["n"][1], s_["n"][0], 0.0))
                    back = nv if s_["L"] >= r_["L"] else -nv
                    step = min(om + 0.003, 0.012, max_slide - s_["slid"])
                    v = max((back, -back * 0.7, tv, -tv), key=lambda c: (s_["root"] + c * step - r_["root"]).length
                            + (0.004 if c is back else 0.0))
                    s_["root"] = s_["root"] + v * step
                    s_["tip"] = s_["tip"] + v * step
                    s_["slid"] += step
                    continue
                axm = m["tip"] - m["root"]
                L = axm.length
                um = axm.normalized()
                away = pm - qm
                away = away - um * away.dot(um)
                if away.length < 1e-6:
                    away = um.orthogonal()
                step = min((om + 0.004) / max(tm, 0.25), 0.03, max_move - m["moved"])
                if view is not None:
                    # move the tip mostly along the front view's line of sight (the front panel's
                    # reading holds; the tooth leans a little more or less in depth)
                    sv = view * (1.0 if view.dot(away) >= 0 else -1.0)
                    m["tip"] = m["tip"] + (sv * 0.8 + away.normalized() * 0.2).normalized() * step
                    m["L"] = (m["tip"] - m["root"]).length
                else:
                    m["tip"] = m["root"] + ((m["tip"] + away.normalized() * step) - m["root"]).normalized() * L
                m["moved"] += step
        if worst <= tol:
            break
    # last resort, where roots stay crowded at the gum line: the teeth are made a little slimmer
    worst = 0.0
    for i in range(len(teeth)):
        for j in range(i + 1, len(teeth)):
            a, b = teeth[i], teeth[j]
            for _ in range(12):
                if _overlap(a, b)[0] <= tol:
                    break
                for m in sorted((a, b), key=lambda t: t["L"]):
                    if m["w"] > 0.6 * m.setdefault("w0", m["w"]):
                        m["w"] = max(m["w"] * 0.93, 0.6 * m["w0"])
                        break
            worst = max(worst, _overlap(a, b)[0])
    return worst


def plan_teeth(F):
    """All teeth from the sheet: upper front row from the front panel, upper side teeth from the
    side panel, lower teeth from the front panel (roots found on the solved jaw rim) and the side
    panel's fan (near side). Returns (upper, lower) in cranium- and jaw-local space."""
    rng.seed(1111)                      # the same plan in the build and in v11_anatomy_check.py
    up, lo = [], []
    # --- upper front row (front panel)
    xs = np.linspace(UP_RIGHT_X - 0.03, UP_LEFT_X, 300)
    arc = [(x,) + gum_front(x) for x in xs]
    arc_u = np.array([front_uv(F.hw(p))[0] for p in arc])
    for (ru, rv), (tu, tvv) in SHEET["front_upper"]:
        i = int(np.argmin(np.abs(arc_u - ru)))
        root = Vector(arc[i])
        rw = F.hw(root)
        drop = (tvv - rv) / FRONT_CAM[2] * UP_LEN_K                # visible length below the gum (m)
        tw = Vector(((tu - FRONT_CAM[0]) / FRONT_CAM[2], rw.y + 0.08 * drop, rw.z - drop))
        tip = F.wh(tw)
        L = (tip - root).length + 0.03
        up.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L), "src": "front"})
    # --- upper side teeth behind the left corner (side panel; the near side), and two on the right
    # behind the corners: the side panel's long teeth hang from the far (right) side - the front panel
    # shows only short teeth at the near (left) corner, and long ones behind the right corner
    for (ru, rv), (tu, tvv) in SHEET["side_upper"]:
        if ru < 109:
            continue                                         # the front row, already placed
        far = (tvv - rv) > 30
        x_side = UP_RIGHT_X if far else UP_LEFT_X
        yw, zw = (ru - SIDE_CAM[0]) / SIDE_CAM[2], (SIDE_CAM[1] - rv) / SIDE_CAM[2]
        root = F.wh(Vector((F.hw((x_side, -0.3, 0.0)).x, yw, zw)))
        root = Vector((x_side, root.y + (0.10 if far else 0.0), GUM_Z - 0.006))
        rw = F.hw(root)
        tw = Vector((rw.x + (0.015 if far else -0.012), rw.y + (tu - ru) / SIDE_CAM[2], rw.z - (tvv - rv) / SIDE_CAM[2]))
        tip = F.wh(tw)
        L = (tip - root).length + 0.03
        up.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L), "src": "far" if far else "side"})
    root = Vector((UP_LEFT_X, -0.44, GUM_Z - 0.006))          # one more short tooth at the left corner
    tip = root + Vector((-0.02, 0.03, -0.20))
    up.append({"root": root, "tip": tip, "L": 0.23, "w": _tooth_width(0.2), "src": "side"})
    # --- lower teeth from the front panel: roots on the jaw rim where they project
    P = jaw_path()
    ts = np.linspace(0.02, 0.98, 400)
    rim = [_rim_point(P, t) for t in ts]
    rim_uv = np.array([front_uv(F.jw(p)) for p, _ in rim])
    for (ru, rv), (tu, tvv) in SHEET["front_lower"]:
        vm = _front_map(F, rv)
        i = int(np.argmin((rim_uv[:, 0] - ru) ** 2 + (rim_uv[:, 1] - vm) ** 2))
        t = float(ts[i])
        root, n = rim[i]
        rw = F.jw(root)
        rise = (rv - tvv) / FRONT_CAM[2] * LO_LEN_K               # the front panel's height (m), scaled
        f = 1.0 - abs(t - 0.5) * 2.0                              # 0 at the hinge end, 1 at the chin
        lean = _lower_lean(f, rise)
        tw = Vector((rw.x + (tu - ru) / FRONT_CAM[2], rw.y - min(lean * rise, LO_FWD_MAX), rw.z + rise))
        tip = F.wj(tw)
        L = (tip - root).length + 0.03
        lo.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L, True), "t": t, "src": "front", "n": n, "rv": rv})
    _spread_on_rim(P, lo)
    # --- lower teeth from the side panel's fan (near side, +x), where the front panel shows none
    near = [k for k in range(len(ts)) if ts[k] <= 0.5]
    side_uv_rim = np.array([side_uv(F.jw(rim[k][0])) for k in near])
    for (ru, rv), (tu, tvv) in SHEET["side_lower"]:
        k = near[int(np.argmin((side_uv_rim[:, 0] - ru) ** 2 + (side_uv_rim[:, 1] - rv) ** 2))]
        root, n = rim[k]
        if min((root - o["root"]).length for o in lo) < 0.06:
            continue
        rw = F.jw(root)
        tw = Vector((rw.x + 0.02 * 0.6, (tu - SIDE_CAM[0]) / SIDE_CAM[2], (SIDE_CAM[1] - tvv) / SIDE_CAM[2]))
        tip = F.wj(tw)
        L = (tip - root).length + 0.03
        lo.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L, True), "t": float(ts[k]), "src": "side", "n": n})
    # --- more lower teeth where the three-quarter panel shows them (its mouth mapped onto the model's)
    g34 = uv34(F.hw((0.0, FRONT_UP, GUM_Z)))[1]
    c34 = uv34(F.jw((JAW["chin_x"], -JAW["L"], RIM_BOT)))[1]
    k34 = (c34 - g34) / (SHEET["34_chin_v"] - SHEET["34_gum_v"])
    rim34 = np.array([uv34(F.jw(p)) for p, _ in rim])
    for (ru, rv), (tu, tvv) in SHEET["34_lower"]:
        vm = g34 + (rv - SHEET["34_gum_v"]) * k34
        i = int(np.argmin((rim34[:, 0] - ru) ** 2 + (rim34[:, 1] - vm) ** 2))
        root, n = rim[i]
        if min((root - o["root"]).length for o in lo) < 0.06:    # the same tooth as one already placed
            continue
        t = float(ts[i])
        rw = F.jw(root)
        rise = (rv - tvv) / 155.0                                 # 3/4 panel: about 155 px per metre
        f = 1.0 - abs(t - 0.5) * 2.0
        tw = Vector((rw.x + (tu - ru) / 155.0 / 0.91, rw.y - min(_lower_lean(f, rise) * rise, LO_FWD_MAX), rw.z + rise))
        tip = F.wj(tw)
        L = (tip - root).length + 0.03
        lo.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L, True), "t": t, "src": "34", "n": n})
    _stagger_rows(lo)
    # upper teeth: turned apart about their roots; lower teeth (the crowded bundle): moved mostly along
    # the front view's line of sight, in jaw-local space, so the front panel's reading holds
    rot = lambda M: M.to_3x3().normalized()
    v_lo = (rot(F.Ji) @ (rot(F.Ci) @ Vector((0.0, 1.0, 0.0)))).normalized()
    rest = (_separate(up), _separate(lo, view=v_lo))
    print("TEETH remaining interpenetration (head units): upper %.3f, lower %.3f" % rest)
    # a few teeth snapped (the shortest ones), as on the sheet
    for group in (up, lo):
        for tth in sorted(group, key=lambda d: d["L"])[:2]:
            tth["kind"] = "snapped"
    return up, lo


def gums_and_teeth(M, col, sk, jaw, F):
    up, lo = plan_teeth(F)
    print("TEETH upper %d (front %d, side %d, far %d) lower %d (front %d, side %d, three-quarter %d)" % (
        len(up), sum(t["src"] == "front" for t in up), sum(t["src"] == "side" for t in up),
        sum(t["src"] == "far" for t in up), len(lo), sum(t["src"] == "front" for t in lo),
        sum(t["src"] == "side" for t in lo), sum(t["src"] == "34" for t in lo)))
    for group, parent, name, curl in ((up, sk, "Teeth_Upper", (0, 1, 0.2)), (lo, jaw, "Teeth_Lower", (0, 0.8, -0.3))):
        bm, layer = D.new_tooth_bm()
        for tth in group:
            d = tth["tip"] - tth["root"]
            Lb = d.length
            base = tth["root"] - d.normalized() * 0.03                 # root set into the gum
            tusk(bm, layer, base, d, Lb + 0.03, tth["w"], tth.get("kind", "fang"), curl_dir=curl,
                 curl_amt=rng.uniform(0.04, 0.11))
        D.bm_object(name, bm, col, [M["teeth"]], parent=parent)

    def lobed(path, roots, r0, r1):
        out = []
        for p in path:
            near = min((p - b).length for b in roots)
            out.append(rng.uniform(r0, r0 + 0.008) + r1 * math.exp(-(near / 0.045) ** 2))
        return out

    up_path = ([Vector((UP_RIGHT_X + 0.01, y, GUM_Z - 0.004)) for y in np.linspace(-0.12, -0.42, 6)] +
               [Vector((x,) + gum_front(x)) + Vector((0, 0.008, -0.004)) for x in np.linspace(UP_RIGHT_X, UP_LEFT_X, 18)] +
               [Vector((UP_LEFT_X + 0.01, y, GUM_Z - 0.004)) for y in np.linspace(-0.50, -0.10, 7)])
    gb = bmesh.new()
    D.tube(gb, up_path, lobed(up_path, [t["root"] for t in up], 0.030, 0.022), 0, sides=9, jitter=0.20,
           frame_ref=(0, 0, 1))
    D.bm_object("Gums_Upper", gb, col, [M["tissue"]], parent=sk)
    P = jaw_path()
    lo_path = [_rim_point(P, t, inward=0.012, dz=0.004)[0] for t in np.linspace(0.04, 0.96, 50)]
    gb = bmesh.new()
    D.tube(gb, lo_path, lobed(lo_path, [t["root"] for t in lo], 0.052, 0.024), 0, sides=9, jitter=0.20,
           frame_ref=(0, 0, 1))
    D.bm_object("Gums_Lower", gb, col, [M["tissue"]], parent=jaw)
    return up, lo


# ---------------------------------------------------------------------------
# Flesh: the cheeks torn open at the gape (red bands down the mouth's sides), the tongue, strands,
# the torn skull sides, palate and throat
# ---------------------------------------------------------------------------
def _sheet(bm, grid, holes=0.0, seed=0, edge_tear=0.0):
    r = random.Random(seed)
    rows, cols = len(grid), len(grid[0])
    vs = [[bm.verts.new(p) for p in row] for row in grid]
    for i in range(rows - 1):
        for j in range(cols - 1):
            u = i / (rows - 2)
            if 0 < j < cols - 2 and r.random() < holes:
                continue
            if u > 1.0 - edge_tear and 0 < j < cols - 2 and r.random() < 0.6:
                continue
            bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))


def mouth_flesh(M, col, sk, jaw, F):
    jm = F.J
    P = jaw_path()
    wb = bmesh.new()                                         # torn cheek flesh at the gape's corners: a few
    for s, x_up, t0 in ((1, UP_LEFT_X, 0.03), (-1, UP_RIGHT_X, 0.97)):     # thick bands, upper jaw -> rim
        for k, (ty, dt, r0) in enumerate(((0.26, 0.00, 0.05), (0.14, 0.05, 0.04), (0.02, 0.10, 0.032))):
            a = Vector((x_up + s * 0.02, ty, GUM_Z - 0.01))
            p, n = _rim_point(P, t0 + dt if s > 0 else t0 - dt, inward=0.0, dz=-0.01)
            b = jm @ p
            pts = []
            for i in range(8):
                f = i / 7
                if k == 2 and f > 0.7:
                    break                                       # torn through
                pts.append(a.lerp(b, f) + Vector((s * 0.04 * math.sin(math.pi * f), rng.uniform(-0.012, 0.012),
                                                  -0.03 * math.sin(math.pi * f))))
            D.tube(wb, pts, [r0 * (1.0 + 0.35 * math.sin(math.pi * i / 7)) * rng.uniform(0.8, 1.2)
                             for i in range(len(pts))], 0, sides=8, jitter=0.3)
    D.bm_object("Mouth_Cheek_Flesh", wb, col, [M["tissue"]], parent=sk)
    ib = bmesh.new()                                         # dark inner cheek walls, set back in the mouth: the
    for s, x_up, t0, t1 in ((1, UP_LEFT_X, 0.02, 0.20), (-1, UP_RIGHT_X, 0.98, 0.60)):   # far (right) side spans
        grid = []                                                                        # the gape, the near side
        for u in np.linspace(0.0, 1.0, 12):                                              # only its rear: the mouth
            ty = 0.32 - u * (0.34 if s > 0 else 0.86)                                    # reads dark, never hollow
            top = Vector((x_up - s * 0.05, ty, GUM_Z + 0.02))
            p, n = _rim_point(P, t0 + (t1 - t0) * u, inward=0.06, dz=-0.03)
            bot = jm @ p
            grid.append([top.lerp(bot, v) + Vector((-s * 0.04 * math.sin(math.pi * v), 0.0, 0.0))
                         for v in np.linspace(0.0, 1.0, 8)])
        _sheet(ib, grid, seed=51 + s)
    walls = D.bm_object("Mouth_Inner_Walls", ib, col, [M["tissue"]], parent=sk)
    sol = walls.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.015
    D.apply_modifiers(walls)
    fb = bmesh.new()                                         # the mouth's floor: dark tissue, set down inside the U
                                                             # (the sheet's gaps between the teeth are dark brown-
                                                             # maroon, about 0.15 bright - not black)
    grid = []
    for y in np.linspace(0.02, -JAW["L"] + 0.14, 14):
        tl = float(np.interp(y, P[:len(P) // 2, 1][::-1], P[:len(P) // 2, 2][::-1]))
        xl = _path_at(P, tl)[0] - 0.05
        xr = _path_at(P, 1.0 - tl)[0] + 0.05
        grid.append([Vector((xr + (xl - xr) * v, y, RIM_BOT + 0.02 - 0.05 * math.sin(math.pi * v)))
                     for v in np.linspace(0.0, 1.0, 9)])
    _sheet(fb, grid, seed=41)
    D.bm_object("Mouth_Floor", fb, col, [M["tissue"]], parent=jaw)
    tb = bmesh.new()                                         # red flesh in the torn skull sides
    for (cx, cy, cz), (hx, hy, hz), _ in TEARS:
        s = 1.0 if cx > 0 else -1.0
        back = cx - s * hx * 1.15
        grid = [[Vector((back + s * 0.02 * math.sin(7 * v + 3 * u), cy + (u - 0.5) * 2 * hy * 1.05,
                         cz + (v - 0.5) * 2 * hz * 1.05)) for v in np.linspace(0, 1, 7)] for u in np.linspace(0, 1, 9)]
        _sheet(tb, grid, seed=int(cy * 100) + 7)
        for k in range(max(3, int(hy * 22))):
            yy = cy + rng.uniform(-0.85, 0.85) * hy
            x0 = back + s * rng.uniform(0.02, 0.06)
            pts = [Vector((x0 + s * 0.03 * math.sin(math.pi * f), yy + rng.uniform(-0.015, 0.015),
                           cz + hz * (1.0 - 2.0 * f))) for f in np.linspace(0, 1, 6)]
            if rng.random() < 0.35:
                pts = pts[:rng.randint(2, 4)]
            D.tube(tb, pts, [rng.uniform(0.012, 0.026)] * len(pts), 0, sides=6, jitter=0.35)
    D.bm_object("Torn_Flesh", tb, col, [M["tissue"]], parent=sk)
    sb = bmesh.new()                                         # thin strands across the gape's corners
    for s, x_up, ts_ in ((1, UP_LEFT_X, (0.06, 0.13, 0.20)), (-1, UP_RIGHT_X, (0.94, 0.88, 0.82))):
        for k, (ty, t) in enumerate(zip((0.18, 0.02, -0.14), ts_)):
            a = Vector((x_up - s * 0.03, ty, GUM_Z - 0.01))
            p, n = _rim_point(P, t, inward=0.05, dz=0.02)
            b = jm @ p
            pts = []
            for i in range(7):
                f = i / 6
                if k == 2 and s > 0 and f > 0.6:
                    break
                pts.append(a.lerp(b, f) + Vector((-s * 0.03 * math.sin(math.pi * f), rng.uniform(-0.01, 0.01),
                                                  -0.05 * math.sin(math.pi * f))))
            D.tube(sb, pts, [0.014 * (1.0 - 0.35 * math.sin(math.pi * i / 6)) for i in range(len(pts))], 0,
                   sides=6, jitter=0.3)
    D.bm_object("Jaw_Strands", sb, col, [M["tissue"]], parent=sk)
    pb = bmesh.new()                                         # palate ridges (rugae) on the vault
    for i in range(8):
        y = -0.50 + i * 0.075
        hw = 0.25 - i * 0.008
        pts = [Vector((x, y + 0.02 * math.sin(x * 9 + i), GUM_Z + 0.052)) for x in (-hw - 0.06, -hw / 2 - 0.06, -0.06, hw / 2 - 0.06, hw - 0.06)]
        D.tube(pb, pts, [0.012, 0.02, 0.016, 0.02, 0.012], 0, sides=5, jitter=0.25)
    D.bm_object("Palate", pb, col, [M["tissue"]], parent=sk)
    tb = bmesh.new()                                         # ribbed throat receding into the body
    path = [Vector((-0.05, 0.22, -0.08)), Vector((-0.05, 0.36, -0.18)), Vector((-0.05, 0.48, -0.30)),
            Vector((-0.05, 0.56, -0.42))]
    rings = []
    for i, p in enumerate(path):
        for sub_ in range(3):
            if i == len(path) - 1 and sub_:
                break
            q = p if i == len(path) - 1 else p.lerp(path[i + 1], sub_ / 3)
            r = (0.24 - 0.04 * (i + sub_ / 3)) * (1.0 if sub_ % 2 == 0 else 0.86)
            rings.append([q + Vector((math.cos(a) * r, 0, math.sin(a) * r * 0.75)) for a in [2 * math.pi * k / 12 for k in range(12)]])
    rr = [[tb.verts.new(p) for p in ring] for ring in rings]
    for a, b in zip(rr, rr[1:]):
        for k in range(12):
            tb.faces.new((a[k], a[(k + 1) % 12], b[(k + 1) % 12], b[k]))
    tb.faces.new(rr[-1])
    bmesh.ops.reverse_faces(tb, faces=tb.faces)
    D.bm_object("Throat", tb, col, [M["throat"]], parent=sk)


def D_skin(bm, profiles, mat):
    rings = [[bm.verts.new(p) for p in prof] for prof in profiles]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


# ---------------------------------------------------------------------------
# Eyes and the two crown knobs (kept from v9)
# ---------------------------------------------------------------------------
def eyes(M, col, sk):
    ebm = bmesh.new()
    me = sk.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    sock = SC.get_attr(me, "socket") > 0.5
    for ex, ez, k in EYES:
        d = (co[:, 0] - ex) ** 2 + (co[:, 2] - ez - 0.01) ** 2 + 0.2 * (co[:, 1] - (float(face_y(ex)) + 0.12)) ** 2
        d[~sock] = 1e9
        i = int(np.argmin(d))
        c = Vector(co[i]) + Vector((0, -0.008, 0))
        bmesh.ops.create_icosphere(ebm, subdivisions=1, radius=0.0045 / U * k, matrix=Matrix.Translation(c))
    D.bm_object("Eyes", ebm, col, [M["eye"]], parent=sk)


def crown_bracket(col, mat, sk):
    me = sk.data
    co = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    bm = bmesh.new()
    for at, tilt, L in (((0.17, 0.54), (0.20, 0.35, 1.0), 0.09), ((0.36, 0.56), (0.60, 0.45, 0.80), 0.08)):
        d2 = (co[:, 0] - at[0]) ** 2 + (co[:, 1] - at[1]) ** 2
        near = np.flatnonzero(d2 < 0.045 ** 2)
        p = Vector(co[int(near[np.argmax(co[near, 2])]) if len(near) else int(np.argmin(d2))])
        d = Vector(tilt).normalized()
        keys = [{"p": tuple(q), "w": 0.045, "d": 0.028, "e": 7.0} for q in (p - d * 0.12, p, p + d * L)]
        SC.merge_bm(bm, SC.loft(keys, ref=(1, 0, 0), seg=20, step=0.012, caps=(0.008, 0.008)))
    ob = SC.obj_from_bm("Crown_Bracket", bm, col, [mat])
    ob.parent = sk
    SC.remesh(ob, 0.006)
    S = SC.Surf(ob, U)
    SC.warp(S, 0.0015, 9.0, 91)
    SC.finish(S, ob, decimate_ratio=0.6, sharp_deg=50.0)
    return ob


def build_head(M, col, location, rotation, open_deg, roll_deg, scale=0.60, fast=False):
    """open_deg is a starting value: the jaw's opening and length are solved from the sheet."""
    global U, FAST
    U, FAST = scale, fast
    F = Frame(location, rotation, scale, open_deg, roll_deg)
    solve_jaw(F)
    print("JAW open %.2f deg, length %.3f u, chin x %.3f; inner edges: left %d pts, right %d pts" % (
        JAW["open"], JAW["L"], JAW["chin_x"], len(JAW["left"]), len(JAW["right"])))
    sk = build_skull(col, M)
    jaw = build_jaw(col, M, sk, F)
    eyes(M, col, sk)
    mouth_flesh(M, col, sk, jaw, F)
    gums_and_teeth(M, col, sk, jaw, F)
    crown_bracket(col, M["bar"], sk)
    sk.location, sk.rotation_euler = location, rotation
    sk.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    return sk, jaw
