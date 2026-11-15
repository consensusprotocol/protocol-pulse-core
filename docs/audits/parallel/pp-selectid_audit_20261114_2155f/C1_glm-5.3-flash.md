# glm-5.3-flash (z-ai/glm-5.3-flash) 46 s finish=stop usage in 5249 / out 1320 usd_reported=0.000326 usd~0.036 (upper-bound price)

# Audit: pp-selectid — RENDER_16X9_ONLY flip

## What the diff does
- `pipeline/visual_pin.py`: `RENDER_16X9_ONLY` `False → True`, comment rewritten to cite the integrator's landed release (c396c3c8, 21:55 ET Nov 14) and the accepted `formats` values (`["16x9"]` / `["16x9","9x16"]`).
- `tests/package/test_visual_pin.py`: the contract test is re-pinned so the *default* (unpatched) behaviour is now "eligible, 16:9-only", and the *held* behaviour is exercised only under `mock.patch.object(VP, "RENDER_16X9_ONLY", False)`.

## Findings

**[P2] The test's "both directions" claim is only half-true — the True path is now the default, so the flip itself is no longer exercised as a *transition*.** Before this diff, the test asserted the shipped default (False → held) and patched to True to prove eligibility. After the diff, the shipped default (True → eligible) is asserted directly and the patched direction (False → held) is the mocked one. Both behaviours are still asserted, so this is not a defect — but note the *unpatched* module constant is now only ever read at its new value; if someone later reverts the constant without touching the test, the test still passes because the assertions are inside/around the patch symmetrically. Actually, checking carefully: the held-assertions are inside the `False` patch and the eligible-assertions are outside it, so a revert of the constant alone *would* fail the outside assertions. That's correct. Downgrade: the test does pin the flip. No finding — withdrawn; kept here only to show the check.

**[P3] Comment says "Until then it was HELD here (layout_block, with this False)" — tense/wording.** "Until then" reads oddly next to a landed change; the comment describes past state in a file whose constant is now True. Nit only; the substantive content (who held, what changed, which commit) is right, and the diff keeps the provenance (c396c3c8, 21:55 ET) which is what the audit package demands.

**[P3] `assertNotIn("ticker", VP.layout_block(blockware))` moved inside the patched-False block but its truth doesn't depend on the flag.** `layout_block` returns the hold message only for 16:9-only clips; the "ticker" exclusion presumably holds in both modes. Harmless, but it slightly weakens the patched-False block's reason to exist (only the "16:9-only" assertion needs the patch). Cosmetic.

**[P3] `VP.formats(blockware)` is asserted twice (line 24 and line 36) with the same expectation `["16x9"]`.** Redundant but harmless; the second occurrence does document that eligibility (not just the hold's absence) carries the 16:9-only formats, which is the point of the flip.

## Answers to the stated questions

**(1) Can any 16:9-only clip now reach a pin WITHOUT "formats" sealed?** No, on the evidence in this diff. The chain is: `layout_block` returns `None` for the 16:9-only clip (no hold) → `package_pin.formats_of` seals `moments_package["formats"] = ["16x9"]` (landed 1e4fb5a9, audited 20261114_2131, outside this diff) → `package_pin.seal` adds `formats` to the body *only when present* → `pin_seal` passes it → the integrator's `check_pin_only` recomputes through `pin_seal`. The one residual risk is the "only when present" clause: if `formats_of` ever returns `None`/absent for a 16:9-only clip (e.g. a source whose caption flags yield neither `IN_9X16` nor a burned kind), `seal` would silently omit `formats` and the integrator's `read moments_package["formats"]` — which the spec says must be *exactly* `["16x9"]` or `["16x9","9x16"]` — would see a missing key. That path is guarded by the integrator's landed code, not by this diff, and the diff's test does not cover a clip that is neither `whole` nor burned-caption. Within the diff's scope: no.

**(2) Does the test pin the flip?** Yes. The held behaviour is asserted under an explicit `RENDER_16X9_ONLY=False` patch, the eligible/16:9-only behaviour is asserted at the module's shipped default (True), and `formats(blockware) == ["16x9"]` is re-asserted post-eligibility. A revert of the constant without a test edit fails the unpatched assertions; a change of the eligibility logic without a constant change fails the patched-False assertions. Both directions are pinned.

## Law compliance
- **LAW 20 / M2 (thresholds/constants, no reclassification):** the flip changes behaviour, not what a check accepts — the 16:9-only clip was *held* (a HOLD, not a FAIL) and is now *eligible*; the gates themselves are untouched. Complies.
- **M12 FAIL CLOSED:** the hold path is retained (patched-False branch proves it), so the fail-closed direction still exists in code, not just in history. Complies.
- **Smallest diff / M1:** two files, one constant + its comment + the corresponding test re-pin. No new renderer/compositor/selector. Complies.
- **L-j (release authorised on these bytes):** the diff does not touch `release_auth`; the integrator's c396c3c8 is cited as landed and audited (20261114_2131) separately. Nothing in this diff weakens the REQUIRED-row inventory. Complies.

P1_OR_WORSE: 0