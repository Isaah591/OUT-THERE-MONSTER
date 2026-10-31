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
| `Jaw` | Rebuilt: hinge moved to the rear of the skull; 0.81 m long (heavy, V-shaped chin, tapering to the rami); opened 57° plus a 2 cm dislocation, so the chin drops 0.78 m below the upper gum line and sits below the front of the skull (the '<' wedge) |
| `Teeth_Upper`, `Teeth_Lower` | Rebuilt as faceted fangs (5–7-sided, tapered, kinked, some snapped/chipped/stumped, a few rammed in crooked): 26 upper (0.10–0.42 m), 23 lower (0.08–0.36 m), front rows plus staggered second rows and side teeth; lower fangs re-aimed up into the opening |
| `Gums_*`, `Mouth_Corner_Tissue`, `Mouth_Tendons`, `Tongue`, `Throat`, `Palate` | Refitted to the longer jaw: thicker swollen gums, larger torn cheek walls bridging the wedge, longer tendons and tongue, dark throat; darker wet crimson materials |
| `Bars` | New set: three back spikes, a shoulder spike, two torso-side rods, two long-arm rods, a short-arm rod, a leg rod, each in its own entry wound |
| Surface (all shell parts) | New pass in `sculpt.py`: after the knife facets the mesh is re-densified evenly and broken into a mosaic of jagged, slightly lifted and tilted rust flakes with cracks between them; peels follow the flake outlines; more and redder exposed tissue |
| Materials | `M_OJ_Rust` (per-flake tint, cracks, sunlit flake edges, dark-red dried-meat under-layers, wet crimson tissue), `M_OJ_Gum` / `M_OJ_Flesh` / `M_OJ_Tongue` / `M_OJ_Throat` (dark wet crimson) |

## Measured on the final model

| | Model | Sheet |
|---|---|---|
| Skull width / torso width (chest) | 0.53 / 0.87 m = 0.61 by mesh extents | ~0.70 (front panel, visible widths) |
| Long arm thickness | 0.30–0.32 m (median), length 2.66 m, hand 1.5 m ahead and out | slim, very long, planted ahead |
| Short arm / leg thickness | 0.28 / 0.30 m | slim |
| Jaw drop below the upper gum line | 0.78 m | ~0.75–0.8 m |
| Front opening (upper gum to lower gum) | 0.66 m; longest fangs reach ~55% of it from above and ~43% from below, interleaving at the front with the dark cavity behind them | crowded fangs, dark cavity |
| Overall height (crouched) | 2.86 m | — |

## Remaining differences (honest)

See the comparison sheets in `model/renders_openjaw/_oj_vs_*.png`. Known gaps after this pass:

- The sheet is a painterly concept image whose views are not fully consistent with each other
  (e.g. the skull looks longer in the side view than in the front view). The model follows the
  front view for widths and the side view for the pose and jaw; the skull was kept compact as
  the brief requires, so it reads shorter than the sheet's side view.
- The sheet's flakes are larger raised "puzzle" plates with bright edges over a darker base; the
  model's flakes are smaller and flatter, closer to cracked plating.
- The sheet shows more saturated red tissue in long streaks; the model's wounds are placed the
  same way but read darker.
- The sheet's legs are straighter columns in the front view; the model's knees splay more.
- Not Roblox-ready yet (1.44 M triangles; needs decimation, UVs and baking after approval).
