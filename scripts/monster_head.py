"""
Head of the OUT THERE monster (v3, R08-directed): skull, hinged jaw, mouth tissue,
mouth interior, gums and teeth. All in cranium-local space (origin = centre of the upper
gum line, front = -Y). The Jaw is parented to the Cranium and pivots at its own origin.

Design (after the Astra R08 reference sheet, keeping the original's dropped jaw)
- Skull: compact blocky barrel built from three stacked rust strata; each band overhangs
  the next, giving R08's layered ledges. Mild asymmetry only.
- Eyes: square, dark, recessed sockets with tiny red square eyes.
- Jaw: heavy, hanging open on knuckle hinges (monster's right hinge split -> sag).
- Mouth: torn flesh at the corners, dark interior (palate ridges, tongue, ribbed throat),
  a deliberate row of big crooked plank teeth with blood at the gum line.
"""
import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

import monster_detail as D

rng = random.Random(77)

HW, HD, CH = 0.90, 0.79, 0.58          # skull width / depth / height
JAW_LEN, JAW_W = 0.81, 0.88
HINGE = Vector((0.0, HD / 2 - 0.12, -0.02))   # jaw pivot in cranium space


def skin(bm, profiles, mats=(0, 0, 0), caps=(True, True)):
    rings = [[bm.verts.new(p) for p in prof] for prof in profiles]
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for i in range(n):
            bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i])).material_index = mats[0]
    if caps[0]:
        bm.faces.new(list(reversed(rings[0]))).material_index = mats[1]
    if caps[1]:
        bm.faces.new(rings[-1]).material_index = mats[2]
    return rings


def superellipse(theta, a, b, p=4.0):
    c, s = math.cos(theta), math.sin(theta)
    return (a * math.copysign(abs(c) ** (2 / p), c), b * math.copysign(abs(s) ** (2 / p), s))


def gauss(p, centre, r):
    return math.exp(-((p - Vector(centre)).length / r) ** 2)


# ---------------------------------------------------------------------------
# Skull
# ---------------------------------------------------------------------------
EYES = [(-0.215, 0.235, 1.0), (0.195, 0.225, 0.9)]   # (x, z, size)


def skull_point(x, y, z):
    p = Vector((x, y, z))
    f = max(0.0, -y / (HD / 2))                         # 1 at the face, 0 at the back
    for ex, ez, k in EYES:                              # shallow recess around each socket
        g = math.exp(-((x - ex) / 0.10) ** 2 - ((z - ez) / 0.08) ** 2)
        p.y += 0.018 * g * f
    if x < 0:
        p.x *= 1.02                                     # right side a little swollen
    p.z += 0.03 * (x / (HW / 2)) * (z / CH) ** 1.5      # crown slants slightly
    p -= (p - Vector((0, 0, 0.28))).normalized() * 0.03 * gauss(p, (0.27, -0.1, 0.5), 0.16)   # old dent
    p += Vector((noise.noise(p * 3.1), noise.noise(p * 3.1 + Vector((5, 1, 2))),
                 noise.noise(p * 3.1 + Vector((9, 4, 7))))) * 0.008
    return p


# Three stacked strata (z0, z1, width, depth, x-shift, y-shift, twist deg). Each band
# starts with an overhanging lip and narrows toward its top, so every boundary reads as
# a ledge - the layered-rock look of the R08 head.
STRATA = [(0.00, 0.17, 0.90, 0.79, 0.000, 0.000, 0.0),
          (0.17, 0.37, 0.91, 0.80, 0.008, -0.006, 2.0),
          (0.37, 0.535, 0.87, 0.76, -0.006, 0.006, -1.5)]


def build_skull(M, col, location, rotation):
    rings = []
    for z0, z1, w, d, sx_, sy_, tw in STRATA:
        for t, k in ((0.0, 1.0), (0.06, 1.022), (0.8, 1.0), (1.0, 0.975)):
            rings.append((z0 + (z1 - z0) * t - (0.004 if t == 1.0 else 0.0), w * k, d * k, sx_, sy_, tw))
    rings[0] = (0.0, 0.86, 0.75, 0, 0, 0)
    rings += [(0.565, 0.80, 0.70, 0, 0, -1.5), (0.585, 0.66, 0.57, 0, 0, -1.5)]
    n = 16
    profiles = []
    for z, w, d, sx_, sy_, tw in rings:
        prof = []
        for k in range(n):
            th = 2 * math.pi * k / n + math.pi / n + math.radians(tw)
            x, y = superellipse(th, w / 2, d / 2, 3.6)
            prof.append(skull_point(x + sx_, y + sy_, z))
        profiles.append(prof)
    bm = bmesh.new()
    skin(bm, profiles, mats=(0, 1, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    sk = D.bm_object("Cranium", bm, col, [M["shell"], M["inner"]])
    sk.location, sk.rotation_euler = location, rotation
    bpy.context.view_layer.update()
    D.chisel(sk, level=1, plate=0.012, lump=0.01, cell=0.15)
    D.deform(sk, 0.01, 3.0, seed=3)
    return sk


def eye_sockets(sk, M, col):
    """Square, dark, recessed sockets with a tiny red square eye deep in each."""
    D.ensure_mat(sk, M["socket"])
    bm = bmesh.new()
    centres = []
    for ex, ez, k in EYES:
        c, n, u = D.ray_frame(sk, sk.matrix_world @ Vector((ex, -1.2, ez)),
                              sk.matrix_world.to_3x3() @ Vector((0, 1, 0)), (0, 0, 1))
        a, b = 0.068 * k, 0.058 * k
        # squarish outline with a few small chips in the rim
        out = []
        for i in range(16):
            ang = 2 * math.pi * i / 16 + math.pi / 16
            x, y = superellipse(ang, a, b, 6.0)
            r = rng.uniform(0.93, 1.05) * (rng.uniform(0.8, 0.9) if rng.random() < 0.15 else 1.0)
            out.append((x * r, y * r))
        D.cutter(bm, c, n, u, 0.10, out, rough_floor=0.1, wall_mat=0, floor_mat=0, taper=(0.72, 0.8))
        centres.append((c, n, u))
    D.boolean_apply(sk, D.cutter_from_bm(bm, [M["socket"]], sk))
    ebm = bmesh.new()
    for (c, n, u), (ex, ez, k) in zip(centres, EYES):
        r = 0.011 * k
        rot = n.to_track_quat('Z', 'Y').to_matrix().to_4x4()
        bmesh.ops.create_cube(ebm, size=2 * r, matrix=Matrix.Translation(c - n * 0.055) @ rot)
    D.bm_object("Eyes", ebm, col, [M["eye"]], parent=sk)
    return centres


# ---------------------------------------------------------------------------
# Jaw
# ---------------------------------------------------------------------------
def jaw_h(x):
    sag = 0.035 * max(0.0, -x / (JAW_W / 2))              # broken side hangs deeper
    return 0.23 + 0.12 * (1 - (x / (JAW_W / 2)) ** 2) + sag


def jaw_front(x):
    return -JAW_LEN + 0.14 * (abs(x) / (JAW_W / 2)) ** 2.5


def build_jaw(M, col, sk, open_deg, roll_deg):
    bm = bmesh.new()
    xs = [-JAW_W / 2 + i * JAW_W / 10 for i in range(11)]
    profs = []
    for x in xs:
        h, yf = jaw_h(x), jaw_front(x)
        j = lambda: Vector((rng.uniform(-0.01, 0.01), rng.uniform(-0.012, 0.012), rng.uniform(-0.012, 0.012)))
        profs.append([Vector(p) + j() for p in (
            (x, 0.07, -0.05), (x, 0.05, 0.0), (x, yf * 0.5, 0.005), (x, yf + 0.03, 0.0), (x, yf, -0.07),
            (x, yf + 0.04, -h * 0.9), (x, yf + 0.09, -h), (x, yf * 0.45, -h * 0.9), (x, 0.07, -0.22))])
    skin(bm, profs)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    jaw = D.bm_object("Jaw", bm, col, [M["shell"]], parent=sk)
    jaw.location = HINGE
    bpy.context.view_layer.update()
    # ascending rami up to the hinge knuckles
    rami = []
    for sx in (-1, 1):
        rb = bmesh.new()
        prof = lambda z, w, t: [Vector((sx * (JAW_W / 2 - 0.04) + dx * t / 2, y, z))
                                for dx, y in ((-1, -0.07 * w), (1, -0.07 * w), (1, 0.07 * w), (-1, 0.07 * w))]
        skin(rb, [prof(-0.20, 1.6, 0.09), prof(-0.06, 1.2, 0.085), prof(0.05, 0.9, 0.08)])
        bmesh.ops.recalc_face_normals(rb, faces=rb.faces)
        r = D.bm_object("_ramus", rb, col, [M["shell"]], parent=jaw)
        rami.append(r)
    bpy.context.view_layer.update()
    D.union(jaw, rami)
    jaw.parent = sk
    jaw.matrix_parent_inverse = Matrix.Identity(4)
    jaw.location = HINGE
    # hollow trough
    cb = bmesh.new()
    ix = JAW_W / 2 - 0.10
    profs = []
    for x in (-ix, -0.2, 0.0, 0.2, ix):
        h, yf = jaw_h(x), jaw_front(x)
        profs.append([Vector(p) for p in (
            (x, 0.22, 0.4), (x, yf + 0.11, 0.4), (x, yf + 0.11, -h + 0.13),
            (x, yf * 0.5, -h * 0.92 + 0.12), (x, 0.22, -0.10))])
    skin(cb, profs)
    bpy.context.view_layer.update()
    D.boolean_apply(jaw, D.cutter_from_bm(cb, [M["inner"]], jaw))
    D.chisel(jaw, level=1, plate=0.012, lump=0.01, cell=0.15)
    D.deform(jaw, 0.01, 2.6, seed=5)
    D.facet_cuts(jaw, 8, M, size=(0.25, 0.4), depth=(0.0, 0.012), tilt=(3, 9))
    jaw.rotation_euler = (math.radians(open_deg), math.radians(-roll_deg), math.radians(1.5))
    bpy.context.view_layer.update()
    return jaw


# ---------------------------------------------------------------------------
# Hinges, tissue, interior
# ---------------------------------------------------------------------------
def hinges_and_tissue(M, col, sk, jaw):
    jm = jaw.matrix_basis                                   # jaw-local -> cranium-local
    bm = bmesh.new()   # 0 shell, 1 edge, 2 metal
    for sx in (-1, 1):
        broken = sx < 0
        c = HINGE + Vector((sx * (HW / 2 + 0.005), 0, 0))
        halves = [(-1, Vector()), (1, Vector())]
        if broken:   # split knuckle: outer half cracked away and dropped
            halves = [(-1, Vector()), (1, Vector((sx * 0.02, 0.015, -0.035)))]
        for h, off in halves:
            ring = []
            for k in range(8):
                ang = 2 * math.pi * k / 8 + 0.2
                r = 0.078 * rng.uniform(0.85, 1.1)
                ring.append(Vector((0, math.cos(ang) * r, math.sin(ang) * r)))
            x0, x1 = (0.0, 0.055) if h < 0 else (0.06, 0.11)
            if broken and h > 0:
                x0 += 0.01
            prof0 = [c + off + Vector((sx * x0, p.y, p.z)) for p in ring]
            prof1 = [c + off + Vector((sx * x1, p.y * 0.92, p.z * 0.92)) for p in ring]
            rings = skin(bm, [prof0, prof1] if sx > 0 else [prof1, prof0], mats=(0, 1, 1))
        # hinge pin; on the broken side it is bent and sticks out
        pin = [c + Vector((-sx * 0.12, 0, 0)), c + Vector((sx * 0.16, 0, 0))]
        if broken:
            pin.append(c + Vector((sx * 0.26, -0.05, -0.13)))
        ring_pts = []
        for p in pin:
            ring_pts.append([p + Vector((0, math.cos(a) * 0.022, math.sin(a) * 0.022))
                             for a in (0, math.pi / 2, math.pi, 1.5 * math.pi)])
        skin(bm, ring_pts, mats=(2, 2, 2))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    D.bm_object("Jaw_Hinges", bm, col, [M["shell"], M["edge"], M["metal"]], parent=sk)

    # stretched, torn membranes at the mouth corners (with tension wrinkles)
    mb = bmesh.new()
    cols_n, rows_n = 6, 5
    for sx in (-1, 1):
        grid = []
        for i in range(cols_n):
            u = i / (cols_n - 1)
            top = Vector((sx * (HW / 2 - 0.06), HINGE.y + 0.02 - u * 0.42, 0.005))
            bot = jm @ Vector((sx * (JAW_W / 2 - 0.05), 0.02 - u * 0.42, -0.01))
            row = []
            for j in range(rows_n):
                v = j / (rows_n - 1)
                p = top.lerp(bot, v)
                wr = math.sin(math.pi * v) * (0.018 if i % 2 else -0.012)   # wrinkle ridges
                p += Vector((sx * wr, 0, 0)) + Vector((rng.uniform(-0.006, 0.006), rng.uniform(-0.01, 0.01), 0))
                row.append(mb.verts.new(p))
            grid.append(row)
        for i in range(cols_n - 1):
            for j in range(rows_n - 1):
                # tear the leading (mouth-corner) edge and punch a few holes
                if i == cols_n - 2 and 0 < j < rows_n - 2 and rng.random() < 0.7:
                    continue
                if i >= 2 and rng.random() < 0.18:
                    continue
                q = (grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])
                mb.faces.new(q if sx > 0 else tuple(reversed(q)))
    mem = D.bm_object("Mouth_Corner_Tissue", mb, col, [M["flesh"]], parent=sk)
    sol = mem.modifiers.new("Thick", 'SOLIDIFY')
    sol.thickness = 0.018
    D.apply_modifiers(mem)


def mouth_interior(M, col, sk, jaw):
    jm = jaw.matrix_basis
    # palate ridges (rugae)
    pb = bmesh.new()
    for i in range(6):
        y = -HD / 2 + 0.14 + i * 0.075
        hw = 0.28 - i * 0.012
        pts = [Vector((x, y + 0.02 * math.sin(x * 9 + i), -0.012)) for x in (-hw, -hw / 2, 0, hw / 2, hw)]
        D.tube(pb, pts, [0.012, 0.02, 0.016, 0.02, 0.012], 0, sides=5, jitter=0.25)
    D.bm_object("Palate", pb, col, [M["gum"]], parent=sk)
    # rotted tongue mass lying in the jaw trough (jaw-local, parented to the jaw)
    gb = bmesh.new()
    pts = [Vector((0.02, -0.19, -0.17)), Vector((0.0, -0.24, -0.19)), Vector((-0.03, -0.28, -0.2)),
           Vector((0.02, -0.46, -0.19)), Vector((0.05, -0.56, -0.17))]
    rings = []
    for i, p in enumerate(pts):
        w = (0.15, 0.15, 0.13, 0.11, 0.06)[i]
        h = (0.06, 0.07, 0.065, 0.05, 0.03)[i]
        ring = []
        for k in range(10):
            a = 2 * math.pi * k / 10
            ring.append(p + Vector((math.cos(a) * w * rng.uniform(0.85, 1.15), 0,
                                    math.sin(a) * h * rng.uniform(0.8, 1.2))))
        rings.append(ring)
    skin(gb, rings)
    bmesh.ops.recalc_face_normals(gb, faces=gb.faces)
    D.bm_object("Tongue", gb, col, [M["tongue"]], parent=jaw)
    # ribbed throat receding into the body
    tb = bmesh.new()
    path = [Vector((0, HD / 2 - 0.28, -0.02)), Vector((0, HD / 2 - 0.12, -0.14)),
            Vector((0, HD / 2 + 0.02, -0.28)), Vector((0, HD / 2 + 0.12, -0.45))]
    rings = []
    for i, p in enumerate(path):
        for sub in range(3):
            if i == len(path) - 1 and sub:
                break
            q = p if i == len(path) - 1 else p.lerp(path[i + 1], sub / 3)
            r = (0.30 - 0.05 * (i + sub / 3)) * (1.0 if sub % 2 == 0 else 0.86)   # ribbing
            rings.append([q + Vector((math.cos(a) * r, 0, math.sin(a) * r * 0.75))
                          for a in [2 * math.pi * k / 12 for k in range(12)]])
    skin(tb, rings, caps=(False, True))
    bmesh.ops.reverse_faces(tb, faces=tb.faces)          # seen from inside
    D.bm_object("Throat", tb, col, [M["throat"]], parent=sk)


# ---------------------------------------------------------------------------
# Gums and teeth
# ---------------------------------------------------------------------------
def gums_and_teeth(M, col, sk, jaw):
    wall = JAW_W / 2 - 0.05
    upper_path = ([(HW / 2 - 0.07, y) for y in (0.14, -0.10)] +
                  [(x, -HD / 2 + 0.085) for x in (HW / 2 - 0.12, 0.22, 0.05, -0.12, -0.28, -HW / 2 + 0.12)] +
                  [(-HW / 2 + 0.07, y) for y in (-0.10, 0.14)])
    lower_path = ([(wall, y) for y in (-0.08, -0.50)] +
                  [(x, jaw_front(x) + 0.06) for x in (wall - 0.08, 0.2, 0.0, -0.2, -wall + 0.08)] +
                  [(-wall, y) for y in (-0.50, -0.08)])
    for name, path, parent, z in (("Gums_Upper", upper_path, sk, -0.01), ("Gums_Lower", lower_path, jaw, 0.01)):
        gb = bmesh.new()
        dense = []
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            steps = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.045))
            for s in range(steps):
                t = s / steps
                dense.append(Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z)))
        dense.append(Vector((path[-1][0], path[-1][1], z)))
        radii = [rng.uniform(0.035, 0.055) for _ in dense]       # swollen, uneven gum ridge
        D.tube(gb, dense, radii, 0, sides=7, jitter=0.25, frame_ref=(0, 0, 1))
        for p in dense[::3]:                                     # dark swellings
            bmesh.ops.create_icosphere(gb, subdivisions=1, radius=rng.uniform(0.022, 0.035),
                                       matrix=Matrix.Translation(p + Vector((rng.uniform(-0.03, 0.03),
                                                                             rng.uniform(-0.03, 0.03),
                                                                             rng.uniform(-0.02, 0.02))))
                                       @ Matrix.Diagonal((1.3, 1.0, 0.7, 1)))
        D.bm_object(name, gb, col, [M["gum"]], parent=parent)

    def front_slots(x0, x1, yfun, z):
        s, x = [], x0
        while x < x1:
            s.append((Vector((x, yfun(x), z)), Vector((0, -1, 0)), True))
            x += rng.uniform(0.062, 0.078)
        return s

    up = front_slots(-HW / 2 + 0.10, HW / 2 - 0.09, lambda x: -HD / 2 + 0.085, -0.02)
    for sx in (-1, 1):
        for y in (-0.24, -0.14, -0.04):
            up.append((Vector((sx * (HW / 2 - 0.07), y + rng.uniform(-0.015, 0.015), -0.02)),
                       Vector((sx, 0, 0)), False))
    bm, layer = D.new_tooth_bm()
    D.plank_row(bm, layer, up, down=(0, 0, -1), out_bias=(0.05, 0.25), lean=(0, 0, 0),
                size={"front_len": (0.16, 0.27), "side_len": (0.11, 0.18)}, wild=1)
    D.bm_object("Teeth_Upper", bm, col, [M["teeth"]], parent=sk)

    lo = front_slots(-wall + 0.06, wall - 0.05, lambda x: jaw_front(x) + 0.06, 0.02)
    for sx in (-1, 1):
        for y in (-0.44, -0.32, -0.20):
            lo.append((Vector((sx * wall, y + rng.uniform(-0.015, 0.015), 0.02)), Vector((sx, 0, 0)), False))
    bm, layer = D.new_tooth_bm()
    D.plank_row(bm, layer, lo, down=(0, 0, 1), out_bias=(0.0, 0.2), lean=(0, 0.7, 0),
                size={"front_len": (0.14, 0.24), "side_len": (0.10, 0.16)}, wild=1)
    D.bm_object("Teeth_Lower", bm, col, [M["teeth"]], parent=jaw)


def build_head(M, col, location, rotation, open_deg, roll_deg):
    sk = build_skull(M, col, location, rotation)
    centres = eye_sockets(sk, M, col)
    jaw = build_jaw(M, col, sk, open_deg, roll_deg)
    hinges_and_tissue(M, col, sk, jaw)
    mouth_interior(M, col, sk, jaw)
    gums_and_teeth(M, col, sk, jaw)
    return sk, jaw, centres
