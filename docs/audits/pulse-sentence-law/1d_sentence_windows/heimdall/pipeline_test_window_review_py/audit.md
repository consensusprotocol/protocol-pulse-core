# Heimdall audit

**Question:** Commit 1d makes selection propose sentence-aligned windows: abbreviation-aware sentence splitting (sentence_law.is_terminal), windows of one to three whole sentences (interjection-only sentences transparent per PBX D4a), clip budget 12-20 s, the editor's hook/clip slots honoured, and a window the sentence law rejects replaced by the next-ranked legal candidate of the same kind (score floor, budget, overlap, per-channel and per-video caps) instead of moving a cut. Find defects: a path that can pick an illegal/overlapping window, a cap or floor bypass, wrong window bookkeeping, a fallback that can loop or silently drop the hook. (this chunk: pipeline/test_window_review.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0115
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
