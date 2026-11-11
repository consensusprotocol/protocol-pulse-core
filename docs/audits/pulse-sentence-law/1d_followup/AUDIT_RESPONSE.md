# 1d follow-up — audit dispositions (2026-11-11 ET)

Cross-LLM (GPT-4o / Grok / Gemini, 2 cycles): 9.5/10, no defects in the changed code.
- P2 "name the slot-ordering hazard at the check": IMPLEMENTED (comment above the `p is first` check).
- P2 "ONSET/TAIL, CREDITS, Law 22 unverifiable from this diff": enforced outside this diff, committed:
  G17a/G17b + D1 pad (99add647), credits render + G12/G15 (3641440f), Law 22 re-render proof (9aa4fdb2).
- P2 "system-level law test": the end-to-end proof is the Phase 4a full re-cut with every gate on.

Heimdall (deepseek / qwen27b / glm, per-file chunks):
- select_passages chunk [low] "claim 3 unverifiable from this chunk": scope of the chunk. Evidence: the
  three TestNextRankedFallback tests run against HEAD's select_passages.py: 2 of 3 fail (duplicate clip;
  no locked-span rejection), all pass against the fixed blob (scratchpad sp_head/run_head.py).
- test_fresh chunk "does not exercise Q1/Q2": scope; Q1/Q2 are exercised in test_sentence_windows.py.
  The test_fresh change is a fixture correction: its declared windows (11 s / 14 s) wrapped 4.6 s /
  7.15 s of text, which the new locked-span budget check correctly rejects (E-FAIL-012).
- test_sentence_windows [high] "word_start should include the window offset": REJECTED, false premise.
  EDL times are source-file coordinates by design (`time_coords: "source_file"`, asserted by
  TestSelectCoords); the test passes against the implementation.
- test_sentence_windows [low] mkdtemp leak: FIXED (addCleanup). Unvoted F2 bare open(): FIXED
  (_dump/_load). Unvoted F3 "boundary report missing on failure": not an issue — select_and_build_edl
  writes SELECT_BOUNDARIES.json in a `finally`.
