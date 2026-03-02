# PULSE CHECK V4 — DUAL-HOST HIGHLIGHT REEL — EXECUTE NOW

CRITICAL: Do NOT use planning mode or todolists. Do NOT show a plan and ask to proceed. Start writing code IMMEDIATELY.

## CONTEXT

You already analyzed this in a previous session and made a plan. The plan identified these files to modify/create in ~/protocol_pulse/video_pipeline_v3/:

| File | Action |
|------|--------|
| script_writer.py | Rewrite for dual-host dialogue JSON |
| tts_engine.py | Add 2nd voice + dialogue audio generation |
| clip_fetcher.py | Add YouTube clip download via yt-dlp |
| assembler.py | Add dialogue visuals + clip-react assembly |
| daily_producer.py | Rewrite to 14-step V4 pipeline |
| shorts_cutter.py | Add V4 shorts generation |
| thumbnail_gen.py | NEW — 1280x720 auto thumbnails (Pillow) |
| chapters.py | NEW — YouTube chapter markers |
| podcast_feed.py | NEW — RSS audio podcast feed |
| newsletter_embed.py | NEW — Resend API email snippet |

## EXISTING FILES

- daily_producer.py, tts_engine.py, clip_fetcher.py, assembler.py, script_writer.py already exist
- ElevenLabs Jessica voice: cgSgspJ2msm6clMCkdW9
- yt-dlp, ffmpeg, Whisper are installed on Ultron

## KEY REQUIREMENTS

### Dual-Host Voices
- Host 1 (Jessica): cgSgspJ2msm6clMCkdW9 (already configured)
- Host 2: List available ElevenLabs voices first:
```bash
curl -s "https://api.elevenlabs.io/v1/voices" -H "xi-api-key: $(grep ELEVENLABS ~/protocol_pulse/.env | cut -d= -f2)" | python3 -c "import json,sys;d=json.load(sys.stdin);[print(f'{v[\"voice_id\"]} | {v[\"name\"]} | {v.get(\"labels\",{}).get(\"gender\",\"?\")}') for v in d['voices'][:20]]"
```
Pick a natural male voice. Fallback: Adam (pNInz6obpgDQGcFmaJgB)

### Script Generation (script_writer.py)
- Claude API generates dual-host conversation script as JSON
- Dialogue array: [{host: 1, text: "..."}, {host: 2, text: "..."}, {host: "CLIP", text: "[PLAYS]"}]
- Casual Joe Rogan banter style — NOT news anchor
- Include chapters array and thumbnail data

### TTS Engine (tts_engine.py)
- generate_dialogue_audio(dialogue_list) function
- Alternates between Jessica and co-host voice
- 0.3s silence gaps between speakers
- Returns timing markers for assembler

### Clip Fetcher (clip_fetcher.py)
- Add fetch_youtube_clips(channels, hours=24) — uses yt-dlp
- Download specific timestamp ranges: yt-dlp --download-sections "*START-END"
- Cache in downloads/yt_cache/
- Screenshot articles via playwright (install if needed: pip install playwright && playwright install chromium)

### Assembler (assembler.py)
- During dialogue: dark studio overlay with speaker labels
- During clips: full-screen YouTube clip with "Source: @Channel" attribution
- Lower-third ticker: "PROTOCOL PULSE | PULSE CHECK | BTC $XX,XXX"
- Crossfade transitions

### Daily Producer (daily_producer.py)
14-step pipeline: GATHER → TRANSCRIBE → SELECT → DOWNLOAD → SCREENSHOT → SCRIPT → TTS → ASSEMBLE → SHORTS → THUMBNAIL → CHAPTERS → PODCAST → NEWSLETTER → OUTPUT

### New Files
- thumbnail_gen.py: Pillow, 1280x720, headline + channel face + branding
- chapters.py: YouTube description format + FFmpeg chapter metadata
- podcast_feed.py: Extract audio to MP3, generate RSS XML
- newsletter_embed.py: HTML email with thumbnail + watch button via Resend

## TEST

```bash
cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --test
```

Expected output in output/test_YYYYMMDD_HHMMSS/:
- pulse_check_*.mp4 (dual-host audio, real or test clips)
- short_1.mp4, short_2.mp4, short_3.mp4
- thumbnail.png (1280x720)
- chapters.txt (timestamped)
- podcast.mp3 (audio only)
- script.json (dialogue arrays)

## GIT

```bash
git add -A && git commit -m "feat(video): Pulse Check V4 — dual-host, YouTube clips, thumbnails, chapters, podcast" && git push origin main
```

START CODING NOW. Build each file one at a time. Test as you go.
