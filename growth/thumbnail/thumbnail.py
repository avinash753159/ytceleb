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
- Look: dark background with red brand light and streaks, white Impact line + yellow-on-red tag, "CELEB WORKOUT" corner.
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


# ---------- text ----------
def text_lines(title):
    t = re.sub(r"\s*\((V\d+[^)]*)\)", "", title).replace("#shorts", "").strip()
    m = re.match(r"Train Like (.+?):", t)
    if m:
        return "TRAIN LIKE", m.group(1).upper()
    star = re.split(r"\s+(Workout|Training|Diet)\b|:|'s ", t)[0].strip()
    if len(star) > 22 or star == t:
        return None, t.split(":")[0].upper()[:28]
    return star.upper(), "WORKOUT & DIET"


def _font(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def _fit(draw, txt, max_w, start, min_size=40):
    s = start
    while s > min_size:
        f = _font(FONT_BIG, s)
        if draw.textlength(txt, font=f) <= max_w:
            return f
        s -= 4
    return _font(FONT_BIG, min_size)


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


def _subject(im):
    global _SESSION
    from rembg import new_session, remove
    from scipy import ndimage
    _SESSION = _SESSION or new_session("u2net_human_seg")
    cut = remove(im, session=_SESSION)
    al = np.array(cut.split()[-1])
    lab, n = ndimage.label(al > 60)
    if n == 0:
        return None
    sizes = ndimage.sum(al > 60, lab, range(1, n + 1))
    mask = np.isin(lab, np.where(sizes >= sizes.max() * 0.25)[0] + 1)
    if mask.sum() < W * H * 0.03:
        return None
    al[~mask] = 0
    cut.putalpha(Image.fromarray(al))
    return cut.crop(Image.fromarray(al).point(lambda v: 255 if v > 60 else 0).getbbox())


def _background():
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    base = np.zeros((H, W, 3), "float32") + np.array([10, 10, 16], "float32")
    d1 = np.exp(-(((xx - W * .78) / (W * .32)) ** 2 + ((yy - H * .55) / (H * .6)) ** 2))
    d2 = np.exp(-(((xx - W * .1) / (W * .35)) ** 2 + ((yy - H * .1) / (H * .5)) ** 2))
    base += d1[..., None] * np.array(ACCENT, "float32") * .55 + d2[..., None] * np.array([40, 60, 110], "float32") * .5
    img = Image.fromarray(np.clip(base + np.random.default_rng(1).normal(0, 4, (H, W, 1)), 0, 255).astype("uint8"))
    d = ImageDraw.Draw(img, "RGBA")
    for k in range(7):
        x0 = 520 + k * 110
        d.polygon([(x0, 0), (x0 + 38, 0), (x0 - 260, H), (x0 - 298, H)], fill=ACCENT + (22,))
    return img


def build(picture, l1, l2):
    im = ImageOps.fit(picture.convert("RGB"), (W, H), Image.LANCZOS)
    canvas = _background().convert("RGBA")
    subj = _subject(im)
    if subj is None:
        raise SystemExit("Could not cut out a person from this picture; pass a clearer real --photo.")
    sc = min(H * 1.02 / subj.height, 660 / subj.width, 2.4)
    subj = subj.resize((int(subj.width * sc), int(subj.height * sc)), Image.LANCZOS)
    subj = ImageEnhance.Color(ImageEnhance.Sharpness(ImageEnhance.Contrast(subj).enhance(1.12)).enhance(1.5)).enhance(1.12)
    x = W - subj.width - max(0, (660 - subj.width) // 2) - 20; y = H - subj.height
    ga = Image.new("L", (W, H)); ga.paste(subj.split()[-1], (x, y))
    rim = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    rim.putalpha(ga.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * .52)))
    glow = Image.new("RGBA", (W, H), ACCENT + (255,))
    glow.putalpha(ga.filter(ImageFilter.MaxFilter(21)).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * .8)))
    canvas = Image.alpha_composite(Image.alpha_composite(canvas, rim), glow)
    canvas.alpha_composite(subj, (x, y))
    d = ImageDraw.Draw(canvas)
    f1 = _fit(d, l1, 600, 150) if l1 else None
    f2 = _fit(d, l2, 556, 120)
    h1 = d.textbbox((0, 0), l1, font=f1)[3] + 24 if l1 else 0
    tb = d.textbbox((0, 0), l2, font=f2); h2 = tb[3] + 34
    ty = (H - (h1 + h2)) // 2 - 20
    if l1:
        d.text((52, ty + 7), l1, font=f1, fill=(0, 0, 0, 210))
        d.text((46, ty), l1, font=f1, fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
        ty += h1
    box = (40, ty, 40 + tb[2] + 44, ty + h2)
    d.rounded_rectangle(tuple(v + 9 for v in box), 14, fill=(0, 0, 0, 180))
    d.rounded_rectangle(box, 14, fill=ACCENT, outline=(255, 255, 255), width=4)
    d.text((62, ty + 8), l2, font=f2, fill=(255, 235, 59), stroke_width=5, stroke_fill=(0, 0, 0))
    d.text((46, H - 62), "CELEB WORKOUT", font=_font(FONT_SMALL, 28), fill=(255, 255, 255, 220), stroke_width=2, stroke_fill=(0, 0, 0))
    return canvas.convert("RGB")


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
        build(pic, *text_lines(title)).save(out, quality=90)
        print("built", out)

    if a.cmd in ("upload", "auto"):
        backup_current(yt, a.video_id)
        set_thumb(yt, a.video_id, out)
        print("uploaded", a.video_id, "(undo: python thumbnail.py rollback --video-id", a.video_id, "--token ...)")


if __name__ == "__main__":
    main()
