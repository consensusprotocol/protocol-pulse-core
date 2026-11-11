#!/usr/bin/env python3
"""G18 WORD-FOR-WORD (mission 4a): the final says exactly the locked sentences. Must-fail: yesterday's
final (PBX review of pinned_20261110_150345): clip_01 starts on a clipped "above 81,000" and runs into
"All right, you've probably seen people celebrating" (D2/D3a); clip_02 starts on "days of course" (D3b).
Run (GPU parts): cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_word_diff.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110")

import word_diff as W  # noqa: E402


class TestCanonical(unittest.TestCase):
    """Two whisper passes over the SAME audio render numbers and disfluent repeats differently (measured on
    the Nov 10 fixture); both sides are canonicalised alike, real word changes still count."""

    def test_asr_renderings_of_the_same_words_are_equal(self):
        for a, b in (("It went from above $81 ,000 after the election.", "it went from above 81,000 after the election"),
                     ("U .S. Bitcoin ETFs had about $1 .3 billion", "US Bitcoin ETFs had about one point three billion dollars"),
                     ("around $74 000, around the 50 weekly MA", "around seventy four thousand dollars around the fifty weekly MA"),
                     ("241 House winners and 50 senators", "two hundred forty one house winners and fifty senators"),
                     ("up still 25 % off the lows", "up still twenty five percent off the lows"),
                     ("days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped")):
            self.assertEqual(W.diff(a, b), [], (a, b))

    def test_missing_added_and_changed_words_count(self):
        d = W.diff("It went from above $81,000 after the election. That was the week.",
                   "81,000 after the election. That was the week. All right, you've probably seen")
        self.assertIn(("delete", "it went from above", ""), d)
        self.assertIn(("insert", "", "all right you've probably seen"), d)
        self.assertEqual(W.diff("the market fell", "the market rose"), [("replace", "fell", "rose")])
        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "sharply")])

    def test_edges_compare_the_first_and_last_two_words(self):
        self.assertEqual(W.edges("But I don't check it. Many times.", "but i don't check it many times"), [])
        self.assertEqual(W.edges("It went from above $81,000. Just last week.",
                                 "above 81,000. Just last week. All right, people celebrating"),
                         [("start", "it went", "above 81000"), ("end", "last week", "people celebrating")])


def _clips():
    """Yesterday's three clips: the editor's sentences locked on today's transcripts (as the G16 fixture),
    and the source span each was cut from."""
    import sentence_law as L
    tmp = tempfile.mkdtemp(prefix="g18_")
    try:
        shutil.copytree(os.path.join(FIX, "run", "transcripts"), os.path.join(tmp, "t"))
        for f in os.listdir(os.path.join(FIX, "selection", "transcripts_punctuated")):
            shutil.copy(os.path.join(FIX, "selection", "transcripts_punctuated", f), os.path.join(tmp, "t"))
        edl = json.load(open(os.path.join(FIX, "run", "edl.json")))
        sel = {p["video_id"]: p for p in json.load(open(os.path.join(FIX, "selection", "B3_chosen.json")))["chosen"]}
        cuts = {c["clip_id"]: c for c in json.load(open(os.path.join(FIX, "run", "cuts_final.json")))}
        out = {}
        for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]:
            words = json.load(open(os.path.join(tmp, "t", f"{seg['video_id']}.json")))["words"]
            i0, i1, _ = L.anchor(words, sel[seg["video_id"]]["text"])
            out[label] = {"lock_text": " ".join(w["word"] for w in words[i0:i1 + 1]),
                          "source": os.path.join(FIX, "audio", f"src_{seg['video_id']}.flac"),
                          "cut_in": cuts[label]["cut_in"], "cut_out": cuts[label]["cut_out"]}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(os.path.exists("/dev/nvidia0"), "whisper large-v3 needs a GPU")
class TestYesterdaysFinal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        segs = json.load(open(os.path.join(FIX, "run", "concat_manifest_16x9.json")))["segments"]
        cls.ok, rows = W.gate_g18(os.path.join(FIX, "audio", "out_16x9.flac"), segs, _clips())
        cls.rows = {r["segment"]: r for r in rows}

    def test_gate_fails(self):
        self.assertFalse(self.ok, self.rows)

    def test_clip01_clipped_start_and_run_on_fail(self):            # D3a + D2
        r = self.rows["clip_01"]
        self.assertFalse(r["pass"], r)
        self.assertEqual([e[0] for e in r["edges"]], ["start", "end"], r)
        self.assertIn("celebrating", r["edges"][1][2], r)
        self.assertIn(("insert", "", "above"), r["identity"], r)    # the clipped fragment is in the final only

    def test_clip02_start_inside_days_fails(self):                  # D3b
        r = self.rows["clip_02"]
        self.assertFalse(r["pass"], r)
        self.assertEqual(r["edges"][0][:2], ("start", "of course"), r)
        self.assertTrue(r["edges"][0][2].startswith("days"), r)

    def test_hook_words_are_intact(self):
        # D1 (the hook's onset) is acoustic and caught by G16/G17; its words are all there. The lock's own
        # ASR rendering of the fast "73,400, 500" differs from the final's: reported, not gated.
        r = self.rows["hook"]
        self.assertTrue(r["pass"], r)
        self.assertTrue(r["lock_diff_reported"], r)


if __name__ == "__main__":
    unittest.main()
