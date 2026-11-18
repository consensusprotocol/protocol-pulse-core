# qwen3.8-27b (qwen/qwen3.8-27b) 164 s finish=stop usage in 6874 / out 5499 usd_reported=0.005135 usd~0.103 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261118_0957 | RULING 148 (3) / 149

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Reviewing the three Cycle 1 outputs against my own trace:

- **Qwen's `autojunk=False` observation** [P3]: I traced the new `SequenceMatcher` call and noted it was correct, but I did not explicitly flag the *asymmetry* with the old `diff()` path. If `diff()` internally omits `autojunk=False`, the two branches have subtly different semantics for sequences > 200 tokens. In practice a single clip's transcript never approaches that length, so this is theoretical, but it is a real (if dormant) inconsistency between the two code paths. I should have called it out.

- **GPT-OSS's "inconsistent `texts` tuple"** [P3]: I verified that `texts = (spoken, approved)` is correct (the critical-word test reads human-readable text, not tokens), but I did not explicitly note that a future reader might *misread* the code as comparing the wrong data. The concern is documentation clarity, not a defect. I agree it's a valid P3.

- **GPT-OSS's "potential misuse of `approved_tokens`"** [P3]: I confirmed the single caller passes the correct list, but I did not flag the *future-maintainer* risk of someone passing non-canonical tokens. Valid P3.

Nothing was missed that would change the severity assessment. All three models' findings are P3 (style, documentation, defensive-coding nits).

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Model | Finding | My verdict |
|-------|---------|------------|
| Gemma | No violations, fix correct, tests comprehensive | **Agree.** The fix is surgical and the tests cover the bug mechanism, the end-to-end adoption, and the fail-closed guarantee. |
| GPT-OSS #1 | Misuse risk for `approved_tokens` | **Agree [P3].** Internal function, one caller, but a `Sequence[str] \| None` annotation would document the contract. |
| GPT-OSS #2 | Backward-compat / signature confusion | **Agree [P3].** The default `None` preserves the old API. A docstring note suffices. |
| GPT-OSS #3 | Inconsistent `texts` tuple | **Partially agree [P3].** The code is *correct*—`texts` must be the human-readable string for the critical-word test. The "inconsistency" is only in the reader's perception. A one-line comment would help. |
| GPT-OSS #4 | No effect on other callers | **Agree [P3].** Informational, not a finding. |
| GPT-OSS #5 | No new logic errors | **Agree [P3].** Informational. |
| Qwen #1 | `autojunk=False` asymmetry | **Agree [P3].** Theoretical for < 200 tokens. A shared helper or comment would make the invariant visible. |
| Qwen #2 | No type guard on `approved_tokens` | **Agree [P3].** `list()` accepts any iterable. The single caller passes a list of strings. Annotation suffices. |
| Qwen #3 | Docstring invariant | **Agree [P3].** "Must be the canon tokens of `approved`" would close the gap. |

**No disagreements.** All findings are correctly scoped at P3.

---

## 3. NEW FINDINGS FROM THIS REVIEW

After re-reading the diff with the benefit of the other models' analyses:

**[P3] The `list(approved_tokens)` shallow copy is correct but untested for the mutation case.**
Line 29: `p = list(approved_tokens)`. This protects the caller's list from mutation. However, no test verifies that `class_84` does *not* mutate the passed list. A one-line assertion in `test_class_84_reads_given_tokens_as_they_are` (e.g., `tokens = ["24","7","365","days"]; AT.class_84(..., tokens); self.assertEqual(tokens, ["24","7","365","days"])`) would lock in the non-mutation contract. Non-blocking.

**[P3] The test `test_class_84_reads_given_tokens_as_they_are` first assertion documents the bug but is coupled to `canon`'s spaced-thousands rule.**
If `canon.py` ever changes its `_SPACED_THOUSANDS` regex (e.g., to require a comma), this test would break for the wrong reason. A comment noting "this assertion encodes the current canon spaced-thousands behavior" would aid future maintenance. Non-blocking.

No P0, P1, or P2 findings.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `class_84` logic (new branch) | Correct | Correct | No change. The `SequenceMatcher` call with `autojunk=False` is correct; the `drop`/filler/classification pipeline is unchanged and operates on the same `r` indices. |
| `class_131` call-site | Correct | Correct | No change. Passing `merged` as `approved_tokens` is the minimal correct fix. |
| `texts` / critical-word test | Unchanged | Unchanged | No change. `texts = (spoken, approved)` is set before the branch; `approved` is still the joined string. |
| Other callers of `class_84` | Unchanged | Unchanged | No change. All pass `approved_tokens=None` (default), taking the old `diff()` path. |
| Tests | Comprehensive | Comprehensive | No change. Four tests cover: bug mechanism, end-to-end adoption, fail-closed (genuine differences still hold), and direct token-passing. Mutation testing (2/2 killed) confirms effectiveness. |
| Law compliance (L-k, L-v 2, Law 20/M2, M12) | Compliant | Compliant | No change. Both sides are canon tokens. No threshold changed. No new pass path. |

**No score changes.** The code is correct as written.

---

## 5. FINAL PRIORITY LIST

| Priority | Finding | File / Line | Action |
|----------|---------|-------------|--------|
| P3 | `autojunk=False` asymmetry with `diff()` path | `attest.py:30` | Add a one-line comment: `# autojunk=False matches diff()'s semantics; sequences here are < 200 tokens` or extract a shared helper. |
| P3 | No type annotation on `approved_tokens` | `attest.py:10` | Add `approved_tokens: Sequence[str] \| None = None` (or a comment). |
| P3 | Docstring does not state the precondition | `attest.py:20-23` | Add: "Must be the canon tokens of `approved` (i.e., `canon.canon_tokens(approved)` or the equivalent merged-reading list)." |
| P3 | No non-mutation test for `approved_tokens` | `test_lock_precheck.py:91-94` | Add a one-line assertion that the passed list is unchanged after the call. |
| P3 | Test couples to `canon`'s spaced-thousands regex | `test_lock_precheck.py:78` | Add a comment noting the coupling. |

**No P0, P1, or P2 items.**

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The fix is already the highest-leverage change: passing the merged reading's tokens *as they are* instead of joining and re-tokenizing eliminates the entire class of spaced-thousands false-positives at the source, with zero impact on any other caller.

If I had to name one *additional* change that would most improve the code's long-term health: **add the type annotation and precondition sentence to the docstring** (lines 10 and 20-23). This is the single point where a future maintainer could introduce a silent correctness bug by passing the wrong token list, and two sentences of documentation close that gap at zero runtime cost.

---

## 7. PRODUCTION READY?

**Yes.**

Conditions (all P3, none blocking):
1. The five P3 items above are recommended for a follow-up commit but do not gate this merge.
2. The test suite (42 files / 938 passed, exit 0) and mutation testing (2/2 killed) confirm the fix is correct and the tests are effective.
3. No law is violated. No threshold is changed. No new pass path is introduced. The default path is byte-identical to the pre-fix behavior.

---

P1_OR_WORSE: 0