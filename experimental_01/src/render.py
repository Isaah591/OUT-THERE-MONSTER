"""Render named views of the saved model with one studio rig.

    bvenv/bin/python experimental_01/src/render.py model.blend outdir view [view ...]
    env: SAMPLES (default 64), RES (pixels of the long side, default 1000)
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import scene as SC
import views

if __name__ == "__main__":
    blend, outdir = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or list(views.VIEWS)
    samples = int(os.environ.get("SAMPLES", "64"))
    res = int(os.environ.get("RES", "1000"))
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    SC.setup_cycles(sc, samples=samples)
    os.makedirs(outdir, exist_ok=True)
    for n in names:
        v = views.VIEWS[n]
        w, h = v.get("size", (640, 680))
        k = res / max(w, h)
        SC.aim_studio(v.get("az", 0.0))
        cam = SC.camera(sc, "Cam_" + n, tuple(v["pos"]), tuple(v["target"]), lens=v["lens"], roll=v.get("roll", 0.0))
        t = time.time()
        SC.render(sc, cam, os.path.join(outdir, n + ".png"), res=(int(round(w * k)), int(round(h * k))))
        print(f"rendered {n} in {time.time() - t:.1f} s")
