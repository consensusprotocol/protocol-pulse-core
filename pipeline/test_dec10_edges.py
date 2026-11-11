#!/usr/bin/env python3
"""DEC-10 (orchestrator 2026-11-11 10:35): the sentence law's TIMING constants are calibrated to the approved
v2f reference (measured 10:45, DoD "DEC-10a"); what a listener hears stays strict.
  must-pass  every v2f edge: its cut lies in the timing-legal range of its pause (or envelope-minimum valley)
             and keeps no audible part of the neighbour word with v2f's own 20 / 30 ms fades. (Lexical
             sentence-completeness is not part of this: v2f predates the law: hook ends on 'Today,', clip_03
             starts mid-sentence; DEC-10 keeps that rule strict for new cuts.)
  recorded   v2f's hook head (file head, 70 ms genuine quiet, no pad) fails ONLY the unchanged D1 head rule,
             the one rule that keeps yesterday's 'half Bitcoin' (60 ms, no pad) failing; and v2f clip_01's OUT
             edge is PBX's own documented ONE-TIME exception (cut with --allow-clip1-gap-ms 20, "the 60 ms rule
             unchanged"): the envelope shows its cut at 249.63 inside the soft "So" whisper places at
             249.54-249.76, so it is not a baseline and must keep failing; and v2f clip_02's IN edge cuts at
             624.63 inside a 110 ms voiced stretch at speech level (-20..-26 dB, 624.56-624.67) between the dips
             at 624.54 and 624.69: it keeps an audible part of a word, so the strict neighbour rule fails it.
  new rules  an abutting sentence boundary is cut at the envelope minimum with a 2-frame fade; a given cut that
             keeps the neighbour audible fails neighbour_clear.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_dec10_edges.py"""
import json
import os
import sys
import unittest

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import sentence_law as L  # noqa: E402
from test_sentence_windows import _sentences  # noqa: E402

V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run")


def _edges(run):
    cuts = json.load(open(os.path.join(run, "cuts_final.json")))
    out = []
    for c in (cuts if isinstance(cuts, list) else cuts["cuts"]):
        words = json.load(open(os.path.join(run, "transcripts", f"{c['video_id']}.json")))["words"]
        sa = L.SourceAudio(os.path.join(run, "sources", f"{c['video_id']}.mp4"))
        mid = lambda w: (w["start"] + w["end"]) / 2
        i0 = next(i for i, w in enumerate(words) if mid(w) > c["cut_in"])
        i1 = max(i for i, w in enumerate(words) if mid(w) < c["cut_out"])
        out.append((c, sa, L.boundary(sa, words, i0 - 1), L.boundary(sa, words, i1)))
    return out


@unittest.skipUnless(os.path.isdir(V2F), "frozen v2f reference not on this machine")
class TestV2fEdgesPass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edges = _edges(V2F)

    def test_every_v2f_edge_is_timing_legal_and_keeps_no_audible_neighbour(self):
        rows = []
        for c, sa, bin_, bout in self.edges:
            for side, b, cut in (("in", bin_, c["cut_in"]), ("out", bout, c["cut_out"])):
                if b.get("file_head") or (c["clip_id"], side) in (("clip_01", "out"), ("clip_02", "in")):
                    continue                                  # recorded below
                g = b["word_gap"]                                 # the heard gap (DEC-10)
                lo, hi = (g["start"], g["end"] - L.LEAD_MIN_S) if side == "in" else \
                    (g["start"] + L.TAIL_MIN_S, g["end"] - (0.0 if b.get("file_end") else L.GUARD_S))
                in_range = lo - L.EDGE_EPS_S <= cut <= hi + L.EDGE_EPS_S
                plan = {"in": bin_ if side == "in" else {"file_head": True},
                        "out": bout if side == "out" else {"file_end": True}}
                clear, det = L.neighbour_clear(sa, plan, c["cut_in"], c["cut_out"],
                                               c.get("fade_in_ms", 20) / 1000, c.get("fade_out_ms", 30) / 1000)
                rows.append((c["clip_id"], side, in_range, clear, cut, g, b.get("point"), det.get(side)))
        self.assertEqual(len(rows), 5)
        for r in rows:
            self.assertTrue(r[2] and r[3], r)

    def test_v2f_clip01_out_one_time_exception_keeps_failing(self):
        c, sa, bin_, bout = self.edges[1]
        self.assertEqual(c["clip_id"], "clip_01")
        plan = {"in": {"file_head": True}, "out": bout}
        clear, det = L.neighbour_clear(sa, plan, c["cut_in"], c["cut_out"], 0.020, 0.030)
        self.assertFalse(clear, det)                          # it keeps part of the next word

    def test_v2f_clip02_in_keeps_a_voiced_stretch_and_fails_the_neighbour_rule(self):
        c, sa, bin_, bout = self.edges[2]
        self.assertEqual(c["clip_id"], "clip_02")
        clear, det = L.neighbour_clear(sa, {"in": bin_, "out": {"file_end": True}}, c["cut_in"], c["cut_out"], 0.020, 0.030)
        self.assertFalse(clear, det)

    def test_v2f_hook_head_fails_only_the_d1_head_rule(self):
        c, sa, bin_, bout = self.edges[0]
        self.assertEqual(c["clip_id"], "hook")
        self.assertTrue(bin_["file_head"])
        self.assertLess(bin_["genuine_lead_ms"], L.HEAD_LEAD_MIN_S * 1000)
        self.assertEqual(float(c.get("lead_in_pad_s") or 0), 0.0)


class TestValleyCut(unittest.TestCase):
    """Two sentences whose words ABUT (no gap at all; each word has a smooth sin^2 envelope, so the junction
    is a dip without a quiet run): before DEC-10 no boundary at all; now cut at that minimum, 2-frame fade."""

    def setUp(self):
        import shutil
        import subprocess
        import tempfile
        self.tmp = tempfile.mkdtemp(prefix="valley_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        sr, dur = 48000, 9.0
        self.words, t = [], 0.5
        for si in range(3):                                   # sentence 0 abuts sentence 1; a 0.5 s pause after 1
            for wi in range(10):
                self.words.append({"word": f"vs{si}w{wi}" + ("." if wi == 9 else ""), "start": round(t, 3),
                                   "end": round(t + 0.25, 3)})
                t += 0.25
            t += 0.5 if si == 1 else 0.0
        x = np.random.default_rng(5).normal(0, 0.0005, int(dur * sr))
        for i, w in enumerate(self.words):
            a, b = int(round(w["start"] * sr)), int(round(w["end"] * sr))
            n = np.arange(b - a)
            x[a:b] += 0.1 * np.sin(np.pi * n / (b - a)) ** 2 * np.sin(2 * np.pi * (250 + 30 * (i % 3)) * n / sr)
        self.src = os.path.join(self.tmp, "s.wav")
        raw = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "-", self.src],
                       input=raw, check=True)
        self.sa = L.SourceAudio(self.src)
        self.junction = self.words[9]["end"]                  # 'vs0w9.' | 'vs1w0': 3.0 s

    def test_abutting_sentences_cut_at_the_minimum_with_a_two_frame_fade(self):
        k = 9
        b = L.boundary(self.sa, self.words, k)
        self.assertTrue(b["valid"], b)
        self.assertLess(b["pause"]["ms"], L.SHORT_IN_S * 1000, b["pause"])   # a short gap (the sin^2 dip)
        plan = L.edge_plan(self.sa, self.words, k + 1, 19)
        self.assertTrue(plan["ok"], plan)
        cut = L.accepted_cut(self.src, plan, sa=self.sa)
        self.assertIsNotNone(cut)
        self.assertTrue(cut["valley_in"], cut)                # unconditionally the valley path ...
        self.assertEqual(cut["fade_in_ms"], int(round(L.VALLEY_FADE_S * 1000)))   # ... with the 2-frame fade
        self.assertLessEqual(abs(cut["cut_in"] - self.junction), L.HOP_S + 1e-9, (cut["cut_in"], self.junction))

    def test_a_given_cut_inside_the_neighbour_word_is_audible(self):
        k = 9
        plan = L.edge_plan(self.sa, self.words, k + 1, 19)
        inside = self.words[k]["end"] - 0.12                  # 120 ms inside 'vs0w9.' (near its peak)
        ok, det = L.neighbour_clear(self.sa, plan, inside, plan["out"]["cut"], 0.020, 0.030)
        self.assertFalse(ok, det)
        self.assertIn("audible", det["in"]["why"])


class TestMixedEdgeAcoustics(unittest.TestCase):
    """Batch-8 Heimdall F2: with one edge cut at its minimum, the OTHER edge still passes cut_accept's checks."""

    def _accepted(self, in_pass, out_pass):
        from unittest import mock
        plan = {"in": {"point": 1.0, "pause": {"ms": 0}}, "out": {"point": 5.0, "pause": {"ms": 300}}}
        cand = {"in": [1.0], "out": [5.1], "valley": {"in": True, "out": False}}
        det = {"in": {"pass": in_pass}, "out": {"pass": out_pass}}
        with mock.patch.object(L, "cut_candidates", return_value=cand), \
                mock.patch("cut_accept.check_cut_acoustics", return_value=(in_pass and out_pass, det)), \
                mock.patch.object(L, "neighbour_clear", return_value=(True, {})):
            return L.accepted_cut("unused.wav", plan, sa=object())

    def test_a_normal_edge_failing_cut_accept_rejects_the_clip(self):
        self.assertIsNone(self._accepted(in_pass=True, out_pass=False))

    def test_the_minimum_edge_is_judged_by_neighbour_clear_not_cut_accept(self):
        c = self._accepted(in_pass=False, out_pass=True)
        self.assertIsNotNone(c)
        self.assertEqual((c["valley_in"], c["valley_out"], c["cut_in"], c["cut_out"]), (True, False, 1.0, 5.1))
        self.assertEqual((c["fade_in_ms"], c["fade_out_ms"]), (83, 30))


if __name__ == "__main__":
    unittest.main()
