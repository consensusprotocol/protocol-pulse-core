# PROTOCOL PULSE — NEW AGENT HANDOFF (FINAL)
# Generated: 2026-03-05 23:45 EST
# Continuation of 20+ hour marathon build session
# THIS IS THE DEFINITIVE HANDOFF. Use this document, not earlier versions.

---

## READ THESE FIRST (from GitHub):
- https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/HANDOFF_V2_COMPLETE.md (full technical context)
- https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/PROTOCOL_PULSE_OVERVIEW.md (product vision + mission)
- https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/LIVE_SPACES_PULSE_LAWS.md (newest feature spec)

---

## WHAT'S HAPPENING RIGHT NOW ON ULTRON

### tmux sessions:
- `autonomous-build`: IDLE — all 5 phases complete, ready for next prompt
- `avatar`: Running 2+ days, Wav2Lip on 4090, healthy

### Active cron jobs (15 total, running automatically):
- Channel daemon (*/15): scanning 80 channels, 42 videos archived, 9 topics tracked
- Live monitor (*/5): YouTube Live detection (Swan Bitcoin currently live)
- Spaces monitor (*/5): X Spaces detection from 20+ influencer accounts
- Plus: Oracle Briefing, Pulse Check, HeyGen, Mining Intel, image backfill, log rotation

### Latest production video:
- Path: `~/protocol_pulse/video_pipeline_v3/output/2026-03-05/pulse_check_20260305.mp4`
- Stats: 330MB, 94/100 quality, 7.2 min, 6.39 Mbps, 5 clips from 5 channels
- Download: `scp ultron:~/protocol_pulse/video_pipeline_v3/output/2026-03-05/pulse_check_20260305.mp4 ~/Downloads/`
- NOTE: 10 video fixes are COMMITTED to code but this render was made BEFORE those fixes. A NEW render needs to be triggered to see the fixes in action.

---

## CRITICAL ITEMS THAT NEED IMMEDIATE ACTION

### 1. FIRE A NEW PRODUCTION VIDEO RENDER
The 10 visual fixes from PBX's review are in the code but NOT in the latest video.
```
Kill idle session: tmux kill-session -t autonomous-build
Start fresh: tmux new-session -s render \; send-keys 'cd ~/protocol_pulse/video_pipeline_v3 && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
Prompt: "Read PIPELINE_LAWS.md and ~/protocol_pulse/PRODUCTION_DESIGN_LAWS.md. Clear cache (rm -rf cache/clips/*) and run python3 daily_producer.py (production mode, no --test). Report SCP path and quality score."
```

PBX's 10 fixes that need to be visible in next render:
1. No logo intro — start with cold open hook + PiP preview
2. Split-screen layout (55% narration left, 40% PiP right)
3. Sentence boundary detection (no mid-sentence clip cuts)
4. PiP only shows when narrator pivots to next topic
5. Tweet card order matches narration order (Saylor tweet = Saylor card)
6. Playwright tweet screenshots (real images, not text-only)
7. Background music from assets/music/ at -20dB
8. "Stay sovereign" closing line always present
9. Cyberpunk animated background on narrator segments
10. Clip quality enforcement (3Mbps min)

### 2. LIVE STREAM LOOP DETECTION — NEW RULE (NOT YET BUILT)
**CRITICAL:** Many YouTube channels run 24/7 "live" streams that are just pre-recorded
content on a loop (recycled clips, price tickers, ambient music). These are NOT genuine
live events and must be EXCLUDED from our live intelligence pipeline.

**Detection logic to build (add to utils/live_monitor.py):**
```
def is_looped_stream(stream_info):
    """Detect fake/looped live streams vs genuine live events."""
    
    RED FLAGS (any 2+ = discard):
    1. Stream duration > 8 hours (genuine Spaces/live events rarely exceed 4-5 hours)
    2. Title contains: "24/7", "live price", "live chart", "radio", "music",
       "ambient", "lofi", "stream", "non-stop", "continuous"
    3. Channel has been "live" for multiple consecutive days
    4. No speaker changes detected in Whisper output (same voice/silence pattern repeating)
    5. Transcript contains repetitive phrases (same 50-word block appearing 3+ times)
    6. Viewer count is static (not fluctuating like a real conversation)
    7. No chat activity or minimal chat engagement
    
    GREEN FLAGS (genuine live event):
    1. Multiple speakers detected (speaker diarization)
    2. Topic shifts over time (different subjects discussed)
    3. Duration 30 min to 4 hours (typical Space/live event range)
    4. Title contains: "discussion", "debate", "interview", "AMA", "recap",
       "reaction", "breaking", "analysis", names of speakers
    5. Fluctuating viewer count
    6. Active chat/comments
    
    Return True if looped (discard), False if genuine (process)
```

**Add to LIVE_INTELLIGENCE_LAWS.md and LIVE_SPACES_PULSE_LAWS.md as a permanent rule.**
Title: "Section X: Loop Detection — Discard Recycled Content Streams"

### 3. NEWSLETTER — FIRE IT LIVE NOW
The newsletter engine is BUILT (routes_newsletter_trigger.py) but NOT yet sending.

**Two separate actions needed:**

**Action A — Standard daily newsletter (DO THIS NOW):**
The daily digest should be LIVE for any current and future subscribers immediately.
- Engine: utils/newsletter_engine.py (on Ultron) or routes_newsletter_trigger.py (on Replit)
- Resend API key: configured on Replit (RESEND_API_KEY in secrets)
- Content: top 3 topics, sentiment gauge, top 5 articles, node pulse
- Cron: daily at 8 AM EST
- BLOCKER: Replit deployment issue (bootstrap not executing). Fix by either:
  a) Migrating Flask to Ultron behind Cloudflare tunnel (preferred), OR
  b) Manually triggering via Ultron cron that calls the Replit endpoint

**Action B — One-time legacy subscriber reactivation (DO LATER when PBX provides emails):**
PBX has email addresses from a previous newsletter on consensusprotocol.org (WordPress on Flux Cloud, currently down).
When PBX provides these emails:
- Send a ONE-TIME reactivation email: "We're live! Protocol Pulse newsletter is here."
- Inform them what to expect (daily intel digest, exclusive insights)
- Include "mark as not spam" instruction
- Do NOT add them to daily sends until they click a confirmation link (double opt-in)

### 4. FIX REPLIT DEPLOYMENT (Terminal API + Newsletter both 404)
The Pulse Terminal API and Newsletter trigger both return 404 on Replit.
- Files exist in Git but Replit's gunicorn doesn't pick up the bootstrap hook
- bootstrap_github.py is at the top of app.py but doesn't execute on deployment
- PREFERRED FIX: Migrate Flask API from Replit to Ultron behind Cloudflare tunnel
  - Ultron already serves relay (port 8201) and avatar (port 8200)
  - Flask would be port 5000, tunneled via Cloudflare to api.protocolpulse.io
  - This eliminates the Replit persistence problem permanently
  - Replit becomes dev/staging only

---

## COMPLETE FEATURE MAP

### OPERATIONAL (running now):
| Feature | Status | Location |
|---------|--------|----------|
| Video pipeline (Pulse Check) | Production-ready, 94/100 quality | Ultron ~/protocol_pulse/video_pipeline_v3/ |
| 80-channel scanner | Active, */15 cron | channels.yaml + channel_daemon.py |
| YouTube Live monitor | Active, */5 cron | utils/live_monitor.py |
| X Spaces monitor | Active, */5 cron | utils/spaces_monitor.py |
| Article engine | 1,479+ articles | Replit routes.py |
| Vercel frontend | Live, glassmorphism | articles.protocolpulse.io |
| Avatar server | Running 2+ days | avatar.protocolpulse.io:8200 |
| Intelligent clip scorer | Deployed | utils/clip_scorer.py |
| Node Pulse monitor | Deployed | utils/node_monitor.py |
| Playwright screenshots | Deployed | utils/tweet_screenshot.py |
| 6 Remotion components | Built + rendered | remotion/src/compositions/ |
| 34 music tracks | Available | assets/music/ |
| Custom whoosh SFX | Uploaded | assets/sfx/custom_whoosh.mp3 |

### BUILT BUT BLOCKED (need Replit fix):
| Feature | Issue | Fix |
|---------|-------|-----|
| Terminal API (5 endpoints) | 404 on Replit | Migrate to Ultron |
| Newsletter trigger | 404 on Replit | Migrate to Ultron |
| Stripe subscription flow | Depends on Terminal | Migrate to Ultron |

### SPECCED BUT NOT YET CODED:
| Feature | Gospel Doc | Priority |
|---------|-----------|----------|
| Live Spaces Pulse (8 use cases) | LIVE_SPACES_PULSE_LAWS.md | HIGH |
| Loop detection for fake streams | (add to LIVE_INTELLIGENCE_LAWS.md) | HIGH |
| Marketing self-learning engine | MARKETING_STRATEGY_LAWS.md | HIGH |
| X posting automation | X_POSTING_LAWS.md | HIGH |
| Terminal Phase 2 (React dashboard) | PULSE_TERMINAL_LAWS.md | MEDIUM |
| Twilio phone call briefings | PRODUCT_BACKLOG.md | LATER |
| Sat Stacker game | PRODUCT_BACKLOG.md | LATER |
| Avatar instant-response mode | PRODUCT_BACKLOG.md | LATER |
| Mobile UI audit | PRODUCT_BACKLOG.md | LATER |

---

## GOSPEL DOCUMENTS (16 total, ~7,800+ lines)

All in GitHub: `https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/{filename}`

| # | Document | Lines | Purpose |
|---|----------|-------|---------|
| 1 | PIPELINE_LAWS.md | 428 | Video pipeline rules (22 sections) |
| 2 | PRODUCTION_DESIGN_LAWS.md | 326 | Research-backed visual/audio design |
| 3 | CONTENT_INTELLIGENCE_LAWS.md | 480 | Brand ethos, content pillars, three threats |
| 4 | PULSE_TERMINAL_LAWS.md | 449 | Premium intelligence product bible |
| 5 | LIVE_INTELLIGENCE_LAWS.md | ~200 | YouTube Live + X Spaces capture |
| 6 | LIVE_SPACES_PULSE_LAWS.md | 418 | 8 use cases for max squeeze from Spaces |
| 7 | MARKETING_STRATEGY_LAWS.md | 406 | Self-learning content engine + milestones |
| 8 | X_POSTING_LAWS.md | 221 | Social media posting strategy |
| 9 | PRODUCT_BACKLOG.md | 100 | 12 prioritized tasks |
| 10 | PROTOCOL_PULSE_OVERVIEW.md | 267 | Pitch deck + mission statement |
| 11 | EXPANSION_SPEC_V22_V30.md | 693 | V22-V30 roadmap |
| 12 | HANDOFF_V2_COMPLETE.md | 362 | Technical handoff |
| 13 | PIPELINE_FORENSIC_AUDIT.md | ~400 | Bug inventory |
| 14 | MASTER_PLAN_OF_ACTION.md | 141 | V11-V21 execution plan |
| 15 | ARTICLE_PAGE_LAWS.md | ~500 | Article system rules |
| 16 | PIPELINE_ELEVATION_SPEC.md | ~400 | Architecture spec |

---

## VOICES + KEYS

### ElevenLabs Voices:
- Host 1 (Female): **Eryn** — `kdnRe2koJdOK4Ovxn2DI` (speed 1.12x)
- Host 2 (Male): **Mark** — `1SM7GgM6IMuvQlz2BwM3` (speed 1.10x)
- BANNED: Gigi, Jessica, Nicole, Sarah, Matilda
- PBX Professional Voice Clone: PENDING (recording tonight at studio)

### HeyGen Avatars:
- Sarah: `d259c335741f4fc0b061e04c59388b4e` ($1/min)
- PBX: `3be8ed14b0954b898f4127836c21f6cc` ($2/min)

### Relay:
- Ultron: `POST https://relay.protocolpulse.io/exec`
  `{"token":"581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552","cmd":"..."}`
  Headers: `User-Agent: Mozilla/5.0` (REQUIRED)
  Use python3 urllib, NOT curl.
- Replit: `POST https://protocolpulse.replit.app/api/admin/exec` (same format)

---

## PENDING FROM PBX

- [ ] PBX ElevenLabs Professional Voice Clone (recording tonight)
- [ ] YouTube OAuth setup (Google Cloud project → enable YouTube Data API v3)
- [ ] Legacy newsletter subscriber emails (from Flux Cloud WordPress, currently down)
- [ ] Replit republish after migration fix
- [ ] Video feedback on next render (after 10 fixes are applied)
- [ ] X Spaces quote-tweet curation (first 50 posts in batches of 10)

---

## GROWTH TARGETS

| Metric | Month 1 | Month 3 | Month 6 | Month 12 |
|--------|---------|---------|---------|----------|
| YouTube subs | 100 | 1,000 | 5,000 | 25,000 |
| X followers | 500 | 2,500 | 10,000 | 50,000 |
| Newsletter | 200 | 1,000 | 5,000 | 15,000 |
| Terminal paid | 0 | 5 | 50 | 200 |
| Revenue/mo | $0 | $750 | $5,500 | $22,500 |

---

## MISSION STATEMENT

Protocol Pulse is the Bloomberg Terminal for Bitcoin. We transform raw intelligence
from 80+ YouTube channels, live X Spaces, on-chain data, and social sentiment into
actionable daily briefings — delivered as video, audio, text, and real-time API data.

For transactors, not tourists. For Bitcoiners, not crypto speculators.

*"Intelligence for transactors, not tourists."*

---

## RULES FOR NEW AGENT

- ALWAYS read relevant gospel docs before writing ANY code
- NEVER use Claude Code `-p` flag (always interactive mode in tmux)
- NEVER run parallel Claude Code sessions on same repo
- ALWAYS run `regression_test.sh` before committing
- NEVER assign PBX manual tasks — do everything autonomously
- Use python3 urllib (not curl) for relay calls
- Ultron relay REQUIRES `User-Agent: Mozilla/5.0` header
- Git push from Ultron only, not Replit
- Triple-verify features before claiming done (RIGOR PROTOCOL)
- One comprehensive Claude Code prompt > multiple small prompts
