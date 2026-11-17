# Cycle 1 consensus (pp-selectid_audit_20261117_1435, ruling 141 (3): the line-up chain, phase A)

SEATS ANSWERED: 3 of 3. qwen3.8-27b: P0/P1 none (three P2s, four P3s). gemma-4-31b-it: P0/P1 none. gpt-oss-20b: three
P0 and two P1 claimed (its "**P1_OR_WORSE**: 2" line is bold, so the driver's tally reads 0); each is answered below.

## gpt-oss's claims
1. [P0] "inventory uses an undefined `med` / `med[0]`": REFUTED. The code reads `medley[0]` (package.py:4561-4564).
   `grep -c "med\[0\]" pipeline/package.py` is 0. Every inventory test (and the 911-test suite) passes.
2. [P0] "`med[0]` instead of `medley[0]`": REFUTED (the same line).
3. [P0] "no join sentences when medley[0] is False": REFUTED. For the accepted candidate the loop sets ok_m True before the
   inventory (package.py:4016: `ok_m, med = True, dict(med, soft=accept_soft)`), and the inventory gets
   medley=(ok_m, med). The two-joins end-to-end test asserts the medley and ly_shape rows FLAGGED with the join sentence.
4-5. [P1] "a question hook's flagged first join is hard (ruling 37)": BY THE AGREED SCOPE. The coordinator's 14:35 ET
   update, after the integrator's answer, makes ruling 37's join SOFT ("may be flagged too"): its render's R1 is soft at
   validate. What stays hard is the rule's purpose, no bridge after a question. The bridge never goes there (lineup_soft
   skips it as bridgeable, bj skips soft joins, ly_shape's other checks are unchanged), and the question-hook end-to-end
   test asserts nothing is written after the question (write join None, pk["bridge"] None).

## qwen's P2s
- "over_budget(ai) sits before the retry and can suppress it": BY DESIGN. over_budget is ruling 41's money stop for the
  angle; the retried candidate pays the same later gates (vision, the writes), so no retry once the money says stop.
- "coherence_soft does not check the summary vo_point under a panel": BY DESIGN. The panel decides by majority
  (package.py:2102); coherence_soft applies the same majority to each answer's through-line and VO point, and still
  requires an int summary vo_point. A panel minority with a stated line cannot pass it.
- "floors keys without a guard": DECLINED. medley() and coherence() always write floors from lineup_floors (calibrated or
  standard, the same keys). Every existing reader uses the same access (last_clip_only, ruling 116's lines).
- P3s (duplicate kept entries of one key: harmless, retried once; rec["kept"] is the record; the tuple `done`;
  a test's conditional assertion): DECLINED (no behaviour change).

## No change from cycle 1 to cycle 2.
