"""ASTRA R08 - game body v2: armoured joints (used by game_mesh.py unless ASTRA_BODY=v1).

v1 united every block of the body into one skin and blended the bones across each joint, which
folds and goes rubbery past about 30 degrees (docs/RIG_AUDIT.md).  v2 keeps the same blocks, the
same skeleton and the same outline at rest, but builds the limbs the way the design is built - as
armour pieces:

  * the torso, pelvis, hip blocks and groin stay one skin that bends smoothly (Pelvis / Spine /
    Chest, with the shoulder corners and hip blocks on their own bones);
  * every limb is cut at every joint pivot into segments - shoulder plate (where there is one, see
    below), upper arm, forearm, second forearm, hand; thigh, shin, foot (with its ankle block),
    toes; and the neck - each a
    closed shell that moves rigidly with its bone, so no limb ever stretches or folds;
  * at each joint the smaller of the two pieces ends in a rounded knuckle centred on the pivot,
    reaching into the larger one.  At rest the knuckle is buried (fitted so it stays inside), so the
    outline does not change; when the joint bends the knuckle fills the outside of the bend, and the
    pieces slide over each other like plates.

Each segment is cut from the very same loft (rings interpolated at the pivot), so a straightened
limb is the v1 limb exactly.

The shoulder plate is the part of the arm's loft between the chest and the shoulder pivot.  Where it
stands well clear of the chest (the short left arm's shoulder block) it is a piece of its own on the
Shoulder bone and the upper arm turns in it like a socket.  Where it is only a thin collar (the long
right arm leaves the chest right at the joint) there is no plate: left on the Shoulder bone the collar
would stand out as a blade whenever the arm swings away from it, and carried by the arm its far end
would swing out of the chest.  The upper arm's own rounded top, centred on the joint, takes the
collar's place and turns in the chest like a ball in its socket.
"""
import numpy as np
import kernel as K

KNUCKLE_PHI = (18.0, 36.0, 54.0, 70.0, 80.0, 87.0)    # ring angles of the rounded end (degrees); the last
                                                      # ring is a tenth of the section, so the tip has no flat cap
# grid sizes: the torso bends, so it keeps a fine grid; rigid pieces cannot stretch, so a coarser grid
# loses nothing (the armour relief and the baked maps carry the detail)
CELL_TORSO, CELL_LIMB, CELL_FOOT, CELL_TOE, CELL_NECK, CELL_TEST = 0.060, 0.072, 0.060, 0.050, 0.072, 0.080
PLATE_MIN_CLEAR = 0.12      # m of the arm's centre line between the chest surface and the shoulder pivot
                            # for the plate to stay with the Shoulder bone (else it rides with the arm)


def _arc(P):
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)])


def path_param(P, p):
    """Arc length along polyline P of the point closest to p."""
    cum = _arc(P)
    best, tb = 1e9, 0.0
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        ab = b - a
        L2 = ab @ ab
        f = float(np.clip(((p - a) @ ab) / L2, 0, 1)) if L2 > 0 else 0.0
        d = np.linalg.norm(a + ab * f - p)
        if d < best:
            best, tb = d, cum[i] + f * np.sqrt(L2)
    return tb


def ring_at(co, t):
    """Interpolated section ring of a loft at arc length t (and the path point and tangent there)."""
    V = co.arrays()
    P = co.path
    cum = _arc(P)
    t = float(np.clip(t, 0, cum[-1]))
    i = int(np.clip(np.searchsorted(cum, t) - 1, 0, len(P) - 2))
    f = (t - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    R = V[co.rings[i]] * (1 - f) + V[co.rings[i + 1]] * f
    c = P[i] * (1 - f) + P[i + 1] * f
    tan = K.unit(P[i + 1] - P[i])
    return R, c, tan


def knuckle_rings(ring, centre, direction, depth, lateral=1.0):
    """Rounded end: rings shrinking toward a tip `depth` beyond the section along `direction`."""
    c0 = ring.mean(0)
    out = []
    for phi in KNUCKLE_PHI:
        a = np.radians(phi)
        s = np.cos(a) ** 0.75 * lateral
        out.append(c0 + direction * depth * np.sin(a) + (ring - c0) * s)
    return out


def segment(name, co, t0, t1, knuckle0=None, knuckle1=None, kind="plate"):
    """A closed piece of loft `co` between arc lengths t0 < t1.  knuckleN = (direction, depth,
    lateral) adds a rounded end beyond that end (direction points away from the piece)."""
    P = co.path
    cum = _arc(P)
    rings = []
    R0, c0, tan0 = ring_at(co, t0)
    rings.append(R0)
    V = co.arrays()
    for i in range(len(P)):
        if t0 + 1e-6 < cum[i] < t1 - 1e-6:
            rings.append(V[co.rings[i]])
    R1, c1, tan1 = ring_at(co, t1)
    rings.append(R1)
    if knuckle0 is not None:
        d, depth, lat = knuckle0
        rings = list(reversed(knuckle_rings(R0, c0, d, depth, lat))) + rings
    if knuckle1 is not None:
        d, depth, lat = knuckle1
        rings = rings + knuckle_rings(R1, c1, d, depth, lat)
    out = K.Coarse(name)
    ids = [out.vs(r) for r in rings]
    m = len(ids[0])
    for i in range(len(ids) - 1):
        for j in range(m):
            out.f([ids[i][j], ids[i][(j + 1) % m], ids[i + 1][(j + 1) % m], ids[i + 1][j]], kind=kind, tag=f"side{j}")
    out.f(ids[0][::-1], kind=kind, tag="cap0")
    out.f(ids[-1], kind=kind, tag="cap1")
    return out


class Inside:
    """Point-in-solid test for a closed mesh (ray parity, majority of three directions)."""

    def __init__(self, V, F):
        from mathutils.bvhtree import BVHTree
        self.tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in V], [tuple(map(int, f)) for f in F])

    def __call__(self, p, margin=0.0):
        from mathutils import Vector
        votes = 0
        for d in ((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (0.577, 0.577, 0.577)):
            d = Vector(d).normalized()
            o = Vector(tuple(map(float, p)))
            hits = 0
            for _ in range(64):
                h = self.tree.ray_cast(o, d)
                if h[0] is None:
                    break
                hits += 1
                o = h[0] + d * 1e-5
            votes += hits % 2
        if votes < 2:
            return False
        if margin > 0:
            loc, nrm, idx, dist = self.tree.find_nearest(Vector(tuple(map(float, p))))
            return dist >= margin
        return True


def fit_knuckle(ring, centre, direction, depth, inside, margin=0.02, min_depth_frac=0.2, open_to=0.0):
    """Largest knuckle (depth, lateral scale) whose every point lies inside the socket (at rest).
    Points less than `open_to` beyond the section are not tested: that part of the knuckle is meant
    to show (it stands in for a collar)."""
    lat = 1.0
    d = depth
    for _ in range(40):
        pts = np.concatenate(knuckle_rings(ring, centre, direction, d, lat))
        pts = pts[(pts - ring.mean(0)) @ direction >= open_to]
        if all(inside(p, margin) for p in pts):
            return d, lat
        if d > depth * min_depth_frac:
            d *= 0.88
        else:
            lat *= 0.9
            if lat < 0.45:
                break
    return d, lat


PLATES = {}                 # filled by build(): how far each shoulder plate stands clear of the chest, what became of it


class InsideAny:
    """Point inside any of several closed solids (parity tests do not add up over overlapping solids)."""

    def __init__(self, *solids):
        self.solids = solids

    def __call__(self, p, margin=0.0):
        return any(s(p, margin) for s in self.solids)


def build(m, skeleton_m, refine, unite, mesh_arrays, clean):
    """Returns the body pieces: list of dict(name, V, F, bone (None = skinned), parts (for the
    skinned shell: [(part name, V, F)]), knuckle (per-vertex flag))."""
    piv = {b[0]: np.asarray(b[2], float) for b in skeleton_m}           # bone heads (pivots), metres
    get = {p["name"]: p for p in m.parts}
    pieces = []

    def add(name, co, bone, cell, knuckle_mask_fn=None):
        V, F, _ = refine(co, cell)
        kn = knuckle_mask_fn(V) if knuckle_mask_fn else np.zeros(len(V), bool)
        pieces.append(dict(name=name, V=V, F=[list(f) for f in F], bone=bone, knuckle=kn))

    # ---- the skinned torso: torso, pelvis, hip blocks and groin.  The rods driven into the torso
    # stay separate closed pieces (added at the end): united, their bases leave slivers in the skin
    # that flip when the spine bends
    tparts = []
    for n in ("torso", "pelvis", "hip_R", "hip_L", "groin"):
        V, F, _ = refine(get[n]["coarse"], CELL_TORSO)
        tparts.append((n, V, F))
    from game_mesh import rod_solid
    rods = m.info["rods"]
    from game_mesh import triangulate, remove_fins, open_edges
    torso_ob = unite("V2_torso", tparts)
    clean(torso_ob)
    # triangulate the union while its faces are still flat, then drop the back-to-back fins that
    # splitting the boolean's many-sided faces leaves; the skin must stay closed
    triangulate(torso_ob, "EAR_CLIP")
    remove_fins(torso_ob)
    assert open_edges(torso_ob.data) == (0, 0), "torso shell not closed"
    TV, TF = mesh_arrays(torso_ob.data)
    torso_in = Inside(TV, TF)
    pieces.append(dict(name="torso", V=TV, F=TF, bone=None, knuckle=np.zeros(len(TV), bool), parts=tparts, object=torso_ob))

    def knuckle_flags(V, centre, direction, beyond=0.0):
        """Vertices of a piece lying past the pivot plane on the knuckle side."""
        return ((V - centre) @ direction) > beyond + 1e-4

    # ---- arms: shoulder plate, upper arm, forearm, second forearm, hand
    for side, loft in (("Right", "arm_long"), ("Left", "arm_short")):
        co = get[loft]["coarse"]
        P = co.path
        L = _arc(P)[-1]
        t_sh, t_el, t_fo, t_wr = (path_param(P, piv[f"{side}{b}"]) for b in ("UpperArm", "LowerArm", "Wrist", "Hand"))
        # plate above the shoulder pivot: the socket the upper arm turns in (Shoulder bone) - or, if it
        # is only a thin collar round the top of the arm, part of the upper arm (see the module notes)
        plate = segment(f"{side}ShoulderPlate", co, 0.0, t_sh)
        PV, PF, _ = refine(plate, CELL_LIMB)
        plate_in = InsideAny(Inside(PV, [list(f) for f in PF]), torso_in)     # the socket: plate and chest
        ts = np.linspace(0.0, t_sh, 60)
        inside_t = [t for t in ts if torso_in(ring_at(co, t)[1])]
        clear = t_sh - (max(inside_t) if inside_t else 0.0)
        if clear >= PLATE_MIN_CLEAR:
            pieces.append(dict(name=f"{side}ShoulderPlate", V=PV, F=[list(f) for f in PF], bone=f"{side}Shoulder",
                               knuckle=np.zeros(len(PV), bool)))
            PLATES[side] = dict(clear_of_chest_m=round(float(clear), 3), plate="a piece of its own on the Shoulder bone")
        else:
            PLATES[side] = dict(clear_of_chest_m=round(float(clear), 3), plate="none: the upper arm's rounded top takes its place")
        # upper arm: rounded top reaching up into the plate and torso; rounded end into the forearm
        R0, c0, tan0 = ring_at(co, t_sh)
        R1, c1, tan1 = ring_at(co, t_el)
        nxt = segment("tmp", co, t_el, t_fo)
        next_in = Inside(*refine(nxt, CELL_TEST)[:2])
        up = -tan0
        dep = 0.95 * max(np.linalg.norm(R0 - R0.mean(0), axis=1).max(), 0.05)
        if clear >= PLATE_MIN_CLEAR:          # hidden in the plate and chest at rest
            d0, l0 = fit_knuckle(R0, c0, up, dep, plate_in)
        else:                                 # a full rounded top: its first few cm show where the collar was,
            d0, l0 = fit_knuckle(R0, c0, up, dep, torso_in, margin=0.005, open_to=clear + 0.01)   # the rest is in the chest
        PLATES[side].update(top_knuckle_depth_m=round(float(d0), 3), top_knuckle_width=round(float(l0), 2))
        dep1 = 0.95 * np.linalg.norm(R1 - R1.mean(0), axis=1).max()
        d1, l1 = fit_knuckle(R1, c1, tan1, dep1, next_in)
        seg = segment(f"{side}UpperArm", co, t_sh, t_el, knuckle0=(up, d0, l0), knuckle1=(tan1, d1, l1))
        add(f"{side}UpperArm", seg, f"{side}UpperArm", CELL_LIMB,
            lambda V, c0=c0, up=up, c1=c1, t1=tan1: knuckle_flags(V, c0, up) | knuckle_flags(V, c1, t1))
        # forearm and second forearm: each ends in a knuckle reaching into the next piece
        for (a, b, bone, nb) in ((t_el, t_fo, "LowerArm", (t_fo, t_wr)), (t_fo, t_wr, "Wrist", (t_wr, L))):
            Rb, cb, tb = ring_at(co, b)
            nxt = segment("tmp", co, nb[0], nb[1])
            nin = Inside(*refine(nxt, CELL_TEST)[:2])
            depb = 0.95 * np.linalg.norm(Rb - Rb.mean(0), axis=1).max()
            db, lb = fit_knuckle(Rb, cb, tb, depb, nin)
            seg = segment(f"{side}{bone}", co, a, b, knuckle1=(tb, db, lb))
            add(f"{side}{bone}", seg, f"{side}{bone}", CELL_LIMB, lambda V, cb=cb, tb=tb: knuckle_flags(V, cb, tb))
        add(f"{side}Hand", segment(f"{side}Hand", co, t_wr, L), f"{side}Hand", CELL_LIMB)

    # ---- legs: thigh (knuckles into the hip block and into the knee block), shin (knuckle into the
    # ankle block), foot with its ankle block, toes
    for side, s in (("Right", "R"), ("Left", "L")):
        th = get[f"thigh_{s}"]["coarse"]
        sh = get[f"shin_{s}"]["coarse"]
        foot_parts = []
        for n in (f"foot_{s}", f"ankle_{s}"):
            V, F, _ = refine(get[n]["coarse"], CELL_FOOT)
            foot_parts.append((n, V, F))
        fob = unite(f"V2_foot_{s}", foot_parts)
        clean(fob)
        triangulate(fob, "EAR_CLIP")
        remove_fins(fob)
        assert open_edges(fob.data) == (0, 0), f"foot {s} not closed"
        FV, FF = mesh_arrays(fob.data)
        foot_in = Inside(FV, FF)
        shin_in = Inside(*refine(sh, CELL_TEST)[:2])
        Pt = th.path
        Lt = _arc(Pt)[-1]
        t_hip = path_param(Pt, piv[f"{side}UpperLeg"])
        t_knee = path_param(Pt, piv[f"{side}LowerLeg"])
        R0, c0, tan0 = ring_at(th, t_hip)
        R1, c1, tan1 = ring_at(th, min(t_knee, Lt))
        dep0 = 0.95 * np.linalg.norm(R0 - R0.mean(0), axis=1).max()
        d0, l0 = fit_knuckle(R0, piv[f"{side}UpperLeg"], -tan0, dep0, torso_in)
        dep1 = 0.95 * np.linalg.norm(R1 - R1.mean(0), axis=1).max()
        d1, l1 = fit_knuckle(R1, piv[f"{side}LowerLeg"], tan1, dep1, shin_in)
        seg = segment(f"{side}UpperLeg", th, t_hip, min(t_knee, Lt), knuckle0=(-tan0, d0, l0), knuckle1=(tan1, d1, l1))
        add(f"{side}UpperLeg", seg, f"{side}UpperLeg", CELL_LIMB,
            lambda V, c0=c0, t0=tan0, c1=c1, t1=tan1: knuckle_flags(V, c0, -t0) | knuckle_flags(V, c1, t1))
        Ps = sh.path
        Ls = _arc(Ps)[-1]
        t_ank = path_param(Ps, piv[f"{side}Foot"])
        Ra, ca, ta = ring_at(sh, min(t_ank, Ls))
        depa = 0.95 * np.linalg.norm(Ra - Ra.mean(0), axis=1).max()
        da, la = fit_knuckle(Ra, piv[f"{side}Foot"], ta, depa, foot_in)
        seg = segment(f"{side}LowerLeg", sh, 0.0, min(t_ank, Ls), knuckle1=(ta, da, la))
        add(f"{side}LowerLeg", seg, f"{side}LowerLeg", CELL_LIMB, lambda V, ca=ca, ta=ta: knuckle_flags(V, ca, ta))
        pieces.append(dict(name=f"{side}Foot", V=FV, F=FF, bone=f"{side}Foot", knuckle=np.zeros(len(FV), bool), object=fob))
        for k in range(4):
            add(f"{side}Toe{k}", get[f"toe_{s}{k}"]["coarse"], f"{side}Toes", CELL_TOE)

    # ---- neck: rigid, rounded base reaching into the torso; its top is buried in the head
    nk = get["neck"]["coarse"]
    Pn = nk.path
    Ln = _arc(Pn)[-1]
    Rn, cn, tn = ring_at(nk, 0.0)
    depn = 0.95 * np.linalg.norm(Rn - Rn.mean(0), axis=1).max()
    dn, ln = fit_knuckle(Rn, piv["Neck"], -tn, depn, torso_in)
    seg = segment("Neck", nk, 0.0, Ln, knuckle0=(-tn, dn, ln))
    add("Neck", seg, "Neck", CELL_NECK, lambda V, cn=cn, tn=tn: knuckle_flags(V, cn, -tn))

    # ---- rods driven into the limbs: rigid with the piece their base is in
    for i, rd in enumerate(rods):
        if rd["group"] != "body" or rd["host"] == "torso":
            continue
        P, F, _ = rod_solid(rd)
        base = rd["base"] + rd["dir"] * 0.03
        best, bone = 1e9, None
        for pc in pieces:
            if pc["bone"] is None:
                continue
            d = np.linalg.norm(pc["V"] - base, axis=1).min()
            if d < best:
                best, bone = d, pc["bone"]
        pieces.append(dict(name=f"rod_body_{i}", V=P, F=[list(f) for f in F], bone=bone, knuckle=np.zeros(len(P), bool), rod=True))
    # ---- rods driven into the torso: skinned like the torso where their base is (bone None)
    for i, rd in enumerate(rods):
        if rd["group"] == "body" and rd["host"] == "torso":
            P, F, _ = rod_solid(rd)
            pieces.append(dict(name=f"rod_body_{i}", V=P, F=[list(f) for f in F], bone=None, knuckle=np.zeros(len(P), bool), rod=True))
    return pieces
