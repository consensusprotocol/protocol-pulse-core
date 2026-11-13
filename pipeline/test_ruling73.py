#!/usr/bin/env python3
"""RULING 73 (orchestrator 2026-11-13 '18:00'), THE CUT FOLLOWS THE LOCK'S WORDS. (a) OUT is never before the decoded
end of the last locked word: the tail pause is searched only after it. (b) IN is never more than 400 ms before the first
locked word's decoded start; dead air is trimmed. The head-lead rule is unchanged.
MUST-FAIL on pin 13949b7c's real spans (run pinned_20261113_221758), held at prepare 17:23:
- the hook's cut fell in 'or [130 ms] reissued.' inside the decoded last word (27.09 < 27.54);
- clip_01 opened 3.47 s before 'I' (10.97 < 14.44 - 0.40).
Both fail on the old sentence_law and pass on the fix. The delivered pins' cuts stay put, except ONE span measured and
named (the medley reference's hook, 'Bitcoin ... ever.', which opened 0.56 s before its first word).
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES= python3 -m pytest -q pipeline/test_ruling73.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import sentence_law as SL  # noqa: E402

RUNS = "/home/ultron/protocol_pulse/runs"


def words_at(*spans):
    return [{"word": w, "start": a, "end": b} for w, a, b in spans]


class TestTheRangesFollowTheLock(unittest.TestCase):
    """_ruling73 on edge_plan's ranges (no audio)."""

    def test_a_out_never_before_the_last_words_decoded_end(self):
        w = words_at(("or", 26.30, 26.66), ("reissued.", 26.66, 27.54), ("Countries", 27.54, 28.08))
        bout = {"valid": True, "cut_lo": 26.91, "cut_hi": 27.13, "cut": 27.09, "cuttable": True}
        SL._ruling73({}, bout, w, 0, 1)
        self.assertEqual((bout["cut_lo"], bout["cuttable"]), (27.54, False))
        self.assertIn("(ruling 73 a)", bout["reason"])
        ok = {"valid": True, "cut_lo": 31.35, "cut_hi": 31.6, "cut": 31.56, "cuttable": True}   # 41f29b1f clip_02
        SL._ruling73({}, ok, words_at(("x", 31.0, 31.2), ("undervalued.", 31.2, 31.48)), 0, 1)
        self.assertEqual((ok["cut_lo"], ok["cut"], ok["cuttable"]), (31.48, 31.56, True))

    def test_b_in_never_more_than_400_ms_before_the_first_word(self):
        w = words_at(("I", 14.44, 15.04), ("think,", 15.04, 15.52))
        bin_ = {"valid": True, "cut_lo": 10.79, "cut_hi": 15.05, "cut": 10.96, "cuttable": True}
        SL._ruling73(bin_, {}, w, 0, 1)
        self.assertEqual((bin_["cut_lo"], bin_["cut"], bin_["cuttable"]), (14.04, 14.19, True))   # dead air trimmed
        near = {"valid": True, "cut_lo": 14.16, "cut_hi": 14.3, "cut": 14.3, "cuttable": True}  # 37c5b5f5 clip_01
        SL._ruling73(near, {}, words_at(("I", 14.36, 14.5)), 0, 0)
        self.assertEqual((near["cut_lo"], near["cut"], "ruling73_in" in near), (14.16, 14.3, False))
        none = {"valid": True, "cut_lo": 10.0, "cut_hi": 10.5, "cut": 10.2, "cuttable": True}     # no room at all
        SL._ruling73(none, {}, words_at(("I", 14.44, 15.0)), 0, 0)
        self.assertEqual((none["cut_lo"], none["cuttable"]), (14.04, False))
        self.assertIn("(ruling 73 b)", none["reason"])

    def test_b_an_emptied_range_is_not_cuttable(self):
        # batch 69 c2's example (cut_lo 10.0, cut_hi 13.0, first word at 14.0): the range empties and says so
        b = {"valid": True, "cut_lo": 10.0, "cut_hi": 13.0, "cut": 12.0, "cuttable": True}
        SL._ruling73(b, {}, words_at(("X", 14.0, 14.4)), 0, 0)
        self.assertEqual((b["cut_lo"], b["cut_hi"], b["cuttable"]), (13.6, 13.0, False))
        self.assertIn("(ruling 73 b)", b["reason"])

    def test_b_a_file_head_keeps_its_quiet_up_to_the_bound(self):
        head = {"valid": True, "file_head": True, "cut_lo": 0.0, "cut_hi": 13.0, "cut": 13.0, "cuttable": True}
        SL._ruling73(head, {}, words_at(("Bitcoin", 14.0, 14.5)), 0, 0)
        self.assertEqual((head["cut_lo"], head["cut_hi"], head["cut"], head["cuttable"]), (13.6, 13.6, 13.6, True))


def _recut(run):
    """The run's cut table recomputed with THIS code on a scratch copy (sources / transcripts linked, edl copied)."""
    tmp = tempfile.mkdtemp(prefix="r73t_")
    try:
        for sub in ("sources", "transcripts"):
            os.symlink(os.path.join(run, sub), os.path.join(tmp, sub))
        shutil.copy(os.path.join(run, "edl.json"), tmp)
        return {c["clip_id"]: c for c in SL.write_lock_cut_table(tmp)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _have(name):
    r = os.path.join(RUNS, name)
    return all(os.path.exists(os.path.join(r, x)) for x in ("edl.json", "sources", "transcripts", "cuts_final.json"))


@unittest.skipUnless(_have("pinned_20261113_221758"), "pin 13949b7c's run")
class TestMustFail13949b7c(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rundir = os.path.join(RUNS, "pinned_20261113_221758")
        cls.cuts = _recut(cls.rundir)
        cls.edl = json.load(open(os.path.join(cls.rundir, "edl.json")))

    def _words(self, vid):
        return json.load(open(os.path.join(self.rundir, "transcripts", f"{vid}.json")))["words"]

    def test_a_the_hooks_out_follows_reissued(self):
        lock = self.edl["hook"]["selection_lock"]
        end = self._words(self.edl["hook"]["video_id"])[lock["i1"]]["end"]       # 'reissued.' 27.54
        self.assertTrue(self.cuts["hook"]["verified"], self.cuts["hook"].get("error"))
        self.assertGreaterEqual(self.cuts["hook"]["cut_out"], end - 1e-9)          # old code: 27.09

    def test_b_clip_01_opens_within_400_ms_of_i(self):
        seg = self.edl["clips"][0]
        start = self._words(seg["video_id"])[seg["selection_lock"]["i0"]]["start"]   # 'I' 14.44
        self.assertTrue(self.cuts["clip_01"]["verified"], self.cuts["clip_01"].get("error"))
        self.assertGreaterEqual(self.cuts["clip_01"]["cut_in"], round(start - SL.IN_LEAD_MAX_S, 3) - 1e-9)  # old: 10.97
        self.assertLessEqual(self.cuts["clip_01"]["cut_in"], start)


HOP = 0.0101
MOVED = {("pinned_20261113_031328", "hook"): 14.57, ("pinned_20261112_165629", "clip_02"): 14.69}


@unittest.skipUnless(all(_have(r) for r in ("pinned_20261113_211048", "pinned_20261113_031328",
                                            "pinned_20261112_165629")), "the delivered pins' runs")
class TestTheDeliveredCuts(unittest.TestCase):
    """0c68b589, 41f29b1f, 37c5b5f5: every cut as recorded (one 10 ms hop), except the one span that opened 0.56 s
    before 'Bitcoin' (its IN moves to the ruling-73 bound: 41f29b1f's hook, 37c5b5f5's clip_02)."""

    def test_unchanged_but_the_named_span(self):
        for name in ("pinned_20261113_211048", "pinned_20261113_031328", "pinned_20261112_165629"):
            run = os.path.join(RUNS, name)
            old = {c["clip_id"]: c for c in json.load(open(os.path.join(run, "cuts_final.json")))}
            new = _recut(run)
            edl = json.load(open(os.path.join(run, "edl.json")))
            segs = dict(SL._segments(edl))
            for cid, o in old.items():
                n = new[cid]
                self.assertLessEqual(abs(n["cut_out"] - o["cut_out"]), HOP, (name, cid, "out", o, n))
                want_in = MOVED.get((name, cid), o["cut_in"])
                self.assertLessEqual(abs(n["cut_in"] - want_in), HOP, (name, cid, "in", o, n))
                seg = segs[cid]                                   # and every cut, moved or not, meets ruling 73
                words = json.load(open(os.path.join(run, "transcripts", f"{seg['video_id']}.json")))["words"]
                lock = seg["selection_lock"]
                self.assertGreaterEqual(n["cut_in"], round(words[lock["i0"]]["start"] - SL.IN_LEAD_MAX_S, 3) - 1e-9)
                self.assertGreaterEqual(n["cut_out"], round(words[lock["i1"]]["end"], 3) - 1e-9)


if __name__ == "__main__":
    unittest.main()
