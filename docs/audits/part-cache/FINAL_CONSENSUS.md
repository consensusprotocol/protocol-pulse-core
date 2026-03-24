# CONSENSUS REPORT — PART-CACHE — CYCLE 2
Generated: 2026-03-24 18:46
Models: gpt4o, grok, gemini

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Backend Logic   | 55     | 68     | 70   | **64**    |
| Error Handling  | 60     | 60     | 60   | **60**    |
| Security        | 72     | 70     | 68   | **70**    |
| Performance     | 65     | 63     | 65   | **64**    |
| Law Compliance  | 70     | 73     | 75   | **73**    |
| World-Class Gap | 55     | 58     | 55   | **56**    |
| **OVERALL**     | **63** | **65** | **65** | **64**  |

> **Scoring note:** Gemini's Backend Logic drop to 55 is the most aggressive and is substantiated by the verified non-functional checkpoint logic. The consensus splits the difference between GPT-4o/Grok's relatively optimistic view and Gemini's pessimism. Overall 64/100 reflects a pipeline that works in the happy path but fails structurally under stress, crashes, or API disruption.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Silent `except` Blocks Swallow Errors
- **What:** Throughout `daily_producer.py`, bare `except: pass` and `except Exception:` blocks with no logging suppress critical failures silently. Diagnosing production failures becomes impossible.
- **Where:** Lines ~116, ~139, ~537, ~1030, ~1306 and other scattered locations throughout the file.
- **Fix:** Replace every bare `except` with `except Exception:` followed by `logger.exception("Context-specific message")`. Never use `pass` alone in an except block. At minimum, emit `logger.error(..., exc_info=True)` so tracebacks appear in logs.

### U2 — No Retry / Backoff on External API Calls
- **What:** All external API calls — BTC price (CoinGecko, mempool.space), Claude clip selection, ElevenLabs TTS, and yt-dlp extractions — have zero retry logic. A single transient network hiccup fails the entire pipeline.
- **Where:** Lines ~142–161 (`get_btc_price`), ~790 (clip extraction), ~1081 (TTS generation).
- **Fix:** Apply a retry decorator uniformly. Use `tenacity`:
  ```python
  from tenacity import retry, stop_after_attempt, wait_exponential
  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
  def get_btc_price(): ...
  ```
  Apply the same decorator to all external I/O functions.

### U3 — Unvalidated External API Responses Used Downstream
- **What:** API responses (BTC price returning `"$N/A"`, cached transcripts, clip metadata) are passed directly into video generation, thumbnail text, and scripts without schema validation. Malformed or empty responses silently degrade content quality or cause downstream crashes.
- **Where:** Lines ~145–160 (`get_btc_price` return value propagated to line ~170 and ~1212), lines ~677–690 (transcript cache loaded without integrity check).
- **Fix:** After each API call, validate the response shape before use. For `get_btc_price`, if the result is `"$N/A"`, raise a warning-level alert and consider halting or substituting a clearly-labeled placeholder. For transcripts, validate non-empty and structurally correct before injecting into the clip selection pipeline.

### U4 — Monolithic `run_pipeline()` Function (~1000 lines)
- **What:** The entire pipeline lives in a single function spanning lines 522–1549. This makes it untestable in isolation, impossible to profile, and dangerous to modify — any change can have unpredictable side effects anywhere in the pipeline.
- **Where:** `run_pipeline()`, lines 522–1549.
- **Fix:** Extract each logical stage into its own named function with a clear signature and return type:
  - `fetch_btc_price()` 
  - `scan_channels()` 
  - `select_and_extract_clips()` 
  - `generate_script_and_tts()` 
  - `assemble_video()` 
  - `run_quality_checks()` 
  - `publish_outputs()` 
  
  `run_pipeline()` becomes an orchestrator that calls these in sequence and handles checkpoint writes between them.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Checkpoint / Resume Logic Is Non-Functional *(Gemini + Grok + GPT-4o all flagged; unanimous in practice)*
- **What:** `_read_checkpoint()` (line ~120) correctly reads the last completed step into `resume_step`, and this is retrieved at line ~540. However, `resume_step` is **never used to branch execution** — it only triggers a log message. The pipeline always restarts from Step 1. The "resume-on-crash" feature advertised in comments is completely broken.
- **Where:** Lines 120 (`_read_checkpoint`), 540–553 (usage site).
- **Fix:** After reading `resume_step`, implement step-skipping logic:
  ```python
  STEPS = ["btc_price", "channel_scan", "clip_selection", "tts", "assembly", "qc", "publish"]
  resume_idx = STEPS.index(resume_step) if resume_step in STEPS else 0
  for i, step in enumerate(STEPS):
      if i < resume_idx:
          logger.info(f"Skipping completed step: {step}")
          continue
      run_step(step)
      _write_checkpoint(step)
  ```
  This requires the U4 refactor (modular functions) to be implemented first — the two fixes are interdependent.

### M2 — Threading Resource Leak in Space Tap Feature *(Gemini + Grok)*
- **What:** The Space Tap thread at lines ~1012–1018 is spawned with a `join(timeout=120)`. If `_fetch_spaces` hangs, the main thread correctly continues — but the zombie thread is left running indefinitely. Over multiple pipeline runs, this exhausts file descriptors and memory.
- **Where:** Lines ~1012–1018.
- **Fix:** Replace `threading.Thread` with `multiprocessing.Process`, which supports reliable termination:
  ```python
  import multiprocessing
  p = multiprocessing.Process(target=_fetch_spaces, args=(spaces_result,))
  p.daemon = True
  p.start()
  p.join(timeout=120)
  if p.is_alive():
      logger.warning("Space Tap timed out — terminating process.")
      p.terminate()
      p.join()
  ```

### M3 — No Fallback When Zero Clips Are Selected or Extracted *(GPT-4o + Grok)*
- **What:** If channel scanning yields no viable clips (e.g., all channels have been used recently, all clips fail quality threshold), the pipeline continues without clips. The subsequent assembly step will either crash or produce an empty/corrupt video with no human alert.
- **Where:** Lines ~740 (post-selection check), ~873 (post-extraction check).
- **Fix:** After clip selection and after extraction, assert minimum clip count:
  ```python
  if len(selected_clips) == 0:
      send_alert("CRITICAL: Zero clips selected — pipeline halted.")
      raise RuntimeError("No clips selected; cannot produce episode.")
  ```
  Consider a final fallback to a pre-approved "evergreen" clip bank before halting.

### M4 — Inconsistent Duration Validation Between Pre-Flight and Post-Render *(Gemini + Grok)*
- **What:** Pre-flight QC accepts videos of 7–15 minutes (420–900s, line ~400). Post-render health check enforces 8–15 minutes (480–900s, line ~244). A video can pass pre-flight and fail post-render, or vice versa, depending on encoding. This violates the `PIPELINE_LAWS` spirit and creates confusing failures.
- **Where:** Line ~244 (post-render), line ~400 (pre-flight).
- **Fix:** Define a single shared constant and use it everywhere:
  ```python
  DURATION_MIN_SECONDS = 480  # 8 minutes — match the stricter post-render law
  DURATION_MAX_SECONDS = 900  # 15 minutes
  ```
  Decide on one canonical range (the post-render rule should be authoritative) and apply it to pre-flight as well.

### M5 — Inconsistent Subprocess Python Interpreter *(Gemini + Grok)*
- **What:** `format_multiplier.py` is correctly launched using `sys.executable` (line ~1500), ensuring the virtualenv Python is used. But `tweet_machine.py` is launched with a hardcoded `python3` (line ~1608), which resolves to the system Python, breaking in any virtualenv setup.
- **Where:** Line ~1608.
- **Fix:**
  ```python
  subprocess.Popen([sys.executable, "tweet_machine.py", ...])
  ```

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### X1 — Chained Sequential Re-Encodes in Pre-Flight Fixes *(Gemini only)*
- **What:** `_apply_preflight_fixes()` (lines ~434–520) runs a separate full FFmpeg re-encode for each detected issue (freeze, silence, loudness). A video with all three issues is re-encoded three times, tripling render time and introducing avoidable generational quality loss.
- **Assessment:** ✅ **IMPLEMENT.** This is a well-reasoned, concrete performance and quality finding. Combining all filters into a single FFmpeg pass (`-vf`, `-af` filter chains) is standard FFmpeg practice and directly improves both output quality and pipeline speed.
- **Fix:** Build a combined filter string from all detected issues and run one consolidated FFmpeg invocation.

### X2 — A/V Sync "Nuclear Re-Encode" Treats Symptom, Not Cause *(Gemini only)*
- **What:** The A/V sync repair at lines ~1249–1269 uses a brute-force full re-encode to fix drift. This is a symptom fix — significant A/V drift indicates a root-cause problem in the assembler (e.g., VFR clip handling, timestamp mismanagement).
- **Assessment:** ✅ **INVESTIGATE FURTHER.** The brute-force fix is acceptable as a short-term safety net, but it must be paired with detailed logging that captures drift magnitude each run. If drift is consistently non-zero, the assembler needs a deeper audit. Add a `logger.warning(f"AV sync drift: {drift_ms}ms — applied nuclear re-encode")` so ops can trend this metric.

### X3 — Music File Existence Not Validated Before Use *(Grok only)*
- **What:** `select_music_bed()` and `select_intro_music()` return file paths that are not verified to exist before being passed to the assembler. A missing file causes a cryptic assembler crash.
- **Assessment:** ✅ **IMPLEMENT.** This is a trivial one-line fix with meaningful crash-prevention value:
  ```python
  assert Path(music_path).exists(), f"Music file missing: {music_path}"
  ```
- **Where:** Lines ~943–944.

### X4 — Hardcoded FFmpeg Timeouts Not Configurable *(Grok only)*
- **What:** Timeout values for FFmpeg/FFprobe operations (e.g., 30s, 300s) are hardcoded and may not suit different hardware or long videos.
- **Assessment:** ⚠️ **INVESTIGATE FURTHER.** This is real but lower urgency. Add these to a config section or environment variables (`FFMPEG_TIMEOUT_SECONDS`, `FFPROBE_TIMEOUT_SECONDS`) but do not block the release on this alone.

### X5 — Fallback Clip Retry Does Not Track Failed Channels *(Gemini only)*
- **What:** In the fallback clip selection loop (lines ~794–851), `tried_video_ids` is updated on extraction failure, but `used_channels` is not. Subsequent fallback candidates from a problematic channel (e.g., geo-blocked) will be retried wastefully.
- **Assessment:** ✅ **IMPLEMENT.** Low-effort, meaningful fix. After a failed extraction, add the channel to `used_channels`:
  ```python
  tried_video_ids.add(fc["video_id"])
  used_channels.add(fc["channel_id"])  # Add this line
  ```

---

## CONFLICTS (models disagree — your tiebreaker)

### C1 — File Lock Atomicity / Race Condition Risk
- **GPT-4o / Grok:** Flagged `fcntl.flock` as potentially non-atomic and a source of race conditions.
- **Gemini:** Assessed `fcntl.flock` as correct, standard, and robust for local POSIX filesystems.
- **Tiebreaker: Gemini is right.** `fcntl.flock` is the canonical, reliable mechanism for advisory process-level locking on Linux/macOS with a local filesystem. The race condition concern is only valid for NFS or exotic network filesystems, which is not the deployment environment described. This is **not a bug** and should not be changed. GPT-4o and Grok's concern is technically possible in the abstract but practically irrelevant here.

### C2 — Severity of Backend Logic Score
- **Gemini** scored Backend Logic at 55/100 (catastrophic drop due to broken checkpoint).
- **GPT-4o / Grok** scored it at 68–70 (moderate concern).
- **Tiebreaker: Gemini's direction is correct; the magnitude may be slightly aggressive.** The checkpoint issue is genuinely critical — it's a documented feature that completely does not work. However, the overall pipeline does produce output successfully in the happy path. Consensus lands at 64, which acknowledges the critical flaw without discarding the pipeline's functional core.

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

1. **Secret Management:** All API keys and credentials are sourced from environment variables. No hardcoded secrets appear anywhere in the reviewed code. Do not change this pattern.

2. **Process-Level Instance Locking:** The use of `fcntl.flock` on a `/tmp` lockfile correctly prevents multiple simultaneous pipeline instances. The implementation is sound. Do not change this.

3. **`--reuse-content` Flag Implementation:** Unlike the broken checkpoint system, the `--reuse-content` content lock path is correctly implemented and validated. It functions as documented.

4. **`sys.executable` for `format_multiplier.py`:** The use of `sys.executable` rather than `python3` for spawning the format multiplier subprocess is correct practice. Extend this pattern to `tweet_machine.py` (see M5) but do not change the format multiplier call.

5. **Feature Flag Architecture:** The `feature_flags.json` approach for toggling pipeline features is clean and operationally sound. All models found it adequate.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Finding |
|-----|--------|---------|
| SOLO HOST | ✅ COMPLIANT | All dialogue correctly assigned to single host in all code paths including fast-test. |
| CONTENT LOCK | ✅ COMPLIANT | `--reuse-content` path correctly implemented and respected. |
| FORMAT MULTIPLIER | ✅ COMPLIANT | Correctly spawned post-pipeline using `sys.executable`. |
| PIPELINE_LAWS: 8–15 min duration | ❌ VIOLATED | Pre-flight enforces 7–15 min (~420s), post-render enforces 8–15 min (~480s). These must be unified to one constant. The post-render law should be authoritative. |
| PIPELINE_LAWS: resume-on-crash | ❌ VIOLATED | Checkpoint read but never used to skip steps. Feature is documented but completely non-functional. |

**Final determination:** 2 of the identifiable internal laws are violated. Both are fixable within hours. No external regulatory compliance issues were identified by any model.

---

## SECURITY CONSENSUS

| Priority | Issue | Models | Finding |
|----------|-------|--------|---------|
| P1 | Hardcoded `python3` in subprocess call | Gemini, Grok | Launches `tweet_machine.py` with system Python; could load wrong environment; indirect risk if system Python has vulnerable packages vs. the venv. |
| P2 | Zombie threads from Space Tap | Gemini, Grok | Resource exhaustion risk over repeated runs; not an injection vector but a DoS risk. |
| P3 | Unvalidated API responses propagated | All | If an API is compromised or returns adversarial content, it flows directly into video scripts and thumbnails without sanitization. Low probability, non-zero risk. |

**Overall security posture:** Adequate for an internal production CLI. No SQL injection, no hardcoded secrets, no XSS surface. The risks are operational reliability risks more than classic security vulnerabilities. The `python3` subprocess issue is the most concrete security-adjacent finding.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly world-class pipeline:

1. **Modularity and Testability** *(All 3 models):* A world-class pipeline has each stage unit-testable in isolation with mocked dependencies. The current monolith cannot be tested at the function level. Every stage should be its own module with a typed interface.

2. **Observability and Structured Logging** *(All 3 models):* World-class pipelines emit structured logs (JSON) with consistent fields: `run_id`, `step`, `duration_ms`, `status`, `error`. The current logging is ad-hoc strings. A tool like `structlog` would transform debuggability overnight.

3. **Retry and Circuit-Breaker Infrastructure** *(All 3 models):* Production-grade pipelines have a centralized retry/backoff/circuit-breaker layer (e.g., `tenacity` + a circuit breaker for repeated API failures) rather than per-call ad-hoc handling.

4. **Checkpoint / Resume Done Right** *(Gemini + Grok + GPT-4o):* True resume-on-crash requires (a) step-skipping logic, (b) idempotent steps (re-running a step produces the same result), and (c) artifact validation before marking a step as complete. None of these three requirements are currently met.

5. **Single-Pass Pre-Flight Fix Pipeline** *(Gemini + Grok implied):* Multiple re-encodes for multiple issues is a fundamental FFmpeg anti-pattern. A world-class pipeline composes all fixes into a single filter graph.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Fix checkpoint/resume: use `resume_step` to actually skip completed steps | `daily_producer.py:540–553` | All | Feature is documented as working but is completely non-functional; crash recovery doesn't exist |
| **P0 CRITICAL** | Replace all `except: pass` and context-free except blocks with `logger.exception()` | `daily_producer.py:116, 139, 537, 1030, 1306` and others | All | Silent failures make production debugging impossible |
| **P0 CRITICAL** | Add `tenacity` retry + exponential backoff to all external API calls | `daily_producer.py:142–161, 790, 1081` | All | Transient network failures permanently halt or corrupt the pipeline |
| **P0 CRITICAL** | Validate API responses before downstream use; alert + halt on `$N/A` BTC price | `daily_producer.py:145–160, 677–690` | All | Malformed data propagates silently into final video output |
| **P0 CRITICAL** | Assert minimum clip count after selection and extraction; halt with alert if zero | `daily_producer.py:740, 873` | GPT-4o, Grok | Pipeline continues silently with no clips, producing empty/corrupt output |
| **P1 HIGH** | Replace Space Tap `threading.Thread` with `multiprocessing.Process` + `terminate()` | `daily_producer.py:1012–1018` | Gemini, Grok | Zombie threads cannot be killed; resource exhaustion risk across multiple runs |
| **P1 HIGH** | Unify duration validation to single constant (`DURATION_MIN_SECONDS = 480`) | `daily_producer.py:244, 400` | Gemini, Grok | Pre-flight and post-render enforce different ranges; law inconsistency causes confusing failures |
| **P1 HIGH** | Replace hardcoded `python3` with `sys.executable` for `tweet_machine.py` | `daily_producer.py:1608` | Gemini, Grok | Breaks in any virtualenv; may load wrong dependencies or wrong Python version |
| **P1 HIGH** | Refactor `run_pipeline()` into per-stage functions; make checkpoint skip logic viable | `daily_producer.py:522–1549` | All | Required for testability, debuggability, and making P0 checkpoint fix implementable |
| **P1 HIGH** | Combine pre-flight fixes into single FFmpeg filter pass | `daily_producer.py:434–520` | Gemini | 3 sequential re-encodes = 3x render time + generational quality loss |
| **P2 MEDIUM** | Track failed channels in fallback clip retry loop (add to `used_channels` on failure) | `daily_producer.py:794–851` | Gemini | Geo-blocked/private channels wastefully retried; minor but zero-cost fix |
| **P2 MEDIUM** | Validate music file existence before passing to assembler | `daily_producer.py:943–944` | Grok | Missing music file causes cryptic assembler crash rather than clean error |
| **P2 MEDIUM** | Add `logger.warning` with drift magnitude to A/V sync nuclear re-encode path | `daily_producer.py:1249–1269` | Gemini | Enables trending of sync drift; signals if assembler needs deeper audit |
| **P2 MEDIUM** | Make FFmpeg/FFprobe timeouts configurable via env vars | `daily_producer.py:237, 300, 347` | Grok | Hardcoded timeouts fail on different hardware or longer content |

---

## CYCLE 2 VERDICT

**NOT PRODUCTION READY.**

The pipeline functions on the happy path — clean network, available APIs, good content — but has three absolute blockers:

1. **The checkpoint/resume system is entirely non-functional.** Any crash restarts from zero, wasting compute and risking duplicate publishing. This is a documented feature promise that doesn't exist.

2. **Silent exception swallowing makes the pipeline undiagnosable in production.** Failures happen invisibly, producing no actionable signal for operators.

3. **Zero retry logic on external dependencies** means a 2-second Cloudflare hiccup against the ElevenLabs API aborts the entire episode production run.

These three issues — all unanimously flagged — are sufficient to block shipping. None is architecturally complex to fix. The estimated remediation effort for P0 items is 1–2 focused engineering days. The P1 refactor is a separate, larger effort (3–5 days) that should follow.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/part-cache_CONSENSUS_C2.md.

This is the FINAL PASS for part-cache.
The feature was reviewed by 3 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Fix checkpoint/resume: use resume_step to skip completed steps | daily_producer.py:540–553 | models: all | Feature

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini delivered the highest-quality analysis across both cycles. In Cycle 1, it independently identified the two most critical and non-obvious findings — the **non-functional checkpoint/resume logic** (a silent architectural failure that GPT-4o missed entirely and Grok only partially surfaced) and the **zombie thread resource leak** in Space Tap — both of which were verified correct and elevated to consensus unanimous findings. It also caught the **inefficient triple-reencoding in preflight fixes** and the **inconsistent duration constant discrepancy** (420s vs 480s), both specific, line-cited, and immediately actionable. In Cycle 2, Gemini's self-audit was the most structurally honest: it reproduced its prior findings with precision, acknowledged no regression in accuracy, and added the hardcoded Python interpreter security issue. GPT-4o produced a competent but surface-level Cycle 1 output that missed the checkpoint flaw and threading issue entirely, only acknowledging them after Gemini surfaced them. Grok demonstrated solid breadth but leaned on consensus framing rather than independent discovery, and its Cycle 1 output contained truncation artifacts suggesting incomplete analysis. Gemini's Backend Logic score of 55 — the most aggressive — proved to be the most accurate signal in the room.

---

# FINAL SECOND-PASS PRIORITY LIST

Definitive ordered list based on verified accuracy, severity, and consensus weight.

---

## P0 — CRITICAL: Fix Before Next Run

### P0-1 — Checkpoint/Resume Logic Is Non-Functional *(Gemini-discovered, consensus-verified)*
- **File:** `daily_producer.py` lines 540–553
- **Problem:** `resume_step` is read from checkpoint, logged, then ignored. The pipeline always restarts from Step 1. A crash at Step 18 of 22 costs the full run time with zero recovery.
- **Fix:**
```python
# Replace the current no-op resume block with:
STEP_ORDER = ["scan", "clip_select", "extract", "mood", "script", 
              "tts", "assemble", "preflight", "render", "postcheck",
              "shorts", "thumbnail", "upload"]

resume_idx = STEP_ORDER.index(resume_step) if resume_step in STEP_ORDER else 0

def should_run(step_name: str) -> bool:
    return STEP_ORDER.index(step_name) >= resume_idx
```
- **Then:** Gate every major pipeline stage with `if should_run("step_name"):` and write checkpoint immediately after each stage completes.

---

### P0-2 — Silent `except` Blocks Swallow All Diagnostic Signal *(Unanimous)*
- **File:** `daily_producer.py` lines ~116, ~139, ~537, ~1030, ~1306 and throughout
- **Problem:** Bare `except: pass` makes production failures completely undiagnosable. Operators see a clean exit with broken output and no log trail.
- **Fix:** Global search-and-replace policy — zero tolerance for silent suppression:
```python
# BANNED:
except:
    pass

except Exception:
    pass

# REQUIRED minimum:
except Exception:
    logger.exception("Failed during [specific context]: [relevant variables]")
    raise  # or handle explicitly with a documented reason for not re-raising
```
- **Enforce:** Add a pre-commit hook or CI lint rule: `grep -n "except.*pass" daily_producer.py` must return zero results.

---

### P0-3 — No Retry/Backoff on Any External API Call *(Unanimous)*
- **File:** `daily_producer.py` lines ~142–161 (BTC price), ~677–690 (channel scan), ~1077–1087 (ElevenLabs TTS), ~771–879 (yt-dlp extraction)
- **Problem:** Single transient network failure kills the entire pipeline. No backoff, no retry, no circuit breaker.
- **Fix:** Install `tenacity` and apply universally:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import requests

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    reraise=True
)
def _fetch_btc_price_with_retry(url: str, timeout: int = 10) -> dict:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()
```
- **Apply this decorator pattern to:** BTC price fetch, CoinGecko fallback, ElevenLabs TTS, Claude API calls, any `requests.get/post` call in the file.

---

## P1 — HIGH: Fix Within Current Sprint

### P1-1 — Zombie Thread Resource Leak in Space Tap *(Gemini-discovered, consensus-verified)*
- **File:** `daily_producer.py` lines 1012–1018
- **Problem:** `threading.Thread` with `join(timeout=120)` — if `_fetch_spaces` hangs, the thread cannot be killed. After N pipeline runs, N zombie threads accumulate.
- **Fix:** Replace with `multiprocessing.Process` which supports hard termination:
```python
import multiprocessing

result_queue = multiprocessing.Queue()

def _fetch_spaces_worker(queue):
    try:
        result = _fetch_spaces()
        queue.put(result)
    except Exception:
        logger.exception("Space Tap fetch failed in subprocess")
        queue.put(None)

st_proc = multiprocessing.Process(target=_fetch_spaces_worker, args=(result_queue,))
st_proc.start()
st_proc.join(timeout=120)

if st_proc.is_alive():
    logger.warning("Space Tap fetch exceeded 120s — terminating subprocess")
    st_proc.terminate()
    st_proc.join()
    spaces_data = None
else:
    spaces_data = result_queue.get_nowait() if not result_queue.empty() else None
```

---

### P1-2 — Inconsistent Duration Constants Create Conflicting Law Enforcement *(Gemini-discovered)*
- **File:** `daily_producer.py` lines ~244 and ~400
- **Problem:** Post-render health check enforces `480–900s` (8–15 min). Pre-flight QC enforces `420–900s` (7–15 min). A 7.5-minute video passes pre-flight and then fails post-render. The pipeline wastes a full render on content it will reject.
- **Fix:** Define a single source of truth:
```python
# constants.py or top of daily_producer.py
DURATION_MIN_SECONDS: int = 480   # 8 minutes — law-enforced minimum
DURATION_MAX_SECONDS: int = 900   # 15 minutes — law-enforced maximum

# Then reference everywhere:
if not (DURATION_MIN_SECONDS <= duration <= DURATION_MAX_SECONDS):
    raise DurationViolation(f"Duration {duration}s outside [{DURATION_MIN_SECONDS}, {DURATION_MAX_SECONDS}]")
```
- **Decision required:** Confirm with team whether 7 or 8 minutes is the actual law. Then enforce it in exactly one place.

---

### P1-3 — Unvalidated API Responses Propagate Corrupt Data Downstream *(Unanimous)*
- **File:** `daily_producer.py` lines ~145–160 (BTC price), ~677–690 (channel scan transcripts)
- **Problem:** API responses are used without schema validation. A malformed JSON or missing key causes a downstream `KeyError` or `TypeError` with no context about the original bad payload.
- **Fix:** Add explicit response validation before use:
```python
def _parse_btc_price(response_json: dict) -> float:
    try:
        price = float(response_json["bitcoin"]["usd"])
        if price <= 0:
            raise ValueError(f"Implausible BTC price: {price}")
        return price
    except (Key