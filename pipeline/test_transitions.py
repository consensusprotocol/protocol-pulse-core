#!/usr/bin/env python3
"""Phase 3 / DEC-4 (2026-11-11): transitions only between DIFFERENT channels, never at the open, never
over speech (bounded by the measured tail of A and lead-in of B), picture and sound frame-locked, sound
design below speech. Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_transitions.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import transitions as TR  # noqa: E402

SEGS = [("hook", "h.mp4", "talking_head"), ("clip_01", "c1.mp4", "talking_head"),
        ("clip_02", "c2.mp4", "talking_head"), ("shoutout", "s.mp4", "shoutout"), ("outro", "o.mp4", "outro")]
CH = {"hook": "DataDash", "clip_01": "Natalie Brunell", "clip_02": "Yahoo Finance"}
LT = {"hook": (0.30, 0.40), "clip_01": (0.35, 0.50), "clip_02": (0.30, 0.45)}   # (lead_s, tail_s)


class TestPlan(unittest.TestCase):
    def test_dissolves_only_between_different_channels_and_talking_heads(self):
        j = TR.plan(SEGS, CH, LT, "crossfade")
        self.assertEqual([(x["after"], x["frames"], x["kind"]) for x in j], [(0, 6, "dissolve"), (1, 6, "dissolve")])
        same = dict(CH, clip_01="DataDash")
        self.assertEqual([x["after"] for x in TR.plan(SEGS, same, LT, "crossfade")], [1])
        self.assertTrue(all(x["after"] < 2 for x in j))          # never into credits / outro

    def test_never_over_speech(self):
        # clip_01 has only 0.10 s of genuine lead-in: the dissolve shrinks to 2 frames (0.083 s)
        lt = dict(LT, clip_01=(0.10, 0.50))
        j = TR.plan(SEGS, CH, lt, "crossfade")
        self.assertEqual(j[0]["frames"], 2)
        self.assertLessEqual(j[0]["frames"] / TR.FPS, min(LT["hook"][1], 0.10))
        # under 2 frames of non-speech: a hard cut, never a transition over a word
        lt = dict(LT, clip_01=(0.05, 0.50))
        self.assertEqual([x["after"] for x in TR.plan(SEGS, CH, lt, "crossfade")], [1])

    def test_A_splits_the_dip_across_the_cut(self):
        lt = dict(LT, clip_01=(0.10, 0.50))                     # each side fades at most its own silence
        j = TR.plan(SEGS, CH, lt, "A")[0]
        self.assertEqual((j["kind"], j["frames"]), ("dip", 4))
        self.assertLessEqual(j["frames"] / 2 / TR.FPS, 0.10)

    def test_C_is_a_short_insert(self):
        j = TR.plan(SEGS, CH, LT, "C")
        self.assertEqual([(x["after"], x["kind"]) for x in j], [(0, "insert"), (1, "insert")])
        self.assertLess(TR.WIPE_FRAMES / TR.FPS, 0.35)

    def test_unknown_style_refused(self):
        with self.assertRaises(ValueError):
            TR.plan(SEGS, CH, LT, "D")


class TestSoundDesign(unittest.TestCase):
    def test_thumps_peak_at_the_declared_level_with_micro_fades(self):
        tmp = tempfile.mkdtemp(prefix="thump_")
        self.addCleanup(shutil.rmtree, tmp, True)
        for name, x in (("t.wav", TR.thump()), ("dt.wav", TR.double_thump())):
            p = os.path.join(tmp, name)
            TR.write_wav(p, x, TR.THUMP_PEAK_DBFS)
            import wave
            with wave.open(p) as f:
                a = np.frombuffer(f.readframes(f.getnframes()), np.int16).astype(np.float64) / 32767
            self.assertAlmostEqual(20 * np.log10(np.max(np.abs(a))), TR.THUMP_PEAK_DBFS, delta=0.1)
            self.assertLess(abs(a[0]), 1e-3)
            self.assertLess(abs(a[-1]), 1e-3)

    def test_wipe_is_a_red_line_sweeping_on_black(self):
        # measured 2026-11-11 at the render sizes: 94.5 % (16:9) / 95.7 % (9:16) black, median pixel 0
        for w, h in ((1920, 1080), (1080, 1920)):
            frames = [np.asarray(f).astype(int) for f in TR.wipe_frames(w, h)]
            self.assertEqual(len(frames), TR.WIPE_FRAMES)
            last = frames[-1]
            self.assertEqual(int(np.median(last.max(axis=2))), 0)                 # on black
            self.assertGreater((last.max(axis=2) < 40).mean(), 0.90)
            red = [((f[..., 0] > 150) & (f[..., 1] < 90)).mean() for f in frames]
            self.assertGreater(red[-1], 0.003)                                    # the red ECG line
            self.assertTrue(all(a < b for a, b in zip(red, red[1:])), red)        # sweeping in


RAMP = "nullsrc=s=320x180:r=24:d={dur},format=gray,geq=lum='16+3*N'"   # luma identifies every frame


def _seg(path, colour, freq, dur, speech):
    """Synthetic segment: a solid colour (or RAMP), a tone only inside `speech` (start, end), silence else."""
    video = RAMP.format(dur=dur) if colour == "ramp" else f"color=c={colour}:s=320x180:r=24:d={dur}"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", video,
                    "-f", "lavfi", "-i", f"sine=f={freq}:r=48000:d={dur}",
                    "-filter_complex", f"[1:a]volume='between(t,{speech[0]},{speech[1]})':eval=frame,"
                                       "aformat=channel_layouts=stereo[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", path], check=True)
    return path


def _lumas(path):
    import cv2
    cap, out = cv2.VideoCapture(path), []
    while True:
        ok, f = cap.read()
        if not ok:
            return np.array(out)
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).mean())


def _onset(path, t0, t1):
    """First 10 ms window in [t0, t1] whose RMS rises above -40 dBFS (the tone's start)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", path, "-f", "f32le",
                        "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True)
    a = np.frombuffer(r.stdout, np.float32)
    for k in range(0, len(a) - 480, 480):
        if 20 * np.log10(np.sqrt(np.mean(a[k:k + 480] ** 2)) + 1e-12) > -40:
            return t0 + k / 48000
    return None


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-show_entries",
                        "stream=codec_type,nb_read_packets,duration", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    return {s["codec_type"]: s for s in json.loads(r.stdout)["streams"]}


@unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "NVENC concat needs GPU0")
class TestConcat(unittest.TestCase):
    """Three 3 s segments, channels A, B, B: one dissolve (A->B), one hard cut (B->B)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trc_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.segs = [("hook", _seg(os.path.join(self.tmp, "a.mp4"), "red", 440, 3, (0.4, 2.6)), "talking_head"),
                     ("clip_01", _seg(os.path.join(self.tmp, "b.mp4"), "ramp", 660, 3, (0.4, 2.6)), "talking_head"),
                     ("clip_02", _seg(os.path.join(self.tmp, "c.mp4"), "green", 880, 3, (0.4, 2.6)), "talking_head")]
        self.ch = {"hook": "A", "clip_01": "B", "clip_02": "B"}
        self.lt = {k: (0.4, 0.4) for k in self.ch}

    def run_style(self, style):
        out = os.path.join(self.tmp, f"{style}.mp4")
        j = TR.plan(self.segs, self.ch, self.lt, style)
        tl = TR.concat(self.segs, j, out, 23, 320, 180, self.tmp)
        return out, j, tl

    def test_dissolve_overlaps_only_silence_and_stays_frame_locked(self):
        out, j, tl = self.run_style("crossfade")
        self.assertEqual([(x["after"], x["frames"]) for x in j], [(0, 6)])
        dd = 6 / 24
        self.assertAlmostEqual(tl[1]["start"], tl[0]["end"] - dd, places=3)   # overlap = the dissolve
        self.assertAlmostEqual(tl[2]["start"], tl[1]["end"], places=3)        # same channel: hard cut
        p = _probe(out)
        n_frames = int(p["video"]["nb_read_packets"])
        self.assertEqual(n_frames, 3 * 72 - 6)
        self.assertAlmostEqual(float(p["audio"]["duration"]), n_frames / 24, delta=0.03)   # A/V locked
        # the overlap region holds no tone from either side (both are in their silences)
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{tl[1]['start']:.3f}", "-t", f"{dd:.3f}", "-i", out,
                            "-f", "f32le", "-ac", "1", "-ar", "48000", "-"], capture_output=True, check=True)
        a = np.frombuffer(r.stdout, np.float32)
        self.assertLess(20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-12), -50)

    def test_dissolved_clip_picture_and_sound_start_together(self):
        # B = a luma ramp (frame k is identifiable): after the dissolve, output frame (start*24 + k) must be
        # B's frame k, and B's tone (0.4 s into B) must start 0.4 s after the same start. ffmpeg 4.4.2's
        # xfade with offset = start put every B frame one frame late (41.7 ms behind its sound).
        out, j, tl = self.run_style("crossfade")
        b, x = _lumas(self.segs[1][1]), _lumas(out)
        s0 = int(round(tl[1]["start"] * 24))
        k = np.arange(6, 72)
        self.assertLess(float(np.max(np.abs(x[s0 + k] - b[k]))), 1.5, (x[s0 + 6:s0 + 12], b[6:12]))
        onset = _onset(out, tl[1]["start"] + 0.2, tl[1]["start"] + 0.6)
        self.assertAlmostEqual(onset - tl[1]["start"], 0.4, delta=0.012)

    def test_C_inserts_one_wipe_between_channels_only(self):
        out, j, tl = self.run_style("C")
        self.assertEqual([e["label"] for e in tl], ["hook", "transition_C", "clip_01", "clip_02"])
        self.assertEqual(tl[0]["start"], 0.0)                                 # nothing at the open
        p = _probe(out)
        self.assertEqual(int(p["video"]["nb_read_packets"]), 3 * 72 + TR.WIPE_FRAMES)


class TestFrozenPath(unittest.TestCase):
    def test_no_transitions_file_keeps_the_frozen_concat(self):
        import render16
        tmp = tempfile.mkdtemp(prefix="trf_")
        self.addCleanup(shutil.rmtree, tmp, True)
        self.assertIsNone(render16._transition_concat(tmp, SEGS, os.path.join(tmp, "x.mp4"), 1920, 1080, tmp))


if __name__ == "__main__":
    unittest.main()
