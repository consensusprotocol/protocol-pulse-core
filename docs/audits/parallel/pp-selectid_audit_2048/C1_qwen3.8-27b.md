# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 19629 / out 2158 usd~0.091 (upper-bound price)

# Code Audit: pp-selectid-2048

## P0 Findings

**1. `pipeline/providers.py` (lines 207-210): Race condition in `_within` allows double-booking or missed booking**
The check `if not done.is_set()` inside the lock is racy. If the worker thread sets `done` *just before* the main thread acquires the lock, the main thread sees `done.is_set() == True` and skips the `abandon()` call. However, the worker thread has already finished and will check `late = "abandoned" in box`. Since `box["abandoned"]` was never set (because the main thread skipped it), `late` is `False`, and `on_late` is never called.
*   **Scenario:** A call times out. The worker thread finishes at `T+0.001s`. The main thread wakes from `done.wait()` at `T+0.002s`. It acquires the lock. `done.is_set()` is `True`. It does **not** raise `DeadlineExceeded` and does **not** call `abandon()`. It proceeds to `if "error" in box` or `return box["value"]`.
*   **Result:** The call is treated as successful (or failed with its own exception), but **no spend is booked** for the prompt tokens, and **no late answer logic** runs. This violates Ruling 83(a) ("booked at its prompt tokens") and Law M12 (fail closed/accurate accounting). The ledger will be under-reported.
*   **Fix:** The `abandon` logic must be triggered by the *timeout* event, not by the state of the worker thread at the moment the main thread wakes. The current structure conflates "worker finished" with "deadline passed".

**2. `pipeline/providers.py` (lines 254-259): Ledger arithmetic error in `_late` for unreported estimates**
In `_late`, when a late answer arrives without a vendor figure (`rep` is None):
```python
d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
# ...
else:
    d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
```
The code subtracts the initial `booked` amount (prompt tokens) and adds the new `usd` (full estimate). This is correct *if* `booked` was the only thing added to `usd_unreported_estimate` for this call. However, `abandon()` calls `self._settle(key, b, {"in": 0, "out": 0}, booked, role)`. We must verify `_settle` adds to `usd_unreported_estimate`. Assuming it does, the math holds.
*   **BUT:** Look at line 259: `d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)`. If `booked` is larger than the current `usd_unreported_estimate` (e.g., due to floating point or previous errors), this can go negative. More critically, if the vendor *does* report a figure, the code does:
    ```python
    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) - booked, 6)
    # ...
    if _num(rep):
        # ... adds to usd_reported
    else:
        d["usd_unreported_estimate"] = round(d["usd_unreported_estimate"] + usd, 6)
    ```
    This logic is sound *only* if `abandon()` correctly added `booked` to `usd_unreported_estimate`. If `abandon()` failed or was skipped (see P0 #1), this subtraction will corrupt the ledger.

**3. `pipeline/attest.py` (lines 44-46): `class_84` filler detection is position-dependent and fragile**
```python
drop = {i for _tag, a, b, _c, _d in ops for i in range(a, b) if r[i] in FILLERS}
```
This drops fillers from the *spoken* side (`r`) based on the *original* diff opcodes. However, `r` is the canonicalized spoken text. If a filler is part of a larger substitution block (e.g., spoken: "um the", approved: "the"), the opcode might be `replace` or `insert`. If it's `insert`, `r[i]` is the filler. If it's `replace`, `r[i]` might be "um" and `p[j]` might be "the". The code drops `r[i]` if it's a filler. This seems correct for "filler on spoken side only".
*   **Issue:** What if the filler is *not* in a separate opcode but part of a `replace` where the other side is also a filler? E.g., spoken: "um", approved: "uh". Both are fillers. `drop` will contain the index of "um". `r2` will be empty. The diff of `r2` vs `p` will show "uh" as an insert. `carry_class` will be called. Is "uh" a function word? No. Is it a repetition? No. It will likely return `None` (hold). This is correct per Ruling 84 (fillers on approved side alone hold).
*   **However:** The logic `one += k is not None` (line 58) is buggy. `k` is a string or `None`. `k is not None` is a boolean. `one` is an integer. `one += True` works in Python, but it's confusing. More importantly, if `k` is `None`, `one` is not incremented. If `k` is "one function word", `one` is incremented. This tracks the count of "one function word" classes. The check `one == 0` ensures only the *first* such difference is allowed. This logic is correct but obscure.

## P1 Findings

**4. `pipeline/providers.py` (lines 196-203): `on_late` exception handling swallows errors**
```python
if late and on_late is not None:
    try:
        on_late(box["abandoned"], box.get("value"), box.get("error"))
    except Exception:
        pass
```
If `on_late` raises an exception (e.g., due to a ledger write failure), it is silently ignored. This violates Law M12 (fail closed). A failure to update the ledger should be logged or raised, not swallowed. The comment says "the booking stands", but if the *replacement* fails, the ledger is left in an inconsistent state (booking present, but no late answer recorded).

**5. `pipeline/lock_precheck.py` (lines 112-114): `decide` uses `class_84` but `attested` uses `row["differences"]`**
`decide` returns `differences` from `class_84`. `attested` uses `row["differences"]`. This is consistent. However, `attested` also uses `row["spoken_text"]`. If `decide` returns `verdict: "adopt"`, `spoken_text` is the second recogniser's text. This is correct per Ruling 84(b).

**6. `tests/providers/test_providers.py` (lines 481-483): Test assertion is fragile**
```python
booked = slow.prompt_usd("p")
self.assertAlmostEqual(booked, 201 * 10 / 1e6, places=9)
```
This hardcodes `201` tokens. `prompt_tokens_upper` counts characters + 200. If the prompt "p" is 1 char, tokens = 1 + 200 = 201. This is correct for the test, but brittle if the prompt changes.

## P2 Findings

**7. `pipeline/attest.py` (line 22): `FILLERS` is a `frozenset` of strings**
The ruling says "canon tokens". `class_84` uses `r[i] in FILLERS`. `r` is a list of canonical tokens. This is correct.

**8. `pipeline/providers.py` (line 154): `prompt_tokens_upper` is a `@staticmethod`**
It doesn't use `self`. This is fine, but `upper_usd` and `prompt_usd` are instance methods that call it. Consistent.

## SHIP: NO

**Reasons:**
1.  **P0 #1:** The race condition in `_within` can lead to missed bookings, violating Ruling 83(a) and Law M12. The ledger will be inaccurate.
2.  **P0 #2:** The ledger arithmetic in `_late` is dependent on the correctness of `abandon()`, which is racy.
3.  **P1 #4:** Swallowing exceptions in `on_late` violates fail-closed principles.

**Conditions for Ship:**
*   Fix the race condition in `_within` by ensuring `abandon()` is called *only* if the deadline has passed, regardless of the worker thread's state. Use a separate flag or event for "deadline passed".
*   Add logging or re-raise exceptions in `on_late` to ensure ledger consistency.
*   Verify that `_settle` correctly updates `usd_unreported_estimate` when `abandon()` is called.