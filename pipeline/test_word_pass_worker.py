#!/usr/bin/env python3
"""word_pass_worker (orchestrator '22:40' ruling 2 / '22:50' item 5), without GPU or network: the pick (rank order, at
most PER_CHANNEL per channel so >= MIN_CHANNELS channels, passed moments and full-record videos skipped), the window
(PAD_S, clipped to the video), the record (YouTube clock, window, words_sha256), the readiness rows (one per moment,
failures included and never retried), the adapter failing closed, a whole cycle on a scratch store, and GPU1 only."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import word_pass_worker as W  # noqa: E402


def row(i, ch, vid=None, start=100.0, end=112.0, pub="2026-11-12T10:00:00+00:00"):
    return {"moment_id": f"m{i:03d}", "video_id": vid or f"v{ch}", "channel_id": f"UC{ch}", "start": start, "end": end,
            "published_at": pub}


class TestPickAndWindow(unittest.TestCase):
    def test_at_most_seven_per_channel_so_forty_span_six_channels(self):
        rows = [row(i, i % 8 if i >= 30 else 0) for i in range(80)]           # the top 30 all from one channel
        picks, nch = W.pick(rows, set(), full=lambda v: False)
        self.assertEqual(len(picks), W.PER_CYCLE)
        self.assertGreaterEqual(nch, W.MIN_CHANNELS)
        per = {}
        for r in picks:
            per[r["channel_id"]] = per.get(r["channel_id"], 0) + 1
        self.assertLessEqual(max(per.values()), W.PER_CHANNEL)
        self.assertEqual(picks[0]["moment_id"], "m000")                       # rank order kept

    def test_five_channels_of_ten_give_thirty_five_and_a_sixth_channel_fills_in(self):   # audit batch 51 C1
        five = [row(i, i // 10) for i in range(50)]                            # ranked: ch0 x10, ch1 x10, ... ch4 x10
        picks, nch = W.pick(five, set(), full=lambda v: False)
        self.assertEqual((len(picks), nch), (35, 5))                           # the ledger allows no more channels
        six = five + [row(100 + i, 9) for i in range(3)]                       # three lower-ranked rows of a 6th
        picks, nch = W.pick(six, set(), full=lambda v: False)
        self.assertEqual((len(picks), nch), (38, 6))
        self.assertEqual([r["moment_id"] for r in picks][-3:], ["m100", "m101", "m102"])

    def test_order_0155_the_last_ten_hours_come_first_by_score_then_the_rest(self):
        import datetime as dt
        now = dt.datetime(2026, 11, 13, 6, 0, tzinfo=dt.timezone.utc)
        old = [row(i, i, pub="2026-11-12T10:00:00+00:00") for i in range(10)]                # ranked first, 20 h old
        fresh = [row(100 + i, 50 + i, pub="2026-11-13T01:00:00+00:00") for i in range(3)]    # ranked last, 5 h old
        edge = [row(200, 70, pub="2026-11-12T20:00:00+00:00"), row(201, 71, pub="2026-11-12T19:59:59+00:00")]
        picks, _ = W.pick(old + fresh + edge, set(), full=lambda v: False, per_cycle=5, now=now)
        self.assertEqual([r["moment_id"] for r in picks], ["m100", "m101", "m102", "m200", "m000"])  # 10 h is inclusive
        self.assertFalse(W.is_fresh(row(1, 1, pub="2026-11-13T07:00:00+00:00"), now))        # a future time is not fresh
        self.assertFalse(W.is_fresh(row(1, 1, pub="2026-11-13T01:00:00"), now))              # no offset: not measured
        self.assertTrue(W.is_fresh(row(1, 1, pub="2026-11-13T01:00:00Z"), now))              # 'Z' as the ledger reads it
        self.assertFalse(W.is_fresh(row(1, 1, pub=None), now))

    def test_order_0155_a_capped_channels_fresh_rows_still_come_before_older_rows(self):
        import datetime as dt
        now = dt.datetime(2026, 11, 13, 6, 0, tzinfo=dt.timezone.utc)
        fresh = [row(i, 1, pub="2026-11-13T02:00:00+00:00") for i in range(10)]            # one channel, 10 fresh
        older = [row(100 + i, 2 + i, pub="2026-11-12T08:00:00+00:00") for i in range(10)]   # ranked above them
        picks, _ = W.pick(older + fresh, set(), full=lambda v: False, per_cycle=12, now=now)
        ids = [r["moment_id"] for r in picks]
        self.assertEqual(ids[:10], [f"m{i:03d}" for i in range(10)])          # 7 capped, then the other 3 fresh
        self.assertEqual(ids[10:], ["m100", "m101"])                            # only then older rows

    def test_passed_moments_and_videos_with_a_full_record_are_skipped(self):
        rows = [row(1, 1), row(2, 2), row(3, 3, vid="vfull")]
        picks, _ = W.pick(rows, {"m001"}, full=lambda v: v == "vfull")
        self.assertEqual([r["moment_id"] for r in picks], ["m002"])

    def test_the_window_pads_45_s_and_stays_inside_the_video(self):
        self.assertEqual(W.window(row(1, 1, start=100.0, end=112.5)), (55.0, 157.5))
        self.assertEqual(W.window(row(1, 1, start=20.0, end=30.0)), (0.0, 75.0))
        self.assertEqual(W.window(row(1, 1, start=900.0, end=950.0), duration=960.0), (855.0, 960.0))
        with self.assertRaises(ValueError):
            W.window(row(1, 1, start=990.0, end=995.0), duration=900.0)


class TestRecord(unittest.TestCase):
    META = {"video_id": "vX", "canonical_url": "https://www.youtube.com/watch?v=vX", "channel_id": "UCx",
            "channel_name": "X", "exact_title": "t", "published_at": "2026-11-12T10:00:00+00:00", "duration": 3600}

    def test_words_go_to_the_youtube_clock_with_the_window_and_their_own_sha(self):
        words = [{"word": "Bitcoin", "start": 1.0, "end": 1.4}, {"word": "wins.", "start": 1.5, "end": 1.9}]
        rec = W.make_record(self.META, words, words, {"still_unpunctuated": False}, 455.0, 560.0, "ab" * 32)
        self.assertEqual(rec["transcript_method"], "whisper_words_punct")
        self.assertEqual([(w["start"], w["end"]) for w in rec["words"]], [(456.0, 456.4), (456.5, 456.9)])
        self.assertEqual(rec["window"], {"start_s": 455.0, "end_s": 560.0, "clock": "youtube", "offset_s": 455.0})
        self.assertEqual(rec["words_sha256"], W.words_sha256(rec["words"]))
        self.assertEqual(rec["segments"], [{"start": 456.0, "end": 456.9, "text": "Bitcoin wins."}])
        moved = [dict(rec["words"][0], start=456.01)] + rec["words"][1:]
        self.assertNotEqual(W.words_sha256(moved), rec["words_sha256"])        # one word moved 10 ms: another sha


class TestAdapter(unittest.TestCase):
    def test_a_failing_or_refusing_adapter_is_never_an_empty_ledger(self):
        root = tempfile.mkdtemp(prefix="fake_ingest_")
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, "pipeline", "ingest"))
        open(os.path.join(root, "pipeline", "__init__.py"), "w").close()
        open(os.path.join(root, "pipeline", "ingest", "__init__.py"), "w").close()
        led = os.path.join(root, "pipeline", "ingest", "ledger.py")
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        with open(led, "w") as f:
            f.write("def best_unused_moments(*a, **k):\n    raise ValueError('opt-out list unreadable')\n")
        with self.assertRaisesRegex(RuntimeError, "the ledger adapter failed"):
            W.ledger_rows(now, ingest_root=root)
        with open(led, "w") as f:
            f.write("def best_unused_moments(*a, **k):\n    return [], {'contract': 'unavailable: drift'}\n")
        with self.assertRaisesRegex(RuntimeError, "the ledger adapter refused"):
            W.ledger_rows(now, ingest_root=root)
        with open(led, "w") as f:
            f.write("def best_unused_moments(*a, **k):\n    return [{'moment_id': 'm1'}], {'lines': 1}\n")
        self.assertEqual(W.ledger_rows(now, ingest_root=root)[0], [{"moment_id": "m1"}])


class TestCycle(unittest.TestCase):
    """A whole cycle on a scratch store: the GPU work and the downloads faked, the lease real (a private file)."""

    def setUp(self):
        self.store = tempfile.mkdtemp(prefix="wp_store_")
        self.addCleanup(shutil.rmtree, self.store)
        self.audio = os.path.join(self.store, "audio.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=400",
                        "-ac", "1", "-ar", "16000", self.audio], check=True)
        lease = os.path.join(self.store, "gpu1.lease")
        meta = dict(TestRecord.META, duration=400)
        self.rows = [row(1, 1, vid="vA", start=100.0, end=110.0), row(2, 2, vid="vB", start=200.0, end=220.0),
                     row(3, 3, vid="vB", start=300.0, end=310.0)]

        def fake_audio(vid):
            p = os.path.join(self.store, f"{vid}.wav")
            shutil.copy(self.audio, p)
            return p

        def fake_decode(wav):
            if wav.endswith("m003.wav"):
                raise RuntimeError("decoder crashed")
            w = [{"word": "Bitcoin", "start": 2.0, "end": 2.4}, {"word": "holds.", "start": 2.5, "end": 2.9}]
            return w, w, None

        self.patches = [mock.patch.object(W, "STORE", self.store),
                        mock.patch.object(W, "ROWS_FILE", os.path.join(self.store, "moments", "word_pass.jsonl")),
                        mock.patch.object(W, "CYCLES_FILE", os.path.join(self.store, "moments", "cycles.jsonl")),
                        mock.patch.object(W, "ledger_rows", lambda now: (self.rows, {"excluded": {}})),
                        mock.patch.object(W, "has_full_record", lambda v: False),
                        mock.patch.object(W.ts, "ensure_meta", lambda vid: dict(meta, video_id=vid)),
                        mock.patch.object(W.ts, "download_audio", fake_audio),
                        mock.patch.object(W.ts, "release_whisper", lambda: None),
                        mock.patch.object(W, "decode", fake_decode),
                        mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "1", "PP_GPU1_LEASE": lease})]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def rows_written(self):
        with open(W.ROWS_FILE) as f:
            return [json.loads(x) for x in f if x.strip()]

    def test_one_cycle_writes_records_rows_a_failure_and_the_report(self):
        rep = W.cycle()
        got = {r["moment_id"]: r for r in self.rows_written()}
        self.assertEqual(set(got), {"m001", "m002", "m003"})
        a = got["m001"]
        self.assertTrue(a["sentence_ready"])
        self.assertEqual(a["window"], [55.0, 155.0])
        path = os.path.join(self.store, a["window_record"])
        self.assertEqual(a["window_record"], "transcripts/vA/windows/55.000-155.000.whisper_words_punct.json")
        with open(path) as f:
            rec = json.load(f)
        self.assertEqual(rec["words"][0], {"word": "Bitcoin", "start": 57.0, "end": 57.4})
        self.assertEqual(W.ts.sha256_file(path), a["record_sha256"])
        self.assertEqual(got["m003"]["sentence_ready"], False)
        self.assertIn("decoder crashed", got["m003"]["error"])
        self.assertEqual((rep["picked"], rep["written"], rep["sentence_ready"], rep["failed"]), (3, 2, 2, 1))
        self.assertEqual((rep["channels"], rep["channels_ready"]), (3, 2))       # m003's channel produced nothing
        self.assertFalse(os.path.exists(os.path.join(self.store, "vA.wav")))       # each download deleted after cuts

    def test_a_record_written_before_a_crash_is_reused_never_decoded_again(self):     # batch 51 C2 (glm)
        W.cycle()
        os.remove(W.ROWS_FILE)                                                 # the rows were lost, the records stay
        calls = []
        with mock.patch.object(W, "decode", lambda wav: calls.append(wav) or ([], [], None)):
            W.cycle()
        got = {r["moment_id"]: r for r in self.rows_written()}
        self.assertTrue(got["m001"].get("reused") and got["m001"]["sentence_ready"])
        self.assertEqual(got["m001"]["record_sha256"], W.ts.sha256_file(os.path.join(self.store, got["m001"]["window_record"])))
        self.assertEqual([os.path.basename(c) for c in calls], ["m003.wav"])   # only the one with no record decodes

    def test_a_second_cycle_works_nothing_twice(self):
        W.cycle()
        rep = W.cycle()
        self.assertEqual(rep["picked"], 0)
        self.assertEqual(len(self.rows_written()), 3)

    def test_the_gpu1_lease_is_held_while_decoding_and_left_after_the_batch(self):
        import gpu0
        seen = []

        def spy(wav):
            seen.append(gpu0.held() if hasattr(gpu0, "held") else None)
            return [{"word": "Ok.", "start": 1.0, "end": 1.2}], [{"word": "Ok.", "start": 1.0, "end": 1.2}], None
        with mock.patch.object(W, "decode", spy):
            W.cycle()
        self.assertTrue(seen and all(seen), seen)
        self.assertFalse(gpu0.held())


class TestGpu1Only(unittest.TestCase):
    def test_the_worker_refuses_any_gpu_but_gpu1(self):
        for v in ("0", "", "0,1"):
            with self.subTest(cuda=v), mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": v}):
                with self.assertRaises(SystemExit):
                    W.main(["--once"])


if __name__ == "__main__":
    unittest.main()
