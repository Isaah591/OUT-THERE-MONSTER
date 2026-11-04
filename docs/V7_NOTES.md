# V7 — reference accuracy pass: the approved sheet as a modelling blueprint

Target: the approved sheet (`references/r08_open_jaw_sheet_v2.webp`), all three main panels: FRONT
(crop (0, 55, 490, 550)), THREE-QUARTER ((500, 55, 1008, 550)) and SIDE (EXACT) ((1017, 55, 1484, 550)).
**New file:** `model/out_there_monster_v7.blend` (`scripts/build_v7.py`, `body_v7.py`, `head_v7.py`).
**Unchanged:** V6 (`model/out_there_monster_v6.blend`, md5 `6a7bc7d7db92b93ac118105574fd8fbf`), V5
(`c249b3159280d6db697906cdb2781dec`) and the open-jaw model (`42cbdae6e7354456c848d18fa06aec02`).
Renders and comparison sheets: `model/renders_v7/`.

## Method

V7 was not adjusted from V6; body and head were rebuilt from measurements of the sheet.

- **One metric frame for the three views.** `scripts/sheet_blueprint.py` reads joint landmarks on
  the front, side and three-quarter panels and solves, by least squares, for one 3D position per
  joint plus the cameras that best explain all three views together (front and side as
  orthographic views, the three-quarter as a perspective camera). That fixes each view's scale
  (front 160 px/m, side 150.2 px/m) and gives the solved joints in
  `data/sheet_blueprint_R_forward.json`. Assuming the right foot is the forward one fits better
  than assuming the left (cost 1869 against 2368).
- **Measured silhouettes.** `scripts/sheet_views.py` separates each panel's figure from its
  backdrop. The model is compared through the same three views: front and side as fitted
  orthographic cameras, the three-quarter view as a fitted perspective camera. It reports the
  overlap (IoU) for the whole figure and for each region, and writes outline overlays.
  - Two fixes over the earlier tool: the front panel's title mask no longer cuts off the top of
    the head, and backdrop seen through the figure stays open (the gap between the legs in the
    side view, under an armpit, between the teeth).
  - Thin sheets of geometry count as surfaces, not as scattered vertices.
- **Building from the measurements.**
  - Torso: horizontal slices. Each slice's width comes from the front view, its back from the
    side view, and its front from the side view where the arms do not hide it.
  - Limbs: run through the solved joints, with the centreline taken from the front view (x) and
    the side view (y), and the thickness taken from each view.
  - Head: rebuilt to the side view's length and profile and the front view's width.
- **Loop.** About 15 passes of build, three-view comparison and correction. Quick passes skipped
  the surface detail (`V7_FAST=1`, about 6 s per build).
- **Where the sheet disagrees with itself, the views were weighted.** As in the blueprint solve,
  the three-quarter view counted 1.5 and the front and side views 1.0 each; the choice was made
  case by case (see *Remaining differences*).

### The three-quarter camera

The three views agree only with a long-lens, nearly orthographic three-quarter camera. Fitted to
V7 it is about 250 mm at about 23 m, azimuth about 24°, elevation 3–4°. The blueprint solve
reached the same camera independently, from the landmarks alone.

The earlier `ref34` camera (46 mm at about 4.6 m) was fitted to an older model's head. V6 was then
posed along that camera's lines of sight. The perspective made V6 match that one view (IoU 0.878)
with a wide, crouched 3D pose that the sheet's own front and side views contradict (0.615 and
0.602).

V7 is therefore rendered from the camera fitted to it (`render_views.py` view `fit34`, parameters
in the FIT34 string below), at twice the panel's resolution, so the sheet and the render share
one pixel grid.

## What changed (actual geometry, V7 files only)

| Part | V7 (V6) |
|---|---|
| Head | A long, angular box-wedge: 0.85 m from the face to the back of the skull (V6: 0.58 m), 0.56 m wide (front view: 0.55 m), its top 0.34 m above the upper gum line, matching the blueprint (V6: 0.32 m on a rounded dome). It has a flat, level top, a forehead that breaks back in uneven planes, and crisp planar breaks: the back-top edge sheared at two levels, front corners broken off, a gouge in the right side, raised and sunken plates on the top. Recessed rectangular sockets sit high on the face under a brow ledge, with tiny red pupils; the left socket is higher and nearer the midline. The snout is turned 4° to the monster's left. |
| Mouth | A long, V-tapered lower jaw hangs from a hinge under the back of the skull, opened 53° so the chin sits low in front of the chest (lowest point z 1.63 m; side view 1.58–1.60 m). There are 36 teeth (V6: 40): 19 upper, 17 lower. Gaps, lengths, widths, tilts (up to ±15°) and curl are all uneven, a few teeth are snapped, the long fangs are at the front of both jaws, and the jaw's right side carries more, longer teeth. Dark inner cheek walls set back in shadow; the flesh is restrained. |
| Torso | A leaning, egg-shaped barrel built from measured slices, not a muscular block. Width 0.69 m at the waist (z 1.3) and 0.79 m at the belly (z 1.6); the belly swells forward only where the side view hides it behind the long arm; the groin front is at y −0.21 m as the side view shows. The hump tops out under the back of the head (z ≈ 2.5 m); the left shoulder rides higher than the right. |
| Long arm | Shoulder (−0.59, −0.36, 2.30) → elbow (−0.99, −0.42, 1.50) → club on the floor at y −1.10 m. Upper arm 0.90 m, forearm and club 1.70 m (blueprint: 0.93 / 1.63 m). The slim upper arm is 0.26 m wide. The forearm is flat with an elliptical section, 0.29 m wide from the front and 0.40 m deep from the side, so it reads slim on the diagonal as in the three-quarter view. The club's end lies flat on the floor. The elbow bend is angular (extra keys either side of the joint). |
| Short arm | Shoulder (0.41, −0.38, 2.25) → elbow (0.59, −0.15, 1.68) → blunt end at z ≈ 0.92 m. Upper arm 0.64 m, forearm 0.75 m (blueprint: 0.66 / 0.76 m). It hangs a little out from the body and bends at an angle. |
| Posture | The body leans forward about 33° (pelvis to the base of the neck; V6: 41°), with the head thrust about 1.1 m ahead of the shoulders. The shoulders are at z 2.25–2.30 m as in the blueprint (V6: 2.30 / 2.42 m), and the crotch is at z ≈ 1.2 m. |
| Legs | Nearly straight from the front, with no wide splay (V6 planted its left foot about a metre out). From the side the stride opens at the hips: the right leg forward with its knee at y −0.09 m, the left leg trailing with its knee at y 0.56 m. Thighs and shins are 0.24–0.27 m wide, thinner than V6's. The feet are broad, blocky and flat, with a tall heel block and low toes. |
| Unchanged | Same sculpt and surface pipeline and materials as V6 (`v6_rust`, `v6_teeth`); the same number of bars (10), moved to where the three views show them. No new parts. |

## Validation

### Silhouette overlap with the sheet (IoU, `sheet_views.py`, fitted cameras for every model)

| View | V5 | V6 | **V7** |
|---|---|---|---|
| Front | 0.734 | 0.615 | **0.896** |
| Exact side | 0.606 | 0.602 | **0.867** |
| Three-quarter | 0.696 | **0.878** | 0.834 |

V7 by region:

| Region | Front | Side | Three-quarter |
|---|---|---|---|
| Head and jaw | 0.934 | 0.865 | 0.901 |
| Torso | 0.948 | 0.893 | 0.939 |
| Long arm | 0.858 | 0.875 | 0.817 |
| Short arm | 0.881 | — | 0.827 |
| Legs | 0.873 | 0.825 | 0.771 |

With the blueprint's own fixed front and side transforms (no per-model fit), V7 scores front
0.880 and side 0.856. The three-quarter camera fitted for the render scores 0.834, with
`FIT34=0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45`.

### Three-quarter landmarks

Each joint was projected through that camera and compared with the sheet's landmarks. The mean
residual is 10.5 px; for scale, the panel is 508 px wide and the figure about 435 px tall.

- Within 5 px: the head top (2.7), the right hip, right knee, right ankle and the long arm's
  wrist.
- 6–11 px: the left ankle, left eye, left shoulder, club, short arm's elbow and left knee.
- 13–24 px: the right toes, the snout and right eye (the face sits about 13 px left), the short
  arm's end, the long arm's elbow, the chin, the left toes (19.7) and the left hip (23.7).
  Each of these is a place where the sheet's own views disagree (next section).

## Remaining differences (honest)

- **The sheet's three views are not one consistent object, so V7 is a weighted compromise.**
  - Measured in metres, the front panel places the chin at z 1.92 m, the three-quarter panel
    about 1.74 m and the exact side 1.58 m. The short arm ends at 0.85 m in the front view and
    0.96–1.0 m in the other two.
  - The three-quarter panel puts the face about 0.1 m further right than the front and side
    views allow, and draws the trailing left foot lower than the right, although the side view
    has it 0.8 m further back.
  - V7 follows the majority, or splits the difference, in each case.
- **The three-quarter overlap is below V6's** (0.834 against 0.878). V6 earned that by bending
  its 3D shape to one perspective camera, at the cost of 0.615 and 0.602 in the front and side
  views. V7 trades about 0.04 in the three-quarter view for +0.28 front and +0.27 side.
- **The front view's face reads taller than the sheet's.** The side and three-quarter views need
  the skull's top 0.34 m above the gum line; the front panel alone suggests about 0.29 m.
- **The torso still reads more like a slab than the sheet's rounded barrel** in the three-quarter
  render, although its outline matches (0.94).
- **Surface:** the sheet's skull has a denser chip mosaic with more broken plates than V7's,
  which reads cleaner. Per the brief, no surface complexity was added.
- **Hidden contact:** the first 0.2 m of the jaw behind the hinge sits inside the neck (1015
  overlapping face pairs), as intended, and is not visible.
- **Presentation:** the backdrop in the V7 renders is a matte version of the sheet studio
  (`STUDIO_BG`). From the distant camera, the glossy floor turned light at grazing angles. The
  sheet's light gradient behind the feet is not reproduced.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V7

```bash
bvenv/bin/python scripts/build_v7.py
```

Three-view validation for V5, V6 and V7 (IoU per view and region, overlays, fitted FIT34
strings):

```bash
bvenv/bin/python scripts/sheet_views.py references /tmp/sv model/out_there_monster_v5.blend model/out_there_monster_v6.blend model/out_there_monster_v7.blend
```

Renders: render from copies, because `render_views.py` saves the file it renders.

```bash
cp model/out_there_monster_v7.blend /tmp/v7_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v7_copy.blend /tmp/v7r fit34 sheet_front sheet_side
```

```bash
cp model/out_there_monster_v6.blend /tmp/v6_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 bvenv/bin/python scripts/render_views.py /tmp/v6_copy.blend /tmp/v6r ref34 sheet_front sheet_side
```

Copy the renders into `model/renders_v7/` as `v7_fit34.png`, `v7_front.png`, `v7_side.png`,
`v6_ref34.png`, `v6_front.png` and `v6_side.png`, and the overlays as `sil_<v6|v7>_<view>.png`.
Then:

```bash
bvenv/bin/python scripts/v7_compare.py model/renders_v7 references model/renders_v7
```

Blueprint solve, which writes `sheet_blueprint_<mode>.json` to `$BLUEPRINT_OUT`:

```bash
BLUEPRINT_OUT=data bvenv/bin/python scripts/sheet_blueprint.py R_forward
```
