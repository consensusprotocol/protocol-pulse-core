# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 19 s finish=stop usage in 5724 / out 1008 usd~0.054 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-1845 (Ruling 73 switch)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
In Cycle 1 I focused on the constant swap, docstring, and new test but overlooked the precise phrasing added to the module docstring (lines 10-11) that explicitly declares “or in a file named for another decoder, is not valid … and is never read.” I also missed that the old-rules test inserts its entry *after* the adopted entry but still asserts “no_difference,” proving the rules filter is applied on every read, not only at first insertion. GLM’s P2-2 on the un-shown glob/read side and Qwen’s explicit mapping to M12 FAIL-CLOSED were sharper than my original notes.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM: Fully agree on verification of “old rules never read” via the future-timestamp test and on the P2 that production `cut` consumption lives outside this diff. Partially agree on P2-1 (docstring documents fields the diff does not implement); the new test’s use of a `cut` dict that still yields verdict=pass is sufficient evidence the consumer tolerates the extra key.  
- Grok: Agree on every point; its “implements exactly the checked requirements” summary is correct.  
- Qwen: Agree on the architecture split (this diff only reads; integrator produces) and on LAW 20 / M2 compliance. Disagree slightly on calling the old-rules test “test_a_request_is_renamed…” — the diff renames that method’s assertion but the new test is the dedicated ruling-73 case.  
- Claude consensus: Agree that all three prior reviewers found zero P0/P1 and that the filtering is the existing, tested mechanism.

3. **NEW FINDINGS FROM THIS REVIEW**  
Combined analysis reveals one unmentioned detail: the ruling-73 test deliberately mixes a hold (segment 0) with a cut-carrying pass (segment 1) and asserts the *overall* `rep["ok"] == False` while preserving per-segment verdicts. This simultaneously proves both “a ruling-73 hold can never pass” *and* that later segments are still evaluated (no short-circuit). No one in Cycle 1 called out that the docstring now documents ruling-68 legacy entries (“Entries without ‘rules’ … are never read”) which the code has honored since the prior switch; the comment is updated but the constant change does not alter that path. All 15 suites still pass.

4. **REVISED SCORES**  
| Subsystem                  | Cycle 1 | Cycle 2 | Why changed |
|----------------------------|---------|---------|-------------|
| Old-rules / old-decoder exclusion | P2     | P2     | No change; still rests on un-shown read path, but three other reviewers + green suites raise confidence |
| Ruling-73 hold semantics   | P2     | P2     | No change; test coverage is strong but render-side consumption of “cut”/“why” remains out of diff |
| Docstring / comment hygiene| P2     | P1     | Elevated because the expanded docstring is now the only place that declares the new decoder SHA and the exact failure reason string; any mismatch here would mislead future audits |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL** — none.  
**P1 HIGH** — none.  
**P2 MEDIUM** —  
- P2 (docs/audits/parallel/pp-selectid_audit_1845/C2_STEP.diff:23): comment claims full SHA but only first 12 chars are stored in DECODER; harmless but should say “decoder_sha[:12]” for consistency with docstring line 7.  
- P2 (pipeline/lock_precheck.py:24): the inline comment listing the exact hold reason string is duplicated in the new test; single source of truth would be preferable but not required.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
The single highest-leverage change is the test that inserts an old-rules entry with a *newer* timestamp (2026-11-14T01:00:00Z) yet still receives “no_difference,” proving the rules filter is applied on every read before recency.

7. **PRODUCTION READY?**  
Yes with conditions: (a) the integrator’s service must be running the merged 585b6da5 decoder that actually emits the new “cut” dict or the exact “ruling 73: the render cannot cut this span: …” reason string, and (b) a repo-wide grep for the old decoder SHA “25cd6f15e6c9” must return only this diff and its test expectations. With those two confirmations the change is safe to ship.