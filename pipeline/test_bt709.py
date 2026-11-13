#!/usr/bin/env python3
"""Ruling 30 (orchestrator 2026-11-13 '01:55'): a BT.601 source is converted to BT.709 at prepare, so it reads, and its
final's tail measures, as a 709 source. The fixture is pin #1's own hook source (run pinned_20261113_054035,
Sjb6lUiL0m4: tv / smpte170m matrix / bt709 primaries and transfer), a 4 s span stream-copied into a scratch run.
must-pass  the converted source: tags bt709 x3 + tv; the same frames, frame times and audio bytes; the same picture
           (RGB within 1 level, each decoded with its own matrix); G9's own decode path (ffmpeg PNG -> OpenCV gray)
           within 0.2 of the original's
must-not   a 709 source or an untagged source is touched; a failed conversion leaves the source and holds the run"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import run_fresh as rf  # noqa: E402

HOOK = os.path.join(REPO, "runs", "pinned_20261113_054035", "sources", "Sjb6lUiL0m4.mp4")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def probe(p, entries, sel="v:0"):
    return subprocess.run(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries", entries, "-of", "csv=p=0",
                           p], capture_output=True, text=True).stdout.strip()


def pts(p):                                             # presentation times, sorted: the packet ORDER may differ
    return sorted(float(x) for x in probe(p, "packet=pts_time").split())   # (the lossless encode uses B-frames)


def rgb(path, t, matrix):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-vf",
                          f"scale=in_color_matrix={matrix}:in_range=tv,format=rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(float)


def g9_gray(path, t):                                   # gate_g9's own path: ffmpeg PNG (its default decode), cv2 gray
    import cv2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", path, "-frames:v", "1", "-f", "image2pipe",
                          "-vcodec", "png", "-"], capture_output=True).stdout
    return float(cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE).mean())


class TestBt709(unittest.TestCase):
    def setUp(self):
        self.run = tempfile.mkdtemp(prefix="bt709_")
        self.addCleanup(shutil.rmtree, self.run)
        os.makedirs(os.path.join(self.run, "sources"))

    def src(self, vid):
        return os.path.join(self.run, "sources", f"{vid}.mp4")

    @unittest.skipUnless(os.path.isfile(HOOK), "pin #1's hook source is not on this machine")
    def test_the_bt601_hook_becomes_bt709_with_the_same_frames_audio_and_picture(self):
        s = self.src("Sjb6lUiL0m4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "14", "-t", "4", "-i", HOOK, "-map", "0", "-c", "copy", s],
                       check=True)
        self.assertEqual(probe(s, "stream=color_space"), "smpte170m")
        before_sha = sha(s)
        frames, times = probe(s, "stream=nb_frames,duration"), pts(s)
        rec = rf.to_bt709(self.run, ["Sjb6lUiL0m4", "Sjb6lUiL0m4"])["Sjb6lUiL0m4"]
        self.assertEqual(probe(s, "stream=color_space,color_primaries,color_transfer,color_range"),
                         "tv,bt709,bt709,bt709")
        keep = os.path.join(self.run, rec["original"])
        self.assertEqual((sha(keep), rec["original_sha256"], rec["converted_sha256"]), (before_sha, before_sha, sha(s)))
        self.assertEqual((probe(s, "stream=nb_frames,duration"), pts(s)), (frames, times))   # every frame time kept
        md5 = [subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", "0:a", "-c", "copy", "-f", "framemd5", "-"],
                              capture_output=True, text=True).stdout.split("\n", 8)[-1] for p in (keep, s)]
        self.assertEqual(md5[0], md5[1])                                          # the audio: copied
        for t in (0.5, 2.0, 3.5):
            self.assertLess(np.abs(rgb(keep, t, "bt601") - rgb(s, t, "bt709")).mean(), 1.0)
            self.assertLess(abs(g9_gray(keep, t) - g9_gray(s, t)), 0.2)

    def test_a_bt709_or_untagged_source_is_never_touched(self):
        for vid, tags in (("v709", ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                                    "-color_range", "tv"]), ("vunk", [])):
            with self.subTest(vid=vid):
                s = self.src(vid)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=24:duration=1",
                                "-c:v", "libx264", "-pix_fmt", "yuv420p", *tags, s], check=True)
                before = sha(s)
                self.assertEqual(rf.to_bt709(self.run, [vid]), {})
                self.assertEqual(sha(s), before)
        self.assertFalse(os.path.exists(os.path.join(self.run, "sources_bt601")))

    def test_a_source_declaring_only_its_bt601_matrix_converts_with_the_matrix_defaults(self):   # batch 54 C1
        for space, rng in (("smpte170m", "tv"), ("bt470bg", "tv"), ("smpte170m", "pc")):
            with self.subTest(space=space, range=rng):
                vid = f"v_{space}_{rng}"
                s = self.src(vid)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                                "testsrc=size=320x180:rate=24:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                "-colorspace", space, "-color_range", rng, s], check=True)
                rec = rf.to_bt709(self.run, [vid])[vid]                  # primaries / transfer undeclared
                self.assertIn(f"iprimaries={space}:itrc={space}:irange={rng}", rec["filter"])
                self.assertEqual(probe(s, "stream=color_space,color_primaries,color_transfer,color_range"),
                                 "tv,bt709,bt709,bt709")

    def test_a_failed_conversion_holds_and_leaves_the_source(self):
        s = self.src("v601")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=24:duration=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-colorspace", "smpte170m", "-color_range", "tv", s],
                       check=True)
        before, real = sha(s), subprocess.run

        def fail_ffmpeg(cmd, *a, **k):
            if cmd and cmd[0] == "ffmpeg":
                return subprocess.CompletedProcess(cmd, 1, "", "colorspace: unsupported input")
            return real(cmd, *a, **k)
        with mock.patch.object(rf.subprocess, "run", fail_ffmpeg):
            with self.assertRaisesRegex(rf.Hold, "ruling 30: the BT.601 -> BT.709 conversion of v601 failed"):
                rf.to_bt709(self.run, ["v601"])
        self.assertEqual(sha(s), before)
        self.assertEqual([n for n in os.listdir(os.path.join(self.run, "sources")) if n != "v601.mp4"], [])


if __name__ == "__main__":
    unittest.main()
