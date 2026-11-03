"""
The approved sheet's three-quarter camera (`ref34` in render_views.py, fitted with fit_camera.py)
as plain geometry: project world points to the sheet panel's pixels, and turn panel pixels into
world-space rays (to place joints on the lines of sight of the reference's landmarks).

Panel pixels: the sheet's three-quarter panel, 508 x 495 (crop (500, 55, 1008, 550) of
references/r08_open_jaw_sheet_v2.webp). The camera renders at exactly twice that resolution.

Pure numpy (no bpy needed); matches Blender's perspective camera with a horizontal 36 mm sensor
fit and lens shift (shift in units of the image width).
"""
import numpy as np

LOC = np.array([1.6734, -4.74, 2.1633])
TARGET = np.array([-0.15, -0.55, 1.45])
LENS = 46.27
SHIFT = (0.0478, 0.0149)
PANEL = (508, 495)


def frame():
    fwd = TARGET - LOC
    fwd = fwd / np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    return fwd, right, up


FWD, RIGHT, UP = frame()
K = LENS / 36.0                       # focal length in units of the image width


def project(points):
    """World points (N, 3) -> panel pixels (N, 2) and depth along the view axis."""
    P = np.atleast_2d(np.asarray(points, float)) - LOC
    z = P @ FWD
    x = (P @ RIGHT) / z
    y = (P @ UP) / z
    W, H = PANEL
    u = (0.5 + x * K - SHIFT[0]) * W                 # Blender: positive shift moves the frame right
    v = (0.5 - (y * K - SHIFT[1]) * W / H) * H
    return np.stack([u, v], 1), z


def ray(u, v):
    """Panel pixel -> (origin, unit direction) in world space."""
    W, H = PANEL
    x = (u / W - 0.5 + SHIFT[0]) / K
    y = ((0.5 - v / H) * H / W + SHIFT[1]) / K
    d = FWD + x * RIGHT + y * UP
    return LOC.copy(), d / np.linalg.norm(d)


def on_plane_z(u, v, z):
    """Point on the line of sight of panel pixel (u, v) at world height z."""
    o, d = ray(u, v)
    t = (z - o[2]) / d[2]
    return o + t * d


def at_depth(u, v, depth):
    """Point on the line of sight of panel pixel (u, v) at the given depth along the view axis."""
    o, d = ray(u, v)
    return o + d * (depth / (d @ FWD))


def closest_on_ray(u, v, p):
    """Point on the line of sight of (u, v) closest to world point p."""
    o, d = ray(u, v)
    return o + d * ((np.asarray(p, float) - o) @ d)
