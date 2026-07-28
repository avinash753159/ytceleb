#!/usr/bin/env python3
"""bruce_interludes.py - build Berton-interview interlude segments.

Two modes (manifest/interludes.json):
  video      - the kinescope picture itself, cropped past the burned
               caption strip (he throws the punch on camera)
  audio_over - Lee's interview audio over verified b-roll windows
               (documentary standard; the picture carries our label)

Writes final_video/v6_work/seg_{idx:03d}_zz_{id}.mp4 (A+V, 48k stereo)
exactly where v10_assemble expects them.
"""
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MAN = ROOT / "manifest"
DOS = ROOT / "dossier" / "david_corenswet"
V6W = ROOT / "final_video" / "v6_work"
V6W.mkdir(parents=True, exist_ok=True)
FONT = ROOT / "graphics" / "public" / "fonts" / "Anton-Regular.ttf"
ACCENT = (242, 194, 48)

CROPS = {
 "Ox8ZLF6cGM0": [0,0,0,0], "0IwY7Mfzw_w": [0,0,0,0],
 "odsQwCAOU2k":  [0.02, 0.14, 0.02, 0.14],
 "YHHQF1SHHLw":  [0.125, 0.14, 0.125, 0.11],
 "-OI1zyajOpw":  [0.12, 0.0, 0.12, 0.0],
}

assets = json.loads((MAN / "assets_v5.json").read_text())
inters = json.loads((MAN / "interludes.json").read_text())
order = sorted(assets)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{r.stderr[-1200:]}")


def crop_vf(cb):
    if not cb:
        return ""
    l, t, rr, b = cb
    return f"crop=iw*{1-l-rr:.4f}:ih*{1-t-b:.4f}:iw*{l:.4f}:ih*{t:.4f},"


def lower_third(label, path):
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(str(FONT), 44)
    f2 = ImageFont.truetype(str(FONT), 26)
    w = dr.textlength(label, font=f1)
    x, y = 70, 940
    dr.rectangle([x - 18, y - 14, x + w + 26, y + 64],
                 fill=(12, 12, 14, 216))
    dr.rectangle([x - 18, y - 14, x - 10, y + 64], fill=ACCENT + (255,))
    dr.text((x, y), label, font=f1, fill=(255, 255, 255, 255))
    dr.text((x, y + 52), "INTERVIEW", font=f2, fill=ACCENT + (255,))
    img.save(path)


def main():
    for it in inters:
        idx = order.index(it["after"])
        out = V6W / f"seg_{idx:03d}_zz_{it['id']}.mp4"
        if out.exists() and out.stat().st_size > 10000:
            continue
        dur = it["t1"] - it["t0"]
        lt = V6W / f"lt_{it['id']}.png"
        lower_third(it["label"], lt)
        src = str(DOS / f"{it['vid']}.mp4")
        af = (f"atrim=start={it['t0']}:end={it['t1']},asetpts=PTS-STARTPTS,"
              "afade=t=in:d=0.25,"
              f"afade=t=out:st={max(dur - 0.3, 0):.2f}:d=0.3,"
              "aformat=channel_layouts=stereo:sample_rates=48000")
        if it["mode"] == "video":
            vf = (crop_vf(it.get("crop_box")) +
                  "scale=1920:1080:force_original_aspect_ratio=increase,"
                  "crop=1920:1080,fps=30,setsar=1")
            run(["ffmpeg", "-ss", f"{it['t0']:.2f}",
                 "-to", f"{it['t1']:.2f}", "-i", src,
                 "-loop", "1", "-i", str(lt),
                 "-filter_complex",
                 f"[0:v]{vf}[v0];[v0][1:v]overlay=0:0:shortest=1[vo];"
                 f"[0:a]afade=t=in:d=0.25,"
                 f"afade=t=out:st={max(dur - 0.3, 0):.2f}:d=0.3,"
                 "aformat=channel_layouts=stereo:sample_rates=48000[ao]",
                 "-map", "[vo]", "-map", "[ao]",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                 "-y", str(out)])
        else:
            bsrc, b0, b1 = it["broll"][0]
            bvf = (crop_vf(CROPS.get(bsrc)) +
                   "scale=1920:1080:force_original_aspect_ratio=increase,"
                   "crop=1920:1080,fps=30,setsar=1")
            broll = V6W / f"broll_{it['id']}.mp4"
            run(["ffmpeg", "-ss", f"{b0:.2f}", "-to", f"{b1:.2f}",
                 "-i", str(DOS / f"{bsrc}.mp4"), "-vf", bvf, "-an",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                 "-y", str(broll)])
            run(["ffmpeg", "-stream_loop", "-1", "-i", str(broll),
                 "-i", src, "-loop", "1", "-i", str(lt),
                 "-filter_complex",
                 f"[0:v][2:v]overlay=0:0:shortest=1[vo];[1:a]{af}[ao]",
                 "-map", "[vo]", "-map", "[ao]",
                 "-t", f"{dur:.3f}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                 "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                 "-y", str(out)])
        print(f"[OK] {out.name} ({dur:.1f}s)")
    print("[OK] interludes built")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
