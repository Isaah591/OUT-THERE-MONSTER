"""ASTRA R08 - Experimental Model 02: game-ready geometry (stage 1 of the Roblox build).

    bvenv/bin/python experimental_02/src/game_mesh.py [out.blend]

The high-detail model is about 1.1 million triangles of rust plates standing on a few dozen planar
blocks.  The game mesh is not a decimation of those plates.  It is rebuilt from the same blocks:

  1. every block (body.py / head.py, exactly as the high-detail build places them) is cut into a
     regular grid of quads - a ring of edges every few centimetres along each limb;
  2. the blocks of the body are united into one watertight skin, and so are the blocks of the skull
     (hidden faces inside the joints disappear, nothing is left open);
  3. each vertex is moved out or in to the height of the armour standing on it in the high-detail
     model (sampled by ray), so the outline keeps the broken, stepped look of the plates;
  4. the lower jaw is its own closed piece and every tooth is its own closed spike (thinned from the
     high-detail tooth's own vertices), so the jaw can swing without touching the skull;
  5. UV maps: the united skins are unwrapped flat (before step 3, so nothing is stretched), teeth
     and cords are unrolled, and everything is packed into one 0..1 square per mesh.

Output: three meshes in metres - ASTRA_R08_Body, ASTRA_R08_Head, ASTRA_R08_Eyes - with the vertex
data the later stages need (which block a vertex came from, how far the lower jaw carries it, how
far the bake cage stands off).  Stage 2 (game_bake.py) bakes the textures from the high-detail
model; stage 3 (game_rig.py) adds the skeleton and weights and converts to studs.
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import kernel as K
from model import Model
import body, head

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIGH = os.path.join(ROOT, "model", "astra_r08_exp02_highdetail.blend")
OUT = os.path.join(ROOT, "model", "work", "game_stage1.blend")

CELL_BODY = 0.068          # grid size on the body's blocks (m)
CELL_HEAD = 0.046          # ... on the skull, its slabs and the jaw
RELIEF = 1.0               # how much of the sampled armour height the outline takes (0 = flat blocks)
REGIONS = ["solid", "jaw", "tooth_upper", "tooth_lower", "gum_upper", "gum_band", "sinew", "web", "throat", "rod"]
RID = {n: i for i, n in enumerate(REGIONS)}


def log(*a):
    print("[game_mesh]", *a, flush=True)


# ------------------------------------------------------------------------------- the blocks

def collect(seed=8):
    """The same blocks, rods, teeth and cords the high-detail build makes (build.py), unplated."""
    m = Model(seed)
    body.build_body(m)
    head.build_head(m)
    return m


def weld_coarse(co, tol=1e-6):
    """Merge coincident vertices of a coarse mesh (parts built side by side share an outline)."""
    V = co.arrays()
    key = np.round(V / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    out = K.Coarse(co.name)
    out.V = [V[i].copy() for i in first]
    for fi, f in enumerate(co.F):
        g = [int(inv[i]) for i in f]
        g = [v for k, v in enumerate(g) if v != g[k - 1]]
        assert len(g) >= 3
        out.f(g, kind=co.kind[fi], grain=co.grain[fi], tag=co.tag[fi], patch=co.patch[fi])
    return out, inv


def skull_solid(m):
    """The skull as one closed block: the skull's contour rings, the socket reveals welded into
    their openings, and every armour slab raised out of the surface it lies on (the slab's own
    corners from the high-detail build), with a wall round its edge - no boolean, no seam."""
    sk = m.get("skull")["coarse"]
    merged = K.Coarse("skull")
    merged.extend(sk)
    merged.extend(m.get("socket_rims")["coarse"])
    W, inv = weld_coarse(merged)
    E = K.Coarse("skull")
    E.V = [p.copy() for p in W.V]
    owner = {}
    tops = []
    for si, (name, _, _) in enumerate(head.SLABS):
        co = m.get(name)["coarse"]
        faces, verts = co.src
        tv = {int(inv[v]): E.v(co.V[k]) for k, v in enumerate(verts)}
        tops.append(tv)
        for fi in faces:
            owner[fi] = si
    for fi, f in enumerate(W.F):
        if fi in owner:
            E.f([tops[owner[fi]][v] for v in f], kind="plate", tag="slab_top")
        else:
            E.f(f, kind=W.kind[fi], tag=W.tag[fi])
    for si in range(len(head.SLABS)):
        edges = set()
        for fi, s2 in owner.items():
            if s2 == si:
                f = W.F[fi]
                for k in range(len(f)):
                    edges.add((f[k], f[(k + 1) % len(f)]))
        tv = tops[si]
        for (a, b) in sorted(edges):
            if (b, a) not in edges:
                E.f([tv[a], a, b, tv[b]], kind="plate", tag="slab_edge")
    return E


def refine_part(co, cell, coarse_kinds=("void", "socket", "core"), coarse_factor=2.4):
    """Cut a closed coarse block into a conforming grid: returns (V, faces, face kinds).
    Opposite edges of a quad share one count, so every side of a limb gets its own number of
    columns and each stretch between two rings its own number of rows.  Triangles are fans
    (apex = their last corner); larger polygons (the caps of limbs) are filled ring by ring."""
    V = co.arrays()
    parent = {}

    def find(e):
        parent.setdefault(e, e)
        while parent[e] != e:
            parent[e] = parent[parent[e]]
            e = parent[e]
        return e

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    ek = lambda i, j: (min(i, j), max(i, j))
    fcell = [cell * (coarse_factor if k in coarse_kinds else 1.0) for k in co.kind]
    want = {}
    for fi, f in enumerate(co.F):
        m = len(f)
        es = [ek(f[k], f[(k + 1) % m]) for k in range(m)]
        for e in es:
            find(e)
            n = np.linalg.norm(V[e[0]] - V[e[1]]) / fcell[fi]
            want[e] = max(want.get(e, 0.0), n)
        if m == 4:
            union(es[0], es[2])
            union(es[1], es[3])
        elif m == 3:
            union(es[1], es[2])
    cls = {}
    for e in parent:
        r = find(e)
        cls[r] = max(cls.get(r, 0.0), want[e])
    count = {e: max(1, int(round(cls[find(e)]))) for e in parent}

    pts, faces, kinds = [], [], []

    def add(P, F, kind):
        o = sum(len(p) for p in pts)
        pts.append(np.asarray(P, float).reshape(-1, 3))
        for f in F:
            faces.append([i + o for i in f])
            kinds.append(kind)

    for fi, f in enumerate(co.F):
        poly = V[f]
        m = len(f)
        kind = co.kind[fi]
        if m == 4:
            ku, kv = count[ek(f[0], f[1])], count[ek(f[1], f[2])]
            G = K._bilinear(poly, ku, kv)
            idx = np.arange((ku + 1) * (kv + 1)).reshape(ku + 1, kv + 1)
            Q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
            add(G, Q.tolist(), kind)
        elif m == 3:
            kc, kr = count[ek(f[0], f[1])], count[ek(f[1], f[2])]
            P, F, rows = [], [], []
            for r in range(kr):
                s = r / kr
                a, b = poly[0] + (poly[2] - poly[0]) * s, poly[1] + (poly[2] - poly[1]) * s
                rows.append([len(P) + i for i in range(kc + 1)])
                P += [a + (b - a) * (i / kc) for i in range(kc + 1)]
            apex = len(P)
            P.append(poly[2])
            for r in range(kr - 1):
                for i in range(kc):
                    F.append([rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]])
            for i in range(kc):
                F.append([rows[-1][i], rows[-1][i + 1], apex])
            add(P, F, kind)
        else:
            B = []
            for k in range(m):
                a, b = poly[k], poly[(k + 1) % m]
                n = count[ek(f[k], f[(k + 1) % m])]
                B += [a + (b - a) * (i / n) for i in range(n)]
            B = np.array(B)
            N = len(B)
            c = B.mean(0)
            rad = np.linalg.norm(B - c, axis=1).mean()
            scales = [1.0] + ([0.55] if rad > 1.6 * fcell[fi] else []) + ([0.22] if rad > 3.2 * fcell[fi] else [])
            P, F = [], []
            for s in scales:
                P += list(c + (B - c) * s)
            ci = len(P)
            P.append(c)
            for r in range(len(scales) - 1):
                for i in range(N):
                    j = (i + 1) % N
                    F.append([r * N + i, r * N + j, (r + 1) * N + j, (r + 1) * N + i])
            o = (len(scales) - 1) * N
            for i in range(N):
                F.append([o + i, o + (i + 1) % N, ci])
            add(P, F, kind)
    P = np.concatenate(pts)
    key = np.round(P / 2e-6).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    F2, K2 = [], []
    for f, k in zip(faces, kinds):
        g = [int(inv[i]) for i in f]
        g = [v for i, v in enumerate(g) if v != g[i - 1]]
        if len(g) >= 3:
            F2.append(g)
            K2.append(k)
    return P[first], F2, K2


def rod_solid(rd):
    """A rod as a closed prism: three of the high-detail rod's own rings (sunk end, shoulder, end)."""
    V = rd["V"]
    S = 6
    rings = [V[k * S:(k + 1) * S] for k in (0, 3, 4)]
    P = np.concatenate(rings)
    F = []
    for i in range(2):
        for j in range(S):
            a = i * S
            F.append([a + j, a + (j + 1) % S, a + S + (j + 1) % S, a + S + j])
    F.append(list(range(S))[::-1])
    F.append([2 * S + j for j in range(S)])
    return P, F, ["rod"] * len(F)


# ------------------------------------------------------------------------------- Blender helpers

def new_object(name, V, faces, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in V], [], [list(map(int, f)) for f in faces])
    me.update()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def is_closed(V, faces):
    edges = {}
    for f in faces:
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            edges[(a, b)] = edges.get((a, b), 0) + 1
    bad = sum(1 for (a, b), n in edges.items() if n != 1 or (b, a) not in edges)
    return bad


def unite(name, solids):
    """Boolean union (exact solver) of closed solids [(part name, V, faces)] -> one object."""
    obs = []
    for (pn, V, F) in solids:
        bad = is_closed(V, F)
        if bad:
            log(f"   warning: {pn} is not closed ({bad} open / doubled edges)")
        obs.append(new_object("tmp_" + pn, V, F))
    base = obs[0]
    for o in obs[1:]:
        md = base.modifiers.new("u", "BOOLEAN")
        md.operation = "UNION"
        md.solver = "EXACT"
        md.object = o
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(base.evaluated_get(dg))
    me.name = name
    for o in obs:
        dm = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(dm)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_arrays(me):
    V = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    return V.reshape(-1, 3), [list(p.vertices) for p in me.polygons]


def clean(ob, weld=0.0012):
    """Weld slivers left along the joints of the union and drop anything degenerate."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-5)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def manifold_report(me):
    bm = bmesh.new()
    bm.from_mesh(me)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()
    return nonman, tris


def label_parts(V, parts):
    """For every vertex: the block whose surface it lies on (index into parts) and whether it lies
    on two blocks at once (the seams of the union)."""
    best = np.full(len(V), 1e9)
    second = np.full(len(V), 1e9)
    lab = np.zeros(len(V), np.int32)
    for pi, (pn, PV, PF) in enumerate(parts):
        tree = BVHTree.FromPolygons([tuple(p) for p in PV], PF, all_triangles=False)
        d = np.array([tree.find_nearest(Vector(p))[3] for p in V])
        better = d < best
        second = np.where(better, best, np.minimum(second, d))
        lab = np.where(better, pi, lab)
        best = np.where(better, d, best)
    return lab, second < 2e-4, second


# ------------------------------------------------------------------------------- UV maps

def activate(ob):
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        if o is not None:
            o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob


def unwrap_solid(ob, angle=66.0, sharp=58.0):
    """Flat unwrap of a united skin while its faces are still planar: charts by facing direction,
    then every chart relaxed (angle based), so three sides of a limb unfold as one undistorted
    strip.  Edges sharper than `sharp` degrees are kept hard and are always chart borders."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=np.radians(angle), island_margin=0.0, area_weight=0.0, correct_aspect=True,
                             scale_to_bounds=False)
    bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    bm = bmesh.new()
    bm.from_mesh(me)
    lim = np.radians(sharp)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > lim:
            e.seam = True
            e.smooth = False
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")


def pack(ob, margin=0.0035, scale_by_region=None):
    """Equal texel density everywhere (optionally scaled per region), then pack into 0..1."""
    me = ob.data
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    if scale_by_region:
        reg = np.zeros(len(me.polygons), np.int32)
        me.attributes["region"].data.foreach_get("value", reg)
        uv = me.uv_layers.active.data
        for p in me.polygons:
            k = scale_by_region.get(REGIONS[reg[p.index]], 1.0)
            if k != 1.0:
                for li in p.loop_indices:
                    uv[li].uv = uv[li].uv * k
    activate(ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(udim_source="CLOSEST_UDIM", rotate=True, rotate_method="ANY", scale=True, merge_overlap=False,
                            margin_method="ADD", margin=margin, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")


def uv_stats(me):
    """(share of the 0..1 square covered, UV out-of-range count, flipped/zero-area triangles)."""
    uv = np.zeros(len(me.loops) * 2)
    me.uv_layers.active.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    area, zero = 0.0, 0
    for p in me.polygons:
        q = uv[list(p.loop_indices)]
        a = 0.5 * abs(sum(q[i][0] * q[(i + 1) % len(q)][1] - q[(i + 1) % len(q)][0] * q[i][1] for i in range(len(q))))
        area += a
        zero += a < 1e-12
    out = int(((uv < -1e-6) | (uv > 1 + 1e-6)).any(1).sum())
    return area, out, int(zero)


# ------------------------------------------------------------------------------- armour height

def load_high(names):
    """Append the named objects of the high-detail model and return {name: BVH}."""
    with bpy.data.libraries.load(HIGH, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    coll = bpy.data.collections.new("HIGH")
    bpy.context.scene.collection.children.link(coll)
    for o in dst.objects:
        coll.objects.link(o)
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    return {o.name: BVHTree.FromObject(o, dg) for o in dst.objects}, coll


def vertex_normals(me):
    N = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("normal", N)
    return N.reshape(-1, 3)


def sample_height(V, N, trees, start=0.075, lo=-0.032, hi=0.046, spread=0.013):
    """Height of the high-detail surface above each vertex of the flat skin, along its normal:
    median of five rays (so a ray falling down a crack between plates does not decide)."""
    H = np.zeros(len(V))
    for i in range(len(V)):
        n = N[i]
        t1 = np.cross(n, (0.0, 0.0, 1.0) if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0))
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(n, t1)
        hs = []
        for (a, b) in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            o = V[i] + n * start + (t1 * a + t2 * b) * spread
            best, front = None, True
            for tr in trees:
                hit = tr.ray_cast(Vector(o), Vector(-n), start - lo + 0.02)
                if hit[0] is not None and (best is None or hit[3] < best):
                    best = hit[3]
                    front = (np.array(hit[1]) @ n) > 0.0
            # a ray that begins inside a neighbouring block meets a surface from behind: not a reading
            if best is not None and front:
                hs.append(start - best)
        if hs:
            H[i] = float(np.clip(np.median(hs), lo, hi))
    return H


def smooth_scalar(me, H, fixed, it=1, k=0.35):
    """One gentle pass over the mesh edges: a single vertex must not stand up like a thorn."""
    E = np.zeros(len(me.edges) * 2, np.int32)
    me.edges.foreach_get("vertices", E)
    E = E.reshape(-1, 2)
    for _ in range(it):
        acc = np.zeros(len(H))
        cnt = np.zeros(len(H))
        np.add.at(acc, E[:, 0], H[E[:, 1]])
        np.add.at(acc, E[:, 1], H[E[:, 0]])
        np.add.at(cnt, E[:, 0], 1)
        np.add.at(cnt, E[:, 1], 1)
        H2 = H * (1 - k) + k * acc / np.maximum(cnt, 1)
        H = np.where(fixed, H, H2)
    return H


# ------------------------------------------------------------------------------- loose shells

class Shells:
    """Closed pieces with their own unrolled UVs: teeth, cords, the throat."""

    def __init__(self):
        self.V, self.F, self.UV, self.reg, self.cage, self.jaw = [], [], [], [], [], []

    def add(self, V, F, UV, region, cage, jaw=None):
        o = len(self.V)
        V = np.asarray(V, float)
        self.V += list(V)
        for f, uv in zip(F, UV):
            self.F.append([i + o for i in f])
            self.UV.append([tuple(map(float, q)) for q in uv])
            self.reg.append(RID[region])
        self.cage += list(np.broadcast_to(np.asarray(cage, float), (len(V),)))
        self.jaw += list(np.broadcast_to(np.nan if jaw is None else np.asarray(jaw, float), (len(V),)))

    def ringed(self, rings, region, cage, jaw=None, tip=None, base=None, cap_ends=True):
        """A closed tube from rings of points (each ring the same count, counter-clockwise seen
        from its far end), unrolled as one strip.  tip / base: end points for the fans (default:
        ring centres)."""
        R = [np.asarray(r, float) for r in rings]
        S = len(R[0])
        V = np.concatenate(R)
        F, UV = [], []
        per = [np.linalg.norm(np.roll(r, -1, axis=0) - r, axis=1) for r in R]
        cum = [np.concatenate([[0.0], np.cumsum(p)]) - p.sum() / 2 for p in per]
        cen = np.array([r.mean(0) for r in R])
        vv = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(cen, axis=0), axis=1))])
        for i in range(len(R) - 1):
            for j in range(S):
                a, b = i * S + j, i * S + (j + 1) % S
                F.append([a, b, b + S, a + S])
                UV.append([(cum[i][j], vv[i]), (cum[i][j + 1], vv[i]), (cum[i + 1][j + 1], vv[i + 1]), (cum[i + 1][j], vv[i + 1])])
        n = len(V)
        extra = []
        if cap_ends:
            # far end
            c1 = cen[-1] if tip is None else np.asarray(tip, float)
            extra.append(c1)
            o = (len(R) - 1) * S
            d1 = float(np.linalg.norm(c1 - cen[-1])) + float(np.mean(np.linalg.norm(R[-1] - cen[-1], axis=1)))
            for j in range(S):
                F.append([o + j, o + (j + 1) % S, n])
                UV.append([(cum[-1][j], vv[-1]), (cum[-1][j + 1], vv[-1]), ((cum[-1][j] + cum[-1][j + 1]) / 2, vv[-1] + d1)])
            # near end (usually buried): a small fan of its own
            c0 = cen[0] if base is None else np.asarray(base, float)
            extra.append(c0)
            r0 = float(np.mean(np.linalg.norm(R[0] - cen[0], axis=1))) * 0.6
            ang = [2 * np.pi * j / S for j in range(S)]
            for j in range(S):
                k = (j + 1) % S
                F.append([n + 1, k, j])
                UV.append([(0.0, 0.0), (r0 * np.cos(ang[k]), r0 * np.sin(ang[k])), (r0 * np.cos(ang[j]), r0 * np.sin(ang[j]))])
        self.add(np.concatenate([V, np.array(extra).reshape(-1, 3)]), F, UV, region, cage, jaw)


def tube_rings(P, R, sides, flat, hint):
    """Rings of kernel.tube without its wobble (same frames, so a flattened band lies as built)."""
    P = np.asarray(P, float)
    hint = np.asarray(hint, float)
    T_, EX, EY = K.path_frames(P, hint if abs(K.unit(P[-1] - P[0]) @ K.unit(hint)) < 0.95 else np.array([1.0, 0.0, 0.0]))
    return [np.array([P[i] + EX[i] * np.cos(2 * np.pi * j / sides) * R[i] + EY[i] * np.sin(2 * np.pi * j / sides) * R[i] * flat
                      for j in range(sides)]) for i in range(len(P))]


def thin_path(P, R, step):
    """Keep the points of a cord that matter: about one every `step` of its own radius."""
    keep = [0]
    acc = 0.0
    for i in range(1, len(P) - 1):
        acc += np.linalg.norm(P[i] - P[i - 1])
        if acc >= max(step * R[i], 0.03):
            keep.append(i)
            acc = 0.0
    keep.append(len(P) - 1)
    return P[keep], R[keep]


def build_shells(m, jaw_tree, skull_tree):
    """Teeth, gum cords, sinews, the throat - and how far the lower jaw carries each vertex."""
    sh = Shells()

    def jaw_share(P):
        """0 on the skull, 1 on the jaw, by which of the two is nearer."""
        out = []
        for p in np.asarray(P, float).reshape(-1, 3):
            ds = skull_tree.find_nearest(Vector(p))[3]
            dj = jaw_tree.find_nearest(Vector(p))[3]
            w = ds / max(ds + dj, 1e-6)
            out.append(w * w * (3 - 2 * w))
        return np.array(out)

    # teeth: four of the high-detail tooth's nine rings and its tip - the same facets, fewer of them
    for sp in m.info["teeth"]:
        S, V = sp["sides"], sp["V"]
        rings = [V[k * S:(k + 1) * S] for k in (0, 1, 4, 7)]
        lower = sp["jaw"] == "lower"
        sh.ringed(rings, "tooth_lower" if lower else "tooth_upper", 0.008, jaw=1.0 if lower else 0.0,
                  tip=V[9 * S], base=V[9 * S + 1])
    # cords of gum and sinew, along the centre lines of the high-detail ones
    gum = m.loose["head_gums"][0]
    for c in head.CORDS:
        P, R = c["P"], c["R"]
        rmean = float(np.mean(R))
        if c.get("band"):
            Pk, Rk = thin_path(P, R, 2.0)
            rings = tube_rings(Pk, Rk, 6, c["flat"], c["hint"])
            sh.ringed(rings, "gum_band", 0.006, jaw=1.0)
            continue
        dark = c["bucket"] is not gum
        if rmean < 0.011:
            continue          # the thin strands twisting round each sinew stay in the texture only
        sides = 5 if rmean < 0.028 else 6
        Pk, Rk = thin_path(P, R, 1.5 if not dark else 3.2)
        rings = tube_rings(Pk, Rk, sides, 1.0, c["hint"])
        w = jaw_share(np.concatenate(rings))
        hmin = min(head.Hl(p)[2] for p in Pk)
        if dark:
            region = "throat"
        elif hmin > -0.02 and float(w.max()) < 0.5:
            region, w = "gum_upper", np.zeros_like(w)          # gum line and pads under the skull
        else:
            region = "sinew" if rmean >= 0.011 else "web"
        ww = np.concatenate([w, jaw_share([Pk[-1], Pk[0]])])
        sh.ringed(rings, region, max(0.008, 0.40 * rmean), jaw=ww)
    # the throat: the black sheet that closes the lower jaw from behind, as a thin closed slab
    # (front face toward the mouth, back face 1.4 cm behind it, walls round the edge)
    G_ = m.info["throat_sheet"]
    n, nv = G_.shape[:2]
    sel = list(range(0, n, 2)) + ([n - 1] if (n - 1) % 2 else [])
    A = G_[sel]
    n = len(A)
    Nr = np.cross(np.gradient(A, axis=1), np.gradient(A, axis=0))
    Nr /= np.maximum(np.linalg.norm(Nr, axis=2, keepdims=True), 1e-9)
    mouth = head.Hw(0.0, 0.20, -0.30)
    sgn = 1.0 if float(np.mean(((mouth - A) * Nr).sum(-1))) > 0 else -1.0     # does a quad (a, b, c, d) face the mouth?
    T_ = 0.014
    B_ = A - Nr * sgn * T_
    off = n * nv
    V = np.concatenate([A.reshape(-1, 3), B_.reshape(-1, 3)])
    w = jaw_share(V)
    lu = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(A[:, nv // 2], axis=0), axis=1))])
    lv = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(A[n // 2], axis=0), axis=1))])
    F, UV, front_edges = [], [], set()
    for i in range(n - 1):
        for k in range(nv - 1):
            q = [i * nv + k, i * nv + k + 1, (i + 1) * nv + k + 1, (i + 1) * nv + k]
            uv = [(lu[i], lv[k]), (lu[i], lv[k + 1]), (lu[i + 1], lv[k + 1]), (lu[i + 1], lv[k])]
            if sgn < 0:
                q, uv = q[::-1], uv[::-1]
            F.append(q)
            UV.append(uv)
            for j in range(4):
                front_edges.add((q[j], q[(j + 1) % 4]))
            # the back face: same quad, turned the other way, its own island beside the front one
            F.append([v + off for v in q[::-1]])
            UV.append([(u + lu[-1] + 0.05, v_) for (u, v_) in uv[::-1]])
    # walls, walked round the edge of the grid so their strip unrolls in one piece
    loop = [(0, k) for k in range(nv)] + [(i, nv - 1) for i in range(1, n)] + [(n - 1, k) for k in range(nv - 2, -1, -1)] + \
           [(i, 0) for i in range(n - 2, 0, -1)]
    loop = [i * nv + k for (i, k) in loop]
    cu = 0.0
    for j in range(len(loop)):
        a_, b_ = loop[j], loop[(j + 1) % len(loop)]
        if (b_, a_) in front_edges:
            a_, b_ = b_, a_
        assert (a_, b_) in front_edges, "throat edge not on the front face"
        L = float(np.linalg.norm(V[a_] - V[b_]))
        F.append([b_, a_, a_ + off, b_ + off])
        UV.append([(cu + L, -0.06), (cu, -0.06), (cu, -0.06 - T_), (cu + L, -0.06 - T_)])
        cu += L
    sh.add(V, F, UV, "throat", 0.008, jaw=w)
    return sh


# ------------------------------------------------------------------------------- assembly

def finish_object(name, solid_ob, solid_parts, shells, solid_region, cell_cage, trees, jaw_fn=None, part_offset=0):
    """Displace a united skin to the armour height, add the loose shells, pack the UVs."""
    me = solid_ob.data
    V, F = mesh_arrays(me)
    names = [p[0] for p in solid_parts]
    lab, seam, dist = label_parts(V, solid_parts)
    N = vertex_normals(me)
    H = sample_height(V, N, trees) * RELIEF
    H[seam] = 0.0
    H = smooth_scalar(me, H, seam)
    # rods are bars, not plated: leave them as built
    isrod = np.array([names[i].startswith("rod") for i in lab])
    H[isrod] = 0.0
    V2 = V + N * H[:, None]
    uvl = me.uv_layers.active.data
    uv = np.zeros(len(me.loops) * 2)
    uvl.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    sharp_e = {tuple(sorted(e.vertices)) for e in me.edges if e.use_edge_sharp}
    seam_e = {tuple(sorted(e.vertices)) for e in me.edges if e.use_seam}
    # one mesh: the skin, then the shells
    nV = len(V2)
    allV = list(V2) + (list(shells.V) if shells else [])
    allF = [list(f) for f in F] + ([[i + nV for i in f] for f in shells.F] if shells else [])
    ob = new_object(name, allV, allF)
    me2 = ob.data
    ul = me2.uv_layers.new(name="UVMap")
    flat = []
    for p in me.polygons:
        for li in p.loop_indices:
            flat.append(uv[li])
    if shells:
        for q in shells.UV:
            flat += q
    ul.data.foreach_set("uv", np.asarray(flat, float).reshape(-1))
    # attributes
    reg = np.zeros(len(allF), np.int32)
    reg[:len(F)] = RID["solid"]
    for fi, f in enumerate(F):
        if isrod[f].all():
            reg[fi] = RID["rod"]
    if shells:
        reg[len(F):] = shells.reg
    if jaw_fn is not None:
        reg[:len(F)] = jaw_fn["region"]
    a = me2.attributes.new("region", "INT", "FACE")
    a.data.foreach_set("value", reg)
    part = np.full(len(allV), -1, np.int32)
    part[:nV] = lab + part_offset
    a = me2.attributes.new("part", "INT", "POINT")
    a.data.foreach_set("value", part)
    cage = np.zeros(len(allV))
    # in the creases between two blocks the cage stays close, so it does not reach into the neighbour
    cage[:nV] = np.clip(dist * 0.8, 0.012, cell_cage)
    if shells:
        cage[nV:] = shells.cage
    a = me2.attributes.new("cage", "FLOAT", "POINT")
    a.data.foreach_set("value", cage)
    jw = np.zeros(len(allV))
    if jaw_fn is not None:
        jw[:nV] = jaw_fn["jaw"]
    if shells:
        jw[nV:] = np.nan_to_num(np.array(shells.jaw), nan=0.0)
    a = me2.attributes.new("jaw", "FLOAT", "POINT")
    a.data.foreach_set("value", jw)
    seamflag = np.zeros(len(allV))
    seamflag[:nV] = seam
    a = me2.attributes.new("on_seam", "FLOAT", "POINT")
    a.data.foreach_set("value", seamflag)
    for e in me2.edges:
        k = tuple(sorted(e.vertices))
        if k in sharp_e:
            e.use_edge_sharp = True
        if k in seam_e:
            e.use_seam = True
    for p in me2.polygons:
        p.use_smooth = True
    ob["parts"] = json.dumps(names)
    me2.update()
    return ob, dict(height_mean=float(H.mean()), height_min=float(H.min()), height_max=float(H.max()))


def triangulate(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def eyes_object(m, r=0.0072):
    """The two pupils: tiny octahedra deep in the sockets (their own mesh, so Roblox can make them glow)."""
    V, F, UV = [], [], []
    ex, eb, eh = (K.unit(a) for a in head.frame())
    for c in m.info["pupils"]:
        o = len(V)
        V += [c + ex * r, c - ex * r, c + eh * r, c - eh * r, c - eb * r * 1.3, c + eb * r * 1.3]
        for (a, b, k) in ((0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)):
            F.append([o + a, o + b, o + k])
    ob = new_object("ASTRA_R08_Eyes", V, F)
    ul = ob.data.uv_layers.new(name="UVMap")
    uv = []
    for fi in range(len(F)):
        u0, v0 = (fi % 4) * 0.25, (fi // 4) * 0.25
        uv += [(u0 + 0.02, v0 + 0.02), (u0 + 0.23, v0 + 0.02), (u0 + 0.125, v0 + 0.23)]
    ul.data.foreach_set("uv", np.asarray(uv, float).reshape(-1))
    for p in ob.data.polygons:
        p.use_smooth = False
    return ob


def joints(m):
    """Landmarks for the skeleton (metres, world): the body's from body.py, the head's from head.py."""
    J = {k: np.asarray(v, float).tolist() for k, v in m.info["joints"].items()}
    H = head.Hw
    J.update(head_base=H(0.0, 0.680, 0.020).tolist(), head_front=H(0.0, 0.000, 0.110).tolist(),
             head_top=H(0.0, 0.47, 0.42).tolist(), skull_centre=H(0.0, 0.40, 0.12).tolist(),
             jaw_hinge=H(0.001, 0.478, -0.040).tolist(), jaw_hinge_R=H(-0.236, 0.478, -0.040).tolist(),
             jaw_hinge_L=H(0.238, 0.478, -0.040).tolist(), jaw_tip=H(0.042, 0.340, -0.666).tolist(),
             head_x=K.unit(head.frame()[0]).tolist(), head_back=K.unit(head.frame()[1]).tolist(),
             head_up=K.unit(head.frame()[2]).tolist(),
             pupils=np.asarray(m.info["pupils"]).tolist())
    J["teeth"] = [dict(jaw=sp["jaw"], root=sp["root"].tolist(), tip=sp["tip"].tolist(), r=float(sp["r"]), L=float(sp["L"]),
                       dir=sp["dir"].tolist(), bd=sp["bd"].tolist(), bend=float(sp["bend"])) for sp in m.info["teeth"]]
    J["rods"] = [dict(group=r["group"], base=r["base"].tolist(), dir=r["dir"].tolist(), L=r["L"], host=r["host"]) for r in m.info["rods"]]
    return J


def main(out=OUT):
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    m = collect()
    slabs = [x[0] for x in head.SLABS]
    body_parts, head_parts = [], []
    for p in m.parts:
        co = p["coarse"]
        if p["group"] == "body":
            body_parts.append((co.name,) + refine_part(co, CELL_BODY)[:2])
        elif co.name in ("hinge_R", "hinge_L", "occiput"):
            head_parts.append((co.name,) + refine_part(co, CELL_HEAD)[:2])
    skV, skF, _ = refine_part(skull_solid(m), CELL_HEAD)
    head_parts.insert(0, ("skull", skV, skF))
    jawV, jawF, _ = refine_part(m.get("jaw")["coarse"], CELL_HEAD)
    for i, rd in enumerate(m.info["rods"]):
        P, F, _ = rod_solid(rd)
        (body_parts if rd["group"] == "body" else head_parts).append((f"rod_{rd['group']}_{i}", P, F))
    log(f"blocks cut: body {len(body_parts)}, head {len(head_parts)} + jaw  ({time.time() - t0:.1f} s)")

    ub = unite("U_body", body_parts)
    clean(ub)
    uh = unite("U_head", head_parts)
    clean(uh)
    uj = new_object("U_jaw", jawV, jawF)
    for o in (ub, uh, uj):
        nm, tr = manifold_report(o.data)
        log(f"   {o.name}: {tr} triangles, {nm} open or doubled edges")
        assert nm == 0, "the united skin must be watertight"
        unwrap_solid(o)
    log(f"united and unwrapped ({time.time() - t0:.1f} s)")

    names = ["R08_body_plates", "R08_body_under", "R08_body_muscle", "R08_head_plates", "R08_head_under", "R08_head_muscle"]
    trees, hcoll = load_high(names)
    bt = [trees[n] for n in names[:3]]
    ht = [trees[n] for n in names[3:]]
    stats = {}
    body_ob, stats["body_relief"] = finish_object("ASTRA_R08_Body", ub, body_parts, None, "solid", 0.030, bt)

    skull_tree = BVHTree.FromPolygons([tuple(p) for p in skV], skF)
    jaw_tree = BVHTree.FromPolygons([tuple(p) for p in jawV], jawF)
    shells = build_shells(m, jaw_tree, skull_tree)
    h1, stats["head_relief"] = finish_object("tmp_head_a", uh, head_parts, None, "solid", 0.026, ht)
    h2, stats["jaw_relief"] = finish_object("tmp_head_b", uj, [("jaw", jawV, jawF)], shells, "jaw", 0.020, ht,
                                           jaw_fn=dict(region=RID["jaw"], jaw=1.0), part_offset=len(head_parts))
    activate(h1)
    h2.select_set(True)
    bpy.ops.object.join()
    head_ob = h1
    head_ob.name = head_ob.data.name = "ASTRA_R08_Head"
    head_ob["parts"] = json.dumps([p[0] for p in head_parts] + ["jaw"])
    eyes = eyes_object(m)

    for o in (ub, uh, uj):
        dm = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(dm)
    for o in list(hcoll.objects):
        dm = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(dm)
    bpy.data.collections.remove(hcoll)

    pack(body_ob, margin=0.0030, scale_by_region=dict(rod=0.8))
    pack(head_ob, margin=0.0030, scale_by_region=dict(throat=0.35, gum_band=0.9, web=0.8))
    for o in (body_ob, head_ob, eyes):
        triangulate(o)
        nm, tr = manifold_report(o.data)
        area, outside, zero = uv_stats(o.data)
        stats[o.name] = dict(triangles=tr, vertices=len(o.data.vertices), uv_coverage=round(area, 3), uv_outside_0_1=outside,
                             uv_zero_area_faces=zero)
        log(f"   {o.name}: {tr} triangles, {len(o.data.vertices)} vertices, UV cover {area:.2f}, outside 0..1: {outside}")
    stats["cells_m"] = dict(body=CELL_BODY, head=CELL_HEAD)
    stats["regions"] = REGIONS
    an = os.path.join(ROOT, "analysis")
    json.dump(stats, open(os.path.join(an, "game_mesh.json"), "w"), indent=1)
    json.dump(joints(m), open(os.path.join(an, "game_joints.json"), "w"), indent=1)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    log(f"saved {out}  ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(args[0] if args else OUT)
