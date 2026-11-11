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


NOV10 = os.path.join(REPO, "runs", "recut_sources_20261111")


@unittest.skipUnless(all(os.path.isfile(os.path.join(NOV10, d, f"lusJ1m-J0Mc.{x}")) for d, x in (("sources", "mp4"), ("transcripts", "json"))),
                     "frozen Nov 10 source + transcript not here")
class TestBoundaryStaysBetweenTheWords(unittest.TestCase):
    """DEC-10 recut 12:22 (runs/pinned_20261111_172202): Natalie 'rally.' (80.40-80.78) | 'But' (80.86-81.02).
    A +-80 ms search put the 'minimum' at 80.93, the stop closure INSIDE 'But', so the cut kept 'Bu' (80.85-80.89
    at -13 / -14 dB) and the render's G3c tail read -22.4 dB. The boundary is searched in the transcript gap."""

    @classmethod
    def setUpClass(cls):
        cls.src = os.path.join(NOV10, "sources", "lusJ1m-J0Mc.mp4")
        cls.words = json.load(open(os.path.join(NOV10, "transcripts", "lusJ1m-J0Mc.json")))["words"]
        cls.sa = L.SourceAudio(cls.src)
        cls.k = next(i for i, w in enumerate(cls.words) if w["word"] == "rally." and 80.3 < w["start"] < 80.5)
        cls.i0 = next(i for i, w in enumerate(cls.words) if w["word"] == "It" and 68.3 < w["start"] < 68.6)

    def test_the_boundary_and_the_cut_sit_before_the_next_word(self):
        nxt = self.words[self.k + 1]
        self.assertEqual(nxt["word"], "But")
        b = L.boundary(self.sa, self.words, self.k)
        self.assertLess(b["point"], nxt["start"], b)
        cut = L.accepted_cut(self.src, L.edge_plan(self.sa, self.words, self.i0, self.k), sa=self.sa)
        self.assertIsNotNone(cut)
        self.assertLess(cut["cut_out"], 80.85, cut)          # 'But' bursts from 80.85 (-15 .. -13 dB)

    def test_the_old_80_ms_margin_lands_inside_the_next_word(self):
        from unittest import mock
        with mock.patch.object(L, "VALLEY_MARGIN_S", 0.080):
            b = L.boundary(self.sa, self.words, self.k)
        nxt = self.words[self.k + 1]
        self.assertTrue(nxt["start"] < b["point"] < nxt["end"], b)   # the defect, reproduced: inside 'But'


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
        # ... with a fade that never overlaps the first word (law L-b): 10 ms .. 2 frames, ending by its onset
        self.assertTrue(10 <= cut["fade_in_ms"] <= int(round(L.VALLEY_FADE_S * 1000)), cut)
        wb = L.edge_word_bounds(self.sa, plan, cut["cut_in"], cut["cut_out"])
        self.assertLessEqual(cut["cut_in"] + cut["fade_in_ms"] / 1000, wb["onset"] + 1e-6, (cut, wb))
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
                mock.patch.object(L, "edge_fades", return_value=(0.083, 0.083, {})), \
                mock.patch.object(L, "neighbour_clear", return_value=(True, {})):
            return L.accepted_cut("unused.wav", plan, sa=object())

    def test_a_normal_edge_failing_cut_accept_rejects_the_clip(self):
        self.assertIsNone(self._accepted(in_pass=True, out_pass=False))

    def test_the_minimum_edge_is_judged_by_neighbour_clear_not_cut_accept(self):
        c = self._accepted(in_pass=False, out_pass=True)
        self.assertIsNotNone(c)
        self.assertEqual((c["valley_in"], c["valley_out"], c["cut_in"], c["cut_out"]), (True, False, 1.0, 5.1))
        self.assertEqual((c["fade_in_ms"], c["fade_out_ms"]), (83, 83))   # DEC-12b: every machine edge


class TestCutStageValleyEdges(unittest.TestCase):
    """DEC-10 d in run_fresh.stage_cut (recut 12:03 HELD there: Natalie OUT 'no >= 60 ms ahead', Yahoo IN 'no
    dip in the prior 100 ms'): an edge the cutter placed at its envelope minimum (valley_in / valley_out) is
    judged by G16's neighbour_clear in the next stage, not by cut_accept's M19 quota; every other edge as before."""

    def _stage_cut(self, flags, m19):
        import shutil
        import tempfile
        from unittest import mock
        import run_fresh as rf
        tmp = tempfile.mkdtemp(prefix="cutstage_")
        self.addCleanup(shutil.rmtree, tmp, True)
        cut = {"clip_id": "clip_01", "video_id": "VID", "cut_in": 10.0, "cut_out": 20.0, "cut_duration": 10.0,
               "verified": True, **flags}
        write = lambda run_dir: json.dump([cut], open(os.path.join(run_dir, "cuts_final.json"), "w"))
        det = {"in": {"pass": m19["in"]}, "out": {"pass": m19["out"]}}
        run = rf.Run(tmp)
        self.assertTrue(rf.machine_placed_cuts(run))
        held = None
        with mock.patch.object(L, "write_lock_cut_table", write), \
                mock.patch.object(rf, "media_summary", return_value={"duration": 100.0}), \
                mock.patch("cut_accept.check_cut_acoustics", return_value=(m19["in"] and m19["out"], det)) as acc:
            try:
                rf.stage_cut(run)
            except rf.Hold as e:
                held = str(e)
        self.assertEqual(acc.call_count, 1)                   # cut_accept still measures every cut
        return held, json.load(open(os.path.join(tmp, "CUT_ACCEPTANCE.json")))[0]

    def test_a_valley_edge_is_deferred_to_g16_with_its_m19_reading_kept(self):
        for side, other in (("in", "out"), ("out", "in")):
            held, rep = self._stage_cut({f"valley_{side}": True}, {side: False, other: True})
            self.assertIsNone(held, side)
            self.assertTrue(rep["pass"], side)
            self.assertIsNone(rep[side]["pass"], side)        # deferred, never recorded as passed
            self.assertEqual(rep[side]["m19"], {"pass": False}, side)
            self.assertIn("G16 neighbour_clear", rep[side]["deferred_to"], side)

    def test_a_normal_edge_failing_m19_still_holds(self):
        held, rep = self._stage_cut({"valley_in": True}, {"in": True, "out": False})
        self.assertIn("cut acceptance rejected", held or "")
        self.assertFalse(rep["pass"])

    def test_without_a_valley_flag_nothing_changes(self):
        held, _ = self._stage_cut({}, {"in": False, "out": True})
        self.assertIn("cut acceptance rejected", held or "")

    def test_g16_is_the_very_next_stage_after_cut(self):
        import re
        import run_fresh as rf
        stages = re.findall(r'run\.stage\("(\w+)"', open(rf.__file__).read())
        self.assertEqual(stages[stages.index("cut") + 1], "sentence_law")


if __name__ == "__main__":
    unittest.main()
