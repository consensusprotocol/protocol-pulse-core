#!/usr/bin/env python3
"""RULING 102 (orchestrator 13:02 ET Nov 14): STEP_A_UNAVAILABLE MUST NEVER END A CLIP. Step A's second family after
Grok: Heimdall deepseek -> Heimdall glm -> Gemini -> the local gemma3:27b (ruling 87's last resort, recorded as such on
the pin and on STATE line 1). The first leg that ANSWERS gives the second verdict; an unavailable leg moves on at once,
is never a refusal and is never cached; only when no leg answers is the clip HELD for this build, retried next build.

Offline: a real providers.Router over fake legs, the real context_integrity.step_a, package.prescreen and
package.second_screen; a temporary step-A cache."""
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/providers", "tests/eligibility"):
    sys.path.insert(0, os.path.join(REPO, _p))
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import proof_ledger as PLG  # noqa: E402
import spotlight as SPOT  # noqa: E402
import test_angles as TA  # noqa: E402
import test_medley as TM  # noqa: E402
import test_spotlight as TS  # noqa: E402
from test_gates import a_item  # noqa: E402

X, DS, G = "xai:grok-4.20-0309-reasoning", "heimdall:deepseek/deepseek-v4.1-flash", "heimdall:z-ai/glm-5.3-flash"
GEM, LJ = "google:gemini-2.5-pro", "local_judge:gemma3:27b"
LEGS = (X, DS, G, GEM, LJ)
VENDOR = {X: ("xai", "grok", None), DS: ("heimdall/deepseek", "deepseek", "heimdall"),
          G: ("heimdall/glm", "glm", "heimdall"), GEM: ("google", "gemini", None), LJ: ("local_judge", "gemma", None)}


def answer(prompt):
    """A step-A reply in contract for exactly the excerpts the prompt carries (each passes: test_gates.a_item)."""
    return json.dumps({"excerpts": [a_item(lb) for lb in re.findall(r'<excerpt label="([^"]+)"', prompt)]})


class Leg(P.Backend):
    """One leg of the chain: answers in contract, or fails with `fail` (an exception), or answers out of contract."""

    def __init__(self, name, fail=None, out_of_contract=False):
        vendor, family, gw = VENDOR[name]
        super().__init__(name, {"model": name.split(":", 1)[1], "family": family, "price_usd_per_1m": [1, 1]},
                         "/nonexistent")
        self.vendor, self.fail, self.ooc, self.calls = vendor, fail, out_of_contract, 0
        if gw:
            self.gateway = gw

    def complete(self, prompt, max_tokens, seed, system=None):
        self.calls += 1
        if self.fail is not None:
            raise self.fail
        return ("this is not JSON" if self.ooc else answer(prompt)), {"in": 10, "out": 10}, 0.01


class Judge(P.LocalJudgeBackend):
    """The local judge (a LocalJudgeBackend: the Router's announcement), answering at once."""

    def __init__(self):
        super().__init__(LJ, {"model": "gemma3:27b", "family": "gemma"}, "/nonexistent")
        self.calls = 0

    def complete(self, prompt, max_tokens, seed, system=None):
        self.calls += 1
        return answer(prompt), {"in": 0, "out": 0}, 0.01


def router(d, legs, **kw):
    cfg = os.path.join(d, "cfg.json")
    with open(cfg, "w") as f:
        json.dump({"schema": "pp.providers/1",
                   "backends": {b.name: {"vendor": "openai", "model": b.model} for b in legs},
                   "roles": {"context_verdict": {"chain": [b.name for b in legs]}},
                   "routing": {"mode": "heimdall_first", "verdict_roles": ["context_verdict"],
                               "verdict_deadline_s": {"heimdall": 120},
                               "heimdall_first": {"context_verdict:step_a_second": list(LEGS)}}}, f)
    r = P.Router(cfg, env_path="/nonexistent", routing="heimdall_first", **kw)
    r.backends = {b.name: b for b in legs}
    return r


def pool(n=2):
    return TM.TestRuling58StepAEveryCandidate.pool(None, n)


class TestTheSecondFamily(unittest.TestCase):
    """package.second_screen on the moments whose FIRST verdict is Grok's (the two hook-4 candidates' case)."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.cache = os.path.join(self.d.name, "STEP_A_CACHE.json")
        self.ms, self.srcs = pool(2)
        self.cleared = {m["moment_id"]: m for m in self.ms}

    def screen(self, legs, first=X):
        r = router(self.d.name, legs)
        a_by = {mid: dict(a_item(mid), backend=first) for mid in self.cleared}
        return PK.second_screen(r, self.cleared, a_by, self.srcs, TM.ctx(), log=lambda *_: None, cache=self.cache)

    def cached(self):
        if not os.path.exists(self.cache):
            return {}
        with open(self.cache) as f:
            return {k: sorted(v) for k, v in json.load(f).items()}

    def test_every_faster_leg_unavailable_the_local_judge_answers_and_is_the_last_resort(self):
        legs = [Leg(X), Leg(DS, P.Unavailable("HTTP 503")), Leg(G, P.Unavailable("HTTP 503")),
                Leg(GEM, P.Unavailable("HTTP 429")), Leg(LJ)]
        two, fail = self.screen(legs)
        self.assertEqual(fail, {})
        self.assertEqual({mid: [a["backend"] for a in v] for mid, v in two.items()},
                         {mid: [X, LJ] for mid in self.cleared})                 # off Grok: the last leg answered
        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])               # in order, each once, never Grok
        self.assertEqual({mid: PK.last_resort_of(v) for mid, v in two.items()}, {mid: [LJ] for mid in self.cleared})

    def test_the_order_is_deepseek_glm_gemini_the_judge(self):
        for down, want in (((), DS), ((DS,), G), ((DS, G), GEM), ((DS, G, GEM), LJ)):
            legs = [Leg(n, P.Unavailable("down") if n in down else None) for n in LEGS]
            two, fail = self.screen(legs)
            self.assertEqual({v[1]["backend"] for v in two.values()}, {want}, down)
            os.path.exists(self.cache) and os.remove(self.cache)
        legs = [Leg(n) for n in LEGS]                         # a first verdict from glm: Grok confirms, as before
        two, _ = self.screen(legs, first=G)
        self.assertEqual({v[1]["backend"] for v in two.values()}, {X})

    def test_a_leg_out_of_contract_or_past_its_deadline_moves_on_at_once_and_is_never_a_refusal(self):
        legs = [Leg(X), Leg(DS, out_of_contract=True), Leg(G, P.DeadlineExceeded("no answer within 60 s")),
                Leg(GEM, P.RequestRejected("refused this request")), Leg(LJ)]
        two, fail = self.screen(legs)
        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {LJ}))
        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])

    def test_no_leg_answers_the_clip_is_held_never_cached_and_retried_next_build(self):
        legs = [Leg(X)] + [Leg(n, P.Unavailable("down")) for n in (DS, G, GEM, LJ)]
        two, fail = self.screen(legs)
        self.assertEqual(two, {})
        self.assertEqual(sorted(fail), sorted(self.cleared))
        self.assertTrue(all(PK.is_held(f) for f in fail.values()), fail)          # HELD, not a refusal
        self.assertTrue(all("retried next build" in f[0] for f in fail.values()))
        self.assertEqual(self.cached(), {})                                        # nothing remembered
        legs = [Leg(X), Leg(DS, P.Unavailable("down")), Leg(G), Leg(GEM), Leg(LJ)]   # the next build: glm is back
        two, fail = self.screen(legs)
        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {G}))   # retried and answered
        self.assertEqual(set(sum(self.cached().values(), [])), {G})                # only an answer is cached

    def test_every_leg_answering_out_of_contract_is_held_through_the_real_step_a(self):
        """glm, audit 20261114_1349 C2 (its P2-1): no mock of the verdict rules. Every leg ANSWERS, out of contract;
        the real step_a skips each (failover), the chain is spent, and the moments are HELD, never cached, retried."""
        legs = [Leg(X)] + [Leg(n, out_of_contract=True) for n in (DS, G, GEM, LJ)]
        two, fail = self.screen(legs)
        self.assertEqual(two, {})
        self.assertTrue(all(PK.is_held(f) for f in fail.values()), fail)
        self.assertEqual([b.calls for b in legs], [0, 1, 1, 1, 1])       # each answered once, none twice
        self.assertEqual(self.cached(), {})
        legs = [Leg(X), Leg(DS, out_of_contract=True), Leg(G)] + [Leg(n) for n in (GEM, LJ)]   # next build: glm in
        two, fail = self.screen(legs)
        self.assertEqual((fail, {v[1]["backend"] for v in two.values()}), ({}, {G}))

    def test_a_verdict_that_fails_the_clip_is_a_refusal_not_held(self):
        legs = [Leg(n) for n in LEGS]
        with mock.patch.object(PK.CI, "a_failures", lambda a: ["REFERENT_OUTSIDE"]):
            two, fail = self.screen(legs)
        self.assertEqual(two, {})
        self.assertFalse(any(PK.is_held(f) for f in fail.values()))
        self.assertEqual(set(map(tuple, fail.values())), {("REFERENT_OUTSIDE",)})


class TestInTheBuild(unittest.TestCase):
    """package.build (the rig: every model stubbed): HELD moments are recorded per screen, and a pin whose clips were
    judged by the local judge carries the record (ruling 87's last resort) in its sealed context_a row."""
    MS = TM.TestBuildLoop.MS

    def test_a_moment_held_at_the_first_screen_is_recorded_as_held(self):
        rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None], unavailable={("xai", "z")})
        out = rig.run()
        self.assertEqual(out["prescreen"]["held_102"], {"first": ["z"], "second": []})
        self.assertTrue(PK.is_held(out["prescreen"]["failed"]["z"]))
        self.assertIsNotNone(out["package"])                      # the build goes on without it

    def test_a_pin_judged_by_the_local_judge_says_so(self):
        rig = TM.Rig(self.MS, ["h", "x", "y"], [(True, [], None, TM.Rig.LINE)], [None])
        rig.router.backends[LJ] = type("B", (), {"vendor": "local_judge", "family": "gemma"})()
        pre = rig.prescreen

        def judged(router_, ms, *a, kind=None, **k):          # the second family: only the local judge answers
            if k.get("plan_only"):                              # ruling 101's plan: nothing asked
                return pre(router_, ms, *a, kind=kind, **k)
            got, fails, v, f = pre(router_, ms, *a, kind=kind, **k)
            if kind == "step_a_second":
                got = {mid: dict(a, backend=LJ) for mid, a in got.items()}
            return got, fails, v, f
        rig.prescreen = judged
        out = rig.run()
        segs = out["package"]["segments"]
        self.assertEqual(out["prescreen"]["last_resort_87"], {mid: [LJ] for mid in sorted(out["prescreen"]
                                                                                         ["last_resort_87"])})
        self.assertTrue({sg["moment_id"] for sg in segs} <= set(out["prescreen"]["last_resort_87"]))
        row = out["package"]["gates"]["context_a"]
        self.assertEqual(row["last_resort"]["verdicts"], {sg["label"]: LJ for sg in segs})
        self.assertEqual(row["status"], "PASS")

    def test_a_re_screen_off_the_writers_with_no_verdict_and_no_reason_is_held(self):
        """The writers' re-screen (order 06:22 item 44): a clip it returns nothing at all for is HELD (its default
        reason), out of this build only, never a refusal."""
        rig = TM.Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, TM.Rig.LINE), (True, [], None, TM.Rig.LINE)],
                     [None, None], angle_from=("xai:grok", "xai", "grok"))
        pre = rig.prescreen

        def silent(router_, ms, sources_, ctx_, writer_vendor, *a, **k):
            res = pre(router_, ms, sources_, ctx_, writer_vendor, *a, **k)
            if k.get("plan_only") or not {"xai", "heimdall"} <= P._as_set(writer_vendor):
                return res
            got, fails, v, f = res                              # the writers' re-screen: y gets nothing at all
            return {m: x for m, x in got.items() if m != "y"}, {m: x for m, x in fails.items() if m != "y"}, v, f
        rig.prescreen = silent
        out = rig.run()
        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
        self.assertTrue(PK.is_held(out["prescreen"]["rescreen_failed"]["y"]))
        self.assertIn("no verdict off the writers", out["prescreen"]["rescreen_failed"]["y"][0])

    def test_the_default_no_second_verdict_is_held(self):
        ms, srcs = pool(1)
        mid = ms[0]["moment_id"]
        r = type("R", (), {"backends": {X: Leg(X), DS: Leg(DS)}, "routing": "heimdall_first"})()
        with mock.patch.object(PK, "prescreen", lambda *a, **k: ({}, {}, set(), set())):   # no verdict, no reason
            two, fail = PK.second_screen(r, {mid: ms[0]}, {mid: dict(a_item(mid), backend=X)}, srcs, TM.ctx(),
                                         log=lambda *_: None)
        self.assertEqual(two, {})
        self.assertTrue(PK.is_held(fail[mid]), fail)


class TestHeldWhy(unittest.TestCase):
    def test_no_verdict_is_held_except_a_context_law_l_s_will_never_shorten(self):
        for e in (P.ProviderError("context_verdict: every back-end unavailable"), P.SpendLimit("over $20"),
                  RuntimeError("anything")):
            why = PK.held_why(e)
            self.assertTrue(PK.is_held([why]), e)
            self.assertIn(type(e).__name__, why)
        why = PK.held_why(ValueError("CONTEXT_TOO_LONG: m1's window is 9000 characters (> 6000); never truncated"))
        self.assertTrue(why.startswith("STEP_A_REFUSED: CONTEXT_TOO_LONG"))
        self.assertFalse(PK.is_held([why]))
        self.assertFalse(PK.is_held([]))
        self.assertFalse(PK.is_held([PK.held_why(RuntimeError("x")), "REFERENT_OUTSIDE"]))   # one refusal: refused


class TestOnThePinAndOnState(unittest.TestCase):
    def test_the_medley_pin_records_the_local_judge_and_a_pin_without_it_is_unchanged(self):
        base = TA.TestInventory.base(None)
        plain = PK.inventory(**base)
        self.assertNotIn("last_resort", plain["context_a"])                          # every other pin as before
        g = PK.inventory(**base, last_resort=PK.last_resort_note({"clip_01": LJ}))
        self.assertEqual(g["context_a"]["last_resort"]["verdicts"], {"clip_01": LJ})
        rule = g["context_a"]["last_resort"]["rule"]
        self.assertTrue(rule.startswith("ruling 87's last resort") and "under ruling 102" in rule, rule)
        self.assertEqual({k: v for k, v in g["context_a"].items() if k != "last_resort"}, plain["context_a"])

    def test_the_spotlight_pin_records_the_local_judge(self):
        m = TS.moment()

        def row(a_two):
            return SPOT.inventory(*TS.package()[0:1], m, TS.FID_OK, [], True, [], TS.CX_OK, a_two[0], a_two,
                                  {"verdict": "keep", "measured": True, "replayed": False},
                                  {"ok": True, "edges": {"cuttable": True}}, TS.pre_of(m), m["spotlight_source"],
                                  {"now": TS.NOW, "day": "d", "never_delivered": True,
                                   "one_per_channel_day": True})["step_a_two_families"]
        self.assertNotIn("last_resort", row(TS.two()))
        judged = [TS.two()[0], dict(TS.two()[1], backend=LJ)]
        r = row(judged)
        self.assertEqual((r["status"], r["last_resort"]["verdicts"]), ("PASS", {m["moment_id"]: LJ}))

    def test_state_line_1_is_told_once_in_the_ruling_s_words_and_plan_b_keeps_its_own(self):
        for plan_b, words in ((False, "RULING 102: NO FASTER LEG OF STEP A'S SECOND FAMILY ANSWERED"),
                              (True, "PLAN B WITH ONE OUTSIDE FAMILY")):
            with tempfile.TemporaryDirectory() as d:
                state = os.path.join(d, "STATE.md")
                with open(state, "w") as f:
                    f.write("line one\nline two\n")
                judge = Judge()
                r = router(d, [Leg(X), Leg(DS, P.Unavailable("down")), Leg(G, P.Unavailable("down")),
                               Leg(GEM, P.Unavailable("down")), judge], state_md=state)
                r.mode = lambda: "plan_b" if plan_b else "heimdall_first"
                ms, srcs = pool(2)
                a_by = {m["moment_id"]: dict(a_item(m["moment_id"]), backend=X) for m in ms}
                for _ in range(2):                                           # two screens: one announcement
                    PK.second_screen(r, {m["moment_id"]: m for m in ms}, a_by, srcs, TM.ctx(), log=lambda *_: None,
                                     cache=None)
                with open(state) as f:
                    first = f.read().split("\n")[0]
                self.assertEqual(first.count(words), 1, first)
                self.assertTrue(first.endswith("| line one"), first)
                self.assertEqual(judge.calls, 2)

    def test_the_build_line(self):
        self.assertEqual(PLG.ruling_102_line({"held_102": {"first": [], "second": []}, "last_resort_87": {}}, {}), "")
        line = PLG.ruling_102_line({"held_102": {"first": ["a"], "second": ["b"]}, "last_resort_87": {"c": [LJ]}},
                                   {"held_102": ["d"], "last_resort_87": {"e": [LJ]}})
        self.assertIn("HELD for this build, retried next build", line)
        self.assertIn("1 at step A's first screen, 1 at the medley's second screen ['b'], 1 at the spotlight's ['d']",
                      line)
        self.assertIn("THE LOCAL JUDGE (RULING 87'S LAST RESORT) GAVE 2 STEP-A VERDICT(S): ['c', 'e']", line)

    def test_no_build_starts_at_the_stop_and_one_starts_below(self):
        """The orchestrator 13:02 Nov 14: at the stop no build starts, and STATE line 1 says so in capitals. RULING 118
        (05:40 Nov 16): the outside vendors' HARD cap is $1.00 a day, Heimdall uncapped; each paid call reserves its
        upper bound, so the cap itself is never passed (ruling 108's headroom between the stop and the limit is gone)."""
        self.assertEqual((PLG.PL.LY_STOP_USD, PLG.PL.LY_LIMIT_USD), (1.00, 1.00))
        self.assertEqual(PLG.PL.LY_LIMIT_BASIS, "reported")               # vendor-reported (audit 2114 C1, glm)
        self.assertEqual(PLG.PL.UNCAPPED, ("heimdall",))
        self.assertIsNone(PLG.start_refused(0.99))
        why = PLG.start_refused(1.0)
        self.assertIn("at or over the $1.00 stop: no build starts", why)
        self.assertIn("SAY IT ON STATE LINE 1 IN CAPITALS", why)

    def test_ruling_118_each_day_keeps_its_own_ledger_from_21_10_et(self):
        """RULING 118: $1.00 a day; a day runs 21:10 ET to 21:10 ET, and the one that starts 21:10 ET Nov 15 is batch 4's
        (the ruling counts batch 4's $0.52 in it), so it keeps SPEND_B4.json; a build charges the day it started in."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        et, dl = ZoneInfo("America/New_York"), PLG.PL.day_ledger
        name = lambda *a: os.path.basename(dl(datetime(*a, tzinfo=et)))
        self.assertEqual([name(2026, 11, 15, 21, 10), name(2026, 11, 16, 5, 40), name(2026, 11, 16, 21, 9)],
                         ["SPEND_B4.json"] * 3)
        self.assertEqual([name(2026, 11, 16, 21, 10), name(2026, 11, 17, 3, 0), name(2026, 11, 17, 21, 10)],
                         ["SPEND_D20261116.json", "SPEND_D20261116.json", "SPEND_D20261117.json"])
        self.assertEqual(PLG.PL.SPEND, dl())                               # the build's ledger is today's
        self.assertNotIn(os.path.basename(PLG.PL.SPEND), ("SPEND_LY.json", "SPEND_B3.json"))   # never a closed one


class TestTheConfirmAheadIsGrokOnly(unittest.TestCase):
    """RULING 101 beside 102: Grok's confirm-ahead never asks Gemini or the local judge (the second family's
    fallbacks are the second screen's, asked only when it needs them)."""

    def test_through_the_real_chain_grok_answers_ahead_and_no_fallback_is_ever_asked(self):
        """qwen, audit 20261114_1349 C1: the confirm-ahead must GET Grok's verdict, not only avoid the rest. A real
        Router over the five legs, the real prescreen and step_a: every new moment gets Grok's verdict; with Grok down,
        none, and no other leg (deepseek, glm, Gemini, the judge) is ever asked."""
        ms, srcs = pool(3)
        for grok_down in (False, True):
            with tempfile.TemporaryDirectory() as d:
                legs = [Leg(X, P.Unavailable("down") if grok_down else None)] + [Leg(n) for n in LEGS[1:]]
                r = router(d, legs)
                res = PK.confirm_ahead(r, ms, srcs, TM.ctx(), {"heimdall/deepseek"}, {"deepseek"}, log=lambda *_: None,
                                       cache=os.path.join(d, "c.json"))
                self.assertEqual(res["asked"], 3)
                self.assertEqual(res.get("by", {}), {} if grok_down else {m["moment_id"]: X for m in ms})
                self.assertEqual([b.calls for b in legs[1:]], [0, 0, 0, 0])      # never a fallback ahead
                self.assertEqual(legs[0].calls, 1)                               # one batch of 3

    def test_every_vendor_but_grok_s_is_avoided_ahead(self):
        legs = {n: Leg(n) for n in LEGS}
        got = {}

        def fake(router_, new, sources, ctx_, wv, wf, n=None, kind=None, cache=None, **k):
            got.update(wv=set(wv), wf=set(wf), kind=kind)
            return {}, {}, set(), set()
        r = type("R", (), {"backends": legs})()
        with mock.patch.object(PK, "prescreen", fake):
            PK.confirm_ahead(r, [{"moment_id": "a"}], {}, None, {"heimdall/deepseek"}, {"deepseek"})
        self.assertEqual(got["wv"], {"heimdall/deepseek", "heimdall/glm", "google", "local_judge"})
        self.assertEqual(got["wf"], {"deepseek", "glm", "gemini", "gemma"})
        self.assertEqual(got["kind"], "step_a_second")


if __name__ == "__main__":
    unittest.main()
