# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 12083 / out 3051 usd~0.082 (upper-bound price)

I have reviewed the diff against the governing laws and the specific attack vectors. Here are the findings.

### Findings

**<critical> L-k Violation: Ad-hoc Normalization in `directive_variant`**
*   **File:** `pipeline/tail_variant.py` (lines 62-67 in diff)
*   **Issue:** The function `directive_variant` uses `C.canon_tokens` to normalize the directive's `ends` string and the source tokens. However, it performs a raw string slice `src.tokens[src.sentences[k0][0]:src.sentences[k][1] + 1]` and then passes it to `E.spoken` before `C.canon_tokens`.
*   **Law Violation:** **L-k (ONE CANONICAL FORM)** states: *"every text comparison in the pipeline uses pipeline/canon.py... TestSites fails any ad-hoc normaliser outside canon.py."*
*   **Concrete Sequence:** If `E.spoken` performs any transformation (e.g., expanding abbreviations, handling punctuation) that is not idempotent with `C.canon_tokens`, or if the directive's `ends` string contains characters that `C.canon_tokens` handles differently than the processed source tokens, the comparison `got[-len(want):] == want` may fail to match a valid boundary or, worse, match an invalid one if the normalization is inconsistent. More critically, the law requires that *all* text comparisons use `canon.py`. While `canon_tokens` is used, the intermediate step `E.spoken` is an external transformation. If `E.spoken` is not part of the canonical read path defined by L-k (which specifies `transcript_store.read_text` and `story_semantics._norm`), this is a violation. The diff does not show `E.spoken` being routed through `canon.py`'s specific entity/token joining rules (L-h). If `E.spoken` returns raw ASR tokens with entities like `&amp;` or split numbers like `$81 ,000`, `C.canon_tokens` might not fix them if it expects pre-processed text, or if `E.spoken` introduces its own normalization that conflicts with `canon.py`.
*   **Impact:** A directive might be rejected because the "ends" string doesn't match the canonically normalized source, or a wrong boundary might be accepted if the normalization is flawed.

**<high> L-l Violation: Directive Fields Not Validated Against Enumerated Values/Ranges**
*   **File:** `tests/package/proof_ledger.py` (lines 122-132 in diff)
*   **Issue:** The `directives` function reads the JSON file and filters rows based on type checks (`isinstance(d.get("parent"), str)`, etc.). However, it does not validate the *content* of these fields against the rules of **L-l (A MODEL REPLY COUNTS ONLY WHOLE)** or the specific constraints of Ruling 104.
*   **Law Violation:** **L-l** states: *"a local-model reply feeds a decision only when every field that decision reads is present, of its exact type, inside its enumerated values and ranges... anything else is a failed call."* While this is a builder-written file, not a model reply, the principle of **M12 (FAIL CLOSED)** and **LAW 20** applies. The code accepts any string for `ends`, `alternative_to`, and `by`.
*   **Concrete Sequence:**
    1.  Builder writes `RULING_104_DIRECTIVES.json` with `{"parent": "valid_id", "ends": "garbage text that matches no boundary", "alternative_to": "invalid_story_id", "by": "orchestrator", "why": "test"}`.
    2.  `directives()` returns this row because all types are correct.
    3.  `directive_variant` is called. It iterates through boundaries. If no boundary matches `ends`, it returns `(None, "no earlier sentence boundary...")`. This is safe.
    4.  **However**, if `ends` *does* match a boundary, but `alternative_to` points to a story that does not exist or is not the one the channel is currently holding, the `day_taken` logic in `spotlight.py` (line 13-14) checks `r.get("story_id") == alternative_to`. If `alternative_to` is wrong, `day_taken` returns `True` (channel is taken), and the variant is rejected in the pool. This is safe.
    5.  **The Risk:** What if `alternative_to` is correct, but the directive is for a *different* parent than the one currently holding the spotlight? The `for_pool` function (line 85) checks `if mid in (directives or {})`. It only applies the directive to the specific parent ID. This seems safe.
    6.  **Re-evaluating L-l:** The law is about *model* replies. This is a *builder* file. The builder is trusted to write valid JSON. The code fails closed if the file is malformed. The main risk is if the builder writes a directive that *looks* valid but is logically inconsistent (e.g., `ends` matches a boundary, but the resulting variant violates other laws like SENTENCE LAW). The variant *does* face all gates (per background: "Every gate... runs on every pool moment, the variant included"). So, if the variant is illegal, the gates will catch it.
    7.  **Correction:** This is not a critical L-l violation because it's not a model reply. It is a builder input. The system relies on the gates to validate the *result*.

**<medium> Potential Bypass of Ruling 90 via `spot_place` Logic**
*   **File:** `tests/package/proof_ledger.py` (lines 135-143 in diff)
*   **Issue:** The `spot_place` function determines if a package can take the spotlight slot. It calls `SPOT.day_taken(again, pk["segments"][0]["channel_id"], SPOT.et_day(now), alt)`.
*   **Logic:** `day_taken` returns `True` if the channel has a spotlight that day, *unless* the current record is the `alternative_to` story.
*   **Concrete Sequence:**
    1.  Channel A has a sealed spotlight `Story_X` today.
    2.  A new package `Pkg_Y` is created for Channel A, with `derived_from.alternative_to = "Story_X"`.
    3.  `spot_place` is called. `alt` is `"Story_X"`.
    4.  `day_taken` checks the `spotlit` list. It finds `Story_X`. Since `r.get("story_id") == alternative_to` is `True`, it skips this record.
    5.  If there are no *other* spotlights for Channel A today, `day_taken` returns `False`.
    6.  `spot_place` returns `(None, "Story_X")`.
    7.  The pin is written. `record_spotlit` adds `Pkg_Y` to the `SPOTLIGHTS.json` with `alternative_to: "Story_X"`.
    8.  **Result:** Channel A now has *two* entries in `SPOTLIGHTS.json` for today: `Story_X` and `Pkg_Y`.
    9.  **Is this allowed?** Ruling 90 says "at most one spotlight per channel per ET day". However, the new code explicitly allows an "alternative" to take the place of the named story. The docstring for `day_taken` says: *"a variant that is the ALTERNATIVE to a named sealed spotlight takes that story's place, and only that one"*.
    10. **The Problem:** Does `Pkg_Y` *replace* `Story_X` in the record, or does it *add* to it? The code `record_spotlit` (line 172-177) *appends* a new record. It does not remove `Story_X`.
    11. **Consequence:** If `Story_X` is later launched, and `Pkg_Y` is also launched, the channel has two spotlights. The `day_taken` check for a *third* spotlight `Pkg_Z` (with no alternative) would see both `Story_X` and `Pkg_Y` and return `True` (taken). But if `Pkg_Z` claims to be the alternative to `Story_X`, it would also be admitted.
    12. **Attack (a):** "Can a directive admit a second spotlight that is NOT the named alternative, or a third one?"
        *   If `Pkg_Y` is the alternative to `Story_X`, it is admitted.
        *   If `Pkg_Z` is *also* the alternative to `Story_X`, `day_taken` will skip `Story_X` (because it matches `alternative_to`). It will *not* skip `Pkg_Y` (because `Pkg_Y`'s `story_id` is not `Story_X`). So `day_taken` returns `True` (taken by `Pkg_Y`). `Pkg_Z` is rejected.
        *   So, only *one* alternative can be admitted per named story. This seems correct.
    13. **However:** What if `Story_X` is *not* the current spotlight, but a *previous* one? The `day_taken` function checks `r.get("day_et") == day`. It only looks at today's records. So it only cares about today's spotlights.
    14. **Verdict:** The logic appears to enforce "one spotlight per channel per day, with one exception for a named alternative". The exception is that the alternative *replaces* the named story in the "taken" check, but both records exist in the file. This is consistent with the "takes that story's place" language.

**<medium> `directive_variant` Boundary Search Efficiency and Correctness**
*   **File:** `pipeline/tail_variant.py` (lines 65-71 in diff)
*   **Issue:** The loop `for k in range(k1 - 1, k0 - 1, -1):` iterates from the last sentence boundary backwards to the first. It checks if the tokens from `k0` to `k` end with `want`.
*   **Logic:** `src.sentences[k0][0]` is the start index of the first sentence. `src.sentences[k][1]` is the end index of sentence `k`.
*   **Concrete Sequence:**
    1.  Parent moment has sentences `k0=0` to `k1=5`.
    2.  Directive `ends` matches the end of sentence `k=3`.
    3.  The loop starts at `k=4`. Checks if tokens `0..4` end with `want`. No.
    4.  Loop `k=3`. Checks if tokens `0..3` end with `want`. Yes.
    5.  Creates variant with `sentences=[0, 3]`.
    6.  This is the *longest* earlier boundary that matches. This is correct per the docstring: *"ending at the longest earlier sentence boundary whose words END as d['ends']"*.
    7.  **Edge Case:** What if `want` is empty? `if not want: return None`. Safe.
    8.  **Edge Case:** What if `want` is longer than the entire span? `got[-len(want):]` will be the whole `got`. If `got != want`, it fails. Safe.

**<low> Test Coverage for `spot_place` with `None` Record**
*   **File:** `tests/package/test_ruling_104.py` (line 266 in diff)
*   **Issue:** `self.assertTrue(PLG.spot_place(pk, None, NOW)[0])`
*   **Logic:** If `again` is `None` (record cannot be read), `spot_place` returns `"ruling 90: ... or the record cannot be read"`. This is a fail-closed behavior. Correct.

### SHIP: yes with conditions

**Conditions:**
1.  **Verify `E.spoken` Compatibility with L-k:** Ensure that `E.spoken` does not perform any normalization that conflicts with `C.canon_tokens`. If `E.spoken` is a raw token extractor, it is fine. If it expands abbreviations or fixes entities, it must be consistent with the canonical form. If there is any doubt, route the source tokens through `transcript_store.read_text` or `story_semantics._norm` before comparing, as mandated by L-k.
2.  **Clarify "Takes Place" Semantics:** The `SPOTLIGHTS.json` file will contain both the original spotlight and the alternative. Ensure that downstream consumers (e.g., the integrator's launch logic) correctly interpret this. If the integrator launches *all* spotlights for a channel, it will launch both. The "takes place" logic only prevents a *third* spotlight from being admitted. It does not remove the first. This is likely intended (the alternative is a *new* pin, not a deletion of the old one), but it should be explicitly documented that the channel will have two pins, and the orchestrator must choose which one to launch.
3.  **Add Test for Multiple Alternatives:** Add a test case where two different packages claim to be the alternative to the *same* story. Verify that the second one is rejected by `day_taken` because the first alternative is now in the `spotlit` list and does not match the `alternative_to` ID. (My analysis suggests this works, but a test is needed to prove it).