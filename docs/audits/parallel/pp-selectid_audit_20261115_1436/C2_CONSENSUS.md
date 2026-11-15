# C2 CONSENSUS — pp-selectid audit 20261115_1436 (ruling 115 (3)'s question-with-examples driver)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and glm-5.3-flash (0): they agree, Grok was not asked. Cycle 2: $0.0043; the
audit $0.0349 vendor-reported. No P1; no third cycle. The cycle-1 fixes (the answering model on every row and in the
verdict, run() / report() tested, the $0.50 router ceiling) were checked.

THE P2s, answered:
- glm N6 "qwen's way back ('agrees at ruling 85's bar') is not measured". Deliberate: the order makes it a condition
  that only matters when qwen PASSES both tests ("qwen wins the job back if it passes both and agrees"). It is run
  then, and only then (replay85's agreement on the 48 rated moments, Grok against qwen on the v2 question), and its
  cost reported first. The report says which case holds.
- glm N1 / qwen F1 "the row's backend vocabulary vs MODELS": the chain is [MODELS[key]], so the answering back-end's
  name IS that string (providers.Reply.backend is the chain entry's name); a record without one prints "by None" and
  counts as no rating (fail closed).
- glm N2 "the last call before the stop can pass STOP_USD": by design (no call STARTS at the stop); the router's $0.50
  ceiling bounds it; a Grok call is ~$0.005.
- qwen F4 / glm "the negatives test reads the proof builds": deliberate (the driver's input is those builds).
- glm N4 / N5 / N8 (report-only staleness, a message's wording, an unknown --models key raising after a spend): P3;
  the JSON carries its "at"; the model keys are fixed.

FINAL DIFF: FINAL.diff (written at landing). Tests: 6 offline, all pass.
