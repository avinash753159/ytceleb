"""Build 1280x720 thumbnails: rembg subject cutout + bold text, from the video's own current thumbnail."""
import json, glob, os, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from rembg import remove, new_session
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
IMPACT = r"C:\Windows\Fonts\impact.ttf"; ARIALBD = r"C:\Windows\Fonts\arialbd.ttf"
W, H = 1280, 720
SESSION = None

def props():
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "out*.json"))):
        for r in json.load(open(p, encoding="utf-8")): out[r["id"]] = r
    return out

def text_lines(title):
    t = re.sub(r"\s*\((V\d+[^)]*)\)", "", title).replace("#shorts", "").strip()
    m = re.match(r"Train Like (.+?):", t)
    if m: return "TRAIN LIKE", m.group(1).upper()
    star = re.split(r"\s+(Workout|Training|Diet)\b|:|'s ", t)[0].strip()
    if len(star) > 22 or star == t: return None, t.split(":")[0].upper()[:28]
    return star.upper(), "WORKOUT & DIET"

def fit(draw, txt, font_path, max_w, start, min_size=40):
    s = start
    while s > min_size:
        f = ImageFont.truetype(font_path, s)
        if draw.textlength(txt, font=f) <= max_w: return f
        s -= 4
    return ImageFont.truetype(font_path, min_size)

def clean_bg(accent):
    import numpy as np
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    base = np.zeros((H, W, 3), "float32") + np.array([10, 10, 16], "float32")
    # accent light behind the subject (right), cool fill top-left
    d1 = np.exp(-(((xx - W*0.78)/(W*0.32))**2 + ((yy - H*0.55)/(H*0.6))**2))
    d2 = np.exp(-(((xx - W*0.1)/(W*0.35))**2 + ((yy - H*0.1)/(H*0.5))**2))
    base += d1[..., None] * np.array(accent, "float32") * 0.55 + d2[..., None] * np.array([40, 60, 110], "float32") * 0.5
    noise = np.random.default_rng(1).normal(0, 4, (H, W, 1))
    img = Image.fromarray(np.clip(base + noise, 0, 255).astype("uint8"))
    # diagonal speed streaks
    d = ImageDraw.Draw(img, "RGBA")
    for k in range(7):
        x0 = 520 + k * 110
        d.polygon([(x0, 0), (x0 + 38, 0), (x0 - 260, H), (x0 - 298, H)], fill=accent + (22,))
    return img

def subject(im):
    global SESSION
    import numpy as np
    from scipy import ndimage
    SESSION = SESSION or new_session("u2net_human_seg")
    cut = remove(im, session=SESSION)
    a = np.array(cut.split()[-1]) > 60
    lab, n = ndimage.label(a)
    if n == 0: return None
    sizes = ndimage.sum(a, lab, range(1, n + 1)); keep = sizes >= sizes.max() * 0.25
    mask = np.isin(lab, np.where(keep)[0] + 1)
    if mask.sum() < W * H * 0.03: return None
    al = np.array(cut.split()[-1]); al[~mask] = 0
    cut.putalpha(Image.fromarray(al))
    return cut.crop(Image.fromarray(al).point(lambda v: 255 if v > 60 else 0).getbbox())

def build(src, l1, l2, accent=(230, 30, 40), subj=None):
    im = ImageOps.fit(Image.open(src).convert("RGB"), (W, H), Image.LANCZOS) if src else None
    canvas = clean_bg(accent).convert("RGBA")
    subj = subj if subj is not None else (subject(im) if im else None)
    if subj is not None:
        sc = min(H * 1.02 / subj.height, 660 / subj.width, 2.4)
        subj = subj.resize((int(subj.width*sc), int(subj.height*sc)), Image.LANCZOS)
        subj = ImageEnhance.Contrast(subj).enhance(1.12); subj = ImageEnhance.Sharpness(subj).enhance(1.5)
        subj = ImageEnhance.Color(subj).enhance(1.12)
        x = W - subj.width - max(0, (660 - subj.width)//2) - 20; y = H - subj.height
        ga = Image.new("L", (W, H)); ga.paste(subj.split()[-1], (x, y))
        rim = ga.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v*0.95))
        col = Image.new("RGBA", (W, H), (255, 255, 255, 255)); col.putalpha(rim.point(lambda v: int(v*0.55)))
        canvas = Image.alpha_composite(canvas, col)
        col2 = Image.new("RGBA", (W, H), accent + (255,)); col2.putalpha(ga.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v*0.8)))
        canvas = Image.alpha_composite(canvas, col2)
        canvas.alpha_composite(subj, (x, y))
    d = ImageDraw.Draw(canvas)
    maxw = 600
    f1 = fit(d, l1, IMPACT, maxw, 150) if l1 else None
    f2 = fit(d, l2, IMPACT, maxw - 44, 120)
    h1 = (d.textbbox((0, 0), l1, font=f1)[3] + 24) if l1 else 0
    tb = d.textbbox((0, 0), l2, font=f2); h2 = tb[3] + 34
    y = (H - (h1 + h2)) // 2 - 20
    if l1:
        d.text((52, y+7), l1, font=f1, fill=(0, 0, 0, 210))
        d.text((46, y), l1, font=f1, fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
        y += h1
    box = (40, y, 40 + tb[2] + 44, y + h2)
    d.rounded_rectangle((box[0]+9, box[1]+9, box[2]+9, box[3]+9), 14, fill=(0, 0, 0, 180))
    d.rounded_rectangle(box, 14, fill=accent, outline=(255, 255, 255), width=4)
    d.text((62, y + 8), l2, font=f2, fill=(255, 235, 59), stroke_width=5, stroke_fill=(0, 0, 0))
    fb = ImageFont.truetype(ARIALBD, 28)
    d.text((46, H - 62), "CELEB WORKOUT", font=fb, fill=(255, 255, 255, 220), stroke_width=2, stroke_fill=(0, 0, 0))
    return canvas.convert("RGB")

if __name__ == "__main__":
    P = props(); ids = sys.argv[1:]
    for i in ids:
        l1, l2 = text_lines(P[i]["title"])
        build(os.path.join(HERE, "orig", f"{i}.jpg"), l1, l2).save(os.path.join(HERE, "new", f"{i}.jpg"), quality=90)
        print(i, l1, "|", l2)
