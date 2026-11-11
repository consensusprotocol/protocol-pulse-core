#!/usr/bin/env python3
"""Recut run 6 V1: the last 3 frames of clip_02 showed the NEXT shot (Natalie's NVIDIA/AMD/MICRON graphic) in
the pause after her sentence. shot_snap holds the speaker's shot outside the speech; audio untouched.
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_shot_snap.py"""
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import shot_snap as SS  # noqa: E402


def _clip(path, shots, speech=(0.3, 2.2), dur=3.0):
    """Solid-colour shots [(colour, first_frame)] at 24 fps with a tone only during `speech`."""
    parts, n = [], int(dur * 24)
    bounds = [f for _, f in shots] + [n]
    for (colour, f0), f1 in zip(shots, bounds[1:]):
        parts.append(f"color=c={colour}:s=160x90:r=24:d={(f1 - f0) / 24}")
    inputs = sum((["-f", "lavfi", "-i", p] for p in parts), [])
    k = len(parts)
    graph = "".join(f"[{i}:v]" for i in range(k)) + f"concat=n={k}:v=1:a=0[v];" \
        f"[{k}:a]volume='between(t,{speech[0]},{speech[1]})':eval=frame,aformat=channel_layouts=stereo[a]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-f", "lavfi", "-i", f"sine=f=440:r=48000:d={dur}",
                    "-filter_complex", graph, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", path], check=True)
    return path


def _lumas(path):
    import cv2
    cap, out = cv2.VideoCapture(path), []
    while True:
        ok, f = cap.read()
        if not ok:
            return np.array(out)
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean())


def _streams(path):
    import json
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,start_time,duration,r_frame_rate",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    return sorted((s["codec_type"], s.get("start_time"), round(float(s.get("duration", 0)), 2), s.get("r_frame_rate"))
                  for s in json.loads(r.stdout)["streams"])


def _pcm(path):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-"], capture_output=True, check=True).stdout


class TestPlan(unittest.TestCase):
    def test_only_changes_outside_the_speech_are_snapped(self):
        self.assertEqual(SS.plan([(5, .6), (30, .6), (60, .6)], 72, 24, 0.3, 2.2), (5, 60))
        self.assertEqual(SS.plan([(30, .6)], 72, 24, 0.3, 2.2), (0, 72))          # inside the speech: content
        self.assertEqual(SS.plan([(60, .6), (66, .6)], 72, 24, 0.3, 2.2), (0, 60))  # first change after the speech
        self.assertEqual(SS.plan([(60, .6)], 72, 24, None, None), (0, 72))         # no pause data: untouched


@unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "NVENC needs GPU0")
class TestApply(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="snap_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.cut = {"cut_in": 10.0, "lead_in_pad_s": 0.0, "pause_in": {"start": 9.9, "end": 10.3},
                    "pause_out": {"start": 12.2, "end": 12.6}}

    def test_neighbouring_shots_are_held_on_the_speakers_shot_audio_untouched(self):
        clip = _clip(os.path.join(self.tmp, "c.mp4"), [("blue", 0), ("red", 5), ("blue", 60)])
        pcm, before = _pcm(clip), _streams(clip)
        red = float(np.mean(_lumas(_clip(os.path.join(self.tmp, "r.mp4"), [("red", 0)]))))
        rec = SS.apply(clip, self.cut, 24, 18)
        self.assertTrue(rec["snapped"], rec)
        self.assertEqual((rec["held_head_frames"], rec["held_tail_frames"], rec["frames"]), (5, 12, 72))
        lum = _lumas(clip)
        self.assertEqual(len(lum), 72)
        self.assertLess(float(np.ptp(lum)), 3.0)               # one shot everywhere ...
        self.assertLess(abs(float(np.mean(lum)) - red), 3.0)   # ... and it is the red (speaker's) shot
        self.assertEqual(hashlib.sha256(_pcm(clip)).hexdigest(), hashlib.sha256(pcm).hexdigest())
        self.assertEqual(_streams(clip), before)               # audio start/duration, frame rate, duration

    def test_a_change_inside_the_speech_leaves_the_file_untouched(self):
        clip = _clip(os.path.join(self.tmp, "d.mp4"), [("red", 0), ("blue", 30)])
        before = hashlib.sha256(open(clip, "rb").read()).hexdigest()
        rec = SS.apply(clip, self.cut, 24, 18)
        self.assertFalse(rec["snapped"])
        self.assertEqual(hashlib.sha256(open(clip, "rb").read()).hexdigest(), before)


if __name__ == "__main__":
    unittest.main()
