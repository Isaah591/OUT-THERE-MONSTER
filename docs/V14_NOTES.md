# V14 ("Experimental 10") — mouth curvature and the brow's expression

Target: the approved sheet (`references/r08_open_jaw_sheet_v2.webp`). The exact side panel is the reference for the jaw's curvature; its detail panels (jaw comparison, side close-up) show the same jaw closer. The brief has two corrections:
- the curved, hooked mouth, which must read from the jaw geometry with the teeth hidden;
- the heavy, scowling brow, which must read from the skull with the pupils off.

**New file:** `model/out_there_monster_v14.blend` (`scripts/build_v14.py`, `head_v14.py`).

**Unchanged:**
- V13 (`model/out_there_monster_v13.blend`, md5 `872e6c36ee3cc419153b9fe0dc774826`) and every earlier version.
- The body: `BODY UNCHANGED (vertex-identical to v13/…/v7): True`.
- The crown bracket, torn skull sides, palate and throat: `KEPT HEAD PARTS UNCHANGED: True`.
- The materials (no new ones), the colours and the cameras.
- The cranium, outside three edited zones: the upper jaw's edge, the brows and the sockets. 13,039 vertices are new and 11,808 removed, all inside those zones (checked in the build); the other 77,852 vertices are V13's, with V13's attributes.

Renders and comparison sheets: `model/renders_v14/`, with V13 alongside.
- `_v14_teeth_hidden.png`: both versions with the teeth and pupils hidden, in all three views.
- `_v14_side_lit.png` and the `*_side_lit.png` renders: the exact side under one more light on the camera's side, as the sheet's side panel is lit (`render_views.py`, `SIDE_KEY=700`). The three-quarter lighting used since V7 leaves the lower jaw's outer face in shadow from that camera, so its shape could not be judged. V13 is rendered the same way for the comparison.

## What changed (measured against the sheet)

| Feature | Approved sheet | V13 | V14 |
|---|---|---|---|
| Rear of the gape (side view) | A dark corner bounded by red tissue that curves from the upper jaw down into the lower jaw. The front of the opening shows the background through the torn cheeks. | A flat wall down the whole side of the gape. From the side it is a red sheet with a straight diagonal edge from the upper gum to the chin. | Torn tissue closes each corner, fixed along the upper jaw, round the hinge and down the lower jaw. Its free edge is read off the side panel: a curve, upright under the upper jaw and sweeping back into the lower jaw. A ragged red rim runs along it. |
| Lower jaw | Seen from the side, the jaw sweeps down in an arc and its chin curls forward (main panel and detail panels). | The tooth row was a straight bar. | The tooth row bows back by up to 10.7 px from a straight line and curls 5.6 px forward at the chin. The jaw's outer edge is still the side panel's trace (1.1 px). |
| Upper jaw's edge | Uneven: the upper roots sit at heights that vary by 8.5 px in the front panel. | A level cut (1.9 px wobble); the teeth hung from a straight shelf. | An uneven, broken edge through the roots that varies by 13.8 px and rises about 4 px toward the cheek. The upper teeth are re-seated on it and move with it. |
| Gum along the lower jaw | A continuous red line sweeping down both arms of the jaw into the chin (three-quarter and side). | A torn strip with gaps. | Unbroken and fuller up both arms, from the chin's corners to the hinges. |
| Sockets | Inner (nose-side) corners lower than the outer: about 8°, a scowl. | Tilted the other way (−7° / +6°): inner corners raised, a worried look. | Tilted ±8° the sheet's way: inner corners 2.2 and 2.4 px lower. The hole sizes are kept; they are deeper (0.19 units), and the pupils are set back 0.9 and 2.1 cm. |
| Brows | Heavy brow plates over the sockets, shading them. | None: the sockets were holes in a flat plate. | A ledge of skull over each socket: 4.8 cm out on the monster's right, 3.3 cm on its left. Each has a near-upright front, and a top that slopes 21° / 19° down toward the nose (steeper than the sockets) before stopping at the face's existing brow line. The brow notches and the plate mosaic break them up. |
| Teeth | — | Upper: V12's. Lower: on V13's rim. | Upper: V12's plan from the sheet (same widths, lengths and curls), re-seated on the new edge. Lower: on the swept rim. 17 + 16 teeth as before; none passes through another. |

## Method

**Order of work (the brief's).** The teeth were hidden first and the jaw edges and the gape's corners shaped. The comparison views (part silhouettes rasterised from the meshes, and renders with the teeth and pupils hidden) were checked before the brows. The teeth and tissue came last.

**Upper jaw's edge (`_edge_z`, `solve_upper_edge`).**
- The face block's lower boundary is no longer the plane z = GUM_Z.
- It is a surface through the front panel's upper roots, each at its own height, as V12 placed them. Small chips break it between roots, and it rises 0.045 units toward the cheek.
- The upper teeth are planned as V12 planned them (`plan_upper`); each root is then set just under the edge and its tooth moved with it.

**Lower jaw (`_top`).**
- The jaw's pose, outer edge and U are V13's.
- The rim's top along the tooth row is no longer level. Its middle is set back by `JAW_BOW` (0.085 units) on a sine and its end raised by `JAW_HOOK` (0.065 units) toward the chin. In the side view the row bows back and the chin curls forward.
- The U is re-fitted to the sheet's lower gum line with the new rim: 1.8 px in front, 2.6 px in three-quarter.

**Corners of the gape (`_corner_web`).** Each web is a membrane between two edges:
- a fixed edge: the upper jaw's edge back to the cheek, the rear block's underside down to the hinge, then the lower jaw's rim;
- a free edge: points read off the side panel. On the far (right) side, this is the boundary between the dark corner and the open front of the gape. On the near (left) side, it is the red tissue at the back corner.

A ragged tissue roll runs along each free edge. V8–V13's flat walls are gone.

**Brows and sockets (`_brows`, `SOCKETS`).** Each brow is a wedge of planes:
- underside: the socket's sloping top edge;
- front: nearly upright, `BROW` units in front of the face plate;
- top: sloping down toward the nose and back into the face, capped at the existing brow line (`BROW_TOP`) so the forehead above is untouched and neither brow juts past the nose ridge.

**Teeth never cross.** The overlap test that parts the teeth now follows each tooth's curved axis, as `tusk()` builds it; V11–V13 tested the straight root-to-tip line. Teeth that would still curl into each other curl less. The lower roots may slide a little further apart along the rim (up to 0.08 head units, 4.8 cm, instead of 0.04) where the swept row crowds them.

## Validation (same cameras and lighting for V13 and V14)

| | V13 | V14 |
|---|---|---|
| Side: tooth row's sweep, largest distance from a straight line | 0 px (straight) | **10.7 px**, curling 5.6 px forward at the chin |
| Side: jaw's rear edge vs the sheet's, mean | **0.9 px** | 1.1 px |
| Side: lowest point (sheet: (163, 231)) | (167, 230) | (167, 230) |
| Side: lower root line vs the sheet's, mean | **3.2 px** | 4.9 px (the sweep; the main side panel draws the root line nearly straight) |
| Side: gape, upper gum to the end of the lower tooth row (sheet: 111 px) | 119 px | 118 px |
| Rim (where the lower teeth stand) vs the sheet's gum line, front / three-quarter | 1.9 / **2.5** px | **1.8** / 2.6 px |
| Front: upper jaw's edge, height variation across the mouth (sheet's upper roots: 8.5 px) | 1.9 px (level) | 13.8 px |
| Sockets: inner corner vs outer (sheet: lower, about 8°) | raised | **lower, 2.2 / 2.4 px (±8°)** |
| Brow ledge over the sockets, right / left | none | 4.8 / 3.3 cm; tops 21° / 19° down toward the nose |
| Lower teeth vs the front panel, root / tip | 2.7 / 5.6 px | 3.2 / **5.0** px |
| Lower teeth vs the side panel, root / tip; lean | **3.4** / 11.7 px; 10.6° too upright | 6.4 / 12.0 px; **8.3°** too upright |
| Lower teeth vs the three-quarter panel, root / tip; lean | 3.8 / **19.0** px; 18.8° too far left | **3.3** / 20.1 px; **17.5°** too far left |
| Teeth passing visibly through each other | 0 | 0 |
| Body seen through the mouth, three-quarter / front | 0 / 4 px | 1 / 3 px |
| Head overlap (IoU), front / three-quarter / side | **0.940 / 0.917 / 0.859** | 0.939 / 0.915 / 0.850 |
| Side: front of the head vs the sheet's, rows v 40–85, mean | **5.3 px** | 6.4 px (the left brow, 8 px out at v = 60) |
| Front sockets' dark areas (sheet: 16 × 18, 20 × 17 px) | 16 × 16, 27 × 20 px | 17 × 16, 27 × 21 px |
| Three-quarter sockets' dark areas (sheet: 14 × 17, 22 × 20 px) | 5 × 16, 25 × 20 px | 6 × 15, 31 × 28 px (the brow's shadow over the left socket) |
| Gaps between the teeth, median brightness (sheet: 0.149 / 0.141) | 0.055 / 0.078 | 0.082 / 0.086 |
| Jaw, teeth, gums and floor overlapping the body (inside the neck) | 218 face pairs | 228 face pairs |

How each measure is computed:
- From the model's geometry: the side jaw (`v12_jaw_check.py`), the sweep, edge, brows, rim and teeth (`v14_anatomy_check.py`), the see-through pixels (`v14_mouth_check.py`, ray casts), the head outline (`measure_head_v8.py`, `measure_side_profile_v9.py`) and the cranium zones and overlaps (`build_v14.py`).
- From the renders: the sockets (`v14_mouth_check.py`) and the gap brightness (`v11_teeth_check.py`).

## Remaining differences (honest)

- **How far the jaw curves.** The jaw keeps the main side panel's outer edge, length and opening; the curve comes from the tooth row's sweep (10.7 px) and from the gape's curved back. The main side panel draws the root line nearly straight, so the sweep moves it 4.9 px from the sheet's on average. The detail panels show the stronger curve; the brief names the main panel as primary.
- **Red tissue.** The gum line and the corner rims now follow the curves, but the tissue material is V12's dark maroon, kept as the brief asks. In three-quarter and side views the sheet's glossy red reads brighter than ours, so the red outline of the curve is weaker than on the sheet.
- **Side lighting.** Under the three-quarter rig used since V7, the lower jaw stays dark in the exact side view; the side-light renders show its shape. Both are provided, for V13 and V14 alike.
- **Front mouth.** As in V13, it is taller than the front panel's (the jaw follows the side panel), and it is still a broad U from the front: the sheet's front outline is that shape too, stretched.
- **Eyes.**
  - The brows add shade over the sockets. In three-quarter the left socket's dark area now includes the brow's shadow (31 × 28 px against the sheet's 22 × 20). The holes themselves are the same size as V13's.
  - The pupils keep their positions, about 7 px low in front and 7 px left in three-quarter as before. The front panel draws the whole face higher than the head allows.
- **Lower teeth, three-quarter.** They still lean about 18° further left than the three-quarter panel draws them; the side panel's fan, which they follow, draws them pointing further forward.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V14

V14 needs scikit-image, as V10–V13 do:

```bash
bvenv/bin/python scripts/build_v14.py
```

Render from a copy, because `render_views.py` saves the file it renders. Three views, then the side view with the side light:

```bash
cp model/out_there_monster_v14.blend /tmp/v14_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v14_copy.blend /tmp/v14r fit34 sheet_front sheet_side
```

```bash
cp model/out_there_monster_v14.blend /tmp/v14_copy.blend && SIDE_KEY=700 STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 bvenv/bin/python scripts/render_views.py /tmp/v14_copy.blend /tmp/v14rs sheet_side
```

For the teeth-and-pupils-hidden renders, set `hide_render` on `Teeth_Upper`, `Teeth_Lower` and `Eyes` in a copy, then render it the same way.

Checks:

```bash
bvenv/bin/python scripts/v14_anatomy_check.py /tmp/v14 front=/tmp/v14r/sheet_front.png side=/tmp/v14r/sheet_side.png 34=/tmp/v14r/fit34.png
```

```bash
bvenv/bin/python scripts/v14_mouth_check.py model/out_there_monster_v14.blend front=/tmp/v14r/sheet_front.png 34=/tmp/v14r/fit34.png
```

```bash
bvenv/bin/python scripts/v12_jaw_check.py model/out_there_monster_v13.blend model/out_there_monster_v14.blend
```

```bash
bvenv/bin/python scripts/v11_teeth_check.py model/out_there_monster_v14.blend front=/tmp/v14r/sheet_front.png 34=/tmp/v14r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v14 model/out_there_monster_v14.blend /tmp/v14r
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v14.blend
```

Put the renders and overlays into `model/renders_v14/` under the names listed in `v14_compare.py`'s docstring, with V13's alongside, then:

```bash
bvenv/bin/python scripts/v14_compare.py model/renders_v14 references model/renders_v14
```
