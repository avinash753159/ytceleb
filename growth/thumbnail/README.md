# Thumbnails (run after every upload)

Real celebrity photos only. Never AI-generated images. Modelled on the most-viewed celebrity fitness thumbnails on YouTube
(Men's Health "Train Like" / "Eat Like", 10M+ views): one big real photo, 2 words, star's face large.

## Best: before / after (use for every transformation video)
Get two REAL photos of the star: one before the transformation, one after (press photos, film stills, social posts).
```
python growth/thumbnail/thumbnail.py auto --video-id <ID> --before before.jpg --after after.jpg --token token_youtube_celebworkout.pickle
```
Split layout: BEFORE | AFTER with a white diagonal and arrow, red name tag, huge italic TRAIN LIKE.
Only use photos that really are before and after. Two random frames are not a before/after.

## Otherwise: one real photo or the video itself
```
python growth/thumbnail/thumbnail.py auto --video-id <ID> --photo star_training_shot.jpg --token ...
python growth/thumbnail/thumbnail.py auto --video-id <ID> --video final.mp4 --token ...
```
Alternates per video between:
- TRAIN LIKE: full-frame real photo, huge white italic TRAIN LIKE, small red name tag.
- EAT LIKE: full-frame real photo, big real meal + water / BLACK WATER bottle in front (props/), EAT LIKE + red name tag.
A shirtless or training shot beats an interview shot every time; pass --photo when you have one.

## Evals (run automatically; upload is blocked if any fail)
- 1280x720, under 2 MB
- a REAL name in the red tag (not "CELEB", "MALE CELEBRITY", "A MARVEL HERO")
- a face is detected, fully inside the frame (not cut off at the top) and big enough
- every thumbnail shows a real meal + water / BLACK WATER bottle (labels never mirrored)
Then LOOK at it before it goes live: right person? no stray old text? no floating arm or extra small figures?
If anything is off, use a different real photo (--photo / --before --after). `--force` exists but should not be used.

## Prop evals (run when adding a meal/bottle to props/)
`python growth/thumbnail/prop_eval.py growth/thumbnail/props` fails any cutout with a straight cut on its left, right or top
(a sliced bottle or plate). Props must also be solid (no faded ghost areas). Bottle labels are never mirrored.

## Safety
- Before uploading, the current thumbnail is saved to `growth/thumbnail/backups/<ID>/` (never deleted).
- Undo one: `python growth/thumbnail/thumbnail.py rollback --video-id <ID> --token ...`
- Undo all: `python growth/thumbnail/thumbnail.py rollback --all --token ...`
- Preview without uploading: `... make --video-id <ID> --title "<title>" (--photo p.jpg | --video f.mp4 | --before b.jpg --after a.jpg)`, then open `out/<ID>.jpg`.
- Look at it before leaving it live: wrong person, cut-off body or stray old text means use a different photo.
- Keep originals on videos that already perform well. Shorts are skipped (Shorts feed ignores custom thumbnails).
