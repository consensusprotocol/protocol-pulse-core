#!/usr/bin/env python3
"""RULING 99 (orchestrator 10:48 ET Nov 14), THE CIRCUIT BREAKER (pipeline/circuit_breaker.py and its use in
providers.Router and the ledger build). Offline: a temporary state file, the test's own clock, fake back-ends."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import circuit_breaker as CB  # noqa: E402
import providers as P  # noqa: E402
from test_providers import Fake, Slow, router, wait_for  # noqa: E402

T0 = datetime(2026, 11, 14, 15, 0, tzinfo=timezone.utc)
GLM = "heimdall:z-ai/glm-5.3-flash"


def at(minutes=0, seconds=0):
    return T0 + timedelta(minutes=minutes, seconds=seconds)


class TestBreaker(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.d.name, "BREAKERS.json")

    def tearDown(self):
        self.d.cleanup()

    def rec(self, outcome, t, **kw):
        return CB.record(GLM, outcome, self.state, now=t, **kw)

    def test_two_deadline_misses_in_a_row_open_it_for_30_minutes(self):
        self.assertIsNone(self.rec("miss", at(0)))
        self.assertIsNone(self.rec("answer", at(1)))                      # an answer between: not in a row
        self.assertIsNone(self.rec("miss", at(2)))
        ev = self.rec("miss", at(3), deadline_s=120.0, seconds=120.0, max_out=16000)
        self.assertEqual({k: ev[k] for k in ("kind", "model", "why", "until", "deadline_s", "seconds", "tokens",
                                             "max_out", "utc")},
                         {"kind": "breaker_open", "model": GLM, "why": "missed its deadline 2 times in a row",
                          "until": "2026-11-14T15:33:00Z", "deadline_s": 120.0, "seconds": 120.0, "tokens": None,
                          "max_out": 16000, "utc": "2026-11-14T15:03:00Z"})
        ok, why = CB.allow(GLM, self.state, now=at(32, 59))
        self.assertFalse(ok)
        self.assertIn("open until 2026-11-14T15:33:00Z", why)
        self.assertEqual(CB.allow("heimdall:deepseek/deepseek-v4.1-flash", self.state, now=at(4)), (True, None))

    def test_after_30_minutes_one_trial_an_answer_closes_it_and_a_miss_reopens_it_for_60(self):
        self.rec("miss", at(0))
        self.rec("miss", at(1))                                           # open until 15:31
        self.assertEqual(CB.allow(GLM, self.state, now=at(31)), (True, "trial"))
        ok, why = CB.allow(GLM, self.state, now=at(31, 1))                # one trial at a time
        self.assertFalse(ok)
        self.assertIn("trial call is in flight", why)
        ev = self.rec("answer", at(32))
        self.assertEqual((ev["kind"], ev["why"]), ("breaker_close", "the trial call answered"))
        self.assertEqual(CB.allow(GLM, self.state, now=at(33)), (True, None))
        self.rec("miss", at(40))
        self.rec("miss", at(41))                                          # open again until 16:11
        self.assertEqual(CB.allow(GLM, self.state, now=at(71)), (True, "trial"))
        ev = self.rec("miss", at(73))                                     # the trial misses: 60 minutes
        self.assertEqual((ev["kind"], ev["until"], ev["why"]),
                         ("breaker_open", "2026-11-14T17:13:00Z", "the trial call missed its deadline"))
        self.assertFalse(CB.allow(GLM, self.state, now=at(132, 59))[0])
        self.assertEqual(CB.allow(GLM, self.state, now=at(133)), (True, "trial"))
        self.assertEqual(json.load(open(self.state))["models"][GLM]["opens"], 3)

    def test_a_runaway_opens_it_at_once(self):
        ev = self.rec("runaway", at(0), tokens=40000, max_out=16000)
        self.assertEqual((ev["kind"], ev["why"], ev["tokens"]),
                         ("breaker_open", "returned more than 2x the cap it was sent", 40000))
        self.assertEqual(CB.allow(GLM, self.state, now=at(30)), (True, "trial"))
        ev = self.rec("runaway", at(31), tokens=40000, max_out=16000)   # a trial that runs away re-opens it too
        self.assertEqual((ev["why"], ev["until"]),
                         ("the trial call returned more than 2x the cap it was sent", "2026-11-14T16:31:00Z"))

    def test_calls_in_flight_when_it_opened_change_nothing_and_a_dead_trial_is_freed(self):
        self.rec("miss", at(0))
        self.rec("miss", at(0, 30))                                       # open until 15:30:30
        self.assertIsNone(self.rec("miss", at(5)))                        # calls from before it opened: two misses
        self.assertIsNone(self.rec("miss", at(5, 30)))                    # never extend or re-open the window
        self.assertIsNone(self.rec("answer", at(6)))                      # an answer inside the window: still open
        self.assertEqual(json.load(open(self.state))["models"][GLM]["open_until"], "2026-11-14T15:30:30Z")
        self.assertEqual(CB.allow(GLM, self.state, now=at(31)), (True, "trial"))   # no deadline given: held for
        self.assertFalse(CB.allow(GLM, self.state, now=at(45, 59))[0])    # TRIAL_HOLD_S, then freed (its caller's
        self.assertEqual(CB.allow(GLM, self.state, now=at(46), hold_s=180.0), (True, "trial"))   # process ended)
        self.assertFalse(CB.allow(GLM, self.state, now=at(48, 59))[0])    # a Heimdall leg: its 120 s + 60 s
        self.assertEqual(CB.allow(GLM, self.state, now=at(49), hold_s=2460.0), (True, "trial"))
        self.assertFalse(CB.allow(GLM, self.state, now=at(89, 59))[0])    # the local judge's 2400 s + 60 s: one trial
        self.assertEqual(CB.allow(GLM, self.state, now=at(90)), (True, "trial"))     # at a time all the same

    def test_the_count_for_state_line_1_and_an_unreadable_state_is_never_guessed(self):
        self.rec("miss", at(0))
        self.rec("miss", at(1))
        CB.allow(GLM, self.state, now=at(31))
        self.rec("answer", at(32))
        self.rec("runaway", at(40), tokens=40000, max_out=16000)
        st = json.load(open(self.state))
        st["events"].append({"kind": "breaker_open", "model": "x", "utc": "garbage"})   # a time that cannot be read
        json.dump(st, open(self.state, "w"))
        s = CB.summary(self.state, now=at(41))
        self.assertEqual((s["opens"], s["closes"], [o["model"] for o in s["open"]]), (2, 1, [GLM]))   # not counted
        self.assertEqual(CB.summary(self.state, now=at(41), since=at(35))["opens"], 1)
        with open(self.state, "w") as f:
            f.write("{ broken")
        for fn in (lambda: CB.allow(GLM, self.state, now=at(50)), lambda: self.rec("miss", at(50)),
                   lambda: CB.summary(self.state, now=at(50))):
            with self.assertRaises(CB.BreakerUnreadable):
                fn()
        self.assertEqual(open(self.state).read(), "{ broken")
        json.dump({"models": {GLM: {"open_until": "soon"}}}, open(self.state, "w"))
        self.assertEqual(CB.allow(GLM, self.state, now=at(50)), (True, None))   # a malformed record skips nothing
        json.dump({"models": {GLM: {"open_until": "2026-11-14T15:00:00Z", "trial_at": "garbage"}}}, open(self.state, "w"))
        self.assertEqual(CB.allow(GLM, self.state, now=at(50)), (True, "trial"))   # a malformed trial: no crash
        with self.assertRaises(ValueError):
            self.rec("slow", at(51))


class TestRouterBreaker(unittest.TestCase):
    """providers.Router: live calls only. Two real deadline misses (P._within) open the breaker, the next family leads,
    and the open is one line in the evidence file."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.d.name, "BREAKERS.json")
        self.log = os.path.join(self.d.name, "DEADLINES.jsonl")

    def tearDown(self):
        self.d.cleanup()

    def mk(self, backends, chain, **kw):
        return router(self.d.name, backends, {"check": chain, "probe87:" + chain[0]: [chain[0]]}, deadline_log=self.log,
                      breakers=self.state, **kw)

    def test_two_misses_skip_glm_and_the_next_family_leads(self):
        glm = Slow(GLM, "heimdall", '{"ok": 1}', delay=0.4, family="glm")
        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
        self.assertEqual([r.call("check", f"p{i}", 100, 7, deadline_s=0.1).backend for i in range(2)],
                         ["heimdall:deepseek"] * 2)
        rep = r.call("check", "p3", 100, 7, deadline_s=0.1)
        import time as _t
        for _ in range(300):                                              # the two abandoned calls end on their clock
            if glm.calls >= 2:
                break
            _t.sleep(0.01)
        _t.sleep(0.2)
        self.assertEqual((rep.backend, glm.calls), ("heimdall:deepseek", 2))      # glm not asked a third time
        self.assertIn("circuit breaker open until", dict(rep.tried)[GLM])
        self.assertEqual([e["kind"] for e in r.breaker_events], ["breaker_open"])
        opened = [x for x in wait_for(self.log, "breaker_open") if x["kind"] == "breaker_open"]
        self.assertEqual({k: opened[0][k] for k in ("model", "deadline_s", "seconds", "max_out", "role")},
                         {"model": GLM, "deadline_s": 0.1, "seconds": 0.1, "max_out": 100, "role": "check"})
        self.assertEqual(r.call("probe87:" + GLM, "Reply with the single word OK.", 64, 7).backend, GLM)  # a probe:
        #   asked all the same, and never counted (ruling 87's probe is not a list)
        st = json.load(open(self.state))
        st["models"][GLM]["open_until"] = "2026-01-01T00:00:00Z"          # the window has passed: the next call is
        json.dump(st, open(self.state, "w"))                              # the one trial, held for its deadline + 60 s
        self.assertIsNone(r._breaker_allow("check", GLM, 0.1))           # this call is the trial (claimed here)
        m = json.load(open(self.state))["models"][GLM]
        held = (CB._t(m["trial_until"]) - CB._t(m["trial_at"])).total_seconds()
        self.assertIn(held, (60.0, 61.0))
        self.assertIn("trial call is in flight", r._breaker_allow("check", GLM, 0.1))     # one trial at a time

    def test_a_runaway_answer_opens_it_and_a_recorded_reply_is_still_served(self):
        glm = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm", usage={"in": 10, "out": 201})   # > 2 x 100
        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"], record_dir=os.path.join(self.d.name, "rec"))
        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # it answered: the answer stands
        self.assertEqual([e["why"] for e in r.breaker_events], ["returned more than 2x the cap it was sent"])   # once
        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # its recorded reply: served, nothing paid
        self.assertEqual(glm.calls, 1)
        self.assertEqual(r.call("check", "q", 100, 7).backend, "heimdall:deepseek")   # a live call: skipped
        glm2 = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm", usage={"in": 10, "out": 200})  # exactly 2x
        r2 = self.mk([glm2, ds], [GLM, "heimdall:deepseek"])
        os.remove(self.state)
        r2.call("check", "p", 100, 7)
        self.assertEqual(r2.breaker_events, [])
        healthy = Fake("heimdall:deepseek2", "heimdall", answer='{"ok": 3}', family="deepseek",
                       usage={"in": 10, "out": 1500})
        healthy.spec["min_out"] = 1000          # a reasoning model is sent its floor (as Grok and deepseek are):
        r3 = self.mk([healthy, ds], ["heimdall:deepseek2", "heimdall:deepseek"])
        self.assertEqual(r3.call("check", "z", 100, 7).backend, "heimdall:deepseek2")
        self.assertEqual(r3.breaker_events, [])  # 1500 of a 1000 cap: no runaway (15x the caller's 100 would be one)

    def test_a_late_answer_that_ran_away_opens_it(self):
        glm = Slow(GLM, "heimdall", '{"ok": 1}', delay=0.3, family="glm", usage={"in": 10, "out": 5000})
        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
        self.assertEqual(r.call("check", "p", 100, 7, deadline_s=0.1).backend, "heimdall:deepseek")   # one miss
        log = wait_for(self.log, "breaker_open")                          # its late answer: 5000 > 2 x 100
        self.assertEqual([x["why"] for x in log if x["kind"] == "breaker_open"],
                         ["returned more than 2x the cap it was sent"])
        self.assertFalse(CB.allow(GLM, self.state)[0])

    def test_replay_never_consults_it_and_an_unreadable_state_skips_nothing(self):
        glm = Fake(GLM, "heimdall", answer='{"ok": 1}', family="glm")
        ds = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 2}', family="deepseek")
        CB.record(GLM, "runaway", self.state)                             # open now
        rr = self.mk([glm, ds], [GLM, "heimdall:deepseek"], replay=True)
        self.assertIsNone(rr._breaker_allow("check", GLM))                # replay walks its recordings only
        with open(self.state, "w") as f:
            f.write("{ broken")
        r = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
        self.assertEqual(r.call("check", "p", 100, 7).backend, GLM)       # never a skip by guess
        self.assertTrue(any("RULING 99" in n for n in r.notices))
        no = self.mk([glm, ds], [GLM, "heimdall:deepseek"])
        no.breakers = None                                                # a router given no state: no breaker
        self.assertIsNone(no._breaker_allow("check", GLM))


class TestTheBuildUsesIt(unittest.TestCase):
    def test_the_build_router_has_the_breaker_and_the_health(self):
        """The ledger build's one router (proof_ledger.build_router) is given ruling 99's state and ruling 87's."""
        sys.path.insert(0, os.path.join(REPO, "tests", "package"))
        import heimdall_health as HH
        import proof_ledger as PLG
        with tempfile.TemporaryDirectory() as d:
            r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
        self.assertEqual((r.breakers, r.health, r.routing), (CB.STATE, HH.STATE, "heimdall_first"))
        self.assertEqual(os.path.basename(CB.STATE), "BREAKERS.json")


if __name__ == "__main__":
    unittest.main()
