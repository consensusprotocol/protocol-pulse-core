"""tests/ingest/test_r121.py: a probe answered with yt-dlp's stub (every fact empty) is "no metadata", not waiting.

Found at the 19:31 ET stall of Nov 16: Yahoo Finance nlRpMRMq2bc ("The Daily Wolf with Scott Melker") and QSHyMFr-i04
had sat in probe_retry since 12:05 ET as "no publish time measured": `yt-dlp -J --ignore-no-formats-error` answers them
with a stub (title "youtube video #<id>", no live_status, duration, timestamps or captions: removed, private or not
public yet). Retried every hour forever, they kept the self-check's stall line up overnight. Now such a probe is
UNAVAILABLE ("no metadata"), tried hourly, given up after NO_METADATA_MAX_TRIES, and never counted as waiting.
"""
import pytest

import helpers as H
from pipeline.ingest import fetch, stall
from pipeline.ingest import queue as Q
from test_r118 import add, q  # noqa: F401 (q: the queue fixture)

NOW = 1794470000.0


def stub(v):
    return H.probe_json(v, title=f"youtube video #{v}", live_status=None, duration=None, timestamp=None,
                        release_timestamp=None, media_type="video", automatic_captions={}, channel_id=None)


def test_a_stub_probe_is_no_metadata_tried_hourly_then_given_up(q):
    v = H.vid("S")
    gate = H.FakeGate(probes={v: stub(v)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
    row = q.video(v)
    assert row["next_at"] == NOW + fetch.NO_METADATA_RETRY_S == NOW + 3600
    assert row["reason"].startswith("no metadata: yt-dlp returned no fact")
    q.x("UPDATE videos SET tries=?, next_at=0", (fetch.NO_METADATA_MAX_TRIES - 1,))
    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
    assert q.video(v)["next_at"] >= NOW + 10 ** 9 - 1                      # given up


def test_a_probe_with_any_fact_is_not_a_stub(q):
    up, vod = H.vid("U"), H.vid("V")
    gate = H.FakeGate(probes={up: H.probe_json(up, live_status="is_upcoming", release_timestamp=NOW + 3600,
                                               duration=None),
                              vod: H.probe_json(vod, timestamp=None, duration=None, upload_date="20261112",
                                                automatic_captions={})})
    assert fetch.process(q, gate, add(q, up), H.CHAN, set(), now_ts=NOW) == Q.UPCOMING
    assert fetch.process(q, gate, add(q, vod), H.CHAN, set(), now_ts=NOW) == Q.PROBE_RETRY   # its old path
    assert q.video(vod)["reason"] == "no publish time measured"


def test_a_stub_is_never_counted_as_waiting(q):
    v = H.vid("W")
    gate = H.FakeGate(probes={v: stub(v)})
    fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW)
    q.x("UPDATE videos SET discovered_ts=? WHERE video_id=?", (NOW - 3600, v))
    chk = stall.check(q, NOW)
    assert chk["waiting"] == [] and chk["stalled"] is False
