"""
Signed-distance block modelling for the v10 head: the approved sheet's skull and jaw are built of
flat planes and blocky chunks (stepped, notched outlines, missing and proud blocks, square holes),
which a lofted, displaced surface cannot reproduce. Shapes are written as signed-distance fields on
a voxel grid (negative inside), combined with min/max (union, intersection, subtraction), given a
mosaic of rectangular tiles that step in and out per face, and turned into a mesh by marching cubes
(scikit-image).

All lengths are in the caller's units (head units for head_v10.py).
"""
import math

import bpy
import numpy as np
from skimage.measure import marching_cubes


class Grid:
    """Regular voxel grid over the box lo..hi with spacing h; X, Y, Z are float32 arrays."""

    def __init__(self, lo, hi, h):
        self.lo, self.h = np.asarray(lo, float), float(h)
        self.shape = tuple(int(math.ceil((b - a) / h)) + 1 for a, b in zip(lo, hi))
        ax = [(self.lo[i] + h * np.arange(self.shape[i])).astype(np.float32) for i in range(3)]
        self.X, self.Y, self.Z = np.meshgrid(*ax, indexing="ij")

    def gradient(self, F):
        g = np.gradient(F, self.h)
        n = np.sqrt(g[0] ** 2 + g[1] ** 2 + g[2] ** 2) + 1e-9
        return g[0] / n, g[1] / n, g[2] / n


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rot(rx=0.0, ry=0.0, rz=0.0):
    """Rotation matrix from Euler angles in degrees (X, then Y, then Z)."""
    a, b, c = (math.radians(t) for t in (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def plane(G, normal, point):
    """Half-space n.(p - point) <= 0 (signed distance, outside positive)."""
    n = _unit(normal)
    return (G.X * n[0] + G.Y * n[1] + G.Z * n[2] - float(np.dot(n, point))).astype(np.float32)


def box(G, center, half, R=None):
    """Box with half-extents `half`, rotated by R (local -> world), centred at `center`."""
    c = np.asarray(center, float)
    x, y, z = G.X - c[0], G.Y - c[1], G.Z - c[2]
    if R is not None:
        Rt = np.asarray(R).T
        x, y, z = (Rt[0, 0] * x + Rt[0, 1] * y + Rt[0, 2] * z, Rt[1, 0] * x + Rt[1, 1] * y + Rt[1, 2] * z,
                   Rt[2, 0] * x + Rt[2, 1] * y + Rt[2, 2] * z)
    qx, qy, qz = np.abs(x) - half[0], np.abs(y) - half[1], np.abs(z) - half[2]
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return (out + np.minimum(np.maximum(np.maximum(qx, qy), qz), 0)).astype(np.float32)


def ellipsoid(G, center, radii, R=None):
    """Approximate ellipsoid distance (exact on the axes; fine for carving)."""
    c = np.asarray(center, float)
    x, y, z = G.X - c[0], G.Y - c[1], G.Z - c[2]
    if R is not None:
        Rt = np.asarray(R).T
        x, y, z = (Rt[0, 0] * x + Rt[0, 1] * y + Rt[0, 2] * z, Rt[1, 0] * x + Rt[1, 1] * y + Rt[1, 2] * z,
                   Rt[2, 0] * x + Rt[2, 1] * y + Rt[2, 2] * z)
    k = np.sqrt((x / radii[0]) ** 2 + (y / radii[1]) ** 2 + (z / radii[2]) ** 2)
    return ((k - 1.0) * min(radii)).astype(np.float32)


def union(*fs):
    out = fs[0]
    for f in fs[1:]:
        out = np.minimum(out, f)
    return out


def inter(*fs):
    out = fs[0]
    for f in fs[1:]:
        out = np.maximum(out, f)
    return out


def sub(a, *bs):
    out = a
    for b in bs:
        out = np.maximum(out, -b)
    return out


def hrand(key, k=0):
    """Deterministic pseudo-random value in [0, 1) per integer key (splitmix64 hash)."""
    with np.errstate(over="ignore"):
        x = np.asarray(key).astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15) * np.uint64(k + 1)
        x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        x = x ^ (x >> np.uint64(31))
    return ((x >> np.uint64(11)).astype(np.float64) / float(1 << 53)).astype(np.float32)


def _cuts(lo, hi, size, rng, jit=0.35):
    """Random partition of [lo, hi] into cells of about `size` (uneven widths)."""
    c = [lo - rng.uniform(0, size)]
    while c[-1] < hi + size:
        c.append(c[-1] + size * rng.uniform(1 - jit, 1 + jit))
    return np.asarray(c)


def tiles(G, F, size=0.10, seed=0, shell=0.07, raised=(0.0, 0.030), sunken=(-0.020, 0.0), p_sunk=0.30,
          p_missing=0.08, missing=-0.055, tilt=0.10, seam=0.006, seam_depth=0.012, wobble=0.012, mask=None,
          spread=0.55):
    """Blocky plate mosaic over the surface of F. Every face (by its dominant axis and side) is split
    into irregular, mostly rectilinear plates - Voronoi cells under the Chebyshev metric around
    unevenly scattered seeds (plates of very different sizes, edges at 0/45/90 degrees, the whole
    pattern turned a little per face). Each plate steps out or in by its own amount (some missing,
    leaving a square-ish hole), tilts a little and is parted from its neighbours by a seam.
    Returns (F', plate id per voxel, plate value 0..1, seam 0..1, hole 0..1)."""
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    nx, ny, nz = G.gradient(F)
    N = np.stack([nx, ny, nz])
    ax = np.argmax(np.abs(N), axis=0)                                  # dominant axis per voxel
    sgn = np.take_along_axis(N, ax[None], 0)[0] > 0
    coords = (G.X, G.Y, G.Z)
    tid = np.zeros(F.shape, np.int64)
    off = np.zeros(F.shape, np.float32)
    val = np.zeros(F.shape, np.float32)
    seamd = np.full(F.shape, 9.0, np.float32)
    hole = np.zeros(F.shape, np.float32)
    lo, hi = G.lo, G.lo + G.h * (np.asarray(G.shape) - 1)
    for a in range(3):
        u_ax, v_ax = [i for i in range(3) if i != a]
        for side in (False, True):
            m = (ax == a) & (sgn == side) & (np.abs(F) < shell)
            if mask is not None:
                m &= mask
            if not m.any():
                continue
            ang = rng.uniform(-0.16, 0.16)                             # the pattern turned per face
            ca, sa = math.cos(ang), math.sin(ang)
            u0, v0 = coords[u_ax][m], coords[v_ax][m]
            wu = wobble * np.sin(v0 * 9.1 + 1.3 * a) * np.cos(u0 * 4.3 + side)
            wv = wobble * np.sin(u0 * 8.3 + 0.7 * a) * np.cos(v0 * 5.1 - side)
            u, v = ca * u0 - sa * v0 + wu, sa * u0 + ca * v0 + wv
            # seeds: uneven density - big plates in places, clusters of small chips in others
            area = (hi[u_ax] - lo[u_ax] + 0.4) * (hi[v_ax] - lo[v_ax] + 0.4)
            n = int(area / size ** 2 * 1.25)
            pts = np.c_[rng.uniform(lo[u_ax] - 0.2, hi[u_ax] + 0.2, n), rng.uniform(lo[v_ax] - 0.2, hi[v_ax] + 0.2, n)]
            dens = np.sin(pts[:, 0] * 5.3 + rng.uniform(0, 6)) * np.cos(pts[:, 1] * 4.7 + rng.uniform(0, 6))
            keep_p = rng.random(n) < np.clip(0.55 + spread * dens, 0.15, 1.0)
            pts = pts[keep_p]
            tree = cKDTree(pts)
            d, i = tree.query(np.c_[u, v], k=2, p=np.inf)
            gap = d[:, 1] - d[:, 0]
            key = i[:, 0].astype(np.int64) + (a * 2 + side) * 1000003 + seed * 7919
            r = np.stack([hrand(key, k) for k in range(4)], 1)
            o = np.where(r[:, 0] < p_sunk, sunken[0] + (sunken[1] - sunken[0]) * r[:, 1],
                         raised[0] + (raised[1] - raised[0]) * r[:, 1])
            miss = r[:, 2] < p_missing
            o = np.where(miss, missing * (0.7 + 0.6 * r[:, 3]), o)
            cu, cv = pts[i[:, 0], 0], pts[i[:, 0], 1]
            o = o + tilt * ((r[:, 3] - 0.5) * (u - cu) + (r[:, 1] - 0.5) * (v - cv))   # plate tilt
            off[m] = o
            val[m] = r[:, 1]
            tid[m] = key
            seamd[m] = gap
            hole[m] = miss
    w = np.clip(1.0 - np.abs(F) / shell, 0, 1).astype(np.float32)
    s = np.clip(1.0 - seamd / seam, 0, 1).astype(np.float32)
    Fo = F - off * w + seam_depth * s * w
    return Fo.astype(np.float32), tid, val, s, hole


def to_object(name, F, G, col, mats=(), smooth=0):
    """Marching cubes on F (level 0) -> mesh object; vertices in grid units (no object scale)."""
    verts, faces, _, _ = marching_cubes(F, level=0.0, spacing=(G.h, G.h, G.h), gradient_direction="descent",
                                        allow_degenerate=False)
    verts = verts + G.lo
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    nl = len(faces)
    me.loops.add(nl * 3)
    me.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    me.polygons.add(nl)
    me.polygons.foreach_set("loop_start", (np.arange(nl) * 3).astype(np.int32))
    me.update(calc_edges=True)
    me.validate()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    return ob


def sample(G, field, pts):
    """Nearest-voxel lookup of a grid field at points (N, 3) in grid units."""
    idx = np.rint((np.asarray(pts) - G.lo) / G.h).astype(int)
    for i in range(3):
        idx[:, i] = np.clip(idx[:, i], 0, G.shape[i] - 1)
    return field[idx[:, 0], idx[:, 1], idx[:, 2]]
