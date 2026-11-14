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
                     "So Bitcoin is down.", "They sold it all at the bottom.", "This is ultimately a bipartisan issue."):
            ok, why = S.opener("hook", text)                         # ruling 94: a third-person opener with no
            self.assertFalse(ok, (text, why))                        # verdict fails closed; conjunctions, replies too
        self.assertFalse(S.opener("hook", "Those folks that sold.", 3.0, "referent_outside", moments=True)[0])

    def test_hook_must_pass(self):
        for text in (DATADASH, "Michael Saylor is back. Strategy purchased 1 ,036 Bitcoin.",
                     "I don't check it on an hourly basis. It seemed to have bounced.",       # ruling 94 (b): first /
                     "We've seen Bitcoin lose 16 %.", "I will bet you one Bitcoin that it holds.",  # second person is
                     "You know, if you look at the chart, Bitcoin held.", "My view is simple: Bitcoin wins."):  # no fault
            self.assertTrue(S.opener("hook", text)[0], text)
        ok, why = S.opener("hook", "This is ultimately a bipartisan issue.", 4.0, "none", moments=True)
        self.assertTrue(ok, why)                                      # ruling 94 (b): third person, the scorer affirms
        self.assertIn("affirms", why)

    def test_ruling_94_check_edl_rates_a_third_person_hook(self):
        edl = {"hook": {"text": "This is ultimately a bipartisan issue for Bitcoin.", "channel": "BM", "duration": 9.0},
               "clips": []}
        asked = []

        def rate(passages):
            asked.extend(p["pid"] for p in passages)
            return {"hook": (4.0, "stands alone", "none")}
        out = S.check_edl(edl, rate=rate, moments=True)
        self.assertEqual((asked, out["rows"][0]["opener"]["pass"]), (["hook"], True))
        self.assertFalse(S.check_edl(edl, rate=None, moments=True)["rows"][0]["opener"]["pass"])   # no verdict
        first = {"hook": {"text": "I will bet you one Bitcoin that it holds.", "channel": "BM", "duration": 9.0},
                 "clips": []}
        asked.clear()
        self.assertTrue(S.check_edl(first, rate=rate, moments=True)["rows"][0]["opener"]["pass"])
        self.assertEqual(asked, [])                                  # a first-person hook asks nobody

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
        self.assertFalse(es._stand_alone_ok("hook", "They just had, of course, Binance with $6 .3 billion in hacks.", subj)[0])   # ruling 94: a third-person opener
        self.assertTrue(es._stand_alone_ok("hook", "Binance confirmed the hack this morning. It means six billion "
                                                   "dollars of customer money left the exchange.", subj)[0])
        self.assertFalse(es._stand_alone_ok("clip", RUN6_CLIP02, S.subject_terms("Bitcoin / US spot Bitcoin ETFs"))[0])


if __name__ == "__main__":
    unittest.main()


MINER_SCREEN = (r"\b(bitcoins?|btc|sats|satoshis?|halving|hash ?rate|lightning network|self[- ]custody|"
                r"cold storage|microstrategy|mstr|ibit|saylor)\b")       # pp-ingest pipeline/ingest/mine.py BTC_SCREEN


class TestRuling34(unittest.TestCase):
    """Ruling 34 (orchestrator 2026-11-13 '03:42'): for a moments package the TOPIC test per segment is the miner's
    about-Bitcoin screen carried on the pin; the MEDLEY names Bitcoin once at least; the story path is unchanged."""
    import re as _re
    SCREEN = _re.compile(MINER_SCREEN, _re.I)

    def edl(self, hook, *clips):
        return {"hook": {"text": hook, "channel": "A"},
                "clips": [{"index": i + 1, "text": t, "channel": f"C{i}"} for i, t in enumerate(clips)]}

    def test_a_clip_on_the_screen_passes_without_saying_bitcoin_when_the_medley_names_it(self):
        e = self.edl(DATADASH, "The halving cut the miners' reward in half, and the hash rate kept climbing.")
        r = S.check_edl(e, screen=self.SCREEN)
        self.assertTrue(r["ok"], r)
        self.assertIn("about Bitcoin by the miner's screen ('halving')", r["rows"][1]["topic"]["why"])
        self.assertEqual(r["medley_names_bitcoin"]["segments"], ["hook"])

    def test_a_clip_off_the_screen_still_fails(self):
        e = self.edl(DATADASH, "The stock market had its worst week since the spring.")
        r = S.check_edl(e, screen=self.SCREEN)
        self.assertFalse(r["ok"])
        self.assertFalse(r["rows"][1]["topic"]["pass"])

    def test_a_medley_that_never_says_bitcoin_fails(self):
        e = self.edl("The halving is the one schedule nobody can change.",
                     "Michael Saylor keeps buying, quarter after quarter.")
        r = S.check_edl(e, screen=self.SCREEN)
        self.assertTrue(all(row["pass"] for row in r["rows"]))              # every segment passes the screen
        self.assertFalse(r["ok"])                                            # but the medley never names Bitcoin
        self.assertEqual(r["medley_names_bitcoin"]["why"],
                         "no segment names Bitcoin in the speaker's own words (ruling 34)")

    def test_without_a_screen_every_segment_names_bitcoin_as_before(self):
        e = self.edl(DATADASH, "The halving cut the miners' reward in half, and the hash rate kept climbing.")
        r = S.check_edl(e)
        self.assertFalse(r["ok"])
        self.assertNotIn("medley_names_bitcoin", r)

    def test_the_opener_rule_is_unchanged_by_the_screen(self):
        e = self.edl(DATADASH, "But the halving cut the miners' reward in half.")
        r = S.check_edl(e, screen=self.SCREEN)                              # no scorer: a 'but' opener fails closed
        self.assertFalse(r["rows"][1]["opener"]["pass"])


class TestMomentsScreen(unittest.TestCase):
    """run_fresh.moments_screen: the carried screen only for a moments package bound to 'bitcoin'; anything else is
    None, so every segment must name Bitcoin (never looser)."""

    def bound(self, **extra):
        return {"moments_package_sha256": "a" * 64, "mode": "pinned", "topic": "bitcoin",
                "moments_checks": {"vo_fidelity_ok": True, "context_integrity_ok": True}, **extra}

    def test_the_screen_is_read_only_for_a_bound_moments_package(self):
        import run_fresh as rf
        sc, why = rf.moments_screen(self.bound(moments_btc_screen={"pattern": MINER_SCREEN, "source": "mine.py@x"}))
        self.assertTrue(sc.search("stack sats") and not sc.search("the nasdaq fell"))
        self.assertEqual(why, "the pin's btc_screen (mine.py@x)")
        for e in ({"topic": "bitcoin", "moments_btc_screen": {"pattern": MINER_SCREEN}},          # not a moments EDL
                  self.bound(topic="bitcoin cash", moments_btc_screen={"pattern": MINER_SCREEN}),  # not bound
                  self.bound(),                                                                    # no screen
                  self.bound(moments_btc_screen={"pattern": ""}),
                  self.bound(moments_btc_screen={"pattern": "x" * 501}),
                  self.bound(moments_btc_screen={"pattern": "(unclosed"}),
                  self.bound(moments_btc_screen="bitcoin")):
            with self.subTest(e=str(e)[:60]):
                self.assertIsNone(rf.moments_screen(e)[0])
