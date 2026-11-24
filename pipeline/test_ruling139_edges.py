#!/usr/bin/env python3
"""RULING 139 (orchestrator 2026-11-17 '12:28'): "CUTTABLE's sentence-edge part FLAGS when the cut sits at a word
boundary; L-v 2's word check and a cut mid-word stay HARD ... a sentence edge is PBX's call to make on review".
RULING 147 (3): it "binds the render's lock too". The render's lock (lock_cut), cut table, G16 and G17 edges plan a
sentence edge at a word boundary like a sentence boundary, marked; the render flags R10's / R9's plain sentence; the
pre-check records it. No audio between the words, a trimmed word's edge and ruling 73's bounds stay HARD; selection
(edge_plan's default) is unchanged."""
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import run_fresh as RF  # noqa: E402
import sentence_law as L  # noqa: E402

NOT_END = "'not' does not end a sentence"


def edge(valid=True, reason=None, pause=(1.0, 1.3), **kw):
    p = None if pause is None else {"start": pause[0], "end": pause[1], "ms": int(round((pause[1] - pause[0]) * 1000))}
    rec = {"after_word": "not", "before_word": "Bitcoin", "valid": valid, "pause": p, "lexical": "punctuation",
           **({"word_gap": {"start": pause[0], "end": pause[1]}, "point": pause[0]} if pause else {}), **kw}
    if reason:
        rec["reason"] = reason
    return rec


class TestSoften(unittest.TestCase):
    def test_a_sentence_edge_at_a_word_boundary_is_softened(self):
        for label, b, why in (
                ("not a sentence end", edge(False, NOT_END), NOT_END),
                ("unpunctuated", edge(False, "unpunctuated transcript stretch: no sentence evidence (fail closed)",
                                      lexical="unpunctuated"),
                 "unpunctuated transcript stretch: no sentence evidence (fail closed)"),
                ("a file end mid-sentence", edge(False, None, file_end=True),
                 "the source file ends on 'not', which ends no sentence")):
            with self.subTest(label):
                L.soften_sentence_edge(b)
                self.assertEqual((b["valid"], b["sentence_edge"], b.get("reason")), (True, why, None))

    def test_everything_else_is_left_as_it_is(self):
        for label, b in (("no audio between the words", edge(False, "no audio between the words", pause=None)),
                         ("no onset at a file head", edge(False, "no onset found at file head", pause=None)),
                         ("another reason", edge(False, "the trimmed word 'so' cannot be cut cleanly")),
                         ("a sentence boundary", edge(True))):
            with self.subTest(label):
                before = json.dumps(b, sort_keys=True)
                L.soften_sentence_edge(b)
                self.assertEqual(json.dumps(b, sort_keys=True), before)


WORDS = [{"word": "It's", "start": 0.4, "end": 0.9}, {"word": "not.", "start": 0.95, "end": 1.0},
         {"word": "Bitcoin", "start": 1.35, "end": 1.8}, {"word": "works", "start": 1.85, "end": 8.95},
         {"word": "today.", "start": 9.4, "end": 9.8}]


class TestPlan(unittest.TestCase):
    def plan(self, bin_, soft, trimmed=None):
        def bound(sa, words, k, tail=False):
            return json.loads(json.dumps(edge(True, pause=(8.95, 9.4)) if tail else bin_))
        with mock.patch.object(L, "boundary", bound), \
                mock.patch.object(L, "trimmed_boundary", lambda sa, words, i0, t: json.loads(json.dumps(bin_))):
            return L.edge_plan(None, WORDS, 2, 3, trimmed=trimmed, sentence_soft=soft)

    def test_selection_keeps_the_hard_rule_the_render_softens_it(self):
        self.assertFalse(self.plan(edge(False, NOT_END), soft=False)["ok"])          # edge_plan's default: selection
        p = self.plan(edge(False, NOT_END), soft=True)
        self.assertTrue(p["ok"], p)
        self.assertEqual((p["in"]["sentence_edge"], p["in"]["cut_lo"], p["in"]["cut_hi"]), (NOT_END, 1.0, 1.3))

    def test_no_audio_between_the_words_and_a_trimmed_edge_stay_hard(self):
        self.assertFalse(self.plan(edge(False, "no audio between the words", pause=None), soft=True)["ok"])
        p = self.plan(edge(False, NOT_END), soft=True, trimmed={"word": "So"})
        self.assertFalse(p["ok"])
        self.assertNotIn("sentence_edge", p["in"])

    def test_the_lock_cut_carries_the_edge_and_the_cut(self):
        def bound(sa, words, k, tail=False):
            return edge(True, pause=(8.95, 9.4)) if tail else edge(False, NOT_END)
        pick = {"cut_in": 1.2, "cut_out": 9.1, "fade_in_ms": 20, "fade_out_ms": 30, "valley_in": False,
                "valley_out": False}
        with mock.patch.object(L, "boundary", bound), mock.patch.object(L, "SourceAudio", lambda s: None), \
                mock.patch.object(L, "accepted_cut", lambda src, plan: dict(pick)):
            r = L.lock_cut("src.mp4", WORDS, {"i0": 2, "i1": 3}, "clip_01")
        self.assertTrue(r["verified"], r)
        self.assertEqual((r["cut_in"], r["sentence_edge"]), (1.2, {"in": NOT_END}))

    def test_g16_passes_a_softened_edge_inside_its_range(self):
        b = L.soften_sentence_edge(edge(False, NOT_END))
        b.update(cut_lo=1.0, cut_hi=1.3, cuttable=True)
        row = L._edge_row(b, 1.2, "in", {"lead_in_pad_s": 0.0})
        self.assertTrue(row["pass"], row)
        self.assertEqual(row["sentence_edge"], NOT_END)
        self.assertFalse(L._edge_row(b, 1.4, "in", {})["pass"])                      # outside the pause: HARD


class TestRenderFlags(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="r139_")
        self.addCleanup(shutil.rmtree, self.d, True)
        with open(os.path.join(self.d, "edl.json"), "w") as f:
            json.dump({"hook": {"channel": "Bitcoin Magazine"},
                       "clips": [{"index": 1, "channel": "Yahoo Finance"}, {"index": 2, "channel": "Natalie Brunell"}]}, f)

    def test_the_in_edge_is_flagged_in_plain_words_never_held(self):
        run = types.SimpleNamespace(dir=self.d, status={}, prov={})
        RF.flag_sentence_edges(run, [{"clip_id": "hook"},
                                     {"clip_id": "clip_01", "sentence_edge": {"in": NOT_END}},
                                     {"clip_id": "clip_02", "sentence_edge": {}}])
        flags = run.status["review_flags"]
        self.assertEqual(len(flags), 1)
        self.assertIn("Yahoo Finance", flags[0])
        self.assertTrue(flags[0].endswith("might start in the middle of a sentence."), flags)
        self.assertEqual(run.status.get("holds"), None)

    def test_ruling_162_an_out_edge_holds_whatever_else_is_marked(self):
        """RULING 162 (1) (orchestrator 07:45 ET Nov 24, from PBX): a clip never ends while the speaker is still
        mid-sentence; ruling 139's flag applies to the IN edge only. The render cannot extend a sealed span: it holds,
        naming every such clip, and flags nothing on the way."""
        for marks in ([{"clip_id": "clip_02", "sentence_edge": {"out": "'it' does not end a sentence"}}],
                      [{"clip_id": "hook", "sentence_edge": {"in": NOT_END, "out": "'and' does not end a sentence"}},
                       {"clip_id": "clip_02", "sentence_edge": {"out": "'it' does not end a sentence"}}]):
            run = types.SimpleNamespace(dir=self.d, status={}, prov={})
            with self.assertRaises(RF.Hold) as cm:
                RF.flag_sentence_edges(run, [{"clip_id": "clip_01"}] + marks)
            self.assertIn("ruling 162 (1)", str(cm.exception))
            for m in marks:
                self.assertIn(f"{m['clip_id']}: {m['sentence_edge']['out']}", str(cm.exception))
            self.assertEqual(run.status.get("review_flags"), None)

    def test_no_edge_no_flag(self):
        run = types.SimpleNamespace(dir=self.d, status={}, prov={})
        RF.flag_sentence_edges(run, [{"clip_id": "hook"}, {"clip_id": "clip_01", "sentence_edge": {}}])
        self.assertEqual(run.status.get("review_flags"), None)

    def test_stage_cut_flags_the_lock_tables_edges(self):
        """N6 (batch 116's mutation run): the stage's own call, not only the helper. The machine-placed table marks
        clip_01's IN; the run is flagged before the cut acceptance looks at any cut (here an unverified cut HOLDS)."""
        run = types.SimpleNamespace(dir=self.d, status={}, prov={}, mode="pinned", machine_cuts=True)

        def table(run_dir):
            with open(os.path.join(run_dir, "cuts_final.json"), "w") as f:
                json.dump([{"clip_id": "hook", "video_id": "v0", "verified": False},
                           {"clip_id": "clip_01", "video_id": "v1", "verified": False, "sentence_edge": {"in": NOT_END}}], f)
        with mock.patch.object(RF.L, "write_lock_cut_table", table):
            with self.assertRaises(RF.Hold):                       # the unverified cuts: the acceptance still decides
                RF.stage_cut(run)
        flags = run.status.get("review_flags") or []
        self.assertEqual(len(flags), 1, flags)
        self.assertIn("Yahoo Finance", flags[0])
        self.assertTrue(flags[0].endswith("might start in the middle of a sentence."), flags)


if __name__ == "__main__":
    unittest.main()
