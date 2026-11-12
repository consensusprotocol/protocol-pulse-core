#!/usr/bin/env python3
"""DEC-12f (orchestrator 2026-11-11 14:45): G3b reads each tail three times with 1.5 s of leading context and
takes the majority; the expected last word must be heard in the majority (one context-free decode heard the
corrected Nov 10 cut's '... rally.' as 'route.' while G17b, G18 and the 9:16 decode passed).
must-pass  the corrected cut's tails (runs/pinned_20261111_172202_replay_cut1329, 16:9)
must-fail  yesterday's Natalie tail, which ran on into '... people celebrating', against its locked last word
           'week.'; a tail cut 250 ms into its last word
law L-g    a word the ASR writes as a symbol is read as the spoken word ('$40 trillion' = '40 trillion dollars'):
           must-pass the approved v2f's 9:16 clip_02 '... above 40 trillion dollars.' (two of three readings wrote
           'above $40 trillion'; the Law 22 re-render of 2026-11-11 23:27 UTC failed G3b on it)
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
V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
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

    def test_symbols_are_read_as_the_spoken_words(self):
        """L-g through the one canonical form (pipeline/canon.py): a symbol and its spoken words read the same."""
        same = lambda a, b: Q._g3b_words(a) == Q._g3b_words(b)     # noqa: E731
        self.assertTrue(same("above $40 trillion", "above 40 trillion dollars"))
        self.assertTrue(same("hit $74,000.", "hit 74,000 dollars"))
        self.assertTrue(same("$1.66 billion in outflows", "1.66 billion dollars in outflows"))
        self.assertTrue(same("up 50% today", "up 50 percent today"))
        self.assertEqual(Q._g3b_words("the Monday rally."), ["the", "monday", "rally"])
        self.assertFalse(same("above 40 trillion", "above 40 trillion dollars"))       # no symbol, no 'dollars'
        # batch 14 audit cases: no doubled 'dollars', abbreviated scales, '$' + '%', commas between words
        self.assertTrue(same("above $40 trillion dollars.", "above 40 trillion dollars"))
        self.assertTrue(same("$40M raised", "40 million dollars raised"))
        self.assertEqual(Q._g3b_words("$50% off"), Q._g3b_words("50 percent off"))
        self.assertEqual(Q._g3b_words("well,known fact"), ["well", "known", "fact"])
        self.assertTrue(same("$5 and $6", "5 dollars and 6 dollars"))

    def test_a_leak_of_any_word_of_a_symbol_next_word_fails(self):
        """batch 14 audit (Gemini): the next source word '50%' reads as ['50', 'percent']; hearing either after the
        last word is a leak (the old rule matched the whole '50%' token)."""
        import json as _json
        saved = (Q.extract_audio_region, Q.whisper_segment)
        heard = {"text": "the market rose. percent"}
        Q.extract_audio_region = lambda *a, **k: None
        Q.whisper_segment = lambda wav, qa_dir: heard["text"]
        edl = os.path.join(self.tmp, "edl_leak.json")
        _json.dump({"hook": {}, "clips": [{"index": 1, "next_source_word": "50%"}]}, open(edl, "w"))
        seg = [{"type": "talking_head", "label": "clip_01", "start": 0.0, "end": 10.0, "last_word": "rose."}]
        try:
            ok, table = Q.gate_g3b("x.mp4", seg, self.tmp, edl_path=edl)
            self.assertFalse(ok, table)
            self.assertTrue(table[0]["last_found"] and table[0]["next_leaked"], table)
            self.assertEqual(table[0]["next_source_word"], "50 percent")
            heard["text"] = "the market rose."                       # nothing after the last word: clean
            ok, table = Q.gate_g3b("x.mp4", seg, self.tmp, edl_path=edl)
            self.assertTrue(ok, table)
            heard["text"] = "above $40 trillion"                     # a symbol never stands in for another word
            ok, table = Q.gate_g3b("x.mp4", [{**seg[0], "last_word": "rally."}], self.tmp, edl_path=edl)
            self.assertFalse(ok, table)
            ok, table = Q.gate_g3b("x.mp4", [{**seg[0], "last_word": "$40."}], self.tmp, edl_path=edl)
            self.assertEqual((ok, table[0]["edl_last"]), (True, "dollars"))   # the EDL's word is read the same way
        finally:
            Q.extract_audio_region, Q.whisper_segment = saved

    @unittest.skipUnless(os.path.exists(os.path.join(V2F, "out", "segment_vertical.mp4")), "v2f reference missing")
    def test_v2f_vertical_dollars_tail_passes(self):
        segs = [s for s in _segs(os.path.join(V2F, "qa", "concat_manifest_9x16.json")) if s["label"] == "clip_02"]
        ok, table = Q.gate_g3b(os.path.join(V2F, "out", "segment_vertical.mp4"), segs, self.tmp,
                               edl_path=os.path.join(V2F, "edl.json"))
        self.assertTrue(ok, table)
        self.assertEqual(table[0]["edl_last"], "dollars")

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
