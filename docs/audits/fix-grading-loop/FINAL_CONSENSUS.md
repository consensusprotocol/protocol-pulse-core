# CONSENSUS REPORT — FIX-GRADING-LOOP — CYCLE 2
Generated: 2026-03-22 06:47
Models: gpt4o, grok (+1 failed — Gemini 2.5 Pro: 403 PERMISSION_DENIED / leaked API key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | ❌ failed | 4/10 | 4/10 | **4/10** |
| Law Compliance | ❌ failed | 7/10 | 6/10 | **6.5/10** |
| Security | ❌ failed | 3/10 | 3/10 | **3/10** |
| Frontend Quality | ❌ failed | N/A | N/A | **N/A** |
| Overall | ❌ failed | 4/10 | 4/10 | **4/10** |

> **Note:** Gemini failed due to a leaked API key (403 PERMISSION_DENIED). Scoring is derived from GPT-4o and Grok only. The strong agreement between the two functioning models (identical Overall: 4/10, identical Security: 3/10) increases confidence in the consensus scores despite the missing third signal.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — `shell=True` + Unescaped File Path Interpolation → Command Injection
**Both models: GPT-4o, Grok — Severity: CRITICAL**

The shared `run()` helper invokes every subprocess with `shell=True`. Multiple callers interpolate external data (video file paths, output filenames) directly into shell command strings without escaping or quoting.

- `overnight_render_loop.py:67-70` — `run()` definition; `shell=True` is unconditional
- `overnight_render_loop.py:271, 289, 293, 299` — `run_forensics()` interpolates `video` directly
- `overnight_render_loop.py:391-400` — `fire_cc_fix()` interpolates session names and paths
- `video_pipeline_v3/gemini_grade.py:31-33, 57, 90, 101, 110, 125, 136-137` — ffmpeg/ffprobe calls throughout

**Fix:** Refactor `run()` to accept a list and default `shell=False`. Replace all f-string command constructions with argument lists. Where shell features like `2>&1` are genuinely needed, use `subprocess.STDOUT` for stderr redirection instead.

```python
# Before
run(f'ffprobe -v error -i {video} ...')

# After
subprocess.run(['ffprobe', '-v', 'error', '-i', str(video), ...],
               capture_output=True, shell=False)
```

---

### U2 — No tmux/claude CLI Validation; Timed-Out Sessions Not Killed
**Both models: GPT-4o, Grok — Severity: HIGH**

`startup_checks()` validates ffmpeg, pipeline dir, output dir, and TTS — but not `tmux` or `claude`. If either is absent, `fire_cc_fix()` fails silently. Worse, when the `fire_cc_fix()` deadline elapses (`overnight_render_loop.py:403`), the code simply logs and continues — the tmux session remains alive, consuming resources and potentially mutating the repo in the background while the next iteration is already running.

- `overnight_render_loop.py:88-149` — `startup_checks()` — missing binary validation
- `overnight_render_loop.py:392-403` — `fire_cc_fix()` — no session cleanup on timeout

**Fix (validation):**
```python
for tool in ['tmux', 'claude']:
    if not shutil.which(tool):
        log.error(f"FATAL: {tool} not found in PATH")
        sys.exit(1)
```

**Fix (session cleanup):**
```python
finally:
    result = subprocess.run(['tmux', 'has-session', '-t', session_name],
                            capture_output=True)
    if result.returncode == 0:
        subprocess.run(['tmux', 'kill-session', '-t', session_name])
        log.warning(f"Killed orphaned tmux session: {session_name}")
```

---

### U3 — Silent Failure on Render: Stale/Missing Output File Not Caught
**Both models: GPT-4o, Grok — Severity: HIGH**

`run_render()` can return a non-zero exit code or produce no output file. In both cases, the code logs and continues, potentially grading a **pre-existing file from an earlier run today** rather than the current attempt's output.

- `overnight_render_loop.py:251, 420-421` — no mtime guard, no hard failure on missing output
- `overnight_render_loop.py:253-255` — today-only filter exists but does not enforce "produced by this attempt"

**Fix:** Record `render_start = time.time()` before calling `run_render()`. After the call, reject any output file whose `os.path.getmtime(f) < render_start`. Emit a Telegram alert and skip the iteration (rather than silently continuing) if no fresh file is found.

---

### U4 — Gemini API Lacks Retry/Backoff; Error Handling Insufficient
**Both models: GPT-4o (partial), Grok — Severity: HIGH**

The `grade_with_gemini()` / `gemini_call()` path has no retry loop, no backoff, and does not distinguish transient failures (network timeout, rate limit) from permanent ones (invalid key, malformed request). The subprocess fallback to `gemini_grade.py` exists but is itself not hardened.

- `overnight_render_loop.py:231-242` — bare API call, no retry
- `overnight_render_loop.py:337-371` — parsing errors not retried

**Fix:** Wrap the API call in a retry loop (3 attempts, exponential backoff: 5s, 15s, 45s). Catch `HTTPError`, `URLError`, `KeyError`, `JSONDecodeError` individually. Log structured failure reason per attempt. On permanent failure, emit alert before falling back.

---

## MAJORITY FINDINGS (2 of 2 models agree)

> With only 2 functioning models, all agreed-upon findings qualify as unanimous. The following were explicitly raised by both but are slightly lower severity, or one model's framing adds nuance:

### M1 — Hardcoded Home-Relative TTS Path
**GPT-4o primary, Grok confirms — Severity: HIGH**

Both `startup_checks()` and `check_tts_ready()` use hardcoded `~/protocol_pulse/video_pipeline_v3/tts_local.py` instead of deriving the path from the `PIPELINE` constant. On any non-home-directory deployment, startup succeeds but runtime TTS checks fail against a different (correct) path.

- `overnight_render_loop.py:131` — startup check
- `overnight_render_loop.py:216` — runtime check

**Fix:**
```python
TTS_SCRIPT = os.path.join(PIPELINE, 'tts_local.py')
# Replace all ~/protocol_pulse/... references with TTS_SCRIPT
```

---

### M2 — Daemon Scheduling Contract Mismatch
**GPT-4o primary, Grok confirms — Severity: MEDIUM**

When started outside of 08:00 ET, the daemon runs a cycle immediately, then sleeps until next 08:00 ET. The docstring and operational documentation state it "runs at 08:00 ET daily." These are different contracts. An operator starting the daemon at 14:00 ET expecting no immediate run will be surprised.

- `overnight_render_loop.py:600-604` — daemon loop body
- `overnight_render_loop.py:9, 528-537` — docstring and sleep function

**Fix:** Either (a) sleep until next 08:00 ET before the first cycle if current time is not within a tolerance window of 08:00, or (b) update all documentation to say "runs immediately on start, then daily at 08:00 ET."

---

### M3 — Temp WAV Leak in TTS Artifact Check
**GPT-4o primary, Grok confirms — Severity: MEDIUM**

The TTS check writes a temporary WAV file. If an exception occurs before `os.unlink()`, the file persists indefinitely. In a long-running daemon this accumulates quietly.

- `overnight_render_loop.py:307-325`

**Fix:**
```python
tmp_path = Path(tempfile.mktemp(suffix='.wav'))
try:
    # ... TTS check logic ...
finally:
    if tmp_path.exists():
        tmp_path.unlink(missing_ok=True)
```

---

### M4 — Brittle Fallback Grade Parser
**GPT-4o primary, Grok confirms — Severity: MEDIUM**

The fallback `gemini_grade.py` subprocess output is parsed by naive `split("|")`. If any field contains a pipe character (plausible in a verdict string), the parser silently misreads or raises an IndexError.

- `overnight_render_loop.py:441-450`

**Fix:**
```python
# Use maxsplit=3 to limit splitting to exactly 4 fields
parts = line.split("|", 3)
if len(parts) != 4:
    log.error(f"Unexpected grade format: {line!r}")
    continue
```

---

## UNIQUE INSIGHTS (only 1 model caught — evaluated carefully)

### UI-1 — `gemini_grade.py` Executes at Import Time (GPT-4o only)
**Assessment: IMPLEMENT**

`gemini_grade.py` contains substantive logic (env load, ffmpeg scan, Gemini API calls, file writes, `sys.exit()`) at module top level rather than inside a `main()` guard. If any future test, importer, or tool imports this module, it will trigger the entire grading pipeline and exit the process. This is a maintainability time bomb.

- `video_pipeline_v3/gemini_grade.py:35-468`

**Fix:** Wrap everything below imports/constants in `if __name__ == '__main__': main()`.

---

### UI-2 — `gemini_grade.py` Opens `.env` with No Exception Handling (GPT-4o only)
**Assessment: IMPLEMENT**

`for line in open('/home/ultron/protocol_pulse/.env'):` — hardcoded absolute path, no try/except. Missing or unreadable `.env` crashes before any controlled logging or alerting.

- `video_pipeline_v3/gemini_grade.py:11`

**Fix:**
```python
try:
    with open(ENV_PATH) as f:
        for line in f:
            ...
except FileNotFoundError:
    print(f"FATAL: .env not found at {ENV_PATH}", file=sys.stderr)
    sys.exit(1)
```

---

### UI-3 — `send_telegram_alert()` Uses HTML Parse Mode with Unescaped Content (GPT-4o only)
**Assessment: IMPLEMENT**

Messages passed to Telegram with `parse_mode="HTML"` may include verdict strings, log lines, or file paths containing `<`, `>`, `&`. These will corrupt rendering or cause API rejection (400 error), silently dropping the alert.

- `overnight_render_loop.py:205`

**Fix:** Either escape all dynamic content with `html.escape()` before insertion, or switch to `parse_mode=None` (plain text) for all alert messages that include dynamic fields.

---

### UI-4 — PID File Not Cleaned Up on Abnormal Termination (Grok only)
**Assessment: IMPLEMENT**

The PID file lock prevents duplicate instances, but if the process is killed (SIGKILL) or crashes, the stale PID file blocks all future runs until manual deletion.

- `overnight_render_loop.py:543-556`

**Fix:** Register a `signal.signal(signal.SIGTERM, ...)` handler and `atexit.register(...)` to remove the PID file. Also check at startup whether the PID in the file is actually running (`os.kill(pid, 0)`) before refusing to start.

---

### UI-5 — Repeated `load_env()` Calls Throughout Runtime (Grok only)
**Assessment: INVESTIGATE FURTHER**

`load_env()` is called from multiple functions on each invocation rather than once at startup. This is a correctness concern if env values change mid-run, and a minor performance concern. However, if the design intent is to allow hot-reload of credentials (e.g., rotating API keys without restart), repeated loads are intentional. Clarify intent before changing; if no hot-reload is needed, load once at startup and cache.

- `overnight_render_loop.py:52-64, 133, 198`

---

### UI-6 — Non-Atomic Heartbeat Writes (GPT-4o, Grok both — elevated)
**Assessment: IMPLEMENT**

Both models noted this independently, so it qualifies as a majority finding even though it wasn't in the primary unanimous list. Mid-write crashes produce truncated JSON. The code tolerates `JSONDecodeError` on load, so it's survivable — but atomic write-via-temp-and-replace is the correct pattern for any daemon state file.

- `overnight_render_loop.py:179-181`

**Fix:**
```python
tmp = Path(str(HEARTBEAT_FILE) + '.tmp')
tmp.write_text(json.dumps(heartbeat_data, indent=2))
tmp.replace(HEARTBEAT_FILE)
```

---

### UI-7 — `GEMINI_API_KEY` Not Validated in Startup Checks (Grok only)
**Assessment: IMPLEMENT**

`startup_checks()` verifies ffmpeg and TTS but not whether `GEMINI_API_KEY` is set. A missing key causes predictable failure deep in the render loop — wasting compute, burning a cycle, and generating confusing logs — rather than a clean early abort.

- `overnight_render_loop.py:88-149, 233`

**Fix:** Add to `startup_checks()`:
```python
if not os.getenv('GEMINI_API_KEY'):
    log.error("FATAL: GEMINI_API_KEY not set")
    sys.exit(1)
```

---

### UI-8 — Logging Handlers Added Unconditionally at Import (GPT-4o only)
**Assessment: SKIP (low priority)**

Duplicate handlers in test environments are a hygiene issue, not a production bug. The standard fix is a `if not log.handlers:` guard, but this should wait until a test suite is introduced. Not a ship blocker.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Severity of Gemini Error Handling Gap

**GPT-4o** characterized U4 as "partially agree" — arguing the subprocess fallback to `gemini_grade.py` provides meaningful resilience and "lacks error handling" is too strong.

**Grok** treated it as a full P0/P1 failure with no mitigation credit.

**Tiebreaker: GPT-4o is more precise.** The fallback exists and does reduce the blast radius of a Gemini API failure. However, GPT-4o's own conclusion is correct: resilience is still *insufficient* because neither the primary nor fallback path has retry/backoff. The finding belongs at **P1 HIGH**, not P0 Critical, unless the system is expected to run fully unattended with no manual recovery option.

---

### C2 — DST / Clock Change Handling in Sleep Function

**Grok** flagged `sleep_until_next_8am_et()` as vulnerable to DST transitions and clock adjustments.

**GPT-4o** did not raise this concern.

**Tiebreaker: Investigate further before promoting to a required fix.** The function uses `pytz`/`zoneinfo` (standard DST-aware libraries in Python 3.9+). If it uses `datetime.now(tz=eastern)` correctly, DST is handled automatically by the timezone library. Grok's concern is valid if the implementation uses naive datetimes or hardcoded UTC offsets. Audit the actual implementation of `sleep_until_next_8am_et()` before committing to a fix. Place at **P2 MEDIUM** pending that review.

---

## VALIDATED STRENGTHS (do NOT change in second pass)

Both models confirmed these areas as working correctly:

1. **PID-based singleton lock** — `_acquire_singleton()` at `overnight_render_loop.py:543-555` correctly prevents duplicate instances on the same host. The mechanism is sound (subject to UI-4's cleanup fix, which is additive, not corrective).

2. **Today-only output file filter** — `overnight_render_loop.py:253-255` correctly restricts candidate files to those produced today, eliminating the old cross-day stale file bug. The mtime guard (U3) is an incremental improvement, not a correction of broken logic.

3. **Startup checks structure** — The `startup_checks()` function's overall architecture (validate before running, exit cleanly on failure) is correct and comprehensive for the checks it does include. Only its *coverage* is insufficient (missing tmux, claude, GEMINI_API_KEY).

4. **Multi-attempt render cycle** — `run_cycle()` at `overnight_render_loop.py:492-524` running up to 2 attempts with a 30-minute wait between them is a meaningful operational improvement over a crash-only loop. Do not change the retry structure.

5. **Grade A early exit** — The logic to lock a winner recipe and stop iterating upon achieving Grade A (`overnight_render_loop.py:468-476`) is correct and efficient.

6. **Heartbeat restore on restart** — Loading existing heartbeat counters from JSON on daemon startup (`overnight_render_loop.py:589-598`) is good operational practice for a long-running daemon.

---

## LAW COMPLIANCE CONSENSUS

**No governing legal framework was specified** in the audit scope (PIPELINE_LAWS.md was not provided to reviewers). The following determination is based on general software engineering standards and implied operational requirements:

| Area | Status | Finding |
|---|---|---|
| Subprocess safety | ❌ Non-compliant | `shell=True` with interpolated inputs violates secure coding standards (CWE-78) |
| Data integrity | ⚠️ At risk | Non-atomic state writes violate durability expectations for daemon state |
| Operational contract | ⚠️ At risk | Daemon scheduling mismatch violates documented behavioral contract |
| API credential handling | ⚠️ At risk | No validation of GEMINI_API_KEY before use; hardcoded `.env` path in `gemini_grade.py` |
| Resource cleanup | ❌ Non-compliant | Orphaned tmux sessions and temp WAV files violate resource management expectations |
| Availability | ⚠️ At risk | Silent failures in render/grade path without alerting violate implied SLA |

**Final determination:** The codebase is not compliant with production-grade operational standards. No specific regulations are violated (no PII, no financial data in scope), but internal engineering laws (if defined in PIPELINE_LAWS.md) should be reviewed against U1–U4 specifically.

---

## SECURITY CONSENSUS

Both models assigned **3/10** — the lowest score in this audit. The security posture is the single biggest blocker to production readiness.

**Priority order (highest to lowest risk):**

1. **Command injection via `shell=True` + unescaped paths** — CWE-78, exploitable if any external input reaches filename construction. Even "internal" filenames can be manipulated via directory names, symlinks, or upstream pipeline compromise. **Must fix before ship.**

2. **Orphaned Claude/tmux sessions with repo write access** — A timed-out Claude Code session continues executing with full filesystem access. If the session received a malformed prompt or is in an unexpected state, it can corrupt the repository silently. **Must fix before ship.**

3. **Hardcoded `.env` path with no permission check** — If `.env` is world-readable (common misconfiguration), API keys are exposed. Not introduced by this code, but the explicit open of a hardcoded path makes it worse.

4. **HTML injection in Telegram alerts** — Low exploitability in current deployment, but unescaped dynamic content in formatted messages is a hygiene failure.

---

## WORLD-CLASS GAP CONSENSUS

Items raised by both functioning models that separate "working code" from "production-grade infrastructure":

### WCG-1 — No Structured Alerting for Silent Failures
Both models flagged multiple "log and continue" patterns (render failure, grade failure, missing output). A world-class pipeline emits **structured alerts** (Telegram, PagerDuty, or equivalent) with actionable context — which file failed, which iteration, what the last known grade was — not just log entries that nobody reads in a cron job.

### WCG-2 — No Observability / Metrics
Neither model saw evidence of metrics emission (cycle duration, grade distribution over time, render success rate, API latency). A world-class overnight render daemon exports these to a time-series store or dashboard. Without them, debugging production degradation is forensic archaeology.

### WCG-3 — No Integration Test Coverage for the Grading Loop
The audit found no test suite for the core `run_single_render()` → `grade_with_gemini()` → `fire_cc_fix()` path. A world-class system has at least smoke-level integration tests that exercise the loop with a known-bad video, verify that grading produces output, and verify that the fix session is invoked. `regression_test.sh` (referenced in the audit) should cover this path.

### WCG-4 — External Process Dependencies Not Version-Pinned
Both models noted assumptions about `tmux`, `claude`, and `ffmpeg` being available and compatible. A world-class deployment pins these versions (in a Dockerfile, Nix flake, or requirements file) and validates versions at startup, not just presence.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Replace `shell=True` with `shell=False`; convert all f-string command constructions to argument lists | `overnight_render_loop.py:67-70, 271, 289, 293, 299, 391-400`; `gemini_grade.py:31-33, 57, 90, 101, 110, 125, 136-137` | both | CWE-78 command injection; top security finding with unanimous agreement |
| **P0 CRITICAL** | Kill tmux/Claude session on timeout expiry; add `tmux` and `claude` to `startup_checks()` | `overnight_render_loop.py:88-149, 392-403` | both | Orphaned sessions with repo write access; silent startup failures |
| **P0 CRITICAL** | Record render start time; reject output files with `mtime < render_start`; alert on no fresh output | `overnight_render_loop.py:245-265, 420-421` | both | Silent grading of stale files; operational correctness failure |
| **P1 HIGH** | Fix hardcoded TTS path to use `os.path.join(PIPELINE, 'tts_local.py')` | `overnight_render_loop.py:131, 216` | both | Deployment correctness bug; non-home-directory deploys silently misconfigure |
| **P1 HIGH** | Add retry loop (3x, exponential backoff) and structured error handling to Gemini API calls | `overnight_render_loop.py:231-242, 337-371` | both | Transient API failures silently skip grading iterations |
| **P1 HIGH** | Add `GEMINI_API_KEY` presence check to `startup_checks()` | `overnight_render_loop.py:88-149, 233` | grok (GPT-4o implicit) | Predictable failure deep in loop instead of clean early abort |
| **P1 HIGH** | Wrap `gemini_grade.py` logic in `if __name__ == '__main__': main()` | `gemini_grade.py:35-468` | gpt4o | Import-time execution is a

---

# WINNER DETERMINATION

# WINNER: **GPT-4o**

GPT-4o delivered the highest-quality analysis across both cycles: its Cycle 1 findings proved accurate and were independently confirmed in Cycle 2 (hardcoded TTS path, daemon scheduling mismatch, orphaned tmux sessions, shell injection), demonstrating superior initial accuracy with zero false positives surfaced. Critically, it provided the most actionable and specific recommendations — including exact line numbers, concrete before/after code patterns, and deployment-context reasoning — while achieving complete section coverage that Grok partially replicated only by referencing GPT-4o's own output in Cycle 2.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × blast radius. Implement in sequence; each item unblocks or reduces risk for those below it.

---

## P0 — CRITICAL / IMPLEMENT BEFORE NEXT DEPLOY

### 1. Eliminate `shell=True` + Unescaped Path Interpolation (Command Injection)
**Files:** `overnight_render_loop.py:67-70, 271, 289, 293, 299, 391-400` | `gemini_grade.py:31-33, 57, 90, 101, 110, 125, 136-137`

Refactor the shared `run()` helper to accept a list and set `shell=False` by default. Replace every f-string command construction with an argument list. Use `subprocess.STDOUT` in place of `2>&1` shell redirection.

```python
# Before
def run(cmd, **kwargs):
    return subprocess.run(cmd, shell=True, **kwargs)
run(f'ffprobe -v error -i {video} -select_streams v:0 ...')

# After
def run(cmd: list[str], **kwargs):
    return subprocess.run(cmd, shell=False, **kwargs)
run(['ffprobe', '-v', 'error', '-i', str(video),
     '-select_streams', 'v:0', ...])
```

---

### 2. Kill Orphaned tmux/Claude Sessions on Timeout
**File:** `overnight_render_loop.py:397-403`

`fire_cc_fix()` currently lets the tmux session live after the deadline expires. This leaks processes, holds file locks, and can mutate the repo while the next iteration is already running.

```python
# After timeout block — add unconditionally:
subprocess.run(['tmux', 'kill-session', '-t', session_name],
               capture_output=True)
```

---

## P1 — HIGH / IMPLEMENT IN NEXT SPRINT

### 3. Fix Hardcoded Home-Relative TTS Path
**File:** `overnight_render_loop.py:131, 216`

Both `startup_checks()` and `check_tts_ready()` reference `~/protocol_pulse/video_pipeline_v3/tts_local.py` as a hardcoded string. If the repo is deployed to any other path, startup will report TTS healthy while runtime will fail — a silent disagreement between the two checks.

```python
# Before
TTS_SCRIPT = os.path.expanduser("~/protocol_pulse/video_pipeline_v3/tts_local.py")

# After
TTS_SCRIPT = PIPELINE_DIR / "tts_local.py"
# where PIPELINE_DIR is already resolved from the script's __file__ location
```

---

### 4. Fix Daemon Scheduling Contract Mismatch
**File:** `overnight_render_loop.py:600-604`

Current behavior: run immediately on startup, then sleep until next 8am ET. Documented contract: "runs at 08:00 ET daily." These disagree. An ops restart at 14:00 ET triggers an unscheduled render.

```python
# Before
while True:
    run_cycle()
    sleep_until_next_8am()

# After
while True:
    sleep_until_next_8am()   # always wait first
    run_cycle()
```

---

### 5. Add tmux + Claude Binary Validation to `startup_checks()`
**File:** `overnight_render_loop.py:88-149`

`fire_cc_fix()` is on the hot path of every non-Grade-A iteration. If `tmux` or `claude` are absent, the fix loop silently fails for all 8 iterations before the run is abandoned. Detect this at startup.

```python
for binary in ['tmux', 'claude']:
    if not shutil.which(binary):
        log.error(f"Required binary not found: {binary}")
        sys.exit(1)
```

---

## P2 — MEDIUM / IMPLEMENT WITHIN TWO SPRINTS

### 6. Fix Temp WAV Leak in TTS Artifact Check
**File:** `overnight_render_loop.py:307-325`

The temp WAV file created during TTS verification is only unlinked on the happy path. Any exception before the `unlink()` call leaves it on disk permanently. Use a context manager.

```python
import tempfile, contextlib

with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
    tmp_path = Path(f.name)
try:
    # ... TTS synthesis into tmp_path ...
    validate(tmp_path)
finally:
    tmp_path.unlink(missing_ok=True)
```

---

### 7. Harden Fallback Grade Parser
**File:** `overnight_render_loop.py:441-450`

Parsing `GRADE_*|score|path|verdict` with a bare `split("|")` will silently produce wrong fields if a path contains a pipe character or if the format drifts. Add field-count validation and a structured format contract.

```python
parts = line.split("|")
if len(parts) != 4:
    log.warning(f"Unexpected grade line format: {line!r}")
    continue
grade_tag, score_str, path, verdict = parts
```

---

### 8. Atomic Write for Heartbeat/State JSON
**File:** `overnight_render_loop.py:589-598`

State JSON is written in-place. A crash mid-write produces a truncated file that fails to parse on the next startup, silently resetting all counters.

```python
import os, json, tempfile

def write_state_atomic(path: Path, data: dict):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)   # POSIX atomic on same filesystem
```

---

### 9. Escalate Silent Render Failures Beyond Log Entry
**File:** `overnight_render_loop.py:420-421`

When `run_render()` returns no output file, the loop logs and continues — burning an iteration with no diagnostic signal sent to operators. At minimum, emit a structured warning to the heartbeat payload so monitoring surfaces it.

---

## P3 — LOW / BACKLOG WITH TRACKING TICKET

### 10. Document and Enforce `PIPELINE_DIR` Resolution Contract
All path construction should derive from a single `PIPELINE_DIR` constant resolved relative to `__file__`, not `os.getcwd()` or `~`. Audit every `Path(...)` construction in both files and unify.

### 11. Add Integration Test for the 8-Iteration Grading Loop
The core loop (render → forensics → grade → fix → repeat) has no automated test coverage. A mock-render harness that injects synthetic grade responses would catch regressions in loop termination logic (Grade A short-circuit, iteration cap, time cap) before they reach production.

### 12. Consider Structured Logging (JSON Lines) for Machine Consumption
Current logging is human-readable strings. If heartbeat data or grade history is ever aggregated across runs or hosts, structured log output (`{"event": "grade", "score": 91, "iteration": 3, ...}`) will be necessary. Lay the groundwork now while the log call sites are still manageable.