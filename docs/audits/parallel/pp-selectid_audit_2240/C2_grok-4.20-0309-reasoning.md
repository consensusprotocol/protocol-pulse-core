# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 91 s finish=stop usage in 34944 / out 1157 usd~0.204 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-2240 (post-fix diff)**

1. WHAT DID THEY CATCH THAT YOU MISSED?  
Cycle 1 (my output) focused on threading races (_within daemon + paid_gates inside the with block) and a title-possessive regex bypass on non-word starters. I completely missed the no-voice early-guard gap when no clip is added (qwen P0-1 + glm P0-1: original medley could carry flagged joins if content already inside nv_lo..nv_hi). Also missed that house_style was previously gated only on shape=="medley" (qwen P0-2) and the exact take_failed double-count path on cheap-then-fidelity failures (glm P1-5). The fixed diff adds the measured+flagged==[] guard at no_voice:422, the build-loop condition at 576, explicit style=HS.lint_lines in inventory, and over_budget before every lineup/write.

2. WHERE DO YOU AGREE OR DISAGREE?  
- **Agree** with qwen/glm on no-voice flagged-join risk: pre-fix dispatch checked not med["flagged"] but the no-add-clip path reused the original med without re-asserting it. The new guard + ly_shape(no_voice record + no bridges) + test_no_voice_never_ships_a_join_the_blind_check_flagged fully closes it.  
- **Partially agree** with glm P0-3 / grok P2 on _within: daemon=True + late answer drop is intentional (docstring + TestDeadline assert reservation popped, upper booked once, no double-settle). The test's usd_estimate == slow.upper_usd(...) confirms no leak; the accounting asymmetry is documented.  
- **Disagree** with grok P2 on paid_gates race: paid_gates does submit+`.result()` before returning; with-block exit cannot occur early. Consensus refutation holds.  
- **Agree** with consensus on possessive (test_house_style now exercises curly quotes, leading punctuation, CONTRACTIONS).  
- **Agree** with consensus on utc_z/recency: naive ISO, None, bad offsets, and parse failures all now refuse at to_pin via recency_problems (lines 651-668); seal includes the fields; tests cover every must-fail case.  
- **Agree** that budget checks moved before every action (over_budget at 400, called at 505/516/593) implements the glm condition (b) note.

3. NEW FINDINGS FROM THIS REVIEW  
**P2: pipeline/package.py:422 (no_voice closure)**  
no_voice closes over cleared, doomed, dropped, writers_v, writers_f from the build scope rather than receiving them as parameters. Concrete scenario: refactor moves the nested def or re-binds cleared after prescreen; no_voice sees stale eligibility or dropped moments when adding a clip (lines 433-442). Rig tests mock the outer names but do not assert the closure values. Maintainability smell only — no behavioral break in the diff.  

No P0/P1. All R1/R3/R5/R6 paths are now exercised by the new tests (test_no_voice_*, TestDeadline, test_house_style every-rule must-fail, recency must-fails in test_angles). Sentence_count, possessive tok cleaning, emoji ranges, money stems, and PROMPT_RULES sync are verified by the fixtures.

4. REVISED SCORES  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| no_voice (R3)      | P2      | resolved| explicit measured+flagged guard + ly_shape + take_failed logic + dedicated tests refute shipping bad joins or VO lines |
| budget/deadline (R5)| P2     | resolved| over_budget before every step, _spent tuple, WRITER_DEADLINE_S, TestDeadline ledger assertions close all timing/accounting gaps |
| house_style (R6)   | P2      | resolved| new test file hits every RULE_ID, must-fail fixtures, PROMPT_RULES literal match, sentence_count edge cases |
| recency seal (R1)  | P1      | resolved| utc_z + recency_problems + pin refusal + seal inclusion + exhaustive test cases for naive/None/bad-format |
| providers/_within  | P2      | P2      | daemon thread + upper booking confirmed safe; only maintainability closure issue added |

5. FINAL PRIORITY LIST  
**P2 MEDIUM** (only)  
- pipeline/package.py:422 — no_voice must receive cleared, doomed, dropped, writers_* as arguments instead of closing over build locals (file:line cited).  
No P0 or P1 remain. All critical invariants (seal contents, no flagged no-voice, budget checked pre-write, house_style required for MEDLEY_GATES, deadline failover recorded) are now guarded and tested.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE  
The combination of the no_voice measured+flagged guard (422), take_failed increment points, over_budget checks before every lineup/write, and explicit style=HS.lint_lines in the inventory call eliminates every bypass that Cycle 1 surfaced.

7. PRODUCTION READY?  
Yes with conditions: (1) eliminate the no_voice closure by passing cleared/doomed/dropped/writers_* explicitly; (2) confirm the full proof_ly.py suite (including 41f29b1f must-fail lines) still produces only passing pins after house_style enforcement.

**SHIP: yes with conditions**