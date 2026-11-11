# Batch 8d (valley search inside the transcript gap: the cut kept 'Bu' of the next word): dispositions

Why: recut #2 (runs/pinned_20261111_172202, HEAD 29299ea5) failed G3c on clip_01's tail (-22.4 dB vs limit
-31.7). Natalie 'rally.' (80.40-80.78) | 'But' (80.86-81.02): with no quiet run between the words, find_valley
searched 80.70-80.94 (transcript edges +- 80 ms) and took 80.93, the stop closure INSIDE 'But'; the cut kept
'Bu' (80.85-80.89 at -13 / -14 dB) and neighbour_clear passed trivially (cut == point). G3c caught it.

Fix: VALLEY_MARGIN_S 0.080 -> 0.010 (one hop), slice end + HOP_S (SourceAudio.sl is half-open). The quiet-run
search stays between the two words' midpoints: narrowing it to the transcript gap was tried and broke the v2f
hook OUT edge and the Nov 10 D3c control, whose real pauses sit 100+ ms off Whisper's word edges (recorded in
the code comment). Natalie's out edge is now the true minimum 80.84 (-22 dB), before 'But' bursts at 80.85.

Audited: cross-LLM GPT-4o + Gemini (Grok blocked: xAI ceiling): no P0 / P1, one P2. Heimdall deepseek + qwen27b.

## Implemented
- Cross-LLM P2 [both]: the slice comment said "both ends inclusive (sl is half-open)"; now "sl is half-open:
  + HOP_S so the window's end frame is in".
- Heimdall consensus [low] (deepseek F3, both): the real-source test skipped on the source only; it now skips
  unless both the source and the transcript exist.
- Heimdall deepseek F1 [medium, agree 1]: the boundary assertion allowed the point to equal 'But''s start; now
  strictly before it (point 80.84 < 80.86; the cut assertion stays < 80.85, the burst).
- Heimdall deepseek F2 [low, agree 0]: the old-margin must-fail now asserts the point lies INSIDE 'But'
  (start < point < end), the defect itself.

## Recorded, not changed
- Heimdall qwen27b F1 [low, not agreed]: the window still reaches one hop (10 ms) into each word, so a minimum
  can sit up to 10 ms inside a word and neighbour_clear passes a cut at that point trivially. Accepted as the
  measurement resolution (10 ms hops); the render's G3c tail / head check is the backstop that caught 80.93.
