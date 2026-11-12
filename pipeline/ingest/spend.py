"""pipeline/ingest/spend.py: the Heimdall spend meter and the STATE notice (orchestrator 02:45: a NOTIFY, never a halt).

Spend is the probe's own measure: GET /credits total_usage minus the sweep baseline (PHASE3_FLEET_LOAD.md: the $460 cap
is "total sweep spend measured by /credits delta from 0.2036796658"), plus this service's usage.cost since that reading.
state(): 'ok' below 90 % of the cap; 'tripped' at or above it; 'unmeasured' when no reading is younger than
stale_after_s (law L-m: an unmeasured spend is never read as below the tripwire). Anything but 'ok' routes mining to the
other back-ends (providers.Router.available) and writes one line at the top of the STATE file.
"""
import json
import os
import threading
import time

from . import config

NOTICE_PREFIXES = ("HEIMDALL SPEND AT 90%", "HEIMDALL SPEND UNMEASURED")


class HeimdallMeter:
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
            with self.lock:
                self.last_error = f"{type(e).__name__}: {e}"[:300]
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


def write_state_notice(state, snap, doc=None, notify_path=None):
    """The first line of the STATE file carries the notice while the meter is not 'ok' (idempotent: one notice line,
    replaced, never duplicated). A 90 % notice stays once written (spend does not go back down)."""
    doc = doc or config.STATE_DOC
    if state == "tripped":
        line = (f"HEIMDALL SPEND AT 90% (${snap.get('spend_usd')} of ${snap.get('cap_usd')} at "
                f"{snap.get('measured_at')}): mining routed to the other back-ends; nothing halted.")
    elif state == "unmeasured":
        line = (f"HEIMDALL SPEND UNMEASURED (last reading {snap.get('measured_at')}, error {snap.get('last_error')}): "
                "mining routed to the other back-ends until a reading succeeds.")
    else:
        line = None
    try:
        with open(doc) as f:
            lines = f.read().split("\n")
    except OSError:
        lines = []
    head = []
    while lines and lines[0].startswith(NOTICE_PREFIXES):
        head.append(lines.pop(0))
    kept = [h for h in head if h.startswith(NOTICE_PREFIXES[0])] if state != "tripped" else []
    lines = ([line] if line else []) + kept[:1] + lines
    tmp = f"{doc}.{os.getpid()}.tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines))
    os.replace(tmp, doc)
    if notify_path:
        os.makedirs(os.path.dirname(notify_path), exist_ok=True)
        with open(notify_path, "a") as f:
            f.write(json.dumps({"at": config.iso(), "state": state, "meter": snap}) + "\n")
    return line
