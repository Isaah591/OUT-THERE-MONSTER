# V13 ("Experimental 09") — mouth anatomy and eye-socket reconstruction

Target: the approved sheet (`references/r08_open_jaw_sheet_v2.webp`), its three main panels and the detail row (head close-up, mouth interior). The brief: reconstruct the mouth from the sheet, not from V9–V12; lower the existing jaw; keep it narrow, tapered and crooked; restore the eyes; leave everything else alone.

**New file:** `model/out_there_monster_v13.blend` (`scripts/build_v13.py`, `head_v13.py`).

**Unchanged:**
- V12 (`model/out_there_monster_v12.blend`, md5 `6cdaa611393f284ad5bc7ccb2ea217b0`), V11 and every earlier version.
- The body: `BODY UNCHANGED (vertex-identical to v12/v11/v10/v9/v8/v7): True`.
- The upper jaw (V12's upper teeth and gums), the pupils (V12's `Eyes`), the crown bracket, the torn skull sides, palate and throat: `KEPT HEAD PARTS UNCHANGED: True`.
- The cranium, except at the sockets. It is rebuilt from the same signed-distance skull with only the socket cuts changed: new boxes, no stepped frame. The same code with V12's cuts reproduces V12's mesh to the bit. 4,505 vertices are new and 4,954 removed, all within 2.3 cm of a socket. The other 85,155 vertices are V12's, with V12's attributes.
- The materials (no new ones) and the cameras.

Renders and comparison sheets: `model/renders_v13/` (`_v13_*.png`; V12's renders and overlays alongside as `v12_*`).

## What was wrong in V12 (measured against the sheet)

| Feature | Approved sheet | V12 | V13 |
|---|---|---|---|
| Lower jaw, seen from the front and three-quarter | The lower teeth stand on a red gum line that converges into a narrow, off-centre chin. In the three-quarter panel that gum is about 30 px wide at the chin, and the left arm runs diagonally up to (237, 160). | The jaw's *inner edge* was put on the front panel's outline, so the teeth and gums stood about 5 px outside it, and the chin was a generic round arc. The three-quarter panel was never fitted. The rim (where the teeth stand) lay 5.9 px from the sheet's gum line in front and 4.7 px in three-quarter: a wide U with straight sides. | The rim's centre line is fitted through the sheet's gum line and lower roots in **both** panels: 1.9 px in front and 2.5 px in three-quarter. The result is a V converging into a narrow, off-centre chin, with the left arm on the three-quarter panel's diagonal. |
| How low the jaw hangs (exact side) | Chin (163, 231). | Moved up 7.8 px with V11's upper gum. Chin (160, 226). | At the side panel's own height, 7.8 px (5 cm) lower. Chin (167, 230); rear edge 0.9 px from the sheet's. |
| Eye sockets | Small horizontal rectangles cut straight into the plates around the pupils. Front: 16 × 18 and 20 × 17 px. | Taller holes inside a stepped frame, reaching down toward the teeth. Front: 19 × 25 and 29 × 24 px. | Horizontal rectangles around the unchanged pupils, without the frame. Front: 16 × 16 and 27 × 20 px (the second figure includes the shaded plate at the face's edge; the hole itself is about 20 px). |
| Lower teeth | A bundle crowded into the narrow chin, fanning up. | 14 + 2 teeth spread along the wide U. | The same 14 + 2 teeth at V12's size (the jaw carries them; they are not stretched). They are packed into the V: at least 2.2 cm apart along the rim instead of 2.5. |
| Inside the mouth | Dark throughout. | The chest and the right arm showed through the mouth: 48 px in three-quarter, 16 px in front. | 0 px in three-quarter and 4 px in front (a sliver at the chin's edge). |
| Gum line | A thin, irregular red line along the jaw's edge. | A torn strip inside the tooth row, half-buried in the rim and mostly hidden. | On the rim's outer edge, where it shows, and torn less, so it still breaks and varies in thickness. |

## On lowering the jaw

The jaw now hangs exactly as low as the sheet draws it: its chin and rear edge lie on the side panel's own trace. V12 had held it 7.8 px higher.

It is not opened further than that, because V12's mouth was already as tall as the sheet's in the side view and **taller** in the other two. In front it was 120 px from upper gum to chin, where the front panel draws 97. In three-quarter its chin was about 12 px below the panel's. Opening further would move every view away from the reference, which the brief ranks first.

What made V12's jaw read as "not dropped" was its shape: the straight-sided U with a wide, flat bottom. V13's V-shaped, crooked jaw with a narrow chin reads as a mandible hanging from the hinge, as on the sheet.

## Method

**Jaw pose (side).** Unchanged from V12 except the height: the side panel's trace (tooth-root line, rear edge, chin) is used where the panel draws it. The opening (75.8°) is still where the root line runs straight along the jaw.

**The jaw's U (`solve_jaw`, `_rim_samples`).**
- For every point where the sheet shows the lower gum, the solver finds the jaw-local point on the rim's top that projects onto it:
  - the front panel's red tissue line, from v 95 down and round the chin;
  - its 14 lower roots;
  - the three-quarter panel's 10 lower roots.
- Each panel's heights in the mouth are mapped linearly from gum line to chin onto the model's mouth, as V12 did for the front. The front panel draws the mouth 0.61 m tall and the three-quarter 0.70 m, against the side panel's 0.81 m.
- Mapped this way, the two panels agree on where each arm is to within 0.03–0.07 head units.
- The points are ordered round the U, smoothed (a Gaussian over the angle, 7° wide), joined to the arms' ends at the hinges, and resampled.
- The jaw's bone, its breaks and the rest are built on this rim as in V12.

**Lower teeth (`plan_lower`).**
- V12's procedure on the new rim: the front panel's 14 teeth, each with its width and height and its root where it projects, plus the side panel's fan where the front shows none (2 teeth).
- Each tooth leans the way the side panel's fan does at its place on the jaw.
- Sizes use V12's front-mouth scale (`TEETH_K`), so the lowered jaw moves its teeth without stretching them.
- Teeth that would touch are parted in depth; none passes through another.

**Tissue.**
- The gum strip sits on the rim's outer edge.
- The far (right) cheek wall lies flat along the sheet's mouth outline, so no line of sight passes it.
- The mouth floor follows each arm of the crooked U (V12 mirrored one arm onto the other) and rises near the hinge, in front of the neck. The lowered jaw would otherwise have sunk it into the neck.
- Materials are V12's.

**Eye sockets (`restore_sockets`).** Two boxes cut straight into the face plate, sized and placed from the sheet's front and three-quarter sockets around V12's pupils:
- deep enough to hold each pupil;
- the right one set a little left of V12's centre, because its lit inner wall reads as plate;
- each still showing its pupil to the three-quarter camera.

The stepped frame is gone.

## Validation (same cameras for V12 and V13)

| | V12 | V13 |
|---|---|---|
| Side: jaw's rear edge vs the sheet's, mean | 1.7 px | **0.9 px** |
| Side: lowest point (sheet: (163, 231)) | (160, 226) | **(167, 230)** |
| Side: jaw angle, hinge to lowest point (sheet: 77–78°) | 76° | 80° |
| Side: lower root line vs the sheet's, mean | **1.9 px** | 3.2 px |
| Side: gape, upper gum to the end of the lower tooth row (sheet: 111 px) | **111 px** | 119 px (the jaw lowered to the panel's own height; see above) |
| Rim (where the lower teeth stand) vs the sheet's gum line, front / three-quarter | 5.9 / 4.7 px | **1.9 / 2.5 px** |
| Lower teeth vs the front panel, root / tip | 4.4 / 7.9 px | **2.7 / 5.6 px** |
| Lower teeth vs the side panel, root / tip; lean | 3.3 / 11.7 px; 12.7° too upright | 3.4 / 11.7 px; **10.6°** too upright |
| Lower teeth vs the three-quarter panel, root / tip; lean | **3.3 / 15.6 px; 10.7° too far left** | 3.8 / 19.0 px; 18.8° too far left |
| Lower teeth | 14 + 2 | 14 + 2 |
| Body seen through the mouth, three-quarter / front | 48 / 16 px | **0 / 4 px** |
| Front sockets (sheet: 16 × 18, 20 × 17 px) | 19 × 25, 29 × 24 px | **16 × 16, 27 × 20 px** |
| Three-quarter sockets (sheet: 14 × 17, 22 × 20 px) | 8 × 22, 17 × 21 px (inside the frame) | 5 × 16, 25 × 20 px |
| Head overlap (IoU), front / three-quarter / side | 0.940 / 0.914 / 0.855 | 0.940 / **0.917 / 0.859** |
| Teeth passing visibly through each other | 0 | 0 |
| Mouth-region overlap (pixel classes), front / three-quarter | 0.681 / **0.717** | **0.740** / 0.603 |
| Gaps between the teeth, median brightness (sheet: 0.149 / 0.141) | 0.063 / 0.078 | 0.055 / 0.078 |
| Jaw, teeth, gums and floor overlapping the body (inside the neck) | 227 face pairs | 218 face pairs |

All tooth and rim figures use the same measure for both versions: `v13_anatomy_check.py`'s, applied to each version's own plan, with each panel's mouth mapped onto that version's mouth.

How each measure is computed:
- From the model's geometry: the side jaw (`v12_jaw_check.py`), the rim and teeth (`v13_anatomy_check.py`), the see-through pixels (`v13_mouth_check.py`, ray casts) and the overlaps with the body (`build_v13.py`).
- From the renders: the sockets (`v13_mouth_check.py`), head overlap (`measure_head_v8.py`), mouth classes (`measure_mouth_v10.py`) and gap brightness (`v11_teeth_check.py`).

## Remaining differences (honest)

- **Front mouth height.** The front view shows the mouth 128 px tall, against the front panel's 97 (V12: 120). The jaw follows the side panel, and the front panel draws the mouth shorter than the other two. Lowering the jaw, as asked, makes this view taller still.
- **Three-quarter mouth.** The chin is about 17 px below the three-quarter panel's (it draws the jaw 0.70 m long). The mouth-region overlap in this view fell from 0.72 to 0.60, for two reasons:
  - The lower teeth crowd into the narrow chin and hide one another: 1,028 px of visible tooth against V12's 1,488 and the sheet's 2,316.
  - The sheet shows a broad band of bright red tissue there (1,060 px) that V12's dark maroon tissue material, kept, does not reproduce (140 px).
- **Lower teeth, three-quarter.** They lean 19° further left than the three-quarter panel draws them; V12's leaned 11°. Their direction follows the side panel's fan and the front panel's lean, which draw them pointing further forward than the three-quarter panel does. Tilting them upright was tried: the three-quarter view improves by about 6°, but the side view moves away from its fan by the same amount, so the side fan was kept.
- **Eyes.** The pupils stay exactly where V12 had them. The front panel draws the whole face about 7 px higher than the model's head allows: the pupils are 5–7 px low in front and 7–8 px left in three-quarter, as in V12. The cranium is locked, and moving the pupils would make one of those views worse. In three-quarter the socket on the monster's right still reads as a narrow slot, because the locked face recedes steeply on that side.
- **Upper teeth.** They are V12's, unchanged: the brief calls the upper jaw correct. They are longer and fewer than the sheet's dense fringe.
- **Red tissue.** The gum line shows more than in V12, but the tissue material is V12's dark maroon, not the sheet's glossy red. No new materials, as the brief asks.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V13

V13 needs scikit-image, as V10–V12 do:

```bash
bvenv/bin/python scripts/build_v13.py
```

Render from a copy, because `render_views.py` saves the file it renders:

```bash
cp model/out_there_monster_v13.blend /tmp/v13_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v13_copy.blend /tmp/v13r fit34 sheet_front sheet_side
```

Checks:

```bash
bvenv/bin/python scripts/v13_anatomy_check.py /tmp/v13 front=/tmp/v13r/sheet_front.png side=/tmp/v13r/sheet_side.png 34=/tmp/v13r/fit34.png
```

```bash
bvenv/bin/python scripts/v13_mouth_check.py model/out_there_monster_v13.blend front=/tmp/v13r/sheet_front.png 34=/tmp/v13r/fit34.png
```

```bash
bvenv/bin/python scripts/v12_jaw_check.py model/out_there_monster_v12.blend model/out_there_monster_v13.blend
```

```bash
bvenv/bin/python scripts/v11_teeth_check.py model/out_there_monster_v13.blend front=/tmp/v13r/sheet_front.png 34=/tmp/v13r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v13 model/out_there_monster_v13.blend /tmp/v13r
```

```bash
bvenv/bin/python scripts/measure_mouth_v10.py /tmp/v13 front=/tmp/v13r/sheet_front.png 34=/tmp/v13r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v13.blend
```

Copy into `model/renders_v13/`:
- the renders, as `v13_fit34.png`, `v13_front.png` and `v13_side.png`;
- the overlays, as `v13_head_<view>.png`, `v13_classes_<front|34>.png` and `v13_anatomy_<view>.png`;
- V12's renders and overlays, as `v12_*`.

Then:

```bash
bvenv/bin/python scripts/v13_compare.py model/renders_v13 references model/renders_v13
```
