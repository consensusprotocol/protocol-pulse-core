# pp-selectid audit 0710 (item 42's gap: the trimmed cut measured as the render measures it): final consensus

**Cycle 2 verdicts:**
- grok: "Production ready: Yes", no conditions;
- glm: "Yes with conditions", two evidence-clarity conditions (N1, N2), no gate changes;
- qwen: "Yes with conditions", one condition: the synthesised record's "why".

All three agree that:
- qwen's cycle-1 "P0"s are misreadings (K1, K2: the helpers are the render's; trimmed_onset measures the audio as
  cut);
- every failure is never a pass, and the trimmed cut carries "trim" on every path;
- untrimmed moments are judged exactly as before;
- the funnel changes are report-only.

## Cycle 2: IMPLEMENTED (no change to what any check accepts)

| # | finding | change |
|---|---|---|
| D1 | The synthesised "trim" record (no plan reached) should say so (qwen C2 condition 1; earlier qwen C1 P1-5, glm C1 P1-2, grok C2 P2: consensus over both cycles) | "no trimmed cut was reached: <why>". |
| D2 | glm C2 N2: a trimmed word that is missing from the window's word record surfaced as "not the word before the lock" | hook_onset checks first that the word right before the clip is timed in the window: else "not measured", with its own reason (tested). The render's functions stay verbatim. |
| D3 | glm C2 N5: assert directly that the clean-trim / failed-lead moment cannot open | test_medley asserts its hook_onset row is a FAIL while trim_cut is empty and it is offered as a clip. |

## Refuted or recorded

| # | claim | the code / disposition |
|---|---|---|
| R1 | glm C2 N1: when the trim fails, the record's top-level cut_in / lead_ms describe "the hook's cut", not the trimmed one | For a trimmed moment there is one plan, edge_plan(..., trimmed=...). The top-level cut_in IS the trimmed plan's IN cut (its target), and the lead is measured from it. trim.cut_in is accepted_cut's pick inside the same pause, the cut the render's onset rule is measured at. Both describe the trimmed cut. No change. |
| R2 | glm C2 P2 (3): the passing test's fixture cannot tell the word gap from the quiet run | Recorded. Here the two coincide by construction, and the cut-inside-the-pause assertion holds either way. |
| R3 | qwen C2 P2-2: the funnel's "[w trimmed]" marks the first word of the original's text | That word is by definition the trimmed one: ruling 33 trims the ONE leading word, and trim_variant builds the variant from the original's next word. Report only. |

## Verification

- On the code as committed (rebased on 45 + 44, 11e455e4):
  - test_hook_onset 9 OK;
  - test_medley 80 OK;
  - angles, gates, house_style, ledger_build, speakers, providers, moments, eligibility, select_by_id OK;
  - regression_test.sh and py_compile are run on the worktree before the commit.
- The rebased change is line-for-line the audited one, except the rig's signature line, which also carries 45 + 44's
  new arguments. Compared by a sorted +/- line diff per file.
- Real data (the 05:48 build's two cleared trims, their own L-v 2 windows):
  - "So MSCI didn't force any Bitcoin selling this week..." (Coin Bureau) passes: cut 624.379 in the pause after
    "So", 83 ms fade, first onset 130 ms. It may also open the medley (lead 130 ms).
  - "So if you look at the average income..." (What Bitcoin Did) stays out: "So" runs into "if", with no measured
    pause.
