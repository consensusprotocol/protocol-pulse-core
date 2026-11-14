#!/usr/bin/env python3
"""Ruling 29 (orchestrator 2026-11-13 '01:55'): the finals' loudness corrected to -14 LUFS before the gates. On
synthetic finals: a quiet pair is corrected (both within TOL_LU, TP <= -2.0), the video streams are untouched and the
9:16 carries exactly the 16:9's corrected audio (Law 23); a pair within tolerance is never rewritten; a failing step or
an off-target re-measure keeps the rendered finals as they were, with no temp file left."""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import loudness as LD  # noqa: E402


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def stream_md5(p, sel):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", sel, "-c", "copy", "-f", "framemd5", "-"],
                         capture_output=True, text=True).stdout
    return hashlib.md5("\n".join(l.split(",")[-1] for l in out.splitlines() if l and not l.startswith("#")).encode()).hexdigest()


def make_pair(d, volume):
    f16, f9 = os.path.join(d, "segment.mp4"), os.path.join(d, "segment_vertical.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=12",
                    "-f", "lavfi", "-i", "anoisesrc=color=pink:duration=12:seed=7", "-af", f"volume={volume}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                    "-shortest", f16], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=360x640:rate=24:duration=12",
                    "-i", f16, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-shortest", f9], check=True)
    return f16, f9


class TestLoudness(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="loud_")
        self.addCleanup(shutil.rmtree, self.d)

    def test_a_quiet_pair_is_corrected_video_untouched_and_the_vertical_gets_the_same_audio(self):
        f16, f9 = make_pair(self.d, 0.03)
        before = LD.measure(f16)["input_i"]
        self.assertLess(before, -20.0)
        v16, v9 = stream_md5(f16, "0:v"), stream_md5(f9, "0:v")
        rec = LD.correct_finals(f16, f9)
        self.assertEqual(rec["action"], "corrected", rec)
        for p in (f16, f9):
            m = LD.measure(p)
            self.assertLessEqual(abs(m["input_i"] - LD.TARGET_I), LD.TOL_LU, m)
            self.assertLessEqual(m["input_tp"], LD.TARGET_TP, m)
        self.assertEqual((stream_md5(f16, "0:v"), stream_md5(f9, "0:v")), (v16, v9))      # pictures untouched
        self.assertEqual(stream_md5(f16, "0:a"), stream_md5(f9, "0:a"))                     # Law 23: one audio
        self.assertEqual([n for n in os.listdir(self.d) if n.endswith(".loud.mp4")], [])

    def test_a_pair_within_tolerance_is_never_rewritten(self):          # audit batch 53 C1 (glm F3): a pair that
        f16, f9 = make_pair(self.d, 0.03)                             # MEASURES in tolerance, no correction first
        s16, s9 = sha(f16), sha(f9)
        ok = {"input_i": -14.2, "input_tp": -3.0, "input_lra": 5.0, "input_thresh": -24.0, "target_offset": 0.1}
        with mock.patch.object(LD, "measure", lambda p: dict(ok)), \
                mock.patch.object(LD, "_correct16", side_effect=AssertionError("pass 2 must not run")):
            rec = LD.correct_finals(f16, f9)
        self.assertEqual(rec["action"], "none: within tolerance")
        self.assertEqual((sha(f16), sha(f9)), (s16, s9))

    def test_the_correction_keeps_every_frame_count_and_duration(self):  # batch 53 C1 (glm F1), also measured on
        f16, f9 = make_pair(self.d, 0.03)                                  # pin #1's real finals: 1549 / 3022 kept
        def frames(p):                   # {codec_type: (frames, duration)}
            out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,nb_frames,duration",
                                  "-of", "csv=p=0", p], capture_output=True, text=True).stdout
            return {t: (int(n), float(d)) for t, d, n in (l.split(",") for l in out.split())}
        before = {p: frames(p) for p in (f16, f9)}
        self.assertEqual(LD.correct_finals(f16, f9)["action"], "corrected")
        for p in (f16, f9):
            after = frames(p)
            self.assertEqual(after["video"], before[p]["video"])                        # the picture: identical
            self.assertEqual(after["audio"][0], before[p]["audio"][0])                  # every audio frame kept
            self.assertLess(abs(after["audio"][1] - before[p]["audio"][1]), 1024 / 48000)   # < one AAC frame

    def test_a_failing_step_keeps_the_rendered_finals(self):
        f16, f9 = make_pair(self.d, 0.03)
        s16, s9 = sha(f16), sha(f9)
        with mock.patch.object(LD, "_mux9", side_effect=RuntimeError("9:16 mux failed: disk full")):
            rec = LD.correct_finals(f16, f9)
        self.assertTrue(rec["action"].startswith("kept the rendered finals: RuntimeError: 9:16 mux failed"), rec)
        self.assertEqual((sha(f16), sha(f9)), (s16, s9))
        self.assertEqual([n for n in os.listdir(self.d) if n.endswith(".loud.mp4")], [])

    def test_an_off_target_re_measure_keeps_the_rendered_finals(self):
        f16, f9 = make_pair(self.d, 0.03)
        s16, s9 = sha(f16), sha(f9)
        real = LD.measure
        calls = []

        def fake(p):
            calls.append(p)
            m = real(p)
            return dict(m, input_i=-16.0) if p.endswith(".loud.mp4") else m
        with mock.patch.object(LD, "measure", fake):
            rec = LD.correct_finals(f16, f9)
        self.assertIn("re-measure off target", rec["action"])
        self.assertEqual((sha(f16), sha(f9)), (s16, s9))
        self.assertEqual([n for n in os.listdir(self.d) if n.endswith(".loud.mp4")], [])   # batch 53 C2 (glm F3)

    def test_a_vertical_whose_audio_is_not_the_corrected_audio_is_never_promoted(self):    # batch 53 C2
        f16, f9 = make_pair(self.d, 0.03)
        s16, s9 = sha(f16), sha(f9)
        real = LD.audio_md5
        with mock.patch.object(LD, "audio_md5", lambda p: real(p) + ("x" if p.endswith("vertical.mp4.loud.mp4") else "")):
            rec = LD.correct_finals(f16, f9)
        self.assertEqual(rec["action"], "kept the rendered finals: the 9:16 audio is not the 16:9's corrected audio")
        self.assertEqual((sha(f16), sha(f9)), (s16, s9))

    def test_a_failed_second_replace_puts_both_originals_back(self):                       # batch 53 C2 (qwen)
        f16, f9 = make_pair(self.d, 0.03)
        s16, s9 = sha(f16), sha(f9)
        real, calls = os.replace, []

        def flaky(src, dst):
            calls.append(dst)
            if dst == f9 and not str(src).endswith(".orig"):
                raise OSError("disk full")
            return real(src, dst)
        with mock.patch.object(LD.os, "replace", flaky):
            rec = LD.correct_finals(f16, f9)
        self.assertTrue(rec["action"].startswith("kept the rendered finals: OSError"), rec)
        self.assertEqual((sha(f16), sha(f9)), (s16, s9))
        self.assertEqual([n for n in os.listdir(self.d) if n.endswith((".loud.mp4", ".orig"))], [])

    def test_an_unmeasurable_file_raises(self):
        bad = os.path.join(self.d, "x.mp4")
        open(bad, "wb").write(b"not a video")
        with self.assertRaises(RuntimeError):
            LD.measure(bad)


if __name__ == "__main__":
    unittest.main()
