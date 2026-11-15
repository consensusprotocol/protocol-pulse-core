# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 28 s finish=stop usage in 8627 / out 556 usd_reported=0.020587 usd~0.057 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1459 (RULING 115 interim hook bar)**

**Summary**  
The diff implements exactly the semantics described in the PR text and the four explicit "PLEASE CHECK" items:  
- No calibration can be valid forever except by an explicit `"valid_h": null`.  
- All pre-existing validation (sha256 seal, rater/question_version/seed/asking match, timezone, skew, floor >= 3) is untouched and executed in the same order.  
- The reading of rulings 115 (1) and (3) matches the provided text (interim bar sourced from a single fixed ALONE_TEST.json therefore does not carry the once-per-day expiry that belongs to the later question-version calibration).  
- Tests are expanded, pass, and kill the four relevant mutations.  

The change is isolated to hook calibration expiry, does not touch rendering, selection logic, EDLs, final bytes, sentence boundaries, credits, voice-over, or any gate that affects L-a through L-l, LAW 20/M2, M12, or LAW 22. No new renderer/compositor/selector. Fail-closed behavior is preserved (missing/invalid `valid_h` → no hook passes). The updated JSON is correctly re-sealed.

**Findings**  
[P3] hook_bar.py top comment still contains "(fail closed, law L-m)". L-m is not defined in the governing laws (they stop at L-l before LAW 20). While the *behavior* is correct (M12 fail-closed is respected), the reference should be removed or updated.  
[P3] bar() uses `type(vh) not in (int, float)` rather than `isinstance`. Functionally harmless for JSON-loaded primitives but deviates from Python norms.  
[P3] TestTheLiveCalibration.test_the_interim_bar_does_not_expire calls `HB.bar(...)` with a 30-day-future timestamp; this is correct but the test name and docstring could be more precise about also exercising the real production calibration file (already done in the subsequent test).  
[P2] "Smallest diff" (M1) is stretched by 176 lines that are 70 % test/docstring updates. The functional delta is ~15 lines; the remainder, while justified for coverage, could have been split into a pure test-only follow-up commit.

No gate logic, byte fidelity, sentence-law edge handling, release_auth, canon.py usage, or protected preview reference is altered. All must-fail/must-pass examples cited in the governing laws remain unaffected. The interim bar now behaves as ruling 115 requires without weakening any other law.

P1_OR_WORSE: 0