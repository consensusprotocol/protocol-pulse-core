# gemma-4-31b-it (google/gemma-4-31b-it) 247 s finish=stop usage in 19190 / out 5244 usd_reported=0.001245 usd~0.136 (upper-bound price)

The code implements **RULING 141 (3)**, introducing a "soft failure" mechanism for the line-up selection process. It allows candidates with minor defects (low clip ratings or certain unbridged joins) to be "kept" and potentially "accepted" as "FLAGGED" rather than "FAILED," provided they stay within a total flag cap of 3.

### Audit Findings

#### 1. Logic and Law Compliance
- **Hard vs. Soft Failures**: The implementation correctly preserves HARD failures. In `lineup_soft` and `coherence_soft`, the absence of a through-line, a hook failing its own bar, or a coherence VO point below the floor results in `None`, ensuring these candidates are never "kept" or "accepted."
- **Ruling 37 (Question Hooks)**: The logic in `lineup_soft` and `ly_shape` correctly handles the "no bridge after a question" rule. By designating the first join of a question hook as a `soft_join`, the code prevents the bridge from being placed there while allowing the candidate to be accepted as "FLAGGED."
- **The "One Doubt" Rule**: The implementation of `coherence_soft` (using the `done` parameter) and `coherence_sentences` (checking the `chain` of medley failures) correctly ensures that a clip weak in both medley and coherence is counted as one flag and described by one sentence.
- **Flag Cap**: `seg_marks` correctly aggregates existing clip flags (Step A, edges, stand-alone) and the hook-bar flag, which are then summed with the new soft failures (`ks["n"]`) and compared against `package_pin.REVIEW_FLAGS_MAX` (3).
- **Retry Mechanism**: The `_build` loop correctly implements the "retry once" logic. The use of `retried` as a boolean flag and the condition `(total < lineups or (soft and kept and not retried))` prevents infinite loops and ensures the search for a clean line-up is prioritized.

#### 2. Technical Correctness
- **Complexity**: The use of `best_kept` with a tuple key `(c["n"], -c["low"])` correctly prioritizes the fewest flags, then the highest minimum rating.
- **Data Integrity**: The use of `dict(med, soft=accept_soft)` and `dict(coh, soft=cs_)` ensures that the original cached verdicts are not mutated, but rather extended with the soft-failure metadata for the accepted candidate.
- **Inventory Reporting**: The `inventory` function correctly maps the internal `soft` dictionaries to the required plain-sentence flags for the `medley`, `ly_shape`, and `coherence` rows.

#### 3. Test Coverage
- The 12 new tests in `test_ruling_137.py` cover the critical paths:
    - Soft failures being kept vs. hard failures being rejected.
    - The "best kept" selection logic.
    - The flag cap (3 flags pass, 4 fail).
    - The "one doubt" deduplication.
    - The specific interaction between question hooks and bridges.
    - The priority of clean line-ups over kept candidates.

### Minor Observations
- **[P3]** In `coherence_soft`, the `rest` lambda is defined inside the function. While not a performance issue given the small number of panel answers, it is redefined on every call.

### Final Verdict
The implementation is robust, strictly adheres to the provided Rulings, and maintains the "fail-closed" nature of the pipeline by ensuring that only explicitly defined "soft" failures are permitted to pass as "FLAGGED."

P1_OR_WORSE: 0