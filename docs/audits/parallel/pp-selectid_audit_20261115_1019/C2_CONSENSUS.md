# C2 CONSENSUS — pp-selectid audit 20261115_1019 (ruling 95's refused count in the driver: a name collision)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0, "PRODUCTION READY? Yes") and deepseek-v4.1-flash (P1_OR_WORSE: 0). glm's
breaker was still open. They agree, so Grok was not asked. Cycle 2: $0.0038 vendor-reported. AUDIT TOTAL: $0.0283
vendor-reported (cap $0.30: 39 changed lines). No real defect, so no third cycle (ruling 107 (2)).

WHAT STANDS:
1. The surviving mutation (D5: res["next_attempt"] set to {} past the router). Both reviewers accept the stated gap.
   deepseek would prefer a regression test. Its suggestion, an assertion in the existing router test, cannot see a
   build record: that test raises at build_router, by design ("a router was built"). So the gap is recorded, with
   two guards:
   - a runtime check on the first real build after this lands: package.json "next_attempt" == inputs.json
     "next_attempt", refused counted, and the ruling-95 log line printing it; the result goes on that build's STATE
     line;
   - this audit's record of the lesson: the defect it fixes was itself a surviving "untested wiring" mutation.
2. deepseek [P2] "the timing shift assumes build_inputs and with_variants do not mutate rows or wp". Checked by reading.
   - build_inputs copies what it keeps from a row (dict(r["scores"]), dict(r.get("mined") or {}, ...)), and reanchor and
     window_source only read the row and its word-pass entry.
   - with_variants works on moments and sources, not rows or wp.
   - The stages that used to run before the late computation (PK.build, SPOT.build, the pins) never receive rows or wp.
   So the early value is the value the late call computed.
3. qwen / deepseek [P3] "the comment split across try / except; 'reads the inputs alone' means the raw inputs (rows, wp,
   now, wp_refused), not the inputs dict". NOT APPLIED, so the code landed is the code audited. The meaning is stated
   here.
4. deepseek [P3] "the test indexes na['conversation'] and uses now for published_at". Kept. A missing "conversation" key
   fails the test loudly, which is wanted. The counts checked do not depend on the time: next_attempt counts a video's
   rows whatever their age.

THE CODE AS AUDITED IS THE CODE LANDED: FINAL.diff, identical to C2_STEP.diff (tests/package/proof_ledger.py,
tests/package/test_ruling_107_guard.py). Suites: 685 pass. Mutations: 4 of 5 killed after a control run.
