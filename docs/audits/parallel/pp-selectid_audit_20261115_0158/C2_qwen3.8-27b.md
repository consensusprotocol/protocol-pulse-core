# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 17898 / out 2224 usd_reported=0.002418 usd~0.087 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261115_0158
# Reviewer: GLM-5.3-FLASH (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Qwen3.8-27B's P1 (System Prompt Mutation):** I missed this in Cycle 1. I noted that `FormatBackend.complete` appends `" Reply with one JSON object only."` to the system message (line 143) and that the test pins body equality after popping `response_format` and `reasoning_effort`. I correctly observed that the test *would* catch a divergence, but I failed to verify whether production's `HeimdallBackend.complete` actually appends that same suffix. Qwen correctly identified that if production does *not* append it, the test fails immediately. The C1 consensus states that production *does* append it (providers.py:420-421), which resolves this. However, my Cycle 1 analysis was contingent on an unverified assumption. I should have flagged this as a P1 "verify production parity" rather than a P3 "nit."

**GLM-5.3-FLASH (myself) Cycle 1:** I raised the body drift concern but downgraded it to P3 because "the test pins it." I was correct that the test exists, but I failed to note that the test's fidelity depends on the production code being stable. The C1 consensus confirms the test was widened to include a vision prompt, which strengthens the pin.

**Claude's C1 Consensus:** The builder's consensus addresses my P1 concerns by:
- Confirming production appends the suffix (resolving Qwen's P1).
- Widening the body test to include vision prompts (resolving my drift concern).
- Documenting that medium's reasoning counts against the output budget (resolving my P1 on budget).
- Bounding the overshoot past the stop (resolving my P2 on spend).
- Fixing the `choose()` gap when no valid answers exist (resolving my P3).

## 2. WHERE DO YOU AGREE OR DISAGREE?

**Qwen P1 (System Prompt):** AGREE with the concern, but DISAGREE with the conclusion that it's a blocker. The C1 consensus confirms production appends the suffix, so the test passes. The code is correct.

**Qwen P2 (shape() truncation heuristic):** AGREE. The heuristic `t.count("{") > t.count("}")` is fragile for JSON with unbalanced braces in string values. However, this is a diagnostic tool, not a verdict gate. The risk is misclassification in the "3 commonest failure shapes" report, which is low-impact. I maintain P2.

**Qwen P3 (choose() tie-breaking):** AGREE. The logic is sound. `None` p50 maps to `-inf`, which is correctly deprioritized.

**Qwen P3 (Spend stop):** AGREE. The stop logic is correct and tested.

**Qwen P3 (Ruling 110 backwards compatibility):** AGREE. Defaults preserve ruling 110 behavior.

**Qwen P3 (Table arithmetic):** AGREE. The formulas match the order's definitions.

**My Cycle 1 P2 (names fallback):** The C1 consensus states that a missing key in `names` falls to `name(m)`, which raises `KeyError` for non-110 keys. This is fail-closed. I agree with the resolution.

**My Cycle 1 P3 (model_id semantics):** The C1 consensus does not explicitly address this, but the test `test_a_named_back_end_on_its_own_chain_answers_for_its_key` verifies that `row["model_id"]` equals `b.model`. For ruling 110's backends, `b.model` should equal `MODELS[m]`. I maintain P3 as a latent risk if backends are aliased.

**My Cycle 1 P1 (body drift):** RESOLVED by the widened test (vision prompt included). I agree with the C1 consensus.

**My Cycle 1 P1 (medium budget):** RESOLVED by documentation. I agree with the C1 consensus.

## 3. NEW FINDINGS FROM THIS REVIEW

**[P2] `shape()` "prose around the JSON" detection is fragile.** Line 183-189: The code finds the first `{` and last `}` and tries to parse the substring. If the JSON is embedded in prose with multiple `{` or `}` characters (e.g., `Here is {a: 1} and {b: 2}`), the substring `{a: 1} and {b: 2}` is not valid JSON, so it falls through to "truncated" or "invalid JSON." This is a misclassification. The fix would be to try parsing the substring and, if it fails, try shorter substrings or use a regex to find balanced braces. However, this is a diagnostic tool, and the impact is low. I maintain P2.

**[P3] `anchor_failures()` relies on `R.anchor_units()` returning a dict of unit->pins.** Line 224: `for u, pins in R.anchor_units(r, anchors).items():`. If `anchor_units` returns a list or another structure, this fails. The test mocks it to return a dict, so the test passes. But the production code must return a dict. This is a latent coupling. I maintain P3.

**[P3] `table()` reads `SOURCE_110` (ruling 110's results) and filters by `model == "dsv4"`.** Line 334: `old = RX.summary([r for r in _rows(SOURCE_110) if r.get("model") == "dsv4" and r.get("record") in keys], models=["dsv4"])`. If ruling 110's model key is not "dsv4" (e.g., it's the full model name), this filter returns nothing, and the "ruling 110" column is empty. The C1 consensus does not address this. I recommend verifying that ruling 110's rows use `model == "dsv4"`. If not, this is a P2.

**[P3] `run()` uses `os.path.relpath(p, WT)` to identify records.** Line 296: `if (os.path.relpath(p, WT), v) not in seen`. If `p` is not under `WT`, `relpath` raises an error. The source records are expected to be under `WT`, so this is safe. But it's a latent assumption.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| FormatBackend body parity | P1 | P3 | C1 consensus confirms production appends the suffix; test widened to include vision. |
| shape() truncation heuristic | P2 | P2 | Unchanged; still fragile but low-impact. |
| choose() tie-breaking | P3 | P3 | Unchanged; logic is sound. |
| Spend stop | P2 | P3 | C1 consensus bounds the overshoot; documented. |
| Ruling 110 backwards compatibility | P3 | P3 | Unchanged; defaults preserve behavior. |
| Table arithmetic | P3 | P3 | Unchanged; formulas match order. |
| names fallback | P2 | P3 | C1 consensus confirms fail-closed behavior. |
| model_id semantics | P3 | P3 | Unchanged; latent risk if backends are aliased. |
| anchor_failures() coupling | P3 | P3 | New finding; latent coupling to `R.anchor_units()` return type. |
| table() SOURCE_110 filter | P3 | P2 | New finding; if ruling 110's model key is not "dsv4", the column is empty. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:**
1. `replay111.py:183-189` — `shape()` "prose around the JSON" detection is fragile for multiple braces. Fix: try parsing the substring, and if it fails, use a regex to find balanced braces.
2. `replay111.py:334` — `table()` filters ruling 110's rows by `model == "dsv4"`. Verify that ruling 110's rows use this key. If not, the "ruling 110" column is empty.

**P3 NIT:**
1. `replay111.py:224` — `anchor_failures()` relies on `R.anchor_units()` returning a dict. Document this assumption.
2. `replay110.py:24` — `row["model_id"] = b.model` changes ruling 110's row semantics. Verify `MODELS[m] == b.model` for all ruling 110 backends.
3. `replay111.py:296` — `run()` uses `os.path.relpath(p, WT)`. Ensure all source records are under `WT`.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Verify that ruling 110's rows use `model == "dsv4"` so that the `table()` function's comparison column is populated; if not, update the filter to match the actual model key.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. Verify that `shape()`'s "prose around the JSON" detection handles multiple braces correctly (P2).
2. Verify that `table()`'s filter for ruling 110's rows uses the correct model key (P2).
3. Confirm that `R.anchor_units()` returns a dict of unit->pins (P3).

P1_OR_WORSE: 0