### The order (ruling 87, orchestrator 21:18 Nov 13, to the builder; relayed, abridged by the builder)
"... When down: switch the whole pin stage to PLAN B at once: Grok mainly, then any other outside key that answers ...
The same switch covers the miner and the writer: tell pp-ingest the contract so the watcher uses the same 'down'
signal (its outage drill already exists). Plan B's spend counts on the same ledger and the same cap ..."
Standing for this watcher: the SPEND FREEZE (orchestrator 05:30 ET Nov 12, "until told otherwise"): paid frontier
vendors are never called; the watcher's chain is Heimdall then local; if both are down the videos queue and are mined
later. The miner's Plan B question (paid models, or queue and wait) is the orchestrator's and open: until answered the
miner's Plan B is QUEUE AND WAIT (nothing in this change alters what the miner calls).

### The builder's contract (pp-selectid, verbatim, 01:5x Nov 14)
RULING 87's shared "Heimdall down" signal is committed: pp-selectid 125e7381, pipeline/heimdall_health.py (audited 2
cycles, 0108). The contract for your watcher:
- STATE FILE: tests/package/proof/HEIMDALL_HEALTH.json in my worktree, read and written only under its flock
  (heimdall_health._Locked). An unreadable file raises HealthUnreadable and is never guessed.
- API (import my module from the worktree, the way the integrator imports package_pin):
  - note(answered, path=..., evidence=..., state_md=..., who="pp-ingest", drill=False). Call it after each Heimdall
    verdict or writer call: answered=True if it answered inside its deadline; False if it was down, refused, empty or
    late. drill=True records your outage drill without counting it.
  - mode(path=...) gives "heimdall_first" or "plan_b".
  - probe_due(path=...) and probe_result(answered, path=...) are for the 2-minute probe while failing or in Plan B.
- THE RULE: "down" is 15 minutes with no Heimdall family answering. One family down is not "down"; that is ruling 82's
  chain. It comes back after 3 probe answers in a row.
- Every switch goes to the state, the evidence file, and STATE line 1 (capitals, the time).
- The miner's Plan B question (paid models, or queue and wait) is still the orchestrator's: STATE carries it since 21:45.

### The builder's module (read only for this session; NOT under review; its API is what the change must use right)
File: /home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py (pp-selectid 125e7381)
```python
"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE. One shared 'Heimdall down' signal for the builder
(verdicts and writes) and pp-ingest's watcher (the miner), kept in ONE JSON state file under an flock.

- Heimdall is DOWN when NO Heimdall family answers a verdict or writer call inside its deadline for DOWN_AFTER_S (15
  minutes) running: note(False) starts the clock (failing_since), any note(True) stops it. One model down is not
  'down': that is ruling 82's chain, and any family's answer stops the clock.
- While calls are failing, and while in Plan B, a cheap probe (probe_due / probe_result) runs every PROBE_EVERY_S
  (2 minutes).
- Down: the mode is "plan_b" at once (the whole pin stage: Grok mainly, then any other outside key that answers).
  BACK: "heimdall_first" when the probe has answered BACK_AFTER (3) times in a row.
- Every switch is recorded three times: in the state's "switches"; as a line {"kind": "switch", ...} in the
  Heimdall evidence file (item 55); and, IN CAPITALS with the time, at the start of the caller's STATE line 1 (one
  physical line).

The state file: {"mode": "heimdall_first" | "plan_b", "last_answer_utc", "failing_since_utc", "last_probe_utc",
"probe_streak", "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
'up' or 'down' by guess: note() / mode() raise HealthUnreadable (fail closed: the caller decides, and says so).
CPU only; no model call here (the caller makes the probe call and reports it)."""
import fcntl
import threading
import json
import os
import time
from datetime import datetime, timezone

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
                     "HEIMDALL_HEALTH.json")
DOWN_AFTER_S = 15 * 60                  # ruling 87: no family answering for 15 minutes running
PROBE_EVERY_S = 2 * 60                  # ruling 87: a cheap probe every 2 minutes while calls fail (and in Plan B)
BACK_AFTER = 3                          # ruling 87: back to Heimdall-first after 3 probe answers in a row
HEARTBEAT_S = 30.0                      # an answer is written at most once per 30 s per process while all is well
_SEEN = {}                              # path -> monotonic time of this process's last written answer (no failure since)
_SEEN_LOCK = threading.Lock()           # the probe thread and the build's threads share _SEEN (audit 0108 C1, qwen)
MODES = ("heimdall_first", "plan_b")


class HealthUnreadable(Exception):
    """The state file exists but cannot be read: no guess either way (law L-j)."""


def _now(now=None):
    return now if now is not None else datetime.now(timezone.utc)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _t(s):
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo is not None else None


def _load(path):
    if not os.path.exists(path):
        return {"mode": "heimdall_first", "last_answer_utc": None, "failing_since_utc": None, "last_probe_utc": None,
                "probe_streak": 0, "switches": [], "notes": 0}
    try:
        with open(path) as f:
            s = json.load(f)
        if not isinstance(s, dict) or s.get("mode") not in MODES:
            raise ValueError("not a health state")
        return s
    except (OSError, ValueError) as e:
        raise HealthUnreadable(f"{path}: {type(e).__name__}: {e}") from None


def _save(path, s):
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        json.dump(s, f, indent=1)
    os.replace(tmp, path)


class _Locked:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        self.f = open(self.path + ".lock", "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()
        return False


def _switch(s, to, why, now, evidence=None, state_md=None, who=""):
    """Record one switch: the state, the evidence file, STATE line 1 (capitals, the time, one physical line)."""
    rec = {"utc": _iso(now), "to": to, "why": why, "by": who}
    s["mode"] = to
    s.setdefault("switches", []).append(rec)
    if evidence:
        try:
            with open(evidence, "a") as f:
                f.write(json.dumps(dict(rec, kind="switch")) + "\n")
        except OSError:
            pass                                # evidence, never a gate (the state file holds the switch)
    if state_md:
        local = now.astimezone().strftime("%H:%M")
        word = "SWITCHED TO PLAN B" if to == "plan_b" else "BACK TO HEIMDALL-FIRST"
        _prepend(state_md, f"{local} ET: {word} ({why.upper()}) |")   # the state and evidence files hold it too


def announce(state_md, text, now=None):
    """RULING 87: a Plan B fact the orchestrator must see, in capitals with the time, prepended to STATE line 1 (one
    physical line). A file that cannot be written is left as it is (the build log carries the fact too)."""
    now = _now(now)
    _prepend(state_md, f"{now.astimezone().strftime('%H:%M')} ET: {text.upper()} |")


def _prepend(state_md, head):
    """Prepend `head` to STATE line 1 (one physical line) under the file's own lock, so a switch (the probe's thread)
    and an announcement (the build's) never lose each other's head (audit 0108 C1, glm). A file that cannot be written
    is left as it is."""
    try:
        with _Locked(state_md):
            with open(state_md) as f:
                lines = f.read().split("\n")
            lines[0] = f"{head} {lines[0]}" if lines and lines[0] else head
            tmp = f"{state_md}.{os.getpid()}.{threading.get_ident()}.tmp"
            with open(tmp, "w") as f:
                f.write("\n".join(lines))
            os.replace(tmp, state_md)
    except OSError:
        pass


def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False):
    """One Heimdall verdict or writer call's outcome: answered inside its deadline (True), or not (False: down,
    refused, empty, past the deadline). -> the mode after it. 15 minutes of failures with no answer: plan_b.
    drill=True (pp-ingest's outage drill, 21:4x Nov 13): recorded (drills, last_drill_utc), never counted.
    An answer while all is well is written at most once per HEARTBEAT_S per process (a failure is always written)."""
    import time as _time
    now, mono = _now(now), _time.monotonic()
    with _SEEN_LOCK:
        if answered and not drill and mono - _SEEN.get(path, -1e9) < HEARTBEAT_S:
            return "heimdall_first" if _SEEN.get(path + "#mode") != "plan_b" else "plan_b"
    with _Locked(path):
        s = _load(path)
        if drill:
            s["drills"], s["last_drill_utc"] = int(s.get("drills") or 0) + 1, _iso(now)
            _save(path, s)
            return s["mode"]
        s["notes"] = int(s.get("notes") or 0) + 1
        if answered:
            s["last_answer_utc"], s["failing_since_utc"] = _iso(now), None
        elif not s.get("failing_since_utc"):
            s["failing_since_utc"] = _iso(now)
        _down_rule(s, now, evidence, state_md, who)
        _save(path, s)
        with _SEEN_LOCK:
            if answered:
                _SEEN[path], _SEEN[path + "#mode"] = mono, s["mode"]
            else:
                _SEEN.pop(path, None)
        return s["mode"]


def _down_rule(s, now, evidence, state_md, who):
    fs = _t(s.get("failing_since_utc"))
    if s["mode"] == "heimdall_first" and fs is not None and (now - fs).total_seconds() >= DOWN_AFTER_S:
        _switch(s, "plan_b", f"no Heimdall family answered inside its deadline for "
                             f"{int((now - fs).total_seconds() // 60)} minutes (since {_iso(fs)})", now, evidence,
                state_md, who)
        s["probe_streak"] = 0


def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches). -> mode."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        before = s["mode"]
        _down_rule(s, now, evidence, state_md, who)
        if s["mode"] != before:
            _save(path, s)
        return s["mode"]


def probe_due(path=STATE, now=None):
    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
            return False
        lp = _t(s.get("last_probe_utc"))
        return lp is None or (now - lp).total_seconds() >= PROBE_EVERY_S


def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
    """A probe's outcome (any Heimdall family answering it counts). BACK_AFTER answers in a row while in plan_b:
    back to heimdall_first (the failure clock cleared). While not yet down, a probe answer is no verdict answer: the
    15-minute clock runs on (the ruling counts verdict and writer calls). -> the mode after it."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        s["last_probe_utc"] = _iso(now)
        s["probe_streak"] = int(s.get("probe_streak") or 0) + 1 if answered else 0
        if s["mode"] == "plan_b" and s["probe_streak"] >= BACK_AFTER:
            _switch(s, "heimdall_first", f"the probe answered {s['probe_streak']} times in a row", now, evidence,
                    state_md, who)
            s["failing_since_utc"], s["probe_streak"] = None, 0
        _save(path, s)
        return s["mode"]
```

### The change under review (diff since ca17cb97)
- pipeline/ingest/downsignal.py (NEW): DownSignal. noted(rec) from Service._on_attempt (the router's threads): O(1),
  never the shared file: a real call to a back-end of providers.json down_signal.vendor is an outcome (ok/invalid =
  answered; every other kind of a real call = not answered); no outcome for kind cache / disabled (no call was made),
  for the probe role, for another vendor; a back-end with a base_url override in overrides.json (the outage drill) is a
  drill. Pending outcomes are compressed under a local lock: the latest answer and the first failure after it, each
  with its own time. tick() (the service's new "signal" loop, every 5 s; the ONLY caller of the module in the process):
  flush (note(drill=True) once if any drill; note(True, now=answer time); note(False, now=failure time)); every 30 s
  mode() (the 15-minute rule on the clock) and, unless a probe back-end is under an override, probe_due() -> the probe
  role asked in its own thread (router.run use_cache=False; "Reply with the single word OK."; any text is an answer; a
  probe whose back-ends were all skipped is no probe: no probe_result); the probe's outcome goes to probe_result() at
  the next tick; _seen(): reads the state file's "switches" (written atomically by the module) and, for each switch
  not yet seen (the count kept in the queue's kv; first sight records the count without announcing history), writes
  the head to this watcher's STATE line 1 (spend.write_switch_head), a "seen" line to the evidence file, an event, a
  log line. Unreadable state / module missing / a call stuck on the lock: never read as up or down (snapshot mode None);
  STATE notice after 30 min (check_notice, from the health loop, which never touches the shared file).
- pipeline/ingest/providers.py: a role may set "breaker": false (its calls skip the circuit's allow() and never
  record() into it: the probe is the breaker's evidence, not its patient) and "transport_retries" (overrides the global
  count); validate_config checks both and down_signal (vendor, label, module, a probe_role whose back-ends are all of
  that vendor: a local or outside answer is no answer of that vendor).
- pipeline/ingest/providers.json: back-ends heimdall_qwen27b_probe / heimdall_glm53flash_probe (the same models as the
  live ones, timeout 60 s = the builder's probe deadline, one in flight, metered); role "probe" (attempts 1,
  max_tokens 512, transport_retries 0, breaker false); "down_signal" {vendor, probe_role, label, module}.
- pipeline/ingest/spend.py: write_switch_head (prepends the head to the ONE physical line of switches, newest first;
  that line is kept FIRST in the notice block whatever other notice comes or goes); write_signal_notice;
  NOTICE_RE/SWITCH_RE extended (no vendor name in code: law L-x).
- pipeline/ingest/service.py: the signal loop (only when providers.json has down_signal), noted() first in
  _on_attempt, check_notice + the snapshot in the health loop, the start log line. stats.py: live.json "down_signal".
- pipeline/ingest/config.py: paths()["signal"] (this watcher's evidence file, down_signal.jsonl in the store).
- tests/ingest/test_signal.py (15 tests; the builder's real module on a throw-away state file).

### Decisions (assumptions A22-A26 in STATE)
- A22: the module gets state_md=None. Its _prepend would leave pp-ingest_STATE.md.lock beside STATE.md (an untracked
  file in this repo), write line 1 under a lock our notice writers do not take (a lost update between them), and merge
  its head into a notice line so NOTICE_RE no longer finds that notice (a notice never removed). Instead EVERY switch in
  the shared state, whoever made it (the "by" field), goes to this watcher's STATE line 1 in the module's words plus
  "BY <who>" and the miner's Plan B; the module still writes its own switch record to our evidence file when we trip it.
- A23: answered = ok or invalid (the gateway answered inside the back-end's deadline: our timeouts are the deadlines);
  every other kind of a real call = not answered (timeout, network, server, empty, refusal, http_429, overloaded,
  routing, redirect, http_auth, http_4xx), as the contract says ("down, refused, empty or late").
- A24: one thread owns the module so a held or stuck shared lock never stalls the miner's threads.
- A25: dedicated probe back-ends (a 60 s deadline without changing the back-end interface; own breaker/throttle),
  breaker-free, first answer ends the probe (any family answering counts).
- A26: drill = a base_url override present for that back-end (whether or not the router honours it: a real call
  wrongly marked drill only loses evidence, never flips the fleet's signal).

### Questions for the reviewers (answer with file:line)
1. Ordering: a pending answer flushed up to ~5 s late with its own (earlier) time can clear a failure the builder's
   process noted in between. Is that a real defect given the module's own heartbeat (an answer written at most every
   30 s per process) and the 15-minute rule?
2. Two processes probing: both may see probe_due True at once and both report probe_result, so 3 "answers in a row"
   can come from 2 rounds. Our side or the module's? (probe_due does not claim the probe.)
3. Is http_4xx (e.g. a 400 for this watcher's own bad request) right to count as "not answered"?
4. Any path where the signal changes what the miner calls, blocks a mining thread, or raises into the router?
5. _seen(): the kv count across restarts and a replaced state file; a STATE write failure (the count stays; retried).
6. Thread safety of DownSignal (pending under its lock; module calls only in the signal thread; the health thread
   reads attributes and writes the STATE notice).
7. The probe back-ends share the key and the gateway with the miner: any way a probe can starve or be starved?
