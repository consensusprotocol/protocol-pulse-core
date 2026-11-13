# qwen3.8-27b (qwen/qwen3.8-27b) 70 s finish=stop usage in 16053 / out 2335 usd~0.083 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-selectid-2315

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I correctly identified the `SNAP_WORDS` per-edge logic and the risk of silent meaning changes, but I **missed the specific mechanism** that Grok and GLM highlighted: the interaction between the *ledger's editorial metadata* (scores/risks) and the *expanded span*. I noted the span could grow, but I did not explicitly trace that `M.judge` and `M.record` would run on the *expanded* span while the `mined` dict retains the *original* ledger text, creating a provenance mismatch that the `SNAP_GUARD` (added in this diff) is designed to mitigate.

I also **missed the `word_source` fall-through visibility issue** (GLM P0-2). I focused on the sort order (which is correct) but failed to note that if the *preferred* punctuated record fails its SHA check, the code silently falls back to the verbatim record without incrementing a "degraded source" counter in the report. The report only records the *winner*, not the *rejected preferred candidate*.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Reviewer | My Position | Reasoning |
| :--- | :--- | :--- | :--- |
| **P0: Empty ledger is "quiet"** | Grok | **DISAGREE** (Reframed) | The docstring and code now explicitly state: "An empty successful read is a real result." The adapter *raises* on failure/refusal. An empty list with a report explaining *why* (e.g., "all delivered") is a valid state, not a failure. The test `test_a_failing_or_refusing_adapter_raises_never_an_empty_ledger` confirms this. |
| **P0: Sort order inverted** | Qwen | **DISAGREE** (Refuted) | `key=lambda p: "punct" not in p` yields `False` (0) for punctuated files and `True` (1) for verbatim. `False < True`, so punctuated sorts *first*. The test `test_the_punctuated_record_is_read_first` proves this. |
| **P0: Snap changes meaning** | Grok/GLM | **AGREE** (Mitigated) | The `SNAP_GUARD` regex now blocks snaps that add negations (`not`, `no`, `nobody`) or digits. This addresses the "flipping the claim" risk. However, it does *not* block all semantic shifts (e.g., adding "very" or "almost"), but those are less likely to flip a binary claim. |
| **P1: `word_source` fall-through** | GLM | **AGREE** | If `transcript.whisper_words_punct.json` has a bad SHA, the code tries `transcript.whisper_words.json`. If that passes, it is used. The report does not indicate that the *preferred* source was rejected. This is a visibility gap, not a correctness bug (if the verbatim record is sentence-ready, it is law-compliant), but it violates the "every drop counted" spirit. |
| **P1: `SEARCH_PAD_S` magic number** | Qwen | **AGREE** | 30s is arbitrary. If caption drift exceeds 30s, valid rows are dropped. It is fail-closed (counted as `not_anchored`), so not a P0, but a P1 for robustness. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `SNAP_GUARD` is a blacklist, not a whitelist.**
`ledger_build.py:39-41`: The guard blocks negations and digits. It does *not* block other semantic modifiers (e.g., "almost", "nearly", "actually", "really"). A snap that adds "almost" to "Bitcoin is sound" changes the meaning from a claim to a hedge. The ledger's scores (e.g., `stance: 3`) would be invalid for the hedged version.
*Scenario:* Ledger row: "Bitcoin is sound money." Word record: "Almost Bitcoin is sound money." (Unlikely, but possible in a transcript error). Snap adds "Almost". `SNAP_GUARD` does not match. The moment is built with a hedged claim but scored as a definitive one.
*Fix:* Consider a whitelist of "safe" snap words (e.g., articles, prepositions) or require `anchor_ratio >= 0.9` to ensure the snap is minimal.

**P1-NEW-2: `build_inputs` uses `rs[0]` for `word_source` but iterates all rows for re-anchoring.**
`ledger_build.py:154`: `src, path = word_source(rs[0], ctx, store)`. If `rs[0]` has a different `channel_id` than other rows in `rs` (e.g., a compilation video), the `Source` is built with `rs[0]`'s identity. Other rows are re-anchored against this Source, but their own `channel_id` is not used for the Source. The `mined.ledger_moment_id` preserves the original row, but the `Source` (and thus the credits card) may show the wrong channel.
*Scenario:* Video with two ledger rows: one from "DataDash", one from "Coin Bureau". `rs[0]` is DataDash. Source is built with DataDash. Coin Bureau row is re-anchored and recorded with DataDash's channel in the Source. Credits card shows DataDash for a Coin Bureau clip.
*Fix:* Verify that the ledger guarantees one channel per video. If not, build a Source per row or validate that all rows in `rs` share the same `channel_id`.

**P2-NEW-1: `proof_ledger.py` hardcodes `DELIVERED_PINS` paths.**
`proof_ledger.py:231-232`: The paths to the two delivered pins are hardcoded. If the pins are moved or renamed, the driver will fail. The `--delivered` argument allows overriding, but the default is fragile.
*Fix:* Use a config file or environment variable for the default delivered pins.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **`rows()` adapter** | 8/10 | 9/10 | The "empty ledger" concern is resolved by the docstring and tests. The fail-closed behavior is robust. |
| **`word_source()`** | 7/10 | 8/10 | The sort order is correct. The SHA check is robust. The fall-through visibility gap is a minor P1. |
| **`reanchor()`** | 6/10 | 8/10 | The `SNAP_GUARD` addresses the most critical meaning-change risks (negations/digits). The remaining risk (other modifiers) is lower probability. |
| **`build_inputs()`** | 7/10 | 8/10 | The counted drops are comprehensive. The `rs[0]` channel identity issue is a P1 but likely mitigated by ledger invariants. |
| **Tests** | 8/10 | 9/10 | The tests cover the key scenarios: sort order, SHA check, snap guard, adapter failure. The missing test for the `rs[0]` channel issue is a gap. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None. The previous P0s are refuted or mitigated.

**P1 HIGH**
1.  **`SNAP_GUARD` is a blacklist, not a whitelist.** (`ledger_build.py:39-41`)
    *   *Risk:* A snap that adds a semantic modifier (e.g., "almost") changes the meaning without being blocked.
    *   *Fix:* Add a whitelist of safe snap words or require `anchor_ratio >= 0.9`.
2.  **`build_inputs` uses `rs[0]` for `word_source` channel identity.** (`ledger_build.py:154`)
    *   *Risk:* If a video has multiple channels, the Source may have the wrong channel identity for some rows.
    *   *Fix:* Validate that all rows in `rs` share the same `channel_id` or build a Source per row.
3.  **`word_source` fall-through is not counted.** (`ledger_build.py:91-107`)
    *   *Risk:* If the preferred punctuated record is rejected, the report does not indicate this.
    *   *Fix:* Add a counter for "preferred source rejected" in the report.

**P2 MEDIUM**
1.  **`SEARCH_PAD_S` is a magic number.** (`ledger_build.py:44`)
    *   *Risk:* If caption drift exceeds 30s, valid rows are dropped.
    *   *Fix:* Document the rationale or make it configurable.
2.  **`proof_ledger.py` hardcodes `DELIVERED_PINS` paths.** (`proof_ledger.py:231-232`)
    *   *Risk:* Fragile if pins are moved.
    *   *Fix:* Use a config file or environment variable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Replace the `SNAP_GUARD` blacklist with a whitelist of "safe" snap words (e.g., articles, prepositions) or require `anchor_ratio >= 0.9` to ensure the snap is minimal.** This directly addresses the core risk of the re-anchor logic: that the snap could change the meaning of the moment in a way that invalidates the ledger's editorial judgment.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  **Address P1-1:** Either expand `SNAP_GUARD` to block all semantic modifiers or require `anchor_ratio >= 0.9`.
2.  **Address P1-2:** Validate that all rows in `rs` share the same `channel_id` or build a Source per row.
3.  **Address P1-3:** Add a counter for "preferred source rejected" in the report.

If these conditions are met, the code is robust, fail-closed, and law-compliant. The tests are comprehensive, and the remaining risks are low-probability edge cases.