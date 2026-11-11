# 1b FIX (punctuation layer; model adjudicator removed) — audit dispositions (2026-11-11 ET)

Evidence that triggered the fix: ADJUDICATOR_EVIDENCE_yahoo_sweep.jsonl (this folder): the per-gap
gemma3:27b adjudicator answered "sentence end" for every Yahoo Finance gap it was asked about, 'the | Wolf',
'of | all', 'is | up', 'pretty | massively' included (E-FAIL-013).

Cross-LLM (GPT-4o / Grok / Gemini, 2 cycles): 9.9/10, unanimous zero defects, READY.
- M1 (all three): a dedicated unit test of the alignment key `_key()`: IMPLEMENTED
  (TestPunctuationLayer.test_alignment_key_contract). The suggested `it's == its` is deliberately NOT the
  contract: apostrophes stay (different words); only the curly apostrophe folds to the straight one.
- U1 (Gemini) "_whisper_transcribe control flow takes a moment to parse": not a defect; left as is.

Heimdall (deepseek / qwen27b / glm, per-file chunks):
- run_fresh.py, select_passages.py, test file: PASS, no findings.
- punctuation.py [low, 3/3] provenance recorded "large-v3" regardless of the model passed: IMPLEMENTED
  (`ensure(..., model_name=)`, the caller passes its model's name).
  Unvoted: "a failed restoration is cached as done" — not a defect: the reference decode is deterministic
  (beam search, same audio, same prompt), a retry yields the same marks; the record says
  `still_unpunctuated`, and the law fails closed on those stretches (TestUnpunctuatedTranscript).
  "language='en' hard-coded": the pipeline is English-only; the verbatim decode is `en` too.
- sentence_law.py [low, qwen27b] "external callers may still pass adj": voted DISAGREE in cycle 2 (not a
  defect). Verified anyway: `grep -rn "edge_plan(\|write_lock_cut_table(\|gate_g16(\|boundary(" pipeline/`
  shows every caller on the new signatures; test_pinned patches write_lock_cut_table with *a, **k.

Regression: regression_test.sh 26 PASS 0 FAIL 4 WARN; pipeline/regression.sh PASS (69 passed, parity
0.041 s). Suites: test_pulse_20261110_mustfail 30 (the GPU reproduction of the fixture's punctuated
transcript included), test_pinned / test_sentence_windows / test_window_review / TestSelectCoords 53 passed.
