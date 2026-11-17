# qwen3.8-27b (qwen/qwen3.8-27b) 295 s finish=stop usage in 18019 / out 15591 usd_reported=0.011954 usd~0.288 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
## pp-selectid-20261117_0843 — RULING 131

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma** and **Qwen** both traced the seven checks and passed them. Qwen's four findings (two P2, two P3) were all minor: a docstring overstatement (already fixed), a SequenceMatcher recomputation note (correctly declined — it mirrors the render's own function), a cosmetic carried-string length, and a comment placement. I agree with all of these and with the consensus dispositions.

What I want to flag honestly: in Cycle 1 I did not explicitly trace the `spill_trimmed` function because it did not exist yet. The consensus notes it is new since Cycle 1's diff. My Cycle 2 review below focuses on that new code and the changed exact-equality check.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My verdict |
|---|---|---|
| Adjudication logic (two-of-three) is correct | Gemma | **Agree.** Traced every branch of `class_131`; the priority (currency → critical → reads-approved → reads-run+edge → hold) is sound. |
| Edge distance and sliding are mathematically sound | Gemma | **Agree.** The `max(min(a+n, len(r)-(b+n)))` over shifts is correct; the per-step `seq[x±n]==seq[y±n]` guard ensures true repetition. |
| `edge_distance` recomputes SM per-op | Qwen [P2] | **Agree it's a note, disagree it needs fixing.** It mirrors `pinned.adjudicate_lock` exactly; a different structure would be a second place to keep in step. Consensus correctly declined. |
| `currency_pair` docstring overstates invariant | Qwen [P2] | **Agree, already fixed.** The reworded docstring (line 32-34) now says "non-empty side(s)" and "an empty side is vacuously so." |
| Carried string is 4 lines longer | Qwen [P3] | **Agree it's cosmetic, decline to fix.** It is the sealed human record; the release caption's short form is the integrator's. |
| Inline comment placement | Qwen [P3] | **Agree, already fixed.** Line 407 now reads `# the base distance is min(1, 14) = 1; sliding right through the equal run gives 3` on its own line. |
| All seven checks pass | Both | **Agree.** I re-verified each on the Cycle 2 code (see §3). |

## 3. NEW FINDINGS FROM THIS REVIEW

### [P3] `spill_trimmed` — the `max(lo, hi)` guard is correct but the failure mode it prevents is worth a comment

Line 80: `return s[lo:max(lo, hi)]`. If the start-trim keeps more tokens than the end-trim allows (e.g., a very long speaker repeat at the start and a short non-repeat at the end), `lo > hi` and the slice would be empty without the guard. The guard is correct. A one-line comment (`# guard: lo can exceed hi if the start repeat is longer than the end allows`) would help a future reader understand why `max` is there rather than just `hi`. Not a defect.

### [P3] `class_131` line 143 — the exact-equality check is correct but the error message could name which side failed

```python
if sp != merged and sp != spill_trimmed(merged, s):
```

The message says "neither the merged reading nor the second recogniser's own reading of the span." In a production hold, an operator would benefit from knowing *which* of the two the spoken text was closest to (or that it matched neither). This is a log-quality nit, not a correctness issue. The tests already verify the hold fires.

### Verification of the seven checks on the **changed** code

| # | Requirement | Verdict |
|---|---|---|
| 1 | Nothing the ruling forbids can be sealed | **PASS.** `critical()` (line 122) gates every non-currency pair before the `reads` check. All-three-differ → `else` (line 129) → `class: None` → hold. `edge_distance < 3` → the `elif` on line 126 fails → `else` → hold. `test_what_still_holds` covers all five sub-cases. |
| 2 | A record that disagrees with this side's derivation always holds | **PASS.** Three independent gates: (a) line 108-110: missing/mismatched readings → early `held`; (b) line 137-141: `theirs != mine` → `held`; (c) line 143-145: spoken ≠ merged AND spoken ≠ trimmed → `held`. `test_this_side_rederives_every_pair_and_never_trusts_the_record` exercises 9 lie variants. |
| 3 | Currency test cannot hide a real difference | **PASS.** `currency_pair` requires *every* token in the range to satisfy `canon.dollars_after_number` (token == "dollars", predecessor matches `\d+(\.\d+)?`). "euros" ≠ "dollars" → rejected. "dollars" after non-numeric → rejected. Double "dollars" → second one has non-numeric predecessor → rejected. Tests (lines 369-374) cover all four negative cases. |
| 4 | Slide cannot carry a non-repetition or go beyond equal context | **PASS.** Sliding is gated on `tag in ("delete","insert")` (line 50); replace never slides. `left`/`right` bounds come from adjacent equal opcodes (lines 53-54). Per-step `seq[x±n]==seq[y±n]` (lines 56, 60) ensures text invariance. `test_a_repetition_slides_to_its_furthest_placement` and `test_a_repetition_near_the_start_slides_right` verify both directions. |
| 5 | Ruling 72 layer cannot reintroduce or revert a decided word | **PASS.** Two independent gates: (a) exact equality (line 143): spoken must be *exactly* the merged tokens or *exactly* the second recogniser's trimmed tokens — no other combination; (b) `class_84(spoken, merged)` (line 146): every difference must be in ruling 84's class (filler, one function word, carry-over); a content word → `class: None` → hold. The old position-wise `reads` check is gone; the exact equality is strictly stronger. `test_ruling_72_on_top_is_the_second_recognisers_reading_with_its_spill_trimmed` (7 sub-cases) verifies: padding trimmed, speaker's repeat kept, next-sentence spill trimmed, speaker's end-repeat kept, and that a spoken text containing trimmed spill holds. |
| 6 | Ruling 84 path unchanged for other adopt_spoken | **PASS.** The new branch is gated on `str(adj.get("rule") or "").startswith(AT.RULE_131)` (line 189). Any other rule string falls through to the existing `class_84` path (line 201). `test_only_a_ruling_131_record_is_rechecked_by_two_of_three` verifies a ruling-17 record still goes through `class_84` and holds on a content word. |
| 7 | Tests | **PASS.** 7 tests in `TestRuling131` (up from 6 in Cycle 1; the new `test_ruling_72_on_top...` replaces the old position-wise test). Mutations: 23 of 23 killed (M20-M23 cover the trim's four branches: start-repeat-kept, start-no-repeat-trimmed, end-repeat-kept, end-no-repeat-trimmed). The `test_ruling_105.py` assertion fix (line 453: `endswith` → `assertIn`) is correct — the RULES string now has "ruling 131" appended after "ruling 105." |

### `spill_trimmed` deep trace (the new function)

I traced all 7 sub-cases in `test_ruling_72_on_top...` by hand:

- **Start trim:** SM between `merged` and `s`. If the first opcode is an insert at position 0 covering `s[0:d]`, scan `n` from `d` down to 1 for `s[d-n:d] == s[d:d+n]` (the last `n` tokens of the insert equal the first `n` tokens after it). If found, `lo = d-n` (keep the repeat). If not, `lo = d` (trim all). Verified: "So when, when" → "so" trimmed, "when" repeat kept.
- **End trim:** Symmetric. If the last opcode is an insert at position `len(lock_tokens)` covering `s[c:len(s)]`, scan `n` from `len(s)-c` down to 1 for `s[c:c+n] == s[c-n:c]`. If found, `hi = c+n` (keep the repeat). If not, `hi = c` (trim all). Verified: "And then" trimmed (not a repeat), "out" kept (repeats the preceding "out").
- **No insert at an edge:** `lo` stays 0, `hi` stays `len(s)`. No trim. Correct.
- **Empty `lock_tokens`:** Both edges are inserts. The start scan finds no repeat (nothing before), `lo = d`. The end scan finds no repeat (nothing after), `hi = c = 0`. `max(lo, hi) = lo`. Returns `s[lo:lo] = []`. Correct.

No defects found.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `attest.class_131` (pair loop, criticals, reads, edge) | PASS | PASS | Unchanged; re-verified. |
| `attest.currency_pair` | PASS | PASS | Docstring fixed (qwen P2). Logic unchanged. |
| `attest.edge_distance` (sliding) | PASS | PASS | Unchanged; re-verified both directions. |
| `attest.spill_trimmed` (NEW) | N/A | PASS | Traced all 4 branches and 7 test sub-cases by hand. Correct. |
| `class_131` exact-equality + `class_84` (CHANGED) | PASS (position-wise `reads`) | PASS | The exact equality is strictly stronger than the old `reads` check. Combined with `class_84`, it cannot let through a spoken text that is neither the merged reading nor the second recogniser's trimmed reading. |
| `lock_precheck.decide` (131 branch) | PASS | PASS | Unchanged; re-verified the gate, the pass/adopt/hold logic. |
| `lock_precheck.attested` | PASS | PASS | Unchanged; re-verified the 131 vs 84 branching. |
| `RULES` / `DECODER` constants | PASS | PASS | Updated correctly. |
| Tests (`TestRuling131`, 7 tests) | PASS (6 tests) | PASS | New `test_ruling_72_on_top...` is thorough (7 sub-cases). 23/23 mutations killed. |
| `test_ruling_105.py` assertion fix | PASS | PASS | `endswith` → `assertIn` is the correct relaxation. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None. (Qwen's SM-recomputation note is correctly declined; the docstring and comment fixes are already applied.)

**P3 NITS:**
- [P3] `attest.py:80` — add a one-line comment explaining the `max(lo, hi)` guard (prevents empty slice if start-repeat exceeds end-allowance).
- [P3] `attest.py:144` — the hold message could name which of the two expected texts the spoken text was closest to, for operator debugging.

Neither P3 blocks shipping.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The replacement of the position-wise `reads` check with the exact-equality gate (`sp == merged or sp == spill_trimmed(merged, s)`) is the single most important change in this diff: it closes the class of bugs where a spoken text could be assembled from *parts* of the merged reading and *parts* of the second recogniser's reading, neither of which the render would have produced, while still passing a token-by-token alignment test.

## 7. PRODUCTION READY?

**Yes.**

Conditions (all already met in the code as submitted):
1. The `spill_trimmed` function correctly trims non-repeat spill at both edges and keeps the speaker's own edge repeat at both edges — verified by 7 sub-cases in `test_ruling_72_on_top...` and by hand-trace.
2. The exact-equality check on line 143 cannot let through a spoken text that is neither the merged reading nor the second recogniser's trimmed reading — verified by the 4 "hold" sub-cases in the same test and by the 3 "neither the merged reading nor" cases in `test_this_side_rederives...`.
3. All seven original checks pass on the changed code — verified above.
4. 23 of 23 mutations killed; 871 tests across 40 files pass by exit code.
5. The ruling 84 path is unchanged for non-131 records — verified by `test_only_a_ruling_131_record_is_rechecked_by_two_of_three` and by the `startswith` gate on line 189.

P1_OR_WORSE: 0