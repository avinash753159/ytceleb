#!/usr/bin/env python3
"""Build CLIP_PLAN_RYAN.html - the per-line clip plan document (V5).
Format mirrors the operator's example doc: script line, then
'[clip title] - from [start] to [end] - link' underneath."""
import html
import json

beats = {b["beat_id"]: b for b in
         json.load(open("manifest/beats.json", encoding="utf-8"))["beats"]}
research = json.load(open("dossier_research.json", encoding="utf-8"))

MH = "https://www.youtube.com/watch?v=OAc4a3Pvojw"       # MH DP2 workout
BIO = ("https://images.squarespace-cdn.com/content/v1/68c946aa463c5e3b8140"
       "8c5e/1758021304629-VQO1EIVUINLFPQUC2F18/DonSaladino_Bio1000.jpg")

# beat -> [(clip title, range, url)]
M = {
 "b_000": [("Wade Wilson Emerges as a Mutant - Deadpool (2016) movie clip",
            "0:10 to 0:16", "https://www.youtube.com/watch?v=T9lXy9f89H0")],
 "b_001": [("Deadpool & Wolverine | Official Trailer (Marvel)",
            "0:58 to 1:04", "https://www.youtube.com/watch?v=73_1biulkYk")],
 "b_002": [("Ryan Reynolds' Deadpool 2 Workout | Men's Health",
            "0:36 to 0:50", MH)],
 "b_003": [("Get Superhero Jacked - Don Saladino (Escapist)",
            "5:56 to 6:04", "https://www.youtube.com/watch?v=zOLdxaUk-po")],
 "b_004": [("PERSON CARD: Don Saladino bio photo (donsaladino.com)",
            "image", BIO),
           ("bg: Men's Health DP2 - Saladino coaching", "0:36 to 0:44", MH)],
 "b_005": [("MH DP2 - Strength Conditioning chapter", "2:03 to 2:10", MH)],
 "b_006": [("Hollywood Superhero Trainer's Own Workout | Men's Health",
            "1:10 to 1:18", "https://www.youtube.com/watch?v=fAaageACI_0")],
 "b_007": [("CHICKEN, SWEET POTATO & BROCCOLI | Meal Prep 101",
            "0:22 to 0:30", "https://www.youtube.com/watch?v=4cS1cYalW2A")],
 "b_008": [("STILL: training-plan flat-lay (library, clean)", "image",
            "library still")],
 "b_009": [("Home-gym regular guy (library, judge-verified)", "clip",
            "library scene")],
 "b_010": [("STAT 6ft2 - bg: D&W Red Carpet Premiere LIVE (Marvel)",
            "66:30 to 66:38", "https://www.youtube.com/watch?v=1B4J7EO059U")],
 "b_011": [("Wade Wilson mutation chamber - physique shot", "1:05 to 1:12",
            "https://www.youtube.com/watch?v=T9lXy9f89H0")],
 "b_012": [("Deadpool | Official HD Trailer #1 (2016)", "0:35 to 0:42",
            "https://www.youtube.com/watch?v=Xithigfg7dA")],
 "b_013": [("PERSON CARD bg: Don Saladino interview", "7:51 to 8:00",
            "https://www.youtube.com/watch?v=Wpf7G7E1Jzw")],
 "b_014": [("MH DP2 - program overview", "1:20 to 1:28", MH)],
 "b_015": [("BLADE TRINITY Making Of - early-2000s Ryan on set",
            "18:20 to 18:28", "https://www.youtube.com/watch?v=QM9OeILgdsE")],
 "b_016": [("Blade: Trinity - Hannibal King interrogation (shirtless)",
            "0:40 to 0:48", "https://www.youtube.com/watch?v=4bKYXIMZey4")],
 "b_017": [("Green Lantern Trailer (WB) - shirtless wake scene",
            "0:19 to 0:24", "https://www.youtube.com/watch?v=7-GO9fo9DtM"),
           ("Deadpool (2016) trailer - suit reveal", "1:24 to 1:29",
            "https://www.youtube.com/watch?v=Xithigfg7dA")],
 "b_018": [("Deadpool & Wolverine | Official Teaser (Marvel)",
            "1:10 to 1:16", "https://www.youtube.com/watch?v=uJMCNJP2ipI")],
 "b_019": [("Ryan on his Green Lantern workout (2011 junket)",
            "0:05 to 0:13", "https://www.youtube.com/watch?v=ntfkrFfjFCU")],
 "b_020": [("Deadpool 2 | The Trailer - fight choreography", "1:30 to 1:36",
            "https://www.youtube.com/watch?v=D86RtevtfrA")],
 "b_021": [("Don Saladino 50-min Kettlebell Workout", "13:45 to 13:53",
            "https://www.youtube.com/watch?v=Bzfh23gYp8w")],
 "b_022": [("Blade Trinity Bloopers - Ryan between takes (2004)",
            "0:30 to 0:38", "https://www.youtube.com/watch?v=aMEayr4S1p4")],
 "b_023": [("LIST 7-day split - bg: MH DP2 gym wide", "2:03 to 2:10", MH)],
 "b_024": [("Saladino coaching bench (Big Three)", "5:00 to 5:08",
            "https://www.youtube.com/watch?v=E0lk4FFI5Fc")],
 "b_025": [("How To: Dumbbell Chest Press", "0:39 to 0:47",
            "https://www.youtube.com/watch?v=VmB1G1K7v94")],
 "b_026": [("LIST main lifts - bg: Incline Barbell Press", "0:21 to 0:29",
            "https://www.youtube.com/watch?v=jPLdzuHckI8")],
 "b_027": [("STAT sets/reps - bg: Cable Flys form", "0:12 to 0:20",
            "https://www.youtube.com/watch?v=JUDTGZh4rhg")],
 "b_028": [("LIST supersets - bg: Dips form fix", "1:28 to 1:36",
            "https://www.youtube.com/watch?v=yN6Q1UI_xkE")],
 "b_029": [("Dumbbell chest press - tension close-up", "1:00 to 1:07",
            "https://www.youtube.com/watch?v=VmB1G1K7v94")],
 "b_030": [("LIST finisher - bg: Assault Bike sprints", "0:30 to 0:38",
            "https://www.youtube.com/watch?v=VX_b3PXcH5I")],
 "b_031": [("Assault bike max effort", "0:45 to 0:52",
            "https://www.youtube.com/watch?v=VX_b3PXcH5I")],
 "b_032": [("MH DP2 - Pull Ups chapter (RYAN'S ACTUAL PROGRAM)",
            "3:05 to 3:13", MH)],
 "b_033": [("Bent Over Rows - 3 tips", "0:38 to 0:46",
            "https://www.youtube.com/watch?v=W-u5CyXXD8U")],
 "b_034": [("Rows continued - form emphasis", "1:00 to 1:07",
            "https://www.youtube.com/watch?v=W-u5CyXXD8U")],
 "b_035": [("Bicep curls: barbell + hammer", "0:23 to 0:31",
            "https://www.youtube.com/watch?v=sGqmHsV07lE")],
 "b_036": [("LIST core circuit - bg: Hanging Leg Raises", "0:50 to 0:58",
            "https://www.youtube.com/watch?v=QyVq5oUBpss")],
 "b_037": [("Functional core (same tutorial, later)", "1:10 to 1:18",
            "https://www.youtube.com/watch?v=QyVq5oUBpss")],
 "b_038": [("MH DP2 - Front Squat chapter (RYAN'S PROGRAM)",
            "2:26 to 2:34", MH),
           ("Squat technique deep-dive", "1:02 to 1:08",
            "https://www.youtube.com/watch?v=bEv6CCg2BC8")],
 "b_039": [("Walking Lunges tutorial", "0:29 to 0:37",
            "https://www.youtube.com/watch?v=Pbmj6xPo-Hw")],
 "b_040": [("STAT HIIT - bg: Assault bike intervals", "0:55 to 1:03",
            "https://www.youtube.com/watch?v=VX_b3PXcH5I")],
 "b_041": [("Lean training b-roll (library, judge-verified)", "clip",
            "library scene")],
 "b_042": [("Shoulder training technique", "0:35 to 0:43",
            "https://www.youtube.com/watch?v=_RlRDWO2jfg")],
 "b_043": [("LIST 3 heads - bg: lateral raises", "1:00 to 1:08",
            "https://www.youtube.com/watch?v=v_ZkxWzYnMc")],
 "b_044": [("Curl variations (preacher/concentration)", "0:50 to 0:58",
            "https://www.youtube.com/watch?v=sGqmHsV07lE")],
 "b_045": [("Saladino shoulder+arm workout", "1:00 to 1:08",
            "https://www.youtube.com/watch?v=wEPYlRWG9Y0")],
 "b_046": [("Lighter recovery pump (same workout)", "2:00 to 2:08",
            "https://www.youtube.com/watch?v=wEPYlRWG9Y0")],
 "b_047": [("Saladino Big Three - deadlift", "7:00 to 7:08",
            "https://www.youtube.com/watch?v=E0lk4FFI5Fc")],
 "b_048": [("Romanian Deadlifts (RDL)", "1:30 to 1:38",
            "https://www.youtube.com/watch?v=_oyxCn2iSjU")],
 "b_049": [("LIST circuit - bg: Saladino KB Swing (Do it Right)",
            "0:10 to 0:18", "https://www.youtube.com/watch?v=yGZIL8-o_zU")],
 "b_050": [("Box Jump tutorial", "4:16 to 4:24",
            "https://www.youtube.com/watch?v=v9cZQqGX1Xk")],
 "b_051": [("Boxer skip jump rope", "4:30 to 4:38",
            "https://www.youtube.com/watch?v=1-KvIEU03yc")],
 "b_052": [("LIST Saturday - bg: DP2 trailer fight beat", "1:52 to 2:00",
            "https://www.youtube.com/watch?v=D86RtevtfrA")],
 "b_053": [("D&W trailer action beat", "1:40 to 1:47",
            "https://www.youtube.com/watch?v=73_1biulkYk")],
 "b_054": [("Saladino 50-min KB full-body flow", "15:00 to 15:08",
            "https://www.youtube.com/watch?v=Bzfh23gYp8w")],
 "b_055": [("STAT steady-state - bg: outdoor cardio (library)", "clip",
            "library scene")],
 "b_056": [("Hiking/outdoor (library, judge-verified)", "clip",
            "library scene")],
 "b_057": [("MH DP2 - foam rolling (RYAN'S PROGRAM)", "0:55 to 1:03", MH)],
 "b_058": [("Fallon interview - relaxed Ryan", "0:20 to 0:28",
            "https://www.youtube.com/watch?v=5Sq0_MGriXc")],
 "b_059": [("Saladino: best work ethic answer", "0:10 to 0:18",
            "https://www.youtube.com/watch?v=gCav3Jkel5I")],
 "b_060": [("STAT sets - bg: MH own-workout", "2:00 to 2:08",
            "https://www.youtube.com/watch?v=fAaageACI_0")],
 "b_061": [("Big Three compound montage", "8:00 to 8:08",
            "https://www.youtube.com/watch?v=E0lk4FFI5Fc")],
 "b_062": [("Saladino programming talk", "3:00 to 3:08",
            "https://www.youtube.com/watch?v=wEPYlRWG9Y0")],
 "b_063": [("Meal prep spread overhead", "1:00 to 1:08",
            "https://www.youtube.com/watch?v=4cS1cYalW2A")],
 "b_064": [("STAT calories - bg: MH DP2 nutrition talk", "3:40 to 3:48",
            MH)],
 "b_065": [("STAT protein - bg: shake prep (library)", "clip",
            "library scene")],
 "b_066": [("STAT carbs - bg: salmon rice bowl", "1:09 to 1:17",
            "https://www.youtube.com/watch?v=YE2bMRNyGMs")],
 "b_067": [("STAT fats - bg: high-protein breakfasts", "0:30 to 0:38",
            "https://www.youtube.com/watch?v=vz1-i9QaNfg")],
 "b_068": [("Daily structure - meal containers", "1:40 to 1:48",
            "https://www.youtube.com/watch?v=4cS1cYalW2A")],
 "b_069": [("LIST pre-workout - bg: breakfast build", "0:08 to 0:16",
            "https://www.youtube.com/watch?v=vz1-i9QaNfg")],
 "b_070": [("Protein shake + banana (library)", "clip", "library scene")],
 "b_071": [("LIST Meal 1 - bg: eggs/oats (library)", "clip",
            "library scene")],
 "b_072": [("LIST Meal 2 - bg: chicken sweet potato broccoli",
            "0:45 to 0:53", "https://www.youtube.com/watch?v=4cS1cYalW2A")],
 "b_073": [("LIST Meal 3 - bg: salmon rice avocado", "1:50 to 1:58",
            "https://www.youtube.com/watch?v=YE2bMRNyGMs")],
 "b_074": [("Lean protein plate (library, clean)", "clip", "library scene")],
 "b_075": [("Greek yogurt snack (library still)", "image", "library still")],
 "b_076": [("Casein shake evening (library)", "clip", "library scene")],
 "b_077": [("LIST rules - bg: whole-food spread", "2:00 to 2:08",
            "https://www.youtube.com/watch?v=4cS1cYalW2A")],
 "b_078": [("LIST carb cycling - bg: MH DP2", "3:50 to 3:58", MH)],
 "b_079": [("Hydration (library, judge-verified)", "clip", "library scene")],
 "b_080": [("STAT cheat meals - bg: Fallon laughing", "1:10 to 1:18",
            "https://www.youtube.com/watch?v=5Sq0_MGriXc")],
 "b_081": [("Strategic fueling (library food)", "clip", "library scene")],
 "b_082": [("Assault bike sprint", "0:35 to 0:42",
            "https://www.youtube.com/watch?v=VX_b3PXcH5I")],
 "b_083": [("LIST his cardio - bg: KB swing how-to", "1:38 to 1:46",
            "https://www.youtube.com/watch?v=bDCeXbMJVNs")],
 "b_084": [("Jump rope boxer skip", "4:40 to 4:47",
            "https://www.youtube.com/watch?v=1-KvIEU03yc")],
 "b_085": [("STAT sleep - bg: calm recovery (library)", "clip",
            "library scene")],
 "b_086": [("Foam rolling / recovery (MH DP2)", "1:00 to 1:08", MH)],
 "b_087": [("Regular-person gym (library home gym)", "clip",
            "library scene")],
 "b_088": [("STAT 4-5 days - bg: home training (library)", "clip",
            "library scene")],
 "b_089": [("STAT 10k steps - bg: outdoor walk (library)", "clip",
            "library scene")],
 "b_090": [("STAT protein/lb - bg: meal prep", "2:20 to 2:28",
            "https://www.youtube.com/watch?v=4cS1cYalW2A")],
 "b_091": [("Burnout caution (library, judged)", "clip", "library scene")],
 "b_092": [("STAT 3000+ cal - bg: food spread", "1:20 to 1:28",
            "https://www.youtube.com/watch?v=YE2bMRNyGMs")],
 "b_093": [("Training log still (library)", "image", "library still")],
 "b_094": [("STAT 8 weeks - bg: MH DP2 finisher", "4:10 to 4:18", MH)],
 "b_095": [("D&W trailer hero shot", "2:20 to 2:27",
            "https://www.youtube.com/watch?v=73_1biulkYk")],
 "b_096": [("LIST the system - bg: Big Three montage", "9:00 to 9:06",
            "https://www.youtube.com/watch?v=E0lk4FFI5Fc")],
 "b_097": [("Ryan smiling premiere (D&W red carpet)", "70:00 to 70:07",
            "https://www.youtube.com/watch?v=1B4J7EO059U")],
 "b_098": [("Free Guy BIG GAINS BTS - muscle-double gag", "0:30 to 0:38",
            "https://www.youtube.com/watch?v=a_Swp1EJtmk")],
 "b_099": [("Subscribe end-card still (library)", "image", "library still")],
 "b_100": [("OUTRO MONTAGE: DP1 emerge / MH pull-ups / D&W trailer / "
            "Blade bloopers", "4 x ~4s callbacks", "(clips above)")],
}

SECTIONS = [
 ("HOOK", "b_000", "b_009"), ("CONTEXT & STATS", "b_010", "b_014"),
 ("CAREER TIMELINE (ERAS)", "b_015", "b_022"),
 ("MONDAY - CHEST & TRICEPS", "b_023", "b_031"),
 ("TUESDAY - BACK & BICEPS", "b_032", "b_037"),
 ("WEDNESDAY - LEGS + HIIT", "b_038", "b_041"),
 ("THURSDAY - SHOULDERS & ARMS", "b_042", "b_046"),
 ("FRIDAY - POSTERIOR CHAIN", "b_047", "b_050"),
 ("WEEKEND - CONDITIONING & REST", "b_051", "b_058"),
 ("TRAINING NOTES", "b_059", "b_062"), ("MACROS", "b_063", "b_068"),
 ("MEALS", "b_069", "b_081"), ("CARDIO & RECOVERY", "b_082", "b_086"),
 ("REALISTIC VERSION", "b_087", "b_094"), ("OUTRO", "b_095", "b_100"),
]

out = [
 "<h1>Train Like Ryan Reynolds - V5 Clip Plan</h1>",
 "<p><i>Every script line with its planned clip: [title] - from [start] "
 "to [end] - link. 'library' = our judge-verified clean pool. Timestamps "
 "are planned cuts; frame-exact trims happen during the watch pass. "
 "Edit anything inline - production follows THIS document.</i></p>",
 "<h2>Ryan's physique phases (era key)</h2><ul>"
 "<li><b>2004</b> - Blade Trinity (first transformation)</li>"
 "<li><b>2011</b> - Green Lantern</li>"
 "<li><b>2016</b> - Deadpool 1 (the shred)</li>"
 "<li><b>2018</b> - Deadpool 2 (Saladino program on film)</li>"
 "<li><b>2021</b> - Free Guy ('Dude' gag)</li>"
 "<li><b>2024</b> - Deadpool & Wolverine (leaner at 47)</li></ul>",
]
for name, a, b in SECTIONS:
    n0, n1 = int(a.split("_")[1]), int(b.split("_")[1])
    t0, t1 = beats[a]["start"], beats[b]["end"]
    out.append(f"<h2>{html.escape(name)} "
               f"[{int(t0//60)}:{int(t0%60):02d}-"
               f"{int(t1//60)}:{int(t1%60):02d}]</h2>")
    for i in range(n0, n1 + 1):
        bid = f"b_{i:03d}"
        txt = beats[bid]["text"] or "(music outro)"
        out.append(f"<p><i>&ldquo;{html.escape(txt)}&rdquo;</i></p>")
        for (title, ts, url) in M.get(bid, []):
            link = (f'<a href="{html.escape(url)}">{html.escape(url)}</a>'
                    if url.startswith("http") else html.escape(url))
            out.append(f'<p style="margin-left:24px">&#9654; '
                       f'<b>{html.escape(title)}</b> - from '
                       f'{html.escape(ts)} - {link}</p>')

out.append("<h2>ASSET BANKS (all 58 verified research entries)</h2>")
cur = None
for e in research:
    key = e.get("researcher", "other")
    if key != cur:
        out.append(f"<h3>{html.escape(key)}</h3>")
        cur = key
    link = (f'<a href="{html.escape(e["url"])}">{html.escape(e["url"])}</a>'
            if e["url"].startswith("http") else html.escape(e["url"]))
    out.append(f'<p>&bull; <b>{html.escape(e["title"][:90])}</b> '
               f'[{html.escape(e.get("era", ""))}] - '
               f'{html.escape(e["timestamp"][:40])} - {link}<br>'
               f'<span style="color:#555">'
               f'{html.escape(e["whats_on_screen"][:160])}</span></p>')

open("CLIP_PLAN_RYAN.html", "w", encoding="utf-8").write("\n".join(out))
print("HTML written; beats mapped:", len(M))
