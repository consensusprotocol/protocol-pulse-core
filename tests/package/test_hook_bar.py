#!/usr/bin/env python3
"""RULING 115 (orchestrator 13:24 ET Nov 15): THE CALIBRATED HOOK BAR (pipeline/hook_bar.py). A hook passes when each of
scroll / alone / setup is at least the LOWEST value that part takes across PBX's approved hooks under the same asking
(ALONE, production's seed, Grok); no floor under 3; one sealed calibration file, valid for its rater, question version,
seed and asking, for 24 h; a package sealed on it says so; PBX's verdicts on such packages are appended as examples.
The live file is checked against its source and against production's hook job."""
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
import package as PK  # noqa: E402
import package_pin as PP  # noqa: E402

AT = datetime(2026, 11, 15, 18, 7, 52, tzinfo=timezone.utc)
G = "xai:grok-4.20-0309-reasoning"
Q = "heimdall:qwen/qwen3.8-27b"


def approved(*parts):
    return [{"ref": f"ref-{i}", "scroll": s, "alone": a, "setup": u, "backend": G} for i, (s, a, u) in enumerate(parts)]


def cal(parts=((3, 4, 3), (3, 5, 4), (4, 5, 4)), **kw):
    ap = approved(*parts)
    fl, low = HB.floors_from(ap)
    return dict({"rater": G, "asking": "alone", "seed": 7, "question_version": "qv", "measured_at": AT.isoformat(),
                 "approved": ap, "floors": fl, "floors_below_3": low, "examples": []}, **kw)


class TestFloors(unittest.TestCase):
    def test_each_floor_is_its_parts_lowest_value_across_the_approved_hooks(self):
        self.assertEqual(HB.floors_from(approved((3, 4, 3), (3, 5, 4), (4, 5, 4))),
                         ({"scroll": 3, "alone": 4, "setup": 3}, []))
        self.assertEqual(HB.floors_from(approved((5, 5, 5), (4, 5, 5))), ({"scroll": 4, "alone": 5, "setup": 5}, []))

    def test_a_floor_under_3_stops_at_3_and_is_told(self):
        fl, low = HB.floors_from(approved((2, 5, 4), (3, 1, 4)))
        self.assertEqual(fl, {"scroll": 3, "alone": 3, "setup": 4})
        self.assertEqual(low, ["scroll 2 (stopped at 3)", "alone 1 (stopped at 3)"])

    def test_a_part_missing_or_not_an_integer_measures_nothing(self):
        for bad in ([{"scroll": 3, "alone": 4}], [{"scroll": 3, "alone": 4, "setup": 3.0}],
                    [{"scroll": True, "alone": 4, "setup": 3}], []):
            with self.assertRaises(ValueError):
                HB.floors_from(bad)


class TestTheFile(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.d.name, "hook_calibration.json")

    def tearDown(self):
        self.d.cleanup()

    def bar(self, now=AT + timedelta(hours=1), **kw):
        a = dict(dict(rater=None, question_version="qv", seed=7), **kw)
        return HB.bar(a["rater"], a["question_version"], a["seed"], now=now, path=self.path)

    def test_written_sealed_and_read_back_as_the_live_bar(self):
        c = HB.write(cal(), self.path)
        self.assertEqual(c["sha256"], HB.body_sha(c))
        live, why = self.bar()
        self.assertIsNone(why)
        self.assertEqual((live["floors"], live["rater"], live["sha256"]),
                         ({"scroll": 3, "alone": 4, "setup": 3}, G, c["sha256"]))
        self.assertIn(f"scroll >= 3, alone >= 4, setup >= 3, on {G} asked alone at seed 7 (calibration "
                      f"{c['sha256'][:12]})", HB.text(live))

    def test_a_hand_edit_breaks_the_seal_and_no_hook_passes(self):
        HB.write(cal(), self.path)
        with open(self.path) as f:
            c = json.load(f)
        c["floors"]["alone"] = 3                                          # edited, not re-sealed
        with open(self.path, "w") as f:
            json.dump(c, f)
        live, why = self.bar()
        self.assertIsNone(live)
        self.assertIn("sha256 does not match", why)
        self.assertEqual(HB.passes({"scroll": 5, "alone": 5, "setup": 5, "backend": G}, live),
                         (False, "no valid hook calibration"))
        self.assertEqual(HB.text(live), "no valid hook calibration: no hook passes")

    def test_missing_or_unreadable_is_no_bar(self):
        live, why = self.bar()
        self.assertIsNone(live)
        self.assertIn("cannot be read", why)
        with open(self.path, "w") as f:
            f.write("{not json")
        self.assertIsNone(self.bar()[0])

    def test_valid_only_for_its_question_version_seed_asking_and_rater(self):
        HB.write(cal(), self.path)
        self.assertIsNotNone(self.bar(rater=G)[0])
        for kw in ({"question_version": "another"}, {"seed": 8}, {"rater": Q}):
            live, why = self.bar(**kw)
            self.assertIsNone(live, kw)
            self.assertIn("no hook passes until it is re-run", why)
        HB.write(cal(asking="batched"), self.path)                         # the batch moved single ratings
        self.assertIsNone(self.bar()[0])

    def test_once_a_day_a_stale_calibration_passes_nothing(self):
        HB.write(cal(), self.path)
        self.assertIsNotNone(self.bar(now=AT + timedelta(hours=23, minutes=59))[0])
        live, why = self.bar(now=AT + timedelta(hours=24, minutes=1))
        self.assertIsNone(live)
        self.assertIn("over 24 h old", why)

    def test_a_future_or_naive_measured_at_passes_nothing(self):
        """Audit 20261115_1410 C1 (qwen): a calibration "measured" ahead of now would stretch its 24 h; a time with no
        timezone cannot be compared with now (it must never raise into a build)."""
        HB.write(cal(), self.path)
        self.assertIsNotNone(self.bar(now=AT - timedelta(minutes=4))[0])  # clock skew inside 5 min
        live, why = self.bar(now=AT - timedelta(minutes=6))
        self.assertIsNone(live)
        self.assertIn("is in the future", why)
        HB.write(cal(measured_at="2026-11-15T18:07:52"), self.path)
        live, why = self.bar()
        self.assertIsNone(live)
        self.assertIn("no timezone", why)

    def test_a_floor_under_3_in_the_file_is_refused(self):
        HB.write(cal(floors={"scroll": 2, "alone": 4, "setup": 3}), self.path)
        live, why = self.bar()
        self.assertIsNone(live)
        self.assertIn("a floor under 3", why)


class TestPasses(unittest.TestCase):
    LIVE = {"floors": {"scroll": 3, "alone": 4, "setup": 3}, "rater": G, "sha256": "s" * 64, "seed": 7}

    def ok(self, s, a, u, b=G):
        return HB.passes({"scroll": s, "alone": a, "setup": u, "backend": b}, self.LIVE)

    def test_every_part_at_least_its_floor_by_the_calibrated_rater(self):
        self.assertEqual(self.ok(3, 4, 3), (True, None))                  # at every floor
        self.assertEqual(self.ok(5, 5, 5), (True, None))
        self.assertEqual(self.ok(2, 4, 3), (False, "scroll 2 < 3"))
        self.assertEqual(self.ok(3, 3, 3), (False, "alone 3 < 4"))
        self.assertEqual(self.ok(3, 4, 2), (False, "setup 2 < 3"))
        self.assertEqual(self.ok(2, 3, 2), (False, "scroll 2 < 3; alone 3 < 4; setup 2 < 3"))
        self.assertEqual(self.ok(5, 5, 5, Q), (False, f"rated by {Q}, but the bar is calibrated on {G}"))
        self.assertFalse(HB.passes({"scroll": 5, "alone": 5, "backend": G}, self.LIVE)[0])           # a part missing
        self.assertFalse(HB.passes({"scroll": 5, "alone": 5, "setup": True, "backend": G}, self.LIVE)[0])


class TestExamples(unittest.TestCase):
    """RULING 115 (2): PBX's approve or reject of a package sealed on the bar is appended as an example."""

    def test_approved_and_rejected_with_his_reason_appended_sealed_and_the_floors_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json")
            HB.write(cal(), path)
            hook = {"moment_id": "m1", "text": "Bitcoin t.", "channel": "A", "scroll": 3, "alone": 4, "setup": 3,
                    "backend": G, "extra": 1}
            HB.add_example("story-1", "approved", hook, path=path, now=AT)
            c = HB.add_example("story-2", "rejected", hook, reason="the opener is mid-sentence", path=path, now=AT)
            self.assertEqual([(e["story_id"], e["verdict"], e["reason"]) for e in c["examples"]],
                             [("story-1", "approved", None), ("story-2", "rejected", "the opener is mid-sentence")])
            self.assertNotIn("extra", c["examples"][0]["hook"])
            self.assertEqual(HB.load(path)[0], c)                          # sealed
            self.assertEqual(c["floors"], cal()["floors"])                  # a new floor comes from the next run
            for verdict, reason in (("rejected", None), ("maybe", "r")):    # a rejection carries his reason
                with self.assertRaises(ValueError):
                    HB.add_example("story-3", verdict, hook, reason=reason, path=path)
            self.assertEqual(len(HB.load(path)[0]["examples"]), 2)


class TestTheMark(unittest.TestCase):
    """RULING 115 (2): a package sealed on the bar says so in its record and in its pin, in one plain line, outside
    the seal (the integrator prints it in the Telegram note)."""

    def test_the_mark_is_the_bar_the_hooks_were_judged_on(self):
        """Audit 20261115_1410 C2 (glm): a mark made at seal time names the bar the build judged its hooks on, even
        if the calibration has changed (or expired) since."""
        from unittest import mock
        judged = {"floors": {"scroll": 3, "alone": 4, "setup": 3}, "sha256": "j" * 64, "rater": G, "seed": 7}
        with mock.patch.object(PK, "_live_bar", lambda: (None, "the hook calibration is over 24 h old")):
            m = PK.hook_bar_mark(judged)
            self.assertEqual((m["calibration_sha256"], m["floors"]), ("j" * 64, judged["floors"]))
            self.assertIsNone(PK.hook_bar_mark()["floors"])                 # read now: what it says now

    def test_the_pin_carries_the_line_outside_the_seal(self):
        import test_angles as TA
        base = TA.TestPinAndTruth.pk(None)
        plain = PP.to_pin(copy.deepcopy(base), "r")
        self.assertNotIn("hook_bar", plain["moments_package"])
        pin = PP.to_pin(dict(copy.deepcopy(base), hook_bar=PK.hook_bar_mark()), "r")
        mp = pin["moments_package"]
        self.assertEqual((mp["hook_bar"]["note"], mp["hook_bar"]["floors"], mp["hook_bar"]["ruling"]),
                         ("hook passed on the calibrated bar", {"scroll": 3, "alone": 4, "setup": 3}, "115"))
        self.assertEqual(mp["package_sha256"], plain["moments_package"]["package_sha256"])   # outside the seal
        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])


class TestTheLiveCache(unittest.TestCase):
    """package._live_bar: the bar is read once per state of the file and per minute (so a calibration that ages past
    its 24 h mid-build stops passing hooks within the minute), and again as soon as the file changes."""
    real_hook_bar = True

    def test_read_once_a_minute_and_again_when_the_file_changes(self):
        import types
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "c.json")
            now = datetime.now(timezone.utc)
            HB.write(cal(question_version=PK.HOOK_VERSION, seed=PK.HOOK_SEED, measured_at=now.isoformat()), path)
            t, reads, real = [1000.0 * 60], [], PK.hook_live_bar
            with mock.patch.object(HB, "PATH", path), mock.patch.object(PK, "time", types.SimpleNamespace(
                    time=lambda: t[0])), mock.patch.object(PK, "hook_live_bar", lambda: (reads.append(1), real())[1]):
                PK._LIVE.clear()
                live, why = PK._live_bar()
                self.assertEqual((live["floors"], why, len(reads)), ({"scroll": 3, "alone": 4, "setup": 3}, None, 1))
                PK._live_bar()
                self.assertEqual(len(reads), 1)                               # the same minute, the same file
                t[0] += 61
                PK._live_bar()
                self.assertEqual(len(reads), 2)                               # a new minute: read again
                HB.write(cal(question_version="another", measured_at=now.isoformat()), path)
                os.utime(path, ns=(1, 1))                                      # the file changed (its mtime moved)
                live, why = PK._live_bar()
                self.assertEqual((live, len(reads)), (None, 3))               # read at once: no hook passes
                self.assertIn("no hook passes until it is re-run", why)
            PK._LIVE.clear()


class TestTheLiveCalibration(unittest.TestCase):
    """The calibration production reads (pipeline/hook_calibration.json): its floors are derived from their source
    (tests/package/proof/hook113/ALONE_TEST.json: Grok asked alone at seed 7; the two out-of-contract first answers
    asked once more), and it is for production's question version, seed and hook list."""
    real_hook_bar = True

    def test_its_floors_are_its_sources_lowest_parts(self):
        c, why = HB.load()
        self.assertIsNone(why)
        with open(os.path.join(REPO, "tests", "package", "proof", "hook113", "ALONE_TEST.json")) as f:
            src = json.load(f)
        grok = dict(src["models"][c["rater"]], **src["retries"])          # a retry answers for an out-of-contract ask
        self.assertEqual(sorted(a["ref"] for a in c["approved"]), sorted(grok))
        for a in c["approved"]:
            self.assertEqual({p: a[p] for p in HB.PARTS}, {p: grok[a["ref"]][p] for p in HB.PARTS}, a["ref"])
            self.assertEqual(grok[a["ref"]]["backend"], c["rater"])
        self.assertEqual(HB.floors_from(c["approved"]), (c["floors"], c["floors_below_3"]))
        self.assertEqual((c["seed"], c["asking"]), (src["seed"], "alone"))

    def test_it_is_for_productions_question_seed_and_hook_list(self):
        import providers as P
        c, _ = HB.load()
        self.assertEqual((c["question_version"], c["seed"]), (PK.HOOK_VERSION, PK.HOOK_SEED))
        for routing in P.ROUTINGS:
            r = P.Router(env_path="/nonexistent", routing=routing)
            self.assertEqual(r.chain("coherence_verdict", "hook"), [c["rater"]], routing)


if __name__ == "__main__":
    unittest.main()
