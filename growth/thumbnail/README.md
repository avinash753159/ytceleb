# Thumbnails (run after every upload)

Real celebrity only: the picture is a real frame from the finished video (or a real photo you pass). No AI-generated images.

```
python growth/thumbnail/thumbnail.py auto --video-id <ID> --video final.mp4 --token token_youtube_celebworkout.pickle
```

- Builds a 1280x720 thumbnail in the channel's best-performing style (Bucky Barnes / Lamine / Hemsworth) with built-in variety (star left or right, 4 colour grades, 4 headlines, arrow or circled meal, 12 meal+bottle combos): real photo scene with glow, star big on the right, huge white `WORKOUT & DIET PLAN` or `TRAIN LIKE`, red name box, and a real meal + water or BLACK WATER bottle (props/, varies per video).
- Keep originals on videos that already perform; use this for new uploads and weak thumbnails only.
- Before uploading, the current thumbnail is saved to `growth/thumbnail/backups/<ID>/` (never deleted).
- Undo one: `python growth/thumbnail/thumbnail.py rollback --video-id <ID> --token ...`
- Undo all: `python growth/thumbnail/thumbnail.py rollback --all --token ...`
- Preview without uploading: `... make --video-id <ID> --title "<title>" --video final.mp4` then look at `out/<ID>.jpg`.
- If no clear face is found it stops and asks for `--photo`. Check the result: if the cutout shows the wrong person, a tiny person, or stray text, use `--photo` with a clean real photo.
- Shorts are skipped (the Shorts feed ignores custom thumbnails).
