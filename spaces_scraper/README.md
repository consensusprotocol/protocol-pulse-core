# Protocol Pulse — X Spaces Scraper

Real-time sentiment intelligence from live Bitcoin X Spaces.

## ⚠️ Legal Disclaimer

This tool is intended **strictly for personal research and analysis** of publicly accessible audio streams. It does NOT:
- Store or redistribute raw audio (transcripts only)
- Create fake accounts or impersonate users
- Violate user privacy (it only processes public Spaces)

Use responsibly. Respect X's rate limits. Do not use for commercial redistribution of content. Users assume full responsibility for compliance with X's Terms of Service and applicable laws.

## Architecture

```
SpaceDetector → AudioCapture (HLS) → RealtimeTranscriber (Whisper/GPU) → SentimentAnalyzer (Gemini)
                                                                        ↓
                                                          FastAPI REST API (port 8210)
```

## Detection Strategy

Tries three approaches in order:
1. **X API v2** — if `TWITTER_BEARER_TOKEN` is set
2. **Guest Token + GraphQL** — no credentials required, searches for live Bitcoin spaces
3. **Playwright** — headless Chromium fallback for monitoring specific accounts

## Setup

```bash
cd ~/protocol_pulse/spaces_scraper
pip install -r requirements.txt
playwright install chromium
```

Environment variables needed:
- `GEMINI_API_KEY` — Gemini API key for sentiment analysis
- `TWITTER_BEARER_TOKEN` — (optional) X API v2 bearer for better detection

## Running

```bash
# Full pipeline
python3 main.py

# 60-second integration test
python3 main.py --test

# API server only (no live capture)
python3 main.py --api-only

# Test detector only
python3 detector.py --test

# Test Whisper transcriber
python3 transcriber.py --test
```

## API Endpoints (port 8210)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health + uptime stats |
| GET | `/spaces/active` | Currently monitored live spaces |
| GET | `/spaces/feed` | Latest transcript chunks |
| GET | `/spaces/sentiment` | Aggregate rolling sentiment |
| GET | `/spaces/{id}/transcript` | Full transcript for a space |
| GET | `/spaces/{id}/sentiment` | Per-space sentiment detail |
| POST | `/spaces/force-scan` | Trigger immediate detection scan |
| GET | `/stats` | Internal performance stats |

## Whisper Performance (RTX 4090)

Expected throughput with `large-v3` model:
- 5s audio segment → transcribed in <0.5s (>10x realtime)
- Model stays loaded in GPU VRAM between segments
- VAD filter skips silence automatically

## External Access

`spaces.protocolpulse.io` → tunneled to `localhost:8210` via Cloudflare.

## Configuration

See `config.py` for all tunable parameters:
- `TARGET_ACCOUNTS` — accounts to monitor for live Spaces
- `DETECTOR_POLL_INTERVAL` — polling frequency (default: 60s)
- `MAX_CONCURRENT_SPACES` — max parallel captures (default: 2)
- `SENTIMENT_ANALYSIS_INTERVAL` — Gemini call frequency (default: 30s)
- `TRANSCRIPT_WINDOW_MINUTES` — rolling window for sentiment context (default: 5m)
