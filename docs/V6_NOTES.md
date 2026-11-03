# V6 — proportional correction from the approved sheet's three-quarter view

Target: the approved sheet's three-quarter panel (`references/r08_open_jaw_sheet_v2.webp`,
crop (500, 55, 1008, 550), 508 × 495 px) as the authority for silhouette, proportions, posture
and shape language. **New file:** `model/out_there_monster_v6.blend` (`scripts/build_v6.py`).
**Unchanged:** V5 (`model/out_there_monster_v5.blend`, md5 `c249b3159280d6db697906cdb2781dec`) and
the earlier open-jaw model (`model/out_there_monster_openjaw.blend`, md5
`42cbdae6e7354456c848d18fa06aec02`). Renders and comparison sheets: `model/renders_v6/`.

## Method

- **Camera.** The fitted three-quarter camera (`ref34`, see `docs/OPENJAW_NOTES.md`), now also as
  plain geometry in `scripts/ref34_camera.py` (world points → panel pixels, panel pixels → lines
  of sight). Renders are made at exactly twice the panel's resolution, so the sheet and the model
  share one pixel grid.
- **Reference silhouette.** `scripts/silhouette_ref34.py` separates the figure from the painted
  backdrop (the floor excluded, so the gap between the legs stays open) and compares it with the
  model's silhouette from the same camera.
- **Pose from the reference.** Each limb's centreline was read from the reference silhouette (the
  middle of its run on each row) and put back into 3D on those lines of sight
  (`scripts/body_v6.py`): the feet and the long arm's club stand on the floor exactly where the
  panel shows them; joints attached to the torso stay put; depths in between are interpolated;
  each knee sits on its own line of sight with a fixed leg length. From the camera, every limb's
  centreline therefore lies on the reference's; limb thickness was then set to the reference's
  measured widths.
- **Loop.** Rebuild → silhouette overlap per region and row-by-row limb extents → correct; eleven
  passes.

## What changed (actual geometry, V6 files only)

| Part | Change |
|---|---|
| Torso | Longer (spine 1.45 m, V5 1.29 m), pelvis 0.17 m lower; narrow waist; heavy rounded belly swelling to its left; heavier, asymmetric hunched upper back (left shoulder raised, right shoulder dropped); spine leans 41° (V5 39°). |
| Long arm | Abducted at the shoulder, then hangs almost straight down (a slight elbow) to a heavy blunt club resting on the floor; 2.50 m (V5 2.66 m). Upper arm and forearm slimmer (half-width 0.13–0.15 m, V5 0.145–0.17 m), the club heavier (0.18–0.23 m). |
| Short arm | Angled out from the high left shoulder; 1.39 m (V5 1.37 m); ends at the reference's height. |
| Legs | Bent and splayed into an uneven, unbalanced stance: the left leg planted far out to the side, the right foot turned out and forward under the body. 1.61 / 1.64 m (V5 1.55 / 1.59 m). Broad, blocky feet (0.37–0.41 m wide, short square toes) lying flat where the panel shows them. |
| Head | Not a uniform scale: the cranium is about 11 % wider with a broad, heavy brow ledge; the forehead slopes back to a flat top with broken corners and chunks; a raised knob at the back right; the back drops into the hump. More recessed chips and deep holes, larger knife facets (150 planes). Rectangular void sockets with tiny red pupils kept. |
| Mouth / jaw | Wider upper tooth row; the lower jaw is about 10 % wider, longer and thinner, with an uneven, broken rim (a chunk missing on its left, bulging on its right), skewed wider on its right side. 40 fangs (21 upper, 19 lower; V5 31), arranged asymmetrically: a dense cluster of long fangs on the jaw's right side, fewer with a gap on its left. Fuller, yellow-ochre fangs. |
| Surface | `M_V6_Rust`: each plate of the mosaic takes its own tone (charred black to orange-tan), with reddish rust regions, dark-brown regions, blackened areas, dark cracks and pits. Larger, more irregular torn regions: dark rust-brown strata over dark red flesh, brighter red streaks, black depths. |
| Presentation | `STUDIO=sheet` in `render_views.py`: a charcoal cyclorama (no horizon line), key light from the upper left front, a weak frontal fill and a rim, approximating the sheet's lighting. |

## Validation: the exact three-quarter camera

Silhouette overlap with the reference (`silhouette_ref34.py`, IoU):

| Region | V5 | V6 |
|---|---|---|
| Whole figure | 0.586 | **0.874** |
| Head and jaw | 0.878 | 0.927 |
| Torso | 0.919 | 0.932 |
| Long arm | 0.576 | 0.848 |
| Short arm | 0.671 | 0.875 |
| Legs | 0.311 | 0.848 |

Limb extents on selected rows (panel px, reference | V6 | V5):

| Row | Reference | V6 | V5 |
|---|---|---|---|
| Long arm, y 300 | 70–122 | 71–119 | 58–111 |
| Long arm, y 400 | 36–104 | 31–100 | 14–72 |
| Long arm (club), y 460 | 25–96 | 42–98 | — (ends higher) |
| Leg, screen left, y 400 | 239–284 | 236–284 | 215–258 |
| Foot, screen left, y 455 | 214–300 | 220–304 | — (ends higher) |
| Leg, screen right, y 400 | 358–401 | 357–403 | 313–355 |
| Foot, screen right, y 455 | 367–419 | 367–425 | — |

Landmarks (`measure_ref34_landmarks.py`, same pixels):

| | Sheet | V5 | V6 |
|---|---|---|---|
| Pupils | (170.1, 81.7), (210.5, 76.0) | (170.0, 78.7), (213.8, 72.3) | (169.6, 78.6), (213.3, 71.8) |
| Skull top over the forehead | y 48 | y 47 | y 45 |
| Lowest tooth | y 204 | y 207 | y 204 |
| Ivory (teeth) area in the mouth | 2793 px | 2943 px | 3274 px |
| Head and jaw area in the silhouette | 20913 px | 19689 px | 21017 px |

Colour under the sheet-like lighting (mean of the warm pixels over the panel): sheet
(83, 51, 35), V5 (85, 54, 34), V6 (78, 48, 31); teeth: sheet (154, 117, 71), V6 (148, 116, 71).

## Remaining differences (honest)

- **The sheet is not one consistent object.** V6 follows the three-quarter panel; the sheet's own
  front and side views show a narrower, more upright stance. From the front, V6's stance is much
  wider (its left foot is planted about a metre out), and from the side its legs crouch forward
  (`_v6_front_side.png`).
- **Torso lean.** The spine leans only slightly more than V5's (41° vs 39°): in this view the
  reference's torso outline fixes it. The stronger hunch comes from the lower pelvis, the
  crouched legs, the heavier upper back and the head thrust forward.
- **Surface.** The sheet's dense chip mosaic with dark seams is finer and more contrasted than
  V6's shell; V6's lit rust still reads a little smoother.
- **Head.** The sheet's cranium shows more distinct broken plates and protruding chunks; V6's is a
  cleaner faceted block. V6's fangs cover about 17 % more ivory area in this view.
- **Small outline differences.** The back spikes' positions and angles, the bottom edge of the
  club, and the short arm's inner edge at y ≈ 240 (about 8 px).
- **Hidden contact.** The rear of the jaw touches the inside of the neck at the hinge (150
  overlapping face pairs, not visible).
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V6

```bash
bvenv/bin/python scripts/build_v6.py
```

Render from copies (`render_views.py` saves the file it renders); V5 under the same lighting for the
side-by-side:

```bash
cp model/out_there_monster_v6.blend /tmp/v6_copy.blend && STUDIO=sheet SAMPLES=32 bvenv/bin/python scripts/render_views.py /tmp/v6_copy.blend /tmp/v6_renders ref34 && cp /tmp/v6_renders/ref34.png model/renders_v6/v6_ref34.png
```

```bash
cp model/out_there_monster_v5.blend /tmp/v5_copy.blend && STUDIO=sheet SAMPLES=32 bvenv/bin/python scripts/render_views.py /tmp/v5_copy.blend /tmp/v5_renders ref34 && cp /tmp/v5_renders/ref34.png model/renders_v6/v5_ref34.png
```

```bash
bvenv/bin/python scripts/silhouette_ref34.py references model/renders_v6/sil model/out_there_monster_v5.blend model/out_there_monster_v6.blend
```

```bash
bvenv/bin/python scripts/v6_compare.py model/renders_v6 references model/renders_v6/sil model/renders_v6
```
