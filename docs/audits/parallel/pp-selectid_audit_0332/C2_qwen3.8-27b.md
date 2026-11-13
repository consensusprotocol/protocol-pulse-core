# qwen3.8-27b (qwen/qwen3.8-27b) 179 s finish=stop usage in 20272 / out 2601 usd~0.100 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0332
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GLM-5.3-FLASH (P1-1, P1-2, P1-3, P1-4):**
- **P1-1 (snap_risk non-list risk):** I missed this in Cycle 1. GLM correctly identified that `list(risk or [])` would mangle a string risk into characters. **However, the fixed diff (line 76-77) now explicitly raises `TypeError` for non-list risks.** This is resolved. I agree with GLM's original concern but note it is now fixed.
- **P1-2 (marker window asymmetry / L-v2 dependency):** I missed the depth of this. GLM correctly noted that the 1.0s edge exclusion is "fail-open by declaration only if L-v2 is a hard gate." The consensus (K3) verified that L-v2 *is* a hard gate (`turn_change_inside is False` required). I agree with GLM's analysis but the risk is mitigated by the verified L-v2 behavior.
- **P1-3 (caption_source cache key):** I missed this. GLM noted that two rows sharing `transcript_sha256` share one `caption_source` lookup. The consensus answered this: `caption_source` is a pure function of the record's sha, so the cache is correct. I agree.
- **P1-4 (20s limit measurement divergence):** I missed this. GLM noted that `SNAP_MAX_S` is measured on word times, but `package.usable()` might measure duration differently (e.g., including pads). The consensus (K1) resolved this by adding a test `test_the_snap_limit_is_the_packagers_clip_limit` that asserts `LB.SNAP_MAX_S == PK.SEG_MAX_S`. I agree with GLM's concern and the fix.

**GROK-4.20-0309-REASONING:**
- Grok's analysis was concise and correct. It verified that `snap_risk` only appends, never removes. It confirmed the marker logic matches the ruling. It noted that non-anchoring rows stay out. I agree with all of Grok's findings.

**QWEN3.8-27B:**
- Qwen's P1-1 (startswith on tuple) was self-corrected: "This is actually fine." I agree.
- Qwen's P1-2 (SNAP_MAX_S hardcoding) was flagged as P2. The consensus (K1) resolved this with a test. I agree.
- Qwen's P1-3 (marker edge behavior) was correctly identified as intended per the ruling. I agree.
- Qwen's P1-4 (info["added"] calculation) was verified as correct. I agree.

**What I missed:** The most significant oversight was the **SNAP_MAX_S vs. package.SEG_MAX_S divergence** (GLM P1-4). I did not consider that the 20s limit might be measured differently in `usable()` vs. `reanchor()`. The consensus fix (test asserting equality) is correct.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My Position | Reason |
|---|---|---|
| GLM P1-1 (snap_risk non-list) | **Agree, now fixed** | The diff now raises `TypeError` for non-list risks (line 76-77). This is correct and tested (line 541-542). |
| GLM P1-2 (marker window / L-v2) | **Agree, mitigated** | The 1.0s edge exclusion is intentional per the ruling. L-v2 is a hard gate (verified in consensus K3). The risk is acceptable. |
| GLM P1-3 (caption cache) | **Agree, correct** | `caption_source` is a pure function of `transcript_sha256`. The cache is correct. |
| GLM P1-4 (20s measurement) | **Agree, now fixed** | The test `test_the_snap_limit_is_the_packagers_clip_limit` (line 504-506) asserts `LB.SNAP_MAX_S == PK.SEG_MAX_S`. This resolves the divergence. |
| Grok (all) | **Agree** | Grok's analysis is correct and concise. No disagreements. |
| Qwen P1-1 (startswith) | **Agree, no issue** | `str.startswith(tuple)` is standard Python. No risk. |
| Qwen P1-2 (SNAP_MAX_S) | **Agree, now fixed** | The test asserts equality with `PK.SEG_MAX_S`. |
| Qwen P1-3 (marker edge) | **Agree, intended** | The ruling explicitly defers edge markers to L-v2. |
| Qwen P1-4 (info["added"]) | **Agree, correct** | The calculation is correct. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `marker_inside` uses `lstrip()` which may not handle all whitespace variants.**
- **File:** `pipeline/ledger_build.py`, line 65.
- **Scenario:** `str(t.get("word") or "").lstrip().startswith(SPEAKER_MARKERS)`. `lstrip()` removes all leading whitespace, including tabs, newlines, and non-breaking spaces. If a caption token has a non-breaking space (`\u00a0`) before `>>`, `lstrip()` will remove it, and `startswith` will match. This is likely correct behavior, but it is not explicitly tested. The test (line 522-528) uses `">>"` and `"&gt;&gt;"` without leading whitespace.
- **Severity:** P2 (low likelihood, but untested edge case).

**P1-NEW-2: `snap_risk` imports `vo_fidelity` inside the function, which may be slow or fail.**
- **File:** `pipeline/ledger_build.py`, line 75.
- **Scenario:** `import vo_fidelity as VF` is inside `snap_risk()`. If `vo_fidelity` is not available or fails to import, `snap_risk` will raise an `ImportError`, which is not caught by `make()`'s `try/except` (which only catches `TypeError` for malformed risks). This could cause a build failure.
- **Severity:** P1 (medium likelihood if `vo_fidelity` is not always available).

**P1-NEW-3: The `caps_v` cache in `build_inputs` does not handle `caption_source` returning `None` for the second element.**
- **File:** `pipeline/ledger_build.py`, line 144.
- **Scenario:** `caps_v[sha] = caption_source(r, ctx, store, ledger_store)[0]`. If `caption_source` returns `(None, "reason")`, `caps_v[sha]` is `None`. This is handled by `marker_inside` (line 64: `getattr(cap, "tokens", None) or []`). However, if `caption_source` raises an exception, it is not caught here. The exception would propagate to `build_inputs`, which may not handle it.
- **Severity:** P2 (low likelihood, but unhandled exception path).

**P1-NEW-4: The test `test_a_snap_longer_than_20_s_stays_out` uses a hardcoded 72-word sentence.**
- **File:** `tests/package/test_ledger_build.py`, line 509.
- **Scenario:** `long_ = "Bitcoin " + " ".join(["keeps"] * 72) + " settling payments."`. This creates a 75-word sentence. The test asserts that `src.tokens[b]["end"] - src.tokens[a]["start"] > LB.SNAP_MAX_S`. If the word timing in the test fixture changes, this assertion may fail. The test is brittle.
- **Severity:** P2 (test brittleness, not a production issue).

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `reanchor` logic | 8/10 | 9/10 | The SNAP_MAX_S divergence is now tested and resolved. The marker logic is correct per the ruling. |
| `snap_risk` | 7/10 | 8/10 | The non-list risk is now handled with `TypeError`. The `vo_fidelity` import is a minor concern. |
| `marker_inside` | 8/10 | 8/10 | The 1.0s edge exclusion is intentional. L-v2 is a hard gate. No changes needed. |
| Tests | 7/10 | 9/10 | The new tests cover the 20s limit, marker edges, and `snap_risk`. The test brittleness is minor. |
| Funnel tools | 8/10 | 8/10 | The funnel tools are offline and read-only. No changes needed. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1. **`snap_risk` imports `vo_fidelity` inside the function** (`pipeline/ledger_build.py:75`). If `vo_fidelity` is not available, `snap_risk` will raise an `ImportError`, which is not caught by `make()`. **Fix:** Move the import to the top of the module, or catch `ImportError` in `make()`.

**P2 MEDIUM:**
1. **`marker_inside` uses `lstrip()` which may not handle all whitespace variants** (`pipeline/ledger_build.py:65`). **Fix:** Add a test for a caption token with a non-breaking space before `>>`.
2. **The `caps_v` cache in `build_inputs` does not handle `caption_source` raising an exception** (`pipeline/ledger_build.py:144`). **Fix:** Wrap the `caption_source` call in a `try/except` and log the error.
3. **The test `test_a_snap_longer_than_20_s_stays_out` is brittle** (`tests/package/test_ledger_build.py:509`). **Fix:** Use a dynamic word count based on the fixture's word timing.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Move the `vo_fidelity` import to the top of `pipeline/ledger_build.py`** to avoid an unhandled `ImportError` in `snap_risk()`. This is the only P1 finding that could cause a build failure.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Fix the `vo_fidelity` import in `snap_risk()`** (P1-NEW-2). Move the import to the top of the module, or catch `ImportError` in `make()`.
2. **Add a test for `marker_inside` with a non-breaking space before `>>`** (P2-NEW-1).
3. **Wrap the `caption_source` call in `build_inputs` in a `try/except`** (P2-NEW-3).

If these conditions are met, the code is production-ready. The core logic correctly implements Ruling 32: it snaps outward to whole sentences, enforces the 20s limit, checks for speaker markers, and records added words. It does not violate the "fail closed" or "verbatim whole sentences" laws.