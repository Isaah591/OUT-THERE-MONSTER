"""
Proportion-pass review sheets: original Roblox monster vs previous proportions vs corrected.

    python proportion_sheet.py <new_dir> <before_dir> <references_dir>
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

new, before, refs = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
except OSError:
    FONT = ImageFont.load_default()


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.width, 44), fill=(20, 20, 22))
    d.text((12, 7), text, fill=(235, 235, 235), font=FONT)
    return im


def row(images, h, pad=8):
    ims = [i.resize((round(i.width * h / i.height), h), Image.LANCZOS) for i in images]
    out = Image.new("RGB", (sum(i.width for i in ims) + pad * (len(ims) - 1), h), (12, 12, 12))
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + pad
    return out


def stack(rows, pad=8):
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + pad * (len(rows) - 1)),
                    (12, 12, 12))
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height + pad
    return out


def img(d, n):
    return Image.open(os.path.join(d, n + ".png")).convert("RGB")


def ref(n, box):
    return Image.open(os.path.join(refs, "roblox_original_%d.webp" % n)).convert("RGB").crop(box)


stack([
    row([label(ref(1, (420, 150, 1420, 1050)), "ORIGINAL (Roblox)"),
         label(img(before, "front"), "PREVIOUS"), label(img(new, "front"), "CORRECTED")], h=620),
    row([label(ref(3, (700, 240, 1380, 1200)), "ORIGINAL side"),
         label(img(before, "side_r"), "PREVIOUS side"), label(img(new, "side_r"), "CORRECTED side")], h=620),
]).save(os.path.join(new, "_proportion_compare.png"))

stack([
    row([label(img(before, "threequarter"), "PREVIOUS 3/4"), label(img(new, "threequarter"), "CORRECTED 3/4"),
         label(img(new, "rear"), "CORRECTED rear")], h=620),
    row([label(img(new, "head_front"), "CORRECTED head"), label(img(new, "head_34"), "CORRECTED head 3/4")], h=520),
]).save(os.path.join(new, "_proportion_views.png"))
print("proportion sheets written")
