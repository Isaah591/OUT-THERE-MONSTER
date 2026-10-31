# Importing the OUT THERE monster into Roblox Studio

Files (produced by `scripts/bake_export.py`):

```
model/roblox_export/out_there_monster_roblox.fbx
model/roblox_export/textures/<Part>_Color.png
model/roblox_export/textures/<Part>_Normal.png
model/roblox_export/textures/<Part>_Roughness.png
model/roblox_export/textures/Rods_Metalness.png
```

The FBX contains nine meshes, one per future MeshPart: `Body` (torso, neck, deltoids),
`Head` (skull, upper teeth/gums, palate, throat, hinge knuckles, mouth-corner membranes),
`Jaw` (jaw, lower teeth/gums, tongue),
`Arm_R_Long`, `Arm_L_Short`, `Leg_R`, `Leg_L`, `Rods`, `Eyes`. In v3 the largest group
(Body) is ~8.6k triangles, far under Roblox's 20k MeshPart limit, and the Head/Jaw split
keeps the hinge separately animatable.

> v3 note: the bake/export has not been run for v3 yet (held until the v3 review is
> approved). The shell is flat-shaded while tissue, gums and teeth are smooth-shaded with
> sharp fracture edges; check after import that Roblox kept that split (if everything
> looks faceted or everything looks soft, re-export with `mesh_smooth_type='OFF'`).

> **R08 high-fidelity pass:** `model/out_there_monster_r08.blend` is a dense design model
> (~2.0 M triangles; the Torso alone is ~0.5 M). It is **not** export-ready: after the design is
> approved, each part needs decimation/retopology to well under Roblox's 20k-triangle MeshPart
> limit, UVs, and baking of the attribute-driven materials (`layer`, `tear`, `tissue`, `convex`,
> `cavity`, `blood`, `socket` -> Color / Normal / Roughness / Metalness maps). The part split
> (Torso, Arm_R_Long, Arm_L_Short, Leg_R, Leg_L, Cranium + Jaw for the hinge, Bars) already
> matches the MeshPart plan below.

## Steps

1. **Avatar / 3D Importer:** in Studio use *File → Import 3D* and pick the FBX.
2. **Scale:** the model is built in metres and is about 3.0 m tall (≈ 2.55 m to the top
   of the head, the rest is the head bracket). At Roblox's real-world convention of
   0.28 m per stud that is ≈ 10.7 studs. Check the size the importer reports and set
   the import scale so the monster ends up at the height you want in-game.
   Do not trust the default blindly — verify against a default R15 rig standing next to it.
3. Import as a **Model** (not a single mesh) so each group becomes its own MeshPart.
4. **SurfaceAppearance** — for each MeshPart except `Eyes`, insert a `SurfaceAppearance`
   and upload the three matching maps:
   - `ColorMap` → `<Part>_Color.png`
   - `NormalMap` → `<Part>_Normal.png`
   - `RoughnessMap` → `<Part>_Roughness.png`
   - `MetalnessMap` → `Rods_Metalness.png` (Rods only; leave others empty = non-metal)
   Textures are 1024², the maximum SurfaceAppearance accepts.
5. **Eyes:** set `Material = Neon`, `Color = (255, 0, 0)`; no SurfaceAppearance.
6. **Collisions:** set `CollisionFidelity = Box` or `Hull` on every part (the wound
   geometry makes `Default`/`PreciseConvexDecomposition` needlessly expensive), and
   use a simple invisible hitbox Part for gameplay.
7. **Double-sided faces:** the cheek membranes and lifted shell flaps are thin; if any
   look missing from some angles enable `DoubleSided` on `Head`/limbs.

## Not done yet (needed before animation)

- **No rig.** There is no armature or skinning. Two workable routes:
  - *Rigid Motor6D rig:* split the limbs at elbows/knees (the loft paths in
    `scripts/build_monster.py` mark exactly where), import as separate MeshParts and
    connect with Motor6Ds. Closest to how the original Roblox monster was built.
  - *Skinned mesh:* add an armature in Blender (spine, neck, jaw hinge at the Jaw
    object's origin, arms, legs), weight-paint, and import as a skinned rig.
- The jaw hinge pivot is the `Jaw` object's origin in the .blend; preserve it when rigging.
- Rods are one mesh spanning several body parts; split them per limb before rigging.
