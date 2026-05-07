# Protocol Pulse — Claude Code Session Adapter
## See CONSTITUTION.md for the full sovereign ground truth.
## This file adds CC-specific tooling only.

## Quick Reference
- Repo: consensusprotocol/protocol-pulse-core
- Server: Waitress port 5000 (Gunicorn BANNED)
- Relay: https://relay.protocolpulse.io/exec
- DB: ~/protocol_pulse/instance/protocol_pulse.db
- All times: Eastern Time (ET)

## Session Start
Read CONSTITUTION.md before any work. It supersedes this file.
Read PIPELINE_LAWS.md before touching any video pipeline file.

## Commands
```bash
# Start website
cd ~/protocol_pulse/core && python3 -m waitress --port=5000 --threads=4 app:app

# Test render
cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --test --no-resume

# Check health
curl -s http://localhost:5000/health
```

## Inviolable (summary — full list in CONSTITUTION.md Section 11)
- NEVER expose .env / API keys
- NEVER kill avatar_server.py (PROTECTED — cuda:1, Wav2Lip/Kokoro)
- NEVER add logic to assembler.py
- NEVER use Gunicorn / Three.js / MuseTalk / SadTalker / blue+cyan+purple
- NEVER add fps=30 to render_clip.py (causes AV drift)
- AUDIT-FIRST: read every file before editing
- SYNTAX CHECK: py_compile every .py before commit
- All commits: git add + commit + push

## Session Quality Laws
- No "simplest fix" / "quick fix" / "workaround" — address root cause
- No premature "done" — show proof (curl output, test results, log evidence)
- Plan before editing >2 files. Execute one file at a time. Verify each.

## Karpathy Rules (K1-K4)
- K1: State assumptions before implementing. Verify before coding.
- K2: Flag suspicious code — do NOT silently delete.
- K3: Step → verify → step → verify on multi-file changes.
- K4: Simplicity gate — if 200 lines could be 50, rewrite.

## CC Launch (always)
unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions

## Slash Commands
/render $MODE | /fix $ISSUE | /audit $FILES | /deploy | /status
/tweet $TOPIC | /post $TEXT | /commit $MSG | /scrape $SOURCE
/check $FILE | /diagnose $PROBLEM | /brief | /pipeline-check

## Subagents
- reviewer (Sonnet) — read-only code review
- ops-monitor (Haiku) — lightweight health checks
