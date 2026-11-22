# ASTRA R08 game rig - hierarchy reference

![Rig reference](ASTRA_R08_rig_reference.png)

One armature, **27 bones**, carrying three meshes (`ASTRA_R08_Body`, `ASTRA_R08_Head`, `ASTRA_R08_Eyes`).
"Right" and "Left" are the creature's own sides (its very long arm is the right one).
Source: `src/game_rig.py`; numbers: `analysis/game_rig.json`, `analysis/game_weights.json`.

## Hierarchy

```
Root
    Pelvis
        Spine
            Chest
                Neck
                    Head
                        Jaw
                RightShoulder
                    RightUpperArm
                        RightLowerArm
                            RightWrist
                                RightHand
                LeftShoulder
                    LeftUpperArm
                        LeftLowerArm
                            LeftWrist
                                LeftHand
        RightHip
            RightUpperLeg
                RightLowerLeg
                    RightFoot
                        RightToes
        LeftHip
            LeftUpperLeg
                LeftLowerLeg
                    LeftFoot
                        LeftToes
```

## Bones

Positions are the bone's head (joint) in **studs**, in the FBX file's and Studio's frame: X = the
creature's right, Y = up, Z = backwards (the creature faces -Z, Roblox's front).  In the Blender file
the same bone sits at (-X, Z, Y) (Blender: Z up, the creature faces -Y).  "Vertices" = vertices with
any weight on the bone.

| Bone | Parent | Head position (studs) | Length (studs) | Vertices | Carries |
|---|---|---|---|---|---|
| Root | - | (-0.00, 0.00, 0.00) | 1.07 | 0 | nothing (no skin weight, as Roblox requires); top of the hierarchy, on the ground at the origin |
| Pelvis | Root | (-0.13, 4.95, -0.06) | 1.25 | 1,309 | pelvis block, groin block and the torso skin up to the waist |
| Spine | Pelvis | (-0.02, 6.00, -0.72) | 1.17 | 542 | the torso skin between waist and chest, shared with Pelvis below and Chest above |
| Chest | Spine | (-0.02, 6.91, -1.46) | 1.24 | 912 | hunched upper torso (top corners shared with the shoulders), the spikes in the back and flank |
| Neck | Chest | (-0.02, 7.50, -2.21) | 2.04 | 393 | neck block - one rigid armour segment, its base seated in the chest, its top inside the skull |
| Head | Neck | (0.04, 8.55, -3.95) | 2.35 | 4,071 | skull with its armour slabs, sockets and hinge blocks; the 32 upper teeth; upper gum; eyes |
| Jaw | Head | (0.03, 8.38, -4.66) | 2.20 | 2,337 | lower jaw, its 35 teeth and the gum band (rigidly); shares the cheek sinews, mouth webs and throat with Head |
| RightShoulder | Chest | (0.70, 7.76, -2.05) | 1.42 | 94 | part of the chest's right top corner; the long arm hangs from it (no shoulder plate on this side: the arm turns on its own rounded top) |
| RightUpperArm | RightShoulder | (2.07, 8.04, -2.29) | 3.14 | 450 | long arm, shoulder to elbow - rigid segment; its rounded top is seated in the chest's corner |
| RightLowerArm | RightUpperArm | (3.50, 5.27, -2.71) | 2.55 | 420 | long arm, elbow to forearm bend - rigid segment |
| RightWrist | RightLowerArm | (3.77, 2.98, -3.80) | 1.54 | 320 | thick forearm - rigid segment |
| RightHand | RightWrist | (3.74, 1.67, -4.60) | 1.43 | 236 | blunt hollow end resting on the floor - rigid |
| LeftShoulder | Chest | (-0.73, 7.76, -2.05) | 1.25 | 277 | left shoulder plate (rigid; the short arm's socket) and part of the chest's left top corner |
| LeftUpperArm | LeftShoulder | (-1.77, 7.64, -2.75) | 2.02 | 452 | short arm, shoulder to elbow - rigid segment; its rounded top turns inside the shoulder plate |
| LeftLowerArm | LeftUpperArm | (-2.27, 5.96, -1.75) | 1.32 | 272 | short forearm - rigid segment |
| LeftWrist | LeftLowerArm | (-2.48, 4.73, -1.34) | 0.72 | 218 | end of the short forearm - rigid segment |
| LeftHand | LeftWrist | (-2.54, 4.03, -1.48) | 0.72 | 110 | blunt end of the short arm - rigid |
| RightHip | Pelvis | (-0.13, 4.95, -0.06) | 0.80 | 308 | right hip block under the right half of the pelvis (part of the torso skin, on this bone alone) |
| RightUpperLeg | RightHip | (0.61, 4.79, -0.30) | 2.20 | 296 | right thigh - rigid segment; its rounded top turns inside the hip block |
| RightLowerLeg | RightUpperLeg | (0.80, 3.12, -1.73) | 2.54 | 324 | right shin with the knee and ankle blocks - rigid segment |
| RightFoot | RightLowerLeg | (0.86, 1.04, -0.29) | 1.46 | 304 | right foot block - rigid |
| RightToes | RightFoot | (0.93, 0.18, -1.46) | 0.61 | 102 | four right toe blocks - rigid |
| LeftHip | Pelvis | (-0.13, 4.95, -0.06) | 0.80 | 326 | left hip block under the left half of the pelvis (part of the torso skin, on this bone alone) |
| LeftUpperLeg | LeftHip | (-0.88, 4.79, 0.18) | 1.57 | 268 | left thigh - rigid segment; its rounded top turns inside the hip block |
| LeftLowerLeg | LeftUpperLeg | (-1.21, 3.27, 0.39) | 2.68 | 324 | left shin with the knee and ankle blocks - rigid segment |
| LeftFoot | LeftLowerLeg | (-1.62, 0.95, 1.66) | 1.10 | 299 | left foot block - rigid |
| LeftToes | LeftFoot | (-1.70, 0.18, 0.88) | 0.61 | 102 | four left toe blocks - rigid |

## Conventions

- **Units**: studs (1 stud = 0.28 m).  The creature stands 10.30 studs (2.885 m) tall; the soles
  rest on Y = 0 and Root sits at the origin.
- **Rest pose** = the approved sheet's stance (hunched, long right arm hanging to the floor, right
  leg striding forward).  Animations are stored as rotations from this pose.
- **Bone axes** (as authored in Blender, FBX primary axis Y, secondary X): every bone's local Y
  runs from its head to its tail; on every bone that is not itself sideways its local X points to
  the creature's left, so "rotate about X" is the forward / backward bend of that joint, "about
  Z" the sideways swing and "about Y" the twist.  The two shoulder and two hip bones run sideways;
  they keep local Z pointing up instead.
- **No leaf bones**, no IK or constraint bones: everything in the hierarchy deforms or is the root,
  so the skeleton Roblox reads is exactly this one.
- **Jaw**: its own bone, hinged at the back corners of the mouth (head at the middle of the hinge
  line, tail at the chin).  Rotating it about its X axis opens and closes the mouth; the skull does
  not move (measured: skull and lower-jaw vertices stay within 0.001 mm of rigid in every test
  clip, `analysis/game_deformation.json`).
- **Head tracking**: turn `Neck` and `Head` (about Z to look left / right, about X to look up /
  down); `HeadTrack` shows the range used in testing (head 30 degrees either side, 18-20 degrees up and down).

## Skin weights

Computed, not painted (`src/game_rig.py`, `body_weights_v2`).  The body is v2, armoured joints
(`src/game_body_v2.py`; the audit and the before / after numbers are in `RIG_AUDIT.md`):

- every limb segment is a closed rigid piece on one bone, weight 1: the left shoulder plate
  (LeftShoulder), each upper arm, forearm, second forearm and hand, each thigh, shin, foot and toe,
  and the neck.  At each joint one segment ends in a rounded knuckle seated inside its neighbour, so
  the pieces turn against each other like plates; nothing in a limb stretches or folds;
- the torso skin (torso, pelvis, hip blocks, groin) is blended: Pelvis > Spine > Chest over the
  torso's whole free height, from the top of the pelvis block to below the shoulder plates and neck
  (half linear, half smoothstep ramps along the torso axis); the chest's top corners follow the
  Shoulder bones part of the way; each hip block is on its Hip bone alone;
- the spikes move rigidly with the piece they are driven into (those in the torso with the torso
  skin where they enter it);
- at most 4 bones per vertex (body: mean 1.28; head: mean 1.12), every vertex weighted, weights
  sum to 1, nothing on Root;
- head mesh (unchanged from v1): 3,396 vertices on Head alone, 1,674 on Jaw alone, 663 shared (the sinews, webs and
  throat that must stretch when the mouth moves); eyes on Head alone.

## Animations

| Clip | Frames (30 fps) | Loops | Bones keyed | File |
|---|---|---|---|---|
| Idle | 91 | yes | all | `export/animations/ASTRA_R08_Idle.fbx` |
| Walk | 31 | yes | all | `export/animations/ASTRA_R08_Walk.fbx` |
| Run | 19 | yes | all | `export/animations/ASTRA_R08_Run.fbx` |
| Chase | 19 | yes | all | `export/animations/ASTRA_R08_Chase.fbx` |
| Attack | 37 | no | all | `export/animations/ASTRA_R08_Attack.fbx` |
| Lunge | 34 | no | all | `export/animations/ASTRA_R08_Lunge.fbx` |
| HitReact | 19 | no | all | `export/animations/ASTRA_R08_HitReact.fbx` |
| Death | 61 | no | all | `export/animations/ASTRA_R08_Death.fbx` |
| JawSnap | 31 | no | Jaw | `export/animations/ASTRA_R08_JawSnap.fbx` |
| JawChatter | 31 | yes | Jaw | `export/animations/ASTRA_R08_JawChatter.fbx` |
| HeadTrack | 103 | no | Neck, Head | `export/animations/ASTRA_R08_HeadTrack.fbx` |

All in place (no root motion), keyed every second frame in Blender and baked to every frame in
the FBX.  The v2 body plays the v1 clips unchanged (copied key for key by `src/game_clips_v2.py`; the
skeleton is the same).  The feet are planted by a two-bone solver in Walk, Run and Chase, and arms (and in Lunge
and Death the head) are laid on the floor rather than through it.  JawSnap and JawChatter key the
Jaw bone only and HeadTrack only Neck and Head, so in Roblox they play over any full-body clip and
move just those bones.  Every clip file carries the same 27 bones with the character's bind pose
as their rest transforms (checked: `FBX_VERIFICATION.md`).  The Roblox handoff package with import
steps is `../handoff/ASTRA_R08_Roblox/`.
