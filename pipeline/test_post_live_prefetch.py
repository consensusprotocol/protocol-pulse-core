"""RULING 142 (3), the route's missing half (Nov 23): a post_live stream's section download that TIMES OUT (U7X6kReXets,
19:03 and 19:48 ET) is cut from the whole stream before pinned.acquire asks for it, in the render and the pre-check."""
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import post_live_prefetch as P  # noqa: E402
import select_passages as SP  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="plp_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.run_dir = os.path.join(self.d, "run")
        self.cuts = []

        def timed_out(vid, lo, hi, run_dir, pad=15.0):             # the section download ran past its 120 s
            os.makedirs(os.path.join(run_dir, "sources"), exist_ok=True)
            return None

        def whole(vid, dl_start, dl_end, out, cookies=None):        # the whole-stream route, writing what it writes
            self.cuts.append((vid, dl_start, dl_end, out))
            with open(out, "wb") as f:
                f.write(b"\0" * 200_000)
            with open(out + ".post_live.json", "w") as f:
                json.dump({"route": "post_live_whole_stream", "video_id": vid, "window": [dl_start, dl_end]}, f)
            return True
        self.timed_out, self.whole = timed_out, whole


class TestPrefetch(Base):
    def test_a_timed_out_post_live_window_is_cut_from_the_whole_stream_and_acquire_finds_it(self):
        with mock.patch.object(SP, "_download_window", self.timed_out), mock.patch.object(SP, "_post_live_window", self.whole), \
                mock.patch.object(P, "live_status", return_value="post_live"):
            res = P.prefetch("U7X6kReXets", 2318.3, 2329.18, self.run_dir, log=lambda s: None)
        out = os.path.join(self.run_dir, "sources", "U7X6kReXets.mp4")
        self.assertEqual(res, (out, 2303.0))
        self.assertEqual(self.cuts, [("U7X6kReXets", 2303.0, 2329.18 + 15.0, out)])
        # pinned.acquire's own call (the real function): a cache hit at the same start, no download, the route marked
        with mock.patch.object(SP.subprocess, "run", side_effect=AssertionError("no download on a cache hit")):
            self.assertEqual(SP._download_window("U7X6kReXets", 2318.3, 2329.18, self.run_dir), (out, 2303.0))
        self.assertTrue(os.path.exists(out + ".post_live.json"))

    def test_a_window_that_downloads_is_used_and_nothing_is_probed(self):
        ok = ("/x/sources/v.mp4", 5.0)
        with mock.patch.object(SP, "_download_window", return_value=ok), \
                mock.patch.object(SP, "_post_live_window", side_effect=AssertionError("no whole stream")), \
                mock.patch.object(P, "live_status", side_effect=AssertionError("no probe")):
            self.assertEqual(P.prefetch("v", 20.0, 30.0, self.run_dir, log=lambda s: None), ok)

    def test_only_a_post_live_stream_takes_the_whole_stream_route(self):
        for status in ("was_live", "not_live", "is_live", None):
            with self.subTest(status=status), mock.patch.object(SP, "_download_window", self.timed_out), \
                    mock.patch.object(SP, "_post_live_window", self.whole), mock.patch.object(P, "live_status", return_value=status):
                self.assertIsNone(P.prefetch("v", 20.0, 30.0, self.run_dir, log=lambda s: None))
        self.assertEqual(self.cuts, [])

    def test_no_media_from_the_whole_stream_is_no_source(self):
        with mock.patch.object(SP, "_download_window", self.timed_out), \
                mock.patch.object(SP, "_post_live_window", return_value=False), mock.patch.object(P, "live_status", return_value="post_live"):
            self.assertIsNone(P.prefetch("v", 20.0, 30.0, self.run_dir, log=lambda s: None))


class TestCallers(Base):
    def test_the_render_prefetches_every_youtube_window_before_prepare(self):
        import run_fresh as RF
        pin = os.path.join(self.d, "pin.json")
        with open(pin, "w") as f:
            json.dump({"segments": [{"video_id": "a", "start": 10.0, "end": 20.0},
                                    {"video_id": "b", "start": 5.0, "end": 9.0, "source": {"kind": "youtube"}},
                                    {"video_id": "a", "start": 40.0, "end": 50.0},
                                    {"video_id": "c", "start": 1.0, "end": 2.0, "source": {"kind": "local_file"}}]}, f)
        calls, order = [], []
        run = types.SimpleNamespace(dir=self.run_dir)
        with mock.patch.object(P, "prefetch", lambda v, lo, hi, d, log=print: calls.append((v, lo, hi, d))):
            RF.prefetch_post_live(run, pin)
        self.assertEqual(calls, [("a", 10.0, 50.0, self.run_dir), ("b", 5.0, 9.0, self.run_dir)])

        class Stop(Exception):
            pass

        def prepare(pin_path, run_dir, log=print):
            order.append("prepare")
            raise Stop
        import pinned
        run = types.SimpleNamespace(dir=self.run_dir, status={}, prov={})
        with mock.patch.object(RF, "free_gpu0_for_whisper", lambda run, stage: None), \
                mock.patch.object(RF, "prefetch_post_live", lambda run, p: order.append("prefetch")), \
                mock.patch.object(RF, "pin_admissible", lambda p: order.append("admissible") or (True, "stub")), \
                mock.patch.object(pinned, "prepare", prepare):
            with self.assertRaises(Stop):
                RF.stage_pinned(run, pin)
        self.assertEqual(order, ["admissible", "prefetch", "prepare"])  # readiness first (rows 13 / 18, Nov 24)

    def test_an_unreadable_pin_is_left_to_prepare(self):
        import run_fresh as RF
        bad = os.path.join(self.d, "bad.json")
        with open(bad, "w") as f:
            f.write("{")
        with mock.patch.object(P, "prefetch", side_effect=AssertionError("nothing to fetch")):
            RF.prefetch_post_live(types.SimpleNamespace(dir=self.run_dir), bad)

    def test_the_lock_precheck_prefetches_through_the_route(self):
        import lock_precheck as LP
        r = {"segments": [{"video_id": "U7X6kReXets", "start": 2318.3, "end": 2329.18, "role": "clip"}]}
        calls = []
        with mock.patch.object(LP, "ROOT", self.d), \
                mock.patch.object(P, "prefetch", lambda v, lo, hi, d, log=print: calls.append((v, lo, hi, d))):
            LP.prefetch(r, "0" * 64)
            want = LP.work_dir("U7X6kReXets", 2318.3, 2329.18, "0" * 64)
        self.assertEqual(calls, [("U7X6kReXets", 2318.3, 2329.18, want)])
        self.assertTrue(want.startswith(self.d))


if __name__ == "__main__":
    unittest.main()
