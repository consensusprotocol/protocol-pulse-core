# qwen3.8-27b (qwen/qwen3.8-27b) 39 s finish=stop usage in 13949 / out 2584 usd_reported=0.002491 usd~0.081 (upper-bound price)

I will review the code changes for `RULING 118` (The Day Cap) against the provided laws and technical constraints.

### Analysis

**1. Logic of `Router._capped` and `_basis_total` (pipeline/providers.py)**
*   **`_capped`**: Checks if the vendor part of the backend name (before `:`) is in `self.uncapped`.
    *   *Observation*: The ledger keys are formatted as `vendor:model` (e.g., `heimdall:qwen...`). The split logic `name.split(":", 1)[0]` correctly extracts the vendor.
    *   *Law Check*: Complies with M12 (Fail Closed) implicitly by defaulting to capped if not in the list.
*   **`_basis_total`**:
    *   **Reported Basis**: Sums `usd_reported` for capped backends + `usd_unreported_estimate` (whole).
        *   *Logic*: If a backend is uncapped (Heimdall), its `usd_reported` is excluded from the sum. The `usd_unreported_estimate` is added in full. The comment states: "the unreported estimate keeps no vendor split, so all of it counts (the stricter reading)".
        *   *Risk*: If Heimdall calls are the *only* source of unreported estimates (unlikely, as Heimdall is local/free and usually reports usage or is estimated differently), this might over-count. However, the prompt says "Heimdall... are free... recorded in the ledger but never capped". If Heimdall calls *do* contribute to `usd_unreported_estimate`, counting them against the $1.00 cap for *outside* vendors is a conservative (safe) error, not a leak. It prevents passing the cap. This is acceptable under "Fail Closed".
    *   **Estimate Basis**: Sums `usd_estimate` for capped backends only.
        *   *Logic*: Uncapped backends are excluded. This aligns with the goal of capping only outside vendors.

**2. Logic of `Router._reserve` (pipeline/providers.py)**
*   **Change**: `if not self.spend_path or b.free() or not self._capped(b.name): return None`
*   **Effect**: If the backend is uncapped (Heimdall), `_reserve` returns `None` immediately.
*   **Implication**: No reservation is made for Heimdall calls. This means Heimdall calls do not block other calls due to reservation limits, nor do they count towards the `limit_usd` check in `_reserve` (since `_reserve` is the gatekeeper for "can I start this call?").
*   **Law Check**: Complies with RULING 118(b) "Heimdall... are free... never reserved".

**3. Day Ledger Logic (tests/package/proof_ly.py)**
*   **`day_ledger`**:
    *   Calculates the start of the current "day" (21:10 ET).
    *   If `now` is before 21:10 ET today, it uses yesterday's 21:10 ET as the start.
    *   Special case: If the start date is `20261115`, it returns `SPEND_B4.json`.
    *   Otherwise, it returns `SPEND_D{YYYYMMDD}.json`.
*   **Boundary Check**:
    *   `t < start`: If current time is 20:00 ET, `start` is 21:10 ET *yesterday*.
    *   `start.strftime("%Y%m%d")`: This gets the date of the *start* of the period.
    *   *Scenario*: Nov 16, 05:40 ET.
        *   `t` = Nov 16 05:40.
        *   `start` (initial) = Nov 16 21:10.
        *   `t < start` is True.
        *   `start` becomes Nov 15 21:10.
        *   `start.strftime` = "20261115".
        *   Returns `SPEND_B4.json`.
    *   *Scenario*: Nov 16, 21:10 ET.
        *   `t` = Nov 16 21:10.
        *   `start` (initial) = Nov 16 21:10.
        *   `t < start` is False.
        *   `start` remains Nov 16 21:10.
        *   `start.strftime` = "20261116".
        *   Returns `SPEND_D20261116.json`.
*   **Correctness**: The logic correctly handles the 21:10 boundary. The "first day" hardcode for `20261115` is a specific migration step for the batch 4 ledger, which is documented and tested.

**4. Shadow Logic (tests/package/proof_ledger.py)**
*   **`build_shadow`**:
    *   Filters `routing.shadow` to keep only entries where the vendor part is in `PL.UNCAPPED`.
    *   `PL.UNCAPPED` is `("heimdall",)`.
    *   This effectively removes all outside vendor shadows (like Grok/xAI) from the shadow list, keeping only Heimdall shadows.
    *   *Law Check*: Complies with RULING 118(a) "no outside shadow".

**5. Tests**
*   **`test_ruling_118_heimdall_is_recorded_but_never_capped`**:
    *   Verifies `spent()` excludes Heimdall.
    *   Verifies Heimdall calls are not reserved/refused.
    *   Verifies outside calls are refused when cap is hit.
    *   Verifies ledger recording still happens for Heimdall.
*   **`TestRuling118TheBuildsRouterCapsOnlyOutsideVendors`**:
    *   Integrates with the build router.
    *   Checks that Heimdall runs past the cap.
    *   Checks that outside calls are refused at the cap.
*   **`test_ruling_118_each_day_keeps_its_own_ledger_from_21_10_et`**:
    *   Validates the `day_ledger` function boundaries.

**6. Potential Issues / Findings**

*   **[P2] `usd_unreported_estimate` handling in `_basis_total` (Reported Basis)**:
    The code adds the *entire* `usd_unreported_estimate` to the capped total. If Heimdall calls generate unreported estimates (e.g., if the local model doesn't report usage and the system falls back to an estimate), those dollars would count against the $1.00 outside vendor cap.
    *   *Mitigation*: The prompt states "Heimdall... are free". If Heimdall is truly free, its cost should be $0. If the system estimates a cost for Heimdall (e.g., electricity/compute cost), it is arguably correct to *not* count it against the *outside vendor* API cap. However, the current implementation *does* count it (via the "stricter reading" comment).
    *   *Impact*: This is a "Fail Closed" behavior. It might cause the system to stop outside calls earlier than necessary if Heimdall estimates are high. It does *not* allow outside calls to exceed the cap. Therefore, it is safe but potentially suboptimal. Given the "Fail Closed" law (M12), this is acceptable. I will flag it as P2 for clarity, but it is not a P1/P0.

*   **[P3] Hardcoded Date in `day_ledger`**:
    `FIRST_DAY = "SPEND_B4.json"` and the check `if start.strftime("%Y%m%d") == "20261115"`.
    This is a temporary migration hack. Once the system moves past Nov 15, 2026, this branch will never be taken. It is safe but will become dead code. The comment explains it. Acceptable for a specific ruling implementation.

*   **[P3] `uncapped` default**:
    `uncapped=()` in `Router.__init__`. This ensures backward compatibility. If `uncapped` is not provided, all backends are capped. This is correct.

*   **[P1] Check: Does `_reserve` correctly skip uncapped backends?**
    Code: `if not self.spend_path or b.free() or not self._capped(b.name): return None`
    If `b.name` is `heimdall:q`, `_capped` returns `False` (because `heimdall` is in `uncapped`). `not False` is `True`. The condition is `True`. It returns `None`.
    This means **no reservation** is made.
    Later, when the call completes, `spent()` is updated.
    Does `spent()` include Heimdall?
    `_basis_total` excludes Heimdall from the sum.
    So `spent()` returns the sum of *capped* backends.
    The check `spent + reserved + upper_bound > limit_usd` happens in `_reserve` for *capped* backends.
    For *uncapped* backends, `_reserve` returns `None` immediately, so the check is skipped.
    This is correct. Heimdall calls are never blocked by the cap.

*   **[P1] Check: Can an outside call pass the cap?**
    Outside call (e.g., `xai:g`). `_capped` returns `True`.
    `_reserve` proceeds.
    It checks `self.spent() + self._reserved_total() + upper_bound > self.limit_usd`.
    `self.spent()` uses `_basis_total`, which sums `usd_reported` for capped backends.
    If the sum exceeds the limit, `SpendLimit` is raised.
    This prevents the outside call from starting if the cap is reached.
    This is correct.

*   **[P2] `build_shadow` logic**:
    `shadow = {k: v for k, v in (shadow or {}).items() if str(v).split(":", 1)[0] in PL.UNCAPPED}`
    `PL.UNCAPPED` is `("heimdall",)`.
    This filters the shadow dict.
    If a shadow entry is `xai:grok`, `str(v).split(":", 1)[0]` is `xai`. `xai` is not in `("heimdall",)`. So it is removed.
    If a shadow entry is `heimdall:qwen`, `str(v).split(":", 1)[0]` is `heimdall`. It is kept.
    This is correct.

**Conclusion**:
The implementation correctly enforces RULING 118.
1.  Outside vendors are capped at $1.00/day.
2.  Heimdall is uncapped (no reservation, not counted in `spent()`).
3.  Heimdall is still recorded in the ledger.
4.  The day ledger rotates at 21:10 ET.
5.  Shadows are filtered to exclude outside vendors.

No P0 or P1 defects found. The P2 regarding `usd_unreported_estimate` is a conservative choice that aligns with "Fail Closed".

P1_OR_WORSE: 0