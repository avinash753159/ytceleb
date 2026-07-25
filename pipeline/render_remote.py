#!/usr/bin/env python3
"""render_remote.py - on-demand DigitalOcean render box.

Lifecycle (all subcommands, or 'run' for the whole thing):
  up        create CPU-Optimized droplet (c-16, ~$0.48/hr) with our SSH key
            + cloud-init that installs ffmpeg/node/python deps
  sync      push project (manifests, pipeline, graphics, needed media) via
            tar-over-ssh (incremental-ish: skips files already same size)
  render    run the assemble on the box
  pull      fetch the finished mp4
  destroy   ALWAYS destroy (also in finally of 'run') - a leaked droplet
            bills forever
  status    list our droplets

Token: do_token.txt in project root (gitignored).
Cost: the whole run bills only while the droplet exists (~$0.50-1.00/video).
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN = (ROOT / "do_token.txt").read_text().strip()
API = "https://api.digitalocean.com/v2"
TAG = "celebworkout-render"
SIZES = ["c-16", "c-8", "s-8vcpu-16gb-amd"]   # try best first
SIZE = SIZES[0]
REGION = "nyc1"
IMAGE = "ubuntu-24-04-x64"
KEY_NAME = "celebworkout-render-key"
SSH_KEY = Path.home() / ".ssh" / "celebworkout_render"

CLOUD_INIT = """#cloud-config
package_update: true
packages: [ffmpeg, python3-pip, rsync, libnss3, libdbus-1-3, libatk1.0-0t64,
           libatk-bridge2.0-0t64, libcups2t64, libgbm1, libasound2t64,
           libpangocairo-1.0-0, libxcomposite1, libxdamage1, libxrandr2,
           fontconfig]
runcmd:
  - curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  - apt-get install -y nodejs
  - echo ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true | debconf-set-selections
  - apt-get install -y ttf-mscorefonts-installer || true
  - fc-cache -f
  - pip3 install --break-system-packages yt-dlp pillow
  - mkdir -p /work
  - touch /ready
"""


def api(method, path, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Content-Type": "application/json"},
        data=json.dumps(body).encode() if body else None)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"DO API {e.code}: {e.read().decode()[:200]}")


def ensure_key():
    if not SSH_KEY.exists():
        subprocess.run(["ssh-keygen", "-t", "ed25519", "-N", "", "-f",
                        str(SSH_KEY)], check=True, capture_output=True)
    pub = (SSH_KEY.with_suffix(".pub")).read_text().strip()
    for k in api("GET", "/account/keys?per_page=200")["ssh_keys"]:
        if k["name"] == KEY_NAME:
            return k["id"]
    return api("POST", "/account/keys",
               {"name": KEY_NAME, "public_key": pub})["ssh_key"]["id"]


def our_droplets():
    return [d for d in api("GET", "/droplets?per_page=200")["droplets"]
            if TAG in d.get("tags", [])]


def up():
    key_id = ensure_key()
    existing = our_droplets()
    if existing:
        d = existing[0]
    else:
        d = None
        last = None
        for size in SIZES:
            try:
                d = api("POST", "/droplets", {
                    "name": "celebworkout-render", "region": REGION,
                    "size": size, "image": IMAGE, "ssh_keys": [key_id],
                    "tags": [TAG], "user_data": CLOUD_INIT})["droplet"]
                print(f"[UP] using size {size}")
                break
            except SystemExit as e:
                last = e
                if "restricted" not in str(e):
                    raise
                print(f"[skip] {size} restricted by account tier")
        if d is None:
            raise last
    for _ in range(60):
        d = api("GET", f"/droplets/{d['id']}")["droplet"]
        ips = [n["ip_address"] for n in d["networks"]["v4"]
               if n["type"] == "public"]
        if d["status"] == "active" and ips:
            print(f"[UP] droplet {d['id']} {ips[0]} ({SIZE})")
            return d["id"], ips[0]
        time.sleep(10)
    raise SystemExit("droplet never became active")


def ssh(ip, cmd, timeout=3600):
    return subprocess.run(
        ["ssh", "-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no",
         "-o", "UserKnownHostsFile=NUL", f"root@{ip}", cmd],
        timeout=timeout)


def wait_ready(ip):
    for _ in range(60):
        r = subprocess.run(
            ["ssh", "-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no",
             "-o", "UserKnownHostsFile=NUL", "-o", "ConnectTimeout=8",
             f"root@{ip}", "test -f /ready && echo READY"],
            capture_output=True, text=True)
        if "READY" in (r.stdout or ""):
            print("[READY] provisioning complete")
            return
        time.sleep(15)
    raise SystemExit("cloud-init never finished")


SYNC_DIRS = ["manifest", "pipeline", "graphics/src", "library/sites",
             "library/stills", "library/refs", "profiles"]
SYNC_GLOBS = ["graphics/package.json", "graphics/tsconfig.json",
              "graphics/remotion.config.ts", "config.json",
              "voiceover_*.mp3"]


def sync(ip, media_dirs=("dossier", "youtube_videos", "pexels_videos",
                         "candidates")):
    import tarfile
    import tempfile
    tf = Path(tempfile.mkdtemp()) / "proj.tar"
    with tarfile.open(tf, "w") as t:
        for d in SYNC_DIRS:
            p = ROOT / d
            if p.exists():
                t.add(p, arcname=d)
        for g in SYNC_GLOBS:
            for p in ROOT.glob(g):
                t.add(p, arcname=p.name)
        for d in media_dirs:
            p = ROOT / d
            if p.exists():
                t.add(p, arcname=d)
    print(f"[SYNC] uploading {tf.stat().st_size/1e9:.2f} GB ...")
    subprocess.run(["scp", "-i", str(SSH_KEY),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=NUL",
                    str(tf), f"root@{ip}:/work/proj.tar"], check=True)
    ssh(ip, "cd /work && tar xf proj.tar && rm proj.tar && "
            "cd graphics && npm install --no-audit --no-fund")
    print("[SYNC] done")


def render(ip):
    ssh(ip, "cd /work && CELEB_ROOT=/work PYTHONUTF8=1 "
            "python3 pipeline/v5_assemble.py", timeout=7200)


def pull(ip, name="RYAN_REYNOLDS_V5.mp4"):
    (ROOT / "final_video").mkdir(exist_ok=True)
    subprocess.run(["scp", "-i", str(SSH_KEY),
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=NUL",
                    f"root@{ip}:/work/final_video/{name}",
                    str(ROOT / "final_video" / name)], check=True)
    print(f"[PULL] final_video/{name}")


def destroy():
    for d in our_droplets():
        api("DELETE", f"/droplets/{d['id']}")
        print(f"[DESTROYED] {d['id']} - billing stopped")
    if not our_droplets():
        print("[OK] no render droplets exist")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        for d in our_droplets():
            print(d["id"], d["status"],
                  [n["ip_address"] for n in d["networks"]["v4"]])
        print("(none)" if not our_droplets() else "")
    elif cmd == "up":
        _, ip = up()
        wait_ready(ip)
    elif cmd == "destroy":
        destroy()
    elif cmd == "run":
        try:
            _, ip = up()
            wait_ready(ip)
            sync(ip)
            render(ip)
            pull(ip, sys.argv[2] if len(sys.argv) > 2
                 else "RYAN_REYNOLDS_V5.mp4")
        finally:
            destroy()          # never leak a paid droplet
    else:
        print("usage: render_remote.py status|up|destroy|run [outname]")


if __name__ == "__main__":
    main()
