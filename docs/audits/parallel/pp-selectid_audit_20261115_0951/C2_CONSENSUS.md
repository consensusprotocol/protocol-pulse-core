# C2 CONSENSUS — pp-selectid audit 20261115_0951 (the word pass's refused moments, counted apart)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0) and glm-5.3-flash (P1_OR_WORSE: 0). They agree, so Grok was not asked. Cycle 2:
$0.0034 vendor-reported. AUDIT TOTAL: $0.0375 vendor-reported (cap $1.00: 166 changed lines). Both say production
ready. No real defect was found in cycle 2, so there is no third cycle (ruling 107 (2)).

AGREED: the worker mirror (worked_by_worker, refused = worked - ready) fixes cycle 1's real defect. The one-call
contract is documented. The waiting count cannot go negative (glm withdrew its C1 concern after tracing it). The
per-video refused map is right. glm's new N1 dissolved on its own trace: the two waiting counts agree.

THE CONDITIONS, AND WHAT STANDS:
1. qwen: "the integrator confirms BLOCK is unchanged since b22a5e56 and will report changes". DONE. The integrator, 10:02
   ET Nov 15: "What you mirror is current as of b22a5e56 and 2585e84f ... I'll tell you whenever passed_ids,
   blocked_failure or BLOCK in pipeline/word_pass_worker.py changes, before or with the merge". It is a contract in the
   integrator's handoff, section 5.
2. glm N5 / qwen: "kill the surviving ruling-95 mutation with a one-line capture in the harness". NOT POSSIBLE AS ONE
   LINE, so it is left and recorded. test_ruling_107_guard's run_driver ends before the driver's next_attempt call:
   left=0 stops at "nothing new", and left=1 raises at build_router. Reaching the call needs a fake router through
   both builds; the existing harness has never gone that far. The keyword is checked by reading the code
   (tests/package/proof_ledger.py:510 is the only caller). The next real build's ruling-95 log line, which now reads
   "ready / waiting / refused", shows it working.
3. glm N2: "a one-word comment that the `not in word_pass` guard keeps ready and refused disjoint". NOT APPLIED here, so
   the code landed is the code audited. It goes into the next audited change to pipeline/spotlight.py.
4. qwen P3s: "the log and funnel wording, 'not sentence-ready or failed', simplifies 'worked, with no usable window'".
   Noted. The docstring states the exact rule; the wording waits for the next audited change to those lines.
5. The two surviving mutations (R11, the driver's ruling-95 keyword; R12, the funnel report script's line) are
   acknowledged as acceptable. Neither changes a build.

THE CODE AS AUDITED IS THE CODE LANDED: FINAL.diff, identical to C2_STEP.diff. Mutations: 16 of 18 killed after a
control run; suites: 684 pass.
