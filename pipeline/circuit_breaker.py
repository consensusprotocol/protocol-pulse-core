"""RULING 99 (orchestrator 10:48 ET Nov 14), THE CIRCUIT BREAKER. A model that misses its deadline MISSES_TO_OPEN (2)
times in a row, or returns more than RUNAWAY_X (2) times its max_tokens, is SKIPPED by every list for OPEN_S (30
minutes): the next family leads. After that, ONE real call may try it again (the trial, claimed under the lock); an
answer closes the breaker, a miss or a runaway re-opens it for REOPEN_S (60 minutes). Every open and close is one line
in the Heimdall evidence file (model, deadline, seconds, tokens: the caller logs the event this module returns); the
count goes on STATE line 1 (summary()).

- "Its max_tokens" is the cap the call actually SENT (providers.Backend.max_out: every Heimdall family is sent its
  min_out floor of 16,000, Grok 8 x max_tokens, since a reasoning model thinks inside it). Measured on 1,252 recorded
  answers (10:4x ET Nov 14): none exceeds 1x that cap; against the CALLER's max_tokens, 309 of 676 healthy Grok answers
  and 61 of 127 deepseek answers would read as runaways. Asked of the orchestrator on STATE line 1.
- A breaker is not an outage (ruling 87's clock is about NO family answering); it lives in its own state file.
- While a breaker is open, an outcome of a call that was in flight before it opened changes nothing and is no event
  (a late runaway's tokens are still on record: its late_answer line in the evidence file).
- Only LIVE calls touch it: a recorded reply is served as before, replay never consults it, and probes (ruling 87) and
  shadow calls (ruling 86) neither count nor skip (the caller decides; providers.Router._breaker_live).
- The state file: {"models": {name: {"misses", "open_until", "trial_at", "trial_until", "opens", "why"}},
  "events": [the last EVENTS_KEPT opens and closes]} under tests/package/proof, beside ruling 87's HEIMDALL_HEALTH.json. Times are ISO UTC. An unreadable file raises BreakerUnreadable: the caller says so and
  skips nothing by it (an optimisation never stops a verdict; ruling 82's chain still fails over call by call)."""
import fcntl
import json
import os
from datetime import datetime, timedelta, timezone

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "package", "proof",
                     "BREAKERS.json")
MISSES_TO_OPEN = 2                      # ruling 99: two deadline misses in a row
OPEN_S = 30 * 60                        # ruling 99: skipped by every list for 30 minutes
REOPEN_S = 60 * 60                      # ruling 99: a failed trial re-opens it for 60
RUNAWAY_X = 2.0                         # ruling 99: more than twice its max_tokens (the cap sent)
TRIAL_HOLD_S = 15 * 60                  # a trial whose call never reports (its process ended) is freed after its OWN
#   deadline + 60 s (allow(hold_s=...), the Router passes it), so one trial at a time even on the local judge's 2400 s,
#   and a dead trial does not hold the model long (audit 1057 C1: grok, glm); this default is for a leg with no deadline
EVENTS_KEPT = 5000                      # enough for every open and close of a day (summary counts the last 24 h)


class BreakerUnreadable(Exception):
    """The state file exists but cannot be read: no guess either way."""


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
        return {"models": {}, "events": []}
    try:
        with open(path) as f:
            s = json.load(f)
        if not isinstance(s, dict) or not isinstance(s.get("models"), dict):
            raise ValueError("not a breaker state")
        return s
    except (OSError, ValueError) as e:
        raise BreakerUnreadable(f"{path}: {type(e).__name__}: {e}") from None


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


def allow(name, path=STATE, now=None, hold_s=None):
    """May a live call go to `name` now? -> (True, None) closed; (True, "trial") the one call after the open window
    (claimed here, under the lock, until now + hold_s: the call's own deadline + 60 s, else TRIAL_HOLD_S); (False, why)
    open, or a trial already in flight. A malformed record skips nothing."""
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        m = s["models"].get(name)
        until = _t(m.get("open_until")) if isinstance(m, dict) else None
        if until is None:
            return True, None
        if now < until:
            return False, f"circuit breaker open until {m['open_until']} (ruling 99: {m.get('why')})"
        ta, tu = _t(m.get("trial_at")), _t(m.get("trial_until"))
        if ta is not None and now < (tu or ta + timedelta(seconds=TRIAL_HOLD_S)):
            return False, f"circuit breaker: its one trial call is in flight since {m['trial_at']} (ruling 99)"
        hold = float(hold_s) if isinstance(hold_s, (int, float)) and hold_s > 0 else TRIAL_HOLD_S
        m["trial_at"], m["trial_until"] = _iso(now), _iso(now + timedelta(seconds=hold))
        _save(path, s)
        return True, "trial"


def is_open(name, path=STATE, now=None):
    """READ ONLY (it never claims a trial): would allow() skip `name` now? Its window open, or its one trial in flight.
    RULING 101's estimate of the filter's wait reads it. An unreadable state skips nothing: False."""
    now = _now(now)
    try:
        with _Locked(path):
            s = _load(path)
    except (BreakerUnreadable, OSError):
        return False
    m = s["models"].get(name)
    until = _t(m.get("open_until")) if isinstance(m, dict) else None
    if until is None:
        return False
    if now < until:
        return True
    ta, tu = _t(m.get("trial_at")), _t(m.get("trial_until"))
    return ta is not None and now < (tu or ta + timedelta(seconds=TRIAL_HOLD_S))


def record(name, outcome, path=STATE, now=None, deadline_s=None, seconds=None, tokens=None, max_out=None):
    """One live call's outcome: "answer", "miss" (its deadline passed) or "runaway" (more than RUNAWAY_X times the cap
    it was sent). -> the event for the evidence file ({"kind": "breaker_open" | "breaker_close", "model", "why",
    "deadline_s", "seconds", "tokens", "max_out", "until", "utc"}) or None."""
    if outcome not in ("answer", "miss", "runaway"):
        raise ValueError(f"outcome must be answer, miss or runaway, not {outcome!r}")
    now = _now(now)
    with _Locked(path):
        s = _load(path)
        m = s["models"].get(name)
        if not isinstance(m, dict):
            m = s["models"][name] = {"misses": 0, "open_until": None, "trial_at": None, "opens": 0}
        until = _t(m.get("open_until"))
        detail = {"model": name, "deadline_s": deadline_s, "seconds": seconds, "tokens": tokens, "max_out": max_out}
        ev = None
        if outcome == "answer":
            m["misses"] = 0
            if until is not None and now >= until:            # the trial (a call after the window) answered
                m["open_until"], m["trial_at"], m["trial_until"] = None, None, None
                ev = dict(detail, kind="breaker_close", why="the trial call answered")
        elif until is not None and now >= until:              # the trial failed: open again, for longer
            m["why"] = "the trial call " + ("missed its deadline" if outcome == "miss" else
                                            f"returned more than {RUNAWAY_X:g}x the cap it was sent")
            m["open_until"], m["trial_at"], m["trial_until"] = _iso(now + timedelta(seconds=REOPEN_S)), None, None
            m["misses"] = 0                                   # as on every open (audit 1057 C2, glm: no latent count)
            m["opens"] = int(m.get("opens") or 0) + 1
            ev = dict(detail, kind="breaker_open", why=m["why"], until=m["open_until"])
        elif until is None:                                   # closed (while open, a call from before it is ignored)
            m["misses"] = int(m.get("misses") or 0) + (1 if outcome == "miss" else 0)
            if outcome == "runaway" or m["misses"] >= MISSES_TO_OPEN:
                m["why"] = (f"returned more than {RUNAWAY_X:g}x the cap it was sent" if outcome == "runaway" else
                            f"missed its deadline {MISSES_TO_OPEN} times in a row")
                m["open_until"], m["trial_at"], m["trial_until"], m["misses"] = \
                    _iso(now + timedelta(seconds=OPEN_S)), None, None, 0
                m["opens"] = int(m.get("opens") or 0) + 1
                ev = dict(detail, kind="breaker_open", why=m["why"], until=m["open_until"])
        if ev:
            ev["utc"] = _iso(now)
            s["events"] = (list(s.get("events") or []) + [ev])[-EVENTS_KEPT:]
        _save(path, s)
        return ev


def summary(path=STATE, now=None, since=None):
    """For STATE line 1 (ruling 99: "the count goes on STATE line 1"): the breakers open now and the opens / closes
    since `since` (an aware datetime; default: the last 24 hours). -> {"open": [...], "opens": n, "closes": n}."""
    now = _now(now)
    since = since or now - timedelta(hours=24)
    with _Locked(path):
        s = _load(path)
    open_now = [{"model": n, "until": m.get("open_until"), "why": m.get("why")}
                for n, m in sorted(s["models"].items()) if isinstance(m, dict) and _t(m.get("open_until")) is not None
                and now < _t(m.get("open_until"))]
    evs = [e for e in s.get("events") or [] if isinstance(e, dict) and _t(e.get("utc")) is not None
           and _t(e.get("utc")) >= since]               # an event whose time cannot be read is not counted (1057 C1)
    return {"open": open_now, "opens": sum(1 for e in evs if e.get("kind") == "breaker_open"),
            "closes": sum(1 for e in evs if e.get("kind") == "breaker_close")}
