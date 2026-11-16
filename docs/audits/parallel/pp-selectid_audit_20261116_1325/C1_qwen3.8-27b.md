# qwen3.8-27b (qwen/qwen3.8-27b) 69 s finish=stop usage in 8938 / out 2564 usd_reported=0.003123 usd~0.065 (upper-bound price)

I have reviewed the diff for `pp-selectid` against the provided context, governing laws, and the specific defect description.

### Analysis

**1. The Defect and Fix Logic**
The core issue is an ID mismatch: the `stories` file uses **Ledger IDs** (stable, from the ledger build), while the `build` pool uses **Build Moment IDs** (ephemeral, generated per build). The previous code compared them directly, resulting in zero matches.
The fix introduces `in_pool_ids`, which maps Ledger IDs to Build Moment IDs using the `mined.ledger_moment_id` field present in the pool moments. It also handles `aliases` (duplicates) where a dropped ledger row points to a kept one.

**2. Code Review: `pipeline/package.py`**

*   **`in_pool_ids` Function:**
    *   **Indexing:** `idx.setdefault(lid, []).append(mid)` correctly builds a map of `ledger_id -> [build_id, ...]`. This handles the case where multiple build moments (e.g., a parent and a trimmed variant) might share the same ledger ID.
    *   **Resolution Loop:**
        ```python
        for lid in s["moment_ids"]:
            for mid in idx.get(lid) or idx.get((aliases or {}).get(lid)) or []:
                if mid not in ids:
                    ids.append(mid)
        ```
        *   It iterates through the story's ledger IDs.
        *   It checks `idx.get(lid)` first. If the ledger ID exists directly in the pool, it uses those build IDs.
        *   If not, it checks `aliases.get(lid)`. If the ledger ID is a duplicate that was dropped, it resolves to the *kept* ledger ID and looks that up in `idx`.
        *   **Potential Issue (P2):** The logic `idx.get(lid) or idx.get((aliases or {}).get(lid))` relies on `idx.get(lid)` returning a truthy value (non-empty list) to short-circuit. If a ledger ID exists in the index but maps to an empty list (which shouldn't happen given `append`, but theoretically possible if data is malformed), it would fall through to the alias check. However, since `idx` is built by appending, values are always non-empty lists if the key exists. This is safe.
        *   **Deduplication:** `if mid not in ids` ensures unique build IDs in the output. This is correct because a single ledger ID might map to multiple build moments (e.g., original + trim), and we want all of them, but we don't want duplicates if the story lists the same ledger ID twice (unlikely, but safe) or if two different ledger IDs alias to the same kept ID which maps to the same build moment.
    *   **Output:** `dict(s, moment_ids=ids, ledger_ids=list(s["moment_ids"]))`. It preserves the original ledger IDs in `ledger_ids` for auditing/reporting (`stories.matched`) and replaces `moment_ids` with the resolved build IDs for downstream processing (`story_angles`). This is correct.

*   **`build` Function Integration:**
    *   `stories = in_pool_ids(stories, cleared, ledger_aliases)` is called immediately after `read_stories`.
    *   `cleared` is the pool of moments. The function signature `in_pool_ids(stories, pool, aliases)` matches.
    *   `out["stories"]["matched"]` is populated with diagnostic info: `ledger_ids` (count of original IDs) and `cleared` (count of resolved build IDs). This is useful for debugging the "matched nothing" issue.
    *   `story_angles(stories, cleared, passing, max_angles)` is called with the *translated* stories. This is the critical fix.

*   **`ledger_aliases` Parameter:**
    *   Added to `build` signature.
    *   Passed from `proof_ledger.py` as `inputs.get("duplicates_of") or {}`. This correctly sources the alias map from the ledger build report.

**3. Code Review: `tests/package/proof_ledger.py`**
*   Passes `ledger_aliases=inputs.get("duplicates_of") or {}`. This is correct. The `duplicates_of` map in the ledger report is exactly the `aliases` needed.

**4. Code Review: `tests/package/test_medley.py`**
*   **`ledgered` Helper:** Creates moments with `mined.ledger_moment_id` set to `"L" + moment_id`. This simulates the real-world scenario where build IDs differ from ledger IDs.
*   **Test Updates:**
    *   `MS` and `STORY` are updated to use `ledgered` moments and ledger IDs (`"Lh"`, etc.) in the story file.
    *   `test_the_files_ledger_ids_become_this_builds_ids`:
        *   Constructs a pool with explicit `ledger_moment_id` values (`"L1"`, `"L2"`).
        *   Includes a duplicate scenario: `"Ldup"` aliases to `"L2"`.
        *   Story has `moment_ids: ["L3", "Ldup", "L1", "L2"]`.
        *   Expected `moment_ids` in output: `["b2", "b1", "b1~trim"]`.
            *   `"L3"`: Not in pool, not in aliases. Resolves to `[]`.
            *   `"Ldup"`: Not in pool. Alias to `"L2"`. `"L2"` is in pool (`"b2"`). Resolves to `["b2"]`.
            *   `"L1"`: In pool (`"b1"`, `"b1~trim"`). Resolves to `["b1", "b1~trim"]`.
            *   `"L2"`: In pool (`"b2"`). Resolves to `["b2"]`.
            *   Combined & Deduped: `["b2", "b1", "b1~trim"]`.
        *   The test asserts this exact order and content. The order is determined by the iteration of `s["moment_ids"]` and the order of `idx` values.
            *   `L3` -> `[]`
            *   `Ldup` -> `idx["L2"]` -> `["b2"]` (assuming `b2` was added to `idx["L2"]` first).
            *   `L1` -> `idx["L1"]` -> `["b1", "b1~trim"]` (assuming `b1` added before `b1~trim`).
            *   `L2` -> `idx["L2"]` -> `["b2"]` (already in `ids`).
            *   Result: `["b2", "b1", "b1~trim"]`.
        *   This matches the assertion. The test is robust.
    *   Other tests are updated to use `ledgered` and ledger IDs, ensuring the translation path is exercised in all story-first scenarios.

**5. Compliance with Laws**
*   **LAW 20 / M2:** No gate thresholds changed. No reclassification.
*   **M12 FAIL CLOSED:** If `ledger_moment_id` is missing, `lid` is `None`, `idx` won't have it, and the story moment won't be resolved. This leads to fewer/no story angles, which is a safe failure (no incorrect content generated). It does not produce a false pass.
*   **Smallest Diff:** The change is localized to ID translation. No new renderers, selectors, or complex logic introduced.

**6. Potential Issues**

*   **[P2] Order Dependency in `in_pool_ids`:** The order of `moment_ids` in the output depends on the order of `idx` values, which depends on the iteration order of `pool.items()`. In Python 3.7+, dict order is insertion order. If `pool` is a dict, the order is deterministic based on how the pool was built. However, if `pool` is a set or unordered collection, the order could be non-deterministic. The code uses `pool.items()`, implying `pool` is a dict. The test `test_the_files_ledger_ids_become_this_builds_ids` asserts a specific order, which implies the test environment has a deterministic pool order. This is acceptable for a test, but in production, if the order of `moment_ids` matters for downstream logic (e.g., `story_angles` might prioritize the first moment), non-deterministic pool ordering could lead to inconsistent story angles. However, `story_angles` likely sorts or ranks moments, so the initial order might not be critical. Still, it's a minor fragility.
*   **[P3] `ledger_ids` in Output:** The `ledger_ids` field is added to the story dict. This is useful for debugging but increases the size of the story object. Not a defect, just a note.
*   **[P3] `aliases` Parameter Name:** The parameter is named `aliases` in `in_pool_ids` but `ledger_aliases` in `build`. This is consistent enough.

**7. Verification of "Nothing Else Changed"**
The diff only touches:
*   `pipeline/package.py`: Adds `in_pool_ids`, modifies `build` to call it and add `ledger_aliases` param, adds `stories.matched` to output.
*   `tests/package/proof_ledger.py`: Passes `ledger_aliases`.
*   `tests/package/test_medley.py`: Updates tests to use ledger IDs.

No other files are modified. No other logic is changed.

### Findings

1.  **[P2] Non-deterministic Order of Resolved Moment IDs:** The order of `moment_ids` in the output of `in_pool_ids` depends on the iteration order of `pool.items()`. If `pool` is not a dict with a stable insertion order (e.g., if it's reconstructed from a set or database query without `ORDER BY`), the order of moments in a story could vary between runs. While `story_angles` may mitigate this by ranking, it's a potential source of non-determinism. **Recommendation:** Ensure `pool` is a dict with stable order, or sort the resolved `ids` if order is not critical. Given the test asserts a specific order, the current implementation is consistent with the test, but the production code should be verified to use a stable pool order.

2.  **[P3] Missing `ledger_moment_id` Handling:** If a moment in `pool` does not have `mined.ledger_moment_id`, it is simply not indexed. This is correct behavior (fail closed), but it might be worth logging a warning if a significant number of moments lack this field, as it would prevent story-first line-ups. However, this is outside the scope of the diff.

3.  **[P3] Test Coverage for Empty Aliases:** The test `test_the_files_ledger_ids_become_this_builds_ids` covers aliases. There is no explicit test for `aliases=None` or `aliases={}` in `in_pool_ids` directly, but the other tests (e.g., `test_every_swap...`) implicitly cover the case where no aliases are needed (since they use distinct ledger IDs). This is sufficient.

### Conclusion

The fix correctly addresses the ID mismatch defect. The logic is sound, the tests are comprehensive and verify the translation, including edge cases like duplicates and unknown IDs. The change is minimal and compliant with the governing laws. The only minor concern is the potential non-determinism of the output order, which is mitigated by the test's assertion of a specific order, implying a stable pool order in the test environment.

P1_OR_WORSE: 0