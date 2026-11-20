# Bringing ASTRA R08 into Roblox Studio

The files were written to Roblox's published requirements and checked in Blender
([FBX_VERIFICATION.md](FBX_VERIFICATION.md)), but they have **not been opened in Roblox Studio**:
Studio does not run in the Linux container this model was built in.  The steps below follow
Roblox's Creator documentation (the Blender guide, the 3D Importer page, the modelling
specifications and the animation pages, read for this build).  Where the documentation leaves a
point open, it says so.

## Files

| File | What it is |
|---|---|
| `export/ASTRA_R08.fbx` | The character: meshes `ASTRA_R08_Body` (9,852 triangles), `ASTRA_R08_Head` (11,082 - skull, lower jaw, 67 teeth, gums, sinews, throat) and `ASTRA_R08_Eyes` (16), skinned to one 27-bone skeleton; one material per mesh with its 1024 x 1024 maps embedded; rest pose; no animation |
| `export/animations/ASTRA_R08_<Clip>.fbx` | One clip per file (Idle, Walk, Run, Attack, Lunge, HeadTrack, JawSnap, HitReact, Death): the skeleton and its keys, 30 fps |
| `textures/ASTRA_R08_<Body or Head>_<Color, Normal, Roughness, Metalness>.png` | The same maps as separate files (Color and Normal 24-bit RGB, normal map OpenGL tangent space; Roughness and Metalness 8-bit grey) |
| `model/astra_r08_exp02_game.blend` | The Blender file the FBX files were exported from (meshes, skeleton, materials, the nine clips as actions) |

How the files were written (Roblox's Blender guide): Unit System *None*, Apply Scalings *FBX Unit
Scale*, Forward *Z Forward*, Up *Y Up*, Path Mode *Copy* with *Embed Textures*, *Add Leaf Bones*
off, *Bake Animation* only in the clip files.  One file unit is one stud.

## 1. Import the character

1. In Studio open the 3D Importer (*Import 3D*) and choose `export/ASTRA_R08.fbx`.
2. Settings:
   - **Rig General > Rig Type: Custom.**  This is not an R15 rig; it has its own 27 bones.
   - **File Geometry > Scale Unit: Stud** (the default) - the file is authored in studs, as the
     Blender guide asks.  The creature should arrive **10.3 studs tall** (2.885 m at 0.28 m a stud).
   - **File Transform > World Forward: Front, World Up: Top** (the defaults).  The creature
     should face the model's front (-Z).
   - **Keep Zero Influence Bones: on.**  Root deliberately carries no weight (Roblox's rule for the
     root bone), and with this off the importer may drop zero-influence bones; the clips key Root too.
   - **Merge Meshes: off** (keep the three meshes; they share the skeleton).  *Set Pivot to Scene
     Origin* and *Import Only As Model*: on (the defaults).
3. Expect a Model holding three MeshParts and the bone hierarchy listed in
   [RIG_HIERARCHY.md](RIG_HIERARCHY.md).  Check: the rust colour, the dents of the normal map and
   the long ivory teeth should be visible; the jaw should hang open as on the approved sheet.

**Textures.**  The documentation says the importer takes "basic and PBR textures" from an FBX but
does not say exactly which FBX material channels it reads.  If a MeshPart arrives without its
SurfaceAppearance or with a map missing, add a `SurfaceAppearance` to `ASTRA_R08_Body` and to
`ASTRA_R08_Head` and give it the four PNGs from `textures/` (ColorMap, NormalMap, RoughnessMap,
MetalnessMap).

**Eyes.**  `ASTRA_R08_Eyes` is two tiny red points deep in the sockets.  Make them glow by setting
that MeshPart's Material to *Neon* and its Color to a deep red (about 255, 16, 2).

**Size.**  At 10.3 studs the creature is about twice the height of a default avatar, as on the
sheet (2.8 m).  To change it, scale the whole Model with `Model:ScaleTo(...)` rather than resizing
parts, so the skeleton scales with the meshes.

## 2. Import the animations

1. Select the imported rig, open the Animation Editor (Avatar tab; the current docs call it the
   Clip Editor), then the **...** menu > **Import** > **From FBX Animation**, and pick one file
   from `export/animations/`.  Each file holds one clip, named after the clip; bone names match
   the character exactly.
2. Turn **Looping** on for Idle, Walk and Run (they are built as seamless loops: last frame =
   first frame).
3. Publish each clip to get its animation ID.  Suggested priorities: Idle - *Idle*; Walk, Run -
   *Movement*; Attack, Lunge, JawSnap, HitReact, HeadTrack - *Action*; Death - *Action4*.

The clips are in place (no root motion), 30 fps (Roblox animations run at 30 fps).  The
documentation does not say whether a clip file must also contain the mesh; these hold only the
skeleton and its keys, the usual form for an animation-only FBX.  If Studio refuses one, the
Blender file holds every clip as an action and `src/game_export.py` can export them again.

## 3. Play them in a game

A rig that is not an R15 humanoid needs an `AnimationController` with an `Animator` inside it
(Roblox's animation docs).  A minimal example, to adapt:

```lua
local model = workspace.ASTRA_R08            -- the imported Model
local controller = model:FindFirstChildOfClass("AnimationController") or Instance.new("AnimationController")
controller.Parent = model
local animator = controller:FindFirstChildOfClass("Animator") or Instance.new("Animator")
animator.Parent = controller

local walk = Instance.new("Animation")
walk.AnimationId = "rbxassetid://0000000000"  -- the published Walk clip
local track = animator:LoadAnimation(walk)
track.Looped = true
track:Play()
```

Movement, pathfinding and hit detection are game-specific and not part of this build.  Two notes:
skinned MeshParts collide with their rest shape, so use simple invisible parts as hitboxes; and
for head tracking at run time, turn the `Neck` and `Head` bones toward the target (about their
up axis to look sideways, about their side axis to look up and down) on top of the playing clip.

## 4. What to look at once it is in Studio

- Height about 10.3 studs; facing the model's front; feet on the ground plane.
- 27 bones (Root, Pelvis, Spine, Chest, Neck, Head, Jaw, five per arm, five per leg).
- Play JawSnap: only the lower jaw, its teeth and gum move; the skull stays still.
- Play Walk and Run: the feet plant; Attack: the long right arm swings across the front.
- Death ends with the creature folded forward on the ground.

If any of these fails, the measurements in [FBX_VERIFICATION.md](FBX_VERIFICATION.md) and the
Blender file give everything needed to find out why.
