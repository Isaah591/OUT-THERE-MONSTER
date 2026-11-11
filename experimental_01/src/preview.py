"""Fast software preview (painter's algorithm, PIL) - for checking shapes and silhouettes while
modelling.  Final pictures are rendered with Cycles (render.py)."""
import numpy as np
from PIL import Image, ImageDraw


def look_at(pos, target, up=(0, 0, 1)):
    pos = np.asarray(pos, float)
    f = np.asarray(target, float) - pos
    f /= np.linalg.norm(f)
    r = np.cross(f, np.asarray(up, float))
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return pos, r, u, f


def project(V, cam, size):
    """cam: dict(pos, target, fov (deg, vertical) | ortho (world height)). Returns (xy, depth)."""
    pos, r, u, f = look_at(cam["pos"], cam["target"], cam.get("up", (0, 0, 1)))
    d = np.asarray(V, float) - pos
    x, y, z = d @ r, d @ u, d @ f
    W, H = size
    if "ortho" in cam:
        s = H / cam["ortho"]
        px = W / 2 + x * s
        py = H / 2 - y * s
    else:
        s = (H / 2) / np.tan(np.radians(cam["fov"]) / 2)
        zz = np.maximum(z, 1e-3)
        px = W / 2 + x / zz * s
        py = H / 2 - y / zz * s
    return np.stack([px, py], 1), z


def render(items, cam, size=(700, 700), bg=(26, 27, 29), light=(-0.45, -0.65, 0.62), ambient=0.38, ss=2):
    """items: list of dict(V, Q, T, color=(r,g,b) 0..1 or fcolor=(nfaces,3))."""
    W, H = size[0] * ss, size[1] * ss
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    L = np.asarray(light, float)
    L /= np.linalg.norm(L)
    polys, depth, cols = [], [], []
    pos, r, u, f = look_at(cam["pos"], cam["target"], cam.get("up", (0, 0, 1)))
    for it in items:
        V = np.asarray(it["V"], float)
        if len(V) == 0:
            continue
        xy, z = project(V, cam, (W, H))
        off = 0
        for key, k in (("Q", 4), ("T", 3)):
            F = it.get(key)
            if F is None or len(F) == 0:
                continue
            F = np.asarray(F)
            P = V[F]
            n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            facing = (n @ -f) > -0.05 if "ortho" in cam else np.einsum("ij,ij->i", n, pos - P.mean(1)) > 0
            sh = ambient + (1 - ambient) * np.clip(n @ L, 0, 1)
            if "fcolor" in it:
                c = np.asarray(it["fcolor"])[off:off + len(F)]
            else:
                c = np.tile(np.asarray(it["color"], float), (len(F), 1))
            off += len(F)
            c = np.clip(c * sh[:, None], 0, 1) ** (1 / 2.2)
            zf = z[F].mean(1)
            ok = facing & (z[F].min(1) > 0.01)
            for i in np.nonzero(ok)[0]:
                polys.append(xy[F[i]])
                depth.append(zf[i])
                cols.append(c[i])
    order = np.argsort(depth)[::-1]
    for i in order:
        p = polys[i]
        c = cols[i]
        dr.polygon([tuple(q) for q in p], fill=(int(c[0] * 255), int(c[1] * 255), int(c[2] * 255)))
    if ss > 1:
        img = img.resize(size, Image.LANCZOS)
    return img


def silhouette(items, cam, size):
    W, H = size
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for it in items:
        V = np.asarray(it["V"], float)
        if len(V) == 0:
            continue
        xy, z = project(V, cam, (W, H))
        for key in ("Q", "T"):
            F = it.get(key)
            if F is None or len(F) == 0:
                continue
            for face in np.asarray(F):
                dr.polygon([tuple(q) for q in xy[face]], fill=255)
    return np.asarray(img) > 0
