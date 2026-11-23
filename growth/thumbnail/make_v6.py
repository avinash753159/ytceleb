"""V6 = what the 10M-view celebrity fitness thumbnails do (Men's Health Train Like / Eat Like):
full-bleed REAL photo, star big, 2 words. Styles rotate per video:
  TRAIN  : full photo, huge white italic 'TRAIN LIKE' bottom-left, small red name tag
  EAT    : full photo, big real meal spread bottom-left, 'EAT LIKE' top-left + red name tag
  SPLIT  : (needs 2 photos) before | after with white arrow, 'TRAIN LIKE' bottom"""
import os, sys, zlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_thumb as m, make_v4 as v4
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps, ImageChops
W, H = 1280, 720
IMPACT = r"C:\Windows\Fonts\impact.ttf"
RED, WHITE = (214, 20, 28), (255, 255, 255)

def name_of(title):
    big, name = v4.texts(title)
    return name, big == ["TRAIN LIKE"]

def italic_text(img, xy, txt, size, fill=WHITE, shadow=True, maxw=None):
    f = ImageFont.truetype(IMPACT, size)
    d0 = ImageDraw.Draw(img)
    if maxw:
        while d0.textlength(txt, font=f) > maxw and size > 40:
            size -= 4; f = ImageFont.truetype(IMPACT, size)
    tw = int(d0.textlength(txt, font=f)) + 80; th = int(size * 1.35)
    layer = Image.new("RGBA", (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.text((20, 0), txt, font=f, fill=fill + (255,))
    sh = 0.18
    layer = layer.transform((tw + int(th * sh), th), Image.AFFINE, (1, sh, -th * sh, 0, 1, 0), Image.BICUBIC)
    if shadow:
        s = layer.split()[-1].filter(ImageFilter.GaussianBlur(10))
        blk = Image.new("RGBA", layer.size, (0, 0, 0, 255)); blk.putalpha(s.point(lambda v: int(v * .85)))
        img.alpha_composite(blk, (xy[0] + 6, xy[1] + 8))
    img.alpha_composite(layer, xy)
    return size, layer.size

def tag(img, xy, txt, size=44):
    d = ImageDraw.Draw(img); f = ImageFont.truetype(IMPACT, size)
    tb = d.textbbox((0, 0), txt, font=f); box = (xy[0], xy[1], xy[0] + tb[2] + 34, xy[1] + tb[3] + 18)
    d.rectangle(box, fill=RED); d.text((xy[0] + 17, xy[1] + 6), txt, font=f, fill=WHITE)
    return box

def scene(src, prefer_right=True):
    """Full-bleed real photo, framed so the person sits right of centre, graded punchy."""
    im = Image.open(src).convert("RGB")
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.3))
    p, touch = v4.cut(im)
    im = ImageEnhance.Contrast(im).enhance(1.12); im = ImageEnhance.Color(im).enhance(1.15); im = ImageEnhance.Sharpness(im).enhance(1.3)
    a = np.asarray(im, "float32")
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    vig = 1 - 0.45 * np.clip(((xx - W * .6) / (W * .75)) ** 2 + ((yy - H * .45) / (H * .8)) ** 2, 0, 1)
    bottom = 1 - 0.55 * np.clip((yy - H * 0.55) / (H * 0.45), 0, 1) * np.clip((W * 0.75 - xx) / (W * 0.75), 0, 1)
    a *= (vig * bottom)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8")).convert("RGBA"), p

def style_train(src, title, vid):
    img, _ = scene(src)
    name, _ = name_of(title)
    s, (lw, lh) = italic_text(img, (10, H - 250), "TRAIN LIKE", 190, maxw=W - 120)
    if name: tag(img, (40, H - 250 - 62), name)
    return img

def style_eat(src, title, vid):
    img, _ = scene(src)
    name, _ = name_of(title)
    pr = v4.prop_for(vid + "eat"); pw = 640
    pr = pr.resize((pw, int(pr.height * pw / pr.width)), Image.LANCZOS)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(pr.split()[-1], (-10, H - pr.height + 4))
    sh.putalpha(sa.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * .7))); img = Image.alpha_composite(img, sh)
    img.alpha_composite(pr, (-30, H - pr.height + 10))
    s, (lw, lh) = italic_text(img, (10, 10), "EAT LIKE", 200, maxw=640)
    if name: tag(img, (44, 10 + lh - 20), name)
    return img

STYLES = [style_train, style_eat]

def build(src, title, vid, style=None):
    fn = STYLES[zlib.crc32(vid.encode()) % len(STYLES)] if style is None else style
    return fn(src, title, vid).convert("RGB")

if __name__ == "__main__":
    P = m.props()
    for i in sys.argv[1:]:
        for st in STYLES:
            build(f"orig/{i}.jpg", P[i]["title"], i, st).save(f"v6/{i}_{st.__name__}.jpg", quality=92)
        print(i)


def face_crop(src, w, h):
    """Crop a real photo to w x h centred on the largest face (falls back to upper-centre)."""
    import cv2
    im = Image.open(src).convert("RGB")
    sc = max(w / im.width, h / im.height) * 1.25
    im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    g = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2GRAY)
    faces = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml").detectMultiScale(g, 1.15, 6, minSize=(60, 60))
    if len(faces):
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3]); cx, cy = x + fw / 2, y + fh / 2
    else:
        cx, cy = im.width / 2, im.height * 0.35
    left = int(min(max(cx - w / 2, 0), im.width - w)); top = int(min(max(cy - h * 0.3, 0), im.height - h))
    return im.crop((left, top, left + w, top + h))

def style_split(before, after, title, vid):
    """Real BEFORE | AFTER photos, diagonal white split, white arrow, name tag, TRAIN LIKE."""
    half = W // 2 + 60
    b = face_crop(before, half, H); a = face_crop(after, half, H)
    b = ImageEnhance.Color(b).enhance(0.75); b = ImageEnhance.Brightness(b).enhance(0.92)
    a = ImageEnhance.Contrast(a).enhance(1.15); a = ImageEnhance.Color(a).enhance(1.2); a = ImageEnhance.Sharpness(a).enhance(1.3)
    img = Image.new("RGBA", (W, H)); img.paste(b, (0, 0))
    mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).polygon([(W // 2 + 40, 0), (W, 0), (W, H), (W // 2 - 40, H)], fill=255)
    full_a = Image.new("RGB", (W, H)); full_a.paste(a, (W - half, 0))
    img.paste(full_a, (0, 0), mask)
    d = ImageDraw.Draw(img)
    d.line([(W // 2 + 40, 0), (W // 2 - 40, H)], fill=WHITE, width=14)
    cx, cy = W // 2, H // 2
    d.polygon([(cx - 42, cy - 70), (cx + 58, cy), (cx - 42, cy + 70)], fill=WHITE, outline=(0, 0, 0))
    d.polygon([(cx - 30, cy - 48), (cx + 38, cy), (cx - 30, cy + 48)], fill=RED)
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    shade = Image.fromarray((255 * (1 - 0.6 * np.clip((yy - H * .6) / (H * .4), 0, 1))).astype("uint8"))
    img = Image.composite(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), shade)
    name, _ = name_of(title)
    italic_text(img, (10, H - 220), "TRAIN LIKE", 170, maxw=W - 120)
    if name: tag(img, (40, H - 220 - 60), name)
    for txt, x in (("BEFORE", 30), ("AFTER", W - 190)):
        tag(img, (x, 24), txt, 40)
    return img.convert("RGB")


def scene_clean(src):
    """For originals with old text baked in: star kept sharp (real cutout), background = same photo softened
    (depth-of-field look) so old text disappears, star placed right like the Men's Health thumbnails."""
    im = ImageOps.fit(Image.open(src).convert("RGB"), (W, H), Image.LANCZOS, centering=(0.5, 0.3))
    p, touch = v4.cut(im)
    if p is None: return None
    bg = im.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    bg = ImageEnhance.Brightness(ImageEnhance.Color(bg).enhance(0.45)).enhance(0.55)
    img = bg.convert("RGBA")
    sc = min(H * 1.12 / p.height, 820 / p.width, 3.0)
    p = p.resize((int(p.width * sc), int(p.height * sc)), Image.LANCZOS)
    al = p.split()[-1]
    rgb = ImageEnhance.Sharpness(ImageEnhance.Color(ImageEnhance.Contrast(p.convert("RGB")).enhance(1.15)).enhance(1.15)).enhance(1.4)
    p = rgb.convert("RGBA"); p.putalpha(al)
    x = W - p.width if touch["r"] else max(W - p.width - 20, 380)
    if touch["l"] and not touch["r"]:
        g = Image.new("L", p.size, 255); gd = ImageDraw.Draw(g)
        for i in range(90): gd.line([(i, 0), (i, p.height)], fill=int(255 * i / 90))
        p.putalpha(ImageChops.multiply(al, g))
    y = H - p.height if p.height >= H or touch["b"] else H - p.height
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(p.split()[-1], (x - 25, y + 10))
    sh.putalpha(sa.filter(ImageFilter.GaussianBlur(25)).point(lambda v: int(v * .55))); img = Image.alpha_composite(img, sh)
    img.alpha_composite(p, (x, y))
    a = np.asarray(img.convert("RGB"), "float32")
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    vig = 1 - 0.40 * np.clip(((xx - W * .65) / (W * .8)) ** 2 + ((yy - H * .45) / (H * .85)) ** 2, 0, 1)
    bottom = 1 - 0.5 * np.clip((yy - H * 0.55) / (H * 0.45), 0, 1) * np.clip((W * 0.7 - xx) / (W * 0.7), 0, 1)
    a *= (vig * bottom)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype("uint8")).convert("RGBA")

def build_clean(src, title, vid):
    img = scene_clean(src)
    if img is None: return None
    name, _ = name_of(title)
    if zlib.crc32(vid.encode()) % 2 == 0:
        italic_text(img, (10, H - 250), "TRAIN LIKE", 190, maxw=W - 120)
        if name: tag(img, (40, H - 250 - 62), name)
    else:
        pr = v4.prop_for(vid + "eat"); pw = 600
        pr = pr.resize((pw, int(pr.height * pw / pr.width)), Image.LANCZOS)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(pr.split()[-1], (-10, H - pr.height + 4))
        sh.putalpha(sa.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * .7))); img = Image.alpha_composite(img, sh)
        img.alpha_composite(pr, (-30, H - pr.height + 10))
        s, (lw, lh) = italic_text(img, (10, 10), "EAT LIKE", 200, maxw=640)
        if name: tag(img, (44, 10 + lh - 20), name)
    return img.convert("RGB")
