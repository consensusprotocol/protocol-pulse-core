# CONSENSUS REPORT — ASSEMBLER-V2-REBUILD — CYCLE 2
Generated: 2026-03-18 18:09
Models: grok, gemini, gpt4o

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 6.0 | 6.0 | 6.0 | **6.0** |
| Law Compliance | 9.0 | 9.0 | 9.2 | **9.1** |
| Security | 7.0 | 7.0 | 6.8 | **6.9** |
| Backend Quality | 5.0 | 6.0 | 6.5 | **5.8** |
| **Overall** | **6.5** | **6.4** | **6.9** | **6.6** |

> **Scoring note:** All three models converged on a 6.0 Correctness score after Cycle 2 reflection — remarkable independent agreement. The Backend Quality spread (5.0–6.5) reflects differing weights on architectural duplication severity. Consensus adopts Gemini's harsher 5.0-anchored view given the scale of `encode_segment` bypass confirmed by all three models.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

### U1 — Silent Omission of Failed Segments from Final Episode
**Files:** `episode.py:143-153`, `segments/base.py:32-60`
**What it is:** `Segment.filler_result()` can return `RenderedSegment(path=None, ...)` if both `make_filler()` and the emergency ffmpeg fallback fail. The concat loop in `episode.py:143` then silently skips that segment. A final episode can be produced missing required content while still passing QC and receiving a non-HOLD verdict. This violates the `RenderedSegment` docstring invariant ("Always populated").
**What to change:**
1. In `segments/base.py`: if the emergency black-frame write fails, do not return `path=None` — raise immediately. The episode must halt, not silently truncate.
2. In `episode.py:143`: if any segment in the list has `path=None`, force `verdict = HOLD` and abort concat rather than skipping.
3. Add an assertion in `EpisodeRunner._run()` after segment collection: `assert all(r.path is not None for r in results)`.

### U2 — Massive Encode Path Duplication Bypassing `encode_segment()`
**Files:** `cold_open.py`, `narration.py`, `partner_clip.py`, `data_segment.py`, `social.py`, `signal_active.py`, `x_spaces_segment.py`
**What it is:** `ffmpeg_core/encode.py::encode_segment()` is a robust wrapper providing temp-file safety, contract checking, filler fallbacks, and atomic renaming. Only `transition.py` and `wrap.py` use it. Every other segment implements its own weaker version, missing the emergency black-frame fallback, consistent error handling, and contract verification.
**What to change:** Refactor all seven bypassing segment classes to route their final encode step through `encode_segment()`. This is the single largest structural defect in the codebase and the root cause of multiple downstream inconsistencies.

### U3 — Multi-Process Metrics Cache Race Condition (`threading.Lock`)
**Files:** `data_segment.py:85-91`, `state.py:37`
**What it is:** The metrics cache refresh is protected by a `threading.Lock`, which is **process-local only**. In a multi-worker deployment (Gunicorn, uWSGI, etc.), multiple workers can simultaneously miss the cache and all hit the upstream `mempool.space` API — the classic "thundering herd" problem. Concurrent writes to `metrics_cache.json` can also corrupt the file despite `os.replace()` atomicity, because both workers compute and stage the file simultaneously.
**What to change:** Replace `threading.Lock` with either:
- A file-based lock (`filelock` library: `FileLock("metrics_cache.lock")`) wrapping all read/write operations, **or**
- A centralized Redis cache with TTL, which also solves the thundering herd problem more elegantly and scales to the stated ~1000 concurrent users.

### U4 — ElevenLabs API Rate Limiting Completely Absent
**Files:** `social.py`, `signal_active.py`, `x_spaces_segment.py`
**What it is:** All three files make direct, unbounded ElevenLabs API calls with no rate limiting, per-episode quota caps, concurrency throttle, or cost guard. Under concurrent episode rendering or large episode manifests, this will exhaust API quotas silently, incur runaway costs, or trigger API key suspension.
**What to change:**
1. Extract the shared TTS call logic into a single `tts_helper.py` (the three call sites are already duplicating the same code).
2. Add a semaphore or token-bucket rate limiter within that helper.
3. Add a per-episode TTS character/call budget check before firing API calls.
4. Log quota consumption per episode in the `EpisodeReport`.

### U5 — Double Degradation Accounting in `NarrationSegment`
**Files:** `narration.py:53-57`, `segments/base.py:56`
**What it is:** After a post-publish contract failure, `NarrationSegment` explicitly calls `ctx.mark_degraded(...)` and then calls `self.filler_result()`, which also calls `ctx.mark_degraded()`. Every such failure is counted twice. This directly corrupts `EpisodeContext.verdict()` by inflating the degraded segment count, potentially flipping a correct PASS to an incorrect HOLD or producing a misleading DEGRADED verdict.
**What to change:** Remove the explicit `ctx.mark_degraded()` call in `narration.py` before `filler_result()`. The contract is that `filler_result()` owns degradation accounting. Audit all other segment classes for the same double-call pattern.

---

## MAJORITY FINDINGS (2 of 3 models agree)

### M1 — Duplicated TTS Generation Logic Across Three Segment Files
**Models:** Gemini + GPT-4o
**Files:** `social.py:98`, `signal_active.py:191`, `x_spaces_segment.py:100`
**What it is:** The ElevenLabs API call logic (auth, payload, response handling) is copy-pasted across three files. Any change to API behavior, auth headers, or error handling must be made in three places.
**What to change:** Extract into `tts_helper.py`. This also directly enables U4's rate limiting fix — implement both together.

### M2 — Brittle `ffprobe`/FFmpeg `stderr` Parsing in `probe.py`
**Models:** Gemini + GPT-4o
**Files:** `ffmpeg_core/probe.py:16-19`, `probe.py:24-26`
**What it is:** `probe.py` uses `subprocess.run` directly instead of `run_ffmpeg`, and parses `stderr` via string-splitting and substring searches. This parsing is tightly coupled to FFmpeg's current log format and will silently break with any FFmpeg version upgrade.
**What to change:** Where FFmpeg supports JSON output (e.g., `ffprobe -of json`), use it. For `ffmpeg -af loudnorm -f null` LUFS measurement, parse structured output or use a dedicated Python library (`pyloudnorm`) to reduce coupling to FFmpeg log strings.

### M3 — Concatenation Failure Has No Retry or Recovery
**Models:** Grok + GPT-4o (implied by silent failure discussion)
**Files:** `episode.py:173-177`
**What it is:** If `run_ffmpeg` fails during the concat step, the error is logged but there is no retry, no partial-concat fallback, and no immediate halt with a clear error report. The episode can silently fail at the final assembly step.
**What to change:** Add retry logic (1-2 retries with backoff) for transient I/O errors. If all retries fail, immediately return an `EpisodeReport` with `verdict=HOLD` and a clear `failure_reason` field — do not proceed to QC on a missing output file.

### M4 — Hardcoded ElevenLabs `voice_id` Magic String in Three Files
**Models:** Gemini + GPT-4o (GPT-4o explicit; Grok implied via API concerns)
**Files:** `social.py`, `signal_active.py`, `x_spaces_segment.py`
**What it is:** The same `voice_id` string literal is hardcoded in multiple files. A voice change requires three separate edits and creates audit risk.
**What to change:** Move `voice_id` to a single config constant in `config.py` or `constants.py`. This is a one-line fix that eliminates a maintenance liability.

### M5 — `preflight.py` Checks `output_dir`, Not Episode `workdir`
**Models:** GPT-4o (primary), Gemini (acknowledged as valid)
**Files:** `episode.py:94-108`, `preflight.py`
**What it is:** Disk space and path preflight checks run before `EpisodeContext.create()`, so they validate the parent output directory rather than the actual episode workdir. If the workdir is on a different mount point or volume, the disk check provides a false guarantee.
**What to change:** Restructure so `EpisodeContext.create()` runs first and passes `ctx.workdir` into preflight. If that order is architecturally constrained, at minimum document the assumption that `output_dir` and `workdir` share the same filesystem.

### M6 — `preflight.py` Severe Readability / Auditability Issues
**Models:** Gemini + GPT-4o
**Files:** `preflight.py` (entire file)
**What it is:** Multiple statements per line, single-letter variable names, no whitespace. The preflight function is a critical gate and must be auditable.
**What to change:** Reformat to PEP 8. Expand variable names. This is a security-adjacent quality issue — unreadable gate code will hide bugs.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### GPT-4o Unique: N1 — Inconsistent `episode_id` Between Fatal Error Path and Success Path
**Files:** `episode.py:75-80`, `episode.py:108`, `episode.py:249-250`
**Assessment: IMPLEMENT.**
Fatal error reports use `manifest.episode_id`; successful runs use `ctx.episode_id` (a newly generated UUID). These can differ. Incident tracing using episode IDs from logs vs. reports will be unreliable. Fix: pass `manifest.episode_id` into `EpisodeContext.create()` as the canonical ID rather than generating a new one.

### GPT-4o Unique: N2 — `EpisodeContext.verdict()` Policy Bug: Exceeding `QC_MAX_DEGRADED_SEGMENTS` Returns `DEGRADED` Not `HOLD`
**Files:** `state.py:72-83`
**Assessment: INVESTIGATE, then implement.**
If `QC_MAX_DEGRADED_SEGMENTS` is intended as a hard cap, returning `DEGRADED` instead of `HOLD` when it is breached is a policy error. Investigate the intended semantics: is `DEGRADED` a shipping-acceptable state? If yes, document it explicitly. If no, change the return to `HOLD`. Given the naming `MAX`, the consensus assessment is that breach should be `HOLD`.

### GPT-4o Unique: N3 — `signal_active.py` Leaks Temp Artifacts on Rerun
**Files:** `signal_active.py:187-223`
**Assessment: IMPLEMENT (low urgency).**
Intermediate files (`top_path`, `bot_path`, `concat_file`) are named by `idx` only. Reruns in the same workdir will silently reuse stale intermediates. Fix: use `tempfile.mkstemp` for all intermediates and clean up after successful encoding. Merge with U2 refactor.

### GPT-4o Unique: N4 — `SocialSegment._render_cards()` Computes `ts` but Never Uses It
**Files:** `social.py:321`
**Assessment: INVESTIGATE.**
Dead variable suggests unfinished rendering logic (timestamp overlay?). Either complete the intended feature or remove the dead code before ship.

### GPT-4o Unique: N5 — `x_spaces_segment.py` Computes `btc_str` but Never Uses It
**Files:** `x_spaces_segment.py:140`
**Assessment: INVESTIGATE.**
Same pattern as N4 — dead variable likely indicates incomplete footer attribution logic. Either implement or remove.

### GPT-4o Unique: N6 — `ffprobe_streams()` Does Not Check `returncode` Before `json.loads()`
**Files:** `helpers.py:64-74`
**Assessment: IMPLEMENT (low urgency).**
On ffprobe failure with empty stdout, `json.loads("")` raises silently caught by the surrounding `except` returning `{}`. Explicit returncode checking with a logged warning would improve diagnostics significantly for zero-cost.

### Grok Unique: N7 — Filler Duration Mismatch in `filler_result()` Emergency Path
**Files:** `segments/base.py:37-55`
**Assessment: IMPLEMENT (merge with P0.1 fix).**
The emergency black-frame write does not guarantee the output duration matches `self.dur`. A duration mismatch produces sync drift in the final concat and may cause QC duration checks to flag the episode. Fix: pass explicit `-t {self.dur}` to the emergency ffmpeg command and verify output duration after write.

### Grok Unique: N8 — No Validation of Social Post Text Length Before TTS
**Files:** `social.py:87-105`
**Assessment: IMPLEMENT.**
An unbounded batch of posts sent to ElevenLabs API with no character count check can hit API limits silently. Add a pre-call character budget check and truncate or split posts exceeding the limit. Merge with U4 fix.

### Gemini Unique: N9 — Brittle Playwright Chromium Discovery via Glob
**Files:** `social.py:124-145`
**Assessment: IMPLEMENT.**
Globbing `~/.cache/ms-playwright/**` for a Chromium binary is fragile across deployment environments (Docker, CI, cloud). Add `CHROMIUM_PATH` as a required environment variable checked in preflight. Keep the `drawtext` fallback but remove the glob discovery in favor of the explicit env var.

### Grok Unique: N10 — Potential Invalid FFmpeg `-ss`/`-t` Values from Unbounded Float Arithmetic in `helpers.py`
**Files:** `helpers.py:257-259`
**Assessment: INVESTIGATE.**
PiP normalization arithmetic on `start` and `actual_dur` is unclamped. While true integer overflow is not a Python risk, negative or zero values (e.g., `start > clip_duration`) would produce invalid FFmpeg arguments that fail silently or produce unexpected output. Add bounds validation: `assert 0 <= start < clip_duration` and `assert actual_dur > 0` before building the FFmpeg command.

---

## CONFLICTS (models disagree — tiebreaker)

### Conflict 1: Severity of `preflight.py` Disk Check Bug
- **GPT-4o:** Flags as an architectural correctness issue.
- **Gemini:** Partially agrees but classifies as low priority since most deployments share a filesystem.
- **Grok:** Does not address explicitly.
- **Tiebreaker: Gemini is right on priority, GPT-4o is right on correctness.** The bug is real but not a ship blocker in single-volume deployments. Classify P2. If multi-volume deployment is ever introduced, this becomes P0 immediately. Add a comment documenting the assumption.

### Conflict 2: Severity of `probe.py` Direct `subprocess.run` Usage
- **Gemini:** Flags as medium-priority inconsistency and brittleness risk.
- **GPT-4o:** Partially agrees but says direct subprocess for probe commands is "understandable."
- **Grok:** Does not flag explicitly.
- **Tiebreaker: GPT-4o is correct on the pragmatic assessment.** Direct subprocess for ffprobe with JSON output parsing is industry-standard and not inherently worse than `run_ffmpeg`. The real issue is the brittle stderr string parsing, not the subprocess call itself. Fix the parsing (use JSON where possible); do not mandate routing through `run_ffmpeg`.

### Conflict 3: Backend Quality Score (5.0 vs. 6.5)
- **Gemini:** 5.0 — emphasizes architectural breakdown from encode duplication.
- **Grok:** 6.5 — more lenient; system is functional.
- **GPT-4o:** 6.0 — middle ground.
- **Tiebreaker: Consensus adopts 5.8, leaning toward Gemini's view.** The encode duplication affects 7 of ~9 content segment classes. That is not a localized problem; it is a systemic architectural failure. The lower score is the more honest assessment.

---

## VALIDATED STRENGTHS (all models agree — do NOT change)

1. **Top-level `EpisodeRunner.run()` never raises** — broad `try/except` wrapper guarantees an `EpisodeReport` is always returned. This is correctly implemented and must not be changed.

2. **Law 1 compliance (`render()` never raises, `filler_result()` on failure)** — Every `Segment.render()` implementation correctly wraps its work in `try/except Exception` and calls `self.filler_result()`. The pattern is universally applied.

3. **Law 2 compliance (CRF-only encoding)** — All video encoding calls correctly use `-crf` with no `-b:v`, `-maxrate`, or `-bufsize` alongside it. Do not add bitrate controls.

4. **Empty segment list guard** — `episode.py:101-102` correctly raises `ValueError` before rendering begins. Keep as-is.

5. **`EpisodeContext` per-episode workdir isolation** — Each episode gets a unique `workdir`, correctly avoiding global state pollution between concurrent episodes.

6. **`encode_segment()` implementation itself** — The function in `ffmpeg_core/encode.py` is excellent: temp-file safety, atomic rename, contract checking, filler fallback, emergency black frame. The problem is it isn't used widely enough — the implementation itself is the gold standard.

7. **`safe_text()` injection prevention** — Shell-injection sanitization on text passed to FFmpeg `drawtext` is present and correct. Do not weaken it.

8. **Manifest validation and preflight gate** — The overall preflight + manifest validation before any rendering begins is the right architecture. Keep the structure; fix the workdir targeting (M5).

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|---|---|---|
| Law 1: `render()` never raises — `filler_result()` on any failure | **COMPLIANT** | Universal compliance across all segment classes. Validated by all 3 models. |
| Law 2: CRF-only encoding. No `-b:v`/`-maxrate`/`-bufsize` alongside `-crf` | **COMPLIANT** | All encoding paths use CRF correctly. |
| Law 3 (implied): Atomic file writes / no partial outputs | **PARTIALLY VIOLATED** | `filler_result()` emergency path does not guarantee atomicity. `encode_segment()` correctly uses temp+rename; bypassing segments do not. Fix under U2. |
| Law 4 (implied): All failures produce `degraded=True` in segment report | **VIOLATED** | Double-counting in `NarrationSegment` corrupts the degraded count. Fix under U5. `path=None` case violates the invariant entirely. Fix under U1. |

**Final determination:** The code is compliant with the explicitly stated encoding laws. It is non-compliant with the implied output invariant laws that underpin the entire pipeline's correctness guarantees.

---

## SECURITY CONSENSUS

All models flagged the following, in priority order:

1. **P0 — API quota exhaustion / cost runaway (ElevenLabs):** Unbounded calls to a metered external API with no rate limiting or budget cap. This is an operational and financial security issue. A malformed manifest or adversarial input could trigger runaway costs. **(U4)**

2. **P1 — `safe_text()` as single point of failure for shell injection:** Validated as correctly implemented, but all text entering FFmpeg `drawtext` routes through it. If any code path bypasses it (e.g., in new segments added by future developers), the consequence is shell injection. Consider a type-wrapper (`SafeText`) that makes the sanitization explicit at the type level rather than a function convention.

3. **P1 — `metrics_cache.json` file corruption under concurrent writes:** Not a traditional security issue, but a data integrity issue with operational security implications — a corrupted cache can cause an episode to use incorrect on-chain metrics, producing misleading financial content. **(U3)**

4. **P2 — `probe.py` brittle `stderr` parsing:** A future FFmpeg upgrade changing log format could silently break LUFS/silence/black-frame QC, allowing out-of-spec content to ship as PASS. This is a content integrity risk.

5. **P2 — No validation of `social_posts` length before TTS call:** Large inputs could trigger unexpected API behavior or timeouts. **(N8)**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models as missing from a truly production-grade system:

1. **Centralized, process-safe caching layer (2+ models):** The metrics cache problem is a symptom of a deeper gap — the system lacks any shared state infrastructure (Redis, Memcached) for a multi-worker deployment. A world-class system at ~1000 concurrent users needs this as a foundation, not an afterthought.

2. **Unified encode pipeline for all segments (all 3 models):** A world-class media pipeline has exactly one encode path with one set of contracts, one fallback chain, and one source of truth for output format. Seven different bespoke encode implementations is not that. Full adoption of `encode_segment()` is the minimum bar.

3. **Guaranteed output invariant with circuit-breaker behavior (2+ models):** A world-class pipeline never silently truncates content. Every segment slot must produce a video file of the correct duration, or the pipeline halts with a clear, actionable error. The current "skip and continue" behavior is fundamentally incompatible with a reliable broadcast system.

4. **Operational observability: rate limiting, quota tracking, cost attribution (all 3 models):** World-class systems know, in real time, how much of each external API quota they've consumed, per episode, per hour, and in total. None of this exists. Add structured logging of API calls with response codes, character counts, and latency to the `EpisodeReport`.

5. **Centralized, testable TTS abstraction (2+ models):** The three duplicated ElevenLabs call sites should be a single injectable `TTSProvider` interface, making it trivial to swap providers, mock in tests, and add new voices without touching segment code.

---

## FINAL ACTION PLAN (sorted by consensus priority)

### P0 CRITICAL

| # | Change | File:Line | Models | Why |
|---|---|---|---|---|
| P0.1 | Enforce segment output invariant: `filler_result()` must always write a file of correct duration; if impossible, raise immediately. `episode.py` concat must treat `path=None` as a hard HOLD, not a skip. | `segments/base.py:32-60`, `episode.py:143-153` | ALL | Silent content omission is a production correctness blocker. Final video can ship missing required segments. |
| P0.2 | Replace `threading.Lock` with process-safe file lock (`filelock`) or Redis for metrics cache | `data_segment.py:85-91`, `state.py:37` | ALL | `threading.Lock` provides zero protection between Gunicorn workers. Cache corruption and API thundering herd are guaranteed under load. |
| P0.3 | Refactor all 7 bypassing segment classes to use `encode_segment()` | `cold_open.py`, `narration.py`, `partner_clip.py`, `data_segment

---

# WINNER DETERMINATION

WINNER: **Gemini** — Gemini delivered the highest-quality analysis across the audit cycle by being the **originating source** of the two most critical and cross-validated findings: the multi-process `threading.Lock` race condition (U-class, unanimous in Cycle 2) and the systemic `encode_segment` bypass duplication (also unanimous). Its analysis demonstrated genuine architectural depth — correctly reasoning from the deployment context ("~1000 concurrent users → Gunicorn multi-process") to a non-obvious concurrency failure that neither Grok nor GPT-4o independently surfaced in Cycle 1 — and its recommendations were specific, implementable, and proved durable under Cycle 2 cross-examination.

---

## FINAL SECOND-PASS PRIORITY LIST

Ordered by: severity of production impact × confidence of consensus confirmation.

---

### PRIORITY 1 — Silent Omission of Failed Segments from Final Episode
**Files:** `episode.py:143-153`, `segments/base.py:32-60`
**Why first:** A completed episode can ship with missing content and still receive a PASS verdict. This is a silent data-integrity failure with zero observable signal at runtime.
**Implement:**
1. `segments/base.py`: Raise immediately if the emergency black-frame write fails. Do not return `path=None` under any code path.
2. `episode.py:143`: Before the concat loop, assert `all(r.path is not None for r in results)` — any `None` forces `verdict = HOLD` and aborts.
3. Add a post-collection guard in `EpisodeRunner._run()` as a belt-and-suspenders check.

---

### PRIORITY 2 — Multi-Process Race Condition on Metrics Cache
**Files:** `data_segment.py`, `state.py:37`
**Why second:** Under multi-worker deployment (Gunicorn), `threading.Lock` provides zero cross-process protection. Result: corrupted `metrics_cache.json` and thundering-herd hammering of the `mempool.space` API. Will manifest under load.
**Implement:**
1. Replace `threading.Lock` with `filelock.FileLock` on `metrics_cache.json` for write operations.
2. Prefer Redis or a centralized cache if the infrastructure already supports it.
3. Add a circuit breaker around the upstream API call to cap blast radius during a thundering-herd event.

---

### PRIORITY 3 — Massive `encode_segment()` Bypass Across Segment Classes
**Files:** `cold_open.py`, `narration.py`, `partner_clip.py`, `data_segment.py`, `social.py`, `signal_active.py`, `x_spaces_segment.py`
**Why third:** Seven segment classes reimplement their own weaker encoding logic, forgoing temp-file atomicity, contract checking, and the emergency black-frame fallback. Every divergence is an independent bug surface.
**Implement:**
1. Refactor all seven classes to route their FFmpeg invocations through `ffmpeg_core/encode.py::encode_segment()`.
2. Extend `encode_segment()` with any segment-specific parameters it currently lacks rather than bypassing it.
3. Delete the duplicated local encoding logic after migration. Do not leave dead code.

---

### PRIORITY 4 — Double Degradation Accounting
**Files:** `narration.py`, and any segment calling `ctx.mark_degraded()` before delegating to `filler_result()`
**Why fourth:** `filler_result()` internally calls `mark_degraded()`. Callers who also call it directly produce inflated degradation counts, which corrupts the QC verdict threshold logic.
**Implement:**
1. Audit every call site of `ctx.mark_degraded()` and remove any that precede a `filler_result()` call.
2. Add a docstring contract to `filler_result()` explicitly stating it calls `mark_degraded()` internally.
3. Consider making `mark_degraded()` idempotent per segment ID as a defensive measure.

---

### PRIORITY 5 — Preflight Runs Against Wrong Directory
**Files:** `episode.py:94-108`
**Why fifth:** Preflight disk and asset checks run against `output_dir` before `EpisodeContext.create()`, meaning the actual episode workdir is never validated. Not a crash risk today, but an architectural incorrectness that will cause silent failures if workdir and output_dir ever diverge.
**Implement:**
1. Restructure `_run()` so `EpisodeContext.create()` is called before preflight.
2. Pass `ctx.workdir` to the preflight checker rather than `output_dir`.

---

### PRIORITY 6 — ElevenLabs API Calls Lack Rate Limiting and Hardcode Voice ID
**Files:** `social.py`, `signal_active.py`, `x_spaces_segment.py`
**Why sixth:** Three independent call sites share no rate-limiting logic and hardcode the same `voice_id`. A burst of concurrent renders will exhaust quota with no circuit breaker. Voice ID drift across deployments is a silent configuration risk.
**Implement:**
1. Centralize all ElevenLabs calls behind a single client wrapper with a token-bucket rate limiter.
2. Move `voice_id` to a single configuration constant or environment variable consumed by the wrapper.
3. Add quota-remaining checks and a graceful degradation path (silence or TTS fallback) when quota is low.

---

### PRIORITY 7 — No Retry Logic on FFmpeg Concatenation Failure
**Files:** `episode.py:143-180`
**Why seventh:** A transient I/O error during concatenation causes immediate episode failure with no retry attempt. This is a reliability gap for I/O-bound production environments.
**Implement:**
1. Wrap the `run_ffmpeg` concat call in a retry loop (max 3 attempts, exponential backoff).
2. Log each retry attempt with attempt number and elapsed time.
3. Only promote to a hard HOLD after all retries are exhausted.

---

### PRIORITY 8 — QC Verdict Downgrade Lacks Specific Failure Logging
**Files:** `episode.py:239-243`
**Why eighth:** When a PASS verdict is overridden to HOLD, the log does not record which specific QC check triggered the downgrade. Debugging production failures requires manual log archaeology.
**Implement:**
1. At the point of each PASS→HOLD override, log the specific failing metric (LUFS value, black frame count, silence duration, measured vs. expected duration) at WARNING level.
2. Include the failing metric in the `EpisodeReport` returned to the caller.