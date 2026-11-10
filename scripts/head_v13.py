"""
v13 ("Experimental 09"): a reconstruction of the mouth and the eye sockets on v12's head (head_v12.py;
v12, the rest of the head and the body are kept unchanged). build_v13.py keeps v12's cranium shape, its
upper jaw (upper teeth and gums), eyes, crown bracket, torn skull sides, palate and throat, and rebuilds:

- the eye sockets (build_skull): small horizontal rectangles cut straight into the face plates around
  the unchanged pupils, at the sheet's size, without v8-v12's stepped frame - only the voxels near the
  sockets change, every other vertex of the cranium stays v12's;
- the lower jaw (solve_jaw): the exact side panel's profile, now at the panel's own height (v12 had moved
  it up with the upper gum, 7.8 px), so the jaw hangs as low as the sheet draws it; and its U, side by
  side, from the sheet's lower gum line in the front AND three-quarter panels: the rim where the teeth
  stand runs along the red tissue line and the roots, converging to a narrow, off-centre chin (v12 put
  the rim's inner edge on that line and closed it with a generic round chin, so its sides stood
  straight down to a wide bottom);
- the lower teeth (plan_lower): the sheet's 14 front-panel teeth (and the side panel's fan where the front
  shows none: 2, as in v12) on the new rim, each with v12's size - they move with the jaw, they are not
  stretched - crowded into the narrow chin as the sheet's bundle is;
- the gums and the mouth's tissue around the new jaw.

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

# Eye sockets: rectangular holes in the face plate (x, z centre; half width, half height; tilt in the
# face plane, degrees; depth into the skull). v13 restores the sheet's: small horizontal rectangles
# around the pupils (front panel 16 x 15 and 21 x 15 px, the pupil a little below the middle), cut
# straight into the plates. v8-v12 had taller holes inside a stepped frame, reaching down toward the
# teeth. The pupils (v12's Eyes) are kept where they were, each in its hole where the sheet has it
# (the right one a little left of v12's centre: its lit inner wall on that side reads as plate) and
# visible from the three-quarter camera; each hole deep enough to hold its pupil.
SOCKETS = [((-0.345, 0.187), (0.082, 0.068), -7.0, 0.150),      # the monster's right: lower, outer
           ((0.133, 0.222), (0.090, 0.072), 6.0, 0.150)]        # left: higher, nearer the midline
SOCKETS_V12 = [((-0.336, 0.165), (0.082, 0.083), -7.0, 0.150), ((0.133, 0.203), (0.090, 0.078), 6.0, 0.140)]
EYES = [(c[0], c[1], k) for (c, _, _, _), k in zip(SOCKETS_V12, (1.25, 1.15))]    # v12's pupils


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
    F = B.sub(F, sock)                                          # cut straight in: no stepped frame
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
    # upper row, front panel, re-read on a sharpened 8x zoom: root -> tip and the width at the root (px).
    # Uneven: a long, wide fang right of the middle, long teeth at the monster's right, short stubs at
    # its left; the roots stand at different heights along the broken gum (v 57-66)
    "front_upper": [((231, 59), (233, 89), 7.0), ((238.5, 60), (238, 95), 5.0), ((245.5, 62), (246, 87), 6.0),
                    ((251, 66), (251.5, 80), 4.5), ((258, 60), (258.5, 105), 8.5), ((269.5, 62), (270.5, 86), 7.5),
                    ((276.5, 61), (276.5, 74), 5.0), ((284.5, 57.5), (284, 80), 7.5), ((291.5, 57.5), (291, 69), 6.0)],
    # two more hang behind the front row (their roots hidden; the tips show below it)
    "front_upper_behind": [((243.5, 66), (244, 92), 5.0), ((272.5, 64), (272.5, 104), 5.5)],
    # lower row, re-read on sharpened 11-12x zooms, with widths: a crowded bundle fanning from the chin -
    # a wide central tooth (275) among taller slim ones behind it and short ones in front; the monster's
    # right group leans outward 6-14 deg, the middle stands upright, its left side leans in a little
    "front_lower": [((248, 146), (241, 105), 4.5), ((253, 151), (245, 113), 4.5), ((256, 153), (250, 115), 3.5),
                    ((261, 149), (255, 109), 5.0), ((265, 146), (261, 111), 4.5), ((262, 154), (257, 131), 4.0),
                    ((269, 154), (268, 135), 3.0), ((275, 153), (275, 118), 7.0), ((279, 153), (278, 132), 4.0),
                    ((283, 147), (282, 118), 5.0), ((288, 139), (285, 105), 5.0), ((293, 128), (290, 96), 5.0),
                    ((296, 119), (295, 92), 4.5), ((298, 109), (297, 88), 4.0)],
    "front_mouth_left": [(232, 62), (235, 80), (237, 100), (238, 120), (241, 138), (246, 147), (252, 153), (260, 157)],
    "front_mouth_right": [(300, 60), (301, 85), (298, 100), (295, 120), (290, 135), (283, 146), (275, 153), (268, 156)],
    "side_upper": [((90, 106), (91, 135)), ((96, 107), (98, 140)), ((104, 107), (106, 157)), ((111, 106), (115, 143)),
                   ((117, 106), (120, 172)), ((123, 105), (126, 150)), ((129, 104), (132, 127)), ((134, 103), (135, 120))],
    "side_lower": [((148, 218), (128, 205)), ((150, 210), (124, 192)), ((152, 200), (122, 180)), ((155, 190), (130, 165)),
                   ((158, 180), (138, 150)), ((160, 170), (142, 143)), ((163, 160), (152, 135)), ((166, 150), (160, 128)),
                   ((168, 140), (162, 120)), ((170, 130), (165, 110))],
    # the lower jaw in the exact side panel, traced against the background: the lower teeth's root line
    # (the jaw's front edge), the jaw's rear edge (its underside: close to vertical below the hinge,
    # then curving forward into the chin) and the chin's bottom with its broken spur
    "side_jaw": {"roots": [(170, 130), (168, 140), (166, 150), (163, 160), (160, 170), (158, 180), (155, 190),
                           (152, 200), (150, 210), (148, 218)],
                 "rear": [(184, 152), (184, 160), (183, 168), (180, 176), (178, 184), (176, 192), (173, 200),
                          (171, 206), (168, 214), (166, 222), (164, 228)],
                 "chin": [(166, 230), (163, 231), (160, 230), (157, 228)]},
    "34_lower": [((186, 199), (178, 167)), ((191, 200), (181, 157)), ((196, 201), (189, 152)), ((201, 202), (195, 150)),
                 ((206, 202), (205, 181)), ((212, 202), (210, 158)), ((219, 201), (220, 158)), ((227, 192), (226, 134)),
                 ((232, 176), (230, 125)), ((237, 160), (235, 124))],
    "34_gum_v": 96.0, "34_chin_v": 206.0,
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
# Lower jaw: its side profile from the exact side panel, its asymmetric U from the front panel
# (jaw-local: hinge at the origin, chin -Y, the tooth row on the rim's top +Z)
# ---------------------------------------------------------------------------
RIM_W = 0.110                     # width of the bony rim across the U (front view)
GUM_T = 0.022                     # the thin gum over the bone where the lower teeth stand
JAW = {}                          # solved: "open", "L" (chin end), "L_top" (end of the tooth row), "top", the
                                  # underside profile, "chin_x", "left"/"right" inner-edge tables, "path"


def _side_world(u, v, x=0.05):
    """A side-panel pixel -> world point on the orthographic side camera's ray, at world x."""
    return Vector((x, (u - SIDE_CAM[0]) / SIDE_CAM[2], (SIDE_CAM[1] - v) / SIDE_CAM[2]))


def _fit_jaw_pose(F):
    """The jaw's opening and side profile from the exact side panel. The opening is the angle at
    which the lower teeth's root line runs straight along the jaw; in the jaw's own frame at that
    angle the root line gives the rim's top (bone under a thin gum), the jaw's rear edge its
    underside (deepest below the hinge, rising toward the chin), and the chin its end. The trace is
    placed relative to the upper gum, as the side panel draws the two jaws."""
    # v13: the jaw hangs at the side panel's own height. v12 moved the trace up with the upper gum (v11's
    # skull, kept, holds it 7.8 px higher than the panel); now the jaw is lowered by that much, so its
    # chin, rear edge and tooth row lie on the sheet's own
    gum_model = np.mean([side_uv(F.hw((x,) + gum_front(x)))[1] for x in np.linspace(UP_RIGHT_X, UP_LEFT_X, 9)])
    gum_sheet = np.mean([rv for (ru, rv), _ in SHEET["side_upper"] if ru < 109])
    JAW["gum_offset"] = float(gum_model - gum_sheet)
    JAW["side_shift"] = shift = 0.0
    S = {k: [(u, v + shift) for u, v in pts] for k, pts in SHEET["side_jaw"].items()}
    best = None
    for od in np.arange(66.0, 86.01, 0.25):
        F.set_jaw(od, F.roll_deg)
        z = np.array([F.wj(_side_world(u, v)).z for u, v in S["roots"]])
        if best is None or z.std() < best[0]:
            best = (z.std(), od)
    od = float(best[1])
    F.set_jaw(od, F.roll_deg)
    loc = lambda pts: np.array([tuple(F.wj(_side_world(u, v)))[1:] for u, v in pts])
    R, Bk, C = loc(S["roots"]), loc(S["rear"]), loc(S["chin"])
    JAW["open"] = od
    JAW["top"] = float(R[:, 1].mean()) - GUM_T
    JAW["L_top"] = float(-R[:, 0].min())
    JAW["L"] = float(-C[:, 0].min())
    order = np.argsort(Bk[:, 0])
    JAW["bot_y"], JAW["bot_z"] = Bk[order, 0], Bk[order, 1]
    JAW["chin_bot"] = float(C[:, 1].min())
    return od, JAW["L"]


def _top(y):
    """The rim's top (bone) along the jaw: level along the tooth row and the chin arc where the front
    teeth stand, then a rounded chamfer down to the chin's end (the side panel's chin front)."""
    over = np.clip(-(JAW["L_top"] + 0.045) - np.asarray(y, float), 0.0, None)
    return JAW["top"] - 2.0 * over - 6.0 * over ** 2


def _bot(y):
    """The jaw's underside along it: the side panel's rear edge, held level beyond its traced ends."""
    return np.interp(np.asarray(y, float), JAW["bot_y"], JAW["bot_z"])


def _front_map(F, v_sheet):
    """Sheet front-panel v in the mouth -> model front-view v: gum line to gum line, the mouth's bottom
    to the rim's top at the chin (where the lower teeth stand), linear."""
    vg = front_uv(F.hw((0.0, FRONT_UP, GUM_Z)))[1]
    yc = -JAW["L_top"]
    vc = front_uv(F.jw((JAW["chin_x"], yc, float(_top(yc)))))[1]
    return vg + (v_sheet - SHEET_FRONT_GUM_V) * (vc - vg) / (SHEET_FRONT_CHIN_V - SHEET_FRONT_GUM_V)


SHEET_34_GUM_V, SHEET_34_CHIN_V = 96.0, 206.0
REAR = ((0.397, 0.060), (-0.443, 0.060))        # the arms' rear ends at the hinges (v12's), left and right


def _map34(F, v_sheet):
    """Sheet three-quarter panel v in the mouth -> model three-quarter v: gum line to gum line, the chin's
    roots to the rim's top at the chin, linear (as _front_map; the panel draws the mouth 0.70 m tall)."""
    vg = float(np.mean([uv34(F.hw((x,) + gum_front(x)))[1] for x in np.linspace(UP_RIGHT_X, UP_LEFT_X, 9)]))
    yc = -JAW["L_top"]
    vc = uv34(F.jw((JAW["chin_x"], yc, float(_top(yc)))))[1]
    return vg + (v_sheet - SHEET_34_GUM_V) * (vc - vg) / (SHEET_34_CHIN_V - SHEET_34_GUM_V)


def _on_rim(F, proj, u_t, v_t, x0):
    """The jaw-local (y, x) on the rim's top whose projection `proj` lands on (u_t, v_t): y by bisection
    on the height (the jaw hangs steeply, so height follows y), x by secant steps on the horizontal.
    None if the height is outside the rim (above the hinge)."""
    lo_, hi_ = -JAW["L_top"], 0.10
    P = lambda x_, y_: proj(F.jw((x_, y_, float(_top(y_)))))
    x, y = x0, lo_
    for _ in range(4):
        vlo, vhi = P(x, lo_)[1], P(x, hi_)[1]
        if not (min(vlo, vhi) - 1.0 <= v_t <= max(vlo, vhi) + 1.0):
            return None
        a, b = lo_, hi_
        for _ in range(40):
            m = 0.5 * (a + b)
            if (P(x, m)[1] > v_t) == (vlo > v_t):
                a = m
            else:
                b = m
        y = 0.5 * (a + b)
        u0, u1 = P(x, y)[0], P(x + 0.05, y)[0]
        x += (u_t - u0) * 0.05 / (u1 - u0)
    return y, x


def _rim_samples(F):
    """Where the sheet shows the lower jaw's rim (the gum the lower teeth stand in), as jaw-local
    (x, y, source): the front panel's red tissue line down the mouth's sides and round the chin, its
    lower roots, and the three-quarter panel's lower roots - each panel's heights mapped onto the
    model's mouth (gum to chin), its horizontal positions as drawn."""
    out = []
    for side, key in ((1, "front_mouth_right"), (-1, "front_mouth_left")):
        for us, vs in SHEET[key]:
            if vs < 95:
                continue                       # higher up the line is the cheeks', between the jaws
            r = _on_rim(F, front_uv, us, _front_map(F, vs), side * 0.3)
            if r:
                out.append((r[1], r[0], "front_line"))
    for (ru, rv), _, _ in SHEET["front_lower"]:
        r = _on_rim(F, front_uv, ru, _front_map(F, rv), 0.0)
        if r:
            out.append((r[1], r[0], "front_root"))
    for (ru, rv), _ in SHEET["34_lower"]:
        r = _on_rim(F, uv34, ru, _map34(F, rv), 0.0)
        if r:
            out.append((r[1], r[0], "34_root"))
    return out


def solve_jaw(F):
    """Fit the jaw: pose and side profile from the exact side panel (at the panel's height); its U - the
    rim's centre line, where the lower teeth stand - through the sheet's lower gum line as the front and
    three-quarter panels draw it, smoothed, round to the arms' rear ends at the hinges."""
    od, L = _fit_jaw_pose(F)
    JAW["chin_x"] = -0.06
    for _ in range(3):                                  # the chin's x feeds the panels' height mappings
        S = _rim_samples(F)
        xs = np.array([p[0] for p in S])
        ys = np.array([p[1] for p in S])
        # order along the U by the angle seen from a point inside it above the chin: + on the left arm
        # (+x), 0 at the chin, - on the right arm
        cx, cy = float(np.median(xs)), -0.55
        phi = np.degrees(np.arctan2(xs - cx, cy - ys))
        rear = [(x, y, math.degrees(math.atan2(x - cx, cy - y))) for x, y in REAR]
        grid = np.linspace(phi.min(), phi.max(), 21)
        pts = []
        for g in grid:                                  # Gaussian-weighted average, 7 degrees wide
            w = np.exp(-0.5 * ((phi - g) / 7.0) ** 2)
            pts.append((float(np.sum(w * xs) / np.sum(w)), float(np.sum(w * ys) / np.sum(w))))
        pts = sorted(pts, key=lambda q: -math.degrees(math.atan2(q[0] - cx, cy - q[1])))
        lp = [(rear[0][0], rear[0][1])] + pts + [(rear[1][0], rear[1][1])]
        low = min(pts, key=lambda q: q[1])
        JAW["chin_x"] = low[0]
    JAW["samples"] = S
    pts = np.array(lp, float)
    seg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    # resample evenly along the path (the rim, the teeth and the tissue use its parameter t)
    tt = np.linspace(0.0, seg[-1], 33)
    P = np.c_[np.interp(tt, seg, pts[:, 0]), np.interp(tt, seg, pts[:, 1]), tt / seg[-1]]
    JAW["path"] = P
    JAW["left"] = [(y, x) for x, y, _ in P if x > JAW["chin_x"]]
    JAW["right"] = [(y, x) for x, y, _ in P if x <= JAW["chin_x"]]
    return JAW


def jaw_path():
    return JAW["path"]


def _rim_params(t, x, y):
    """Rim width, top and underside at path parameter t (0..1, chin near 0.5): the side panel's profile
    (_top, _bot), uneven along the jaw - the left rim dips where it is broken, the chin is wider."""
    t = np.asarray(t, float)
    f = 1.0 - np.abs(t - 0.5) * 2.0
    w = RIM_W * (1.0 + 0.10 * np.sin(9.0 * t + 1.0) + 0.15 * f)
    top = _top(y) + 0.010 * np.sin(13.0 * t) - 0.025 * np.exp(-((t - 0.30) / 0.06) ** 2)
    bot = _bot(y) - 0.010 * np.sin(7.0 * t + 2.0)
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
    zc = 0.5 * (JAW["top"] + float(_bot(0.0)))
    for (ex_, ey_, _), s in zip((P[0], P[-1]), (1, -1)):  # rami rising to the torn-out condyles
        F = B.union(F, B.box(G, (ex_, ey_ + 0.01, zc), (0.055, 0.06, 0.10), B.rot(0, s * 6, 0)))
    # the chin's broken spur, hanging below its end (the side panel's chin)
    F = B.union(F, B.box(G, (JAW["chin_x"] - 0.03, -JAW["L"] + 0.035, JAW["chin_bot"] + 0.02), (0.035, 0.05, 0.03),
                         B.rot(18, 0, 10)))
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
    chips out of the underside (the side view's rear edge) and the top, a blocky lump on the right."""
    P = jaw_path()
    at = lambda t: _path_at(P, t)
    out_n, out_c = [], []
    x, y, _, n = at(0.62)                                     # chin's right corner
    out_n.append(((x - 0.02, y - 0.03, float(_top(y)) - 0.02), (0.07, 0.06, 0.05), (0, 0, 20)))
    x, y, _, n = at(0.30)                                     # left rim broken down
    out_n.append(((x - n[0] * 0.02, y, float(_top(y)) + 0.01), (0.05, 0.09, 0.04), (0, 0, 0)))
    for t, dz, sz in ((0.10, -0.01, 0.05), (0.18, 0.0, 0.06), (0.27, -0.02, 0.045), (0.40, 0.0, 0.05),
                      (0.70, 0.0, 0.05), (0.84, -0.01, 0.06)):
        x, y, _, n = at(t)                                    # chips out of the underside (side silhouette)
        out_n.append(((x - n[0] * 0.03, y - n[1] * 0.03, float(_bot(y)) + dz), (0.06, sz, 0.035), (12, 0, 10)))
    for t in (0.14, 0.23, 0.35):
        x, y, _, n = at(t)                                    # bites out of the top between the teeth
        out_n.append(((x + n[0] * 0.02, y, float(_top(y)) + 0.01), (0.04, 0.025, 0.03), (0, 0, 25)))
    x, y, _, n = at(0.80)                                     # lump on the right side
    out_c.append(((x - n[0] * 0.05, y - n[1] * 0.05, float(_bot(y)) + 0.06), (0.04, 0.09, 0.06), (0, 0, 4)))
    x, y, _, n = at(0.52)
    out_c.append(((x - n[0] * 0.04, y - n[1] * 0.04, float(_bot(y)) + 0.04), (0.05, 0.05, 0.05), (0, 0, 12)))
    return out_n, out_c


def build_jaw(col, M, sk, F):
    global JAW_NOTCHES, JAW_CHUNKS
    JAW_NOTCHES, JAW_CHUNKS = _jaw_breaks()
    P = jaw_path()
    lo = (P[:, 0].min() - 0.15, P[:, 1].min() - 0.14, float(np.min(JAW["bot_z"])) - 0.16)
    hi = (P[:, 0].max() + 0.15, max(P[:, 1].max(), 0.06) + 0.12, JAW["top"] + 0.10)
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
    depth = width * rng.uniform(0.86, 0.97)
    n = sides
    prof = [(math.cos(2 * math.pi * k / n) * width / 2 * rng.uniform(0.95, 1.05),
             math.sin(2 * math.pi * k / n) * depth / 2 * rng.uniform(0.95, 1.05)) for k in range(n)]
    c_dir = Vector(curl_dir) if curl_dir is not None else side
    c_dir = c_dir - d * c_dir.dot(d)
    if c_dir.length < 1e-6:
        c_dir = side
    curl = c_dir.normalized() * length * (curl_amt if curl_amt is not None else rng.uniform(0.05, 0.12))
    cut = rng.uniform(0.62, 0.82) if kind == "snapped" else 1.0
    ts = [-0.08, 0.0, 0.10, 0.22, 0.36, 0.50, 0.64, 0.77, 0.88, 0.95]
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


UP_LEN_K, LO_LEN_K = 1.30, 1.00           # front-panel tooth heights -> model, on the front mouth's own scale
                                          # (x the mapping, 1.3); the lower row capped by the side panel's fan
WIDTH_K_UP, WIDTH_K_LO = 1.35, 1.80       # the sheet's tooth widths (front panel px) -> model, as v12: the sheet's
                                          # teeth are lit full-width; the model's lose their edges to shade and gum
TEETH_K = 1.233                           # the front panel's tooth sizes -> model: v12's front-mouth scale, kept,
                                          # so the lowered jaw carries its teeth without stretching them


def _side_fan(F):
    """The side panel's lower teeth along the jaw, in jaw-local terms: for each root's position along
    the jaw (local y), the tooth's elevation in the side view (from horizontal, forward) and length (m).
    About 33 deg at the chin, steepening to 76 deg toward the hinge."""
    rows = []
    for (ru, rv), (tu, tv) in SHEET["side_lower"]:
        y = F.wj(_side_world(ru, rv)).y
        dY, dZ = (tu - ru) / SIDE_CAM[2], (rv - tv) / SIDE_CAM[2]
        rows.append((y, math.atan2(dZ, -dY), math.hypot(dY, dZ)))
    rows.sort()
    return np.array(rows)


def _fan_envelope():
    """The front edge of the side panel's lower fan: the most forward tip at each height (side px)."""
    tips = sorted((tv, tu) for _, (tu, tv) in SHEET["side_lower"])
    return np.array([v for v, _ in tips], float), np.array([u for _, u in tips], float)


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


def _tooth_width(L, px=None, lower=False):
    """Root width (head units). Teeth read off the front panel keep the sheet's own width there (px, at
    160 px per metre, x WIDTH_K_*); the others (side panel) get a width that varies with their length."""
    if px is not None:
        return px / FRONT_CAM[2] * (WIDTH_K_LO if lower else WIDTH_K_UP) / U * rng.uniform(0.95, 1.05)
    return (0.052 + 0.050 * L) * rng.uniform(0.85, 1.15)


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


def _spread_on_rim(P, teeth, gap=0.036):
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


def _curl(i, lower):
    """Each tooth's own gentle curve: mostly back into the mouth, turned a little to one side or the
    other, by an amount that differs tooth to tooth (deterministic per tooth)."""
    r = random.Random(907 + i * 31 + (500 if lower else 0))
    side = r.uniform(-0.9, 0.9)
    return ((side, 0.8, -0.3) if lower else (side, 1.0, 0.2)), r.uniform(0.03, 0.13)


def plan_lower(F):
    """The lower teeth from the sheet (v13; the upper row is v12's, kept): the front panel's bundle (each
    tooth's own width and height; roots where they project on the solved rim) and the side panel's fan
    where the front panel shows none; every tooth points the way the side panel's fan does at its place
    on the jaw. Sizes on v12's scale (TEETH_K): the jaw is lowered, the teeth are not stretched.
    Returns the teeth in jaw-local space."""
    rng.seed(1313)                      # the same plan in the build and in the checks
    lo = []
    kmap = TEETH_K
    P = jaw_path()
    fan = _side_fan(F)
    env_v, env_u = _fan_envelope()
    ts = np.linspace(0.02, 0.98, 400)
    rim = [_rim_point(P, t) for t in ts]
    rim_uv = np.array([front_uv(F.jw(p)) for p, _ in rim])
    for k, ((ru, rv), (tu, tvv), wpx) in enumerate(SHEET["front_lower"]):
        vm = _front_map(F, rv)
        i = int(np.argmin((rim_uv[:, 0] - ru) ** 2 + (rim_uv[:, 1] - vm) ** 2))
        t = float(ts[i])
        root, n = rim[i]
        rw = F.jw(root)
        rise = (rv - tvv) / FRONT_CAM[2] * LO_LEN_K * kmap         # the front panel's height (m), on v12's scale
        e_fan = float(np.interp(root.y, fan[:, 0], fan[:, 1]))
        su, sv = side_uv(rw)
        u_env = float(np.interp(sv - rise * SIDE_CAM[2], env_v, env_u))
        fwd_max = max((su - u_env) / SIDE_CAM[2], 0.02)
        e = max(e_fan, math.atan2(rise, fwd_max))
        Lw = rise / math.sin(e)
        tw = rw + Vector(((tu - ru) / FRONT_CAM[2] * kmap * LO_LEN_K, -Lw * math.cos(e), Lw * math.sin(e)))
        tip = F.wj(tw)
        L = (tip - root).length + 0.03
        c, ca = _curl(k, True)
        lo.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L, wpx, True), "t": t, "src": "front", "n": n,
                   "rv": rv, "curl": c, "curl_amt": ca})
    _spread_on_rim(P, lo)
    # --- lower teeth from the side panel's fan (near side, +x), where the front panel shows none
    near = [k for k in range(len(ts)) if ts[k] <= 0.5]
    side_uv_rim = np.array([side_uv(F.jw(rim[k][0])) for k in near])
    for j, ((ru, rv), (tu, tvv)) in enumerate(SHEET["side_lower"]):
        k = near[int(np.argmin((side_uv_rim[:, 0] - ru) ** 2 + (side_uv_rim[:, 1] - rv) ** 2))]
        root, n = rim[k]
        if min((root - o["root"]).length for o in lo) < 0.10:
            continue                                # (v13: wider than v12's 0.07, so the count stays v12's 16)
        rw = F.jw(root)
        tw = Vector((rw.x + 0.012, rw.y + (tu - ru) / SIDE_CAM[2], rw.z + (rv - tvv) / SIDE_CAM[2]))
        tip = F.wj(tw)
        L = (tip - root).length + 0.03
        c, ca = _curl(30 + j, True)
        lo.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L), "t": float(ts[k]), "src": "side", "n": n,
                   "curl": c, "curl_amt": ca})
    _stagger_rows(lo)
    # teeth that would touch are moved apart mostly along the front view's line of sight, so the front
    # panel's reading holds and they part in depth
    rot = lambda M: M.to_3x3().normalized()
    v_lo = (rot(F.Ji) @ (rot(F.Ci) @ Vector((0.0, 1.0, 0.0)))).normalized()
    rest = _separate(lo, view=v_lo)
    print("TEETH remaining interpenetration (head units): lower %.3f" % rest)
    for tth in sorted(lo, key=lambda d: d["L"])[:2]:            # a few teeth snapped (the shortest), as on the sheet
        tth["kind"] = "snapped"
    return lo


def gums_and_teeth(M, col, sk, jaw, F):
    """The lower teeth and gums (v13); the upper ones are v12's, kept by build_v13.py."""
    lo = plan_lower(F)
    print("TEETH lower %d (front %d, side %d)" % (len(lo), sum(t["src"] == "front" for t in lo),
                                                  sum(t["src"] == "side" for t in lo)))
    bm, layer = D.new_tooth_bm()
    for tth in lo:
        d = tth["tip"] - tth["root"]
        Lb = d.length
        base = tth["root"] - d.normalized() * 0.03                     # root set into the gum
        tusk(bm, layer, base, d, Lb + 0.03, tth["w"], tth.get("kind", "fang"), curl_dir=tth.get("curl", (0, 0.8, -0.3)),
             curl_amt=tth.get("curl_amt", rng.uniform(0.04, 0.11)))
    D.bm_object("Teeth_Lower", bm, col, [M["teeth"]], parent=jaw)

    # gums: not a smooth tube along the jaw but irregular collars of tissue around each tooth's base,
    # joined by a thin band that breaks off in places, so the jaw's damaged bone shows between them
    def collars(bm, group, seed, scale, bare=0.25):
        """Lumps of gum around the teeth's bases, each its own size; some teeth stand on bare bone."""
        r_ = random.Random(seed)
        for tth in group:
            if r_.random() < bare:
                continue
            d = (tth["tip"] - tth["root"]).normalized()
            c = tth["root"] + d * 0.006
            rad = scale * r_.uniform(0.6, 1.25) * (0.55 * tth["w"] + 0.010)
            for _ in range(r_.choice((1, 1, 2, 3))):
                off = d.orthogonal().normalized() * r_.uniform(-0.7, 0.7) * rad
                off = Matrix.Rotation(r_.uniform(0, 2 * math.pi), 3, d) @ off
                sq = (r_.uniform(0.9, 1.7), r_.uniform(0.7, 1.2), r_.uniform(0.4, 0.75))
                rot = d.to_track_quat('Z', 'Y').to_matrix()
                m = (Matrix.Translation(c + off) @ rot.to_4x4() @
                     Matrix.Diagonal((rad * sq[0], rad * sq[1], rad * sq[2], 1.0)))
                res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0, matrix=m)
                cen = c + off
                for v in res["verts"]:
                    v.co += (v.co - cen) * r_.uniform(-0.22, 0.22)

    def band(bm, path, r0, seed, keep=0.68):
        """A thin strip of tissue along a path, torn into runs of uneven length that thin out at their
        torn ends, with gaps of bare bone between them."""
        r_ = random.Random(seed)
        run = []
        for p in path + [None]:
            if p is not None and (r_.random() < keep or len(run) < 2):
                run.append(p)
                continue
            if len(run) >= 2:
                n_ = len(run)
                rad = [r0 * r_.uniform(0.5, 1.4) * (0.35 + 0.65 * math.sin(math.pi * (i + 0.5) / n_)) for i in range(n_)]
                D.tube(bm, run, rad, 0, sides=7, jitter=0.35, frame_ref=(0, 0, 1))
            run = []

    P = jaw_path()
    # the gum along the jaw's edge, outside the tooth row: the sheet's thin red line down both arms and
    # round the chin (v13: on the rim's outer edge, where it shows, and torn less - still uneven, with gaps)
    lo_path = [_rim_point(P, t, inward=-0.015, dz=0.008)[0] for t in np.linspace(0.03, 0.97, 72)]
    gb = bmesh.new()
    collars(gb, lo, 73, 1.0)
    band(gb, lo_path, 0.020, 74, keep=0.78)
    D.bm_object("Gums_Lower", gb, col, [M["tissue"]], parent=jaw)
    return lo


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
    for s, x_up, t0 in ((1, UP_LEFT_X, 0.03), (-1, UP_RIGHT_X, 0.97)):     # thin, ragged bands, upper jaw -> rim
        for k, (ty, dt, r0) in enumerate(((0.26, 0.00, 0.028), (0.14, 0.05, 0.022), (0.02, 0.10, 0.017))):
            a = Vector((x_up + s * 0.02, ty, GUM_Z - 0.01))
            p, n = _rim_point(P, t0 + dt if s > 0 else t0 - dt, inward=0.0, dz=-0.01)
            b = jm @ p
            pts = []
            for i in range(8):
                f = i / 7
                if (k == 2 and f > 0.7) or (k == 1 and s < 0 and f > 0.55):
                    break                                       # torn through
                pts.append(a.lerp(b, f) + Vector((s * 0.04 * math.sin(math.pi * f), rng.uniform(-0.012, 0.012),
                                                  -0.03 * math.sin(math.pi * f))))
            D.tube(wb, pts, [r0 * (1.0 + 0.5 * math.sin(math.pi * i / 7)) * rng.uniform(0.65, 1.35)
                             for i in range(len(pts))], 0, sides=7, jitter=0.4)
    D.bm_object("Mouth_Cheek_Flesh", wb, col, [M["tissue"]], parent=sk)
    ib = bmesh.new()                                         # dark inner cheek walls, set back in the mouth: the
    for s, x_up, t0, t1 in ((1, UP_LEFT_X, 0.02, 0.24), (-1, UP_RIGHT_X, 0.98, 0.55)):   # far (right) side spans
        grid = []                                                                        # the gape, the near side
        for u in np.linspace(0.0, 1.0, 12):                                              # only its rear: the mouth
            ty = 0.32 - u * (0.40 if s > 0 else 0.92)                                    # reads dark, never hollow
            top = Vector((x_up - s * (0.05 if s > 0 else -0.02), ty, GUM_Z + 0.02))      # (v13: down to the lowered,
            p, n = _rim_point(P, t0 + (t1 - t0) * u, inward=0.035, dz=-0.03)             # narrower jaw's rim; the far
            bot = jm @ p                                                                 # wall flat, along the sheet's
            bulge = 0.04 if s > 0 else 0.0                                               # mouth outline, so no line of
            grid.append([top.lerp(bot, v) + Vector((-s * bulge * math.sin(math.pi * v), 0.0, 0.0))   # sight passes
                         for v in np.linspace(0.0, 1.0, 8)])                             # it into the body behind)
        _sheet(ib, grid, seed=51 + s)
    walls = D.bm_object("Mouth_Inner_Walls", ib, col, [M["tissue"]], parent=sk)
    sol = walls.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.015
    D.apply_modifiers(walls)
    fb = bmesh.new()                                         # the mouth's floor: dark tissue, set down inside the U
                                                             # (the sheet's gaps between the teeth are dark brown-
                                                             # maroon, about 0.15 bright - not black)
    grid = []
    fr = random.Random(41)
    ic = int(np.argmin(P[:, 1]))                             # the chin: the U's lowest point

    def arm_x(y, q):                                         # an arm's centre line x at jaw-local y (v13's U is
        o = np.argsort(q[:, 1])                              # crooked: each arm is read on its own)
        return float(np.interp(y, q[o, 1], q[o, 0]))
    for y in np.linspace(0.05, -JAW["L"] + 0.14, 22):
        xl = arm_x(y, P[:ic + 1]) - 0.03                     # the floor's edges run into the rim's walls
        xr = arm_x(y, P[ic:]) + 0.03
        row = []
        lift = 0.12 * min(max((y + 0.30) / 0.35, 0.0), 1.0)    # near the hinge the floor rises in front of the
        for v in np.linspace(0.0, 1.0, 13):                  # neck (the lowered jaw's floor would sink into it)
            fold = 0.022 * math.sin(19.0 * y + 2.3) * math.sin(math.pi * v) + 0.016 * math.sin(11.0 * v + 7.0 * y)
            row.append(Vector((xr + (xl - xr) * v + fr.uniform(-0.01, 0.01), y + fr.uniform(-0.012, 0.012),
                               float(_bot(y)) + 0.02 + lift - 0.05 * math.sin(math.pi * v) + fold
                               + fr.uniform(-0.012, 0.012))))
        grid.append(row)
    _sheet(fb, grid, seed=41)
    D.bm_object("Mouth_Floor", fb, col, [M["tissue"]], parent=jaw)
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


MOUTH_OBJECTS = ("Jaw", "Teeth_Lower", "Gums_Lower", "Mouth_Cheek_Flesh", "Mouth_Inner_Walls", "Mouth_Floor",
                 "Jaw_Strands")        # rebuilt by v13; v12's Teeth_Upper and Gums_Upper are kept


def restore_sockets(M, col, sk):
    """Re-cut the cranium's eye sockets (SOCKETS). The cranium is rebuilt from the same SDF with only
    the socket boxes changed (it reproduces v12's mesh exactly when they are not); every new vertex that
    coincides with one of v12's takes v12's attributes, so away from the sockets the cranium is v12's to
    the bit. The object (its transform and its children - eyes, upper teeth, tissue) is kept; only its
    mesh is swapped. Returns (changed vertices, their bounding box in cranium space)."""
    from scipy.spatial import cKDTree
    global U, FAST
    U, FAST = sk.scale[0], False
    old = sk.data
    tmp = build_skull(col, M)
    me = tmp.data
    n_old, n_new = len(old.vertices), len(me.vertices)
    a = np.empty(n_old * 3, np.float32)
    old.vertices.foreach_get("co", a)
    b = np.empty(n_new * 3, np.float32)
    me.vertices.foreach_get("co", b)
    a, b = a.reshape(-1, 3), b.reshape(-1, 3)
    d, idx = cKDTree(a).query(b)
    same = d < 1e-7
    for at in old.attributes:
        if at.domain != 'POINT' or at.data_type != 'FLOAT' or at.name.startswith('.') or at.name not in me.attributes:
            continue
        x = np.empty(n_old, np.float32)
        at.data.foreach_get("value", x)
        y = np.empty(n_new, np.float32)
        me.attributes[at.name].data.foreach_get("value", y)
        y[same] = x[idx[same]]
        me.attributes[at.name].data.foreach_set("value", y)
    me.update()
    name = old.name
    sk.data = me
    bpy.data.objects.remove(tmp)
    bpy.data.meshes.remove(old)
    me.name = name
    ch = b[~same]
    box = (ch.min(axis=0), ch.max(axis=0)) if len(ch) else None
    return int((~same).sum()), box


def build_mouth(M, col, sk, location, rotation, open_deg, roll_deg, scale=0.60, fast=False):
    """v13: rebuild the lower jaw, the lower teeth and gums and the mouth's tissue on v12's head; `sk` is
    v12's cranium (its upper teeth and gums, eyes, crown bracket, torn sides, palate and throat kept)."""
    global U, FAST
    U, FAST = scale, fast
    F = Frame(location, rotation, scale, open_deg, roll_deg)
    solve_jaw(F)
    print("JAW open %.2f deg, length %.3f u (tooth row %.3f), rim top %.3f, chin x %.3f; %d rim samples"
          % (JAW["open"], JAW["L"], JAW["L_top"], JAW["top"], JAW["chin_x"], len(JAW["samples"])))
    jaw = build_jaw(col, M, sk, F)
    mouth_flesh(M, col, sk, jaw, F)
    gums_and_teeth(M, col, sk, jaw, F)
    bpy.context.view_layer.update()
    return jaw
