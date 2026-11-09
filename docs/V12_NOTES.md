# V12 — jaw silhouette and tooth placement correction

Target: the approved sheet's head (`references/r08_open_jaw_sheet_v2.webp`). The exact side panel is the reference for the lower jaw; the front panel for the teeth; the three-quarter panel is the check.

**New file:** `model/out_there_monster_v12.blend` (`scripts/build_v12.py`, `head_v12.py`).

**Unchanged:**
- V11 (`model/out_there_monster_v11.blend`, md5 `eeeb15a930a9ab95c70bf82a2dff2645`), V10 (md5 `a5ba72026f535bde195755e58ddfe56c`) and every earlier version.
- Everything outside the mouth. The build opens V11, removes only the mouth objects (lower jaw, teeth, gums, mouth tissue) and builds new ones on V11's cranium. Before saving it checks, vertex by vertex against V11:
  - the body: `BODY UNCHANGED (vertex-identical to v11/v10/v9/v8/v7): True`;
  - the rest of the head (cranium, eyes, crown bracket, torn skull sides, palate, throat): `REST OF THE HEAD UNCHANGED: True`.
- The materials (V11's, which are V10's) and the cameras.

Renders and comparison sheets: `model/renders_v12/`.

## What was still wrong in V11 (measured on the sheet)

| Feature | Approved sheet | V11 | V12 |
|---|---|---|---|
| Lower jaw, exact side | A steep, bony bar. The lower teeth's root line runs straight at about 76°. The rear edge drops almost vertically below the hinge, then curves forward into the chin (87°, 73°, then 69°). About 19–21 px from the tooth roots to the rear edge. A broken spur under the chin at (163, 231). | A straight bar at 67° (71° from hinge to lowest point). The rear edge sits 5–13 px forward of the sheet's, and the chin ends in a point at (153, 221). | The jaw's side profile is the sheet's own trace (see Method): opened 75.8°, 76° from hinge to lowest point. The rear edge lies within 1.7 px of the sheet's on average, the tooth-root line within 1.9 px. Lowest point (160, 226); the chin's spur is there; chips are cut out of the underside. |
| Upper teeth, front | 9 in the front row and 2 hanging behind it. Widths 4.5–8.5 px, lengths 11–45 px. A long, wide fang right of the middle; long teeth at the monster's right; short stubs at its left. The roots stand at different heights on the broken gum (v 57–66). | 10 teeth, all hanging from one level line. Widths from one formula (3.3–5.7 cm). | 9 + 2 teeth, each with the sheet's own width (3.3–7.3 cm), root height and length, and its own gentle curve. Front agreement: roots 0.6 px, tips 2.1 px. |
| Lower teeth | Front panel: 14 overlapping teeth fanning from the chin. A wide central tooth (7 px) among slimmer ones (3–5 px); heights 19–41 px; the monster's right group leans outward 6–14°. Side panel: a fan pointing forward at 33° at the chin, steepening to 76° toward the hinge. | 14 + 4 teeth standing close to parallel, widths 2.9–6.0 cm, lengths 19–40 cm. The front view reads as a fence of long cigars. | 14 + 2 teeth, each with the sheet's own width (3.2–7.9 cm, the central tooth widest), lengths 16–35 cm. Each leans forward as the side panel's fan does at its place on the jaw, as far as its tip stays inside the fan's outline in the side view. So the short chin teeth point forward and the tall ones stand up behind them, and they fan out with gaps between them. Front agreement: roots 5.2 px, tips 5.4 px. |
| Mouth tissue | Thin, irregular red rims; the jaw's bone shows; dark tissue inside. | A smooth gum tube along the whole lower rim (5–8 cm thick) and another along the upper jaw: a clean red outline. Thick cheek bands. | Gum collars of different sizes around the tooth bases, with a quarter of the teeth standing on bare bone. They are joined by a thin, torn strip (about 2 cm, with gaps) that thins out at its torn ends. The cheek bands are thinner (2–3 cm) and torn. The mouth floor is folded, not a flat sheet. |
| Mouth proportions, side | Upper gum to the end of the lower tooth row: 111 px. | 105 px. | 111 px. |

## Method

**Lower jaw from the exact side panel.**
- The jaw's front edge (the lower teeth's root line), its rear edge and its chin were traced against the panel's background (`SHEET["side_jaw"]`).
- `_fit_jaw_pose` finds the opening at which the root line runs straight along the jaw (75.8°). In the jaw's own frame at that opening:
  - the root line gives the rim's top (the bone under a thin gum);
  - the rear edge gives its underside, profile by profile (deepest below the hinge, rising toward the chin);
  - the chin gives its end, with a chamfer from the tooth row down to the chin's front.
- The front panel's mouth outline still sets the U's width, side by side, as in V11.
- The trace is placed relative to the upper gum, as the side panel draws the two jaws. V11's skull, which V12 keeps, holds the upper gum 7.8 px higher than the side panel does, so the traced jaw moves up with it. This keeps the gape at the sheet's 111 px instead of 119, and keeps the mouth close to V11's size.

**Teeth from the sheet, one by one.**
- The front panel's upper and lower teeth were re-read with their widths (`SHEET["front_upper"]`, `["front_upper_behind"]`, `["front_lower"]`: root, tip, width in px).
- Widths are the sheet's × 1.35 (upper) and × 1.8 (lower). The sheet's teeth are lit full-width; the model's lose their edges to shade and to the gum at the root, and the model's mouth is drawn taller.
- Upper roots stand at their own heights on the gum. The two teeth behind the front row hang from the palate.
- Lower teeth follow the side panel's fan (`_side_fan`, `_fan_envelope`).
- Teeth that would touch are moved apart mostly along the front view's line of sight, so they part in depth and the front reading holds. None pass through each other: checked on the meshes with `v11_teeth_check.py`.

**Tissue.** The gums are no longer tubes but collars and torn strips (`gums_and_teeth`), and the cheek bands are thinner and torn (`mouth_flesh`). The tissue material is V11's.

## Validation (same cameras for V11 and V12)

| | V11 | V12 |
|---|---|---|
| Front: head overlap (IoU) | 0.939 | **0.940** |
| Three-quarter: head overlap | **0.916** | 0.914 |
| Exact side: head overlap | 0.833 | **0.855** |
| Side: jaw's rear edge vs the sheet's, mean distance | 5.3 px | **1.7 px** |
| Side: jaw angle, hinge to lowest point (sheet: 77–78°) | 71° | **76°** |
| Side: lowest point (sheet's chin: (163, 231)) | (153, 221) | **(160, 226)** |
| Side: lower teeth's root line vs the sheet's, mean distance | 4.5 px | **1.9 px** |
| Side: gape, upper gum to the end of the lower tooth row (sheet: 111 px) | 105 px | **111 px** |
| Teeth vs the front panel's readings (mapped), root / tip | upper 1.2 / 1.5 px; lower 4.6 / 6.4 px | upper 0.6 / 2.1 px (with each root's own height); lower 5.2 / 5.4 px |
| Lower teeth vs the side panel's fan, root / tip | 6.1 / 13.8 px | **3.3 / 11.7 px** |
| Lower teeth vs the three-quarter panel, root / tip | — | 3.4 / 15.9 px; they lean 10° more on average |
| Tooth widths, upper / lower (spread, widest ÷ narrowest) | 3.3–5.7 cm (1.7×) / 2.9–6.0 cm (2.1×) | 3.3–7.3 cm (2.3×) / 3.2–7.9 cm (2.4×) |
| Teeth passing visibly through each other | 0 | 0 |
| Mouth-region overlap (pixel classes), front / three-quarter | 0.61 / 0.68 | **0.68 / 0.72** |
| Gaps between the teeth, median brightness (sheet: 0.149 / 0.141) | 0.055 / 0.075 | 0.063 / 0.078 |
| Jaw, teeth, gums and floor overlapping the body (inside the neck) | 375 face pairs | 227 face pairs |

How each measure is computed:
- Head overlap, the side jaw (`v12_jaw_check.py`) and the side profile (`measure_side_profile_v9.py`) come from the model's geometry.
- Mouth-region overlap and gap brightness come from the renders.
- In the side render the jaw's rear edge is dark against the studio's black background (the same lighting as V7–V11); its outline is on the sheet's, as the silhouette overlays in `_v12_head_silhouettes.png` show.

## Remaining differences (honest)

- **Mouth height, front and three-quarter.** The mouth is 6% taller than V11's: 120 px against 113 in front, 119 against 113 in the three-quarter view. The jaw now follows the side panel's length and angle. The front panel draws the mouth shorter still (97 px) and the three-quarter panel at 110 px; the panels disagree, and the side profile was kept.
- **Chin.** The lowest point sits 5 px above the side panel's chin, because the jaw is placed relative to V11's upper gum, which sits 7.8 px higher than the side panel's.
- **Density.** The sheet's lower teeth overlap more; V12 shows dark tissue in the gaps between them.
- **Three-quarter.** The lower teeth lean about 10° more than the three-quarter panel draws them, because their direction follows the side panel's fan.
- **Upper teeth in the side view.** They are 5.6 px (roots) and 20 px (tips) from the side panel's readings; the front panel's row takes priority.
- **Skull.** V11's, unchanged, as the brief asks.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V12

V12 needs scikit-image, as V10 and V11 do:

```bash
bvenv/bin/python scripts/build_v12.py
```

Render from a copy, because `render_views.py` saves the file it renders:

```bash
cp model/out_there_monster_v12.blend /tmp/v12_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v12_copy.blend /tmp/v12r fit34 sheet_front sheet_side
```

Checks:

```bash
bvenv/bin/python scripts/v12_anatomy_check.py /tmp/v12 front=/tmp/v12r/sheet_front.png side=/tmp/v12r/sheet_side.png 34=/tmp/v12r/fit34.png
```

```bash
bvenv/bin/python scripts/v12_jaw_check.py model/out_there_monster_v11.blend model/out_there_monster_v12.blend
```

```bash
bvenv/bin/python scripts/v11_teeth_check.py model/out_there_monster_v12.blend front=/tmp/v12r/sheet_front.png 34=/tmp/v12r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v12 model/out_there_monster_v12.blend /tmp/v12r
```

```bash
bvenv/bin/python scripts/measure_mouth_v10.py /tmp/v12 front=/tmp/v12r/sheet_front.png 34=/tmp/v12r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v12.blend
```

Copy into `model/renders_v12/`:
- the renders, as `v12_fit34.png`, `v12_front.png` and `v12_side.png`;
- the overlays, as `v12_head_<view>.png`, `v12_classes_<front|34>.png` and `v12_anatomy_<view>.png`;
- V11's renders and overlays, as `v11_*`.

Then:

```bash
bvenv/bin/python scripts/v12_compare.py model/renders_v12 references model/renders_v12
```
