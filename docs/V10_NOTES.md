# V10 — approved-head replication: new base shapes for the skull, jaw and mouth

Target: the approved sheet's head (`references/r08_open_jaw_sheet_v2.webp`).
- **Validation views:** the front and three-quarter panels.
- **Shape evidence:** the side panel and the sheet's four detail panels (head close-up, jaw comparison, mouth-interior detail, side-angle close-up), which earlier versions did not use.

**New file:** `model/out_there_monster_v10.blend` (`scripts/build_v10.py`, `head_v10.py`, `blocks_v10.py`).

**Unchanged:**
- **V9 and earlier versions:** V9 is `model/out_there_monster_v9.blend`, md5 `11df5ea293404629c99f7937a5553251`.
- **Body:** the build opens V9, removes only the head objects and builds the new head on the same mount. Before saving it checks the torso, arms, legs and bars vertex by vertex: `BODY UNCHANGED (vertex-identical to v9/v8/v7): True`.
- **Body materials and cameras:**
  - the three-quarter view uses V7's fitted `fit34` camera;
  - the front and side views use the sheet's panels as orthographic cameras.

Renders and comparison sheets: `model/renders_v10/`.

## Step 1 — what was geometrically wrong in V9

Each view was measured against the sheet: outlines with `measure_head_v8.py`, and interior features with the new `measure_mouth_v10.py`. The latter classifies the sheet's panel and the render pixel by pixel into rust, teeth, dark voids and red tissue (`_v10_mouth_classes.png`). The four detail panels show the head close up.

| Feature | Approved sheet | V9 (what was wrong) |
|---|---|---|
| Skull | **Construction:** an angular block of flat planes, built of blocky chunks, with stepped, notched edges and missing blocks (all four detail panels). **Front view:** the top rises to a peak, with broken corners. **Three-quarter view:** the brow line is straight. | A rounded loft: smooth, superellipse sections and a domed top, with thin cracks over it ("helmet"). |
| Forehead | A flat brow edge over the sockets, then a slope back to a crown that peaks off-centre. | A rounded dome over the face. |
| Eye sockets | Square holes cut into a flat face plate (front: 15×16 and 18×15 px). In the three-quarter view the monster's right socket is narrow (11 px), so that half of the face turns away. In the close-up it opens at the face's corner. | Irregular six-sided holes inside soft orbits. Their dark areas measure 21×13 and 19×21 px. |
| Upper jaw | A thick slab edge with a lobed maroon gum along it. The fangs hang from it. | A thin gum tube along a smooth edge. |
| Lower jaw | A broad U: in the front view the mouth stays about 90 px (0.56 m) wide for about 80 % of its height, then rounds to a wide chin. Its rim carries a red gum. | A narrow, pointed V: 0.33 m wide at its middle and 8 cm at the tip. In the front view the mouth narrows to 40 px by row 127 and 15 px at the bottom. |
| Mouth opening | Framed on both sides by the jaw's red-rimmed edges. Inside it is maroon flesh, black only in the throat. Mouth-region overlap with the sheet = 1 by definition. | Unframed: the chest shows beside the mouth, and the inside is a black void. Mouth-region overlap: front 0.52, three-quarter 0.52. |
| Teeth | Thick-rooted, faceted fangs. In the front view the lower ones stand up along the lower U. | Slender, smooth cones, with the lower ones spread along the V. |
| Tissue | Thick gums, flesh-lined cheeks, and both sides of the skull torn open onto red cords. Red pixels in the head box: front 818, three-quarter 1060. | Little tissue. Red pixels: front 565, three-quarter 153. |

**The sheet's panels disagree with each other, as in V7–V9.**
- The front panel draws the face about 7 cm higher than the three-quarter and side panels allow.
- It also places the chin far higher: z 1.90 m, against 1.57 m in the side panel.
- A perspective camera fitted to the front panel (on the body only) does not resolve this. It fits the body worse than the orthographic one (overlap 0.865 against 0.880).
- V10 therefore keeps the face height and the long jaw where the three-quarter and side panels agree. In the front view this leaves the face about 6 px low.

## What V10 builds (head only)

The skull and the jaw are signed-distance volumes made of planes and boxes, meshed by marching cubes (`blocks_v10.py`). This gives flat faces, crisp stepped breaks and real holes, which V9's displaced loft could not produce.

| Part | V10 |
|---|---|
| Skull | **Planes:** a vertical face plate angled back from a nasal ridge, the right half steeply (about 33°); a brow leaning back; a straight brow line over a forehead slope; and a gable crown rising to an off-centre ridge (the front view's peak). **Sides and corners:** the sides narrow toward the back and the right side narrows toward the face, so the right socket opens at the corner. The right-front corner drops. **Breaks:** 17 stepped notches and 6 proud chunks, one of them the broken-up right top corner. **Mosaic:** irregular, mostly rectilinear plates that step out or in, some missing, parted by seams. **Tears:** stepped diagonal tears in both sides (larger on the left), from behind the brow down to the hinge. |
| Sockets | Square holes cut into the face plate, each inside a stepped frame. Positions as V9 (the three-quarter view's pupils); depth measured from the angled face. |
| Upper jaw | The face plate's broken lower edge over a vaulted palate, with a thick, lobed maroon gum swelling around each root. |
| Lower jaw | A broad, skeletal U of blocky bone: two rami and a wide chin. It is 0.61 m wide at its middle (V9: 0.33 m) and 0.28 m wide at the chin (V9: 8 cm). **Asymmetry:** the right side bulges, the left rim dips, and the chin's right corner is broken off. **Tissue:** a lobed maroon gum along the rim and a sagging flesh floor. **Length and opening:** kept from V9 (64°). Side-view jaw angle 68° (the sheet's 69°); its lowest point is 2 px below and 2 px forward of the sheet's chin. |
| Teeth | 36, as in V9, re-arranged: 16 upper and 20 lower. **Shape:** thick-rooted, faceted fangs (seven flat sides, a swollen root, a slight twist; a few snapped). **Upper:** 9 across the front, crowded, with uneven gaps and the longest fangs just right of the middle; shorter at the corners; plus 4 + 3 along the sides. **Lower:** 20 along the front two thirds of the U, standing up with little inward lean; the longest at the chin's corners. |
| Tissue | Head-only flesh material `M_V10_Flesh`: dark, wet maroon with little sheen. It covers the gums, the torn cheek walls at the gape, the jaw's floor, 8 sagging strands between the jaws, and the torn skull sides, which have a dark backing with cords hanging across. The throat stays black. |
| Knobs | V9's two crown knobs. No new parts. |

## Validation

Same cameras for V9 and V10.

| | V9 | V10 |
|---|---|---|
| **Front: head overlap (IoU)** | 0.940 | **0.941** |
| Front: top outline, mean distance | 7.1 px | **6.6 px** |
| Front: left outline | **6.0 px** | 7.1 px |
| **Front: mouth-region overlap** | 0.517 | **0.679** |
| Front: red tissue in the head box (sheet: 818 px) | 565 px | 1296 px |
| Front: pupils vs sheet (R, L) | (+1, +9), (+5, +6) | (+1, +7), (+4, +5) |
| **Three-quarter: head overlap (IoU)** | 0.902 | **0.917** |
| Three-quarter: top outline | **4.6 px** | 5.1 px |
| Three-quarter: left outline | **3.3 px** | 4.6 px |
| **Three-quarter: mouth-region overlap** | 0.518 | **0.579** |
| Three-quarter: red tissue (sheet: 1060 px) | 153 px | **988 px** |
| Three-quarter: pupils vs sheet (R, L) | (−7, 0), (−7, 0) | (−7, −2), (−8, −1) |
| Side: head overlap (IoU) | **0.847** | 0.827 |
| Side: jaw angle, hinge to lowest point (sheet: 69°) | 67° | **68°** |

Pixel figures are panel pixels. The three-quarter panel is 508 px wide, with the head about 110 px wide in it. Front: 160 px per metre.

Tools:
- `measure_head_v8.py`: head-box overlap, outlines, pupils.
- `measure_mouth_v10.py`: mouth region, sockets, teeth and tissue.
- `measure_side_profile_v9.py`: jaw angle.

## Remaining differences (honest)

- **Surface tone.** The sheet's skull reads darker and chunkier. V10's plates read lighter, more like flaking plates. Per the brief, the rust material and palette were not changed.
- **Face height in the front view.** The pupils sit 5–7 px low and the head's top 7 px low, as explained in Step 1. In the three-quarter view the pupils sit 7–8 px left of the sheet's.
- **Teeth.** The sheet's mouth looks more crowded, and its upper fangs splay more at the corners. V10 keeps V9's 36 teeth, re-arranged.
- **Knobs.** The sheet's front view shows a knob at the monster's right top corner. V10 keeps V9's two knobs (no new components) and has a broken corner block there instead.
- **Tears.** The torn sides are stepped and planar. The sheet's are more fibrous at the edges.
- **Side view.** Its overlap fell by 0.02 (0.847 to 0.827): the broader jaw and the stepped skull edges. The side view was not a V10 validation view.
- **Hidden contact.** The jaw's rear and its flesh floor sit inside the neck at the hinge (943 and 238 overlapping face pairs) and are not visible.
- **Not done (held for approval):** baked textures, Roblox export, rig.

## Rebuilding V10

V10 needs scikit-image for marching cubes:

```bash
bvenv/bin/pip install scikit-image
```

```bash
bvenv/bin/python scripts/build_v10.py
```

Render from a copy, because `render_views.py` saves the file it renders:

```bash
cp model/out_there_monster_v10.blend /tmp/v10_copy.blend && STUDIO=sheet STUDIO_BG=0.01 SAMPLES=32 FIT34="0.434346,0.0558458,22.9893,252.175,-0.21544,-0.00356052,-0.764,-0.55,1.45" bvenv/bin/python scripts/render_views.py /tmp/v10_copy.blend /tmp/v10r fit34 sheet_front sheet_side
```

Measurements:

```bash
bvenv/bin/python scripts/measure_head_v8.py /tmp/v10 model/out_there_monster_v10.blend /tmp/v10r
```

```bash
bvenv/bin/python scripts/measure_mouth_v10.py /tmp/v10 front=/tmp/v10r/sheet_front.png 34=/tmp/v10r/fit34.png
```

```bash
bvenv/bin/python scripts/measure_side_profile_v9.py model/out_there_monster_v10.blend
```

Copy the renders into `model/renders_v10/` as `v10_fit34.png`, `v10_front.png` and `v10_side.png`. Copy the overlays as `v10_head_<view>.png` and the class maps as `v10_classes_<front|34>.png`. Add V9's (`v9_*.png` from `model/renders_v9/`, and its class maps from the same tool). Then:

```bash
bvenv/bin/python scripts/v10_compare.py model/renders_v10 references model/renders_v10
```
