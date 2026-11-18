# qwen3.8-27b (qwen/qwen3.8-27b) 161 s finish=stop usage in 7690 / out 6200 usd_reported=0.005782 usd~0.116 (upper-bound price)



# Code Audit — pp-selectid / RULING 148 (3) / 149

## Summary

The change is a surgical fix to `attest.class_84`: when the caller already holds the approved side's canon tokens (as `class_131` does with its `merged` list), pass them through instead of joining to a string and re-tokenising. The re-tokenisation was the bug: canon's spaced-thousands rule turned `"24 7 365"` into `["24", "7365"]`, creating a phantom number difference against the spoken `["24", "7", "365"]`.

I verified the three questions posed in the diff header, plus law compliance and edge cases.

---

## Findings

### [P3] `autojunk=False` is new relative to the old `diff()` path

```python
ops = [o for o in SequenceMatcher(None, r, p, autojunk=False).get_opcodes() if o[0] != "equal"]
```

If the existing `diff()` helper does **not** pass `autojunk=False`, then for token sequences longer than 200 elements the two paths could produce different opcodes (SequenceMatcher's automatic-junk heuristic would suppress frequent elements). In practice a single clip's transcript will never exceed 200 tokens, so this is theoretical. Still, the new branch is now the *only* place `autojunk=False` is explicit; if `diff()` lacks it, the two code paths are not byte-identical in their diffing semantics for the spoken side. Worth a one-line comment or a shared helper so the invariant is visible.

### [P3] No guard that `approved_tokens` is a list of strings

`list(approved_tokens)` will happily wrap a generator, a set, or a list of non-strings. The function would then fail (or misbehave) at the `r[i] in FILLERS` or the SequenceMatcher comparison. This is an internal function with exactly one caller (`class_131`) that passes `merged` (a list of canon-token strings), so the risk is nil in production. A `typing` annotation (`Sequence[str] | None`) on the signature would document the contract without adding runtime cost.

### [P3] Docstring could state the invariant on `approved_tokens`

The new docstring paragraph explains *why* the parameter exists (the join-re-read bug) but does not state the precondition: **`approved_tokens` must be the output of `canon.canon_tokens` (or the equivalent merged-reading token list) for the same text that `approved` represents.** If a future caller passes tokens from a *different* normalisation, the comparison is silently meaningless. One sentence ("must be the canon tokens of `approved`") would close that gap.

---

## Answers to the three review questions

**(1) Can `approved_tokens` let a genuine number / name / negation difference through?**

No. The classification logic (steps 2–5 of the docstring) operates on the *values* in the opcode spans, not on how the tokens were obtained. I traced three cases:

| Spoken tokens | `approved_tokens` | Opcode | Step that holds |
|---|---|---|---|
| `[…, "41", …]` | `[…, "40", …]` | substitute | 2 – number |
| `[…, "do", "not", …]` | `[…, …]` | insert ×2 | 2 – negation |
| `[…, "euros"]` | `[…, "dollars"]` | substitute | 2 – name |

The test `test_a_number_that_differs_still_holds` confirms this for 365→366 and 24→25.

**(2) Is the merged reading's critical-word test (`texts`) still the same as before?**

Yes. `texts = (spoken, approved)` is set before the branch and is unchanged. `approved` is still the joined string (`" ".join(merged)` in `class_131`). The critical-word scan reads the human-readable text, not the token list. The diff only changes how `r`, `p`, and `ops` are computed for the *structural* comparison.

**(3) Anything else this changes?**

- All other callers of `class_84` pass `approved_tokens=None` (the default) and take the old `diff(spoken, approved)` path. No behavioural change for them.
- `list(approved_tokens)` creates a shallow copy, so the caller's list is not mutated.
- The `drop` / filler-removal / re-compare logic downstream of `ops` is unchanged; it reads `r` (spoken tokens) and the opcode indices, which are now computed against the correct approved tokens.
- Law L-k (one canonical form): both sides of the comparison are canon tokens. Compliant.
- Law 20 / M2: no threshold is changed; a held class is still a hard stop. The fix removes a *false* hold, not a real one.
- M12 fail-closed: no new pass path is introduced; the default path is byte-identical to before.

---

## Law-compliance spot-check

| Law | Status |
|---|---|
| SENTENCE LAW | Not touched by this diff. |
| SELECTION LOCK | Not touched. |
| L-k (canon) | Improved: approved side is now compared as its actual canon tokens. |
| LAW 20 / M2 | Compliant: no threshold or acceptance criterion changed. |
| M12 | Compliant: no new pass path. |
| Smallest diff / M1 | 100-line diff, one function signature change, one call-site change, one test class. Minimal. |

---

## Verdict

The change is correct, well-scoped, and well-tested. The root cause (join → re-tokenise → spaced-thousands merge) is eliminated at the single point where it occurred. No gate is weakened; genuine differences are still caught. The three P3 items are documentation/robustness nits, not defects.

P1_OR_WORSE: 0