# qwen3.8-27b (qwen/qwen3.8-27b) 75 s finish=stop usage in 14386 / out 2548 usd~0.081 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_1835

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I identified the `IndexError` risk in `spot_place` (H6) and the silent drop of directives without `why` (H1). I missed the following:

1.  **The "Silent Parent Drop" on Directive Mismatch (Grok's Key Finding):** In Cycle 1, I analyzed the `for_pool` logic but failed to trace the control flow when `directive_variant` returns `None` (no boundary match). I assumed the `continue` statement at the end of the directive block (which was present in the *original* pre-fix code or implied by the "in its place" logic) would skip the parent's normal trigger checks. Grok correctly identified that if a directive is present but invalid (e.g., `ends` doesn't match any boundary), the parent was being silently excluded from the pool without its normal hold/ceiling triggers running. This violated "the rules stand." The fix in the current diff (lines 96-97) addresses this by *not* continuing, allowing the normal triggers to run. I missed this specific control-flow defect in the pre-fix state and its resolution.
2.  **The `IndexError` in `spot_place` (My H6, but I under-weighted it):** I flagged it as a "crash" but didn't explicitly verify if it was caught. Looking at `proof_ledger.py:174`, `pk["segments"][0]` is accessed *outside* the `try` block that wraps the pin logic in `main` (lines 192-213). Wait, looking closer at the diff: `spot_place` is called at line 198. The `try` block starts at line 192. `spot_place` is *inside* the try. However, `spot_place` itself does not have a try/except for `IndexError`. If `pk["segments"]` is empty, `spot_place` raises `IndexError`. The `except` clause at line 213 catches `(package_pin.PinRefused, ValueError, OSError)`. `IndexError` is **not** caught. This would crash the build. I flagged this in Cycle 1 (H6) but the consensus marked it as "Taken" (fixed) or "Documented"? The consensus says "glm (1), a crash... A non-list value now gives no directive". It does *not* say the `IndexError` in `spot_place` was fixed. Let me re-read the diff.
    *   `spot_place` (line 168-176) accesses `pk["segments"][0]`.
    *   `main` (line 198) calls `spot_place`.
    *   `main`'s `except` (line 213) does NOT catch `IndexError`.
    *   **This is still a live bug.** If a package has no segments, the build crashes with an unhandled `IndexError` instead of failing closed with a note.

3.  **Qwen's L-k "Critical" was a False Positive:** Qwen flagged `E.spoken` as a violation of L-k (One Canonical Form). I agree with the consensus that this is not a violation because `E.spoken` is the canonical read path for ASR tokens, and `C.canon_tokens` is applied to the result. The comparison is canonical. I missed the nuance that `E.spoken` is *part* of the canonical pipeline, not an ad-hoc normalizer.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok (Parent Drop on Bad Directive):** **Agree.** This was the most significant logic error in the pre-fix code. The current diff fixes it by removing the `continue` on directive failure, allowing normal triggers to run.
*   **Qwen (L-k Critical):** **Disagree.** `E.spoken` is the standard way to get text from tokens in this codebase. It is not an ad-hoc normalizer. The use of `C.canon_tokens` on the result satisfies L-k.
*   **Qwen (L-l High):** **Disagree.** `directives()` is a builder input, not a model reply. L-l applies to model replies. However, the fail-closed validation added (20-hex parent, story id format) is good practice and addresses the spirit of M12.
*   **GLM (IndexError in spot_place):** **Agree.** This is a real crash risk. The `except` block in `main` does not catch `IndexError`.
*   **GLM (Silent Drop of `why`):** **Agree.** The `directives()` function now requires `by` to be non-blank, but `why` is still optional. This is consistent with the builder's writer, so it's a minor consistency wart, not a break.

## 3. NEW FINDINGS FROM THIS REVIEW

**<high> H1 — `proof_ledger.py:174` (spot_place): Unhandled `IndexError` on empty segments.**
*   **File:** `tests/package/proof_ledger.py`
*   **Issue:** `spot_place` accesses `pk["segments"][0]["channel_id"]`. If `pk["segments"]` is an empty list, this raises `IndexError`.
*   **Concrete Sequence:**
    1.  A package is created with no segments (malformed or edge case).
    2.  `main` calls `spot_place(sp["package"], again, now)` at line 198.
    3.  `spot_place` raises `IndexError`.
    4.  The `except` block at line 213 catches `(package_pin.PinRefused, ValueError, OSError)`. `IndexError` is not caught.
    5.  The build crashes with a traceback instead of failing closed with a note.
*   **Fix:** Add `IndexError` to the `except` tuple in `main`, or add a check in `spot_place` for empty segments.

**<medium> H2 — `tail_variant.py:66` (directive_variant): Potential `IndexError` if `src.sentences` is empty.**
*   **File:** `pipeline/tail_variant.py`
*   **Issue:** `directive_variant` accesses `src.sentences[k0][0]` and `src.sentences[k][1]`. If `src.sentences` is empty, this raises `IndexError`.
*   **Concrete Sequence:**
    1.  A moment `m` has `sentences` defined, but the source `src` has no sentences (malformed source).
    2.  `directive_variant` is called.
    3.  `src.sentences[k0][0]` raises `IndexError`.
    4.  This is not caught in `for_pool` (the `try` block at line 90-94 only catches `KeyError` from `CI.source_for`).
    5.  The build crashes.
*   **Fix:** Add a check for `src.sentences` being non-empty in `directive_variant` or `for_pool`.

**<medium> H3 — `proof_ledger.py:162-165` (directives): `re.fullmatch` on `parent` is strict but `alternative_to` uses `re.match`.**
*   **File:** `tests/package/proof_ledger.py`
*   **Issue:** `parent` is validated with `re.fullmatch(r"[0-9a-f]{20}", d["parent"])`, which is correct. `alternative_to` is validated with `story.match(d["alternative_to"])`, where `story = re.compile(r"^moments-[A-Za-z0-9_]+-[0-9a-f]{8}$")`. `re.match` anchors at the start but not the end. If `alternative_to` is `"moments-x-3f481f5aEXTRA"`, `re.match` will succeed because it matches the prefix.
*   **Concrete Sequence:**
    1.  Builder writes `alternative_to: "moments-x-3f481f5aEXTRA"`.
    2.  `directives()` accepts it because `re.match` succeeds.
    3.  `day_taken` compares `r.get("story_id") == alternative_to`. The real story id is `"moments-x-3f481f5a"`, so the comparison fails.
    4.  The variant is refused at the pool (fail-closed).
*   **Impact:** Fail-closed, but a malformed directive is accepted by the reader and then silently behaves as no-alternative. Silent, fail-closed.
*   **Fix:** Use `re.fullmatch` for `alternative_to` as well.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| `spotlight.py` | 8/10 | 9/10 | `day_taken` is clean and well-tested. The `IndexError` in `spot_place` is in `proof_ledger.py`, not `spotlight.py`. |
| `tail_variant.py` | 7/10 | 8/10 | The "parent drop" bug is fixed. The `IndexError` on empty `src.sentences` is a new finding but low probability. |
| `proof_ledger.py` | 6/10 | 7/10 | The `IndexError` in `spot_place` is a real crash risk. The `re.match` vs `re.fullmatch` inconsistency is a minor wart. |
| `test_ruling_104.py` | 9/10 | 9/10 | Tests are comprehensive and cover the key edge cases. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL**
*   None.

**P1 HIGH**
1.  **`proof_ledger.py:174` (spot_place):** Add `IndexError` to the `except` tuple in `main` (line 213) or add a check for empty `pk["segments"]` in `spot_place`. This prevents a crash on malformed packages.

**P2 MEDIUM**
1.  **`tail_variant.py:66` (directive_variant):** Add a check for `src.sentences` being non-empty to prevent `IndexError` on malformed sources.
2.  **`proof_ledger.py:164` (directives):** Use `re.fullmatch` for `alternative_to` to prevent accepting malformed story ids that fail-closed but are silently ignored.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add `IndexError` to the `except` tuple in `proof_ledger.py:213`** to ensure that malformed packages (empty segments) fail closed with a note instead of crashing the build.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix the `IndexError` in `spot_place` by adding `IndexError` to the `except` tuple in `main` or by checking for empty segments in `spot_place`.
2.  (Optional but recommended) Use `re.fullmatch` for `alternative_to` in `directives()` to prevent accepting malformed story ids.