# qwen3.8-27b (qwen/qwen3.8-27b) 124 s finish=stop usage in 18390 / out 4434 usd~0.122 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the boundary logic (`<` vs `<=`) and the "repeated token" edge case. I missed the **structural ordering flaw** that Grok and GLM identified: the original `parents_first` logic only reordered the *spotlight finalists*, but the **medley** path (which runs on the full pool) had no such protection. This meant a high-ranked variant could be selected by the medley *before* its parent was even considered, violating the "full clip first" intent of Ruling 104.

I also underestimated the risk of **stale holds**. I assumed `holds()` would naturally filter for current relevance, but the Cycle 1 code (and my initial reading of the diff) allowed `holds()` to read *any* decoder/rules entry. Grok and GLM correctly flagged that an older decoder's hold could trigger a variant even if the current decoder passed the clip. The rework (replacing parents, using `lock_precheck.answer` for current-only) addresses this, but I need to verify the *implementation* of that rework in the current diff.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok <high> (Medley ordering):** **Agree.** The removal of `parents_first` and the introduction of `replaced` (dropping the parent from the pool entirely if held) is the correct fix. If the parent is dropped, it cannot compete in the medley. If it's not held (just over ceiling), it stays "beside" the variant, which is acceptable because the medley can choose either, but the *spotlight* (which has the 35s ceiling) will naturally prefer the variant if the parent is too long, or the parent if the variant is too short. Wait — if the parent is over the ceiling, it *cannot* be a spotlight. So the medley is the only place it competes. Is that a problem? Ruling 104 says "a spotlight (and a medley hook or clip) may be sealed as a variant". It doesn't explicitly forbid the medley from using the parent if the parent is lawful. However, if the parent is *held*, it is *not* lawful. The rework drops held parents. This is correct.
*   **Grok <medium> (ALONE score inheritance):** **Disagree (Refuted).** As noted in the consensus, `M.record` creates a fresh record. The `scores` dict is copied, but the *verdict* (the actual ALONE rating from the clip scorer) is keyed by `moment_id` and `text_sha256`. Since the variant has a new ID and new text, it *must* get a new verdict. The copied `scores` are just the miner's initial heuristic scores, not the final gate verdicts.
*   **GLM (b) (Repeated token):** **Agree (Refuted by design).** The `held_word` function finds the *first* occurrence of the held token. The variant ends *before* that sentence. If the token appears again later, it is in the "left out" part. If it appears *earlier*, the variant ends before the *first* occurrence, so the later one is also left out. The logic `src.sentences[k][1] < i` ensures the variant ends at the last sentence *entirely before* the held word's index. This is robust.
*   **Qwen (Boundary ambiguity):** **Agree (Refuted by tests).** The tests explicitly verify that `E.Span(src, k0, k)` includes sentences `k0` to `k-1` (or `k` inclusive? Let's check). `variant(m, src, 2, ...)` on a parent `[0, 4]` results in `[0, 2]`. The text is `SENTENCES[:3]` (indices 0, 1, 2). So `k=2` means "end at sentence index 2". The span is `E.Span(src, 0, 2)`. In `eligibility.Span`, the second argument is typically the *exclusive* end index for the *sentence list*? No, `E.Span(src, k0, k1)` usually means sentences `k0` to `k1-1`? Or `k0` to `k1`?
    *   Test line 296: `v["sentences"]` is `[0, 2]`.
    *   Test line 295: `v["text"]` is `SENTENCES[:3]` (3 sentences).
    *   So `sentences=[0, 2]` means "from sentence 0 to sentence 2 inclusive".
    *   `E.Span(src, 0, 2)` must therefore be inclusive of the end index `2`.
    *   In `for_pool`, `ks = [k for k in range(k0, k1) if ... src.sentences[k][1] < i]`.
    *   If `i` is the index of the held word, and `src.sentences[k][1]` is the last word index of sentence `k`, then `src.sentences[k][1] < i` means sentence `k` ends *before* the held word.
    *   We pick `k = ks[-1]` (the last such sentence).
    *   We call `variant(m, src, k, ...)`.
    *   This creates a span ending at sentence `k`.
    *   Since sentence `k` ends before the held word, the held word is excluded. Correct.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> `pipeline/tail_variant.py:147` — The `held_word` placement uses `canon_spans` on the *parent's* words, but compares against `src.tokens` indices.**
`held_word` returns `w0 + spans[i][1]`. `w0` is `m["words"][0]` (the start word index of the parent). `spans` are computed on `src.tokens[w0:w1+1]`. So `spans[i][1]` is the *relative* index of the last word of the held token within the parent's word slice. Adding `w0` gives the *absolute* index in `src.tokens`. This is correct.
However, `for_pool` uses this absolute index `i` to check `src.sentences[k][1] < i`. `src.sentences[k][1]` is the absolute index of the last word of sentence `k`. This comparison is valid.

**<medium> `pipeline/tail_variant.py:157` — The ceiling check uses `src.tokens[src.sentences[k][1]]["end"]`.**
This assumes `src.sentences[k][1]` is a valid index into `src.tokens`. Since `src.sentences` is derived from the same source, this is safe.

**<high> `tests/package/proof_ledger.py:203` — The `with_variants` function returns a new list, but does it preserve the *order* of the original moments?**
`return [m for m in moments if m["moment_id"] not in replaced] + variants`
This appends variants to the *end* of the list.
In `spotlight.build`, the pool is processed. Does the order of the pool matter for the medley?
The medley uses `rank_key` to sort. So the initial order in the list doesn't matter for the medley.
For the spotlight, the free pool is filtered, then sorted by `rank_key`. So order doesn't matter.
However, if there is any *tie-breaking* in the sort that relies on stable order (Python's `sorted` is stable), the variants will come *after* the original moments in the list. If a variant and its parent have the *same* `rank_score`, the parent (which is earlier in the list) will be preferred. This is actually *good* for the "full clip first" intent, even without `parents_first`. But if the variant has a *higher* rank score, it will be sorted before the parent.
Wait, if the parent is *replaced*, it's not in the list. So no competition.
If the parent is *not* replaced (ceiling case), it stays. The variant is appended.
If the variant has a higher rank, it sorts first. Is that a problem?
Ruling 104: "a spotlight ... may be sealed as a variant ... when that is what keeps it lawful".
If the parent is over the ceiling, it *cannot* be a spotlight. So the variant is the *only* option for the spotlight. The medley *can* use the parent.
So, if the variant sorts first in the medley, it might be chosen over the parent. Is that a violation?
The ruling says "a medley hook or clip may be sealed as a variant". It doesn't say "the parent must be preferred in the medley".
However, the orchestrator's instruction for Blockware was "FIRST the re-listen... if it holds, seal the tail-side variant". This implies a preference for the full clip *if it passes*. If it doesn't pass (held), the variant is the fallback.
In the ceiling case, the parent *passes* the hold (it's not held), but fails the ceiling. So the variant is the *only* spotlight candidate. The medley can use either.
I don't see a violation here.

**<critical> `pipeline/tail_variant.py:142-154` — Logic flaw in `for_pool` when *both* a hold and a ceiling apply.**
```python
        if e is not None:
            if str(e.get("reason") or "").startswith(CUT_HOLD):
                wanted.append((k1 - 1, ...))
            else:
                i = held_word(m, src, e)
                ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]
                if ks:
                    wanted.append((ks[-1], ...))
                else:
                    notes[mid] = ...
        if float(m.get("duration_s") or 0) > ceil_s:
            t0 = float(m["start"])
            ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]
            if ks:
                wanted.append((ks[-1], ...))
            else:
                notes[mid] = ...
        if not wanted:
            continue
        k = min(x[0] for x in wanted)
```
If a hold exists, `wanted` gets an entry. If the ceiling is also exceeded, `wanted` gets *another* entry.
`k = min(x[0] for x in wanted)` picks the *shortest* variant (smallest `k`).
This is correct: "When two apply, the shorter variant (it satisfies both)."
However, consider the case where the hold is in the *first* sentence.
`held_word` returns `None` (or the index is such that `ks` is empty).
`notes[mid]` is set to "no variant: the held word is in its first sentence".
But then the code *continues* to the ceiling check.
If the ceiling is also exceeded, `wanted` gets an entry from the ceiling check.
Then `k = min(...)` picks the ceiling variant.
But the parent is *held*. The hold is *final*.
The code *replaces* the parent (`replaced.add(mid)` at line 166) *only if* `e is not None`.
So the parent is replaced.
But the variant generated is based on the *ceiling*, not the *hold*.
Is this lawful?
The hold is on a word in the first sentence. The variant ends at the first sentence boundary *after* the held word? No, the variant ends at an *earlier* boundary.
If the held word is in the first sentence, there is *no* earlier boundary.
So a variant *cannot* leave the held word out.
But the code generates a variant based on the *ceiling*.
This variant *still contains* the held word (because it ends at a later boundary, or the same boundary).
Wait, if the held word is in sentence 0, and the ceiling variant ends at sentence 2, the variant *contains* sentence 0, and thus the held word.
The variant is *not* lawful (it contains the held word).
But the parent is *replaced* by this unlawful variant.
The variant will then face the gates.
The lock pre-check will *hold* the variant (because it contains the held word).
So the variant will fail.
The parent is gone.
The result: *no pin* for this moment.
Is this a bug?
The ruling says: "if it holds, seal the tail-side variant ... if it passes every gate."
If the variant *cannot* be made lawful (because the hold is in the first sentence), then *no* variant should be made.
The code *should* not replace the parent in this case, or should not generate a variant.
But the code *does* generate a variant (based on the ceiling) and *replaces* the parent.
This leads to a "spend without a pin" scenario: the parent is removed, the variant is added, the variant fails the pre-check, and nothing is sealed.
This is a **<high>** severity issue. It wastes the build's opportunity to potentially seal the parent (if the hold was somehow resolved, though the ruling says it's final) or to simply not seal anything.
Actually, if the hold is final, the parent *cannot* be sealed anyway. So removing it is correct.
But adding a *variant* that *also* fails is wasteful.
More importantly, if the ceiling variant *does* pass the pre-check (e.g., if the held word is *not* in the variant's span? No, we established it is), it would be sealed.
But we established it *contains* the held word.
So it *will* fail.
So the outcome is: no pin.
Is this a violation of the ruling?
The ruling says "if it holds, seal the tail-side variant ... if it passes every gate."
It implies that if the variant *cannot* pass, we don't seal it.
It doesn't explicitly say "don't replace the parent".
But replacing the parent with a variant that *guaranteed* fails is a design flaw.
It should be: if the hold is in the first sentence, *no* variant is possible. The parent is held. The build should just skip it.
The current code replaces the parent with a doomed variant.
This is not a "wrong pin" (it doesn't seal a bad pin), but it is a "spend without a trigger" (it spends the build's effort on a variant that cannot pass).
I will tag this as **<high>**.

**<medium> `pipeline/tail_variant.py:166` — `replaced.add(mid)` is called if `e is not None`.**
This happens *after* the `wanted` list is built.
If `wanted` is empty (no variant possible), the code `continue`s at line 163.
So `replaced.add(mid)` is *not* called.
So if the hold is in the first sentence, `wanted` is empty (from the hold check), but the ceiling check might add to `wanted`.
If the ceiling check *also* fails (no boundary within ceiling), `wanted` is empty.
Then `continue`.
So `replaced` is *not* updated.
The parent stays in the pool.
The parent is held.
The parent will fail the pre-check.
No pin.
This is correct.
But if the ceiling check *succeeds*, `wanted` is not empty.
Then `k` is picked.
Then `replaced.add(mid)` is called.
So the parent is replaced by a variant that contains the held word.
This variant will fail.
So the "doomed variant" scenario only happens if the ceiling check *succeeds* while the hold check *fails* (due to first sentence).
This is a specific edge case.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Boundary Logic | 8/10 | 9/10 | Verified against tests. The `<` comparison is correct. |
| Gate Independence | 7/10 | 9/10 | Confirmed that `M.record` creates fresh IDs and verdicts. |
| Ordering/Competition | 5/10 | 8/10 | The `replaced` mechanism fixes the medley competition issue. |
| Edge Cases (First Sentence Hold) | 6/10 | 7/10 | Identified the "doomed variant" scenario. |
| Test Coverage | 8/10 | 9/10 | Tests cover the main cases, but not the "first sentence hold + ceiling" edge case. |

## 5. FINAL PRIORITY LIST

**P1 HIGH**
1.  **`pipeline/tail_variant.py:142-166`**: When a hold is in the first sentence (no variant possible) but the ceiling is exceeded, the code generates a variant based on the ceiling and replaces the parent. This variant *contains* the held word and will fail the pre-check. This results in a "doomed variant" that wastes build resources.
    *   *Fix:* If the hold is in the first sentence, do *not* generate a variant based on the ceiling. Or, do *not* replace the parent if the generated variant still contains the held word.
    *   *Concrete Sequence:* Parent `[0, 4]`, held word in sentence 0. Ceiling exceeded. `wanted` gets ceiling entry. `k` picked. `replaced.add(mid)`. Variant `[0, 2]` created. Variant contains sentence 0 (held word). Variant fails pre-check. Parent is gone. No pin.

**P2 MEDIUM**
1.  **`tests/package/test_ruling_104.py`**: Add a test for the "first sentence hold + ceiling" edge case to verify the behavior (and fix the P1 issue).
2.  **`pipeline/tail_variant.py:147`**: The `held_word` function returns `None` if the held word is in the first sentence. The `for_pool` function should explicitly check for this and *not* proceed to the ceiling check if the hold is unplaceable.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Prevent the generation of "doomed variants" when a hold is in the first sentence.**
If the held word is in the first sentence, no tail-side variant can exclude it. Therefore, no variant should be generated, and the parent should not be replaced (or should be replaced by *nothing*, i.e., just removed). The current code generates a variant based on the ceiling, which is guaranteed to fail, wasting the build's effort.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix the "doomed variant" edge case (P1 HIGH) where a first-sentence hold combined with a ceiling violation leads to the replacement of the parent with a variant that still contains the held word.
2.  Add a test for this edge case.
3.  Verify that the `replaced` mechanism correctly handles the case where *no* variant is possible (the parent should be removed from the pool, but no variant added).

The core logic is sound, the boundary handling is correct, and the gate independence is verified. The main risk is the edge case where the variant is generated but is guaranteed to fail, leading to wasted resources and potential confusion in the build logs.