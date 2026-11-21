# Bringing ASTRA R08 into Roblox Studio

The complete, self-contained handoff is **`experimental_02/handoff/ASTRA_R08_Roblox/`** (also as
`experimental_02/handoff/ASTRA_R08_Roblox.zip`).  Its `README.md` has the exact Studio steps (import
settings, animation import, priorities, jaw control, a test script, troubleshooting); this page only
summarises them.

- Character: `ASTRA_R08.fbx` - Import 3D with Rig Type **Custom**, Scale Unit **Stud**, World Forward
  **Front** / Up **Top**, **Keep Zero Influence Bones on**, Merge Meshes off.  About 10.3 studs tall,
  facing -Z, feet on the ground.
- Clips: `animations/ASTRA_R08_<Clip>.fbx`, one per file (Idle, Walk, Run, Chase, Attack, Lunge,
  HitReact, Death, JawSnap, JawChatter, HeadTrack) - Animation Editor > ... > Import > From FBX
  Animation, then set Looping / Priority and publish.
- Jaw: its own bone; JawSnap / JawChatter key only it; the controller script can also open it on top
  of any clip.
- Not yet opened in Roblox Studio (it does not run where this was built); everything that can be
  checked outside Studio is in `FBX_VERIFICATION.md`.
