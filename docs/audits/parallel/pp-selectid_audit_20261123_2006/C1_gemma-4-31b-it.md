# gemma-4-31b-it (google/gemma-4-31b-it) 308 s finish=stop usage in 15064 / out 6411 usd_reported=0.002788 usd~0.141 (upper-bound price)

The code implements **RULING 143** (and its integration via Ruling 153) to allow the "builder's side" to re-verify transcript settlements derived from two audio readings.

### Analysis against Governing Laws & Requirements

1.  **Material Word Definition (L-v 2 / Ruling 143 (1))**:
    *   `attest.critical` is correctly updated to include **tickers** (defined as $\ge 2$ uppercase characters, regardless of position). This matches the render's `_lv2_critical` logic.
    *   `material_pair` correctly identifies a difference as material if it is not a word-form variation and contains at least one critical token.

2.  **Wrong Audio Detection (Ruling 143 (4))**:
    *   `audio_share` calculates the ratio of matched tokens from the run decode found in the second reading.
    *   `wrong_audio` correctly triggers a `HOLD` if the share is $< 85\%$ **and** more than 3 tokens are missing. This prevents accidental holds on very short clips while catching genuine audio mismatches.

3.  **Settlement Logic (Ruling 143 (2) & (3))**:
    *   **Material Pairs**: `class_143` only takes the run decode's reading if the second recognizer agrees (`run_ok`). Otherwise, it returns `took=None`, which `lock_precheck.decide` treats as a `HOLD`. This ensures material changes are only automated when audio evidence is redundant.
    *   **Non-Material Pairs**: These never hold. They prefer the approved text if the second recognizer agrees (`pin_ok`), otherwise they default to the run decode. This matches the "small word" rule.
    *   **No-Difference Pairs**: Currency and spelling pairs are correctly excluded from the settlement logic and the `mine` comparison list.

4.  **Verification & Security (L-c / L-j)**:
    *   **No Trust in Records**: `class_143` re-derives the settlement (`mine`) from the raw readings (`run_decode`, `approved`, `second_recogniser`) rather than trusting the `pairs` or `class` fields in the record.
    *   **Integrity Check**: The code compares the re-derived `mine` against the record's `theirs`. Any discrepancy (unless the specific fallback is met) results in a `HOLD`.
    *   **Spoken Text Lock**: The final `spoken` text is compared against the `merged` settled reading. If they differ, it fails closed.
    *   **Fallback**: The fallback logic correctly handles cases where the settled words cannot be written into the approved text (requiring all pairs to be 'run' and the spoken text to match the run decode).

5.  **Integration & Tests**:
    *   `lock_precheck.decide` correctly routes "ruling 143" adjudications to `class_143`.
    *   `lock_precheck.attested` provides the required legal "carried" text for the sealed record.
    *   `TestRuling143` covers the critical edge cases: the 'FDX' $\rightarrow$ 'FTX' correction, ticker/number materiality, small word non-holds, and various `HOLD` triggers (wrong audio, lying records, etc.).
    *   The `DECODER` hash update ensures that results from the previous (now invalid) decoder are ignored.

### Findings

No violations of the Governing Laws or the specific requirements of Ruling 143 were found. The implementation is fail-closed and strictly adheres to the provided logic.

P1_OR_WORSE: 0