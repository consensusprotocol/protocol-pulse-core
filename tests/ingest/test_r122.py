"""tests/ingest/test_r122.py: a stub probe can be a moment's answer for a real video.

Nov 17: CoinDesk yHuY9r30Oug ("Solana Breakpoint Day 1 | Replay") was live 01:08-02:08 ET (four re-probes), then
yt-dlp answered two probes with a stub (02:28, 03:28); r121 gave it up on a count of tries that held the live
re-probes, while the pipeline transcribed it at 07:00 and a probe at 07:4x gave every fact again (post_live, 6,728 s).
Now a stub is given up only past its moments' life, and the sweep makes a "no metadata" video due once the
pipeline's store holds its record (the pipeline saw it: it exists).
"""
import helpers as H
from pipeline.ingest import fetch
from pipeline.ingest import queue as Q
from test_r118 import add, downloads, pipeline_record, q  # noqa: F401 (q: the queue fixture)
from test_r120 import post_live
from test_r121 import stub

NOW = 1794470000.0


def test_a_stream_live_for_an_hour_then_answered_with_a_stub_is_not_given_up(q):
    v = H.vid("C")
    gate = H.FakeGate(probes={v: H.probe_json(v, live_status="is_live", media_type="livestream", duration=None,
                                              release_timestamp=NOW - 3600)})
    add(q, v)
    for k in range(4):                                                   # four live re-probes
        q.x("UPDATE videos SET next_at=0")
        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW + k * 1200) == Q.LIVE
    gate.probes[v] = stub(v)
    for k in range(2):                                                   # then two stubs
        q.x("UPDATE videos SET next_at=0")
        t = NOW + 4800 + k * 3600
        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=t) == Q.UNAVAILABLE
        assert q.video(v)["next_at"] == t + fetch.NO_METADATA_RETRY_S     # never given up inside its 12 h


def test_the_sweep_makes_a_stub_due_once_the_pipeline_holds_its_record(q):
    for v, rec, age in (("stub0000001", True, 3600), ("stub0000002", False, 3600), ("stub0000003", True, 13 * 3600)):
        q.add_video(v, H.CHAN["channel_id"], "t", "rss")
        q.x("UPDATE videos SET state=?, reason=?, next_at=?, discovered_ts=?, published_ts=? WHERE video_id=?",
            (Q.UNAVAILABLE, "no metadata: yt-dlp returned no fact about it", NOW + 900, NOW - age, NOW - age, v))
        if rec:
            pipeline_record(v)
    q.add_video("gone0000001", H.CHAN["channel_id"], "t", "rss")       # unavailable for another reason: untouched
    q.x("UPDATE videos SET state=?, reason=?, next_at=?, discovered_ts=? WHERE video_id='gone0000001'",
        (Q.UNAVAILABLE, "yt-dlp: Private video", NOW + 900, NOW - 3600))
    pipeline_record("gone0000001")
    assert fetch.pipeline_sweep(q, NOW) == ["stub0000001"]
    assert q.video("stub0000001")["next_at"] == NOW
    assert q.video("stub0000002")["next_at"] == q.video("stub0000003")["next_at"] == NOW + 900
    assert q.video("gone0000001")["next_at"] == NOW + 900


def test_a_stub_whose_video_answers_again_takes_the_pipelines_record(q, monkeypatch):
    v = H.vid("R")
    pipeline_record(v)
    downloads(monkeypatch)
    gate = H.FakeGate(probes={v: stub(v)})
    assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
    assert fetch.pipeline_sweep(q, NOW + 60) == [v]                       # the pipeline holds its record
    gate.probes[v] = post_live(v)                                          # YouTube answers it again
    assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW + 61) == Q.TRANSCRIBED
    assert q.video(v)["transcript_method"] == "whisper"
