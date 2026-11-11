#!/usr/bin/env python3
"""DEC-12f (orchestrator 2026-11-11 14:45): G3b reads each tail three times with 1.5 s of leading context and
takes the majority; the expected last word must be heard in the majority (one context-free decode heard the
corrected Nov 10 cut's '... rally.' as 'route.' while G17b, G18 and the 9:16 decode passed).
must-pass  the corrected cut's tails (runs/pinned_20261111_172202_replay_cut1329, 16:9)
must-fail  yesterday's Natalie tail, which ran on into '... people celebrating', against its locked last word
           'week.'; a tail cut 250 ms into its last word
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_g3b_majority.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
sys.path.insert(0, os.path.join(REPO, "segment_v1"))
import qa_gates as Q  # noqa: E402

FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110")
RUN = os.path.join(REPO, "runs", "pinned_20261111_172202_replay_cut1329")


def _segs(manifest, **override):
    out = []
    for s in json.load(open(manifest))["segments"]:
        if s.get("type") == "talking_head":
            out.append({**s, **override.get(s["label"], {})})
    return out


class TestG3bMajority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="g3b_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_three_readings_with_context(self):
        self.assertEqual((Q.G3B_READS, Q.G3B_CONTEXT_S), (3, 1.5))

    @unittest.skipUnless(os.path.exists(os.path.join(FIX, "audio", "out_16x9.flac")), "Nov 10 fixture missing")
    def test_yesterdays_natalie_tail_fails_against_its_locked_last_word(self):
        segs = [s for s in _segs(os.path.join(FIX, "run", "concat_manifest_16x9.json"),
                                 clip_01={"last_word": "week."}) if s["label"] == "clip_01"]
        ok, table = Q.gate_g3b(os.path.join(FIX, "audio", "out_16x9.flac"), segs, self.tmp)
        self.assertFalse(ok, table)
        self.assertFalse(table[0]["last_found"], table)

    @unittest.skipUnless(os.path.exists(os.path.join(RUN, "out", "segment.mp4")), "Nov 11 replay run missing")
    def test_the_corrected_cut_passes(self):
        segs = _segs(os.path.join(RUN, "qa", "concat_manifest_16x9.json"))
        ok, table = Q.gate_g3b(os.path.join(RUN, "out", "segment.mp4"), segs, self.tmp)
        self.assertTrue(ok, table)
        self.assertEqual(len(table), len(segs))
        for e in table:
            self.assertTrue(e["last_found"] and not e["next_leaked"], e)

    @unittest.skipUnless(os.path.exists(os.path.join(RUN, "out", "segment.mp4")), "Nov 11 replay run missing")
    def test_a_tail_cut_inside_its_last_word_fails(self):
        segs = _segs(os.path.join(RUN, "qa", "concat_manifest_16x9.json"))
        c1 = next(s for s in segs if s["label"] == "clip_01")
        cut = {**c1, "end": round(c1["end"] - 0.25, 3)}          # 250 ms into 'rally.' (80.84 -> 80.59)
        ok, table = Q.gate_g3b(os.path.join(RUN, "out", "segment.mp4"), [cut], self.tmp)
        self.assertFalse(ok, table)


if __name__ == "__main__":
    unittest.main()
