#!/usr/bin/env python3
"""pipeline/hook_onset.py: G17a at the PIN stage. Batch pin #1 was held at render (01:39 ET Nov 13) because its hook
kept 30 ms of genuine quiet before its first onset. The word record showed a 400 ms gap, but the source held breath,
then DIGITAL ZEROS (a hard edit), then speech. Offline: synthetic 10 ms envelopes, built to the render's own level
rules (sentence_law: speech near -20 dBFS, room tone near -55, digital zeros below DIGITAL_FLOOR_DBFS)."""
import os
import shutil
import sys
import tempfile
import unittest
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import eligibility as E  # noqa: E402
import hook_onset as HO  # noqa: E402
import sentence_law as SL  # noqa: E402

WORDS = [("Before", 0.20, 0.60), ("this", 0.60, 0.95), ("markets.", 0.95, 1.35),        # the previous sentence
         ("When", 1.75, 2.15), ("Bitcoin", 2.15, 2.60), ("rises.", 2.60, 3.20),           # the hook: words 3..5
         ("Next", 3.60, 4.00), ("words", 4.00, 4.40), ("follow.", 4.40, 5.00)]


class Env(SL.SourceAudio):
    """A synthetic source envelope (no decode): `spans` [(t0, t1, dBFS)] over a bed of room tone."""

    def __init__(self, spans, dur=6.0, bed=-55.0):
        self.path, self.dur = "synthetic", dur
        self.t = np.arange(int(round(dur / SL.HOP_S))) * SL.HOP_S
        self.db = np.full(len(self.t), bed)
        for a, b, v in spans:
            self.db[(self.t >= a - 1e-9) & (self.t < b - 1e-9)] = v


SPEECH = [(0.20, 1.36, -20.0), (3.60, 5.00, -20.0)]


def src():
    toks = tuple({"word": w, "start": a, "end": b} for w, a, b in WORDS)
    return E.Source("vidH", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
                    timing="word", file_head=False, vod=True)


class TestHookOnset(unittest.TestCase):
    def measure(self, env, **kw):
        return HO.measure(src(), 3, 5, "vidH", 1.75, 3.20, "/nonexistent", audio=(env, 0.0), **kw)

    def test_breath_then_digital_zeros_before_the_first_word_fails_g17a(self):
        """Pin #1's pattern: a 400 ms word-record gap that is breath, then digital zeros, then 30 ms of quiet."""
        env = Env(SPEECH + [(1.41, 1.58, -27.0), (1.65, 1.78, -200.0), (1.78, 1.81, -60.0), (1.81, 3.20, -20.0)])
        r = self.measure(env)
        self.assertEqual((r["pass"], r["measured"]), (False, True), r)
        self.assertLess(r["lead_ms"], 80)
        self.assertIn("G17a", r["why"])

    def test_room_tone_before_the_first_word_passes(self):
        env = Env(SPEECH + [(1.81, 3.20, -20.0)])                    # 1.36 .. 1.81: genuine room tone (-55)
        r = self.measure(env)
        self.assertEqual((r["pass"], r["measured"]), (True, True), r)
        self.assertGreaterEqual(r["lead_ms"], 80)

    def test_a_lead_within_one_frame_of_80_ms_does_not_pass(self):
        """Audit 0155 C1 (glm P0-1 / P1-1, qwen): the slice can differ from the render's decode by one 10 ms frame,
        so 80-89 ms of genuine lead is not enough here. The margin is pinned (C2, glm P1-1)."""
        self.assertEqual((HO.MARGIN_MS, SL.HEAD_LEAD_MIN_S), (10, 0.080))
        for lead_s, ok in ((0.085, False), (0.12, True)):
            env = Env(SPEECH + [(1.36, 1.81 - lead_s, -27.0), (1.81, 3.20, -20.0)])   # breath, then room tone
            r = self.measure(env)
            self.assertEqual(r["pass"], ok, (lead_s, r))

    def test_a_file_head_hook_counts_the_pad_the_render_adds_once(self):
        """qwen C1: at a file head edge_plan grants a room-tone pad when the genuine lead is short. The render adds it
        before the source audio, so it is added to the measured lead once, never twice."""
        toks = tuple({"word": w, "start": a - 1.70, "end": b - 1.70} for w, a, b in WORDS[3:])  # the hook opens the file
        s0 = E.Source("vidF", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
                      timing="word", file_head=True, vod=True)
        env = Env([(0.06, 1.50, -20.0), (1.90, 3.30, -20.0)], dur=4.0)          # speech 60 ms after the file start
        r = HO.measure(s0, 0, 2, "vidF", 0.05, 1.50, "/nonexistent", audio=(env, 0.0))
        self.assertEqual(r["pad_s"], SL.LEAD_PAD_S)
        self.assertTrue(r["pass"], r)
        self.assertLess(r["lead_ms"] - int(SL.LEAD_PAD_S * 1000), 80)            # the source alone has < 80 ms

    def test_no_audio_or_words_outside_the_window_is_not_measured_never_a_pass(self):
        r = HO.measure(src(), 3, 5, "vidH", 1.75, 3.20, "/nonexistent/dir")      # no L-v 2 window, no network
        self.assertEqual((r["pass"], r["measured"]), (False, False))
        env = Env(SPEECH + [(1.81, 3.20, -20.0)], dur=2.5)                       # the hook runs past the audio
        r = self.measure(env)
        self.assertEqual((r["pass"], r["measured"]), (False, False))
        self.assertIn("not inside its audio window", r["why"])


TRIM_WORDS = [("Before", 0.20, 0.60), ("this", 0.60, 0.95), ("markets.", 0.95, 1.35),   # the previous sentence
              ("So", 1.75, 1.95),                                                       # the trimmed word
              ("Bitcoin", 2.40, 2.80), ("rises.", 2.80, 3.30),                          # the clip: words 4..5
              ("Next", 3.70, 4.10), ("words", 4.10, 4.50), ("follow.", 4.50, 5.10)]
TRIM_SPEECH = [(0.20, 1.35, -20.0), (2.40, 3.30, -20.0), (3.70, 5.10, -20.0)]


def wav(path, spans, dur=6.0, bed=-55.0, sr=16000):
    """A real 16 kHz file: white noise at `bed` dBFS RMS (room tone), louder noise over `spans` [(t0, t1, dBFS)]."""
    lv = np.full(int(dur * sr), 10 ** (bed / 20))
    for a, b, v in spans:
        lv[int(a * sr):int(b * sr)] = 10 ** (v / 20)
    x = np.clip(np.random.default_rng(7).standard_normal(len(lv)) * lv, -1, 1)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((x * 32767).astype(np.int16).tobytes())
    return path


def trim_src():
    toks = tuple({"word": w, "start": a, "end": b} for w, a, b in TRIM_WORDS)
    return E.Source("vidT", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
                    timing="word", file_head=False, vod=True)


class TestTrimmedCut(unittest.TestCase):
    """Ruling 33 part 2 (item 42): a trimmed moment's IN edge is planned AFTER the trimmed word, as the render plans it
    (sentence_law.trimmed_boundary / edge_plan(trimmed=...), verbatim from its c6605895), and ruling 33 (a) is the
    render's own onset rule on the audio as cut (accepted_cut's cut and fade, then trimmed_onset), with one more 10 ms
    frame here. On a generated audio file: the render's rule decodes the file. The 05:48 build's two cleared trims
    failed the old measure, which only cut after a sentence end ("'So' does not end a sentence")."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def measure(self, spans, trimmed="So"):
        sa = SL.SourceAudio(wav(os.path.join(self.d, "t.wav"), spans))
        return HO.measure(trim_src(), 4, 5, "vidT", 2.40, 3.30, self.d, audio=(sa, 0.0), trimmed=trimmed)

    def test_a_measured_pause_after_the_trimmed_word_passes(self):
        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)])                 # "So", 450 ms of room tone, "Bitcoin"
        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"]), (True, True), r)
        self.assertGreater(r["trim"]["onset_s"], SL.HOP_S + HO.MARGIN_MS / 1000)
        self.assertTrue(1.95 <= r["trim"]["cut_in"] < 2.40, r["trim"])        # the cut sits in the pause
        self.assertTrue(SL.FADE_MIN_S * 1000 - 1e-6 <= r["trim"]["fade_in_ms"] <= SL.VALLEY_FADE_S * 1000 + 1,
                        r["trim"])                                            # with law L-b's fade (accepted_cut)
        self.assertTrue(r["pass"], r)                                         # and its lead lets it open a medley

    def test_a_trimmed_word_run_into_the_next_cannot_be_cut(self):
        r = self.measure([(0.20, 1.35, -20.0), (1.75, 3.30, -20.0), (3.70, 5.10, -20.0)])   # no pause after "So"
        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"], r["pass"]), (False, True, False), r)
        self.assertIn("cannot be cut cleanly", r["trim"]["why"])

    def test_the_trimmed_word_must_be_the_word_heard_before_the_clip(self):
        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)], trimmed="But")
        self.assertEqual((r["trim"]["pass"], r["pass"]), (False, False), r)
        self.assertIn("not the word before the lock", r["trim"]["why"])

    def test_untrimmed_is_unchanged_and_no_audio_file_is_never_a_pass(self):
        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)], trimmed=None)   # the old rule: a sentence end first
        self.assertEqual((r["pass"], "trim" in r), (False, False), r)
        self.assertIn("does not end a sentence", r["why"])
        words = [dict(t) for t in trim_src().tokens]
        words[3].pop("start")                                                # "So" has no timing: not measured
        s0 = E.Source("vidT", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", tuple(words),
                      timing="word", file_head=False, vod=True)
        r = HO.measure(s0, 4, 5, "vidT", 2.40, 3.30, self.d, audio=(Env(TRIM_SPEECH), 0.0), trimmed="So")
        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"]), (False, False), r)
        self.assertIn("no timed word right before the clip", r["trim"]["why"])
        env = Env(TRIM_SPEECH + [(1.75, 1.95, -20.0)])                        # an envelope, no file to cut (law L-m)
        r = HO.measure(trim_src(), 4, 5, "vidT", 2.40, 3.30, self.d, audio=(env, 0.0), trimmed="So")
        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"], r["pass"]), (False, False, False), r)


if __name__ == "__main__":
    unittest.main()
