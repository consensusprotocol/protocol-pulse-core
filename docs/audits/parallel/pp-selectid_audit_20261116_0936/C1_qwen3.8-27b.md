# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 5745 / out 3332 usd_reported=0.002643 usd~0.067 (upper-bound price)

I have reviewed the provided code delta against the governing laws and the specific instructions for RULING 120.

### Analysis

1.  **RULING 120 Compliance (The Note Text)**:
    *   **Requirement**: The note must be exactly "a clip passed stand-alone on the calibrated bar" (no capital, no full stop).
    *   **Code**: `STAND_ALONE_NOTE = "a clip passed stand-alone on the calibrated bar"` in `pipeline/package_pin.py`.
    *   **Test**: `tests/package/test_medley.py` asserts `m["note"]` equals `"a clip passed stand-alone on the calibrated bar"`.
    *   **Verdict**: Compliant. The text matches the ruling verbatim.

2.  **Scope of Change (Smallest Diff / Law 20)**:
    *   **Requirement**: Only the note constant and its corresponding test expectations should change. The floor (3.0), scorer digests, and logic must remain unchanged.
    *   **Code**: The diff shows changes only to the `STAND_ALONE_NOTE` string constant and two string assertions in the test file.
    *   **Verdict**: Compliant. No logic, thresholds, or hashes were modified.

3.  **Governing Laws Check**:
    *   **LAW 20 / M2**: Gate thresholds are constants. The floor `3.0` is unchanged. The note is metadata, not a gate threshold.
    *   **M12 FAIL CLOSED**: Not applicable to this specific string change, as it doesn't alter data processing or failure modes.
    *   **L-k ONE CANONICAL FORM**: The note is a static string for display/Telegram, not a text comparison for speech/word matching. No violation.
    *   **L-j RELEASE IS AUTHORISED**: The change is in `package_pin.py` which is part of the pinning/attestation logic. The test `test_medley.py` verifies the pin structure. Since the `package_sha256` is asserted to be identical to the plain pin (line 31 of diff: `self.assertEqual(marked["package_sha256"], plain["package_sha256"])`), and the note is explicitly stated to be "outside the seal" in the context description, this change does not invalidate existing attestations or break the hash chain of the sealed content.

4.  **Potential Issues**:
    *   **Telegram Integration**: The context states: "the integrator's Telegram note prints that note... reads the same text from its own constant `telegram.STAND_ALONE_BAR_NOTE`... changed in its own audited delta."
    *   **Risk**: If `telegram.STAND_ALONE_BAR_NOTE` is *not* updated in the same commit/branch to match `package_pin.STAND_ALONE_NOTE`, the "exact-shape check" mentioned in the context ("so the two cannot differ") will fail at runtime or in integration tests.
    *   **Audit Scope**: The provided diff *only* contains `pipeline/package_pin.py` and `tests/package/test_medley.py`. It does *not* contain `pipeline/telegram.py` or `tests/telegram/test_*.py`.
    *   **Conclusion**: The prompt states "Files: pipeline/package_pin.py (one constant), tests/package/test_medley.py (two expected strings)." and "changed in its own audited delta." This implies the Telegram change is handled elsewhere or in a separate file not shown here. However, as an auditor of *this* package, I must flag that if the Telegram constant is not synchronized, the system will break. But since the prompt explicitly says the Telegram change is "in its own audited delta" and this package is just the "DELTA of the stand-alone floor... that RULING 120 makes," I will assume the synchronization is handled by the integrator's separate change.
    *   **Wait**: The prompt says "You are one of... [AI models]... review this." and "THE CODE (every new and modified file)". If `telegram.py` was modified, it should be here. If it wasn't modified, then the "exact-shape check" relies on the two constants being equal. If `package_pin.STAND_ALONE_NOTE` changes but `telegram.STAND_ALONE_BAR_NOTE` does not, the check fails.
    *   **Re-reading Context**: "the integrator's Telegram note prints that note... reads the same text from its own constant `telegram.STAND_ALONE_BAR_NOTE`... changed in its own audited delta." This phrasing suggests the Telegram constant *is* changed, but perhaps in a different file/commit that is part of the "integrator's" work, while this "pp-selectid" branch only handles the pin.
    *   **However**, the "Governing Laws" and "What this feature does" section implies a holistic view. If I am auditing the *merge* of this feature, and the Telegram constant is not updated in *this* diff, but the code relies on them being identical, this is a **P1** risk if the other change is not guaranteed to land simultaneously.
    *   **But**, the prompt explicitly lists the files in this diff: `pipeline/package_pin.py` and `tests/package/test_medley.py`. It does *not* list `pipeline/telegram.py`.
    *   **Assumption**: The "integrator's delta" is a separate, already-audited or concurrent change. The prompt asks me to check: "(1) the note is exactly the ruling's words; (2) nothing else changed; (3) the tests pin it."
    *   **Check (2) "Nothing else changed"**: In the context of *this file*, nothing else changed.
    *   **Check (1) "Note is exactly ruling's words"**: Yes.
    *   **Check (3) "Tests pin it"**: Yes.

    **Is there a P0/P1?**
    If `telegram.STAND_ALONE_BAR_NOTE` is hardcoded in `telegram.py` and *not* updated in this diff, and this diff is merged *before* the Telegram update, the system will fail the "exact-shape check" (likely a test or runtime assertion).
    
    The context says: "changed in its own audited delta." This implies the change *has* been made or *will* be made in a separate, audited package. As an auditor of *this* specific package (`pp-selectid`), I cannot see the Telegram file.
    
    However, usually, in these "Code Audit Packages," if a cross-file dependency is broken by a constant change, it's a defect. But the prompt explicitly separates the "integrator's" work.
    
    Let's look at **LAW 20**: "never change what a check accepts to make a render pass". This is a note change, not a check acceptance change.
    
    Let's look at **L-k**: "every text comparison... uses pipeline/canon.py". The note is not a text comparison for speech.
    
    **Finding**: The change is isolated and correct within the provided files. The dependency on `telegram.STAND_ALONE_BAR_NOTE` is an external integration point. If the "integrator's delta" is not part of this merge, there is a risk of mismatch. But the prompt says "changed in its own audited delta," implying it's handled.
    
    **Strict Interpretation**: The prompt asks to flag any violation of the laws.
    Does changing a string constant violate any law? No.
    Does it break the "Smallest diff"? No.
    
    **One potential P2/P3**: The note "a clip passed stand-alone on the calibrated bar" is grammatically slightly awkward ("a clip passed... on the bar"). The ruling says "YES... exactly as you and the integrator describe... ('a clip passed stand-alone on the calibrated bar')". So it is correct per the ruling.
    
    **Conclusion**: The code in the diff is correct. The tests are correct. The constant is correct.

    **Wait, let me double check the "exact-shape check" logic.**
    Context: "its exact-shape check of the mark reads the same text from its own constant `telegram.STAND_ALONE_BAR_NOTE`, so the two cannot differ".
    If `package_pin.STAND_ALONE_NOTE` is changed, and `telegram.STAND_ALONE_BAR_NOTE` is *not* changed in this diff, then *if* the Telegram file is not updated elsewhere, the check `package_pin.STAND_ALONE_NOTE == telegram.STAND_ALONE_BAR_NOTE` will fail.
    
    Since the prompt says "THE CODE (every new and modified file)" and lists only two files, and the context says the Telegram constant is "changed in its own audited delta", I must assume the Telegram change is *not* in this diff.
    
    If I am auditing *this* package for merge, and the Telegram package is separate, is this a P1?
    If the two packages are merged independently, there is a window where they differ.
    However, the prompt says "Pre-merge quality gate."
    
    Let's look at the instruction: "Flag any violation."
    If the system *requires* them to be identical, and this diff changes one without the other, it creates a state of inconsistency *unless* the other change is atomic.
    
    Given the explicit statement "changed in its own audited delta", I will treat the Telegram change as out-of-scope for *this* diff's correctness, but I will flag the dependency as a **P2** (Should fix/Verify) to ensure the integrator's delta is synchronized, or a **P1** if the "exact-shape check" is a hard gate that will fail on this branch if the other branch isn't merged.
    
    Actually, looking at the test `test_medley.py`, it only tests `package_pin`. It does *not* test `telegram`.
    
    If I merge *only* this diff, and the Telegram code still has the old string, does anything break?
    The context says: "the integrator's Telegram note prints that note... reads the same text from its own constant... so the two cannot differ".
    This implies there is a check *somewhere* (likely in `run_fresh` or a test) that compares them.
    
    If that check exists and runs on this branch, it will fail because `telegram.STAND_ALONE_BAR_NOTE` (old) != `package_pin.STAND_ALONE_NOTE` (new).
    
    Therefore, **this diff is incomplete** if the Telegram constant is not updated in the same commit/branch.
    
    **Severity**: [P1] (A real defect that must be fixed before merge). The merge will likely fail integration tests or runtime checks due to constant mismatch.

    **Counter-argument**: The prompt says "changed in its own audited delta." This might mean the Telegram change is in a *different* file that *is* part of the "pp-selectid" branch but just not shown in the "THE CODE" section? No, "THE CODE (every new and modified file)" implies the list is exhaustive.
    
    If the list is exhaustive, and the Telegram file is not modified, then the Telegram constant is *not* updated.
    
    Therefore, the constants will differ.
    
    **Finding**: [P1] The `STAND_ALONE_NOTE` in `package_pin.py` is updated, but the corresponding `STAND_ALONE_BAR_NOTE` in `telegram.py` (referenced in the context as the source for the "exact-shape check") is not included in this diff. If the check compares these two constants, the merge will fail or the system will be in an inconsistent state. The context claims it is "changed in its own audited delta," but if that delta is not part of this merge package, the package is incomplete.

    **Refinement**: The prompt asks me to review "this code". If the "integrator's delta" is a separate, already-cleared audit, then *this* code is correct *in isolation*. But "Pre-merge quality gate" usually implies the whole feature.
    
    However, the prompt explicitly says: "Files: pipeline/package_pin.py (one constant), tests/package/test_medley.py (two expected strings)."
    
    If I assume the Telegram change is *not* my responsibility (because it's "its own audited delta"), then I should not flag it as a P1 *of this code*.
    
    But, is there a violation of **LAW 20** or **M12**? No.
    
    Let's look at **L-k** again. "Every text comparison... uses canon.py". The note is not a text comparison.
    
    Let's look at the **Ruling** again. "YES... exactly as you and the integrator describe".
    
    I will flag the missing Telegram constant update as a **P1** because the context explicitly states the two constants "cannot differ" and this diff changes one without the other. Even if it's "its own delta," a pre-merge gate for the *feature* should ensure consistency. If the Telegram delta is not merged, this feature is broken.

    **Alternative View**: Maybe the "exact-shape check" is in `package_pin.py` itself? No, the context says "reads the same text from its own constant `telegram.STAND_ALONE_BAR_NOTE`".
    
    Okay, I will stick with **P1**.

    **Wait**, let me check if there are any other issues.
    - `STAND_ALONE_FLOOR` is 3.0. Correct.
    - `STAND_ALONE_FLOOR_SCORER` and `DIGEST` are unchanged. Correct.
    - Test assertions match the new string. Correct.
    
    Is there a **P2**?
    The string "a clip passed stand-alone on the calibrated bar" is lowercase. The ruling says "no capital, no full stop". This is correct.
    
    Is there a **P3**?
    None.

    **Final Decision**:
    The primary risk is the desynchronization with `telegram.STAND_ALONE_BAR_NOTE`.
    
    [P1] The diff updates `STAND_ALONE_NOTE` in `pipeline/package_pin.py` but does not update the corresponding `STAND_ALONE_BAR_NOTE` in `pipeline/telegram.py` (or wherever it resides). The context states these two constants are checked for equality ("so the two cannot differ"). Merging this diff without the Telegram update will cause the "exact-shape check" to fail or result in inconsistent metadata.

    *Self-Correction*: The prompt says "changed in its own audited delta". If I am auditing *this* package, and the other package is separate, is it a defect *here*?
    If the "Pre-merge quality gate" is for the *branch* `pp-selectid`, and the branch contains *both* changes, then the diff provided is incomplete.
    If the branch *only* contains these two files, then the feature is broken.
    Given "THE CODE (every new and modified file)", I must assume the list is complete for the branch.
    Therefore, the Telegram file is *not* modified.
    Therefore, the constants differ.
    Therefore, it is a P1.

P1_OR_WORSE: 1