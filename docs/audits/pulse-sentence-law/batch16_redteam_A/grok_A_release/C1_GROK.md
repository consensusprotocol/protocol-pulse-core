**Q1: CORRECTNESS**  
Yes for all changed functions visible in the diff. `stage_gates` (run_fresh.py:87-296) now records exact verdicts + evidence via `put`/`_samples` and delegates blockers to release_auth; `attest_run` (355-382) and `verdict_for` (303-308) enforce terminal state + inventory before any candidate; `release_auth.blockers`/`attest`/`authorise` (580-727) reject missing/zero-sample/non-PASS rows and re-verify bytes on disk. No silent exceptions that produce PASS; every missing or malformed path yields HOLD. No time/index arithmetic or unit conversions appear in this diff.  

**Q2: LAW COMPLIANCE**  
- L-a, L-b, L-c, L-j: COMPLIANT (run_fresh:155-163 G20, 206-249 G17c + final-only proof via `edges_on_final`, 285-382 attestation last, release_auth:555-611 exact REQUIRED rows + evidence).  
- L-d, SELECTION_LOCK, SNAP_LIMIT, SENTENCE_LAW constants: not modified in this diff (PARTIAL).  
- No loosened thresholds, no recomputation of locked words, no v2f divergence.  

**Q3: TESTS**  
`test_release_auth.py` (new) exhaustively mutates every REQUIRED row, evidence field, bound file, pack, and run_state; each case asserts HOLD with the precise reason. `test_story_ledger.py` (448-472) covers the new `authorised`/`status` fields. No vacuous assertions.  

**Q4: VERDICT**  
- LOW | run_fresh:212 | G17_onset_tail evidence written after `put` (minor race if exception) | move inside `put`  
- LOW | replay:18-23 | attestation exception path sets HOLD but does not call `write_report` again | cosmetic only  

READY