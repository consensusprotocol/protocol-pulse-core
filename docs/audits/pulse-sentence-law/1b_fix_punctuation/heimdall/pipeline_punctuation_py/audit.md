# Heimdall audit

**Question:** Sentence-law fix. The per-gap local-model adjudicator for unpunctuated transcripts was found to be a rubber stamp (gemma3:27b called 19 of 19 Yahoo Finance gaps sentence ends, including 'the | Wolf', 'of | all', 'is | up'). It is removed: sentence_law.boundary now returns invalid for any gap in an unpunctuated stretch (fail closed), and the adj parameter is gone from boundary, edge_plan, write_lock_cut_table, gate_g16 and their callers. Punctuation now comes from the ASR: select_passages._whisper_transcribe keeps the verbatim decode's words and, only where the transcript is unpunctuated, runs pipeline/punctuation.ensure, which decodes the same audio again with a neutral punctuated initial_prompt and copies trailing punctuation onto verbatim words in difflib equal blocks only (word keys asserted unchanged). Verify from the diff: (1) no path lets a gap without terminal punctuation become a sentence boundary; (2) transfer can never change, add or drop a word, and never puts a mark on a word the two decodes disagree on; (3) cached transcripts are re-punctuated or returned unchanged correctly; (4) no caller still passes the removed argument; (5) the must-fail tests (D3b's new reason, the rejected false ends, the reproduced fixture) are meaningful, not vacuous. Only state what you can verify; if uncertain, say so. (this chunk: pipeline/punctuation.py)

**Panel:** deepseek, qwen27b, glm  |  **Cost:** $0.0119
## Consensus findings (majority of panel agrees)
- **[low] pipeline/punctuation.py:63** Hardcoded model name in metadata does not reflect the actual model passed to reference_decode. If a caller passes a model other than 'large-v3', the recorded metadata will be incorrect.
  - evidence: `"model": "large-v3", "prompt": PROMPT, "marks_transferred": moved,`
  - fix: Capture the model identifier from the `model` parameter (e.g., `getattr(model, 'model_size', 'unknown')` or pass the name explicitly) and use it in the metadata dict instead of the literal string.
  - raised by qwen27b:F1; agree: deepseek, qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [medium] Failed punctuation attempts are cached as successful, preventing re-punctuation.
- glm: [low] reference_decode hardcodes language="en" while the verbatim decode's language is not shown here; a non-English transcript would get an English-prompted reference decode and likely few matching blocks (harmless — transfer just moves 0 marks and still_unpunctuated stays true, failing closed).
- glm: [info] ensure() records still_unpunctuated in metadata but does not itself fail when restoration is incomplete; the fail-closed behavior presumably lives in sentence_law.boundary (not in this chunk), so I cannot verify from this diff that an unpunctuated gap after transfer is actually rejected rather than silently treated as a boundary.
