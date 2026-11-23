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
  meal + water / BLACK WATER bottle (props/ were cut from our own thumbnails; the combo varies per video).
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
    return build(tmp, title, key=key)


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
