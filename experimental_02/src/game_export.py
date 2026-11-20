"""ASTRA R08 - Experimental Model 02: FBX export for Roblox and its verification (stage 5).

    bvenv/bin/python experimental_02/src/game_export.py [game.blend]

Writes export/:
    ASTRA_R08.fbx                       the character: three skinned meshes on the 27-bone skeleton,
                                        rest pose, one material per mesh with its textures embedded,
                                        no animation
    animations/ASTRA_R08_<Clip>.fbx     one clip per file (Roblox reads one animation track from an
                                        FBX): the skeleton alone, keyed on every frame at 30 fps

Then every file is read back and checked, three independent ways:

  1. the raw FBX structure (Blender's own FBX parser, no importer logic): axis system and units,
     triangles per mesh, skin clusters and the number of bones on each vertex, embedded texture
     images (pixel size and channels decoded from the embedded bytes), animation stacks;
  2. Blender's Python FBX importer, and
  3. Blender's C++ FBX importer (built on ufbx, a separate FBX reader):
     each re-imports the character, compares meshes, UVs, materials, skeleton and weights with the
     source, then plays every clip from its own file on the re-imported rig and compares the
     deformed vertices with the source at the start, a third, two thirds and the end of the clip.

Finally the files are checked against Roblox's published import requirements for skinned meshes.
Results: analysis/fbx_verification.json (all numbers) and docs/FBX_VERIFICATION.md (summary).
Roblox Studio itself cannot run in this container; see docs/ROBLOX_IMPORT.md for the import steps.
"""
import os, sys, io, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import addon_utils
from mathutils import Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "model", "astra_r08_exp02_game.blend")
EXP = os.path.join(ROOT, "export")
ANIM_DIR = os.path.join(EXP, "animations")
BASE_NAME = "ASTRA_R08.fbx"
ARMATURE = "ASTRA_R08"
MESHES = ["ASTRA_R08_Body", "ASTRA_R08_Head", "ASTRA_R08_Eyes"]
STUD = 0.28

addon_utils.enable("io_scene_fbx")
import game_anim as GA                      # noqa: E402  (clip list and set_clip)
from io_scene_fbx import export_fbx_bin as _EFB, fbx_utils as _FU      # noqa: E402

# Blender writes each bone's default transform (the "Lcl" values of its Model) from the pose at
# the frame the scene is on.  In a file holding only a skeleton and its animation there is no bind
# pose, so readers take those defaults for the rest pose - and a clip that does not start at rest
# (Idle, Walk, Run) would then be read relative to its own first frame.  Write the true rest pose
# there instead; the animation curves (absolute local transforms) are untouched.
_FORCE_REST = [False]
_orig_tx = _FU.ObjectWrapper.fbx_object_tx
_orig_obj = _EFB.fbx_data_object_elements


def _tx(self, scene_data, rest=False, rot_euler_compat=None):
    if _FORCE_REST[0] and self._tag == "BO":
        rest = True
    return _orig_tx(self, scene_data, rest=rest, rot_euler_compat=rot_euler_compat)


def _obj(root, ob_obj, scene_data):
    _FORCE_REST[0] = True
    try:
        return _orig_obj(root, ob_obj, scene_data)
    finally:
        _FORCE_REST[0] = False


_FU.ObjectWrapper.fbx_object_tx = _tx
_EFB.fbx_data_object_elements = _obj

# Settings from Roblox's Blender export guide (Creator Hub, art/blender.md): Path Mode "Copy", Embed
# Textures on, Apply Scalings "FBX Unit Scale", Forward "Z Forward", Up "Y Up", Add Leaf Bones off,
# Bake Animation only for animation files.  (Blender's own default, -Z Forward, would leave the
# creature facing away from Roblox's front.)
COMMON = dict(check_existing=False, use_selection=True, global_scale=1.0, apply_unit_scale=True,
              apply_scale_options="FBX_SCALE_UNITS", use_space_transform=True, bake_space_transform=False,
              use_mesh_modifiers=False, mesh_smooth_type="FACE", use_tspace=True, use_triangles=True,
              use_custom_props=False, add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
              use_armature_deform_only=False, armature_nodetype="NULL", axis_forward="Z", axis_up="Y",
              use_metadata=True, colors_type="NONE")

# Roblox's published limits for imported skinned meshes (Creator Hub modelling and export
# requirements, read for this build): one mesh at most 20,000 triangles; closed (watertight) meshes;
# at most 4 bone influences per vertex; the root bone at the origin and not skinned; no leaf bones;
# one UV set inside 0..1; one material per mesh; colour and normal maps 24-bit RGB (normal map:
# OpenGL tangent space), roughness / metalness 8-bit single channel, 1024 x 1024 for a character;
# one animation per FBX file.
LIMITS = dict(max_tris_per_mesh=20000, max_influences=4, texture_px=1024)


def log(*a):
    print("[game_export]", *a, flush=True)


# ------------------------------------------------------------------------------- export

def select_only(objs):
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def export_all(game=GAME):
    bpy.ops.wm.open_mainfile(filepath=game)
    sc = bpy.context.scene
    ao = bpy.data.objects[ARMATURE]
    meshes = [bpy.data.objects[n] for n in MESHES]
    os.makedirs(ANIM_DIR, exist_ok=True)
    GA.set_clip(ao, None)
    sc.frame_set(0)
    select_only([ao] + meshes)
    base = os.path.join(EXP, BASE_NAME)
    bpy.ops.export_scene.fbx(filepath=base, object_types={"ARMATURE", "MESH"}, bake_anim=False, path_mode="COPY",
                             embed_textures=True, **COMMON)
    files = dict(base=base, clips={})
    scene_name = sc.name
    for (name, secs, loop, fn) in GA.CLIPS:
        GA.set_clip(ao, name)
        sc.frame_set(sc.frame_start)
        sc.name = name                      # the exporter names the file's one animation take after the scene
        select_only([ao])
        p = os.path.join(ANIM_DIR, f"ASTRA_R08_{name}.fbx")
        bpy.ops.export_scene.fbx(filepath=p, object_types={"ARMATURE"}, bake_anim=True, bake_anim_use_all_bones=True,
                                 bake_anim_use_nla_strips=False, bake_anim_use_all_actions=False,
                                 bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
                                 path_mode="AUTO", embed_textures=False, **COMMON)
        files["clips"][name] = p
    sc.name = scene_name
    GA.set_clip(ao, None)
    for k, p in [("base", base)] + list(files["clips"].items()):
        log(f"   wrote {os.path.relpath(p, ROOT)}  ({os.path.getsize(p) / 1e6:.2f} MB)")
    return files


# ------------------------------------------------------------------------------- the source, as a reference

def world_verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = oe.to_mesh()
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    M = np.array(oe.matrix_world)
    oe.to_mesh_clear()
    co = co.reshape(-1, 3)
    return co @ M[:3, :3].T + M[:3, 3]


def mesh_weights(ob):
    """(n, bones) dense weights by bone name order of the vertex groups, plus the names."""
    names = [vg.name for vg in ob.vertex_groups]
    W = np.zeros((len(ob.data.vertices), len(names)))
    for v in ob.data.vertices:
        for g in v.groups:
            W[v.index, g.group] = g.weight
    return W, names


def test_frames(n_last):
    return sorted({0, n_last // 3, (2 * n_last) // 3, n_last})


def reference(game=GAME):
    """Everything the re-imports are compared with, from the .blend."""
    bpy.ops.wm.open_mainfile(filepath=game)
    sc = bpy.context.scene
    ao = bpy.data.objects[ARMATURE]
    GA.set_clip(ao, None)
    sc.frame_set(0)
    R = dict(bones={}, meshes={}, poses={})
    for b in ao.data.bones:
        R["bones"][b.name] = dict(parent=b.parent.name if b.parent else None, head=np.array(b.head_local), tail=np.array(b.tail_local))
    for n in MESHES:
        ob = bpy.data.objects[n]
        me = ob.data
        W, names = mesh_weights(ob)
        uv = np.zeros(len(me.loops) * 2)
        me.uv_layers.active.data.foreach_get("uv", uv)
        R["meshes"][n] = dict(V=world_verts(ob), tris=sum(len(p.vertices) - 2 for p in me.polygons), W=W, wnames=names,
                              uv=uv.reshape(-1, 2), materials=[m.name for m in me.materials])
    for (name, secs, loop, fn) in GA.CLIPS:
        GA.set_clip(ao, name)
        n_last = int(bpy.data.actions[name].frame_range[1])
        R["poses"][name] = {}
        for f in test_frames(n_last):
            sc.frame_set(f)
            R["poses"][name][f] = {n: world_verts(bpy.data.objects[n]) for n in MESHES}
    GA.set_clip(ao, None)
    return R


# ------------------------------------------------------------------------------- 1. raw FBX structure

def _name(b):
    return b.split(b"\x00\x01")[0].decode("utf-8", "replace") if isinstance(b, bytes) else str(b)


def fbx_structure(path):
    from io_scene_fbx import parse_fbx
    root, version = parse_fbx.parse(path)
    top = {e.id: e for e in root.elems}
    out = dict(file=os.path.relpath(path, ROOT), bytes=os.path.getsize(path), fbx_version=version)
    gs = {}
    for e in top[b"GlobalSettings"].elems:
        if e.id == b"Properties70":
            for p in e.elems:
                gs[_name(p.props[0])] = p.props[4] if len(p.props) > 4 else None
    out["global_settings"] = {k: gs.get(k) for k in ("UpAxis", "UpAxisSign", "FrontAxis", "FrontAxisSign", "CoordAxis",
                                                     "CoordAxisSign", "UnitScaleFactor", "OriginalUnitScaleFactor",
                                                     "TimeMode", "CustomFrameRate")}
    objs = {}
    for e in top[b"Objects"].elems:
        objs[e.props[0]] = e
    conns = [(c.props[1], c.props[2]) for c in top[b"Connections"].elems if c.id == b"C"]
    parent_of = {}
    children = {}
    for (c, p) in conns:
        parent_of.setdefault(c, []).append(p)
        children.setdefault(p, []).append(c)

    def kind(e):
        return e.id.decode(), (e.props[2].decode() if len(e.props) > 2 and isinstance(e.props[2], bytes) else "")

    geoms, models, skins, clusters, videos, stacks, curves = {}, {}, {}, {}, [], [], []
    for oid, e in objs.items():
        k, t = kind(e)
        if k == "Geometry" and t == "Mesh":
            geoms[oid] = e
        elif k == "Model":
            models[oid] = (t, _name(e.props[1]))
        elif k == "Deformer" and t == "Skin":
            skins[oid] = e
        elif k == "Deformer" and t == "Cluster":
            clusters[oid] = e
        elif k == "Video":
            videos.append(e)
        elif k == "AnimationStack":
            stacks.append(_name(e.props[1]))
        elif k == "AnimationCurve":
            curves.append(e)
    out["models"] = {t: sorted(n for (tt, n) in models.values() if tt == t) for t in sorted({t for (t, n) in models.values()})}
    # meshes: triangles, closedness, skin
    meshes = {}
    for gid, g in geoms.items():
        sub = {c.id: c for c in g.elems}
        pvi = np.asarray(sub[b"PolygonVertexIndex"].props[0], np.int64)
        nverts = len(sub[b"Vertices"].props[0]) // 3
        ends = np.nonzero(pvi < 0)[0]
        sizes = np.diff(np.concatenate([[-1], ends]))
        idx = np.where(pvi < 0, -pvi - 1, pvi)
        edges = {}
        start = 0
        for s in sizes:
            f = idx[start:start + s]
            for j in range(s):
                a, b = int(f[j]), int(f[(j + 1) % s])
                edges[(a, b)] = edges.get((a, b), 0) + 1
            start += s
        open_e = sum(1 for (a, b), n in edges.items() if (b, a) not in edges)
        multi = sum(1 for n in edges.values() if n > 1)
        model = [models[p][1] for p in parent_of.get(gid, []) if p in models]
        uvsets = [c for c in g.elems if c.id == b"LayerElementUV"]
        uvmin, uvmax = None, None
        for c in uvsets:
            for cc in c.elems:
                if cc.id == b"UV":
                    a = np.asarray(cc.props[0]).reshape(-1, 2)
                    uvmin, uvmax = a.min(0).round(4).tolist(), a.max(0).round(4).tolist()
        info = dict(model=model[0] if model else None, vertices=nverts, polygons=int(len(sizes)),
                    triangles=int((sizes - 2).sum()), max_polygon_sides=int(sizes.max()),
                    open_edges=open_e, repeated_directed_edges=multi, uv_sets=len(uvsets), uv_min=uvmin, uv_max=uvmax)
        # skin: clusters of this geometry
        sk = [s for s in children.get(gid, []) if s in skins]
        infl = np.zeros(nverts, np.int32)
        wsum = np.zeros(nverts)
        bones = []
        for s in sk:
            for cid in children.get(s, []):
                if cid not in clusters:
                    continue
                c = {x.id: x for x in clusters[cid].elems}
                bone = [models[m][1] for m in children.get(cid, []) if m in models]
                if b"Indexes" in c:
                    ii = np.asarray(c[b"Indexes"].props[0], np.int64)
                    ww = np.asarray(c[b"Weights"].props[0], float)
                    np.add.at(infl, ii[ww > 0], 1)
                    np.add.at(wsum, ii, ww)
                    bones.append((bone[0] if bone else "?", int((ww > 0).sum())))
        info["skin_clusters"] = len(bones)
        info["bones_with_weights"] = sorted(b for b, n in bones if n > 0)
        info["max_influences"] = int(infl.max()) if len(infl) else 0
        info["unweighted_vertices"] = int((wsum <= 1e-6).sum())
        info["weight_sum_range"] = [round(float(wsum.min()), 5), round(float(wsum.max()), 5)]
        meshes[info["model"] or str(gid)] = info
    out["meshes"] = meshes
    # which way the creature faces in the file's own coordinates: where the head mesh lies relative to
    # the body mesh, horizontally, after each mesh's own Lcl transform (Euler XYZ, degrees)
    from scipy.spatial.transform import Rotation as _R

    def model_tx(mid):
        e = objs[mid]
        t, r, sc_ = np.zeros(3), np.zeros(3), np.ones(3)
        for c in e.elems:
            if c.id == b"Properties70":
                for p in c.elems:
                    nm = _name(p.props[0])
                    if nm == "Lcl Translation":
                        t = np.array(p.props[4:7], float)
                    elif nm == "Lcl Rotation":
                        r = np.array(p.props[4:7], float)
                    elif nm == "Lcl Scaling":
                        sc_ = np.array(p.props[4:7], float)
        return t, _R.from_euler("xyz", r, degrees=True).as_matrix(), sc_
    cents = {}
    for gid, g in geoms.items():
        mids = [p for p in parent_of.get(gid, []) if p in models]
        if not mids:
            continue
        V = np.asarray({c.id: c for c in g.elems}[b"Vertices"].props[0], float).reshape(-1, 3)
        t, Rm, sc_ = model_tx(mids[0])
        W = (V * sc_) @ Rm.T + t
        cents[models[mids[0]][1]] = W.mean(0)
    if "ASTRA_R08_Head" in cents and "ASTRA_R08_Body" in cents:
        dv = cents["ASTRA_R08_Head"] - cents["ASTRA_R08_Body"]
        up = np.array([0.0, 1.0, 0.0]) if gs.get("UpAxis") == 1 else np.array([0.0, 0.0, 1.0])
        hz = dv - (dv @ up) * up
        out["facing"] = dict(head_from_body=(hz / max(np.linalg.norm(hz), 1e-9)).round(3).tolist(),
                             head_above_body=round(float(dv @ up), 3))
    # embedded images
    from PIL import Image
    ims = []
    for v in videos:
        sub = {c.id: c for c in v.elems}
        name = _name(v.props[1])
        d = dict(name=name, file=os.path.basename(_name(sub[b"RelativeFilename"].props[0])) if b"RelativeFilename" in sub else None)
        content = sub.get(b"Content")
        data = content.props[0] if content is not None and content.props else b""
        d["embedded_bytes"] = len(data) if isinstance(data, (bytes, bytearray)) else 0
        if d["embedded_bytes"]:
            im = Image.open(io.BytesIO(bytes(data)))
            d.update(format=im.format, size=list(im.size), mode=im.mode)
        ims.append(d)
    out["embedded_images"] = sorted(ims, key=lambda d: d["name"])
    out["animation_stacks"] = stacks
    if curves:
        kt = [len(c.elems[[x.id for x in c.elems].index(b"KeyTime")].props[0]) for c in curves if b"KeyTime" in [x.id for x in c.elems]]
        out["animation_curves"] = dict(count=len(curves), keys_per_curve=[int(min(kt)), int(max(kt))])
    return out


# ------------------------------------------------------------------------------- 2./3. re-import

IMPORTERS = {
    "python": lambda p: bpy.ops.import_scene.fbx(filepath=p, use_anim=True, anim_offset=0.0, ignore_leaf_bones=False,
                                                 automatic_bone_orientation=False, primary_bone_axis="Y",
                                                 secondary_bone_axis="X", use_image_search=False, use_custom_normals=True),
    "ufbx": lambda p: bpy.ops.wm.fbx_import(filepath=p, use_anim=True, anim_offset=0.0, ignore_leaf_bones=False,
                                            use_custom_normals=True),
}


def do_import(which, path):
    before = set(bpy.data.objects)
    acts_before = set(bpy.data.actions)
    IMPORTERS[which](path)
    new = [o for o in bpy.data.objects if o not in before]
    acts = [a for a in bpy.data.actions if a not in acts_before]
    return new, acts


def find_mesh(objs, name):
    for o in objs:
        if o.type == "MESH" and (o.name == name or o.name.startswith(name + ".") or o.data.name.startswith(name)):
            return o
    return None


def verify_importer(which, files, R):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("io_scene_fbx")
    res = dict(importer=which)
    t = time.time()
    objs, _ = do_import(which, files["base"])
    arms = [o for o in objs if o.type == "ARMATURE"]
    res["objects"] = sorted(f"{o.type}:{o.name}" for o in objs)
    if len(arms) != 1:
        res["error"] = f"expected one armature, found {len(arms)}"
        return res
    arm = arms[0]
    bpy.context.view_layer.update()
    # skeleton
    bones = {b.name: b for b in arm.data.bones}
    res["bones"] = len(bones)
    res["bone_names_match"] = sorted(bones) == sorted(R["bones"])
    res["hierarchy_match"] = all((bones[n].parent.name if bones[n].parent else None) == R["bones"][n]["parent"] for n in R["bones"] if n in bones)
    Mw = np.array(arm.matrix_world)
    heads = np.array([Mw[:3, :3] @ np.array(bones[n].head_local) + Mw[:3, 3] for n in R["bones"] if n in bones])
    src_heads = np.array([R["bones"][n]["head"] for n in R["bones"] if n in bones])
    # imported units / scale: the ratio of the two skeletons (should be a plain unit conversion)
    k = float(np.linalg.norm(heads - heads.mean(0), axis=1).sum() / np.linalg.norm(src_heads - src_heads.mean(0), axis=1).sum())
    res["scale_to_source"] = round(k, 6)
    res["bone_head_error_studs"] = float(np.abs(heads / k - src_heads).max())
    res["root_bone_at_origin"] = bool(np.linalg.norm(heads[list(R["bones"]).index("Root")]) < 1e-5)
    # meshes
    res["meshes"] = {}
    imported = {}
    for n in MESHES:
        ob = find_mesh(objs, n)
        if ob is None:
            res["meshes"][n] = dict(error="missing")
            continue
        imported[n] = ob
        me = ob.data
        src = R["meshes"][n]
        V = world_verts(ob) / k
        d = dict(vertices=len(me.vertices), source_vertices=len(src["V"]),
                 triangles=sum(len(p.vertices) - 2 for p in me.polygons), source_triangles=src["tris"],
                 uv_layers=len(me.uv_layers), materials=[m.name for m in me.materials if m])
        same_order = len(V) == len(src["V"]) and float(np.abs(V - src["V"]).max()) < 1e-3
        d["vertex_order_preserved"] = bool(same_order)
        if same_order:
            d["rest_position_error_studs"] = float(np.abs(V - src["V"]).max())
        else:
            from scipy.spatial import cKDTree
            dd, _ = cKDTree(src["V"]).query(V)
            d["rest_position_error_studs"] = float(dd.max())
        if me.uv_layers:
            uv = np.zeros(len(me.loops) * 2)
            me.uv_layers[0].data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            d["uv_range"] = [uv.min(0).round(4).tolist(), uv.max(0).round(4).tolist()]
            if len(uv) == len(src["uv"]):
                d["uv_error"] = float(np.abs(uv - src["uv"]).max())
        # weights
        W, names = mesh_weights(ob)
        if same_order:
            Ws, ns = src["W"], src["wnames"]
            err = 0.0
            for j, nm in enumerate(ns):
                if nm in names:
                    err = max(err, float(np.abs(W[:, names.index(nm)] - Ws[:, j]).max()))
                elif Ws[:, j].max() > 0:
                    err = max(err, float(Ws[:, j].max()))
            d["weight_error"] = err
        cnt = (W > 1e-6).sum(1)
        d["max_influences"] = int(cnt.max()) if len(cnt) else 0
        d["weight_on_root"] = float(W[:, names.index("Root")].sum()) if "Root" in names else 0.0
        # material and its images
        mats = []
        for m in me.materials:
            if not m or not m.node_tree:
                continue
            imgs = []
            for nd in m.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image:
                    im = nd.image
                    links = [l.to_socket.name + "@" + l.to_node.name for l in nd.outputs[0].links] if nd.outputs[0].links else []
                    imgs.append(dict(image=im.name, size=list(im.size), packed=im.packed_file is not None, feeds=links))
            mats.append(dict(name=m.name, images=imgs))
        d["material_images"] = mats
        res["meshes"][n] = d
    res["import_seconds"] = round(time.time() - t, 2)
    # animations: each clip from its own file, played on the re-imported rig
    res["clips"] = {}
    for (name, secs, loop, fn) in GA.CLIPS:
        p = files["clips"][name]
        new, acts = do_import(which, p)
        c = dict(file=os.path.relpath(p, ROOT), actions_created=len(acts))
        if not acts:
            c["error"] = "no animation read"
            res["clips"][name] = c
            for o in new:
                bpy.data.objects.remove(o)
            continue
        act = acts[0]
        c["frame_range"] = [round(float(act.frame_range[0]), 3), round(float(act.frame_range[1]), 3)]
        if arm.animation_data is None:
            arm.animation_data_create()
        arm.animation_data.action = act
        try:
            if arm.animation_data.action_slot is None and len(act.slots):
                arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
        worst = 0.0
        per_frame = {}
        for f, ref in R["poses"][name].items():
            bpy.context.scene.frame_set(int(f))
            e = 0.0
            for n, ob in imported.items():
                V = world_verts(ob) / k
                if len(V) == len(ref[n]):
                    e = max(e, float(np.linalg.norm(V - ref[n], axis=1).max()))
            per_frame[int(f)] = round(e, 5)
            worst = max(worst, e)
        c["deformation_error_studs"] = per_frame
        c["max_error_studs"] = round(worst, 5)
        c["max_error_mm"] = round(worst * STUD * 1000, 2)
        res["clips"][name] = c
        arm.animation_data.action = None
        for o in new:
            bpy.data.objects.remove(o)
    return res


# ------------------------------------------------------------------------------- Roblox requirements

def conformance(struct_base, struct_clips, imports):
    checks = []

    def chk(name, ok, detail):
        checks.append(dict(check=name, passed=bool(ok), detail=detail))

    ms = struct_base["meshes"]
    for n, d in ms.items():
        chk(f"{n}: triangles <= {LIMITS['max_tris_per_mesh']}", d["triangles"] <= LIMITS["max_tris_per_mesh"], d["triangles"])
        chk(f"{n}: closed (no open edges, no doubled edges)", d["open_edges"] == 0 and d["repeated_directed_edges"] == 0,
            dict(open_edges=d["open_edges"], doubled=d["repeated_directed_edges"]))
        chk(f"{n}: triangles only", d["max_polygon_sides"] == 3, d["max_polygon_sides"])
        chk(f"{n}: one UV set inside 0..1", d["uv_sets"] == 1 and min(d["uv_min"]) >= 0 and max(d["uv_max"]) <= 1,
            dict(sets=d["uv_sets"], min=d["uv_min"], max=d["uv_max"]))
        chk(f"{n}: at most {LIMITS['max_influences']} bones per vertex", d["max_influences"] <= LIMITS["max_influences"], d["max_influences"])
        chk(f"{n}: every vertex weighted, weights sum to 1", d["unweighted_vertices"] == 0 and abs(d["weight_sum_range"][0] - 1) < 1e-3
            and abs(d["weight_sum_range"][1] - 1) < 1e-3, dict(unweighted=d["unweighted_vertices"], sums=d["weight_sum_range"]))
        chk(f"{n}: Root bone carries no weight", "Root" not in d["bones_with_weights"], d["bones_with_weights"])
    limbs = struct_base["models"].get("LimbNode", [])
    chk("skeleton: 27 bones, no leaf bones", len(limbs) == 27 and not any(b.endswith("_end") for b in limbs), len(limbs))
    py = imports.get("python", {})
    chk("skeleton: Root bone at the origin", py.get("root_bone_at_origin", False), py.get("root_bone_at_origin"))
    ims = struct_base["embedded_images"]
    for d in ims:
        nm = d["name"]
        want = "L" if ("Roughness" in nm or "Metalness" in nm) else "RGB"
        chk(f"texture {d.get('file') or nm}: embedded, {LIMITS['texture_px']} px, {want}",
            d["embedded_bytes"] > 0 and d.get("size") == [LIMITS["texture_px"]] * 2 and d.get("mode") == want,
            dict(bytes=d["embedded_bytes"], size=d.get("size"), mode=d.get("mode"), format=d.get("format")))
    for n in ("ASTRA_R08_Body", "ASTRA_R08_Head"):
        mats = py.get("meshes", {}).get(n, {}).get("materials", [])
        chk(f"{n}: one material", len(mats) == 1, mats)
    gsd = struct_base["global_settings"]
    chk("axis system: Y up (Roblox's Blender guide: Z Forward, Y Up)", gsd["UpAxis"] == 1 and gsd["UpAxisSign"] == 1, gsd)
    fz = struct_base.get("facing")
    chk("facing: in the file's own frame the creature faces -Z (Roblox's front) with Y up",
        fz is not None and fz["head_from_body"][2] < -0.9, fz)
    for name, s in struct_clips.items():
        chk(f"animation {name}: exactly one animation in the file, named {name}", s["animation_stacks"] == [name], s["animation_stacks"])
        gsc = s["global_settings"]
        chk(f"animation {name}: 30 frames per second", abs((gsc.get("CustomFrameRate") or 0) - 30.0) < 1e-6 or gsc.get("TimeMode") == 6,
            dict(TimeMode=gsc.get("TimeMode"), fps=gsc.get("CustomFrameRate")))
    for which, r in imports.items():
        if "error" in r:
            chk(f"{which} importer: reads the character", False, r["error"])
            continue
        chk(f"{which} importer: skeleton matches (names, parents, joint positions)",
            r["bone_names_match"] and r["hierarchy_match"] and r["bone_head_error_studs"] < 1e-3,
            dict(bones=r["bones"], head_error_studs=r["bone_head_error_studs"]))
        for n, d in r["meshes"].items():
            if "error" in d:
                chk(f"{which} importer: {n}", False, d["error"])
                continue
            chk(f"{which} importer: {n} geometry, UVs and weights match the source",
                d["vertices"] == d["source_vertices"] and d["triangles"] == d["source_triangles"] and d["rest_position_error_studs"] < 1e-3
                and d.get("weight_error", 0.0) < 1e-3,
                dict(vertices=d["vertices"], triangles=d["triangles"], pos_err=d["rest_position_error_studs"], weight_err=d.get("weight_error")))
        for name, c in r["clips"].items():
            chk(f"{which} importer: {name} plays back on the re-imported rig like the source",
                "error" not in c and c["max_error_studs"] < 0.01, c.get("max_error_mm", c.get("error")))
    return checks


def write_report(V):
    lines = ["# FBX verification - ASTRA R08 Experimental Model 02", "",
             "Generated by `src/game_export.py`.  Every number below is measured on the files in `export/`.", ""]
    s = V["structure"]["base"]
    gs = s["global_settings"]
    lines += ["## The character file", "",
              f"`export/{BASE_NAME}` - {s['bytes'] / 1e6:.2f} MB, FBX {s['fbx_version']}, binary.  Axis system: up = "
              f"{'XYZ'[gs['UpAxis']]}, front = {'XYZ'[gs['FrontAxis']]}; unit scale factor {gs['UnitScaleFactor']} "
              f"(one file unit = one stud = 0.28 m; the creature is {V['height_studs']} units tall).", "",
              "| Mesh | Triangles | Vertices | Open edges | UV sets | UV range | Max bones / vertex | Bones used |",
              "|---|---|---|---|---|---|---|---|"]
    for n, d in s["meshes"].items():
        lines.append(f"| {n} | {d['triangles']:,} | {d['vertices']:,} | {d['open_edges']} | {d['uv_sets']} | "
                     f"{d['uv_min']} - {d['uv_max']} | {d['max_influences']} | {len(d['bones_with_weights'])} |")
    lines += ["", "Embedded images (decoded from the bytes inside the FBX):", "", "| Image | Size | Channels | Bytes |", "|---|---|---|---|"]
    for d in s["embedded_images"]:
        lines.append(f"| {d.get('file') or d['name']} | {d.get('size')} | {d.get('mode')} | {d['embedded_bytes']:,} |")
    lines += ["", "## Round trip through two FBX importers", "",
              "Each importer reads the character file into an empty scene; each clip is then read from its own file and "
              "played on that re-imported rig.  Deformation error = the largest distance between a re-imported vertex "
              "and the same vertex of the source model in the same frame (start, one third, two thirds, end of each clip).", ""]
    for which, r in V["imports"].items():
        lines.append(f"### {which} importer" if which != "ufbx" else "### C++ importer (ufbx)")
        lines.append("")
        if "error" in r:
            lines += [f"Failed: {r['error']}", ""]
            continue
        lines.append(f"Skeleton: {r['bones']} bones, names and parents {'identical' if r['bone_names_match'] and r['hierarchy_match'] else 'DIFFERENT'}, "
                     f"joint positions within {r['bone_head_error_studs']:.2e} studs.  Scale on import: x{r['scale_to_source']}.")
        lines.append("")
        lines.append("| Mesh | Vertices | Triangles | Rest position error (studs) | Weight error | Max bones / vertex | Material |")
        lines.append("|---|---|---|---|---|---|---|")
        for n, d in r["meshes"].items():
            if "error" in d:
                lines.append(f"| {n} | {d['error']} | | | | | |")
                continue
            lines.append(f"| {n} | {d['vertices']:,} | {d['triangles']:,} | {d['rest_position_error_studs']:.1e} | "
                         f"{d.get('weight_error', float('nan')):.1e} | {d['max_influences']} | {', '.join(d['materials'])} |")
        lines += ["", "| Clip | Frames read | Largest deformation error |", "|---|---|---|"]
        for name, c in r["clips"].items():
            if "error" in c:
                lines.append(f"| {name} | {c['error']} | |")
            else:
                lines.append(f"| {name} | {c['frame_range'][0]:.0f}-{c['frame_range'][1]:.0f} | {c['max_error_mm']} mm |")
        lines.append("")
    lines += ["## Roblox import requirements", "",
              f"{sum(c['passed'] for c in V['checks'])} of {len(V['checks'])} checks passed.", "",
              "| Check | Result | Detail |", "|---|---|---|"]
    for c in V["checks"]:
        det = json.dumps(c["detail"]) if not isinstance(c["detail"], str) else c["detail"]
        lines.append(f"| {c['check']} | {'pass' if c['passed'] else '**FAIL**'} | {det[:140]} |")
    lines += ["", "## Not tested here", "",
              "Roblox Studio does not run in this build's Linux container, so the files have not been opened in "
              "Studio's 3D Importer or Animation Editor.  The checks above cover what Roblox's documentation asks of "
              "an FBX; `docs/ROBLOX_IMPORT.md` lists the import steps and what to look at once the character is in Studio.", ""]
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    open(os.path.join(ROOT, "docs", "FBX_VERIFICATION.md"), "w").write("\n".join(lines))


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, bytes):
        return o.decode("utf-8", "replace")
    return o


def main(game=GAME):
    t0 = time.time()
    files = export_all(game)
    log(f"exported ({time.time() - t0:.1f} s)")
    R = reference(game)
    hs = R["meshes"]["ASTRA_R08_Body"]["V"][:, 2]
    hh = R["meshes"]["ASTRA_R08_Head"]["V"][:, 2]
    height = float(max(hs.max(), hh.max()) - min(hs.min(), hh.min()))
    struct_base = fbx_structure(files["base"])
    struct_clips = {n: fbx_structure(p) for n, p in files["clips"].items()}
    log(f"structure read ({time.time() - t0:.1f} s)")
    imports = {}
    for which in ("python", "ufbx"):
        try:
            imports[which] = verify_importer(which, files, R)
        except Exception as e:                       # an importer that cannot read the file is a finding, not a crash
            import traceback
            imports[which] = dict(importer=which, error=f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1500:])
        log(f"{which} importer checked ({time.time() - t0:.1f} s)")
    checks = conformance(struct_base, struct_clips, imports)
    V = dict(files={k: (os.path.relpath(v, ROOT) if isinstance(v, str) else {kk: os.path.relpath(vv, ROOT) for kk, vv in v.items()})
                    for k, v in files.items()},
             height_studs=round(height, 3), structure=dict(base=struct_base, clips=struct_clips), imports=imports, checks=checks)
    json.dump(_jsonable(V), open(os.path.join(ROOT, "analysis", "fbx_verification.json"), "w"), indent=1)
    write_report(V)
    npass = sum(c["passed"] for c in checks)
    log(f"{npass} of {len(checks)} checks passed ({time.time() - t0:.1f} s)")
    for c in checks:
        if not c["passed"]:
            log("   FAILED:", c["check"], json.dumps(_jsonable(c["detail"]))[:300])


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(*args[:1])
