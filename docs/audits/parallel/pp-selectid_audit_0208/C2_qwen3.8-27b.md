# qwen3.8-27b (qwen/qwen3.8-27b) 57 s finish=stop usage in 14453 / out 1871 usd~0.071 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0208

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the core architectural shift (one window per moment) and the dedup logic. However, I missed the **critical inconsistency in failure modes** between the lookup sites, which was the primary P1 finding from GLM and Qwen.

*   **The `.get()` vs `[]` Divergence:** I noted that `speakers.py` used `.get()` but did not fully trace the consequence: if a `source_key` is missing or invalid, `speakers.py` would pass `None` to `attribute()`, potentially resulting in a silent "unknown" speaker (fail-open) rather than a crash (fail-closed). `package.py` and `context_integrity.py` used direct indexing `[]`, which raises `KeyError` (fail-closed). This inconsistency is a violation of Law L-j (fail closed) in the speaker path.
*   **The "Three Copies" Problem:** I did not explicitly flag that the lookup logic (`sources[x.get("source_key") or x["video_id"]]`) was duplicated in three places with slightly different implementations. This is a maintenance hazard.
*   **Report Schema Break:** I missed that `report["window_records"]` changed from `{vid: path}` to `{vid: [paths]}`. While the diff shows internal logging is updated, any external consumer (e.g., a dashboard or driver script not in the diff) expecting a string would break.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-FLASH:** **Agree** on the P1 regarding the inconsistent lookup semantics. The fix in the provided diff (introducing `source_for` in `context_integrity.py` and using it everywhere) directly addresses this. I agree that `speakers.py` catching `KeyError` and returning "unknown" is the correct fail-closed behavior for a speaker attribution (it doesn't claim a name, it just doesn't measure).
*   **GROK-4.20:** **Disagree** with "No findings." Grok missed the `.get()` vs `[]` inconsistency entirely. It also missed the report schema change. Its "SHIP: yes" was premature based on the Cycle 1 code.
*   **QWEN3.8-27B:** **Agree** on the P1s. Qwen correctly identified that `speakers.py` passing `None` was a fail-open risk. The fix in the diff (using `source_for` and catching `KeyError`) resolves this. Qwen's P2 on the report schema is valid but low-risk if no external consumers exist.

## 3. NEW FINDINGS FROM THIS REVIEW

**P2 — `source_for` is defined in `context_integrity.py` but imported in `speakers.py` and `package.py`.**
*   **File:** `pipeline/context_integrity.py:9`, `pipeline/speakers.py:275`, `pipeline/package.py:228`
*   **Scenario:** `package.py` defines `src_of` which calls `CI.source_for`. `speakers.py` imports `CI` inside the function. This is fine, but it creates a dependency of `speakers` on `context_integrity`. If `context_integrity` has heavy imports or side effects, this could be a performance or circular dependency issue. However, since `context_integrity` is a core module, this is likely acceptable.
*   **Verdict:** No defect, but worth noting.

**P2 — `window_waiting` count logic.**
*   **File:** `pipeline/ledger_build.py:195`
*   **Scenario:** `report["window_waiting"] += waiting` is only incremented if `windows > 0` (i.e., at least one row for this video had a window record). If a video has *no* window records at all, `waiting` is not added to `window_waiting`; instead, the rows are counted in `no_word_record`. This is consistent with the docstring ("rows of a window video with no window record of their own"), but the distinction between "video has no windows" and "video has windows but this row doesn't" is subtle. The report keys `no_word_record` and `window_waiting` are distinct, which is good.
*   **Verdict:** Correct behavior, but the logic is slightly complex.

**P1 — `source_for` uses `x.get("source_key") or x["video_id"]`.**
*   **File:** `pipeline/context_integrity.py:13`
*   **Scenario:** If `source_key` is an empty string `""`, `or` will fall back to `video_id`. This is the intended behavior for full-video moments (which don't have a `source_key`). However, if a window moment *accidentally* has an empty `source_key`, it will fall back to `video_id`, which will raise `KeyError` (since window sources are keyed by `vid@...`). This is fail-closed, so it's safe. But it means an empty `source_key` is treated the same as a missing one. This is acceptable.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Lookup Consistency** | 7/10 | 9/10 | The introduction of `source_for` in `context_integrity.py` and its use in all three sites (`package`, `speakers`, `context_integrity`) resolves the P1 inconsistency. The fail-closed behavior is now uniform. |
| **Dedup Logic** | 8/10 | 9/10 | The time-overlap dedup (`a < sp.end and sp.start < b`) is correct. The test `test_each_moment_reads_its_own_window_and_the_same_speech_twice_is_one_moment` verifies that two windows with the same speech result in one moment. |
| **Report Schema** | 6/10 | 8/10 | The change to `{vid: [paths]}` is a breaking change for external consumers, but the internal logging is updated. The risk is low if no external consumers exist. |
| **Test Coverage** | 8/10 | 9/10 | The new tests cover the key scenarios: one window per moment, dedup of same speech, and fail-closed behavior for missing `source_key`. |

## 5. FINAL PRIORITY LIST

*   **P0 CRITICAL:** None.
*   **P1 HIGH:** None. The P1s from Cycle 1 (lookup inconsistency) have been resolved in the provided diff.
*   **P2 MEDIUM:**
    1.  **Report Schema Change:** `report["window_records"]` is now `{vid: [paths]}`. Verify that no external consumers (drivers, dashboards) expect a string. If they do, they will break. (File: `pipeline/ledger_build.py:148`)
    2.  **`source_for` Dependency:** `speakers.py` and `package.py` now depend on `context_integrity.source_for`. Ensure this does not introduce circular imports or performance issues. (File: `pipeline/context_integrity.py:9`)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The introduction of `source_for` in `context_integrity.py` as the single source of truth for Source lookup is the highest-leverage change. It eliminates the risk of inconsistent failure modes (fail-open vs. fail-closed) across the codebase, which was the primary P1 finding from Cycle 1.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Verify External Consumers:** Confirm that no external code (drivers, dashboards, scripts) reads `report["window_records"]` and expects a string. If they do, they must be updated to handle a list.
2.  **Run Full Test Suite:** Ensure that the 11 offline suites and 234 tests pass, as stated in the consensus. The new tests in `test_ledger_build.py` are critical for verifying the one-window-per-moment behavior.
3.  **Monitor `window_waiting`:** In production, monitor the `window_waiting` count in the report. A high count may indicate that the word-pass worker is not generating window records for all moments, which could lead to a loss of moments.