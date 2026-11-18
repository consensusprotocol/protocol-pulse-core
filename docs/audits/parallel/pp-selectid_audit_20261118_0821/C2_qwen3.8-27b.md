# qwen3.8-27b (qwen/qwen3.8-27b) 283 s finish=stop usage in 17808 / out 10665 usd_reported=0.010529 usd~0.213 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## Feature: pp-selectid-20261118_0821 | RULING 147

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1 I gave a clean bill of health (P1_OR_WORSE: 0). Reviewing the other models' outputs against the actual diff:

- **Gemma** confirmed every structural element I verified independently. No new issues.
- **Qwen's [P1]** (SOFT_GATES missing EXCEPTION_GATE) was correctly **refuted** by the consensus: the literal `"pbx_exception"` has been in `SOFT_GATES` since the RULING 144 landing (fc191b4e), outside this diff's hunks. The test `assertIn(PP.EXCEPTION_GATE, PP.SOFT_GATES)` passes. I agree with the refutation.
- **Qwen's [P2]s** (ONSET/TAIL law text, gate_g16 trimmed path) concern the integrator's `sentence_law.py`, which is copied byte-identical (sha256 48e5b639…). Not this side's to amend. Agreed.
- **Qwen's [P3]s** (double-call in `to_pin`, empty-`tried` message, timeline header, RULES comment formatting) are all valid nits. I noted the double-call in Cycle 1 as cosmetic; I did not explicitly flag the empty-`tried` message or the timeline inconsistency. Minor omissions, no severity impact.

Nothing material was missed.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Reasoning |
|---|---|---|
| Qwen [P1] SOFT_GATES | **Disagree (refuted)** | `EXCEPTION_GATE = "pbx_exception"` is already in `SOFT_GATES` since fc191b4e. The diff context simply doesn't show that line (it's unchanged). Test suite confirms: 398 passed. |
| Qwen [P2] ONSET/TAIL text | **Agree it's valid, disagree it's this side's** | The law-text amendment belongs to the integrator's file. This side copies it byte-identical. |
| Qwen [P2] gate_g16 trimmed | **Agree it's valid, disagree it's this side's** | Same reasoning. The `trimmed=lock.get("trimmed_leading")` addition is part of the byte-identical mirror. |
| Qwen [P3] double-call in `to_pin` | **Agree** | 4 calls where 2 suffice. Cosmetic. Inconsistent with the `review_problems` fix that uses locals. |
| Qwen [P3] empty-`tried` message | **Agree** | Practically unreachable (if no candidates, `accepted_cut` returns None first), but the "digital zeros lie between" phrasing is misleading for the "no candidates" case. |
| Qwen [P3] timeline header | **Agree** | 08:21 UTC vs. 08:20 ET ruling timestamp is a ~5-hour gap. Likely a timezone-labeling error in the header. |
| Gemma: all findings | **Agree** | Every structural confirmation matches my independent read. |
| Claude consensus: no change C1→C2 | **Agree** | The code is the same; the additional context from other models doesn't change the assessment. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

After a second, line-by-line pass with the other models' outputs in mind:

**[P3] `to_pin` double-call inconsistency (re-confirmed, now with contrast)**

`review_problems` was correctly refactored to bind locals:
```python
n, cap = content_flags(mp.get("gates")), flags_cap(mp.get("gates"))
```
But `to_pin` (diff lines 68–69) still inlines four calls:
```python
problems += [f"{content_flags(pk.get('gates'))} review flags, over {flags_cap(pk.get('gates'))} (ruling 136 (2) / "
             f"147)"] if content_flags(pk.get('gates')) > flags_cap(pk.get('gates')) else []
```
Not a bug (both functions are pure), but the asymmetry within the same file is a readability nit. A future maintainer might wonder if the two call-sites are meant to differ.

**[P3] `hook_lead` refusal message when `tried` is empty (re-confirmed)**

If `cut_candidates(src, plan)["in"]` returns `[]`, the refusal reads "…no legal cut has genuine quiet from the cut to the word for a D1 pad to join (digital zeros lie between)." The actual cause is "no candidates exist." Unreachable in practice (the `accepted_cut` → None path fires first), but the message is technically wrong for that edge. A one-line `if not tried:` branch would fix it.

**[P3] `padded_lead_ms` docstring phrasing**

The docstring says "the clip's fade, then pad" but the code does `np.concatenate([tone, _cut_head(src, c, fade_ms)])` — pad first, then the (faded) cut head. The docstring's "then" is reversed. The code is correct; the comment is slightly misleading.

**No new P0, P1, or P2 findings.**

I specifically verified:
- `flags_cap` cannot return 5 for a non-excepted pin: `EXCEPTION_GATE in gates` is the sole gate, and `EXCEPTION_GATE` is only written by the driver under `--pbx-exception`, sealed with the gates. No other code path inserts it.
- The `_ruling73` IN-bound logic correctly handles the `file_head` case (keeps `hi` at `max(cut_hi, bound)` so a negative bound doesn't shrink the range below 0).
- The `span_fidelity` fail-closed check (`keep[n:].any()`) is sound: if `keep.any()` is True and `keep[n:].any()` is False, then `keep[:n].any()` must be True, so `np.max` never operates on an empty selection.
- The `lock_cut` SOFT-failure path correctly preserves the planned cut's `valley_in` (since `hook["cut_in"] == pick["cut_in"]` in the refused branch, the `valley_in = False` reassignment is skipped).
- The `write_lock_cut_table` refactoring preserves `pause_in`/`pause_out` in the output dict via `lock_cut`'s `out` dict, matching the old behaviour.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `lock_precheck.py` (RULES, DECODER) | PASS | PASS | No change. Strings and comment are correct. |
| `package_pin.py` (flags_cap, review_problems, to_pin) | PASS | PASS | Logic correct. P3 double-call in `to_pin` noted but unchanged. |
| `sentence_law.py` (mirror: _ruling73, hook_lead, lock_cut, span_fidelity, etc.) | PASS | PASS | Byte-identical to integrator. All logic verified. |
| Tests (test_lock_precheck, test_ruling_105, test_ruling_137) | PASS | PASS | Decoder pins updated. Exception cap tests correctly cover 4/5/6 on excepted pin and 4 on non-excepted pin. |
| Overall | P1_OR_WORSE: 0 | P1_OR_WORSE: 0 | No change. |

---

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 NITS (should fix, not blocking):**

1. **`package_pin.py` ~line 68–69** (`to_pin`): Bind `content_flags` and `flags_cap` to locals, matching the `review_problems` pattern. Four calls → two.
2. **`sentence_law.py` ~line 257–263** (`hook_lead` refusal): Add a `if not tried:` branch with a distinct message ("no legal cut candidates in the pause") before the "digital zeros" text.
3. **`sentence_law.py` ~line 202–206** (`padded_lead_ms` docstring): "the clip's fade, then pad" → "the pad, then the clip's faded head" to match the `np.concatenate([tone, _cut_head(...)])` order.
4. **Audit header**: Correct the `Generated:` timestamp timezone label (08:21 ET, not UTC) so the audit trail is internally consistent with the 08:20 ET ruling.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `to_pin` double-call (P3 #1) is the one line that, if left unfixed, will cause a future maintainer to wonder whether the two call-sites in the same file are intentionally different — and in a codebase where "the bytes measured by the gates are identical to the bytes used in the final render" is a governing law (L-j), that ambiguity is the kind of thing that breeds a real bug six months from now.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all already met or trivially satisfiable):
1. The integrator's `sentence_law.py` at `r146-g17a 7c1bed55` has passed its own two audit cycles (stated in the description; sha256 48e5b639… confirmed byte-identical).
2. The full test suite passes: `test_lock_precheck` + `test_ruling_105` + `test_attest` + `test_ruling_137` + `test_angles` + `test_medley` (398 passed; dev61 suites 41 files / 924, exit 0).
3. The three-clean-videos release criterion includes at least one segment with a trimmed leading word (to exercise the new `gate_g16` trimmed-onset path) and one hook segment (to exercise the `hook_lead` → SOFT path). This is a release-process check, not a code change.

The four P3 nits are non-blocking and can be addressed in a follow-up commit.

---

P1_OR_WORSE: 0