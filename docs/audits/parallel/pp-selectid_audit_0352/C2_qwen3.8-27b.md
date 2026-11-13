# qwen3.8-27b (qwen/qwen3.8-27b) 49 s finish=stop usage in 9112 / out 1672 usd~0.052 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0352

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I (GLM-5.3-FLASH) raised several P1s that were largely **coverage/documentation gaps** rather than behavioral defects (e.g., P1-1 about `context_around` returning `""` vs `None`). The other models (Grok, Qwen) correctly identified that these were non-issues because the verdicts coincide.

However, **Grok and Qwen missed a subtle interaction** that I partially flagged but didn't fully resolve: the **differential test** in `test_medley.py` (lines 145–153) is the critical piece that *proves* the "refuse exactly what the package stage refuses" law. In Cycle 1, I noted this was a "condition" but didn't verify the test logic itself. In Cycle 2, I can see the test explicitly stubs `CI.context_around` and calls `PK.exclusion_for` with a router that **throws an exception if called**. This proves the deterministic path is identical. I missed verifying this test's correctness in Cycle 1.

**Qwen** correctly noted that `ad_read_marker` handles `before_text=None` by treating it as `""`, which means the marker search only runs on the moment text. This is consistent with the "fail closed" law because the package stage will still refuse no-context moments. I agreed with this but didn't explicitly trace the `None` path in my Cycle 1 output.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My Position |
|---|---|
| **Grok: "SHIP: yes"** | **Agree.** The diff is clean, the laws are respected, and the tests are sufficient. |
| **Qwen: "SHIP: yes"** | **Agree.** Qwen's analysis of the `KeyError` and `None` context paths is correct. |
| **My Cycle 1 P1-1 (context_around contract)** | **Downgrade to P2.** The differential test proves the behavior is identical. The "contract" concern is moot because the test stubs the context and verifies the verdict matches. |
| **My Cycle 1 P1-2 (why_none ordering)** | **Agree it's correct.** The guard `if out["package"] is None and not out.get("why_none")` is sound. |
| **My Cycle 1 P2-1 (why_none truncation)** | **Agree it's fixed.** The new code truncates each angle's reason to 250 chars, not the whole message to 900. This is better. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1 — `ad_read_out` uses `m["sentences"][0]` and `m["sentences"][1]` directly.**
`package.py:57`: `CI.context_around(src_of(m, sources), m["sentences"][0], m["sentences"][1], *m["words"])`.
If a moment has fewer than 2 sentences, this will raise an `IndexError`, not a `KeyError`. The `except KeyError` clause will not catch it.
*   **Scenario:** A moment with `sentences=[0]` (only one sentence) reaches `ad_read_out`. `m["sentences"][1]` raises `IndexError`. The build crashes.
*   **Mitigation:** The `no_role_on_screen` filter runs before `ad_read_out`. If `no_role_on_screen` requires at least 2 sentences (which it likely does, given the "opener rule" context), then moments with <2 sentences are already filtered out. **However, this is not verifiable from the diff.** If `no_role_on_screen` does not filter out single-sentence moments, this is a **P1**.
*   **Verdict:** **P1** (potential crash) unless `no_role_on_screen` guarantees `len(sentences) >= 2`. Since I cannot see `no_role_on_screen`'s implementation, I must flag this.

**P2-2 — `ad_read_out` does not check if `m["text"]` is present.**
`package.py:60`: `M.ad_read_marker(m["text"], before)`. If `m["text"]` is `None` or missing, `ad_read_marker` handles it (`moment_text or ""`), so this is safe. No issue.

**P2-3 — The differential test only checks `ms[:2]`.**
`test_medley.py:148`: `for m in ms[:2]:`. The test only verifies that the first two moments (which have context) produce the same verdict. It does not verify that moment "c" (no context) or "d" (no Source) are handled identically by both stages. However, the docstring and the `ad_read_out` logic make it clear that these are skipped. The test is sufficient for the *deterministic* part, which is the focus of the law. No issue.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `moments.py` | P1 (coverage) | P2 (clean) | The differential test proves the behavior is identical. |
| `package.py` | P1 (context contract) | P1 (IndexError risk) | New finding: `m["sentences"][1]` may raise `IndexError` if not caught. |
| `test_medley.py` | P2 (truncation) | P2 (sufficient) | The tests are adequate for the stated laws. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1.  **`package.py:57` — Potential `IndexError` if `m["sentences"]` has fewer than 2 elements.**
    *   **Scenario:** A moment with `sentences=[0]` survives `no_role_on_screen` and reaches `ad_read_out`. `m["sentences"][1]` raises `IndexError`. The build crashes.
    *   **Fix:** Either ensure `no_role_on_screen` filters out moments with <2 sentences, or add a check in `ad_read_out` for `len(m["sentences"]) < 2` and skip (fail closed).

**P2 MEDIUM:**
1.  **`package.py:57` — `KeyError` catch is too narrow.**
    *   **Scenario:** If `src_of` or `CI.context_around` raises an `IndexError` or other exception, it is not caught.
    *   **Fix:** Consider catching `Exception` or specifically `IndexError` in addition to `KeyError`, or ensure the inputs are validated upstream.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Ensure that `ad_read_out` cannot crash on malformed moments by either validating `m["sentences"]` length or broadening the exception handling to catch `IndexError` in addition to `KeyError`.**

## 7. PRODUCTION READY?

**Yes with conditions.**

**Condition:** Verify that `no_role_on_screen` filters out all moments with fewer than 2 sentences. If it does, the `IndexError` risk is mitigated. If it does not, add a guard in `ad_read_out` to skip moments with `len(m["sentences"]) < 2` (fail closed).