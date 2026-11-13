#!/usr/bin/env python3
"""RULING 66's standing part (orchestrator 14:02 Nov 13): the candidate registry (pipeline/candidates.py)."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import candidates as CA  # noqa: E402

T0 = datetime(2026, 11, 13, 19, 0, tzinfo=timezone.utc)


def record(now, tried, package=None, candidate=None, registry=False):
    return {"now": now.isoformat(), "tried": tried, "package": package, "candidate": candidate,
            **({"registry": True} if registry else {})}


def t(lineup, ok=True, cand=None):
    return {"lineup": lineup, "medley_ok": ok, **({"candidate": cand} if cand else {})}


class TestRegistry(unittest.TestCase):
    def test_a_passed_line_up_is_a_candidate_once_and_a_packaged_one_is_closed(self):
        reg = CA.new_registry()
        self.assertEqual(CA.seed(reg, record(T0, [t(["a", "b", "c"], ok=False), t(["a", "b", "d"])]), "r1"),
                         ["a+b+d"])
        self.assertEqual(CA.seed(reg, record(T0, [t(["a", "b", "d"])]), "r1"), [])          # a record seeds once
        self.assertEqual(CA.seed(reg, record(T0 + timedelta(hours=1), [t(["a", "b", "d"])]), "r2"), [])   # one entry
        self.assertEqual((reg["candidates"]["a+b+d"]["source"], reg["candidates"]["a+b+d"]["index"]), ("r1", 1))
        CA.seed(reg, record(T0, [t(["x", "y", "z"])], package={"segments": [{"moment_id": m} for m in "xyz"]}), "r3")
        self.assertEqual(reg["candidates"]["x+y+z"]["state"], "closed")                  # its own build packaged it
        CA.seed(reg, record(T0, [t(["a", "b", "d"], cand="r1")]), "r4")                  # a candidate's own try
        self.assertEqual(set(reg["candidates"]), {"a+b+d", "x+y+z"})                     # is never a new candidate

    def test_a_try_made_before_the_registry_counts_once(self):
        reg = CA.new_registry()
        CA.seed(reg, record(T0, [t(["a", "b", "d"])]), "r1")
        legacy = record(T0, [t(["a", "b", "d"], cand="r1")],
                        candidate={"source": "r1", "index": 0, "lineup": ["a", "b", "d"], "result": "PACKAGE"})
        CA.seed(reg, legacy, "r2")
        self.assertEqual(reg["candidates"]["a+b+d"]["state"], "closed")
        reg2 = CA.new_registry()
        CA.seed(reg2, record(T0, [t(["a", "b", "d"])]), "r1")
        CA.seed(reg2, dict(legacy, registry=True), "r2")                                # a registry build: no again
        self.assertEqual(reg2["candidates"]["a+b+d"]["state"], "open")

    def test_the_14_02_rules(self):
        e = {"history": [], "state": "open", "until": None, "fresh_used": False}
        CA.outcome(e, "budget", T0.isoformat(), "b1")
        self.assertEqual(e["state"], "open")                                              # a budget is no outcome
        CA.outcome(e, "line", T0.isoformat(), "b2")                                       # a line failed again
        self.assertEqual((e["state"], e["until"]), ("resting", (T0 + timedelta(hours=6)).isoformat()))
        e["fresh_used"] = True                                                            # its one more try
        CA.outcome(e, "line", (T0 + timedelta(hours=7)).isoformat(), "b3")
        self.assertEqual(e["state"], "closed")
        for cls in ("clip", "package"):
            e2 = {"history": [], "state": "open", "until": None, "fresh_used": False}
            CA.outcome(e2, cls, T0.isoformat(), "b")
            self.assertEqual(e2["state"], "closed", cls)
        with self.assertRaises(ValueError):
            CA.outcome(e2, "maybe", T0.isoformat(), "b")

    def test_due_sorts_by_time_not_by_text(self):
        reg = CA.new_registry()
        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "utc")                              # 19:00Z
        CA.seed(reg, dict(record(T0, [t(["d", "e", "f"])]), now="2026-11-13T14:30:00-05:00"), "et")   # 19:30Z
        CA.seed(reg, dict(record(T0, [t(["g", "h", "i"])]), now=None), "none")             # no time: the oldest
        self.assertEqual([k for k, _, _ in CA.due(reg, T0)], ["d+e+f", "a+b+c", "g+h+i"])

    def test_a_found_at_without_a_zone_is_utc_and_a_malformed_one_raises(self):
        reg = CA.new_registry()
        CA.seed(reg, dict(record(T0, [t(["a", "b", "c"])]), now="2026-11-13T20:00:00"), "zoneless")   # 20:00 UTC
        CA.seed(reg, record(T0, [t(["d", "e", "f"])]), "utc")                                          # 19:00 UTC
        self.assertEqual([k for k, _, _ in CA.due(reg, T0)], ["a+b+c", "d+e+f"])
        reg["candidates"]["a+b+c"]["found_at"] = "tomorrow"
        with self.assertRaises(ValueError):
            CA.due(reg, T0)

    def test_due_is_newest_first_and_a_rested_one_gets_fresh_writes(self):
        reg = CA.new_registry()
        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "old")
        CA.seed(reg, record(T0 + timedelta(hours=2), [t(["d", "e", "f"])]), "new")
        CA.seed(reg, record(T0 + timedelta(hours=1), [t(["g", "h", "i"])]), "mid")
        CA.outcome(reg["candidates"]["g+h+i"], "line", T0.isoformat(), "b")              # resting until T0 + 6 h
        self.assertEqual([(k, f) for k, _, f in CA.due(reg, T0 + timedelta(hours=3))],
                         [("d+e+f", False), ("a+b+c", False)])
        self.assertEqual([(k, f) for k, _, f in CA.due(reg, T0 + timedelta(hours=6))],
                         [("d+e+f", False), ("g+h+i", True), ("a+b+c", False)])

    def test_a_stored_time_without_a_zone_is_utc_and_a_malformed_one_raises(self):
        reg = CA.new_registry()
        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "r")
        e = reg["candidates"]["a+b+c"]
        e.update(state="resting", until="2026-11-13T19:00:00")                       # no zone: UTC
        self.assertEqual([k for k, _, f in CA.due(reg, T0)], ["a+b+c"])
        e["until"] = "tomorrow"
        with self.assertRaises(ValueError):
            CA.due(reg, T0)

    def test_registered_is_every_line_up_whatever_its_state(self):
        """The search leaves every registered line-up to the registry (the 16:30 Nov 13 gap)."""
        reg = CA.new_registry()
        CA.seed(reg, record(T0, [t(["a", "b", "c"]), t(["d", "e", "f"]), t(["g", "h", "i"])]), "r")
        CA.outcome(reg["candidates"]["d+e+f"], "line", T0.isoformat(), "b")
        CA.outcome(reg["candidates"]["g+h+i"], "clip", T0.isoformat(), "b")
        got = CA.registered(reg)
        self.assertEqual({k: v["state"] for k, v in got.items()},
                         {("a", "b", "c"): "open", ("d", "e", "f"): "resting", ("g", "h", "i"): "closed"})
        self.assertEqual((got[("d", "e", "f")]["until"], got[("d", "e", "f")]["key"], got[("d", "e", "f")]["index"]),
                         ((T0 + timedelta(hours=6)).isoformat(), "d+e+f", 1))
        self.assertEqual(CA.registered(CA.new_registry()), {})
        for bad in (["a", "b"], None, "abc", ["a", "", "c"], ["a", 2, "c"]):          # not a line-up matching its key
            reg["candidates"]["a+b+c"]["lineup"] = bad
            with self.assertRaises(ValueError):
                CA.registered(reg)

    def test_run_due_stops_at_a_package_inside_the_judged_line_ups(self):
        reg = CA.new_registry()
        for h, lu in enumerate((["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"])):
            CA.seed(reg, record(T0 + timedelta(hours=h), [t(lu)]), f"r{h}")
        seen = []

        def try_one(e, fresh, left):
            seen.append((CA.key(e["lineup"]), fresh, left))
            return ({"package": "pk"} if e["lineup"][0] == "d" else None,
                    {"g": "clip", "d": "package"}[e["lineup"][0]], "why", 1)
        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), try_one, 8, build="b")
        self.assertEqual(out, {"package": "pk"})
        self.assertEqual(seen, [("g+h+i", False, 8), ("d+e+f", False, 7)])                # newest first; then stop
        self.assertEqual((left, [x["class"] for x in tries]), (6, ["clip", "package"]))
        self.assertEqual(reg["candidates"]["a+b+c"]["state"], "open")                    # never reached: still open
        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), lambda e, f, l: (None, "budget", "", 0), 0)
        self.assertEqual((out, tries, left), (None, [], 0))                              # no line-up left: no try
        out, tries, left = CA.run_due(reg, T0 + timedelta(hours=3), lambda e, f, l: (None, "budget", "w", 99), 8)
        self.assertEqual((left, tries[0]["judged"]), (0, 8))                             # out of range: all charged
        self.assertIn("all are charged", tries[0]["why"])

    def test_the_fresh_try_is_marked_and_a_line_failing_it_closes(self):
        reg = CA.new_registry()
        CA.seed(reg, record(T0, [t(["a", "b", "c"])]), "r")
        CA.outcome(reg["candidates"]["a+b+c"], "line", T0.isoformat(), "b1")
        out, tries, _ = CA.run_due(reg, T0 + timedelta(hours=6, minutes=1), lambda e, f, l: (None, "line", "w", 1), 8)
        self.assertEqual((tries[0]["fresh"], tries[0]["state"]), (True, "closed"))
        self.assertTrue(reg["candidates"]["a+b+c"]["history"][-1]["fresh"])


if __name__ == "__main__":
    unittest.main()
