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


## ANTHROPIC PROMPTING BEST PRACTICES (added 2026-05-11)
Derived from Anthropic Applied AI team workshop (Hannah + Christian, Prompting 101).
These apply to ALL Claude interactions: CC sessions, script writer prompts, clip selection, audits.

### P1: STRUCTURE EVERY PROMPT
Follow this order every time:
  1. Task context — what are we doing, what is Claude's role
  2. Tone context — factual, confident, no guessing
  3. Background data — static info that never changes (form structure, pipeline laws, file layouts)
  4. Dynamic content — the specific data for this run (clips, scripts, error logs)
  5. Detailed instructions — step-by-step how to analyze/execute
  6. Examples — concrete input/output pairs for tricky cases
  7. Output format — XML tags, JSON, or specific structure for the response
  8. Task reminder — repeat critical constraints at the end

### P2: CONTEXT BEFORE ANALYSIS
Order of information matters. Claude should read background BEFORE analyzing data.
Bad: "Fix this error" + paste traceback
Good: "You are debugging assembler.py. It has 20+ run_ffmpeg calls with different timeouts.
       Here is the function signature. Here is the traceback. Find which call caused this."

### P3: ONE CHANGE, ONE TEST
Prompt engineering is iterative empirical science. Change ONE thing, test, observe.
Never change 5 things at once. Never claim fixed without running the test.
If a fix requires multiple files: change file 1 -> verify -> change file 2 -> verify.

### P4: PREVENT HALLUCINATION
Always include: "Only state what you can verify from the code/data provided."
Always include: "If uncertain, say so. Do not guess."
For CC sessions: "Show your work. Grep to verify before claiming done."

### P5: STATIC CONTEXT IN SYSTEM PROMPT
Information that never changes between runs goes in the system prompt:
  - Pipeline file structure and module responsibilities
  - Brand rules, encoding specs, voice settings
  - Known failure patterns and their fixes
This is what CLAUDE.md and PIPELINE_LAWS.md already do. Keep them current.

### P6: OUTPUT FORMATTING
Tell Claude exactly how to format output. Use XML tags for structured data.
For CC sessions: "Commit message must include grep verification results."
For audits: "Wrap findings in <critical>, <high>, <medium> tags."
For script writer: "Wrap final script in <script> tags with JSON structure."

### P7: PREFILL WHEN POSSIBLE
When using the API, prefill Claude's response to enforce format.
For clip selection: start response with opening JSON bracket.
For script generation: start with the script header structure.
This eliminates preamble and forces structured output.

### P8: USE EXTENDED THINKING AS DIAGNOSTIC
Enable extended thinking to see HOW Claude reasons about your data.
Use this to find where Claude's logic diverges from yours.
Build corrections into the system prompt based on thinking patterns.
