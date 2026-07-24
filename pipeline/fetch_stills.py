#!/usr/bin/env python3
"""
fetch_stills.py - licensed still images for still_pushin / person_card /
split_compare beats.

Sources, in order: Wikimedia Commons (one-round-trip generator=search with
iiurlwidth=1920 pre-scaled thumbs), then Openverse, then the Pexels photo API.
Patterns follow the verified reference implementation (docs/RESEARCH_NOTES.md):
polite UA with contact, per-source delays, exponential backoff, 429 honors
Retry-After once, 4xx gives up, deny-by-default licensing, Referer +
thumburl fallback for Commons hotlink 403s.

Every download is re-gated: OCR text check (same thresholds as ingest) and
min width 1920 (upscale path handles smaller). Results cached by query hash.
"""
import hashlib
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(os.environ.get("CELEB_ROOT", "")) if os.environ.get("CELEB_ROOT") \
    else Path(__file__).resolve().parent.parent
STILLS = ROOT / "library" / "stills"
CACHE = ROOT / "library" / "stills_cache.json"

UA = {"User-Agent": "ytceleb/1.0 (+https://github.com/avinash753159/ytceleb)",
      "Accept": "application/json"}
ALLOWED = {"cc0", "pdm", "pd", "publicdomain", "by", "cc-by", "by-sa",
           "cc-by-sa", "cc-by-4.0", "cc-by-sa-4.0", "cc-by-3.0",
           "cc-by-sa-3.0", "cc-by-2.0", "cc-by-sa-2.0", "attribution"}
DENIED_SUB = ("-nc", "-nd", "copyright", "fair use", "all rights")

PEXELS_KEY = os.environ.get(
    "PEXELS_API_KEY",
    "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8")


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403, 404):
                return None
            if e.code == 429 and attempt < 1:
                ra = e.headers.get("Retry-After")
                time.sleep(float(ra) if ra else 2.0)
                continue
            time.sleep(1.0 * (2 ** attempt))
        except Exception:
            time.sleep(1.0 * (2 ** attempt))
    return None


def license_ok(lic):
    l = (lic or "").lower().strip()
    if any(d in l for d in DENIED_SUB):
        return False
    return any(a in l for a in ALLOWED)


def search_wikimedia(query, limit=8):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": "6",
        "gsrlimit": min(limit, 50), "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime", "iiurlwidth": 1920,
        "iiextmetadatafilter": "License|LicenseShortName|UsageTerms|Artist",
    }
    raw = _get("https://commons.wikimedia.org/w/api.php?"
               + urllib.parse.urlencode(params))
    time.sleep(0.3)
    if not raw:
        return []
    out = []
    pages = (json.loads(raw).get("query") or {}).get("pages", {})
    for p in pages.values():
        for info in p.get("imageinfo", []):
            meta = info.get("extmetadata", {})
            lic = (meta.get("LicenseShortName", {}) or {}).get("value") \
                or (meta.get("License", {}) or {}).get("value") or ""
            if not license_ok(lic):
                continue
            out.append({
                "url": info.get("url"),
                "thumb": info.get("thumburl") or info.get("url"),
                "width": info.get("width", 0),
                "page": info.get("descriptionurl",
                                 "https://commons.wikimedia.org/"),
                "license": lic, "source": "wikimedia",
                "title": p.get("title", ""),
            })
    return out


def search_openverse(query, limit=8):
    q = " ".join(w for w in query.split() if w.isalpha() and len(w) >= 3)
    if len(q) < 3:
        return []
    params = {"q": q, "page_size": min(limit, 20), "mature": "false",
              "license_type": "commercial,modification"}
    raw = _get("https://api.openverse.engineering/v1/images/?"
               + urllib.parse.urlencode(params))
    time.sleep(0.6)
    if not raw:
        return []
    out = []
    for r in json.loads(raw).get("results", []):
        if not license_ok(r.get("license", "")):
            continue
        out.append({"url": r.get("url"), "thumb": r.get("url"),
                    "width": r.get("width") or 0,
                    "page": r.get("foreign_landing_url") or "",
                    "license": r.get("license"), "source": "openverse",
                    "title": r.get("title") or ""})
    return out


def search_pexels(query, limit=8):
    raw = _get("https://api.pexels.com/v1/search?"
               + urllib.parse.urlencode({"query": query,
                                         "per_page": min(limit, 15),
                                         "orientation": "landscape"}),
               headers={"Authorization": PEXELS_KEY})
    time.sleep(0.4)
    if not raw:
        return []
    out = []
    for p in json.loads(raw).get("photos", []):
        src = p.get("src", {})
        out.append({"url": src.get("original") or src.get("large2x"),
                    "thumb": src.get("large2x") or src.get("original"),
                    "width": p.get("width", 0),
                    "page": p.get("url", ""), "license": "pexels",
                    "source": "pexels",
                    "title": p.get("alt") or ""})
    return out


def download(cand, dest):
    """Commons hotlink-safe download with thumburl fallback."""
    hdrs = {"Accept": "*/*", "Referer": cand.get("page")
            or "https://commons.wikimedia.org/"}
    for url in (cand.get("url"), cand.get("thumb")):
        if not url:
            continue
        raw = _get(url, headers=hdrs, timeout=60)
        if raw and len(raw) > 20_000:
            dest.write_bytes(raw)
            return True
    return False


def ocr_reject(path):
    """Same gate as ingest: burned text in top/bottom bands -> reject."""
    try:
        from rapidocr_onnxruntime import RapidOCR
        import cv2
        img = cv2.imread(str(path))
        if img is None:
            return True
        H, W = img.shape[:2]
        ocr = RapidOCR()
        for band in (img[int(H * 0.70):, :], img[:int(H * 0.15), :]):
            res, _ = ocr(band)
            for box, text, conf in (res or []):
                if float(conf) <= 0.5:
                    continue
                xs = [pt[0] for pt in box]
                ys = [pt[1] for pt in box]
                if (max(xs) - min(xs)) * (max(ys) - min(ys)) / (H * W) > 0.004:
                    return True
        return False
    except Exception:
        return False        # OCR unavailable: don't block, ingest QC catches it


def upscale_if_needed(path, min_w=1920, max_w=2560):
    """Normalize width into [min_w, max_w]: upscale small stills
    (Real-ESRGAN, else lanczos), downscale megapixel monsters - headless
    Chrome fails to load ~60MP images during Remotion renders."""
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width", "-of", "csv=p=0",
                        str(path)], capture_output=True, text=True)
    try:
        w = int(r.stdout.strip().split("\n")[0])
    except Exception:
        return False
    if w > max_w:
        dn = path.with_name(path.stem + "_dn" + path.suffix)
        subprocess.run(["ffmpeg", "-i", str(path),
                        "-vf", f"scale={max_w}:-2:flags=lanczos",
                        "-q:v", "2", "-y", str(dn)], capture_output=True)
        if dn.exists():
            dn.replace(path)
            return True
        return False
    if w >= min_w:
        return True
    up = path.with_name(path.stem + "_up" + path.suffix)
    try:
        from realesrgan_ncnn_py import Realesrgan
        rgan = Realesrgan(gpuid=-1)
        from PIL import Image
        img = Image.open(path).convert("RGB")
        rgan.process_pil(img).save(up)
    except Exception:
        subprocess.run(["ffmpeg", "-i", str(path),
                        "-vf", f"scale={min_w}:-2:flags=lanczos",
                        "-q:v", "2", "-y", str(up)], capture_output=True)
    if up.exists():
        up.replace(path)
        return True
    return False


def fetch_still(query, name_hint="", prefer_person=False):
    """Main entry: returns dict(path, license, source, page) or None."""
    STILLS.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    key = hashlib.sha256(query.encode()).hexdigest()[:16]
    if key in cache and Path(cache[key]["path"]).exists():
        return cache[key]

    cands = search_wikimedia(query) + search_openverse(query)
    if not prefer_person:              # pexels has no celebrities, only stock
        cands += search_pexels(query)
    cands.sort(key=lambda c: -(c["width"] or 0))

    slug = re.sub(r"[^\w]+", "_", (name_hint or query))[:40]
    for i, c in enumerate(cands[:10]):
        dest = STILLS / f"{slug}_{key}_{i}.jpg"
        if not download(c, dest):
            continue
        if ocr_reject(dest):
            dest.unlink(missing_ok=True)
            continue
        if not upscale_if_needed(dest):
            dest.unlink(missing_ok=True)
            continue
        rec = {"path": str(dest), "license": c["license"],
               "source": c["source"], "page": c["page"], "title": c["title"]}
        cache[key] = rec
        CACHE.write_text(json.dumps(cache, indent=0))
        return rec
    return None


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "Ryan Reynolds premiere"
    print(json.dumps(fetch_still(q), indent=2))
