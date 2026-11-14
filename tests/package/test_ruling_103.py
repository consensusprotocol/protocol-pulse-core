#!/usr/bin/env python3
"""RULING 103 (orchestrator 14:12 ET Nov 14), the builder's side, landed with the integrator's canon-401k fix (one
decoder-sha move): the pre-check's rules and decoder; the targeted re-listen's record ("Record both short readings on
the pin") carried from the pre-check entry onto the segment as it stands and sealed (package_pin.SEALED_LATER), only when
a re-listen ran, so every pin without one seals as before; canon's '401k' is a plan's name (pipeline/test_canon.py, the
integrator's tests, byte-identical). Offline: temporary requests and results directories."""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package"):
    sys.path.insert(0, os.path.join(REPO, _p))
import canon as C  # noqa: E402
import lock_precheck as LP  # noqa: E402
import package_pin  # noqa: E402
import test_angles as TA  # noqa: E402
from test_lock_precheck import CLIP, HOOK, Dirs, entry  # noqa: E402

RELISTEN = {"token": "401k", "against": "", "window": [14.84, 18.38], "source_window": [14.84, 18.38],
            "decoder_reading": "IRA. I don't have a 401k. I don't own a single",
            "second_reading": "Roth IRA. I don't have a 401k. I don't own a single", "verdict": "pass",
            "scribe_usd": 0.0007}


class TestTheRules(Dirs):
    def test_an_entry_under_the_rules_before_103_is_never_read(self):
        s = LP.segments_of([HOOK])[0]
        self.put(s, entry(s, rules="ruling 17 + ruling 72 + ruling 73 + ruling 84", at="2026-11-14T19:00:00Z"))
        self.assertIsNone(LP.answer(s, self.res))
        self.put(s, entry(s, at="2026-11-14T19:01:00Z"))                     # the same answer under ruling 103's rules
        self.assertEqual(LP.answer(s, self.res)["outcome"], "no_difference")


class TestTheRecordReachesTheSeal(Dirs):
    def check(self, relisten):
        segs = LP.segments_of([HOOK, CLIP])
        self.put(segs[0], entry(segs[0], relisten=relisten))
        self.put(segs[1], entry(segs[1], relisten=None))
        return LP.check([HOOK, CLIP], "r", self.req, self.res, log=lambda m: None)

    def pk(self):
        return {"segments": [{"video_id": m["video_id"], "start": m["start"], "end": m["end"], "text": m["text"]}
                             for m in (HOOK, CLIP)], "lines": [], "hook_first_words": ""}

    def test_a_relisten_record_is_carried_as_it_stands_and_only_when_one_ran(self):
        pre = self.check(copy.deepcopy(RELISTEN))
        self.assertTrue(pre["ok"])
        self.assertEqual([r["relisten"] for r in pre["segments"]], [RELISTEN, None])
        pk = LP.apply(self.pk(), pre)
        self.assertEqual(pk["segments"][0]["relisten"], RELISTEN)                 # as it stands,
        self.assertIsNot(pk["segments"][0]["relisten"], pre["segments"][0]["relisten"])   # a copy (glm C1)
        self.assertNotIn("relisten", pk["segments"][1])                           # null: no key
        edge = {"token": "401k", "against": "401", "verdict": "hold", "why": "the lock's words do not read as its token"}
        self.assertEqual(LP.relisten_of({"relisten": dict(edge)}), edge)          # the edge form, as it stands (grok C2)
        for odd in ("pass", ["401k"], 7):                                           # not an object: no record
            self.tmp.cleanup()
            self.setUp()
            pre = self.check(odd)
            self.assertIsNone(pre["segments"][0]["relisten"], odd)                 # the row's contract: None
            pk = LP.apply(self.pk(), pre)
            self.assertNotIn("relisten", pk["segments"][0], odd)

    def test_the_record_is_sealed_and_a_pin_without_one_seals_as_before(self):
        base = TA.TestPinAndTruth.pk(None)
        plain = package_pin.to_pin(copy.deepcopy(base), "r")
        self.assertNotIn("relisten", plain["segments"][0])
        with_r = copy.deepcopy(base)
        with_r["segments"][0]["relisten"] = copy.deepcopy(RELISTEN)
        pin = package_pin.to_pin(with_r, "r")
        self.assertEqual(pin["segments"][0]["relisten"], RELISTEN)
        sha = pin["moments_package"]["package_sha256"]
        self.assertEqual(package_pin.pin_seal(pin), sha)                           # the integrator's recompute
        self.assertNotEqual(sha, plain["moments_package"]["package_sha256"])      # the record is inside the seal
        tampered = copy.deepcopy(pin)
        tampered["segments"][0]["relisten"]["second_reading"] = "Roth IRA. I don't have a 401. I don't own a single"
        self.assertNotEqual(package_pin.pin_seal(tampered), sha)
        self.assertEqual(package_pin.pin_seal(plain), plain["moments_package"]["package_sha256"])


class TestCanonOnThisSide(unittest.TestCase):
    """The integrator's canon fix, taken byte-identical (its own tests: pipeline/test_canon.py TestRetirementPlans):
    this side's step-A and attest code read the same canonical tokens as the render's lock."""

    def test_the_plan_is_a_name_here_too(self):
        self.assertFalse(C.same("a 401k", "a 401,000"))
        self.assertTrue(C.same("I don't have a 401k.", "I don't have a 401(k)."))
        self.assertFalse(C.same("I don't have a 401k", "I don't have a 401 ,"))     # Blockware's hold stands


if __name__ == "__main__":
    unittest.main()
