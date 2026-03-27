# CONSENSUS REPORT — FIX-GRADING-LOOP — CYCLE 1
Generated: 2026-03-22 06:44
Models: grok, gpt4o (+1 failed: gemini — 403 PERMISSION_DENIED leaked API key)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | ❌ FAILED | 4/10 | 5/10 | 4/10 |
| Law Compliance | ❌ FAILED | 6/10 | 7/10 | 6/10 |
| Security | ❌ FAILED | 3/10 | 5/10 | 3/10 |
| Frontend Quality | ❌ FAILED | N/A | N/A | N/A |
| Overall | ❌ FAILED | 4/10 | 5/10 | **4/10** |

> **Scoring note:** Gemini was unable to produce scores due to API key invalidation (leaked key — 403). GPT-4o scores derived from severity of identified bugs (5 P0-class issues). Grok scores derived from breadth of coverage. Consensus weights GPT-4o more heavily as it produced the most forensically detailed output.

---

## UNANIMOUS FINDINGS
*(Both active models flagged these — implement unconditionally)*

### U1 — `shell=True` + unescaped file path interpolation → command injection
- **File:** `overnight_render_loop.py:67-70, 271, 289, 293, 299` and `video_pipeline_v3/gemini_grade.py:57, 90, 101, 110, 125, 136-137`
- **What:** `run()` uses `shell=True` universally. Callers interpolate raw filesystem paths (e.g., `video`, `LATEST`) directly into shell command strings. Both GPT-4o and Grok independently flagged this.
- **What to change:** Replace `shell=True` with `shell=False` and pass commands as lists. Use `shlex.quote()` wherever a string form is truly required. At minimum, validate filenames contain no shell metacharacters before interpolation.

### U2 — No tmux/claude CLI validation in startup checks, orphaned sessions never killed
- **File:** `overnight_render_loop.py:392-403`
- **What:** `fire_cc_fix()` assumes `tmux` and `claude` are installed and accessible. Neither is validated in `startup_checks()`. When the 2700s deadline expires, the tmux session is **not killed** — it continues mutating the repo while the outer loop advances.
- **What to change:** (a) Add `which tmux` and `which claude` checks to `startup_checks()` with a hard exit on failure. (b) On deadline expiry, call `tmux kill-session -t <session_name>` before continuing.

### U3 — Silent failure when `run_render()` returns no video / non-zero exit
- **File:** `overnight_render_loop.py:251, 420-421`
- **What:** Render exit code is logged but not acted upon. If render fails, the loop still scans for an output file, potentially grading a stale or corrupt artifact from a prior run. Both models flagged the absence of an alert escalation path (no Telegram/PagerDuty on this specific failure).
- **What to change:** If render exit code is non-zero **and** no fresh output file is found, immediately send a Telegram alert and `continue` (skip grading for this iteration). Add a timestamp/mtime guard: only accept output files created after the render subprocess started.

### U4 — Gemini API call lacks error handling / retry logic
- **File:** `overnight_render_loop.py:231-242`
- **What:** `gemini_call()` catches nothing. No handling for HTTP errors, quota failures, empty candidates, or missing API key. Both models noted root-cause visibility is poor and behavior is inconsistent with the more robust handling in `gemini_grade.py`.
- **What to change:** Wrap `gemini_call()` with specific exception catches (`google.api_core.exceptions.ResourceExhausted`, `google.api_core.exceptions.PermissionDenied`, connection errors). Add exponential backoff with 3 retries before falling back to the subprocess grader. Log specific error type and HTTP code.

---

## MAJORITY FINDINGS
*(2 of 2 models agree — implement unless compelling reason not to)*

All findings here are also unanimous given only two active models. The following are **confirmed by both models** but are lower severity than U1-U4:

### M1 — TTS startup check uses hardcoded home-relative path instead of `PIPELINE` variable
- **File:** `overnight_render_loop.py:131, 216`
- **What:** `~/protocol_pulse/video_pipeline_v3/tts_local.py` is hardcoded rather than derived from `PIPELINE`. If the repo is deployed at a different path, startup check and runtime behavior disagree silently.
- **What to change:** Replace both occurrences with `PIPELINE / "tts_local.py"`.

### M2 — TTS temp file leaked on any exception path
- **File:** `overnight_render_loop.py:305-327`
- **What:** Temp `.wav` created during forensics TTS artifact check is only deleted on the success path. Any exception (ffmpeg failure, whisper timeout, JSON parse error) leaks the file. Long-running daemon accumulates these.
- **What to change:** Wrap in `try/finally` or use `tempfile.NamedTemporaryFile(delete=True)` as a context manager.

### M3 — PID lock file has no timeout/staleness cleanup
- **File:** `overnight_render_loop.py:543-556`
- **What:** If the process crashes without releasing the PID lock, subsequent runs fail silently until manual intervention. No lock timeout or staleness check (e.g., check if PID in lockfile is still alive).
- **What to change:** On lockfile acquisition failure, read the PID from the file and check `os.kill(pid, 0)`. If the process is dead, remove the stale lockfile and re-acquire. Log a warning when this occurs.

### M4 — Heartbeat JSON write is non-atomic
- **File:** `overnight_render_loop.py:179-181`
- **What:** Direct write to target file; if interrupted mid-write, produces truncated/invalid JSON. Startup only catches `JSONDecodeError` and silently ignores, losing all heartbeat state.
- **What to change:** Write to a `.tmp` file then `os.replace()` atomically. Add checksum or sentinel value validation on read.

### M5 — `gemini_grade.py` executes at import time — no `if __name__ == "__main__"` guard
- **File:** `video_pipeline_v3/gemini_grade.py` (entire file)
- **What:** The script runs unconditionally on import. Any future attempt to import it (e.g., for shared utilities) triggers a full execution: env load, ffmpeg calls, Gemini API call, sys.exit. Both models flagged this as a major maintainability smell.
- **What to change:** Wrap all top-level execution in `def main(): ...` and add `if __name__ == "__main__": main()`.

### M6 — `gemini_grade.py` `.env` load has no try/except — crashes before logging
- **File:** `video_pipeline_v3/gemini_grade.py:11`
- **What:** `for line in open('/home/ultron/protocol_pulse/.env'):` with no exception handling. Missing `.env` causes an unstructured traceback before any log is written. Inconsistent with `overnight_render_loop.py`'s safer env loading.
- **What to change:** Wrap in `try/except FileNotFoundError` with a structured log message and graceful exit.

### M7 — Hardcoded absolute paths in `gemini_grade.py`
- **File:** `video_pipeline_v3/gemini_grade.py:11, 19-21, 36, 163, 392`
- **What:** All paths hardcoded to `/home/ultron/protocol_pulse/...`. Both models flagged this as non-portable and fragile.
- **What to change:** Derive all paths from `pathlib.Path(__file__).resolve().parent` or a single `BASE_DIR` constant at the top of the file.

---

## UNIQUE INSIGHTS
*(Only 1 model caught these — evaluate carefully)*

### UI1 — Daemon scheduling contract mismatch: runs immediately on startup, not only at 08:00 ET
- **Source:** GPT-4o only
- **File:** `overnight_render_loop.py:600-604`
- **What:** `--daemon` mode runs a cycle immediately on process start, then sleeps until next 8am ET. Docstring and spec say "runs at 08:00 ET daily." On a deploy/restart at 14:00 ET, an extra unscheduled cycle runs. This could produce a duplicate episode or corrupt the daily scheduling contract.
- **Assessment: IMPLEMENT.** This is a real behavioral gap. Fix: check current time on startup; if not within an acceptable window of 08:00 ET (e.g., ±15 minutes), sleep first, then run. Or document the "run-immediately-then-daily" contract explicitly and update all operator documentation to match.

### UI2 — Fallback grading parser is brittle — assumes fixed token positions
- **Source:** GPT-4o only
- **File:** `overnight_render_loop.py:445-450`
- **What:** `parts[1]` assumed to be int, `parts[3]` assumed to exist if `len > 3`, and `grade_letter = parts[0].split("_")[1]` only works if format is exactly `GRADE_A_PASS`. Any change to the subprocess output format silently truncates or misparses the verdict.
- **Assessment: IMPLEMENT.** Add explicit format validation: assert expected token count, wrap int conversion in try/except with a fallback to Grade F, and log the raw output on any parse failure.

### UI3 — Output file selection logic is inconsistent between `run_render()` and `gemini_grade.py`
- **Source:** GPT-4o only
- **File:** `overnight_render_loop.py:255-259` vs `video_pipeline_v3/gemini_grade.py:39-47`
- **What:** `run_render()` scans only `output/YYYY-MM-DD/*.mp4` with specific exclusion patterns. `gemini_grade.py` recursively scans all output dirs for `pulse_check` files. These two scripts can disagree on what "the latest output" means, meaning the grader may grade a different file than the one the render loop thinks was produced.
- **Assessment: IMPLEMENT.** Canonicalize output file selection into a single shared utility function used by both scripts. The render loop should pass the explicit output path to the grader rather than having the grader rediscover it independently.

### UI4 — Duplicate logger handler attachment on multiple imports
- **Source:** GPT-4o only
- **File:** `overnight_render_loop.py:36-44`
- **What:** Module-level logger setup unconditionally adds handlers. Multiple imports cause duplicate log lines.
- **Assessment: SKIP for now.** This is a script, not a library. Risk of multiple imports in production is negligible. However, add `if not logger.handlers:` guard as a low-effort defensive measure during P2 cleanup.

### UI5 — DST edge cases and system clock changes not handled in `sleep_until_next_8am_et()`
- **Source:** Grok only
- **File:** `overnight_render_loop.py:527-537`
- **What:** No handling for DST transitions (clock springs forward/back) or NTP corrections. Could cause the daemon to fire 1 hour early/late on DST transition days.
- **Assessment: INVESTIGATE FURTHER.** The `pytz`/`zoneinfo` approach with `datetime.now(tz)` should handle DST correctly if implemented properly. Audit whether the sleep calculation uses naive or aware datetimes. If using aware datetimes throughout, this may already be handled. Add a log line showing the computed wake time for operator verification.

### UI6 — Telegram alert rate limiting absent on consecutive failures
- **Source:** Grok only
- **File:** `overnight_render_loop.py:203-211`
- **What:** Telegram alerts are sent on every consecutive failure without rate limiting, risking API abuse or notification flood if failures cascade.
- **Assessment: IMPLEMENT at P2.** Add a simple cooldown: track `last_telegram_alert_time` and enforce a minimum interval (e.g., 5 minutes) between identical alert types.

### UI7 — No validation of file integrity (zero-byte / corrupt) before forensics
- **Source:** Grok only
- **File:** `overnight_render_loop.py:420`
- **What:** Only checks `if not video` (i.e., path is falsy). Doesn't validate file size > 0 or that ffprobe can open it before committing to a full forensics pass.
- **Assessment: IMPLEMENT.** Add `os.path.getsize(video) > MIN_FILE_SIZE_BYTES` check and a quick `ffprobe -v error -show_entries format=duration` sanity probe before invoking full forensics. Log and skip on failure.

---

## CONFLICTS
*(Models gave contradictory recommendations)*

### C1 — Severity of `shell=True` risk
- **Grok** characterized the shell injection risk as "low" because "inputs are controlled internally."
- **GPT-4o** characterized it as a genuine security concern requiring remediation.
- **Tiebreaker: GPT-4o is correct.** Filesystem-derived filenames are not user-controlled, but they are not fully controlled either. A compromised upstream process, a malicious file dropped into the output directory, or a symlink attack could craft a filename that breaks out of the shell command. Defense in depth requires sanitization regardless of the assumed input source. Additionally, `shell=True` with `capture_output=True` and `2>&1` in the command string produces the fragile behavior GPT-4o identified. The fix is low-cost and high-value.

### C2 — ElevenLabs quota fallback necessity
- **Grok** flagged the absence of a secondary TTS provider fallback as a potential compliance violation for reliability expectations.
- **GPT-4o** did not flag this as a compliance issue, treating it as a correctness/resilience gap only.
- **Tiebreaker: GPT-4o's framing is more accurate.** There is no evidence in the spec that a secondary TTS provider is required. The existing quota check (`Lines 133-148`) is a reasonable safeguard. This is a resilience enhancement, not a compliance violation. Downgrade to P2 enhancement.

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change in second pass)*

1. **Singleton PID lock pattern** (`overnight_render_loop.py:543-555`): Correctly prevents duplicate instances. The implementation is sound; only the staleness cleanup (M3) needs addition.

2. **Startup checks structure** (`overnight_render_loop.py:88-149`): The concept and ordering of checks (FFmpeg → pipeline dir → output dir → TTS) is well-designed. Only the hardcoded path bug (M1) needs fixing; the overall structure is correct.

3. **8-iteration / 6-hour loop bounds** (`overnight_render_loop.py:406-489`): The ceiling on iterations and wall-clock time is the right safety design. Do not change the bounds.

4. **Gemini subprocess fallback pattern** (`overnight_render_loop.py:433-454`): Having a subprocess fallback grader when the direct API call fails is architecturally sound. The fallback itself needs hardening (UI2), but the pattern is correct.

5. **Telegram alerting integration** (`overnight_render_loop.py:198-211`): The existence and placement of Telegram alerts is good operational practice. Only add rate limiting (UI6) — do not remove or restructure.

6. **2-attempt / 30-minute retry in `run_cycle()`** (`overnight_render_loop.py:492-524`): Sound resilience design. Do not change the retry count or wait interval.

7. **ElevenLabs quota pre-check** (`overnight_render_loop.py:133-148`): Checking quota before starting a full render cycle is correct fail-fast behavior. Keep as-is.

---

## LAW COMPLIANCE CONSENSUS

| Requirement | Status | Notes |
|---|---|---|
| Python 3.12 | ✅ COMPLIANT | Shebang and syntax consistent |
| Ubuntu 24.04 / Ultron server | ✅ COMPLIANT | Paths consistent; no OS-specific issues beyond hardcoded home dir |
| CSS/SVG animations only | ✅ N/A | No frontend code in reviewed files |
| External services (ElevenLabs, HeyGen, Wav2Lip) | ⚠️ PARTIAL | ElevenLabs quota checked; HeyGen/Wav2Lip failure handling absent |
| ~1000 concurrent users | ✅ N/A | Backend render loop; singleton ensures no concurrency conflicts |
| DB query indexing | ✅ N/A | No DB queries in reviewed code |
| No hardcoded secrets | ⚠️ PARTIAL | Keys loaded from `.env` correctly, but `.env` load in `gemini_grade.py` is fragile and pre-logging |
| Portability / deployment path independence | ❌ VIOLATED | `gemini_grade.py` has 7+ hardcoded absolute paths; `overnight_render_loop.py` has 2 hardcoded TTS paths |

**Final determination:** Two violations requiring remediation — hardcoded path portability (M7, M1) and missing `gemini_grade.py` import guard (M5). All other laws are compliant or not applicable to this code surface.

---

## SECURITY CONSENSUS

Priority order (both models contributing):

| Rank | Issue | Severity | File | Models |
|---|---|---|---|---|
| 1 | Command injection via unescaped file paths with `shell=True` | **CRITICAL** | `overnight_render_loop.py:67-70, 271-299` + `gemini_grade.py:57-137` | Both |
| 2 | Orphaned tmux/Claude sessions executing arbitrary code without sandboxing | **HIGH** | `overnight_render_loop.py:392-403` | Both |
| 3 | Gemini API key handling — no guard against key appearing in logs/error messages | **MEDIUM** | `overnight_render_loop.py:198-199`, `gemini_grade.py:11` | Both |
| 4 | Telegram bot token/chat ID potentially exposed in unfiltered log error messages | **MEDIUM** | `overnight_render_loop.py:198-199` | Grok |
| 5 | No rate limiting on Telegram alerts — potential API abuse vector | **LOW** | `overnight_render_loop.py:203-211` | Grok |

**Top security action:** Fix `shell=True` + path interpolation across both files (maps to U1 in action plan). This is the only exploitable vulnerability; all others are operational security concerns.

---

## WORLD-CLASS GAP CONSENSUS
*(Items mentioned by 2+ models as missing from a truly world-class product)*

1. **No structured observability / alerting on render failures beyond logging** — Both models noted that silent failures (no video, API down, parse error) result in log entries only, with no escalation. A world-class pipeline would have: (a) a Telegram/PagerDuty alert on every P0 failure path, (b) a structured JSON event log parseable by a monitoring dashboard, and (c) a heartbeat watchdog that fires an alert if no successful render occurs within 25 hours.

2. **No canonical "latest output" contract shared between render loop and grader** — Both models identified that `run_render()` and `gemini_grade.py` discover "the latest video" independently with different logic. A world-class system would pass the explicit output path through the entire pipeline as a typed artifact identifier, eliminating all file-rediscovery races.

3. **No integration/smoke test for the grading loop itself** — Both models implicitly noted the absence of tests (the `regression_test.sh` reference in the second-pass prompt implies tests exist, but no test coverage of the grading loop's correctness was evidenced). A world-class pipeline would have a fixture-based test that runs the loop against a known video and asserts the expected grade output, covering all fallback paths.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0-1 | Replace `shell=True` with `shell=False` + list args throughout; use `shlex.quote()` where string form required; validate filenames before interpolation | `overnight_render_loop.py:67-70, 271, 289, 293, 299` + `gemini_grade.py:57, 90, 101, 110, 125, 136-137` | Both | Command injection vector; also fixes fragile stderr capture behavior |
| P0-2 | Add tmux + claude CLI validation to `startup_checks()`; kill orphaned tmux session on deadline expiry in `fire_cc_fix()` | `overnight_render_loop.py:89-149, 397-403` | Both | Silent failure + resource leak + arbitrary code execution risk |
| P0-3 | Guard `run_single_render()` against non-zero render exit + stale output file; add mtime guard and Telegram alert on render failure | `overnight_render_loop.py:251, 420-421` | Both | Can grade wrong/corrupt artifact; silent failure in cron |
| P0-4 | Add specific exception handling + exponential backoff (3 retries) to `gemini_call()` | `overnight_render_loop.py:231-242` | Both | Any API error causes silent loop degradation; inconsistent with grader behavior |

### P1 HIGH

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P1-1 | Wrap `gemini_grade.py` execution in `def main()` + `if __name__ == "__main__"` guard | `gemini_grade.py` (entire file) | Both | Import-time execution is a critical maintainability and correctness defect |
| P1-2 | Replace hardcoded `.env` open with try/except; add structured log before crash | `gemini_grade.py:11` | Both | Crashes before logging; inconsistent failure mode |
| P1-3 | Replace all hardcoded `/home/ultron/protocol_pulse/...` paths with `BASE_DIR` derived from `__file__` | `gemini_grade.py:11, 19-21, 36, 163, 392` | Both | Non-portable; breaks on any non-default deployment |
| P1-4 | Fix TTS path references to use `PIPELINE` variable | `overnight_render_loop.py:131, 216` | Both | Startup check and runtime can silently disagree |
| P1-5 | Wrap temp wav creation in `try/finally` with guaranteed cleanup | `overnight_render_loop.py:305-327` | Both | Long-running daemon accumulates leaked temp files |
| P1-6 | Add stale PID cleanup logic to `_acquire_singleton()` | `overnight_render_loop.py:543-556` | Both | Dead-process lockfile requires manual operator intervention |
| P1-7 | Fix daemon scheduling — check current time on startup; sleep first if not within 08:00 ET window | `overnight_render_loop.py:600-604` | GPT-4o unique | Extra cycle on deploy breaks daily scheduling contract |
| P1-8 | Canonicalize output file selection into shared utility; pass explicit path from render to grader | `overnight_render_loop.py:255-259` + `gemini_grade.py:39-47` | GPT-4o unique | Two scripts can grade different files; race condition on output discovery |
| P1-9 | Add format validation to fallback grading parser; wrap int conversion; log raw output on parse failure | `overnight_render_loop.py:445-450` | GPT-4o unique | Silent grade misparse on any format change |
| P