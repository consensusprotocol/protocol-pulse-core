# Pulse Check Video Pipeline v3

MMA-Central-style daily Bitcoin news video generator.

## Quick Start

```bash
cd ~/protocol_pulse/video_pipeline_v3

# Generate default style video
python3 daily_run.py --output output/pulse_check.mp4

# Generate breaking news style
python3 daily_run.py --style breaking --output output/breaking.mp4
```

## Pipeline Steps

1. **Script Generation** — Claude API narration script (falls back to curated samples)
2. **TTS Audio** — ElevenLabs voice (falls back to gTTS)
3. **Clip Fetching** — Pexels B-roll (falls back to FFmpeg-generated visuals)
4. **Assembly** — FFmpeg filter_complex compositing with branded assets
5. **Verification** — ffprobe checks for codec, resolution, duration, A/V sync
6. **Vertical Shorts** — Auto-generated 9:16 shorts from each segment

## Output Specs

- **Horizontal**: 1920x1080, H.264, AAC 44100Hz stereo, 30fps, 90-180s
- **Vertical Shorts**: 1080x1920, H.264, AAC, 15-60s each

## Project Structure

```
daily_run.py          # Master orchestrator
script_writer.py      # Claude/sample narration scripts
tts_engine.py         # ElevenLabs/gTTS voice generation
clip_fetcher.py       # Pexels/FFmpeg visual generation
assembler.py          # FFmpeg video assembly
shorts_cutter.py      # Vertical short generation
create_assets.py      # One-time asset creation
relay.py              # Replit relay helper
config.yaml           # Configuration
assets/               # Branded transitions, intro, outro
output/               # Finished videos
output/shorts/        # Vertical shorts
```

## Cron (Daily at 2PM UTC)

```
0 14 * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_run.py >> logs/daily.log 2>&1
```

## API Keys (via env or Replit relay)

- `ANTHROPIC_API_KEY` — Claude script generation
- `ELEVENLABS_API_KEY` — TTS voice
- `PEXELS_API_KEY` — B-roll video clips
- `XAI_API_KEY` — Grok triage scoring

All have local fallbacks — pipeline works without any API keys.
