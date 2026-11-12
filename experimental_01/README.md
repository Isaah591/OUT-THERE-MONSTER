# ASTRA R08 — Experimental Model 01 (independent reconstruction, from scratch)

A new 3D model of the creature on the approved sheet
(`references/r08_open_jaw_sheet_v2.webp`, *ASTRA R08 – MORE OPEN JAW VERSION (SLIGHTLY LONGER
TEETH ONLY)*), built in a blank Blender scene by Python.

**Independence.** Nothing from the fifteen earlier builds is used: no `.blend` is opened, no mesh
or measurement file is read, and none of the scripts in `scripts/` is imported. The only inputs
are the approved sheet and Blender itself (as the `bpy` module, as the rest of the repository
uses it). Every number in the model was re-read from the sheet for this build
(`src/measure_sheet.py`, and the readings quoted beside each block in `src/body.py` and
`src/head.py`).

| | |
|---|---|
| Model | `model/astra_r08_exp01.blend` — 937,444 triangles, 2.85 m tall |
| Presentation sheet | `renders/ASTRA_R08_EXP01_sheet.png` |
| Comparison with the approved sheet | `renders/ASTRA_R08_EXP01_vs_approved.png` |
| Outline check | `renders/silhouette_check.png` |
| Single views | `renders/front.png`, `tq.png` (three-quarter), `side.png` (exact side), `head.png` (head close-up), `mouth.png` (mouth close-up), `mouthside.png` (mouth, exact side profile), `jawside.png` and `sideclose.png` (the sheet's two side-angle close-ups) |
| Measurements | `analysis/model_stats.json`, `analysis/mouth_fill.json`, `analysis/silhouette_iou.json` |

## What was asked for, and where it is in the model

| Brief | In the model |
|---|---|
| Tall, hunched, forward-leaning; compact broad torso | Torso block leaning 39° forward with a hunched upper back and deep chest; the head hangs 1.76 m ahead of the hips (exact side view) |
| Extremely long arms, uneven | Right arm 2.48 m long, bent, thickening to a blunt hollow-looking end that rests on the floor ahead of the feet; left arm 1.67 m, ending at knee height |
| Bent, digitigrade-looking legs, large block feet | Separate thigh, shin (with a knee block), ankle block, foot and four block toes per leg; right leg strides forward, left trails; knees ahead of the ankles |
| Rusty fragmented armour, dark cracks, damaged edges | Every surface carries a shell of rust slabs cut from small cells: four overlapping strata, each slab with its own height, tilt and tone, stepped chipped outlines, pits; all geometry (see *Plates* below) |
| Exposed dark red tissue | Where the shell is torn the under-surface is sunk and red, with muscle fibres lying in the hole; 41 wounds placed where the sheet shows them |
| Rods and debris | 15 rusted bars driven into head, shoulders, back, flank, both arms and shins |
| Block-like battered skull, uneven overlapping plates | Short vertical mask, brow slabs, nasal plate, domed cranium with broken crown plates, cheek and occiput blocks — separate overlapping pieces, each plated |
| Two recessed black square sockets, tiny red pupils | 11 × 11 cm and 13 × 11 cm openings, 9 cm deep, black inside; 14 mm emissive pupils set toward the inner-lower corner |
| Heavy brow, inner ends sloping down, not symmetrical | Brow slabs drop 20° (right) and 15° (left) toward the nose and hood the inner corners; the two sockets differ in width, height and pupil position |
| Mouth: irregular, curved, hooked; upper contour dips in the middle; lower jaw descends and sweeps inward | Upper lip line dips 11 cm to a blunt point right of centre, corners higher (left corner highest). Lower jaw rim is a 3D curve: a narrow U hanging 66 cm below the lip, sweeping inward and hooking 13 cm forward at the chin, asymmetric |
| Long yellowed teeth, uneven, crooked, tapered, in red gums | 67 teeth modelled one by one (32 upper, 35 lower), 15–39 cm, each an irregular 5–7-sided spike with its own length, thickness, lean, bend and twist; each stands in a rise of gum |
| Teeth fill the opening; rear teeth as long as the front | Two rows per jaw, with extra standing teeth across the middle of the lower jaw. Rear upper teeth 25–33 cm (front 15–37 cm). Teeth cover 40 % of the mouth opening in the head close-up (sheet: 28 %), see *Checks* |
| Real 3D jaw curvature, teeth placed on the curved jaws, nothing faked by texture or camera | Upper teeth root along the lip line and both sides of the upper jaw; lower teeth along the rim curve, fanning forward and up. The same model is rendered from every angle |
| Stylised, low-poly, damaged; not smooth, shiny or realistic | Planar blocks, flat-shaded slabs and faceted teeth; matte rust; only the tissue is wet |

## How it is built

Units metres, Z up, the creature faces −Y, its left is +X.

**Reading the sheet** (`src/sheet.py`, `src/measure_sheet.py`). The sheet's eight pictures are
cut out and the creature is masked from the grey studio. Heights, widths and depths are read
from the three body panels with the figure taken as 2.8 m tall; the head and mouth are read from
the close-ups in units of the mask width and the gape. The panels do not agree with one another
exactly (they are separate pictures): the head is 32 % of the height in the front view, 39 % in
the three-quarter view and 42 % in the side view, and the gape is 4–6 socket-widths depending on
the panel. One 3D model cannot match all of them; the choices are noted in `src/head.py`.

**Blocks** (`src/kernel.py`, `src/body.py`, `src/head.py`). Each part is first a low-poly solid
of planar faces: beams with a chamfered-rectangle section for torso and limbs, hand-placed
hexahedra and a ten-sided lofted cranium for the head, a free-section loft swept along the jaw
rim for the lower jaw.

**Plates** (`kernel.build_shell`). Every plated face is cut into ~1–1.7 cm cells; cells are
grouped into slabs by a noisy nearest-seed rule (so outlines come out stepped and chipped), and
each slab is raised to its own height with its own tilt and closed with side walls. Four strata
with different seed lattices overlap. At the edges of the blocks the slabs are mitred so corners
close. Cells are knocked out as pits; inside a wound zone the slabs are removed stratum by
stratum, the under-surface is sunk up to 5 cm and coloured as tissue, and muscle fibres are laid
in the hole.

**Pose** (`src/fit_pose.py`). Joints and limb thicknesses were first set from the readings, then
polished by coordinate descent on the overlap of the model's silhouette with the sheet's three
body panels (bounded to ±10 cm), and finally corrected by hand where the three panels pull in
different directions. Camera framing for the three body views comes from the same fit
(`analysis/cameras.json`).

**Head.** Coordinates: x sideways, b back from the snout, h above the upper jaw line.
The mask is a 7 × 4 grid of points (lip, socket floors, socket tops, brow) so the sockets and
the dip of the lip are set directly from the front view. The lower jaw is a loft along the rim
curve `RIM` (18 points from the right hinge round the chin to the left hinge) with a gum band on
its front face. Teeth come from five tables (upper front, upper sides, upper inner row, lower
rim, lower inner row); neighbours stand at alternate depths, and a relaxation step then slides
roots along the gum (≤ 2.6 cm) and leans teeth (≤ 7.5°) until none passes through another (a
tooth still touching a neighbour after that is thinned slightly). The inner rows stand in pads
of gum behind the lip and inside the jaw rim.

**Materials and studio** (`src/scene.py`). Procedural: rust (slab tone, mottling at three
scales, pits, orange oxidised edges, dark walls), under-surface / tissue, muscle, gum, dirty
ivory with lengthwise grooves, rods, emissive pupils, near-black mouth lining with a dark-red
sheen. One studio rig (key, fill, front, rim, top, backdrop) hangs from a single empty that is
turned with the camera, so every view is lit the same way.

## Checks

| Check | Result |
|---|---|
| Silhouette overlap (IoU) with the sheet's panels, as framed | front 0.80, three-quarter 0.75, side 0.78 (`renders/silhouette_check.png`) |
| Teeth as a share of the mouth opening, head close-up | model 40 %, sheet 28 % |
| Dark as a share of the mouth opening, head close-up | model 32 %, sheet 37 % |
| Largest unbroken dark patch in the opening, head close-up | model 29 %, sheet 28 % |
| Teeth passing through one another | 0 (21 pairs as first placed) |
| Rear upper teeth vs front | rear 25–33 cm; front 15–37 cm |

The mouth figures come from `src/mouth_check.py`: the opening (lip line and jaw rim, projected
with the view's camera) is cut out of the picture and its pixels are sorted by colour; the same
sort is run on the sheet's head close-up inside an outline traced from it.

## Where it still differs from the sheet

- **Proportions are a compromise.** The model's head is 40 % of the height (sheet: 32, 39
  and 42 % in its three views), so it is a little large for the front view and a little small
  for the side view. Silhouettes overlap the panels by about 0.8, not 1.0.
- **The skull is more regular than the sheet's.** Its outline is made of straight-edged blocks
  with stepped plates on them; the sheet's skull has larger, more broken plates and a rougher
  outline, particularly along the brow and the crown.
- **Plates are in the sheet's language, not copies.** Stepped rust slabs in overlapping strata
  with orange torn edges and pits — but the layout is generated, so no individual plate matches.
- **Wounds.** Placement follows the sheet; the tissue is modelled as fibres in a sunk hole and
  reads more ropey than the sheet's.
- **Teeth.** Deliberately fuller than the sheet where the brief asks for it (more of the opening
  covered, rear teeth long), so the model has more teeth than can be counted on the sheet.
  Tooth-for-tooth positions follow the sheet only for the prominent ones (the long fang at the
  lip point, the thick fang left of centre, the long pair at the right corner); the rest are
  placed for the overall look. The largest unbroken dark patch in the mouth is about the same
  size as the sheet's, not smaller.
- **Left cheek.** The torn temple and the sinews running into the gum band are there, but
  simpler than the sheet's knotted mass.
- **No rig, UVs or baked textures**; about a million triangles. This is a design model.

## Rebuilding

```bash
python3.11 -m venv bvenv && bvenv/bin/pip install bpy pillow "scipy<1.14" scikit-image
```

```bash
bvenv/bin/python experimental_01/src/build.py
```

```bash
SAMPLES=96 RES=1300 bvenv/bin/python experimental_01/src/render.py experimental_01/model/astra_r08_exp01.blend experimental_01/renders front tq side
```

```bash
SAMPLES=96 RES=1200 bvenv/bin/python experimental_01/src/render.py experimental_01/model/astra_r08_exp01.blend experimental_01/renders head mouth mouthside jawside sideclose
```

```bash
bvenv/bin/python experimental_01/src/make_sheets.py && bvenv/bin/python experimental_01/src/report.py && bvenv/bin/python experimental_01/src/make_sheets.py
```

The build takes about 7 s; each final view 4–7 minutes on four CPU cores (Cycles, no GPU).
`src/fit_views.py` and `src/fit_pose.py --cams` repeat the silhouette checks without rendering.

| File | Contents |
|---|---|
| `src/sheet.py`, `measure_sheet.py` | Panel rectangles, creature masks, silhouette measurements of the sheet |
| `src/kernel.py` | Geometry kernel: blocks, lofts, mitred offsets, the plate shell, wounds, muscle fibres, rods, teeth, tubes |
| `src/model.py` | Container: parts with their wounds, loose pieces, output meshes |
| `src/body.py` | Torso, arms, legs, feet, neck, rods, wound placement; the pose |
| `src/head.py` | Mask and sockets, brows, cranium, lower jaw, teeth tables and relaxation, gums, sinews, mouth lining, pupils |
| `src/scene.py` | Blender meshes from numpy, materials, studio rig, cameras |
| `src/views.py` | The cameras (one per sheet panel, plus the exact mouth profile) |
| `src/build.py`, `render.py` | Build the `.blend`; render named views |
| `src/fit_pose.py`, `fit_views.py` | Silhouette fit of cameras / joints; silhouette check |
| `src/compare.py`, `mouth_check.py`, `report.py`, `make_sheets.py` | Comparisons, mouth-fill measurement, statistics, the two sheets |
| `src/preview.py` | Fast software preview used while modelling |
