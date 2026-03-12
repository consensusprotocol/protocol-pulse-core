# Protocol Pulse — Current State
**Generated:** 2026-03-12 03:09:09  
**Git:** `d2dd725a` on `main`  
**Repo:** https://github.com/consensusprotocol/protocol-pulse-core

---

## 🚦 SERVICE STATUS
| Service | Status |
|---------|--------|
| Flask (protocolpulse.io) | HTTP 200 |
| Avatar server (port 8200) | HTTP 200 — avg latency 48.92s |
| CF Tunnel | Active |
| Watchdog cron | Every 5 min |

---

## 🎬 VIDEO PIPELINE — CURRENT
- **V8:** GRADE_F_FAIL|29|/home/ultron/protocol_pulse/video_pipeline_v3/output/2026-03-12/pulse_check_20260312.mp4|This episode is a catastrophic technical failure, rendered unwatchable by a complete TTS failure that cascaded into massive audio and video errors.
- **V9:** Rendering — [027] DATA [ERYN]: 19.5s
[assemble] [028] DATA [MARK]: 17.8s
[028] DATA [MARK]: 17.8s
[assemble] [029] DATA [ERYN]: 19.1s
[029] DATA [ERYN]: 19.1s
- **V9 grade:** 
- **V9 file:** -rw-r--r-- 1 ultron ultron 167M Mar 12 02:01 video_pipeline_v3/output/2026-03-12/pulse_check_20260312.mp4
- **Root cause of V7/V8 F:** Eryn voice ID `uxKr2vlA4hYgXZR1oPRT` (Natasha) was wiped by git reset. Fixed in commit `7667c3d6` — correct ID `kdnRe2koJdOK4Ovxn2DI`
- **QC false positive bug:** Internal scorer reports 94/100 PASS on Grade F renders — CC session `qc_audit` fixing now

---

## 🔊 TTS — VOICE DECISIONS (2026-03-12)
| Provider | Host 1 (Female) | Host 2 (Male) |
|----------|----------------|---------------|
| **ElevenLabs** (current default) | Eryn `kdnRe2koJdOK4Ovxn2DI` | Mark `1SM7GgM6IMuvQlz2BwM3` |
| **Inworld** (pending, set TTS_PROVIDER=inworld) | Lauren | Nate |

Inworld voices selected 2026-03-12 via A/B test. CC session `tts_patch` adding Inworld support to tts_engine.py now.  
Quality notes: Inworld = better audio quality, ElevenLabs = better cadence. FFmpeg atempo=1.2 applied post-gen on Inworld.

---

## 🌐 SITE CSS — ALL FIXED ✅
All CSS files 200 BYPASS on Cloudflare via `/v3/css/` Flask route with `no-store` headers:
  pp-core.css: 200 BYPASS
  pp-style.css: 200 BYPASS
  pp-coindesk.css: 200 BYPASS
  pp-fix.css: 200 BYPASS
  pp-homepage.css: 200 BYPASS

---

## 🤖 AVATAR SERVER — BROKEN (CC audit running)
- **Port:** 8200 | **Route:** avatar.protocolpulse.io
- **Engine:** Wav2Lip-GAN FP16, GFPGAN face restore, BATCH_SIZE=64
- **Known issues being fixed:**
  - avg_latency 48.92s (target <10s)
  - apply_blink() creates black oval artifacts
  - /status returns 404 (frontend expects it)
  - blinks_enabled: false
- **CC session:** `avatar_audit` running now

---

## 🔄 ACTIVE CC SESSIONS
| Session | Task | Status |
|---------|------|--------|
| `v9_render` | V9 video render | Running |
| `qc_audit` | Fix QC false positives | Running |
| `tts_patch` | Add Inworld Lauren+Nate | Running |
| `avatar_audit` | Fix avatar latency/artifacts | Running |

---

## 📋 PENDING — NEEDS ATTENTION
1. **V9 grade** — fire `python3 gemini_grade.py` in `video_pipeline_v3/` once render completes
2. **TTS_PROVIDER=inworld** — set in .env after tts_patch CC commits, V10 will use Inworld
3. **Google Cloud billing** — console.cloud.google.com → enable billing for Tier 1 Gemini (150 RPM vs 25 RPD)
4. **Render.com** — disconnect GitHub repo (stop deploy failure emails)
5. **gunicorn.pid** — add to .gitignore (keeps getting committed)
6. **ADMIN_TOKEN** — add to .env for /sponsor-agent dashboard
7. **Overnight loop** — `overnight_render_loop.py` ready, launch after first Grade A
8. **RNS.ID affiliate** — $300/referral, add to Oracle Briefings + newsletter (parked)

---

## 🔑 KEY FILES
- `~/protocol_pulse/PIPELINE_LAWS.md` — gospel, load into every CC session
- `~/protocol_pulse/.env` — all API keys
- `~/protocol_pulse/app.py` — ROOT Flask app (gunicorn loads this via wsgi.py)
- `~/protocol_pulse/video_pipeline_v3/tts_engine.py` — dual-provider TTS
- `~/protocol_pulse/oracle/avatar_server.py` — 984-line avatar engine
- `~/protocol_pulse/overnight_render_loop.py` — autonomous grade-A loop
- `~/protocol_pulse/docs/handoff/CURRENT_STATE.md` — this file

---

## ⚡ CC LAUNCH LAW (PERMANENT)
```bash
tmux new-session -s NAME \; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
```

---

## 📜 GIT LOG (last 8)
```
d2dd725a feat(tts): add Inworld provider Lauren+Nate (TTS_PROVIDER=inworld), ElevenLabs default
7667c3d6 fix(tts): RESTORE Eryn voice kdnRe2koJdOK4Ovxn2DI (lost in git reset, wiped V6 fix)
20bcca4c fix(site): rename pp-lightfix -> pp-fix to bypass CF cached 404
8503e711 fix(site): rename pp-core->pp-main, pp-lightfix->pp-fixes to clear CF 404 cache
bfc4eeb4 fix(site): extract all inline CSS from templates — zero <style> tags remaining
104b6e50 fix(site): base.html - use pp-core/pp-coindesk/pp-lightfix names, all v3/css BYPASS
cbdba781 fix(site): rename style.css/session15 to pp-style/pp-homepage to bypass CF 404 cache
84bcc2c1 fix(site): base.html CSS paths -> /v3/css/ with no-store bypass
```
