"""
v15 ("Experimental 11"): the posterior teeth lengthened and the brows made angrier, on v14's head
(head_v14.py: its jaw and curvature, the opening, the gums and the mouth's tissue, the sockets and the
pupils are kept unchanged, as are v14 itself and the body). build_v15.py rebuilds two things:

- the teeth (lengthen_posterior): both rows are planned exactly as v14 plans them; then the teeth
  further inside the mouth - behind the upper front row and along both sides of the upper jaw, the
  front row's near end where it turns back toward the corner, and the lower teeth from the near side
  of the chin up the jaw's arm - grow from their own roots toward the prominent front teeth's length
  (POST_LEN_*, POST_VAR, POST_CAP_*), each to its own length and shortening again toward the hinges
  (taper_up, taper_lo). They grow a step at a time, and a step is kept only where the whole tooth stays
  clear of every other tooth of both rows and of bone and tissue; a tooth may turn aside a little to
  pass (NUDGE_DEG), a far-leaning upper tooth hangs straighter as it grows (LEAN_MAX), and a grown tooth
  thickens a little with its length where it stays clear (WIDTH_GROW). The other teeth are v14's;
- the brows (_brows, _brow_lips): their tops drop more steeply toward the nose on their inner halves
  (their outer halves, the head's side outline, stay v14's: BROW_V14), the right one juts a little
  further, and a lip of brow overhangs each socket's inner top corner (BROW_DROP, BROW_LIP), so the
  eyes' upper edges slant down into the scowl. The holes behind and the pupils are v14's.

Only the voxels at the brows and the sockets change in the cranium; every other vertex stays v14's
(checked in build_v15.py).

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
# face plane, degrees; depth into the skull). v13's holes, size and place kept, now:
# - tilted the sheet's way: each socket's inner (nose-side) corner lower than its outer one (v8-v13
#   tilted them the other way, raising the inner corners: a worried look);
# - deeper, under a heavy brow ledge (BROW) that overhangs each socket's top edge and follows its slope.
SOCKETS = [((-0.345, 0.187), (0.082, 0.068), 8.0, 0.190),       # the monster's right: lower, outer
           ((0.133, 0.222), (0.090, 0.072), -8.0, 0.190)]       # left: higher, nearer the midline
SOCKETS_V13 = [((-0.345, 0.187), (0.082, 0.068), -7.0, 0.150), ((0.133, 0.222), (0.090, 0.072), 6.0, 0.150)]
# pupils: v12's (x, z) and size, set deeper into the sockets (the right one less, so the three-quarter
# camera still sees it past the hole's inner wall)
EYES = [(-0.340, 0.180, 1.25, 0.015), (0.130, 0.210, 1.15, 0.035)]      # x, z, size, recess (head units)
EYES_V12_Y = (-0.398, -0.501)
# brow ledges over the sockets: how far each juts out in front of the face plate at the socket's top
# edge (head units), the height of its front face, and the slope of its top toward the nose (degrees):
# steeper than the socket's own edge, so the brows angle down into the middle of the face (the sheet's
# scowl). They stop at the face's brow line (BROW_TOP), where the forehead leans back, and neither juts
# past the nose ridge's front: the head's side outline stays the sheet's.
BROW = [(0.095, 0.090, 28.0), (0.055, 0.075, -26.0)]       # v15: heavier and steeper than v14's; each top
BROW_V14 = [(0.080, 0.075, 21.0), (0.055, 0.065, -19.0)]   # stays under v14's (BROW_V14), so the brows' outer
BROW_TOP = 0.37                                            # ends - the head's side outline - stay v14's and only
                                                           # their inner halves drop more steeply toward the nose
BROW_DROP = 10.0          # v15: the brow's lip drops over each socket's inner top corner, its edge this many
BROW_LIP = 0.05           # degrees steeper than the socket's own top edge (pivoting at its outer corner), and
                          # reaches this far back into the hole (head units) - the glare


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
    # the face block down to the upper jaw's edge: v14 - an irregular, curved edge through the upper teeth's
    # roots (the sheet's front panel), rising toward the back (side panel), instead of v8-v13's flat cut
    front = B.inter(*planes, (_edge_z(G.X, G.Y) - G.Z).astype(np.float32))
    # the rear block over the jaw hinges reaches lower, sloping up toward the face
    rear = B.inter(*planes, P((0, 0, -1), (0, 0.6, -0.27)), P((0, -0.62, -0.78), (0, 0.10, -0.06)))
    return B.union(front, rear)


UP_EDGE = {}                    # solved: the upper roots' x and heights across the front (solve_upper_edge)
EDGE_RISE = 0.045               # the upper edge rises toward the back (side panel: about 4 px)


def _edge_z(x, y):
    """The upper jaw's bony edge (cranium z) at x, y: through the front panel's upper roots (a little above
    each, so they emerge from it), broken between them, rising toward the cheek."""
    x = np.asarray(x, np.float32)
    y = np.asarray(y, np.float32)
    dz = np.interp(x, UP_EDGE["x"], UP_EDGE["dz"]).astype(np.float32)
    chips = 0.010 * np.sin(23.0 * x + 3.0) + 0.006 * np.sin(57.0 * x + 1.0)
    f = np.clip((y + 0.65) / 0.60, 0.0, 1.0)
    rise = EDGE_RISE * f * f * (3.0 - 2.0 * f)
    return (GUM_Z + 0.008 + dz + chips + rise).astype(np.float32)


def solve_upper_edge(F):
    """The heights of the upper teeth's roots across the front, as v12 placed them (each tooth's own root
    height on the sheet, on the front mouth's scale) -> UP_EDGE, the upper jaw's edge."""
    xs = np.linspace(UP_RIGHT_X - 0.03, UP_LEFT_X, 300)
    arc_u = np.array([front_uv(F.hw((x, float(face_y(x)) + 0.065, GUM_Z)))[0] for x in xs])
    pts = []
    for (ru, rv), _, _ in SHEET["front_upper"]:
        i = int(np.argmin(np.abs(arc_u - ru)))
        pts.append((float(xs[i]), -(rv - SHEET_FRONT_GUM_V) * TEETH_K / FRONT_CAM[2] / U))
    pts.sort()
    UP_EDGE["x"] = np.array([p[0] for p in pts], np.float32)
    UP_EDGE["dz"] = np.array([p[1] for p in pts], np.float32)
    return UP_EDGE


def _brows(G):
    """Heavy brow ledges: over each socket a block of skull that juts out in front of the face plate along
    the socket's sloping top edge (its underside), with a near-vertical front face and a top that angles
    down toward the nose and climbs back into the brow (capped there: the forehead above is kept) - it
    overhangs the hole and shades it; the brow notches and the plate mosaic break it up."""
    out = []
    for ((cx, cz), (hw, hh), tilt, _), (ov, bh, top_tilt), (ov4, bh4, top4) in zip(SOCKETS, BROW, BROW_V14):
        b, bt, bt4 = math.radians(tilt), math.radians(top_tilt), math.radians(top4)
        fy = float(face_y(cx))
        z0 = cz + hh / math.cos(b)
        yf, yf4 = fy - ov, fy - ov4
        out.append(B.inter(
            B.plane(G, (-math.tan(b), 0.0, -1.0), (cx, 0.0, z0)),                   # underside: the socket's edge
            B.plane(G, (0.0, -1.0, 0.25), (0.0, yf, z0)),                           # front face, nearly upright
            B.plane(G, (math.tan(bt), -1.0, 0.5), (cx, yf + 0.25 * bh, z0 + bh)),   # top: down to the nose, back up
            B.plane(G, (math.tan(bt), 0.0, 1.0), (cx, 0.0, max(BROW_TOP, z0 + bh))),  # into the brow line, no higher
            B.plane(G, (math.tan(bt4), -1.0, 0.5), (cx, yf4 + 0.25 * bh4, z0 + bh4)),  # v15: and under v14's top
            B.plane(G, (math.tan(bt4), 0.0, 1.0), (cx, 0.0, max(BROW_TOP, z0 + bh4))),
            B.plane(G, (1.0, 0.0, 0.0), (cx + hw + 0.05, 0.0, 0.0)),               # (the forehead above is kept)
            B.plane(G, (-1.0, 0.0, 0.0), (cx - hw - 0.05, 0.0, 0.0)),
            B.plane(G, (0.0, 1.0, 0.0), (0.0, fy + 0.10, 0.0))))
    return B.union(*out)


def _brow_lips(G):
    """v15: the brows' lips. Over each socket the brow's underside drops more steeply toward the nose than
    the socket's own top edge (BROW_DROP, pivoting at the outer corner): a wedge of brow overhangs the
    inner top corner of the opening, from the brow's front back BROW_LIP into the hole, so the eye's
    upper boundary slants down into the scowl. The hole behind it and the pupil are unchanged."""
    out = []
    for ((cx, cz), (hw, hh), tilt, _), (ov, bh, top_tilt) in zip(SOCKETS, BROW):
        b = math.radians(tilt)
        sg = 1.0 if tilt > 0 else -1.0
        bu = b + sg * math.radians(BROW_DROP)
        fy = float(face_y(cx))
        z0 = cz + hh / math.cos(b)
        xo = cx - sg * hw                                        # the socket's outer top corner
        zo = z0 - (xo - cx) * math.tan(b)
        out.append(B.inter(
            B.plane(G, (-math.tan(bu), 0.0, -1.0), (xo, 0.0, zo)),                   # the lip's steeper edge
            B.plane(G, (math.tan(b), 0.0, 1.0), (cx, 0.0, z0 + 0.01)),               # up to the socket's top
            B.plane(G, (0.0, -1.0, 0.25), (0.0, fy - ov, z0)),                       # the brow's front
            B.plane(G, (0.0, 1.0, 0.0), (0.0, fy + BROW_LIP, 0.0)),
            B.plane(G, (1.0, 0.0, 0.0), (cx + hw + 0.01, 0.0, 0.0)),
            B.plane(G, (-1.0, 0.0, 0.0), (cx - hw - 0.01, 0.0, 0.0))))
    return B.union(*out)


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
    F = B.union(F, _brows(G))                                   # v14: heavy brows over the sockets
    sock = _socket_boxes(G)
    F = B.sub(F, sock)                                          # cut straight in: no stepped frame
    lips = _brow_lips(G)
    F = B.union(F, lips)                                        # v15: the brows' lips over the openings
    for c, h, r in NOTCHES:
        F = B.sub(F, B.box(G, c, h, B.rot(*r)))
    tear = B.union(*[B.box(G, c, h, B.rot(*r)) for c, h, r in TEARS])
    F = B.sub(F, tear)
    # vaulted palate: the face block hollowed from below behind the front rim
    pal = B.box(G, (0.0, -0.20, GUM_Z - 0.02), (0.30, 0.36, 0.085), B.rot(0, 0, 0))
    F = B.sub(F, pal)
    # the hole proper, for the socket attribute and the plate mosaic: inside the boxes, behind the face plate,
    # not in the lips (v15: the lips are brow - rust plates - not socket)
    hole = B.inter(sock, -lips, (face_y(G.X) - 0.005 - G.Y).astype(np.float32))
    return F, hole, tear, pal


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


JAW_BOW, JAW_HOOK, JAW_ROW0 = 0.085, 0.065, 0.12     # v14: the tooth row's sweep (head units, see _top)


def _top(y):
    """The rim's top (bone) along the jaw. v14: not a straight bar - from below the hinge the tooth row
    sweeps down in an arc (its middle set back, JAW_BOW) and curls forward again toward the chin
    (JAW_HOOK), as the sheet's side panels draw the jaw; then a rounded chamfer down to the chin's end."""
    y = np.asarray(y, float)
    f = np.clip((-y - JAW_ROW0) / (JAW["L_top"] - JAW_ROW0), 0.0, 1.0)
    g = np.clip((f - 0.70) / 0.30, 0.0, 1.0)
    sweep = -JAW_BOW * np.sin(np.pi * f) + JAW_HOOK * g * g * (3.0 - 2.0 * g)
    over = np.clip(-(JAW["L_top"] + 0.045) - y, 0.0, None)
    return JAW["top"] + sweep - 2.0 * over - 6.0 * over ** 2


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
    """The upper jaw's broken lower edge across the front: (y, z) at x (cranium-local) - v14: on the
    irregular bony edge (_edge_z), just under it, where the gum is."""
    y = float(face_y(x)) + 0.065
    return y, float(_edge_z(x, y)) - 0.016


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


def _spread_on_rim(P, teeth, gap=0.040):
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


def _curl_vec(t_):
    """The sideways bend tusk() gives a tooth at its tip (its axis: root + d s + c s^2)."""
    d = t_["tip"] - t_["root"]
    c = Vector(t_.get("curl", (0.0, 0.0, 0.0)))
    c = c - d.normalized() * c.dot(d.normalized())
    if c.length < 1e-6:
        return Vector((0.0, 0.0, 0.0))
    return c.normalized() * (d.length + 0.03) * t_.get("curl_amt", 0.0)


def _overlap(a, b, n=14):
    """Deepest interpenetration of two teeth's visible parts (> 0: they intersect), with the axis
    points where it happens (on a, on b) and a's parameter there. v14: along each tooth's curved axis,
    as tusk() builds it (v11-v13 used the straight root -> tip line, so two curling teeth could still
    cross near their tips)."""
    best = (-9.0, None, None, 0.0)
    ts = np.linspace(T_VISIBLE, 0.95, n)
    da, db = a["tip"] - a["root"], b["tip"] - b["root"]
    ca, cb = _curl_vec(a), _curl_vec(b)
    pb = [(b["root"] + db * tb + cb * tb * tb, 0.53 * b["w"] * TOOTH_RAD(tb)) for tb in ts]   # +6%: the swell
    for ta in ts:
        p = a["root"] + da * ta + ca * ta * ta
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
    # v14: where two teeth curl into each other, they curl less (the shorter first, to 30% of its own)
    for i in range(len(teeth)):
        for j in range(i + 1, len(teeth)):
            a, b = teeth[i], teeth[j]
            for _ in range(16):
                if _overlap(a, b)[0] <= tol:
                    break
                for m in sorted((a, b), key=lambda t: t["L"]):
                    if m.get("curl_amt", 0.0) > 0.3 * m.setdefault("ca0", m.get("curl_amt", 0.0)) + 1e-9:
                        m["curl_amt"] = max(m["curl_amt"] * 0.85, 0.3 * m["ca0"])
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


def plan_upper(F):
    """The upper teeth as v12 planned them from the sheet - the front panel's row (each tooth's own width
    and root height), the two behind it, the side panel's teeth behind the corners and one short tooth
    at the left corner - on v12's scale. v14 sets every root on the upper jaw's new edge (_edge_z) and
    moves its tooth with it: the front row's roots already stand where the edge passes, the corner teeth
    rise with it toward the cheek. Returns the teeth in cranium space."""
    rng.seed(1212)                      # v12's seed: the same widths and curls
    up = []
    kmap = TEETH_K
    vg = front_uv(F.hw((0.0, FRONT_UP, GUM_Z)))[1]
    xs = np.linspace(UP_RIGHT_X - 0.03, UP_LEFT_X, 300)
    arc = [(x, float(face_y(x)) + 0.065) for x in xs]
    arc_u = np.array([front_uv(F.hw((x, y, GUM_Z)))[0] for x, y in arc])
    for k, ((ru, rv), (tu, tvv), wpx) in enumerate(SHEET["front_upper"]):
        i = int(np.argmin(np.abs(arc_u - ru)))
        x, y = arc[i]
        root = Vector((x, y, GUM_Z - (rv - SHEET_FRONT_GUM_V) * kmap / FRONT_CAM[2] / U))
        rw = F.hw(root)
        drop = (tvv - rv) / FRONT_CAM[2] * UP_LEN_K                # visible length below the gum (m)
        tw = Vector(((tu - FRONT_CAM[0]) / FRONT_CAM[2], rw.y + 0.08 * drop, rw.z - drop))
        tip = F.wh(tw)
        L = (tip - root).length + 0.03
        c, ca = _curl(k, False)
        up.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L, wpx), "src": "front", "curl": c, "curl_amt": ca})
    for k, ((ru, rv), (tu, tvv), wpx) in enumerate(SHEET["front_upper_behind"]):   # behind the front row
        i = int(np.argmin(np.abs(arc_u - ru)))
        x, y = arc[i]
        root = Vector((x, y + 0.075, GUM_Z + 0.012))
        rw = F.hw(root)
        tz = vg + (tvv - SHEET_FRONT_GUM_V) * kmap
        drop = (tz - front_uv(rw)[1]) / FRONT_CAM[2] * UP_LEN_K / kmap
        tw = Vector(((tu - FRONT_CAM[0]) / FRONT_CAM[2], rw.y + 0.06 * drop, rw.z - drop))
        tip = F.wh(tw)
        L = (tip - root).length + 0.03
        c, ca = _curl(20 + k, False)
        up.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L, wpx), "src": "behind", "curl": c, "curl_amt": ca})
    for k, ((ru, rv), (tu, tvv)) in enumerate(SHEET["side_upper"]):                  # behind the corners
        if ru < 109:
            continue
        far = (tvv - rv) > 30
        x_side = UP_RIGHT_X if far else UP_LEFT_X
        yw, zw = (ru - SIDE_CAM[0]) / SIDE_CAM[2], (SIDE_CAM[1] - rv) / SIDE_CAM[2]
        root = F.wh(Vector((F.hw((x_side, -0.3, 0.0)).x, yw, zw)))
        root = Vector((x_side, root.y + (0.10 if far else 0.0), GUM_Z - 0.006))
        rw = F.hw(root)
        tw = Vector((rw.x + (0.015 if far else -0.012), rw.y + (tu - ru) / SIDE_CAM[2], rw.z - (tvv - rv) / SIDE_CAM[2]))
        tip = F.wh(tw)
        L = (tip - root).length + 0.03
        c, ca = _curl(40 + k, False)
        up.append({"root": root, "tip": tip, "L": L, "w": _tooth_width(L), "src": "far" if far else "side",
                   "curl": c, "curl_amt": ca})
    root = Vector((UP_LEFT_X, -0.44, GUM_Z - 0.006))          # one more short tooth at the left corner
    tip = root + Vector((-0.02, 0.03, -0.20))
    c, ca = _curl(60, False)
    up.append({"root": root, "tip": tip, "L": 0.23, "w": _tooth_width(0.2), "src": "side", "curl": c, "curl_amt": ca})
    # v14: each root onto the edge (it emerges just under the bone), its tooth moved with it
    for t in up:
        dz = float(_edge_z(t["root"].x, t["root"].y)) - 0.008 - t["root"].z
        if t["src"] == "behind":
            dz = max(dz, 0.0)                                  # behind the row: up into the palate, not down
        t["root"].z += dz
        t["tip"].z += dz
    rot = lambda M: M.to_3x3().normalized()
    v_up = (rot(F.Ci) @ Vector((0.0, 1.0, 0.0))).normalized()
    rest = _separate(up, view=v_up, max_move=0.10)
    print("TEETH remaining interpenetration (head units): upper %.3f" % rest)
    for tth in sorted(up, key=lambda d: d["L"])[:2]:
        tth["kind"] = "snapped"
    return up


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
    rest = _separate(lo, view=v_lo, max_slide=0.08)
    print("TEETH remaining interpenetration (head units): lower %.3f" % rest)
    for tth in sorted(lo, key=lambda d: d["L"])[:2]:            # a few teeth snapped (the shortest), as on the sheet
        tth["kind"] = "snapped"
    return lo


# ---------------------------------------------------------------------------
# v15: the posterior teeth lengthened
# ---------------------------------------------------------------------------
POST_LEN_UP, POST_LEN_LO = 0.62, 0.62     # the posterior teeth grow toward the prominent front teeth's length
POST_VAR = (0.80, 1.15)                   # (head units), each by its own factor, and no longer than the row's
POST_CAP_UP, POST_CAP_LO = 0.66, 0.62     # prominent front teeth (v14: upper 0.61, lower 0.57) and a little
PIERCE_FROM = 0.25                        # a tooth's axis is tested from here (above the gum) to its tip
WIDTH_GROW = 0.25                         # a grown tooth then thickens with its length (w ~ L^0.25), so the
                                          # long ones stay fangs, not needles - as far as it stays clear


def _sm(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def posterior_up(t):
    """How far into the mouth an upper tooth stands (0..1): the teeth behind the front row, behind its
    corners and along the far side all of them; of the front row only its near end (the monster's left),
    where it turns back toward the corner over the deep part of the opening. The rest of the front row is
    v14's: its uneven lengths match the sheet's front and three-quarter panels (cranium space)."""
    if t["src"] != "front":
        return 1.0
    return _sm((t["root"].x + 0.10) / 0.18)


def taper_up(t):
    """Toward the back of the mouth the upper teeth shorten again (the sheet's side panel: the rearmost
    are about two thirds of the middle ones)."""
    return 1.0 - 0.30 * _sm((t["root"].y + 0.35) / 0.25)


def posterior_lo(t):
    """How far from the middle of the chin a lower tooth stands, along the rim (t: the chin's middle is at
    0.47): 0 there, 1 from the near side of the chin up the jaw's arm toward the hinge - the teeth the
    three-quarter camera sees round the deep part of the opening."""
    return _sm((abs(t["t"] - 0.47) - 0.02) / 0.10)


def taper_lo(t):
    """Up the arm toward the hinge the lower teeth shorten again (the sheet's side panel)."""
    return 0.65 + 0.35 * _sm((t["t"] - 0.07) / 0.20)


def _axis(t, s0=PIERCE_FROM, n=12):
    d = t["tip"] - t["root"]
    c = _curl_vec(t)
    return [t["root"] + d * s_ + c * s_ * s_ for s_ in np.linspace(s0, 1.0, n)]


def _in_cranium(F, t):
    """A lower tooth (jaw space) as a cranium-space copy, for testing it against the upper row."""
    R = F.J.to_3x3()
    c = dict(t)
    c["root"], c["tip"] = F.J @ t["root"], F.J @ t["tip"]
    c["curl"] = tuple(R @ Vector(t.get("curl", (0.0, 0.0, 0.0))))
    return c


def _place(t, d, L):
    """Set a tooth's direction and its length above the gum."""
    t["tip"] = t["root"] + d * L
    t["L"] = L + 0.03


NUDGE_DEG = (2.5, 5.0, 7.5, 10.0)         # how far a grown tooth may be turned aside to pass another tooth,
GROW_STEP = 0.02                          # bone or tissue (degrees, eight ways round), and its growth step
LEAN_MAX = 15.0                           # an upper tooth leaning back further than this from hanging straight
                                          # down (degrees) hangs straighter as it grows (the sheet's side panel)


def _prefer(t, L):
    """The direction a growing tooth takes at length L: v14's, or for a far-leaning upper tooth, swinging
    from v14's toward its straighter one (dir1) as it grows."""
    if t.get("dir1") is None:
        return t["dir0"]
    f = min(max((L - t["L0"]) / max(t["goal"] - t["L0"], 1e-6), 0.0), 1.0)
    return t["dir0"].slerp(t["dir1"], f).normalized()


def _turns(t, L):
    """The directions a growing tooth may take at length L, nearest first: the preferred one, as it
    stands, then the preferred one turned aside by each of NUDGE_DEG, eight ways round."""
    d0 = _prefer(t, L)
    e1 = d0.orthogonal().normalized()
    e2 = d0.cross(e1).normalized()
    out = [d0, (t["tip"] - t["root"]).normalized()]
    for deg in NUDGE_DEG:
        a = math.radians(deg)
        for k in range(8):
            b = 2.0 * math.pi * k / 8.0
            out.append((d0 * math.cos(a) + (e1 * math.cos(b) + e2 * math.sin(b)) * math.sin(a)).normalized())
    return out


def _near(A, B):
    """Could two teeth (the same space) touch at all? Bounding spheres round them."""
    ra = (A["tip"] - A["root"]).length * 0.5 + _curl_vec(A).length + A["w"]
    rb = (B["tip"] - B["root"]).length * 0.5 + _curl_vec(B).length + B["w"]
    return ((A["root"] + A["tip"]) - (B["root"] + B["tip"])).length * 0.5 < ra + rb


def _pierce_hit(F, t, solids):
    """Where the tooth's axis (above the gum) first runs into one of the solids, with the surface's normal
    there turned against the axis, both in the tooth's space (t['space']); None if it runs into none.
    `solids` maps a space ('c' cranium, 'j' jaw) to BVH trees in that space."""
    pts = _axis(t)
    for space, trees in solids.items():
        if space == t["space"]:
            q, back = pts, None
        elif space == "c":
            q, back = [F.J @ p for p in pts], F.Ji
        else:
            q, back = [F.Ji @ p for p in pts], F.J
        for a, b in zip(q, q[1:]):
            d = b - a
            for tree in trees:
                loc, nrm, _i, _dist = tree.ray_cast(a, d.normalized(), d.length)
                if loc is not None:
                    if nrm.dot(d) > 0.0:
                        nrm = -nrm
                    if back is not None:
                        loc, nrm = back @ loc, back.to_3x3() @ nrm
                    return loc, nrm
    return None


def _pierces(F, t, solids):
    return _pierce_hit(F, t, solids) is not None


def _clear(F, t, teeth, solids, tol, base):
    """Is the tooth clear of every other tooth of both rows (compared in cranium space; a pair may keep the
    interpenetration v14 left it, where that is more than tol) and of bone and tissue (`solids`)?"""
    A = t if t["space"] == "c" else _in_cranium(F, t)
    for b in teeth:
        if b is t:
            continue
        Bq = b if b["space"] == "c" else _in_cranium(F, b)
        if _near(A, Bq) and _overlap(A, Bq)[0] > max(tol, base.get((id(t), id(b)), 0.0) + 1e-4):
            return False
    return _pierce_hit(F, t, solids) is None


def lengthen_posterior(F, up, lo, solids, tol=0.002):
    """v15: the teeth further back in the mouth - behind the upper front row, at its corners and along its
    near half, and from the near side of the chin up the lower jaw's arm - grow toward the prominent
    front teeth's length (POST_LEN_*), each to its own length (POST_VAR), from their v14 roots (so the
    gums round them stay v14's). They grow together, a step (GROW_STEP) at a time, and a step is taken
    only where the whole tooth stays clear of every other tooth and of bone and tissue (`solids`: for each
    row, BVH trees by space); where it would not, the tooth may turn aside a little (NUDGE_DEG), else it
    stops at its last clear length - so no tooth ever crosses another. The other teeth are v14's.
    Returns the grown teeth."""
    r = random.Random(1515)
    grown = []
    for group, target, cap, post, taper, space in ((up, POST_LEN_UP, POST_CAP_UP, posterior_up, taper_up, "c"),
                                                   (lo, POST_LEN_LO, POST_CAP_LO, posterior_lo, taper_lo, "j")):
        for t in group:
            L0 = (t["tip"] - t["root"]).length
            t["L0"], t["dir0"], t["space"], t["w0"] = L0, (t["tip"] - t["root"]).normalized(), space, t["w"]
            goal = min(target * r.uniform(*POST_VAR) * taper(t), cap)
            t["goal"] = L0 + post(t) * (goal - L0)
            if t["goal"] > L0 * 1.02:
                grown.append(t)
    down = (F.Ci.to_3x3().normalized() @ Vector((0.0, 0.0, -1.0))).normalized()      # cranium space
    lean = math.radians(LEAN_MAX)
    for t in grown:
        ang = t["dir0"].angle(down) if t["space"] == "c" else 0.0
        if ang > lean:                                 # the more it grows, the straighter it hangs (at most
            a = min(0.7, (t["goal"] - t["L0"]) / t["goal"])                  # 70% of the way to LEAN_MAX)
            t["dir1"] = down.slerp(t["dir0"], (lean + (ang - lean) * (1.0 - a)) / ang).normalized()
    teeth = up + lo
    cr = {id(t): (t if t["space"] == "c" else _in_cranium(F, t)) for t in teeth}
    base = {}                                  # v14's own interpenetrations, pair by pair
    for t in grown:
        for b in teeth:
            if b is not t and _near(cr[id(t)], cr[id(b)]):
                base[(id(t), id(b))] = base[(id(b), id(t))] = _overlap(cr[id(t)], cr[id(b)])[0]
    active = list(grown)
    while active:                                  # a blocked tooth tries again next round (another may have
        moved = False                              # turned out of its way), until a round moves none
        for t in list(active):
            L1 = min((t["tip"] - t["root"]).length + GROW_STEP, t["goal"])
            keep = (t["tip"].copy(), t["L"], t["w"])
            for d in _turns(t, L1):
                _place(t, d, L1)
                if _clear(F, t, teeth, solids["up" if t["space"] == "c" else "lo"], tol, base):
                    moved = True
                    if L1 >= t["goal"] - 1e-9:
                        active.remove(t)
                    break
            else:
                t["tip"], t["L"], t["w"] = keep        # blocked every way: it keeps its last clear length
        if not moved:
            break
    for t in grown:                                    # then each thickens with its length, as far as it
        w1 = t["w0"] * ((t["tip"] - t["root"]).length / t["L0"]) ** WIDTH_GROW      # stays clear
        for f in (1.0, 0.67, 0.33, 0.0):
            t["w"] = t["w0"] + (w1 - t["w0"]) * f
            if f == 0.0 or _clear(F, t, teeth, solids["up" if t["space"] == "c" else "lo"], tol, base):
                break
    return [t for t in grown if (t["tip"] - t["root"]).length > t["L0"] + 1e-6]       # those that could grow


def build_teeth_v15(M, col, sk, jaw, F, solids):
    """v15: both rows as v14 planned them, the posterior teeth lengthened, built as v14 builds them (same
    random sequence: the teeth that do not grow come out as v14's)."""
    up = plan_upper(F)
    lo = plan_lower(F)
    grown = lengthen_posterior(F, up, lo, solids)
    for group, name in ((up, "upper"), (lo, "lower")):
        g = [t for t in group if any(t is q for q in grown)]
        print("TEETH %s: %d of %d lengthened, by %s" % (name, len(g), len(group), ", ".join(
            "%.2f->%.2f" % (t["L0"], (t["tip"] - t["root"]).length) for t in sorted(g, key=lambda d: d["L0"]))))
    for group, parent, name, curl in ((up, sk, "Teeth_Upper", (0, 1, 0.2)), (lo, jaw, "Teeth_Lower", (0, 0.8, -0.3))):
        bm, layer = D.new_tooth_bm()
        for tth in group:
            d = tth["tip"] - tth["root"]
            Lb = d.length
            base = tth["root"] - d.normalized() * 0.03                 # root set into the gum
            tusk(bm, layer, base, d, Lb + 0.03, tth["w"], tth.get("kind", "fang"), curl_dir=tth.get("curl", curl),
                 curl_amt=tth.get("curl_amt", rng.uniform(0.04, 0.11)))
        D.bm_object(name, bm, col, [M["teeth"]], parent=parent)
    return up, lo, grown


def gums_and_teeth(M, col, sk, jaw, F):
    """Both rows (v14: the upper teeth re-seated on the new upper edge, the lower on the swept rim) and
    their gums."""
    up = plan_upper(F)
    lo = plan_lower(F)
    print("TEETH upper %d lower %d (front %d, side %d)" % (len(up), len(lo), sum(t["src"] == "front" for t in lo),
                                                            sum(t["src"] == "side" for t in lo)))
    for group, parent, name, curl in ((up, sk, "Teeth_Upper", (0, 1, 0.2)), (lo, jaw, "Teeth_Lower", (0, 0.8, -0.3))):
        bm, layer = D.new_tooth_bm()
        for tth in group:
            d = tth["tip"] - tth["root"]
            Lb = d.length
            base = tth["root"] - d.normalized() * 0.03                 # root set into the gum
            tusk(bm, layer, base, d, Lb + 0.03, tth["w"], tth.get("kind", "fang"), curl_dir=tth.get("curl", curl),
                 curl_amt=tth.get("curl_amt", rng.uniform(0.04, 0.11)))
        D.bm_object(name, bm, col, [M["teeth"]], parent=parent)

    # gums: not a smooth tube along the jaws but irregular collars of tissue around each tooth's base,
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

    side_edge = lambda x, ys: [Vector((x + 0.01, y, float(_edge_z(x, y)) - 0.012)) for y in ys]
    up_path = (side_edge(UP_RIGHT_X, np.linspace(-0.12, -0.42, 7)) +
               [Vector((x,) + gum_front(x)) + Vector((0, 0.008, 0.004)) for x in np.linspace(UP_RIGHT_X, UP_LEFT_X, 26)] +
               side_edge(UP_LEFT_X, np.linspace(-0.50, -0.10, 8)))
    gb = bmesh.new()
    collars(gb, up, 71, 0.62)
    band(gb, up_path, 0.014, 72)                                   # along the new, uneven edge
    D.bm_object("Gums_Upper", gb, col, [M["tissue"]], parent=sk)
    P = jaw_path()
    # the gum along the jaw's edge, outside the tooth row: the sheet's thin red line down both arms and
    # round the chin (v13: on the rim's outer edge, where it shows, and torn less - still uneven, with gaps)
    lo_path = [_rim_point(P, t, inward=-0.015, dz=0.008)[0] for t in np.linspace(0.03, 0.97, 72)]
    gb = bmesh.new()
    collars(gb, lo, 73, 1.0)
    band(gb, lo_path, 0.020, 74, keep=0.78)
    # v14: up both arms, from the chin's corners to the hinges, the gum runs unbroken and fuller - the red
    # line that sweeps the gape's curve down into the chin (the sheet's three-quarter and side panels)
    for t0, t1 in ((0.0, 0.30), (0.70, 1.0)):
        arm = [_rim_point(P, t, inward=-0.022, dz=0.012)[0] for t in np.linspace(t0, t1, 26)]
        D.tube(gb, arm, [0.024 * (0.75 + 0.25 * math.sin(7.0 * i / 25.0 + 1.0)) for i in range(len(arm))], 0,
               sides=7, jitter=0.3, frame_ref=(0, 0, 1))
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


# the free edges of the corner webs, as the sheet's exact side panel shows them (side px, top to bottom;
# None = the upper jaw's edge at that u): the far (right) one seen through the gape, the near (left) one
WEB_FAR = [(122, None), (125, 120), (127, 138), (132, 157), (139, 172), (146, 186)]
WEB_NEAR = [(155, None), (160, 104), (165, 116), (170, 127)]


def _side_to_cranium(F, u, v, x_c):
    """A side-panel pixel -> the cranium-space point on its line of sight at cranium x = x_c."""
    xw = F.hw((x_c, 0.0, 0.0)).x
    for _ in range(3):
        c = F.wh(Vector((xw, (u - SIDE_CAM[0]) / SIDE_CAM[2], (SIDE_CAM[1] - v) / SIDE_CAM[2])))
        xw += (x_c - c.x) * U
    return c


def _resample(pts, n):
    pts = [Vector(p) for p in pts]
    seg = [0.0]
    for a, b in zip(pts, pts[1:]):
        seg.append(seg[-1] + (b - a).length)
    out = []
    for t in np.linspace(0.0, seg[-1], n):
        i = int(np.clip(np.searchsorted(seg, t) - 1, 0, len(pts) - 2))
        f = (t - seg[i]) / max(seg[i + 1] - seg[i], 1e-9)
        out.append(pts[i].lerp(pts[i + 1], f))
    return out


def _corner_web(bm, F, P, jm, s, x_up, pts, t_bot, seed, rows=16, cols=7):
    """One corner of the gape closed by torn tissue: a membrane between its fixed edge (the upper jaw's edge
    from the free edge's top back to the cheek, the rear block's underside down to the hinge, then the lower
    jaw's rim from the hinge down to t_bot) and its free edge (the sheet's side-panel points `pts`)."""
    r = random.Random(seed)
    # free edge, top to bottom, in cranium space on the cheek plane
    free = []
    for u, v in pts:
        if v is None:
            c = _side_to_cranium(F, u, 100.0, x_up)
            free.append(Vector((x_up, c.y, float(_edge_z(x_up, c.y)) - 0.01)))
        else:
            free.append(_side_to_cranium(F, u, v, x_up))
    bot, _ = _rim_point(P, t_bot, inward=0.0, dz=-0.01)
    free.append(jm @ bot)
    # fixed edge: along the upper jaw's edge back to the cheek, down the rear block's underside to the
    # hinge, then down the lower jaw's rim
    y0 = free[0].y
    fixed = [Vector((x_up, y, float(_edge_z(x_up, y)) - 0.01)) for y in np.linspace(y0, 0.10, 6)]
    fixed += [Vector((x_up, 0.10 + 0.26 * f, -0.06 - 0.21 * f)) for f in (0.35, 0.7, 1.0)]
    t_top = 0.985 if s < 0 else 0.015
    fixed += [jm @ _rim_point(P, t, inward=0.0, dz=-0.01)[0] for t in np.linspace(t_top, t_bot, 8)]
    A, Bf = _resample(free, rows), _resample(fixed, rows)
    grid = []
    for a, (p, q) in enumerate(zip(A, Bf)):
        row = []
        for b in np.linspace(0.0, 1.0, cols):
            w = math.sin(math.pi * b) * math.sin(math.pi * a / (rows - 1))
            row.append(p.lerp(q, b) + Vector((-s * 0.03 * w + r.uniform(-0.006, 0.006), r.uniform(-0.006, 0.006),
                                              r.uniform(-0.006, 0.006))))
        grid.append(row)
    _sheet(bm, grid, holes=0.05, seed=seed)
    return A


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
    # v14: the mouth's rear corners. Not v8-v13's flat walls down the whole side of the gape (seen from
    # the side, a straight-edged sheet across the mouth) but torn tissue closing each corner: fixed along
    # the upper jaw's edge, round the hinge and down the lower jaw's rim; its free edge is read off the
    # sheet's exact side panel (the dark corner of the gape against the open front), so the opening's
    # back is a curve from the upper jaw down into the lower jaw
    ib = bmesh.new()
    edges = [_corner_web(ib, F, P, jm, s_, x_up, pts, t_bot, seed=51 + s_)
             for s_, x_up, pts, t_bot in ((-1, UP_RIGHT_X + 0.02, WEB_FAR, 0.66), (1, UP_LEFT_X - 0.02, WEB_NEAR, 0.07))]
    walls = D.bm_object("Mouth_Inner_Walls", ib, col, [M["tissue"]], parent=sk)
    sol = walls.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.015
    D.apply_modifiers(walls)
    # the torn edge of each web: a ragged roll of exposed tissue along its free edge - the red line that
    # follows the gape's curve from the upper jaw down into the lower jaw (sheet: side and three-quarter)
    rb = bmesh.new()
    er = random.Random(61)
    for edge, r0 in zip(edges, (0.010, 0.024)):
        pts = edge[1:-1]
        D.tube(rb, pts, [r0 * er.uniform(0.6, 1.3) * (0.5 + 0.5 * math.sin(math.pi * (i + 1) / (len(pts) + 1)))
                         for i in range(len(pts))], 0, sides=7, jitter=0.35)
    D.bm_object("Mouth_Corner_Rims", rb, col, [M["tissue"]], parent=sk)
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
    """The tiny red pupils: v12's (x, z, size), set deeper into the sockets (EYES)."""
    ebm = bmesh.new()
    for (ex, ez, k, recess), y12 in zip(EYES, EYES_V12_Y):
        c = Vector((ex, y12 + recess, ez))
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


MOUTH_OBJECTS = ("Jaw", "Teeth_Upper", "Teeth_Lower", "Gums_Upper", "Gums_Lower", "Mouth_Cheek_Flesh",
                 "Mouth_Inner_Walls", "Mouth_Floor", "Jaw_Strands", "Eyes")      # rebuilt by v14 (and
                                                                                   # Mouth_Corner_Rims added)


def rebuild_cranium(M, col, sk):
    """Rebuild the cranium with v14's upper jaw edge, brows and sockets. It is rebuilt from the same SDF
    with only those changed; every new vertex that coincides with one of the old mesh's takes its
    attributes, so away from the changes the cranium stays as it was to the bit. The object (transform,
    children) is kept; only its mesh is swapped. Returns the old and new vertex arrays."""
    from scipy.spatial import cKDTree
    global FAST
    FAST = False
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
    return a, b


def build_head_v14(M, col, sk, location, rotation, open_deg, roll_deg, scale=0.60, fast=False):
    """v14 on v13's head: the upper jaw's edge, the brows and the sockets re-cut in the cranium; the lower
    jaw, both rows of teeth, the gums, the mouth's tissue and the pupils rebuilt. Returns (old, new)
    cranium vertices for the caller's checks."""
    global U, FAST
    U = scale
    F = Frame(location, rotation, scale, open_deg, roll_deg)
    solve_upper_edge(F)
    verts = rebuild_cranium(M, col, sk)
    U, FAST = scale, fast
    solve_jaw(F)
    print("JAW open %.2f deg, length %.3f u (tooth row %.3f), rim top %.3f, chin x %.3f; %d rim samples"
          % (JAW["open"], JAW["L"], JAW["L_top"], JAW["top"], JAW["chin_x"], len(JAW["samples"])))
    jaw = build_jaw(col, M, sk, F)
    mouth_flesh(M, col, sk, jaw, F)
    gums_and_teeth(M, col, sk, jaw, F)
    eyes(M, col, sk)
    bpy.context.view_layer.update()
    return verts
