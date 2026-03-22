## CYCLE 2 FINAL REVIEW — assembler-v2-rebuild

## 1) What they caught that I missed

A few important things the other models surfaced that I agree I underweighted or missed:

- **Multi-process cache locking is not safe** in `data_segment.py` / `state.py`.  
  `threading.Lock()` only protects threads in one process, not multiple workers. That is a real concurrency bug if renders happen across processes.

- **`Segment.filler_result()` can return `path=None`**, violating the `RenderedSegment` docstring invariant and enabling silent segment omission during concat.  
  This is a major correctness issue.

- **Concat silently skips missing segment outputs** in `episode.py:143`.  
  That means a badly failed segment can disappear from the final episode instead of forcing a hold.

- **Double degradation accounting** in `narration.py` on post-publish contract failure.  
  `ctx.mark_degraded(...)` is called, then `filler_result()` calls it again.

- **Preflight runs before `EpisodeContext.create()`** and checks `output_dir`, not the actual episode workdir.  
  Not catastrophic, but architecturally wrong.

- **Large encode-path duplication** across most segment classes instead of using `ffmpeg_core.encode.encode_segment()`.  
  This is a maintainability and consistency problem, and it directly affects fallback robustness.

- **ElevenLabs call sites lack rate limiting / quota guardrails** and hardcode the same `voice_id` in 3 files.  
  That’s a real production-risk issue.

## 2) Where I agree or disagree

### A. Multi-process metrics cache race
**Agree.**  
`ctx.metrics_lock` in `state.py:37` is process-local only. If this runs under multiple workers, `metrics_cache.json` can be concurrently refreshed by multiple processes. `os.replace()` helps atomic replacement, but it does not prevent duplicate refreshes or read/write contention patterns. This should be fixed with a file lock or centralized cache.

### B. Massive encode duplication / bypass of `encode_segment`
**Agree strongly.**  
Only `transition.py` and `wrap.py` use the centralized encoder. The rest duplicate temp-file handling, contract checks, rename logic, and fallback behavior. This is the biggest structural quality issue in the codebase.

### C. `probe.py` uses direct `subprocess.run` and brittle stderr parsing
**Partially agree.**  
Yes, it is inconsistent with the “all ffmpeg through `run_ffmpeg`” philosophy. But for probe-style commands that need stderr parsing, direct subprocess use is understandable. The real issue is brittleness of parsing, especially in `measure_lufs()`. I’d classify this as medium priority, not top-tier.

### D. `preflight.py` formatting is poor
**Agree, but low priority.**  
It is ugly and harder to audit. That matters, but it’s not a ship blocker by itself.

### E. `filler_result()` can leave no output file
**Agree strongly.**  
This is one of the most important correctness defects.

### F. Silent truncation of failed segments in final concat
**Agree strongly.**  
This is a production blocker. Missing required content should never be silently omitted.

### G. `encode_segment()` return contract is misleading
**Agree.**  
Returning `(False, False, summary, ms)` even when filler was successfully written is semantically confusing. It works if every caller is careful, but it’s easy to misuse.

### H. `TransitionSegment` duration reporting inaccurate
**Agree.**  
Minor issue, but real.

### I. `NarrationSegment` double degradation accounting
**Agree strongly.**  
This directly distorts episode verdicting.

### J. `ffprobe_contract()` audio/video codec check nesting issue
**Partially agree.**  
The current placement of the video codec check inside the `audio` branch is sloppy and weakens diagnostics. But because missing audio already fails contract, it won’t usually create a false pass. Still should be cleaned up.

### K. `normalize_pip_preview()` does not validate output contract
**Agree.**  
It should at least verify the expected no-audio preview format or a dedicated preview contract. Right now success is “ffmpeg exited and file exists,” which is weak.

### L. ElevenLabs rate limiting absent
**Agree strongly.**  
This is a real operational and cost-control issue.

### M. Hardcoded ElevenLabs voice ID
**Agree.**  
Easy fix, worthwhile.

## 3) New findings from this review

Here are issues I did not see called out clearly in the Cycle 1 outputs provided:

### N1 — `EpisodeRunner` returns `manifest.episode_id` on fatal top-level exception, but successful runs use `ctx.episode_id`
- **Files:** `episode.py:75-80`, `episode.py:108`, `episode.py:249-250`
- **Issue:** The report’s `episode_id` is inconsistent depending on failure timing. `EpisodeManifest` has its own `episode_id`, but `EpisodeContext.create()` generates a new one. That makes tracing and operator debugging harder.
- **Impact:** Observability / auditability issue.
- **Fix:** Use one canonical episode ID. Prefer manifest ID or pass manifest ID into `EpisodeContext.create()`.

### N2 — `EpisodeContext.verdict()` likely has a policy bug: too many degraded segments returns `DEGRADED`, not `HOLD`
- **Files:** `state.py:72-83`
- **Issue:** If `degraded_count > QC_MAX_DEGRADED_SEGMENTS`, verdict is `"DEGRADED"`, not `"HOLD"`. Given the constants naming (`QC_MAX_DEGRADED_SEGMENTS`), this reads like a threshold breach, not a soft warning.
- **Impact:** Episodes can exceed the configured max degraded segments and still ship.
- **Fix:** Clarify policy. If “max” means hard cap, return `HOLD`.

### N3 — `signal_active.py` leaks temp artifacts and may reuse stale intermediate files
- **Files:** `signal_active.py:187-223`
- **Issue:** Generated `top_path`, `bot_path`, `gap`, `concat_file`, and `out` are left in `ctx.segment_dir()`. That may be acceptable per-episode, but there’s no cleanup and no uniqueness beyond `idx`, so reruns in the same workdir could reuse stale files.
- **Impact:** Debug clutter, possible stale artifact confusion.
- **Fix:** Use temp names or clean intermediates after success.

### N4 — `SocialSegment._render_cards()` computes `ts` but never uses it
- **Files:** `social.py:321`
- **Issue:** Dead local variable.
- **Impact:** Minor code smell; suggests unfinished rendering logic.

### N5 — `x_spaces_segment.py` computes `btc_str` and never uses it
- **Files:** `x_spaces_segment.py:140`
- **Issue:** Dead variable; likely intended for footer attribution.
- **Impact:** Minor, but indicates incomplete implementation.

### N6 — `ffprobe_streams()` does not check `returncode` before `json.loads(r.stdout)`
- **Files:** `helpers.py:64-74`
- **Issue:** On ffprobe failure with empty stdout, exception is swallowed and `{}` returned, which is okay. But explicit returncode checking would improve diagnostics and logging.
- **Impact:** Low-medium observability issue.

## 4) Revised scores

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---:|---:|---|
| Correctness | 7.0 | 6.0 | Silent segment omission, filler invariant break, double degradation counting, and verdict-policy ambiguity are more serious than I initially weighted. |
| Law Compliance | 9.0 | 9.0 | Still broadly compliant with the stated laws. Most issues are correctness/ops, not direct law violations. |
| Security | 7.0 | 7.0 | No major change. Main concerns remain subprocess usage, external API dependence, and operational controls rather than classic appsec flaws. |
| Backend Quality | 7.0 | 6.0 | Encode-path duplication, inconsistent IDs, weak cache concurrency model, and brittle probing reduce maintainability. |
| Overall | 7.3 | 6.4 | Good intent and many robust patterns, but not production-ready without fixing the failure-path correctness issues. |

## 5) Final priority list

## P0 CRITICAL

### P0.1 Silent omission of failed segments from final episode
- **Files:** `episode.py:143-153`, `segments/base.py:32-60`
- **Problem:** A segment can fail so badly that `RenderedSegment.path=None`, and concat simply skips it.
- **Required change:** Enforce invariant that every segment result must have a real output file, or immediately HOLD if any segment output is missing. Do not silently drop segments.

### P0.2 `filler_result()` does not guarantee a file
- **Files:** `segments/base.py:36-60`
- **Problem:** Even fallback may return `path=None`.
- **Required change:** Write filler via temp file + atomic rename, verify contract or at least existence/size, and if emergency fallback also fails, abort episode with explicit HOLD path rather than returning a missing segment.

### P0.3 Double degradation accounting in narration
- **Files:** `segments/narration.py:53-57`, `segments/base.py:56`
- **Problem:** One failure increments degraded metrics twice.
- **Required change:** Remove the explicit `ctx.mark_degraded(...)` before `filler_result()`.

### P0.4 Metrics cache locking is not safe across processes
- **Files:** `state.py:37`, `segments/data_segment.py:83-90`
- **Problem:** `threading.Lock` is not enough under multi-worker deployment.
- **Required change:** Use file locking or centralized cache/lock.

### P0.5 ElevenLabs calls need rate limiting / quota protection
- **Files:** `segments/social.py:87-112`, `segments/signal_active.py:176-226`, `segments/x_spaces_segment.py:85-116`
- **Problem:** Unbounded external TTS calls can blow quota/cost and degrade unpredictably.
- **Required change:** Add shared limiter + per-episode cap + explicit quota-error logging.

## P1 HIGH

### P1.1 Refactor all segment encodes through `encode_segment()`
- **Files:** `segments/cold_open.py`, `segments/narration.py`, `segments/partner_clip.py`, `segments/data_segment.py`, `segments/social.py`, `segments/signal_active.py`, `segments/x_spaces_segment.py`
- **Problem:** Duplicated encode/fallback logic is inconsistent and bug-prone.
- **Required change:** Centralize.

### P1.2 Preflight should be episode-scoped
- **Files:** `episode.py:94-108`
- **Problem:** Preflight runs before context creation and checks `output_dir`, not actual workdir.
- **Required change:** Create context first or split preflight into global and episode-scoped phases.

### P1.3 Clarify/fix verdict policy for degraded segment threshold
- **Files:** `state.py:78-83`
- **Problem:** Exceeding `QC_MAX_DEGRADED_SEGMENTS` returns `DEGRADED`, not `HOLD`.
- **Required change:** Align implementation with policy intent.

### P1.4 Unify canonical episode ID
- **Files:** `manifest.py:59`, `state.py:43-53`, `episode.py:75-80`, `episode.py:249-250`
- **Problem:** Manifest ID and context ID diverge.
- **Required change:** Use one ID end-to-end.

### P1.5 `ffprobe_contract()` structure should be cleaned up
- **Files:** `helpers.py:116-142`
- **Problem:** Video codec check is nested under audio branch; diagnostics are weaker than they should be.
- **Required change:** Validate video and audio independently.

## P2 MEDIUM

### P2.1 Extract ElevenLabs voice ID to config/constant
- **Files:** `segments/social.py:98`, `segments/signal_active.py:183`, `segments/x_spaces_segment.py:97`

### P2.2 Validate normalized PiP output more strictly
- **Files:** `helpers.py:238-279`

### P2.3 Improve probe robustness / logging
- **Files:** `ffmpeg_core/probe.py:6-83`, `helpers.py:64-74`

### P2.4 Clean up temp/intermediate artifacts in signal/social flows
- **Files:** `segments/signal_active.py:187-223`, `segments/social.py:235-240`

### P2.5 Reformat `preflight.py`
- **Files:** `preflight.py:1-52`

### P2.6 Remove dead locals / incomplete remnants
- **Files:** `social.py:321`, `x_spaces_segment.py:140`

## 6) The single highest-leverage change

**Make segment output a hard invariant: every segment must always produce a real file or the episode must immediately HOLD—never silently omit failed segments from concat.**

## 7) Production ready?

**No.**

### Conditions required before production:
1. **Fix missing-segment omission** in concat and guarantee filler/output invariants.
2. **Fix double degradation counting** in `narration.py`.
3. **Implement multi-process-safe metrics cache locking**.
4. **Add ElevenLabs rate limiting / quota controls**.
5. **Decide and enforce verdict policy** for degraded-segment threshold.
6. **Preferably refactor all segment encodes through `encode_segment()`** before broad rollout, or at minimum standardize fallback behavior across all segments.

After P0 items are fixed, I’d call it **“Yes with conditions” for limited rollout**. Before that, it is not safe enough for production.