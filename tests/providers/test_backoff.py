#!/usr/bin/env python3
"""A reply cut mid-body is a transport failure: retried on the backoff, then Unavailable, so the chain fails over as
for any other transport failure. At 00:46 ET Nov 15 Heimdall cut a reply 43,669 bytes in; http.client.IncompleteRead
(an HTTPException, not an OSError) escaped providers._with_backoff as itself and ended ruling 110's replay of one
model. Offline: the real HeimdallBackend and Router; urlopen and the backoff's sleep are stubbed."""
import http.client
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import providers as P  # noqa: E402
from test_providers import Fake, router  # noqa: E402

def cut():
    return http.client.IncompleteRead(b"{" * 10, 21278)


class Cut:
    """An HTTP response whose body ends before its Content-Length: read() raises IncompleteRead."""

    def read(self):
        raise cut()


class TestACutReplyIsATransportFailure(unittest.TestCase):

    def test_a_cut_reply_or_a_dropped_connection_is_retried_on_the_backoff_and_the_next_try_answers(self):
        for first in (cut, lambda: http.client.BadStatusLine("")):
            tries, waits = [], []

            def fn():
                tries.append(1)
                if len(tries) == 1:
                    raise first()
                return {"ok": 1}
            with mock.patch.object(P.time, "sleep", waits.append):
                self.assertEqual(P._with_backoff(fn), {"ok": 1})
            self.assertEqual((len(tries), waits), (2, [P.BACKOFF_S[0]]))

    def test_any_other_http_error_cannot_answer_and_is_unavailable_at_once(self):
        tries, waits = [], []

        def fn():
            tries.append(1)
            raise http.client.ImproperConnectionState()
        with mock.patch.object(P.time, "sleep", waits.append), self.assertRaises(P.Unavailable) as cm:
            P._with_backoff(fn)
        self.assertEqual((len(tries), waits), (1, []))                # no backoff: no retry can help
        self.assertIn("ImproperConnectionState (final)", str(cm.exception))

    def test_a_reply_cut_every_time_is_unavailable_and_the_chain_fails_over(self):
        with tempfile.TemporaryDirectory() as d:
            h = P.HeimdallBackend("heimdall:deepseek/x", {"vendor": "heimdall", "model": "deepseek/x",
                                                          "base_url": "http://gateway.invalid/api/v1",
                                                          "price_usd_per_1m": [3, 15], "family": "deepseek"},
                                  "/nonexistent")
            h.key = lambda name: "test-key"
            nxt = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
            led = os.path.join(d, "SPEND.json")
            r = router(d, [h, nxt], {"check": ["heimdall:deepseek/x", "heimdall:qwen"]}, spend_path=led, limit_usd=50.0,
                       limit_basis="reported")
            r.backends = {h.name: h, nxt.name: nxt}
            asked, waits = [], []

            def urlopen(req, timeout=None):
                asked.append(req.full_url)
                return Cut()
            with mock.patch.object(P.urllib.request, "urlopen", urlopen), \
                    mock.patch.object(P.time, "sleep", waits.append):
                rep = r.call("check", "p", 100, 7)
            self.assertEqual((rep.text, rep.backend), ('{"ok": 2}', "heimdall:qwen"))
            tries = [u for u in asked if u.endswith("/chat/completions")]   # (the 90 % tripwire asks /credits)
            self.assertEqual(len(tries), len(P.BACKOFF_S) + 1)          # every try, then Unavailable
            self.assertEqual(waits, list(P.BACKOFF_S))
            self.assertIn("IncompleteRead", rep.tried[0][1])
            self.assertIn(h.name, r.down)                               # down for the run, as any transport failure
            spent = json.load(open(led))                                # its reservation released, nothing booked for
            self.assertEqual((spent["reserved"], list(spent["by_backend"]), spent["calls"]),   # the cut tries; the
                             ({}, ["heimdall:qwen"], 1))                # answer booked once


if __name__ == "__main__":
    unittest.main()
