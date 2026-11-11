# Heimdall audit

**Question:** Protocol Pulse news-video pipeline verification (no publishing). Changes on top of an audited batch: (1) the visual checklist's credits question now gets the channel list from the edit decision list (a 9:16 crop can hide a show's branding); (2) the 'next shot visible before a cut' line is answered one cut at a time: the frame 3 frames before and 3 frames after each cut, side by side, asked of two vision models; any 'yes', missing answer or error fails; the whole-sheet answer for that line is kept only as advisory; (3) a vision reply missing up to 3 final closing braces is closed before parsing (nothing else repaired); (4) a new deterministic gate G19: on each finished video, no hard shot change (ffmpeg scene score >= 0.3) inside a talking-head segment's clean span before its first word or after its last word, with speech times from the prepare stage's record, failing closed without a record; (5) batch-6 audit fixes (stand-alone subject terms, replay catch-all, shot-snap test strengthening, a reason string). Find real bugs: a check that can pass when it should fail, wrong frame/time arithmetic, a repair that accepts a reply the model did not give, a gate that ignores a segment. Only state what you can verify from the diff. (this chunk: pipeline/stand_alone.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0052
## Consensus findings (majority of panel agrees)
- **[high] pipeline/stand_alone.py:74** The new fallback `words or {"bitcoin", "btc"}` returns Bitcoin/BTC for a non-Bitcoin story whenever no subject words are extracted. This can happen when the subject is only in the headline (the function only extracts from `affected_object`) or when all subject words are filtered out (e.g., short words like 'AI'). In those cases a Bitcoin aside will pass as a clip of a non-Bitcoin story, contradicting the stated rule that a Bitcoin aside is not a clip of that story. This is a check that can pass when it should fail.
  - evidence: `return words or {"bitcoin", "btc"}`
  - fix: Do not fall back to Bitcoin/BTC for non-Bitcoin stories. Return an empty set or a sentinel that fails closed, and extract subject words from both `affected_object` and `headline` (e.g., `_words(f"{affected_object} {headline}")`) so the fallback is not triggered by missing headline words.
  - raised by deepseek:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
