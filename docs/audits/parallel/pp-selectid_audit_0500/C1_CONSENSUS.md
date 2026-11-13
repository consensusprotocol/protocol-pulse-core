# pp-selectid audit 0500 (ruling 37's pin side: a question may end the hook only): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers eligibility.py, package.py, test_eligibility.py and test_medley.py. No P0. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- qwen: "yes with conditions";
- glm: "yes with conditions".

## Consensus (each verified from the code, or implemented)

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | The re-line's termination is not shown in the diff (qwen P1-1, glm P1-4) | VERIFIED. The enclosing loop is `while n_lineup < lineups and not out["packages"] and not out.get("budget_stop")`. n_lineup is incremented before every verdict, so the loop is bounded by `lineups`. `dropped` only grows and lineup_for excludes it, so a re-line never returns a line-up holding a dropped moment. ly_shape runs in the sealed inventory of every package (inventory(..., shape=ly_shape(pk))), and "ly_shape" is a required medley gate. |
| K2 | segs[1] on a one-segment line-up (glm P1-2) | VERIFIED unreachable. lineup_for returns the hook plus LY_CLIPS = 2-4 clips (`for n in range(clips[0], clips[1] + 1)`), so every judged line-up has at least 3 segments. |
| K3 | Does the predicate read the same text as the render's R1 (glm P1-3)? | VERIFIED. The pin's approved_text is the moment's text verbatim (package_pin.to_pin: "approved_text": s["text"]), and pinned.build_edl gives the render that text. The integrator confirmed that their R1 reading (medley PASS live, "hook -> clip_01" not flagged, coherence PASS live) matches this one (message, 04:56 ET). |
| K4 | Is js[0] "hook -> clip_01" in production, not only in the fixture (glm condition 3)? | TESTED: PK.joins(PK.labels(4))[0] == "hook -> clip_01". |
| K5 | A must-pass case is missing (glm condition 4) | IMPLEMENTED: a question hook, its first join not flagged, no bridge: ly_shape == (True, []). |

## Answered or kept

- **glm P1-8 (two definitions of "ends on a question"):** eligibility's not_statement fires when the span's last word does not end a statement (ends_statement). The line-up's question_hook reads the text's last character, as the render's R1 does. A hook whose word record splits off the "?" would be eligible as a hook and not seen as a question by question_hook; the render's R1 reads the same text and would not see one either. They agree.
- **glm condition 5 (the frozen references):** the 2026-11-11 preview and the v2f references are story-path EDLs (not medleys), and ly_shape and the line-up loop run only for medleys. regression_test.sh passes (26 PASS | 0 FAIL).
- **qwen P2 (the comment's time zone):** the ruling's time is ET, as cited.

## Verification

- test_medley 61 OK, test_eligibility 30 OK; the other suites are run before the commit.
