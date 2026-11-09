"""
V11 teeth and mouth-interior checks.

- Teeth passing through each other: every tooth in Teeth_Upper / Teeth_Lower is its own closed shell.
  Pairs of teeth whose triangles intersect are counted as visible (both triangles more than
  EXIT_M from the tooth's base, i.e. above the gum) or hidden (only the root ends meet, inside the gum).
- With renders: brightness of the gaps between the teeth inside the mouth (pixels that are neither
  teeth nor brighter than 0.35), against the same boxes on the sheet's front and three-quarter panels.

    python v11_teeth_check.py <file.blend> [front=<sheet_front.png> 34=<fit34.png>]     (with `bpy`)
"""
import os
import sys

import bpy  # noqa: I001  (first: it provides bmesh and mathutils)
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from PIL import Image

REFS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")
PANELS = {"front": (0, 55, 490, 550), "34": (500, 55, 1008, 550)}
GAP_BOX = {"front": (245, 80, 292, 140), "34": (180, 120, 230, 185)}      # inside the mouth, panel px
EXIT_M = 0.054                       # base of a tooth -> gum surface (the base is set 3 cm into the gum)


def teeth_shells(name):
    """Each tooth of an object as (BVH tree, per-face distance of its lowest vertex from the base)."""
    ob = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    lay = bm.verts.layers.float_color.get("tooth")         # (t root -> tip, ...) per vertex
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    seen, out = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            g = stack.pop()
            comp.append(g)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen:
                        seen.add(h.index)
                        stack.append(h)
        vs = sorted({v.index for g in comp for v in g.verts})
        base = [bm.verts[v].co for v in vs if bm.verts[v][lay][0] < 1e-4]
        c0 = sum(base, Vector()) / len(base)
        tip = max((bm.verts[v] for v in vs), key=lambda v: v[lay][0]).co
        L = (tip - c0).length
        idx = {v: i for i, v in enumerate(vs)}
        tree = BVHTree.FromPolygons([bm.verts[v].co.copy() for v in vs], [[idx[v.index] for v in g.verts] for g in comp])
        out.append((tree, [min(v[lay][0] for v in g.verts) * L for g in comp]))
    bm.free()
    return out


def intersections(A, B, same):
    visible, hidden = [], 0
    for i in range(len(A)):
        for j in range(len(B)):
            if same and j <= i:
                continue
            pairs = A[i][0].overlap(B[j][0])
            if not pairs:
                continue
            above = [(a, b) for a, b in pairs if A[i][1][a] > EXIT_M and B[j][1][b] > EXIT_M]
            if above:
                visible.append((i, j))
            else:
                hidden += 1
    return visible, hidden


def gap_brightness(img, box):
    x0, y0, x1, y1 = box
    a = img[y0:y1, x0:x1].reshape(-1, 3)
    v = a.max(1) / 255.0
    teeth = (v > 0.45) & (a[:, 0] > a[:, 2] * 1.3)
    g = v[~teeth & (v < 0.35)]
    return np.median(g), np.percentile(g, 25), np.percentile(g, 75)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    bpy.ops.wm.open_mainfile(filepath=argv[0])
    U, L = teeth_shells("Teeth_Upper"), teeth_shells("Teeth_Lower")
    for name, (vis, hid) in (("upper", intersections(U, U, True)), ("lower", intersections(L, L, True)),
                             ("upper vs lower", intersections(U, L, False))):
        print("teeth passing through each other, %s: visible %d pairs %s | root ends meeting in the gum: %d"
              % (name, len(vis), vis, hid))
    sheet = Image.open(os.path.join(REFS, "r08_open_jaw_sheet_v2.webp")).convert("RGB")
    for arg in argv[1:]:
        view, path = arg.split("=")
        b = PANELS[view]
        s = np.asarray(sheet.crop(b)).astype(float)
        r = np.asarray(Image.open(path).convert("RGB").resize((b[2] - b[0], b[3] - b[1]), Image.LANCZOS)).astype(float)
        print("%-5s gaps between the teeth, median brightness (p25-p75): sheet %.3f (%.3f-%.3f) | model %.3f (%.3f-%.3f)"
              % ((view,) + gap_brightness(s, GAP_BOX[view]) + gap_brightness(r, GAP_BOX[view])))
