# pp-selectid audit 0352 (the exclusion screen's deterministic part before step A; why_none named): cycle 2 consensus, FINAL

**Run.** Cycle 2 cross-reviewed the FIXED diff against the cycle-1 reviews and C1_CONSENSUS.md. No P0. Verdicts:
- glm: no P1, "Yes. No conditions required to ship";
- grok: no P1, "yes with conditions" (P2 items);
- qwen: one P1, IndexError on a moment with fewer than two sentence fields, "yes with conditions".

## Implemented after cycle 2

| # | finding (reviewers) | disposition |
|---|---|---|
| F1 | ad_read_out caught only KeyError, so a moment with too few sentence fields would raise IndexError and crash build() (qwen P1, P2) | IMPLEMENTED: (KeyError, IndexError) skip the moment, which is left to the package stage (fail closed). moments.record always writes "sentences": [k0, k1], and exclusion_for indexes the same fields, so the exposure was pre-existing there. Tested with sentences=[0]. |
| F2 | The differential test covered only the positive case (glm N1, grok P2) | IMPLEMENTED: for moment "b" (no marker), ad_read_out does not refuse it, and the package stage's exclusion_for goes past its deterministic part to the model verdict (the test router asserts that it is called). |

## Kept (with reasons)

- **grok P2 (call ad_read_marker even when the context is None):** KEPT. The package stage refuses a moment without context for that reason ("no context"). Leaving it to the package stage keeps one reason per refusal, and glm calls the guard load-bearing for the documented contract. Both forms refuse the same moments; neither passes anything new.
- **glm N3 (the log line's sequential counts):** cosmetic, no change.

## Verification

- test_medley 54 OK; all 11 offline suites OK; regression_test.sh 26 PASS | 0 FAIL | 5 WARN.
- These were run on exactly the committed state: the in-progress ruling-34 files were set aside to the scratchpad and restored after the commit.
