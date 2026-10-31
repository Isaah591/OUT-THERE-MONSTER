"""
Side-by-side comparison against the Astra R08 reference sheet (same panel aspect).

    python r08_compare.py <renders_dir> <references_dir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

renders, refs = sys.argv[1], sys.argv[2]
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
except OSError:
    FONT = ImageFont.load_default()
SHEET = Image.open(os.path.join(refs, "r08_reference_sheet_primary.webp")).convert("RGB")
DETAIL = Image.open(os.path.join(refs, "r08_remaster_surface_2.webp")).convert("RGB")   # detail panels
PANELS = {"front": (0, 30, 537, 628), "34": (537, 30, 1111, 628), "side": (1111, 30, 1586, 628),
          "head": (0, 656, 380, 992),
          # R08 side-view head at the same scale and centre as the `mouth_profile` camera
          # (1.25 m wide, centred on y -0.52 / z 2.22; R08 sheet ~0.0051 m per pixel)
          "head_side": (1197, 68, 1442, 272)}


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 40), fill=(18, 18, 20))
    d.text((10, 6), text, fill=(235, 235, 235), font=FONT)
    return im


def fit(im, h):
    return im.resize((round(im.width * h / im.height), h), Image.LANCZOS)


DETAILS = {"det_shoulder": (0, 30, 398, 364), "det_arm": (398, 30, 796, 364)}


def pair(ref_key, render, title, h=760):
    src = DETAIL.crop(DETAILS[ref_key]) if ref_key in DETAILS else SHEET.crop(PANELS[ref_key])
    a = label(fit(src, h), "ASTRA R08 - " + title)
    b = label(fit(Image.open(os.path.join(renders, render + ".png")).convert("RGB"), h), "RECONSTRUCTION - " + title)
    out = Image.new("RGB", (a.width + b.width + 10, h), (10, 10, 10))
    out.paste(a, (0, 0))
    out.paste(b, (a.width + 10, 0))
    return out


for key, render, title, name in (("front", "r08_front", "FRONT", "_r08_vs_front.png"),
                                 ("side", "r08_side", "EXACT SIDE", "_r08_vs_side.png"),
                                 ("34", "r08_34", "THREE-QUARTER", "_r08_vs_34.png"),
                                 ("head", "head_close", "HEAD", "_r08_vs_head.png"),
                                 ("head_side", "mouth_profile", "MOUTH PROFILE", "_r08_vs_mouth_profile.png"),
                                 ("det_shoulder", "torso_close", "SHOULDER / TORSO", "_r08_vs_torso.png"),
                                 ("det_arm", "arm_close", "LONG ARM", "_r08_vs_arm.png")):
    if os.path.exists(os.path.join(renders, render + ".png")):
        pair(key, render, title).save(os.path.join(renders, name))
prof = Image.open(os.path.join(renders, "mouth_profile.png")).convert("RGB")
label(prof, "NEW MOUTH - EXACT PROFILE (Pac-Man wedge)").save(os.path.join(renders, "_mouth_profile.png"))
print("R08 comparison sheets written")
