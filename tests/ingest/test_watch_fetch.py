"""Watching (uploads playlist, RSS, the last-seen ledger, backoff, opt-outs) and fetching (live / upcoming / Short /
captions pending / re-uploads, the frozen-live regression INGEST-FAIL-01, stream dating INGEST-FAIL-03, the store's
record format)."""
import json
import os
import time

import pytest

import helpers as H
from pipeline.ingest import config, fetch, watch
from pipeline.ingest import queue as Q

NOW = 1794470000.0          # 2026-11-12 ~08:33 UTC


@pytest.fixture
def q(tmp_path):
    return Q.Queue(str(tmp_path / "q.sqlite"), clock=lambda: NOW)


def listing(entries):
    return {"channel_id": H.CHAN["channel_id"], "entries": entries}


def entry(v, ts, live=None, dur=900, url=None):
    return {"id": v, "title": f"title {v}", "timestamp": ts, "live_status": live, "duration": dur,
            "url": url or f"https://www.youtube.com/watch?v={v}"}


class TestWatch:
    def test_the_uploads_playlist_is_used_and_lists_streams_and_shorts(self, q):
        a, b, c, old = H.vid("a"), H.vid("b"), H.vid("c"), H.vid("o")
        gate = H.FakeGate(listing={H.CHAN["channel_id"]: listing([
            entry(a, NOW - 3600, live="was_live", dur=3500), entry(b, NOW - 7200, dur=80),
            entry(c, NOW - 600, url=f"https://www.youtube.com/shorts/{c}"), entry(old, NOW - 5 * 86400)])})
        r = watch.poll_channel(q, gate, H.CHAN, rss_mode=False, now_ts=NOW)
        assert r["source"] == "uploads_playlist" and r["new"] == 4
        assert gate.calls[0][-1] == "https://www.youtube.com/playlist?list=UU" + H.CHAN["channel_id"][2:]
        assert q.video(a)["state"] == Q.DISCOVERED and q.video(a)["listing_live_status"] == "was_live"
        assert q.video(c)["state"] == Q.SHORT
        assert q.video(old)["state"] == Q.SEEN_OLD          # first sight: older than the 72 h window
        assert watch.poll_channel(q, gate, H.CHAN, rss_mode=False, now_ts=NOW)["new"] == 0   # the last-seen ledger

    def test_first_sight_is_backfill_and_later_uploads_are_live(self, q):
        a, b = H.vid("f"), H.vid("n")
        gate = H.FakeGate(listing={H.CHAN["channel_id"]: listing([entry(a, NOW - 3600)])})
        watch.poll_channel(q, gate, H.CHAN, rss_mode=False, now_ts=NOW)
        gate.listing[H.CHAN["channel_id"]]["entries"].insert(0, entry(b, NOW - 60))
        watch.poll_channel(q, gate, H.CHAN, rss_mode=False, now_ts=NOW + 600)
        assert q.video(a)["first_sight"] == 1 and q.video(b)["first_sight"] == 0
        from pipeline.ingest import stats
        for v, pub in ((a, NOW - 3600), (b, NOW - 60)):
            q.set_state(v, Q.MINED, published_ts=pub, mined_ts=NOW + 700, moments=2)
        s = stats.live(q, now_ts=NOW + 800, router=H.make_router([H.FakeBackend("x")]))
        assert s["new_uploads_seen"] == 1 and s["backfill_seen"] == 1 and s["videos_mined_live"] == 1
        assert s["publish_to_mined_min"]["p50"] == round((NOW + 700 - (NOW - 60)) / 60, 1)

    def test_a_failed_listing_backs_off_and_is_recorded(self, q):
        gate = H.FakeGate(listing={})
        r = watch.poll_channel(q, gate, H.CHAN, rss_mode=False, now_ts=NOW)
        ch = q.channel(H.CHAN["channel_id"])
        assert r["error"] and ch["consecutive_errors"] == 1 and ch["backoff_until"] > NOW
        assert watch.poll_channel(q, gate, H.CHAN, rss_mode=False, now_ts=NOW + 1)["skipped"]

    def test_rss_falls_back_to_the_playlist(self, q, monkeypatch):
        monkeypatch.setattr(watch, "rss_list", lambda *a, **k: (_ for _ in ()).throw(watch.ListError("rss_http_404")))
        gate = H.FakeGate(listing={H.CHAN["channel_id"]: listing([entry(H.vid(), NOW - 60)])})
        r = watch.poll_channel(q, gate, H.CHAN, rss_mode=True, now_ts=NOW)
        assert r["source"] == "uploads_playlist" and r["new"] == 1

    def test_rss_is_parsed_with_its_exact_publish_time(self, q, monkeypatch):
        v = H.vid()
        monkeypatch.setattr(watch, "rss_list", lambda *a, **k: ("ok", [
            {"video_id": v, "title": "t", "published": "2026-11-12T08:00:00+00:00",
             "url": f"https://www.youtube.com/watch?v={v}"}], {"ETag": "abc"}))
        r = watch.poll_channel(q, H.FakeGate(), H.CHAN, rss_mode=True, now_ts=NOW)
        assert r["source"] == "rss" and q.channel(H.CHAN["channel_id"])["etag"] == "abc"
        from datetime import datetime, timezone
        assert q.video(v)["listing_ts"] == datetime(2026, 11, 12, 8, 0, tzinfo=timezone.utc).timestamp()

    def test_optouts(self, tmp_path, monkeypatch):
        p = tmp_path / "optout.json"
        monkeypatch.setattr(config, "OPTOUT_PATH", str(p))
        assert watch.optouts() == (set(), None)
        p.write_text(json.dumps(["UCx"]))
        assert watch.optouts() == ({"UCx"}, None)
        p.write_text(json.dumps({"channel_ids": ["UCy"]}))
        assert watch.optouts() == ({"UCy"}, None)
        for bad in ("{", json.dumps({"ids": 1}), json.dumps([1, 2])):
            p.write_text(bad)
            assert watch.optouts()[1]                      # an error: the caller pauses (fail closed)

    def test_the_channel_filter_for_drills(self, monkeypatch):
        monkeypatch.setenv("PP_INGEST_CHANNELS", "scott_melker")
        reg, chans = watch.registry()
        assert [c["slug"] for c in chans] == ["scott_melker"] and len(reg) > 50


def add(q, v, **listing_kw):
    q.add_video(v, H.CHAN["channel_id"], "Bitcoin test video", "uploads_playlist", **listing_kw)
    return q.video(v)


class TestFetch:
    def test_a_live_stream_is_reprobed_never_frozen(self, q):
        """INGEST-FAIL-01 must-fail: no meta.json may be written while the stream is live."""
        v = H.vid("L")
        gate = H.FakeGate(probes={v: H.probe_json(v, live_status="is_live", media_type="livestream", duration=None,
                                                  release_timestamp=NOW - 1800)})
        assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.LIVE
        assert not os.path.exists(os.path.join(config.ts()._vdir(v), "meta.json"))
        row = q.video(v)
        assert row["next_at"] == NOW + config.LIVE_REPROBE_S and row["live_status"] == "is_live"
        gate.probes[v] = H.probe_json(v, live_status="was_live", media_type="livestream", duration=3600,
                                      release_timestamp=NOW - 5400, timestamp=NOW - 60, automatic_captions={})
        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW + 1200) == Q.CAPTIONS_PENDING
        assert not os.path.exists(os.path.join(config.ts()._vdir(v), "meta.json"))

    def test_live_vod_is_dated_by_its_stream_start(self):
        """INGEST-FAIL-03: release_timestamp, not the VOD processing timestamp."""
        j = H.probe_json("x", live_status="was_live", release_timestamp=1794400000, timestamp=1794445000)
        pub, src = fetch.publish_time(j)
        assert pub.startswith("2026-11-11T") and "release_timestamp" in src
        assert fetch.publish_time(H.probe_json("y", timestamp=1794445000))[1] == "yt-dlp timestamp"
        assert fetch.publish_time(H.probe_json("z", timestamp=1794445000), "2026-11-12T01:00:00+00:00")[1] == \
            "youtube_rss"

    def test_upcoming_waits_for_its_start(self, q):
        v = H.vid("U")
        gate = H.FakeGate(probes={v: H.probe_json(v, live_status="is_upcoming", release_timestamp=NOW + 7200,
                                                  duration=None)})
        assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.UPCOMING
        assert q.video(v)["next_at"] == NOW + 7200 + 900

    def test_a_short_is_recorded_not_mined(self, q):
        v = H.vid("S")
        gate = H.FakeGate(probes={v: H.probe_json(v, media_type="short", duration=58, timestamp=NOW - 600)})
        assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.SHORT

    def test_old_long_unavailable_and_mismatched(self, q):
        old, long_, gone, other = H.vid("O"), H.vid("G"), H.vid("X"), H.vid("M")
        gate = H.FakeGate(probes={old: H.probe_json(old, timestamp=NOW - 80 * 3600),
                                  long_: H.probe_json(long_, timestamp=NOW - 600, duration=7 * 3600),
                                  gone: "ERROR: [youtube] x: Private video. Sign in if you've been granted access",
                                  other: H.probe_json(other, timestamp=NOW - 600, channel_id="UC" + "b" * 22)})
        assert fetch.process(q, gate, add(q, old), H.CHAN, set(), now_ts=NOW) == Q.SEEN_OLD
        assert fetch.process(q, gate, add(q, long_), H.CHAN, set(), now_ts=NOW) == Q.TOO_LONG
        assert fetch.process(q, gate, add(q, gone), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
        assert fetch.process(q, gate, add(q, other), H.CHAN, set(), now_ts=NOW) == Q.UNAVAILABLE
        assert "channel mismatch" in q.video(other)["reason"]

    def test_no_captions_waits_then_gives_up_with_a_reason(self, q):
        v = H.vid("C")
        gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 3600, automatic_captions={})})
        assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.CAPTIONS_PENDING
        gate.probes[v] = H.probe_json(v, timestamp=NOW - 49 * 3600, automatic_captions={})
        q.set_state(v, Q.DISCOVERED)
        # published 49 h ago (inside the 72 h window, past the 48 h caption deadline)
        assert fetch.process(q, gate, q.video(v), H.CHAN, set(), now_ts=NOW) == Q.NO_CAPTIONS

    def test_an_opted_out_channel_is_never_fetched(self, q):
        v = H.vid("P")
        gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
        assert fetch.process(q, gate, add(q, v), H.CHAN, {H.CHAN["channel_id"]}, now_ts=NOW) == Q.OPTOUT
        assert gate.calls == []

    def test_captions_are_stored_by_the_stores_own_writer(self, q, monkeypatch):
        v = H.vid("T")
        ts = config.ts()
        rec, _ = H.caption_record(v)
        monkeypatch.setattr(ts, "fetch_captions", lambda meta, work: ("ok", ts._make_record(
            meta, "yt_auto:en-orig", "youtube captions (auto-subs, en-orig)", rec["segments"])))
        gate = H.FakeGate(probes={v: H.probe_json(v, timestamp=NOW - 600)})
        assert fetch.process(q, gate, add(q, v), H.CHAN, set(), now_ts=NOW) == Q.TRANSCRIBED
        stored = ts.canonical_transcript(v)
        assert stored["transcript_sha256"] == ts.segments_sha256(stored["segments"])
        assert stored["channel_name"] == "Test Channel" and q.video(v)["transcript_sha256"] == stored["transcript_sha256"]
        meta = json.load(open(os.path.join(ts._vdir(v), "meta.json")))
        assert meta["captions_auto_en"] == ["en", "en-orig"] and meta["written_by"] == "pipeline.ingest.fetch"
        assert list(ts.chunks(stored))                     # the selector's chunker reads it (identity carried)

    def test_a_reupload_by_title_and_duration_is_a_duplicate(self, q):
        a, b = H.vid("A"), H.vid("B")
        q.add_video(a, H.CHAN["channel_id"], "x", "uploads_playlist")
        q.set_state(a, Q.MINED, title_canon=fetch.title_canon("Bitcoin test video"), duration=900.0)
        gate = H.FakeGate(probes={b: H.probe_json(b, timestamp=NOW - 600, duration=901)})
        q.clock = lambda: NOW + 5
        assert fetch.process(q, gate, add(q, b), H.CHAN, set(), now_ts=NOW + 5) == Q.DUPLICATE
        assert q.video(b)["duplicate_of"] == a


def test_a_shared_long_intro_is_not_a_reupload_but_the_same_speech_is():
    """Audit c2 consensus: two different videos opening on the same 3-minute sponsor read must not collide."""
    intro = [f"This show is brought to you by our sponsor, line {i} of the same read every week about bitcoin."
             for i in range(60)]
    a, _ = H.caption_record(H.vid("a"), lead=intro, extra=["Today we talk about the halving and miners."])
    b, _ = H.caption_record(H.vid("b"), lead=intro, extra=["Today we talk about ETF flows and treasuries."])
    c, _ = H.caption_record(H.vid("c"), lead=intro, extra=["Today we talk about the halving and miners."])
    assert len(" ".join(intro).split()) > 400
    assert fetch.text_fingerprint(a) != fetch.text_fingerprint(b)
    assert fetch.text_fingerprint(a) == fetch.text_fingerprint(c)      # the same speech re-uploaded


def test_meta_record_has_every_key_ensure_meta_writes(monkeypatch):
    ts = config.ts()
    v = H.vid("K")
    j = H.probe_json(v, timestamp=NOW - 600)
    import subprocess
    monkeypatch.setattr(ts, "_ytdlp", lambda args, timeout=120: subprocess.CompletedProcess(args, 0, json.dumps(j), ""))
    theirs = ts.ensure_meta(v, channel=H.CHAN)
    ours = fetch.meta_record(j, H.CHAN, *fetch.publish_time(j))
    assert set(theirs) <= set(ours)
    for k in theirs:
        if k not in ("metadata_fetched_at",):
            assert ours[k] == theirs[k], k
