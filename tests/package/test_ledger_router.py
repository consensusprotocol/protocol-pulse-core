#!/usr/bin/env python3
"""The ledger build's router, as batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) found it wanting:
- proof_ly.meter observes the router's accounting and never stands between a call and its booking. Its wrapper refused
  ruling 107 Q1's `unreported` keyword, so a call abandoned at its deadline raised TypeError in place of failing over
  to the next leg; its booking never reached the ledger, its late answer was never accounted, its moments were held.
- proof_ledger.build_router waits for calls in flight (Router reserve_wait_s): step A's six workers had been refused
  whenever four reservations filled the $4.50 limit with $0.27 spent.
Offline: the real Router over fake legs, every state file of the build in a temporary folder."""
import contextlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/providers"):
    sys.path.insert(0, os.path.join(REPO, _p))
import circuit_breaker as CB  # noqa: E402
import deadline_table as DT  # noqa: E402
import heimdall_health as HH  # noqa: E402
import proof_ledger as PLG  # noqa: E402
import proof_ly as PL  # noqa: E402
import providers as P  # noqa: E402
from test_providers import Fake, SlowFail, router, wait_for  # noqa: E402
from test_reserve_wait import U, gate, run, seed, until  # noqa: E402
from test_ruling_107 import LIST, TOKENS, seed as seed107  # noqa: E402

QWEN_LIST = 1000 * 10 / 1e6 + 100 * 100 / 1e6          # Fake's list price for qwen's 1,000 in / 100 out


def metered_miss(d, **seeded):
    """One call through a METERED router: deepseek passes its 0.2 s deadline (and fails later), qwen answers with the
    vendor's own figure. -> (reply, the meter, the ledger, the deadline log once the abandoned thread has ended)."""
    spend, log = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
    seed107(spend, **seeded)
    slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.4, family="deepseek")
    qwen = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
                usage={"in": 1000, "out": 100, "usd_reported": 0.002})
    r = router(d, [slow, qwen], {"check": ["heimdall:deepseek", "heimdall:qwen"]}, spend_path=spend,
               limit_usd=50.0, limit_basis="reported", deadline_log=log)
    own = PL.meter(r)
    rep = r.call("check", "p", 100, 7, deadline_s=0.2)
    lines = wait_for(log, "late_error")                # ruling 83 (a)'s late path ran: the abandonment was booked
    return rep, own, json.load(open(spend)), lines


class TestTheMeterNeverStandsBetweenACallAndItsBooking(unittest.TestCase):

    def test_a_missed_deadline_through_the_meter_fails_over_and_is_booked(self):
        with tempfile.TemporaryDirectory() as d:
            rep, own, led, log = metered_miss(d)
            self.assertEqual((rep.text, rep.backend), ('{"ok": 2}', "heimdall:qwen"))     # failed over: no TypeError
            self.assertIn("abandoned at the deadline", rep.tried[0][1])
            self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)          # the booking is in the ledger
            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)
            self.assertEqual([x["kind"] for x in log if x["kind"] in ("missed_deadline", "late_error")],
                             ["missed_deadline", "late_error"])
            self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                  # this process's two calls

    def test_the_meter_counts_an_abandoned_call_at_the_booking_the_cap_counts(self):
        with tempfile.TemporaryDirectory() as d:        # three reported calls: deepseek's booking is at its own rate
            rep, own, led, log = metered_miss(d, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
                                              in_reported=3000)
            booked = 0.003 / 3000 * TOKENS
            self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=9)
            self.assertAlmostEqual(own["best"], booked + 0.002, places=9)                    # as the cap reads it
            self.assertAlmostEqual(own["est"], LIST + QWEN_LIST, places=9)                   # est stays list price


class TestRuling118TheBuildsRouterCapsOnlyOutsideVendors(unittest.TestCase):
    """RULING 118 (05:40 ET Nov 16): the build's router caps the outside vendors at the day's cap (proof_ly.DAY_CAP_USD,
    $1.50 since amendment C, Nov 24) and records
    Heimdall, never capping it: reaching the cap stops outside calls, not the free work."""

    def test_heimdall_runs_past_the_cap_and_an_outside_call_is_refused_at_it(self):
        with tempfile.TemporaryDirectory() as d:          # every file the build's router reads or writes is d's
            led = os.path.join(d, "SPEND.json")
            near = round(PL.DAY_CAP_USD - 0.05, 2)            # amendment C (Nov 24): the one day cap, $1.50
            json.dump({"usd_estimate": 0.0, "calls": 2, "by_backend": {
                "xai:g": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": near},
                "heimdall:q": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": 3.0}},
                "by_role": {}, "reserved": {}, "usd_reported": near + 3.0, "usd_unreported_estimate": 0.0},
                      open(led, "w"))
            with contextlib.ExitStack() as st:
                for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
                                       (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")),
                                       (HH, "STATE", os.path.join(d, "HEALTH.json")),
                                       (CB, "STATE", os.path.join(d, "BREAKERS.json")),
                                       (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
                                       (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
                    st.enter_context(mock.patch.object(mod, name, val))
                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
            h = Fake("heimdall:q", "heimdall", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.5})
            x = Fake("xai:g", "xai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.01})
            r.backends, r.chains["check"], r.chains["judge"] = {"heimdall:q": h, "xai:g": x}, ["heimdall:q"], ["xai:g"]
            self.assertAlmostEqual(r.spent(), near, places=6)      # the day's outside dollars only
            self.assertIsNone(PLG.start_refused(r.spent()))        # under the day's stop: a build may start
            self.assertEqual(r.call("check", "p" * 100_000).backend, "heimdall:q")   # its upper bound alone > the cap
            with self.assertRaises(P.SpendLimit):
                r.call("judge", "p")                               # near + its upper bound > the cap: refused at once
            self.assertEqual((h.calls, x.calls), (1, 0))
            self.assertAlmostEqual(json.load(open(led))["by_backend"]["heimdall:q"]["usd_reported"], 3.5, places=6)


class TestRuling107TheBuildsRouterNamesEveryCallItRefusedForMoney(unittest.TestCase):
    """RULING 107 (1) (build 134, 12:57 ET Nov 17): the build's router names the back-end of every paid call it refused
    for money in spend_refused, and the build records them as work left undone, so the next build is never "nothing
    new" on their account. A free call, an answered paid call or a recorded reply is no refusal."""

    def router_at(self, d, xai_spent):
        led = os.path.join(d, "SPEND.json")
        json.dump({"usd_estimate": 0.0, "calls": 1, "by_backend": {
            "xai:g": {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported": xai_spent}},
            "by_role": {}, "reserved": {}, "usd_reported": xai_spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
        with contextlib.ExitStack() as st:
            for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
                                   (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")),
                                   (HH, "STATE", os.path.join(d, "HEALTH.json")),
                                   (CB, "STATE", os.path.join(d, "BREAKERS.json")),
                                   (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
                                   (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
                st.enter_context(mock.patch.object(mod, name, val))
            r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
        h = Fake("heimdall:q", "heimdall", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
        x = Fake("xai:g", "xai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.01})
        r.backends, r.chains["check"], r.chains["judge"] = {"heimdall:q": h, "xai:g": x}, ["heimdall:q"], ["xai:g"]
        return r, led, x

    def test_each_refusal_for_money_is_named_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as d:
            r, led, x = self.router_at(d, round(PL.DAY_CAP_USD - 0.05, 2))   # near the one day cap
            self.assertEqual(r.spend_refused, [])
            r.call("check", "p")                                     # Heimdall: free, never reserved
            for n in (1, 2):
                with self.assertRaises(P.SpendLimit):
                    r.call("judge", "p")                             # near + its upper bound > the day's stop
                self.assertEqual(r.spend_refused, ["xai:g"] * n)
            self.assertEqual(x.calls, 0)
            open(led, "w").write("{not json")                        # an unreadable ledger refuses for money too
            with self.assertRaises(P.SpendLimit):
                r.call("judge", "p")
            self.assertEqual(r.spend_refused, ["xai:g"] * 3)
        with tempfile.TemporaryDirectory() as d:
            r, led, x = self.router_at(d, 0.0)
            self.assertEqual((r.call("judge", "p").backend, r.spend_refused), ("xai:g", []))   # answered: none
            self.assertEqual((r.call("judge", "p").backend, x.calls, r.spend_refused), ("xai:g", 1, []))   # replayed


class TestTheLedgerBuildsRouterWaitsForCallsInFlight(unittest.TestCase):

    def test_a_call_kept_out_only_by_a_call_in_flight_waits_and_answers(self):
        with tempfile.TemporaryDirectory() as d:          # every file the build's router reads or writes is d's
            led = os.path.join(d, "SPEND.json")
            seed(led)
            with contextlib.ExitStack() as st:
                for mod, name, val in ((PL, "SPEND", led), (PL, "REPLIES", os.path.join(d, "rec")),
                                       (PL, "DEADLINE_LOG", os.path.join(d, "DL.jsonl")), (PL, "LY_LIMIT_USD", 1.5 * U),
                                       (HH, "STATE", os.path.join(d, "HEALTH.json")),
                                       (CB, "STATE", os.path.join(d, "BREAKERS.json")),
                                       (DT, "STATE", os.path.join(d, "DEADLINE_TABLE.json")),
                                       (PLG, "STATE_MD", os.path.join(d, "STATE.md"))):
                    st.enter_context(mock.patch.object(mod, name, val))
                r = PLG.build_router("heimdall_first", None, os.path.join(d, "SHADOW86.jsonl"))
            g, release, track = gate()
            r.backends, r.chains["check"], r.reserve_poll_s = {"openai:g": g}, ["openai:g"], 0.02
            results = {}
            first = threading.Thread(target=run, args=(r, results, 0))
            first.start()
            until(lambda: track["now"] == 1)
            second = threading.Thread(target=run, args=(r, results, 1))
            second.start()
            time.sleep(0.3)
            self.assertEqual((track["now"], results), (1, {}))   # one in flight, one WAITING: not refused (a default
                                                                # router refuses it at once)
            release.set()
            first.join(10)
            second.join(10)
            self.assertEqual([results[i][0] for i in (0, 1)], ["answer", "answer"])
            self.assertGreaterEqual(results[1][2], 0.25)        # it WAITED for the first call (held 0.3 s)
            self.assertEqual((g.calls, track["max"]), (2, 1))   # never two in flight past the limit
            self.assertEqual(json.load(open(led))["reserved"], {})


if __name__ == "__main__":
    unittest.main()
