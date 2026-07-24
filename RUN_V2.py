#!/usr/bin/env python3
"""
RUN_V2 - v2 pipeline driver (treatment-planned, OCR-gated, QC-gated).

  narration -> words -> beats -> signals -> [plan] -> resolve -> assemble -> QC

The planner stage needs an LLM: with ANTHROPIC_API_KEY (or anthropic_key.txt)
it authors plan_llm.json automatically; otherwise it stops and tells you to
author plan_llm.json (Claude Code does this in-session), then re-run.

Run:  py -3.12 RUN_V2.py --name "Ryan Reynolds" --audio voiceover_x.mp3
      py -3.12 RUN_V2.py --resume        # continue after any stage artifact
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
ENV = {**os.environ, "CELEB_ROOT": str(ROOT), "PYTHONUTF8": "1",
       "PYTHONIOENCODING": "utf-8"}


def step(name, cmd, artifact=None, resume=False):
    if resume and artifact and Path(artifact).exists():
        print(f"[=] {name}: {Path(artifact).name} exists")
        return
    print(f"\n[*] {name}...")
    r = subprocess.run(cmd, env=ENV, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"[!] {name} failed (exit {r.returncode})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="Ryan Reynolds")
    ap.add_argument("--audio", default="")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--skip-qc-ocr", action="store_true")
    args = ap.parse_args()
    R = args.resume
    M = ROOT / "manifest"

    audio = args.audio or f"voiceover_{args.name.lower().replace(' ', '_')}.mp3"
    step("align", [PY, "pipeline/align.py", audio], M / "words.json", R)
    step("beats", [PY, "pipeline/beats.py"], M / "beats.json", R)
    step("signals", [PY, "pipeline/plan_treatments.py", "--signals"],
         M / "plan_signals.json", R)

    if not (M / "plan_llm.json").exists():
        key = os.environ.get("ANTHROPIC_API_KEY") or \
            (ROOT / "anthropic_key.txt").exists()
        if not key:
            print("\n[!] No planner LLM available. Author manifest/"
                  "plan_llm.json (see pipeline/plan_treatments.py docstring "
                  "+ manifest/plan_signals.json), then re-run with --resume.")
            return 2
        step("plan (LLM)", [PY, "pipeline/plan_llm_api.py"])
    step("validate plan", [PY, "pipeline/plan_treatments.py",
                           "--from", str(M / "plan_llm.json")],
         M / "plan.json", R)

    step("ingest gate", [PY, "pipeline/ingest_ocr.py"],
         ROOT / "library" / "shots.jsonl", R)
    step("embed index", [PY, "pipeline/embed_index.py", "--build"],
         ROOT / "library" / "shots_emb.npy", R)
    step("resolve assets", [PY, "pipeline/resolve_assets.py"],
         M / "assets.json", R)
    step("assemble", [PY, "pipeline/assemble.py"])

    cfg = json.loads((ROOT / "config.json").read_text()) \
        if (ROOT / "config.json").exists() else {}
    final = ROOT / "final_video" / cfg.get(
        "output", "RYAN_REYNOLDS_FINAL.mp4").replace(".mp4", "_V2.mp4")
    qc = [PY, "pipeline/qc.py", str(final), "--normalize"]
    if args.skip_qc_ocr:
        qc.append("--skip-ocr")
    step("QC gates", qc)
    print(f"\n[OK] SHIPPED: {final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
