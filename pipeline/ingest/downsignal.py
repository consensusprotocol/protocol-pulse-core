"""pipeline/ingest/downsignal.py: RULING 87 (orchestrator 21:18 Nov 13), this watcher's side of the ONE shared
'Heimdall down' signal (pp-selectid pipeline/heimdall_health.py, the builder's module, used through its API only; its
state file under its own flock).

NOTE  every real call of this watcher to a back-end of the signal's vendor (providers.json down_signal) is one outcome:
      answered (ok, invalid: the gateway answered inside the back-end's deadline) or not (any other kind of a real call:
      down, refusing, empty, past the deadline). No note: a stored reply or a missing key (no call was made), a probe
      call (its outcome is the probe's, never a verdict answer), another vendor's back-end. A back-end under a runtime
      base_url override (this watcher's outage drill) is noted drill=True: recorded by the module, never counted.
ONE   thread owns the shared file (tick, the service's signal loop): the router's threads only leave a pending outcome
      under a local lock (the latest answer and the first failure after it, each with its own time), so a held or
      stuck shared lock never stalls the miner.
TICK  pending notes; every SIGNAL_MODE_S: mode() (the 15-minute rule on the clock) and, while probe_due(), the probe
      role asked in its own thread (never from a stored reply, never while a probe back-end is under an override); its
      outcome goes to probe_result() at the next tick (a probe whose back-ends could not be called is no probe).
SEEN  every switch in the shared state, whoever made it, once: at the start of this watcher's STATE line 1
      (spend.write_switch_head) and in its evidence file (the number seen is kept in the queue; the history before
      this watcher was wired is not announced). The module is given no STATE path: its own head writer would leave a
      lock file beside STATE.md and bypass the notices' lock.
FAIL  an unreadable state (HealthUnreadable, OSError, the module missing or broken, a call stuck on the lock) is never
      read as up or down: live.json says so at once, STATE after SIGNAL_NOTICE_S (spend.write_signal_notice, removed
      when the signal is read again). The miner does not depend on the mode: its Plan B under the 05:30 Nov 12 spend
      freeze is queue and wait (the mine chain as it is: Heimdall, then the local model, else the videos wait).
"""
import importlib.util
import inspect
import json
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from . import providers, spend

SIGNAL_EVERY_S = 5.0            # the signal loop: pending notes are written this often
SIGNAL_MODE_S = 30.0            # mode() and probe_due() at most this often (the module's probe interval is 120 s)
SIGNAL_NOTICE_S = 1800          # the signal not read this long: one line at the top of STATE
PROBE_PROMPT = "Reply with the single word OK."      # the builder's probe question; any answer counts
WHO = "pp-ingest"
ANSWERED = frozenset({"ok", "invalid"})              # the gateway answered inside the deadline
NO_CALL = frozenset({"cache", "disabled"})           # nothing was asked of the gateway
ET = ZoneInfo("America/New_York")
DOWN = "plan_b"                                      # the module's down mode; its other mode is the up one (MODES)
MINER_PLAN_B = ("queue and wait: the 05:30 Nov 12 spend freeze binds the miner until the orchestrator answers the "
                "Plan B question (the mine chain as it is, else the videos wait)")


def load_module(path):
    """The builder's module, by path (its `pipeline` package would shadow this one), checked for the API used here."""
    spec = importlib.util.spec_from_file_location("pp_selectid_down_signal", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no module at {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for name in ("note", "mode", "probe_due", "probe_result", "HealthUnreadable", "STATE", "MODES"):
        if not hasattr(mod, name):
            raise ImportError(f"{path} has no {name}: not the ruling 87 API this watcher was written for")
    if len(mod.MODES) != 2 or DOWN not in mod.MODES:
        raise ImportError(f"{path}: modes {mod.MODES!r}, not one up mode and {DOWN!r}")
    return mod


def _utc(t):
    return datetime.fromtimestamp(t, timezone.utc)


def _iso(t):
    return _utc(t).strftime("%Y-%m-%dT%H:%M:%SZ") if t is not None else None


def _any_text(c):
    if not c.strip():
        raise providers.Invalid("no text")
    return c


def head(rec, seen_ts, up, plan_b_tail="; THE MINER'S PLAN B: QUEUE AND WAIT (SPEND FREEZE)"):
    """STATE line 1's head for one switch record {"utc", "to", "why", "by"} (the module's words: "SWITCHED TO PLAN B",
    "BACK TO <UP MODE>", plus who made it and what the miner does), IN CAPITALS, one physical line. None: not a switch
    between the module's two modes (up: the mode that is not DOWN)."""
    to = rec.get("to")
    if to == DOWN:
        word, tail = "SWITCHED TO PLAN B", plan_b_tail
    elif to == up:
        word, tail = "BACK TO " + up.upper().replace("_", "-"), ""
    else:
        return None
    try:
        t = datetime.fromisoformat(str(rec.get("utc")).replace("Z", "+00:00"))
        t = t if t.tzinfo is not None else None
    except ValueError:
        t = None
    when = t.astimezone(ET).strftime("%H:%M") if t else _utc(seen_ts).astimezone(ET).strftime("%H:%M")
    text = f"{when} ET: {word} ({rec.get('why') or 'no reason recorded'}; BY {rec.get('by') or 'unknown'}" + \
           ("" if t else "; ITS TIME NOT RECORDED, SEEN AT THIS TIME") + f"){tail} |"
    return " ".join(text.upper().split())


class DownSignal:
    def __init__(self, cfg, router, overrides, q, paths, clock=time.time, log=print, module_path=None,
                 state_path=None):
        ds = cfg["down_signal"]
        self.vendor, self.probe_role, self.label = ds["vendor"], ds["probe_role"], ds["label"]
        self.paid, self.roles = cfg.get("paid_route"), cfg["roles"]     # ruling 98: the miner's paid route
        self.paid_open, self.view = False, None   # the miner reads paid_open; view: the shared state as last read
        pr = self.paid
        self.plan_b_tail = (f"; THE MINER'S PLAN B (RULING 98): NEW UPLOADS ON {pr['label']} AFTER "
                            f"{int(pr['after_down_s'] // 60)} MINUTES DOWN, CAPPED" if pr else
                            "; THE MINER'S PLAN B: QUEUE AND WAIT (SPEND FREEZE)")
        self.miner_plan_b = (f"ruling 98: after {int(pr['after_down_s'] // 60)} minutes down, new uploads (the last "
                             f"{int(pr['new_within_s'] // 3600)} h, conversations first) on {pr['role']} "
                             f"({pr['label']}), capped at ${float(self.roles[pr['role']]['daily_cap_usd']):.2f} a "
                             "day (ET); then queue and wait" if pr else MINER_PLAN_B)
        self.router, self.overrides, self.q, self.clock, self.log = router, overrides, q, clock, log
        self.evidence, self.notify = paths["signal"], paths["notify"]
        self.lock = threading.Lock()
        self.pending = {"answer": None, "fail": None, "drills": 0}
        self.probe_out, self.probe_thread, self.next_mode = None, None, 0.0
        self.mode, self.last_probe, self.head_error, self.drill_logged = None, None, None, False
        self.error = self.error_since = self.busy_since = None
        self.n = {"answers_noted": 0, "failures_noted": 0, "drill_notes": 0, "unnoted": 0, "probes": 0,
                  "probe_answers": 0, "probes_not_made": 0, "probe_reports_lost": 0}
        self.module_path, self.state_path, self.hh, self.up = module_path or ds["module"], state_path, None, None
        self.probe_kw = {}
        try:
            self.hh = load_module(self.module_path)
            self.state_path = state_path or self.hh.STATE
            self.up = next(m for m in self.hh.MODES if m != DOWN)
            try:                                     # the builder's probe_due CLAIMS its slot and names the claimer
                takes_who = "who" in inspect.signature(self.hh.probe_due).parameters   # (pp-selectid 11ed255f,
            except (TypeError, ValueError):          # REQUESTS R12); an older module's probe_due takes no `who`
                takes_who = False
            # probe_kw: the name this watcher's claims carry (the state's last_probe_by names whoever won the latest
            # slot). Without it the fallback is said once (audit r87claim c2, its condition), never silent.
            self.probe_kw = {"who": WHO + " probe"} if takes_who else {}
            if not takes_who:
                self.log("RULING 87: the shared module's probe_due takes no `who`: this watcher's probes are not "
                         "named (a module older than pp-selectid 11ed255f has no slot claim; a probe_due whose "
                         "signature cannot be read, e.g. wrapped or positional-only, is called without a name)")
        except Exception as e:                       # noqa: BLE001 (a module that cannot load is said, never guessed)
            self._fail(f"the shared module {self.module_path} cannot be loaded: {type(e).__name__}: {e}")

    # ── the router's threads ──

    def noted(self, rec):
        """One attempt record (Service._on_attempt): O(1), never the shared file, never raises."""
        try:
            bid, kind = rec.get("backend"), rec.get("kind")
            if kind in NO_CALL or rec.get("role") == self.probe_role or self.router.vendor(bid) != self.vendor:
                return
            drill, t = self._drill(bid), self.clock()
            with self.lock:
                if drill:
                    self.pending["drills"] += 1
                elif kind in ANSWERED:
                    self.pending["answer"], self.pending["fail"] = t, None
                elif self.pending["fail"] is None:
                    self.pending["fail"] = t
        except Exception:                            # noqa: BLE001 (the signal never decides a call)
            pass

    def _drill(self, bid):
        return bool(self.overrides is not None and self.overrides.get(bid, "base_url"))

    # ── the signal thread ──

    def tick(self, wait=False):
        """The signal loop: the only caller of the shared module in this process. wait: join a probe started now."""
        if self.hh is None:
            return
        self._flush()
        self._report_probe()                         # a finished probe is reported before another can be due
        now = self.clock()                           # (audit r87 C1-3: else a second probe in its slot)
        if now >= self.next_mode:
            self.next_mode = now + SIGNAL_MODE_S
            m = self._call("mode", now=_utc(now), evidence=self.evidence, who=WHO)
            self.mode = m if m is not None else self.mode
            if not self._probing():
                drills = [b for b in self.router.chain(self.probe_role) if self._drill(b)]
                if drills:
                    if not self.drill_logged:
                        self.log(f"RULING 87: no probe while {drills} run under an override (a drill)")
                    self.drill_logged = True
                else:
                    self.drill_logged = False
                    if self._call("probe_due", now=_utc(now), **self.probe_kw):   # True claims the slot (11ed255f):
                        self._start_probe()      # a probe this watcher then cannot make sends no probe_result and the
                                                 # slot stays spent from its claim (the builder's semantics)
        if wait and self.probe_thread is not None:
            self.probe_thread.join()
            self._report_probe()
        self._seen()
        self._route_tick()

    # ── ruling 98: the miner's paid route ──

    def _route_tick(self):
        """Opens when the shared state says DOWN and no family of the signal's vendor has answered for after_down_s
        running (the state's failure clock); closes when the signal is back (3 good probes). A signal not read opens,
        closes and spends nothing (paid_open False while it lasts; the queue keeps the route's state for a restart).
        Every switch, and the day's cap when no further call fits under it, goes to STATE line 1."""
        pr = self.paid
        if not pr:
            return
        now, v = self.clock(), (self.view if not self.error else None)
        st = self.q.kv_get("paid_route") or {"open": False, "since": None}
        if v is None:
            self.paid_open = False
            return
        if not st["open"]:
            fs = v.get("failing_since_utc")
            try:
                fs_t = datetime.fromisoformat(str(fs).replace("Z", "+00:00")).timestamp() if fs else None
            except ValueError:
                fs_t = None
            if v.get("mode") == DOWN and fs_t is not None and now - fs_t >= float(pr["after_down_s"]):
                st = {"open": True, "since": _iso(now)}
                cap = float(self.roles[pr["role"]]["daily_cap_usd"])
                self._route_switch(st, f"MINER ON THE PAID ROUTE ({pr['label']}: NO {self.label} ANSWER FOR "
                                       f"{int((now - fs_t) // 60)} MINUTES, SINCE {fs}; NEW UPLOADS OF THE LAST "
                                       f"{int(pr['new_within_s'] // 3600)} H ONLY, CONVERSATIONS FIRST; CAP "
                                       f"${cap:.2f} A DAY, ET)", "paid_route_open")
        elif v.get("mode") == self.up:
            st = {"open": False, "since": _iso(now)}
            self._route_switch(st, f"MINER OFF THE PAID ROUTE (BACK ON {self.label}: THE SIGNAL IS BACK; ITS "
                                   f"VIDEOS STILL INSIDE {int(pr['recheck_within_s'] // 3600)} H ARE MINED AGAIN "
                                   "THERE)", "paid_route_closed")
        self.paid_open = bool(st["open"])
        if self.paid_open:
            rc = self.roles[pr["role"]]
            cap, spent = float(rc["daily_cap_usd"]), self.router.caps.today(pr["role"])
            day = datetime.fromtimestamp(now, ET).date().isoformat()
            if spent + float(rc.get("cap_reserve_usd", 0.0)) > cap and self.q.kv_get("paid_cap_day") != day:
                self.q.kv_set("paid_cap_day", day)
                self._route_switch(None, f"MINER PAID ROUTE CAP REACHED (${spent:.2f} OF ${cap:.2f} TODAY, ET): "
                                         "QUEUE AND WAIT", "paid_route_cap")

    def _route_switch(self, st, words, kind):
        now = self.clock()
        if st is not None:
            self.q.kv_set("paid_route", st)
        h = " ".join(f"{_utc(now).astimezone(ET).strftime('%H:%M')} ET: {words} |".upper().split())
        try:
            spend.write_switch_head(h, notify_path=self.notify)
        except (OSError, ValueError) as e:
            self.log(f"RULING 98: STATE line 1 not written: {type(e).__name__}: {e}")
        self._evidence({"kind": kind, "utc": _iso(now), "head": h, "by": WHO})
        self.q.event(kind, None, None, head=h)
        self.log(f"RULING 98: {h}")

    def _probing(self):
        """A probe in flight, or finished and not yet reported (its thread leaves the outcome before it ends)."""
        if self.probe_thread is not None and self.probe_thread.is_alive():
            return True
        with self.lock:
            return self.probe_out is not None

    def _call(self, fn, *a, **kw):
        self.busy_since = self.clock()
        try:
            out = getattr(self.hh, fn)(*a, path=self.state_path, **kw)
        except Exception as e:                       # noqa: BLE001 (HealthUnreadable, OSError, a broken module)
            self._fail(f"{type(e).__name__}: {str(e)[:240]}", where=fn)     # one stable text per cause: no log or
            return None                                                      # STATE churn while it lasts
        finally:
            self.busy_since = None
        self._recovered()
        return out

    def _flush(self):
        with self.lock:
            p, self.pending = self.pending, {"answer": None, "fail": None, "drills": 0}
        if p["drills"]:
            if self._call("note", False, now=_utc(self.clock()), evidence=self.evidence, who=WHO, drill=True) \
                    is not None:
                self.n["drill_notes"] += 1
        for answered, t in ((True, p["answer"]), (False, p["fail"])):     # the failure, if any, came after the answer
            if t is None:
                continue
            m = self._call("note", answered, now=_utc(t), evidence=self.evidence, who=WHO)
            if m is None:
                self.n["unnoted"] += 1
                continue
            self.mode = m
            self.n["answers_noted" if answered else "failures_noted"] += 1

    def _start_probe(self):
        def run():
            t0 = self.clock()
            try:
                out = self.router.run(self.probe_role, PROBE_PROMPT, None, _any_text, tag="probe87", use_cache=False)
                res = (True, f"{out.backend} answered in {self.clock() - t0:.0f} s")
            except providers.AllBackendsFailed as e:
                tried = "; ".join(f"{b} {s} ({str(w)[:100]})" for b, s, w in e.tried)
                called = any(s in ("unavailable", "rejected") for _, s, _ in e.tried)
                res = (False, tried) if called else (None, "no probe back-end could be called: " + tried)
            except Exception as e:                   # noqa: BLE001 (a probe that breaks is no probe)
                res = (None, f"the probe broke: {type(e).__name__}: {e}")
            with self.lock:
                self.probe_out = {"t": self.clock(), "answered": res[0], "why": res[1], "logged": False}
        self.probe_thread = threading.Thread(target=run, daemon=True, name="probe87")
        self.probe_thread.start()

    def _report_probe(self):
        """A finished probe's outcome to probe_result (with its own time). One the shared state did not take is kept
        for the next tick while it is younger than the module's probe interval, then dropped and counted, never
        reported late: an old answer proves nothing about now (audit r87 C2-1)."""
        with self.lock:
            out, self.probe_out = self.probe_out, None
        if out is None:
            return
        t, answered, why = out["t"], out["answered"], out["why"]
        if not out["logged"]:                        # the evidence line once, whatever happens to the report
            out["logged"] = True
            self.last_probe = {"utc": _iso(t), "answered": answered, "why": why[:300]}
            self._evidence({"kind": "probe", "utc": _iso(t), "answered": answered, "why": why[:300], "by": WHO})
        if answered is None:
            self.n["probes_not_made"] += 1
            self.log(f"RULING 87: probe not made: {why[:300]}")
            return
        m = self._call("probe_result", answered, now=_utc(t), evidence=self.evidence, who=WHO + " probe")
        if m is None:
            if self.clock() - t < float(getattr(self.hh, "PROBE_EVERY_S", 120)):
                with self.lock:                      # no new probe starts while it waits (_probing)
                    self.probe_out = self.probe_out or out
            else:
                self.n["probe_reports_lost"] += 1
                self.log(f"RULING 87: the probe of {_iso(t)} was never recorded (the shared state not read): "
                         "dropped, never reported late")
            return
        self.n["probes"] += 1
        self.n["probe_answers"] += int(answered)
        self.mode = m

    def _seen(self):
        """Every switch in the shared state not yet seen here: STATE line 1, the evidence file, an event."""
        try:
            with open(self.state_path) as f:
                s = json.load(f)
            sw = s.get("switches") if isinstance(s, dict) else None
            if not isinstance(sw, list):
                raise ValueError("no switches list")
        except FileNotFoundError:
            self.view = None
            return                                   # no state yet: the module writes it at the first note
        except (OSError, ValueError) as e:
            self.view = None
            if self.error is None:                   # the module's own calls already said so otherwise
                self._fail(f"{type(e).__name__}: {str(e)[:240]}", where="reading the switches")
            return
        self.view = s
        try:
            seen = int(self.q.kv_get("signal_switches_seen"))
        except (TypeError, ValueError):              # none yet, or unreadable: recorded again (audit r87 C1-4)
            seen = None
        if seen is None or seen > len(sw):
            self.q.kv_set("signal_switches_seen", str(len(sw)))
            self.log(f"RULING 87: wired to {self.state_path} (mode {s.get('mode')}); {len(sw)} earlier switch(es) "
                     "there are not announced here")
            self._evidence({"kind": "wired", "utc": _iso(self.clock()), "mode": s.get("mode"),
                            "switches_before": len(sw), "by": WHO})
            return
        for i in range(seen, len(sw)):
            rec = sw[i] if isinstance(sw[i], dict) else {}
            h = head(rec, self.clock(), self.up, self.plan_b_tail)
            if h is not None:
                try:
                    spend.write_switch_head(h, notify_path=self.notify)
                except (OSError, ValueError) as e:
                    msg = f"RULING 87: STATE line 1 not written (tried again next tick): {type(e).__name__}: {e}"
                    if msg != self.head_error:
                        self.log(msg)
                    self.head_error = msg
                    return
            self.head_error = None
            self._evidence(dict(rec, kind="seen", seen_utc=_iso(self.clock()), seen_by=WHO, head=h))
            self.q.event("down_signal_switch", None, None, utc=rec.get("utc"), to=rec.get("to"),
                         why=rec.get("why"), by=rec.get("by"))
            self.log(f"RULING 87: {h or 'an unknown switch: ' + json.dumps(rec)[:300]}")
            self.q.kv_set("signal_switches_seen", str(i + 1))

    def _fail(self, why, where="loading"):
        if self.error != why:
            self.log(f"RULING 87: the shared {self.label} down signal is not read ({where}): {why} (never guessed up "
                     "or down)")
            if self.error is None:
                self._evidence({"kind": "unreadable", "utc": _iso(self.clock()), "why": why, "by": WHO})
                self.q.event("down_signal_unreadable", None, None, why=why)
        self.error_since = self.error_since or self.clock()   # first: the health thread never sees an error
        self.error = why                                       # without its time (audit r87 C1-2)

    def _recovered(self):
        if self.error is not None:
            self.log(f"RULING 87: the shared {self.label} down signal is read again (not read since "
                     f"{_iso(self.error_since)})")
            self._evidence({"kind": "readable", "utc": _iso(self.clock()), "since": _iso(self.error_since),
                            "by": WHO})
            self.q.event("down_signal_readable", None, None, since=_iso(self.error_since))
            self.error = self.error_since = None

    def _evidence(self, rec):
        try:
            with open(self.evidence, "a") as f:
                f.write(json.dumps(rec, default=str) + "\n")
        except OSError:
            pass                                     # evidence, never a gate

    # ── the health thread (never blocked by the shared file) ──

    def check_notice(self):
        """The signal not read (or a call into it not returned) for SIGNAL_NOTICE_S: one line at the top of STATE;
        removed when it is read again (the queue remembers it across restarts)."""
        now, busy, err, err_since = self.clock(), self.busy_since, self.error, self.error_since   # one snapshot
        if err:
            why, since = err, err_since if err_since is not None else now
        elif busy is not None and now - busy >= SIGNAL_NOTICE_S:
            why, since = "a call into the shared state has not returned (its lock held?)", busy
        else:
            why, since = None, None
        noticed = self.q.kv_get("signal_noticed") == "1"
        if why and now - since >= SIGNAL_NOTICE_S:
            line = spend.write_signal_notice(why[:300], _iso(since), notify_path=self.notify, label=self.label)
            if not noticed:
                self.log(line)
                self.q.kv_set("signal_noticed", "1")
        elif not why and noticed:
            spend.write_signal_notice(None, None, notify_path=self.notify, label=self.label)
            self.q.kv_set("signal_noticed", "0")

    def snapshot(self):
        now, busy = self.clock(), self.busy_since
        return {"wired": self.hh is not None, "module": self.module_path, "state_file": self.state_path,
                "evidence": self.evidence, "vendor": self.vendor, "mode": None if self.error else self.mode,
                "not_read": self.error, "not_read_since": _iso(self.error_since),
                "call_waiting_s": round(now - busy) if busy is not None else None, "last_probe": self.last_probe,
                "counts": dict(self.n), "switches_seen": self.q.kv_get("signal_switches_seen"),
                "probe_claimed_as": self.probe_kw.get("who"),
                "paid_route": self._route_snapshot(),
                "miner_plan_b": self.miner_plan_b}

    def signal_back(self):
        """Ruling 98: the signal is read and says up, and the paid route is closed (the paid route's videos may be
        mined again on the mine role)."""
        v = self.view if not self.error else None
        return v is not None and v.get("mode") == self.up and not self.paid_open

    def _route_snapshot(self):
        if not self.paid:
            return None
        rc = self.roles[self.paid["role"]]
        st = self.q.kv_get("paid_route") or {"open": False, "since": None}
        return {"open": self.paid_open, "recorded": st, "role": self.paid["role"],
                "spent_today_usd": round(self.router.caps.today(self.paid["role"]), 4),
                "cap_usd": float(rc["daily_cap_usd"]), "label": self.paid["label"]}

