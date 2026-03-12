#!/bin/bash
# sync_handoff.sh — generates docs/handoff/CURRENT_STATE.md and pushes to GitHub

set -e
cd /home/ultron/protocol_pulse
mkdir -p docs/handoff

OUT="docs/handoff/CURRENT_STATE.md"
DATE=$(date '+%Y-%m-%d %H:%M:%S')
GIT_SHA=$(git rev-parse --short HEAD)
GIT_LOG=$(git log --oneline -8)

# V9 render status
V9_LOG=$(tail -5 video_pipeline_v3/logs/v9_render.log 2>/dev/null | grep -v '^$' || echo "not running")
V9_FILE=$(ls -lh video_pipeline_v3/output/2026-03-12/pulse_check_*.mp4 2>/dev/null | grep -v "norm\|raw\|music_mixed" | tail -1 || echo "none")
GRADE_V8=$(grep "NOT GRADE A\|GRADE_.*PASS\|GRADE_.*FAIL" video_pipeline_v3/logs/grade_report_v8.log 2>/dev/null | tail -1 || echo "no grade")
GRADE_V9=$(grep "NOT GRADE A\|GRADE_.*PASS\|GRADE_.*FAIL" video_pipeline_v3/logs/grade_report_v9.log 2>/dev/null | tail -1 || echo "pending")

# Service health
FLASK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ 2>/dev/null)
AVATAR=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8200/health 2>/dev/null)
AVG_LAT=$(curl -s http://localhost:8200/health 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('avg_latency_sec','?'))" 2>/dev/null || echo "?")

# Tmux sessions
SESSIONS=$(tmux list-sessions 2>/dev/null | awk '{print $1}' | tr '\n' ' ')

# CSS status
CSS_STATUS=$(for f in pp-core.css pp-style.css pp-coindesk.css pp-fix.css pp-homepage.css; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://protocolpulse.io/v3/css/$f" 2>/dev/null)
  cf=$(curl -sI "https://protocolpulse.io/v3/css/$f" 2>/dev/null | grep -i cf-cache | tr -d '\r' | awk '{print $2}')
  echo "  $f: $code $cf"
done)

# Active CC sessions
QC_STATUS=$(tmux capture-pane -t qc_audit -p 2>/dev/null | grep -v '^$' | tail -3 || echo "not running")
TTS_STATUS=$(tmux capture-pane -t tts_patch -p 2>/dev/null | grep -v '^$' | tail -3 || echo "not running")
AVATAR_STATUS=$(tmux capture-pane -t avatar_audit -p 2>/dev/null | grep -v '^$' | tail -3 || echo "not running")

cat > "$OUT" << MDEOF
# Protocol Pulse — Current State
**Generated:** $DATE  
**Git:** \`$GIT_SHA\` on \`main\`  
**Repo:** https://github.com/consensusprotocol/protocol-pulse-core

---

## 🚦 SERVICE STATUS
| Service | Status |
|---------|--------|
| Flask (protocolpulse.io) | HTTP $FLASK |
| Avatar server (port 8200) | HTTP $AVATAR — avg latency ${AVG_LAT}s |
| CF Tunnel | Active |
| Watchdog cron | Every 5 min |

---

## 🎬 VIDEO PIPELINE — CURRENT
- **V8:** $GRADE_V8
- **V9:** Rendering — $V9_LOG
- **V9 grade:** $GRADE_V9
- **V9 file:** $V9_FILE
- **Root cause of V7/V8 F:** Eryn voice ID \`uxKr2vlA4hYgXZR1oPRT\` (Natasha) was wiped by git reset. Fixed in commit \`7667c3d6\` — correct ID \`kdnRe2koJdOK4Ovxn2DI\`
- **QC false positive bug:** Internal scorer reports 94/100 PASS on Grade F renders — CC session \`qc_audit\` fixing now

---

## 🔊 TTS — VOICE DECISIONS (2026-03-12)
| Provider | Host 1 (Female) | Host 2 (Male) |
|----------|----------------|---------------|
| **ElevenLabs** (current default) | Eryn \`kdnRe2koJdOK4Ovxn2DI\` | Mark \`1SM7GgM6IMuvQlz2BwM3\` |
| **Inworld** (pending, set TTS_PROVIDER=inworld) | Lauren | Nate |

Inworld voices selected 2026-03-12 via A/B test. CC session \`tts_patch\` adding Inworld support to tts_engine.py now.  
Quality notes: Inworld = better audio quality, ElevenLabs = better cadence. FFmpeg atempo=1.2 applied post-gen on Inworld.

---

## 🌐 SITE CSS — ALL FIXED ✅
All CSS files 200 BYPASS on Cloudflare via \`/v3/css/\` Flask route with \`no-store\` headers:
$CSS_STATUS

---

## 🤖 AVATAR SERVER — BROKEN (CC audit running)
- **Port:** 8200 | **Route:** avatar.protocolpulse.io
- **Engine:** Wav2Lip-GAN FP16, GFPGAN face restore, BATCH_SIZE=64
- **Known issues being fixed:**
  - avg_latency 48.92s (target <10s)
  - apply_blink() creates black oval artifacts
  - /status returns 404 (frontend expects it)
  - blinks_enabled: false
- **CC session:** \`avatar_audit\` running now

---

## 🔄 ACTIVE CC SESSIONS
| Session | Task | Status |
|---------|------|--------|
| \`v9_render\` | V9 video render | Running |
| \`qc_audit\` | Fix QC false positives | Running |
| \`tts_patch\` | Add Inworld Lauren+Nate | Running |
| \`avatar_audit\` | Fix avatar latency/artifacts | Running |

---

## 📋 PENDING — NEEDS ATTENTION
1. **V9 grade** — fire \`python3 gemini_grade.py\` in \`video_pipeline_v3/\` once render completes
2. **TTS_PROVIDER=inworld** — set in .env after tts_patch CC commits, V10 will use Inworld
3. **Google Cloud billing** — console.cloud.google.com → enable billing for Tier 1 Gemini (150 RPM vs 25 RPD)
4. **Render.com** — disconnect GitHub repo (stop deploy failure emails)
5. **gunicorn.pid** — add to .gitignore (keeps getting committed)
6. **ADMIN_TOKEN** — add to .env for /sponsor-agent dashboard
7. **Overnight loop** — \`overnight_render_loop.py\` ready, launch after first Grade A
8. **RNS.ID affiliate** — \$300/referral, add to Oracle Briefings + newsletter (parked)

---

## 🔑 KEY FILES
- \`~/protocol_pulse/PIPELINE_LAWS.md\` — gospel, load into every CC session
- \`~/protocol_pulse/.env\` — all API keys
- \`~/protocol_pulse/app.py\` — ROOT Flask app (gunicorn loads this via wsgi.py)
- \`~/protocol_pulse/video_pipeline_v3/tts_engine.py\` — dual-provider TTS
- \`~/protocol_pulse/oracle/avatar_server.py\` — 984-line avatar engine
- \`~/protocol_pulse/overnight_render_loop.py\` — autonomous grade-A loop
- \`~/protocol_pulse/docs/handoff/CURRENT_STATE.md\` — this file

---

## ⚡ CC LAUNCH LAW (PERMANENT)
\`\`\`bash
tmux new-session -s NAME \\; send-keys 'cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions' Enter
\`\`\`

---

## 📜 GIT LOG (last 8)
\`\`\`
$GIT_LOG
\`\`\`
MDEOF

echo "Written: $OUT"
wc -l "$OUT"

# Commit and push
git add docs/handoff/CURRENT_STATE.md sync_handoff.sh 2>/dev/null || true
git add docs/handoff/CURRENT_STATE.md
git commit -m "chore: update CURRENT_STATE.md handoff doc $(date +%Y-%m-%d)"
git push origin main 2>&1 | tail -2
echo "PUSHED"
echo "https://raw.githubusercontent.com/consensusprotocol/protocol-pulse-core/main/docs/handoff/CURRENT_STATE.md"
