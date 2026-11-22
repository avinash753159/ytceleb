# Celeb Workout (@CelebWorkout): Channel Analysis

Pulled 2026-11-21 with yt-dlp (public metadata only). Channel: 32,300 subscribers.
Coverage: 207 long-form videos and 53 Shorts. All 260 have full per-video metadata, with no gaps and no 429s.
Raw data: `channel_videos.csv`, in the same folder as this report. Analysis output: `analysis_out.txt`. Scripts and raw JSON: `scripts/` and `raw/`.
"Views/day" means lifetime views divided by days since upload. That measure favours recent uploads only slightly, because YouTube views decay.
Anything marked **[GUESS]** is an inference, not something the data measured.

---

## 1. Headline numbers

| | Long-form | Shorts |
|---|---|---|
| Videos | 207 | 53 (last Short posted Jul 2022) |
| Total views | 6,121,369 | 159,630 |
| Median views | 6,566 | 1,399 |
| Median views/day | 6.6 | 0.7 |
| Median like rate | 1.66% | 2.14% |
| Median comment rate | 0.10% | 0.06% |
| Share of views from the top 10 videos | 49.3% | 67.6% |
| Videos with 100k+ views | 10 | 0 |

The channel has had three eras.

| Era | Uploads | Median views | Total views | Note |
|---|---|---|---|---|
| 2021 | 52 | 30,324 | 3.72M | "X Workout And Diet \| Train Like a Celebrity \| Celeb Workout" template, A-list names |
| 2022–Jan 2024 | 104 | 4.4k–7.4k | 1.48M | Same template, B-list names (Jonah Hill, Scott Herman, Ashley Graham, Jake Paul) |
| Sep 2025–Sep 2026 | 51 | 2,076 | 0.93M | New, shorter (~8 min) format |

Inside the new era, Oct–Dec 2025 was a breakout and 2026 fell off:
- Oct 2025 to Dec 2025: Lamine Yamal 427k, Chris Hemsworth 119k, Chris Evans/Captain America 96k, Michael B. Jordan 47k, Christian Bale/Batman 32k. November 2025 alone brought 528k views.
- 2026: 33 uploads, median 1,525 views.
- Cadence collapsed. Uploads went from 4–5 a month to 3 in Jul 2026, 1 in Aug and 3 in Sep. **The last upload was 2026-09-12, so the channel has been silent for 10 weeks.**

## 2. Top 10 / bottom 10 (long-form)

**Top 10 by total views:**
1. Jason Statham, 592k
2. Lamine Yamal, 427k (2025, 1,142 views/day, the best rate on the channel)
3. Daniel Craig, 390k
4. Jason Momoa, 361k
5. Michael B Jordan, 358k
6. Jennifer Aniston, 310k
7. Dita Von Teese, 176k
8. Usain Bolt, 158k
9. Henry Cavill, 126k
10. Chris Hemsworth Full Week, 119k (2025)

**Top views/day:**
1. Yamal, 1,142
2. Hemsworth Full Week, 302
3. Statham, 299
4. Captain America 12-Week Plan, 252
5. Daniel Craig, 199
6. MBJ, 194
7. Momoa, 185
8. Aniston, 170
9. MBJ Creed & Black Panther, 121
10. Train Like James Bond, 112

**Bottom 10 by views/day (all 0.6–1.3/day):**
- Jonah Hill
- Scott Herman
- Ashley Graham
- "LOSE BELLY FAT at Home NO GYM!": 209 views, the only non-celebrity video
- Tessa Thompson
- Ashton Kutcher
- Alia Bhatt
- Tom Brady
- Gabrielle Union
- Jake Paul

2026 flops (under 1,000 views each):
- Hudson Williams (407)
- Rock vs Cena (462)
- Tommy Shelby vs Alfie Solomons (475)
- Dita Von Teese remake (485)
- Jason Statham & Mark Wahlberg "Never Eat That RUIN Youth" (578)
- Chris Heria anime (604)
- Marvel 4-week program (632)
- Idris Elba (666)
- Jeremy Renner Hawkeye (722)
- Thanos (825)

**What viewers watch:**
- **Who** the star is matters most. A-list action and superhero leads (Statham, Craig, Momoa, MBJ, Hemsworth, Evans, Cavill, Bale) and global athletes at peak hype (Yamal, Bolt) win.
- Niche, B-list or side-character subjects lose, whatever the title.
- Clickbait angles ("never eat", "5 HUGE mistakes", "vs") lost in 2026 as well.

## 3. Duration

| Length | n | Median views | Median views/day |
|---|---|---|---|
| 5–8 min | 16 | 1,810 | 7.7 |
| **8–10 min** | **45** | **14,957** | **18.9** |
| 10–12 min | 30 | 6,421 | 5.8 |
| 12–15 min | 64 | 9,824 | 7.0 |
| 15–20 min | 46 | 5,249 | 3.7 |

- Duration and views are basically uncorrelated (log–log r = 0.05).
- 8–10 minutes is the best bucket on both measures, and 8 minutes is the ad-break threshold for mid-rolls. Keep videos at 8:00–9:30.
- **[GUESS]** The 5–8 minute 2026 videos give up mid-roll inventory.

## 4. Titles

The old 2021 formula worked when demand was easy:
`<A-list name> Workout And Diet | Train Like a Celebrity | Celeb Workout`
- 156 videos use it, with median 9,071 views. Its views/day is lower (5.7 against 9.8) because it is old content.
- The winners in it were all stars.

Winners in the new era share one shape: **star + iconic role or credential + concrete specificity, with no brand suffix.**
- "Train Like Captain America: Chris Evans' 12-Week Plan" (96k)
- "Chris Hemsworth Workout & Diet Plan (Full Week Breakdown)" (119k)
- "Inside Lamine Yamal's Brutal Training & Matchday Diet" (427k)
- "How Michael B. Jordan Built His Creed & Black Panther Physique" (47k)
- "Christian Bale's Batman Workout & Diet (Full Routine)" (32k)

What the title features show (long-form, median views):
- **Colon titles** ("Train Like X: ..."): 7 videos, median 15.5k, 47.8 views/day against 6.1 without a colon. This is the strongest single signal, but n is small.
- **A hype word** (brutal, insane): 4 videos, 67.6 views/day.
- **A movie or role reference** (Batman, Captain America, Creed, Spider-Man): 14 videos, 34 views/day against 5.8 without.
- **ALL-CAPS words** (TRAIN LIKE THANOS, LOSE BELLY FAT, HUGE): 5 videos, median 825 views. These hurt.
- "Routine" in the title: median 2,268. "Transformation": 3 videos, median 1,599. Neither moves views.
- Best title length is 55–70 characters (median 9,149). Titles over 85 characters had a median of 2,076.

Search position, checked 2026-11-21 with yt-dlp ytsearch25:
- "celebrity workout routine": #1 is our "Top 10 Hardest Celebrity Workouts Ranked 2026", even though it has only 1,587 views.
- "celebrity workout and diet": we hold #6, #10, #13, #18, #24 and #25.
- "train like a superhero actor workout": we hold #13 and #20.

The channel already ranks on the generic head terms. That search traffic is small. The views come from the celebrity name searches.

**Winning title formula** (use one of these):
- A. `Train Like <Role>: <Star>'s <Specific Plan>` (e.g. "Train Like Doctor Doom: Robert Downey Jr.'s Avengers Workout")
- B. `How <Star> Got <Result> for <Movie/Role> (Workout + Diet)`
- C. `<Star>'s <Role> Workout & Diet (Full Week Breakdown)`

Rules:
- Put the star's name in the first 30 characters.
- Name one role or event.
- Add one specific detail: weeks, Full Week, Matchday or a number.
- Use at most one hype word.
- No ALL CAPS.
- No "| Celeb Workout" suffix.
- Keep the title at 55–70 characters.

## 5. Tags and descriptions

**Tags:**
- Every video carries the same boilerplate of about 13 tags (celebrity workout, train like a celebrity, celebrity diet plan, fitness, men's health, women's health, motivational workout, and so on). The median is 16 tags.
- The tag sets include duplicates with stray spaces, such as " train like a celebrity " twice.
- Because the boilerplate is on everything, its "median views" tells us nothing. YouTube treats tags as a minor signal anyway.
- Use 5–8 tags: the star's name, star + workout, star + diet, the role + workout, and the movie title + training.

**"Men's Health" in metadata:**
- One 2026 title literally ends "| Men's Health" (Hudson Williams, 407 views).
- 90 videos carry a "men's health" tag.
- That is another publisher's brand, and Men's Health is the #1 competitor in this search space. **[GUESS]** It risks a misleading-metadata strike. Remove it.

**Descriptions:**
- Old videos open with Amazon affiliate equipment links (72% of long-form descriptions contain a link).
- New videos open with a narrative paragraph ("Before Spider-Man became...").
- No long-form description uses hashtags.
- Short descriptions are pasted Wikipedia-style bios.

**Chapters:**
- 193 of 207 long-form videos have chapters. Median views are 7,283 with chapters and 694 without.
- That gap is confounded by era, so it is not proof that chapters cause views. Keep using them.

**Template:**
```
TITLE:  Train Like <Role>: <Star>'s <Movie> Workout & Diet (Full Week)
DESC line 1 (shows in search, ~150 chars): How <Star> trained and ate to play <Role> in <Movie> (<year>): the weekly split, sets/reps, and the exact diet.
DESC line 2: What you'll learn: 1) <Star>'s training split 2) the diet and calories 3) how to copy it at home or in the gym.
CHAPTERS: 0:00 The transformation · 0:45 The trainer · 1:30 Weekly split · ... · Diet · Your version
SOURCES: trainer interviews / magazine articles cited (builds trust)
Related: <2 playlist links: same franchise / same star>
Affiliate block (below the fold, not first line)
#<StarName> #<Movie> #CelebrityWorkout   (3 hashtags max)
TAGS: <star>, <star> workout, <star> diet, <role> workout, <movie> training, <star> transformation, celebrity workout
```

## 6. Shorts

- 53 Shorts, all posted Aug 2021–Jul 2022, all titled `<Name> Workout And Diet #short`, with Wikipedia-bio descriptions.
- Median 1,399 views. Only 3 passed 10k: Tom Cruise 54,551, Daniel Craig 15,106 and Vin Diesel 12,275.
- Like rate is higher than on long-form (2.14% against 1.66%), but reach is about 1/5.
- **There have been no Shorts for 4+ years.**

Competitor Shorts that work (flat-playlist view counts):
- **Paris Demers** (208k subs) has a Shorts median of 40,000. Their top Shorts are story and controversy hooks about a star's body:
  - "These 5 Celebrities' Just Admitted To Taking Juice!" 25M
  - "How Bruce Lee built his famous one-inch punch" 13M
  - "Jason Momoa is getting in trouble for being fat…" 10M
  - "Hugh Jackman is in trouble for being unfit..." 8M
  - "Robert Pattinson said no to taking juice during Batman!" 7.5M
- **Men's Health Shorts** (median 12k):
  - "Everything Jensen Ackles eats in a day #theboys" 1.3M
  - "Laz Alonso explains his Mother's Milk body transformation" 877k
- **Beast Mode** (faceless, 1.6k subs, closest to our format): "Mark Wahlberg's INSANE diet for lent" 19k, "Henry Cavill's Secret Trick To Get Ripped" 13k.

**Shorts recommendations:**
- Restart at 3–5 a week.
- Make each Short one surprising fact plus a hook, never a "Workout And Diet" summary. Example: "Jason Momoa got in trouble for his dad bod... then did THIS for Lobo".
- Keep them under 40 seconds.
- Link each Short to the matching long video (related-video link).
- Cut 2–3 Shorts from every long video.
- **[GUESS]** Shorts bring subscribers more than ad revenue; Shorts RPM is far below long-form.

## 7. Competitors

Channels found by `ytsearch25` on 5 seed queries. Stats are from the flat playlists of each channel's latest ~400 videos and 200 Shorts.

| Channel | Subs | Long median | Best long titles (views) | Contrast with us |
|---|---|---|---|---|
| **Paris Demers** | 208k | 72,000 | "Will Poulter's Secret That Got Him JACKED For Guardians Of The Galaxy 3!" 941k; "Tom Hardy's Secret For Getting BIG To Play Bane! (Full Workout Program)" 815k; "How Tom Holland Got Ripped For Spider-Man No Way Home (Do It Yourself!)" 711k | Closest analog. **Every title names role + movie**, adds a "Secret"/"JACKED" payoff and a "you can do it" promise. Videos run 6–12 min. |
| **Men's Health** | 1.83M | 90,500 | "Jake Gyllenhaal's Workout To Get His Ridiculous Road House Body \| Train Like" 10M; "Reacher's Alan Ritchson Shows Off His Gym and Fridge" 7.7M; "Everything Tom Holland Eats In a Day" 5.7M | Has access to the stars (on-camera). Series names: Train Like / Eat Like / Gym & Fridge. |
| **Beast Mode** | 1.6k | 1,400 | "How Jason Statham Got Jacked WITHOUT Lifting Heavy Weight" 373k; "Daniel Craig's Workout To Get His Ridiculous James Bond Body" 122k | Faceless like us. Wins come from the same stars (Statham, Craig) with a contrarian twist. |
| **Radoslav Detchev** | 119k | 3,500 | "Actors Give Advice on Diet & Exercise" 10M (a compilation) | One-hit compilation; ranks #1 for "celebrity workout and diet". |
| **Will Tennyson** | 5.64M | 1.7M | Fitness-challenge entertainment (not celebrity) | Shows the ceiling for personality-led fitness. Not a direct competitor. |
| The Bossticks | 319k | 21,000 | Interviews (Ivanka Trump 805k) | Appears in search via a Miranda Kerr video only. Not a real competitor. |

Paris Demers's titles sell a **payoff** ("Secret", "Got JACKED", "Lost 60 Pounds") tied to a **specific role**. Ours mostly sell a **category** ("Workout & Diet Routine").

## 8. Keyword demand (YouTube autocomplete, 2026-11-21)

Autocomplete shows that a phrase is demanded. It does not give volume.

Generic phrases that appear:
- "celebrity workout routines (female)"
- "celebrity workout and diet"
- "celebrity diet plan"
- "actor workout transformation"
- "actors workout for movies"
- "how actors get in shape so fast"
- "actors who lost weight for a role"
- "celebrities who gained weight for a role"
- "get a body like brad pitt / bruce lee / captain america"

"train like ..." completes to fictional characters and athletes:
- invincible, goku, batman, david goggins, jason statham, tom holland, henry cavill, spider man, reacher, wolverine, thor, deadpool, tom rhys harries

Role-specific phrases that are live now:
- tom holland workout **brand new day** / "how did tom holland get jacked for brand new day" / "tom holland diet 2026"
- matt damon workout / diet / transformation **for odyssey**
- jason momoa **lobo** workout / training for **blanka** / workout chief of war
- chris hemsworth **avengers doomsday** workout / "thor doomsday workout" / "chris evans doomsday workout"
- roman reigns transformation **akuma** / noah centineo training for **street fighter** / "street fighter movie akuma training"
- milly alcock training for **supergirl** / nicholas galitzine workout for **he-man**
- alan ritchson workout for **reacher season 4**
- jacob elordi transformation **frankenstein** / dwayne johnson **smashing machine** workout / sydney sweeney training for **christy**
- jaafar jackson training for **michael** / sophie turner training **tomb raider** / karl urban training **mortal kombat**
- glen powell workout **running man** / brad pitt workout for **f1** / austin butler training for dune
- Athletes: lamine yamal diet / diet plan / diet and workout; erling haaland diet "6000 calories"; ilia topuria workout and diet; jake paul training for anthony joshua

## 9. The next 15 videos (ranked by likely demand)

Release timing is from my training memory (cutoff mid-2026). **Verify every date before scheduling.** The demand column is evidence from autocomplete.

| # | Video (title draft) | Why / demand evidence |
|---|---|---|
| 1 | Train Like Doctor Doom: Robert Downey Jr.'s Avengers: Doomsday Body | Avengers: Doomsday, Dec 2026 **[GUESS date]**; "avengers doctor doom" autocomplete |
| 2 | Chris Hemsworth's Avengers: Doomsday Thor Workout (Full Week) | "chris hemsworth avengers doomsday workout", "thor doomsday workout"; Hemsworth is already our #2 recent hit (119k) |
| 3 | How Tom Holland Got Jacked for Spider-Man: Brand New Day | 4 separate "brand new day" autocompletes; competitor video at 711k |
| 4 | Train Like Odysseus: Matt Damon's Workout for The Odyssey | "matt damon workout for odyssey", "matt damon odysseus transformation" |
| 5 | Jon Bernthal's Punisher Workout & Diet (Brand New Day) | "jon bernthal punisher workout / training / diet" |
| 6 | Inside Erling Haaland's 6,000-Calorie Diet & Training | Athlete format = our best rate ever (Yamal 1,142/day); "haaland diet 6000 calories" |
| 7 | Lamine Yamal Diet & Training: One Year Later (follow-up) | Sequel to the channel's #2 video; "lamine yamal diet plan" |
| 8 | How Alan Ritchson Bulked for Reacher Season 4 | "alan ritchson workout/training for reacher season 4"; Men's Health's Ritchson video has 7.7M |
| 9 | Jason Momoa's Lobo Workout: From Aquaman to Supergirl | "jason momoa lobo workout"; Momoa is already our #5 video (361k) |
| 10 | Street Fighter Movie Training: Roman Reigns' Akuma & Noah Centineo's Ken | "roman reigns transformation akuma", "noah centineo training for street fighter" **[GUESS: Oct 2026 release]** |
| 11 | Train Like He-Man: Nicholas Galitzine's Masters of the Universe Body | "nicholas galitzine workout for heman" |
| 12 | Milly Alcock's Supergirl Training (Female Superhero Workout) | "milly alcock training for supergirl"; female seed demand ("celebrity workout routines female") |
| 13 | David Corenswet's Superman Workout for Man of Tomorrow | "david corenswet workout for superman", "man of tomorrow 2027" |
| 14 | Robert Pattinson's Batman Part II Workout | "robert pattinson workout for batman"; our 2026 Pattinson video drew 6.2k, among the top 2026 results **[GUESS: Oct 2027 release]** |
| 15 | How Dwayne Johnson Transformed for The Smashing Machine | "dwayne johnson smashing machine workout". Alternates: Sydney Sweeney/Christy, Jacob Elordi/Frankenstein, Jaafar Jackson/Michael, Sophie Turner/Tomb Raider, Ilia Topuria |

## 10. Thumbnails

yt-dlp metadata contains no thumbnail text, so this section is inferred **[GUESS]**:
- The 2021 hits and the 2025 winners all lead with the star's face and the role or franchise.
- Competitor winners pair the role costume with the real-life physique plus 2–4 words ("JACKED FOR BANE", "60 LBS").
- Suggest the star in costume next to them in the gym, with 2–4 words naming the payoff, not the category.
- The bottom performers used ALL-CAPS in the title; avoid repeating title text in the thumbnail.

## 11. Priority actions

1. **Resume uploading.** The channel has been silent since 2026-09-12. Upload 1–2 long videos a week on A-list and current-role topics only.
2. **Drop niche, B-list and listicle subjects.** In 2026 they averaged under 1,000 views.
3. Use the title formula in §4. Keep videos at 8:00–9:30 for mid-rolls. Remove "Men's Health" from titles and tags.
4. Restart Shorts as hook-led single-fact clips cut from each long video. Shorts are the subscriber engine.
5. **Athlete videos at peak news moments** (Yamal format) are the channel's best views-per-day lever.

**[GUESS]** Weekday effects (Monday and Friday look strong) are confounded by era and are not reliable.
