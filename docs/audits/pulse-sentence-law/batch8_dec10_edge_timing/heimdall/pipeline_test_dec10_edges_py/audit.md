# Heimdall audit

**Question:** Protocol Pulse sentence law for cutting video clips at sentence edges (DEC-10). Change: the timing minimums (pause, lead, tail, guard) are calibrated to the approved reference's measured worst (0 ms: one approved edge has abutting words); a boundary's legal cut range is now the HEARD gap (the previous word's last offset to the next word's first onset at speech - 6 dB) and the neighbour side ends at the envelope minimum between the two words; abutting words get a zero-length pause at that minimum; a short gap is cut at the minimum with a 2-frame audio fade instead of being rejected; a new check neighbour_clear fails any cut that keeps frames of the neighbouring word above the valley threshold (speech - 12 dB) after the fade; a separate file-head rule (80 ms or a room-tone pad) is unchanged; prerender passes per-cut fade lengths (the frozen reference declares 20/30 ms, identical to the old defaults). Find real bugs: a cut that can now include part of another word or sentence and pass, a clipped first/last word that passes, ranges that are empty or inverted, the frozen reference's output changing, must-fail cases that now pass. Only state what you can verify from the diff. (this chunk: pipeline/test_dec10_edges.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0218
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_dec10_edges.py:125** The assertion allows the cut to be up to 20 ms inside the previous word, so a cut that clips the last 20 ms of the previous word passes, contradicting the comment 'never inside the previous word'.
  - evidence: `self.assertLessEqual(self.words[k]["end"] - 0.02, cut["cut_in"])     # never inside the previous word`
  - fix: Change to self.assertLessEqual(self.words[k]["end"], cut["cut_in"]) or use a negligible epsilon (e.g., 1e-6) instead of 0.02.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[high] pipeline/test_dec10_edges.py:126** The assertion allows the cut to be up to 20 ms after the start of the next word, so a cut that includes the first 20 ms of the next word passes.
  - evidence: `self.assertLessEqual(cut["cut_in"], self.words[k + 1]["start"] + 0.02)`
  - fix: Change to self.assertLessEqual(cut["cut_in"], self.words[k + 1]["start"]) or use a negligible epsilon.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[high] pipeline/test_dec10_edges.py:122** The valley check is optional when the pause is under 80 ms; since the test setup has a 50 ms gap, this condition is always true, so a cut that is not at the envelope minimum and has no 2-frame fade can pass.
  - evidence: `self.assertTrue(cut["valley_in"] or b["pause"]["ms"] < 80, (cut, b["pause"]))`
  - fix: Require cut["valley_in"] unconditionally for this short-gap case, and always assert the fade length when valley_in is expected.
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[medium] pipeline/test_dec10_edges.py:119** The valley-cut assertion is logically vacuous for the abutting (0 ms pause) case it is meant to verify. Because the 50 ms word gap carries no inter-word silence, b["pause"]["ms"] is 0, making the right-hand side of the or always True. The test therefore passes even if the implementation does NOT produce a valley_in cut (i.e. it cuts at the wrong point in the gap or uses a 20 ms fade instead of the mandated 2-frame fade), because the fade-length check on the next line is guarded by if cut["valley_in"] and is skipped.
  - evidence: `self.assertTrue(cut["valley_in"] or b["pause"]["ms"] < 80, (cut, b["pause"]))
        if cut["valley_in"]:
            self.assertEqual(cut["fade_in_ms"], int(round(L.VALLEY_FADE_S * 1000)))`
  - fix: Assert valley_in unconditionally for the 0 ms-pause / 50 ms-gap fixture (the case the test is named for), or restructure so the fade-length check runs whenever the gap is below the 80 ms head threshold, not only when the implementation self-reports valley_in.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[low] pipeline/test_dec10_edges.py:63** Variable p is assigned from b["pause"] but never referenced; only g (word_gap) is used in the range computation. This is dead code that obscures intent and could mask a future refactor where the pause value is needed for the legal-range bounds.
  - evidence: `p, g = b["pause"], b["word_gap"]                  # the heard gap (DEC-10)`
  - fix: Remove the unused p binding: g = b["word_gap"].
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [medium] The test does not verify the cut is at the envelope minimum; it only checks the valley_in flag (which is optional) and a loose 20 ms tolerance around word boundaries, so a cut anywhere in the 50 ms gap with valley_in=True and correct fade length would pass.
