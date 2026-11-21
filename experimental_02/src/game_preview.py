"""ASTRA R08 - Experimental Model 02: pictures of the game model (stage 6 of the Roblox build).

    bvenv/bin/python experimental_02/src/game_preview.py poses     # deformation test: pose sheet
    bvenv/bin/python experimental_02/src/game_preview.py clip      # deformation test: short clip (MP4)
    bvenv/bin/python experimental_02/src/game_preview.py compare   # game model beside the high-detail model
    bvenv/bin/python experimental_02/src/game_preview.py rig       # rig reference picture
    bvenv/bin/python experimental_02/src/game_preview.py uv        # UV layouts over the colour maps
    env: SAMPLES, RES

Everything is rendered from the game file itself (astra_r08_exp02_game.blend: the 21k-triangle
meshes with their baked 1024-pixel textures, posed by the skeleton), in the same studio and with
the same cameras as the high-detail renders.
"""
import os, sys, json, time, subprocess, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont
import scene as SC
import views
import game_anim as GA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "model", "astra_r08_exp02_game.blend")
OUT = os.path.join(ROOT, "renders", "game")
STUD = 0.28
BG = (13, 14, 15)
FG = (236, 236, 232)
DIM = (160, 162, 160)
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(size, bold=True):
    try:
        return ImageFont.truetype(FONT_B if bold else FONT_R, int(size))
    except Exception:
        return ImageFont.load_default()


def log(*a):
    print("[game_preview]", *a, flush=True)


def open_game(samples=32):
    bpy.ops.wm.open_mainfile(filepath=GAME)
    sc = bpy.context.scene
    ao = bpy.data.objects[GA.ARMATURE]
    ao.scale = (STUD, STUD, STUD)               # studs -> metres, so the metric cameras of views.py fit
    SC.studio(sc)
    SC.setup_cycles(sc, samples=samples)
    sc.render.use_persistent_data = True
    return sc, ao


def shoot(sc, view, path, res, cam_name="Cam"):
    v = views.VIEWS[view] if isinstance(view, str) else view
    w, h = v["size"]
    k = res / max(w, h)
    SC.aim_studio(v.get("az", 0.0))
    cam = SC.camera(sc, cam_name, tuple(v["pos"]), tuple(v["target"]), lens=v["lens"], roll=v.get("roll", 0.0))
    SC.render(sc, cam, path, res=(int(round(w * k)), int(round(h * k))))
    return cam


def label(d, xy, text, size, fill=FG, bold=True, shadow=True):
    f = font(size, bold)
    if shadow:
        d.text((xy[0] + 2, xy[1] + 2), text, font=f, fill=(0, 0, 0))
    d.text(xy, text, font=f, fill=fill)


# ------------------------------------------------------------------------------- deformation test: poses

POSES = [("Rest", None, 0, "rest pose (the sheet's stance)"), ("Idle", "Idle", 30, "idle - breathing"),
         ("Walk", "Walk", 8, "walk - right foot planted"), ("Walk", "Walk", 23, "walk - left foot planted"),
         ("Run", "Run", 4, "run"), ("Chase", "Chase", 9, "chase"), ("Attack", "Attack", 9, "attack - wind-up"),
         ("Attack", "Attack", 15, "attack - swipe"), ("Lunge", "Lunge", 9, "lunge - draw back"),
         ("Lunge", "Lunge", 16, "lunge - bite"), ("HeadTrack", "HeadTrack", 14, "head tracking - left"),
         ("HitReact", "HitReact", 4, "hit reaction"),
         ("Death", "Death", 30, "death - knees give"), ("Death", "Death", 60, "death - down")]
CLOSE = [("JawSnap", 6, "jaw open (Jaw bone only)", "pose_jaw"), ("JawSnap", 10, "jaw shut - the skull does not move", "pose_jaw"),
         ("Attack", 15, "shoulder at full swing", "pose_shoulder2"), ("Run", 6, "hips at full stride", "pose_hips")]


def poses(res=430, samples=24):
    sc, ao = open_game(samples)
    tmp = os.path.join(OUT, "_frames")
    os.makedirs(tmp, exist_ok=True)
    tiles = []
    for vi, view in enumerate(("pose_tq", "pose_side")):
        row = []
        for (key, clip, f, text) in POSES:
            GA.set_clip(ao, clip)
            sc.frame_set(f)
            p = os.path.join(tmp, f"{view}_{key}_{f}.png")
            shoot(sc, view, p, res)
            row.append((Image.open(p).convert("RGB"), text))
        tiles.append(row)
        log(f"   {view} done")
    close = []
    for (clip, f, text, view) in CLOSE:
        GA.set_clip(ao, clip)
        sc.frame_set(f)
        p = os.path.join(tmp, f"close_{clip}_{f}.png")
        shoot(sc, view, p, int(res * 1.05))
        close.append((Image.open(p).convert("RGB"), text))
    GA.set_clip(ao, None)
    # sheet: 7 poses a row, two views -> 4 rows; close-ups underneath
    per = 7
    tw, th = tiles[0][0][0].size
    gap, head_h = 6, 64
    rows = []
    for k in range(0, len(POSES), per):
        for vi in range(2):
            rows.append([tiles[vi][j] for j in range(k, min(k + per, len(POSES)))])
    cw, ch = close[0][0].size
    W = per * tw + (per - 1) * gap
    cs = (W - 3 * gap) / (4 * cw)
    cwh = (int(cw * cs), int(ch * cs))
    H = head_h + len(rows) * (th + gap) + 34 + cwh[1] + 70
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    label(d, (14, 10), "ASTRA R08 - GAME MODEL - DEFORMATION TEST", 26)
    label(d, (14, 40), "the Roblox meshes (9,852 + 11,082 triangles, baked 1024 px maps) posed by the 27-bone skeleton; "
          "rows: three-quarter and side view of the same frame", 13, fill=DIM, bold=False, shadow=False)
    y = head_h
    for r, row in enumerate(rows):
        x = 0
        for (t, text) in row:
            im.paste(t, (x, y))
            if r % 2 == 0:
                label(d, (x + 8, y + 6), text, 13)
            x += tw + gap
        y += th + gap
    y += 8
    label(d, (14, y), "close-ups", 15)
    y += 26
    x = 0
    for (t, text) in close:
        im.paste(t.resize(cwh, Image.LANCZOS), (x, y))
        label(d, (x + 8, y + 6), text, 13)
        x += cwh[0] + gap
    y += cwh[1] + 10
    label(d, (14, y), "weights: computed per block, shared across each joint over its width, relaxed across the seams; "
          "<= 4 bones per vertex, none on Root; skull on Head only, lower jaw / its teeth / gum on Jaw only", 12,
          fill=DIM, bold=False, shadow=False)
    out = os.path.join(OUT, "ASTRA_R08_game_poses.png")
    im.save(out)
    log("wrote", out)


# ------------------------------------------------------------------------------- deformation test: clip

SEQUENCE = [("Idle", 0, 44), ("Walk", 0, 30), ("Walk", 0, 30), ("Run", 0, 18), ("Run", 0, 18), ("Run", 0, 18),
            ("Chase", 0, 18), ("Chase", 0, 18), ("Chase", 0, 18), ("Attack", 0, 36), ("Lunge", 0, 33),
            ("JawSnap", 0, 30), ("JawChatter", 0, 30), ("HeadTrack", 0, 102), ("HitReact", 0, 18), ("Death", 0, 60)]


def clip(res=480, samples=10, step=2, view="pose_tq"):
    sc, ao = open_game(samples)
    tmp = os.path.join(OUT, "_clip")
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    n = 0
    t0 = time.time()
    jobs = []
    for (name, a, b) in SEQUENCE:
        for f in range(a, b, step):
            jobs.append((name, f))
    jobs += [("Death", 60)] * 8                            # hold the last frame
    for i, (name, f) in enumerate(jobs):
        GA.set_clip(ao, name)
        sc.frame_set(f)
        p = os.path.join(tmp, f"f{i:04d}.png")
        if i == 0 or jobs[i - 1] != (name, f):
            shoot(sc, view, p, res)
            last = p
        else:
            shutil.copy(last, p)
        im = Image.open(p).convert("RGB")
        d = ImageDraw.Draw(im)
        label(d, (12, 10), name.upper(), 18)
        label(d, (12, im.height - 26), "ASTRA R08 game model - test animations (in place, 30 fps; shown at 15 fps)", 11,
              fill=DIM, bold=False)
        im.save(p)
        n += 1
        if i % 20 == 0:
            log(f"   frame {i + 1}/{len(jobs)}  ({time.time() - t0:.0f} s)")
    GA.set_clip(ao, None)
    out = os.path.join(OUT, "ASTRA_R08_deformation_test.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(30 // step), "-i", os.path.join(tmp, "f%04d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", out], check=True)
    log("wrote", out, f"({n} frames)")


# ------------------------------------------------------------------------------- game vs high-detail

COMPARE = [("front", "FRONT"), ("tq", "THREE-QUARTER"), ("side", "SIDE"), ("head", "HEAD CLOSE-UP"), ("mouthside", "MOUTH - SIDE")]


def compare(res=900, samples=48):
    sc, ao = open_game(samples)
    GA.set_clip(ao, None)
    sc.frame_set(0)
    tmp = os.path.join(OUT, "_frames")
    os.makedirs(tmp, exist_ok=True)
    pairs = []
    for (v, text) in COMPARE:
        p = os.path.join(tmp, f"cmp_{v}.png")
        shoot(sc, v, p, res)
        hi = Image.open(os.path.join(ROOT, "renders", v + ".png")).convert("RGB")
        lo = Image.open(p).convert("RGB")
        pairs.append((hi, lo, text))
    h = 520
    gap = 10
    cols = []
    for (hi, lo, text) in pairs:
        w = int(round(hi.width / hi.height * h))
        cols.append((hi.resize((w, h), Image.LANCZOS), lo.resize((w, h), Image.LANCZOS), text))
    W = sum(c[0].width for c in cols) + gap * (len(cols) - 1)
    H = 60 + 2 * (h + 28) + 50
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    label(d, (14, 10), "ASTRA R08 - HIGH-DETAIL SOURCE vs GAME MODEL", 26)
    label(d, (14, 40), "same cameras, same studio", 13, fill=DIM, bold=False, shadow=False)
    x = 0
    stats = json.load(open(os.path.join(ROOT, "analysis", "fbx_verification.json")))["structure"]["base"]["meshes"]
    tri = sum(m["triangles"] for m in stats.values())
    for (hi, lo, text) in cols:
        im.paste(hi, (x, 60 + 22))
        im.paste(lo, (x, 60 + 22 + h + 28))
        label(d, (x + 6, 60), text + "  -  high detail (1.13 M triangles)", 13, fill=DIM, bold=False, shadow=False)
        label(d, (x + 6, 60 + h + 28), text + f"  -  game model ({tri:,} triangles)", 13, fill=FG, bold=False, shadow=False)
        x += hi.width + gap
    out = os.path.join(OUT, "ASTRA_R08_game_vs_highdetail.png")
    im.save(out)
    log("wrote", out)


# ------------------------------------------------------------------------------- rig reference picture

CHAIN_COL = {"core": (240, 220, 90), "Right": (90, 190, 255), "Left": (255, 120, 90), "Jaw": (250, 250, 250)}


def bone_colour(name):
    if name.startswith("Right"):
        return CHAIN_COL["Right"]
    if name.startswith("Left"):
        return CHAIN_COL["Left"]
    if name == "Jaw":
        return CHAIN_COL["Jaw"]
    return CHAIN_COL["core"]


def rig(res=1000, samples=24):
    from bpy_extras.object_utils import world_to_camera_view
    sc, ao = open_game(samples)
    GA.set_clip(ao, None)
    sc.frame_set(0)
    clay = SC.NT("RigClay")
    clay.principled(**{"Base Color": (0.30, 0.29, 0.28, 1.0), "Roughness": 0.8})
    for ob in ao.children:
        if ob.type == "MESH":
            ob.data.materials.clear()
            ob.data.materials.append(clay.mat)
    tmp = os.path.join(OUT, "_frames")
    os.makedirs(tmp, exist_ok=True)
    panels = []
    for v, text in (("rig_front", "FRONT"), ("rig_side", "SIDE (creature's left)")):
        p = os.path.join(tmp, f"{v}.png")
        cam = shoot(sc, v, p, res)
        im = Image.open(p).convert("RGB")
        W, H = im.size
        bones = []
        for b in ao.data.bones:
            hw = ao.matrix_world @ b.head_local
            tw = ao.matrix_world @ b.tail_local
            a = world_to_camera_view(sc, cam, hw)
            c = world_to_camera_view(sc, cam, tw)
            bones.append((b.name, (a.x * W, (1 - a.y) * H), (c.x * W, (1 - c.y) * H), a.z, b.parent.name if b.parent else None))
        # pad the picture with label margins
        M = 250
        big = Image.new("RGB", (W + 2 * M, H), BG)
        big.paste(Image.eval(im, lambda x: int(x * 0.85)), (M, 0))
        d = ImageDraw.Draw(big)
        side = v == "rig_side"
        for (name, a, c, z, par) in sorted(bones, key=lambda t: -t[3] if side else 0):
            col = bone_colour(name)
            A = (a[0] + M, a[1])
            C = (c[0] + M, c[1])
            d.line([A, C], fill=col, width=5)
            r = 6
            d.ellipse([A[0] - r, A[1] - r, A[0] + r, A[1] + r], outline=col, fill=(20, 20, 20), width=2)
        # labels in the margins with leader lines to each bone's middle
        if not side:
            left = [t for t in bones if t[0].startswith("Right")]
            right = [t for t in bones if not t[0].startswith("Right")]
        else:
            left = [t for t in bones if t[0] in ("Head", "Jaw", "Neck", "RightShoulder", "RightUpperArm", "RightLowerArm",
                                                 "RightWrist", "RightHand", "LeftShoulder", "LeftUpperArm", "LeftLowerArm",
                                                 "LeftWrist", "LeftHand", "RightToes", "RightFoot", "LeftToes", "LeftFoot")]
            right = [t for t in bones if t not in left]
        f = font(15, True)
        for group, x0, align in ((left, 10, "l"), (right, W + M + 14, "r")):
            group = sorted(group, key=lambda t: (t[1][1] + t[2][1]) / 2)
            n = len(group)
            ys = np.linspace(40, H - 40, n) if n > 1 else [H / 2]
            for (name, a, c, z, par), yy in zip(group, ys):
                mx, my = (a[0] + c[0]) / 2 + M, (a[1] + c[1]) / 2
                tx = x0 + (0 if align == "l" else 0)
                col = bone_colour(name)
                d.text((tx, yy - 9), name, font=f, fill=col)
                lx = tx + d.textlength(name, font=f) + 6 if align == "l" else tx - 6
                d.line([(lx, yy), (mx, my)], fill=tuple(int(cc * 0.6) for cc in col), width=1)
        label(d, (M + 10, 10), text, 18)
        panels.append(big)
    # hierarchy panel
    rigd = json.load(open(os.path.join(ROOT, "analysis", "game_rig.json")))
    tree = {}
    for b in rigd["bones"]:
        tree.setdefault(b["parent"], []).append(b)
    lines = []

    def walk(par, depth):
        for b in tree.get(par, []):
            lines.append(("    " * depth + b["name"], b))
            walk(b["name"], depth + 1)
    walk(None, 0)
    TW = 560
    H = panels[0].height
    tp = Image.new("RGB", (TW, H), BG)
    d = ImageDraw.Draw(tp)
    label(d, (14, 10), "HIERARCHY (27 bones)", 18)
    fr = font(15, False)
    y = 50
    step = min(26, (H - 50 - 6 * 22 - 30) // max(len(lines), 1))
    for (txt, b) in lines:
        d.text((14, y), txt, font=fr, fill=bone_colour(b["name"]))
        d.text((360, y), f"{b['length_studs']:.2f} studs", font=fr, fill=DIM)
        y += step
    y += 10
    for t in ("Root: at the origin, on the floor; no skin weight",
              "Jaw: its own bone at the hinge; the lower jaw,",
              "   its 35 teeth and gum move on it alone",
              "Units: studs (1 stud = 0.28 m), Y up in the FBX",
              "Bone X axis = the creature's left on every",
              "   limb: rotate about X to bend fore / aft"):
        d.text((14, y), t, font=font(14, False), fill=DIM)
        y += 22
    W = sum(p.width for p in panels) + TW
    im = Image.new("RGB", (W, H + 50), BG)
    d = ImageDraw.Draw(im)
    label(d, (14, 10), "ASTRA R08 - GAME RIG REFERENCE", 24)
    x = 0
    for p in panels:
        im.paste(p, (x, 50))
        x += p.width
    im.paste(tp, (x, 50))
    os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
    out = os.path.join(ROOT, "docs", "ASTRA_R08_rig_reference.png")
    im.save(out)
    log("wrote", out)


# ------------------------------------------------------------------------------- UV layouts

def uv(px=2048):
    bpy.ops.wm.open_mainfile(filepath=GAME)
    d_out = os.path.join(ROOT, "textures", "uv")
    os.makedirs(d_out, exist_ok=True)
    for key in ("Body", "Head"):
        ob = bpy.data.objects[f"ASTRA_R08_{key}"]
        me = ob.data
        uvs = np.zeros(len(me.loops) * 2)
        me.uv_layers.active.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)
        col = Image.open(os.path.join(ROOT, "textures", f"ASTRA_R08_{key}_Color.png")).convert("RGB").resize((px, px), Image.LANCZOS)
        wire = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        d = ImageDraw.Draw(wire)
        for p in me.polygons:
            q = [(uvs[li][0] * px, (1 - uvs[li][1]) * px) for li in p.loop_indices]
            d.polygon(q, outline=(255, 255, 255, 170))
        over = Image.alpha_composite(Image.eval(col, lambda x: int(x * 0.75)).convert("RGBA"), wire).convert("RGB")
        over.save(os.path.join(d_out, f"ASTRA_R08_{key}_UV_over_color.png"))
        bw = Image.new("RGB", (px, px), (18, 18, 20))
        bw.paste(wire, (0, 0), wire)
        bw.save(os.path.join(d_out, f"ASTRA_R08_{key}_UV_layout.png"))
        log("wrote UV layout", key)


# ------------------------------------------------------------------------------- deformation numbers

def stats(step=1, min_edge_studs=0.107):
    """Per clip: the most any edge (>= 3 cm at rest) stretches or shrinks, where, how low anything goes,
    and how far skull and lower-jaw vertices move relative to their own bone (they should not)."""
    bpy.ops.wm.open_mainfile(filepath=GAME)
    sc = bpy.context.scene
    ao = bpy.data.objects[GA.ARMATURE]
    obs = [bpy.data.objects[n] for n in ("ASTRA_R08_Body", "ASTRA_R08_Head")]

    def verts(ob):
        dg = bpy.context.evaluated_depsgraph_get()
        me = ob.evaluated_get(dg).to_mesh()
        v = np.zeros(len(me.vertices) * 3)
        me.vertices.foreach_get("co", v)
        ob.evaluated_get(dg).to_mesh_clear()
        return v.reshape(-1, 3)

    GA.set_clip(ao, None)
    sc.frame_set(0)
    rest = {o.name: verts(o) for o in obs}
    E, dom, rigid = {}, {}, {}
    for o in obs:
        e = np.zeros(len(o.data.edges) * 2, np.int32)
        o.data.edges.foreach_get("vertices", e)
        E[o.name] = e.reshape(-1, 2)
        names = [g.name for g in o.vertex_groups]
        dom[o.name] = np.array([names[max(v.groups, key=lambda g: g.weight).group] for v in o.data.vertices])
        for bn in ("Head", "Jaw"):
            if bn in names:
                gi = names.index(bn)
                rigid[(o.name, bn)] = np.array([any(g.group == gi and g.weight > 0.999 for g in v.groups) for v in o.data.vertices])
    restM = {b.name: np.array(b.matrix_local) for b in ao.data.bones}
    out = {}
    for (name, secs, loop, fn) in GA.CLIPS:
        GA.set_clip(ao, name)
        act = bpy.data.actions[name]
        worst, shrink, where, zmin, rig_err = 1.0, 1.0, None, 1e9, 0.0
        for f in range(int(act.frame_range[0]), int(act.frame_range[1]) + 1, step):
            sc.frame_set(f)
            for o in obs:
                v = verts(o)
                e = E[o.name]
                L0 = np.linalg.norm(rest[o.name][e[:, 0]] - rest[o.name][e[:, 1]], axis=1)
                L1 = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
                ok = L0 >= min_edge_studs
                r = L1[ok] / L0[ok]
                if r.max() > worst:
                    worst = float(r.max())
                    i = np.nonzero(ok)[0][int(r.argmax())]
                    where = dict(frame=f, mesh=o.name, bone=str(dom[o.name][e[i, 0]]))
                shrink = min(shrink, float(r.min()))
                zmin = min(zmin, float(v[:, 2].min()))
                for bn in ("Head", "Jaw"):
                    m = rigid.get((o.name, bn))
                    if m is None or not m.any():
                        continue
                    P = np.array(ao.pose.bones[bn].matrix)
                    T = P @ np.linalg.inv(restM[bn])                     # rest -> posed, for anything carried by the bone alone
                    pr = rest[o.name][m] @ T[:3, :3].T + T[:3, 3]
                    rig_err = max(rig_err, float(np.linalg.norm(pr - v[m], axis=1).max()))
        out[name] = dict(max_edge_stretch=round(worst, 2), max_edge_shrink=round(shrink, 2), worst_at=where,
                         lowest_point_m=round(zmin * STUD, 3), rigid_skull_and_jaw_error_mm=round(rig_err * STUD * 1000, 3))
        log(f"   {name:<10} stretch x{worst:.2f} shrink x{shrink:.2f} at {where}; lowest {zmin * STUD:+.3f} m; "
            f"skull / jaw rigid to {rig_err * STUD * 1000:.3f} mm")
    GA.set_clip(ao, None)
    json.dump(dict(edge_min_studs=min_edge_studs, clips=out), open(os.path.join(ROOT, "analysis", "game_deformation.json"), "w"), indent=1)


# working views for the close-ups of the deformation test
import head as _HD                                               # noqa: E402
views.VIEWS["pose_jaw"] = views.cam(80.0, 2.0, _HD.Hw(0.0, 0.32, -0.22), 6.0, 1.75, (480, 420))
views.VIEWS["pose_shoulder2"] = views.cam(-35.0, 8.0, (-0.35, -0.75, 1.95), 16.0, 2.9, (480, 420))

# working views for the rig picture
views.VIEWS["rig_front"] = views.cam(0.0, 2.0, (-0.10, -0.75, 1.42), 22.0, 3.6, (620, 700))
views.VIEWS["rig_side"] = views.cam(90.0, 2.0, (0.0, -0.80, 1.42), 22.0, 3.6, (620, 700))

if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "poses"
    os.makedirs(OUT, exist_ok=True)
    S = os.environ.get("SAMPLES")
    R = os.environ.get("RES")
    kw = {}
    if S:
        kw["samples"] = int(S)
    if R:
        kw["res"] = int(R)
    dict(poses=poses, clip=clip, compare=compare, rig=rig, uv=lambda **k: uv(), stats=lambda **k: stats())[what](**kw)
