"""The cameras used for every picture of Experimental Model 01 (one rig, shared by the preview,
the silhouette checks and the Cycles renders).  Each view frames what the matching panel of the
approved sheet frames, so pictures can be compared side by side."""
import numpy as np

SENSOR = 36.0


def cam(az_deg, elev_deg, target, dist, width, size, roll=0.0):
    """az = 0: front (camera on -Y); 90: exact side from the creature's left (+X).
    width = metres of scene across the picture at the target."""
    a, e = np.radians(az_deg), np.radians(elev_deg)
    t = np.asarray(target, float)
    pos = t + dist * np.array([np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e)])
    lens = SENSOR * dist / width
    w, h = size
    fov_v = 2 * np.arctan((width * h / w) / 2 / dist)
    return dict(pos=pos, target=t, lens=lens, fov=float(np.degrees(fov_v)), size=size, roll=roll, az=az_deg, elev=elev_deg,
                dist=dist, width=width)


import json, os
_CJ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "analysis", "cameras.json")
# body cameras: long lens (the sheet's body panels show very little perspective); framing fitted
# to each panel's silhouette by fit_pose.py --cams
CAMS = dict(dist=22.0, fx=-0.21, fz=1.39, fw=3.02, taz=26.5, tx=-0.09, ty=-0.55, tz=1.49, tw=3.31, sy=-0.86, sz=1.50, sw=3.00)
if os.path.exists(_CJ):
    CAMS.update(json.load(open(_CJ)))
BODY_DIST = CAMS["dist"]


def _h(x, b, h):
    import head
    return head.Hw(x, b, h)


def body_views(c=None):
    c = c or CAMS
    return {
        "front": cam(0.0, 0.3, (c["fx"], -0.55, c["fz"]), c["dist"], c["fw"], (490, 496)),
        "tq": cam(c["taz"], 0.3, (c["tx"], c["ty"], c["tz"]), c["dist"], c["tw"], (510, 496)),
        "side": cam(90.0, 0.3, (0.0, c["sy"], c["sz"]), c["dist"], c["sw"], (468, 496)),
    }


VIEWS = {
    # full figure - the sheet's three body panels
    **body_views(),
    # head and mouth - the sheet's close-up panels
    "head": cam(27.0, -3.0, _h(0.085, 0.036, -0.180), 4.6, 1.38, (438, 352)),
    "mouth": cam(27.0, -9.0, _h(0.030, 0.200, -0.330), 3.6, 0.74, (310, 313)),
    "jawside": cam(58.0, -2.0, _h(0.0, 0.230, -0.300), 3.8, 0.78, (231, 263)),
    "sideclose": cam(68.0, 0.0, _h(0.0, 0.360, -0.130), 4.4, 1.00, (286, 317)),
    # exact profile of the mouth (asked for in the brief)
    "mouthside": cam(90.0, 0.0, _h(0.0, 0.290, -0.190), 4.4, 1.12, (340, 340)),
    # working views of the head
    "hfront": cam(0.0, 0.0, _h(0.0, 0.2, -0.13), 7.0, 1.20, (400, 440)),
    "hside": cam(90.0, 0.0, _h(0.0, 0.36, -0.13), 7.0, 1.30, (440, 440)),
}

# which sheet panel each view answers
PANEL_OF = {"front": "front", "tq": "tq", "side": "side", "head": "head", "mouth": "mouth",
            "jawside": "jaw_new", "sideclose": "sideclose"}

# a working view of the feet
VIEWS["feet"] = cam(20.0, 12.0, (0.0, -0.20, 0.22), 6.0, 1.9, (560, 300))
