# PROTOCOL PULSE — MASTER HANDOFF DOCUMENT
# Generated: 2026-03-05 19:36
# Drop this into a new Claude chat to restore FULL project context.
# Also fetch gospel docs from GitHub for detailed rules.

---

## 1. WHAT IS PROTOCOL PULSE

Protocol Pulse is an autonomous Bitcoin intelligence and media platform.
CEO: PBX (Consensus Protocol LLC, Naples FL)
Domain: protocolpulse.io (Replit Flask backend), articles.protocolpulse.io (Vercel Next.js)

Products:
- Daily "Pulse Check" video episodes (autonomous pipeline on Ultron GPU server)
- Article generation engine (Claude AI + Grok fact-checker, 1,479+ articles)
- Pulse Terminal API (premium intelligence dashboard, $19-99/mo tiers)
- The Oracle (AI chat assistant with avatar on website)
- Cypherpunk'd podcast
- Curated Mining (white-glove Bitcoin mining service)
- G'OLDS Nutrition (premium nutritional drinks, separate product)

Tech Stack:
- Ultron: 4x RTX 4090 GPU server, runs video pipeline, Whisper, Wav2Lip avatar, Remotion
- Replit: Flask API, PostgreSQL on Neon, serves protocolpulse.io
- Vercel: Next.js frontend for articles.protocolpulse.io
- Cloudflare: DNS, tunnels, caching
- GitHub: consensusprotocol/protocol-pulse-core (source of truth)

## 2. INFRASTRUCTURE

Ultron GPU Server:
- SSH: ssh ultron (alias configured) or via ssh.protocolpulse.io with cloudflared proxy
- Relay: POST https://relay.protocolpulse.io/exec
  Body: {"token": "REDACTED-stored-in-env", "cmd": "..."}
  Headers: User-Agent: Mozilla/5.0 (required, Cloudflare blocks default)
- Avatar: avatar.protocolpulse.io (port 8200)
- Claude Code: Always use interactive mode in tmux:
  tmux new-session -s NAME \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
- NEVER use -p flag. NEVER run parallel sessions on same repo.

Replit:
- URL: protocolpulse.replit.app
- Relay: POST https://protocolpulse.replit.app/api/admin/exec (same token+cmd format)
- KNOWN ISSUE: Republish wipes files. bootstrap_github.py auto-pulls from GitHub on startup.
- Medium-term: migrate Flask to Ultron behind Cloudflare tunnel.

GitHub: consensusprotocol/protocol-pulse-core
- All gospel docs, pipeline code, config in this repo
- Git push from Ultron (SSH keys configured)

## 3. GOSPEL DOCUMENTS (13 total, ~6000+ lines)

These are the LAW. Every Claude Code session must read relevant docs before writing code.

On Ultron ~/protocol_pulse/:
1. PIPELINE_LAWS.md (428 lines, 22 sections) — video pipeline rules
2. PRODUCTION_DESIGN_LAWS.md (326 lines) — research-backed visual/audio design
3. CONTENT_INTELLIGENCE_LAWS.md (480 lines) — brand ethos, node pulse, three threats
4. PULSE_TERMINAL_LAWS.md (449 lines) — premium intelligence product bible
5. LIVE_INTELLIGENCE_LAWS.md — real-time stream capture system
6. X_POSTING_LAWS.md (221 lines) — social media strategy
7. PRODUCT_BACKLOG.md (100 lines) — 12 tasks prioritized by phase
8. EXPANSION_SPEC_V22_V30.md (693 lines) — V22-V30 roadmap

On Ultron ~/protocol_pulse/video_pipeline_v3/:
9. PIPELINE_FORENSIC_AUDIT.md — bug inventory
10. MASTER_PLAN_OF_ACTION.md — V11-V21 execution plan
11. PIPELINE_ELEVATION_SPEC.md — architecture spec
12. ARTICLE_PAGE_LAWS.md — article system rules
13. AGENT_HANDOFF_NOTE.md — handoff procedures

## 4. VIDEO PIPELINE (current state)

Location: ~/protocol_pulse/video_pipeline_v3/ on Ultron

Architecture:
- channel_scanner.py → scans 80 YouTube channels (4 tiers)
- channel_daemon (cron */15) → continuous transcript archiving to data/channel_archive/
- clip_selector.py → intelligent scoring engine (0-100 per clip)
- clip_extractor.py → downloads + extracts 30-60s moments with sentence boundary detection
- script_writer.py → Claude generates episode arc with segment tags [COLD_OPEN], [NARRATION], etc.
- tts_engine.py → ElevenLabs voices: Eryn (female, kdnRe2koJdOK4Ovxn2DI), Mark (male, 1SM7GgM6IMuvQlz2BwM3)
- assembler.py → FFmpeg + Remotion assembly (1800+ lines)
- daily_producer.py → orchestrates everything, quality gate (85/100 threshold)

Remotion Components (remotion/src/compositions/):
- CyberpunkBackground.tsx — animated loop background
- WaveformVisualizer.tsx — heartbeat pulse animation
- SocialCard.tsx — cyberpunk tweet cards
- TitleCard.tsx — animated logo intro
- LowerThird.tsx — alpha overlay for clip identification
- GlitchTransition.tsx — alpha channel transitions

Key Rules:
- 5 clips from 5 different channels per episode (HARD rule, production mode)
- Voices: Eryn (speed 1.12x) + Mark (speed 1.10x), 4 voice modes
- Episode arc: cold open hook → clip1 → narration → clip2 → data → social → wrap
- Logo: max 3 appearances per episode (title card, lower third, outro)
- AV sync: < 0.05s, Bitrate: > 5Mbps, Resolution: 1920x1080
- Custom whoosh: assets/sfx/custom_whoosh.mp3
- 34 music tracks: assets/music/
- regression_test.sh must pass before any commit

## 5. ACTIVE CRON JOBS ON ULTRON
```
# Protocol Pulse — Automated Pipelines
# Updated: 2026-03-02

# Oracle Briefing — Daily at 7 AM EST (12 UTC)
0 12 * * * cd /home/ultron/protocol_pulse/oracle_briefing && /usr/bin/python3 briefing_producer.py >> /home/ultron/protocol_pulse/logs/oracle_briefing.log 2>&1

# Medley Engine V2 — Daily at 8 AM EST (13 UTC)
0 13 * * * LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:/usr/local/cuda/lib64" /home/ultron/protocol_pulse/medley_engine_v2/daily_run.sh >> /tmp/medley_daily.log 2>&1

# Pulse Check V4 — Daily at 9 AM EST (14 UTC)
0 14 * * * cd /home/ultron/protocol_pulse/video_pipeline_v3 && /usr/bin/python3 daily_producer.py >> /home/ultron/protocol_pulse/logs/pulse_check.log 2>&1

# Mining Intel — Twice weekly (Wed + Sun at 10 AM EST = 15 UTC)
0 15 * * 3,0 cd /home/ultron/protocol_pulse/mining_intel && /usr/bin/python3 mining_intel_scheduler.py >> /home/ultron/protocol_pulse/logs/mining_intel.log 2>&1

# Image Backfill — Weekly Monday 3 AM EST (08 UTC)
0 8 * * 1 cd /home/ultron/protocol_pulse && /usr/bin/python3 scripts/image_backfill_pexels.py >> /home/ultron/protocol_pulse/logs/image_backfill.log 2>&1

# Spaces Scraper — Check for live spaces every 15 minutes
*/15 * * * * /usr/bin/python3 main.py --check >> /home/ultron/protocol_pulse/logs/spaces_scraper.log 2>&1

# Log rotation — Weekly (Sunday midnight UTC)
0 0 * * 0 find /home/ultron/protocol_pulse/logs -name "*.log" -size +50M -exec truncate -s 0 {} \;

# Pulse Check Video Pipeline V5 — Daily at 6 PM EST (23 UTC)
0 23 * * * /home/ultron/protocol_pulse/services/video_engine/run_daily.sh >> /home/ultron/protocol_pulse/logs/video_pipeline.log 2>&1

# HeyGen Oracle Briefings — Sarah (3x/day)
# Morning: 8 AM EST (13 UTC)
0 13 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/heygen_briefing.py --type morning >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1
# Midday: 1 PM EST (18 UTC)
0 18 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/heygen_briefing.py --type midday >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1
# Evening: 6 PM EST (23 UTC)
30 23 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/heygen_briefing.py --type evening >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1

# PBX Weekly Report — Tuesday + Friday at 10 AM EST (15 UTC)
0 15 * * 2,5 cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/pbx_report.py >> /home/ultron/protocol_pulse/logs/pbx_report.log 2>&1
*/15 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/channel_daemon.py >> logs/channel_daemon.log 2>&1
*/5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/live_monitor.py >> logs/live_monitor.log 2>&1
```

## 6. TMUX SESSIONS
```
autonomous-build: 1 windows (created Thu Mar  5 18:55:15 2026)
avatar: 1 windows (created Tue Mar  3 14:23:18 2026)
```

## 7. RECENT GIT LOG
```
824a38f fix: live_monitor filter — only detect currently broadcasting streams
9b9d00b feat: intelligent clip selection engine — data-driven scoring
67e97ab feat: Terminal /live endpoint — real-time stream intelligence
c8bd294 feat: live stream monitor — detect YouTube Live + classify in real-time
5a6e2c2 docs: LIVE_INTELLIGENCE_LAWS.md — real-time stream intelligence system
99163ca feat: bootstrap_github.py — auto-pull Terminal + Newsletter on startup
28fd23b deploy: register Terminal + Newsletter blueprints in app.py
0eae178 deploy: Newsletter trigger + config + intelligence data for Replit
2cf4fe9 deploy: Terminal API to repo root for Replit
1efc4a4 docs: PRODUCT_BACKLOG.md — full task queue from PBX session
68ff893 fix: 16 PBX video pipeline fixes — all issues from production review
80909c9 feat: Terminal API OpenAPI 3.0.3 spec + Swagger UI docs
b34e78e feat: Terminal API Phase 1 — real data, entity tracker, sentiment, rate limiting
f9b92af feat: daily newsletter engine with intelligence digest
a29b40a feat: expand channel network 18 → 80 channels across 4 tiers
8b8522c docs: PULSE_TERMINAL_LAWS.md — premium intelligence terminal product bible
8a4ddf0 feat: Follow-up build — 5 tasks complete
52872e6 feat: Overnight Build — Remotion rebuild, voice swap, episode arc, PiP, sound design
f750f0f docs: Sections 21-22 — channel intelligence daemon + 5-clip rule
2c2a335 docs: Section 20 — Eryn + Mark approved voices, 5 voices banned
```

## 8. WHAT'S RUNNING / IN PROGRESS

- 10-fix video session: fixing clip cuts, tweet mismatch, music wiring, layout, etc.
- Channel daemon: scanning 80 channels every 15 min
- Live stream monitor: detecting YouTube Live every 5 min
- Avatar server: Wav2Lip on 4090, healthy
- Intelligent clip scorer: deployed, data-driven selection
- Pulse Terminal API: built but Replit bootstrap issue (migrate to Ultron planned)
- Newsletter engine: built, needs Replit working to activate

PENDING FROM PBX:
- PBX ElevenLabs Professional Voice Clone (recording in ~4-5 hours)
- YouTube OAuth setup (create Google Cloud project, enable API, run setup script)
- Telegram bot already configured

KEY VOICES:
- Host 1 (Female): Eryn — kdnRe2koJdOK4Ovxn2DI (speed 1.12x)
- Host 2 (Male): Mark — 1SM7GgM6IMuvQlz2BwM3 (speed 1.10x)
- BANNED: Gigi, Jessica, Nicole, Sarah, Matilda
- HeyGen Sarah: d259c335741f4fc0b061e04c59388b4e ($1/min)
- HeyGen PBX: 3be8ed14b0954b898f4127836c21f6cc ($2/min)


## 9. CRITICAL RULES FOR NEW CHAT AGENT

- ALWAYS read relevant gospel docs before writing code
- NEVER use Claude Code -p flag (always interactive mode)
- NEVER run parallel Claude Code sessions on same repo
- ALWAYS run regression_test.sh before committing
- NEVER assign PBX manual tasks — do everything autonomously
- One comprehensive prompt > multiple small prompts
- Use python3 urllib (not curl) for relay calls from Claude.ai sandbox
- Ultron relay requires User-Agent: Mozilla/5.0 header
- Git push from Ultron, not Replit
- Cross-verify code with Gemini 2.5 Pro, not Grok (Grok = article fact-checker only)
