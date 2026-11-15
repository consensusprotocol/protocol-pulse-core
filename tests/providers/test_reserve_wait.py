#!/usr/bin/env python3
"""The spend guard and calls IN FLIGHT. Batch 3's builds 1 and 2 (22:05 and 22:20 ET Nov 14) held 65 moments at step A
(90 holds, medley and spotlight): six workers in parallel, each reserving its price-table upper bound (about $0.85)
under a $4.50 limit with $0.27 spent, so four fit and the other two were refused batch after batch while those four
ran. A router that opts in (reserve_wait_s > 0, the ledger build's) waits for calls in flight to settle; it never passes
the limit and refuses when the wait ends. A default router still refuses at once (every other caller, the render's
among them, relies on that). Offline: the real Router over fake back-ends, real threads, a temporary ledger."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import providers as P  # noqa: E402
from test_providers import Fake, router  # noqa: E402

U = (1 + 200) * 10 / 1e6 + 1000 * 100 / 1e6     # Fake's upper bound for prompt "p" and max_tokens 1000: $0.10201


class Gate(Fake):
    """A back-end whose call stays in flight (its reservation held) until `release` is set; `track` counts how many of
    its calls are in flight at once."""

    def __init__(self, name, release, track):
        super().__init__(name, "openai", answer='{"ok": 1}', usage={"in": 10, "out": 10, "usd_reported": 0.0001})
        self.release, self.track = release, track

    def complete(self, prompt, max_tokens, seed, system=None):
        with self.track["lock"]:
            self.track["now"] += 1
            self.track["max"] = max(self.track["max"], self.track["now"])
        try:
            if not self.release.wait(10):
                raise P.Unavailable("the test never released this call")
            return super().complete(prompt, max_tokens, seed, system)
        finally:
            with self.track["lock"]:
                self.track["now"] -= 1


def gate():
    release, track = threading.Event(), {"lock": threading.Lock(), "now": 0, "max": 0}
    return Gate("openai:g", release, track), release, track


def seed(led, spent=0.0):
    json.dump({"usd_estimate": spent, "calls": 1 if spent else 0, "by_backend": {}, "by_role": {}, "reserved": {},
               "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))


def guarded(d, limit, spent=0.0, wait_s=None):
    """A router on a ledger with `spent` reported dollars, the guard at `limit`, one Gate back-end; wait_s None: the
    Router's default (no wait)."""
    led = os.path.join(d, "SPEND.json")
    seed(led, spent)
    g, release, track = gate()
    kw = {} if wait_s is None else {"reserve_wait_s": wait_s}
    r = router(d, [g], {"check": ["openai:g"]}, spend_path=led, limit_usd=limit, limit_basis="reported", **kw)
    r.reserve_poll_s = 0.02
    return r, g, release, track, led


def run(r, results, i, max_tokens=1000):
    t0 = time.time()
    try:
        results[i] = ("answer", r.call("check", "p", max_tokens, i).text, time.time() - t0)
    except P.SpendLimit as e:
        results[i] = ("refused", str(e), time.time() - t0)


def until(cond, timeout=5.0):
    t0 = time.time()
    while not cond():
        if time.time() - t0 > timeout:
            raise AssertionError(f"not reached in {timeout} s")
        time.sleep(0.01)


class TestARouterThatOptsInWaitsForCallsInFlight(unittest.TestCase):

    def test_six_workers_with_room_for_four_all_answer_and_never_more_than_four_run(self):
        with tempfile.TemporaryDirectory() as d:          # the batch-3 case: room for four upper bounds, six workers
            r, g, release, track, led = guarded(d, limit=4.5 * U, wait_s=10.0)
            results = {}
            ts = [threading.Thread(target=run, args=(r, results, i)) for i in range(6)]
            for t in ts:
                t.start()
            until(lambda: track["now"] == 4)
            time.sleep(0.2)
            self.assertEqual((track["now"], results), (4, {}))    # four in flight, two waiting: none refused
            held = json.load(open(led))["reserved"]
            self.assertEqual(len(held), 4)
            self.assertLessEqual(sum(held.values()), 4.5 * U)
            release.set()
            for t in ts:
                t.join(10)
            self.assertEqual(sorted(v[0] for v in results.values()), ["answer"] * 6)
            self.assertEqual((g.calls, track["max"]), (6, 4))
            final = json.load(open(led))
            self.assertEqual(final["reserved"], {})
            self.assertAlmostEqual(final["usd_reported"], 6 * 0.0001, places=9)

    def test_a_call_kept_out_by_spend_alone_is_refused_at_once_even_with_a_call_in_flight(self):
        with tempfile.TemporaryDirectory() as d:          # 0.01 spent: the small call fits, the large one never will
            r, g, release, track, led = guarded(d, limit=0.1, spent=0.01, wait_s=5.0)
            results = {}
            small = threading.Thread(target=run, args=(r, results, 0, 10))
            small.start()
            until(lambda: track["now"] == 1)
            run(r, results, 1)                              # 0.01 + its upper bound $0.102 > $0.10
            kind, why, secs = results[1]
            self.assertEqual(kind, "refused")
            self.assertLess(secs, 1.0)                      # no wait: no call settling could let it in
            self.assertNotIn("after waiting", why)
            release.set()
            small.join(10)
            self.assertEqual(results[0][0], "answer")

    def test_a_call_still_kept_out_when_its_wait_ends_is_refused_and_the_limit_is_never_passed(self):
        with tempfile.TemporaryDirectory() as d:          # room for one upper bound and a half
            r, g, release, track, led = guarded(d, limit=1.5 * U, wait_s=0.4)
            results = {}
            first = threading.Thread(target=run, args=(r, results, 0))
            first.start()
            until(lambda: track["now"] == 1)
            second = threading.Thread(target=run, args=(r, results, 1))
            second.start()
            time.sleep(0.15)
            self.assertEqual(len(json.load(open(led))["reserved"]), 1)    # while it waits: never two reservations
            second.join(3)
            self.assertFalse(second.is_alive())
            kind, why, secs = results[1]
            self.assertEqual(kind, "refused")
            self.assertIn("after waiting", why)
            self.assertGreaterEqual(secs, 0.4)
            self.assertEqual(g.calls, 0)                    # nothing answered yet: the first call is still in flight
            release.set()
            first.join(10)
            self.assertEqual((results[0][0], g.calls, track["max"]), ("answer", 1, 1))
            self.assertEqual(json.load(open(led))["reserved"], {})


class TestADefaultRouterRefusesAtOnce(unittest.TestCase):

    def test_with_no_opt_in_a_call_kept_out_by_a_call_in_flight_is_refused_at_once(self):
        with tempfile.TemporaryDirectory() as d:          # the contract every caller had before batch 3
            r, g, release, track, led = guarded(d, limit=1.5 * U)
            results = {}
            first = threading.Thread(target=run, args=(r, results, 0))
            first.start()
            until(lambda: track["now"] == 1)
            run(r, results, 1)
            kind, why, secs = results[1]
            self.assertEqual(kind, "refused")
            self.assertLess(secs, 0.5)
            self.assertNotIn("after waiting", why)
            release.set()
            first.join(10)
            self.assertEqual(results[0][0], "answer")


if __name__ == "__main__":
    unittest.main()
