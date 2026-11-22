# ASTRA R08 - Roblox Studio handoff

Everything needed to bring the ASTRA R08 monster into Roblox Studio as an animated enemy: the
game-ready mesh, its 27-bone skeleton and skinning, textures, eleven animation clips (each in its own
FBX, all on the same skeleton and bind pose), an independently animated jaw, the bone list, a
controller script and a test script.

**Status:** every file was exported from Blender with the settings in Roblox's Blender guide and
verified in Blender (116 of 116 checks passed - below and in `checks/VERIFICATION.md`).  The
package has **not** been opened in Roblox Studio: Studio does not run where it was built.  The steps
below follow Roblox's documentation; the test script in step 4 is the quickest way to see that
everything arrived.

## Contents

| Path | What it is |
|---|---|
| `ASTRA_R08.fbx` | The character: meshes `ASTRA_R08_Body` (9,852 triangles), `ASTRA_R08_Head` (11,082 - skull, lower jaw, 67 teeth, gums, sinews, throat) and `ASTRA_R08_Eyes` (16), skinned to one 27-bone skeleton; one material per mesh with its 1024 x 1024 maps embedded; rest pose; no animation |
| `animations/` | Eleven clips, one per FBX (table below) |
| `ASTRA_R08_game.blend` | The rigged Blender project: the three meshes, the skeleton and weights, the materials (maps linked from `textures/`) and all eleven clips as actions; saved in the rest pose |
| `textures/` | `ASTRA_R08_<Body or Head>_<Color, Normal, Roughness, Metalness>.png`, 1024 x 1024 (Color / Normal 24-bit RGB, normal map OpenGL tangent space; Roughness / Metalness 8-bit grey); `uv/` UV layouts; `source_2048/` 2048 masters + albedo and ambient occlusion (folder only, not in the zip) |
| `rig/` | `BONES.md` (every bone, its parent and what it moves), `bones.csv`, `ASTRA_R08_rig_reference.png` |
| `roblox/` | `AstraR08.lua` (ModuleScript: plays the clips, layers jaw / head clips, procedural jaw and look-at), `AstraR08_Test.server.lua` (Script: plays every clip in turn), both together in `ASTRA_R08_Scripts.rbxmx` |
| `checks/` | `VERIFICATION.md` (all 116 checks with their numbers), the data behind it, deformation numbers |
| `previews/` | Pose sheet and deformation clip (MP4) of every clip, the game model beside the high-detail model |
| `MANIFEST.txt` | Every file with its size and SHA-256 |

The high-detail source model (1.13 million triangles) the maps were baked from is not part of the
package and was not changed: `experimental_02/model/astra_r08_exp02_highdetail.blend` in the repository.

## Verified before export

| Requirement | Result |
|---|---|
| Each mesh within Roblox's 20,000-triangle limit | Body 9,852 · Head 11,082 · Eyes 16 - pass |
| No vertex with more than four bone influences | most on any vertex: Body 4, Head 2, Eyes 1 - pass |
| Root bone has no vertex influences | no skin cluster for Root in the file; 0 weight on Root - pass |
| Skeleton and skinning survive FBX export | read back by two independent FBX readers (Blender's Python importer and its C++ ufbx importer): 27 bones with identical names and parents; vertex positions within 4e-06 studs; skin weights identical (largest difference 0) - pass |
| All animations use the same skeleton and bind pose | all 11 clip files: the same 27 bones and hierarchy, and default (rest) transforms equal to the character's bind pose (largest difference 0 studs, 0 degrees); the character's bind pose equals its rest skeleton (to 2e-06); each clip played from its own file on the re-imported character deforms it exactly as in Blender (largest difference 0.0 mm) - pass |
| Textures correctly linked | in the FBX each material carries its own four maps on their channels (colour on DiffuseColor, normal on NormalMap, roughness on ShininessExponent, metalness on ReflectionFactor) with the 1024 x 1024 PNGs embedded; in the .blend all 8 maps are linked from `./textures/` and load - pass |
| Root position and orientation | Root bone at the origin, pointing straight up; soles on the ground plane (lowest point Y = 0.000); faces -Z (Roblox's front); the origin lies between the feet, 0.54 studs from their centre; height 10.30 studs (2.885 m) - pass |

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
| `animations/ASTRA_R08_Idle.fbx` | Idle | 91 (3.0 s) | yes | all 27 | Idle | - | standing, breathing, small jaw movement |
| `animations/ASTRA_R08_Walk.fbx` | Walk | 31 (1.0 s) | yes | all 27 | Movement | 6.0 | walk cycle, in place |
| `animations/ASTRA_R08_Run.fbx` | Run | 19 (0.6 s) | yes | all 27 | Movement | 22.3 | run cycle, in place |
| `animations/ASTRA_R08_Chase.fbx` | Chase | 19 (0.6 s) | yes | all 27 | Movement | 25.1 | aggressive run: lower, long arm reaching, jaws snapping |
| `animations/ASTRA_R08_Attack.fbx` | Attack | 37 (1.2 s) | no | all 27 | Action | - | long-arm swipe |
| `animations/ASTRA_R08_Lunge.fbx` | Lunge | 34 (1.1 s) | no | all 27 | Action | - | bite: draw back, lunge, snap |
| `animations/ASTRA_R08_HitReact.fbx` | HitReact | 19 (0.6 s) | no | all 27 | Action2 | - | struck from the front |
| `animations/ASTRA_R08_Death.fbx` | Death | 61 (2.0 s) | no | all 27 | Action4 | - | staggers, knees give, folds forward onto the ground |
| `animations/ASTRA_R08_JawSnap.fbx` | JawSnap | 31 (1.0 s) | no | Jaw | Action3 | - | jaw only: gape, snap shut twice - layer over anything |
| `animations/ASTRA_R08_JawChatter.fbx` | JawChatter | 31 (1.0 s) | yes | Jaw | Action3 | - | jaw only, looping: restless jaw - layer over Idle or Chase |
| `animations/ASTRA_R08_HeadTrack.fbx` | HeadTrack | 103 (3.4 s) | no | Neck, Head | Action2 | - | neck and head only: look left, right, up, down - layer over anything |

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
local rig = AstraR08.new(workspace.ASTRA_R08, { Idle = "rbxassetid://...", Walk = "rbxassetid://...", ... })
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
