"""tests/ingest/test_r120.py: a stream that is over but still processing (YouTube's live_status post_live).

Found by r119's own measure on Nov 16: Yahoo Finance kh3U_15pFZc was mined 3,205 s after its transcript; YouTube kept
it post_live from 12:26 to 14:26 ET while the pipeline had Whispered it at 13:33, and the watcher treated post_live as
live (re-probed every 20 min, outside the sweep). Now a post_live video whose record the pipeline has goes on through
every other probe check and takes it; the sweep and the self-check cover it. A stream still live never is taken.
"""
import json
import os
import shutil

import pytest

import helpers as H
from pipeline.ingest import config, fetch, stall
from pipeline.ingest import queue as Q
from test_r118 import add, downloads, pipeline_record, q, staged  # noqa: F401 (q: the queue fixture)

NOW = 1794470000.0


def post_live(v, **over):
    j = dict(live_status="post_live", media_type="livestream", duration=1080, release_timestamp=NOW - 7200,
             timestamp=NOW - 7200)
    j.update(over)
    return H.probe_json(v, **j)


def test_a_stream_over_takes_the_pipelines_record_after_every_check(q, monkeypatch):
    v = H.vid("P")
    src, rec = pipeline_record(v)
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: post_live(v)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
    row = q.video(v)
    assert made == [] and row["transcript_method"] == "whisper" and row["live_status"] == "post_live"
    meta = json.load(open(os.path.join(config.ts()._vdir(v), "meta.json")))
    assert meta["live_status"] == "post_live" and meta["written_by"] == "pipeline.ingest.fetch"


def test_a_stream_over_without_a_record_waits_as_before(q, monkeypatch):
    v = H.vid("W")
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: post_live(v)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
    row = q.video(v)
    assert made == [] and row["next_at"] == NOW + config.LIVE_REPROBE_S and row["reason"].startswith("post_live")
    assert not os.path.exists(os.path.join(config.ts()._vdir(v), "meta.json"))


def test_a_stream_still_live_is_never_given_its_record(q, monkeypatch):
    v = H.vid("L")
    pipeline_record(v)
    downloads(monkeypatch)
    gate = H.FakeGate(probes={v: post_live(v, live_status="is_live", duration=None)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
    assert not os.path.exists(staged(v)) and q.video(v)["transcript_method"] is None


def test_a_stream_over_with_no_length_yet_takes_the_length_the_pipeline_recorded(q, monkeypatch):
    v = H.vid("D")
    src, rec = pipeline_record(v, tamper=lambda r: r.update(duration=1066))
    downloads(monkeypatch)
    gate = H.FakeGate(probes={v: post_live(v, duration=None)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
    assert q.video(v)["duration"] == 1066


@pytest.mark.parametrize("over,state", [(dict(release_timestamp=NOW - 80 * 3600, timestamp=NOW - 80 * 3600), Q.SEEN_OLD),
                                        (dict(duration=7 * 3600), Q.TOO_LONG)])
def test_a_stream_over_still_meets_every_other_check(q, monkeypatch, over, state):
    v = H.vid("C")
    pipeline_record(v)
    downloads(monkeypatch)
    gate = H.FakeGate(probes={v: post_live(v, **over)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == state
    assert not os.path.exists(staged(v))


def test_a_stream_over_whose_copy_is_refused_waits_for_its_video(q, monkeypatch):
    v = H.vid("R")
    pipeline_record(v)
    real = shutil.copyfile

    def swap(a, b):
        real(a, b)
        r = json.load(open(b))
        r["segments"][0]["text"] = "swapped"
        json.dump(r, open(b, "w"))
    monkeypatch.setattr(fetch.shutil, "copyfile", swap)
    made = downloads(monkeypatch)
    gate = H.FakeGate(probes={v: post_live(v)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
    assert made == [] and not os.path.exists(staged(v))                     # no caption download while post_live


def test_the_sweep_and_the_self_check_cover_a_stream_over_never_one_still_live(q):
    later = NOW + 1200
    for v, status in (("over0000001", "post_live"), ("live0000001", "is_live")):
        q.add_video(v, H.CHAN["channel_id"], "t", "rss")
        q.x("UPDATE videos SET state=?, live_status=?, next_at=?, discovered_ts=?, published_ts=? WHERE video_id=?",
            (Q.LIVE, status, later, NOW - 2400, NOW - 2400, v))
        pipeline_record(v, tamper=None if status == "post_live" else      # r125: a still-live row's record older
                        (lambda r: r.update(acquired_at="2026-01-01T00:00:00+00:00")))   # than its probe: never due
    assert fetch.pipeline_sweep(q, NOW) == ["over0000001"]
    assert q.video("over0000001")["next_at"] == NOW and q.video("live0000001")["next_at"] == later
    q.x("UPDATE videos SET next_at=? WHERE video_id='over0000001'", (later,))
    chk = stall.check(q, NOW)
    assert [r["video_id"] for r in chk["waiting"]] == ["over0000001"] and chk["stalled"]
    assert "1 STREAM OVER, ITS VIDEO STILL PROCESSING" in stall.line(chk, NOW)
    assert stall.act(q, chk, NOW) == 1 and q.video("over0000001")["next_at"] == NOW
    assert q.video("live0000001")["next_at"] == later


def test_a_stream_over_reads_the_pipelines_record_once(q, monkeypatch):
    """Audit r120 c1 (both reviewers): the record is read and hashed once per probe of a stream over, not three times
    (the live check, the length, the take); the copy is still checked again before it is linked in."""
    v = H.vid("O")
    pipeline_record(v)
    downloads(monkeypatch)
    real, calls = fetch.pipeline_transcript, []
    monkeypatch.setattr(fetch, "pipeline_transcript", lambda *a, **k: (calls.append(a[0]), real(*a, **k))[1])
    gate = H.FakeGate(probes={v: post_live(v, duration=None)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
    assert calls == [v]
