# ASTRA R08 - rig articulation audit

**Audit only - nothing was changed.**  The game model was opened read-only by
`src/rig_audit.py`; every pose was set on an in-memory copy and never saved.  SHA-256 before and
after the audit (identical):

| File | SHA-256 |
|---|---|
| `model/astra_r08_exp02_game.blend` | `f76e772e9fe58445f9275ad238597b52bd4b8e185a62b13d73d956dc45893329` |
| `model/astra_r08_exp02_highdetail.blend` | `d9c9f9e51cfa888a295a5ff06bde301af956450568c3969e4735989e20bbee4b` |
| `handoff/ASTRA_R08_Roblox/ASTRA_R08.fbx` | `0a4fa2fd0affddf25f2c691f9bec7e7f4d01ed11a8d8839a406ca3bec5c78f99` |

Numbers: `analysis/rig_audit.json`.  Pictures: `renders/audit/`.

## 1. Short answer

**Every articulation asked for already exists as its own bone.**  The three MeshParts (Body, Head,
Eyes) are not three rigid pieces: they are skins on one 27-bone skeleton, and Roblox Studio's
Animation Editor poses the bones themselves ("In the 3D viewport or the Explorer window, select a
bone or mesh ... For bones, you can rotate them to pose the rig along the created bone joints" -
Roblox Creator docs, *animation/editor.md*).  Rotating a bone moves only its own body section, the
sections below it in the hierarchy, and a short blend zone at its joint - measured for every bone,
nothing unrelated moves.  No separate MeshParts are needed to pose individual limbs.

**What the current rig does not do well is bend far.**  The joints bend cleanly to about +-30 degrees
(spine, head and jaw further), which covers most of the eleven clips; the attack swing already takes
the right shoulder to 72 degrees, which is where the armpit stretch reported earlier comes from.
Bent further - elbows and knees to 90-120 degrees, shoulders and hips to 60-90 - the skin creases and
folds on the inside of the joint and the blocky limbs go rubbery (pictures below).  That is the part worth improving, and it can be improved without
touching the skeleton, so the eleven clips and the jaw system stay valid.

## 2. Requested functions and the bones that provide them

| Asked for | Bone(s) | Pivot | Moves (measured, bone rotated on its own) |
|---|---|---|---|
| Right upper arm | `RightUpperArm` (shoulder joint); `RightShoulder` is the clavicle above it | top of the long arm, inside the shoulder block | right upper arm, forearm, hand; blends into the right shoulder block |
| Right forearm | `RightLowerArm` (elbow) + `RightWrist` (second forearm joint, for the very long arm) | elbow; mid-forearm | right forearm and hand |
| Right hand | `RightHand` | wrist | the blunt, hollow arm end |
| Left upper arm / forearm / hand | `LeftUpperArm`, `LeftLowerArm` + `LeftWrist`, `LeftHand` (+ `LeftShoulder`) | as on the right | the short left arm, section by section |
| Right / left upper leg | `RightUpperLeg`, `LeftUpperLeg` (hip joint); `RightHip` / `LeftHip` hold the hip blocks | hip joint, under each half of the pelvis | thigh, shin, foot; blends into the hip block |
| Right / left lower leg | `RightLowerLeg`, `LeftLowerLeg` (knee) | knee | shin, ankle block, foot |
| Right / left foot | `RightFoot` (ankle) + `RightToes`; `LeftFoot` + `LeftToes` | ankle; ball of the foot | foot block; toes |
| Pelvis | `Pelvis` | centre of the pelvis | the whole body above Root (it is the parent of torso and legs, as LowerTorso is on an R15 rig) |
| Torso | `Spine`, `Chest` | lower back; upper back | everything above: chest, shoulders, arms, neck, head |
| Head | `Neck`, `Head` | base of the neck; base of the skull | neck and head; the head alone |
| Lower jaw | `Jaw` | the hinge line | lower jaw, 35 lower teeth and gum only - skull rigid to 0.001 mm |
| Shoulder / elbow / hip / knee articulation | the joints between the bones above | all 24 joint pivots lie inside the limb they bend (checked) | - |

The asymmetric anatomy is in the skeleton itself: the right arm's four segments are 3.14 / 2.55 /
1.54 / 1.43 studs, the left arm's 2.02 / 1.32 / 0.72 / 0.72; each leg's joints sit where that leg
stands (right leg striding forward, left trailing).  Nothing in the rig is mirrored.

## 3. How to pose it in Studio now

1. Select the ASTRA_R08 model and open the **Animation Editor** (Avatar tab).
2. Bones show while the Animation Editor is open (or with **View > Show Constraint Details**).
   Click a bone's joint in the viewport, or select the `Bone` in the Explorer (inside the model's
   MeshPart: Root > Pelvis > Spine > Chest > ...).
3. Rotate it (rotate tool).  A track for that bone appears in the track list.
4. R15 equivalents, for animators used to them: Pelvis ~ LowerTorso (root joint), Spine/Chest ~
   UpperTorso (waist), RightUpperArm ~ shoulder, RightLowerArm ~ elbow, RightHand ~ wrist,
   RightUpperLeg ~ hip, RightLowerLeg ~ knee, RightFoot ~ ankle.  ASTRA adds RightWrist (a second
   forearm joint for the long arm), the Shoulder and Hip bones (clavicle / hip block), Toes, Neck and Jaw.
5. Things to know:
   - Rotating **Pelvis** moves the whole body; to tilt the hips with the feet planted, counter-rotate
     the UpperLeg bones (as with LowerTorso on R15).
   - **RightHip / LeftHip** run from the pelvis centre out to each hip joint and swing the whole leg
     about the pelvis centre; use **UpperLeg** for normal hip bending.
   - Roblox documents Animation Editor IK ("Manage IK") without saying whether it works on bone rigs;
     forward posing (bone by bone) is the documented way.
   - Until the joints are improved, stay within the clean ranges below.

## 4. Measurements

### Independence (each bone rotated 25 degrees on its own)

Every bone moves its own section, the sections below it, and the blend zone at its own joint.
Sections elsewhere on the body never move.  Four blend zones reach a little further than they should
(a few cm into a neighbouring section): Neck into the top of the left shoulder, the Shoulder bones
into the base of the neck, LeftUpperArm into the side of the chest, and each UpperLeg into the
underside of the pelvis block.

### Joint range (each joint bent on its own; "fold-free" = no triangle turned inside out, both directions)

| Joint | Bone | Fold-free | Folding at |
|---|---|---|---|
| Right shoulder, swing fore / aft | RightUpperArm | +-30 | 60 (10-12 triangles), 90 (20+) |
| Right shoulder, swing out / in | RightUpperArm | +-30 | 60 |
| Right elbow | RightLowerArm | 60 bending, 30 back | 90 bending (9), 60 back (15) |
| Right forearm, hand | RightWrist, RightHand | +-30 | 60 |
| Left shoulder | LeftUpperArm | slivers flip from 30 | 60 (7-9), 90 (20) |
| Left elbow | LeftLowerArm | +-30 | 60 |
| Right hip | RightUpperLeg | slivers flip from 20-30 | 60 (11-23), 90 (32-56) |
| Right knee | RightLowerLeg | 60 one way; slivers from 30 bending | 90-120 bending (20-44) |
| Left hip | LeftUpperLeg | slivers from 20-30 | 60 (12-25) |
| Left knee | LeftLowerLeg | 30 (60 with 1 sliver) | 90 (12), 120 (37) |
| Ankles | RightFoot, LeftFoot | 15-45 | 30-45 |
| Spine bend / twist | Spine | 30-45 bend, 15 twist | 45, 30 |
| Chest bend | Chest | 15 | 30 |
| Neck nod / turn | Neck | slivers from 15 | 45 (10-34) |
| Head nod / turn | Head | 30-45 | 45-60 |
| Jaw | Jaw | full range, -30 to +25 | none |

"Slivers" are one to five tiny triangles left where the body's blocks were united; they flip early
but are not visible at normal distance.  Visible creasing starts around 60 degrees at the elbows,
knees, shoulders and hips (`renders/audit/ASTRA_R08_deep_bends.png`).

### Head and neck

No gap opens between the Head and Body meshes when the head turns 45 degrees, nods 40 or the neck
turns 45 (rendered from behind and from the side).  Surfaces buried inside the skull slide past
each other there (up to 14 cm), out of sight.

## 5. Why deep bends fold

1. **Topology.**  The game body is the blocks of the design united into one skin on a 6.8 cm grid.
   Where two blocks meet at a joint (thigh into hip block, shin's knee block into the thigh, arm into
   the shoulder) the union leaves irregular triangles and only one to three edge loops across the
   bend - too few for a deep fold to stay clean.
2. **Weights.**  Each joint blends its two bones over a fixed band with a smooth ramp.  That suits
   about +-30 degrees; past it, the inner side of the bend collapses and the outer side stretches (linear
   blend skinning - the only kind Roblox offers - loses volume at a sharp bend).
3. **Blocky limbs.**  ASTRA's limbs are square armoured blocks, so a rubbery bend reads wrong even
   where nothing folds: the design wants plates that hinge, not tubes that curve.

## 6. Recommended approach

### A. Keep the skeleton; rebuild the joints of the game body (recommended)

- **Skeleton unchanged** - the same 27 bones, names, hierarchy, rest and bind pose, Jaw included.
  The eleven clips are bone rotations, so they play unchanged; the jaw-only and head-only clips and
  the jaw script keep working.
- **Joint construction** (game Body mesh only): continuous limb sleeves with dense, regular edge loops
  through every shoulder, elbow, wrist, hip, knee, ankle and the neck, replacing the boolean junctions
  there; section outlines unchanged, so the silhouette at rest is the same.
- **Armoured hinges** at elbows and knees (also wrists and ankles): the segments stay rigid, the bend
  is confined to a short band at the joint, and the end of the upper segment overlaps the lower one as
  an armour cuff - as ASTRA's existing knee block already does - so a deep bend reads as plates
  sliding over each other instead of a rubber crease.  Shoulders and hips get the same treatment with
  the shoulder and hip blocks as the caps.
- **Weights redone** per joint type; the four over-wide blend zones fixed.
- **Head mesh untouched** (skull, jaw, teeth, gums, eyes); **high-detail source untouched** - the body
  maps are re-baked from it by the existing bake stage, in the same style.
- **Targets**, measured with the same audit script before and after: elbows and knees fold-free to
  120 degrees, shoulders and hips to 90, neck to +-45, spine to +-45, stretch at most 1.6, no gaps;
  each mesh still under 20,000 triangles; the full FBX verification (116 checks) re-run; deformation
  sheet and clip re-rendered.
- **Backups first**: the current package is copied to `handoff/ASTRA_R08_Roblox_v1/` (and its zip)
  and the current game file to `model/astra_r08_exp02_game_v1.blend`; the new build becomes v2 beside it.

### B. Separate MeshParts per body section (only if per-part customisation is wanted)

Splitting the body into its own skinned MeshParts (torso, pelvis, each upper arm, forearm, hand,
thigh, shin, foot) adds **no articulation** - the bones already give it - but it does allow per-part
customisation in Roblox: hide a severed limb, swap or recolour one section, give one part its own
material.  If wanted, it is done after A: each cut follows a joint edge loop, the seam vertices are
shared by both sides with identical weights and normals (so no gap opens in any pose), UVs and
textures are unchanged (every part uses the same maps), and every part stays skinned to the same 27
bones, so the clips are unaffected.  Cost: more MeshParts to draw, a SurfaceAppearance on each.

### C. Rigid R15-style parts joined by Motor6Ds (not recommended)

Re-cutting ASTRA into rigid parts would open or overlap every joint when posed, break the fused
silhouette of the blocks, and need all eleven clips re-made as Motor6D animations.

## 7. Decision needed

- **A** - improve the joints, keep everything else (recommended); or
- **A + B** - also split the body into per-section MeshParts for customisation; or
- **none** - keep the rig as it is and pose within the clean ranges above.

## Pictures

- `renders/audit/ASTRA_R08_bone_influence_map.png` - colour = the bone that moves each part.
- `renders/audit/ASTRA_R08_isolated_joints.png` - each joint bent on its own.
- `renders/audit/ASTRA_R08_deep_bends.png` - elbows, knees, shoulders and hips bent deep, beside rest.
