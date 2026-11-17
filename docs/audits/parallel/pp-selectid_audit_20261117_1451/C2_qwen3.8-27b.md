# qwen3.8-27b (qwen/qwen3.8-27b) 202 s finish=stop usage in 11229 / out 7861 usd_reported=0.007519 usd~0.152 (upper-bound price)



# CYCLE 2 — FINAL REVIEW (pp-selectid-20261117_1451, Ruling 142 mirror)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Nothing material. In Cycle 1 I reached the same conclusion (P1_OR_WORSE: 0) and the same reasoning. The other models' P2/P3 findings are discussed below; none represent a defect I overlooked.

## 2. WHERE DO I AGREE OR DISAGREE?

**GPT-OSS-20B, P2 #1 — "_FORM_END may over-strip (class/glass)":**
**Disagree.** The example is flawed. `word_form(["class"], ["glass"])` → diff = `[("class","glass")]` → strip → `"clas"` vs `"glas"` → not equal → `False`. The regex only strips a *trailing* `s`/`'s`/`s'`/`'`; it does not turn "class" into "class" minus an internal `s`. The only real false-positive vectors are pairs like `["so"]`/`["so's"]` or `["not"]`/`["nots"]`, which are (a) practically unreachable in ASR output and (b) still gated by the two-of-three vote. Not a P2.

**GPT-OSS-20B, P2 #2 — "suppresses critical-token handling for other tokens in the slice":**
**Disagree.** `word_form` returns `True` only when `len(diff) == 1` — exactly one token differs. If a second token in the slice were also critical *and* different, `len(diff)` would be ≥ 2 and `word_form` would return `False`, restoring the hold. The critical tokens that are *identical* on both sides (e.g., a "5" present in both `r[a:b]` and `p[c:d]`) are not in dispute; the ruling exempts the *difference*, not the presence of a number. The guard is correctly scoped.

**Qwen, P3 #1 — "_NUM_HYPHEN doesn't cover '24 - 7' (space after hyphen)":**
**Agree it's a gap, but by design.** The ruling names only the `digit space hyphen digit` spacing. `digit space hyphen space digit` is the existing range pattern (`'70 - 75'`), and `_SIGN_SPACED`'s lookbehind `[^\d\s.,%]` correctly rejects a preceding digit. canon.py is byte-identical to the integrator's file; widening is their call.

**Qwen, P3 #2/#3 — "no lexicon guard" / "bare `'` wider than possessive/plural":**
**Agree as observations, not defects.** The `bool(a)` guard prevents a bare-`'` token from matching. The two-of-three vote is the actual decision point; `word_form` only removes the L-v 2 *pre-hold*. No law is violated.

**Gemma — "precise mirror, no violations":**
**Agree.**

**Consensus — all P3s declined, no change:**
**Agree.**

## 3. NEW FINDINGS FROM THIS REVIEW

I re-traced every code path and test case independently. No new defects.

One clarification worth recording for the audit trail: in `TestRuling142.test_two_of_three_decides_a_word_form_pair_of_a_name`, the three readings are drawn from `run_decode` (RUN = "Bitcoin"), `approved` (APP = "Bitcoin's"), and `second_recogniser` (varies) — *not* from the `spoken` parameter, which only sets the segment text. The "hold" case (line 172) correctly has all three readings distinct: "Bitcoin" / "Bitcoin's" / "Bitcoins". This is correct and the test name could be slightly misleading, but the logic is sound. [P3] Cosmetic test-naming nit; no action needed.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| canon.py (`_NUM_HYPHEN`, `word_form`) | Clean | Clean | Re-verified all regex interactions and edge cases; no change |
| attest.class_131 (mirror hunk) | Clean | Clean | Confirmed `word_form`'s `len(diff)==1` invariant makes GPT-OSS-20B's P2 #2 inapplicable |
| lock_precheck.py (RULES, DECODER) | Clean | Clean | SHA and string match integrator's batch 110 |
| Tests (TestRuling142, pins) | Clean | Clean | All 4 new tests + 2 pin updates verified; 6/6 mutations killed |

No score changes.

## 5. FINAL PRIORITY LIST

No P0, P1, or P2 findings.

| # | Severity | Finding |
|---|---|---|
| 1 | [P3] | `_NUM_HYPHEN` does not cover `digit space hyphen space digit` ("24 - 7"). By design; outside ruling scope; integrator's file. |
| 2 | [P3] | `_FORM_END` has no lexicon guard; structurally matches non-words like "nots". Practically unreachable; two-of-three vote still governs. |
| 3 | [P3] | Bare `'` alternative in `_FORM_END` is wider than "possessive or plural." Handles a fold artefact; `bool(a)` guard prevents empty matches. |
| 4 | [P3] | Test method name `test_two_of_three_decides_a_word_form_pair_of_a_name` could be read as using the `spoken` param for the three readings, but it actually uses `run_decode`/`approved`/`second_recogniser`. Cosmetic. |

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Nothing. The code is a byte-faithful mirror of the integrator's audited branch, the ruling's two sub-requirements are correctly and minimally implemented, the decoder lockstep is in place, and the test suite (including mutation testing) confirms the behavior. The highest-leverage action is to **ship it as-is**.

## 7. PRODUCTION READY?

**Yes.** No conditions. The diff is a precise mirror of the integrator's batch 110 (canon.py byte-identical, attest hunk logically equivalent, RULES/DECODER lockstep). All four review questions are answered affirmatively. The test suite passes (903 tests, exit 0) and all 6 mutations are killed. No governing law is violated.

P1_OR_WORSE: 0