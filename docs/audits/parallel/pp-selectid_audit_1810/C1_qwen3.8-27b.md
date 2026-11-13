# qwen3.8-27b (qwen/qwen3.8-27b) 42 s finish=stop usage in 14903 / out 2380 usd~0.080 (upper-bound price)

I have reviewed the diff for `pp-selectid-1810` against RULING 76 and the Governing Laws.

### P0 Findings (Blockers)

**1. `pipeline/package.py`: `same_speech` logic is unsound and violates L-k (Canonical Form)**
*   **Location:** `pipeline/package.py` (lines 67-83 in diff context, specifically the `same_speech` function).
*   **Issue:** The function uses `difflib.SequenceMatcher` on `canon.canon_tokens` to determine if two texts are the "same speech."
    *   **Violation of L-k:** L-k states that "two strings a listener hears as the same words compare equal... a different number, unit, sign, name, negation or dropped word never does." `difflib` is a fuzzy string matching algorithm. It does not understand semantic or canonical equivalence. For example, if `canon_tokens` produces `["bitcoin", "is", "up"]` and `["bitcoin", "is", "down"]`, `difflib` might find a high match ratio (2/3 words) and potentially flag it as "same speech" depending on the threshold, which is a critical failure (negation change).
    *   **Unsound Threshold:** The logic `sum(x.size for x in sm.get_matching_blocks() if x.size >= SAME_SPEECH_RUN) >= REPOST_ALIGN_MIN * short` is mathematically fragile. `REPOST_ALIGN_MIN` is not defined in the diff (likely imported or global, but its value is critical). If `REPOST_ALIGN_MIN` is 0.8, and `short` is 8, it requires 6.4 words in runs of 3. This allows for significant divergence.
    *   **Scenario:** A delivered clip says "Bitcoin crashed 5%." A new clip says "Bitcoin crashed 5% and then recovered." `same_speech` might return `True` if the matching blocks are large enough, incorrectly blocking a valid, distinct new statement. Conversely, if the new clip is "Bitcoin fell 5%," `canon` might normalize "crashed" and "fell" differently, but `difflib` operates on the token list. If `canon` doesn't map synonyms (it shouldn't, per L-k), `difflib` will see them as different. However, the risk is false positives where *different* events are deemed "same speech" due to shared boilerplate words (e.g., "The market is..."), leading to valid content being rejected (M12 Fail Closed violation? No, it's a false rejection, which is safe but bad for utility. Wait, L-k says "a different... dropped word never does." If `same_speech` returns True for different words, it violates the spirit of strict canonical comparison).
    *   **Correction:** `same_speech` should likely rely on exact canonical equality or a very strict subset check, not fuzzy matching. Fuzzy matching is explicitly dangerous for "same speech" determination in a legal/compliance context.

**2. `pipeline/package.py`: `expired` check order and `ctx.now` availability**
*   **Location:** `pipeline/package.py` (lines 123-125 in diff context).
*   **Issue:** The check `elif expired(m, ctx.now):` is placed *after* the `time_sensitive` check.
    *   **Scenario:** A moment is `time_sensitive` AND `expired` (>12h). The code reports `time_sensitive` failure (L-v 3) and does *not* report `expired`. This is acceptable per the comment "both exclude," but the `expired` function itself calls `E.age_hours`. If `ctx.now` is not a valid datetime or `m.get("published_at")` is malformed, `expired` might raise an exception or return `False` incorrectly.
    *   **Critical:** The `expired` function in `package.py` (lines 86-91) calls `E.age_hours(m.get("published_at"), now)`. If `m.get("published_at")` is `None`, `E.age_hours` must handle it. The docstring says "or its publish time cannot be read (never assumed fresh)." If `E.age_hours` returns `None` for missing data, `age is None` is `True`, so it returns `True` (expired). This is correct. However, if `E.age_hours` raises an exception on bad data, `usable` will crash. The diff does not show `E.age_hours` implementation. Assuming it is robust, this is a P1. If it is not, it is P0. Given `M12 FAIL CLOSED`, an exception is a fail, which is safe, but a crash in `usable` might prevent the entire build from running, which is a DoS.

**3. `tests/package/proof_ledger.py`: `--hours` validation logic**
*   **Location:** `tests/package/proof_ledger.py` (lines 192-194 in diff context).
*   **Issue:** `if not 0 < a.hours <= package_pin.WINDOW_H:`.
    *   **Scenario:** If `a.hours` is `0`, it refuses. If `a.hours` is `12.0`, it allows. This is correct.
    *   **However:** The default is `package_pin.WINDOW_H` (12.0). The argument is `type=float`. If a user passes `--hours 12.0000001`, it refuses. This is strict.
    *   **P1:** The refusal message says "outside (0, 12]". This is correct.

### P1 Findings (Major)

**4. `pipeline/candidates.py`: `expire` function does not update `lineup` or `history` correctly for "for good"**
*   **Location:** `pipeline/candidates.py` (lines 27-49 in diff context).
*   **Issue:** `expire` calls `outcome(e, "expired", ...)`. `outcome` sets `state` to `"closed"` and `until` to `None`. This prevents `due` from returning it. This is correct.
*   **However:** The `expire` function iterates over `reg["candidates"]`. It checks `if e["state"] == "closed": continue`. This is correct.
*   **Potential Issue:** The `published` dict is built in `proof_ledger.py` by reading `inputs.json`. If `inputs.json` is missing or corrupt, `pub` will be empty or partial. `expire` will then treat missing publish times as "no known publish time" and expire them. This is Fail Closed (M12). Correct.

**5. `pipeline/package_pin.py`: `window_problems` uses `datetime.now(timezone.utc)` as default**
*   **Location:** `pipeline/package_pin.py` (lines 141-159 in diff context).
*   **Issue:** `now = now or datetime.now(timezone.utc)`.
    *   **Scenario:** In `proof_ledger.py`, `window_problems` is called with `res["package"]["segments"]` but *no* `now` argument (line 230: `package_pin.window_problems(res["package"]["segments"])`).
    *   **Violation of RULING 76 (c):** "Open candidates and sealed-but-unrendered pins are re-checked against (a) at the moment they would render."
    *   **The Render Clock:** The build has a specific `ctx.now` (the render clock). Using `datetime.now(timezone.utc)` inside `window_problems` when called from the pin stage means it uses the *current system time*, not the *build's render clock*.
    *   **Impact:** If the build takes 10 minutes, and the render clock is fixed at the start, the pin stage check might use a time 10 minutes later. This could cause a moment that was valid at the start of the build to be expired at the pin stage, or vice versa. More critically, it breaks determinism. The pin should be checked against the *same* clock that was used for selection.
    *   **Correction:** `proof_ledger.py` must pass `now` to `window_problems`. Line 230 should be `package_pin.window_problems(res["package"]["segments"], now)`.

**6. `pipeline/package.py`: `same_speech` imports `canon` and `difflib` inside the function**
*   **Location:** `pipeline/package.py` (lines 72-73 in diff context).
*   **Issue:** `import difflib` and `import canon` are inside `same_speech`. This is inefficient but not a bug. However, `canon` is a local module. If `canon` is not in the path, it will fail. Assuming it is, this is a P2.

### P2 Findings (Minor)

**7. `tests/package/test_medley.py`: `TestRuling76Window` uses `NOW`**
*   **Location:** `tests/package/test_medley.py` (lines 310-355 in diff context).
*   **Issue:** The tests use a global `NOW`. This is standard for unit tests.

**8. `pipeline/package.py`: `REPOST_ALIGN_MIN` is not defined in the diff**
*   **Location:** `pipeline/package.py` (line 83 in diff context).
*   **Issue:** `REPOST_ALIGN_MIN` is used but not defined in the diff. It must be defined elsewhere. If it is not defined, this is a P0 (NameError). Assuming it is defined in the existing codebase, this is a P2 (verify value).

### Summary of Critical Issues

1.  **P0:** `same_speech` uses `difflib` (fuzzy matching) which violates L-k (strict canonical comparison) and can lead to false positives/negatives for "same speech."
2.  **P0:** `window_problems` in the pin stage uses `datetime.now()` instead of the build's `ctx.now`, violating RULING 76 (c) and determinism.

### SHIP: No

**Conditions for Ship:**
1.  Replace `difflib` in `same_speech` with a strict canonical comparison (e.g., `canon.canon_tokens(a) == canon.canon_tokens(b)` or a strict subset check that does not allow for word order changes or missing words unless explicitly defined as "same speech" by a stricter rule).
2.  Pass `now` (the render clock) to `package_pin.window_problems` in `proof_ledger.py` line 230.
3.  Verify `REPOST_ALIGN_MIN` is defined and its value is appropriate for strict "same speech" detection.