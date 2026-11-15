#!/usr/bin/env python3
"""RULING 116 (Q3, ruling 106's default APPLY): THE CALIBRATED LINE-UP BAR (pipeline/lineup_bar.py). Each verdict's
parts (clips-alone: every clip after the hook; coherence: every clip after the hook and the VO point) are at least the
lowest value they took on PBX's four approved line-ups (seeds 7, 8, 9, Grok), never under 3; ONLY for a verdict the
calibrated rater gave; every other verdict, and every verdict while the file is invalid, stays on the standard bar."""
import copy
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package"):
    sys.path.insert(0, os.path.join(REPO, _p))
import hook_bar as HB  # noqa: E402
import lineup_bar as LB  # noqa: E402
import package as PK  # noqa: E402
import package_pin as PP  # noqa: E402

AT = datetime(2026, 11, 15, 20, 33, 0, tzinfo=timezone.utc)
G = "xai:grok-4.20-0309-reasoning"
V = {"clips_alone": "mv", "coherence": "cv"}


def runs(ca=((4, 3), (4, 4)), co=(((5, 3), 3), ((4, 4), 4))):
    return {"clips_alone": [{"clips": {"clip_01": a, "clip_02": b}} for a, b in ca],
            "coherence": [{"clips": {"clip_01": a, "clip_02": b}, "vo_point": v} for (a, b), v in co]}


def cal(**kw):
    fl, low = LB.floors_from(runs())
    return dict({"rater": G, "question_versions": dict(V), "measured_at": AT.isoformat(), "valid_h": None,
                 "floors": fl, "floors_below_3": low}, **kw)


class TestFloors(unittest.TestCase):
    def test_each_part_is_its_lowest_value_never_under_3(self):
        self.assertEqual(LB.floors_from(runs()), ({"clips_alone": {"clip": 3}, "coherence": {"clip": 3, "vo_point": 3}},
                                                  []))
        fl, low = LB.floors_from(runs(ca=((4, 4), (5, 4)), co=(((5, 4), 4), ((4, 4), 5))))
        self.assertEqual(fl, {"clips_alone": {"clip": 4}, "coherence": {"clip": 4, "vo_point": 4}})
        fl, low = LB.floors_from(runs(ca=((2, 4),), co=(((4, 4), 1),)))
        self.assertEqual((fl["clips_alone"]["clip"], fl["coherence"]["vo_point"]), (3, 3))
        self.assertEqual(low, ["clips_alone clip 2 (stopped at 3)", "coherence vo_point 1 (stopped at 3)"])

    def test_a_run_without_its_ratings_measures_nothing(self):
        for bad in ({"clips_alone": [], "coherence": runs()["coherence"]},
                    dict(runs(), coherence=[{"clips": {"clip_01": 4}}]),
                    dict(runs(), clips_alone=[{"clips": {}}])):
            with self.assertRaises(ValueError):
                LB.floors_from(bad)


class TestTheFile(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.d.name, "lineup_calibration.json")

    def tearDown(self):
        self.d.cleanup()

    def test_valid_only_sealed_for_its_versions_and_rater_and_within_its_validity(self):
        HB.write(cal(), self.path)
        live, why = LB.bar(V, now=AT + timedelta(days=30), path=self.path)          # valid_h null: no expiry
        self.assertEqual((live["clips_alone"], live["coherence"], live["rater"], why),
                         ({"clip": 3}, {"clip": 3, "vo_point": 3}, G, None))
        self.assertIn("clips-alone every clip >= 3; coherence every clip >= 3 and the VO point >= 3", LB.text(live))
        for k, v in (("clips_alone", "another"), ("coherence", "another")):
            live, why = LB.bar(dict(V, **{k: v}), now=AT, path=self.path)
            self.assertIsNone(live)
            self.assertIn("standard bar until it is re-run", why)
        bad = (cal(rater=""), cal(valid_h=24), cal(measured_at="2026-11-15T20:33:00"),
               cal(floors={"clips_alone": {"clip": 2}, "coherence": {"clip": 3, "vo_point": 3}}))
        for c in bad:
            HB.write(c, self.path)
            self.assertIsNone(LB.bar(V, now=AT + timedelta(days=2), path=self.path)[0], c.get("valid_h"))
        c = cal()
        del c["valid_h"]
        HB.write(c, self.path)
        self.assertIn("names no valid_h", LB.bar(V, now=AT, path=self.path)[1])
        HB.write(cal(), self.path)
        live, why = LB.bar(V, now=AT - timedelta(minutes=6), path=self.path)
        self.assertIn("in the future", why)
        with open(self.path) as f:
            body = json.load(f)
        body["floors"]["clips_alone"]["clip"] = 2                                 # a hand edit: the seal breaks
        with open(self.path, "w") as f:
            json.dump(body, f)
        self.assertIsNone(LB.bar(V, now=AT, path=self.path)[0])

    def test_the_floors_only_for_the_calibrated_raters_own_verdict(self):
        HB.write(cal(), self.path)
        live, _ = LB.bar(V, now=AT, path=self.path)
        std = PK.STANDARD_LINEUP
        self.assertEqual(LB.floors_for("coherence", G, live, std), ({"clip": 3, "vo_point": 3}, "calibrated"))
        self.assertEqual(LB.floors_for("coherence", "heimdall:deepseek/deepseek-v4.1-flash", live, std),
                         ({"clip": 4, "vo_point": 4}, "standard"))
        self.assertEqual(LB.floors_for("clips_alone", G, None, std), ({"clip": 4}, "standard"))   # no valid bar


class TestTheMark(unittest.TestCase):
    """Q3: a package whose two verdicts both passed on the calibrated bar says so in its record and pin, outside the
    seal; one judged on the standard bar carries no mark."""

    def test_both_verdicts_calibrated_or_no_mark_and_the_pin_carries_it_outside_the_seal(self):
        import test_angles as TA
        med = {"bar": "calibrated", "floors": {"clip": 3}, "calibration_sha256": "l" * 64}
        coh = {"bar": "calibrated", "floors": {"clip": 3, "vo_point": 3}, "calibration_sha256": "l" * 64}
        m = PK.lineup_bar_mark(med, coh)
        self.assertEqual((m["note"], m["floors"], m["ruling"]),
                         ("line-up passed on the calibrated bar", {"clips_alone": {"clip": 3},
                                                                   "coherence": {"clip": 3, "vo_point": 3}}, "116"))
        self.assertIsNone(PK.lineup_bar_mark(dict(med, bar="standard"), coh))
        self.assertIsNone(PK.lineup_bar_mark(med, None))
        base = TA.TestPinAndTruth.pk(None)
        plain = PP.to_pin(copy.deepcopy(base), "r")["moments_package"]
        marked = PP.to_pin(dict(copy.deepcopy(base), lineup_bar=m), "r")["moments_package"]
        self.assertNotIn("lineup_bar", plain)
        self.assertEqual(marked["lineup_bar"]["note"], "line-up passed on the calibrated bar")
        self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal


class TestTheLiveCalibration(unittest.TestCase):
    """The file production reads (pipeline/lineup_calibration.json): its floors derive from their source
    (tests/package/proof/clips116/), it is valid for production's two prompts, its rater is the first of both
    verdicts' production lists, and it does not expire."""
    real_hook_bar = True

    def test_its_floors_are_its_sources_lowest_ratings(self):
        c, why = HB.load(LB.PATH)
        self.assertIsNone(why)
        proof = os.path.join(REPO, "tests", "package", "proof", "clips116")
        with open(os.path.join(proof, "CALIBRATION.json")) as f:
            ca = json.load(f)
        with open(os.path.join(proof, "COHERENCE.json")) as f:
            co = json.load(f)
        src = {"clips_alone": [r for x in ca["lineups"].values() for r in x["runs"]],
               "coherence": [r for x in co["packages"].values() for r in x["runs"]]}
        self.assertTrue(all(r.get("backend") == c["rater"] for v in src.values() for r in v))
        self.assertEqual(LB.floors_from(src), (c["floors"], c["floors_below_3"]))
        self.assertEqual(max(len(r["flagged"]) for r in src["clips_alone"]), PK.LY_MAX_BRIDGES)   # joins: the law's

    def test_it_is_live_for_production_and_does_not_expire(self):
        import providers as P
        c, _ = HB.load(LB.PATH)
        versions = {"clips_alone": PK.MEDLEY_VERSION, "coherence": PK.COHERENCE_VERSION}
        live, why = LB.bar(versions, now=datetime.fromisoformat(c["measured_at"]) + timedelta(days=30))
        self.assertEqual((live is not None, why), (True, None))
        r = P.Router(env_path="/nonexistent", routing="heimdall_first")
        for kind in ("clips_alone", "coherence"):
            self.assertEqual(r.chain("coherence_verdict", kind)[0], c["rater"], kind)


if __name__ == "__main__":
    unittest.main()
