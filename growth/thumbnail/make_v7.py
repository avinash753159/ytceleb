"""V7 thumbnails + evals.
Look (Men's Health 10M-view style): real star sharp on the right, softened real background, huge italic TRAIN LIKE / EAT LIKE,
red name tag, a real meal + bottle on EVERY thumbnail (15 meals x bottles x mirror, balanced so nearby videos differ).
Evals (all must pass before upload): name present, meal present, a face detected and fully inside the frame with margin,
face and star big enough. Results -> v7_evals.csv. A human (Claude) then checks every image for wrong person / artifacts."""
import os, sys, csv, zlib, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_thumb as m, make_v4 as v4, make_v6 as v6
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps, ImageChops

W, H = 1280, 720
PD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "props")
FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
PROFILE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
FOODS = ["food_cruise", "food_tyson", "food_kim", "food_brad", "food_deadpool", "food_lamine", "food_steak",
         "food_cavill", "food_dua", "food_omelette", "food_bale"]
SETS = ["set_bucky", "set_hems", "set_cap"]
BOTTLES = ["bottle_black", "bottle_clear"]
COMBOS = [(s, None, False) for s in SETS] + \
         [(fd, b, f) for fd in FOODS for b in BOTTLES for f in (False, True)]


def L(n):
    return Image.open(os.path.join(PD, n + ".png")).convert("RGBA")


def meal(combo):
    food, bottle, flip = combo
    f = L(food)
    if flip and not food.startswith("set_"):  # flip the plate only; bottles/labels never mirrored
        f = ImageOps.mirror(f)
    if bottle:
        b = L(bottle); bh = int(f.height * 1.05); b = b.resize((max(1, int(b.width * bh / b.height)), bh), Image.LANCZOS)
        c = Image.new("RGBA", (f.width + int(b.width * 0.6), max(f.height, bh)), (0, 0, 0, 0))
        c.alpha_composite(f, (0, c.height - f.height)); c.alpha_composite(b, (c.width - b.width, c.height - bh)); f = c
    return f


def assign_meals(ids, star_of):
    """Balanced: least-used combo; never the same meal as the previous 3 videos or another video of the same star."""
    used = {c: 0 for c in COMBOS}; recent = []; star_meals = {}; out = {}
    for i in ids:
        st = star_of.get(i, i)
        cands = sorted(COMBOS, key=lambda c: (used[c], zlib.crc32((i + str(c)).encode())))
        pick = next((c for c in cands if c[0] not in recent[-3:] and c[0] not in star_meals.get(st, set())), cands[0])
        out[i] = pick; used[pick] += 1; recent.append(pick[0]); star_meals.setdefault(st, set()).add(pick[0])
    return out


def face_box(img):
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    f = FACE.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    if len(f) == 0:
        f = PROFILE.detectMultiScale(g, 1.1, 5, minSize=(40, 40))
    return max(f, key=lambda b: b[2] * b[3]) if len(f) else None


def build(src, title, combo, word):
    name, _ = v6.name_of(title)
    if not name:
        return None, "no name"
    im = ImageOps.fit(Image.open(src).convert("RGB"), (W, H), Image.LANCZOS, centering=(0.5, 0.3))
    p, touch = v4.cut(im)
    if p is None:
        return None, "no person"
    fb = face_box(p)
    bg = im.resize((W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(20))
    img = ImageEnhance.Brightness(ImageEnhance.Color(bg).enhance(0.45)).enhance(0.55).convert("RGBA")
    sc = min(H * 1.12 / p.height, 820 / p.width, 3.0)
    for _ in range(30):  # shrink until the whole face sits >= 30px below the top edge
        if fb is None or (H - int(p.height * sc)) + fb[1] * sc >= 30:
            break
        sc *= 0.95
    p = p.resize((int(p.width * sc), int(p.height * sc)), Image.LANCZOS)
    al = p.split()[-1]
    rgb = ImageEnhance.Sharpness(ImageEnhance.Color(ImageEnhance.Contrast(p.convert("RGB")).enhance(1.15)).enhance(1.15)).enhance(1.4)
    p = rgb.convert("RGBA"); p.putalpha(al)
    x = W - p.width if touch["r"] else max(W - p.width - 20, 400)
    if touch["l"] and not touch["r"]:
        g = Image.new("L", p.size, 255); gd = ImageDraw.Draw(g)
        for i in range(90):
            gd.line([(i, 0), (i, p.height)], fill=int(255 * i / 90))
        p.putalpha(ImageChops.multiply(al, g))
    y = H - p.height
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(p.split()[-1], (x - 25, y + 10))
    sh.putalpha(sa.filter(ImageFilter.GaussianBlur(25)).point(lambda v: int(v * .55))); img = Image.alpha_composite(img, sh)
    # GLOW behind the star (owner 2026-11-23): warm light burst behind the head + wide halo + tight bright rim
    A = Image.new("L", (W, H)); A.paste(p.split()[-1], (x, y))
    fx = x + p.width / 2; fy = y + p.height * 0.28
    if fb is not None:
        fx = x + (fb[0] + fb[2] / 2) * p.width / max(1, al.width); fy = y + (fb[1] + fb[3] / 2) * p.height / max(1, al.height)
    yy0, xx0 = np.mgrid[0:H, 0:W].astype("float32")
    burst = np.exp(-(((xx0 - fx) / 330) ** 2 + ((yy0 - fy) / 300) ** 2))
    bl = Image.new("RGBA", (W, H), (255, 165, 70, 255)); bl.putalpha(Image.fromarray((burst * 200).astype("uint8")))
    img = Image.alpha_composite(img, bl)
    halo = Image.new("RGBA", (W, H), (255, 140, 40, 255))
    halo.putalpha(A.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(45)).point(lambda v: min(255, int(v * 0.95))))
    img = Image.alpha_composite(img, halo)
    rim = Image.new("RGBA", (W, H), (255, 225, 170, 255))
    rim.putalpha(A.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.75)))
    img = Image.alpha_composite(img, rim)
    img.alpha_composite(p, (x, y))
    a = np.asarray(img.convert("RGB"), "float32"); yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    a *= (1 - 0.30 * np.clip(((xx - W * .65) / (W * .8)) ** 2 + ((yy - H * .45) / (H * .85)) ** 2, 0, 1))[..., None]
    img = Image.fromarray(np.clip(a, 0, 255).astype("uint8")).convert("RGBA")
    pr = meal(combo); pw = 560 if pr.width / pr.height > 1.6 else 470
    pr = pr.resize((pw, int(pr.height * pw / pr.width)), Image.LANCZOS)
    if pr.height > 330:
        pr = pr.resize((int(pr.width * 330 / pr.height), 330), Image.LANCZOS)
    px, py = 10, H - pr.height + 6
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sa = Image.new("L", (W, H)); sa.paste(pr.split()[-1], (px + 10, py + 4))
    sh.putalpha(sa.filter(ImageFilter.GaussianBlur(16)).point(lambda v: int(v * .7))); img = Image.alpha_composite(img, sh)
    img.alpha_composite(pr, (px, py))
    s, (lw, lh) = v6.italic_text(img, (10, 10), word, 200, maxw=min(660, x + 160))
    v6.tag(img, (44, 10 + lh - 20), name, 50)
    fbc = None if fb is None else (int(x + fb[0] * sc), int(y + fb[1] * sc), int(fb[2] * sc), int(fb[3] * sc))
    return img.convert("RGB"), {"star_h": p.height, "meal": combo[0], "bottle": combo[1], "name": name, "face_canvas": fbc}


def evaluate(path, meta):
    im = Image.open(path); fb = meta.get("face_canvas") or face_box(im); r = {}  # face measured on the real photo before the glow
    r["name_present"] = bool(meta.get("name"))
    r["meal_present"] = bool(meta.get("meal"))
    r["face_detected"] = fb is not None
    r["face_inside"] = fb is not None and fb[1] >= 15 and fb[0] + fb[2] <= W and fb[1] + fb[3] <= H
    r["face_big_enough"] = fb is not None and fb[3] >= H * 0.12
    r["star_big_enough"] = meta.get("star_h", 0) >= H * 0.6
    r["pass"] = all(r.values())
    return r


if __name__ == "__main__":
    P = m.props(); ids = open("v6_order.txt").read().split()
    star = {i: (v6.name_of(P[i]["title"])[0] or i) for i in ids}
    meals = assign_meals(ids, star)
    os.makedirs("v7", exist_ok=True); rows = []
    for i in ids:
        word = "EAT LIKE" if zlib.crc32(i.encode()) % 2 else "TRAIN LIKE"
        img, meta = build(f"orig/{i}.jpg", P[i]["title"], meals[i], word)
        if img is None:
            rows.append({"id": i, "title": P[i]["title"], "pass": False, "reason": meta}); continue
        img.save(f"v7/{i}.jpg", quality=92)
        r = evaluate(f"v7/{i}.jpg", meta)
        r.update({"id": i, "title": P[i]["title"], "meal": meta["meal"], "bottle": meta["bottle"], "word": word,
                  "reason": ",".join(k for k, v in r.items() if v is False)})
        rows.append(r)
    keys = ["id", "title", "pass", "reason", "name_present", "meal_present", "face_detected", "face_inside",
            "face_big_enough", "star_big_enough", "meal", "bottle", "word"]
    with open("v7_evals.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    print(sum(1 for r in rows if r["pass"]), "pass of", len(rows))
