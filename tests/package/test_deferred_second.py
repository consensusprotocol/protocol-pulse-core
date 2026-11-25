#!/usr/bin/env python3
"""A-F (the owner's approval, 15:55 ET Nov 25: "the deferred second-vendor verification for all three selected lineup
segments"), offline: every model stubbed (the rigs of test_medley, test_ruling_163, test_lean_reserve,
test_lean_ops), every socket blocked for the whole module.
  A  on the lean path the second vendor's step A is NOT asked before the line-up; a line-up that passed its join table
     and its clips-alone verdict asks it ONCE for its segments; a FAIL, no answer or a refusal for money drops it;
     THE SEAL refuses a pending, failing, unanswered, same-vendor or local-judge segment (must-fail);
  B  the step-A cache: a verdict is reused only for the same words, cut, context and prompt version, from a model of
     the chain (each change misses: must-fail); a FAIL is cached as a FAIL, no answer is not cached; a later line-up
     asks only for the segments it lacks;
  C  a refusal for money is budget_refused everywhere: build 172's two refused Gemini calls replayed give 15
     budget_refused and 0 provider_unavailable;
  D  the completion reserve still refuses a speculative call that would eat into it; the deferred call and the
     alternative line-ups are search, never completion;
  E  the ceiling: $1.50 by default; the launcher's --ceiling-usd (e.g. 3.00) is honoured by the builder, the lock
     service and the renderer, recorded in the launch record and the outcome line; above $5.00 refused;
  F  at most DEFERRED_LINEUPS_MAX line-ups have their deferred verdicts asked; a sealed medley stops the search."""
import argparse
import copy
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility", "tests/moments", "tests/package/lean"):
    sys.path.insert(0, os.path.join(REPO, _p))
import outcomes as OC  # noqa: E402
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import spend_ceiling as SC  # noqa: E402
import test_lean_reserve as TLR  # noqa: E402
import test_medley as TM  # noqa: E402
import test_ruling_163 as T163  # noqa: E402

B172 = os.path.join(HERE, "proof", "ledger_20261125_180553")     # build 172's record, as it ran (a42470d28)
LEAN_RELEASE = "/home/ultron/worktrees/pp-lean-release/pipeline"
MONEY = ("SpendLimit (the completion reserve, lean (5)): spend (reported) 0.55 USD + this call's upper bound 0.11 + "
         "the $0.87 held back to finish one package > the limit")
_SAVED = {}


def _blocked(*a, **k):
    raise OSError("the network is blocked by this test module")


def setUpModule():
    for obj, name in ((socket.socket, "connect"), (socket.socket, "connect_ex"), (socket, "create_connection"),
                      (socket, "getaddrinfo"), (socket, "gethostbyname")):
        _SAVED[(obj, name)] = getattr(obj, name)
        setattr(obj, name, _blocked)


def tearDownModule():
    for (obj, name), v in _SAVED.items():
        setattr(obj, name, v)


def lean_rig(n=2, money=(), **kw):
    """test_ruling_163's rig (h, x, y, z on four channels) on the LEAN path, with the order of every step-A screen and
    clips-alone verdict, and the router's phase at each, recorded; `money`: (back-end, moment) pairs whose screen the
    router refuses for money (a CompletionReserve, as providers raises it)."""
    r = T163.rig(n=n, **kw)
    r.build_kw = {"lean": True}
    oe = r.out_edges                                     # the rig's OUT edge: every clip ends a thought (lean (2)'s
    r.out_edges = lambda *a, recover=False, **k: oe(*a, **k)   # recovery is test_lean_out_edge's)
    seq = []
    med, pre, wr = r.medley, r.prescreen, r.write

    def medley(router, segs, ctx_, wv, seed=7, writer_family=None):
        seq.append(("medley", "medley", [m["moment_id"] for m in segs], getattr(r.router, "completing", None)))
        return med(router, segs, ctx_, wv, seed, writer_family)

    def prescreen(router, ms, *a, **k):
        if k.get("plan_only"):                          # ruling 101's plan: no screen is asked
            return pre(router, ms, *a, **k)
        got, fails, v, f = pre(router, ms, *a, **k)
        name = r.screens[-1][0] if r.screens else None
        for mid in list(got):
            if (name, mid) in money:
                got.pop(mid)
                fails[mid] = [PK.held_why(P.CompletionReserve(MONEY))]
        seq.append(("step_a", name, [m["moment_id"] for m in ms], getattr(r.router, "completing", None)))
        return got, fails, v, f

    def write(*a, **k):
        seq.append(("write", None, None, getattr(r.router, "completing", None)))
        return wr(*a, **k)
    r.medley, r.prescreen, r.write = medley, prescreen, write
    return r, seq


def seconds_of(seq):
    return [s for s in seq if s[0] == "step_a" and s[1] == "heimdall:deepseek"]   # the second vendor (off xai)


def first_lineup():
    """The rig's first line-up on the lean path, every verdict passing: its moment ids, hook first."""
    r, seq = lean_rig()
    out = r.run()
    return [sg["moment_id"] for sg in out["package"]["segments"]]


class TheDeferredSecondVerdict(unittest.TestCase):
    def test_the_second_vendor_is_asked_once_after_the_clips_alone_verdict_on_its_segments(self):
        """MUST-PASS: no second-vendor screen before the first clips-alone verdict; then ONE, on the line-up's own
        segments, while the router searches (D); the package seals; every other moment stays PENDING."""
        r, seq = lean_rig()
        out = r.run()
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        segs = [sg["moment_id"] for sg in pk["segments"]]
        second = seconds_of(seq)
        self.assertEqual(len(second), 1, seq)
        first_medley = next(i for i, s in enumerate(seq) if s[0] == "medley")
        self.assertGreater(seq.index(second[0]), first_medley)
        self.assertEqual(sorted(second[0][2]), sorted(segs))
        self.assertIs(second[0][3], False)
        sv = out["prescreen"]["second_vendor"]
        self.assertTrue(all(sv[m].startswith("PASS") for m in segs), sv)
        self.assertTrue(all(v == PK.PENDING for m, v in sv.items() if m not in segs), sv)
        self.assertEqual(out["prescreen"]["deferred_second"]["lineups"], 1)

    def test_pending_is_never_counted_as_screened_by_the_second_family(self):
        """The yield's "step A, second family" counts only the moments its verdict was asked for."""
        r, _ = lean_rig()
        out = r.run()
        sv = out["prescreen"]["second_vendor"]
        row = next(x for x in OC.yield_of(out, {"moments": []}) if x["stage"] == "step A, second family")
        self.assertEqual(row["entered"], sum(not v.startswith("PENDING") for v in sv.values()))
        self.assertLess(row["entered"], len(sv))

    def drop_case(self, **kw):
        bad = first_lineup()[1]                         # the first line-up's first clip after the hook
        r, seq = self._rig_with(bad, **kw)
        return bad, r, seq, r.run()

    def _rig_with(self, bad, a_fail=False, unavailable=False, money=False):
        kw = {}
        if a_fail:
            kw["a_fail"] = {("heimdall", bad): ["NOT_OWN_SINCERE"]}
        if unavailable:
            kw["unavailable"] = {("heimdall", bad)}
        return lean_rig(n=3, money={("heimdall:deepseek", bad)} if money else (), **kw)

    def test_a_failing_segment_drops_its_line_up_and_the_next_one_is_tried(self):
        bad, r, seq, out = self.drop_case(a_fail=True)
        t0 = out["tried"][0]
        self.assertTrue(t0["second_vendor"][bad].startswith("FAIL"), t0)
        self.assertIn("the line-up is dropped", t0["why"])
        pk = out["package"]
        self.assertIsNotNone(pk, out.get("why_none"))
        self.assertNotIn(bad, [sg["moment_id"] for sg in pk["segments"]])
        later = [s[2] for s in seq if s[0] == "medley"][1:]
        self.assertTrue(later and all(bad not in ids for ids in later), seq)    # out for good

    def test_an_unanswered_segment_drops_its_line_up(self):
        bad, r, seq, out = self.drop_case(unavailable=True)
        t0 = out["tried"][0]
        self.assertTrue(t0["second_vendor"][bad].startswith("HELD"), t0)
        self.assertEqual(out["prescreen"]["held_102"]["second"], [bad])
        self.assertEqual(out["prescreen"]["budget_102"]["second"], [])
        self.assertNotIn(bad, [sg["moment_id"] for sg in (out["package"] or {}).get("segments") or []])

    def test_a_refusal_for_money_stops_the_search_as_budget_never_as_a_provider(self):
        bad, r, seq, out = self.drop_case(money=True)
        t0 = out["tried"][0]
        self.assertEqual((t0["measure"], t0.get("budget")), ("BUDGET_REFUSED", True), t0)
        self.assertTrue(t0["second_vendor"][bad].startswith("BUDGET"), t0)
        self.assertIsNone(out["package"])
        self.assertEqual(out["prescreen"]["budget_102"]["second"], [bad])
        self.assertEqual(out["prescreen"]["held_102"]["second"], [])
        vc = OC.verdict_classes(out)
        self.assertEqual(vc["undone"]["provider_unavailable"], 0)
        self.assertEqual(vc["undone"]["budget_refused"], 1)
        self.assertEqual(vc["lineups"]["budget_refused"], 1)

    def test_the_seal_is_wired_in(self):
        """MUST-FAIL: a seal that refuses: no package is returned, its reason is the line-up's."""
        r, _ = lean_rig()
        with mock.patch.object(PK, "seal_second_refusal", lambda *a, **k: "A: the seal refuses: test"):
            out = r.run()
        self.assertIsNone(out["package"])
        self.assertTrue(any("the seal refuses" in str(t.get("why")) for t in out["tried"]), out["tried"])

    def test_the_old_path_is_as_it_was(self):
        """lean=False (the tests' rigs): the second screen before the line-up, as before; no PENDING."""
        r = T163.rig(n=2)
        out = r.run()
        self.assertIsNotNone(out["package"], out.get("why_none"))
        self.assertFalse(any(v == PK.PENDING for v in out["prescreen"]["second_vendor"].values()))
        self.assertNotIn("deferred_second", out["prescreen"])


class TheSeal(unittest.TestCase):
    """THE SEAL REFUSES unless every segment, its opener first, holds a PASS second-vendor verdict off its first
    verdict's vendor and family (package.seal_second_refusal)."""

    def setUp(self):
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        self.router = type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek":
                                                  B("heimdall", "deepseek"), "google:gemini": B("google", "gemini"),
                                                  "local_judge:gemma3:27b": B("local_judge", "gemma")}})()
        self.first = dict(TM.Rig.A_OK, backend="xai:grok")
        self.segs = [{"label": "hook", "moment_id": "h"}, {"label": "clip_01", "moment_id": "x"},
                     {"label": "clip_02", "moment_id": "y"}]
        self.a_first = {m: self.first for m in ("h", "x", "y")}
        ok = dict(TM.Rig.A_OK, backend="google:gemini")
        self.a_two = {m: [self.first, ok] for m in ("h", "x", "y")}

    def refusal(self, a_two=None, soft_two=(), soft=False):
        return PK.seal_second_refusal(self.router, self.segs, self.a_first, self.a_two if a_two is None else a_two,
                                      soft_two, soft)

    def test_every_segment_with_its_pass_seals(self):
        self.assertIsNone(self.refusal())

    def test_a_pending_segment_cannot_seal(self):
        a2 = dict(self.a_two)
        del a2["y"]
        self.assertIn("clip_02 y", self.refusal(a2))

    def test_a_failing_segment_cannot_seal(self):
        a2 = dict(self.a_two, x=[self.first, dict(TM.Rig.A_OK, backend="google:gemini", view="attributed")])
        self.assertIn("clip_01 x", self.refusal(a2))

    def test_an_unanswered_segment_cannot_seal(self):
        a2 = dict(self.a_two, x=[self.first])                       # its first only: the second gave no answer
        self.assertIn("clip_01 x", self.refusal(a2))

    def test_a_verdict_from_the_first_s_vendor_or_the_local_judge_cannot_seal(self):
        for b in ("xai:grok", "local_judge:gemma3:27b"):
            a2 = dict(self.a_two, h=[self.first, dict(TM.Rig.A_OK, backend=b)])
            self.assertIn("hook h", self.refusal(a2), b)            # the opener first

    def test_the_never_empty_pass_accepts_only_its_own_soft_codes(self):
        a2 = dict(self.a_two)
        del a2["y"]
        self.assertIsNone(self.refusal(a2, soft_two={"y": ["REFERENT_OUTSIDE"]}, soft=True))
        self.assertIsNotNone(self.refusal(a2, soft_two={"y": ["REFERENT_OUTSIDE"]}, soft=False))


class TheCache(unittest.TestCase):
    """B: package.prescreen's step-A cache, as second_for asks it (kind step_a_second, off the first's vendor)."""
    pool = TM.TestRuling58StepAEveryCandidate.pool
    router = TM.TestRuling58StepAEveryCandidate.router
    fake = TM.TestRuling58StepAEveryCandidate.fake

    def second(self, ms, srcs, cache, router=None):
        return PK.prescreen(router or self.router(), ms, srcs, TM.ctx(), {"xai"}, {"grok"}, cache=cache,
                            kind="step_a_second")

    def asked(self, calls):
        return sorted(sum((c[0] for c in calls), []))

    def test_the_same_segment_is_paid_once_and_every_change_misses(self):
        ms, srcs = self.pool(3)
        calls = []
        self.fake(calls)
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "STEP_A_CACHE.json")
            self.second(ms, srcs, cache)
            self.assertEqual(self.asked(calls), ["m00", "m01", "m02"])
            calls.clear()
            self.second(ms, srcs, cache)
            self.assertEqual(calls, [])                                   # identical: never paid again
            words, srcs2 = self.pool(3, words="is the softest money ever made")
            calls.clear()
            self.second(words[:1], dict(srcs, vm00=srcs2["vm00"]), cache)
            self.assertEqual(self.asked(calls), ["m00"])                 # MUST-FAIL: changed words miss
            cut = [dict(ms[0], words=[ms[0]["words"][0] + 1, ms[0]["words"][1]])]   # the same text: the cut moves
            calls.clear()
            self.second(cut, srcs, cache)
            self.assertEqual(self.asked(calls), ["m00"])                 # MUST-FAIL: a changed cut misses
            other = TM.source(["Before it came a different part of the show.", "Bitcoin number 0 is the hardest "
                               "money ever made.", "After it came the end of the show."], vid="vm00")
            calls.clear()
            self.second(ms[:1], dict(srcs, vm00=other), cache)
            self.assertEqual(self.asked(calls), ["m00"])                 # MUST-FAIL: a changed context misses
            calls.clear()
            with mock.patch.object(PK, "STEP_A_VERSION", "another-version"):
                self.second(ms[:1], srcs, cache)
            self.assertEqual(self.asked(calls), ["m00"])                 # MUST-FAIL: a changed prompt version misses

    def test_a_cached_verdict_counts_only_from_a_model_of_the_chain(self):
        ms, srcs = self.pool(2)
        calls = []
        self.fake(calls)
        r = self.router()
        r.chain = lambda role, kind=None: ["heimdall:deepseek"]
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "c.json")
            self.second(ms, srcs, cache, r)
            calls.clear()
            self.second(ms, srcs, cache, r)
            self.assertEqual(calls, [])                                   # its model is the chain's: reused
            r.chain = lambda role, kind=None: ["openai:gpt"]
            calls.clear()
            self.second(ms, srcs, cache, r)
            self.assertEqual(self.asked(calls), ["m00", "m01"])          # MUST-FAIL: another model never stands in

    def test_a_fail_is_cached_as_a_fail_and_no_answer_is_never_cached(self):
        import context_integrity as CI
        from test_gates import a_item
        ms, srcs = self.pool(2)
        calls, boom = [], {"on": True}

        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
            calls.append((sorted(contexts), seed))
            if "m01" in contexts and boom["on"]:
                raise P.ProviderError("context_verdict: every back-end unavailable")
            return {mid: dict(a_item(mid), backend="heimdall:deepseek",
                              **({"view": "attributed"} if mid == "m00" else {})) for mid in contexts}, \
                "heimdall:deepseek"
        saved = CI.step_a
        CI.step_a = step_a
        self.addCleanup(setattr, CI, "step_a", saved)
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "c.json")
            for m in ms:
                self.second([m], srcs, cache)
            calls.clear()
            a_by, fails, _, _ = self.second(ms[:1], srcs, cache)
            self.assertEqual(calls, [])                                   # the FAIL is read back, not asked
            self.assertTrue(fails["m00"] and not PK.is_held(fails["m00"]))
            boom["on"] = False
            calls.clear()
            self.second(ms[1:], srcs, cache)
            self.assertEqual(self.asked(calls), ["m01"])                 # no answer was never cached: asked again

    def test_a_later_line_up_asks_only_for_the_segments_it_lacks(self):
        bad = first_lineup()[1]
        r, seq = lean_rig(n=3, a_fail={("heimdall", bad): ["NOT_OWN_SINCERE"]})
        out = r.run()
        second = seconds_of(seq)
        passed_first = [m for m in second[0][2] if m != bad]
        for s in second[1:]:
            self.assertFalse(set(s[2]) & set(passed_first), seq)        # never asked twice in one build
        self.assertIsNotNone(out["package"], out.get("why_none"))


class TheMisclassification(unittest.TestCase):
    def test_build_172_its_two_refused_gemini_calls_are_15_budget_refused(self):
        """C, replayed from build 172's record: the 15 moments of its two Gemini calls the completion reserve refused
        are budget_refused, 0 provider_unavailable; read with the code as it now writes the record, and the record as
        it ran read again."""
        with open(os.path.join(B172, "package.json")) as f:
            rec = json.load(f)
        with open(os.path.join(B172, "FINGERPRINT.json")) as f:
            fp = json.load(f)
        sv = rec["never_empty"]["soft_record"]["prescreen"]["second_vendor"]
        off_fail = {mid: [v[len("HELD: "):]] for mid, v in sv.items() if v.startswith("HELD: ")}
        self.assertEqual(len(off_fail), 15)
        held, budget = PK.held_and_budget(off_fail, off_fail)
        self.assertEqual((len(held), len(budget)), (0, 15))
        rec2 = copy.deepcopy(rec)
        pre2 = rec2["never_empty"]["soft_record"]["prescreen"]
        pre2["held_102"], pre2["budget_102"] = {"first": [], "second": held}, {"first": [], "second": budget}
        items = OC.undone(rec2, rec2.get("spotlight"), fp["spend_refused"])
        self.assertEqual(sum(1 for x in items if x["kind"] == "budget"), 15)
        self.assertFalse([x for x in items if x["kind"] == "held"])
        vc = OC.verdict_classes(rec2, {"undone": items})
        self.assertEqual((vc["undone"]["budget_refused"], vc["undone"]["provider_unavailable"]), (21, 0))
        vc_as_ran = OC.verdict_classes(rec, fp)                        # the record as it ran, read again
        self.assertEqual((vc_as_ran["undone"]["budget_refused"], vc_as_ran["undone"]["provider_unavailable"]),
                         (21, 0))

    def test_a_refusal_for_money_and_a_silent_provider_are_their_own_kinds(self):
        money, silent = [PK.held_why(P.CompletionReserve(MONEY))], \
            [PK.held_why(P.ProviderError("context_verdict: every back-end unavailable"))]
        self.assertTrue(PK.is_held(money) and PK.is_budget(money))
        self.assertTrue(PK.is_held(silent) and not PK.is_budget(silent))
        self.assertEqual(PK.held_and_budget({"a": money, "b": silent}, ["a", "b"]), (["b"], ["a"]))
        rec = {"prescreen": {"held_102": {"first": [], "second": ["b"]}, "budget_102": {"first": [], "second": ["a"]},
                             "second_vendor": {"a": "BUDGET: " + money[0], "b": "HELD: " + silent[0]}}}
        vc = OC.verdict_classes(rec, {"undone": OC.undone(rec)})
        self.assertEqual((vc["undone"]["budget_refused"], vc["undone"]["provider_unavailable"]), (1, 1))


class TheReserveIsUnchanged(TLR.RouterCase):
    def test_a_speculative_call_still_may_not_eat_the_reserve(self):
        """D, MUST-FAIL: $0.60 spent, the $0.87 completion reserve held back: a speculative Grok verdict that fits the
        limit but not the reserve is refused before the back-end is asked; while completing it is made."""
        TLR.ledger(self.path, 0.60)
        self.r.completion_reserve_usd = 0.8651
        with self.assertRaises(P.CompletionReserve):
            self.r.call("coherence_verdict", self.prompt, 1200, 7)
        self.assertEqual(self.asked, [])
        self.r.completing = True
        self.r.call("coherence_verdict", self.prompt, 1200, 7)
        self.assertEqual(len(self.asked), 1)

    def test_the_deferred_call_and_the_alternatives_search_and_only_the_passed_line_up_completes(self):
        bad = first_lineup()[1]
        r, seq = lean_rig(n=3, a_fail={("heimdall", bad): ["NOT_OWN_SINCERE"]})
        out = r.run()
        self.assertIsNotNone(out["package"], out.get("why_none"))
        self.assertTrue(all(s[3] is False for s in seq if s[0] in ("medley",) or s in seconds_of(seq)), seq)
        self.assertTrue([s for s in seq if s[0] == "write"] and
                        all(s[3] is True for s in seq if s[0] == "write"), seq)
        self.assertIs(r.router.completing, False)                       # nothing finishes after the build


class TheCeiling(unittest.TestCase):
    def setUp(self):
        p = mock.patch.dict(os.environ)
        p.start()
        self.addCleanup(p.stop)
        os.environ.pop(SC.CAP_ENV, None)

    def test_the_default_is_1_50_a_one_build_value_is_honoured_and_a_wrong_one_refused(self):
        self.assertEqual(SC.cap_usd(), 1.50)
        os.environ[SC.CAP_ENV] = "3.00"
        self.assertEqual(SC.cap_usd(), 3.00)
        for bad in ("5.01", "0", "-1", "abc", "nan", "inf"):
            os.environ[SC.CAP_ENV] = bad
            with self.assertRaises(SC.CeilingRefused, msg=bad):
                SC.cap_usd()

    def test_the_one_ledger_reserves_up_to_the_value_in_force(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        prod = os.path.join(d, "production")
        os.makedirs(prod)
        os.environ.update({"PP_SPEND_LEDGER_DIR": os.path.join(d, "spend"), "PP_SPEND_PROD_BUILDER": prod,
                           "PP_SPEND_PROD_OUTSIDE": os.path.join(prod, "outside.jsonl"),
                           "PP_SPEND_PROD_RUNS": "no-production-run-in-a-test"})
        SC.init_day({}, by="test (E)")
        with self.assertRaises(SC.CeilingRefused):
            SC.reserve("xai:grok", 2.00)                                # the $1.50 default
        os.environ[SC.CAP_ENV] = "3.00"
        key = SC.reserve("xai:grok", 2.00)                              # the one-build $3.00
        SC.settle(key, "xai:grok", 0.0)
        with self.assertRaises(SC.CeilingRefused):
            SC.reserve("xai:grok", 3.01)
        self.assertEqual(SC.status()["cap"], 3.00)

    def test_the_builder_s_router_takes_the_same_value(self):
        code = "import sys; sys.path[:0] = ['tests/package', 'pipeline']; import proof_ly as PL; print(PL.DAY_CAP_USD)"
        for env, want in ({}, "1.5"), ({SC.CAP_ENV: "3.00"}, "3.0"):
            r = subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, capture_output=True, text=True,
                               env=dict({k: v for k, v in os.environ.items() if k != SC.CAP_ENV}, **env))
            self.assertEqual(r.stdout.strip(), want, r.stderr[-500:])

    @unittest.skipUnless(os.path.isfile(os.path.join(LEAN_RELEASE, "spend_ceiling.py")), "lean-release not here")
    def test_the_lock_service_and_the_renderer_read_the_same_one_place(self):
        """The lock service and the renderer import lean-release's spend_ceiling (the same bytes): the same value."""
        with open(os.path.join(REPO, "pipeline", "spend_ceiling.py"), "rb") as a, \
                open(os.path.join(LEAN_RELEASE, "spend_ceiling.py"), "rb") as b:
            self.assertEqual(a.read(), b.read())
        code = f"import sys; sys.path.insert(0, {LEAN_RELEASE!r}); import spend_ceiling as S; print(S.cap_usd())"
        for env, want in ({}, "1.5"), ({SC.CAP_ENV: "3.00"}, "3.0"):
            r = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True,
                               env=dict({k: v for k, v in os.environ.items() if k != SC.CAP_ENV}, **env))
            self.assertEqual(r.stdout.strip(), want, r.stderr[-500:])

    def test_the_launcher_passes_it_to_every_program_and_records_it(self):
        import lean_ops as LO
        p = LO.paths(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, p["run"], True)
        self.assertEqual(LO.env_builder(p, "b").get(SC.CAP_ENV), None)
        self.assertEqual(OC.ceiling_note(), {})                          # the default: nothing on the line
        self.assertIsNone(LO.ceiling_from_args(argparse.Namespace(what="run", ceiling_usd=3.0)))
        self.assertEqual(os.environ[SC.CAP_ENV], "3.00")
        for n in ("lockcheck", "scorer", "render"):
            self.assertEqual(LO.env_instance(p, n, "b")[SC.CAP_ENV], "3.00", n)
        self.assertEqual(LO.env_builder(p, "b")[SC.CAP_ENV], "3.00")
        script = LO.service_script(p, "lockcheck", LO.env_instance(p, "lockcheck", "b"), [])
        line = next(x for x in script.split("\n") if x.startswith("env "))
        self.assertLess(line.index(f"--unset={SC.CAP_ENV}"), line.index(f"{SC.CAP_ENV}=3.00"))
        self.assertEqual(OC.ceiling_note()["ceiling_usd"], 3.0)

    def test_the_launcher_refuses_a_wrong_or_inherited_value(self):
        import lean_ops as LO
        ns = lambda what, v=None: argparse.Namespace(what=what, ceiling_usd=v)
        self.assertIn("outside", LO.ceiling_from_args(ns("run", 6.0)))
        os.environ[SC.CAP_ENV] = "2.00"
        self.assertIn("only from --ceiling-usd", LO.ceiling_from_args(ns("run")))
        self.assertIn("is not --ceiling-usd", LO.ceiling_from_args(ns("launch", 3.0)))
        self.assertIsNone(LO.ceiling_from_args(ns("guard")))           # no paid call: the guard runs
        os.environ[SC.CAP_ENV] = "3.00"
        self.assertIsNone(LO.ceiling_from_args(ns("run", 3.0)))        # run's detached child: the same value


class TheBound(unittest.TestCase):
    def test_after_the_bound_the_search_stops_before_another_deferred_call(self):
        bad = first_lineup()[1]
        r, seq = lean_rig(n=3, a_fail={("heimdall", bad): ["NOT_OWN_SINCERE"]})
        with mock.patch.object(PK, "DEFERRED_LINEUPS_MAX", 1):
            out = r.run()
        self.assertIsNone(out["package"])
        self.assertEqual(out["deferred_stop"], {"lineups": 1})
        self.assertEqual(len(seconds_of(seq)), 1, seq)
        self.assertTrue(any(str(t.get("why")).startswith("F:") for t in out["tried"]), out["tried"])

    def test_a_sealed_medley_stops_the_search(self):
        import proof_ledger as PL
        self.assertIsNone(PL.sealed_stops_search({"package": None}))
        sp = PL.sealed_stops_search({"package": {"segments": []}})
        self.assertIsNone(sp["package"])
        self.assertTrue(sp["why_none"].startswith("F: the medley sealed"))
        r, seq = lean_rig(n=3)
        out = r.run()
        self.assertIsNotNone(out["package"])
        self.assertEqual((len([s for s in seq if s[0] == "medley"]), len(seconds_of(seq))), (1, 1))


if __name__ == "__main__":
    unittest.main()
