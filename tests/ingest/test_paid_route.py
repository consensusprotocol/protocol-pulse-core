"""Ruling 98 (orchestrator 06:13 ET Nov 14): the miner's Plan B. Heimdall down by ruling 87's signal for 20 minutes
-> NEW uploads only (the last 6 h, conversations first, then newest; no backfill, no hook pass) on the paid route
(the freeze lifted for this one role and its cap only: $2.00 a day, ET; here a test cap), back after 3 good probes,
every switch on STATE line 1, every row's miner_route, the paid route's videos mined again on Heimdall when it is
back. The builder's real module on a throw-away state file; fake back-ends (two of them on frozen vendors)."""
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

import helpers as H
from pipeline.ingest import config, mine, providers, service
from pipeline.ingest import queue as Q
from pipeline.ingest.providers import BackendError

MODULE = "/home/ultron/worktrees/pp-selectid/pipeline/heimdall_health.py"     # the builder's, read only
T0 = datetime(2026, 11, 14, 7, 0, tzinfo=timezone.utc).timestamp()            # 02:00 ET


def et(ts):
    return datetime.fromtimestamp(ts, providers.ET).strftime("%H:%M")


def paid_cfg():
    cfg = H.router_cfg(["hv1", "local"])
    cfg["backends"]["hv1"]["vendor"], cfg["backends"]["local"]["vendor"] = "hv", "lv"
    for b, v in (("hv_p1", "hv"), ("hv_p2", "hv"), ("px", "xv"), ("pg", "gv")):
        cfg["backends"][b] = {"kind": "openai_compat", "vendor": v, "model": f"model-{b}", "enabled": True}
    cfg["spend_freeze"] = {"vendors": ["xv", "gv"]}
    cfg["roles"]["probe"] = {"chain": ["hv_p1", "hv_p2"], "attempts": 1, "max_tokens": 64, "transport_retries": 0,
                             "breaker": False}
    cfg["roles"]["mine_paid"] = {"chain": ["px", "pg"], "attempts": 2, "max_tokens": 1000,
                                 "freeze_lifted": "ruling 98 (test)", "daily_cap_usd": 0.01, "cap_reserve_usd": 0.002}
    cfg["down_signal"] = {"vendor": "hv", "probe_role": "probe", "label": "HV", "module": MODULE}
    cfg["paid_route"] = {"role": "mine_paid", "after_down_s": 1200, "new_within_s": 21600,
                         "recheck_within_s": 43200, "conversation_tpm": 1.0, "label": "PX, THEN PG"}
    cfg["spend_meter"]["backend"] = "hv1"
    return cfg


def fakes(fn=lambda p: "x", probe_fn=lambda p: "OK"):
    b = {k: H.FakeBackend(k, fn=fn) for k in ("hv1", "local", "px", "pg")}
    b.update({k: H.FakeBackend(k, fn=probe_fn) for k in ("hv_p1", "hv_p2")})
    return b


# ── the router: the freeze lifted for one role, under its cap ──

def test_only_the_freeze_lifted_role_calls_a_frozen_vendor_and_never_starts_a_call_past_its_cap():
    b = fakes()
    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=b, sleep=lambda s: None,
                         role_spend=lambda role, since: 0.0)
    with pytest.raises(providers.AllBackendsFailed) as e:              # any other role: the freeze holds
        r.run("mine", "p", None, lambda c: c, use_cache=False, only="px")
    assert "spend freeze" in e.value.tried[0][2] and b["px"].calls == []
    n = 0                                                              # $0.001 a call, $0.002 held per call in
    while True:                                                        # flight, cap $0.01
        try:
            assert r.run("mine_paid", f"p{n}", None, lambda c: c, use_cache=False).backend == "px"
            n += 1
        except providers.AllBackendsFailed as stop:
            assert all(s == "skipped" and "daily cap" in w for _, s, w in stop.tried)
            break
    assert n == 9 and abs(r.caps.today("mine_paid") - 0.009) < 1e-9
    r2 = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=fakes(),
                          sleep=lambda s: None, role_spend=lambda role, since: 0.0095)   # the day's earlier spend
    with pytest.raises(providers.AllBackendsFailed):
        r2.run("mine_paid", "p", None, lambda c: c, use_cache=False)


def test_the_freeze_is_lifted_only_with_a_cap():
    cfg = paid_cfg()
    del cfg["roles"]["mine_paid"]["daily_cap_usd"]
    with pytest.raises(ValueError, match="freeze_lifted"):
        providers.validate_config(cfg)
    cfg = paid_cfg()
    cfg["paid_route"]["role"] = "mine"                                 # a route on a role without a cap
    with pytest.raises(ValueError, match="paid_route"):
        providers.validate_config(cfg)


def test_every_row_carries_the_role_that_mined_it():
    rec, meta = H.caption_record(H.vid(), n_rep=4)
    r = providers.Router(paid_cfg(), keyring=providers.Keyring("/nonexistent"), backends=fakes(fn=H.first_two),
                         sleep=lambda s: None)
    with ThreadPoolExecutor(4) as ex:
        paid, _ = mine.mine_video(r, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                  role="mine_paid", use_cache=False)
        heim, _ = mine.mine_video(r, ex, rec, meta, H.CHAN, [H.CHAN], datetime.now(timezone.utc), "c1",
                                  use_cache=False)
    assert paid and {l["miner_route"] for l in paid} == {"mine_paid"}
    assert {l["mined"]["backend"] for l in paid} == {"px"}
    assert heim and {l["miner_route"] for l in heim} == {"mine"}


# ── the service ──

@pytest.fixture
def paid(monkeypatch, tmp_path):
    p = config.paths()
    for k in ("ingest", "moments"):
        shutil.rmtree(p[k], ignore_errors=True)
    doc = tmp_path / "STATE.md"
    doc.write_text("# STATE\n")
    monkeypatch.setattr(config, "STATE_DOC", str(doc))                 # never the real STATE file
    t, made, msgs = [T0], [], []

    def make(probe_fn=lambda p: "OK"):
        cpath = tmp_path / "providers.json"
        cpath.write_text(json.dumps(paid_cfg()))
        b = fakes(probe_fn=probe_fn)
        s = service.Service(providers_path=str(cpath), backends=b, gate=H.FakeGate(), log=msgs.append,
                            keyring=providers.Keyring("/nonexistent"), sleep=lambda x: None, clock=lambda: t[0],
                            signal_module=MODULE, signal_state=str(tmp_path / "HH.json"))
        made.append(s)
        return s, b
    yield make, t, doc, tmp_path, msgs
    for s in made:
        s.close()


def test_the_paid_route_opens_after_20_minutes_down_says_its_cap_once_and_closes_when_the_signal_is_back(paid):
    make, t, doc, tmp, msgs = paid
    s, b = make(probe_fn=lambda p: BackendError("network", "down"))   # while down the probes fail too
    hs = s.hsig
    hs.noted({"role": "mine", "backend": "hv1", "kind": "timeout"})
    hs.tick(wait=True)
    t[0] = T0 + 15 * 60
    hs.noted({"role": "mine", "backend": "hv1", "kind": "timeout"})
    hs.tick(wait=True)
    assert json.loads((tmp / "HH.json").read_text())["mode"] == "plan_b" and hs.paid_open is False
    assert "PAID ROUTE" not in doc.read_text()                         # down 15 min: Plan B, the miner not yet
    assert "THE MINER'S PLAN B (RULING 98): NEW UPLOADS ON PX, THEN PG AFTER 20 MINUTES DOWN, CAPPED" in doc.read_text()
    t[0] = T0 + 20 * 60
    hs.tick(wait=True)
    assert hs.paid_open is True and s.q.kv_get("paid_route")["open"] is True
    assert doc.read_text().startswith(
        "02:20 ET: MINER ON THE PAID ROUTE (PX, THEN PG: NO HV ANSWER FOR 20 MINUTES, SINCE 2026-11-14T07:00:00Z; NEW "
        "UPLOADS OF THE LAST 6 H ONLY, CONVERSATIONS FIRST; CAP $0.01 A DAY, ET) | 02:15 ET: SWITCHED TO PLAN B")
    good = (tmp / "HH.json").read_text()
    (tmp / "HH.json").write_text("{not json")                         # a signal not read: no spend, the route kept
    t[0] += 5
    hs.tick(wait=True)
    assert hs.paid_open is False and s.q.kv_get("paid_route")["open"] is True
    (tmp / "HH.json").write_text(good)                                # read again at the next module call (mode,
    t[0] += 30                                                         # every 30 s): the route resumes
    hs.tick(wait=True)
    assert hs.paid_open is True
    s.router.caps.add("mine_paid", 0.009)                              # no further call fits under the cap
    t[0] += 5
    hs.tick(wait=True)
    t[0] += 5
    hs.tick(wait=True)
    assert doc.read_text().count("MINER PAID ROUTE CAP REACHED ($0.01 OF $0.01 TODAY, ET): QUEUE AND WAIT") == 1
    for k in ("hv_p1", "hv_p2"):                                       # Heimdall answers again: 3 good probes
        b[k].fn = lambda p: "OK"
    for _ in range(3):
        t[0] += 121
        hs.tick(wait=True)
    assert json.loads((tmp / "HH.json").read_text())["mode"] == "heimdall_first"
    assert hs.paid_open is False and hs.signal_back() is True
    line1 = doc.read_text().split("\n")[0]
    assert line1.startswith(f"{et(t[0])} ET: MINER OFF THE PAID ROUTE (BACK ON HV: THE SIGNAL IS BACK; ITS VIDEOS "
                            "STILL INSIDE 12 H ARE MINED AGAIN THERE) |")
    assert "BACK TO HEIMDALL-FIRST" in line1 and doc.read_text() == line1 + "\n# STATE\n"   # one physical line


def test_the_paid_route_mines_new_uploads_only_conversations_first(paid, monkeypatch):
    make, t, doc, tmp, msgs = paid
    s, b = make()
    now = t[0]
    rows = [{"video_id": "solo1h", "published_ts": now - 3600}, {"video_id": "conv2h", "published_ts": now - 7200},
            {"video_id": "old8h", "published_ts": now - 8 * 3600},
            {"video_id": "conv5h", "published_ts": now - 5 * 3600}]
    monkeypatch.setattr(s.q, "due", lambda states, limit=50: rows[:limit])

    class TS:
        @staticmethod
        def canonical_transcript(vid):
            return vid
    monkeypatch.setattr(service.config, "ts", lambda: TS)
    monkeypatch.setattr(service.mine, "episode_measure",
                        lambda rec: {"turns_per_min": 2.0 if rec.startswith("conv") else 0.1})
    assert [v["video_id"] for v in s._paid_due(s.cfg["paid_route"], 3)] == ["conv2h", "conv5h", "solo1h"]
    submitted = []
    monkeypatch.setattr(s.q, "claim", lambda vid, a, b_: True)
    monkeypatch.setattr(s.videos, "submit", lambda fn, *a: submitted.append(a))
    s.hsig.paid_open = True
    s.mine_once()
    assert [(v["video_id"], role) for v, role in submitted] == [("conv2h", "mine_paid"), ("conv5h", "mine_paid"),
                                                                ("solo1h", "mine_paid")]
    submitted.clear()
    s.inflight.clear()
    s.hsig.paid_open = False
    s.mine_once()                                                      # off the route: the normal order, the mine role
    assert [role for v, role in submitted] == [None, None, None]


def test_the_paid_routes_videos_are_mined_again_on_heimdall_once_it_is_back(paid, monkeypatch):
    make, t, doc, tmp, msgs = paid
    s, b = make()
    now = t[0]
    for vid, age, route in (("paid2h", 2, "mine_paid"), ("paid13h", 13, "mine_paid"), ("heim1h", 1, "mine")):
        s.q.add_video(vid, H.CHAN["channel_id"], "t", "uploads_playlist")
        s.q.set_state(vid, Q.MINED, next_at=now + 10 ** 9, published_ts=now - age * 3600, mine_route=route)
    pr = s.cfg["paid_route"]
    monkeypatch.setattr(s.hsig, "signal_back", lambda: False)
    s._queue_rechecks(pr)
    assert s.q.video("paid2h")["state"] == Q.MINED                    # not back yet: nothing queued
    monkeypatch.setattr(s.hsig, "signal_back", lambda: True)
    s._queue_rechecks(pr)
    v = s.q.video("paid2h")
    assert v["state"] == Q.TRANSCRIBED and v["recheck_ts"] == now and "ruling 98" in v["reason"]
    assert s.q.video("paid13h")["state"] == Q.MINED and s.q.video("heim1h")["state"] == Q.MINED
    s.q.set_state("paid2h", Q.MINED, next_at=now + 10 ** 9, mine_route="mine_paid")   # mined again, say on the
    s._queue_rechecks(pr)                                              # paid route once more: queued once only
    assert s.q.video("paid2h")["state"] == Q.MINED
