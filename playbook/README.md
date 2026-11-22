# Celeb Workout Playbook (shared by both repos)

This `playbook/` folder and `growth/` are **identical** in
`avinash753159/celebworkout-editor-kit` and `avinash753159/ytceleb`. Edit one, copy to the other.

**Goal:** viewers LOVE the videos (they watch to the end, come back, subscribe), the channel ranks in
search, ad revenue goes up, and the numbers prove it gets better every week.

| File | What it is | Read it when |
|---|---|---|
| `../FINAL_ASSEMBLY_PROMPT.md` | The prompt to paste into Claude Code for the final cut | Every film, Step 3 |
| `EDITING_CRAFT.md` | Cut, music, transition, graphics and structure rules with numbers, plus the edit-quality eval | Before editing anything |
| `TOOLS.md` | Every tool: what it is good for, when to use it, when not to, CORE / ADD NOW / OPTIONAL / NOT RECOMMENDED | Before picking a tool |
| `GROWTH_SHORTS_EVALS.md` | Algorithm, ad revenue, monetization risk, Shorts system, Test & Compare, tracking, evals | Before titles, Shorts, upload |
| `CHANNEL_ANALYSIS.md` | What our own 260 videos say wins (titles, length, stars), competitors, keyword demand, next 15 films | Before choosing the next celebrity |
| `../growth/weekly_tracker.py` | Weekly snapshot + report that shows if we improved | Every week, same day |

---

## 1. The weekly flow (3 long-form + 15 to 21 Shorts per week)

| # | Step | Who | Output | Gate |
|---|---|---|---|---|
| 0 | **Pick the film** from `CHANNEL_ANALYSIS.md` section 9 (A-list action / superhero / peak-hype athlete, tied to a current role) | Owner + editor | `BRIEF.md` | Celebrity has search demand (autocomplete check) |
| 1 | **Research + harvest**: books, trainer interviews, long-form interviews (`SKILL.md` RUN IT steps 0-3) | Claude | `SOURCES.md`, transcripts, bites | Every source is real (publisher, outlet, date) |
| 2 | **Script around the bites** (hook in the first 30-60s, 6-8 chapters, `EDITING_CRAFT.md` section 6) | Claude + editor | `script.md`, `quotes.json` | Every claim maps to SOURCES.md |
| 3 | **Voice**: Kokoro `am_michael`, phoneme input for homographs and names | Claude | narration WAVs | Re-transcribe = script, word for word |
| 4 | **First cut**: picture, photos, cards, transitions, music bed (`EDITING_CRAFT.md` sections 3-5) | Claude + editor | first-cut MP4 | Edit-quality eval passes |
| 5 | **YouTube copyright pass**: upload UNLISTED, Studio > Copyright > Trim out claims, download edited version | Editor | edited MP4 + `YOUTUBE_CLAIMS.md` | Studio shows no claims |
| 6 | **Final assembly**: run `FINAL_ASSEMBLY_PROMPT.md` on the edited version; bridge every hole | Claude | final MP4 + CREDITS, SOURCES, VIDEO, QC_REPORT | QC gate (prompt section 7) passes |
| 7 | **Shorts**: 5-7 per film, 20-45s, native 9:16, cut from the final film (`GROWTH_SHORTS_EVALS.md` section 3) | Claude + editor | Shorts MP4s | Hook in first second, captions, loops, no licensed music |
| 8 | **Package**: title, description, chapters, tags, 3 thumbnails for Test & Compare (section 3 below) | Claude + editor | `METADATA.md` + thumbnails | Pre-publish evals (section 4 below) |
| 9 | **Human watch**: editor watches the whole film with sound | Editor | sign-off line in QC_REPORT | No sign-off, no publish |
| 10 | **Publish**: owner approves the unlisted video, then public; Shorts spread over the week with Related video = parent film | Owner | live video | |
| 11 | **Measure**: run `growth/weekly_tracker.py`, fill `growth/video_tags.csv`, write 3 lessons into `growth/LESSONS.md` | Claude | `WEEKLY_REPORT.md` | Committed to both repos |

---

## 2. What the data says (from `CHANNEL_ANALYSIS.md`, 2026-11-21)

- **The channel has been silent since 2026-09-12.** Uploads are the first lever: 3 a week, every week.
- **Star power wins.** A-list action and superhero leads and athletes at peak hype. Niche, B-list, "vs", listicle and clickbait titles got under 1,000 views in 2026.
- **Name the role:** titles naming the movie role get about 6x the views/day of titles that don't.
- **Winning title formula:** `Train Like <Role>: <Star>'s <Specific Plan>`, star name in the first 40 characters, 55-70 characters, no ALL CAPS, no "| Celeb Workout" suffix.
- **Length: 15-25 min is the house standard (owner decision 2026-11-21, final).** Our older data shows 8-10 min videos had the best median views; that was a different, thinner format. The tracker reports views and watch hours by length so the result stays visible.
- **Shorts:** none since July 2022. The closest competitor's Shorts use story hooks ("X is getting in trouble for being fat...") and get a 40k median; ours were generic "#short" clips.
- **Tags** are the same 13 generic tags on every video, and 90 videos carry a competitor's "men's health" tag. Tags count for little; the title and the first lines of the description do the work.

---

## 3. SEO metadata template (every long-form)

```
TITLE:  Train Like <Role>: <Star>'s <Movie> Workout & Diet          (55-70 chars, star in first 40)
DESC line 1 (shown in search, ~150 chars): How <Star> trained and ate to play <Role> in <Movie> (<year>): the weekly split, sets and reps, and the real diet.
DESC line 2: What you'll learn: 1) the training split 2) the diet and calories 3) how to copy it at home or in the gym.
CHAPTERS (5+, first one 0:00): 0:00 The transformation · 0:45 The trainer · ... · The diet · Your version
SOURCES: the books, interviews and articles the film cites (builds trust and originality)
MUSIC: every CC-BY credit from CREDITS.txt
Related: 2 playlist links (same franchise, same star)
#<StarName> #<Movie> #CelebrityWorkout                          (3 hashtags max)
TAGS: <star>, <star> workout, <star> diet, <role> workout, <movie> training, <star> transformation, celebrity workout
CAPTIONS: upload the SRT made from the script (better than auto-captions for search)
PINNED COMMENT: a question that invites replies ("Which part of <Star>'s routine would you try first?")
END SCREEN: next film in the same franchise playlist + subscribe
```

Thumbnails: 3 variants per film into YouTube **Test & Compare**. One variable per week across all 3 uploads
(e.g. face close-up vs before/after split). A style becomes the default after it wins 2 of 3 tests.

---

## 4. Evals

### 4a. Pre-publish (automatic, any fail blocks the upload)

| # | Check | Pass |
|---|---|---|
| 1 | Length | 15:00-25:00 |
| 2 | Hook (LLM judge on first 60s of script + frames) | score >= 8/10: a surprising true claim in the first 10s, a promise, an open loop |
| 3 | Fact sourcing | 100% of claims map to SOURCES.md |
| 4 | Bites | every bite ends on a full sentence; >= 200ms pre-roll and >= 500ms tail (`EDITING_CRAFT.md` section 7) |
| 5 | Narration | Whisper re-transcript matches script; no homograph or name errors |
| 6 | Audio | -14 LUFS +/- 1, true peak <= -1.5 dBTP, bed ducked under every word, track changes in pauses |
| 7 | Picture | no source under 640px tall, no static frame over 4s, no third-party watermark |
| 8 | Transitions + graphics | no hard cut on a chapter change; graphics land within 150ms of their word |
| 9 | Title rubric | formula match, star in first 40 chars, 55-70 chars, no ALL CAPS, no misleading claim |
| 10 | Thumbnail rubric | readable at 168x94, max 4 words, face visible, 3 variants ready |
| 11 | SEO | description line 1 has star + role + movie; 5+ chapters; SRT; 3 hashtags; playlists |
| 12 | Originality (monetization safety) | own thesis stated, own cards/charts, celebrity footage under ~30% of runtime, sources shown on screen |
| 13 | Human watch | editor signed off in QC_REPORT.md |

### 4b. Post-publish (from analytics at 48h, 7d, 28d)

| Metric | Target to start (replace with our 60th percentile after 6 weeks) |
|---|---|
| Views/day vs baseline (median of last 10 long-form) | >= 1.15 |
| CTR (impressions click-through) | 4-6% (third-party benchmark) |
| Average view percentage | >= 35% for 15-25 min; 30s retention >= 70% |
| Likes per 1k views | track trend week over week |
| Subs gained per 1k views | track trend week over week |
| RPM | track trend; health/fitness third-party range is $1.2-5 |
| Shorts viewed vs swiped away (Studio, manual) | >= 70% viewed |

---

## 5. The learning loop (how it gets better every week)

1. **Monday:** `python growth/weekly_tracker.py --token <token_youtube_celebworkout.pickle>` (public stats work with no token).
2. Fill `growth/video_tags.csv` for every new video: `id,title_formula,hook,thumb_style,celebrity_type,length_bucket`.
3. The report scores every new video against the baseline and every tag value against the others.
   A tag value with 3+ videos at median score >= 1.15 becomes the default. Keep 20% of slots for new ideas.
4. Open the retention graph of each new film, find the 3 steepest drops, write what was on screen in `growth/LESSONS.md`.
5. Feed `LESSONS.md` and the winning tags into next week's briefs and the script prompt.
6. Commit `growth/` to both repos. The history folder is the proof of improvement.

## Step 9b: Thumbnail (right after upload)
Run `growth/thumbnail/thumbnail.py auto` (see growth/thumbnail/README.md). Real celebrity frame + text, never AI imagery.
The old thumbnail is backed up first; `rollback` restores it. Eyeball the result before leaving it live.
