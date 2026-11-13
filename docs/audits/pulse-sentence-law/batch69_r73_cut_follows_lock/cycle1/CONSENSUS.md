# Batch 69 cycle 1: one consensus finding (low), fixed
glm F2 [low], agreed by qwen27b: accepted_cut's ruling-73 clamp guarded only the boundary-point path; the candidate
fallback (cand[...][0]) was not clamped. The candidates come from grid(cut_lo, cut_hi), and the fallback is the plan's
cut, which _ruling73 clamps, so none lay outside. But the guarantee should not rest on that.
FIX: both paths go through clamp(), so every cut accepted_cut returns lies in [cut_lo, cut_hi].
Also taken from a cross-examination point: test_unchanged_but_the_named_span now asserts that every recomputed cut of
the three delivered pins meets ruling 73 (IN >= first word start - 0.400, OUT >= last word end), not only the expected
numbers. 32 passed.
Single vote, checked, no change:
- glm F1 [medium] "the IN narrowing can raise cut_hi so the cut sits after the onset". The only widening is the file
  head's: hi = max(cut_hi, bound), with bound = start - 0.400, which is before the onset. A file head's quiet runs up to
  its onset, so the cut stays inside it.
- glm F3: the pre-check's cut is sentence_law.lock_cut on the pre-check's own acquisition, whose decode is
  byte-identical to the render's (ruling 68 measurement: transcript sha256 equal on 6/6 spans). Same inputs, same code.
- cross-examination: when a range empties, 'cut' keeps an out-of-range value, but cuttable False blocks every use of it.
