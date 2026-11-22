"""Celeb Workout weekly tracker: proves (or disproves) that the channel improves every week.

Run once a week (any day, same day each week):
    python growth/weekly_tracker.py
Optional (unlocks watch time, retention %, subs gained, revenue):
    --token <path to token_youtube_celebworkout.pickle>   (YouTube Analytics API, owner OAuth)

Writes:
    growth/history/<YYYY-MM-DD>.csv     one row per video (public stats + analytics if token)
    growth/WEEKLY_REPORT.md             this week vs last week, new uploads vs baseline, tag winners
Reads (optional):
    growth/video_tags.csv               your creative tags per video: id,title_formula,hook,thumb_style,celebrity_type,length_bucket

Public stats come from yt-dlp (no key). CTR/impressions need the YouTube Reporting API and
Shorts "viewed vs swiped away" is Studio-only; enter those in growth/manual_metrics.csv if wanted.
"""
import argparse, csv, datetime as dt, json, os, statistics, subprocess, sys

CHANNEL = "https://www.youtube.com/channel/UCSI7B4MrQaZTS4At_T3N-ow"
HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, "history")
FIELDS = ["id", "kind", "title", "upload_date", "duration_s", "views", "likes", "comments",
          "a_views_28d", "a_minutes_28d", "a_avg_view_pct_28d", "a_subs_gained_28d", "a_revenue_28d"]


def ytdlp_list(tab, kind):
    cmd = [sys.executable, "-m", "yt_dlp", "-j", "--skip-download", "--ignore-errors",
           "--sleep-requests", "1", "--extractor-args", "youtubetab:approximate_date",
           "--flat-playlist", f"{CHANNEL}/{tab}"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8").stdout
    rows = []
    for line in out.splitlines():
        try:
            j = json.loads(line)
        except ValueError:
            continue
        rows.append({"id": j.get("id"), "kind": kind, "title": j.get("title", ""),
                     "upload_date": j.get("upload_date") or "", "duration_s": j.get("duration") or "",
                     "views": j.get("view_count") or 0, "likes": j.get("like_count") or "",
                     "comments": j.get("comment_count") or ""})
    return rows


def add_analytics(rows, token_path):
    import pickle
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    with open(token_path, "rb") as f:
        creds = pickle.load(f)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    ya = build("youtubeAnalytics", "v2", credentials=creds)
    end = dt.date.today()
    start = end - dt.timedelta(days=28)
    metrics = "views,estimatedMinutesWatched,averageViewPercentage,subscribersGained"
    try:
        r = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end),
                               metrics=metrics + ",estimatedRevenue", dimensions="video",
                               sort="-views", maxResults=200).execute()
        money = True
    except Exception:
        r = ya.reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end),
                               metrics=metrics, dimensions="video", sort="-views", maxResults=200).execute()
        money = False
    by = {row[0]: row[1:] for row in r.get("rows", [])}
    for v in rows:
        a = by.get(v["id"])
        if a:
            v["a_views_28d"], v["a_minutes_28d"], v["a_avg_view_pct_28d"], v["a_subs_gained_28d"] = a[:4]
            v["a_revenue_28d"] = a[4] if money else ""
    return money


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def age_days(d, today):
    try:
        return max(1, (today - dt.datetime.strptime(d, "%Y%m%d").date()).days)
    except ValueError:
        return None


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default=os.environ.get("CW_YT_TOKEN", ""))
    a = ap.parse_args()
    os.makedirs(HIST, exist_ok=True)
    today = dt.date.today()
    rows = ytdlp_list("videos", "long") + ytdlp_list("shorts", "short")
    if not rows:
        sys.exit("ERROR: yt-dlp returned 0 videos (rate limit or yt-dlp outdated: pip install -U yt-dlp). Nothing written.")
    analytics = False
    if a.token and os.path.exists(a.token):
        try:
            add_analytics(rows, a.token)
            analytics = True
        except Exception as e:
            print("analytics skipped:", e)
    snap = os.path.join(HIST, f"{today}.csv")
    with open(snap, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    prev_files = sorted(p for p in os.listdir(HIST) if p.endswith(".csv") and p[:10] < str(today))
    prev = load(os.path.join(HIST, prev_files[-1])) if prev_files else {}
    prev_date = prev_files[-1][:10] if prev_files else None

    tot_views = sum(num(r["views"]) for r in rows)
    prev_views = sum(num(r["views"]) for r in prev.values()) if prev else None
    gained = {r["id"]: num(r["views"]) - num(prev[r["id"]]["views"]) for r in rows if r["id"] in prev}
    new = [r for r in rows if prev and r["id"] not in prev]

    # baseline = median views/day of the last 10 long-form uploads before this week
    longs = sorted([r for r in rows if r["kind"] == "long" and r["upload_date"]], key=lambda r: r["upload_date"])
    base_pool = [r for r in longs if r not in new][-10:]
    vpd = lambda r: num(r["views"]) / (age_days(r["upload_date"], today) or 1)
    baseline = statistics.median([vpd(r) for r in base_pool]) if base_pool else 0

    L = [f"# Weekly report {today}", ""]
    L.append(f"Compared with: {prev_date or 'nothing (first snapshot, this is the baseline)'}  ")
    L.append(f"Analytics API: {'yes' if analytics else 'no (public stats only)'}")
    L.append("")
    L.append("## Scorecard")
    L.append("| Metric | This week | Last snapshot | Change |")
    L.append("|---|---|---|---|")
    pv = f"{prev_views:,.0f}" if prev_views is not None else "-"
    dv = f"{tot_views - prev_views:+,.0f}" if prev_views is not None else "-"
    L.append(f"| Total channel views | {tot_views:,.0f} | {pv} | {dv} |")
    L.append(f"| Videos (long / shorts) | {sum(r['kind']=='long' for r in rows)} / {sum(r['kind']=='short' for r in rows)} | "
             f"{len(prev) if prev else '-'} | {len(new):+d} new |")
    if gained:
        L.append(f"| Views gained this period | {sum(gained.values()):,.0f} | | |")
    L.append(f"| Baseline: median views/day, last 10 long-form | {baseline:,.1f} | | |")
    if analytics:
        mins = sum(num(r.get("a_minutes_28d")) for r in rows)
        subs = sum(num(r.get("a_subs_gained_28d")) for r in rows)
        rev = sum(num(r.get("a_revenue_28d")) for r in rows)
        L.append(f"| Watch hours (28d) | {mins/60:,.0f} | | |")
        L.append(f"| Subs gained (28d, by video) | {subs:,.0f} | | |")
        if rev:
            L.append(f"| Est. revenue (28d) | ${rev:,.2f} | | |")
    L.append("")
    L.append("## New uploads vs baseline (target: score >= 1.15)")
    if new:
        L.append("| Video | Kind | Age (d) | Views | Views/day | Score vs baseline |")
        L.append("|---|---|---|---|---|---|")
        for r in sorted(new, key=vpd, reverse=True):
            s = vpd(r) / baseline if baseline else 0
            L.append(f"| {r['title'][:70]} | {r['kind']} | {age_days(r['upload_date'], today)} | {num(r['views']):,.0f} | {vpd(r):,.1f} | **{s:.2f}** |")
    else:
        L.append("No new uploads since the last snapshot. The channel cannot improve without uploads.")
    L.append("")
    if gained:
        L.append("## Top 10 movers this period")
        L.append("| Video | Views gained |")
        L.append("|---|---|")
        for vid, g in sorted(gained.items(), key=lambda kv: kv[1], reverse=True)[:10]:
            t = next(r["title"] for r in rows if r["id"] == vid)
            L.append(f"| {t[:80]} | {g:+,.0f} |")
        L.append("")
    tags_path = os.path.join(HERE, "video_tags.csv")
    if os.path.exists(tags_path):
        tags = load(tags_path)
        L.append("## Creative tags: which choices win (score = views/day vs baseline)")
        by_tag = {}
        for r in rows:
            t = tags.get(r["id"])
            if not t or not baseline:
                continue
            for k, v in t.items():
                if k in ("id", "title") or not v:
                    continue
                by_tag.setdefault((k, v), []).append(vpd(r) / baseline)
        L.append("| Tag | Value | Videos | Median score | Promote? |")
        L.append("|---|---|---|---|---|")
        for (k, v), ss in sorted(by_tag.items(), key=lambda kv: -statistics.median(kv[1])):
            m = statistics.median(ss)
            L.append(f"| {k} | {v} | {len(ss)} | {m:.2f} | {'YES (default it)' if len(ss) >= 3 and m >= 1.15 else ''} |")
        L.append("")
        L.append("Rule: a tag value becomes the default after 3+ videos with median score >= 1.15. Keep 20% of slots for new ideas.")
    out = os.path.join(HERE, "WEEKLY_REPORT.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("wrote", snap, "and", out)


if __name__ == "__main__":
    main()
