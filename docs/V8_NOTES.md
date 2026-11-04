# V8 — head-only correction to the approved sheet

Target: the approved sheet's head (`references/r08_open_jaw_sheet_v2.webp`), in its three-quarter
view first, with the front and exact-side views as checks. **New file:**
`model/out_there_monster_v8.blend` (`scripts/build_v8.py`, `head_v8.py`).

**Unchanged:**
- V7 (`model/out_there_monster_v7.blend`, md5 `ddf429657fcfdafa03b1b86ae04220f1`).
- V8's body. The build opens the V7 file, removes only the head objects and builds the new head
  on the same mount (same position, hinge and neck). Before saving, it checks the torso, arms,
  legs and bars vertex by vertex against V7. Result: `BODY UNCHANGED (vertex-identical to v7):
  True`.
- The cameras. All renders use V7's: the three-quarter view uses V7's fitted `fit34` camera
  (FIT34 string below); front and side use the sheet's panels as orthographic cameras.

Renders and comparison sheets: `model/renders_v8/`.

## What changed (head geometry only)

| Part | V8 (V7) |
|---|---|
| Skull silhouette | V7's long skull is kept in length and width; the upper skull is reshaped. The top falls about 7 cm toward the monster's right-front corner, where both the three-quarter and front views show the skull lower, and rises to a crown about two-thirds back, as in the side view. The forehead is a little lower, and the back edge is rounded and broken off. The cranium narrows behind the face (up to 26 % at the top-back), so its side recedes in the three-quarter view as the sheet shows, while the front view still sees the face's full width. V7: a level, rectangular slab. |
| Forehead and face | Irregular, uneven planes instead of one flat sloped panel. The face angles back on both sides of a central nasal ridge, which stays the side view's forward outline. Brow ledges overhang the sockets. |
| Surface | 26 rust fragments built into the upper skull, raised or broken out with crisp edges and uneven sizes. Seven uneven plates (raised and sunken), ten planar breaks, smaller and more irregular low-poly facets (210 instead of 120 large planes), and a lumpier base form. Same rust colours and damage style; no plates added on top. |
| Eye sockets | Irregular six-sided voids at the sheet's positions, about 0.10 m across (V7: about 0.14 m wide). The right socket sits lower; both top edges slope down toward the nose. Each sits in a shallow orbit with a stepped, chipped rim, deep black inside, with tiny red pupils still visible from the three-quarter view. |
| Mouth | Uneven upper gum line (dipping at the corners, higher on the monster's left) with a fuller dark-red gum rim. The lower jaw is leaner and narrower: a V-shaped rim rather than a solid bar. It is asymmetric (bulging on its right side, slightly twisted, rim dipping) and ends in a narrow, off-centre chin. The opening stays tall and V-shaped, with a dark interior. |
| Teeth | 36, the same as V7: 21 upper (a crowded front row of 11 in uneven clusters, 5 along each side) and 15 lower, angled inward along the V. Uneven gaps, lengths, tilts (up to ±21°) and curls; a few snapped. The longest fangs sit left of centre in the upper row. 12 % shorter and slightly fuller than V7's, in the same aged ivory material. |
| Knobs | V7's two crown knobs, moved to where the sheet shows them: top back-left and back edge. No new spikes or parts. |

## Validation (same cameras for V7 and V8, `scripts/measure_head_v8.py`)

| | V7 | V8 |
|---|---|---|
| Three-quarter: head overlap (IoU) | 0.894 | **0.905** |
| Three-quarter: top outline of the head, mean distance | 8.4 px | **4.2 px** |
| Three-quarter: face's left outline, mean distance | 7.1 px | **3.4 px** |
| Three-quarter: pupils vs sheet (R, L) | (−10, −7), (−3, −7) | (−9, 0), (−6, +1) |
| Front: head overlap | **0.948** | 0.939 |
| Front: pupils vs sheet (R, L) | (+7, +2), (+12, −1) | (+5, −2), (+4, +7) |
| Side: head overlap | **0.860** | 0.830 |

Pixel figures are panel pixels; the three-quarter panel is 508 px wide, and the head is about
110 px wide in it.

Three-quarter camera:
`FIT34=0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45`.

## Remaining differences (honest)

- **Eye position conflict.** The pupils still sit 6–9 px left of the sheet's in the
  three-quarter view, while in the front view the left one is 4 px right of the sheet's. The
  sheet's front and three-quarter views disagree on where the face is. No head position satisfies
  both, and the camera was not changed. The angled face moves the eyes as far toward the
  three-quarter position as the front view allows.
- **Front and side trade-off.** Front and side head overlap is slightly lower than V7's (−0.01 and
  −0.03), from three changes made for the three-quarter view:
  - the lower right-front corner;
  - the lower forehead (the side view's forehead outline sits about 4 px low);
  - the leaner jaw (the sheet's side view shows a thicker jaw-and-teeth mass at the chin).
- **Surface.** The sheet's skull is still chunkier and darker: a dense mosaic of plates with dark
  seams and star-shaped holes. V8's surface is more irregular than V7's but lighter in tone.
  Per the brief, the colour palette and material were not changed.
- **Teeth.** The sheet's mouth looks more crowded than V8's 36 teeth. No teeth were added beyond
  V7's count.
- **Hidden contact.** The jaw's rear sits inside the neck at the hinge (971 overlapping face
  pairs, as in V7), and is not visible.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V8

```bash
bvenv/bin/python scripts/build_v8.py
```

Render from a copy, because `render_views.py` saves the file it renders:

```bash
cp model/out_there_monster_v8.blend /tmp/v8_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v8_copy.blend /tmp/v8r fit34 sheet_front sheet_side
```

Head measurement. The third argument is a folder holding the renders `fit34.png` and
`sheet_front.png`, used for the pupil positions:

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v8 model/out_there_monster_v8.blend /tmp/v8r
```

Copy the renders into `model/renders_v8/` as `v8_fit34.png`, `v8_front.png` and `v8_side.png`.
Copy V7's from `model/renders_v7/` as `v7_*.png`, and the head overlays as
`<v7|v8>_head_<view>.png`. Then:

```bash
bvenv/bin/python scripts/v8_compare.py model/renders_v8 references model/renders_v8
```
