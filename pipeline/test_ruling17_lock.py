#!/usr/bin/env python3
"""Ruling 17 (orchestrator 2026-11-12 '10:20'): sentence-lock text adjudication, integrity fail-closed.
When the run's own decode differs from the pin's approved text inside a locked span, a difference on a number, a
name or a negation always holds (law L-v 2); otherwise the independent second recogniser on the acquired window
decides: it reads the approved words at every difference -> the lock takes the approved text and G18 compares the
final against it; it reads the run's decode, or neither -> HOLD naming the three readings.
must-fail  the second recogniser siding with the run's decode holds (synthetic, and the real Nov 12 clip_01 head:
           scribe_v1 reads 'I think' where the pin says 'I mean,'); a negation flip holds even when the second
           recogniser sides with the pin (2-1); a number or a mid-sentence name difference holds
must-pass  the second recogniser reading the approved words: the lock takes them, its digest verifies, and G18 then
           compares the final with the adjudicated text (not a third decode of the source span)
Ruling 18 ('10:36') replaces the HOLD for an even split on ONE non-critical token: the lock records both attested
readings; G18 passes that token only when the final's decode reads one of them AND the prepared clip's audio over
the token is the source's (G17c's comparison). must-fail: a third word; the token's audio attenuated or replaced;
'can' / 'can't'; '15' / '50'; two ambiguous tokens in one span; the Nov 10 fixtures (test_word_diff).
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_ruling17_lock.py"""
import json
import os
import sys
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import pinned as P  # noqa: E402
import sentence_law as L  # noqa: E402
import word_diff as WD  # noqa: E402

NOV12 = os.path.join(REPO, "runs", "pinned_20261112_135315")
FIX = os.path.join(PIPELINE, "fixtures", "ruling17", "c1JGheQBPH4.scribe.json")


def _words(text, t0=10.0, step=0.4):
    return [{"word": w, "start": t0 + k * step, "end": t0 + k * step + 0.35} for k, w in enumerate(text.split())]


def _lock(run_text, approved):
    w = _words(run_text)
    return L.make_lock("vid", w, 0, len(w) - 1, "0" * 64, approved, None, 0.9, "pinned approved_text"), w


def _reads(text, t0=10.0, step=0.4):
    calls = []

    def rec(src):
        calls.append(src)
        return _words(text, t0, step), 0.01
    rec.calls = calls
    return rec


class TestAdjudication(unittest.TestCase):
    RUN = "I think the good news is that it works."
    PIN = "I mean, the good news is that it works."

    def test_the_second_recogniser_reading_the_approved_words_wins(self):
        lock, w = _lock(self.RUN, self.PIN)
        rec = _reads("I mean the good news is that it works.")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None)
        self.assertEqual(new["text"], self.PIN)
        self.assertEqual(new["adjudication"]["verdict"], "approved")
        self.assertEqual(new["adjudication"]["differences"], [["think", "mean"]])
        self.assertEqual(L.verify_lock(new), [])                       # the digest covers the adjudicated text
        self.assertEqual(rec.calls, ["src.mp4"])

    def test_siding_with_the_run_decode_on_one_token_records_both_readings(self):      # ruling 18
        lock, w = _lock(self.RUN, self.PIN)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(self.RUN), log=lambda *_: None)
        self.assertEqual(new["text"], self.RUN)                         # the text stays the run's decode
        alt, = new["alternatives"]
        self.assertEqual((alt["readings"], alt["word_index"], alt["token_index"]), (["think", "mean"], 1, 1))
        self.assertEqual(alt["source_span"], [w[1]["start"], round(w[1]["end"], 3)])
        self.assertEqual(L.verify_lock(new), [])

    def test_siding_with_the_run_decode_on_two_tokens_holds(self):                   # ruling 18: at most one
        run_t, pin_t = "I think the good news is that it works.", "I mean, the good news is how it works."
        lock, w = _lock(run_t, pin_t)
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(run_t), log=lambda *_: None)
        for part in ("the run decode", "run_decode:", "approved:", "second_recogniser:"):
            self.assertIn(part, str(e.exception))

    def test_can_and_cant_or_15_and_50_hold_before_any_vote(self):                  # ruling 18 / L-v 2
        for run_t, pin_t in (("You can do it.", "You can't do it."), ("It took 15 years.", "It took 50 years.")):
            lock, w = _lock(run_t, pin_t)
            rec = _reads(run_t)
            with self.assertRaises(P.PinError) as e:
                P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None)
            self.assertIn("L-v 2", str(e.exception))
            self.assertEqual(rec.calls, [])

    def test_a_reading_of_neither_holds(self):
        lock, w = _lock(self.RUN, self.PIN)
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I guess the good news is that it works."),
                              log=lambda *_: None)
        self.assertIn("reads neither", str(e.exception))

    def test_a_negation_flip_holds_even_at_two_to_one(self):
        lock, w = _lock("Bitcoin is the answer.", "Bitcoin is not the answer.")
        rec = _reads("Bitcoin is not the answer.")
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None)
        self.assertIn("L-v 2", str(e.exception))
        self.assertEqual(rec.calls, [])                                # never put to a vote

    def test_a_number_or_a_name_difference_holds(self):
        for run_t, pin_t in (("It hit 70 thousand today.", "It hit 17 thousand today."),
                             ("Ask Saylor about it.", "Ask Taylor about it.")):
            lock, w = _lock(run_t, pin_t)
            with self.assertRaises(P.PinError):
                P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)

    def test_audit_f1_the_approved_word_elsewhere_in_the_span_is_not_a_vote(self):
        run_t, pin_t = "so I think the plan works and we mean it", "so I mean the plan works and we mean it"
        lock, w = _lock(run_t, pin_t)
        with self.assertRaises(P.PinError):                             # it read 'guess' AT the difference
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("so I guess the plan works and we mean it"),
                              log=lambda *_: None)

    def test_audit_f2_a_deletion_read_as_a_different_word_is_neither(self):
        lock, w = _lock("I think the good news is here", "I the good news is here")
        with self.assertRaises(P.PinError):
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I guess the good news is here"),
                              log=lambda *_: None)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I the good news is here"), log=lambda *_: None)
        self.assertEqual(new["text"], "I the good news is here")

    def test_audit_f3_ordinals_and_grouped_numbers_are_numbers(self):
        for run_t, pin_t in (("the 2nd time", "the 3rd time"), ("the second time", "the third time"),
                             ("about 1,000 people", "about 1,500 people")):
            lock, w = _lock(run_t, pin_t)
            with self.assertRaises(P.PinError) as e:
                P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)
            self.assertIn("L-v 2", str(e.exception))

    def test_audit_c2_f1_a_difference_at_the_span_start_needs_nothing_before_it(self):
        lock, w = _lock("think the good news is here", "the good news is here")
        with self.assertRaises(P.PinError):                             # it read 'guess' before 'the'
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("guess the good news is here"), log=lambda *_: None)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("the good news is here"), log=lambda *_: None)
        self.assertEqual(new["text"], "the good news is here")

    def test_audit_c2_f2_spelled_cardinals_are_numbers(self):              # canon writes 'one' as '1'
        lock, w = _lock("We need one more block.", "We need two more blocks.")
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("We need two more blocks."), log=lambda *_: None)
        self.assertIn("L-v 2", str(e.exception))

    def test_audit_b34_indices_are_relative_to_the_locked_span(self):
        # the lock text is words i0..i1 only, so the diff and the token mapping are span-relative: a span in the
        # middle of a transcript maps the ambiguous token to the right word, and a boundary is the span's
        w = _words("so as I said earlier I think the good news is here okay")
        lock = L.make_lock("vid", w, 5, 10, "0" * 64, "I mean the good news is", None, 0.9, "x")   # words 5..10
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("so as I said earlier I think the good news is here okay"),
                                log=lambda *_: None)
        alt, = new["alternatives"]
        self.assertEqual((alt["word_index"], w[alt["word_index"]]["word"]), (6, "think"))

    def test_no_difference_keeps_the_lock_and_asks_nobody(self):
        lock, w = _lock(self.PIN, "I mean the good news is that it works.")
        rec = _reads("anything")
        self.assertIs(P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None), lock)
        self.assertEqual(rec.calls, [])


class TestRuling84b(unittest.TestCase):
    """RULING 84 (b) (orchestrator 2026-11-13 '20:40') in adjudicate_lock: where the second recogniser reads ONE function
    word against the decode's one (it reads the approved words), the lock keeps the decode's word and records the other
    reading (ruling 18's record); two or more such in one span hold; a content word stays ruling 17's."""

    def test_one_function_word_keeps_the_decodes_word_and_records_the_other(self):
        lock, w = _lock("I go to the bank today.", "I go to a bank today.")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I go to a bank today."), log=lambda *_: None)
        self.assertEqual(new["text"], "I go to the bank today.")
        self.assertNotIn("adjudication", new)
        alt, = new["alternatives"]
        self.assertEqual((alt["readings"], alt["token_index"], alt["word_index"]), (["the", "a"], 3, 3))
        self.assertEqual(alt["source_span"], [w[3]["start"], round(w[3]["end"], 3)])
        self.assertEqual(L.verify_lock(new), [])
        for heard in ("I go to the bank today.", "I go to a bank today."):            # G18 passes either reading
            self.assertEqual(WD.diff(new["text"], heard, alts=new["alternatives"]), [])
        self.assertTrue(WD.diff(new["text"], "I go to my bank today.", alts=new["alternatives"]))   # a third: no

    def test_with_fillers_the_rest_is_ruling_17s(self):
        run_t = "So it will replace or be replaced. So it is gone."
        pin_t = "So it will replace, uh, or be replaced, or it is gone."
        lock, w = _lock(run_t, pin_t)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)
        self.assertEqual(new["text"], "So it will replace, uh, or be replaced, so it is gone.")
        self.assertEqual(new["adjudication"]["differences"], [["", "uh"]])
        alt, = new["alternatives"]
        self.assertEqual((alt["readings"], w[alt["word_index"]]["word"]), (["so", "or"], "So"))
        self.assertEqual(WD._alt_positions(new["text"], new["alternatives"]), {alt["token_index"]: {"so", "or"}})
        self.assertEqual(L.verify_lock(new), [])

    def test_two_function_words_in_one_span_hold(self):
        lock, w = _lock("I go to the bank in town.", "I go to a bank on town.")
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I go to a bank on town."), log=lambda *_: None)
        self.assertIn("ruling 84 (b): two or more in one span hold", str(e.exception))

    def test_a_content_word_is_still_adopted_by_ruling_17(self):
        lock, w = _lock("The bank holds the money.", "The bank owns the money.")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("The bank owns the money."), log=lambda *_: None)
        self.assertEqual((new["text"], new["adjudication"]["differences"]), ("The bank owns the money.", [["holds", "owns"]]))
        self.assertNotIn("alternatives", new)

    def test_the_word_takes_the_approved_words_punctuation_and_capital(self):
        self.assertEqual(P._with_token("replaced, or real estate.", 1, "so"), "replaced, so real estate.")
        self.assertEqual(P._with_token("replaced. Or real estate.", 1, "so"), "replaced. So real estate.")
        self.assertEqual(P._with_token("and i think", 1, "i"), "and I think")
        self.assertIsNone(P._with_token("it is and/or not", 2, "so"))       # not one whole word: fail closed


@unittest.skipUnless(os.path.isdir(os.path.join(NOV12, "transcripts")) and os.path.exists(FIX),
                     "the Nov 12 moments run not on this machine")
class TestNov12Clip01Head(unittest.TestCase):
    def test_scribe_reads_i_think_so_both_readings_are_recorded(self):                # ruling 18
        edl = json.load(open(os.path.join(NOV12, "edl.json")))
        lock = edl["clips"][0]["selection_lock"]
        words = json.load(open(os.path.join(NOV12, "transcripts", "c1JGheQBPH4.json")))["words"]
        sw = [{"word": x["text"], "start": x["start"], "end": x["end"]}
              for x in json.load(open(FIX))["words"] if x.get("type") == "word"]
        new = P.adjudicate_lock(lock, "unused.mp4", words, recognise=lambda src: (sw, 0.008), log=lambda *_: None)
        alt, = new["alternatives"]
        self.assertEqual(alt["readings"], ["think", "mean"])
        self.assertEqual(alt["source_span"], [14.84, 15.32])
        self.assertEqual(alt["word_index"], lock["i0"] + 1)


@unittest.skipUnless(os.path.isdir(os.path.join(NOV12, "sources")) and os.path.exists(FIX),
                     "the Nov 12 moments run not on this machine")
class TestG18WithAttestedReadings(unittest.TestCase):
    """Ruling 18 on the real Nov 12 clip_01 (its source and prepared clip); the final's decode is supplied."""

    @classmethod
    def setUpClass(cls):
        import shutil
        import subprocess
        import tempfile
        cls.tmp = tempfile.mkdtemp(prefix="r18_")
        edl = json.load(open(os.path.join(NOV12, "edl.json")))
        words = json.load(open(os.path.join(NOV12, "transcripts", "c1JGheQBPH4.json")))["words"]
        sw = [{"word": x["text"], "start": x["start"], "end": x["end"]}
              for x in json.load(open(FIX))["words"] if x.get("type") == "word"]
        cls.lock = P.adjudicate_lock(edl["clips"][0]["selection_lock"], "unused.mp4", words,
                                     recognise=lambda src: (sw, 0.008), log=lambda *_: None)
        cut = next(c for c in json.load(open(os.path.join(NOV12, "cuts_final.json"))) if c["clip_id"] == "clip_01")
        cls.cut = cut
        cls.src = os.path.join(NOV12, "sources", "c1JGheQBPH4.mp4")
        cls.prepared = os.path.join(NOV12, "qa", "final_clip_01.mp4")
        a, b = (x - cut["cut_in"] for x in cls.lock["alternatives"][0]["source_span"])
        cls.attenuated = os.path.join(cls.tmp, "attenuated.mp4")       # the token's audio 3 dB down
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cls.prepared, "-c:v", "copy", "-af",
                        f"volume=enable='between(t,{a:.3f},{b:.3f})':volume=0.708", "-c:a", "aac", "-b:a", "192k",
                        cls.attenuated], check=True)
        cls.replaced = os.path.join(cls.tmp, "replaced.mp4")           # the token's audio replaced by silence
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", cls.prepared, "-c:v", "copy", "-af",
                        f"volume=enable='between(t,{a:.3f},{b:.3f})':volume=0", "-c:a", "aac", "-b:a", "192k",
                        cls.replaced], check=True)
        cls._rm = staticmethod(lambda: shutil.rmtree(cls.tmp, ignore_errors=True))

    @classmethod
    def tearDownClass(cls):
        cls._rm()

    def _g18(self, heard, prepared=None):
        clips = {"clip_01": {"lock_text": self.lock["text"], "source": self.src, "cut_in": self.cut["cut_in"],
                             "cut_out": self.cut["cut_out"], "pad_s": 0.0, "alternatives": self.lock["alternatives"],
                             "prepared": prepared or self.prepared}}
        segs = [{"label": "clip_01", "type": "talking_head", "start": 0.0,
                 "end": self.cut["cut_out"] - self.cut["cut_in"]}]
        tr = _Tr(heard, "The good news about Bitcoin.")
        tr.span = lambda media, t0, t1: heard if media == self.prepared else "The good news about Bitcoin."
        return WD.gate_g18(self.prepared, segs, clips, transcriber=tr)

    def test_either_attested_reading_passes_on_the_untouched_audio(self):
        for head in ("I mean,", "I think"):
            heard = self.lock["text"].replace("I think", head, 1)
            ok, rows = self._g18(heard)
            self.assertTrue(ok, rows)
            self.assertTrue(rows[0]["alternatives"][0]["acoustic_prepared"]["ok"], rows)

    def test_a_third_word_fails(self):
        ok, rows = self._g18(self.lock["text"].replace("I think", "I guess", 1))
        self.assertFalse(ok)

    def test_the_tokens_audio_attenuated_or_replaced_fails(self):
        heard = self.lock["text"].replace("I think", "I mean,", 1)
        for bad in (self.attenuated, self.replaced):
            ok, rows = self._g18(heard, prepared=bad)
            self.assertFalse(ok, rows)
            self.assertTrue(rows[0].get("acoustic_mismatch"), rows)


class _Tr:
    def __init__(self, final_text, source_text):
        self.final_text, self.source_text = final_text, source_text

    def span(self, media, t0, t1):
        return self.final_text if media == "final.mp4" else self.source_text


class TestG18AgainstTheAdjudicatedLock(unittest.TestCase):
    LOCK = "I mean, the good news about Bitcoin is it's not, you know, its success is not dependent upon us."
    SEGS = [{"label": "clip_01", "type": "talking_head", "start": 0.0, "end": 10.0}]

    def _g18(self, heard, source_heard, adjudicated):
        clips = {"clip_01": {"lock_text": self.LOCK, "source": "src.mp4", "cut_in": 1.0, "cut_out": 11.0,
                             "adjudicated": adjudicated}}
        return WD.gate_g18("final.mp4", self.SEGS, clips, transcriber=_Tr(heard, source_heard))

    def test_the_final_matching_the_adjudicated_lock_passes(self):
        third = "The good news about Bitcoin is its success is not dependent upon us."
        ok, rows = self._g18(self.LOCK, third, adjudicated=True)
        self.assertTrue(ok, rows)
        self.assertEqual(rows[0]["identity_reference"], "the adjudicated lock text (ruling 17)")
        self.assertFalse(self._g18(self.LOCK, third, adjudicated=False)[0])  # unadjudicated: unchanged, fails

    def test_a_dropped_word_against_the_adjudicated_lock_still_fails(self):
        heard = self.LOCK.replace("is not dependent", "is dependent")
        ok, rows = self._g18(heard, heard, adjudicated=True)
        self.assertFalse(ok, rows)


if __name__ == "__main__":
    unittest.main()
