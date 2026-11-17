# gemma-4-31b-it (google/gemma-4-31b-it) 304 s finish=stop usage in 18342 / out 6323 usd_reported=0.001353 usd~0.150 (upper-bound price)

The code implements **RULING 131** (two-of-three adjudication) for the lock pre-check phase. It ensures that text adoptions are re-derived from raw readings rather than trusted from the record, enforces a 3-token edge buffer, blocks critical word changes, and handles currency formatting and repetitions.

### Audit Findings

**1. Adjudication Logic (Two-of-Three)**
The implementation in `attest.class_131` correctly follows the priority:
- **Currency Formatting:** `currency_pair` identifies "dollars" tokens following numbers. Since `all([])` is `True`, it correctly handles `delete` (run has "dollars", approved doesn't) and `insert` (approved has "dollars", run doesn't) cases.
- **Criticals:** `critical(t, texts)` (the render's `_lv2_critical`) is applied to all tokens in the pair, correctly blocking numbers, names, and negations.
- **Voting:** It uses `reads()` to check if the second recogniser agrees with the approved text first, then the run's text (provided the `edge_distance` $\ge 3$).
- **Fail-Closed:** Any pair that doesn't fit these categories results in `class: None`, which `lock_precheck.decide` treats as a `hold`.

**2. Edge Distance and Sliding**
The `edge_distance` function correctly implements the "slide" for repetitions. By calculating the equal runs before and after a `delete` or `insert` and iterating through possible shifts, it finds the placement that maximizes the distance from the nearest edge. The use of `max(min(a + n, len(r) - (b + n)))` is mathematically sound for this purpose.

**3. Final Spoken Text Validation**
The logic in `class_131` (lines 124–133) ensures that the final `spoken` text is not just a result of the merged adjudication, but that any additional adoptions (via Ruling 72/84) are also supported by the second recogniser's reading. This prevents the "adopt_spoken" layer from introducing hallucinated or unsupported words.

**4. Integration and Regression**
- `lock_precheck.decide` correctly isolates Ruling 131 records using `.startswith(AT.RULE_131)`, ensuring that existing Ruling 84/105 paths remain unchanged.
- `lock_precheck.attested` updates the sealing metadata to include the specific "two of three readings" language required for the release caption.
- The `RULES` string update and `DECODER` constant update align with the integrator's requirements.

**5. Test Coverage**
The `TestRuling131` suite is comprehensive:
- It verifies the "happy path" with real readings.
- It tests "lies" in the record (wrong `took` value, missing pairs, incorrect distances).
- It validates that criticals and edge-buffer violations trigger a `hold`.
- It confirms the sliding logic for repetitions and the currency formatting exception.
- It ensures that non-Ruling 131 records are not processed by the new logic.

### Conclusion
The implementation is robust, strictly adheres to the governing laws, and includes a high-coverage test suite that kills all identified mutations.

P1_OR_WORSE: 0