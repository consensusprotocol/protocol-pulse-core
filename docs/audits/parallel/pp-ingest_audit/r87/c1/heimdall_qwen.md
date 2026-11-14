# heimdall_qwen (qwen/qwen3.8-27b, 308.4 s, $0.024, finish stop)

## SECTION 1: CORRECTNESS

**1. Race Condition in `DownSignal._seen` (Critical)**
`pipeline/ingest/downsignal.py:253-270`
The `_seen` method reads the shared state file, iterates through new switches, and updates the `signal_switches_seen` counter in the SQLite queue. This is **not atomic**.
- If the process crashes between `spend.write_switch_head` (line 258) and `self.q.kv_set("signal_switches_seen", ...)` (line 270), the switch is written to the STATE file but the counter is not incremented.
- On restart, `_seen` will see the same switch again (because the counter is still at the old value) and **write the switch head to the STATE file a second time**.
- `spend.write_switch_head` (line 208) prepends the new head to the existing switch line. This results in duplicate switch entries in the STATE file's first line, violating the "one physical line" invariant and potentially confusing the orchestrator.
- **Fix:** The counter update must happen *before* or *atomically with* the STATE write, or the STATE write must be idempotent (check if the head is already present). Given the "append-only" nature of the ledger and the "latest wins" logic elsewhere, this specific "prepend to line 1" pattern is fragile.

**2. `DownSignal._flush` Ordering and Heartbeat Interaction**
`pipeline/ingest/downsignal.py:181-196`
The `_flush` method sends `note(True)` for the latest answer and `note(False)` for the first failure *after* that answer.
- The builder's module `heimdall_health.py` has a heartbeat mechanism (`HEARTBEAT_S = 30.0`) that suppresses `note(True)` calls if one was made recently.
- If the watcher sends `note(True)` at T=0, and then a failure occurs at T=10, and the next flush is at T=15, the watcher sends `note(False)` at T=15.
- However, if the builder's process also sends `note(True)` at T=5 (within the 30s heartbeat), the builder's `note(True)` is suppressed.
- The watcher's `note(False)` at T=15 will correctly start the failure clock.
- **Potential Issue:** If the watcher sends `note(True)` at T=0, and the builder sends `note(False)` at T=10, and the watcher's next flush is at T=15, the watcher sends `note(True)` (from T=0) *again*? No, `_flush` clears `self.pending` after sending.
- **Real Issue:** The watcher's `noted` method (line 122) only keeps the *latest* answer and the *first* failure after it. If the sequence is: Answer(T=0), Failure(T=10), Answer(T=20), Failure(T=30).
    - T=0: `pending.answer = 0`, `pending.fail = None`
    - T=10: `pending.fail = 10` (since `pending.fail` was None)
    - T=20: `pending.answer = 20`, `pending.fail = None` (Answer resets fail)
    - T=30: `pending.fail = 30`
    - Flush at T=35: Sends `note(True, now=20)` and `note(False, now=30)`.
    - This is correct. The module will see the answer at 20, then the failure at 30.
    - **However**, if the sequence is: Failure(T=0), Answer(T=10), Failure(T=20).
    - T=0: `pending.fail = 0`
    - T=10: `pending.answer = 10`, `pending.fail = None`
    - T=20: `pending.fail = 20`
    - Flush at T=25: Sends `note(True, now=10)` and `note(False, now=20)`.
    - This is correct.
    - **Edge Case:** What if the failure at T=0 was *before* the last flush? It would have been sent in the previous flush. So this is fine.

**3. `DownSignal._start_probe` and `AllBackendsFailed`**
`pipeline/ingest/downsignal.py:198-213`
If `router.run` raises `AllBackendsFailed`, the code checks if any backend was "unavailable" or "rejected". If so, it reports `answered=False`. If all were "skipped" (e.g., frozen, disabled), it reports `answered=None` (no probe).
- This is correct. A probe that couldn't be made is not a failure of Heimdall.

**4. `spend.write_switch_head` and `NOTICE_RE`**
`pipeline/ingest/spend.py:25-26`
`NOTICE_RE` includes `SWITCH_PATTERN`.
`SWITCH_PATTERN = r"\d\d:\d\d ET: (?:SWITCHED TO PLAN B|BACK TO [A-Z0-9_-]+-FIRST)"`
The `head` function in `downsignal.py:93-95` generates:
`f"{when} ET: {word} ({rec.get('why') or 'no reason recorded'}; BY {rec.get('by') or 'unknown'}" + ...`
If `word` is "SWITCHED TO PLAN B", the line starts with `HH:MM ET: SWITCHED TO PLAN B ...`. This matches `SWITCH_PATTERN`.
If `word` is "BACK TO HEIMDALL-FIRST", the line starts with `HH:MM ET: BACK TO HEIMDALL-FIRST ...`. This matches `SWITCH_PATTERN`.
- **Correct.**

**5. `DownSignal._seen` and `int(seen)`**
`pipeline/ingest/downsignal.py:246`
`if seen in (None, "") or int(seen) > len(sw):`
If `seen` is a string like "12", `int(seen)` works. If `seen` is `None`, it's handled.
- **Correct.**

**6. `providers.py` `Router.run` and `breaker`**
`pipeline/ingest/providers.py:776`
`breaker = rc.get("breaker", True) is not False`
If `breaker` is `False`, `self.available(bid, breaker)` is called with `breaker=False`.
`available` (line 740) returns `(True, "")` if `breaker` is `False` (after checking freeze, enabled, budget).
- **Correct.**

**7. `providers.py` `Router._try` and `_NoHealth`**
`pipeline/ingest/providers.py:836`
`h = self.health[bid] if rc.get("breaker", True) is not False else _NoHealth`
If `breaker` is `False`, `h` is `_NoHealth`.
`_NoHealth.record` does nothing.
- **Correct.**

**8. `downsignal.py` `noted` and `NO_CALL`**
`pipeline/ingest/downsignal.py:40`
`NO_CALL = frozenset({"cache", "disabled"})`
If `kind` is "cache" or "disabled", `noted` returns early.
- **Correct.**

**9. `downsignal.py` `noted` and `ANSWERED`**
`pipeline/ingest/downsignal.py:39`
`ANSWERED = frozenset({"ok", "invalid"})`
If `kind` is "ok" or "invalid", it's an answer.
- **Correct.**

**10. `downsignal.py` `noted` and `drill`**
`pipeline/ingest/downsignal.py:139-140`
`_drill` checks if the backend has a `base_url` override.
If `drill` is `True`, `pending["drills"]` is incremented.
- **Correct.**

**11. `downsignal.py` `tick` and `probe_due`**
`pipeline/ingest/downsignal.py:162`
`if self._call("probe_due", now=_utc(now)):`
`probe_due` in the builder's module checks if the mode is `plan_b` or `failing_since_utc` is set, and if the last probe was > 2 minutes ago.
- **Correct.**

**12. `downsignal.py` `tick` and `probe_result`**
`pipeline/ingest/downsignal.py:229`
`m = self._call("probe_result", answered, now=_utc(t), evidence=self.evidence, who=WHO + " probe")`
`probe_result` in the builder's module updates the probe streak and mode.
- **Correct.**

**13. `downsignal.py` `check_notice` and `busy_since`**
`pipeline/ingest/downsignal.py:301`
`now, busy = self.clock(), self.busy_since`
`busy_since` is set in `_call` (line 170) and cleared in `finally` (line 177).
If a call is stuck, `busy_since` remains set.
`check_notice` checks if `now - busy >= SIGNAL_NOTICE_S`.
- **Correct.**

**14. `downsignal.py` `snapshot` and `mode`**
`pipeline/ingest/downsignal.py:321`
`"mode": None if self.error else self.mode`
If there's an error, mode is `None`.
- **Correct.**

**15. `service.py` `health_once` and `check_notice`**
`pipeline/ingest/service.py:552-556`
`if self.hsig is not None: try: self.hsig.check_notice() except OSError as e: ...`
- **Correct.**

**16. `service.py` `run` and `signal` thread**
`pipeline/ingest/service.py:683-684`
`[threading.Thread(target=self._loop, args=("signal", self.hsig.tick, downsignal.SIGNAL_EVERY_S), daemon=True, name="signal")] if self.hsig is not None else []`
- **Correct.**

**17. `config.py` `paths` and `signal`**
`pipeline/ingest/config.py:100`
`"signal": os.path.join(ing, "down_signal.jsonl")`
- **Correct.**

**18. `providers.json` `down_signal`**
`pipeline/ingest/providers.json:96-100`
`"down_signal": { "vendor": "heimdall", "probe_role": "probe", "label": "HEIMDALL", "module": "/home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py", ... }`
- **Correct.**

**19. `providers.json` `probe` role**
`pipeline/ingest/providers.json:109-111`
`"probe": { "chain": ["heimdall_qwen27b_probe", "heimdall_glm53flash_probe"], "attempts": 1, "max_tokens": 512, "transport_retries": 0, "breaker": false, ... }`
- **Correct.**

**20. `providers.py` `validate_config` and `down_signal`**
`pipeline/ingest/providers.py:123-132`
Checks that `down_signal` has `vendor`, `label`, `module`, and `probe_role` is a role.
Checks that all backends in the probe role's chain have the same vendor as `down_signal.vendor`.
- **Correct.**

**21. `providers.py` `validate_config` and `breaker`**
`pipeline/ingest/providers.py:118-119`
`if "breaker" in r and type(r["breaker"]) is not bool: raise ValueError(...)`
- **Correct.**

**22. `providers.py` `validate_config` and `transport_retries`**
`pipeline/ingest/providers.py:120-122`
`tr = r.get("transport_retries") if tr is not None and (type(tr) is not int or tr < 0): raise ValueError(...)`
- **Correct.**

**23. `downsignal.py` `load_module`**
`pipeline/ingest/downsignal.py:47-59`
Loads the module from the path and checks for required attributes.
- **Correct.**

**24. `downsignal.py` `head`**
`pipeline/ingest/downsignal.py:76-95`
Generates the head string.
- **Correct.**

**25. `downsignal.py` `_any_text`**
`pipeline/ingest/downsignal.py:70-73`
`if not c.strip(): raise providers.Invalid("no text")`
- **Correct.**

**26. `downsignal.py` `_utc` and `_iso`**
`pipeline/ingest/downsignal.py:62-67`
- **Correct.**

**27. `downsignal.py` `DownSignal.__init__`**
`pipeline/ingest/downsignal.py:99-118`
Initializes the signal.
- **Correct.**

**28. `downsignal.py` `DownSignal.noted`**
`pipeline/ingest/downsignal.py:122-137`
- **Correct.**

**29. `downsignal.py` `DownSignal._drill`**
`pipeline/ingest/downsignal.py:139-140`
- **Correct.**

**30. `downsignal.py` `DownSignal.tick`**
`pipeline/ingest/downsignal.py:144-167`
- **Correct.**

**31. `downsignal.py` `DownSignal._call`**
`pipeline/ingest/downsignal.py:169-179`
- **Correct.**

**32. `downsignal.py` `DownSignal._flush`**
`pipeline/ingest/downsignal.py:181-196`
- **Correct.**

**33. `downsignal.py` `DownSignal._start_probe`**
`pipeline/ingest/downsignal.py:198-213`
- **Correct.**

**34. `downsignal.py` `DownSignal._report_probe`**
`pipeline/ingest/downsignal.py:215-230`
- **Correct.**

**35. `downsignal.py` `DownSignal._seen`**
`pipeline/ingest/downsignal.py:232-270`
- **Correct (with the race condition noted above).**

**36. `downsignal.py` `DownSignal._fail`**
`pipeline/ingest/downsignal.py:272-278`
- **Correct.**

**37. `downsignal.py` `DownSignal._recovered`**
`pipeline/ingest/downsignal.py:280-287`
- **Correct.**

**38. `downsignal.py` `DownSignal._evidence`**
`pipeline/ingest/downsignal.py:289-294`
- **Correct.**

**39. `downsignal.py` `DownSignal.check_notice`**
`pipeline/ingest/downsignal.py:298-316`
- **Correct.**

**40. `downsignal.py` `DownSignal.snapshot`**
`pipeline/ingest/downsignal.py:318-325`
- **Correct.**

## SECTION 2: LAW COMPLIANCE

- **L-x NO SINGLE MODEL, ULTRON FIRST:** COMPLIANT. The `probe` role has two backends (`heimdall_qwen27b_probe`, `heimdall_glm53flash_probe`). The `mine` role has two backends (`heimdall_qwen27b`, `local_gemma`). The `judge` role has three backends. The `flagcheck` role has two backends.
- **L-l a model reply counts only whole:** COMPLIANT. The `probe` role uses `_any_text` which raises `Invalid` if the text is empty. The `mine` role uses a strict validator.
- **L-j / L-m: fail closed; nothing measured is never a pass:** COMPLIANT. `DownSignal` never guesses up or down. If the state file is unreadable, it sets `self.error` and `self.mode` remains `None`.
- **L-h / L-k: transcript text is read as spoken:** COMPLIANT. Not affected by this change.
- **L-e: word timing for anything heard:** COMPLIANT. Not affected by this change.
- **L-u hard exclusions:** COMPLIANT. Not affected by this change.
- **L-v: a moment never spans a speaker change:** COMPLIANT. Not affected by this change.
- **Secrets:** COMPLIANT. Keys are read from the env file.
- **SPEND FREEZE:** COMPLIANT. The `probe` role uses Heimdall backends, which are not frozen. The `mine` role uses Heimdall and local, which are not frozen.

## SECTION 3: SECURITY

- **SQL injection:** No raw SQL queries with user input.
- **Authentication bypasses:** No routes.
- **Rate limiting gaps:** The `probe` role has `max_inflight: 1` for each backend, and `transport_retries: 0`. This prevents excessive probing.
- **Secrets in code:** No hardcoded secrets.
- **Unvalidated user input:** The `down_signal` config is validated in `validate_config`.

## SECTION 4: FRONTEND QUALITY

N/A (Backend only)

## SECTION 5: BACKEND QUALITY

- **DB operations:** The `signal_switches_seen` counter is updated in the SQLite queue. The race condition in `_seen` is a concern.
- **External API calls:** The `probe` role uses the `Router` which has timeouts and retries.
- **Cron job:** The `signal` loop runs every 5 seconds. It handles failures by setting `self.error`.
- **Memory leaks:** No large objects created per-request.
- **Logging:** Errors are logged with context.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

- **Atomicity of `_seen`:** The switch announcement and counter update should be atomic.
- **Idempotency of `write_switch_head`:** The STATE file's first line should be idempotent to prevent duplicates.

## SECTION 7: SCORES (0-100 each)

- Backend logic: 90/100
- Frontend/UI: N/A
- Error handling: 95/100
- Security: 95/100
- Performance: 95/100
- Law compliance: 100/100
- World-class gap: 85/100
- OVERALL: 92/100

## SECTION 8: PRIORITY ACTION PLAN

P0 CRITICAL | Make `_seen` atomic or idempotent | `pipeline/ingest/downsignal.py:253-270` | Duplicate switch entries in STATE file on crash/restart
P1 HIGH | Add idempotency check to `write_switch_head` | `pipeline/ingest/spend.py:195-209` | Prevent duplicate switch heads in STATE file
P2 MEDIUM | Add logging for `probe` role calls | `pipeline/ingest/downsignal.py:198-213` | Better observability of probe outcomes
P3 LOW | Add unit tests for `DownSignal._seen` race condition | `tests/ingest/test_signal.py` | Verify atomicity/idempotency

## SECTION 9: THE ONE THING

Make the switch announcement and counter update in `_seen` atomic to prevent duplicate switch entries in the STATE file on crash/restart.

## SECTION 10: FINAL VERDICT

This code is ready for production with one critical fix: the race condition in `DownSignal._seen` that can cause duplicate switch entries in the STATE file. The rest of the code is well-structured, compliant with the laws, and handles errors gracefully.