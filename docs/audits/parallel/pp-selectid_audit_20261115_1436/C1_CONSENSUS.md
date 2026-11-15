# C1 CONSENSUS — pp-selectid audit 20261115_1436 (ruling 115 (3)'s question-with-examples driver, tests/package/hook115.py)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0), glm-5.3-flash (1); they disagree on a P1, so Grok was asked (0). Cycle 1:
$0.0306 vendor-reported. No paid call of the driver has been made.

THE P1 (glm F5): "nothing asserts which model answered: if the Router fell back to another model, the report would
credit the wrong one". The chain is one model (r.chains["coherence_verdict:hook"] = [model]; providers.Router.call
tries only its chain, and call_parsed skips a model that answered out of contract, so a one-model chain cannot reach
another: tests/providers/test_providers.py covers both). FIXED anyway, as the report's own guarantee: each row keeps
the answering back-end (hook_ratings' record "backend"), the report prints it on every rating ("by <model>"), and
verdict(rows, model) counts a rating ONLY when the named model gave it (else it is no rating, and the model does not
pass). New test.

ACTED ON:
- qwen P2 "the router limit $0.55 is above ruling 115's $0.50 cap": LIMIT_USD is now $0.50 (the router reserves each
  call's list-price upper bound, so it sits above our own stop on reported spend, STOP_USD $0.25).
- glm F8 "run() and report() are never exercised": NEW TEST with the calls stubbed: both models, both variants, ten
  rows each; as ordered every example is in the prompt; leave-one-out leaves the rated item out; the rows carry the
  answering model; past STOP_USD no call is made (7 rows "stopped", 3 calls); the JSON and REPORT.md are written.
- The final spend read no longer constructs a ledger when none exists.

NOT CHANGED:
- glm F1 "a stopped row reads like a rating failure in the verdict": the row says "stopped at $x" in the report's
  every-rating list; the verdict fails closed (no rating = no pass), which is right for "takes the job only when".
- glm F2 "rate() drops err when a record exists": one candidate a call, so a record means no error for it.
- glm F7 "the order says 'rates ... 4 or more': the own-job rating min(scroll, alone)": that is the rating ruling 113
  (2)'s law reads (ruling 61); the report gives every part beside it, setup included.
- Grok P2 "the negatives test reads the proof builds": deliberate; the driver's whole input is those builds, and the
  test pins that the five are found rated 2 with their texts.
- Grok P2 "partition('\n\n')": it splits at the FIRST blank line only (as split(..., 1)); the test pins the block
  right after the first paragraph and HOOK_QUESTION unchanged.

TESTS: 6 offline (was 4), all pass.
