"""
Detail-pass geometry for the OUT THERE monster:

- chisel():       simple subdivision + stepped Voronoi/cloud displacement -> the faceted,
                  plate-like shell surface (stays low-poly and flat-shaded).
- Wounds:         jagged, *shallow* boolean cuts. Cut walls show the shell's thickness
                  (torn-edge material), the floor is dark tissue only a few cm below the
                  surface, with muscle strands and lifted shell flaps added on top.
- Chips:          tiny shallow cuts exposing the darker corroded under-layer.
- make_tooth():   irregular, bent, chipped/broken teeth with a per-vertex 'tooth' attribute.
- blood attribute painted from wound / mouth / stump / rod sources, with downward drips.
"""
import math
import random

import bpy
import bmesh
from mathutils import Matrix, Vector
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


def surface_frame(ob, world_pt, world_axis=(0, 0, 1)):
    """Nearest surface point to world_pt -> (local point, local normal, local tangent)."""
    inv = ob.matrix_world.inverted()
    loc, nor, _, _ = local_bvh(ob).find_nearest(inv @ Vector(world_pt))
    ax = (inv.to_3x3() @ Vector(world_axis)).normalized()
    u = ax - nor * ax.dot(nor)
    if u.length < 1e-4:
        u = nor.orthogonal()
    return loc, nor.normalized(), u.normalized()


# ---------------------------------------------------------------------------
# Shell surface
# ---------------------------------------------------------------------------
def chisel(ob, level=1, plate=0.03, lump=0.035, cell=0.24, seed=0):
    sub = ob.modifiers.new("Sub", 'SUBSURF')
    sub.subdivision_type, sub.levels, sub.render_levels = 'SIMPLE', level, level
    t1 = bpy.data.textures.new(ob.name + "_plates", 'VORONOI')
    t1.noise_scale, t1.color_mode = cell, 'POSITION'
    t2 = bpy.data.textures.new(ob.name + "_lumps", 'CLOUDS')
    t2.noise_scale, t2.noise_depth = 0.55, 1
    for tex, s in ((t1, plate), (t2, lump)):
        d = ob.modifiers.new("Disp", 'DISPLACE')
        d.texture, d.strength, d.mid_level, d.texture_coords = tex, s, 0.5, 'GLOBAL'
    apply_modifiers(ob)
    bpy.data.textures.remove(t1)
    bpy.data.textures.remove(t2)


def clamp_to_floor(ob, floor=0.004):
    mw, inv = ob.matrix_world, ob.matrix_world.inverted()
    for v in ob.data.vertices:
        w = mw @ v.co
        if w.z < floor:
            w.z = floor
            v.co = inv @ w


# ---------------------------------------------------------------------------
# Wounds and chips
# ---------------------------------------------------------------------------
def jagged_outline(a, b, n, notch=0.18):
    """Irregular torn outline: smooth wobble + uneven splinter teeth (never a regular star)."""
    ph = [rng.uniform(0, 2 * math.pi) for _ in range(3)]
    pts = []
    for i in range(n):
        ang = 2 * math.pi * (i + rng.uniform(-0.3, 0.3)) / n
        r = 1.0 + 0.16 * math.sin(2 * ang + ph[0]) + 0.10 * math.sin(3 * ang + ph[1]) \
            + 0.06 * math.sin(5 * ang + ph[2])
        r *= rng.uniform(0.9, 1.06)
        roll = rng.random()
        if roll < notch:
            r *= rng.uniform(0.62, 0.8)          # torn-in notch
        elif roll < notch + 0.10:
            r *= rng.uniform(1.12, 1.28)         # splinter
        pts.append((math.cos(ang) * a * r, math.sin(ang) * b * r))
    return pts


def cutter(bm, c, n, u, a, b, depth, outline_n=26, rough_floor=0.5, floor_mat=1, outline=None):
    """Closed jagged prism: walls -> material 0 (torn edge), floor -> floor_mat."""
    v = n.cross(u)
    out = outline or jagged_outline(a, b, outline_n)
    top = [bm.verts.new(c + u * x + v * y + n * 0.12) for x, y in out]
    bot = [bm.verts.new(c + (u * x + v * y) * rng.uniform(0.82, 0.95) - n * depth * rng.uniform(0.8, 1.2))
           for x, y in out]
    mid = [bm.verts.new(c + (u * x + v * y) * 0.5 - n * depth * rng.uniform(1.0, 1.0 + rough_floor))
           for x, y in out]
    ctr = bm.verts.new(c - n * depth * rng.uniform(0.9, 1.0 + rough_floor))
    k = len(out)
    for i in range(k):
        j = (i + 1) % k
        bm.faces.new((top[i], top[j], bot[j], bot[i])).material_index = 0
        bm.faces.new((bot[i], bot[j], mid[j], mid[i])).material_index = floor_mat
        bm.faces.new((mid[i], mid[j], ctr)).material_index = floor_mat
    bm.faces.new(list(reversed(top))).material_index = 0
    return out, v


def strands(bm, c, n, u, v, a, b, depth, count, mat):
    """Thick, uneven muscle bundles lying in the wound along its long axis (u)."""
    for _ in range(count):
        off = rng.uniform(-0.45, 0.45) * b
        L = a * rng.uniform(1.0, 1.6)
        lift = depth * rng.uniform(0.25, 0.6)          # stays shallow, near the surface
        r = rng.uniform(0.016, 0.028)
        p0 = c + v * off - u * L / 2 - n * depth * 1.2
        p1 = c + v * (off + rng.uniform(-0.015, 0.015)) - n * lift
        p2 = c + v * off + u * L / 2 - n * depth * 1.2
        rings = []
        for t, s in ((0.0, 0.6), (0.2, 0.95), (0.4, 0.8), (0.6, 1.0), (0.8, 0.85), (1.0, 0.6)):
            p = (p0 * (1 - t) ** 2 + p1 * 2 * t * (1 - t) + p2 * t * t)
            ring = []
            for k in range(5):
                ang = 2 * math.pi * k / 5
                ring.append(bm.verts.new(p + (n * math.cos(ang) * 0.7 + v * math.sin(ang)) * r * s
                                         * rng.uniform(0.75, 1.2)))
            rings.append(ring)
        for ra, rb in zip(rings, rings[1:]):
            for k in range(5):
                f = bm.faces.new((ra[k], ra[(k + 1) % 5], rb[(k + 1) % 5], rb[k]))
                f.material_index = mat


def flap(bm, c, n, u, v, outline, start, length, shell_mat, edge_mat):
    """Split shell lip at the rim, peeled back and curling up off the surface."""
    k = len(outline)
    idx = [(start + i) % k for i in range(length)]
    lift = rng.uniform(0.012, 0.03)
    reach = rng.uniform(0.10, 0.22)
    th = 0.012
    base, tip = [], []
    for j, i in enumerate(idx):
        x, y = outline[i]
        p = c + u * x + v * y
        taper = math.sin(math.pi * (j + 0.5) / length)      # pointed at both ends
        base.append(p - n * 0.006 - (p - c) * 0.04)
        tip.append(p + (p - c) * reach * taper * rng.uniform(0.6, 1.2) + n * lift * taper)
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


def damage(ob, wounds, chips, M, blood_sources):
    """wounds: list of dict(world, axis, a, b, depth, strands, flaps). chips: count.

    Each wound is two stacked cuts: a wide, very shallow peel that strips the outer
    rust skin (under-layer floor), and inside it the tear through the shell with dark
    tissue only a few centimetres below the surface.
    """
    for k in ("edge", "flesh", "under", "shell"):
        ensure_mat(ob, M[k])
    cut_bm = bmesh.new()
    extras = []
    for w in wounds:
        c, n, u = surface_frame(ob, w["world"], w.get("axis", (0, 0, 1)))
        a, b, depth = w["a"], w["b"], w.get("depth", 0.04)
        peel = [(x * rng.uniform(1.25, 1.5), y * rng.uniform(1.3, 1.7))
                for x, y in jagged_outline(a, b, 30, notch=0.3)]
        cutter(cut_bm, c, n, u, a, b, 0.010, rough_floor=0.1, floor_mat=2, outline=peel)
        outline, v = cutter(cut_bm, c, n, u, a, b, depth, floor_mat=1)
        extras.append((c, n, u, v, w, outline))
        blood_sources.append((ob.matrix_world @ c, max(a, b) * 1.6, 2.5))
    # small shallow chips: no tissue, just the corroded under-layer
    polys = [p for p in ob.data.polygons if p.area > 1e-4]
    for p in rng.choices(polys, [p.area for p in polys], k=chips):
        n = p.normal.copy()
        u = Matrix.Rotation(rng.uniform(0, math.pi), 3, n) @ n.orthogonal().normalized()
        s = rng.uniform(0.022, 0.06)
        cutter(cut_bm, p.center.copy(), n, u, s * rng.uniform(1.2, 2.4), s, rng.uniform(0.007, 0.013),
               outline_n=14, rough_floor=0.2, floor_mat=2)
    bmesh.ops.recalc_face_normals(cut_bm, faces=cut_bm.faces)
    cme = bpy.data.meshes.new("_cut")
    cut_bm.to_mesh(cme)
    cut_bm.free()
    for k in ("edge", "flesh", "under"):
        cme.materials.append(M[k])
    cut_ob = bpy.data.objects.new("_cut_" + ob.name, cme)
    bpy.context.scene.collection.objects.link(cut_ob)
    cut_ob.matrix_world = ob.matrix_world.copy()
    mod = ob.modifiers.new("Damage", 'BOOLEAN')
    mod.operation, mod.object, mod.solver = 'DIFFERENCE', cut_ob, 'EXACT'
    mod.material_mode = 'TRANSFER'
    mod.use_self, mod.use_hole_tolerant = True, True
    apply_modifiers(ob)
    bpy.data.objects.remove(cut_ob)
    bpy.data.meshes.remove(cme)

    flesh_i, edge_i, shell_i = (ensure_mat(ob, M[k]) for k in ("flesh", "edge", "shell"))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for c, n, u, v, w, outline in extras:
        depth = w.get("depth", 0.04)
        strands(bm, c, n, u, v, w["a"], w["b"], depth, w.get("strands", 2), flesh_i)
        for _ in range(w.get("flaps", 1)):
            flap(bm, c, n, u, v, outline, rng.randrange(len(outline)), rng.randint(4, 6), shell_i, edge_i)
    bm.to_mesh(ob.data)
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = False


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
def make_tooth(bm, layer, base, direction, length, w, d, kind=None, twist=0.0):
    """Irregular, bent tooth. Writes layer colour (t, blood, dirt) per vertex."""
    dvec = Vector(direction).normalized()
    side = dvec.orthogonal().normalized()
    side = Matrix.Rotation(math.radians(twist), 3, dvec) @ side
    fwd = dvec.cross(side).normalized()
    kind = kind or rng.choices(["fang", "broken", "blunt", "stump"], [0.26, 0.34, 0.30, 0.10])[0]
    if kind == "stump":
        length *= rng.uniform(0.25, 0.4)
    elif kind == "broken":
        length *= rng.uniform(0.55, 0.8)
    sides = rng.choice([5, 6, 6])
    prof = [(math.cos(2 * math.pi * k / sides + 0.3) * w / 2 * rng.uniform(0.8, 1.12),
             math.sin(2 * math.pi * k / sides + 0.3) * d / 2 * rng.uniform(0.8, 1.12)) for k in range(sides)]
    bend = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)) * length * rng.uniform(0.05, 0.25)
    blood = rng.choice([0.0, 0.15, 0.3, 0.5, 0.7, 0.95]) * rng.uniform(0.7, 1.0)
    dirt = rng.uniform(0.0, 0.8)
    ts = [(-0.18, 0.80), (0.0, 1.0), (0.3, 1.06), (0.62, 0.86)]
    tip_scale = {"fang": 0.45, "broken": 0.78, "blunt": 0.75, "stump": 0.85}[kind]
    ts.append((1.0, tip_scale))
    rings = []
    for t, s in ts:
        ctr = Vector(base) + dvec * length * t + bend * max(t, 0) ** 2
        ring = []
        for x, y in prof:
            p = ctr + side * x * s + fwd * y * s
            ring.append(p)
        rings.append((t, ring))
    # fracture plane on broken / stump teeth, chipped corner on blunt
    t_last, last = rings[-1]
    if kind in ("broken", "stump"):
        tilt = (side * rng.uniform(-1, 1) + fwd * rng.uniform(-1, 1)).normalized()
        for i, p in enumerate(last):
            last[i] = p + dvec * (p - (Vector(base) + dvec * length)).dot(tilt) * rng.uniform(0.6, 1.2) \
                - dvec * rng.uniform(0, 0.25) * w
    elif kind == "blunt":
        i = rng.randrange(len(last))
        last[i] = last[i] - dvec * w * rng.uniform(0.3, 0.6)
    verts = []
    for t, ring in rings:
        row = []
        for p in ring:
            bv = bm.verts.new(p)
            bv[layer] = (max(t, 0.0), blood, dirt, 1.0)
            row.append(bv)
        verts.append(row)
    k = len(prof)
    for ra, rb in zip(verts, verts[1:]):
        for i in range(k):
            bm.faces.new((ra[i], ra[(i + 1) % k], rb[(i + 1) % k], rb[i]))
    bm.faces.new(list(reversed(verts[0])))
    if kind == "fang":
        apex = bm.verts.new(Vector(base) + dvec * length * 1.07 + bend * 1.15 + side * rng.uniform(-0.3, 0.3) * w)
        apex[layer] = (1.0, blood, dirt, 1.0)
        for i in range(k):
            bm.faces.new((verts[-1][i], verts[-1][(i + 1) % k], apex))
    else:
        bm.faces.new(verts[-1])


def teeth_row(bm, layer, slots, down, out_bias, lean, size):
    """slots: list of (base point, outward vector, is_front). down = growth direction."""
    for base, outward, front in slots:
        if rng.random() < 0.08:
            continue  # missing tooth
        L = rng.uniform(*size["front_len"]) if front else rng.uniform(*size["side_len"])
        if front and rng.random() < 0.18:
            L *= rng.uniform(1.25, 1.45)  # a few monstrous ones
        w = rng.uniform(0.075, 0.135)
        d = rng.uniform(0.055, 0.09)
        crooked = Vector((rng.uniform(-0.38, 0.38), rng.uniform(-0.2, 0.2), 0))
        dvec = Vector(down) + outward * rng.uniform(*out_bias) + Vector(lean) + crooked
        make_tooth(bm, layer, base, dvec, L, w, d, twist=rng.uniform(-35, 35))
        if rng.random() < 0.15:   # crowded second tooth growing behind
            inner = base - outward.normalized() * 0.06 + Vector((rng.uniform(-0.03, 0.03), 0, 0))
            make_tooth(bm, layer, inner, Vector(down) + crooked * 1.5, L * 0.6, w * 0.8, d * 0.8,
                       twist=rng.uniform(-40, 40))


def new_tooth_bm():
    bm = bmesh.new()
    layer = bm.verts.layers.float_color.new("tooth")
    return bm, layer
