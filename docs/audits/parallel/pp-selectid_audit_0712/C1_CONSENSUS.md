# pp-selectid audit 0712 (RULING 49: a trimmed clip sealed with the clip scorer's verdict pending): cycle 1 consensus

**Run.** Verdicts:
- grok: "yes with conditions" (P2 only);
- qwen: no P0 / P1, "SHIP: yes";
- glm: no P0, "yes with conditions" (its P1s are consistency and diagnostics; its conditions are answered below).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | grok P2 (its condition 2), in glm P1-2's spirit: the row's scorer_pending is hard-coded True whatever TRIM_SCORER_PENDING says | The row writes bool(TRIM_SCORER_PENDING). Under the strict switch a trimmed segment would carry False, which trim_problems refuses, so the pin can never claim pending when the switch says strict. |

## Answered (verified from the code; no change)

| # | condition | answer |
|---|---|---|
| A1 | glm condition 1: is the package row the only producer of trimmed_leading / untrimmed_start on a segment? | Yes. They are set only by trim_variant (the moment, always both keys together), the _package row literal (both, with scorer_pending), and to_pin's copy. So the pin's ruling-49 (a) check cannot see a trimmed row without scorer_pending. |
| A2 | glm P1-1: lineup_ok counts trimmed_leading while trim_problems counts either key | Equal on every producer's output, because both keys always come together (A1). trim_problems is the pin's backstop: it also refuses a row with only one key. |
| A3 | glm condition 2: derive TRIMMED_PER_PIN_MAX from package | Kept as two constants plus the equality test (test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin). The integrator's check_pin_only imports this branch's package_pin.py, and package_pin must not pull package.py (and its imports) into the integrator's process. |
| A4 | glm condition 3: a test of the no-voice path's copy of the rule | Not added (one reviewer, P2). The inline rule is the same expression as lineup_for's, which is tested, and a pin with two trimmed clips is refused by trim_problems anyway (tested). |
| A5 | grok condition 1: when is the limit of one raised? | Only when the integrator reports the first trimmed clip affirmed at validate, and on your word. It is stated in the constant's comment and in STATE. |

## Verification

- test_medley 81 OK; every other suite OK.
