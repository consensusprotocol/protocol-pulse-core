#!/usr/bin/env python3
"""DEC-12a (orchestrator 2026-11-11 14:45): G9's floor per format = v2f's measured tail luma minus the MEASURED
re-encode spread of the same locked outro (docs/audits/pulse-sentence-law/dec12a_g9_spread/spread.json);
outro_locked (the locked brand asset was used) stays the hard row.
must-pass  v2f's finals; the Nov 11 recut preview's finals (the same locked outro, another encode)
must-fail  a tail 1.0 luma code darker than v2f's; a tail that is not the locked outro (black); a conform
           fallback fails outro_locked even when its luma clears the floor
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_g9_floor.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
sys.path.insert(0, os.path.join(REPO, "segment_v1"))
import qa_gates as Q  # noqa: E402

V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run", "out")
PREVIEW = os.path.join(REPO, "runs", "pinned_20261111_172202_replay_cut1329_replay_preview", "out")
FINALS = {"16x9": "segment.mp4", "9x16": "segment_vertical.mp4"}


def _tail_variant(src, dst, vf):
    """The last 3 s of a final, picture changed by `vf`, tagged like the finals, audio kept."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-3", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "10",
                    "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                    "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", dst], check=True)


class TestG9Floor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="g9floor_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_floor_is_v2f_minus_the_measured_spread(self):
        spread = json.load(open(os.path.join(REPO, "docs", "audits", "pulse-sentence-law", "dec12a_g9_spread",
                                             "spread.json")))
        for fmt in ("16x9", "9x16"):
            self.assertEqual(Q.G9_REENCODE_SPREAD[fmt], spread[fmt]["spread_rounded"])     # exactly the rule
            self.assertLessEqual(Q.G9_REENCODE_SPREAD[fmt], 0.05)
            self.assertAlmostEqual(Q.G9_LUMA_FLOOR[fmt], Q.G9_V2F_LUMA[fmt] - Q.G9_REENCODE_SPREAD[fmt], places=4)

    @unittest.skipUnless(os.path.isdir(V2F), "frozen v2f reference not on this machine")
    def test_v2f_finals_pass(self):
        for fmt, name in FINALS.items():
            ok, d = Q.gate_g9(os.path.join(V2F, name), self.tmp, fmt=fmt)
            self.assertTrue(ok, (fmt, d))

    @unittest.skipUnless(all(os.path.exists(os.path.join(PREVIEW, n)) for n in FINALS.values()),
                         "Nov 11 preview finals not on this machine")
    def test_another_encode_of_the_same_locked_outro_passes(self):
        for fmt, name in FINALS.items():
            ok, d = Q.gate_g9(os.path.join(PREVIEW, name), self.tmp, fmt=fmt)
            self.assertTrue(ok, (fmt, d))

    @unittest.skipUnless(os.path.isdir(V2F), "frozen v2f reference not on this machine")
    def test_a_tail_one_luma_code_darker_fails(self):
        for fmt, name in FINALS.items():
            out = os.path.join(self.tmp, f"darker_{fmt}.mp4")
            _tail_variant(os.path.join(V2F, name), out, "lutyuv=y=val-1")
            ok, d = Q.gate_g9(out, self.tmp, fmt=fmt)
            self.assertFalse(ok, (fmt, d))

    @unittest.skipUnless(os.path.isdir(V2F), "frozen v2f reference not on this machine")
    def test_a_tail_that_is_not_the_locked_outro_fails(self):
        out = os.path.join(self.tmp, "black_16x9.mp4")
        _tail_variant(os.path.join(V2F, FINALS["16x9"]), out, "lutyuv=y=16:u=128:v=128")
        ok, d = Q.gate_g9(out, self.tmp, fmt="16x9")
        self.assertFalse(ok, d)

    def test_a_conform_fallback_fails_outro_locked_even_when_g9_passes(self):
        import run_fresh as rf
        self.assertEqual(rf.tail_rows(True, True), {"G9_tail": "PASS", "outro_locked": "FAIL"})
        self.assertEqual(rf.tail_rows(True, False), {"G9_tail": "PASS", "outro_locked": "PASS"})


if __name__ == "__main__":
    unittest.main()
