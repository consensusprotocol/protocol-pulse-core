#!/usr/bin/env python3
"""pipeline/hook_onset.py: G17a at the PIN stage. Batch pin #1 was held at render (01:39 ET Nov 13) because its hook
kept 30 ms of genuine quiet before its first onset. The word record showed a 400 ms gap, but the source held breath,
then DIGITAL ZEROS (a hard edit), then speech. Offline: synthetic 10 ms envelopes, built to the render's own level
rules (sentence_law: speech near -20 dBFS, room tone near -55, digital zeros below DIGITAL_FLOOR_DBFS)."""
import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
