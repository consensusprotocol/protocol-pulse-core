# Heimdall audit

**Question:** DEC-10 recut 12:22 (runs/pinned_20261111_172202) found a cutter defect: with no quiet run between two words, find_valley searched the envelope minimum from the first word's transcript end - 80 ms to the second word's start + 80 ms, so for Natalie 'rally.' (80.40-80.78) | 'But' (80.86-81.02) it picked 80.93, the stop closure INSIDE 'But', and the cut kept 'Bu' (80.85-80.89 at -13 dB); neighbour_clear passed trivially because the cut equals that point; G3c failed the render's tail. Fix: VALLEY_MARGIN_S 0.080 -> 0.010 (one 10 ms hop) and the slice made inclusive at both ends (SourceAudio.sl is half-open). The quiet-run search deliberately stays between the two words' midpoints (narrowing it to the transcript gap broke the v2f hook OUT and Nov 10 D3c references, whose real pauses sit 100+ ms off Whisper's word edges). Tests: real-source regression (boundary and accepted cut before 'But' < 80.85; the old 80 ms margin reproduces the defect). Find real defects only: can the minimum still land inside a word, can the inclusive end reach past the next word's start by more than one hop, any interaction with boundary_geometry / neighbour_clear? (this chunk: pipeline/sentence_law.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0121
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [low] The effective search window still extends one hop (10 ms) into each adjacent word, so the envelope minimum can land inside a word. In the Natalie case the window is [80.77, 80.87] and the last included sample (80.87) is 1 ms inside 'But' (80.86–81.02). This is a deliberate design trade-off (±1 hop) and a large improvement over the old 80 ms, but it means neighbour_clear must still reject a cut that falls inside the next word's extent; if neighbour_clear only checks 'cut ≠ word edge' rather than 'cut outside [start, end]', a 10 ms interior point could pass. (agree: 0)

## Added in cross-examination (not voted on)
- none
