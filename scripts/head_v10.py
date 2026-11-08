"""
v10 head (approved-head replication; head_v9.py and the body are kept unchanged). The approved
sheet's head - its front, three-quarter and exact-side panels and the close-up, mouth-interior,
jaw-comparison and side-angle detail panels - is rebuilt from different base shapes, not
re-detailed from v9's:

- cranium: a planar, angular block instead of v9's rounded loft. It has a vertical face plate,
  a brow leaning back, a forehead slope and a crown that rise to an off-centre ridge (the front
  view's peaked top), sides narrowing toward the back, and a steep back. The monster's right-front
  corner drops. Square, stepped eye sockets are cut into the face plate. The edges are broken by
  stepped notches and proud chunks, and the whole shell is a mosaic of rectangular blocks that
  step in and out, some missing. The left side behind the mouth (and, smaller, the right side) is
  torn open onto red flesh.
- upper jaw: the face plate's lower edge is a broken rim over a vaulted palate, with a thick,
  lobed maroon gum along it from which the upper fangs hang.
- lower jaw: a broad, skeletal U of blocky bone - two rami joined by a wide chin, not a narrow V.
  It is asymmetric (the right side bulges, the rim dips and twists, one corner of the chin is
  broken), with a thick gum along the rim and a sagging flesh floor.
- teeth: 36 as in v9 (16 upper, 20 lower), thick-rooted, faceted fangs, crowded, overlapping and
  leaning irregularly; the long fangs at the front.
- tissue: the mouth is lined with dark maroon flesh (gums, cheek walls torn at the gape, strands),
  black only deep in the throat.

Space: the cranium's local space in head units (1 unit = HEAD_SCALE metres), origin at the middle
of the skull's length at the upper gum line, front -Y, Z up; the jaw is parented to the cranium and
pivots at its own origin (the hinge), extending along its -Y.
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

import blocks_v10 as B
import monster_detail as D
import sculpt as SC

rng = random.Random(1010)
U = 0.60
FAST = False
HINGE = Vector((0.0, 0.60, -0.20))
DISLOCATE = Vector((0.0, 0.0, -0.05))
FACE_Y = -0.70                       # the face plate
RIDGE_X = 0.07                       # the crest of the forehead and crown (front view: off-centre peak)
NOSE_X = -0.09                       # the face's vertical nasal ridge between the sockets
SLOPE_L, SLOPE_R = 0.30, 0.65        # how fast the face recedes from it to the left and to the right


def face_y(x):
    """The face plate's depth at x (the wedge)."""
    return FACE_Y + np.where(np.asarray(x) > NOSE_X, SLOPE_L, SLOPE_R) * np.abs(np.asarray(x) - NOSE_X)
GUM_Z = -0.055                       # the face plate's lower edge (upper gum line)

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
# Lower jaw: a broad, skeletal U of blocky bone (jaw-local: hinge at the origin, chin toward -Y)
# ---------------------------------------------------------------------------
# rim centre line, rear to front: (y, half width to the rim's centre line) - wide for most of its
# length, as the front and three-quarter views' mouth outline, then a broad rounded chin
JAW_SIDE = [(0.04, 0.318), (-0.15, 0.388), (-0.45, 0.420), (-0.75, 0.395), (-0.93, 0.338), (-1.00, 0.305)]
CHIN_C, CHIN_R = (0.018, -1.00), (0.305, 0.255)
RIM_W = (0.118, 0.100)            # rim width, rear -> chin
RIM_TOP = (0.048, 0.034)          # rim top (z), rear -> chin
RIM_BOT = (-0.120, -0.088)        # rim underside (z), rear -> chin


def _bulge(y, s):
    """Asymmetry: the right side (s = -1) bulges out around its middle; the left rim stays lean."""
    return 0.040 * math.exp(-((y + 0.48) / 0.22) ** 2) if s < 0 else -0.010 * math.exp(-((y + 0.70) / 0.25) ** 2)


def _dip(y, s):
    """The left rim dips (broken down) toward the front; the right one rises a little."""
    return np.where(s > 0, -0.030 * np.exp(-((y + 0.62) / 0.18) ** 2), 0.010 * np.exp(-((y + 0.30) / 0.2) ** 2))


def jaw_path():
    """U centre line as (x, y, t) points, t = 0 at the left rear end, 1 at the right rear end."""
    left = [(rw + _bulge(y, 1), y) for y, rw in JAW_SIDE]
    arc = [(CHIN_C[0] + CHIN_R[0] * math.cos(a), CHIN_C[1] - CHIN_R[1] * math.sin(a))
           for a in np.linspace(0.0, math.pi, 15)[1:-1]]
    right = [(-(rw + _bulge(y, -1)), y) for y, rw in reversed(JAW_SIDE)]
    pts = np.array(left + arc + right, float)
    seg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    return np.c_[pts, seg / seg[-1]]


def _rim_params(t, x, y):
    """Rim width, top and underside at path parameter t (0..1, chin at 0.5)."""
    f = 1.0 - np.abs(t - 0.5) * 2.0                      # 0 at the rear ends, 1 at the chin
    s = np.where(np.asarray(x) > 0, 1.0, -1.0)
    w = RIM_W[0] + (RIM_W[1] - RIM_W[0]) * f
    top = RIM_TOP[0] + (RIM_TOP[1] - RIM_TOP[0]) * f + _dip(np.asarray(y), s)
    bot = RIM_BOT[0] + (RIM_BOT[1] - RIM_BOT[0]) * f
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
    for s in (1, -1):                                     # rami up to the torn-out condyles at the hinge
        F = B.union(F, B.box(G, (s * 0.318, 0.015, -0.025), (0.058, 0.065, 0.105), B.rot(0, s * 6, 0)))
    for c, h, r in JAW_CHUNKS:
        F = B.union(F, B.inter(B.box(G, c, h, B.rot(*r)), rim - 0.045))
    for c, h, r in JAW_NOTCHES:
        F = B.sub(F, B.box(G, c, h, B.rot(*r)))
    return F


JAW_NOTCHES = [((-0.20, -1.24, 0.03), (0.09, 0.07, 0.06), (0, 0, 20)),     # the chin's right corner broken off
               ((0.46, -0.60, 0.05), (0.05, 0.10, 0.04), (0, 0, 0)),       # the left rim broken down
               ((-0.47, -0.30, -0.13), (0.06, 0.09, 0.05), (0, 0, 0)),     # underside chips
               ((0.39, -0.88, -0.11), (0.05, 0.07, 0.04), (0, 0, 10)),
               ((0.10, -1.27, -0.09), (0.07, 0.05, 0.04), (0, 0, 0)),
               ((-0.44, -0.75, 0.05), (0.04, 0.06, 0.03), (0, 0, 0))]
JAW_CHUNKS = [((-0.49, -0.48, -0.03), (0.05, 0.10, 0.07), (0, 0, 4)),      # the right side's bulge, blocky
              ((0.40, -0.25, -0.10), (0.05, 0.08, 0.05), (0, 0, -6)),
              ((-0.12, -1.27, -0.04), (0.06, 0.05, 0.06), (0, 0, 12))]


def build_jaw(col, M, sk, open_deg, roll_deg):
    G = B.Grid((-0.62, -1.42, -0.30), (0.62, 0.18, 0.22), 0.009 if not FAST else 0.015)
    F = jaw_sdf(G)
    F, tid, val, seam, hole = B.tiles(G, F, size=0.068, seed=21, shell=0.05, raised=(0.0, 0.020),
                                      sunken=(-0.015, 0.0), p_sunk=0.30, p_missing=0.08, missing=-0.035,
                                      tilt=0.12, seam=0.0055, seam_depth=0.009, wobble=0.012)
    jaw = B.to_object("Jaw", F, G, col, [M["rust"]])
    S = SC.Surf(jaw, U)
    co = S.co / U
    S.a["flake"] = B.sample(G, val, co)
    S.a["crack"] = np.clip(B.sample(G, seam, co) * 1.4, 0, 1)
    S.a["pit"] = B.sample(G, hole, co)
    S.a["socket"] = np.zeros(S.n)
    S.a_socket_final = S.a["socket"]
    if not FAST:
        rot = Matrix.Rotation(math.radians(open_deg), 3, 'X')
        down_local = rot.inverted() @ Vector((0, 0, -1))
        SC.blood(S, 76, drips=6, near=0.03, down=tuple(down_local))
    SC.finish(S, jaw, decimate_ratio=1.0, sharp_deg=30.0)
    jaw.parent = sk
    jaw.matrix_parent_inverse = Matrix.Identity(4)
    jaw.location = HINGE + DISLOCATE
    jaw.rotation_euler = (math.radians(open_deg), math.radians(-roll_deg), math.radians(1.5))
    bpy.context.view_layer.update()
    return jaw


# ---------------------------------------------------------------------------
# Teeth: thick-rooted, faceted fangs
# ---------------------------------------------------------------------------
def tusk(bm, layer, base, direction, length, width, kind, curl_dir=None, curl_amt=None, sides=7):
    """Faceted conical fang: a full, slightly swollen root narrowing to a sharp point (flat facets,
    as the sheet's carved-looking teeth), curved toward `curl_dir`; 'snapped' teeth end in a tilted
    fracture. Colour attribute: (t root->tip, blood, decay, tint)."""
    d = Vector(direction).normalized()
    side = Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, d) @ d.orthogonal().normalized()
    fwd = d.cross(side).normalized()
    depth = width * rng.uniform(0.80, 0.94)
    n = sides
    prof = [(math.cos(2 * math.pi * k / n + 0.3) * width / 2 * rng.uniform(0.90, 1.08),
             math.sin(2 * math.pi * k / n + 0.3) * depth / 2 * rng.uniform(0.90, 1.08)) for k in range(n)]
    c_dir = Vector(curl_dir) if curl_dir is not None else side
    c_dir = c_dir - d * c_dir.dot(d)
    if c_dir.length < 1e-6:
        c_dir = side
    curl = c_dir.normalized() * length * (curl_amt if curl_amt is not None else rng.uniform(0.06, 0.14))
    cut = rng.uniform(0.55, 0.75) if kind == "snapped" else 1.0
    ts = [-0.18, 0.0, 0.10, 0.24, 0.40, 0.56, 0.72, 0.85, 0.94]
    rad = lambda t: (1.0 - max(t, 0.0)) ** 0.95 * (1.0 + 0.12 * math.sin(math.pi * min(max(t, 0.0) / 0.3, 1.0)))
    ts = [t for t in ts if t < cut - 0.02] + ([cut] if cut < 1.0 else [])
    blood = min(1.0, rng.choice([0.0, 0.0, 0.0, 0.2, 0.3]) * rng.uniform(0.7, 1.2))
    decay, tint = rng.random() ** 1.6, rng.random()
    twist = rng.uniform(-0.25, 0.25)
    rings = []
    for t in ts:
        c = Vector(base) + d * length * t + curl * max(t, 0.0) ** 2
        sc = rad(t) if t >= 0 else 0.95
        a = twist * max(t, 0.0)
        ring = []
        for x, y in prof:
            xr, yr = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
            ring.append(c + side * xr * sc + fwd * yr * sc)
        rings.append(ring)
    if cut < 1.0:
        tilt = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)).normalized()
        c = Vector(base) + d * length * cut + curl * cut ** 2
        rings[-1] = [p + d * (p - c).dot(tilt) * rng.uniform(0.5, 1.0) for p in rings[-1]]
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


def _tilted(d, ax, ay):
    return Matrix.Rotation(math.radians(ay), 3, 'Y') @ (Matrix.Rotation(math.radians(ax), 3, 'X') @ Vector(d))


# Upper teeth (16): 9 across the front of the snout - crowded, uneven gaps, the longest fangs right
# of the middle (the monster's right, as the front view) - and 4 + 3 along the sides behind the
# corners. (x along the front, kind, length, root width, tilt about x, tilt about y, curl)
UPPER_FRONT = [(-0.338, "fang", 0.34, 0.118, -8, -21, 0.18), (-0.262, "fang", 0.60, 0.140, 4, 9, 0.10),
               (-0.200, "snapped", 0.30, 0.118, -6, -4, 0.04), (-0.142, "fang", 0.76, 0.152, 9, 4, 0.12),
               (-0.080, "fang", 0.46, 0.124, -7, -11, 0.16), (-0.012, "fang", 0.66, 0.140, 6, 7, 0.10),
               (0.088, "fang", 0.36, 0.116, -10, -9, 0.20), (0.162, "fang", 0.58, 0.134, 3, 15, 0.12),
               (0.268, "fang", 0.40, 0.120, 8, 22, 0.18)]
UPPER_SIDES = {1: [(-0.565, "fang", 0.56, 0.130, 13), (-0.47, "fang", 0.44, 0.120, -8), (-0.37, "snapped", 0.28, 0.112, 5),
                   (-0.25, "fang", 0.38, 0.112, -12)],
               -1: [(-0.575, "fang", 0.54, 0.130, -12), (-0.46, "fang", 0.48, 0.124, 9), (-0.33, "fang", 0.36, 0.114, -5)]}
# Lower teeth (20) by position along the U rim (0 = left rear end, 0.5 = chin, 1 = right rear end):
# a dense, uneven fan, the long lower fangs at the chin's corners. (t, kind, length, root width, lean)
LOWER = [(0.17, "fang", 0.30, 0.104, 6), (0.215, "fang", 0.40, 0.114, -8), (0.25, "snapped", 0.26, 0.110, 4),
         (0.285, "fang", 0.46, 0.122, -11), (0.32, "fang", 0.38, 0.116, 9), (0.352, "fang", 0.52, 0.128, -6),
         (0.385, "fang", 0.60, 0.136, 12), (0.418, "fang", 0.46, 0.124, -9), (0.45, "fang", 0.40, 0.118, 5),
         (0.488, "fang", 0.50, 0.126, -4), (0.522, "snapped", 0.30, 0.118, 10), (0.555, "fang", 0.56, 0.132, -12),
         (0.592, "fang", 0.64, 0.138, 7), (0.628, "fang", 0.44, 0.122, -6), (0.66, "fang", 0.52, 0.126, 11),
         (0.695, "fang", 0.38, 0.116, -9), (0.73, "fang", 0.46, 0.120, 6), (0.765, "snapped", 0.28, 0.110, -5),
         (0.80, "fang", 0.40, 0.112, 8), (0.84, "fang", 0.30, 0.104, -7)]
FRONT_UP = FACE_Y + 0.072                 # upper gum line just behind the face plate
SIDE_UP = 0.392                           # and along the sides


def _path_at(P, t):
    """Point, tangent and inward normal (toward the U's inside) on the jaw path at parameter t."""
    i = int(np.clip(np.searchsorted(P[:, 2], t) - 1, 0, len(P) - 2))
    a, b = P[i], P[i + 1]
    f = (t - a[2]) / max(b[2] - a[2], 1e-9)
    x, y = a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])
    tx, ty = b[0] - a[0], b[1] - a[1]
    L = math.hypot(tx, ty)
    tx, ty = tx / L, ty / L
    nx, ny = -ty, tx                                    # left normal of the travel direction
    cx, cy = CHIN_C
    if (cx - x) * nx + (cy * 0.6 - y * 0.6) * ny < 0 and abs(x) > 0.05:
        nx, ny = -nx, -ny
    if abs(x) <= 0.05 or y < CHIN_C[1]:                 # at the chin: inward is back toward the U
        nx, ny = (cx - x), (cy + 0.25 - y)
        L = math.hypot(nx, ny)
        nx, ny = nx / L, ny / L
    return x, y, (tx, ty), (nx, ny)


def gums_and_teeth(M, col, sk, jaw):
    bm, layer = D.new_tooth_bm()
    upper_bases = []
    for x, kind, L, w, ax, ay, cu in UPPER_FRONT:              # hang down from the face plate's rim
        base = Vector((x, FRONT_UP + rng.uniform(-0.025, 0.015), GUM_Z - 0.012 + rng.uniform(-0.01, 0.01)))
        upper_bases.append(base)
        tusk(bm, layer, base, _tilted((0, -0.08, -1), 0.7 * ax, ay), L, w, kind, curl_dir=(0, 1, 0), curl_amt=cu)
    for sx, teeth in UPPER_SIDES.items():
        for y, kind, L, w, ay in teeth:
            base = Vector((sx * (SIDE_UP - 0.01 * rng.random()), y + rng.uniform(-0.015, 0.015), GUM_Z - 0.010))
            upper_bases.append(base)
            tusk(bm, layer, base, _tilted((-sx * 0.10, -0.05, -1), rng.uniform(-12, 12), ay), L, w, kind,
                 curl_dir=(-sx, 0.3, 0), curl_amt=rng.uniform(0.06, 0.16))
    D.bm_object("Teeth_Upper", bm, col, [M["teeth"]], parent=sk)

    P = jaw_path()
    bm, layer = D.new_tooth_bm()
    lower_bases = []
    for t, kind, L, w, lean in LOWER:
        x, y, tan, nin = _path_at(P, t)
        ww, top, _ = _rim_params(np.array(t), np.array(x), np.array(y))
        base = Vector((x + nin[0] * 0.022, y + nin[1] * 0.022, float(top) + 0.004))
        lower_bases.append(base)
        dvec = Vector((nin[0] * 0.16, nin[1] * 0.16 + 0.24, 1.0))
        tusk(bm, layer, base, _tilted(dvec, rng.uniform(-10, 10), lean), L, w, kind,
             curl_dir=(nin[0], nin[1] + 0.6, 0), curl_amt=rng.uniform(0.06, 0.16))
    D.bm_object("Teeth_Lower", bm, col, [M["teeth"]], parent=jaw)

    # gums: thick, lobed maroon cushions, swelling around each root
    def lobed(path, bases, r0, r1):
        out = []
        for p in path:
            near = min((p - b).length for b in bases)
            out.append(rng.uniform(r0, r0 + 0.008) + r1 * math.exp(-(near / 0.045) ** 2))
        return out

    up_path = ([Vector((SIDE_UP + 0.012, y, GUM_Z - 0.004)) for y in np.linspace(-0.20, -0.60, 9)] +
               [Vector((x, FRONT_UP + 0.008, GUM_Z - 0.010 + 0.008 * math.sin(9 * x))) for x in np.linspace(0.33, -0.38, 17)] +
               [Vector((-SIDE_UP - 0.012, y, GUM_Z - 0.004)) for y in np.linspace(-0.60, -0.24, 8)])
    gb = bmesh.new()
    D.tube(gb, up_path, lobed(up_path, upper_bases, 0.030, 0.026), 0, sides=9, jitter=0.20, frame_ref=(0, 0, 1))
    D.bm_object("Gums_Upper", gb, col, [M["tissue"]], parent=sk)
    lo_path = []
    for t in np.linspace(0.06, 0.94, 46):
        x, y, tan, nin = _path_at(P, t)
        _, top, _ = _rim_params(np.array(t), np.array(x), np.array(y))
        lo_path.append(Vector((x + nin[0] * 0.030, y + nin[1] * 0.030, float(top) - 0.004)))
    gb = bmesh.new()
    D.tube(gb, lo_path, lobed(lo_path, lower_bases, 0.026, 0.024), 0, sides=9, jitter=0.20, frame_ref=(0, 0, 1))
    D.bm_object("Gums_Lower", gb, col, [M["tissue"]], parent=jaw)


# ---------------------------------------------------------------------------
# Flesh: torn cheek walls at the gape, the jaw's floor, flesh in the torn skull, strands, throat
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


def mouth_flesh(M, col, sk, jaw):
    jm = jaw.matrix_basis                                    # jaw-local -> cranium-local
    P = jaw_path()
    wb = bmesh.new()
    for s in (1, -1):                                        # cheek walls from the upper jaw's sides to the rim
        grid = []
        for i, u in enumerate(np.linspace(0.0, 1.0, 14)):
            ty = 0.34 - u * 0.66                             # skull side: from the hinge forward
            top = Vector((s * (SIDE_UP - 0.02), ty, GUM_Z + 0.01))
            t = 0.04 + u * 0.24 if s > 0 else 0.96 - u * 0.24
            x, y, tan, nin = _path_at(P, t)
            _, rtop, _ = _rim_params(np.array(t), np.array(x), np.array(y))
            bot = jm @ Vector((x + nin[0] * 0.04, y + nin[1] * 0.04, float(rtop) - 0.01))
            row = []
            for j, v in enumerate(np.linspace(0.0, 1.0, 9)):
                sag = (0.05 + 0.03 * math.sin(5 * u + 2 * v)) * math.sin(math.pi * v)
                p = top.lerp(bot, v) + Vector((-s * sag, rng.uniform(-0.006, 0.006), rng.uniform(-0.006, 0.006)))
                row.append(p)
            grid.append(row)
        _sheet(wb, grid, holes=0.10, seed=31 + s, edge_tear=0.18)
    walls = D.bm_object("Mouth_Cheek_Flesh", wb, col, [M["tissue"]], parent=sk)
    sol = walls.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.018
    D.apply_modifiers(walls)
    fb = bmesh.new()                                         # the jaw's sagging flesh floor inside the U
    grid = []
    for i, y in enumerate(np.linspace(-0.05, -1.04, 16)):
        tl = np.interp(y, P[:16, 1][::-1], P[:16, 2][::-1])
        xl, yl, _, nl = _path_at(P, float(tl))
        xr, yr, _, nr = _path_at(P, 1.0 - float(tl))
        row = []
        for j, v in enumerate(np.linspace(0.0, 1.0, 11)):
            x = (xl + nl[0] * 0.05) * (1 - v) + (xr + nr[0] * 0.05) * v
            z = -0.035 - 0.06 * math.sin(math.pi * v) - 0.02 * math.sin(3 * y)
            row.append(Vector((x, y, z + rng.uniform(-0.006, 0.006))))
        grid.append(row)
    _sheet(fb, grid, holes=0.05, seed=41)
    floor = D.bm_object("Jaw_Flesh_Floor", fb, col, [M["tissue"]], parent=jaw)
    sol = floor.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.02
    D.apply_modifiers(floor)
    tb = bmesh.new()                                         # red flesh in the torn cheeks: a dark backing
    for (cx, cy, cz), (hx, hy, hz), _ in TEARS:              # with torn cords hanging across the hole
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
                pts = pts[:rng.randint(2, 4)]                # snapped, hanging
            D.tube(tb, pts, [rng.uniform(0.012, 0.026)] * len(pts), 0, sides=6, jitter=0.35)
    D.bm_object("Torn_Flesh", tb, col, [M["tissue"]], parent=sk)
    sb = bmesh.new()                                         # sagging strands between the jaws
    for s in (1, -1):
        for k, (ty, t, r0, broken) in enumerate(((0.30, 0.06, 0.020, False), (0.14, 0.12, 0.016, False),
                                                 (-0.02, 0.18, 0.014, True), (-0.18, 0.24, 0.012, s > 0))):
            a = Vector((s * (SIDE_UP - 0.04), ty, GUM_Z - 0.01))
            tt = t if s > 0 else 1.0 - t
            x, y, _, nin = _path_at(P, tt)
            b = jm @ Vector((x + nin[0] * 0.05, y + nin[1] * 0.05, 0.02))
            pts = []
            for i in range(7):
                f = i / 6
                if broken and f > 0.62:
                    break
                pts.append(a.lerp(b, f) + Vector((-s * 0.03 * math.sin(math.pi * f), rng.uniform(-0.01, 0.01),
                                                  -0.05 * math.sin(math.pi * f))))
            D.tube(sb, pts, [r0 * (1.0 - 0.35 * math.sin(math.pi * i / 6)) for i in range(len(pts))], 0, sides=6, jitter=0.3)
    D.bm_object("Jaw_Strands", sb, col, [M["tissue"]], parent=sk)
    pb = bmesh.new()                                         # palate ridges (rugae) on the vault
    for i in range(8):
        y = -0.50 + i * 0.075
        hw = 0.25 - i * 0.008
        pts = [Vector((x, y + 0.02 * math.sin(x * 9 + i), GUM_Z + 0.135)) for x in (-hw, -hw / 2, 0, hw / 2, hw)]
        D.tube(pb, pts, [0.012, 0.02, 0.016, 0.02, 0.012], 0, sides=5, jitter=0.25)
    D.bm_object("Palate", pb, col, [M["tissue"]], parent=sk)
    tb = bmesh.new()                                         # ribbed throat receding into the body
    path = [Vector((0, 0.30, -0.06)), Vector((0, 0.42, -0.16)), Vector((0, 0.52, -0.28)), Vector((0, 0.58, -0.40))]
    rings = []
    for i, p in enumerate(path):
        for sub_ in range(3):
            if i == len(path) - 1 and sub_:
                break
            q = p if i == len(path) - 1 else p.lerp(path[i + 1], sub_ / 3)
            r = (0.25 - 0.04 * (i + sub_ / 3)) * (1.0 if sub_ % 2 == 0 else 0.86)
            rings.append([q + Vector((math.cos(a) * r, 0, math.sin(a) * r * 0.75)) for a in [2 * math.pi * k / 12 for k in range(12)]])
    rr = [[tb.verts.new(p) for p in ring] for ring in rings]
    for a, b in zip(rr, rr[1:]):
        for k in range(12):
            tb.faces.new((a[k], a[(k + 1) % 12], b[(k + 1) % 12], b[k]))
    tb.faces.new(rr[-1])
    bmesh.ops.reverse_faces(tb, faces=tb.faces)
    D.bm_object("Throat", tb, col, [M["throat"]], parent=sk)


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
    global U, FAST
    U, FAST = scale, fast
    sk = build_skull(col, M)
    jaw = build_jaw(col, M, sk, open_deg, roll_deg)
    eyes(M, col, sk)
    mouth_flesh(M, col, sk, jaw)
    gums_and_teeth(M, col, sk, jaw)
    crown_bracket(col, M["bar"], sk)
    sk.location, sk.rotation_euler = location, rotation
    sk.scale = (scale, scale, scale)
    bpy.context.view_layer.update()
    return sk, jaw
