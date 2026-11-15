#!/usr/bin/env python3
"""RULING 114: the x-bf-tunnel-instance replay (tests/package/replay114.py). Offline: urlopen is replaced by a fake
gateway; the key is a fake one; files go to a temporary directory."""
import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay114 as RT  # noqa: E402

KEY = "sk-FAKE-KEY-never-in-a-row"


class Gateway:
    """A fake Heimdall: answers each request from `answers` (text, finish_reason), with response headers that name the
    instance (x-bf-instance) by whether the request carried the header; it keeps every request it saw."""

    def __init__(self, answers):
        self.answers, self.seen = list(answers), []

    def __call__(self, req, timeout=None):
        self.seen.append({"headers": {k.lower(): v for k, v in req.header_items()}, "body": json.loads(req.data)})
        text, fin = self.answers.pop(0)
        sent = "x-bf-tunnel-instance" in self.seen[-1]["headers"]
        h = Message()
        h["x-bf-instance"] = "pinga282" if sent else "vllm-7"
        h["content-type"] = "application/json"
        body = {"id": f"chatcmpl-{len(self.seen)}", "model": "deepseek/deepseek-v4-flash-0731-abliterated",
                "choices": [{"message": {"content": text}, "finish_reason": fin}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50, "cost": 0.0001}}
        r = io.BytesIO(json.dumps(body).encode())
        r.status, r.headers = 200, h
        return r


def rec():
    return {"prompt": "Judge it.", "max_tokens": 1200, "seed": 28, "system": "Be brief."}


class TestPick(unittest.TestCase):
    def test_the_named_five_first_then_spread_and_refused_without_one(self):
        rows = [{"record": f"r{i:03d}", "type": "t", "out_tokens": t, "shape": "truncated"}
                for i, t in enumerate([7, 122, 171, 497, 1564] + list(range(200, 1200, 10)))]
        got = RT.pick(rows + [dict(rows[7])], 30)                               # a record twice is one record
        self.assertEqual([r["out_tokens"] for r in got[:5]], [7, 122, 171, 497, 1564])
        self.assertEqual(len({r["record"] for r in got}), 30)
        self.assertLess(got[5]["out_tokens"], got[-1]["out_tokens"])           # spread over the out_tokens order
        with self.assertRaises(ValueError):
            RT.pick([r for r in rows if r["out_tokens"] != 497], 30)


class TestAsk(unittest.TestCase):
    def setUp(self):
        self.b = RT.backend()
        self.b.key = lambda name: KEY

    def test_the_header_only_on_its_leg_the_same_request_otherwise_and_no_key_in_a_row(self):
        g = Gateway([('{"a": 1', "length"), ('{"a": 1}', "stop")])
        with mock.patch("urllib.request.urlopen", g):
            w = RT.ask(self.b, rec(), "with")
            wo = RT.ask(self.b, rec(), "without")
        self.assertEqual(g.seen[0]["headers"].get("x-bf-tunnel-instance"), "pinga282")
        self.assertNotIn("x-bf-tunnel-instance", g.seen[1]["headers"])
        self.assertEqual(g.seen[0]["body"], g.seen[1]["body"])                     # the same request, same seed
        body = g.seen[0]["body"]
        self.assertEqual((body["seed"], body["response_format"], body["reasoning_effort"], body["model"]),
                         (28, {"type": "json_object"}, "none", "deepseek/deepseek-v4-flash-0731-abliterated"))
        self.assertEqual((w["finish_reason"], w["id"], w["out_tokens"], w["shape"], w["unclosed"]),
                         ("length", "chatcmpl-1", 50, "truncated", True))
        self.assertEqual((wo["shape"], wo["unclosed"], wo["response_headers"]["x-bf-instance"]),
                         ("closed JSON", False, "vllm-7"))
        self.assertEqual([a["response_headers"]["x-bf-instance"] for a in w["attempts"]], ["pinga282"])
        for row in (w, wo):
            s = json.dumps(row)
            self.assertNotIn(KEY, s)
            self.assertNotIn("Bearer", s)
            self.assertNotIn("authorization", s.lower())

    def test_every_attempt_of_a_retried_call_keeps_its_headers(self):
        """glm F18: providers._with_backoff retries a 429; the first attempt's instance header is evidence too."""
        import urllib.error
        g, n = Gateway([('{"a": 1}', "stop")]), [0]

        def flaky(req, timeout=None):
            n[0] += 1
            if n[0] == 1:
                h = Message()
                h["X-BF-Instance"] = "vllm-3"
                raise urllib.error.HTTPError(req.full_url, 429, "slow down", h, io.BytesIO(b"{}"))
            return g(req, timeout)
        with mock.patch("urllib.request.urlopen", flaky), mock.patch.object(RT.P, "BACKOFF_S", (0,)):
            row = RT.ask(self.b, rec(), "with")
        self.assertEqual([(a["status"], a["response_headers"]["x-bf-instance"]) for a in row["attempts"]],
                         [(429, "vllm-3"), (200, "pinga282")])                # names lowercased, both kept
        self.assertEqual((row["status"], row["shape"]), (200, "closed JSON"))

    def test_a_failed_call_is_a_row_with_the_responses_headers(self):
        import urllib.error

        def refuse(req, timeout=None):
            h = Message()
            h["x-bf-instance"] = "gw-1"
            raise urllib.error.HTTPError(req.full_url, 400, "bad", h, io.BytesIO(b"{}"))
        with mock.patch("urllib.request.urlopen", refuse):
            row = RT.ask(self.b, rec(), "with")
        self.assertIn("error", row)
        self.assertEqual((row["status"], row["response_headers"]["x-bf-instance"]), (400, "gw-1"))
        self.assertNotIn(KEY, json.dumps(row))


class TestRun(unittest.TestCase):
    def test_both_legs_alternating_resumed_and_stopped_at_the_cap(self):
        with tempfile.TemporaryDirectory() as d:
            src = [{"record": f"rec{i}.json", "type": "step_a", "out_tokens": t, "shape": "truncated"}
                   for i, t in enumerate((7, 122, 171, 497, 1564, 900))]
            for s in src:
                with open(os.path.join(d, s["record"]), "w") as f:
                    json.dump(rec(), f)
            b = RT.backend()
            b.key = lambda name: KEY
            res, spend = os.path.join(d, "RESULTS.jsonl"), os.path.join(d, "SPEND.json")
            real = RT.SPEND
            before = os.path.exists(real)
            g = Gateway([('{"a": 1}', "stop")] * 12)
            with mock.patch.object(RT, "unclosed", lambda: src), mock.patch.object(RT, "WT", d), \
                    mock.patch.object(RT, "SPEND", spend), mock.patch("urllib.request.urlopen", g):
                RT.run(3, b, stop_usd=1.0, results=res)
                rows = [json.loads(x) for x in open(res)]
                self.assertEqual([r["leg"] for r in rows], ["with", "without", "without", "with", "with", "without"])
                RT.run(3, b, stop_usd=1.0, results=res)                         # resumed: nothing asked again
                self.assertEqual(len(g.seen), 6)
                RT.run(4, b, stop_usd=0.0005, results=res)                      # the ledger holds 0.0006: stopped
                self.assertEqual(len(g.seen), 6)
                self.assertAlmostEqual(RT.spent(spend), 0.0006)
            self.assertEqual(os.path.exists(real), before)                      # the real ledger never touched

    def test_an_unpriced_reply_counts_at_the_bound_and_the_report_survives_no_calls(self):
        """A reply with no cost is counted at UNREPORTED_USD on its own ledger line, so the stop never reads it as $0;
        a report with no RESULTS file (stopped at once) is written, not a crash."""
        with tempfile.TemporaryDirectory() as d:
            spend = os.path.join(d, "SPEND.json")
            b = RT.backend()
            b.key = lambda name: KEY
            g = Gateway([('{"a": 1}', "stop")])

            def unpriced(req, timeout=None):
                r = g(req, timeout)
                body = json.loads(r.getvalue())
                del body["usage"]["cost"]
                r2 = io.BytesIO(json.dumps(body).encode())
                r2.status, r2.headers = r.status, r.headers
                return r2
            with mock.patch("urllib.request.urlopen", unpriced), mock.patch.object(RT, "SPEND", spend):
                row = RT.ask(b, rec(), "with")
                RT.add_spend(row.get("usd_reported"), row.get("usd_unreported_estimate"))
                self.assertEqual((row["usd_reported"], row["usd_unreported_estimate"]), (None, RT.UNREPORTED_USD))
                self.assertAlmostEqual(RT.spent(), RT.UNREPORTED_USD)
            with mock.patch.object(RT, "OUT", d):
                s = RT.report(os.path.join(d, "none.jsonl"))
            self.assertEqual((s["calls"], s["with"]["unclosed"]), (0, 0))
            self.assertTrue(os.path.exists(os.path.join(d, "REPORT.md")))

    def test_an_unreadable_ledger_stops_before_any_call(self):
        with tempfile.TemporaryDirectory() as d:
            spend = os.path.join(d, "SPEND.json")
            with open(spend, "w") as f:
                f.write("{torn")
            g = Gateway([('{"a": 1}', "stop")])
            with mock.patch.object(RT, "SPEND", spend), mock.patch.object(RT, "unclosed", lambda: [
                    {"record": f"x{t}.json", "type": "t", "out_tokens": t, "shape": "truncated"} for t in RT.NAMED]), \
                    mock.patch("urllib.request.urlopen", g):
                with self.assertRaises(RuntimeError):
                    RT.run(1, RT.backend(), results=os.path.join(d, "R.jsonl"))
            self.assertEqual(g.seen, [])


if __name__ == "__main__":
    unittest.main()
