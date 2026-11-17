#!/usr/bin/env python3
"""RULING 107 (1) (orchestrator 20:20 ET Nov 14): "a build that judges nothing new must cost $0.00". The build driver
fingerprints its inputs before any model is asked (proof_ledger.fingerprint), and stops with no router and no call
when they equal the newest finished build's and that build left nothing undone (nothing_new, open_work). Offline:
temporary proof directories; the driver test stubs the ledger reads and makes building a router an error."""
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import proof_ledger as PLG  # noqa: E402

NOW = datetime(2026, 11, 14, 22, 0, tzinfo=timezone.utc)                  # 17:00 ET
POOL = [{"moment_id": "m1", "video_id": "vidZZZZZZZ1", "text": "Bitcoin is a bearer asset.", "start": 1.0, "end": 9.0},
        {"moment_id": "m2", "video_id": "vidZZZZZZZ2", "text": "Self custody matters.", "start": 3.0, "end": 12.0}]
PINS = [{"story_id": "s1"}]
DELIVERED = [{"video_id": "old", "start": 0.0, "end": 5.0}]
SINCE = datetime(2026, 11, 13, 3, 1, 9, tzinfo=timezone.utc)


class Paths(unittest.TestCase):
    """Every file the fingerprint reads, in a temporary directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        self.res, self.spot, self.dirs, self.scorer = (os.path.join(d, "results"), os.path.join(d, "SPOTLIGHTS.json"),
                                                       os.path.join(d, "DIRECTIVES.json"), os.path.join(d, "latest.json"))
        os.makedirs(self.res)
        for p, body in ((self.spot, "[]"), (self.dirs, '{"directives": []}'), (self.scorer, '{"verdicts": {}}')):
            open(p, "w").write(body)
        self.patches = [mock.patch.object(PLG.LP, "RESULTS", self.res), mock.patch.object(PLG, "SPOTLIGHTS", self.spot),
                        mock.patch.object(PLG, "DIRECTIVES", self.dirs),
                        mock.patch.object(PLG.PK, "SCORER_VERDICTS", self.scorer)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def fp(self, pool=POOL, delivered=DELIVERED, pins=PINS, since=SINCE, now=NOW, reg=None):
        return PLG.fingerprint(pool, delivered, pins, since, now, reg or PLG.CA.new_registry())


class TestFingerprint(Paths):
    def test_the_same_inputs_give_the_same_fingerprint(self):
        self.assertEqual(self.fp()[0], self.fp(pool=copy.deepcopy(POOL))[0])
        later = NOW + timedelta(hours=3)                                     # still 14 Nov ET
        self.assertEqual(self.fp()[0], self.fp(now=later)[0])

    def test_every_input_moves_it(self):
        base = self.fp()[0]
        pool = copy.deepcopy(POOL)
        pool[0]["text"] = "Bitcoin is a bearer instrument."
        self.assertNotEqual(self.fp(pool=pool)[0], base, "a word of a moment")
        self.assertNotEqual(self.fp(pool=POOL + [dict(POOL[0], moment_id="m3")])[0], base, "a new moment")
        self.assertNotEqual(self.fp(delivered=DELIVERED + [{"video_id": "x", "start": 1, "end": 2}])[0], base,
                            "a delivered span")
        self.assertNotEqual(self.fp(pins=[{"story_id": "s2"}])[0], base, "a delivered pin")
        self.assertNotEqual(self.fp(since=SINCE + timedelta(hours=1))[0], base, "since")
        self.assertNotEqual(self.fp(now=NOW + timedelta(hours=8))[0], base, "the ET day (the show date)")   # 01:00 ET Nov 15
        reg = PLG.CA.new_registry()
        reg["candidates"]["a+b+c"] = {"lineup": ["a", "b", "c"], "source": "r", "index": 0, "state": "closed",
                                      "found_at": "2026-11-14T10:00:00+00:00", "until": None, "fresh_used": False,
                                      "history": []}
        self.assertNotEqual(self.fp(reg=reg)[0], base, "the registry")
        for path, body, what in ((self.spot, '[{"channel_id": "c"}]', "the spotlights record"),
                                 (self.dirs, '{"directives": [{"parent": "x"}]}', "a directive"),
                                 (self.scorer, '{"verdicts": {"t": 4}}', "the clip scorer's verdicts")):
            was = open(path).read()
            open(path, "w").write(body)
            self.assertNotEqual(self.fp()[0], base, what)
            open(path, "w").write(was)
        self.assertEqual(self.fp()[0], base)
        with mock.patch.object(PLG, "code_content", lambda *a, **k: "other code"):
            self.assertNotEqual(self.fp()[0], base, "the code")
        self.assertNotEqual(PLG.fingerprint(POOL, DELIVERED, PINS, SINCE, NOW, PLG.CA.new_registry(), "today")[0],
                            PLG.fingerprint(POOL, DELIVERED, PINS, SINCE, NOW, PLG.CA.new_registry(), "heimdall_first")[0],
                            "the routing")

    def test_a_precheck_result_moves_it_only_for_a_video_of_the_pool(self):
        base = self.fp()[0]
        open(os.path.join(self.res, "otherVideo1.0.000-9.000.a4c307f78c94.json"), "w").write("[]")
        self.assertEqual(self.fp()[0], base)                                 # another video's answer: not this pool
        open(os.path.join(self.res, "vidZZZZZZZ1.1.000-9.000.a4c307f78c94.json"), "w").write("[]")
        self.assertNotEqual(self.fp()[0], base)                              # an answer for the pool

    def test_a_resting_candidate_coming_due_moves_it(self):
        reg = PLG.CA.new_registry()
        reg["candidates"]["a+b+c"] = {"lineup": ["a", "b", "c"], "source": "r", "index": 0, "state": "resting",
                                      "found_at": "2026-11-14T10:00:00+00:00", "until": "2026-11-14T23:00:00+00:00",
                                      "fresh_used": False, "history": []}
        before, after = self.fp(reg=reg)[0], self.fp(reg=reg, now=NOW + timedelta(hours=1, minutes=30))[0]
        self.assertNotEqual(before, after)                                   # 18:30 ET: its 6 h are over

    def test_the_code_is_read_by_content_not_by_commit(self):
        self.assertEqual(PLG.code_content(), PLG.code_content())
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "pipeline"))
            os.makedirs(os.path.join(d, "drv"))
            open(os.path.join(d, "pipeline", "a.py"), "w").write("x = 1\n")
            open(os.path.join(d, "drv", "proof_x.py"), "w").write("y = 1\n")
            open(os.path.join(d, "drv", "test_x.py"), "w").write("z = 1\n")
            one = PLG.code_content(d, os.path.join(d, "drv"))
            open(os.path.join(d, "drv", "test_x.py"), "w").write("z = 2\n")
            self.assertEqual(PLG.code_content(d, os.path.join(d, "drv")), one)      # a test is not the build's code
            open(os.path.join(d, "pipeline", "a.py"), "w").write("x = 2\n")
            self.assertNotEqual(PLG.code_content(d, os.path.join(d, "drv")), one)


class TestOpenWorkAndNothingNew(unittest.TestCase):
    def test_open_work_counts_what_a_build_left_undone(self):
        self.assertEqual(PLG.open_work({"prescreen": {}, "visual": {}}, {}), 0)
        self.assertEqual(PLG.open_work({"prescreen": {"held_102": {"first": ["a"], "second": ["b", "c"]}}},
                                       {"held_102": ["d"]}), 4)
        self.assertEqual(PLG.open_work({"tried": [{"precheck": {"segments": [{"verdict": "error"}]}}]}, {}), 1)
        self.assertEqual(PLG.open_work({}, {"lock_stop": {"segments": [{"verdict": "error"}]}}), 1)
        self.assertEqual(PLG.open_work({"visual": {"unmeasured": 2}}, {}), 2)
        self.assertEqual(PLG.open_work({"a": [{"b": {"verdict": "error"}}, {"verdict": "pass"}]}, {}), 1)   # nested
        self.assertEqual(PLG.open_work({"why": 'a log line quoting "verdict": "error"'}, {}), 0)   # a string is no verdict

    def test_money_refused_calls_and_the_never_empty_pass_holds_are_left_undone(self):
        """Build 134 (12:57 ET Nov 17) asked nothing: free build 133's two clips-alone verdicts, refused at its $0.00
        stop, were not counted as undone, and the never-empty pass's own record was not read."""
        self.assertEqual(PLG.open_work({}, {}, ["xai:grok", "xai:grok"]), 2)      # each refused call
        self.assertEqual((PLG.open_work({}, {}, ()), PLG.open_work({}, {}, None)), (0, 0))

        def soft(first, second):
            return {"never_empty": {"soft_record": {"prescreen": {"held_102": {"first": first, "second": second}}}}}
        self.assertEqual(PLG.open_work(soft(["a"], ["b"]), {}), 2)                # the soft pass's own holds
        both = dict(soft(["a"], ["b", "c"]), prescreen={"held_102": {"first": ["a"], "second": ["b"]}})
        self.assertEqual(PLG.open_work(both, {}), 3)      # a and b once (the clean pass held them too), c new
        self.assertEqual(PLG.open_work(dict(both, never_empty=None), {}, ["x"]), 3)   # no soft pass: clean + money
        self.assertEqual(PLG.open_work({"never_empty": {"stage": "2a"}}, {}), 0)      # a soft pass that held nothing

    def test_only_the_newest_finished_build_counts(self):
        with tempfile.TemporaryDirectory() as d:
            def build(name, fp=None, left=0):
                os.makedirs(os.path.join(d, name))
                if fp is not None:
                    json.dump({"fingerprint": fp, "open_work": left, "build": name},
                              open(os.path.join(d, name, PLG.FINGERPRINT), "w"))
            me = os.path.join(d, "ledger_20261114_230000")
            self.assertIsNone(PLG.nothing_new(d, me, "F"))                  # no earlier build
            build("ledger_20261114_200000", "F")
            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")
            build("ledger_20261114_210000")                                  # no FINGERPRINT (stopped, skipped, or a
            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_200000")   # candidate's): passed over
            build("ledger_20261114_220000", "G")                             # the newest finished build differs
            self.assertIsNone(PLG.nothing_new(d, me, "F"))
            build("ledger_20261114_221000", "F", left=1)                     # the same, but it left work undone
            self.assertIsNone(PLG.nothing_new(d, me, "F"))
            os.makedirs(me)
            json.dump({"fingerprint": "F", "open_work": 0}, open(os.path.join(me, PLG.FINGERPRINT), "w"))
            self.assertIsNone(PLG.nothing_new(d, me, "F"))                   # never this build itself
            build("ledger_20261114_222000", "F")
            open(os.path.join(d, "ledger_20261114_222500", PLG.FINGERPRINT) if os.makedirs(
                os.path.join(d, "ledger_20261114_222500")) is None else "", "w").write("{not json")
            self.assertEqual(PLG.nothing_new(d, me, "F"), "ledger_20261114_222000")   # an unreadable one is passed


class TestTheDriverAsksNoModel(Paths):
    """The driver itself: with the newest finished build's fingerprint equal to this one's and nothing left undone, it
    stops before any router exists (building one is an error here); with work left undone, it goes on to the router."""
    PIN_PATHS = [os.path.join(HERE, "proof", "fresh_20261112_050611", n) for n in ("MOMENTS_PIN.json",
                                                                                  "MOMENTS_PIN_LY.json")]

    def run_driver(self, left, wp_rep=None, seen=None, rows=None):
        """wp_rep: the word pass's report the stubbed index gives; seen: filled with build_inputs' keyword arguments;
        rows: the ledger rows the stubbed adapter gives (default none)."""
        proof = os.path.join(self.tmp.name, "drv", "proof")
        os.makedirs(proof)
        delivered, last, pins = PLG.delivered_pins(self.PIN_PATHS)
        fp, _ = PLG.fingerprint(copy.deepcopy(POOL), delivered, pins, last, datetime.now(timezone.utc),
                                PLG.CA.new_registry())
        prev = os.path.join(proof, "ledger_20000101_000000")
        os.makedirs(prev)
        json.dump({"fingerprint": fp, "open_work": left, "build": "ledger_20000101_000000"},
                  open(os.path.join(prev, PLG.FINGERPRINT), "w"))

        class Built(Exception):
            pass

        def no_router(*a, **k):
            raise Built("a router was built")

        def inputs(*a, **k):
            (seen if seen is not None else {}).update(k)
            return copy.deepcopy(POOL), {}, {}
        stubs = [mock.patch.object(PLG, "HERE", os.path.join(self.tmp.name, "drv")),
                 mock.patch.object(PLG, "REGISTRY", os.path.join(proof, "CANDIDATES.json")),
                 mock.patch.object(PLG.PS, "ledger_entries", lambda *a, **k: []),
                 mock.patch.object(PLG.LB, "rows", lambda *a, **k: (list(rows or []), {"excluded": {}})),
                 mock.patch.object(PLG.LB, "word_pass_index", lambda *a, **k: ({}, dict(wp_rep or {"rows": 0}))),
                 mock.patch.object(PLG.LB, "build_inputs", inputs),
                 mock.patch.object(PLG, "with_variants", lambda moments, *a, **k: moments),
                 mock.patch.object(PLG, "build_router", no_router),
                 mock.patch("sys.stdout", new=io.StringIO())]
        for s in stubs:
            s.start()
        try:
            try:
                rc = PLG.main(["--delivered", *self.PIN_PATHS])
            except Built:
                rc = "router"
        finally:
            for s in stubs:
                s.stop()
        runs = sorted(n for n in os.listdir(proof) if n.startswith("ledger_") and n != "ledger_20000101_000000")
        return rc, [os.path.join(proof, n) for n in runs]

    def test_nothing_new_stops_before_any_router_and_costs_nothing(self):
        rc, runs = self.run_driver(left=0)
        self.assertEqual(rc, 0)
        self.assertEqual(len(runs), 1)
        rec = json.load(open(os.path.join(runs[0], PLG.NOTHING_NEW)))
        self.assertEqual(rec["same_as"], "ledger_20000101_000000")
        self.assertIn("NOTHING NEW (ruling 107 (1))", open(os.path.join(runs[0], "package.log")).read())
        self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.FINGERPRINT)))   # a skip never stands for a build

    def test_the_word_pass_refused_reach_the_inputs_and_the_log_gives_their_count(self):
        seen = {}
        rc, runs = self.run_driver(left=0, wp_rep={"rows": 2, "ready": 0, "refused": ["Xa1", "Yb2"]}, seen=seen)
        self.assertEqual((rc, seen.get("word_pass_refused")), (0, ["Xa1", "Yb2"]))
        log = open(os.path.join(runs[0], "package.log")).read()
        self.assertIn('"refused": 2', log)                                   # the count; the ids stay in inputs.json
        self.assertNotIn("Xa1", log)
        self.assertEqual(json.load(open(os.path.join(runs[0], "inputs.json")))["inputs"]["word_pass"]["refused"],
                         ["Xa1", "Yb2"])

    def test_ruling_95_counts_the_refused_from_the_inputs_alone(self):
        """Ruling 95 reads the inputs beside build_inputs (before main() rebinds any name for the spend check), and
        inputs.json records it, even for a build that stops with nothing new."""
        at = datetime.now(timezone.utc).isoformat()
        rows = [{"video_id": "v1", "channel_name": "Talk", "published_at": at, "moment_id": m,
                 "episode": {"turns_per_min": 2.0}, "mined": {"pass": "moment", "prompt_version": "mine/2"}}
                for m in ("Xa1", "Yb2", "Zc3")]
        rc, runs = self.run_driver(left=0, wp_rep={"rows": 2, "ready": 0, "refused": ["Xa1", "Yb2"]}, rows=rows)
        na = json.load(open(os.path.join(runs[0], "inputs.json")))["next_attempt"]["conversation"]
        self.assertEqual((rc, na["rows"], na["word_pass_ready"], na["word_pass_refused"], na["word_pass_waiting"]),
                         (0, 3, 0, 2, 1))

    def test_work_left_undone_goes_on_to_the_router(self):
        rc, runs = self.run_driver(left=1)
        self.assertEqual(rc, "router")
        self.assertFalse(os.path.exists(os.path.join(runs[0], PLG.NOTHING_NEW)))


if __name__ == "__main__":
    unittest.main()
