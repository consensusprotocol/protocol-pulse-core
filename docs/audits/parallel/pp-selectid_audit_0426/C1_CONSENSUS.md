# pp-selectid audit 0426 (ruling 34's pin side: the miner's screen sealed and applied, the medley names Bitcoin): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers stand_alone.py (the sync), eligibility.py, package.py, package_pin.py and the two test
files. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- glm: no P0, "yes with conditions";
- qwen: "SHIP: NO" on three P0s, each refuted below with evidence.

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | The sealed screen equals the judged one only by construction (glm P1-1 and condition 2; qwen's P0-4 on the same seal path, found consistent) | IMPLEMENTED: screen_problems refuses a medley whose sealed btc_screen.pattern is not the pattern its "stand_alone" gate row recorded. check_edl's out["screen"] is copied into the row by inventory. Tested: a row with no judged screen refuses, and a compiling but different pattern refuses. |
| K2 | stand_alone.BITCOIN, the medley rule's regex, is not shown in the diff (qwen P0-1 and P1-1, glm P1-2) | REFUTED with the file. stand_alone.py:27 is `BITCOIN = re.compile(r"\b(bitcoin|btc)\b", re.I)`, in the base file and byte-identical to the render's (main 55315124, cmp). The medley-rule tests run that code path and pass, which a NameError would not. IMPLEMENTED: glm's hook-only case ("named by hook"). |
| K3 | no_topic's literal "Bitcoin" predecessor may not be the most favourable place (qwen P0-3, glm P1-3 and condition 4) | VERIFIED as maximal. topical()'s completion rule (stand_alone.py:80-97) is `prev_text and _mentions(prev_text, subject) and first in BACKREF and FIGURE.search(text)`. It reads the previous text ONLY through _mentions(prev_text, {bitcoin, btc}). Every predecessor that mentions Bitcoin gives the same result, so "Bitcoin" is maximal, and a moment it fails can take no place. glm confirms the drop direction is safe. |
| K4 | Does stand_alone_check serve the story path (glm P1-4, condition 1)? | VERIFIED by grep. It is called only by package.py's medley build (lineup_for's need_stand_alone and the two inventory call sites) and by tests. The story path never calls it, and the render's story path passes no screen (unchanged). |

## Refuted

- **qwen P0-2 (the mirror test's parsing):** not a defect. The test ran, it was not skipped, and it passed: it parsed mine.py at 8e6afb61 and matched the pattern exactly. Its skip covers only an environment without pp-ingest's history.

## Verification

- test_medley 57 OK; test_eligibility 30 OK; all 11 suites OK.
- Old pins still recompute (check_pin_only, with the integrator's 7-argument call, on d2657bbe, 1b4a63d0 and 41f29b1f: READY, per the integrator at 04:20 ET).
