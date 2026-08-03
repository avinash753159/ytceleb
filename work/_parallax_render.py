"""Render a 2.5D parallax move from the depth layers, in ffmpeg.

parallax.py produces layers for Remotion's <ParallaxPhoto>. The rest of this
film is assembled in ffmpeg, so rather than pull Remotion into the picture
chain for one shot, the layers are composited here: each is scaled up and
drifts at its own rate under a single virtual camera, nearest fastest.

Drift is deliberately small. The inpainting behind the subject is classical
(Telea), so it fills convincingly at a few dozen pixels and smears if pushed -
which is why the far layer moves least, not most.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1920, 1080, 30


def render(name: str, dur: float, dest: Path, layers_dir: Path) -> Path:
    L = [layers_dir / f"{name}_L{i}.png" for i in range(3)]
    for p in L:
        if not p.exists():
            raise FileNotFoundError(p)
    n = int(round(dur * FPS))
    # (zoom, total horizontal drift px, total vertical drift px)
    # far layer moves least; near layer moves most.
    spec = [(1.10, 16, 6), (1.15, 34, 10), (1.21, 58, 16)]
    ins, filt = [], []
    for i, (p, (z, dx, dy)) in enumerate(zip(L, spec)):
        ins += ["-loop", "1", "-t", f"{dur + 0.12:.4f}", "-i", str(p)]
        sw, sh = int(W * z) // 2 * 2, int(H * z) // 2 * 2
        # ease the drift so it starts and ends calm
        t = f"(1-pow(1-min(1,n/{n}),3))"
        filt.append(
            f"[{i}:v]scale={sw}:{sh}:flags=lanczos,"
            # crop has no `eval` option - that belongs to scale/overlay - and
            # it re-evaluates x/y every frame anyway. Passing eval=frame here
            # makes ffmpeg reject the whole filter graph.
            f"crop={W}:{H}:x='({sw}-{W})/2+{dx}*({t}-0.5)*2'"
            f":y='({sh}-{H})/2+{dy}*({t}-0.5)*2'[l{i}]")
    filt.append("[l0][l1]overlay=0:0:format=auto[a]")
    filt.append("[a][l2]overlay=0:0:format=auto[b]")
    fade = (f"[b]fps={FPS},fade=t=in:st=0:d=0.3,"
            f"fade=t=out:st={max(0, dur-0.3):.3f}:d=0.3,format=yuv420p[v]")
    filt.append(fade)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *ins,
         "-filter_complex", ";".join(filt), "-map", "[v]",
         "-t", f"{dur:.4f}", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-threads", "2", str(dest)],
        check=True, timeout=900)
    return dest


if __name__ == "__main__":
    out = ROOT / "work/parallax/jimmy_symptoms_move.mp4"
    render("jimmy_symptoms", 6.0, out, ROOT / "work/parallax")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=nb_read_frames,width,height",
         "-of", "default=nw=1", str(out)],
        capture_output=True, text=True).stdout.strip()
    print(f"[OK] {out}\n{r}")
