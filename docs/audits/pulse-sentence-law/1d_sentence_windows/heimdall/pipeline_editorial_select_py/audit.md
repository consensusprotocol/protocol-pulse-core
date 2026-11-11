# Heimdall audit

**Question:** Commit 1d makes selection propose sentence-aligned windows: abbreviation-aware sentence splitting (sentence_law.is_terminal), windows of one to three whole sentences (interjection-only sentences transparent per PBX D4a), clip budget 12-20 s, the editor's hook/clip slots honoured, and a window the sentence law rejects replaced by the next-ranked legal candidate of the same kind (score floor, budget, overlap, per-channel and per-video caps) instead of moving a cut. Find defects: a path that can pick an illegal/overlapping window, a cap or floor bypass, wrong window bookkeeping, a fallback that can loop or silently drop the hook. (this chunk: pipeline/editorial_select.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0213
## Consensus findings (majority of panel agrees)
- **[low] pipeline/editorial_select.py:527** n_sentences bookkeeping uses raw sentence count (b - a + 1) while the new cap logic uses _n_sentences which excludes interjection-only sentences. A legal window of 4 sentences (3 content + 1 interjection) reports n_sentences=4, exceeding MAX_WINDOW_SENTENCES=3. Any downstream consumer that validates n_sentences against MAX_WINDOW_SENTENCES will incorrectly reject a legal window.
  - evidence: `"n_sentences": b - a + 1, "text": " ".join(w["word"].strip() for w in words[sents[a][0]:sents[b][1] + 1]),`
  - fix: Change to "n_sentences": _n_sentences(words, sents, a, b) to match the cap semantics, or add a separate field (e.g. "n_content_sentences") so the raw count and the cap-relevant count are both available without ambiguity.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [low] _ends_statement allows a window to end on a question if the word ends with '!' after '?', e.g., 'What?!', because it only checks endswith('?') after stripping quotes. This violates the statement-end rule.
