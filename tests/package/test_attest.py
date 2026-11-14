#!/usr/bin/env python3
"""RULING 67 (orchestrator 14:02 Nov 13): the attested-text re-seal (pipeline/attest.py, tests/package/reseal_attested.py).
The fixture is the pin the render held at 13:48 ET (ledger_20261113_183302, clip 3 mKNAcOFMYD4 words 32-73)."""
import copy
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import attest as AT  # noqa: E402
import package_pin  # noqa: E402
import reseal_attested as RA  # noqa: E402

PIN = os.path.join(HERE, "proof", "ledger_20261113_183302", "MOMENTS_PIN_LEDGER.json")
APPROVED = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the bank "
            "owns the money and they could just take it from me. And that's why we Bitcoin.")
RUN = ("my biggest fear is that i go to the bank and i punch in my code and the money's not there because the bank owns "
       "the money and they could just take it from me. and that's why that's why we bitcoin.")
SCRIBE = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there, 'cause the bank "
          "owns the money and they could just take it from me. And that's why, that's why we Bitcoin.")
ATTESTED = ("My biggest fear is that I go to the bank and I punch in my code and the money's not there because the bank "
            "owns the money and they could just take it from me. And that's why that's why we Bitcoin.")


class TestAttest(unittest.TestCase):
    def test_the_held_clip_is_the_carry_over_class(self):
        r, p, ops = AT.diff(RUN, APPROVED)
        self.assertEqual([[" ".join(r[a:b]), " ".join(p[c:d])] for _, a, b, c, d in ops],
                         [["in", "you"], ["that's why", ""]])            # the render's own diffs, verbatim
        self.assertEqual([AT.carry_class(r, p, o, (RUN, APPROVED)) for o in ops],
                         ["function word", "immediate repetition"])
        s = AT.canon.canon_tokens(SCRIBE)
        self.assertEqual([AT.reads(r, s, a, b) for _, a, b, c, d in ops], [True, True])    # reads the run decode
        self.assertEqual([AT.reads(p, s, c, d) for _, a, b, c, d in ops], [False, False])  # not the approved text
        self.assertEqual(AT.attested_text(APPROVED, RUN.split()), ATTESTED)
        self.assertEqual(AT.diff(RUN, ATTESTED)[2], [])                   # no ruling-17 difference is left

    def test_a_number_a_name_a_negation_or_a_content_word_is_never_carried(self):
        for run, pin in (("the money is there", "the money is not there"),          # a negation
                         ("i paid 3 coins", "i paid 2 coins"),                     # a number
                         ("the first block", "the second block"),                  # an ordinal
                         ("i punch in my card", "i punch in my code"),             # a content word
                         ("as I told Saylor today", "as I told him today"),        # a name (capitalised mid-sentence)
                         ("no no it is fine", "no it is fine")):                   # a repeated negation stays critical
            r, p, ops = AT.diff(run, pin)
            self.assertTrue(ops, (run, pin))
            self.assertIn(None, [AT.carry_class(r, p, o, (run, pin)) for o in ops], (run, pin))
        r, p, ops = AT.diff("we buy it we buy it now", "we buy it now")            # a repeated phrase: carried
        self.assertEqual([AT.carry_class(r, p, o, ("", "")) for o in ops], ["immediate repetition"])
        r, p, ops = AT.diff("and that's why that's why we", "and that's why so we")   # aligned as a REPLACE
        self.assertEqual([o[0] for o in ops], ["replace"])
        self.assertEqual([AT.carry_class(r, p, o, ("", "")) for o in ops], ["immediate repetition"])
        r, p, ops = AT.diff("and that's why that's why we", "and that's why bank we")   # its other side: content
        self.assertEqual([AT.carry_class(r, p, o, ("", "")) for o in ops], [None])

    def test_the_attested_text_is_a_minimal_edit_with_the_run_tokens(self):
        self.assertEqual(AT.attested_text("So it is, Mr. Big.", "so it was mr big".split()),
                         "So it was Mr. Big.")                           # the run's whole word replaces "is,"
        with self.assertRaises(ValueError):                                       # a difference inside a word
            AT.attested_text("a well-known fact", "a well made fact".split())
        self.assertEqual(AT.canon.canon_tokens(AT.attested_text(APPROVED, RUN.split())), AT.canon.canon_tokens(RUN))

    def test_a_line_quoting_the_changed_words_is_found(self):
        r, p, ops = AT.diff(RUN, APPROVED)
        self.assertEqual(AT.quotes(["i punch you my code, he says", "no single owner"], r, p, ops),
                         ["i punch you my code, he says"])
        self.assertEqual(AT.quotes(["No single owner controls the bitcoin network"], r, p, ops), [])



class TestClass84(unittest.TestCase):
    """RULING 84 (orchestrator 20:41 Nov 13): the pre-check's class, as the integrator applies it, on this side's
    comparison (the spoken text against the approved text)."""

    def k(self, spoken, approved):
        return [(x["spoken"], x["approved"], x["class"]) for x in AT.class_84(spoken, approved)]

    def test_fillers_on_the_spoken_side_and_one_function_word(self):
        self.assertEqual(self.k("So over time, um, I came to think, uh, or the", "So over time, I came to think, so the"),
                         [("um", "", "filler"), ("uh", "", "filler"), ("or", "so", "one function word")])
        self.assertEqual(self.k("hmm mm er ah uh um yes", "yes"),
                         [(f, "", "filler") for f in ("hmm", "mm", "er", "ah", "uh", "um")])
        self.assertEqual(self.k("Um, the", "the"), [("um", "", "filler")])         # capitalised, still not a name
        self.assertEqual(self.k("came um came to", "came to"),                      # the repetition, filler-free
                         [("um", "", "filler"), ("came", "", "immediate repetition")])
        self.assertEqual(self.k("I think the Bitcoin", "I think Bitcoin"), [("the", "", "function word")])
        self.assertEqual(self.k("the same", "the same"), [])
        self.assertEqual(self.k("so, um, yes", "so um yes"), [])                  # a filler both sides heard stays
        self.assertEqual(self.k("so, um, the", "so um a"), [("the", "a", "one function word")])   # (audit 2048 glm)

    def test_what_holds(self):
        self.assertEqual(self.k("in the house on it", "on the house in it"),        # a second 1-for-1 holds
                         [("in", "on", "one function word"), ("on", "in", None)])
        self.assertEqual(self.k("we went to the store", "we went to a shop"), [("the store", "a shop", None)])
        self.assertEqual(self.k("went in a store", "went to the store"), [("in a", "to the", None)])   # 2-for-2
        self.assertEqual(self.k("the", "the um"), [("", "um", None)])              # a filler on the approved side
        self.assertEqual(self.k("I paid 5 dollars", "I paid 6 dollars"), [("5", "6", None)])
        self.assertEqual(self.k("it is not", "it is"), [("not", "", None)])
        self.assertEqual(self.k("um I asked Mike", "I asked mike"), [("um", "", "filler")])   # canon: the same name

    def test_ruling_67s_class_is_unchanged(self):
        r, p, ops = AT.diff("so um I came", "so I came")
        self.assertEqual([AT.carry_class(r, p, o, ("so um I came", "so I came")) for o in ops], [None])
        self.assertEqual(AT.FILLERS, frozenset({"um", "uh", "er", "ah", "mm", "hmm"}))


class TestReseal(unittest.TestCase):
    """reseal() on the pin the render held, with its run's records rebuilt in a temporary directory."""

    def setUp(self):
        with open(PIN) as f:
            self.pin = json.load(f)
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.frozen = os.path.join(d, "MOMENTS_PIN_LEDGER_183302.json")
        with open(self.frozen, "w") as f:
            json.dump(self.pin, f)
        os.makedirs(os.path.join(d, "transcripts"))
        with open(os.path.join(d, "PROVENANCE.json"), "w") as f:
            json.dump({"x": {"owner": f"pulse_check_run 1 (--pinned {self.frozen})"}}, f)
        with open(os.path.join(d, "transcripts", "mKNAcOFMYD4.json"), "w") as f:
            json.dump({"words": [{"word": "x"}] * 32 + [{"word": " " + w} for w in RUN.split()]}, f)
        self.hold("the run decode")
        seg = self.pin["segments"][2]
        self.rec = {"tried": [{"attempts": [{"second_pass": {"c3": {
            "video_id": "mKNAcOFMYD4", "start": seg["start"], "end": seg["end"], "model": "elevenlabs_stt:scribe_v1",
            "replayed": False, "second_pass_text": SCRIBE}}}]}]}

    def tearDown(self):
        self.tmp.cleanup()

    def hold(self, side):
        with open(os.path.join(self.tmp.name, "status.json"), "w") as f:
            json.dump({"holds": [f"pinned: pinned decision rejected: mKNAcOFMYD4 words 32-{32 + len(RUN.split()) - 1}"
                                 f": lock text not adjudicated (ruling 17): at [['in', 'you']] the second recogniser "
                                 f"reads {side} | run_decode: '...'"]}, f)

    def test_the_held_pin_is_re_sealed_with_the_attested_text(self):
        out, summary = RA.reseal(self.pin, self.tmp.name, self.rec, "tests/package/proof/ledger_x")
        seg, mp = out["segments"][2], out["moments_package"]
        self.assertEqual(seg["approved_text"], ATTESTED)
        self.assertEqual(seg["attested"]["was"], APPROVED)
        self.assertEqual([(x["run"], x["approved"], x["class"]) for x in seg["attested"]["differences"]],
                         [("in", "you", "function word"), ("that's why", "", "immediate repetition")])
        sha = package_pin.seal(out["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
                               mp["gates"], mp.get("btc_screen"))
        self.assertEqual((mp["package_sha256"], out["story_id"]), (sha, "moments-ledger_20261113_183302-" + sha[:8]))
        self.assertNotEqual(sha, self.pin["moments_package"]["package_sha256"])
        self.assertEqual(mp["resealed"]["package_sha256"], self.pin["moments_package"]["package_sha256"])
        segs = [{k: v for k, v in s.items() if k != "attested"} for s in out["segments"]]
        self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp.get("signoff_expected"), mp["title"],
                                             mp["caption"], mp["gates"], mp.get("btc_screen")), sha)   # sealed
        self.assertEqual([s["approved_text"] for i, s in enumerate(out["segments"]) if i != 2],
                         [s["approved_text"] for i, s in enumerate(self.pin["segments"]) if i != 2])   # one clip

    def test_it_refuses_without_both_recognisers_or_on_another_pin(self):
        self.hold("neither")                                               # the render's recogniser did not attest
        with self.assertRaises(ValueError):
            RA.reseal(self.pin, self.tmp.name, self.rec)
        self.hold("the run decode")
        rec = copy.deepcopy(self.rec)                                      # this side's recogniser reads the pin
        rec["tried"][0]["attempts"][0]["second_pass"]["c3"]["second_pass_text"] = APPROVED
        with self.assertRaises(ValueError):
            RA.reseal(self.pin, self.tmp.name, rec)
        rec["tried"][0]["attempts"][0]["second_pass"]["c3"].update(second_pass_text=SCRIBE, start=1.0)
        with self.assertRaises(ValueError) as e:                           # another span: named in the refusal
            RA.reseal(self.pin, self.tmp.name, rec)
        self.assertIn("its readings of mKNAcOFMYD4", str(e.exception))
        rec["tried"][0]["attempts"][0]["second_pass"]["c3"].update(start=self.pin["segments"][2]["start"] + 0.001)
        self.assertEqual(RA.reseal(self.pin, self.tmp.name, rec)[1]["text"], ATTESTED)   # 1 ms apart: the same
        rec["tried"][0]["attempts"][0]["second_pass"]["c3"].update(replayed=True)
        with self.assertRaises(ValueError):                                # a replayed reading is never evidence
            RA.reseal(self.pin, self.tmp.name, rec)
        other = copy.deepcopy(self.pin)
        other["moments_package"]["package_sha256"] = "0" * 64
        with open(self.frozen, "w") as f:
            json.dump(other, f)
        with self.assertRaises(ValueError):                                # the run rendered another pin
            RA.reseal(self.pin, self.tmp.name, self.rec)

    def test_it_refuses_a_difference_outside_the_carry_over_class(self):
        with open(os.path.join(self.tmp.name, "transcripts", "mKNAcOFMYD4.json"), "w") as f:
            json.dump({"words": [{"word": "x"}] * 32 + [{"word": w} for w in RUN.replace("code", "card").split()]}, f)
        with self.assertRaises(ValueError) as e:
            RA.reseal(self.pin, self.tmp.name, self.rec)
        self.assertIn("re-judged first", str(e.exception))


if __name__ == "__main__":
    unittest.main()
