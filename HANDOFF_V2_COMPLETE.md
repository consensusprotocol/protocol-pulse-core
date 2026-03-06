# PROTOCOL PULSE — MASTER HANDOFF v2
# Generated: 2026-03-05 22:00 EST
# Session: 20+ hour marathon build session
# Drop this into a new Claude chat to restore FULL project context.

---

## 1. WHAT IS PROTOCOL PULSE

Protocol Pulse is an autonomous Bitcoin intelligence and media platform.
CEO: PBX (Consensus Protocol LLC, Naples FL)
Domain: protocolpulse.io (Replit Flask backend), articles.protocolpulse.io (Vercel Next.js)

Products:
- Daily "Pulse Check" video episodes (autonomous pipeline on Ultron GPU server)
- Article generation engine (Claude AI + Grok fact-checker, 1,479+ articles)
- Pulse Terminal API (premium intelligence dashboard, $19-$99/mo tiers)
- The Oracle (AI chat assistant with avatar on website)
- Cypherpunk'd podcast
- Live Intelligence System (real-time YouTube Live + X Spaces monitoring)
- Curated Mining (white-glove Bitcoin mining service)
- G'OLDS Nutrition (premium nutritional drinks, separate product)

Tech Stack:
- Ultron: 4x RTX 4090 GPU server, runs video pipeline, Whisper, Wav2Lip avatar, Remotion
- Replit: Flask API, PostgreSQL on Neon, Gunicorn, serves protocolpulse.io
- Vercel: Next.js frontend for articles.protocolpulse.io (glassmorphism cyberpunk design)
- Cloudflare: DNS, tunnels, caching
- GitHub: consensusprotocol/protocol-pulse-core (source of truth)

---

## 2. INFRASTRUCTURE

### Ultron GPU Server:
- SSH: `ssh ultron` (alias configured) or via ssh.protocolpulse.io with cloudflared proxy
- Relay: POST https://relay.protocolpulse.io/exec
  Body: {"token": "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552", "cmd": "..."}
  Headers: User-Agent: Mozilla/5.0 (REQUIRED — Cloudflare blocks default)
- Avatar: avatar.protocolpulse.io (port 8200)
- Claude Code: Always interactive mode in tmux:
  `tmux new-session -s NAME \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter`
- NEVER use -p flag. NEVER run parallel sessions on same repo.
- Use python3 urllib (not curl) for relay calls from Claude.ai sandbox.

### Replit:
- URL: protocolpulse.replit.app
- Relay: POST https://protocolpulse.replit.app/api/admin/exec (same token+cmd format)
- KNOWN ISSUE: Republish wipes dynamic files. bootstrap_github.py in app.py auto-pulls from GitHub on startup. BUT gunicorn doesn't always execute it.
- PLANNED: Migrate Flask to Ultron behind Cloudflare tunnel (medium-term fix).
- Stripe billing already integrated. Resend API key set for newsletters.

### GitHub: consensusprotocol/protocol-pulse-core
- All gospel docs, pipeline code, config in this repo
- Git push from Ultron (SSH keys configured), NOT from Replit

---

## 3. GOSPEL DOCUMENTS (14 total, ~7,000+ lines)

These are LAW. Every Claude Code session MUST read relevant docs before writing code.

### On Ultron ~/protocol_pulse/:
1. **PIPELINE_LAWS.md** (428 lines, 22 sections) — video pipeline rules, voices, encoding, 5-clip rule, channel daemon, ad-read filter
2. **PRODUCTION_DESIGN_LAWS.md** (326 lines) — research-backed visual/audio design, episode arc, PiP preview, face rule, anti-AI-detection, MrBeast-style pacing science
3. **CONTENT_INTELLIGENCE_LAWS.md** (480 lines) — brand ethos, node pulse, three threats (node decline, mining centralization, ETF hypothecation), content pillars, topic balance
4. **PULSE_TERMINAL_LAWS.md** (449 lines) — premium intelligence product bible, 4 tiers ($0/$19/$49/$99), API spec, dashboard UI, Stripe billing, competitive moat
5. **LIVE_INTELLIGENCE_LAWS.md** — real-time YouTube Live + X Spaces capture, Whisper chunked processing, live_signals.json
6. **MARKETING_STRATEGY_LAWS.md** (406 lines) — self-learning content engine, platform strategies, growth milestones (100→1K→5K→25K YouTube subs), revenue projections ($22.5K/mo at 12 months), Social SEO
7. **X_POSTING_LAWS.md** (221 lines) — platform algorithm rules, posting cadence, content mix, Nostr adaptation
8. **PRODUCT_BACKLOG.md** (100 lines) — 12 prioritized tasks across phases
9. **EXPANSION_SPEC_V22_V30.md** (693 lines) — V22-V30 roadmap
10. **HANDOFF_COMPLETE.md** — previous handoff (update with this doc)

### On Ultron ~/protocol_pulse/video_pipeline_v3/:
11. PIPELINE_FORENSIC_AUDIT.md
12. MASTER_PLAN_OF_ACTION.md
13. ARTICLE_PAGE_LAWS.md
14. PIPELINE_ELEVATION_SPEC.md

---

## 4. VIDEO PIPELINE (current state after marathon session)

Location: ~/protocol_pulse/video_pipeline_v3/ on Ultron

### Architecture:
- **channel_scanner.py** → scans 80 YouTube channels (4 tiers: Core Bitcoin, Adjacent/Macro, Tradfi, Mainstream)
- **channel_daemon** (cron */15) → continuous transcript archiving to data/channel_archive/ (42+ videos archived)
- **live_monitor.py** (cron */5) → detects YouTube Live streams from partner channels
- **spaces_monitor.py** (cron */5) → detects X Spaces from Bitcoin influencers
- **clip_selector.py** → intelligent scoring engine (0-100 per clip, data-driven)
- **clip_extractor.py** → downloads + extracts 30-60s moments with sentence boundary detection + quality enforcement (3Mbps min, 1.5Mbps reject)
- **script_writer.py** → Claude generates episode arc with segment tags [COLD_OPEN], [NARRATION:REACT], [NARRATION:SETUP], [DATA], [SOCIAL], [WARM]
- **tts_engine.py** → ElevenLabs voices with speed control
- **assembler.py** → FFmpeg + Remotion assembly (1800+ lines), PiP preview, cyberpunk bg, music mixing
- **daily_producer.py** → orchestrates everything, quality gate (85/100 threshold)

### Remotion Components (remotion/src/compositions/):
- CyberpunkBackground.tsx — animated loop background (particles, grid, scan line)
- WaveformVisualizer.tsx — heartbeat pulse animation with neon glow + traveling dot
- SocialCard.tsx — cyberpunk tweet cards with scanlines + pulse dot
- TitleCard.tsx — animated logo intro with EKG pulse
- LowerThird.tsx — alpha overlay for clip identification
- GlitchTransition.tsx — alpha channel transitions (1 second)

### Key Rules:
- 5 clips from 5 DIFFERENT channels per episode (HARD rule, production mode)
- Episode arc: cold open hook (no logo first) → clip1 → narration → clip2 → data → social → wrap → "Stay sovereign" outro
- PiP preview: 40% frame, right side, actual muted video (not static image), ONLY during SETUP segments
- Split-screen layout: narration left 55%, PiP right 40%
- Alpha transitions between EVERY segment with custom whoosh (assets/sfx/custom_whoosh.mp3)
- Background music from assets/music/ (34 tracks) at -20dB under narration, muted during partner clips
- Cyberpunk animated background on all narrator segments
- Tweet screenshots via Playwright (when URLs available)
- Sentence boundary detection for clip start/end (no mid-sentence cuts)
- Ad-read double gate with expanded patterns
- Clip quality: 3Mbps minimum, 1.5Mbps absolute floor
- Logo: max 3 appearances per episode (lower third on clips, outro only)
- AV sync: < 0.05s, Bitrate: > 5Mbps, Resolution: 1920x1080

### Voices:
- Host 1 (Female): Eryn — kdnRe2koJdOK4Ovxn2DI (speed 1.12x)
- Host 2 (Male): Mark — 1SM7GgM6IMuvQlz2BwM3 (speed 1.10x)
- BANNED: Gigi, Jessica, Nicole, Sarah, Matilda (all tested, all failed)
- PBX Professional Voice Clone: PENDING (recording at studio imminently)

### Voice Modes (Host 1):
- COLD_OPEN: stability 0.38, speed 1.12 (dramatic whisper, max 2/episode)
- NARRATION: stability 0.75, speed 1.12 (clear, confident)
- DATA: stability 0.70, speed 1.10 (authoritative)
- SOCIAL: stability 0.60, speed 1.12 (warm)
- WARM: stability 0.60, speed 1.10 (inviting, for wrap-up)

---

## 5. PULSE TERMINAL API

### Built (Phase 1 complete):
- routes_api_terminal.py (585 lines) — 5 endpoints with real data reads
- GET /api/v2/terminal/topics — topic velocity from daily_signals.json
- GET /api/v2/terminal/entities — entity mention tracking
- GET /api/v2/terminal/sentiment — market sentiment composite
- GET /api/v2/terminal/breaking — breaking news alerts
- GET /api/v2/terminal/live — real-time live stream data (NEW)
- Auth: X-API-Key header, tier-based rate limiting
- OpenAPI/Swagger documentation
- Stripe subscription flow (checkout → API key generation)
- Test key: pp-test-commander-001

### ISSUE: Terminal API returns 404 on Replit after republish
- Files pushed to Git but Replit bootstrap doesn't always execute
- bootstrap_github.py added to top of app.py but gunicorn may not trigger it
- FIX NEEDED: Migrate Flask to Ultron behind Cloudflare tunnel

---

## 6. LIVE INTELLIGENCE SYSTEM (NEW — built this session)

### Components:
- **utils/live_monitor.py** — detects YouTube Live streams from Tier 1+2 channels (cron */5)
- **utils/spaces_monitor.py** — detects X Spaces from Bitcoin influencers (cron */5)
- **utils/clip_scorer.py** — intelligent clip selection (topic velocity × engagement × novelty × authority × impact)
- **data/intelligence/live_signals.json** — real-time output consumed by pipeline + Terminal API

### X Accounts Monitored for Spaces:
@saylor, @APompliano, @LynAldenContact, @DocumentingBTC, @PeterMcCormack, @nataborelle, @PrestonPysh, @MartyBent, @stephanlivera, @david_eng_mba, @BitPaine

### Live detection already working:
- Swan Bitcoin "Bitcoin Price Live!" detected at 19:40
- Simply Bitcoin "Bitcoin Trapped at $74K or Ready for $500K+?" detected at 19:30

### PLANNED: X Spaces Quote-Tweet Strategy
When a high-impact moment is detected in a live Space:
1. Transcribe the quote via Whisper
2. Auto-draft quote tweet with the transcription + Protocol Pulse intelligence context
3. Quote-retweet the Space link to drive real-time listeners
4. Drop a full recap + best moments breakdown in the reply thread
5. Feed the quotes into the site dashboard as live flashcards (hyperlinked to Space)
6. Human approval for first 50 posts (batches of 10), then auto after <5% rejection rate

---

## 7. NEWSLETTER + SOCIAL AUTOMATION

### Newsletter:
- routes_newsletter_trigger.py built (dark-themed HTML digest with velocity bars)
- POST /api/newsletter/send triggers daily digest
- Resend API key configured on Replit
- PENDING: Welcome email for new signups, legacy subscriber import from consensusprotocol.org

### X/Twitter Automation:
- X_POSTING_LAWS.md defines strategy (5-8 posts/day, content mix ratios)
- Phoenix Engine built (not activated)
- PENDING: Batch approval flow → auto-post with quality gate

---

## 8. CHANNEL NETWORK

### 80 channels across 4 tiers:
- Tier 1 (Priority 1, 30 channels): Bitcoin Magazine, Simply Bitcoin, WBD, TFTC, Preston Pysh, The Bitcoin Layer, Swan Bitcoin, BTC Sessions, Stephan Livera, Bitcoin Audible, etc.
- Tier 2 (Priority 2, 32 channels): Real Vision, George Gammon, Coin Bureau, Pompliano, Ark Invest, Bankless, etc.
- Tier 3 (Priority 3, 11 channels): CNBC, Bloomberg, WSJ, Fox Business, Yahoo Finance — Bitcoin keyword filter
- Tier 4 (Priority 4, 7 channels): Joe Rogan, Lex Fridman, Tucker Carlson, PBD, All-In — Bitcoin keyword filter

### Channel daemon: */15 cron, archives transcripts to data/channel_archive/
- 42 videos archived so far, growing continuously
- Whisper transcription on 4090 GPU (17x realtime speed)

---

## 9. WHAT'S RUNNING ON ULTRON RIGHT NOW

### Active tmux sessions:
- autonomous-build: Production render in progress (scanning 106 videos)
- avatar: Wav2Lip avatar server (48+ hours uptime, healthy)

### Active cron jobs (15 total):
- Channel daemon: */15 (80 channels)
- Live monitor: */5 (YouTube Live detection)
- Spaces monitor: */5 (X Spaces detection)
- Oracle Briefing: daily 7 AM EST
- Pulse Check: daily 9 AM EST
- HeyGen Sarah: 3x daily (8 AM, 1 PM, 6 PM)
- PBX Weekly Report: Tue + Fri 10 AM
- Mining Intel: Wed + Sun 10 AM
- Various others (log rotation, image backfill, etc.)

### Production render in progress:
- First full 80-channel network scan (~2 hours, one-time cost)
- Future renders: 15-20 minutes (cached transcripts)
- All 10 visual fixes applied
- Live signals integration active

---

## 10. PENDING ITEMS FROM PBX

### Immediate:
- PBX ElevenLabs Professional Voice Clone (recording at studio, ~4 hours)
- Watch latest production video and provide feedback
- Republish Replit (Terminal API + Newsletter need deployment fix)
- YouTube OAuth setup (Google Cloud project → enable API → run setup script)

### This Week:
- X Spaces quote-tweet strategy (50-post curation in batches of 10)
- Pulse Terminal Phase 2 (React dashboard on Vercel)
- Marketing engine code build (utils/marketing_engine.py — the self-learning scorer)
- Newsletter activation (first send)
- Article page final 10% (Cloudflare proxy, SEO meta)

### Phase Next:
- Migrate Flask from Replit to Ultron/VPS behind Cloudflare tunnel
- 40 additional 4090 GPUs coming online (massive Whisper parallelization)
- Sat Stacker game integration (existing Mario-style game + Lightning rewards)
- Avatar instant-response mode (Remotion wave default, avatar on button press)
- Gemini vision camera feature (real-time Bitcoin device setup assistance)
- Phone call briefings via Twilio + ElevenLabs
- Mobile UI forensic audit

---

## 11. GROWTH MILESTONES (from MARKETING_STRATEGY_LAWS.md)

| Metric | Month 1 | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|----------|
| YouTube subs | 100 | 1,000 | 5,000 | 25,000 |
| X followers | 500 | 2,500 | 10,000 | 50,000 |
| Newsletter | 200 | 1,000 | 5,000 | 15,000 |
| Terminal paid | 0 | 5 | 50 | 200 |
| Revenue/mo | $0 | $750 | $5,500 | $22,500 |

---

## 12. CRITICAL RULES FOR NEW CHAT AGENT

- ALWAYS read relevant gospel docs before writing code
- NEVER use Claude Code -p flag (always interactive mode in tmux)
- NEVER run parallel Claude Code sessions on same repo
- ALWAYS run regression_test.sh before committing
- NEVER assign PBX manual tasks — do everything autonomously
- One comprehensive prompt > multiple small prompts
- Use python3 urllib (not curl) for relay calls from Claude.ai sandbox
- Ultron relay REQUIRES User-Agent: Mozilla/5.0 header
- Git push from Ultron, not Replit
- Cross-verify code with Gemini 2.5 Pro (not Grok — Grok = article fact-checker only)
- Triple-verify every feature before claiming done (RIGOR PROTOCOL)

---

## 13. KEY FILES + PATHS

### Ultron:
- ~/protocol_pulse/ — main repo root
- ~/protocol_pulse/video_pipeline_v3/ — video pipeline
- ~/protocol_pulse/video_pipeline_v3/channels.yaml — 80 channel configs
- ~/protocol_pulse/video_pipeline_v3/config/feature_flags.json — all feature toggles
- ~/protocol_pulse/video_pipeline_v3/assets/sfx/custom_whoosh.mp3 — PBX's custom transition sound
- ~/protocol_pulse/video_pipeline_v3/assets/music/ — 34 music tracks
- ~/protocol_pulse/video_pipeline_v3/assets/logo_protocol_pulse.png — 800x800 logo
- ~/protocol_pulse/video_pipeline_v3/data/channel_archive/ — transcript archive
- ~/protocol_pulse/video_pipeline_v3/data/intelligence/ — live signals, daily signals, sentiment, entities
- ~/protocol_pulse/video_pipeline_v3/remotion/ — all Remotion compositions

### Replit:
- /home/runner/workspace/ — Flask app root
- routes.py — 8,472-line main routes file
- routes_api_v2.py — V2 API
- routes_api_terminal.py — Terminal API (needs deployment fix)
- templates/oracle.html — The Oracle chat page

### Key API Keys (in Replit secrets):
- ELEVENLABS_API_KEY, HEYGEN_API_KEY, RESEND_API_KEY, STRIPE_SECRET_KEY
- ANTHROPIC_API_KEY (for Claude), GEMINI_API_KEY
- YOUTUBE_DATA_API_KEY (for Sponsor Agent, not yet used)

### HeyGen Avatars:
- Sarah: d259c335741f4fc0b061e04c59388b4e ($1/min) — Oracle Briefings
- PBX: 3be8ed14b0954b898f4127836c21f6cc ($2/min) — Weekly PBX Report

---

## 14. TONIGHT'S SESSION — COMPLETE BUILD LOG

### Commits (chronological):
1. V11-V18 pipeline features (voice, dedup, padding, quality gates, analytics, alerts, fast-test)
2. Remotion 6 components (CyberpunkBg, Waveform, SocialCard, TitleCard, LowerThird, GlitchTransition)
3. Overnight rebuild (Eryn+Mark voices, episode arc, PiP preview, sound design)
4. 80-channel expansion (18→80 across 4 tiers)
5. Newsletter engine (daily HTML digest via Resend)
6. Terminal API Phase 1 (5 endpoints, auth, rate limiting, OpenAPI docs, Stripe)
7. Node Pulse monitor (Bitnodes API)
8. Playwright tweet screenshots
9. Channel intelligence daemon (*/15 cron, persistent archive)
10. 10 video production fixes (layout, sentence boundaries, tweet mismatch, music, outro)
11. 16 video production fixes (earlier round)
12. Live stream monitor (YouTube Live detection)
13. X Spaces monitor (influencer account detection)
14. Intelligent clip scorer (data-driven 0-100 scoring)
15. Live signals → pipeline integration
16. PRODUCTION_DESIGN_LAWS.md (326 lines, research-backed)
17. PULSE_TERMINAL_LAWS.md (449 lines, product bible)
18. CONTENT_INTELLIGENCE_LAWS.md addendums (Node Pulse, Three Threats, brand ethos)
19. MARKETING_STRATEGY_LAWS.md (406 lines, self-learning engine)
20. PRODUCT_BACKLOG.md (12 tasks prioritized)
21. HANDOFF_COMPLETE.md (for chat transitions)
22. Next.js glassmorphism frontend deployed to Vercel
23. Cloudflare redirect rules configured

### Gospel doc count: 14 documents, ~7,000+ lines of codified rules
### Total commits this session: 30+
### Total renders: 8 (progressive quality improvement, latest 94/100)

---

*For detailed code context, fetch gospel docs from GitHub:*
*https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/{DOCUMENT_NAME}*

*Available docs: PIPELINE_LAWS.md, PRODUCTION_DESIGN_LAWS.md, CONTENT_INTELLIGENCE_LAWS.md,*
*PULSE_TERMINAL_LAWS.md, LIVE_INTELLIGENCE_LAWS.md, MARKETING_STRATEGY_LAWS.md,*
*X_POSTING_LAWS.md, PRODUCT_BACKLOG.md, HANDOFF_COMPLETE.md*
