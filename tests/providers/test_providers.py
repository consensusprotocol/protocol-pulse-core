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


class TestDeadline(unittest.TestCase):
    """Orchestrator 22:40 ruling 5: one writer call never waits more than its deadline; it fails over to the next
    back-end, the failover is recorded, and the abandoned call's upper bound is booked as spent."""

    def test_a_call_that_passes_its_deadline_fails_over_and_is_recorded(self):
        import tempfile
        import time as _t
        with tempfile.TemporaryDirectory() as d:
            slow = Slow("heimdall:deepseek", "heimdall", '{"ok": 1}', delay=2.0, family="deepseek")
            next_ = Fake("heimdall:qwen", "heimdall", answer='{"ok": 2}', family="qwen")
            r = router(d, [slow, next_], {"angle_write": ["heimdall:deepseek", "heimdall:qwen"]},
                       spend_path=os.path.join(d, "SPEND.json"), limit_usd=50.0)
            t0 = _t.time()
            rep = r.call("angle_write", "p", 100, 7, deadline_s=0.3)
            self.assertLess(_t.time() - t0, 1.5)                       # never waited for the slow one
            self.assertEqual((rep.backend, rep.text), ("heimdall:qwen", '{"ok": 2}'))
            self.assertIn("no answer within 0 s", rep.tried[0][1])   # the failover is recorded on the reply
            self.assertIn("abandoned at the deadline", rep.tried[0][1])
            led = json.load(open(os.path.join(d, "SPEND.json")))
            self.assertEqual(led["by_backend"]["heimdall:deepseek"]["calls"], 1)       # booked, at its upper bound
            self.assertAlmostEqual(led["by_backend"]["heimdall:deepseek"]["usd_estimate"],
                                   slow.upper_usd("p", 100), places=6)
            self.assertEqual(led["reserved"], {})                      # no reservation left behind

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


if __name__ == "__main__":
    unittest.main()
