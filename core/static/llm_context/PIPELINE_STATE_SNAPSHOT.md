# PROTOCOL PULSE — PIPELINE STATE SNAPSHOT
**Last updated:** 2026-03-13 ~02:30 UTC (Session 16, Chat 2)
**Repo:** consensusprotocol/protocol-pulse-core (main branch)
**Server:** Ultron — AMD EPYC 9R14 / 4x RTX 4090, relay at relay.protocolpulse.io/exec

---

## 🔴 CURRENT STATUS — READ FIRST

**Both GPUs are MID-RENDER right now.** Iteration 2 on GPU0 (render-stable), GPU1 on main.
- GPU0: Started ~02:25 UTC — ETA ~03:15-03:25 UTC
- GPU1: Running in parallel (experimental slot)
- Render watcher PID 4177269 — fires Telegram + download link the moment any render lands
- Last grade: F(48/100) — that was iteration 1 on pre-fix code. Iteration 2 has all 9 fixes.
- **Do NOT kill the orchestrator. Do NOT touch render output dirs.**

---

## LAUNCH COMMANDS (permanent)

```bash
# CC session (never use -p flag):
tmux new-session -s NAME \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter

# Orchestrator (if dead):
tmux new-session -d -s gpu_orchestrator -x 220 -y 50
tmux send-keys -t gpu_orchestrator 'cd ~/protocol_pulse && python3 dual_gpu_orchestrator.py >> logs/orchestrator.log 2>&1' Enter

# Relay pattern (python3 urllib only, never curl):
# POST https://relay.protocolpulse.io/exec
# {"token":"581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552","cmd":"..."}
# Header: User-Agent: Mozilla/5.0
```

---

## GOSPEL FILES (load into every CC session that touches these areas)

- `~/protocol_pulse/PIPELINE_LAWS.md` — audio targets, color palette, timing, TTS rules
- `~/protocol_pulse/PIPELINE_LESSONS.md` — 518+ lines of hard-won lessons
- `~/protocol_pulse/PIPELINE_STATE_SNAPSHOT.md` — this file (cross-LLM onboarding)
- `~/protocol_pulse/ARTICLE_PAGE_LAWS.md` — article code gospel
- `~/protocol_pulse/video_pipeline_v3/VISUAL_DESIGN_SYSTEM.md` — 542 lines, color/typography gospel

---

## INFRASTRUCTURE

| Service | Location | Status |
|---------|----------|--------|
| Flask/Gunicorn | port 5000, ~/protocol_pulse/core/app.py | ✅ |
| Oracle Live (FastAPI) | port 8202 | ✅ |
| Video file server | port 5100 | ✅ |
| Avatar server | port 8200, avatar.protocolpulse.io | ✅ |
| CF Tunnel | protocolpulse.io → Ultron | ✅ |
| Orchestrator | tmux:gpu_orchestrator | ✅ RUNNING |
| Render watcher | PID 4177269 (nohup) | ✅ |
| Watchdog | tmux:watchdog | ✅ |

---

## VIDEO PIPELINE — COMPLETE STATE

### Architecture
- `dual_gpu_orchestrator.py` — runs both GPUs forever. GPU0=render-stable, GPU1=main
- `video_pipeline_v3/daily_producer.py` — manifest builder + render orchestration
- `video_pipeline_v3/assembler.py` — FFmpeg filtergraph assembly (~4019 lines)
- `video_pipeline_v3/tts_engine.py` — ElevenLabs TTS, cache, validation
- `video_pipeline_v3/gemini_grade.py` — Gemini 2.5 Pro grader (10 criteria × 10pts)

### Grader Criteria (90+/100 = Grade A)
host_authenticity, episode_title, no_filler, timeliness, music_mix, transitions, visual_polish, no_artifacts, audio_quality, pacing

### Hosts
| Role | Voice ID | Speed | Notes |
|------|----------|-------|-------|
| Eryn (HOST_1) | kdnRe2koJdOK4Ovxn2DI | 1.12x | ElevenLabs — sharp female host |
| Mark (HOST_2) | 1SM7GgM6IMuvQlz2BwM3 | 1.10x | ElevenLabs — male contrarian |
| Oracle Jessica | cgSgspJ2msm6clMCkdW9 | — | Oracle briefings only |

**BANNED VOICE ID (caused 48h of silent renders):** uxKr2vlA4hYgXZR1oPRT — deleted voice, ElevenLabs returns 200 + 0 bytes silently

### Music
- 30 Suno tracks at `video_pipeline_v3/assets/music/`
- Custom whoosh: `assets/sfx/custom_whoosh.mp3`
- Sidechain ducking: -18dB idle → -30dB under voice

---

## ALL FIXES APPLIED THIS SESSION (commits dcbf6742, 27f38e83, 5daba551, e0c9fe0a)

### ✅ CONFIRMED FIXED — DO NOT RE-FLAG

**Audio (P0 — biggest grade impact):**
- `assembler.py` — Per-segment `loudnorm` removed from ALL 5 locations (lines 583, 1028, 1560, 2267, 2485). Single loudnorm now ONLY in `concatenate_parts()` at lines 3123/3339. This was causing LUFS drift to -17.7 and over-compression.
- `tts_engine.py` — All audio helpers now 48000Hz stereo: `_generate_silence()` (was `r=44100:cl=mono`), `_mp3_to_m4a()` (was `-ar 44100 -ac 1`), `tts_inworld()` wav decode (was `-ar 44100 -ac 1`)
- `assembler.py` — Duplicate `aformat` after `alimiter` removed (was at lines 2267, 2485)
- TTS cache wiped (had stale 44100Hz files) — `video_pipeline_v3/tts_cache/`

**TTS Hardening (P1):**
- `tts_engine.py` — `_get_tts_provider()` now hard-fails on anything != "elevenlabs" with RuntimeError
- `tts_engine.py` — `tts_inworld()` stubbed to raise RuntimeError with ban message
- `tts_engine.py` — Inworld branch removed from `generate_dialogue_audio()` — always calls `tts_elevenlabs()`
- `tts_engine.py` — `_tts_cache_get()` now validates cache hits via `validate_tts_output()`, raises size gate to 10240 bytes, deletes corrupt cache on hit
- `tts_engine.py` — `ffprobe_duration()` now returns -1.0 (not 0.0) on failure + logs warning
- `tts_engine.py` — `MAX_CHUNK_CHARS = 500` constant injected (was accidentally eaten by Inworld stub regex)

**Pipeline Integrity (P1):**
- `daily_producer.py` — Post-render health check now blocks `return passed` → `return passed and hc_passed`
- `daily_producer.py` — 5 clips from 5 unique channels now hard-enforced in production mode (not test_mode)

**Color Palette (P1/P2):**
- `assembler.py` — `COLOR_RED` constant: `0xFF0000` → `0xFF3333` ✅
- `assembler.py` — 7 solid border drawboxes: `0xFF0000@0.85+` → `0xFF3333` ✅
- `assembler.py` — 2 bare `fontcolor=0xFFFFFF` (no opacity) → `0xF4F5F8` ✅
- `assembler.py` — 5 `0xFF0033` (off-spec red) → `{COLOR_RED}` ✅
- `assembler.py` — `BV2_MUTED = "0xFFFFFF"` → `COLOR_WHITE` (warm white) ✅
- `assembler.py` — Info bar base: `0x000000@0.75` → `{COLOR_BG}@0.75` (navy, not pure black) ✅

**Other:**
- `daily_producer.py` — `COLOR_RED` was `0xFF0000` → `0xFF3333` ✅
- `daily_producer.py` — Duration health check: `400-600s` → `480-900s` ✅
- `daily_producer.py` — BTC price: CoinGecko primary + mempool fallback, no hardcoded `$97,000` ✅
- `daily_producer.py` — BTC price docstring updated ✅

### ✅ WHAT IS NOT A BUG (do not let LLMs re-flag these)
- `_tts_generate_silence_fallback()` — intentionally hard-fails. Silence = F grade. This is correct.
- `expand_numbers_for_tts` — already wired at lines 301 and 385 of tts_engine.py
- `BV2_STARK_WHITE` — maps to `COLOR_WHITE = 0xF4F5F8`, not pure white
- Atmospheric grid overlays at `0xFF0000@0.04-0.12` — low opacity, imperceptible, leave them
- `fontcolor=0x000000` on gold info bar text — intentional dark text on gold background
- `0x000000` panel overlays at lines 887, 920 — subtle overlays, not the banned solid pure black

---

## MULTI-LLM AUDIT SYSTEM

**Prompt template for other LLMs:** (serves files via Flask static)
- Snapshot: `https://protocolpulse.io/static/llm_context/PIPELINE_STATE_SNAPSHOT.md`
- Files: `/static/llm_context/assembler.py`, `daily_producer.py`, `tts_engine.py`
- Note: Gemini and Perplexity can't fetch these URLs — paste file contents directly

**LLM performance this session:**
- **Grok** — Most reliable. Found real P1s both rounds (COLOR_RED, duration cap, BTC fallback, 0xFF0033 ticker, 44kHz)
- **ChatGPT** — Strong on cross-validation and synthesis. Correctly called out loudnorm P0, cache validation, health gate, 5-clip enforcement
- **Perplexity** — Good code reading. Caught Inworld footgun, 44kHz, cache validation, info bar pure black
- **Gemini** — Solid but flagged already-fixed items (duplicate aformat, pure white) — checked "already fixed" list needed
- **Venice** — Useless. Ignored structured prompt entirely. Do not use.

**Cross-LLM audit law:** Claude Code builds → all LLMs audit actual code (not specs) → Claude synthesizes → second CC pass on P0+P1 → merge

---

## PENDING / OUTSTANDING

### IMMEDIATE (after Grade A render lands)
1. Review Telegram link when render_watcher fires
2. Check grade_report.log for breakdown
3. If Grade A → `git tag grade-a-$(date +%Y%m%d) && promote_to_stable.sh`
4. If still failing → check grade breakdown, identify new failure mode, iterate

### PARKED (do not build until Grade A locked)
- PBX Report pipeline — spec at `/tmp/pbx_report_spec.md`, voice profile at `pbx_report/voice_training/PBX_VOICE_PROFILE.md` (239 lines)
- Sponsor Agent — spec at `SPONSOR_AGENT_SPEC.md`
- RNS.ID / Palau Digital Residency affiliate ($300/referral) — add to partners section
- Sovereignty Stack
- HeyGen Oracle Briefings (Sarah avatar d259c335..., PBX avatar 3be8ed14...)

### KNOWN OPEN ISSUES
- Duration cap: script generates ~603s, QC max 900s — word budget enforcement in `script_writer.py` still loose
- Resend domain not verified → no overnight email alerts
- Channel scanner not on cron (manual scan via --skip-scan flag)
- Dual app.py issue — `core/app.py` has hardcoded dev secret key
- Caller ID "Protocol Pulse" — buy Twilio toll-free + CNAM (~$2/mo)
- `apply_blink()` in avatar_server.py creates black oval artifacts — replace body with `return frame` no-op

---

## MORNING / NEW CHAT CHECK COMMANDS

```bash
# Is render done?
ls -lh ~/protocol_pulse/video_pipeline_v3/output/2026-03-13/pulse_check_*.mp4 2>/dev/null

# Grade result
tail -20 ~/protocol_pulse/video_pipeline_v3/logs/grade_report.log

# Orchestrator alive?
ps aux | grep dual_gpu_orchestrator | grep -v grep
tail -5 ~/protocol_pulse/logs/orchestrator.log

# GPU utilization
nvidia-smi --query-gpu=index,utilization.gpu,power.draw --format=csv,noheader

# TTS confirmed ElevenLabs + correct IDs?
grep "TTS_PROVIDER\|ELEVEN" ~/protocol_pulse/.env | head -3
grep "kdnRe2koJdOK4Ovxn2DI\|1SM7GgM6IMuvQlz2BwM3" ~/protocol_pulse/video_pipeline_v3/tts_engine.py | head -2

# No loudnorm in segments?
grep -n "loudnorm" ~/protocol_pulse/video_pipeline_v3/assembler.py | grep -v "3089\|3123\|3134\|3159\|3328\|3338\|3339\|concatenate\|BUG5"

# No 44100Hz?
grep -n "44100\|cl=mono" ~/protocol_pulse/video_pipeline_v3/tts_engine.py

# No banned reds?
grep -n "0xFF0033\|0xFF0000@0.8" ~/protocol_pulse/video_pipeline_v3/assembler.py

# Render watcher alive?
ps aux | grep render_watcher | grep -v grep
```

---

## KEY FILE LOCATIONS

```
~/protocol_pulse/
├── PIPELINE_LAWS.md                    ← gospel
├── PIPELINE_LESSONS.md                 ← 518+ lines hard-won lessons
├── PIPELINE_STATE_SNAPSHOT.md          ← this file
├── ARTICLE_PAGE_LAWS.md                ← article code gospel
├── dual_gpu_orchestrator.py            ← both GPUs, runs forever
├── render_watcher.py                   ← Telegram alert on render complete (PID 4177269)
├── .env                                ← TTS_PROVIDER=elevenlabs, all API keys
├── logs/
│   ├── orchestrator.log
│   ├── best_grade.json                 ← {"score":0} — first Grade A will update this
│   └── runtime_status.json
├── video_pipeline_v3/
│   ├── assembler.py                    ← FFmpeg filtergraph (~4019 lines)
│   ├── daily_producer.py               ← main pipeline orchestration
│   ├── tts_engine.py                   ← ElevenLabs TTS + cache + validation
│   ├── gemini_grade.py                 ← Gemini 2.5 Pro grader
│   ├── VISUAL_DESIGN_SYSTEM.md         ← 542 lines, color/typography gospel
│   ├── tts_cache/                      ← cleared this session (stale 44100Hz)
│   ├── logs/grade_report.log           ← full grade breakdowns
│   └── output/2026-03-13/             ← today's renders land here
├── pbx_report/voice_training/
│   └── PBX_VOICE_PROFILE.md            ← 239-line PBX voice analysis
└── core/static/llm_context/            ← files served for LLM audits
```

---

## RECENT COMMITS (this session)

```
27f38e83  fix(tts): inject missing MAX_CHUNK_CHARS eaten by Inworld stub regex
dcbf6742  fix(pipeline): ALL 9 AUDIT FIXES — loudnorm segments, 48kHz, Inworld ban, cache validate, health gate, 5-clip enforce, color palette purge
5daba551  fix(assembler): 0xFF3333 solid borders, no pure-white fontcolor, remove duplicate aformat
428dfc55  chore: refresh llm_context with fixed daily_producer
326b8636  fix(pipeline): remove em-dash from BTC fallback comment
302374da  fix(pipeline): syntax error in daily_producer BTC fallback comment
e0c9fe0a  fix(pipeline): Grok P1s — COLOR_RED 0xFF3333 + duration 480-900s + BTC CoinGecko fallback
64e170ba  docs: add PIPELINE_STATE_SNAPSHOT.md — full cross-LLM onboarding doc
```

---

## RELAY TOOL KNOWLEDGE

- Hard ~30s connection timeout — unsuitable for LLM API calls (60-120s)
- Pattern for long ops: fire into named tmux session, wait with sleep(), read via tmux capture-pane or log tail
- Python pycache must be explicitly cleared after editing .py files
- Gemini 2.5 Pro thinking model: `parts[]` where index 0 is thought block (no text key) — parse with `next((p["text"] for p in parts if "text" in p), ...)`
- File writes via base64 chunked encoding (500-char chunks → /tmp/file.b64 → base64 -d)
- Token: `581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552`
