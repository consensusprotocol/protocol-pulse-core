# qwen3.8-27b (qwen/qwen3.8-27b) 29 s finish=stop usage in 9796 / out 1899 usd_reported=0.001810 usd~0.058 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261116_1325
# Reviewer: Heimdall (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and Gemma) concluded "No defects found" or focused heavily on the correctness of the mapping logic itself. I missed the **operational safety net** issue that MIMO identified.

*   **MIMO's P1 (Silent Zero-Match):** I correctly identified that `in_pool_ids` handles the mapping, but I failed to recognize that if the mapping fails *entirely* (e.g., due to a schema drift where `mined.ledger_moment_id` is missing from all moments, or the stories file is stale), the pipeline would proceed with zero story angles. In Cycle 1, I viewed the `matched` telemetry as "useful for debugging" but did not flag the lack of a *warning* or *halt* condition as a defect. MIMO correctly identified that "missing data never produces a pass" (Law M12) implies that a total failure to match IDs should be loud, not silent.
*   **MIMO's P2 (Aliases Omission):** I noted that `proof_ledger` passes the aliases, but I did not explicitly flag the risk that *other* callers might omit `ledger_aliases` while still providing `stories_path`, leading to a partial silent failure (duplicates not resolved). MIMO caught this.
*   **QWEN's P2 (Order/Determinism):** QWEN raised a point about order. While the code uses file order, the concern was valid enough to warrant explicit confirmation that the output order is deterministic and matches the input file order for auditing purposes.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **MIMO's P1 (Zero Match Silence):** **AGREE.** The Cycle 2 diff addresses this by adding `out["stories"]["warning"]` and logging it when `in_pool` is 0 for all stories. This is the correct "loud" response. It does not HOLD the build (which would be wrong, as story-first is an *extra* source, not the *only* source), but it makes the failure visible in the build log and record.
*   **MIMO's P2 (Parent/Trim Variant Duplication):** **DISAGREE (with context).** MIMO worried that a story line-up could contain two clips of the same speech (parent + trim). The Consensus note clarifies: "every segment needs its own video... a variant shares its parent's video." Since `story_angles` and `story_pool` are unchanged and rely on the existing `lineup_for` logic which enforces unique video IDs, and since a trimmed variant *is* a distinct moment ID (`b1` vs `b1~trim`) but maps to the same *video*, the existing gates (which check video uniqueness) will prevent a line-up from using both if they share the same underlying video asset. If they are distinct video assets (e.g., different cuts), then they are distinct moments and valid. The `in_pool_ids` function correctly returns both IDs if both are in the pool. The downstream logic handles the video constraint. No change needed here.
*   **MIMO's P2 (Aliases Omitted):** **AGREE.** The Cycle 2 diff adds `out["stories"]["aliases"] = len(alias) if ledger_aliases is not None else "not supplied"`. This makes the state explicit.
*   **MIMO's P3 (Inputs None):** **DISAGREE.** `build_inputs` in `ledger_build.py` always returns a dict. `inputs` is not `None` in the production path. The test harness `proof_ledger.py` uses `inputs.get(...)`. This is safe.
*   **GEMMA's "No Defects":** **PARTIALLY DISAGREE.** Gemma missed the operational safety net (P1) and the alias visibility (P2). The code was *logically* correct for the happy path, but *operationally* fragile for the sad path.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] The `warning` logic relies on `in_pool` being 0 for *all* stories.**
Line 57: `if stories and not any(r["in_pool"] for r in out["stories"]["matched"]):`
This is correct. If *any* story has *any* ID in the pool, no warning is issued. This is the right threshold. A partial match is normal (some moments held at Step A). A total mismatch is the defect.

**[P3] `pool_lids` calculation includes `None` removal.**
Line 50: `pool_lids = {(m.get("mined") or {}).get("ledger_moment_id") for m in moments} - {None}`
This is robust. It handles moments without `mined` or without `ledger_moment_id`.

**[P3] Test Coverage for the Warning.**
Line 130: `self.assertIn("NO ID OF THE STORIES FILE NAMES A MOMENT OF THIS BUILD'S POOL", out["stories"]["warning"])`
The test explicitly verifies the warning is present when build IDs are used in the stories file (which won't match ledger IDs). This is a strong test.

**[P3] Test Coverage for "Not Supplied" Aliases.**
Line 131: `self.assertEqual(out["stories"]["aliases"], "not supplied")`
The test verifies the alias state is recorded when `ledger_aliases` is not passed.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| **Mapping Logic** | 9/10 | 10/10 | Confirmed correct. Handles variants, aliases, and unknowns. |
| **Operational Safety** | 6/10 | 9/10 | Cycle 1 lacked a warning for total mismatch. Cycle 2 adds `warning` and `aliases` state. |
| **Test Coverage** | 8/10 | 9/10 | Cycle 2 tests explicitly verify the warning and alias state. |
| **Integration** | 9/10 | 9/10 | No changes needed. `proof_ledger` is the only caller. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.
**P1 HIGH:** None. (MIMO's P1 is resolved by the warning/log in Cycle 2).
**P2 MEDIUM:**
1.  **Verify Downstream Video Uniqueness:** Confirm that `story_angles`/`lineup_for` correctly rejects line-ups where two moments (e.g., `b1` and `b1~trim`) share the same `video_id`. The Consensus says this is handled, but it is outside the diff. *Action: No code change in this diff, but ensure the existing gate is active.*
2.  **Monitor `stories.warning`:** The warning is logged, but is it surfaced in the UI/Dashboard? If not, it may still be "silent" to the operator. *Action: Ensure the build log is monitored or the warning is pushed to the alerting system.*

**P3 NIT:**
1.  **Docstring for `in_pool_ids`:** The docstring is excellent. No change needed.
2.  **Variable Naming:** `pool_lids` is clear. `alias` is clear.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The addition of the **`stories.warning`** and **`stories.aliases`** fields in the build record (lines 52-60) is the highest-leverage change. It transforms a silent, invisible failure mode (the exact defect that caused builds 41-57 to fail) into a loud, auditable signal. This allows operators to immediately distinguish between "story-first didn't fire because moments were held" (normal) and "story-first didn't fire because IDs don't match" (defect).

## 7. PRODUCTION READY?

**Yes.**

**Conditions:**
1.  The `warning` log line must be visible in the standard build monitoring/alerting pipeline. If the build log is not monitored, the warning is still "silent" to the human.
2.  Confirm that `proof_ledger.py` is the *only* production caller of `build()` with `stories_path`. If other callers exist, they must also pass `ledger_aliases` or accept the "not supplied" state.

P1_OR_WORSE: 0