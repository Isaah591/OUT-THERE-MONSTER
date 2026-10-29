"""
Build review sheets from rendered views (needs Pillow).

    python make_sheets.py <renders_dir> <references_dir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

renders, refs = sys.argv[1], sys.argv[2]
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
except OSError:
    FONT = ImageFont.load_default()


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 44), fill=(20, 20, 22))
    d.text((12, 7), text, fill=(235, 235, 235), font=FONT)
    return im


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


def row(images, h=600, pad=8):
    ims = [fit(i, h) for i in images]
    out = Image.new("RGB", (sum(i.width for i in ims) + pad * (len(ims) - 1), h), (12, 12, 12))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + pad
    return out


def stack(rows, pad=8):
    w = max(r.width for r in rows)
    out = Image.new("RGB", (w, sum(r.height for r in rows) + pad * (len(rows) - 1)), (12, 12, 12))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + pad
    return out


def R(name):
    return Image.open(os.path.join(renders, name + ".png")).convert("RGB")


def REF(n, box=None):
    im = Image.open(os.path.join(refs, "roblox_original_%d.webp" % n)).convert("RGB")
    return im.crop(box) if box else im


# 1. Blockout overview: front / side / three-quarter
views = [("front", "FRONT (ortho)"), ("side_r", "SIDE R 90deg (ortho)"),
         ("threequarter", "THREE-QUARTER")]
stack([row([label(R(v), t) for v, t in views])]).save(os.path.join(renders, "_sheet_blockout_main.png"))

views = [("side_l", "SIDE L 90deg (ortho)"), ("threequarter_l", "THREE-QUARTER L"),
         ("rear", "REAR (ortho)")]
stack([row([label(R(v), t) for v, t in views])]).save(os.path.join(renders, "_sheet_blockout_extra.png"))

# 2. Reference vs blockout, matched as closely as the screenshots allow
pairs = [
    (label(REF(1, (420, 150, 1420, 1050)), "REF 1 front"), label(R("front"), "BLOCKOUT front")),
    (label(REF(2, (700, 220, 1500, 1020)), "REF 2 side/3-4"), label(R("side_l"), "BLOCKOUT side L")),
    (label(REF(3, (700, 240, 1380, 1200)), "REF 3 side"), label(R("side_r"), "BLOCKOUT side R")),
    (label(REF(5, (680, 40, 1320, 700)), "REF 5 head"), label(R("head"), "BLOCKOUT head")),
]
stack([row(list(p), h=560) for p in pairs[:2]]).save(os.path.join(renders, "_compare_1.png"))
stack([row(list(p), h=560) for p in pairs[2:]]).save(os.path.join(renders, "_compare_2.png"))
print("sheets written")
