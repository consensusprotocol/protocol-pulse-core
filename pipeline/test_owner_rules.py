#!/usr/bin/env python3
"""RULING 162 (orchestrator 07:45 ET Nov 24, from PBX's review of pin afd8977d at 07:37), both sides, one file
(pipeline/owner_rules.py, loaded read-only by the builder):
(1) out_edge(): the OUT edge's complete-thought question through the CALLER's router; an answer is read only from the
    JSON asked for; no answer (an exception of the caller's no_answer kinds, an unreadable reply) is measured False:
    UNVERIFIED (ruling 160 (2a)), never a pass and never a refusal; any other exception propagates.
(2) line_faults(): a line of ours that names a credited channel or says a listing phrase. Must-fail: afd8977d's own
    closing line 'Bitcoin, in the words of Simply Bitcoin, Digital Asset News and Yahoo Finance, in their own clips.'
No network: the router is a stub. Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_owner_rules.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import owner_rules as O  # noqa: E402

HOOK = "Stocks had fallen seven days in a row, Bitcoin was on its way to $55k, and everybody had the same story."
AFTER = ["The AI bubble had finally popped, and a full market crash was coming Monday morning.", "What a reversal.",
         "Now we covered Jensen Wang getting pushed out of Nvidia in this episode here."]
AFD_LINE = "Bitcoin, in the words of Simply Bitcoin, Digital Asset News and Yahoo Finance, in their own clips."


class Reply:
    def __init__(self, text, backend="heimdall:stub"):
        self.text, self.backend = text, backend


class Router:
    def __init__(self, text=None, exc=None):
        self.text, self.exc, self.calls = text, exc, []

    def call(self, role, prompt, max_tokens=2000, seed=7, **kw):
        self.calls.append({"role": role, "prompt": prompt, "max_tokens": max_tokens, "seed": seed, **kw})
        if self.exc is not None:
            raise self.exc
        return Reply(self.text)


class ProviderError(Exception):
    pass


class SpendStop(Exception):
    pass


class TestOutEdge(unittest.TestCase):
    def test_an_unfinished_thought_is_named_with_the_sentence_that_finishes_it(self):
        r = Router('Sure. {"complete": "no", "finishes_at": 0, "why": "the same story is told next"}')
        got = O.out_edge(r, HOOK, "Bitcoin popped right along with it.", AFTER, seed=11, avoid_vendor="xai")
        self.assertEqual({k: got[k] for k in ("complete", "finishes_at", "measured", "backend", "version")},
                         {"complete": False, "finishes_at": 0, "measured": True, "backend": "heimdall:stub",
                          "version": O.VERSION})
        self.assertEqual(got["why"], "the same story is told next")
        call = r.calls[0]
        self.assertEqual((call["role"], call["seed"], call["avoid_vendor"]), ("out_edge", 11, "xai"))
        for part in (HOOK, "Bitcoin popped right along with it.", "[0] " + AFTER[0], "[2] " + AFTER[2]):
            self.assertIn(part, call["prompt"])

    def test_a_finished_thought_has_no_finishing_sentence(self):
        for reply in ('{"complete": "yes", "finishes_at": 1, "why": "complete"}',
                      '{"complete": "Yes", "finishes_at": null, "why": "complete"}'):
            got = O.out_edge(Router(reply), HOOK, "", AFTER)
            self.assertEqual((got["complete"], got["finishes_at"], got["measured"]), (True, None, True), reply)

    def test_a_finishing_index_outside_the_sentences_given_is_none(self):
        for fin, want in (("2", 2), (3, None), (-1, None), (True, None), ("x", None), (1.0, 1), (1.5, None)):
            got = O.out_edge(Router('{"complete": "no", "finishes_at": %s, "why": "w"}' % (
                f'"{fin}"' if isinstance(fin, str) else str(fin).lower())), HOOK, "", AFTER)
            self.assertEqual((got["complete"], got["finishes_at"], got["measured"]), (False, want, True), fin)

    def test_no_answer_is_unverified_never_a_pass_or_a_refusal(self):
        for r in (Router(exc=ProviderError("every back-end unavailable")), Router("I think it is complete."),
                  Router('{"complete": "maybe"}'), Router('{"finishes_at": 0}'), Router("")):
            got = O.out_edge(r, HOOK, "", AFTER, no_answer=(ProviderError,))
            self.assertEqual((got["complete"], got["finishes_at"], got["measured"]), (None, None, False), got)
            self.assertTrue(got["why"].startswith(("no answer", "unreadable reply")), got["why"])

    def test_any_other_exception_propagates(self):
        with self.assertRaises(SpendStop):
            O.out_edge(Router(exc=SpendStop("$1.50 reached")), HOOK, "", AFTER, no_answer=(ProviderError,))
        with self.assertRaises(KeyboardInterrupt):                           # never swallowed, whatever no_answer is
            O.out_edge(Router(exc=KeyboardInterrupt()), HOOK, "", AFTER)

    def test_the_recording_ending_with_the_clip_is_said(self):
        r = Router('{"complete": "yes", "finishes_at": null, "why": "w"}')
        O.out_edge(r, HOOK, None, [" ", ""])
        self.assertIn("(none: the recording ends with the clip)", r.calls[0]["prompt"])
        self.assertIn("(the clip starts the recording)", r.calls[0]["prompt"])


class TestSentences(unittest.TestCase):
    def test_split_after_a_full_stop_question_or_exclamation(self):
        words = [{"word": w} for w in " The AI bubble had popped. What a reversal! Is it \"over?\" Now we".split()]
        self.assertEqual(O.sentences(words, 3), ["The AI bubble had popped.", "What a reversal!", 'Is it "over?"'])
        self.assertEqual(O.sentences(words, 9)[-1], "Now we")                 # the recording ends mid-sentence
        self.assertEqual(O.sentences(words, 2, forward=False), ['Is it "over?"', "Now we"])
        self.assertEqual(O.sentences([], 3), [])
        self.assertEqual(O.sentences(words, 0, forward=False), [])


class TestLineFaults(unittest.TestCase):
    NAMES = ["Simply Bitcoin", "Digital Asset News", "DAN", "Yahoo Finance"]

    def test_last_nights_closing_line_is_a_listing(self):
        self.assertEqual(O.line_faults(AFD_LINE, self.NAMES),
                         ["names 'Simply Bitcoin'", "names 'Digital Asset News'", "names 'Yahoo Finance'",
                          "says 'in the words of'", "says 'in their own clips'"])

    def test_each_phrase_and_name_form_is_caught(self):
        for text in ("As these clips show, the floor held.", "Three takes on one weekend.",
                     "In their words: the bottom is in.", "That is the market, in their own words."):
            self.assertTrue(O.line_faults(text, []), text)
        self.assertEqual(O.line_faults("YAHOO FINANCE's call aged well.", self.NAMES), ["names 'Yahoo Finance'"])
        self.assertEqual(O.line_faults("Finance at Yahoo is busy.", self.NAMES), [])        # not side by side, in order
        self.assertEqual(O.line_faults("Yahoo\u2019s finance desk", self.NAMES), [])     # a possessive INSIDE a name is
        self.assertEqual(O.line_faults("Natalie Brunell\u2019s point stands.", ["Natalie Brunell"]),   # not the name;
                         ["names 'Natalie Brunell'"])                                              # on its last word, it is
        self.assertEqual(O.line_faults("Dan was right.", self.NAMES), ["names 'DAN'"])

    def test_a_line_that_adds_value_passes(self):
        for text in ("The same four-year rhythm keeps showing up at the bottom: watch whether the wick holds.",
                     "A cycle low that lands on the day is a pattern, not proof."):
            self.assertEqual(O.line_faults(text, self.NAMES), [], text)


class TestMeaningPair(unittest.TestCase):
    """ITEM 7 (orchestrator 09:20 / 09:35 ET Nov 24): one list of meaning pairs, both sides."""

    def test_a_swap_of_meaning_is_a_pair_and_a_word_form_is_not(self):
        for x, y in ((["approved"], ["rejected"]), (["bought"], ["sold"]), (["million"], ["billion"]),
                     (["doubled"], ["halved"]), (["rose"], ["fell"]), (["up"], ["down"]), (["bullish"], ["bearish"]),
                     (["went", "higher"], ["went", "lower"]), (["inflows"], ["outflows"]), (["Approves."], ["denies"])):
            self.assertTrue(O.meaning_pair(x, y), (x, y))
            self.assertTrue(O.meaning_pair(y, x), (y, x))
        for x, y in ((["bottomed"], ["bottom"]), (["the", "rally"], ["a", "rally"]), (["Up"], ["up."]), (["a"], ["the"]),
                     (["approved"], ["approval"]), (["sold"], []), ([], [])):
            self.assertFalse(O.meaning_pair(x, y), (x, y))


class TestAnswerCache(unittest.TestCase):
    """The out-edge answer (orchestrator 09:45 ET Nov 24): cached against the exact transcript, cut coordinates and
    prompt version; a changed cut or transcript voids it; the replay serves frozen answers only; no answer is never
    stored (open work)."""

    def setUp(self):
        import tempfile
        import shutil
        self.d = tempfile.mkdtemp(prefix="out_edge_cache_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def test_an_answer_is_served_again_only_for_the_same_words_and_cut(self):
        coords = {"video_id": "0shaXx_n870", "i0": 48, "i1": 68, "cut_out": 21.169}
        r = Router('{"complete": "no", "finishes_at": 0, "why": "w"}')
        a = O.out_edge(r, HOOK, "", AFTER, cache_dir=self.d, coords=coords)
        b = O.out_edge(r, HOOK, "", AFTER, cache_dir=self.d, coords=coords)
        self.assertEqual((len(r.calls), a.get("cached"), b.get("cached"), a["key"]), (1, None, True, b["key"]))
        self.assertEqual((b["complete"], b["finishes_at"]), (False, 0))
        O.out_edge(r, HOOK, "", AFTER, cache_dir=self.d, coords=dict(coords, cut_out=21.4))     # another cut
        O.out_edge(r, HOOK + " The AI bubble", "", AFTER, cache_dir=self.d, coords=coords)     # another transcript
        self.assertEqual(len(r.calls), 3)

    def test_the_replay_serves_frozen_answers_only_and_no_answer_is_open_work(self):
        coords = {"video_id": "v", "i0": 1, "i1": 9}
        r = Router(exc=ProviderError("down"))
        got = O.out_edge(r, HOOK, "", AFTER, cache_dir=self.d, coords=coords, no_answer=(ProviderError,))
        self.assertEqual((got["measured"], len(os.listdir(self.d))), (False, 0))             # not stored
        r2 = Router('{"complete": "yes", "finishes_at": null, "why": "w"}')
        frozen = O.out_edge(r2, HOOK, "", AFTER, cache_dir=self.d, coords=coords, frozen=True)
        self.assertEqual((frozen["measured"], len(r2.calls)), (False, 0))                    # never asks
        self.assertIn("open work", frozen["why"])
        O.out_edge(r2, HOOK, "", AFTER, cache_dir=self.d, coords=coords)                     # recorded live once
        frozen = O.out_edge(Router(exc=AssertionError("asked")), HOOK, "", AFTER, cache_dir=self.d, coords=coords,
                            frozen=True)
        self.assertEqual((frozen["measured"], frozen["complete"], frozen["cached"]), (True, True, True))


if __name__ == "__main__":
    unittest.main()
