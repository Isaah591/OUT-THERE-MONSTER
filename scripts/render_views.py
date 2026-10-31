"""
Render review views of the monster with neutral studio lighting (Cycles, CPU).

    python render_views.py <file.blend> <out_dir> [view ...]

Views: see VIEWS (full-body ortho views, three-quarters, head/mouth and wound close-ups).
Adds a STUDIO collection (ground, lights, cameras) to the file and saves it.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

VIEWS = {
    # name: (camera location, look-at target, ortho scale or None, lens, resolution)
    "front":          ((-0.66, -12.0, 1.62), (-0.66, 0.0, 1.62), 3.95, None, (1200, 1200)),
    "side_r":         ((-12.0, -0.50, 1.62), (0.0, -0.50, 1.62), 3.55, None, (1000, 1200)),
    "side_l":         ((12.0, -0.50, 1.62), (0.0, -0.50, 1.62), 3.55, None, (1000, 1200)),
    "rear":           ((-0.66, 12.0, 1.62), (-0.66, 0.0, 1.62), 3.95, None, (1200, 1200)),
    "threequarter":   ((-5.6, -7.4, 2.2), (-0.65, -0.45, 1.45), None, 50, (1100, 1200)),
    "threequarter_l": ((5.6, -6.6, 2.7), (-0.45, -0.40, 1.30), None, 50, (1100, 1200)),
    "head":           ((-1.10, -3.0, 2.55), (0.0, -0.95, 2.02), None, 60, (1200, 1000)),
    "head_front":     ((0.02, -3.55, 2.45), (0.02, -0.90, 2.28), None, 85, (1200, 1000)),
    "head_34":        ((-1.30, -3.05, 2.75), (-0.02, -0.95, 2.20), None, 70, (1200, 1000)),
    "mouth":          ((0.10, -2.75, 1.70), (0.0, -0.95, 1.80), None, 62, (1200, 1000)),
    "mouth_side":     ((-2.4, -2.05, 1.95), (0.0, -0.95, 1.85), None, 62, (1200, 1000)),
    "wound_arm":      ((-1.55, -2.05, 1.55), (-0.98, -0.62, 1.05), None, 70, (1200, 1000)),
    "wound_leg":      ((0.75, -1.85, 0.75), (0.17, -0.10, 0.42), None, 60, (1000, 1200)),
    "wound_torso":    ((2.1, -1.0, 1.85), (0.32, -0.10, 1.55), None, 55, (1200, 1000)),
    # R08-sheet-matched cameras (same panel aspect; front/3-4 perspective like the sheet,
    # side is an exact orthographic 90-degree profile)
    "r08_front":      ((-0.08, -9.0, 1.45), (-0.08, 0.0, 1.45), None, 100, (1074, 1256)),
    "r08_34":         ((1.65, -5.43, 1.70), (-0.05, -0.20, 1.42), None, 59, (1148, 1256)),
    "r08_side":       ((12.0, -0.36, 1.43), (0.0, -0.36, 1.43), 3.09, None, (950, 1256)),
    "mouth_profile":  ((12.0, -0.52, 2.22), (0.0, -0.52, 2.22), 1.25, None, (1200, 1000)),
    "mouth_34":       ((1.50, -2.80, 2.55), (0.0, -0.50, 2.30), None, 55, (1200, 1000)),
    "wound_shoulder": ((-1.75, -1.55, 2.95), (-0.62, -0.25, 2.22), None, 55, (1200, 1000)),
    # geometry close-ups matching the R08 sheet's detail panels
    "torso_close":    ((1.25, -1.55, 2.70), (0.40, -0.12, 2.22), None, 50, (1200, 1000)),
    "head_close":     ((1.00, -2.30, 2.78), (0.02, -0.52, 2.42), None, 62, (1200, 1000)),
    "arm_close":      ((-1.95, -1.75, 1.05), (-0.98, -0.45, 1.05), None, 45, (1000, 1100)),
    "wound_back":     ((-1.3, 2.4, 2.9), (-0.25, 0.10, 1.95), None, 50, (1200, 1000)),
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
    dark = os.environ.get("STUDIO") == "dark"     # R08-sheet style presentation backdrop
    g = 0.018 if dark else 0.30
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (g, g, g, 1)
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

    k = 1.25 if dark else 1.0
    area("Key", (-4.5, -6.0, 5.5), 900 * k, 4.0)
    area("Fill", (5.5, -4.5, 3.0), 380 * k, 5.0)
    area("Rim", (1.5, 6.0, 5.0), 700 * k, 4.0)
    area("Top", (0.0, -1.0, 8.0), 250 * k, 6.0)

    world = bpy.data.worlds.new("StudioWorld")
    bg = (0.028, 0.030, 0.033, 1) if dark else (0.32, 0.34, 0.37, 1)
    world.node_tree.nodes["Background"].inputs["Color"].default_value = bg
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0 if dark else 0.6
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
    sc.cycles.samples = int(os.environ.get("SAMPLES", 48))
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1200
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Base Contrast'
    for n in names:
        loc, tgt, ortho, lens, res = VIEWS[n]
        cam = camera("CAM_" + n, col, loc, tgt, ortho, lens)
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = os.path.join(out, n + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
    sc.camera = bpy.data.objects.get("CAM_threequarter") or sc.camera
    bpy.ops.wm.save_as_mainfile(filepath=blend)


if __name__ == "__main__":
    main()
