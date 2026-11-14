#!/usr/bin/env python3
"""pipeline/providers.py (law L-x): one interface, a chain per role, the run continues when a vendor is down, verdicts
never on the writer's vendor or model family, every exchange recorded and replayable, an invalid reply never served
again, spend guarded (reserve the upper bound, fail closed, free back-ends never stopped). Offline: fake back-ends."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import providers as P  # noqa: E402


class Fake(P.Backend):
    def __init__(self, name, vendor, answer=None, fail=None, usage=None, price=(10, 100), family=None):
        spec = {"model": name.split(":", 1)[1], "price_usd_per_1m": list(price)}
        if family:
            spec["family"] = family
        super().__init__(name, spec, "/nonexistent")
        self.vendor, self.answer, self.fail, self.calls = vendor, answer, fail, 0
        self._usage = usage or {"in": 1000, "out": 100}

    def complete(self, prompt, max_tokens, seed, system=None):
        self.calls += 1
        if isinstance(self.fail, Exception):
            raise self.fail
        if self.fail:
            raise P.Unavailable(self.fail)
        return self.answer, dict(self._usage), 0.01


class FakeSTT(P.STTBackend):
    def __init__(self, name, vendor, result=None, fail=None):
        super().__init__(name, {"model": name.split(":", 1)[1], "price_usd_per_min": 0.01}, "/nonexistent")
        self.vendor, self.result, self.fail, self.calls = vendor, result, fail, 0

    def transcribe(self, wav):
        self.calls += 1
        if self.fail:
            raise P.Unavailable(self.fail)
        return self.result, 0.01


def router(tmp, backends, roles, **kw):
    cfg = os.path.join(tmp, "cfg.json")
    json.dump({"schema": "pp.providers/1",
               "backends": {b.name: {"vendor": "openai", "model": b.model} for b in backends},
               "roles": {r: {"chain": c} for r, c in roles.items()}}, open(cfg, "w"))
    r = P.Router(cfg, env_path="/nonexistent", **kw)
    r.backends = {b.name: b for b in backends}
    return r


def wav(tmp, seconds=2.0):
    import wave
    p = os.path.join(tmp, "a.wav")
    with wave.open(p, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return p


class Slow(Fake):
    """A back-end that answers only after `delay` seconds (a Heimdall angle call that hangs)."""

    def __init__(self, name, vendor, answer, delay, **kw):
        super().__init__(name, vendor, answer=answer, **kw)
        self.delay = delay

    def complete(self, prompt, max_tokens, seed, system=None):
        import time as _t
        _t.sleep(self.delay)
        return super().complete(prompt, max_tokens, seed, system)


class SlowFail(Slow):
    """A back-end that fails only after `delay` seconds (a call abandoned at its deadline that never answers)."""

    def complete(self, prompt, max_tokens, seed, system=None):
        import time as _t
        _t.sleep(self.delay)
        raise P.Unavailable("HTTP 504 after the deadline")


def wait_for(path, kind, timeout=5.0):
    """The deadline log's lines once one of `kind` is in it (an abandoned thread ends on its own clock)."""
    import time as _t
    t0 = _t.time()
    while _t.time() - t0 < timeout:
        if os.path.exists(path):
            with open(path) as f:
                log = [json.loads(x) for x in f]
            if any(x["kind"] == kind for x in log):
                return log
        _t.sleep(0.05)
    raise AssertionError(f"no {kind} line in {timeout} s")


class TestDeadline(unittest.TestCase):
    """Orchestrator 22:40 ruling 5: one writer call never waits more than its deadline; it fails over to the next
    back-end, and the failover is recorded. RULING 83 (a) (20:33 Nov 13): the abandoned call is booked at its PROMPT
    tokens at the listed input rate (not the upper bound of a full answer); a late answer's own figure replaces it."""

    def test_a_call_that_passes_its_deadline_fails_over_and_is_recorded(self):
        import tempfile
        import time as _t
        with tempfile.TemporaryDirectory() as d:
            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.8, family="deepseek",
                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
            r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0,
                       deadline_log=os.path.join(d, "DEADLINES.jsonl"))
            t0 = _t.time()
            rep = r.call("angle_write", "p", 100, 7, deadline_s=0.3)
            with open(os.path.join(d, "DEADLINES.jsonl")) as f:                          # item 55: the evidence
                log = [json.loads(x) for x in f]
            self.assertEqual([(x["kind"], x["model"], x["prompt_chars"], x["max_tokens"], x["deadline_s"]) for x in log],
                             [("missed_deadline", "heimdall:deepseek", 1, 100, 0.3)])
            self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
            self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
            self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
            self.assertIn("abandoned at the deadline; booked at its prompt tokens", rep.tried[0][1])
            led = json.load(open(os.path.join(d, "SPEND.json")))
            booked = slow.prompt_usd("p")                              # ruling 83 (a): 201 tokens at $10 / 1M
            self.assertAlmostEqual(booked, 201 * 10 / 1e6, places=9)
            self.assertLess(booked, slow.upper_usd("p", 100) / 5)     # not the upper bound of a full answer
            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)
            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"], booked, places=6)
            self.assertAlmostEqual(led["usd_unreported_estimate"], booked + next_.usd({"in": 1000, "out": 100}),
                                   places=6)                           # the answer that was used: no vendor figure
            self.assertAlmostEqual(log[0]["booked_usd"], booked, places=9)
            self.assertEqual(led["reserved"], {})                      # no reservation left behind
            log = wait_for(os.path.join(d, "DEADLINES.jsonl"), "late_answer")   # then the vendor's figure arrives
            late = [x for x in log if x["kind"] == "late_answer"]
            self.assertEqual([(x["model"], x["usd_reported"], x["replaced"], x["booked_usd"]) for x in late],
                             [("heimdall:deepseek", 0.0123, True, booked)])
            led = json.load(open(os.path.join(d, "SPEND.json")))
            b = led["by_backend"]["heimdall:deepseek"]
            self.assertEqual((b["calls"], b["in"], b["out"], b["reported_calls"], led["late_answers"]),
                             (1, 1000, 100, 1, 1))                     # still one call, now with its own counts
            self.assertAlmostEqual(b["usd_reported"], 0.0123, places=9)
            self.assertAlmostEqual(b["usd_estimate"], slow.usd({"in": 1000, "out": 100}), places=6)
            self.assertAlmostEqual(led["usd_reported"], 0.0123, places=9)        # the booking is replaced, not added
            self.assertAlmostEqual(led["usd_unreported_estimate"], next_.usd({"in": 1000, "out": 100}), places=6)
            self.assertAlmostEqual(led["usd_estimate"], slow.usd({"in": 1000, "out": 100}) +
                                   next_.usd({"in": 1000, "out": 100}), places=6)
            self.assertEqual(led["reserved"], {})

    def test_ruling_83_a_a_late_error_leaves_the_booking_and_a_late_answer_without_a_figure_is_its_estimate(self):
        import tempfile
        for cls, usage, kind in ((SlowFail, None, "late_error"), (Slow, {"in": 3000, "out": 500}, "late_answer")):
            with tempfile.TemporaryDirectory() as d:
                slow = cls("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.5, family="glm", usage=usage)
                next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen",
                             usage={"in": 10, "out": 10, "usd_reported": 0.001})
                path = os.path.join(d, "DEADLINES.jsonl")
                r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]},
                           spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0, limit_basis="reported",
                           deadline_log=path)
                self.assertEqual(r.call("check", "pp", 100, 7, deadline_s=0.1).backend, "heimdall:qwen")
                booked = slow.prompt_usd("pp")
                self.assertAlmostEqual(r.spent(), booked + 0.001, places=6)   # the reported basis: booking + figure
                log = wait_for(path, kind)
                led = json.load(open(os.path.join(d, "SPEND.json")))
                if kind == "late_error":                               # no answer: the booking stands
                    self.assertIn("HTTP 504", [x for x in log if x["kind"] == kind][0]["error"])
                    self.assertAlmostEqual(led["usd_unreported_estimate"], booked, places=6)
                    self.assertNotIn("late_answers", led)
                else:                                                  # an answer, no vendor figure: its estimate
                    est = slow.usd(usage)
                    self.assertAlmostEqual(led["usd_unreported_estimate"], est, places=6)
                    self.assertAlmostEqual(r.spent(), est + 0.001, places=6)
                    self.assertIsNone([x for x in log if x["kind"] == kind][0]["usd_reported"])

    def test_ruling_83_a_an_unreadable_ledger_at_the_deadline_stops_the_call_and_the_miss_is_logged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            spend, path = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")

            class Corrupts(Slow):                                       # the ledger breaks while the call is out
                def complete(self, prompt, max_tokens, seed, system=None):
                    with open(spend, "w") as f:
                        f.write("{ corrupt")
                    return super().complete(prompt, max_tokens, seed, system)
            slow = Corrupts("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.4, family="glm")
            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
            r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]}, spend_path=spend,
                       limit_usd=50.0, deadline_log=path)
            with self.assertRaises(P.SpendLimit):                       # fail closed: no paid call on an unreadable
                r.call("check", "pp", 100, 7, deadline_s=0.1)          # total, as before
            self.assertEqual(next_.calls, 0)
            with open(path) as f:                                       # the miss is on record all the same
                self.assertEqual([json.loads(x)["kind"] for x in f], ["missed_deadline"])
            import time as _t
            _t.sleep(0.6)                                               # the abandoned thread ends: nothing to do
            with open(path) as f:
                self.assertEqual([json.loads(x)["kind"] for x in f], ["missed_deadline"])
            self.assertEqual(open(spend).read(), "{ corrupt")          # never overwritten

    def test_ruling_83_a_a_late_answer_that_cannot_be_booked_is_on_record_and_the_booking_stands(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            spend, path = os.path.join(d, "SPEND.json"), os.path.join(d, "DEADLINES.jsonl")
            slow = Slow("heimdall:glm", "heimdall", '{"ok": 1}', delay=0.5, family="glm",
                        usage={"in": 1000, "out": 100, "usd_reported": 0.0123})
            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
            r = router(d, [slow, next_], {"check": ["heimdall:glm", "heimdall:qwen"]}, spend_path=spend,
                       limit_usd=50.0, deadline_log=path)
            r.call("check", "pp", 100, 7, deadline_s=0.1)
            with open(spend, "w") as f:                                  # the ledger breaks before the late answer
                f.write("{ corrupt")
            late = [x for x in wait_for(path, "late_answer") if x["kind"] == "late_answer"]
            self.assertEqual((late[0]["replaced"], late[0]["usd_reported"]), (False, 0.0123))
            self.assertIn("SpendLimit", late[0]["ledger_error"])
            self.assertEqual(open(spend).read(), "{ corrupt")

    def test_ruling_83_a_the_booking_always_comes_before_the_late_answer(self):
        import threading
        go, order = threading.Event(), []

        def fn():                                                       # answers only once the test lets it
            go.wait(5)
            order.append("answered")
            return "late"

        def abandon():
            order.append("booked")
            go.set()                                                    # the answer races the booking
            import time as _t
            _t.sleep(0.3)
            order.append("booked done")
            return {"k": 1}
        done = threading.Event()

        def late(ab, value, error):
            order.append(("late", ab, value, error))
            done.set()
        with self.assertRaises(P.DeadlineExceeded):
            P._within(0.05, fn, on_abandon=abandon, on_late=late)
        self.assertTrue(done.wait(5))
        self.assertEqual(order, ["booked", "answered", "booked done", ("late", {"k": 1}, "late", None)])
        self.assertEqual(P._within(1.0, lambda: 7, on_abandon=abandon, on_late=late), 7)   # in time: neither runs
        self.assertEqual(len(order), 4)

    @staticmethod
    def lines(path):
        with open(path) as f:
            return len(f.read().splitlines())

    def test_item_55_a_slow_answer_is_logged_and_no_log_writes_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            class Took(Fake):                                           # a back-end reports its own seconds
                def complete(self, prompt, max_tokens, seed, system=None):
                    text, usage, _ = super().complete(prompt, max_tokens, seed, system)
                    return text, usage, 0.25
            slow = Took("heimdall:deepseek", "heimdall", answer='{"ok": 1}', family="deepseek")
            path = os.path.join(d, "DEADLINES.jsonl")
            r = router(d, [slow], {"check": ["heimdall:deepseek"]}, deadline_log=path, slow_log_s=0.2)
            r.call("check", "pp", 50, 7)                                # no deadline, answered in 0.25 s >= 0.2 s
            with open(path) as f:
                log = [json.loads(x) for x in f]
            self.assertEqual([(x["kind"], x["prompt_chars"], x["in"], x["out"]) for x in log],
                             [("answered_slowly", 2, 1000, 100)])
            self.assertGreaterEqual(log[0]["seconds"], 0.2)
            fast = Fake("heimdall:qwen", "heimdall", answer="{}")
            router(d, [fast], {"check": ["heimdall:qwen"]}, deadline_log=path, slow_log_s=0.2).call("check", "p")
            self.assertEqual(self.lines(path), 1)   # a fast answer is not evidence
            router(d, [Took("heimdall:x", "heimdall", answer="{}")], {"check": ["heimdall:x"]},
                   slow_log_s=0.2).call("check", "p")                   # no deadline_log: nothing written
            self.assertEqual(self.lines(path), 1)

    def test_an_answer_inside_the_deadline_and_an_error_keep_their_meaning(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ok = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=0.05)
            r = router(d, [ok], {"angle_write": ["heimdall:deepseek"]})
            self.assertEqual(r.call("angle_write", "p", 100, 7, deadline_s=5).text, '{"ok": 1}')
            bad = Fake("heimdall:deepseek", "heimdall", fail="HTTP 503")
            r2 = router(d, [bad], {"angle_write": ["heimdall:deepseek"]})
            with self.assertRaises(P.ProviderError) as cm:            # the back-end's own error, not a deadline
                r2.call("angle_write", "p", 100, 7, deadline_s=5)
            self.assertIn("HTTP 503", str(cm.exception))


class TestRouter(unittest.TestCase):
    def test_the_chain_fails_over_and_names_the_model_that_answered(self):
        with tempfile.TemporaryDirectory() as d:
            a = Fake("openai:x", "openai", fail="HTTP 429 insufficient_quota (final: account)")
            b = Fake("anthropic:y", "anthropic", answer='{"ok": 1}')
            r = router(d, [a, b], {"write": ["openai:x", "anthropic:y"]})
            rep = r.call("write", "p")
            self.assertEqual((rep.text, rep.backend, rep.vendor), ('{"ok": 1}', "anthropic:y", "anthropic"))
            self.assertEqual(rep.tried[0][0], "openai:x")
            r.call("write", "p2")
            self.assertEqual(a.calls, 1)                    # down for the rest of the run: not asked again

    def test_a_refused_request_skips_the_backend_for_that_call_only(self):
        with tempfile.TemporaryDirectory() as d:
            a = Fake("local:g", "local", fail=P.RequestRejected("prompt over the local context"), price=(0, 0))
            b = Fake("xai:z", "xai", answer='{"v": 1}')
            r = router(d, [a, b], {"verdict": ["local:g", "xai:z"]})
            self.assertEqual(r.call("verdict", "a long prompt").backend, "xai:z")
            self.assertNotIn("local:g", r.down)               # never down for the run
            a.fail, a.answer = None, '{"v": 2}'
            self.assertEqual(r.call("verdict", "a short prompt").backend, "local:g")

    def test_a_verdict_never_runs_on_the_vendors_or_families_of_the_text_it_judges(self):
        with tempfile.TemporaryDirectory() as d:
            a = Fake("openai:x", "openai", answer="{}")
            b = Fake("xai:z", "xai", answer='{"v": 1}')
            g = Fake("heimdall:gem", "heimdall", answer='{"v": 2}', family="gemma")
            r = router(d, [a, g, b], {"verdict": ["openai:x", "heimdall:gem", "xai:z"]})
            rep = r.call("verdict", "p", avoid_vendor={"openai", "anthropic"}, avoid_family={"gemma"})
            self.assertEqual(rep.backend, "xai:z")
            self.assertEqual((a.calls, g.calls), (0, 0))
            with self.assertRaises(P.ProviderError):
                router(d, [a], {"verdict": ["openai:x"]}).call("verdict", "p", avoid_vendor="openai")

    def test_every_backend_down_is_a_failed_role_never_a_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r = router(d, [Fake("openai:x", "openai", fail="HTTP 503"), Fake("xai:z", "xai", fail="URLError")],
                       {"mine": ["openai:x", "xai:z", "heimdall:missing"]})
            with self.assertRaises(P.ProviderError) as cm:
                r.call("mine", "p")
            self.assertIn("HTTP 503", str(cm.exception))
            self.assertIn("not in config backends", str(cm.exception))
            with self.assertRaises(P.ProviderError):
                r.call("unknown_role", "p")

    def test_record_then_replay_offline_and_cached_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as d:
            a = Fake("anthropic:y", "anthropic", answer='{"ok": 1}')
            rec = os.path.join(d, "rec")
            r = router(d, [a], {"write": ["anthropic:y"]}, record_dir=rec)
            first = r.call("write", "p", seed=7)
            self.assertEqual((first.replayed, first.cached), (False, False))
            again = r.call("write", "p", seed=7)              # a live run served the recording: cached, not replayed
            self.assertEqual((again.replayed, again.cached, a.calls), (False, True, 1))
            rp = router(d, [Fake("anthropic:y", "anthropic", fail="must not be called")], {"write": ["anthropic:y"]},
                        record_dir=rec, replay=True)
            rep = rp.call("write", "p", seed=7)
            self.assertEqual((rep.text, rep.backend, rep.replayed), ('{"ok": 1}', "anthropic:y", True))
            with self.assertRaises(P.ReplayMiss):
                rp.call("write", "p", seed=8)               # another attempt is its own exchange

    def test_a_rejected_reply_is_asked_again_never_served_again(self):
        with tempfile.TemporaryDirectory() as d:
            a = Fake("anthropic:y", "anthropic", answer="not json")
            r = router(d, [a], {"write": ["anthropic:y"]}, record_dir=os.path.join(d, "rec"))
            bad = r.call("write", "p")
            self.assertTrue(r.reject(bad, "not one JSON object"))
            a.answer = '{"ok": 1}'
            self.assertEqual((r.call("write", "p").text, a.calls), ('{"ok": 1}', 2))

    def test_ruling_48_the_limit_counts_vendor_reported_dollars(self):
        """Ruling 48 (07:02 Nov 13): the cap counts the vendors' own reported dollars, plus the estimate for a call
        whose vendor reports none; the price-table estimate (12x high on xAI) no longer binds."""
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "SPEND.json")
            json.dump({"usd_estimate": 39.5, "calls": 400, "by_backend": {}, "by_role": {}, "reserved": {},
                       "usd_reported": 3.46, "usd_unreported_estimate": 1.81}, open(led, "w"))
            a = Fake("openai:x", "openai", answer="{}", usage={"in": 1000, "out": 100})        # no vendor figure
            rep = Fake("openai:y", "openai", answer="{}", usage={"in": 1000, "out": 100, "usd_reported": 0.001})
            p = "p" * 50_000
            with self.assertRaises(P.SpendLimit):                   # the old basis: 39.5 + the upper bound > 40
                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=40).call("write", p)
            r = router(d, [a, rep], {"write": ["openai:x"], "judge": ["openai:y"]}, spend_path=led, limit_usd=12,
                       limit_basis="reported")
            self.assertAlmostEqual(r.spent(), 5.27, places=6)
            r.call("write", p)                                      # 5.27 + its upper bound < 12: it runs
            self.assertAlmostEqual(r.spent(), 5.27 + 0.02, places=6)                 # no figure: its estimate counts
            r.call("judge", p)
            self.assertAlmostEqual(r.spent(), 5.29 + 0.001, places=6)                # a figure: only the figure counts
            self.assertGreater(json.load(open(led))["usd_estimate"], 39.5)
            r.limit_usd = r.spent() + 0.05
            with self.assertRaises(P.SpendLimit):                   # spent + this call's upper bound > the limit
                r.call("write", p)
            self.assertEqual(json.load(open(led))["reserved"], {})
            with self.assertRaises(ValueError):
                router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_basis="dollars")
            json.dump({"usd_estimate": 1.0, "calls": 3, "by_backend": {}, "by_role": {}, "reserved": {}},
                      open(led, "w"))                       # calls, but no reported figures: never a silent 0.0
            with self.assertRaises(P.SpendLimit):
                r.spent()

    def test_the_spend_guard_reserves_the_upper_bound_and_never_passes_the_limit(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "SPEND.json")
            a = Fake("openai:x", "openai", answer="{}", usage={"in": 400_000, "out": 0})        # $4.00 a call
            r = router(d, [a], {"write": ["openai:x"]}, spend_path=led, limit_usd=10)
            p = "p" * 400_000                                     # upper bound ~ $4.00 in + $0.20 out
            r.call("write", p)
            r.call("write", p)
            with self.assertRaises(P.SpendLimit):
                r.call("write", p)                                # 8.00 + 4.20 > 10: refused BEFORE it runs
            d_ = json.load(open(led))
            self.assertEqual((d_["calls"], a.calls, d_["reserved"]), (2, 2, {}))
            self.assertLessEqual(d_["usd_estimate"], 10)
            free = Fake("local:g", "local", answer="{}", price=(0, 0))
            rf = router(d, [free], {"write": ["local:g"]}, spend_path=led, limit_usd=1)
            self.assertEqual(rf.call("write", "p").backend, "local:g")      # a free back-end is never stopped

    def test_an_unreadable_ledger_stops_every_paid_call_and_a_failed_call_releases_its_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            led = os.path.join(d, "SPEND.json")
            open(led, "w").write("{ corrupt")
            r = router(d, [Fake("openai:x", "openai", answer="{}")], {"write": ["openai:x"]}, spend_path=led)
            with self.assertRaises(P.SpendLimit):
                r.call("write", "p")
            self.assertEqual(open(led).read(), "{ corrupt")      # never overwritten from zero
            os.remove(led)
            r2 = router(d, [Fake("openai:x", "openai", fail="HTTP 503")], {"write": ["openai:x"]}, spend_path=led)
            with self.assertRaises(P.ProviderError):
                r2.call("write", "p")
            self.assertEqual(json.load(open(led))["reserved"], {})

    def test_transcription_runs_its_own_chain_with_failover_record_and_replay(self):
        with tempfile.TemporaryDirectory() as d:
            res = {"text": "Bitcoin is not going to zero.", "segments": [{"speaker": "A", "start": 0.1, "end": 1.9,
                                                                           "text": "Bitcoin is not going to zero."}]}
            a = FakeSTT("openai_stt:t", "openai", fail="HTTP 429 insufficient_quota (final: account)")
            b = FakeSTT("elevenlabs_stt:s", "elevenlabs", result=res)
            rec = os.path.join(d, "rec")
            r = router(d, [a, b], {"transcribe": ["openai_stt:t", "elevenlabs_stt:s"]}, record_dir=rec)
            got, rep = r.transcribe("transcribe", wav(d))
            self.assertEqual((got, rep.backend, rep.tried[0][0]), (res, "elevenlabs_stt:s", "openai_stt:t"))
            rp = router(d, [FakeSTT("openai_stt:t", "openai", fail="x"), FakeSTT("elevenlabs_stt:s", "elevenlabs",
                                                                                 fail="must not be called")],
                        {"transcribe": ["openai_stt:t", "elevenlabs_stt:s"]}, record_dir=rec, replay=True)
            got2, rep2 = rp.transcribe("transcribe", wav(d))
            self.assertEqual((got2, rep2.replayed), (res, True))

    def test_the_local_backend_without_its_gpu_lease_is_unavailable(self):
        b = P.LocalBackend("local:gemma3:27b", {"model": "gemma3:27b"}, "/nonexistent", llm=None)
        with self.assertRaises(P.Unavailable):
            b.complete("p", 10, 7)

    def test_the_shipped_config_keeps_every_verdict_off_every_possible_writer(self):
        cfg = json.load(open(P.CONFIG))
        be = cfg["backends"]
        for name, spec in be.items():
            self.assertTrue(spec.get("family"), name)                           # law L-x: model family named
            if spec["vendor"] == "heimdall":
                self.assertTrue(spec.get("base_url"), name)
        for role, spec in cfg["roles"].items():
            if role == "trend_brief":
                self.assertIn("fallback", spec)              # the free local baseline is its second back-end
                continue
            self.assertGreaterEqual(len(spec["chain"]), 2, role)
            for b in spec["chain"]:
                self.assertIn(b, be, (role, b))
        local = [n for n, s in be.items() if s["vendor"] == "local"]
        self.assertEqual(cfg["roles"]["mine"]["chain"][0], local[0])             # Ultron first (L-x)
        self.assertTrue(all(be[b]["vendor"].endswith("_stt") for b in cfg["roles"]["transcribe"]["chain"]))
        for role in ("fidelity_verdict", "context_verdict", "viewer_takeaway", "coherence_verdict"):
            for writer in cfg["roles"]["angle_write"]["chain"]:
                w = be[writer]
                left = [b for b in cfg["roles"][role]["chain"]
                        if be[b]["vendor"] != w["vendor"] and be[b]["family"] != w["family"]]
                self.assertGreaterEqual(len(left), 2, (role, writer))           # still a chain, never one back-end
        miners = cfg["roles"]["mine"]["chain"]
        for m in miners:
            left = [b for b in cfg["roles"]["exclusion_verdict"]["chain"] if b != m]
            self.assertGreaterEqual(len(left), 2, m)

    def test_role_model_maps_failures_into_select_by_id(self):
        import select_by_id as SB
        with tempfile.TemporaryDirectory() as d:
            r = router(d, [Fake("openai:x", "openai", fail="HTTP 503")], {"story": ["openai:x"]})
            with self.assertRaises(SB.ModelError):
                P.RoleModel(r, "story").complete("p", 10, 7)
            ok = router(d, [Fake("xai:z", "xai", answer='{"story": [], "claim": null}')], {"story": ["xai:z"]})
            text, meta = P.RoleModel(ok, "story").complete("p", 10, 7)
            self.assertEqual(meta["backend"], "xai:z")



class TestRuling85Routing(unittest.TestCase):
    """RULING 85 (21:15 Nov 13): Heimdall first for every verdict, Grok last, behind a switch; the two-family rule kept
    INSIDE Heimdall (each family its own maker); the 20:33 order: ruling 82's 120 s on Heimdall for every verdict role,
    and an answer out of contract moves on (providers.call_parsed)."""

    def cfg(self, d, mode="today"):
        p = os.path.join(d, "cfg.json")
        json.dump({"schema": "pp.providers/1",
                   "backends": {"xai:grok": {"vendor": "xai", "model": "grok", "family": "grok"},
                                "heimdall:deepseek": {"vendor": "heimdall", "model": "deepseek", "family": "deepseek"},
                                "heimdall:glm": {"vendor": "heimdall", "model": "glm", "family": "glm"},
                                "heimdall:qwen": {"vendor": "heimdall", "model": "qwen", "family": "qwen"}},
                   "roles": {"coherence_verdict": {"chain": ["xai:grok", "heimdall:deepseek", "heimdall:glm",
                                                             "heimdall:qwen"]},
                             "mine": {"chain": ["heimdall:qwen", "xai:grok"]}},
                   "routing": {"mode": mode, "verdict_roles": ["coherence_verdict"],
                               "verdict_deadline_s": {"heimdall": 120},
                               "heimdall_first": {"coherence_verdict": ["heimdall:deepseek", "heimdall:glm",
                                                                        "heimdall:qwen", "xai:grok"]}}}, open(p, "w"))
        return p

    def fakes(self):
        return [Fake("xai:grok", "xai", answer="x", family="grok"),
                Fake("heimdall:deepseek", "heimdall", answer="d", family="deepseek"),
                Fake("heimdall:glm", "heimdall", answer="g", family="glm"),
                Fake("heimdall:qwen", "heimdall", answer="q", family="qwen")]

    def router(self, d, mode=None, cfg_mode="today"):
        r = P.Router(self.cfg(d, cfg_mode), env_path="/nonexistent", routing=mode)
        fs = self.fakes()
        if r.routing == "heimdall_first":          # the router's own init re-keyed its real back-ends; fakes too
            for b in fs:
                if b.vendor == "heimdall":
                    b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
        r.backends = {b.name: b for b in fs}
        return r

    def test_today_is_unchanged_and_heimdall_first_puts_grok_last(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            t = self.router(d)
            self.assertEqual(t.routing, "today")
            self.assertEqual(t.call("coherence_verdict", "p").backend, "xai:grok")
            self.assertEqual(t.chain("mine"), ["heimdall:qwen", "xai:grok"])
            h = self.router(d, "heimdall_first")
            self.assertEqual(h.chain("coherence_verdict"), ["heimdall:deepseek", "heimdall:glm", "heimdall:qwen",
                                                            "xai:grok"])
            self.assertEqual(h.chain("mine"), ["heimdall:qwen", "xai:grok"])   # a role the routing names not: as is
            self.assertEqual(h.call("coherence_verdict", "p").backend, "heimdall:deepseek")
            self.assertEqual(self.router(d, cfg_mode="heimdall_first").routing, "heimdall_first")  # the config's mode
            with self.assertRaises(ValueError):
                P.Router(self.cfg(d), env_path="/nonexistent", routing="grok_only")

    def test_the_two_family_rule_inside_heimdall(self):
        """A Heimdall writer (deepseek) is judged by another Heimdall family (glm) under heimdall_first; today the
        vendor rule leaves only Grok; the router's own init re-keys a real Heimdall back-end's vendor."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            h = self.router(d, "heimdall_first")
            r = h.call("coherence_verdict", "p", avoid_vendor={"heimdall/deepseek"}, avoid_family={"deepseek"})
            self.assertEqual((r.backend, r.vendor), ("heimdall:glm", "heimdall/glm"))
            t = self.router(d)
            r = t.call("coherence_verdict", "p", avoid_vendor={"heimdall"}, avoid_family={"deepseek"})
            self.assertEqual(r.backend, "xai:grok")
            real = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first")
            b = real.backends["heimdall:glm"]
            self.assertEqual((b.vendor, P.gateway(b), real.backends["xai:grok"].vendor), ("heimdall/glm", "heimdall",
                                                                                           "xai"))
            self.assertEqual(P.gateway(P.Router(self.cfg(d), env_path="/nonexistent").backends["heimdall:glm"]),
                             "heimdall")

    def test_a_verdict_role_gets_120_s_on_heimdall_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            h = self.router(d, "heimdall_first")
            self.assertEqual(h.role_deadline("coherence_verdict", h.backends["heimdall:glm"]), 120.0)
            self.assertIsNone(h.role_deadline("coherence_verdict", h.backends["xai:grok"]))
            self.assertIsNone(h.role_deadline("mine", h.backends["heimdall:qwen"]))
            slow = Slow("heimdall:deepseek", "heimdall/deepseek", "d", delay=0.6, family="deepseek")
            slow.gateway = "heimdall"
            h.backends["heimdall:deepseek"] = slow
            h.config["routing"]["verdict_deadline_s"] = {"heimdall": 0.1}
            r = h.call("coherence_verdict", "p")                 # deepseek is abandoned at 0.1 s: glm answers
            self.assertEqual(r.backend, "heimdall:glm")
            self.assertIn("abandoned at the deadline", r.tried[0][1])

    def test_the_real_config_bounds_today_as_ruled_and_heimdall_first_everywhere(self):
        """The 20:33 order bounds fidelity, coherence, step B, speaker and exclusion (120 s on Heimdall); step A's
        first screen and step C stay unbounded today (8 clips a call); under heimdall_first every verdict is bounded."""
        today, hf = P.Router(env_path="/nonexistent"), P.Router(env_path="/nonexistent", routing="heimdall_first")
        ds, xs = "heimdall:deepseek/deepseek-v4.1-flash", "xai:grok-4.20-0309-reasoning"
        for role in ("fidelity_verdict", "coherence_verdict", "viewer_takeaway", "speaker_verdict",
                     "exclusion_verdict"):
            self.assertEqual((today.role_deadline(role, today.backends[ds]), hf.role_deadline(role, hf.backends[ds])),
                             (120.0, 120.0), role)
            self.assertIsNone(today.role_deadline(role, today.backends[xs]))
        self.assertIsNone(today.role_deadline("context_verdict", today.backends[ds]))
        self.assertEqual(hf.role_deadline("context_verdict", hf.backends[ds]), 120.0)
        self.assertIsNone(hf.role_deadline("angle_write", hf.backends[ds]))   # the writer keeps ruling 5's 300 s

    def test_call_parsed_moves_on_past_an_answer_out_of_contract(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            h = self.router(d, "heimdall_first")
            h.backends["heimdall:deepseek"].answer = "not json"
            r, v = P.call_parsed(h, "coherence_verdict", "p", lambda t: {"d": 1, "g": 2}[t])
            self.assertEqual((r.backend, v), ("heimdall:glm", 2))
            for b in h.backends.values():
                b.answer = "bad"
            with self.assertRaises(P.ProviderError) as e:
                P.call_parsed(h, "coherence_verdict", "p", lambda t: {"d": 1}[t])
            self.assertIn("answers out of contract", str(e.exception))
            self.assertEqual({n: b.calls for n, b in h.backends.items()},          # the second run asks each model
                             {"heimdall:deepseek": 2, "heimdall:glm": 2, "heimdall:qwen": 1, "xai:grok": 1})  # once

    def test_the_writes_keep_their_gateway(self):
        """package.build: every write stays on the angle's GATEWAY, so a Heimdall write may still fail over
        deepseek -> qwen under heimdall_first, and Grok never writes there."""
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            h = self.router(d, "heimdall_first")
            writers = ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
            avoid = {P.gateway(h.backends[n]) for n in writers} - {P.gateway(h.backends["heimdall:deepseek"])}
            self.assertEqual(avoid, {"xai"})
            self.assertFalse({h.backends["heimdall:qwen"].vendor} & avoid)


class TestRuling86Shadow(TestRuling85Routing):
    """RULING 86 (21:18 Nov 13): the first pins under Heimdall-first are judged twice: Heimdall's families decide, and
    Grok is asked the same prompt in SHADOW (recorded to shadow_log, never deciding)."""

    def shadow_router(self, d, **kw):
        r = P.Router(self.cfg(d), env_path="/nonexistent", routing="heimdall_first", shadow={"*": "xai:grok"},
                     shadow_log=os.path.join(d, "SHADOW.jsonl"), **kw)
        fs = self.fakes()
        for b in fs:
            if b.vendor == "heimdall":
                b.gateway, b.vendor = b.vendor, f"heimdall/{b.family}"
        r.backends = {b.name: b for b in fs}
        return r

    def lines(self, d):
        p = os.path.join(d, "SHADOW.jsonl")
        return [json.loads(x) for x in open(p)] if os.path.exists(p) else []

    def test_a_heimdall_verdict_is_asked_of_grok_in_shadow_and_grok_never_decides(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self.shadow_router(d)
            rep = r.call("coherence_verdict", "the prompt", 500, 7)
            self.assertEqual((rep.backend, rep.text), ("heimdall:deepseek", "d"))      # Heimdall decides
            self.assertEqual(r.shadow_wait(5), 0)
            got = self.lines(d)
            self.assertEqual([(x["role"], x["prompt"], x["deciding"]["backend"], x["deciding"]["text"],
                               x["shadow"]["backend"], x["shadow"]["text"]) for x in got],
                             [("coherence_verdict", "the prompt", "heimdall:deepseek", "d", "xai:grok", "x")])
            self.assertEqual(r.backends["xai:grok"].calls, 1)
            r.call("mine", "p")                                   # not a verdict: no shadow
            r.backends["heimdall:deepseek"].fail = "down"
            r.backends["heimdall:glm"].fail = "down"
            r.backends["heimdall:qwen"].fail = "down"
            self.assertEqual(r.call("coherence_verdict", "q").backend, "xai:grok")   # Grok decided: nothing to shadow
            self.assertEqual(r.shadow_wait(5), 0)
            self.assertEqual(len(self.lines(d)), 1)

    def test_a_shadow_that_fails_is_on_record_and_stops_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self.shadow_router(d)
            r.backends["xai:grok"].fail = "xAI is down"
            self.assertEqual(r.call("coherence_verdict", "p").text, "d")
            self.assertEqual(r.shadow_wait(5), 0)
            (x,) = self.lines(d)
            self.assertIn("xAI is down", x["shadow"]["error"])

    def test_a_recorded_verdict_is_shadowed_too_and_the_shadow_back_end_must_exist(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            r = self.shadow_router(d, record_dir=os.path.join(d, "rec"))
            r.call("coherence_verdict", "p")
            r.shadow_wait(5)
            r.call("coherence_verdict", "p")                      # served from its recording
            r.shadow_wait(5)
            got = self.lines(d)
            self.assertEqual([x["deciding"]["cached"] for x in got], [False, True])
            self.assertEqual([x["shadow"]["cached"] for x in got], [False, True])   # the shadow's own recording
            self.assertEqual(r.backends["xai:grok"].calls, 1)
            with self.assertRaises(ValueError):
                P.Router(self.cfg(d), env_path="/nonexistent", shadow={"*": "xai:nope"})

if __name__ == "__main__":
    unittest.main()
