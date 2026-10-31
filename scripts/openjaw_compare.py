"""
Side-by-side sheets against the ASTRA R08 - MORE OPEN JAW sheet (same panel framing).

    python openjaw_compare.py <renders_dir> <references_dir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

renders, refs = sys.argv[1], sys.argv[2]
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
except OSError:
    FONT = ImageFont.load_default()
SHEET = Image.open(os.path.join(refs, "r08_open_jaw_sheet.webp")).convert("RGB")
PANELS = {  # sheet crops (pixels of the 1484 x 1060 sheet)
    "front": (0, 55, 490, 550), "34": (495, 55, 978, 550), "side": (985, 55, 1484, 550),
    "head": (0, 557, 438, 912), "mouth": (629, 595, 862, 862),
    "arm": (20, 120, 235, 548), "torso": (180, 100, 375, 330),
}
PAIRS = [("front", "oj_front", "FRONT (ORTHO)", "_oj_vs_front.png"),
         ("34", "oj_34", "THREE-QUARTER", "_oj_vs_34.png"),
         ("side", "oj_side", "EXACT SIDE", "_oj_vs_side.png"),
         ("head", "oj_head", "HEAD CLOSE-UP", "_oj_vs_head.png"),
         ("mouth", "oj_mouth_side", "MOUTH, SIDE PROFILE", "_oj_vs_mouth.png"),
         ("arm", "oj_arm", "LONG ARM", "_oj_vs_arm.png"),
         ("torso", "oj_torso", "TORSO / WOUNDS", "_oj_vs_torso.png")]


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 40), fill=(18, 18, 20))
    d.text((10, 6), text, fill=(235, 235, 235), font=FONT)
    return im


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


for key, render, title, name in PAIRS:
    path = os.path.join(renders, render + ".png")
    if not os.path.exists(path):
        continue
    h = 760
    a = label(fit(SHEET.crop(PANELS[key]), h), "SHEET - " + title)
    b = label(fit(Image.open(path).convert("RGB"), h), "MODEL - " + title)
    out = Image.new("RGB", (a.width + b.width + 10, h), (10, 10, 10))
    out.paste(a, (0, 0))
    out.paste(b, (a.width + 10, 0))
    out.save(os.path.join(renders, name))
print("open-jaw comparison sheets written")
