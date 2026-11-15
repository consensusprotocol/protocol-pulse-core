# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2243
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 158 s finish=stop usage in 10784 / out 4814 usd_reported=0.000931 usd~0.105 (upper-bound price)

# Code Audit: pp-selectid — Batch 3 Spend-Guard Fixes

**Scope reviewed:** C1_STEP.diff (providers.py `_reserve` wait, proof_ly.py `meter()` wrapper, two new test files) against the governing laws (M12 fail-closed, LAW 20/M2, L-j) and the stated defect narrative.

---

## Findings

### [P1] F1 — `_reserve` wait loop: `waited` flag set outside the lock, and the "spend alone" early-exit can misreport, but more importantly the loop's exit condition ordering can raise SpendLimit *before* one final successful poll

`providers.py`, new `_reserve`:

```python
while True:
    with self._lock():
        ...
        if spent + held + upper <= self.limit_usd:  # reserve & return
        if spent + upper > self.limit_usd or time.time() >= t_end:
            raise SpendLimit(...)
    waited = True
    time.sleep(...)
```

Two issues:

1. **`waited = True` executes after the `with` block, before the sleep — but if the loop body raises, `waited` was already set on the *previous* iteration.** That part is fine. The real issue: on the *first* iteration, if the call doesn't fit, the code checks `time.time() >= t_end`. With `reserve_wait_s = 0.0` (or a very small value), `t_end = now + 0.0`, so `time.time() >= t_end` is true immediately and the call is refused without ever waiting — correct fail-closed, but the error message then lacks the "(still, after waiting...)" suffix even though `waited` is False, which is consistent. However, when `reserve_wait_s > 0` and the deadline expires, the final check happens *inside* the lock *before* one last reservation attempt — no, wait, the fit-check runs first, so the last-iteration fit is still honored. **Downgrade: the ordering is actually correct.** The remaining defect: **`waited` is set to True even when the loop exits via the raise on the *first* pass** — no, it isn't; the raise happens before `waited = True`. After careful trace: the flag logic is correct. **Residual [P2]:** the error message when `waited` is true reports `spent + reserved + upper > limit` using the *last-read* `held`, which may have changed; cosmetic.

2. **Poll interval vs. deadline: `time.sleep(max(0.01, reserve_poll_s))` can oversleep past `t_end`** — the next iteration's `time.time() >= t_end` catches it, so the wait can exceed `reserve_wait_s` by up to one poll interval (600 s default → up to +1.0 s). [P3] (message says "after waiting 600 s" while actual wait is 600–601 s; harmless).

**Verdict: no P0/P1 in the loop logic itself; the wait is fail-closed (M12 ✓).** But see F2 for the real P1.

### [P1] F2 — Starvation: the waiting call re-reads the ledger but never re-checks *its own* reservation against *newly arrived* competitors; under sustained contention a call can wait the full 600 s and be refused despite the limit having room "in principle" — and, critically, **the wait runs *before* the call's deadline (`_within`) starts, so the caller's time budget is silently consumed**

This is the question the author asked (CHECK 3) and it is a real defect. Trace: `Router.call` → `_reserve` (new: can block up to 600 s) → *then* the deadline/`_within` machinery starts. Callers with their own time budgets:

- **prescreen (step A, ruling 101's wait estimate):** computes a wait estimate from... the *pre-wait* state. A worker that would have been refused at once (old behavior, ~0 s) now blocks up to 600 s; ruling 101's estimate and any prescreen timeout computed *before* `Router.call` no longer bound the wall-clock. If prescreen's ThreadPoolExecutor or the ruling-102 "retried next build" logic has its own deadline, a 600 s `_reserve` wait can blow it, producing holds that *look* like gate failures rather than SpendLimit.
- **the shadow's background asks:** background threads now block up to 600 s inside `_reserve`; if the shadow's teardown joins its workers with a shorter timeout, the join times out and the ask is lost — previously it was refused *fast* and the shadow could react.

**Fix:** either (a) start the caller's deadline clock *before* `_reserve` (pass a deadline into `_reserve` and cap `t_end` by it), or (b) document + bound `reserve_wait_s` per call-site. As written, the 600 s default is a silent 10-minute hang for every caller that assumed SpendLimit returns at once. **[P1] — must fix before merge** (or, at minimum, the author must demonstrate no caller has a budget shorter than 600 s; the diff neither demonstrates nor bounds this).

### [P3] F3 — `test_reserve_wait.py` timing assumptions

- `test_six_workers...`: `time.sleep(0.4)` then asserts `track["now"] == 4` exactly. On a loaded 2×4090 box (or CI), thread startup jitter can leave only 3 workers reserved at the 0.4 s mark → flaky. Prefer: poll until `track["now"] == 4` with a deadline, or assert `track["now"] >= 3` / `<= 4` with a later re-check. Also `assertEqual(results, {})` at 0.4 s — if the box is slow, a worker co

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 40 s finish=stop usage in 11938 / out 2836 usd_reported=0.002577 usd~0.078 (upper-bound price)

I will analyze the provided code changes against the governing laws and the specific questions raised in the audit request.

### Analysis of `pipeline/providers.py` (Defect 2 Fix)

**1. Deadlock and Starvation Analysis**
The new `_reserve` logic introduces a wait loop.
*   **Locking:** The code acquires `self._lock()` (an `fcntl` flock on a file) to read the ledger and check limits. If the limit is not met, it releases the lock (exits the `with` block) and then calls `time.sleep()`.
*   **Deadlock:** Since the lock is released during the sleep, other threads can acquire the lock, read the ledger, and potentially reserve or settle. There is no circular dependency where a waiting thread holds a resource needed by a running thread. The running threads hold the lock only briefly to update the ledger.
*   **Starvation:** The wait is bounded by `reserve_wait_s` (600s). If a call cannot fit within this time, it raises `SpendLimit`. This prevents indefinite starvation. However, if the system is under heavy load where calls take longer than 600s to settle, new calls will fail. This is a "fail closed" behavior consistent with LAW 20/M12.
*   **Conclusion:** No deadlock. Starvation is bounded and results in a hard stop (SpendLimit), which is acceptable for a spend guard.

**2. Limit Integrity (Spent + Reserved > Limit)**
*   **Check:** The condition `if spent + held + upper <= self.limit_usd` is evaluated *inside* the lock.
*   **Race Condition:** Two threads could theoretically pass the check simultaneously if the lock wasn't held. However, `self._lock()` is a file lock (`fcntl.flock`). On Linux, `flock` is exclusive. Only one process/thread can hold the lock at a time.
*   **Atomicity:** The read of `spent` and `held`, the check, and the write of the new reservation (`d["reserved"][key] = ...`) and save (`self._save(d)`) all happen within the `with self._lock():` block.
*   **Conclusion:** The limit is never passed. The reservation is only saved if the check passes while holding the exclusive lock.

**3. Caller Time Budgets**
*   **Context:** The prompt notes that `_reserve` is called before the call's deadline (`_within`) starts.
*   **Impact:** If a caller has a strict time budget (e.g., 5 seconds) for the entire operation, and `_reserve` waits for 600 seconds, the caller will time out.
*   **Code Review:** The `Router.call` method likely wraps the backend call in a deadline context. If `_reserve` blocks for 600s, the thread is occupied. If the caller uses `concurrent.futures` with a timeout, the future will time out, but the thread running `_reserve` will continue to wait until `reserve_wait_s` expires or the limit is met. This could lead to thread pool exhaustion if many callers time out while the underlying threads are still waiting in `_reserve`.
*   **Severity:** This is a potential resource leak/thread exhaustion issue under high contention. However, the default `reserve_wait_s` is 600s. If the pipeline steps (like Step A) have timeouts shorter than 600s, this is a P1 defect. The prompt mentions "prescreen, ruling 101's wait estimate". If those estimates are < 600s, this is a problem.
*   **Mitigation:** The code does not check the caller's remaining time budget before waiting. It waits blindly up to `reserve_wait_s`.
*   **Finding:** [P1] The `_reserve` method does not respect the caller's remaining time budget. If a caller has a 10s timeout and `_reserve` waits 600s, the caller will time out, but the thread remains blocked in `_reserve` until the wait expires or the limit is met. This can exhaust the thread pool.

**4. "Best" Calculation for Abandoned Calls**
*   **Code:** `tot["best"] += float(rep) if P._num(rep) else float((usd if booked is None else booked) or 0.0)`
*   **Logic:**
    *   If `rep` (reported USD) is a number, use it.
    *   Else, if `booked` (unreported keyword) is not None, use `booked`.
    *   Else, use `usd` (estimate).
*   **Context:** For an abandoned call, `Router._settle` is called with `unreported=booked` (the list price estimate). `usage` is `{"in": 0, "out": 0}`, so `rep` is likely `None` or 0.
    *   If `rep` is `None`, `P._num(None)` is False.
    *   `booked` is the list price.
    *   So `tot["best"]` adds the list price.
*   **Correctness:** The prompt states: "An abandoned call counts in 'best' at that booking, as the cap counts it". The cap (`_basis_total`) uses `usd_unreported_estimate` for abandoned calls. The meter now aligns with this.
*   **Conclusion:** Correct.

**5. Other Wrappers**
*   **Search:** The diff only modifies `proof_ly.py`'s `meter` function. Are there other wrappers?
*   **Code:** `router._settle = _settle`. This is the only wrapper shown.
*   **Conclusion:** No other wrappers are modified or shown to be broken.

### Analysis of `tests/package/test_meter.py`

*   **Test 1:** `test_a_missed_deadline_through_the_meter_fail

## CLAUDE'S CYCLE 1 CONSENSUS
# C1 consensus, audit 20261114_2243 (written by the builder; reviewers qwen3.8-27b and glm-5.3-flash, Heimdall;
# Grok not asked: both raised one P1, the same one)

## P1, both reviewers: the wait runs before the call's deadline (_within) starts
A caller that relied on SpendLimit coming back at once (a thread pool with its own timeout, a render) could now stall
for up to 600 s; glm: "either cap the wait by the call's deadline, or show no caller has a budget shorter than 600 s".
ACCEPTED, FIXED: the wait is OPT-IN. Router(reserve_wait_s=0.0) by default: refused at once, exactly as before, for
every caller (the integrator's render among them). Only the ledger build's router opts in
(tests/package/proof_ledger.py build_router: reserve_wait_s=proof_ly.RESERVE_WAIT_S = 600 s). It is a batch job:
step A's workers run under ThreadPoolExecutor.map with no timeout (base pipeline/package.py:588-589), the build's
shadow wait is 900 s (Router.shadow_wait), and no caller in it has a time budget of its own.
Tests: a default router refuses at once with a call in flight (tests/providers/test_reserve_wait.py); the ledger
build's router, built by build_router with every state file in a temporary folder, waits and answers
(tests/package/test_ledger_router.py). Mutations: "the ledger build does not opt in" and "every router waits by
default" are both killed.

## Tagged [P1] by qwen, answered by itself: no defect
qwen's items 5 (the meter's "best") and 7 (the spend-alone refusal) end "This seems correct" / "This is correct"; its
closing count is P1_OR_WORSE: 1 (the item above).

## P2 / P3, by decision
- glm F3 (P3), test timing: FIXED. Each sleep-then-assert is a poll with a deadline (until(...)), then the check.
- glm F4 (P2), the meter does not follow a late answer's replacement (Router._replace_booking): NOT CHANGED. It was
  never followed (before ruling 107 Q1 too); the docstring says so. The cap is the router's ledger, which does follow
  it; the meter feeds the per-package budget only.
- glm F5 (P2), other wrappers with an old signature: CHECKED repo-wide (grep of assignments to Router methods): the
  only fixed-signature wrapper was this one; reply_meter (proof_ly.py) and every test wrapper pass *a, **k.
- glm F15 (P2), a reservation leaked by a raising bare _settle(key) now blocks a waiter for up to 600 s, not 0:
  NOTED. Opt-in only, bounded, and _ledger() drops it when its process ends.
- glm F7 (P3), ledger traffic: _ledger() only reads; one flock and one read per poll per waiting call. No change.
- glm F17 (P3), the free back-end's fast path: unchanged code, covered by test_providers'
  test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit (a free back-end at a $1 limit).
- The other P3s (messages, constants' comments, the cross-test import): no change.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2243/C2_STEP.diff (429 lines)
```
   1 | diff --git a/pipeline/providers.py b/pipeline/providers.py
   2 | index 44468d7..78ff10f 100644
   3 | --- a/pipeline/providers.py
   4 | +++ b/pipeline/providers.py
   5 | @@ -69,6 +69,8 @@ class ReplayMiss(Exception):
   6 |  IMAGE_TOKENS_UPPER = 6000            # ruling 70: one image's input tokens, as the spend guard's upper bound
   7 |  RATE_MIN_REPORTED = 3                # RULING 107 Q1 (orchestrator 20:40 ET Nov 14): an abandoned call is booked at
   8 |                                       # the model's own reported rate once it has this many reported calls
   9 | +RESERVE_POLL_S = 1.0                 # BATCH 3 (Nov 14): how often a call waiting for room under the limit re-reads
  10 | +                                     # the ledger (Router reserve_wait_s, Router._reserve)
  11 |  
  12 |  
  13 |  def is_vision(prompt):
  14 | @@ -722,7 +724,7 @@ class Router:
  15 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
  16 |                   local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
  17 |                   routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
  18 | -                 breakers=None, deadlines=None):
  19 | +                 breakers=None, deadlines=None, reserve_wait_s=0.0):
  20 |          with open(config) as f:
  21 |              self.config = json.load(f)
  22 |          rt = self.config.get("routing") or {}
  23 | @@ -734,6 +736,8 @@ class Router:
  24 |          if limit_basis not in ("estimate", "reported"):
  25 |              raise ValueError(f"limit_basis must be 'estimate' or 'reported', not {limit_basis!r}")
  26 |          self.limit_basis = limit_basis            # what limit_usd counts: _basis_total
  27 | +        self.reserve_wait_s = float(reserve_wait_s)   # _reserve: 0 (the default) refuses at once, as every caller had
  28 | +        self.reserve_poll_s = RESERVE_POLL_S          # it; a batch build that may wait for calls in flight opts in
  29 |          import threading
  30 |          self.deadline_log, self.slow_log_s = deadline_log, slow_log_s     # order 08:06 item 55: the evidence file
  31 |          self._log_lock = threading.Lock()
  32 | @@ -888,20 +892,37 @@ class Router:
  33 |      def _reserve(self, b, upper):
  34 |          """Reserve a paid call's upper bound -> a reservation key (None for a free back-end or no ledger); raises
  35 |          SpendLimit when spent (on the limit basis) + reserved + this call's upper bound would pass the limit. The
  36 | -        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late."""
  37 | +        reservations stay price-table upper bounds whatever the basis: the guard can only stop early, never late.
  38 | +        With reserve_wait_s > 0 (a batch build's opt-in; the default 0 keeps the refusal at once that every other
  39 | +        caller, the render's among them, relies on): when spent + this call's upper bound fits and only the reservations
  40 | +        of calls IN FLIGHT stand in the way, the call waits for them to settle (each ends in an answer, an error or an
  41 | +        abandonment, and releases its reservation), sleeping outside the ledger lock and re-reading the ledger every
  42 | +        reserve_poll_s, and reserves once it fits; still kept out after reserve_wait_s, it is refused (fail closed).
  43 | +        Spend alone over the limit is refused at once. The wait runs before the call's own deadline starts: only a
  44 | +        caller with no time budget of its own should opt in. Batch 3's builds 1 and 2 (Nov 14) held
  45 | +        65 moments at step A, medley and spotlight (90 holds in all), without this wait: six step-A workers, each
  46 | +        reserving about $0.85, under a $4.50 limit with $0.27 spent; four fit, and the other workers were refused batch
  47 | +        after batch while those four ran."""
  48 |          if not self.spend_path or b.free():
  49 |              return None
  50 | -        with self._lock():
  51 | -            d = self._ledger()
  52 | -            held = sum(float(x) for x in d["reserved"].values())
  53 | -            spent = self._basis_total(d)
  54 | -            if spent + held + upper > self.limit_usd:
  55 | -                raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's upper "
  56 | -                                 f"bound {upper:.2f} > the limit {self.limit_usd} USD")
  57 | -            key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
  58 | -            d["reserved"][key] = round(upper, 6)
  59 | -            self._save(d)
  60 | -        return key
  61 | +        t_end, waited = time.time() + max(0.0, float(self.reserve_wait_s)), False
  62 | +        while True:
  63 | +            with self._lock():
  64 | +                d = self._ledger()
  65 | +                held = sum(float(x) for x in d["reserved"].values())
  66 | +                spent = self._basis_total(d)
  67 | +                if spent + held + upper <= self.limit_usd:
  68 | +                    key = f"{os.getpid()}:{uuid.uuid4().hex[:10]}"
  69 | +                    d["reserved"][key] = round(upper, 6)
  70 | +                    self._save(d)
  71 | +                    return key
  72 | +                if spent + upper > self.limit_usd or time.time() >= t_end:
  73 | +                    raise SpendLimit(f"spend ({self.limit_basis}) {spent:.2f} USD + reserved {held:.2f} + this call's "
  74 | +                                     f"upper bound {upper:.2f} > the limit {self.limit_usd} USD" +
  75 | +                                     (f" (still, after waiting {self.reserve_wait_s:g} s for the calls in flight)"
  76 | +                                      if waited else ""))
  77 | +            waited = True
  78 | +            time.sleep(max(0.01, float(self.reserve_poll_s)))
  79 |  
  80 |      def reported_rate(self, name):
  81 |          """RULING 107 Q1 (orchestrator 20:40 ET Nov 14): the model's own recorded vendor cost per PROMPT token: its
  82 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
  83 | index befaff1..0e36ebd 100644
  84 | --- a/tests/package/proof_ledger.py
  85 | +++ b/tests/package/proof_ledger.py
  86 | @@ -209,7 +209,8 @@ def build_router(routing, shadow, shadow_log):
  87 |                      routing=routing, shadow=shadow, shadow_log=shadow_log,
  88 |                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
  89 |                      breakers=CB.STATE,                                                         # ruling 99
  90 | -                    deadlines=DT.load(DT.STATE, PL.REPLIES))                                   # ruling 100
  91 | +                    deadlines=DT.load(DT.STATE, PL.REPLIES),                                   # ruling 100
  92 | +                    reserve_wait_s=PL.RESERVE_WAIT_S)          # batch 3: a call that fits waits for calls in flight
  93 |  
  94 |  
  95 |  def applied(router):
  96 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
  97 | index 5dcf21f..3fca2fe 100644
  98 | --- a/tests/package/proof_ly.py
  99 | +++ b/tests/package/proof_ly.py
 100 | @@ -54,6 +54,10 @@ LY_LIMIT_BASIS = "reported"        # mining and checks $1.00), VENDOR-REPORTED;
 101 |  LY_STOP_USD = 4.00                 # rate (ruling 107 Q1). No build starts at or over $4.00 (a build runs $0.15-0.50, so
 102 |                                     # none ends over $4.50: each paid call still RESERVES its upper bound while in
 103 |                                     # flight, and none passes the limit); STATE line 1 says so in capitals.
 104 | +RESERVE_WAIT_S = 600.0             # BATCH 3 (Nov 14): the ledger build's router waits up to this long for calls in
 105 | +                                   # flight to settle before refusing a call that fits under the limit by itself
 106 | +                                   # (Router reserve_wait_s): step A's six workers reserve about $0.85 each, so under
 107 | +                                   # $4.50 four run and two wait, where builds 1 and 2 held them (SpendLimit)
 108 |  TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
 109 |  DEADLINE_LOG = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_HEIMDALL_DEADLINES.jsonl")   # item 55
 110 |  RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
 111 | @@ -108,17 +112,22 @@ def ledger():
 112 |  def meter(router):
 113 |      """THIS process's own spend, from every call the router accounts (Router._settle). The shared ledger's total moves
 114 |      with the other workers too, so a per-package budget read from it would charge one universe for another's calls.
 115 | -    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}."""
 116 | +    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}.
 117 | +    Every keyword the router's own _settle takes is passed on unchanged: the meter observes, it never stands between
 118 | +    a call and its booking. Batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) lost three abandoned calls' bookings
 119 | +    and held five moments (six holds) because this wrapper refused ruling 107 Q1's `unreported` (a TypeError in
 120 | +    place of the failover). An abandoned call counts in "best" at that booking, as the cap counts it; a late answer that replaces
 121 | +    the booking (Router._replace_booking) is not followed here."""
 122 |      import threading
 123 |      tot, lock, settle = {"est": 0.0, "best": 0.0}, threading.Lock(), router._settle
 124 |  
 125 | -    def _settle(key, backend=None, usage=None, usd=0.0, role=""):
 126 | -        settle(key, backend, usage, usd, role)
 127 | +    def _settle(key, backend=None, usage=None, usd=0.0, role="", **kw):
 128 | +        settle(key, backend, usage, usd, role, **kw)
 129 |          if backend is not None:
 130 | -            rep = (usage or {}).get("usd_reported")
 131 | +            rep, booked = (usage or {}).get("usd_reported"), kw.get("unreported")
 132 |              with lock:
 133 |                  tot["est"] += float(usd or 0.0)
 134 | -                tot["best"] += float(rep) if P._num(rep) else float(usd or 0.0)
 135 | +                tot["best"] += float(rep) if P._num(rep) else float((usd if booked is None else booked) or 0.0)
 136 |      router._settle = _settle
 137 |      return tot
 138 |  
 139 | diff --git a/tests/package/test_ledger_router.py b/tests/package/test_ledger_router.py
 140 | new file mode 100644
 141 | index 0000000..5774da9
 142 | --- /dev/null
 143 | +++ b/tests/package/test_ledger_router.py
 144 | @@ -0,0 +1,109 @@
 145 | +#!/usr/bin/env python3
 146 | +"""The ledger build's router, as batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) found it wanting:
 147 | +- proof_ly.meter observes the router's accounting and never stands between a call and its booking. Its wrapper refused
 148 | +  ruling 107 Q1's `unreported` keyword, so a call abandoned at its deadline raised TypeError in place of failing over
 149 | +  to the next leg; its booking never reached the ledger, its late answer was never accounted, its moments were held.
 150 | +- proof_ledger.build_router waits for calls in flight (Router reserve_wait_s): step A's six workers had been refused
 151 | +  whenever four reservations filled the $4.50 limit with $0.27 spent.
 152 | +Offline: the real Router over fake legs, every state file of the build in a temporary folder."""
 153 | +import contextlib
 154 | +import json
 155 | +import os
 156 | +import sys
 157 | +import tempfile
 158 | +import threading
 159 | +import time
 160 | +import unittest
 161 | +from unittest import mock
 162 | +
 163 | +HERE = os.path.dirname(os.path.abspath(__file__))
 164 | +REPO = os.path.dirname(os.path.dirname(HERE))
 165 | +for _p in ("pipeline", "tests/package", "tests/providers"):
 166 | +    sys.path.insert(0, os.path.join(REPO, _p))
 167 | +import circuit_breaker as CB  # noqa: E402
 168 | +import deadline_table as DT  # noqa: E402
 169 | +import heimdall_health as HH  # noqa: E402
 170 | +import proof_ledger as PLG  # noqa: E402
 171 | +import proof_ly as PL  # noqa: E402
 172 | +from test_providers import Fake, SlowFail, router, wait_for  # noqa: E402
 173 | +from test_reserve_wait import U, gate, run, seed, until  # noqa: E402
 174 | +from test_ruling_107 import LIST, TOKENS, seed as seed107  # noqa: E402
 175 | +
 176 | +QWEN_LIST = 1000 * 10 / 1e6 + 100 * 100 / 1e6          # Fake's list price for qwen's 1,000 in / 100 out
 177 | +
 178 | +
 179 | +def metered_miss(d, **seeded):
 180 | +    """One call through a METERED router: deepseek passes its 0.2 s deadline (and fails later), qwen answers with the
 181 | +    vendor's own figure. -> (reply, the meter, the ledger, the deadline log once the abandoned thread has ended)."""
 182 | +    spend, log = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
 183 | +    seed107(spend, **seeded)
 184 | +    slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.4, family="deepseek")
 185 | +    qwen = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
 186 | +                usage={"in": 1000, "out": 100, "usd_reported": 0.002})
 187 | +    r = router(d, [slow, qwen], {"check": ["heimdall:deepseek", "heimdall:qwen"]}, spend_path=spend,
 188 | +               limit_usd=50.0, limit_basis="reported", deadline_log=log)
 189 | +    own = PL.meter(r)
 190 | +    rep = r.call("check", "p", 100, 7, deadline_s=0.2)
 191 | +    lines = wait_for(log, "late_error")                # ruling 83 (a)'s late path ran: the abandonment was booked
 192 | +    return rep, own, json.load(open(spend)), lines
 193 | +
 194 | +
 195 | +class TestTheMeterNeverStandsBetweenACallAndItsBooking(unittest.TestCase):
 196 | +
 197 | +    def test_a_missed_deadline_through_the_meter_fails_over_and_is_booked(self):
 198 | +        with tempfile.TemporaryDirectory() as d:
 199 | +            rep, own, led, log = metered_miss(d)
 200 | +            self.assertEqual((rep.text, rep.backend), ('{"ok": 2}', "heimdall:qwen"))     # failed over: no TypeError
 201 | +            self.assertIn("abandoned at the deadline", rep.tried[0][1])
 202 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)          # the booking is in the ledger
 203 | +            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)
 204 | +            self.assertEqual([x["kind"] for x in log if x["kind"] in ("missed_deadline", "late_error")],
 205 | +                             ["missed_deadline", "late_error"])
 206 | +            self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                  # this process's two calls
 207 | +
 208 | +    def test_the_meter_counts_an_abandoned_call_at_the_booking_the_cap_counts(self):
 209 | +        with tempfile.TemporaryDirectory() as d:        # three reported calls: deepseek's booking is at its own rate
 210 | +            rep, own, led, log = metered_miss(d, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
 211 | +                                              in_reported=3000)
 212 | +            booked = 0.003 / 3000 * TOKENS
 213 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=9)
 214 | +            self.assertAlmostEqual(own["best"], booked + 0.002, places=9)                    # as the cap reads it
 215 | +            self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                   # est stays list price
 216 | +
 217 | +
 218 | +class TestTheLedgerBuildsRouterWaitsForCallsInFlight(unittest.TestCase):
 219 | +
 220 | +    def test_a_call_kept_out_only_by_a_call_in_flight_waits_and_answers(self):
 221 | +        with tempfile.TemporaryDirectory() as d:          # every file the build's router reads or writes is d's
 222 | +            led = os.path.join(d, "SPEND.json")
 223 | +            seed(led)
 224 | +            with contextlib.ExitStack() as st:
 225 | +                for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
 226 | +                                       (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")), (PL, "LY_LIMIT_USD", 1.5 * U),
 227 | +                                       (HH, "STATE", os.path.join(d, "HEALTH.json")),
 228 | +                                       (CB, "STATE", os.path.join(d, "BREAKERS.json")),
 229 | +                                       (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
 230 | +                                       (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
 231 | +                    st.enter_context(mock.patch.object(mod, name, val))
 232 | +                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 233 | +            g, release, track = gate()
 234 | +            r.backends, r.chains["check"], r.reserve_poll_s = {"openai:g": g}, ["openai:g"], 0.02
 235 | +            results = {}
 236 | +            first = threading.Thread(target=run, args=(r, results, 0))
 237 | +            first.start()
 238 | +            until(lambda: track["now"] == 1)
 239 | +            second = threading.Thread(target=run, args=(r, results, 1))
 240 | +            second.start()
 241 | +            time.sleep(0.3)
 242 | +            self.assertEqual((track["now"], results), (1, {}))   # one in flight, one WAITING: not refused (a default
 243 | +                                                                # router refuses it at once)
 244 | +            release.set()
 245 | +            first.join(10)
 246 | +            second.join(10)
 247 | +            self.assertEqual([results[i][0] for i in (0, 1)], ["answer", "answer"])
 248 | +            self.assertEqual((g.calls, track["max"]), (2, 1))   # never two in flight past the limit
 249 | +            self.assertEqual(json.load(open(led))["reserved"], {})
 250 | +
 251 | +
 252 | +if __name__ == "__main__":
 253 | +    unittest.main()
 254 | diff --git a/tests/providers/test_reserve_wait.py b/tests/providers/test_reserve_wait.py
 255 | new file mode 100644
 256 | index 0000000..50a18d2
 257 | --- /dev/null
 258 | +++ b/tests/providers/test_reserve_wait.py
 259 | @@ -0,0 +1,169 @@
 260 | +#!/usr/bin/env python3
 261 | +"""The spend guard and calls IN FLIGHT. Batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) held 65 moments at step A
 262 | +(90 holds, medley and spotlight): six workers in parallel, each reserving its price-table upper bound (about $0.85)
 263 | +under a $4.50 limit with $0.27 spent, so four fit and the other two were refused batch after batch while those four
 264 | +ran. A router that opts in (reserve_wait_s > 0, the ledger build's) waits for calls in flight to settle; it never passes
 265 | +the limit and refuses when the wait ends. A default router still refuses at once (every other caller, the render's
 266 | +among them, relies on that). Offline: the real Router over fake back-ends, real threads, a temporary ledger."""
 267 | +import json
 268 | +import os
 269 | +import sys
 270 | +import tempfile
 271 | +import threading
 272 | +import time
 273 | +import unittest
 274 | +
 275 | +HERE = os.path.dirname(os.path.abspath(__file__))
 276 | +REPO = os.path.dirname(os.path.dirname(HERE))
 277 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 278 | +sys.path.insert(0, HERE)
 279 | +import providers as P  # noqa: E402
 280 | +from test_providers import Fake, router  # noqa: E402
 281 | +
 282 | +U = (1 + 200) * 10 / 1e6 + 1000 * 100 / 1e6     # Fake's upper bound for prompt "p" and max_tokens 1000: $0.10201
 283 | +
 284 | +
 285 | +class Gate(Fake):
 286 | +    """A back-end whose call stays in flight (its reservation held) until `release` is set; `track` counts how many of
 287 | +    its calls are in flight at once."""
 288 | +
 289 | +    def __init__(self, name, release, track):
 290 | +        super().__init__(name, "openai", answer='{"ok": 1}', usage={"in": 10, "out": 10, "usd_reported": 0.0001})
 291 | +        self.release, self.track = release, track
 292 | +
 293 | +    def complete(self, prompt, max_tokens, seed, system=None):
 294 | +        with self.track["lock"]:
 295 | +            self.track["now"] += 1
 296 | +            self.track["max"] = max(self.track["max"], self.track["now"])
 297 | +        try:
 298 | +            if not self.release.wait(10):
 299 | +                raise P.Unavailable("the test never released this call")
 300 | +            return super().complete(prompt, max_tokens, seed, system)
 301 | +        finally:
 302 | +            with self.track["lock"]:
 303 | +                self.track["now"] -= 1
 304 | +
 305 | +
 306 | +def gate():
 307 | +    release, track = threading.Event(), {"lock": threading.Lock(), "now": 0, "max": 0}
 308 | +    return Gate("openai:g", release, track), release, track
 309 | +
 310 | +
 311 | +def seed(led, spent=0.0):
 312 | +    json.dump({"usd_estimate": spent, "calls": 1 if spent else 0, "by_backend": {}, "by_role": {}, "reserved": {},
 313 | +               "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
 314 | +
 315 | +
 316 | +def guarded(d, limit, spent=0.0, wait_s=None):
 317 | +    """A router on a ledger with `spent` reported dollars, the guard at `limit`, one Gate back-end; wait_s None: the
 318 | +    Router's default (no wait)."""
 319 | +    led = os.path.join(d, "SPEND.json")
 320 | +    seed(led, spent)
 321 | +    g, release, track = gate()
 322 | +    kw = {} if wait_s is None else {"reserve_wait_s": wait_s}
 323 | +    r = router(d, [g], {"check": ["openai:g"]}, spend_path=led, limit_usd=limit, limit_basis="reported", **kw)
 324 | +    r.reserve_poll_s = 0.02
 325 | +    return r, g, release, track, led
 326 | +
 327 | +
 328 | +def run(r, results, i, max_tokens=1000):
 329 | +    t0 = time.time()
 330 | +    try:
 331 | +        results[i] = ("answer", r.call("check", "p", max_tokens, i).text, time.time() - t0)
 332 | +    except P.SpendLimit as e:
 333 | +        results[i] = ("refused", str(e), time.time() - t0)
 334 | +
 335 | +
 336 | +def until(cond, timeout=5.0):
 337 | +    t0 = time.time()
 338 | +    while not cond():
 339 | +        if time.time() - t0 > timeout:
 340 | +            raise AssertionError(f"not reached in {timeout} s")
 341 | +        time.sleep(0.01)
 342 | +
 343 | +
 344 | +class TestARouterThatOptsInWaitsForCallsInFlight(unittest.TestCase):
 345 | +
 346 | +    def test_six_workers_with_room_for_four_all_answer_and_never_more_than_four_run(self):
 347 | +        with tempfile.TemporaryDirectory() as d:          # the batch-3 case: room for four upper bounds, six workers
 348 | +            r, g, release, track, led = guarded(d, limit=4.5 * U, wait_s=10.0)
 349 | +            results = {}
 350 | +            ts = [threading.Thread(target=run, args=(r, results, i)) for i in range(6)]
 351 | +            for t in ts:
 352 | +                t.start()
 353 | +            until(lambda: track["now"] == 4)
 354 | +            time.sleep(0.2)
 355 | +            self.assertEqual((track["now"], results), (4, {}))    # four in flight, two waiting: none refused
 356 | +            held = json.load(open(led))["reserved"]
 357 | +            self.assertEqual(len(held), 4)
 358 | +            self.assertLessEqual(sum(held.values()), 4.5 * U)
 359 | +            release.set()
 360 | +            for t in ts:
 361 | +                t.join(10)
 362 | +            self.assertEqual(sorted(v[0] for v in results.values()), ["answer"] * 6)
 363 | +            self.assertEqual((g.calls, track["max"]), (6, 4))
 364 | +            final = json.load(open(led))
 365 | +            self.assertEqual(final["reserved"], {})
 366 | +            self.assertAlmostEqual(final["usd_reported"], 6 * 0.0001, places=9)
 367 | +
 368 | +    def test_a_call_kept_out_by_spend_alone_is_refused_at_once_even_with_a_call_in_flight(self):
 369 | +        with tempfile.TemporaryDirectory() as d:          # 0.01 spent: the small call fits, the large one never will
 370 | +            r, g, release, track, led = guarded(d, limit=0.1, spent=0.01, wait_s=5.0)
 371 | +            results = {}
 372 | +            small = threading.Thread(target=run, args=(r, results, 0, 10))
 373 | +            small.start()
 374 | +            until(lambda: track["now"] == 1)
 375 | +            run(r, results, 1)                              # 0.01 + its upper bound $0.102 > $0.10
 376 | +            kind, why, secs = results[1]
 377 | +            self.assertEqual(kind, "refused")
 378 | +            self.assertLess(secs, 1.0)                      # no wait: no call settling could let it in
 379 | +            self.assertNotIn("after waiting", why)
 380 | +            release.set()
 381 | +            small.join(10)
 382 | +            self.assertEqual(results[0][0], "answer")
 383 | +
 384 | +    def test_a_call_still_kept_out_when_its_wait_ends_is_refused_and_the_limit_is_never_passed(self):
 385 | +        with tempfile.TemporaryDirectory() as d:          # room for one upper bound and a half
 386 | +            r, g, release, track, led = guarded(d, limit=1.5 * U, wait_s=0.4)
 387 | +            results = {}
 388 | +            first = threading.Thread(target=run, args=(r, results, 0))
 389 | +            first.start()
 390 | +            until(lambda: track["now"] == 1)
 391 | +            second = threading.Thread(target=run, args=(r, results, 1))
 392 | +            second.start()
 393 | +            time.sleep(0.15)
 394 | +            self.assertEqual(len(json.load(open(led))["reserved"]), 1)    # while it waits: never two reservations
 395 | +            second.join(3)
 396 | +            self.assertFalse(second.is_alive())
 397 | +            kind, why, secs = results[1]
 398 | +            self.assertEqual(kind, "refused")
 399 | +            self.assertIn("after waiting", why)
 400 | +            self.assertGreaterEqual(secs, 0.4)
 401 | +            self.assertEqual(g.calls, 0)                    # nothing answered yet: the first call is still in flight
 402 | +            release.set()
 403 | +            first.join(10)
 404 | +            self.assertEqual((results[0][0], g.calls, track["max"]), ("answer", 1, 1))
 405 | +            self.assertEqual(json.load(open(led))["reserved"], {})
 406 | +
 407 | +
 408 | +class TestADefaultRouterRefusesAtOnce(unittest.TestCase):
 409 | +
 410 | +    def test_with_no_opt_in_a_call_kept_out_by_a_call_in_flight_is_refused_at_once(self):
 411 | +        with tempfile.TemporaryDirectory() as d:          # the contract every caller had before batch 3
 412 | +            r, g, release, track, led = guarded(d, limit=1.5 * U)
 413 | +            results = {}
 414 | +            first = threading.Thread(target=run, args=(r, results, 0))
 415 | +            first.start()
 416 | +            until(lambda: track["now"] == 1)
 417 | +            run(r, results, 1)
 418 | +            kind, why, secs = results[1]
 419 | +            self.assertEqual(kind, "refused")
 420 | +            self.assertLess(secs, 0.5)
 421 | +            self.assertNotIn("after waiting", why)
 422 | +            release.set()
 423 | +            first.join(10)
 424 | +            self.assertEqual(results[0][0], "answer")
 425 | +
 426 | +
 427 | +if __name__ == "__main__":
 428 | +    unittest.main()
 429 | 
```

---

pp-selectid, two defects found in batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14), each fixed at its root. Both
builds held moments at step A's first screen ("no step-A verdict ... held for this build, retried next build", ruling
102), in the medley's step A and the spotlight's: 65 distinct moments (90 holds) by SpendLimit and 5 moments (6
holds) by a TypeError. No refusal, no wrong pass.

DEFECT 1 (tests/package/proof_ly.py meter()): the wrapper it puts over Router._settle had the old signature
(key, backend, usage, usd, role). Ruling 107 Q1 (commit e7f68e11) made the router's abandon() call
self._settle(key, b, {"in": 0, "out": 0}, listed, role, unreported=booked) (base pipeline/providers.py:1327). In a
metered build each call abandoned at its deadline raised TypeError inside on_abandon. _within (base providers.py:
347-378, UNCHANGED) lets that exception propagate in place of DeadlineExceeded and never sets box["abandoned"], so:
no failover to the next leg; the booking never reached the ledger; on_late never ran. Router.call's
`except BaseException: self._settle(key); raise` (base providers.py:1356-1358, UNCHANGED) released the reservation.
Three glm calls lost their bookings ($0.086 at list, from the deadline log).
FIX: the wrapper passes every keyword on (**kw) and counts an abandoned call in "best" at the booking
(kw["unreported"]), as the router's _settle counts it on the cap's basis (base providers.py:975-976).

DEFECT 2 (pipeline/providers.py Router._reserve): batch 3's build cap is LY_LIMIT_USD = 4.50 on the reported basis
(tests/package/proof_ly.py, UNCHANGED). Each paid call reserves its price-table upper bound (a Grok step-A call about
$0.85: prompt + 8 x max_tokens of reasoning output, XAIBackend.max_out base providers.py:445-446). Step A runs six
batches in parallel (package.PRESCREEN_WORKERS = 6, base pipeline/package.py:77, ThreadPoolExecutor at :588). With
$0.27 spent four calls fit; _reserve refused the fifth and sixth AT ONCE ("spend 0.27 + reserved 3.64 + this call's
upper bound 0.85 > the limit 4.5"), and those workers were refused batch after batch while the four ran.
FIX: when spent + this call's upper bound fits and only reservations of calls IN FLIGHT stand in the way, _reserve
waits (sleeping OUTSIDE the ledger lock, re-reading the ledger every reserve_poll_s) and reserves once it fits. Still
kept out after reserve_wait_s (600 s): SpendLimit, as before (fail closed). Spend alone over the limit: SpendLimit at
once, as before. Each save still keeps spent + reserved <= the limit. UNCHANGED: _ledger() (base providers.py:
814-839) drops reservations of processes that are gone; _lock() (base :806-812) is an fcntl flock on SPEND.json.lock
taken through a NEW open file each time, so threads of one process exclude each other too.

TESTS: tests/package/test_meter.py (a deadline miss through a metered router fails over, books, and the meter
counts the booking); tests/providers/test_reserve_wait.py (six workers with room for four: all six answer, never more
than four in flight; spend alone over the limit: refused at once with a call in flight; a wait that ends still kept
out: refused, and never two reservations past the limit). Mutation checks: 3 of 3 and 4 of 4 killed.

PLEASE CHECK: (1) Can the wait deadlock or starve: can a call in flight need anything a waiting call holds? (2) Is
the limit ever passed: any path where a reservation is saved with spent + reserved > limit? (3) Callers that assumed
SpendLimit comes back at once: the wait runs before the call's deadline (_within) starts; can a caller with its own
time budget (prescreen, ruling 101's wait estimate, the shadow's background asks) now hang for long? (4) Is "best" right
for an abandoned call, and is any other wrapper of a Router method left with an old signature? (5) Test timing.

AFTER CYCLE 1 (both reviewers' P1: the wait runs before the call's deadline starts): THE WAIT IS NOW OPT-IN.
Router(reserve_wait_s=0.0) by default refuses at once, as before, for every caller; only the ledger build's router
(tests/package/proof_ledger.py build_router) opts in with proof_ly.RESERVE_WAIT_S = 600 s. test_meter.py became
tests/package/test_ledger_router.py (the meter tests + the ledger build's router waits); test_reserve_wait.py adds a
default router's refusal at once and polls in place of fixed sleeps. 9 of 9 mutations killed.
PLEASE CHECK AGAIN: (1) any caller still exposed to a wait it did not ask for; (2) the opt-in itself; (3) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
