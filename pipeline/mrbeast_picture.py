"""Build the locked MrBeast V2 picture cut against the approved radio master."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_MODE = __import__("os").environ.get("MRBEAST_FINAL", "0") == "1"
PLAN = ROOT / "manifest/mrbeast_picture_plan_v2.json"
CUTLIST = ROOT / ("manifest/mrbeast_radio_cutlist_v2_final.json" if FINAL_MODE else "manifest/mrbeast_radio_cutlist_v2.json")
RADIO = ROOT / ("final_video/MRBEAST_RADIO_V2_FINAL.mp4" if FINAL_MODE else "final_video/MRBEAST_RADIO_V2.mp4")
OUT = ROOT / ("final_video/THE_DISEASE_THAT_BUILT_MRBEAST_FINAL.mp4" if FINAL_MODE else "final_video/MRBEAST_V2_PICTURE_DRAFT.mp4")
WORK = ROOT / ("work/mrbeast_picture_v2_final" if FINAL_MODE else "work/mrbeast_picture_v2")
LOGO = ROOT / "library/brand/brand_lockup.png"
FONT = ROOT / "graphics/public/fonts/Anton-Regular.ttf"
FONT_FF = "graphics/public/fonts/Anton-Regular.ttf"

W, H, FPS = 1920, 1080, 30

DOCS = {
    "n004": "dossier/mrbeast/documents/niddk_definition.png",
    "s005": "dossier/mrbeast/documents/niddk_definition.png",
    "n009": "dossier/mrbeast/documents/niddk_definition.png",
    "n017": "dossier/mrbeast/documents/niddk_definition.png",
    "n030": "dossier/mrbeast/documents/niddk_diet.png",
    "n044": "dossier/mrbeast/documents/niddk_treatment.png",
}

CARDS = {
    "n020": ("1. MAKE IT OBSERVABLE", "ACCOUNTABILITY PACT  /  PROGRAMMED REST"),
    "n021": ("DAY 310", "FOLLOWING THE PACT  /  TRAINING + PROGRAMMED REST"),
    "n024": ("3. DAILY MOVEMENT", "15,000 STEPS/DAY  /  JIMMY'S JUNE 2023 ACCOUNT"),
    "n026": ("4. PROTECTED TIME", "~90 MIN WORKOUT  /  AT LEAST 2 HOURS REDIRECTED"),
    "s027": ("DAILY MOVEMENT", "WALKING CALLS  /  ILLUSTRATIVE"),
    "n028": ("FOOD: DETAILS NOT PUBLIC", "NO VERIFIED MEAL PLAN  /  NO VERIFIED CALORIE TARGET"),
    "c029": ("FOOD: DETAILS NOT PUBLIC", "EVIDENCE BOUNDARY"),
    "n031": ("THE FOUR PRINCIPLES", "ACCOUNTABILITY  /  TRAINING + RECOVERY  /  DAILY MOVEMENT  /  PROTECTED TIME"),
    "n033": ("TWO DATED ACCOUNTS", "JUNE 2023: DAY 310  /  JUNE 2024: 600-DAY CHALLENGE"),
    "n050": ("WHAT THE RECORD SUPPORTS", "SUSTAINED LIFTING  /  TRAINER + ACCOUNTABILITY PACT"),
    "n051": ("THE ORDINARY SYSTEM", "TRAIN  /  REST  /  WALK  /  CHECK IN"),
    "s057": ("CELEB WORKOUT", "THE DISEASE THAT BUILT MRBEAST"),
}

FALLBACK = {
    "n002": ("dossier/mrbeast/sources/cWEUE8X7p-k.mp4", 420.0),
    "n006": ("dossier/mrbeast/archive/AKJfakEsgy0.mp4", 49.0),
    "n012": ("dossier/mrbeast/archive/AKJfakEsgy0.mp4", 7.0),
    "n014": ("dossier/mrbeast/sources/cWEUE8X7p-k.mp4", 590.0),
    "s016": ("dossier/mrbeast/sources/NdjcGrpNSF4.mp4", 530.0),
    "n047": ("dossier/mrbeast/sources/WwVs1qVaOb4.mp4", 160.0),
}


def run(args: list[str]) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def esc(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace(":", r"\:")
        .replace("'", "")
        .replace("%", r"\%")
    )


def common_overlay() -> str:
    return (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1[base];"
        f"[1:v]scale=250:-1[logo];"
        f"[base][logo]overlay=W-w-42:36,format=yuv420p"
    )


def source_piece(path: Path, t0: float, dur: float, out: Path, label: str | None = None) -> None:
    vf = common_overlay()
    if label:
        vf += (
            f",drawbox=x=42:y={H-142}:w=820:h=90:color=black@0.72:t=fill,"
            f"drawtext=fontfile='{FONT_FF}':text='{esc(label)}':"
            f"fontcolor=white:fontsize=48:x=68:y={H-126}"
        )
    run([
        "ffmpeg", "-y", "-ss", f"{t0:.3f}", "-i", str(path), "-loop", "1", "-i", str(LOGO),
        "-t", f"{dur:.6f}", "-filter_complex", vf, "-an", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", str(out),
    ])


def card_piece(title: str, subtitle: str, dur: float, out: Path) -> None:
    title, subtitle = esc(title), esc(subtitle)
    vf = (
        f"[0:v]drawbox=x=0:y=0:w=24:h={H}:color=#E3120B:t=fill,"
        f"drawbox=x=92:y=250:w=1736:h=4:color=#E3120B:t=fill,"
        f"drawtext=fontfile='{FONT_FF}':text='{title}':"
        "fontcolor=white:fontsize=112:x=(w-text_w)/2:y=330,"
        f"drawtext=fontfile='{FONT_FF}':text='{subtitle}':"
        "fontcolor=#D8D8D8:fontsize=44:x=(w-text_w)/2:y=510[base];"
        f"[1:v]scale=250:-1[logo];[base][logo]overlay=W-w-42:36,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=#090909:s={W}x{H}:r={FPS}",
        "-loop", "1", "-i", str(LOGO), "-t", f"{dur:.6f}", "-filter_complex", vf,
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out),
    ])


def document_piece(path: Path, dur: float, out: Path, label: str) -> None:
    vf = (
        f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=#101010[doc];"
        f"[doc]drawbox=x=0:y=0:w={W}:h=130:color=black@0.82:t=fill,"
        f"drawtext=fontfile='{FONT_FF}':text='{esc(label)}':"
        "fontcolor=white:fontsize=54:x=56:y=36[base];"
        f"[1:v]scale=250:-1[logo];[base][logo]overlay=W-w-42:36,format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(path), "-loop", "1", "-i", str(LOGO),
        "-t", f"{dur:.6f}", "-filter_complex", vf, "-an", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out),
    ])


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text(encoding="utf-8-sig"))["segments"]
    cuts = json.loads(CUTLIST.read_text(encoding="utf-8"))["segments"]
    assert [x["id"] for x in plan] == [x["id"] for x in cuts]

    pieces: list[Path] = []
    for i, (pic, cut) in enumerate(zip(plan, cuts)):
        sid, dur = cut["id"], float(cut["dur"])
        out = WORK / f"{i:03d}_{sid}.mp4"
        pieces.append(out)
        if out.exists():
            continue
        if sid in DOCS:
            document_piece(ROOT / DOCS[sid], dur, out, "MEDICAL CONTEXT  /  NIH-NIDDK")
        elif sid in CARDS:
            card_piece(*CARDS[sid], dur, out)
        else:
            source = pic.get("source_path")
            t0 = pic.get("t0")
            if not source and sid in FALLBACK:
                source, t0 = FALLBACK[sid]
            if source:
                label = None
                if source.endswith("WwVs1qVaOb4.mp4"):
                    label = "LATER WORKOUT FOOTAGE  /  SEPT. 2024"
                elif sid in {"n034", "s036", "n039", "s041"}:
                    label = "AIRRACK'S SIDE  /  JUNE 2024 ACCOUNT"
                source_piece(ROOT / source, float(t0 or 0), dur, out, label)
            else:
                card_piece("THE MRBEAST SYSTEM", cut.get("chapter", "").upper(), dur, out)

    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in pieces), encoding="utf-8")
    silent = WORK / "picture_silent.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-an",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", str(silent)])
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(RADIO), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(OUT)])
    print(OUT)


if __name__ == "__main__":
    main()
