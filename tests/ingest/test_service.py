"""End to end with fakes: listing -> probe -> captions (the store's writer) -> mining -> ledger; the outage drill
(primary back-end dead: the fallback mines, nothing is lost; every back-end dead: videos wait, then complete)."""
import json
import os
import shutil

import pytest

import helpers as H
from pipeline.ingest import config, ledger, providers, service, watch
from pipeline.ingest import queue as Q
from pipeline.ingest.providers import BackendError


@pytest.fixture
def svc(monkeypatch, tmp_path):
    p = config.paths()
    for k in ("ingest", "moments"):
        shutil.rmtree(p[k], ignore_errors=True)
    cfg = H.router_cfg(["primary", "fallback"])
    cfg["backends"]["primary"]["spend_meter"] = "heimdall"
    cpath = tmp_path / "providers.json"
    cpath.write_text(json.dumps(cfg))
    monkeypatch.setattr(watch, "registry", lambda: ([H.CHAN], [H.CHAN]))
    monkeypatch.setattr(watch, "rss_canary", lambda chans: False)
    monkeypatch.setattr(service.spend, "write_state_notice", lambda *a, **k: None)
    ts = config.ts()

    def fake_captions(meta, work):
        rec, _ = H.caption_record(meta["video_id"], n_rep=8,     # distinct speech per video (else: a re-upload)
                                  lead=[f"Bitcoin show {meta['video_id']} opens with {i} new facts." for i in range(30)])
        return "ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])
    monkeypatch.setattr(ts, "fetch_captions", fake_captions)

    def make(primary_fn, fallback_fn, n_videos=3):
        now = __import__("time").time()
        vids = [H.vid("e") for _ in range(n_videos)]
        listing = {H.CHAN["channel_id"]: {"channel_id": H.CHAN["channel_id"], "entries": [
            {"id": v, "title": f"Bitcoin {v}", "timestamp": now - 1800, "live_status": None, "duration": 900,
             "url": f"https://www.youtube.com/watch?v={v}"} for v in vids]}}
        gate = H.FakeGate(listing=listing, probes={v: H.probe_json(v, timestamp=now - 1800, title=f"Bitcoin {v}")
                                                   for v in vids})
        backends = {"primary": H.FakeBackend("primary", fn=primary_fn, cfg={"spend_meter": "heimdall"},
                                             usage_total=1.0),
                    "fallback": H.FakeBackend("fallback", fn=fallback_fn)}
        s = service.Service(providers_path=str(cpath), backends=backends, gate=gate, log=lambda m: None,
                            keyring=providers.Keyring("/nonexistent"), sleep=lambda x: None)
        s.meter.measure()
        return s, vids, backends
    return make


def run_once(s):
    s.watch_once()
    while s.fetch_once(limit=20):
        pass
    while s.mine_once(wait=True):
        pass


def test_watch_fetch_mine_end_to_end(svc):
    s, vids, b = svc(H.first_two, H.first_two)
    run_once(s)
    for v in vids:
        row = s.q.video(v)
        assert row["state"] == Q.MINED and row["moments"] >= 1 and json.loads(row["miners"]) == {"primary": row["windows"]}
    lines, bad = ledger.read(s.p["ledger"])
    assert not bad and {l["video_id"] for l in lines} == set(vids)
    assert all(l["mined"]["backend"] == "primary" for l in lines)
    assert b["fallback"].calls == []
    live = s.health_once()
    assert live["videos_mined"] == 3 and live["moments"] == len(lines)


def test_outage_drill_primary_dead_fallback_mines_nothing_lost(svc):
    dead = lambda p: BackendError("network", "connection refused (dead URL)")   # noqa: E731
    s, vids, b = svc(dead, H.first_two)
    run_once(s)
    for v in vids:
        assert s.q.video(v)["state"] == Q.MINED
    lines, _ = ledger.read(s.p["ledger"])
    assert {l["video_id"] for l in lines} == set(vids) and {l["mined"]["backend"] for l in lines} == {"fallback"}
    assert s.router.health["primary"].snapshot()["open"] is True        # the breaker opened; later calls skip it
    calls = s.q.rows("SELECT backend, kind, COUNT(*) AS n FROM calls GROUP BY backend, kind")
    assert {(c["backend"], c["kind"]) for c in calls} >= {("primary", "network"), ("fallback", "ok")}


def test_every_back_end_dead_videos_wait_then_complete(svc):
    state = {"up": False}
    s, vids, b = svc(lambda p: H.first_two(p) if state["up"] else BackendError("network", "down"),
                     lambda p: H.first_two(p) if state["up"] else "not json")
    run_once(s)
    for v in vids:
        assert s.q.video(v)["state"] == Q.MINE_WAIT and "every back-end" in s.q.video(v)["reason"]
    assert ledger.read(s.p["ledger"])[0] == []                       # nothing half-written
    state["up"] = True
    for bid in ("primary", "fallback"):                               # the outage is over (breakers re-probed)
        s.router.health[bid].open_until = 0.0
    s.q.x("UPDATE videos SET next_at=0")
    while s.mine_once(wait=True):
        pass
    for v in vids:
        assert s.q.video(v)["state"] == Q.MINED, s.q.video(v)["reason"]
    assert {l["video_id"] for l in ledger.read(s.p["ledger"])[0]} == set(vids)


def test_a_restart_recovers_and_reuses_validated_replies(svc):
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    run_once(s)
    first = len(b["primary"].calls)
    s.q.x("UPDATE videos SET state=?", (Q.MINING,))                  # as if the process died mid-mining
    assert s.q.recover() == (0, 1)
    while s.mine_once(wait=True):
        pass
    assert len(b["primary"].calls) == first                          # every window from the reply cache
    assert s.q.video(vids[0])["state"] == Q.MINED


def test_the_heimdall_tripwire_falls_back_and_notifies(svc, monkeypatch):
    notes = []
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    monkeypatch.setattr(service.spend, "write_state_notice", lambda st, snap, **k: notes.append(st))
    b["primary"].usage_total = 99.0                                   # 99 of the test cap 100
    s.meter.measure()
    run_once(s)
    lines, _ = ledger.read(s.p["ledger"])
    assert lines and {l["mined"]["backend"] for l in lines} == {"fallback"} and notes == ["tripped"]
    assert s.q.video(vids[0])["state"] == Q.MINED                     # never halted
