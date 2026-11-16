#!/usr/bin/env python3
"""transcript_store: a video whose stored metadata was taken while it was live is read again before it is skipped
(pp-ingest's finding, 2026-11-16 13:3x ET, INGEST-FAIL-01's pattern).

Scott Melker f0NnJM63Ffc's meta.json was written at 09:30 ET while its stream was live. ensure_meta returned that
stored record for ever, so every cron run since skipped the video ("skip: live_status is_live") long after the
stream had ended (was_live, 3,679 s). Now:
- a stored live_status of is_live, is_upcoming or post_live is re-read, at most once per META_RECHECK_S per video;
- the fresh snapshot is appended to meta_history.jsonl, and meta.json stays write-once;
- ensure_meta returns the newest snapshot;
- a failed re-read appends nothing and the stored state stands for that run.
No network, GPU or model: yt-dlp is a stub, and the store lives in a temp directory."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcript_store as ts  # noqa: E402

VID = "f0NnJM63Ffc"


class R:
    def __init__(self, out="", err=""):
        self.stdout, self.stderr = out, err


def yt(live_status, duration=None, **k):
    return dict({"id": VID, "channel_id": "UCmelker", "channel": "Scott Melker", "title": "The Wolf Of All Streets",
                 "timestamp": 1794830000, "duration": duration, "live_status": live_status, "description": "",
                 "subtitles": {}, "automatic_captions": {"en": [{}]} if live_status == "was_live" else {}}, **k)


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ts_live_")
        self.addCleanup(shutil.rmtree, self.root)
        self.calls, self.replies = [], []

        def ytdlp(args, timeout=120):
            self.calls.append(args)
            r = self.replies.pop(0) if self.replies else R(err="ERROR: no reply staged")
            return r
        for p in (mock.patch.object(ts, "TRANSCRIPTS_DIR", os.path.join(self.root, "transcripts")),
                  mock.patch.object(ts, "STATE_DIR", os.path.join(self.root, "state")),
                  mock.patch.object(ts, "_ytdlp", ytdlp)):
            p.start()
            self.addCleanup(p.stop)

    def stage(self, *metas):
        self.replies += [R(json.dumps(m)) if isinstance(m, dict) else R(err=m) for m in metas]

    def stored_live(self, status="is_live"):
        """The 09:30 record: written once while the stream was live."""
        self.stage(yt(status))
        m = ts.ensure_meta(VID)
        self.assertEqual(m["live_status"], status)
        self.calls.clear()
        with open(os.path.join(ts._vdir(VID), "meta.json"), "rb") as f:
            return f.read()

    def age(self, seconds):
        """Make the newest snapshot `seconds` old (its metadata_fetched_at)."""
        hist = os.path.join(ts._vdir(VID), "meta_history.jsonl")
        path = hist if os.path.exists(hist) else os.path.join(ts._vdir(VID), "meta.json")
        when = ts.datetime.fromtimestamp(time.time() - seconds, ts.timezone.utc).isoformat()
        if path == hist:
            lines = open(hist).read().splitlines()
            last = json.loads(lines[-1])
            last["metadata_fetched_at"] = when
            lines[-1] = json.dumps(last)
            open(hist, "w").write("\n".join(lines) + "\n")
        else:                                            # meta.json is write-once: rewrite it only in the test
            m = json.load(open(path))
            m["metadata_fetched_at"] = when
            os.chmod(path, 0o644)
            open(path, "w").write(json.dumps(m))

    def acquire(self):
        return ts.acquire(VID, allow_whisper=False, caption_fn=lambda meta, wd: ("unavailable", None))


class TestStaleLive(Base):

    def test_a_stream_that_ended_since_its_meta_was_written_is_read_again_and_goes_on(self):
        self.stored_live()
        self.age(4 * 3600)                                              # written at 09:30; it is now 13:30
        with open(os.path.join(ts._vdir(VID), "meta.json"), "rb") as f:
            before = f.read()
        self.stage(yt("was_live", 3679))
        rec, st = self.acquire()
        self.assertEqual(st, "pending_whisper")                         # not skipped_live: on to Whisper
        self.assertEqual(len(self.calls), 1)                            # one re-read
        with open(os.path.join(ts._vdir(VID), "meta.json"), "rb") as f:
            self.assertEqual(f.read(), before)                          # meta.json stays write-once
        m = ts.ensure_meta(VID)                                         # the newest snapshot
        self.assertEqual((m["live_status"], m["duration"]), ("was_live", 3679))
        with open(os.path.join(ts._vdir(VID), "meta_history.jsonl")) as f:
            hist = [json.loads(l) for l in f]
        self.assertEqual([h["live_status"] for h in hist], ["was_live"])
        self.assertEqual(len(self.calls), 1)                            # ensure_meta asked YouTube nothing

    def test_still_live_it_is_skipped_and_read_again_only_after_the_recheck_interval(self):
        self.stored_live()
        self.age(4 * 3600)
        self.stage(yt("is_live"))
        self.assertEqual(self.acquire()[1], "skipped_live")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.acquire()[1], "skipped_live")             # the same run's second look: no new read
        self.assertEqual(len(self.calls), 1)
        self.age(ts.META_RECHECK_S + 1)                                 # the next run
        self.stage(yt("was_live", 3679))
        self.assertEqual(self.acquire()[1], "pending_whisper")
        self.assertEqual(len(self.calls), 2)

    def test_a_failed_re_read_appends_nothing_and_the_next_run_tries_again(self):
        self.stored_live()
        self.age(4 * 3600)
        self.stage("ERROR: [youtube] f0NnJM63Ffc: HTTP Error 429: Too Many Requests")
        self.assertEqual(self.acquire()[1], "skipped_live")             # the stored state stands this run
        self.assertFalse(os.path.exists(os.path.join(ts._vdir(VID), "meta_history.jsonl")))
        with open(os.path.join(ts._vdir(VID), "attempts.jsonl")) as f:
            steps = [json.loads(l).get("step") for l in f]
        self.assertIn("meta_refresh", steps)                            # the failed read is logged
        self.stage(yt("was_live", 3679))
        self.assertEqual(self.acquire()[1], "pending_whisper")          # retried: nothing recent was written
        self.assertEqual(len(self.calls), 2)

    def test_upcoming_and_post_live_are_read_again_too(self):
        for stored, fresh, want in (("is_upcoming", yt("was_live", 1200), "pending_whisper"),
                                    ("is_upcoming", yt("is_upcoming"), "skipped_live"),
                                    ("post_live", yt("was_live", 1200), "pending_whisper"),
                                    ("post_live", yt("post_live"), "pending_whisper")):   # post_live was never a skip
            with self.subTest(stored=stored, fresh=fresh["live_status"]):
                shutil.rmtree(os.path.join(self.root, "transcripts"), ignore_errors=True)
                self.calls.clear()
                self.stored_live(stored)
                self.age(4 * 3600)
                self.stage(fresh)
                self.assertEqual(self.acquire()[1], want)
                self.assertEqual(len(self.calls), 1)

    def test_a_finished_video_is_never_read_again(self):
        for status in ("was_live", "not_live", None):
            with self.subTest(status=status):
                shutil.rmtree(os.path.join(self.root, "transcripts"), ignore_errors=True)
                self.stage(yt(status, 900))
                ts.ensure_meta(VID)
                self.calls.clear()
                self.age(4 * 3600)
                self.assertEqual(self.acquire()[1], "pending_whisper")
                self.assertEqual(self.calls, [])                        # YouTube is not asked again

    def test_a_torn_history_line_is_skipped_and_the_last_whole_snapshot_wins(self):
        self.stored_live()
        self.age(4 * 3600)
        self.stage(yt("was_live", 3679))
        self.acquire()
        with open(os.path.join(ts._vdir(VID), "meta_history.jsonl"), "a") as f:
            f.write('{"video_id": "f0NnJM63Ffc", "live_status": "is_li')     # a crash mid-write
        m = ts.ensure_meta(VID)
        self.assertEqual((m["live_status"], m["duration"]), ("was_live", 3679))

    def test_a_snapshot_for_another_video_in_the_history_is_ignored(self):
        self.stored_live()
        os.makedirs(ts._vdir(VID), exist_ok=True)
        with open(os.path.join(ts._vdir(VID), "meta_history.jsonl"), "w") as f:
            f.write(json.dumps({"video_id": "XXXXXXXXXXX", "live_status": "was_live", "duration": 5}) + "\n")
        self.assertEqual(ts.ensure_meta(VID)["live_status"], "is_live")


if __name__ == "__main__":
    unittest.main(verbosity=2)
