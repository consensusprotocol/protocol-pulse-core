# gemma-4-31b-it (google/gemma-4-31b-it) 166 s finish=stop usage in 9436 / out 1767 usd_reported=0.000512 usd~0.055 (upper-bound price)

The code implements a fix for a defect where the `stories` file (using Ledger IDs) failed to match the current build's moments (using Build IDs).

### Analysis

1.  **Mapping Logic (`in_pool_ids`)**:
    *   The function correctly builds an index of `ledger_moment_id` $\rightarrow$ `build_id`.
    *   It handles **trimmed variants** by allowing multiple build IDs to map to a single ledger ID (`idx.setdefault(lid, []).append(mid)`).
    *   It handles **duplicates** via the `aliases` (duplicates_of) map: `idx.get(lid) or idx.get((aliases or {}).get(lid)) or []`. This ensures that if a ledger row was dropped as a duplicate, the kept row's build ID is used.
    *   It preserves the original file IDs in `ledger_ids` for auditing and ensures `moment_ids` contains only valid build IDs present in the current `cleared` pool.

2.  **Integration**:
    *   The `build` function now accepts `ledger_aliases` and applies the translation immediately after reading the stories file. This ensures that subsequent calls to `story_angles` and `story_pool` operate on the correct internal IDs.
    *   The addition of `out["stories"]["matched"]` provides the necessary telemetry to verify how many moments from the stories file were actually found in the current build.

3.  **Test Verification**:
    *   `test_the_files_ledger_ids_become_this_builds_ids` is a high-quality test. It explicitly verifies:
        *   Standard mapping.
        *   Trimmed variants (one ledger ID $\rightarrow$ multiple build IDs).
        *   Alias resolution (duplicate ledger ID $\rightarrow$ kept ledger ID $\rightarrow$ build ID).
        *   Fail-closed behavior for IDs not in the pool.
        *   The specific failure case: verifying that providing build IDs in the stories file (instead of ledger IDs) results in no match, confirming the translation is mandatory and functioning.
    *   Existing story-first tests were updated with the `ledgered()` helper to reflect the real-world data structure (`mined.ledger_moment_id`).

4.  **Governing Laws**:
    *   The change is a targeted fix for ID resolution and does not modify the Sentence Law, Selection Lock, or any rendering/QA gates.
    *   It adheres to the "Smallest diff" principle.

### Findings

No defects found. The implementation correctly resolves the ID mismatch between the receipts session and the build process.

P1_OR_WORSE: 0