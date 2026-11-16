# qwen3.8-27b (qwen/qwen3.8-27b) 70 s finish=stop usage in 8815 / out 5781 usd_reported=0.004532 usd~0.113 (upper-bound price)

I will analyze the provided diff for `pipeline/providers.py` and `tests/providers/test_providers.py` against the specific instructions in "RULING 123 (1)" and the general "Governing Laws" (specifically M12 Fail Closed and Law 20/22 regarding constants and hard stops).

### Analysis of `pipeline/providers.py`

**1. `_reserve_fraction` method (Lines 23-33)**
*   **Logic:** Returns the fraction if `reserve_list_fraction` is in the spec, `_num` is valid, and `spend_path` exists. It checks the ledger for `reserve_tripped`.
*   **Potential Issue:** It accesses `self._ledger()` inside `self._lock()`. This is consistent with other ledger operations.
*   **Fail Closed (M12):** If `spend_path` is None, it returns `None` (which means reserve at list price). This is safe. If the ledger read fails, `_ledger()` likely raises or returns a default. Assuming `_ledger()` is robust (as implied by existing code structure), this is acceptable.

**2. `_settle` method modification (Lines 38-56)**
*   **Logic:** After popping the reservation `held`, it checks if the backend has `reserve_list_fraction`.
*   **Comparison:** `float(usage["usd_reported"]) > float(f) * usd`.
    *   `usd` here is the argument passed to `_settle`. Looking at the call site in `Router.call` (not fully shown but implied by context), `usd` is typically the *list price* estimate or the *actual* cost?
    *   Let's look at the tripwire logic: "compare what was billed with what was reserved... first call that bills above 25 % of list".
    *   The code calculates `float(f) * usd`. If `usd` is the *list price* of the usage, then `0.25 * usd` is the threshold.
    *   The condition is `usage["usd_reported"] > threshold`.
    *   **Critical Check:** Does `usd` passed to `_settle` represent the *list price* of the tokens used?
        *   In `Router.call` (Line 63-66), `upper = b.upper_usd(...)`. This is the list price upper bound.
        *   The reservation `key` is created with `round(upper * frac, 6)`.
        *   When `_settle` is called, it needs to know the *list price* of the actual usage to compare against the fraction.
        *   The code uses `usd` (the parameter). We must verify that `usd` passed to `_settle` is indeed the list price of the *actual* usage, not the reserved amount.
        *   Looking at standard patterns in such routers: `_settle` usually receives the actual cost or the list cost of the actual tokens.
        *   The trip record stores `"list": round(usd, 6)`. This implies `usd` is the list price.
        *   The comparison is `billed > fraction * list`. This matches the ruling: "bills above 25 % of list".
*   **Locking:** The write to `d["reserve_tripped"]` happens *outside* the `self._lock()` block shown in the snippet?
    *   Wait, let's look at the indentation in the diff.
    *   Lines 44-56 are inside the `if backend is not None:` block.
    *   Is this block inside a lock?
    *   The diff shows:
        ```python
        def _settle(self, key, backend=None, usage=None, usd=0.0, role="", unreported=None):
            try:
                # ...
                d["reserved"].pop(key, None) # Line 43
                if backend is not None:
                    usage = usage or {}
                    f = backend.spec.get("reserve_list_fraction")
                    if _num(f) and _num(usage.get("usd_reported")) and ...:
                        # ...
                        d.setdefault("reserve_tripped", {})[backend.name] = trip # Line 54
        ```
    *   The `try` block usually wraps the ledger access. In the previous code (Line 39-41), `d` is obtained. If `d` is a reference to the ledger dict, and the ledger is protected by a lock *during the read/write*, we need to ensure the write to `reserve_tripped` is atomic with the read of `d`.
    *   The diff does *not* show `with self._lock():` around the `d.setdefault...` line.
    *   However, `_reserve_fraction` *does* use `with self._lock(): d = self._ledger()`.
    *   If `_settle` modifies `d` (the ledger) without holding the lock, and another thread calls `_reserve_fraction` (which reads the ledger under lock), there is a **Race Condition**.
    *   **Scenario:**
        1. Thread A calls `_settle`. It reads `d` (ledger). It sees `reserve_tripped` is empty.
        2. Thread B calls `_reserve_fraction`. It acquires lock, reads `d` (ledger). Sees `reserve_tripped` is empty. Returns 0.25.
        3. Thread A (still in `_settle`, no lock held for the write?) calculates the trip. Writes `d["reserve_tripped"][name] = trip`.
        4. Thread C calls `_reserve_fraction`. Acquires lock, reads `d`. Sees `reserve_tripped` is set. Returns None (List).
    *   The danger is if Thread A's write is not synchronized. If `d` is a shared mutable object (the ledger JSON loaded into memory), and `_settle` modifies it without the lock, it could corrupt the ledger or miss the trip for concurrent reads.
    *   **Standard Practice in this codebase:** The comment in `_reserve_fraction` says "under the ledger lock, as every ledger write". This implies `_settle` *should* be holding the lock or the ledger object handles it.
    *   Looking at the diff for `_settle`, it does *not* show a `with self._lock():` block surrounding the modification of `d`.
    *   If `self._ledger()` returns a *copy* or a *file-backed* object that handles locking internally, this might be fine. But `_reserve_fraction` explicitly uses `with self._lock(): d = self._ledger()`. This suggests `self._ledger()` might just return the current state, and the lock is the synchronization primitive.
    *   If `_settle` modifies `d` without the lock, it violates the concurrency safety implied by the rest of the router.
    *   **Severity:** [P1] Race condition / Data Integrity. The tripwire might be missed or the ledger corrupted if `_settle` runs concurrently with `_reserve_fraction` or other ledger writes.

**3. `Router.call` modification (Lines 60-66)**
*   **Logic:** `frac = self._reserve_fraction(b)`. `key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)`.
*   **Correctness:** If `frac` is 0.25, reserve is 25% of list. If `frac` is None (tripped or no spec), reserve is 100% of list. This matches the ruling.

### Analysis of `tests/providers/test_providers.py`

**1. `TestRuling123Reserve`**
*   **Setup:** `ledger` creates a JSON file with `usd_estimate: 0.69`.
*   **Backend:** `grok` with `reserve_list_fraction: 0.25`.
*   **Test Case 1:** `test_a_quarter_of_list_until_a_call_bills_above_it_then_list_for_the_day`
    *   `p = "p" * 3000`.
    *   `g.upper_usd(p, 12000)` is asserted to be `0.3825`.
    *   `r.call("judge", p, 12000)`.
        *   Reserve at 25%: `0.3825 * 0.25 = 0.095625`.
        *   Current spend: `0.69`.
        *   Total: `0.785625 < 1.00`. Call succeeds.
    *   `g._usage` is set to `usd_reported: 0.01`.
    *   `r.call("judge", p, 12000)` (2nd call).
        *   `_settle` runs. `billed = 0.01`. `list = 0.055` (calculated from usage? No, `usd` param in `_settle` is the list price of the *actual* usage).
        *   Wait, the test sets `g._usage`. The `Fake` backend likely uses this to return `usd_reported`.
        *   The `usd` passed to `_settle` must be the list price of the tokens in `g._usage`.
        *   `g._usage` has `in: 1000, out: 2000`.
        *   Price: `5, 25`.
        *   List cost: `1000 * 5/1e6 + 2000 * 25/1e6 = 0.005 + 0.05 = 0.055`.
        *   Threshold: `0.25 * 0.055 = 0.01375`.
        *   Billed: `0.01`.
        *   `0.01 > 0.01375` is **False**. No trip.
        *   Test asserts `reserve_tripped` is `None`. Correct.
    *   `g._usage` is set to `usd_reported: 0.02`.
    *   `r.call("judge", p, 12000)` (3rd call).
        *   Reserve at 25% (since no trip yet): `0.095625`.
        *   Spend `0.69 + 0.095625 < 1.00`. Call succeeds.
        *   `_settle` runs.
        *   List cost of usage: `0.055` (same tokens).
        *   Threshold: `0.01375`.
        *   Billed: `0.02`.
        *   `0.02 > 0.01375` is **True**. Trip occurs.
        *   Test asserts `reserve_tripped` is set. Correct.
        *   Test asserts notice. Correct.
    *   `r.call("judge", p, 12000)` (4th call).
        *   `_reserve_fraction` returns `None` (tripped).
        *   Reserve at List: `0.3825`.
        *   Spend `0.69 + 0.3825 = 1.0725 > 1.00`.
        *   `SpendLimit` raised. Correct.
    *   `day2` router with new ledger.
        *   `day2.call` succeeds. Correct.

**2. Potential Test Flaw / Logic Gap**
*   The test relies on `g._usage` being updated *before* the call to simulate the billing.
*   In `Router.call`, the flow is:
    1.  Check reserve.
    2.  Call backend.
    3.  Get usage.
    4.  Settle.
*   The `Fake` backend `g` is configured with `g._usage`. When `r.call` is invoked, `g.complete` (or similar) returns the answer and usage.
*   The test sets `g._usage` *between* calls. This simulates the backend returning different usage/costs for subsequent calls. This is a valid unit test pattern for this abstraction.

**3. Missing Test: "Cannot be missed"**
*   The prompt asks to check that the tripwire "cannot be missed".
*   The code checks `if _num(f) and _num(usage.get("usd_reported")) and ...`.
*   If `usage` does *not* have `usd_reported` (e.g., free call, or error), the trip is *not* evaluated.
*   Is this correct? "After every outside call compare what was billed...". If nothing is billed (0 or missing), it shouldn't trip.
*   However, if `usd_reported` is missing but the call *did* cost money (e.g., internal error in reporting), the trip is missed.
*   The ruling says "bills above 25%". If it doesn't report a bill, we assume it's 0 or free.
*   M12 Fail Closed: If data is missing, reject. Here, missing `usd_reported` means we don't trip. This is "Fail Open" for the tripwire (we keep the discount).
*   Is this a violation? The discount is a *benefit* to the user (lower reserve). Missing the trip means we *keep* the benefit. This is not a safety failure (like spending too much), it's a financial optimization failure.
*   However, if `usd_reported` is missing, `usage.get("usd_reported")` is `None`. `_num(None)` is likely `False`. So the condition fails. No trip.
*   This seems acceptable for a "reserve" optimization. The hard cap (`limit_usd`) still applies to the *actual* spend if it's reported. If it's not reported, the `SpendLimit` check in `_reserve` might also be affected?
*   `_reserve` uses `upper` (list price) for the reservation. The *actual* spend check happens in `_settle` or the ledger update.
*   If `usd_reported` is missing, the ledger `usd_reported` might not increase?
*   This is outside the scope of the diff, but the tripwire logic itself is sound for the "billed" case.

**4. Concurrency in `_settle` (Revisited)**
*   The diff for `_settle` does *not* show a lock.
*   The diff for `_reserve_fraction` *does* show a lock.
*   If `_settle` writes to the ledger (`d["reserve_tripped"]`) without a lock, and `_reserve_fraction` reads it with a lock, there is a race.
*   **Finding:** [P1] The write to `reserve_tripped` in `_settle` is not protected by `self._lock()`. This can lead to race conditions where the trip is not visible to concurrent `_reserve_fraction` calls, or the ledger JSON is corrupted if `d` is a shared mutable structure.

**5. `usd` parameter in `_settle`**
*   The code uses `usd` (the parameter) to calculate the list price for the trip comparison.
*   `trip["list"] = round(usd, 6)`.
*   `threshold = float(f) * usd`.
*   We must ensure `usd` passed to `_settle` is the **List Price** of the actual usage, not the **Reserved Amount** or the **Billed Amount**.
*   In `Router.call`, `usd` is likely calculated as `b.usd(usage)` (list price).
*   The diff doesn't show the `Router.call` body where `_settle` is invoked, but standard practice and the variable name `usd` (vs `billed` or `reserved`) suggest it is the list price.
*   The test `test_a_quarter...` asserts `trip["list"]` is `0.055`.
*   The usage was `in: 1000, out: 2000`. Price `5, 25`.
*   List price = `0.005 + 0.05 = 0.055`.
*   So `usd` in `_settle` *is* the list price. This is correct.

**6. "Nothing but the named back-end changes"**
*   `_reserve_fraction` returns `None` if `reserve_list_fraction` is not in spec.
*   `Router.call` uses `frac` only if not `None`.
*   `_settle` only checks `f = backend.spec.get("reserve_list_fraction")`. If not present, it skips the trip logic.
*   This is correct.

**7. "The trip holds for the day"**
*   The trip is stored in the ledger file (`led.json`).
*   `_reserve_fraction` reads the ledger.
*   The ledger is "one ledger a day" (per `proof_ly.day_ledger` mentioned in comments).
*   So the trip persists for the day. Correct.

**8. Severity of the Lock Issue**
*   If the ledger is a file, and `self._ledger()` loads it into memory, and `self._lock()` is a `threading.Lock` protecting the in-memory dict `d`...
*   If `_settle` modifies `d` without the lock, and another thread is reading `d` (under lock) or writing `d` (under lock), it's a race.
*   Given `Router` is likely used in a multi-threaded Flask app (1000 concurrent users), this is a **P1** defect.

**9. Minor: `_num` check**
*   `_num(f)` and `_num(usage.get("usd_reported"))`.
*   If `usd_reported` is a string "0.01", `_num` should handle it.
*   If `usd_reported` is `None`, `_num` returns False.
*   This is safe.

**10. Minor: `round(upper * frac, 6)`**
*   Rounding the reserve.
*   `upper` is list price. `frac` is 0.25.
*   This reduces the reserve.
*   Is there a risk of under-reserving?
*   The tripwire corrects this if the actual bill is high.
*   If the actual bill is low, we saved money.
*   This is the intended behavior.

**11. Check: "Gate passing what it must refuse"**
*   The `SpendLimit` is the gate.
*   If the trip is missed (due to race), the reserve stays at 25%.
*   The call might proceed when it should have been refused (if the list reserve would have exceeded the limit).
*   This is a **P0** risk if the race condition allows a call to bypass the spend limit.
*   However, the spend limit is based on `usd_estimate` in the ledger.
*   `_reserve` checks `d["usd_estimate"] + reserve > limit`.
*   If the trip is missed, `reserve` is smaller (25% vs 100%).
*   So `d["usd_estimate"] + 0.25*upper` might be `< limit`, while `d["usd_estimate"] + upper` would be `> limit`.
*   So a call that *should* be refused (because it would exceed the limit at list price) is *allowed* (because it fits at 25% reserve).
*   This violates the "Hard Stop" / "Fail Closed" principle if the tripwire is the mechanism to enforce the limit after a deviation.
*   But wait, the limit is on *spend*. The reserve is a *pre-check*.
*   If the pre-check passes at 25%, the call is made.
*   If the call bills high, the trip is set.
*   The *next* call is refused.
*   The *current* call is not refused.
*   The ruling says: "The worst case is one call's overshoot... I accept that tail".
*   So allowing the call that *trips* the wire is intended.
*   The race condition would allow *subsequent* calls to also use 25% if the trip isn't visible.
*   This could lead to multiple overshoots.
*   Given the "1000 concurrent users" and the race condition in `_settle`, this is a **P1** (or potentially P0 if it leads to significant budget overrun). I will classify it as **P1** because it's a concurrency bug in a financial guard, but the "one call overshoot" is accepted, so a few extra calls might be within the "tail" tolerance, but it's still a defect.

**12. Test Coverage for Race**
*   The tests are single-threaded. They do not catch the race.

**13. `reserve_tripped` structure**
*   `d.setdefault("reserve_tripped", {})[backend.name] = trip`.
*   This is a dict of dicts.
*   `_reserve_fraction` checks `(d.get("reserve_tripped") or {}).get(b.name)`.
*   This is consistent.

**14. `notices`**
*   `self.notices.append(...)`.
*   Is `notices` thread-safe?
*   If `self.notices` is a list, `append` is atomic in CPython (GIL), but reading it might not be.
*   This is a minor concern, usually P3.

**15. `usd` in `_settle` vs `usage`**
*   The code uses `usd` (param) for the list price.
*   It uses `usage["usd_reported"]` for the billed price.
*   This is correct.

**16. `frac` in `Router.call`**
*   `frac = self._reserve_fraction(b)`.
*   `key = self._reserve(b, round(upper * frac, 6) if frac is not None else upper)`.
*   If `frac` is 0.25, `upper * 0.25`.
*   If `frac` is None, `upper`.
*   Correct.

**17. `model_providers.json`**
*   Added `reserve_list_fraction: 0.25` to `xai:grok-4.20-0309-reasoning`.
*   Correct.

**18. `test_providers.py`**
*   `xai` helper updated to pop `reserve_list_fraction` if `frac=False`.
*   `TestRuling121Reserve` updated to use `frac=False` (list price) for its checks.
*   This ensures the old tests don't break due to the new default behavior.
*   Correct.

**19. `TestRuling123Reserve`**
*   `ledger` helper creates a fresh ledger.
*   `grok` helper creates a Fake backend.
*   The test logic is sound.

**20. One subtle bug in `_settle`**
*   `if _num(f) and _num(usage.get("usd_reported")) and float(usage["usd_reported"]) > float(f) * usd and not (d.get("reserve_tripped") or {}).get(backend.name):`
*   If `usd` is 0 (free call?), `float(f) * usd` is 0.
*   If `usd_reported` is > 0, it trips.
*   If `usd` is 0, the list price is 0.
*   This is an edge case.

**21. `usd` parameter default**
*   `def _settle(self, key, backend=None, usage=None, usd=0.0, ...)`
*   If `usd` is not passed, it defaults to 0.0.
*   If `usd` is 0.0, `float(f) * usd` is 0.0.
*   If `usd_reported` is > 0, it trips.
*   But if `usd` is 0, the list price is 0.
*   This might be incorrect if `usd` is not passed but the call had a cost.
*   However, `Router.call` likely always passes `usd`.

**Conclusion:**
The main defect is the lack of locking in `_settle` when writing to the ledger. This is a P1.
The logic for the tripwire and reserve fraction is correct.
The tests are correct for the single-threaded case.

**Findings:**
1.  [P1] Race condition in `Router._settle`: The write to `d["reserve_tripped"]` is not protected by `self._lock()`. Concurrent calls to `_reserve_fraction` (which reads the ledger under lock) may miss the trip, leading to continued use of the 25% reserve after the tripwire should have activated. This can result in exceeding the intended spend limit behavior.
2.  [P3] `self.notices.append` is not explicitly synchronized, though likely safe under GIL for append.
3.  [P3] The test `test_a_quarter...` does not verify that the `reserve_tripped` entry is *persisted* to the file correctly in a multi-threaded scenario, but the single-threaded persistence is tested.

P1_OR_WORSE: 1