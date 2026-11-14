# qwen3.8-27b (qwen/qwen3.8-27b) 103 s finish=stop usage in 20972 / out 3317 usd~0.113 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
## Feature: pp-selectid-1057

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I focused heavily on the trial-hold duration and the `BreakerUnreadable` fail-open behavior. I missed or under-weighted the following:

1.  **The "Late Runaway" Race (Grok/Glm insight):** I noted the late runaway check exists but did not fully trace the interaction between the *immediate* miss record and the *late* runaway record. If a call misses its deadline (recorded as `miss`), and then the vendor returns a response that is a runaway, the `record("runaway")` call in `_late` (providers.py:206) will see `until is None` (if the breaker wasn't opened by the miss yet) or `now < until` (if it was).
    *   *Correction:* Actually, looking at `circuit_breaker.py:139`, if `until is not None and now >= until`, it re-opens. If `until is None` (closed), it goes to line 145. If the breaker is OPEN (from a previous miss), and the late answer arrives *inside* the open window, line 139 is false (`now < until`), line 145 is false (`until is not None`). The event is **discarded**. This is correct behavior (calls in flight when it opened are ignored), but it means a runaway that happens *during* the open window does not extend the window. This is per ruling ("calls in flight... are ignored"). I missed explicitly verifying that a late runaway *does not* extend the open window, which is a subtle correctness point.

2.  **The `max_out` Calculation for Late Runaways (Glm insight):** I assumed `max_out` was always available. In `_late` (providers.py:204), `cap = ab.get("max_out")`. `ab` is the "abandoned" dict returned by `_within`. I need to verify that `_within` actually populates `max_out` in the exception context or the returned dict.
    *   *Verification:* In `providers.py:1289`, the `ab` dict is created: `return {"backend": b, ..., "max_out": b.max_out(max_tokens)}`. This is the *successful* path.
    *   *Critical Check:* What happens on the *failure* path (DeadlineExceeded)?
    *   Looking at `providers.py:1295-1297`: `except DeadlineExceeded as e: ... self._breaker(role, name, "miss", ..., max_out=b.max_out(max_tokens))`.
    *   So the *miss* record has `max_out`.
    *   But what about the *late* runaway? `_late` is called with `(text, usage, seconds)`. It does *not* receive `max_out` directly. It relies on `ab.get("max_out")`.
    *   *Where does `ab` come from in `_late`?*
    *   In `providers.py:1291-1292`: `text, usage, secs = _within(dl, lambda: b.complete(...), ...)`.
    *   If `_within` raises `DeadlineExceeded`, the `ab` dict is *not* created in the `try` block. The `except` block handles it.
    *   However, `_late` is called by the *thread* that was abandoned. Does the thread have access to `ab`?
    *   Looking at `_within` implementation (not in diff, but described in BACKGROUND): "the abandoned call keeps running in its own thread and, if it ends, calls Router._late (:934) with (text, usage, seconds) or an error."
    *   The BACKGROUND says `_late` receives `(text, usage, seconds)`. It does *not* mention `ab` or `max_out`.
    *   *Code Check:* `providers.py:204` `n_out, cap = usage.get("out"), ab.get("max_out")`.
    *   If `ab` is not passed to `_late`, this line will fail or `ab` will be undefined/stale.
    *   *Wait:* The diff shows `providers.py:204` inside a block. Let's look at the context.
    *   The diff at `providers.py:200-207` is inside a method. Which method?
    *   The diff header says `@@ -947,6 +952,10 @@ class Router:`. This is likely inside `_late` or a helper called by `_late`.
    *   If `_late` does not have `ab` in scope, this is a **NameError** or **KeyError**.
    *   *Re-reading BACKGROUND:* "Router._late (:934) with (text, usage, seconds) or an error."
    *   If `_late` signature is `def _late(self, role, b, text, usage, seconds)`, then `ab` is not defined.
    *   *However*, the diff at `providers.py:1289` adds `"max_out": b.max_out(max_tokens)` to the return dict of the *successful* leg setup.
    *   Does `_late` receive this dict?
    *   The BACKGROUND says `_within` raises `DeadlineExceeded`. The `except` block at `:1295` handles the miss.
    *   The *late* answer comes from the thread. The thread calls `_late`.
    *   If `_late` does not have access to the `ab` dict (which contains `max_out`), then `ab.get("max_out")` at `:204` is a bug.
    *   *Hypothesis:* The `ab` variable in `:204` might be a parameter passed to the function containing that code.
    *   Let's check the function signature in the diff. The diff doesn't show the `def` line for the function containing `:204`.
    *   But `:204` is in the `@@ -947,6 +952,10 @@` hunk.
    *   If this code is in `_late`, and `_late` doesn't take `ab`, it's broken.
    *   *Alternative:* Maybe `ab` is a global or self attribute? Unlikely.
    *   *Most likely:* The code at `:204` is in a function that *does* receive `ab`.
    *   Let's look at `providers.py:1291`. `text, usage, secs = _within(...)`.
    *   If `_within` succeeds, it returns `text, usage, secs`. It does *not* return `ab`.
    *   The `ab` dict is created *before* the call at `:1289`? No, `:1289` is the `return` of the *setup* function?
    *   Actually, `:1289` is inside the `try` block of the main loop?
    *   Let's trace:
        1.  `:1263` `dl = ...`
        2.  `:1266` `bwhy = self._breaker_allow(...)`
        3.  `:1270` `upper = ...`
        4.  `:1271` `key = self._reserve(...)`
        5.  `:1272` `if isinstance(b, HeimdallBackend):`
        6.  `:1289` `return {"backend": b, ..., "max_out": ...}`
    *   This `return` at `:1289` suggests this is a helper function that *prepares* the call, not the call itself.
    *   If this helper returns `ab`, and the caller uses `ab` to make the call, and passes `ab` to `_late`...
    *   The BACKGROUND says `_late` is called with `(text, usage, seconds)`.
    *   If the diff at `:204` is in `_late`, and `_late` doesn't have `ab`, it's a **CRITICAL** bug.
    *   *However*, the test `test_a_late_answer_that_ran_away_opens_it` (test file:563) passes.
    *   The test uses `Slow` backend. `Slow` likely simulates the delay.
    *   If the test passes, `ab` must be accessible.
    *   *Conclusion:* I missed verifying the scope of `ab` in `_late`. The test passing suggests it works, but I should flag it as a potential fragility if `_late`'s signature changes. *Actually*, looking at the diff, `:204` is in a hunk that modifies an existing function. If that function is `_late`, and `ab` is not a parameter, it's a bug. If the test passes, `ab` must be defined. I will mark this as **<high>** for lack of clarity/robustness, but not critical since tests pass.

3.  **The `summary()` Lock Release (Glm insight):** I noted `summary` takes the lock. I missed that `summary` releases the lock *before* computing `open_now` from the snapshot. This is correct (avoids holding lock during computation), but I didn't explicitly verify that `s` is a deep copy or that the snapshot is consistent. `_load` returns a dict. `json.load` creates a new object. So `s` is a snapshot. Safe.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **Grok (SHIP yes):** I agree. The core logic is sound. The trial hold fix addresses the main C1 concern.
*   **Qwen (SHIP no):** I **disagree** with the "M12 Fail Closed" critical. The breaker is an optimization, not a gate. Failing open (skipping nothing) is the correct behavior for an unreadable state file, as it preserves the existing failover chain. Failing closed would cause an outage.
*   **GLM (No SHIP line):** I agree with its observation on the trial hold. The fix (using `hold_s`) is correct. I agree with its observation on `EVENTS_KEPT`.

## 3. NEW FINDINGS FROM THIS REVIEW

1.  **<high> `providers.py:204` Scope of `ab`:** The code `cap = ab.get("max_out")` in the late-runaway check relies on `ab` being in scope. If this code is in `_late`, and `_late` does not receive `ab` as a parameter, this is a `NameError`. The test passes, implying `ab` is available (perhaps via closure or a different function structure), but this is fragile. If `_late` is refactored, this breaks.
    *   *Sequence:* `_late` is called. `ab` is not defined. `NameError` is raised. The late runaway is not recorded. The breaker does not open for a runaway that only manifests late.
    *   *Mitigation:* Ensure `max_out` is passed to `_late` or stored in `self` per call.

2.  **<medium> `circuit_breaker.py:111` Trial Hold Calculation:** `now < (tu or ta + timedelta(seconds=TRIAL_HOLD_S))`. If `tu` is `None` (malformed), it falls back to `ta + TRIAL_HOLD_S`. This is correct. However, if `ta` is `None` (malformed), `ta + ...` raises `TypeError`.
    *   *Sequence:* State file has `trial_at: null`. `allow` is called. `ta` is `None`. `tu` is `None`. `tu or ta + ...` evaluates `ta + ...`. `None + timedelta` raises `TypeError`.
    *   *Impact:* `allow` raises `TypeError`. The caller (`_breaker_allow`) catches `OSError` and `BreakerUnreadable`, but **not** `TypeError`. The exception propagates to `Router.call`, potentially crashing the build.
    *   *Fix:* Guard against `ta is None`.

3.  **<medium> `providers.py:232` `hold_s` Calculation:** `hold_s=deadline_s + 60.0 if _num(deadline_s) else None`. If `deadline_s` is `None`, `hold_s` is `None`. `CB.allow` uses `TRIAL_HOLD_S` (15 min). This is correct. If `deadline_s` is a valid number, `hold_s` is `deadline_s + 60`. This is correct.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Circuit Breaker Logic | 8/10 | 9/10 | Trial hold fix is solid. Minor edge case in `allow` with malformed `trial_at`. |
| Provider Integration | 7/10 | 8/10 | Late runaway logic is correct but relies on `ab` scope. Miss recording is correct. |
| Concurrency | 9/10 | 9/10 | Locking is correct. Atomic write is correct. |
| Tests | 8/10 | 9/10 | Tests cover the main paths. Missing test for malformed `trial_at`. |

## 5. FINAL PRIORITY LIST

*   **P1 HIGH:** `providers.py:204` — Verify `ab` is in scope in `_late`. If not, pass `max_out` to `_late`.
*   **P2 MEDIUM:** `circuit_breaker.py:111` — Guard against `ta is None` to prevent `TypeError` on malformed state.
*   **P2 MEDIUM:** `tests/providers/test_circuit_breaker.py` — Add test for malformed `trial_at` (null) to ensure `allow` does not crash.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Ensure that the `max_out` cap is reliably available in the `_late` handler for runaway detection, as a missing cap would silently disable the runaway breaker for late-arriving responses.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1.  Verify that `ab` is defined in the scope of the code at `providers.py:204`. If it is not, refactor to pass `max_out` to `_late`.
2.  Add a guard in `circuit_breaker.py:111` to handle `ta is None` gracefully (treat as no trial in flight).
3.  Add a test for the malformed `trial_at` case.