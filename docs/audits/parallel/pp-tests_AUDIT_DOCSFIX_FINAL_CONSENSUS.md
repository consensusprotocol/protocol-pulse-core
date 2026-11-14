# pp-tests_docsfix — FINAL CONSENSUS (two cycles; written by the session, 2026-11-14, after the 10:02 merge)

Diff audited: the docs-only commit on top of d1ccdfc7 (pp-tests_REQUESTS.md, pp-tests_STATE.md,
pp-tests_BIBLE_ADDITIONS.md; no test changed). Brief: pp-tests_AUDIT_DOCSFIX_BRIEF.md. The session writes the
consensus because the repo tool's consensus step (claude-sonnet-4-6) cannot run: Anthropic is out of credit. Rule
(pp-ingest's): consensus = the same finding from >= 2 reviewers, or one reviewer's finding verified against the text.

## What the diff does
- R-29's "effect" is corrected. The stale-title cases were not passed: the gate rejected them on the dated sign-off.
  The builder's fix (91d37100, on origin/pp-selectid, not yet on the release line) is recorded.
- R-30 is restated as a decision for the orchestrator (NUMBER and the manifest's date), not a request. Both branches
  of the ruling and their acceptance are stated, and the builder's interim scoring is recorded.
- A decision item on the PRICE_NOW tolerance, independent of R-30.
- STATE records the merge, the corrected exam section and the commit times (from git).
- BIBLE: PP-E28 corrected; PP-E33 ("verdict-only scoring credits a must-fail case rejected for the wrong reason").

## Cycle 1: pp-tests_AUDIT_DOCSFIX_C1_*.md
- gemini-2.5-pro 100, Heimdall qwen3.8-27b 95, Heimdall glm-5.3-flash 88.
- Implemented (pp-tests_AUDIT_DOCSFIX_C1_CONSENSUS.md):
  - both R-30 branches, from qwen and glm (consensus);
  - "the 14 are not measured yet";
  - the class-C source cited (pp-tests_AUDIT_INTEG_BRIEF.md "Order 2", checked);
  - "the builder REPORTS", with PRICE_NOW by absence;
  - commit times from git. glm's ordering note led to it: a hand-typed "~10:20" was really 09:52;
  - R-29's fix located on origin/pp-selectid, with its audit record named;
  - PRICE_NOW independent of R-30.

## Cycle 2 (the tool's cycle-2 template, on the diff after cycle 1): pp-tests_AUDIT_DOCSFIX_C2_*.md
- gemini-2.5-pro: "Yes", nothing to change.
- Heimdall qwen3.8-27b: "Yes".
  - "Verify the Order 2 citation": done before cycle 2. The brief's line 31 is "### Order 2 — orchestrator 05:25 ET",
    and its class (C) PRODUCTION is at line 35.
  - "Hole hidden by another line is a report category": DONE, said in so many words.
- Heimdall glm-5.3-flash: "Yes with conditions", three P2s:
  - the 16 / 14 split's source: DONE, "by the corpus's own labels (`expected.verdict`), not from a run", in REQUESTS
    and STATE;
  - the approval condition: DONE, satisfied by the 10:02 merge (d1ccdfc7, the tests), and this docs commit does not
    gate the exam;
  - "explicit current_levels still win": DONE, now "in a case ... over the levels derived from its universe".
  - P3s taken: regression_test.sh named everywhere in STATE; the docs entry points to `git log -1 --format='%h %ci'`
    for its hash and time. Bolding: not acted on.

## Outcome
No P0 or P1. No text asks for a check to be loosened. No test changed. Spend of this audit: $0.131 (gemini-2.5-pro
2 calls $0.125, Heimdall $0.006); the session's audit ledger stands at $2.423 of the $3.00 cap.
