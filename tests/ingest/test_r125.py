"""tests/ingest/test_r125.py: a stream last seen live takes the pipeline's record within the sweep, not at its re-probe.

Found by r119's own measure on Nov 18: Fox Business J0UvqtdsBmc (a scheduled live show) was probed is_live at 09:20 ET;
the pipeline's transcript ingest Whispered it at 09:32 (it transcribes a stream only once its own probe sees it over);
the sweep never looked at an is_live row, so the record waited for the 09:40 re-probe: 462 s from its transcript (the
re-probe is every 20 min, so this path could have passed the 13:05 ruling's 10 minutes). Now the sweep makes such a row
due ONCE when a record acquired after its last probe (state_at) lands; the probe decides (a stream still live is never
taken) and rewrites state_at, so it is never made due again for the same record.
"""
import json
from datetime import datetime, timedelta, timezone

import helpers as H
from pipeline.ingest import config, fetch
from pipeline.ingest import queue as Q
from test_r118 import downloads, pipeline_record, q, staged  # noqa: F401 (q: the queue fixture)

NOW = 1794470000.0
REAL = datetime.now(timezone.utc)                    # state_at is wall time (Queue.set_state: config.iso())


def iso(dt):
    return dt.isoformat()


def live_row(q, v, live="is_live", state=Q.LIVE, probed=REAL - timedelta(hours=1)):
    q.add_video(v, H.CHAN["channel_id"], "t", "rss")
    q.x("UPDATE videos SET state=?, live_status=?, next_at=?, discovered_ts=?, published_ts=?, state_at=? "
        "WHERE video_id=?", (state, live, NOW + 1200, NOW - 2400, NOW - 2400, iso(probed), v))


def record(v, acquired):
    return pipeline_record(v, tamper=lambda r: r.update(acquired_at=acquired))


def test_a_stream_last_seen_live_is_made_due_once_and_never_taken_while_still_live(q, monkeypatch):
    v = H.vid("L")
    live_row(q, v)
    record(v, iso(REAL - timedelta(minutes=50)))          # landed after the probe that said live
    assert fetch.pipeline_sweep(q, NOW) == [v] and q.video(v)["next_at"] == NOW
    ev = [json.loads(d) for (d,) in q.db.execute("SELECT detail FROM events WHERE video_id=? AND kind=?",
                                                 (v, "pipeline_transcript_due"))]
    assert ev == [{"live_status": "is_live", "acquired_at": iso(REAL - timedelta(minutes=50)),        # audit r125
                   "probed_at": iso(REAL - timedelta(hours=1))}]                                      # c1: why
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: H.probe_json(v, live_status="is_live", media_type="livestream", duration=None,
                                              release_timestamp=NOW - 2400, timestamp=NOW - 2400)})
    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.LIVE      # YouTube still says live
    assert made == [] and q.video(v)["transcript_method"] is None
    assert fetch.pipeline_sweep(q, NOW + 60) == []        # the probe rewrote state_at: once per record, no loop
    assert q.video(v)["next_at"] == NOW + config.LIVE_REPROBE_S


def test_a_record_no_newer_than_the_live_probe_never_makes_it_due(q):
    v = H.vid("O")
    live_row(q, v, probed=REAL - timedelta(minutes=10))
    record(v, iso(REAL - timedelta(minutes=40)))          # the probe at -10 min already saw the stream after it
    assert fetch.pipeline_sweep(q, NOW) == [] and q.video(v)["next_at"] == NOW + 1200


def test_a_time_without_its_zone_never_makes_a_live_stream_due(q):
    a, b = H.vid("A"), H.vid("B")
    live_row(q, a)
    record(a, (REAL - timedelta(minutes=50)).replace(tzinfo=None).isoformat())          # the record's time: no zone
    live_row(q, b, probed=(REAL - timedelta(hours=1)).replace(tzinfo=None))            # the probe's time: no zone
    record(b, iso(REAL - timedelta(minutes=50)))
    assert fetch.pipeline_sweep(q, NOW) == []


def test_a_z_time_is_read_as_utc(q):
    v = H.vid("Z")
    live_row(q, v)
    record(v, (REAL - timedelta(minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    assert fetch.pipeline_sweep(q, NOW) == [v]


def test_the_other_waits_keep_their_rule_any_record_makes_them_due(q):
    """r119 / r120 unchanged: a transcript wait, or a stream over (post_live), is made due by any record, whatever its
    time; even a probe_retry row whose stored live_status is is_live."""
    over, retry = H.vid("P"), H.vid("R")
    live_row(q, over, live="post_live", probed=REAL)
    record(over, iso(REAL - timedelta(hours=2)))
    live_row(q, retry, state=Q.PROBE_RETRY, probed=REAL)
    record(retry, iso(REAL - timedelta(hours=2)))
    assert sorted(fetch.pipeline_sweep(q, NOW)) == sorted([over, retry])
