# CONSENSUS REPORT — PIPELINE-COMPREHENSIVE-AUDIT — CYCLE 2
Generated: 2026-03-23 00:05
Models: gpt4o, grok (+1 failed — Gemini 2.5 Pro: 403 PERMISSION_DENIED, leaked API key)

---

## SCORES

| Subsystem       | Gemini  | GPT-4o  | Grok    | Consensus |
|-----------------|---------|---------|---------|-----------|
| Backend logic   | —       | 70/100  | 73/100  | **71/100** |
| Frontend/UI     | —       | N/A     | N/A     | **N/A** |
| Error handling  | —       | 65/100  | 65/100  | **65/100** |
| Security        | —       | 60/100  | 65/100  | **62/100** |
| Performance     | —       | 75/100  | 78/100  | **76/100** |
| Law compliance  | —       | 55/100  | 58/100  | **56/100** |
| World-class gap | —       | 50/100  | 50/100  | **50/100** |
| **OVERALL**     | —       | **65/100** | **66/100** | **65/100** |

> ⚠️ Gemini scores absent due to API failure. Consensus derived from 2 of 3 models. Confidence is moderate; treat all findings as 2-model majority rather than 3-model unanimous until Gemini is re-run with a valid key.

---

## UNANIMOUS FINDINGS (all 2 available models agree — implement unconditionally)

### U1 — No Rate Limiting on External API Calls
**What it is:** The codebase makes calls to Gemini API, ElevenLabs TTS, and other paid external services with no rate limiting, throttling, or quota-guard logic. A runaway render loop (max 8 iterations over 6 hours) can hammer these services, exhaust quotas, and generate unexpected costs or hard failures mid-run.
**Files/Lines:**
- `overnight_render_loop.py:266-284` — `gemini_call` retry block fires immediately on failure with no inter-call throttle
- `local_watchdog.py:207-221` — external API calls with no rate guard
- `video_pipeline_v3/tts_engine.py:1082` — ElevenLabs TTS call with no quota check
**What to change:** Implement a token-bucket or sliding-window rate limiter wrapping all external API call sites. At minimum, add a configurable `RATE_LIMIT_CALLS_PER_MINUTE` env var and enforce it before each call. Add quota exhaustion detection (HTTP 429 / specific error codes) that triggers graceful pipeline pause with alert, not silent retry.

---

### U2 — Silent Failures on API Timeout / Malformed Response Propagate Undetected
**What it is:** `gemini_call` (overnight_render_loop.py:253-284) returns `None` after all retries are exhausted. The caller at lines 513-549 silently skips the grading iteration without escalation, alerting, or aborting the loop. The same pattern applies to malformed JSON from Gemini (lines 417-451) — a basic retry is attempted but there is no deeper fallback, circuit-breaker, or human-alerting mechanism. The pipeline can burn through all 8 iterations producing no grades whatsoever, and the operator has no indication until they inspect logs.
**Files/Lines:**
- `overnight_render_loop.py:253-284` — `gemini_call` returns `None` silently
- `overnight_render_loop.py:417-451` — malformed JSON retry without escalation
- `overnight_render_loop.py:513-549` — caller skips iteration on `None` grade without abort or alert
- `video_pipeline_v3/daily_producer.py:99-116` — BTC price fetch silently defaults to "N/A"
**What to change:** After retry exhaustion, raise a structured exception or set a pipeline-abort flag. Add a `CONSECUTIVE_GRADE_FAILURES_THRESHOLD` (suggest: 3) that triggers an operator alert (Slack/email/webhook) and halts the loop cleanly. For the BTC price fetch, surface the degraded-data condition in the run report rather than silently continuing.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above also qualify. Additional majority findings:

### M1 — Race Condition on Global Counter Updates in `write_heartbeat`
**Models:** GPT-4o (identified `os.makedirs` race) + Grok (identified non-atomic global counter updates)
**What it is:** Global counters `_total_episodes` and `_consecutive_failures` are read and written in `write_heartbeat` (lines 176-205) without locking. Under concurrent runs (e.g., watchdog + render loop running simultaneously), these counters can be corrupted. Additionally, `os.makedirs` at lines 37-38 has no `exist_ok=True` or exception guard, creating a TOCTOU race if two processes initialize simultaneously.
**Files/Lines:**
- `overnight_render_loop.py:176-205` — global counter mutation without lock
- `overnight_render_loop.py:37-38` — `os.makedirs` without `exist_ok=True`
**What to change:** Use `threading.Lock()` to guard all mutations of `_total_episodes` and `_consecutive_failures`. Change all `os.makedirs` calls to include `exist_ok=True`. If multi-process (not just multi-thread) concurrency is expected, use file-based locking (`fcntl.flock`).

### M2 — Database Indexing on Sort/Filter Columns Not Evidenced
**Models:** GPT-4o (explicit violation) + Grok (partial agreement)
**What it is:** The project spec (PIPELINE_LAWS.md) requires database indexes on all columns used for sorting and filtering. No migration files or model definitions in the reviewed code demonstrate these indexes exist.
**Files/Lines:** Database model/migration files (not directly shown in reviewed code)
**What to change:** Audit all SQLAlchemy models for columns used in `.filter()`, `.order_by()`, `.group_by()`. Add `index=True` to those column definitions or add explicit `Index(...)` objects. Generate and apply a migration. This is a law compliance item, not optional.

### M3 — `run_render` Assumes Output File Always Produced; No Recovery Path
**Models:** GPT-4o + Grok
**What it is:** `run_render` (lines 287-311) logs a fatal error if no output file is produced but continues the loop. Over 8 iterations this means the loop can exhaust its budget making no progress, with no backoff, no early-abort, and no operator notification.
**Files/Lines:**
- `overnight_render_loop.py:287-311` — empty output logs error but does not break loop or alert
**What to change:** After N consecutive render failures (suggest: 3, configurable), abort the loop and surface a structured failure report. Do not silently iterate to the maximum.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — TTS Provider Failure Has No Ultimate Fallback or Alert (Grok)
**What it is:** `tts_engine.py` attempts a fallback for Host 2 (lines 984-990) but there is no escalation path if all TTS providers (local + ElevenLabs) fail or exhaust quotas. The pipeline stalls silently with degraded or absent audio.
**Assessment: IMPLEMENT.** This is a real production risk. Add an explicit TTS-total-failure condition that writes a structured error to the run manifest and aborts the episode gracefully rather than producing a silent corrupt artifact. A webhook alert here is high value.

### X2 — Potential Orphaned Process / Resource Leak from CC Fix Session Timeout (Grok)
**What it is:** `fire_cc_fix` in `overnight_render_loop.py:476-484` waits up to 2700 seconds for a tmux session, then issues `kill-session`. If the tmux session or its child processes ignore the kill or are in an uninterruptible state, orphaned processes accumulate across overnight runs.
**Assessment: IMPLEMENT.** After `kill-session`, add a `pkill -f <session_pattern>` fallback and verify process table is clean. Log a warning if cleanup is needed. Over a multi-night automated run this becomes a host stability issue.

### X3 — Timestamp Validation of Render Output Is Insufficient (Grok)
**What it is:** `run_render` checks that the output file was created after render start (line 304) but does not validate file format, codec, or that it isn't a stale artifact from a previous run that happened to be touched.
**Assessment: INVESTIGATE FURTHER.** An `ffprobe` format-validation call on the output file before accepting it as a valid render product is low-cost and high-value. If `ffprobe` is already called elsewhere in the health check (`_post_render_health_check`, lines 172-218), consolidate and ensure it runs before grading is triggered.

### X4 — N+1-Like Repeated `ffprobe` Calls Without Caching (Grok)
**What it is:** `daily_producer.py:845-861` makes repeated `ffprobe` calls on the same files without caching results.
**Assessment: IMPLEMENT (low urgency).** A simple in-process dict cache keyed on filepath+mtime eliminates redundant subprocess spawns. Low risk, meaningful speedup on large clip libraries.

### X5 — `.env` Loading Has No Failure Guard (GPT-4o)
**What it is:** Environment variables are loaded from a `.env` file but there is no check for partial load failures. A truncated or malformed `.env` silently produces a misconfigured runtime.
**Assessment: IMPLEMENT.** After loading, explicitly assert the presence of all required keys (GEMINI_API_KEY, ELEVENLABS_API_KEY, etc.) and fail fast with a descriptive error if any are missing. This prevents the far more confusing downstream failures.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Urgency of Database Indexing Fix
- **GPT-4o:** Explicit law compliance violation, P1 priority.
- **Grok:** Partially agrees but deprioritizes because "the provided code does not directly interact with the database."

**Tiebreaker — GPT-4o is correct.** The fact that the reviewed files don't contain model definitions doesn't mean indexing is acceptable to defer. PIPELINE_LAWS.md is an unconditional requirement. The fix lives in model/migration files. Mark as P1 and audit those files explicitly. Grok's deprioritization reasoning is a scope limitation, not a technical justification.

### C2 — Overall Security Score
- **GPT-4o:** 60/100 (harsher, emphasizing missing rate limiting as near-critical)
- **Grok:** 65/100 (slightly more lenient)

**Tiebreaker:** Score the security dimension at **62/100** (midpoint). The absence of rate limiting on paid external APIs in an automated overnight loop is a genuine financial and operational risk, not just a best-practice gap. GPT-4o's severity framing is correct. The 62 reflects real gaps without over-penalizing for issues that have no evidence of active exploitation surface.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in the second pass)

1. **Gemini API Retry with Exponential Backoff** (`overnight_render_loop.py:253-284`) — The retry mechanism itself is correctly structured. Do not remove or simplify it; the fix is to add escalation *after* retries, not replace them.

2. **No Raw SQL / No SQL Injection Surface** — Both models confirmed the codebase uses SQLAlchemy ORM correctly with no raw query construction from user input. Do not introduce raw SQL in the second pass.

3. **No Authentication Bypasses** — Both models confirmed no routes or endpoints expose auth bypasses. Do not alter auth flow.

4. **No Three.js / WebGL / Canvas UI Violations** — Tech stack compliance on the frontend rendering layer is clean. Do not introduce prohibited libraries.

5. **Clip Extraction Fallback Logic** (`daily_producer.py:396-453`) — The alternates-retry approach for insufficient clips is structurally correct. The fix needed is a hard retry cap (see M3 pattern), not a rewrite of the fallback logic itself.

6. **Environment Variable Usage for API Keys** — Keys are not hardcoded in source. The fix needed (X5) is validation-on-load, not a structural change to how keys are stored.

---

## LAW COMPLIANCE CONSENSUS

| Law / Requirement | Status | Determination |
|---|---|---|
| Python 3.12 + Flask + SQLAlchemy stack | ✅ Compliant | Both models confirmed |
| Database indexes on sort/filter columns | ❌ **VIOLATION** | No evidence of indexes; P1 fix required |
| No Three.js / WebGL / Canvas for UI | ✅ Compliant | Both models confirmed |
| API quota / rate limiting guards | ❌ **VIOLATION** | Absent across all external API call sites; P0 fix required |
| No raw SQL / injection surface | ✅ Compliant | Confirmed |
| Secrets management (no hardcoding) | ✅ Compliant (partial) | Keys in env vars but no load validation; X5 fix required |

**Final determination:** 2 active law violations. Code may not merge until U1 (rate limiting) and M2 (database indexing) are resolved. The secrets partial-compliance (X5) must also be addressed to reach full compliance posture.

---

## SECURITY CONSENSUS

Priority order (both models in agreement):

1. **P0 — Rate Limiting on External API Calls** (U1) — Financial and operational risk. An overnight loop with no throttle can exhaust paid quotas in a single bad run. Highest urgency.
2. **P1 — Silent API Failure Propagation** (U2) — Not a direct security vulnerability but a reliability/integrity risk: grades are silently skipped, operators are unaware, and the system produces outputs without valid quality gates. Treat as a security-adjacent integrity issue.
3. **P2 — Environment Variable Load Validation** (X5) — Misconfigured secrets lead to unexpected runtime behavior. Fail-fast validation prevents ambiguous failure modes.
4. **P2 — Race Conditions on Shared State** (M1) — Under concurrent execution, counter corruption could produce misleading run reports. Not an external attack surface but an internal integrity risk.

No evidence of: SQL injection, authentication bypass, XSS, CSRF, or hardcoded secrets. These are genuine strengths.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

### WC1 — No Operator Alerting / Observability Layer
Both models identified that the pipeline can fail silently across multiple dimensions (API timeouts, empty renders, grade skips, TTS failures). A world-class automated pipeline would have structured alerting (Slack/PagerDuty/webhook) triggered on: grade-failure streaks, API quota exhaustion, render output absence, and loop abort conditions. Currently, an operator discovers failures only by reading logs after the fact.

### WC2 — No Circuit Breaker Pattern on External Dependencies
Both models flagged the pattern of retrying then silently failing on external services. A world-class system implements circuit breakers: after N failures in a window, open the circuit, stop hammering the service, alert the operator, and attempt recovery on a schedule. This is distinct from simple retry-with-backoff and prevents the cascade where one bad API key or network partition burns the entire overnight budget.

### WC3 — Missing Monitoring / Metrics Instrumentation
Both models noted the absence of structured metrics (Prometheus counters, Datadog gauges, or equivalent) on: render success/failure rates, grading score distribution, API call latency, TTS provider fallback frequency. Without metrics, there is no baseline for detecting regressions and no data for capacity planning.

### WC4 — No Hard Retry Cap on Clip Extraction Fallback
Both models (directly or by implication) flagged that the clip extraction fallback loop in `daily_producer.py:396-453` has no hard ceiling on retries if no valid candidates remain, risking an effectively infinite loop. World-class pipelines always have an unconditional outer timeout or iteration cap on every loop.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Implement rate limiting (token-bucket or sliding window) for all external API calls; add quota-exhaustion detection with graceful pipeline pause and operator alert | `overnight_render_loop.py:266-284`, `local_watchdog.py:207-221`, `tts_engine.py:1082` | all (2/2) | Financial risk; operational failure risk; law compliance violation |
| **P0 CRITICAL** | Add consecutive-grade-failure threshold (suggest: 3); raise structured exception and abort loop with operator alert when `gemini_call` returns `None` or JSON is malformed after all retries | `overnight_render_loop.py:253-284`, `417-451`, `513-549` | all (2/2) | Silent pipeline degradation; grades bypassed without operator awareness |
| **P1 HIGH** | Add database indexes on all sort/filter columns in SQLAlchemy models; generate and apply migration | DB model/migration files | 2/2 | Law compliance violation (PIPELINE_LAWS.md); query performance |
| **P1 HIGH** | Add N consecutive render-output-absent abort with operator alert; do not silently iterate to max iterations | `overnight_render_loop.py:287-311` | 2/2 | Loop can exhaust 8-iteration budget with no output and no signal |
| **P1 HIGH** | Fix `os.makedirs` to use `exist_ok=True`; add `threading.Lock()` guards on `_total_episodes` and `_consecutive_failures` mutations | `overnight_render_loop.py:37-38`, `176-205` | 2/2 | Race condition under concurrent watchdog + render loop execution |
| **P1 HIGH** | Assert all required env vars present after `.env` load; fail fast with descriptive error if any missing | `overnight_render_loop.py:58-70` | 1/2 (X5) | Misconfigured runtime from partial `.env` load is a silent but critical failure mode |
| **P1 HIGH** | Add TTS total-failure condition: if all providers fail, write structured error to run manifest, abort episode, send alert | `tts_engine.py:984-990`, `1082` | 1/2 (X1) | Silent audio degradation produces corrupt episode artifacts |
| **P2 MEDIUM** | After `kill-session` on CC fix timeout, add `pkill -f <session_pattern>` fallback and verify process table; log warning if cleanup required | `overnight_render_loop.py:476-484` | 1/2 (X2) | Orphaned processes accumulate over multi-night runs; host stability risk |
| **P2 MEDIUM** | Add hard retry cap to clip extraction fallback loop | `daily_producer.py:396-453` | 2/2 (implied) | Potential infinite loop if no valid clip candidates remain |
| **P2 MEDIUM** | Add `ffprobe` format+codec validation on render output before accepting for grading; consolidate with existing health check | `overnight_render_loop.py:304`, `172-218` | 1/2 (X3) | Timestamp-only check accepts stale artifacts and corrupt files |
| **P2 MEDIUM** | Cache `ffprobe` results keyed on filepath+mtime to eliminate redundant subprocess calls | `daily_producer.py:845-861` | 1/2 (X4) | Redundant subprocess spawns on large clip libraries; low-risk optimization |
| **P2 MEDIUM** | Validate tmux session actually starts in `fire_cc_fix`; log and escalate if tmux is misconfigured | `overnight_render_loop.py:472` | 1/2 | Silent failure if tmux unavailable |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

Two full cycles of 2-model review (Gemini failed both cycles — fix the leaked API key before Cycle 3) produce a consensus score of **65/100** with the following hard blockers:

1. **P0 — No rate limiting on paid external APIs.** An automated overnight loop with no throttle is one bad run away from quota exhaustion or an unexpected billing spike. This is not a nice-to-have; it is an operational and financial gate.

2. **P0 — Silent grade failure propagation.** The pipeline can complete 8 iterations, produce 8 render outputs, and never successfully grade any of them — all without alerting the operator. This makes the quality-gate loop meaningless as a correctness guarantee.

3. **P1 — Missing database indexes.** A stated law compliance requirement with no evidence of implementation. Cannot merge while a documented law is violated.

These three items are the absolute final blockers. The P1 HIGH items (race conditions, env var validation, TTS fallback) must also be resolved before a production merge, but the P0s are the gate. All P2 items should be addressed in the same pass given their low implementation cost.

> **Note on Gemini failure:** The leaked API key (`403 PERMISSION_DENIED`) must be rotated and a Cycle 3 Gemini pass run before treating any finding as truly 3-model unanimous. The current consensus is valid but carries reduced confidence on items where Gemini's independent signal would be most valuable (particularly the security scoring and law compliance determination). Rotate the key, re-run Gemini, and confirm scores hold.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/pipeline-comprehensive-audit_CONSENSUS_C2.md.

This is the FINAL PASS for pipeline-comprehensive-audit.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Implement rate limiting (token-bucket or sliding window) for all external API calls; add quota-exhaustion detection (HTTP 429 + service-specific codes) with graceful pipeline pause and operator alert | overnight_render_loop.py:266-284, local_watchdog.py:207-221, video_pipeline_v3/tts_engine.py:1082 | models: 2/2 | Financial and operational risk; law compliance violation

P0 CRITICAL | Add consecutive-grade-failure threshold (suggest: 3, make configurable via env); raise structured exception and abort loop with operator alert when gemini_call returns None or JSON is malformed after all retries | overnight_render_loop.py:253-284, 417-451, 513-549 | models: 2/2 | Silent pipeline degradation; quality gate rendered meaningless

P1 HIGH | Add database indexes on all sort/filter columns in SQLAlchemy models; generate and apply Alembic migration | DB model and migration files | models: 2/2 | Law compliance violation per PIPELINE_LAWS.md

P1 HIGH | Add N consecutive render-output-absent abort (suggest: 3) with structured error and operator alert; do not silently iterate to max iterations | overnight_render_loop.py:287-311 | models: 2/2 | Loop exhausts 8-iteration budget with no output and no signal

P1 HIGH | Fix os.makedirs to use exist_ok=True; add threading.Lock() guards on _total_episodes and _consecutive_failures mutations in write_heartbeat | overnight_render_loop.py:37-38, 176-205 | models: 2/2 | Race condition under concurrent watchdog + render loop execution

P1 HIGH | Assert all required env vars present after .env load (GEMINI_API_KEY, ELEVENLABS_API_KEY, and all other required keys); fail fast with descriptive error listing missing vars | overnight_render_loop.py:58-70 | models: 1/2 | Misconfigured runtime from partial .env load causes silent downstream failures

P1 HIGH | Add TTS total-failure condition: if all providers (local + ElevenLabs) fail or exhaust quotas, write structured error to run manifest

---

# WINNER DETERMINATION

# WINNER: **Grok**

Grok delivered the highest-quality analysis across both cycles by combining precise line-number citations with genuine forensic depth — notably identifying the non-atomic global counter race condition in `write_heartbeat` (lines 176-205) and the tmux silent-failure risk, both of which GPT-4o missed entirely in Cycle 1. In Cycle 2, Grok demonstrated stronger self-correction discipline, explicitly acknowledging each missed finding by source and integrating them structurally rather than listing them loosely, producing the more actionable and complete final report.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered implementation list, derived from 2-model consensus plus unique high-confidence findings. Items marked **[U]** = unanimous, **[G]** = Grok-unique, **[P]** = GPT-4o-unique.

---

## TIER 1 — CRITICAL: Fix Before Any Production Merge

### 1. [U] Rate-Limit All External API Call Sites
**Why first:** A runaway 8-iteration render loop can exhaust paid quotas in a single overnight run, generating real financial damage and silent mid-run failures that corrupt the entire pipeline output.
**Implement:**
```python
# Add to config.py
RATE_LIMIT_CALLS_PER_MINUTE = int(os.getenv("RATE_LIMIT_CALLS_PER_MINUTE", "20"))

# Wrap in token-bucket decorator
@rate_limited(RATE_LIMIT_CALLS_PER_MINUTE)
def gemini_call(...): ...
```
**Files:** `overnight_render_loop.py:266-284`, `local_watchdog.py:207-221`, `tts_engine.py:1082`

---

### 2. [U] Silent `None` Return After Exhausted Retries in `gemini_call`
**Why second:** A `None` grade silently skips the iteration, making the loop believe it ran 8 cycles of valid grading when it may have run zero. This is a correctness failure masquerading as a performance issue.
**Implement:**
```python
# overnight_render_loop.py:253-284
if result is None:
    raise GradingUnavailableError(
        "gemini_call exhausted all retries without valid response. "
        "Aborting render loop — do not proceed to merge."
    )
```
**Files:** `overnight_render_loop.py:253-284`, callers at lines ~549

---

### 3. [G] Race Condition on Global Counters in `write_heartbeat`
**Why third:** Non-atomic updates to `_total_episodes` and `_consecutive_failures` under any concurrent access (manual re-run, watchdog, cron overlap) produce silently wrong counts that feed downstream grading and loop-exit logic — a state corruption bug.
**Implement:**
```python
import threading
_counter_lock = threading.Lock()

def write_heartbeat(...):
    with _counter_lock:
        _total_episodes += 1
        _consecutive_failures += ...
```
**Files:** `overnight_render_loop.py:176-205`

---

### 4. [G] `tmux` Launch in CC Fix Session Has No Success Validation
**Why fourth:** If tmux is misconfigured or missing, `run_cc_fix_session` returns without error, the loop marks the fix as attempted, and proceeds — meaning the entire corrective branch silently does nothing. This is an undetectable no-op failure.
**Implement:**
```python
# overnight_render_loop.py:472
result = subprocess.run(["tmux", "new-session", ...], capture_output=True)
if result.returncode != 0:
    raise EnvironmentError(f"tmux failed to start: {result.stderr.decode()}")
```
**Files:** `overnight_render_loop.py:454-486`

---

## TIER 2 — HIGH: Fix Within One Sprint

### 5. [P] `os.makedirs` Without `exist_ok` or Exception Handling
**Why:** In any environment where two processes could start concurrently (watchdog + main loop), unguarded `makedirs` raises `FileExistsError` and crashes the calling process entirely.
**Implement:**
```python
# Replace all bare os.makedirs calls
os.makedirs(path, exist_ok=True)
```
**Files:** `overnight_render_loop.py:37-38` and all other call sites — grep for `os.makedirs` project-wide

---

### 6. [U] Malformed JSON from Gemini Has No Deep Fallback
**Why:** The retry block catches some failures but does not handle structurally valid JSON that is missing expected keys (e.g., `grade`, `score`). A `KeyError` here propagates as an unhandled exception mid-loop.
**Implement:**
```python
grade = response_data.get("grade")
if grade not in ("A", "B", "C", "D", "F"):
    log.warning("Unexpected grade value: %s — treating as ungradeable", grade)
    return GradeResult.ungradeable()
```
**Files:** `overnight_render_loop.py:416-450`

---

### 7. [P] Database Indexes Missing on Sort/Filter Columns
**Why:** Without indexes, any dashboard query that sorts or filters episodes (by date, grade, status) performs a full table scan. At production volume this becomes a multi-second query blocking the Flask request thread.
**Implement:**
```python
# In relevant SQLAlchemy models
class Episode(Base):
    grade = Column(String, index=True)
    created_at = Column(DateTime, index=True)
    status = Column(String, index=True)
```
**Files:** All SQLAlchemy model definitions — audit every `Column` used in a `filter()` or `order_by()`

---

### 8. [G] `_post_render_health_check` Does Not Detect Corrupt Video Files
**Why:** Existence + size checks pass for a corrupt file. A zero-duration or undecodable video that passes health check gets graded, receives a real score, and potentially ships — a silent quality failure.
**Implement:**
```python
# After size check in daily_producer.py:172-218
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=noprint_wrappers=1:nokey=1", video_path],
    capture_output=True, text=True
)
if probe.returncode != 0 or not probe.stdout.strip():
    raise VideoCorruptError(f"ffprobe rejected output file: {video_path}")
```
**Files:** `video_pipeline_v3/daily_producer.py:172-218`

---

## TIER 3 — MEDIUM: Fix Before Public Launch

### 9. [P] `.env` Load Failures Not Handled Robustly
**Why:** If `python-dotenv` silently fails to load (missing file, permission error), all downstream `os.getenv()` calls return `None`, which causes cryptic failures far from the actual root cause.
**Implement:**
```python
from dotenv import load_dotenv
loaded = load_dotenv()
if not loaded:
    raise EnvironmentError(
        ".env file not found or unreadable. "
        "Copy .env.example to .env and populate required keys."
    )
```
**Files:** Entry point / `config.py`

---

### 10. [U] ElevenLabs TTS Has No Quota Pre-Check
**Why:** A TTS call that fails mid-render (quota exhausted) produces a partial video with no audio, which may still pass the file-size health check and proceed to grading with a corrupt artifact.
**Implement:** Add a `/v1/user/subscription` quota check to `tts_engine.py` at render startup. If remaining characters < estimated script length, abort with `QuotaInsufficientError` before any render work begins.
**Files:** `video_pipeline_v3/tts_engine.py:1082`, render startup sequence

---

### 11. [G] `shutil.which` Return Value Not Validated for Required Bin