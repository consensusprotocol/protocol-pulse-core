# CONSENSUS REPORT — ASSEMBLER-V2-REBUILD — CYCLE 2
Generated: 2026-03-18 02:31
Models: Grok (+2 failed — Gemini 403 API key leaked, GPT-4o 429 quota exceeded)

---

> ⚠️ **AUDIT INTEGRITY NOTICE:** This Cycle 2 consensus was produced from a single model (Grok). Gemini 2.5 Pro and GPT-4o failed due to infrastructure errors (leaked API key and exhausted quota, respectively). Cross-model validation is absent. All findings below reflect Grok's analysis across Cycles 1 and 2. Confidence ratings are adjusted downward accordingly. **Strongly recommend resolving API issues and running a full 3-model Cycle 3 before treating any P0/P1 item as fully validated.**

---

## SCORES

| Subsystem        | Gemini | GPT-4o | Grok | Consensus         |
|------------------|--------|--------|------|-------------------|
| Correctness      | N/A    | N/A    | 5.5/10 | 5.5/10 ⚠️ single-model |
| Law Compliance   | N/A    | N/A    | 6/10   | 6/10 ⚠️ single-model   |
| Security         | N/A    | N/A    | 7/10   | 7/10 ⚠️ single-model   |
| Frontend Quality | N/A    | N/A    | N/A    | N/A (no frontend)      |
| Overall Readiness| N/A    | N/A    | 6/10   | 6/10 ⚠️ single-model   |

> **Score note:** Grok downgraded from Cycle 1 (Correctness 6→5.5, Law Compliance 7→6, Security 7.5→7, Overall 6.5→6) based on compounding issues discovered across both cycles. Without Gemini and GPT-4o confirmation, treat all scores as provisional lower bounds — the true score could be higher or lower.

---

## UNANIMOUS FINDINGS (all 1 active models agree — implement unconditionally)

With only one model available, "unanimous" means Grok identified these issues consistently across both Cycle 1 and Cycle 2, demonstrating internal stability. These are the highest-confidence findings from the available data.

---

### U-1 — Law 2 Violation: CRF-only encoding rule broken
- **What it is:** Governing Law 2 mandates CRF-only encoding. `VIDEO_BITRATE`, `VIDEO_MAXRATE`, and `VIDEO_BUFSIZE` constants are defined and actively passed to FFmpeg alongside `-crf`, violating this constraint and producing non-compliant output.
- **Files/Lines:** `constants.py:15-17`, `ffmpeg_core/encode.py:22`
- **What to change:** Remove `VIDEO_BITRATE`, `VIDEO_MAXRATE`, `VIDEO_BUFSIZE` from `constants.py`. Remove all references to these in `ffmpeg_core/encode.py:22`. Keep only `-crf` and `-preset` in the encoding chain.
- **Confidence:** HIGH (Grok flagged in both cycles with consistent evidence)

---

### U-2 — Law 6 Violation: Duplicate drawtext sanitization bypasses canonical safe_text()
- **What it is:** Custom sanitization logic exists in `narration.py:139-156` and `cold_open.py:140-150` instead of routing through the canonical `safe_text()` in `helpers.py:278-282`. Law 6 requires a single sanitizer. Multiple sanitization paths create divergent attack surfaces and maintenance liability.
- **Files/Lines:** `narration.py:139-156`, `cold_open.py:140-150`, `helpers.py:278-282`
- **What to change:** Delete the custom sanitization blocks in both segment files. Replace with direct calls to `helpers.safe_text()`. Verify `safe_text()` covers all cases the custom logic handled (if not, extend `safe_text()` canonically rather than patching locally).
- **Confidence:** HIGH (Grok flagged in both cycles)

---

### U-3 — Silent FFmpeg failure propagation prevents production debugging
- **What it is:** `run_ffmpeg()` in `helpers.py:20-42` returns `False` on failure without propagating FFmpeg stderr content to higher layers. Failures in production are invisible without log correlation, significantly extending mean time to diagnose.
- **Files/Lines:** `helpers.py:20-42`
- **What to change:** Capture and surface FFmpeg stderr in the return value or via structured logging at ERROR level. Consider returning a result object `(success: bool, stderr: str)` or raising a typed exception that calling code can handle and log meaningfully.
- **Confidence:** HIGH (flagged both cycles, operationally impactful)

---

### U-4 — Race condition in workdir naming during concurrent rendering
- **What it is:** `state.py:43` constructs `workdir` using `date_str` (date-level granularity). Two episodes rendering concurrently on the same day will share the same workdir path, risking file overwrites, corrupted intermediate segments, and silently incorrect final output.
- **Files/Lines:** `state.py:43`
- **What to change:** Append a UUID4 or high-resolution timestamp (microseconds) to the workdir name. Example: `workdir = base_dir / f"{date_str}_{episode_id}_{uuid.uuid4().hex[:8]}"`. Alternatively, use `tempfile.mkdtemp()` for guaranteed uniqueness.
- **Confidence:** HIGH (flagged both cycles)

---

### U-5 — Silent failure in metrics background thread (stale data risk)
- **What it is:** The background thread responsible for refreshing metrics in `data_segment.py:76` fails silently. Stale or missing data renders without warning, producing episodes with outdated metrics that appear valid to operators.
- **Files/Lines:** `data_segment.py:60-96`, `data_segment.py:76`
- **What to change:** Add structured exception handling in the background thread with ERROR-level logging on failure. Expose a staleness indicator (e.g., timestamp of last successful fetch). Consider surfacing a visible warning in the rendered segment or the episode manifest when data is stale beyond a configurable threshold.
- **Confidence:** HIGH (flagged both cycles)

---

## MAJORITY FINDINGS (2 of 1 models agree)

> **Structural note:** With only one functioning model, true majority consensus (2-of-3) is impossible. This section captures findings Grok identified in *both* Cycle 1 and Cycle 2 independently — the closest analog to majority confirmation available from a single-model audit. These should be treated as strong single-model findings, not confirmed cross-model consensus.

---

### M-1 — Inconsistent timeout values across FFmpeg calls
- **What it is:** Timeout values are not standardized — `helpers.py:20` uses 300s, `helpers.py:173` uses 60s, `cold_open.py:108` uses 120s, with additional variation in `ffmpeg_core/encode.py:9` and `segments/transition.py:50`. On Ultron server under load, short timeouts may cause false failures; long timeouts may stall pipelines.
- **Files/Lines:** `helpers.py:20`, `helpers.py:173`, `cold_open.py:108`, `ffmpeg_core/encode.py:9`, `segments/transition.py:50`
- **What to change:** Define a `FFMPEG_TIMEOUT_DEFAULT` constant in `constants.py`. Optionally define per-category timeouts (encode vs. probe vs. filter). Audit all call sites and replace magic numbers with constant references.
- **Recommendation:** Implement — operational reliability risk is real.

---

### M-2 — Empty segments list in manifest proceeds silently
- **What it is:** `EpisodeManifest.__init__` in `manifest.py:63` does not validate that the `segments` list is non-empty. An empty manifest silently produces no content, likely resulting in a failed or zero-duration output file with no immediate error raised.
- **Files/Lines:** `manifest.py:63`
- **What to change:** Add an explicit guard: `if not self.segments: raise ValueError("EpisodeManifest must contain at least one segment.")` at initialization. Add a test case for this invariant.
- **Recommendation:** Implement — fast-fail behavior here prevents silent corruption.

---

## UNIQUE INSIGHTS (only 1 model, single-cycle — evaluate carefully)

These were raised by Grok in Cycle 2 only (not in Cycle 1), making them lower-confidence novel observations. Each is assessed individually.

---

### X-1 — Integer precision risk in duration rounding
- **What it is:** `round()` applied to durations at `ffmpeg_core/encode.py:24` and `narration.py:109` may introduce subtle timing drift for very long segments or compounding rounding across many segments in a long episode.
- **Assessment:** **Investigate further.** This is a real class of bug in video pipeline math. The risk depends on whether durations are accumulated additively (compound error) or treated independently. If segment durations feed into `-t` or `-ss` parameters that stack, precision matters. Recommend auditing the full duration arithmetic chain before dismissing.
- **Action:** Map how `round(duration, 3)` values propagate through FFmpeg command construction. If any accumulation occurs, switch to integer milliseconds internally and convert only at FFmpeg invocation boundaries.

---

### X-2 — Chart keyword not validated against supported values
- **What it is:** `chart_keyword` in `SegmentSpec` is not validated against the set of keywords supported by `get_chart_path()` in `helpers.py:258-276`. An invalid keyword returns `None` silently, causing unexpected visual fallback without logging or alerting.
- **Files/Lines:** `data_segment.py:125-129`, `helpers.py:258-276`
- **Assessment:** **Implement.** This is a clean defensive programming fix. Define an allowlist of valid chart keywords (presumably small and stable) and validate at `SegmentSpec` construction time or at `get_chart_path()` entry. Log a warning with the invalid keyword when fallback is triggered.

---

### X-3 — whoosh_applied deduplication fragile on symlinked paths
- **What it is:** `EpisodeContext.whoosh_applied` in `state.py:26` uses a set of resolved paths for SFX deduplication. On systems with symlinks or inconsistent path resolution, the same physical file may appear as different strings, defeating deduplication.
- **Assessment:** **Investigate further.** Depends on deployment environment. If Ultron server has no symlinks in the audio asset path, risk is low. Recommend normalizing paths with `Path.resolve()` before insertion into the set as a low-cost hardening measure regardless.

---

### X-4 — partner_clip.py short-clip fallback has no duration logging
- **What it is:** In `partner_clip.py:59-64`, clips under 2 seconds trigger a filler segment but do not log the actual measured duration. Silent fallback in production makes it impossible to diagnose whether the source asset is corrupt, incorrectly trimmed, or from a bad ingest.
- **Assessment:** **Implement.** Trivial one-line fix: log the measured duration at WARNING level before returning filler. High signal-to-noise for operators.

---

## CONFLICTS (models disagree — your tiebreaker)

> With only one active model, there are no inter-model conflicts to resolve. Grok's Cycle 2 output showed one internal tension:

**Grok C1 vs. C2 on manifest.py:63 severity:** Cycle 1 treated empty manifest as a clear error; Cycle 2 hedged that it "might not always be a critical failure if handled gracefully by the caller." 

**Tiebreaker:** Cycle 1 was correct. A pipeline that silently produces zero-content output is never acceptable behavior regardless of caller handling. The caller should not be expected to defend against a malformed manifest — the manifest should defend itself. Implement the explicit `ValueError` guard (see M-2).

---

## VALIDATED STRENGTHS (all models agree this is already excellent)

> **Caveat:** With only Grok available, "validated" means Grok identified these patterns as correctly implemented across both cycles without raising concerns. These assessments should be re-confirmed when Gemini and GPT-4o are restored.

---

**VS-1 — Consistent filler fallback pattern across all segment renderers**
Every segment type correctly falls back to a filler segment on rendering failure rather than crashing the pipeline. This is the correct production behavior for a live broadcast tool. Do not remove or weaken this pattern.

**VS-2 — EpisodeContext eliminates global state correctly**
`EpisodeContext` in `state.py:15-99` properly scopes all episode state to a context object, avoiding the global variable anti-pattern. The design is correct per spec. Do not regress this.

**VS-3 — FFmpeg stderr capture in run_ffmpeg**
`run_ffmpeg` does capture stderr — the issue is propagation, not capture. The underlying capture architecture is sound. Fix the propagation (U-3) without restructuring the capture mechanism.

**VS-4 — Segment rendering follows consistent interface contract**
All segment types in `segments/*.py` follow a consistent `render() -> Path` interface pattern, making the pipeline composable and testable. This uniformity is a strength. Do not break the interface contract when making fixes.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Evidence | Determination |
|-----|--------|----------|---------------|
| Law 2 — CRF-only encoding | ❌ **VIOLATED** | `VIDEO_BITRATE/MAXRATE/BUFSIZE` in `constants.py:15-17`, used in `ffmpeg_core/encode.py:22` | P0 blocker. Remove bitrate params. |
| Law 6 — Single canonical sanitizer | ❌ **VIOLATED** | Custom sanitization in `narration.py:139-156`, `cold_open.py:140-150` bypasses `safe_text()` | P0 blocker. Consolidate to `safe_text()`. |
| All other laws | ✅ **Tentatively compliant** | No violations flagged by Grok across 2 cycles | Confirm with full 3-model cycle when APIs restored. |

**Final determination:** Two confirmed law violations. Both are P0 blockers. Code is **not law-compliant** and cannot ship in current state.

---

## SECURITY CONSENSUS

Priority order based on Grok's findings (single-model — treat as preliminary):

1. **HIGHEST — Sanitization bypass (Law 6 / U-2):** Custom sanitization in narration and cold open creates an inconsistent injection surface for drawtext commands. If any user-controlled or externally-sourced text reaches these paths, the inconsistent handling could allow filter injection. Consolidate to `safe_text()` immediately.

2. **HIGH — Race condition in workdir (U-4):** Concurrent rendering sharing a workdir is not merely a correctness bug — an attacker with ability to trigger concurrent renders could potentially read or overwrite intermediate files from another episode's render. Use UUID-suffixed paths.

3. **MEDIUM — Silent failure masking (U-3, U-5):** Silent failures can mask active exploitation or data corruption. Observable, logged failures are a security property, not just an operational convenience.

4. **LOW — Path deduplication on symlinks (X-3):** Potential for SFX duplication; low direct security impact but worth hardening.

---

## WORLD-CLASS GAP CONSENSUS

> With only one model, this section identifies gaps Grok raised consistently across both cycles. These represent the delta between "working code" and "production-grade broadcast infrastructure."

**Gap 1 — No retry mechanism for transient failures (mentioned both cycles)**
FFmpeg failures and API fetch failures hit filler immediately with no retry. World-class media pipeline infrastructure implements exponential backoff with jitter for transient failures (network blips, resource contention) before falling back to filler. A single transient FFmpeg error causing a filler in a live broadcast episode is avoidable.

**Gap 2 — No structured observability / metrics emission (mentioned both cycles)**
Silent failures, stale data, and filler fallbacks are all operationally invisible. A world-class pipeline emits structured events (e.g., OpenTelemetry spans, Prometheus counters) for: segment render success/failure, filler activation, FFmpeg duration, API fetch latency. Without this, operators are flying blind in production.

**Gap 3 — No manifest validation layer (mentioned both cycles)**
Manifest arrives unchecked: empty segments, invalid keywords, out-of-order dependencies. World-class systems validate the manifest as a typed contract before any rendering begins, producing a complete validation report rather than discovering failures mid-render.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Remove `VIDEO_BITRATE`, `VIDEO_MAXRATE`, `VIDEO_BUFSIZE` constants and all FFmpeg usages | `constants.py:15-17`, `ffmpeg_core/encode.py:22` | Grok (both cycles) | Direct Law 2 violation; non-compliant encoding output |
| **P0 CRITICAL** | Replace custom sanitization with `safe_text()` calls | `narration.py:139-156`, `cold_open.py:140-150` | Grok (both cycles) | Law 6 violation; inconsistent injection surface |
| **P0 CRITICAL** | Add UUID/microsecond suffix to workdir construction | `state.py:43` | Grok (both cycles) | Race condition causes file overwrites in concurrent rendering |
| **P1 HIGH** | Propagate FFmpeg stderr to callers via structured logging or typed exception | `helpers.py:20-42` | Grok (both cycles) | Silent failures undebuggable in production |
| **P1 HIGH** | Add exception handling + ERROR logging to metrics background thread; expose staleness timestamp | `data_segment.py:60-96`, `data_segment.py:76` | Grok (both cycles) | Stale data renders silently as valid output |
| **P1 HIGH** | Define `FFMPEG_TIMEOUT_DEFAULT` constant; replace all magic timeout numbers | `helpers.py:20`, `helpers.py:173`, `cold_open.py:108`, `ffmpeg_core/encode.py:9`, `segments/transition.py:50` | Grok (both cycles) | Unpredictable behavior under load; operational reliability |
| **P1 HIGH** | Validate `chart_keyword` against allowlist; log WARNING on invalid keyword fallback | `data_segment.py:125-129`, `helpers.py:258-276` | Grok C2 unique | Silent visual fallback is unacceptable for broadcast output |
| **P2 MEDIUM** | Add `ValueError` guard for empty `segments` list in manifest | `manifest.py:63` | Grok (both cycles) | Silent zero-content render instead of fast-fail |
| **P2 MEDIUM** | Log measured clip duration at WARNING before partner clip filler fallback | `partner_clip.py:59-64` | Grok (unique) | Ingest debugging impossible without duration in logs |
| **P2 MEDIUM** | Normalize paths with `Path.resolve()` before inserting into `whoosh_applied` | `state.py:26` | Grok (unique) | Symlink edge case defeats SFX deduplication |
| **P2 MEDIUM** | Audit duration arithmetic chain; switch to integer-millisecond internal representation if durations accumulate | `ffmpeg_core/encode.py:24`, `narration.py:109` | Grok C2 unique | Potential compound rounding drift in long episodes |

---

## CYCLE 2 VERDICT

**Production-ready: NO.**

**Status: BLOCKED on P0 items.**

Two confirmed governing law violations (Law 2 CRF-only, Law 6 single sanitizer) are hard blockers regardless of any other assessment. These are not style issues or recommendations — they are contractual violations with the system's own specification.

Beyond the law violations, the race condition in workdir naming (U-4) is a correctness blocker for any deployment environment that renders more than one episode concurrently, which must be assumed for any production system.

**The absolute final blockers before any production deployment:**
1. Remove bitrate parameters — Law 2 (`constants.py:15-17`, `ffmpeg_core/encode.py:22`)
2. Consolidate to `safe_text()` — Law 6 (`narration.py:139-156`, `cold_open.py:140-150`)
3. Fix workdir race condition — (`state.py:43`)

**Additional critical caveat:** This verdict is based on a single-model audit. The two model failures (Gemini leaked key, GPT-4o quota) mean cross-model validation never occurred in Cycle 2. There may be additional issues Gemini or GPT-4o would have caught that Grok missed. **Restore API access and run a full 3-model Cycle 3 before treating this as a fully validated audit.**

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/ASSEMBLER_V2_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/assembler-v2-rebuild_CONSENSUS_C2.md.

This is the FINAL PASS for assembler-v2-rebuild.
The codebase was reviewed by 1 active AI model (Grok) across 2 cycles.
Note: Gemini and GPT-4o failed due to API errors in Cycle 2 — cross-model
validation is incomplete. Implement every P0 and P1 item. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Remove VIDEO_BITRATE, VIDEO_MAXRATE, VIDEO_BUFSIZE constants and FFmpeg usages | constants.py:15-17, ffmpeg_core/encode.py:22 | Law 2 violation — CRF-only encoding rule broken
P0 CRITICAL | Replace custom drawtext sanitization with safe_text() calls | narration.py:139-156, cold_open.py:140-150 | Law 6 violation — duplicate sanitization bypasses canonical sanitizer
P0 CRITICAL | Add UUID4 or microsecond suffix to workdir path construction | state.py:43 | Race condition on concurrent rendering causes file overwrites

P1 HIGH | Propagate FFmpeg stderr to callers via structured ERROR logging or typed exception | helpers.py:20-42 | Silent failures are undebuggable in production
P1 HIGH | Add exception handling + ERROR logging to metrics background thread; expose last-successful-fetch timestamp | data_segment.py:60-96, data_segment.py:76 | Stale metrics render as valid output with no operator signal
P1 HIGH | Define FFMPEG_TIMEOUT_DEFAULT in constants.py; replace all hardcoded timeout values | helpers.py:20, helpers.py:173, cold_open.py:108, ffmpeg_core/encode.py:9, segments/transition.py:50 | Inconsistent timeouts cause unpredictable behavior under load
P1 HIGH | Validate chart_keyword against supported allowlist; log WARNING on invalid keyword fallback | data_segment.py:125-129, helpers.py:258-276 | Silent visual fallback unacceptable for broadcast output

P2 MEDIUM | Add ValueError guard for empty segments list at manifest construction | manifest.py:63 | Silent zero-content render instead of immediate fast-fail
P2 MEDIUM | Log measured clip duration at WARNING level before partner clip filler activation | partner_clip.py:59-64 | Ingest debugging impossible without duration in logs
P2 MEDIUM | Normalize paths with Path.resolve() before inserting into whoosh_applied set | state.py:26 | Symlink paths defeat SFX deduplication
P2 MEDIUM | Audit duration arithmetic chain for accumulation; switch to integer-millisecond internal representation if durations compound | ffmpeg_core/encode.py:24, narration.py:109 | Potential rounding drift in long episodes

VALIDATED (do NOT touch — all models confirmed excellent):
- Filler fallback pattern across all segment renderers (segments/*.py) — correct production behavior, do not weaken
- EpisodeContext scoped state management (state.py:15-99) —

---

# WINNER DETERMINATION

# WINNER: Grok

Grok demonstrated the highest-quality analysis across all four criteria — its Cycle 1 findings proved accurate enough to survive into the Cycle 2 consensus as the sole validated source, it surfaced issues others either missed or failed to weigh in on (race conditions, silent failures, duplicate sanitization, Law 2 violations with specific line citations), its recommendations were actionable with precise file and line-number references, and it maintained thorough coverage across correctness, compliance, security, and state management. The structural integrity of its findings held across both cycles without self-contradiction, which is the strongest signal available given the collapsed cross-validation environment.

---

# FINAL SECOND-PASS PRIORITY LIST

> **Confidence note:** All items below are provisionally validated by Grok across two cycles. No cross-model confirmation exists. Treat P0/P1 as high-confidence directional findings — not fully ratified. Resolve API failures and run Cycle 3 before marking any item closed in production.

---

## P0 — CRITICAL: FIX BEFORE ANY MERGE

---

### P0-1 — Law 2 Violation: CRF-only encoding rule broken
- **File:** `constants.py:15–17`, `ffmpeg_core/encode.py:22`
- **Issue:** `VIDEO_BITRATE`, `VIDEO_MAXRATE`, and `VIDEO_BUFSIZE` are defined and actively passed to FFmpeg alongside `-crf`, directly violating the governing law mandating CRF-only encoding. This is not a style issue — it is a hard compliance failure.
- **Action:** Remove `VIDEO_BITRATE`, `VIDEO_MAXRATE`, and `VIDEO_BUFSIZE` from `constants.py`. Audit `ffmpeg_core/encode.py` to strip all `-b:v`, `-maxrate`, and `-bufsize` flags from the FFmpeg command construction. Confirm only `-crf` and `-preset` remain in the video encoding chain.
- **Verification:** Run a full encode and inspect the FFmpeg command log. Assert no bitrate flags appear in output.

---

### P0-2 — Silent FFmpeg Failure: Errors swallowed without propagation
- **File:** `helpers.py:20–42`
- **Issue:** FFmpeg subprocess calls do not raise on non-zero exit codes. Failures are logged but not propagated, meaning a failed render silently continues and produces corrupt or empty output downstream.
- **Action:** Add explicit returncode checks after every FFmpeg subprocess call. Raise a named exception (e.g., `FFmpegError`) on non-zero exit, capturing stderr for context. Do not allow the pipeline to continue past a failed segment render.
- **Verification:** Inject a deliberately invalid FFmpeg command and confirm the pipeline halts with a traceable exception rather than silent continuation.

---

### P0-3 — Silent API Failure: Data segment refresh errors not propagated
- **File:** `data_segment.py:60–96`
- **Issue:** API refresh failures inside the data segment renderer are caught and suppressed. If the data feed fails, the segment renders with stale or null data with no signal to the caller.
- **Action:** Reclassify API failure as a hard error. Raise on fetch failure unless an explicit fallback policy is defined and tested. If stale data is intentionally acceptable, make that decision explicit with a documented `allow_stale=True` flag and an operator-visible warning log at ERROR level.
- **Verification:** Mock a failed API call and confirm the pipeline either halts or logs a clearly visible ERROR with stale-data context.

---

## P1 — HIGH: FIX BEFORE PRODUCTION DEPLOY

---

### P1-1 — Race Condition: Workdir naming collision under concurrent rendering
- **File:** `state.py:43`
- **Issue:** Working directories are named using `date_str`, which is not unique enough to prevent collisions when multiple episodes render concurrently. Concurrent renders risk writing to the same directory, producing file overwrites and corrupted output.
- **Action:** Replace or augment `date_str` with a UUID or monotonic counter suffix (e.g., `{date_str}_{uuid4().hex[:8]}`). Alternatively, implement a directory-level lock using `fcntl.flock` or a threading lock if concurrency is in-process.
- **Verification:** Spawn three concurrent render processes targeting the same date and confirm all three produce isolated, non-overlapping workdirs.

---

### P1-2 — Law 6 Violation: Duplicate sanitization bypasses canonical `safe_text()`
- **File:** `narration.py:139–156`, `cold_open.py:140`
- **Issue:** Custom inline text sanitization is implemented in both files, bypassing the canonical `safe_text()` function in `helpers.py:278–282`. This creates two divergent sanitization paths that can produce different outputs for identical input, violating Law 6 and creating a maintenance hazard.
- **Action:** Delete all custom sanitization logic in `narration.py:139–156` and `cold_open.py:140`. Replace with direct calls to `helpers.safe_text()`. If `safe_text()` is missing a needed transformation, extend it centrally — never locally.
- **Verification:** Diff the output of both paths against identical test input. Confirm they are identical after refactor. Add a unit test asserting `safe_text()` is the only sanitization entrypoint.

---

### P1-3 — Missing Segment Validation: Empty segment list renders silently
- **File:** `manifest.py:63`
- **Issue:** If the `segments` list in `EpisodeManifest` is empty, no validation error is raised and rendering proceeds, producing empty or broken output with no diagnostic signal.
- **Action:** Add a guard at manifest construction time: raise `ValueError("EpisodeManifest requires at least one segment")` if `segments` is empty or None. Optionally add segment-order validation (e.g., assert cold open precedes narration if both are present).
- **Verification:** Pass an empty segment list and confirm a `ValueError` is raised immediately at manifest instantiation, not at render time.

---

## P2 — MEDIUM: FIX WITHIN SPRINT

---

### P2-1 — Deduplication Fragility: `whoosh_applied` path comparison fails on symlinks
- **File:** `state.py:26`
- **Issue:** The `whoosh_applied` set uses raw resolved paths for deduplication. Symbolic links or alternate path representations pointing to the same file may not deduplicate correctly, allowing duplicate SFX application.
- **Action:** Normalize all paths before insertion using `pathlib.Path.resolve()` consistently. Add a test case with symlinked paths confirming deduplication holds.

---

### P2-2 — Missing Segment Order Enforcement
- **File:** `manifest.py:57–89`
- **Issue:** No validation enforces segment sequencing rules (e.g., cold open before narration, wrap as last segment). Logical misordering will not error — it will silently produce a structurally invalid episode.
- **Action:** Define an optional `SEGMENT_ORDER_RULES` policy and validate against it during manifest construction. At minimum, assert wrap segment (if present) is last.

---

## CYCLE 3 PREREQUISITES

Before treating any item above as fully closed:

| Action | Owner | Priority |
|---|---|---|
| Rotate leaked Gemini API key and provision replacement | Infra | Immediate |
| Resolve GPT-4o quota exhaustion | Infra | Immediate |
| Re-run full 3-model Cycle 3 audit | Audit Lead | Before merge |
| Confirm P0-1 through P0-3 independently validated by at least 2 models | Audit Lead | Before production |

> Until Cycle 3 completes, all scores remain provisional lower bounds. Do not treat the 6/10 overall readiness score as a deployment gate — it is a single-model estimate under degraded audit conditions.