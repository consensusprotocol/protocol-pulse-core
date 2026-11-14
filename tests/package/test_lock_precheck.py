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
                         "DcUbBkyeh9M.216.054-228.674.962353613cb0.json")             # ruling 84's decoder

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
        self.assertEqual(LP.RULES, "ruling 17 + ruling 72 + ruling 73 + ruling 84")

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
        s2 = dict(self.s, approved_text=e["approved_text"])               # a filler on the approved side alone
        self.assertEqual(LP.decide(s2, e)["verdict"], "hold")


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
        self.assertEqual(rep["segments"][0]["entry"]["file"], "DcUbBkyeh9M.216.054-228.674.962353613cb0.json")

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
        """Audit 1845 C2 (glm): ruling 73 changed the decoder, and ruling 84 changed it again; a file named for an
        older decoder (25cd6f15e6c9, 8a101f222598) is never opened, even with a matching, newer entry under the current
        rules."""
        s = LP.segments_of([HOOK])[0]
        for dec in ("25cd6f15e6c9", "8a101f222598"):
            old = LP.result_file(s, self.res, decoder=dec)
            with open(old, "w") as f:
                json.dump([entry(s, "no_difference", at="2026-11-14T02:00:00Z")], f)
            self.assertTrue(old.endswith(f".{dec}.json"))
        self.assertIsNone(LP.answer(s, self.res))                                         # only 962353613cb0's file

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
