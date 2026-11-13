#!/usr/bin/env python3
"""Nov 11 recut (runs/pinned_20261111_172202): the 9:16 final came out color_space=unknown because its first
part opened on a safe-frame shot (LETTERBOX_VF's colorlevels runs in RGB and the round trip drops the matrix
tag); decoders then read the whole video as BT.601 (G9 luma 14.47 instead of 14.74). A safe-frame part keeps
its source's bt709 tag; a speaker-crop part is unchanged. Nov 13 (runs pinned_20261113_031328 / _191409): a part
opening on a STACK2 shot came out with all four tags unknown, and so did the final (G9 13.6 vs 14.73, every source
BT.709): every shot re-declares the input's colour now.
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_safe_frame_colour.py"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import render_vertical as RV  # noqa: E402


def _nvenc():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True)
    return "h264_nvenc" in r.stdout and subprocess.run(["nvidia-smi"], capture_output=True).returncode == 0


def _size(path):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                           "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()


def _range(path):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_range",
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
                        "-color_trc", "bt709", "-color_range", "tv", "-c:a", "aac", cls.src], check=True)
        assert _colour(cls.src) == "bt709,bt709,bt709", _colour(cls.src)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _render(self, first_class):
        shots = [{"class": first_class, "start": 0.0, "end": 1.0, "face_cx": 960, "band_cx": [480, 1440],
                  "band_cy": [540, 540]},
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

    def test_a_part_opening_on_a_stack2_keeps_bt709_and_its_range(self):
        self.assertEqual(self._render("stack2"), "bt709,bt709,bt709")
        self.assertEqual(_range(os.path.join(self.tmp, "out_stack2.mp4")), "tv")


class TestEveryShotRedeclaresTheColour(unittest.TestCase):
    """CPU: the filter graph reframe_auto runs, and the probe it reads (no GPU, no encode)."""

    def test_every_shot_ends_on_the_inputs_colour(self):
        colour = "range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709"
        shots = [{"class": "stack2", "start": 0.0, "end": 1.0, "band_cx": [480, 1440], "band_cy": [540, 540]},
                 {"class": "single", "start": 1.0, "end": 2.0, "face_cx": 960},
                 {"class": "screen", "start": 2.0, "end": 3.0}]
        ran = []
        ok = mock.Mock(returncode=0, stderr=b"")
        with mock.patch.object(RV, "_input_colour", lambda p: colour), \
                mock.patch.object(RV.subprocess, "run", lambda cmd, **k: ran.append(cmd) or ok), \
                mock.patch("gpu0.swap_to", lambda *a, **k: None), mock.patch("gpu0.raise_if_oom", lambda *a, **k: None):
            self.assertTrue(RV.reframe_auto("in.mp4", "out.mp4", "t", {"fps": 24, "width": 1920, "height": 1080,
                                                                         "shots": shots})[0])
        graph = ran[0][ran[0].index("-filter_complex") + 1]
        for k in range(3):
            self.assertIn(f",setparams={colour},setsar=1:1[v{k}]", graph)

    def test_the_probe_keeps_known_values_only(self):
        def probe(out):
            return mock.patch.object(RV.subprocess, "run", lambda cmd, **k: mock.Mock(stdout=out))
        with probe("color_range=tv\ncolor_space=bt709\ncolor_transfer=bt709\ncolor_primaries=bt709\n"):
            self.assertEqual(RV._input_colour("x.mp4"), "range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709")
        with probe("color_range=unknown\ncolor_space=smpte170m\ncolor_transfer=unknown\ncolor_primaries=bt470bg\n"):
            self.assertEqual(RV._input_colour("x.mp4"), "color_primaries=bt470bg:colorspace=smpte170m")
        with probe("color_range=unknown\ncolor_space=unknown\ncolor_transfer=unknown\ncolor_primaries=unknown\n"):
            self.assertEqual(RV._input_colour("x.mp4"), "")


if __name__ == "__main__":
    unittest.main()
