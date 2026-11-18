#!/usr/bin/env python3
"""RULING 146 (2) (orchestrator 2026-11-18 '07:55'): G17a, the quiet before the hook's first word, is SOFT: the render
flags 'The opening clip may start abruptly.' and never holds on it. A cut mid-word stays HARD.
lock_cut     a hook hook_lead cannot give 80 ms keeps the planned cut (accepted_cut's), marked "short"; a segment
             with no clean cut is still refused
run_fresh    the cut table's short hook, a shot snap short of the hook's 80 ms and G17a's hook row each flag (one
             flag in all); every other G17a row, every tail and a refused snap judge as before"""
import os
import sys
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import run_fresh as RF  # noqa: E402
import sentence_law as L  # noqa: E402

ABRUPT = "The opening clip may start abruptly."          # the ruling's words
SHORT = ("no legal cut in the pause keeps 80 ms of genuine quiet before the hook's first word (best 30 ms), and no "
         "legal cut has genuine quiet from the cut to the word for a D1 pad to join (digital zeros lie between)")


class TestLockCut(unittest.TestCase):
    PLAN = {"ok": True, "in": {"pause": [1.0, 1.3], "lead_in_pad_s": 0.0, "cut_lo": 1.0, "cut_hi": 1.3},
            "out": {"pause": [9.0, 9.4], "cut_lo": 9.0, "cut_hi": 9.4}}
    PICK = {"cut_in": 1.02, "cut_out": 9.1, "fade_in_ms": 20, "fade_out_ms": 30, "valley_in": True,
            "valley_out": False}

    def cut(self, hook, label="hook", pick=True):
        calls = []

        def lead(src, plan, p):
            calls.append(p["cut_in"])
            return dict(hook)
        with mock.patch.object(L, "SourceAudio", lambda src: None), \
                mock.patch.object(L, "edge_plan", lambda *a, **k: self.PLAN), \
                mock.patch.object(L, "accepted_cut", lambda src, plan: dict(self.PICK) if pick else None), \
                mock.patch.object(L, "hook_lead", lead):
            return L.lock_cut("src.mp4", [], {"i0": 0, "i1": 3}, label), calls

    def test_a_hook_short_of_80_ms_keeps_the_planned_cut_marked_short(self):
        r, calls = self.cut({"need_ms": 80, "planned_cut_in": 1.02, "planned_lead_ms": 30, "refused": SHORT,
                             "tried": [{"cut_in": 1.05, "lead_ms": 30}]})
        self.assertEqual(calls, [1.02])
        self.assertTrue(r["verified"], r)
        self.assertNotIn("error", r)
        self.assertEqual((r["cut_in"], r["cut_out"], r["fade_in_ms"], r["lead_in_pad_s"], r["valley_in"]),
                         (1.02, 9.1, 20, 0.0, True))
        self.assertEqual((r["hook_lead"]["short"], r["hook_lead"]["lead_ms"]), (SHORT, 30))
        self.assertNotIn("refused", r["hook_lead"])          # nothing downstream reads it as a refusal

    def test_a_hook_hook_lead_can_open_is_unchanged(self):
        r, _ = self.cut({"need_ms": 80, "planned_cut_in": 1.02, "planned_lead_ms": 30, "cut_in": 1.0, "fade_in_ms": 10,
                         "pad_s": 0.0, "lead_ms": 90, "how": "moved inside the pause to keep 80 ms"})
        self.assertEqual((r["cut_in"], r["fade_in_ms"], r["valley_in"]), (1.0, 10, False))
        self.assertNotIn("short", r["hook_lead"])

    def test_a_clip_never_asks_the_hook_rule(self):
        r, calls = self.cut({"refused": SHORT}, label="clip_01")
        self.assertEqual((calls, r["cut_in"], r.get("hook_lead")), ([], 1.02, None))

    def test_a_segment_with_no_clean_cut_is_still_refused(self):      # HARD: never a cut through a word
        r, calls = self.cut({"refused": SHORT}, pick=False)
        self.assertIn("no cut inside the locked pauses keeps the neighbour words inaudible", r["error"])
        self.assertNotIn("cut_in", r)


def run():
    return types.SimpleNamespace(status={}, prov={})


class TestRenderFlags(unittest.TestCase):
    def table(self, hook_lead_ok=False, hook_tail_ok=True, clip_ok=True):
        return [{"segment": "hook", "lead_ms": 30, "tail_ms": 200, "lead_ok": hook_lead_ok, "tail_ok": hook_tail_ok,
                 "pass": hook_lead_ok and hook_tail_ok},
                {"segment": "clip_01", "lead_ms": 0, "tail_ms": 90, "lead_ok": True, "tail_ok": clip_ok,
                 "pass": clip_ok}]

    def test_g17a_a_hook_short_of_80_ms_passes_the_row_and_is_flagged(self):
        r, t = run(), self.table()
        self.assertTrue(RF.g17a_hook_lead_soft(r, False, t))
        self.assertEqual(r.status["review_flags"], [ABRUPT])
        self.assertIn("the hook keeps 30 ms of quiet before its first word (< 80 ms)", r.prov["review_flags"][0]["detail"])
        self.assertEqual(t[0]["lead_soft"], "ruling 146 (2)")

    def test_g17a_every_other_failure_still_fails_the_row(self):
        for label, t in (("the hook's tail", self.table(hook_tail_ok=False)),
                         ("another clip", self.table(clip_ok=False))):
            with self.subTest(label):
                self.assertFalse(RF.g17a_hook_lead_soft(run(), False, t))

    def test_g17a_a_passing_table_is_untouched(self):
        r = run()
        self.assertTrue(RF.g17a_hook_lead_soft(r, True, self.table(hook_lead_ok=True)))
        self.assertEqual(r.status.get("review_flags"), None)

    def test_the_cut_tables_short_hook_is_flagged(self):
        r = run()
        RF.flag_short_hook_cut(r, [{"clip_id": "hook", "hook_lead": {"short": SHORT}}, {"clip_id": "clip_01"},
                                   {"clip_id": "clip_02", "hook_lead": {"lead_ms": 120}}])
        self.assertEqual(r.status["review_flags"], [ABRUPT])
        self.assertIn(SHORT, r.prov["review_flags"][0]["detail"])

    def test_a_snap_short_of_the_hooks_80_ms_is_flagged_a_refused_snap_holds(self):
        r = run()
        RF.snap_verdict(r, "hook", {"snapped": True, "hook_lead_short": "the speaker's own shot starts 0.050 s"})
        self.assertEqual(r.status["review_flags"], [ABRUPT])
        with self.assertRaisesRegex(RF.Hold, r"clip_01: shot snap refused \(ruling 71\): the speaker's own shot ends"):
            RF.snap_verdict(run(), "clip_01", {"refused": "the speaker's own shot ends 0.010 s after the last word"})
        r2 = run()
        RF.snap_verdict(r2, "clip_01", {"snapped": True})
        self.assertEqual(r2.status.get("review_flags"), None)

    def test_three_findings_make_one_flag(self):
        r = run()
        RF.flag_short_hook_cut(r, [{"clip_id": "hook", "hook_lead": {"short": SHORT}}])
        RF.snap_verdict(r, "hook", {"hook_lead_short": "the speaker's own shot starts 0.050 s"})
        RF.g17a_hook_lead_soft(r, False, self.table())
        self.assertEqual(r.status["review_flags"], [ABRUPT])
        self.assertEqual(len(r.prov["review_flags"]), 3)            # each finding's detail kept


if __name__ == "__main__":
    unittest.main()
