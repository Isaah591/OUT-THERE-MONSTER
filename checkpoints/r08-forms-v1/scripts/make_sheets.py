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


def has(n):
    return os.path.exists(os.path.join(renders, n + ".png"))


def R08(box):
    return Image.open(os.path.join(refs, "r08_remaster_surface_1.webp")).convert("RGB").crop(box)


def SHEET(box):
    return Image.open(os.path.join(refs, "r08_reference_sheet_primary.webp")).convert("RGB").crop(box)


if has("wound_shoulder"):   # v3: panel-by-panel against the R08 reference sheet
    P = {"front": (0, 30, 537, 628), "3/4": (537, 30, 1111, 628), "side": (1111, 30, 1586, 628),
         "head": (0, 656, 380, 992), "shoulder": (380, 656, 770, 992), "arm": (770, 656, 1188, 992),
         "leg": (1188, 656, 1586, 992)}
    stack([row([label(SHEET(P["front"]), "R08 FRONT"), label(R("front"), "v3 FRONT (ortho)")], h=620),
           row([label(SHEET(P["3/4"]), "R08 3/4"), label(R("threequarter"), "v3 THREE-QUARTER")], h=620),
           row([label(SHEET(P["side"]), "R08 SIDE"), label(R("side_r"), "v3 SIDE 90deg (ortho)")], h=620)]
          ).save(os.path.join(renders, "_compare_r08_body.png"))
    stack([row([label(SHEET(P["head"]), "R08 HEAD"), label(R("head_front"), "v3 HEAD")], h=480),
           row([label(SHEET(P["shoulder"]), "R08 SHOULDER"), label(R("wound_shoulder"), "v3 SHOULDER")], h=480),
           row([label(SHEET(P["arm"]), "R08 ARM"), label(R("wound_arm"), "v3 ARM")], h=480),
           row([label(SHEET(P["leg"]), "R08 LEG"), label(R("wound_leg"), "v3 LEG")], h=480)]
          ).save(os.path.join(renders, "_compare_r08_detail.png"))
    stack([row([label(R("front"), "FRONT"), label(R("threequarter"), "THREE-QUARTER"),
                label(R("side_r"), "SIDE 90deg")], h=700)]).save(os.path.join(renders, "_sheet_main.png"))
    stack([row([label(R("head_front"), "HEAD"), label(R("mouth"), "MOUTH"), label(R("wound_shoulder"), "SHOULDER")], h=480),
           row([label(R("wound_leg"), "LEG"), label(R("wound_arm"), "ARM"), label(R("wound_torso"), "FLANK")], h=480)]
          ).save(os.path.join(renders, "_sheet_closeups.png"))
    print("v3 sheets written")
    raise SystemExit

if has("head_front"):   # v2 review sheets
    stack([row([label(R("front"), "FRONT (ortho)"), label(R("threequarter"), "THREE-QUARTER"),
                label(R("side_r"), "SIDE R 90deg (ortho)")], h=700)]).save(os.path.join(renders, "_sheet_main.png"))
    stack([row([label(R("head_front"), "HEAD"), label(R("mouth"), "MOUTH")], h=520),
           row([label(R("wound_leg"), "TISSUE - LEG"), label(R("wound_arm"), "TISSUE - ARM"),
                label(R("wound_torso"), "TISSUE - FLANK")], h=520)]).save(os.path.join(renders, "_sheet_closeups.png"))
    stack([row([label(REF(1, (420, 150, 1420, 1050)), "ORIGINAL front"), label(R("front"), "v2 front")], h=560),
           row([label(REF(3, (700, 240, 1380, 1200)), "ORIGINAL side"), label(R("side_r"), "v2 side R")], h=560)]
          ).save(os.path.join(renders, "_compare_original.png"))
    stack([row([label(R08((0, 628, 380, 992)), "R08 head (benchmark)"), label(R("head_front"), "v2 head")], h=520),
           row([label(R08((1188, 628, 1586, 992)), "R08 leg tissue (benchmark)"), label(R("wound_leg"), "v2 leg tissue")], h=520)]
          ).save(os.path.join(renders, "_compare_r08.png"))
    print("v2 sheets written")
    raise SystemExit

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
