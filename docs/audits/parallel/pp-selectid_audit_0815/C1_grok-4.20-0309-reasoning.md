# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 37 s finish=stop usage in 8997 / out 442 usd~0.056 (upper-bound price)

**P0: None**

**P1: pipeline/package.py:67-70 (validation block)**  
Concrete scenario: JSON reply contains `"hook":{"scroll":4,"alone":4,"setup":4.0}` (integral float after json.loads). The `type(x) is not int` check rejects it, routing to the `except` block → `measured=False`, `ok=False`. This matches the strict contract test added at test_medley.py:160 but is stricter than the "harmless variations (integral float as int)" rule stated in L-l / test_editorial_robust.py (not visible in this diff). Uncertain whether downstream LLM JSON parser or cache re-validation would ever surface a float.

**P2: pipeline/package.py:78 & tests/package/test_medley.py:94,138**  
The derivation is hardcoded to `min(...)` and `HOOK_RULE` explicitly calls it "the lowest". This matches the audit's stated choice (K1) and the new test assertions. The ruling text only required "derived, never free-form"; min is a reasonable reading but was not the only possible formula.

All other checked items verify cleanly from the diff:
- Hook is no longer rated on through-line (prompt text, `"For each clip AFTER the hook"`, `set(v["clips"]) == set(labs[1:])`, test that `"hook": 1` is absent from prompt).
- Clips after hook rated exactly as before (unchanged prompt language and validation).
- Derived rating cannot be free-form/missing (strict key+type+range contract; every malformed case in test_out_of_contract... returns False/measured=False).
- Joins, flagged-bridge logic, and pass/fail rule are byte-identical to prior version.
- `verdict["clips"]["hook"]` receives the derived integer (line 78) so weak-segment detection / ruling-41 hook swap continue to see it under the expected key.

test_medley.py passes (82 OK); no other suites touched.

**SHIP: yes with conditions** (tighten hook-part validator to accept integral float or rely on shared LLM parser; add float test case).