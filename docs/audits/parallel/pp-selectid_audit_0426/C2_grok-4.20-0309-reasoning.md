# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 30 s finish=stop usage in 13824 / out 1093 usd~0.096 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0426 (Ruling 34 pin side)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   In my Cycle 1 I flagged only the unsealed-screen recompute path and the untested hook-only medley-names case. I completely missed (a) the brittle git-show mirror test's environment-specific skip, (b) that `screen_problems` must also reject a compiling but non-identical pattern (the exact drift GLM P1-1 described), and (c) that `no_topic` now chains `or no_topic(m)` inside the comprehension and updates the log string. Those three gaps are visible only after seeing the fixed diff + the other reviewers' outputs.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM P1-1 (sealed vs judged screen drift): fully agree on the risk; the fixed `package_pin.py:161-163` (`judged != pat`) plus test at `test_medley.py:346` that injects `["screen"] = check()["screen"]` now closes it.  
   - GLM P1-2 (BITCOIN definition + hook test): agree the diff alone did not show the definition; consensus + `stand_alone.py:27` (base) and the new `TestRuling34Screen.test_the_screen...` exercising hook-only naming refute any runtime or logic gap.  
   - GLM P1-3 (most-favourable predecessor): agree "Bitcoin" is maximal per `topical()`'s `_mentions` rule; `no_topic` + its test at `test_medley.py:331-333` are correct.  
   - Qwen P0-1 (NameError on BITCOIN): disagree — refuted by consensus and by the passing test suite that reaches line 247.  
   - Qwen P0-2 (mirror test parsing): disagree — test passes when the worktree is present; skip is documented.  
   - Grok's "byte-for-byte identical, SHIP yes": agree on the render sync and on old-pin recompute (explicit 7-arg vs 6-arg test at `test_medley.py:351-352`).

3. **NEW FINDINGS FROM THIS REVIEW**  
   - P2-1 `tests/eligibility/test_eligibility.py:265`: the mirror test hard-codes `/home/ultron/worktrees/pp-ingest`. It correctly skips in CI but is the only place the sealed source string is validated against live git history; a future move of the worktree silently weakens the guarantee.  
   - P2-2 `package_pin.py:162`: `judged = ((pk.get("gates") or {}).get("stand_alone") or {}).get("screen")`; if the gate row is absent the comparison becomes `None != pat` and correctly refuses, but the error message interpolates `None` — readable but could be more explicit.  
   No P0 or P1 surfaced; the diff now implements every contract point that was conditional in Cycle 1.

4. **REVISED SCORES**  
   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | stand_alone sync       | P1      | clean   | topical_screen + check_edl(screen=) now byte-identical to render; medley_names_bitcoin exercised for hook and clip |
   | btc_screen sealing     | P1      | clean   | screen_problems enforces exact pattern match; seal() conditional inclusion; 7-arg recompute test |
   | no_topic / build filter| P1      | clean   | chains correctly, drops only unplaceable moments, log updated |
   | test coverage          | P2      | P2      | mirror test still environment-dependent (new P2-1) |
   | pin refusal surface    | clean   | clean   | screen_problems integrated into to_pin gate_problems path |

5. **FINAL PRIORITY LIST**  
   **P0 CRITICAL** — none.  
   **P1 HIGH** — none.  
   **P2 MEDIUM** — `tests/eligibility/test_eligibility.py:265` (brittle git worktree path); `package_pin.py:162` (None interpolation in error). These are documentation/test-maintenance items only; nothing blocks correctness or render-pin agreement.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   `screen_problems()` (package_pin.py:143-164) plus the test that forces the gate row to contain exactly what `stand_alone_check` emitted — this is the mechanical proof that the sealed screen cannot diverge from the judged screen.

7. **PRODUCTION READY?**  
   **Yes**. The pin stage now performs exactly the render's `check_edl(screen=...)` contract, seals the identical screen, refuses any mismatch or malformed screen, leaves out only moments with no possible place, leaves the story path untouched, and recomputes every older pin. The two P2 items are non-blocking.

**P0:** none  
**P1:** none  
**P2:** two minor test/maintenance items (see #5)  
**SHIP: yes**