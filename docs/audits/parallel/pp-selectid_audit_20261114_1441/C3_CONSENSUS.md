# Audit 20261114_1441 (ruling 104), cycle 3 (the one-line fix after cycle 2): consensus

- grok-4.20: SHIP yes with conditions. No P0 or P1.
- qwen3.8-27b: yes. No P0 or P1.
- glm-5.3-flash: yes with conditions. No P0 or P1. Its conditions are two one-line tests or notes, and it says neither
  blocks the Blockware case.

All three confirm (h): a current hold can no longer produce a variant that keeps the held word. The hold branch finds a
boundary strictly before the held word, or gives no variant at all (the fix). They also confirm (i): the cut hold, a
placeable hold and the ceiling alone are unchanged.

## Conditions, answered from the code (no change)

- **grok (1) / glm (2), the ceiling's rounding.** for_pool keeps a boundary only when its token-end minus the start is
  <= ceil_s, unrounded. M.record's duration_s rounds the same span to 0.01 s, and a value <= ceil_s never rounds above
  it. spotlight.pool's usable(seg_max=35 s) still applies to the variant as to any moment.
- **grok (2), lock_precheck.answer reads only the current decoder's file under the current rules.** This is unchanged
  code (result_file with DECODER; _matches with rules == RULES). test_ruling_104 checks it through holds(): an older
  decoder's or older rules' hold is not read.
- **grok (3), the first production build's RULING 104 line.** It is read onto STATE line 1 after the build.
- **glm (1), a variant under SNAP_TO_S (13.7 s).** It is NOT a spotlight. spotlight.pool calls snap(), which refuses to
  snap a variant outward, and pool() then records "the snap fails: ... never snapped outward" and leaves it out.
  13.7 s is the shortest clip that reaches the spotlight's 28 s runtime floor with its 14.3 s tail, so such a variant
  could not seal as a spotlight anyway. The medley may still use it under its own rules. Blockware's variant is 15.28 s.

FINAL.diff = the diff cycle 3 reviewed (C3_STEP.diff). 20 of 20 mutations killed.
