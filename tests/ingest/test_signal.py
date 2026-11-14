"""Ruling 87 (orchestrator 21:18 Nov 13): the watcher on the ONE shared 'Heimdall down' signal (pp-selectid
pipeline/heimdall_health.py, used through its API only, on a throw-away state file here).

The router: a breaker-free role (the probe) is never held back by an open circuit and never teaches the breaker; its
own transport retries. The STATE head: every switch, whoever made it, at the start of line 1, newest first, one
physical line, kept first when other notices come and go. The service: what is noted (a real call to the signal's
vendor; answered = ok or invalid), what is not (a stored reply, a missing key, a probe call, another vendor), a drill
(a back-end under a base_url override) never counted, the probe while one is due (never from a stored reply, never
during a drill), an unreadable state said (live.json, then STATE after 30 min) and never guessed, the miner never
waiting on the shared lock."""
import fcntl
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

import helpers as H
from pipeline.ingest import config, downsignal, providers, service, spend, stats
from pipeline.ingest.providers import BackendError

MODULE = "/home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py"     # the builder's, read only
T0 = datetime(2026, 11, 14, 7, 0, tzinfo=timezone.utc).timestamp()            # 02:00 ET


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def probe_cfg(chain=("a", "b"), vendor="hv"):
    cfg = H.router_cfg(list(chain))
    for b in chain:
        cfg["backends"][b]["vendor"] = vendor
    cfg["roles"]["probe"] = {"chain": list(chain), "attempts": 1, "max_tokens": 64, "transport_retries": 0,
                             "breaker": False}
    cfg["down_signal"] = {"vendor": vendor, "probe_role": "probe", "label": "HV", "module": MODULE}
    return cfg


def router_for(cfg, backends):
    return providers.Router(cfg, keyring=providers.Keyring("/nonexistent/.env"), backends={b.id: b for b in backends},
                            sleep=lambda s: None)


def ok_any(c):
    if not c.strip():
        raise providers.Invalid("empty")
    return c


# ── the router ──

def test_a_breaker_free_role_calls_through_an_open_circuit_and_never_teaches_the_breaker():
    a = H.FakeBackend("a", script=["OK", BackendError("network", "down"), "OK"])
    b = H.FakeBackend("b", script=["OK"])
    r = router_for(probe_cfg(), [a, b])
    r.health["a"]._open(time.time(), "test")
    before = (r.health["a"].open_until, r.health["a"].consec, len(r.health["a"].events))
    with pytest.raises(providers.AllBackendsFailed) as e:          # the mining role: a is held back (b is down too)
        r.run("mine", "p", None, ok_any, use_cache=False, only="a")
    assert e.value.tried[0][1] == "skipped" and a.calls == []
    out = r.run("probe", "p1", None, ok_any, use_cache=False)        # the probe goes through the open circuit
    assert out.backend == "a" and len(a.calls) == 1
    out = r.run("probe", "p2", None, ok_any, use_cache=False)        # a fails once: no transport retry, b answers
    assert out.backend == "b" and len(a.calls) == 2
    assert (r.health["a"].open_until, r.health["a"].consec, len(r.health["a"].events)) == before
    assert r.health["a"].probing is False                             # no half-open slot taken or left behind


def test_the_role_transport_retries_override_the_global_ones():
    a = H.FakeBackend("a", script=[BackendError("timeout", "t"), BackendError("timeout", "t"), "OK"])
    r = router_for(probe_cfg(chain=("a", "b")), [a, H.FakeBackend("b", script=[BackendError("network", "x")])])
    with pytest.raises(providers.AllBackendsFailed):
        r.run("probe", "p", None, ok_any, use_cache=False)
    assert len(a.calls) == 1                                          # global transport_retries 2; the role's 0
    a2 = H.FakeBackend("a", script=[BackendError("timeout", "t"), BackendError("timeout", "t"), "OK"])
    r2 = router_for(probe_cfg(chain=("a", "b")), [a2, H.FakeBackend("b")])
    assert r2.run("mine", "p", None, ok_any, use_cache=False).backend == "a" and len(a2.calls) == 3


def test_the_config_refuses_a_probe_another_vendor_could_answer():
    cfg = probe_cfg()
    cfg["backends"]["b"]["vendor"] = "local"
    with pytest.raises(ValueError, match="not of vendor"):
        providers.validate_config(cfg)
    cfg = probe_cfg()
    cfg["down_signal"]["probe_role"] = "nope"
    with pytest.raises(ValueError, match="probe_role"):
        providers.validate_config(cfg)


def test_the_live_config_wires_the_signal_to_heimdall_only():
    cfg = providers.load_config()
    ds = cfg["down_signal"]
    pr = cfg["roles"][ds["probe_role"]]
    assert pr["breaker"] is False and pr["transport_retries"] == 0 and pr["attempts"] == 1
    assert all(cfg["backends"][b]["vendor"] == ds["vendor"] and cfg["backends"][b]["timeout_s"] <= 60
               for b in pr["chain"])
    assert {cfg["backends"][b]["model"] for b in pr["chain"]} <= {b["model"] for b in cfg["backends"].values()
                                                                  if b.get("enabled", True)}


# ── the STATE head ──

def test_every_switch_opens_state_line_1_newest_first_on_one_physical_line(tmp_path):
    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
    doc.write_text("# STATE\nbody\n")
    spend.write_switch_head("21:47 ET: SWITCHED TO PLAN B (NO FAMILY FOR 15 MINUTES; BY PP-SELECTID) |", str(doc),
                            str(notify))
    spend.write_outage_notice(3, "2026-11-14T02:00:00Z", doc=str(doc), notify_path=str(notify))
    spend.write_switch_head("21:55 ET: BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW; BY PP-INGEST) |",
                            str(doc), str(notify))
    lines = doc.read_text().split("\n")
    assert lines[0] == ("21:55 ET: BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW; BY PP-INGEST) | "
                        "21:47 ET: SWITCHED TO PLAN B (NO FAMILY FOR 15 MINUTES; BY PP-SELECTID) |")
    assert lines[1].startswith(spend.OUTAGE_PREFIX) and lines[2:] == ["# STATE", "body", ""]
    spend.write_purge_notice("the spec is refused", "t", doc=str(doc), notify_path=str(notify))   # another notice
    spend.write_outage_notice(0, None, doc=str(doc), notify_path=str(notify))                        # one goes
    lines = doc.read_text().split("\n")
    assert spend.SWITCH_RE.match(lines[0]) and lines[1].startswith(spend.PURGE_PREFIX) and lines[2] == "# STATE"
    assert [json.loads(x).get("down_signal_switch", "")[:5] for x in notify.read_text().splitlines()
            if "down_signal_switch" in x] == ["21:47", "21:55"]
    with pytest.raises(ValueError):
        spend.write_switch_head("PLAN B", str(doc), str(notify))
    assert not os.path.exists(str(doc) + ".lock")                     # the notices' lock is beside NOTIFY.txt


def test_the_signal_notice_comes_and_goes_below_the_switch_line(tmp_path):
    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
    doc.write_text("# STATE\n")
    spend.write_switch_head("01:02 ET: SWITCHED TO PLAN B (X; BY PP-INGEST) |", str(doc), str(notify))
    spend.write_signal_notice("HealthUnreadable: bad json", "2026-11-14T06:00:00Z", doc=str(doc),
                              notify_path=str(notify), label="HV")
    lines = doc.read_text().split("\n")
    assert spend.SWITCH_RE.match(lines[0]) and lines[1].startswith("HV DOWN SIGNAL NOT READ since 2026-11-14T06:00")
    assert spend.NOTICE_RE.match(lines[1])
    spend.write_signal_notice(None, None, doc=str(doc), notify_path=str(notify), label="HV")
    assert doc.read_text() == "01:02 ET: SWITCHED TO PLAN B (X; BY PP-INGEST) |\n# STATE\n"


# ── the service ──

@pytest.fixture
def sig(monkeypatch, tmp_path):
    p = config.paths()
    for k in ("ingest", "moments"):
        shutil.rmtree(p[k], ignore_errors=True)
    doc = tmp_path / "STATE.md"
    doc.write_text("# STATE\nbody\n")
    monkeypatch.setattr(config, "STATE_DOC", str(doc))              # never the real STATE file
    t, made, msgs = [T0], [], []

    def make(module=MODULE, probe_enabled=True, probes=None):
        cfg = probe_cfg(chain=("hv_p1", "hv_p2"))
        cfg["backends"]["hv1"] = {"kind": "openai_compat", "vendor": "hv", "model": "model-hv1", "enabled": True}
        cfg["backends"]["local"] = {"kind": "openai_compat", "vendor": "lv", "model": "model-local", "enabled": True}
        for r in ("mine", "hook", "flagcheck", "judge"):
            cfg["roles"][r]["chain"] = ["hv1", "local"]
        cfg["spend_meter"]["backend"] = "hv1"
        cpath = tmp_path / "providers.json"
        cpath.write_text(json.dumps(cfg))
        probes = probes or {}
        backends = {"hv1": H.FakeBackend("hv1", fn=lambda p: "x"), "local": H.FakeBackend("local", fn=lambda p: "x")}
        for b in ("hv_p1", "hv_p2"):
            backends[b] = H.FakeBackend(b, fn=probes.get(b, lambda p: "OK"), enabled=probe_enabled)
        s = service.Service(providers_path=str(cpath), backends=backends, gate=H.FakeGate(), log=msgs.append,
                            keyring=providers.Keyring("/nonexistent"), sleep=lambda x: None, clock=lambda: t[0],
                            signal_module=module, signal_state=str(tmp_path / "HH.json"))
        made.append(s)
        return s, backends
    yield make, t, doc, tmp_path, msgs
    for s in made:
        s.close()


def state(tmp):
    return json.loads((tmp / "HH.json").read_text())


def rec(**k):
    return dict({"role": "mine", "backend": "hv1", "kind": "ok"}, **k)


def test_what_the_watcher_notes_and_what_it_does_not(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    hs = s.hsig
    assert hs.hh is not None and hs.state_path == str(tmp / "HH.json") and hs.up == "heimdall_first"
    for r in (rec(kind="cache"), rec(kind="disabled"), rec(role="probe", backend="hv_p1", kind="timeout"),
              rec(backend="local", kind="timeout")):
        s._on_attempt(r)
    assert hs.pending == {"answer": None, "fail": None, "drills": 0}
    hs.noted(rec(kind="timeout"))
    assert hs.pending["fail"] == T0 and hs.pending["answer"] is None
    t[0] += 10
    hs.noted(rec(kind="invalid"))                                     # the gateway answered: an answer
    assert hs.pending == {"answer": T0 + 10, "fail": None, "drills": 0}
    for k in ("network", "http_429", "overloaded", "server", "empty", "refusal", "http_auth", "http_4xx", "routing",
              "redirect"):
        t[0] += 1
        hs.noted(rec(kind=k))
    assert hs.pending == {"answer": T0 + 10, "fail": T0 + 11, "drills": 0}   # the first failure after the answer
    hs.tick(wait=True)
    st = state(tmp)
    assert st["notes"] == 2 and st["last_answer_utc"] == iso(T0 + 10) and st["failing_since_utc"] == iso(T0 + 11)
    assert hs.n["answers_noted"] == 1 and hs.n["failures_noted"] == 1 and st["mode"] == "heimdall_first"


def test_a_real_call_through_the_router_is_noted_and_a_stored_reply_is_not(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    s.router.run("mine", "p", None, lambda c: c)                      # a real call: noted
    assert s.hsig.pending["answer"] == T0
    s.hsig.tick(wait=True)
    s.router.run("mine", "p", None, lambda c: c)                      # the same prompt again: the stored reply
    assert s.hsig.pending["answer"] is None and len(b["hv1"].calls) == 1


def test_fifteen_minutes_without_an_answer_switch_to_plan_b_and_three_probe_answers_bring_it_back(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    hs = s.hsig
    hs.noted(rec(kind="timeout"))
    hs.tick(wait=True)                    # failing since T0; a probe is due: it answers (no verdict answer: the clock
    st = state(tmp)                       # runs on)
    assert st["failing_since_utc"] == iso(T0) and st["probe_streak"] == 1 and st["mode"] == "heimdall_first"
    assert len(b["hv_p1"].calls) == 1 and b["hv_p1"].calls[0] == downsignal.PROBE_PROMPT
    t[0] = T0 + 15 * 60
    hs.noted(rec(role="hook", kind="network"))
    hs.tick(wait=True)
    st = state(tmp)
    assert st["mode"] == "plan_b" and st["switches"][-1]["by"] == "pp-ingest" and hs.mode == "plan_b"
    switched = ("02:15 ET: SWITCHED TO PLAN B (NO HEIMDALL FAMILY ANSWERED INSIDE ITS DEADLINE FOR 15 MINUTES (SINCE "
                "2026-11-14T07:00:00Z); BY PP-INGEST); THE MINER'S PLAN B: QUEUE AND WAIT (SPEND FREEZE) |")
    assert doc.read_text() == switched + "\n# STATE\nbody\n"
    t[0] += 5
    hs.tick(wait=True)                                                # seen once: no second head
    assert doc.read_text() == switched + "\n# STATE\nbody\n"
    for _ in range(2):                                                # the probe every 2 minutes: 3 answers in a row
        t[0] += 121
        hs.tick(wait=True)
    st = state(tmp)
    assert st["mode"] == "heimdall_first" and st["failing_since_utc"] is None and hs.mode == "heimdall_first"
    back = "02:19 ET: BACK TO HEIMDALL-FIRST (THE PROBE ANSWERED 3 TIMES IN A ROW; BY PP-INGEST PROBE) |"
    assert doc.read_text() == back + " " + switched + "\n# STATE\nbody\n"
    assert st["notes"] == 2 and len(b["hv_p1"].calls) == 4            # probe calls are never notes; never stored
    kinds = [json.loads(x)["kind"] for x in open(s.p["signal"]).read().splitlines()]
    assert kinds.count("switch") == 2 and kinds.count("seen") == 2 and kinds.count("probe") == 4 and "wired" in kinds
    s.close()
    s2, b2 = make()                                                   # a restart announces nothing again
    s2.hsig.tick(wait=True)
    assert doc.read_text() == back + " " + switched + "\n# STATE\nbody\n"
    assert stats.live(s2.q, signal=s2.hsig.snapshot())["down_signal"]["switches_seen"] == "2"


def test_a_failed_probe_resets_the_streak_and_a_probe_nobody_could_answer_is_no_probe(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make(probes={"hv_p1": lambda p: BackendError("timeout", "t"), "hv_p2": lambda p: BackendError("server", "x")})
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)
    st = state(tmp)
    assert st["probe_streak"] == 0 and st["last_probe_utc"] == iso(T0) and s.hsig.last_probe["answered"] is False
    s.close()
    s2, b2 = make(probe_enabled=False)                                # both probe back-ends switched off: no call
    t[0] += 200
    s2.hsig.tick(wait=True)
    assert state(tmp)["last_probe_utc"] == iso(T0) and s2.hsig.n["probes_not_made"] == 1
    assert s2.hsig.last_probe["answered"] is None and b2["hv_p1"].calls == []


def test_a_drill_is_recorded_never_counted_and_no_probe_runs_through_it(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    ov = s.p["overrides"]
    with open(ov, "w") as f:
        json.dump({"hv1": {"base_url": "http://127.0.0.1:9"}}, f)
    s.hsig.noted(rec(kind="network"))
    s.hsig.tick(wait=True)
    st = state(tmp)
    assert st["drills"] == 1 and st["notes"] == 0 and st["failing_since_utc"] is None
    time.sleep(0.01)
    with open(ov, "w") as f:
        json.dump({"hv_p1": {"base_url": "http://127.0.0.1:9"}}, f)
    os.utime(ov, (time.time() + 5, time.time() + 5))                  # the mtime moves: the override is re-read
    s.hsig.noted(rec(kind="network"))                                  # a real failure: counted, a probe is due
    t[0] += 60
    s.hsig.tick(wait=True)
    assert state(tmp)["failing_since_utc"] == iso(T0)
    assert b["hv_p1"].calls == [] and any("no probe while" in m for m in msgs)
    os.remove(ov)
    t[0] += 60
    s.hsig.tick(wait=True)
    assert len(b["hv_p1"].calls) == 1


def test_an_unreadable_state_is_never_guessed_and_is_noticed_after_30_minutes(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    (tmp / "HH.json").write_text("{not json")
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)
    snap = s.hsig.snapshot()
    assert snap["mode"] is None and snap["not_read"] and snap["not_read_since"] == iso(T0)
    assert s.hsig.n["unnoted"] == 1
    s.hsig.check_notice()
    assert doc.read_text() == "# STATE\nbody\n"                     # not yet 30 minutes
    t[0] += downsignal.SIGNAL_NOTICE_S
    s.hsig.check_notice()
    assert doc.read_text().startswith("HV DOWN SIGNAL NOT READ since 2026-11-14T07:00:00Z: ")
    (tmp / "HH.json").write_text(json.dumps({"mode": "heimdall_first", "last_answer_utc": None,
                                            "failing_since_utc": None, "last_probe_utc": None, "probe_streak": 0,
                                            "switches": [], "notes": 0}))
    t[0] += 60
    s.hsig.tick(wait=True)
    s.hsig.check_notice()
    assert s.hsig.snapshot()["not_read"] is None and doc.read_text() == "# STATE\nbody\n"


def test_a_missing_module_is_said_and_noticed(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make(module=str(tmp / "nope" / "missing.py"))
    snap = s.hsig.snapshot()
    assert snap["wired"] is False and "cannot be loaded" in snap["not_read"]
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)                                            # nothing to call: no error raised
    t[0] += downsignal.SIGNAL_NOTICE_S
    s.hsig.check_notice()
    assert doc.read_text().startswith("HV DOWN SIGNAL NOT READ since ")
    assert not os.path.exists(tmp / "HH.json")


def test_the_miner_never_waits_on_the_shared_lock(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    lk = open(str(tmp / "HH.json") + ".lock", "w")
    fcntl.flock(lk, fcntl.LOCK_EX)                                    # another process holds the shared state
    try:
        t0 = time.monotonic()
        for _ in range(50):
            s._on_attempt(rec(kind="timeout", attempt=1))
        assert time.monotonic() - t0 < 1.0 and s.hsig.pending["fail"] == T0
        th = threading.Thread(target=s.hsig.tick, daemon=True)
        th.start()
        deadline = time.monotonic() + 5
        while s.hsig.busy_since is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert s.hsig.snapshot()["call_waiting_s"] == 0
        t[0] += downsignal.SIGNAL_NOTICE_S
        s.hsig.check_notice()                                         # the health thread is never blocked
        assert "a call into the shared state has not returned" in doc.read_text().split("\n")[0]
    finally:
        fcntl.flock(lk, fcntl.LOCK_UN)
        lk.close()
    th.join(timeout=10)
    assert not th.is_alive()
    s.hsig.check_notice()
    assert doc.read_text() == "# STATE\nbody\n" and state(tmp)["failing_since_utc"] == iso(T0)


def test_run_starts_the_signal_loop_only_when_configured(sig, monkeypatch):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    loops = {}

    class FakeThread:
        def __init__(self, target=None, args=(), daemon=None, name=None):
            loops[name] = args[2] if len(args) > 2 else None

        def start(self):
            pass

        def join(self, timeout=None):
            pass
    monkeypatch.setattr(service.threading, "Thread", FakeThread)
    s.stop.set()
    s.run()
    assert loops["signal"] == downsignal.SIGNAL_EVERY_S and {"watch", "mine", "hook", "check", "purge"} <= set(loops)
    assert any("ruling 87: the shared down signal wired to" in m for m in msgs)
