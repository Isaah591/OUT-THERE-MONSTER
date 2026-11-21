"""ASTRA R08 - assemble the Roblox Studio handoff package.

    bvenv/bin/python experimental_02/src/handoff.py

Run after game_export.py (which writes and verifies the FBX files).  Builds
experimental_02/handoff/ASTRA_R08_Roblox/ and experimental_02/handoff/ASTRA_R08_Roblox.zip:

    README.md                      how to bring the monster and its clips into Roblox Studio
    ASTRA_R08.fbx                  the character: meshes + skeleton + skin, textures embedded
    ASTRA_R08_game.blend           the rigged Blender project (textures linked from ./textures)
    animations/ASTRA_R08_<Clip>.fbx  one clip per file, all on the same skeleton and bind pose
    textures/                      the 1024 maps (+ uv/ layouts, + source_2048/ masters - folder only)
    rig/                           BONES.md, bones.csv, rig picture
    roblox/                        AstraR08 controller, test script, both in ASTRA_R08_Scripts.rbxmx
    checks/                        the verification report and its data
    previews/                      pose sheet, deformation clip, comparison pictures
    MANIFEST.txt                   every file with its size and SHA-256

The high-detail source model is not touched (it is not part of the package; see the README).
"""
import os, sys, json, shutil, hashlib, zipfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "handoff", "ASTRA_R08_Roblox")
ZIP = os.path.join(ROOT, "handoff", "ASTRA_R08_Roblox.zip")
AN = os.path.join(ROOT, "analysis")
STUD = 0.28

CARRIES = {
    "Root": "nothing (no skin weight, as Roblox requires); top of the hierarchy, on the ground at the origin",
    "Pelvis": "bottom of the torso, pelvis block, groin block",
    "Spine": "middle of the torso",
    "Chest": "hunched upper torso (top corners shared with the shoulders), rods in the back and flank",
    "Neck": "neck block (shared with Chest at its base, Head at its top)",
    "Head": "skull with its armour slabs, sockets and hinge blocks; the 32 upper teeth; upper gum; eyes",
    "Jaw": "lower jaw, its 35 teeth and the gum band (rigidly); shares the cheek sinews, mouth webs and throat with Head",
    "RightShoulder": "right top corner of the chest, start of the long arm",
    "RightUpperArm": "long arm, shoulder to elbow",
    "RightLowerArm": "long arm, elbow to forearm bend",
    "RightWrist": "thick forearm",
    "RightHand": "blunt hollow end resting on the floor",
    "LeftShoulder": "left top corner of the chest, start of the short arm",
    "LeftUpperArm": "short arm, shoulder to elbow",
    "LeftLowerArm": "short forearm",
    "LeftWrist": "end of the short forearm",
    "LeftHand": "blunt end of the short arm",
    "RightHip": "right hip block under the right half of the pelvis",
    "RightUpperLeg": "right thigh",
    "RightLowerLeg": "right shin, knee and ankle block",
    "RightFoot": "right foot block",
    "RightToes": "four right toe blocks",
    "LeftHip": "left hip block under the left half of the pelvis",
    "LeftUpperLeg": "left thigh",
    "LeftLowerLeg": "left shin, knee and ankle block",
    "LeftFoot": "left foot block",
    "LeftToes": "four left toe blocks",
}
PRIORITY = {"Idle": "Idle", "Walk": "Movement", "Run": "Movement", "Chase": "Movement", "Attack": "Action",
            "Lunge": "Action", "HitReact": "Action2", "Death": "Action4", "JawSnap": "Action3", "JawChatter": "Action3",
            "HeadTrack": "Action2"}
PURPOSE = {"Idle": "standing, breathing, small jaw movement", "Walk": "walk cycle, in place",
           "Run": "run cycle, in place", "Chase": "aggressive run: lower, long arm reaching, jaws snapping",
           "Attack": "long-arm swipe", "Lunge": "bite: draw back, lunge, snap", "HitReact": "struck from the front",
           "Death": "staggers, knees give, folds forward onto the ground",
           "JawSnap": "jaw only: gape, snap shut twice - layer over anything",
           "JawChatter": "jaw only, looping: restless jaw - layer over Idle or Chase",
           "HeadTrack": "neck and head only: look left, right, up, down - layer over anything"}


def log(*a):
    print("[handoff]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    return dst


# ------------------------------------------------------------------------------- the .blend

def package_blend():
    """The game file, saved into the package with its textures linked from ./textures."""
    import bpy
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "model", "astra_r08_exp02_game.blend"))
    import game_anim as GA
    ao = bpy.data.objects[GA.ARMATURE]
    GA.set_clip(ao, None)                               # saved in the rest (bind) pose, no clip assigned
    bpy.context.scene.frame_set(0)
    out = os.path.join(PKG, "ASTRA_R08_game.blend")
    for im in bpy.data.images:
        if im.filepath and im.packed_file is None:
            name = os.path.basename(bpy.path.abspath(im.filepath))
            im.filepath = "//textures/" + name
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True, relative_remap=False)
    # read it back from where it now lives: every image must load, the rig and clips must be there
    bpy.ops.wm.open_mainfile(filepath=out)
    imgs = []
    for im in bpy.data.images:
        p = bpy.path.abspath(im.filepath)
        im.reload()
        imgs.append(dict(image=im.name, path=im.filepath, exists=os.path.exists(p), size=list(im.size)))
    res = dict(file=os.path.relpath(out, PKG), images=imgs,
               images_ok=all(i["exists"] and i["size"] == [1024, 1024] for i in imgs) and len(imgs) == 8,
               objects=sorted(f"{o.type}:{o.name}" for o in bpy.data.objects),
               actions=sorted(a.name for a in bpy.data.actions),
               materials={o.name: [m.name for m in o.data.materials] for o in bpy.data.objects if o.type == "MESH"},
               bones=len(bpy.data.objects[GA.ARMATURE].data.bones))
    return res


# ------------------------------------------------------------------------------- bones

def bone_docs(rig, weights):
    vb = weights["ASTRA_R08_Body"]["vertices_per_bone"]
    vh = weights["ASTRA_R08_Head"]["vertices_per_bone"]
    bones = rig["bones"]
    kids = {}
    for b in bones:
        kids.setdefault(b["parent"], []).append(b["name"])
    depth = {}
    for b in bones:
        depth[b["name"]] = 0 if b["parent"] is None else depth[b["parent"]] + 1
    tree = []

    def walk(p, d):
        for n in kids.get(p, []):
            tree.append("    " * d + n)
            walk(n, d + 1)
    walk(None, 0)

    def studio(v):                  # Blender (x, y, z) -> FBX / Studio (-x, z, y): Y up, the creature faces -Z
        return (-v[0], v[2], v[1])
    rows, csv = [], ["index,bone,parent,depth,children,head_x,head_y,head_z,tail_x,tail_y,tail_z,length_studs,vertices,carries"]
    for i, b in enumerate(bones):
        h, t = studio(b["head_studs"]), studio(b["tail_studs"])
        nv = vb.get(b["name"], 0) + vh.get(b["name"], 0) + (12 if b["name"] == "Head" else 0)
        ch = kids.get(b["name"], [])
        rows.append(f"| {i + 1} | `{b['name']}` | {('`' + b['parent'] + '`') if b['parent'] else '-'} | "
                    f"({h[0]:.2f}, {h[1]:.2f}, {h[2]:.2f}) | {b['length_studs']:.2f} | {nv:,} | {CARRIES[b['name']]} |")
        csv.append(",".join([str(i + 1), b["name"], b["parent"] or "", str(depth[b["name"]]), " ".join(ch)]
                            + [f"{v:.4f}" for v in h + t] + [f"{b['length_studs']:.4f}", str(nv), '"' + CARRIES[b["name"]] + '"']))
    md = f"""# ASTRA R08 - bones

27 bones in one hierarchy; every mesh (`ASTRA_R08_Body`, `ASTRA_R08_Head`, `ASTRA_R08_Eyes`) is skinned to it.
"Right" / "Left" are the creature's own sides - its very long arm is the right one.

![Rig](ASTRA_R08_rig_reference.png)

## Hierarchy

```
{chr(10).join(tree)}
```

## Bones

Head (joint) and length in **studs**, in the frame of the FBX file and of Studio after import with the
settings in the README: X = the creature's right, Y = up, Z = toward its back (the creature faces -Z).
Vertices = vertices with any weight on the bone (all three meshes).

| # | Bone | Parent | Head position (studs) | Length (studs) | Vertices | Carries |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

The same table as CSV: `bones.csv`.

## Notes for animating

- **Root** sits on the ground at the origin and carries no weight.  The clips key it but never move it
  (in place, no root motion): move the model itself in the game.
- **Jaw** is a bone of its own at the hinge (head at the middle of the hinge line, tail at the chin); the
  lower jaw, its 35 teeth and its gum follow it rigidly, the skull does not move (measured to 0.001 mm).
  Opening = rotating it about the creature's left-right axis; useful range from 21 degrees shut to 16
  degrees wider than the rest pose (the rest pose is the sheet's open mouth).
- **Neck + Head** turn the head; the test clip HeadTrack uses up to 52 degrees left / right (22 neck + 30
  head) and about 34 up / 30 down.
- Each arm has five bones (Shoulder, UpperArm, LowerArm, Wrist, Hand) for the very long arms; each leg
  five (Hip, UpperLeg, LowerLeg, Foot, Toes).
- In Blender every bone's local Y runs along it and, except on the sideways Shoulder and Hip bones,
  its local X points to the creature's left.  Studio may express bone axes differently after import;
  the controller script in `roblox/` works in world space so it does not depend on them.
"""
    return md, "\n".join(csv) + "\n"


# ------------------------------------------------------------------------------- Roblox model file

def rbxmx(module_src, test_src):
    def esc(s):
        assert "]]>" not in s
        return "<![CDATA[" + s + "]]>"
    return f"""<roblox xmlns:xmime="http://www.w3.org/2005/05/xmlmime" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.roblox.com/roblox.xsd" version="4">
	<Item class="Folder" referent="RBX0">
		<Properties>
			<string name="Name">ASTRA_R08_Scripts</string>
		</Properties>
		<Item class="ModuleScript" referent="RBX1">
			<Properties>
				<string name="Name">AstraR08</string>
				<ProtectedString name="Source">{esc(module_src)}</ProtectedString>
			</Properties>
		</Item>
		<Item class="Script" referent="RBX2">
			<Properties>
				<string name="Name">AstraR08_Test</string>
				<ProtectedString name="Source">{esc(test_src)}</ProtectedString>
			</Properties>
		</Item>
	</Item>
</roblox>
"""


# ------------------------------------------------------------------------------- README

def readme(V, anims, weights, blend, rig):
    b = V["structure"]["base"]
    meshes = b["meshes"]
    clips = V["structure"]["clips"]
    pl = b["placement"]
    bp = b.get("bind_pose", {})
    n_pass, n_all = sum(c["passed"] for c in V["checks"]), len(V["checks"])
    dT = max(max(abs(a - c) for a, c in zip(s["skeleton"][k]["T"], b["skeleton"][k]["T"])) for s in clips.values() for k in b["skeleton"])
    dR = max(max(abs(a - c) for a, c in zip(s["skeleton"][k]["R"], b["skeleton"][k]["R"])) for s in clips.values() for k in b["skeleton"])
    imp = V["imports"]
    worst_mm = max(c["max_error_mm"] for w in imp.values() for c in w["clips"].values())
    pos_err = max(d["rest_position_error_studs"] for w in imp.values() for d in w["meshes"].values())
    w_err = max(d.get("weight_error", 0.0) for w in imp.values() for d in w["meshes"].values())
    clip_rows = []
    for c in anims["clips"]:
        nm = c["name"]
        sp = f"{c['ground_speed_studs_s']:.1f}" if c.get("ground_speed_studs_s") else "-"
        bones = "all 27" if c["bones"] == "all" else ", ".join(c["bones"])
        clip_rows.append(f"| `animations/ASTRA_R08_{nm}.fbx` | {nm} | {c['frames']} ({c['seconds']:.1f} s) | "
                         f"{'yes' if c['loop'] else 'no'} | {bones} | {PRIORITY[nm]} | {sp} | {PURPOSE[nm]} |")
    tri = {k: v["triangles"] for k, v in meshes.items()}

    def num(v):
        return "0" if abs(v) < 1e-12 else f"{v:.0e}"
    infl = {k: v["max_influences"] for k, v in meshes.items()}
    return f"""# ASTRA R08 - Roblox Studio handoff

Everything needed to bring the ASTRA R08 monster into Roblox Studio as an animated enemy: the
game-ready mesh, its 27-bone skeleton and skinning, textures, eleven animation clips (each in its own
FBX, all on the same skeleton and bind pose), an independently animated jaw, the bone list, a
controller script and a test script.

**Status:** every file was exported from Blender with the settings in Roblox's Blender guide and
verified in Blender ({n_pass} of {n_all} checks passed - below and in `checks/VERIFICATION.md`).  The
package has **not** been opened in Roblox Studio: Studio does not run where it was built.  The steps
below follow Roblox's documentation; the test script in step 4 is the quickest way to see that
everything arrived.

## Contents

| Path | What it is |
|---|---|
| `ASTRA_R08.fbx` | The character: meshes `ASTRA_R08_Body` ({tri['ASTRA_R08_Body']:,} triangles), `ASTRA_R08_Head` ({tri['ASTRA_R08_Head']:,} - skull, lower jaw, 67 teeth, gums, sinews, throat) and `ASTRA_R08_Eyes` ({tri['ASTRA_R08_Eyes']}), skinned to one 27-bone skeleton; one material per mesh with its 1024 x 1024 maps embedded; rest pose; no animation |
| `animations/` | Eleven clips, one per FBX (table below) |
| `ASTRA_R08_game.blend` | The rigged Blender project: the three meshes, the skeleton and weights, the materials (maps linked from `textures/`) and all eleven clips as actions; saved in the rest pose |
| `textures/` | `ASTRA_R08_<Body or Head>_<Color, Normal, Roughness, Metalness>.png`, 1024 x 1024 (Color / Normal 24-bit RGB, normal map OpenGL tangent space; Roughness / Metalness 8-bit grey); `uv/` UV layouts; `source_2048/` 2048 masters + albedo and ambient occlusion (folder only, not in the zip) |
| `rig/` | `BONES.md` (every bone, its parent and what it moves), `bones.csv`, `ASTRA_R08_rig_reference.png` |
| `roblox/` | `AstraR08.lua` (ModuleScript: plays the clips, layers jaw / head clips, procedural jaw and look-at), `AstraR08_Test.server.lua` (Script: plays every clip in turn), both together in `ASTRA_R08_Scripts.rbxmx` |
| `checks/` | `VERIFICATION.md` (all {n_all} checks with their numbers), the data behind it, deformation numbers |
| `previews/` | Pose sheet and deformation clip (MP4) of every clip, the game model beside the high-detail model |
| `MANIFEST.txt` | Every file with its size and SHA-256 |

The high-detail source model (1.13 million triangles) the maps were baked from is not part of the
package and was not changed: `experimental_02/model/astra_r08_exp02_highdetail.blend` in the repository.

## Verified before export

| Requirement | Result |
|---|---|
| Each mesh within Roblox's 20,000-triangle limit | Body {tri['ASTRA_R08_Body']:,} · Head {tri['ASTRA_R08_Head']:,} · Eyes {tri['ASTRA_R08_Eyes']} - pass |
| No vertex with more than four bone influences | most on any vertex: Body {infl['ASTRA_R08_Body']}, Head {infl['ASTRA_R08_Head']}, Eyes {infl['ASTRA_R08_Eyes']} - pass |
| Root bone has no vertex influences | no skin cluster for Root in the file; 0 weight on Root - pass |
| Skeleton and skinning survive FBX export | read back by two independent FBX readers (Blender's Python importer and its C++ ufbx importer): 27 bones with identical names and parents; vertex positions within {num(pos_err)} studs; skin weights identical (largest difference {num(w_err)}) - pass |
| All animations use the same skeleton and bind pose | all 11 clip files: the same 27 bones and hierarchy, and default (rest) transforms equal to the character's bind pose (largest difference {num(dT)} studs, {num(dR)} degrees); the character's bind pose equals its rest skeleton (to {num(bp.get('max_diff_from_rest', 0))}); each clip played from its own file on the re-imported character deforms it exactly as in Blender (largest difference {worst_mm} mm) - pass |
| Textures correctly linked | in the FBX each material carries its own four maps on their channels (colour on DiffuseColor, normal on NormalMap, roughness on ShininessExponent, metalness on ReflectionFactor) with the 1024 x 1024 PNGs embedded; in the .blend all 8 maps are linked from `./textures/` and load - pass |
| Root position and orientation | Root bone at the origin, pointing straight up; soles on the ground plane (lowest point Y = {pl['lowest_point'] + 0.0:.3f}); faces -Z (Roblox's front); the origin lies between the feet, {pl['feet_centre_offset_from_origin']:.2f} studs from their centre; height {pl['highest_point']:.2f} studs (2.885 m) - pass |

## 1. Import the monster

1. In Studio: **Avatar** tab (or **Home**) > **Import 3D**, choose `ASTRA_R08.fbx`.
2. Set, in the importer's settings panel:

   | Setting | Value | Why |
   |---|---|---|
   | Rig General > **Rig Type** | **Custom** | it is not an R15 rig; it has its own 27 bones |
   | File Geometry > **Scale Unit** | **Stud** (the default) | the file is authored in studs, as Roblox's Blender guide asks |
   | File Transform > **World Forward** / **World Up** | **Front** / **Top** (the defaults) | the file is Z Forward / Y Up, as the guide asks |
   | **Keep Zero Influence Bones** | **on** | Root carries no weight (Roblox's rule) and must not be dropped - the clips address it |
   | **Merge Meshes** | **off** | keep Body, Head and Eyes separate; they share the skeleton |
   | Set Pivot to Scene Origin / Import Only As Model | on (the defaults) | the pivot is the creature's ground point |

3. Import.  Expect a Model holding three MeshParts with the bones inside, about **10.3 studs** tall
   (2.885 m; twice a default avatar), facing the front (-Z), feet on the ground.  Name the Model
   **`ASTRA_R08`** (the test script looks for that name).
4. **Textures.**  The maps are embedded in the FBX.  If a MeshPart arrives without its
   SurfaceAppearance, or with a map missing, add a `SurfaceAppearance` to `ASTRA_R08_Body` and to
   `ASTRA_R08_Head` and set ColorMap, NormalMap, RoughnessMap and MetalnessMap to the matching files
   in `textures/` (Body maps on Body, Head maps on Head).
5. **Eyes.**  Select `ASTRA_R08_Eyes`, set Material **Neon** and Color about (255, 16, 2) - two small
   red glowing points deep in the sockets.
6. **Animation holder.**  If the import did not create one, insert an `AnimationController` into the
   Model and an `Animator` into the AnimationController (a non-humanoid rig plays animations through
   these; the Animation Editor also needs one to open the rig).

## 2. Import the animations

For each file in `animations/`:

1. Avatar tab > **Animation Editor** (the docs call it the Clip Editor), click the ASTRA_R08 model.
2. **...** menu > **Import** > **From FBX Animation**, choose the file.  Bone names match the rig exactly.
3. Set **Looping** and **Priority** as in the table; then **Publish to Roblox** and note the animation ID.

| File | Clip | Frames at 30 fps | Loop | Bones keyed | Priority | Ground speed (studs/s) | What it is |
|---|---|---|---|---|---|---|---|
{chr(10).join(clip_rows)}

- All clips are **in place** (no root motion).  For Walk, Run and Chase, the ground speed is the
  speed at which the feet do not slide: play the clip at `speed / ground speed` (the controller
  script does this).  Roblox's default WalkSpeed is 16 studs/s.
- Idle, Walk, Run, Chase and JawChatter are seamless loops (their last frame equals the first).
- **JawSnap, JawChatter and HeadTrack** key only the bones listed; played at their higher priority they
  move those bones over whatever else is playing.  If Studio adds tracks for other bones when importing
  them, delete those tracks before publishing, or they will hold the rest of the body still.

## 3. The jaw on its own

The lower jaw, its 35 teeth and its gum are carried by the **Jaw** bone alone, so the mouth opens and
closes without bending the skull.  Three ways to drive it:

1. **Jaw clips** - `JawSnap` (bite) and `JawChatter` (loop) animate the Jaw bone only; play them over
   Idle, Walk, Run, Chase or anything else.
2. **Full-body clips** - Chase, Lunge, Attack, HitReact and Death also move the jaw as part of the action.
3. **From a script** - `AstraR08:SetJawOpen(amount)` (-1 shut ... 0 as animated ... 1 widest) adds a jaw
   angle on top of whatever is playing; `AstraR08:SetLookTarget(position)` turns the neck and head
   toward a point.  Both work in world space, so they do not depend on how Studio orients the bones'
   local axes.  Bone transforms set by a script are seen where the script runs: use them from a
   LocalScript for players (or in Studio's Run mode on the server).

## 4. Test it in Studio

1. In the Explorer, right-click **ServerScriptService** > **Insert from File...**, choose
   `roblox/ASTRA_R08_Scripts.rbxmx`.  It adds a folder with **AstraR08** (ModuleScript) and
   **AstraR08_Test** (Script).
2. Open AstraR08_Test, paste each published animation ID into the `IDS` table.
3. Press **Run** (F8).  The model plays every locomotion loop, the actions, the jaw and head clips
   layered over Idle and Chase, the procedural jaw and look-at, then dies and holds the last frame;
   the Output window names each clip as it starts.  Things to check:
   - JawSnap over Idle: only the jaw moves differently; the skull stays still.
   - HeadTrack: only the neck and head move.
   - Walk / Run / Chase: the feet plant; Death ends folded forward on the ground.

## 5. Use it in a game

```lua
local AstraR08 = require(game.ServerScriptService.ASTRA_R08_Scripts.AstraR08)
local rig = AstraR08.new(workspace.ASTRA_R08, {{ Idle = "rbxassetid://...", Walk = "rbxassetid://...", ... }})
rig:SetLocomotion("Chase", 24)     -- loop, sped to match 24 studs/s
rig:Play("JawSnap")                -- jaw only, over the chase
rig:Play("Attack")
rig:Die()                          -- stops everything, plays Death, holds the last frame
```

Movement, pathfinding and damage are game-specific.  Skinned MeshParts collide with their rest shape,
so give the enemy simple invisible hitbox parts.  To resize the monster, scale the whole Model with
`Model:ScaleTo(...)` so the skeleton scales with the meshes.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Far too small or too large | Re-import with Scale Unit = Stud (one file unit is one stud) |
| Facing backwards | Re-import with World Forward = Front (the file is Z Forward, as Roblox's Blender guide asks) |
| A bone is missing (often Root) | Re-import with Keep Zero Influence Bones on |
| Animation Editor will not open the model | Add an AnimationController with an Animator inside the Model |
| A jaw or head clip freezes the body | Delete the tracks for other bones in the Animation Editor, re-publish; check its priority |
| Textures missing or flat | Add a SurfaceAppearance per MeshPart with the maps from `textures/` |
| Procedural jaw or look-at turns the wrong way | They use the Model's pivot as the creature's frame: keep the pivot facing the creature's front (as imported with Set Pivot to Scene Origin); or call SetJawOpen with the opposite sign |

## Re-exporting

The package is built by `experimental_02/src/` in the repository (Blender 5 as a Python module):
`game_export.py` writes and verifies the FBX files from the game .blend, `handoff.py` assembles this
folder.  To export by hand from `ASTRA_R08_game.blend`: Scene Units > Unit System None; File > Export
> FBX with Path Mode Copy + Embed Textures, Apply Scalings FBX Unit Scale, Forward Z Forward, Up Y Up,
Add Leaf Bones off, and Bake Animation on only for a clip (with only that clip's action on the armature).
"""


# ------------------------------------------------------------------------------- main

def main():
    t0 = time.time()
    if os.path.isdir(PKG):
        shutil.rmtree(PKG)
    os.makedirs(PKG)
    V = json.load(open(os.path.join(AN, "fbx_verification.json")))
    assert all(c["passed"] for c in V["checks"]), "run game_export.py: not every FBX check passes"
    anims = json.load(open(os.path.join(AN, "game_animations.json")))
    weights = json.load(open(os.path.join(AN, "game_weights.json")))
    rig = json.load(open(os.path.join(AN, "game_rig.json")))
    # FBX files
    copy(os.path.join(ROOT, "export", "ASTRA_R08.fbx"), os.path.join(PKG, "ASTRA_R08.fbx"))
    for c in anims["clips"]:
        f = f"ASTRA_R08_{c['name']}.fbx"
        copy(os.path.join(ROOT, "export", "animations", f), os.path.join(PKG, "animations", f))
    extra = sorted(set(os.listdir(os.path.join(ROOT, "export", "animations"))) - {f"ASTRA_R08_{c['name']}.fbx" for c in anims["clips"]})
    assert not extra, f"stale clip files in export/animations: {extra}"
    # textures
    for f in sorted(os.listdir(os.path.join(ROOT, "textures"))):
        if f.endswith(".png"):
            copy(os.path.join(ROOT, "textures", f), os.path.join(PKG, "textures", f))
    for f in sorted(os.listdir(os.path.join(ROOT, "textures", "uv"))):
        if f.endswith("_UV_layout.png"):            # the layouts; the over-colour versions stay in the repository
            copy(os.path.join(ROOT, "textures", "uv", f), os.path.join(PKG, "textures", "uv", f))
    for f in sorted(os.listdir(os.path.join(ROOT, "textures", "source"))):
        copy(os.path.join(ROOT, "textures", "source", f), os.path.join(PKG, "textures", "source_2048", f))
    # the .blend
    blend = package_blend()
    assert blend["images_ok"], blend["images"]
    assert len(blend["actions"]) == len(anims["clips"]) and blend["bones"] == 27, blend
    log("blend saved and re-read:", blend["file"], f"{len(blend['images'])} maps load, {len(blend['actions'])} clips")
    # rig
    md, csv = bone_docs(rig, weights)
    os.makedirs(os.path.join(PKG, "rig"))
    open(os.path.join(PKG, "rig", "BONES.md"), "w").write(md)
    open(os.path.join(PKG, "rig", "bones.csv"), "w").write(csv)
    copy(os.path.join(ROOT, "docs", "ASTRA_R08_rig_reference.png"), os.path.join(PKG, "rig", "ASTRA_R08_rig_reference.png"))
    # Roblox scripts
    mod = open(os.path.join(ROOT, "roblox", "AstraR08.lua")).read()
    test = open(os.path.join(ROOT, "roblox", "AstraR08_Test.server.lua")).read()
    from luaparser import ast as lua_ast
    lua_ast.parse(mod)
    lua_ast.parse(test)
    copy(os.path.join(ROOT, "roblox", "AstraR08.lua"), os.path.join(PKG, "roblox", "AstraR08.lua"))
    copy(os.path.join(ROOT, "roblox", "AstraR08_Test.server.lua"), os.path.join(PKG, "roblox", "AstraR08_Test.server.lua"))
    x = rbxmx(mod, test)
    import xml.etree.ElementTree as ET
    tree = ET.fromstring(x)
    srcs = [p.text for p in tree.iter("ProtectedString")]
    assert srcs == [mod, test], "rbxmx does not round-trip the script sources"
    open(os.path.join(PKG, "roblox", "ASTRA_R08_Scripts.rbxmx"), "w").write(x)
    # checks and previews
    copy(os.path.join(ROOT, "docs", "FBX_VERIFICATION.md"), os.path.join(PKG, "checks", "VERIFICATION.md"))
    for f in ("fbx_verification.json", "game_deformation.json", "game_weights.json", "game_animations.json", "game_rig.json"):
        copy(os.path.join(AN, f), os.path.join(PKG, "checks", f))
    for src in ("renders/game/ASTRA_R08_game_poses.png", "renders/game/ASTRA_R08_deformation_test.mp4",
                "renders/game/ASTRA_R08_game_vs_highdetail.png"):
        copy(os.path.join(ROOT, src), os.path.join(PKG, "previews", os.path.basename(src)))
    # README
    open(os.path.join(PKG, "README.md"), "w").write(readme(V, anims, weights, blend, rig))
    # manifest
    files = []
    for d, _, fs in os.walk(PKG):
        for f in sorted(fs):
            p = os.path.join(d, f)
            files.append((os.path.relpath(p, PKG), os.path.getsize(p), sha256(p)))
    files.sort()
    lines = ["ASTRA R08 - Roblox Studio handoff package: files, sizes, SHA-256", ""]
    lines += [f"{s:>11,}  {h}  {r}" for r, s, h in files]
    open(os.path.join(PKG, "MANIFEST.txt"), "w").write("\n".join(lines) + "\n")
    # zip (without the 2048 masters, which stay in the folder)
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(PKG):
            for f in sorted(fs):
                p = os.path.join(d, f)
                r = os.path.relpath(p, PKG)
                if r.startswith(os.path.join("textures", "source_2048")):
                    continue
                z.write(p, os.path.join("ASTRA_R08_Roblox", r))
    with zipfile.ZipFile(ZIP) as z:
        bad = z.testzip()
        n = len(z.namelist())
    assert bad is None
    # the package's copies must be the verified files
    for r, s, h in files:
        if r.endswith(".fbx"):
            src = os.path.join(ROOT, "export", r) if "/" in r else os.path.join(ROOT, "export", r)
            assert sha256(src) == h, f"{r} differs from the verified export"
    report = dict(package=os.path.relpath(PKG, ROOT), files=len(files), zip=os.path.relpath(ZIP, ROOT), zip_files=n,
                  zip_mb=round(os.path.getsize(ZIP) / 1e6, 1), folder_mb=round(sum(s for _, s, _ in files) / 1e6, 1),
                  blend=blend, fbx_checks=f"{sum(c['passed'] for c in V['checks'])}/{len(V['checks'])}")
    json.dump(report, open(os.path.join(PKG, "checks", "package.json"), "w"), indent=1)
    log(f"package: {len(files)} files, {report['folder_mb']} MB; zip {n} files, {report['zip_mb']} MB  ({time.time() - t0:.1f} s)")


if __name__ == "__main__":
    main()
