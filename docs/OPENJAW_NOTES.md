# ASTRA R08 – MORE OPEN JAW: reconstruction notes

Primary reference: `references/r08_open_jaw_sheet.webp`. The earlier R08 sheet is still used
for material and construction checks. Model: `model/out_there_monster_openjaw.blend`
(build: `scripts/build_openjaw.py`). The previous version is checkpointed in
`checkpoints/r08-hd-v1/` and is still rebuildable with `scripts/build_r08.py`.

## What the new sheet asks for (measured on its panels)

Measured relative to the skull width H, against the R08 HD build:

| | R08 HD build | New sheet |
|---|---|---|
| Pose | upright, slight hunch | crouched predator: torso leaning ~30–35°, head thrust well ahead of the shoulders, knees bent forward, hips back, long arm planted on the ground ahead and out to the side like a front leg |
| Torso width | 1.6–1.7 H | ~1.4 H, compact block |
| Limb thickness | 0.75–0.85 H (club-like long arm) | ~0.55 H (slim long arm) |
| Leg length | ~2.0 H | ~2.7 H |
| Jaw | 66° about a hinge at the shoulder line, jaw ~0.44 m long | hinged at the rear of the skull, lower jaw longer than the skull is deep, tip ~0.75–0.8 m below the upper teeth, '<' profile |
| Teeth | crooked plank teeth | long, tapered, faceted fangs, crowded and overlapping in staggered rows, dark central cavity |
| Surface | large knife facets, torn bark peels | dense mosaic of jagged rust flakes over chunky faceted forms; dark red tissue streaks along the limbs |
| Hardware | 5 bars, crown staple | back and shoulder spikes, torso-side rods, rods on both arms and a leg, short crown spikes |

## What was rebuilt (actual Blender objects)

| Object | Change |
|---|---|
| `Torso` | New leaning spine (~32°), broader boxy sections (exponent ~4, chest ~0.87 m), hunched upper back, belly, spine groove, arm sockets; shorter thick neck block fused in; new damage map (chest, both flanks, belly, upper back) |
| `Arm_R_Long` | Rebuilt slim (0.30–0.32 m vs 0.45–0.47 m) along a new path: shoulder, out to the elbow, forearm forward and out to a blunt end on the ground 1.5 m ahead; boxier sections; chiselled cap; elbow knob, inner notch, forearm ridge; red streaks along its length; two rods |
| `Arm_L_Short` | Slim (0.28 m), hangs forward from the shoulder to just above knee height; rods |
| `Leg_R`, `Leg_L` | Crouched: hips back, knees bent forward and splayed, feet back under the body; slimmer (0.30 m); new blocky feet with three toes each |
| `Cranium` | Same compact skull layout, boxier (flat-topped block), scaled to ~0.53 m wide; flake mosaic; three crown spikes replace the staple bracket |
| `Jaw` | Rebuilt: hinge moved to the rear of the skull; 0.61 m long (heavy, V-shaped chin, tapering to the rami); forced open 72° plus a 2 cm dislocation, so it hangs steeply from the hinge, the chin drops 0.71 m below the upper gum line and sits behind the snout (the sheet's '<' wedge) |
| `Teeth_Upper`, `Teeth_Lower` | Rebuilt as faceted fangs (5–7-sided, tapered, kinked, some snapped/chipped/stumped, a few rammed in crooked): 19 upper (0.09–0.40 m), 16 lower (0.11–0.35 m), front rows plus a sparse staggered second row and side teeth, with real gaps between them; lower fangs aimed up and slightly forward out of the steep jaw |
| `Gums_*`, `Mouth_Corner_Tissue`, `Mouth_Tendons`, `Tongue`, `Throat`, `Palate` | Refitted to the longer jaw: thicker swollen gums, larger torn cheek walls bridging the wedge, longer tendons and tongue, dark throat; darker wet crimson materials |
| `Bars` | New set: three back spikes, a shoulder spike, two torso-side rods, two long-arm rods, a short-arm rod, a leg rod, each in its own entry wound |
| Surface (all shell parts) | New pass in `sculpt.py`: after the knife facets the mesh is re-densified evenly and broken into a mosaic of jagged, slightly lifted and tilted rust flakes with cracks between them; peels follow the flake outlines; more and redder exposed tissue |
| Materials | `M_OJ_Rust` (per-flake tint, cracks, sunlit flake edges, dark-red dried-meat under-layers, wet crimson tissue), `M_OJ_Gum` / `M_OJ_Flesh` / `M_OJ_Tongue` / `M_OJ_Throat` (dark wet crimson) |

## Validation: measured against the sheet

Everything below is measured, not estimated, and can be re-run:

```bash
bvenv/bin/python -I scripts/measure_front_silhouette.py <out_dir> model/renders_openjaw/oj_front.png
```

```bash
bvenv/bin/python -I scripts/measure_teeth_coverage.py <out_dir> model/renders_openjaw/oj_front.png
```

```bash
bvenv/bin/python scripts/measure_jaw_profile.py model/out_there_monster_openjaw.blend
```

- **Front view (silhouettes).** The warm pixels of the sheet's front panel and of the model's
  orthographic front render are masked, cracks closed, holes filled, rods opened away; widths are
  medians over bands at the eyes (skull), below the mouth clear of the arms (torso) and across the
  long forearm (corrected for its slope). Overlays show where every width was taken.
- **Tooth coverage.** Inside the mouth opening (a polygon read off zoomed landmark grids: upper gum
  line, corners, lower gum arc), pale yellow pixels count as teeth and very dark ones as cavity.
- **Side profile.** Sheet: landmarks read on a 4x grid of its exact side view (crown, upper gum
  line, snout front, apex of the '<', lowest point and front of the lower jaw). Model: the same
  quantities computed from the geometry (world y/z of the built meshes).

| Quantity | Sheet | Model, first open-jaw build | Model, final |
|---|---|---|---|
| Skull width / torso width (front) | 0.70 | 0.72 | 0.72 |
| Long-forearm thickness / torso width (front) | 0.43 | 0.45 | 0.45 |
| Long-forearm thickness / skull width (front) | 0.61 | 0.63 | 0.63 |
| Mouth opening / skull height (front) | 2.1 | 2.13 | 2.0 |
| Teeth covering the mouth opening (front) | 26% | 49% | 24% |
| Very dark central cavity (front) | 54% | 33% | 56% |
| Lower-jaw length / upper-jaw length (side) | ~1.1 | 1.52 | 1.22 |
| Opening angle between the jaws (side) | ~70–72° | 57° | 72° |
| Chin drop / skull height (side) | ~2.0 | 2.55 | 2.28 |
| Front of the lower jaw behind the snout, in upper-jaw lengths (side) | ~0.6–0.7 | 0.06 | 0.53 |

The first build's numbers showed the proportions and the slim long arm were right but the jaw
profile and the teeth were not (fangs wider than their spacing, sealing half the opening; jaw too
long and too shallow, chin under the snout). Those were fixed and re-measured. With the steeper
jaw the tongue faced the camera and its wet sheen read as a grey sheet in the open mouth (found
with a colour-coded diagnostic render); tongue and throat are now near-black and matte.

In absolute terms (final model): skull 0.53 m wide, long arm 0.30–0.32 m thick and 2.66 m long
with its blunt end on the ground 1.5 m ahead, short arm 0.28 m, legs 0.30 m, overall height 2.86 m
(crouched), 1.42 M triangles.

## Remaining differences (honest)

See the comparison sheets in `model/renders_openjaw/_oj_vs_*.png`. Known gaps after this pass:

- The sheet is a painterly concept image whose views are not fully consistent with each other
  (e.g. the skull looks longer and taller in the side view than in the front view). The model
  follows the front view for widths and the side view for the pose and jaw; the skull was kept
  compact as the brief requires, so it reads flatter than the sheet's side view. That is also why
  the measured chin drop relative to skull height (2.28) is above the sheet's (~2.0), and the lower
  jaw is still ~10% long relative to the upper jaw (1.22 vs ~1.1); shortening it further would
  shrink the front-view opening below the sheet's.
- The sheet's flakes are larger raised "puzzle" plates with bright edges over a darker base; the
  model's flakes are smaller and flatter, closer to cracked plating.
- The sheet shows more saturated red tissue in long streaks; the model's wounds are placed the
  same way but read darker.
- The sheet's legs are straighter columns in the front view; the model's knees splay more.
- The sheet's fangs are fewer and thicker (conical tusks); the model's are thinner and more
  numerous, which gives the same measured coverage (24% vs 26%) but a finer, busier tooth row.
- The sheet's skull is chunkier and rockier in close-up; the model's skull reads smoother.
- The sheet's landmarks are read by eye on a zoomed grid (about ±5% on the side-profile ratios).
- Not Roblox-ready yet (1.42 M triangles; needs decimation, UVs and baking after approval).

---

# Approved sheet pass ("MORE OPEN JAW VERSION — SLIGHTLY LONGER TEETH ONLY")

Primary target: `references/r08_open_jaw_sheet_v2.webp`. The model before this pass is
checkpointed in `checkpoints/openjaw-v2/` (.blend, renders, scripts). Body proportions, pose,
head position and the jaw opening were kept; only the head, the teeth and the surface/materials
were changed. Comparison sheets: `model/renders_v3/_v3_vs_*.png`.

## What was changed (actual Blender objects)

| Object | Change |
|---|---|
| `Cranium` | Rebuilt as an angular wedge after the sheet: the top slopes down from the crown to a hard brow edge that overhangs deep square sockets; steep flat front face; cheek planes narrowing into the upper jaw (flat planar trims instead of a rounded loft). Fewer, larger surface plates and damage sections (upper-left fracture, torn mouth corner as a gash along the mouth line, right side, back, a brow chip); controlled asymmetry (a broken left brow corner, two dents) instead of noise. Not enlarged: 0.524 × 0.617 × 0.323 m vs 0.536 × 0.603 × 0.333 m before (a first version came out 4% wider across the eyes in the front-view measurement and was narrowed back), gum line unchanged; the extra 1.4 cm of depth is the brow's projection. The three existing crown spikes were moved to the sheet's knobs (no additions). |
| `Teeth_Upper`, `Teeth_Lower` | Rebuilt as thick, fluted tusks (ridge-and-groove sections, wide roots tapering to points) that curl into the mouth, in an explicit irregular layout instead of generated rows: long tusks, medium crooked ones, short snapped teeth and stumps, uneven spacing, widths and tilts (lower teeth now also lean sideways). 21 upper / 22 lower, all rooted on the existing gum lines; no inner row; jaw opening unchanged. |
| `Mouth_Corner_Tissue` | Adds inner tissue walls inside the side tooth rows, from the hinge to behind the front teeth, so the forced-open mouth reads as red flesh in profile instead of showing the background through it; the torn outer cheek membranes are kept. |
| Surface (all shell parts) | The rust-flake pass now makes larger, flatter plates (8.5 cm cells instead of 5.5 cm), damage stays inside its zones (no extra coverage), chips only on a few convex edges, half as many lifted plates; torn edges keep their jaggedness. |
| Materials | `M_OJ_Rust`: darker, saturated reddish-brown with thin orange crackle along the plate edges, localized oxidation and dark corrosion patches, low specular (the previous dark rust read pale grey under the studio lights), per-plate roughness variation, matte exposed layers; exposed layers and tissue are dark red and kept clear of crevice grime. `M_OJ_Teeth`: dirty yellowed bone with dark streaks along each tusk, root grime, decay and old blood. Gums and mouth tissue: wet, darker red. Rods: less metallic sheen. |

## Verification (measured)

```bash
bvenv/bin/python scripts/measure_teeth_reach.py model/out_there_monster_openjaw.blend
```

```bash
bvenv/bin/python scripts/measure_head_size.py model/out_there_monster_openjaw.blend
```

```bash
bvenv/bin/python scripts/measure_jaw_profile.py model/out_there_monster_openjaw.blend
```

| | Approved sheet | Before this pass | After |
|---|---|---|---|
| Upper teeth reach into the opening (front view), median / longest | ~0.45 / ~0.64 | 0.29 / 0.58 | 0.48 / 0.66 |
| Lower teeth reach, median / longest | ~0.44 / ~0.60 | 0.22 / 0.51 | 0.41 / 0.64 |
| Teeth (upper / lower) | — | 19 / 16 | 21 / 22 |
| Jaw opening angle / chin drop | (unchanged by request) | 72° / 0.714 m | 72° / 0.716 m |
| Skull width × depth × height above the gum line | (not enlarged) | 0.536 × 0.603 × 0.333 m | 0.524 × 0.617 × 0.323 m |
| Gum line position | (unchanged) | (0, −1.160, 2.480) | (0, −1.160, 2.480) |

Tooth reach is measured from the geometry: the vertical distance from the gum line to each tooth
tip (the part buried in the gum excluded), as a fraction of the mouth opening, as seen in the
front view. The sheet's values were read on a 6× grid of its front view. The pixel-colour tooth
coverage used in the previous pass undercounts the sheet's half-shaded teeth, so reach is used here.
