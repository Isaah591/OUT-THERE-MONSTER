"""Fit cameras and joints to the sheet's three body silhouettes (coarse blocks only, so one
evaluation takes a fraction of a second).  Writes experimental_01/analysis/pose_fit.json.

    bvenv/bin/python experimental_01/src/fit_pose.py [passes]
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
sh = S.load_sheet()
REF = {n: S.creature_mask(S.panel(n, sh), label_box=(0, 0, 260, 40)) for n in NAMES}
SIZE = {n: S.panel(n, sh).size for n in NAMES}


def polys_of(pose, hcfg):
    m = Model(8)
    body.build_body(m, pose)
    old = dict(head.HEAD)
    head.HEAD.update(hcfg)
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


def cams_of(cp):
    c = {}
    c["front"] = views.cam(0.0, 0.3, (cp["fx"], -0.55, cp["fz"]), views.BODY_DIST, cp["fw"], SIZE["front"])
    c["tq"] = views.cam(cp["taz"], 0.3, (cp["tx"], cp["ty"], cp["tz"]), views.BODY_DIST, cp["tw"], SIZE["tq"])
    c["side"] = views.cam(90.0, 0.3, (0.0, cp["sy"], cp["sz"]), views.BODY_DIST, cp["sw"], SIZE["side"])
    return c


def score(pose, hcfg, cp, detail=False):
    polys = polys_of(pose, hcfg)
    cams = cams_of(cp)
    tot, d = 0.0, {}
    for n in NAMES:
        s = sil(polys, cams[n], SIZE[n])
        r = REF[n]
        iou = (s & r).sum() / max((s | r).sum(), 1)
        d[n] = iou
        tot += iou
    return (tot / 3, d) if detail else tot / 3


def descend(get, setv, keys, steps, f, passes=2, lo=None, hi=None):
    best = f()
    for ps in range(passes):
        for k, st in zip(keys, steps):
            v0 = get(k)
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


if __name__ == "__main__":
    passes = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    pose = copy.deepcopy(body.POSE)
    hcfg = dict(origin=head.HEAD["origin"].copy(), scale=1.0, pitch=head.HEAD["pitch"])
    cp = dict(fx=-0.19, fz=1.37, fw=3.05, taz=31.0, tx=-0.33, ty=-0.55, tz=1.49, tw=3.40, sy=-0.84, sz=1.50, sw=3.10)
    pf = os.path.join(OUT, "pose_fit.json")
    if os.path.exists(pf) and "--fresh" not in sys.argv:
        j = json.load(open(pf))
        pose.update(j["pose"]); cp.update(j["cams"])
        hcfg.update(origin=np.array(j["head"]["origin"]), scale=j["head"]["scale"], pitch=j["head"]["pitch"])
    f = lambda: score(pose, hcfg, cp)
    t = time.time()
    print("start", score(pose, hcfg, cp, True))
    # 1) cameras
    ck = list(cp)
    descend(lambda k: cp[k], lambda k, v: cp.__setitem__(k, v), ck, [0.02 if k != "taz" else 1.0 for k in ck], f, passes=2)
    print("cameras", {k: round(v, 3) for k, v in cp.items()}, score(pose, hcfg, cp, True))
    # 2) joints and sizes
    keys, steps, base = [], [], {}
    def add(path, st):
        keys.append(path); steps.append(st)
    for name in ("arm_long", "arm_short"):
        for i in range(len(pose[name])):
            for a in range(3):
                add((name, i, a), 0.025)
    for name in ("hip", "hipR", "kneeR", "ankR", "hipL", "kneeL", "ankL", "neck_end"):
        for a in range(3):
            add((name, a), 0.025)
    for name, st in (("lean", 1.5), ("torso_len", 0.03), ("torso_w", 0.03), ("torso_d", 0.03), ("arm_long_w", 0.04), ("arm_long_d", 0.04),
                     ("arm_short_w", 0.04), ("arm_short_d", 0.04), ("leg_w", 0.04), ("leg_d", 0.04), ("footR", 0.03), ("footL", 0.03)):
        add((name,), st)
    for a in range(3):
        add(("HEAD", a), 0.025)
    add(("HSCALE",), 0.025)
    add(("HPITCH",), 0.02)

    def get(path):
        if path[0] == "HEAD":
            return float(hcfg["origin"][path[1]])
        if path[0] == "HSCALE":
            return hcfg["scale"]
        if path[0] == "HPITCH":
            return hcfg["pitch"]
        v = pose[path[0]]
        for q in path[1:]:
            v = v[q]
        return float(v)

    def setv(path, val):
        if path[0] == "HEAD":
            hcfg["origin"][path[1]] = val; return
        if path[0] == "HSCALE":
            hcfg["scale"] = val; return
        if path[0] == "HPITCH":
            hcfg["pitch"] = val; return
        if len(path) == 1:
            pose[path[0]] = val; return
        v = pose[path[0]]
        for q in path[1:-1]:
            v = v[q]
        v[path[-1]] = val

    start = {k: get(k) for k in keys}
    span = {k: (0.22 if st == 0.025 else st * 6) for k, st in zip(keys, steps)}
    lo = {k: start[k] - span[k] for k in keys}
    hi = {k: start[k] + span[k] for k in keys}
    descend(get, setv, keys, steps, f, passes=passes, lo=lo, hi=hi)
    descend(lambda k: cp[k], lambda k, v: cp.__setitem__(k, v), ck, [0.01 if k != "taz" else 0.5 for k in ck], f, passes=1)
    final = score(pose, hcfg, cp, True)
    print("final", final, f"{time.time() - t:.0f} s")
    json.dump(dict(pose=pose, cams=cp, head=dict(origin=[float(x) for x in hcfg["origin"]], scale=hcfg["scale"], pitch=hcfg["pitch"]),
                   iou=final[1]), open(pf, "w"), indent=1)
    print("wrote", pf)
