# qwen3.8-27b (qwen/qwen3.8-27b) 131 s finish=stop usage in 24567 / out 3677 usd~0.129 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (FINAL)
# Feature: pp-selectid-2315

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (and the other models) focused heavily on the `delivered_ids` omission (K7) and the `since` default ambiguity. The consensus correctly resolved K7 by proving that `package.usable`'s overlap check is stricter than an ID check and is the correct carrier for L-p.

However, the other models (specifically GLM-5.3-Flash in C1 P1-2 and Qwen3.8-27B in C3) correctly identified that the **word record selection logic** was fragile. In Cycle 1, I noted the glob/sort issue but did not fully trace the consequence of the *fixed* implementation. The fix in C4 (using a static tuple `WORD_RECORDS` instead of a glob) is correct, but I need to verify if the *interaction* between `word_source` and `build_inputs` handles the "fallback" case correctly in the report.

More critically, **nobody in Cycle 1 fully verified the `words_off_segments` logic against the `tol` parameter.** The code uses `tol=0.001` (1ms). The consensus states "all 66 word records agree to the ms." If the store writes times with higher precision (e.g., microseconds) but the segments are rounded to ms, this check passes. But if the *words* have higher precision than the *segments*, does `words_off_segments` fail? The code compares `ws[first]["start"]` (word time) to `sg["start"]` (segment time). If the store writes words with microsecond precision and segments with millisecond precision, `abs(word_start - seg_start)` could be > 0.001. The consensus says "measured... agree to the ms," implying the store normalizes. I must verify if this is a latent P1 if the store changes precision.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **K7 (delivered_ids):** **Agree.** The driver passes `delivered` spans to `PK.build`, which passes them to `PK.usable`. `PK.usable` checks for overlap. The adapter's `delivered_ids` are for *ledger moment IDs* (24h window), which are not present in the pins. The overlap check is the correct L-p enforcement. The test `test_a_moment_overlapping_any_delivered_span_is_out_whatever_the_pins_age` verifies this.
*   **K8 (malformed rows):** **Agree.** `build_inputs` now checks `isinstance(r, dict)` and required keys. It counts them in `report["malformed"]` with a unique key. The test `test_a_row_without_an_id_is_counted_never_a_crash` verifies this.
*   **SNAP_GUARD:** **Agree.** The regex now includes `hardly|scarcely|barely|rarely|seldom` and handles typographic apostrophes via `APOSTROPHES` mapping before the guard check. The tests `test_a_snap_never_adds_a_near_negation` and `test_a_typographic_apostrophe_does_not_hide_a_negation` verify this.
*   **Word Record Order:** **Agree.** `WORD_RECORDS` is a static tuple `("transcript.whisper_words_punct.json", "transcript.whisper_words.json")`. This is a total order, not filesystem-dependent. The test `test_only_the_stores_two_word_record_slots_are_read_in_a_fixed_order` verifies that a renamed file is ignored.
*   **`since` Default:** **Partially Agree.** The default is `newest approved_at`. The ruling says "since the last delivered video." Using `approved_at` is a reasonable proxy for "when the video was finalized/delivered." The 72h window in the adapter catches anything published recently. The risk of "reading too few" is low because the adapter's contract includes "published inside the 72h window." The risk of "reading too many" is mitigated by the `delivered` overlap check in `PK.usable`. I downgrade this from P1 to P2 (ambiguity, not defect).

## 3. NEW FINDINGS FROM THIS REVIEW

### P1: `words_off_segments` tolerance may be too tight for mixed-precision stores
**File:** `pipeline/ledger_build.py:102-130`
**Issue:** The function `words_off_segments` checks if `abs(word_start - seg_start) > tol` where `tol=0.001` (1ms). The consensus states the store's records "agree to the ms." However, if the store writes `words` with microsecond precision (e.g., `1.234567`) and `segments` with millisecond precision (e.g., `1.234`), the difference is `0.000567`, which is < 0.001, so it passes. But if the store writes `words` with ms precision and `segments` with *second* precision (unlikely, but possible in a bug), it would fail. More importantly, if the store writes `words` with *higher* precision than `segments` (e.g., words at 100us, segments at 1ms), the difference could be up to 0.0005s, which is < 0.001. So it passes.
**Wait:** The check is `abs(float(ws[first]["start"]) - float(sg["start"])) > tol`. If `ws` is 1.2345 and `sg` is 1.234, diff is 0.0005 < 0.001. Pass. If `ws` is 1.2349 and `sg` is 1.234, diff is 0.0009 < 0.001. Pass. If `ws` is 1.2350 and `sg` is 1.234, diff is 0.0010. `> 0.001` is False. Pass. If `ws` is 1.2351 and `sg` is 1.234, diff is 0.0011 > 0.001. Fail.
**Scenario:** A store update changes word precision to 100us. A segment boundary is at 1.2345s. The first word starts at 1.2345s. The segment start is rounded to 1.234s (if the store rounds segments to ms). Diff = 0.0005s. Pass.
**Real Risk:** If the store *does not* round segments to ms, but words are at ms, and there is a 1.1ms drift due to clock skew between the word-pass and segment-pass, this check fails. The consensus says "measured... agree to the ms," implying the store is consistent. I will mark this as **P2** (latent, depends on store behavior not visible in diff).

### P1: `reanchor` uses `src.sentences` but `SL.anchor` returns token indices
**File:** `pipeline/ledger_build.py:186-187`
**Code:**
```python
k0 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i0 <= b), None)
k1 = next((k for k, (a, b) in enumerate(src.sentences) if a <= i1 <= b), None)
```
**Issue:** `src.sentences` is a list of `(start_token_idx, end_token_idx)` tuples. `i0` and `i1` are token indices returned by `SL.anchor`. This logic finds the sentence *containing* the start and end tokens. This is correct.
**However:** What if `i0` is exactly at the boundary between two sentences? E.g., sentence 0 is tokens 0-4, sentence 1 is tokens 5-9. If `i0=5`, `a=5, b=9` for sentence 1. `5 <= 5 <= 9` is True. `k0=1`. Correct.
**Edge Case:** What if `i0` is *before* the first token of the first sentence? `a=0`. `0 <= i0 <= b`. If `i0=0`, `k0=0`. Correct.
**Edge Case:** What if `i0` is *after* the last token of the last sentence? `k0` becomes `None`. The code handles this: `if k0 is None or k1 is None: return None, "..."`. Correct.

### P1: `build_inputs` does not check if `src` is `None` before calling `reanchor`
**File:** `pipeline/ledger_build.py:233-244`
**Code:**
```python
src, path, passed_over = word_source(rs[0], ctx, store)
if src is None:
    # ... count no_word_record ...
    continue
# ...
for i, r in irs:
    sp, info = reanchor(r, src)
```
**Issue:** This is correct. If `src` is `None`, it continues to the next video. `reanchor` is only called if `src` is not `None`.

### P1: `proof_ledger.py` does not pass `delivered_ids` to `LB.rows`
**File:** `tests/package/proof_ledger.py:386`
**Code:**
```python
rows, rep = LB.rows(since, now, horizon_h=a.hours)
```
**Issue:** `LB.rows` has a parameter `delivered_ids=()`. The driver does not pass any `delivered_ids`. This is consistent with the K7 resolution: the adapter's `delivered_ids` are for ledger moment IDs, which are not available. The L-p check is done later in `PK.usable`. This is **correct** per the consensus.

### P1: `test_ledger_build.py` does not test `LB.rows` with `delivered_ids`
**File:** `tests/package/test_ledger_build.py:685-715`
**Issue:** The `TestAdapter` class mocks `subprocess.run` and tests `LB.rows`. It does not test that `delivered_ids` are passed to the subprocess. However, since the driver doesn't pass them, this is not a defect.

### P1: `word_source` does not check if `rec` is a dict
**File:** `pipeline/ledger_build.py:148-153`
**Code:**
```python
with open(p) as f:
    rec = json.load(f)
# ...
if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
```
**Issue:** If `rec` is not a dict (e.g., a list or string), `rec.get` will raise `AttributeError`. This is not caught.
**Scenario:** A corrupt word record file contains `[1, 2, 3]`. `json.load` returns a list. `rec.get` raises `AttributeError`. The build crashes.
**Fix:** Wrap in `try/except (AttributeError, TypeError)` or check `isinstance(rec, dict)`.
**Severity:** P1. A corrupt file should be counted as `passed_over`, not crash the build.

### P1: `words_off_segments` does not check if `sg` is a dict
**File:** `pipeline/ledger_build.py:113-114`
**Code:**
```python
for i, sg in enumerate(rec.get("segments") or []):
    need, got, first = "".join(str(sg.get("text") or "").split()), "", k
```
**Issue:** If `sg` is not a dict, `sg.get` raises `AttributeError`.
**Scenario:** A corrupt word record has `segments: [1, 2, 3]`. `sg.get` raises `AttributeError`.
**Severity:** P1.

### P1: `reanchor` does not check if `src.tokens` is a list
**File:** `pipeline/ledger_build.py:178`
**Code:**
```python
hit = SL.anchor(src.tokens, row.get("text") or "", ...)
```
**Issue:** If `src.tokens` is not a list, `SL.anchor` may crash. However, `src` is created by `E.Source`, which likely validates `tokens`. Unverifiable from diff.

### P1: `build_inputs` does not check if `r["scores"]` is a dict
**File:** `pipeline/ledger_build.py:252`
**Code:**
```python
m = {"scores": dict(r["scores"]), ...}
```
**Issue:** If `r["scores"]` is not a dict, `dict(r["scores"])` may crash or produce unexpected results.
**Scenario:** A ledger row has `scores: [1, 2, 3]`. `dict([1, 2, 3])` raises `ValueError`.
**Severity:** P1.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `ledger_build.py` | P1 (glob/sort, snap guard) | P1 (corrupt file handling) | The glob/sort and snap guard are fixed. New P1s found in error handling for corrupt JSON. |
| `proof_ledger.py` | P1 (delivered_ids, since) | P2 (since ambiguity) | K7 resolved. `since` default is defensible. |
| `test_ledger_build.py` | P2 (missing tests) | P2 (missing corrupt file tests) | Tests for K7, K8, snap guard are present. Missing tests for corrupt JSON. |

## 5. FINAL PRIORITY LIST

**P1 HIGH**
1.  **`pipeline/ledger_build.py:148-153`**: `word_source` does not handle non-dict `rec`. A corrupt word record file (e.g., a list) will crash the build with `AttributeError`. **Fix:** Check `isinstance(rec, dict)` and count as `passed_over` if not.
2.  **`pipeline/ledger_build.py:113-114`**: `words_off_segments` does not handle non-dict `sg`. A corrupt `segments` list will crash the build. **Fix:** Check `isinstance(sg, dict)` and return a `why` string if not.
3.  **`pipeline/ledger_build.py:252`**: `build_inputs` does not handle non-dict `r["scores"]`. A ledger row with a non-dict `scores` will crash the build. **Fix:** Check `isinstance(r.get("scores"), dict)` and count as `malformed` if not.

**P2 MEDIUM**
1.  **`pipeline/ledger_build.py:102`**: `words_off_segments` tolerance `tol=0.001` may be too tight if the store uses mixed precision. **Fix:** Increase `tol` to `0.01` (10ms) or document the store's precision guarantee.
2.  **`tests/package/proof_ledger.py:304`**: `since` default is `approved_at`. This is a reasonable proxy for "last delivered video," but the ruling's wording is ambiguous. **Fix:** Document this choice in the docstring.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Add `isinstance` checks for `rec`, `sg`, and `r["scores"]` in `ledger_build.py` to prevent crashes from corrupt or malformed JSON, ensuring the build fails closed (counts the error) rather than crashing.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Fix the P1s in `ledger_build.py` to handle non-dict `rec`, `sg`, and `r["scores"]` gracefully (count as `passed_over` or `malformed`, do not crash).
2.  Add tests for corrupt word record files (non-dict `rec`, non-dict `sg`) to `test_ledger_build.py`.
3.  Document the `since` default choice (`approved_at`) in the `proof_ledger.py` docstring.