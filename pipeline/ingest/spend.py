"""pipeline/ingest/spend.py: the gateway's spend meter and the STATE notice (orchestrator 02:45: a NOTIFY, never a halt).

The metered gateway and its label live in providers.json (spend_meter). Spend is the probe's own measure: GET /credits
total_usage minus the sweep baseline (PHASE3_FLEET_LOAD.md: the $460 cap is "total sweep spend measured by /credits
delta from 0.2036796658"), plus this service's usage.cost since that reading. state(): 'ok' below 90 % of the cap;
'tripped' at or above it; 'unmeasured' when no reading is younger than stale_after_s (law L-m: an unmeasured spend is
never read as below the tripwire). Anything but 'ok' NOTIFIES: one line at the top of the STATE file ("<LABEL> SPEND AT
90%" / "<LABEL> SPEND UNMEASURED"), and the metered back-ends go to the end of every chain (providers.Router.order);
they keep mining (integrator B1; orchestrator 05:30: "Heimdall mining continues").
"""
import fcntl
import json
import os
import re
import threading
import time

from . import config

OUTAGE_PREFIX = "MINING WAITING ON AN OUTAGE"
PURGE_PREFIX = "PURGE NOT RUNNING"
SIGNAL_SUFFIX = "DOWN SIGNAL NOT READ"        # ruling 87: "<label> DOWN SIGNAL NOT READ since ..." (the label from
SWITCH_PATTERN = (r"\d\d:\d\d ET: (?:SWITCHED TO PLAN B|BACK TO [A-Z0-9_-]+-FIRST|"   # providers.json down_signal)
                  r"MINER (?:ON|OFF) THE PAID ROUTE|MINER PAID ROUTE CAP REACHED)")       # ruling 98: the miner's route
SWITCH_RE = re.compile("^" + SWITCH_PATTERN)
SIGNAL_RE = re.compile(r"^[A-Z0-9_-]+ " + SIGNAL_SUFFIX)    # any label's: only the signal writes this notice
NOTICE_RE = re.compile(r"^(?:[A-Z0-9_-]+ SPEND (?:AT 90%|UNMEASURED)|" + OUTAGE_PREFIX + "|" + PURGE_PREFIX + "|" +
                       r"[A-Z0-9_-]+ " + SIGNAL_SUFFIX + "|" + SWITCH_PATTERN + ")")


def notice_prefixes(label):
    return (f"{label} SPEND AT 90%", f"{label} SPEND UNMEASURED")


def _rewrite_top(doc, lock_path, mine, line, keep=lambda h: False):
    """The STATE file's leading block of notice lines (NOTICE_RE): this writer's lines (mine) are replaced by `line`
    (None: removed; one of them kept where keep(h); a callable: line(this writer's lines) -> the line), every other
    notice stays; ruling 87's switch line is always the first. Rewritten only when the text changes, under an flock.
    Only a MISSING file starts empty: a STATE file that exists and cannot be read raises (OSError) and is never
    rewritten from nothing (audit r87 C1-5: it would have lost the whole file)."""
    with open(lock_path, "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            with open(doc) as f:
                text = f.read()
        except FileNotFoundError:
            text = ""
        lines = text.split("\n") if text else []
        head = []
        while lines and NOTICE_RE.match(lines[0]):
            head.append(lines.pop(0))
        if callable(line):
            line = line([h for h in head if mine(h)])
        kept = [h for h in head if mine(h) and keep(h)][:1]
        others = [h for h in head if not mine(h)]
        block = ([line] if line else []) + kept + others
        block = [h for h in block if SWITCH_RE.match(h)] + [h for h in block if not SWITCH_RE.match(h)]
        new = "\n".join(block + lines)
        if new != text:
            tmp = f"{doc}.{os.getpid()}.{threading.get_ident()}.tmp"
            with open(tmp, "w") as f:
                f.write(new)
            os.replace(tmp, doc)


def write_outage_notice(waiting, since, doc=None, notify_path=None):
    """While videos wait on an outage of every mine back-end (service.OUTAGE_NOTICE_S), one line at the top of the
    STATE file says so; waiting == 0 removes it."""
    doc = doc or config.STATE_DOC
    line = (f"{OUTAGE_PREFIX}: {waiting} video(s) waiting since {since}: every mine back-end down or refusing; they "
            "are mined when one returns (nothing dropped, no paid frontier fallback).") if waiting else None
    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
    if notify_path:
        os.makedirs(os.path.dirname(notify_path), exist_ok=True)
        with open(notify_path, "a") as f:
            f.write(json.dumps({"at": config.iso(), "outage_waiting": waiting, "since": since}) + "\n")
    _rewrite_top(doc, lock_path, lambda h: h.startswith(OUTAGE_PREFIX), line)
    return line


class CreditMeter:
    def __init__(self, mcfg, backend, clock=time.time, on_change=None):
        self.c, self.backend, self.clock, self.on_change = mcfg, backend, clock, on_change
        self.measured_at = None
        self.measured_spend = None
        self.total_usage = None
        self.total_credits = None
        self.local_since = 0.0
        self.last_error = None
        self.lock = threading.Lock()
        self._state = None

    @property
    def label(self):
        return str(self.c.get("label") or "GATEWAY").upper()

    @property
    def threshold(self):
        return float(self.c["cap_usd"]) * float(self.c["notify_fraction"])

    def measure(self):
        try:
            j = self.backend.get_json("/credits")
            d = j.get("data") if isinstance(j, dict) else None
            usage, credits = d.get("total_usage"), d.get("total_credits")
            if type(usage) not in (int, float):
                raise ValueError(f"total_usage {usage!r}")
        except Exception as e:
            red = getattr(self.backend, "redact", None)
            msg = f"{type(e).__name__}: {e}"[:300]
            with self.lock:
                self.last_error = red(msg) if red is not None else msg
            self._check()
            return None
        with self.lock:
            self.total_usage, self.total_credits = float(usage), credits
            self.measured_spend = float(usage) - float(self.c["baseline_usage"])
            self.measured_at, self.local_since, self.last_error = self.clock(), 0.0, None
        self._check()
        return self.measured_spend

    def add_local(self, usd):
        with self.lock:
            self.local_since += float(usd or 0.0)

    def estimate(self):
        with self.lock:
            return None if self.measured_spend is None else self.measured_spend + self.local_since

    def state(self):
        with self.lock:
            if self.measured_at is None or self.clock() - self.measured_at > float(self.c["stale_after_s"]):
                return "unmeasured"
            return "tripped" if self.measured_spend + self.local_since >= self.threshold else "ok"

    def _check(self):
        st = self.state()
        if st != self._state:
            self._state = st
            if self.on_change:
                self.on_change(st, self.snapshot())

    def probe_ledger(self):
        try:
            with open(self.c["probe_ledger"]) as f:
                j = json.load(f)
            return {"aggregate_spend_usd": j.get("aggregate_spend_usd"), "updated_at": j.get("updated_at")}
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}"[:200]}

    def snapshot(self):
        with self.lock:
            est = None if self.measured_spend is None else self.measured_spend + self.local_since
            return {"spend_usd": None if est is None else round(est, 4), "cap_usd": self.c["cap_usd"],
                    "fraction": None if est is None else round(est / float(self.c["cap_usd"]), 4),
                    "threshold_usd": self.threshold, "total_usage": self.total_usage,
                    "total_credits": self.total_credits,
                    "measured_at": None if self.measured_at is None else
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.measured_at)),
                    "last_error": self.last_error}


def write_state_notice(state, snap, doc=None, notify_path=None, label="GATEWAY"):
    """The first line of the STATE file carries the notice while the meter is not 'ok' (idempotent: one notice line,
    replaced, never duplicated). A 90 % notice stays once written (spend does not go back down). The file is rewritten
    only when its text changes, under a lock next to the notify log; the NOTIFY log gets every state change."""
    doc = doc or config.STATE_DOC
    prefixes = notice_prefixes(label)
    if state == "tripped":
        line = (f"{prefixes[0]} (${snap.get('spend_usd')} of ${snap.get('cap_usd')} at {snap.get('measured_at')}): "
                "NOTIFY only; mining continues on it (other back-ends first where any are available); nothing halted.")
    elif state == "unmeasured":
        line = (f"{prefixes[1]} (last reading {snap.get('measured_at')}, error {snap.get('last_error')}): NOTIFY "
                "only; mining continues on it; the spend is read again every 10 min.")
    else:
        line = None
    if notify_path:
        os.makedirs(os.path.dirname(notify_path), exist_ok=True)
        with open(notify_path, "a") as f:
            f.write(json.dumps({"at": config.iso(), "state": state, "meter": snap}) + "\n")
    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
    _rewrite_top(doc, lock_path, lambda h: h.startswith(prefixes), line,
                 keep=(lambda h: False) if state == "tripped" else (lambda h: h.startswith(prefixes[0])))
    return line


def write_purge_notice(why, since, doc=None, notify_path=None):
    """Ruling 77 (audit c1, muse P1): while the rolling purge has deleted nothing because it could not run safely (its
    spec refused, the delivered set or /proc unreadable) for longer than service.PURGE_NOTICE_S, one line at the top of
    the STATE file says so; why None removes it."""
    doc = doc or config.STATE_DOC
    line = (f"{PURGE_PREFIX} since {since}: {why} (expired media is kept until this is fixed; nothing is deleted "
            "while it cannot run safely)") if why else None
    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
    _rewrite_top(doc, lock_path, lambda h: h.startswith(PURGE_PREFIX), line)
    return line


def write_switch_head(head, doc=None, notify_path=None):
    """Ruling 87: one switch of the shared Heimdall signal, whoever made it ("HH:MM ET: SWITCHED TO PLAN B (...) |"),
    prepended to the one physical line at the start of STATE line 1 that holds every earlier switch, newest first; that
    line stays the first whatever other notice comes or goes. Under the notices' own lock (never a lock file beside the
    STATE file)."""
    if not SWITCH_RE.match(head or ""):
        raise ValueError(f"not a switch head: {head!r}")
    doc = doc or config.STATE_DOC
    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
    if notify_path:
        os.makedirs(os.path.dirname(notify_path), exist_ok=True)
        with open(notify_path, "a") as f:
            f.write(json.dumps({"at": config.iso(), "down_signal_switch": head}) + "\n")
    def merged(old):                    # idempotent (audit r87 C1-1): a head already there is not added again (a
        cur = " ".join(old)             # restart between this write and the count of switches seen re-sends it)
        return cur if head in cur else " ".join([head] + old)
    _rewrite_top(doc, lock_path, lambda h: bool(SWITCH_RE.match(h)), merged)
    return head


def write_signal_notice(why, since, doc=None, notify_path=None, label="GATEWAY"):
    """Ruling 87: the shared Heimdall signal not read for longer than downsignal.SIGNAL_NOTICE_S (its state file
    unreadable, its module missing, its lock held): one line at the top of STATE (never 'up' or 'down' by guess); why
    None removes it."""
    doc = doc or config.STATE_DOC
    prefix = f"{label} {SIGNAL_SUFFIX}"
    line = (f"{prefix} since {since}: {why} (this watcher's notes and probes wait; the miner does not depend on the "
            "signal: its chain as it is, else the videos wait)") if why else None
    lock_path = os.path.join(os.path.dirname(notify_path), "state_doc.lock") if notify_path else doc + ".lock"
    if notify_path:
        os.makedirs(os.path.dirname(notify_path), exist_ok=True)
    _rewrite_top(doc, lock_path, lambda h: bool(SIGNAL_RE.match(h)), line)   # any label's (audit r87 C1-6)
    return line
