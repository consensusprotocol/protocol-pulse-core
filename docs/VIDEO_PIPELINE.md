# Pulse Check Video Pipeline V5

## Architecture Overview

The Pulse Check pipeline produces a daily Bitcoin intelligence video from multiple sources. It runs entirely on Ultron (local GPU server) with episode metadata synced to Replit for the web frontend.

```
YouTube Channels ──┐
YouTube Search ────┤
Nostr Notes ───────┤──→ Transcription ──→ Grok Triage ──→ Claude Director
X/Twitter Posts ───┤        (Whisper)     (relevance)     (show planning)
X Spaces ──────────┘
                                               │
                                               ▼
    ┌──────────────────────────────────────────────────────┐
    │ Episode Assembly                                     │
    │  Intro bumper → Cold open → Story segments → Outro   │
    │  + Shorts (1080x1920) + Teaser (90s) + Thumbnail     │
    └──────────────────────────────────────────────────────┘
                                               │
                                               ▼
                                     Replit Sync (DB + JSON)
```

## Directory Structure

```
services/video_engine/
├── first_run.py              # Streamlined pipeline runner
├── daily_driver.py           # Full-featured orchestrator
├── run_daily.sh              # Cron entry point
├── local_whisper.py          # Whisper transcription
├── assembly/
│   ├── ffmpeg_ops.py         # FFmpeg wrapper functions
│   ├── local_assembler.py    # Horizontal video assembly
│   ├── episode_builder.py    # Master assembly orchestrator
│   ├── shorts_builder.py     # Vertical (9:16) shorts
│   ├── teaser_builder.py     # X teaser trailer
│   └── manifest_builder.py   # Assembly manifest creation
├── editorial/
│   ├── grok_triage.py        # Grok API: source relevance scoring
│   ├── claude_director.py    # Claude API: show planning
│   ├── clip_extractor.py     # Extract clips from source videos
│   ├── narration_generator.py # ElevenLabs TTS
│   └── schemas.py            # Pydantic models
├── graphics/
│   ├── motion_graphics.py    # Intro/outro bumpers, transitions
│   ├── thumbnail.py          # Episode thumbnails
│   └── waveform_viz.py       # Audio waveform visualization
├── sources/
│   ├── nostr_capture.py      # Nostr note fetcher
│   ├── spaces_listener.py    # X Spaces detector
│   └── tweet_screenshot.py   # Tweet card renderer
└── distribution/
    └── replit_sync.py        # Push metadata to Replit
```

## How to Run

### Manual run (production)
```bash
cd /home/ultron/protocol_pulse
source venv/bin/activate
python3 -m services.video_engine.first_run
```

### Test mode (fewer sources, faster)
```bash
python3 -m services.video_engine.first_run --test
```

### Sync to Replit
```bash
python3 -m services.video_engine.distribution.replit_sync
```

## Scheduler

Cron runs daily at 23:00 UTC (6:00 PM ET):

```
0 23 * * * /home/ultron/protocol_pulse/services/video_engine/run_daily.sh
```

After the pipeline completes, it automatically syncs to Replit.

## API Keys Required

| Key | Source | Used For |
|-----|--------|----------|
| `ELEVENLABS_API_KEY` | .env | TTS narration (Daniel voice) |
| `ANTHROPIC_API_KEY` | .env | Claude Director (show planning) |
| `XAI_API_KEY` | .env | Grok triage (relevance scoring) |

All keys are loaded from `.env` in the project root.

## Cost Estimates

Per episode (typical):
- **Whisper**: Free (local, base model)
- **Grok triage**: ~$0.05 (10K tokens in, 2K out)
- **Claude Director**: ~$0.08 (8K tokens in, 4K out)
- **ElevenLabs TTS**: ~$0.13 (~4,300 characters)
- **Total**: ~$0.26 per episode

## Output Files

Each episode creates:

```
data/episodes/YYYY-MM-DD/
├── final/
│   ├── pulse_check_YYYY-MM-DD.mp4       # Full episode (1920x1080)
│   ├── pulse_check_YYYY-MM-DD_audio.mp3  # Podcast audio
│   ├── pulse_check_YYYY-MM-DD_teaser.mp4 # X teaser (≤90s)
│   └── pulse_check_YYYY-MM-DD_thumb.png  # Thumbnail
├── shorts/
│   ├── short_00_YYYY-MM-DD.mp4           # Vertical short (1080x1920)
│   ├── short_01_YYYY-MM-DD.mp4
│   └── short_02_YYYY-MM-DD.mp4
├── manifest/
│   ├── show_plan.json                    # Claude Director output
│   └── assembly_manifest.json            # Assembly timeline
├── costs/
│   └── run_costs.json                    # Per-run cost breakdown
└── pipeline.log                          # Full run log
```

## Troubleshooting

### Pipeline fails at YouTube scan
- Check if `yt-dlp` is installed and up to date: `yt-dlp --version`
- The pipeline has a search fallback if channel scanning returns empty

### No clips extracted
- This is usually because Claude Director generates source_ids that don't match actual video IDs
- The pipeline handles this gracefully — it builds episodes with narration-only segments

### ElevenLabs fails
- Check API key: `echo $ELEVENLABS_API_KEY`
- Voice: Daniel (`onwK4e9ZLuTAKqWW03F9`), Model: `eleven_turbo_v2_5`

### Replit sync fails
- Check relay URL: `curl -s https://protocolpulse.replit.app/api/admin/exec`
- Token is hardcoded in `replit_sync.py`

### Check latest status
```bash
cat data/episodes/latest_status.json
```
