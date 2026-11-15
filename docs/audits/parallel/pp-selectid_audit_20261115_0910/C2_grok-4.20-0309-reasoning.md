# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 37 s finish=stop usage in 7598 / out 1053 usd_reported=0.022893 usd~0.064 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261115_0910**

1. WHAT DID THEY CATCH THAT YOU MISSED?
In Cycle 1 I correctly identified the subset argument, absence of paid calls before the gate, candidate exclusion, and that the synthetic prescreen satisfied the known readers. I missed GLM's point about the log-line `n_usable` vs `len(ms)` discrepancy (and that the base :2573 log already does the same split between "usable" and later no-role trimming). I also missed that the diff context left `trims`/`trim_out`/`admitted`/`no_role`/`current_levels` undefined in the visible hunk, forcing reliance on the placement comment and test coverage. Finally, I did not call for an explicit integration test of `proof_ledger.open_work` and `candidates.seed` on the synthetic record; that test (now present) is the highest-value addition from Cycle 1 feedback.

2. WHERE DO YOU AGREE OR DISAGREE?
- GLM [P2] record-shape divergence across failure modes: partially agree. The original test was narrow, but the new `test_the_guard_finds_no_open_work_and_the_registry_no_line_up` plus the consensus clarification that :2587 returns a single dict literal (no conditional keys added between gate and return) resolves it. The shape test now runs the real downstream functions; I agree the risk is eliminated.
- GLM [P2] `n_usable` vs `len(ms)` log line: agree with consensus that it is intentional and matches base semantics (usable includes moments later removed by no-role). Downgrade to P3.
- GLM [P3] variables referenced but not in diff context: agree — the comment now suffices and mutation coverage confirms placement.
- GLM [P3] synthetic `held_102` and missing `visual`: agree; the new guard test proves tolerance.
- Qwen analysis of subset argument, paid-call ordering, candidate exclusion, and test comprehensiveness: fully agree. No P0/P1.
- Both on pre-existing `proof_ledger.py:484` KeyError for candidate builds: agree it must not be fixed here (law K2, no candidate due today, change adds no new exposure). Tracked in handoff.
- Consensus that shape is not mode-dependent: agree after re-reading the base return literal.

3. NEW FINDINGS FROM THIS REVIEW
[P3] `why` variable in early-return dict (pipeline/package.py:19) is not declared in the diff hunk. It is accumulated during free-stage unusable collection before the gate; tests never assert its value on the early path. Harmless because readers use `"usable"` and `"why_none"`, but a comment tying the variable to the pre-gate `why` list would prevent future drift.  
[P3] Test method `test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns` imports `candidates` and `proof_ledger` inside the method. Works but pollutes test style; move to module level.  
[P3] `why_none` wording differs between gate ("after the free stages… no paid verdict (ruling 109)") and :2587 ("X moments cleared step A from fewer than 3 channels"). Accurate for each path and logged only on its own path, but could confuse log aggregation. No functional impact.

4. REVISED SCORES
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| Record shape & readers     | P2      | P3      | New guard test + confirmation that :2587 dict is static |
| Log-line / usable vs pool  | P2      | P3      | Consensus confirms matches base intent |
| Paid-call ordering & gate placement | P1 | P1 | No change — still correct but remains highest-visibility item |
| Candidate exclusion & pre-existing defect | P3 | P3 | No change; K2 still applies |
| Test coverage & mutation kill | P2 | P2 | Added test is excellent but style nits remain |

5. FINAL PRIORITY LIST
P0 CRITICAL: none  
P1 HIGH: none  
P2 MEDIUM: none  
[P3] pipeline/package.py:19 — add comment tying `"unusable": why` to pre-gate accumulation (see finding 3).  
[P3] tests/package/test_medley.py:78 and :79 — move imports to top of file.  
[P3] pipeline/package.py:16 and tests/package/test_medley.py:72 — consider harmonizing `why_none` wording if log comparison ever becomes important (non-blocking).

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The new `test_the_guard_finds_no_open_work_and_the_registry_no_line_up` that runs the actual `open_work` and `CA.seed` functions on the synthetic record; everything else is now proven tolerant.

7. PRODUCTION READY?
Yes with conditions: apply the three P3 comment/import/wording cleanups above (trivial) and land.

P1_OR_WORSE: 0