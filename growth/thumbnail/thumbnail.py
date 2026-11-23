"""Celeb Workout thumbnail builder + uploader (REAL celebrity only, never AI-generated imagery).

Run it right after a video is uploaded:

    python thumbnail.py auto --video-id VIDEO_ID --video final.mp4 --token token_youtube_celebworkout.pickle
    python thumbnail.py auto --video-id VIDEO_ID --photo licensed_photo.jpg --token ...   # use a chosen real photo instead

Other commands:
    python thumbnail.py make     --video-id ID --title "Train Like Thor: ..." (--video f.mp4 | --photo p.jpg)   # build only, no upload
    python thumbnail.py upload   --video-id ID --token T        # upload out/<ID>.jpg (backs up the current one first)
    python thumbnail.py rollback --video-id ID --token T        # put the previous thumbnail back
    python thumbnail.py rollback --all --token T                # undo every thumbnail this tool ever uploaded

How it works
- Picture: a real frame from the video itself (sampled frames, the sharpest, largest frontal face wins) or a real photo you pass.
  The person is cut out (rembg u2net_human_seg) and placed right; nothing is generated or altered beyond cutout,
  contrast and sharpening.
- Text: from the video title. "Train Like X: ..." -> TRAIN LIKE / X. Otherwise STAR / WORKOUT & DIET.
- Look: copies the channel's best performers (Bucky Barnes / Lamine Yamal / Hemsworth thumbnails): real photo scene
  with warm backlight, star big on the right, huge white WORKOUT & DIET PLAN or TRAIN LIKE, red name box, and a real
  meal + water / BLACK WATER bottle (props/ were cut from our own thumbnails).
  Every video looks different: star left or right, warm/green/teal/red grade, headline (WORKOUT & DIET PLAN, TRAIN LIKE,
  GET BODY LIKE, INSANE TRAINING PLAN, + EAT LIKE THIS / DIET INCLUDED), red arrow or circled meal, meal + bottle combo.
- Safety: before every upload the CURRENT thumbnail is downloaded to backups/<ID>/<timestamp>.jpg and logged in
  backups/log.jsonl. rollback re-uploads the newest backup. Nothing is ever deleted.
- Quota: thumbnails.set = 50 units. Shorts are skipped (the Shorts feed ignores custom thumbnails).

Needs: pip install pillow rembg opencv-python scipy numpy google-api-python-client google-auth
"""
import argparse, glob, json, os, pickle, re, sys, time, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); BACK = os.path.join(HERE, "backups")
W, H = 1280, 720
ACCENT = (230, 30, 40)
FONT_BIG = next((p for p in [r"C:\Windows\Fonts\impact.ttf", "/usr/share/fonts/truetype/msttcorefonts/Impact.ttf",
                             "/Library/Fonts/Impact.ttf", os.path.join(HERE, "Impact.ttf")] if os.path.exists(p)), None)
FONT_SMALL = next((p for p in [r"C:\Windows\Fonts\arialbd.ttf", "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
                               "/Library/Fonts/Arial Bold.ttf"] if os.path.exists(p)), None)
_SESSION = None


# ---------- look: the channel's own best style (Bucky Barnes / Lamine / Hemsworth thumbnails) ----------
from scipy import ndimage
from rembg import remove, new_session
from PIL import ImageChops
IMPACT = FONT_BIG
RED = (206, 17, 26)
PD = os.path.join(HERE, "props")
def _l(n): return Image.open(os.path.join(PD, n + ".png")).convert("RGBA")
def compose(food, bottle):
    f, b = _l(food), _l(bottle)
    bh = int(f.height * 1.05); b = b.resize((int(b.width * bh / b.height), bh), Image.LANCZOS)
    c = Image.new("RGBA", (f.width + int(b.width * 0.6), max(f.height, bh)), (0, 0, 0, 0))
    c.alpha_composite(f, (0, c.height - f.height)); c.alpha_composite(b, (c.width - b.width, c.height - bh))
    return c
COMBOS = [lambda: _l("set_bucky"), lambda: _l("set_hems"), lambda: _l("set_cap"), lambda: _l("set_bale"),
          lambda: compose("food_cruise", "bottle_black"), lambda: compose("food_tyson", "bottle_clear"),
          lambda: compose("food_kim", "bottle_black"), lambda: compose("food_brad", "bottle_clear"),
          lambda: compose("food_deadpool", "bottle_black"), lambda: compose("food_cruise", "bottle_clear"),
          lambda: compose("food_tyson", "bottle_black"), lambda: compose("food_brad", "bottle_black")]
def prop_for(key):
    import zlib
    return COMBOS[zlib.crc32(key.encode()) % len(COMBOS)]()
S = None

def texts(title):
    t = re.sub(r"\s*\((V\d+[^)]*)\)", "", title).strip()
    mt = re.match(r"Train Like (.+?):", t)
    if mt: return ["TRAIN LIKE"], mt.group(1).upper()
    vs = re.match(r"((?:(?!Workout|Diet|Training).)+?) (vs|&) ((?:(?!Workout|Diet|Training).)+?)(:| Workout| Diet)", t)
    if vs: return ["WORKOUT", "& DIET PLAN"], f"{vs.group(1)} {vs.group(2).upper()} {vs.group(3)}".upper()
    star = re.split(r"\s+(Workout|Training|Diet)\b|:|'s ", t)[0].strip()
    if star == t or len(star) > 26: return [t.split(":")[0].upper()], None
    return ["WORKOUT", "& DIET PLAN"], star.upper()

def cut(im):
    global S
    S = S or new_session("u2net_human_seg")
    c = remove(im, session=S); al = np.array(c.split()[-1])
    lab, n = ndimage.label(al > 60)
    if n == 0: return None, None
    sizes = ndimage.sum(al > 60, lab, range(1, n + 1)); k = int(np.argmax(sizes)) + 1
    if sizes[k - 1] < W * H * 0.03: return None, None
    al[lab != k] = 0
    bb = Image.fromarray(al).point(lambda v: 255 if v > 60 else 0).getbbox()
    touch = {"l": bb[0] <= 4, "r": bb[2] >= W - 4, "t": bb[1] <= 4, "b": bb[3] >= H - 4}
    c.putalpha(Image.fromarray(al).filter(ImageFilter.GaussianBlur(0.8)))
    return c.crop(bb), touch

def fit(d, txt, maxw, start, lo=34):
    s = start
    while s > lo:
        f = ImageFont.truetype(IMPACT, s)
        if d.textlength(txt, font=f) <= maxw: return f
        s -= 3
    return ImageFont.truetype(IMPACT, lo)

def build(src, title, props=True, key=None):
    im = ImageOps.fit(Image.open(src).convert("RGB"), (W, H), Image.LANCZOS)
    p, touch = cut(im)
    if p is None: return None
    # scene: same real photo, soft focus, warm gym grade, dark on the text side
    bg = im.filter(ImageFilter.GaussianBlur(30))
    a = np.asarray(ImageEnhance.Color(bg).enhance(0.55), "float32") * 0.55
    a = a * np.array([1.12, 0.98, 0.80]) + np.array([14, 8, 0])
    xx = np.linspace(0, 1, W)[None, :, None]
    a *= 0.30 + 0.70 * np.clip((xx - 0.18) / 0.55, 0, 1)
    img = Image.fromarray(np.clip(a, 0, 255).astype("uint8")).convert("RGBA")
    # star: big, right, punchy
    sc = min(H * 1.08 / p.height, 760 / p.width, 3.0)
    p = p.resize((int(p.width * sc), int(p.height * sc)), Image.LANCZOS)
    al = p.split()[-1]
    rgb = ImageEnhance.Sharpness(ImageEnhance.Color(ImageEnhance.Contrast(p.convert("RGB")).enhance(1.15)).enhance(1.12)).enhance(1.5)
    p = rgb.convert("RGBA"); p.putalpha(al)
    x = W - p.width + (60 if not touch["r"] else 0); x = max(x, 520)
    if touch["r"]: x = W - p.width
    y = H - p.height + (0 if touch["b"] or p.height >= H else 0)
    if touch["l"]:  # arm/body cut at the photo edge: fade it out instead of showing a hard cut
        g = Image.new("L", p.size, 255); gd = ImageDraw.Draw(g)
        for i in range(90): gd.line([(i, 0), (i, p.height)], fill=int(255 * i / 90))
        al = ImageChops.multiply(al, g); p.putalpha(al)
    if touch["t"] and p.height < H:
        y = 0
    A = Image.new("L", (W, H)); A.paste(al, (x, y))
    glow = Image.new("RGBA", (W, H), (255, 150, 60, 255))
    glow.putalpha(A.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(45)).point(lambda v: int(v * 0.75)))
    img = Image.alpha_composite(img, glow)
    rim = Image.new("RGBA", (W, H), (255, 225, 180, 255))
    rim.putalpha(ImageChops.subtract(A.filter(ImageFilter.MaxFilter(5)), A).filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.8)))
    img.alpha_composite(p, (x, y)); img = Image.alpha_composite(img, rim)
    # plate + BLACK WATER, bottom, overlapping the star's lower edge
    if props:
        pr = prop_for(key or title); s2 = 540 / pr.width; pr = pr.resize((540, int(pr.height * s2)), Image.LANCZOS)
        px = max(300, min(x - 190, W - pr.width - 40)); py = H - pr.height
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(pr.split()[-1], (px - 10, py - 6))
        sh.putalpha(sa.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .6))); img = Image.alpha_composite(img, sh)
        img.alpha_composite(pr, (px, py))
    # text, Bucky layout
    big, name = texts(title)
    d = ImageDraw.Draw(img); maxw = 600
    f = min((fit(d, s, maxw, 200) for s in big), key=lambda f: f.size)
    yy = 30
    for s in big:
        d.text((44 + 5, yy + 7), s, font=f, fill=(0, 0, 0, 170)); d.text((44, yy), s, font=f, fill=(255, 255, 255))
        yy += int(f.size * 1.0)
    if name:
        fn = fit(d, name, maxw - 44, 96); tb = d.textbbox((0, 0), name, font=fn)
        yy += 16; box = (40, yy, 40 + tb[2] + 44, yy + tb[3] + 30)
        d.rectangle((box[0] + 6, box[1] + 8, box[2] + 6, box[3] + 8), fill=(0, 0, 0, 150))
        d.rectangle(box, fill=RED); d.text((62, yy + 11), name, font=fn, fill=(255, 255, 255))
    return img.convert("RGB")



# ---------- variety (v5): layout mirror, colour grade, headline, arrow / circled meal ----------
import math, zlib
RED, YEL, WHITE = (206, 17, 26), (255, 214, 0), (255, 255, 255)
GRADES = {  # multiplier, add, glow colour
    "warm":  ((1.12, 0.98, 0.80), (14, 8, 0), (255, 150, 60)),
    "green": ((0.80, 1.10, 0.90), (0, 14, 6), (120, 255, 150)),
    "teal":  ((0.75, 1.05, 1.15), (0, 18, 26), (60, 220, 255)),
    "red":   ((1.25, 0.75, 0.75), (30, 0, 0), (255, 60, 60)),
}

def headline(title, variant, star_or_role):
    t = re.sub(r"\s*\((V\d+[^)]*)\)", "", title)
    big, name = texts(t)
    if name is None: return big, None, None
    is_role = big == ["TRAIN LIKE"]
    opts = {0: (big, name, None),
            1: (["GET BODY", "LIKE"], name, None),
            2: (big, name, "EAT LIKE THIS"),
            3: (["INSANE", "TRAINING PLAN"], name, None),
            4: (big, name, "DIET INCLUDED")}
    return opts[variant]

def arrow(d, p0, p1, color=RED, width=22):
    # curved arrow p0 -> p1 with white outline
    (x0, y0), (x1, y1) = p0, p1
    cx, cy = (x0 + x1) / 2 - (y1 - y0) * 0.35, (y0 + y1) / 2 + (x1 - x0) * 0.35 * (1 if x1 > x0 else -1)
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1) for t in np.linspace(0, 0.86, 40)]
    ang = math.atan2(y1 - pts[-1][1], x1 - pts[-1][0]); L = 62
    head = [(x1, y1), (x1 - L * math.cos(ang - 0.55), y1 - L * math.sin(ang - 0.55)), (x1 - L * math.cos(ang + 0.55), y1 - L * math.sin(ang + 0.55))]
    for col, w in ((WHITE, width + 12), (color, width)):
        d.line(pts, fill=col, width=w, joint="curve")
        hh = head if col == color else [(x + (x - x1) * 0.0, y) for x, y in head]
        d.polygon(hh, fill=col, outline=WHITE if col == color else None)
        if col == WHITE: d.polygon(head, fill=WHITE); d.line(head + [head[0]], fill=WHITE, width=12)

def build5(src, title, vid):
    h = zlib.crc32(vid.encode())
    mirror = (h >> 1) % 3 == 0
    grade = list(GRADES)[(h >> 3) % 4]
    hv = (h >> 5) % 5
    use_arrow = (h >> 8) % 2 == 0
    circle = not use_arrow and (h >> 9) % 2 == 0
    mul, add, gl = GRADES[grade]
    im = ImageOps.fit(Image.open(src).convert("RGB"), (W, H), Image.LANCZOS)
    p, touch = cut(im)
    if p is None: return None
    if mirror:
        p = ImageOps.mirror(p); touch = {"l": touch["r"], "r": touch["l"], "t": touch["t"], "b": touch["b"]}
    bg = im.filter(ImageFilter.GaussianBlur(30))
    a = np.asarray(ImageEnhance.Color(bg).enhance(0.55), "float32") * 0.55 * np.array(mul) + np.array(add)
    xx = np.linspace(0, 1, W)[None, :, None]
    side = np.clip((xx - 0.18) / 0.55, 0, 1) if not mirror else np.clip((0.82 - xx) / 0.55, 0, 1)
    a *= 0.30 + 0.70 * side
    img = Image.fromarray(np.clip(a, 0, 255).astype("uint8")).convert("RGBA")
    sc = min(H * 1.08 / p.height, 760 / p.width, 3.0)
    p = p.resize((int(p.width * sc), int(p.height * sc)), Image.LANCZOS)
    al = p.split()[-1]
    rgb = ImageEnhance.Sharpness(ImageEnhance.Color(ImageEnhance.Contrast(p.convert("RGB")).enhance(1.15)).enhance(1.12)).enhance(1.5)
    p = rgb.convert("RGBA"); p.putalpha(al)
    if not mirror:
        x = W - p.width if touch["r"] else max(W - p.width + 60, 520)
    else:
        x = 0 if touch["l"] else min(-60, W - 520 - p.width)
        x = max(x, -p.width // 3)
    edge = "l" if not mirror else "r"
    if touch[edge]:
        g = Image.new("L", p.size, 255); gd = ImageDraw.Draw(g)
        for i in range(90):
            xx_ = i if edge == "l" else p.width - 1 - i
            gd.line([(xx_, 0), (xx_, p.height)], fill=int(255 * i / 90))
        al = ImageChops.multiply(al, g); p.putalpha(al)
    y = 0 if (touch["t"] and p.height < H) else H - p.height
    A = Image.new("L", (W, H)); A.paste(al, (x, y))
    glow = Image.new("RGBA", (W, H), gl + (255,)); glow.putalpha(A.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(45)).point(lambda v: int(v * .75)))
    img = Image.alpha_composite(img, glow)
    rim = Image.new("RGBA", (W, H), (255, 235, 200, 255)); rim.putalpha(ImageChops.subtract(A.filter(ImageFilter.MaxFilter(5)), A).filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * .8)))
    img.alpha_composite(p, (x, y)); img = Image.alpha_composite(img, rim)
    # meal
    pr = prop_for(vid); pw = 500; pr = pr.resize((pw, int(pr.height * pw / pr.width)), Image.LANCZOS)
    if not mirror: px = max(300, min(x - 170, W - pw - 40))
    else: px = min(W - pw - 300, x + p.width - 330); px = max(px, 420)
    py = H - pr.height
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(pr.split()[-1], (px - 10, py - 6))
    sh.putalpha(sa.filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .6))); img = Image.alpha_composite(img, sh)
    img.alpha_composite(pr, (px, py))
    _, _, _k = headline(title, hv, None)
    if _k: use_arrow, circle = False, True
    d = ImageDraw.Draw(img)
    if circle:
        cx, cy = px + pw * 0.42, py + pr.height * 0.55; r = pw * 0.48
        for col, w in ((WHITE, 16), (YEL, 10)): d.ellipse((cx - r, cy - r * 0.62, cx + r, cy + r * 0.62), outline=col, width=w)
    # text block
    big, name, kicker = headline(title, hv, None)
    tx = 44 if not mirror else W - 44 - 600
    maxw = 600
    f = min((fit(d, s, maxw, 200) for s in big), key=lambda f: f.size)
    yy = 30
    for s in big:
        wtxt = d.textlength(s, font=f); xx0 = tx if not mirror else W - 44 - wtxt
        d.text((xx0 + 5, yy + 7), s, font=f, fill=(0, 0, 0, 170)); d.text((xx0, yy), s, font=f, fill=WHITE)
        yy += int(f.size * 1.0)
    if name:
        fn = fit(d, name, maxw - 44, 96); tb = d.textbbox((0, 0), name, font=fn); bw = tb[2] + 44
        bx = tx if not mirror else W - 44 - bw
        yy += 16; box = (bx, yy, bx + bw, yy + tb[3] + 30)
        d.rectangle((box[0] + 6, box[1] + 8, box[2] + 6, box[3] + 8), fill=(0, 0, 0, 150)); d.rectangle(box, fill=RED)
        d.text((bx + 22, yy + 11), name, font=fn, fill=WHITE); yy = box[3]
    if kicker:
        fk = ImageFont.truetype(IMPACT, 76); kw = d.textlength(kicker, font=fk)
        kx = tx if not mirror else W - 44 - kw
        d.text((kx, yy + 18), kicker, font=fk, fill=YEL, stroke_width=5, stroke_fill=(0, 0, 0)); yy += 100
    if use_arrow:
        start = (tx + 180 if not mirror else W - 44 - 200, yy + 40)
        end = (px + 60 if not mirror else px + pw - 80, py + 40)
        if abs(end[1] - start[1]) > 60: arrow(d, start, end)
    return img.convert("RGB")


# ---------- v6: what 10M-view celebrity fitness thumbnails do (Men's Health Train Like / Eat Like, before/after) ----------
RED, WHITE = (214, 20, 28), (255, 255, 255)

def name_of(title):
    big, name = texts(title)
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
    p, touch = cut(im)
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
    pr = prop_for(vid + "eat"); pw = 640
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

# ---------- picture: real frame or real photo ----------
def best_frame(video_path, samples=80):
    """Pick the real frame with the biggest, sharpest frontal face."""
    import cv2
    cap = cv2.VideoCapture(video_path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    best, best_score = None, -1
    for k in range(samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * (0.05 + 0.9 * k / samples)))
        ok, fr = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        faces = face.detectMultiScale(g, 1.2, 6, minSize=(g.shape[0] // 8,) * 2)
        if len(faces) == 0:
            continue
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        sharp = cv2.Laplacian(g[y:y + h, x:x + w], cv2.CV_64F).var()
        score = (w * h) / (g.shape[0] * g.shape[1]) * min(sharp, 400)
        if score > best_score:
            best, best_score = fr, score
    cap.release()
    if best is None:
        raise SystemExit("No clear face found in the video; pass --photo with a real photo of the celebrity.")
    return Image.fromarray(best[:, :, ::-1])


def build_from(pic, title, key):
    tmp = os.path.join(OUT, "_src.jpg"); pic.convert("RGB").save(tmp, quality=95)
    return build(tmp, title, key)


# ---------- YouTube ----------
def api(token):
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build as gbuild
    creds = pickle.load(open(token, "rb"))
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    return gbuild("youtube", "v3", credentials=creds, cache_discovery=False)


def backup_current(yt, vid):
    sn = yt.videos().list(part="snippet", id=vid).execute()["items"][0]["snippet"]
    th = sn["thumbnails"]
    os.makedirs(os.path.join(BACK, vid), exist_ok=True)
    dest = os.path.join(BACK, vid, time.strftime("%Y%m%d-%H%M%S") + ".jpg")
    for k in sorted(th, key=lambda k: -th[k]["width"]):
        try:
            urllib.request.urlretrieve(th[k]["url"], dest)
            im = Image.open(dest).convert("RGB")
            if os.path.getsize(dest) > 2_000_000:
                im.resize((1280, 720)).save(dest, quality=90)
            break
        except Exception:
            continue
    else:
        raise SystemExit(f"Could not back up the current thumbnail of {vid}; not uploading.")
    with open(os.path.join(BACK, "log.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps({"id": vid, "backup": dest, "t": time.time()}) + "\n")
    return sn


def set_thumb(yt, vid, path):
    from googleapiclient.http import MediaFileUpload
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(path, mimetype="image/jpeg")).execute()


def rollback(yt, vid):
    files = sorted(glob.glob(os.path.join(BACK, vid, "*.jpg")))
    if not files:
        print("no backup for", vid); return
    set_thumb(yt, vid, files[-1])
    print("restored", vid, "from", files[-1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make", "upload", "auto", "rollback"])
    ap.add_argument("--video-id"); ap.add_argument("--title"); ap.add_argument("--video"); ap.add_argument("--photo")
    ap.add_argument("--token"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--before", help="REAL photo of the star before the transformation"); ap.add_argument("--after", help="REAL photo after")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{a.video_id}.jpg") if a.video_id else None
    yt = api(a.token) if a.cmd in ("upload", "auto", "rollback") else None

    if a.cmd == "rollback":
        ids = {json.loads(l)["id"] for l in open(os.path.join(BACK, "log.jsonl"), encoding="utf-8")} if a.all else [a.video_id]
        for vid in ids:
            rollback(yt, vid)
        return

    if a.cmd in ("make", "auto"):
        title = a.title
        if not title and yt:
            title = yt.videos().list(part="snippet", id=a.video_id).execute()["items"][0]["snippet"]["title"]
        if title.endswith("#shorts"):
            print("Short: skipped (Shorts feed ignores custom thumbnails)."); return
        if a.before and a.after:
            style_split(a.before, a.after, title, a.video_id).save(out, quality=92); print('built (before/after)', out)
        else:
          pic = Image.open(a.photo) if a.photo else best_frame(a.video)
          img = build_from(pic, title, a.video_id)
          if img is None: raise SystemExit('No clear person in this picture; pass --photo with a real photo of the celebrity.')
          img.save(out, quality=92)
          print("built", out)

    if a.cmd in ("upload", "auto"):
        backup_current(yt, a.video_id)
        set_thumb(yt, a.video_id, out)
        print("uploaded", a.video_id, "(undo: python thumbnail.py rollback --video-id", a.video_id, "--token ...)")


if __name__ == "__main__":
    main()
