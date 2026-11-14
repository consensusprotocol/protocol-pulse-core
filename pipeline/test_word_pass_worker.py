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

import datetime as _dt                                                   # a fixed clock: never the wall clock
NOW = _dt.datetime(2026, 11, 13, 6, 0, tzinfo=_dt.timezone.utc)


def row(i, ch, vid=None, start=100.0, end=112.0, pub="2026-11-13T03:00:00+00:00"):   # 3 h before NOW: the 6 h tier
    return {"moment_id": f"m{i:03d}", "video_id": vid or f"v{ch}", "channel_id": f"UC{ch}", "start": start, "end": end,
            "published_at": pub}


class TestPickAndWindow(unittest.TestCase):
    def test_at_most_seven_per_channel_so_forty_span_six_channels(self):
        self.assertEqual(W.PER_CHANNEL, -(-W.PER_CYCLE // W.MIN_CHANNELS))     # the cap still makes 6 channels
        rows = [row(i, i % 8 if i >= 30 else 0) for i in range(80)]           # the top 30 all from one channel
        picks, nch = W.pick(rows, set(), full=lambda v: False, per_cycle=40, per_channel=7, now=NOW)
        self.assertEqual(len(picks), 40)
        self.assertGreaterEqual(nch, W.MIN_CHANNELS)
        per = {}
        for r in picks:
            per[r["channel_id"]] = per.get(r["channel_id"], 0) + 1
        self.assertLessEqual(max(per.values()), 7)
        self.assertEqual(picks[0]["moment_id"], "m000")                       # rank order kept

    def test_five_channels_of_ten_give_thirty_five_and_a_sixth_channel_fills_in(self):   # audit batch 51 C1
        # ruling 77.4: every row is in a 6 h / 12 h tier, filled capped (7 a channel) and then by the tier's uncapped rest
        five = [row(i, i // 10) for i in range(50)]                            # ranked: ch0 x10, ch1 x10, ... ch4 x10
        picks, nch = W.pick(five, set(), full=lambda v: False, per_cycle=40, per_channel=7, now=NOW)
        ids = [r["moment_id"] for r in picks]
        self.assertEqual((len(picks), nch), (40, 5))                           # 35 capped, then 5 of the rest
        self.assertEqual(ids[35:], ["m007", "m008", "m009", "m017", "m018"])
        six = five + [row(100 + i, 9) for i in range(3)]                       # three lower-ranked rows of a 6th
        picks, nch = W.pick(six, set(), full=lambda v: False, per_cycle=40, per_channel=7, now=NOW)
        ids = [r["moment_id"] for r in picks]
        self.assertEqual((len(picks), nch), (40, 6))
        self.assertEqual(ids[35:38], ["m100", "m101", "m102"])                 # the 6th channel before any uncapped row

    def test_ruling_77_4_the_last_six_hours_first_then_six_to_twelve_nothing_older(self):
        import datetime as dt
        now = dt.datetime(2026, 11, 13, 6, 0, tzinfo=dt.timezone.utc)
        old = [row(i, i, pub="2026-11-12T10:00:00+00:00") for i in range(10)]                # ranked first, 20 h old
        fresh = [row(100 + i, 50 + i, pub="2026-11-13T01:00:00+00:00") for i in range(3)]    # ranked last, 5 h old
        edge = [row(200, 70, pub="2026-11-13T00:00:00+00:00"), row(201, 71, pub="2026-11-12T23:59:59+00:00"),
                row(202, 72, pub="2026-11-12T18:00:00+00:00"), row(203, 73, pub="2026-11-12T17:59:59+00:00")]
        picks, _ = W.pick(old + fresh + edge, set(), full=lambda v: False, per_cycle=20, now=now)
        self.assertEqual([r["moment_id"] for r in picks],                                 # 6 h and 12 h are inclusive
                         ["m100", "m101", "m102", "m200", "m201", "m202"])               # 12 h + 1 s and 20 h: never
        self.assertFalse(W.is_fresh(row(1, 1, pub="2026-11-13T07:00:00+00:00"), now))        # a future time is not fresh
        self.assertFalse(W.is_fresh(row(1, 1, pub="2026-11-13T01:00:00"), now))              # no offset: not measured
        self.assertTrue(W.is_fresh(row(1, 1, pub="2026-11-13T01:00:00Z"), now))              # 'Z' as the ledger reads it
        self.assertFalse(W.is_fresh(row(1, 1, pub=None), now))

    def test_order_0155_a_capped_channels_fresh_rows_still_come_before_older_rows(self):
        import datetime as dt
        now = dt.datetime(2026, 11, 13, 6, 0, tzinfo=dt.timezone.utc)
        fresh = [row(i, 1, pub="2026-11-13T02:00:00+00:00") for i in range(10)]            # one channel, 10 fresh
        older = [row(100 + i, 2 + i, pub="2026-11-12T22:00:00+00:00") for i in range(10)]   # 8 h old, ranked above
        picks, _ = W.pick(older + fresh, set(), full=lambda v: False, per_cycle=12, now=now)
        ids = [r["moment_id"] for r in picks]
        self.assertEqual(ids[:10], [f"m{i:03d}" for i in range(10)])          # 7 capped, then the other 3 fresh
        self.assertEqual(ids[10:], ["m100", "m101"])                            # only then the 6-12 h rows

    def test_ruling_77_4_six_hours_then_six_to_twelve_and_never_a_day_old(self):
        import datetime as dt
        now = dt.datetime(2026, 11, 13, 6, 0, tzinfo=dt.timezone.utc)
        older = [row(i, 10 + i, pub="2026-11-11T06:00:00+00:00") for i in range(3)]      # 48 h old, ranked first
        day = [row(100 + i, 20 + i, pub="2026-11-12T12:00:00+00:00") for i in range(3)]   # 18 h old
        twelve = [row(300 + i, 40 + i, pub="2026-11-12T21:00:00+00:00") for i in range(3)]  # 9 h old
        six = [row(200 + i, 30 + i, pub="2026-11-13T02:00:00+00:00") for i in range(3)]   # 4 h old, ranked last
        picks, _ = W.pick(older + day + twelve + six, set(), full=lambda v: False, per_cycle=12, now=now)
        self.assertEqual([r["moment_id"] for r in picks],
                         ["m200", "m201", "m202", "m300", "m301", "m302"])               # nothing over 12 h
        self.assertEqual((W.FRESH_H, W.DAY_H, W.HORIZON_H), (6, 12, 12))

    def test_passed_moments_and_videos_with_a_full_record_are_skipped(self):
        rows = [row(1, 1), row(2, 2), row(3, 3, vid="vfull")]
        picks, _ = W.pick(rows, {"m001"}, full=lambda v: v == "vfull", now=NOW)
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
        stamp = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)).isoformat()   # W.cycle() runs on the
        for r in self.rows:                                                   # wall clock: an hour old is the 6 h tier
            r["published_at"] = stamp

        def fake_audio(vid):
            p = os.path.join(self.store, f"{vid}.wav")
            shutil.copy(self.audio, p)
            return p

        def fake_decode(wav):
            if wav.endswith("m003.wav"):
                return RuntimeError("decoder crashed")
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
                        mock.patch.object(W, "decode_batch", lambda wavs: [fake_decode(w) for w in wavs]),
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
        with mock.patch.object(W, "decode_batch", lambda wavs: [calls.append(w) or ([], [], None) for w in wavs]):
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

        def spy(wavs):
            seen.append(gpu0.held())
            w = [{"word": "Ok.", "start": 1.0, "end": 1.2}]
            return [(w, w, None) for _ in wavs]
        with mock.patch.object(W, "decode_batch", spy):
            rep = W.cycle()
        self.assertEqual(rep["batches"], 1)
        for k in ("fetch_s", "lease_wait_s", "foreign_wait_s", "gpu_s"):
            self.assertIsInstance(rep[k], float)
        self.assertTrue(seen and all(seen), seen)
        self.assertFalse(gpu0.held())


class TestDecodeBatch(unittest.TestCase):
    """Order '02:46': ONE load of each model per batch (before: two swaps per moment), the punctuation reference only
    where the verbatim words need it, and a failed window never stops the others."""

    def test_each_model_is_loaded_once_per_batch_and_the_reference_only_where_needed(self):
        loads = []

        class Seg:
            def __init__(self, ws):
                self.words = ws

        class Word:
            def __init__(self, w, s, e):
                self.word, self.start, self.end = w, s, e

        class Model:
            def transcribe(self, wav, **k):
                if wav == "bad.wav":
                    return iter([]), None
                last = "ends." if wav == "clean.wav" else "ends"
                return iter([Seg([Word("It", 0.0, 0.2), Word(last, 0.3, 0.6)])]), None

        def whisper():
            loads.append("verbatim")
            return Model()

        def reference():
            loads.append("reference")
            return Model()
        import punctuation
        with mock.patch.object(W.ts, "_whisper", whisper), mock.patch.object(W.ts, "_reference", reference), \
                mock.patch.object(punctuation, "needs_restoration", lambda words: not words[-1]["word"].endswith(".")), \
                mock.patch.object(punctuation, "ensure", lambda rec, wav, model, **k: dict(rec, punctuation={"x": 1})):
            out = W.decode_batch(["clean.wav", "raw1.wav", "bad.wav", "raw2.wav"])
        self.assertEqual(out[0][2], None)                                     # needed no reference
        self.assertEqual((out[1][2], out[3][2]), ({"x": 1}, {"x": 1}))
        self.assertIsInstance(out[2], Exception)                              # one window failed, the others ran
        # the ORDER is the property (batch 55 C2): no reference call before the last verbatim call, so the model on
        # the GPU changes ONCE per batch; ts._whisper / ts._reference return the resident model without reloading
        # (gpu0.whisper -> swap_to loads only a model that is not resident)
        last_verbatim = max(i for i, c in enumerate(loads) if c == "verbatim")
        first_reference = loads.index("reference")
        self.assertLess(last_verbatim, first_reference)
        self.assertEqual((loads.count("verbatim"), loads.count("reference")), (4, 2))   # bad.wav needs no reference


class TestFetchFailure(TestCycle):
    def test_a_fetch_that_dies_writes_failure_rows_and_the_cycle_goes_on(self):          # batch 55 C1
        real = W._fetch

        def dying(vid, rows, tmp, hold=None):
            if vid == "vB":
                raise OSError("sha256 read failed")
            return real(vid, rows, tmp, hold)
        with mock.patch.object(W, "_fetch", dying):
            rep = W.cycle()
        got = {r["moment_id"]: r for r in self.rows_written()}
        self.assertTrue(got["m001"]["sentence_ready"])
        self.assertIn("fetch: OSError: sha256 read failed", got["m002"]["error"])
        self.assertIn("fetch: OSError", got["m003"]["error"])
        self.assertEqual((rep["written"], rep["failed"]), (1, 2))


BOT = ("acquisition: AcquisitionError: audio download failed: ERROR: [youtube] x: Sign in to confirm you're not a bot. "
       "Use --cookies-from-browser or --cookies for the authentication.")


class TestPlatformBlock(unittest.TestCase):
    """2026-11-13 04:47: YouTube refused every request and 330 moments got failure rows in 2 minutes. A failure in
    YouTube's sign-in wording is checked ONCE per cycle against a control video: refused too = the platform's (no row,
    the cycle stops, retried later); answered = that video's own (written, control_ok)."""

    def setUp(self):
        TestCycle.setUp(self)

    def rows_written(self):
        return TestCycle.rows_written(self) if os.path.exists(W.ROWS_FILE) else []

    def blocked_audio(self, vid):
        raise W.ts.AcquisitionError("audio download failed: ERROR: [youtube] x: Sign in to confirm you're not a bot. "
                                    "Use --cookies-from-browser or --cookies for the authentication.")

    def test_a_platform_block_writes_no_row_and_the_moments_come_back_when_it_clears(self):
        calls = []
        with mock.patch.object(W.ts, "download_audio", self.blocked_audio), \
                mock.patch.object(W, "control_ok", lambda: calls.append(1) or False):
            rep = W.cycle()
        self.assertEqual(self.rows_written(), [])                             # nothing burned
        self.assertEqual((rep["failed"], rep["blocked_rows"], len(calls)), (0, 3, 1))   # one control request
        self.assertIn("control video", rep["blocked"])
        self.assertEqual(W.passed_ids(), set())
        rep = W.cycle()                                                       # the platform answers again
        got = {r["moment_id"]: r for r in self.rows_written()}
        self.assertEqual(set(got), {"m001", "m002", "m003"})
        self.assertTrue(got["m001"]["sentence_ready"])
        self.assertIsNone(rep["blocked"])

    def test_the_videos_own_sign_in_failure_is_written_with_control_ok_and_not_retried(self):
        failed, cycles = 0, 0
        with mock.patch.object(W.ts, "download_audio", self.blocked_audio), mock.patch.object(W, "control_ok", lambda: True):
            while cycles < 4:                     # a fetch that starts after the first sign-in failure is skipped
                rep = W.cycle()                   # (batch 60 C1) and picked again by the next cycle
                cycles += 1
                if not rep["picked"]:
                    break
                failed += rep["failed"]
                self.assertIsNone(rep["blocked"])
        rows = self.rows_written()
        self.assertEqual((failed, len(rows), rep["picked"]), (3, 3, 0))
        self.assertTrue(all(r.get("control_ok") is True and W.BLOCK.search(r["error"]) for r in rows), rows)
        self.assertEqual(W.passed_ids(), {"m001", "m002", "m003"})

    def test_a_fetch_starting_after_a_sign_in_failure_makes_no_request(self):          # batch 60 C1
        import threading
        hold, asked = threading.Event(), []
        with mock.patch.object(W.ts, "ensure_meta", lambda vid: asked.append(("meta", vid)) or {"duration": 400}), \
                mock.patch.object(W.ts, "download_audio", lambda vid: asked.append(("audio", vid)) or self.blocked_audio(vid)):
            jobs, fails, _ = W._fetch("vA", [self.rows[0]], self.store, hold)
            self.assertTrue(hold.is_set())                                     # set by the failure, in its thread
            self.assertTrue(W.blocked_failure(fails[0][1]))
            jobs, fails, secs = W._fetch("vB", self.rows[1:], self.store, hold)
        self.assertEqual(asked, [("meta", "vA"), ("audio", "vA")])               # vB never asked the platform
        self.assertEqual((jobs, [w for _, w in fails], secs), ([], [W.SKIPPED, W.SKIPPED], 0.0))

    def test_an_old_sign_in_failure_row_without_control_ok_is_retried_once_and_other_rows_are_not(self):
        os.makedirs(os.path.dirname(W.ROWS_FILE), exist_ok=True)
        with open(W.ROWS_FILE, "w") as f:
            for mid, err in (("m001", BOT), ("m002", "acquisition: AcquisitionError: metadata unavailable: Video unavailable"),
                             ("m003", "word pass: RuntimeError: decoder crashed")):
                f.write(json.dumps({"moment_id": mid, "video_id": "v", "sentence_ready": False, "error": err}) + "\n")
        self.assertEqual(W.passed_ids(), {"m002", "m003"})
        self.assertFalse(W.blocked_failure("word pass: RuntimeError: Sign in to confirm"))   # acquisition only
        self.assertFalse(W.blocked_failure(None))

    def test_a_non_sign_in_acquisition_failure_never_asks_the_control(self):
        def gone(vid):
            raise W.ts.AcquisitionError("audio download failed: ERROR: Video unavailable")
        with mock.patch.object(W.ts, "download_audio", gone), \
                mock.patch.object(W, "control_ok", lambda: self.fail("the control was asked")):
            rep = W.cycle()
        self.assertEqual((rep["failed"], rep["blocked_rows"]), (3, 0))
        self.assertTrue(all("control_ok" not in r for r in self.rows_written()))

    def test_the_control_is_the_stores_own_ytdlp_call(self):
        seen = []

        def fake(args, timeout=120):
            seen.append(args)
            return subprocess.CompletedProcess(args, 0, W.CONTROL_VIDEO + "\n", "")
        with mock.patch.object(W.ts, "_ytdlp", fake):
            self.assertTrue(W.control_ok())
        self.assertEqual(seen, [["--skip-download", "--print", "id", W.ts.canonical_url(W.CONTROL_VIDEO)]])
        for res in (subprocess.CompletedProcess([], 1, "", "Sign in to confirm"), subprocess.CompletedProcess([], 0, "", "")):
            with mock.patch.object(W.ts, "_ytdlp", lambda args, timeout=120, res=res: res):
                self.assertFalse(W.control_ok())
        with mock.patch.object(W.ts, "_ytdlp", mock.Mock(side_effect=subprocess.TimeoutExpired("yt-dlp", 60))):
            self.assertFalse(W.control_ok())

    def test_a_blocked_cycle_sleeps_before_the_next(self):
        sleeps = []

        def stop(s):
            sleeps.append(s)
            raise KeyboardInterrupt
        with mock.patch.object(W, "cycle", lambda limit=None: {"picked": 3, "blocked": "x"}), \
                mock.patch.object(W.time, "sleep", stop):
            with self.assertRaises(KeyboardInterrupt):
                W.main(["--sleep", "7"])
        self.assertEqual(sleeps, [7.0])


class TestGpu1Only(unittest.TestCase):
    def test_the_worker_refuses_any_gpu_but_gpu1(self):
        for v in ("0", "", "0,1"):
            with self.subTest(cuda=v), mock.patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": v}):
                with self.assertRaises(SystemExit):
                    W.main(["--once"])


if __name__ == "__main__":
    unittest.main()
