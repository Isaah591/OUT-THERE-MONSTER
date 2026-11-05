# V9 — head reconstruction on V8's unchanged body

Target: the approved sheet's head (`references/r08_open_jaw_sheet_v2.webp`). The three-quarter and
exact-side views were matched together; the front view is a check. **New file:**
`model/out_there_monster_v9.blend` (`scripts/build_v9.py`, `head_v9.py`).

The brief: V8's head reads as a rectangular armour shell with a large mouth cut into it, while the
sheet shows a damaged, irregular skull around an enormous skeletal mouth. V9 therefore rebuilds
the underlying shapes rather than varying V8's head. The cranium is built from new sections, and
the upper jaw, lower jaw, teeth and tissue are new.

**Unchanged:**
- V8 (`model/out_there_monster_v8.blend`, md5 `6db0e33cb94532012fe6a33877a67e8f`) and every
  earlier version.
- V9's body. The build opens V8, removes only the head objects, and builds the new head on the
  same mount (same position, hinge and neck). Before saving it checks the torso, arms, legs and
  bars vertex by vertex against V8. Result: `BODY UNCHANGED (vertex-identical to v8/v7): True`.
- Body materials, pose and proportions.
- The cameras. Every render uses V7's cameras: the fitted `fit34` for the three-quarter view, and
  the sheet's panels as orthographic cameras for the front and exact side.

Renders and comparison sheets: `model/renders_v9/`.

## What changed (head only)

| Part | V9 (V8) |
|---|---|
| Skull | **Sections:** rounded, skull-like cross sections (V8: box-like). **Profile:** the side view's dome; the forehead climbs from the snout to the crown in one curve. V8's brow stood about 3 cm proud of the sheet's profile, and above it the forehead was set 5–18 cm too far back. Side-view front outline, mean distance from the sheet: 4.1 px (V8: 10.4). **Kept from V8:** the top still falls toward the monster's right-front corner, and the cranium still narrows behind the face (three-quarter and front views). **Fragmentation:** 52 rust fragments raised or broken out (V8: 26), 230 knife facets (V8: 210), wider cracks, more chipped edges; the same 8 planar breaks. |
| Mouth frame | **Upper jaw:** a broken bony rim around a vaulted palate. Its lower edge is jagged and notched between the teeth, and the breaks go up into the bone. **Cheeks:** behind the snout the gape tears up into both sides of the skull, larger and higher on the left (the side view's torn area), exposing dark red tissue. **Inner walls:** dark, only at the rear, so the gape reads open rather than enclosed. |
| Lower jaw | An elongated skeletal V, not a chin. The bone is about 40 % shallower: 5–8 cm below the rim against V8's 10–13 cm. The tip is pointed: 8 cm wide over its last 6 cm, against V8's 12 cm. It opens at 64° (V8: 53°) and hangs lower, its lowest point at z 1.59 m (V8: 1.65 m). Its open trough is deeper. In the side view it now lies on the sheet's diagonal (see *Validation*). |
| Teeth | 36, the same count as V8, re-arranged. **Upper, 16 (V8: 21):** crowded at the front of the snout, long fangs forward, and none at the rear of the upper jaw, where the sheet shows the torn cheek. **Lower, 20 (V8: 15):** a dense fan over the front four fifths of the jaw. They lean up and forward, about 40° from vertical once the jaw is open, and overlap. Uneven lengths, gaps, tilts and curls; a few snapped. Same aged ivory material. |
| Red tissue | All of it restrained and dark maroon, in a new head-only material (`M_V9_Tissue`). **Gums:** thin and uneven along both jaws, the upper one partly set into the bone. **Hinge webs:** fine membranes with rounded tears and a ragged front edge. **Strands:** 8 thin, sagging strands between the jaws, some snapped. **Torn cheeks:** exposed flesh. |
| Eyes | V8's sockets and pupils: same positions, size and depth, in a more broken surround. |
| Knobs | V8's two crown knobs; no new parts, spikes or plates. They are now placed on the crown and on the back-left corner, independent of the random surface detail. |

### Defects found in the first V9 renders and corrected before saving

- **Beak:** a chunk of the face hung about 9 cm below the gum line between the front fangs. The
  jagged-rim noise was unbounded downward.
- **Hole into the left eye socket:** the palate vault broke through into the socket, so a pale,
  wet surface showed inside it. The vault is now capped below the socket floors.
- **Tissue:** the gums were salmon pink and read as tubes, and the hinge webs were flat panels
  with stair-stepped holes. The tissue is now darker and more saturated, the gums thinner and
  partly embedded, and the webs fine and torn.
- **Side profile:** the brow stood out and the forehead was low (the profile fix above).

The random layout of the skull fragments moves the head outline by a few pixels. The layout used
(seed 71) is the best of eight tried against the three views' outlines.

## Validation

Same cameras for V8 and V9. The tools are `scripts/measure_head_v8.py` (head-box overlap,
outlines, pupils) and `scripts/measure_side_profile_v9.py` (side-view forehead profile and jaw).

| | V8 | V9 |
|---|---|---|
| Three-quarter: head overlap (IoU) | **0.905** | 0.902 |
| Three-quarter: top outline of the head, mean distance | **4.2 px** | 4.6 px |
| Three-quarter: face's left outline, mean distance | 3.4 px | **3.3 px** |
| Three-quarter: pupils vs sheet (R, L) | (−9, 0), (−6, +1) | (−7, 0), (−7, 0) |
| Side: head overlap (IoU) | 0.830 | **0.847** |
| Side: front outline (forehead, brow, snout), rows 40–85 | 10.4 px | **4.1 px** |
| Side: top outline, columns 90–220 | 3.4 px | **2.5 px** |
| Side: jaw's lowest point (sheet's chin: (160, 231)) | (146, 218) | **(157, 227)** |
| Side: jaw angle, hinge to lowest point (sheet: 69°) | 60° | **67°** |
| Side: lowest point of the lower teeth | v 203 | v 223 |
| Front: head overlap (IoU) | 0.939 | **0.940** |
| Front: top outline of the head | 7.3 px | 7.1 px |
| Front: pupils vs sheet (R, L) | (+5, −2), (+4, +7) | (+1, +9), (+5, +6) |

Pixel figures are panel pixels.
- Three-quarter: the panel is 508 px wide, and the head about 110 px wide in it.
- Side: 150 px per metre.

Three-quarter camera:
`FIT34=0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45`.

**The jaw's opening is a compromise.** At 66° the chin lands within 2 px of the sheet's and the
angle matches (69°). But the side-view overlap drops to 0.839, because the tooth fan swings away
from the sheet's. 64° keeps the overlap and brings the chin within 3–4 px.

## Remaining differences (honest)

- **Surface.** The sheet's skull is a chunkier, darker mosaic of blocky plates with dark gaps and
  star-shaped holes. V9's is more broken than V8's but still reads as a lighter rust shell
  crossed by thin dark cracks. Per the brief, the colour palette and the body materials were not
  changed.
- **The sheet's views disagree on the face, as in V8.**
  - In the three-quarter view the pupils sit 7 px left of the sheet's.
  - In the front view they sit 6–9 px low, and the top of the head is 7 px lower than the front
    panel draws it.
  - No single head satisfies all three panels. V9 follows the three-quarter and side views.
- **Lower teeth.** In the side view the sheet's tooth fan reaches further forward, toward the
  upper teeth. V9's leaves a gap there, shown red in `_v9_head_silhouettes.png`.
- **Crowding.** The sheet's mouth looks more crowded overall. V9 keeps V8's 36 teeth,
  re-arranged, not added.
- **Red tissue** is darker and less extensive than the sheet's:
  - the sheet's large maroon torn area behind the upper teeth (side view);
  - the red rim along its lower jaw (three-quarter view).
- **Tooth roots.** A few roots read pink or dark at the mouth corners. These are the blood and
  decay tints of V8's unchanged tooth material.
- **Hidden contact.** The rear of the jaw sits inside the neck at the hinge: 991 overlapping face
  pairs (V8: 971). So do the rear ends of the tongue (109 pairs) and the lower gum (47). All of it
  is inside the neck and not visible.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V9

```bash
bvenv/bin/python scripts/build_v9.py
```

Render from a copy, because `render_views.py` saves the file it renders:

```bash
cp model/out_there_monster_v9.blend /tmp/v9_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v9_copy.blend /tmp/v9r fit34 sheet_front sheet_side
```

Head measurements. For `measure_head_v8.py`, the third argument is the render folder, used for
the pupil positions:

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v9 model/out_there_monster_v9.blend /tmp/v9r
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v8.blend model/out_there_monster_v9.blend
```

Copy the renders into `model/renders_v9/` as `v9_fit34.png`, `v9_front.png` and `v9_side.png`,
and the head overlays as `v9_head_<view>.png`. Copy V8's from `model/renders_v8/` (`v8_*.png`).
Then:

```bash
bvenv/bin/python scripts/v9_compare.py model/renders_v9 references model/renders_v9
```
