#!/usr/bin/env python3
"""RULING 111's re-try driver (tests/package/replay111.py), offline. The v4 is asked in the gateway's JSON mode with a set
effort, and otherwise exactly as production asks; an out-of-contract answer's text is kept and its shape named; the
better effort is chosen by the stated rule; every anchor decision Grok passed and the candidate failed is listed."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/providers"):
    sys.path.insert(0, os.path.join(REPO, _p))
import providers as P  # noqa: E402
import replay110 as RX  # noqa: E402
import replay111 as RY  # noqa: E402
from test_providers import Fake, router  # noqa: E402
from test_replay110 import GROK, Timed, candidate, job  # noqa: E402

SPEC = {"vendor": "heimdall", "model": RY.MODEL, "base_url": "http://gateway.invalid/api/v1",
        "price_usd_per_1m": [3, 15], "family": "deepseek", "temperature": 0, "min_out": 16000}


class Answer:
    def read(self):
        return json.dumps({"choices": [{"message": {"content": '{"ok": 1}'}}],
                           "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.0001}}).encode()


class TestTheBackend(unittest.TestCase):

    def test_the_json_mode_and_the_effort_are_the_only_fields_added_to_productions_body(self):
        bodies = []

        def urlopen(req, timeout=None):
            bodies.append(json.loads(req.data))
            return Answer()
        prod = P.HeimdallBackend("heimdall:" + RY.MODEL, SPEC, "/nonexistent")
        fmt = RY.FormatBackend(RY.bname("none"), SPEC, "/nonexistent", "none")
        for b in (prod, fmt):
            b.key = lambda name: "test-key"
        vision = {"text": "the sheet", "images": ["aGVsbG8="]}
        with mock.patch.object(P.urllib.request, "urlopen", urlopen):
            prod.complete("the prompt", 300, 7, "the system")
            text, usage, _ = fmt.complete("the prompt", 300, 7, "the system")
            prod.complete(vision, 300, 7)
            fmt.complete(vision, 300, 7)
        for i in (1, 3):
            added = {k: bodies[i].pop(k) for k in ("response_format", "reasoning_effort")}
            self.assertEqual(added, {"response_format": {"type": "json_object"}, "reasoning_effort": "none"})
            self.assertEqual(bodies[i], bodies[i - 1])                 # all else exactly as production sends it
        self.assertEqual((text, usage["usd_reported"]), ('{"ok": 1}', 0.0001))


class TestTheCall(unittest.TestCase):

    def test_an_out_of_contract_answers_text_is_kept_only_when_asked(self):
        with tempfile.TemporaryDirectory() as d:
            kept = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0, keep_raw=True)
            plain = RX.replay_one(candidate(d, Timed("not json")), job(d), cap_s=2.0)
            self.assertEqual((kept["outcome"], kept["raw_text"]), ("out_of_contract", "not json"))
            self.assertNotIn("raw_text", plain)                            # ruling 110's rows are unchanged

    def test_a_named_back_end_on_its_own_chain_answers_for_its_key(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "SPEND.json")
            json.dump({"usd_estimate": 0.0, "calls": 0, "by_backend": {}, "by_role": {}, "reserved": {},
                       "usd_reported": 0.0, "usd_unreported_estimate": 0.0}, open(led, "w"))
            b = Fake(RY.bname("none"), "heimdall", answer=GROK, usage={"in": 10, "out": 10, "usd_reported": 0.001})
            r = router(d, [b], {"replay111_none": [b.name]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
                       routing="heimdall_first")
            r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": 120}}
            p, rec, k, a, _ = job(d)
            row = RX.replay_one(r, (p, rec, k, a, "none"), cap_s=2.0, names={"none": b.name}, prefix="replay111")
            self.assertEqual((row["outcome"], row["model"], row["model_id"], b.calls), ("in_time", "none", b.model, 1))


class TestThisOrdersCall(unittest.TestCase):

    def named(self, d, spent, answer):
        led = os.path.join(d, "SPEND.json")
        json.dump({"usd_estimate": spent, "calls": 1, "by_backend": {}, "by_role": {}, "reserved": {},
                   "usd_reported": spent, "usd_unreported_estimate": 0.0}, open(led, "w"))
        b = Fake(RY.bname("none"), "heimdall", answer=answer, usage={"in": 10, "out": 10, "usd_reported": 0.001})
        r = router(d, [b], {"replay111_none": [b.name]}, spend_path=led, limit_usd=50.0, limit_basis="reported",
                   routing="heimdall_first")
        r.config["routing"] = {"verdict_roles": ["context_verdict"], "verdict_deadline_s": {"heimdall": 120}}
        p, rec, k, a, _ = job(d)
        return r, b, (p, rec, k, a, "none")

    def test_this_orders_stop_not_ruling_110s(self):
        for held in (0.40, RY.STOP_USD):                                # the order's cap, and its stop below it
            with tempfile.TemporaryDirectory() as d:
                r, b, j = self.named(d, held, GROK)
                self.assertEqual((RY.ask_one(r, j, {"none": b.name}, cap_s=2.0), b.calls), ("stopped", 0))
        with tempfile.TemporaryDirectory() as d:
            r, b, j = self.named(d, RY.STOP_USD - 0.01, "not json")
            row = RY.ask_one(r, j, {"none": b.name}, cap_s=2.0)
            self.assertEqual((row["outcome"], row["raw_text"], b.calls), ("out_of_contract", "not json", 1))


class TestTheShapes(unittest.TestCase):

    def test_each_shape(self):
        cases = [("", "empty"), ("   ", "empty"),
                 ('```json\n{"a": 1}\n```', "code fence"),
                 ('{"a": 1}', "valid JSON, not the contract"),
                 ('Here it is: {"a": 1} as asked.', "prose around the JSON"),
                 ('{"a": [1, 2', "truncated"),
                 ('{"a": "an answer cut mid-wor', "truncated"),          # the error is at the string's start
                 ('{"a": 1 "b": 2}', "invalid JSON")]
        for text, want in cases:
            self.assertEqual(RY.shape(text), want, text)
        self.assertEqual(RY.shape('{"a": 1 "b": 2}', out_tokens=16000, cap=16000), "truncated")   # at its token cap
        self.assertEqual(RY.shape('{"a": 1 "b": 2}', out_tokens=900, cap=16000), "invalid JSON")


def rows_of(v, valid, out_of_contract, agree, secs):
    """`valid` in-contract answers (the first `agree` of them agree with Grok) and `out_of_contract` others."""
    rs = [{"model": v, "outcome": "in_time", "seconds": secs,
           "compare": {f"u{i}": "agree" if i < agree else "stricter"}} for i in range(valid)]
    return rs + [{"model": v, "outcome": "out_of_contract", "seconds": secs} for _ in range(out_of_contract)]


class TestTheChoice(unittest.TestCase):

    def test_the_higher_valid_answer_rate_wins(self):
        rows = rows_of("none", 9, 1, 8, 3.0) + rows_of("medium", 7, 3, 7, 3.0)
        self.assertEqual(RY.choose(rows)[0], "none")

    def test_at_the_same_rate_the_higher_agreement_wins_then_the_lower_p50(self):
        rows = rows_of("none", 9, 1, 7, 3.0) + rows_of("medium", 9, 1, 9, 3.0)
        self.assertEqual(RY.choose(rows)[0], "medium")
        rows = rows_of("none", 9, 1, 9, 3.0) + rows_of("medium", 9, 1, 9, 10.0)
        self.assertEqual(RY.choose(rows)[0], "none")

    def test_no_effort_with_a_valid_answer_means_no_full_run(self):
        rows = rows_of("none", 0, 10, 0, 3.0) + rows_of("medium", 0, 10, 0, 9.0)
        self.assertIsNone(RY.choose(rows)[0])
        self.assertEqual(RY.choose(rows_of("none", 0, 10, 0, 3.0) + rows_of("medium", 1, 9, 1, 9.0))[0], "medium")


class TestTheAnchors(unittest.TestCase):

    def test_every_anchor_decision_grok_passed_and_the_candidate_failed_is_listed(self):
        rows = [{"record": "r1", "type": "step_a", "model": "none", "compare": {"u1": "stricter", "u2": "stricter"}},
                {"record": "r2", "type": "step_a", "model": "none", "compare": {"u1": "stricter"}},
                {"record": "r3", "type": "step_a", "model": "none", "compare": {"u1": "agree"}}]
        units = {"r1": {"u1": ["37c5b5f5"]}, "r2": {}, "r3": {"u1": ["0c68b589"]}}
        with mock.patch.object(RY.R, "anchor_texts", lambda: []), \
                mock.patch.object(RY.R, "anchor_units", lambda row, anchors: units[row["record"]]):
            got = RY.anchor_failures(rows)
        self.assertEqual(got, [{"record": "r1", "type": "step_a", "model": "none", "unit": "u1", "pins": ["37c5b5f5"]}])


if __name__ == "__main__":
    unittest.main()
