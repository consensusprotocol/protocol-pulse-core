Read ~/protocol_pulse/docs/gospels/MONTAGE_GOSPEL.md first. Then read ~/protocol_pulse/PIPELINE_LAWS.md.

Build the Protocol Pulse daily montage pipeline. All shell commands. No GUI.

SYSTEM: Ultron, Ubuntu 22.04, FFmpeg 4.4, Python 3.10.
GOSPEL: ~/protocol_pulse/docs/gospels/MONTAGE_GOSPEL.md
CLIP SOURCE: ~/protocol_pulse/video_pipeline_v3/output/{DATE}/clips/
METADATA: ~/protocol_pulse/video_pipeline_v3/output/{DATE}/selections.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — EXAMINE AVAILABLE CLIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ls ~/protocol_pulse/video_pipeline_v3/output/2026-03-21/clips/
cat ~/protocol_pulse/video_pipeline_v3/output/2026-03-21/selections.json | python3 -m json.tool

Understand the clip file naming convention and metadata schema before building.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — BUILD montage_producer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
File: ~/protocol_pulse/services/montage_producer.py

The service must:

A) LOAD CLIPS
   - Find today output dir: ~/protocol_pulse/video_pipeline_v3/output/{TODAY}/
   - Read selections.json
   - Map each selection to its clip file: clips/clip_{rank}_{channel}_{video_id}.mp4
   - Filter: score >= 60.0
   - Sort by score DESC
   - Take top 4 (or 5 if all fit in 90s)

B) VALIDATE CLIPS
   - ffprobe each clip: duration, codec, resolution, audio
   - Skip any clip that is corrupt or <5s
   - Require at least 2 valid clips to proceed

C) NORMALIZE AUDIO (per clip)
   For each clip:
   ffmpeg -i {clip} -af loudnorm=I=-16:TP=-1.5:LRA=11 -c:v copy {clip_norm}
   Save normalized version to work/ subdir

D) SCALE VIDEO (if needed)
   If any clip is not 1920x1080:
   ffmpeg -i {clip} -vf scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2 {clip_scaled}

E) BUILD INTRO SLATE (3 seconds)
   Pure FFmpeg lavfi — no external images needed:
   ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=3      -vf "drawtext=fontcolor=white:fontsize=80:text=PROTOCOL PULSE:x=(w-tw)/2:y=(h-th)/2-60,
          drawtext=fontcolor=red:fontsize=40:text=DAILY HIGHLIGHTS:x=(w-tw)/2:y=(h-th)/2+20,
          drawtext=fontcolor=white:fontsize=30:text={DATE}:x=(w-tw)/2:y=(h-th)/2+80"    -c:v libx264 -t 3 intro.mp4

F) BUILD LOWER THIRDS (burned into each clip)
   For each clip, add overlay:
   - Red bar at bottom: channel name + score dots
   ffmpeg -i {clip} -vf "drawbox=x=0:y=960:w=600:h=50:color=red@0.85:t=fill,
     drawtext=fontcolor=white:fontsize=28:text={CHANNEL}:x=15:y=973" {clip_overlay}

G) BUILD OUTRO SLATE (2 seconds)
   ffmpeg -f lavfi -i color=c=black:s=1920x1080:d=2      -vf "drawtext=fontcolor=red:fontsize=100:text=STAY SOVEREIGN.:x=(w-tw)/2:y=(h-th)/2-40,
          drawtext=fontcolor=white:fontsize=35:text=protocolpulse.io:x=(w-tw)/2:y=(h-th)/2+60"    -c:v libx264 -t 2 outro.mp4

H) CONCAT WITH XFADE
   Build concat_list.txt with all parts (intro + clips + outro)
   Use xfade filter for 0.3s dissolve between each clip:
   Build filter_complex string dynamically based on clip count
   Final concat produces montage_{DATE}.mp4

I) ADD MUSIC BED
   Pick from ~/protocol_pulse/assets/music/ — choose track matching mood
   Mix at 0.15 volume under the video audio:
   ffmpeg -i montage_nomusic.mp4 -i {music_track}      -filter_complex "[0:a][1:a]amix=inputs=2:weights=1 0.15:duration=first[a]"      -map 0:v -map "[a]" montage_{DATE}.mp4

J) GENERATE SHORTS VERSION
   Crop center 1080x1920 from 1920x1080:
   ffmpeg -i montage_{DATE}.mp4 -vf "crop=1080:1920:(1920-1080)/2:0"      montage_{DATE}_shorts.mp4

K) GENERATE THUMBNAIL
   Extract frame from highest-scoring clip at midpoint:
   ffmpeg -ss {midpoint} -i {top_clip} -vframes 1 -q:v 2 montage_thumb_{DATE}.jpg

L) COPY TO OUTPUT + UPDATE SYMLINK
   cp montage_{DATE}.mp4 ~/protocol_pulse/video_pipeline_v3/output/{DATE}/
   cp montage_{DATE}_shorts.mp4 ~/protocol_pulse/video_pipeline_v3/output/{DATE}/
   ln -sf ~/protocol_pulse/video_pipeline_v3/output/{DATE}/montage_{DATE}.mp4 ~/protocol_pulse/static/montage_latest.mp4

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — FLASK ROUTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add to ~/protocol_pulse/core/blueprints/ as montage_routes.py blueprint:
  GET /montage — serves montage_latest.mp4
  GET /montage/latest — returns JSON with today montage metadata (title, duration, clips used, scores)
  GET /montage/shorts — serves montage_latest_shorts.mp4

Register blueprint in app.py.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — TEST END TO END
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
python3 ~/protocol_pulse/services/montage_producer.py

Verify:
- montage_2026-03-21.mp4 exists and is >10MB
- montage_2026-03-21_shorts.mp4 exists
- montage_thumb_2026-03-21.jpg exists
- Duration between 45-90s
- ffprobe shows clean A/V (no silence, no black)
- /static/montage_latest.mp4 symlink works
- curl http://localhost:5000/montage/latest returns JSON

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — ADD CRON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add: 0 14 * * * python3 /home/ultron/protocol_pulse/services/montage_producer.py >> /home/ultron/protocol_pulse/logs/montage.log 2>&1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
git add services/montage_producer.py core/blueprints/montage_routes.py app.py
git commit -m "feat(montage): daily highlights montage — top-scored clips, FFmpeg assembly, intro/outro slates, lower thirds, music bed, Shorts version, Flask routes"
git push

DO NOT touch: assembler.py, tts_engine.py, daily_producer.py, overnight_render_loop.py