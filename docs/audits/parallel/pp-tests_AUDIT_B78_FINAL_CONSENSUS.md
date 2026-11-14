# pp-tests_batch78 — FINAL CONSENSUS (two cycles; written by the session, 2026-11-14 ~09:00 ET)

Diff audited: the commit that answers the integrator's audit batch 78 (tests/adversarial and docs/audits/parallel/
pp-tests_* only). Brief: pp-tests_AUDIT_B78_BRIEF.md (one "## THE LAWS" section; extraction replayed: 11,414 of 11,509
bytes reach the reviewers). The session writes the consensus because the repo tool's consensus step (claude-sonnet-4-6)
cannot run: Anthropic is out of credit (HTTP 400 at 08:27 ET). Rule (pp-ingest's): consensus = the same file, function
and root cause from >= 2 reviewers, or one reviewer's finding verified against the code; refutations carry evidence.

## Cycle 1 (the repo tool's own package): pp-tests_AUDIT_B78_C1_*.md
- gemini-2.5-pro 96, Heimdall qwen3.8-27b 94, Heimdall glm-5.3-flash 92: all "ready", no P0. gpt-4o: OpenAI 429.
  Grok: not run (unmetered).
- Implemented (pp-tests_AUDIT_B78_C1_CONSENSUS.md):
  - Gemini P2: ONE list for the three network guards, child_guard/netguard_names.py, plus a test that the runner
    refuses every listed call.
  - glm P1: the automated PP-E31 check, test_keys_are_read_only_by_name_through_the_pipelines_loader. Mutation: a suite
    file naming the key file fails it.
  - glm P3: the unscanned-names check also covers packages.
  - glm: two docstrings.
- Refuted with evidence:
  - qwen's relative or env-var loader path: relay.py finds its key file beside itself, and an env path would choose
    the code that runs.
  - glm's "spec None -> AttributeError": measured as FileNotFoundError naming the path.
- Not acted on, with reasons: qwen's `_calls` reset and .pth test; glm's "unexercised" toy functions.

## Cycle 2 (the tool's own build_cycle2_prompt, on the diff AFTER the cycle-1 dispositions)
- gemini-2.5-pro: "Production ready: Yes"; no remaining issue.
- Heimdall qwen3.8-27b: "Yes". P2: the both-lookups assertion needs >= 2 exclusion rows; the runner's path to the
  shared list is fixed by the suite's layout.
- Heimdall glm-5.3-flash: "Yes with conditions".
  - P2 N5, the evidence count 381 -> 382 does not close against three new tests.
  - P2, put len(rows) in that assertion's message.
  - P2 N3, the refusal message of a sendmsg without an address shows its flags.
  - P3 N8, the test depends on refuse_network overwriting the child guard: document it.
  - P3 N4, PP-E29 should say the list is shared and the exception type / restore behaviour are not.
  - P3, PP-E31 should record "an env-chosen loader path is executed code".
- Dispositions:
  - The >= 2-rows coupling: CONSENSUS (qwen and glm). DONE: the message carries len(rows), plus a comment
    (33 rows today).
  - N5: ALREADY RESOLVED. glm read the diff built at 08:35, before the session regenerated the evidence. The file was
    then regenerated from a fresh two-run measurement after the two new tests: "384 others" (381 at 621604bb + 3 new
    tests: the reverse-lookup parameter, the key-rule test, the runner-coverage test). It was regenerated again after
    the cycle-2 edits: still 384.
  - N3: VERIFIED and DONE in both guards that print a target, through one shared function,
    netguard_names.refused_target. A sendmsg without an address now reads "to 'its connected peer'"; with one, the
    address. Checked directly under the conftest guard.
  - N8, N4, the PP-E31 clause: DONE (docstring, netguard_names docstring, BIBLE).
  - qwen's layout coupling: NOT ACTED ON (the suite's own fixed layout).
  - glm's repeated "AttributeError on a missing loader": REFUTED, as in cycle 1.
  - glm N6 (default-encoding open(), house-wide): recorded only.

## Outcome
No P0 or P1 stands. Nothing implemented loosens what a check accepts; three checks are stricter than before (the
runner's own refusal named, the key rule automated, packages in the unscanned-names check). Spend of this audit:
$0.170 (gemini-2.5-pro 2 calls $0.160, Heimdall qwen 2 calls $0.007, Heimdall glm 2 calls $0.003); the session's audit
ledger stands at $2.019 of the $3.00 cap.
