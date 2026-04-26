# Protocol Pulse — Claude Code Constitution

## Project
Protocol Pulse (protocolpulse.io) — autonomous Bitcoin intelligence platform.
Flask/Python backend on Ultron (AMD EPYC 9R14, 4x RTX 4090, 128GB RAM, Ubuntu 24.04).
Served by Waitress on port 5000 via Cloudflare tunnel.

## Architecture
```
core/app.py                    — Flask app entry point
core/routes_admin.py           — Admin endpoints
core/routes_api.py             — API endpoints  
core/routes_auth.py            — Auth + Stripe
core/routes_pages.py           — Page rendering
services/                      — Business logic (tweet_machine, morning_brief, etc.)
video_pipeline_v3/             — Video production pipeline (SPLIT into modules)
  assembler.py                 — THIN orchestrator (<1,800 lines) — DO NOT add logic here
  render_narrator.py           — PBX narration scenes
  render_clip.py               — Partner channel clip scenes
  render_social.py             — Tweet cards + Nostr signal
  render_intro_outro.py        — Intro/outro/cold open
  render_data.py               — Charts + data overlays
  audio_master.py              — LUFS normalization, music mixing
  transitions.py               — Crossfades between segments
  lower_thirds.py              — Branded overlays
```

## Commands
```bash
# Start website
cd ~/protocol_pulse/core && python3 -m waitress --port=5000 --threads=4 app:app

# Test render
cd ~/protocol_pulse/video_pipeline_v3 && python3 daily_producer.py --test --no-resume

# Fire tweet
cd ~/protocol_pulse && python3 services/tweet_machine.py

# Refresh brief
cd ~/protocol_pulse && python3 services/morning_brief.py

# Check health
curl -s http://localhost:5000/health
```

## Coding Standards
- Python 3.10+, Flask blueprints
- All commits: git add + commit + push (NEVER leave uncommitted .py files)
- Syntax check every .py edit: python3 -m py_compile <file>
- Git repo: consensusprotocol/protocol-pulse-core

## INVIOLABLE RULES
- NEVER print .env contents or expose API keys
- NEVER sed .env files — use nano
- NEVER start avatar_server.py (HeyGen broken, wastes 6GB RAM)
- NEVER export ANTHROPIC_API_KEY before CC
- NEVER force push to git
- NEVER add logic to assembler.py — use the split modules
- AUDIT-FIRST: Read files before changing them
- TRIPLE-VERIFY: Test output, test from different angle, confirm live
- Waitress serves port 5000. Gunicorn is RETIRED.
- Ollama models auto-unload after 5 min idle
- All time references in Eastern Time (ET) for PBX
- Video pipeline: read PIPELINE_LAWS.md and LOCKED_FIXES.md before touching any pipeline file
- REGRESSION TEST: Run `bash video_pipeline_v3/regression_test.sh` before any pipeline commit
- aresample=async=1 is BANNED everywhere except clip_extractor.py fix_av_sync()

## SESSION QUALITY LAWS

### LAW: NO "SIMPLEST FIX" SHORTCUTS
- NEVER use the phrase "simplest fix", "quick fix", "simple solution", "easiest approach", or "let me just"
- Every fix must address the ROOT CAUSE, not the symptom
- If you catch yourself proposing a hack, STOP. Read the surrounding code. Understand WHY it broke. Fix the actual problem.
- BANNED PHRASES: "simplest fix", "quick fix", "the easiest way", "let me just", "for now we can", "as a workaround", "temporary fix"

### LAW: READ BEFORE EDIT (MANDATORY)
- NEVER edit a file without reading it first in the same session
- Before ANY file modification, you MUST have read that file with the view/read tool in this session
- If you find yourself about to edit a file you haven't read, STOP and read it first
- This prevents the #1 cause of regressions: editing code you don't understand

### LAW: SELF-VERIFICATION BEFORE "DONE"
- NEVER claim a task is complete without verification
- After implementing, you MUST:
  1. Run the code or test it
  2. Verify the output matches expectations
  3. Check for regressions (did you break anything else?)
  4. If it is a web page: curl the URL and confirm it returns expected content
  5. If it is a script: run it and show the output
- "It should work" is NOT verification. Show proof.

### LAW: NO PREMATURE SESSION ENDING
- NEVER suggest ending a session early, calling it a day, or wrapping up
- NEVER say "it is getting late", "we have accomplished a lot", "let us pick this up later"
- Complete the task fully or explicitly state what remains incomplete and why
- The user decides when the session ends, not you

### LAW: NO OWNERSHIP DODGING
- NEVER say "this was pre-existing", "this is unrelated to my changes", or "this test was already failing"
- If a test fails after your changes, investigate it regardless of whether you caused it
- If you broke something, own it immediately and fix it

### LAW: COMPLETE THE FULL TASK
- If given a list of items to implement, implement ALL of them
- NEVER implement 80% and then summarize the rest as "remaining items"
- If you cannot complete an item, explain specifically WHY (not just "time constraints")
- Do not ask the user if they want you to continue. Just continue.

### LAW: NO HALLUCINATED REFERENCES
- NEVER reference a file path, function name, API endpoint, git SHA, package version, or configuration value from memory
- ALWAYS verify by reading the actual file, running the actual command, or checking the actual state
- If you are unsure whether something exists, CHECK before referencing it

### PRE-COMMIT VERIFICATION TEMPLATE
Every session must run before committing:
```
=== PRE-COMMIT VERIFICATION ===
1. All modified files compile: python3 -m py_compile [each file]
2. No import errors: python3 -c "import [module]" for each modified module
3. If web routes changed: curl every affected URL and confirm 200
4. If cron scripts changed: run the script once and confirm no errors
5. Git diff review: git diff --stat to confirm only intended files changed
6. No secrets exposed: grep for API keys, tokens, passwords in diff
```

## When Compacting
Preserve: list of modified files, current test status, active render status, any errors encountered.


## Plan Mode (MANDATORY for multi-file changes)
When a task touches more than 2 files:
1. PLAN FIRST: Outline what files will change and why
2. WAIT for confirmation or proceed if autonomous
3. THEN implement one file at a time
4. Syntax check after each file
5. Test integration after all files done

Never start editing 5 files at once. Plan → execute → verify.

## Available Slash Commands
Type /help to see all. Key commands:
- /render $MODE — fire video render (test/fast/full/reuse)
- /fix $ISSUE — audit-first fix protocol
- /audit $FILES — cross-LLM code audit
- /deploy — full health check
- /status — system dashboard
- /tweet $TOPIC — generate + post tweet
- /post $TEXT — post specific tweet text
- /commit $MSG — standardized git commit
- /scrape $SOURCE — trigger social scrapers (x/nostr/spaces/all)
- /check $FILE — audit single file
- /diagnose $PROBLEM — trace root cause without fixing
- /brief — refresh morning intelligence brief
- /pipeline-check — pre-render verification

## Subagents
- reviewer (Sonnet) — code review specialist, invoked for auditing
- ops-monitor (Haiku) — lightweight health checks

## KARPATHY RULES (added 2026-04-25)
Derived from Andrej Karpathy LLM coding pitfall observations (83K GitHub stars).

### K1: STATE ASSUMPTIONS BEFORE IMPLEMENTING
Before any fix, write: I believe X causes Y because Z -- and VERIFY Z before coding.
If uncertain between two approaches, present both. Do not pick silently.

### K2: MENTION DONT DELETE
If you see dead code or suspicious patterns unrelated to your task, FLAG them -- do NOT silently remove.

### K3: STEP-VERIFY LOOP (mandatory for multi-file changes)
Every fix: Step 1 action -> verify specific check -> Step 2 action -> verify -> proceed only on pass.

### K4: SIMPLICITY GATE
Before committing: Would a senior engineer say this is overcomplicated? If 200 lines could be 50, rewrite.
