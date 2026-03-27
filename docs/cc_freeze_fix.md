Read ~/protocol_pulse/docs/PIPELINE_LAWS.md first.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.

FREEZE FRAME ROOT CAUSE — SURGICAL FIX
Gemini grade: 1/10 freeze_check. 14 freeze frames in iter4.
"temporal noise patch is not a solution" — fix the SOURCE.

CONTEXT:
Every render iteration detects 14-15 freeze frames in pre-flight.
The current fix adds noise=c0s=3 to output — Gemini penalizes this
as a band-aid (1/10). Root cause is UPSTREAM in source clip generation.
Gemini explicitly says: inspect part_*.mp4 for static frames,
re-acquire or re-render faulty assets.

STEP 1 — FIND THE FREEZE FRAME SOURCE
Run freezedetect on the most recent render parts:
  RENDER_DIR=$(ls -td ~/protocol_pulse/video_pipeline_v3/renders/pulse_check_* 2>/dev/null | head -1)
  echo "Render dir: $RENDER_DIR"
  ls $RENDER_DIR/parts/ 2>/dev/null | head -30

For each part_*.mp4 run freezedetect to find WHICH parts have frozen frames:
  for f in $RENDER_DIR/parts/part_*.mp4; do result=$(ffmpeg -i "$f" -vf freezedetect=n=-60dB:d=0.5 -f null - 2>&1 | grep freeze_start); if [ -n "$result" ]; then echo "FREEZE IN: $f"; echo "$result"; fi; done

Document exactly which part files freeze. This identifies the upstream source.

STEP 2 — TRACE TO SOURCE
Read video_pipeline_v3/clip_extractor.py fully.
Read video_pipeline_v3/assembler.py sections that generate the frozen parts.
Look for:
  - Still images converted to video with -loop 1 with no motion added
  - Video clips shorter than expected where ffmpeg pads with last frame
  - Avatar fallback static text cards
  - Any ffmpeg command using -loop 1 on image inputs without zoompan

grep -n "loop 1\|freeze\|static\|fallback\|text_card\|still" video_pipeline_v3/clip_extractor.py | head -30
grep -n "loop 1\|freeze\|static\|fallback" video_pipeline_v3/assembler.py | head -30

STEP 3 — FIX AT SOURCE
For static image-to-video conversions, add Ken Burns motion (no more freeze):
  ffmpeg -loop 1 -i input.jpg -vf "scale=1920:1080,zoompan=z=min(zoom+0.002,1.05):d=125:s=1920x1080,setsar=1" -t DURATION -r 30 -c:v libx264 -pix_fmt yuv420p output.mp4

For clips too short that get padded: use tpad to clone last frame with motion:
  Add -vf "tpad=stop_mode=clone:stop_duration=2" only as absolute last resort.
  Better: ensure clip_extractor never produces clips shorter than minimum duration.

For avatar fallback text cards that are static: add a slow gradient pulse animation.

Implement fix in clip_extractor.py at the generation point — not in assembler.py output.

STEP 4 — REMOVE THE BAND-AID FROM ASSEMBLER
Find and remove the noise=c0s=3 patch from assembler.py:
  grep -n "noise=c0s\|c0s=3" video_pipeline_v3/assembler.py

Remove those filter insertions entirely. Source fix makes them wrong.
Gemini penalizes the noise patch as evidence of poor source quality.

STEP 5 — VERIFY + COMMIT
Test: ffmpeg -i [fixed_clip] -vf freezedetect=n=-60dB:d=0.5 -f null - 2>&1 | grep freeze
Should return zero freeze events.

bash ~/protocol_pulse/regression_test.sh — 0 FAILs required before commit.

Document root cause in ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md:
  Pattern: freeze_frames_source
  Root cause: [what you found]
  Fix: [what you implemented]
  Verify: ffmpeg freezedetect command

git add -A
git commit -m "fix(pipeline): freeze frames at source — motion on static clips, remove noise band-aid"
git push
