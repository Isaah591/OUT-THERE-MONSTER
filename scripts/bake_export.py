"""
Bake the procedural materials to image maps and export an FBX for Roblox Studio.

    python bake_export.py <model.blend> <out_dir> [texture_size]

Works on a throw-away copy of the scene (the editable .blend is not modified).
Per export group: join -> Smart UV Project -> bake Color / Normal / Roughness
(+ Metalness for the rods) -> write PNGs -> assign a simple preview material that
uses the baked maps -> export one FBX with every group as its own mesh.

Groups are split so that each mesh stays far below Roblox's per-MeshPart triangle
limit and so the parts map onto a future rig (head / jaw / limbs).
"""
import os
import sys

import bpy

GROUPS = {
    "Body": ["Torso"],                                   # torso, neck, deltoids, spine, scapulae
    "Head": ["Cranium", "Teeth_Upper", "Gums_Upper", "Palate", "Throat", "Jaw_Hinges",
             "Mouth_Corner_Tissue"],
    "Jaw": ["Jaw", "Teeth_Lower", "Gums_Lower", "Tongue"],
    "Arm_R_Long": ["Arm_R_Long"],
    "Arm_L_Short": ["Arm_L_Short"],
    "Leg_R": ["Leg_R"],
    "Leg_L": ["Leg_L"],
    "Rods": ["Rods"],
    "Eyes": ["Eyes"],          # not baked: use Neon material in Roblox
}
NO_BAKE = {"Eyes"}
METAL = {"Rods"}


def join_group(name, members):
    objs = [bpy.data.objects[m] for m in members]
    dups = []
    for ob in objs:
        d = ob.copy()
        d.data = ob.data.copy()
        bpy.context.scene.collection.objects.link(d)
        d.parent = None
        d.matrix_world = ob.matrix_world.copy()
        dups.append(d)
    bpy.ops.object.select_all(action='DESELECT')
    for d in dups:
        d.select_set(True)
    bpy.context.view_layer.objects.active = dups[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if len(dups) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = "EXPORT_" + name
    return ob


def uv_unwrap(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.006)
    bpy.ops.object.mode_set(mode='OBJECT')


def bake(ob, kind, img, metal_trick=False):
    """Insert an active image node into every material on ob and bake into img."""
    added = []
    links = []
    for slot in ob.material_slots:
        nt = slot.material.node_tree
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = img
        nt.nodes.active = n
        added.append((nt, n))
        if metal_trick:
            bsdf = nt.nodes.get("Principled BSDF")
            out = next(x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL')
            em = nt.nodes.new("ShaderNodeEmission")
            src = bsdf.inputs["Metallic"].links
            if src:
                nt.links.new(src[0].from_socket, em.inputs["Color"])
            else:
                v = bsdf.inputs["Metallic"].default_value
                em.inputs["Color"].default_value = (v, v, v, 1)
            old = out.inputs["Surface"].links[0].from_socket
            l = nt.links.new(em.outputs[0], out.inputs["Surface"])
            links.append((nt, em, old, out))
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sc = bpy.context.scene
    sc.render.bake.margin = 6
    if kind == "COLOR":
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    elif kind == "NORMAL":
        bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
    elif kind == "ROUGHNESS":
        bpy.ops.object.bake(type='ROUGHNESS')
    elif kind == "METALNESS":
        bpy.ops.object.bake(type='EMIT')
    for nt, em, old, out in links:
        nt.links.new(old, out.inputs["Surface"])
        nt.nodes.remove(em)
    for nt, n in added:
        nt.nodes.remove(n)


def preview_material(name, maps):
    m = bpy.data.materials.new("BAKED_" + name)
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    def tex(path, non_color):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path)
        if non_color:
            n.image.colorspace_settings.name = 'Non-Color'
        return n
    nt.links.new(tex(maps["Color"], False).outputs[0], bsdf.inputs["Base Color"])
    nt.links.new(tex(maps["Roughness"], True).outputs[0], bsdf.inputs["Roughness"])
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex(maps["Normal"], True).outputs[0], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bsdf.inputs["Normal"])
    if "Metalness" in maps:
        nt.links.new(tex(maps["Metalness"], True).outputs[0], bsdf.inputs["Metallic"])
    return m


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    blend, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    size = int(argv[2]) if len(argv) > 2 else 1024
    texdir = os.path.join(out, "textures")
    os.makedirs(texdir, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = int(os.environ.get("BAKE_SAMPLES", 24))

    originals = [o for o in bpy.data.objects if o.type == 'MESH' and o.name != "Ground"]
    exports = []
    for name, members in GROUPS.items():
        ob = join_group(name, members)
        print("GROUP %-12s %6d tris" % (name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
        exports.append(ob)
    # originals would overlap the joined copies and darken the AO term: hide them
    for o in originals:
        o.hide_render = True
    for name, ob in zip(GROUPS, exports):
        if name in NO_BAKE:
            continue
        uv_unwrap(ob)
        maps = {}
        kinds = ["COLOR", "NORMAL", "ROUGHNESS"] + (["METALNESS"] if name in METAL else [])
        for kind in kinds:
            label = kind.capitalize()
            img = bpy.data.images.new("%s_%s" % (name, label), size, size)
            if kind != "COLOR":
                img.colorspace_settings.name = 'Non-Color'
            bake(ob, kind, img, metal_trick=(kind == "METALNESS"))
            path = os.path.join(texdir, "%s_%s.png" % (name, label))
            img.filepath_raw = path
            img.file_format = 'PNG'
            img.save()
            maps[label] = path
            print("  baked", os.path.basename(path))
        ob.data.materials.clear()
        ob.data.materials.append(preview_material(name, maps))

    # Hide the editable originals; keep only export meshes, then write FBX + preview blend.
    for o in list(bpy.data.objects):
        if o in originals:
            bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in exports:
        o.select_set(True)
    fbx = os.path.join(out, "out_there_monster_roblox.fbx")
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'},
                             apply_unit_scale=True, axis_forward='-Z', axis_up='Y',
                             mesh_smooth_type='FACE', use_mesh_modifiers=True,
                             path_mode='COPY', embed_textures=False)
    print("FBX", fbx, os.path.getsize(fbx))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "baked_preview.blend"))


if __name__ == "__main__":
    main()
