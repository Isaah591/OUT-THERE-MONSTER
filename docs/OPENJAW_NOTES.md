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
| Teeth covering the mouth opening (front) | 26% | 49% | 25% |
| Very dark central cavity (front) | 54% | 33% | 50% |
| Lower-jaw length / upper-jaw length (side) | ~1.1 | 1.52 | 1.22 |
| Opening angle between the jaws (side) | ~70–72° | 57° | 72° |
| Chin drop / skull height (side) | ~2.0 | 2.55 | 2.28 |
| Front of the lower jaw behind the snout, in upper-jaw lengths (side) | ~0.6–0.7 | 0.06 | 0.53 |

The first build's numbers showed the proportions and the slim long arm were right but the jaw
profile and the teeth were not (fangs wider than their spacing, sealing half the opening; jaw too
long and too shallow, chin under the snout). Those were fixed and re-measured.

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
- The sheet's landmarks are read by eye on a zoomed grid (about ±5% on the side-profile ratios).
- Not Roblox-ready yet (1.42 M triangles; needs decimation, UVs and baking after approval).
