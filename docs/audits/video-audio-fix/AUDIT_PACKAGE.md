# PROTOCOL PULSE — CODE AUDIT PACKAGE
# Feature: video-audio-fix
# Branch: feature/video-audio-fix
# Generated: 2026-05-30 04:42 UTC
# Purpose: Pre-merge quality gate. 3 independent AI models will review this.
# You are one of: Gemini 2.5 Pro / GPT-4o / Grok-3
# Other top AI models will also review this same code. Put your best work forward.

---

## WHAT THIS FEATURE DOES
(see gospel)

---

## GOVERNING LAWS (this code MUST comply with every law below — flag any violation)
## THE LAWS (from PIPELINE_LAWS.md)
### Always run auto-forensic after render: ffprobe, blackdetect, silencedetect, ebur128
### Never skip regression_test.sh — zero FAILs before commit
### AV sync diagnosis first: check raw clips before touching assembler
### Audio target: -14 LUFS integrated, -1 dBTP ceiling, music at -14 LUFS with sidechain



---

## TECHNOLOGY STACK
- Python 3.12, Flask 3.x, SQLite via SQLAlchemy ORM
- Ubuntu 24.04 on Ultron server (2x RTX 4090, 93GB RAM)
- All UI animations: CSS/SVG only — NO Three.js, no WebGL, no Canvas
- External services: ElevenLabs TTS, HeyGen avatars, Wav2Lip GPU lip-sync
- ~1000 concurrent users at peak — every route must handle load
- Every DB query on a sort/filter column MUST have an index

---

## THE CODE (every new and modified file)

### File: .claude/agents/ops-monitor.md (20 lines)
```
   1 | ---
   2 | name: ops-monitor
   3 | description: Lightweight health monitor for Protocol Pulse. Checks processes, RAM, GPU, endpoints.
   4 | model: claude-haiku-4-5-20251001
   5 | tools:
   6 |   deny:
   7 |     - Write
   8 |     - Edit
   9 | ---
  10 | # Ops Monitor Agent
  11 | Quick health checks:
  12 | 1. Waitress on port 5000
  13 | 2. RAM (warn <30GB free)
  14 | 3. GPU VRAM (warn <3GB free)
  15 | 4. Zombie processes (avatar_server, ollama)
  16 | 5. Crons (watchdog, tweets, morning brief)
  17 | 6. Render status
  18 | 7. Disk space
  19 | Report: GREEN/YELLOW/RED per check. Keep SHORT.
  20 | 
```

### File: .claude/agents/reviewer.md (20 lines)
```
   1 | ---
   2 | name: reviewer
   3 | description: Code review specialist for Protocol Pulse. Reviews Python code for bugs, style, and pipeline compliance. Read-only.
   4 | model: claude-sonnet-4-20250514
   5 | tools:
   6 |   deny:
   7 |     - Write
   8 |     - Edit
   9 | skills:
  10 |   - pipeline-fix
  11 | ---
  12 | # Code Reviewer Agent
  13 | You are a senior code reviewer for Protocol Pulse video pipeline.
  14 | 1. Read the code changes or files specified
  15 | 2. Check for bugs, edge cases, error handling
  16 | 3. Verify compliance with PIPELINE_LAWS.md
  17 | 4. Check logging and error messages
  18 | 5. Report: CRITICAL / WARNING / INFO findings
  19 | NEVER edit files yourself. Report only.
  20 | 
```

### File: .claude/commands/audit.md (10 lines)
```
   1 | Run cross-LLM audit on: $ARGUMENTS
   2 | 
   3 | Follow AUDIT-FIRST LAW:
   4 | 1. Read every file mentioned — understand before changing
   5 | 2. For each file, identify: bugs, fragility, quality killers, architecture smell
   6 | 3. Grade each function A-F with specific reasoning
   7 | 4. Provide exact code diffs for every fix (not vague suggestions)
   8 | 5. Syntax check all changes: python3 -m py_compile <file>
   9 | 6. Test the changes work
  10 | 7. Git add + commit + push
```

### File: .claude/commands/brief.md (6 lines)
```
   1 | Refresh the Protocol Pulse morning intelligence brief:
   2 | 1. Check Ollama: `pgrep -f "ollama serve"` — start if not running
   3 | 2. Wait for Ollama: `sleep 10` if just started
   4 | 3. Run: `cd ~/protocol_pulse && python3 services/morning_brief.py`
   5 | 4. Report: age, sentiment, top narratives, BTC price used
   6 | 5. If failed, check logs/morning_brief_cron.log for error
```

### File: .claude/commands/check.md (9 lines)
```
   1 | Audit and verify a specific file or module.
   2 | 
   3 | Target: $ARGUMENTS
   4 | - Read the file thoroughly
   5 | - Check for: syntax errors, logic bugs, missing imports, dead code
   6 | - Verify all functions are called (not orphaned)
   7 | - Check integration with other modules (imports work both ways)
   8 | - Run: `python3 -m py_compile $ARGUMENTS`
   9 | - Report: issues found, grade A-F, fixes needed
```

### File: .claude/commands/commit.md (14 lines)
```
   1 | Commit changes with Protocol Pulse standards.
   2 | 
   3 | Commit message: $ARGUMENTS
   4 | 
   5 | Steps:
   6 | 1. Show all changed files: `git diff --name-only`
   7 | 2. Syntax check every modified .py file: `python3 -m py_compile <file>`
   8 | 3. If any syntax errors, FIX THEM before committing
   9 | 4. `git add -A`
  10 | 5. Check if pipeline files changed — if yes, prefix with [HOTFIX-EXEMPT] unless audit exists
  11 | 6. `git commit -m "$ARGUMENTS"`
  12 | 7. `git push`
  13 | 8. Verify push succeeded
  14 | 9. Report: files committed, push status
```

### File: .claude/commands/deploy.md (11 lines)
```
   1 | Verify full Protocol Pulse deployment health. Check ALL of these:
   2 | 1. Waitress alive: `pgrep -f "waitress.*5000"` 
   3 | 2. Website responds: `curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/health`
   4 | 3. RAM usage: `free -h` (warn if >70GB used)
   5 | 4. Top RAM consumers: `ps aux --sort=-%mem | head -5` (flag any >5GB)
   6 | 5. Cloudflare tunnel: `curl -s -o /dev/null -w '%{http_code}' https://protocolpulse.io/health`
   7 | 6. Ollama running: `pgrep -f "ollama serve"`
   8 | 7. Last tweet: check logs/tweet_machine_cron.log for most recent post
   9 | 8. Brief freshness: check age of data/intelligence/morning_intelligence_brief.json
  10 | 9. Git status: `git status --porcelain | wc -l` uncommitted files
  11 | Report each check as PASS/FAIL with details.
```

### File: .claude/commands/diagnose.md (13 lines)
```
   1 | Diagnose why something is broken or not working.
   2 | 
   3 | Problem: $ARGUMENTS
   4 | 
   5 | Protocol:
   6 | 1. Search logs for errors: grep -ri "error\|fail\|traceback" in relevant log files
   7 | 2. Check if the relevant service/process is running
   8 | 3. Check cron schedule — did it fire?
   9 | 4. Check dependencies (Ollama, waitress, API keys)
  10 | 5. Trace the data path from source to output
  11 | 6. Identify root cause (not symptoms)
  12 | 7. Propose fix with exact code change
  13 | Do NOT fix yet — just diagnose and report findings.
```

### File: .claude/commands/fix.md (11 lines)
```
   1 | Fix this issue: $ARGUMENTS
   2 | 
   3 | Follow the Protocol Pulse fix protocol:
   4 | 1. AUDIT-FIRST: Read all relevant files before touching anything
   5 | 2. Identify root cause (not symptoms)
   6 | 3. Implement the minimal fix that solves the problem
   7 | 4. Syntax check: `python3 -m py_compile <file>` for every changed file
   8 | 5. Test the fix works (don't just claim it works)
   9 | 6. Git add + commit + push with descriptive message
  10 | 7. Verify deployment: check waitress still healthy after changes
  11 | 8. Report what was changed, why, and proof it works
```

### File: .claude/commands/logs.md (10 lines)
```
   1 | View Protocol Pulse unified logs.
   2 | 
   3 | Mode: $ARGUMENTS
   4 | - If blank or "summary": show last line from each log with age
   5 | - If "follow" or "-f": tail -f all logs simultaneously
   6 | - If a specific service name: show last 20 lines of that log
   7 | 
   8 | ```bash
   9 | ~/protocol_pulse/scripts/unified_log.sh $ARGUMENTS
  10 | ```
```

### File: .claude/commands/monitor.md (7 lines)
```
   1 | Check Protocol Pulse uptime monitoring status.
   2 | 
   3 | Steps:
   4 | 1. Run: python3 ~/protocol_pulse/scripts/setup_uptime_monitor.py --status
   5 | 2. Also check: curl -s http://localhost:5000/health
   6 | 3. Report combined status — which monitors are UP/DOWN, local health endpoint response, and any anomalies.
   7 | 
```

### File: .claude/commands/pipeline-check.md (11 lines)
```
   1 | Verify the video pipeline is ready to render:
   2 | 1. GPU available: `nvidia-smi --query-gpu=memory.free --format=csv,noheader`
   3 | 2. Disk space: `df -h /home/ultron`
   4 | 3. No other renders running: `pgrep -fa daily_producer`
   5 | 4. yt-dlp working: `yt-dlp --version`
   6 | 5. Deno installed: `deno --version`
   7 | 6. ElevenLabs key valid: check .env has ELEVENLABS_API_KEY
   8 | 7. Claude API key valid: check .env has ANTHROPIC_API_KEY
   9 | 8. Assembler imports clean: `cd ~/protocol_pulse/video_pipeline_v3 && python3 -c "from assembler import assemble_episode; print('OK')"`
  10 | 9. All pipeline modules compile: py_compile each render_*.py
  11 | Report each check.
```

### File: .claude/commands/post.md (21 lines)
```
   1 | Post a specific tweet to X/Protocol Pulse account.
   2 | 
   3 | Tweet text: $ARGUMENTS
   4 | 
   5 | Steps:
   6 | 1. Verify tweet is <280 chars
   7 | 2. Check X gate: is posting allowed right now?
   8 | 3. Post via tweepy using credentials from .env
   9 | 4. Report: tweet ID, URL, or gate rejection reason
  10 | ```bash
  11 | cd ~/protocol_pulse && python3 -c "
  12 | from services.x_service import post_tweet, x_gate_check
  13 | text = '$ARGUMENTS'
  14 | allowed, reason = x_gate_check(text, source='manual', angle_category='manual')
  15 | if allowed:
  16 |     result = post_tweet(text)
  17 |     print(f'Posted: {result}')
  18 | else:
  19 |     print(f'Blocked: {reason}')
  20 | "
  21 | ```
```

### File: .claude/commands/processes.md (13 lines)
```
   1 | Show PM2 process status dashboard.
   2 | 
   3 | Steps:
   4 | 1. Run: pm2 list
   5 | 2. Run: pm2 jlist (JSON status of all processes)
   6 | 3. Report status, uptime, memory, and restart count for each managed process:
   7 |    - waitress (Flask web server, port 5000)
   8 |    - relay (Ultron relay, port 8201)
   9 |    - ollama (local LLM inference)
  10 |    - social-daemon (social media automation)
  11 | 4. Flag any process that is stopped, errored, or has restarted more than 3 times
  12 | 5. Note: the HeyGen video process is intentionally NOT managed by PM2 (DISABLED)
  13 | 
```

### File: .claude/commands/render.md (15 lines)
```
   1 | Fire a Protocol Pulse video render.
   2 | 
   3 | Mode: $ARGUMENTS
   4 | - If blank or "test": `python3 daily_producer.py --test --no-resume`
   5 | - If "fast": `python3 daily_producer.py --fast-test --no-resume`
   6 | - If "full": `python3 daily_producer.py --no-resume` (production render)
   7 | - If "reuse": `python3 daily_producer.py --test --reuse-content` (re-render with cached content)
   8 | 
   9 | ```bash
  10 | export PATH=$HOME/.deno/bin:$PATH
  11 | cd ~/protocol_pulse/video_pipeline_v3
  12 | python3 daily_producer.py $ARGUMENTS 2>&1 | tee /tmp/latest_render.log
  13 | ```
  14 | Monitor output. If it fails, diagnose root cause, fix it, and re-run.
  15 | After success, copy output to static/renders/ and report duration + file size.
```

### File: .claude/commands/scrape.md (11 lines)
```
   1 | Trigger a specific social scraper.
   2 | 
   3 | Source: $ARGUMENTS
   4 | - "x" or "twitter" or "nitter": `python3 services/nitter_scraper.py`
   5 | - "nostr": `python3 cron/nostr_cron.py`
   6 | - "spaces": `python3 x_spaces_scraper/run_scraper.py`
   7 | - "media" or "rss": `python3 scripts/sync_media_feeds.py`
   8 | - "all": run all scrapers sequentially
   9 | - If blank: show status of all scrapers (last run time, data freshness)
  10 | 
  11 | After scraping, report: items collected, data freshness, any errors.
```

### File: .claude/commands/site-check.md (17 lines)
```
   1 | Run a comprehensive site health check on protocolpulse.io.
   2 | 
   3 | Check ALL of these endpoints and report results:
   4 | ```bash
   5 | for ep in /health /api/btc-price /api/pro-metrics /api/kol/sentiment /api/kol/themes /api/media/stats /api/intelligence/sovereign-context; do
   6 |     code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000$ep)
   7 |     echo "$ep → $code"
   8 | done
   9 | ```
  10 | 
  11 | Also check:
  12 | - BTC price value (should be >0): `curl -s http://localhost:5000/api/btc-price | python3 -c "import sys,json; print(json.load(sys.stdin))"`
  13 | - Morning brief age
  14 | - Last article generated
  15 | - Site health log: `tail -10 ~/protocol_pulse/logs/site_health.log`
  16 | 
  17 | If any endpoint returns non-200, diagnose and fix immediately.
```

### File: .claude/commands/status.md (22 lines)
```
   1 | Full Protocol Pulse system status dashboard:
   2 | 
   3 | **Infrastructure:**
   4 | - Waitress (port 5000): alive/dead + uptime
   5 | - RAM: used/total + top 3 consumers
   6 | - GPU: nvidia-smi summary
   7 | - Disk: df -h /home
   8 | 
   9 | **Content Pipeline:**
  10 | - Last render: when + success/fail + duration
  11 | - Last tweet: when + text + posted/blocked
  12 | - Morning brief: age + sentiment
  13 | - Transcript intel: last run + creator count
  14 | - KOL sentiment: avg score + creator count
  15 | 
  16 | **Cron Health:**
  17 | - Tweet machine: last fire time
  18 | - Brief generation: last fire time  
  19 | - Convergence engine: last fire time
  20 | - Media sync: last fire time
  21 | 
  22 | Format as a clean, readable dashboard.
```

### File: .claude/commands/tweet.md (12 lines)
```
   1 | Generate and post a Protocol Pulse tweet.
   2 | 
   3 | Topic/angle: $ARGUMENTS
   4 | - If blank: use default tweet machine (random format from brief)
   5 | - If specified: pass as context to tweet machine for targeted content
   6 | 
   7 | Steps:
   8 | 1. Check brief freshness: if >12h old, refresh first
   9 | 2. Fire tweet machine: `cd ~/protocol_pulse && python3 services/tweet_machine.py`
  10 | 3. If $ARGUMENTS specified, generate a targeted tweet about that topic
  11 | 4. Check if posted or blocked — show gate decision
  12 | 5. If blocked, explain which gate and fix
```

### File: .claude/settings.json (46 lines)
```
   1 | {
   2 |   "hooks": {
   3 |     "SessionStart": [
   4 |       {
   5 |         "hooks": [
   6 |           {
   7 |             "type": "command",
   8 |             "command": "/home/ultron/protocol_pulse/scripts/hooks/session_start.sh"
   9 |           }
  10 |         ]
  11 |       }
  12 |     ],
  13 |     "PreToolUse": [
  14 |       {
  15 |         "matcher": "Bash",
  16 |         "hooks": [
  17 |           {
  18 |             "type": "command",
  19 |             "command": "/home/ultron/protocol_pulse/scripts/hooks/pre_bash_gate.sh"
  20 |           }
  21 |         ]
  22 |       }
  23 |     ],
  24 |     "PostToolUse": [
  25 |       {
  26 |         "matcher": "Write|Edit|MultiEdit",
  27 |         "hooks": [
  28 |           {
  29 |             "type": "command",
  30 |             "command": "/home/ultron/protocol_pulse/scripts/hooks/post_edit_syntax.sh"
  31 |           }
  32 |         ]
  33 |       }
  34 |     ],
  35 |     "Stop": [
  36 |       {
  37 |         "hooks": [
  38 |           {
  39 |             "type": "command",
  40 |             "command": "/home/ultron/protocol_pulse/scripts/hooks/stop_audit.sh"
  41 |           }
  42 |         ]
  43 |       }
  44 |     ]
  45 |   }
  46 | }
```

---

## YOUR REVIEW TASK

Perform a forensic code review. Be brutally honest. Cite line numbers.
There is no developer present. No ego to protect. Only quality matters.

### SECTION 1: CORRECTNESS
Walk through the main user flow step by step. Does the code do what it claims?
- Logic errors, wrong variable names, silent failures
- Race conditions (concurrent requests hitting same state)
- N+1 query problems (DB queries inside loops)
- Edge cases that will break in production (empty DB, API timeout, bad input)

### SECTION 2: LAW COMPLIANCE
For each LAW in the governing spec above, state: COMPLIANT / VIOLATION / PARTIAL
Cite specific line numbers for any violation or partial compliance.

### SECTION 3: SECURITY
- SQL injection (check raw queries and ORM filter() with user input)
- Authentication bypasses (routes that should require login but don't)
- Rate limiting gaps (can one user exhaust paid API limits?)
- Secrets in code (API keys, tokens, passwords hardcoded anywhere?)
- Unvalidated user input reaching DB, filesystem, or shell

### SECTION 4: FRONTEND QUALITY
- Does the UI match the spec layout exactly?
- Hardcoded values that should be dynamic (prices, counts, dates)
- Mobile viewport breakage
- JS errors that prevent page functioning
- Loading / error / empty state for every async operation — are all 3 handled?
- Does it look world-class? Or does it look like a rushed prototype?

### SECTION 5: BACKEND QUALITY
- DB operations: try/except with rollback on every write?
- External API calls: timeout + retry + graceful degradation on every call?
- Cron job: does it handle failure without crashing the service?
- Memory leaks: large objects created per-request without cleanup?
- Logging: are errors logged with enough context to debug production issues?

### SECTION 6: WORLD-CLASS GAP ANALYSIS
This is Protocol Pulse — a premium Bitcoin intelligence product.
What would Bloomberg Terminal, Coinbase Advanced, or Blockworks do differently?
What is genuinely missing that would make this impressive to a professional?
DO NOT pad this section. Only include changes with material impact.
If an area is already excellent, explicitly say so — that's equally important.

### SECTION 7: SCORES (0-100 each)
- Backend logic:    X/100
- Frontend/UI:      X/100
- Error handling:   X/100
- Security:         X/100
- Performance:      X/100
- Law compliance:   X/100
- World-class gap:  X/100 (100 = nothing missing, 0 = prototype quality)
- OVERALL:          X/100

### SECTION 8: PRIORITY ACTION PLAN
Every fix and improvement, sorted by impact. Be specific — cite file and line.
Format exactly as:
P0 CRITICAL | [what] | [file:line] | [why it will break production]
P1 HIGH     | [what] | [file:line] | [why it degrades quality]
P2 MEDIUM   | [what] | [file:line] | [enhancement that matters]
P3 LOW      | [what] | [file:line] | [polish]

### SECTION 9: THE ONE THING
If you could only tell the developer one thing to make this dramatically better,
what would it be? One sentence. Make it count.

### SECTION 10: FINAL VERDICT
In 2-3 sentences: is this code ready for production? What must change first?

