"""Container for the generated creature: coarse parts with their wounds, plus loose pieces
(rods, muscle strands, teeth, gums ...).  generate() returns plain numpy meshes."""
import numpy as np
import kernel as K


class Model:
    def __init__(self, seed=8):
        self.seed = seed
        self.parts = []          # dict(name, coarse, wounds, params, seed, group)
        self.loose = {}          # name -> (MeshOut, material key, smooth)
        self.rng = np.random.default_rng(seed)
        self.info = {}

    # -- coarse parts -------------------------------------------------------------------------
    def part(self, coarse, wounds=None, params=None, group="body"):
        w = wounds or K.Wounds(self.seed + len(self.parts))
        self.parts.append(dict(name=coarse.name, coarse=coarse, wounds=w, params=params or {},
                               seed=self.seed * 100 + len(self.parts), group=group))
        return self.parts[-1]

    def get(self, name):
        for p in self.parts:
            if p["name"] == name:
                return p
        raise KeyError(name)

    # -- loose geometry -----------------------------------------------------------------------
    def bucket(self, name, material, smooth=False):
        if name not in self.loose:
            self.loose[name] = (K.MeshOut(), material, smooth)
        return self.loose[name][0]

    def add_rod(self, base, direction, length, radius=0.028, group="body"):
        V, Q, T = K.rod(base, direction, length, radius, self.rng)
        self.bucket(f"{group}_rods", "rod").add(V, Q, T)

    # -- output -------------------------------------------------------------------------------
    def generate(self, only=None, verbose=True):
        """Returns {object name: (mesh dict, material key, smooth)}."""
        out = {}
        groups = {}
        for p in self.parts:
            if only and p["group"] not in only:
                continue
            pl, un = K.build_shell(p["coarse"], p["wounds"], p["params"], p["seed"])
            g = groups.setdefault(p["group"], (K.MeshOut(), K.MeshOut(), K.MeshOut()))
            g[0].add(pl["V"], pl["Q"], vattr=pl["vattr"], qattr=pl["fattr"])
            g[1].add(un["V"], un["Q"], vattr=un["vattr"])
            # muscle strands in the wounds
            rng = np.random.default_rng(p["seed"] + 77)
            for z in p["wounds"].z:
                if z.get("n") is None or z.get("strands", True) is False:
                    continue
                for (V, Q, T) in K.strands_for_wound(z, rng, z["n"], spacing=z.get("spacing", 0.034),
                                                    depth=z.get("sdepth", 0.030)):
                    g[2].add(V, Q, T)
            if verbose:
                print(f"   {p['name']:<18} plates {len(pl['Q']):>7} quads   under {len(un['Q']):>6}")
        for gname, (pl, un, st) in groups.items():
            out[f"{gname}_plates"] = (pl.finish(), "rust", False)
            out[f"{gname}_under"] = (un.finish(), "under", False)
            if st.nv:
                out[f"{gname}_muscle"] = (st.finish(), "muscle", True)
        for name, (mo, mat, smooth) in self.loose.items():
            if only and name.split("_")[0] not in only:
                continue
            if mo.nv:
                out[name] = (mo.finish(), mat, smooth)
        return out


def support(points, c, d):
    """How far a ring of points reaches from c along direction d."""
    return float(np.max((np.asarray(points) - np.asarray(c)) @ K.unit(d)))


def surface_point(part, s, side):
    """Point on a lofted beam's surface: s in [0,1] along its path, on the side facing `side`.
    Returns (point, outward direction, tangent)."""
    co = part["coarse"]
    P = co.path
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    d = s * cum[-1]
    i = int(np.clip(np.searchsorted(cum, d) - 1, 0, len(seg) - 1))
    f = (d - cum[i]) / max(seg[i], 1e-9)
    c = P[i] * (1 - f) + P[i + 1] * f
    t = K.unit(P[i + 1] - P[i])
    sd = np.asarray(side, float)
    sd = K.unit(sd - (sd @ t) * t)
    V = co.arrays()
    r0 = V[co.rings[i]]
    r1 = V[co.rings[i + 1]]
    reach = (1 - f) * support(r0, P[i], sd) + f * support(r1, P[i + 1], sd)
    return c + sd * reach, sd, t


def rod_on(m, part, s, side, length, radius=0.027, tilt=(0, 0, 0), group="body"):
    """A bar driven into a beam at s along it, sticking out of the side facing `side`."""
    p, sd, t = surface_point(part, s, side)
    m.add_rod(p - sd * 0.02, K.unit(sd + np.asarray(tilt, float)), length, radius, group=group)


def wound_on(part, s, side, L, W, axis=None, strength=1.0, strands=True, spacing=0.034, shift=0.0):
    """Add a wound on a lofted beam: s in [0,1] along its path, on the side facing `side`
    (a world direction).  L / W = half length (along the beam, or `axis`) / half width."""
    centre, sd, t = surface_point(part, s, side)
    centre = centre + t * shift
    ax = t if axis is None else K.unit(np.asarray(axis, float) - (np.asarray(axis, float) @ sd) * sd)
    part["wounds"].add(centre, ax, L, W, normal=sd, strength=strength)
    z = part["wounds"].z[-1]
    z["strands"] = strands
    z["spacing"] = spacing
    return z
