# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0108A
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 794 s finish=length usage in 37184 / out 24000 usd~0.472 (upper-bound price)

# PACKAGE A AUDIT — pp-selectid (router, health, config, driver)

Scope: the diff as given (C1_STEP.diff, 1542 lines) + both addenda. I only claim what the diff shows; where the diff references code not shown (e.g. `Router._skip`, `Reply`, `_within`, `shadow86.py`, `prescreen`), I reason from the stated contracts and flag uncertainty.

---

## P0 findings

**P0-1. `Router.chain()` Plan-B branch can raise `StopIteration` → ProviderError path bypassed, and the Plan-B chain is only consulted when the role is *named* in `plan_b_chains` — roles not named silently keep the Heimdall chain while Heimdall is down.**
`providers.py:649-662` (diff numbering):

```python
keys = ([f"{role}:{kind}"] if kind else []) + [role]
if self.health and any(k in self.plan_b_chains for k in keys) and self.mode() == "plan_b":
    return list(next(self.plan_b_chains[k] for k in keys if k in self.plan_b_chains))
```

Two issues:

(a) `next(...)` over a generator that is guaranteed non-empty by the `any(...)` guard — OK, not a bug. But note the guard calls `self.mode()` which, with `health` set, imports `heimdall_health` and takes the flock **on every `chain()` call**; `chain()` is called once per back-end attempt inside `call()`'s loop? No — checking the diff: `call()` calls `self.chain(role, kind)` once at the top (`providers.py:794-795`). So one flock acquisition per call, plus one per `_note` and per probe. Acceptable, but see P1-3 (lock contention with pp-ingest's watcher).

(b) The real issue: **`plan_b_chains` (from `proof_ly.plan_b_chains()`, diff:996-1003) only contains roles named in `routing.plan_b`** — the six verdict roles + `angle_write` + `visual_check`. Any other role that runs during a build while Heimdall is down (e.g. `mine`, or any role whose chain is Heimdall-only) keeps its Heimdall chain. The test at diff:1222 even asserts this: `r.chain("mine") == ["heimdall:deepseek"]` while in plan_b. That is *by design* per the test, but it means: **if Heimdall is down and a non-`plan_b` role's chain is Heimdall-only, the build fails closed with ProviderError** — consistent with M12, so I downgrade this to P1, not P0. Actually, re-reading: the ruling says "switch the whole pin stage to PLAN B at once", and the test asserts the opposite for unnamed roles. The test *is* the spec here. **P1.**

Let me re-derive what is actually P0. The strongest candidate:

**P0-1 (real). `heimdall_health.note()` heartbeat short-circuit returns a mode derived from `_SEEN`, not from the state file — and it can return a stale mode.**
`heimdall_health.py:142-150` (diff:149-150):

```python
if answered and not drill and mono - _SEEN.get(path, -1e9) < HEARTBEAT_S:
    return "heimdall_first" if _SEEN.get(path + "#mode") != "plan_b" else "plan_b"
```

`_SEEN` is a **process-local** dict. Scenario: process A (the builder) notes `True` at t=0, `_SEEN[path]=0, _SEEN[path+"#mode"]="heimdall_first"`. Process B (pp-ingest's watcher, the miner — the module docstring at diff:7-8 says the state is *shared* with pp-ingest) switches to `plan_b` at t=10. Process A notes `True` at t=15 (< 30 s): it returns `"heimdall_first"` from `_SEEN` without reading the file. If A's caller then consults that return value to decide routing, it acts on a mode that B just changed. Is the return value of `note()` actually consulted? In `Router._note` (diff:683-698) the return value is discarded — the router calls `self.mode()` separately in `chain()`, which reads the file. So the stale return is only informational. **Downgrade: P2.** But there is a sharper variant: `_SEEN` is keyed by `path`, and `note()`'s heartbeat check happens *before* the lock, so two processes' heartbeats interleave fine — no correctness issue, just staleness. P2.

**P0-2 (real). `probe_result()` clears `failing_since_utc` only when switching back — while in plan_b, a probe answer that does NOT reach 3-in-a-row leaves `failing_since` set, which is correct; but when the switch-back happens, `probe_streak` is reset *after* `_switch` appended the record — fine. However: `probe_result` increments `probe_streak` even when mode is `heimdall_first` and calls are failing (pre-down).** Diff:203-217: `s["probe_streak"] = ... + 1 if answered else 0` unconditionally, and the switch-back only fires `if s["mode"] == "plan_b"`. So during the 15-minute failing window (mode still `heimdall_first`), probe answers accumulate a streak; if it reaches 3, nothing happens (correct — not yet down); when the 15-min switch fires, `_down_rule` resets `probe_streak = 0` (diff:177). OK. But: **`probe_result` writes `last_probe_utc` and the streak even when NOT failing and NOT in plan_b** — `probe_due` would never be true then, so `probe_result` shouldn't be called; if a caller does, it silently writes state. Harmless. P2.

**P0-3 (real). `LocalJudgeBackend.complete` polls with no upper bound on the *file-reading* race: it che

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 48 s finish=stop usage in 36354 / out 390 usd~0.192 (upper-bound price)

**P2: pipeline/providers.py:610** (Router.__init__): `if self.routing not in ROUTINGS` raises on unknown mode; concrete scenario with routing="today" or "heimdall_first" (the only values ever passed from proof_ly.py:936 or model_providers.json:303) passes, but an audit-only malformed config would fail closed (matches L-j / M12).  
**P2: pipeline/heimdall_health.py:72** (`_load` on corrupt JSON): raises HealthUnreadable; test_heimdall_health:1176 verifies no guess, state left untouched (matches ruling 87 fail-closed).  
**P2: pipeline/providers.py:813** (`_shadow_ask` thread): shadow calls use separate role "shadow86:<role>", own recordings, and are joined only in shadow_wait(900s) after main verdict; never affects deciding Reply or raises into build (matches ruling 86; verified in test_ruling_86_shadow:1501).  
**P2: tests/package/test_ledger_build.py:1065**: explicit test expectation that coherence:coherence returns None (gap) when deepseek writes + xAI down matches ruling 88(d) lists and "fails closed" design note; no verdict from writer's family (verified for all other roles).  
No P0/P1 (today routing unchanged except 20:33 chains + 120s on Heimdall; xAI-down path completes all but the documented coherence gap under heimdall_first; health uses flock + tmp+replace, unreadable raises, 15-min / probe / 3-streak rules match tests; Plan B, shadow, spend-ledger, and re-keying only under heimdall_first all verified in added tests; addenda for spotlight / rulings 93-95 merge cleanly via first_bounds + same Router).  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
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

**Recommendation:** This is not a P0, but a P1. The `chain` method should 

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0108, package A (the router, the health state, the config, the driver), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (no P0/P1); qwen3.8-27b SHIP no (two P0s); glm-5.3-flash cut at its 24k-token budget
(finish=length; several "P0" items it re-derives to P1/P2 in its own text).

## Implemented

1. glm (P0-7 re-derived to P1): Router.mode() let heimdall_health.HealthUnreadable, a new exception type, escape
   Router.call. The call sites catch ProviderError, so the build would have crashed rather than recorded "no verdict".
   FIXED: an unreadable health state is ProviderError (no verdict, law L-m), never guessed (tested).
2. glm (P1): announce() rewrote STATE line 1 outside any lock, so a switch written by the probe's thread at the same
   moment could lose a head. FIXED: both go through _prepend(), under the STATE file's own flock, with a per-thread
   tmp name.
3. glm (P0-3 re-derived to P1): the local judge took a torn answer file (read mid-write) as final: Unavailable, the
   40-minute window lost. FIXED: an unreadable answer is polled again until the deadline, and the deadline's message
   names it (tested: a half-written file, then the answer).
4. qwen P0-2: _SEEN (the heartbeat throttle) is shared by the probe thread and the build's threads. Its writes were
   already inside the flock; qwen's "updated after the lock" is not so. The read was outside, so a race could only
   write the same state twice. A module lock now guards both.

## Refuted, with evidence

- glm P0-6, its "highest-risk item" (a hard-coded avoid_vendor={"heimdall"} would skip nothing under heimdall_first's
  re-keying, so a writer's family could judge its own line). There is NO such literal anywhere in pipeline/ or the
  drivers (grep: no `{"heimdall"}`, no `== "heimdall"`). Every avoid set is built from a reply (r.vendor, r.family) or
  from router.backends, which the re-keying itself sets. Router._skip also avoids by FAMILY, and the families stay
  distinct under either routing, so L-s holds even if a vendor string mismatched.
- qwen P0-1 (the local judge "blocks the main thread for 40 minutes"). Ruling 87 names it for exactly one case: step
  A's second verdict when only ONE outside family answers in Plan B. The integrator's judge swaps gemma onto GPU0
  behind a live render, so minutes are its normal answer time. deadline_floor_s 2400 is the agreed wait. The second
  screen runs its batches in a thread pool, and no answer in time is no verdict (fail closed).
- glm P1 (roles not named in plan_b keep their Heimdall chain): this is the design under test (`chain("mine")` stays
  Heimdall). The miner's Plan B is pp-ingest's question, still open with the orchestrator. A Heimdall-only role with
  Heimdall down fails closed.
- glm P1 (the coherence gap: xAI down AND deepseek writing leaves coherence no family). This is ruled. Ruling 88 (d)
  takes glm out of coherence and (e) bars qwen. The gap is documented by TestRuling85NoXai, and the question (glm as
  coherenc

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0108/A/C2_STEP.diff (1579 lines)
```
   1 | diff --git a/pipeline/heimdall_health.py b/pipeline/heimdall_health.py
   2 | new file mode 100644
   3 | index 0000000..510725f
   4 | --- /dev/null
   5 | +++ b/pipeline/heimdall_health.py
   6 | @@ -0,0 +1,212 @@
   7 | +"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE. One shared 'Heimdall down' signal for the builder
   8 | +(verdicts and writes) and pp-ingest's watcher (the miner), kept in ONE JSON state file under an flock.
   9 | +
  10 | +- Heimdall is DOWN when NO Heimdall family answers a verdict or writer call inside its deadline for DOWN_AFTER_S (15
  11 | +  minutes) running: note(False) starts the clock (failing_since), any note(True) stops it. One model down is not
  12 | +  'down': that is ruling 82's chain, and any family's answer stops the clock.
  13 | +- While calls are failing, and while in Plan B, a cheap probe (probe_due / probe_result) runs every PROBE_EVERY_S
  14 | +  (2 minutes).
  15 | +- Down: the mode is "plan_b" at once (the whole pin stage: Grok mainly, then any other outside key that answers).
  16 | +  BACK: "heimdall_first" when the probe has answered BACK_AFTER (3) times in a row.
  17 | +- Every switch is recorded three times: in the state's "switches"; as a line {"kind": "switch", ...} in the
  18 | +  Heimdall evidence file (item 55); and, IN CAPITALS with the time, at the start of the caller's STATE line 1 (one
  19 | +  physical line).
  20 | +
  21 | +The state file: {"mode": "heimdall_first" | "plan_b", "last_answer_utc", "failing_since_utc", "last_probe_utc",
  22 | +"probe_streak", "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
  23 | +'up' or 'down' by guess: note() / mode() raise HealthUnreadable (fail closed: the caller decides, and says so).
  24 | +CPU only; no model call here (the caller makes the probe call and reports it)."""
  25 | +import fcntl
  26 | +import threading
  27 | +import json
  28 | +import os
  29 | +import time
  30 | +from datetime import datetime, timezone
  31 | +
  32 | +STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  33 | +                     "HEIMDALL_HEALTH.json")
  34 | +DOWN_AFTER_S = 15 * 60                  # ruling 87: no family answering for 15 minutes running
  35 | +PROBE_EVERY_S = 2 * 60                  # ruling 87: a cheap probe every 2 minutes while calls fail (and in Plan B)
  36 | +BACK_AFTER = 3                          # ruling 87: back to Heimdall-first after 3 probe answers in a row
  37 | +HEARTBEAT_S = 30.0                      # an answer is written at most once per 30 s per process while all is well
  38 | +_SEEN = {}                              # path -> monotonic time of this process's last written answer (no failure since)
  39 | +_SEEN_LOCK = threading.Lock()           # the probe thread and the build's threads share _SEEN (audit 0108 C1, qwen)
  40 | +MODES = ("heimdall_first", "plan_b")
  41 | +
  42 | +
  43 | +class HealthUnreadable(Exception):
  44 | +    """The state file exists but cannot be read: no guess either way (law L-j)."""
  45 | +
  46 | +
  47 | +def _now(now=None):
  48 | +    return now if now is not None else datetime.now(timezone.utc)
  49 | +
  50 | +
  51 | +def _iso(t):
  52 | +    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
  53 | +
  54 | +
  55 | +def _t(s):
  56 | +    try:
  57 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  58 | +    except (TypeError, ValueError):
  59 | +        return None
  60 | +    return t if t.tzinfo is not None else None
  61 | +
  62 | +
  63 | +def _load(path):
  64 | +    if not os.path.exists(path):
  65 | +        return {"mode": "heimdall_first", "last_answer_utc": None, "failing_since_utc": None, "last_probe_utc": None,
  66 | +                "probe_streak": 0, "switches": [], "notes": 0}
  67 | +    try:
  68 | +        with open(path) as f:
  69 | +            s = json.load(f)
  70 | +        if not isinstance(s, dict) or s.get("mode") not in MODES:
  71 | +            raise ValueError("not a health state")
  72 | +        return s
  73 | +    except (OSError, ValueError) as e:
  74 | +        raise HealthUnreadable(f"{path}: {type(e).__name__}: {e}") from None
  75 | +
  76 | +
  77 | +def _save(path, s):
  78 | +    tmp = f"{path}.{os.getpid()}.tmp"
  79 | +    with open(tmp, "w") as f:
  80 | +        json.dump(s, f, indent=1)
  81 | +    os.replace(tmp, path)
  82 | +
  83 | +
  84 | +class _Locked:
  85 | +    def __init__(self, path):
  86 | +        self.path = path
  87 | +
  88 | +    def __enter__(self):
  89 | +        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
  90 | +        self.f = open(self.path + ".lock", "w")
  91 | +        fcntl.flock(self.f, fcntl.LOCK_EX)
  92 | +        return self
  93 | +
  94 | +    def __exit__(self, *exc):
  95 | +        fcntl.flock(self.f, fcntl.LOCK_UN)
  96 | +        self.f.close()
  97 | +        return False
  98 | +
  99 | +
 100 | +def _switch(s, to, why, now, evidence=None, state_md=None, who=""):
 101 | +    """Record one switch: the state, the evidence file, STATE line 1 (capitals, the time, one physical line)."""
 102 | +    rec = {"utc": _iso(now), "to": to, "why": why, "by": who}
 103 | +    s["mode"] = to
 104 | +    s.setdefault("switches", []).append(rec)
 105 | +    if evidence:
 106 | +        try:
 107 | +            with open(evidence, "a") as f:
 108 | +                f.write(json.dumps(dict(rec, kind="switch")) + "\n")
 109 | +        except OSError:
 110 | +            pass                                # evidence, never a gate (the state file holds the switch)
 111 | +    if state_md:
 112 | +        local = now.astimezone().strftime("%H:%M")
 113 | +        word = "SWITCHED TO PLAN B" if to == "plan_b" else "BACK TO HEIMDALL-FIRST"
 114 | +        _prepend(state_md, f"{local} ET: {word} ({why.upper()}) |")   # the state and evidence files hold it too
 115 | +
 116 | +
 117 | +def announce(state_md, text, now=None):
 118 | +    """RULING 87: a Plan B fact the orchestrator must see, in capitals with the time, prepended to STATE line 1 (one
 119 | +    physical line). A file that cannot be written is left as it is (the build log carries the fact too)."""
 120 | +    now = _now(now)
 121 | +    _prepend(state_md, f"{now.astimezone().strftime('%H:%M')} ET: {text.upper()} |")
 122 | +
 123 | +
 124 | +def _prepend(state_md, head):
 125 | +    """Prepend `head` to STATE line 1 (one physical line) under the file's own lock, so a switch (the probe's thread)
 126 | +    and an announcement (the build's) never lose each other's head (audit 0108 C1, glm). A file that cannot be written
 127 | +    is left as it is."""
 128 | +    try:
 129 | +        with _Locked(state_md):
 130 | +            with open(state_md) as f:
 131 | +                lines = f.read().split("\n")
 132 | +            lines[0] = f"{head} {lines[0]}" if lines and lines[0] else head
 133 | +            tmp = f"{state_md}.{os.getpid()}.{threading.get_ident()}.tmp"
 134 | +            with open(tmp, "w") as f:
 135 | +                f.write("\n".join(lines))
 136 | +            os.replace(tmp, state_md)
 137 | +    except OSError:
 138 | +        pass
 139 | +
 140 | +
 141 | +def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False):
 142 | +    """One Heimdall verdict or writer call's outcome: answered inside its deadline (True), or not (False: down,
 143 | +    refused, empty, past the deadline). -> the mode after it. 15 minutes of failures with no answer: plan_b.
 144 | +    drill=True (pp-ingest's outage drill, 21:4x Nov 13): recorded (drills, last_drill_utc), never counted.
 145 | +    An answer while all is well is written at most once per HEARTBEAT_S per process (a failure is always written)."""
 146 | +    import time as _time
 147 | +    now, mono = _now(now), _time.monotonic()
 148 | +    with _SEEN_LOCK:
 149 | +        if answered and not drill and mono - _SEEN.get(path, -1e9) < HEARTBEAT_S:
 150 | +            return "heimdall_first" if _SEEN.get(path + "#mode") != "plan_b" else "plan_b"
 151 | +    with _Locked(path):
 152 | +        s = _load(path)
 153 | +        if drill:
 154 | +            s["drills"], s["last_drill_utc"] = int(s.get("drills") or 0) + 1, _iso(now)
 155 | +            _save(path, s)
 156 | +            return s["mode"]
 157 | +        s["notes"] = int(s.get("notes") or 0) + 1
 158 | +        if answered:
 159 | +            s["last_answer_utc"], s["failing_since_utc"] = _iso(now), None
 160 | +        elif not s.get("failing_since_utc"):
 161 | +            s["failing_since_utc"] = _iso(now)
 162 | +        _down_rule(s, now, evidence, state_md, who)
 163 | +        _save(path, s)
 164 | +        with _SEEN_LOCK:
 165 | +            if answered:
 166 | +                _SEEN[path], _SEEN[path + "#mode"] = mono, s["mode"]
 167 | +            else:
 168 | +                _SEEN.pop(path, None)
 169 | +        return s["mode"]
 170 | +
 171 | +
 172 | +def _down_rule(s, now, evidence, state_md, who):
 173 | +    fs = _t(s.get("failing_since_utc"))
 174 | +    if s["mode"] == "heimdall_first" and fs is not None and (now - fs).total_seconds() >= DOWN_AFTER_S:
 175 | +        _switch(s, "plan_b", f"no Heimdall family answered inside its deadline for "
 176 | +                             f"{int((now - fs).total_seconds() // 60)} minutes (since {_iso(fs)})", now, evidence,
 177 | +                state_md, who)
 178 | +        s["probe_streak"] = 0
 179 | +
 180 | +
 181 | +def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
 182 | +    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches). -> mode."""
 183 | +    now = _now(now)
 184 | +    with _Locked(path):
 185 | +        s = _load(path)
 186 | +        before = s["mode"]
 187 | +        _down_rule(s, now, evidence, state_md, who)
 188 | +        if s["mode"] != before:
 189 | +            _save(path, s)
 190 | +        return s["mode"]
 191 | +
 192 | +
 193 | +def probe_due(path=STATE, now=None):
 194 | +    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old."""
 195 | +    now = _now(now)
 196 | +    with _Locked(path):
 197 | +        s = _load(path)
 198 | +        if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
 199 | +            return False
 200 | +        lp = _t(s.get("last_probe_utc"))
 201 | +        return lp is None or (now - lp).total_seconds() >= PROBE_EVERY_S
 202 | +
 203 | +
 204 | +def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
 205 | +    """A probe's outcome (any Heimdall family answering it counts). BACK_AFTER answers in a row while in plan_b:
 206 | +    back to heimdall_first (the failure clock cleared). While not yet down, a probe answer is no verdict answer: the
 207 | +    15-minute clock runs on (the ruling counts verdict and writer calls). -> the mode after it."""
 208 | +    now = _now(now)
 209 | +    with _Locked(path):
 210 | +        s = _load(path)
 211 | +        s["last_probe_utc"] = _iso(now)
 212 | +        s["probe_streak"] = int(s.get("probe_streak") or 0) + 1 if answered else 0
 213 | +        if s["mode"] == "plan_b" and s["probe_streak"] >= BACK_AFTER:
 214 | +            _switch(s, "heimdall_first", f"the probe answered {s['probe_streak']} times in a row", now, evidence,
 215 | +                    state_md, who)
 216 | +            s["failing_since_utc"], s["probe_streak"] = None, 0
 217 | +        _save(path, s)
 218 | +        return s["mode"]
 219 | diff --git a/pipeline/model_providers.json b/pipeline/model_providers.json
 220 | index 11238b1..446e62d 100644
 221 | --- a/pipeline/model_providers.json
 222 | +++ b/pipeline/model_providers.json
 223 | @@ -156,6 +156,26 @@
 224 |     "family": "glm",
 225 |     "base_url": "https://api-staging.heimdallm.com/api/v1",
 226 |     "measured": "ruling 82 (orchestrator 20:02 Nov 13): pp-ingest measured it 24/24 on calibration (default reasoning)"
 227 | +  },
 228 | +  "google:gemini-2.5-pro": {
 229 | +   "vendor": "google",
 230 | +   "model": "gemini-2.5-pro",
 231 | +   "family": "gemini",
 232 | +   "key_name": "GEMINI_API_KEY_MEDLEY",
 233 | +   "price_usd_per_1m": [
 234 | +    1.25,
 235 | +    10
 236 | +   ],
 237 | +   "min_out": 8000,
 238 | +   "timeout_s": 300,
 239 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B only. The GEMINI_API_KEY_MEDLEY key is fenced to this pipeline. Gemini reports no cost: the price-table estimate (list price, thinking counted as output) is booked, labelled."
 240 | +  },
 241 | +  "local_judge:gemma3:27b": {
 242 | +   "vendor": "local_judge",
 243 | +   "model": "gemma3:27b",
 244 | +   "family": "gemma",
 245 | +   "deadline_floor_s": 2400,
 246 | +   "what": "RULING 87 (21:18 Nov 13): PLAN B ONLY, step A's verdict when one outside family answers: the integrator's GPU0 judge service (request files in tests/package/proof/judge_requests, answers in /home/ultron/protocol_pulse/data/local_judge/results). Free. A render comes first: up to 40 min."
 247 |    }
 248 |   },
 249 |   "roles": {
 250 | @@ -183,6 +203,8 @@
 251 |      "xai:grok-4.20-0309-reasoning",
 252 |      "anthropic:claude-opus-5-5",
 253 |      "heimdall:deepseek/deepseek-v4.1-flash",
 254 | +    "heimdall:z-ai/glm-5.3-flash",
 255 | +    "heimdall:qwen/qwen3.8-27b",
 256 |      "local:gemma3:27b"
 257 |     ],
 258 |     "what": "vo_fidelity.py: the blind claim-by-claim verdict on VO, title and caption; never the writer's vendor"
 259 | @@ -203,6 +225,8 @@
 260 |     "chain": [
 261 |      "anthropic:claude-opus-5-5",
 262 |      "xai:grok-4.20-0309-reasoning",
 263 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 264 | +    "heimdall:z-ai/glm-5.3-flash",
 265 |      "heimdall:qwen/qwen3.8-27b",
 266 |      "local:gemma3:27b"
 267 |     ],
 268 | @@ -238,7 +262,9 @@
 269 |      "local:gemma3:27b",
 270 |      "xai:grok-4.20-0309-reasoning",
 271 |      "anthropic:claude-opus-5-5",
 272 | -    "heimdall:deepseek/deepseek-v4.1-flash"
 273 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 274 | +    "heimdall:z-ai/glm-5.3-flash",
 275 | +    "heimdall:qwen/qwen3.8-27b"
 276 |     ],
 277 |     "what": "moments.exclusion_verdict: the hard exclusions of law L-u on one moment in its context"
 278 |    },
 279 | @@ -247,6 +273,8 @@
 280 |      "anthropic:claude-opus-5-5",
 281 |      "xai:grok-4.20-0309-reasoning",
 282 |      "heimdall:deepseek/deepseek-v4.1-flash",
 283 | +    "heimdall:z-ai/glm-5.3-flash",
 284 | +    "heimdall:qwen/qwen3.8-27b",
 285 |      "local:gemma3:27b"
 286 |     ],
 287 |     "what": "package.coherence: the blind QUALITY verdict (through-line, ratings); never the writer's vendor"
 288 | @@ -256,6 +284,8 @@
 289 |      "xai:grok-4.20-0309-reasoning",
 290 |      "anthropic:claude-opus-5-5",
 291 |      "heimdall:deepseek/deepseek-v4.1-flash",
 292 | +    "heimdall:z-ai/glm-5.3-flash",
 293 | +    "heimdall:qwen/qwen3.8-27b",
 294 |      "local:gemma3:27b"
 295 |     ],
 296 |     "what": "speakers.attribute: who speaks one pin segment, from the source's own title / channel / description and the transcript around the clip (orchestrator 00:05 ET Nov 13 item 3); code keeps only what the text shows"
 297 | @@ -275,5 +305,161 @@
 298 |     ],
 299 |     "what": "transcript_truth.py: law L-v 2's second, independent recognition pass with speaker turns on the selected segment's source audio (CPU fetch; no GPU, no Whisper)"
 300 |    }
 301 | + },
 302 | + "routing": {
 303 | +  "ruling": "RULING 85 (orchestrator 21:15 Nov 13, locked 21:18): HEIMDALL FIRST FOR EVERY VERDICT, GROK LAST, behind this switch. mode 'today': the chains under roles (with the 20:33 order: ruling 82's Heimdall chain after Grok on every verdict role). mode 'heimdall_first': the lists below; each Heimdall family is its own maker for every vendor rule, so the two-family rule is kept inside Heimdall (providers.Router). The per-type order is ruled from the replay (tests/package/replay85.py); until then each list is ruling 82's order (deepseek, glm, qwen), Grok last. A build names its routing (proof_ledger --routing).",
 304 | +  "mode": "today",
 305 | +  "verdict_roles": [
 306 | +   "context_verdict",
 307 | +   "coherence_verdict",
 308 | +   "fidelity_verdict",
 309 | +   "exclusion_verdict",
 310 | +   "speaker_verdict",
 311 | +   "viewer_takeaway"
 312 | +  ],
 313 | +  "verdict_deadline_s": {
 314 | +   "heimdall": 120
 315 | +  },
 316 | +  "heimdall_first": {
 317 | +   "context_verdict": [
 318 | +    "heimdall:qwen/qwen3.8-27b",
 319 | +    "heimdall:z-ai/glm-5.3-flash",
 320 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 321 | +    "xai:grok-4.20-0309-reasoning"
 322 | +   ],
 323 | +   "coherence_verdict": [
 324 | +    "xai:grok-4.20-0309-reasoning",
 325 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 326 | +   ],
 327 | +   "fidelity_verdict": [
 328 | +    "heimdall:qwen/qwen3.8-27b",
 329 | +    "heimdall:z-ai/glm-5.3-flash",
 330 | +    "xai:grok-4.20-0309-reasoning"
 331 | +   ],
 332 | +   "exclusion_verdict": [
 333 | +    "heimdall:z-ai/glm-5.3-flash",
 334 | +    "heimdall:qwen/qwen3.8-27b",
 335 | +    "xai:grok-4.20-0309-reasoning"
 336 | +   ],
 337 | +   "speaker_verdict": [
 338 | +    "xai:grok-4.20-0309-reasoning",
 339 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 340 | +    "heimdall:z-ai/glm-5.3-flash",
 341 | +    "heimdall:qwen/qwen3.8-27b"
 342 | +   ],
 343 | +   "viewer_takeaway": [
 344 | +    "xai:grok-4.20-0309-reasoning",
 345 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 346 | +    "heimdall:z-ai/glm-5.3-flash",
 347 | +    "heimdall:qwen/qwen3.8-27b"
 348 | +   ],
 349 | +   "context_verdict:step_a_first": [
 350 | +    "heimdall:qwen/qwen3.8-27b",
 351 | +    "heimdall:z-ai/glm-5.3-flash",
 352 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 353 | +    "xai:grok-4.20-0309-reasoning"
 354 | +   ],
 355 | +   "context_verdict:step_a_second": [
 356 | +    "xai:grok-4.20-0309-reasoning",
 357 | +    "heimdall:qwen/qwen3.8-27b",
 358 | +    "heimdall:z-ai/glm-5.3-flash",
 359 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 360 | +   ],
 361 | +   "context_verdict:step_c": [
 362 | +    "xai:grok-4.20-0309-reasoning",
 363 | +    "heimdall:z-ai/glm-5.3-flash",
 364 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 365 | +   ],
 366 | +   "coherence_verdict:hook": [
 367 | +    "heimdall:qwen/qwen3.8-27b",
 368 | +    "heimdall:z-ai/glm-5.3-flash",
 369 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 370 | +    "xai:grok-4.20-0309-reasoning"
 371 | +   ],
 372 | +   "coherence_verdict:clips_alone": [
 373 | +    "xai:grok-4.20-0309-reasoning",
 374 | +    "heimdall:qwen/qwen3.8-27b",
 375 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 376 | +   ],
 377 | +   "coherence_verdict:coherence": [
 378 | +    "xai:grok-4.20-0309-reasoning",
 379 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 380 | +   ]
 381 | +  },
 382 | +  "plan_b": {
 383 | +   "context_verdict": [
 384 | +    "xai:grok-4.20-0309-reasoning",
 385 | +    "google:gemini-2.5-pro",
 386 | +    "openai:gpt-6.1-sol",
 387 | +    "anthropic:claude-opus-5-5",
 388 | +    "local_judge:gemma3:27b"
 389 | +   ],
 390 | +   "coherence_verdict": [
 391 | +    "xai:grok-4.20-0309-reasoning",
 392 | +    "google:gemini-2.5-pro",
 393 | +    "openai:gpt-6.1-sol",
 394 | +    "anthropic:claude-opus-5-5"
 395 | +   ],
 396 | +   "fidelity_verdict": [
 397 | +    "xai:grok-4.20-0309-reasoning",
 398 | +    "google:gemini-2.5-pro",
 399 | +    "openai:gpt-6.1-sol",
 400 | +    "anthropic:claude-opus-5-5"
 401 | +   ],
 402 | +   "exclusion_verdict": [
 403 | +    "xai:grok-4.20-0309-reasoning",
 404 | +    "google:gemini-2.5-pro",
 405 | +    "openai:gpt-6.1-sol",
 406 | +    "anthropic:claude-opus-5-5"
 407 | +   ],
 408 | +   "speaker_verdict": [
 409 | +    "xai:grok-4.20-0309-reasoning",
 410 | +    "google:gemini-2.5-pro",
 411 | +    "openai:gpt-6.1-sol",
 412 | +    "anthropic:claude-opus-5-5"
 413 | +   ],
 414 | +   "viewer_takeaway": [
 415 | +    "xai:grok-4.20-0309-reasoning",
 416 | +    "google:gemini-2.5-pro",
 417 | +    "openai:gpt-6.1-sol",
 418 | +    "anthropic:claude-opus-5-5"
 419 | +   ],
 420 | +   "angle_write": [
 421 | +    "xai:grok-4.20-0309-reasoning",
 422 | +    "google:gemini-2.5-pro",
 423 | +    "openai:gpt-6.1-sol",
 424 | +    "anthropic:claude-opus-5-5"
 425 | +   ],
 426 | +   "visual_check": [
 427 | +    "xai_vision:grok-4.7"
 428 | +   ]
 429 | +  },
 430 | +  "plan_b_note": "RULING 87: while pipeline/heimdall_health.py says Heimdall is down (no family answered a verdict or writer call inside its deadline for 15 minutes running), these roles run on these chains: Grok mainly, then any other outside key that answers (Gemini's fenced key; OpenAI and Anthropic only when a call shows they have credit: they are tried, never assumed). Back to the mode's chains when the probe has answered 3 times in a row.",
 431 | +  "shadow": {
 432 | +   "*": "xai:grok-4.20-0309-reasoning",
 433 | +   "visual_check": "xai_vision:grok-4.7"
 434 | +  },
 435 | +  "shadow_until_clean_pins": 3,
 436 | +  "shadow_note": "RULING 86: a heimdall_first build asks these back-ends the same prompt of every verdict Heimdall decided (recorded, never deciding) until 3 pins in a row show no decision-changing difference.",
 437 | +  "today_unbounded": [
 438 | +   "context_verdict"
 439 | +  ],
 440 | +  "today": {
 441 | +   "coherence_verdict:coherence": [
 442 | +    "xai:grok-4.20-0309-reasoning",
 443 | +    "heimdall:deepseek/deepseek-v4.1-flash"
 444 | +   ],
 445 | +   "coherence_verdict:clips_alone": [
 446 | +    "xai:grok-4.20-0309-reasoning",
 447 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 448 | +    "heimdall:qwen/qwen3.8-27b"
 449 | +   ],
 450 | +   "context_verdict:step_c": [
 451 | +    "xai:grok-4.20-0309-reasoning",
 452 | +    "heimdall:deepseek/deepseek-v4.1-flash",
 453 | +    "heimdall:z-ai/glm-5.3-flash"
 454 | +   ]
 455 | +  },
 456 | +  "ruling_88": "RULING 88 (orchestrator 22:15 Nov 13), from the replay's interim, the full table to confirm: (a) fidelity and exclusion on Heimdall now (two families, Grok last); (b) step C and the hook rating move when the full table holds the interim's 98-100 % (Grok first until then); (c) step A: Heimdall FIRST, a clip Heimdall refuses is refused and Grok is never asked, a clip Heimdall passes goes to Grok to confirm; (d) clips-alone and coherence keep Grok, glm out of both; (e) qwen never decides coherence or step C. THE FULL TABLE (01:06 ET Nov 14, 884 rows): (b) holds for the hook rating (qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %): it moved, qwen -> glm -> deepseek -> Grok; it does not hold for step C (glm 97 %, deepseek 96 %; qwen 98 % but barred by (e)): Grok first."
 457 |   }
 458 |  }
 459 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 460 | index 55b66b3..aa5474b 100644
 461 | --- a/pipeline/providers.py
 462 | +++ b/pipeline/providers.py
 463 | @@ -254,6 +254,89 @@ class OpenAIBackend(Backend):
 464 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 465 |  
 466 |  
 467 | +class GeminiBackend(Backend):
 468 | +    """Google Gemini generateContent. RULING 87 (21:18 Nov 13): PLAN B ONLY. The key (key_name, default
 469 | +    GEMINI_API_KEY_MEDLEY) is fenced to this pipeline. It is sent in a header, never in the URL. JSON is asked for in
 470 | +    words and by responseMimeType. The reply's usageMetadata gives the tokens (thinking counted as output). Gemini
 471 | +    reports no cost, so the price-table estimate stands for each call, labelled as one."""
 472 | +    vendor = "google"
 473 | +    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
 474 | +
 475 | +    def complete(self, prompt, max_tokens, seed, system=None):
 476 | +        if is_vision(prompt):
 477 | +            raise RequestRejected("gemini: no image input on this back-end")
 478 | +        key = self.key(self.spec.get("key_name") or "GEMINI_API_KEY_MEDLEY")
 479 | +        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
 480 | +                "generationConfig": {"maxOutputTokens": self.max_out(max_tokens), "temperature": 0, "seed": seed,
 481 | +                                     "responseMimeType": "application/json"}}
 482 | +        if system:
 483 | +            body["systemInstruction"] = {"parts": [{"text": system}]}
 484 | +        t0 = time.time()
 485 | +        j = _with_backoff(lambda: _http_json(self.URL.format(model=self.model), body, {"x-goog-api-key": key},
 486 | +                                             self.timeout))
 487 | +        u = j.get("usageMetadata") or {}
 488 | +        try:
 489 | +            parts = j["candidates"][0]["content"]["parts"]
 490 | +            text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
 491 | +        except (KeyError, IndexError, TypeError):
 492 | +            raise RequestRejected("gemini: no candidates") from None
 493 | +        return text, {"in": int(u.get("promptTokenCount") or 0),
 494 | +                      "out": int(u.get("candidatesTokenCount") or 0) + int(u.get("thoughtsTokenCount") or 0)}, \
 495 | +            time.time() - t0
 496 | +
 497 | +
 498 | +class LocalJudgeBackend(Backend):
 499 | +    """RULING 87 (21:18 Nov 13): the integrator's GPU0 judge service (gemma3:27b). PLAN B ONLY: step A's verdict when
 500 | +    only one outside family answers. The integrator's contract (its message of 21:4x Nov 13):
 501 | +    - a request file in this worktree's tests/package/proof/judge_requests/<request_id>.json (written .tmp, then
 502 | +      renamed; read-only there, answered once per name and content), body {request_id, family "step_a", prompt,
 503 | +      max_tokens, seed}, ONE call per request;
 504 | +    - the answer in RESULTS/<request_id>.<prompt_id>.json, prompt_id = sha256(json.dumps([prompt, max_tokens,
 505 | +      seed]))[:20] (the integrator's local_judge.prompt_id; live 22:26:30 Nov 13, judge_sha c62a1e12088c), with
 506 | +      {request_id, family, prompt_id, model, digest, seed, max_tokens, text, error, seconds, waited_s, at, judge_sha}.
 507 | +      Only that exact file is read: an answer is this prompt's by its own sha.
 508 | +    A render always comes first, so the wait allows WAIT_S (40 min). No answer in time, an error, or a file that
 509 | +    cannot be read is no verdict (Unavailable for this call). The reply's contract is checked by the caller, as for a
 510 | +    vendor's. Local: free, no spend."""
 511 | +    vendor = "local_judge"
 512 | +    REQUESTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
 513 | +                            "judge_requests")
 514 | +    RESULTS = "/home/ultron/protocol_pulse/data/local_judge/results"      # the integrator's; read only
 515 | +    WAIT_S, POLL_S = 2400.0, 10.0
 516 | +
 517 | +    def complete(self, prompt, max_tokens, seed, system=None):
 518 | +        if is_vision(prompt) or system:
 519 | +            raise RequestRejected("local judge: a text prompt without a system message only")
 520 | +        rid = f"pp-selectid.{time.strftime('%Y%m%dT%H%M%S')}.{uuid.uuid4().hex[:8]}"
 521 | +        pid = hashlib.sha256(json.dumps([prompt, int(max_tokens), int(seed)]).encode()).hexdigest()[:20]
 522 | +        os.makedirs(self.REQUESTS, exist_ok=True)
 523 | +        tmp, final = os.path.join(self.REQUESTS, rid + ".tmp"), os.path.join(self.REQUESTS, rid + ".json")
 524 | +        with open(tmp, "x") as f:
 525 | +            json.dump({"request_id": rid, "family": "step_a", "prompt": prompt, "max_tokens": int(max_tokens),
 526 | +                       "seed": int(seed)}, f)
 527 | +        os.rename(tmp, final)
 528 | +        t0 = time.time()
 529 | +        answer = os.path.join(self.RESULTS, f"{rid}.{pid}.json")
 530 | +        while True:
 531 | +            rec, torn = None, None
 532 | +            if os.path.exists(answer):
 533 | +                try:
 534 | +                    with open(answer) as f:
 535 | +                        rec = json.load(f)
 536 | +                except (OSError, ValueError) as e:      # audit 0108 C1 (glm): a file read while it is being written
 537 | +                    torn = f"{type(e).__name__}"        # is polled again until the deadline, never taken as final
 538 | +            if rec is not None:
 539 | +                if not isinstance(rec, dict) or rec.get("request_id") != rid or rec.get("prompt_id") != pid or \
 540 | +                        rec.get("error") or not isinstance(rec.get("text"), str):
 541 | +                    raise RequestRejected(f"local judge: no verdict ({str((rec or {}).get('error'))[:200]})")
 542 | +                return rec["text"], {"in": 0, "out": 0, **{k: rec.get(k) for k in ("judge_sha", "digest",
 543 | +                                                                                    "waited_s")}}, time.time() - t0
 544 | +            if time.time() - t0 >= self.WAIT_S:
 545 | +                raise Unavailable(f"local judge: no answer within {self.WAIT_S:.0f} s (a render comes first)" +
 546 | +                                  (f"; the answer file could not be read ({torn})" if torn else ""))
 547 | +            time.sleep(self.POLL_S)
 548 | +
 549 | +
 550 |  class DeadlineExceeded(Exception):
 551 |      """A back-end gave no answer within the caller's deadline (orchestrator 22:40 ruling 5: one writer call never waits
 552 |      more than 5 min). The call is abandoned, not killed: Python cannot stop the thread."""
 553 | @@ -577,7 +660,48 @@ class ElevenLabsTranscribe(STTBackend):
 554 |  
 555 |  
 556 |  VENDORS = {"local": LocalBackend, "xai_search": XAISearchBackend, "xai_vision": XAIVisionBackend, "openai": OpenAIBackend, "heimdall": HeimdallBackend, "xai": XAIBackend,
 557 | -           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe}
 558 | +           "anthropic": AnthropicBackend, "openai_stt": OpenAITranscribe, "elevenlabs_stt": ElevenLabsTranscribe,
 559 | +           "google": GeminiBackend, "local_judge": LocalJudgeBackend}
 560 | +
 561 | +
 562 | +ROUTINGS = ("today", "heimdall_first")    # RULING 85 (21:15 Nov 13): the switch (model_providers.json "routing")
 563 | +SHADOW_ROLES = ("context_verdict", "coherence_verdict", "fidelity_verdict", "exclusion_verdict", "speaker_verdict",
 564 | +                "viewer_takeaway", "visual_check")      # RULING 86: the verdicts a shadow back-end is asked again
 565 | +
 566 | +
 567 | +def gateway(b):
 568 | +    """The vendor a back-end is reached through: "heimdall" for every Heimdall model, whatever its routing makes of
 569 | +    b.vendor (ruling 85: under heimdall_first, a Heimdall family is its own maker, b.vendor == "heimdall/<family>")."""
 570 | +    return getattr(b, "gateway", b.vendor)
 571 | +
 572 | +
 573 | +def call_parsed(router, role, prompt, parse, max_tokens=2000, seed=7, system=None, avoid_vendor=None,
 574 | +                avoid_model=None, avoid_family=None, deadline_s=None, kind=None):
 575 | +    """The 20:33 order (ruling 82's chain on every verdict): the role's chain, where an answer OUT OF CONTRACT also
 576 | +    moves on to the next model, each model once. parse(text) raises ValueError / TypeError / KeyError for an answer
 577 | +    out of contract; that reply is rejected (its recording dropped, so it is asked again another time) and its model
 578 | +    skipped. -> (reply, parse(reply.text)). The chain spent: ProviderError (no verdict; nothing is cached by the
 579 | +    caller). Errors of the back-ends themselves (down, refused, past the deadline, empty) move on inside Router.call.
 580 | +    Works with any router that has call() (and reject(), when it has one)."""
 581 | +    skip, why = set(_as_set(avoid_model)), []
 582 | +    while True:
 583 | +        kw = {k: v for k, v in (("system", system), ("avoid_vendor", avoid_vendor), ("avoid_family", avoid_family),
 584 | +                                ("deadline_s", deadline_s), ("kind", kind)) if v is not None}
 585 | +        try:
 586 | +            r = router.call(role, prompt, max_tokens, seed, **kw, **({"avoid_model": frozenset(skip)} if skip else {}))
 587 | +        except ProviderError as e:
 588 | +            if why:
 589 | +                raise ProviderError(f"{e}; answers out of contract: {why}") from e
 590 | +            raise
 591 | +        if r.backend in skip:                      # never a loop: a model told to skip answered again (no verdict)
 592 | +            raise ProviderError(f"{role}: {r.backend} answered again though skipped; answers out of contract: {why}")
 593 | +        try:
 594 | +            return r, parse(r.text)
 595 | +        except (ValueError, TypeError, KeyError) as e:
 596 | +            if hasattr(router, "reject"):
 597 | +                router.reject(r)
 598 | +            why.append((r.backend, f"{type(e).__name__}: {str(e)[:120]}"))
 599 | +            skip.add(r.backend)
 600 |  
 601 |  
 602 |  def _as_set(x):
 603 | @@ -594,9 +718,14 @@ class Router:
 604 |      spend ledger, and returns a Reply naming the back-end that answered. replay=True serves recorded exchanges only."""
 605 |  
 606 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
 607 | -                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0):
 608 | +                 local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
 609 | +                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None):
 610 |          with open(config) as f:
 611 |              self.config = json.load(f)
 612 | +        rt = self.config.get("routing") or {}
 613 | +        self.routing = routing or rt.get("mode") or "today"     # RULING 85: "today" or "heimdall_first"
 614 | +        if self.routing not in ROUTINGS:
 615 | +            raise ValueError(f"routing must be one of {ROUTINGS}, not {self.routing!r}")
 616 |          self.env_path = env_path or ENV_PATH
 617 |          self.record_dir, self.replay, self.spend_path, self.limit_usd = record_dir, replay, spend_path, limit_usd
 618 |          if limit_basis not in ("estimate", "reported"):
 619 | @@ -612,10 +741,49 @@ class Router:
 620 |              self.backends[name] = cls(name, spec, self.env_path, local_llm) if cls is LocalBackend else \
 621 |                  cls(name, spec, self.env_path)
 622 |          self.chains = dict(chains or {})          # tests / the A/B harness may pin a role's chain (still by config name)
 623 | -
 624 | -    def chain(self, role):
 625 | -        if role in self.chains:
 626 | -            return list(self.chains[role])
 627 | +        # RULING 86 (21:18 Nov 13): {role or "*": back-end} asked the SAME prompt of every verdict another back-end
 628 | +        # decided (recorded to shadow_log, never deciding); its role is "shadow86:<role>", so its recordings and its
 629 | +        # spend (ruling 48's ledger) are its own
 630 | +        self.shadow, self.shadow_log, self._shadows = dict(shadow or {}), shadow_log, []
 631 | +        for r_, name_ in self.shadow.items():
 632 | +            if name_ not in self.backends:
 633 | +                raise ValueError(f"the shadow back-end {name_!r} is not in the config")
 634 | +        # RULING 87 (21:18 Nov 13): PLAN B. health: the shared state file (pipeline/heimdall_health.py); every
 635 | +        # Heimdall verdict or writer call's outcome is noted there, and while it says "plan_b" the roles named in
 636 | +        # plan_b_chains (frozen legs already out) run on them: Grok mainly, then any other outside key that answers.
 637 | +        # A probe thread asks each Heimdall family a one-word question every 2 minutes while calls fail.
 638 | +        self.health, self.plan_b_chains, self.state_md = health, dict(plan_b_chains or {}), state_md
 639 | +        self._probe = None
 640 | +        if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
 641 | +            for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
 642 | +                if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
 643 | +                    b.gateway, b.vendor = b.vendor, f"{b.vendor}/{b.family}"
 644 | +
 645 | +    def mode(self):
 646 | +        """RULING 87: "plan_b" while the shared health state says Heimdall is down, else this router's routing."""
 647 | +        if not self.health:
 648 | +            return self.routing
 649 | +        import heimdall_health as HH
 650 | +        try:
 651 | +            m = HH.mode(self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid")
 652 | +        except HH.HealthUnreadable as e:          # audit 0108 C1 (glm): never guessed, and never an exception the
 653 | +            raise ProviderError(f"the Heimdall health state cannot be read: {e}") from None   # call sites miss: no
 654 | +        return "plan_b" if m == "plan_b" else self.routing                                    # verdict (law L-m)
 655 | +
 656 | +    def chain(self, role, kind=None):
 657 | +        """The back-ends a call of `role` tries, in order. RULING 88 (22:15 Nov 13): a verdict TYPE may have its own
 658 | +        list, keyed "<role>:<kind>" (step_a_first, step_a_second, step_c, hook, clips_alone, coherence); without one,
 659 | +        the role's. Plan B's lists first while Heimdall is down (ruling 87); then this router's overrides; then the
 660 | +        routing's lists (ruling 85, not under "today"); then the role's configured chain."""
 661 | +        keys = ([f"{role}:{kind}"] if kind else []) + [role]
 662 | +        if self.health and any(k in self.plan_b_chains for k in keys) and self.mode() == "plan_b":
 663 | +            return list(next(self.plan_b_chains[k] for k in keys if k in self.plan_b_chains))   # ruling 87
 664 | +        for k in keys:
 665 | +            if k in self.chains:
 666 | +                return list(self.chains[k])
 667 | +            routed = ((self.config.get("routing") or {}).get(self.routing) or {}).get(k)
 668 | +            if routed:                            # RULING 85 / 88: this routing's own list (today: per type only)
 669 | +                return list(routed)
 670 |          try:
 671 |              return list(self.config["roles"][role]["chain"])
 672 |          except KeyError:
 673 | @@ -825,6 +993,119 @@ class Router:
 674 |          except OSError:
 675 |              return False
 676 |  
 677 | +    def role_deadline(self, role, b):
 678 | +        """The 20:33 order (ruling 82's chain on the verdicts): a call of a verdict role on a back-end whose gateway
 679 | +        names a deadline (model_providers.json routing.verdict_deadline_s, e.g. {"heimdall": 120}) gets it when the
 680 | +        caller sets none. -> seconds or None."""
 681 | +        rt = self.config.get("routing") or {}
 682 | +        bounded = set(rt.get("verdict_roles") or ())
 683 | +        if self.routing == "today":                   # step A's first screen and step C keep no deadline today:
 684 | +            bounded -= set(rt.get("today_unbounded") or ())   # ruling 82 bounded only the second screen (8 clips a
 685 | +        if role not in bounded:                       # call cannot answer in 120 s on Heimdall)
 686 | +            return None
 687 | +        d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
 688 | +        return float(d) if _num(d) and d > 0 else None
 689 | +
 690 | +    def _note(self, role, b, answered):
 691 | +        """RULING 87: a Heimdall verdict or writer call's outcome, to the shared health state (never a gate here: a
 692 | +        state file that cannot be written is a notice). The probe thread starts at the first failure."""
 693 | +        rt = self.config.get("routing") or {}
 694 | +        if not self.health or not isinstance(b, HeimdallBackend) or \
 695 | +                role not in set(rt.get("verdict_roles") or ()) | {"angle_write"}:
 696 | +            return
 697 | +        import heimdall_health as HH
 698 | +        try:
 699 | +            HH.note(answered, self.health, evidence=self.deadline_log, state_md=self.state_md, who="pp-selectid")
 700 | +        except (HH.HealthUnreadable, OSError) as e:
 701 | +            n = f"RULING 87: the Heimdall health state cannot be read or written: {e}"
 702 | +            if n not in self.notices:
 703 | +                self.notices.append(n)
 704 | +        if not answered:
 705 | +            self.start_probe()
 706 | +
 707 | +    def start_probe(self, every_s=30.0):
 708 | +        """RULING 87: the probe thread (one per router): while HH.probe_due, ask each Heimdall family a one-word
 709 | +        question (60 s each, on ruling 48's ledger as role "probe87"); any answer is a probe answer."""
 710 | +        import threading
 711 | +        if self._probe is not None or not self.health:
 712 | +            return
 713 | +        import heimdall_health as HH
 714 | +        fams = [n for n, b in self.backends.items() if isinstance(b, HeimdallBackend) and n.startswith("heimdall:")
 715 | +                and b.family in ("deepseek", "glm", "qwen")]
 716 | +
 717 | +        def loop():
 718 | +            while True:
 719 | +                try:
 720 | +                    if HH.probe_due(self.health):
 721 | +                        HH.probe_result(self.probe_once(fams), self.health, evidence=self.deadline_log,
 722 | +                                        state_md=self.state_md, who="pp-selectid probe")
 723 | +                except Exception:                      # noqa: BLE001 (the probe never stops a build)
 724 | +                    pass
 725 | +                time.sleep(every_s)
 726 | +        self._probe = threading.Thread(target=loop, daemon=True, name="pp-probe87")
 727 | +        self._probe.start()
 728 | +
 729 | +    def probe_once(self, names):
 730 | +        """RULING 87: one probe round: each Heimdall family asked a one-word question (60 s, never recorded nor served
 731 | +        from a recording). A family this run marked down is probed all the same: its mark is lifted for the probe and
 732 | +        stays lifted when it answers (it may serve again), restored when it does not. -> True if any family answered."""
 733 | +        ok = False
 734 | +        for n in names:
 735 | +            self.chains.setdefault(f"probe87:{n}", [n])
 736 | +            was = self.down.pop(n, None)
 737 | +            try:
 738 | +                r = self.call(f"probe87:{n}", "Reply with the single word OK.", 64, 7, deadline_s=60.0)
 739 | +                ok = ok or bool(r.text.strip())
 740 | +            except Exception:                          # noqa: BLE001 (a probe that fails is a probe that failed)
 741 | +                if was is not None and n not in self.down:
 742 | +                    self.down[n] = was
 743 | +        return ok
 744 | +
 745 | +    def _shadow_of(self, role):
 746 | +        return self.shadow.get(role) or self.shadow.get("*")
 747 | +
 748 | +    def _shadow_ask(self, role, prompt, max_tokens, seed, system, deciding):
 749 | +        """RULING 86: ask the role's shadow back-end the same prompt, in a thread; one JSON line to shadow_log per
 750 | +        verdict with both answers. Never raises into the build and never decides."""
 751 | +        import threading
 752 | +        name = self._shadow_of(role)
 753 | +        self.chains.setdefault(f"shadow86:{role}", [name])
 754 | +
 755 | +        def run():
 756 | +            rec = {"role": role, "prompt": prompt_text(prompt), "images": len(prompt["images"]) if is_vision(prompt)
 757 | +                   else 0, "max_tokens": max_tokens, "seed": seed, "system": system,
 758 | +                   "deciding": {"backend": deciding.backend, "vendor": deciding.vendor, "text": deciding.text,
 759 | +                                "cached": bool(getattr(deciding, "cached", False))}}
 760 | +            t0 = time.time()
 761 | +            try:
 762 | +                r = self.call(f"shadow86:{role}", prompt, max_tokens, seed, system=system)
 763 | +                rec["shadow"] = {"backend": r.backend, "text": r.text, "seconds": round(time.time() - t0, 2),
 764 | +                                 "cached": bool(getattr(r, "cached", False)),
 765 | +                                 "usd_reported": (r.usage or {}).get("usd_reported"), "usd_estimate": r.usd}
 766 | +            except Exception as e:                     # noqa: BLE001 (a shadow never stops a build)
 767 | +                rec["shadow"] = {"backend": name, "error": f"{type(e).__name__}: {str(e)[:300]}",
 768 | +                                 "seconds": round(time.time() - t0, 2)}
 769 | +            if self.shadow_log:
 770 | +                line = json.dumps(dict(rec, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
 771 | +                try:
 772 | +                    with self._log_lock:
 773 | +                        os.makedirs(os.path.dirname(os.path.abspath(self.shadow_log)), exist_ok=True)
 774 | +                        with open(self.shadow_log, "a") as f:
 775 | +                            f.write(line + "\n")
 776 | +                except OSError as e:
 777 | +                    self.notices.append(f"the shadow log could not be written: {type(e).__name__}: {e}")
 778 | +        t = threading.Thread(target=run, daemon=True, name="pp-shadow86")
 779 | +        self._shadows.append(t)
 780 | +        t.start()
 781 | +
 782 | +    def shadow_wait(self, timeout_s=900.0):
 783 | +        """RULING 86: wait for every shadow call of this router (a build's side-by-side needs them all). -> the number
 784 | +        still running when the time ran out (their lines are then missing from shadow_log, and the report says so)."""
 785 | +        end = time.time() + timeout_s
 786 | +        for t in list(self._shadows):
 787 | +            t.join(max(0.0, end - time.time()))
 788 | +        return sum(t.is_alive() for t in self._shadows)
 789 | +
 790 |      def heimdall_tripwire(self, at=0.9):
 791 |          """NOTIFY when Heimdall's account usage reaches `at` of its credits (PBX 02:45: never a halt)."""
 792 |          h = next((b for b in self.backends.values() if isinstance(b, HeimdallBackend)), None)
 793 | @@ -859,10 +1140,10 @@ class Router:
 794 |          os.replace(tmp, path)
 795 |  
 796 |      def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
 797 | -             avoid_family=None, deadline_s=None):
 798 | +             avoid_family=None, deadline_s=None, kind=None):
 799 |          av, am, af = _as_set(avoid_vendor), _as_set(avoid_model), _as_set(avoid_family)
 800 |          tried, notices = [], []
 801 | -        for name in self.chain(role):
 802 | +        for name in self.chain(role, kind):           # ruling 88: the verdict type's own list when it has one
 803 |              b = self.backends.get(name)
 804 |              why = self._skip(name, b, av, am, af)
 805 |              if why is None and isinstance(b, STTBackend):
 806 | @@ -874,23 +1155,36 @@ class Router:
 807 |              if why:
 808 |                  tried.append((name, why))
 809 |                  continue
 810 | -            path = self._path(role, name, prompt, max_tokens, seed, system) if self.record_dir else None
 811 | +            path = self._path(role, name, prompt, max_tokens, seed, system) \
 812 | +                if self.record_dir and not role.startswith("probe87:") else None      # ruling 87: a probe is live
 813 |              if path and os.path.exists(path):
 814 |                  with open(path) as f:
 815 |                      rec = json.load(f)
 816 | -                return Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
 817 | -                             rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
 818 | +                out = Reply(rec["text"], name, b.vendor, rec.get("seconds", 0.0), rec.get("usage") or {},
 819 | +                            rec.get("usd", 0.0), self.replay, tried, notices, b.family, not self.replay, path)
 820 | +                if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 821 | +                    self._shadow_ask(role, prompt, max_tokens, seed, system, out)  # ruling 86: a recorded verdict too
 822 | +                return out
 823 |              if self.replay:
 824 |                  tried.append((name, "replay: not recorded"))
 825 |                  continue
 826 |              upper = b.upper_usd(prompt, max_tokens, system)
 827 |              key = self._reserve(b, upper)
 828 | -            if b.vendor == "heimdall":
 829 | +            if isinstance(b, HeimdallBackend):
 830 |                  n = self.heimdall_tripwire()
 831 |                  if n:
 832 |                      notices.append(n)
 833 |  
 834 | -            def abandon(b=b, key=key, name=name):      # RULING 83 (a): booked at its PROMPT tokens (input rate), an
 835 | +            dl = deadline_s or self.role_deadline(role, b)      # the caller's deadline, else the role's (20:33)
 836 | +            if dl and _num(b.spec.get("deadline_floor_s")):     # ruling 87: the local judge waits out a render
 837 | +                dl = max(dl, float(b.spec["deadline_floor_s"]))
 838 | +            if isinstance(b, LocalJudgeBackend) and self.state_md and not getattr(self, "_announced_local", False):
 839 | +                import heimdall_health as HH
 840 | +                self._announced_local = True                    # ruling 87: "and STATE line 1 says so"
 841 | +                HH.announce(self.state_md, "PLAN B WITH ONE OUTSIDE FAMILY: STEP A'S VERDICT IS ASKED OF THE LOCAL "
 842 | +                                           "GEMMA3:27B ON GPU0 (THE INTEGRATOR'S JUDGE SERVICE)")
 843 | +
 844 | +            def abandon(b=b, key=key, name=name, deadline_s=dl):   # RULING 83 (a): booked at its PROMPT tokens, an
 845 |                  booked = b.prompt_usd(prompt, system)  # unreported estimate, until a late answer's figure replaces it
 846 |                  self._log_slow({"kind": "missed_deadline", "role": role, "model": name, "vendor": b.vendor,
 847 |                                  "deadline_s": deadline_s, "seconds": deadline_s,
 848 | @@ -899,22 +1193,25 @@ class Router:
 849 |                  self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 850 |                  return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
 851 |              try:
 852 | -                if deadline_s:                         # ruling 5 (22:40): fail over instead of waiting
 853 | -                    text, usage, secs = _within(deadline_s, lambda: b.complete(prompt, max_tokens, seed, system),
 854 | +                if dl:                                 # ruling 5 (22:40): fail over instead of waiting
 855 | +                    text, usage, secs = _within(dl, lambda: b.complete(prompt, max_tokens, seed, system),
 856 |                                                  on_abandon=abandon, on_late=self._late)
 857 |                  else:
 858 |                      text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 859 |              except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 860 | -                booked = b.prompt_usd(prompt, system)  # abandon()
 861 | +                self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
 862 | +                booked = b.prompt_usd(prompt, system)
 863 |                  tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 864 |                                      "ruling 83 (a))"))
 865 |                  continue
 866 |              except RequestRejected as e:
 867 |                  self._settle(key)
 868 | +                self._note(role, b, False)
 869 |                  tried.append((name, f"refused this request: {e}"))
 870 |                  continue
 871 |              except Unavailable as e:
 872 |                  self._settle(key)
 873 | +                self._note(role, b, False)
 874 |                  self.down[name] = str(e)
 875 |                  tried.append((name, str(e)))
 876 |                  continue
 877 | @@ -925,13 +1222,15 @@ class Router:
 878 |              self._settle(key, b, usage, usd, role)
 879 |              if secs >= self.slow_log_s:                # item 55: an answer this slow is evidence too
 880 |                  self._log_slow({"kind": "answered_slowly", "threshold_s": self.slow_log_s, "role": role, "model": name,
 881 | -                                "vendor": b.vendor, "deadline_s": deadline_s, "seconds": round(secs, 2),
 882 | +                                "vendor": b.vendor, "deadline_s": dl, "seconds": round(secs, 2),
 883 |                                  "prompt_chars": len(prompt_text(prompt)), "max_tokens": max_tokens,
 884 |                                  "in": (usage or {}).get("in"),
 885 |                                  "out": (usage or {}).get("out")})
 886 |              if not (isinstance(text, str) and text.strip()):   # an empty reply: this call moves on (audit C2 K7)
 887 | +                self._note(role, b, False)
 888 |                  tried.append((name, "refused this request: an empty reply"))
 889 |                  continue
 890 | +            self._note(role, b, True)                  # ruling 87: a Heimdall family answered inside its deadline
 891 |              recorded = ""
 892 |              if path and isinstance(text, str) and text.strip():
 893 |                  self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
 894 | @@ -939,8 +1238,11 @@ class Router:
 895 |                                      "text": text,
 896 |                                      "usage": usage, "usd": usd, "seconds": round(secs, 2)})
 897 |                  recorded = path
 898 | -            return Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 899 | -                         recorded)
 900 | +            out = Reply(text, name, b.vendor, round(secs, 2), usage, usd, False, tried, notices, b.family, False,
 901 | +                        recorded)
 902 | +            if self.shadow and role in SHADOW_ROLES and self._shadow_of(role) not in (None, name):
 903 | +                self._shadow_ask(role, prompt, max_tokens, seed, system, out)     # ruling 86: asked, never deciding
 904 | +            return out
 905 |          if self.replay:
 906 |              raise ReplayMiss(f"{role}: no recorded exchange ({tried})")
 907 |          raise ProviderError(f"{role}: every back-end unavailable: {tried}")
 908 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 909 | index 74013a1..b034586 100644
 910 | --- a/tests/package/proof_ledger.py
 911 | +++ b/tests/package/proof_ledger.py
 912 | @@ -56,6 +56,8 @@ sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
 913 |  sys.path.insert(0, HERE)
 914 |  import eligibility as E  # noqa: E402
 915 |  import candidates as CA  # noqa: E402
 916 | +import heimdall_health as HH  # noqa: E402
 917 | +import shadow86 as SH  # noqa: E402
 918 |  import ledger_build as LB  # noqa: E402
 919 |  import moments as M  # noqa: E402
 920 |  import package as PK  # noqa: E402
 921 | @@ -69,6 +71,7 @@ import lock_precheck as LP  # noqa: E402
 922 |  
 923 |  REGISTRY = os.path.join(HERE, "proof", "CANDIDATES.json")     # ruling 66: the candidates, kept
 924 |  SPOTLIGHTS = os.path.join(HERE, "proof", "SPOTLIGHTS.json")   # ruling 90: one spotlight per channel per ET day
 925 | +STATE_MD = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_STATE.md")   # ruling 87: a switch on line 1
 926 |  
 927 |  
 928 |  def delivered_pins(paths):
 929 | @@ -108,6 +111,8 @@ def main(argv=None):
 930 |                      help="the adapter's publish window (horizon_h); RULING 76: at most 12 h, never widened")
 931 |      ap.add_argument("--work-dir", default=os.path.join(PL.SCRATCH, "lv2"))
 932 |      ap.add_argument("--word-pass", default=LB.WORD_PASS, help="the word-pass worker's rows (read-only)")
 933 | +    ap.add_argument("--routing", choices=P.ROUTINGS, default=None,
 934 | +                    help="RULING 85: 'today' or 'heimdall_first' (default: model_providers.json routing.mode)")
 935 |      ap.add_argument("--from-candidate", metavar="BUILD_DIR[:N]",
 936 |                      help="RULING 66: try ONLY the line-up that passed the clips-alone verdict in this earlier build's "
 937 |                           "record (its tried[N]; default the first that passed), as it was judged")
 938 | @@ -183,8 +188,17 @@ def main(argv=None):
 939 |          json.dump({"since": since.isoformat(), "publish_window_h": a.hours, "delivered_pins": pins,
 940 |                     "adapter_report": rep, "inputs": inputs, "delivered": delivered, "moments": moments},
 941 |                    f, indent=1, default=str)
 942 | +    rt = json.load(open(P.CONFIG)).get("routing") or {}
 943 | +    routing = a.routing or rt.get("mode") or "today"
 944 | +    shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 945 | +    if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
 946 | +        shadow = rt.get("shadow") or None
 947 |      router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 948 | -                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(), deadline_log=PL.DEADLINE_LOG)
 949 | +                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 950 | +                      routing=routing, shadow=shadow, shadow_log=os.path.join(out_dir, "SHADOW86.jsonl"),
 951 | +                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD)    # ruling 87
 952 | +    say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 953 | +        + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 954 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 955 |      if spent0 >= PL.LY_STOP_USD:
 956 |          say(f"REFUSED (ruling 48): this order's ledger stands at ${spent0:.2f} vendor-reported (the estimate where a "
 957 | @@ -333,8 +347,14 @@ def main(argv=None):
 958 |                          "hooks_4": len(hp.get("passing") or []) if isinstance(hp.get("passing"), list) else None}
 959 |      say(f"  RULING 76 (d): {res['ruling_76']['inside_12h']} moments inside 12 h, {res['ruling_76']['cleared']} "
 960 |          f"cleared, {res['ruling_76']['cuttable']} cuttable, {res['ruling_76']['hooks_4']} hooks >= 4")
 961 | +    res["routing"] = router.routing                # RULING 85: which routing decided this build
 962 | +    res["mode_at_end"] = router.mode()             # RULING 87: plan_b when Heimdall was down at the end
 963 | +    if router.shadow:                              # RULING 86: every shadow answer in (the pin, if any, is already
 964 | +        left = router.shadow_wait(900.0)           # written and logged above), then the side-by-side
 965 | +        res["shadow86"] = SH.report(out_dir, res, missing=left)
 966 | +        say(f"  SHADOW (ruling 86): {res['shadow86'].get('summary')}")
 967 |      try:                                         # the record is written whatever the ledger says (audit 0707 C1)
 968 | -        after = round(router.spent(), 4)
 969 | +        after = round(router.spent(), 4)         # (after the shadows: their spend is in it)
 970 |      except Exception as e:                       # noqa: BLE001
 971 |          after = f"unreadable: {type(e).__name__}: {str(e)[:120]}"
 972 |      res["spend_ruling_48"] = {"before": round(spent0, 4), "after": after, "cap": PL.LY_LIMIT_USD,
 973 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
 974 | index dc5fe4a..702160b 100644
 975 | --- a/tests/package/proof_ly.py
 976 | +++ b/tests/package/proof_ly.py
 977 | @@ -64,14 +64,34 @@ WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b",
 978 |  SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
 979 |  
 980 |  
 981 | -def chains():
 982 | -    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
 983 | +def chains(routing=None):
 984 | +    """Every role's chain for the routing without the frozen legs; the writer = two Heimdall families, then Grok.
 985 | +    RULING 85: routing "today" (the chains under roles) or "heimdall_first" (model_providers.json routing.heimdall_first,
 986 | +    Grok last); default: the config's routing.mode."""
 987 |      cfg = json.load(open(P.CONFIG))
 988 | -    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
 989 | +    rt = cfg.get("routing") or {}
 990 | +    routing = routing or rt.get("mode") or "today"
 991 | +    if routing not in P.ROUTINGS:
 992 | +        raise ValueError(f"routing must be one of {P.ROUTINGS}, not {routing!r}")
 993 | +    routed = rt.get(routing) or {}
 994 | +    out = {r: [b for b in ((routed.get(r) if routing != "today" else None) or v["chain"]) if not b.startswith(FROZEN)]
 995 | +           for r, v in cfg["roles"].items()}
 996 | +    for k, ch in routed.items():                 # RULING 88: a verdict type's own list ("<role>:<kind>")
 997 | +        if ":" in k and isinstance(ch, list):
 998 | +            out[k] = [b for b in ch if not b.startswith(FROZEN)]
 999 |      out["angle_write"] = list(WRITERS)
1000 |      return out
1001 |  
1002 |  
1003 | +def plan_b_chains():
1004 | +    """RULING 87: the Plan B chains (model_providers.json routing.plan_b): Grok mainly, then any other outside key that
1005 | +    answers. OpenAI and Anthropic stay in (they are tried, never assumed: an account without credit is Unavailable at
1006 | +    its first call and down for the run); only GPU0's local model is out (never this builder's)."""
1007 | +    cfg = json.load(open(P.CONFIG))
1008 | +    return {r: [b for b in ch if not b.startswith(("local:", "openai_stt:"))]
1009 | +            for r, ch in ((cfg.get("routing") or {}).get("plan_b") or {}).items()}
1010 | +
1011 | +
1012 |  def ledger():
1013 |      try:
1014 |          d = json.load(open(SPEND))
1015 | diff --git a/tests/package/test_ledger_build.py b/tests/package/test_ledger_build.py
1016 | index 99f713c..ea67906 100644
1017 | --- a/tests/package/test_ledger_build.py
1018 | +++ b/tests/package/test_ledger_build.py
1019 | @@ -826,5 +826,63 @@ class TestDriverRefuses(unittest.TestCase):
1020 |                  self.assertIn("overlaps a delivered moment", why["m1"])
1021 |  
1022 |  
1023 | +
1024 | +class TestRuling85NoXai(unittest.TestCase):
1025 | +    """RULINGS 85 + 88 (22:15 Nov 13), on the real config and the real Router's skip rule (no model is called):
1026 | +    the lists per verdict type under heimdall_first; with xAI answering nothing and deepseek writing, every type but
1027 | +    one still has a Heimdall family off the writer, and step A's two verdicts come from two families. The one gap:
1028 | +    coherence keeps Grok with deepseek alone behind it (88 (d): glm out; (e): qwen never decides it), so when deepseek
1029 | +    writes and xAI is down, coherence has no family and the package fails closed."""
1030 | +
1031 | +    @staticmethod
1032 | +    def pl():
1033 | +        sys.path.insert(0, HERE)
1034 | +        import proof_ly as PL
1035 | +        return PL
1036 | +
1037 | +    def pick(self, r, role, av=(), af=(), am=(), kind=None):
1038 | +        PL = self.pl()
1039 | +        for name in r.chain(role, kind):
1040 | +            b = r.backends.get(name)
1041 | +            if b is not None and r._skip(name, b, set(av), set(am), set(af)) is None and not \
1042 | +                    name.startswith(PL.FROZEN):
1043 | +                return name
1044 | +        return None
1045 | +
1046 | +    def test_ruling_88s_lists_and_xai_answering_nothing(self):
1047 | +        PL = self.pl()
1048 | +        X, DS, G, Q = ("xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash",
1049 | +                       "heimdall:z-ai/glm-5.3-flash", "heimdall:qwen/qwen3.8-27b")
1050 | +        ch = PL.chains("heimdall_first")
1051 | +        self.assertEqual(ch["fidelity_verdict"], [Q, G, X])                       # (a): Heimdall, Grok last
1052 | +        self.assertEqual(ch["exclusion_verdict"], [G, Q, X])
1053 | +        self.assertEqual(ch["context_verdict:step_a_first"], [Q, G, DS, X])        # (c): Heimdall first
1054 | +        self.assertEqual(ch["context_verdict:step_a_second"][0], X)               # (c): Grok confirms
1055 | +        self.assertEqual(ch["context_verdict:step_c"], [X, G, DS])                 # (b) / (e): no qwen
1056 | +        self.assertEqual(ch["coherence_verdict:coherence"], [X, DS])              # (d) / (e): no glm, no qwen
1057 | +        self.assertEqual(ch["coherence_verdict:clips_alone"], [X, Q, DS])         # (d): no glm
1058 | +        today = PL.chains("today")                                                 # (d) and (e) hold today too
1059 | +        self.assertEqual((today["coherence_verdict:coherence"], today["context_verdict:step_c"]), ([X, DS], [X, DS, G]))
1060 | +        r = PL.P.Router(env_path="/nonexistent", routing="heimdall_first", chains=ch)
1061 | +        for n in [n for n in r.backends if n.startswith("xai")]:
1062 | +            r.down[n] = "xAI answers nothing (the test)"
1063 | +        w = r.backends[DS]                                                         # the writer
1064 | +        got = {(role, kind): self.pick(r, role, {w.vendor}, {w.family}, kind=kind) for role, kind in (
1065 | +            ("fidelity_verdict", None), ("exclusion_verdict", None), ("speaker_verdict", None),
1066 | +            ("viewer_takeaway", None), ("context_verdict", "step_c"), ("coherence_verdict", "hook"),
1067 | +            ("coherence_verdict", "clips_alone"), ("coherence_verdict", "coherence"))}
1068 | +        self.assertEqual(got, {("fidelity_verdict", None): Q, ("exclusion_verdict", None): G,
1069 | +                               ("speaker_verdict", None): G, ("viewer_takeaway", None): G,
1070 | +                               ("context_verdict", "step_c"): G, ("coherence_verdict", "hook"): Q,
1071 | +                               ("coherence_verdict", "clips_alone"): Q,
1072 | +                               ("coherence_verdict", "coherence"): None})          # THE GAP (fails closed)
1073 | +        first = self.pick(r, "context_verdict", {w.vendor}, {w.family}, kind="step_a_first")
1074 | +        fb = r.backends[first]
1075 | +        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
1076 | +        self.assertEqual((first, second), (Q, G))                                  # two Heimdall families, Grok down
1077 | +        r.down.clear()
1078 | +        second = self.pick(r, "context_verdict", {fb.vendor}, {fb.family}, kind="step_a_second")
1079 | +        self.assertEqual(second, X)                                                # (c): Grok confirms when it answers
1080 | +
1081 |  if __name__ == "__main__":
1082 |      unittest.main()
1083 | diff --git a/tests/providers/test_heimdall_health.py b/tests/providers/test_heimdall_health.py
1084 | new file mode 100644
1085 | index 0000000..e47a60c
1086 | --- /dev/null
1087 | +++ b/tests/providers/test_heimdall_health.py
1088 | @@ -0,0 +1,289 @@
1089 | +#!/usr/bin/env python3
1090 | +"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE (pipeline/heimdall_health.py and its use in
1091 | +providers.Router). Offline: a temporary state file, the test's own clock, fake back-ends."""
1092 | +import json
1093 | +import os
1094 | +import sys
1095 | +import tempfile
1096 | +import unittest
1097 | +from datetime import datetime, timedelta, timezone
1098 | +
1099 | +HERE = os.path.dirname(os.path.abspath(__file__))
1100 | +REPO = os.path.dirname(os.path.dirname(HERE))
1101 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1102 | +sys.path.insert(0, HERE)
1103 | +import heimdall_health as HH  # noqa: E402
1104 | +import providers as P  # noqa: E402
1105 | +from test_providers import Fake  # noqa: E402
1106 | +
1107 | +T0 = datetime(2026, 11, 14, 2, 0, tzinfo=timezone.utc)
1108 | +
1109 | +
1110 | +class TestHealth(unittest.TestCase):
1111 | +    def setUp(self):
1112 | +        HH._SEEN.clear()
1113 | +        self.d = tempfile.TemporaryDirectory()
1114 | +        self.state = os.path.join(self.d.name, "HEALTH.json")
1115 | +        self.ev = os.path.join(self.d.name, "DEADLINES.jsonl")
1116 | +        self.md = os.path.join(self.d.name, "STATE.md")
1117 | +        with open(self.md, "w") as f:
1118 | +            f.write("21:00 ET: line one as it was.\n\n## a section\n")
1119 | +
1120 | +    def tearDown(self):
1121 | +        self.d.cleanup()
1122 | +
1123 | +    def kw(self, t):
1124 | +        return {"path": self.state, "now": t, "evidence": self.ev, "state_md": self.md}
1125 | +
1126 | +    def test_fifteen_minutes_with_no_family_answering_is_plan_b_and_every_switch_is_on_record(self):
1127 | +        self.assertEqual(HH.note(False, **self.kw(T0)), "heimdall_first")
1128 | +        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=14, seconds=59))), "heimdall_first")
1129 | +        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=15))), "plan_b")
1130 | +        st = json.load(open(self.state))
1131 | +        self.assertEqual([s["to"] for s in st["switches"]], ["plan_b"])
1132 | +        with open(self.ev) as f:
1133 | +            self.assertEqual([json.loads(x)["kind"] for x in f], ["switch"])
1134 | +        first = open(self.md).read().split("\n")[0]
1135 | +        self.assertTrue(first.endswith("| 21:00 ET: line one as it was."), first)     # one physical line, prepended
1136 | +        self.assertIn("ET: SWITCHED TO PLAN B (NO HEIMDALL FAMILY ANSWERED", first)
1137 | +
1138 | +    def test_one_answer_stops_the_clock(self):
1139 | +        HH.note(False, **self.kw(T0))
1140 | +        HH.note(True, **self.kw(T0 + timedelta(minutes=10)))           # any family answering: not down
1141 | +        self.assertEqual(HH.note(False, **self.kw(T0 + timedelta(minutes=20))), "heimdall_first")
1142 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=34))), "heimdall_first")
1143 | +        self.assertEqual(HH.mode(**self.kw(T0 + timedelta(minutes=35))), "plan_b")   # idle: the clock still runs
1144 | +
1145 | +    def test_the_probe_every_2_minutes_and_back_after_3_answers_in_a_row(self):
1146 | +        k = lambda m: self.kw(T0 + timedelta(minutes=m))
1147 | +        self.assertFalse(HH.probe_due(self.state, T0))                  # healthy: no probe
1148 | +        HH.note(False, **k(0))
1149 | +        self.assertTrue(HH.probe_due(self.state, T0))
1150 | +        HH.note(False, **k(15))                                          # down
1151 | +        self.assertEqual(HH.probe_result(True, **k(16)), "plan_b")
1152 | +        self.assertFalse(HH.probe_due(self.state, T0 + timedelta(minutes=17)))      # 2 minutes apart
1153 | +        self.assertTrue(HH.probe_due(self.state, T0 + timedelta(minutes=18)))
1154 | +        self.assertEqual(HH.probe_result(False, **k(18)), "plan_b")      # a miss resets the streak
1155 | +        self.assertEqual(HH.probe_result(True, **k(20)), "plan_b")
1156 | +        self.assertEqual(HH.probe_result(True, **k(22)), "plan_b")
1157 | +        self.assertEqual(HH.probe_result(True, **k(24)), "heimdall_first")
1158 | +        st = json.load(open(self.state))
1159 | +        self.assertEqual([s["to"] for s in st["switches"]], ["plan_b", "heimdall_first"])
1160 | +        self.assertIsNone(st["failing_since_utc"])
1161 | +        self.assertIn("BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW)",
1162 | +                      open(self.md).read().split("\n")[0])
1163 | +
1164 | +    def test_a_drill_is_recorded_never_counted_and_answers_write_once_per_heartbeat(self):
1165 | +        HH._SEEN.clear()
1166 | +        for m in range(0, 40, 5):                                        # 40 minutes of drill failures
1167 | +            self.assertEqual(HH.note(False, drill=True, **self.kw(T0 + timedelta(minutes=m))), "heimdall_first")
1168 | +        st = json.load(open(self.state))
1169 | +        self.assertEqual((st["drills"], st["failing_since_utc"], st["notes"]), (8, None, 0))
1170 | +        HH.note(True, **self.kw(T0))
1171 | +        HH.note(True, **self.kw(T0 + timedelta(seconds=5)))              # inside the heartbeat: not written
1172 | +        self.assertEqual(json.load(open(self.state))["notes"], 1)
1173 | +        HH.note(False, **self.kw(T0 + timedelta(seconds=6)))             # a failure is always written
1174 | +        HH.note(True, **self.kw(T0 + timedelta(seconds=7)))              # and the next answer too
1175 | +        st = json.load(open(self.state))
1176 | +        self.assertEqual((st["notes"], st["failing_since_utc"]), (3, None))
1177 | +        HH._SEEN.clear()
1178 | +
1179 | +    def test_an_unreadable_state_is_never_guessed(self):
1180 | +        with open(self.state, "w") as f:
1181 | +            f.write("{ broken")
1182 | +        for fn in (lambda: HH.note(True, **self.kw(T0)), lambda: HH.mode(**self.kw(T0))):
1183 | +            with self.assertRaises(HH.HealthUnreadable):
1184 | +                fn()
1185 | +        self.assertEqual(open(self.state).read(), "{ broken")
1186 | +        r = P.Router.__new__(P.Router)                                     # the router: no verdict, never a crash
1187 | +        r.health, r.deadline_log, r.state_md, r.routing = self.state, None, None, "heimdall_first"
1188 | +        with self.assertRaises(P.ProviderError):                           # (audit 0108 C1, glm)
1189 | +            r.mode()
1190 | +
1191 | +
1192 | +class TestRouterPlanB(unittest.TestCase):
1193 | +    """providers.Router: a Heimdall verdict or writer call's outcome is noted; in plan_b the roles of plan_b_chains run
1194 | +    on them at once (Grok first)."""
1195 | +
1196 | +    def setUp(self):
1197 | +        self.d = tempfile.TemporaryDirectory()
1198 | +        self.cfg = os.path.join(self.d.name, "cfg.json")
1199 | +        json.dump({"schema": "pp.providers/1",
1200 | +                   "backends": {"xai:grok": {"vendor": "xai", "model": "grok", "family": "grok"},
1201 | +                                "heimdall:deepseek": {"vendor": "heimdall", "model": "deepseek",
1202 | +                                                      "family": "deepseek"}},
1203 | +                   "roles": {"coherence_verdict": {"chain": ["heimdall:deepseek", "xai:grok"]},
1204 | +                             "mine": {"chain": ["heimdall:deepseek"]}},
1205 | +                   "routing": {"mode": "today", "verdict_roles": ["coherence_verdict"]}}, open(self.cfg, "w"))
1206 | +        self.state = os.path.join(self.d.name, "HEALTH.json")
1207 | +
1208 | +    def tearDown(self):
1209 | +        self.d.cleanup()
1210 | +
1211 | +    def router(self):
1212 | +        r = P.Router(self.cfg, env_path="/nonexistent", health=self.state,
1213 | +                     plan_b_chains={"coherence_verdict": ["xai:grok"]})
1214 | +        h = P.HeimdallBackend("heimdall:deepseek", {"model": "deepseek", "family": "deepseek"}, "/nonexistent")
1215 | +        h.complete = lambda *a, **k: ("d", {"in": 1, "out": 1}, 0.01)
1216 | +        r.backends = {"xai:grok": Fake("xai:grok", "xai", answer="x", family="grok"), "heimdall:deepseek": h}
1217 | +        r.start_probe = lambda *a, **k: None                              # no thread in a unit test
1218 | +        return r
1219 | +
1220 | +    def test_outcomes_are_noted_and_plan_b_takes_the_chain(self):
1221 | +        r = self.router()
1222 | +        self.assertEqual(r.call("coherence_verdict", "p").backend, "heimdall:deepseek")
1223 | +        st = json.load(open(self.state))
1224 | +        self.assertIsNotNone(st["last_answer_utc"])
1225 | +        self.assertEqual(st["notes"], 1)
1226 | +        r.call("mine", "p")                                               # not a verdict or a write: not noted
1227 | +        self.assertEqual(json.load(open(self.state))["notes"], 1)
1228 | +        HH.note(False, self.state, now=datetime.now(timezone.utc) - timedelta(minutes=16))
1229 | +        HH.note(False, self.state)                                        # 16 minutes with no answer: plan_b
1230 | +        self.assertEqual(r.mode(), "plan_b")
1231 | +        self.assertEqual(r.chain("coherence_verdict"), ["xai:grok"])
1232 | +        self.assertEqual(r.call("coherence_verdict", "p").backend, "xai:grok")   # the whole pin stage, at once
1233 | +        self.assertEqual(r.chain("mine"), ["heimdall:deepseek"])          # a role Plan B does not name: as is
1234 | +
1235 | +    def test_a_probe_round_reaches_a_family_marked_down_and_restores_the_mark_when_it_fails(self):
1236 | +        r = self.router()
1237 | +        r.down["heimdall:deepseek"] = "HTTP 503 earlier this run"
1238 | +        self.assertTrue(r.probe_once(["heimdall:deepseek"]))             # it answers now: the mark is lifted
1239 | +        self.assertNotIn("heimdall:deepseek", r.down)
1240 | +
1241 | +        def down(*a, **k):
1242 | +            raise P.Unavailable("HTTP 503")
1243 | +        r.backends["heimdall:deepseek"].complete = down
1244 | +        r.down["heimdall:deepseek"] = "HTTP 503 earlier this run"
1245 | +        self.assertFalse(r.probe_once(["heimdall:deepseek"]))
1246 | +        self.assertIn("heimdall:deepseek", r.down)                       # still down: marked as before
1247 | +        self.assertFalse(os.path.exists(os.path.join(self.d.name, "rec")))   # a probe is never recorded
1248 | +
1249 | +    def test_a_failing_heimdall_call_is_noted_as_not_answered(self):
1250 | +        r = self.router()
1251 | +
1252 | +        def down(*a, **k):
1253 | +            raise P.Unavailable("HTTP 503")
1254 | +        r.backends["heimdall:deepseek"].complete = down
1255 | +        self.assertEqual(r.call("coherence_verdict", "p").backend, "xai:grok")    # ruling 82's chain moved on
1256 | +        st = json.load(open(self.state))
1257 | +        self.assertIsNotNone(st["failing_since_utc"])
1258 | +        self.assertIsNone(st["last_answer_utc"])
1259 | +
1260 | +
1261 | +
1262 | +class TestLocalJudge(unittest.TestCase):
1263 | +    """RULING 87: the integrator's GPU0 judge (Plan B, one outside family): a request file in this worktree, the answer
1264 | +    read from its results; an error or no answer in time is no verdict; the wait outlasts ruling 82's 120 s."""
1265 | +
1266 | +    def setUp(self):
1267 | +        self.d = tempfile.TemporaryDirectory()
1268 | +        self.req, self.res = os.path.join(self.d.name, "req"), os.path.join(self.d.name, "res")
1269 | +        os.makedirs(self.res)
1270 | +        self.b = P.LocalJudgeBackend("local_judge:gemma3:27b", {"model": "gemma3:27b", "family": "gemma",
1271 | +                                                                "deadline_floor_s": 2400}, "/nonexistent")
1272 | +        self.b.REQUESTS, self.b.RESULTS, self.b.POLL_S = self.req, self.res, 0.05
1273 | +
1274 | +    def tearDown(self):
1275 | +        self.d.cleanup()
1276 | +
1277 | +    def answer_when_asked(self, body):
1278 | +        import threading
1279 | +        import time as _t
1280 | +
1281 | +        def run():                                   # answers the one request that has no answer yet
1282 | +            for _ in range(500):
1283 | +                for n in sorted(os.listdir(self.req)) if os.path.isdir(self.req) else []:
1284 | +                    if not n.endswith(".json"):
1285 | +                        continue
1286 | +                    rid = n[:-len(".json")]
1287 | +                    rq = json.load(open(os.path.join(self.req, n)))
1288 | +                    import hashlib                       # the integrator's prompt_id
1289 | +                    pid = hashlib.sha256(json.dumps([rq["prompt"], rq["max_tokens"], rq["seed"]]).encode()) \
1290 | +                        .hexdigest()[:20]
1291 | +                    out = os.path.join(self.res, f"{rid}.{pid}.json")
1292 | +                    if not os.path.exists(out):
1293 | +                        with open(out, "w") as f:
1294 | +                            json.dump(dict(body, request_id=rid, prompt_id=pid), f)
1295 | +                        return
1296 | +                _t.sleep(0.02)
1297 | +        threading.Thread(target=run, daemon=True).start()
1298 | +
1299 | +    def test_a_request_is_written_and_its_answer_read(self):
1300 | +        self.answer_when_asked({"family": "step_a", "text": '{"excerpts": []}', "error": None})
1301 | +        text, usage, secs = self.b.complete("the step A prompt", 4000, 7)
1302 | +        self.assertEqual((text, usage["in"], usage["out"]), ('{"excerpts": []}', 0, 0))
1303 | +        stray = os.path.join(self.res, "pp-selectid.x.0000.json")         # another answer's file is never read
1304 | +        json.dump({"request_id": "other", "text": "{}"}, open(stray, "w"))
1305 | +        (name,) = os.listdir(self.req)
1306 | +        rq = json.load(open(os.path.join(self.req, name)))
1307 | +        self.assertEqual({k: rq[k] for k in ("family", "prompt", "max_tokens", "seed")},
1308 | +                         {"family": "step_a", "prompt": "the step A prompt", "max_tokens": 4000, "seed": 7})
1309 | +        self.assertTrue(self.b.free())
1310 | +
1311 | +    def test_an_error_or_no_answer_is_no_verdict(self):
1312 | +        self.answer_when_asked({"family": "step_a", "text": "", "error": "GPU0 busy"})
1313 | +        with self.assertRaises(P.RequestRejected):
1314 | +            self.b.complete("p", 100, 7)
1315 | +        self.b.WAIT_S = 0.2
1316 | +        with self.assertRaises(P.Unavailable):
1317 | +            self.b.complete("q", 100, 7)
1318 | +        with self.assertRaises(P.RequestRejected):
1319 | +            self.b.complete("q", 100, 7, system="no system message")
1320 | +
1321 | +    def test_a_torn_answer_file_is_read_again_never_final(self):
1322 | +        """Audit 0108 C1 (glm): an answer file read while it is being written is polled again until the deadline."""
1323 | +        import threading
1324 | +        import time as _t
1325 | +
1326 | +        def run():
1327 | +            for _ in range(500):
1328 | +                for n in sorted(os.listdir(self.req)) if os.path.isdir(self.req) else []:
1329 | +                    if not n.endswith(".json"):
1330 | +                        continue
1331 | +                    rid = n[:-len(".json")]
1332 | +                    rq = json.load(open(os.path.join(self.req, n)))
1333 | +                    import hashlib
1334 | +                    pid = hashlib.sha256(json.dumps([rq["prompt"], rq["max_tokens"], rq["seed"]]).encode()) \
1335 | +                        .hexdigest()[:20]
1336 | +                    out = os.path.join(self.res, f"{rid}.{pid}.json")
1337 | +                    with open(out, "w") as f:
1338 | +                        f.write('{"request_id": "' + rid)                   # half written
1339 | +                    _t.sleep(0.2)
1340 | +                    with open(out, "w") as f:
1341 | +                        json.dump({"request_id": rid, "prompt_id": pid, "text": "{}", "error": None}, f)
1342 | +                    return
1343 | +                _t.sleep(0.02)
1344 | +        threading.Thread(target=run, daemon=True).start()
1345 | +        self.assertEqual(self.b.complete("torn", 100, 7)[0], "{}")
1346 | +
1347 | +    def test_the_wait_outlasts_the_120_s_deadline_and_state_line_1_says_so_once(self):
1348 | +        cfg = os.path.join(self.d.name, "cfg.json")
1349 | +        json.dump({"schema": "pp.providers/1",
1350 | +                   "backends": {"local_judge:gemma3:27b": {"vendor": "local_judge", "model": "gemma3:27b",
1351 | +                                                           "family": "gemma", "deadline_floor_s": 2400}},
1352 | +                   "roles": {"context_verdict": {"chain": ["local_judge:gemma3:27b"]}}}, open(cfg, "w"))
1353 | +        md = os.path.join(self.d.name, "STATE.md")
1354 | +        open(md, "w").write("21:50 ET: line one.\n")
1355 | +        r = P.Router(cfg, env_path="/nonexistent", state_md=md)
1356 | +        r.backends["local_judge:gemma3:27b"] = self.b
1357 | +        seen = {}
1358 | +        orig = P._within
1359 | +
1360 | +        def spy(seconds, fn, **kw):
1361 | +            seen["deadline"] = seconds
1362 | +            return orig(seconds, fn, **kw)
1363 | +        P._within = spy
1364 | +        try:
1365 | +            self.answer_when_asked({"family": "step_a", "text": "{}", "error": None})
1366 | +            r.call("context_verdict", "p", 100, 7, deadline_s=120.0)
1367 | +            self.answer_when_asked({"family": "step_a", "text": "{}", "error": None})
1368 | +            r.call("context_verdict", "p2", 100, 7, deadline_s=120.0)
1369 | +        finally:
1370 | +            P._within = orig
1371 | +        self.assertEqual(seen["deadline"], 2400.0)
1372 | +        first = open(md).read().split("\n")[0]
1373 | +        self.assertEqual(first.count("PLAN B WITH ONE OUTSIDE FAMILY"), 1)
1374 | +        self.assertTrue(first.endswith("| 21:50 ET: line one."))
1375 | +
1376 | +if __name__ == "__main__":
1377 | +    unittest.main()
1378 | diff --git a/tests/providers/test_providers.py b/tests/providers/test_providers.py
1379 | index b7498ef..7d9e0a6 100644
1380 | --- a/tests/providers/test_providers.py
1381 | +++ b/tests/providers/test_providers.py
1382 | @@ -481,5 +481,196 @@ class TestRouter(unittest.TestCase):
1383 |              self.assertEqual(meta["backend"], "xai:z")
1384 |  
1385 |  
1386 | +
1387 | +class TestRuling85Routing(unittest.TestCase):
1388 | +    """RULING 85 (21:15 Nov 13): Heimdall first for every verdict, Grok last, behind a switch; the two-family rule kept
1389 | +    INSIDE Heimdall (each family its own maker); the 20:33 order: ruling 82's 120 s on Heimdall for every verdict role,
1390 | +    and an answer out of contract moves on (providers.call_parsed)."""
1391 | +
1392 | +    def cfg(self, d, mode="today"):
1393 | +        p = os.path.join(d, "cfg.json")
1394 | +        json.dump({"schema": "pp.providers/1",
1395 | +                   "backends": {"xai:grok": {"vendor": "xai", "model": "grok", "family": "grok"},
1396 | +                                "heimdall:deepseek": {"vendor": "heimdall", "model": "deepseek", "family": "deepseek"},
1397 | +                                "heimdall:glm": {"vendor": "heimdall", "model": "glm", "family": "glm"},
1398 | +                                "heimdall:qwen": {"vendor": "heimdall", "model": "qwen", "family": "qwen"}},
1399 | +                   "roles": {"coherence_verdict": {"chain": ["xai:grok", "heimdall:deepseek", "heimdall:glm",
1400 | +                                                             "heimdall:qwen"]},
1401 | +                             "mine": {"chain": ["heimdall:qwen", "xai:grok"]}},
1402 | +                   "routing": {"mode": mode, "verdict_roles": ["coherence_verdict"],
1403 | +                               "verdict_deadline_s": {"heimdall": 120},
1404 | +                               "heimdall_first": {"coherence_verdict": ["heimdall:deepseek", "heimdall:glm",
1405 | +                                                                        "heimdall:qwen", "xai:grok"]}}}, open(p, "w"))
1406 | +        return p
1407 | +
1408 | +    def fakes(self):
1409 | +        return [Fake("xai:grok", "xai", answer="x", family="grok"),
1410 | +                Fake("heimdall:deepseek", "heimdall", answer="d", family="deepseek"),
1411 | +                Fake("heimdall:glm", "heimdall", answer="g", family="glm"),
1412 | +                Fake("heimdall:qwen", "heimdall", answer="q", family="qwen")]
1413 | +
1414 | +    def router(self, d, mode=None, cfg_mode="today"):
1415 | +        r = P.Router(self.cfg(d, cfg_mode), env_path="/nonexistent", routing=mode)
1416 | +        fs = self.fakes()
1417 | +        if r.routing == "heimdall_first":          # the router's own init re-keyed its real back-ends; fakes too
1418 | +            for b in fs:
1419 | +                if b.vendor == "heimdall":
1420 | +                    b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
1421 | +        r.backends = {b.name: b for b in fs}
1422 | +        return r
1423 | +
1424 | +    def test_today_is_unchanged_and_heimdall_first_puts_grok_last(self):
1425 | +        import tempfile
1426 | +        with tempfile.TemporaryDirectory() as d:
1427 | +            t = self.router(d)
1428 | +            self.assertEqual(t.routing, "today")
1429 | +            self.assertEqual(t.call("coherence_verdict", "p").backend, "xai:grok")
1430 | +            self.assertEqual(t.chain("mine"), ["heimdall:qwen", "xai:grok"])
1431 | +            h = self.router(d, "heimdall_first")
1432 | +            self.assertEqual(h.chain("coherence_verdict"), ["heimdall:deepseek", "heimdall:glm", "heimdall:qwen",
1433 | +                                                            "xai:grok"])
1434 | +            self.assertEqual(h.chain("mine"), ["heimdall:qwen", "xai:grok"])   # a role the routing names not: as is
1435 | +            self.assertEqual(h.call("coherence_verdict", "p").backend, "heimdall:deepseek")
1436 | +            self.assertEqual(self.router(d, cfg_mode="heimdall_first").routing, "heimdall_first")  # the config's mode
1437 | +            with self.assertRaises(ValueError):
1438 | +                P.Router(self.cfg(d), env_path="/nonexistent", routing="grok_only")
1439 | +
1440 | +    def test_the_two_family_rule_inside_heimdall(self):
1441 | +        """A Heimdall writer (deepseek) is judged by another Heimdall family (glm) under heimdall_first; today the
1442 | +        vendor rule leaves only Grok; the router's own init re-keys a real Heimdall back-end's vendor."""
1443 | +        import tempfile
1444 | +        with tempfile.TemporaryDirectory() as d:
1445 | +            h = self.router(d, "heimdall_first")
1446 | +            r = h.call("coherence_verdict", "p", avoid_vendor={"heimdall/deepseek"}, avoid_family={"deepseek"})
1447 | +            self.assertEqual((r.backend, r.vendor), ("heimdall:glm", "heimdall/glm"))
1448 | +            t = self.router(d)
1449 | +            r = t.call("coherence_verdict", "p", avoid_vendor={"heimdall"}, avoid_family={"deepseek"})
1450 | +            self.assertEqual(r.backend, "xai:grok")
1451 | +            real = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first")
1452 | +            b = real.backends["heimdall:glm"]
1453 | +            self.assertEqual((b.vendor, P.gateway(b), real.backends["xai:grok"].vendor), ("heimdall/glm", "heimdall",
1454 | +                                                                                           "xai"))
1455 | +            self.assertEqual(P.gateway(P.Router(self.cfg(d), env_path="/nonexistent").backends["heimdall:glm"]),
1456 | +                             "heimdall")
1457 | +
1458 | +    def test_a_verdict_role_gets_120_s_on_heimdall_only(self):
1459 | +        import tempfile
1460 | +        with tempfile.TemporaryDirectory() as d:
1461 | +            h = self.router(d, "heimdall_first")
1462 | +            self.assertEqual(h.role_deadline("coherence_verdict", h.backends["heimdall:glm"]), 120.0)
1463 | +            self.assertIsNone(h.role_deadline("coherence_verdict", h.backends["xai:grok"]))
1464 | +            self.assertIsNone(h.role_deadline("mine", h.backends["heimdall:qwen"]))
1465 | +            slow = Slow("heimdall:deepseek", "heimdall/deepseek", "d", delay=0.6, family="deepseek")
1466 | +            slow.gateway = "heimdall"
1467 | +            h.backends["heimdall:deepseek"] = slow
1468 | +            h.config["routing"]["verdict_deadline_s"] = {"heimdall": 0.1}
1469 | +            r = h.call("coherence_verdict", "p")                 # deepseek is abandoned at 0.1 s: glm answers
1470 | +            self.assertEqual(r.backend, "heimdall:glm")
1471 | +            self.assertIn("abandoned at the deadline", r.tried[0][1])
1472 | +
1473 | +    def test_the_real_config_bounds_today_as_ruled_and_heimdall_first_everywhere(self):
1474 | +        """The 20:33 order bounds fidelity, coherence, step B, speaker and exclusion (120 s on Heimdall); step A's
1475 | +        first screen and step C stay unbounded today (8 clips a call); under heimdall_first every verdict is bounded."""
1476 | +        today, hf = P.Router(env_path="/nonexistent"), P.Router(env_path="/nonexistent", routing="heimdall_first")
1477 | +        ds, xs = "heimdall:deepseek/deepseek-v4.1-flash", "xai:grok-4.20-0309-reasoning"
1478 | +        for role in ("fidelity_verdict", "coherence_verdict", "viewer_takeaway", "speaker_verdict",
1479 | +                     "exclusion_verdict"):
1480 | +            self.assertEqual((today.role_deadline(role, today.backends[ds]), hf.role_deadline(role, hf.backends[ds])),
1481 | +                             (120.0, 120.0), role)
1482 | +            self.assertIsNone(today.role_deadline(role, today.backends[xs]))
1483 | +        self.assertIsNone(today.role_deadline("context_verdict", today.backends[ds]))
1484 | +        self.assertEqual(hf.role_deadline("context_verdict", hf.backends[ds]), 120.0)
1485 | +        self.assertIsNone(hf.role_deadline("angle_write", hf.backends[ds]))   # the writer keeps ruling 5's 300 s
1486 | +
1487 | +    def test_call_parsed_moves_on_past_an_answer_out_of_contract(self):
1488 | +        import tempfile
1489 | +        with tempfile.TemporaryDirectory() as d:
1490 | +            h = self.router(d, "heimdall_first")
1491 | +            h.backends["heimdall:deepseek"].answer = "not json"
1492 | +            r, v = P.call_parsed(h, "coherence_verdict", "p", lambda t: {"d": 1, "g": 2}[t])
1493 | +            self.assertEqual((r.backend, v), ("heimdall:glm", 2))
1494 | +            for b in h.backends.values():
1495 | +                b.answer = "bad"
1496 | +            with self.assertRaises(P.ProviderError) as e:
1497 | +                P.call_parsed(h, "coherence_verdict", "p", lambda t: {"d": 1}[t])
1498 | +            self.assertIn("answers out of contract", str(e.exception))
1499 | +            self.assertEqual({n: b.calls for n, b in h.backends.items()},          # the second run asks each model
1500 | +                             {"heimdall:deepseek": 2, "heimdall:glm": 2, "heimdall:qwen": 1, "xai:grok": 1})  # once
1501 | +
1502 | +    def test_the_writes_keep_their_gateway(self):
1503 | +        """package.build: every write stays on the angle's GATEWAY, so a Heimdall write may still fail over
1504 | +        deepseek -> qwen under heimdall_first, and Grok never writes there."""
1505 | +        import tempfile
1506 | +        with tempfile.TemporaryDirectory() as d:
1507 | +            h = self.router(d, "heimdall_first")
1508 | +            writers = ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
1509 | +            avoid = {P.gateway(h.backends[n]) for n in writers} - {P.gateway(h.backends["heimdall:deepseek"])}
1510 | +            self.assertEqual(avoid, {"xai"})
1511 | +            self.assertFalse({h.backends["heimdall:qwen"].vendor} & avoid)
1512 | +
1513 | +
1514 | +class TestRuling86Shadow(TestRuling85Routing):
1515 | +    """RULING 86 (21:18 Nov 13): the first pins under Heimdall-first are judged twice: Heimdall's families decide, and
1516 | +    Grok is asked the same prompt in SHADOW (recorded to shadow_log, never deciding)."""
1517 | +
1518 | +    def shadow_router(self, d, **kw):
1519 | +        r = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first", shadow={"*": "xai:grok"},
1520 | +                     shadow_log=os.path.join(d, "SHADOW.jsonl"), **kw)
1521 | +        fs = self.fakes()
1522 | +        for b in fs:
1523 | +            if b.vendor == "heimdall":
1524 | +                b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
1525 | +        r.backends = {b.name: b for b in fs}
1526 | +        return r
1527 | +
1528 | +    def lines(self, d):
1529 | +        p = os.path.join(d, "SHADOW.jsonl")
1530 | +        return [json.loads(x) for x in open(p)] if os.path.exists(p) else []
1531 | +
1532 | +    def test_a_heimdall_verdict_is_asked_of_grok_in_shadow_and_grok_never_decides(self):
1533 | +        import tempfile
1534 | +        with tempfile.TemporaryDirectory() as d:
1535 | +            r = self.shadow_router(d)
1536 | +            rep = r.call("coherence_verdict", "the prompt", 500, 7)
1537 | +            self.assertEqual((rep.backend, rep.text), ("heimdall:deepseek", "d"))      # Heimdall decides
1538 | +            self.assertEqual(r.shadow_wait(5), 0)
1539 | +            got = self.lines(d)
1540 | +            self.assertEqual([(x["role"], x["prompt"], x["deciding"]["backend"], x["deciding"]["text"],
1541 | +                               x["shadow"]["backend"], x["shadow"]["text"]) for x in got],
1542 | +                             [("coherence_verdict", "the prompt", "heimdall:deepseek", "d", "xai:grok", "x")])
1543 | +            self.assertEqual(r.backends["xai:grok"].calls, 1)
1544 | +            r.call("mine", "p")                                   # not a verdict: no shadow
1545 | +            r.backends["heimdall:deepseek"].fail = "down"
1546 | +            r.backends["heimdall:glm"].fail = "down"
1547 | +            r.backends["heimdall:qwen"].fail = "down"
1548 | +            self.assertEqual(r.call("coherence_verdict", "q").backend, "xai:grok")   # Grok decided: nothing to shadow
1549 | +            self.assertEqual(r.shadow_wait(5), 0)
1550 | +            self.assertEqual(len(self.lines(d)), 1)
1551 | +
1552 | +    def test_a_shadow_that_fails_is_on_record_and_stops_nothing(self):
1553 | +        import tempfile
1554 | +        with tempfile.TemporaryDirectory() as d:
1555 | +            r = self.shadow_router(d)
1556 | +            r.backends["xai:grok"].fail = "xAI is down"
1557 | +            self.assertEqual(r.call("coherence_verdict", "p").text, "d")
1558 | +            self.assertEqual(r.shadow_wait(5), 0)
1559 | +            (x,) = self.lines(d)
1560 | +            self.assertIn("xAI is down", x["shadow"]["error"])
1561 | +
1562 | +    def test_a_recorded_verdict_is_shadowed_too_and_the_shadow_back_end_must_exist(self):
1563 | +        import tempfile
1564 | +        with tempfile.TemporaryDirectory() as d:
1565 | +            r = self.shadow_router(d, record_dir=os.path.join(d, "rec"))
1566 | +            r.call("coherence_verdict", "p")
1567 | +            r.shadow_wait(5)
1568 | +            r.call("coherence_verdict", "p")                      # served from its recording
1569 | +            r.shadow_wait(5)
1570 | +            got = self.lines(d)
1571 | +            self.assertEqual([x["deciding"]["cached"] for x in got], [False, True])
1572 | +            self.assertEqual([x["shadow"]["cached"] for x in got], [False, True])   # the shadow's own recording
1573 | +            self.assertEqual(r.backends["xai:grok"].calls, 1)
1574 | +            with self.assertRaises(ValueError):
1575 | +                P.Router(self.cfg(d), env_path="/nonexistent", shadow={"*": "xai:nope"})
1576 | +
1577 |  if __name__ == "__main__":
1578 |      unittest.main()
1579 | 
```

---

You are auditing PACKAGE A of a change on branch pp-selectid (Protocol Pulse: the builder of sealed medley pins). It
is the router, the Heimdall health state, the provider config and the build driver. Package B (the verdict call
sites, the shadow report and the replay driver) is audited separately. Only state what you can verify from the diff;
if uncertain, say so; do not guess.

Background (static):
- providers.Router.call(role, ...) tries the role's chain of back-ends in order. It skips a back-end that is:
  - on a vendor or family the caller avoids (law L-s: a verdict never comes from the writer's vendor or family);
  - a model the caller avoids;
  - marked down for the run.
  It moves on when a back-end is unavailable, refuses, misses its deadline, or answers empty. The chain spent:
  ProviderError (no verdict, never a pass).
- Each paid call reserves its upper bound on the spend ledger (ruling 48) and settles after. Ruling 83: a call
  abandoned at its deadline is booked at its prompt tokens; a late answer replaces that booking.
- Back-ends are: xAI Grok (vendor xai, family grok); Heimdall, a gateway to several model families (vendor heimdall:
  deepseek, glm, qwen, nemotron); Anthropic and OpenAI (out of credit); a local gemma3:27b on GPU0 (never this
  builder's).
- Every verdict today runs Grok FIRST: step A's first verdict, clips-alone, coherence, hook ratings, fidelity, step B,
  step C, speaker, exclusion, visual. Grok costs about ten times Heimdall per call, and the card behind it may be
  declined.

The orders (verbatim excerpts):
- 20:33 Nov 13: "Ruling 82's chain (deepseek -> glm-5.3-flash -> qwen3.8-27b, 120 s a call, an out-of-contract answer
  moves on, an outage is never a verdict) applies to every step that today has one Heimdall model as its only route
  when xAI is the writer or is down: the fidelity verdict, coherence / clips-alone / hook ratings, step B, the speaker
  and exclusion verdicts. The family rules stay: a verdict never comes from the family that wrote the line it judges,
  and step A's two verdicts are from two families."
- RULING 85 (21:15, locked 21:18): "HEIMDALL FIRST FOR EVERY VERDICT, GROK LAST. ... THE ROUTING I will rule from that
  table [the replay], but build it now behind a switch: each verdict type has an ordered list of model FAMILIES; the
  two-family rule (step A: two verdicts from two families; no verdict from the family that wrote the line) is
  satisfied INSIDE Heimdall wherever two Heimdall families both pass the replay for that type; Grok is the last entry
  of every list (used only when Heimdall's families are down or split), and the pipeline must complete a video with
  xAI answering nothing at all."
- RULING 86 (21:18): "The first pin sealed under Heimdall-first routing is judged TWICE: Heimdall's families decide
  (that is the pin), and Grok is asked the same prompts once in SHADOW (recorded, never deciding ...). I get the
  side-by-side per verdict ...: every decision where they differ, which was stricter, and whether the pin would have
  sealed under Grok. ... After three pins with no decision-changing difference, the shadow stops."
- RULING 87 (21:18): "PLAN B, THE FAIL-SAFE. Heimdall is 'down' when NO Heimdall family answers a verdict or writer
  call inside its deadline for 15 MINUTES running (a cheap health probe every 2 min while calls are failing; one model
  down is not 'down' ...). When down: switch the whole pin stage to PLAN B at once: Grok mainly, then any other outside
  key that answers (the Gemini key is fenced to this pipeline and may be used here; OpenAI and Anthropic when they have
  credit: probe, do not assume), keeping the two-family rule with whatever two families answer; if only ONE outside
  family answers, step A's second verdict is the local gemma3:27b on GPU0 through the integrator's judge service, and
  STATE line 1 says so. Return to Heimdall-first when its probe has answered 3 times in a row. Every switch ... is
  written to STATE line 1 in capitals with the time, and to the Heimdall evidence file. The same switch covers the
  miner and the writer ... Plan B's spend counts on the same ledger and the same cap ..."

- RULING 88 (22:15, from the replay's interim): "(a) fidelity and exclusion MOVE to Heimdall now ... (two Heimdall
  families, Grok last). (b) step C, hook rating: MOVE when the full table holds the interim numbers (98-100 %). (c) STEP A
  stays two families with Grok as one of them, but the ORDER changes: the Heimdall verdict is asked FIRST; a clip
  Heimdall refuses is refused and Grok is never asked; only a clip Heimdall passes goes to Grok to confirm. ... (d)
  clips-alone and coherence keep Grok until the table is complete; glm is out of those two (out-of-contract answers).
  (e) qwen failed two anchors: qwen is never the deciding family on coherence or step C."

The change (package A):
1. model_providers.json:
   - roles: the 20:33 chains. fidelity / coherence / speaker / exclusion gain glm and qwen after deepseek;
     viewer_takeaway (step B) gains deepseek and glm before qwen.
   - backends: google:gemini-2.5-pro (Plan B only; key GEMINI_API_KEY_MEDLEY, sent in a header; no vendor cost, so
     the estimate stands). local_judge:gemma3:27b (Plan B only; deadline_floor_s 2400).
   - RULING 88: Router.chain(role, kind) and call(..., kind): a verdict TYPE may have its own list "<role>:<kind>"
     (step_a_first, step_a_second, step_c, hook, clips_alone, coherence); the recordings stay keyed by role. Under
     heimdall_first: fidelity [qwen, glm, Grok]; exclusion [glm, qwen, Grok]; step_a_first [qwen, glm, deepseek, Grok];
     step_a_second [Grok, qwen, glm, deepseek]; step_c [Grok, glm, deepseek]; hook [Grok, qwen, deepseek, glm];
     clips_alone [Grok, qwen, deepseek]; coherence [Grok, deepseek]; speaker / step B [Grok, deepseek, glm, qwen].
     Under today: per-type lists only for (d)/(e): coherence [Grok, deepseek], clips_alone [Grok, deepseek, qwen],
     step_c [Grok, deepseek, glm]; every role keeps its chain.
   - "routing":
     - mode (today);
     - verdict_roles;
     - verdict_deadline_s {heimdall: 120};
     - today_unbounded [context_verdict]: today, step A's first screen and step C keep no deadline (their Heimdall
       fallback carries 8 clips a call; ruling 82 bounded only the second screen);
     - heimdall_first: deepseek, glm, qwen, then Grok, for every verdict role (the per-type order is set from the
       replay);
     - plan_b: Grok, Gemini, OpenAI, Anthropic; context_verdict also gets local_judge;
     - shadow: Grok (grok-4.7 for visual_check);
     - shadow_until_clean_pins: 3.
2. providers.py:
   - ROUTINGS. Router(routing=...): under heimdall_first, each Heimdall back-end's vendor becomes "heimdall/<family>"
     (gateway() keeps "heimdall"), so every existing vendor rule separates the families.
   - chain(role): the Plan B chain while the health state says plan_b, else the overrides, else the routing's list,
     else the role's chain.
   - role_deadline: 120 s on Heimdall for the verdict roles, minus today_unbounded under today.
   - call_parsed(router, ...): an answer out of contract is rejected and its model skipped; the chain spent is
     ProviderError; a skipped model answering again is ProviderError (never a loop).
   - The shadow: SHADOW_ROLES, _shadow_ask (a thread; role "shadow86:<role>" with its own recordings), shadow_wait.
   - Plan B: _note (each Heimdall verdict or writer call's outcome to heimdall_health); mode(); start_probe / probe_once
     (a family marked down is probed; its mark is lifted only if it answers); probes are never recorded or served from
     a recording.
   - GeminiBackend.
   - LocalJudgeBackend: the integrator's contract, a request file in this worktree, its answer from the integrator's
     results directory, up to 40 min; an error or no answer is no verdict. Its deadline floor overrides 120 s. Its first
     use is announced on STATE line 1.
   - The tripwire checks isinstance(HeimdallBackend), not the vendor string.
3. heimdall_health.py (new; shared with pp-ingest's watcher):
   - a state file under an flock;
   - note(answered): the 15-minute rule; a drill is recorded, never counted; an answer is written at most once per
     30 s per process while all is well, a failure always;
   - mode() applies the rule on the clock;
   - probe_due every 2 min while failing or in plan_b;
   - probe_result: 3 answers in a row in plan_b switch back;
   - every switch goes to the state, the evidence file and STATE line 1 (prepended, one physical line);
   - announce();
   - an unreadable state raises HealthUnreadable (never guessed).
4. proof_ly.py: chains(routing); plan_b_chains() (OpenAI / Anthropic kept: tried, never assumed).
   proof_ledger.py: --routing; the Router gets health, plan_b_chains and state_md; the shadow while the routing is
   heimdall_first and the clean streak is under 3; shadow_wait and the shadow report at the end; res["routing"] and
   res["mode_at_end"].
5. Tests:
   - test_providers: today unchanged; Grok last; the two-family rule inside Heimdall; 120 s on Heimdall only;
     call_parsed; the writer's gateway; the real config's deadline split; the shadow (asked, never deciding, failures
     recorded, recorded verdicts shadowed).
   - test_heimdall_health: 15 minutes; one answer stops the clock; probes; back after 3; switches on record; drills;
     the heartbeat; unreadable state; the router's Plan B chain; the probe and the down marks; the local judge.
   - test_ledger_build: the real config with xAI down and deepseek writing; every verdict role answers inside Heimdall
     off the writer; step A's two verdicts from two Heimdall families.

Design choices to check (say if you think any is wrong):
- The family-as-maker re-keying happens only under heimdall_first; today's behaviour is unchanged.
- A refused request (HTTP 400) counts as "not answered" for the health clock; any other family's answer stops it.
- In Plan B the writer is Grok first; with one outside family, verdicts other than step A have no second family and
  fail closed (the ruling names the local judge for step A only).
- The probe lifts a down mark only when the family answers.

Check, against the diff:
- that today's routing is unchanged except the 20:33 chains and their 120 s;
- that no verdict can come from the writer's family under either routing;
- that xAI answering nothing still completes every verdict under heimdall_first;
- the health state's concurrency and fail-closed behaviour;
- that a shadow can never decide or block;
- the Plan B switch and its return;
- spend: shadows, probes and Plan B calls all on the same ledger.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".

ADDENDUM (00:4x ET Nov 14): this change is now rebased onto the branch's newer HEAD 07321410. That HEAD adds the
SPOTLIGHT pin kind (rulings 90-92: pipeline/spotlight.py, package_pin's spotlight contract) and RULING 93 (DEC-12d per
clip: visual_pin's burned-in text question). Both were audited separately (2322, 0003). The merge points, to check:
- package.first_bounds(router): one helper for step A's FIRST screen. Under heimdall_first it is 2 clips and 120 s a
  call; under today, {}. The medley build and spotlight.build both call prescreen(..., kind="step_a_first",
  **first_bounds(router)).
- proof_ledger.py keeps both module constants (SPOTLIGHTS for ruling 90; STATE_MD for ruling 87). The spotlight runs
  on the same Router after the medley search, so its calls are shadowed (ruling 86) and noted for Plan B (ruling 87)
  like the medley's.
- shadow86.pin_texts covers a sealed spotlight pin (res["spotlight_pin"] with res["spotlight"]["package"]) as well as
  the medley pin, so ruling 86's "first pin sealed under Heimdall-first" holds whatever the pin's kind.
- The spotlight's value verdict (ruling 91) stays ONE call with no move-on ("one write, one verdict; anything short of
  a clear yes means no line"); its layout verdict (ruling 92) is one vision call, and failing it means not measured.

ADDENDUM 2 (01:1x ET Nov 14):
- The change is now rebased onto HEAD 2f081cba, which adds RULINGS 94 and 95 (audited separately, 0041):
  - stand_alone's hook opener rule (first/second-person pronouns free, third-person ones need the scorer);
  - package._can_open's re-check with the verdict and its spotlight-only deferral;
  - hook trim variants;
  - spotlight.next_attempt.
  The merge was mechanical (git merge-file, no conflict). The one hand-applied line is spotlight.build's step-A call:
  kind="step_a_first" with package.first_bounds(router), as the medley's.
- THE REPLAY IS COMPLETE (884 rows; tests/package/proof/replay85/TABLE.md). Ruling 88 (b) was conditional on the
  full table:
  - it holds for the HOOK rating: qwen 100 % of 15 units, glm 100 % of 11, deepseek 96 %. model_providers.json's
    heimdall_first "coherence_verdict:hook" is now qwen -> glm -> deepseek -> Grok (Grok was first);
  - it does not hold for STEP C: glm 97 %, deepseek 96 %, and qwen's 98 % is barred by (e). Step C stays Grok first.
  routing.ruling_88's note records both.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
