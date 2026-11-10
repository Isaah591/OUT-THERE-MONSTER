# V15 ("Experimental 11") — posterior teeth lengthened, angrier brows

Target: the approved sheet (`references/r08_open_jaw_sheet_v2.webp`), starting from V14. The brief is a targeted refinement, not a redesign:
- **main:** make the gap between the rows smaller by lengthening the teeth further inside the mouth, so they hide more of the dark interior from the three-quarter camera. The jaws, the opening and V14's curvature stay as they are, and nothing solid is added;
- **secondary:** make the eyes angrier through the brows only. The sockets' size, spacing, position and square shape stay, and so do the pupils.

**New file:** `model/out_there_monster_v15.blend` (`scripts/build_v15.py`, `head_v15.py`).

**Unchanged:**
- V14 (`model/out_there_monster_v14.blend`, md5 `fe6daac7109f0dc8655fe25ddad70639`) and every earlier version.
- The body: `BODY UNCHANGED (vertex-identical to v14/…/v7): True`.
- The jaw and its curvature, the gums, the mouth's tissue (cheek flesh, inner walls, floor, strands, corner rims), the pupils, the crown bracket, the torn skull sides, the palate and the throat: `KEPT HEAD PARTS UNCHANGED: True`.
- The materials and colours (no new ones), the cameras and the lighting.
- The cranium, outside the brows and sockets. 1,898 vertices are new and 1,248 removed, all at the brows and sockets (checked in the build); the other 89,643 are V14's, with V14's attributes.
- 15 of the 33 teeth: V14's planning, shapes and random sequence are reused, so a tooth that does not grow comes out exactly as V14's.

Renders and comparison sheets: `model/renders_v15/`, with V14 alongside.
- `_v15_head_*.png`, `_v15_mouth_*.png`: the sheet, V14 and V15 from the same cameras.
- `_v15_lengthened.png`: the lengthened teeth in all three views. Each is drawn white for its V14 length; the yellow beyond is what V15 adds.
- `_v15_teeth_hidden.png`: the teeth and pupils hidden. The jaws and the opening are V14's; only the brows differ.
- `_v15_eyes.png`: the eyes, with and without the pupils.
- `_v15_side_lit.png`: the exact side under the extra camera-side light (`SIDE_KEY=700`), as for V14.

## What changed

| Feature | Approved sheet | V14 | V15 |
|---|---|---|---|
| Teeth deep in the mouth (three-quarter view) | A crowded mouth: the near side's lower teeth stand tall and the rows overlap, so little of the dark interior shows. | The upper teeth along the near side and behind the corner were short stubs (0.20–0.26 units), as were the near-corner front teeth and the lower teeth up the jaw's arm. A large dark gap showed over the near side. | 18 teeth lengthened, 9 per row, toward the prominent front teeth's length (V14's longest: upper 0.61 at the front, lower 0.57). The three-quarter camera sees 26% less of the mouth's interior between the jaws. |
| Upper row | Uneven lengths. Short and long teeth alternate across the front; the rearmost are short in the side panel. | V12's plan from the sheet. | The front row's far half and its middle tooth (U0–U4) are V14's: they match the sheet's front and three-quarter panels. Grown: the near end of the front row (U5–U8, two of them snapped), a tooth behind the row (U9), the far side's U11, and the side teeth behind the near corner (U14–U16). |
| Lower row | A bundle fanning from the chin; up the arms the teeth stand tall in three-quarter and shorten toward the hinge in the side panel. | V13's plan on V14's swept rim. | The chin's middle (L0–L5) is V14's. Grown: from the near side of the chin up the arm (L6–L14), shortening again toward the hinge. L15, the last one, cannot grow: at any length its tip runs into the cheek's underside. |
| Tooth character | Ivory, tapered, crooked, uneven | — | V14's teeth and materials. Every tooth grows from its own root along its own direction, to its own length (a random factor, 0.80–1.15). Two far-leaning upper teeth swing toward hanging straight as they grow, U8 from 36° to 23° and U15 from 32° to 22° (the side panel's upper teeth hang nearly upright). Grown teeth thicken a little with their length where they stay clear (w ∝ L^0.25), so they stay fangs. None passes through another. |
| Brows | Heavy brow plates over square sockets, scowling | Ledges 4.8 / 3.3 cm out over the sockets; tops sloping 21° / 19° toward the nose | The right ledge juts 5.7 cm. On their inner halves both tops drop 28° / 26° toward the nose; their outer halves stay V14's, so the head's side outline does too. A lip of brow 10° steeper than each socket's own top edge overhangs the opening's inner top corner, 2.9 / 3.2 px deep (front panel). The eyes' upper edges now slant down toward the nose. |
| Sockets, pupils | — | Boxes 17 × 16, 27 × 21 px (front) | The holes and pupils are V14's. Boxes 19 × 15 and 27 × 21 px (front), within 2 px of V14's. The visible dark area is smaller where the lips cover the inner top corners (front: 303 / 230 → 252 / 181 px). |

The teeth, with lengths in head units (1 unit = 0.6 m):

| Upper | V14 → V15 | | Lower | V14 → V15 |
|---|---|---|---|---|
| U5 (front, middle) | 0.33 → 0.38 | | L6 (chin, near side) | 0.35 → 0.41 |
| U6 (front, snapped) | 0.18 → 0.38 | | L7 | 0.54 → 0.57 |
| U7 (front, near end) | 0.31 → 0.58 | | L8 | 0.39 → 0.54 |
| U8 (front corner, snapped) | 0.19 → 0.50 | | L9 | 0.49 → 0.62 |
| U9 (behind the row) | 0.44 → 0.66 | | L10 (up the arm) | 0.54 → 0.62 |
| U11 (far side) | 0.41 → 0.66 | | L11 | 0.50 → 0.59 |
| U14 (behind the near corner) | 0.26 → 0.61 | | L12 | 0.40 → 0.48 |
| U15 | 0.22 → 0.55 | | L13 | 0.29 → 0.45 |
| U16 | 0.20 → 0.52 | | L14 (snapped, near the hinge) | 0.23 → 0.34 |

## Method

**Which teeth.** The posterior teeth, as the brief lists them, from the sheet and the three-quarter camera:
- Upper: every tooth not in the front row (behind it, along the far side and behind the near corner). Of the front row, only its near end (`posterior_up`), where it turns back toward the corner and hangs over the deep part of the opening.
- Lower: from the near side of the chin up the arm (`posterior_lo`).

The far half of the front row was grown in a draft. It hung 15–20 px below the sheet's teeth in three-quarter, and the row read as an even curtain, which the brief rules out. It is V14's again.

**How long.**
- Each tooth's goal (`lengthen_posterior`) is 0.62 units times its own random factor (0.80–1.15), capped near the row's longest front tooth (upper 0.66, lower 0.62).
- The goal tapers toward the back of the mouth (`taper_up`, `taper_lo`), as the sheet's side panel draws the rearmost teeth at about two thirds of the middle ones.
- How far a tooth moves toward its goal depends on how posterior it is.

**Growth that never crosses.**
- The teeth grow together, 0.02 units at a time. A step is kept only if the whole tooth stays clear of:
  - every other tooth of both rows (their curved axes and radii, compared in the cranium's space);
  - bone and tissue: the cranium, the jaw, the gums, the floor, the walls, strands, rims, torn flesh, palate and throat (ray casts along its axis).
- If the straight step is blocked, the tooth may turn aside by up to 10°. An upper tooth leaning more than 15° from vertical swings toward it as it grows, at most 70% of the way (`LEAN_MAX`). If no direction is clear, it stays at its last clear length and tries again next round.
- So no state with a crossing is ever reached, and no tooth needs shrinking afterwards.
- Roots never move. The gums round them are V14's.

**Brows (`_brows`, `_brow_lips`).**
- The ledges keep V14's construction. Their tops are steeper but may not rise above V14's, so the steeper slope only lowers their inner halves. The outer ends, which form the head's side outline, are V14's.
  - A draft with the steeper tops alone pushed the left brow 7 px further out of the side profile, at v ≈ 55.
- The lips are wedges of brow under each ledge's front. Each runs from the socket's outer top corner, 10° steeper than its top edge, back 0.05 units into the hole.

**Order of work.**
1. V14's coverage was measured against the sheet (colour classes, and a ray-cast map of what the three-quarter camera sees in the mouth), and the short teeth were identified.
2. The teeth were lengthened and the brows changed.
3. Each draft was rendered from the sheet's three cameras and compared with the sheet and V14 (14 drafts).

## Validation (same cameras and lighting for V14 and V15)

| | V14 | V15 |
|---|---|---|
| Three-quarter: mouth interior seen between the jaws (ray casts, no lighting) | 4,148 px | **3,080 px (−26%)** |
| Three-quarter: tooth surface seen between the jaws | 3,678 px | **4,919 px (+34%)** |
| Front: mouth interior / teeth seen between the jaws | 3,812 / 4,035 px | **3,055 / 4,856 px** |
| Three-quarter: dark pixels between the jaws, render (sheet: 3,014) | 4,969 | **3,870** |
| Front: dark pixels between the jaws, render (sheet: 2,287) | 3,772 | **3,041** |
| Ivory tooth pixels in the mouth, front / three-quarter (sheet: 1,718 / 2,316) | 1,549 / 1,271 | **1,677 / 1,433** |
| Teeth passing visibly through each other (upper, lower, between rows) | 0 | 0 |
| Root ends meeting inside the gum (hidden) | 8 / 8 / 0 | 8 / 9 / 0 |
| Mouth opening vs the sheet (IoU with the teeth hidden), front / three-quarter | 0.678 / 0.749 | 0.678 / 0.749 (unchanged) |
| Jaw, side: rear edge vs the sheet, lowest point, root line | 1.1 px, (167, 230), 4.9 px | the same |
| Head overlap (IoU), front / three-quarter / side | 0.939 / 0.915 / 0.850 | 0.939 / 0.915 / 0.861 |
| Side: front of the head vs the sheet's, rows v 40–85, mean | 6.4 px | 6.4 px (unchanged, row for row) |
| Sockets, front: boxes (sheet: 16 × 18, 20 × 17 px) | 17 × 16, 27 × 21 | 19 × 15, 27 × 21 |
| Sockets, three-quarter: boxes (sheet: 14 × 17, 22 × 20 px) | 6 × 15, 31 × 28 | 8 × 13, 31 × 28 |
| Pupils, front / three-quarter, offsets from the sheet's | (+1, +7) (+3, +5) / (−7, −2) (−7, −1) | the same |
| Lower teeth vs the three-quarter panel, root / tip | 3.3 / 20.1 px | 3.3 / **18.5** px |
| Lower teeth vs the front panel, root / tip | 3.2 / **5.0** px | 3.2 / 7.2 px |
| Lower teeth vs the side panel, root / tip | 6.4 / **12.0** px | 6.4 / 16.2 px |
| Gaps between the teeth, median brightness (sheet: 0.149 / 0.141) | 0.082 / 0.086 | 0.071 / 0.082 |
| Body seen through the mouth, three-quarter / front | 1 / 3 px | 1 / 3 px |

How each measure is computed:
- **From the model's geometry** (`v15_mouth_check.py`): rays through every pixel of the box between the jaws from the sheet's front and three-quarter cameras, sorted by what they hit. A hit on the floor, inner walls, throat, palate, cheek flesh or the inside of the cranium counts as interior; a hit on a tooth counts as teeth.
- **Also from the geometry:** the jaw (`v12_jaw_check.py`); the head outline (`measure_head_v8.py`, `measure_side_profile_v9.py`); the crossings (`v11_teeth_check.py`, triangle intersections per tooth pair); the plan against the sheet's annotations and the lengthened teeth (`v15_anatomy_check.py`).
- **From the renders** (`v15_mouth_check.py`, `measure_mouth_v10.py`, `v11_teeth_check.py`): the dark and ivory pixels, the sockets, the pupils and the gap brightness.
- **The teeth-hidden opening:** with the teeth shown, `measure_mouth_v10.py`'s three-quarter mouth region falls from 0.685 to 0.432. Its colour classes call the longer teeth in shadow "rust", which leaves holes in the region. With the teeth hidden the opening is V14's exactly, so that is the figure given.

## Remaining differences (honest)

- **The middle of the opening.** A dark pocket remains between the chin's middle teeth and the upper front teeth. Those are front teeth, not posterior ones, and the brief keeps them. The sheet has a pocket there too, above its short centre tooth, but a smaller one.
- **Why the gap cannot close like the sheet's.** The three-quarter panel draws the lower roots about 10 px higher than V14's jaw stands. The jaw is kept, so its teeth start lower. The dark area is 22% down from V14's but still 28% above the sheet's (three-quarter); in front it is 19% down and 33% above.
- **Longer than the sheet draws them.** In the sheet's three-quarter panel, the upper teeth behind the near corner are short; V15's are now medium-long (as the brief asks). In the side panel the lengthened teeth's tips are further from the sheet's annotated tips (lower teeth 16.2 px against V14's 12.0). In the three-quarter panel they are closer (18.5 against 20.1).
- **Two teeth short of their goal.** U6 (snapped) stopped at 0.38 of 0.47: its neighbours U5 and U7 leave no clear path. L15 cannot grow at all without entering the cheek.
- **Lower teeth's lean in three-quarter.** Still about 18° further left than the three-quarter panel draws them. They follow the side panel's fan, as in V14.
- **Eyes.** The lips make the openings' inner top corners slant. The holes, their spacing and the pupils are V14's, and the outer corners stay square, but the visible dark area is about a fifth smaller in front. The pupils keep V14's offsets from the sheet.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V15

V15 needs scikit-image, as V10–V14 do:

```bash
bvenv/bin/python scripts/build_v15.py
```

Render from a copy, because `render_views.py` saves the file it renders. Three views, then the side view with the side light:

```bash
cp model/out_there_monster_v15.blend /tmp/v15_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v15_copy.blend /tmp/v15r fit34 sheet_front sheet_side
```

```bash
cp model/out_there_monster_v15.blend /tmp/v15_copy.blend && SIDE_KEY=700 STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 bvenv/bin/python scripts/render_views.py /tmp/v15_copy.blend /tmp/v15rs sheet_side
```

For the teeth-and-pupils-hidden renders, set `hide_render` on `Teeth_Upper`, `Teeth_Lower` and `Eyes` in a copy, then render it the same way.

Checks:

```bash
bvenv/bin/python scripts/v15_anatomy_check.py model/out_there_monster_v15.blend /tmp/v15 front=/tmp/v15r/sheet_front.png side=/tmp/v15rs/sheet_side.png 34=/tmp/v15r/fit34.png
```

```bash
bvenv/bin/python scripts/v15_mouth_check.py model/out_there_monster_v15.blend front=/tmp/v15r/sheet_front.png 34=/tmp/v15r/fit34.png
```

```bash
bvenv/bin/python scripts/v11_teeth_check.py model/out_there_monster_v15.blend front=/tmp/v15r/sheet_front.png 34=/tmp/v15r/fit34.png
```

```bash
bvenv/bin/python scripts/v12_jaw_check.py model/out_there_monster_v14.blend model/out_there_monster_v15.blend
```

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v15 model/out_there_monster_v15.blend /tmp/v15r
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v14.blend model/out_there_monster_v15.blend
```

Put the renders and overlays into `model/renders_v15/` under the names listed in `v15_compare.py`'s docstring, with V14's alongside, then:

```bash
bvenv/bin/python scripts/v15_compare.py model/renders_v15 references model/renders_v15
```
