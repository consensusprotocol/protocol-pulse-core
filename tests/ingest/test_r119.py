"""tests/ingest/test_r119.py: the orchestrator's 13:05 ET ruling of Nov 16: "Mine each video within 10 minutes of its
transcript, Bitcoin channels first".

- pipeline_sweep: every video waiting on a transcript whose record lands in the pipeline's store is due at once,
  whatever its own retry time (each fetch round, at most every fetch.PIPELINE_SWEEP_S, never while the gate is open).
- Queue.due / hook_due: the Bitcoin channels (the registry's tiers up to config.BITCOIN_TIER_MAX) before the rest,
  newest first among each.
"""
import json
import os

import pytest

import helpers as H
from pipeline.ingest import config, fetch, ledger, watch
from pipeline.ingest import queue as Q
from test_service import svc  # noqa: F401 (the service fixture: fake back-ends, fake gate, its own store)

NOW = 1794470000.0
BTC, MAIN = H.CHAN["channel_id"], "UC" + "m" * 22


@pytest.fixture
def q(tmp_path):
    return Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: NOW)


def row(q, v, cid, state, published, next_at=NOW - 1, discovered=None, reason=None):
    q.add_video(v, cid, f"t {v}", "rss")
    q.x("UPDATE videos SET state=?, published_ts=?, next_at=?, discovered_ts=?, reason=? WHERE video_id=?",
        (state, published, next_at, discovered if discovered is not None else published, reason, v))


def pipeline_record(v, cid=BTC, tamper=None):
    rec, _ = H.caption_record(v, channel=dict(H.CHAN, channel_id=cid))
    rec = dict(rec, transcript_method="whisper", transcript_model="test model")
    if tamper:
        tamper(rec)
    d = os.path.join(fetch.PIPELINE_STORE, v)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "transcript.whisper.json"), "w") as f:
        json.dump(rec, f)
    return rec


# ── Bitcoin channels first ──

def test_due_takes_the_bitcoin_channels_first_then_the_newest():
    import tempfile
    q = Q.Queue(os.path.join(tempfile.mkdtemp(), "q.sqlite"), clock=lambda: NOW)
    row(q, "b_old000001", BTC, Q.TRANSCRIBED, NOW - 3000)
    row(q, "b_new000001", BTC, Q.TRANSCRIBED, NOW - 1000)
    row(q, "m_new000001", MAIN, Q.TRANSCRIBED, NOW - 100)
    row(q, "m_old000001", MAIN, Q.TRANSCRIBED, NOW - 4000)
    ids = lambda rows: [r["video_id"] for r in rows]
    assert ids(q.due(Q.MINE_DUE, 10)) == ["m_new000001", "b_new000001", "b_old000001", "m_old000001"]   # as before
    assert ids(q.due(Q.MINE_DUE, 10, first={BTC})) == ["b_new000001", "b_old000001", "m_new000001", "m_old000001"]
    assert ids(q.due(Q.MINE_DUE, 1, first={BTC})) == ["b_new000001"]                    # one free slot: Bitcoin
    q.x("UPDATE videos SET state=?", (Q.CAPTIONS_PENDING,))
    assert ids(q.due(Q.FETCH_DUE, 2, first={BTC})) == ["b_new000001", "b_old000001"]
    q.x("UPDATE videos SET state=?, hook_ts=NULL", (Q.MINED,))
    assert ids(q.hook_due(12 * 3600, 10, first={BTC})) == ["b_new000001", "b_old000001", "m_new000001", "m_old000001"]
    assert ids(q.hook_due(12 * 3600, 10)) == ["m_new000001", "b_new000001", "b_old000001", "m_old000001"]


def test_the_bitcoin_channels_are_the_registrys_tiers_up_to_two(svc, monkeypatch):
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    chans = [dict(H.CHAN, channel_id="UC" + c * 22, tier=t) for c, t in (("a", 1), ("b", 2), ("c", 3))] + \
        [dict(H.CHAN, channel_id="UC" + "d" * 22, tier=None)]
    assert s._first(chans) == {"UC" + "a" * 22, "UC" + "b" * 22} and config.BITCOIN_TIER_MAX == 2
    monkeypatch.setattr(watch, "registry", lambda: (_ for _ in ()).throw(OSError("registry unreadable")))
    s._first_at = None
    assert s._first() == {"UC" + "a" * 22, "UC" + "b" * 22}           # a registry not read keeps the last set


def test_the_watcher_mines_a_bitcoin_channels_video_before_a_newer_mainstream_one(svc, monkeypatch):
    s, vids, b = svc(H.first_two, H.first_two, n_videos=2)
    main = dict(H.CHAN, channel_id=MAIN, slug="main", tier=3)
    monkeypatch.setattr(watch, "registry", lambda: ([H.CHAN, main], [H.CHAN, main]))
    s.watch_once()
    while s.fetch_once(limit=20):
        pass
    older, newer = vids
    s.q.x("UPDATE videos SET published_ts=published_ts - 600 WHERE video_id=?", (older,))
    s.q.x("UPDATE videos SET channel_id=? WHERE video_id=?", (MAIN, newer))     # the newer one: mainstream
    s.q.x("UPDATE videos SET state=?, next_at=0", (Q.TRANSCRIBED,))
    order = []
    real = s.mine_video
    monkeypatch.setattr(s, "mine_video", lambda v, role=None: (order.append(v["video_id"]), real(v, role))[1])
    s.inflight = {"x", "y"}                                            # one free slot
    s.mine_once(wait=True)
    assert order == [older]


# ── within minutes of its transcript ──

def _broken(r):
    r["segments"][0]["text"] += " (edited)"


def test_the_sweep_makes_due_only_a_waiting_video_whose_transcript_is_in_the_pipelines_store(q):
    later = NOW + 3600
    for v, state, pub, rec in (("w1aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 600, True),
                               ("w2aaaaaaaaa", Q.PROBE_RETRY, NOW - 600, True),
                               ("w3aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 600, False),       # no record yet
                               ("w4aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 600, "broken"),    # fails its checks
                               ("w5aaaaaaaaa", Q.CAPTIONS_PENDING, NOW - 13 * 3600, True),  # past its 12 h
                               ("w6aaaaaaaaa", Q.MINING, NOW - 600, True),                  # in flight
                               ("w7aaaaaaaaa", Q.UPCOMING, NOW - 600, True)):               # not a transcript wait
        row(q, v, BTC, state, pub, next_at=later)
        if rec:
            pipeline_record(v, tamper=_broken if rec == "broken" else None)
    row(q, "w8aaaaaaaaa", BTC, Q.CAPTIONS_PENDING, NOW - 600, next_at=NOW - 5)                # already due
    pipeline_record("w8aaaaaaaaa")
    assert sorted(fetch.pipeline_sweep(q, NOW)) == ["w1aaaaaaaaa", "w2aaaaaaaaa"]
    nxt = {r["video_id"]: r["next_at"] for r in q.rows("SELECT video_id, next_at FROM videos")}
    assert nxt["w1aaaaaaaaa"] == nxt["w2aaaaaaaaa"] == NOW
    assert all(nxt[v] == later for v in ("w3aaaaaaaaa", "w4aaaaaaaaa", "w5aaaaaaaaa", "w6aaaaaaaaa", "w7aaaaaaaaa"))
    assert sorted(r["video_id"] for r in q.rows("SELECT video_id FROM events WHERE kind='pipeline_transcript_due'")) \
        == ["w1aaaaaaaaa", "w2aaaaaaaaa"]
    assert fetch.pipeline_sweep(q, NOW) == []                          # due now: nothing more to do


def test_a_transcript_landing_in_the_pipelines_store_is_mined_at_the_next_fetch_round(svc, monkeypatch):
    """A video put off 30 min by a caption 429: its Whisper record lands; the next fetch round (the sweep: at most
    fetch.PIPELINE_SWEEP_S apart) takes it and the miner mines it, long before its own retry."""
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    v = vids[0]
    ts = config.ts()
    monkeypatch.setattr(ts, "fetch_captions", lambda meta, work: ("throttled", None))
    s.watch_once()
    s.fetch_once(limit=20)
    row0 = s.q.video(v)
    assert row0["state"] == Q.CAPTIONS_PENDING and row0["next_at"] > s.clock() + 500
    rec = pipeline_record(v)
    s._last_sweep = s.clock() - fetch.PIPELINE_SWEEP_S                 # the next sweep is due
    s.fetch_once(limit=20)
    assert s.q.video(v)["state"] == Q.TRANSCRIBED and s.q.video(v)["transcript_sha256"] == rec["transcript_sha256"]
    while s.mine_once(wait=True):
        pass
    assert s.q.video(v)["state"] == Q.MINED
    lines, bad = ledger.read(s.p["ledger"])
    assert not bad and {l["video_id"] for l in lines} == {v}
    ev = s.q.rows("SELECT detail FROM events WHERE kind='pipeline_transcript' AND video_id=?", (v,))
    assert json.loads(ev[0]["detail"])["acquired_at"] == rec["acquired_at"]  # the pipeline's own time: the latency


def test_no_sweep_while_the_gate_is_open_and_at_most_one_a_minute(svc, monkeypatch):
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    calls = []
    monkeypatch.setattr(fetch, "pipeline_sweep", lambda q, now: (calls.append(now), [])[1])
    monkeypatch.setattr(s.gate, "open_for", lambda: 300.0, raising=False)
    s.fetch_once(limit=1)
    assert calls == []                                                 # no probe can run: looked at once it shuts
    monkeypatch.setattr(s.gate, "open_for", lambda: 0.0, raising=False)
    s.fetch_once(limit=1)
    s.fetch_once(limit=1)                                              # the same minute: not again
    assert len(calls) == 1
    s._last_sweep -= fetch.PIPELINE_SWEEP_S
    s.fetch_once(limit=1)
    assert len(calls) == 2


# ── the measure (audit r119 c1): seconds from its transcript to its rows, LATE past 10 minutes ──

def test_transcript_lag_reads_only_a_time_with_its_zone():
    from datetime import datetime, timezone
    from pipeline.ingest import service
    at = datetime.fromtimestamp(NOW - 800, timezone.utc)
    assert service.transcript_lag(at.isoformat(), NOW) == pytest.approx(800.0)
    assert service.transcript_lag(at.strftime("%Y-%m-%dT%H:%M:%SZ"), NOW) == pytest.approx(800.0)
    naive = at.replace(tzinfo=None).isoformat()
    assert service.transcript_lag(None, NOW) is None and service.transcript_lag(naive, NOW) is None
    assert service.transcript_lag("not a time", NOW) is None
    assert service.transcript_lag("2030-01-01T00:00:00+00:00", NOW) == 0.0          # never negative


def test_a_video_mined_past_10_minutes_from_its_transcript_is_said_late_in_the_log_and_on_the_cycles_line(svc,
                                                                                                        monkeypatch):
    import time as _time
    from datetime import datetime, timezone
    from pipeline.ingest import cycles
    s, vids, b = svc(H.first_two, H.first_two, n_videos=1)
    logs = []
    s.log = logs.append
    v = vids[0]
    monkeypatch.setattr(config.ts(), "fetch_captions", lambda meta, work: ("throttled", None))
    s.watch_once()
    s.fetch_once(limit=20)
    old = datetime.fromtimestamp(_time.time() - 700, timezone.utc).isoformat()
    pipeline_record(v, tamper=lambda r: r.update(acquired_at=old))   # the pipeline's Whisper, 700 s ago
    s._last_sweep = None
    s.fetch_once(limit=20)
    while s.mine_once(wait=True):
        pass
    row = s.q.video(v)
    assert row["state"] == Q.MINED and 695 <= row["transcript_lag_s"] <= 760
    said = [m for m in logs if m.startswith(f"mine {v} ")]
    assert said and "s from its transcript (LATE: past the 13:05 ruling's 10 minutes)" in said[-1]
    line = cycles.compose(s.q, _time.time())
    assert f"{row['transcript_lag_s']:.0f} s transcript (LATE) -> rows" in line
    s.q.x("UPDATE videos SET transcript_lag_s=42 WHERE video_id=?", (v,))
    line = cycles.compose(s.q, _time.time())
    assert "42 s transcript -> rows" in line and "(LATE)" not in line
