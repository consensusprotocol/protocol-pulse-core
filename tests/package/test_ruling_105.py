#!/usr/bin/env python3
"""RULING 105 (orchestrator 20:13 ET Nov 14), the builder's side, landed in lockstep with the integrator's pre-check
(branch ruling105 d5bf9674, decoder a4c307f78c94): the rules and decoder; the record "unstable_second_reading" ("All
readings are recorded on the pin") carried from the pre-check entry onto the segment as it stands and sealed
(package_pin.SEALED_LATER), only when present, so every pin without one seals as before; and THIS side's own check of a
pass that rests on it (lock_precheck.ruling_105_fails): the decoder stable, the second recogniser unstable with one
reading equal to the lock's token, every differing reading a truncation of a NUMBER token. Anything else is a hold:
a stable disagreement, a different number ('68,000' / '86,000'), a different name (the must-fail cases). Offline."""
import copy
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package"):
    sys.path.insert(0, os.path.join(REPO, _p))
import lock_precheck as LP  # noqa: E402
import package_pin  # noqa: E402
import test_angles as TA  # noqa: E402
from test_lock_precheck import CLIP, HOOK, Dirs, entry  # noqa: E402


def record(token="401k", decoder=("401k", "401k", "401k"), second=("401", "401", "401k"), verdict="pass", tests=None):
    """The integrator's field shape (its message of 20:5x Nov 14), as Blockware 06d34e15's readings fill it."""
    when = ("2026-11-14T18:51:07Z", "2026-11-14T19:16:06Z", "now")
    return {"token": token,
            "decoder_readings": [{"at": when[i % 3], "source": "re-listen" if i == 1 else "lock (long window)",
                                  "token": t} for i, t in enumerate(decoder)],
            "second_readings": [{"at": when[i % 3], "source": "re-listen" if i == 1 else "long window", "token": t}
                                for i, t in enumerate(second)],
            "tests": tests if tests is not None else {"decoder_stable": True, "second_unstable": True,
                                                      "truncations_only": True},
            "verdict": verdict}


BLOCKWARE = record()


class TestTheRules(Dirs):
    def test_the_rules_and_decoder_are_the_integrators_ruling_105_ones(self):
        self.assertIn("+ ruling 103 + ruling 105", LP.RULES)                      # ruling 131 joined after it
        self.assertEqual(LP.DECODER, "50fa01b400bd")                                 # batch 114 moved it
        s = LP.segments_of([HOOK])[0]
        self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84 + ruling 103",
                          at="2026-11-14T21:00:00Z"))
        self.assertIsNone(LP.answer(s, self.res))                                 # ruling 103's rules: never read
        self.put(s, entry(s, at="2026-11-14T21:01:00Z"))
        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")


class TestThisSidesCheck(unittest.TestCase):
    s = LP.segments_of([HOOK])[0]

    def decide(self, rec, outcome="no_difference"):
        return LP.decide(self.s, entry(self.s, outcome, unstable_second_reading=rec))

    def test_blockwares_readings_pass(self):
        self.assertIsNone(LP.ruling_105_fails(copy.deepcopy(BLOCKWARE)))
        self.assertEqual(self.decide(copy.deepcopy(BLOCKWARE))["verdict"], "pass")

    def test_no_record_changes_nothing(self):
        self.assertEqual(self.decide(None)["verdict"], "pass")
        self.assertEqual(self.decide(None, "hold")["verdict"], "hold")

    def test_must_fail_a_second_recogniser_stable_in_its_disagreement(self):
        d = self.decide(record(second=("401", "401", "401")))              # even a record that says "pass"
        self.assertEqual(d["verdict"], "hold")
        self.assertIn("(2)", d["why"])

    def test_a_record_whose_second_readings_never_vary_is_no_unstable_reading(self):
        d = self.decide(record(second=("401k", "401k")))                   # nothing disputed: the record should
        self.assertEqual(d["verdict"], "hold")                              # be null; one that says "pass" is
        self.assertIn("(2)", d["why"])                                      # malformed, and fails closed

    def test_must_fail_a_different_number(self):
        d = self.decide(record(token="86000", decoder=("86000", "86000"), second=("68000", "86000")))
        self.assertEqual(d["verdict"], "hold")                              # '68,000' is no truncation of '86,000'
        self.assertIn("(3)", d["why"])

    def test_must_fail_a_different_name(self):
        for second in (("Taylor", "Saylor"), ("Say", "Saylor")):           # a name never qualifies, cut short or not
            d = self.decide(record(token="Saylor", decoder=("Saylor", "Saylor"), second=second))
            self.assertEqual(d["verdict"], "hold", second)
            self.assertIn("a name never qualifies", d["why"])

    def test_a_dropped_token_or_a_digit_cut_off_is_no_truncation(self):
        for token, second in (("401k", ("", "401k")),                   # dropped
                              ("4015", ("401", "4015")),                 # a digit cut off: another number
                              ("401k", ("40", "401k"))):                 # '1k' cut off holds a digit
            d = self.decide(record(token=token, decoder=(token, token), second=second))
            self.assertEqual(d["verdict"], "hold", second)
            self.assertIn("(3)", d["why"])

    def test_formatting_is_read_through_canon_on_both_sides(self):          # audit 2049 C1 (qwen, glm)
        self.assertIsNone(LP.ruling_105_fails(record(token="401K", decoder=("401(k)", "401k", "401K"),
                                                     second=("401", "401", "401K"))))
        d = self.decide(record(token="86,000", decoder=("86,000", "86000"), second=("68,000", "86,000")))
        self.assertEqual(d["verdict"], "hold")                              # commas change nothing: still another
        self.assertIn("(3)", d["why"])                                      # number
        for tok in (None, "", "  "):
            d = self.decide(record(token=tok, decoder=("401k", "401k"), second=("401", "401k")))
            self.assertEqual(d["verdict"], "hold", tok)
            self.assertIn("is not a number", d["why"])

    def test_an_adoption_that_rests_on_the_record_is_checked_too(self):     # audit 2049 C1 (glm)
        spoken = "Bitcoin launched in January of 2009. It's never been, uh, renamed."
        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken,
                                    unstable_second_reading=record(second=("401", "401", "401"))))
        self.assertEqual((d["verdict"], "(2)" in d["why"]), ("hold", True))
        d = LP.decide(self.s, entry(self.s, "adopt_spoken", spoken_text=spoken,
                                    unstable_second_reading=copy.deepcopy(BLOCKWARE)))
        self.assertEqual(d["verdict"], "adopt")                             # a good record: the adoption goes on

    def test_an_unstable_decoder_holds(self):
        d = self.decide(record(decoder=("401k", "401")))
        self.assertEqual(d["verdict"], "hold")
        self.assertIn("(1)", d["why"])

    def test_the_second_recogniser_must_read_the_token_at_least_once(self):
        d = self.decide(record(second=("401", "40l")))
        self.assertEqual(d["verdict"], "hold")
        self.assertIn("(2)", d["why"])

    def test_too_few_readings_hold(self):
        for dec, sec in (((), ("401", "401k")), (("401k",), ("401k",))):
            d = self.decide(record(decoder=dec, second=sec))
            self.assertEqual(d["verdict"], "hold", (dec, sec))
            self.assertIn("too few readings", d["why"])

    def test_the_records_own_tests_and_verdict_must_agree(self):
        d = self.decide(record(tests={"decoder_stable": True, "second_unstable": True, "truncations_only": False}))
        self.assertEqual(d["verdict"], "hold")
        self.assertIn("own tests", d["why"])
        d = self.decide(record(verdict="hold"))                          # a hold record under a pass outcome: hold
        self.assertEqual(d["verdict"], "hold")
        many = {"tokens": ["401k", "45"], "verdict": "hold", "why": "more than one disputed token"}
        d = self.decide(many)                                               # the edge form
        self.assertEqual(d["verdict"], "hold")
        self.assertIn("more than one disputed token", d["why"])
        for odd in ("pass", ["401k"], 7):                                   # not an object
            self.assertEqual(self.decide(odd)["verdict"], "hold", odd)

    def test_a_ruling_105_hold_stays_a_hold(self):
        d = self.decide(record(second=("401", "401", "401"), verdict="hold"), outcome="hold")
        self.assertEqual(d["verdict"], "hold")


class TestTheRecordReachesTheSeal(Dirs):
    def check(self, rec):
        segs = LP.segments_of([HOOK, CLIP])
        self.put(segs[0], entry(segs[0], unstable_second_reading=rec))
        self.put(segs[1], entry(segs[1], unstable_second_reading=None))
        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)

    def pk(self):
        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
                             for m in (HOOK, CLIP)], "lines": [], "hook_first_words": ""}

    def test_the_record_is_carried_as_it_stands_and_only_when_present(self):
        pre = self.check(copy.deepcopy(BLOCKWARE))
        self.assertTrue(pre["ok"])
        self.assertEqual([r["unstable_second_reading"] for r in pre["segments"]], [BLOCKWARE, None])
        pk = LP.apply(self.pk(), pre)
        self.assertEqual(pk["segments"][0]["unstable_second_reading"], BLOCKWARE)
        self.assertIsNot(pk["segments"][0]["unstable_second_reading"], pre["segments"][0]["unstable_second_reading"])
        self.assertNotIn("unstable_second_reading", pk["segments"][1])
        self.assertIsNone(LP.unstable_of({"unstable_second_reading": ["401k"]}))     # not an object: no record

    def test_a_pass_this_side_refuses_never_reaches_a_pin(self):
        pre = self.check(record(second=("401", "401", "401")))
        self.assertFalse(pre["ok"])
        self.assertEqual(pre["segments"][0]["verdict"], "hold")
        with self.assertRaises(ValueError):
            LP.apply(self.pk(), pre)

    def test_the_record_is_sealed_and_a_pin_without_one_seals_as_before(self):
        base = TA.TestPinAndTruth.pk(None)
        plain = package_pin.to_pin(copy.deepcopy(base), "r")
        self.assertNotIn("unstable_second_reading", plain["segments"][0])
        with_r = copy.deepcopy(base)
        with_r["segments"][0]["unstable_second_reading"] = copy.deepcopy(BLOCKWARE)
        pin = package_pin.to_pin(with_r, "r")
        self.assertEqual(pin["segments"][0]["unstable_second_reading"], BLOCKWARE)
        sha = pin["moments_package"]["package_sha256"]
        self.assertEqual(package_pin.pin_seal(pin), sha)                           # the integrator's recompute
        self.assertNotEqual(sha, plain["moments_package"]["package_sha256"])      # the record is inside the seal
        tampered = copy.deepcopy(pin)
        tampered["segments"][0]["unstable_second_reading"]["second_readings"][2]["token"] = "401"
        self.assertNotEqual(package_pin.pin_seal(tampered), sha)
        self.assertEqual(package_pin.pin_seal(plain), plain["moments_package"]["package_sha256"])

    def test_the_spotlight_now_rendering_still_recomputes_to_its_own_seal(self):
        import json
        p = os.path.join(REPO, "tests", "package", "proof", "ledger_20261114_230148", "SPOTLIGHT_PIN.json")
        pin = json.load(open(p))
        self.assertEqual(package_pin.pin_seal(pin), pin["moments_package"]["package_sha256"])
        self.assertTrue(pin["moments_package"]["package_sha256"].startswith("3f481f5a"))


if __name__ == "__main__":
    unittest.main()
