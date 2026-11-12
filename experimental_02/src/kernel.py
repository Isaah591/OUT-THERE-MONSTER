"""Geometry kernel for ASTRA R08 - Experimental Model 02 (written from scratch, numpy only).

The creature is built the way the sheet reads: blocky, planar, low-poly forms ("coarse" meshes)
carrying a shell of small, irregular, overlapping rust plates.  Where the plates are torn away a
recessed under-surface with muscle strands shows.  Nothing here imports or reads earlier builds.

Coarse mesh  -> planar faces (quads / n-gons) with a `kind` per face
Shell        -> every plated coarse face is cut into small cells, the cells are grouped into
                plates (noisy Voronoi), each plate is raised to its own height with its own tilt
                and closed with side walls; several layers overlap.
"""
import numpy as np

# ----------------------------------------------------------------------------- small helpers


def unit(v, axis=-1):
    v = np.asarray(v, float)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def rot_axis(axis, ang):
    """Rotation matrix about `axis` by `ang` radians."""
    a = unit(axis)
    c, s = np.cos(ang), np.sin(ang)
    x, y, z = a
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.uint64) * np.uint64(374761393) + iy.astype(np.uint64) * np.uint64(668265263)
         + iz.astype(np.uint64) * np.uint64(2246822519) + np.uint64(seed) * np.uint64(3266489917))
    h &= np.uint64(0xFFFFFFFF)
    h = ((h ^ (h >> np.uint64(15))) * np.uint64(2246822519)) & np.uint64(0xFFFFFFFF)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(3266489917)) & np.uint64(0xFFFFFFFF)
    h = h ^ (h >> np.uint64(16))
    return h.astype(np.float64) / 4294967296.0


def vnoise(p, freq, seed=0):
    """Smooth value noise in [0, 1] at points p (n, 3)."""
    q = np.asarray(p, float) * freq + 1000.0
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = 0.0
    for dx in (0, 1):
        wx = f[:, 0] if dx else 1 - f[:, 0]
        for dy in (0, 1):
            wy = f[:, 1] if dy else 1 - f[:, 1]
            for dz in (0, 1):
                wz = f[:, 2] if dz else 1 - f[:, 2]
                out = out + wx * wy * wz * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(p, freq, octaves=3, seed=0):
    out, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * vnoise(p, freq * 2 ** o, seed + 17 * o)
        tot += amp
        amp *= 0.5
    return out / tot


def cnoise(p, freq, seed=0):
    """Blocky (cellular, piecewise-constant) noise in [0, 1] - gives stepped, chipped edges."""
    q = np.floor(np.asarray(p, float) * freq + 1000.0).astype(np.int64)
    return _hash(q[:, 0], q[:, 1], q[:, 2], seed)


# ----------------------------------------------------------------------------- coarse meshes


class Coarse:
    """A low-poly mesh of planar faces.  kind: 'plate' (gets the rust shell), 'tissue', 'gum',
    'socket', 'void', 'core' (dark under-body only)."""

    def __init__(self, name="part"):
        self.name = name
        self.V = []
        self.F = []
        self.kind = []
        self.grain = []
        self.tag = []
        self.patch = []          # None: plates stay on this face; an id: plates wrap across the patch

    def v(self, p):
        self.V.append(np.asarray(p, float).copy())
        return len(self.V) - 1

    def vs(self, pts):
        return [self.v(p) for p in pts]

    def f(self, idx, kind="plate", grain=None, tag="", patch=None):
        self.F.append([int(i) for i in idx])
        self.kind.append(kind)
        self.grain.append(None if grain is None else np.asarray(grain, float))
        self.tag.append(tag)
        self.patch.append(patch)

    def arrays(self):
        return np.array(self.V, float).reshape(-1, 3)

    def transform(self, M, t=(0, 0, 0)):
        M = np.asarray(M, float)
        t = np.asarray(t, float)
        self.V = [M @ p + t for p in self.V]
        self.grain = [None if g is None else M @ g for g in self.grain]
        return self

    def extend(self, other):
        o = len(self.V)
        self.V += [p.copy() for p in other.V]
        self.F += [[i + o for i in f] for f in other.F]
        self.kind += list(other.kind)
        self.grain += list(other.grain)
        self.tag += list(other.tag)
        self.patch += list(other.patch)
        return self

    def face_normal(self, fi):
        P = self.arrays()[self.F[fi]]
        return newell(P)

    def face_center(self, fi):
        return self.arrays()[self.F[fi]].mean(0)


def newell(P):
    n = np.zeros(3)
    m = len(P)
    for i in range(m):
        a, b = P[i], P[(i + 1) % m]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return unit(n)


def ring_points(c, ex, ey, half, chamfer=0.22, rng=None, jit=0.0, sides=8):
    """Chamfered-rectangle ring (8 points, counter-clockwise about ex x ey).
    half = (a_pos, a_neg, b_pos, b_neg) half extents along +ex, -ex, +ey, -ey (or (a, b))."""
    if len(half) == 2:
        ap = an = half[0]
        bp = bn = half[1]
    else:
        ap, an, bp, bn = half
    k = chamfer * min(ap, an, bp, bn)
    if sides == 4:
        pts = [(ap, -bn), (ap, bp), (-an, bp), (-an, -bn)]
    else:
        pts = [(ap - k, -bn), (ap, -bn + k), (ap, bp - k), (ap - k, bp),
               (-an + k, bp), (-an, bp - k), (-an, -bn + k), (-an + k, -bn)]
    out = []
    for (a, b) in pts:
        if rng is not None and jit > 0:
            a += rng.normal(0, jit)
            b += rng.normal(0, jit)
        out.append(np.asarray(c, float) + a * np.asarray(ex) + b * np.asarray(ey))
    return out


def path_frames(P, xhint):
    """Tangent / lateral / depth frames along a polyline (mitred at the joints)."""
    P = np.asarray(P, float)
    n = len(P)
    T, EX, EY = [], [], []
    for i in range(n):
        if i == 0:
            t = P[1] - P[0]
        elif i == n - 1:
            t = P[-1] - P[-2]
        else:
            t = unit(P[i + 1] - P[i]) + unit(P[i] - P[i - 1])
        t = unit(t)
        ex = np.asarray(xhint, float)
        ex = unit(ex - (ex @ t) * t)
        ey = np.cross(t, ex)
        T.append(t)
        EX.append(ex)
        EY.append(ey)
    return np.array(T), np.array(EX), np.array(EY)


def loft(name, P, halves, xhint, chamfer=0.22, rng=None, jit=0.0, caps=("plate", "plate"),
         kind="plate", sides=8, twist=None, cap_tags=("cap0", "cap1")):
    """Blocky beam through path points P with a chamfered-rectangle section at each point."""
    co = Coarse(name)
    P = np.asarray(P, float)
    T, EX, EY = path_frames(P, xhint)
    rings = []
    for i in range(len(P)):
        ex, ey = EX[i], EY[i]
        if twist is not None and twist[i] != 0.0:
            R = rot_axis(T[i], twist[i])
            ex, ey = R @ ex, R @ ey
        ch = chamfer[i] if np.ndim(chamfer) else chamfer
        rings.append(co.vs(ring_points(P[i], ex, ey, halves[i], ch, rng, jit, sides)))
    m = len(rings[0])
    for i in range(len(P) - 1):
        g = unit(P[i + 1] - P[i])
        for j in range(m):
            co.f([rings[i][j], rings[i][(j + 1) % m], rings[i + 1][(j + 1) % m], rings[i + 1][j]],
                 kind=kind, grain=g, tag=f"side{j}")
    if caps[0]:
        co.f(rings[0][::-1], kind=caps[0], grain=EX[0], tag=cap_tags[0])
    if caps[1]:
        co.f(rings[-1], kind=caps[1], grain=EX[-1], tag=cap_tags[1])
    co.rings = rings
    co.frames = (T, EX, EY)
    co.path = P
    return co


def loft_poly(name, P, sections, xhint, kinds, rng=None, jit=0.0, caps=("core", "core")):
    """Beam with an arbitrary section: sections[i] = list of (a, b) in the ring frame (ex, ey),
    counter-clockwise about the path; kinds[j] = kind of the side from point j to j+1."""
    co = Coarse(name)
    P = np.asarray(P, float)
    T, EX, EY = path_frames(P, xhint)
    rings = []
    for i in range(len(P)):
        pts = []
        for (a, b) in sections[i]:
            p = P[i] + a * EX[i] + b * EY[i]
            if rng is not None and jit > 0:
                p = p + rng.normal(0, jit, 3)
            pts.append(p)
        rings.append(co.vs(pts))
    m = len(rings[0])
    for i in range(len(P) - 1):
        g = unit(P[i + 1] - P[i])
        for j in range(m):
            co.f([rings[i][j], rings[i][(j + 1) % m], rings[i + 1][(j + 1) % m], rings[i + 1][j]],
                 kind=kinds[j], grain=g, tag=f"side{j}")
    if caps[0]:
        co.f(rings[0][::-1], kind=caps[0], grain=EX[0], tag="cap0")
    if caps[1]:
        co.f(rings[-1], kind=caps[1], grain=EX[-1], tag="cap1")
    co.rings = rings
    co.frames = (T, EX, EY)
    co.path = P
    return co


def box(name, c, ex, ey, ez, half, kind="plate", rng=None, jit=0.0, taper=(1.0, 1.0)):
    """Battered box: centre c, axes ex/ey/ez, half sizes; the +ez end scaled by taper."""
    co = Coarse(name)
    c = np.asarray(c, float)
    ex, ey, ez = (np.asarray(a, float) for a in (ex, ey, ez))
    a, b, h = half
    P = []
    for sz, tx, ty in ((-1, 1.0, 1.0), (1, taper[0], taper[1])):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = c + sx * a * tx * ex + sy * b * ty * ey + sz * h * ez
            if rng is not None and jit > 0:
                p = p + rng.normal(0, jit, 3)
            P.append(p)
    i = co.vs(P)
    co.f([i[3], i[2], i[1], i[0]], kind=kind, grain=ex, tag="-z")
    co.f([i[4], i[5], i[6], i[7]], kind=kind, grain=ex, tag="+z")
    co.f([i[0], i[1], i[5], i[4]], kind=kind, grain=ez, tag="-y")
    co.f([i[2], i[3], i[7], i[6]], kind=kind, grain=ez, tag="+y")
    co.f([i[1], i[2], i[6], i[5]], kind=kind, grain=ez, tag="+x")
    co.f([i[3], i[0], i[4], i[7]], kind=kind, grain=ez, tag="-x")
    return co


# ----------------------------------------------------------------------------- offset vectors


def offset_vectors(co, eps=0.03, kinds=("plate",), limit=2.2):
    """Per coarse vertex / edge: the vector d such that p + h*d lies on every adjacent plated
    face's plane raised by h (mitred corners).  Returns (d_vert dict, d_edge dict, face normals)."""
    V = co.arrays()
    FN = np.array([newell(V[f]) for f in co.F])
    vfaces = {}
    efaces = {}
    for fi, f in enumerate(co.F):
        if co.kind[fi] not in kinds:
            continue
        m = len(f)
        for k in range(m):
            vfaces.setdefault(f[k], []).append(fi)
            e = (min(f[k], f[(k + 1) % m]), max(f[k], f[(k + 1) % m]))
            efaces.setdefault(e, []).append(fi)

    def solve(fs):
        N = FN[fs]
        A = N.T @ N + eps * len(fs) * np.eye(3)
        d = np.linalg.solve(A, N.sum(0)) * (1 + eps)
        L = np.linalg.norm(d)
        if L > limit:
            d *= limit / L
        return d

    dv = {vi: solve(fs) for vi, fs in vfaces.items()}
    de = {e: solve(fs) for e, fs in efaces.items()}
    return dv, de, FN


# ----------------------------------------------------------------------------- fine cells


def _bilinear(q, ku, kv):
    u = np.linspace(0, 1, ku + 1)[:, None, None]
    v = np.linspace(0, 1, kv + 1)[None, :, None]
    return (1 - u) * (1 - v) * q[0] + u * (1 - v) * q[1] + u * v * q[2] + (1 - u) * v * q[3]


def refine_face(poly, cell):
    """Cut a planar convex polygon into small quads.  Returns (points (n,3), quads (m,4))."""
    poly = np.asarray(poly, float)
    m = len(poly)
    grids = []
    if m == 4:
        ku = max(1, int(np.ceil(max(np.linalg.norm(poly[1] - poly[0]), np.linalg.norm(poly[2] - poly[3])) / cell)))
        kv = max(1, int(np.ceil(max(np.linalg.norm(poly[3] - poly[0]), np.linalg.norm(poly[2] - poly[1])) / cell)))
        grids.append(_bilinear(poly, ku, kv))
    else:
        c = poly.mean(0)
        mid = [(poly[i] + poly[(i + 1) % m]) / 2 for i in range(m)]
        L = max(max(np.linalg.norm(poly[i] - mid[i]) for i in range(m)), max(np.linalg.norm(mid[i] - c) for i in range(m)))
        k = max(1, int(np.ceil(L / cell)))
        for i in range(m):
            grids.append(_bilinear(np.array([poly[i], mid[i], c, mid[i - 1]]), k, k))
    pts, quads, off = [], [], 0
    for G in grids:
        nu, nv = G.shape[0], G.shape[1]
        idx = (np.arange(nu * nv).reshape(nu, nv)) + off
        pts.append(G.reshape(-1, 3))
        q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
        quads.append(q)
        off += nu * nv
    P = np.concatenate(pts)
    Q = np.concatenate(quads)
    # weld
    key = np.round(P / 2e-6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    return P[first], inv[Q]


def edge_counts(co, cell, faces=None):
    """Subdivision count for every coarse edge such that neighbouring faces agree: opposite edges
    of a quad share one count; all edges of an n-gon share one even count (it is cut as a fan)."""
    V = co.arrays()
    faces = range(len(co.F)) if faces is None else faces
    parent = {}

    def find(e):
        parent.setdefault(e, e)
        while parent[e] != e:
            parent[e] = parent[parent[e]]
            e = parent[e]
        return e

    def union(a_, b_):
        ra, rb = find(a_), find(b_)
        if ra != rb:
            parent[ra] = rb

    ek = lambda i, j: (min(i, j), max(i, j))
    even = []
    for fi in faces:
        f = co.F[fi]
        m = len(f)
        es = [ek(f[k], f[(k + 1) % m]) for k in range(m)]
        for e in es:
            find(e)
        if m == 4:
            union(es[0], es[2])
            union(es[1], es[3])
        else:
            for e in es[1:]:
                union(es[0], e)
            even.append(es[0])
    length = {}
    for e in list(parent):
        r = find(e)
        length[r] = max(length.get(r, 0.0), float(np.linalg.norm(V[e[0]] - V[e[1]])))
    evenroots = {find(e) for e in even}
    counts = {}
    for e in list(parent):
        r = find(e)
        k = max(1, int(np.ceil(length[r] / cell - 1e-9)))
        if r in evenroots and k % 2:
            k += 1
        counts[e] = k
    return counts


def refine_face_counts(f, V, counts):
    """Cut one coarse face using the shared edge counts.  Returns (points (n,3), quads (m,4))."""
    poly = V[f]
    m = len(f)
    ek = lambda i, j: (min(i, j), max(i, j))
    grids = []
    if m == 4:
        ku = counts[ek(f[0], f[1])]
        kv = counts[ek(f[1], f[2])]
        grids.append(_bilinear(poly, ku, kv))
    else:
        k = max(1, counts[ek(f[0], f[1])] // 2)
        c = poly.mean(0)
        mid = [(poly[i] + poly[(i + 1) % m]) / 2 for i in range(m)]
        for i in range(m):
            grids.append(_bilinear(np.array([poly[i], mid[i], c, mid[i - 1]]), k, k))
    pts, quads, off = [], [], 0
    for G in grids:
        nu, nv = G.shape[0], G.shape[1]
        idx = (np.arange(nu * nv).reshape(nu, nv)) + off
        pts.append(G.reshape(-1, 3))
        quads.append(np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4))
        off += nu * nv
    P = np.concatenate(pts)
    Q = np.concatenate(quads)
    key = np.round(P / 2e-6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return P[first], inv.reshape(-1)[Q]


# ----------------------------------------------------------------------------- wounds


class Wounds:
    """Zones where the plating is torn away.  Each zone is a flattened ellipsoid on the surface."""

    def __init__(self, seed=0):
        self.z = []
        self.seed = seed

    def add(self, c, axis, L, W, normal=None, depth=None, strength=1.0, lobes=3):
        z = dict(c=np.asarray(c, float), a=unit(axis), L=float(L), W=float(W),
                 n=None if normal is None else unit(normal), depth=depth, s=strength)
        # a torn hole is never an ellipse: add off-centre lobes along and across it
        rng = np.random.default_rng(int(abs(z["c"]).sum() * 1e5) % (2 ** 31) + self.seed)
        z["lobes"] = []
        if z["n"] is not None:
            side = np.cross(z["n"], z["a"])
            for k in range(lobes):
                u = rng.uniform(0.35, 0.85) * L * (1 if k % 2 == 0 else -1)
                v = rng.uniform(-0.55, 0.55) * W
                z["lobes"].append((z["c"] + z["a"] * u + side * v, L * rng.uniform(0.35, 0.6), W * rng.uniform(0.55, 0.9)))
        self.z.append(z)
        return self

    @staticmethod
    def _q(p, c, a, L, W):
        d = p - c
        u = d @ a
        r = d - np.outer(u, a)
        return np.sqrt((u / L) ** 2 + (np.linalg.norm(r, axis=1) / W) ** 2)

    def value(self, p, nrm=None):
        """Exposure in [0, 1]: > ~0.5 means inside a wound.  Edges are broken up by noise."""
        p = np.asarray(p, float)
        out = np.zeros(len(p))
        if not self.z:
            return out
        nz = fbm(p, 7.0, 3, self.seed + 5) - 0.5
        nb = cnoise(p, 30.0, self.seed + 9) - 0.5
        for z in self.z:
            q = self._q(p, z["c"], z["a"], z["L"], z["W"])
            for (c2, L2, W2) in z.get("lobes", ()):
                q = np.minimum(q, self._q(p, c2, z["a"], L2, W2))
            val = 1.0 - q + 0.95 * nz + 0.24 * nb
            if z["n"] is not None and nrm is not None:
                val = np.where(nrm @ z["n"] > 0.15, val, -1.0)
            out = np.maximum(out, np.clip(0.5 + val * 2.2, 0, 1) * z["s"])
        return out

    def raw(self, p):
        """Un-noised signed depth factor in [0,1] (1 at the centre) for the cavity floor."""
        p = np.asarray(p, float)
        out = np.zeros(len(p))
        for z in self.z:
            q = self._q(p, z["c"], z["a"], z["L"], z["W"])
            for (c2, L2, W2) in z.get("lobes", ()):
                q = np.minimum(q, self._q(p, c2, z["a"], L2, W2))
            out = np.maximum(out, np.clip(1.25 - q, 0, 1))
        return out


# ----------------------------------------------------------------------------- the plate shell


class MeshOut:
    """Accumulates vertices / quads / tris with attributes for one output object."""

    def __init__(self):
        self.V, self.Q, self.T = [], [], []
        self.vattr = {}
        self.qattr = {}
        self.tattr = {}
        self.nv = 0

    def add(self, V, Q=None, T=None, vattr=None, qattr=None, tattr=None):
        V = np.asarray(V, float).reshape(-1, 3)
        n = len(V)
        self.V.append(V)
        for k, a in (vattr or {}).items():
            self.vattr.setdefault(k, []).append(np.broadcast_to(np.asarray(a, float), (n,)).copy())
        if Q is not None and len(Q):
            Q = np.asarray(Q, np.int64).reshape(-1, 4)
            self.Q.append(Q + self.nv)
            for k, a in (qattr or {}).items():
                self.qattr.setdefault(k, []).append(np.broadcast_to(np.asarray(a, float), (len(Q),)).copy())
        if T is not None and len(T):
            T = np.asarray(T, np.int64).reshape(-1, 3)
            self.T.append(T + self.nv)
            for k, a in (tattr or {}).items():
                self.tattr.setdefault(k, []).append(np.broadcast_to(np.asarray(a, float), (len(T),)).copy())
        self.nv += n

    def finish(self):
        V = np.concatenate(self.V) if self.V else np.zeros((0, 3))
        Q = np.concatenate(self.Q) if self.Q else np.zeros((0, 4), np.int64)
        T = np.concatenate(self.T) if self.T else np.zeros((0, 3), np.int64)
        va = {k: np.concatenate(a) for k, a in self.vattr.items()}
        names = set(self.qattr) | set(self.tattr)
        fa = {}
        for k in names:
            q = np.concatenate(self.qattr[k]) if k in self.qattr else np.zeros(len(Q))
            t = np.concatenate(self.tattr[k]) if k in self.tattr else np.zeros(len(T))
            if len(q) != len(Q):
                q = np.zeros(len(Q))
            if len(t) != len(T):
                t = np.zeros(len(T))
            fa[k] = np.concatenate([q, t])
        return dict(V=V, Q=Q, T=T, vattr=va, fattr=fa)


DEFAULT_SHELL = dict(
    cell=0.016,            # size of the small cells the plates are cut from (m)
    plate=(0.15, 0.12),    # slab size along / across the grain (m)
    layers=((0.004, 0.010, 1.00, 0.00), (0.015, 0.024, 0.64, 0.06), (0.028, 0.040, 0.28, 0.12), (0.042, 0.056, 0.09, 0.16)),
    #        (h_min, h_max, coverage, extra wound margin)
    tilt=0.035,            # random tilt of a plate (m per m)
    pit=0.020,             # fraction of cells knocked out as pits
    rag=0.20,              # waviness of slab outlines (fraction of the slab size)
    chip=0.30,             # stepped chipping of slab outlines (fraction of the slab size)
    under=0.004,           # under-surface below the coarse face (m)
    cavity=0.050,          # depth of the under-surface inside wounds (m)
    drop=0.35,             # chance that a plate is missing outside wounds (per layer >0)
)


def _poisson(C, r, rng):
    """Indices of points of C no closer than r to one another (dart throwing on a hash grid)."""
    keys = np.floor(C / r).astype(np.int64)
    grid = {}
    out = []
    r2 = r * r
    for i in rng.permutation(len(C)):
        kx, ky, kz = keys[i]
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((kx + dx, ky + dy, kz + dz), ()):
                        d = C[j] - C[i]
                        if d @ d < r2:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault((kx, ky, kz), []).append(i)
            out.append(i)
    return np.array(out, np.int64)


def _shell_patch(co, V, FN, dv, de, faces, wounds, pr, seed, plates, under):
    """Plate shell over a curved patch: the faces are cut with shared edge counts and welded, so
    slabs wrap across the coarse edges and follow the surface."""
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    cell = pr["cell"]
    counts = edge_counts(co, cell, faces)
    Ps, Ds, Qs, Ns = [], [], [], []
    off = 0
    tol = 1e-5
    for fi in faces:
        f = co.F[fi]
        poly = V[f]
        n = FN[fi]
        P, Q = refine_face_counts(f, V, counts)
        D = np.tile(n, (len(P), 1))
        m = len(f)
        for k in range(m):
            a_, b_ = poly[k], poly[(k + 1) % m]
            ab = b_ - a_
            L2 = ab @ ab
            if L2 < 1e-14:
                continue
            t = ((P - a_) @ ab) / L2
            on = np.linalg.norm(P - (a_ + np.outer(np.clip(t, 0, 1), ab)), axis=1) < tol
            e = (min(f[k], f[(k + 1) % m]), max(f[k], f[(k + 1) % m]))
            if e in de:
                D[on] = de[e]
        for k in range(m):
            on = np.linalg.norm(P - poly[k], axis=1) < tol
            if f[k] in dv:
                D[on] = dv[f[k]]
        Ps.append(P)
        Ds.append(D)
        Qs.append(Q + off)
        Ns.append(np.tile(n, (len(Q), 1)))
        off += len(P)
    P = np.concatenate(Ps)
    D = np.concatenate(Ds)
    Q = np.concatenate(Qs)
    NC = np.concatenate(Ns)
    key = np.round(P / 2e-6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    P, D, Q = P[first], D[first], inv[Q]
    nP = len(P)
    C = P[Q].mean(1)
    ncell = len(Q)
    # vertex normals for the wound test: mean of the cells round each vertex
    VN = np.zeros((nP, 3))
    np.add.at(VN, Q.reshape(-1), np.repeat(NC, 4, axis=0))
    VN = unit(VN)
    wv = wounds.value(P, VN)
    wc = wv[Q].mean(1)
    raw = wounds.raw(P)
    sink = pr["under"] + pr["cavity"] * np.clip(wv * 1.3, 0, 1) * (0.55 + 0.45 * raw)
    under.add(P - D * sink[:, None], Q, vattr=dict(wound=np.clip(wv * 1.25, 0, 1), kind=0.0))
    pit = (cnoise(C, 1.0 / (cell * 1.9), seed + 31) < pr["pit"]) | (rng.random(ncell) < pr["pit"] * 0.35)
    rmean = float(np.mean(pr["plate"]))
    for li, (h0, h1, cover, margin) in enumerate(pr["layers"]):
        rr = rmean * (1.0 + 0.18 * li)
        si = _poisson(C, rr * 0.80, rng)
        S = C[si]
        ns = len(S)
        wob = np.stack([fbm(C, 13.0, 2, seed + 3 + li + 11 * a_) for a_ in range(3)], 1) - 0.5
        blk = np.stack([cnoise(C, 1.0 / (cell * 2.2), seed + 7 + li + 13 * a_) for a_ in range(3)], 1) - 0.5
        q = C + rr * (pr["rag"] * wob + pr["chip"] * blk * (0.45 + 0.9 * np.clip(wc * 2.5, 0, 1))[:, None])
        _, sid = cKDTree(S).query(q)
        ph = rng.uniform(h0, h1, ns)
        tone = rng.random(ns)
        alive = rng.random(ns) < cover
        gv = rng.normal(0, pr["tilt"] * (1 + 1.3 * li), (ns, 3))
        sw = wounds.value(S, NC[si])
        alive &= sw < (0.52 - margin * 6.0)
        keep = alive[sid] & (wc < (0.60 - margin * 7.0))
        if li == 0:
            keep &= ~pit
        else:
            keep &= ~(pit & (rng.random(ncell) < 0.5))
        if not keep.any():
            continue
        Qk = Q[keep]
        sk = sid[keep]
        pairs = sk[:, None].astype(np.int64) * nP + Qk
        upair, pinv = np.unique(pairs.reshape(-1), return_inverse=True)
        pinv = pinv.reshape(-1, 4)
        vp = upair % nP
        sp = upair // nP
        hv = ph[sp] + np.einsum("ij,ij->i", gv[sp], P[vp] - S[sp])
        hv = np.clip(hv, h0 * 0.55, h1 * 1.5)
        top = P[vp] + D[vp] * hv[:, None]
        a_ = Qk
        b_ = np.roll(Qk, -1, axis=1)
        ekey = sk[:, None].astype(np.int64) * (nP * nP) + a_.astype(np.int64) * nP + b_
        tkey = sk[:, None].astype(np.int64) * (nP * nP) + b_.astype(np.int64) * nP + a_
        flat = np.sort(ekey.reshape(-1))
        pos = np.clip(np.searchsorted(flat, tkey.reshape(-1)), 0, len(flat) - 1)
        bnd = ~(flat[pos] == tkey.reshape(-1)).reshape(-1, 4)
        wa = pinv[bnd]
        wb = np.roll(pinv, -1, axis=1)[bnd]
        ntop = len(top)
        need = np.unique(np.concatenate([wa, wb]))
        remap = -np.ones(ntop, np.int64)
        remap[need] = np.arange(len(need)) + ntop
        vb = vp[need]
        bot = P[vb] - D[vb] * (pr["under"] + 0.004 + pr["cavity"] * np.clip(wv[vb] * 1.3, 0, 1))[:, None]
        rim = np.zeros(ntop)
        rim[need] = 1.0
        walls = np.stack([wa, remap[wa], remap[wb], wb], 1)
        plates.add(np.concatenate([top, bot]), np.concatenate([pinv, walls]),
                   vattr=dict(rim=np.concatenate([rim, np.ones(len(bot))]), ht=np.concatenate([hv, np.zeros(len(bot))])),
                   qattr=dict(tone=np.concatenate([tone[sk], tone[sk[np.nonzero(bnd)[0]]]]),
                              wall=np.concatenate([np.zeros(len(pinv)), np.ones(len(walls))]),
                              layer=np.full(len(pinv) + len(walls), float(li))))


def build_shell(co, wounds=None, params=None, seed=0):
    """Turn a coarse mesh into (plates MeshOut, under MeshOut).

    plates face attrs: tone (per plate), wall (1 on side walls), layer; vertex attr: rim.
    under  vertex attrs: wound (0..1), kind code (0 core, 1 tissue, 2 gum, 3 socket, 4 void)."""
    from scipy.spatial import cKDTree
    pr = dict(DEFAULT_SHELL)
    pr.update(params or {})
    rng = np.random.default_rng(seed)
    wounds = wounds or Wounds(seed)
    V = co.arrays()
    dv, de, FN = offset_vectors(co)
    plates, under = MeshOut(), MeshOut()
    kcode = {"plate": 0, "core": 0, "tissue": 1, "gum": 2, "socket": 3, "void": 4}

    patches = {}
    for fi in range(len(co.F)):
        pid = co.patch[fi] if fi < len(co.patch) else None
        if pid is not None and co.kind[fi] == "plate":
            patches.setdefault(pid, []).append(fi)
    patched = {fi for fs in patches.values() for fi in fs}
    for pid in sorted(patches, key=str):
        _shell_patch(co, V, FN, dv, de, patches[pid], wounds, pr, seed + 1000 + (hash(str(pid)) % 9973), plates, under)

    for fi, f in enumerate(co.F):
        if fi in patched:
            continue
        poly = V[f]
        n = FN[fi]
        kind = co.kind[fi]
        cell = pr["cell"]
        P, Q = refine_face(poly, cell)
        nP = len(P)
        # offset vector of every fine vertex (mitre on coarse edges / corners)
        D = np.tile(n, (nP, 1))
        m = len(f)
        tol = 1e-5
        for k in range(m):
            a, b = poly[k], poly[(k + 1) % m]
            ab = b - a
            L2 = ab @ ab
            if L2 < 1e-14:
                continue
            t = ((P - a) @ ab) / L2
            dist = np.linalg.norm(P - (a + np.outer(np.clip(t, 0, 1), ab)), axis=1)
            on = dist < tol
            e = (min(f[k], f[(k + 1) % m]), max(f[k], f[(k + 1) % m]))
            if e in de:
                D[on] = de[e]
        for k in range(m):
            on = np.linalg.norm(P - poly[k], axis=1) < tol
            if f[k] in dv:
                D[on] = dv[f[k]]
        if kind != "plate":
            D = np.tile(n, (nP, 1))

        C = P[Q].mean(1)                                   # cell centres
        wv = wounds.value(P, np.tile(n, (nP, 1))) if kind == "plate" else np.zeros(nP)
        wc = wv[Q].mean(1)

        # ---- under-surface (always present; sunk and red inside wounds)
        if kind == "plate":
            raw = wounds.raw(P)
            sink = pr["under"] + pr["cavity"] * np.clip(wv * 1.3, 0, 1) * (0.55 + 0.45 * raw)
            Pu = P - D * sink[:, None]
            under.add(Pu, Q, vattr=dict(wound=np.clip(wv * 1.25, 0, 1), kind=0.0))
        else:
            under.add(P, Q, vattr=dict(wound=0.0, kind=float(kcode.get(kind, 0))))
            continue

        # ---- plates
        g = co.grain[fi]
        if g is None:
            g = poly[1] - poly[0]
        e1 = unit(g - (g @ n) * n)
        e2 = np.cross(n, e1)
        uv = np.stack([(C - poly[0]) @ e1, (C - poly[0]) @ e2], 1)
        puv = np.stack([(P - poly[0]) @ e1, (P - poly[0]) @ e2], 1)
        lo, hi = puv.min(0) - 0.05, puv.max(0) + 0.05
        r1, r2 = pr["plate"]
        ncell = len(Q)
        # cell-level knock-outs: pits, and chips that step the wound edge
        pit = (cnoise(C, 1.0 / (cell * 1.9), seed + 31) < pr["pit"]) | (rng.random(ncell) < pr["pit"] * 0.35)
        for li, (h0, h1, cover, margin) in enumerate(pr["layers"]):
            # seeds on a jittered lattice (different lattice per layer -> overlapping outlines)
            s1 = r1 * (1.0 + 0.18 * li)
            s2 = r2 * (1.0 + 0.18 * li)
            ox, oy = rng.random(2)
            gx = np.arange(lo[0] - s1, hi[0] + s1, s1) + ox * s1
            gy = np.arange(lo[1] - s2, hi[1] + s2, s2) + oy * s2
            S = np.stack(np.meshgrid(gx, gy, indexing="ij"), -1).reshape(-1, 2)
            S = S + rng.normal(0, 0.27, S.shape) * np.array([s1, s2])
            ns = len(S)
            # noisy nearest seed (anisotropic)
            sc = np.array([1.0 / s1, 1.0 / s2])
            tree = cKDTree(S * sc)
            wob = np.stack([fbm(C, 13.0, 2, seed + 3 + li), fbm(C, 13.0, 2, seed + 4 + li)], 1) - 0.5
            blk = np.stack([cnoise(C, 1.0 / (cell * 2.2), seed + 7 + li), cnoise(C, 1.0 / (cell * 2.2), seed + 8 + li)], 1) - 0.5
            q = uv * sc + pr["rag"] * wob + pr["chip"] * blk * (0.45 + 0.9 * np.clip(wc * 2.5, 0, 1))[:, None]
            _, sid = tree.query(q)
            # plate properties
            ph = rng.uniform(h0, h1, ns)
            tone = rng.random(ns)
            alive = rng.random(ns) < cover
            if li > 0:
                alive &= rng.random(ns) > pr["drop"] * 0.0
            tx = rng.normal(0, pr["tilt"] * (1 + 1.3 * li), ns)     # higher strata lift more at one edge
            ty = rng.normal(0, pr["tilt"] * (1 + 1.3 * li), ns)
            # seeds inside wounds lose their plate entirely
            sw = wounds.value(np.asarray(poly[0]) + np.outer(S[:, 0], e1) + np.outer(S[:, 1], e2), np.tile(n, (ns, 1)))
            alive &= sw < (0.52 - margin * 6.0)
            keep = alive[sid] & (wc < (0.60 - margin * 7.0))
            if li == 0:
                keep &= ~pit
            else:
                keep &= ~(pit & (rng.random(ncell) < 0.5))
            if not keep.any():
                continue
            Qk = Q[keep]
            sk = sid[keep]
            # unique (plate, vertex) pairs
            pairs = sk[:, None].astype(np.int64) * nP + Qk
            upair, inv = np.unique(pairs.reshape(-1), return_inverse=True)
            inv = inv.reshape(-1, 4)
            vp = upair % nP
            sp = upair // nP
            hv = ph[sp] + tx[sp] * (puv[vp, 0] - S[sp, 0]) + ty[sp] * (puv[vp, 1] - S[sp, 1])
            hv = np.clip(hv, h0 * 0.55, h1 * 1.5)
            top = P[vp] + D[vp] * hv[:, None]
            # boundary edges -> walls
            a = Qk
            b = np.roll(Qk, -1, axis=1)
            ekey = sk[:, None].astype(np.int64) * (nP * nP) + a.astype(np.int64) * nP + b
            tkey = sk[:, None].astype(np.int64) * (nP * nP) + b.astype(np.int64) * nP + a
            flat = np.sort(ekey.reshape(-1))
            pos = np.searchsorted(flat, tkey.reshape(-1))
            pos = np.clip(pos, 0, len(flat) - 1)
            has_twin = (flat[pos] == tkey.reshape(-1)).reshape(-1, 4)
            bnd = ~has_twin
            ia = inv
            ib = np.roll(inv, -1, axis=1)
            wa = ia[bnd]
            wb = ib[bnd]
            ntop = len(top)
            # wall bottoms go down below the under-surface
            need = np.unique(np.concatenate([wa, wb]))
            remap = -np.ones(ntop, np.int64)
            remap[need] = np.arange(len(need)) + ntop
            vb = vp[need]
            bot = P[vb] - D[vb] * (pr["under"] + 0.004 + pr["cavity"] * np.clip(wv[vb] * 1.3, 0, 1))[:, None]
            rim = np.zeros(ntop)
            rim[need] = 1.0
            Vall = np.concatenate([top, bot])
            walls = np.stack([wa, remap[wa], remap[wb], wb], 1)
            tq = tone[sk]
            tw = tone[sk[np.nonzero(bnd)[0]]]
            plates.add(Vall, np.concatenate([inv, walls]),
                       vattr=dict(rim=np.concatenate([rim, np.ones(len(bot))]),
                                  ht=np.concatenate([hv, np.zeros(len(bot))])),
                       qattr=dict(tone=np.concatenate([tq, tw]),
                                  wall=np.concatenate([np.zeros(len(inv)), np.ones(len(walls))]),
                                  layer=np.full(len(inv) + len(walls), float(li))))
    return plates.finish(), under.finish()


# ----------------------------------------------------------------------------- simple solids


def spindle(c, axis, length, w, t, normal, segs=8, rings=7, rng=None, tag=0.0):
    """A muscle bundle: stretched, slightly irregular ellipsoid.  Returns (V, Q, T)."""
    a = unit(axis)
    nrm = unit(np.asarray(normal, float) - (np.asarray(normal, float) @ a) * a)
    s = np.cross(nrm, a)
    V, Q, T = [], [], []
    us = np.linspace(-1, 1, rings + 2)[1:-1]
    V.append(np.asarray(c) - a * length / 2)
    for u in us:
        rr = np.sqrt(max(1 - u * u, 0)) ** 0.8
        kw = 1.0 + (rng.normal(0, 0.08) if rng is not None else 0)
        for j in range(segs):
            th = 2 * np.pi * j / segs
            V.append(np.asarray(c) + a * u * length / 2 + (s * np.cos(th) * w * kw + nrm * np.sin(th) * t * kw) * rr)
    V.append(np.asarray(c) + a * length / 2)
    last = len(V) - 1
    for j in range(segs):
        T.append([0, 1 + (j + 1) % segs, 1 + j])
    for i in range(rings - 1):
        for j in range(segs):
            p = 1 + i * segs
            Q.append([p + j, p + (j + 1) % segs, p + segs + (j + 1) % segs, p + segs + j])
    p = 1 + (rings - 1) * segs
    for j in range(segs):
        T.append([p + j, p + (j + 1) % segs, last])
    return np.array(V), np.array(Q, np.int64).reshape(-1, 4), np.array(T, np.int64).reshape(-1, 3)


def tube(P, R, sides=7, rng=None, wob=0.0, xhint=(0.0, 0.0, 1.0), caps=True, flat=1.0):
    """Lumpy tube through points P with radii R.  Returns (V, Q, T)."""
    P = np.asarray(P, float)
    R = np.broadcast_to(np.asarray(R, float), (len(P),))
    hint = np.asarray(xhint, float)
    T_, EX, EY = path_frames(P, hint if abs(unit(P[-1] - P[0]) @ unit(hint)) < 0.95 else np.array([1.0, 0.0, 0.0]))
    V, Q, T = [], [], []
    for i in range(len(P)):
        for j in range(sides):
            th = 2 * np.pi * j / sides
            r = R[i] * (1 + (rng.normal(0, wob) if (rng is not None and wob) else 0))
            V.append(P[i] + EX[i] * np.cos(th) * r + EY[i] * np.sin(th) * r * flat)
    for i in range(len(P) - 1):
        for j in range(sides):
            a = i * sides
            Q.append([a + j, a + (j + 1) % sides, a + sides + (j + 1) % sides, a + sides + j])
    if caps:
        V.append(P[0])
        V.append(P[-1])
        c0, c1 = len(V) - 2, len(V) - 1
        a = (len(P) - 1) * sides
        for j in range(sides):
            T.append([c0, (j + 1) % sides, j])
            T.append([a + j, a + (j + 1) % sides, c1])
    return np.array(V), np.array(Q, np.int64).reshape(-1, 4), np.array(T, np.int64).reshape(-1, 3)


def spline(pts, n):
    """Catmull-Rom curve through pts, resampled to n points."""
    P = np.asarray(pts, float)
    P = np.concatenate([[2 * P[0] - P[1]], P, [2 * P[-1] - P[-2]]])
    m = len(P) - 3
    out = []
    for t in np.linspace(0, m, n):
        i = min(int(t), m - 1)
        f = t - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3))
    return np.array(out)


def rod(base, direction, length, radius, rng, sides=6, sink=0.08):
    """A rusted bar driven into the body: irregular prism with a blunt chamfered end."""
    d = unit(direction)
    hint = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    ex = unit(hint - (hint @ d) * d)
    ey = np.cross(d, ex)
    ts = [-sink, 0.0, length * rng.uniform(0.35, 0.6), length - radius * 0.35, length]
    rs = [1.0, 1.0, rng.uniform(0.92, 1.05), rng.uniform(0.9, 1.0), 0.72]
    ph = rng.uniform(0, 2 * np.pi)
    fl = rng.uniform(0.72, 1.0)
    V, Q, T = [], [], []
    for t, r in zip(ts, rs):
        for j in range(sides):
            th = ph + 2 * np.pi * j / sides
            V.append(np.asarray(base) + d * t + (ex * np.cos(th) + ey * np.sin(th) * fl) * radius * r * (1 + rng.normal(0, 0.04)))
    for i in range(len(ts) - 1):
        for j in range(sides):
            a = i * sides
            Q.append([a + j, a + (j + 1) % sides, a + sides + (j + 1) % sides, a + sides + j])
    V.append(np.asarray(base) + d * (length + radius * 0.02))
    c = len(V) - 1
    a = (len(ts) - 1) * sides
    for j in range(sides):
        T.append([a + j, a + (j + 1) % sides, c])
    return np.array(V), np.array(Q, np.int64).reshape(-1, 4), np.array(T, np.int64).reshape(-1, 3)


def tooth(root, direction, length, radius, rng, bend_dir=None, bend=0.0, sides=6, sink=0.03, flat=0.8,
          twist=0.3):
    """One fang: an irregular, chiselled, slightly curved spike.  Returns (V, Q, T, attrs) with
    attrs t (0 at the gum, 1 at the tip) and ca / sa (cos / sin of the angle round the tooth)."""
    d = unit(direction)
    hint = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    ex = unit(hint - (hint @ d) * d)
    ey = np.cross(d, ex)
    if bend_dir is None:
        bend_dir = ex
    bd = unit(np.asarray(bend_dir, float) - (np.asarray(bend_dir, float) @ d) * d)
    ph = rng.uniform(0, 2 * np.pi)
    ex, ey = ex * np.cos(ph) + ey * np.sin(ph), -ex * np.sin(ph) + ey * np.cos(ph)
    ts = np.array([-sink / length, 0.0, 0.10, 0.24, 0.40, 0.56, 0.71, 0.84, 0.94])
    prof = np.array([0.90, 1.0, 0.99, 0.93, 0.82, 0.67, 0.50, 0.32, 0.15])
    prof = prof * (1 + rng.normal(0, 0.05, len(prof)))
    fac = 1 + rng.normal(0, 0.15, sides)          # unequal faces: a carved, not turned, section
    ang0 = 2 * np.pi * (np.arange(sides) + rng.normal(0, 0.10, sides)) / sides
    V, Q, T, tt, ca, sa = [], [], [], [], [], []
    for k, (t, pr_) in enumerate(zip(ts, prof)):
        c = np.asarray(root) + d * (t * length) + bd * (bend * length * max(t, 0) ** 2)
        if 0 < k < len(ts) - 1:
            c = c + (ex * rng.normal() + ey * rng.normal()) * radius * 0.045   # slight kinks
        tw = twist * t
        for j in range(sides):
            th = ang0[j] + tw
            r = radius * pr_ * fac[j] * (1 + rng.normal(0, 0.05))
            V.append(c + ex * np.cos(th) * r + ey * np.sin(th) * r * flat)
            tt.append(max(t, 0.0)); ca.append(np.cos(ang0[j])); sa.append(np.sin(ang0[j]))
    for i in range(len(ts) - 1):
        for j in range(sides):
            a_ = i * sides
            Q.append([a_ + j, a_ + (j + 1) % sides, a_ + sides + (j + 1) % sides, a_ + sides + j])
    tip = np.asarray(root) + d * length + bd * (bend * length)
    V.append(tip); tt.append(1.0); ca.append(0.0); sa.append(0.0)
    c = len(V) - 1
    a_ = (len(ts) - 1) * sides
    for j in range(sides):
        T.append([a_ + j, a_ + (j + 1) % sides, c])
    V.append(np.asarray(root) - d * sink); tt.append(0.0); ca.append(0.0); sa.append(0.0)
    c0 = len(V) - 1
    for j in range(sides):
        T.append([c0, (j + 1) % sides, j])
    return (np.array(V), np.array(Q, np.int64).reshape(-1, 4), np.array(T, np.int64).reshape(-1, 3),
            dict(t=np.array(tt), ca=np.array(ca), sa=np.array(sa)))


def strands_for_wound(z, rng, surf_normal, spacing=0.034, depth=0.030):
    """Muscle laid bare in a wound: long cords running along it, each swelling and thinning,
    weaving slightly over one another.  Returns list of (V, Q, T)."""
    a = z["a"]
    n = unit(np.asarray(surf_normal, float) - (np.asarray(surf_normal, float) @ a) * a)
    s = np.cross(n, a)
    out = []
    L, W = z["L"], z["W"]
    L2 = L * 1.25
    nrow = max(2, int(round(2 * W * 0.95 / spacing)))
    for r in range(nrow):
        v0 = (-W * 0.95 + (r + 0.5) * (2 * W * 0.95 / nrow))
        span = L2 * np.sqrt(max(1 - (v0 / (W * 1.15)) ** 2, 0.08))
        # one to three cords end to end in this row
        u = -span
        while u < span - 0.04:
            ln = min(rng.uniform(0.55, 1.5) * max(L * 0.8, 0.09), span - u)
            if ln < 0.05:
                break
            k = max(6, int(ln / 0.018))
            ts = np.linspace(0, 1, k)
            ph, fq = rng.uniform(0, 6.28), rng.uniform(1.2, 2.6)
            r0 = spacing * rng.uniform(0.38, 0.70)
            sw = rng.uniform(0.25, 0.5)
            P, R = [], []
            for t in ts:
                uu = u + t * ln
                vv = v0 + spacing * 0.42 * np.sin(ph + t * fq * 2.0)
                edge = max(abs(uu) / L2, abs(vv) / (W * 1.15))
                dd = depth - 0.012 * min(edge, 1.0) ** 2 + 0.005 * np.sin(ph * 1.7 + t * 5.0)
                P.append(z["c"] + a * uu + s * vv - n * dd)
                bulge = (1 - sw) + sw * abs(np.sin(ph + t * np.pi * fq)) ** 0.7
                taper = min(1.0, t / 0.12, (1 - t) / 0.12) ** 0.6 * 0.85 + 0.15
                R.append(r0 * bulge * taper)
            out.append(tube(np.array(P), np.array(R), sides=7, rng=rng, wob=0.05, xhint=n, flat=0.82))
            u += ln * rng.uniform(0.9, 1.0)
    return out
