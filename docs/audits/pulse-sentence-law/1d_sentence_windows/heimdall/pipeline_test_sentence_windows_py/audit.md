# Heimdall audit

**Question:** Commit 1d makes selection propose sentence-aligned windows: abbreviation-aware sentence splitting (sentence_law.is_terminal), windows of one to three whole sentences (interjection-only sentences transparent per PBX D4a), clip budget 12-20 s, the editor's hook/clip slots honoured, and a window the sentence law rejects replaced by the next-ranked legal candidate of the same kind (score floor, budget, overlap, per-channel and per-video caps) instead of moving a cut. Find defects: a path that can pick an illegal/overlapping window, a cap or floor bypass, wrong window bookkeeping, a fallback that can loop or silently drop the hook. (this chunk: pipeline/test_sentence_windows.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0211
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_sentence_windows.py:102** The bad clip's end time 524.0 does not correspond to the end of its text. The text is text("BBB", 4, 6), which includes sentences 4-6. In _sentences, sentence 6 ends at relative time 19.35, absolute 495.0 + 19.35 = 514.35. The bad clip ends at 524.0, 9.65 s later. This means the test may reject the clip for being out of bounds rather than for the intended no-pause boundary.
  - evidence: `bad = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
                   "duration": 14.0, "score": 80, "clip_score": 4.0, "text": text("BBB", 4, 6)}
...
d`
  - fix: Set the passage start/end to match the actual word times, e.g., end at 514.35 for the bad clip, and similarly align the hook and alt passages.
  - raised by deepseek:F1; agree: deepseek, qwen27b, glm
- **[high] pipeline/test_sentence_windows.py:126** The test only checks edl["clips"][0] and never asserts that the hook is present in the EDL. A fallback that silently drops the hook would still pass.
  - evidence: `clip = edl["clips"][0]
self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)`
  - fix: Add an assertion that the hook is present in the EDL, e.g., self.assertIn("hook", edl) or check edl["hook"].
  - raised by deepseek:F3; agree: deepseek, qwen27b, glm
- **[high] pipeline/test_sentence_windows.py:127** The test only checks the first and last words of the selected clip, not its start, end, or duration. It cannot detect an illegal/overlapping window or budget bypass.
  - evidence: `self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)`
  - fix: Add assertions that the clip's start/end are within the alt passage's bounds and duration is within 12-20 s, and that it does not overlap the hook.
  - raised by deepseek:F4; agree: deepseek, qwen27b
- **[high] pipeline/test_sentence_windows.py:121** The test never asserts that the hook survives in the EDL output. The audit requirement explicitly calls out 'a fallback that can loop or silently drop the hook,' yet the test only inspects edl["clips"][0]. If select_and_build_edl's fallback path for the rejected clip corrupts or omits the hook entry, this test still passes.
  - evidence: `clip = edl["clips"][0]
            self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)`
  - fix: After the clip assertion, add: hooks = edl.get("hooks", []); self.assertTrue(hooks, f"hook missing from EDL: {edl}"); self.assertEqual(hooks[0]["video_id"], "AAA"); self.assertEqual(hooks[0]["kind"], "hook")
  - raised by qwen27b:F1; agree: deepseek, qwen27b, glm
- **[medium] pipeline/test_sentence_windows.py:121** The test only checks edl["clips"][0] but never verifies that the rejected 'bad' clip is absent from the clips list. If the production code appends the fallback without removing the rejected entry, the EDL would contain both the illegal and the legal clip, and the test would still pass because index 0 happens to be the correct one (or the bad one, depending on ordering).
  - evidence: `clip = edl["clips"][0]
            self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)`
  - fix: Add: self.assertEqual(len(edl["clips"]), 1, f"expected exactly one clip, got {len(edl['clips'])}: {edl['clips']}") to ensure the rejected clip was removed, not merely reordered.
  - raised by qwen27b:F2; agree: deepseek, qwen27b, glm

## Raised but not agreed
- deepseek:F2 [medium] The fake download function ignores the requested start, end, and pad, so it does not simulate the download window. This means the test cannot detect bugs where the selection picks a window outside the downloaded window or overlapping with other passages. (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [high] All three passages have start/end times that do not match their text. For example, alt text is sentences 0-2 (ends at 504.15 absolute) but its end is 510.0; hook text is sentences 5-6 (ends at 114.35) but its end is 119.0. This means the test does not actually provide sentence-aligned passages, and the production code may be selecting windows based on text rather than the passage boundaries, so the test does not validate sentence-aligned window selection or boundary handling.
- deepseek: [medium] The test does not assert per-channel or per-video caps or the score floor, so a cap bypass or floor bypass would not be caught.
- qwen27b: [high] The alt passage (the expected fallback) has text covering sentences 0-2 of BBB, which spans only ~7.05 s (relative 2.0 to 9.05). This is well below the 12 s clip minimum (CLIP_MIN_S). If the production code correctly enforces the 12-20 s budget, the alt window would also be rejected, and the test's expectation that it is 'accepted' is wrong. The test either encodes an incorrect expectation or the production code has a budget-bypass bug that the test inadvertently validates.
- glm: [medium] All three fixture passages' start/end/duration fields disagree with the synthesized word timings, so the 8-12s hook and 12-20s clip budgets are never actually exercised against real word times.
