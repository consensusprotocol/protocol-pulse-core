#!/usr/bin/env python3
"""RULING 110's replay driver (tests/package/replay110.py), offline: fake candidates on the real Router, ruling 100's
deadline as the Router gives it, replay85's own decisions. A call is in time, late (a missed deadline), a timeout, an
error or out of contract; a rate limit writes no row; the spend stop makes no call; the record set is ruling 85.1's."""
import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/providers"):
    sys.path.insert(0, os.path.join(REPO, _p))
import providers as P  # noqa: E402
import replay110 as RX  # noqa: E402
from test_gates import a_item  # noqa: E402
from test_providers import Fake, router  # noqa: E402

M = "dsv41unc"
PROMPT = '<excerpt label="m1">Bitcoin is a savings technology.</excerpt>'
GROK = json.dumps({"excerpts": [a_item("m1")]})
FAILS = json.dumps({"excerpts": [a_item("m1", view="quoting_other")]})


class Timed(Fake):
    """A candidate that answers after `delay` seconds and reports that time, as a live back-end does."""

    def __init__(self, answer, delay=0.0, fail=None):
        super().__init__(RX.name(M), "heimdall", answer=answer, fail=fail,
                         usage={"in": 100, "out": 10, "usd_reported": 0.001})
        self.delay = delay

    def complete(self, prompt, max_tokens, seed, system=None):
        time.sleep(self.delay)
        text, usage, _ = super().complete(prompt, max_tokens, seed, system)
        return text, usage, self.delay


def candidate(d, b, deadline_s=0.3, spent=0.0):
    """A Router with the candidate on its replay chain and ruling 100's gateway deadline for context_verdict."""
    led = os.path.join(d, "SPEND.json")
    json.dump({"usd_estimate": spent, "calls": 1 if spent else 0, "by_backend": {}, "by_role": {}, "reserved": {},
               "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
    r = router(d, [b], {f"replay110_{M}": [RX.name(M)]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
               routing="heimdall_first")
    r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": deadline_s}}
    return r


def job(d):
    p = os.path.join(d, "rec.json")
    rec = {"role": "context_verdict", "backend": "xai:grok", "prompt": PROMPT, "text": GROK, "max_tokens": 100,
           "seed": 7, "recorded_at": "2026-11-14T01:00:00Z", "seconds": 20.0}
    json.dump(rec, open(p, "w"))
    return (p, rec, "step_a", [], M)


class TestOneRecord(unittest.TestCase):

    def test_an_answer_inside_ruling_100s_deadline_is_in_time_and_compared(self):
        with tempfile.TemporaryDirectory() as d:
            row = RX.replay_one(candidate(d, Timed(GROK, 0.05)), job(d), cap_s=2.0)
            self.assertEqual((row["outcome"], row["deadline_100_s"], row["compare"]), ("in_time", 0.3, {"m1": "agree"}))

    def test_an_answer_after_the_deadline_is_late_a_missed_deadline_and_still_compared(self):
        with tempfile.TemporaryDirectory() as d:
            row = RX.replay_one(candidate(d, Timed(FAILS, 0.5)), job(d), cap_s=2.0)
            self.assertEqual((row["outcome"], row["compare"]), ("late", {"m1": "stricter"}))
            self.assertGreater(row["seconds"], row["deadline_100_s"])

    def test_no_answer_by_the_cap_is_a_timeout_with_no_decision(self):
        with tempfile.TemporaryDirectory() as d:
            row = RX.replay_one(candidate(d, Timed(GROK, 0.6)), job(d), cap_s=0.2)
            self.assertEqual((row["outcome"], row["heimdall"]), ("timeout", None))
            self.assertNotIn("compare", row)

    def test_an_answer_out_of_contract_is_no_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            row = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0)
            self.assertEqual((row["outcome"], row["heimdall"]), ("out_of_contract", None))

    def test_a_failure_is_an_error_and_a_rate_limit_writes_no_row(self):
        with tempfile.TemporaryDirectory() as d:
            row = RX.replay_one(candidate(d, Timed(GROK, fail="HTTP 502 overloaded")), job(d), cap_s=2.0)
            self.assertEqual(row["outcome"], "error")
            waited = []
            self.assertIsNone(RX.replay_one(candidate(d, Timed(GROK, fail="HTTP 429 too many")), job(d), cap_s=2.0,
                                            sleep=waited.append))
            self.assertEqual(waited, [30])

    def test_a_call_that_fails_in_a_way_the_router_does_not_name_is_an_error_row(self):
        import http.client
        with tempfile.TemporaryDirectory() as d:          # 00:46 ET Nov 15: a reply cut mid-body ended the run
            cut = Timed(GROK, fail=http.client.IncompleteRead(b"x", 21278))
            row = RX.replay_one(candidate(d, cut), job(d), cap_s=2.0)
            self.assertEqual((row["outcome"], row["heimdall"]), ("error", None))
            self.assertTrue(row["heimdall_error"].startswith("IncompleteRead"))
            self.assertIsInstance(row["seconds"], float)

    def test_at_the_spend_stop_no_call_is_made(self):
        with tempfile.TemporaryDirectory() as d:
            b = Timed(GROK)
            self.assertEqual(RX.replay_one(candidate(d, b, spent=0.75), job(d), cap_s=2.0, stop_usd=0.75), "stopped")
            self.assertEqual(b.calls, 0)
            self.assertNotEqual(RX.replay_one(candidate(d, b, spent=0.74), job(d), cap_s=2.0, stop_usd=0.75),
                                "stopped")
            self.assertEqual(b.calls, 1)


class TestTheSetAndTheTable(unittest.TestCase):

    def test_the_records_are_ruling_85s_once_each_and_an_unreadable_one_is_set_aside(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "r"))
            good = {"role": "context_verdict", "prompt": PROMPT, "text": GROK}
            json.dump(good, open(os.path.join(d, "r", "a.json"), "w"))
            json.dump(dict(good, role="fidelity_verdict"), open(os.path.join(d, "r", "b.json"), "w"))
            src = os.path.join(d, "RESULTS.jsonl")
            with open(src, "w") as f:
                for rel, m in (("r/a.json", "deepseek"), ("r/a.json", "glm"), ("r/b.json", "glm"), ("r/gone.json", "glm")):
                    f.write(json.dumps({"record": rel, "type": "step_a", "model": m, "anchors": ["37c5b5f5"]}) + "\n")
            recs, missing = RX.source_records(src, wt=d)
            self.assertEqual([(os.path.relpath(p, d), k, a) for p, _, k, a in recs], [("r/a.json", "step_a",
                                                                                        ["37c5b5f5"])])
            self.assertEqual(sorted(missing), ["r/b.json", "r/gone.json"])

    def test_agreement_in_time_leaves_late_answers_out_and_missed_counts_late_and_timeouts(self):
        rows = [{"type": "step_a", "model": M, "outcome": "in_time", "seconds": 10.0, "compare": {"a": "agree"}},
                {"type": "step_a", "model": M, "outcome": "in_time", "seconds": 30.0, "compare": {"b": "stricter"}},
                {"type": "step_a", "model": M, "outcome": "late", "seconds": 200.0, "compare": {"c": "agree"}},
                {"type": "step_a", "model": M, "outcome": "timeout", "seconds": 300.0},
                {"type": "step_a", "model": M, "outcome": "error", "seconds": 1.0}]
        x = RX.summary(rows)[("step_a", M)]
        self.assertEqual((x["in_time"], x["late"], x["timeout"], x["error"], x["missed"]), (2, 1, 1, 1, 2))
        self.assertEqual((x["units_in_time"], x["agree_in_time_pct"]), (2, 50.0))
        self.assertAlmostEqual(x["agree_all_pct"], 200 / 3)
        self.assertEqual((x["p50_s"], x["p90_s"]), (30.0, 166.0))     # the answers' times only (10, 30, 200)


if __name__ == "__main__":
    unittest.main()
