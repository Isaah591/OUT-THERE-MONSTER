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


BODY_DIST = 11.5
HEAD_T = np.array([-0.045, -1.47, 2.20])      # middle of the head (between the mask and the chin)

VIEWS = {
    # full figure - the sheet's three body panels
    "front": cam(0.0, 0.3, (-0.210, -0.55, 1.390), BODY_DIST, 3.020, (490, 496)),
    "tq": cam(26.5, 0.3, (-0.090, -0.550, 1.490), BODY_DIST, 3.310, (510, 496)),
    "side": cam(90.0, 0.3, (0.0, -0.860, 1.500), BODY_DIST, 3.000, (468, 496)),
    # head and mouth - the sheet's close-up panels
    "head": cam(27.0, -3.0, HEAD_T + (0.03, 0.0, 0.03), 4.2, 1.16, (438, 352)),
    "mouth": cam(27.0, -9.0, HEAD_T + (0.03, 0.0, -0.12), 3.4, 0.64, (310, 313)),
    "jawside": cam(58.0, -2.0, HEAD_T + (0.0, 0.10, -0.08), 3.6, 0.72, (231, 263)),
    "sideclose": cam(68.0, 0.0, HEAD_T + (0.0, 0.18, 0.06), 4.2, 1.08, (286, 317)),
    # exact profile of the mouth (asked for in the brief)
    "mouthside": cam(90.0, 0.0, HEAD_T + (0.0, 0.10, -0.06), 4.2, 1.10, (330, 330)),
    # working views of the head
    "hfront": cam(0.0, 0.0, HEAD_T, 7.0, 1.10, (400, 440)),
    "hside": cam(90.0, 0.0, HEAD_T + (0, 0.1, 0), 7.0, 1.30, (440, 440)),
}

# which sheet panel each view answers
PANEL_OF = {"front": "front", "tq": "tq", "side": "side", "head": "head", "mouth": "mouth",
            "jawside": "jaw_new", "sideclose": "sideclose"}
