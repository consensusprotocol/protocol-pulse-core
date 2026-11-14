"""End to end with fakes: listing -> probe -> captions (the store's writer) -> mining -> ledger; the outage drill
(primary back-end dead: the fallback mines, nothing is lost; every back-end dead: videos wait without using a try,
however long, then complete); rejected windows (partial, retryable, never counted as mined); the spend freeze (a
frozen fallback is never called: the videos wait); one service per store."""
import json
import os
import shutil
from datetime import datetime, timezone

import pytest

import helpers as H
from pipeline.ingest import config, ledger, mine, providers, service, stats, watch
from pipeline.ingest import queue as Q
from pipeline.ingest.providers import BackendError


@pytest.fixture
def svc(monkeypatch, tmp_path):
    p = config.paths()
    for k in ("ingest", "moments"):
        shutil.rmtree(p[k], ignore_errors=True)
    cfg = H.router_cfg(["primary", "fallback"])
    cfg["backends"]["primary"]["spend_meter"] = True
    cpath = tmp_path / "providers.json"

    def write_cfg(freeze=()):
        c = json.loads(json.dumps(cfg))
        if freeze:
            c["spend_freeze"] = {"vendors": list(freeze)}
        cpath.write_text(json.dumps(c))
    write_cfg()
    monkeypatch.setattr(watch, "registry", lambda: ([H.CHAN], [H.CHAN]))
    monkeypatch.setattr(watch, "rss_canary", lambda chans: False)
    monkeypatch.setattr(service.spend, "write_state_notice", lambda *a, **k: None)
    monkeypatch.setattr(service.spend, "write_outage_notice", lambda *a, **k: None)    # never the real STATE file
    ts = config.ts()

    def fake_captions(meta, work):
        rec, _ = H.caption_record(meta["video_id"], n_rep=8,     # distinct speech per video (else: a re-upload)
                                  lead=[f"Bitcoin show {meta['video_id']} opens with {i} new facts." for i in range(30)])
        return "ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])
    monkeypatch.setattr(ts, "fetch_captions", fake_captions)

    def make(primary_fn, fallback_fn, n_videos=3, freeze=()):
        write_cfg(freeze)
        now = __import__("time").time()
        vids = [H.vid("e") for _ in range(n_videos)]
        listing = {H.CHAN["channel_id"]: {"channel_id": H.CHAN["channel_id"], "entries": [
            {"id": v, "title": f"Bitcoin {v}", "timestamp": now - 1800, "live_status": None, "duration": 900,
             "url": f"https://www.youtube.com/watch?v={v}"} for v in vids]}}
        gate = H.FakeGate(listing=listing, probes={v: H.probe_json(v, timestamp=now - 1800, title=f"Bitcoin {v}")
                                                   for v in vids})
        backends = {"primary": H.FakeBackend("primary", fn=primary_fn, cfg={"spend_meter": True},
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


def _again(s, n=1):
    """n more mining passes (the retry delay skipped; open circuits re-probed)."""
    for _ in range(n):
        s.q.x("UPDATE videos SET next_at=0 WHERE state IN (?,?)", (Q.MINE_WAIT, Q.MINED_PARTIAL))
        for h in s.router.health.values():
            h.open_until = 0.0
        while s.mine_once(wait=True):
            pass


def test_every_back_end_down_for_any_number_of_passes_waits_without_a_try_then_completes(svc):
    """Integrator B2: an outage (nothing answered) never uses a try and never becomes mined_partial, however long
    (the old code: 8 passes x 10 min = an 80 min outage turned into permanent, silent loss)."""
    state = {"up": False}
    down = lambda p: H.first_two(p) if state["up"] else BackendError("network", "down")    # noqa: E731
    s, vids, b = svc(down, lambda p: H.first_two(p) if state["up"] else BackendError("overloaded", "busy"))
    run_once(s)
    _again(s, 12)                                                     # 13 passes: past the old 8-pass limit
    for v in vids:
        row = s.q.video(v)
        assert row["state"] == Q.MINE_WAIT and row["reason"].startswith("OUTAGE") and row["mine_tries"] == 0
    assert ledger.read(s.p["ledger"])[0] == []                       # nothing half-written
    assert s.health_once()["mine_waiting_outage"] == 3
    state["up"] = True
    _again(s)
    for v in vids:
        assert s.q.video(v)["state"] == Q.MINED, s.q.video(v)["reason"]
    assert {l["video_id"] for l in ledger.read(s.p["ledger"])[0]} == set(vids)


def test_rejected_windows_become_partial_retryable_and_never_counted_as_mined(svc, monkeypatch):
    """A window every back-end answers wrongly: the good windows' moments go to the ledger after the content limit;
    the video stays retryable (MINE_DUE) and is never counted as mined; a later success completes it."""
    bad = {"on": True}

    def picky(p):
        ids = H.offered_ids(p)
        if bad["on"] and ids and ids[0] == 0:                         # the first window is always answered wrongly
            return "not json"
        return H.first_two(p)
    s, vids, b = svc(picky, picky, n_videos=1)
    vid = vids[0]
    run_once(s)
    assert s.q.video(vid)["state"] == Q.MINE_WAIT and s.q.video(vid)["mine_tries"] == 1
    _again(s, service.MINE_CONTENT_PASSES - 1)
    row = s.q.video(vid)
    assert row["state"] == Q.MINED_PARTIAL and row["windows_failed"] == 1 and row["next_at"] < s.clock() + 7 * 3600
    assert Q.MINED_PARTIAL in Q.MINE_DUE and Q.MINED_PARTIAL not in Q.TERMINAL
    n_partial = len(ledger.read(s.p["ledger"])[0])
    assert n_partial >= 1                                             # the good windows' moments are served now
    live = s.health_once()
    assert live["videos_mined"] == 0 and live["videos_partial"] == 1
    ids = {l["moment_id"] for l in ledger.read(s.p["ledger"])[0]}
    _again(s)                     # still rejected: the good windows' lines again (glm C2: every pass that mined
    lines = ledger.read(s.p["ledger"])[0]                                 # windows appends; the latest line wins)
    assert s.q.video(vid)["state"] == Q.MINED_PARTIAL and {l["moment_id"] for l in lines} == ids
    assert len(lines) == 2 * n_partial
    bad["on"] = False
    _again(s)
    assert s.q.video(vid)["state"] == Q.MINED
    assert s.health_once()["videos_mined"] == 1


def test_coverage_never_counts_a_partial_or_waiting_video_as_mined(svc, monkeypatch):
    from pipeline.ingest import coverage
    s, vids, b = svc(H.first_two, H.first_two, n_videos=3)
    run_once(s)
    s.q.x("UPDATE videos SET state=? WHERE video_id=?", (Q.MINED_PARTIAL, vids[0]))
    s.q.x("UPDATE videos SET state=? WHERE video_id=?", (Q.MINE_WAIT, vids[1]))
    now = __import__("time").time()
    monkeypatch.setattr(watch, "playlist_list", lambda gate, cid: [
        {"video_id": v, "title": "t", "ts": now - 1800, "url": f"https://www.youtube.com/watch?v={v}"} for v in vids])
    rep = coverage.check(s.q, s.gate, hours=24, rss=False, chans=[H.CHAN])
    assert rep["eligible"] == 3 and rep["mined"] == 1
    assert {m["video_id"] for m in rep["missed"]} == {vids[0], vids[1]}


def test_the_spend_freeze_never_falls_through_to_a_frozen_vendor_videos_wait_then_complete(svc):
    """Orchestrator 05:30: Heimdall then local only; both down = queue and mine later, never a paid frontier model."""
    state = {"up": False}
    s, vids, b = svc(lambda p: H.first_two(p) if state["up"] else BackendError("network", "connection refused"),
                     H.first_two, freeze=["vendor-fallback"])
    run_once(s)
    _again(s, 3)
    assert b["fallback"].calls == []                                  # frozen: never called, not once
    for v in vids:
        row = s.q.video(v)
        assert row["state"] == Q.MINE_WAIT and row["reason"].startswith("OUTAGE") and row["mine_tries"] == 0
        assert "spend freeze" in row["reason"]
    state["up"] = True
    _again(s)
    assert b["fallback"].calls == []
    for v in vids:
        assert s.q.video(v)["state"] == Q.MINED
    assert {l["mined"]["backend"] for l in ledger.read(s.p["ledger"])[0]} == {"primary"}
    calls = s.q.rows("SELECT DISTINCT backend FROM calls")
    assert {c["backend"] for c in calls} == {"primary"}


def test_one_service_per_store(svc):
    """Integrator (non-blocking): `once` beside `run` reset the live process's MINING rows (recover) and both
    appended. A second service on the same store is refused before it recovers anything."""
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    run_once(s)
    s.q.x("UPDATE videos SET state=? WHERE video_id=?", (Q.MINING, vids[0]))
    kw = dict(providers_path=s.providers_path, backends=b, gate=s.gate, log=lambda m: None,
              keyring=providers.Keyring("/nonexistent"))
    with pytest.raises(service.ServiceBusy):
        service.Service(**kw)
    assert s.q.video(vids[0])["state"] == Q.MINING                   # the live row was not touched
    s.close()
    s2 = service.Service(**kw)                                        # free again once the holder closed
    assert s2.q.video(vids[0])["state"] == Q.TRANSCRIBED             # recovered by the one service that holds it
    s2.close()


def test_the_tripwire_notifies_prefers_the_others_and_never_halts(svc, monkeypatch):
    notes = []
    s, vids, b = svc(H.first_two, H.first_two, n_videos=2)
    monkeypatch.setattr(service.spend, "write_state_notice", lambda st, snap, **k: notes.append((st, k.get("label"))))
    b["primary"].usage_total = 99.0                                   # 99 of the test cap 100
    s.meter.measure()
    run_once(s)
    lines, _ = ledger.read(s.p["ledger"])
    assert lines and {l["mined"]["backend"] for l in lines} == {"fallback"} and notes == [("tripped", "GW")]
    b["fallback"].cfg["enabled"] = False                              # no other back-end: the gateway keeps mining
    s.q.x("UPDATE videos SET state=?, next_at=0 WHERE video_id=?", (Q.TRANSCRIBED, vids[1]))
    while s.mine_once(wait=True):
        pass
    assert s.q.video(vids[1])["state"] == Q.MINED
    assert {l["mined"]["backend"] for l in ledger.read(s.p["ledger"])[0] if l["video_id"] == vids[1]} >= {"primary"}


def test_a_partial_videos_later_passes_append_what_they_mine_and_an_outage_keeps_the_count(svc):
    """Freeze audit c1 (glm C2, C24): a retry that mined windows appends its lines (the latest win); a retry in an
    outage (nothing mined) leaves the ledger and the recorded count as they are."""
    mode = {"m": "picky"}

    def fn(p):
        ids = H.offered_ids(p)
        if mode["m"] == "down":
            return BackendError("network", "down")
        if mode["m"] == "picky" and ids and ids[0] == 0:
            return "not json"
        return H.first_two(p)
    s, vids, b = svc(fn, lambda p: BackendError("overloaded", "busy"), n_videos=1)
    vid = vids[0]
    run_once(s)
    _again(s, service.MINE_CONTENT_PASSES - 1)
    row = s.q.video(vid)
    assert row["state"] == Q.MINED_PARTIAL and row["moments"] >= 1
    n_lines, moments = len(ledger.read(s.p["ledger"])[0]), row["moments"]
    s.router.cache_dir = None                                        # every window is asked again: an outage now
    mode["m"] = "down"
    _again(s)
    row = s.q.video(vid)
    assert row["state"] == Q.MINED_PARTIAL and row["moments"] == moments           # not overwritten with 0
    assert len(ledger.read(s.p["ledger"])[0]) == n_lines                            # nothing appended
    mode["m"] = "ok"
    _again(s)
    assert s.q.video(vid)["state"] == Q.MINED and len(ledger.read(s.p["ledger"])[0]) > n_lines


def test_a_stop_inside_a_fetch_never_strands_the_video_in_probing(svc, monkeypatch):
    """Freeze audit c1 (glm C8): a BaseException out of fetch.process left the video `probing` until a restart."""
    from pipeline.ingest import fetch

    class Stop(BaseException):
        pass
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    s.watch_once()

    def boom(*a, **k):
        raise Stop("gpu0 stop")
    monkeypatch.setattr(fetch, "process", boom)
    with pytest.raises(Stop):
        s.fetch_once(limit=5)
    row = s.q.video(vids[0])
    assert row["state"] == Q.PROBE_RETRY and "fetch stopped: Stop" in row["reason"]


def test_an_outage_longer_than_the_notice_delay_is_noticed_then_cleared(svc, monkeypatch):
    notes = []
    s, vids, b = svc(lambda p: BackendError("network", "down"), lambda p: BackendError("overloaded", "busy"))
    monkeypatch.setattr(service.spend, "write_outage_notice", lambda n, since, **k: notes.append((n, since)) or "x")
    run_once(s)
    s.health_once()
    assert s.q.kv_get("outage_since") and notes == []                 # waiting, but not yet for 30 min
    s.q.kv_set("outage_since", str(s.clock() - service.OUTAGE_NOTICE_S - 1))
    s.health_once()
    assert notes and notes[-1][0] == 3
    s.q.x("UPDATE videos SET state=?, reason=NULL", (Q.MINED,))       # the outage is over
    s.health_once()
    assert notes[-1] == (0, None) and not s.q.kv_get("outage_since")


def test_an_unmeasured_coverage_report_is_tried_again_the_same_day(svc, monkeypatch):
    from pipeline.ingest import coverage as C
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    calls = []

    def check(q, gate, hours=24, now_ts=None, rss=None, chans=None):
        calls.append(1)
        return {"at": config.iso(), "hours": 24, "listing": "rss", "channels": 1, "measured": len(calls) > 1,
                "unmeasured_channels": [] if len(calls) > 1 else [{"channel": "x", "channel_id": "y", "error": "e"}],
                "published": 0, "shorts": 0, "eligible": 0, "mined": 0, "missed": [], "per_channel": {},
                "coverage": None}
    monkeypatch.setattr(C, "check", check)
    monkeypatch.setattr(C, "write", lambda rep, out: "/dev/null")
    monkeypatch.setattr(service, "COVERAGE_HOUR_UTC", 0)
    s.health_once()
    assert len(calls) == 1 and s.q.kv_get("coverage_day") != config.iso()[:10]     # unmeasured: not done
    s.health_once()
    assert len(calls) == 1                                             # waits COVERAGE_RETRY_S
    s.q.kv_set("coverage_next_try", "0")
    s.health_once()
    assert len(calls) == 2 and s.q.kv_get("coverage_day") == config.iso()[:10]


def test_the_queue_has_the_indexes_the_per_video_cost_and_the_spend_read_need(svc):
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    names = {r["name"] for r in s.q.rows("SELECT name FROM sqlite_master WHERE type='index'")}
    assert {"calls_video", "calls_backend"} <= names


def test_the_local_model_is_released_only_after_an_idle_spell(svc, monkeypatch):
    """Freeze audit c2 (glm N1): releasing on every quiet 5 s reloads the model on the next video; now only after
    IDLE_RELEASE_S without mining due."""
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    released = []
    monkeypatch.setattr(s.router, "release", lambda: released.append(s.clock()))
    run_once(s)                                                     # mining happened just now
    assert s.mine_once() == 0 and released == []
    s._last_mining = s.clock() - service.IDLE_RELEASE_S - 1
    assert s.mine_once() == 0 and len(released) == 1


def test_a_partial_videos_count_is_its_distinct_moments_in_the_ledger(svc):
    """Freeze audit c2 consensus (qwen, glm N2, muse N4): the row's count was the last pass's lines only."""
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    run_once(s)
    vid = vids[0]
    lines = [l for l in ledger.read(s.p["ledger"])[0] if l["video_id"] == vid]
    s.q.x("UPDATE videos SET moments=1 WHERE video_id=?", (vid,))
    assert s._ledger_count(s.q.video(vid)) == len({l["moment_id"] for l in lines}) >= 1


def test_the_watcher_runs_the_purge_in_its_own_loop_and_a_refused_spec_deletes_nothing(svc, monkeypatch):
    """Ruling 77: no cron; the purge is one of the service's loops (every purge.json every_s), its last pass in
    live.json; a spec that does not load deletes nothing and says so."""
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    assert s.purge_spec is not None and s.purge_spec["every_s"] == 600
    seen = []
    monkeypatch.setattr(service.purge, "run_pass", lambda spec, **kw: seen.append(kw) or {
        "at": "t", "dry_run": False, "deleted": {"run_sources": {"files": 2, "bytes": 5}}, "kept": {}, "problems": [],
        "delivered_runs": [], "delivered_videos": 0, "freed_bytes": 5, "seconds": 0.1})
    s.purge_once()
    assert seen and seen[0]["log_dir"] == s.p["purge"] and float(s.q.kv_get("purge_freed_total")) == 5
    live = stats.live(s.q, meter=s.meter, router=s.router)
    assert live["purge"]["freed_total_bytes"] == 5 and live["purge"]["last_pass"]["deleted"]["run_sources"]["files"] == 2
    msgs = []
    s.log = msgs.append
    s.purge_spec, s.purge_error = None, "SpecError: bad"
    seen.clear()
    assert s.purge_once() is None and not seen and "nothing deleted" in msgs[-1]
    loops = {}

    class FakeThread:                                   # records the loops run() starts, runs none of them
        def __init__(self, target=None, args=(), daemon=None, name=None):
            loops[name] = args[2] if len(args) > 2 else None

        def start(self):
            pass

        def join(self, timeout=None):
            pass
    monkeypatch.setattr(service.threading, "Thread", FakeThread)
    s.purge_spec = service.purge.load_spec()
    s.stop.set()
    s.run()
    assert loops["purge"] == 600.0 and {"watch", "fetch", "mine", "health"} <= set(loops)


def test_a_purge_that_cannot_run_safely_for_30_min_is_noticed_at_the_top_of_state(svc, monkeypatch, tmp_path):
    """Audit r77 c1 (muse P1): a refused purge must not be silent; the notice goes when a pass runs again."""
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    doc = tmp_path / "STATE.md"
    doc.write_text("# STATE\nbody\n")
    monkeypatch.setattr(config, "STATE_DOC", str(doc))
    refused = {"at": "t", "dry_run": False, "deleted": {}, "kept": {}, "problems": ["/proc not readable"],
               "delivered_runs": [], "delivered_videos": 0, "freed_bytes": 0, "refused": "nothing deleted: /proc"}
    monkeypatch.setattr(service.purge, "run_pass", lambda spec, **kw: dict(refused))
    s.purge_once()
    assert not doc.read_text().startswith("PURGE NOT RUNNING")          # not yet 30 min
    s.q.kv_set("purge_blocked_since", str(s.clock() - service.PURGE_NOTICE_S - 1))
    s.purge_once()
    assert doc.read_text().startswith("PURGE NOT RUNNING since ")
    ok = dict(refused, refused=None, problems=[])
    monkeypatch.setattr(service.purge, "run_pass", lambda spec, **kw: dict(ok))
    s.purge_once()
    assert doc.read_text() == "# STATE\nbody\n"


def test_the_hook_pass_mines_the_12_h_window_newest_first_and_its_rows_carry_earlier_flags(svc, monkeypatch):
    """Ruling 80: after the moment pass, the hook loop asks the hook question of every mined video published in the
    last 12 h, newest first; its rows are moments with role_hint 'hook'; the same span's earlier flags are carried,
    so a hook the moment pass flagged is still excluded; a video older than 12 h is never hook-mined."""
    def fn(prompt):
        if H.is_spot(prompt):                                           # unmarked captions: asked since 09:02 (A36)
            return json.dumps({"spotlights": []})
        if H.is_hook(prompt):
            return H.hooks_reply(prompt, ((0, 1), (2, 3)))
        ids = H.offered_ids(prompt)
        return H.reply([H.moment(ids[0], ids[1], risk=["accusation"])])  # the moment pass flags the first span
    s, vids, b = svc(fn, fn, n_videos=3)
    run_once(s)
    old = vids[2]
    s.q.x("UPDATE videos SET published_ts=? WHERE video_id=?", (s.clock() - 13 * 3600, old))
    s.q.x("UPDATE videos SET published_ts=published_ts+60 WHERE video_id=?", (vids[1],))     # vids[1] is the newest
    due = [v["video_id"] for v in s.q.hook_due(service.HOOK_HORIZON_S)]
    assert due[0] == vids[1] and old not in due
    while s.hook_once(wait=True):
        pass
    for v in vids[:2]:
        row = s.q.video(v)
        assert row["hook_ts"] and row["hook_rows"] >= 2 and row["hook_cost_usd"] is not None
    assert s.q.video(old)["hook_ts"] is None
    lines = ledger.read(s.p["ledger"])[0]
    latest = {}
    for l in lines:
        latest[l["moment_id"]] = l
    hooks = [l for l in latest.values() if l.get("role_hint") == "hook"]
    assert hooks and {l["video_id"] for l in hooks} == set(vids[:2])
    flagged = [l for l in hooks if l["sentences"] == latest[l["moment_id"]]["sentences"] and "accusation" in l["risk"]]
    assert flagged                                                  # the span the moment pass flagged keeps it
    out, rep = ledger.best_unused_moments(s.p["ledger"], datetime.fromtimestamp(s.clock() - 3600, timezone.utc),
                                          registry=[H.CHAN], optout=(), store_root=s.p["root"])
    assert any(l.get("role_hint") == "hook" for l in out)           # returned like any row
    assert not [l for l in out if "accusation" in l["risk"]]        # never a hard-flagged one
    assert s.hook_once(wait=True) == 0                              # done: not asked again


def test_a_hook_pass_in_an_outage_waits_without_using_a_try(svc):
    s, vids, b = svc(H.first_two_and_hooks, H.first_two_and_hooks, n_videos=1)
    run_once(s)
    b["primary"].fn = b["fallback"].fn = lambda p: providers.BackendError("network", "down")
    s.hook_once(wait=True)
    row = s.q.video(vids[0])
    assert row["hook_ts"] is None and not row["hook_tries"] and row["hook_next_ts"] > s.clock()
    assert row["hook_note"].startswith("OUTAGE")


def _checker(rows_answer="no", probes_right=True):
    """The second model in the service tests: answers the calibration quotes (right, or one wrong) and every row's
    question with rows_answer; everything else like a miner."""
    import re
    from pipeline.ingest import flagcheck as FC
    gold = {t: g for _, g, t in FC.PROBES}

    def fn(prompt):
        if "You answer ONE narrow question" not in prompt:
            return H.first_two_and_hooks(prompt)
        q = re.search(r"QUOTE: (.*)\n</quote>", prompt).group(1)
        ans = gold.get(q, rows_answer)
        if not probes_right and q == FC.PROBES[0][2]:
            ans = "no"
        ev = q.split()[0] if ans == "yes" else ""
        return json.dumps({"answer": ans, "evidence": ev, "why": "w"})
    return fn


def _flagging_miner(prompt):
    if H.is_hook(prompt):
        return H.hooks_reply(prompt)
    ids = H.offered_ids(prompt)
    return H.reply([H.moment(ids[0], ids[1], risk=["imperative"])])


def test_the_watcher_asks_the_second_model_and_the_adapter_releases_a_no(svc):
    """Ruling 40 P1 end to end: a moment the miner flagged imperative is asked of the second model (a model other than
    the miner's, calibrated first); its "no" goes into a new line of the moment; the adapter returns the moment with
    the label as a note."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    since = datetime.fromtimestamp(s.clock() - 3600, timezone.utc)
    out, rep = ledger.best_unused_moments(s.p["ledger"], since, registry=[H.CHAN], optout=(), store_root=s.p["root"])
    assert out == [] and rep["excluded"]["hard exclusion flag (L-u)"] >= 1          # flagged: excluded
    while s.check_once(wait=True):
        pass
    assert s.check_allowed == ["fallback"]                                        # the miner's back-end never checks
    out, rep = ledger.best_unused_moments(s.p["ledger"], since, registry=[H.CHAN], optout=(), store_root=s.p["root"])
    assert out and all(l["risk"] == [] and l["risk_notes"][0]["flag"] == "imperative" for l in out)
    assert rep["released_by_the_second_model"] == len(out)
    assert s.check_once(wait=True) == 0                                           # answered: not asked again


def test_a_checker_that_misses_a_calibration_quote_never_releases_anything(svc):
    s, vids, b = svc(_flagging_miner, _checker("no", probes_right=False), n_videos=1)
    run_once(s)
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    since = datetime.fromtimestamp(s.clock() - 3600, timezone.utc)
    out, _ = ledger.best_unused_moments(s.p["ledger"], since, registry=[H.CHAN], optout=(), store_root=s.p["root"])
    assert out == []


def test_f1_a_calibration_an_outage_left_unanswered_is_tried_again_soon_and_the_wait_doubles(svc):
    """F1 (Nov 14): the calibration is asked live, so an outage can leave it unanswered. Then no checker may answer
    (nothing measured is never a pass), but the next calibration comes after CHECK_RETRY_S, not a day later, the wait
    doubling while it keeps failing; once one passes, the daily calibration again, and the flags are checked."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    good = b["fallback"].fn
    b["fallback"].fn = lambda p: providers.BackendError("network", "down")
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    assert s.check_recal_s == service.CHECK_RETRY_S
    n = len(b["fallback"].calls)
    s.check_once(wait=True)                                          # not due yet: nothing asked
    assert len(b["fallback"].calls) == n and s.check_recal_s == service.CHECK_RETRY_S

    def due():
        s.check_calibrated -= s.check_recal_s
        for h in s.router.health.values():
            h.open_until = 0.0
    due()
    assert s.check_once(wait=True) == 0 and s.check_allowed == []   # still down: asked again, the wait doubles
    assert len(b["fallback"].calls) > n and s.check_recal_s == 2 * service.CHECK_RETRY_S
    b["fallback"].fn = good                                          # back
    due()
    while s.check_once(wait=True):
        pass
    assert s.check_allowed == ["fallback"] and s.check_recal_s == service.CHECK_RECALIBRATE_S
    cal = json.loads(s.q.kv_get("check_calibration"))
    assert cal["fallback"]["right"] == cal["fallback"]["of"] == 16 and cal["fallback"]["asked_at"]
    assert cal["fallback"]["wrong"] == [] and cal["fallback"]["seconds"] >= 0
    since = datetime.fromtimestamp(s.clock() - 3600, timezone.utc)
    out, rep = ledger.best_unused_moments(s.p["ledger"], since, registry=[H.CHAN], optout=(), store_root=s.p["root"])
    assert out and rep["released_by_the_second_model"] == len(out)


def test_f1_a_checker_that_answers_a_quote_wrong_waits_for_the_daily_calibration(svc):
    """A calibration every back-end answered in full, with a quote answered wrong, bars them until the daily one (at
    temperature 0 a model answers a known quote the same way again: no quick retry)."""
    s, vids, b = svc(_checker("no", probes_right=False), _checker("no", probes_right=False), n_videos=1)
    run_once(s)
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    assert s.check_recal_s == service.CHECK_RECALIBRATE_S
    cal = json.loads(s.q.kv_get("check_calibration"))                 # the wrong answer is kept (audit f1 c1, glm)
    from pipeline.ingest import flagcheck as FC
    for bid in ("primary", "fallback"):
        assert [(w["flag"], w["gold"], w["answer"]) for w in cal[bid]["wrong"]] == [("imperative", "yes", "no")]
        assert cal[bid]["wrong"][0]["text"] == FC.PROBES[0][2][:80]


def test_f1_a_calibration_that_crashes_fails_closed_and_waits_like_an_unanswered_one(svc, monkeypatch):
    """Audit f1 c1 (glm): a calibration that raises (say after its live calls) must not run again every 30 s. Nobody
    answers (nothing measured; the earlier allowance is not kept), the stored calibration is emptied, the crash is an
    event, and the next calibration comes after CHECK_RETRY_S, the wait doubling."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    while s.check_once(wait=True):
        pass
    assert s.check_allowed == ["fallback"]
    calls = []

    def boom(router, *a, **k):
        calls.append(1)
        raise RuntimeError("a regression after the live calls")
    monkeypatch.setattr(service.flagcheck, "watcher_checkers", boom)
    s.check_calibrated -= s.check_recal_s                               # the daily calibration is due
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    assert s.check_recal_s == service.CHECK_RETRY_S and json.loads(s.q.kv_get("check_calibration")) == {}
    s.check_once(wait=True)
    assert calls == [1]                                                  # not again on the next 30 s loop
    s.check_calibrated -= s.check_recal_s
    assert s.check_once(wait=True) == 0
    assert calls == [1, 1] and s.check_recal_s == 2 * service.CHECK_RETRY_S
    assert s.q.rows("SELECT COUNT(*) AS n FROM events WHERE kind='check_calibration_crash'")[0]["n"] == 2
    ck = s.health_once()["second_model_checks_12h"]                      # audit f1 c2 (glm N4): visible live
    assert ck["calibration_crashes"] == 2 and ck["calibration"] == {}


def test_f1_a_calibration_with_no_back_end_to_ask_is_tried_again_soon(svc):
    """Audit f1 c2 (muse): when no back-end of the role can be called (both frozen here; a checker under the GPU0
    lease could be absent for a while), the calibration asks nothing and nobody answers, and the next one comes after
    CHECK_RETRY_S, not a day later (it costs no call)."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1, freeze=["vendor-primary", "vendor-fallback"])
    assert s.check_once(wait=True) == 0 and s.check_allowed == []
    assert s.check_recal_s == service.CHECK_RETRY_S
    assert b["primary"].calls == [] and b["fallback"].calls == []
    assert json.loads(s.q.kv_get("check_calibration")) == {}


def _asked_calibration(backend):
    from pipeline.ingest import flagcheck as FC
    quotes = [t for _, _, t in FC.watcher_probes()]
    return [p for p in backend.calls if any(q in p for q in quotes)]


def test_a_restart_within_a_day_keeps_the_live_calibration_and_asks_nothing(svc):
    """09:16 ET Nov 14: each restart's live calibration ended on muse's 502s, and a quiet watcher turned that dangling
    failure into a false plan_b. A restart within a day of the last LIVE calibration keeps its measured result (its
    asked_at, the same back-ends and models, at least one passed) and asks no quote; the next calibration stays due a
    day after the live one."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    while s.check_once(wait=True):
        pass
    assert s.check_allowed == ["fallback"] and _asked_calibration(b["fallback"])
    first = s.check_calibrated
    s.close()
    s2, _, b2 = svc(_flagging_miner, _checker("no"), n_videos=1)
    s2.check_once(wait=True)
    assert s2.check_allowed == ["fallback"] and not _asked_calibration(b2["fallback"])
    assert abs(s2.check_calibrated - first) < 60 and s2.check_recal_s == service.CHECK_RECALIBRATE_S
    assert s2.q.rows("SELECT COUNT(*) AS n FROM events WHERE kind='check_calibration_reused'")[0]["n"] == 1


@pytest.mark.parametrize("edit", ["old", "model", "no_asked_at", "none_passed"])
def test_a_restart_asks_live_when_the_stored_calibration_is_old_changed_or_failed(svc, edit):
    """Anything but a live, under-a-day, same-model calibration with a back-end that passed is asked again at start:
    an old one, a changed model, the record of the cached era (no asked_at), one in which nobody passed."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    while s.check_once(wait=True):
        pass
    cal = json.loads(s.q.kv_get("check_calibration"))
    old = datetime.fromtimestamp(s.clock() - 25 * 3600, timezone.utc).isoformat()   # ONE time, as a calibration stores
    for c in cal.values():
        if edit == "old":
            c["asked_at"] = old
        elif edit == "model":
            c["model"] = "another-model"
        elif edit == "no_asked_at":
            c.pop("asked_at")
        else:
            c["right"] = c["of"] - 1
    s.q.kv_set("check_calibration", json.dumps(cal))
    s.close()
    s2, _, b2 = svc(_flagging_miner, _checker("no"), n_videos=1)
    s2.check_once(wait=True)
    assert _asked_calibration(b2["fallback"]) and s2.check_allowed == ["fallback"]
    assert s2.q.rows("SELECT COUNT(*) AS n FROM events WHERE kind='check_calibration_reused'")[0]["n"] == 0


def test_an_unanswered_question_records_nothing_and_waits(svc):
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    s.check_allowed, s.check_calibrated = ["fallback"], s.clock()
    b["fallback"].fn = lambda p: providers.BackendError("network", "down")
    assert s.check_once(wait=True) >= 1
    assert not [l for l in ledger.read(s.p["ledger"])[0] if l.get("risk_checks")]
    assert s.check_once(wait=True) == 0                                           # retried only after CHECK_RETRY_S


def test_the_check_loop_does_not_reread_an_unchanged_ledger(svc, monkeypatch):
    """Audit r40p1 c1 (glm): every 30 s the loop re-parsed a day of ledger; now only when the ledger changed or a
    retry is due."""
    s, vids, b = svc(_flagging_miner, _checker("no"), n_videos=1)
    run_once(s)
    while s.check_once(wait=True):
        pass
    s.check_once(wait=True)                               # sees the checked lines; nothing left to start
    monkeypatch.setattr(service.ledger, "read", lambda *a, **k: (_ for _ in ()).throw(AssertionError("re-read")))
    assert s.check_once(wait=True) == 0


def _every_question(prompt):
    """The miner answering every question: the moment pass its first two ids; the hook question as many hooks as it
    allows (5 in a conversation, else 3); the spotlight question two 4-sentence spans (16 s at 4 s a sentence)."""
    flat = " ".join(prompt.split())
    if H.is_spot(prompt):                     # spans that START on a '>>' sentence (3, 7: the test's markers fall on
        return H.spots_reply(prompt, ((3, 6), (7, 10)))   # every 4th): one speaker inside, so the adapter keeps them
    if H.is_hook(prompt):
        n = 5 if "1 to 5 lines" in flat else 3
        return H.hooks_reply(prompt, tuple((i, i) for i in range(n)))
    return H.first_two(prompt)


def test_the_hook_pass_of_a_conversation_asks_5_hooks_and_the_spotlight_question_a_solo_one_neither(svc,
                                                                                                    monkeypatch):
    """The orchestrator's 08:15 ruling 2 (ruling 92 (b) + (c)) as widened at 09:02 (A36): a conversation is asked for
    up to 5 hooks a window and the spotlight question (its rows: role_hint "spotlight", 12-35 s); a MARKED solo episode
    (under 0.3 caption turns a minute) keeps 3 hooks and is never asked the spotlight question. The pass's version, its
    spotlight rows and its cost (both roles) are recorded; live.json counts them."""
    s, vids, b = svc(_every_question, _every_question, n_videos=2)
    conv = vids[0]
    ts = config.ts()

    def captions(meta, work):
        v = meta["video_id"]
        mark = (lambda i: i % 4 == 3) if v == conv else (lambda i: i == 1)    # the other: ONE marker in 5.7 min
        lead = [(">> " if mark(i) else "") + f"Bitcoin show {v} opens with {i} new facts." for i in range(30)]
        rec, _ = H.caption_record(v, n_rep=8, lead=lead)
        return "ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])
    monkeypatch.setattr(ts, "fetch_captions", captions)
    run_once(s)
    while s.hook_once(wait=True):
        pass
    rows = [l for l in ledger.read(s.p["ledger"])[0]]
    c, o = s.q.video(conv), s.q.video(vids[1])
    assert c["episode_tpm"] >= mine.CONVERSATION_TPM > o["episode_tpm"] > 0 and o["episode_markers"] == 1
    assert c["hook_version"] == o["hook_version"] == mine.HOOK_PROMPT_VERSION == "mine-hook/4"
    spots = [l for l in rows if l.get("role_hint") == "spotlight"]
    assert spots and {l["video_id"] for l in spots} == {conv} and c["spot_rows"] == len(spots) and o["spot_rows"] is None
    assert all(12.0 <= l["duration_estimate_s"] <= 35.0 and l["mined"]["pass"] == "spotlight" for l in spots)
    per_window = {}
    for l in rows:
        if l.get("role_hint") == "hook" and l["mined"]["pass"] == "hook":
            per_window.setdefault((l["video_id"], tuple(l["mined"]["window"])), set()).add(tuple(l["sentences"]))
    assert max(len(v) for (vid, _), v in per_window.items() if vid == conv) == 5
    assert max(len(v) for (vid, _), v in per_window.items() if vid != conv) == 3
    calls = s.q.rows("SELECT video_id, role, COUNT(*) AS n, SUM(cost_usd) AS usd FROM calls WHERE role IN ('hook', "
                     "'spotlight') GROUP BY video_id, role")
    assert {(r["video_id"], r["role"]) for r in calls} == {(conv, "hook"), (conv, "spotlight"), (vids[1], "hook")}
    assert c["hook_cost_usd"] == pytest.approx(sum(r["usd"] for r in calls if r["video_id"] == conv))
    hk = s.health_once()["hooks_12h"]
    assert hk["spotlight_asked_videos"] == 1 and hk["spotlight_rows"] == len(spots)
    assert set(hk["rows_by_episode"]) == {">= 0.3 turns / min (asked)",               # audit a36 c1 (muse): the
                                          "< 0.3 turns / min (a marked solo episode)"}  # buckets are the threshold
    # audit hk3 c1 (muse): end to end, the packager's read returns the spotlight rows (no filter drops them)
    since = datetime.fromtimestamp(s.clock() - 3600, timezone.utc)
    out, rep = ledger.best_unused_moments(s.p["ledger"], since, registry=[H.CHAN], optout=(), store_root=s.p["root"],
                                          limit=1000)
    got = {l["moment_id"] for l in out if l.get("role_hint") == "spotlight"}
    assert got and got == {l["moment_id"] for l in spots if not l["speaker"]["turn_change_inside"]}


def test_the_hook_note_says_which_question_failed(svc):
    """Audit hk3 c1 (glm): a pass whose spotlight question was rejected says so (hook 0, spotlight N), and is retried."""
    def bad_spot(prompt):
        if H.is_spot(prompt):                                          # 3 spotlights: more than the question allows
            return H.spots_reply(prompt, ((3, 6), (7, 10), (11, 14)))
        return _every_question(prompt)
    s, vids, b = svc(bad_spot, bad_spot, n_videos=1)
    ts = config.ts()
    solo_captions = ts.fetch_captions

    def captions(meta, work):
        lead = [(">> " if i % 4 == 3 else "") + f"Bitcoin show {meta['video_id']} opens with {i} new facts."
                for i in range(30)]
        rec, _ = H.caption_record(meta["video_id"], n_rep=8, lead=lead)
        return "ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])
    ts.fetch_captions = captions
    try:
        run_once(s)
        s.hook_once(wait=True)
    finally:
        ts.fetch_captions = solo_captions
    row = s.q.video(vids[0])
    assert row["hook_ts"] is None and row["hook_tries"] == 1 and "(hook 0, spotlight " in row["hook_note"]


def test_a_crashing_spotlight_question_never_holds_back_the_hook_rows(svc, monkeypatch):
    """Audit hk3 c2 (all three reviewers): the spotlight question RAISING (a crash, not a model failure) after the hook
    question answered: the hook rows are written, the pass completes marked 'spotlight crashed' (hooks --rerun asks it
    again), the crash is an event, and the pass does not loop."""
    s, vids, b = svc(_every_question, _every_question, n_videos=1)
    ts = config.ts()

    def captions(meta, work):
        lead = [(">> " if i % 4 == 3 else "") + f"Bitcoin show {meta['video_id']} opens with {i} new facts."
                for i in range(30)]
        rec, _ = H.caption_record(meta["video_id"], n_rep=8, lead=lead)
        return "ok", ts._make_record(meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])
    monkeypatch.setattr(ts, "fetch_captions", captions)
    real = mine.mine_video

    def crash(*a, **k):
        if k.get("kind") == "spotlight":
            raise RuntimeError("a spotlight bug")
        return real(*a, **k)
    monkeypatch.setattr(service.mine, "mine_video", crash)
    run_once(s)
    assert s.hook_once(wait=True) == 1
    row = s.q.video(vids[0])
    hooks = [l for l in ledger.read(s.p["ledger"])[0] if l.get("role_hint") == "hook" and l["video_id"] == vids[0]]
    assert hooks and row["hook_ts"] and row["hook_rows"] == len(hooks) and row["spot_rows"] is None
    assert row["hook_version"] == f"{mine.HOOK_PROMPT_VERSION} (spotlight crashed)"
    assert "the spotlight question crashed: RuntimeError: a spotlight bug" in row["hook_note"]
    assert s.q.rows("SELECT COUNT(*) AS n FROM events WHERE kind='spotlight_crash'")[0]["n"] == 1
    assert s.hook_once(wait=True) == 0                                   # done: no loop


def test_every_mining_question_needs_its_role_to_start():
    """The 08:15 ruling 2: the spotlight question has its own role; a provider config without it, or without the
    second-model check's (audit hk3 c1, glm), stops the start (every pass of it would crash)."""
    service.check_roles(providers.load_config())                        # the real providers.json: every role there
    cfg = H.router_cfg(["primary", "fallback"])
    service.check_roles(cfg)
    for role in ("spotlight", "flagcheck"):
        c = H.router_cfg(["primary", "fallback"])
        del c["roles"][role]
        with pytest.raises(ValueError, match=rf"no role \['{role}'\]"):
            service.check_roles(c)


def test_the_hook_rerun_is_idempotent_per_question_version(svc, monkeypatch):
    """Audit r92 c2 (glm): a completed pass records the question it asked; --rerun re-queues only passes of an older
    question, so a second --rerun after a successful re-run spends nothing."""
    import argparse
    import importlib.util
    spec = importlib.util.spec_from_file_location("ingest_watch", os.path.join(config.REPO, "tools", "ingest_watch.py"))
    iw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(iw)
    s, vids, b = svc(H.first_two_and_hooks, H.first_two_and_hooks, n_videos=1)
    run_once(s)
    while s.hook_once(wait=True):
        pass
    assert s.q.video(vids[0])["hook_version"] == mine.HOOK_PROMPT_VERSION
    monkeypatch.setattr(iw.config, "paths", lambda root=None: s.p)
    iw.cmd_hooks(argparse.Namespace(hours=12.0, rerun=True))
    assert s.q.video(vids[0])["hook_ts"] is not None                       # same version: not queued again
    s.q.set_hook(vids[0], hook_version="mine-hook/1")
    iw.cmd_hooks(argparse.Namespace(hours=12.0, rerun=True))
    row = s.q.video(vids[0])
    assert row["hook_ts"] is None and row["hook_note"] == f"re-run: {mine.HOOK_PROMPT_VERSION}"
    while s.hook_once(wait=True):
        pass
    assert s.q.video(vids[0])["hook_version"] == mine.HOOK_PROMPT_VERSION
