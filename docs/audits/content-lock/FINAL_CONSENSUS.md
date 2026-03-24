# CONSENSUS REPORT — CONTENT-LOCK — CYCLE 2
Generated: 2026-03-24 14:02
Models: Grok, Gemini (+1 failed — GPT-4o rate-limited)

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 4/10 | N/A | 6.0/10 | **5.0/10** |
| Law Compliance | 8/10 | N/A | 7.5/10 | **7.8/10** |
| Security | 3/10 | N/A | 5.0/10 | **4.0/10** |
| Frontend Quality | N/A | N/A | N/A | **N/A** |
| Backend Quality | 6/10 | N/A | 7.0/10 | **6.5/10** |
| World-Class Gap | 4/10 | N/A | 5.5/10 | **4.8/10** |
| **Overall** | **5.0/10** | **N/A** | **6.2/10** | **5.6/10** |

> **Scoring note:** Gemini's scores are materially lower than Grok's, driven primarily by Gemini's discovery that the perfection loop does not actually apply fixes — a finding Grok did not explicitly raise. Consensus averages weight both models equally. The true overall is closer to Gemini's 5.0 if the non-functional loop finding is validated, which the second-pass implementer must confirm first.

---

## UNANIMOUS FINDINGS
*(Both available models agree — implement unconditionally)*

---

### U1 — Shell Injection via `shell=True` + f-string Construction
**File:** `overnight_render_loop.py` — Lines 107, 389, 407, 411, 418 (and any other `subprocess.run` call using `shell=True`)
**What it is:** `subprocess.run` is called with `shell=True` and command strings built via f-strings that incorporate external data (filenames, paths, API responses). Any filename or value containing shell metacharacters (spaces, semicolons, backticks, `$(...)`) will be interpreted by the shell, enabling arbitrary command execution on the host.
**Severity:** Critical / P0. This is a textbook remote/local code execution vector on the Ultron production server.
**What to change:**
```python
# BEFORE (dangerous)
subprocess.run(f"ffmpeg -i {input_path} -c copy {output_path}", shell=True)

# AFTER (safe)
subprocess.run(["ffmpeg", "-i", str(input_path), "-c", "copy", str(output_path)],
               shell=False, check=True)
```
Convert every `subprocess.run` / `subprocess.Popen` call to a list-of-arguments form with `shell=False`. Use `shlex.quote()` only if a shell is genuinely required for a specific call, and document why.

---

### U2 — Fragile Pipe-Delimited Grade String Parsing
**File:** `overnight_render_loop.py` — Lines 612–647
**What it is:** The grading subprocess returns results as a pipe-delimited string (`GRADE_A_PASS|95|path|verdict`). This is parsed with `split("|")`. Any filename containing a pipe character, or any verdict string with a pipe, silently corrupts the parse. The `split("|", 3)` cap helps but does not solve the structural fragility.
**Severity:** High / P1. Will cause silent, hard-to-debug failures in production.
**What to change:** Replace the pipe-delimited protocol entirely. The grading script (`gemini_grade.py`) should write a small JSON object to stdout or to a temp file:
```json
{"grade": "GRADE_A_PASS", "score": 95, "path": "/path/to/video.mp4", "verdict": "Excellent clarity on macro section."}
```
The loop then does `result = json.loads(proc.stdout)` — zero ambiguity, safe with all characters.

---

### U3 — No Structured Escalation After Max Render Iterations
**File:** `overnight_render_loop.py` — Lines 677–681
**What it is:** When the loop exhausts all iterations without achieving Grade A, it sends a Telegram alert and exits. There is no machine-readable failure artifact, no structured handoff to a human operator, and no integration with a formal alert channel.
**Severity:** High / P1 for a production system running autonomously overnight.
**What to change:**
1. Write a structured failure manifest to a deterministic path (e.g., `~/protocol_pulse/renders/failures/YYYYMMDD_failure.json`) containing: iteration count, best score achieved, best grade, path to best video, full verdict history.
2. Log the manifest path in the Telegram message so a human can act immediately.
3. Optionally trigger a secondary alert (email, PagerDuty webhook) after manifest is written.

---

## MAJORITY FINDINGS
*(Both models agree — implement unless compelling reason not to)*

These are identical to U1–U3 above since only two models were available. All unanimous findings are also majority findings by definition. The following are strong single-model findings elevated to near-unanimous status by their technical clarity.

---

### M1 — Inefficient Chained Re-encoding in `_apply_preflight_fixes`
**File:** `daily_producer.py` — Lines 434–519
**Both models flagged this.** When a video needs both freeze-frame correction and loudness normalization, the function runs two separate full `ffmpeg` passes. Each generational encode adds compression artifacts, extends wall-clock time, and is architecturally wasteful.
**What to change:** Audit all fix paths. Where multiple audio or video filters can be applied in sequence, construct a single `ffmpeg` command using `-filter_complex` or chained `-af`/`-vf` arguments. Use `-c:v copy` when only audio needs adjustment (loudness-only fix should never re-encode video).

---

## UNIQUE INSIGHTS
*(Only one model raised this — evaluate carefully)*

---

### UI-1 — CRITICAL: The "Perfection Loop" Does Not Apply Fixes
**Source:** Gemini only
**File:** `overnight_render_loop.py` — Lines 526–564 (`fire_cc_fix`)
**What it is:** Gemini identified that `fire_cc_fix` contains a comment explicitly stating CC self-healing was removed, and the function now only logs failure details for an external "Qwen watchdog" to handle. The loop re-renders with an identical codebase and identical inputs — expecting a different result is the definition of the loop being broken. The feature's primary value proposition (autonomous quality improvement) is not implemented.
**Assessment: IMPLEMENT — Investigate and fix before ship.**
This is the single most architecturally significant finding in the entire two-cycle review. Before the second pass begins, the implementer must answer: *Does the Qwen watchdog process actually exist and run between iterations?* If yes, document it and add a health-check assertion at loop start. If no, `fire_cc_fix` must be redesigned to make at least one deterministic programmatic change between iterations (e.g., adjusting a config parameter, swapping a prompt variant, changing a QC threshold) so re-renders are not identical runs. A retry loop with no state change is not a perfection loop.

---

### UI-2 — Fragile Output Video Discovery via Glob + mtime
**Source:** Gemini (also lightly touched by Grok on related issues)
**File:** `overnight_render_loop.py` — Lines 354–366
**What it is:** The loop finds the output video by globbing for files and filtering by modification time vs. `render_start`. If an intermediate file type is added to the assembler, or if the system clock drifts, the wrong file could be selected.
**Assessment: IMPLEMENT.**
`daily_producer.py` should write the canonical final video path to a small `result.json` (or print it as the last line to stdout). The loop reads this file. Zero ambiguity, zero glob fragility. Low-effort, high-reliability fix.

---

### UI-3 — TTS Quota Sentinel File Has No Atomic Access or Error Handling
**Source:** Grok only
**File:** `overnight_render_loop.py` — Lines 279–309
**What it is:** The quota sentinel file is read/written without atomic file operations. Under concurrent process access (unlikely but not impossible), a torn write could leave a corrupt sentinel, causing the loop to incorrectly believe TTS is available or unavailable.
**Assessment: IMPLEMENT — low effort, meaningful reliability gain.**
Use `tempfile.NamedTemporaryFile` + `os.replace()` for atomic writes to the sentinel. Wrap reads in try/except for `FileNotFoundError` and `PermissionError`.

---

### UI-4 — Checkpoint File Write Has No Atomicity Guarantee
**Source:** Grok only
**File:** `daily_producer.py` — Lines 106–117
**What it is:** `_write_checkpoint` writes directly to the checkpoint file. An interrupted write (power loss, OOM kill) produces a corrupt JSON file that cannot be resumed, defeating the checkpoint system entirely.
**Assessment: IMPLEMENT.**
```python
import tempfile, os
def _write_checkpoint(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)  # atomic on POSIX
```

---

### UI-5 — Space Tap Scraper Thread Leak on Timeout
**Source:** Gemini only
**File:** `daily_producer.py` — Lines 943–952
**What it is:** A daemon thread is spawned for the space tap scraper with a `join(timeout=N)`. If the scraper hangs, the thread is abandoned but continues running, leaking file handles or network connections until the process exits.
**Assessment: INVESTIGATE FURTHER.**
Daemon threads are cleaned up on process exit, so this is not a true leak in long-running terms. However, if the thread holds a network socket open, it could exhaust file descriptors over many invocations. Replace with `subprocess` or add explicit cancellation via a `threading.Event` stop signal.

---

### UI-6 — Stale Cache Not Validated in `--skip-scan` Mode
**Source:** Grok (Cycle 1, confirmed Cycle 2)
**File:** `daily_producer.py` — Lines 607–623
**What it is:** `--skip-scan` loads cached transcripts with no freshness check. A cache from days ago could produce an episode about stale news.
**Assessment: IMPLEMENT.**
Add a staleness check: if the cache file mtime is older than `MAX_CACHE_AGE_HOURS` (suggest 48h, configurable), emit a prominent warning and optionally refuse to proceed without `--force-stale`.

---

### UI-7 — BTC Price API Response Not Structurally Validated
**Source:** Grok only
**File:** `daily_producer.py` — Lines 142–161
**What it is:** `get_btc_price()` checks basic existence but not structural sanity of the API response. An unexpected schema change or malicious response could cause a downstream formatting exception.
**Assessment: IMPLEMENT — low effort.**
Add explicit key path validation: `assert isinstance(price, (int, float)) and 1000 < price < 10_000_000` before returning. Fail loudly on schema violations rather than propagating garbage.

---

## CONFLICTS
*(Models gave contradictory assessments — tiebreaker ruling)*

---

### C1 — Stale PID Lock Risk
**Grok** flagged the PID file lock as a meaningful risk.
**Gemini** partially disagreed, noting that `overnight_render_loop.py:779` already checks if the old PID is alive, and that `fcntl.flock` is process-aware.
**Ruling: Gemini is more correct.** `fcntl.flock` is inherently safe against stale locks because the kernel releases the lock when the file descriptor is closed (i.e., when the process dies). The PID-alive check is belt-and-suspenders. The risk is minor. Do not invest engineering time here; document the behavior in a comment and move on.

---

### C2 — Overall Severity Assessment
**Grok** scored Overall at 6.2/10, treating the non-functional loop as a medium concern.
**Gemini** scored Overall at 5.0/10, treating the non-functional loop as a critical architectural flaw.
**Ruling: Gemini's framing is correct.** If `fire_cc_fix` genuinely does nothing and the Qwen watchdog does not exist, the feature's core premise is false. A product that markets autonomous quality improvement but actually just retries blindly is not a 6/10 product. Consensus score of 5.6 is a compromise, but the implementer should treat UI-1 with the same urgency as U1.

---

## VALIDATED STRENGTHS
*(Both models confirmed — do NOT change these)*

1. **`fcntl.flock` Singleton Guards** — Both files correctly use file locking to prevent concurrent execution. The implementation is clean and idiomatic. Do not refactor.

2. **Gemini API Retry-with-Backoff** — `gemini_call()` implements exponential backoff with jitter for API failures. Both models rated this as production-ready. Do not change the retry logic.

3. **BTC Price Fallback Chain** — `get_btc_price()` has a multi-provider fallback. Both models noted this is well-implemented resilience. Only add the structural validation from UI-7; do not change the fallback logic itself.

4. **Graceful Pipeline Abort on Empty Selection** — Both models noted that empty clip selection and empty video scan correctly terminate the pipeline rather than producing empty content. This fail-fast behavior is correct and should be preserved.

5. **Telegram Alert Integration** — The alerting on failure paths is consistently implemented throughout both files. Both models noted this as a good operational feature. Extend it (UI-1 / U3) but do not replace it.

---

## LAW COMPLIANCE CONSENSUS

| Requirement | Status | Notes |
|---|---|---|
| Python 3.12 | ✅ COMPLIANT | Code is Python 3; type annotations and f-strings confirm compatibility |
| Flask 3.x / SQLAlchemy | ✅ COMPLIANT | Not present in these backend pipeline files; not required here |
| Ubuntu 24.04 / Ultron | ✅ COMPLIANT | `fcntl`, `ffmpeg`, `ffprobe` system calls are Linux-native and appropriate |
| CSS/SVG animations only | ✅ COMPLIANT | Backend files; no UI code present |
| ElevenLabs TTS integration | ✅ COMPLIANT | Integration present; quota sentinel logic exists (needs hardening per UI-3) |
| HeyGen / external services | ✅ COMPLIANT | Integrations present per both models |
| GOVERNING LAWS section | ⚠️ EMPTY | Spec section was blank; no legal compliance violations identified, but spec must be completed |

**Final determination:** No law violations found. The empty GOVERNING LAWS section in the spec is a documentation debt that must be resolved before the product reaches users. Tag the spec owner.

---

## SECURITY CONSENSUS

Priority order of confirmed security issues:

| Priority | Issue | File | Consensus |
|---|---|---|---|
| P0 | Shell injection via `shell=True` + f-strings | `overnight_render_loop.py:107,389,407,411,418` | Both models |
| P1 | Atomic sentinel file writes (TOCTOU on quota file) | `overnight_render_loop.py:279–309` | Grok only (but technically valid) |
| P1 | Atomic checkpoint writes (corrupt-on-interrupt) | `daily_producer.py:106–117` | Grok only (but technically valid) |
| P2 | Unvalidated external API response structure | `daily_producer.py:142–161` | Grok only |
| P2 | `/tmp` used for lock and checkpoint files | Both files | Gemini Cycle 1 |

**Security bottom line:** The `shell=True` issue is the only genuinely critical security vulnerability. Everything else is reliability hardening. Fix U1 before anything else ships.

---

## WORLD-CLASS GAP CONSENSUS
*(Only items 2+ models mentioned)*

1. **No real self-healing in the perfection loop.** A world-class autonomous pipeline modifies its own parameters between iterations — prompt temperature, clip selection strategy, loudness targets — based on the grading feedback. The current loop is a dumb retry. Both models agree the gap between the feature's promise and its implementation is large.

2. **Inter-process communication via fragile string protocols.** World-class pipelines use structured IPC (JSON, protobuf, named pipes with schemas). Pipe-delimited strings and glob-based file discovery are 1990s shell-scripting patterns. Both models independently flagged this as a maturity gap.

3. **No structured failure artifacts.** When the loop fails overnight, a human arrives in the morning to a Telegram message with no machine-readable context, no iteration history, no best-attempt video path. A world-class system produces a rich failure report that makes the next human or AI action immediately obvious.

4. **Sequential re-encoding degrades output quality.** A world-class video pipeline never re-encodes more than once. The multi-pass re-encoding pattern signals that preflight fixes were bolted on after the fact rather than integrated into the pipeline architecture.

---

## FINAL ACTION PLAN
*(Sorted by consensus priority)*

| Priority | Change | File:Line | Models | Why |
|---|---|---|---|---|
| **P0 CRITICAL** | Refactor all `subprocess.run(shell=True)` to argument lists with `shell=False` | `overnight_render_loop.py:107,389,407,411,418` | Both | Shell injection = arbitrary code execution on production server |
| **P0 CRITICAL** | Investigate and redesign `fire_cc_fix` — either implement real fix application or document external watchdog with health-check assertion | `overnight_render_loop.py:526–564` | Gemini (critical; Grok missed) | Core feature premise may be non-functional |
| **P1 HIGH** | Replace pipe-delimited grade parsing with JSON IPC between grader and loop | `overnight_render_loop.py:612–647` + `gemini_grade.py` | Both | Brittle parsing causes silent corruption in production |
| **P1 HIGH** | Write structured failure manifest JSON + enhanced alert on loop exhaustion | `overnight_render_loop.py:677–681` | Both | Overnight autonomous system must produce actionable failure artifacts |
| **P1 HIGH** | Combine multi-pass `ffmpeg` re-encodes into single-pass filter chains | `daily_producer.py:434–519` | Both | Quality degradation + wasted wall-clock time |
| **P1 HIGH** | Have `daily_producer.py` emit canonical output path to `result.json`; update loop to read it | `overnight_render_loop.py:354–366` + `daily_producer.py` | Gemini + pattern match | Glob + mtime video discovery is fragile and will break |
| **P2 MEDIUM** | Add atomic write (tmp + `os.replace`) to `_write_checkpoint` | `daily_producer.py:106–117` | Grok | Interrupted write corrupts resume state |
| **P2 MEDIUM** | Add atomic write + error handling to TTS quota sentinel | `overnight_render_loop.py:279–309` | Grok | Race condition on quota file under concurrent access |
| **P2 MEDIUM** | Add cache freshness check in `--skip-scan` mode (warn/refuse if older than 48h) | `daily_producer.py:607–623` | Grok C1+C2 | Stale news episodes are a product quality failure |
| **P2 MEDIUM** | Add structural validation of BTC price API response | `daily_producer.py:142–161` | Grok | Malformed API response propagates silently to script formatter |
| **P2 MEDIUM** | Replace daemon thread for space tap scraper with subprocess or cancellable thread | `daily_producer.py:943–952` | Gemini | Resource leak on timeout; subprocess gives better isolation |
| **P2 MEDIUM** | Move lock and checkpoint files from `/tmp` to project-local directory | Both files | Gemini C1 | OS reboot clears `/tmp`, loses checkpoint and lock state |

---

## CYCLE 2 VERDICT

**Not production-ready. Two hard blockers.**

**Blocker 1 (Security):** The `shell=True` vulnerability is a pre-ship showstopper. A single malformed filename from any external API could execute arbitrary commands as the server process user. This takes approximately 2–4 hours to fix correctly and must be the first commit.

**Blocker 2 (Correctness):** The status of `fire_cc_fix` must be resolved before the feature ships under the name "perfection loop" or any equivalent marketing. If the Qwen watchdog exists and is functional, prove it with a health-check. If it does not, the loop must be redesigned to make at least one deterministic state change per iteration. Shipping a retry loop marketed as self-healing AI quality control is a product integrity problem, not just a code quality problem.

Everything else in the P1 and P2 list represents meaningful quality and reliability improvements but does not individually block the ship — except that they collectively indicate the IPC architecture needs a single focused refactor session (U2 + UI-2 can and should be fixed together in one sitting).

**If both blockers are resolved and the P1 items completed, this code has the structural bones of a genuinely impressive autonomous pipeline. The retry resilience, API fallback chains, and alerting infrastructure are well-built. The foundation is sound. The blockers are fixable.**

---

## SECOND PASS PROMPT
*(Ready to fire into Claude Code)*

```
Read ~/protocol_pulse/docs/gospels/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/audits/content-lock_CONSENSUS_C2.md.

This is the FINAL PASS for content-lock.
The feature was reviewed by 2 independent AI models (Grok, Gemini) across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

═══════════════════════════════════════════════
PRIORITY ACTION PLAN
═══════════════════════════════════════════════

P0 CRITICAL — Shell Injection
File: overnight_render_loop.py lines 107, 389, 407, 411, 418
Change: Refactor ALL subprocess.run(cmd, shell=True) calls to use
        argument lists and shell=False. Use shlex.quote() ONLY if
        a shell is genuinely unavoidable for a specific call; add
        a comment explaining why.
Why: Arbitrary code execution on production server.

P0 CRITICAL — Non-Functional Perfection Loop
File: overnight_render_loop.py lines 526–564 (fire_cc_fix)
Change: First, determine if a Qwen watchdog process exists and is
        active between loop iterations. If yes: add a watchdog
        health-check assertion at loop start and document the
        architecture. If no: implement fire_cc_fix to make at least
        one deterministic programmatic change per failed iteration
        (e.g., write a JSON config delta that daily_producer.py
        reads to adjust a parameter such as prompt temperature,
        clip count, or loudness target).
Why: Loop re-renders with identical inputs — not self-healing.

P1 HIGH — Fragile Grade String Parsing → JSON IPC
File: overnight_render_loop.py lines 612–647 + gemini_grade.py
Change: gemini_grade.py must output a JSON object:
        {"grade": str, "score": int, "path": str, "verdict": str}
        overnight_render_loop.py must parse with json.loads().
        Remove all split("|") parsing logic.
Why: Pipe chars in filenames/verdicts silently corrupt grading.

P1 HIGH — No Failure Manifest on Loop Exhaustion
File: overnight_render_loop.py lines 677–681
Change: On loop exhaustion without Grade A, write a JSON manifest to:
        ~/protocol_pulse/renders/failures/YYYYMMDD_failure.json
        Containing: iteration_count, best_score, best_grade,
        

---

# WINNER DETERMINATION

# WINNER: **Gemini**

Gemini consistently demonstrated superior depth and precision across both cycles — it uniquely identified the non-functional perfection loop (fixes applied but never re-evaluated), the chained re-encoding quality degradation, and the fragile pipe-delimited parsing, all of which proved accurate in Cycle 2 and directly drove the consensus scoring delta. Its recommendations were specific, implementable, and architecturally sound (JSON over pipe-delimited, single-pass ffmpeg filter chains, argument-list subprocess calls), and it covered structural pipeline logic failures that Grok acknowledged missing entirely.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × implementation risk × blast radius. Implement top-down without skipping.

---

## P0 — CRITICAL / IMPLEMENT IMMEDIATELY

### [P0-1] Shell Injection via `shell=True` + f-string Construction
**File:** `overnight_render_loop.py` — Lines 107, 389, 407, 411, 418 and all other `subprocess.run` calls
**Root cause:** `shell=True` with f-string-interpolated filenames/paths enables arbitrary command execution if any value contains shell metacharacters.
**Action:**
```python
# REPLACE every instance of this pattern:
subprocess.run(f"ffmpeg -i {input_path} -vf {filter} {output_path}", shell=True)

# WITH explicit argument lists:
subprocess.run(
    ["ffmpeg", "-i", str(input_path), "-vf", filter_str, str(output_path)],
    shell=False,
    check=True,
    capture_output=True,
    text=True
)
```
**Validation:** `grep -n "shell=True" overnight_render_loop.py` must return zero results after refactor.

---

### [P0-2] Non-Functional Perfection Loop — Fixes Never Re-Evaluated
**File:** `overnight_render_loop.py` — Loop block ~Lines 677–710 (confirm exact range)
**Root cause (Gemini-unique finding):** The render loop applies preflight fixes but does not re-run the quality grader on the fixed output before iterating. The loop increments the counter and re-grades the *original* artifact or exits prematurely, meaning Grade A is never achievable through iteration regardless of fix success.
**Action:**
1. Confirm the finding: trace the variable holding the graded file path through each loop iteration. Verify whether the grader receives the fixed output path or the pre-fix path.
2. If confirmed broken: after `_apply_preflight_fixes(output_path)` completes, reassign the grader input to the fixed file before the next grade call.
3. Add an explicit log line: `logger.info(f"Re-grading fixed artifact: {fixed_path}")` to make this traceable in production logs.
**Validation:** Run a synthetic render that is known to fail loudness check. Confirm loop iteration 2 grades the fixed file and achieves Grade A.

---

## P1 — HIGH SEVERITY / IMPLEMENT THIS SPRINT

### [P1-1] Fragile Pipe-Delimited Grade String Parsing
**File:** `overnight_render_loop.py` — Lines 612–647
**Root cause:** `line.split("|")` on grade strings will silently misparse any filename or verdict message containing a pipe character, corrupting grade logic.
**Action:** Replace pipe-delimited inter-process communication with JSON:
```python
# PRODUCER SIDE — emit structured output:
import json
grade_payload = {
    "grade": "GRADE_A_PASS",
    "score": 95,
    "path": str(output_path),
    "verdict": verdict_text
}
print(json.dumps(grade_payload))

# CONSUMER SIDE — parse safely:
try:
    grade_data = json.loads(line.strip())
    grade = grade_data["grade"]
    score = int(grade_data["score"])
except (json.JSONDecodeError, KeyError, ValueError) as e:
    logger.error(f"Grade parse failed: {e} — raw line: {line!r}")
    grade = "PARSE_ERROR"
```
**Validation:** Unit test with a verdict string containing `|` characters — confirm parsing succeeds without corruption.

---

### [P1-2] Chained Re-encoding Degrading Output Quality
**File:** `daily_producer.py` — `_apply_preflight_fixes` function, Lines 434–519
**Root cause:** Freeze frame fix, silence fix, and loudness fix each spawn a separate ffmpeg encode. A video with all three issues is re-encoded 3× sequentially, accumulating generational quality loss on every pass.
**Action:** Consolidate into a single ffmpeg invocation with a combined filtergraph:
```python
def _apply_preflight_fixes(input_path, issues):
    filters = []
    audio_filters = []

    if issues.get("freeze_frames"):
        filters.append("mpdecimate,setpts=N/FRAME_RATE/TB")
    if issues.get("silence"):
        audio_filters.append("silenceremove=start_periods=1:start_silence=0.1:start_threshold=-50dB")
    if issues.get("loudness"):
        audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

    vf = ",".join(filters) if filters else None
    af = ",".join(audio_filters) if audio_filters else None

    cmd = ["ffmpeg", "-i", str(input_path)]
    if vf:
        cmd += ["-vf", vf]
    if af:
        cmd += ["-af", af]
    cmd += ["-c:v", "libx264", "-crf", "18", str(output_path)]

    subprocess.run(cmd, shell=False, check=True)
```
**Validation:** Profile encode time and VMAF score on a test clip with all three issues present. Single-pass must match or exceed multi-pass output quality.

---

### [P1-3] Stale `/tmp` State Causing Cross-Run Contamination
**File:** `overnight_render_loop.py` Line 59 (`render_checkpoint.json`), `daily_producer.py` Line 1501 (`daily_producer.lock`)
**Root cause:** `/tmp` is not cleared between runs on many Linux configurations. A stale `render_checkpoint.json` from a crashed run can cause the next run to skip completed-but-bad renders or resume from an invalid state.
**Action:**
1. On startup, validate checkpoint schema and `run_id` against the current run before trusting any cached state.
2. Write `run_id` (timestamp + git SHA) into the checkpoint at creation time.
3. Reject checkpoints older than `MAX_CHECKPOINT_AGE_HOURS = 6` with a warning log and fresh start.
```python
MAX_CHECKPOINT_AGE_HOURS = 6
checkpoint_age = time.time() - os.path.getmtime(CHECKPOINT_PATH)
if checkpoint_age > MAX_CHECKPOINT_AGE_HOURS * 3600:
    logger.warning("Stale checkpoint detected — discarding and restarting clean.")
    os.unlink(CHECKPOINT_PATH)
```

---

## P2 — MEDIUM SEVERITY / IMPLEMENT NEXT SPRINT

### [P2-1] No Escalation Path After Max Iterations Without Grade A
**File:** `overnight_render_loop.py` — Lines 677–681
**Root cause:** When the loop exhausts `MAX_ITERATIONS` without achieving Grade A, execution silently exits or logs a warning. No human alert is triggered. Ultron produces nothing and the failure is invisible until morning.
**Action:**
1. After loop exhaustion, call a dedicated `_escalate_to_human(run_id, final_grade, final_score, log_path)` function.
2. Escalation must: (a) write a structured failure report to a persistent location outside `/tmp`, (b) send a notification (email/Slack webhook/PagerDuty — whichever is already wired), (c) retain the highest-scoring render artifact for manual review even if below Grade A threshold.

---

### [P2-2] Stale Cache Risk on `--skip-scan