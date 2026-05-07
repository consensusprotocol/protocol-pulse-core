# PROTOCOL PULSE — SOVEREIGN CONSTITUTION
## Version 1.0 | May 2026
### This document is tool-agnostic. It is the ground truth for Protocol Pulse, readable by any AI system, developer, or operator. It supersedes all other context files in the event of conflict.

---

## SECTION 1: WHAT THIS IS

**Protocol Pulse** (protocolpulse.io) is an autonomous Bitcoin intelligence platform built by Consensus Protocol LLC in Naples, FL.

It is not a news aggregator. It is not a crypto blog. It is a sovereign intelligence operation — synthesizing on-chain data, congressional STOCK Act disclosures, options flow, miner conviction signals, and KOL sentiment into a single live feed. Updated in real time. Accessible for the price of a Substack. No Bloomberg terminal required.

**Two properties:**
- **Protocol Pulse** — Bloomberg-style Bitcoin intelligence terminal. Daily video briefings (Pulse Check), live signal matrix, newsletter, Commander intelligence dashboard.
- **The Bitcoin Boomers** — Premium podcast for Gen X / Boomer Bitcoin holders. High-net-worth, decision-making demographic.

---

## SECTION 2: ORG STRUCTURE

| Role | Person | Notes |
|------|--------|-------|
| CMO + Internal Builder | **PBX (Paul Evans)** | Technical lead, Bitcoin maximalist, runs all internal builds with Claude as primary partner |
| CEO | **Matty** | Strategic lead, web3-oriented (not maxi-aligned), separate from the build process |

**CRITICAL:** PBX is never to be positioned publicly as founder, solo-builder, or CEO. Matty is the CEO. This distinction must be maintained on all public-facing surfaces without exception.

---

## SECTION 3: INFRASTRUCTURE

**Server:** Ultron
- CPU: AMD EPYC 9R14
- GPU: 4× RTX 4090 (24GB VRAM each, 96GB total)
- RAM: 128GB
- OS: Ubuntu 24.04
- Storage: 1.8TB NVMe (955GB free as of May 2026)

**GPU Assignment (INVIOLABLE):**
- `cuda:0` — Video pipeline (daily_producer.py) ONLY
- `cuda:1` — Avatar server (Wav2Lip/Kokoro for Satomi Oracle) — PROTECTED LIVE SERVICE
- `cuda:2,3` — Local LLM inference (Ollama: gpt-oss-20b, Qwen3, Llama 3.1) + image generation

**Web Stack:**
- Flask/Python backend
- **Waitress** on port 5000 (Gunicorn is PERMANENTLY RETIRED — banned)
- Cloudflare Tunnel → protocolpulse.io
- Cloudflare Zone: `cae015a44a3885100c651db2b36e76a8`
- SQLite DB: `~/protocol_pulse/instance/protocol_pulse.db`

**Key File Paths:**
```
~/protocol_pulse/
  core/app.py                    — Flask entry point
  core/routes_admin.py           — Admin + board endpoints
  core/routes_api.py             — API endpoints (14k+ lines)
  core/routes_auth.py            — Auth + Stripe
  core/routes_pages.py           — Page rendering
  core/services/                 — Business logic
  core/models.py                 — SQLAlchemy models
  video_pipeline_v3/             — Video production pipeline
  agents/                        — Sovereign Agent Fleet
  templates/                     — Jinja2 HTML templates
  static/                        — Assets, uploads
  CLAUDE.md                      — CC adapter (thin wrapper)
  PIPELINE_LAWS.md               — Video pipeline laws
  CONSTITUTION.md                — This file (sovereign ground truth)
```

**Relay:** `https://relay.protocolpulse.io/exec`
Token: `57eadb9f3e6503ecf381b9046f90f7c21dd98e1d9c17bc8d83061649b081edcf`
Rules: Python3 urllib only, User-Agent: Mozilla/5.0, 90s keepalive

**Git:** `consensusprotocol/protocol-pulse-core` on GitHub, SSH keys on Ultron

---

## SECTION 4: BRAND VOICE + VISUAL IDENTITY

**Voice:** Intelligent, edgy, confident. Not tribal, not cypherpunk-dogma. Not "stay free stay sovereign." Not "no chain but Bitcoin." Must appeal to institutional AND retail audiences. Bitcoin-first without being alienating.

**Visual Identity:**
```
Background:     #000000 (pure black) / #0A0A0A (surface)
Surface:        #0d0d0d / #141414
Primary Red:    #CC0000
Dark Red:       #880000
Light Red:      #FF4444
Gold (metrics): #F8C15C
Text Primary:   #FFFFFF
Text Muted:     #888888
Border:         #1F1F1F
Font:           JetBrains Mono (monospace throughout)
```

**BANNED colors in all UI:** Blue, cyan, purple — permanently banned from every visual element.

**Aesthetic:** Bloomberg Terminal meets freedom tech. Data-dense, dark, authoritative. The product looks like you're already inside an intelligence operation before you click anything.

---

## SECTION 5: PHILOSOPHY (THE WHY)

Protocol Pulse is **freedom tech infrastructure**. This framing bridges PBX's Bitcoin conviction and Matty's web3 orientation without compromising either.

**Freedom tech includes:** Bitcoin, Lightning, Nostr, self-custody, open protocols, BTCPay, Spiral, HRF, OpenSats, Foundation Devices, Start9.

**Freedom tech explicitly excludes:** VC-backed KYC L2s, custodial platforms that require trusting a third party with your financial life, anything that requires permission to participate.

**The five tenets (from /philosophy page):**
1. Bitcoin is the exit — not a trade, not an asset class
2. Self-custody is the only real custody
3. Open protocols beat closed platforms
4. The signal is always there — the noise is manufactured
5. Intelligence should be sovereign — no ads, no data sold, no engagement optimization

---

## SECTION 6: TECHNOLOGY DECISIONS + WHY

Every major decision is recorded here so future AI systems and operators understand the reasoning — not just the outcome.

### Web Server: Waitress (not Gunicorn)
**Why:** Gunicorn was causing production instability. Waitress is simpler, more reliable for this stack, and runs cleanly as a single process. Gunicorn is permanently retired and banned from all configuration.

### Voice: ElevenLabs PBX Clone (not Grok TTS)
**Why:** PBX's voice clone (ID: `HmUVvDlHsEz0m3eUGLgu`) is the show's identity. Grok TTS was evaluated (~70× cheaper) but doesn't support custom voice cloning. The voice is non-negotiable. Cost savings that require abandoning it are not acceptable.

### Lip Sync: Wav2Lip (not MuseTalk, not SadTalker, not HeyGen)
**Why:** Wav2Lip runs at 134fps on the 4090 with batch_size=48. MuseTalk and SadTalker are permanently banned. HeyGen was broken and wasted 6GB RAM — avatar_server.py now runs Wav2Lip/Kokoro and is a PROTECTED LIVE SERVICE.

### TTS: Kokoro af_heart (Host 1) + ElevenLabs PBX (Host 2)
**Why:** Kokoro runs locally at zero cost. ElevenLabs for PBX's voice specifically. Native ElevenLabs pronunciation confirmed superior to manual phonetic overrides — all phonetic overrides have been removed.

### Local LLM: gpt-oss-20b (OpenAI open-weight, Apache 2.0)
**Why:** Fits in a single 4090 (needs ~16GB VRAM). Benchmarks similar to o3-mini. The 120B variant was evaluated and rejected — it would require all four 4090s and block the pipeline. QWEN_FIRST law: local LLM runs before any paid API call. $0 cost per call.

### API Monetization: LSAT (not API keys, not x402/Base)
**Why:** LSAT (Lightning Service Authentication Tokens) is the Bitcoin-native answer to x402 on Coinbase's Base. An agent hits an endpoint → gets a 402 with a Lightning invoice → pays → gets access. Zero accounts, zero KYC, zero custodian. Coinbase's x402 runs on Base (ETH L2) requiring USDC and Coinbase infrastructure. Our LSAT runs on Bitcoin/Lightning via `protocolpulse@getalby.com`.

### Service Discovery: Nostr NIP-89 (not Agentic.Market)
**Why:** Agentic.Market is a centralized index. NIP-89 publishes cryptographically signed service cards to 5 Nostr relays (Damus, nostr.band, nos.lol, Primal, Snort). Any Nostr-aware agent discovers Protocol Pulse APIs without a centralized gatekeeper.

### AV Sync: fps=30 in clip_extractor.py ONLY
**Why:** This is load-bearing. `fps=30` must stay in `clip_extractor.py` for VFR YouTube sources. It must NOT appear in `render_clip.py`'s filter graph — this caused progressive AV drift. Root cause confirmed, fix locked. Do not revert.

### Music: confident_02.mp3 (LOCKED)
**Why:** This is the show's signature track. Not configurable. Not mood-selected. Locked.

### `aresample=async=1` BANNED
**Why:** Banned everywhere except `clip_extractor.py` fix_av_sync(). It adds latency and causes sync drift in the assembly pipeline.

---

## SECTION 7: WHAT WAS TRIED AND REJECTED

| Technology | Status | Reason |
|-----------|--------|--------|
| Gunicorn | RETIRED | Production instability |
| HeyGen | BROKEN | Wasted 6GB RAM, avatar_server now runs Wav2Lip |
| MuseTalk | BANNED | Wav2Lip is the only approved lip sync engine |
| SadTalker | BANNED | Same — consumes 3GB+ on cuda:1 |
| Creatomate | BANNED | Not approved |
| OpusClip | BANNED | Not approved |
| Suno API | BANNED | Use pre-generated tracks in assets/music/ |
| Three.js | BANNED | No Three.js in any component |
| Grok TTS | SHELVED | No custom voice clone support |
| Manual phonetic overrides | REMOVED | Native ElevenLabs pronunciation is superior |
| CRF 20+ | BANNED | Quality too low |
| Preset "fast"/"ultrafast" | BANNED | Final output only |
| Blue/cyan/purple in UI | PERMANENTLY BANNED | Brand colors only |
| Gunicorn | BANNED | Waitress only |
| x402 on Base | REJECTED | Runs on ETH L2 — not freedom tech |
| Agentic.Market as sole discovery | SUPPLEMENTARY | Listed there but NIP-89 is primary |
| gpt-oss-120B | REJECTED | Requires all 4 GPUs, blocks pipeline |
| HF downloads on cuda:1 | CONFLICTS | avatar_server owns cuda:1 |

---

## SECTION 8: SOVEREIGN AGENT FLEET

Four async agents run as daemons, communicating via SQLite event_bus (`~/protocol_pulse/agents/`):

| Agent | File | Consumes | Does |
|-------|------|---------|------|
| **HERALD** | herald_agent.py | `grade_complete` (A grade) | Posts tweet + Telegram alert, logs episode |
| **SENTINEL** | sentinel_agent.py | `grade_complete` (non-A) | Alerts on quality failures, emits `fix_requested` |
| **ARCHIVIST** | archivist_agent.py | All `grade_complete` | Records to episode_archive.jsonl, queries 7d trends |
| **RENDER_LOOP** | render_loop_agent.py | `fix_requested` | Maps to DIMENSION_MAP, escalates repeats to human |

**Runner:** `agent_runner.py` — threads all 4, polls event_bus every 10s
**Auto-restart:** crontab wired `@reboot` + `*/10 * * * *` watchdog
**Event bus:** SQLite at `agents/state/agent_state.db`
**Episode archive:** `agents/state/episode_archive.jsonl`

**Barry Zhang principles applied:**
- Budget-aware: SENTINEL = zero tokens for grade monitoring
- Self-evolving: ARCHIVIST queries 7d archive, emits insights for other agents
- Async: agents communicate via event_bus without knowing each other exist

---

## SECTION 9: VIDEO PIPELINE QUICK REFERENCE

**Orchestrator:** `~/protocol_pulse/video_pipeline_v3/daily_producer.py`

**Quality Target:** Grade A = score ≥ 88, broadcast_ready=True, zero 0/10 on critical dimensions
**Convergence Target:** 10 consecutive Grade A renders before pipeline is "locked"
**Counter:** `video_pipeline_v3/logs/consecutive_a_grades.txt`

**Output specs (INVIOLABLE):**
- Video: 1920×1080, 30fps CFR, h264, yuv420p
- Audio: AAC, 48000Hz, stereo, -14 LUFS, <-1.5 dBTP true peak
- Container: MP4, 8Mbps target bitrate

**5-Clip Rule:** Exactly 5 partner clips from 5 different channels per episode (production mode)
**Freshness Law:** Every clip must have upload_date within 48 hours of render time

**Voice IDs:**
- Host 1 (Deborah): `VeCVR24o7g2y1IxLJzZs`
- Host 2 PBX clone: `HmUVvDlHsEz0m3eUGLgu` — 1.2× speed, non-negotiable

**Music volumes:** 0.22 narration, 0.04 clips, 0.15 social

**AV Sync Root Cause (LOCKED — do not revisit):**
- `fps=30` belongs in `clip_extractor.py` for VFR YouTube sources
- `fps=30` must NOT appear in `render_clip.py`'s filter graph
- Violation causes progressive AV drift across the episode

**Pipeline modules (assembler.py is THIN ORCHESTRATOR — add no logic there):**
```
assembler.py          — orchestrator only (<1,800 lines)
render_narrator.py    — PBX narration scenes
render_clip.py        — Partner channel clips
render_social.py      — Tweet cards + Nostr signal
render_intro_outro.py — Intro/outro/cold open
render_data.py        — Charts + data overlays
audio_master.py       — LUFS normalization, music mixing
```

---

## SECTION 10: PLATFORM FEATURES + STATE

### /intelligence — Sovereign Signal Matrix
- Radar (center hero, span-5): 6-axis polygon — MCX, EPX, IHX, OPX, FDX, OCX
- PCAF Orb (left, span-3): composite score 0-100
- Proprietary Indices (right sidebar, span-4): hover → highlights radar axis + shows rich data
- **Random walk removed** from radar (was causing 6s jolts) — real /api/orb data refreshes every 30s

### /live — Bitcoin Live Terminal
- D3 geoOrthographic globe (Bitcoin node network)
- 3-block blockchain visualizer (Canvas 2D, real mempool.space data, animated chain links)

### /panopticon — Sovereign Panopticon
- Globe REMOVED (belongs on /live only)

### /philosophy — Freedom Tech Manifesto
- 5 tenets, freedom stack grid, LSAT/Nostr build philosophy, Commander CTA

### /api-access — LSAT Documentation
- Pay-per-use API pricing, Lightning instructions, code examples

### Commander Dashboard
- 14 widgets (12 original + dune_onchain + lunar_social)
- Drag-drop layout per user, persisted via /api/hub/layout PATCH
- Dashboard configurator panel (toggle widgets on/off, save/reset)

### Ops Board (/admin/board)
- Kanban: backlog → in_progress → review → done → archived
- Card attachments: PDF/doc/image upload (25MB limit) + URL link pinning
- BoardAttachment model, files stored in static/board_attachments/

### LSAT API Gating (live, Lightning DNS pending)
- `/v1/signals/live` — 1,000 msats/1hr
- `/api/intelligence/signal` — 500 msats/30min
- `/api/hub/intel` — 2,000 msats/24hr
- `/api/orb` — FREE (homepage radar, not gated)
- Payment: `protocolpulse@getalby.com`
- Note: getalby.com DNS not resolving from Ultron network — graceful pass-through active

### NIP-89 Nostr Service Cards
- Published to: Damus, nostr.band, nos.lol, Primal, Snort
- 3 service cards: signals/live, orb, intelligence/signal

---

## SECTION 11: INVIOLABLE RULES (for any AI system operating on this codebase)

1. **NEVER print .env contents or expose API keys**
2. **NEVER run sed on .env files** — use nano or Python string replacement
3. **NEVER start a second Claude Code session on the same repo/worktree** — one session at a time
4. **NEVER use Gunicorn** — Waitress only
5. **NEVER add logic to assembler.py** — use the split render modules
6. **NEVER use Three.js, MuseTalk, SadTalker, Creatomate, OpusClip, Suno API**
7. **NEVER use blue/cyan/purple** in any visual element
8. **NEVER add fps=30 to render_clip.py filter graph** — causes AV drift
9. **NEVER kill avatar_server.py** — it is a PROTECTED live service on cuda:1
10. **NEVER force push to git**
11. **NEVER claim done without proof** — show curl output, test results, or log evidence
12. **NEVER assign PBX manual tasks** — always attempt autonomously
13. **AUDIT-FIRST:** Read every file before editing it in the same session
14. **EVERY commit:** git add + commit + push — no uncommitted .py files left on disk
15. **SYNTAX CHECK:** python3 -m py_compile on every modified .py before committing
16. **REGRESSION TEST:** bash video_pipeline_v3/regression_test.sh before any pipeline commit
17. **ROOT CAUSE OVER BAND-AIDS:** Fix the actual problem, not the symptom
18. **All times in Eastern Time (ET)** for PBX

---

## SECTION 12: WHAT GOOD LOOKS LIKE

**A Grade A Pulse Check episode:**
- Score ≥ 88/100 from Gemini grading
- No 0/10 on critical dimensions (true_peak, black_frames, freeze, host_authenticity)
- broadcast_ready = True
- 5 clips from 5 different channels, all within 48h of render
- Music at correct volumes (0.22/0.04/0.15)
- AV sync < 0.03s on final output
- PBX voice at 1.2× speed, natural pronunciation

**The brand is not:**
- Tribal or cypherpunk-dogma
- "Stay free stay sovereign" / "Blood oath" / "Defiant HODLer"
- Accessible only to Bitcoin maxis

**The brand is:**
- Intelligent, edgy, confident
- The Bloomberg terminal of Bitcoin
- Freedom tech that anyone can understand and use
- Sovereign infrastructure you can trust because you can verify it

---

## SECTION 13: KEY PEOPLE + OUTREACH

| Person | Context | Status |
|--------|---------|--------|
| John Michael Drew | Bitcoin Day / Bitcoin 2026 speaker | Guest outreach target |
| Madison Hanson | Podcast guest target | Guest outreach target |
| Mel Sands | Team member | Commander account active (sandsotime1@gmail.com) |
| Matty | CEO of Consensus Protocol LLC | Not involved in builds |

**Sponsor outreach:** 30 prospects emailed April 2026, zero replies to date. Follow-up needed.

---

## SECTION 14: HOW TO ONBOARD A NEW AI SYSTEM

If you are an AI system reading this for the first time:

1. This codebase runs a live Bitcoin intelligence platform. Real subscribers pay for access. Production mistakes have real consequences.
2. Read PIPELINE_LAWS.md before touching any video pipeline file
3. Read Section 11 (Inviolable Rules) before executing any command
4. When in doubt, read the file first. Then read it again. Then act.
5. Every fix addresses root cause. Never patch symptoms.
6. The relay at `https://relay.protocolpulse.io/exec` is how you execute commands on Ultron remotely
7. PBX communicates directly and tersely. He expects autonomous execution. Never ask permission for something you already know how to do.
8. The voice clone (ElevenLabs `HmUVvDlHsEz0m3eUGLgu`) is the show's identity. It is not replaceable.
9. This is freedom tech. Bitcoin rails, Lightning payments, Nostr discovery. That is not a preference — it is the product.

---

*CONSTITUTION.md — Consensus Protocol LLC — Last updated: May 2026*
*Tool-agnostic. Version-controlled. Supersedes CLAUDE.md in the event of conflict.*
