# Heimdall audit

**Question:** DEC-10 recut 12:22 (runs/pinned_20261111_172202) found a cutter defect: with no quiet run between two words, find_valley searched the envelope minimum from the first word's transcript end - 80 ms to the second word's start + 80 ms, so for Natalie 'rally.' (80.40-80.78) | 'But' (80.86-81.02) it picked 80.93, the stop closure INSIDE 'But', and the cut kept 'Bu' (80.85-80.89 at -13 dB); neighbour_clear passed trivially because the cut equals that point; G3c failed the render's tail. Fix: VALLEY_MARGIN_S 0.080 -> 0.010 (one 10 ms hop) and the slice made inclusive at both ends (SourceAudio.sl is half-open). The quiet-run search deliberately stays between the two words' midpoints (narrowing it to the transcript gap broke the v2f hook OUT and Nov 10 D3c references, whose real pauses sit 100+ ms off Whisper's word edges). Tests: real-source regression (boundary and accepted cut before 'But' < 80.85; the old 80 ms margin reproduces the defect). Find real defects only: can the minimum still land inside a word, can the inclusive end reach past the next word's start by more than one hop, any interaction with boundary_geometry / neighbour_clear? (this chunk: pipeline/test_dec10_edges.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0107
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_dec10_edges.py:96** The skip condition only checks for the source video, but setUpClass immediately opens the transcript JSON. If the source exists and the transcript is missing, the test errors instead of skipping.
  - evidence: `@unittest.skipUnless(os.path.isfile(os.path.join(NOV10, "sources", "lusJ1m-J0Mc.mp4")), "frozen Nov 10 sources not here") ... cls.words = json.load(open(os.path.join(NOV10, "transcripts", "lusJ1m-J0Mc`
  - fix: Include the transcript file in the skip condition, e.g. skip unless both the source and transcript files exist.
  - raised by deepseek:F3; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F1 [medium] The boundary assertion allows the point to equal the next word's start. Because the fix made the slice inclusive at both ends, equality means the slice includes the next word's first sample, so the test does not fully guard the inclusive-end defect. (agree: 1)
- deepseek:F2 [low] The old-margin regression only checks that the point is after the next word's start, not that it is inside the word. It could pass if the point lands after the word's end, so it does not actually verify the described 'inside the next word' defect. (agree: 0)

## Added in cross-examination (not voted on)
- deepseek: [medium] Test does not assert the boundary point is after the first word's end, so the minimum could still land inside 'rally.' because the search window extends 10ms before its end.
- deepseek: [medium] Test only checks cut_out value, not the actual inclusive slice end, so the slice could include samples past the next word's start by one hop.
- deepseek: [low] Test does not check neighbour_clear or boundary_geometry interaction, so a trivially passing neighbour_clear would not be caught.
- deepseek: [low] Docstring incorrectly states the boundary is searched in the transcript gap, but the fix keeps the search between the two words' midpoints.
