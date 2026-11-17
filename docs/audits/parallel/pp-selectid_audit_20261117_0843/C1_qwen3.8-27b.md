# qwen3.8-27b (qwen/qwen3.8-27b) 450 s finish=stop usage in 17514 / out 23745 usd_reported=0.017745 usd~0.409 (upper-bound price)



# Code Audit: RULING 131 (pp-selectid-20261117_0843)

## Scope Reviewed

`pipeline/attest.py` (new: `RULE_131`, `EDGE_131`, `currency_pair`, `edge_distance`, `class_131`), `pipeline/lock_precheck.py` (modified: `RULES`, `decide`, `attested`), `tests/package/test_lock_precheck.py` (new: `TestRuling131`, 7 tests), `tests/package/test_ruling_105.py` (1 assertion fix).

---

## Findings

### [P2] `edge_distance` recomputes `SequenceMatcher` per-op; `class_131` calls it a third time for `merged`

`class_131` calls `diff(run_t, pin_t)` (1st SM), then `edge_distance` per non-equal op (each does a 2nd SM on the same `r, p`), then a 3rd SM for the `merged` loop. For a segment with *N* differing pairs this is *O(N)* full `SequenceMatcher` passes over the same two token lists. At clip scale (≤ ~200 tokens, ≤ ~10 pairs) this is negligible, but the `full` opcode list is identical every time and could be computed once and threaded through. Not a correctness issue; a maintainability / future-performance note.

### [P2] `currency_pair` docstring slightly overstates the invariant

The docstring says *"every token on both sides of the pair is a 'dollars' right after a number."* For a delete/insert op one side is empty and `all()` over an empty range is vacuously `True`. The code is correct, but a reader skimming the docstring might think both sides must be non-empty. Suggest: *"every token on the non-empty side is a 'dollars' immediately following a numeric token; the empty side is vacuously satisfied."*

### [P3] `attested()` – the `carried` string for ruling 131 is 4 lines longer than the ruling 84 one

Not a defect, but the sealed record's `carried` field is human-readable release text. The ruling 131 version is dense and could be trimmed to match the existing style (the release caption already prints the short form *"word check settled by two of three readings"*). Purely cosmetic.

### [P3] `test_a_repetition_near_the_start_slides_right` – inline comment "1 without the slide"

The comment `# 1 without the slide` is correct (base distance = `min(1, 14) = 1`), but it sits on the same line as the assertion that checks the *slid* distance (3). A reader might momentarily think the assertion expects 1. Suggest moving the comment to its own line or rewording: `# base distance is 1; sliding right through the equal run yields 3`.

---

## Verification of the Seven Requested Checks

| # | Requirement | Verdict |
|---|---|---|
| 1 | Nothing the ruling forbids can be sealed (number, name, negation, 3-way disagreement, run reading < 3 tokens from edge) | **PASS.** `critical()` (unchanged `_lv2_critical`) gates every non-currency pair before the `reads` check. All-three-differ falls to the `else` → `class: None` → caller holds. `edge_distance < EDGE_131` → `class: None` → hold. Tests `test_what_still_holds` covers all five. |
| 2 | A record that disagrees with this side's derivation always holds | **PASS.** `theirs != mine` → `held(...)`. The record's `pairs` are compared field-by-field (run words, approved words, took, edge_distance) against this side's re-derivation. `test_this_side_rederives_every_pair_and_never_trusts_the_record` exercises 9 lie variants. |
| 3 | Currency test cannot hide a real difference | **PASS.** `currency_pair` requires *every* token in the range to satisfy `canon.dollars_after_number` (token == "dollars", predecessor matches `\d+(\.\d+)?`). "euros" ≠ "dollars" → rejected. "dollars" after a non-numeric token → rejected. Double "dollars" → rejected. Tests cover all four negative cases. |
| 4 | Slide cannot carry a non-repetition or go beyond equal context | **PASS.** Sliding is gated on `tag in ("delete","insert")` (replace never slides). The `left`/`right` bounds are the lengths of the *adjacent equal* opcodes in the full SM list. The per-step condition `seq[x±n] == seq[y±n]` ensures the text is invariant under the shift (true repetition). `test_a_repetition_slides_to_its_furthest_placement` and `test_a_repetition_near_the_start_slides_right` verify both directions. |
| 5 | Ruling 72 layer cannot reintroduce or revert a decided word | **PASS.** Two independent checks: (a) `class_84(spoken, merged)` – every difference must be in ruling 84's class (filler, one function word, carry-over); a content word → `class: None` → hold. (b) `reads(sp, s, a, b)` – every non-equal token in spoken must be the second recogniser's own reading at that position; a word the second recogniser never heard → hold. `test_this_side_rederives_every_pair_and_never_trusts_the_record` case 6 (`"the climbing"` not in second recogniser) and case 7 (second recogniser alone can't adopt a content word) verify this. |
| 6 | Ruling 84 path unchanged for other `adopt_spoken` | **PASS.** The new branch is gated on `str(adj.get("rule") or "").startswith(AT.RULE_131)`. Any other rule string falls through to the existing `class_84` path, byte-identical to before. `test_only_a_ruling_131_record_is_rechecked_by_two_of_three` confirms a ruling-17 entry still goes through `class_84` and holds on a content word. |
| 7 | Tests | **PASS.** 7 new tests in `TestRuling131` cover: the real held span adopting (merged + ruling 72), 9 record-lie variants, 5 hold conditions, currency format (real BTC Sessions data + 6 unit-level `currency_pair` checks), repetition sliding (both directions, real mKNAcOFMYD4 data), and ruling-17 fallback. The `test_ruling_105.py` fix (`endswith` → `assertIn`) is correct. The 19-mutation kill rate (19/19) is reported. |

---

## Governing-Law Compliance

- **SENTENCE LAW / SELECTION LOCK / SNAP LIMIT / NEIGHBOUR / ONSET-TAIL / CREDITS / L-a … L-l:** This diff touches only the lock pre-check and attestation layer (text adoption). It does not modify cut points, fades, avatars, sign-off, punctuation, channel selection, canon, release auth, or any gate threshold. No law is violated.
- **LAW 20 / M2:** No gate threshold is changed. No failing gate is reclassified.
- **M12 FAIL CLOSED:** Every missing-data, mismatch, or exception path in `class_131` returns `class: None` (hold). The `decide` function maps any `class: None` to `"verdict": "hold"`. No path produces a pass on incomplete data.
- **LAW 22 (v2f byte-identical):** No renderer, compositor, or selector code is touched.
- **Smallest diff / M1 / GPU0 / no publishing:** Compliant.

---

## P1_OR_WORSE: 0