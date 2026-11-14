#!/usr/bin/env python3
"""pp-tests' REQUESTS R-29 and the exam's router (the orchestrator's 09:03 ET Nov 14 order: "R-29: FIX IT NOW";
"THE EXAM: APPROVED ... heimdall_first, bound $5.00 vendor-reported, on its OWN ledger"):
pipeline/moments_gate_adapter.py, the one adapter of pp-tests' moments exam, predated vo_fidelity v1.1. Its
vo_fidelity() passed no title and no current price levels from the case's universe, so the must-fail cases built on
them were never judged on them. Now: the title is judged like a line (as the packager passes it); the universe's news
gives the current levels the way package.current_levels reads sources; v1 cases are unchanged; one router
configuration serves the live recording and the offline replay."""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)
import moments_gate_adapter as A  # noqa: E402
import vo_fidelity as VF  # noqa: E402

PASS = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "fake",
        "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
        "verdict": {"ok": True, "violations": [], "classes": {}, "claims": []}}
SEGS = [{"label": "A", "channel": "Coin Bureau", "video_id": "va", "speaker": None,
         "sentences": [{"n": 0, "text": "Bitcoin closed just under 76K on the day."}]},
        {"label": "B", "channel": "Swan Bitcoin", "video_id": "vb", "speaker": None,
         "sentences": [{"n": 0, "text": "We were around $76,000 by the U.S. close."}]}]
LINES = [{"slot": "intro", "text": "Coin Bureau, then Swan Bitcoin.", "cites": ["A", "B"], "after": None},
         {"slot": "signoff", "text": "That's Pulse Check.", "cites": [], "after": "B"}]
# the real stale_price_title__01's title and universe (pp-tests' corpus, v1.1): its $73,500 news is 38 h old
UNIVERSE = {"built_at": "2026-11-12T05:06:13.234375+00:00", "date": "2026-11-12", "use": "staleness only",
            "news": [{"headline": "Bitcoin Price Trades Down Near $73,500 After Hot CPI Print Lifts Fed Hike Bets",
                      "published_at": "2026-11-10T14:28:12.195473+00:00",
                      "summary": "Bitcoin price slipped to $73,500 Tuesday morning."},
                     {"headline": "Stablecoin Drain, ETF Outflows Leave Bitcoin 'Running on Empty'",
                      "published_at": "2026-11-11T21:46:12.195473+00:00",
                      "summary": "Stablecoin supply fell $14.2 billion in 30 days."}]}


def v11(**over):
    return dict({"schema": "pp.vo_case/1.1", "id": "case-x", "segments": SEGS, "lines": LINES,
                 "manifest": {"show": "Pulse Check", "date": "2026-11-12", "channels": ["Coin Bureau", "Swan Bitcoin"]},
                 "title": "Bitcoin ran from 16K to 126K", "universe": UNIVERSE}, **over)


class Capture:
    """VF.check as the adapter calls it: the arguments kept, a measured pass returned."""

    def __init__(self):
        self.calls = []

    def __call__(self, router, segments, lines, writer_vendor=None, manifest=None, current_levels=None, **k):
        self.calls.append({"segments": segments, "lines": lines, "manifest": manifest, "levels": current_levels})
        return PASS


class TestR29(unittest.TestCase):
    def run_case(self, case):
        cap = Capture()
        with mock.patch.object(A.VF, "check", cap), mock.patch.object(A, "router", lambda: object()):
            out = A.vo_fidelity(case)
        return out, cap.calls

    def test_the_title_is_judged_like_a_line_and_the_universe_gives_the_levels(self):
        out, calls = self.run_case(v11())
        self.assertEqual(out["verdict"], "pass")
        lines = calls[0]["lines"]
        self.assertEqual(lines[-1], {"slot": "title", "text": "Bitcoin ran from 16K to 126K", "cites": []})
        self.assertEqual([x["slot"] for x in lines], ["intro_0", "signoff_1", "title"])
        self.assertEqual(calls[0]["levels"], [])           # measured: no level inside 24 h (not None: not measured)

    def test_a_v1_case_is_unchanged(self):
        case = {k: v for k, v in v11().items() if k not in ("title", "universe")}
        _, calls = self.run_case(case)
        self.assertEqual([x["slot"] for x in calls[0]["lines"]], ["intro_0", "signoff_1"])
        self.assertIsNone(calls[0]["levels"])               # as before: price_now not measured without a universe

    def test_explicit_current_levels_still_win(self):
        _, calls = self.run_case(v11(current_levels=[90000.0]))
        self.assertEqual(calls[0]["levels"], [90000.0])

    def test_the_universe_reads_like_package_current_levels(self):
        fresh = {"headline": "Bitcoin is trading at $73,500 this morning.", "summary": "",
                 "published_at": "2026-11-12T01:00:00+00:00"}
        u = dict(UNIVERSE, news=UNIVERSE["news"] + [fresh])
        self.assertEqual(A.universe_levels(u), [73500.0])   # inside 24 h of built_at; the 38 h old one is not
        not_btc = dict(fresh, headline="Ethereum is trading at $73,500 this morning.")   # a level, but not Bitcoin's
        self.assertEqual(VF.current_level_values(not_btc["headline"]), [73500.0])
        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[not_btc])), [])
        unreadable = dict(fresh, published_at="yesterday")
        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[unreadable, fresh])), [73500.0])   # skipped
        zoneless = dict(fresh, published_at="2026-11-12T01:00:00")
        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[zoneless])), [])   # no zone, no measurement
        late = dict(fresh, published_at="2026-11-12T09:00:00+00:00")   # after built_at: inside (as for sources)
        self.assertEqual(A.universe_levels(dict(UNIVERSE, news=[late])), [73500.0])

    def test_an_unreadable_case_is_the_harness_error_never_a_guess(self):
        for bad in (v11(title=""), v11(title=5), v11(universe=dict(UNIVERSE, built_at="2026-11-12")),
                    v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")), v11(universe={"news": []}),
                    v11(universe=dict(UNIVERSE, news="none"))):
            with self.assertRaises(A.GateNotMeasured, msg=str(bad.get("title"))):
                self.run_case(bad)
        with self.assertRaisesRegex(A.GateNotMeasured, "not a zoned time"):           # said plainly, never a guess
            self.run_case(v11(universe=dict(UNIVERSE, built_at="2026-11-12T05:06:13")))

    def test_the_real_stale_title_case_now_fails_on_its_title_deterministically(self):
        """No model: the deterministic layer on the lines the adapter now passes (the 16K / 126K title against the
        clips' 76K, with the universe's measured [] levels)."""
        _, calls = self.run_case(v11())
        c = calls[0]
        det = VF.check_deterministic(c["segments"], c["lines"], c["manifest"], c["levels"])
        rules = {v["rule"] for v in det["violations"] if v["slot"] == "title"}
        self.assertTrue({"NUMBER", "PRICE_NOW"} <= rules, rules)
        old = [x for x in c["lines"] if x["slot"] != "title"]   # the old adapter's lines: the title never judged
        self.assertFalse([v for v in VF.check_deterministic(c["segments"], old, c["manifest"], None)["violations"]
                          if v["slot"] == "title"])


class TestExamRouter(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = [mock.patch.object(A, "SPEND", os.path.join(self.d, "SPEND.json")),
                  mock.patch.object(A, "RECORD", os.path.join(self.d, "replies"))]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        shutil.rmtree(self.d, ignore_errors=True)

    def test_heimdall_first_on_vendor_reported_dollars_bounded_at_5(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for k in ("PP_GATES_ROUTING", "PP_GATES_LIMIT_USD", "PP_GATES_LIMIT_BASIS", "PP_GATES_REPLAY"):
                os.environ.pop(k, None)
            r = A.make_router()
        self.assertEqual((r.routing, r.limit_basis, r.limit_usd), ("heimdall_first", "reported", 5.0))
        self.assertEqual(r.chain("context_verdict", "step_c")[0], "xai:grok-4.20-0309-reasoning")   # routed lists
        with mock.patch.dict(os.environ, {"PP_GATES_ROUTING": "today", "PP_GATES_LIMIT_USD": "4.00",
                                          "PP_GATES_REPLAY": "1"}):
            r = A.make_router()
        self.assertEqual((r.routing, r.limit_usd, r.replay), ("today", 4.0, True))

    def test_the_recorder_and_the_harness_share_one_router(self):
        import run_exam_record as RX
        made = []

        def fake(chains=None):
            made.append(chains)
            return mock.Mock(notices=[])

        def no_network(*a, **k):
            raise AssertionError("no network in this test")
        corpus, out = os.path.join(self.d, "corpus"), os.path.join(self.d, "out")
        os.makedirs(corpus)
        with mock.patch.object(A, "make_router", fake), mock.patch("urllib.request.urlopen", no_network):
            self.assertEqual(RX.main(["--corpus", corpus, "--out", out]), 0)
            self.assertEqual(RX.main(["--corpus", corpus, "--out", out, "--chain", "context_verdict=xai:x"]), 0)
        self.assertEqual(made, [None, {"context_verdict": ["xai:x"]}])


if __name__ == "__main__":
    unittest.main()
