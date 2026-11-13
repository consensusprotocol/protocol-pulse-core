# qwen3.8-27b (qwen/qwen3.8-27b) 46 s finish=stop usage in 20385 / out 2649 usd~0.101 (upper-bound price)

I have reviewed the diff for `pipeline/package.py` and `tests/package/test_medley.py` against the governing laws and the specific orders (Ruling 66 Amended, 17:20).

### P0 Findings (Blockers)

**1. `takeaway_refusal` fails closed on missing context data (M12 Violation)**
*   **File:** `pipeline/package.py` (in `takeaway_refusal`)
*   **Line:** ~131-136 (logic for `STRONGER`/`NOT_ENTAILED`)
*   **Scenario:** If a `STRONGER` violation occurs but the `cx` (context integrity) object is `None` or does not contain the specific segment key (e.g., due to a partial failure or a different gate ordering), `cseg` will be `{}`. `cseg[v["segment"]]` will raise a `KeyError` or return `None`.
    *   If `cseg[v["segment"]]` is `None`, `(cseg[v["segment"]] or {}).get("C")` handles it.
    *   However, if `v["segment"]` is not in `cseg` at all, `cseg[v["segment"]]` raises `KeyError`.
    *   **Impact:** An unhandled exception in `takeaway_refusal` propagates up to `build`. While `build` might catch it, this prevents the "alone" determination. More critically, if `cx` is passed as `None` (which happens in the first call at line 330: `takeaway_refusal(fields, cheap)` where `cx` defaults to `None`), and a `STRONGER` violation is present in `cheap` (which is unlikely as `STRONGER` is a paid gate, but `NOT_ENTAILED` might be deterministic?), the code attempts to access `cseg` which is `{}`.
    *   **Correction:** `STRONGER` and `NOT_ENTAILED` are typically paid gates (context integrity). In the first call (line 330), only `cheap` violations are passed. `cheap` contains deterministic checks. If `STRONGER` is not in `cheap`, this path isn't hit. However, in the second call (line 355), `cx` is passed. If `cx` is `None` (e.g., if `paid_gates` failed before returning `cx`?), `cseg` is `{}`.
    *   **Actual Risk:** The code `cseg = (cx or {}).get("segments") or {}`. If `v["segment"]` is not in `cseg`, `cseg[v["segment"]]` raises `KeyError`. This violates M12 (Fail Closed) because it crashes the build loop instead of gracefully determining "not alone".
    *   **Fix:** Use `cseg.get(v["segment"])` instead of `cseg[v["segment"]]`.

**2. `merge_fid` precondition violation risk**
*   **File:** `pipeline/package.py` (in `build` loop)
*   **Line:** ~342-344
*   **Scenario:** `takeaway_alone_gates` is called when `lone` is True and `last_fid` is not None. It merges `last_fid` (the verdict from the *previous* full write) with the new takeaway verdict.
    *   The law states: "the kept lines' verdicts are only merged when that write's lines were judged".
    *   `last_fid` is set at line 357: `last_fid, last_rw65 = fid, bool(att.get("rewrite"))`. This `fid` is the result of `paid_gates` for the *current* full write.
    *   If the current full write failed on the takeaway *alone*, `fid` contains violations for the takeaway. The other lines (title, caption) passed.
    *   `takeaway_alone_gates` runs `VF.check` on the *new* takeaway and `CI.check_contexts` on the *whole* package.
    *   It returns `merge_fid(fid, "takeaway", one)`.
    *   **Issue:** `merge_fid` assumes `fid` is a valid verdict object. If `fid` was from a write that *didn't* reach paid gates (e.g., failed cheap checks), `last_fid` would be `None` (initialized at line 234, only set at 357 after paid gates). So `last_fid` is only non-None if the previous write reached paid gates.
    *   **However:** `takeaway_alone_gates` re-runs `CI.check_contexts` on the *new* package. The `fid` being merged is the *old* fidelity verdict. The new `one` is the new fidelity verdict for the takeaway.
    *   **Critical Check:** Does `merge_fid` correctly handle the case where the *old* `fid` had a violation on the takeaway, and the *new* `one` passes? Yes, that's the point.
    *   **Potential Bug:** `takeaway_alone_gates` does *not* re-run the fidelity check on the *kept* lines (title, caption). It relies on `last_fid` for them. This is correct *if* `last_fid` is valid.
    *   **But:** `last_fid` is the verdict from the *last full write*. If the last full write failed on the takeaway, `last_fid` contains the takeaway violation. The kept lines passed. Merging `last_fid` (with takeaway violation) with `one` (new takeaway pass) should result in a pass for the takeaway and keep the pass for the others.
    *   **Law Check:** "No gate accepts more than before". The kept lines are *not* re-judged. They are trusted from the previous write. This is allowed by Ruling 66 ("passing lines kept as gated").
    *   **Verdict:** This logic seems sound, *provided* `last_fid` is indeed the verdict from a write where the kept lines passed. Since `takeaway_refusal` returned `alone=True`, it implies the only failures were on the takeaway (or global runtime). Thus, the kept lines *did* pass in `last_fid`.

**3. `avoid_model` logic in `write_line`**
*   **File:** `pipeline/package.py` (in `write_line`)
*   **Line:** ~87-88
*   **Scenario:** `avoid_model` is passed as a set `{by}`. `router.call` accepts `avoid_model`.
*   **Check:** Does `router.call` support `avoid_model`? The diff shows `**({"avoid_model": avoid_model} if avoid_model else {})`.
*   **Risk:** If `router.call` does not accept `avoid_model`, this raises `TypeError`. The background says "Writers are two Heimdall models... avoid_vendor is used". It does not explicitly confirm `avoid_model` support in the router interface.
*   **Assumption:** The test `test_the_second_takeaway_alone_is_on_the_other_writer_model` mocks `router.call` and checks `k.get("avoid_model")`. This implies the *test* expects it, but does not prove the *real* router supports it.
*   **Finding:** **P1** - Verify `router.call` signature supports `avoid_model`. If not, this is a P0 crash. Given the "17:20" order explicitly asks for "second attempt on the other writer model", and the code implements it, it's likely supported, but the diff doesn't show the router change.

### P1 Findings (Major)

**4. `TAKEAWAY_SAID` injection into `WRITE_LY`**
*   **File:** `pipeline/package.py`
*   **Line:** ~20, 30
*   **Scenario:** `TAKEAWAY_SAID` is added to the `WRITE_LY` prompt.
*   **Law Check:** "The writer, not the judges, is what changed".
*   **Verdict:** Correct. This is a prompt change for the writer.

**5. `LINE_ONLY_WRITES` for Title**
*   **File:** `pipeline/package.py` (in `rewrite_alone`)
*   **Line:** ~189
*   **Scenario:** `for k in range(LINE_ONLY_WRITES if slot == "title" else 1):`
*   **Law Check:** "17:20: YES, the second attempt applies to a failed title as well... then hold as ruling 65 says."
*   **Verdict:** Correct. Title gets 2 writes. Caption gets 1.

**6. `takeaway_refusal` "Alone" Logic**
*   **File:** `pipeline/package.py`
*   **Line:** ~127-141
*   **Scenario:** `alone` starts as `True` if there are violations and takeaway text exists. It becomes `False` if *any* violation is not "own".
*   **Law Check:** "alone: every failure of the write is such an entry... so the takeaway alone may be written again."
*   **Verdict:** Correct. If a caption fails, `alone` becomes `False`, and no takeaway-alone write is triggered.

**7. `merge_fid` usage in `takeaway_alone_gates`**
*   **File:** `pipeline/package.py`
*   **Line:** ~153
*   **Scenario:** `return merge_fid(fid, "takeaway", one), cx`
*   **Law Check:** "the kept lines' verdicts are only merged when that write's lines were judged".
*   **Verdict:** `fid` is `last_fid`, which is the verdict from the previous full write. The kept lines were judged in that write. The new `one` is the verdict for the new takeaway. This is correct.

### P2 Findings (Minor)

**8. `rec["tries"]` accumulation**
*   **File:** `pipeline/package.py` (in `rewrite_alone`)
*   **Line:** ~217
*   **Scenario:** `rec.setdefault("tries", []).append(...)`
*   **Verdict:** Correctly tracks attempts for the title.

**9. `TAKEAWAY_WHY` dictionary**
*   **File:** `pipeline/package.py`
*   **Line:** ~52-55
*   **Scenario:** Defines reasons for takeaway refusal.
*   **Verdict:** Correct.

**10. `test_which_failures_are_the_takeaways_own`**
*   **File:** `tests/package/test_medley.py`
*   **Line:** ~546-562
*   **Scenario:** Tests `takeaway_refusal` logic.
*   **Verdict:** Good coverage of edge cases (STRONGER, RUNTIME, LY_SHAPE, etc.).

### SHIP: No

**Reasons:**
1.  **P0 Crash Risk:** `takeaway_refusal` uses `cseg[v["segment"]]` which will raise `KeyError` if the segment is not in the context integrity results. This violates M12 (Fail Closed) and will crash the build loop.
2.  **P1 Interface Risk:** `router.call` is invoked with `avoid_model`. The diff does not show that `router.call` supports this keyword argument. If it doesn't, the second write attempt will crash with `TypeError`.

**Conditions for Ship:**
1.  Change `cseg[v["segment"]]` to `cseg.get(v["segment"])` in `takeaway_refusal`.
2.  Verify that `router.call` in the codebase accepts `avoid_model`. If not, update the router or use a different mechanism to switch models.
3.  Ensure `last_fid` is never `None` when `takeaway_alone_gates` is called (currently guarded by `if lone and last_fid is not None`, so this is safe).