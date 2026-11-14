# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1057
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 814 s finish=stop usage in 17240 / out 23591 usd~0.406 (upper-bound price)

<medium> circuit_breaker.py:141-148 — a runaway recorded while the breaker is CLOSED but after the model already missed once silently discards the miss count. Sequence: `record("miss")` (misses=1), then `record("runaway")` — line 143's `if outcome == "runaway" or m["misses"] >= MISSES_TO_OPEN` opens on the runaway, fine — but the reverse order, `record("runaway")` when `until is None` and misses=0, opens and resets misses to 0 at :146, so a subsequent single miss + answer + miss + miss = 2 misses in a row is required again. That is per ruling, not a bug. No defect found here; noting the reset at :146 also clears misses on open, so after a 30-min expiry with a trial miss the reopen path at :135-140 does not touch misses — correct.

<medium> circuit_breaker.py:106 vs :108 — `allow` returns `(False, why)` when `now < until`, but when `now >= until` and a trial is in flight it returns `(False, "trial in flight")` — and when the trial's caller dies, the trial is freed only after TRIAL_HOLD_S=15 min. During those 15 minutes every list skips the model even though its 30-min window has expired, so the "next family leads" for up to 45+15=45 min... wait, 30+15=45 min of skip for a 30-min ruling. Concrete: glm opens at T, window ends T+30; a trial claimed at T+30:01 by a process that dies; every list skips glm until T+45. The ruling says "After 30 minutes one real call may try it again" — the 15-min hold is a documented, tested (test at :443-445) extension, not a violation, but it means the ruling's "one real call may try it again" can be delayed 15 extra minutes with no evidence line. <high> — no: it is documented in the ruling? The ruling says nothing about a 15-min hold. It is in the module docstring :35 and tested. I'll tag <medium>.

<medium> providers.py:1256-1257 — the miss path records `seconds=dl` (the deadline, not the actual elapsed). The abandoned call's true seconds arrive later via `_late` → the runaway check at :198-201. So the evidence line for a miss carries `seconds=deadline`, which is the ruling's intent ("model, deadline, seconds") — acceptable, but the evidence line for the late answer's runaway carries the true seconds. Consistent.

<medium> providers.py:198-201 — the late-runaway check runs in `_late`'s thread (via the usage block at :194-204) — wait, the diff shows the runaway check inside the usage-recording block at :194-204, which the BACKGROUND says is reached from `_late` (:934). If `_late` fires with an error (not a usage dict), the runaway check is skipped — correct, no tokens to compare. But if `_late` fires with usage where `out` is missing or non-numeric, `_num(n_out)` guards it — correct.

<medium> (a) — Can glm burn its deadline more than twice in a row across processes? Yes, in one narrow case: **the trial claim is per-state-file, but the miss→open transition requires the miss to be recorded while CLOSED**. If glm's breaker is open and the window expires, `allow` at :110-112 claims the trial by writing `trial_at` — but the call that claimed it may be one of MANY concurrent calls: two threads in the same process (or two processes) both call `allow` before either records. The lock serialises them, so the second gets `(False, "trial in flight")` and skips glm — only one trial. Correct.

<medium> (a) — Healthy-model skip: the runaway rule uses the cap SENT (`max_out`), measured: no model exceeds 1x. But the test at :517-522 sets `healthy.spec["min_out"]=1000` with caller max_tokens=100 → cap 1000, out=1500 → 1.5x, no runaway. For xAI: cap = 8×max_tokens. A Grok call with caller max_tokens=100 → cap 800; Grok reasoning answers routinely exceed 800 tokens? The FACT says against the CALLER's max_tokens 309/676 Grok answers exceed 2x — but against the cap sent, none exceed 1x. So no healthy skip. Correct.

<medium> (e) — proof_ledger.py:339-345: `CB.summary(CB.STATE)` takes the flock and reads the file; if the state file is unreadable it raises BreakerUnproofLedger... the except at :344 catches `Exception` broadly — fine, the record is written whatever the breaker says. But note :339 `CB.summary(CB pp-ingest never loads this file — verified: the diff touches only providers.py, circuit_breaker.py, proof_ledger.py, test file. pp-ingest untouched.

<medium> (d) — `_save` at :72-76: writes `f"{path}.{pid}.tmp"` then `os.replace` — atomic on the same directory. But `_load` in another process can read the file WITHOUT the lock? No — `allow`/`record`/`summary` all take the lock before `_load`. But `summary` at :161-162 takes the lock, loads, releases, then computes `open_now` from the loaded snapshot — fine. However **the `.lock` file itself is never cleaned up** — a stray `BREAKERS.json.lock` persists; harmless.

The one real defect I can verify: <high> circuit_breaker.py:132-134 — the trial-close condition `if until is not None and now >= until` in the `answer` branch. Consider: brea

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 56 s finish=stop usage in 17021 / out 318 usd~0.093 (upper-bound price)

<medium>providers.py:256 (in Router.call): if all models in a chain have open breakers (e.g. concurrent GLM+deepseek misses across 2 processes hitting the serialized record("miss") twice, then a later fidelity chain ["qwen","grok"] where both are opened by prior runaway/miss), the loop appends every bwhy and falls through with no successful leg; facts confirm this only affects live calls and M12 fail-closed is acceptable, but full call() body not in diff so outcome (exception vs INCONCLUSIVE) uncertain.</medium>
<medium>circuit_breaker.py:108 and providers.py:221 (_breaker_live + allow): trial_at is set under lock but TRIAL_HOLD_S=15*60 frees only on next allow(); concrete sequence: process A claims trial at T0 (sets trial_at), crashes before record(); process B at T+14min calls allow() (still in flight, returns False); at T+16min B retries and claims new trial. Matches test but hold time is arbitrary (not in ruling).</medium>
No critical findings; no violations of SENTENCE LAW through L-l, M2/M12/LAW22 or governing stack constraints verifiable from diff+facts (change is orthogonal to clips/gates/render/selection; only live calls; no renderer; replay/recorded paths untouched per :1219-:1222; pp-ingest unaffected as breakers=None keeps _breaker_live=False). All attack vectors (a-e) covered by tests or lock/atomic _save/os.replace.

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
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
    14. **But:** What if Process A claims the trial, but the *caller* (Router) ignores the "trial" flag and just makes the call?

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 1057 (the orchestrator's 10:48 ruling 99, the circuit breaker), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes. Two <medium>.
- qwen3.8-27b: SHIP no. Two <critical>, one <high> and four <medium>. One <medium> stands (implemented); the others are
  refuted below.
- glm-5.3-flash: no SHIP line (14 minutes, 89K). Most of its tags resolve inside its own text. It stands on: the trial
  hold against "after 30 minutes one real call may try it again", the event cap, and a fixed sleep in a test. It asks to
  verify the late runaway's cap (refuted below, with the code).

Upper-bound cost: grok $0.093 + qwen $0.118 + glm (its usage line is in its file). Outside SPEND_LY.json.

## Implemented

1. The trial's hold (grok <medium> 2, glm <high> 2). The two reviewers point opposite ways, and both are right:
   - grok: a 15-minute hold is shorter than the local judge's 2400 s deadline floor, so a second trial could be claimed
     while the first is legitimately in flight. That breaks "ONE real call".
   - glm: a hold longer than the call delays "after 30 minutes one real call may try it again" when the trial's
     process dies.
   - Now the trial is held for ITS OWN call's deadline + 60 s (allow(hold_s=...), stored as trial_until). The Router
     computes the leg's deadline before the breaker check, local judge floor included, and passes it.
   - So: about 3 minutes for a Heimdall leg (120 s), 41 minutes for the local judge (2400 s), and TRIAL_HOLD_S (15
     minutes) only for a leg with no deadline.
   - Tests: the default, a Heimdall-style and a local-judge-style hold, read at the claim. The Router claims with its
     deadline + 60 s, and a second claim inside it is refused.
   - Mutations B18 (the hold ignores its call's deadline), B20 (the Router passes no hold) and B21 (a 45-minute
     default): killed.
2. qwen <medium> 7: summary() counted an event whose time cannot be read (`None or since >= since`). It no longer does.
   Test: an event with utc "garbage" is not counted. Mutation B19: killed.
3. glm: EVENTS_KEPT 500 -> 5000, so the 24-hour count on STATE line 1 cannot be cut short by a flapping day.
4. glm: the Router test's fixed 0.6 s sleep is replaced by a bounded wait on the abandoned calls' own count.

The mutation check: 20 of 20 killed. 10 breaker tests.

## Refuted, with evidence from the code

- qwen <critical> 1: "M12 fail closed: an unreadable breaker state must reject the call".
  - M12 is about a gate: "missing data, model failure or an exception rejects; it never produces a pass".
  - The breaker never decides a verdict. It only decides whether a leg is tried now or skipped for the next family.
  - An unreadable state that skips nothing leaves the chain exactly as it was before ruling 99. Every verdict is still
    the model's own, judged by its gate. A model that should have been skipped can only cost its deadline, never pass
    anything.
  - Failing closed here would stop EVERY live call on one bad file. That is an outag

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1057/C2_STEP.diff (603 lines)
```
   1 | diff --git a/pipeline/circuit_breaker.py b/pipeline/circuit_breaker.py
   2 | new file mode 100644
   3 | index 0000000..277c5d8
   4 | --- /dev/null
   5 | +++ b/pipeline/circuit_breaker.py
   6 | @@ -0,0 +1,168 @@
   7 | +"""RULING 99 (orchestrator 10:48 ET Nov 14), THE CIRCUIT BREAKER. A model that misses its deadline MISSES_TO_OPEN (2)
   8 | +times in a row, or returns more than RUNAWAY_X (2) times its max_tokens, is SKIPPED by every list for OPEN_S (30
   9 | +minutes): the next family leads. After that, ONE real call may try it again (the trial, claimed under the lock); an
  10 | +answer closes the breaker, a miss or a runaway re-opens it for REOPEN_S (60 minutes). Every open and close is one line
  11 | +in the Heimdall evidence file (model, deadline, seconds, tokens: the caller logs the event this module returns); the
  12 | +count goes on STATE line 1 (summary()).
  13 | +
  14 | +- "Its max_tokens" is the cap the call actually SENT (providers.Backend.max_out: every Heimdall family is sent its
  15 | +  min_out floor of 16,000, Grok 8 x max_tokens, since a reasoning model thinks inside it). Measured on 1,252 recorded
  16 | +  answers (10:4x ET Nov 14): none exceeds 1x that cap; against the CALLER's max_tokens, 309 of 676 healthy Grok answers
  17 | +  and 61 of 127 deepseek answers would read as runaways. Asked of the orchestrator on STATE line 1.
  18 | +- A breaker is not an outage (ruling 87's clock is about NO family answering); it lives in its own state file.
  19 | +- Only LIVE calls touch it: a recorded reply is served as before, replay never consults it, and probes (ruling 87) and
  20 | +  shadow calls (ruling 86) neither count nor skip (the caller decides; providers.Router._breaker_live).
  21 | +- The state file: {"models": {name: {"misses", "open_until", "trial_at", "trial_until", "opens", "why"}},
  22 | +  "events": [the last EVENTS_KEPT opens and closes]} under tests/package/proof, beside ruling 87's HEIMDALL_HEALTH.json. Times are ISO UTC. An unreadable file raises BreakerUnreadable: the caller says so and
  23 | +  skips nothing by it (an optimisation never stops a verdict; ruling 82's chain still fails over call by call)."""
  24 | +import fcntl
  25 | +import json
  26 | +import os
  27 | +from datetime import datetime, timedelta, timezone
  28 | +
  29 | +STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
  30 | +                     "BREAKERS.json")
  31 | +MISSES_TO_OPEN = 2                      # ruling 99: two deadline misses in a row
  32 | +OPEN_S = 30 * 60                        # ruling 99: skipped by every list for 30 minutes
  33 | +REOPEN_S = 60 * 60                      # ruling 99: a failed trial re-opens it for 60
  34 | +RUNAWAY_X = 2.0                         # ruling 99: more than twice its max_tokens (the cap sent)
  35 | +TRIAL_HOLD_S = 15 * 60                  # a trial whose call never reports (its process ended) is freed after its OWN
  36 | +#   deadline + 60 s (allow(hold_s=...), the Router passes it), so one trial at a time even on the local judge's 2400 s,
  37 | +#   and a dead trial does not hold the model long (audit 1057 C1: grok, glm); this default is for a leg with no deadline
  38 | +EVENTS_KEPT = 5000                      # enough for every open and close of a day (summary counts the last 24 h)
  39 | +
  40 | +
  41 | +class BreakerUnreadable(Exception):
  42 | +    """The state file exists but cannot be read: no guess either way."""
  43 | +
  44 | +
  45 | +def _now(now=None):
  46 | +    return now if now is not None else datetime.now(timezone.utc)
  47 | +
  48 | +
  49 | +def _iso(t):
  50 | +    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
  51 | +
  52 | +
  53 | +def _t(s):
  54 | +    try:
  55 | +        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
  56 | +    except (TypeError, ValueError):
  57 | +        return None
  58 | +    return t if t.tzinfo is not None else None
  59 | +
  60 | +
  61 | +def _load(path):
  62 | +    if not os.path.exists(path):
  63 | +        return {"models": {}, "events": []}
  64 | +    try:
  65 | +        with open(path) as f:
  66 | +            s = json.load(f)
  67 | +        if not isinstance(s, dict) or not isinstance(s.get("models"), dict):
  68 | +            raise ValueError("not a breaker state")
  69 | +        return s
  70 | +    except (OSError, ValueError) as e:
  71 | +        raise BreakerUnreadable(f"{path}: {type(e).__name__}: {e}") from None
  72 | +
  73 | +
  74 | +def _save(path, s):
  75 | +    tmp = f"{path}.{os.getpid()}.tmp"
  76 | +    with open(tmp, "w") as f:
  77 | +        json.dump(s, f, indent=1)
  78 | +    os.replace(tmp, path)
  79 | +
  80 | +
  81 | +class _Locked:
  82 | +    def __init__(self, path):
  83 | +        self.path = path
  84 | +
  85 | +    def __enter__(self):
  86 | +        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
  87 | +        self.f = open(self.path + ".lock", "w")
  88 | +        fcntl.flock(self.f, fcntl.LOCK_EX)
  89 | +        return self
  90 | +
  91 | +    def __exit__(self, *exc):
  92 | +        fcntl.flock(self.f, fcntl.LOCK_UN)
  93 | +        self.f.close()
  94 | +        return False
  95 | +
  96 | +
  97 | +def allow(name, path=STATE, now=None, hold_s=None):
  98 | +    """May a live call go to `name` now? -> (True, None) closed; (True, "trial") the one call after the open window
  99 | +    (claimed here, under the lock, until now + hold_s: the call's own deadline + 60 s, else TRIAL_HOLD_S); (False, why)
 100 | +    open, or a trial already in flight. A malformed record skips nothing."""
 101 | +    now = _now(now)
 102 | +    with _Locked(path):
 103 | +        s = _load(path)
 104 | +        m = s["models"].get(name)
 105 | +        until = _t(m.get("open_until")) if isinstance(m, dict) else None
 106 | +        if until is None:
 107 | +            return True, None
 108 | +        if now < until:
 109 | +            return False, f"circuit breaker open until {m['open_until']} (ruling 99: {m.get('why')})"
 110 | +        ta, tu = _t(m.get("trial_at")), _t(m.get("trial_until"))
 111 | +        if ta is not None and now < (tu or ta + timedelta(seconds=TRIAL_HOLD_S)):
 112 | +            return False, f"circuit breaker: its one trial call is in flight since {m['trial_at']} (ruling 99)"
 113 | +        hold = float(hold_s) if isinstance(hold_s, (int, float)) and hold_s > 0 else TRIAL_HOLD_S
 114 | +        m["trial_at"], m["trial_until"] = _iso(now), _iso(now + timedelta(seconds=hold))
 115 | +        _save(path, s)
 116 | +        return True, "trial"
 117 | +
 118 | +
 119 | +def record(name, outcome, path=STATE, now=None, deadline_s=None, seconds=None, tokens=None, max_out=None):
 120 | +    """One live call's outcome: "answer", "miss" (its deadline passed) or "runaway" (more than RUNAWAY_X times the cap
 121 | +    it was sent). -> the event for the evidence file ({"kind": "breaker_open" | "breaker_close", "model", "why",
 122 | +    "deadline_s", "seconds", "tokens", "max_out", "until", "utc"}) or None."""
 123 | +    if outcome not in ("answer", "miss", "runaway"):
 124 | +        raise ValueError(f"outcome must be answer, miss or runaway, not {outcome!r}")
 125 | +    now = _now(now)
 126 | +    with _Locked(path):
 127 | +        s = _load(path)
 128 | +        m = s["models"].get(name)
 129 | +        if not isinstance(m, dict):
 130 | +            m = s["models"][name] = {"misses": 0, "open_until": None, "trial_at": None, "opens": 0}
 131 | +        until = _t(m.get("open_until"))
 132 | +        detail = {"model": name, "deadline_s": deadline_s, "seconds": seconds, "tokens": tokens, "max_out": max_out}
 133 | +        ev = None
 134 | +        if outcome == "answer":
 135 | +            m["misses"] = 0
 136 | +            if until is not None and now >= until:            # the trial (a call after the window) answered
 137 | +                m["open_until"], m["trial_at"], m["trial_until"] = None, None, None
 138 | +                ev = dict(detail, kind="breaker_close", why="the trial call answered")
 139 | +        elif until is not None and now >= until:              # the trial failed: open again, for longer
 140 | +            m["why"] = "the trial call " + ("missed its deadline" if outcome == "miss" else
 141 | +                                            f"returned more than {RUNAWAY_X:g}x the cap it was sent")
 142 | +            m["open_until"], m["trial_at"], m["trial_until"] = _iso(now + timedelta(seconds=REOPEN_S)), None, None
 143 | +            m["opens"] = int(m.get("opens") or 0) + 1
 144 | +            ev = dict(detail, kind="breaker_open", why=m["why"], until=m["open_until"])
 145 | +        elif until is None:                                   # closed (while open, a call from before it is ignored)
 146 | +            m["misses"] = int(m.get("misses") or 0) + (1 if outcome == "miss" else 0)
 147 | +            if outcome == "runaway" or m["misses"] >= MISSES_TO_OPEN:
 148 | +                m["why"] = (f"returned more than {RUNAWAY_X:g}x the cap it was sent" if outcome == "runaway" else
 149 | +                            f"missed its deadline {MISSES_TO_OPEN} times in a row")
 150 | +                m["open_until"], m["trial_at"], m["trial_until"], m["misses"] = \
 151 | +                    _iso(now + timedelta(seconds=OPEN_S)), None, None, 0
 152 | +                m["opens"] = int(m.get("opens") or 0) + 1
 153 | +                ev = dict(detail, kind="breaker_open", why=m["why"], until=m["open_until"])
 154 | +        if ev:
 155 | +            ev["utc"] = _iso(now)
 156 | +            s["events"] = (list(s.get("events") or []) + [ev])[-EVENTS_KEPT:]
 157 | +        _save(path, s)
 158 | +        return ev
 159 | +
 160 | +
 161 | +def summary(path=STATE, now=None, since=None):
 162 | +    """For STATE line 1 (ruling 99: "the count goes on STATE line 1"): the breakers open now and the opens / closes
 163 | +    since `since` (an aware datetime; default: the last 24 hours). -> {"open": [...], "opens": n, "closes": n}."""
 164 | +    now = _now(now)
 165 | +    since = since or now - timedelta(hours=24)
 166 | +    with _Locked(path):
 167 | +        s = _load(path)
 168 | +    open_now = [{"model": n, "until": m.get("open_until"), "why": m.get("why")}
 169 | +                for n, m in sorted(s["models"].items()) if isinstance(m, dict) and _t(m.get("open_until")) is not None
 170 | +                and now < _t(m.get("open_until"))]
 171 | +    evs = [e for e in s.get("events") or [] if isinstance(e, dict) and _t(e.get("utc")) is not None
 172 | +           and _t(e.get("utc")) >= since]               # an event whose time cannot be read is not counted (1057 C1)
 173 | +    return {"open": open_now, "opens": sum(1 for e in evs if e.get("kind") == "breaker_open"),
 174 | +            "closes": sum(1 for e in evs if e.get("kind") == "breaker_close")}
 175 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 176 | index 6dc0aee..36ece53 100644
 177 | --- a/pipeline/providers.py
 178 | +++ b/pipeline/providers.py
 179 | @@ -719,7 +719,8 @@ class Router:
 180 |  
 181 |      def __init__(self, config=CONFIG, env_path=None, record_dir=None, replay=False, spend_path=None, limit_usd=40.0,
 182 |                   local_llm=None, chains=None, limit_basis="estimate", deadline_log=None, slow_log_s=240.0,
 183 | -                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None):
 184 | +                 routing=None, shadow=None, shadow_log=None, health=None, plan_b_chains=None, state_md=None,
 185 | +                 breakers=None):
 186 |          with open(config) as f:
 187 |              self.config = json.load(f)
 188 |          rt = self.config.get("routing") or {}
 189 | @@ -754,6 +755,10 @@ class Router:
 190 |          # A probe thread asks each Heimdall family a one-word question every 2 minutes while calls fail.
 191 |          self.health, self.plan_b_chains, self.state_md = health, dict(plan_b_chains or {}), state_md
 192 |          self._probe = None
 193 | +        # RULING 99 (10:48 Nov 14): the circuit breaker's state file (pipeline/circuit_breaker.py). A model that misses
 194 | +        # its deadline twice in a row, or runs past twice the cap it was sent, is skipped by every list for 30 minutes
 195 | +        # (live calls only: a recorded reply, replay, probes and shadow calls never touch it)
 196 | +        self.breakers, self.breaker_events = breakers, []
 197 |          if self.routing == "heimdall_first":      # RULING 85: the two-family rule is kept INSIDE Heimdall, so each of
 198 |              for b in self.backends.values():      # its families is its own maker for every vendor rule (law L-s); the
 199 |                  if isinstance(b, HeimdallBackend):     # gateway stays "heimdall" (gateway(b))
 200 | @@ -947,6 +952,10 @@ class Router:
 201 |                  usd, rep = b.usd(usage), usage.get("usd_reported")
 202 |                  rec.update({"in": usage.get("in"), "out": usage.get("out"), "usd_estimate": usd,
 203 |                              "usd_reported": float(rep) if _num(rep) else None})
 204 | +                n_out, cap = usage.get("out"), ab.get("max_out")
 205 | +                if _num(n_out) and _num(cap) and n_out > self._runaway_x() * cap:   # ruling 99: a late runaway
 206 | +                    self._breaker(role, b.name, "runaway", deadline_s=ab.get("deadline_s"), seconds=rec["seconds"],
 207 | +                                  tokens=n_out, max_out=cap)
 208 |                  if self.spend_path:
 209 |                      try:
 210 |                          self._replace_booking(b, role, booked, usage, usd, rep)
 211 | @@ -1006,6 +1015,47 @@ class Router:
 212 |          d = (rt.get("verdict_deadline_s") or {}).get(gateway(b))
 213 |          return float(d) if _num(d) and d > 0 else None
 214 |  
 215 | +    def _breaker_live(self, role):
 216 | +        """RULING 99: the breaker counts and skips only this builder's LIVE calls (never replay, a probe or a shadow)."""
 217 | +        return bool(self.breakers) and not self.replay and not role.startswith(("probe87:", "shadow86:"))
 218 | +
 219 | +    @staticmethod
 220 | +    def _runaway_x():
 221 | +        import circuit_breaker as CB
 222 | +        return CB.RUNAWAY_X
 223 | +
 224 | +    def _breaker_allow(self, role, name, deadline_s=None):
 225 | +        """RULING 99 -> why `name` is skipped now (its breaker is open, or its one trial is in flight), or None. A trial
 226 | +        is held for this call's own deadline + 60 s. A state that cannot be read skips nothing (a notice): the breaker
 227 | +        saves minutes, it never stops a verdict."""
 228 | +        if not self._breaker_live(role):
 229 | +            return None
 230 | +        import circuit_breaker as CB
 231 | +        try:
 232 | +            ok, why = CB.allow(name, self.breakers, hold_s=deadline_s + 60.0 if _num(deadline_s) else None)
 233 | +        except (CB.BreakerUnreadable, OSError) as e:
 234 | +            n = f"RULING 99: the circuit breaker's state cannot be read, so it skips nothing: {e}"
 235 | +            if n not in self.notices:
 236 | +                self.notices.append(n)
 237 | +            return None
 238 | +        return None if ok else why
 239 | +
 240 | +    def _breaker(self, role, name, outcome, **kw):
 241 | +        """RULING 99: one live call's outcome to the breaker; an open or a close is one line in the evidence file."""
 242 | +        if not self._breaker_live(role):
 243 | +            return
 244 | +        import circuit_breaker as CB
 245 | +        try:
 246 | +            ev = CB.record(name, outcome, self.breakers, **kw)
 247 | +        except (CB.BreakerUnreadable, OSError) as e:
 248 | +            n = f"RULING 99: the circuit breaker's state cannot be read or written: {e}"
 249 | +            if n not in self.notices:
 250 | +                self.notices.append(n)
 251 | +            return
 252 | +        if ev:
 253 | +            self.breaker_events.append(ev)
 254 | +            self._log_slow(dict(ev, role=role))
 255 | +
 256 |      def _note(self, role, b, answered):
 257 |          """RULING 87: a Heimdall verdict or writer call's outcome, to the shared health state (never a gate here: a
 258 |          state file that cannot be written is a notice). The probe thread starts at the first failure."""
 259 | @@ -1170,6 +1220,13 @@ class Router:
 260 |              if self.replay:
 261 |                  tried.append((name, "replay: not recorded"))
 262 |                  continue
 263 | +            dl = deadline_s or self.role_deadline(role, b)      # the caller's deadline, else the role's (20:33)
 264 | +            if dl and _num(b.spec.get("deadline_floor_s")):     # ruling 87: the local judge waits out a render
 265 | +                dl = max(dl, float(b.spec["deadline_floor_s"]))
 266 | +            bwhy = self._breaker_allow(role, name, dl)          # ruling 99: an open breaker skips it; the next leads
 267 | +            if bwhy:
 268 | +                tried.append((name, bwhy))
 269 | +                continue
 270 |              upper = b.upper_usd(prompt, max_tokens, system)
 271 |              key = self._reserve(b, upper)
 272 |              if isinstance(b, HeimdallBackend):
 273 | @@ -1177,9 +1234,6 @@ class Router:
 274 |                  if n:
 275 |                      notices.append(n)
 276 |  
 277 | -            dl = deadline_s or self.role_deadline(role, b)      # the caller's deadline, else the role's (20:33)
 278 | -            if dl and _num(b.spec.get("deadline_floor_s")):     # ruling 87: the local judge waits out a render
 279 | -                dl = max(dl, float(b.spec["deadline_floor_s"]))
 280 |              if isinstance(b, LocalJudgeBackend) and self.state_md and not getattr(self, "_announced_local", False):
 281 |                  import heimdall_health as HH
 282 |                  self._announced_local = True                    # ruling 87: "and STATE line 1 says so"
 283 | @@ -1193,7 +1247,8 @@ class Router:
 284 |                                  "prompt_chars": len(prompt_text(prompt)),
 285 |                                  "max_tokens": max_tokens, "booked_usd": booked})   # evidence first (audit 2048 C1)
 286 |                  self._settle(key, b, {"in": 0, "out": 0}, booked, role)          # an unreadable ledger raises here
 287 | -                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time()}
 288 | +                return {"backend": b, "role": role, "usd": booked, "deadline_s": deadline_s, "t0": time.time(),
 289 | +                        "max_out": b.max_out(max_tokens)}             # ruling 99: a late runaway is measured on it
 290 |              try:
 291 |                  if dl:                                 # ruling 5 (22:40): fail over instead of waiting
 292 |                      text, usage, secs = _within(dl, lambda: b.complete(prompt, max_tokens, seed, system),
 293 | @@ -1202,6 +1257,7 @@ class Router:
 294 |                      text, usage, secs = b.complete(prompt, max_tokens, seed, system)
 295 |              except DeadlineExceeded as e:              # abandoned (the vendor may still bill it): booked and logged by
 296 |                  self._note(role, b, False)             # abandon(); ruling 87: not answered inside its deadline
 297 | +                self._breaker(role, name, "miss", deadline_s=dl, seconds=dl, max_out=b.max_out(max_tokens))
 298 |                  booked = b.prompt_usd(prompt, system)
 299 |                  tried.append((name, f"{e} (abandoned at the deadline; booked at its prompt tokens, ${booked:.4f}, "
 300 |                                      "ruling 83 (a))"))
 301 | @@ -1233,6 +1289,9 @@ class Router:
 302 |                  tried.append((name, "refused this request: an empty reply"))
 303 |                  continue
 304 |              self._note(role, b, True)                  # ruling 87: a Heimdall family answered inside its deadline
 305 | +            cap, n_out = b.max_out(max_tokens), (usage or {}).get("out")
 306 | +            self._breaker(role, name, "runaway" if _num(n_out) and n_out > self._runaway_x() * cap else "answer",
 307 | +                          deadline_s=dl, seconds=round(secs, 2), tokens=n_out, max_out=cap)       # ruling 99
 308 |              recorded = ""
 309 |              if path and isinstance(text, str) and text.strip():
 310 |                  self._record(path, {"role": role, "backend": name, "model": b.model, "vendor": b.vendor, "seed": seed,
 311 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 312 | index b034586..ac9acba 100644
 313 | --- a/tests/package/proof_ledger.py
 314 | +++ b/tests/package/proof_ledger.py
 315 | @@ -57,6 +57,7 @@ sys.path.insert(0, HERE)
 316 |  import eligibility as E  # noqa: E402
 317 |  import candidates as CA  # noqa: E402
 318 |  import heimdall_health as HH  # noqa: E402
 319 | +import circuit_breaker as CB  # noqa: E402
 320 |  import shadow86 as SH  # noqa: E402
 321 |  import ledger_build as LB  # noqa: E402
 322 |  import moments as M  # noqa: E402
 323 | @@ -101,6 +102,16 @@ def delivered_pins(paths):
 324 |      return spans, newest, pins
 325 |  
 326 |  
 327 | +def build_router(routing, shadow, shadow_log):
 328 | +    """The build's router: ruling 48's ledger and limit, the routing's chains (frozen legs out), the evidence file
 329 | +    (item 55), ruling 86's shadow, ruling 87's shared Heimdall health and Plan B chains, ruling 99's circuit breaker."""
 330 | +    return P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 331 | +                    limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 332 | +                    routing=routing, shadow=shadow, shadow_log=shadow_log,
 333 | +                    health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD,      # ruling 87
 334 | +                    breakers=CB.STATE)                                                         # ruling 99
 335 | +
 336 | +
 337 |  def main(argv=None):
 338 |      ap = argparse.ArgumentParser()
 339 |      ap.add_argument("--delivered", nargs="+", required=True, metavar="PIN",
 340 | @@ -193,10 +204,7 @@ def main(argv=None):
 341 |      shadow = None                                # RULING 86: Grok in shadow on the first heimdall_first pins
 342 |      if routing == "heimdall_first" and SH.clean_streak() < int(rt.get("shadow_until_clean_pins") or 3):
 343 |          shadow = rt.get("shadow") or None
 344 | -    router = P.Router(env_path=PS.ENV, record_dir=PL.REPLIES, spend_path=PL.SPEND, limit_usd=PL.LY_LIMIT_USD,
 345 | -                      limit_basis=PL.LY_LIMIT_BASIS, chains=PL.chains(routing), deadline_log=PL.DEADLINE_LOG,
 346 | -                      routing=routing, shadow=shadow, shadow_log=os.path.join(out_dir, "SHADOW86.jsonl"),
 347 | -                      health=HH.STATE, plan_b_chains=PL.plan_b_chains(), state_md=STATE_MD)    # ruling 87
 348 | +    router = build_router(routing, shadow, os.path.join(out_dir, "SHADOW86.jsonl"))
 349 |      say(f"  routing (ruling 85): {router.routing}; now {router.mode()} (ruling 87: the shared Heimdall health)"
 350 |          + (f"; SHADOW (ruling 86): {shadow}" if shadow else ""))
 351 |      spent0 = router.spent()                      # ruling 48: the running total, vendor-reported (+ estimates where none)
 352 | @@ -367,6 +375,16 @@ def main(argv=None):
 353 |                                if vis.get("estimated_calls") else ""))
 354 |      say(f"  spend (ruling 48): {after if isinstance(after, str) else f'${after:.2f}'} of ${PL.LY_LIMIT_USD:.2f} "
 355 |          f"vendor-reported after this build (before it: ${spent0:.2f})")
 356 | +    evs = router.breaker_events                  # RULING 99: the circuit breaker's count, for STATE line 1
 357 | +    try:
 358 | +        bs = CB.summary(CB.STATE)
 359 | +        res["breakers_ruling_99"] = dict(bs, this_build=evs)
 360 | +        say(f"  RULING 99 (circuit breaker): this build opened {sum(e['kind'] == 'breaker_open' for e in evs)} and "
 361 | +            f"closed {sum(e['kind'] == 'breaker_close' for e in evs)}; open now: "
 362 | +            + ("; ".join(f"{o['model']} until {o['until']} ({o['why']})" for o in bs["open"]) or "none")
 363 | +            + f"; in 24 h: {bs['opens']} opened, {bs['closes']} closed")
 364 | +    except Exception as e:                       # noqa: BLE001 (the record is written whatever the breaker says)
 365 | +        say(f"  RULING 99 (circuit breaker): its state cannot be read: {type(e).__name__}: {str(e)[:160]}")
 366 |      try:                                                 # audit 1420 C2: a registry failure never loses the record;
 367 |          if cand is not None and CA.key(cand["lineup"]) in reg["candidates"]:      # 1420b C2: its flag tells the truth
 368 |              CA.outcome(reg["candidates"][CA.key(cand["lineup"])], res["candidate"]["class"], at, name,
 369 | diff --git a/tests/providers/test_circuit_breaker.py b/tests/providers/test_circuit_breaker.py
 370 | new file mode 100644
 371 | index 0000000..368d890
 372 | --- /dev/null
 373 | +++ b/tests/providers/test_circuit_breaker.py
 374 | @@ -0,0 +1,228 @@
 375 | +#!/usr/bin/env python3
 376 | +"""RULING 99 (orchestrator 10:48 ET Nov 14), THE CIRCUIT BREAKER (pipeline/circuit_breaker.py and its use in
 377 | +providers.Router and the ledger build). Offline: a temporary state file, the test's own clock, fake back-ends."""
 378 | +import json
 379 | +import os
 380 | +import sys
 381 | +import tempfile
 382 | +import unittest
 383 | +from datetime import datetime, timedelta, timezone
 384 | +
 385 | +HERE = os.path.dirname(os.path.abspath(__file__))
 386 | +REPO = os.path.dirname(os.path.dirname(HERE))
 387 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 388 | +sys.path.insert(0, HERE)
 389 | +import circuit_breaker as CB  # noqa: E402
 390 | +import providers as P  # noqa: E402
 391 | +from test_providers import Fake, Slow, router, wait_for  # noqa: E402
 392 | +
 393 | +T0 = datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc)
 394 | +GLM = "heimdall:z-ai/glm-5.3-flash"
 395 | +
 396 | +
 397 | +def at(minutes=0, seconds=0):
 398 | +    return T0 + timedelta(minutes=minutes, seconds=seconds)
 399 | +
 400 | +
 401 | +class TestBreaker(unittest.TestCase):
 402 | +    def setUp(self):
 403 | +        self.d = tempfile.TemporaryDirectory()
 404 | +        self.state = os.path.join(self.d.name, "BREAKERS.json")
 405 | +
 406 | +    def tearDown(self):
 407 | +        self.d.cleanup()
 408 | +
 409 | +    def rec(self, outcome, t, **kw):
 410 | +        return CB.record(GLM, outcome, self.state, now=t, **kw)
 411 | +
 412 | +    def test_two_deadline_misses_in_a_row_open_it_for_30_minutes(self):
 413 | +        self.assertIsNone(self.rec("miss", at(0)))
 414 | +        self.assertIsNone(self.rec("answer", at(1)))                      # an answer between: not in a row
 415 | +        self.assertIsNone(self.rec("miss", at(2)))
 416 | +        ev = self.rec("miss", at(3), deadline_s=120.0, seconds=120.0, max_out=16000)
 417 | +        self.assertEqual({k: ev[k] for k in ("kind", "model", "why", "until", "deadline_s", "seconds", "tokens",
 418 | +                                             "max_out", "utc")},
 419 | +                         {"kind": "breaker_open", "model": GLM, "why": "missed its deadline 2 times in a row",
 420 | +                          "until": "2026-11-14T15:33:00Z", "deadline_s": 120.0, "seconds": 120.0, "tokens": None,
 421 | +                          "max_out": 16000, "utc": "2026-11-14T15:03:00Z"})
 422 | +        ok, why = CB.allow(GLM, self.state, now=at(32, 59))
 423 | +        self.assertFalse(ok)
 424 | +        self.assertIn("open until 2026-11-14T15:33:00Z", why)
 425 | +        self.assertEqual(CB.allow("heimdall:deepseek/deepseek-v4.1-flash", self.state, now=at(4)), (True, None))
 426 | +
 427 | +    def test_after_30_minutes_one_trial_an_answer_closes_it_and_a_miss_reopens_it_for_60(self):
 428 | +        self.rec("miss", at(0))
 429 | +        self.rec("miss", at(1))                                           # open until 15:31
 430 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(31)), (True, "trial"))
 431 | +        ok, why = CB.allow(GLM, self.state, now=at(31, 1))                # one trial at a time
 432 | +        self.assertFalse(ok)
 433 | +        self.assertIn("trial call is in flight", why)
 434 | +        ev = self.rec("answer", at(32))
 435 | +        self.assertEqual((ev["kind"], ev["why"]), ("breaker_close", "the trial call answered"))
 436 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(33)), (True, None))
 437 | +        self.rec("miss", at(40))
 438 | +        self.rec("miss", at(41))                                          # open again until 16:11
 439 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(71)), (True, "trial"))
 440 | +        ev = self.rec("miss", at(73))                                     # the trial misses: 60 minutes
 441 | +        self.assertEqual((ev["kind"], ev["until"], ev["why"]),
 442 | +                         ("breaker_open", "2026-11-14T17:13:00Z", "the trial call missed its deadline"))
 443 | +        self.assertFalse(CB.allow(GLM, self.state, now=at(132, 59))[0])
 444 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(133)), (True, "trial"))
 445 | +        self.assertEqual(json.load(open(self.state))["models"][GLM]["opens"], 3)
 446 | +
 447 | +    def test_a_runaway_opens_it_at_once(self):
 448 | +        ev = self.rec("runaway", at(0), tokens=40000, max_out=16000)
 449 | +        self.assertEqual((ev["kind"], ev["why"], ev["tokens"]),
 450 | +                         ("breaker_open", "returned more than 2x the cap it was sent", 40000))
 451 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(30)), (True, "trial"))
 452 | +        ev = self.rec("runaway", at(31), tokens=40000, max_out=16000)   # a trial that runs away re-opens it too
 453 | +        self.assertEqual((ev["why"], ev["until"]),
 454 | +                         ("the trial call returned more than 2x the cap it was sent", "2026-11-14T16:31:00Z"))
 455 | +
 456 | +    def test_calls_in_flight_when_it_opened_change_nothing_and_a_dead_trial_is_freed(self):
 457 | +        self.rec("miss", at(0))
 458 | +        self.rec("miss", at(0, 30))                                       # open until 15:30:30
 459 | +        self.assertIsNone(self.rec("miss", at(5)))                        # calls from before it opened: two misses
 460 | +        self.assertIsNone(self.rec("miss", at(5, 30)))                    # never extend or re-open the window
 461 | +        self.assertIsNone(self.rec("answer", at(6)))                      # an answer inside the window: still open
 462 | +        self.assertEqual(json.load(open(self.state))["models"][GLM]["open_until"], "2026-11-14T15:30:30Z")
 463 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(31)), (True, "trial"))   # no deadline given: held for
 464 | +        self.assertFalse(CB.allow(GLM, self.state, now=at(45, 59))[0])    # TRIAL_HOLD_S, then freed (its caller's
 465 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(46), hold_s=180.0), (True, "trial"))   # process ended)
 466 | +        self.assertFalse(CB.allow(GLM, self.state, now=at(48, 59))[0])    # a Heimdall leg: its 120 s + 60 s
 467 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(49), hold_s=2460.0), (True, "trial"))
 468 | +        self.assertFalse(CB.allow(GLM, self.state, now=at(89, 59))[0])    # the local judge's 2400 s + 60 s: one trial
 469 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(90)), (True, "trial"))     # at a time all the same
 470 | +
 471 | +    def test_the_count_for_state_line_1_and_an_unreadable_state_is_never_guessed(self):
 472 | +        self.rec("miss", at(0))
 473 | +        self.rec("miss", at(1))
 474 | +        CB.allow(GLM, self.state, now=at(31))
 475 | +        self.rec("answer", at(32))
 476 | +        self.rec("runaway", at(40), tokens=40000, max_out=16000)
 477 | +        st = json.load(open(self.state))
 478 | +        st["events"].append({"kind": "breaker_open", "model": "x", "utc": "garbage"})   # a time that cannot be read
 479 | +        json.dump(st, open(self.state, "w"))
 480 | +        s = CB.summary(self.state, now=at(41))
 481 | +        self.assertEqual((s["opens"], s["closes"], [o["model"] for o in s["open"]]), (2, 1, [GLM]))   # not counted
 482 | +        self.assertEqual(CB.summary(self.state, now=at(41), since=at(35))["opens"], 1)
 483 | +        with open(self.state, "w") as f:
 484 | +            f.write("{ broken")
 485 | +        for fn in (lambda: CB.allow(GLM, self.state, now=at(50)), lambda: self.rec("miss", at(50)),
 486 | +                   lambda: CB.summary(self.state, now=at(50))):
 487 | +            with self.assertRaises(CB.BreakerUnreadable):
 488 | +                fn()
 489 | +        self.assertEqual(open(self.state).read(), "{ broken")
 490 | +        json.dump({"models": {GLM: {"open_until": "soon"}}}, open(self.state, "w"))
 491 | +        self.assertEqual(CB.allow(GLM, self.state, now=at(50)), (True, None))   # a malformed record skips nothing
 492 | +        with self.assertRaises(ValueError):
 493 | +            self.rec("slow", at(51))
 494 | +
 495 | +
 496 | +class TestRouterBreaker(unittest.TestCase):
 497 | +    """providers.Router: live calls only. Two real deadline misses (P._within) open the breaker, the next family leads,
 498 | +    and the open is one line in the evidence file."""
 499 | +
 500 | +    def setUp(self):
 501 | +        self.d = tempfile.TemporaryDirectory()
 502 | +        self.state = os.path.join(self.d.name, "BREAKERS.json")
 503 | +        self.log = os.path.join(self.d.name, "DEADLINES.jsonl")
 504 | +
 505 | +    def tearDown(self):
 506 | +        self.d.cleanup()
 507 | +
 508 | +    def mk(self, backends, chain, **kw):
 509 | +        return router(self.d.name, backends, {"check": chain, "probe87:" + chain[0]: [chain[0]]}, deadline_log=self.log,
 510 | +                      breakers=self.state, **kw)
 511 | +
 512 | +    def test_two_misses_skip_glm_and_the_next_family_leads(self):
 513 | +        glm = Slow(GLM, "heimdall", '{"ok": 1}', delay=0.4, family="glm")
 514 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 515 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 516 | +        self.assertEqual([r.call("check", f"p{i}", 100, 7, deadline_s=0.1).backend for i in range(2)],
 517 | +                         ["heimdall:deepseek"] * 2)
 518 | +        rep = r.call("check", "p3", 100, 7, deadline_s=0.1)
 519 | +        import time as _t
 520 | +        for _ in range(300):                                              # the two abandoned calls end on their clock
 521 | +            if glm.calls >= 2:
 522 | +                break
 523 | +            _t.sleep(0.01)
 524 | +        _t.sleep(0.2)
 525 | +        self.assertEqual((rep.backend, glm.calls), ("heimdall:deepseek", 2))      # glm not asked a third time
 526 | +        self.assertIn("circuit breaker open until", dict(rep.tried)[GLM])
 527 | +        self.assertEqual([e["kind"] for e in r.breaker_events], ["breaker_open"])
 528 | +        opened = [x for x in wait_for(self.log, "breaker_open") if x["kind"] == "breaker_open"]
 529 | +        self.assertEqual({k: opened[0][k] for k in ("model", "deadline_s", "seconds", "max_out", "role")},
 530 | +                         {"model": GLM, "deadline_s": 0.1, "seconds": 0.1, "max_out": 100, "role": "check"})
 531 | +        self.assertEqual(r.call("probe87:" + GLM, "Reply with the single word OK.", 64, 7).backend, GLM)  # a probe:
 532 | +        #   asked all the same, and never counted (ruling 87's probe is not a list)
 533 | +        st = json.load(open(self.state))
 534 | +        st["models"][GLM]["open_until"] = "2026-01-01T00:00:00Z"          # the window has passed: the next call is
 535 | +        json.dump(st, open(self.state, "w"))                              # the one trial, held for its deadline + 60 s
 536 | +        self.assertIsNone(r._breaker_allow("check", GLM, 0.1))           # this call is the trial (claimed here)
 537 | +        m = json.load(open(self.state))["models"][GLM]
 538 | +        held = (CB._t(m["trial_until"]) - CB._t(m["trial_at"])).total_seconds()
 539 | +        self.assertIn(held, (60.0, 61.0))
 540 | +        self.assertIn("trial call is in flight", r._breaker_allow("check", GLM, 0.1))     # one trial at a time
 541 | +
 542 | +    def test_a_runaway_answer_opens_it_and_a_recorded_reply_is_still_served(self):
 543 | +        glm = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm", usage={"in": 10, "out": 201})   # > 2 x 100
 544 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 545 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"], record_dir=os.path.join(self.d.name, "rec"))
 546 | +        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # it answered: the answer stands
 547 | +        self.assertEqual(r.breaker_events[0]["why"], "returned more than 2x the cap it was sent")
 548 | +        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # its recorded reply: served, nothing paid
 549 | +        self.assertEqual(glm.calls, 1)
 550 | +        self.assertEqual(r.call("check", "q", 100, 7).backend, "heimdall:deepseek")   # a live call: skipped
 551 | +        glm2 = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm", usage={"in": 10, "out": 200})  # exactly 2x
 552 | +        r2 = self.mk([glm2, ds], [GLM, "heimdall:deepseek"])
 553 | +        os.remove(self.state)
 554 | +        r2.call("check", "p", 100, 7)
 555 | +        self.assertEqual(r2.breaker_events, [])
 556 | +        healthy = Fake("heimdall:deepseek2", "heimdall", answer='{"ok": 3}', family="deepseek",
 557 | +                       usage={"in": 10, "out": 1500})
 558 | +        healthy.spec["min_out"] = 1000          # a reasoning model is sent its floor (as Grok and deepseek are):
 559 | +        r3 = self.mk([healthy, ds], ["heimdall:deepseek2", "heimdall:deepseek"])
 560 | +        self.assertEqual(r3.call("check", "z", 100, 7).backend, "heimdall:deepseek2")
 561 | +        self.assertEqual(r3.breaker_events, [])  # 1500 of a 1000 cap: no runaway (15x the caller's 100 would be one)
 562 | +
 563 | +    def test_a_late_answer_that_ran_away_opens_it(self):
 564 | +        glm = Slow(GLM, "heimdall", '{"ok": 1}', delay=0.3, family="glm", usage={"in": 10, "out": 5000})
 565 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 566 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 567 | +        self.assertEqual(r.call("check", "p", 100, 7, deadline_s=0.1).backend, "heimdall:deepseek")   # one miss
 568 | +        log = wait_for(self.log, "breaker_open")                          # its late answer: 5000 > 2 x 100
 569 | +        self.assertEqual([x["why"] for x in log if x["kind"] == "breaker_open"],
 570 | +                         ["returned more than 2x the cap it was sent"])
 571 | +        self.assertFalse(CB.allow(GLM, self.state)[0])
 572 | +
 573 | +    def test_replay_never_consults_it_and_an_unreadable_state_skips_nothing(self):
 574 | +        glm = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm")
 575 | +        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
 576 | +        CB.record(GLM, "runaway", self.state)                             # open now
 577 | +        rr = self.mk([glm, ds], [GLM, "heimdall:deepseek"], replay=True)
 578 | +        self.assertIsNone(rr._breaker_allow("check", GLM))                # replay walks its recordings only
 579 | +        with open(self.state, "w") as f:
 580 | +            f.write("{ broken")
 581 | +        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 582 | +        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # never a skip by guess
 583 | +        self.assertTrue(any("RULING 99" in n for n in r.notices))
 584 | +        no = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
 585 | +        no.breakers = None                                                # a router given no state: no breaker
 586 | +        self.assertIsNone(no._breaker_allow("check", GLM))
 587 | +
 588 | +
 589 | +class TestTheBuildUsesIt(unittest.TestCase):
 590 | +    def test_the_build_router_has_the_breaker_and_the_health(self):
 591 | +        """The ledger build's one router (proof_ledger.build_router) is given ruling 99's state and ruling 87's."""
 592 | +        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
 593 | +        import heimdall_health as HH
 594 | +        import proof_ledger as PLG
 595 | +        with tempfile.TemporaryDirectory() as d:
 596 | +            r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
 597 | +        self.assertEqual((r.breakers, r.health, r.routing), (CB.STATE, HH.STATE, "heimdall_first"))
 598 | +        self.assertEqual(os.path.basename(CB.STATE), "BREAKERS.json")
 599 | +
 600 | +
 601 | +if __name__ == "__main__":
 602 | +    unittest.main()
 603 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff and the facts below; if uncertain, say so; do not guess. Be specific: file:line and a concrete
sequence of calls that breaks it.

BACKGROUND (static):
- providers.Router.call(role, prompt, max_tokens, ...) walks a role's chain of model back-ends in order. For each leg
  it first serves a RECORDED reply when one exists on disk (no paid call), else (in replay mode) moves on, else makes a
  live paid call under a deadline (Heimdall gateway legs: 120 s). A leg that misses its deadline is abandoned and the
  chain moves on; a leg that answers decides. Ruling 87's shared health file and its probe thread (probe roles
  "probe87:<model>") are a SEPARATE mechanism about Heimdall as a whole; ruling 86's shadow calls (roles
  "shadow86:<role>") ask Grok the same prompt and never decide.
- Before this change, a deadline miss did not stop the Router from asking the same model again on the next call: glm
  missed every call's 120 s deadline at 09:55 ET, so every glm-first verdict burned 120 s before deepseek or Grok.

UNCHANGED CODE THIS CHANGE RELIES ON (not in the diff; verify against these facts, do not assume them away):
- providers.py:1211 serves a recorded reply before anything else; :1219 `if self.replay: ... continue` (replay never
  makes a live call). The new breaker check (:1222) sits AFTER both, so it only ever gates a live paid call.
- providers._within (:345) raises DeadlineExceeded (class at :340) when the deadline passes; the abandoned call keeps
  running in its own thread and, if it ends, calls Router._late (:934) with (text, usage, seconds) or an error.
- Router._log_slow (:850) appends one JSON line to the evidence file (deadline_log) and does nothing when no path is
  set; a write failure becomes a notice, never an exception.
- Backend.max_out(max_tokens) is the output cap a call actually SENDS: base back-ends max(spec min_out, max_tokens)
  (:177), xAI text max(min_out or 8000, 8 x max_tokens) (:443), xAI vision max(..., 4 x max_tokens) (:531).
  model_providers.json gives every Heimdall family min_out 16,000. Usage "out" is the vendor's completion count, with
  reasoning tokens included (xAI's backend adds them explicitly).
- tests/package/proof_ledger.py builds the ONE production Router of a ledger build; the exam's adapter
  (moments_gate_adapter.make_router) builds its own Router with no breaker (its replay must stay deterministic).

THE ORCHESTRATOR'S RULING (10:48 ET Nov 14), verbatim:
"RULING 99, THE CIRCUIT BREAKER. A model that misses its deadline TWICE in a row, or returns more than twice its
max_tokens (a runaway: glm gave 16,000 tokens against 4,000, and 10,455 for a one-word probe), is SKIPPED by every list
for 30 minutes; the next family leads. After 30 minutes one real call may try it again; a miss re-opens the breaker for
60. Every open / close is one line in the Heimdall evidence file (model, deadline, seconds, tokens) and the count goes
on STATE line 1. A breaker is not an outage: ruling 87's clock is about NO family answering. While glm's breaker is
open, step A's Heimdall filter is deepseek, the hook rating is qwen -> deepseek, fidelity is qwen -> Grok, exclusion
is deepseek -> Grok. This is why Grok served 24 of 27 step A verdicts at 09:55 after each burned 120 s: fix that first,
it is costing every build minutes and dollars."
FACT, measured and put to the orchestrator on STATE line 1 (10:45): glm was SENT a 16,000-token cap (its min_out), not
4,000; its 16,000 tokens were 1.00x that cap and the probe's 10,455 were 0.65x. On 1,252 recorded answers no model
exceeds 1x the cap it was sent; against the CALLER's max_tokens, 309 of 676 healthy Grok answers and 61 of 127 deepseek
answers exceed 2x. So this change reads "its max_tokens" as the cap actually sent (Backend.max_out). The heimdall_first
lists minus glm are exactly the chains the ruling names (step A first: deepseek, Grok; hook: qwen, deepseek, Grok;
fidelity: qwen, Grok; exclusion: deepseek, Grok).

THE CHANGE (the diff follows):
1. pipeline/circuit_breaker.py (new): a JSON state file under an flock (tests/package/proof/BREAKERS.json), shared by the
   builder's processes. allow(name) -> (True, None) closed; (True, "trial") the ONE call after the open window, claimed
   under the lock; (False, why) open, or a trial in flight (a trial whose caller never reports is freed after 15
   minutes). record(name, "answer" | "miss" | "runaway"): closed: 2 misses in a row (an answer resets the count) or one
   runaway open it for 30 minutes; open, inside the window: ignored (calls in flight from before it opened); after the
   window: an answer closes it, a miss or a runaway re-opens it for 60 minutes. Each open / close is returned as an
   event with model, why, deadline_s, seconds, tokens, max_out, until, utc. summary() gives the open breakers and the
   opens / closes in the last 24 h. An unreadable file raises BreakerUnreadable; a malformed record skips nothing.
2. pipeline/providers.py: Router(breakers=path). Live calls only (never replay, probe87: or shadow86: roles):
   _breaker_allow before the paid call skips an open model (the next leg leads); a deadline miss records "miss"; an
   answer records "runaway" when its output exceeds 2x the cap sent, else "answer"; a LATE answer (in _late) that ran
   past 2x the cap records "runaway". Each event goes to the evidence file (_log_slow) and router.breaker_events. An
   unreadable breaker state skips nothing (a notice): the breaker saves minutes, it never stops a verdict.
3. tests/package/proof_ledger.py: the build's Router is made by build_router() (the same arguments as before, plus
   breakers=circuit_breaker.STATE), and the build log and record carry the count for STATE line 1.
4. Tests: tests/providers/test_circuit_breaker.py (new, 10 tests, real deadline misses through _within). 17 mutations,
   each killed. 21 suites, 578 tests pass.

ATTACK:
(a) Can glm burn its deadline more than twice in a row, across threads or across build processes, once this is live?
    Can the breaker skip a model that is healthy (Grok or deepseek reasoning inside their caps)?
(b) The trial: can two calls both be the trial? Can a trial claim be lost so the model is never tried again? Can a
    call that started before the open re-open or extend it?
(c) Can an open breaker ever leave a verdict with NO leg (fail closed is acceptable; a wrong verdict is not)? Can it
    change which RECORDED reply a replay serves?
(d) Concurrency: two processes and eight threads on one state file; the lock; the atomic write.
(e) Anything that could make a build slower or costlier than before, or break pp-ingest (which never loads this file).

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete sequence), then
"SHIP: yes / no / yes with conditions".


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
