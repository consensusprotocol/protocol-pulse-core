# PROTOCOL PULSE — VIDEO PIPELINE CONTEXT
# Complete system state for autonomous Claude Code build
# Updated: March 3, 2026

## WHAT IS THE VIDEO PIPELINE

"Pulse Check" is a daily Bitcoin intelligence video that aggregates the best moments from 
14+ Bitcoin YouTube channels, notable X posts, Nostr notes, and X Spaces audio — all into 
one cinematic daily brief with world-class ElevenLabs narration and motion graphics.

NO ONE ELSE DOES THIS. This is the niche: "Bitcoin's best moments, every day, in one place."

## INFRASTRUCTURE

### Ultron (WHERE THIS RUNS)
- Path: /home/ultron/protocol_pulse/
- 2x NVIDIA RTX 4090 (48GB total VRAM)
- Python 3.10 (SadTalker venv for ML deps)
- ffmpeg, yt-dlp, faster-whisper 1.2.1, moviepy 2.2.1, Pillow 10.4
- Playwright 1.58.0 (for browser automation / screenshots)
- websocket-client, websockets (for Nostr relay connections)

### Replit (FRONTEND — DO NOT MODIFY IN THIS SESSION)
- Flask app at protocolpulse.replit.app
- Templates, routes, DB
- Relay: POST https://protocolpulse.replit.app/api/admin/exec
  Token: 581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552

### API Keys Available (in env vars)
- ANTHROPIC_API_KEY — Claude for editorial direction
- ELEVENLABS_API_KEY — TTS narration
- XAI_API_KEY — Grok for triage
- TWITTER_BEARER_TOKEN — X API v2 read access
- TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET — full X API

### GitHub
- Repo: consensusprotocol/protocol-pulse-core (SSH configured)
- RULE: git commit + push after EVERY phase

## EXISTING CODE (48 FILES ALREADY BUILT)

### Source Ingestion (services/video_engine/sources/)
- youtube_scanner.py (293 lines) — scans channels via yt-dlp, downloads audio, sends to Whisper
- tweet_monitor.py (157 lines) — fetches notable tweets via Twitter API v2 Bearer token
- tweet_card_renderer.py (206 lines) — renders branded 1920x1080 tweet images with Pillow
- spaces_monitor.py (36 lines) — SKELETON ONLY, returns []
- market_data.py (160 lines) — market data for show context
- bundle_assembler.py (144 lines) — bundles all source data

### Editorial Pipeline (services/video_engine/editorial/)
- grok_triage.py — Stage 1: Grok scans transcripts, scores candidates, flags ads/sponsors
- clustering.py — Stage 1.5: groups related stories, deduplicates
- claude_director.py — Stage 2: Claude writes complete ShowPlanV2 with narration scripts
- clip_extractor.py — Precision clip cuts with sentence boundary validation
- narration_generator.py — ElevenLabs TTS with emotion-aware voice settings
- qa_reviewer.py — QA validation
- schemas.py — Pydantic models for all data contracts (TriageOutput, ShowPlanV2, etc.)

### Assembly (services/video_engine/assembly/)
- manifest_builder.py — creates timeline manifest
- ultron_assembler.py — calls Ultron API for video assembly (BROKEN: points to video.protocolpulse.io which doesn't exist)
- post_assembly_qa.py — validates final video
- distribution_pack.py — generates distribution variants

### Orchestration (services/video_engine/)
- daily_driver.py — Master orchestrator (18-step pipeline)
- pulse_check_ultron.py — Ultron-side version with PARTNER_CHANNELS and prompts
- daily_scheduler.py — cron-like scheduler
- ultron_client.py — HTTP client (BROKEN: points to video.protocolpulse.io)

### Other Services
- services/nostr_service.py — connects to Nostr relays, fetches notes
- services/nostr_signal_service.py — tracks 7 Nostr OGs with scoring
- services/x_service.py — X/Twitter posting (tweepy)
- services/elevenlabs_service.py — TTS wrapper

## 14 PARTNER YOUTUBE CHANNELS
(from config/partner_channels.json)
Bitcoin Magazine, Simply Bitcoin, The Bitcoin Layer, Coin Bureau, Anthony Pompliano,
Swan Bitcoin, Robert Breedlove, Preston Pysh, What Bitcoin Did, Stephan Livera,
TFTC, Bitcoin Fundamentals, Natalie Brunell, BTC Sessions

## 28 MONITORED X ACCOUNTS
(from data/supported_sources.json)
Saylor, Lyn Alden, Jeff Booth, Preston Pysh, Saifedean, Breedlove, Jack Dorsey,
Elizabeth Stark, Adam Back, Pieter Wuille, Jameson Lopp, Matt Odell, Pierre Rochard,
Marty Bent, Marshall Long + 13 more

## 7 NOSTR PUBKEYS
Saylor, Dorsey, Matt Odell, + 4 more (with npub/hex pubkeys in supported_sources.json)

## WHAT HAS NEVER WORKED
1. Pipeline has NEVER run end-to-end — episodes/ directory is empty
2. ultron_client.py points to video.protocolpulse.io which doesn't exist
3. ultron_assembler.py calls an HTTP API that doesn't exist
4. No video assembly actually happens — need to use moviepy/ffmpeg locally
5. No motion graphics, transitions, lower thirds, or intro/outro bumpers
6. Spaces monitor is a skeleton
7. No Nostr post screenshot capability
8. No X post screenshot capability  
9. No audio waveform animation for clips
10. No thumbnail generation

## VOICE SETTINGS
- Oracle voice: Jessica (cgSgspJ2msm6clMCkdW9) — for Oracle avatar only
- Pulse Check narrator: Use "Adam" or "Josh" voice from ElevenLabs — check available voices
- Emotion-aware settings already defined in narration_generator.py

## SHOW FORMAT
(from claude_director.py system prompt)
1. COLD OPEN (15 sec) — tease today's stories
2. LEAD STORY (2-3 min) — most important story
3. FOLLOW STORY (1.5-2 min) — second story
4. SIGNAL vs NOISE (30 sec) — 1 signal, 1 noise, 1 wildcard
5. QUICK HITS (1-2 min) — rapid fire smaller stories
6. COMMUNITY PULSE (30 sec) — tweets, Nostr, reactions
7. OUTRO (10 sec) — "Stay sovereign"

Target: 5-8 minutes total. 7 pieces of daily content:
- 1 full YouTube episode
- 1 X teaser trailer
- 5 vertical shorts

## DESIGN STANDARDS
- Background: #0a0f0a (near black)
- Primary accent: #CC2222 (PP red)
- Fonts: Space Mono for titles, sans-serif for body
- Lower thirds: frosted glass effect, red accent line
- Transitions: clean cuts with 3-frame cross-dissolve, not flashy
