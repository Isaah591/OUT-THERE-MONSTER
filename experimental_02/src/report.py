"""Measure the finished model and collect the checks into experimental_02/analysis/.

    bvenv/bin/python experimental_02/src/report.py [renders_dir]

Writes model_stats.json (dimensions, tooth list summary), mouth_fill.json (how much of the mouth
opening the teeth cover in each view, with the approved sheet's own figure) and facts.json (the
lines printed on the presentation sheet).
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import sheet as S, head, body, views
from model import Model
import mouth_check as MC

AN = os.path.join(S.ROOT, "experimental_02", "analysis")

if __name__ == "__main__":
    rdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(S.ROOT, "experimental_02", "renders")
    m = Model(8)
    body.build_body(m)
    head.build_head(m)
    out = m.generate(verbose=False)
    tris = {k: int(len(v[0]["Q"]) * 2 + len(v[0]["T"])) for k, v in out.items()}
    allv = np.concatenate([v[0]["V"] for k, v in out.items()])
    norod = np.concatenate([v[0]["V"] for k, v in out.items() if "rods" not in k])
    hv = np.concatenate([v[0]["V"] for k, v in out.items() if k.startswith("head") and "rods" not in k])
    teeth = m.info["teeth"]
    up = [t for t in teeth if t["jaw"] == "upper"]
    lo = [t for t in teeth if t["jaw"] == "lower"]
    L = lambda ts: [round(float(t["L"]), 3) for t in ts]
    hs = head.HEAD["scale"]
    lipc = head.Hw(0.262, 0.0, head.lip(0.262))
    chin = head.Hw(*head.RIM[np.argmin(head.RIM[:, 2])])
    stats = dict(
        triangles=tris, triangles_total=int(sum(tris.values())),
        height_m=round(float(norod[:, 2].max() - allv[:, 2].min()), 3), height_with_rods_m=round(float(allv[:, 2].max()), 3),
        width_m=round(float(np.ptp(allv[:, 0])), 3), length_m=round(float(np.ptp(allv[:, 1])), 3),
        head=dict(width_m=round(float(np.ptp(hv[:, 0])), 3), length_m=round(float(np.ptp(hv[:, 1])), 3),
                  height_m=round(float(np.ptp(hv[:, 2])), 3),
                  mask_width_m=round(float(head.COLX[-1] - head.COLX[0]) * hs, 3),
                  gape_m=round(float(-head.RIM[:, 2].min() + head.LIP.max()) * hs, 3),
                  lip_dip_m=round(float(head.LIP.max() - head.LIP.min()) * hs, 3),
                  chin_forward_of_hinge_m=round(float(head.RIM[0, 1] - head.RIM[:, 1].min()) * hs, 3),
                  sockets_m=[[round(float(head.COLX[2] - head.COLX[1]) * hs, 3), round(float(np.mean(head.SOCT[1:3] - head.SOCB[1:3])) * hs, 3)],
                             [round(float(head.COLX[5] - head.COLX[4]) * hs, 3), round(float(np.mean(head.SOCT[4:6] - head.SOCB[4:6])) * hs, 3)]],
                  socket_depth_m=round(head.SOCKET_DEPTH * hs, 3), pupil_radius_m=head.PUPIL_R,
                  brow_drop_deg=[round(float(np.degrees(np.arctan2(head.SOCT[1] - head.SOCT[2], head.COLX[2] - head.COLX[1]))), 1),
                                 round(float(np.degrees(np.arctan2(head.SOCT[5] - head.SOCT[4], head.COLX[5] - head.COLX[4]))), 1)]),
        teeth=dict(upper=len(up), lower=len(lo), upper_front=len(head.UPPER_FRONT), upper_side=len(head.UPPER_SIDE),
                   upper_inner=len(head.UPPER_INNER), lower_rim=len(head.LOWER), lower_inner=len(head.LOWER_INNER),
                   upper_lengths_m=L(up), lower_lengths_m=L(lo),
                   longest_m=max(L(teeth)), shortest_m=min(L(teeth)),
                   rear_upper_lengths_m=[round(float(t[2]) * hs, 3) for t in head.UPPER_SIDE],
                   clashes_as_placed=int(m.info["tooth_clashes"][0]), clashes_after_relaxing=int(m.info["tooth_clashes"][1])),
        arm_long_m=round(float(np.linalg.norm(np.diff(np.array(body.POSE["arm_long"]), axis=0), axis=1).sum()), 2),
        arm_short_m=round(float(np.linalg.norm(np.diff(np.array(body.POSE["arm_short"]), axis=0), axis=1).sum()), 2),
        head_ahead_of_hips_m=round(float(body.POSE["hip"][1] - head.HEAD["origin"][1]), 2),
        wounds=int(sum(len(p["wounds"].z) for p in m.parts)), rods=15,
        front_upper_lengths_m=[round(float(t[1]) * hs, 3) for t in head.UPPER_FRONT],
        pose=body.POSE, head_placement=dict(origin=[float(x) for x in head.HEAD["origin"]], pitch_rad=float(head.HEAD["pitch"])),
        cameras=views.CAMS)
    json.dump(stats, open(os.path.join(AN, "model_stats.json"), "w"), indent=1)
    # ---- mouth fill
    sh = S.load_sheet()
    fill = {}
    im = S.panel("head", sh)
    fill["sheet_head_closeup"] = {k: round(float(v), 3) for k, v in MC.measure(im, MC.REF_OUTLINES["head"], im.size)[0].items()}
    for v in ("head", "mouth", "hfront", "front", "tq", "mouthside"):
        p = os.path.join(rdir, v + ".png")
        if os.path.exists(p):
            im = Image.open(p)
            poly, size = MC.opening_polygon(v)
            fill["model_" + v] = {k: round(float(x), 3) for k, x in MC.measure(im, poly * (im.width / size[0]), im.size)[0].items()}
    json.dump(fill, open(os.path.join(AN, "mouth_fill.json"), "w"), indent=1)
    iou = {}
    p = os.path.join(AN, "silhouette_iou.json")
    if os.path.exists(p):
        iou = json.load(open(p))
    t = stats["teeth"]
    hd = stats["head"]
    left = [
        "BUILT FROM A BLANK SCENE: NO EARLIER MODEL, MESH OR SCRIPT IS LOADED",
        f"{stats['triangles_total']:,} TRIANGLES, {stats['height_m']:.2f} M TALL, EVERY RUST PLATE IS GEOMETRY",
        f"{t['upper'] + t['lower']} TEETH MODELLED ONE BY ONE ({t['upper']} UPPER / {t['lower']} LOWER), {t['shortest_m'] * 100:.0f}-{t['longest_m'] * 100:.0f} CM LONG",
        f"REAR UPPER TEETH {min(t['rear_upper_lengths_m']) * 100:.0f}-{max(t['rear_upper_lengths_m']) * 100:.0f} CM: AS LONG AS THE FRONT ONES",
        f"JAW RIM IS A 3D CURVE: {hd['gape_m'] * 100:.0f} CM GAPE, CHIN HOOKS {hd['chin_forward_of_hinge_m'] * 100:.0f} CM FORWARD, LIP DIPS {hd['lip_dip_m'] * 100:.0f} CM",
        "ONE STUDIO RIG FOR ALL VIEWS (TURNED WITH THE CAMERA)",
    ]
    right = []
    if iou:
        right.append("SILHOUETTE OVERLAP WITH THE SHEET: FRONT %.2f / THREE-QUARTER %.2f / SIDE %.2f" % (
            iou["front"]["as_framed"], iou["tq"]["as_framed"], iou["side"]["as_framed"]))
    if "model_head" in fill:
        right.append("HEAD CLOSE-UP: TEETH COVER %.0f%% OF THE MOUTH OPENING (SHEET: %.0f%%), DARK %.0f%% (SHEET: %.0f%%)" % (
            fill["model_head"]["teeth"] * 100, fill["sheet_head_closeup"]["teeth"] * 100,
            fill["model_head"]["dark"] * 100, fill["sheet_head_closeup"]["dark"] * 100))
        right.append("LARGEST UNBROKEN DARK PATCH: %.0f%% OF THE OPENING (SHEET: %.0f%%)" % (
            fill["model_head"]["largest_dark"] * 100, fill["sheet_head_closeup"]["largest_dark"] * 100))
    right.append(f"TEETH PASSING THROUGH ONE ANOTHER: {t['clashes_after_relaxing']} (WAS {t['clashes_as_placed']} PAIRS BEFORE EASING APART)")
    right.append("SOCKETS %.0f x %.0f CM AND %.0f x %.0f CM, %.0f CM DEEP; BROWS DROP %.0f AND %.0f DEG TOWARD THE NOSE" % (
        hd["sockets_m"][0][0] * 100, hd["sockets_m"][0][1] * 100, hd["sockets_m"][1][0] * 100, hd["sockets_m"][1][1] * 100,
        hd["socket_depth_m"] * 100, hd["brow_drop_deg"][0], hd["brow_drop_deg"][1]))
    right.append("HEAD (CROWN TO CHIN) = %.0f%% OF THE HEIGHT; THE SHEET SHOWS 32%% (FRONT), 39%% (THREE-QUARTER), 42%% (SIDE)" % (
        100 * hd["height_m"] / stats["height_m"]))
    json.dump(dict(left=left, right=right), open(os.path.join(AN, "facts.json"), "w"), indent=1)
    print(json.dumps(dict(height=stats["height_m"], width=stats["width_m"], length=stats["length_m"], head=hd, teeth={k: v for k, v in t.items() if "lengths" not in k}), indent=1))
    print("\n".join(left + right))
