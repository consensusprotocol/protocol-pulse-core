# gemma-4-31b-it (google/gemma-4-31b-it) 431 s finish=stop usage in 12307 / out 4520 usd_reported=0.000942 usd~0.105 (upper-bound price)

The code implements the coherence panel as specified in RULING 118 (2) and RULING 130 (4).

### Audit Findings

1.  **Replay Rule Compliance**:
    *   **Member/Seed Logic**: The implementation correctly iterates through the configured members and seeds (`[7, 8]`), with a retry at `seed + 100` if the first attempt fails or violates the contract.
    *   **Verdict Threshold**: The "no verdict" condition (`len(votes) < min_members`) is correctly implemented as a hard stop that returns `False` and `measured: False`, ensuring it can never pass.
    *   **Pass Condition**: The majority rule (`sum(passes) * 2 > len(answers)`) correctly implements "more than half of all answers."
    *   **The Bar**: It uses `lineup_floors("coherence", ...)` to establish the standard bar, and the `passes` lambda correctly validates both the `through_line` (via `_line_ok`) and the ratings against those floors.
    *   **Output Values**: The use of `statistics.median_low` for `clips` and `vo_point`, and the selection of the first sound `through_line`, matches the replay requirements.

2.  **Writer Exclusion**:
    *   The code filters the `names` list to exclude the `writer_vendor` and `writer_family`.
    *   Furthermore, it passes `avoid_family=others` (where `others` includes other panel members and the writer's family) to `P.call_parsed`, ensuring strict isolation.

3.  **Contract and Parsing**:
    *   The `PANEL_CONTRACT` is correctly passed as the system prompt.
    *   The `parse` function correctly handles the "closing-brace rule" by routing through `hook_answer(text)[0]` when `braces=True`.

4.  **Integration and Fallbacks**:
    *   `coherence_panel_spec` allows the system to fall back to a single rater if the panel is not configured in the router, preserving existing behavior.
    *   The hook's cached rating (`own["passes"]`) is correctly required for a final `ok` verdict, adhering to Ruling 61.

5.  **Test Coverage**:
    *   `TestRuling130CoherencePanel` comprehensively covers the critical paths: majority pass, exactly-half failure, member-count failure (including retry seed verification), writer exclusion, and the brace-parsing rule.

### Conclusion
The implementation is precise, fail-closed, and adheres to all governing laws and the specific replay rules provided.

P1_OR_WORSE: 0