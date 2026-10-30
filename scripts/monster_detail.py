"""
Detail-pass geometry for the OUT THERE monster (v2).

Structure
- deform():       low-frequency structural dents / bulges (years of deformation).
- chisel():       light subdivision + stepped displacement (plate-like surface).
- facet_cuts():   planar "knapping" cuts that slice corners and break straight edges;
                  the stepped cut walls expose the shell's layer thickness.
- union():        boolean-merge parts into one connected structure.

Damage (all shallow, layered)
- peels:          wide ~1 cm strips where the outer rust skin has flaked off,
                  exposing the darker corroded metal under-layer.
- tears:          ~3-4 cm splits through the shell; the floor is packed fibrous tissue
                  whose top sits only ~1 cm below the surface; splinter shards and
                  peeled lips stay attached to the rim; optional rod driven into it.

Teeth
- make_tooth():   kinked, lumpy, split / snapped / chipped teeth; per-vertex 'tooth'
                  colour attribute: R root->tip, G blood, B decay, A tint.

Attributes for the shaders: 'blood' (point float), 'facet' (face float), 'tooth'.
"""
import math
import random

import bpy
import bmesh
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

rng = random.Random(1308)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    bpy.data.meshes.remove(old)
    for p in me.polygons:
        p.use_smooth = False


def ensure_mat(ob, mat):
    for i, s in enumerate(ob.material_slots):
        if s.material == mat:
            return i
    ob.data.materials.append(mat)
    return len(ob.data.materials) - 1


def local_bvh(ob):
    me = ob.data
    return BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons])


def ray_frame(ob, origin_world, dir_world, world_axis=(0, 0, 1)):
    """First surface hit along a ray -> (local point, local normal, local tangent)."""
    inv = ob.matrix_world.inverted()
    o = inv @ Vector(origin_world)
    d = (inv.to_3x3() @ Vector(dir_world)).normalized()
    loc, nor, _, _ = local_bvh(ob).ray_cast(o, d)
    ax = (inv.to_3x3() @ Vector(world_axis)).normalized()
    u = ax - nor * ax.dot(nor)
    return loc, nor.normalized(), u.normalized()


def surface_frame(ob, world_pt, world_axis=(0, 0, 1)):
    """Nearest surface point to world_pt -> (local point, local normal, local tangent)."""
    inv = ob.matrix_world.inverted()
    loc, nor, _, _ = local_bvh(ob).find_nearest(inv @ Vector(world_pt))
    ax = (inv.to_3x3() @ Vector(world_axis)).normalized()
    u = ax - nor * ax.dot(nor)
    if u.length < 1e-4:
        u = nor.orthogonal()
    return loc, nor.normalized(), u.normalized()


def bm_object(name, bm, col, mats, parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if parent is not None:
        ob.parent = parent
        ob.matrix_parent_inverse = Matrix.Identity(4)
    for p in me.polygons:
        p.use_smooth = False
    return ob


def boolean_apply(target, cutter_ob, op='DIFFERENCE'):
    mod = target.modifiers.new("Bool", 'BOOLEAN')
    mod.operation, mod.object, mod.solver = op, cutter_ob, 'EXACT'
    mod.material_mode = 'TRANSFER'
    mod.use_self, mod.use_hole_tolerant = True, True
    apply_modifiers(target)
    me = cutter_ob.data
    bpy.data.objects.remove(cutter_ob)
    if me.users == 0:
        bpy.data.meshes.remove(me)


def cutter_from_bm(bm, mats, like):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("_cutter")
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new("_cutter", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = like.matrix_world.copy()
    return ob


def union(target, others):
    """Merge `others` into `target` as one connected, manifold structure."""
    for o in others:
        bpy.context.view_layer.update()
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        mod = target.modifiers.new("Union", 'BOOLEAN')
        mod.operation, mod.object, mod.solver = 'UNION', o, 'EXACT'
        mod.material_mode = 'TRANSFER'
        mod.use_self = True
        apply_modifiers(target)
        bpy.data.objects.remove(o)


def clamp_to_floor(ob, floor=0.004):
    mw, inv = ob.matrix_world, ob.matrix_world.inverted()
    for v in ob.data.vertices:
        w = mw @ v.co
        if w.z < floor:
            w.z = floor
            v.co = inv @ w


# ---------------------------------------------------------------------------
# Structural surface shaping
# ---------------------------------------------------------------------------
def deform(ob, amp=0.025, freq=1.7, seed=0.0):
    """Coherent dents and swellings along the normals (world-space Perlin)."""
    mw = ob.matrix_world
    off = Vector((seed * 13.1, seed * 7.7 + 3.0, seed * 3.3 + 11.0))
    me = ob.data
    for v in me.vertices:
        w = mw @ v.co
        n = noise.noise(w * freq + off) + 0.45 * noise.noise(w * freq * 2.6 + off * 1.7)
        v.co += v.normal * amp * n
    me.update()


def chisel(ob, level=1, plate=0.015, lump=0.02, cell=0.22):
    if level:
        sub = ob.modifiers.new("Sub", 'SUBSURF')
        sub.subdivision_type, sub.levels, sub.render_levels = 'SIMPLE', level, level
    t1 = bpy.data.textures.new(ob.name + "_plates", 'VORONOI')
    t1.noise_scale, t1.color_mode = cell, 'POSITION'
    t2 = bpy.data.textures.new(ob.name + "_lumps", 'CLOUDS')
    t2.noise_scale, t2.noise_depth = 0.5, 1
    for tex, s in ((t1, plate), (t2, lump)):
        d = ob.modifiers.new("Disp", 'DISPLACE')
        d.texture, d.strength, d.mid_level, d.texture_coords = tex, s, 0.5, 'GLOBAL'
    apply_modifiers(ob)
    bpy.data.textures.remove(t1)
    bpy.data.textures.remove(t2)


def _box(bm, centre, rot, size, top_mat, wall_mat):
    """Box with local +Z face = cutting plane side... returns nothing.
    Face whose normal is -Z (the cutting plane) gets top_mat (it becomes the new facet)."""
    sx, sy, sz = size
    corners = [Vector((x * sx / 2, y * sy / 2, z * sz / 2))
               for z in (-1, 1) for y in (-1, 1) for x in (-1, 1)]
    vs = [bm.verts.new(centre + rot @ c) for c in corners]
    faces = [((0, 2, 3, 1), top_mat),  # -Z (cut plane)
             ((4, 5, 7, 6), wall_mat), ((0, 1, 5, 4), wall_mat), ((2, 6, 7, 3), wall_mat),
             ((0, 4, 6, 2), wall_mat), ((1, 3, 7, 5), wall_mat)]
    for idx, m in faces:
        bm.faces.new([vs[i] for i in idx]).material_index = m


def facet_cuts(ob, count, M, size=(0.18, 0.36), depth=(0.0, 0.016), tilt=(3, 13), weight=None, steps=0.0):
    """Knapping: broad, shallow planes slice corners and break straight edges cleanly.
    A fraction (`steps`) are small, slightly deeper cuts that leave layered plate steps.
    weight(poly_center_world) biases placement."""
    shell, edge = M["shell"], M["edge"]
    ensure_mat(ob, shell)
    ensure_mat(ob, edge)
    polys = [p for p in ob.data.polygons if p.area > 1e-5]
    mw = ob.matrix_world
    wts = [p.area * (weight(mw @ p.center) if weight else 1.0) for p in polys]
    bm = bmesh.new()
    for p in rng.choices(polys, wts, k=count):
        n = p.normal.copy()
        r = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        r = (r - n * r.dot(n))
        if r.length < 1e-4:
            continue
        small = rng.random() < steps
        tl = rng.uniform(10, 24) if small else rng.uniform(*tilt)
        t = (n + r.normalized() * math.tan(math.radians(tl))).normalized()
        S = rng.uniform(0.06, 0.14) if small else rng.uniform(*size)
        p0 = p.center - n * (rng.uniform(0.006, 0.02) if small else rng.uniform(*depth))
        # jagged-outline cutter whose floor is the (tilted) knapping plane: where the plane
        # dips below the surface the step wall is a torn, splintered edge, never a rectangle
        ut = (r - t * r.dot(t)).normalized()
        out = jagged_outline(S * rng.uniform(0.5, 1.0), S * 0.5, 14, notch=0.3, fine=0.2)
        cutter(bm, p0, t, ut, 0.0005, out, rough_floor=0.0, wall_mat=1, floor_mat=0, taper=(0.99, 1.0))
    if not bm.verts:
        bm.free()
        return
    boolean_apply(ob, cutter_from_bm(bm, [shell, edge], ob))


def dissolve_planar(ob, angle=1.5):
    """Merge the coplanar slivers that booleans leave behind (shape unchanged)."""
    mod = ob.modifiers.new("Planar", 'DECIMATE')
    mod.decimate_type = 'DISSOLVE'
    mod.angle_limit = math.radians(angle)
    mod.delimit = {'MATERIAL'}
    apply_modifiers(ob)


def facet_attr(ob):
    """Random per-face value so the shader can tint each chiselled plate differently."""
    me = ob.data
    if "facet" in me.attributes:
        me.attributes.remove(me.attributes["facet"])
    a = me.attributes.new("facet", 'FLOAT', 'FACE')
    a.data.foreach_set("value", [rng.random() for _ in me.polygons])


# ---------------------------------------------------------------------------
# Wounds
# ---------------------------------------------------------------------------
def jagged_outline(a, b, n, notch=0.2, fine=0.0):
    """Irregular torn outline: smooth wobble + uneven splinter teeth (never a regular star)."""
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(4)]
    pts = []
    for i in range(n):
        ang = 2 * math.pi * (i + rng.uniform(-0.35, 0.35)) / n
        r = 1.0 + 0.18 * math.sin(2 * ang + ph[0]) + 0.11 * math.sin(3 * ang + ph[1]) \
            + 0.07 * math.sin(5 * ang + ph[2]) + 0.05 * math.sin(7 * ang + ph[3])
        r *= rng.uniform(0.9, 1.06)
        roll = rng.random()
        if roll < notch:
            r *= rng.uniform(0.6, 0.82)
        elif roll < notch + 0.12:
            r *= rng.uniform(1.1, 1.3)
        if fine and i % 2:
            r *= 1 - fine * rng.uniform(0.5, 1.0)     # fine sawtooth splintering
        pts.append((math.cos(ang) * a * r, math.sin(ang) * b * r))
    return pts


def cutter(bm, c, n, u, depth, outline, rough_floor=0.4, wall_mat=0, floor_mat=1, taper=(0.82, 0.95)):
    """Closed jagged prism cutter. Walls -> wall_mat, floor -> floor_mat."""
    v = n.cross(u)
    top = [bm.verts.new(c + u * x + v * y + n * 0.12) for x, y in outline]
    bot = [bm.verts.new(c + (u * x + v * y) * rng.uniform(*taper) - n * depth * rng.uniform(0.8, 1.2))
           for x, y in outline]
    mid = [bm.verts.new(c + (u * x + v * y) * 0.5 - n * depth * rng.uniform(1.0, 1.0 + rough_floor))
           for x, y in outline]
    ctr = bm.verts.new(c - n * depth * rng.uniform(0.95, 1.0 + rough_floor))
    k = len(outline)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((top[i], top[j], bot[j], bot[i])).material_index = wall_mat
        bm.faces.new((bot[i], bot[j], mid[j], mid[i])).material_index = floor_mat
        bm.faces.new((mid[i], mid[j], ctr)).material_index = floor_mat
    bm.faces.new(list(reversed(top))).material_index = wall_mat
    return v


def tube(bm, pts, radii, mat, sides=5, jitter=0.2, frame_ref=None, flat=0.8):
    """Lumpy tapered tube along a polyline (tissue bundles, strings, tendons)."""
    pts = [Vector(p) for p in pts]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized() if frame_ref is None else (Vector(frame_ref) - t * t.dot(Vector(frame_ref))).normalized()
        b = t.cross(a)
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            r = radii[i] * rng.uniform(1 - jitter, 1 + jitter)
            ring.append(bm.verts.new(p + (a * math.cos(ang) + b * math.sin(ang) * flat) * r))
        rings.append(ring)
    for ra, rb in zip(rings, rings[1:]):
        for k in range(sides):
            bm.faces.new((ra[k], ra[(k + 1) % sides], rb[(k + 1) % sides], rb[k])).material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[-1]).material_index = mat


def tissue_sheet(bm, c, n, u, v, a, b, mat, project, top=(0.012, 0.02), groove=0.013, pitch=(0.024, 0.036)):
    """Corrugated fibrous tissue filling a tear: parallel muscle-fibre ridges running along u,
    dark grooves between them, swelling toward the middle. The sheet is larger than the hole;
    its edges disappear under the torn shell, so the flesh reads as part of the body."""
    nu, nv = 22, 22
    P = rng.uniform(*pitch)
    ph = rng.uniform(0, 2 * math.pi)
    t0 = rng.uniform(*top)
    grid = []
    for i in range(nu + 1):
        x = (i / nu - 0.5) * 1.9 * a
        row = []
        for j in range(nv + 1):
            y = (j / nv - 0.5) * 2.0 * b
            q, nn = project(c + u * x + v * y)
            nn = (n * 0.7 + nn * 0.3).normalized()       # faceted surface: avoid normal jumps
            rr = (x / (0.95 * a)) ** 2 + (y / (1.0 * b)) ** 2
            swell = max(0.0, 1 - rr) ** 0.7                     # bulges toward the centre
            wob = noise.noise(Vector((x * 6, y * 6, ph))) * 0.15
            ridge = 0.5 + 0.5 * math.cos(2 * math.pi * (y + 0.01 * math.sin(x * 23 + ph)) / P + ph + wob)
            d = t0 + groove * (1 - ridge) - 0.008 * swell + 0.06 * (1 - swell) ** 2
            row.append(bm.verts.new(q - nn * d))
        grid.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1])).material_index = mat


def shard(bm, c, n, u, v, outline, start, length, shell_mat, edge_mat, reach=(0.05, 0.13), lift=(0.002, 0.016),
          project=None):
    """Splintered shell lip still attached to the rim, lifted / peeled outward."""
    k = len(outline)
    idx = [(start + i) % k for i in range(length)]
    L = rng.uniform(*lift)
    R = rng.uniform(*reach)
    th = rng.uniform(0.006, 0.01)
    inward = True                         # hang over the opening (never float off a silhouette)
    base, tip = [], []
    for j, i in enumerate(idx):
        x, y = outline[i]
        p = c + u * x + v * y
        taper = math.sin(math.pi * (j + 0.5) / length) ** 0.7
        d = (c - p) if inward else (p - c)
        if project:
            p = project(p)[0]
        base.append(p - n * 0.005)
        tip.append(p + d * R * taper * rng.uniform(0.5, 1.3) + n * L * taper * rng.uniform(0.6, 1.3))
    ta = [bm.verts.new(p + n * th) for p in base]
    tb = [bm.verts.new(p + n * th) for p in tip]
    ba = [bm.verts.new(p) for p in base]
    bb = [bm.verts.new(p) for p in tip]
    m = len(idx)
    for i in range(m - 1):
        bm.faces.new((ta[i], ta[i + 1], tb[i + 1], tb[i])).material_index = shell_mat
        bm.faces.new((bb[i], bb[i + 1], ba[i + 1], ba[i])).material_index = edge_mat
        bm.faces.new((tb[i], tb[i + 1], bb[i + 1], bb[i])).material_index = edge_mat
        bm.faces.new((ba[i], ba[i + 1], ta[i + 1], ta[i])).material_index = edge_mat
    bm.faces.new((ta[0], tb[0], bb[0], ba[0])).material_index = edge_mat
    bm.faces.new((ba[-1], bb[-1], tb[-1], ta[-1])).material_index = edge_mat


def damage(ob, tears, peels, chips, M, blood_sources, rod_bm=None):
    """tears: dict(world, axis, a, b, depth, bundles, shards, rod)
    peels: dict(world, axis, a, b)  chips: count of tiny random flakes."""
    for k in ("shell", "edge", "flesh", "under"):
        ensure_mat(ob, M[k])
    cbm = bmesh.new()   # mats: 0 edge, 1 flesh, 2 under
    extras = []
    mw = ob.matrix_world
    for p in peels:
        c, n, u = surface_frame(ob, p["world"], p.get("axis", (0, 0, 1)))
        out = jagged_outline(p["a"], p["b"], 40, notch=0.3, fine=0.25)
        cutter(cbm, c, n, u, rng.uniform(0.008, 0.014), out, rough_floor=0.0, floor_mat=2, taper=(0.9, 0.98))
    for w in tears:
        c, n, u = surface_frame(ob, w["world"], w.get("axis", (0, 0, 1)))
        a, b, depth = w["a"], w["b"], max(0.045, w.get("depth", 0.045))
        # layered: wide jagged peel of the rust skin around the split ...
        peel = [(x * rng.uniform(1.3, 1.6), y * rng.uniform(1.5, 2.0))
                for x, y in jagged_outline(a, b, 40, notch=0.3, fine=0.2)]
        cutter(cbm, c, n, u, 0.011, peel, rough_floor=0.0, floor_mat=2, taper=(0.92, 0.98))
        # ... and the split itself through the shell to the tissue
        out = jagged_outline(a, b, 34, notch=0.22, fine=0.3)
        v = cutter(cbm, c, n, u, depth, out, rough_floor=0.3, floor_mat=1)
        extras.append((c, n, u, v, w, out))
        blood_sources.append((mw @ c, max(a, b) * 1.5, 2.6))
    polys = [p for p in ob.data.polygons if p.area > 1e-5]
    for p in rng.choices(polys, [p.area for p in polys], k=chips):
        n = p.normal.copy()
        u = Matrix.Rotation(rng.uniform(0, math.pi), 3, n) @ n.orthogonal().normalized()
        s = rng.uniform(0.02, 0.05)
        out = jagged_outline(s * rng.uniform(1.2, 2.6), s, 16, notch=0.3)
        cutter(cbm, p.center.copy(), n, u, rng.uniform(0.006, 0.011), out, rough_floor=0.0, floor_mat=2)
    surf = local_bvh(ob)          # intact surface, before the cuts: tissue/shards follow it
    if cbm.verts:
        boolean_apply(ob, cutter_from_bm(cbm, [M["edge"], M["flesh"], M["under"]], ob))
    else:
        cbm.free()

    flesh_i, edge_i, shell_i = (ensure_mat(ob, M[k]) for k in ("flesh", "edge", "shell"))

    def project(p):
        loc, nor, _, _ = surf.find_nearest(p)
        return (loc, nor) if loc is not None else (p, Vector((0, 0, 1)))

    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for c, n, u, v, w, out in extras:
        tissue_sheet(bm, c, n, u, v, w["a"], w["b"], flesh_i, project)
        for _ in range(max(2, w.get("shards", 4) // 2)):
            shard(bm, c, n, u, v, out, rng.randrange(len(out)), rng.randint(3, 5), shell_i, edge_i,
                  project=project)
        if w.get("rod") and rod_bm is not None:
            d = (n * 1.0 + u * rng.uniform(-0.6, 0.6) + v * rng.uniform(-0.4, 0.4)).normalized()
            p0 = mw @ (c - n * 0.06 - d * 0.04)
            p1 = mw @ (c + d * w["rod"])
            rod_bm.append((p0, p1))
            blood_sources.append((mw @ c, 0.12, 3.0))
    bm.to_mesh(ob.data)
    bm.free()
    smooth_organic(ob, [flesh_i])


def smooth_organic(ob, mat_indices, sharp_angle=None):
    """Shell stays faceted; tissue is smooth-shaded so it reads soft and wet.
    sharp_angle keeps hard breaks (fractured teeth) crisp inside smooth surfaces."""
    for p in ob.data.polygons:
        p.use_smooth = p.material_index in mat_indices
    if sharp_angle:
        ob.data.set_sharp_from_angle(angle=math.radians(sharp_angle))


# ---------------------------------------------------------------------------
# Blood attribute
# ---------------------------------------------------------------------------
def paint_blood(ob, sources, base=0.0):
    """sources: (world point, radius, drip_stretch). Stains run further downward."""
    me = ob.data
    if "blood" in me.attributes:
        me.attributes.remove(me.attributes["blood"])
    at = me.attributes.new("blood", 'FLOAT', 'POINT')
    mw = ob.matrix_world
    vals = []
    for v in me.vertices:
        p = mw @ v.co
        best = base
        for s, r, drip in sources:
            d = p - s
            dz = d.z / drip if d.z < 0 else d.z * 1.4
            dist = math.sqrt(d.x * d.x + d.y * d.y + dz * dz)
            if dist < r:
                best = max(best, (1 - dist / r) ** 1.2)
        vals.append(best)
    at.data.foreach_set("value", vals)


# ---------------------------------------------------------------------------
# Teeth
# ---------------------------------------------------------------------------
def make_tooth(bm, layer, base, direction, length, w, d, kind=None, twist=0.0, root_exposed=0.0):
    """Kinked, lumpy, damaged tooth. Colour attr: (t, blood, decay, tint)."""
    dvec = Vector(direction).normalized()
    side = Matrix.Rotation(math.radians(twist), 3, dvec) @ dvec.orthogonal().normalized()
    fwd = dvec.cross(side).normalized()
    kind = kind or rng.choices(["fang", "snapped", "chipped", "stump", "slab"],
                               [0.24, 0.26, 0.24, 0.1, 0.16])[0]
    if kind == "stump":
        length *= rng.uniform(0.25, 0.4)
    elif kind == "snapped":
        length *= rng.uniform(0.5, 0.8)
    elif kind == "slab":
        w *= rng.uniform(1.3, 1.7)
    sides = rng.choice([5, 6, 6, 7])
    prof = [(math.cos(2 * math.pi * k / sides + 0.3) * w / 2 * rng.uniform(0.88, 1.08),
             math.sin(2 * math.pi * k / sides + 0.3) * d / 2 * rng.uniform(0.88, 1.08)) for k in range(sides)]
    kink = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)) * length * rng.uniform(0.06, 0.22)
    blood = min(1.0, rng.choice([0.0, 0.2, 0.35, 0.5, 0.7, 0.95]) * rng.uniform(0.7, 1.2))
    decay = rng.random() ** 1.6
    tint = rng.random()
    tip_scale = {"fang": 0.42, "snapped": 0.8, "chipped": 0.72, "stump": 0.85, "slab": 0.7}[kind]
    ts = [(-0.2, 0.78), (0.0 - root_exposed, 0.95), (0.22, 1.05), (0.45, 1.0), (0.7, 0.86), (1.0, tip_scale)]
    rings = []
    for idx, (t, s) in enumerate(ts):
        bend = kink * (max(t, 0) ** 1.6) + (side * rng.uniform(-0.04, 0.04) * w if 0 < idx < len(ts) - 1 else Vector())
        ctr = Vector(base) + dvec * length * t + bend
        rings.append((t, [ctr + side * x * s * rng.uniform(0.97, 1.03) + fwd * y * s * rng.uniform(0.97, 1.03)
                          for x, y in prof]))
    t_last, last = rings[-1]
    tipc = Vector(base) + dvec * length + kink
    if kind in ("snapped", "stump"):     # fracture plane
        tilt = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)).normalized()
        for i, p in enumerate(last):
            last[i] = p + dvec * (p - tipc).dot(tilt) * rng.uniform(0.7, 1.4) - dvec * rng.uniform(0, 0.3) * w
    elif kind in ("chipped", "slab"):    # one or two corners broken away
        for _ in range(rng.randint(1, 2)):
            i = rng.randrange(len(last))
            last[i] = last[i] - dvec * w * rng.uniform(0.3, 0.8)
    verts = []
    for t, ring in rings:
        row = []
        for p in ring:
            bv = bm.verts.new(p)
            bv[layer] = (max(t, 0.0), blood, decay, tint)
            row.append(bv)
        verts.append(row)
    k = len(prof)
    for ra, rb in zip(verts, verts[1:]):
        for i in range(k):
            bm.faces.new((ra[i], ra[(i + 1) % k], rb[(i + 1) % k], rb[i]))
    bm.faces.new(list(reversed(verts[0])))
    if kind == "fang":
        apex = bm.verts.new(tipc + dvec * length * 0.08 + side * rng.uniform(-0.3, 0.3) * w)
        apex[layer] = (1.0, blood, decay, tint)
        for i in range(k):
            bm.faces.new((verts[-1][i], verts[-1][(i + 1) % k], apex))
    else:
        bm.faces.new(verts[-1])


def teeth_row(bm, layer, slots, down, out_bias, lean, size):
    """slots: (base, outward, is_front). Produces a chaotic, crowded, damaged row."""
    down = Vector(down)
    for base, outward, front in slots:
        if rng.random() < 0.07:
            continue                                   # missing tooth (gap)
        cls = rng.choices(["giant", "normal", "needle"], [0.22, 0.6, 0.18])[0]
        L = rng.uniform(*size["front_len"]) if front else rng.uniform(*size["side_len"])
        if cls == "giant":
            L *= rng.uniform(1.2, 1.5)
            w, d = rng.uniform(0.11, 0.16), rng.uniform(0.07, 0.10)
        elif cls == "needle":
            L *= rng.uniform(0.7, 1.0)
            w, d = rng.uniform(0.035, 0.05), rng.uniform(0.035, 0.05)
        else:
            w, d = rng.uniform(0.07, 0.11), rng.uniform(0.05, 0.08)
        crooked = Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.25, 0.25), 0))
        dvec = down + outward * rng.uniform(*out_bias) + Vector(lean) + crooked
        roll = rng.random()
        if roll < 0.12:      # rammed in at an unnatural angle (sideways / outward)
            axis = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized()
            dvec = Matrix.Rotation(math.radians(rng.uniform(50, 80)), 3, axis) @ dvec
            L *= 0.8
        elif roll < 0.2:     # pointing back into the throat
            dvec = dvec - outward * 0.9
        exposed = rng.uniform(0.0, 0.25) if rng.random() < 0.5 else 0.0   # receded gum
        b = Vector(base) + Vector((rng.uniform(-0.012, 0.012), rng.uniform(-0.015, 0.015), 0))
        if cls != "giant" and rng.random() < 0.1:   # split tooth: two halves with a crack between
            for s in (-1, 1):
                make_tooth(bm, layer, b + Vector((s * w * 0.3, 0, 0)), dvec + Vector((s * 0.12, 0, 0)),
                           L * rng.uniform(0.7, 1.0), w * 0.5, d, kind="snapped", twist=rng.uniform(-30, 30))
        else:
            make_tooth(bm, layer, b, dvec, L, w, d, twist=rng.uniform(-40, 40), root_exposed=exposed,
                       kind="slab" if cls == "giant" and rng.random() < 0.5 else None)
        if rng.random() < 0.2:   # crowded second tooth growing behind / beside
            inner = Vector(base) - outward.normalized() * rng.uniform(0.05, 0.09) + Vector((rng.uniform(-0.04, 0.04), 0, 0))
            make_tooth(bm, layer, inner, down + crooked * 1.6 + Vector(lean), L * rng.uniform(0.45, 0.7),
                       w * 0.75, d * 0.8, twist=rng.uniform(-50, 50))


def new_tooth_bm():
    bm = bmesh.new()
    layer = bm.verts.layers.float_color.new("tooth")
    return bm, layer
