#!/usr/bin/env python3
"""Round-2 must-fail fixture. Drop this file in pipeline/ next to test_edl_rules.py.

EXPECTED ON SNAPSHOT 7c3a4416: every test in this file FAILS.
A green run means the fix landed. Do not invert an assertion to make it pass.

Covers the seven audit bugs plus the magnitude cut:

  1. 9:16 still appends a missing hook, intro, bridge, shout-out, or outro.
  2. gates9 never calls G8, G9, G11, G12.
  3. G3b ignores a next word shorter than 3 letters ("So").
  4. G3b accepts "magnet" as "magnitude" (4-character prefix).
     G3 accepts an empty whisper transcript, because "" in "magnitude" is true.
  5. A legal M20 edit with no intro crashes G1 on manifest["intro"].
  6. A later passing gate run leaves the previous GATE_FAIL.txt in place.
  7. G5 rejects the approved 102.9 s vertical (cap is 75 s) and accepts a 50 s one.
  8. The magnitude cut. The quiet gap inside the word is not the cut.
     Existing test_clip_01_source_valley REQUIRES cut_out == 249.37.
     That oracle is the bug. It has to go.

No GPU, no paid API, no source mp4. The magnitude case is a synthetic
waveform fed through the real compute_acoustic_cut_out.
"""
from __future__ import annotations

import importlib
import inspect
import json
import os
import sys
import tempfile
import unittest

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)
sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")


def _qa():
    return importlib.import_module("qa_gates")


class TestVerticalFailClosed(unittest.TestCase):
    """Bug 1. render_9x16 must refuse a missing required piece. It currently appends whatever exists."""

    def _src(self):
        import render_vertical
        return inspect.getsource(render_vertical.render_9x16)

    def test_missing_pieces_are_a_stop_not_a_skip(self):
        src = self._src()
        # These are the current fail-open branches. None of them may remain.
        self.assertNotIn(
            'if "hook" in reframed:\n        segments.append',
            src,
            "a missing vertical hook is skipped",
        )
        self.assertNotIn(
            "if os.path.exists(vo_intro_mp4):\n        segments.append",
            src,
            "a missing vertical intro is skipped",
        )
        self.assertNotIn(
            "if os.path.exists(vo_bridge_mp4):\n                segments.append",
            src,
            "a missing vertical bridge is skipped",
        )
        self.assertNotIn(
            "if shoutout_path:\n        segments.append",
            src,
            "a missing vertical shout-out is skipped",
        )
        self.assertNotIn(
            "if outro_path:\n        segments.append",
            src,
            "a missing vertical outro is skipped",
        )
        self.assertIn("STOP: intro VO missing", src)
        self.assertIn("STOP: bridge VO missing", src)
        self.assertIn("STOP: shoutout not found", src)
        self.assertIn("STOP: outro not found", src)


class TestVerticalGatesWired(unittest.TestCase):
    """Bug 2. The 9:16 runner must actually call the vertical gates."""

    def test_g8_g9_g11_g12_are_called(self):
        src = inspect.getsource(_qa().run_all_gates)
        for name in ("gate_g8", "gate_g9", "gate_g11", "gate_g12"):
            self.assertIn(name + "(", src, "%s is not called from run_all_gates" % name)


class TestCutWordChecks(unittest.TestCase):
    """Bugs 3 and 4, plus the empty-transcript hole in the same functions."""

    def setUp(self):
        self.qa = _qa()
        self._whisper = self.qa.whisper_segment
        self._extract = self.qa.extract_audio_region
        self.qa.extract_audio_region = lambda *a, **k: True
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        self.qa.whisper_segment = self._whisper
        self.qa.extract_audio_region = self._extract

    def _talking(self, last, first="The"):
        return [{
            "type": "talking_head",
            "label": "clip_01",
            "start": 0.0,
            "end": 10.0,
            "first_word": first,
            "last_word": last,
        }]

    def test_g3_empty_transcript_fails(self):
        self.qa.whisper_segment = lambda *a, **k: ""
        ok, _ = self.qa.gate_g3("x.mp4", self._talking("magnitude"), self.tmpdir)
        self.assertFalse(ok, 'empty whisper passed G3 because "" in "magnitude"')

    def test_g3b_rejects_magnet_as_magnitude(self):
        self.qa.whisper_segment = lambda *a, **k: "magnet"
        ok, _ = self.qa.gate_g3b("x.mp4", self._talking("magnitude"), self.tmpdir)
        self.assertFalse(ok, "4-character prefix accepted magnet as magnitude")

    def test_g3b_rejects_short_next_word_so(self):
        self.qa.whisper_segment = lambda *a, **k: "magnitude so"
        edl = os.path.join(self.tmpdir, "edl.json")
        with open(edl, "w") as f:
            json.dump({
                "hook": {},
                "clips": [{
                    "index": 1,
                    "next_source_word": "So",
                    "text": "magnitude.",
                }],
            }, f)
        ok, table = self.qa.gate_g3b(
            "x.mp4", self._talking("magnitude"), self.tmpdir, edl_path=edl,
        )
        self.assertFalse(ok, 'next word "So" was ignored because len < 3')
        self.assertTrue(table and table[0]["next_leaked"])


class TestNoIntroDoesNotCrashG1(unittest.TestCase):
    """Bug 5. M20 allows an edit with no intro. G1 must not KeyError on manifest['intro']."""

    def test_no_intro_is_not_a_keyerror(self):
        qa = _qa()
        manifest = {
            "signoff": {"stem_wav": "signoff.wav", "text": "Go follow them."},
        }
        try:
            qa.gate_g1("nope.mp4", manifest, [], tempfile.mkdtemp())
        except KeyError as exc:
            self.fail("no-intro edit crashed G1 on manifest['intro']: %s" % exc)
        except Exception:
            # A missing reference wav, or a voice backend that is not configured
            # in this process, is fine. The intro key is not.
            return


class TestGateFailClears(unittest.TestCase):
    """Bug 6. A passing run must delete a stale GATE_FAIL.txt. It currently only writes one."""

    def test_pass_path_removes_gate_fail(self):
        src = inspect.getsource(_qa().run_all_gates)
        self.assertRegex(
            src,
            r"(remove|unlink)\([^)]*GATE_FAIL",
            "passing run_all_gates never deletes GATE_FAIL.txt",
        )


class TestDurationWindow(unittest.TestCase):
    """Bug 7. Approved vertical is 102.9 s. Product window is 60-120 s, both aspects."""

    def _g5(self, dur, fmt):
        qa = _qa()

        class _Proc:
            returncode = 0
            stdout = ""
            stderr = "Summary:\nI: -14.0 LUFS\nPeak: -2.5 dBFS\n"

        real_run = qa.subprocess.run
        real_dur = qa.get_duration
        real_probe = qa.ffprobe_json
        qa.subprocess.run = lambda *a, **k: _Proc()
        qa.get_duration = lambda path: dur
        if fmt == "9x16":
            w, h = 1080, 1920
        else:
            w, h = 1920, 1080
        qa.ffprobe_json = lambda path: {
            "streams": [{
                "codec_type": "video",
                "width": w,
                "height": h,
                "sample_aspect_ratio": "1:1",
                "r_frame_rate": "24/1",
            }],
        }
        try:
            ok, _ = qa.gate_g5("x.mp4", fmt)
            return ok
        finally:
            qa.subprocess.run = real_run
            qa.get_duration = real_dur
            qa.ffprobe_json = real_probe

    def test_approved_102s_vertical_passes(self):
        self.assertTrue(
            self._g5(102.9, "9x16"),
            "G5 rejected the approved 102.9 s vertical",
        )

    def test_50s_vertical_fails(self):
        self.assertFalse(
            self._g5(50.0, "9x16"),
            "G5 accepted a 50 s vertical; floor is 60 s",
        )

    def test_130s_either_aspect_fails(self):
        self.assertFalse(self._g5(130.0, "9x16"))
        self.assertFalse(self._g5(130.0, "16x9"), "16:9 duration is not checked")


class TestMagnitudeCut(unittest.TestCase):
    """Bug 8. Cut after the syllable, never on the stop inside the word.

    Timeline (source seconds), whisper end planted early at 10.00:

        8.00-10.05  speech
        10.05-10.12 intra-word gap  (what the current code selects, ~10.12)
        10.12-10.34 rest of the syllable
        10.34-10.70 real gap
        10.70-      next word

    A correct cut is after 10.40 and at least 60 ms before the next onset.
    """

    def test_cut_is_after_the_syllable_not_inside_it(self):
        import numpy as np
        from acoustic import compute_acoustic_cut_out

        sr = 16000
        whisper_end = 10.0
        n = int(3.5 * sr)
        amp = 10 ** (-15 / 20)
        rng = np.random.default_rng(19)
        samples = amp * rng.standard_normal(n)

        def silence(t0, t1):
            samples[int(t0 * sr):int(t1 * sr)] = 0.0

        # Times below are absolute. The extractor window starts at whisper_end - 2.
        origin = whisper_end - 2.0

        def abs_silence(t0, t1):
            silence(t0 - origin, t1 - origin)

        abs_silence(10.05, 10.12)
        abs_silence(10.34, 10.70)

        def fake_extract(mp4, start_s, duration_s, out_wav, sr=16000):
            return out_wav

        def fake_load(wav_path):
            return samples, sr

        import acoustic
        real_extract = acoustic._extract_audio_mono
        real_load = acoustic._load_wav_samples
        acoustic._extract_audio_mono = fake_extract
        acoustic._load_wav_samples = fake_load
        try:
            result = compute_acoustic_cut_out("clip.mp4", whisper_word_end=whisper_end)
        finally:
            acoustic._extract_audio_mono = real_extract
            acoustic._load_wav_samples = real_load

        cut = result["cut_out"]
        self.assertGreaterEqual(cut, 10.40, "cut landed inside the word: %s" % result)
        self.assertLessEqual(cut, 10.64, "cut did not clear the next onset by 60 ms: %s" % result)
        self.assertTrue(result["safe"], result)

    def test_real_bitcoin_magazine_clip_when_present(self):
        source = "/home/ultron/protocol_pulse/segment_v2/sources/Pxrak-iMT0g.mp4"
        if not os.path.exists(source):
            self.skipTest("source mp4 not on this machine")
        from acoustic import compute_acoustic_cut_out
        result = compute_acoustic_cut_out(source, whisper_word_end=249.3)
        cut = result["cut_out"]
        self.assertGreaterEqual(cut, 249.62, result)
        self.assertLessEqual(cut, 249.72, result)
        self.assertTrue(result["safe"], result)

    def test_old_oracle_does_not_require_249_37(self):
        candidates = [
            os.path.join(PIPELINE_DIR, "test_edl_rules.py"),
            "/home/ultron/protocol_pulse/pipeline/test_edl_rules.py",
        ]
        text = None
        for path in candidates:
            if os.path.exists(path):
                with open(path) as f:
                    text = f.read()
                break
        self.assertIsNotNone(text, "test_edl_rules.py not found")
        self.assertNotIn(
            'assertAlmostEqual(result["cut_out"], 249.37',
            text,
            "test_clip_01_source_valley still requires the cut inside magnitude",
        )


class TestG8SourceRelative(unittest.TestCase):
    """A9/Addendum 2 item 3: G8 compares output to source, not absolute only."""

    def _make_frames(self, qa_dir, label, out_var, src_var, n=5):
        """Create fake PNG frames with known Laplacian variance."""
        import cv2
        import numpy as np
        os.makedirs(qa_dir, exist_ok=True)
        for i in range(n):
            # Output frame: use a pattern with controlled frequency
            img = np.zeros((200, 200), dtype=np.uint8)
            # Higher variance = sharper edges
            step = max(1, int(200 / (out_var ** 0.5 + 1)))
            for r in range(0, 200, step):
                img[r:r+max(1, step//2), :] = 255
            cv2.imwrite(os.path.join(qa_dir, f"g8_{label}_{i}.png"), img)

            # Source frame
            src_img = np.zeros((200, 200), dtype=np.uint8)
            step_s = max(1, int(200 / (src_var ** 0.5 + 1)))
            for r in range(0, 200, step_s):
                src_img[r:r+max(1, step_s//2), :] = 255
            cv2.imwrite(os.path.join(qa_dir, f"g8_{label}_{i}_src.png"), src_img)

    def test_g8_requires_source_clips(self):
        """G8 fails when no source_clips provided (fail-closed)."""
        sys.path.insert(0, os.path.join(os.path.dirname(PIPELINE_DIR), "segment_v1"))
        from qa_gates import gate_g8
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            segments = [{"label": "clip_01", "start": 0, "end": 10, "type": "talking_head"}]
            ok, table = gate_g8("/dev/null", segments, td, source_clips=None)
            self.assertFalse(ok, "G8 must fail when no source clips provided")

    def test_g8_signature_has_source_clips(self):
        """gate_g8 must accept source_clips kwarg."""
        sys.path.insert(0, os.path.join(os.path.dirname(PIPELINE_DIR), "segment_v1"))
        import qa_gates
        sig = inspect.signature(qa_gates.gate_g8)
        self.assertIn("source_clips", sig.parameters,
                       "gate_g8 must accept source_clips parameter")


if __name__ == "__main__":
    unittest.main(verbosity=2)
