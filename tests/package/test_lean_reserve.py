#!/usr/bin/env python3
"""LEAN (5) + (3) (the owner's assignment, 13:37 ET Nov 24, issues 5 and 3: "Upstream spending can exhaust the budget
required for final verification and delivery"; "Build 171's second and third line-ups were unmeasured because of
SpendLimit, not genuine editorial failures").

(5) THE COMPLETION RESERVE: providers.Router.completion_reserve_usd is the money a SPECULATIVE paid call must leave
    under the limit; while a line-up that passed its clips-alone verdict is being finished (router.completing, set by
    package._build) its calls may spend it. package.completion_reserve(router) sizes it from the router's own
    reservations; the driver sets it before any paid call.
(3) A VERDICT THAT WAS NOT MEASURED IS NO FAILURE: a line-up whose clips-alone verdict the spend stop (or the reserve)
    refused is BUDGET_REFUSED, one no back-end answered PROVIDER_UNAVAILABLE, anything else UNMEASURED; never "no
    through-line"; a clip whose corrected-words verdict was not measured is never put out for good; the outcome line
    keeps the four kinds apart (outcomes.verdict_classes).

Every test here runs offline: no model, no network (the router's back-ends are stubbed at complete())."""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
for _p in ("pipeline", "tests/package", "tests/eligibility", "tests/moments"):
    sys.path.insert(0, os.path.join(REPO, _p))
import outcomes as OC  # noqa: E402
import package as PK  # noqa: E402
import providers as P  # noqa: E402
import test_medley as TM  # noqa: E402
import test_ruling_163 as T163  # noqa: E402
from test_moments import pm  # noqa: E402

GROK = "xai:grok-4.20-0309-reasoning"
B171 = os.path.join(HERE, "proof", "ledger_20261124_175601")      # build 171's record (12:56 ET Nov 24)
SPEND_171 = "SpendLimit: spend (reported) 1.43 USD + reserved 0.00 + this call's upper bound 0.08 > the limit 1.5 USD"


def ledger(path, spent_reported):
    """A day ledger whose cap basis (capped vendors' reported dollars) stands at `spent_reported`."""
    with open(path, "w") as f:
        json.dump({"usd_estimate": 0.0, "usd_reported": spent_reported, "usd_unreported_estimate": 0.0, "calls": 1,
                   "by_backend": {GROK: {"calls": 1, "in": 0, "out": 0, "usd_estimate": 0.0, "usd_reported":
                                         spent_reported, "reported_calls": 1, "in_reported": 0,
                                         "price_usd_per_1m": [5, 25]}},
                   "by_role": {}, "reserved": {}}, f)


class RouterCase(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.path = os.path.join(self.d, "SPEND.json")
        ledger(self.path, 0.832)                         # build 171's start: $0.83 of $1.50
        self.r = P.Router(spend_path=self.path, limit_usd=1.50, limit_basis="reported", uncapped=("heimdall",),
                          chains={"coherence_verdict": [GROK]})
        self.asked = []
        b = self.r.backends[GROK]
        b.complete = lambda prompt, max_tokens, seed, system=None: (self.asked.append(prompt) or
                                                                     ('{"ok": true}', {"in": 10, "out": 10,
                                                                                       "usd_reported": 0.011}, 0.1))
        self.prompt = "x" * 3000

    def held(self):
        with open(self.path) as f:
            return json.load(f)["reserved"]


class TestTheReserveAtTheRouter(RouterCase):
    def test_a_speculative_call_that_would_eat_the_reserve_is_refused_and_named(self):
        """MUST-FAIL: $0.83 spent of $1.50, $0.62 held back: a speculative Grok call ($0.08 reservation) fits the
        limit but not the reserve: BUDGET_REFUSED by the reserve, before the back-end is asked, recorded twice
        (spend_refused, reserve_refused)."""
        self.r.completion_reserve_usd = 0.62
        with self.assertRaises(P.CompletionReserve) as e:
            self.r.call("coherence_verdict", self.prompt, 1200, 7)
        self.assertIsInstance(e.exception, P.SpendLimit)                 # every caller's spend-stop handling applies
        self.assertIn("completion reserve", str(e.exception))
        self.assertEqual(self.asked, [])                                 # nothing was asked, nothing was paid
        self.assertEqual((self.r.spend_refused, self.r.reserve_refused), ([GROK], [GROK]))
        self.assertEqual(self.held(), {})                                # no reservation left behind

    def test_the_finishing_line_up_may_spend_the_reserve(self):
        """MUST-PASS: the same call while a package is being finished (router.completing) is made."""
        self.r.completion_reserve_usd = 0.62
        self.r.completing = True
        got = self.r.call("coherence_verdict", self.prompt, 1200, 7)
        self.assertEqual(got.text, '{"ok": true}')
        self.assertEqual((len(self.asked), self.r.spend_refused, self.held()), (1, [], {}))

    def test_no_reserve_is_the_router_as_before_and_the_cap_still_binds_a_finishing_call(self):
        got = self.r.call("coherence_verdict", self.prompt, 1200, 7)    # completion_reserve_usd 0 (the default)
        self.assertEqual(len(self.asked), 1)
        self.assertIsNotNone(got)
        ledger(self.path, 1.45)                                          # the day's cap itself: never passed, also
        self.r.completing, self.r.completion_reserve_usd = True, 0.62    # not by a finishing call
        with self.assertRaises(P.SpendLimit) as e:
            self.r.call("coherence_verdict", self.prompt, 1200, 7)
        self.assertNotIsInstance(e.exception, P.CompletionReserve)
        self.assertEqual(self.r.reserve_refused, [])


class TestTheReserveIsEnough(RouterCase):
    def test_it_covers_every_finishing_call_it_counts_even_billed_at_its_reservation(self):
        """MUST-PASS: the day standing at limit - reserve, every call the reserve counts (each reserved at the router's
        own figure and, the worst case, billed at it) is made while finishing; MUST-FAIL: before that, a speculative
        call of the smallest size the reserve counts is refused by the reserve."""
        res = PK.completion_reserve(self.r)
        self.assertGreater(res["usd"], 0.0)
        whats = [p["what"] for p in res["parts"]]
        for want in ("vision", "appeals", "value", "coherence", "second ear", "lock pre-check", "sign-off"):
            self.assertTrue([w for w in whats if want in w], (want, whats))
        self.assertEqual(res["segments"], 3)
        self.assertIn("monthly quota", res["unpriced"][0])               # the voice: not in dollars, said so
        inside = round(sum(p["usd"] for p in res["parts"] if p["backend"]), 6)   # what the router itself will hold
        ledger(self.path, round(1.50 - inside, 6))
        self.r.completion_reserve_usd = inside
        small = min(p["usd_each"] for p in res["parts"] if p["backend"])
        b0 = self.r.backends[next(p["backend"] for p in res["parts"] if p["backend"])]
        with self.assertRaises(P.CompletionReserve):
            self.r._reserve(b0, small)
        self.r.completing = True
        for p in res["parts"]:
            if not p["backend"]:
                continue                                                 # outside the router (the lock's Scribe, the
            b = self.r.backends[p["backend"]]                            # render's sign-off): the day cap counts them
            for _ in range(p["calls"]):
                key = self.r._reserve(b, p["usd_each"])                  # never refused
                self.r._settle(key, b, {"in": 0, "out": 0, "usd_reported": p["usd_each"]}, p["usd_each"], "t")

    def test_it_follows_the_router_s_own_figures(self):
        """The reserve is the router's own reservation sizes: when Grok's reserve trips back to list for the day
        (rulings 123 (1) / 130 (3)), the appeals and verdicts it holds back grow with it."""
        before = PK.completion_reserve(self.r)
        with open(self.path) as f:
            d = json.load(f)
        d["reserve_tripped"] = {GROK: {"why": "billed above its reserve"}}
        with open(self.path, "w") as f:
            json.dump(d, f)
        after = PK.completion_reserve(self.r)
        part = lambda r, w: next(p for p in r["parts"] if w in p["what"])
        self.assertAlmostEqual(part(after, "appeals")["usd_each"], 4 * part(before, "appeals")["usd_each"], places=4)
        self.assertGreater(after["usd"], before["usd"])


class MoneyRig(TM.Rig):
    """The medley rig whose clips-alone verdicts may come back UNMEASURED: "SPEND" (the spend stop refused it, as
    build 171's line-ups 2 and 3), "DOWN" (no back-end answered)."""
    ERR = {"SPEND": SPEND_171, "DOWN": "ProviderError: coherence_verdict: every back-end unavailable: [...]",
           "JUNK": "ValueError: clips-alone verdict out of contract"}

    def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
        self.__dict__.setdefault("phase_at_medley", []).append(getattr(router, "completing", None))
        if self.medleys and isinstance(self.medleys[0], str):
            self.medley_calls.append([m["moment_id"] for m in segs])
            return False, {"error": self.ERR[self.medleys.pop(0)], "measured": False, "flagged": None}
        return super().medley(router, segs, ctx_, wv, seed, writer_family)

    def write(self, router, *a, **k):
        self.__dict__.setdefault("phase_at_write", []).append(getattr(router, "completing", None))
        return super().write(router, *a, **k)


MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]


class TestUnmeasuredIsNoFailure(unittest.TestCase):
    def test_a_line_up_the_spend_stop_refused_is_budget_refused_never_no_through_line(self):
        """MUST-PASS: build 171's line-up 2 / 3 case: the clips-alone verdict refused by the spend stop."""
        rig = MoneyRig(MS, ["h", "x", "y", "z"], ["SPEND"], [])
        out = rig.run()
        t = out["tried"][0]
        self.assertEqual(t["measure"], "BUDGET_REFUSED")
        self.assertTrue(t["why"].startswith("BUDGET_REFUSED: the clips-alone verdict was not measured (SpendLimit"),
                        t["why"])
        self.assertNotIn("no through-line", t["why"])
        self.assertTrue(t["budget"])                                     # a registry candidate stays open
        self.assertEqual(rig.write_calls, [])                            # nothing judged, nothing written
        self.assertEqual(OC.classify(out["why_none"], out["prescreen"], out["hook_pool"], out["tried"])["outcome"],
                         "BUDGET_STOPPED")

    def test_no_answer_and_an_answer_out_of_contract_are_their_own_kinds(self):
        for err, kind in (("DOWN", "PROVIDER_UNAVAILABLE"), ("JUNK", "UNMEASURED")):
            out = MoneyRig(MS, ["h", "x", "y", "z"], [err], []).run()
            self.assertEqual(out["tried"][0]["measure"], kind)
            self.assertTrue(out["tried"][0]["why"].startswith(kind + ":"), out["tried"][0]["why"])

    def test_a_measured_no_is_still_a_measured_failure(self):
        """MUST-FAIL: the verdict was asked and said there is no through-line: an editorial failure, as before."""
        out = MoneyRig(MS, ["h", "x", "y", "z"], [(False, [], None, "none")], []).run()
        t = out["tried"][0]
        self.assertEqual(t["measure"], "MEASURED_FAILURE")
        self.assertIn("no through-line", t["why"])
        self.assertNotIn("not measured", t["why"])
        self.assertFalse(t.get("budget"))

    def test_an_unmeasured_candidate_verdict_never_closes_the_candidate(self):
        med = {"through_line": "Nobody controls the rules.", "clips": {"hook": 4, "clip_01": 4, "clip_02": 4},
               "flagged": [], "measured": True, "replayed": False, "backend": "xai:grok"}
        c = PK.load_candidate({"tried": [{"angle": 1, "text": "W", "lineup": ["h", "x", "y"], "supply_exception": None,
                                          "medley": med, "medley_ok": True}],
                               "angles": [{"angle": "W", "moments": ["h", "x", "y", "z"], "hook": "h"}],
                               "angle_backend": "heimdall:deepseek", "angle_tried": []}, source="proof/ledger_x")
        out = MoneyRig(MS, ["h", "x", "y", "z"], ["SPEND"], [], candidate=c).run()
        self.assertEqual(out["candidate"]["class"], "budget")            # kept open, never "clip" (closed for good)
        out = MoneyRig(MS, ["h", "x", "y", "z"], [(False, [], None, "none")], [], candidate=c).run()
        self.assertEqual(out["candidate"]["class"], "clip")              # a measured no closes it, as before


class TestTheCorrectedWordsVerdict(unittest.TestCase):
    def test_an_unmeasured_verdict_on_the_corrected_words_puts_no_clip_out(self):
        """MUST-PASS: build 171 line-up 1's case: the lock corrected a clip; its clips-alone verdict on the corrected
        words was refused for money: BUDGET_REFUSED, the clip NOT doomed, nothing written, the search stops."""
        r = T163.rig(n=1, lock_check=T163.melker_lock())
        r.__class__ = MoneyRig
        r.medleys = [(True, [], None, TM.Rig.LINE)]                      # the line-up passes on the transcript's words

        def medley(router, segs, ctx_, wv, seed=7, writer_family=None, _m=MoneyRig.medley.__get__(r)):
            if any(PK.HEARD in m["moment_id"] for m in segs):             # the corrected words: refused for money
                r.medleys.insert(0, "SPEND")
            return _m(router, segs, ctx_, wv, seed, writer_family)
        r.medley = medley
        out = r.run()
        t = out["tried"][0]
        self.assertEqual(t.get("unmeasured"), "BUDGET_REFUSED")
        self.assertTrue(t["why"].startswith("BUDGET_REFUSED: ruling 163 (2)(b)"), t["why"])
        self.assertNotIn("fails", t["why"])
        self.assertEqual(t["heard"]["x"].get("not_measured"), "BUDGET_REFUSED")
        self.assertNotIn("out", t["heard"]["x"])
        self.assertTrue(out.get("unmeasured_stop"))
        self.assertEqual(len(out["tried"]), 1)                           # no re-line: the search stopped
        self.assertEqual(r.write_calls, [])

    def test_a_measured_no_on_the_corrected_words_still_puts_the_clip_out_for_good(self):
        """MUST-FAIL (unchanged): measured and failing on the corrected words: out under both ids."""
        r = T163.rig(n=2, lock_check=T163.melker_lock())
        r.medleys = [(True, [], None, TM.Rig.LINE), (False, [], None, "none"), (True, [], None, TM.Rig.LINE)]
        r.last_medley = (None, None)

        def medley(router, segs, ctx_, wv, seed=7, writer_family=None, _m=TM.Rig.medley.__get__(r)):
            r.last_medley = (None, None)                                 # the corrected words get their own verdict
            return _m(router, segs, ctx_, wv, seed, writer_family)
        r.medley = medley
        out = r.run()
        t = out["tried"][0]
        self.assertIn("the clips-alone verdict on the corrected words fails", t["heard"]["x"]["out"])
        self.assertIsNone(t.get("unmeasured"))
        self.assertFalse(out.get("unmeasured_stop"))
        later = [u["lineup"] for u in out["tried"][1:] if u.get("lineup")]
        self.assertFalse([lu for lu in later if "x" in lu or "x" + PK.HEARD in lu], later)


class TestThePhase(unittest.TestCase):
    def test_only_a_line_up_that_passed_its_clips_alone_verdict_spends_the_reserve(self):
        """The router is `completing` for the passed line-up's writes and gates, never for any clips-alone verdict
        (the search), and never after the build."""
        rig = MoneyRig(MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, TM.Rig.LINE), (True, [], None,
                                                                                           TM.Rig.LINE)], [None])
        rig.router.completing = False
        out = rig.run()
        self.assertIsNotNone(out["package"], out.get("why_none"))
        self.assertEqual(rig.phase_at_medley, [False, False])
        self.assertEqual(rig.phase_at_write, [True])
        self.assertIs(rig.router.completing, False)


class TestTheOutcomeLineKeepsThemApart(unittest.TestCase):
    def test_build_171_its_line_ups_2_and_3_are_budget_refused_not_editorial(self):
        """MUST-PASS on the real record (written before lean (3), so read from its verdicts): line-up 1 passed its
        clips-alone verdict, line-ups 2 and 3 were refused by the spend stop; no measured failure."""
        with open(os.path.join(B171, "package.json")) as f:
            pk = json.load(f)
        with open(os.path.join(B171, "FINGERPRINT.json")) as f:
            fp = json.load(f)
        got = OC.verdict_classes(pk, fp)
        self.assertEqual(got["lineups"], {"passed": 1, "measured_failure": 0, "budget_refused": 2,
                                          "provider_unavailable": 0, "unmeasured": 0})
        self.assertEqual(got["undone"]["budget_refused"], 6)              # 4 refused calls + 2 refused verdicts
        line = OC.outcome_of(B171)
        self.assertEqual((line["outcome"], line["verdict_classes"]), ("BUDGET_STOPPED", got))

    def test_a_measured_failure_is_never_counted_as_money(self):
        """MUST-FAIL: a record whose line-up was measured and failed counts it as a measured failure."""
        pk = {"tried": [{"lineup": ["h", "x", "y"], "medley_ok": False,
                         "medley": {"measured": True, "through_line": "None."}},
                        {"lineup": ["h", "x", "z"], "medley_ok": False, "medley": {"measured": False,
                                                                                    "error": SPEND_171}},
                        {"lineup": ["h", "y", "z"], "measure": "PROVIDER_UNAVAILABLE"}]}
        got = OC.verdict_classes(pk, {"undone": []})
        self.assertEqual(got["lineups"], {"passed": 0, "measured_failure": 1, "budget_refused": 1,
                                          "provider_unavailable": 1, "unmeasured": 0})

    def test_the_reserve_s_refusals_say_so_on_the_line(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        run = os.path.join(d, "ledger_20261124_175601")
        shutil.copytree(B171, run)
        with open(os.path.join(run, "package.json")) as f:
            pk = json.load(f)
        pk["completion_reserve"] = {"usd": 0.6, "refused": [GROK, GROK]}
        with open(os.path.join(run, "package.json"), "w") as f:
            json.dump(pk, f)
        line = OC.outcome_of(run)
        self.assertIn("2 of them held back by the completion reserve", line["gate"])
        self.assertEqual(line["note"], OC.NOTE_RESERVE)


if __name__ == "__main__":
    unittest.main()
