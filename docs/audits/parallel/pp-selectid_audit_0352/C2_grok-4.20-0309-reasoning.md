# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 36 s finish=stop usage in 8603 / out 1296 usd~0.075 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0352 (C2_STEP.diff)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
Cycle 1 (my own output) treated the `before is not None` guard and `ad_read_marker` contract as obviously safe because the function defaults `before_text=""` and the docstring explicitly says “no context” moments are left to the package stage. I therefore did not scrutinize the interaction when `before=None` *and* a marker sits inside `moment_text` itself. GLM-5.3-FLASH’s P1-1 (context sentinel divergence) and Qwen’s P2 note on “no context” deferral both flagged the exact contract surface I glossed over. The differential test added in C2 catches the normal case but not this edge. I also missed that the original `why_none` path could emit literal “None” (GLM P2-1); the C2 fix makes that obvious in retrospect.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
- GLM P1-1 / coverage note on context sentinel: **partially agree**. The risk was real before the differential test; the test now proves the *common* path matches `exclusion_for` exactly, but still omits the `before=None + marker-in-moment` subcase.  
- GLM P1-2 / why_none ordering and “angle N: None”: **agree**. The guard `if out["package"] is None and not out.get("why_none")` plus the new per-angle “no reason recorded” fallback eliminates it; the C2 diff implements exactly what GLM asked for.  
- GLM truncation concern: **agree** — resolved by `[:250]` *per angle*.  
- Grok’s “byte-identical, SHIP yes”: **disagree on completeness**. It understated the contract gaps outside the diff; the added differential test and why_none naming were necessary.  
- Qwen’s P2 observations (KeyError scope, duplication removal, test mocking): **agree**. All are now documented in the new docstring and covered by the explicit differential test that forces `exclusion_for` on the identical stubbed context.  
- Consensus K1–K5: **agree**. Every item listed as “IMPLEMENTED” or “DOCUMENTED” in the C2 diff is present and verifiable.

3. **NEW FINDINGS FROM THIS REVIEW**  
**P2-1 — pipeline/package.py:60 (ad_read_out)**: `why = M.ad_read_marker(m["text"], before) if before is not None else None`.  
`ad_read_marker` *always* examines `moment_text` first (its loop starts with `("the moment", moment_text or "")`), and `ad_read_marker(..., None)` correctly returns a reason when a marker is present in the moment. The guard therefore silently skips early refusal for the subcase “marker inside moment text + before=None”. The moment still reaches the package stage’s `exclusion_for` (which calls the same function and will exclude it), satisfying “fail closed” and “nothing new is accepted”. However it violates the stated goal “refuse exactly what the package stage refuses, *only earlier*”. The new test (`test_ad_read_out_reads_the_same_context…`) only exercises a marker-in-before case and a no-marker `None` case; it never asserts that a moment containing “sponsored” with `before=None` is still recorded in `ad_read`. Scenario verifiable from diff only: `ms` entry whose `context_around` returns `(None, None)` *and* whose `m["text"]` matches `AD_MARKERS`.  
(No P0 or P1; the final package cannot contain the prohibited moment.)

All other paths (KeyError, no_role, prescreen counts, angle-write exclusion, why_none construction, truncation at 250 chars per angle, log line, test assertions) match the spec in the diff.

4. **REVISED SCORES**  
| Subsystem          | Cycle 1 | Cycle 2 | Why changed |
|--------------------|---------|---------|-------------|
| ad_read_marker / exclusion_verdict | P2:1   | P2:0   | Extraction + removal of double regex call is clean; differential test proves deterministic part unchanged. |
| ad_read_out context handling | P1:1   | P2:1   | Missed `before=None + marker-in-moment` bypass of early filter (new P2-1). |
| why_none / diagnostic path | P2:2   | P2:0   | Per-angle “no reason recorded” + 250-char slice fully resolves GLM concerns. |
| Test coverage & law compliance | P2:1   | P2:1   | Differential test added (good); still misses the edge above. Overall risk lowered but not eliminated. |

5. **FINAL PRIORITY LIST**  
**P0 CRITICAL**: none verifiable from diff.  
**P1 HIGH**: none.  
**P2 MEDIUM**:  
- pipeline/package.py:60 — remove `if before is not None else None`; call `M.ad_read_marker(m["text"], before)` unconditionally (function already treats `None` correctly). Update docstring and add test case exercising marker-in-moment when context_around returns `(None, None)`.  
- tests/package/test_medley.py:149 — extend the differential block to also test a moment whose text contains an AD_MARKER while its mocked context is `(None, None)`.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
Make `ad_read_out` call `ad_read_marker` unconditionally so the early filter exactly matches the deterministic part that `exclusion_for` will later run, eliminating the last documented gap between “left to package stage” and “refuse earlier”.

7. **PRODUCTION READY?**  
**Yes with conditions**. The two P2 items above (unconditional call to `ad_read_marker` + one extra test case) must be addressed before merge; they are small, localized, and preserve every law (fail-closed, never accept new moments, why_none never hides a prior reason). After those changes the diff satisfies every requirement verifiable from the provided files.