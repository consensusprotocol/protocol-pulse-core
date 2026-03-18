# CONSENSUS REPORT — ASSEMBLER-V2-REBUILD — CYCLE 1
Generated: 2026-03-18 02:28
Models: Grok-3 (+2 failed: Gemini 2.5 Pro — API key leaked/revoked; GPT-4o — quota exhausted)

---

> **⚠️ AUDIT INTEGRITY NOTICE**
> This consensus was produced from a **single-model review**. Gemini 2.5 Pro and GPT-4o both failed before producing output. All findings below originate exclusively from Grok-3. The "Unanimous," "Majority," and "Conflict" sections are structurally preserved but honestly annotated to reflect single-source confidence. Treat every finding as **single-model confidence**, not multi-model consensus. A Cycle 2 re-audit with all three models operational is strongly recommended before merging to main.

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | ❌ N/A | ❌ N/A | 6/10 | 6/10 (single source) |
| Law Compliance | ❌ N/A | ❌ N/A | 7/10 | 7/10 (single source) |
| Security | ❌ N/A | ❌ N/A | 7.5/10 | 7.5/10 (single source) |
| Frontend Quality | ❌ N/A | ❌ N/A | N/A (no FE code) | N/A |
| Overall Readiness | ❌ N/A | ❌ N/A | 6.5/10 | 6.5/10 (single source) |

> Scores are estimated from Grok's qualitative descriptions, as no explicit numerical scores were provided. Gemini and GPT-4o produced zero output.

---

## UNANIMOUS FINDINGS (all 1 active models agree — implement unconditionally)

These are findings where the one functioning model provided clear, specific, citable evidence. Given single-source status, "unconditional" means: **the cited code evidence is concrete enough to fix regardless of multi-model confirmation.**

---

### U-1 — Law 2 Violation: CRF-only encoding rule broken
- **What it is:** The governing law explicitly forbids `-b:v`, `-maxrate`, and `-bufsize` alongside `-crf`. All three bitrate parameters are defined and actively passed to FFmpeg.
- **File/Line:** `constants.py:15-17` (definitions), `ffmpeg_core/encode.py:22` (usage alongside `-crf` at line 21)
- **What to change:** Remove `VIDEO_BITRATE`, `VIDEO_MAXRATE`, `VIDEO_BUFSIZE` from `constants.py`. Strip those flags entirely from the FFmpeg command construction in `encode.py`. Use `-crf` alone for quality control. Verify no other call sites reference these constants with `grep -rn VIDEO_BITRATE`.

---

### U-2 — Law 6 Violation: Duplicate drawtext sanitization logic
- **What it is:** `safe_text()` in `helpers.py` is designated the single, canonical sanitizer. Two segments bypass it with custom sanitization, creating an inconsistent attack surface and violating the single-sanitizer law.
- **File/Line:** `narration.py:139-156`, `cold_open.py:140`; canonical function at `helpers.py:278-282`
- **What to change:** Delete the custom sanitization blocks in `narration.py` and `cold_open.py`. Replace with calls to `safe_text()` from `helpers.py`. Audit all remaining segment files for any additional inline sanitization not routed through `safe_text()`.

---

### U-3 — Silent FFmpeg failure propagation
- **What it is:** `run_ffmpeg` returns `False` on failure without propagating error details upward. Higher layers receive a boolean with no diagnostic context. Debugging production failures becomes guesswork.
- **File/Line:** `helpers.py:20-42` (specifically line 40)
- **What to change:** On failure, log the full captured stdout/stderr at `ERROR` level before returning `False`. Consider returning a structured result object (or raising an internal sentinel exception caught at the render boundary) that includes the FFmpeg command, return code, and stderr tail. At minimum, ensure every `False` return is accompanied by a log entry with enough detail to reproduce the failure.

---

### U-4 — Empty manifest: silent no-op instead of explicit failure
- **What it is:** `EpisodeManifest` with an empty `segments` list proceeds through the rendering pipeline producing no content, with no error raised and no early exit. This will produce a blank or broken output in production with no signal.
- **File/Line:** `manifest.py:63` (segments list initialization), `manifest.py:57-89` (class body)
- **What to change:** Add a `__post_init__` or validation method that raises `ValueError` (caught at the orchestration level before any render call) if `segments` is empty. Alternatively, add an explicit guard at the render entry point that calls `filler_result()` and logs a critical error if the manifest contains zero segments.

---

### U-5 — Concurrent episode rendering: workdir collision risk
- **What it is:** `ctx.workdir` is keyed by `date_str` alone. If two episodes render concurrently on the same date (plausible in any queued or parallel execution environment), they share a working directory, causing file overwrites and corrupted outputs.
- **File/Line:** `state.py:43`
- **What to change:** Make workdir unique per episode instance, not per date. Append a UUID or episode ID: e.g., `workdir = base / f"{date_str}_{episode_id}"` or `workdir = base / f"{date_str}_{uuid.uuid4().hex[:8]}"`. Ensure cleanup logic accounts for the new naming scheme.

---

## MAJORITY FINDINGS (2 of 1 active models agree)

**Not applicable in the strict sense** — only one model produced output. This section is preserved for structural completeness. All findings above are effectively "unanimous" within the available data. No finding can be labeled majority with a single source.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

All findings are technically unique (single model). The following are flagged as **highest independent value** — findings that would typically require multi-model confirmation but carry strong intrinsic evidence:

---

### UI-1 — External API rate limiting absent on mempool.space calls
- **Source:** Grok only
- **What it is:** `data_segment.py:35-49` and `83-93` make HTTP calls to `mempool.space` with no rate limiting, no retry logic, and no backoff. Background refresh threads (line 76) can fire independently and compound the issue under load. This risks IP-level bans from the public API and service degradation.
- **File/Line:** `data_segment.py:35-49`, `83-93`, `76`
- **Assessment:** **Implement.** This is a classic production reliability gap. Public APIs with no auth tokens have rate limits; hitting them silently degrades data quality. Add exponential backoff with jitter, a request rate limiter (token bucket or simple time-gated lock), and explicit logging on HTTP errors.

---

### UI-2 — Stale metrics cache: background refresh failures are silent
- **Source:** Grok only
- **What it is:** The background thread responsible for refreshing the metrics cache fails silently (line 76). Stale data served without any warning or log entry makes it impossible to detect how long bad data has been flowing into episodes.
- **File/Line:** `data_segment.py:76`
- **Assessment:** **Implement.** Wrap the background refresh in a try/except that logs at `ERROR` level with timestamp and exception details. Consider writing a `cache_health` flag to `ctx.workdir` so the orchestrator can inspect cache freshness without parsing logs.

---

### UI-3 — `partner_clip.py` short-clip fallback is silently undiagnosable
- **Source:** Grok only
- **What it is:** When a partner clip is under 2 seconds, filler is used — but the actual detected duration is never logged. In production, diagnosing why a partner's clip was silently replaced requires guessing.
- **File/Line:** `partner_clip.py:59-64`
- **Assessment:** **Implement.** One-line fix: log `f"Partner clip duration {actual_duration:.2f}s < 2s minimum; using filler"` before falling back. Low cost, high diagnostic value.

---

### UI-4 — `whoosh_applied` deduplication fragile on symlinked filesystems
- **Source:** Grok only
- **What it is:** `whoosh_applied` (a set of resolved paths) may fail to deduplicate correctly when symbolic links create multiple valid path representations for the same file, resulting in duplicate SFX application.
- **File/Line:** `state.py:26`
- **Assessment:** **Investigate further.** Resolve all paths through `Path.resolve()` consistently before adding to or checking the set. If the Ultron deployment environment uses symlinks (e.g., for asset libraries), this is a real bug. If not, it's theoretical. Add `Path(p).resolve()` normalization as a low-cost defensive measure regardless.

---

### UI-5 — `ffmpeg_core/encode.py` has no retry on transient failures
- **Source:** Grok only
- **What it is:** If encoding fails due to transient resource contention (Ultron server under load, temp disk pressure), it immediately falls back to filler with no retry attempt. A single retry with a short delay would recover from most transient failures without producing filler content.
- **File/Line:** `ffmpeg_core/encode.py:37-39`
- **Assessment:** **Implement.** Add a single retry (1-2 second delay) before filler fallback. Log both the initial failure and the retry outcome. This is a standard resilience pattern with minimal complexity cost.

---

### UI-6 — No test file verification
- **Source:** Grok only
- **What it is:** Law 10 requires all 29 tests to pass before commit. No test files were included in the submission, making compliance unverifiable.
- **Assessment:** **Investigate.** The second pass must explicitly run `regression_test.sh` and attach results to the commit. If tests don't exist, they must be written. This is a blocking law compliance issue.

---

## CONFLICTS (models disagree — your tiebreaker)

**Not applicable.** Only one model produced output. No conflicting positions exist in this cycle.

If Gemini and GPT-4o had run, likely conflict zones based on the nature of the findings would have been:
- Whether the empty manifest issue is a `ValueError` (hard fail) or a `filler_result()` soft fail at the law boundary
- Severity assessment of the workdir collision risk (depends on actual deployment concurrency model)

These should be surfaced as explicit discussion items in Cycle 2.

---

## VALIDATED STRENGTHS (all active models agree this is already excellent)

> **Note:** "All models" = Grok only in this cycle. These are flagged as **do not touch** based on strong positive findings, but should be re-validated by Gemini and GPT-4o in Cycle 2 before being considered truly locked.

---

### VS-1 — Law 1: render() never raises
All segment render methods (`cold_open.py:30-33`, `narration.py:22-26`, and equivalents) correctly catch all exceptions and return `filler_result()`. The no-raise contract is fully honored. **Do not modify this exception handling pattern.**

### VS-2 — Law 4: ffprobe_contract enforcement
`ffprobe_contract` in `helpers.py:74-148` enforces the exact 1920x1080 h264 yuv420p 30fps aac 192k 48000hz stereo spec with full parameter checks. This is correct and complete. **Do not modify the contract validation logic.**

### VS-3 — Law 5: Atomic writes via atomic_rename
`atomic_rename` (`helpers.py:194-207`) is used consistently across all segment writers (`cold_open.py:65`, `narration.py:111`, etc.). File atomicity is correctly implemented throughout. **Do not replace or bypass atomic_rename.**

### VS-4 — Law 7: PiP eof_action=repeat + stream_loop=-1
PiP rendering in `narration.py:72` and `helpers.py:211-252` correctly uses `eof_action=repeat` and `stream_loop=-1` on pre-normalized clips. **Do not alter PiP filter graph construction.**

### VS-5 — Law 8: Metrics cache scoped to ctx.workdir
`data_segment.py:126` correctly scopes the metrics cache to `ctx.workdir/"metrics_cache.json"`, not `/tmp`. **Do not move this to a global temp location.**

### VS-6 — Law 9: Outro -an before stream_loop
`wrap.py:36` correctly strips audio with `-an` before `stream_loop=-1` on the outro branded video. **Do not modify the outro audio stripping logic.**

### VS-7 — Law 3: EpisodeContext episode-scoped, no module globals
`EpisodeContext` is correctly passed as a parameter throughout the codebase with no module-level state globals. **Do not introduce module-level state.**

---

## LAW COMPLIANCE CONSENSUS

| Law | Description | Status | Confidence |
|---|---|---|---|
| Law 1 | render() never raises — filler_result() on any failure | ✅ COMPLIANT | High (Grok, citable lines) |
| Law 2 | CRF-only encoding — no -b:v/-maxrate/-bufsize with -crf | ❌ **VIOLATED** | High (Grok, citable lines) |
| Law 3 | EpisodeContext episode-scoped — no module globals | ✅ COMPLIANT | High (Grok) |
| Law 4 | ffprobe_contract: exact spec enforcement | ✅ COMPLIANT | High (Grok, citable lines) |
| Law 5 | Atomic writes via atomic_rename | ✅ COMPLIANT | High (Grok, citable lines) |
| Law 6 | safe_text() single drawtext sanitizer | ⚠️ **PARTIAL VIOLATION** | High (Grok, citable lines) |
| Law 7 | PiP eof_action=repeat + stream_loop=-1 | ✅ COMPLIANT | High (Grok) |
| Law 8 | Metrics cache scoped to ctx.workdir not /tmp | ✅ COMPLIANT | High (Grok) |
| Law 9 | Outro -an strips audio before stream_loop | ✅ COMPLIANT | High (Grok) |
| Law 10 | All 29 tests pass before commit | ⚠️ **UNVERIFIABLE** | Low (no test files submitted) |

**Final Determination:** 2 laws violated/unverifiable. Code is **not law-compliant** and cannot be committed until Law 2 and Law 6 are fixed and Law 10 is verified.

---

## SECURITY CONSENSUS

| Priority | Issue | Severity | Source |
|---|---|---|---|
| 1 | No rate limiting or retry on mempool.space API calls | Medium-High | Grok |
| 2 | Inconsistent drawtext sanitization (also a security surface) | Medium | Grok |
| 3 | Background refresh thread failures are silent — could mask data poisoning | Low-Medium | Grok |
| 4 | No hardcoded secrets detected | ✅ Clean | Grok |
| 5 | No SQL injection surface detected | ✅ Clean | Grok |
| 6 | No auth bypass surface detected | ✅ Clean | Grok |

**Security Summary:** No critical vulnerabilities found. The primary risk is reliability/availability degradation through undefended external API calls, not confidentiality or integrity breaches. The sanitization inconsistency (Law 6) is the most relevant security surface — FFmpeg filter injection is a real attack class and safe_text() must be the sole gate.

---

## WORLD-CLASS GAP CONSENSUS

> Only items with strong single-model evidence are listed. Multi-model confirmation deferred to Cycle 2. These represent gaps between "working" and "production-grade reliable."

### Gap 1 — Observability: Silent failures at every layer
The codebase has a pervasive pattern of swallowing errors (FFmpeg failures, API failures, cache refresh failures, short-clip fallbacks) without emitting structured log events. A world-class video pipeline has a telemetry layer that records every filler substitution, every API failure, and every encoding retry with enough context to reconstruct what went wrong in any given episode without SSH access to the server.

### Gap 2 — Resilience: No retry anywhere in the stack
Neither FFmpeg encoding nor external API calls have retry logic. World-class pipelines treat transient failures as normal operating conditions, not exceptions. A simple retry-with-backoff decorator applied at the FFmpeg execution layer and the HTTP fetch layer would eliminate the majority of production incidents.

### Gap 3 — Concurrency safety
The workdir collision issue suggests the system was designed for single-episode-at-a-time execution but may be deployed in a context where that assumption breaks. A world-class pipeline explicitly documents its concurrency model and enforces it — either with proper isolation (unique workdirs) or with explicit single-execution guards.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Remove VIDEO_BITRATE/VIDEO_MAXRATE/VIDEO_BUFSIZE flags from FFmpeg command | constants.py:15-17, ffmpeg_core/encode.py:22 | models: Grok (unique, law violation) | Law 2 is an explicit governing rule; bitrate+CRF together produce undefined encoding behavior and violate the spec contract

P0 CRITICAL | Replace custom sanitization in narration.py and cold_open.py with safe_text() | narration.py:139-156, cold_open.py:140, helpers.py:278-282 | models: Grok (unique, law violation) | Law 6 violation; inconsistent sanitization is an FFmpeg filter injection surface and a law breach

P0 CRITICAL | Run regression_test.sh and attach passing results before any commit | All test files | models: Grok (unique, law requirement) | Law 10 is unverifiable; 29 tests must pass; no commit without green suite

P1 HIGH     | Make ctx.workdir unique per episode instance (append UUID or episode_id) | state.py:43 | models: Grok | Concurrent rendering causes file overwrites; any queue-based or parallel execution model triggers this

P1 HIGH     | Add structured error logging to run_ffmpeg before returning False | helpers.py:40 | models: Grok | Silent failures make production debugging impossible; stderr/stdout must be captured and logged at ERROR level

P1 HIGH     | Add rate limiting and exponential backoff to mempool.space API calls | data_segment.py:35-49, 83-93 | models: Grok | Undefended public API calls under load cause IP bans and silent data degradation

P1 HIGH     | Add empty-manifest guard with explicit error path | manifest.py:63 / render entry point | models: Grok | Silent no-op on empty manifest produces broken output with no signal in production

P2 MEDIUM   | Log actual duration before partner_clip filler fallback | partner_clip.py:59-64 | models: Grok | One-line fix; eliminates silent replacement with zero diagnostic trace

P2 MEDIUM   | Wrap background cache refresh thread in try/except with ERROR-level logging | data_segment.py:76 | models: Grok | Silent refresh failures make stale data undetectable; add timestamp + exception details to log

P2 MEDIUM   | Add single retry (1-2s delay) before filler fallback in encode_segment | ffmpeg_core/encode.py:37-39 | models: Grok | Transient FFmpeg failures (resource contention) produce unnecessary filler; one retry recovers most cases

P2 MEDIUM   | Normalize all paths through Path.resolve() before whoosh_applied set operations | state.py:26 | models: Grok | Symlinked asset paths produce duplicate SFX application; resolve() is a defensive one-liner
```

---

## CYCLE 1 VERDICT

**NOT READY for second build pass in current state.**

Two law violations (Law 2, Law 6) are blocking. Law 10 compliance is unverifiable. These are not design-level concerns — they are specific, citable, fixable code issues that must be resolved before the second pass is meaningful.

The architectural foundations are sound: no-raise contract, atomic writes, ffprobe contract enforcement, scoped context, and PiP/outro handling are all correctly implemented. This is not a fundamental rework situation — it is a targeted remediation of 2 hard law violations plus reliability hardening across 6-8 additional issues.

**Additionally:** This audit's confidence is materially reduced by the loss of two models. A Cycle 2 re-audit with all three models operational is recommended after the second build pass, before any production deployment. The single-source findings here are well-evidenced but lack adversarial cross-checking.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/ASSEMBLER_V2_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/assembler-v2-rebuild_CONSENSUS_C1.md.

This is the SECOND PASS for assembler-v2-rebuild.
The first build was reviewed by 1 independent AI model (Grok-3) across 1 cycle.
Gemini 2.5 Pro and GPT-4o both failed to produce output (API key revoked / quota
exhausted). A Cycle 2 re-audit with all three models is planned post-second-pass.

Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Remove VIDEO_BITRATE/VIDEO_MAXRATE/VIDEO_BUFSIZE flags from FFmpeg command | constants.py:15-17, ffmpeg_core/encode.py:22 | Law 2 violation — CRF-only encoding is a governing rule; these flags must be fully removed, not commented out

P0 CRITICAL | Replace custom sanitization in narration.py and cold_open.py with safe_text() | narration.py:139-156, cold_open.py:140 | Law 6 violation — safe_text() from helpers.py:278-282 is the single canonical sanitizer; delete all inline alternatives

P0 CRITICAL | Run regression_test.sh and confirm all 29 tests pass before committing | All test files | Law 10 — no commit without green test suite; if tests are missing, write them first

P1 HIGH | Make ctx.workdir unique per episode (append UUID or episode_id to date_str) | state.py:43 | Concurrent rendering causes workdir collisions and file overwrites

P1 HIGH | Add structured ERROR-level logging (command, returncode, stderr) to run_ffmpeg before returning False | helpers.py:40 | Silent failures are undebuggable in production

P1 HIGH | Add rate limiting and exponential backoff with jitter to mempool.space HTTP calls | data_segment.py:35-49, 83-93 | Undefended public API calls cause IP bans and silent data degradation under load

P1 HIGH | Add empty-manifest guard at render entry point with explicit filler/error path | manifest.py:63 / render entry point | Empty segments list currently produces silent broken output

P2 MEDIUM | Log actual clip duration before partner_clip filler fallback | partner_clip.py:59-64 | Zero-cost observability fix for silent clip replacement

P2 MEDIUM | Wrap background cache refresh in try/except with ERROR log including timestamp and exception | data_segment.py:76 | Stale data is undetectable without this

P2 MEDIUM | Add single retry (1-2s delay) in encode_segment before filler fallback | ffmpeg_core/encode.py:37-39 | Recovers from transient resource contention without producing filler

P2 MEDIUM | Normalize paths through Path.resolve() in whoosh_applied set operations | state.py:26 | Defensive fix against symlink-caused duplicate SFX application