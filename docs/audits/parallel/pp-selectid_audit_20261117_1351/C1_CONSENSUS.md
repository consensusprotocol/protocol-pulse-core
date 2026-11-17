# Cycle 1 consensus (pp-selectid_audit_20261117_1351, ruling 141 (2): STAND_ALONE soft, the builder's half)

SEATS ANSWERED: 2 of 3. qwen3.8-27b: P0/P1 none (three P2s, two P3s). gemma-4-31b-it: P0/P1 none. gpt-oss-20b: its
32,000-token cap ran out with no answer.

## qwen's findings
- [P2] stand_plain's fallback to the raw reason "silently degrades" the flag: BY DESIGN, DECLINED. The two patterns
  are stand_alone.opener's own clip wordings (stand_alone.py:98 and :101); any other wording is shown as the render
  gives it. That is still the render's reason in the sentence, never an empty or wrong flag.
- [P2] no end-to-end case of a soft pass whose pin row has a HARD failure: COVERED below the end-to-end level. Every
  hard case of stand_soft_rows has a unit test: the hook's row (marked or not), a topic row, an unmarked clip, the
  medley not naming Bitcoin or that record missing. lineup_ok refuses an unmarked conjunction clip. The end-to-end
  pool's topic-refused moment w stays out. Mutations S6-S9 are killed.
- [P2] stand_soft_rows maps rows to segments by labels() position: BY DESIGN. stand_alone_check builds its EDL from the
  same segs in the same order (the hook, then clip_01...: package.py:1221-1248), and check_edl labels its rows so
  (stand_alone.py:186).
- [P3] a double period if a raw reason ends with ".": none of opener's clip wordings does. DECLINED.
- [P3] the dense comprehension: DECLINED (cosmetic).

## No change from cycle 1 to cycle 2.
