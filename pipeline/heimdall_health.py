"""RULING 87 (orchestrator 21:18 Nov 13): PLAN B, THE FAIL-SAFE. One shared 'Heimdall down' signal for the builder
(verdicts and writes) and pp-ingest's watcher (the miner), kept in ONE JSON state file under an flock.

- RULING 87 AMENDED (orchestrator 10:06 Nov 14, after the false outage of 09:16-09:22: one 502 on a calibration call,
  then silence, and the clock ran while every probe was answering): Heimdall is DOWN when there is NO SUCCESSFUL
  ANSWER OF ANY KIND for DOWN_AFTER_S (15 minutes) running. note(False) starts the clock (failing_since); an answered
  call (note(True)) OR an answered probe (probe_result(True) while heimdall_first) resets it to zero. One model down is
  not 'down': that is ruling 82's chain, and any family's answer resets the clock.
- While the clock runs, and while in Plan B, the probe (probe_due / probe_result) goes every PROBE_EVERY_S (2
  minutes), so one failed call followed by one good probe is never 'down'. A probe is a REAL model call on the family
  that failed and one other, never a ping (the caller makes it: providers.Router.probe_once asks each of its Heimdall
  families). note(False, family=...) records the failed family (failing_families, cleared by any answer); while the
  clock runs, a prober that names its families (probe_due(families=...)) and can ask none of the failed ones leaves
  the slot to the prober that can (the builder and pp-ingest call different families). In plan_b any prober claims.
- Down: the mode is "plan_b" at once (the whole pin stage: Grok mainly, then any other outside key that answers).
  BACK: "heimdall_first" when the probe has answered BACK_AFTER (3) times in a row.
- Every switch is recorded three times: in the state's "switches"; as a line {"kind": "switch", ...} in the
  Heimdall evidence file (item 55); and, IN CAPITALS with the time, at the start of the caller's STATE line 1 (one
  physical line).

The state file: {"mode": "heimdall_first" | "plan_b", "last_answer_utc", "failing_since_utc", "last_probe_utc",
"probe_streak", "failing_families": [...], "switches": [{"utc", "to", "why"}], "notes": n}. Times are ISO UTC. An unreadable state file is never
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


def note(answered, path=STATE, now=None, evidence=None, state_md=None, who="", drill=False, family=None):
    """One Heimdall verdict or writer call's outcome: answered inside its deadline (True), or not (False: down,
    refused, empty, past the deadline). -> the mode after it. 15 minutes of failures with no answer: plan_b.
    drill=True (pp-ingest's outage drill, 21:4x Nov 13): recorded (drills, last_drill_utc), never counted.
    family: the Heimdall family the call went to; a failure records it in failing_families (ruling 87 amended).
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
            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
        else:
            if not s.get("failing_since_utc"):
                s["failing_since_utc"], s["failing_families"] = _iso(now), []
            if family:
                s["failing_families"] = sorted(set(_families(s)) | {str(family)})
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
        _switch(s, "plan_b", f"no answer of any kind (no call and no probe answered) for "
                             f"{int((now - fs).total_seconds() // 60)} minutes (since {_iso(fs)})", now, evidence,
                state_md, who)
        s["probe_streak"] = 0


def mode(path=STATE, now=None, evidence=None, state_md=None, who=""):
    """The mode now (the 15-minute rule applied on the clock too, so an idle build still switches: no call and no
    probe answered for 15 minutes; the probe goes every 2 minutes while the clock runs). -> mode."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        before = s["mode"]
        _down_rule(s, now, evidence, state_md, who)
        if s["mode"] != before:
            _save(path, s)
        return s["mode"]


def _families(s):
    """The failed families on the running clock (a malformed field reads as none: no prober is kept out by it)."""
    f = s.get("failing_families")
    return [x for x in f if isinstance(x, str)] if isinstance(f, list) else []


def probe_due(path=STATE, now=None, who="", families=None):
    """True when a probe is due: calls are failing (or the mode is plan_b) and the last probe is PROBE_EVERY_S old.
    A True CLAIMS the slot (last_probe_utc and last_probe_by stamped under the lock), so with several probers (this
    builder's router, pp-ingest's watcher) there is ONE probe per PROBE_EVERY_S slot, and "BACK_AFTER answers in a
    row" means that many slots (pp-ingest REQUESTS R12, 02:3x ET Nov 14). The next probe is due PROBE_EVERY_S after the
    later stamp: probe_result re-stamps last_probe_utc when the probe reports (answer-anchored), and a claimer that
    never reports leaves the slot spent from its claim (claim-anchored) (audit 0230 C1, glm). who names the claimer
    (pp-ingest's watcher passes it from its next restart; "" until then). RULING 87 AMENDED (10:06 Nov 14): a probe is a
    real model call on the family that failed: while the clock runs in heimdall_first, a prober whose `families` include
    none of failing_families does not claim (the prober that can ask them does); families=None claims as before."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        if s["mode"] != "plan_b" and not s.get("failing_since_utc"):
            return False
        failed = set(_families(s))
        if families is not None and s["mode"] != "plan_b" and failed and not failed & set(families):
            return False
        lp = _t(s.get("last_probe_utc"))
        if lp is not None and (now - lp).total_seconds() < PROBE_EVERY_S:
            return False
        s["last_probe_utc"], s["last_probe_by"] = _iso(now), who
        _save(path, s)
        return True


def probe_result(answered, path=STATE, now=None, evidence=None, state_md=None, who=""):
    """A probe's outcome (any Heimdall family answering it counts). RULING 87 AMENDED (10:06 Nov 14): an answered probe
    is an answer like an answered call, in both modes: it resets the clock (failing_since_utc, failing_families) and
    stamps last_answer_utc (pp-ingest's ruling-98 route reads the clock as "no answer of any kind"). A probe answer
    timed before the failure that started the clock (a report that arrives late) does not reset that clock; it still
    counts in probe_streak (plan_b's question is whether the last probes answered, the clock's is whether anything
    answered since the failure) (audit 1008 C2). A failed probe never starts the clock (note(False) does). plan_b
    closes on BACK_AFTER answers in a row, as before.
    -> the mode after it."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        s["last_probe_utc"] = _iso(now)
        s["probe_streak"] = int(s.get("probe_streak") or 0) + 1 if answered else 0
        fs = _t(s.get("failing_since_utc"))
        if answered and (fs is None or now >= fs):     # not a late report from before the clock started
            s["last_answer_utc"], s["failing_since_utc"], s["failing_families"] = _iso(now), None, []
        if s["mode"] == "plan_b" and s["probe_streak"] >= BACK_AFTER:
            _switch(s, "heimdall_first", f"the probe answered {s['probe_streak']} times in a row", now, evidence,
                    state_md, who)
            s["failing_since_utc"], s["failing_families"], s["probe_streak"] = None, [], 0
        _save(path, s)
        return s["mode"]
