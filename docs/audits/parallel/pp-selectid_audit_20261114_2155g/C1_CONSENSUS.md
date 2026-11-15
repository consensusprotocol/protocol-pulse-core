# Cycle 1 consensus: pp-selectid audit 20261114_2155g (ruling 107 (1): the guard that makes a no-news build $0.00)

Reviewers under ruling 107 (2): qwen3.8-27b and glm-5.3-flash. Both raised P0/P1s, so they agree and Grok was not
asked. Cost: $0.0060 vendor-reported.

IMPLEMENTED:
- qwen P1 (open_work by string search is fragile). It now walks the structure: _errors() counts every object anywhere
  whose "verdict" is "error". Tests: a nested error counts; a log string quoting the phrase does not.
- glm F4 (--routing decides which models judge, but was not in the fingerprint). fingerprint(..., routing=a.routing).
  Test: "today" and "heimdall_first" fingerprint differently. The config's routing mode is already in code_content
  (pipeline/model_providers.json).

REFUTED, with evidence:
- glm F11 ("the next build's pool depends on this build's outputs, so the guard never fires"). The pool comes from
  ledger_build.build_inputs over pp-ingest's ledger rows and the word records. This build's outputs (the pre-check
  answers, the scorer verdicts, the registry) never feed it. Measured: the same 157 moments were byte-identical in
  every field between builds ledger_20261114_183413 and _192056. The integrator's outputs are fingerprinted separately,
  as they stand at the END of the build that read them.
- glm F2 ("now makes the fingerprint time-varying"). Only CA.due(reg, now) reads now: the list of DUE candidates, not
  a time. It changes only when a candidate comes due, which is new work. The ET day changes at midnight, which is also
  new (the show date). Tests: three hours later the fingerprint is equal; a candidate coming due moves it.
- glm F1 / qwen (the newest decides). By design and as documented: the newest FINISHED build decides. A stopped or
  skipped build writes no FINGERPRINT.json and is passed over. Tested.
- glm F5 (a moment without video_id): every moment record has video_id (eligibility.Span / moments.record).
- glm F7: the test's registry has no resting candidate, by intent. The resting case has its own test.
- glm F3: superseded by the structural walk above.
- glm F6: the skip writes inputs.json and NOTHING_NEW.json and no package.json, by intent: no build ran.

Mutations: 9 of 9 killed (work left undone ignored; pool, code, day, due candidates or pre-check answers left out; the
driver never stopping; an older match counting; held work not counted).
