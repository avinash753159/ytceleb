#!/usr/bin/env python3
"""Build V9 on a throwaway DigitalOcean box, because this laptop has no disk.

WHY NOT render_remote.py AS IT STANDS
-------------------------------------
1. Its sync() builds the whole tar in a temp directory FIRST and then scps it.
   That needs as much free local disk as the payload - about 11.5 GB - and
   this machine has 1.6 GB. Here the tar is streamed straight into ssh, so
   nothing large is ever written locally.

2. It uploads whole directories. library/broll7 alone is 8.5 GB, most of which
   is clips the screening pass REJECTED. Only files the allow-list actually
   references are sent, so the reject pile never crosses the wire.

WHY THE RENDER IS DETACHED, AND WHY SYNC RESUMES
------------------------------------------------
The first attempt died with the local process: the upload was killed at
700/1071 files and, because the kill skipped the `finally`, it left a live
droplet billing with nothing to show. Two consequences, both fixed here:

* `render` starts under nohup on the box and returns immediately. Losing the
  laptop, the shell or the session no longer loses the render.
* `sync` asks the box what it already has and sends only what is missing or
  the wrong size, so a resumed run costs minutes, not another 11.5 GB.

Subcommands, so a killed step never means starting over:
    up | sync | start | wait | pull | destroy | run

DESTROY IS STILL YOUR JOB IF A STEP DIES. `run` destroys in a finally, but a
SIGKILL cannot be caught by anything - check `render_remote.py status` after
any abnormal exit. A leaked box bills until someone notices.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import render_remote as R                                        # noqa: E402

OUT_NAME = "THE_DISEASE_THAT_BUILT_MRBEAST_V9.mp4"
LOG = "/work/v9render.log"

DIRS = ["manifest", "pipeline", "work/post_cards", "work/docs_v8",
        "work/cards", "work/jimmy_pool2", "work/bite_windows",
        "dossier/mrbeast/medical", "dossier/mrbeast/primary",
        "dossier/mrbeast/documents", "dossier/mrbeast/owner_links",
        "graphics/src"]
FILES = ["config.json",
         "final_video/mrbeast_audio_v6/MRBEAST_V6_STORY_MASTER.wav"]


def payload() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    def add(p: Path, arc: str):
        if p.exists() and p.is_file() and p not in seen:
            seen.add(p)
            items.append((p, arc))

    for d in DIRS:
        base = ROOT / d
        if base.exists():
            for p in base.rglob("*"):
                # NEVER ship __pycache__. Windows writes .pyc files with
                # timestamps ahead of the box's clock, so CPython treated the
                # cached bytecode as current and ran an OLD plan: the build
                # failed on "span 15 slot 1 is 7.30s" long after that had been
                # fixed, because the fix was in the .py and the box was
                # reading the .pyc.
                if p.is_file() and "__pycache__" not in p.parts:
                    add(p, f"{d}/{p.relative_to(base).as_posix()}")
    for f in FILES:
        add(ROOT / f, f)

    allow = json.loads((ROOT / "manifest/broll_allow.json")
                       .read_text(encoding="utf-8"))
    for group in allow.values():
        for it in group:
            add(ROOT / it["file"], it["file"])

    src = ROOT / "dossier/mrbeast/sources"
    if src.exists():
        for p in src.glob("*.mp4"):
            add(p, f"dossier/mrbeast/sources/{p.name}")
    return items


def ip_of() -> str:
    ds = R.our_droplets()
    if not ds:
        raise SystemExit("no render droplet - run `up` first")
    return [n["ip_address"] for n in ds[0]["networks"]["v4"]
            if n["type"] == "public"][0]


def _ssh_out(ip: str, cmd: str) -> str:
    return subprocess.run(
        ["ssh", "-i", str(R.SSH_KEY), "-o", "StrictHostKeyChecking=no",
         "-o", "UserKnownHostsFile=NUL", f"root@{ip}", cmd],
        capture_output=True, text=True, timeout=600).stdout


def remote_sizes(ip: str) -> dict:
    out = _ssh_out(ip, "cd /work 2>/dev/null && find . -type f "
                       "-printf '%s %P\\n' || true")
    sizes = {}
    for line in out.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            sizes[parts[1]] = int(parts[0])
    return sizes


def sync(ip: str) -> None:
    items = payload()
    have = remote_sizes(ip)
    todo = [(p, a) for p, a in items
            if have.get(a) != p.stat().st_size]
    skipped = len(items) - len(todo)
    total = sum(p.stat().st_size for p, _ in todo)
    print(f"[SYNC] {len(items)} files in payload, {skipped} already on the "
          f"box, sending {len(todo)} ({total/1e9:.2f} GB)", flush=True)
    if not todo:
        print("[SYNC] nothing to do")
        return

    R.ssh(ip, "mkdir -p /work")
    proc = subprocess.Popen(
        ["ssh", "-i", str(R.SSH_KEY), "-o", "StrictHostKeyChecking=no",
         "-o", "UserKnownHostsFile=NUL", f"root@{ip}", "tar x -C /work"],
        stdin=subprocess.PIPE)
    sent = 0
    with tarfile.open(fileobj=proc.stdin, mode="w|") as tar:
        for i, (p, arc) in enumerate(todo, 1):
            tar.add(p, arcname=arc)
            sent += p.stat().st_size
            if i % 50 == 0 or sent > 1e9 and i % 10 == 0:
                print(f"  {i}/{len(todo)}  {sent/1e9:.2f} GB", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit("tar stream failed - rerun `sync`, it resumes")
    print("[SYNC] done", flush=True)


def start(ip: str) -> None:
    """Detached, so losing this shell does not lose the render."""
    R.ssh(ip, "pip3 install --break-system-packages -q numpy pillow "
              "2>/dev/null || pip3 install -q numpy pillow || true")
    R.ssh(ip, f"cd /work && rm -f {LOG} DONE FAILED && "
              f"nohup sh -c 'CELEB_ROOT=/work PYTHONUTF8=1 BUILD_SUFFIX=V9 "
              f"python3 pipeline/mrbeast_picture_v9.py > {LOG} 2>&1 && "
              f"touch /work/DONE || touch /work/FAILED' "
              f"> /dev/null 2>&1 &")
    print(f"[START] render detached; log at {LOG}")


def wait(ip: str) -> bool:
    state = _ssh_out(ip, "ls /work/DONE /work/FAILED 2>/dev/null; "
                         f"tail -4 {LOG} 2>/dev/null")
    print(state.strip() or "(no output yet)")
    return "/work/DONE" in state


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "up":
        _, ip = R.up()
        R.wait_ready(ip)
    elif cmd == "sync":
        sync(ip_of())
    elif cmd == "start":
        start(ip_of())
    elif cmd == "wait":
        return 0 if wait(ip_of()) else 2
    elif cmd == "pull":
        R.pull(ip_of(), OUT_NAME)
    elif cmd == "destroy":
        R.destroy()
    elif cmd == "run":
        try:
            _, ip = R.up()
            R.wait_ready(ip)
            sync(ip)
            start(ip)
        except Exception:
            R.destroy()
            raise
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
