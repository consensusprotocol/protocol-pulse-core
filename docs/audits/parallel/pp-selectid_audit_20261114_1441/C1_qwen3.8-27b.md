# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 18116 / out 2261 usd~0.088 (upper-bound price)

I have carefully audited the diff against the Ruling 104 requirements, the governing laws, and the specific attack vectors provided.

### Findings

**<critical> None**
The core logic for creating tail variants (`pipeline/tail_variant.py`) correctly implements the "fail closed" and "sentence law" requirements.
1.  **Boundary Integrity:** `variant()` uses `E.Span(src, k0, k)`, ensuring the new clip ends exactly at a sentence boundary. It does not cut mid-sentence.
2.  **Gate Independence:** The variant is created via `M.record(...)`, which generates a new `moment_id` and re-judges eligibility. The `for_pool` function adds these to the main pool *before* the spotlight/medley stages run. Consequently, the variant faces all gates (Step A, ALONE, Lock Pre-check) as a distinct entity. It does not inherit the parent's cached verdicts.
3.  **Snap Protection:** `spotlight.snap` explicitly checks for `derived_from.ruling == 104` and returns `None` (blocking the snap) if the duration is below the target. This prevents the variant from being extended outward to include the "held" words that caused the parent to fail.
4.  **Ordering:** `finalist_order` ensures the parent is always tried before the variant. If the parent passes (e.g., via a successful re-listen), the variant is never reached. If the parent fails, the variant is tried. This matches the orchestrator's instruction: "FIRST the re-listen... if it holds, seal the tail-side variant".

**<high> None**
1.  **Held Word Placement:** `held_word` correctly identifies the word causing the hold by comparing the `as_spoken` text against the approved text using `attest.class_84`. It finds the *first* difference outside the allowed class. The variant ends at the last sentence boundary *before* this word index. This ensures the held word is excluded from the variant.
2.  **Duplicate Prevention:** `for_pool` checks if the variant's `moment_id` already exists in the pool (`have` set) and skips it if so. This prevents double-counting or conflicting entries.
3.  **Trigger Validity:** Variants are only generated if a specific trigger exists: a Lock Pre-check HOLD, a Ruling 73 cut failure, or a duration ceiling violation. No variant is created "for no reason."

**<medium> 1**
**File:** `pipeline/tail_variant.py`, lines 190-194
**Issue:** Potential off-by-one or boundary ambiguity in `for_pool` when calculating the variant end for a held word.
**Sequence:**
1.  `held_word` returns index `i` of the held word in `src.tokens`.
2.  `for_pool` calculates `ks = [k for k in range(k0, k1) if i is not None and src.sentences[k][1] < i]`.
3.  `src.sentences[k][1]` is the index of the *last* word of sentence `k`.
4.  The condition `src.sentences[k][1] < i` ensures the sentence ends *before* the held word starts.
5.  The variant is created with `k = ks[-1]`.
6.  **Risk:** If the held word `i` is the *first* word of a sentence, `src.sentences[k][1]` (last word of previous sentence) will be `< i`. This is correct. However, if the held word is *inside* a sentence, the variant ends at the *previous* sentence boundary. This is also correct per Ruling 104 ("ends at an earlier sentence boundary").
7.  **Subtle Risk:** The code assumes `src.sentences` is a list of `(start_idx, end_idx)` tuples. If `src.sentences[k][1]` is inclusive (which is standard for word indices in this codebase, as seen in `E.Span` usage), the logic holds. If `src.sentences` were exclusive, the variant might include the held word. Given `E.Span(src, k0, k)` uses `k` as the exclusive end of the sentence range (standard Python slicing), and `src.sentences[k][1]` is the last word index, the comparison `last_word_idx < held_word_idx` is the correct way to ensure the held word is *not* in the variant.
    *   *Verification:* `E.Span(src, k0, k)` creates a span from word `src.sentences[k0][0]` to `src.sentences[k-1][1]` (if `k` is the count of sentences) or similar. Wait, `E.Span(src, k0, k)` in `variant()` takes `k` as the *sentence index* to end at.
    *   In `for_pool`, `ks` contains sentence indices `k` such that the sentence ends before the held word.
    *   `variant(m, src, k, ...)` creates `E.Span(src, k0, k)`.
    *   If `E.Span` interprets the second argument as the *exclusive* sentence index (i.e., sentences `k0` to `k-1`), then ending at `k` means the last sentence included is `k-1`.
    *   The condition `src.sentences[k][1] < i` checks if sentence `k` ends before the held word.
    *   If we pick `k = ks[-1]`, and `variant` uses `E.Span(src, k0, k)`, we need to ensure `E.Span` includes sentence `k-1` but not `k`.
    *   Looking at `test_ruling_104.py` line 345: `v = TV.variant(m, src, 2, CTX, "a held word")`. `m` has sentences `[0, 4]`. `v` has sentences `[0, 2]`. The text is `SENTENCES[:3]` (indices 0, 1, 2).
    *   This implies `E.Span(src, 0, 2)` includes sentences 0 and 1? No, `SENTENCES[:3]` is 3 sentences.
    *   Let's re-read `test_ruling_104.py` line 344: `self.assertEqual(v["text"], " ".join(SENTENCES[:3]))`.
    *   `SENTENCES` has 5 items. `[:3]` is items 0, 1, 2.
    *   `TV.variant(m, src, 2, ...)` results in sentences `[0, 2]`.
    *   This suggests `E.Span(src, k0, k)` includes sentences `k0` through `k-1`? No, if it includes 0, 1, 2, the end index must be 3.
    *   Wait, the test says `v["sentences"]` is `[0, 2]`. And the text is `SENTENCES[:3]`.
    *   This implies `E.Span` with end `2` includes sentence index 2?
    *   Let's check `eligibility.Span` definition (not in diff, but standard). Usually `Span(src, start, end)` is inclusive or exclusive.
    *   If `v["sentences"]` is `[0, 2]` and text is `SENTENCES[0:3]`, then the span includes sentence 0, 1, and 2.
    *   Therefore, `E.Span(src, 0, 2)` likely means "from sentence 0 to sentence 2 inclusive".
    *   Back to `for_pool`: `ks = [k for k in range(k0, k1) if src.sentences[k][1] < i]`.
    *   If `i` is the held word, and we want the variant to end *before* `i`, we need the last sentence `k` such that its last word is before `i`.
    *   If `variant` uses `E.Span(src, k0, k)` and that includes sentence `k`, then we must ensure sentence `k` does *not* contain the held word.
    *   The condition `src.sentences[k][1] < i` ensures the last word of sentence `k` is before the held word `i`. Thus, sentence `k` does not contain `i`.
    *   So the variant ends at sentence `k`, which is safe.
    *   **Conclusion:** The logic is correct. The medium risk is resolved by the test evidence.

**<low> 1**
**File:** `pipeline/tail_variant.py`, line 120
**Issue:** `glob` pattern matching for hold files.
**Sequence:**
1.  `glob.glob(os.path.join(results_dir, f"{m['video_id']}.{start:.3f}-{end:.3f}.*.json"))`
2.  If `start` or `end` have floating point precision issues, the filename might not match.
3.  However, `start` and `end` are rounded to 3 decimal places in `holds()` (line 118) and in the filename generation in `put()` (test line 335).
4.  The integrator writes files with specific precision. If the integrator uses higher precision, the glob might miss.
5.  **Mitigation:** The code uses `round(float(m["start"]), 3)`. This is a standard convention in this codebase (seen in `spotlight.py` and tests). It is unlikely to be a bug, but worth noting if the integrator changes precision.

### SHIP: yes

The change correctly implements Ruling 104.
1.  **Variants are new spans** that face all gates.
2.  **Variants are not snapped** outward.
3.  **Parents are tried first**.
4.  **Held words are excluded** from variants.
5.  **Provenance is recorded** in the pin.

The code is robust, fail-closed, and adheres to the governing laws (Sentence Law, Selection Lock, etc.). The tests cover the critical paths, including the specific Blockware case.