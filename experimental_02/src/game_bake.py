"""ASTRA R08 - Experimental Model 02: texture maps for the game meshes (stage 2 of the Roblox build).

    bvenv/bin/python experimental_02/src/game_bake.py [stage1.blend] [out.blend]
    env: BAKE_RES (default 2048), BAKE_ONLY (Body / Head), BAKE_PASSES (comma list),
         COMPOSE_ONLY=1 (no baking: put the maps together again from the raw passes of an earlier bake)

Everything the high-detail model shows - every plate, crack, pit, wound and tooth groove - is
projected onto the game meshes' UV maps by ray (Cycles "selected to active" with a cage that
stands off each vertex by its own distance: 3 cm on the armour, half a centimetre on a tooth).

Per mesh, in textures/ :
    <Mesh>_Color.png       base colour (sRGB, 24-bit) with part of the ambient shadow multiplied in
    <Mesh>_Normal.png      tangent-space normal map, OpenGL convention (+Y up), 24-bit
    <Mesh>_Roughness.png   8-bit grey
    <Mesh>_Metalness.png   8-bit grey
and in textures/source/ the 2048-pixel masters plus the unmixed albedo and ambient-occlusion maps.
The Roblox set is 1024 x 1024 (Roblox's texture size for a character part).
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HIGH = os.path.join(ROOT, "model", "astra_r08_exp02_highdetail.blend")
STAGE1 = os.path.join(ROOT, "model", "work", "game_stage1.blend")
STAGE2 = os.path.join(ROOT, "model", "work", "game_stage2.blend")
TEX = os.path.join(ROOT, "textures")
SRC = os.path.join(TEX, "source")
RAW = os.path.join(ROOT, "model", "work", "bake")      # the raw baked passes (intermediate, not kept in git)
RES = int(os.environ.get("BAKE_RES", "2048"))
GAME_RES = 1024
AO_MIX = 0.55            # share of the baked ambient shadow multiplied into the colour map

TARGETS = {
    "Body": dict(object="ASTRA_R08_Body", sources=["R08_body_plates", "R08_body_under", "R08_body_muscle", "R08_body_rods"]),
    # the teeth are baked a second time from the teeth and gums alone: a tooth that stands in the dark
    # masses of the throat must not pick up their black where a ray slips past its own surface
    "Head": dict(object="ASTRA_R08_Head", sources=["R08_head_plates", "R08_head_under", "R08_head_muscle", "R08_head_rods",
                                                   "R08_head_gums", "R08_head_teeth", "R08_head_mouth"],
                 sources2=["R08_head_teeth", "R08_head_gums"], regions2=(2, 3)),
}
PASSES = ["albedo", "roughness", "normal", "ao", "metal", "region"]
JOINT_TEXELS = {}
REGION_STEP = 16.0 / 255.0          # the region map stores region number x 16 as a grey level


def log(*a):
    print("[game_bake]", *a, flush=True)


def select(active, others=()):
    bpy.context.view_layer.update()
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in others:
        o.select_set(True)
    active.select_set(True)
    bpy.context.view_layer.objects.active = active


def cage_of(ob):
    """A copy of the mesh with every vertex pushed out along its normal by its own stand-off."""
    me = ob.data.copy()
    n = len(me.vertices)
    co = np.zeros(n * 3)
    no = np.zeros(n * 3)
    d = np.zeros(n)
    me.vertices.foreach_get("co", co)
    me.vertices.foreach_get("normal", no)
    me.attributes["cage"].data.foreach_get("value", d)
    me.vertices.foreach_set("co", (co.reshape(-1, 3) + no.reshape(-1, 3) * d[:, None]).reshape(-1))
    me.update()
    c = bpy.data.objects.new(ob.name + "_cage", me)
    bpy.context.scene.collection.objects.link(c)
    return c


def bake_material(ob, image):
    """A material on the target whose only job is to name the image being baked into."""
    mat = bpy.data.materials.get("BakeTarget") or bpy.data.materials.new("BakeTarget")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    # metalness of the game mesh itself (rods are bare iron under the rust, the rest is oxide)
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "region"
    cmp_ = nt.nodes.new("ShaderNodeMath")
    cmp_.operation = "COMPARE"
    cmp_.inputs[1].default_value = 9.0
    cmp_.inputs[2].default_value = 0.1
    nt.links.new(at.outputs["Fac"], cmp_.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 0.30
    nt.links.new(cmp_.outputs[0], mul.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(mul.outputs[0], em.inputs["Color"])
    # the region number of each face, for the masks used when the maps are put together
    rg = nt.nodes.new("ShaderNodeMath")
    rg.operation = "MULTIPLY"
    rg.inputs[1].default_value = REGION_STEP
    nt.links.new(at.outputs["Fac"], rg.inputs[0])
    em2 = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(rg.outputs[0], em2.inputs["Color"])
    nt.nodes.active = tex
    tex.select = True
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return mat, em, out, em2


def new_image(name, data):
    im = bpy.data.images.get(name)
    if im is not None:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False, is_data=data)
    return im


def save(im, path):
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()


def bake_target(key, passes):
    sc = bpy.context.scene
    T = TARGETS[key]
    ob = bpy.data.objects[T["object"]]
    srcs = [bpy.data.objects[n] for n in T["sources"]]
    cage = cage_of(ob)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = False
    sc.render.bake.use_selected_to_active = True
    sc.render.bake.use_cage = True
    sc.render.bake.cage_object = cage
    sc.render.bake.max_ray_distance = 0.11
    sc.render.bake.margin = max(4, RES // 128)
    sc.render.bake.margin_type = "EXTEND"
    sc.render.bake.use_clear = True
    sc.render.bake.target = "IMAGE_TEXTURES"
    out = {}
    M = sc.render.bake.margin
    jobs = [(ps, "", srcs) for ps in passes]
    if T.get("sources2"):
        s2 = [bpy.data.objects[n] for n in T["sources2"]]
        jobs += [(ps, "_teeth", s2) for ps in passes if ps in ("albedo", "roughness", "normal", "ao")]
    for (ps, tag, src) in jobs:
        t = time.time()
        im = new_image(f"{key}_{ps}{tag}", data=(ps != "albedo"))
        mat, em, outn, em2 = bake_material(ob, im)
        nt = mat.node_tree
        kw = dict(use_selected_to_active=True, use_cage=True, cage_object=cage.name, max_ray_distance=0.11, margin=M)
        if ps == "albedo":
            sc.cycles.samples = 8
            select(ob, src)
            bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, **kw)
        elif ps == "roughness":
            sc.cycles.samples = 4
            select(ob, src)
            bpy.ops.object.bake(type="ROUGHNESS", **kw)
        elif ps == "normal":
            sc.cycles.samples = 8
            select(ob, src)
            bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z", **kw)
        elif ps == "ao":
            sc.cycles.samples = 40
            if sc.world is None:
                sc.world = bpy.data.worlds.new("BakeWorld")
            sc.world.light_settings.distance = 0.30
            select(ob, src)
            bpy.ops.object.bake(type="AO", **kw)
        elif ps in ("metal", "region"):
            sc.cycles.samples = 1
            nt.links.new((em if ps == "metal" else em2).outputs[0], outn.inputs[0])
            select(ob)
            bpy.ops.object.bake(type="EMIT", use_selected_to_active=False, margin=M)
        path = os.path.join(RAW, f"ASTRA_R08_{key}_{ps}{tag}_{RES}.png")
        save(im, path)
        out[ps + tag] = path
        log(f"   {key} {ps}{tag}: {time.time() - t:.1f} s")
    dm = cage.data
    bpy.data.objects.remove(cage)
    bpy.data.meshes.remove(dm)
    return out


def joint_texels(ob):
    """v2 body (armoured joints): the texels of the faces that lie inside a neighbouring piece at rest -
    the rounded knuckles and end caps that a bending joint turns into view - and which piece each
    texel belongs to.  Baked from inside another block, they caught the dark inner layers or nothing
    at all, and an ambient shadow of almost zero.  Returns (buried texels, piece of every texel) or
    None for a mesh without them."""
    from PIL import ImageDraw
    me = ob.data
    if "buried" not in me.attributes or "piece" not in me.attributes:
        return None
    n = len(me.vertices)
    bur, kn, pc = np.zeros(n), np.zeros(n), np.zeros(n, np.int32)
    me.attributes["buried"].data.foreach_get("value", bur)
    me.attributes["knuckle"].data.foreach_get("value", kn)
    me.attributes["piece"].data.foreach_get("value", pc)
    hidden = (bur > 0.5) | (kn > 0.5)
    uv = me.uv_layers.active.data
    imb, imv, imp = (Image.new(m, (RES, RES), 0) for m in ("L", "L", "I"))
    db, dv, dp = ImageDraw.Draw(imb), ImageDraw.Draw(imv), ImageDraw.Draw(imp)
    for p in me.polygons:
        pts = [(uv[i].uv[0] * RES, (1.0 - uv[i].uv[1]) * RES) for i in p.loop_indices]
        (db if hidden[list(p.vertices)].sum() >= 2 else dv).polygon(pts, fill=255)
        dp.polygon(pts, fill=int(pc[p.vertices[0]]) + 1)
    visible = np.asarray(imv) > 0
    buried = (np.asarray(imb) > 0) & ~visible
    piece = np.asarray(imp).astype(np.int32) - 1
    return buried, visible, piece


def refill_joints(maps, masks, margin):
    """Buried texels (and the bake margin round them) take the colour, roughness and ambient shadow of
    the nearest visible texel of the same piece, softened; their normal is flat - an exposed knuckle
    reads as the smooth rounded end of the plate."""
    from scipy import ndimage
    buried, visible, piece = masks
    near_b = ndimage.binary_dilation(buried, iterations=margin)
    target = near_b & ~visible
    # margin texels belong to the piece of the nearest drawn texel
    drawn = piece >= 0
    idx = ndimage.distance_transform_edt(~drawn, return_distances=False, return_indices=True)
    pid = piece[idx[0], idx[1]]
    filled = {k: v.copy() for k, v in maps.items()}
    for k in np.unique(pid[target]):
        src = visible & (piece == k)
        tg = target & (pid == k)
        if not src.any() or not tg.any():
            continue
        j = ndimage.distance_transform_edt(~src, return_distances=False, return_indices=True)
        for ps in ("albedo", "ao", "roughness"):
            filled[ps][tg] = maps[ps][j[0][tg], j[1][tg]]
    for ps in ("albedo", "ao", "roughness"):
        a = filled[ps].astype(np.float32)
        sig = (2.0, 2.0, 0) if a.ndim == 3 else 2.0
        b = ndimage.gaussian_filter(a, sigma=sig)
        a[target] = b[target]
        filled[ps] = (a + 0.5).clip(0, 255).astype(np.uint8)
    filled["normal"][target] = (128, 128, 255)
    return filled, int(target.sum())


def compose(key):
    """Masters -> the Roblox set: colour = albedo x part of the ambient shadow; 1024 px; 8-bit."""
    T = TARGETS[key]
    region = np.asarray(Image.open(os.path.join(RAW, f"ASTRA_R08_{key}_region_{RES}.png")).convert("L"), np.float32)
    region = np.round(region / 16.0).astype(np.int32)
    mask2 = np.isin(region, T.get("regions2", ()))

    def load(ps, mode):
        im = Image.open(os.path.join(RAW, f"ASTRA_R08_{key}_{ps}_{RES}.png")).convert(mode)
        p2 = os.path.join(RAW, f"ASTRA_R08_{key}_{ps}_teeth_{RES}.png")
        if mask2.any() and os.path.exists(p2):
            a, b = np.asarray(im).copy(), np.asarray(Image.open(p2).convert(mode))
            a[mask2] = b[mask2]
            im = Image.fromarray(a, mode)
        return im
    maps = {ps: np.asarray(load(ps, mode)).copy() for ps, mode in (("albedo", "RGB"), ("ao", "L"), ("normal", "RGB"), ("roughness", "L"))}
    # a few texels on the teeth catch nothing at all (a ray leaving past a tip): fill them from their neighbours
    if mask2.any():
        from scipy import ndimage
        hole = mask2 & (maps["albedo"].max(axis=2) < 16)
        if hole.any():
            idx = ndimage.distance_transform_edt(hole | ~mask2, return_distances=False, return_indices=True)
            for ps in maps:
                maps[ps][hole] = maps[ps][idx[0][hole], idx[1][hole]]
        log(f"   {key}: {int(hole.sum())} empty tooth texels filled")
    # v2 body: the knuckles and end caps buried in a neighbouring piece at rest
    masks = joint_texels(bpy.data.objects[T["object"]])
    JOINT_TEXELS[key] = 0
    if masks is not None:
        maps, JOINT_TEXELS[key] = refill_joints(maps, masks, max(4, RES // 128))
        log(f"   {key}: {JOINT_TEXELS[key]} texels of buried knuckles and end caps refilled from their own piece")
    load_ = load
    load = lambda ps, mode: Image.fromarray(maps[ps], mode) if ps in maps else load_(ps, mode)
    alb = maps["albedo"].astype(np.float32) / 255.0
    ao = maps["ao"].astype(np.float32) / 255.0
    col = alb * (1.0 - AO_MIX + AO_MIX * ao)[..., None]
    Image.fromarray((alb * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(SRC, f"ASTRA_R08_{key}_Albedo_{RES}.png"))
    Image.fromarray((ao * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(SRC, f"ASTRA_R08_{key}_AO_{RES}.png"))
    sets = {"Color": Image.fromarray((np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8), "RGB"),
            "Normal": load("normal", "RGB"), "Roughness": load("roughness", "L"), "Metalness": load("metal", "L")}
    files = {}
    for name, im in sets.items():
        im.save(os.path.join(SRC, f"ASTRA_R08_{key}_{name}_{RES}.png"))
        small = im.resize((GAME_RES, GAME_RES), Image.LANCZOS)
        if name == "Normal":           # averaged normals are shorter than 1: bring them back to length
            a = np.asarray(small, np.float32) / 127.5 - 1.0
            a /= np.maximum(np.linalg.norm(a, axis=2, keepdims=True), 1e-6)
            small = Image.fromarray(((a + 1.0) * 127.5 + 0.5).clip(0, 255).astype(np.uint8), "RGB")
        p = os.path.join(TEX, f"ASTRA_R08_{key}_{name}.png")
        small.save(p, optimize=True)
        files[name] = p
    return files


def game_material(key, files):
    """One material per mesh: the four maps on a Principled BSDF (what the FBX carries)."""
    mat = bpy.data.materials.new(f"ASTRA_R08_{key}")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.location = (200, 0)
    nt.links.new(b.outputs[0], out.inputs[0])

    def tex(name, y, data):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.location = (-420, y)
        n.image = bpy.data.images.load(files[name], check_existing=True)
        n.image.name = os.path.basename(files[name])
        n.image.colorspace_settings.name = "Non-Color" if data else "sRGB"
        n.label = name
        return n
    nt.links.new(tex("Color", 300, False).outputs["Color"], b.inputs["Base Color"])
    nt.links.new(tex("Metalness", 20, True).outputs["Color"], b.inputs["Metallic"])
    nt.links.new(tex("Roughness", -260, True).outputs["Color"], b.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.location = (-100, -540)
    nt.links.new(tex("Normal", -540, True).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = 0.3
    return mat


def eyes_material():
    mat = bpy.data.materials.new("ASTRA_R08_Eyes")
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (1.0, 0.06, 0.008, 1.0)
    b.inputs["Emission Color"].default_value = (1.0, 0.06, 0.008, 1.0)
    b.inputs["Emission Strength"].default_value = 4.0
    b.inputs["Roughness"].default_value = 0.5
    mat.diffuse_color = (1.0, 0.06, 0.008, 1.0)
    return mat


def main(stage1=STAGE1, out=STAGE2):
    t0 = time.time()
    os.makedirs(SRC, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=stage1)
    only = os.environ.get("BAKE_ONLY")
    passes = os.environ.get("BAKE_PASSES", ",".join(PASSES)).split(",")
    keys = [k for k in TARGETS if not only or k == only]
    if os.environ.get("COMPOSE_ONLY"):
        keys = []                     # the raw passes of an earlier bake are used as they are
    need = sorted({n for k in keys for n in TARGETS[k]["sources"]})
    with bpy.data.libraries.load(HIGH, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in need]
    coll = bpy.data.collections.new("HIGH")
    bpy.context.scene.collection.children.link(coll)
    for o in dst.objects:
        coll.objects.link(o)
    log(f"high-detail source appended: {sum(len(o.data.polygons) for o in dst.objects)} faces  ({time.time() - t0:.1f} s)")
    for k in keys:
        bake_target(k, passes)
    if set(passes) != set(PASSES):
        log("partial bake: raw passes written, no materials made")
        return
    # (BAKE_ONLY: the other mesh's raw passes from an earlier full bake are used as they are)
    for o in list(coll.objects):
        dm = o.data
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(dm)
    bpy.data.collections.remove(coll)
    for m_ in list(bpy.data.materials):
        if m_.users == 0 or m_.name == "BakeTarget":
            pass
    report = {}
    for k in TARGETS:
        files = compose(k)
        ob = bpy.data.objects[TARGETS[k]["object"]]
        ob.data.materials.clear()
        ob.data.materials.append(game_material(k, files))
        report[k] = {n: os.path.relpath(p, ROOT) for n, p in files.items()}
    eyes = bpy.data.objects["ASTRA_R08_Eyes"]
    eyes.data.materials.clear()
    eyes.data.materials.append(eyes_material())
    for im in list(bpy.data.images):
        if im.users == 0:
            bpy.data.images.remove(im)
    for m_ in list(bpy.data.materials):
        if m_.users == 0:
            bpy.data.materials.remove(m_)
    json.dump(dict(master_px=RES, game_px=GAME_RES, ao_mix=AO_MIX, maps=report, buried_joint_texels_refilled=JOINT_TEXELS),
              open(os.path.join(ROOT, "analysis", "game_textures.json"), "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True, relative_remap=True)
    log(f"saved {out}  ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(*(args[:2]))
