#!/usr/bin/env python3
"""RULING 93 AMENDED (orchestrator 21:10 ET Nov 14; the integrator's spelling, 21:31): a pin whose clip carries a
source caption the 9:16 crop cuts is sealed 16:9-ONLY, moments_package["formats"] = ["16x9"], inside the seal; absent
means both formats, and every pin sealed before it recomputes to its own sha. A medley takes the intersection."""
import copy
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package"):
    sys.path.insert(0, os.path.join(REPO, _p))
import package_pin as PP  # noqa: E402
import test_angles as TA  # noqa: E402


class TestFormats(unittest.TestCase):
    def test_a_16x9_only_clip_seals_its_format_and_a_pin_without_one_as_before(self):
        base = TA.TestPinAndTruth.pk(None)
        plain = PP.to_pin(copy.deepcopy(base), "r")
        self.assertNotIn("formats", plain["moments_package"])
        self.assertEqual(PP.pin_seal(plain), plain["moments_package"]["package_sha256"])
        only = copy.deepcopy(base)
        only["segments"][1]["visual"] = dict(only["segments"][1].get("visual") or {}, formats=["16x9"])
        pin = PP.to_pin(only, "r")                                        # ONE clip of the medley: the intersection
        mp = pin["moments_package"]
        self.assertEqual(mp["formats"], ["16x9"])
        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])          # the integrator's recompute
        self.assertNotEqual(mp["package_sha256"], plain["moments_package"]["package_sha256"])
        dropped = copy.deepcopy(pin)
        del dropped["moments_package"]["formats"]                         # stripping it breaks the seal
        self.assertNotEqual(PP.pin_seal(dropped), mp["package_sha256"])

    def test_formats_of(self):
        self.assertIsNone(PP.formats_of([]))
        self.assertIsNone(PP.formats_of([{"visual": {"formats": None}}, {}]))
        self.assertEqual(PP.formats_of([{}, {"visual": {"formats": ["16x9"]}}]), ["16x9"])

    def test_the_spotlight_now_held_still_recomputes(self):
        p = os.path.join(REPO, "tests", "package", "proof", "ledger_20261114_230148", "SPOTLIGHT_PIN.json")
        pin = json.load(open(p))
        self.assertEqual(PP.pin_seal(pin), pin["moments_package"]["package_sha256"])


if __name__ == "__main__":
    unittest.main()
