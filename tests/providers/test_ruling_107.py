#!/usr/bin/env python3
"""RULING 107 Q1 (orchestrator 20:40 ET Nov 14): "An abandoned call is booked at the model's own reported rate (its
recorded cost per prompt token x the prompt sent), not list price; if the model has no reported rate yet, list price
until it has three. The $20 cap is on that basis from now." Offline: fake back-ends, a seeded ledger, the real Router."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import providers as P  # noqa: E402
from test_providers import Fake, Slow, SlowFail, router, wait_for  # noqa: E402

TOKENS = 201                       # prompt_tokens_upper("p"): 1 character + 200, counted from above (ruling 83 (a))
LIST = TOKENS * 10 / 1e6           # Fake's list input price: $10 / 1M


def seed(path, **deepseek):
    """A ledger whose deepseek row is `deepseek` (calls / in / reported_calls / usd_reported / in_reported)."""
    row = {"calls": 0, "in": 0, "out": 0, "usd_estimate": 0.0, "price_usd_per_1m": [10, 100]}
    row.update(deepseek)
    json.dump({"usd_estimate": 0.0, "calls": row["calls"], "by_backend": {"heimdall:deepseek": row}, "by_role": {},
               "reserved": {}, "usd_reported": float(row.get("usd_reported", 0.0)),
               "usd_unreported_estimate": 0.0}, open(path, "w"))


def abandon_once(d, slow, **seeded):
    """One call whose first leg (deepseek) passes its 0.2 s deadline; qwen answers with the vendor's own figure, so the
    unreported estimate holds the abandoned call's booking alone. -> (reply, the ledger, the deadline log)."""
    spend, log = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
    seed(spend, **seeded)
    next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
                 usage={"in": 1000, "out": 100, "usd_reported": 0.002})
    r = router(d, [slow, next_], {"check": ["heimdall:deepseek", "heimdall:qwen"]}, spend_path=spend,
               limit_usd=50.0, limit_basis="reported", deadline_log=log)
    rep = r.call("check", "p", 100, 7, deadline_s=0.2)
    with open(log) as f:
        lines = [json.loads(x) for x in f]
    return r, rep, json.load(open(spend)), lines


class TestRuling107Booking(unittest.TestCase):

    def test_an_abandoned_call_is_booked_at_the_models_own_reported_rate_once_it_has_three_reported_calls(self):
        with tempfile.TemporaryDirectory() as d:
            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
                                            in_reported=3000)
            want = 0.003 / 3000 * TOKENS                               # $1 / 1M prompt tokens, its own figure
            self.assertAlmostEqual(led["usd_unreported_estimate"], want, places=9)
            self.assertLess(want, LIST / 5)                            # not list price
            row = led["by_backend"]["heimdall:deepseek"]
            self.assertEqual(row["calls"], 4)                          # counted once, as ruling 83 (a) counts it
            self.assertAlmostEqual(row["usd_estimate"], LIST, places=9)    # usd_estimate stays the list-price figure
            miss = [x for x in log if x["kind"] == "missed_deadline"]
            self.assertEqual([(x["booked_basis"], round(x["booked_usd"], 9)) for x in miss],
                             [("reported_rate", round(want, 9))])
            self.assertIn("at its own reported rate", rep.tried[0][1])
            self.assertAlmostEqual(r.spent(), 0.003 + 0.002 + want, places=9)   # the cap reads that booking

    def test_list_price_until_the_model_has_three_reported_calls(self):
        for n in (0, 1, 2):
            with tempfile.TemporaryDirectory() as d:
                slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
                r, rep, led, log = abandon_once(d, slow, calls=n, **{"in": 1000 * n}, reported_calls=n,
                                                usd_reported=0.001 * n, in_reported=1000 * n)
                self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9, msg=f"{n} reported call(s)")
                miss = [x for x in log if x["kind"] == "missed_deadline"]
                self.assertEqual([x["booked_basis"] for x in miss], ["list"])
                self.assertIn("at list price", rep.tried[0][1])

    def test_the_rate_is_over_the_reported_calls_prompt_tokens_only(self):
        with tempfile.TemporaryDirectory() as d:                   # 10,000 prompt tokens, 2,000 of them on calls
            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")   # with a figure
            r, rep, led, log = abandon_once(d, slow, calls=5, **{"in": 10000}, reported_calls=3, usd_reported=0.004,
                                            in_reported=2000)
            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.004 / 2000 * TOKENS, places=9)

    def test_no_prompt_tokens_on_record_is_list_price(self):
        with tempfile.TemporaryDirectory() as d:
            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 0}, reported_calls=3, usd_reported=0.003,
                                            in_reported=0)
            self.assertAlmostEqual(led["usd_unreported_estimate"], LIST, places=9)

    def test_a_ledger_kept_before_reads_every_calls_prompt_tokens_and_starts_counting_the_reported_ones(self):
        with tempfile.TemporaryDirectory() as d:                   # no in_reported yet: "in" stands in for it
            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006)
            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.006 / 3000 * TOKENS, places=9)
            self.assertEqual(led["by_backend"]["heimdall:qwen"]["in_reported"], 1000)   # a new row counts from 0
        with tempfile.TemporaryDirectory() as d:                   # an answer with a figure on an older row:
            spend = os.path.join(d, "SPEND.json")                  # in_reported starts from that row's "in"
            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006)
            ans = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek",
                       usage={"in": 500, "out": 50, "usd_reported": 0.001})
            router(d, [ans], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0,
                   limit_basis="reported").call("check", "q", 100, 7)
            row = json.load(open(spend))["by_backend"]["heimdall:deepseek"]
            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (3500, 3500, 4))

    def test_an_answer_without_a_figure_adds_no_reported_prompt_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            spend = os.path.join(d, "SPEND.json")
            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.006, in_reported=3000)
            ans = Fake("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek",
                       usage={"in": 700, "out": 50})
            router(d, [ans], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0,
                   limit_basis="reported").call("check", "q", 100, 7)
            row = json.load(open(spend))["by_backend"]["heimdall:deepseek"]
            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (3700, 3000, 3))

    def test_a_late_answer_replaces_exactly_the_booking_made_at_the_reported_rate(self):
        with tempfile.TemporaryDirectory() as d:
            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",
                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
                                            in_reported=3000)
            booked = 0.003 / 3000 * TOKENS
            self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=9)
            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
            late = [x for x in log if x["kind"] == "late_answer"]
            self.assertEqual([(x["replaced"], x["booked_basis"], round(x["booked_usd"], 9)) for x in late],
                             [(True, "reported_rate", round(booked, 9))])
            led = json.load(open(os.path.join(d, "SPEND.json")))
            row = led["by_backend"]["heimdall:deepseek"]
            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.0, places=9)   # that booking, exactly, gone
            self.assertAlmostEqual(led["usd_reported"], 0.003 + 0.002 + 0.0123, places=9)
            self.assertEqual((row["calls"], row["reported_calls"], row["in"], row["in_reported"]), (4, 4, 4000, 4000))
            self.assertAlmostEqual(row["usd_estimate"], slow.usd({"in": 1000, "out": 100}), places=9)  # list figure

    def test_a_late_answer_on_a_row_kept_before_starts_its_reported_prompt_tokens_from_that_rows_in(self):
        with tempfile.TemporaryDirectory() as d:                   # no in_reported on the row: "in" stands in
            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",
                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
            abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003)
            wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
            row = json.load(open(os.path.join(d, "SPEND.json")))["by_backend"]["heimdall:deepseek"]
            self.assertEqual((row["in"], row["in_reported"], row["reported_calls"]), (4000, 4000, 4))

    def test_a_late_answer_without_a_figure_is_its_own_estimate_in_place_of_the_booking(self):
        with tempfile.TemporaryDirectory() as d:                   # ruling 83 (a): "with none, the estimate from its
            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.6, family="deepseek",   # own counts"
                        usage={"in": 1000, "out": 100})
            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
                                            in_reported=3000)
            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.003 / 3000 * TOKENS, places=9)
            wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")
            led = json.load(open(os.path.join(d, "SPEND.json")))
            self.assertAlmostEqual(led["usd_unreported_estimate"], slow.usd({"in": 1000, "out": 100}), places=9)
            row = led["by_backend"]["heimdall:deepseek"]
            self.assertEqual((row["reported_calls"], row["in"], row["in_reported"]), (3, 4000, 3000))

    def test_the_rate_is_none_whenever_the_ledger_cannot_give_one(self):
        with tempfile.TemporaryDirectory() as d:                   # glm, audit 20261114_2043 C1 F1 / F19
            spend = os.path.join(d, "SPEND.json")
            fake = Fake("heimdall:deepseek", "heimdall", answer="{}", family="deepseek")
            self.assertIsNone(router(d, [fake], {"check": ["heimdall:deepseek"]}).reported_rate("heimdall:deepseek"))
            r = router(d, [fake], {"check": ["heimdall:deepseek"]}, spend_path=spend, limit_usd=50.0)
            for body in ("{not json", json.dumps({"usd_estimate": 0.0, "by_backend": ["a list"]}),
                         json.dumps({"usd_estimate": 0.0, "by_backend": {"heimdall:deepseek": {
                             "calls": 3, "in": 3000, "reported_calls": "three", "usd_reported": 0.003}}}),
                         json.dumps({"usd_estimate": 0.0, "by_backend": {"heimdall:deepseek": "a row"}})):
                open(spend, "w").write(body)
                self.assertIsNone(r.reported_rate("heimdall:deepseek"), body)
                self.assertEqual(r.booking_usd(fake, "p"), (LIST, "list"), body)
            seed(spend, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003, in_reported=3000)
            self.assertAlmostEqual(r.reported_rate("heimdall:deepseek"), 1e-6, places=12)
            self.assertIsNone(r.reported_rate("heimdall:qwen"))       # no row: list price

    def test_a_late_error_leaves_the_reported_rate_booking_standing(self):
        with tempfile.TemporaryDirectory() as d:
            slow = SlowFail("heimdall:deepseek", "heimdall", None, delay=0.6, family="deepseek")
            r, rep, led, log = abandon_once(d, slow, calls=3, **{"in": 3000}, reported_calls=3, usd_reported=0.003,
                                            in_reported=3000)
            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_error")
            led = json.load(open(os.path.join(d, "SPEND.json")))
            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.003 / 3000 * TOKENS, places=9)


if __name__ == "__main__":
    unittest.main()
