# heimdall_qwen (qwen/qwen3.8-27b, 28.2 s, $0.002, finish stop)

# PROTOCOL PULSE: CODE AUDIT REPORT

**Subject:** `pp-ingest` (r124)
**Scope:** `pipeline/ingest/providers.py`, `pipeline/ingest/providers.json`, `tests/ingest/test_r124.py`
**Context:** Fix for latent ordering bug where local model (last resort) could be prioritized over Heimdall models when spend meter is not 'ok'.

---

## SECTION 1: CORRECTNESS

**Verdict: CORRECT**

The logic in `Router.order` (providers.py:844-853) correctly implements the three-tier sorting required by Ruling 118 and the Spend Freeze laws.

1.  **Logic Flow:**
    *   If `meter` is `None` or `state() == "ok"`, the chain is returned as configured. This preserves the default behavior where the local model is last in the static config.
    *   If `meter.state() != "ok"` (i.e., 'tripped' or 'unmeasured'):
        *   `last` list: Backends with `last_resort: true`.
        *   `middle` list: Backends with `spend_meter: true` (but not last resort).
        *   `front` list: All other backends.
        *   Result: `[front] + [middle] + [last]`.
    *   This ensures that when the meter is tripped/unmeasured, non-metered backends (if any) go first, then metered backends (Heimdall), and finally the local model. This strictly enforces "Heimdall is free... local model is last resort."

2.  **Edge Cases:**
    *   **Empty Chain:** If `ch` is empty, lists are empty, result is empty. Safe.
    *   **No Last Resort:** If no backend has `last_resort: true`, `last` is empty. Order becomes `[non-metered] + [metered]`. This matches B1's original intent (metered go last among the rest).
    *   **No Metered:** If no backend has `spend_meter: true`, `middle` is empty. Order becomes `[non-metered] + [last]`. Correct.
    *   **Both Metered and Last Resort:** The code explicitly excludes `last` from the `middle` calculation (`b not in last`). A backend cannot be in both `middle` and `last`. It will appear only in `last`. This is correct per the requirement that last-resort stays *after* all metered backends.

3.  **Validation:**
    *   `validate_config` (providers.py:117-118) correctly enforces that `last_resort` is a boolean if present. This prevents type errors in the `bool(...)` cast inside `_last_resort`.

4.  **Test Coverage:**
    *   `test_r124.py` covers the tripped state, the unmeasured state (implicitly via `Meter` mock), the 'ok' state, and the validation error.
    *   `test_the_real_chains_keep_ruling_118s_order_whatever_the_meter_says` verifies that for the *actual* production config, the order remains consistent with the static chain definition across all meter states. This is a strong integration check.

**No logic errors found.**

---

## SECTION 2: LAW COMPLIANCE

| Law | Status | Evidence |
| :--- | :--- | :--- |
| **BUILD** (Continuous ingest, mining, etc.) | **COMPLIANT** | The change only affects backend ordering. It does not break the ingest pipeline, queue, or mining logic. It ensures the mining chain respects the "Heimdall first, local last" hierarchy. |
| **L-x** (No single model, Ultron first) | **COMPLIANT** | The code supports multiple backends. The local model (Ultron) is explicitly marked `last_resort`, ensuring it is only used when other options are exhausted or the meter is not 'ok' and other options are unavailable. It does not force a single model. |
| **L-l** (Strict schema, no repair) | **COMPLIANT** | `validate_config` raises `ValueError` on invalid `last_resort` type. No silent repairs. |
| **L-j / L-m** (Fail closed) | **COMPLIANT** | If the meter is 'unmeasured', it is treated as not 'ok', triggering the safe ordering (local last). This is a fail-safe behavior. |
| **L-h / L-k** (Transcript handling) | **N/A** | Not touched by this diff. |
| **L-e** (Word timing) | **N/A** | Not touched by this diff. |
| **L-u / L-v** (Exclusions) | **N/A** | Not touched by this diff. |
| **Secrets** | **COMPLIANT** | No secrets are introduced. `last_resort` is a boolean flag. |
| **SPEND FREEZE** | **COMPLIANT** | The core purpose of r124 is to comply with the Spend Freeze and Ruling 118. By keeping the local model last when the meter is not 'ok', it prevents the local model from being called unnecessarily (which would violate the "Heimdall is free" preference and potentially the "no paid frontier" rule if the local model were misconfigured, though it's local). More importantly, it ensures that if the meter is tripped, the system falls back to Heimdall (metered) before Local (last resort), adhering to the "Heimdall mining continues" directive. |

**All applicable laws are compliant.**

---

## SECTION 3: SECURITY

**Verdict: NO ISSUES**

*   **Injection:** No SQL, shell, or template injection vectors. The code manipulates Python lists and dictionaries.
*   **Authentication:** No auth logic in this diff.
*   **Rate Limiting:** The `max_inflight` and `timeout_s` in `providers.json` are unchanged. The ordering logic does not bypass rate limits; it only changes *which* backend is tried first.
*   **Secrets:** No hardcoded keys. `last_resort` is a public config flag.
*   **Input Validation:** `validate_config` ensures `last_resort` is a bool. This prevents potential type confusion errors that could lead to unexpected behavior, though not a direct security vulnerability.

---

## SECTION 4: FRONTEND QUALITY

**N/A**

This is a backend pipeline change. No UI components are affected.

---

## SECTION 5: BACKEND QUALITY

**Verdict: EXCELLENT**

*   **DB Operations:** N/A (No DB writes in this diff).
*   **External API Calls:** The `Router` class handles backend selection. The change ensures that the "last resort" backend is only called when appropriate. This improves reliability by preventing the local model (which has high latency due to loading) from being called when faster, free Heimdall models are available.
*   **Cron Job:** N/A.
*   **Memory Leaks:** The `order` method creates new lists on each call. This is standard Python practice and does not leak memory. The lists are small (number of backends).
*   **Logging:** The code does not add new logging. However, the `note` field in `providers.json` is updated to explain the `last_resort` behavior, which aids debugging and understanding.

**Performance Note:** The `order` method is called for every request. The list comprehensions are O(N) where N is the number of backends. This is negligible.

---

## SECTION 6: WORLD-CLASS GAP ANALYSIS

**Gap: None.**

This is a surgical fix for a specific, high-impact ordering bug. The implementation is clean, well-tested, and adheres to the complex governance laws of the system. There is no "Bloomberg Terminal" feature missing here because this is a backend routing logic fix, not a user-facing feature. The quality of the test suite (`test_r124.py`) is high, covering edge cases and integration with the real config.

**One minor observation:** The `note` field in `providers.json` is very long. While informative, it might be better to keep the JSON config concise and move detailed explanations to a separate `README` or `docs` file. However, this is a style preference, not a functional gap.

---

## SECTION 7: SCORES

*   **Backend logic:** 100/100
*   **Frontend/UI:** N/A
*   **Error handling:** 100/100
*   **Security:** 100/100
*   **Performance:** 100/100
*   **Law compliance:** 100/100
*   **World-class gap:** 100/100
*   **OVERALL:** 100/100

---

## SECTION 8: PRIORITY ACTION PLAN

**No actions required.**

The code is ready for production. The fix is correct, compliant, and well-tested.

---

## SECTION 9: THE ONE THING

The test `test_the_real_chains_keep_ruling_118s_order_whatever_the_meter_says` is the most valuable part of this diff; it proves that the fix works not just in isolation, but against the actual production configuration, ensuring that the "last resort" behavior is correctly applied to the real backends.

---

## SECTION 10: FINAL VERDICT

**Ready for production.**

The code correctly implements the required ordering logic for the spend meter and last-resort backends. It is compliant with all governing laws, secure, and well-tested. No changes are needed.