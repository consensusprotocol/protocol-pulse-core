# qwen3.8-27b (qwen/qwen3.8-27b) 112 s finish=stop usage in 41782 / out 2926 usd~0.169 (upper-bound price)

# Code Audit: Package A (pp-selectid-0108A)

## P0 Findings (Blockers)

### 1. `LocalJudgeBackend` blocks the main thread for up to 40 minutes, violating the "fail over instead of waiting" architecture
**File:** `pipeline/providers.py` (lines 516–543 in diff)
**Scenario:** In Plan B, if `local_judge:gemma3:27b` is the only available backend for a verdict (e.g., `context_verdict`), `Router.call` invokes `b.complete()`. `LocalJudgeBackend.complete` enters a `while True` loop polling the filesystem every 10 seconds for up to `WAIT_S` (2400s / 40 min).
**Impact:**
1.  **Deadlock/Starvation:** The `Router.call` method is synchronous. If the local judge is slow or the integrator service is stuck, the entire build pipeline hangs for 40 minutes. Other backends in the chain (if any) are never tried because the code is stuck inside the first backend's `complete` call.
2.  **Deadline Bypass:** The `Router.call` logic wraps `b.complete` in `_within(dl, ...)` to enforce deadlines. However, `_within` likely uses a thread or timeout mechanism. If it uses a thread, the main thread waits. If the local judge takes 39 minutes, the build is effectively stalled. The `deadline_floor_s` (2400) is explicitly set to override the 120s deadline, meaning the system *intends* to wait this long, but doing so in a blocking manner within the main call path is a severe architectural flaw for a pipeline that must handle "1000 concurrent users" (even if this is a batch job, it blocks the worker).
3.  **Probe Interaction:** The probe thread (`start_probe`) runs in a daemon thread. If the main thread is blocked in `LocalJudgeBackend.complete` for 40 minutes, the probe thread continues, but the main build is frozen. If the probe detects Heimdall is back, it switches mode, but the current call is still stuck on the local judge.

**Recommendation:** `LocalJudgeBackend.complete` should not block indefinitely. It should either:
*   Return immediately with a "pending" status, and the `Router` should handle polling/retry logic externally.
*   Or, the `Router` should run `LocalJudgeBackend` in a separate thread with a strict timeout that *does* allow failover to other backends (though in Plan B, there may be no other backends, so it would just fail closed after the timeout, not wait 40 mins).
*   Given the "fail closed" law, if the local judge is the only option, it should fail after a reasonable timeout (e.g., 5-10 mins) rather than blocking the worker for 40 mins. The 40-min wait is only acceptable if it's an async job, but `Router.call` is synchronous.

### 2. `heimdall_health.py` `_SEEN` dictionary is not thread-safe and causes race conditions in `note()`
**File:** `pipeline/heimdall_health.py` (lines 37, 149–150, 165–167)
**Scenario:** `_SEEN` is a module-level dictionary. `note()` is called from `Router._note`, which can be called from multiple threads (e.g., if the `Router` is used in a multi-threaded context, or if the probe thread and main thread interact).
**Impact:**
1.  **Race Condition:** `note()` checks `mono - _SEEN.get(path, -1e9) < HEARTBEAT_S` *before* acquiring the lock. If two threads call `note(True)` simultaneously, both may see the old `_SEEN` value and both proceed to write, defeating the heartbeat throttle.
2.  **Inconsistent State:** `_SEEN` is updated *after* the lock is released (lines 165–167). This means the heartbeat check is based on stale data.
3.  **Memory Leak:** `_SEEN` grows unbounded if many different `path` values are used (though in practice, it's likely one path, but still a design flaw).

**Recommendation:** Move the `_SEEN` check and update *inside* the `_Locked` context. Use a lock-protected dictionary or a more robust concurrency primitive.

### 3. `Router.chain` does not respect `avoid_vendor`/`avoid_family` when selecting Plan B chains
**File:** `pipeline/providers.py` (lines 649–665)
**Scenario:** `Router.chain(role, kind)` returns the Plan B chain if `self.mode() == "plan_b"`. It does *not* filter the chain based on `avoid_vendor` or `avoid_family`. The filtering happens later in `Router.call` via `self._skip`.
**Impact:**
1.  **Inefficiency:** The chain may include backends that are immediately skipped, causing unnecessary iterations.
2.  **Potential Logic Error:** If the Plan B chain is `["xai:grok", "google:gemini", ...]` and the caller avoids `xai`, the chain still starts with `xai:grok`. `Router.call` will skip it, but the `tried` list will record the skip. This is functionally correct but inefficient.
3.  **Critical:** If the Plan B chain *only* contains backends that are avoided (e.g., all are `xai` and the caller avoids `xai`), the chain is exhausted, and `ProviderError` is raised. This is correct fail-closed behavior, but the error message may be misleading ("every back-end unavailable" vs "all backends avoided").

**Recommendation:** This is not a P0, but a P1. The `chain` method should ideally return a filtered list, or the `call` method should handle the "all avoided" case with a specific error message.

## P1 Findings (Major)

### 4. `GeminiBackend` does not handle `thought` parts correctly in all cases
**File:** `pipeline/providers.py` (lines 489–490)
**Scenario:** `text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))`.
**Impact:** If a part is a `dict` but does not have a `"text"` key (e.g., it's an image part or a function call), `p.get("text", "")` returns `""`. This is safe. However, if the API returns a part that is *not* a dict (e.g., a string), `isinstance(p, dict)` is False, and it is skipped. This is safe.
**However:** The `usage` calculation `int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)` assumes `thoughtsTokenCount` is present. If it's missing, it defaults to 0. This is safe.
**Real Issue:** The `GeminiBackend` does not validate that the response is valid JSON. The `responseMimeType` is set to `application/json`, but if the model returns invalid JSON, `parse` in `call_parsed` will raise `ValueError`, and the model will be skipped. This is correct behavior.

### 5. `LocalJudgeBackend` does not clean up request files on timeout
**File:** `pipeline/providers.py` (lines 521–543)
**Scenario:** If the local judge does not answer within `WAIT_S`, `Unavailable` is raised. The request file `rid.json` remains in `self.REQUESTS`.
**Impact:**
1.  **Disk Space:** Over time, many timed-out requests will accumulate in the `judge_requests` directory.
2.  **Integrator Confusion:** The integrator may see old request files and try to answer them, causing confusion.

**Recommendation:** Add a `finally` block or cleanup logic to remove the request file if the call times out or fails.

### 6. `Router._shadow_ask` does not handle `prompt` being a dict (vision) correctly in the log
**File:** `pipeline/providers.py` (lines 749–750)
**Scenario:** `rec = {"role": role, "prompt": prompt_text(prompt), ...}`. `prompt_text` is assumed to handle both string and dict prompts. If `prompt` is a dict (vision), `prompt_text` should extract the text. If it doesn't, the log will contain a dict representation, which is not useful.
**Impact:** The shadow log may contain non-human-readable prompts for vision calls.

**Recommendation:** Ensure `prompt_text` handles vision prompts correctly, or log a summary (e.g., "vision prompt with N images").

### 7. `heimdall_health.py` `probe_due` does not account for the current mode
**File:** `pipeline/heimdall_health.py` (lines 192–200)
**Scenario:** `probe_due` returns `True` if `s["mode"] != "plan_b" and not s.get("failing_since_utc")` is `False`. This means it returns `True` if the mode is `plan_b` OR if `failing_since_utc` is set.
**Impact:** If the mode is `plan_b` but `failing_since_utc` is `None` (e.g., after a switch back to `heimdall_first` and then a new failure), `probe_due` will return `True` because `s["mode"]` is `plan_b`. This is correct.
**However:** If the mode is `heimdall_first` and `failing_since_utc` is set, `probe_due` returns `True`. This is correct.
**Real Issue:** The probe is only started by `Router.start_probe`, which is called on the first failure. If the mode is `plan_b` but the probe thread is not running (e.g., it crashed), `probe_due` will return `True`, but no probe will be run. The `Router` should ensure the probe thread is running whenever `probe_due` is `True`.

**Recommendation:** Add a check in `Router.mode()` or `Router.call` to ensure the probe thread is running if `probe_due` is `True`.

## P2 Findings (Minor)

### 8. `model_providers.json` `plan_b` chains do not include `local_judge` for all roles
**File:** `pipeline/model_providers.json` (lines 381–428)
**Scenario:** `plan_b` chains for `context_verdict` include `local_judge:gemma3:27b`, but other roles (e.g., `coherence_verdict`) do not.
**Impact:** If Heimdall is down and only one outside family (e.g., Grok) is available, `context_verdict` can use the local judge, but `coherence_verdict` cannot. This is consistent with RULING 87 ("if only ONE outside family answers, step A's second verdict is the local gemma3:27b"), but it means other verdicts will fail closed if Grok is also down. This is correct fail-closed behavior.

### 9. `Router.chain` does not handle `kind` for `today` routing
**File:** `pipeline/providers.py` (lines 649–665)
**Scenario:** `keys = ([f"{role}:{kind}"] if kind else []) + [role]`. For `today` routing, `routed` is `((self.config.get("routing") or {}).get(self.routing) or {}).get(k)`. If `self.routing` is `today`, `routed` will be `None` unless the config has a `today` key with per-type lists. The config does have `today` with per-type lists (lines 439–454). This is correct.

### 10. `heimdall_health.py` `_switch` does not handle `state_md` being `None`
**File:** `pipeline/heimdall_health.py` (lines 98–122)
**Scenario:** `if state_md:` checks if `state_md` is truthy. If `state_md` is `None`, it is skipped. This is correct.

## SHIP: No

**Reasons:**
1.  **P0-1:** `LocalJudgeBackend` blocks the main thread for up to 40 minutes, which is a severe architectural flaw for a pipeline that must handle load and fail over.
2.  **P0-2:** `heimdall_health.py` `_SEEN` dictionary is not thread-safe, causing race conditions in `note()`.

**Conditions for Ship:**
1.  Refactor `LocalJudgeBackend` to not block the main thread. Use an async pattern or a shorter timeout with fail-closed behavior.
2.  Make `heimdall_health.py` `_SEEN` thread-safe by moving the check and update inside the lock.
3.  Add cleanup logic for `LocalJudgeBackend` request files on timeout.
4.  Ensure the probe thread is running whenever `probe_due` is `True`.