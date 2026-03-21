# PROTOCOL PULSE — DAILY MONTAGE GOSPEL
# Version 1.0 | March 2026
# GOSPEL STATUS: Read before ANY montage modification

## MISSION
A daily 60-90 second "Best of Bitcoin" montage video compiled automatically
from the top-scored clips already downloaded by the render pipeline.
Zero new content acquisition. Zero new API cost. Runs after daily render completes.

## CONCEPT
"Protocol Pulse Daily Highlights" — the 4-5 most signal-dense moments
from today's Bitcoin media, back-to-back with branding and music.
Format optimized for YouTube Shorts (vertical 9:16) AND standard (16:9).

## INPUT DATA
Source: ~/protocol_pulse/video_pipeline_v3/output/{DATE}/clips/
Metadata: ~/protocol_pulse/video_pipeline_v3/output/{DATE}/selections.json
Schema: rank, video_id, channel, video_title, start_seconds, end_seconds,
        quote, why, score (float 0-100)

## CLIP SELECTION LOGIC
1. Read selections.json for today
2. Filter: score >= 60 (quality gate)
3. Sort by score DESC
4. Take top 4 clips (aim for 60-75s total)
5. If total duration > 90s: trim lowest-scoring clip to fit
6. If total duration < 45s: lower score threshold to 40

## ASSEMBLY PIPELINE (pure FFmpeg, no re-encoding for same-codec clips)
Step 1: LUFS normalization per clip (target -16 LUFS, loudnorm filter)
Step 2: Scale all clips to 1920x1080 if needed (some sources vary)
Step 3: Add Protocol Pulse intro slate (3s) — red/black brand card
Step 4: Concat clips with 0.3s crossfade xfade filter
Step 5: Add lower-third text overlay per clip (channel name + score bar)
Step 6: Add music bed from assets/music/ (tense or upbeat, 0.15 volume)
Step 7: Add Protocol Pulse outro slate (2s) — "protocolpulse.io"
Step 8: Export 1920x1080 H.264 (standard) + 1080x1920 cropped (shorts)

## BRANDING OVERLAYS
Intro slate: Black bg, red "PROTOCOL PULSE" in Impact, "DAILY HIGHLIGHTS" subtitle
             "MARCH 21, 2026" date stamp, BTC price from morning brief
Lower third: Source channel (white text, red background bar, bottom-left)
             Clip score as signal strength: "●●●●○" (4/5 dots)
Outro slate: Red "STAY SOVEREIGN." on black, protocolpulse.io URL, QR code optional

## OUTPUT FILES
Standard:  ~/protocol_pulse/video_pipeline_v3/output/{DATE}/montage_{DATE}.mp4
Shorts:    ~/protocol_pulse/video_pipeline_v3/output/{DATE}/montage_{DATE}_shorts.mp4
Thumbnail: ~/protocol_pulse/video_pipeline_v3/output/{DATE}/montage_thumb_{DATE}.jpg
Symlink:   ~/protocol_pulse/static/montage_latest.mp4 (always points to today)

## TRIGGER
Runs automatically after overnight_render_loop.py completes a PASS render
OR via cron at 10:00 ET daily as fallback
Cron: 0 14 * * * python3 ~/protocol_pulse/services/montage_producer.py

## SERVICE FILE
~/protocol_pulse/services/montage_producer.py

## QUALITY GATES
- Total duration: 45s minimum, 90s maximum
- All clips: 1920x1080, 30fps, AAC audio
- LUFS: -16 ± 2 (consistent loudness across clips)
- No black frames > 0.5s
- Thumbnail: extracted from highest-scoring clip at peak moment (score keyframe)

## PUBLISHING (Phase 2 — after quality confirmed)
YouTube Shorts API — upload montage_shorts.mp4 daily
X/Twitter — post montage_standard.mp4 with daily BTC price caption
Substack — embed in daily digest

## WHAT MONTAGE NEVER DOES
- Never re-downloads clips (uses already-extracted files only)
- Never runs during active render (check pgrep daily_producer)
- Never blocks or delays main pipeline
- Never uploads without human approval in Phase 1 (local output only)
- Never uses API calls for any processing (pure FFmpeg)
