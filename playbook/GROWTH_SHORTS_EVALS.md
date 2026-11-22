# Celeb Workout: Growth, Shorts and Evals System

Channel: https://www.youtube.com/@CelebWorkout · Format: 15-25 min celebrity workout and diet documentaries · Output: 3 long-form videos a week (AI pipeline plus a human editor)
Researched 2026-11-21. Labels used throughout: **[OFFICIAL]** = YouTube or Google documentation · **[BENCH]** = a published third-party benchmark · **[GUESS]** = my estimate, to be replaced by the channel's own baseline after about 6 weeks.

---

## 0. TL;DR (the system in 10 lines)

1. **Optimize for satisfied watch time, not clicks.** YouTube ranks using satisfaction surveys, likes and dislikes, and how well a video "interested and satisfied similar viewers". Test & Compare also picks winners by **watch-time share**, not CTR.
2. **Monetization risk is the biggest threat.** An AI-narrated celebrity compilation is the exact profile of the July-2025 "inauthentic content" rule. Every video must visibly carry original analysis: a sourced claim ledger, original graphics, the editor's structure, and a different arc each time.
3. **Long-form makes the money; Shorts bring in subscribers.** Make **5-7 Shorts per long-form** (15-21 a week). Give each one a single payoff, a 1-second hook, burned-in captions and a "Related video" link to its parent.
4. **Mid-rolls:** turn on auto placement plus manual breaks at chapter boundaries. Use 3-5 breaks per 15-25 min video, the first one after the 30%-retention cliff (about 3-4 min) **[GUESS]**.
5. **SEO order:** title, then description (the first 2 lines plus chapters), then an accurate transcript (upload your own SRT from the script), then playlists by celebrity type, then a pinned comment. Tags are low value **[OFFICIAL]**.
6. **Tracking:** use YouTube Analytics API (OAuth) for retention, revenue and traffic. Use the Reporting API `channel_reach_basic_a1` for impressions and CTR (the only API route to CTR). Use Data API v3 for public counts. "Viewed vs swiped" is **Studio-only**, so paste it in by hand or scrape it.
7. **Weekly scorecard plus learning loop:** score each video against the channel's rolling median at the same age (lift = video / baseline). Tag every video with its creative variables. Promote a variable to "default" only after 3 or more videos with lift of at least 1.15.
8. **Pre-publish gate:** 12 automatic checks; any red blocks the upload. **Post-publish gate:** 48h, 7d and 28d checks against channel baseline.

---

## 1. How ranking works now (2025-2026)

**Long-form (Home and Suggested):**
- The system "learns from signals". **Viewer satisfaction surveys** let it weigh satisfaction beyond watch time **[OFFICIAL]**. https://support.google.com/youtube/answer/16089387
- Todd Beaupré (YouTube Discovery): "we look at things like likes, dislikes, these survey responses… a variety of different signals to get at this satisfaction". The goal is long-term viewer satisfaction. https://www.searchenginejournal.com/how-youtubes-recommendation-system-works-in-2025/538379/
- Discovery is based on "how well your video has interested and satisfied similar viewers". Likes and dislikes are "some of the hundreds of signals" **[OFFICIAL]**. https://support.google.com/youtube/answer/141805
- Returning viewers make the system "more likely to suggest more of your videos" **[OFFICIAL]**. https://support.google.com/youtube/answer/10246996 (vidIQ reports that Studio moved to *casual* and *regular* viewer segments in July 2025: https://vidiq.com/blog/post/track-returning-viewers-on-youtube/)
- **What this means for us:** CTR only gets the click. AVD %, survey satisfaction and repeat viewing decide reach. Clickbait that under-delivers costs us twice, once in retention and once in survey scores.

**Shorts:**
- Since 31 March 2025, a public Shorts "view" counts every play or replay. **Engaged views** (the older definition) still drive YPP eligibility and revenue **[OFFICIAL]**. https://techcrunch.com/2025/03/26/youtube-is-changing-how-youtube-shorts-views-are-counted · https://support.google.com/youtube/answer/2991785
- Studio has a **Viewed vs Swiped away** chart under Analytics → Content → Shorts. It is the main Shorts diagnostic. Example channel: 26.6% viewed / 73.4% swiped. https://www.socialmediaexaminer.com/?p=251758
- Shorts can run up to 3 minutes. No official length is "rewarded"; retention is what counts. Third-party completion figures vary widely **[BENCH, weak]**. https://www.bytecap.io/research/youtube-shorts-retention-benchmarks

**Search and SEO:**
- Search ranks partly on how well the **title, description and video content** match the query **[OFFICIAL]**.
- **Tags play a "minimal role"** except for misspellings. Title, thumbnail and description matter more **[OFFICIAL]**. https://support.google.com/youtube/answer/146402
- **Chapters:** add manual timestamps. They override auto-chapters and can surface as "key moments" in Google search **[BENCH]**.
- **Captions:** upload the script-derived SRT (the exact words, so celebrity and exercise names are spelled correctly). This fixes the transcript YouTube indexes. It is cheap and has no downside.
- **Playlists:** group by celebrity type ("Marvel Actors", "Athletes", "Musicians") and by intent ("What X Eats in a Day"). Playlists add a session and Suggested surface.
- **Pinned comment:** link the source list plus a question that invites replies ("Which routine should we break down next?").

**Search-friendly title pattern:** `[Celebrity] [Workout/Diet] [specific hook]`, for example "Henry Cavill's Superman Workout: The 4-Phase Plan That Added 20 lb". Put the celebrity name in the first 40 characters, because titles get truncated on mobile.

---

## 2. Ad revenue

### 2.1 Eligibility (YPP) **[OFFICIAL]**, https://support.google.com/youtube/answer/13429240
| Tier | Subs | Plus one of | Also |
|---|---|---|---|
| Fan funding (expanded YPP) | 500 | 3,000 public watch hours in 12 months **or** 3M Shorts views in 90 days | 3 uploads in 90 days |
| Ad revenue share | 1,000 | 4,000 public watch hours in 12 months **or** 10M Shorts views in 90 days | policy review |

- Shorts revenue: ad revenue from the Shorts feed goes into a Creator Pool and **creators keep 45%** of their allocation. Music use shrinks the pool share **[OFFICIAL]**. https://support.google.com/youtube/answer/12504220 Rule: **no licensed music in Shorts**. Use our own or royalty-free beds only, otherwise revenue is diluted.

### 2.2 Mid-rolls
- Mid-rolls are available on monetized videos of **8 minutes or more**. Auto placement is the default and picks "natural breaks". YouTube says auto breaks are "2x less interruptive" than manual ones. Since 2025 you can run **manual and auto together**, and Studio flags "interruptive" manual slots **[OFFICIAL]**. https://support.google.com/youtube/answer/6175006 · https://blog.youtube/creator-and-artist-stories/mid-roll-ads-updates-explained/
- **Spacing plan for 15-25 min [GUESS, to be tuned with the retention data in §5]:**
  - No break before the hook payoff and the first chapter end, roughly 3-4 min in, after the steep early drop.
  - Then one break at each chapter boundary, about every 4-5 min. That gives 3 breaks at 15 min and 4-5 at 25 min.
  - The script should create the breaks deliberately. End each chapter with a mini-cliffhanger ("…but the diet is where it gets weird"), then cut to a beat of silence or a title card. That is a natural break for both the auto detector and the viewer.
  - Never break mid-sentence, during a transformation reveal, or within 60 s of the end.
  - Test it: alternate 3 and 5 breaks on comparable videos and compare RPM against the drop in `audienceWatchRatio` around each break.

### 2.3 RPM drivers (fitness, health and celebrity)
- Published RPM ranges for health and fitness conflict: about **$2-5** (vidIQ), a $1.23 median for "Health & Sport" (AIR, 300 channels, 2026), and $8-15 in some lists **[BENCH, low agreement]**. https://vidiq.com/blog/post/youtube-rpm · https://air.io/en/air-data-findings/how-much-does-youtube-really-pay-in-2026-real-rpm-data-from-300-channels
- **Levers we control:**
  1. **US/UK/CA/AU audience share.** English narration plus US celebrities already helps.
  2. **Length of 15-25 min plus 3-5 mid-rolls** gives more ad impressions per view.
  3. **Advertiser-friendly framing.** Steroid, PED, eating-disorder or extreme-cut topics risk limited ads (yellow icon). Frame them as health or science, keep the language clean, and avoid shocking body imagery in the first 30 s.
  4. **Seasonality.** January (resolutions) and Q4 CPMs are higher, so stockpile the strongest videos for late December and early January.
  5. **Diet and supplement topics** pull higher-CPM health advertisers.

### 2.4 Inauthentic-content and reused-content risk (the critical section)
- On **15 July 2025** YouTube renamed "repetitious content" to **"inauthentic content"** and said it covers "mass-produced and repetitious" content. YouTube called it a minor update to an existing rule, with enforcement increasing; channels that persist can be **removed from YPP**. https://techcrunch.com/2025/07/09/youtube-prepares-crackdown-on-mass-produced-and-repetitive-videos-as-concern-over-ai-slop-grows · https://www.searchenginejournal.com/youtube-monetization-update-spam-not-reaction-channels/550755/
- **Our risk profile:** high. We have TTS narration, a templated structure, a repeated thumbnail style, celebrity footage we did not shoot, and 3 videos a week.
- **Synthetic voice:** Kokoro is a generic, non-cloned voice, so it needs **no disclosure**. Cloning a real person's voice, or realistic fake scenes of a celebrity, **does need disclosure** **[OFFICIAL]**. https://support.google.com/youtube/answer/14328491 Rule: never generate realistic celebrity likeness or voice.
- **Make originality visible (each item is a pre-publish eval in §6):**
  1. **An original thesis per video** (for example "Why Cavill's cut failed the first time"), not just a recap.
  2. **A claim ledger.** Every factual claim links to a source (interview, trainer quote, article). Show citations on screen.
  3. **Original analysis assets:** macro breakdown charts, a weekly split table, cost-of-diet math, a "can a normal person do this" scaled version. These are HyperFrames/Remotion graphics we create.
  4. **Celebrity footage under 30% of runtime**, short clips (about 5 s or less each), each one being commented on. This is a transformative-use posture and also reduces Content ID claims, which redirect revenue.
  5. **Rotate the structure.** Use 4 or more arc templates in rotation (chronological, myth-busting, versus-comparison, "I tried it", ranking), so videos are not templated clones.
  6. **Human editor fingerprint.** The editor chooses pacing and the B-roll story and adds at least 1 original segment.
  7. Optional but strong: **a recurring human element** (a coach or host cameo, or a real person trying the workout).

---

## 3. Shorts strategy (the subscriber engine)

### 3.1 Formats ranked for this niche **[GUESS, based on niche patterns; validate with §5]**
| # | Format | Why it converts |
|---|---|---|
| 1 | **"What [Celeb] eats in a day"**, a fast meal-by-meal list with calorie counter | Curiosity plus utility; a series format makes people subscribe for the next one |
| 2 | **One shocking fact**: "The Rock eats 10 lb of cod a week" | 1-second hook with a single payoff; loops well |
| 3 | **Transformation reveal** (before, then after, then "here's how", then a link) | Visual payoff; strongest open loop to the long-form |
| 4 | **"Can you do [Celeb]'s finisher?"** challenge | Prompts comments and shares |
| 5 | **Myth vs truth**: "Did [Celeb] really get shredded in 6 weeks?" | Sets up the long-form documentary |
| 6 | **Ranking or versus**: "Hardest superhero workouts, ranked" | Series potential, debate in comments |

- **Series branding wins subscribers.** Use a recurring title prefix and a recurring visual (counter or card). People subscribe to a series, not a single clip.
- **Audience fit:** only make Shorts on-niche. Subscribers gained from off-topic Shorts never watch long-form (vidIQ). https://vidiq.com/blog/post/youtube-shorts-for-brands/

### 3.2 Craft spec
- **Length:** 20-45 s by default, up to 60 s for diet lists **[BENCH/GUESS]**. Retention is what matters, not runtime.
- **Hook within 1 s:** the first frame shows the payoff visual plus text (number or celebrity face plus claim). No logo, no "hey guys". Voice starts at 0.0 s.
- **Loop:** the last line runs into the first ("…and that's why he eats this. | This is what…").
- **Captions:** burned-in, word-level highlight (whisperX timestamps), kept inside the safe zone (avoid the bottom 20% and the right-side UI).
- **Related video link:** **always** link to the parent long-form (Studio → Shorts → Related video; one link per Short) **[OFFICIAL]**. https://support.google.com/youtube/answer/14075157 Click-through is low (one guide reports as little as 0.05%), so subscribers, not referral views, are the main payoff.
- **Shorts make the promise; the long-form's first 30 s must deliver that same promise.**
- **Cadence:** **5-7 Shorts per long-form**, 2-3 a day. Release the first 2 within 24 h of the long-form. Hold the strongest for days 3-5 so they act as a second push.
- **No licensed music** (see the revenue split in §2.1).

### 3.3 Automation: long-form to vertical (verified on GitHub 2026-11-21 via `gh api`)
| Repo | Stars | License | Last push | Notes |
|---|---|---|---|---|
| zhouxiaoka/autoclip | 12,932 | MIT | 2026-11-22 | Active; AI highlight clipping pipeline |
| mutonby/openshorts | 9,648 | MIT | 2026-11-21 | Active; long-form to vertical Shorts |
| modelscope/FunClip | 6,617 | MIT | 2026-11-01 | ASR plus LLM clipping (strong for Chinese and English) |
| Anil-matcha/AI-Youtube-Shorts-Generator | 6,435 | MIT | 2026-11-21 | `SamurAIGPT/...` redirects here; highlight detection plus face crop |
| WyattBlue/auto-editor | 6,045 | Unlicense | 2026-11-22 | Silence and dead-air cuts (pre-pass) |
| leamsigc/ShortsGenerator | 362 | MIT | 2026-10-11 | Small |
| ClipsAI/clipsai | 609 | MIT | 2024-01-17 | **Stale**; avoid |
| m-bain/whisperX | 25,576 | BSD-2 | 2026-11-21 | Word timestamps for captions |
| google-ai-edge/mediapipe | 37,776 | Apache-2.0 | 2026-11-22 | Face detection for a custom smart crop |
| facebookresearch/sam2 | 20,209 | Apache-2.0 | 2026-05-30 | Subject tracking when there is no face |

- **Recommendation:** we already have the script, the timestamps and the graphics, so **don't clip blindly**.
  1. The LLM picks 5-7 "Short-able beats" from the script's claim ledger.
  2. FFmpeg cuts at those script timestamps.
  3. For footage segments, run the MediaPipe face track plus a smoothed crop (borrow from openshorts or AI-Youtube-Shorts-Generator).
  4. For our graphics, **re-render them natively at 1080×1920** in HyperFrames/Remotion rather than cropping 16:9.
  5. Add a new 1 s hook card and a Kokoro VO re-cut.
  6. Use autoclip or openshorts as the fallback or idea generator. YouTube Studio's own "Clips and Shorts" tool also exists. https://support.google.com/youtube/answer/15824265

---

## 4. Thumbnails, titles and Test & Compare

- **What works [BENCH/GUESS]:**
  - 1 celebrity face with strong emotion, plus 1 contrasting object (plate of food, dumbbell, before/after split), plus 0-3 words that do not repeat the title.
  - High contrast, readable at phone size.
  - A consistent channel look, so returning viewers recognize it.
  - Titles: specificity beats hype (numbers, timeframes, named plan).
- **Test & Compare** **[OFFICIAL]**, https://support.google.com/youtube/answer/16391400:
  - Up to **3 variants** of thumbnail, title, or title plus thumbnail. Requires advanced features.
  - Runs up to 2 weeks. The **winner is chosen on watch-time share** (watch time per impression), not CTR. If there is no winner, variant 1 stays.
  - Titles were added July-Dec 2025. https://www.tubefilter.com/2025/07/16/youtube-feature-test-and-compare-titles-thumbnails/
  - Not available for Shorts.
- **Weekly experiment protocol:**
  1. **One hypothesis per week, the same variable across all 3 uploads**, for example "face-close-up vs before/after split". Do not mix variables.
  2. Variant A = control (current house style), B = challenger, C = a wild card.
  3. Log the test result ("Winner", "Performed same" or "Inconclusive") plus the watch-time share in the experiment table.
  4. Promote a style to house default after it wins **2 of 3** tests. Retire a style after it loses 3.
  5. Run title tests in alternate weeks (title-only test) so effects don't confound.

---

## 5. Tracking

### 5.1 What each API gives
| Source | Auth | Gives | Gaps |
|---|---|---|---|
| **Data API v3** | API key | Public views, likes, comments, duration, publish time, title, tags | No retention, CTR or revenue |
| **Analytics API** (`youtubeAnalytics.reports.query`) | Owner OAuth (`yt-analytics.readonly`, plus `yt-analytics-monetary.readonly` for revenue) | `views`, `engagedViews`, `estimatedMinutesWatched`, `averageViewDuration`, `averageViewPercentage`, `subscribersGained/Lost`, `likes`, `shares`, `comments`, `estimatedRevenue`, `estimatedAdRevenue`, `playbackBasedCpm`, `cpm`, `monetizedPlaybacks`, `adImpressions`; retention curve via `audienceWatchRatio` and `relativeRetentionPerformance` by `elapsedVideoTimeRatio`; dimensions `creatorContentType` (SHORTS / VIDEO_ON_DEMAND), `insightTrafficSourceType` (YT_SEARCH, RELATED_VIDEO, SHORTS, SUBSCRIBER…), `subscribedStatus` | **No thumbnail impressions or CTR**; no new/returning split; no viewed-vs-swiped |
| **Reporting API** (bulk daily CSV jobs) | Owner OAuth | `channel_reach_basic_a1` / `channel_reach_combined_a1` → `video_thumbnail_impressions`, `video_thumbnail_impressions_ctr` (by video, traffic source, device) | Daily batch, about 2-day lag |
| **Studio only** (manual or scraped) | n/a | Viewed vs Swiped (Shorts), casual/regular/new viewers, survey satisfaction (not exposed), Test & Compare results | Paste into the sheet weekly |

Docs: https://developers.google.com/youtube/analytics/metrics · https://developers.google.com/youtube/analytics/dimensions · https://developers.google.com/youtube/reporting/v1/reports/channel_reports
Setup: create Reporting API jobs for `channel_reach_basic_a1` on day 1, because data accrues only after a job exists. Run a nightly cron that pulls all three sources into SQLite plus a Google Sheet.

### 5.2 Per-video metric set (snapshots at 48h, 7d and 28d)
- `impr`, `ctr` (Reporting) · `views`, `engaged_views` · `avd_s`, `apv` = averageViewPercentage
- `ret30` = audienceWatchRatio at elapsedVideoTimeRatio ≈ 30 s / duration · `ret_rel` = mean relativeRetentionPerformance
- `likes_per_1k` = likes / views × 1000 · `comments_per_1k`, `shares_per_1k`
- `subs_per_1k` = (subscribersGained − subscribersLost) / views × 1000
- `rpm` = estimatedRevenue / views × 1000 · `cpm` · `mon_rate` = monetizedPlaybacks / views
- `search_share` = YT_SEARCH views / views · `browse_suggested_share`
- Shorts only: `viewed_pct` (Studio), `engaged_rate` = engagedViews / views, `rel_link_ctr` (Studio Related-video clicks / views), `subs_per_1k`

### 5.3 Weekly scorecard (one row per week, plus per-video rows)
| KPI | Formula | Target |
|---|---|---|
| Watch hours (LF) | Σ estimatedMinutesWatched / 60 | +5% WoW |
| Net subs | Σ gained − lost (split LF vs Shorts) | +10% WoW early stage |
| Shorts → sub efficiency | Shorts net subs / (Shorts engaged views / 1000) | ≥ channel median |
| Revenue | Σ estimatedRevenue; RPM = rev / views × 1000 | RPM ≥ last 4-week median |
| Packaging | median CTR of the week's LF at 7d | ≥ baseline |
| Holding | median APV of the week's LF at 7d | ≥ baseline |
| Love | likes_per_1k and comments_per_1k median | ≥ baseline |
| Search | search_share median | rising trend |
| Hit rate | % of LF with lift_composite ≥ 1.0 | ≥ 50% |

`baseline(metric, age)` = rolling **median of the last 10 long-forms** (or 20 Shorts) **at the same age** (48h, 7d or 28d). `lift = video / baseline`.
`lift_composite = 0.25·ctr + 0.35·apv + 0.15·subs_per_1k + 0.15·likes_per_1k + 0.10·rpm` (each term is a lift) **[GUESS weights]**.

### 5.4 Learning loop
1. **Tag at creation** (written by the pipeline into `video_meta`): celebrity, celebrity category, topic (workout/diet/transformation), arc template, title formula (question, number, "how X…", "I tried"), hook type (shock fact, contradiction, visual reveal, stakes), thumbnail style, length bucket, mid-roll count, footage %, publish day and hour, Short format.
2. **Nightly:** pull the 48h, 7d and 28d snapshots and compute lifts.
3. **Weekly (Monday):**
   - Group by each tag value and compute the median lift and n.
   - A tag value becomes a **"winner"** when n ≥ 3 and median lift_composite ≥ 1.15.
   - It becomes a **"loser"** when n ≥ 3 and lift ≤ 0.85.
   - Keep 20% of slots for **exploration**: untested celebrities and formats.
4. **Feed forward:** the LLM writes the next week's 3 briefs with winners as defaults plus 1 exploration slot. The brief cites the evidence ("number titles: n=5, lift 1.22").
5. **Retention autopsy:** for every video, find the 3 steepest drops in `audienceWatchRatio`. The LLM reads the script lines at those timestamps and adds lessons to `lessons.md`, which is injected into the script prompt as few-shot "don't do this" examples.
6. **Guard rails:** never promote a tag on CTR alone. It must not reduce APV or likes_per_1k.

---

## 6. Evals

### 6.1 Pre-publish (automatic; any red blocks the upload)
| # | Check | Method | Pass |
|---|---|---|---|
| 1 | **Hook strength** | LLM judge (3 runs, take the median) scores the first 30 s script on curiosity gap, specificity, payoff promise and "no throat-clearing", each 1-5 | ≥ 16/20; delivery of the title promise by 60 s |
| 2 | **Fact sourcing** | Claim extractor → every numeric or biographical claim needs a ledger URL; LLM verifies the source supports the claim | 100% sourced; 0 contradictions |
| 3 | **Originality / inauthentic guard** | Third-party footage seconds / runtime; max single clip; embedding similarity of the script vs the last 20 scripts; arc template ≠ the previous 2 | footage ≤ 30%, clip ≤ 5-8 s, cosine < 0.85 |
| 4 | **Length** | ffprobe | 15:00-25:00 LF; Shorts ≤ 60 s (≤ 180 hard cap) |
| 5 | **Loudness** | `ffmpeg -af ebur128` / loudnorm | −14 LUFS ±1, true peak ≤ −1.5 dBTP **[BENCH, community standard]** https://productionadvice.co.uk/youtube-loudness/ |
| 6 | **Audio QA** | silence gaps > 1.5 s, TTS mispronunciation of names (ASR round-trip WER on proper nouns) | 0 gaps; proper-noun WER = 0 |
| 7 | **Title rubric** | celebrity name in the first 40 characters; ≤ 70 characters; specific number or noun; matches the content; no ALL CAPS; LLM "does the video deliver this?" | all pass |
| 8 | **Thumbnail rubric** | vision LLM at 168×94 px: face visible, ≤ 3 words, legible, contrast, not duplicating title text; 3 variants exist for Test & Compare | ≥ 4/5 and 3 variants |
| 9 | **SEO pack** | description first 150 characters contain celebrity plus topic; ≥ 5 chapters starting 00:00, each ≥ 10 s; SRT uploaded; playlist assigned; pinned comment drafted; ≤ 15 tags | all present |
| 10 | **Ad suitability** | LLM scan of script and visuals for advertiser-unfriendly terms or imagery (drugs/PEDs framing, profanity, gore) | 0 high-risk in first 30 s; flag for editor review |
| 11 | **Mid-roll plan** | breaks align with chapter ends, none in the first 3 min or the final 60 s, 3-5 total | pass |
| 12 | **Disclosure** | any realistic synthetic depiction of a real person? | none, or the disclosure box is ticked |
| S | **Shorts extras** | payoff visual in frame 0; text in the first 1 s; captions within the safe zone; loop point; Related-video set; no licensed music | all pass |

### 6.2 Post-publish (from analytics, vs targets)
| Metric | 48h | 7d | 28d | Target basis |
|---|---|---|---|---|
| CTR (LF) | ≥ 5% | ≥ 4.5% | ≥ 4% | **[BENCH, weak]** third-party guides: 4-6% typical, > 6% excellent, ~3% fine for a new channel (no official YouTube CTR benchmark exists); then use own baseline |
| APV (LF, 15-25 min) | ≥ 35% | ≥ 33% | ≥ 30% | **[BENCH]** platform average ~23.7%, educational how-to ~42.1% (https://research.stripo.email/youtube-benchmarks); 30-35% is a **[GUESS]** for doc-length |
| 30 s retention (LF) | ≥ 70% | — | — | **[BENCH]** > 65% first-minute retention correlates with +58% AVD (Retention Rabbit via Stripo) |
| relativeRetentionPerformance | ≥ 0.5 | ≥ 0.5 | — | API: 0.5 = median of similar-length videos |
| Likes / 1k views | ≥ 30 | ≥ 25 | ≥ 25 | **[GUESS]** |
| Net subs / 1k views (LF) | ≥ 3 | ≥ 2.5 | ≥ 2 | **[GUESS]** |
| RPM (LF) | — | ≥ $3 | ≥ $3 | **[BENCH]** health/fitness $1.2-5, low agreement |
| Shorts viewed % | ≥ 60% | ≥ 60% | — | **[GUESS]**; the example channel was 26.6%, so start from own median |
| Shorts net subs / 1k engaged views | ≥ 1.0 | ≥ 1.0 | — | **[GUESS]** |
| Shorts APV | ≥ 70% | — | — | **[BENCH, weak]** median Short ~45% view-through; completion claims of 73-76% at 50-60 s |

**Actions on failure:**
- **48h CTR red** → swap to the next Test & Compare variant or start a test.
- **APV red with good CTR** → packaging over-promises; flag the title formula.
- **30 s retention red** → hook rubric recalibration (add the case to the judge's few-shot examples).
- **Subs red with good APV** → add a mid-video subscribe beat and an end-screen to the next series video.
- **Shorts viewed % red** → re-cut frame 0 and repost as a new angle (never an identical reupload; that is an inauthentic-content risk).

**Calibration:** after 6 weeks, replace every [GUESS] target with the channel's own 60th-percentile value and keep ratcheting it quarterly. "Better every week" = hit rate and median lift_composite trending up on a 4-week rolling basis.
