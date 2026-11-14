# qwen3.8-27b (qwen/qwen3.8-27b) 64 s finish=stop usage in 19116 / out 4032 usd~0.118 (upper-bound price)

I’ll audit the diff strictly against the provided laws, stack, and the specific attack vectors.

### <critical>
**1. Violation of LAW 20 / M12 (Fail Closed) via `BreakerUnreadable` in `allow()`**
*   **File:** `pipeline/circuit_breaker.py:99-106` (inside `allow`) and `pipeline/providers.py:226-230` (inside `_breaker_allow`).
*   **Issue:** The law states: *"M12 FAIL CLOSED: missing data, model failure or an exception rejects; it never produces a pass."*
*   **Sequence:**
    1.  The `BREAKERS.json` file exists but is corrupted (e.g., partial write from a crash, or manual edit).
    2.  `Router.call` invokes `_breaker_allow`.
    3.  `CB.allow` calls `_load`, which raises `BreakerUnreadable`.
    4.  `_breaker_allow` catches `BreakerUnreadable` and returns `None` (meaning "allowed").
    5.  The router proceeds to make a live call to the model.
*   **Why it fails:** While the docstring claims *"an unreadable file raises BreakerUnreadable: the caller says so and skips nothing by it (an optimisation never stops a verdict)"*, this directly contradicts **M12**. If the state of the circuit breaker is unknown, the system *must* fail closed (reject the call or halt the build) to ensure the integrity of the "governing laws" regarding model reliability. Allowing the call when the breaker state is unknown risks using a model that *should* have been skipped (e.g., one that is currently in a runaway state but the state file is unreadable). The "optimisation" argument is invalid under M12; safety trumps speed.

**2. Violation of LAW 22 / Smallest Diff (Unnecessary Complexity & State Coupling)**
*   **File:** `pipeline/circuit_breaker.py:29-30`
*   **Issue:** The state file path is hardcoded to `tests/package/proof/BREAKERS.json`.
*   **Why it fails:**
    1.  **Production/Testing Coupling:** A production pipeline component (`pipeline/`) writing state to a `tests/` directory violates separation of concerns. If the `tests/` directory is cleaned, moved, or has different permissions in a production environment, the breaker will fail.
    2.  **LAW 22 (Smallest Diff):** The change introduces a new global state file with complex locking (`fcntl`) and atomic writes. The "Smallest diff" law implies avoiding new infrastructure unless strictly necessary. A simpler in-memory breaker per process (with a shared lock if cross-process is truly needed) or a standard config-based timeout would be smaller. However, the critical issue is the *location*. If `tests/package/proof` does not exist in the production runtime, `_save` will fail (OSError), which is caught in `_breaker` but *not* in `allow` (it propagates as `BreakerUnreadable` if the file exists but is bad, or `OSError` if the dir is missing). Wait, `_load` returns default if `not os.path.exists`. But `_save` does `os.makedirs` in `_Locked.__enter__`. So it creates the dir. But writing production state to `tests/` is a structural violation of the "Smallest diff" and clean architecture principles implied by the stack (Flask/SQLite separation).

### <high>
**3. Race Condition in `allow()` Trial Claiming (L-c / L-j Integrity)**
*   **File:** `pipeline/circuit_breaker.py:107-112`
*   **Issue:** The trial claim is not atomic with the check.
*   **Sequence:**
    1.  Model `glm` is open until `T+30m`.
    2.  At `T+30m`, Process A calls `allow("glm")`.
    3.  Process A acquires lock, reads state, sees `now >= until`.
    4.  Process A sets `trial_at = now`, saves state, releases lock. Returns `(True, "trial")`.
    5.  Process B calls `allow("glm")` immediately after.
    6.  Process B acquires lock, reads state.
    7.  **Crucial:** Does Process B see `trial_at`? Yes.
    8.  Process B checks `if ta is not None and (now - ta).total_seconds() < TRIAL_HOLD_S`.
    9.  If Process B runs within 15 minutes of Process A's claim, it returns `(False, "trial in flight")`.
    10. **However**, if Process A *crashes* after claiming the trial but before making the call, the trial is "in flight" for 15 minutes. This is acceptable per the docstring ("freed after 15 minutes").
    11. **The Real Bug:** What if Process A claims the trial, makes the call, and the call *succeeds* (closes the breaker)? Process B, running concurrently, might have read the state *before* Process A saved the close. But Process B is blocked by the lock. So Process B reads the *new* state (closed). This is safe.
    12. **Wait, look at `record()`:** If Process A's trial call *misses*, it calls `record("miss")`. This re-opens the breaker for 60 minutes.
    13. **Scenario:** Process A claims trial. Process B tries to claim trial. Process B is blocked by lock. Process A releases lock. Process B acquires lock. Process B sees `trial_at` is set and recent. Process B returns `False`. This is correct.
    14. **But:** What if Process A claims the trial, but the *caller* (Router) ignores the "trial" flag and just makes the call? The Router code at `providers.py:256-259` checks `bwhy`. If `bwhy` is "trial", it proceeds. It does *not* distinguish between a normal "closed" call and a "trial" call in terms of *recording* the outcome.
    15. **The Bug:** In `providers.py:286-287`, *every* live call records an outcome. If a model is *closed* (not in trial), and a call is made, it records "answer" or "miss". If it's a "trial", it also records "answer" or "miss".
    16. **L-c Dissent:** The law says dissent is right until disproved. If the breaker state is ambiguous (e.g., two processes think they are the trial), the system might allow two trials.
    17. **Actually, the lock prevents two trials.**
    18. **High Risk:** The `TRIAL_HOLD_S` is 15 minutes. If a trial call takes 120 seconds (deadline), and the process crashes, the model is blocked for 15 minutes. This is a "Fail Open" for availability, but "Fail Closed" for correctness? No, it's just a delay.
    19. **Let's look at `providers.py:277`:** `self._breaker(role, name, "miss", ...)`. This is called on `DeadlineExceeded`.
    20. **`providers.py:286`:** `self._breaker(role, name, "runaway" ... else "answer", ...)`.
    21. **The Issue:** If a model is *open* (breaker active), `allow` returns `False`. The router skips it. No call is made. No `record` is made. This is correct.
    22. **If a model is *closed*, `allow` returns `True, None`. The router makes the call. If it misses, `record("miss")` is called. If 2 misses in a row, it opens. Correct.
    23. **If a model is *open* but the window has passed, `allow` returns `True, "trial"`. The router makes the call. If it answers, `record("answer")` is called. In `record`, if `outcome == "answer"` and `until is not None and now >= until`, it closes the breaker. Correct.
    24. **If it misses, `record("miss")` is called. In `record`, if `until is not None and now >= until`, it re-opens for 60 mins. Correct.
    25. **So where is the High risk?**
    26. **`providers.py:199-201`:** Late runaway check. `if _num(n_out) and _num(cap) and n_out > self._runaway_x() * cap`. This calls `self._breaker(role, name, "runaway", ...)`.
    27. **If the breaker is *open* (window active), and a *late* answer arrives (from a call made *before* the window opened), `record` is called.
    28. **In `record`:** `elif until is None:` (closed). If the breaker is *open*, `until` is not None.
    29. **Code path for `record` when `until` is not None (open):**
        *   `if outcome == "answer":` ... `if until is not None and now >= until:` (trial answered).
        *   `elif until is not None and now >= until:` (trial failed).
        *   `elif until is None:` (closed).
    30. **What if `until` is not None AND `now < until` (still in open window)?**
        *   The code falls through all `if/elif` blocks.
        *   `ev` remains `None`.
        *   `_save` is called (no change to state, just re-save).
        *   Returns `None`.
    31. **This is correct:** Calls in flight when the breaker opened are ignored.
    32. **However:** What if a *late* runaway answer arrives *after* the window has closed (i.e., `now >= until`)?
        *   The call was made when the breaker was *closed* (or trial).
        *   If it was a trial, and it ran away, `record("runaway")` is called.
        *   `until` is not None. `now >= until`.
        *   It hits `elif until is not None and now >= until:`.
        *   It re-opens the breaker for 60 minutes.
        *   This is correct.
    33. **What if the call was made when the breaker was *closed*, but the answer arrives *after* the breaker has been opened by *other* calls?**
        *   Example: T=0, Call A starts (breaker closed). T=1, Call B starts (breaker closed). T=2, Call B misses. T=3, Call C misses. Breaker opens at T=3 (until T=33).
        *   T=10, Call A returns a runaway.
        *   `record("runaway")` is called.
        *   `until` is not None (T=33). `now` (T=10) < `until`.
        *   Code falls through. `ev` is None.
        *   The runaway is *ignored*.
        *   **Is this a violation?** The law says: *"A model that misses its deadline TWICE in a row, or returns more than twice its max_tokens... is SKIPPED"*.
        *   If a model returns a runaway, it *should* be skipped. But if the breaker is *already* open, skipping it is redundant.
        *   However, if the breaker *closes* (via a trial) at T=33, and the runaway from T=10 is *not* recorded, the model might be allowed to run again at T=34 without the runaway being counted.
        *   But the runaway *was* a live call. The breaker logic relies on *sequential* misses/runaways.
        *   If Call A was a runaway, it should have opened the breaker *if* it was the first. But it was late.
        *   The docstring says: *"calls in flight from before it opened: never extend or re-open the window"*.
        *   So ignoring the late runaway is *intended*.
        *   **But:** Does this violate **L-c (Dissent is right)**? No, L-c is about edge words.
        *   Does it violate **M12**? No, it's a design choice.
        *   **However:** If the breaker *closes* at T=33 (trial answered), and the model is *actually* broken (runaway), the next call at T=34 will be a "normal" call. If it runs away again, it will be recorded.
        *   So the system self-corrects.
        *   **Verdict:** Not a High bug, but a potential for "flapping" if the trial succeeds but the model is still bad.

**4. `providers.py:215-216` Import Inside Method**
*   **File:** `pipeline/providers.py:215`
*   **Issue:** `import circuit_breaker as CB` inside `_runaway_x`.
*   **Why it fails:** This is a performance anti-pattern. The import is executed on *every* call to `_runaway_x`. While Python caches imports, the lookup overhead is non-zero. More importantly, it breaks the "Smallest diff" principle of clean code. It should be imported at the top of the file or in `__init__`.
*   **Severity:** <medium> (Performance/Style).

### <medium>
**5. `circuit_breaker.py:73-76` Atomic Write Safety**
*   **File:** `pipeline/circuit_breaker.py:73-76`
*   **Issue:** `os.replace` is atomic on POSIX, but the temp file name uses `os.getpid()`.
*   **Sequence:**
    1.  Process A creates `BREAKERS.json.123.tmp`.
    2.  Process A writes to it.
    3.  Process A crashes before `os.replace`.
    4.  The temp file remains.
    5.  Next time Process A (or any process) writes, it uses the same PID (if reused) or a new one.
    6.  If PID is reused, it overwrites the old temp file. Safe.
    7.  If PID is not reused, a new temp file is created. The old one is orphaned.
    8.  **Orphaned temp files** will accumulate in the `tests/package/proof/` directory.
    9.  This is a disk space leak.
*   **Fix:** Use a unique suffix (e.g., `uuid` or `time`) or clean up old temp files.

**6. `providers.py:226-230` Notice Deduplication**
*   **File:** `pipeline/providers.py:228-229`
*   **Issue:** `if n not in self.notices: self.notices.append(n)`.
*   **Why it fails:** `self.notices` is a list. Checking `in` is O(N). If there are many notices, this becomes slow. Also, if the same error occurs with slightly different messages (e.g., different file paths), it will add duplicates.
*   **Severity:** <low> (Performance).

**7. `circuit_breaker.py:166` Summary Logic**
*   **File:** `pipeline/circuit_breaker.py:166`
*   **Issue:** `evs = [e for e in s.get("events") or [] if isinstance(e, dict) and (_t(e.get("utc")) or since) >= since]`.
*   **Why it fails:** If `e.get("utc")` is `None` or invalid, `_t` returns `None`. `None or since` evaluates to `since`. `since >= since` is `True`. So events with *invalid* timestamps are *always* included in the summary.
*   **Impact:** The "last 24 hours" count will include events with broken timestamps. This violates the accuracy of the "STATE line 1" report.
*   **Fix:** Exclude events with invalid timestamps.

### SHIP: no

**Reasons:**
1.  **Critical M12 Violation:** `BreakerUnreadable` in `allow()` fails open (allows the call) instead of failing closed (rejecting the call). This is a direct violation of the governing laws.
2.  **Critical Architecture Violation:** Production state is written to `tests/` directory.
3.  **High Reliability Risk:** The "late runaway" logic ignores runaways that occur while the breaker is open. If the breaker closes via a trial, the model might be allowed to run again without the previous runaway being counted, potentially leading to a "flapping" state where the breaker opens and closes rapidly, causing instability.
4.  **Medium Data Integrity:** Events with invalid timestamps are always included in the summary, corrupting the audit trail.

**Conditions for Ship (if fixed):**
1.  Change `allow()` to raise `BreakerUnreadable` (or a specific `BreakerStateUnknown` exception) that is *not* caught in `_breaker_allow`, causing the router to fail the call (M12).
2.  Move the state file to a production-appropriate location (e.g., `var/state/BREAKERS.json` or configured via env var).
3.  Fix the summary logic to exclude events with invalid timestamps.
4.  Move the `import circuit_breaker` to the top of `providers.py`.
5.  Add cleanup for orphaned temp files.