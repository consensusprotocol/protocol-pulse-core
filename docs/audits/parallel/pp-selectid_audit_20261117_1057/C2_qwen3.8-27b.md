# qwen3.8-27b (qwen/qwen3.8-27b) 166 s finish=stop usage in 11584 / out 13337 usd_reported=0.010048 usd~0.235 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## Feature: pp-selectid-20261117_1057 · RULING 135 · Comparison Canon

---

## 1. WHAT THE OTHER MODELS CAUGHT THAT I MISSED

Qwen's four P3 findings are all valid and I confirm them. In my Cycle 1 pass I focused on the four requested checks and the mutation results, and I did not flag:

- The tautological `else` branch in `test_a_spelling_pair_never_reaches_the_vote_in_class_131` (line 286–287). I traced the logic and confirmed the *meaningful* assertions are the `all(x["took"] == "spelling")` line and the final `verdict == "pass"` check, but I should have called out the circular first assertion explicitly.
- The `d.get("differences") or []` vacuous-pass pattern (line 266). I noted it mentally but did not write it down.
- The `REDUCTIONS["cause"]` sense ambiguity. I accepted the docstring's justification ("two readings of one audio never trade the noun 'cause' for 'because'") without flagging it as a noted limitation.
- The bare `#   RULING 131` comment heading in `lock_precheck.py` (line 136). Cosmetic; I missed it.

None of these change the safety assessment. I owe the correction.

## 2. AGREEMENT / DISAGREEMENT WITH CYCLE 1 FINDINGS

| Qwen finding | My position | Reasoning |
|---|---|---|
| [P3] `REDUCTIONS["cause"]` sense-ambiguous | **Agree** | The closed list is by design; the docstring justifies it for the domain. No action unless a future ruling adds disambiguation. |
| [P3] Tautological `else` branch in spelling-pair test | **Agree** | The `else` reconstructs expected from actual. The next two assertions (`all took == "spelling"`, `verdict == "pass"`) are the real checks. Simplify to a concrete list to remove the appearance of circularity. |
| [P3] `d.get("differences") or []` vacuous pass | **Agree** | `all()` over `[]` is `True`. In practice `decide` always populates the key, but a `self.assertIn("differences", d)` guard would make the test fail-closed. |
| [P3] Comment layout in `lock_precheck.py` | **Agree** | Cosmetic. The `#   RULING 131` line reads as a heading but is just a comment. No functional impact. |

I have no disagreements with Qwen. The other two seats (gemma, mimo) produced no output, so there is nothing to cross-check against.

## 3. NEW FINDINGS FROM THIS REVIEW

### [P3] `same_words` letter-concatenation path: "a man" ≡ "aman"

Line 108: `"".join(a).replace("-", "") == "".join(b).replace("-", "")`.

If one side tokenises as `["a", "man"]` and the other as `["aman"]`, the concatenation yields `"aman" == "aman"` → `True`. The ruling explicitly says "SEGMENTATION ignored … names too," so this is by design. In a Bitcoin/crypto transcript a standalone token `"aman"` is vanishingly unlikely, and the closed-list philosophy means no new segmentation rules are added without a ruling. Noted for completeness; no action required.

### [P3] `stray` parameter accepts a string; `"x" in "xy"` would enable both sides

The signature is `stray=()` (tuple default), but callers pass the string `"x"`. The membership test `"x" in stray` works for both strings and tuples. If a future caller passes `stray="xy"`, both sides get stray filtering. Mutation M28 ("stray on both sides") is killed, so the test suite catches this. The docstring says "a side named in `stray`" (singular), so the API contract is clear. No action; the mutation coverage is sufficient.

### [P3] `test_spelling_is_no_difference_in_ruling_72s_layer` asserts ALL differences are spelling-only

Line 266: `all(x["class"] == "spelling only (ruling 135)" for x in d.get("differences") or [])`.

If the spoken text introduces a filler *and* a spelling difference, the filler would get class `"filler"` (from ruling 84's existing filler step, which runs before `same_words`), and this assertion would fail. The three test inputs are carefully chosen so that every difference is spelling-only. This is correct for the test's purpose, but the assertion is stricter than necessary — a `<= {"filler", "spelling only (ruling 135)"}` set-containment check (as used in the TestRuling131 fixture at line 218–219) would be more robust if the inputs are ever extended. P3.

### [P3] `TestRuling131` fixture: `SPOKEN = MERGED` removes the ruling-72 overlay

The old fixture had `SPOKEN = MERGED.replace("2023 bull", "2023, uh, bull")` to test ruling 72's filler layer on top of the merged text. The new fixture sets `SPOKEN = MERGED` and introduces `HEARD` for the second-recogniser text. The ruling-72 filler path is still exercised (the `HEARD` text contains `"Um"` and `"uh"`), but the specific "ruling 72 on top of merged" scenario is no longer tested in isolation. The mutation suite (M1–M28) covers the filler logic, so this is acceptable. P3.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `canon.same_words` logic | 9/10 | 9/10 | No change. The stray parameter, digit guard, and letter-concatenation path are all correct. The "a man" / "aman" edge is by design. |
| `attest.class_131` integration | 9/10 | 9/10 | No change. Drop placement (after currency, before critical/vote) is correct. `mine` filter excludes both currency and spelling. |
| `attest.class_84` integration | 9/10 | 9/10 | No change. `stray="x"` correctly targets the spoken/second-recogniser side. Filler step runs first (unchanged). |
| `lock_precheck.RULES` | 9/10 | 9/10 | No change. String updated, test matches. |
| Test suite | 8/10 | 8/10 | Tautological assertion and vacuous `or []` pattern remain. 28/28 mutations killed is strong. The `SPOKEN = MERGED` change slightly narrows the ruling-72 overlay test. |
| Documentation / comments | 8/10 | 8/10 | Bare `# RULING 131` heading, `cause` ambiguity note. Minor. |

No score changed between cycles. The other models' findings were all P3 and did not alter my assessment of correctness.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL: none.**
I traced every "still holds" case through `same_words` and confirmed the digit guard, negation check, content-word check, and letter-name check all return `False`. No gate passes what it must refuse.

**P1 HIGH: none.**
The drop placement in both `class_131` and `class_84` matches the render's lock exactly. The `mine` filter correctly excludes spelling pairs from the record comparison. The sealed text preserves approved words for all spelling pairs. The 28/28 mutation kill rate confirms the test suite catches every single-point failure.

**P2 MEDIUM: none.**

**P3 NITS (all from Qwen, confirmed):**

1. [P3] `tests/package/test_lock_precheck.py` line 286–287: tautological `else` branch in `test_a_spelling_pair_never_reaches_the_vote_in_class_131`. Replace with a concrete expected list.
2. [P3] `tests/package/test_lock_precheck.py` line 266: `d.get("differences") or []` allows vacuous pass. Add `self.assertIn("differences", d)` guard.
3. [P3] `pipeline/canon.py` line 66: `REDUCTIONS["cause"]` is sense-ambiguous (noun vs. spoken reduction). Documented as by design; no action unless a future ruling adds disambiguation.
4. [P3] `pipeline/lock_precheck.py` line 136: bare `#   RULING 131` comment reads as a heading. Cosmetic.
5. [P3] `tests/package/test_lock_precheck.py` line 266: the `all(x["class"] == "spelling only ...")` assertion is stricter than the set-containment pattern used at line 218–219. Consider unifying.
6. [P3] `tests/package/test_lock_precheck.py` line 193: `SPOKEN = MERGED` removes the isolated ruling-72-overlay test. Acceptable given mutation coverage, but noted.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `stray` parameter in `canon.same_words` is the one design decision that, if misapplied, would silently turn a real single-consonant token into a "no difference" — and the entire safety of the gate rests on the caller passing the correct side. The two call sites (`class_84` with `stray="x"`, `class_131` with no stray) are correct today, and mutations M27/M28 pin them, but a single comment at each call site stating *why* that side is the stray side (not just *that* it is) would make the invariant self-documenting for the next person who touches `attest.py`.

## 7. PRODUCTION READY?

**Yes.**

Conditions (all P3, none blocking):
- The tautological test assertion (item 1) should be simplified before the next feature lands on `test_lock_precheck.py`, to avoid a future reviewer trusting a circular check.
- The `d.get("differences") or []` guard (item 2) should be tightened in the same pass.
- No other conditions. The four requested checks all pass: (1) nothing 135 keeps holding can be dropped as spelling; (2) drops sit exactly where the render's do; (3) a same-words pair can never change the sealed text; (4) the tests are correct and comprehensive (28/28 mutations killed, 47 lock tests pass).

---

P1_OR_WORSE: 0