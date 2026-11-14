#!/usr/bin/env python3
"""Orchestrator 08:30 ET (direction 2): a segment must stand alone and belong to a Bitcoin story. Must-fail
fixtures are recut run 6's own segments (runs/pinned_20261111_123750): the hook "But I don't check it on an
hourly basis..." and clip_02 "And the NASDAQ fell even harder ... concentrated in AI."
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_stand_alone.py"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stand_alone as S  # noqa: E402

RUN6_HOOK = ("But I don't check it on an hourly basis. It seemed to have bounced very nicely at a very key level "
             "around $74 ,000, around the 50 -weekly MA, which we've talked about many times.")
RUN6_CLIP01 = ("But we've seen a really nice decline here on Bitcoin, okay? 16 % so far. And, you know, really just "
               "looking to see if we hold in this region, even if we don't get back towards these highs.")
RUN6_CLIP02 = ("And the NASDAQ fell even harder, dropping 5 .5%, pushing it into correction territory, which means it "
               "fell more than 10 % from its October high. And let's take a look at where the selling hit because it "
               "was concentrated in AI.")
DATADASH = ("Bitcoin has now seen a 16 % decline from the overall high from $88 ,000, touching down towards about "
            "$73 ,400, $500, give or take.")


class TestOpener(unittest.TestCase):
    def test_hook_must_fail(self):
        for text in (RUN6_HOOK, "It seemed to have bounced very nicely at $74,000.", "Yeah, Bitcoin is down 16 %.",
                     "So Bitcoin is down.", "They sold it all at the bottom."):
            ok, why = S.opener("hook", text)
            self.assertFalse(ok, (text, why))

    def test_hook_must_pass(self):
        for text in (DATADASH, "Michael Saylor is back. Strategy purchased 1 ,036 Bitcoin.",
                     "I don't check it on an hourly basis. It seemed to have bounced.",      # RULING 94 (b): first or
                     "We've seen Bitcoin lose 16 %.", "I will bet you one Bitcoin that it gets there."):   # second person
            self.assertTrue(S.opener("hook", text)[0], text)

    def test_ruling_94_a_third_person_hook_needs_the_scorer(self):
        text = "This is ultimately a bipartisan issue."
        self.assertFalse(S.opener("hook", text)[0])                                  # no verdict: fail closed
        self.assertTrue(S.opener("hook", text, 4.0, "none", moments=True)[0])
        self.assertFalse(S.opener("hook", text, 3.0, "none", moments=True)[0])
        self.assertEqual(S.PRONOUNS, S.FIRST_SECOND | S.THIRD)
        edl = {"hook": {"channel": "H", "text": text}, "clips": []}
        r = S.check_edl(edl, rate=lambda ps: {p["pid"]: (4.0, "r", "none") for p in ps}, moments=True)
        self.assertTrue(r["rows"][0]["opener"]["pass"], r["rows"][0])                # the hook is rated (check_edl)
        self.assertFalse(S.check_edl(edl, rate=None, moments=True)["rows"][0]["opener"]["pass"])

    def test_clip_conjunction_needs_the_scorer(self):
        self.assertTrue(S.opener("clip", RUN6_CLIP01, 5.0, "none")[0])
        self.assertFalse(S.opener("clip", RUN6_CLIP01, 3.0, "starts_mid_thought")[0])
        self.assertFalse(S.opener("clip", RUN6_CLIP01, 5.0, "starts_mid_thought")[0])
        self.assertFalse(S.opener("clip", RUN6_CLIP01, None, None)[0])          # no verdict: fail closed
        self.assertTrue(S.opener("clip", "It went from above $81 ,000 after the election.")[0])   # topic decides


class TestTopic(unittest.TestCase):
    def test_nasdaq_statement_is_context_not_a_clip(self):
        ok, why = S.topical("clip", RUN6_CLIP02, prev_text=RUN6_CLIP01)
        self.assertFalse(ok, why)

    def test_subject_of_a_non_bitcoin_story_counts(self):
        """Nov 4's approved Binance-hack video: its segments name Binance / the exchange, not Bitcoin."""
        subj = S.subject_terms("Binance exchange", "Binance hacked for six billion dollars")
        self.assertEqual(subj, {"binance", "exchange"})
        self.assertTrue(S.topical("clip", "The exchange says withdrawals resume in 48 hours.", subject=subj)[0])
        self.assertFalse(S.topical("clip", "The NASDAQ fell 5.5 % on Thursday.", subject=subj)[0])
        self.assertFalse(S.topical("clip", "Bitcoin is sitting at 77,000 today.", subject=subj)[0])   # an aside
        self.assertEqual(S.subject_terms("Bitcoin / US spot Bitcoin ETFs"), {"bitcoin", "btc"})
        self.assertEqual(S.subject_terms("", "Binance hacked for six billion dollars"),
                         {"binance", "hacked", "dollars"})     # headline words, no Bitcoin; 'six billion' is one
                                                               # canonical value (canon.py) and values never count
        self.assertEqual(S.subject_terms("AI", "AI"), set())                        # nothing usable: fail closed
        self.assertFalse(S.topical("clip", "Bitcoin is sitting at 77,000 today.", subject=set())[0])

    def test_bitcoin_segments_and_completions(self):
        self.assertTrue(S.topical("hook", DATADASH)[0])
        self.assertFalse(S.topical("hook", "The NASDAQ fell 5.5 % on Thursday.")[0])
        it = "It went from above $81 ,000 after the election to below $75 ,000 by the weekend."
        self.assertTrue(S.topical("clip", it, prev_text="Bitcoin also wasn't spared in the sell -off.")[0])
        self.assertFalse(S.topical("clip", it, prev_text="The S &P 500 rallied 1 .6 % on Wednesday.")[0])
        self.assertFalse(S.topical("clip", "It was a strange week for everyone.", prev_text=DATADASH)[0])  # no figure
        self.assertTrue(S.topical("clip", "And it touched $73 ,400 on Sunday.", prev_text=DATADASH)[0])


class TestEDL(unittest.TestCase):
    def edl(self, hook, *clips):
        return {"hook": {"channel": "H", "text": hook},
                "clips": [{"index": i + 1, "channel": f"C{i}", "text": t, "duration": 15.0} for i, t in enumerate(clips)]}

    def test_run6_lineup_fails_on_the_hook_and_clip_02(self):
        calls = []

        def rate(passages):
            calls.append([p["pid"] for p in passages])
            return {p["pid"]: (5.0, "fake", "none") for p in passages}
        r = S.check_edl(self.edl(RUN6_HOOK, RUN6_CLIP01, RUN6_CLIP02), rate=rate)
        self.assertFalse(r["ok"])
        self.assertEqual({x["segment"]: x["pass"] for x in r["rows"]}, {"hook": False, "clip_01": True, "clip_02": False})
        self.assertEqual(calls, [["clip_01", "clip_02"]])                  # the scorer only for conjunction openers

    def test_a_clean_lineup_passes_and_an_unavailable_scorer_fails_closed(self):
        lineup = self.edl(DATADASH, "It went from above $81 ,000 after the election to below $75 ,000 by the weekend.",
                          RUN6_CLIP01)
        self.assertTrue(S.check_edl(lineup, rate=lambda ps: {p["pid"]: (4.0, "fake", "none") for p in ps})["ok"])
        r = S.check_edl(lineup, rate=lambda ps: (_ for _ in ()).throw(RuntimeError("no GPU")))
        self.assertFalse(r["ok"])
        self.assertIn("RuntimeError", r["rate_error"])


class TestAutoSelectionScreen(unittest.TestCase):
    """editorial_select applies the same screen to the final (scored, repaired) windows: a pronoun-opening
    hook is ineligible, its D3 repair (the previous sentence prepended) is eligible."""

    def test_selection_uses_the_same_rule(self):
        import editorial_select as es
        subj = S.subject_terms("Binance exchange", "Binance hacked for six billion dollars")
        self.assertFalse(es._stand_alone_ok("hook", "They just had, of course, Binance with $6 .3 billion in hacks.",
                                            subj)[0])                # ruling 94 (b): a third-person opener, no verdict
        self.assertTrue(es._stand_alone_ok("hook", "Binance confirmed the hack this morning. It means six billion "
                                                   "dollars of customer money left the exchange.", subj)[0])
        self.assertFalse(es._stand_alone_ok("clip", RUN6_CLIP02, S.subject_terms("Bitcoin / US spot Bitcoin ETFs"))[0])


if __name__ == "__main__":
    unittest.main()
