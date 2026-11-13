# qwen3.8-27b (qwen/qwen3.8-27b) 39 s finish=stop usage in 8451 / out 1280 usd~0.045 (upper-bound price)

# Audit: C1_STEP.diff (pp-selectid)

## P0 Findings
None.

## P1 Findings

**1. `pipeline/providers.py:34` — `time` module not imported in the diff**
The new method `_log_slow` calls `time.strftime(...)` and `time.gmtime()`. The diff does not show an `import time` statement being added to `pipeline/providers.py`. If `time` is not already imported at the top of the module (which is plausible given the file is ~750+ lines and may use `time` elsewhere, but not verifiable from this diff alone), this will raise `NameError` at runtime.
*Scenario:* First slow call or missed deadline triggers `_log_slow` → `NameError: name 'time' is not defined` → caught by the `except OSError` block? **No** — `NameError` is not an `OSError`, so it propagates up and **crashes the call**, violating the stated invariant that "a write that fails becomes a notice and the call goes on." This would turn an evidence-logging failure into a hard failure of the model call.
*Verification needed:* Confirm `import time` exists in `pipeline/providers.py` outside this diff. If it does, downgrade to P2.

**2. `pipeline/providers.py:37` — `os.makedirs` on every log write**
`os.makedirs(os.path.dirname(...), exist_ok=True)` is called on every single log line. While `exist_ok=True` makes it idempotent, this is a filesystem syscall on the hot path of every slow/missed call. Under concurrent load (thread pool), this is a minor contention point on the directory inode. Not a correctness bug, but unnecessary I/O.
*Scenario:* 50 concurrent slow calls → 50 redundant `makedirs` syscalls. Low risk, but worth noting.

## P2 Findings

**3. `pipeline/providers.py:34` — UTC stamp uses second-resolution `time.strftime`**
The timestamp is `%Y-%m-%dT%H:%M:%SZ` (no sub-second). If two calls miss their deadline in the same second, their log lines are indistinguishable by timestamp alone. The `model` and `role` fields disambiguate, but for forensic ordering of near-simultaneous events, millisecond resolution would be preferable.
*Scenario:* Two backends time out in the same second; the Heimdall team cannot determine which was first from the log alone.

**4. `pipeline/providers.py:50-52` — `seconds` field in `missed_deadline` is always equal to `deadline_s`**
The logged `"seconds": deadline_s` is the deadline value, not the actual elapsed time at abandonment. The order asks for "seconds" as evidence of how long the call took. Since the call was abandoned *at* the deadline, the actual elapsed time is approximately `deadline_s`, but if the timer has drift or the check is slightly late, the true elapsed time could differ. This is a minor semantic inaccuracy: the field name implies measured duration, but it's the configured limit.
*Scenario:* Heimdall team reads `"seconds": 300.0` and assumes the call ran exactly 300 s; in reality it may have been 300.02 s or 299.98 s. Low impact.

**5. `tests/providers/test_providers.py:115-117` — Test reads log file without closing it**
`open(os.path.join(d, "DEADLINES.jsonl"))` is not closed (no `with` statement). In CPython this is harmless due to reference counting, but it's a resource leak in principle and inconsistent with the `with` usage elsewhere in the test.
*Scenario:* No practical impact in the test suite, but poor hygiene.

**6. `pipeline/providers.py:18` — `import threading` inside `__init__`**
The import is inside the method body rather than at module level. This works but is unconventional and slightly slower on first instantiation (though negligible). More importantly, if `threading` were somehow unavailable (it's stdlib, so this is theoretical), the failure mode would be a `ModuleNotFoundError` at construction time rather than import time.
*Scenario:* No practical impact.

## Verification of Stated Invariants

| Invariant | Verdict |
|---|---|
| Every missed deadline logged exactly once | **Yes** — the `except DeadlineExceeded` block is the sole path for abandonment, and `_log_slow` is called once there. |
| Log never changes call outcome or spend ledger | **Yes** — `_log_slow` is called *after* `_settle` in both paths; a write failure appends to `self.notices` and does not re-raise (assuming `time` is imported, see P1-1). |
| Concurrent calls cannot interleave lines | **Yes** — `self._log_lock` (a `threading.Lock`) guards the entire `open`/`write`/`close` sequence. Each line is written atomically under the lock. |
| No secrets written (no keys, no prompt text) | **Yes** — only `prompt_chars` (integer length) is logged, never the prompt string. No API keys, no response text. |
| Without `deadline_log`, nothing is written | **Yes** — `_log_slow` returns immediately if `self.deadline_log` is falsy. |

## SHIP: yes with conditions

**Condition:** Verify that `import time` is present in `pipeline/providers.py` (module-level or earlier in the file). If it is not, this is a **P0** — the evidence logger will crash the model call on first use, violating the fail-open contract. If it is present, ship as-is; the P1/P2 items are non-blocking.