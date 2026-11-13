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
from unittest import mock

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


class TestRuling71Parity(unittest.TestCase):
    """Ruling 71 (orchestrator '15:45'): both formats in parity, on CPU (the snap's encode replaced)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="snap71_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.clip = os.path.join(self.tmp, "final_hook.mp4")
        open(self.clip, "wb").write(b"x")
        self.hook = {"clip_id": "hook", "cut_in": 14.6, "lead_in_pad_s": 0.0, "pause_in": {"end": 14.69},
                     "pause_out": {"start": 31.46}}               # speech 0.09-16.86 s of the clip, as 0c68b589's hook

    def _apply(self, c16, c9, n=407):
        def fake_encode(cmd, **k):
            open(cmd[-1], "wb").write(b"y")
            return mock.Mock(returncode=0)
        with mock.patch.object(SS, "scene_changes", lambda p: c16), \
                mock.patch.object(SS, "scene_changes_9x16", lambda p: c9), \
                mock.patch.object(SS, "frame_count", lambda p: n), \
                mock.patch.object(SS.subprocess, "run", fake_encode), mock.patch("gpu0.swap_to", lambda *a: None):
            return SS.apply(self.clip, self.hook, 24, 18)

    def test_a_change_only_the_9x16_crop_sees_is_snapped(self):
        rec = self._apply([(336, 0.997)], [(336, 1.0), (406, 0.3172)])   # 16:9 scored frame 406 at 0.2718
        self.assertTrue(rec["snapped"], rec)
        self.assertEqual((rec["held_head_frames"], rec["held_tail_frames"]), (0, 1))
        self.assertEqual(rec["hard_cuts_9x16"], [(336, 1.0), (406, 0.317)])
        self.assertIn("tail: frames 406-406 were the next shot, held on frame 405", rec["why"])

    def test_nothing_to_snap_in_either_format_leaves_the_clip(self):
        rec = self._apply([(336, 0.997)], [(336, 1.0)])
        self.assertFalse(rec["snapped"])
        self.assertNotIn("refused", rec)

    def test_a_snap_that_cannot_keep_the_hooks_lead_is_refused(self):
        self.hook["pause_in"] = {"end": 14.6 + 2 / 24 + 0.05}    # the first word 50 ms after a change at frame 2
        rec = self._apply([], [(2, 0.5)])
        self.assertEqual(rec.get("refused"),
                         "the speaker's own shot starts 0.050 s before the first word (< 0.080 s)")
        self.assertFalse(rec["snapped"])
        self.assertEqual(open(self.clip, "rb").read(), b"x")     # refused: nothing re-encoded
        self.hook["clip_id"] = "clip_01"                         # not the hook: LEAD_MIN_S, snapped
        self.assertTrue(self._apply([], [(2, 0.5)])["snapped"])


HOOK_0C68 = "/home/ultron/protocol_pulse/runs/pinned_20261113_191409"


def _scores_9x16(clip):
    """The clip's 9:16 picture scored frame by frame with the renderer's own per-shot filters (render_vertical._shot_vf
    on vertical_layout.classify's plan): built here so this test runs on the code before ruling 71 too."""
    import re
    import render_vertical
    import vertical_layout
    plan = vertical_layout.classify(clip)
    g, lab = [], []
    for k, sh in enumerate(plan["shots"]):
        a, b = int(round(sh["start"] * plan["fps"])), int(round(sh["end"] * plan["fps"]))
        g.append(f"[0:v]trim=start_frame={a}:end_frame={b},setpts=PTS-STARTPTS,"
                 f"{render_vertical._shot_vf(sh, plan['width'], plan['height'])},setsar=1:1[v{k}]")
        lab.append(f"[v{k}]")
    g.append("".join(lab) + f"concat=n={len(lab)}:v=1:a=0,select='gte(scene,0)',"
                            "metadata=print:key=lavfi.scene_score:file=-[s]")
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", clip, "-filter_complex", ";".join(g), "-map", "[s]", "-f", "null",
                        "-"], capture_output=True, text=True, check=True, timeout=600)
    return {int(f): float(x) for f, x in
            re.findall(r"frame:(\d+)\s+pts:\S+\s+pts_time:\S+\s+lavfi\.scene_score=([0-9.]+)", r.stdout)}


@unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0" and
                     os.path.exists(os.path.join(HOOK_0C68, "qa", "final_hook.mp4")), "NVENC + the 0c68b589 run")
class TestRuling71OnTheHeldHook(unittest.TestCase):
    """MUST-FAIL: 0c68b589's prepared hook (run pinned_20261113_191409): the source's punch-in at frame 406, after the
    last word, scored 0.3172 in the 9:16 crop and 0.2718 in 16:9. Before ruling 71 prepare kept it (G19 held the 9:16)."""

    def test_the_punch_in_after_the_last_word_is_snapped_in_both_formats(self):
        import json
        tmp = tempfile.mkdtemp(prefix="snap71h_")
        self.addCleanup(shutil.rmtree, tmp, True)
        clip = os.path.join(tmp, "final_hook.mp4")
        shutil.copy(os.path.join(HOOK_0C68, "qa", "final_hook.mp4"), clip)
        cut = next(c for c in json.load(open(os.path.join(HOOK_0C68, "cuts_final.json"))) if c["clip_id"] == "hook")
        self.assertGreaterEqual(_scores_9x16(clip)[406], SS.SCENE_CUT)            # the fixture really has it
        rec = SS.apply(clip, cut, 24, 18)
        off = int(rec["speech_off_s"] * 24)
        late9 = {f: s for f, s in _scores_9x16(clip).items() if f > off and s >= SS.SCENE_CUT}
        late16 = [f for f, s in SS.scene_changes(clip) if f > off]
        self.assertEqual((late9, late16), ({}, []), rec)                           # no shot change after the last word
        self.assertEqual(SS.frame_count(clip), 407)


if __name__ == "__main__":
    unittest.main()
