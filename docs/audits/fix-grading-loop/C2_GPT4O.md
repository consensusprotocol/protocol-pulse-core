## Cycle 2 Review

### 1) What they caught that I missed

I agree I missed several important issues in Cycle 1:

- **Hardcoded local TTS path mismatch** in both `startup_checks()` and `check_tts_ready()`  
  - `overnight_render_loop.py:131, 216`  
  - This is a real deployment correctness bug.

- **Daemon scheduling contract mismatch**  
  - `overnight_render_loop.py:600-604`  
  - It runs immediately on startup, then sleeps until next 8am ET. That does not match “runs at 08:00 ET daily.”

- **Temp WAV leak in TTS artifact check**  
  - `overnight_render_loop.py:307-325`  
  - If any exception occurs before unlink, temp files accumulate.

- **Fallback grade parser brittleness**  
  - `overnight_render_loop.py:441-450`  
  - Parsing `GRADE_*|score|path|verdict` by naive `split("|")` is fragile.

- **Orphaned tmux/Claude sessions** after timeout  
  - `overnight_render_loop.py:397-403`  
  - This is a major operational risk.

- **`shell=True` + interpolated file paths** in both files  
  - This is the most serious security finding and should have been emphasized more strongly.

### 2) Where I agree / disagree

#### U1 — `shell=True` + unescaped path interpolation → command injection
**Agree.**  
This is valid and severe.

- `overnight_render_loop.py:67-70, 271, 289, 293, 299, 391-400`
- `video_pipeline_v3/gemini_grade.py:31-33, 57, 90, 101, 110, 125, 136-137`

Even if filenames are “internal,” filesystem names are still untrusted input. This is both a security and reliability problem.

#### U2 — No tmux/claude validation; timed-out sessions not killed
**Agree.**  
Both are real.

- `startup_checks()` should validate `tmux` and `claude` if `fire_cc_fix()` is part of the required path.
- `fire_cc_fix()` absolutely should kill the session on timeout.

#### U3 — Silent failure around render exit / stale artifact selection
**Agree, with one nuance.**  
The code did improve by restricting candidates to today-only output:

- `overnight_render_loop.py:253-255`

So it no longer falls back to arbitrarily old outputs. But it can still pick a **pre-existing file from earlier today**, not necessarily one produced by the current render attempt. The recommendation to require `mtime >= render_start` is correct.

#### U4 — Gemini API lacks robust error handling / retry logic
**Partially agree.**  
There is some fallback behavior:

- direct API call in `grade_with_gemini()`
- subprocess fallback to `gemini_grade.py` in `run_single_render()`

So “lacks error handling” is too strong. But it **does** lack:
- retries with backoff,
- structured handling of HTTP errors / malformed responses in `gemini_call()`,
- clear distinction between transient and permanent failures.

So the practical conclusion is still correct: resilience is insufficient.

#### Hardcoded TTS path
**Agree.**  
This is a straightforward correctness bug and likely to break non-home-directory deployments.

#### Daemon mode mismatch
**Agree.**  
This is not a crash bug, but it is a production contract bug.

#### Temp file leak
**Agree.**  
Needs `finally`.

### 3) New findings from this review

These are issues I do not see clearly called out in the Cycle 1 summaries provided.

#### N1 — `gemini_grade.py` executes substantial grading logic at import time
- `video_pipeline_v3/gemini_grade.py:35-468`

This file is written as a script, but almost all logic runs at module top level. If any other code ever imports it, it will:
- load env from a hardcoded path,
- scan outputs,
- run ffmpeg/ffprobe,
- call Gemini,
- write files,
- exit the process.

That is a major maintainability and integration hazard. It should be wrapped in `main()`.

#### N2 — `gemini_grade.py` can crash on missing `.env`
- `video_pipeline_v3/gemini_grade.py:11`

`for line in open('/home/ultron/protocol_pulse/.env'):` has no exception handling. If `.env` is absent or unreadable, the script crashes before any controlled logging. That is a correctness bug.

#### N3 — `send_telegram_alert()` uses `parse_mode="HTML"` with unescaped arbitrary message text
- `overnight_render_loop.py:205`

Current messages are mostly internal strings, but they may include values derived from logs/verdicts. With HTML parse mode enabled, `<`, `>`, `&` can alter rendering or cause API rejection. This is low-to-medium severity, but should be escaped or parse mode removed.

#### N4 — heartbeat writes are non-atomic and can leave corrupted JSON
- `overnight_render_loop.py:179-181`

If the process dies mid-write, next startup may see truncated JSON. The code tolerates `JSONDecodeError` on load, so this is survivable, but atomic write-via-temp-and-replace would be better for daemon reliability.

#### N5 — logging handlers are added unconditionally at import
- `overnight_render_loop.py:36-44`

If this module is imported more than once in tests or another runner, duplicate handlers will cause repeated log lines. Not a ship blocker, but poor hygiene.

### 4) Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---:|---:|---|
| Correctness | 5/10 | 4/10 | Additional confirmed issues: hardcoded TTS path, daemon contract mismatch, temp leak, brittle fallback parsing, import-time execution in `gemini_grade.py`, uncontrolled `.env` open. |
| Law Compliance | 7/10 | 7/10 | No meaningful change; no explicit governing laws were provided. |
| Security | 5/10 | 3/10 | After seeing the breadth of `shell=True` usage plus interpolated paths and tmux command construction, this is clearly worse than I scored initially. |
| Frontend Quality | N/A | N/A | No frontend here. |
| Overall | 5/10 | 4/10 | Combined review confirms this is not production-ready without fixes. |

### 5) Final priority list

## P0 CRITICAL

1. **Remove `shell=True` and stop interpolating untrusted paths into shell commands**
   - `overnight_render_loop.py:67-70, 271, 289, 293, 299, 391-400`
   - `video_pipeline_v3/gemini_grade.py:31-33, 57, 90, 101, 110, 125, 136-137`
   - Use argument lists with `shell=False`. This is the top security issue.

2. **Ensure current render output is actually from the current attempt**
   - `overnight_render_loop.py:245-265`
   - Record render start time and only accept output files with `mtime >= render_start`.
   - If render exits non-zero and no fresh file exists, fail that iteration and alert.

3. **Kill timed-out Claude/tmux sessions**
   - `overnight_render_loop.py:397-403`
   - On deadline expiry, explicitly `tmux kill-session -t <name>` before continuing.

## P1 HIGH

4. **Validate `tmux` and `claude` in startup checks**
   - `overnight_render_loop.py:88-149`
   - If fix loop depends on them, missing binaries should be startup failures.

5. **Fix hardcoded TTS path**
   - `overnight_render_loop.py:131, 216`
   - Replace `~/protocol_pulse/video_pipeline_v3/tts_local.py` with `os.path.join(PIPELINE, 'tts_local.py')`.

6. **Make temp WAV cleanup exception-safe**
   - `overnight_render_loop.py:305-327`
   - Use `try/finally` around `tmp_path` unlink.

7. **Harden Gemini API handling**
   - `overnight_render_loop.py:231-242`
   - Catch `HTTPError`, `URLError`, malformed JSON, missing keys; add retry/backoff for transient failures.

8. **Fix brittle fallback grade parsing**
   - `overnight_render_loop.py:441-450`
   - Parse only the expected prefix and split with a maxsplit, e.g. `split("|", 3)`.

9. **Wrap `gemini_grade.py` in `main()` and stop executing on import**
   - `video_pipeline_v3/gemini_grade.py:35-468`
   - This is a major maintainability and integration fix.

10. **Handle missing `.env` safely in `gemini_grade.py`**
   - `video_pipeline_v3/gemini_grade.py:11-16`
   - Add try/except and log a controlled error.

## P2 MEDIUM

11. **Fix daemon behavior to match documented schedule**
   - `overnight_render_loop.py:600-604`
   - Either sleep until next 8am before first run, or update docs/help text to say “runs immediately, then daily at 08:00 ET.”

12. **Atomic heartbeat writes**
   - `overnight_render_loop.py:179-181`
   - Write temp file then `os.replace()`.

13. **Escape Telegram HTML or remove parse mode**
   - `overnight_render_loop.py:205`
   - Prevent malformed alert payloads.

14. **Avoid duplicate logger handlers on import**
   - `overnight_render_loop.py:36-44`

### 6) The single highest-leverage change

**Replace all shell-string subprocess calls with argument-list subprocess calls and enforce fresh-output validation per render attempt.**

### 7) Production ready?

**No.**

### Conditions for “Yes with conditions”
Before shipping, at minimum all of these must be done:

1. Eliminate `shell=True` command construction in both files.
2. Ensure `run_render()` only returns artifacts created by the current render attempt.
3. Kill timed-out tmux sessions and validate `tmux`/`claude` at startup.
4. Fix hardcoded TTS path usage.
5. Make temp file cleanup exception-safe.
6. Harden Gemini error handling enough that transient API failures do not silently waste iterations.

If those are fixed, I’d call it **conditionally production-testable**, but I would still want:
- daemon scheduling clarified/fixed,
- `gemini_grade.py` refactored into `main()`,
- atomic heartbeat writes,
before calling it fully production-ready.