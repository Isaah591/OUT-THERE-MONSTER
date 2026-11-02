"""
Continuous corroded surface for the v5 variation (see sculpt.py for the Surf helpers).

Instead of distinct armour-like plates, the shell gets damage that is part of the material:
a fine network of thin, shallow cracks (no lifted or tilted plates), scattered square-ish rust
pits, and low-frequency erosion. All displacements are inward and small, so the low-poly
facets of the form stay readable.
"""
import numpy as np
from scipy.spatial import cKDTree

import sculpt as SC


def crack_network(S, cell=0.07, width=0.0018, depth=0.0025, seed=0, w=None):
    """Thin, flat, embedded cracks along jagged Voronoi borders (no plate relief)."""
    return SC.flakes(S, cell=cell, crack=width, depth=depth, lift=0.0, tilt=0.0, seed=seed, w=w)


def pits(S, per_m2, size=(0.010, 0.024), depth=(0.004, 0.010), seed=0, w=None):
    """Scattered square-ish rust pits (small dark holes in the shell), written to `cavity`."""
    r = np.random.default_rng(seed)
    nrm = S.normals()
    # surface area estimate from the mean edge length
    area = S.n * S.h * S.h * 0.9
    count = int(per_m2 * area)
    pool = np.arange(S.n) if w is None else np.flatnonzero(w > 0.5)
    if count <= 0 or len(pool) == 0:
        return
    centres = r.choice(pool, size=min(count, len(pool)), replace=False)
    hole = np.zeros(S.n)
    tree = cKDTree(S.co)
    for i in centres:
        c, n = S.co[i], nrm[i]
        sz = r.uniform(*size)
        idx = tree.query_ball_point(c, sz * 1.6)
        if not idx:
            continue
        idx = np.asarray(idx)
        t = SC.unit(np.cross(n, [0.0, 0.0, 1.0] if abs(n[2]) < 0.9 else [1.0, 0.0, 0.0]))
        b = np.cross(n, t)
        a = r.uniform(0, np.pi)
        t, b = t * np.cos(a) + b * np.sin(a), -t * np.sin(a) + b * np.cos(a)
        rel = S.co[idx] - c
        q = np.maximum(np.abs(rel @ t) / (sz * r.uniform(0.7, 1.0)), np.abs(rel @ b) / (sz * r.uniform(0.5, 1.0)))
        inside = np.clip((1.0 - q) / 0.25, 0, 1)                  # square-ish, crisp-ish edge
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
