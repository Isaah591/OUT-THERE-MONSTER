# V11 — head anatomy correction (mouth, lower jaw, teeth)

Target: the approved sheet's head (`references/r08_open_jaw_sheet_v2.webp`), checked in its front, three-quarter and exact-side panels.

**New file:** `model/out_there_monster_v11.blend` (`scripts/build_v11.py`, `head_v11.py`).

**Unchanged:**
- V10 (`model/out_there_monster_v10.blend`, md5 `a5ba72026f535bde195755e58ddfe56c`) and every earlier version.
- V11's body. The build opens V10, removes only its head objects, and builds the new head on the same mount. Before saving it checks the torso, arms, legs and bars vertex by vertex against V10. Result: `BODY UNCHANGED (vertex-identical to v10/v9/v8/v7): True`.
- The materials: V10's rust, teeth, flesh, throat, eye and bar materials, unchanged. V11 only assigns them to its new head parts.
- The cameras: the three-quarter view uses V7's fitted `fit34`; the front and side views use the sheet's panels as orthographic cameras.

Renders and comparison sheets: `model/renders_v11/`.

## Method: the sheet's anatomy as data, not V9/V10's head

Earlier versions styled a mouth and then placed teeth along it. For V11, the head's anatomy was first read off the sheet's three panels, on gridded zooms, then drawn back over the sheet to check the readings:

- every visible tooth as root → tip:
  - front panel: 10 upper, 14 lower;
  - exact side: 8 upper, 10 lower;
  - three-quarter: 11 upper, 10 lower;
- the front panel's mouth outline;
- the side panel's jaw edges and chin.

The lower teeth were read twice. The first reading counted only the teeth that could be told apart (11 in the front panel, 8 in the three-quarter). A second reading on sharpened 11–12× zooms found the sheet's crowded bundle:
- 14 lower teeth in the front panel and 10 in the three-quarter;
- the tall teeth behind the chin reach 8–12 px higher than first read, about half-way up the mouth;
- on the monster's right the teeth lean outward by 6–14°, the middle ones stand upright, and those on the left lean in a little.

V11 uses the second reading.

The jaw and every tooth are solved from these readings in `head_v11.py` (`SHEET`, `solve_jaw`, `plan_teeth`):

- **Jaw pose:** the jaw's opening and length put its chin on the side panel's jaw line.
- **Jaw outline:** its inner rim, side by side, is solved so that it projects onto the front panel's mouth outline.
- **Upper teeth:** their roots sit on the broken upper-jaw edge, where the front panel shows them. Their tips come from the front panel's tips.
- **Lower teeth:** their roots are found on the solved jaw rim, where they project onto the front panel's roots. Their tips come from the front panel's tips.
- **Lower teeth, depth:** the panels disagree here.
  - The side panel's chin teeth are short and point forward.
  - The front and three-quarter panels show tall teeth standing behind the chin.
  - V11 reads both as one bundle: short teeth at the chin point forward, tall ones stand up behind them, and the lean steepens up the jaw. The forward reach is at most the side panel's (0.18 m).
- **Crowding:** where roots stand closer than the teeth are wide, the teeth stand in two rows on the gum. Which row comes from the front panel: a root that reads higher there sits further back.
- **No tooth passes through another.** `_separate` checks every pair along their visible length (above the gum), with the teeth's real profile. It then staggers the roots, or moves the shorter tooth's tip (lower teeth: along the front view's line of sight, so the front reading holds), or, as a last resort, slims it a little.

`scripts/v11_anatomy_check.py` reprints the plan against the readings and draws them over renders (`_v11_anatomy_overlays.png`). `scripts/v11_teeth_check.py` finds teeth that pass through each other in the built meshes and measures the mouth interior's brightness.

**The sheet's panels disagree on the mouth's height.** Gum line to chin measures 0.61 m in the front panel, 0.70 m in the three-quarter panel, and 0.81 m in the exact side.
- V11 keeps the side profile (0.77 m): the chin sits on the side panel's jaw line, about 8 px short of its chin, in exchange for the three-quarter view.
- The front panel's vertical positions in the mouth are mapped proportionally between the model's gum line and chin.
- The upper and lower tooth lengths are the front panel's, scaled by the side panel's ratio of 1.4. For comparison, the three-quarter panel's ratio is 1.2, and the front panel's own mapping (scale 1.32, printed by `v11_anatomy_check.py`) would give 1.3.

## What was anatomically wrong in V10, and what V11 builds

| Feature | Approved sheet (measured) | V10 | V11 |
|---|---|---|---|
| Mouth outline (front) | Asymmetric. The monster's right side drops straight; the left slants inward (from x≈300 to 268 px); the chin is off-centre to the right; red rims run along the sides. | A symmetric box: parallel sides and a broad, flat chin. | The jaw's inner rim is solved from the outline: the right side straight at x≈−0.35 head units, the left converging from +0.33 to +0.20, and the chin 0.12 units off-centre to the right. Mouth outline drawn over V11: `_v11_anatomy_overlays.png`. |
| Lower jaw | It hangs from under the cheek, ahead of the neck. In the side view it is a thin bony bar falling at about 71–77° (hinge to chin), with a red gum along its top. | Hinged at the neck (local y 0.60), opened 64°. A broad, symmetric U: 0.61 m wide at its middle, 0.28 m at the chin. A lit flesh floor filled the U. | Hinge moved 0.18 units forward (local y 0.42). Opened 67°; jaw 1.14 units long; side-view angle 71° (hinge to lowest point). A thin, uneven bony rim, 6 cm wide, with a thick lobed gum along its top; the chin's right corner is broken off and chips are missing. A dark tissue floor sits low inside the U. |
| Upper teeth | Irregular lengths (front panel: 10–48 px), alternating short and long. One long fang just right of the middle; shorter teeth toward the monster's left corner; long fangs behind the right corner (side panel). | A fence of nine long, similar fangs across the front, plus seven along the sides. | 16 teeth: 10 across the front where the front panel shows them, 3 long ones behind the right corner, and 3 short ones at the left corner. Front-panel agreement (mapped): roots 1.2 px, tips 1.5 px on average. |
| Lower teeth | Front panel: a crowded bundle of 14 overlapping teeth along the chin and the monster's left side; only 2 on the right side. It fans from the chin: the right group leans outward, the middle stands upright. Side panel: a fan leaning forward, more steeply toward the chin. | 20 spread around the whole U, leaning inward like a cage. | 18 teeth: the front panel's 14 plus 4 from the side panel's fan, all rooted on the rim. They stand in two rows where crowded. Short teeth at the chin point forward; tall ones stand up behind them. Front agreement: roots 4.6 px, tips 6.4 px. |
| Tooth form | Long fangs, full through their lower half, tapering to sharp points (cigar-shaped); uneven. Front panel: 3–5 cm wide. | Seven-sided, faceted and blunt-looking. | Round, slightly flattened and twisted fangs, full through their lower half and tapering to a sharp point, curving gently. Upper fangs are 4–6 cm wide at the root; the lower bundle 5–6.5 cm, a little wider because the model's mouth is drawn 1.3 times taller. Two of each row are snapped. |
| Teeth passing through each other (visible, above the gum) | None. | 7 upper and 4 lower pairs. | None. Only root ends meet, inside the gum (4 and 7 pairs). |
| Forehead-to-mouth | The eye sockets sit just above the upper teeth (front and three-quarter panels). | The upper gum line sat lower. | The upper jaw's edge is raised 0.06 units (3.6 cm); the sockets are unchanged. |
| Tissue | Red rims along the mouth's sides; dark red at the gape's corners; between the teeth a dark brown-maroon interior (median brightness 0.15), black only deep in the throat. | A lit, flat maroon floor and cheek sheets (gaps 0.10). | A thick red gum on the jaw rim. Torn cheek bands at each corner of the gape. Dark-red inner cheek walls set back in the mouth: the far side spans the gape, the near side only its rear, so the side view reads dark and never see-through. A dark tissue floor (gaps 0.055–0.075). The upper gum is lobed around each root. |
| Skull | Blocky, broken and asymmetric, with square sockets. | V10's planar, broken skull. | Kept as V10's except the upper jaw's edge: its silhouette already matched in all three views, and the brief asks to preserve it. |

## Validation (same cameras for V10 and V11)

| | V10 | V11 |
|---|---|---|
| Front: head overlap (IoU) | **0.941** | 0.939 |
| Three-quarter: head overlap | **0.917** | 0.916 |
| Exact side: head overlap | 0.827 | **0.833** |
| Exact side: jaw angle, hinge to lowest point | 68° (hinge at the neck) | 71° (hinge under the cheek) |
| Teeth vs the sheet's readings, front panel (mapped), mean root / tip distance | — | upper 1.2 / 1.5 px; lower 4.6 / 6.4 px |
| Teeth vs the side panel's readings | — | upper teeth behind the corners 8.5 / 15.3 px; lower fan 6.1 / 13.8 px |
| Teeth passing visibly through each other | 7 upper + 4 lower pairs | **0** |
| Gaps between the teeth, median brightness, front / three-quarter (sheet: 0.149 / 0.141) | 0.102 / 0.106 (lit red floor) | 0.055 / 0.075 |
| Mouth-region overlap (pixel classes), front / three-quarter | **0.68** / 0.58 | 0.61 / **0.68** |
| Jaw, teeth, gums and floor overlapping the body (inside the neck) | 1181 face pairs | 375 face pairs |

Notes on the measures:
- Head overlap and the side profile are computed from the model's geometry (`measure_head_v8.py`, `measure_side_profile_v9.py`); the mouth-region overlap and the gap brightness from the renders.
- The mouth-region overlap compares raw pixels, so V11's taller mouth costs it in the front view; the panels disagree on the mouth's height, as explained under Method. The tooth-by-tooth readings are the better check of the arrangement.
- Pupils are unchanged from V10: front (+1, +7) and (+4, +5) px, three-quarter (−7, −2) and (−8, −1) px.

## Remaining differences (honest)

- **Front view.** The mouth is taller than the front panel draws it, about 1.3 times its height. The panels disagree, and V11 keeps the side profile. The eye sockets sit 5–7 px low, as in V8–V10.
- **Fullness.** The sheet's mouth looks fuller. Its teeth overlap more in view, so less of the inside shows.
  - In pixel classes, dark void is 0.50 of V11's mouth in front and 0.56 in the three-quarter view; the sheet's is 0.36 and 0.42.
  - A fuller mouth would need teeth that pass through each other, wider teeth than the sheet's, or more teeth than the sheet shows. V11 does none of these.
- **Interior.** Between the teeth the mouth is darker than the sheet's: median brightness 0.055–0.075 against 0.14–0.15. It is dark tissue, not a black hole. Brighter would need new materials or lighting, which the brief keeps as they are.
- **Side view.**
  - V11's upper jaw edge sits 6–10 px higher than the side panel draws it (raised for the front and three-quarter panels).
  - The chin's tall teeth stand more upright than the side panel's fan, a compromise with the front and three-quarter panels. One short chin tooth points forward, slightly past the fan.
- **Skull.** Unchanged from V10 apart from the upper jaw's edge. The sheet's skull surface still reads darker and chunkier.
- **Hidden contact.** The jaw's rear and the floor's rear sit inside the neck at the hinge (375 face pairs). Not visible.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V11

V11 needs scikit-image, as V10 does:

```bash
bvenv/bin/python scripts/build_v11.py
```

Render from a copy, because `render_views.py` saves the file it renders:

```bash
cp model/out_there_monster_v11.blend /tmp/v11_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v11_copy.blend /tmp/v11r fit34 sheet_front sheet_side
```

Checks:

```bash
bvenv/bin/python scripts/v11_anatomy_check.py /tmp/v11 front=/tmp/v11r/sheet_front.png side=/tmp/v11r/sheet_side.png 34=/tmp/v11r/fit34.png
```

```bash
bvenv/bin/python scripts/v11_teeth_check.py model/out_there_monster_v11.blend front=/tmp/v11r/sheet_front.png 34=/tmp/v11r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v11 model/out_there_monster_v11.blend /tmp/v11r
```

```bash
bvenv/bin/python scripts/measure_mouth_v10.py /tmp/v11 front=/tmp/v11r/sheet_front.png 34=/tmp/v11r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v11.blend
```

Copy into `model/renders_v11/`:
- the renders, as `v11_fit34.png`, `v11_front.png` and `v11_side.png`;
- the overlays, as `v11_head_<view>.png`, `v11_classes_<front|34>.png` and `v11_anatomy_<view>.png`;
- V10's renders and overlays, as `v10_*`.

Then:

```bash
bvenv/bin/python scripts/v11_compare.py model/renders_v11 references model/renders_v11
```
