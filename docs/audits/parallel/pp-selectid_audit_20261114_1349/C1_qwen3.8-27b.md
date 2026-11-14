# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 31453 / out 3127 usd~0.141 (upper-bound price)

To audit the `pp-selectid` branch, I have analyzed the diff against the Governing Laws, the Orchestrator's Ruling 102, and the provided background facts.

### Findings

**<critical> (a) Refusal vs. Held Ambiguity in `held_why`**
*   **File:** `pipeline/package.py` (lines 57-64 in diff)
*   **Issue:** The function `held_why(e)` determines if a failure is a "Held" (retry next build) or a "Refusal" (permanent fail). It checks `if isinstance(e, ValueError) and str(e).startswith("CONTEXT_TOO_LONG")`.
*   **Sequence:** If a model returns a `ValueError` that does *not* start with "CONTEXT_TOO_LONG" (e.g., a parsing error wrapped in a ValueError, or a different context error), it is classified as `HELD`. However, if a *valid* verdict is returned that fails the integrity check (e.g., `REFERENT_OUTSIDE`), that is handled elsewhere. The risk is if a *transient* error is misclassified as a *permanent* refusal, or vice versa.
    *   *Correction:* The code explicitly handles `CONTEXT_TOO_LONG` as a Refusal. All other exceptions (including `ProviderError`, `RuntimeError`, `DeadlineExceeded`) are treated as `HELD`. This aligns with Ruling 102 ("an unavailable leg moves on... never a refusal").
    *   *However*, look at `second_screen` (line 193-194 in diff). If `fails.get(mid)` is empty and `a2 is None`, it defaults to `HELD`. If `a2` exists but fails the vendor check, it is `STEP_A_SAME_VENDOR` (a Refusal). This logic seems sound.
    *   *Real Critical Risk:* In `prescreen` (line 91-94 in diff), if `got is None`, it calls `held_why(e)`. If `e` is a `ValueError` from `context_integrity.step_a` that is *not* `CONTEXT_TOO_LONG` (e.g., a bug in the integrity check itself), it will be marked `HELD` and retried forever, potentially masking a code bug. But more importantly, **does `context_integrity.step_a` raise `ValueError` for other reasons?** The background says `step_a` raises `ValueError` for `CONTEXT_TOO_LONG`. If it raises other `ValueError`s, they are now `HELD`. If it raises `RuntimeError` for logic errors, they are `HELD`. This is fail-open for logic errors, but fail-closed for availability. Given "M12 FAIL CLOSED: missing data... rejects", treating a *logic* error as "unavailable" (Held) might violate the spirit of fail-closed if the logic error is deterministic. But Ruling 102 explicitly says "STEP_A_UNAVAILABLE MUST NEVER END A CLIP". So this is likely intended.

**<high> (b) Chain Order and Vendor Exclusion in `confirm_ahead`**
*   **File:** `pipeline/package.py` (lines 169-175 in diff)
*   **Issue:** `confirm_ahead` is supposed to ask Grok *only*. The code constructs `hv` and `hf` (vendors/families to exclude) as *all* backends where `b.vendor != CONFIRM_VENDOR` (i.e., everything except xAI).
    ```python
    hv = {b.vendor for b in router.backends.values() if b.vendor != CONFIRM_VENDOR}
    hf = {b.family for b in router.backends.values() if b.family != CONFIRM_VENDOR} # BUG?
    ```
    Wait, `CONFIRM_VENDOR` is `"xai"`. `b.family` is e.g., `"grok"`, `"deepseek"`. `b.family != "xai"` is always True. So `hf` becomes the set of *all* families.
    Then `prescreen` is called with `set(wv) | hv` and `set(wf) | hf`.
    `prescreen` uses these sets to *exclude* backends.
    If `hf` contains all families, then *all* backends are excluded from the `confirm_ahead` call?
    Let's check `prescreen` logic (line 86-97 in diff). It iterates `router.chain(...)`. It checks `if b.vendor in set(wv) or b.family in set(wf)`.
    If `hf` is `{grok, deepseek, glm, gemini, gemma}`, then `b.family in hf` is True for *all* backends.
    Therefore, `confirm_ahead` will **skip every backend** and return no verdicts.
    *   **Sequence:**
        1.  `confirm_ahead` is called.
        2.  `hv` = `{heimdall/deepseek, heimdall/glm, google, local_judge}`.
        3.  `hf` = `{deepseek, glm, grok, gemini, gemma}` (since no family is "xai").
        4.  `prescreen` is called with `wv = {heimdall/deepseek, heimdall/glm, google, local_judge, xai}` (writers + hv) and `wf = {deepseek, glm, grok, gemini, gemma}` (writers + hf).
        5.  The chain for `step_a_second` is `[Grok, Deepseek, Glm, Gemini, LocalJudge]`.
        6.  Grok: `vendor="xai"` is in `wv`. Skipped.
        7.  Deepseek: `family="deepseek"` is in `wf`. Skipped.
        8.  Glm: `family="glm"` is in `wf`. Skipped.
        9.  Gemini: `family="gemini"` is in `wf`. Skipped.
        10. LocalJudge: `family="gemma"` is in `wf`. Skipped.
    *   **Result:** `confirm_ahead` produces **no verdicts**. The parallel optimization (Ruling 101) is broken. The build will fall back to sequential, or if it relies on `confirm_ahead` for the second verdict, it will fail.
    *   **Fix:** `hf` should be the set of families *other than* the confirm vendor's family? No, the goal is to ask *only* Grok. So we should exclude everyone *except* Grok.
    *   The current logic excludes everyone *except* those whose vendor is NOT xAI? No, it excludes those whose vendor IS in `hv`. `hv` is "vendors not xai". So it excludes non-xai vendors. It *keeps* xai vendors.
    *   But it *also* excludes families in `hf`. `hf` is "families not xai". Since no family is "xai", `hf` is all families. So it excludes all families.
    *   **Conclusion:** The intersection of "vendor not in hv" (i.e., vendor is xai) AND "family not in hf" (i.e., family is not in all families) is **empty**.
    *   **Verdict:** **CRITICAL BUG**. `confirm_ahead` will never ask any model.

**<high> (c) Local Judge Deadline and Hang**
*   **File:** `pipeline/providers.py` (background fact)
*   **Issue:** `LocalJudgeBackend` has `WAIT_S = 2400` (40 minutes).
*   **Sequence:** If Deepseek, Glm, and Gemini are all down/unavailable, the chain reaches `local_judge`. The router waits up to 40 minutes for the local judge.
*   **Ruling 102:** "reached without declaring Heimdall down".
*   **Risk:** If the local judge is slow or stuck, the build hangs for 40 minutes. This is allowed by Ruling 87 ("up to 40 min"). However, if this happens *during* the `confirm_ahead` parallel phase, it might block the main thread? No, `confirm_ahead` runs in a `ThreadPoolExecutor`. But if `confirm_ahead` is broken (see finding b), it doesn't matter. If it were fixed, and it asked the local judge, it would wait 40 mins in the background. The main thread waits for the *filter* (Heimdall). If the filter is fast, the build proceeds. The `confirm_ahead` result is used later. If the local judge takes 40 mins, the *second screen* (which runs after the first screen) might wait for it?
*   **Second Screen:** `second_screen` calls `prescreen` with `kind="step_a_second"`. If the first 3 legs are down, it hits the local judge. It will wait 40 minutes. This is a **High** risk for build latency, but compliant with Ruling 87/102.

**<medium> (d) Pin Seal and `last_resort`**
*   **File:** `pipeline/package.py` (lines 310-313 in diff)
*   **Issue:** The `context_a` row in the pin inventory is modified to include `last_resort` if present.
*   **Law L-d:** "The PBX-approved preview... must reproduce with the current code".
*   **Law 22:** "Frozen v2f reference... must keep re-rendering byte-identically".
*   **Sequence:** If a *new* build uses the local judge, the pin will have a `last_resort` key. If an *old* pin (v2f) is re-verified, does it have `last_resort`? No, because the local judge wasn't used. The code says: `**({"last_resort": last_resort} if last_resort else {})`. So old pins remain unchanged. New pins with local judge verdicts get the key. This is compliant.

**<medium> (e) $19 Stop**
*   **File:** `tests/package/proof_ly.py` (line 446 in diff)
*   **Issue:** `LY_STOP_USD` changed from 16.0 to 19.0.
*   **Ruling:** "At $19 stop and tell me on line 1 in capitals".
*   **Code:** `start_refused` checks `if spent0 >= PL.LY_STOP_USD`.
*   **Sequence:** If spend is $18.99, it starts. If $19.00, it refuses. This matches the ruling.

**<low> (f) Test Coverage**
*   **File:** `tests/package/test_ruling_102.py`
*   **Issue:** The test `test_every_vendor_but_grok_s_is_avoided_ahead` (line 873) mocks `prescreen` and checks the `wv` and `wf` sets passed to it.
    *   It expects `wv` to be `{"heimdall/deepseek", "heimdall/glm", "google", "local_judge"}`.
    *   It expects `wf` to be `{"deepseek", "glm", "gemini", "gemma"}`.
    *   This test **passes** with the current buggy code because it only checks the *inputs* to `prescreen`, not the *result* of `prescreen`. It does not verify that `confirm_ahead` actually *gets* a verdict from Grok.
    *   The test `test_the_confirm_ahead_is_grok_only` is named misleadingly; it tests the *exclusion sets*, not the *inclusion* of Grok.

### Summary of Findings

1.  **<critical> `confirm_ahead` is broken:** The calculation of `hf` (families to exclude) in `package.py` (line 172) results in excluding *all* families, because no backend has a family named "xai". Consequently, `confirm_ahead` will skip every backend in the chain and return no verdicts. This disables the Ruling 101 parallel optimization and may cause the build to fail if it relies on the ahead-of-time confirm.
2.  **<high> Latency Risk:** The local judge (40 min wait) is now in the main `step_a_second` chain. If upstream models are down, builds will hang for 40 minutes. This is compliant with Ruling 87 but operationally risky.
3.  **<medium> Test Blind Spot:** The test for `confirm_ahead` exclusion sets passes despite the logic being broken, because it doesn't assert that a verdict is actually returned.

### SHIP: NO

**Conditions for Ship:**
1.  Fix `confirm_ahead` in `pipeline/package.py`. The `hf` set should likely be empty or contain only families *other than* the confirm vendor's family if the intent is to allow the confirm vendor's family. Actually, the intent is to ask *only* Grok. So we should exclude all vendors *except* xAI, and all families *except* Grok's family?
    *   Current: `hv` = non-xai vendors. `hf` = non-xai families (which is all families).
    *   Correct: `hv` = non-xai vendors. `hf` = non-grok families?
    *   If we set `hf` to `{f for f in families if f != "grok"}`, then Grok (family "grok") is *not* excluded by family. Grok (vendor "xai") is *not* excluded by vendor (since `hv` is non-xai). So Grok would be asked.
    *   Deepseek (vendor "heimdall/deepseek") is in `hv`. Excluded.
    *   This seems correct.
2.  Add a test that asserts `confirm_ahead` returns a non-empty verdict when Grok is available.