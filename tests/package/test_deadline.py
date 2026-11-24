#!/usr/bin/env python3
"""R3 (build 172, the owner's 15:25 ET Nov 24 order): ONE deadline. The builder's side, offline (every model a stub):
  - the router starts no call whose own deadline would end past the build's (DeadlineStopped; the back-end never
    asked), and none once it has passed; without a deadline, as before;
  - the lock pre-check waits at most the time left; an answer still missing when the deadline comes stops the build
    (UNVERIFIED, never a pass);
  - at its deadline the driver stops wherever it is and still writes its ONE outcome line, DEADLINE_STOPPED, with its
    time per stage; a seal (a pin) written before it stands; nothing seals after it;
  - DEADLINE_STOPPED is its own outcome word, apart from every other."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package"):
    sys.path.insert(0, os.path.join(REPO, _p))
import outcomes as OC  # noqa: E402
import providers as P  # noqa: E402

GROK = "xai:grok-4.20-0309-reasoning"
HEIMDALL = "heimdall:qwen/qwen3.8-27b"


class TheRouter(unittest.TestCase):
    def router(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        r = P.Router(spend_path=os.path.join(d, "L.json"), limit_usd=1.5, limit_basis="reported",
                     uncapped=("heimdall",), chains={"coherence_verdict": [GROK]})
        self.asked = []

        def complete(prompt, max_tokens, seed, system=None):
            self.asked.append(prompt)
            return '{"ok": true}', {"in": 10, "out": 10, "usd_reported": 0.011}, 0.1
        r.backends[GROK].complete = complete
        return r

    def test_a_call_that_could_not_end_inside_the_budget_is_not_started(self):
        r = self.router()
        r.deadline_at = time.time() + 30                 # 30 s left; the call's own deadline is 120 s
        with self.assertRaises(P.DeadlineStopped):
            r.call("coherence_verdict", "x" * 3000, 1200, 7, deadline_s=120)
        self.assertEqual(self.asked, [])
        r.call("coherence_verdict", "x" * 3000, 1200, 7, deadline_s=20)      # one that fits goes ahead
        self.assertEqual(len(self.asked), 1)
        r.deadline_at = time.time() - 1                  # past it: nothing starts
        with self.assertRaises(P.DeadlineStopped):
            r.call("coherence_verdict", "x" * 3001, 1200, 8, deadline_s=5)
        self.assertEqual(len(self.asked), 1)

    def test_no_deadline_as_before(self):
        r = self.router()
        r.call("coherence_verdict", "x" * 3000, 1200, 7, deadline_s=120)
        self.assertEqual(len(self.asked), 1)

    def test_it_is_never_read_as_a_failure_or_a_verdict(self):
        """DeadlineStopped is a BaseException: an `except Exception` on the way (a verdict's fallback) never swallows
        it into "no answer, go on"."""
        self.assertFalse(issubclass(P.DeadlineStopped, Exception))
        r = self.router()
        r.deadline_at = time.time() - 1
        with self.assertRaises(P.DeadlineStopped):
            try:
                r.call("coherence_verdict", "x", 100, 7, deadline_s=5)
            except Exception:                            # noqa: BLE001  what an editorial fallback does
                self.fail("swallowed")


class TheLockWait(unittest.TestCase):
    def test_the_wait_is_the_time_left_and_a_missing_answer_at_the_deadline_stops(self):
        import proof_ledger as PLG
        seen = []

        def check(segs, rid, log=print, timeout_s=None, **k):
            seen.append(timeout_s)
            time.sleep(min(timeout_s, 0.4))
            return {"ok": False, "request_id": rid, "segments": [], "error": "x 1.0-2.0: no verdict"}
        with mock.patch.object(PLG.LP, "check", check):
            far = PLG.lock_for("on", "/tmp/ledger_x", print, deadline_at=time.time() + 3600)
            self.assertEqual(far([{}])["error"], "x 1.0-2.0: no verdict")     # far from it: as before (no pass)
            self.assertEqual(seen[-1], PLG.LP.TIMEOUT_S)
            near = PLG.lock_for("on", "/tmp/ledger_x", print, deadline_at=time.time() + 0.3)
            with self.assertRaises(P.DeadlineStopped) as c:
                near([{}])
            self.assertLessEqual(seen[-1], 0.3)
            self.assertIn("UNVERIFIED", str(c.exception))
            with self.assertRaises(P.DeadlineStopped):  # past it: not even asked
                near([{}])
            self.assertEqual(len(seen), 2)
        self.assertIs(PLG.lock_for("off", "/tmp/x", print, deadline_at=time.time() - 9), PLG.lock_off)

    def test_nothing_seals_after_the_deadline(self):
        import proof_ledger as PLG
        PLG.past_deadline(None, "seal")
        PLG.past_deadline(time.time() + 60, "seal")
        with self.assertRaises(P.DeadlineStopped):
            PLG.past_deadline(time.time() - 0.001, "seal")


class TheDriverStopsAndRecords(unittest.TestCase):
    def driver(self, body):
        import proof_ledger as PLG
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p, out = os.path.join(d, "outcomes.jsonl"), os.path.join(d, "ledger_20261125_030000")

        def fake(argv, box):
            os.makedirs(out)
            box["out_dir"] = out
            box["deadline_at"] = PLG.arm_deadline(time.time() + 0.5)
            return body(out, box)
        with mock.patch.object(OC, "OUTCOMES", p), mock.patch.object(PLG, "_main", fake):
            t0 = time.time()
            try:
                rc = PLG.main([])
            except P.DeadlineStopped as e:
                rc = e
            return rc, OC.lines(p), time.time() - t0

    def test_at_its_deadline_the_build_stops_where_it_is_and_writes_its_one_line(self):
        """MUST-FAIL: a build still in its line-ups (a 30 s wait) at its deadline (0.5 s): it stops there, inside a
        second, and its ONE outcome line says DEADLINE_STOPPED at "line-ups" with its time per stage."""
        def body(out, box):
            box["clock"].mark("  step A: 3 moments")
            box["clock"].mark("  angle 1 line-up: asked")
            time.sleep(30)
            return 0
        rc, ls, secs = self.driver(body)
        self.assertIsInstance(rc, P.DeadlineStopped)
        self.assertLess(secs, 5)
        x, = ls
        self.assertEqual((x["outcome"], x["stage"]), ("DEADLINE_STOPPED", "line-ups"))
        self.assertIn("line-ups", x["seconds"])
        self.assertGreater(x["seconds"]["line-ups"], 0.3)
        self.assertEqual(x["note"], OC.NOTE_DEFAULT["DEADLINE_STOPPED"])

    def test_a_pin_sealed_before_the_deadline_stands(self):
        def body(out, box):
            with open(os.path.join(out, "MOMENTS_PIN_LEDGER.json"), "w") as f:
                json.dump({"story_id": "S-00000001", "moments_package": {"package_sha256": "a" * 64}}, f)
            time.sleep(30)
            return 0
        rc, ls, _ = self.driver(body)
        self.assertEqual([x["outcome"] for x in ls], ["SEALED"])

    def test_a_build_that_ends_first_is_not_stopped_later(self):
        def body(out, box):
            json.dump({"same_as": "ledger_x"}, open(os.path.join(out, "NOTHING_NEW.json"), "w"))
            return 0
        rc, ls, _ = self.driver(body)
        time.sleep(0.8)                                  # past the 0.5 s: the alarm was disarmed at the end
        self.assertEqual((rc, [x["outcome"] for x in ls]), (0, ["NO_ELIGIBLE_STORY"]))


class TheWord(unittest.TestCase):
    def test_deadline_stopped_is_its_own_outcome(self):
        self.assertIn("DEADLINE_STOPPED", OC.KINDS)
        self.assertIn("DEADLINE_STOPPED", OC.BUILDER_KINDS)
        self.assertEqual(len(set(OC.KINDS)), len(OC.KINDS))
        for st in ("render", "delivery"):
            self.assertIn(("DEADLINE_STOPPED", st), OC.NOTES)

    def test_the_launch_s_render_and_delivery_on_the_one_line(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "o.jsonl")
        for run in ("r1", "r2", "r3"):
            OC.write_once({"side": "builder", "run": run, "outcome": "SEALED", "stage": "seal", "seconds": {}}, p)
        a = OC.amend_stage("r1", "render", OC.DEADLINE_EXIT, 1380.0, "pin", "", path=p)
        self.assertEqual((a["outcome"], a["stage"], a["seconds"]["render"]), ("DEADLINE_STOPPED", "render", 1380.0))
        b = OC.amend_stage("r2", "render", 3, 3400.0, "pin", "HOLD", path=p)            # held by its own gates
        self.assertEqual((b["outcome"], b["render"]["exit"]), ("SEALED", 3))
        OC.amend_stage("r3", "render", 0, 2000.0, "pin", "", path=p)
        c = OC.amend_stage("r3", "delivery", OC.DEADLINE_EXIT, 120.0, "pin", path=p)
        self.assertEqual((c["outcome"], c["stage"], sorted(c["seconds"])), ("DEADLINE_STOPPED", "delivery",
                                                                            ["delivery", "render"]))
        self.assertEqual(len(OC.lines(p)), 3)                                         # still one line a run


if __name__ == "__main__":
    unittest.main()
