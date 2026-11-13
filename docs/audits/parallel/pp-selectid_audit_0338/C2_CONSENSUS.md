# pp-selectid audit 0338 (rulings 38 + 39): cycle 2 consensus, FINAL

**Run.** Cycle 2 cross-reviewed the diff against the cycle-1 reviews and C1_CONSENSUS.md. All three reviewers: P0
none, P1 none.
- grok: "yes with conditions";
- qwen: "yes with conditions";
- glm: "yes with conditions; the conditions are documentation/coverage, not code".

## Implemented after cycle 2

| # | finding (reviewers) | disposition |
|---|---|---|
| F1 | The edge matcher read the EARLIEST candidate within 0.6 s (IN) and the LATEST within 0.8 s (OUT). With the canonical match adding candidates, an earlier occurrence of the same word or number could be read (grok C2 P2, glm C1 P2-2) | IMPLEMENTED: the occurrence NEAREST the clip's own start (IN) or end (OUT). This fixes a fail-open the cycle-2 test exposed: with "Bitcoin" said 450 ms before the clip's own "Bitcoin", the earliest rule judged the IN at the earlier word (1000 ms of no word before it: pass); the clip's own occurrence follows a word by 250 ms (fail). Tests: both edges, with two competing occurrences each. |
| F2 | Document that (b) is measured on the recogniser's word timing, and that the render's acoustic check is the backstop (glm C2 condition 1, grok C2 condition b, qwen C2 condition 1) | DONE: a code comment at the gap, plus STATE. |
| F3 | Document the time-order assumption (glm C2 condition 2) | DONE: a code comment citing the 99 of 99 recorded transcriptions. |
| F4 | The canonical run may reach past the 0.6 / 0.8 s windows (glm C2 N1) | DONE: a code comment; only the CANDIDATE word must sit inside the window. |
| F5 | Missing tests: exactly 700 ms; the file head with a qualifying gap (precedence); an identical canonical token in the window (glm C2 N3, grok C2) | DONE: test_the_boundaries_and_the_precedence. |

## Kept

- **glm C2 N2:** a negative gap (overlapping words) shows "-150 ms" in the reason string. It fails closed; the text is cosmetic.
- **grok C2 (the fallback wav_start):** KEPT. No caller passes wav= without wav_start (C1 K3).
- **grok C2 condition (c), "the new 4 s WAV files are confirmed cached":** they are cached by name like every window. The cost: each moment's L-v 2 window is new once, about 2.5 s longer, at the per-minute price.
- **qwen C2 (canon does not merge "Bit- coin"):** a limitation of the shared canonicaliser that the old 4-letter rule shares. No regression.

## Verification

- test_angles 27 OK (20 existing, 7 new).
- test_hook_onset, test_medley and test_gates OK.
- regression_test.sh is run before the commit (in the commit message).
