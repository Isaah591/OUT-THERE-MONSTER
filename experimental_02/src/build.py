"""Build ASTRA R08 - Experimental Model 02 from a blank scene.

    bvenv/bin/python experimental_02/src/build.py [out.blend] [--only head|body]

Nothing is loaded from earlier models: the scene starts empty and every vertex comes from
body.py / head.py (which hold the sheet readings) through kernel.py.
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import bpy
import kernel as K
import scene as SC
from model import Model
import body, head

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "model", "astra_r08_exp02_highdetail.blend")


def build(only=None, seed=8):
    m = Model(seed)
    body.build_body(m)
    head.build_head(m)
    return m, m.generate(only=only)


def to_blender(m, out):
    sc = SC.new_scene()
    mats = dict(rust=SC.mat_rust(), under=SC.mat_under(), muscle=SC.mat_muscle(), gum=SC.mat_gum(),
                mouth=SC.mat_mouth(), tooth=SC.mat_tooth(), rod=SC.mat_rod(), pupil=SC.mat_pupil())
    stats = {}
    for name, (data, mat, smooth) in out.items():
        ob = SC.add_mesh("R08_" + name, data, mats[mat], smooth=smooth)
        stats[name] = len(data["Q"]) * 2 + len(data["T"])
    # a faint red glow inside each socket
    for i, p in enumerate(m.info.get("pupils", [])):
        L = bpy.data.lights.new(f"PupilGlow{i}", "POINT")
        L.energy = 0.012
        L.color = (1.0, 0.07, 0.02)
        L.shadow_soft_size = 0.008
        o = bpy.data.objects.new(f"R08_pupil_glow{i}", L)
        o.location = p + np.array([0.0, -0.012, 0.0])
        SC.collection("ASTRA_R08").objects.link(o)
    SC.studio(sc)
    SC.setup_cycles(sc)
    return sc, stats


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = None
    if "--only" in sys.argv:
        only = [sys.argv[sys.argv.index("--only") + 1]]
    path = args[0] if args else DEFAULT
    t = time.time()
    m, out = build(only)
    print(f"geometry generated in {time.time() - t:.1f} s")
    sc, stats = to_blender(m, out)
    tot = sum(stats.values())
    for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
        print(f"   {k:<16} {v:>8} triangles")
    print(f"   total            {tot:>8} triangles;  teeth upper/lower: {m.info.get('n_teeth')}")
    c = m.info.get("tooth_clashes")
    if c:
        print(f"   teeth passing through one another: {c[0]} pairs as placed -> {c[1]} after relaxing (deepest {c[2] * 1000:.1f} mm)")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("saved", path, f"({os.path.getsize(path) / 1e6:.1f} MB) in {time.time() - t:.1f} s")
