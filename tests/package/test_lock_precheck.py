#!/usr/bin/env python3
"""RULINGS 68 / 72 (orchestrator 14:02 Nov 13; live on the integrator's side 17:17 Nov 13): the render's own ruling-17
lock, asked before a line-up is written and before its pin is sealed (pipeline/lock_precheck.py). Offline: the
requests and results directories are temporary, the clock and the sleep are the test's."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import attest as AT  # noqa: E402
import canon as C  # noqa: E402
import lock_precheck as LP  # noqa: E402

HOOK = {"moment_id": "h", "video_id": "DcUbBkyeh9M", "start": 216.0541, "end": 228.6739,
        "text": "Bitcoin launched in January of 2009. It's never been renamed."}
CLIP = {"moment_id": "x", "video_id": "MqVqfEDXgLo", "start": 937.971, "end": 957.291,
        "text": "I think Bitcoin only dropped like 5, 6%."}
TRIM = dict(CLIP, moment_id="t", video_id="HWuMai_mAug", start=1691.139, end=1698.069, trimmed_leading="And",
            untrimmed_start=1690.9, text="treasury companies will also bleed to Bitcoin.")


def entry(seg, outcome="no_difference", at="2026-11-13T22:30:00Z", rid="r1", **kw):
    e = {"rules": LP.RULES, "request_id": rid, "video_id": seg["video_id"], "start": seg["start"], "end": seg["end"],
         "window": [seg["start"], seg["end"]], "role": seg["role"], "approved_text": seg["approved_text"],
         "trimmed_leading": seg.get("trimmed_leading"), "untrimmed_start": seg.get("untrimmed_start"),
         "outcome": outcome, "reason": None, "lock": {"sha256": "ab" * 32}, "at": at}
    e.update(kw)
    return e


class Dirs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.req, self.res = os.path.join(self.tmp.name, "req"), os.path.join(self.tmp.name, "res")
        os.makedirs(self.res)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, seg, *entries):
        p = LP.result_file(seg, self.res)
        old = []
        if os.path.exists(p):
            with open(p) as f:
                old = json.load(f)
        with open(p, "w") as f:
            json.dump(old + list(entries), f)


class TestRequest(Dirs):
    def test_the_segments_are_the_pins_own(self):
        s = LP.segments_of([HOOK, CLIP, TRIM])
        self.assertEqual([x["role"] for x in s], ["hook", "clip", "clip"])
        self.assertEqual((s[0]["start"], s[0]["end"]), (216.054, 228.674))              # to the millisecond
        self.assertEqual(s[0]["approved_text"], HOOK["text"])
        self.assertNotIn("trimmed_leading", s[1])                                        # only a trimmed moment
        self.assertEqual((s[2]["trimmed_leading"], s[2]["untrimmed_start"]), ("And", 1690.9))
        self.assertEqual(os.path.basename(LP.result_file(s[0], self.res)),
                         "DcUbBkyeh9M.216.054-228.674.fe809cb4e680.json")             # ruling 142's decoder

    def test_a_request_is_renamed_from_its_tmp_and_never_written_over(self):
        segs = LP.segments_of([HOOK, CLIP])
        p = LP.send(segs, "pp-selectid.ledger_x.1", self.req)
        self.assertEqual(os.listdir(self.req), ["pp-selectid.ledger_x.1.json"])           # no .tmp left
        with open(p) as f:
            self.assertEqual(json.load(f), {"request_id": "pp-selectid.ledger_x.1", "segments": segs})
        with self.assertRaises(FileExistsError):
            LP.send(segs, "pp-selectid.ledger_x.1", self.req)
        for bad in ("", "a b", "x" * 121, "../x"):
            with self.assertRaises(ValueError):
                LP.send(segs, bad, self.req)


class TestAnswer(Dirs):
    def test_the_newest_matching_entry_of_ruling_72_and_only_it(self):
        s = LP.segments_of([HOOK])[0]
        self.put(s, entry(s, "hold", at="2026-11-13T22:00:00Z"), entry(s, "no_difference", at="2026-11-13T22:05:00Z"),
                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), rules=None),        # ruling 68's: never read
                 entry(dict(s, approved_text="other words"), "adopted", at="2026-11-13T23:00:00Z"),
                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), window=[216.0, 228.674]),
                 dict(entry(s, "adopted", at="2026-11-13T23:00:00Z"), role="clip"))
        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")
        self.put(s, dict(entry(s, "adopted", at="2026-11-14T01:00:00Z"), rules="ruling 17 + ruling 72"))   # before
        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")              # ruling 73: never read
        self.put(s, entry(s, "hold", at="2026-11-13T22:05:00Z", rid="r2"))                 # same time: the later one
        self.assertEqual(LP.answer(s, self.res)["outcome"], "hold")
        self.assertEqual(LP.answer(s, self.res, request_id="r1")["outcome"], "no_difference")
        self.assertIsNone(LP.answer(s, self.res, request_id="r9"))
        t = LP.segments_of([TRIM])[0]
        self.put(t, dict(entry(t), untrimmed_start=1690.0))                               # the trim must match
        self.assertIsNone(LP.answer(t, self.res))
        with open(LP.result_file(LP.segments_of([CLIP])[0], self.res), "w") as f:
            f.write("{not json")
        self.assertIsNone(LP.answer(LP.segments_of([CLIP])[0], self.res))                  # unreadable: no answer


class TestDecide(unittest.TestCase):
    s = LP.segments_of([CLIP])[0]

    def test_the_outcomes(self):
        for out in ("no_difference", "adopted", "two_readings"):
            self.assertEqual(LP.decide(self.s, entry(self.s, out))["verdict"], "pass")
        self.assertEqual(LP.decide(self.s, entry(self.s, "hold", reason="ruling 72: at ['x']"))["why"],
                         "ruling 72: at ['x']")
        for e in (None, entry(self.s, "error"), entry(self.s, "decoded"), entry(self.s, "adopt_spoken"),
                  entry(self.s, "adopt_spoken", spoken_text="  ")):
            self.assertEqual(LP.decide(self.s, e)["verdict"], "error", e and e.get("outcome"))

    def test_adopt_spoken_only_inside_ruling_67s_class_by_this_sides_check(self):
        rep = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="I think I think Bitcoin only dropped like "
                                                                          "5, 6%."))
        self.assertEqual((rep["verdict"], rep["differences"][0]["class"]), ("adopt", "immediate repetition"))
        fw = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="I think the Bitcoin only dropped like 5, 6%."))
        self.assertEqual(fw["verdict"], "adopt")
        for spoken in ("I think Bitcoin only dropped like 7, 6%.", "I think Ethereum only dropped like 5, 6%.",
                       "I think Bitcoin never dropped like 5, 6%."):                      # a number, a name, a negation
            d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
            self.assertEqual(d["verdict"], "hold", spoken)
            self.assertIn("outside ruling 84's class", d["why"])
        same = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text="i think bitcoin only dropped like 5 6%"))
        self.assertEqual(same["verdict"], "pass")                                          # no canonical difference



class TestRuling84(unittest.TestCase):
    """RULING 84 (orchestrator 20:41 Nov 13): fillers the second recogniser hears adopt; ONE 1-for-1 function word
    adopts (the render's lock keeps its decode's word and records the other reading); two hold; any other
    substitution holds. The 20:12 build's held span: [['', 'um'], ['', 'uh'], ['so', 'or']]."""
    BREEDLOVE = {"moment_id": "b", "video_id": "uaHNzi-Kgr8", "start": 100.0, "end": 112.6,
                 "text": "So over time, I came to think so the money itself was broken."}
    s = LP.segments_of([BREEDLOVE])[0]

    def test_the_rules_string_is_the_integrators(self):
        """RULING 103 (14:12 Nov 14), RULING 105 (20:13 Nov 14), RULING 131 (08:25 Nov 17), RULING 135 (10:50 Nov 17) and
        RULING 142 (14:32 Nov 17) joined the integrator's rules string (its batch 110 values, 14:5x ET Nov 17)."""
        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103 + ruling 105 + "
                                   "ruling 131 + ruling 135 + ruling 142")

    def test_the_held_span_of_the_20_12_build_now_adopts(self):
        spoken = "So over time, um, I came to think, uh, or the money itself was broken."
        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
        self.assertEqual(d["verdict"], "adopt")
        self.assertEqual([(x["spoken"], x["approved"], x["class"]) for x in d["differences"]],
                         [("um", "", "filler"), ("uh", "", "filler"), ("or", "so", "one function word")])
        row = dict(self.s, **d, entry={"request_id": "r1"})
        self.assertIn("ruling 84", LP.attested(row)["rule"])
        self.assertIn("ruling 84's class", LP.attested(row)["carried"])

    def test_what_still_holds(self):
        for spoken in ("So over time, I came to think or the money itself is broken.",    # two 1-for-1 function words
                       "So over time, I came to think in a the money itself was broken.", # a 1-for-2 substitution
                       "So over time, I came to believe so the money itself was broken.", # a content word
                       "So over time, I came to think so the money itself was not broken.",   # a negation
                       "So over time, I came to think so the money itself was broken 2."):    # a number
            d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken))
            self.assertEqual(d["verdict"], "hold", spoken)
            self.assertIn("outside ruling 84's class", d["why"])
        e = entry(self.s, "adopt_spoken", spoken_text="So over time, I came to think so the money itself was broken.")
        e["approved_text"] = "So over time, um, I came to think so the money itself was broken."
        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone: since
        self.assertEqual(LP.decide(s2, e)["verdict"], "adopt")             # RULING 135 (d) no difference wherever it sits


class TestRuling131(Dirs):
    """RULING 131 (orchestrator 08:25 ET Nov 17). (A): per differing pair of the render's lock, two of the three readings
    (the approved text, the run's decode, the second recogniser) decide it and the sealed text takes that reading, at
    least 3 tokens from both cut edges; never a number, a name or a negation; all three different holds. (B): currency
    format is no difference. The render's lock records it (the integrator's message of 08:2x Nov 17); this side
    re-derives every pair from the three readings (attest.class_131). Last night's held span: What Bitcoin Did d6adeb54
    (WdiF0i925rs 3339.900-3354.680), its three readings as the pre-check recorded them at 03:46:30Z Nov 17."""
    RUN = ("i have been recently done a bunch of pieces on the 2023 bull market, that climbing a wall of worry. um there "
           "was massive amounts of fear during that period of time. bitcoin was actually trending up into the right, "
           "and fear was also trending up into the right during that.")
    APPROVED = ("I have been recently done a budget pieces on the 2023 bull market, like climbing a wall of worry. There "
                "was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
                "right, and fear was also trending up into the right during that.")
    SECOND = ("comes next? I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a "
              "wall of worry. Um, there was massive amounts of fear during that period of time. Bitcoin was actually "
              "trending up into the right, and fear was also trending up into the right during that,")
    MERGED = ("I have been recently done a bunch of pieces on the 2023 bull market, like climbing a wall of worry. There "
              "was massive amounts of fear during that period of time. Bitcoin was actually trending up into the "
              "right, and fear was also trending up into the right during that.")   # RULING 135: 'um' is no word, the
    SPOKEN = MERGED                     # approved words stay there; ruling 72's 'uh' and 'Um' are no difference either
    HEARD = ("I have been, recently done a bunch of pieces on the 2023, uh, bull market, like climbing a wall of worry. "
             "Um, there was massive amounts of fear during that period of time. Bitcoin was actually trending up into "
             "the right, and fear was also trending up into the right during that,")   # the second reading, trimmed
    PAIRS = [{"run": "bunch of", "approved": "budget", "second_reads": "run", "took": "run",
              "agreed": ["run", "second"], "edge_distance": 6},
             {"run": "that", "approved": "like", "second_reads": "approved", "took": "approved",
              "agreed": ["approved", "second"], "edge_distance": 14}]          # 'um' / '': spelling only (ruling 135)
    WBD = {"moment_id": "w", "video_id": "WdiF0i925rs", "start": 3339.9, "end": 3354.68, "text": APPROVED}

    def adj(self, **kw):
        return dict({"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "verdict": "approved",
                     "pairs": self.PAIRS, "recogniser": "elevenlabs:scribe_v1", "usd": 0.0, "run_decode": self.RUN,
                     "approved": self.APPROVED, "second_recogniser": self.SECOND}, **kw)

    def decide(self, spoken=None, **kw):
        s = LP.segments_of([self.WBD])[0]
        return LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken or self.MERGED, adjudication=self.adj(**kw)))

    def test_last_nights_held_span_now_adopts_and_is_sealed_with_its_record(self):
        d = self.decide()                                          # the merged text as it stands ("same")
        self.assertEqual(d["verdict"], "adopt", d.get("why"))
        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in d["differences"]],
                         [("bunch of", "budget", "run"), ("that", "like", "approved"), ("um", "", "spelling")])
        d = self.decide(self.HEARD)                                # the second reading itself: only no-words differ
        self.assertEqual(d["verdict"], "adopt", d.get("why"))
        self.assertTrue(d["differences"][3:] and {x["class"] for x in d["differences"][3:]} <=
                        {"filler", "spelling only (ruling 135)"}, d["differences"][3:])   # no word differs
        s = LP.segments_of([self.WBD])[0]
        self.put(s, entry(s, "adopt_spoken", spoken_text=self.SPOKEN, adjudication=self.adj()))
        pre = LP.check([self.WBD], "r", self.req, self.res, log=lambda m: None)
        pk = LP.apply({"segments": [{k: self.WBD[k] for k in ("video_id", "start", "end", "text")}], "lines": []}, pre)
        seg = pk["segments"][0]
        self.assertEqual((seg["text"], seg["attested"]["was"]), (self.SPOKEN, self.APPROVED))
        self.assertIn("ruling 131 (A)", seg["attested"]["rule"])
        self.assertIn("two of the three readings", seg["attested"]["carried"])
        self.assertEqual(LP.pin_problems(pk), [])

    def test_this_side_rederives_every_pair_and_never_trusts_the_record(self):
        lie = [dict(self.PAIRS[0]), dict(self.PAIRS[1], took="run", agreed=["run", "second"])]
        for spoken, kw, why in (
                (self.MERGED.replace("like climbing", "that climbing"), {"pairs": lie},   # the second reads 'like'
                 "the lock record's pairs are not this side's"),
                (self.MERGED, {"pairs": self.PAIRS[:1]}, "the lock record's pairs are not this side's"),
                (self.MERGED, {"pairs": [dict(p, edge_distance=9) for p in self.PAIRS]},
                 "the lock record's pairs are not this side's"),
                (self.MERGED.replace("bunch of", "budget"), {}, "neither the merged reading nor"),
                (self.MERGED.replace("massive", "huge"), {}, "neither the merged reading nor"),
                (self.MERGED.replace("climbing", "the climbing"), {}, "neither the merged reading nor"),
                (self.HEARD.replace("massive", "huge"), {"second_recogniser": self.SECOND.replace("massive", "huge")},
                 "outside ruling 84's class"),                                     # the second recogniser alone
                (self.MERGED, {"second_recogniser": None}, "does not hold the three readings"),
                (self.MERGED, {"approved": self.MERGED}, "does not hold the three readings")):
            d = self.decide(spoken, **kw)
            self.assertEqual(d["verdict"], "hold", (spoken, kw))
            self.assertIn(why, d["why"])

    def test_what_still_holds(self):
        for kw, why in (
                ({"second_recogniser": self.SECOND.replace("bunch of", "lunch of")}, "all three readings differ"),
                ({"run_decode": self.RUN.replace("have been", "have seen"),               # the 3rd token: 2 from the
                  "second_recogniser": self.SECOND.replace("have been", "have seen")},     # edge
                 "within 3 tokens of a cut edge"),
                ({"run_decode": self.RUN.replace("2023", "2024"),
                  "second_recogniser": self.SECOND.replace("2023", "2024")}, "a number, a name or a negation"),
                ({"run_decode": self.RUN.replace("there was", "there wasn't"),
                  "second_recogniser": self.SECOND.replace("there was", "there wasn't")},
                 "a number, a name or a negation"),
                ({"run_decode": self.RUN.replace("bunch of", "Saylor"),
                  "second_recogniser": self.SECOND.replace("bunch of", "Saylor")}, "a number, a name or a negation")):
            d = self.decide(**kw)
            self.assertEqual(d["verdict"], "hold", kw)
            self.assertIn(why, d["why"])

    def test_currency_format_is_no_difference(self):
        """BTC Sessions 93cfa865 (2oY7TU6CPok 54.260-61.380), the line-up's second hold: the approved '$2 billion',
        '$645 million'; the run's decode and the second recogniser say no 'dollars' (the pre-check at 03:46:32Z)."""
        app = ("Meanwhile, Bitcoin had a terrible weekend. We went all the way down to 62K, $2 billion in leverage wiped "
               "out, $645 million in just 30 minutes.")
        adj = self.adj(pairs=[], run_decode="meanwhile, bitcoin had a terrible weekend. we went all the way down to "
                                            "62k, 2 billion in leverage wiped out, 645 million in just 30 minutes.",
                       approved=app, second_recogniser="emerging. Meanwhile, Bitcoin had a terrible weekend. We went "
                       "all the way down to 62K, two billion in leverage wiped out, 645 million in just 30 minutes.")
        s = LP.segments_of([{"video_id": "2oY7TU6CPok", "start": 54.26, "end": 61.38, "text": app}])[0]
        rows = AT.class_131(app, app, adj)
        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in rows],
                         [("", "dollars", "currency"), ("", "dollars", "currency")])
        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")
        self.assertTrue(AT.currency_pair(["2000000000", "dollars"], ["2000000000"], ("delete", 1, 2, 1, 1)))
        self.assertTrue(AT.currency_pair(["2000000000"], ["2000000000", "dollars"], ("insert", 1, 1, 1, 2)))
        self.assertFalse(AT.currency_pair(["many", "dollars"], ["many"], ("delete", 1, 2, 1, 1)))   # no number before
        self.assertFalse(AT.currency_pair(["5", "dollars", "dollars"], ["5", "dollars"], ("delete", 2, 3, 2, 2)))
        self.assertFalse(AT.currency_pair(["5", "euros"], ["5", "dollars"], ("replace", 1, 2, 1, 2)))
        self.assertFalse(AT.currency_pair(["5", "dollars"], ["5", "euros"], ("replace", 1, 2, 1, 2)))

    def test_a_repetition_slides_to_its_furthest_placement(self):
        """mKNAcOFMYD4 755.454-764.214, held Nov 13 (its real readings): difflib puts the extra "that's why" on the
        second copy, 2 tokens from the end; the first copy gives the same two texts and is 4 from it (the integrator's
        message of 08:4x Nov 17). A spoken text that reverts the vote holds, though it is in ruling 84's class."""
        run = ("my biggest fear is that i go to the bank and i punch in my code and the money's not there because the "
               "bank owns the money and they could just take it from me. and that's why that's why we bitcoin.")
        app = ("My biggest fear is that I go to the bank and I punch you my code and the money's not there because the "
               "bank owns the money and they could just take it from me. And that's why we Bitcoin.")
        sec = ("second biggest. My biggest fear is that I go to the bank and I punch in my code and the money's not "
               "there, 'cause the bank owns the money and they could just take it from me, and that's why, that's why "
               "we Bitcoin.")
        merged = app.replace("punch you", "punch in").replace("that's why we", "that's why that's why we")
        pairs = [{"run": "in", "approved": "you", "took": "run", "edge_distance": 13},
                 {"run": "that's why", "approved": "", "took": "run", "edge_distance": 4}]
        s = LP.segments_of([{"video_id": "mKNAcOFMYD4", "start": 755.454, "end": 764.214, "text": app}])[0]
        adj = self.adj(pairs=pairs, run_decode=run, approved=app, second_recogniser=sec)
        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=merged, adjudication=adj))["verdict"],
                         "adopt")
        back = LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))
        self.assertEqual(back["verdict"], "hold")
        self.assertIn("neither the merged reading nor", back["why"])

    def test_a_repetition_near_the_start_slides_right(self):
        """The same repetition near the span's start: difflib puts the extra "that's why" on the FIRST copy (1 token
        from the edge); sliding right through the equal words gives 3."""
        app = "So that's why we went to the bank and asked them for the money back."
        run = "so that's why that's why we went to the bank and asked them for the money back."
        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
        adj = self.adj(pairs=[{"run": "that's why", "approved": "", "took": "run", "edge_distance": 3}],
                       run_decode=run, approved=app, second_recogniser=run)
        r, p, ops = AT.diff(run, app)
        # the base distance is min(1, 14) = 1; sliding right through the equal run gives 3
        self.assertEqual((ops, AT.edge_distance(r, p, ops[0])), ([("delete", 1, 3, 1, 1)], 3))
        d = LP.decide(s, entry(s, "adopt_spoken", spoken_text="So that's why that's why we went to the bank and asked "
                                                               "them for the money back.", adjudication=adj))
        self.assertEqual(d["verdict"], "adopt", d.get("why"))

    def test_ruling_72_on_top_is_the_second_recognisers_reading_with_its_spill_trimmed(self):
        """The pre-check's as_spoken text is the second recogniser's tokens with the neighbours' spill trimmed, except
        the speaker's own edge repeat ('When, when'); a padding word ('So') is never adopted."""
        app = "When we started this we had a budget pieces of the plan and it worked out."
        run = "when we started this we had a bunch of pieces of the plan and it worked out."
        sec = "So when, when we started this we had a bunch of pieces of the plan and it worked out."
        s = LP.segments_of([{"video_id": "y", "start": 2.0, "end": 9.0, "text": app}])[0]
        adj = self.adj(pairs=[{"run": "bunch of", "approved": "budget", "took": "run", "edge_distance": 7}],
                       run_decode=run, approved=app, second_recogniser=sec)
        merged = app.replace("a budget", "a bunch of")
        self.assertEqual(AT.spill_trimmed(AT.canon.canon_tokens(merged), AT.canon.canon_tokens(sec))[:3],
                         ["when", "when", "we"])
        twice = "When, when " + merged[5:]
        for second, spoken, verdict in ((sec, merged, "adopt"), (sec, twice, "adopt"),
                                        (sec, "So when, when " + merged[5:], "hold"), (sec, "So " + merged, "hold"),
                                        (sec + " And then", twice, "adopt"),            # the next sentence's spill
                                        (sec + " And then", twice[:-1] + " and then.", "hold"),
                                        (sec + " out", twice[:-1] + ", out.", "adopt")):   # the speaker's own repeat
            d = LP.decide(s, entry(s, "adopt_spoken", spoken_text=spoken,
                                   adjudication=dict(adj, second_recogniser=second)))
            self.assertEqual(d["verdict"], verdict, (second, spoken, d.get("why")))

    def test_only_a_ruling_131_record_is_rechecked_by_two_of_three(self):
        d = self.decide(rule="ruling 17 (orchestrator 2026-11-12 '10:20')")                # ruling 84's class: a
        self.assertEqual(d["verdict"], "hold")                                             # content word holds
        self.assertIn("outside ruling 84's class", d["why"])


class TestRuling135(unittest.TestCase):
    """RULING 135 (orchestrator 10:50 ET Nov 17), the comparison canon: spelling, segmentation (names too), the closed
    list of spoken reductions, fillers and a stray single consonant are no difference; a digit, a different single
    letter, a negation and any other change of letters still are. Today's held spans: DataDash 8dbc30ee ('itrust
    capital's' / 'I trust capital's' / 'iTrustCapital's'), DataDash f9413625 ('kind of' / 'kinda'), Natalie Brunell
    cae5123f (the second recogniser's stray 'h')."""
    APPROVED = "Bitcoin conviction and risk management with I trust capital's vault is kind of the point here today."
    s = LP.segments_of([{"video_id": "WjnphankXmM", "start": 601.967, "end": 613.827, "text": APPROVED}])[0]

    def decide(self, spoken, **kw):
        return LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken, **kw))

    def test_spelling_is_no_difference_in_ruling_72s_layer(self):
        for spoken in ("Bitcoin conviction and risk management with iTrustCapital's vault is kind of the point here today.",
                       "Bitcoin conviction and risk management with I trust capital's vault is kinda the point here today.",
                       "Bitcoin conviction and risk management with I-trust Capital's vault is kind of the point here, h, today."):
            d = self.decide(spoken)
            self.assertEqual(d["verdict"], "adopt", (spoken, d.get("why")))     # audit 1057 C2: never a vacuous pass
            self.assertTrue(d["differences"] and all(x["class"] == "spelling only (ruling 135)"
                                                     for x in d["differences"]), d)

    def test_what_still_holds(self):
        for spoken in ("Bitcoin conviction and risk management with I trust capital's vault is kind of the point here 2day.",
                       "Bitcoin conviction and risk management with I trust capital's vault isn't kind of the point here today.",
                       "Bitcoin conviction and risk management with I bust capital's vault is kind of the point here today.",
                       "Bitcoin conviction and risk management with Q trust capital's vault is kind of the point here today."):
            self.assertEqual(self.decide(spoken)["verdict"], "hold", spoken)

    def test_a_spelling_pair_never_reaches_the_vote_in_class_131(self):
        """The render's lock drops a same-words pair right after the currency pairs: it is in neither the record's
        pairs nor the vote, and the sealed text keeps the approved words there (8dbc30ee's three readings)."""
        app = "So Q is a product, iTrustCapital's vault holds the coins and the founder bought a bunch of pieces then."
        run = "so q is a product, itrust capital's vault holds the coins and the founder bought a bunch of pieces then."
        sec = "So Q is a product, I trust capital's vault holds the coins and the founder bought a bunch of pieces then."
        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "pairs": [], "run_decode": run,
               "approved": app, "second_recogniser": sec}
        rows = AT.class_131(app, app, adj)
        self.assertEqual([(x["spoken"], x["approved"], x["took"]) for x in rows],
                         [("itrust capital's", "itrustcapital's", "spelling")])   # audit 1057 C2: a concrete list
        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "pass")


class TestRuling142(unittest.TestCase):
    """RULING 142 (orchestrator 14:32 ET Nov 17), the integrator's batch 110 mirrored (its canon.py byte-identical, its
    adjudicate_lock hunk in attest.class_131): (1) a hyphen right after a number and a space, before a digit, is never
    a sign ('24/7/365' decoded '24 -7, 365': Yahoo Finance f0a51c45 held on 'minus'); (2) a possessive or plural
    ending is a word-form pair: no law L-v 2 hold before ruling 131 (A)'s two of three, which decides it (the run's
    reading only at an edge >= 3; all three different still holds): Natalie Brunell feb4b72f ('bitcoin' / "bitcoin's")."""
    APP = "The thing about Bitcoin's design is that nobody can change the rules without everyone agreeing to it here."
    RUN = "The thing about Bitcoin design is that nobody can change the rules without everyone agreeing to it here."
    THIRD = "The thing about Bitcoins design is that nobody can change the rules without everyone agreeing to it here."
    s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": APP}])[0]

    def test_a_number_space_hyphen_digit_is_no_sign(self):
        self.assertEqual(C.canon_tokens("24 -7, 365"), ["24", "7", "365"])
        self.assertIn("minus", C.canon_tokens("it fell -5% today"))           # a sign after a word stays a sign
        self.assertIn("minus", C.canon_tokens("it is - 5% now"))

    def test_a_word_form_pair_and_what_is_not_one(self):
        self.assertTrue(C.word_form(["bitcoin"], ["bitcoin's"]))
        self.assertTrue(C.word_form(["bitcoin"], ["bitcoins"]))
        for x, y in ((["1990"], ["1990s"]), (["bitcoin", "x"], ["bitcoin's", "y"]), (["bitcoin"], ["ethereum"]),
                     ([], []), (["bitcoin"], ["bitcoin's", "x"])):
            self.assertFalse(C.word_form(x, y), (x, y))

    def decide(self, spoken, second, took):
        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": self.APP,
               "second_recogniser": second,
               "pairs": [{"run": "bitcoin", "approved": "bitcoin's", "took": took, "edge_distance": 3}]}
        return LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken, adjudication=adj))

    def test_two_of_three_decides_a_word_form_pair_of_a_name(self):
        self.assertEqual(self.decide(self.APP, self.APP, "approved")["verdict"], "pass")   # the approved words
        d = self.decide(self.RUN, self.RUN, "run")                                      # as spoken, edge 3
        self.assertEqual((d["verdict"], d.get("adoption")), ("adopt", AT.RULE_131), d)
        self.assertEqual(self.decide(self.APP, self.THIRD, None)["verdict"], "hold")    # all three differ

    def test_a_name_that_is_no_word_form_still_holds(self):
        app = self.APP.replace("Bitcoin's", "Ethereum's")
        adj = {"rule": "ruling 131 (A) (orchestrator 2026-11-17 '08:25')", "run_decode": self.RUN, "approved": app,
               "second_recogniser": app, "pairs": [{"run": "bitcoin", "approved": "ethereum's", "took": "approved",
                                                    "edge_distance": 3}]}
        s = LP.segments_of([{"video_id": "x", "start": 1.0, "end": 9.0, "text": app}])[0]
        self.assertEqual(LP.decide(s, entry(s, "adopt_spoken", spoken_text=app, adjudication=adj))["verdict"], "hold")


class TestCheck(Dirs):
    def run_check(self, segs, appear=None, timeout=60.0):
        t = [0.0]
        sleeps = []

        def sleep(s):
            sleeps.append(s)
            t[0] += s
            if appear and len(sleeps) == 1:
                appear()
        rep = LP.check(segs, "pp-selectid.ledger_x.1", self.req, self.res, timeout_s=timeout, poll_s=10.0,
                       clock=lambda: t[0], sleep=sleep, log=lambda m: None)
        return rep, sleeps

    def test_answers_on_file_are_used_and_nothing_is_asked(self):
        segs = LP.segments_of([HOOK, CLIP])
        for s in segs:
            self.put(s, entry(s))
        rep, sleeps = self.run_check([HOOK, CLIP])
        self.assertEqual((rep["ok"], rep["request_id"], sleeps, os.path.exists(self.req)), (True, None, [], False))
        self.assertEqual(rep["segments"][0]["entry"]["file"], f"DcUbBkyeh9M.216.054-228.674.{LP.DECODER}.json")

    def test_a_missing_answer_asks_the_whole_line_up_and_waits_for_its_own(self):
        segs = LP.segments_of([HOOK, CLIP])
        self.put(segs[0], entry(segs[0]))                                                  # one answered before
        self.put(segs[1], entry(segs[1], "error"))                                         # an error: asked again

        def appear():
            for s in segs:
                self.put(s, entry(s, rid="pp-selectid.ledger_x.1", at="2026-11-13T23:00:00Z"))
        rep, sleeps = self.run_check([HOOK, CLIP], appear)
        self.assertEqual((rep["ok"], rep["request_id"], len(sleeps)), (True, "pp-selectid.ledger_x.1", 1))
        with open(os.path.join(self.req, "pp-selectid.ledger_x.1.json")) as f:
            req = json.load(f)
        self.assertEqual(len(req["segments"]), 2)                                          # the WHOLE line-up

    def test_no_answer_in_time_is_no_verdict_never_a_pass(self):
        rep, sleeps = self.run_check([HOOK, CLIP], timeout=30.0)
        self.assertFalse(rep["ok"])
        self.assertIn("no answer from the render's lock in time", rep["error"])
        self.assertEqual(sleeps, [10.0, 10.0, 10.0])

    def test_an_answer_in_the_old_decoders_file_is_never_read(self):
        """Audit 1845 C2 (glm): ruling 73 changed the decoder, ruling 84 changed it again, and ruling 90 (the
        integrator's spotlight branches) again, ruling 103 with the canon-401k fix again (14:3x Nov 14), and ruling 105
        again (20:5x Nov 14), and ruling 131 again (Nov 17); a file named for an older decoder (25cd6f15e6c9, 8a101f222598,
        962353613cb0, c705b20ed800, d1e155c642a6, a4c307f78c94) is never opened, even with a matching, newer entry under the current rules."""
        s = LP.segments_of([HOOK])[0]
        for dec in ("25cd6f15e6c9", "8a101f222598", "962353613cb0", "c705b20ed800", "d1e155c642a6", "a4c307f78c94",
                    "ce72aefa342d"):
            old = LP.result_file(s, self.res, decoder=dec)
            with open(old, "w") as f:
                json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
            self.assertTrue(old.endswith(f".{dec}.json"))
        self.assertIsNone(LP.answer(s, self.res))                                         # only LP.DECODER's file

    def test_ruling_73_holds_a_span_the_render_cannot_cut(self):
        segs = LP.segments_of([HOOK, CLIP])
        self.put(segs[0], entry(segs[0], "hold", reason="ruling 73: the render cannot cut this span: OUT before the "
                                                        "last locked word's end"))
        self.put(segs[1], entry(segs[1], cut={"cut_in": 937.5, "cut_out": 957.4, "cut_duration": 19.9,
                                              "lead_in_pad_s": 0.47, "error": None}))
        rep, _ = self.run_check([HOOK, CLIP])
        self.assertEqual((rep["ok"], rep["segments"][0]["verdict"], rep["segments"][1]["verdict"]),
                         (False, "hold", "pass"))
        self.assertIn("ruling 73: the render cannot cut this span", rep["segments"][0]["why"])

    def test_a_hold_is_not_ok_and_is_not_an_error(self):
        segs = LP.segments_of([HOOK, CLIP])
        self.put(segs[0], entry(segs[0], "hold", reason="PinError: edge"))
        self.put(segs[1], entry(segs[1]))
        rep, _ = self.run_check([HOOK, CLIP])
        self.assertEqual((rep["ok"], rep["error"], rep["segments"][0]["verdict"]), (False, None, "hold"))


class TestApply(Dirs):
    def pk(self):
        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
                             for m in (HOOK, CLIP)],
                "lines": [{"slot": "takeaway", "text": "Durability matters more than speed."}],
                "hook_first_words": " ".join(HOOK["text"].split()[:8])}

    def pre(self, hook_spoken=None):
        segs = LP.segments_of([HOOK, CLIP])
        self.put(segs[0], entry(segs[0], "adopt_spoken", spoken_text=hook_spoken) if hook_spoken else entry(segs[0]))
        self.put(segs[1], entry(segs[1]))
        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)

    def test_an_adopted_text_is_sealed_with_its_record_and_the_hook_words_follow(self):
        spoken = "Bitcoin launched in in January of 2009. It's never been renamed."      # 'in' said twice
        pk = LP.apply(self.pk(), self.pre(spoken))
        s = pk["segments"][0]
        self.assertEqual(s["text"], spoken)
        self.assertEqual(s["attested"]["was"], HOOK["text"])
        self.assertIn(s["attested"]["differences"][0]["class"], ("immediate repetition", "function word"))
        self.assertEqual(pk["hook_first_words"], "Bitcoin launched in in January of 2009. It's")
        named = "Bitcoin Bitcoin launched in January of 2009. It's never been renamed."   # a name is critical
        with self.assertRaises(ValueError):                                                # (L-v 2): held
            LP.apply(self.pk(), self.pre(named))
        self.assertEqual(LP.pin_problems(pk), [])
        self.assertNotIn("attested", pk["segments"][1])

    def test_apply_refuses_what_does_not_cover_or_pass_or_is_quoted(self):
        pre = self.pre()
        other = self.pk()
        other["segments"][1]["end"] = 958.0
        with self.assertRaises(ValueError):
            LP.apply(other, pre)                                                          # not these segments
        with self.assertRaises(ValueError):
            LP.apply(self.pk(), dict(pre, ok=False))
        spoken = "Bitcoin launched in January of 2009. It's it's never been renamed."
        quoting = self.pk()
        quoting["lines"] = [{"slot": "takeaway", "text": "It's it's never been renamed, and that matters."}]
        with self.assertRaises(ValueError):
            LP.apply(quoting, self.pre(spoken))

    def test_the_pin_stage_needs_a_passing_pre_check_on_these_segments(self):
        self.assertIn("no passing lock pre-check", LP.pin_problems(self.pk())[0])
        pk = LP.apply(self.pk(), self.pre())
        self.assertEqual(LP.pin_problems(pk), [])
        pk["segments"][0]["start"] = 216.2
        self.assertIn("does not cover", LP.pin_problems(pk)[0])


if __name__ == "__main__":
    unittest.main()
