# PROTOCOL PULSE — PIPELINE STATE SNAPSHOT
## For: Cross-LLM Debugging / Onboarding
## Generated: 2026-03-13
## Repo: github.com/consensusprotocol/protocol-pulse-core

---

## WHAT THIS IS

Paul (PBX) runs an autonomous daily Bitcoin video pipeline on a self-hosted server called Ultron
(AMD EPYC 9R14 / 4x RTX 4090, Naples FL). This document is the full state snapshot so any LLM
can get up to speed instantly without re-diagnosing known issues.

**The product:** "Pulse Check" — daily ~10 min Bitcoin intelligence video, two AI hosts (Eryn +
Mark), partner channel clips, gold info bar, cyberpunk aesthetic. Rendered daily at 14:00 via cron.

**Current status:** Chasing first Grade A render (Gemini 2.5 Pro grader, 0-100). Best so far: F(34).
Root cause of most failures: TTS voice ID bugs (now fixed). See KNOWN BUGS section.

---

## INFRASTRUCTURE

```
Server: Ultron — 192.168.1.152 (LAN) / ssh.protocolpulse.io (CF tunnel)
Relay:  https://relay.protocolpulse.io/exec  (POST JSON, token below)
        Headers: User-Agent: Mozilla/5.0
        Body: {"token": "581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552", "cmd": "..."}
        HARD LIMIT: 30s timeout — use tmux for long ops

Flask app:    port 5000 (gunicorn), CF tunnel → protocolpulse.io
Video server: port 5100
Oracle Live:  port 8202 (FastAPI)
Avatar:       port 8200 (Wav2Lip-GAN, Wav2Lip ONLY — MuseTalk/SadTalker BANNED)
```

## CC LAUNCH LAW (INVIOLABLE)
```bash
tmux new-session -s NAME \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
```
- NEVER use `-p` flag — produces shallow work
- NEVER export ANTHROPIC_API_KEY before launching — CC uses Max subscription
- ONE CC session at a time — never parallel on same repo

---

## DIRECTORY STRUCTURE

```
~/protocol_pulse/
├── video_pipeline_v3/          ← THE PIPELINE (gospel files inside)
│   ├── daily_producer.py       ← main orchestrator (893 lines)
│   ├── assembler.py            ← FFmpeg assembly (4019 lines)
│   ├── tts_engine.py           ← TTS dual-provider (679 lines)
│   ├── gemini_grade.py         ← Gemini 2.5 Pro grader (360 lines)
│   ├── manifest_builder.py     ← episode manifest
│   ├── clip_scorer.py          ← 0-100 clip scoring
│   ├── tts_cache/              ← SHA256-keyed .m4a cache
│   ├── output/YYYY-MM-DD/      ← rendered episodes
│   ├── logs/
│   │   ├── grade_report.log    ← Gemini grade breakdowns
│   │   └── v6_render.log       ← active render log
│   └── assets/
│       ├── music/              ← 30 Suno tracks
│       └── sfx/custom_whoosh.mp3
├── dual_gpu_orchestrator.py    ← runs both GPUs continuously (515 lines)
├── PIPELINE_LAWS.md            ← GOSPEL — load into every CC session
├── PIPELINE_LESSONS.md         ← append-only lessons log (518+ lines)
├── utils/notify.py             ← Telegram + Twilio alerts
├── promote_to_stable.sh        ← grade-gated branch promotion
├── render_watcher.py           ← sends download link on render complete
├── pbx_report/
│   └── voice_training/         ← 19 transcripts + PBX_VOICE_PROFILE.md
│       └── PBX_VOICE_PROFILE.md ← 239-line PBX voice analysis
├── docs/gospels/               ← 10 gospel spec files
└── .env                        ← all API keys (never paste in chat)
```

---

## PIPELINE_LAWS.md (FULL — load this into every session)

```
# PROTOCOL PULSE — PIPELINE LAWS

## PIXEL ZONES (confirmed spec)
- Background: full 1920×1080, color #0A0A0F (never pure black #000000)
- Text zone (narration): x=40-960, y=80-760 (left half only)
- PiP zone: x=960-1880, y=0-540 (top right)
- Subtitle band: y=778-885, full width (1920px), dark glass rgba(0,0,0,0.75), 4px red left bar
- Info rail (gold): bottom, y≈1032-1080, full width, #F8C15C text
- Title card: full canvas, no thumbnail bleed

## COLOR PALETTE (locked)
- Background: #0A0A0F (VDS dark navy)
- Accent / border: #FF3333 (red, 2px borders)
- Gold info text: #F8C15C
- Primary text: #FFFFFF
- Subtitle band bg: rgba(0,0,0,0.75) + blur

## AUDIO TARGETS (locked)
- Integrated LUFS: -14 ±2
- True peak: ≤ -2.0dBTP  ← alimiter added 2026-03-13 at all 4 assembly points
- LRA: 7 LU
- Single loudnorm: only in concatenate_parts() — no per-segment loudnorm
- Sample rate: 48000 Hz
- Bitrate: 192k (audio)

## TTS (locked)
- Provider: ElevenLabs (TTS_PROVIDER=elevenlabs in .env)
- Host 1 (Eryn):  voice_id=kdnRe2koJdOK4Ovxn2DI, speed=1.12x
- Host 2 (Mark):  voice_id=1SM7GgM6IMuvQlz2BwM3, speed=1.10x
- Model: eleven_turbo_v2_5
- BOTH voices MUST render in every episode
- Speed param: top-level body param, NOT inside voice_settings
- Fallback: ElevenLabs → pyttsx3 → gTTS → silence (silence = instant F grade)
- Cache: tts_cache/ SHA256(voice_id:segment_type:text)[:16].m4a

## BANNED VOICES (ElevenLabs)
Nicole, Jessica (in host role), Sarah, Matilda, Gigi
BANNED voice IDs: uxKr2vlA4hYgXZR1oPRT (deleted/invalid — caused 2 days of failures)

## FFMPEG TIMEOUTS (locked)
- Default: 300s
- Heavy filtergraphs (make_intro_coldopen, PiP): 300s minimum
- concatenate_parts(): 600s

## TIMING SPEC
- Title card: 2.0s exactly
- Cold open: 10-14s
- Narration segments: 15-35s each
- Clip segments: natural duration
- Tweet cards: 8-12s
- Outro: 10-15s abrupt end (NO fade — EVER)
- Total: 8-15 minutes (script word budget: 1040 words max)

## VISUAL RULES
- Logo: title card + watermark + outro ONLY — never in narration segments
- No debug overlays — instant F grade if visible
- Cold open: NO logos, bars, watermarks — pure dramatic clip
- Continuous BGM: mixed ONCE in concatenate_parts()
- Gold info bar: single non-negotiable signature element — always present
- Outro ends ABRUPTLY — no fade

## PRODUCTION RULES
- debug_mode = False always
- 5 clips from 5 different channels (hard rule)
- 3Mbps minimum bitrate (below = warning)
- Sentence boundary detection on all clips
- 0.3s clip fade in / 0.5s clip fade out
- Duplicate outro removal
- Per-tweet social card rendering
```

---

## TTS ENGINE — CURRENT STATE

```python
# File: video_pipeline_v3/tts_engine.py (679 lines)
# Provider: ElevenLabs (TTS_PROVIDER=elevenlabs)

_NATASHA_VOICE = {         # HOST 1 — Eryn
    "voice_id": "kdnRe2koJdOK4Ovxn2DI",
    "name": "Eryn",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.12,
    "voice_settings": {"stability": 0.55, "similarity_boost": 0.80,
                        "style": 0.15, "use_speaker_boost": True},
}

_MARK_VOICE = {             # HOST 2 — Mark
    "voice_id": "1SM7GgM6IMuvQlz2BwM3",
    "name": "Mark",
    "model_id": "eleven_turbo_v2_5",
    "speed": 1.10,
    "voice_settings": {"stability": 0.55, "similarity_boost": 0.80,
                        "style": 0.15, "use_speaker_boost": True},
}

# Inworld configs exist but TTS_PROVIDER=elevenlabs — Inworld synthesis returns
# HTTP 200 with 0 bytes (account not provisioned for synthesis). DO NOT switch back.
```

---

## AUDIO ASSEMBLY — alimiter LOCATIONS

All 4 audio filter chains in `assembler.py` end with:
```
loudnorm=I=-14:TP=-2.0:LRA=7,alimiter=limit=0.891:level=disabled:attack=5:release=50,...[outa]
```
Lines: 583, 1028, 2267, 2485 (as of commit 9261ebb9)

---

## DUAL-GPU ORCHESTRATOR

```python
# File: dual_gpu_orchestrator.py (515 lines)
# PIPELINE = ~/protocol_pulse/video_pipeline_v3
# Both GPUs render from same PIPELINE dir (no worktrees — they fail silently)

# GPU 0: runs render-stable branch
# GPU 1: runs main branch
# Both restart immediately after finish
# If GPU1 beats GPU0 → promote main → render-stable

# find_latest_video: checks today AND yesterday (midnight rollover fix 2026-03-13)
# Requires >10MB file size to reject corrupt/empty renders
```

---

## KNOWN BUGS — FIXED

| Bug | Root Cause | Fix | Commit |
|-----|-----------|-----|--------|
| All Eryn narration silent | Wrong voice ID `uxKr2vlA4hYgXZR1oPRT` (deleted) | Correct ID `kdnRe2koJdOK4Ovxn2DI` in tts_engine.py | pre-existing in tts_engine |
| Inworld TTS 404 → switched to inworld | EL bad ID not diagnosed | TTS_PROVIDER=elevenlabs restored | 5f732791 |
| Inworld synthesis 0 bytes | Account not provisioned for synthesis | Reverted to ElevenLabs | 5f732791 |
| True peak +0.4 dBTP | alimiter missing from filter chains | alimiter at all 4 assembly points | 9261ebb9 |
| Orchestrator blind after midnight | find_latest_video only checked today's dir | Check today + yesterday within 12h | 5f732791 |
| Worktrees failed silently | Transcripts gitignored, worktree had 0 data | Both GPUs run from PIPELINE directly | f86b7fe3 |
| part_018 corrupt (48 bytes) | Unknown — monitor | Worktree fix likely resolved | f86b7fe3 |
| Duplicate outro | Assembler bug | Duplicate removal committed | earlier |

---

## KNOWN BUGS — OPEN

| Bug | Symptom | Priority |
|-----|---------|----------|
| Script generates 603s, QC max 600s | Duration cap warning | P2 — word budget in script_writer.py |
| Watchdog false positives | flask_main/video_server "stalled" alerts are noise | P3 |
| Dual app.py | core/app.py has hardcoded dev secret key | P2 |
| Resend domain unverified | No overnight email alerts | P3 |
| Channel scanner not on cron | Manual trigger only | P3 |

---

## ENFORCEMENT SYSTEMS

```
Pre-commit hook:     .git/hooks/pre-commit — fires cross_llm_audit.py on every commit
GitHub Actions:      .github/workflows/pipeline_gate.yml — blocks bad pushes
                     .github/workflows/heartbeat.yml — 6h dead-man's switch
Telegram alerts:     utils/notify.py — TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env
Twilio SMS:          utils/notify.py — TWILIO_* in .env
Promote gate:        promote_to_stable.sh — grade-gated branch promotion
Render watcher:      render_watcher.py — sends download link on render complete
Best grade tracking: logs/best_grade.json — {"score": 0} — first Grade A promotes
```

---

## CROSS-LLM AUDIT LAW (INVIOLABLE)

Every feature:
1. Claude Code builds full working code
2. `~/protocol_pulse/utils/cross_llm_audit.py` fires — Gemini + GPT-4o + Grok PARALLEL audit ACTUAL CODE (never specs)
3. Claude synthesizes Cycle 1 consensus
4. Cycle 2 — models cross-validate
5. Second CC pass on P0+P1 issues
6. Merge

NEVER skip. NEVER merge without it. Script: `~/protocol_pulse/utils/cross_llm_audit.py`

---

## API KEYS IN .env (keys only — never share values)

```
ANTHROPIC_API_KEY     ← spend cap raised to $500
ELEVENLABS_API_KEY    ← active Pro tier, 37k/500k chars used
GEMINI_API_KEY        ← was auto-revoked Mar 2, replace in console (green checkmark Sep 2025 key)
OPENAI_API_KEY        ← quota sometimes exhausted
XAI_API_KEY           ← Grok, credits sometimes exhausted
HEYGEN_API_KEY        ← PBX avatar $2/min, Sarah avatar $1/min
INWORLD_API_KEY       ← voices endpoint works, synthesis returns 0 bytes — DO NOT USE for TTS
TELEGRAM_BOT_TOKEN    ← @Proto_P_bot
TELEGRAM_CHAT_ID      ← PBX personal account
TWILIO_*              ← SMS alerts, paid account
TTS_PROVIDER=elevenlabs
GEMINI_MODEL=gemini-2.5-pro-exp-03-25
```

---

## GRADER — GEMINI GRADE CRITERIA (100 points)

```
host_authenticity    10pts — both hosts must speak, no silence gaps
episode_title        10pts — proper title card
no_filler            10pts — no dead air, no repeated content
timeliness           10pts — Bitcoin news from last 24-48h
music_mix            10pts — BGM present, ducked under voice (-18dB idle → -30dB under voice)
transitions          10pts — whoosh SFX, smooth cuts
visual_polish        10pts — no freeze frames, correct aesthetic
no_artifacts         10pts — no black frames, no corruption
audio_quality        10pts — clean narration, correct LUFS/TP
pacing               10pts — natural flow, 8-15 min total
```

Grade A = 90+. Currently best: F(34). Target before building PBX Report pipeline.

---

## ORACLE / AVATAR SYSTEMS

```
Avatar server: port 8200 — avatar.protocolpulse.io
Model: Wav2Lip-GAN FP16, GPU-cached, 3.8s generation, 134fps on 4090, batch_size=48
Voice: Jessica (cgSgspJ2msm6clMCkdW9) — ElevenLabs
KNOWN BUG: apply_blink() creates black oval artifacts — replace body with `return frame`
BANNED: MuseTalk, SadTalker — Wav2Lip ONLY

HeyGen avatars:
- PBX avatar:   3be8ed14b0954b898f4127836c21f6cc ($2/min) — for PBX Report pipeline
- Sarah avatar: d259c335741f4fc0b061e04c59388b4e ($1/min) — Oracle Briefings
```

---

## PBX REPORT PIPELINE (IN PROGRESS — DO NOT BUILD YET)

Parallel pipeline to Pulse Check. Same clip infrastructure, different editorial voice.
PBX HeyGen avatar replaces narrator. Investigative, dry, opinionated Bitcoin journalism.

Status: Spec written. 19 voice training transcripts scraped (144,305 words).
Voice profile: `pbx_report/voice_training/PBX_VOICE_PROFILE.md`
Full spec: `/tmp/pbx_report_spec.md` (not yet committed)

**Build trigger:** Pulse Check hits Grade A. Then fire CC with spec on freed GPU.

---

## GIT LOG (last 15 commits)

```
5f732791  fix(tts+orch): elevenlabs TTS restored + midnight date rollover fix
e54fd122  fix(orchestrator): find_latest_video today-only + 10MB gate
9261ebb9  fix(audio): alimiter hard ceiling after loudnorm at all assembly points
f86b7fe3  fix(orchestrator): remove worktrees entirely, both GPUs use PIPELINE
b1f16532  fix(orchestrator): disable git worktrees (failing silently)
5b5752d2  fix(orchestrator): shutil import scope fix in worktree env setup
ca4922ff  fix(orchestrator): symlink .env into worktree
936ecc3b  [HOTFIX-EXEMPT] feat(enforcement): Telegram/Twilio + GitHub Actions
1f31793e  feat(enforcement): dual-GPU orchestrator + audit gate + pre-commit hook
5457a56c  feat(audit): add tts-pipeline feature to cross_llm_audit + gospel
dc2d4ff6  fix(tts): show real ffmpeg error (tail not head)
14054a91  fix(tts): .m4a output path + ElevenLabs key gate + loop TypeError fix
9286214c  CRITICAL: permanently disable CC fix sessions
846cc5cb  fix(clips): reset episode memory, increase selector sample 20->60
f38dce3a  fix(loop): TTS preflight + deterministic fix map
```

---

## MORNING CHECK COMMANDS

```bash
# Grade result
tail -20 ~/protocol_pulse/video_pipeline_v3/logs/grade_report.log

# Orchestrator alive?
ps aux | grep dual_gpu_orchestrator | grep -v grep
tail -5 ~/protocol_pulse/logs/orchestrator.log

# Both GPUs?
nvidia-smi --query-gpu=index,utilization.gpu,power.draw --format=csv,noheader
ps aux | grep daily_producer | grep -v grep | wc -l

# TTS confirmed ElevenLabs?
grep TTS_PROVIDER ~/protocol_pulse/.env

# alimiter confirmed?
grep -c "alimiter" ~/protocol_pulse/video_pipeline_v3/assembler.py
# should return 4

# Bad voice ID gone?
grep -r "uxKr2vlA4hYgXZR1oPRT" ~/protocol_pulse/video_pipeline_v3/
# should return nothing

# Latest render
ls -lh ~/protocol_pulse/video_pipeline_v3/output/*/pulse_check_*.mp4 2>/dev/null | grep -v '\.' | tail -3

# Best grade
cat ~/protocol_pulse/logs/best_grade.json

# Render watcher alive?
ps aux | grep render_watcher | grep -v grep
```

---

## ANTI-PATTERNS — THINGS THAT HAVE BROKEN THIS PIPELINE

1. **CC sessions reverting fixes** — CC would "fix" a file and undo proven fixes. Commit 9286214c permanently disabled this. Never let CC touch a file it didn't write.
2. **Switching TTS providers without diagnosing the actual error** — Spent 2 days on Inworld because nobody stopped to check which voice ID was 404ing. Always `curl` the actual failing call first.
3. **Parallel CC sessions on same repo** — causes git conflicts and pycache collisions. One session at a time.
4. **Not clearing pycache after edits** — `find . -name '__pycache__' -exec rm -rf {} +` after any .py file change.
5. **Using `-p` flag with Claude Code** — rushes to complete, produces shallow work.
6. **Worktrees with gitignored data** — transcripts are gitignored, worktrees had 0 data, renders crashed in 1 second.
7. **Inworld TTS** — voices list endpoint works, synthesis returns 0 bytes. Account likely not provisioned. ElevenLabs is the correct provider.
8. **Running audits on specs instead of code** — cross-LLM audit must run on actual committed code, not design docs.

---

## VOICE REFERENCE TABLE

| Role | Provider | Voice ID | Speed | Notes |
|------|----------|----------|-------|-------|
| HOST_1 Eryn | ElevenLabs | kdnRe2koJdOK4Ovxn2DI | 1.12x | Setup/bridge host |
| HOST_2 Mark | ElevenLabs | 1SM7GgM6IMuvQlz2BwM3 | 1.10x | Contrarian/react host |
| Oracle Jessica | ElevenLabs | cgSgspJ2msm6clMCkdW9 | 1.0x | Oracle briefings only |
| PBX HeyGen | HeyGen | 3be8ed14b0954b898f4127836c21f6cc | — | PBX Report pipeline |
| Sarah HeyGen | HeyGen | d259c335741f4fc0b061e04c59388b4e | — | Social shorts |

**BANNED voices:** Nicole, Gigi, Sarah (EL), Matilda, Jessica (in host role)
**BANNED IDs:** uxKr2vlA4hYgXZR1oPRT (deleted — caused 48h of silent renders)

---

## WHAT TO WORK ON NEXT (IN ORDER)

1. ✅ ElevenLabs TTS restored with correct voice IDs
2. ✅ alimiter at all 4 assembly points
3. ✅ Date rollover fix in find_latest_video
4. ⏳ **First Grade A render** — all fixes applied, render running now
5. 🔒 PBX Report pipeline build (blocked on Grade A)
6. 🔒 Sovereignty Stack (specced, not built)
7. 🔒 Sponsor Agent (specced in SPONSOR_AGENT_SPEC.md, not built)
8. 🔒 Pulse Terminal v3.0 ($19/$49/$99 tiers)
