# qwen3.8-27b (qwen/qwen3.8-27b) 40 s finish=stop usage in 20800 / out 2283 usd~0.097 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0155
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM-5.3-FLASH (Cycle 1):**
- **P0-1 (slice vs. render divergence):** I missed this in Cycle 1. GLM correctly identified that the pin-stage measurement uses a `_Slice` of the source envelope (10 ms hop, no 20 ms fade-in), while the render measures its own decode of the prepared file. The 10 ms quantization + missing fade means the two gates can disagree at the boundary. **However**, the Cycle 2 diff *implements the fix*: `MARGIN_MS = int(round(SL.HOP_S * 1000))` (line 33) and `need = SL.HEAD_LEAD_MIN_S * 1000 + MARGIN_MS` (line 48). The threshold is now 90 ms, not 80 ms. The test `test_a_lead_within_one_frame_of_80_ms_does_not_pass` (line 417) confirms 85 ms fails and 120 ms passes. **This is resolved.**
- **P0-2 (cache freezes transient failure):** I missed this. The `hk` cache in `build()` (line 252) is keyed by `moment_id` and shared across all `hook_onset_for` calls. If `TT.audio_window` has a transient I/O failure, the fail-closed result is frozen for the entire build. **This is real but low-severity**: it is fail-closed (L-m compliant), and the consensus notes the L-v 2 audio window is disk-cached and deterministic. Downgrade to P2.

**GROK-4.20-0309-REASONING (Cycle 1):**
- No findings. I agree with the "SHIP: yes" verdict, but I would have been more cautious about the slice-vs-render divergence (now fixed) and the cache behavior.

**QWEN3.8-27B (Cycle 1):**
- **P1 (pad double-counted?):** I missed this. QWEN raised the concern that `edge_plan`'s `lead_in_pad_s` might be *included* in the slice, causing double-counting. **The consensus REFUTED this**: `edge_plan` grants the pad only at a file head, and the render adds it *before* the source audio. The slice is the source alone, so the pad is added once. The test `test_a_file_head_hook_counts_the_pad_the_render_adds_once` (line 425) confirms this. **Resolved.**
- **P1 (medley opens with a clip instead of a hook):** I missed this. QWEN worried that if no hook passes G17a, the medley might open with a non-hook clip. **The consensus REFUTED this**: `lineup_for` returns `None` if no hook-able moment passes, so no line-up is produced. The test `test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up` (line 573) confirms this. **Resolved.**

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My Position | Reasoning |
|---|---|---|
| GLM P0-1 (slice vs. render) | **Agree, but resolved** | The Cycle 2 diff adds `MARGIN_MS` to the threshold, making the pin gate stricter than the render gate. A pass at pin (90 ms) guarantees a pass at render (80 ms). The test confirms this. |
| GLM P0-2 (cache freezes transient failure) | **Partially agree** | Real, but fail-closed and low-severity. The audio window is disk-cached and deterministic, so transient failures are unlikely. Downgrade to P2. |
| QWEN P1 (pad double-counted) | **Disagree** | The pad is added once: the slice is the source alone, and the pad is added by the render before the source. The test confirms this. |
| QWEN P1 (medley opens with a clip) | **Disagree** | `lineup_for` returns `None` if no hook passes, so no line-up is produced. The test confirms this. |
| GROK (no findings) | **Partially agree** | GROK missed the slice-vs-render divergence (now fixed) and the cache behavior. But the code is correct as written. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2 — `hook_onset_for` is called in a `ThreadPoolExecutor` with `max_workers=4`, but `TT.audio_window` may not be thread-safe.**
- **File:** `pipeline/package.py:253-256`
- **Scenario:** If `TT.audio_window` writes to `work_dir` or uses shared state, concurrent calls from the thread pool could race. The diff does not show `audio_window`'s implementation, so I cannot verify thread-safety. If it is not thread-safe, the measurement could be corrupted, leading to a wrong `pass`/`measured` result.
- **Mitigation:** The consensus notes the L-v 2 audio window is disk-cached and deterministic, which suggests `audio_window` is read-only after the first call. But this is not verifiable from the diff. Flagging as P2 pending verification.

**P2 — The `hook_onset` row is only added to `inventory` when `hook is not None`, but `hook` is derived from `cleared.get(pk["segments"][0]["moment_id"])`.**
- **File:** `pipeline/package.py:271, 293`
- **Scenario:** If `pk["segments"][0]["moment_id"]` is not in `cleared` (e.g., the moment was dropped after the hook_onset measurement), `cleared.get(...)` returns `None`, and the `hook_onset` row is absent. `package_pin.MEDLEY_GATES` includes `"hook_onset"`, so `to_pin` will refuse the pin (missing required row). This is correct fail-closed behavior, but it means a package can be built and then refused at pin time, with no clear reason in the log.
- **Mitigation:** The `log` at line 260-261 reports how many moments can open a medley, but does not log which specific moments were dropped. Adding a log line for the missing `hook_onset` row would improve debuggability. Flagging as P2.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `hook_onset.py` | 8/10 | 9/10 | The `MARGIN_MS` fix resolves the slice-vs-render divergence. The pad handling is correct. The only remaining concern is thread-safety of `audio_window` (P2). |
| `package.py` | 7/10 | 8/10 | The `hook_onset_for` cache is fail-closed and correct. The `lineup_for` filter is correct. The `inventory` row is correct. The only remaining concerns are thread-safety (P2) and debuggability of missing `hook_onset` row (P2). |
| `package_pin.py` | 9/10 | 9/10 | No changes. The `MEDLEY_GATES` addition is correct. |
| Tests | 8/10 | 9/10 | The new tests cover the key scenarios: breath+zeros (FAIL), room tone (PASS), boundary (85 ms FAIL, 120 ms PASS), file head pad (PASS), no audio (NOT MEASURED), and the build loop (proposer's hook gives way, no line-up if none pass). The only missing test is for the thread-safety concern (P2). |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. **`hook_onset_for` thread-safety:** `pipeline/package.py:253-256` — Verify that `TT.audio_window` is thread-safe. If it is not, the concurrent calls from the `ThreadPoolExecutor` could race, leading to a wrong `pass`/`measured` result. **Action:** Add a lock or serialize the calls if `audio_window` is not thread-safe.
2. **Debuggability of missing `hook_onset` row:** `pipeline/package.py:271, 293` — If `pk["segments"][0]["moment_id"]` is not in `cleared`, the `hook_onset` row is absent, and the pin is refused with no clear reason in the log. **Action:** Add a log line when the `hook_onset` row is missing.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `MARGIN_MS` fix in `hook_onset.py` (line 33, 48) is the highest-leverage change: it resolves the slice-vs-render divergence by making the pin gate stricter than the render gate, ensuring that a pass at pin guarantees a pass at render. This prevents the 01:39 failure mode (a package pinned and then held at render) and is confirmed by the test `test_a_lead_within_one_frame_of_80_ms_does_not_pass`.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Verify thread-safety of `TT.audio_window`:** If it is not thread-safe, add a lock or serialize the calls in `hook_onset_for` (P2).
2. **Add a log line for the missing `hook_onset` row:** If `pk["segments"][0]["moment_id"]` is not in `cleared`, log the reason (P2).

If these conditions are met, the code is production-ready. The G17a check at the pin stage is correct, fail-closed, and prevents the 01:39 failure mode. The tests cover the key scenarios, and the `MARGIN_MS` fix resolves the slice-vs-render divergence.