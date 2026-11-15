# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2155f
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
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
- **L-j (release authorised on these bytes):** the diff does not touch `release_auth`; the integrator's

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 18 s finish=stop usage in 5364 / out 707 usd_reported=0.013416 usd~0.044 (upper-bound price)

**CODE AUDIT: pp-selectid-20261114_2155f (C1_STEP.diff)**

**Summary**  
The diff performs the final gated flip of `visual_pin.RENDER_16X9_ONLY` from `False` to `True`, updates the explanatory comment to reference the previously landed integrator release (c396c3c8 / 1e4fb5a9), and inverts the unit test so that the new default behavior (eligible 16:9-only clip, formats=["16x9"]) is exercised without a patch while the legacy HOLD path is explicitly re-tested via patch. No functional logic, renderer, selector, or compositor was altered—only the gate constant and its test.

**Findings**

[P3] Comment length and history density in `visual_pin.py:13-15` is higher than strictly necessary for runtime code even though it accurately cites the governing commit, orchestrator timestamp, and downstream consumers (run_fresh, release_auth, review drop). This is acceptable under "smallest diff" (M1) but should be considered for extraction into the audit package or governing-laws appendix in future steps.  

[P2] The test `TestContract.test_blockware` now correctly asserts both the patched (HOLD) and default (eligible + formats=["16x9"]) paths. However it does not directly invoke `package_pin.seal`, `pin_seal`, or the integrator's `check_pin_only` recomputation on the sealed dict. While the diff description asserts these were audited in the prior 20261114_2131 package, a cross-boundary assertion would strengthen L-j (exact bytes seen by release_auth) and L-d (protected preview layout reproduction).  

[P3] No regression risk to LAW 22 (v2f byte-identical re-render) or L-d (protected 2026-11-11 preview) because the 16:9-only path was already explicitly HELD under the old default; the protected fixtures use non-16:9-only blockware or whole-frame crops that route around this constant.  

[P1] The diff does not update or add any coverage for L-e / L-h / L-k (punctuation-before-read, canon.py routing, transcript_store.acquire(prefer_words)) or for the new D5 vertical-letterbox gate that motivated the change. While this specific constant flip is orthogonal, the overall feature package claims "fixes the causes" of the 2026-11-10 must-fail suite. Absence of a linked test exercising a 16:9-only burned-caption clip through the full sentence_law + release_auth path on the must-fail fixture set constitutes an incomplete quality gate for the stated purpose of the branch.  

[P3] The constant flip itself satisfies SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, LAW 20/M2, M12, and FAIL-CLOSED. No gate was reclassified, no model reply was loosened, no selection lock was recomputed downstream, and `formats` is only emitted when present (per the unchanged guard in package_pin.seal).  

**Conclusion**  
The mechanical change is correct and minimal. The primary defect is the missing end-to-end regression link for the D5 vertical fix and the 16:9-only sealed path through release_auth/ATTESTATION.json.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 44 s finish=stop usage in 5673 / out 3659 usd_reported=0.002873 usd~0.072 (upper-bound price)

I will review the provided diff and context against the governing laws and the specific questions asked.

### Analysis

**1. Context and Change Verification**
The change flips `RENDER_16X9_ONLY` from `False` to `True` in `pipeline/visual_pin.py`.
*   **Previous State:** When `False`, `layout_block` returned a string indicating the clip was held ("16:9-only") because the integrator could not handle it.
*   **New State:** When `True`, `layout_block` returns `None` (eligible), and the pin is sealed with `formats: ["16x9"]`.
*   **Justification:** The comment states the integrator's format-aware release has landed (commit `c396c3c8`), allowing `run_fresh` and `release_auth` to read `moments_package["formats"]`.

**2. Review of Question (1): Can any 16:9-only clip now reach a pin WITHOUT "formats" sealed?**
*   The diff shows the constant flip. It does *not* show the implementation of `layout_block` or `package_pin.formats_of`.
*   However, the text description states: "package_pin.formats_of seals moments_package["formats"] = ["16x9"] for it (landed 1e4fb5a9, audited 20261114_2131)."
*   The test `test_visual_pin.py` asserts: `self.assertEqual(VP.formats(blockware), ["16x9"])`.
*   **Risk:** If `formats_of` relies on the `RENDER_16X9_ONLY` flag to decide *whether* to add the key, and the logic is inverted or missing, the key might be absent. But the test explicitly checks for the presence of the key `["16x9"]` when the flag is `True` (default).
*   **Law Check (L-j):** "release_auth.py ... exact gate inventory ... REQUIRED rows exactly 'PASS' ... on exactly the bytes that are sent." If the pin lacks the `formats` key, `release_auth` (which reads `moments_package["formats"]`) would likely fail or raise an exception (Fail Closed, M12).
*   **Conclusion:** Based on the provided test and description, the mechanism is in place. The test verifies the output. There is no evidence in this diff that the key is missing. The flip enables the *sealing* of the key.

**3. Review of Question (2): Does the test pin the flip?**
*   The test `TestContract` in `tests/package/test_visual_pin.py` is modified.
*   **Old Test:**
    *   Asserted `layout_block` contained "16:9-only" (held).
    *   Used `mock.patch.object(VP, "RENDER_16X9_ONLY", True)` to assert `layout_block` was `None` and `formats` was `["16x9"]`.
*   **New Test:**
    *   Uses `mock.patch.object(VP, "RENDER_16X9_ONLY", False)` to assert `layout_block` contains "16:9-only" (held). This verifies the *old* behavior is still accessible via the flag (regression check for the flag's function).
    *   **Without mock** (default `True`): Asserts `layout_block` is `None` and `formats` is `["16x9"]`.
*   **Conclusion:** Yes, the test pins the flip. It verifies that the default state (True) results in eligibility and correct formatting, and that the state (False) results in holding. This is a robust test for the constant change.

**4. Law Compliance Check**
*   **LAW 20 / M2:** "never change what a check accepts to make a render pass".
    *   This change *expands* what is accepted (16:9-only clips are no longer held). Is this a violation?
    *   The context says: "RULING 93 AMENDED ... a clip ... is 16:9-ONLY, sealed as formats ["16x9"], and not ineligible."
    *   The amendment explicitly changes the rule. The code change implements the amended ruling. It does not bypass a gate; it updates the gate's criteria based on a new orchestrator ruling. This is compliant with the *amended* law.
*   **L-j (Release Authorised on Bytes):** The `release_auth` now reads `formats`. The pin must contain it. The test ensures it does.
*   **M12 (Fail Closed):** If the integrator *hadn't* landed, this flip would cause `release_auth` to fail (missing key or unexpected value), which is fail-closed. Since the integrator *has* landed, it passes.

**5. Potential Issues**
*   **Dependency on External Commit:** The change relies on `c396c3c8` (integrator) and `1e4fb5a9` (formats sealing). If those commits are not present in the branch `pp-selectid` or if there is a merge conflict, this code will break. However, the audit package implies these are "landed".
*   **Test Coverage:** The test only checks `blockware` (a specific fixture). Does it check a clip that is *not* 16:9-only?
    *   Line 37-39: `whole = rec(...); self.assertIsNone(VP.formats(whole)); self.assertIsNone(VP.layout_block(whole))`.
    *   This checks that a "whole" clip (presumably eligible for both formats) still works. `formats` is `None`? Wait.
    *   If `formats` is `None` for a "whole" clip, does `release_auth` handle `None`?
    *   The description says: "run_fresh ... read moments_package["formats"], exactly ["16x9"] or ["16x9", "9x16"]".
    *   If a "whole" clip has `formats: None`, `release_auth` might reject it because `None` is not `["16x9"]` or `["16x9", "9x16"]`.
    *   Let's look at the t

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit 20261114_2155f (the flip of RENDER_16X9_ONLY)

The reviewers disagreed (qwen P1_OR_WORSE 1, glm 0), so Grok was asked as the third (1). Cost: $0.0166 vendor-reported.

BOTH P1s ARE REFUTED, with evidence:
- qwen P1, "a pin WITHOUT formats may be rejected". The integrator's landed code (main c396c3c8,
  pipeline/release_auth.py package_formats) returns None, meaning both formats, when "formats" is absent. It raises
  only for a present value other than ['16x9'] or ['16x9', '9x16']: "None when absent (both) ... (absent = both)".
  So every dual-format pin, absent the key, renders both as before. This side seals the key only for a 16:9-only clip.
- Grok P1, "no end-to-end test through release_auth". The release side is the integrator's own landed change, which
  covers release_auth, run_fresh's verdict, the drops and check_pin_only: audits batch 85, two cycles, no defect,
  both regressions green. This side's half is pinned by test_formats (the seal covers formats; stripping it breaks
  the seal) and by test_visual_pin (the flip, both directions).
glm: no P0/P1, and it confirms the flip is the minimal change.

Nothing to implement. The test already pins both directions.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2155f/C2_STEP.diff (40 lines)
```
   1 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
   2 | index 844a320..a3d31e6 100644
   3 | --- a/pipeline/visual_pin.py
   4 | +++ b/pipeline/visual_pin.py
   5 | @@ -45,10 +45,9 @@ TILES, EVERY_S, TILE_W, COLS = 40, 1.0, 320, 6   # 21:10 Nov 14: "at least one f
   6 |  HOW = ("still", "photo", "graphic", "none")
   7 |  BURNED = ("ticker", "crawl", "lower_third", "bug", "caption")   # ruling 93: question 4's kinds; "caption" (ruling 93
   8 |  CAPTION = "caption"                                    # amended): the source's own burned subtitles of the words
   9 | -RENDER_16X9_ONLY = False      # the integrator's render cannot yet pass a 16:9-only pin (its message 21:2x Nov 14: its
  10 | -#   release_auth needs the 9:16 rows; it builds the format-aware path, audited): until it says so, a clip that is
  11 | -#   16:9-only is HELD here (layout_block), and no 16:9-only pin is sealed. Flipped on its word, with the package-level
  12 | -#   "formats" (package_pin), in one audited change.
  13 | +RENDER_16X9_ONLY = True       # the integrator's format-aware release LANDED (c396c3c8, its message 21:55 ET Nov 14: run_fresh,
  14 | +#   release_auth and the review drop read moments_package["formats"], exactly ["16x9"] or ["16x9", "9x16"]): a 16:9-only
  15 | +#   clip is eligible and sealed with formats ["16x9"]. Until then it was HELD here (layout_block, with this False).
  16 |  RUNNING = ("ticker", "crawl")                          # ruling 93: "a ticker or crawl = not eligible"
  17 |  IN_9X16 = ("whole", "out", "cut")
  18 |  FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
  19 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
  20 | index 326fb65..708919f 100644
  21 | --- a/tests/package/test_visual_pin.py
  22 | +++ b/tests/package/test_visual_pin.py
  23 | @@ -113,11 +113,11 @@ class TestContract(unittest.TestCase):
  24 |          self.assertEqual(VP.formats(blockware), ["16x9"])
  25 |          self.assertEqual([f["kind"] for f in VP.flags(blockware)], ["burned_caption", "burned_caption"])
  26 |          self.assertEqual(VP.flags(blockware)[1]["at"], [16.35, 19.62])
  27 | -        self.assertIn("16:9-only", VP.layout_block(blockware))               # held while the render cannot pass it
  28 | -        self.assertNotIn("ticker", VP.layout_block(blockware))
  29 | -        with mock.patch.object(VP, "RENDER_16X9_ONLY", True):
  30 | -            self.assertIsNone(VP.layout_block(blockware))                    # then eligible, 16:9 only
  31 | -            self.assertEqual(VP.formats(blockware), ["16x9"])
  32 | +        with mock.patch.object(VP, "RENDER_16X9_ONLY", False):
  33 | +            self.assertIn("16:9-only", VP.layout_block(blockware))           # held while the render cannot pass it
  34 | +            self.assertNotIn("ticker", VP.layout_block(blockware))
  35 | +        self.assertIsNone(VP.layout_block(blockware))                        # the integrator's release landed
  36 | +        self.assertEqual(VP.formats(blockware), ["16x9"])                    # (c396c3c8): eligible, 16:9 only
  37 |          whole = rec(cap("FINANCIALLY INDEPENDENT BY 45", "whole"))
  38 |          self.assertIsNone(VP.formats(whole))                                 # a crop shows it whole: both formats
  39 |          self.assertIsNone(VP.layout_block(whole))
  40 | 
```

---

pp-selectid: the FLIP of visual_pin.RENDER_16X9_ONLY to True. The integrator's format-aware release has landed
(c396c3c8, its message at 21:55 ET Nov 14): run_fresh, release_auth and the review drop read moments_package["formats"],
exactly ["16x9"] or ["16x9", "9x16"]; anything else is a rejected pin. RULING 93 AMENDED (orchestrator 21:10): a clip
whose source caption the 9:16 crop cuts is 16:9-ONLY, sealed as formats ["16x9"], and not ineligible.

THE CHANGE: RENDER_16X9_ONLY False -> True, with its comment. layout_block no longer holds a 16:9-only clip;
package_pin.formats_of seals moments_package["formats"] = ["16x9"] for it (landed 1e4fb5a9, audited 20261114_2131).
The test pins both directions: patched to False, the clip is held; by default it is eligible and 16:9-only.
UNCHANGED GUARDS: package_pin.seal adds "formats" to the body only when present; pin_seal passes it; the
integrator's check_pin_only recomputes through pin_seal.
PLEASE CHECK: (1) Can any 16:9-only clip now reach a pin WITHOUT "formats" sealed? (2) Does the test pin the flip?


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
