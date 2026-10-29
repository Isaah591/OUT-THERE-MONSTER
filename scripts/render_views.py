"""
Render review views of the monster with neutral studio lighting (Cycles, CPU).

    python render_views.py <file.blend> <out_dir> [view ...]

Views: front, side_r, side_l, threequarter, threequarter_l, rear, head, mouth.
Adds a STUDIO collection (ground, lights, cameras) to the file and saves it.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

VIEWS = {
    # name: (camera location, look-at target, ortho scale or None, lens)
    "front":          ((-0.45, -12.0, 1.45), (-0.45, 0.0, 1.45), 3.9, None),
    "side_r":         ((-12.0, -0.40, 1.45), (0.0, -0.40, 1.45), 3.9, None),
    "side_l":         ((12.0, -0.40, 1.45), (0.0, -0.40, 1.45), 3.9, None),
    "rear":           ((-0.45, 12.0, 1.45), (-0.45, 0.0, 1.45), 3.9, None),
    "threequarter":   ((-5.6, -6.6, 2.6), (-0.45, -0.35, 1.30), None, 50),
    "threequarter_l": ((5.4, -6.8, 2.6), (-0.30, -0.35, 1.30), None, 50),
    "head":           ((-1.15, -3.3, 2.45), (0.0, -0.95, 2.00), None, 60),
    "mouth":          ((0.05, -3.0, 1.95), (0.0, -0.95, 1.85), None, 65),
}


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def ensure_studio():
    if "STUDIO" in bpy.data.collections:
        return bpy.data.collections["STUDIO"]
    col = bpy.data.collections.new("STUDIO")
    bpy.context.scene.collection.children.link(col)

    me = bpy.data.meshes.new("Ground")
    s = 12.0
    me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("Ground", me)
    m = bpy.data.materials.new("M_Studio_Ground")
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.30, 0.30, 0.30, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    me.materials.append(m)
    col.objects.link(ground)

    def area(name, loc, energy, size, target=(0, -0.4, 1.4)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy, ld.size = energy, size
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        look_at(ob, target)
        col.objects.link(ob)

    area("Key", (-4.5, -6.0, 5.5), 900, 4.0)
    area("Fill", (5.5, -4.5, 3.0), 380, 5.0)
    area("Rim", (1.5, 6.0, 5.0), 700, 4.0)
    area("Top", (0.0, -1.0, 8.0), 250, 6.0)

    world = bpy.data.worlds.new("StudioWorld")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.32, 0.34, 0.37, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    bpy.context.scene.world = world
    return col


def camera(name, col, loc, target, ortho, lens):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name])
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type, cd.ortho_scale = 'ORTHO', ortho
    else:
        cd.lens = lens
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    look_at(ob, target)
    col.objects.link(ob)
    return ob


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    blend, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    names = argv[2:] or ["front", "side_r", "threequarter"]
    os.makedirs(out, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    col = ensure_studio()
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1200
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Base Contrast'
    for n in names:
        loc, tgt, ortho, lens = VIEWS[n]
        cam = camera("CAM_" + n, col, loc, tgt, ortho, lens)
        sc.camera = cam
        if n in ("head", "mouth"):
            sc.render.resolution_x, sc.render.resolution_y = 1200, 1000
        else:
            sc.render.resolution_x, sc.render.resolution_y = 1000, 1200
        sc.render.filepath = os.path.join(out, n + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
    sc.camera = bpy.data.objects.get("CAM_threequarter") or sc.camera
    bpy.ops.wm.save_as_mainfile(filepath=blend)


if __name__ == "__main__":
    main()
