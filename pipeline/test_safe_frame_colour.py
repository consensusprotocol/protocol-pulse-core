#!/usr/bin/env python3
"""Nov 11 recut (runs/pinned_20261111_172202): the 9:16 final came out color_space=unknown because its first
part opened on a safe-frame shot (LETTERBOX_VF's colorlevels runs in RGB and the round trip drops the matrix
tag); decoders then read the whole video as BT.601 (G9 luma 14.47 instead of 14.74). A safe-frame part keeps
its source's bt709 tag; a speaker-crop part is unchanged.
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_safe_frame_colour.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import render_vertical as RV  # noqa: E402


def _nvenc():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return "h264_nvenc" in r.stdout and subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0


def _size(path):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()


def _colour(path):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=color_space,color_primaries,color_transfer", "-of", "csv=p=0", path],
                          capture_output=True, text=True).stdout.strip()


@unittest.skipUnless(_nvenc(), "reframe_auto encodes with h264_nvenc (GPU)")
class TestSafeFrameKeepsBt709(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="sfcol_")
        cls.src = os.path.join(cls.tmp, "src.mp4")       # a prepared-clip stand-in, tagged bt709 like ours
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:r=24:d=2",
                        "-f", "lavfi", "-i", "sine=f=440:d=2:sample_rate=48000", "-shortest",
                        "-vf", "setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                        "-color_trc", "bt709", "-c:a", "aac", cls.src], check=True)
        assert _colour(cls.src) == "bt709,bt709,bt709", _colour(cls.src)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _render(self, first_class):
        shots = [{"class": first_class, "start": 0.0, "end": 1.0, "face_cx": 960},
                 {"class": "single", "start": 1.0, "end": 2.0, "face_cx": 960}]
        out = os.path.join(self.tmp, f"out_{first_class}.mp4")
        ok, _ = RV.reframe_auto(self.src, out, "t", {"fps": 24, "width": 1920, "height": 1080, "shots": shots})
        self.assertTrue(ok)
        self.assertEqual(_size(out), "1080,1920")           # the 9:16 reframe (and its safe frame) really ran
        return _colour(out)

    def test_a_part_opening_on_a_safe_frame_keeps_bt709(self):
        self.assertEqual(self._render("screen"), "bt709,bt709,bt709")

    def test_a_part_opening_on_a_speaker_crop_is_unchanged(self):
        self.assertEqual(self._render("single"), "bt709,bt709,bt709")


if __name__ == "__main__":
    unittest.main()
