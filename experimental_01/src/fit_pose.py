"""Fit cameras (and optionally joints) to the sheet's three body silhouettes, using the coarse
blocks only so one evaluation takes a fraction of a second.

    bvenv/bin/python experimental_01/src/fit_pose.py --cams [--dist 22]     -> analysis/cameras.json
    bvenv/bin/python experimental_01/src/fit_pose.py --joints [passes]      -> analysis/pose_fit.json

The joint fit starts from body.POSE and only suggests values; they are copied into body.py by
hand after a sanity check (the sheet's panels do not agree with one another exactly).
"""
import os, sys, json, time, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import sheet as S, views, preview as PV, kernel as K
from model import Model
import body, head

OUT = os.path.join(S.ROOT, "experimental_01", "analysis")
NAMES = ("front", "tq", "side")
WEIGHT = dict(front=1.0, tq=1.0, side=1.3)
sh = S.load_sheet()
REF = {n: S.creature_mask(S.panel(n, sh), label_box=(0, 0, 260, 40)) for n in NAMES}
SIZE = {n: S.panel(n, sh).size for n in NAMES}


def polys_of(pose, hcfg=None):
    m = Model(8)
    old = dict(head.HEAD)
    if hcfg:
        head.HEAD.update(hcfg)
    body.build_body(m, pose)
    head.build_head(m)
    head.HEAD.clear(); head.HEAD.update(old)
    P = []
    for p in m.parts:
        V = p["coarse"].arrays()
        P += [V[f] for f in p["coarse"].F]
    for name, (mo, mat, sm) in m.loose.items():
        d = mo.finish()
        P += [d["V"][q] for q in d["Q"]] + [d["V"][t] for t in d["T"]]
    return P


def sil(polys, cam, size):
    W, H = size
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    allp = np.concatenate(polys)
    xy, z = PV.project(allp, cam, (W, H))
    o = 0
    for p in polys:
        k = len(p)
        dr.polygon([tuple(q) for q in xy[o:o + k]], fill=255)
        o += k
    return np.asarray(img) > 0


def score_polys(polys, cp, detail=False):
    cams = views.body_views(cp)
    tot, d, wt = 0.0, {}, 0.0
    for n in NAMES:
        s = sil(polys, cams[n], SIZE[n])
        r = REF[n]
        iou = (s & r).sum() / max((s | r).sum(), 1)
        d[n] = round(float(iou), 4)
        tot += iou * WEIGHT[n]
        wt += WEIGHT[n]
    return (tot / wt, d) if detail else tot / wt


def descend(get, setv, keys, steps, f, passes=2, lo=None, hi=None):
    best = f()
    for ps in range(passes):
        for k, st in zip(keys, steps):
            improved = True
            while improved:
                improved = False
                for sgn in (1, -1):
                    v = get(k) + sgn * st
                    if lo is not None and not (lo[k] <= v <= hi[k]):
                        continue
                    old = get(k)
                    setv(k, v)
                    sc = f()
                    if sc > best + 1e-5:
                        best = sc
                        improved = True
                        break
                    setv(k, old)
        print(f"   pass {ps + 1}: {best:.4f}", flush=True)
    return best


def fit_cams(pose, cp):
    polys = polys_of(pose)
    f = lambda: score_polys(polys, cp)
    ck = [k for k in cp if k != "dist"]
    for st in (0.04, 0.01):
        descend(lambda k: cp[k], lambda k, v: cp.__setitem__(k, v), ck, [st if k != "taz" else st * 40 for k in ck], f, passes=2)
    return score_polys(polys, cp, True)


if __name__ == "__main__":
    pose = copy.deepcopy(body.POSE)
    cp = dict(views.CAMS)
    if "--dist" in sys.argv:
        cp["dist"] = float(sys.argv[sys.argv.index("--dist") + 1])
    t = time.time()
    if "--cams" in sys.argv:
        print("start", score_polys(polys_of(pose), cp, True))
        res = fit_cams(pose, cp)
        cp = {k: round(float(v), 4) for k, v in cp.items()}
        json.dump(cp, open(os.path.join(OUT, "cameras.json"), "w"), indent=1)
        print("cameras", cp, res, f"{time.time() - t:.0f} s")
    if "--joints" in sys.argv:
        i = sys.argv.index("--joints")
        passes = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 2
        hcfg = dict(origin=head.HEAD["origin"].copy(), scale=head.HEAD["scale"], pitch=head.HEAD["pitch"])
        f = lambda: score_polys(polys_of(pose, hcfg), cp)
        print("start", score_polys(polys_of(pose, hcfg), cp, True))
        keys, steps = [], []
        def add(path, st):
            keys.append(path); steps.append(st)
        for name in ("arm_long", "arm_short"):
            for i in range(len(pose[name])):
                for a in range(3):
                    add((name, i, a), 0.02)
        for name in ("hip", "hipR", "kneeR", "ankR", "hipL", "kneeL", "ankL"):
            for a in range(3):
                add((name, a), 0.02)
        for name, st in (("lean", 1.0), ("torso_len", 0.02), ("torso_w", 0.02), ("torso_d", 0.02), ("arm_long_w", 0.03), ("arm_long_d", 0.03),
                         ("arm_short_w", 0.03), ("arm_short_d", 0.03), ("leg_w", 0.03), ("leg_d", 0.03), ("footR", 0.02), ("footL", 0.02)):
            add((name,), st)

        def get(path):
            v = pose[path[0]]
            for q in path[1:]:
                v = v[q]
            return float(v)

        def setv(path, val):
            if len(path) == 1:
                pose[path[0]] = val; return
            v = pose[path[0]]
            for q in path[1:-1]:
                v = v[q]
            v[path[-1]] = val

        start = {k: get(k) for k in keys}
        span = {k: (0.10 if st == 0.02 else st * 4) for k, st in zip(keys, steps)}
        lo = {k: start[k] - span[k] for k in keys}
        hi = {k: start[k] + span[k] for k in keys}
        descend(get, setv, keys, steps, f, passes=passes, lo=lo, hi=hi)
        final = score_polys(polys_of(pose, hcfg), cp, True)
        print("final", final, f"{time.time() - t:.0f} s")
        json.dump(dict(pose=pose, iou=final[1]), open(os.path.join(OUT, "pose_fit.json"), "w"), indent=1)
        for k, v in pose.items():
            if v != body.POSE[k]:
                print("   ", k, "=", json.dumps(v))
