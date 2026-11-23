"""V4 = the channel's own best style (Bucky Barnes / Lamine / Hemsworth / Captain America thumbnails):
real photo scene, star big on the right, huge white WORKOUT & DIET PLAN or TRAIN LIKE, red name box,
real plate + BLACK WATER bottle (cut from our own Bucky thumbnail), warm backlight glow."""
import os, re, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_thumb as m
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps, ImageChops
from scipy import ndimage
from rembg import remove, new_session
W, H = 1280, 720
IMPACT = r"C:\Windows\Fonts\impact.ttf"
RED = (206, 17, 26)
HERE = os.path.dirname(os.path.abspath(__file__))
PD = os.path.join(HERE, "props", "final")
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

if __name__ == "__main__":
    P = m.props()
    for i in sys.argv[1:]:
        o = build(f"orig/{i}.jpg", P[i]["title"], key=i)
        if o is None: print("SKIP", i); continue
        o.save(f"v4/{i}.jpg", quality=92); print(i, texts(P[i]["title"]))
