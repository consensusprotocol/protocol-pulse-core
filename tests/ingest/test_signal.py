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
    s, b = make(probes={"hv_p1": lambda p: BackendError("timeout", "t"),
                        "hv_p2": lambda p: BackendError("server", "x")})
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)
    st = state(tmp)
    assert st["probe_streak"] == 0 and st["last_probe_utc"] == iso(T0) and s.hsig.last_probe["answered"] is False
    s.close()
    s2, b2 = make(probe_enabled=False)                                # both probe back-ends switched off: no call
    t[0] += 200
    s2.hsig.tick(wait=True)
    st = state(tmp)                                                   # no probe_result: the streak is untouched (the
    assert st["probe_streak"] == 0 and st["last_probe_utc"] in (iso(T0), iso(T0 + 200))   # builder's claim version
    assert s2.hsig.n["probes_not_made"] == 1 and s2.hsig.n["probes"] == 0   # stamps the slot it claimed at T0+200)
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
    for _ in range(12):                                               # 12 ticks, 2 of them asking the module
        t[0] += 5
        s.hsig.tick(wait=True)
    assert len([m for m in msgs if "is not read" in m]) == 1          # one cause, one log line (no churn)
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


# ── audit r87 cycle 1 ──

def test_a_switch_head_is_written_once_even_when_sent_again(tmp_path):
    """qwen P0: a restart between the STATE write and the count of switches seen re-sends the head: one copy."""
    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
    doc.write_text("# STATE\n")
    h = "01:02 ET: SWITCHED TO PLAN B (X; BY PP-INGEST) |"
    spend.write_switch_head(h, str(doc), str(notify))
    spend.write_switch_head(h, str(doc), str(notify))
    assert doc.read_text() == h + "\n# STATE\n"


def test_a_restart_before_the_count_was_kept_announces_nothing_twice(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)
    t[0] = T0 + 15 * 60
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)
    first = doc.read_text()
    assert first.startswith("02:15 ET: SWITCHED TO PLAN B")
    s.q.kv_set("signal_switches_seen", "0")                           # as if the process died before the count
    t[0] += 5
    s.hsig.tick(wait=True)
    assert doc.read_text() == first


def test_a_state_file_that_cannot_be_read_is_never_rewritten_from_nothing(tmp_path):
    """glm D21: only a missing STATE file starts empty; an unreadable one raises and keeps every line."""
    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
    doc.write_text("# STATE\nevery line of the session\n")
    os.chmod(doc, 0)
    try:
        with pytest.raises(OSError):
            spend.write_switch_head("01:02 ET: SWITCHED TO PLAN B (X; BY PP-INGEST) |", str(doc), str(notify))
        with pytest.raises(OSError):
            spend.write_outage_notice(2, "t", doc=str(doc), notify_path=str(notify))
    finally:
        os.chmod(doc, 0o644)
    assert doc.read_text() == "# STATE\nevery line of the session\n"
    missing = tmp_path / "NEW.md"
    spend.write_signal_notice("x", "t", doc=str(missing), notify_path=str(notify), label="HV")
    assert missing.read_text().startswith("HV DOWN SIGNAL NOT READ since t: x")


def test_a_signal_notice_under_an_earlier_label_is_still_removed(tmp_path):
    """glm D48: only the signal writes this notice, so any label's line is its own."""
    doc, notify = tmp_path / "STATE.md", tmp_path / "ingest" / "NOTIFY.txt"
    doc.write_text("# STATE\n")
    spend.write_signal_notice("x", "t", doc=str(doc), notify_path=str(notify), label="OLD")
    spend.write_signal_notice(None, None, doc=str(doc), notify_path=str(notify), label="NEW")
    assert doc.read_text() == "# STATE\n"


def test_a_finished_probe_is_reported_before_another_is_started(sig):
    """glm D18: a probe that finished after the last tick is reported first; no second probe in its slot."""
    make, t, doc, tmp, msgs = sig
    s, b = make()
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick()                                                     # a probe is due: started, not waited for
    s.hsig.probe_thread.join(timeout=10)                              # it finished between two ticks
    t[0] += downsignal.SIGNAL_MODE_S                                  # the next tick asks probe_due again
    s.hsig.tick()
    s.hsig.probe_thread.join(timeout=10)
    assert len(b["hv_p1"].calls) == 1 and s.hsig.n["probes"] == 1 and state(tmp)["last_probe_utc"] == iso(T0)


def test_an_unreadable_count_of_switches_seen_is_recorded_again(sig):
    """glm D19: a count that is not a number never raises on every tick."""
    make, t, doc, tmp, msgs = sig
    s, b = make()
    s.hsig.noted(rec(kind="timeout"))
    s.hsig.tick(wait=True)
    s.q.kv_set("signal_switches_seen", "abc")
    t[0] += 5
    s.hsig.tick(wait=True)
    assert s.q.kv_get("signal_switches_seen") == "0"


def test_an_error_seen_before_its_time_never_breaks_the_health_loop(sig):
    """muse Q6: the health thread reads the error and its time without the signal thread's lock."""
    make, t, doc, tmp, msgs = sig
    s, b = make()
    s.hsig.error, s.hsig.error_since = "HealthUnreadable: x", None   # the moment between the two assignments
    s.hsig.check_notice()                                             # no TypeError; not yet 30 minutes
    assert doc.read_text() == "# STATE\nbody\n"


# ── audit r87 cycle 2 ──

def test_a_probe_the_shared_state_did_not_take_is_kept_while_fresh_then_dropped(sig):
    """glm N1 (c2): a probe_result that fails keeps its outcome for the next tick (no new probe meanwhile) while it is
    younger than the probe interval; an older one is dropped and counted, never reported late."""
    make, t, doc, tmp, msgs = sig
    s, b = make()
    hs = s.hsig
    hs.noted(rec(kind="timeout"))
    hs.tick()                                                         # a probe starts (not waited for)
    hs.probe_thread.join(timeout=10)
    good = (tmp / "HH.json").read_text()
    (tmp / "HH.json").write_text("{not json")                         # the state goes unreadable before the report
    t[0] += 5
    hs.tick()
    assert hs.probe_out is not None and hs.n["probes"] == 0 and hs.last_probe["answered"] is True
    t[0] += downsignal.SIGNAL_MODE_S
    hs.tick()                                                         # still unreadable: kept, and no second probe
    assert len(b["hv_p1"].calls) == 1 and hs.probe_out is not None
    (tmp / "HH.json").write_text(good)
    t[0] += 5
    hs.tick()                                                         # readable again: reported with its own time
    assert hs.n["probes"] == 1 and state(tmp)["last_probe_utc"] == iso(T0) and state(tmp)["probe_streak"] == 1
    probes = [json.loads(x) for x in open(s.p["signal"]).read().splitlines() if '"probe"' in x]
    assert len(probes) == 1                                           # one evidence line for one probe
    t[0] += 200                                                       # a second probe; the state unreadable for good
    hs.tick()
    hs.probe_thread.join(timeout=10)
    (tmp / "HH.json").write_text("{not json")
    t[0] += 5
    hs.tick()
    t[0] += 130                                                       # older than the probe interval: dropped
    hs.tick()
    assert hs.probe_out is None and hs.n["probe_reports_lost"] == 1 and hs.n["probes"] == 1


def test_status_shows_the_watchers_view_of_the_signal(sig, capsys):
    """glm N5 (c2): `ingest_watch.py status` carries live.json's down_signal block with its age."""
    import importlib.util
    make, t, doc, tmp, msgs = sig
    s, b = make()
    stats.write_live(s.q, s.p["live"], signal=s.hsig.snapshot())
    spec = importlib.util.spec_from_file_location("ingest_watch_cli", os.path.join(config.REPO, "tools",
                                                                                     "ingest_watch.py"))
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    cli.cmd_status(type("A", (), {"hours": 24})())
    out = json.loads(capsys.readouterr().out)
    assert out["down_signal"]["wired"] is True and out["down_signal"]["from_live_json_age_s"] >= 0


# ── the builder's probe claim (pp-selectid 11ed255f, REQUESTS R12) ──

def test_the_probe_claims_its_slot_by_name_and_a_slot_claimed_by_another_prober_is_left_alone(sig):
    make, t, doc, tmp, msgs = sig
    s, b = make()
    hs = s.hsig
    if "who" not in downsignal.inspect.signature(hs.hh.probe_due).parameters:
        pytest.skip("the module at the builder's path predates the probe claim")
    assert hs.probe_kw == {"who": "pp-ingest probe"} and hs.snapshot()["probe_claimed_as"] == "pp-ingest probe"
    hs.noted(rec(kind="timeout"))
    hs.tick(wait=True)
    st = state(tmp)
    assert st["last_probe_by"] == "pp-ingest probe" and st["probe_streak"] == 1 and len(b["hv_p1"].calls) == 1
    t[0] += 130                                                       # the next slot: the builder's prober claims it
    assert hs.hh.probe_due(path=str(tmp / "HH.json"), now=datetime.fromtimestamp(t[0], timezone.utc),
                           who="pp-selectid probe") is True
    t[0] += 5
    hs.tick(wait=True)                                                # this watcher finds the slot taken: no probe
    assert len(b["hv_p1"].calls) == 1 and state(tmp)["last_probe_by"] == "pp-selectid probe"


def test_a_module_without_the_claim_is_called_without_a_name(sig, tmp_path):
    """The watcher loads the module once at start: an older module (125e7381) takes no `who` and must keep working."""
    import subprocess
    old = tmp_path / "old_module" / "heimdall_health.py"
    old.parent.mkdir()
    r = subprocess.run(["git", "-C", os.path.dirname(os.path.dirname(MODULE)), "show",
                        "125e7381:pipeline/heimdall_health.py"], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("the builder's 125e7381 is not reachable")
    old.write_text(r.stdout)
    make, t, doc, tmp, msgs = sig
    s, b = make(module=str(old))
    hs = s.hsig
    assert hs.hh is not None and hs.probe_kw == {} and hs.snapshot()["probe_claimed_as"] is None
    hs.noted(rec(kind="timeout"))
    hs.tick(wait=True)
    st = state(tmp)
    assert hs.snapshot()["not_read"] is None and st["probe_streak"] == 1 and "last_probe_by" not in st


def test_a_probe_due_whose_signature_cannot_be_read_is_called_without_a_name(sig, tmp_path):
    """Audit r87claim c1 (P3): inspect.signature raising (TypeError / ValueError) falls back to no `who`."""
    src = open(MODULE).read() + '''

class _Unsigned:                                  # inspect.signature raises TypeError on a non-Signature __signature__
    __signature__ = "broken"

    def __call__(self, path=STATE, now=None):
        return _probe_due_plain(path=path, now=now)


_probe_due_plain = probe_due
probe_due = _Unsigned()
'''
    mod = tmp_path / "unsigned" / "heimdall_health.py"
    mod.parent.mkdir()
    mod.write_text(src)
    make, t, doc, tmp, msgs = sig
    s, b = make(module=str(mod))
    hs = s.hsig
    with pytest.raises(TypeError):
        downsignal.inspect.signature(hs.hh.probe_due)
    assert hs.hh is not None and hs.probe_kw == {}
    hs.noted(rec(kind="timeout"))
    hs.tick(wait=True)                                                # probe_due called without `who`: it works
    assert hs.snapshot()["not_read"] is None and state(tmp)["probe_streak"] == 1 and len(b["hv_p1"].calls) == 1
