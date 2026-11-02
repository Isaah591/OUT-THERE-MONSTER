"""
Numpy sculpting toolkit for the R08 high-fidelity rebuild.

Every body part is built the way a sculpt is: a nuanced base form (spline loft with varying
superellipse sections) is voxel-remeshed into a dense, even surface, then shaped by
vectorised brush operations in order of scale:

    large forms (pushes, dents)  ->  knife facets (Voronoi planar cells)  ->
    layered bark peels with torn edges, shallow fibrous tissue, chips  ->  decimate

Per-vertex float attributes record what each surface is, so the materials respond to the
geometry and the maps can be baked for Roblox later:
    layer   0 outer rust shell, 0.5 first under-layer, 1 deep layer
    tissue  exposed flesh
    tear    torn shell edge (the lighter fringe around every peel)
    convex  convexity (edge wear)        cavity  concavity (grime)
    blood   old blood
All lengths are metres (a Surf converts from object-local units with `unit`).
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from scipy.spatial import cKDTree


# ---------------------------------------------------------------------------
# Noise
# ---------------------------------------------------------------------------
class Perlin:
    """Vectorised 3D gradient noise, roughly in [-1, 1]."""

    def __init__(self, seed):
        r = np.random.default_rng(seed)
        self.perm = np.concatenate([r.permutation(256)] * 2)
        g = r.normal(size=(256, 3))
        self.g = g / np.linalg.norm(g, axis=1, keepdims=True)

    def __call__(self, p):
        p = np.asarray(p, dtype=np.float64)
        i0 = np.floor(p).astype(np.int64)
        f = p - i0
        i0 &= 255
        i1 = (i0 + 1) & 255
        u = f * f * f * (f * (f * 6 - 15) + 10)
        P, G = self.perm, self.g

        def corner(ix, iy, iz, ox, oy, oz):
            g = G[P[P[P[ix] + iy] + iz]]
            return g[:, 0] * (f[:, 0] - ox) + g[:, 1] * (f[:, 1] - oy) + g[:, 2] * (f[:, 2] - oz)

        x0, y0, z0 = i0.T
        x1, y1, z1 = i1.T
        ux, uy, uz = u.T
        lx = lambda a, b: a + ux * (b - a)
        ly = lambda a, b: a + uy * (b - a)
        lz = lambda a, b: a + uz * (b - a)
        return 1.8 * lz(ly(lx(corner(x0, y0, z0, 0, 0, 0), corner(x1, y0, z0, 1, 0, 0)),
                           lx(corner(x0, y1, z0, 0, 1, 0), corner(x1, y1, z0, 1, 1, 0))),
                        ly(lx(corner(x0, y0, z1, 0, 0, 1), corner(x1, y0, z1, 1, 0, 1)),
                           lx(corner(x0, y1, z1, 0, 1, 1), corner(x1, y1, z1, 1, 1, 1))))


def fbm(noise, p, octaves=4, lac=2.03, gain=0.5):
    s, a, f, norm = 0.0, 1.0, 1.0, 0.0
    for o in range(octaves):
        s = s + a * noise(p * f + 17.31 * o)
        norm += a
        a *= gain
        f *= lac
    return s / norm


class Cells:
    """Random 3D Voronoi cells over a box: nearest-seed index, F1/F2 and a value per cell."""

    def __init__(self, lo, hi, size, seed):
        r = np.random.default_rng(seed)
        lo, hi = np.asarray(lo, float) - size, np.asarray(hi, float) + size
        n = max(16, int(np.prod((hi - lo) / size)))
        self.pts = r.uniform(lo, hi, (n, 3))
        self.tree = cKDTree(self.pts)
        self.val = r.random(n)

    def query(self, p):
        d, i = self.tree.query(p, k=2)
        return d[:, 0], d[:, 1], i[:, 0]


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def unit(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v, axis=-1, keepdims=True) + 1e-12)


# ---------------------------------------------------------------------------
# Base forms: spline lofts with varying superellipse sections
# ---------------------------------------------------------------------------
def _catmull(P, t):
    """Catmull-Rom through rows of P (k, m) at fractional indices t."""
    P = np.asarray(P, float)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    i = np.clip(np.floor(t).astype(int), 0, len(P) - 4)
    u = (t - i)[:, None]
    p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
    return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)


KEYS = ("ws", "wn", "df", "db", "e", "rot", "ox", "oy")


def loft(keys, ref=(0, -1, 0), seg=28, step=0.025, caps=(0.06, 0.06), path=False):
    """Closed tube through key rings.
    keys: dicts with p (point) and half-extents: ws/wn (+/- side), df/db (front/back),
    or w / d for symmetric; e superellipse exponent; rot twist (deg); ox/oy offsets.
    The side axis is oriented toward +X where possible, front along `ref` (monster faces -Y).
    caps: rounded end-cap radius at start/end (0 = flat)."""
    rows = []
    for k in keys:
        w, d = k.get("w", 0.2), k.get("d", 0.2)
        rows.append([k.get("ws", w), k.get("wn", w), k.get("df", d), k.get("db", d), k.get("e", 3.0),
                     k.get("rot", 0.0), k.get("ox", 0.0), k.get("oy", 0.0)])
    pts = np.array([k["p"] for k in keys], float)
    seglen = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total = seglen.sum()
    n = max(4, int(total / step))
    # sample uniformly in arc length (approx: map length -> key index)
    cum = np.concatenate([[0], np.cumsum(seglen)])
    s = np.linspace(0, total, n)
    t = np.interp(s, cum, np.arange(len(pts)))
    C = _catmull(pts, t)
    R = _catmull(np.array(rows), t)
    T = np.gradient(C, axis=0)
    T = unit(T)
    ref = np.asarray(ref, float)
    rings = []
    th = np.linspace(0, 2 * np.pi, seg, endpoint=False) + np.pi / seg
    c, sn = np.cos(th), np.sin(th)
    for i in range(n):
        tt = T[i]
        f = ref - np.dot(ref, tt) * tt
        if np.linalg.norm(f) < 1e-6:
            f = np.array([0, 0, 1.0]) - tt[2] * tt
        f = unit(f)
        sd = np.cross(tt, f)
        if sd[0] < 0:
            sd = -sd
        ws, wn, df, db, e, rot, ox, oy = R[i]
        e = max(e, 1.2)
        x = np.sign(c) * np.abs(c) ** (2 / e) * np.where(c > 0, ws, wn)
        y = np.sign(sn) * np.abs(sn) ** (2 / e) * np.where(sn > 0, df, db)
        a = math.radians(rot)
        x, y = x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)
        ctr = C[i] + sd * ox + f * oy
        rings.append((ctr, ctr[None] + x[:, None] * sd + y[:, None] * f, tt))
    out = [r[1] for r in rings]
    # rounded caps
    for end, rad in ((0, caps[0]), (1, caps[1])):
        if rad <= 0:
            continue
        ctr, ring, tt = rings[0] if end == 0 else rings[-1]
        sgn = -1.0 if end == 0 else 1.0
        rad_v = ring - ctr
        rlen = np.linalg.norm(rad_v, axis=1, keepdims=True) + 1e-9
        extra = []
        for k in range(1, 6):
            ph = (math.pi / 2) * k / 6
            shrink = np.minimum(rad * (1 - math.cos(ph)), 0.92 * rlen)   # rounded edge of radius `rad`
            extra.append(ring - rad_v / rlen * shrink + sgn * tt * rad * math.sin(ph))
        out = (extra[::-1] + out) if end == 0 else (out + extra)
    bm = bmesh.new()
    vr = [[bm.verts.new(p) for p in ring] for ring in out]
    m = len(vr[0])
    for a, b in zip(vr, vr[1:]):
        for i in range(m):
            bm.faces.new((a[i], a[(i + 1) % m], b[(i + 1) % m], b[i]))
    bm.faces.new(list(reversed(vr[0])))
    bm.faces.new(vr[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if path:
        return bm, C, T
    return bm


def path_axes(co, C, T):
    """Per-vertex limb axis: tangent of the nearest path sample."""
    return T[cKDTree(C).query(co)[1]]


def merge_bm(dst, src):
    """Append bmesh `src` into `dst` (both closed shells; a later remesh fuses them)."""
    me = bpy.data.meshes.new("_tmp")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)
    return dst


def box_blob(center, size, e=3.0, seg=24, rings=14, round_top=0.5, round_bot=0.5):
    """Rounded superellipsoid-ish block (for feet, caps...): superellipse sections stacked in Z."""
    cx, cy, cz = center
    sx, sy, sz = size
    keys = []
    for i in range(rings + 1):
        v = i / rings
        z = cz - sz / 2 + sz * v
        k = 1.0
        if v < round_bot * 0.5:
            k = math.sqrt(max(0.0, 1 - ((round_bot * 0.5 - v) / (round_bot * 0.5)) ** 2)) * 0.6 + 0.4
        if v > 1 - round_top * 0.5:
            k = math.sqrt(max(0.0, 1 - ((v - (1 - round_top * 0.5)) / (round_top * 0.5)) ** 2)) * 0.6 + 0.4
        keys.append({"p": (cx, cy, z), "w": sx / 2 * k, "d": sy / 2 * k, "e": e})
    return loft(keys, ref=(0, -1, 0), seg=seg, step=sz / rings * 0.99, caps=(0, 0))


# ---------------------------------------------------------------------------
# Object helpers
# ---------------------------------------------------------------------------
def obj_from_bm(name, bm, col, mats=()):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    return ob


def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    me.name = old.name
    bpy.data.meshes.remove(old)


def remesh(ob, voxel):
    m = ob.modifiers.new("Remesh", 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = voxel
    m.adaptivity = 0.0
    apply_mods(ob)


def union_into(ob, others, voxel):
    """Fuse other closed meshes into ob through a voxel remesh (sculpt-style DynTopo merge)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for o in others:
        me = o.data.copy()
        me.transform(ob.matrix_world.inverted() @ o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        bpy.data.objects.remove(o)
    bm.to_mesh(ob.data)
    bm.free()
    remesh(ob, voxel)


def decimate(ob, ratio):
    if ratio >= 0.999:
        return
    m = ob.modifiers.new("Decimate", 'DECIMATE')
    m.decimate_type = 'COLLAPSE'
    m.ratio = ratio
    m.use_collapse_triangulate = True
    apply_mods(ob)


def lowpoly(ob, target_faces, jitter=0.008, seed=0, dissolve_deg=5.0, levels=4, remesh_after=None):
    """Knife-cut facets the way a low-poly sculpt is made: decimate the shaped form down to
    large facets, jitter the vertices so neighbouring planes meet at clear angles, dissolve
    near-coplanar triangles into irregular polygons, then re-densify with SIMPLE subdivision
    (every facet stays planar and every edge stays straight and crisp) so the damage pass
    has resolution to cut into."""
    me = ob.data
    decimate(ob, max(1e-4, target_faces / max(1, len(me.polygons))))
    me = ob.data
    r = np.random.default_rng(seed)
    n = len(me.vertices)
    co = np.empty(n * 3, np.float32)
    me.vertices.foreach_get("co", co)
    nr = np.empty(n * 3, np.float32)
    me.vertex_normals.foreach_get("vector", nr)
    co = co.reshape(-1, 3) + nr.reshape(-1, 3) * r.uniform(-jitter, jitter, (n, 1))
    me.vertices.foreach_set("co", co.astype(np.float32).ravel())
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(dissolve_deg), use_dissolve_boundaries=False,
                             verts=bm.verts, edges=bm.edges)
    bm.to_mesh(me)
    bm.free()
    m = ob.modifiers.new("Densify", 'SUBSURF')
    m.subdivision_type = 'SIMPLE'
    m.levels = m.render_levels = levels
    apply_mods(ob)
    if remesh_after:                                  # even resolution for the flake mosaic
        remesh(ob, remesh_after)


def set_attr(me, name, vals, domain='POINT'):
    a = me.attributes.get(name)
    if a is None:
        a = me.attributes.new(name, 'FLOAT', domain)
    a.data.foreach_set("value", np.asarray(vals, np.float32))


def get_attr(me, name):
    a = me.attributes.get(name)
    out = np.zeros(len(me.vertices), np.float32)
    if a is not None:
        a.data.foreach_get("value", out)
    return out.astype(np.float64)


# ---------------------------------------------------------------------------
# Surface: dense mesh as numpy arrays
# ---------------------------------------------------------------------------
class Surf:
    ATTRS = ("layer", "tissue", "tear", "blood")

    def __init__(self, ob, unit_=1.0):
        me = ob.data
        self.ob, self.u = ob, unit_
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", co)
        self.co = co.reshape(-1, 3).astype(np.float64) * unit_
        e = np.empty(len(me.edges) * 2, np.int32)
        me.edges.foreach_get("vertices", e)
        self.E = e.reshape(-1, 2).astype(np.int64)
        me.calc_loop_triangles()
        t = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", t)
        self.T = t.reshape(-1, 3).astype(np.int64)
        self.n = n
        self.deg = np.maximum(np.bincount(self.E.ravel(), minlength=n), 1).astype(np.float64)
        self.a = {k: np.zeros(n) for k in self.ATTRS}
        for k in self.ATTRS:
            if me.attributes.get(k) is not None:
                self.a[k] = get_attr(me, k)
        self.h = float(np.linalg.norm(self.co[self.E[:, 0]] - self.co[self.E[:, 1]], axis=1).mean())

    # -- geometry queries
    def normals(self):
        a, b, c = self.co[self.T[:, 0]], self.co[self.T[:, 1]], self.co[self.T[:, 2]]
        fn = np.cross(b - a, c - a)
        vn = np.zeros_like(self.co)
        for k in range(3):
            for j in range(3):
                vn[:, j] += np.bincount(self.T[:, k], fn[:, j], self.n)
        return unit(vn)

    def nb_mean(self, v):
        v = np.asarray(v, float)
        E, n = self.E, self.n
        if v.ndim == 1:
            return (np.bincount(E[:, 0], v[E[:, 1]], n) + np.bincount(E[:, 1], v[E[:, 0]], n)) / self.deg
        return np.stack([self.nb_mean(v[:, j]) for j in range(v.shape[1])], 1)

    def blur(self, v, iters=2):
        for _ in range(iters):
            v = 0.5 * v + 0.5 * self.nb_mean(v)
        return v

    def smooth(self, iters=2, lam=0.5, mu=-0.53, w=None):
        for _ in range(iters):
            for f in (lam, mu):
                d = (self.nb_mean(self.co) - self.co) * f
                if w is not None:
                    d *= w[:, None]
                self.co += d

    def curvature(self):
        """Signed mean-curvature proxy in 1/m: > 0 convex, < 0 concave."""
        lap = self.nb_mean(self.co) - self.co
        return -(lap * self.normals()).sum(1) / (self.h * self.h) * 2.0

    def grad_mag(self, s):
        """Per-vertex |grad s| (per metre) estimated over incident edges."""
        E = self.E
        L = np.linalg.norm(self.co[E[:, 0]] - self.co[E[:, 1]], axis=1) + 1e-9
        g = np.abs(s[E[:, 0]] - s[E[:, 1]]) / L
        return (np.bincount(E[:, 0], g, self.n) + np.bincount(E[:, 1], g, self.n)) / self.deg + 1e-6

    def grad_vec(self, s):
        """Per-vertex gradient vector of a scalar field (least-squares-ish over edges)."""
        E = self.E
        d = self.co[E[:, 1]] - self.co[E[:, 0]]
        ds = (s[E[:, 1]] - s[E[:, 0]]) / ((d * d).sum(1) + 1e-12)
        g = np.zeros_like(self.co)
        for j in range(3):
            g[:, j] = np.bincount(E[:, 0], ds * d[:, j], self.n) + np.bincount(E[:, 1], ds * d[:, j], self.n)
        return g / self.deg[:, None]

    def step(self, s, wall):
        """Sharp but resolved 0->1 transition across the iso-line s = 0, `wall` metres wide."""
        g = self.grad_mag(s)
        return smoothstep(-0.5, 0.5, s / (g * wall))

    # -- write back
    def write(self, extra=None):
        me = self.ob.data
        me.vertices.foreach_set("co", (self.co / self.u).astype(np.float32).ravel())
        me.update()
        for k, v in self.a.items():
            set_attr(me, k, np.clip(v, 0, 1))
        for k, v in (extra or {}).items():
            set_attr(me, k, v)


# ---------------------------------------------------------------------------
# Brushes
# ---------------------------------------------------------------------------
def falloff(S, center, radius):
    d = (S.co - np.asarray(center, float)) / np.asarray(radius, float)
    return np.exp(-(d * d).sum(1))


def push(S, center, radius, amount, axis=None, w=None):
    """Gaussian brush: move along the vertex normals (or a fixed axis) by `amount` metres."""
    f = falloff(S, center, radius) * amount
    if w is not None:
        f = f * w
    d = S.normals() if axis is None else unit(axis)[None]
    S.co += f[:, None] * d


def flatten(S, center, radius, normal, strength=1.0, offset=0.0, trim=True):
    """Flatten / trim brush: pull vertices toward a plane through `center` (+offset along the
    normal). trim: only cut down what stands above the plane (a planar knife cut)."""
    nrm = unit(normal)
    f = falloff(S, center, radius) * strength
    dist = ((S.co - np.asarray(center, float)) @ nrm) - offset
    if trim:
        dist = np.maximum(dist, 0.0)
    S.co -= (f * dist)[:, None] * nrm[None]


def dents(S, count, r_range, depth_range, seed, w=None):
    r = np.random.default_rng(seed)
    nrm = S.normals()
    pool = np.arange(S.n) if w is None else np.flatnonzero(w > 0.5)
    for i in r.choice(pool, size=min(count, len(pool)), replace=False):
        rad = r.uniform(*r_range)
        f = falloff(S, S.co[i], (rad, rad, rad)) * r.uniform(*depth_range)
        S.co -= f[:, None] * nrm


def warp(S, amp, freq, seed, w=None):
    """Low-frequency 3D warp of the whole form (asymmetry, lumpy irregular planes)."""
    P = Perlin(seed)
    p = S.co * freq
    d = np.stack([fbm(P, p + o, 3) for o in (0.0, 31.7, 71.3)], 1) * amp
    if w is not None:
        d *= w[:, None]
    S.co += d


def facets(S, cell, strength=1.0, tilt=5.0, seed=0, w=None, agree=0.35, chip=0.0, chip_p=0.0, k=7):
    """Knife facets. The surface is split into Voronoi cells; every cell gets a cutting plane
    (its mean tangent plane, slightly tilted). Each vertex then moves along its normal to the
    nearest of the neighbouring planes, so the result is a polyhedral envelope whose edges lie
    exactly on plane/plane intersections: large irregular planar facets with crisp ridges and
    valleys, as on R08. chip/chip_p: a fraction of planes is set `chip` m deeper (chipped
    facets)."""
    r = np.random.default_rng(seed)
    nrm = S.normals()
    off = r.uniform(0, cell, 3)
    key = np.floor((S.co + off) / cell).astype(np.int64)
    order = r.permutation(S.n)
    _, first = np.unique(key[order], axis=0, return_index=True)
    sidx = order[first]
    m = len(sidx)
    # cell membership (nearest seed with an agreeing normal) -> one plane per cell
    tree = cKDTree(S.co[sidx])
    kk = min(6, m)
    _, cand = tree.query(S.co, k=kk)
    cand = cand.reshape(S.n, kk)
    ok = np.einsum('nkj,nj->nk', nrm[sidx][cand], nrm) > 0.5
    lab = cand[np.arange(S.n), np.where(ok.any(1), ok.argmax(1), 0)]
    cnt = np.bincount(lab, minlength=m).astype(float) + 1e-9
    cen = np.stack([np.bincount(lab, S.co[:, j], m) for j in range(3)], 1) / cnt[:, None]
    pn = unit(np.stack([np.bincount(lab, nrm[:, j], m) for j in range(3)], 1))
    ax = r.normal(size=(m, 3))
    ax = unit(ax - (ax * pn).sum(1, keepdims=True) * pn)
    ang = np.radians(r.uniform(0, tilt, m))
    pn = pn * np.cos(ang)[:, None] + ax * np.sin(ang)[:, None]
    # tangent (outermost) plane of each cell: every member vertex lies on or below it
    h = (S.co * pn[lab]).sum(1)
    top = np.full(m, -np.inf)
    np.maximum.at(top, lab, h)
    is_chip = r.random(m) < chip_p
    top = top - np.where(is_chip, r.uniform(0.4, 1.0, m) * chip, 0.0)
    # circumscribed envelope: each vertex moves out along its normal to the first plane it
    # meets; chip planes may also cut in (a knife chip through the edge).
    ctree = cKDTree(cen)
    kk = min(k, m)
    _, J = ctree.query(S.co, k=kk)
    J = J.reshape(S.n, kk)
    nj = pn[J]
    cos = np.einsum('nkj,nj->nk', nj, nrm)
    d = np.einsum('nj,nkj->nk', S.co, nj) - top[J]           # <= 0 below the plane
    t = -d / np.maximum(cos, 1e-3)
    good = cos > agree
    out = np.where(good & (t >= 0), t, np.inf).min(1)
    cut = np.where(good & is_chip[J] & (t < 0), t, np.inf).min(1)
    best = np.where(np.isfinite(cut), cut, np.where(np.isfinite(out), out, 0.0))
    best = np.clip(best, -chip - 1e-4, min(0.12 * cell, 0.025))
    s = np.full(S.n, strength) if w is None else strength * w
    S.co += (s * best)[:, None] * nrm
    return lab


# ---------------------------------------------------------------------------
# Damage: layered bark peels, torn edges, shallow fibrous tissue
# ---------------------------------------------------------------------------
def zone_field(co, zones):
    """zones: (centre, radii, strength). Smooth max of gaussian blobs, 0..1."""
    out = np.zeros(len(co))
    for c, rad, s in zones:
        d = (co - np.asarray(c, float)) / np.asarray(rad, float)
        out = np.maximum(out, s * np.exp(-(d * d).sum(1)))
    return out


def snap_iso(S, s):
    """Move vertices onto the s = 0 iso-line along their shortest crossing edge (by less than
    half an edge), so torn edges follow the field instead of the voxel grid."""
    E = S.E
    si, sj = s[E[:, 0]], s[E[:, 1]]
    x = (si * sj) < 0
    e, a, b = E[x], si[x], sj[x]
    lam = a / (a - b)
    v = np.concatenate([e[:, 0], e[:, 1]])
    o = np.concatenate([e[:, 1], e[:, 0]])
    lv = np.concatenate([lam, 1 - lam])
    order = np.lexsort((lv, v))
    v, o, lv = v[order], o[order], lv[order]
    first = np.unique(v, return_index=True)[1]
    v, o, lv = v[first], o[first], lv[first]
    m = lv < 0.5
    v, o, lv = v[m], o[m], lv[m]
    S.co[v] += (S.co[o] - S.co[v]) * lv[:, None]
    s = s.copy()
    s[v] = 0.0
    return s


def _z(x):
    return (x - x.mean()) / (x.std() + 1e-9)


def flakes(S, cell=0.055, crack=0.005, depth=0.0045, lift=0.0025, tilt=0.06, seed=0, w=None):
    """Rust flake mosaic: jagged (domain-warped) Voronoi plates with dark cracks between them;
    each plate is lifted or sunk and tilted a little, so the shell reads as layered flakes.
    Returns a per-vertex plate value in [-1, 1] so peels can follow the flake outlines."""
    P = Perlin(seed)
    warp = np.stack([fbm(P, S.co * 11.0 + o, 2) for o in (0.0, 13.1, 27.7)], 1) * cell * 0.30
    q = S.co + warp
    cells = Cells(S.co.min(0), S.co.max(0), cell, seed + 1)
    d, i = cells.tree.query(q, k=2)
    edge = d[:, 1] - d[:, 0]                                     # ~0 on a plate border
    idx = i[:, 0]
    crackm = smoothstep(crack, 0.0, edge)
    nrm = S.normals()
    r = np.random.default_rng(seed + 2)
    m = len(cells.pts)
    off = r.uniform(-1, 1, m) * lift
    tdir = unit(r.normal(size=(m, 3)))
    tl = ((q - cells.pts[idx]) * tdir[idx]).sum(1) * tilt
    disp = off[idx] + tl - depth * crackm
    if w is not None:
        disp = disp * w
        crackm = crackm * w
    S.co += disp[:, None] * nrm
    S.a["crack"] = np.maximum(S.a.get("crack", np.zeros(S.n)), crackm)
    S.a["flake"] = cells.val[idx]
    return 2 * cells.val[idx] - 1


def damage(S, peel_zones, wound_zones, axis, seed, t1=0.024, t2=0.013, tissue=0.020,
           cover=0.0, jag=1.0, lips=0.006, fibre_dir=None, w=None, extra=None, tear_amt=1.0,
           n_flaps=0, chunk=None):
    """Bark-like peel of the rust shell inside `peel_zones` (two stepped strata with torn
    sawtooth edges and partly curled lips) and shallow fibrous tissue inside `wound_zones`.
    `axis` is the part's long axis (features stretch along it); `cover` biases coverage;
    `extra` an additional per-vertex term for the peel field (e.g. chipped convex edges)."""
    nrm = S.normals()
    a = unit(axis)
    if a.ndim == 1:
        a = np.broadcast_to(a, S.co.shape)
    P1, P2, P3, P4 = Perlin(seed), Perlin(seed + 1), Perlin(seed + 2), Perlin(seed + 3)
    cells = Cells(S.co.min(0), S.co.max(0), 0.065, seed + 4)
    tree = cKDTree(S.co)                                          # zone centres sit on the surface
    snapz = lambda zs: [(S.co[tree.query(np.asarray(c, float))[1]], r_, st) for c, r_, st in zs]
    zp0 = zone_field(S.co, snapz(peel_zones))
    zw0 = zone_field(S.co, snapz(wound_zones))
    zp0 = np.maximum(zp0, zw0)

    def stretch(co, k):
        al = (co * a).sum(1)
        return co + ((1 / k) - 1) * al[:, None] * a

    def f1(co):
        q = stretch(co, 2.4)
        ch = chunk if chunk is not None else 2 * cells.val[cells.query(co)[2]] - 1   # whole flakes / chips
        v = (2.7 * zp0 - 1.35 + cover + 0.45 * _z(fbm(P1, q * 5.5, 3)) + (0.55 if chunk is not None else 0.32) * ch
             + 0.22 * jag * _z(P2(stretch(co, 3.5) * 20.0))          # splinters along the limb
             + 0.06 * jag * _z(P2(q * 55.0 + 5.3)))                  # torn-paper sawtooth
        if extra is not None:
            v = v + extra
        if w is not None:
            v = np.where(w > 0.5, v, -1.0)
        return v

    def f2(co, s1):
        q = stretch(co, 2.4)
        return np.minimum(s1 - 0.28 + 0.45 * _z(fbm(P3, q * 9.0, 3)) + 0.12 * jag * _z(P4(q * 40.0)), s1)

    def ff(co, s2):
        q = stretch(co, 2.4)
        return np.minimum(2.4 * zw0 - 1.25 + 0.4 * _z(fbm(P1, q * 11.0 + 9.1, 3)), s2)

    s1 = snap_iso(S, f1(S.co))
    s2 = snap_iso(S, f2(S.co, s1))
    sf = snap_iso(S, ff(S.co, s2))
    S1, S2, Sf = (s1 > 0) * 1.0, (s2 > 0) * 1.0, (sf > 0) * 1.0
    # fibres: ridged noise stretched hard along the limb (strands of tissue)
    fd = unit(fibre_dir) if fibre_dir is not None else a
    if fd.ndim == 1:
        fd = np.broadcast_to(fd, S.co.shape)
    alf = (S.co * fd).sum(1)
    qf = S.co + ((1 / 7.0) - 1) * alf[:, None] * fd
    fib = np.clip(1.0 - np.abs(P3(qf * 30.0)), 0, 1) ** 2.5        # thick vertical strands
    fib2 = np.clip(1.0 - np.abs(P4(qf * 75.0)), 0, 1) ** 3
    swell = smoothstep(-1.0, 1.0, _z(fbm(P2, S.co * 12.0, 2)))
    depth = (t1 * S1 + S2 * (t2 - 0.005 * fib + 0.004 * swell)
             + Sf * (tissue * (0.55 + 0.45 * swell) - 0.012 * fib - 0.004 * fib2))
    # distance (approx.) outside the torn edge -> curled lips and the light torn fringe
    g1 = S.grad_mag(s1)
    dist = np.where(s1 <= 0, -s1 / g1, 0.0)
    rim = np.clip(1 - dist / 0.018, 0, 1) ** 0.6 * (s1 <= 0)            # lifted plate edges
    gv = unit(S.grad_vec(s1))
    hang = np.clip(-gv[:, 2], 0, 1)                                      # plate above a hole hangs over it
    lipmask = smoothstep(-0.3, 0.9, _z(fbm(P4, stretch(S.co, 2.4) * 5.0, 2)))
    depth -= lips * rim * lipmask * (0.35 + 0.65 * hang)
    # hinge points for lifted shell plates: on the torn rim, inside the strongest zones
    if n_flaps:
        r = np.random.default_rng(seed + 9)
        cand = np.flatnonzero((np.abs(s1) < 1e-9) & (zp0 > 0.5))
        r.shuffle(cand)
        chosen = []
        for i in cand:
            if len(chosen) >= n_flaps:
                break
            if all(np.linalg.norm(S.co[i] - S.co[j]) > 0.08 for j in chosen):
                chosen.append(i)
        flaps = []
        for i in chosen:
            n = nrm[i]
            d = gv[i] - (gv[i] @ n) * n
            if np.linalg.norm(d) < 1e-6:
                continue
            flaps.append((S.co[i] - depth[i] * n, n, unit(d)))
        S.flaps = getattr(S, "flaps", []) + flaps
    S.co -= depth[:, None] * nrm
    S.a["layer"] = np.maximum(S.a["layer"], 0.5 * S1 + 0.5 * S2)
    S.a["tissue"] = np.maximum(S.a["tissue"], Sf)
    tear = np.clip(1 - dist / 0.009, 0, 1) * (s1 <= 0) * tear_amt
    S.a["tear"] = np.maximum(S.a["tear"], tear)
    return S1, S2, Sf


def add_flaps(ob, flaps, seed, unit_=1.0):
    """Lifted shell plates hinged on a torn rim and overhanging the wound: a thick jagged
    plate (rust shell on top, under-layer beneath, torn edges) rotated outward 15-40 deg.
    flaps: (hinge point, surface normal, direction into the hole), metres."""
    if not flaps:
        return
    r = np.random.default_rng(seed)
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    lay = {k: bm.verts.layers.float.get(k) or bm.verts.layers.float.new(k)
           for k in ("layer", "tear", "tissue", "blood", "convex", "cavity")}
    for p, n, d in flaps:
        p, n, d = np.asarray(p), unit(np.asarray(n)), unit(np.asarray(d))
        t = np.cross(n, d)
        L, W, th = r.uniform(0.035, 0.07), r.uniform(0.035, 0.065), r.uniform(0.010, 0.016)
        k = 7
        far = [(L * r.uniform(0.55, 1.0) * (0.8 if j % 2 else 1.0), W / 2 - W * j / (k - 1)) for j in range(k)]
        uv = [(-0.014, -W / 2), (-0.014, W / 2)] + far
        ang = -math.radians(r.uniform(15, 40))
        c, sn = math.cos(ang), math.sin(ang)

        def place(u, v, h):
            q = d * u + t * v + n * h
            # rotate about the hinge axis t (Rodrigues; t is perpendicular to d and n)
            q = q * c + np.cross(t, q) * sn + t * (t @ q) * (1 - c)
            return (p + q) / unit_
        top = [bm.verts.new(place(u, v, 0.003)) for u, v in uv]
        bot = [bm.verts.new(place(u, v, -th)) for u, v in uv]
        for v_ in top:
            v_[lay["layer"]], v_[lay["tear"]] = 0.0, 0.25
        for v_ in bot:
            v_[lay["layer"]], v_[lay["tear"]] = 0.5, 0.7
        f = bm.faces.new(top)
        bm.faces.new(list(reversed(bot)))
        m = len(top)
        for j in range(m):
            bm.faces.new((top[(j + 1) % m], top[j], bot[j], bot[(j + 1) % m]))
        bmesh.ops.recalc_face_normals(bm, faces=[f])
    bm.to_mesh(me)
    bm.free()


def blood(S, seed, drips=24, near=0.05, down=(0, 0, -1)):
    """Old blood: stains around exposed tissue plus a few runs down the surface."""
    r = np.random.default_rng(seed)
    t = S.a["tissue"]
    src = np.flatnonzero(t > 0.5)
    b = np.zeros(S.n)
    if len(src):
        tree = cKDTree(S.co[src])
        d, _ = tree.query(S.co, k=1)
        b = np.exp(-d / near) * 0.8
        dn = unit(down)
        nrm = S.normals()
        side = 1 - np.abs(nrm @ dn)
        P = Perlin(seed)
        for i in r.choice(src, size=min(drips, len(src)), replace=False):
            o = S.co[i]
            rel = S.co - o
            drop = rel @ dn
            hor = np.linalg.norm(rel - drop[:, None] * dn[None], axis=1)
            L = r.uniform(0.06, 0.22)
            wid = r.uniform(0.008, 0.02) * (1 + 0.5 * P(S.co * 9.0))
            run = np.exp(-(hor / wid) ** 2) * (drop > 0) * np.clip(1 - drop / L, 0, 1) * side
            b = np.maximum(b, run * r.uniform(0.6, 1.0))
    S.a["blood"] = np.maximum(S.a["blood"], b)


def finish(S, ob, decimate_ratio=1.0, sharp_deg=38.0):
    """Write coords + attributes, add convexity/cavity, decimate, set shading."""
    k = S.curvature()
    k = S.blur(k, 5)
    convex = smoothstep(9.0, 40.0, k)
    cavity = smoothstep(6.0, 35.0, -k)
    S.write(extra={"convex": convex, "cavity": cavity})
    decimate(ob, decimate_ratio)
    me = ob.data
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    return ob
