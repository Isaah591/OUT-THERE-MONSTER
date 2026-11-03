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
    # ASTRA R08 - MORE OPEN JAW sheet (hunched pose, head thrust forward, long arm planted ahead)
    "oj_front":       ((-0.20, -12.0, 1.50), (-0.20, 0.0, 1.50), 3.30, None, (1000, 1010)),
    "oj_34":          ((2.30, -5.80, 2.10), (-0.15, -0.55, 1.45), None, 55, (1000, 1030)),
    "oj_side":        ((12.0, -0.42, 1.50), (0.0, -0.42, 1.50), 3.35, None, (1000, 990)),
    "oj_head":        ((0.95, -2.95, 2.95), (0.0, -1.15, 2.30), None, 55, (1100, 900)),
    "oj_mouth_side":  ((12.0, -1.02, 2.22), (0.0, -1.02, 2.22), 1.35, None, (1000, 1000)),
    "oj_arm":         ((-2.65, -2.75, 1.20), (-1.10, -0.95, 0.90), None, 45, (1000, 1100)),
    "oj_torso":       ((1.75, -1.60, 2.45), (0.30, -0.15, 1.95), None, 42, (1100, 1000)),
    "oj_teeth":       ((0.40, -2.35, 1.95), (0.0, -1.20, 2.20), None, 55, (1000, 1030)),
    "oj_surface":     ((0.02, -12.0, 1.80), (0.02, 0.0, 1.80), 1.05, None, (1100, 980)),
    # the face, front orthographic (same direction as oj_front, framed on the head)
    "oj_face":        ((-0.01, -12.0, 2.42), (-0.01, 0.0, 2.42), 0.95, None, (1000, 1150)),
    # the face as seen in the sheet's three-quarter panel (same direction as oj_34, framed on the head)
    "oj_face34":      ((2.30, -5.80, 2.10), (-0.02, -1.15, 2.28), None, 135, (1000, 1260)),
    # the approved sheet's three-quarter camera, fitted to its silhouette with fit_camera.py:
    # ref34 = fitted on the head, shoulders and upper torso (IoU 0.81), the view used to compare the
    # face; ref34_body = fitted on the whole figure (IoU 0.67; the painting's legs and long arm are
    # posed differently, which pulls that fit ~11 deg further round). Same location, lens and lens
    # shift as the reference panel, at twice its resolution.
    "ref34":          ((1.6734, -4.74, 2.1633), (-0.15, -0.55, 1.45), None, 46.27, (1016, 990), (0.0478, 0.0149)),
    "ref34_body":     ((3.9392, -6.4692, 2.3411), (-0.15, -0.55, 1.45), None, 80.88, (1016, 990), (0.0254, 0.0314)),
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
    if os.environ.get("STUDIO") == "sheet":
        # seamless cyclorama facing the sheet's three-quarter camera: the floor bends up into a
        # back wall, so there is no horizon line (as in the sheet's painted backdrop)
        prof = [(-14.0, 0.0), (2.6, 0.0)]
        prof += [(2.6 + 3.4 * math.sin(a), 3.4 - 3.4 * math.cos(a)) for a in [math.pi / 2 * k / 12 for k in range(1, 13)]]
        prof += [(6.0, 14.0)]
        az = math.radians(23.5)
        rot = lambda x, y: (x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az))
        verts, faces = [], []
        for x in (-20.0, 20.0):
            for y, z in prof:
                rx, ry = rot(x, y - 0.3)
                verts.append((rx, ry, z))
        n = len(prof)
        faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
        me.from_pydata(verts, [], faces)
        for p_ in me.polygons:
            p_.use_smooth = True
    else:
        s = 12.0
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("Ground", me)
    m = bpy.data.materials.new("M_Studio_Ground")
    sheet = os.environ.get("STUDIO") == "sheet"   # approximates the approved sheet's three-quarter panel
    dark = os.environ.get("STUDIO") == "dark" or sheet   # R08-sheet style presentation backdrop
    g = 0.006 if sheet else (0.018 if dark else 0.30)
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

    if sheet:   # dark charcoal backdrop, key from the upper left front, weak fill, warm-neutral rim
        area("Key", (-4.0, -5.2, 5.6), 1250, 3.2)
        area("Fill", (3.2, -5.6, 1.7), 260, 5.0)
        area("Rim", (3.0, 4.6, 4.6), 620, 3.0)
        area("Top", (0.0, -1.0, 8.0), 120, 6.0)
    else:
        k = 1.25 if dark else 1.0
        area("Key", (-4.5, -6.0, 5.5), 900 * k, 4.0)
        area("Fill", (5.5, -4.5, 3.0), 380 * k, 5.0)
        area("Rim", (1.5, 6.0, 5.0), 700 * k, 4.0)
        area("Top", (0.0, -1.0, 8.0), 250 * k, 6.0)

    world = bpy.data.worlds.new("StudioWorld")
    bg = (0.014, 0.015, 0.017, 1) if sheet else ((0.028, 0.030, 0.033, 1) if dark else (0.32, 0.34, 0.37, 1))
    world.node_tree.nodes["Background"].inputs["Color"].default_value = bg
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0 if dark else 0.6
    bpy.context.scene.world = world
    return col


def camera(name, col, loc, target, ortho, lens, shift=(0.0, 0.0)):
    if name in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[name])
    cd = bpy.data.cameras.new(name)
    if ortho:
        cd.type, cd.ortho_scale = 'ORTHO', ortho
    else:
        cd.lens = lens
        cd.sensor_fit = 'HORIZONTAL'
        cd.sensor_width = 36.0
    cd.shift_x, cd.shift_y = shift
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
        loc, tgt, ortho, lens, res = VIEWS[n][:5]
        shift = VIEWS[n][5] if len(VIEWS[n]) > 5 else (0.0, 0.0)
        cam = camera("CAM_" + n, col, loc, tgt, ortho, lens, shift)
        sc.camera = cam
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = os.path.join(out, n + ".png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", sc.render.filepath)
    sc.camera = bpy.data.objects.get("CAM_threequarter") or sc.camera
    bpy.ops.wm.save_as_mainfile(filepath=blend)


if __name__ == "__main__":
    main()
