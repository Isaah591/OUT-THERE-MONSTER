"""
Continuous corroded surface for the v5 variation (see sculpt.py for the Surf helpers).

Instead of distinct armour-like plates, the shell gets damage that is part of the material:
a fine network of thin, shallow cracks (no lifted or tilted plates), irregular clustered rust
pits, and low-frequency erosion. All displacements are inward and small, so the low-poly
facets of the form stay readable.
"""
import numpy as np
from scipy.spatial import cKDTree

import sculpt as SC


def crack_network(S, cell=0.07, width=0.0018, depth=0.0025, seed=0, w=None, tilt=0.0):
    """Thin, embedded cracks along jagged Voronoi borders. The plates stay flush (no lift); an
    optional small `tilt` turns each plate a little so neighbouring plates catch the light
    differently (an integrated mosaic, not stacked armour)."""
    return SC.flakes(S, cell=cell, crack=width, depth=depth, lift=0.0, tilt=tilt, seed=seed, w=w)


def pits(S, per_m2, size=(0.010, 0.024), depth=(0.004, 0.010), seed=0, w=None):
    """Scattered rust pits (small dark holes in the shell), written to `pit`: irregular blobs
    (random superellipse exponent, wobbly rim, random aspect and rotation), clustered by a
    low-frequency field so corrosion gathers in places instead of an even polka-dot spread."""
    r = np.random.default_rng(seed)
    nrm = S.normals()
    area = S.n * S.h * S.h * 0.9                     # surface area estimate from the mean edge length
    count = int(per_m2 * area)
    pool = np.arange(S.n) if w is None else np.flatnonzero(w > 0.5)
    if count <= 0 or len(pool) == 0:
        return
    field = np.clip(SC._z(SC.fbm(SC.Perlin(seed + 101), S.co * 4.0, 2)) + 0.3, 0, None) ** 2 + 0.08
    p = field[pool] / field[pool].sum()
    centres = r.choice(pool, size=min(count, len(pool)), replace=False, p=p)
    hole = np.zeros(S.n)
    tree = cKDTree(S.co)
    for i in centres:
        c, n = S.co[i], nrm[i]
        sz = r.uniform(*size)
        idx = tree.query_ball_point(c, sz * 1.9)
        if not idx:
            continue
        idx = np.asarray(idx)
        t = SC.unit(np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]))
        b = np.cross(n, t)
        a = r.uniform(0, np.pi)
        t, b = t * np.cos(a) + b * np.sin(a), -t * np.sin(a) + b * np.cos(a)
        rel = S.co[idx] - c
        u, v = rel @ t / (sz * r.uniform(0.6, 1.0)), rel @ b / (sz * r.uniform(0.45, 1.0))
        e = r.uniform(1.3, 3.0)
        q = (np.abs(u) ** e + np.abs(v) ** e) ** (1.0 / e)
        ang = np.arctan2(v, u)
        q = q * (1.0 + 0.22 * np.sin(r.integers(3, 6) * ang + r.uniform(0, 6.3)) + 0.10 * np.sin(7 * ang + r.uniform(0, 6.3)))
        inside = np.clip((1.0 - q) / 0.3, 0, 1)
        d = r.uniform(*depth) * inside
        S.co[idx] -= d[:, None] * nrm[idx]
        hole[idx] = np.maximum(hole[idx], inside)
    S.a["pit"] = np.maximum(S.a.get("pit", np.zeros(S.n)), hole)


def erode(S, amp=0.0025, freq=9.0, seed=0, w=None):
    """Low-frequency shallow erosion: inward only (corroded, never swollen)."""
    P = SC.Perlin(seed)
    e = np.clip(SC._z(SC.fbm(P, S.co * freq, 3)), 0, None) * amp
    if w is not None:
        e = e * w
    S.co -= e[:, None] * S.normals()
