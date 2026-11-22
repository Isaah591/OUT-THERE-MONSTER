# ASTRA R08 - Roblox Studio handoff (v2: armoured joints)

Everything needed to bring the ASTRA R08 monster into Roblox Studio as an animated enemy: the
game-ready mesh, its 27-bone skeleton and skinning, textures, eleven animation clips (each in its own
FBX, all on the same skeleton and bind pose), an independently animated jaw, the bone list, a
controller script and a test script.

## What is new in v2

v1 (kept unchanged beside this package: `ASTRA_R08_Roblox_v1/` and `ASTRA_R08_Roblox_v1.zip`) covered
the body in one blended skin, which folded and went rubbery when a joint bent past about 30 degrees.
In v2 the joints of the game Body mesh are rebuilt the way ASTRA's armour is built:

- every limb segment - upper arm, forearm, second forearm, hand, thigh, shin, foot, toes, the left
  shoulder plate and the neck - is a **rigid closed piece that follows its own bone alone**;
- at each joint one segment ends in a rounded knuckle seated inside its neighbour, so when the joint
  bends the segments turn against each other like plates, with no crease, no stretch and no gap (the
  long right arm turns on its own rounded top, seated in the chest);
- only the torso skin bends (Pelvis / Spine / Chest), spread over its whole height between the hip
  blocks and the shoulder plates;
- the spikes ride with the piece they are driven into.

**Unchanged:** the skeleton (the same 27 bones, names, hierarchy, rest and bind pose), the eleven
clips (copied from v1 key for key - 18,784 keys, none different), the jaw
system, the Head and Eyes meshes (identical vertices and UVs), the silhouette at rest, and the
high-detail source.  Nothing in Studio is set up differently from v1.

Measured by the same audit script on both versions (`checks/rig_audit_v1.json`, `checks/rig_audit.json`):
each joint bent on its own; *clean* = no triangle turned inside out, no edge stretched more than x2,
and (v2) every pair of interlocking pieces still interlocked.

| Joint | Bone | v1 clean to (degrees) | v2 clean to (degrees) | v2 worst stretch | v2 folded triangles | v2 pieces apart |
|---|---|---|---|---|---|---|
| Right shoulder, swing fore / aft | `RightUpperArm` | +-30 | **+-120 (all tested)** | 1.00 | 0 | none |
| Right shoulder, swing out / in | `RightUpperArm` | +-30 | **+-90 (all tested)** | 1.00 | 0 | none |
| Right elbow | `RightLowerArm` | +-30 | **+-120 (all tested)** | 1.00 | 0 | none |
| Right forearm bend (RightWrist) | `RightWrist` | +-30 | **+-90 (all tested)** | 1.00 | 0 | none |
| Right hand | `RightHand` | +-30 | **+-90 (all tested)** | 1.00 | 0 | none |
| Left shoulder, swing fore / aft | `LeftUpperArm` | 0 | **+-120 (all tested)** | 1.00 | 0 | none |
| Left shoulder, swing out / in | `LeftUpperArm` | 0 | **+-90 (all tested)** | 1.00 | 0 | none |
| Left elbow | `LeftLowerArm` | +-30 | **+-120 (all tested)** | 1.00 | 0 | none |
| Left hand | `LeftHand` | +-30 | **+-90 (all tested)** | 1.00 | 0 | none |
| Right hip, swing fore / aft | `RightUpperLeg` | 0 | **+-120 (all tested)** | 1.00 | 0 | none |
| Right hip, swing out / in | `RightUpperLeg` | +0 / -20 | **+-90 (all tested)** | 1.00 | 0 | none |
| Right knee | `RightLowerLeg` | +0 / -30 | **+-120 (all tested)** | 1.00 | 0 | none |
| Right ankle | `RightFoot` | +45 / -15 | **+-45 (all tested)** | 1.00 | 0 | none |
| Left hip, swing fore / aft | `LeftUpperLeg` | 0 | **+-120 (all tested)** | 1.00 | 0 | none |
| Left hip, swing out / in | `LeftUpperLeg` | 0 | **+-90 (all tested)** | 1.00 | 0 | none |
| Left knee | `LeftLowerLeg` | +30 / -0 | **+-120 (all tested)** | 1.00 | 0 | none |
| Left ankle | `LeftFoot` | +15 / -0 | **+-45 (all tested)** | 1.00 | 0 | none |
| Spine bend | `Spine` | +45 / -30 | **+-45 (all tested)** | 1.46 | 0 | none |
| Spine twist | `Spine` | +-15 | **+-45 (all tested)** | 1.34 | 0 | none |
| Chest bend | `Chest` | +15 / -0 | **+-45 (all tested)** | 1.53 | 0 | none |
| Neck nod | `Neck` | 0 | **+-45 (all tested)** | 1.00 | 0 | none |
| Neck turn | `Neck` | 0 | **+-60 (all tested)** | 1.00 | 0 | none |
| Head nod | `Head` | +45 / -30 | **+-45 (all tested)** | 1.00 | 0 | none |
| Head turn | `Head` | +45 / -30 | **+-60 (all tested)** | 1.00 | 0 | none |
| Jaw open / shut | `Jaw` | +25 / -30 | **+25 / -30** | 1.40 | 0 | none |

Rotating a limb bone on its own moves only its own segments and the ones below it in the hierarchy
(measured for every bone); Pelvis, Spine and Chest share the torso skin, so Spine and Chest bend it
smoothly from the waist up.  The Head and Body meshes stay joined when the head and jaw move (the
neck's top is seated inside the skull; buried surfaces slide past each other by up to
16 cm, out of sight).  Interlocking pieces pass
through each other at the extremes of a pose rather than open a gap - as real armour plates would
collide, keep poses within what the creature could physically do.

**Status:** every file was exported from Blender with the settings in Roblox's Blender guide and
verified in Blender (116 of 116 checks passed - below and in `checks/VERIFICATION.md`).  The
package has **not** been opened in Roblox Studio: Studio does not run where it was built.  The steps
below follow Roblox's documentation; the test script in step 4 is the quickest way to see that
everything arrived.

## Contents

| Path | What it is |
|---|---|
| `ASTRA_R08.fbx` | The character: meshes `ASTRA_R08_Body` (13,386 triangles), `ASTRA_R08_Head` (11,082 - skull, lower jaw, 67 teeth, gums, sinews, throat) and `ASTRA_R08_Eyes` (16), skinned to one 27-bone skeleton; one material per mesh with its 1024 x 1024 maps embedded; rest pose; no animation |
| `animations/` | Eleven clips, one per FBX (table below) |
| `ASTRA_R08_game.blend` | The rigged Blender project: the three meshes, the skeleton and weights, the materials (maps linked from `textures/`) and all eleven clips as actions; saved in the rest pose |
| `textures/` | `ASTRA_R08_<Body or Head>_<Color, Normal, Roughness, Metalness>.png`, 1024 x 1024 (Color / Normal 24-bit RGB, normal map OpenGL tangent space; Roughness / Metalness 8-bit grey); `uv/` UV layouts; `source_2048/` 2048 masters + albedo and ambient occlusion (folder only, not in the zip) |
| `rig/` | `BONES.md` (every bone, its parent and what it moves), `bones.csv`, `ASTRA_R08_rig_reference.png` |
| `roblox/` | `AstraR08.lua` (ModuleScript: plays the clips, layers jaw / head clips, procedural jaw and look-at), `AstraR08_Test.server.lua` (Script: plays every clip in turn), both together in `ASTRA_R08_Scripts.rbxmx` |
| `checks/` | `VERIFICATION.md` (all 116 checks with their numbers), the data behind it, deformation numbers, the articulation audit of v1 and v2 (`rig_audit_v1.json`, `rig_audit.json`), the clip carry-over check (`game_clips_v2.json`) |
| `previews/` | Pose sheet and deformation clip (MP4) of every clip, the game model beside the high-detail model, deep joint bends v1 against v2, the bone-influence map and isolated joint bends of v2 |
| `MANIFEST.txt` | Every file with its size and SHA-256 |

The high-detail source model (1.13 million triangles) the maps were baked from is not part of the
package and was not changed: `experimental_02/model/astra_r08_exp02_highdetail.blend` in the repository.

## Verified before export

| Requirement | Result |
|---|---|
| Each mesh within Roblox's 20,000-triangle limit | Body 13,386 · Head 11,082 · Eyes 16 - pass |
| No vertex with more than four bone influences | most on any vertex: Body 4, Head 2, Eyes 1 - pass |
| Root bone has no vertex influences | no skin cluster for Root in the file; 0 weight on Root - pass |
| Skeleton and skinning survive FBX export | read back by two independent FBX readers (Blender's Python importer and its C++ ufbx importer): 27 bones with identical names and parents; vertex positions within 4e-06 studs; skin weights identical (largest difference 0) - pass |
| All animations use the same skeleton and bind pose | all 11 clip files: the same 27 bones and hierarchy, and default (rest) transforms equal to the character's bind pose (largest difference 0 studs, 0 degrees); the character's bind pose equals its rest skeleton (to 2e-06); each clip played from its own file on the re-imported character deforms it exactly as in Blender (largest difference 0.0 mm) - pass |
| Textures correctly linked | in the FBX each material carries its own four maps on their channels (colour on DiffuseColor, normal on NormalMap, roughness on ShininessExponent, metalness on ReflectionFactor) with the 1024 x 1024 PNGs embedded; in the .blend all 8 maps are linked from `./textures/` and load - pass |
| Root position and orientation | Root bone at the origin, pointing straight up; soles on the ground plane (lowest point Y = 0.000); faces -Z (Roblox's front); the origin lies between the feet, 0.41 studs from their centre; height 10.30 studs (2.885 m) - pass |

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

## Posing it in the Animation Editor

Every section has its own bone - each upper arm, forearm, hand, thigh, shin and foot, the pelvis,
the torso, the head and the jaw - and the Animation Editor poses bones directly ("for bones, you
can rotate them to pose the rig" - Roblox Creator docs).

1. Select the ASTRA_R08 model and open the **Animation Editor** (Avatar tab).
2. Bones show while the Animation Editor is open (or with **View > Show Constraint Details**).  Click
   a bone's joint in the viewport, or select the `Bone` in the Explorer (inside the model's MeshPart:
   Root > Pelvis > Spine > Chest > ...).
3. Rotate it (rotate tool).  A track for that bone appears in the track list.
4. R15 equivalents: Pelvis ~ LowerTorso (root joint), Spine / Chest ~ UpperTorso (waist),
   RightUpperArm ~ shoulder, RightLowerArm ~ elbow, RightHand ~ wrist, RightUpperLeg ~ hip,
   RightLowerLeg ~ knee, RightFoot ~ ankle.  ASTRA adds RightWrist (a second forearm joint for the
   long arm), the Shoulder and Hip bones (the chest's top corners and the left shoulder plate / the hip
   blocks), Toes, Neck and Jaw.
5. Rotating **Pelvis** moves the whole body; to tilt the hips with the feet planted, counter-rotate the
   UpperLeg bones.  **RightHip / LeftHip** swing the whole leg about the pelvis centre; use **UpperLeg**
   for normal hip bending.  Forward posing (bone by bone) is the documented way; Roblox does not say
   whether its IK works on bone rigs.

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
