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
        self.assertEqual(new["adjudication"]["verdict"], "settled")            # ruling 143: two of three (was 17's)
        self.assertEqual([(x["took"], x["material"]) for x in new["adjudication"]["pairs"]], [("approved", False)])
        self.assertEqual(new["adjudication"]["differences"], [["think", "mean"]])
        self.assertEqual(L.verify_lock(new), [])                       # the digest covers the adjudicated text
        self.assertEqual(rec.calls, ["src.mp4"])
    def test_siding_with_the_run_decode_on_one_token_takes_the_run_reading(self):     # ruling 143 (was 18's record)
        lock, w = _lock(self.RUN, self.PIN)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(self.RUN), log=lambda *_: None)
        self.assertEqual(new["text"], self.RUN)                         # two of three: the run decode's word
        self.assertNotIn("alternatives", new)
        self.assertEqual([(x["took"], x["agreed"]) for x in new["adjudication"]["pairs"]], [("run", ["run", "second"])])
        self.assertEqual(L.verify_lock(new), [])
    def test_siding_with_the_run_decode_on_two_tokens_settles(self):                   # ruling 143 (18's one-token
        run_t, pin_t = "I think the good news is that it works.", "I mean, the good news is how it works."   # cap held it)
        lock, w = _lock(run_t, pin_t)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(run_t), log=lambda *_: None)
        self.assertEqual(new["text"], run_t)
        self.assertEqual([x["took"] for x in new["adjudication"]["pairs"]], ["run", "run"])
    def test_can_and_cant_or_15_and_50_follow_the_two_audio_readings(self):        # ruling 143 (3) (was L-v 2's
        for run_t, pin_t in (("You can do it.", "You can't do it."), ("It took 15 years.", "It took 50 years.")):  # hold)
            with self.subTest(run=run_t):
                lock, w = _lock(run_t, pin_t)                           # the two audio readings agree: corrected
                new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(run_t), log=lambda *_: None)
                self.assertEqual(new["text"], run_t)
                self.assertEqual(len(new["transcript_corrected"]), 1)
                with self.assertRaises(P.PinError) as e:                # they disagree: the real doubt, HOLD
                    P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)
                self.assertIn("ruling 143 (3)", str(e.exception))
    def test_a_reading_of_neither_takes_the_run_decode(self):          # ruling 143 (2) (it held)
        lock, w = _lock(self.RUN, self.PIN)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I guess the good news is that it works."),
                                log=lambda *_: None)
        self.assertEqual(new["text"], self.RUN)
        self.assertEqual(new["adjudication"]["pairs"][0]["second_reads"], "neither")
        self.assertEqual(new["small_words_unsettled"], 1)
    def test_a_negation_flip_holds_when_the_audio_readings_disagree(self):   # ruling 143 (3)
        lock, w = _lock("Bitcoin is the answer.", "Bitcoin is not the answer.")
        rec = _reads("Bitcoin is not the answer.")                      # the second hears the transcript's 'not'
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None)
        self.assertIn("ruling 143 (3)", str(e.exception))
        self.assertEqual(rec.calls, ["src.mp4"])                        # the audio is asked (L-v 2 held before it)
    def test_a_number_or_a_name_difference_holds(self):
        for run_t, pin_t in (("It hit 70 thousand today.", "It hit 17 thousand today."),
                             ("Ask Saylor about it.", "Ask Taylor about it.")):
            lock, w = _lock(run_t, pin_t)
            with self.assertRaises(P.PinError):
                P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)

    def test_audit_f1_the_approved_word_elsewhere_in_the_span_is_not_a_vote(self):
        run_t, pin_t = "so I think the plan works and we mean it", "so I mean the plan works and we mean it"
        lock, w = _lock(run_t, pin_t)                                   # it read 'guess' AT the difference: neither
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("so I guess the plan works and we mean it"),
                                log=lambda *_: None)
        self.assertEqual((new["text"], new["adjudication"]["pairs"][0]["second_reads"]), (run_t, "neither"))
    def test_audit_f2_a_deletion_read_as_a_different_word_is_neither(self):
        lock, w = _lock("I think the good news is here", "I the good news is here")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I guess the good news is here"),
                                log=lambda *_: None)
        self.assertEqual((new["text"], new["adjudication"]["pairs"][0]["second_reads"]),
                         ("I think the good news is here", "neither"))   # ruling 143 (2): the run's (it held)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I the good news is here"), log=lambda *_: None)
        self.assertEqual(new["text"], "I the good news is here")
    def test_audit_f3_ordinals_and_grouped_numbers_are_numbers(self):
        for run_t, pin_t in (("the 2nd time", "the 3rd time"), ("the second time", "the third time"),
                             ("about 1,000 people", "about 1,500 people")):
            lock, w = _lock(run_t, pin_t)
            with self.assertRaises(P.PinError) as e:                    # material, and the audio readings disagree
                P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)
            self.assertIn("ruling 143 (3)", str(e.exception))
    def test_audit_c2_f1_a_difference_at_the_span_start_needs_nothing_before_it(self):
        lock, w = _lock("think the good news is here", "the good news is here")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("guess the good news is here"), log=lambda *_: None)
        self.assertEqual((new["text"], new["adjudication"]["pairs"][0]["second_reads"]),
                         ("think the good news is here", "neither"))     # 'guess' before 'the': not the approved
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("the good news is here"), log=lambda *_: None)
        self.assertEqual(new["text"], "the good news is here")
    def test_audit_c2_f2_spelled_cardinals_are_numbers(self):              # canon writes 'one' as '1'
        lock, w = _lock("We need one more block.", "We need two more blocks.")
        with self.assertRaises(P.PinError) as e:
            P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("We need two more blocks."), log=lambda *_: None)
        self.assertIn("ruling 143 (3)", str(e.exception))
    def test_audit_b34_indices_are_relative_to_the_locked_span(self):
        # the lock text is words i0..i1 only, so the diff is span-relative: a span in the middle of a transcript settles
        # on its own words (ruling 143: the run's reading; ruling 18's index record is gone)
        w = _words("so as I said earlier I think the good news is here okay")
        lock = L.make_lock("vid", w, 5, 10, "0" * 64, "I mean the good news is", None, 0.9, "x")   # words 5..10
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("so as I said earlier I think the good news is here okay"),
                                log=lambda *_: None)
        self.assertEqual((new["text"], [x["took"] for x in new["adjudication"]["pairs"]]),
                         ("I think the good news is", ["run"]))
    def test_no_difference_keeps_the_lock_and_asks_nobody(self):
        lock, w = _lock(self.PIN, "I mean the good news is that it works.")
        rec = _reads("anything")
        self.assertIs(P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None), lock)
        self.assertEqual(rec.calls, [])


class TestRuling84b(unittest.TestCase):
    """RULING 84 (b) (orchestrator 2026-11-13 '20:40') in adjudicate_lock: where the second recogniser reads ONE function
    word against the decode's one (it reads the approved words), the lock keeps the decode's word and records the other
    reading (ruling 18's record); two or more such in one span hold; a content word stays ruling 17's."""

    def test_one_function_word_takes_the_two_of_three_reading(self):        # ruling 143 (84 (b) kept the decode's)
        lock, w = _lock("I go to the bank today.", "I go to a bank today.")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I go to a bank today."), log=lambda *_: None)
        self.assertEqual(new["text"], "I go to a bank today.")
        self.assertNotIn("alternatives", new)
        self.assertEqual(L.verify_lock(new), [])
    def test_with_fillers_the_rest_is_two_of_three(self):                   # ruling 143
        run_t = "So it will replace or be replaced. So it is gone."
        pin_t = "So it will replace, uh, or be replaced, or it is gone."
        lock, w = _lock(run_t, pin_t)
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads(pin_t), log=lambda *_: None)
        self.assertEqual(new["text"], pin_t)                            # the second reads 'or': approved + second
        self.assertEqual(new["spelling_only"], [["", "uh"]])            # ruling 135 (d): the 'uh' is not a word
        self.assertNotIn("alternatives", new)
        self.assertEqual(L.verify_lock(new), [])
    def test_two_function_words_in_one_span_settle(self):                   # ruling 143 (84 (b) held them)
        lock, w = _lock("I go to the bank in town.", "I go to a bank on town.")
        new = P.adjudicate_lock(lock, "src.mp4", w, recognise=_reads("I go to a bank on town."), log=lambda *_: None)
        self.assertEqual(new["text"], "I go to a bank on town.")
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


class TestRuling131(unittest.TestCase):
    """RULING 131 (orchestrator 2026-11-17 '08:25'). (A) per differing pair, two of the three readings (approved text,
    run decode, second recogniser) decide it and the lock takes that reading, at least 3 tokens from both span ends for
    the run decode's reading; never a number, a name or a negation; all three different HOLDS. (B) a currency symbol
    is formatting: '$2 billion' equals a spoken '2 billion' (recorded, nobody asked).
    must-fail  the d6adeb54 shape (a content pair and a filler read as the run's, a function word read as the
               approved's) is settled pair by pair; a pair the run wins exactly 3 tokens from an edge passes; the
               repetition 'that's why that's why' slides to the copy 4 from the end; '$2 billion' / '2 billion' is no
               difference either way round (the old lock held them all)
    must-hold  a pair the run wins 2 tokens from an edge; all three readings different; a number under the '$'"""
    RUN = "And so we built it from a bunch of pieces that we had lying um around the office for years."
    PIN = "And so we built it from a budget pieces like we had lying around the office for years."
    SEC = "And so we built it from a bunch of pieces like we had lying um around the office for years."

    def settle(self, run_t, pin_t, sec_t):
        lock, w = _lock(run_t, pin_t)
        rec = _reads(sec_t)
        return P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None), rec

    def test_each_pair_takes_its_two_of_three_reading(self):
        new, rec = self.settle(self.RUN, self.PIN, self.SEC)
        self.assertEqual(new["text"], "And so we built it from a bunch of pieces like we had lying around the "
                                      "office for years.")          # ruling 135 (d): the 'um' is not a word
        adj = new["adjudication"]
        self.assertTrue(adj["rule"].startswith("ruling 143"), adj["rule"])
        self.assertEqual([(x["run"], x["approved"], x["took"], x["agreed"]) for x in adj["pairs"]],
                         [("bunch of", "budget", "run", ["run", "second"]),
                          ("that", "like", "approved", ["approved", "second"])])
        self.assertEqual(new["spelling_only"], [["um", ""]])
        self.assertEqual((adj["run_decode"], adj["approved"], adj["second_recogniser"]), (self.RUN, self.PIN, self.SEC))
        self.assertEqual(L.verify_lock(new), [])                       # the digest covers the settled text
        self.assertEqual(rec.calls, ["src.mp4"])
    def test_the_run_reading_needs_no_distance_from_the_edge(self):          # ruling 143 (131 (A) wanted 3)
        for run_t, pin_t in (("We went to to the bank and then home.", "We went to the bank and then home."),
                             ("We to to the bank and then home.", "We to the bank and then home.")):
            new, _ = self.settle(run_t, pin_t, run_t)
            self.assertEqual(new["text"], run_t)
    def test_a_repetition_settles_as_the_run_reads_it(self):                # ruling 143 (no edge rule)
        run_t = "It is the bank that owns the money and that's why that's why we Bitcoin."
        new, _ = self.settle(run_t, "It is the bank that owns the money and that's why we Bitcoin.", run_t)
        self.assertEqual(new["text"], run_t)
        run_t = "It is the bank that owns the money we said Bitcoin Bitcoin."
        new, _ = self.settle(run_t, "It is the bank that owns the money we said Bitcoin.", run_t)
        import canon                                                    # the run's word written after the approved
        self.assertEqual(canon.canon_tokens(new["text"]), canon.canon_tokens(run_t))   # 'Bitcoin.': same words
    def test_three_different_readings_take_the_run_decode(self):            # ruling 143 (2) (it held)
        new, _ = self.settle(self.RUN, self.PIN, self.SEC.replace("bunch of", "punch of"))
        self.assertEqual(new["text"], "And so we built it from a bunch of pieces like we had lying around the "
                                      "office for years.")
        self.assertEqual(new["small_words_unsettled"], 1)
    def test_a_currency_symbol_is_formatting_either_way_round(self):
        for run_t, pin_t in (("They raised 2 billion last year from the fund.", "They raised $2 billion last year "
                              "from the fund."), ("They raised $2 billion last year from the fund.",
                                                  "They raised 2 billion last year from the fund.")):
            with self.subTest(run=run_t):
                new, rec = self.settle(run_t, pin_t, "nothing heard")
                self.assertEqual(new["text"], run_t)                   # nothing to adjudicate: the decode stands
                self.assertNotIn("adjudication", new)
                self.assertEqual(len(new["currency_format"]), 1)
                self.assertEqual(rec.calls, [])                        # nobody asked, nothing spent
                self.assertEqual(L.verify_lock(new), [])

    def test_the_currency_symbol_never_hides_a_number(self):                # ruling 143 (3): corrected from
        new, _ = self.settle("They raised 3 billion last year from the fund.",            # the audio when both
                             "They raised $2 billion last year from the fund.",            # audio readings agree
                             "They raised 3 billion last year from the fund.")
        self.assertEqual(new["text"], "They raised 3 billion last year from the fund.")
        self.assertEqual(len(new["transcript_corrected"]), 1)
        with self.assertRaises(P.PinError) as e:                        # and holds when they disagree
            self.settle("They raised 3 billion last year from the fund.",
                        "They raised $2 billion last year from the fund.", "They raised 2 billion last year from the fund.")
        self.assertIn("ruling 143 (3)", str(e.exception))
    def test_currency_and_two_of_three_together(self):
        new, _ = self.settle("They raised 2 billion last year from the bank.",
                             "They raised $2 billion last year from the fund.",
                             "They raised 2 billion last year from the fund.")
        self.assertEqual(new["text"], "They raised $2 billion last year from the fund.")
        self.assertEqual(new["currency_format"], [["", "dollars"]])
        self.assertTrue(new["adjudication"]["rule"].startswith("ruling 143"))
class TestRuling135(unittest.TestCase):
    """RULING 135 (orchestrator 10:50 ET Nov 17) in the render's lock: a run / approved pair that is the same words under
    the comparison canon is dropped before any vote (recorded in spelling_only, nobody asked); the rest is unchanged.
    must-fail  today's DataDash hook (three spellings of iTrust Capital), 'kinda' / 'kind of', a filler only the decoder
               and the second recogniser hear right at the span's start (ruling 131 (A) held it inside 3 tokens)
    must-hold  a number, a name whose letters differ"""

    def settle(self, run_t, pin_t, sec_t):
        lock, w = _lock(run_t, pin_t)
        rec = _reads(sec_t)
        return P.adjudicate_lock(lock, "src.mp4", w, recognise=rec, log=lambda *_: None), rec

    def test_todays_datadash_hook_three_spellings_one_brand(self):
        run_t = "Q is itrust capital's way of offering predefined automated crypto strategies inside the same account."
        pin_t = "Q is I trust capital's way of offering predefined automated crypto strategies inside the same account."
        new, rec = self.settle(run_t, pin_t, "Q is iTrustCapital's way of offering predefined automated crypto "
                                             "strategies inside the same account.")
        self.assertEqual((new["text"], new["spelling_only"], rec.calls), (run_t, [["itrust", "i trust"]], []))
        self.assertNotIn("adjudication", new)
        self.assertEqual(L.verify_lock(new), [])

    def test_kinda_is_kind_of(self):
        run_t = "That framing is just kind of too simple for the market we have today."
        new, rec = self.settle(run_t, "That framing is just kinda too simple for the market we have today.", "x")
        self.assertEqual((new["spelling_only"], rec.calls), ([["kind of", "kinda"]], []))

    def test_a_filler_at_the_edge_is_not_a_word(self):
        run_t = "Um so we went to the bank and then we went home."
        new, rec = self.settle(run_t, "So we went to the bank and then we went home.", run_t)
        self.assertEqual((new["spelling_only"], rec.calls), ([["um", ""]], []))

    def test_a_number_or_a_differently_spelled_name_still_holds(self):
        for run_t, pin_t in (("It cost them 68,000 dollars in the end.", "It cost them 86,000 dollars in the end."),
                             ("Then I asked Saylor about it again.", "Then I asked Taylor about it again.")):
            with self.subTest(run=run_t), self.assertRaises(P.PinError):
                self.settle(run_t, pin_t, pin_t)


class TestRuling142(unittest.TestCase):
    """RULING 142 (2) (orchestrator 14:32 ET Nov 17): 'bitcoin' against "bitcoin's", a name with a possessive or plural
    ending, is a word-form pair like any other: ruling 131 (A)'s two of three decides it (the run's reading at least 3
    tokens from an edge) and the sealed text takes that reading; all three different still holds; a name whose letters
    differ still holds under law L-v 2 before any vote. must-fail on the code before batch 110 (it held them all)."""
    RUN = "They said that Bitcoin's network will keep running for a very long time."
    PIN = "They said that Bitcoin network will keep running for a very long time."
    settle = TestRuling131.settle

    def test_a_possessive_pair_takes_the_two_of_three_reading(self):
        new, _ = self.settle(self.RUN, self.PIN, self.RUN)           # the second recogniser hears the run's
        self.assertEqual(new["text"], self.RUN)
        self.assertEqual([(x["took"], x["agreed"]) for x in new["adjudication"]["pairs"]], [("run", ["run", "second"])])
        new, _ = self.settle(self.RUN, self.PIN, self.PIN)           # it hears the approved text's
        self.assertEqual(new["text"], self.PIN)
        new, _ = self.settle(self.PIN.replace("Bitcoin", "Bitcoins"), self.PIN, self.PIN)     # a plural ending too
        self.assertEqual(new["text"], self.PIN)

    def test_all_three_different_take_the_run_decode(self):                 # ruling 143 (2): word forms never
        new, _ = self.settle(self.RUN, self.PIN, self.RUN.replace("Bitcoin's", "Bitcoins"))   # hold (142 held them)
        self.assertEqual(new["text"], self.RUN)
        self.assertEqual(new["small_words_unsettled"], 1)
    def test_a_name_whose_letters_differ_holds_when_the_audio_readings_disagree(self):   # ruling 143 (3)
        with self.assertRaises(P.PinError) as e:
            self.settle(self.RUN.replace("Bitcoin's", "Ethereum's"), self.PIN, self.RUN)
        self.assertIn("ruling 143 (3)", str(e.exception))
        new, _ = self.settle(self.RUN.replace("Bitcoin's", "Ethereum's"), self.PIN,
                             self.RUN.replace("Bitcoin's", "Ethereum's"))   # both audio readings: corrected
        self.assertIn("Ethereum's", new["text"])
        self.assertEqual(len(new["transcript_corrected"]), 1)
class TestBatch112(unittest.TestCase):
    """Batch 112: the two re-judged spans of ruling 142, settled from their recorded readings (the run decode, the
    approved text, the second recogniser's, verbatim from the pre-check's 15:24 entries). must-fail on batch 110's code."""
    settle = TestRuling131.settle

    def test_yahoo_f0a51c45_settles_two_of_three(self):
        run_t = ("But if you're wondering why having decentralized money that's available 24 -7, 365, that has no CEO "
                 "and is mined by a decentralized network around the world, like Bitcoin, is important. Well, when you "
                 "want access to your money with Bitcoin, you have it.")
        pin_t = ("But, you know, if you're wondering why having decentralized money that's available 24 -7, 365, that has "
                 "no CEO in his mind by a decentralized network. around the world, like Bitcoin is important. Well, when "
                 "you want access to your money with Bitcoin, you have it.")
        sec_t = ("But, you know, if you're wondering why having decentralized money that's available 24/7/365, uh, that "
                 "has no CEO and is mined by a decentralized network around the world, like Bitcoin, is important, well, "
                 "when you want access to your money, with Bitcoin, you have it.")
        new, _ = self.settle(run_t, pin_t, sec_t)
        self.assertIn("you know", new["text"])
        self.assertIn("and is mined by", new["text"])
        self.assertEqual(sorted(x["took"] for x in new["adjudication"]["pairs"]), ["approved", "run"])

    def test_natalie_feb4b72f_contraction_is_decided_two_of_three(self):
        run_t = ("And that's not to say that it's bad. It's that self -custody Bitcoin is a responsibility. If I have a "
                 "gun, it's a responsibility. Sovereignty is a responsibility.")
        pin_t = run_t.replace("Bitcoin is", "Bitcoin's")
        new, _ = self.settle(run_t, pin_t, run_t)                    # the second recogniser hears 'Bitcoin is'
        self.assertEqual(new["text"], run_t)
        new, _ = self.settle(run_t, pin_t, pin_t)                    # it hears "Bitcoin's"
        self.assertEqual(new["text"], pin_t)


class TestRuling143(unittest.TestCase):
    """RULING 143 (orchestrator 15:55 ET Nov 17): ONE principle. (1) MATERIAL = a number, a negation, a name (letters
    differ after the canon), a ticker or a currency amount. (2) a non-material pair never holds: two of three, else the
    run decode's; more than 3 all-differing pairs in a clip are counted for ONE soft flag. (3) a material pair: the two
    AUDIO readings (run decode, second recogniser) agreeing against the transcript correct it (recorded); disagreeing,
    HOLD. (4) HARD: the second reading hearing under 85 % of the run's words (more than 3 missing): the wrong audio.
    must-fail on the code before batch 113."""
    settle = TestRuling131.settle

    def test_a_material_word_both_audio_readings_agree_on_corrects_the_transcript(self):
        run_t = "The fund raised 2.35 billion dollars this year from the bank."
        pin_t = "The fund raised 2.25 billion dollars this year from the bank."
        new, _ = self.settle(run_t, pin_t, run_t)
        self.assertEqual(new["text"], run_t)
        self.assertEqual(new["transcript_corrected"], [["2250000000", "2350000000"]])
        self.assertTrue(new["adjudication"]["rule"].startswith("ruling 143"))
        with self.assertRaises(P.PinError) as e:                       # the audio readings disagree: HOLD
            self.settle(run_t, pin_t, pin_t)
        self.assertIn("ruling 143 (3)", str(e.exception))

    def test_a_ticker_holds_unless_both_audio_readings_agree(self):    # 'i've' / 'IBIT'
        run_t = "So I've seen inflows into it every single day this week."
        pin_t = "So IBIT seen inflows into it every single day this week."
        with self.assertRaises(P.PinError):
            self.settle(run_t, pin_t, pin_t)                           # the second hears IBIT, the decode I've
        new, _ = self.settle(run_t, pin_t, run_t)                      # both hear I've: the transcript was wrong
        self.assertEqual(new["text"], run_t)
        self.assertEqual(len(new["transcript_corrected"]), 1)

    def test_fillers_of_any_length_never_hold(self):
        run_t = "Bitcoin is the hardest money we have ever had in our lives."
        for pin_t, sec_t in (("Bitcoin is, you know, the hardest money we have ever had in our lives.",
                              "Bitcoin is the hardest money we have ever had in our lives."),
                             ("Bitcoin is sort of like the hardest money we have ever had in our lives.",
                              "Bitcoin is kind of the hardest money we have ever had in our lives.")):
            with self.subTest(pin=pin_t):
                new, _ = self.settle(run_t, pin_t, sec_t)
                self.assertNotIn("transcript_corrected", new)

    def test_another_clips_audio_is_the_wrong_audio(self):
        run_t = "Bitcoin is the hardest money we have ever had in our lives and it keeps growing."
        pin_t = "Bitcoin is the hardest money we have ever had in our life and it keeps growing."
        with self.assertRaises(P.PinError) as e:
            self.settle(run_t, pin_t, "The weather today is cold and the roads are icy near the river bank.")
        self.assertIn("ruling 143 (4)", str(e.exception))

    def test_all_differing_small_words_are_counted_for_the_flag(self):   # a long span: 4 of 36 words is not the
        tail = " and then we all walked home together slowly along the quiet river road before the sun went down."
        run_t = "We went in the house and saw a dog by the gate near the old red barn" + tail      # wrong audio
        pin_t = "We went into the house and saw the dog at the gate by the old red barn" + tail
        sec_t = "We went unto the house and saw one dog past the gate near a old red barn" + tail
        new, _ = self.settle(run_t, pin_t, sec_t)
        self.assertEqual(new["text"], run_t)                              # all three differ: the run decode's
        self.assertEqual(new["small_words_unsettled"], 4)                 # in/into/unto, a/the/one, by/at/past,
        #                                                                   near/by ('near a' is no neighbour match)
