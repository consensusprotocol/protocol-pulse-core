#!/usr/bin/env python3
"""pp-ingest R14 (INGEST-FAIL-03), Nov 16: a scheduled stream is dated by when it AIRED, not by its RSS time.

Bitcoin Magazine KRvh4AcSofA's RSS time is 2026-11-13T17:19:33Z, when the stream was SCHEDULED. It aired at
2026-11-16T14:32:26Z, but the ingest's 72 h universe dropped it at 12:19 ET that day, just as it aired. Its stored
record (is_live, read at 10:00 ET) was never reached again.
- The store now keeps a stream's release_timestamp (its start) in every metadata snapshot.
- stream_start() gives when a stored stream aired: its release_timestamp. A snapshot read while the stream was not
  yet finished, and naming no start, gives the time of that read.
- universe() dates an entry whose RSS time is outside the window by that start instead. Any other entry is dated by
  its RSS time, as before.
No network: the RSS feed and yt-dlp are stubs, and the store is a temp directory."""
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcript_ingest as TI  # noqa: E402
import transcript_store as ts  # noqa: E402

NOW = datetime.now(timezone.utc)
CH = {"channel_id": "UCbtcmag", "display_name": "Bitcoin Magazine", "tier": 1, "layout_status": "approved"}


def iso(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).isoformat()


def entry(vid, hours_ago):
    return {"video_id": vid, "title": f"title {vid}", "published": iso(hours_ago),
            "url": f"https://www.youtube.com/watch?v={vid}"}


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="stream_win_")
        self.addCleanup(shutil.rmtree, self.root)
        self.rss = []
        for p in (mock.patch.object(ts, "TRANSCRIPTS_DIR", os.path.join(self.root, "transcripts")),
                  mock.patch.object(ts, "STATE_DIR", os.path.join(self.root, "state")),
                  mock.patch.object(TI, "fetch_rss", lambda channel_id, timeout=15: list(self.rss))):
            p.start()
            self.addCleanup(p.stop)

    def store(self, vid, live_status, read_hours_ago, release_hours_ago=None, history=None):
        """meta.json as the store writes it (optionally an older record without release_timestamp)."""
        os.makedirs(ts._vdir(vid), exist_ok=True)
        m = {"video_id": vid, "live_status": live_status, "metadata_fetched_at": iso(read_hours_ago),
             "published_at": iso(80), "duration": None}
        if release_hours_ago is not None:
            m["release_timestamp"] = iso(release_hours_ago)
        with open(os.path.join(ts._vdir(vid), "meta.json"), "w") as f:
            json.dump(m, f)
        if history:
            with open(os.path.join(ts._vdir(vid), "meta_history.jsonl"), "w") as f:
                for h in history:
                    f.write(json.dumps(dict({"video_id": vid}, **h)) + "\n")

    def ids(self):
        return {v["video_id"]: v["age_h"] for v in TI.universe(72, channels=[CH])}


class TestStreamStart(Base):

    def test_r14_a_stream_scheduled_days_ago_is_dated_by_when_it_aired(self):
        self.rss = [entry("KRvh4AcSofA", 80)]                           # scheduled 80 h ago
        self.store("KRvh4AcSofA", "is_live", 5)                         # read live 5 h ago, no start recorded
        got = self.ids()
        self.assertIn("KRvh4AcSofA", got)                               # old code: dropped at 72 h
        self.assertAlmostEqual(got["KRvh4AcSofA"], 5.0, delta=0.2)      # dated by the read while live
        self.store("KRvh4AcSofA", "post_live", 1, release_hours_ago=1.5)   # read again: aired 1.5 h ago
        self.assertAlmostEqual(self.ids()["KRvh4AcSofA"], 1.5, delta=0.2)

    def test_the_start_comes_from_the_newest_snapshot(self):
        self.rss = [entry("KRvh4AcSofA", 80)]
        self.store("KRvh4AcSofA", "is_live", 30, history=[
            {"live_status": "was_live", "metadata_fetched_at": iso(0.5), "release_timestamp": iso(2)}])
        self.assertAlmostEqual(self.ids()["KRvh4AcSofA"], 2.0, delta=0.2)

    def test_a_stream_that_aired_more_than_the_window_ago_is_still_dropped(self):
        self.rss = [entry("OLDSTREAM01", 200)]
        self.store("OLDSTREAM01", "was_live", 100, release_hours_ago=150)
        self.assertNotIn("OLDSTREAM01", self.ids())

    def test_an_ordinary_video_past_the_window_is_dropped_as_before(self):
        self.rss = [entry("PLAINVIDEO1", 80), entry("NOSTORE0001", 80)]
        self.store("PLAINVIDEO1", "not_live", 79, release_hours_ago=2)  # an upload, not a stream: RSS time stands,
                                                                        # whatever release time it names
        self.assertEqual(self.ids(), {})

    def test_inside_the_window_the_rss_time_stands(self):
        self.rss = [entry("RECENT00001", 10)]
        self.store("RECENT00001", "was_live", 1, release_hours_ago=2)
        self.assertAlmostEqual(self.ids()["RECENT00001"], 10.0, delta=0.2)  # unchanged behaviour inside the window

    def test_a_finished_stream_with_no_start_recorded_keeps_its_rss_time(self):
        self.rss = [entry("WASLIVENOTS", 80)]
        self.store("WASLIVENOTS", "was_live", 2)                        # finished, no release_timestamp
        self.assertNotIn("WASLIVENOTS", self.ids())

    def test_an_unreadable_or_odd_record_never_breaks_the_universe(self):
        self.rss = [entry("BROKENREC01", 80), entry("RECENT00001", 3)]
        os.makedirs(ts._vdir("BROKENREC01"), exist_ok=True)
        with open(os.path.join(ts._vdir("BROKENREC01"), "meta.json"), "w") as f:
            f.write("{not json")
        self.assertEqual(set(self.ids()), {"RECENT00001"})
        self.store("BROKENREC01", "is_live", 5)
        with open(os.path.join(ts._vdir("BROKENREC01"), "meta.json")) as f:
            m = json.load(f)
        m["metadata_fetched_at"] = "not a time"
        with open(os.path.join(ts._vdir("BROKENREC01"), "meta.json"), "w") as f:
            json.dump(m, f)
        self.assertEqual(set(self.ids()), {"RECENT00001"})              # no start known: the RSS time stands

    def test_a_start_in_the_future_is_not_in_the_window_yet(self):
        self.rss = [entry("UPCOMING001", 80)]
        self.store("UPCOMING001", "is_upcoming", 1, release_hours_ago=-3)   # airs in 3 h
        self.assertNotIn("UPCOMING001", self.ids())


class TestStoreKeepsTheStart(Base):

    def test_every_snapshot_records_the_streams_release_timestamp(self):
        class R:
            def __init__(self, out):
                self.stdout, self.stderr = out, ""
        j = {"id": "KRvh4AcSofA", "channel_id": "UCbtcmag", "channel": "Bitcoin Magazine", "title": "t",
             "timestamp": 1794850000, "duration": 7309, "live_status": "post_live",
             "release_timestamp": 1794839546, "subtitles": {}, "automatic_captions": {}}
        with mock.patch.object(ts, "_ytdlp", lambda args, timeout=120: R(json.dumps(j))):
            m = ts.ensure_meta("KRvh4AcSofA")
        self.assertEqual(m["release_timestamp"],
                         datetime.fromtimestamp(1794839546, timezone.utc).isoformat())
        for bad in (None, "1794839546", True):
            with self.subTest(release_timestamp=bad):
                shutil.rmtree(os.path.join(self.root, "transcripts"), ignore_errors=True)
                with mock.patch.object(ts, "_ytdlp", lambda args, timeout=120: R(json.dumps(
                        dict(j, release_timestamp=bad)))):
                    self.assertIsNone(ts.ensure_meta("KRvh4AcSofA")["release_timestamp"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
