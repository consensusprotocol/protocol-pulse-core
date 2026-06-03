# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: video-audio-fix
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
**SECTION 1: CORRECTNESS**

The files are Claude Code slash-command and agent definitions. They correctly define a set of operational commands that map to shell invocations. However, several have correctness issues:

- `post.md:14` and `tweet.md:9-11`: `$ARGUMENTS` is directly interpolated into a Python `-c` string without escaping. A tweet containing single quotes or backticks will break the command or cause syntax errors.
- `render.md:12`: `$ARGUMENTS` is passed raw to `daily_producer.py`. No validation of allowed modes.
- `diagnose.md` and `fix.md` both claim to follow "AUDIT-FIRST" but the command definitions themselves do not enforce reading files first — they rely on the model obeying the text.
- Multiple commands assume `~/protocol_pulse` exists and that the user is `ultron`; no fallback or validation.

No race conditions or N+1 issues exist because these are not application code.

**SECTION 2: LAW COMPLIANCE**

- Always run auto-forensic after render → **PARTIAL** (`render.md` does not invoke ffprobe/blackdetect/silencedetect/ebur128).
- Never skip regression_test.sh → **VIOLATION** (no command references `regression_test.sh`).
- AV sync diagnosis first → **VIOLATION** (no command enforces checking raw clips before assembler).
- Audio target (-14 LUFS, -1 dBTP) → **NOT ADDRESSED** (none of the files reference audio normalization).

Most laws are simply outside the scope of these agent/command files.

**SECTION 3: SECURITY**

**Critical issues present:**

- Multiple commands (`post.md:11-20`, `tweet.md:9`, `fix.md`, `commit.md`) perform direct shell interpolation of `$ARGUMENTS` into `python3 -c "..."` or bash. This is a command injection vector.
- `settings.json` registers hooks that run arbitrary scripts on `Write|Edit|MultiEdit`. If an attacker can trigger edits, they can execute code.
- No sanitization or allow-listing of `$ARGUMENTS` anywhere.
- Secrets: no hardcoded keys in these files (good), but the commands assume `.env` exists without verification.

**SECTION 4: FRONTEND QUALITY**

No frontend code provided. N/A.

**SECTION 5: BACKEND QUALITY**

These files are not backend code. The command definitions are fragile because they lack:

- Error handling around external calls (`pgrep`, `curl`, `python3 -c`).
- Consistent use of `set -e` or explicit failure checking.
- Logging of command execution results.

**SECTION 6: WORLD-CLASS GAP ANALYSIS**

These files are operational tooling for an AI agent, not the product itself. The gap that matters is that the commands encourage the model to run raw shell with user input rather than using a proper CLI interface or Python entrypoints. This is the opposite of what a professional system would do (Bloomberg-style tooling uses structured, validated command interfaces).

**SECTION 7: SCORES**

- Backend logic: 55/100
- Frontend/UI: N/A
- Error handling: 40/100
- Security: 25/100
- Performance: 70/100
- Law compliance: 30/100
- World-class gap: 35/100
- **OVERALL: 42/100**

**SECTION 8: PRIORITY ACTION PLAN**

P0 CRITICAL | Command injection via `$ARGUMENTS` interpolation | `post.md:11`, `tweet.md:9`, `render.md:12` | Allows arbitrary command execution
P0 CRITICAL | No enforcement of pipeline laws (ffprobe, regression_test.sh) | `render.md` | Direct violation of governing laws
P1 HIGH | All commands lack input validation/escaping | Multiple files | Breaks on normal user input containing quotes
P2 MEDIUM | No verification that required tools/paths exist before execution | `deploy.md`, `pipeline-check.md` | Silent failures in production
P3 LOW | Repetitive boilerplate across command files | All `.md` command files | Maintenance burden

**SECTION 9: THE ONE THING**

Stop interpolating `$ARGUMENTS` directly into shell and Python `-c` strings — use a proper argument parser or at minimum `shlex.quote`.

**SECTION 10: FINAL VERDICT**

Not ready for production use as written. The command injection risk and complete absence of the required video pipeline forensic steps (ffprobe, regression tests, LUFS checks) are blocking issues. These files should be rewritten to call validated Python entrypoints instead of raw shell interpolation.

## GEMINI — CYCLE 1 OUTPUT
Here is a forensic code review of the `video-audio-fix` feature branch.

### OVERVIEW
The provided files do not contain the `video-audio-fix` feature itself. Instead, they define a comprehensive operational framework for an AI agent (named Claude) to manage, monitor, and deploy the "Protocol Pulse" application. The review will therefore focus on the correctness, security, and quality of this agent's command and control system.

The core architecture uses Markdown files to define commands, which are then executed as shell scripts. This approach is novel but introduces significant security and fragility risks if not implemented with extreme care. This review has identified critical vulnerabilities and compliance failures in the current implementation.

---

### SECTION 1: CORRECTNESS

The logic of the individual commands is generally straightforward, but several areas exhibit fragility or potential for silent failure.

*   **`brief.md`, Line 3:** The `sleep 10` is a fragile way to wait for a service to start. If Ollama takes longer than 10 seconds to initialize, the subsequent script will fail. A more robust approach would be a loop that polls a health endpoint on the Ollama service before proceeding.
*   **`post.md`, Lines 11-20:** The method of passing `$ARGUMENTS` into the Python script is extremely dangerous and incorrect. The `text = '$ARGUMENTS'` line (13) directly embeds the argument string. If the tweet text contains a single quote (`'`), it will break the Python syntax, causing the entire command to fail. If it contains a quote and other special characters, it could lead to arbitrary code execution (see Security section).
*   **`commit.md`, Line 10:** The logic `prefix with [HOTFIX-EXEMPT] unless audit exists` is confusingly worded. It's unclear what it's trying to enforce. A clearer rule would be "Prefix pipeline changes with `[PIPELINE]` and require an audit. Hotfixes can be prefixed with `[HOTFIX]` to bypass this."
*   **`render.md`, Line 12:** Using `tee /tmp/latest_render.log` is acceptable for debugging but not for production. The `/tmp` directory can be cleared on system reboots, and its permissions are often world-writable, making it insecure. Logs should be sent to a persistent, permission-controlled directory (e.g., `~/protocol_pulse/logs/`).
*   **`site-check.md`, Line 12:** Piping `curl` output to a Python one-liner to parse JSON is brittle. A standard tool like `jq` (`... | jq .price`) would be more robust and conventional for shell-based JSON parsing.

---

### SECTION 2: LAW COMPLIANCE

The defined commands and processes show significant non-compliance with the governing PIPELINE_LAWS.

*   **LAW: Always run auto-forensic after render: ffprobe, blackdetect, silencedetect, ebur128**
    *   **VIOLATION.** The `render.md` command (lines 9-13) defines the entire render process. It concludes after the `daily_producer.py` script finishes. There are no subsequent steps defined to run `ffprobe`, `blackdetect`, `silencedetect`, or `ebur128` for forensic analysis. This is a direct violation of the law.

*   **LAW: Never skip regression_test.sh — zero FAILs before commit**
    *   **VIOLATION.** The `commit.md` command (lines 6-12) defines the pre-commit checks. It includes a syntax check (`py_compile`) but makes no mention of running `regression_test.sh`. This completely omits a required quality gate.

*   **LAW: AV sync diagnosis first: check raw clips before touching assembler**
    *   **PARTIAL / VIOLATION.** This is a procedural law. While no command explicitly violates it, the `diagnose.md` and `fix.md` command definitions, which would be used for such issues, do not codify this critical first step. They are too generic. An effective agent needs this rule embedded in its diagnostic protocol for A/V issues.

*   **LAW: Audio target: -14 LUFS integrated, -1 dBTP ceiling, music at -14 LUFS with sidechain**
    *   **VIOLATION.** Similar to the first law, the `render.md` command lacks any steps that would enforce these audio targets. The render script `daily_producer.py` is treated as a black box. The command definition should include post-processing steps (e.g., using `ffmpeg-normalize` or a custom FFmpeg filter chain) to ensure compliance, or at least a verification step that checks the output against these targets.

---

### SECTION 3: SECURITY

The current implementation has a CRITICAL security vulnerability.

*   **Shell Injection via Argument Passing:** The pattern of taking `$ARGUMENTS` and embedding it directly into a shell command string is present in multiple files, but is most dangerously exploited in `post.md`.
    *   **File: `.claude/commands/post.md`, Line 13:** The line `text = '$ARGUMENTS'` is inside a `python -c "..."` block. An attacker could provide an argument like: `malicious tweet' ; import os; os.system('rm -rf ~') #`. This would break out of the string literal and execute arbitrary Python code, and subsequently arbitrary shell commands, on the server with the user's p

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — VIDEO-AUDIO-FIX — CYCLE 1
Generated: 2026-05-30 04:45
Models: grok, gemini (+1 failed — GPT-4o quota exhausted)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Backend Logic | ~50/100 | N/A | 55/100 | **52/100** |
| Frontend/UI | N/A | N/A | N/A | **N/A** |
| Error Handling | ~35/100 | N/A | 40/100 | **37/100** |
| Security | ~20/100 | N/A | 25/100 | **22/100** |
| Performance | ~65/100 | N/A | 70/100 | **67/100** |
| Law Compliance | ~25/100 | N/A | 30/100 | **27/100** |
| World-Class Gap | ~30/100 | N/A | 35/100 | **32/100** |
| **OVERALL** | **~37/100** | **N/A** | **42/100** | **39/100** |

> ⚠️ **Confidence Note:** Only 2 of 3 models produced output. GPT-4o failed due to quota exhaustion. Scores carry reduced statistical confidence. Treat consensus figures as directional, not definitive. A Cycle 2 re-score with all 3 models is strongly recommended.

---

## UNANIMOUS FINDINGS
*(Both models agree — implement unconditionally)*

---

### U1 — Shell/Command Injection via `$ARGUMENTS` Interpolation
**What it is:** `$ARGUMENTS` is embedded directly into `python3 -c "..."` strings and bare shell commands. A user-controlled input containing a single quote, semicolon, or backtick can break the string boundary and execute arbitrary code.

**Files/Lines:**
- `post.md` line 13: `text = '$ARGUMENTS'` inside a `python -c` block
- `tweet.md` lines 9–11: same pattern
- `render.md` line 12: raw `$ARGUMENTS` passed to `daily_producer.py`

**What to change:** Never interpolate `$ARGUMENTS` into a shell string. Instead:
1. Write a named Python entrypoint (e.g., `scripts/post_content.py`) that accepts `sys.argv` arguments properly.
2. Call it as `python3 scripts/post_content.py "$ARGUMENTS"` (quoted, not embedded).
3. Inside the script, use `argparse` or `shlex` to parse input.
4. Apply `shlex.quote()` at any boundary where strings re-enter shell context.

---

### U2 — `render.md` Does Not Run Post-Render Forensics (ffprobe / blackdetect / silencedetect / ebur128)
**What it is:** The render command terminates after `daily_producer.py` completes. No forensic analysis runs automatically afterward. This directly violates the governing PIPELINE_LAWS.

**File/Line:** `render.md` lines 9–14

**What to change:** Append a mandatory post-render forensic block:
```bash
ffprobe -v error -show_streams output.mp4
ffmpeg -i output.mp4 -vf blackdetect=d=0.1:pix_th=0.10 -f null -
ffmpeg -i output.mp4 -af silencedetect=n=-50dB:d=0.5 -f null -
ffmpeg -i output.mp4 -af ebur128=peak=true -f null -
```
All four tools must run and their output must be logged to `~/protocol_pulse/logs/render_forensics_$(date +%Y%m%d_%H%M%S).log`.

---

### U3 — `commit.md` Never References `regression_test.sh`
**What it is:** The commit command defines pre-commit quality gates but omits `regression_test.sh` entirely. This violates the "never skip regression_test.sh — zero FAILs before commit" law.

**File/Line:** `commit.md` lines 6–12


---

## ORIGINAL CODE (same code as Cycle 1)
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



---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
