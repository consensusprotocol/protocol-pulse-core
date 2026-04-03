# Protocol Pulse — Claude Code Constitution

## Project
Protocol Pulse (protocolpulse.io) — autonomous Bitcoin intelligence platform.
Flask/Python backend on Ultron (AMD EPYC 9R14, 4x RTX 4090, 128GB RAM, Ubuntu 24.04).
Served by Waitress on port 5000 via Cloudflare tunnel.

## Architecture
```
core/app.py                    — Flask app entry point
core/routes_admin.py           — Admin endpoints
core/routes_api.py             — API endpoints  
core/routes_auth.py            — Auth + Stripe
core/routes_pages.py           — Page rendering
services/                      — Business logic (tweet_machine, morning_brief, etc.)
video_pipeline_v3/             — Video production pipeline (SPLIT into modules)
  assembler.py                 — THIN orchestrator (<1,800 lines) — DO NOT add logic here
  render_narrator.py           — PBX narration scenes
  render_clip.py               — Partner channel clip scenes
  render_social.py             — Tweet cards + Nostr signal
  render_intro_outro.py        — Intro/outro/cold open
  render_data.py               — Charts + data overlays
  audio_master.py              — LUFS normalization, music mixing
  transitions.py               — Crossfades between segments
  lower_thirds.py              — Branded overlays
```

## Commands
```bash
# Start website
cd ~/protocol_pulse/core && python3 -m waitress --port=5000 --threads=4 app:app

# Test render
cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --test --no-resume

# Fire tweet
cd ~/protocol_pulse && python3 services/tweet_machine.py

# Refresh brief
cd ~/protocol_pulse && python3 services/morning_brief.py

# Check health
curl -s http://localhost:5000/health
```

## Coding Standards
- Python 3.10+, Flask blueprints
- All commits: git add + commit + push (NEVER leave uncommitted .py files)
- Syntax check every .py edit: python3 -m py_compile <file>
- Git repo: consensusprotocol/protocol-pulse-core

## INVIOLABLE RULES
- NEVER print .env contents or expose API keys
- NEVER sed .env files — use nano
- NEVER start avatar_server.py (HeyGen broken, wastes 6GB RAM)
- NEVER export ANTHROPIC_API_KEY before CC
- NEVER force push to git
- NEVER add logic to assembler.py — use the split modules
- AUDIT-FIRST: Read files before changing them
- TRIPLE-VERIFY: Test output, test from different angle, confirm live
- Waitress serves port 5000. Gunicorn is RETIRED.
- Ollama models auto-unload after 5 min idle
- All time references in Eastern Time (ET) for PBX
- Video pipeline: read PIPELINE_LAWS.md before touching any pipeline file

## When Compacting
Preserve: list of modified files, current test status, active render status, any errors encountered.
