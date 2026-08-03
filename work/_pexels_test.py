"""Diagnose the Pexels 403: is the key dead, or was the request wrong?"""
import json
import urllib.error
import urllib.parse
import urllib.request

KEY = "OqvEHNfwvEjuuvosrZXe5keUApJkPuapj79araQgOWtaxZ1xRY9DRsC8"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def attempt(label, url, headers):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read().decode("utf-8"))
            n = len(d.get("videos", d.get("photos", [])))
            print(f"OK    {label}: {r.status}, {n} results")
            return d
    except urllib.error.HTTPError as e:
        body = e.read()[:220].decode("utf-8", "replace")
        print(f"FAIL  {label}: HTTP {e.code} — {body}")
    except Exception as e:  # noqa: BLE001
        print(f"FAIL  {label}: {type(e).__name__}: {e}")
    return None


base = "https://api.pexels.com/videos/search?"
q = urllib.parse.urlencode({"query": "gym", "per_page": 2})

attempt("videos, key only", base + q, {"Authorization": KEY})
attempt("videos, key + UA", base + q,
        {"Authorization": KEY, "User-Agent": UA})
attempt("videos, Bearer", base + q,
        {"Authorization": f"Bearer {KEY}", "User-Agent": UA})
attempt("photos endpoint",
        "https://api.pexels.com/v1/search?" + q,
        {"Authorization": KEY, "User-Agent": UA})
attempt("videos + Accept", base + q,
        {"Authorization": KEY, "User-Agent": UA,
         "Accept": "application/json"})
