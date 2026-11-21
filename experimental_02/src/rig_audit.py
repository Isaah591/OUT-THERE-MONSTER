"""ASTRA R08 - audit of the game rig's articulation (read-only).

    bvenv/bin/python experimental_02/src/rig_audit.py

Opens model/astra_r08_exp02_game.blend and NEVER saves it.  Every pose is set on the in-memory
copy only.  Measures:

  1. inventory  - every bone: parent, children, joint position, which vertices it carries (alone or
                  shared), which body section that is;
  2. independence - each bone rotated on its own: which body sections move (its own, its children's,
                  the blend zone of its joint) and whether anything unrelated moves;
  3. joint range - shoulders, elbows, wrists, hips, knees, ankles, spine, neck, head and jaw bent
                  through a range of angles on their own: stretch, compression and folded triangles,
                  and the largest angle that stays clean;
  4. pivots     - whether each joint's pivot lies inside the limb it bends;
  5. seams      - whether the Head and Body meshes stay joined when the head and jaw move;
and renders the bone-influence map and isolated joint bends to renders/audit/.
Results: analysis/rig_audit.json.
"""
import os, sys, json, math, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
from mathutils import Quaternion, Vector, Matrix
from mathutils.bvhtree import BVHTree
import game_anim as GA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "model", "astra_r08_exp02_game.blend")
OUT_DIR = os.path.join(ROOT, "renders", "audit")
STUD = 0.28
MOVED = 0.002 / STUD              # a vertex "moves" when it travels more than 2 mm
EDGE_MIN = 0.03 / STUD            # edges of at least 3 cm are measured for stretch

SECTIONS = {
    "Pelvis": ["Pelvis"], "Torso": ["Spine", "Chest"], "Neck": ["Neck"], "Head": ["Head"], "Jaw": ["Jaw"],
    "R shoulder": ["RightShoulder"], "R upper arm": ["RightUpperArm"], "R forearm": ["RightLowerArm", "RightWrist"],
    "R hand": ["RightHand"], "L shoulder": ["LeftShoulder"], "L upper arm": ["LeftUpperArm"],
    "L forearm": ["LeftLowerArm", "LeftWrist"], "L hand": ["LeftHand"],
    "R hip": ["RightHip"], "R upper leg": ["RightUpperLeg"], "R lower leg": ["RightLowerLeg"], "R foot": ["RightFoot", "RightToes"],
    "L hip": ["LeftHip"], "L upper leg": ["LeftUpperLeg"], "L lower leg": ["LeftLowerLeg"], "L foot": ["LeftFoot", "LeftToes"],
}
SECTION_OF = {b: s for s, bs in SECTIONS.items() for b in bs}

# joint range tests: (label, bone, local axis, angles in degrees)
FULL = [-120, -90, -60, -30, 30, 60, 90, 120]
RANGES = [
    ("R shoulder - swing fore/aft", "RightUpperArm", "X", FULL),
    ("R shoulder - swing out/in", "RightUpperArm", "Z", [-90, -60, -30, 30, 60, 90]),
    ("R elbow", "RightLowerArm", "X", FULL),
    ("R forearm bend", "RightWrist", "X", [-90, -60, -30, 30, 60, 90]),
    ("R hand", "RightHand", "X", [-90, -60, -30, 30, 60, 90]),
    ("L shoulder - swing fore/aft", "LeftUpperArm", "X", FULL),
    ("L shoulder - swing out/in", "LeftUpperArm", "Z", [-90, -60, -30, 30, 60, 90]),
    ("L elbow", "LeftLowerArm", "X", FULL),
    ("L hand", "LeftHand", "X", [-90, -60, -30, 30, 60, 90]),
    ("R hip - swing fore/aft", "RightUpperLeg", "X", FULL),
    ("R hip - swing out/in", "RightUpperLeg", "Z", [-60, -45, -20, 20, 45, 60]),
    ("R knee", "RightLowerLeg", "X", FULL),
    ("R ankle", "RightFoot", "X", [-45, -30, -15, 15, 30, 45]),
    ("L hip - swing fore/aft", "LeftUpperLeg", "X", FULL),
    ("L hip - swing out/in", "LeftUpperLeg", "Z", [-60, -45, -20, 20, 45, 60]),
    ("L knee", "LeftLowerLeg", "X", FULL),
    ("L ankle", "LeftFoot", "X", [-45, -30, -15, 15, 30, 45]),
    ("Pelvis tilt", "Pelvis", "X", [-30, -15, 15, 30]),
    ("Spine bend", "Spine", "X", [-45, -30, -15, 15, 30, 45]),
    ("Spine twist", "Spine", "Y", [-45, -30, -15, 15, 30, 45]),
    ("Chest bend", "Chest", "X", [-45, -30, -15, 15, 30, 45]),
    ("Neck nod", "Neck", "X", [-45, -30, -15, 15, 30, 45]),
    ("Neck turn", "Neck", "Z", [-60, -45, -30, -15, 15, 30, 45, 60]),
    ("Head nod", "Head", "X", [-45, -30, -15, 15, 30, 45]),
    ("Head turn", "Head", "Z", [-60, -45, -30, -15, 15, 30, 45, 60]),
    ("Jaw open / shut", "Jaw", "X", [-30, -21, -10, 10, 16, 25]),
]
AXES = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}


def log(*a):
    print("[rig_audit]", *a, flush=True)


class Scene:
    def __init__(self):
        bpy.ops.wm.open_mainfile(filepath=GAME)
        self.sc = bpy.context.scene
        self.ao = bpy.data.objects[GA.ARMATURE]
        GA.set_clip(self.ao, None)
        self.meshes = [bpy.data.objects[n] for n in ("ASTRA_R08_Body", "ASTRA_R08_Head", "ASTRA_R08_Eyes")]
        self.names = [b.name for b in self.ao.data.bones]
        self.W, self.F, self.E = {}, {}, {}
        for ob in self.meshes:
            me = ob.data
            gnames = [g.name for g in ob.vertex_groups]
            W = np.zeros((len(me.vertices), len(self.names)))
            for v in me.vertices:
                for g in v.groups:
                    W[v.index, self.names.index(gnames[g.group])] = g.weight
            self.W[ob.name] = W
            self.F[ob.name] = np.array([list(p.vertices) for p in me.polygons])
            e = np.zeros(len(me.edges) * 2, np.int32)
            me.edges.foreach_get("vertices", e)
            self.E[ob.name] = e.reshape(-1, 2)
        self.rest = self.verts()

    def verts(self):
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        out = {}
        for ob in self.meshes:
            me = ob.evaluated_get(dg).to_mesh()
            v = np.zeros(len(me.vertices) * 3)
            me.vertices.foreach_get("co", v)
            ob.evaluated_get(dg).to_mesh_clear()
            out[ob.name] = v.reshape(-1, 3)
        return out

    def reset(self):
        for p in self.ao.pose.bones:
            p.rotation_mode = "QUATERNION"
            p.rotation_quaternion = Quaternion()
            p.location = (0, 0, 0)
            p.scale = (1, 1, 1)

    def pose(self, bone, axis, deg):
        self.reset()
        self.ao.pose.bones[bone].rotation_quaternion = Quaternion(AXES[axis], math.radians(deg))
        return self.verts()

    def subtree(self, bone):
        b = self.ao.data.bones[bone]
        return {bone} | {c.name for c in b.children_recursive}

    def dominant(self, name):
        return np.array(self.names)[self.W[name].argmax(1)]


def measure(S, V, bones_moving):
    """Stretch / compression / folded triangles of the posed meshes against the rest pose."""
    worst, shrink, folded, where = 1.0, 1.0, 0, None
    for name in ("ASTRA_R08_Body", "ASTRA_R08_Head"):
        R, P, E, F = S.rest[name], V[name], S.E[name], S.F[name]
        moved = np.linalg.norm(P - R, axis=1) > MOVED
        L0 = np.linalg.norm(R[E[:, 0]] - R[E[:, 1]], axis=1)
        L1 = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
        ok = (L0 >= EDGE_MIN) & (moved[E[:, 0]] | moved[E[:, 1]])
        if ok.any():
            r = L1[ok] / L0[ok]
            if r.max() > worst:
                worst = float(r.max())
                i = np.nonzero(ok)[0][int(r.argmax())]
                where = SECTION_OF.get(S.dominant(name)[E[i, 0]], "?")
            shrink = min(shrink, float(r.min()))
        # a triangle is folded when it faces away from where its own bone has turned it
        dom = S.W[name].argmax(1)
        n0 = np.cross(R[F[:, 1]] - R[F[:, 0]], R[F[:, 2]] - R[F[:, 0]])
        n1 = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        mv = moved[F].any(1)
        if mv.any():
            rot = {}
            for bi in np.unique(dom[F[mv, 0]]):
                pb = S.ao.pose.bones[S.names[bi]]
                M = np.array(pb.matrix) @ np.linalg.inv(np.array(S.ao.data.bones[S.names[bi]].matrix_local))
                rot[bi] = M[:3, :3]
            rn = np.array([rot[dom[f[0]]] @ n for f, n in zip(F[mv], n0[mv])])
            a0 = np.linalg.norm(n0[mv], axis=1)
            folded += int(((np.einsum("ij,ij->i", rn, n1[mv]) < 0) & (a0 > 1e-6)).sum())
    return dict(stretch=round(worst, 2), shrink=round(shrink, 2), folded_triangles=folded, worst_section=where)


def inventory(S):
    out = {}
    tot = {}
    for name in ("ASTRA_R08_Body", "ASTRA_R08_Head", "ASTRA_R08_Eyes"):
        W = S.W[name]
        dom = W.argmax(1)
        for j, b in enumerate(S.names):
            d = out.setdefault(b, dict(vertices_any=0, vertices_dominant=0, vertices_alone=0, shares_with={}))
            has = W[:, j] > 0
            d["vertices_any"] += int(has.sum())
            d["vertices_dominant"] += int((dom == j).sum() * (W[:, j].max() > 0))
            d["vertices_alone"] += int((W[:, j] > 0.999).sum())
            for k in np.nonzero((W[has] > 0).any(0))[0]:
                if k != j:
                    d["shares_with"][S.names[k]] = d["shares_with"].get(S.names[k], 0) + int(((W[:, j] > 0) & (W[:, k] > 0)).sum())
        tot[name] = len(W)
    for b in S.ao.data.bones:
        d = out[b.name]
        d["parent"] = b.parent.name if b.parent else None
        d["children"] = [c.name for c in b.children]
        h, t = b.head_local, b.tail_local
        d["head_studio"] = [round(-h[0], 3), round(h[2], 3), round(h[1], 3)]
        d["length_studs"] = round(b.length, 3)
        d["section"] = SECTION_OF.get(b.name, "Root")
    return out, tot


def independence(S):
    res = {}
    dom = {n: S.dominant(n) for n in S.W}
    for b in S.names:
        if b == "Root":
            continue
        V = S.pose(b, "X", 25)
        sub = S.subtree(b)
        par = S.ao.data.bones[b].parent.name if S.ao.data.bones[b].parent else None
        moved_by_section = {}
        for name in S.W:
            mv = np.linalg.norm(V[name] - S.rest[name], axis=1)
            for sec, bones in SECTIONS.items():
                m = np.isin(dom[name], bones)
                if not m.any():
                    continue
                k = mv[m] > MOVED
                if k.any():
                    a = moved_by_section.setdefault(sec, [0, 0, 0.0])
                    a[0] += int(k.sum())
                    a[1] += int(m.sum())
                    a[2] = max(a[2], float(mv[m].max()) * STUD * 100)
                else:
                    a = moved_by_section.setdefault(sec, [0, 0, 0.0])
                    a[1] += int(m.sum())
        own = {SECTION_OF[x] for x in sub if x in SECTION_OF}
        parent_sec = SECTION_OF.get(par)
        unrelated = {s: v for s, v in moved_by_section.items() if v[0] and s not in own and s != parent_sec}
        blend = moved_by_section.get(parent_sec, [0, 1, 0.0]) if parent_sec and parent_sec not in own else [0, 1, 0.0]
        res[b] = dict(moves_sections=sorted(s for s, v in moved_by_section.items() if v[0]),
                      own_sections=sorted(own),
                      parent_blend=dict(section=parent_sec, share=round(blend[0] / max(blend[1], 1), 3), max_cm=round(blend[2], 1)),
                      unrelated=sorted(unrelated))
    S.reset()
    return res


def pivots(S):
    me = bpy.data.objects["ASTRA_R08_Body"].data
    V = S.rest["ASTRA_R08_Body"]
    F = S.F["ASTRA_R08_Body"]
    tree = BVHTree.FromPolygons([tuple(p) for p in V], [tuple(f) for f in F])
    out = {}
    for b in S.ao.data.bones:
        if b.name in ("Root", "Head", "Jaw"):
            continue
        p = b.head_local
        loc, nrm, idx, dist = tree.find_nearest(p)
        # inside test: count crossings of a ray along +Z and -Z
        inside = 0
        for d in (Vector((0, 0, 1)), Vector((0, 0, -1)), Vector((1, 0, 0))):
            o = p.copy()
            hits = 0
            for _ in range(64):
                h = tree.ray_cast(o, d)
                if h[0] is None:
                    break
                hits += 1
                o = h[0] + d * 1e-4
            inside += hits % 2
        out[b.name] = dict(inside=inside >= 2, depth_cm=round(dist * STUD * 100, 1))
    return out


def seams(S):
    """Head mesh against Body mesh where they meet: does any gap open when the head and jaw move?"""
    from scipy.spatial import cKDTree
    H, B = S.rest["ASTRA_R08_Head"], S.rest["ASTRA_R08_Body"]
    d, j = cKDTree(B).query(H)
    near = np.nonzero(d < 0.015 / STUD)[0]
    out = {}
    tests = {"neck turn 45 + nod 30": [("Neck", "Z", 30), ("Neck", "X", 20), ("Head", "Z", 15), ("Head", "X", 10)],
             "head turn 45": [("Head", "Z", 45)], "head nod 40": [("Head", "X", 40)], "jaw open 25": [("Jaw", "X", 25)],
             "jaw shut 30": [("Jaw", "X", -30)]}
    for label, poses in tests.items():
        S.reset()
        for (bn, ax, deg) in poses:
            pb = S.ao.pose.bones[bn]
            pb.rotation_quaternion = Quaternion(AXES[ax], math.radians(deg)) @ pb.rotation_quaternion
        V = S.verts()
        d1 = np.linalg.norm(V["ASTRA_R08_Head"][near] - V["ASTRA_R08_Body"][j[near]], axis=1)
        out[label] = dict(pairs=int(len(near)), max_opening_cm=round(float((d1 - d[near]).max()) * STUD * 100, 2))
    S.reset()
    return out


def ranges(S):
    res = []
    for (label, bone, axis, angles) in RANGES:
        rows = []
        for a in angles:
            V = S.pose(bone, axis, a)
            m = measure(S, V, S.subtree(bone))
            m["angle"] = a
            m["clean"] = m["folded_triangles"] == 0 and m["stretch"] <= 2.0
            rows.append(m)
        pos = [r for r in rows if r["angle"] > 0]
        neg = [r for r in rows if r["angle"] < 0]

        def clean_to(rs):
            best = 0
            for r in sorted(rs, key=lambda r: abs(r["angle"])):
                if r["clean"]:
                    best = abs(r["angle"])
                else:
                    break
            return best
        res.append(dict(test=label, bone=bone, axis=axis, results=rows, clean_to_plus=clean_to(pos), clean_to_minus=clean_to(neg)))
        log(f"   {label:<30} clean to +{clean_to(pos)} / -{clean_to(neg)} deg")
    S.reset()
    return res


# ------------------------------------------------------------------------------- pictures

def bone_colours(names):
    import colorsys
    cols = {}
    chains = {"core": ["Root", "Pelvis", "Spine", "Chest", "Neck", "Head", "Jaw"],
              "R arm": ["RightShoulder", "RightUpperArm", "RightLowerArm", "RightWrist", "RightHand"],
              "L arm": ["LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftWrist", "LeftHand"],
              "R leg": ["RightHip", "RightUpperLeg", "RightLowerLeg", "RightFoot", "RightToes"],
              "L leg": ["LeftHip", "LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "LeftToes"]}
    hues = {"core": [0.10, 0.14, 0.02, 0.07, 0.17, 0.80, 0.0], "R arm": [0.52, 0.58, 0.62, 0.66, 0.70],
            "L arm": [0.30, 0.34, 0.38, 0.42, 0.46], "R leg": [0.73, 0.77, 0.83, 0.88, 0.93], "L leg": [0.45, 0.20, 0.25, 0.11, 0.05]}
    for ch, bs in chains.items():
        for i, b in enumerate(bs):
            h = hues[ch][i]
            v = 0.95 if i % 2 == 0 else 0.62
            s = 0.75 if ch != "core" else 0.55 + 0.08 * i
            cols[b] = colorsys.hsv_to_rgb(h, s, v)
    cols["Jaw"] = (0.95, 0.95, 0.95)
    return cols


def influence_material(S):
    """Paint every vertex with its bones' colours (weighted), as a colour attribute, in memory only."""
    cols = bone_colours(S.names)
    C = np.array([cols[n] for n in S.names])
    mat = bpy.data.materials.new("AuditInfluence")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "audit_col"
    nt.links.new(at.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    for ob in S.meshes:
        me = ob.data
        W = S.W[ob.name]
        rgb = (W @ C) / np.maximum(W.sum(1, keepdims=True), 1e-9)
        attr = me.color_attributes.new("audit_col", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", np.hstack([rgb, np.ones((len(rgb), 1))]).astype(np.float32).ravel())
        me.materials.clear()
        me.materials.append(mat)
    return cols


def render_audit(S, cols):
    import scene as SC
    import views
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(OUT_DIR, exist_ok=True)
    sc = S.sc
    S.ao.scale = (STUD, STUD, STUD)
    SC.studio(sc)
    SC.setup_cycles(sc, samples=12)
    sc.render.use_persistent_data = True
    fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    fr = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)

    def shoot(view, path, res):
        v = views.VIEWS[view]
        w, h = v["size"]
        k = res / max(w, h)
        SC.aim_studio(v.get("az", 0.0))
        cam = SC.camera(sc, "AuditCam", tuple(v["pos"]), tuple(v["target"]), lens=v["lens"])
        SC.render(sc, cam, path, res=(int(round(w * k)), int(round(h * k))))
        return Image.open(path).convert("RGB")
    views.VIEWS["audit_front"] = views.cam(0.0, 3.0, (-0.15, -0.75, 1.40), 22.0, 3.9, (520, 560))
    views.VIEWS["audit_side"] = views.cam(90.0, 3.0, (0.0, -0.80, 1.40), 22.0, 4.2, (560, 560))
    views.VIEWS["audit_back"] = views.cam(180.0, 6.0, (-0.15, -0.40, 1.40), 22.0, 3.9, (520, 560))
    views.VIEWS["audit_tq"] = views.cam(32.0, 8.0, (-0.05, -0.75, 1.35), 22.0, 4.4, (560, 460))
    # 1. influence map
    S.reset()
    tiles = [shoot(v, os.path.join(OUT_DIR, f"_inf_{v}.png"), 620) for v in ("audit_front", "audit_side", "audit_back")]
    leg_w = 300
    W = sum(t.width for t in tiles) + leg_w
    H = max(t.height for t in tiles) + 50
    im = Image.new("RGB", (W, H), (13, 14, 15))
    d = ImageDraw.Draw(im)
    d.text((12, 12), "ASTRA R08 - WHAT EACH BONE MOVES (colour = bone; blends = shared joint zones)", font=fb, fill=(236, 236, 232))
    x = 0
    for t in tiles:
        im.paste(t, (x, 50))
        x += t.width
    y = 60
    for n in S.names:
        c = tuple(int(255 * v) for v in cols[n])
        d.rectangle([x + 12, y, x + 30, y + 14], fill=c)
        d.text((x + 38, y - 1), n, font=fr, fill=(220, 220, 216))
        y += 20
    im.save(os.path.join(OUT_DIR, "ASTRA_R08_bone_influence_map.png"))
    # 2. isolated joint bends
    demo = [("R shoulder fwd 60", "RightUpperArm", "X", -60), ("R shoulder out 45", "RightUpperArm", "Z", -45),
            ("R elbow 90", "RightLowerArm", "X", -90), ("R hand 45", "RightHand", "X", -45),
            ("L shoulder fwd 60", "LeftUpperArm", "X", -60), ("L elbow 90", "LeftLowerArm", "X", -90),
            ("R hip fwd 60", "RightUpperLeg", "X", -60), ("R knee 90", "RightLowerLeg", "X", 90),
            ("L hip fwd 60", "LeftUpperLeg", "X", -60), ("L knee 90", "LeftLowerLeg", "X", 90),
            ("R ankle 30", "RightFoot", "X", -30), ("Pelvis tilt 20", "Pelvis", "X", 20),
            ("Spine bend 25", "Spine", "X", 25), ("Chest twist 25", "Chest", "Y", 25),
            ("Neck turn 40", "Neck", "Z", 40), ("Head nod 30", "Head", "X", 30),
            ("Jaw open +16", "Jaw", "X", 16), ("Jaw shut -21", "Jaw", "X", -21)]
    tiles = []
    for (label, bone, axis, deg) in demo:
        S.pose(bone, axis, deg)
        view = "audit_side" if bone in ("Jaw", "Head", "Spine", "Pelvis", "RightLowerLeg", "LeftLowerLeg", "RightFoot") else "audit_tq"
        t = shoot(view, os.path.join(OUT_DIR, f"_bend_{bone}_{axis}_{deg}.png"), 360)
        dd = ImageDraw.Draw(t)
        dd.text((8, 6), label, font=fb, fill=(255, 255, 255))
        tiles.append(t)
    S.reset()
    per = 6
    tw, th = tiles[0].size
    rows = math.ceil(len(tiles) / per)
    im = Image.new("RGB", (per * tw, rows * th + 44), (13, 14, 15))
    d = ImageDraw.Draw(im)
    d.text((12, 12), "ASTRA R08 - EACH JOINT BENT ON ITS OWN (everything else at rest; colours as on the influence map)", font=fb, fill=(236, 236, 232))
    for i, t in enumerate(tiles):
        t = t.resize((tw, th))
        im.paste(t, ((i % per) * tw, 44 + (i // per) * th))
    im.save(os.path.join(OUT_DIR, "ASTRA_R08_isolated_joints.png"))
    S.ao.scale = (1, 1, 1)


def main():
    t0 = time.time()
    S = Scene()
    inv, totals = inventory(S)
    log(f"inventory: {len(inv)} bones ({time.time() - t0:.1f} s)")
    ind = independence(S)
    log(f"independence ({time.time() - t0:.1f} s)")
    piv = pivots(S)
    sea = seams(S)
    log(f"pivots, seams ({time.time() - t0:.1f} s)")
    rng = ranges(S)
    log(f"ranges ({time.time() - t0:.1f} s)")
    json.dump(dict(model=os.path.relpath(GAME, ROOT), saved=False, vertices=totals, bones=inv, independence=ind,
                   pivots=piv, seams=sea, ranges=rng), open(os.path.join(ROOT, "analysis", "rig_audit.json"), "w"), indent=1)
    if "--no-render" not in sys.argv:
        cols = influence_material(S)
        render_audit(S, cols)
        log(f"pictures ({time.time() - t0:.1f} s)")
    # nothing is ever saved: the game file on disk is unchanged
    log("done; model file not modified")


if __name__ == "__main__":
    main()
