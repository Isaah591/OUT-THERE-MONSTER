# ASTRA R08 - rig articulation audit

> **Update - option A has been built (v2).**  Sections 1-7 are the audit of v1 as it was written,
> before anything changed; section 8 has the result, measured with the same script.  v1 is kept:
> `handoff/ASTRA_R08_Roblox_v1/` (+ `.zip`) and `model/astra_r08_exp02_game_v1.blend`.  The v1
> numbers are now `analysis/rig_audit_v1.json` (re-measured with the extended script, same values for
> everything sections 1-7 report) and the v1 pictures `renders/audit_v1/`.

**Audit only - nothing was changed.**  The game model was opened read-only by
`src/rig_audit.py`; every pose was set on an in-memory copy and never saved.  SHA-256 before and
after the audit (identical):

| File | SHA-256 |
|---|---|
| `model/astra_r08_exp02_game.blend` | `f76e772e9fe58445f9275ad238597b52bd4b8e185a62b13d73d956dc45893329` |
| `model/astra_r08_exp02_highdetail.blend` | `d9c9f9e51cfa888a295a5ff06bde301af956450568c3969e4735989e20bbee4b` |
| `handoff/ASTRA_R08_Roblox/ASTRA_R08.fbx` | `0a4fa2fd0affddf25f2c691f9bec7e7f4d01ed11a8d8839a406ca3bec5c78f99` |

Numbers: `analysis/rig_audit_v1.json`.  Pictures: `renders/audit_v1/`.

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
knees, shoulders and hips (`renders/audit_v1/ASTRA_R08_deep_bends.png`).

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

## Pictures (v1)

- `renders/audit_v1/ASTRA_R08_bone_influence_map.png` - colour = the bone that moves each part.
- `renders/audit_v1/ASTRA_R08_isolated_joints.png` - each joint bent on its own.
- `renders/audit_v1/ASTRA_R08_deep_bends.png` - elbows, knees, shoulders and hips bent deep, beside rest.

## 8. Result: option A built (v2)

Decision: **A** ("go with option a, keep the backups and proceed").

**Backups, made before any change** (commit `7ef3a75`), unchanged since:

| File | SHA-256 |
|---|---|
| `model/astra_r08_exp02_game_v1.blend` (the v1 game file) | `f76e772e9fe58445f9275ad238597b52bd4b8e185a62b13d73d956dc45893329` |
| `handoff/ASTRA_R08_Roblox_v1/ASTRA_R08.fbx` (in the v1 package as delivered) | `0a4fa2fd0affddf25f2c691f9bec7e7f4d01ed11a8d8839a406ca3bec5c78f99` |
| `handoff/ASTRA_R08_Roblox_v1.zip` | `81bc601e89bb0fa0c3bad1a1a5ce0333f7c0163fef6dec34042b27c2bce8697c` |
| `model/astra_r08_exp02_highdetail.blend` (high-detail source - not touched) | `d9c9f9e51cfa888a295a5ff06bde301af956450568c3969e4735989e20bbee4b` |

v2 is the current build: `model/astra_r08_exp02_game.blend`, `export/`, `handoff/ASTRA_R08_Roblox/` (+ `.zip`).

### What changed - the game Body mesh only (`src/game_body_v2.py`)

- **Limbs are rigid armour segments.**  Each arm and leg is cut at every joint pivot from the same
  loft as before: upper arm, forearm, second forearm, hand; thigh, shin (with knee and ankle blocks),
  foot, four toes; and the neck.  Each segment is a closed piece that follows its own bone alone
  (weight 1), so a limb can no longer stretch, crease or go rubbery.
- **Rounded knuckles.**  At each joint one segment ends in a rounded knuckle centred on the pivot,
  seated inside its neighbour and fitted so it stays hidden at rest - the outline at rest is
  unchanged.  When the joint bends the segments turn against each other like plates.
- **Shoulders.**  The short left arm keeps its shoulder block as a plate on `LeftShoulder`, a socket the
  upper arm turns in.  On the long right arm only a 5 cm collar stood between the chest and the
  joint: left on `RightShoulder` it stood out as a blade when the arm swung, so it is gone, and the
  arm's own rounded top takes its place.
- **The torso skin** (torso, pelvis, hip blocks, groin) is still one blended skin.  Each hip block is
  on its Hip bone alone.  Pelvis / Spine / Chest are now spread over the torso's whole free height,
  between the top of the pelvis block and the shoulder plates and neck (v1: two 28 cm bands).  The
  spikes driven into it are separate pieces that move with the skin where they enter it.
- **Surface.**  No armour relief on faces buried inside a neighbour at rest, faded near other pieces.
  The texture of the buried knuckles and end caps that a bend turns into view is refilled from the
  visible armour of the same piece, where the bake had caught the dark inside of the high-detail blocks.
- **Unchanged:** the skeleton (27 bones, names, hierarchy, rest and bind pose - checked equal), the
  eleven clips (copied from v1, not re-keyed: 928 curves, 18,784 keys, every one identical -
  `src/game_clips_v2.py`, `analysis/game_clips_v2.json`), the jaw bone and jaw clips, the Head and Eyes
  meshes (identical vertices and UVs) and their textures (byte-identical), the high-detail source.
- Triangles: Body 13,386 (v1 9,852), Head 11,082, Eyes 16 - each under 20,000.

### Measured - the same script, v1 against v2

`analysis/rig_audit_v1.json` and `analysis/rig_audit.json`.  The script gained one test for v2
(section 6 of its header).  It checks every joint between two pieces that interlock at rest (23 of
them), and passes if they still interlock at the angle tested.  A pair that came apart would be a gap you could see
through.  Hip side-swing is now tested to 90.  *Clean* = no folded triangle, no edge stretched more than
x2, no joint apart.

| Joint | Bone | v1 clean to | v1 worst (stretch / folded) | v2 clean to | v2 worst stretch | v2 folded | v2 pieces apart |
|---|---|---|---|---|---|---|---|
| Right shoulder, fore / aft | `RightUpperArm` | +-30 | 2.90 / 26 | **+-120** | 1.00 | 0 | none |
| Right shoulder, out / in | `RightUpperArm` | +-30 | 2.02 / 17 | **+-90** | 1.00 | 0 | none |
| Right elbow | `RightLowerArm` | +-30 | 2.60 / 27 | **+-120** | 1.00 | 0 | none |
| Right forearm bend | `RightWrist` | +-30 | 2.70 / 29 | **+-90** | 1.00 | 0 | none |
| Right hand | `RightHand` | +-30 | 2.88 / 24 | **+-90** | 1.00 | 0 | none |
| Left shoulder, fore / aft | `LeftUpperArm` | 0 (slivers) | 2.50 / 30 | **+-120** | 1.00 | 0 | none |
| Left shoulder, out / in | `LeftUpperArm` | 0 (slivers) | 2.26 / 21 | **+-90** | 1.00 | 0 | none |
| Left elbow | `LeftLowerArm` | +-30 | 3.05 / 23 | **+-120** | 1.00 | 0 | none |
| Left hand | `LeftHand` | +-30 | 2.89 / 27 | **+-90** | 1.00 | 0 | none |
| Right hip, fore / aft | `RightUpperLeg` | 0 (slivers) | 2.78 / 74 | **+-120** | 1.00 | 0 | none |
| Right hip, out / in | `RightUpperLeg` | +0 / -20 | 2.36 / 49 | **+-90** | 1.00 | 0 | none |
| Right knee | `RightLowerLeg` | +0 / -30 | 2.55 / 44 | **+-120** | 1.00 | 0 | none |
| Right ankle | `RightFoot` | +45 / -15 | 1.40 / 6 | **+-45** | 1.00 | 0 | none |
| Left hip, fore / aft | `LeftUpperLeg` | 0 (slivers) | 2.21 / 67 | **+-120** | 1.00 | 0 | none |
| Left hip, out / in | `LeftUpperLeg` | 0 (slivers) | 1.86 / 45 | **+-90** | 1.00 | 0 | none |
| Left knee | `LeftLowerLeg` | +30 / -0 | 1.80 / 37 | **+-120** | 1.00 | 0 | none |
| Left ankle | `LeftFoot` | +15 / -0 | 1.52 / 18 | **+-45** | 1.00 | 0 | none |
| Spine bend | `Spine` | +45 / -30 | 1.84 / 1 | **+-45** | 1.46 | 0 | none |
| Spine twist | `Spine` | +-15 | 2.08 / 5 | **+-45** | 1.34 | 0 | none |
| Chest bend | `Chest` | +15 / -0 | 2.07 / 21 | **+-45** | 1.53 | 0 | none |
| Neck nod | `Neck` | 0 (slivers) | 2.22 / 19 | **+-45** | 1.00 | 0 | none |
| Neck turn | `Neck` | 0 (slivers) | 2.40 / 34 | **+-60** | 1.00 | 0 | none |
| Head nod | `Head` | +45 / -30 | 1.99 / 3 | **+-45** | 1.00 | 0 | none |
| Head turn | `Head` | +45 / -30 | 2.18 / 13 | **+-60** | 1.00 | 0 | none |
| Jaw open / shut | `Jaw` | +25 / -30 | 1.40 / 0 | **+25 / -30** | 1.40 | 0 | none |

Every v2 range is clean to the largest angle tested (the jaw's test range is its useful range).

| Target set before building | v2 |
|---|---|
| Elbows and knees fold-free to 120 degrees | all four clean to +-120: no fold, no stretch (rigid segments), no gap |
| Shoulders and hips to 90 | fore / aft clean to +-120, out / in to +-90 |
| Neck +-45, spine +-45 | neck nod +-45, turn +-60; spine bend and twist +-45; chest bend +-45 |
| Stretch at most 1.6 | joints: worst 1.53 (chest bent 45); limbs 1.00.  Clips (largest edge stretch over every frame): Idle 1.07, Walk 1.09, Run 1.18, Chase 1.28, Attack 1.57, Lunge 1.29, HitReact 1.21, Death 1.56, JawSnap 1.32, JawChatter 1.16, HeadTrack 1.00 (v1: up to 2.39 in Attack) |
| No gaps | all 23 joints between pieces stay interlocked at every tested angle; Head and Body stay joined (the neck's top is seated in the skull; buried surfaces slide by up to 16 cm, out of sight) |
| Each mesh under 20,000 triangles | Body 13,386, Head 11,082, Eyes 16 |
| Full FBX verification re-run | 116 of 116 checks pass (`docs/FBX_VERIFICATION.md`) |
| Deformation sheet and clip re-rendered | `renders/game/ASTRA_R08_game_poses.png`, `renders/game/ASTRA_R08_deformation_test.mp4`; deep bends v1 above v2: `renders/game/ASTRA_R08_deep_bends_v1_v2.png` |

**Independence.**  The four over-wide blend zones of v1 are gone:

- Neck no longer moves the top of the left shoulder.
- The Shoulder bones no longer move the base of the neck.
- LeftUpperArm no longer moves the side of the chest.
- The UpperLeg bones no longer move the underside of the pelvis.

Every limb bone now moves its own segments and nothing else.  One wide zone is deliberate: the torso
skin is shared by Pelvis, Spine and Chest over its whole height, so a 45-degree bend spreads
instead of folding.  Colouring by the bone that carries the most labels the lower half of that skin
"Pelvis", and turning Chest 25 degrees moves that skin too (up to 5.7 cm, median 1.6 cm).  Narrower
chest bands that keep it still were tried and measured: they push the chest bend at 45 degrees to a
1.66-1.88 stretch, and one folds.

**Things to know:**

- Pieces that interlock pass through each other at the extremes of a pose rather than open a gap,
  the way real armour plates would collide: a thigh swung 90 degrees inward would pass through the
  other leg.  Keep poses to what the creature could physically do.
- Where a limb turns through its shoulder plate or hip block at a large angle, the line where the two
  surfaces cross is jagged (faceted, low-poly surfaces).  The left shoulder plate's lower edge shows
  as a seam at rest.
- A rounded knuckle or end cap that a bend turns into view is smooth, with the colour of its piece but
  without the plate detail.
- The torso is still linear-blend skinned (the only skinning Roblox has): clean to 45 degrees, it will
  start to fold well beyond.

Pictures (v2): `renders/audit/ASTRA_R08_bone_influence_map.png`, `renders/audit/ASTRA_R08_isolated_joints.png`,
`renders/game/ASTRA_R08_deep_bends_v1_v2.png`.
