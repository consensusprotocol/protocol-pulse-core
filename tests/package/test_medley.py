#!/usr/bin/env python3
"""L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12): the packager's MEDLEY, offline.

- The arithmetic: the clips' seconds that let ONE takeaway land the factory's estimate in 60-70 s, and the takeaway's
  word budget, which lands it there.
- The line-up: the hook + 2-4 clips in the proposer's play order, one per channel (a repeat only as the recorded supply
  exception).
- The clips-ALONE verdict's contract.
- The writer's contract: a bridge only at the flagged join.
- ly_shape's must-fail cases.
- The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
"""
import json
import re
import os
import sys
import shutil
import tempfile
import unittest
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
sys.path.insert(0, HERE)
import eligibility as E  # noqa: E402
import package as PK  # noqa: E402
import package_pin  # noqa: E402
from config import BRIDGE_WORD_CAP  # noqa: E402
from test_eligibility import NOW, REG, source  # noqa: E402
from test_gates import Canned  # noqa: E402
from test_moments import pm  # noqa: E402
import house_style as HS  # noqa: E402
import visual_pin as VP  # noqa: E402

W = lambda n: " ".join(["word"] * n)


def angle(ms, hook, text="Nobody controls Bitcoin."):
    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}


def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
    js = PK.joins(labs)
    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
                          if j in flagged else "same subject"} for j in js}}


def reply(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
    """The clips-alone JUDGE's raw reply (ruling 61): the clips after the hook and the joins; the hook is not rated."""
    js = PK.joins(labs)
    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs[1:]},
            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
                          if j in flagged else "same subject"} for j in js}}


def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
    """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
    labs = PK.labels(n)
    segs = [{"label": lb, "channel_id": (chans or "ABCDEFG")[i], "duration_s": 12.0, "text": f"Bitcoin {lb}."}
            for i, lb in enumerate(labs)]
    bridges, aft = (["B " + W(5)] if bridge else []) + [W(20)], ([after] if bridge else []) + [n - 1]
    return {"shape": "medley", "segments": segs,
            "vo": {"intro": intro, "bridges": bridges, "bridges_after_clip": aft, "signoff": "S"},
            "medley": {"measured": measured, "flagged": list(flagged)},
            "bridge": {"why": bridge, "text": intro or (bridges[0] if bridge else None),
                       "confirmed_by": {"join": "x", "why": "y"}} if bridge or intro else None,
            "supply_exception": supply}



def sv(text, score, fault="none"):
    """A clip-scorer verdict on exactly `text` as build() attaches it (package.scorer_verdicts' shape, ruling 56; ruling
    60: kind "moments", no event, the affirmation is the score alone)."""
    return {"score": score, "reason": "r", "fault": fault, "affirmed": score >= 3.5, "text_sha256": PK.text_sha(text),
            "prompt_sha256": "p" * 64, "model": "gemma3:27b", "kind": "moments", "event": None,
            "rubric": "ruling 60: stand-alone only", "rule": "stand_alone.affirmed(moments=True): score >= threshold",
            "scorer_sha": "s" * 64, "threshold": 3.5, "rated_at": "2026-11-13T15:35:10Z"}


def fv(text, score, fault="none"):
    """One verdict as the integrator's verdicts file holds it (their contract, ruling 56), on exactly `text`."""
    return {"text_sha256": PK.text_sha(text), "score": score, "reason": "r", "fault": fault,
            "affirmed": score >= 3.5, "prompt_sha256": "p" * 64}            # ruling 60: the score alone


def spk(pk):
    """speakers.attribute's record on every segment, as the real flow attaches it before the pin is sealed (the
    00:05 ET Nov 13 order, item 3): an unknown speaker, measured, no person named."""
    for s in pk.get("segments") or []:
        s.setdefault("speaker", {"name": "unknown", "role": None, "line": None, "basis": None, "why": "test",
                                 "people": [], "measured": True})
    return pk

class TestMedleyArithmetic(unittest.TestCase):
    def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
        lo, hi = PK.medley_content_range()
        self.assertEqual((lo, hi), (36.7, 51.5))          # 60 - 14.30 - (20 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
        seg = lambda c: [{"duration_s": c}]               # (ruling 6, 22:40: a new takeaway is at most 20 words)
        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.LY_TAKEAWAY_MAX_WORDS)]), 60.0, places=2)
        self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
        lo1, hi1 = PK.medley_content_range(n_bridges=1)
        self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
        self.assertAlmostEqual(hi - hi1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)

    def test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps(self):
        aimed = 0
        for c10 in range(300, 560):
            c = c10 / 10
            b = PK.takeaway_budget(c)
            if b is None:
                self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
                continue
            lo, hi = b
            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.LY_TAKEAWAY_MAX_WORDS, (c, b))
            for w in (lo, hi):
                est = PK.runtime([{"duration_s": c}], [W(w)])
                self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
                p = {"segments": [{"duration_s": c, "channel": "A"}, {"duration_s": 0.0, "channel": "B"}],
                     "vo": {"intro": None, "bridges": [W(w)], "bridges_after_clip": [1]}, "runtime_s_estimate": est}
                self.assertTrue(PK.r4(p)[0], (c, w, PK.r4(p)[1]))
            aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
        self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
        self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
        b0, b1 = PK.takeaway_budget(45.0), PK.takeaway_budget(45.0, other=[W(10)])
        self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway


class TestMedleyLineup(unittest.TestCase):
    def test_the_hook_and_clips_in_the_proposers_order_one_per_channel(self):
        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
                                          pm("z", "D", 12.0), pm("e", "A", 14.0))}
        seg = PK.lineup_for(angle(["h", "y", "x", "z", "e"], "h"), by)
        self.assertEqual([m["moment_id"] for m in seg], ["h", "y", "x"])        # the earliest that fit, in that order
        self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])

    def test_more_clips_when_two_do_not_fill_the_medley(self):
        by = {m["moment_id"]: m for m in (pm("h", "A", 9.5), pm("x", "B", 9.5), pm("y", "C", 9.5), pm("z", "D", 9.5))}
        seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 38 s: the hook + 3 clips
        short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
        self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits

    def test_a_channel_twice_only_as_the_supply_exception_and_from_two_videos(self):
        by = {m["moment_id"]: m for m in (pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0),
                                          pm("e", "A", 13.0))}
        a = angle(["h", "x", "y", "e"], "h")
        self.assertIsNone(PK.lineup_for(a, by))                                    # one per channel cannot fill it
        seg = PK.lineup_for(a, by, repeat_ok=True)
        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "e"])
        same_video = dict(by, e=dict(by["e"], video_id=by["h"]["video_id"]))
        self.assertIsNone(PK.lineup_for(a, same_video, repeat_ok=True))           # never two clips of one video


class TestClipsAloneVerdict(unittest.TestCase):
    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 3, "backend": "xai:grok"}),
            pm("x", "B", 14.0), pm("y", "C", 13.0)]   # ruling 115: rated by the rigs' calibrated rater (conftest)
    LABS = ["hook", "clip_01", "clip_02"]

    def run_it(self, reply):
        r = Canned(coherence_verdict=[reply])
        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
        return ok, v, r

    def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
        r = Canned(coherence_verdict=[reply(self.LABS)])
        prompts = []
        call = r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
        self.assertTrue(ok)
        self.assertEqual(v["flagged"], [])
        self.assertNotIn("VOICE-OVER", prompts[0])
        self.assertNotIn("TITLE", prompts[0])
        self.assertIn('"hook -> clip_01"', prompts[0])
        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))

    def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
        ok, v, _ = self.run_it(reply(self.LABS, flagged=["clip_01 -> clip_02"]))
        self.assertTrue(ok)
        self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
        ok, v, _ = self.run_it(reply(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
        self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)

    def test_no_through_line_or_a_weak_clip_fails(self):
        self.assertFalse(self.run_it(reply(self.LABS, line="none"))[0])
        self.assertFalse(self.run_it(reply(self.LABS, line="Bitcoin."))[0])
        self.assertFalse(self.run_it(reply(self.LABS, ratings={"clip_02": 3}))[0])

    def test_ruling_61_115_the_hook_is_rated_once_and_passes_by_its_calibrated_bar(self):
        """Ruling 61: the hook is not rated in the line-up's verdict; its cached own-job rating stands. Ruling 115:
        it passes when EACH part is at least its calibrated floor (the rigs': scroll 3, alone 4, setup 3), rated by
        the calibrated rater; its slot is judged by that bar, never by COHERENCE_MIN; the clips keep their bar."""
        prompts = []
        r = Canned(coherence_verdict=[reply(self.LABS)])
        call = r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
        self.assertTrue(ok)
        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})   # min(scroll 5, alone 4), cached
        self.assertEqual(tuple(v["hook_own"][k] for k in ("scroll", "alone", "setup", "rating", "passes")),
                         (5, 4, 3, 4, True))
        self.assertNotIn(PK.HOOK_QUESTION, prompts[0])                         # never re-asked per line-up
        self.assertIn("NOT rated here", prompts[0])
        self.assertIn('"hook -> clip_01"', prompts[0])                         # 'sets up': the hook's own join
        self.assertNotIn('"hook": 1', prompts[0])
        self.assertIn('"clip_01": 1, "clip_02": 1', prompts[0])
        run = lambda hr: PK.medley(Canned(coherence_verdict=[reply(self.LABS)]),
                                   [dict(self.SEGS[0], hook_rating=hr), *self.SEGS[1:]], E.Context(NOW, REG), set())
        ok, v = run({"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"})   # every part AT its floor
        self.assertEqual((ok, v["clips"]["hook"], v["hook_own"]["passes"]), (True, 3, True))   # 3 < COHERENCE_MIN
        for hr in ({"scroll": 2, "alone": 5, "setup": 5, "backend": "xai:grok"},   # one part under its floor
                   {"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"},
                   {"scroll": 5, "alone": 5, "setup": 2, "backend": "xai:grok"},   # setup counts (ruling 115)
                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"},   # not the rater
                   {"scroll": 5, "alone": 5, "backend": "xai:grok"}):              # a part missing: fail closed
            ok, v = run(hr)
            self.assertFalse(ok, hr)
            self.assertIs(v["hook_own"].get("passes", False), False)
        ok, v = PK.medley(Canned(coherence_verdict=[reply(self.LABS)]), [pm("h", "A", 12.0), *self.SEGS[1:]],
                          E.Context(NOW, REG), set())
        self.assertFalse(ok)                                                   # no cached rating: fail closed
        self.assertNotIn("hook", v["clips"])
        ok, v, _ = self.run_it(reply(self.LABS, ratings={"clip_01": 3}))
        self.assertFalse(ok)                                                   # the clips keep their bar

    def test_out_of_contract_is_not_measured_and_rejected(self):
        good = reply(self.LABS)
        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
                    dict(good, vo_point=5),
                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),            # the hook among the clips
                    dict(good, hook={"scroll": 5, "alone": 5, "setup": 5}),               # a hook rating (ruling 61)
                    dict(good, clips={"clip_01": 6, "clip_02": 5})):
            ok, v, r = self.run_it(bad)
            self.assertFalse(ok)
            self.assertFalse(v["measured"])
            self.assertIsNone(v["flagged"])
            self.assertEqual(r.rejected, ["fake:coherence_verdict"])


class TestRuling130CoherencePanel(unittest.TestCase):
    """RULING 130 (4) / RULING 118 (2): the coherence verdict of the free panel (qwen + minimax + gpt-oss), asked as the
    panel replay measured it: each member at seeds 7 and 8 under the JSON-only contract line and 900 s, a malformed
    answer asked once more (seed + 100), the closing-brace rule; fewer than 3 members answering is no verdict; the panel
    passes when MORE THAN HALF of all its answers pass the bar; never the writers' vendor or family."""
    M = ["heimdall:qwen/qwen3.8-27b", "heimdall:minimax/minimax-m3.1-flash", "heimdall:openai/gpt-oss-20b"]
    FAM = {M[0]: "qwen", M[1]: "minimax", M[2]: "gpt-oss"}
    GOOD = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 5, "clip_02": 4}, "vo_point": 4}
    BAD = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 5, "clip_02": 3}, "vo_point": 2}

    def router(self, answers):
        """answers: {member: {seed: dict | str (raw text) | Exception}}; a seed with no entry raises ProviderError."""
        import providers as P
        calls, M, FAM = [], self.M, self.FAM

        class R:
            config = {"roles": {"coherence_panel": {"chain": M, "seeds": [7, 8], "min_members": 3, "deadline_s": 900}}}
            backends = {n: type("B", (), {"vendor": "heimdall/" + FAM[n], "family": FAM[n]})() for n in M}

            def chain(self, role, kind=None):
                return list(M) if role == "coherence_panel" else []

            def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
                     avoid_family=None, deadline_s=None, kind=None):
                left = [n for n in M if FAM[n] not in set(avoid_family or ()) and n not in set(avoid_model or ())]
                if role != "coherence_panel" or not left:
                    raise P.ProviderError(f"{role}: every back-end unavailable")
                n = left[0]
                calls.append({"role": role, "member": n, "seed": seed, "system": system, "deadline_s": deadline_s})
                a = (answers.get(n) or {}).get(seed)
                if a is None or isinstance(a, Exception):
                    raise a if isinstance(a, Exception) else P.ProviderError(f"{n}: no answer")
                return P.Reply(a if isinstance(a, str) else json.dumps(a), n, "heimdall")
        return R(), calls

    def run_it(self, answers, writer_family=None):
        r, calls = self.router(answers)
        ok, v = PK.coherence(r, TestCoherenceHookRatedOnce.PK_, {"xai"}, writer_family=writer_family,
                             hook=TestCoherenceHookRatedOnce.HOOK)
        return ok, v, calls

    def test_the_panel_passes_on_more_than_half_of_its_answers(self):
        G, B = self.GOOD, self.BAD
        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: G}, self.M[2]: {7: B, 8: B}})
        self.assertTrue(ok)                                            # 4 of 6 answers pass
        self.assertEqual(v["backend"], "panel:" + "+".join(sorted(self.M)))
        self.assertEqual(sorted((c["member"], c["seed"]) for c in calls), sorted((n, s) for n in self.M for s in (7, 8)))
        self.assertTrue(all(c["system"] == PK.PANEL_CONTRACT and c["deadline_s"] == 900 for c in calls))
        self.assertEqual((v["measured"], v["replayed"], v["bar"]), (True, False, "standard"))

    def test_half_is_not_a_pass_and_the_fields_are_lower_medians(self):
        G, B = self.GOOD, self.BAD
        ok, v, _ = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: B}, self.M[2]: {7: B, 8: B}})
        self.assertFalse(ok)                                           # 3 of 6: not more than half
        self.assertEqual((v["clips"]["clip_02"], v["vo_point"]), (3, 2))   # the redo and the re-line read these
        self.assertEqual(v["clips"]["hook"], 4)                        # the hook's own cached rating (ruling 61)

    def test_fewer_than_three_members_answering_is_no_verdict(self):
        G = self.GOOD
        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: G, 8: G}})
        self.assertFalse(ok)
        self.assertFalse(v["measured"])
        self.assertIn("no verdict", v["error"])
        self.assertEqual(sorted(c["seed"] for c in calls if c["member"] == self.M[2]), [7, 8, 107, 108])

    def test_the_writers_family_is_never_asked(self):
        G = self.GOOD
        ok, v, calls = self.run_it({n: {7: G, 8: G} for n in self.M}, writer_family={"qwen"})
        self.assertNotIn(self.M[0], {c["member"] for c in calls})
        self.assertFalse(ok)                                           # two members left: no verdict
        self.assertIn("no verdict", v["error"])

    def test_a_malformed_answer_is_asked_once_more_and_trailing_braces_are_read(self):
        G = self.GOOD
        ok, v, calls = self.run_it({self.M[0]: {7: G, 8: G}, self.M[1]: {7: "not json", 107: G, 8: G},
                                    self.M[2]: {7: json.dumps(G) + "}", 8: G}})
        self.assertTrue(ok)
        self.assertEqual(sorted(v["panel"]["answered"]), sorted(self.M))
        self.assertIn((self.M[1], 107), [(c["member"], c["seed"]) for c in calls])
        read = [(a["backend"], a["seed"]) for a in v["panel"]["answers"]]
        self.assertIn((self.M[2], 7), read)                            # the trailing brace dropped, the object read
        self.assertIn((self.M[1], 107), read)

    def test_a_router_without_the_panel_keeps_one_rater(self):
        self.assertIsNone(PK.coherence_panel_spec(Canned(coherence_verdict=[self.GOOD])))

    def test_the_configured_panel_is_the_measured_one(self):
        """The build's own router: the role's chain resolves to back-ends it holds, of the three families measured."""
        sys.path.insert(0, HERE)
        import proof_ledger as PLG
        r = PLG.build_router("heimdall_first", {}, os.devnull)
        spec = PK.coherence_panel_spec(r)
        self.assertEqual(sorted(r.backends[n].family for n in spec["members"]), ["gpt-oss", "minimax", "qwen"])
        self.assertEqual((spec["seeds"], spec["min_members"], spec["deadline_s"]), ([7, 8], 3, 900))


class TestCoherenceHookRatedOnce(unittest.TestCase):
    """RULING 61 (12:00): the coherence verdict after the takeaway does not rate the hook either: its cached own-job
    rating stands (hook_own); the clips after the hook and vo_point are judged as before."""
    PK_ = {"title": "Nobody bends the rules", "caption": "three clips",
           "vo": {"intro": None, "bridges": ["No ruler, just rules."], "bridges_after_clip": [2], "signoff": "S"},
           "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
                        {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
                        {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}
    HOOK = dict(pm("h", "A", 12.0), hook_rating={"scroll": 5, "alone": 4, "setup": 3, "backend": "xai:grok"})

    def reply(self, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
        return {"through_line": line, "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}

    def run_it(self, reply, hook=HOOK):
        r = Canned(coherence_verdict=[reply])
        prompts = []
        call = r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        ok, v = PK.coherence(r, self.PK_, {"heimdall"}, writer_family={"deepseek"}, hook=hook)
        return ok, v, r, prompts

    def test_the_hook_is_not_re_rated(self):
        ok, v, _, prompts = self.run_it(self.reply())
        self.assertTrue(ok)
        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
        self.assertNotIn(PK.HOOK_QUESTION, prompts[0])
        self.assertNotIn(PK.HOOK_QUESTION, PK.MEDLEY_PROMPT)
        self.assertIn("NOT", prompts[0])
        self.assertIn("For each clip AFTER the hook", prompts[0])
        self.assertIn('"clips": {"clip_01": 1, "clip_02": 1}', prompts[0])
        self.assertFalse(self.run_it(self.reply(clips={"clip_02": 3}))[0])      # clips and vo_point as before
        self.assertFalse(self.run_it(self.reply(vo=3))[0])
        self.assertFalse(self.run_it(self.reply(), hook=pm("h", "A", 12.0))[0])   # no cached rating: fail closed
        self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 5}))[0])
        G = "xai:grok"                                        # ruling 115: the hook's slot is its calibrated bar
        ok, v, _, _ = self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating={"scroll": 3, "alone": 4,
                                                                                     "setup": 3, "backend": G}))
        self.assertEqual((ok, v["clips"]["hook"]), (True, 3))
        for hr in ({"scroll": 5, "alone": 5, "setup": 2, "backend": G}, {"scroll": 5, "alone": 3, "setup": 5,
                                                                         "backend": G},
                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"}):
            self.assertFalse(self.run_it(self.reply(), hook=dict(self.HOOK, hook_rating=hr))[0], hr)

    def test_out_of_contract_is_not_measured(self):
        good = self.reply()
        for bad in (dict(good, hook={"scroll": 5, "alone": 5, "setup": 5}),
                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),
                    {k: x for k, x in good.items() if k != "vo_point"}, dict(good, vo_point=0)):
            ok, v, r, _ = self.run_it(bad)
            self.assertEqual((ok, v["measured"]), (False, False))
            self.assertEqual(r.rejected, ["fake:coherence_verdict"])


class TestWriteTakeaway(unittest.TestCase):
    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]

    def write(self, reply, join=None):
        r = Canned(angle_write=[reply])
        return PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {}, join), r

    def lines(self, bridge=None):
        return {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": bridge,
                "title": {"text": "No ruler.", "cites": ["h"]}, "caption": {"text": "three clips", "cites": []}}

    def test_no_bridge_unless_a_join_was_flagged(self):
        (rep, f), _ = self.write(self.lines())
        self.assertIsNone(f["bridge_after"])
        with self.assertRaises(ValueError):
            self.write(self.lines({"text": "Next, B.", "cites": ["x"], "why": "w"}))

    def test_a_bridge_at_the_flagged_join_needs_its_reason_and_may_be_declined(self):
        (rep, f), _ = self.write(self.lines({"text": "Next, B's show on keys.", "cites": ["x"], "why": "no referent"}),
                                 join=(1, "the next speaker's 'it' has no referent"))
        self.assertEqual(f["bridge_after"], 1)
        (rep, f), _ = self.write(self.lines(None), join=(1, "w"))
        self.assertIsNone(f["bridge_after"])                                       # declined: build re-lines
        for bad in ({"text": "Next.", "cites": ["x"]}, {"text": "Next.", "cites": ["x"], "why": " "},
                    {"text": "Next.", "cites": ["zz"], "why": "w"}):
            with self.assertRaises(ValueError):
                self.write(self.lines(bad), join=(1, "w"))

    def test_an_offered_bridge_leaves_a_budget_that_holds_for_any_bridge_it_allows(self):
        import re
        fits = none = 0
        for c10 in range(240, 520, 3):                     # audit 2030 C2 (qwen P1, grok P2), C3 (glm P0-2, qwen P2-2)
            c = c10 / 10
            segs = [dict(m, duration_s=c / 3) for m in self.SEGS]
            r = Canned(angle_write=[self.lines()])
            prompts = []
            call = r.call
            r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
            bb = PK.bridge_budget(c)
            if bb is None:                                  # no bridge length fits: refused before any model call
                with self.assertRaises(PK.NoBridgeFits):
                    PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
                self.assertEqual(prompts, [])
                none += 1
                continue
            fits += 1
            PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
            lo, hi = map(int, re.search(r'"takeaway": ONE sentence of (\d+)-(\d+) words', prompts[0]).groups())
            n = int(re.search(r"as short as it can be \(at most (\d+) words\)", prompts[0]).group(1))
            self.assertEqual((n, (lo, hi)), bb)
            self.assertTrue(PK.LY_BRIDGE_MIN_WORDS <= n <= PK.LY_BRIDGE_WORDS)
            for t in (lo, hi):                              # EVERY bridge the writer may write lands 60-70 s
                for bw in range(PK.LY_BRIDGE_MIN_WORDS, n + 1):
                    est = PK.runtime([{"duration_s": c}], [W(t), W(bw)])
                    self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, t, bw, est))
        self.assertGreater(fits, 40)                       # coverage: both branches exercised (50 fit, ruling 6 caps)
        self.assertGreater(none, 0)                         # at the top of the medley's seconds no bridge fits

    def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
        r = Canned(angle_write=[self.lines()])
        prompts = []
        call = r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
        lo, hi = PK.takeaway_budget(39.0)
        self.assertIn(f'"takeaway": ONE sentence of {lo}-{hi} words', prompts[0])          # RULING 162 (2)
        self.assertIn("it NEVER names a\n  channel, a show or a speaker", prompts[0])
        self.assertIn("HOUSE STYLE", prompts[0])                  # ruling 6 (22:40): the copy rules ride every write
        self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
        self.assertNotIn('"intro"', prompts[0])


class TestLyShape(unittest.TestCase):
    def test_a_clean_medley_passes(self):
        self.assertEqual(PK.ly_shape(medley_pk()), (True, []))
        self.assertTrue(PK.ly_shape(medley_pk(n=5))[0])

    def test_a_bridge_only_and_always_at_the_flagged_join_with_its_reason(self):
        self.assertTrue(PK.ly_shape(medley_pk(n=4, bridge="no referent", after=2, flagged=["clip_02 -> clip_03"]))[0])
        rec = {"why": "no referent", "text": "Next, B.", "confirmed_by": {"join": "hook -> clip_01"}}
        self.assertTrue(PK.ly_shape(medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {"bridge": rec})[0])
        must_fail = {
            "bridge at an unflagged join": medley_pk(n=4, bridge="w", after=1, flagged=["clip_02 -> clip_03"]),
            "bridge with nothing flagged": medley_pk(n=4, bridge="w", after=1),
            "flagged join left unbridged": medley_pk(flagged=["clip_01 -> clip_02"]),
            "bridge without its reason": medley_pk(n=4, bridge="", after=2, flagged=["clip_02 -> clip_03"]) | {
                "vo": medley_pk(n=4, bridge="w", after=2)["vo"]},
            "an intro with nothing flagged": medley_pk(intro="Here's the thing.") | {"bridge": {"why": "w"}},
            "two bridges": medley_pk(n=4, intro="Next.", bridge="w", after=2,
                                     flagged=["hook -> clip_01", "clip_02 -> clip_03"]),
            "verdict not measured": medley_pk(measured=False),
            "verdict missing": medley_pk() | {"medley": None},
            # the factory's R11 (integrator, branch ly-shape): the record binds the line and carries its confirmation
            "record text is not the line": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
                "bridge": dict(rec, text="Next, C.")},
            "confirmation missing": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
                "bridge": dict(rec, confirmed_by=None)},
            "confirmation a bool": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
                "bridge": dict(rec, confirmed_by=True)},
            "confirmation empty": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
                "bridge": dict(rec, confirmed_by={})},
            "a record with no bridge line": medley_pk() | {"bridge": rec},
        }
        for why, pk in must_fail.items():
            self.assertFalse(PK.ly_shape(pk)[0], why)

    def test_an_after_clip_that_is_not_a_clip_index_is_named(self):
        for bad in (0, 3, "1", None):                      # audit 2030 C4: the hook join is the intro, never after 0
            pk = medley_pk(n=4, bridge="w", after=2, flagged=["clip_02 -> clip_03"])
            pk["vo"]["bridges_after_clip"] = [bad, 3]
            ok, why = PK.ly_shape(pk)
            self.assertFalse(ok)
            self.assertTrue(any(w.startswith(f"after_clip [{bad!r}]") for w in why), why)

    def test_the_takeaway_is_the_line_after_the_last_clip(self):
        pk = medley_pk()
        pk["vo"] = dict(pk["vo"], bridges_after_clip=[1])
        self.assertFalse(PK.ly_shape(pk)[0])
        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
        self.assertFalse(PK.ly_shape(pk)[0])

    def test_a_no_voice_medley_needs_its_record_and_no_vo_line(self):
        pk = medley_pk()
        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
        self.assertFalse(PK.ly_shape(pk)[0])                          # no takeaway and no record: L-y 1 fails
        self.assertTrue(PK.ly_shape(dict(pk, no_voice={"why": "the takeaway failed twice"}, bridge=None))[0])
        self.assertFalse(PK.ly_shape(dict(pk, no_voice={"why": " "}, bridge=None))[0])      # a record without a why
        self.assertFalse(PK.ly_shape(dict(medley_pk(), no_voice={"why": "x"}))[0])        # a VO line with the record
        flagged = dict(pk, no_voice={"why": "x"}, bridge=None, medley={"measured": True, "flagged": ["hook -> clip_01"]})
        self.assertFalse(PK.ly_shape(flagged)[0])                     # a join a viewer cannot follow, left unbridged

    def test_three_to_five_segments_and_one_clip_per_channel(self):
        self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
        self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
        self.assertFalse(PK.ly_shape(medley_pk(chans="ABA"))[0])
        self.assertTrue(PK.ly_shape(medley_pk(chans="ABA", supply="A gives two clips (L-y 4)"))[0])

    def test_a_bridge_over_the_word_cap_fails(self):
        pk = medley_pk(n=4, bridge="w", after=2, flagged=["clip_02 -> clip_03"])
        pk["vo"]["bridges"][0] = W(BRIDGE_WORD_CAP + 1)
        self.assertFalse(PK.ly_shape(pk)[0])


def ctx():
    return E.Context(NOW, REG)


class TestMedleyPackageAndPin(unittest.TestCase):
    def build(self, bridge=None, k=None, n=3, text="No ruler, just rules nobody gets to bend."):
        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
                                          pm("z", "D", 9.0))}
        order = ["h", "x", "y", "z"][:n]
        fields = {"takeaway": {"text": text, "cites": []}, "bridge": bridge, "bridge_after": k,
                  "title": {"text": "No ruler.", "cites": []}, "caption": {"text": "three clips", "cites": []}}
        return PK.assemble_medley(order, by, fields, ctx(), "medley (L-y)")

    def gates(self, pk, **over):
        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
        g["stand_alone"] = dict(g["stand_alone"], screen=E.BTC_SCREEN.pattern)      # the screen it judged with
        if "takeaway_value" in g:                       # ruling 91: the row names the takeaway it judged
            g["takeaway_value"] = dict(g["takeaway_value"], text=package_pin.takeaway_line(pk))
        g.update(over)
        return g

    def test_no_intro_and_one_takeaway_after_the_last_clip(self):
        pk = self.build()
        self.assertIsNone(pk["vo"]["intro"])
        self.assertEqual((pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]),
                         (["No ruler, just rules nobody gets to bend."], [2]))
        self.assertEqual([x["slot"] for x in pk["lines"]], ["takeaway", "title", "caption"])
        self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
        self.assertEqual(PK.r4(pk)[0], True)

    def test_each_segment_states_whether_its_clip_is_time_sensitive_and_when_it_was_published(self):
        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0, risk=("time_sensitive",)),
                                          pm("y", "C", 13.0))}
        fields = {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None, "bridge_after": None,
                  "title": {"text": "No ruler", "cites": []}, "caption": {"text": "three clips", "cites": []}}
        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
        self.assertEqual([s["time_sensitive"] for s in pk["segments"]], [False, True, False])
        self.assertEqual({s["source_published_at"] for s in pk["segments"]}, {PK.utc_z(by["h"]["published_at"])})
        self.assertRegex(pk["segments"][0]["source_published_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
        pk = self.build(bridge=b, k=1, n=4)
        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 3])
        self.assertEqual([x["slot"] for x in pk["lines"]][:2], ["bridge_1", "takeaway"])
        self.assertEqual(pk["bridge"]["join"], "clip_01 -> clip_02")
        pk0 = self.build(bridge=b, k=0)
        self.assertEqual(pk0["vo"]["intro"], "Next, on keys.")
        self.assertEqual(pk0["vo"]["bridges_after_clip"], [2])
        with self.assertRaises(ValueError):
            self.build(bridge=b, k=2)                     # after the last clip is the takeaway's place

    def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
        pk = self.build()
        self.assertEqual(package_pin.required_gates(pk)[-7:], ("medley", "ly_shape", "house_style", "hook_onset",
                                                               "stand_alone", "visual",
                                                               "takeaway_value"))   # ruling 91: it has a takeaway
        pk["gates"] = self.gates(pk)
        pin = package_pin.to_pin(spk(pk), "test")
        self.assertEqual(pin["label"], "bitcoin")     # the render's STAND_ALONE subject rests on it (audit 0310 C2)
        self.assertNotIn("stand_alone", package_pin.required_gates({"shape": "story"}))   # medleys only (glm P2-1)
        mp = pin["moments_package"]
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
        self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
        self.assertEqual(mp["shape"], "medley")
        for missing in ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone", "takeaway_value"):
            g = self.gates(pk)
            g.pop(missing)
            with self.assertRaises(package_pin.PinRefused):
                package_pin.to_pin(spk(dict(pk, gates=g)), "test")
        with self.assertRaises(package_pin.PinRefused):
            package_pin.to_pin(spk(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False}))), "test")

    def test_the_gated_takeaway_must_be_the_spoken_one(self):
        pk = self.build()
        pk["gates"] = self.gates(pk)
        pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
        with self.assertRaises(package_pin.PinRefused) as cm:
            package_pin.to_pin(spk(pk), "test")
        self.assertIn("bridges", str(cm.exception))

    def test_the_old_shape_keeps_its_slots(self):
        pk = {"vo": {"intro": "I", "bridges": ["B", "T"], "bridges_after_clip": [1, 2]}, "segments": [{}, {}, {}]}
        self.assertEqual(package_pin.bridge_slots(pk), ["bridge_1", "bridge_2"])
        self.assertEqual(package_pin.bridge_slots(dict(pk, shape="medley")), ["bridge_1", "takeaway"])


    def test_a_takeaway_over_30_words_fails_r4_and_a_hook_join_bridge_pins(self):
        pk = self.build(text=" ".join(["rules"] * (PK.MOMENTS_TAKEAWAY_WORD_CAP + 1)))
        pk["medley"] = {"measured": True, "flagged": []}
        cheap = PK.cheap_checks(pk, {}, [], NOW)[0]
        self.assertTrue(any(v["rule"] == "R4" and "takeaway 1 31 words (max 30)" in v["detail"] for v in cheap), cheap)
        b = {"text": "Next, on keys.", "cites": ["x"], "why": "no referent"}
        pk0 = self.build(bridge=b, k=0)                   # audit 2030 C1 (grok P2-2): the intro slot pins as intro
        pk0["gates"] = self.gates(pk0)
        mp = package_pin.to_pin(spk(pk0), "test")["moments_package"]
        self.assertEqual(mp["edl_vo"], {"intro": "Next, on keys.",
                                        "bridges": [{"text": pk0["vo"]["bridges"][0], "after_clip": 2}]})
        self.assertEqual(mp["vo_jobs"], {"intro": "connection", "takeaway": "takeaway"})



NV_FLAG_OK = lambda g: (all(r["status"] == "PASS" for k, r in g.items() if k != "no_closing_line") and   # RULING 162
                        g["no_closing_line"]["status"] == "FLAGGED" and g["no_closing_line"]["flags"] == [  # (2): the
                            PK.NO_LINE_FLAG])                     # no-voice shape carries exactly its one flag


class Rig:
    """build() with every model and the network stubbed: the LOOP CONTROL under test (audit 2030 C1, glm P2-6).
    medleys: the clips-alone verdicts in call order, each (ok, flagged, ratings, through_line); writes: the writer's
    bridges in call order (None = no bridge / declined)."""

    LINE = "Nobody gets to bend these rules, and that is exactly why they hold when it counts."
    A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
            "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}

    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
                 spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None, truths=None,
                 trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
                 cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
                 real_value=False, caption=None, coherences=None, joins=None):
        import providers as P
        self.joins, self.join_calls = joins, []           # RULING 117: {(a, b): followable}; None = no table (as before)
        self.coherences = list(coherences or [])         # RULING 116: (ok, every clip's rating, the VO point) in order
        self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
        self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
        self.caption = caption or "nobody bends these rules"   # 07:30 (C): a caption that fails its own gates
        self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
        self.takeaways, self.spend = list(takeaways or []), spend
        self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
        self.truths = dict(truths or {})                  # {moment id: the second pass's record} (default: clean)
        self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
        self.verdicts = verdicts                           # ruling 56: {pid: verdict} in the integrator's file shape
        self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
        self.medley_calls, self.write_calls, self.prompts = [], [], []
        self.candidate, self.seeds = candidate, []          # ruling 66: build from a candidate; the seeds asked with
        self.registered = registered                        # ruling 66: the registry's line-ups (candidates.registered)
        self.lock_check = lock_check                        # rulings 68 / 72: the render's lock (lock_precheck.check)
        self.visuals, self.visual_calls = dict(visuals or {}), []   # ruling 70: {moment id: record} (default: clean)
        self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
        self.screens, self.events, self.a_seen, self.screen_deadlines = [], [], [], []
        self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
        self.paid_seen, self.write_texts = [], []          # RULING 163 (2)(b): what the verdicts and the writer read
        many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}] + ([follow_up] if follow_up else [])
                             + list(lines or []))                  # ruling 65: the replies for a line written alone
        self.fids, self.cached = list(fids or []), cached     # ruling 65: the paid fidelity results, in order
        self.angle_hooks = {a[0] for a in many}           # ruling 59: by default only the canned angles' hooks pass
        call = self.router.call

        def rcall(role, prompt, *a, **k):
            self.prompts.append((role, prompt))
            self.events.append(role)
            r = call(role, prompt, *a, **k)
            if role == "angle_write" and angle_from:              # the angle from a named back-end (ORDER 06:22)
                r = P.Reply(r.text, angle_from[0], angle_from[1], family=angle_from[2])
            return r
        self.router.call = rcall
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        self.router.backends = {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek"),
                                "heimdall:qwen": B("heimdall", "qwen"), "openai:gpt": B("openai", "gpt")}
        self.router.chain = lambda role: ["heimdall:deepseek", "heimdall:qwen", "xai:grok"]
        self.write_avoid = []

    def prescreen(self, router, ms, sources, ctx_, writer_vendor, writer_family=None, n=PK.PRESCREEN_N,
                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None, deadline_s=None, kind=None,
                  failover=None, plan_only=False):
        if plan_only:                                      # ruling 101's plan: the moments new to the first screen
            return [m for m in ms if m["moment_id"] in getattr(self, "plan_new", ())]
        self.screen_deadlines.append(deadline_s)           # ruling 82: which calls are bounded
        """Step A as the real prescreen calls it: on the first back-end off the given vendors and families
        (context_verdict: xai, then heimdall; a third vendor only for the rig); per (vendor, moment) failures."""
        av, af = self.P._as_set(writer_vendor), self.P._as_set(writer_family)
        name = next((x for x in ("xai:grok", "heimdall:deepseek", "openai:gpt")
                     if self.router.backends[x].vendor not in av and self.router.backends[x].family not in af), None)
        self.screens.append((name, [m["moment_id"] for m in ms]))
        self.events.append(f"step_a:{name}")
        got, fails = {}, {}
        for m in ms[:n]:
            mid = m["moment_id"]
            v = self.router.backends[name].vendor if name else None
            if name is None or (v, mid) in self.unavailable:
                fails[mid] = [PK.held_why(self.P.ProviderError("context_verdict: every back-end unavailable"))]
                continue
            got[mid] = dict(self.A_OK, backend=name)
            fails[mid] = list(self.a_fail.get((v, mid), []))
        return got, fails, set(), set()

    def rate_hooks(self, router, ms, ctx_, writer_vendor, writer_family=None, cache=None, seed=7):
        """Ruling 59 (a) as the real hook_ratings answers: every given moment rated (self.hooks, default 5 / 5 / 5),
        the rating derived as the lowest part; hook_err: the call failed and nothing is rated."""
        self.hook_calls.append([m["moment_id"] for m in ms])
        self.events.append("hook_ratings")
        if self.hook_err:
            return {}, self.hook_err
        out = {}
        for m in ms:
            mid0 = m["moment_id"].split(PK.HEARD)[0]                   # RULING 163 (2)(b): its corrected words, rated
            sc, al, se = self.hooks.get(mid0, (5, 5, 5) if mid0 in self.angle_hooks else (3, 3, 3))
            out[m["moment_id"]] = {"scroll": sc, "alone": al, "setup": se, "rating": min(sc, al),   # ruling 61
                                   "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
        return out, None

    def join_table(self, router, ms, ctx_, wv, wf=None, cache=None, seed=7):
        """Ruling 117 as the real join_table answers: every ordered pair of `ms` (the hook never B) the rig knows
        (self.joins), followable or not; a pair it does not know is not answered. None: no table at all."""
        self.join_calls.append([m["moment_id"] for m in ms])
        if self.joins is None:
            return {}, None
        out = {}
        for a in ms:
            for b in ms[1:]:
                if a is not b and (a["moment_id"], b["moment_id"]) in self.joins:
                    out[(a["moment_id"], b["moment_id"])] = {"followable": self.joins[(a["moment_id"], b["moment_id"])],
                                                             "why": "w", "backend": "xai:grok", "cached": False}
        return out, None

    def coherence(self, router, pk, *a, **k):
        """As the real coherence() answers: the clips after the hook and the VO point (self.coherences, default all 5
        and a pass), the hook's slot its own rating, and the line-up bar it was judged on (ruling 116)."""
        own = PK.hook_own(k.get("hook"))
        ok, clip, vo = self.coherences.pop(0) if self.coherences else (True, 5, 5)
        fl, which, csha = PK.lineup_floors("coherence", "xai:grok")
        segs = pk["segments"]
        return ok, {"through_line": "Nobody gets to bend the rules.",
                    "clips": dict({segs[0]["label"]: (own or {}).get("rating")}, **{sg["label"]: clip for sg in segs[1:]}),
                    "vo_point": vo, "backend": "xai:grok", "measured": True, "replayed": False,
                    "hook_own": own or {"rating": None}, "floors": fl, "bar": which, "calibration_sha256": csha}

    def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
        """As the real medley() answers: the verdict, its flagged joins, the hook's own-job record (ruling 115) and
        the line-up bar it was judged on (ruling 116: the rigs' rater, so the calibrated floors)."""
        self.medley_calls.append([m["moment_id"] for m in segs])
        self.seeds.append(("medley", seed))
        base = [m["moment_id"].split(PK.HEARD)[0] for m in segs]       # RULING 163 (2)(b): a line-up judged again on
        if any(PK.HEARD in m["moment_id"] for m in segs) and getattr(self, "last_medley", (None,))[0] == base:
            ok, flagged, ratings, line = self.last_medley[1]          # its corrected words: the same clips' verdict
        else:
            ok, flagged, ratings, line = self.medleys.pop(0)
            self.last_medley = (base, (ok, flagged, ratings, line))
        labs = PK.labels(len(segs))
        v = verdict(labs, flagged, ratings, line)
        own = PK.hook_own(segs[0])
        if "hook" not in (ratings or {}):                  # the hook's slot holds its own rating, as medley() writes it
            v["clips"]["hook"] = (own or {}).get("rating")
        fl, which, csha = PK.lineup_floors("clips_alone", "xai:grok")
        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False,
                        cached=self.cached, hook_own=own or {"rating": None},
                        bar=which, floors=fl, calibration_sha256=csha)

    def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=(),
              avoid_model=None):
        if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
            raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
        self.write_calls.append(([m["moment_id"] for m in segs], join))
        self.write_texts.append([m["text"] for m in segs])
        self.seeds.append(("write", seed))
        self.write_avoid.append(avoid_vendor)
        self.write_avoid_model = getattr(self, "write_avoid_model", []) + [avoid_model]   # RULING 162 (2)
        self.a_seen.append({m["moment_id"]: a_by[m["moment_id"]]["backend"] for m in segs})
        b = self.writes.pop(0)
        fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
                  "bridge_after": join[0] if join is not None and b is not None else None,
                  "title": {"text": "Nobody bends the rules", "cites": []},
                  "caption": {"text": self.caption, "cites": []},
                  "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
        return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields

    OUT_EDGE_OK = {"complete": True, "why": "the thought ends", "backend": "heimdall:qwen/qwen3.8-27b@low",
                   "measured": True, "version": "owner_rules 1 (ruling 162, 2026-11-24)", "sha256": "e" * 64}

    def out_edges(self, router, ms, sources, ctx_, cache_path=None, log=print, delivered=(), optout=frozenset(),
                  seg_max=None, admit=None):
        """RULING 162 (1) as package.out_edges answers: every moment ends a thought (OUT_EDGE_OK), unless
        self.out_edge_refused / self.out_edge_unverified name it (out of the pool, recorded). ITEM 3: the moments it
        is asked about are recorded (out_edge_asked); self.out_edge_extend {parent: extension id} makes the extension
        (the parent's span under a new id) and puts it through the build's admit() as the real pool does, recorded
        in self.admitted [(id, ok, why)]."""
        self.__dict__.setdefault("out_edge_asked", []).append([m["moment_id"] for m in ms])
        ext, admitted = getattr(self, "out_edge_extend", {}), self.__dict__.setdefault("admitted", [])
        if ext:
            got, rec = [], {"ruling": "162 (1)", "version": self.OUT_EDGE_OK["version"],
                            "sha256": self.OUT_EDGE_OK["sha256"], "asked": len(ms), "complete": [], "extended": {},
                            "refused": {}, "unverified": {}}
            for m in ms:
                if m["moment_id"] not in ext:
                    got.append(dict(m, out_edge=dict(self.OUT_EDGE_OK)))
                    rec["complete"].append(m["moment_id"])
                    continue
                v = dict(m, moment_id=ext[m["moment_id"]], derived_from={"ruling": "162 (1)", "from": m["moment_id"]})
                ok, why = admit(v) if admit is not None else (False, "no admit")
                admitted.append((v["moment_id"], ok, why))
                if ok:
                    got.append(dict(v, out_edge=dict(self.OUT_EDGE_OK)))
                    rec["extended"][m["moment_id"]] = v["moment_id"]
                else:
                    rec["refused"][m["moment_id"]] = f"its extension {v['moment_id']} fails before its question: {why}"
            return got, rec
        bad, un = set(getattr(self, "out_edge_refused", ())), set(getattr(self, "out_edge_unverified", ()))
        rec = {"ruling": "162 (1)", "version": self.OUT_EDGE_OK["version"], "sha256": self.OUT_EDGE_OK["sha256"],
               "asked": len(ms), "complete": [m["moment_id"] for m in ms if m["moment_id"] not in bad | un],
               "extended": {}, "refused": {mid: "runs on" for mid in bad}, "unverified": {mid: "no answer" for mid in un}}
        return [dict(m, out_edge=dict(self.OUT_EDGE_OK)) for m in ms if m["moment_id"] not in bad | un], rec

    def value(self, router, segs, ctx_, line, wv, wf, seed=7):
        """RULING 91 (medley half): package.takeaway_value as the build calls it. A clear yes on all four unless
        self.values gives the next answers ({"adds": "no", ...}; {"measured": False} = no verdict)."""
        self.value_calls.append({"line": line, "segs": [m["moment_id"] for m in segs], "wv": set(wv), "wf": set(wf),
                                 "texts": [m["text"] for m in segs]})
        got = self.values.pop(0) if self.values else {}
        base = {"text": line, "words": len(line.split()), "cap": PK.LY_TAKEAWAY_MAX_WORDS}
        if got.get("measured") is False:
            return dict(base, measured=False, ok=False, why="ProviderError: no back-end", backend=None, replayed=False)
        ans = {k: got.get(k, "yes") for k in ("adds", "no_restate", "missed", "short")}
        return dict(base, **ans, why=got.get("why", "a point the clips do not make"), measured=True,
                    backend="xai:grok", replayed=False,
                    ok=all(x == "yes" for x in ans.values()) and base["words"] <= PK.LY_TAKEAWAY_MAX_WORDS)

    def visual(self, router, m, work_dir, cache, seed=7, log=print):
        """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
        self.visual_calls.append(m["moment_id"])
        base = {"version": VP.VERSION, "measured": True, "flags": [],
                "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
                                 "finding": "no third person"},
                "on_screen_text": [], "lower_third": {"name": None, "text": None}, "burned_in": [],   # ruling 93
                "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
                "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "usd_basis": "reported",
                "cached": False}
        return dict(base, **self.visuals.get(m["moment_id"], {}))

    def onset(self, m, *a, **k):
        """hook_onset.measure's record: the hook lead, and for a trimmed moment its trimmed cut ("trim")."""
        r = ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"} if m["moment_id"] in self.no_hook
             else {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"})
        if m.get("trimmed_leading"):
            ok = m["moment_id"] not in self.trim_fail
            r["trim"] = {"pass": ok, "measured": True, "why": "ok" if ok else "the trimmed word 'But' cannot be cut "
                                                                              "cleanly: no measured pause (co-articulated)"}
            r["pass"] = r["pass"] and ok
        return r

    def run(self):
        fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
               "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
               "verdict": {"ok": True, "violations": [], "classes": {}}}
        cx = {"ok": True, "violations": [], "measured": True, "replayed": False, "backends": {"B": "xai", "C": "xai"}}
        stubs = {
            "_writers": lambda router: ({"heimdall"}, {"deepseek"}),
            "prescreen": self.prescreen,
            "current_levels": lambda *a, **k: [],
            "medley": self.medley, "write_takeaway": self.write,
            "paid_gates": lambda router, pk, *a, **k: (self.paid_seen.append(   # RULING 163 (2)(b): the texts the
                [dict(sg) for sg in pk["segments"]]) or (self.fids.pop(0) if self.fids else fid), cx),   # verdicts read
            "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
                                                         "keep", "measured": True, "replayed": False,
                                                         "backend": "xai:grok",     # RULING 146 (3): as the real one
                                                         **({"ad_before": m["ad_before"]} if m.get("ad_before") else {})},
            "truth_for": lambda router, m, *a, **k: dict(self.truths[m["moment_id"]]) if m["moment_id"] in self.truths else {"ok": True, "replayed": False, "model": "scribe_v1",
                                                     "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
            "hook_onset_for": self.onset,
            "hook_ratings": self.rate_hooks,
            "join_table": self.join_table,
            "takeaway_value": self.value,                  # ruling 91 (medley half)
            "coherence": self.coherence,
            "out_edges": self.out_edges,                   # RULING 162 (1): every OUT edge ends a thought by default
        }
        if self.real_value:                                # ruling 91: the real verdict, on the fake router
            del stubs["takeaway_value"]
        kw, path = ({"candidate": self.candidate} if self.candidate is not None else {}), None
        if self.registered is not None:
            kw["registered"] = self.registered
        if self.lock_check is not None:
            kw["lock_check"] = self.lock_check
        kw.update(getattr(self, "build_kw", None) or {})  # RULING 137: never_empty / flagged_today, when a test sets
        if getattr(self, "stories_path", None):            # RULING 118 (4): the stories file (default: none read)
            kw["stories_path"] = self.stories_path
        if self.verdicts is not None:                      # ruling 56: the integrator's file, read by the real reader
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".json")
            with os.fdopen(fd, "w") as f:
                json.dump({"rated_at": "2026-11-13T15:35:10Z", "build": "test", "scorer": {
                    "model": "gemma3:27b", "kind": "moments", "threshold": 3.5, "event": None,
                    "scorer_sha": "s" * 64},
                    "verdicts": self.verdicts}, f)
            kw["scorer_verdicts_path"] = path
            stubs["render_scorer_sha"] = lambda *a, **k: "s" * 64       # the render's scorer code, as it is now
        saved = {k: getattr(PK, k) for k in stubs}
        import visual_pin as VP
        saved_vp, VP.visual_for = VP.visual_for, self.visual       # ruling 70
        try:
            for k, v in stubs.items():
                setattr(PK, k, v)
            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
                            spend=self.spend, **kw)
        finally:
            VP.visual_for = saved_vp
            for k, v in saved.items():
                setattr(PK, k, v)
            if path:
                os.remove(path)


class TestBuildLoop(unittest.TestCase):
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]

    def test_nothing_is_written_for_clips_that_fail_alone(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], None, "none")], [])
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual(rig.write_calls, [])
        self.assertIn("no through-line", out["tried"][0]["why"])
        self.assertTrue(out["why_none"].startswith("no angle gave a package: angle 1: the clips alone have no "
                                                   "through-line"), out["why_none"])     # never None (03:39 build)

    def test_a_weak_clip_alone_is_dropped_and_the_line_up_re_picked(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])           # written only after the clips pass
        self.assertIsNotNone(out["package"])
        self.assertIsNone(out["package"]["bridge"])

    def test_a_declined_bridge_drops_the_clip_after_the_flagged_join(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE),
                                                  (True, [], None, Rig.LINE)], [None, None])
        out = rig.run()
        self.assertEqual(rig.write_calls[0], (["h", "x", "y"], (1, "the next speaker's 'it' has no referent")))
        self.assertIn("followable without a bridge", out["tried"][0]["why"])
        self.assertEqual(rig.medley_calls[1], ["h", "x", "z"])                  # y, after the flagged join, dropped
        pk = out["package"]
        self.assertIsNone(pk["bridge"])
        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["ly_shape"]["status"]), ("PASS", "PASS"))

    def test_a_flagged_join_no_bridge_can_fill_drops_the_line_up_before_any_write(self):
        long_ms = [pm("h", "A", 17.0), pm("x", "B", 17.0), pm("y", "C", 17.0), pm("z", "D", 13.0), pm("w", "E", 13.0)]
        rig = Rig(long_ms, ["h", "x", "y", "z", "w"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE),
                                                       (True, [], None, Rig.LINE)], [None])
        self.assertIsNone(PK.bridge_budget(51.0))           # 51 s of clips: a bridge leaves no takeaway inside 70 s
        out = rig.run()
        self.assertIn("no bridge of 3-12 words", out["tried"][0]["why"])
        self.assertEqual(rig.write_calls[0][0], [m for m in rig.medley_calls[1]])   # the first write is the 2nd line-up
        self.assertNotIn("y", rig.medley_calls[1])           # the clip after the flagged join was dropped

    def test_a_given_bridge_sits_at_the_flagged_join_with_its_reason(self):
        b = {"text": "Next, a show on keys.", "cites": ["y"], "why": "the next clip's 'it' has no referent"}
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b])
        pk = rig.run()["package"]
        self.assertEqual((pk["bridge"]["join"], pk["bridge"]["why"]), ("clip_01 -> clip_02", b["why"]))
        self.assertEqual(pk["bridge"]["confirmed_by"]["join"], "clip_01 -> clip_02")
        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 2])
        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
        package_pin.to_pin(spk(pk), "test")                    # every required row exactly PASS: the pin is allowed

    def test_a_clip_the_second_recogniser_cannot_cut_is_never_offered_to_the_angles(self):
        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None], uncuttable={"y"})
        out = rig.run()
        angle_prompt = next(p for r, p in rig.prompts if r == "angle_write")
        self.assertNotIn("id=y ", angle_prompt)          # measured once per moment, before the angles (L-y 3)
        self.assertIn("id=x ", angle_prompt)
        self.assertEqual(out["prescreen"]["second_pass"]["y"], "not cuttable at an edge (ruling C / 7)")
        self.assertEqual(out["prescreen"]["cuttable"], 3)
        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
        pk = out["package"]
        self.assertEqual(pk["gates"]["cuttable"]["status"], "PASS")
        package_pin.to_pin(spk(pk), "test")                    # build() returns only a package its pin accepts

    def test_an_excluded_moment_stays_out_of_every_later_angle(self):
        ms = self.MS + [pm("w", "E", 14.0)]
        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "z", "w"]], [(True, [], None, Rig.LINE)] * 2, [None, None],
                  excluded={"x"})
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "z", "w"]])   # angle 2 never offers x again
        self.assertIn("'x': 'exclusion'", out["tried"][0]["why"])
        self.assertEqual(len(rig.write_calls), 2)          # the paid verdicts never ran on the doomed line-up
        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "z", "w"])

    def test_no_voice_when_the_takeaway_fails_its_one_write_on_clips_that_hold_alone(self):
        """Ruling 3 (22:40), with ITEM 2 (orchestrator 09:35 ET Nov 24: "One write ... no retry loop"): the takeaway
        failing its gates in its ONE write means no VO line: clips back to back and the sign-off, NOT dropped; one clip
        added to land 60-70 s. The second takeaway offered is never asked for."""
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], takeaways=bad)
        out = rig.run()
        pk = out["package"]
        self.assertIsNotNone(pk)
        self.assertEqual(len(rig.write_calls), 1)                  # ITEM 2: its one write failed (takeaway-opener)
        self.assertEqual(rig.takeaways, bad[1:])                   # the second takeaway offered: never asked for
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])   # 39 s + z: 52 s
        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])   # the new line-up judged on the clips alone
        self.assertEqual((pk["vo"]["intro"], pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]), (None, [], []))
        self.assertEqual(pk["no_voice"]["added_clip"], "z")
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
        self.assertAlmostEqual(pk["runtime_s_estimate"], 52.0 + PK.FINAL_TAIL_S, places=2)
        self.assertTrue(NV_FLAG_OK(pk["gates"]), pk["gates"])                 # RULING 162 (2): one flag, no line
        self.assertIn("no VO line", pk["checks"]["coherence"]["note"])
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})

    def test_no_voice_never_ships_a_join_the_blind_check_flagged(self):
        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        rig = Rig(self.MS, ["h", "x", "y"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b, b], takeaways=bad)
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertNotIn("no_voice", out["tried"][0])           # not tried: the clips need a bridge to be followed

    def test_every_write_stays_on_the_angles_vendor(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.write_avoid, [{"heimdall", "xai"}])  # the angle came from vendor "fake": all others out
        self.assertEqual(out["angle_backend"], "fake:angle_write")
        self.assertEqual(out["angle_tried"], [])

    def test_the_search_budget_ends_the_build_and_the_package_budget_ends_only_its_line_up(self):
        """Ruling 41 (04:58): a build may spend $3.00 reported searching (a $10.00 estimate ceiling); ruling 5's $1.50 /
        15 min is per PACKAGE delivered, counted from its own line-up's clips-alone verdict."""
        for spent, why in (((0.10, 3.01), "reported"), ((10.01, 0.20), "estimate ceiling")):
            reads = [(0.0, 0.0), (0.0, 0.0)]                  # the baseline, then the check before line-up 1
            calls = iter(reads + [spent] * 80)                # ... then over the search budget from the next check on
            rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(False, [], None, "none")] * 2, [],
                      spend=lambda: next(calls))
            out = rig.run()
            self.assertIn("ruling 41", out["why_none"], why)
            self.assertEqual(len(rig.medley_calls), 1, why)          # line-up 1 ran; nothing after the stop
            self.assertEqual(out["budget_stop"]["angles_tried"], 1, why)
            self.assertEqual(out["search"]["lineups"], 1, why)
        over = iter([(0.0, 0.0)] + [(11.0, 11.0)] * 80)             # over the search budget from the very first check
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], spend=lambda: next(over))
        out = rig.run()
        self.assertEqual((rig.medley_calls, rig.write_calls), ([], []))   # no clips-alone call, no write paid
        self.assertIsNone(out["package"])
        rig = Rig(self.MS, [["h", "x", "y"], ["h", "x", "z"]], [(True, [], None, Rig.LINE)] * 2, [None, None])
        rig.spend = lambda: (0.0, 1.6) if rig.medley_calls else (0.0, 0.0)  # line-up 1's package: $1.60 > $1.50
        out = rig.run()
        self.assertIn("per package delivered", out["tried"][0]["why"])      # only that line-up stopped
        self.assertEqual(len(rig.write_calls), 1)                          # line-up 2 (its own $0.00) wrote
        self.assertIsNotNone(out["package"])                               # the search went on: $1.60 < $3.00
        self.assertEqual((out["search"]["lineups"], out["search"]["usd_reported"]), (2, 1.6))

    def test_a_hook_without_80_ms_of_genuine_quiet_never_opens_and_none_means_no_hook(self):
        """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
        only when its hook onset was measured and passed. RULING 59: it is never rated as a hook nor one of THE HOOKS
        the writer is given; with no moment that can open, the build stops before any line-up."""
        rig = Rig(self.MS, ["x", "h", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h"})
        out = rig.run()
        self.assertNotIn("h", rig.hook_calls[0])                          # never asked as a hook
        p = next(p for r, p in rig.prompts if r == "angle_write")
        self.assertIn("id=h | A | 12.0 s | cannot open (never the hook) | ", p)
        self.assertNotIn("id=h | rated", p)                               # not one of THE HOOKS
        pk = out["package"]
        self.assertEqual(pk["segments"][0]["moment_id"], "x")
        self.assertEqual(pk["gates"]["hook_onset"]["status"], "PASS")
        self.assertEqual(pk["gates"]["hook_onset"]["lead_ms"], 200)
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h", "x", "y", "z"})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual((rig.medley_calls, rig.hook_calls), ([], []))   # nothing paid for: no hook, no line-up
        self.assertIn("no hook in the pool", out["why_none"])
        self.assertIn("no cleared, cuttable moment can open", out["why_none"])

    def test_the_supply_exception_is_recorded(self):
        ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
        rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
        pk = rig.run()["package"]
        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "e"])
        self.assertIn("gives two clips, from two videos (L-y 4)", pk["supply_exception"])
        self.assertEqual(pk["gates"]["ly_shape"]["status"], "PASS")


class TestStandAloneAtThePinStage(unittest.TestCase):
    """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) at the pin stage, after the
    integrator held pin d2657bbe on it (03:00 ET Nov 13): no clip scorer here (it is a local model on GPU0), so a clip
    opening on a conjunction or reply fragment fails closed, and no line-up the render would hold is sealed."""

    HOOK = ("Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin "
            "wins, open source wins.")
    BUT1 = "But we have very rarely in Bitcoin's history seen six negative weeks back to back. I think that was six."
    BUT2 = ("But then if someone doesn't understand Bitcoin and you drop 25 % of their portfolio in Bitcoin and Bitcoin "
            "goes down 50%. You get fired and they sell their Bitcoin.")

    def test_it_gives_the_renders_verdicts_on_the_held_pin_d2657bbe(self):
        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": self.BUT1}, {"text": self.BUT2}])
        self.assertFalse(r["ok"])
        self.assertEqual([(x["segment"], x["pass"]) for x in r["rows"]],     # the render's run_log.txt lines 47-49
                         [("hook", True), ("clip_01", False), ("clip_02", False)])
        self.assertIn("clip opens on 'but'", r["rows"][1]["opener"]["why"])
        self.assertEqual(r["subject"], ["bitcoin", "btc"])

    def test_a_moment_opening_on_a_conjunction_or_reply_fragment_has_no_role(self):
        for t in (self.BUT1, "And Bitcoin is money.", "Yeah, Bitcoin is money.", "Well, Bitcoin is money."):
            self.assertIn("STAND_ALONE", PK.no_role_on_screen({"text": t}) or "", t)
        for t in ("I think Bitcoin is money.", "Bitcoin is money.", "It is Bitcoin."):   # a pronoun opens a clip
            self.assertIsNone(PK.no_role_on_screen({"text": t}), t)

    def test_no_line_up_holds_a_clip_the_render_would_hold(self):
        by = {m["moment_id"]: m for m in (dict(pm("h", "A", 12.0), text=self.HOOK), dict(pm("b", "B", 14.0), text=self.BUT1),
                                          dict(pm("x", "C", 13.0), text="Bitcoin x."),
                                          dict(pm("y", "D", 13.0), text="Bitcoin y."))}
        a = angle(["h", "b", "x", "y"], "h")
        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by)], ["h", "b", "x"])     # the old pick
        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by, need_stand_alone=True)], ["h", "x", "y"])
        no_subject = dict(by, y=dict(by["y"], text="Gold is money."), x=dict(by["x"], text="Gold x."))
        self.assertIsNone(PK.lineup_for(a, no_subject, need_stand_alone=True))   # topical: no clip names Bitcoin

    def test_a_pronoun_hook_gives_way_to_the_next_hook(self):
        by = {m["moment_id"]: m for m in (dict(pm("p", "A", 12.0), text="It is the hardest money. Bitcoin is."),
                                          dict(pm("h", "B", 12.0), text=self.HOOK), dict(pm("x", "C", 14.0), text="Bitcoin x."),
                                          dict(pm("y", "D", 13.0), text="Bitcoin y."))}
        a = angle(["p", "h", "x", "y"], "p")
        self.assertEqual(PK.lineup_for(a, by)[0]["moment_id"], "p")
        self.assertEqual(PK.lineup_for(a, by, need_stand_alone=True)[0]["moment_id"], "h")

    def test_build_leaves_no_role_moments_out_before_the_angle_and_seals_the_row(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
              dict(pm("b", "E", 13.0), text=self.BUT1)]
        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(list(out["no_role"]), ["b"])
        self.assertIn("clip opens on 'but'", out["no_role"]["b"])
        self.assertFalse(any("id=b " in p for role, p in rig.prompts if role == "angle_write"))
        g = out["package"]["gates"]["stand_alone"]
        self.assertEqual(g["status"], "PASS")
        self.assertEqual(len(g["rows"]), 3)

    def test_inventory_writes_a_FAIL_row_with_its_evidence(self):     # audit 0310 C1, glm P1-3
        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": "Bitcoin x."}, {"text": self.BUT2}])
        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
               "backend": "x", "replayed": False, "measured": True}
        g = PK.inventory(fid, [], True, (True,), {"ok": True, "measured": True, "replayed": False}, {}, {}, {}, True,
                         {"measured": True, "replayed": False}, stand=r)["stand_alone"]
        self.assertEqual(g["status"], "FAIL")
        self.assertEqual([x.split(":")[0] for x in g["rows"]], ["hook", "clip_01", "clip_02"])
        self.assertIn("clip_02: FAIL opener: clip opens on 'but'", g["rows"][2])
        self.assertNotIn("stand_alone", PK.inventory(fid, [], True, (True,), {"ok": True, "measured": True,
                                                                                 "replayed": False}, {}, {}, {}, True,
                                                         {"measured": True, "replayed": False}))

    def test_the_row_fails_and_the_pin_is_refused_when_a_clip_opens_on_a_conjunction(self):
        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": "Bitcoin x."}, {"text": self.BUT2}])
        self.assertFalse(r["ok"])
        pk = {"shape": "medley"}
        gates = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
        gates["stand_alone"] = {"status": "PASS" if r["ok"] else "FAIL", "by": "x", "replayed": False, "n": 1}
        self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])


class TestRuling33TrimAtThePinStage(unittest.TestCase):
    """Ruling 33 part 2 (render merged 11e361cc), used per the 04:58 order's item 42: a moment opening on ONE of
    but/and/so/well/now/yeah, left out by the render's STAND_ALONE opener rule, may be cut one word in. The variant is
    judged like any moment (step A, L-v 2 with the trimmed word heard, the acoustic onset rule at the trimmed cut); the
    clip scorer must affirm the trimmed text (ruling 56: the integrator's pin-stage verdicts; ruling 49 a's pending form
    is retired); the pin seals trimmed_leading, untrimmed_start and the affirmation."""

    def moment(self, sentence, mid="t"):
        src = source([sentence], vid="vT")
        a, b = src.sentences[0]
        m = dict(pm(mid, "T", 0.0, vid="vT"), text=E.spoken(src.tokens[a:b + 1]), words=[a, b],
                 start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
        m["duration_s"] = round(m["end"] - m["start"], 2)
        return m, {"vT": src}

    def test_one_leading_word_is_trimmed_and_the_variant_carries_it(self):
        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
        self.assertIn("clip opens on 'but'", PK.no_role_on_screen(m))
        v = PK.trim_variant(m, srcs)
        self.assertEqual((v["moment_id"], v["trimmed_leading"], v["untrimmed_start"]), ("t~trim", "But", m["start"]))
        self.assertTrue(v["text"].startswith("Bitcoin has rarely"))
        self.assertEqual(v["words"], [m["words"][0] + 1, m["words"][1]])
        self.assertGreater(v["start"], m["start"])
        self.assertAlmostEqual(v["duration_s"], round(m["end"] - v["start"], 2))
        self.assertIsNone(PK.no_role_on_screen(v))

    def test_only_one_word_and_only_the_ruled_words(self):
        for sentence in ("But then Bitcoin had six negative weeks back to back in its whole history.",    # 'then'
                         "Because Bitcoin had six negative weeks back to back in its whole history.",      # not ruled
                         "And/or Bitcoin had six negative weeks back to back in its whole history.",       # 2 tokens
                         "Bitcoin had six negative weeks back to back in its whole history."):             # no opener
            m, srcs = self.moment(sentence)
            self.assertIsNone(PK.trim_variant(m, srcs), sentence)
        self.assertEqual(PK.TRIM_WORDS, package_pin.TRIM_WORDS)
        m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
        self.assertIsNone(PK.trim_variant(m, srcs))

    def test_ruling_56_a_trimmed_clip_passes_only_with_the_scorers_affirmation(self):
        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
        v = PK.trim_variant(m, srcs)
        hook, last = {"text": "Bitcoin is the hardest money ever made."}, {"text": "Bitcoin wins."}
        self.assertFalse(hasattr(PK, "TRIM_SCORER_PENDING"))          # ruling 49 (a)'s pending form is retired
        r = PK.stand_alone_check([hook, v, last])                     # no verdict: fails closed, as at validate
        self.assertFalse(r["ok"])
        self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
        self.assertNotIn("scorer_pending", r)
        r = PK.stand_alone_check([hook, dict(v, scorer_verdict=sv(v["text"], 4.0)), last])
        self.assertTrue(r["ok"], r["rows"])
        self.assertIn("the clip scorer affirms the trimmed text", r["rows"][1]["opener"]["why"])
        self.assertEqual(r["rows"][1]["scorer"]["score"], 4.0)        # the verdict used is in the sealed row
        for bad in (sv(v["text"], 3.0, "ends_mid_thought"), sv(v["text"], 3.4),
                    sv(m["text"], 4.0)):                              # the untrimmed text's verdict is not its own
            self.assertFalse(PK.stand_alone_check([hook, dict(v, scorer_verdict=bad), last])["ok"], bad)
        self.assertTrue(PK.stand_alone_check([hook, dict(v, scorer_verdict=sv(v["text"], 4.0, "starts_mid_thought")),
                                              last])["ok"])           # ruling 60: the score alone, as validate
        self.assertIn("no clip-scorer verdict on the trimmed text yet", PK.trim_refused(v))
        self.assertIsNone(PK.trim_refused(dict(v, scorer_verdict=sv(v["text"], 4.0))))
        self.assertIn("does not affirm", PK.trim_refused(dict(v, scorer_verdict=sv(v["text"], 3.0, "other"))))

    def test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin(self):
        self.assertEqual(PK.TRIMMED_PER_LINEUP_MAX, package_pin.TRIMMED_PER_PIN_MAX)
        ms = [dict(pm("h", "A", 12.0)), dict(pm("x", "B", 14.0), trimmed_leading="But", untrimmed_start=0.0),
              dict(pm("y", "C", 13.0), trimmed_leading="So", untrimmed_start=0.0), dict(pm("z", "D", 13.0))]
        for m in ms:
            m["hook_onset"] = {"pass": True}
        by = {m["moment_id"]: m for m in ms}
        self.assertEqual(PK.lineup_ok([by["h"], by["x"], by["y"]])[1], "more than 1 trimmed clip (ruling 49 b)")
        segs = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by, need_onset=True)
        self.assertEqual(sum(bool(m.get("trimmed_leading")) for m in segs), 1, [m["moment_id"] for m in segs])
        two = [{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True},
               {"trimmed_leading": "So", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True}]
        self.assertIn("2 trimmed clips", package_pin.trim_problems(two)[0])

    def test_the_pin_seals_the_trim_with_its_affirmation_and_refuses_a_malformed_one(self):
        import copy
        x_text = "Bitcoin keeps every promise it ever made to me."
        segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
                dict(pm("x", "B", 14.0), text=x_text, trimmed_leading="But", untrimmed_start=0.0, start=0.3,
                     scorer_verdict=sv(x_text, 4.0)),
                dict(pm("y", "C", 13.0), text="Bitcoin wins in the end, every single time.")]
        by = {m["moment_id"]: m for m in segs}
        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
                  "caption": {"text": "three clips", "cites": []}}
        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
        self.assertEqual((pk["segments"][1]["trimmed_leading"], pk["segments"][1]["untrimmed_start"]), ("But", 0.0))
        pk["gates"] = TestMedleyPackageAndPin().gates(pk)
        pin = package_pin.to_pin(copy.deepcopy(spk(pk)), "test")
        s1 = pin["segments"][1]
        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
        self.assertTrue(package_pin.affirmed_verdict(s1))                         # ruling 56: sealed, on its text
        self.assertNotIn("scorer_pending", s1)
        for k in ("trimmed_leading", "scorer_verdict", "scorer_pending"):         # untrimmed segments: unchanged
            self.assertNotIn(k, pin["segments"][0])
        mp = pin["moments_package"]
        args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
        self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
        other = copy.deepcopy(pin["segments"])
        other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
        other = copy.deepcopy(pin["segments"])
        other[1]["scorer_verdict"]["score"] = 5.0                                 # and so is the affirmation
        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
        for bad in ({"trimmed_leading": "Because"}, {"trimmed_leading": "But so"}, {"trimmed_leading": "and/or"},
                    {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
                    {"scorer_pending": True},                                     # ruling 56: never sealed
                    {"scorer_verdict": sv(x_text, 3.0, "ends_mid_thought")},      # a refusal
                    {"scorer_verdict": sv("But " + x_text, 4.0)},                 # another text's verdict
                    {"scorer_verdict": dict(sv(x_text, 4.0), kind="story")}):     # not the moments judgment
            p = copy.deepcopy(spk(pk))                                            # each case on its own
            p["segments"][1] = dict(p["segments"][1], **bad)
            with self.assertRaises(package_pin.PinRefused, msg=str(bad)):
                package_pin.to_pin(p, "test")
        p = copy.deepcopy(spk(pk))
        p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "scorer_verdict"}   # no affirmation
        with self.assertRaises(package_pin.PinRefused):
            package_pin.to_pin(p, "test")
        p = copy.deepcopy(spk(pk))
        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # not on any segment
        with self.assertRaises(package_pin.PinRefused):
            package_pin.to_pin(p, "test")
        self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
        p = copy.deepcopy(spk(pk))                                        # ^ refused, never raised (glm P0-8)
        p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
        with self.assertRaises(package_pin.PinRefused):                          # both keys or neither
            package_pin.to_pin(p, "test")

    def test_a_trimmed_moment_that_cannot_be_cut_cleanly_is_left_out(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
              dict(pm("b", "E", 13.0), text="But Bitcoin x.")]
        v = dict(ms[4], moment_id="b~trim", text="Bitcoin x.", trimmed_leading="But", untrimmed_start=0.0)
        saved = PK.trim_variant
        try:
            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
            ok = {"b~trim": fv("Bitcoin x.", 4.0)}                  # ruling 56: the scorer affirms the trimmed text
            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"}, verdicts=ok)
            out = rig.run()
            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"}, verdicts=ok)
            out2 = rig2.run()
        finally:
            PK.trim_variant = saved
        self.assertEqual(out["trimmed"], {"b": "b~trim"})
        self.assertTrue(out["prescreen"]["trim_cut"]["b~trim"].startswith("FAIL: the trimmed word"))   # (a): out
        self.assertNotIn("id=b~trim ", next(p for r, p in rig.prompts if r == "angle_write"))         # at any place
        self.assertIsNotNone(out["package"])
        self.assertTrue(out2["prescreen"]["hook_onset"]["b~trim"].startswith("FAIL"))   # cannot open (glm C2 N5)
        self.assertEqual(out2["prescreen"]["trim_cut"], {})        # its cut is clean, only its hook lead fails: it
        self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip


class TestRuling94HookOpeners(unittest.TestCase):
    """RULING 94 (00:40 ET Nov 14): (a) a hook opening on a conjunction or reply word opens as ruling 33's one-word trim
    variant, whatever its clip role (the trim cuts cleanly, the scorer affirms it); (b) a first/second-person opener is
    no fault; a third-person or demonstrative one needs the clip scorer's affirmation."""

    def opener(self, text, reasons=(), verdict=None):
        m = dict(pm("o", "O", 13.0), text=text, hook_onset={"pass": True, "measured": True})
        m["eligibility"] = {"hook": {"ok": not reasons, "reasons": list(reasons)}, "clip": {"ok": True}}
        return dict(m, scorer_verdict=verdict) if verdict else m

    def test_first_and_second_person_open_and_third_person_needs_the_scorer(self):
        self.assertTrue(PK._can_open(self.opener("I will bet you one Bitcoin that it gets there.")))
        self.assertTrue(PK._can_open(self.opener("You know, Bitcoin is not done.")))
        t = "This is ultimately a bipartisan issue for Bitcoin."
        self.assertTrue(PK.third_opener({"text": t}))
        self.assertFalse(PK._can_open(self.opener(t, ["opener"])))                         # no verdict: closed
        self.assertTrue(PK._can_open(self.opener(t, ["opener"], sv(t, 4.0))))              # affirmed: open
        self.assertFalse(PK._can_open(self.opener(t, ["opener"], sv(t, 3.0))))
        self.assertTrue(PK._can_open(self.opener(t, ["opener"]), pending_verdict=True))   # the spotlight waits
        self.assertFalse(PK._can_open(self.opener(t, ["opener", "hook_lead"], sv(t, 4.0))))   # another reason holds
        self.assertFalse(PK._can_open(self.opener("So Bitcoin is down.")))                 # (a): only the trim opens
        self.assertTrue(PK.hook_trim({"text": "So Bitcoin is down."}))
        self.assertFalse(PK.hook_trim({"text": "Because Bitcoin is down."}))               # not a ruled trim word

    def test_the_scorer_is_asked_for_a_hook_trim_and_a_third_person_opener(self):
        d = tempfile.mkdtemp()
        try:
            src = source(["So Bitcoin has rarely seen six negative weeks back to back in its whole history."],
                         vid="vS")
            a, b = src.sentences[0]
            so = dict(pm("s", "S", 0.0, vid="vS"), text=E.spoken(src.tokens[a:b + 1]), words=[a, b],
                      start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
            so = dict(so, scorer_verdict=sv(so["text"], 4.0))          # its CLIP role is affirmed as it is
            this = dict(pm("t", "T", 12.0), text="This is ultimately a bipartisan issue for Bitcoin.")
            plain = dict(pm("p", "P", 12.0), text="Bitcoin is the hardest money there is.")
            PK.scorer_pass([so, this, plain], {"vS": src}, E.Context(NOW, REG), None,
                           os.path.join(d, "c.json"), "b")
            asked = [c["pid"] for c in json.load(open(os.path.join(d, "c.json")))["candidates"]]
            self.assertIn("s~trim", asked)                              # (a): its hook trim variant
            self.assertIn("t", asked)                                   # (b): the third-person opener itself
            self.assertNotIn("p", asked)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_hook_trim_variant_joins_the_pool_beside_its_affirmed_original(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
              dict(pm("s", "E", 13.0), text="So Bitcoin x.")]
        v = dict(ms[4], moment_id="s~trim", text="Bitcoin x.", trimmed_leading="So", untrimmed_start=0.0)
        saved = PK.trim_variant
        try:
            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "s" else None
            ok = {"s": fv("So Bitcoin x.", 4.0), "s~trim": fv("Bitcoin x.", 4.0)}   # the clip role affirmed as it is
            out = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], verdicts=ok).run()
        finally:
            PK.trim_variant = saved
        self.assertEqual(out["trimmed"], {"s": "s~trim"})               # ruling 94 (a): not only for no_role ones
        self.assertIsNotNone(out["package"])


class TestRuling58StepAEveryCandidate(unittest.TestCase):
    """RULING 58 (11:00): EVERY candidate is screened at step A, the miner's best first, and a verdict is cached by the
    moment id + its text sha (and the exact context step A reads), so a moment is paid for once, not once per build."""

    def pool(self, n=20, words="is the hardest money ever made"):
        ms, srcs = [], {}
        for i in range(n):
            mid = f"m{i:02d}"
            src = source(["Before it came the long part of the show.", f"Bitcoin number {i} {words}.",
                          "After it came the end of the show."], vid=f"v{mid}")
            a, b = src.sentences[1]
            m = dict(pm(mid, f"C{i:02d}", 0.0, rank=float(i), vid=f"v{mid}"), text=E.spoken(src.tokens[a:b + 1]),
                     words=[a, b], sentences=[1, 1], start=float(src.tokens[a]["start"]), end=float(src.tokens[b]["end"]))
            m["duration_s"] = round(m["end"] - m["start"], 2)
            ms.append(m)
            srcs[f"v{mid}"] = src
        return ms, srcs

    def router(self):
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        return type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall", "deepseek")}})()

    def fake(self, calls, fail=frozenset(), seen=None):
        import context_integrity as CI
        from test_gates import a_item

        def step_a(router_, contexts, wv, seed=7, writer_family=None, deadline_s=None, failover=False, kind=None):
            calls.append((sorted(contexts), seed))
            if seen is not None:
                seen.update(contexts)                    # ruling 126 (1): the exact contexts step A was given
            if set(contexts) & set(fail):
                raise RuntimeError("the batch reply was out of contract")
            b = "heimdall:deepseek" if "xai" in (wv or set()) else "xai:grok"
            return {mid: dict(a_item(mid), backend=b) for mid in contexts}, b
        saved = CI.step_a
        CI.step_a = step_a
        self.addCleanup(setattr, CI, "step_a", saved)

    def test_every_candidate_is_screened_the_miners_best_first(self):
        self.assertIsNone(PK.PRESCREEN_N)
        import tempfile
        ms, srcs = self.pool(20)
        calls = []
        self.fake(calls)
        with tempfile.TemporaryDirectory() as d:
            a_by, fails, vendors, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"},
                                                   store=os.path.join(d, "a.json"), cache=os.path.join(d, "c.json"))
        self.assertEqual(len(a_by), 20)                                   # all 20, not 24 of 150
        self.assertEqual(sum(len(c[0]) for c in calls), 20)
        self.assertEqual(sorted(c[1] for c in calls), [7, 15, 23])        # 8 + 8 + 4, the seeds of their places
        first = next(c[0] for c in calls if c[1] == 7)
        self.assertEqual(first, sorted(f"m{i:02d}" for i in range(19, 11, -1)))   # the miner's best 8 first
        self.assertEqual(vendors, {"xai"})
        self.assertFalse(any(fails.values()))

    def test_a_moment_is_paid_for_once_across_builds(self):
        import tempfile
        ms, srcs = self.pool(10)
        calls = []
        self.fake(calls)
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "STEP_A_CACHE.json")
            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, store=os.path.join(d, "1.json"),
                         cache=cache)
            self.assertEqual(sum(len(c[0]) for c in calls), 10)
            calls.clear()                                                 # the next build: a new ledger, same cache
            a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"},
                                             store=os.path.join(d, "2.json"), cache=cache)
            self.assertEqual((calls, len(a_by)), ([], 10))               # nothing paid for again
            with open(os.path.join(d, "2.json")) as f:
                self.assertEqual(len(json.load(f)), 10)                   # this build's ledger still records them
            changed, srcs2 = self.pool(10, words="is the softest money ever made")
            PK.prescreen(self.router(), changed[:2] + ms[2:], dict(srcs, **{k: srcs2[k] for k in ("vm00", "vm01")}),
                         ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01"])   # a new text: asked again
            calls.clear()
            later = E.Context(NOW + timedelta(days=1), REG)
            PK.prescreen(self.router(), ms[:3], srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(calls, [])                  # RULING 126 (1): no time words: a new show date asks nothing
            ts = [dict(m, risk=["time_sensitive"]) for m in ms[:2]]          # the miner's flag: time words
            PK.prescreen(self.router(), ts, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            calls.clear()
            PK.prescreen(self.router(), ts, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(calls, [])                  # the same show date: paid for once
            PK.prescreen(self.router(), ts, srcs, later, {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01"])   # time words: a new show date
            calls.clear()
            a_by, _, _, _ = PK.prescreen(self.router(), ms[:3], srcs, ctx(), {"xai"}, {"grok"}, cache=cache)
            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
            self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict

    def test_ruling_126_the_show_date_is_the_et_date(self):
        """RULING 126 (1): the show date step A and the context check carry is the ET date, not the UTC date (19:30 ET
        Nov 10 is 00:30 UTC Nov 11)."""
        import context_integrity as CI
        import tempfile
        from datetime import datetime, timezone
        evening = datetime(2026, 11, 11, 0, 30, tzinfo=timezone.utc)
        self.assertEqual(CI.show_date(evening), "2026-11-10")
        self.assertEqual(CI.show_date(datetime(2026, 11, 11, 5, 0, tzinfo=timezone.utc)), "2026-11-11")
        self.assertIsNone(CI.show_date(None))
        ms, srcs = self.pool(2)
        calls, seen = [], {}
        self.fake(calls, seen=seen)
        with tempfile.TemporaryDirectory() as d:
            PK.prescreen(self.router(), ms, srcs, E.Context(evening, REG), {"heimdall"}, {"deepseek"},
                         cache=os.path.join(d, "c.json"))
        self.assertEqual({c["show_date"] for c in seen.values()}, {"2026-11-10"})
        seg = {"label": "clip_01", "video_id": ms[0]["video_id"], "k0": 1, "k1": 1, "words": ms[0]["words"],
               "channel": "C00"}
        self.assertEqual(CI.contexts_from_sources({"segments": [seg]}, srcs, evening)["clip_01"]["show_date"],
                         "2026-11-10")

    def test_ruling_126_a_verdict_cached_under_the_old_key_is_read_once_and_moved(self):
        """RULING 126 (1): a moment with no time words finds its verdict under the key it was cached under before (the
        UTC show date in it, today's or yesterday's UTC date) and pays nothing; the verdict is written under its new key;
        a time-sensitive moment never takes an old key's verdict; older than yesterday is not looked for."""
        import tempfile
        ms, srcs = self.pool(4)
        ms[3] = dict(ms[3], risk=["time_sensitive"])
        calls, seen = [], {}
        self.fake(calls, seen=seen)
        asked = lambda: sorted(sum((c[0] for c in calls), []))
        with tempfile.TemporaryDirectory() as d:
            c1 = os.path.join(d, "c1.json")
            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=c1)
            with open(c1) as f:
                now_keys = json.load(f)
            old = {}
            for m in ms:                                 # the same verdicts under the keys used before ruling 126 (1)
                c = dict(seen[m["moment_id"]], show_date=NOW.strftime("%Y-%m-%d"))
                old[f"{m['moment_id']}:{PK.text_sha(m['text'])}:{PK.text_sha(json.dumps(c, sort_keys=True))}:"
                    f"{PK.STEP_A_VERSION}"] = now_keys[PK.step_a_key(m, seen[m["moment_id"]])]
            for days, want in ((20 / 24, ["m03"]), (1 + 20 / 24, ["m00", "m01", "m02", "m03"])):
                c2 = os.path.join(d, f"c2_{days:.2f}.json")
                with open(c2, "w") as f:
                    json.dump(old, f)
                calls.clear()
                later = E.Context(NOW + timedelta(days=days), REG)
                a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, later, {"heimdall"}, {"deepseek"}, cache=c2)
                self.assertEqual((asked(), len(a_by)), (want, 4), days)
                if days < 1:
                    with open(c2) as f:
                        moved = json.load(f)
                    for m in ms[:3]:                     # written under the new key: found there next time
                        self.assertIn(PK.step_a_key(m, seen[m["moment_id"]]), moved)
                    calls.clear()
                    PK.prescreen(self.router(), ms, srcs, later, {"heimdall"}, {"deepseek"}, cache=c2)
                    self.assertEqual(calls, [])

    def test_ruling_101_plan_only_lists_what_the_screen_would_ask_and_asks_nothing(self):
        import tempfile
        ms, srcs = self.pool(10)
        calls = []
        self.fake(calls)
        ids = lambda xs: sorted(m["moment_id"] for m in xs)
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "STEP_A_CACHE.json")
            new = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache, plan_only=True)
            self.assertEqual((ids(new), calls, os.path.exists(cache)), (ids(ms), [], False))   # all new, nothing asked
            PK.prescreen(self.router(), ms[:6], srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)   # 6 paid for
            calls.clear()
            with open(cache) as f:
                before = f.read()
            new = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache, plan_only=True)
            self.assertEqual(ids(new), ids(ms[6:]))                       # only the 4 the cache does not hold
            with open(cache) as f:
                self.assertEqual((calls, f.read()), ([], before))         # nothing asked, nothing written

    def test_a_failed_batch_is_no_verdict_never_cached_and_says_why(self):
        import tempfile
        ms, srcs = self.pool(10)
        calls = []
        self.fake(calls, fail={"m09"})                                    # the miner's best batch fails
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "c.json")
            a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(len(a_by), 2)                                # the other batch (2) only
            self.assertEqual(fails["m09"], [f"{PK.HELD}: no step-A verdict (RuntimeError: the batch reply was out of "
                                            f"contract); held for this build, retried next build"])   # ruling 102
            with open(cache) as f:
                self.assertEqual(len(json.load(f)), 2)                    # a failure is never remembered
            calls.clear()
            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(len(sum((c[0] for c in calls), [])), 8)      # asked again, the 8 only


class TestRuling59HookFirst(unittest.TestCase):
    """RULING 59 (11:00): HOOK FIRST. Every cleared, cuttable moment that can open is rated on the hook's own job (ruling
    52's question), cached; the angles are written FOR the passing hooks and tried best hook first; with no passing
    hook the build stops before any line-up, listing the best three. RULING 115: each candidate is asked ALONE (one
    call a candidate), and a hook passes when each of its parts is at least its calibrated floor (the rigs': conftest)."""

    def canned(self, *replies):
        c = Canned(coherence_verdict=list(replies))
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        c.backends = {"fake:coherence_verdict": B("fake", "fake")}
        return c

    def test_each_candidate_is_asked_alone_one_call_each_and_the_rating_is_derived_and_cached(self):
        from unittest import mock
        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
        ra = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"}}}
        rb = {"hooks": {"b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "HOOK_CACHE.json")
            c = self.canned(ra, rb)
            got, err = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertIsNone(err)
            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})] * 2)   # ONE call EACH (ruling
            #   115: the asking the calibration measured), off the writers
            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # scroll / alone: it ORDERS hooks
            self.assertEqual((got["a"]["setup"], got["b"]["why"]), (5, "needs what came before"))   # every part kept
            again, err = PK.hook_ratings(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual((err, again["a"]["rating"], again["a"]["cached"]), (None, 4, True))   # no call at all
            new = [dict(ms[0], text="Bitcoin is a new text now."), ms[1]]
            c = self.canned({"hooks": {"a": {"scroll": 3, "alone": 3, "setup": 3, "why": "w"}}})
            got, _ = PK.hook_ratings(c, new, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual((len(c.calls), got["a"]["rating"], got["b"]["cached"]), (1, 3, True))   # its new text only
            c = self.canned(ra)                                              # a router whose hook list is missing:
            c.chain = lambda role, kind=None: (_ for _ in ()).throw(__import__("providers").ProviderError("no chain"))
            got, _ = PK.hook_ratings(c, ms[:1], ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))   # no cached rating answers (fail closed)
            with mock.patch.object(PK, "HOOK_VERSION", "another-asking"):   # a rating cached under another question
                c = self.canned(ra, rb)                                      # or asking never answers (the batched
                got, _ = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)   # ratings of before)
                self.assertEqual((len(c.calls), got["a"]["cached"], got["b"]["cached"]), (2, False, False))

    def test_the_cache_answers_only_for_todays_hook_list_and_production_seed(self):
        """Audit 20261115_1410 C1 (glm): a rating cached by a model that is NOT on today's hook list is asked again (a
        rater change re-asks every hook: a rating off the list can never pass the bar); a rating asked at another
        seed never reads or writes the cache (the key's version carries production's seed)."""
        ms = [pm("a", "A", 12.0)]
        ra = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w"}}}
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "HOOK_CACHE.json")
            c = self.canned(ra)
            c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
            PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache)            # cached by fake:coherence_verdict
            c = self.canned()
            c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
            got, err = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache)
            self.assertEqual((err, got["a"]["cached"], c.calls), (None, True, []))   # on the list: served
            c = self.canned(ra)
            c.chain = lambda role, kind=None: ["xai:another-rater"]
            got, err = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache)
            self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))    # off today's list: asked again
            before = open(cache).read()
            c = self.canned({"hooks": {"b": {"scroll": 5, "alone": 4, "setup": 5, "why": "w"}}})
            got, _ = PK.hook_ratings(c, [pm("b", "B", 12.0)], ctx(), set(), set(), cache=cache, seed=PK.HOOK_SEED + 1)
            self.assertEqual((len(c.calls), open(cache).read()), (1, before))   # another seed: never written
            c = self.canned(ra)
            got, _ = PK.hook_ratings(c, ms, ctx(), set(), set(), cache=cache, seed=PK.HOOK_SEED + 1)
            self.assertEqual((got["a"]["cached"], len(c.calls)), (False, 1))   # ... and never read

    def test_q2_an_answer_whose_only_extra_is_trailing_closing_braces_is_read(self):
        """STATE Q2 (15:04 ET Nov 15, default 15:24): Grok's out-of-contract hook answers were valid JSON and ONE extra
        closing brace; such an answer is read and its record says so; any other extra stays out of contract, and the
        contract's own checks still apply."""
        ms = [pm("a", "A", 12.0)]
        ok = '{"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}'
        for extra, n in (("}", 1), ("}}\n", 2), (" }", 1)):
            got, err = PK.hook_ratings(self.canned(ok + extra), ms, ctx(), set(), set())
            self.assertEqual((err, got["a"]["rating"], got["a"].get("answer_note")),
                             (None, 4, f"{n} {PK.BRACES_NOTE}"), extra)
        got, err = PK.hook_ratings(self.canned(ok), ms, ctx(), set(), set())
        self.assertEqual((err, "answer_note" in got["a"]), (None, False))
        for bad in (ok + "} x", ok + "]", ok + ', "b": 1}', '{"hooks": {"a": {"scroll": 4}}}}', "} " + ok):
            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
            self.assertEqual(got, {}, bad)                                   # out of contract: no rating
            self.assertIn("Error", err)

    def test_a_candidate_left_unrated_never_stops_the_others_being_asked(self):
        """RULING 115: one call a candidate; a candidate whose chain is spent has no rating (law L-m), the others are
        still asked, and the first error is returned."""
        import providers as P
        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
        c = self.canned()
        asked = []

        def call(role, prompt, *a, **k):
            asked.append(re.findall(r'CANDIDATE id="(\w+)"', prompt))
            if 'CANDIDATE id="a"' in prompt:
                raise P.ProviderError("coherence_verdict: every back-end unavailable")
            return P.Reply(json.dumps({"hooks": {"b": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}),
                           "fake:coherence_verdict", "fake")
        c.call = call
        got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
        self.assertEqual((asked, sorted(got), got["b"]["rating"]), ([["a"], ["b"]], ["b"], 4))
        self.assertIn("ProviderError: coherence_verdict: every back-end unavailable", err)

    def test_the_prompt_asks_ruling_52s_question_of_each_candidate_alone(self):
        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
        prompts = []
        c = self.canned(*({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"}}} for k in "ab"))
        call = c.call
        c.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        PK.hook_ratings(c, ms, ctx(), set(), set())
        self.assertEqual(len(prompts), 2)                                 # ruling 115: ONE candidate a call
        for p, me, other in ((prompts[0], "a", "b"), (prompts[1], "b", "a")):
            self.assertIn(PK.HOOK_QUESTION, p)                            # ONE definition of the hook's job
            self.assertIn(f'CANDIDATE id="{me}"', p)
            self.assertNotIn(f'CANDIDATE id="{other}"', p)
            self.assertIn("Judge each one ALONE", p)

    def chained(self, *replies):
        """A canned chain: each call is answered by the next model (fake:1, fake:2, ...), and a model the caller
        skips (avoid_model) is never asked."""
        c = self.canned(*replies)
        call, n = c.call, [0]

        def nxt(role, prompt, *a, avoid_model=None, **k):
            r = call(role, prompt, *a, **k)
            n[0] += 1
            name = f"fake:{n[0]}"
            assert name not in (avoid_model or ()), "a skipped model was asked"
            c.asked_skip = getattr(c, "asked_skip", []) + [sorted(avoid_model or ())]
            import providers as P
            return P.Reply(r.text, name, "fake")
        c.call = nxt
        return c

    def test_a_reply_out_of_contract_moves_on_to_the_next_model_then_nothing_is_rated(self):
        """The 20:33 order (ruling 82's chain on every verdict): an answer out of contract moves on to the NEXT model
        (it was one re-ask of the same model); the chain spent is no verdict (law L-m)."""
        ms = [pm("a", "A", 12.0)]
        ok = {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}
        c = self.chained({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
        got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
        self.assertEqual((err, got["a"]["rating"], got["a"]["backend"], len(c.calls), c.rejected),
                         (None, 4, "fake:2", 2, ["fake:1"]))
        self.assertEqual(c.asked_skip, [[], ["fake:1"]])                   # the second ask skips the first model
        for bad in ({"hooks": {}}, {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4}}}, {"x": 1}, "no json"):
            got, err = PK.hook_ratings(self.chained(bad, bad), ms, ctx(), set(), set())
            self.assertEqual(got, {})
            self.assertIn("Error", err)
        got, err = PK.hook_ratings(self.canned(), ms, ctx(), set(), set())   # unavailable: no verdict (law L-m)
        self.assertEqual(got, {})
        self.assertIn("ProviderError", err)

    def test_only_a_hook_on_its_calibrated_bar_opens(self):
        """RULING 115: a rated hook opens when EACH part is at least its calibrated floor (the rigs': scroll 3, alone 4,
        setup 3) and the calibrated rater rated it; with no valid calibration no rated hook opens (fail closed)."""
        from unittest import mock
        m = dict(pm("a", "A", 12.0), hook_onset={"pass": True})
        self.assertTrue(PK.can_open(m))                                   # not rated yet: as before ruling 59
        G = "xai:grok"
        for (sc, al, se), ok in (((3, 4, 3), True), ((5, 4, 5), True), ((2, 5, 5), False), ((5, 3, 5), False),
                                 ((5, 5, 2), False)):                     # setup counts now (ruling 115)
            r = dict(m, hook_rating={"scroll": sc, "alone": al, "setup": se, "backend": G})
            self.assertEqual(PK.can_open(r), ok, (sc, al, se))
            self.assertEqual(PK.placement(r), "" if ok else " | cannot open (never the hook)")
        top = dict(m, hook_rating={"scroll": 5, "alone": 5, "setup": 5, "backend": G})
        self.assertFalse(PK.can_open(dict(top, hook_rating=dict(top["hook_rating"],
                                                                backend="heimdall:qwen/qwen3.8-27b"))))   # off the rater
        for bad in (None, {"rating": 5}, {"scroll": True, "alone": 5, "setup": 5, "backend": G},
                    {"scroll": 5.0, "alone": 5, "setup": 5, "backend": G}, {"scroll": 5, "alone": 5, "backend": G}):
            self.assertFalse(PK.can_open(dict(m, hook_rating=bad)), bad)
        self.assertFalse(PK.can_open(dict(top, text="And Bitcoin is money.")))   # the render's hook rule
        low = dict(m, hook_rating={"scroll": 5, "alone": 3, "setup": 4, "backend": G})
        self.assertFalse(PK.lineup_ok([low, pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])
        with mock.patch.object(PK, "_live_bar", lambda: (None, "the hook calibration is over 24 h old: re-run it")):
            self.assertFalse(PK.can_open(top))                             # no valid calibration: no hook passes
            self.assertEqual(PK.hook_own(top)["short"], "the hook calibration is over 24 h old: re-run it")

    def test_a_line_up_opens_on_its_angles_own_hook_and_never_swaps_it(self):
        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"scroll": 5, "alone": 5, "setup": 5,
                                                                                 "backend": "xai:grok"})
              for k, d in (("a", 12.0), ("b", 14.0), ("c", 13.0), ("d", 13.0))]
        by = {m["moment_id"]: m for m in ms}
        by["b"]["scores"] = dict(by["b"]["scores"], hook_first_2s=99)     # a stronger opener elsewhere
        segs = PK.lineup_for(angle(["b", "a", "c", "d"], "a"), by, need_onset=True, hook_only=True)
        self.assertEqual(segs[0]["moment_id"], "a")
        low = dict(by, a=dict(by["a"], hook_rating={"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"}))
        self.assertIsNone(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True, hook_only=True))
        self.assertEqual(PK.lineup_for(angle(["b", "a", "c", "d"], "a"), low, need_onset=True)[0]["moment_id"], "b")
        self.assertEqual(PK.swap_lineup(segs, {"a"}, by, keep_hook=True), (None, None))
        new, swaps = PK.swap_lineup(segs, {segs[1]["moment_id"]}, by, keep_hook=True)
        self.assertEqual(new[0]["moment_id"], "a")
        with self.assertRaises(ValueError):
            PK.check_angles({"angles": [angle(["b", "a", "c"], "b")]}, by, hooks={"a"})
        self.assertEqual(len(PK.check_angles({"angles": [angle(["a", "b", "c"], "a")]}, by, hooks={"a"})), 1)

    def test_no_hook_in_the_pool_stops_before_the_second_screen_and_lists_the_best_three(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                  hooks={"h": (3, 4, 2), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})   # each under ONE floor
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertTrue(out["why_none"].startswith("no hook in the pool (ruling 59 d): none of the 4 moments"))
        self.assertIn("passes the calibrated hook bar (ruling 115): scroll >= 3, alone >= 4, setup >= 3", out["why_none"])
        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["y", "h", "x"])   # rating, then parts
        self.assertEqual([b["rating"] for b in out["hook_pool"]["best"]], [3, 3, 2])
        self.assertIn("A 3 (scroll 3, alone 4, setup 2): why h", out["why_none"])   # setup alone held h back
        self.assertEqual(out["hook_pool"]["bar_floors"], {"scroll": 3, "alone": 4, "setup": 3})
        self.assertEqual(rig.medley_calls, [])
        self.assertNotIn("angle_write", rig.events)                     # no angle, no line-up paid for
        self.assertEqual(len(rig.screens), 1)                            # and no second screen
        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], hook_err="ProviderError: down")
        out = rig.run()
        self.assertIn("not rated: ProviderError: down", out["why_none"])
        self.assertEqual(rig.medley_calls, [])

    def test_the_writer_is_given_the_passing_hooks_and_the_best_hook_goes_first(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        rig = Rig(ms, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)], [None],
                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 3, 5)})
        out = rig.run()
        p = next(p for r, p in rig.prompts if r == "angle_write")
        self.assertIn("THE HOOKS", p)
        self.assertLess(p.index("id=x | rated 5"), p.index("id=h | rated 4"))    # best first
        self.assertNotIn("id=y | rated", p)
        self.assertIn("id=y | C | 13.0 s | cannot open (never the hook) | ", p)
        self.assertIn("for EACH hook above at least one and at most 1 (every hook gets its own)", p)
        self.assertNotIn("angle_follow_up", out)                          # ruling 64: both hooks have an angle
        self.assertEqual(rig.medley_calls[0][0], "x")                   # the x angle, though the writer gave it second
        self.assertEqual(out["hook_pool"]["passing"], ["x", "h"])
        self.assertIsNotNone(out["package"])
        self.assertEqual((out["package"]["hook_bar"]["note"], out["package"]["hook_bar"]["floors"]),   # ruling 115 (2)
                         ("hook passed on the calibrated bar", {"scroll": 3, "alone": 4, "setup": 3}))
        self.assertEqual(out["package"]["hook_bar"]["calibration_sha256"], out["hook_pool"]["bar_sha256"])

    def test_the_mark_names_the_bar_the_hooks_were_judged_on(self):
        """Audit 20261115_1410 C2 (glm): the live bar changes after the hook stage (here at the write: another valid
        calibration); the sealed package's mark still names the bar its hooks were judged on."""
        from unittest import mock
        import conftest
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        cur = [conftest.rig_bar()]
        write = rig.write

        def flip(*a, **k):
            cur[0] = dict(conftest.rig_bar(), sha256="u" * 64)
            return write(*a, **k)
        rig.write = flip
        with mock.patch.object(PK, "_live_bar", lambda: (cur[0], None)):
            out = rig.run()
        self.assertIsNotNone(out["package"])
        self.assertEqual((out["package"]["hook_bar"]["calibration_sha256"], cur[0]["sha256"]), ("t" * 64, "u" * 64))

    def test_an_angle_not_written_for_a_passing_hook_is_out_of_contract(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        rig = Rig(ms, ["y", "h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
                  hooks={"y": (3, 3, 3), "h": (5, 5, 5), "x": (5, 5, 5), "z": (5, 5, 5)})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertIn("is not one of THE HOOKS", out["why_none"])           # the first reply, rejected
        self.assertEqual((len(rig.router.rejected), sum(r == "angle_write" for r, _ in rig.prompts)), (1, 2))
        self.assertEqual(rig.medley_calls, [])


class TestRuling116LineupBar(unittest.TestCase):
    """RULING 116 (Q3, ruling 106's default APPLY): the clips-alone and coherence verdicts judged on the calibrated
    line-up bar (the rigs': every clip after the hook >= 3, the VO point >= 3) when the calibrated rater gave them, on
    the standard bar (>= 4) otherwise; the hook's slot is its own bar everywhere (ruling 115)."""
    LABS = ["hook", "clip_01", "clip_02"]
    SEGS = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"}),
            pm("x", "B", 14.0), pm("y", "C", 13.0)]

    @staticmethod
    def router(reply, backend):
        import providers as P
        r = Canned(coherence_verdict=[reply])
        call = r.call

        def as_backend(role, *a, **k):
            x = call(role, *a, **k)
            return P.Reply(x.text, backend, backend.split(":")[0])
        r.call = as_backend
        return r

    def test_clips_alone_a_clip_at_3_passes_only_on_the_calibrated_raters_verdict(self):
        rep = reply(self.LABS, ratings={"clip_02": 3})
        ok, v = PK.medley(self.router(rep, "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
        self.assertEqual((ok, v["bar"], v["floors"], v["clips"]["hook"]), (True, "calibrated", {"clip": 3}, 3))
        ok, v = PK.medley(self.router(rep, "google:gemini-2.5-pro"), self.SEGS, E.Context(NOW, REG), set())
        self.assertEqual((ok, v["bar"], v["floors"]), (False, "standard", {"clip": 4}))     # Plan B: the standard bar
        ok, v = PK.medley(self.router(reply(self.LABS, ratings={"clip_02": 2}), "xai:grok"), self.SEGS,
                          E.Context(NOW, REG), set())
        self.assertFalse(ok)                                                             # under the floor
        ok, v = PK.medley(self.router(reply(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]),
                                      "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
        self.assertFalse(ok)                                                             # joins: the law's one
        ok, v = PK.medley(self.router(reply(self.LABS, line="none"), "xai:grok"), self.SEGS, E.Context(NOW, REG), set())
        self.assertFalse(ok)                                                             # a through-line, always

    def test_coherence_a_clip_or_vo_point_at_3_passes_only_on_the_calibrated_raters_verdict(self):
        pk = {"title": "t", "caption": "c", "vo": {"intro": None, "bridges": ["No ruler, just rules."],
                                                  "bridges_after_clip": [2], "signoff": "S"},
              "segments": [{"label": lb, "channel": ch, "text": f"Bitcoin {lb}."}
                           for lb, ch in zip(self.LABS, "ABC")]}
        rep = {"through_line": "Nobody can change the rules of Bitcoin.", "clips": {"clip_01": 3, "clip_02": 4},
               "vo_point": 3}
        ok, v = PK.coherence(self.router(rep, "xai:grok"), pk, set(), hook=self.SEGS[0])
        self.assertEqual((ok, v["bar"], v["floors"]), (True, "calibrated", {"clip": 3, "vo_point": 3}))
        ok, v = PK.coherence(self.router(rep, "heimdall:deepseek/deepseek-v4.1-flash"), pk, set(), hook=self.SEGS[0])
        self.assertEqual((ok, v["bar"]), (False, "standard"))
        ok, v = PK.coherence(self.router(dict(rep, vo_point=2), "xai:grok"), pk, set(), hook=self.SEGS[0])
        self.assertFalse(ok)

    def test_ruling_62_reads_the_verdicts_own_floor(self):
        segs = self.SEGS + [pm("z", "D", 9.0)]
        med = dict(verdict(PK.labels(4), ratings={"hook": 3, "clip_01": 3, "clip_02": 3, "clip_03": 2}),
                   measured=True, flagged=[], floors={"clip": 3})
        self.assertTrue(PK.last_clip_only(segs, med))                                   # only the last under 3
        self.assertFalse(PK.last_clip_only(segs, dict(med, floors={"clip": 4})))        # the standard bar: all fail
        self.assertFalse(PK.last_clip_only(segs, {k: x for k, x in med.items() if k != "floors"}))   # no floors: 4

    def test_ruling_63_reorders_a_line_up_whose_hook_sits_at_its_floors(self):
        """The hook's own rating (3, at its floors) never blocks ruling 63: the clips after it pass and two joins
        are flagged, so the same clips are reordered (before ruling 115 / 116 the hook's 3 sat in the min)."""
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        from unittest import mock
        for bar in ("calibrated", "standard"):            # the standard bar's floor 4 is where the hook's 3 blocked
            with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "none")) if bar == "standard" else \
                    mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN):
                rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
                                                (True, [], None, Rig.LINE)], [None], hooks={"h": (3, 4, 3)})
                out = rig.run()
            self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "x"]], bar)
            self.assertIn("ruling 63", out["tried"][0]["why"], bar)
            self.assertIsNotNone(out["package"], bar)

    def test_a_weak_vo_point_is_never_rewritten_and_the_line_up_takes_the_no_voice_shape(self):
        """REPLACES 'the takeaway alone is rewritten when only its point is weak with a hook at its floors' (ITEM 2,
        orchestrator 09:35 ET Nov 24: "One write ... no retry loop"): coherence fails on the VO point alone (2), the
        clips pass the calibrated floor and the hook sits at its floors (rating 3): the closing line is NOT written
        again; no line is a valid close, so the line-up takes the no-voice shape (its clips meet the seconds), one
        flag."""
        ms = [pm("h", "A", 16.0), pm("x", "B", 16.0), pm("y", "C", 16.0)]          # 48 s: 62.3 s with no VO line
        from unittest import mock
        for bar, clip in (("calibrated", 3), ("standard", 4)):   # the standard bar's 4: the hook's 3 blocked it
            with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "none")) if bar == "standard" else \
                    mock.patch.object(PK, "COHERENCE_MIN", PK.COHERENCE_MIN):
                rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None, None], hooks={"h": (3, 4, 3)},
                          coherences=[(False, clip, 2), (True, 4, 4)])
                out = rig.run()
            self.assertEqual(len(rig.write_calls), 1, bar)                               # never the takeaway again
            self.assertFalse([p for r, p in rig.prompts if r == "angle_write" and "was refused" in p], bar)
            pk = out["package"]
            self.assertIsNotNone(pk, (bar, out.get("why_none")))
            self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"], bar)    # no closing line
            self.assertTrue(NV_FLAG_OK(pk["gates"]), (bar, pk["gates"]))

    def test_after_a_failed_verdict_only_the_clips_under_its_own_floor_are_swapped(self):
        """A clip at 3 passes the calibrated floor: when the line-up fails on another clip (2), only that one is
        dropped and swapped, never the clip at 3."""
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        rig = Rig(ms, ["h", "x", "y"], [(False, [], {"clip_01": 3, "clip_02": 2}, Rig.LINE)], [None])
        out = rig.run()
        self.assertIn("dropped ['y']", out["tried"][0]["why"])

    def test_the_mark_on_a_package_whose_two_verdicts_passed_on_the_calibrated_bar(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual((out["package"]["lineup_bar"]["note"], out["package"]["lineup_bar"]["floors"]),
                         ("line-up passed on the calibrated bar", {"clips_alone": {"clip": 3},
                                                                   "coherence": {"clip": 3, "vo_point": 3}}))
        from unittest import mock
        with mock.patch.object(PK, "_live_lineup_bar", lambda: (None, "no valid line-up calibration")):
            rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None])
            out = rig.run()
        self.assertIsNotNone(out["package"])
        self.assertNotIn("lineup_bar", out["package"])                                  # the standard bar: no mark


class TestRuling119StandAloneFloor(unittest.TestCase):
    """RULING 119 (1) (orchestrator 08:25 ET Nov 16): the clip scorer asked ALONE (the candidates path) refused four of
    PBX's approved clips (the integrator's run: 2.0 and 3.0); the candidates path's calibrated floor is the lowest an
    approved clip takes, never under 3: 3.0, for the scorer code it was measured on only. A clip affirmed only on that
    floor marks the package and its pin, outside the seal; the render's own validate (3.5) is unchanged."""

    SHA, DIGEST = "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53", "a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203"
    OPENER = "And Bitcoin is the hardest money ever made, which is why it wins."       # TestRuling56Scorer's opener

    def file(self, verdicts, sha, digest=DIGEST):
        """The integrator's file with each verdict's own weights digest (their 08:52 contract): None names none."""
        vs = {k: dict(v, **({"digest": digest} if digest else {})) for k, v in verdicts.items()}
        return TestRuling56Scorer.file(self, vs, scorer_sha=sha, digest=digest)

    def test_the_floor_affirms_from_3_only_on_the_scorer_it_was_measured_on(self):
        vs = {"a": fv(self.OPENER, 3.0), "b": fv("Bitcoin b.", 3.4), "c": fv("Bitcoin c.", 2.9), "d": fv("Bitcoin d.", 4.0)}
        idx, rec = PK.scorer_verdicts(self.file(vs, self.SHA), self.SHA)
        self.assertEqual({k: idx[k]["affirmed"] for k in "abcd"}, {"a": True, "b": True, "c": False, "d": True})
        self.assertEqual({k: idx[k].get("bar") for k in "abcd"}, {"a": "calibrated", "b": "calibrated", "c": None,
                                                                  "d": None})
        self.assertEqual((idx["a"]["affirmed_render"], idx["a"]["floor"], idx["d"]["affirmed_render"]), (False, 3.0, True))
        self.assertEqual((rec["affirmed"], rec["affirmed_on_the_floor"]), (3, 2))
        other = "s" * 64                                                 # other scorer code: the render's own 3.5
        idx, rec = PK.scorer_verdicts(self.file(vs, other), other)
        self.assertEqual({k: idx[k]["affirmed"] for k in "abcd"}, {"a": False, "b": False, "c": False, "d": True})
        self.assertEqual(rec["affirmed_on_the_floor"], 0)
        for digest in (None, "f" * 64, "a418f5838eaf"):                  # other weights, a bare prefix, none: 3.5 only
            idx, rec = PK.scorer_verdicts(self.file(vs, self.SHA, digest), self.SHA)
            self.assertEqual((idx["a"]["affirmed"], idx["b"]["affirmed"], rec["affirmed_on_the_floor"]), (False, False, 0))

    def test_the_pin_check_accepts_a_floor_affirmation_only_whole(self):
        idx, _ = PK.scorer_verdicts(self.file({"a": fv(self.OPENER, 3.0)}, self.SHA), self.SHA)
        seg = {"text": self.OPENER, "scorer_verdict": idx["a"]}
        self.assertTrue(package_pin.affirmed_verdict(seg))
        self.assertEqual(package_pin.scorer_problems([{"text": "Bitcoin."}, seg]), [])
        for k, val in (("bar", None), ("floor", 2.5), ("score", 2.9), ("scorer_sha", "s" * 64), ("threshold", 3.0),
                       ("digest", None), ("digest", "f" * 64), ("digest", "a418f5838eaf")):
            v = dict(idx["a"], **{k: val}) if val is not None else {x: y for x, y in idx["a"].items() if x != k}
            self.assertFalse(package_pin.affirmed_verdict(dict(seg, scorer_verdict=v)), k)

    def test_a_clip_affirmed_on_the_floor_marks_the_package_and_the_pin_outside_the_seal(self):
        import copy
        import test_angles as TA
        idx, _ = PK.scorer_verdicts(self.file({"a": fv(self.OPENER, 3.0), "d": fv("Bitcoin d.", 4.0)}, self.SHA),
                                    self.SHA)
        segs = [{"text": "Bitcoin d.", "scorer_verdict": idx["d"]}, {"text": self.OPENER, "scorer_verdict": idx["a"]}]
        m = PK.stand_alone_mark(segs)
        self.assertEqual((m["note"], m["floor"], m["segments"], m["ruling"]),
                         ("a clip passed stand-alone on the calibrated bar", 3.0, [1], "119"))
        self.assertIsNone(PK.stand_alone_mark(segs[:1]))                # every affirmation on the render's own bar
        base = TA.TestPinAndTruth.pk(None)
        plain = package_pin.to_pin(copy.deepcopy(base), "r")["moments_package"]
        marked = package_pin.to_pin(dict(copy.deepcopy(base), stand_alone_bar=m), "r")["moments_package"]
        self.assertNotIn("stand_alone_bar", plain)
        self.assertEqual(marked["stand_alone_bar"]["note"], "a clip passed stand-alone on the calibrated bar")
        self.assertEqual(marked["package_sha256"], plain["package_sha256"])        # outside the seal


class TestRuling117JoinSearch(unittest.TestCase):
    """RULING 117 (orchestrator 16:24 ET Nov 15), SEARCH, DO NOT LOOSEN: the join table (the clips-alone verdict's own
    join question once per ordered pair of an angle's moments, Grok, cached) and the line-ups chosen BY SEARCH over it
    (hook first, 2-4 clips in every order, the rules as now, at most one flagged join); the verdicts still decide."""

    def canned(self, *replies):
        c = Canned(coherence_verdict=list(replies))
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        c.backends = {"fake:coherence_verdict": B("fake", "fake")}
        return c

    @staticmethod
    def all_pairs(prompt, followable=True):
        ids = re.findall(r'PAIR id="(p\d+)"', prompt)
        return {"pairs": {p: {"followable": followable, "why": "w"} for p in ids}}

    def test_the_question_is_the_clips_alone_verdicts_own(self):
        self.assertIn(PK.JOIN_QUESTION, " ".join(PK.MEDLEY_PROMPT.split()))   # ONE join question
        self.assertIn(PK.JOIN_QUESTION, PK.JOINS_PROMPT)

    def test_once_per_ordered_pair_the_hook_never_second_batched_and_cached(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        prompts = []
        c = self.canned()
        import providers as P

        def call(role, prompt, *a, **k):
            prompts.append(prompt)
            c.calls.append((role, k.get("avoid_vendor"), k.get("avoid_family"), k.get("kind")))
            return P.Reply(json.dumps(self.all_pairs(prompt)), "fake:coherence_verdict", "fake")
        c.call = call
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "JOIN_CACHE.json")
            got, err = PK.join_table(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertIsNone(err)
            self.assertEqual(sorted(got), [("h", "x"), ("h", "y"), ("x", "y"), ("y", "x")])   # 4 pairs, no (.., h)
            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"}, "joins")])   # one call
            self.assertIn(PK.JOIN_QUESTION, prompts[0])
            again, err = PK.join_table(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual((err, len(again), all(x["cached"] for x in again.values())), (None, 4, True))   # no call
            prompts.clear()
            c.calls.clear()
            new = [ms[0], dict(ms[1], text="Bitcoin is a new text now."), ms[2]]
            got, _ = PK.join_table(c, new, ctx(), set(), set(), cache=cache)
            self.assertEqual(len(re.findall(r'PAIR id=', prompts[0])), 3)       # only the pairs with the new text
        big = [pm(f"m{i}", chr(65 + i), 10.0) for i in range(9)]
        prompts.clear()
        c.calls.clear()
        got, _ = PK.join_table(c, big, ctx(), set(), set())
        self.assertEqual((len(got), len(prompts)), (49, 2))                     # 8 moments: 49 pairs in 25 + 24

    def test_a_chunk_out_of_contract_has_no_entries_and_the_others_are_still_asked(self):
        big = [pm(f"m{i}", chr(65 + i), 10.0) for i in range(8)]
        import providers as P
        c, n = self.canned(), [0]

        def call(role, prompt, *a, **k):
            n[0] += 1
            if n[0] == 1:
                raise P.ProviderError("coherence_verdict: every back-end unavailable")
            return P.Reply(json.dumps(self.all_pairs(prompt, False)), "fake:coherence_verdict", "fake")
        c.call = call
        got, err = PK.join_table(c, big, ctx(), set(), set())
        self.assertEqual((len(got), "ProviderError" in err), (24, True))       # the second chunk only
        self.assertTrue(all(x["followable"] is False for x in got.values()))

    def moments(self):
        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
        return {m["moment_id"]: m for m in (h, pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 6.0))}

    def test_the_search_every_order_the_rules_and_at_most_one_flagged_join(self):
        by = self.moments()
        a = angle(["h", "x", "y", "z"], "h")
        T = lambda ok: {"followable": ok}
        table = {(p, q): T(True) for p in "hxyz" for q in "xyz" if p != q}
        table[("h", "x")] = T(False)
        table[("x", "y")] = T(False)                                          # the writer's order: two flagged
        got = PK.search_lineups(a, by, table)
        self.assertTrue(got)
        best = [m["moment_id"] for m in got[0]]
        self.assertEqual(best[0], "h")                                       # the hook first
        ids = [[m["moment_id"] for m in s] for s in got]
        self.assertNotIn(["h", "x", "y", "z"], ids)                          # two flagged: never offered
        for s in ids:
            self.assertLessEqual(sum(table.get((p, q), {}).get("followable") is not True for p, q in zip(s, s[1:])), 1)
            self.assertTrue(PK.lineup_ok([by[i] for i in s])[0])              # the rules as now
            self.assertNotIn("z", s[1:-1])                                    # z is short (6 s): only last
        self.assertEqual(sum(table.get((p, q), {}).get("followable") is not True for p, q in zip(best, best[1:])), 0)
        del table[("y", "z")]                                                # no answer counts as flagged
        self.assertTrue(all(sum((p, q) == ("y", "z") or table.get((p, q), {}).get("followable") is not True
                                for p, q in zip(s, s[1:])) <= 1 for s in
                            [[m["moment_id"] for m in x] for x in PK.search_lineups(a, by, table)]))
        judged = {tuple(best)}
        self.assertNotIn(best, [[m["moment_id"] for m in s] for s in PK.search_lineups(a, by, table, judged=judged)])
        self.assertFalse([s for s in PK.search_lineups(a, by, table, dropped=frozenset({"x", "y"}))])   # 1 clip left
        bp = {("h", "y")}                                                    # a verdict flagged it: it counts
        for s in [[m["moment_id"] for m in x] for x in PK.search_lineups(a, by, table, bad_pairs=bp)]:
            n_bad = sum((p, q) in bp or table.get((p, q), {}).get("followable") is not True for p, q in zip(s, s[1:]))
            self.assertLessEqual(n_bad, 1)

    def test_an_unanswered_pair_and_a_verdicts_flag_each_count_as_flagged(self):
        by = dict(self.moments(), z=pm("z", "D", 13.0))
        a = angle(["h", "x", "y", "z"], "h")
        table = {(p, q): {"followable": True} for p in "hxyz" for q in "xyz" if p != q}
        ids = lambda got: [[m["moment_id"] for m in s] for s in got]
        self.assertEqual(ids(PK.search_lineups(a, by, table))[0], ["h", "x", "y"])   # the writer's order first
        t2 = dict(table)
        t2[("h", "x")] = {"followable": False}
        del t2[("x", "y")]                                                   # no answer for x -> y
        self.assertNotIn(["h", "x", "y"], ids(PK.search_lineups(a, by, t2)))       # flagged + unanswered: 2
        self.assertNotIn(["h", "x", "y"], ids(PK.search_lineups(a, by, table, bad_pairs={("h", "x"), ("x", "y")})))

    def test_the_search_prefers_higher_known_ratings(self):
        by = dict(self.moments(), z=pm("z", "D", 13.0))                      # z long enough to stand in for y
        a = angle(["h", "x", "y", "z"], "h")
        table = {(p, q): {"followable": True} for p in "hxyz" for q in "xyz" if p != q}
        got = PK.search_lineups(a, by, table, ratings={"x": 5, "y": 2}, floor=3)
        self.assertNotIn("y", [m["moment_id"] for m in got[0]])              # a 2 ranks below the unknown z

    def test_a_build_asks_the_searchs_line_up_first_and_records_the_agreement(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        joins = {("h", "x"): False, ("x", "y"): False, ("h", "y"): True, ("y", "x"): True}
        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins=joins)
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "y", "x"]])                  # the table's order, not the writer's
        self.assertEqual(rig.join_calls, [["h", "x", "y"]])
        self.assertEqual(out["tried"][0]["join_table_vs_verdict"],
                         {"hook -> clip_01": {"table": True, "verdict": True},
                          "clip_01 -> clip_02": {"table": True, "verdict": True}})
        self.assertEqual(out["join_agreement"], {"joins": 2, "agree": 2, "table_unanswered": 0})
        self.assertEqual(out["join_tables"][0]["moments"], ["h", "x", "y"])
        self.assertIsNotNone(out["package"])

    def test_after_a_failed_verdict_the_search_gives_the_next_line_up(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
                                             (True, [], None, Rig.LINE)], [None], joins=joins)
        out = rig.run()
        first, second = rig.medley_calls                                      # the search's shortest first: h x y
        self.assertEqual(first, ["h", "x", "y"])
        self.assertIn("ruling 117", out["tried"][0]["why"])
        flagged = {("h", "x"), ("x", "y")}                                    # the verdict's flags count as flagged
        self.assertEqual(sum(p in flagged for p in zip(second, second[1:])), 0)   # the next has neither
        self.assertIsNotNone(out["package"])

    def test_the_cache_answers_only_for_todays_joins_list(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0)]
        import providers as P
        c = self.canned()
        c.call = lambda role, prompt, *a, **k: (c.calls.append(role), P.Reply(
            json.dumps(self.all_pairs(prompt)), "fake:coherence_verdict", "fake"))[1]
        c.chain = lambda role, kind=None: ["fake:coherence_verdict"]
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "JOIN_CACHE.json")
            PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
            c.calls.clear()
            got, _ = PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
            self.assertEqual((c.calls, got[("h", "x")]["cached"]), ([], True))     # on the list: served
            c.chain = lambda role, kind=None: ["xai:another-rater"]
            got, _ = PK.join_table(c, ms, ctx(), set(), set(), cache=cache)
            self.assertEqual((len(c.calls), got[("h", "x")]["cached"]), (1, False))   # off it: asked again

    def test_a_clip_under_the_verdicts_floor_leaves_the_search(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_01": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None], joins=joins)
        out = rig.run()
        first, second = rig.medley_calls
        self.assertEqual(first[1], "x")                                      # x rated 2 on the calibrated bar
        self.assertNotIn("x", second)                                         # out of every later line-up
        self.assertIn("ruling 117", out["tried"][0]["why"])

    def test_clips_under_a_verdicts_floor_never_come_back_when_the_search_runs_out(self):
        """x, then y, rated 2: each leaves the search; with neither, no line-up of 2-4 clips is left, so no third
        verdict is asked (with them kept, the search would ask a line-up holding a clip already rated 2)."""
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        joins = {(p, q): True for p in "hxyz" for q in "xyz" if p != q}
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_01": 2}, Rig.LINE), (False, [], {"clip_01": 2}, Rig.LINE),
                                             (True, [], None, Rig.LINE)], [None], joins=joins)
        rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "z"]])

    def test_the_tables_moments_are_the_hook_its_writers_picks_then_the_cleared_pool(self):
        """The order's set: the hook and the clips that passed step A from both vendors, the second pass and CUTTABLE
        (the cleared pool), at most 8: the writer's own moments first, then the pool by rank score."""
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("w", "D", 13.0)]
        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins={})
        rig.run()
        self.assertEqual(rig.join_calls, [["h", "x", "y", "w"]])
        big = [pm("h", "A", 12.0)] + [pm(f"m{i}", chr(66 + i), 10.0) for i in range(9)]
        rig = Rig(big, ["h", "m0", "m1"], [(True, [], None, Rig.LINE)], [None], joins={})
        rig.run()
        self.assertEqual((len(rig.join_calls[0]), rig.join_calls[0][:3]), (8, ["h", "m0", "m1"]))

    def test_the_table_holds_only_moments_that_can_stand_beside_the_hook_a_new_channel_first(self):
        """The 16:54 replay: never the hook's own video, never a clip-ineligible moment; after the writer's picks, a
        moment of a channel not yet in the set comes before a second moment of a channel already in it, whatever their
        rank scores."""
        ms = [pm("h", "A", 12.0, vid="V1"), pm("x", "B", 14.0), pm("y", "C", 13.0),
              pm("a2", "A", 13.0, rank=99.0, vid="V1"),                       # the hook's own video: never
              pm("n", "E", 13.0, rank=99.0, clip=False),                      # not clip-eligible: never
              pm("b2", "B", 13.0, rank=50.0),                                 # B is in the set already: after...
              pm("d", "D", 13.0, rank=1.0),                                   # ...the new channel D
              pm("e1", "E", 13.0, rank=90.0), pm("e2", "E", 13.0, rank=80.0)]   # E: its first new, its second not
        rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins={})
        rig.run()
        self.assertEqual(rig.join_calls, [["h", "x", "y", "e1", "d", "e2", "b2"]])

    def test_the_writers_own_picks_join_the_table_only_when_they_can_stand_beside_the_hook(self):
        c = {m["moment_id"]: m for m in [pm("h", "A", 12.0, vid="V1"), pm("w", "A", 13.0, vid="V1"),
                                         pm("z", "C", 13.0, clip=False), pm("x", "D", 13.0), pm("q", "E", 13.0)]}
        angle = {"hook": "h", "moments": ["h", "w", "z", "x"]}
        self.assertEqual(PK.join_moments(angle, c), ["h", "x", "q"])
        self.assertEqual(PK.join_moments(angle, c, doomed={"x"}), ["h", "q"])            # a doomed moment: never

    def test_a_moment_doomed_in_an_earlier_angle_never_joins_a_later_angles_table(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0), pm("w", "E", 14.0)]
        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "z", "w"]], [(True, [], None, Rig.LINE)] * 2, [None, None],
                  excluded={"x"}, joins={})
        out = rig.run()
        self.assertIn("'x': 'exclusion'", out["tried"][0]["why"])                     # angle 1 dooms x
        self.assertEqual(rig.join_calls, [["h", "x", "y", "w", "z"], ["h", "z", "w", "y"]])   # equal ranks: by id

    def test_no_table_or_an_empty_one_is_the_build_as_before(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        for joins in (None, {}):
            rig = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], joins=joins)
            out = rig.run()
            self.assertEqual(rig.medley_calls, [["h", "x", "y"]])              # the writer's order
            self.assertNotIn("join_agreement", out)


class TestRuling56Scorer(unittest.TestCase):
    """RULING 56 (09:59): the render's own STAND_ALONE clip scorer, asked at the pin stage by the integrator's service
    about every moment left out as an opener it would have to affirm, untrimmed and trimmed; only what it affirms is
    sealed. Their verdicts file is read only and fail closed."""

    OPENER = "And Bitcoin is the hardest money ever made, which is why it wins."

    def file(self, verdicts=None, drop=(), **scorer):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=".json")
        sc = {k: x for k, x in dict({"model": "gemma3:27b", "kind": "moments", "rubric": "ruling 60: stand-alone only",
                                     "threshold": 3.5, "event": None, "scorer_sha": "s" * 64}, **scorer).items()
              if k not in drop}
        with os.fdopen(fd, "w") as f:
            json.dump({"rated_at": "2026-11-13T15:35:10Z", "build": "b", "candidates_generated_at": "g",
                       "scorer": sc, "verdicts": verdicts or {}}, f)
        self.addCleanup(os.remove, path)
        return path

    def test_the_verdicts_file_is_used_only_when_every_check_holds(self):
        good = {"a": fv(self.OPENER, 4.0), "b": fv("Bitcoin b.", 3.0, "ends_mid_thought")}
        idx, rec = PK.scorer_verdicts(self.file(good), "s" * 64)
        self.assertEqual(sorted(idx), ["a", "b"])
        self.assertEqual((rec["read"], rec["verdicts"], rec["affirmed"]), (True, 2, 1))
        self.assertEqual((idx["a"]["affirmed"], idx["b"]["affirmed"]), (True, False))
        self.assertEqual((idx["a"]["kind"], idx["a"]["event"], idx["a"]["scorer_sha"], idx["a"]["threshold"]),
                         ("moments", None, "s" * 64, 3.5))
        for scorer, code, why in (({"kind": "story"}, "s" * 64, "a kind other than 'moments' (ruling 60)"),
                                  ({"event": "Pinned: bitcoin"}, "s" * 64,
                                   "an event (ruling 60: a moments verdict carries none)"),
                                  ({}, "t" * 64, "a scorer_sha that is not the render's scorer code now"),
                                  ({}, None, "the render's scorer code could not be read"),
                                  ({"threshold": 3.0}, "s" * 64, "another threshold"),
                                  ({"threshold": True}, "s" * 64, "another threshold")):
            idx, rec = PK.scorer_verdicts(self.file(good, **scorer), code)
            self.assertEqual((idx, rec["read"], rec["why"]), ({}, False, why))
        idx, rec = PK.scorer_verdicts(self.file(good, drop=("event",)), "s" * 64)   # "event": null, never absent
        self.assertEqual((idx, rec["why"]), ({}, "an event (ruling 60: a moments verdict carries none)"))
        idx, rec = PK.scorer_verdicts(self.file({"f": fv("x", 4.0, "starts_mid_thought")}), "s" * 64)
        self.assertTrue(idx["f"]["affirmed"])                           # ruling 60: the score alone
        idx, rec = PK.scorer_verdicts("/nonexistent/latest.json", "s" * 64)
        self.assertEqual((idx, rec["read"], rec["path"], rec["render_scorer_sha"]),
                         ({}, False, "/nonexistent/latest.json", "s" * 64))
        self.assertTrue(rec["why"].startswith("open: FileNotFoundError"))   # audit 1138 C2: what failed, and where
        odd_shape = self.file()
        with open(odd_shape, "w") as f:
            json.dump({"scorer": {"kind": "moments", "event": None, "scorer_sha": "s" * 64, "threshold": 3.5}}, f)
        idx, rec = PK.scorer_verdicts(odd_shape, "s" * 64)                # no "verdicts" key
        self.assertEqual((idx, rec["kind"], rec["scorer_sha"]), ({}, "moments", "s" * 64))
        self.assertTrue(rec["why"].startswith("shape: KeyError"))
        with open(odd_shape, "w") as f:                                  # audit 1138b C1 (qwen, glm): a "scorer"
            json.dump({"scorer": ["moments"], "verdicts": {}}, f)        # that is not an object
        idx, rec = PK.scorer_verdicts(odd_shape, "s" * 64)
        self.assertEqual((idx, rec["read"], "kind" in rec), ({}, False, False))
        self.assertTrue(rec["why"].startswith("shape: AttributeError"))
        bad = self.file()
        with open(bad, "w") as f:
            f.write("{not json")
        self.assertEqual(PK.scorer_verdicts(bad, "s" * 64)[0], {})
        odd = {"e": dict(fv("x", 4.0), error="not rated"), "n": dict(fv("x", 4.0), score=None),
               "t": dict(fv("x", 4.0), score=True), "d": dict(fv("x", 3.0), affirmed=True),
               "s": dict(fv("x", 4.0), text_sha256=None)}
        idx, rec = PK.scorer_verdicts(self.file(odd), "s" * 64)
        self.assertEqual(idx, {})                                       # none of them is a verdict
        self.assertEqual(rec["disagree_with_the_rule"], ["d"])          # "affirmed" against the render's own rule

    def test_the_scorer_sha_is_recomputed_from_the_renders_code(self):
        import hashlib
        import tempfile
        self.assertEqual(PK.RENDER_SCORER_CODE, ("/home/ultron/protocol_pulse/pipeline/stand_alone.py",
                                                 "/home/ultron/protocol_pulse/pipeline/story_semantics.py"))
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.py"), os.path.join(d, "b.py")
            for path, data in ((a, b"one"), (b, b"two")):
                with open(path, "wb") as f:
                    f.write(data)
            self.assertEqual(PK.render_scorer_sha((a, b)), hashlib.sha256(b"onetwo").hexdigest())
            self.assertIsNone(PK.render_scorer_sha((a, os.path.join(d, "missing.py"))))

    def test_a_verdict_attaches_only_to_its_own_text(self):
        m = dict(pm("a", "A", 12.0), text=self.OPENER)
        got = PK.with_verdict(m, {"a": sv(self.OPENER, 4.0)})
        self.assertIs(PK.verdict_of(got), got["scorer_verdict"])
        self.assertNotIn("scorer_verdict", PK.with_verdict(m, {"a": sv("Another text.", 4.0)}))
        self.assertNotIn("scorer_verdict", PK.with_verdict(m, {"b": sv(self.OPENER, 4.0)}))
        trimmed = dict(got, moment_id="a~trim", text=self.OPENER[len("And "):])   # carries the key, not the verdict
        self.assertIsNone(PK.verdict_of(trimmed))
        self.assertNotIn("scorer_verdict", PK.with_verdict(trimmed, {"a": sv(self.OPENER, 4.0)}))

    def test_an_affirmed_opener_plays_as_a_clip_never_as_the_hook(self):
        m = dict(pm("a", "A", 12.0), text=self.OPENER, hook_onset={"pass": True})
        self.assertIn("with no clip scorer", PK.no_role_on_screen(m))
        ok = dict(m, scorer_verdict=sv(self.OPENER, 4.0))
        self.assertIsNone(PK.no_role_on_screen(ok))
        why = PK.no_role_on_screen(dict(m, scorer_verdict=sv(self.OPENER, 3.0, "ends_mid_thought")))
        self.assertIn("with the clip scorer's verdict", why)
        self.assertIn("does not affirm", why)
        self.assertIsNone(PK.no_role_on_screen(dict(m, scorer_verdict=sv(self.OPENER, 4.0, "starts_mid_thought"))))
        self.assertTrue(ok["eligibility"]["hook"]["ok"])               # hook-eligible (L-o: a conjunction is a target)
        self.assertEqual(PK.placement(ok), " | cannot open (never the hook)")   # but the render's hook rule refuses
        self.assertEqual(PK.placement(dict(ok, duration_s=6.0)), " | under 8 s: only the LAST clip")
        hook, x = dict(pm("h", "B", 12.0), hook_onset={"pass": True}), dict(pm("x", "C", 13.0), hook_onset={"pass": True})
        r = PK.stand_alone_check([hook, ok, x])
        self.assertTrue(r["ok"], r["rows"])
        self.assertIn("the clip scorer affirms it stands alone", r["rows"][1]["opener"]["why"])
        self.assertFalse(PK.stand_alone_check([ok, hook, x])["ok"])    # never the hook
        by = {y["moment_id"]: y for y in (ok, hook, x, dict(pm("y", "D", 13.0), hook_onset={"pass": True}))}
        segs = PK.lineup_for(angle(["a", "h", "x", "y"], "a"), by, need_onset=True, need_stand_alone=True)
        self.assertNotEqual(segs[0]["moment_id"], "a")                  # the proposer's hook gives way ...
        self.assertIn("a", [y["moment_id"] for y in segs])             # ... and it plays as a clip

    def test_the_build_admits_only_what_the_scorer_affirms(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), dict(pm("b", "E", 13.0), text=self.OPENER)]
        rig = Rig(ms, ["h", "b", "x", "y"], [(True, [], None, Rig.LINE)], [None], verdicts={"b": fv(self.OPENER, 4.0)})
        out = rig.run()
        self.assertNotIn("b", out["no_role"])
        self.assertEqual((out["scorer"]["read"], out["scorer"]["admitted"]), (True, ["b"]))
        self.assertIn("id=b | E | 13.0 s | cannot open (never the hook) | ",
                      next(p for r, p in rig.prompts if r == "angle_write"))
        seg = next(s for s in out["package"]["segments"] if s["moment_id"] == "b")      # it plays, as a clip,
        self.assertTrue(package_pin.affirmed_verdict(seg))                                # its affirmation sealed
        self.assertNotEqual(out["package"]["segments"][0]["moment_id"], "b")
        refused = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None],
                      verdicts={"b": fv(self.OPENER, 3.0, "ends_mid_thought")}).run()
        self.assertIn("with the clip scorer's verdict", refused["no_role"]["b"])
        self.assertEqual(refused["scorer"]["admitted"], [])
        none = Rig(ms, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None]).run()     # no verdicts: as before 56
        self.assertIn("with no clip scorer", none["no_role"]["b"])
        self.assertEqual(none["scorer"]["why"], "no verdicts file given")

    def test_a_trimmed_variant_needs_the_affirmation_before_any_vendor_call(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
              dict(pm("b", "E", 13.0), text="But Bitcoin x.")]
        v = dict(ms[4], moment_id="b~trim", text="Bitcoin x.", trimmed_leading="But", untrimmed_start=0.0)
        saved, outs = PK.trim_variant, {}
        try:
            PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
            for k, vs in (("none", None), ("refused", {"b~trim": fv("Bitcoin x.", 3.0, "ends_mid_thought")}),
                          ("affirmed", {"b~trim": fv("Bitcoin x.", 4.0)})):
                rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], verdicts=vs)
                outs[k] = (rig, rig.run())
        finally:
            PK.trim_variant = saved
        for k in ("none", "refused"):
            rig, out = outs[k]
            self.assertEqual(out["trimmed"], {}, k)
            self.assertFalse(any("b~trim" in ids for _, ids in rig.screens), k)     # never sent to step A
        self.assertIn("no clip-scorer verdict on the trimmed text yet", outs["none"][1]["scorer"]["trims_out"]["b"])
        self.assertIn("does not affirm", outs["refused"][1]["scorer"]["trims_out"]["b"])
        rig, out = outs["affirmed"]
        self.assertEqual((out["trimmed"], out["scorer"]["trims_affirmed"]), ({"b": "b~trim"}, ["b"]))
        self.assertTrue(any("b~trim" in ids for _, ids in rig.screens))

    def test_the_candidates_file_asks_about_every_opener_left_out_and_changes_only_with_its_set(self):
        import tempfile
        but, srcs = TestRuling33TrimAtThePinStage().moment(
            "But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
        opener = dict(pm("o", "B", 12.0), text=self.OPENER)
        gold = dict(pm("g", "C", 12.0), text="And gold is the hardest money ever made, which is why it wins.")
        plain = pm("p", "D", 12.0)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "candidates.json")

            def load():
                with open(path) as f:
                    return json.load(f)
            r = PK.scorer_pass([but, opener, gold, plain], srcs, ctx(), None, path, "ledger_test")
            self.assertEqual((r["index"], r["record"]["read"], r["record"]["candidates_written"]), ({}, False, True))
            doc = load()
            self.assertEqual((doc["build"], doc["kind"]), ("ledger_test", "moments"))   # ruling 60: no event
            got = {c["pid"]: c for c in doc["candidates"]}
            self.assertEqual(sorted(got), ["o", "t", "t~trim"])           # gold fails the topic rule: never asked
            for pid, c in got.items():
                self.assertEqual(c["text_sha256"], PK.text_sha(c["text"]), pid)
                self.assertEqual(set(c), {"pid", "video_id", "channel", "duration", "text", "text_sha256",
                                          "trimmed_leading"})
            self.assertEqual((got["t~trim"]["trimmed_leading"], got["o"]["trimmed_leading"]), ("But", None))
            self.assertTrue(got["t~trim"]["text"].startswith("Bitcoin has rarely"))
            gen = doc["generated_at"]
            r = PK.scorer_pass([but, dict(opener, scorer_verdict=sv(self.OPENER, 4.0)), gold, plain], srcs, ctx(),
                               None, path, "ledger_test2")                # a verdict attached changes nothing asked
            self.assertFalse(r["record"]["candidates_written"])
            self.assertEqual(load()["generated_at"], gen)
            r = PK.scorer_pass([but, plain], srcs, ctx(), None, path, "ledger_test3")
            self.assertTrue(r["record"]["candidates_written"])
            self.assertEqual(sorted(c["pid"] for c in load()["candidates"]), ["t", "t~trim"])
            self.assertFalse(os.path.exists(path + ".tmp"))
        self.assertTrue(PK.SCORER_CANDIDATES.endswith("docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json"))

    def test_the_pin_holds_the_affirmation_to_its_text(self):
        import stand_alone as SA
        self.assertEqual(package_pin.SCORER_MIN, SA.CLIP_MIN_SCORE)
        s = {"approved_text": self.OPENER, "scorer_verdict": sv(self.OPENER, 4.0)}
        self.assertTrue(package_pin.affirmed_verdict(s))
        self.assertTrue(package_pin.affirmed_verdict({"text": self.OPENER, "scorer_verdict": sv(self.OPENER, 4.0)}))
        for bad in (dict(sv(self.OPENER, 4.0), affirmed=False), sv(self.OPENER, 3.0),
                    dict(sv(self.OPENER, 4.0), kind="story"), dict(sv(self.OPENER, 4.0), threshold=3.0),
                    dict(sv(self.OPENER, 4.0), score="4"), dict(sv(self.OPENER, 4.0), scorer_sha=""),
                    dict(sv(self.OPENER, 4.0), event="Pinned: bitcoin"),
                    {k: x for k, x in sv(self.OPENER, 4.0).items() if k != "event"},
                    sv(self.OPENER + " ", 4.0), None, "affirmed"):
            self.assertFalse(package_pin.affirmed_verdict(dict(s, scorer_verdict=bad)), bad)
        self.assertTrue(package_pin.affirmed_verdict(dict(s, scorer_verdict=sv(self.OPENER, 4.0, "starts_mid_thought"))))
        self.assertTrue(SA.affirmed(4.0, "starts_mid_thought", moments=True))        # the render's own module,
        self.assertFalse(SA.affirmed(4.0, "starts_mid_thought"))                     # ruling 60's moments rule;
        self.assertFalse(SA.affirmed(3.4, "none", moments=True))                     # the story path unchanged
        segs = [{"approved_text": "Bitcoin is money."}, {"approved_text": self.OPENER},
                {"approved_text": "Yeah, Bitcoin is money."},
                {"approved_text": "Bitcoin x.", "scorer_verdict": sv("Bitcoin y.", 4.0)}]
        self.assertEqual([x.split(":")[0] for x in package_pin.scorer_problems(segs)],
                         ["segment 1", "segment 2", "segment 3"])
        for i, t in ((1, self.OPENER), (2, "Yeah, Bitcoin is money."), (3, "Bitcoin x.")):
            segs[i]["scorer_verdict"] = sv(t, 4.0)
        self.assertEqual(package_pin.scorer_problems(segs), [])
        self.assertEqual(package_pin.scorer_problems([{"approved_text": self.OPENER}]), [])   # a hook: the gate's
        import hashlib
        t = "And Bitcoin\u2019s caf\u00e9 \u2014 na\u00efve \u201choldlers\u201d win \U0001F680"   # audit 1138 C2 (glm
        self.assertTrue(package_pin.affirmed_verdict({"approved_text": t, "scorer_verdict": sv(t, 4.0)}))   # P2-2):
        self.assertEqual(PK.text_sha(t), hashlib.sha256(t.encode("utf-8")).hexdigest())   # one sha, build and pin


class TestRulings6264Search(unittest.TestCase):
    """RULINGS 62-64 (12:00): the last clip retried away before any swap; joins before swaps (the same clips
    reordered); an angle for every passing hook; the budget counts JUDGED line-ups (an identical one is free)."""

    def fresh(self, mid, ch, dur, hours_ago=6.0):
        return dict(pm(mid, ch, dur), published_at=(NOW - timedelta(hours=hours_ago)).isoformat())

    def test_ruling_62_only_the_last_clip_fails_and_the_floor_holds(self):
        ms = [self.fresh("h", "A", 12.0), self.fresh("x", "B", 14.0), self.fresh("y", "C", 13.0),
              self.fresh("z", "D", 9.0, hours_ago=1.0)]                      # z is fresh: the 4-clip line-up first
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_03": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y", "z"], ["h", "x", "y"]])   # 39 s >= the 36.7 s floor
        self.assertIn("ruling 62", out["tried"][0]["why"])
        self.assertIsNotNone(out["package"])

    def test_ruling_62_only_with_a_hook_on_its_calibrated_bar(self):
        """RULING 115: 'only the last clip fails' needs the line-up's own hook on its calibrated bar (its slot is never
        COHERENCE_MIN's: a scroll-3 hook at every floor counts as passing)."""
        segs = [dict(pm("h", "A", 12.0), hook_rating={"scroll": 3, "alone": 4, "setup": 3, "backend": "xai:grok"}),
                pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 9.0)]
        med = dict(verdict(PK.labels(4), ratings={"hook": 3, "clip_03": 2}), measured=True, flagged=[])
        self.assertTrue(PK.last_clip_only(segs, med))
        for hr in ({"scroll": 5, "alone": 3, "setup": 5, "backend": "xai:grok"},
                   {"scroll": 5, "alone": 5, "setup": 5, "backend": "heimdall:qwen/qwen3.8-27b"}, None):
            bad = [dict(segs[0], hook_rating=hr), *segs[1:]]
            self.assertFalse(PK.last_clip_only(bad, med), hr)                 # the hook fails: never "only the last"
        self.assertFalse(PK.last_clip_only(segs, dict(med, clips=dict(med["clips"], clip_01=3))))   # two clips fail

    def test_ruling_62_under_the_floor_swaps_as_now(self):
        ms = [self.fresh("h", "A", 12.0), self.fresh("x", "B", 10.0), self.fresh("y", "C", 10.0),
              self.fresh("z", "D", 9.0)]                                    # without z: 32 s, under 36.7
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"clip_03": 2}, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(len(rig.medley_calls), 1)
        self.assertNotIn("ruling 62", out["tried"][0]["why"])
        self.assertIn("the clips alone fail", out["tried"][0]["why"])

    def test_ruling_63_two_flagged_joins_reorder_the_same_clips_first(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE),
                                        (True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "x"]])   # the hook first, no clip dropped
        self.assertIn("ruling 63", out["tried"][0]["why"])
        self.assertIsNotNone(out["package"])

    def test_reorder_avoids_the_known_unfollowable_pairs_and_moves_least(self):
        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})          # it can open (G17a)
        segs = [h, pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0)]
        got = PK.reorder(segs, {("h", "x"), ("y", "z")}, {("h", "x", "y", "z")})
        self.assertEqual([m["moment_id"] for m in got], ["h", "y", "x", "z"])
        two = [h, pm("x", "B", 14.0), pm("y", "C", 13.0)]
        self.assertIsNone(PK.reorder(two, {("h", "y"), ("y", "x"), ("h", "x"), ("x", "y")}, set()))   # no order helps
        short = [dict(h, duration_s=14.0, end=14.0), pm("x", "B", 14.0), pm("s", "C", 7.0), pm("y", "D", 9.0)]
        got = PK.reorder(short, {("x", "s")}, {("h", "x", "s", "y")})
        self.assertEqual(got[-1]["moment_id"], "s")                         # a short clip plays only LAST

    def test_ruling_64_a_passing_hook_left_without_an_angle_is_asked_for(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("g", "D", 12.0), pm("z", "E", 13.0)]
        rig = Rig(ms, [["h", "x", "y"]], [(False, [], None, "none"), (True, [], None, Rig.LINE)], [None],
                  hooks={"h": (5, 5, 5), "g": (5, 5, 5)},
                  follow_up={"angles": [angle(["g", "x", "z"], "g")]})
        out = rig.run()
        self.assertEqual(out["angle_follow_up"]["hooks"], ["g"])
        follow = [p for r, p in rig.prompts if r == "angle_write"][1]
        self.assertIn("id=g | rated 5", follow)
        self.assertNotIn("id=h | rated", follow)                           # written for exactly the hook left out
        self.assertEqual([c[0] for c in rig.medley_calls], ["h", "g"])     # the second hook is tried
        self.assertIsNotNone(out["package"])
        self.assertEqual([a["hook"] for a in PK.allot([angle(["a", "b", "c"], "a")] * 3 +
                                                       [angle(["b", "a", "c"], "b")], 1)], ["a", "b"])

    def test_the_budget_counts_judged_line_ups_and_an_identical_one_is_free(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "y"]], [(False, [], None, "none")], [None])
        out = rig.run()
        self.assertEqual(len(rig.medley_calls), 1)                          # judged once
        self.assertEqual(out["search"]["lineups"], 1)
        self.assertTrue(out["tried"][1].get("verdict_again"))               # the second angle's: free


class TestRuling70Visual(unittest.TestCase):
    """RULING 70 (15:29): one contact sheet per clip; xAI first, Heimdall image models as failover; fail closed. A finding
    is sealed as a FLAG, never a reject by itself; a third_person finding may not be the HOOK (step A confirms no claim
    as reported fact: it passes only the speaker's own view)."""
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
    TP = {"flags": [{"kind": "third_person", "text": "a photo of a CEO beside the host", "name_on_screen": None}],
          "third_person": {"shown": True, "how": "photo", "words_negative": True, "name_on_screen": None,
                           "finding": "a photo of a CEO beside the host"}}

    def test_hooks_are_seen_before_the_angle_and_a_clean_package_seals_every_sheet(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertLess(rig.events.index("hook_ratings"), rig.events.index("angle_write"))
        self.assertEqual(rig.visual_calls[0], "h")                     # the hook, at the hook stage
        self.assertEqual(sorted(set(rig.visual_calls)), ["h", "x", "y"])
        pk = out["package"]
        self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
        self.assertEqual([sg["visual"]["sheet"]["name"] for sg in pk["segments"]],
                         ["visual_h.jpg", "visual_x.jpg", "visual_y.jpg"])
        self.assertNotIn("path", pk["segments"][0]["visual"]["sheet"])  # never a scratch path in the seal
        self.assertEqual((out["visual"]["usd_reported"], out["visual"]["usd_estimate"]), (0.006, 0.0))
        self.assertIn("visual", package_pin.MEDLEY_GATES)
        pin = package_pin.to_pin(spk(pk), "r")
        self.assertIn("visual", pin["segments"][1])
        segs = [{k: v for k, v in sg.items() if k != "visual"} for sg in pin["segments"]]
        mp = pin["moments_package"]
        self.assertNotEqual(package_pin.seal(segs, mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"],
                                             mp["gates"], mp.get("btc_screen")), mp["package_sha256"])   # sealed

    def test_a_clip_flag_is_sealed_never_a_reject(self):
        flag = {"flags": [{"kind": "on_screen_text", "text": "CEO SCANDAL", "why": "the words say no such thing"}]}
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"x": flag}).run()
        pk = out["package"]
        self.assertIsNotNone(pk)
        self.assertEqual(pk["gates"]["visual"]["status"], "PASS")
        self.assertEqual(pk["gates"]["visual"]["flags"], [dict(flag["flags"][0], segment=1)])
        self.assertEqual(pk["segments"][1]["visual"]["flags"], flag["flags"])

    def test_a_third_person_finding_may_not_open_and_no_angle_is_written_for_it(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TP})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertIn("h", out["hook_pool"]["visual_blocked"])
        self.assertIn("ruling 70", out["hook_pool"]["visual_blocked"]["h"])
        self.assertNotIn("angle_write", rig.events)                      # "no hook in the pool": nothing written
        self.assertTrue(out["why_none"].startswith("no hook in the pool"), out["why_none"])

    def test_the_line_names_the_visual_check_when_it_alone_refuses_a_hook_that_passes_the_bar(self):
        """RULING 122 (3): builds 52-54 said 'none of the 2 moments that can open passes the calibrated hook bar' for
        What Bitcoin Did's 3 / 5 / 4, which passes it; ruling 93's lower-third check had refused it."""
        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TICKER}).run()
        self.assertIn("1 of the 4 moments that can open pass the calibrated hook bar", out["why_none"])
        self.assertIn("the visual check (rulings 70 / 93) refuses each as an opener: A h: ruling 93 (1 item(s)): a ticker",
                      out["why_none"])
        self.assertNotIn("none of the", out["why_none"])
        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], hooks={"h": (2, 3, 4)}).run()    # the bar itself refuses it
        self.assertIn("none of the 4 moments that can open passes the calibrated hook bar", out["why_none"])
        self.assertNotIn("the visual check", out["why_none"])

    def test_a_third_person_clip_that_is_not_the_hook_is_kept_with_its_flag(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"y": self.TP}).run()
        self.assertIsNotNone(out["package"])
        self.assertEqual([f["kind"] for f in out["package"]["gates"]["visual"]["flags"]], ["third_person"])

    def test_an_unmeasured_clip_is_dropped_before_any_write(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
                  visuals={"y": {"measured": False, "why": "no verdict in contract after two tries"}})
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
        self.assertTrue(out["tried"][0]["why"].startswith("ruling 70: y: no verdict"), out["tried"][0]["why"])
        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])     # no write for the line-up with y
        self.assertIsNotNone(out["package"])

    def test_an_unmeasured_hook_may_not_open(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": {"measured": False, "why": "no sheet"}}).run()
        self.assertIn("not measured", out["hook_pool"]["visual_blocked"]["h"])
        self.assertIsNone(out["package"])

    TICKER = {"burned_in": [{"kind": "ticker", "text": "BTC 74,512 | ETH 2,410", "whole_in_16x9": True,
                             "in_9x16": "cut", "covers_speaker": False}]}

    def test_ruling_93_a_ticker_holds_the_clip_in_any_role_by_its_own_frames(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TICKER}).run()
        self.assertIn("ruling 93 (1 item(s)): a ticker", out["hook_pool"]["visual_blocked"]["h"])     # it may not open
        self.assertIsNone(out["package"])
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
                  visuals={"y": self.TICKER})
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])          # dropped and re-lined
        self.assertIn("ruling 93 (1 item(s)): a ticker", out["tried"][0]["why"])
        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])                   # no write for it
        self.assertIsNotNone(out["package"])

    def test_ruling_93_a_whole_lower_third_is_eligible_and_flagged(self):
        strap = {"kind": "lower_third", "text": "JOE CARLASARE", "whole_in_16x9": True, "in_9x16": "out",
                 "covers_speaker": False}
        flag = {"kind": "burned_in", "text": "JOE CARLASARE", "item": "lower_third", "in_9x16": "out"}
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                  visuals={"x": {"burned_in": [strap], "flags": [flag]}}).run()
        self.assertIsNotNone(out["package"])
        self.assertEqual(out["package"]["gates"]["visual"]["flags"], [dict(flag, segment=1)])


class TestRuling66Candidate(unittest.TestCase):
    """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. A line-up that passed the clips-alone verdict is a candidate. A build
    from it asks no angle, tries exactly its clips in its order with its own seeds (so its recorded calls are served
    from their recordings), and never re-lines or swaps it: a failing gate closes it."""
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
    TEXT, T2 = "Nobody controls Bitcoin.", "Nobody can change it."
    MED = {"through_line": "Nobody controls the rules.", "clips": {"hook": 4, "clip_01": 4, "clip_02": 4},
           "flagged": [], "measured": True, "replayed": False, "backend": "xai:grok"}

    def record(self, tried=None):
        return {"tried": tried if tried is not None else [
            {"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y"], "supply_exception": None, "medley": self.MED,
             "medley_ok": True},
            {"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "z"], "supply_exception": None,
             "medley": dict(self.MED, clips={"hook": 4, "clip_01": 2, "clip_02": 4}), "medley_ok": False}],
            "angles": [{"angle": self.TEXT, "moments": ["h", "x", "y", "z"], "hook": "h"},
                       {"angle": self.T2, "moments": ["x", "h", "y", "z"], "hook": "x"}],
            "angle_backend": "heimdall:deepseek", "angle_tried": []}

    def test_the_record_gives_the_first_passing_line_up_with_its_seeds(self):
        c = PK.load_candidate(self.record(), source="proof/ledger_x")
        self.assertEqual((c["index"], c["ai"], c["n_lineup"], c["lineup"], c["angle"]["hook"], c["angle_backend"]),
                         (0, 0, 1, ["h", "x", "y"], "h", "heimdall:deepseek"))
        self.assertEqual(c["medley"], self.MED)                              # the verdict travels with it
        with self.assertRaises(ValueError):
            PK.load_candidate(self.record(), 1)                              # tried[1] did not pass
        r = self.record()
        for bad in (dict(r, tried=[]),                                       # nothing passed
                    dict(r, angles=[dict(r["angles"][0], angle="another angle")]),   # not its angle
                    dict(r, tried=[dict(r["tried"][0], medley=dict(self.MED, replayed=True))]),   # replayed (L-j)
                    dict(r, tried=[dict(r["tried"][0], lineup=["x", "h", "y"])]),    # not its angle's hook
                    dict(r, tried=[dict(r["tried"][0], lineup="hxy")]),             # malformed (audit 1330 C2)
                    dict(r, tried=[dict(r["tried"][0], angle="1")])):
            with self.assertRaises(ValueError):
                PK.load_candidate(bad)

    def test_the_line_up_number_counts_only_this_angles_line_ups(self):
        rec = self.record(tried=[
            {"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y"], "medley": self.MED, "medley_ok": False},
            {"angle": 1, "text": self.TEXT, "lineup": None},
            {"angle": 2, "text": self.T2, "lineup": ["x", "h", "y"], "medley": self.MED, "medley_ok": False},
            {"angle": 2, "text": self.T2, "lineup": ["x", "h", "z"], "medley": self.MED, "medley_ok": True}])
        c = PK.load_candidate(rec)
        self.assertEqual((c["index"], c["ai"], c["n_lineup"], c["lineup"]), (3, 1, 2, ["x", "h", "z"]))
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], hooks={"x": (5, 5, 5)},
                  candidate=c)
        out = rig.run()
        self.assertIsNotNone(out["package"])
        self.assertEqual(rig.seeds, [("medley", 7 + 2 + 10), ("write", 7 + 1 + 10 + 200)])   # angle 2, line-up 2's

    def test_a_build_from_the_candidate_asks_no_angle_and_judges_it_with_its_own_seeds(self):
        c = PK.load_candidate(self.record(), source="proof/ledger_x")
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c)
        out = rig.run()
        self.assertIsNotNone(out["package"])
        self.assertEqual([r for r, _ in rig.prompts if r == "angle_write"], [])   # no angle asked for
        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])
        self.assertEqual(rig.seeds, [("medley", 8), ("write", 108)])        # angle 1 line-up 1's, as recorded
        self.assertEqual(out["tried"][0]["candidate"], "proof/ledger_x")
        self.assertEqual((out["candidate"]["closed"], out["candidate"]["result"]), (None, "PACKAGE"))
        self.assertEqual(out["angle_backend"], "heimdall:deepseek")          # L-x: the writers' vendor as recorded

    def test_a_candidate_whose_clip_left_the_pool_is_closed_before_any_call(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [], [], uncuttable={"y"}, candidate=PK.load_candidate(self.record()))
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertTrue(out["why_none"].startswith("ruling 66: the candidate is closed: no longer cleared"),
                        out["why_none"])
        self.assertIn("'y'", out["candidate"]["closed"])
        self.assertEqual((rig.medley_calls, rig.write_calls, [r for r, _ in rig.prompts if r == "angle_write"]),
                         ([], [], []))

    def test_a_candidate_failing_its_verdict_now_is_closed_never_re_lined(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE)], [],
                  candidate=PK.load_candidate(self.record()))
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])               # no swap, no second line-up
        self.assertEqual(len(out["tried"]), 1)
        self.assertEqual(out["tried"][0]["why"], "ruling 66: the candidate fails its clips-alone verdict now: closed")
        self.assertEqual(out["candidate"]["result"], out["tried"][0]["why"])

    def test_the_outcome_class_and_the_fresh_writes(self):
        """14:02: the class candidates.outcome reads: "package"; "clip" (closed before any call, or its clips-alone
        verdict fails now); "line" (its clips pass, its writes fail). write_seed shifts every write's seed."""
        c = PK.load_candidate(self.record(), source="r")
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c).run()
        self.assertEqual(out["candidate"]["class"], "package")
        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], uncuttable={"y"}, candidate=c).run()
        self.assertEqual((out["candidate"]["class"], out["candidate"]["result"][:16]), ("clip", "no longer cleare"))
        out = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE)], [], candidate=c).run()
        self.assertEqual(out["candidate"]["class"], "clip")
        bad = dict(TestRuling65Caption.OK, ok=False, violations=[{"slot": "takeaway", "rule": "VERDICT_NO",
                                                                    "detail": "x"}])
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None, None], fids=[bad, bad],
                  candidate=dict(c, write_seed=1000))
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual((out["candidate"]["class"], out["candidate"]["fresh"]), ("line", True))
        self.assertEqual(rig.seeds, [("medley", 8), ("write", 1108)])   # ITEM 2: ONE fresh write; the verdict
                                                                                          # still its recorded seed

    def test_the_search_never_re_forms_a_registered_line_up(self):
        """RULING 66 (14:02; the 16:30 Nov 13 build's search re-formed the resting candidate and re-wrote it from its
        recordings): a line-up the registry holds is neither judged nor written by the search, first formed or swapped
        in, and the angle ends there; a build from the candidate itself still tries it."""
        two = [["h", "x", "y", "z"], ["x", "h", "y", "z"]]
        held = lambda lu, st, until=None: {tuple(lu): {"key": "+".join(lu), "state": st, "until": until,
                                                       "source": "proof/ledger_x", "index": 0}}
        rig = Rig(self.MS, two, [(True, [], None, Rig.LINE)], [None],
                  registered=held(["h", "x", "y"], "resting", "2026-11-14T03:29:49+00:00"))
        out = rig.run()
        self.assertIsNotNone(out["package"])
        self.assertEqual(out["tried"][0]["lineup"], ["h", "x", "y"])           # formed, then left alone
        self.assertEqual(out["tried"][0]["registered"]["state"], "resting")
        self.assertTrue(out["tried"][0]["why"].startswith("ruling 66: a registered candidate (resting until "
                                                          "2026-11-14T03:29:49+00:00; proof/ledger_x tried[0])"))
        self.assertNotIn("medley_ok", out["tried"][0])                          # never a new candidate (CA.seed)
        self.assertEqual([c[0] for c in rig.medley_calls], ["x"])                # only angle 2's line-up is judged
        self.assertEqual([w[0][0] for w in rig.write_calls], ["x"])              # and written
        self.assertEqual(out["search"]["lineups"], 1)                           # the skip is no judged line-up
        rig = Rig(self.MS, two, [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)], [None],
                  registered=held(["h", "x", "z"], "closed"))
        out = rig.run()                                                          # a swap that forms it: the same
        self.assertEqual(rig.medley_calls[0], ["h", "x", "y"])
        self.assertEqual((out["tried"][1]["lineup"], out["tried"][1]["registered"]["state"]),
                         (["h", "x", "z"], "closed"))
        self.assertEqual([c[0] for c in rig.medley_calls[1:]], ["x"])
        self.assertIsNotNone(out["package"])
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                  candidate=PK.load_candidate(self.record()), registered=held(["h", "x", "y"], "resting"))
        out = rig.run()                                                          # its own try: never skipped
        self.assertEqual((rig.medley_calls, out["candidate"]["class"]), ([["h", "x", "y"]], "package"))

    def test_a_reordered_or_pool_filled_line_up_is_skipped_too(self):
        """Audit 1655 C1 (grok P2-1, glm P1-1): every path that forms a line-up meets the check: ruling 63's reorder
        (through `swapped`) and PROPOSAL 1's pool fill (an angle that forms none of its own)."""
        held = lambda lu, st: {tuple(lu): {"key": "+".join(lu), "state": st, "until": None,
                                           "source": "proof/ledger_x", "index": 0}}
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
        rig = Rig(ms, ["h", "x", "y"], [(False, ["hook -> clip_01", "clip_01 -> clip_02"], None, Rig.LINE)], [],
                  registered=held(["h", "y", "x"], "closed"))
        out = rig.run()
        self.assertIn("ruling 63", out["tried"][0]["why"])                   # the same clips reordered...
        self.assertEqual((out["tried"][1]["lineup"], out["tried"][1]["registered"]["key"]), (["h", "y", "x"], "h+y+x"))
        self.assertEqual((rig.medley_calls, rig.write_calls), ([["h", "x", "y"]], []))   # ...and never judged
        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
        filled = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"}).run()
        lu = filled["tried"][0]["lineup"]
        self.assertEqual(filled["tried"][0]["pool_filled"], ["z"])
        rig = Rig(ms, ["h", "x", "s", "y"], [], [], no_hook={"s", "y"}, registered=held(lu, "open"))
        out = rig.run()
        self.assertEqual((out["tried"][0]["pool_filled"], out["tried"][0]["registered"]["state"]), (["z"], "open"))
        self.assertEqual((rig.medley_calls, rig.write_calls, out["package"]), ([], [], None))
        self.assertTrue(out["why_none"].startswith("no angle gave a package: angle 1: ruling 66: a registered "
                                                   "candidate (open; proof/ledger_x tried[0])"), out["why_none"])

    def test_the_no_voice_fallback_never_adds_the_clip_that_forms_a_registered_line_up(self):
        """Audit 1655: ruling 3's no-voice fallback adds one clip and judges the new line-up; a registered one is left
        to the registry (here the only clip that lands it, so no package)."""
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None, None], takeaways=bad,
                  registered={("h", "x", "y", "z"): {"key": "h+x+y+z", "state": "resting", "until": None,
                                                     "source": "proof/ledger_x", "index": 0}})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])                 # h+x+y+z never judged
        nv = out["tried"][0]["no_voice"]
        self.assertEqual(nv["registered_skipped"], ["h+x+y+z"])
        self.assertIn("ruling 66: ['h+x+y+z'] left to the registry", nv["why_not"])

    def test_exactly_its_clips_never_a_subset(self):
        ms = [pm("h", "A", 13.0), pm("x", "B", 13.0), pm("y", "C", 13.0), pm("z", "D", 11.0)]
        rec = self.record(tried=[{"angle": 1, "text": self.TEXT, "lineup": ["h", "x", "y", "z"],
                                  "supply_exception": None, "medley": self.MED, "medley_ok": True}])
        self.assertEqual(PK.lineup_for(rec["angles"][0], {m["moment_id"]: m for m in ms}),
                         [ms[0], ms[1], ms[2]])                              # the search alone would take a subset
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], None, "none")], [], candidate=PK.load_candidate(rec))
        rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y", "z"]])


class TestRuling66Amended(unittest.TestCase):
    """RULING 66 amended (17:02 Nov 13), as ITEM 2 leaves it (orchestrator 09:35 ET Nov 24: "An in-house model writes,
    a different family judges, no paid rescue, no retry loop"): a takeaway refused in its ONE write is never written
    again alone (the writes of the takeaway ALONE are withdrawn); ruling 3's no-voice fallback when its seconds allow,
    else the line-up rests. A title or caption failing alone keeps ruling 65's own writes, unchanged."""
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
    WHY = "host commentary 'Nobody gets to bend these rules' fails imperative_or_prediction"

    def failing(self, slot="takeaway", detail=WHY, rule="COMMENTARY"):
        return TestRuling65Caption.failing(TestRuling65Caption(), slot, detail, rule)

    def run_rig(self, fids, lines, alone_ok=(True,), ms=None, takeaways=None, medleys=None):
        import context_integrity as CI
        import vo_fidelity as VF
        seen, ok_q, avoid = [], list(alone_ok), {}

        def one(router, segs, lns, *a, **k):
            seen.append([ln["text"] for ln in lns])
            ok = ok_q.pop(0) if ok_q else True
            v = [] if ok else [{"slot": lns[0]["slot"], "rule": "COMMENTARY", "detail": f"'{lns[0]['text']}' fails x"}]
            return {"ok": ok, "violations": v, "measured": True, "replayed": False, "backend": "xai:grok",
                    "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
                    "verdict": {"ok": ok, "violations": v, "classes": {lns[0]["slot"]: ["commentary"]}, "claims": []}}
        saved = (VF.check, CI.check_contexts, CI.contexts_from_sources)
        VF.check = one
        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
                                             "backends": {"B": "xai", "C": "xai"}}
        CI.contexts_from_sources = lambda *a, **k: {}
        try:
            rig = Rig(ms or self.MS, ["h", "x", "y", "z"] if ms else ["h", "x", "y"],
                      medleys or [(True, [], None, Rig.LINE)], [None, None], fids=fids, lines=lines,
                      takeaways=takeaways)
            inner = rig.router.call

            def spy(role, prompt, *a, **k):
                m = re.search(r"Your (\w+) was refused", prompt) if role == "angle_write" else None
                if m:                                          # each line written alone: the model it avoided
                    avoid.setdefault(m.group(1), []).append(k.get("avoid_model"))
                return inner(role, prompt, *a, **k)
            rig.router.call = spy
            return rig, rig.run(), seen, avoid
        finally:
            VF.check, CI.check_contexts, CI.contexts_from_sources = saved

    def test_a_refused_takeaway_is_never_written_again_alone(self):
        """REPLACES 'both writes refuse the takeaway, then the takeaway alone passes' (ITEM 2: no retry loop): the
        takeaway refused in its one write is never written alone and no prompt tells it why; the reply offered for it is
        never asked for, and no verdict judges a line alone."""
        new = "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."
        rig, out, seen, avoid = self.run_rig([self.failing()], [{"takeaway": {"text": new, "cites": []}}])
        self.assertIsNone(out["package"])                                      # 39 s: no no-voice line-up lands
        self.assertEqual((len(rig.write_calls), seen, avoid), (1, [], {}))      # one write; nothing written alone
        self.assertFalse([p for r, p in rig.prompts if r == "angle_write" and "Your takeaway was refused" in p])
        self.assertEqual(rig.router.answers["angle_write"], [{"takeaway": {"text": new, "cites": []}}])   # unasked
        self.assertEqual([t["write"] for t in out["takeaways"]], [1])
        self.assertEqual(rig.seeds, [("medley", 8), ("write", 108)])
        self.assertFalse([a for a in out["tried"][0]["attempts"] if a.get("takeaway_alone")])

    def test_no_writer_is_asked_for_the_takeaway_again_the_paid_model_included(self):
        """REPLACES 'the second takeaway alone is on the other writer model' (ITEM 2: one write, no paid rescue): after
        the takeaway's refusal no writer, the paid model included, is asked for it again: the only angle_write call on
        the router is the angle's own; both replies offered for the line alone stay unasked."""
        a1, a2 = "Rules nobody can bend are rules that work the same way for every single person who holds them.", "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."
        rig, out, seen, avoid = self.run_rig([self.failing()],
                                             [{"takeaway": {"text": a1, "cites": []}},
                                              {"takeaway": {"text": a2, "cites": []}}], alone_ok=(False, True))
        self.assertEqual([c[0] for c in rig.router.calls].count("angle_write"), 1)    # the angle, nothing more
        self.assertEqual((seen, avoid), ([], {}))
        self.assertEqual(len(rig.router.answers["angle_write"]), 2)
        self.assertIsNone(out["package"])

    def test_a_refused_takeaway_rests_the_line_up_after_its_one_write(self):
        """REPLACES 'both takeaway-alone writes fail and the line-up rests' (ITEM 2): the line-up rests after the ONE
        write when no no-voice line-up lands (39 s of clips, no clip to add), its reason recorded."""
        rig, out, seen, _ = self.run_rig([self.failing()],
                                         [{"takeaway": {"text": "Rules nobody can bend are rules that work the same way for every single person who holds them.", "cites": []}},
                                          {"takeaway": {"text": "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere.", "cites": []}}],
                                         alone_ok=(False, False))
        self.assertIsNone(out["package"])
        self.assertEqual(seen, [])                                             # no line judged alone
        self.assertEqual(out["tried"][0]["why"], "1 write(s) failed their gates (COMMENTARY)")
        self.assertIn("no one clip of the angle lands", out["tried"][0]["no_voice"]["why_not"])   # then rest
        self.assertIn("1 write(s) failed their gates", out["why_none"])

    def test_a_failure_on_another_line_gets_no_takeaway_alone_write(self):
        both = dict(self.failing(), violations=[{"slot": "takeaway", "rule": "COMMENTARY", "detail": self.WHY},
                                                {"slot": "caption", "rule": "VERDICT_NO", "detail": "x"}])
        both["verdict"] = dict(both["verdict"], violations=both["violations"])
        rig, out, seen, avoid = self.run_rig([both, both], [{"takeaway": {"text": "never asked", "cites": []}}])
        self.assertIsNone(out["package"])
        self.assertEqual((seen, avoid), ([], {}))

    def test_the_no_voice_fallback_comes_right_after_the_one_write(self):
        """REPLACES 'the no-voice fallback comes after the takeaway alone' (ITEM 2): ruling 3's no-voice shape comes
        straight after the takeaway's one refused write; no line is written alone first."""
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        rig, out, seen, avoid = self.run_rig([], [{"takeaway": {"text": "Ultimately nobody bends the rules.",
                                                                "cites": []}},
                                                  {"takeaway": {"text": "In the end nobody bends them.", "cites": []}}],
                                             ms=ms, takeaways=bad,
                                             medleys=[(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)])
        self.assertEqual((avoid, seen, len(rig.write_calls)), ({}, [], 1))    # no line alone; one write
        self.assertEqual(len(rig.router.answers["angle_write"]), 2)            # the replies for a line alone: unasked
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")   # then ruling 3
        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])

    def test_a_title_refused_alone_gets_its_second_write_on_the_other_model_then_is_held(self):
        """17:20: YES, the second attempt applies to a failed title too (two writes of the title alone, the second on
        the other writer model), then hold as ruling 65 says."""
        t1, t2 = "Rules nobody can bend", "Nobody bends these rules"
        refused = self.failing("title", "Bitcoin is owned by nobody at all", "VERDICT_NO")
        replies = [{"title": {"text": t1, "cites": []}}, {"title": {"text": t2, "cites": []}}]
        rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, True))
        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"), t2)
        self.assertEqual(avoid, {"title": [None, {"fake:angle_write"}]})
        second = [p for r, p in rig.prompts if r == "angle_write" and "Your title was refused" in p][1]
        self.assertIn(f'"{t1}: ', second)                                       # told the first rewrite's refusal
        self.assertIn("(your first rewrite of it was refused too)", second)
        self.assertEqual(len(out["tried"][0]["attempts"][0]["rewrite"]["tries"]), 1)
        rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, False))
        self.assertIsNone(out["package"])                                      # then held (ruling 65 c)
        self.assertEqual(len(seen), 2)                                          # two writes of the title, no more
        self.assertIn("the title failed alone 4 times", out["tried"][0]["why"])   # RULING 156 (1): 4 writes a line
        self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])
        rig, out, seen, avoid = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
                                                                                      "cites": []}}],
                                             alone_ok=(False,))
        self.assertEqual((len(seen), avoid), (1, {"caption": [None]}))          # the caption: one, then the fixed line
        self.assertTrue(out["package"]["caption_fallback"])

    def test_a_title_reply_out_of_contract_still_sends_the_second_write_to_the_other_model(self):
        """Audit 1735 C1 (glm P1-1), on ruling 65's TITLE path (unchanged by item 2): the first write of the title alone
        answered out of contract (no line, so no gate): its model is still known, and the second write avoids it. Its
        TAKEAWAY half is gone with ITEM 2: a takeaway refused in its one write gets no write alone, so a reply out of
        contract offered for it is never asked for and never rejected."""
        a2 = "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."
        rig, out, seen, avoid = self.run_rig([self.failing()],
                                             [{"takeaway": "not an object"}, {"takeaway": {"text": a2, "cites": []}}])
        self.assertEqual((avoid, seen, rig.router.rejected), ({}, [], []))     # ITEM 2: never asked, never rejected
        self.assertEqual(len(rig.router.answers["angle_write"]), 2)
        self.assertIsNone(out["package"])
        rig, out, seen, avoid = self.run_rig([self.failing("title", "Bitcoin is owned by nobody at all", "VERDICT_NO")],
                                             [{"title": "not an object"},
                                              {"title": {"text": "Nobody bends these rules", "cites": []}}])
        self.assertEqual(avoid, {"title": [None, {"fake:angle_write"}]})
        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"),
                         "Nobody bends these rules")
        self.assertEqual(rig.router.rejected, ["fake:angle_write"])             # the bad title reply was rejected

    def test_both_takeaway_prompts_name_the_two_refused_patterns(self):
        """17:20: the takeaway writer is told the two patterns refused today, and that the line may characterise what
        was SAID, not what WILL happen: in the full write's prompt and in the takeaway written alone."""
        self.assertIn("SAID, never what WILL happen", PK.TAKEAWAY_SAID)
        self.assertIn("a forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.')", PK.TAKEAWAY_SAID)
        self.assertIn("a superlative that upgrades a speaker's hedged view to a settled claim", PK.TAKEAWAY_SAID)
        r = Canned(angle_write=[{"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None,
                                 "title": {"text": "No ruler.", "cites": ["h"]},
                                 "caption": {"text": "three clips", "cites": []}}])
        prompts, inner = [], r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), inner(role, prompt, *a, **k))[1]
        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), TestWriteTakeaway.SEGS, E.Context(NOW, REG), {})
        self.assertIn(PK.TAKEAWAY_SAID, prompts[0])

    def test_which_failures_are_the_takeaways_own(self):
        f = {"takeaway": {"text": "Bitcoin's apolitical design is the real productivity story."},
             "title": {"text": "Apolitical money"}, "caption": {"text": "a steadier design"}, "bridge": None}
        strong = {"segment": "clip_02", "rule": "STRONGER",
                  "detail": "stronger certainty: the video's words 'x' make the clip sound likely"}
        cx = lambda w: {"segments": {"clip_02": {"C": {"raising_words": w}}}}
        own, alone = PK.takeaway_refusal(f, [strong], cx("the real productivity story"))
        self.assertEqual((alone, own[0]["text"], own[0]["rule"]), (True, f["takeaway"]["text"], "STRONGER"))
        self.assertEqual(PK.takeaway_refusal(f, [strong], cx("Apolitical money"))[1], False)       # the title's
        self.assertEqual(PK.takeaway_refusal(f, [strong], cx("apolitical"))[1], False)             # < 2 tokens
        unsure = dict(strong, detail="stronger certainty: uncertain")
        self.assertEqual(PK.takeaway_refusal(f, [unsure], cx("the real productivity story"))[1], False)
        self.assertEqual(PK.takeaway_refusal(f, [{"slot": "-", "rule": "RUNTIME", "detail": "72 s"}])[1], True)
        self.assertEqual(PK.takeaway_refusal(f, [{"slot": "-", "rule": "LY_SHAPE", "detail": "x"}])[1], False)
        self.assertEqual(PK.takeaway_refusal(f, [])[1], False)                                     # no failure
        self.assertEqual(PK.takeaway_refusal(f, [{"segment": "clip_02", "rule": "POLARITY", "detail": "x"}],
                                             cx("the real productivity story"))[1], False)        # a clip's own


def lock_stub(verdicts=None, error=False, calls=None):
    """lock_precheck.check as the build calls it: each moment's outcome from `verdicts` ({moment id: (outcome,
    spoken_text)}, default no_difference), decided by the real lock_precheck.decide; error: no answer at all."""
    import lock_precheck as LP

    def check(segs):
        req = LP.segments_of(segs)
        if calls is not None:
            calls.append([m["moment_id"] for m in segs])
        if error:
            return {"ok": False, "request_id": "r", "error": "no answer from the render's lock in time",
                    "segments": [dict(s, verdict="error", outcome=None, why="no answer", entry=None) for s in req]}
        rows = []
        for m, s in zip(segs, req):
            out, spoken = (verdicts or {}).get(m["moment_id"], ("no_difference", None))
            e = {"outcome": out, "reason": "PinError: the edge word" if out == "hold" else None,
                 "spoken_text": spoken, "request_id": "r", "at": "2026-11-13T23:00:00Z", "lock": {"sha256": "ab" * 32}}
            rows.append(dict(s, **LP.decide(s, e), entry={"request_id": "r", "outcome": out}))
        return {"ok": all(r["verdict"] in ("pass", "adopt") for r in rows), "request_id": "r", "segments": rows,
                "error": None}
    return check


class TestRuling72Lock(unittest.TestCase):
    """RULINGS 68 / 72 (14:02; live 17:17 Nov 13): the render's own lock, asked for a line-up whose clips pass, BEFORE
    any write: a held clip is out and the line-up re-lined; no verdict stops the search with nothing written; a package
    seals the approved texts, or an adopted spoken text with its "attested" record; the pin stage checks it again."""
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0)]   # every line-up >= 39 s

    def test_a_held_clip_is_out_and_the_line_up_is_re_lined_before_any_write(self):
        calls = []
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
                  lock_check=lock_stub({"x": ("hold", None)}, calls=calls))
        out = rig.run()
        self.assertEqual(calls, [["h", "x", "y"], ["h", "y", "z"]])
        self.assertEqual(rig.write_calls, [(["h", "y", "z"], None)])               # nothing written for the held one
        self.assertIn("ruling 72: the render's lock holds x: PinError: the edge word", out["tried"][0]["why"])
        self.assertEqual(out["tried"][0]["precheck"]["segments"][1]["verdict"], "hold")
        self.assertIsNotNone(out["package"])
        import lock_precheck as LP
        self.assertEqual(LP.pin_problems(out["package"]), [])                       # the pin stage's own check

    def test_ruling_130_a_clip_the_lock_holds_is_never_seen(self):
        """RULING 130 (2) (23:00 ET Nov 16): the render's lock is asked FIRST: a clip it holds is never sent to the paid
        vision check; the line-up the search forms next is seen once its own lock passes."""
        calls = []
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
                  lock_check=lock_stub({"x": ("hold", None)}, calls=calls))
        out = rig.run()
        self.assertEqual(calls, [["h", "x", "y"], ["h", "y", "z"]])
        self.assertNotIn("x", rig.visual_calls)                                  # held by the lock: never seen
        self.assertTrue({"y", "z"} <= set(rig.visual_calls), rig.visual_calls)    # the next line-up: seen after it
        self.assertIsNotNone(out["package"])

    def test_no_verdict_writes_nothing_and_stops_the_search(self):
        rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
                  lock_check=lock_stub(error=True))
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))       # no write, no second angle
        self.assertTrue(out["tried"][0]["budget"])
        self.assertIn("no lock verdict", out["lock_stop"])
        self.assertNotIn("y", rig.visual_calls)        # ruling 130 (2): the line-up's clip is never seen (h and x
        #                                                are seen earlier only as the hook stage's openers)
        c = PK.load_candidate(TestRuling66Candidate().record(), source="proof/ledger_x")
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
                  lock_check=lock_stub(error=True)).run()
        self.assertEqual(out["candidate"]["class"], "budget")                      # it stays as it was
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], candidate=c,
                  lock_check=lock_stub({"y": ("hold", None)})).run()
        self.assertEqual(out["candidate"]["class"], "clip")                        # a clip fails a gate: closed

    def test_an_adopted_spoken_text_is_sealed_with_its_record(self):
        import lock_precheck as LP
        spoken = self.MS[0]["text"].replace(" ", " the ", 1)                      # one function word more
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                  lock_check=lock_stub({"h": ("adopt_spoken", spoken)}))
        pk = rig.run()["package"]
        self.assertEqual(pk["segments"][0]["text"], spoken)
        self.assertEqual(pk["segments"][0]["attested"]["was"], self.MS[0]["text"])
        self.assertEqual(pk["hook_first_words"], " ".join(spoken.split()[:8]))
        self.assertEqual(LP.pin_problems(pk), [])
        pin = package_pin.to_pin(spk(pk), "test")
        self.assertEqual(pin["segments"][0]["approved_text"], spoken)
        self.assertEqual(pin["segments"][0]["attested"]["was"], self.MS[0]["text"])   # sealed (SEALED_LATER)
        mp = pin["moments_package"]
        self.assertEqual(package_pin.seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"],
                                          mp["caption"], mp["gates"], mp.get("btc_screen")), mp["package_sha256"])
        bare = dict(pin["segments"][0])
        bare.pop("attested")
        self.assertNotEqual(package_pin.seal([bare] + pin["segments"][1:], mp["edl_vo"], mp["signoff_expected"],
                                             mp["title"], mp["caption"], mp["gates"], mp.get("btc_screen")),
                            mp["package_sha256"])                                 # the record is in the seal

    def test_a_pre_check_that_raises_is_no_verdict_never_a_crash(self):
        """Audit 1744 C1 (glm P1-2): a request that cannot be written, or an answer that cannot be decided, raises
        inside lock_check: the line-up gets no write, the search stops, and the build still returns its record."""
        def boom(segs):
            raise OSError("the lock_requests directory is not writable")
        rig = Rig(self.MS, [["h", "x", "y", "z"], ["x", "h", "y", "z"]], [(True, [], None, Rig.LINE)] * 2, [None],
                  lock_check=boom)
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual((rig.write_calls, len(rig.medley_calls)), ([], 1))
        self.assertIn("OSError: the lock_requests directory is not writable", out["lock_stop"])
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        calls = []

        def second_raises(segs):                        # the voiced line-up passes; the no-voice one raises
            calls.append(len(segs))
            if len(calls) > 1:
                raise ValueError("an answer that cannot be decided")
            return lock_stub()(segs)
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], takeaways=bad, lock_check=second_raises).run()
        self.assertIsNone(out["package"])
        self.assertIn("ValueError: an answer that cannot be decided", out["lock_stop"])   # stops, as voiced

    def test_the_pin_stage_compares_the_text_the_lock_passed(self):
        import lock_precheck as LP
        pk = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], lock_check=lock_stub()).run()[
            "package"]
        self.assertEqual(LP.pin_problems(pk), [])
        pk["segments"][1]["text"] += " And more."                                 # changed after the lock passed
        self.assertIn("as they now stand", LP.pin_problems(pk)[0])

    def test_the_no_voice_line_up_asks_the_lock_too(self):
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        calls = []
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], takeaways=bad, lock_check=lock_stub({"z": ("hold", None)}, calls=calls))
        out = rig.run()
        self.assertEqual(calls, [["h", "x", "y"], ["h", "x", "y", "z"]])          # its own line-up, the added clip
        self.assertIsNone(out["package"])
        self.assertIn("ruling 68 / 72: the render's lock", out["tried"][0]["no_voice"]["why_not"])
        self.assertNotIn("z", rig.visual_calls)        # RULING 130 (2): the added clip the lock holds is never seen


class TestRuling76Window(unittest.TestCase):
    """RULING 76 (18:08 Nov 13): (a) a moment only while its source is <= 12 h old on the RENDER clock, no exception for
    one that is not time-sensitive; (b) a delivered span never again, nor the same speech re-posted in another video;
    (c) the pin stage re-checks (a) on the render clock."""

    def at(self, mid, hours_ago, **kw):
        return dict(pm(mid, mid.upper(), 12.0, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat())

    def test_a_moment_over_12_h_or_of_unknown_age_is_expired(self):
        ok, why = PK.usable([self.at("a", 11.9), self.at("b", 12.1), dict(self.at("c", 1), published_at=None),
                             dict(self.at("d", 1), published_at="yesterday")], ctx())
        self.assertEqual([m["moment_id"] for m in ok], ["a"])
        for mid in "bcd":
            self.assertIn("ruling 76 (a)", why[mid])
        both = PK.usable([self.at("t", 30, risk=("time_sensitive",)), dict(self.at("e", 13), excluded=["x"])],
                         ctx())[1]
        self.assertIn("ruling 76 (a)", both["t"])                              # expired first (audit 1810 C2): the
        self.assertIn("ruling 76 (a)", both["e"])                              # why agrees with (d)'s count

    def test_delivered_speech_is_never_used_again_in_any_other_video(self):
        said = "Currencies are often born for political reasons, but fail for economic reasons."
        delivered = [{"video_id": "vD", "start": 10.0, "end": 20.0, "pin": "moments-x-1", "text": said}]
        copy = dict(self.at("c", 1), text="Currencies are often born for political reasons but fail for economic "
                                          "reasons, he said.", video_id="vOther")
        other = dict(self.at("o", 1), text="Bitcoin launched in January of 2009 and was never renamed.",
                     video_id="vOther2")
        same_video_elsewhere = dict(self.at("s", 1), text=said, video_id="vD", start=40.0, end=50.0)
        ok, why = PK.usable([copy, other, same_video_elsewhere], ctx(), delivered)
        self.assertEqual([m["moment_id"] for m in ok], ["o"])
        self.assertIn("ruling 76 (b): the same speech as a delivered clip (moments-x-1: vD 10.0-20.0), re-posted",
                      why["c"])
        self.assertIn("said again at another time of the same video", why["s"])    # audit 1810 C3
        self.assertTrue(PK.same_speech(said, said.upper()))
        self.assertFalse(PK.same_speech("Bitcoin", "Bitcoin"))                 # never on one word
        self.assertFalse(PK.same_speech(said, "Currencies fail."))             # short: only an equal text
        self.assertTrue(PK.same_speech("Bitcoin fixes this.", "bitcoin fixes this"))
        scattered = "Currencies are rarely political, but reasons fail for many economic reasons of their own."
        self.assertFalse(PK.same_speech(said, scattered))                      # common words, not runs of three

    def test_the_pin_stage_re_checks_on_the_render_clock(self):
        now = NOW
        fresh = {"video_id": "v1", "source_published_at": (now - timedelta(hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ")}
        stale = {"video_id": "v2", "source_published_at": (now - timedelta(hours=12, minutes=1)).isoformat()}
        naive = {"video_id": "v3", "source_published_at": (now - timedelta(hours=2)).replace(tzinfo=None).isoformat()}
        self.assertEqual(package_pin.window_problems([fresh], now), [])
        p = package_pin.window_problems([fresh, stale, {"video_id": "v4", "source_published_at": None}, naive], now)
        self.assertEqual(len(p), 3)
        self.assertIn("v2 was published", p[0])
        self.assertIn("over 12 h): expired", p[0])
        self.assertIn("v4: no readable publish time", p[1])
        self.assertIn("v3: a publish time without a zone", p[2])               # audit 1810 C1: no measurement
        with self.assertRaises(ValueError):                                     # audit 1810 C3: never a zoneless
            package_pin.window_problems([fresh], now.replace(tzinfo=None))      # render clock
        self.assertEqual(package_pin.WINDOW_H, 12.0)


class TestRuling65Caption(unittest.TestCase):
    """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
    alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
    the FIXED caption (the gated title in lowercase, a line break, the channel names in play order), code-written,
    caption_fallback: true. The title alone: one more write, then hold."""
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
    OK = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
          "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
          "verdict": {"ok": True, "violations": [], "classes": {"takeaway": ["commentary"], "title": ["fact"],
                                                                "caption": ["fact"]}, "claims": []}}

    def failing(self, slot, detail="it belongs to everyone who uses it.", rule="VERDICT_NO"):
        v = {"slot": slot, "rule": rule, "detail": detail}
        return dict(self.OK, ok=False, violations=[v], verdict=dict(self.OK["verdict"], ok=False, violations=[v]))

    def run_rig(self, fids, lines, line_ok=True):
        import context_integrity as CI
        import vo_fidelity as VF
        seen = []

        def one(router, segs, lns, *a, **k):
            seen.append([ln["text"] for ln in lns])
            v = [] if line_ok else [{"slot": lns[0]["slot"], "rule": "VERDICT_UNCERTAIN", "detail": lns[0]["text"]}]
            return {"ok": line_ok, "violations": v, "measured": True, "replayed": False, "backend": "xai:grok",
                    "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
                    "verdict": {"ok": line_ok, "violations": v, "classes": {lns[0]["slot"]: ["commentary"]}, "claims": []}}
        saved = (VF.check, CI.check_contexts, CI.contexts_from_sources)
        VF.check = one
        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
                                             "backends": {"B": "xai", "C": "xai"}}
        CI.contexts_from_sources = lambda *a, **k: {}
        try:
            rig = Rig(self.MS, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], fids=fids, lines=lines)
            return rig, rig.run(), seen
        finally:
            VF.check, CI.check_contexts, CI.contexts_from_sources = saved

    def test_only_the_caption_fails_and_its_own_write_passes(self):
        new = "nobody holds the keys to these rules."
        rig, out, seen = self.run_rig([self.failing("caption")], [{"caption": {"text": new, "cites": []}}])
        pk = out["package"]
        self.assertIsNotNone(pk)
        lines = {x["slot"]: x["text"] for x in pk["lines"]}
        self.assertEqual(lines["caption"], new)
        self.assertEqual((lines["takeaway"], lines["title"]), (Rig.LINE, "Nobody bends the rules"))   # kept as gated
        self.assertFalse(pk.get("caption_fallback"))
        prompt = [p for r, p in rig.prompts if r == "angle_write"][-1]
        self.assertIn("Your caption was refused", prompt)                   # a new prompt, never a replay
        self.assertIn('"it belongs to everyone who uses it." (the fact check found that the clips do not say it)', prompt)
        self.assertIn('TAKEAWAY: "' + Rig.LINE, prompt)
        self.assertEqual(seen, [[new]])                                       # the verdict on that line alone
        rw = out["tried"][0]["attempts"][0]["rewrite"]
        self.assertEqual((rw["slot"], rw["passed"]), ("caption", True))
        self.assertEqual(pk["gates"]["vo_fidelity_verdict"]["status"], "PASS")
        self.assertEqual(len(rig.write_calls), 1)                            # no second full write was spent

    def test_a_caption_that_fails_again_is_the_fixed_line(self):
        rig, out, seen = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
                                                                               "cites": []}}], line_ok=False)
        pk = out["package"]
        self.assertIsNotNone(pk)                                              # a caption never kills a package
        cap = next(x for x in pk["lines"] if x["slot"] == "caption")
        self.assertEqual(cap["text"], "nobody bends the rules\na / b / c")   # the title, lowercase; the channels
        self.assertEqual(cap["cites"], ["h", "x", "y"])
        self.assertTrue(pk["caption_fallback"])
        self.assertTrue(out["tried"][0]["attempts"][0]["rewrite"]["caption_fallback"])
        self.assertIn("ruling 65 b", pk["gates"]["vo_fidelity_verdict"]["by"])
        self.assertEqual(pk["gates"]["house_style"]["status"], "PASS")
        self.assertEqual(HS.lint("caption", cap["text"]), [])
        bad_reply = self.run_rig([self.failing("caption")], [{"caption": "not an object"}])[1]   # the write fails
        self.assertTrue(bad_reply["package"]["caption_fallback"])

    def test_the_title_alone_gets_one_more_write_then_is_held(self):
        rig, out, _ = self.run_rig([self.failing("title", "Bitcoin is owned by nobody at all")],
                                   [{"title": {"text": "Rules nobody can bend", "cites": []}}])
        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"),
                         "Rules nobody can bend")
        rig, out, _ = self.run_rig([self.failing("title")], [{"title": {"text": "Rules nobody can bend", "cites": []}}],
                                   line_ok=False)
        self.assertIsNone(out["package"])                                     # no fixed title without a ruling
        self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])

    def test_only_a_lone_caption_or_title_takes_the_path(self):
        self.assertEqual(PK.lone_slot([{"slot": "caption"}, {"slot": "caption"}]), "caption")
        self.assertEqual(PK.lone_slot([{"slot": "title"}]), "title")
        for vs in ([], [{"slot": "takeaway"}], [{"slot": "caption"}, {"slot": "title"}], [{"slot": "-"}],
                   [{"slot": "caption"}, {"slot": "-"}]):
            self.assertIsNone(PK.lone_slot(vs), vs)
        rig, out, _ = self.run_rig([dict(self.failing("caption"), violations=[
            {"slot": "caption", "rule": "VERDICT_NO", "detail": "x"}, {"slot": "takeaway", "rule": "VERDICT_NO",
                                                                      "detail": "y"}])], [])
        self.assertNotIn("rewrite", out["tried"][0]["attempts"][0])          # the takeaway failed too: as before

    def test_merge_keeps_the_other_lines_as_gated(self):
        merged = PK.merge_fid(self.failing("caption"), "caption",
                              {"deterministic": {"ok": True, "violations": []}, "measured": True, "replayed": False,
                               "verdict": {"ok": True, "violations": [], "classes": {"caption": ["commentary"]},
                                           "claims": []}, "backend": "heimdall:qwen"})
        self.assertTrue(merged["ok"])
        self.assertEqual(merged["verdict"]["classes"], {"takeaway": ["commentary"], "title": ["fact"],
                                                        "caption": ["commentary"]})
        self.assertIn("the caption alone: heimdall:qwen (ruling 65)", merged["backend"])
        unmeasured = PK.merge_fid(self.OK, "caption", {"deterministic": {"ok": True, "violations": []},
                                                       "measured": False, "verdict": {"ok": True, "violations": []}})
        self.assertFalse(unmeasured["ok"])                                   # law L-m

    def test_a_cached_clips_alone_verdict_is_free(self):
        rig = Rig([pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)], ["h", "x", "y"],
                  [(False, [], None, "none")], [None], cached=True)
        out = rig.run()
        self.assertEqual((len(rig.medley_calls), out["search"]["lineups"]), (1, 0))


class TestOrder0622StepAFromBothVendors(unittest.TestCase):
    """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
    after a write swaps out that clip only, and the line-up carries on."""
    MS = TestBuildLoop.MS

    def test_every_cuttable_clip_is_screened_by_the_second_vendor_before_the_angle_step(self):
        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],      # the writer never sees y
                  a_fail={("heimdall", "y"): ["REFERENT_OUTSIDE"]})
        out = rig.run()
        self.assertEqual(rig.screens[0], ("xai:grok", ["h", "x", "y", "z"]))          # the first screen, off heimdall
        self.assertEqual(rig.screens[1:3], [("heimdall:deepseek", ["h", "x"]),          # the second, off xai, in
                                            ("heimdall:deepseek", ["y", "z"])])         # ruling 82's chunks of 2
        self.assertLess(rig.events.index("step_a:heimdall:deepseek"), rig.events.index("angle_write"))
        sv = out["prescreen"]["second_vendor"]
        self.assertEqual(sv["h"], "PASS (heimdall:deepseek)")
        self.assertTrue(sv["y"].startswith("FAIL: REFERENT_OUTSIDE"), sv["y"])
        angle_prompt = next(p for r, p in rig.prompts if r == "angle_write")
        self.assertNotIn("id=y ", angle_prompt)                    # never offered to the angles
        self.assertIn("id=z ", angle_prompt)
        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])     # no line-up is built on it
        self.assertIsNotNone(out["package"])

    def test_a_clip_with_no_second_verdict_is_out(self):           # law L-m: nothing measured is never a pass
        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],
                  unavailable={("heimdall", "y")})
        out = rig.run()
        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith(f"HELD: {PK.HELD}"))      # ruling 102
        self.assertEqual(out["prescreen"]["held_102"], {"first": [], "second": ["y"]})
        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])

    def test_the_verdict_used_is_the_one_off_the_writers_vendor(self):
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        rig.run()                                                  # the angle from vendor "fake": the first verdict
        self.assertEqual(set(rig.a_seen[0].values()), {"xai:grok"})
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                  angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
        out = rig.run()                                            # Grok wrote the angles: Heimdall's verdict counts
        self.assertEqual(set(rig.a_seen[0].values()), {"heimdall:deepseek"})
        self.assertEqual(rig.write_avoid, [{"heimdall"}])          # and every write avoids Heimdall, so with the two
        # real vendors the writers never span both and a verdict off them always exists (audit 0640 C1, glm cond. 1)
        self.assertEqual(len(rig.screens), 3)                      # (the second screen in two chunks of 2) and no
        #   re-screen was needed after the write
        self.assertIsNotNone(out["package"])

    def test_a_clip_that_fails_its_re_screen_is_swapped_out_alone_and_the_line_up_carries_on(self):
        """The 05:48 build: a line-up passed the clips-alone verdict, a re-screen failed ONE clip, and the line-up was
        lost. Now only that clip goes (for good, with its reason), the next-best clip takes its place, the clips-alone
        verdict re-judges, and the build goes on to the writer. (Both vendors write here, so the rig's third vendor
        re-screens.)"""
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], angle_from=("xai:grok", "xai", "grok"), a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
        self.assertEqual(out["prescreen"]["rescreen_failed"], {"y": ["REFERENT_OUTSIDE"]})
        self.assertIn("swapped {'y': 'z'}", out["tried"][0]["why"])
        self.assertIn("(out for good)", out["tried"][0]["why"])
        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])
        self.assertEqual(rig.screens[3], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
        self.assertEqual(rig.screens[4], ("openai:gpt", ["z"]))                   # only what changed is re-judged
        self.assertEqual(rig.screen_deadlines, [None, 120.0, 120.0, 120.0, 120.0])   # audit 2005 C1: the first screen
        #   unbounded as before; the second screen's two chunks and both off-writer re-screens at ruling 82's 120 s

    def test_ruling_85_the_first_screen_is_bounded_under_heimdall_first(self):
        """RULING 85: under heimdall_first the FIRST step-A verdict is a Heimdall family's, so it gets ruling 82's
        bounds too (2 clips a call, 120 s); under today's routing it stays unbounded (Grok's), as before. RULING 100:
        the Router holds each leg to its own row in place of the 120 s (Router.effective_deadline, test_deadline_table)."""
        batches = []
        for routing in ("today", "heimdall_first"):
            rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                      angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
            rig.router.routing = routing
            pre = rig.prescreen

            def spy(*a, batch=PK.PRESCREEN_BATCH, **k):
                batches.append((routing, batch))
                return pre(*a, batch=batch, **k)
            rig.prescreen = spy
            rig.run()
            self.assertEqual(rig.screen_deadlines[0], None if routing == "today" else PK.SECOND_VERDICT_DEADLINE_S)
        self.assertEqual([b for r, b in batches if r == "heimdall_first"][0], PK.SECOND_VERDICT_BATCH)
        self.assertEqual(PK.first_bounds(type("R", (), {"routing": "heimdall_first"})()),
                         {"batch": PK.SECOND_VERDICT_BATCH, "deadline_s": PK.SECOND_VERDICT_DEADLINE_S})
        self.assertEqual([b for r, b in batches if r == "today"][0], PK.PRESCREEN_BATCH)

    def test_ruling_101_the_plan_parallel_only_over_20_new_moments_and_10_minutes_of_filter(self):
        """RULING 101 (12:16 Nov 14): parallel when the new moments are over 20 AND the filter would hold the build over
        10 minutes: its rounds (batches over PRESCREEN_WORKERS) x the leading leg's deadline (ruling 100's, for the
        first screen's 120 s), the leg the first off the writers and not breaker-open; when Grok leads (no Heimdall
        family can), sequential whatever the wait."""
        from unittest import mock

        class B:
            def __init__(self, vendor, family):
                self.vendor, self.family, self.gateway = vendor, family, vendor.split("/")[0]

        class R:
            routing, down = "heimdall_first", {}

            def __init__(self, open_=()):
                self.backends = {"heimdall:glm": B("heimdall/glm", "glm"), "heimdall:ds": B("heimdall/deepseek",
                                                                                          "deepseek"),
                                 "xai:grok": B("xai", "grok")}
                self.open_ = set(open_)

            def chain(self, role, kind=None):
                assert role == "context_verdict"
                return {"step_a_first": ["heimdall:glm", "heimdall:ds", "xai:grok"],
                        "step_a_second": ["xai:grok", "heimdall:ds", "heimdall:glm"]}[kind]

            def effective_deadline(self, role, b, deadline_s=None):
                assert (role, deadline_s) == ("context_verdict", PK.SECOND_VERDICT_DEADLINE_S)   # the first screen's
                return {"glm": 60.0, "deepseek": 300.0, "grok": 118.1}.get(b.family)

            def breaker_open(self, name):
                return name in self.open_

        def plan(n, router, wv=(), wf=()):
            new = [{"moment_id": f"m{i}"} for i in range(n)]
            with mock.patch.object(PK, "prescreen", lambda *a, plan_only=False, **k: new if plan_only else None):
                return PK.step_a_plan(router, [], {}, None, set(wv), set(wf), **PK.first_bounds(router))
        p = plan(20, R())                                                  # under the line: nothing else consulted
        self.assertEqual((p["parallel"], p["n_new"], p["est_wait_s"], p["leg"]), (False, 20, None, None))
        p = plan(21, R())                                  # glm leads: 11 batches of 2, 2 rounds x 60 s = 2 minutes
        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 120.0, "heimdall:glm"))
        p = plan(21, R(open_={"heimdall:glm"}))           # glm's breaker open: deepseek leads, 2 x 300 s = 10 minutes
        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 600.0, "heimdall:ds"))   # not OVER 10
        p = plan(37, R(open_={"heimdall:glm"}))           # 19 batches, 4 rounds x 300 s = 20 minutes
        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"], p["confirm"], p["why"]),
                         (True, 1200.0, "heimdall:ds", "xai:grok", None))
        p = plan(37, R(open_={"heimdall:glm", "xai:grok"}))   # glm C2 H1: Grok breaker-open, no confirm leg
        self.assertEqual((p["parallel"], p["est_wait_s"], p["confirm"]), (False, 1200.0, None))
        self.assertIn("no confirm leg", p["why"])
        p = plan(37, R(open_={"heimdall:glm"}), wv={"xai"})   # Grok writes: a confirm ahead could ask nothing
        self.assertEqual((p["parallel"], p["leg"], p["confirm"]), (False, "heimdall:ds", None))
        down = R()
        down.down = {"heimdall:glm": "HTTP 503"}               # glm down this run: deepseek leads, as breaker-open
        p = plan(37, down)
        self.assertEqual((p["parallel"], p["leg"], p["confirm"]), (True, "heimdall:ds", "xai:grok"))
        down.down = {"heimdall:glm": "HTTP 503", "xai:grok": "HTTP 503"}   # Grok down: no confirm leg
        self.assertEqual(plan(37, down)["confirm"], None)
        p = plan(37, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # the writer's family: Grok leads,
        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 472.4, "xai:grok"))   # 4 x 118.1 s
        p = plan(80, R(open_={"heimdall:glm"}), wv={"heimdall/deepseek"})   # 40 batches, 7 rounds: over 10 minutes
        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 826.7, "xai:grok"))   # but Grok leads
        p = plan(80, R())                                                  # glm leads: 7 x 60 s, under 10 minutes
        self.assertEqual((p["parallel"], p["est_wait_s"], p["leg"]), (False, 420.0, "heimdall:glm"))

    def test_ruling_101_confirm_ahead_asks_off_every_heimdall_family_and_tallies_its_dollars(self):
        from unittest import mock
        import providers as P
        hb = lambda name, fam: P.HeimdallBackend(name, {"model": fam, "family": fam, "base_url": "http://x"}, "/x")

        class Rep:
            def __init__(self, usd, reported):
                self.usd, self.usage = usd, ({"usd_reported": reported} if reported is not None else {})

        class R:
            backends = {"heimdall:glm": hb("heimdall:glm", "glm"), "heimdall:ds": hb("heimdall:ds", "deepseek")}
            replies = [Rep(0.5, 0.01), Rep(0.5, None)]

            def call(self, *a, **k):
                return self.replies.pop(0)
        got = {}

        def fake(router, new, sources, ctx_, wv, wf, n=None, kind=None, cache=None, **k):
            got.update(wv=set(wv), wf=set(wf), kind=kind, n=n, cache=cache)
            router.call("context_verdict", "p")
            router.call("context_verdict", "q")
            return {m["moment_id"]: {"backend": "xai:grok"} for m in new}, {}, set(), set()
        with mock.patch.object(PK, "prescreen", fake):
            res = PK.confirm_ahead(R(), [{"moment_id": "a"}, {"moment_id": "b"}], {}, None, {"openai"}, {"gpt"},
                                   cache="/tmp/c")
        self.assertEqual(got, {"wv": {"openai", "heimdall"}, "wf": {"gpt", "glm", "deepseek"}, "kind": "step_a_second",
                               "n": 2, "cache": "/tmp/c"})       # off every Heimdall family and off the writers
        self.assertEqual(res, {"asked": 2, "verdicts": 2, "usd": 0.51, "calls": 2,      # vendor-reported, else estimate
                               "by": {"a": "xai:grok", "b": "xai:grok"}})

    def test_ruling_101_in_a_build_grok_confirms_beside_the_filter_and_the_extra_is_reported(self):
        """The plan says parallel: Grok's confirm (step_a_second) runs on every new moment ON ANOTHER THREAD while the
        first screen runs; the second screen later reads the cache; the report counts what it used."""
        import threading
        from unittest import mock
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
                  angle_from=("xai:grok", "xai", "grok"), write_from=("xai:grok", "xai", "grok"))
        rig.router.routing = "heimdall_first"
        rig.plan_new = {m["moment_id"] for m in self.MS}
        rig.router.backends["heimdall:glm"] = type("B", (), {"vendor": "heimdall/glm", "family": "glm",
                                                             "gateway": "heimdall"})()    # off the rig's writer
        rig.router.chain = lambda role, kind=None: ["heimdall:glm", "xai:grok"]          # (heimdall, deepseek)
        rig.router.effective_deadline = lambda role, b, deadline_s=None: 300.0 if b.family == "glm" else None
        rig.router.breaker_open = lambda name: False
        seen, pre = [], rig.prescreen

        def spy(router_, ms, sources_, ctx_, writer_vendor, *a, kind=None, plan_only=False, **k):
            if not plan_only:
                seen.append((kind, set(writer_vendor), threading.get_ident()))
            return pre(router_, ms, sources_, ctx_, writer_vendor, *a, kind=kind, plan_only=plan_only, **k)
        rig.prescreen = spy
        with mock.patch.object(PK, "STEP_A_PARALLEL_NEW", 1), mock.patch.object(PK, "STEP_A_PARALLEL_WAIT_S", 60.0):
            out = rig.run()
        par = out["prescreen"]["parallel_101"]
        self.assertEqual((par["parallel"], par["n_new"], par["asked"], par["leg"]),
                         (True, len(self.MS), len(self.MS), "heimdall:glm"))
        main = threading.get_ident()
        ahead = [t for k, wv, t in seen if k == "step_a_second" and wv == {"heimdall", "heimdall/glm", "openai"}]
        # off every vendor but Grok's (ruling 102: never Gemini or the local judge ahead) and off the writers
        self.assertEqual(len(ahead), 1)                                   # Grok's confirm: once,
        self.assertNotEqual(ahead[0], main)                               # on its own thread,
        self.assertIn(("step_a_first", {"heimdall"}, main), seen)         # beside the filter on the build's thread
        self.assertEqual(par["used"], 0)              # here every first verdict is Grok's own: the second screen
        self.assertEqual(rig.screens[-1][0], "heimdall:deepseek")         # screens off it as before

    def test_ruling_101_used_counts_only_a_verdict_off_the_first(self):
        class B:
            def __init__(self, vendor, family):
                self.vendor, self.family = vendor, family
        r = type("R", (), {"backends": {"heimdall:ds": B("heimdall/deepseek", "deepseek"), "xai:grok": B("xai", "grok"),
                                        "heimdall:glm": B("heimdall/glm", "glm")}})()
        a_by = {"a": {"backend": "heimdall:ds"}, "b": {"backend": "xai:grok"}, "c": {"backend": "heimdall:glm"},
                "d": {"backend": "heimdall:ds"}}
        pre_by = {"a": "xai:grok", "b": "xai:grok", "c": "xai:grok"}      # d: no verdict ahead
        self.assertEqual(PK.prewarm_used(r, ["a", "b", "c", "d"], a_by, pre_by), 2)   # a and c; b is Grok's own

    def test_ruling_88_grok_confirms_in_its_own_batches_under_heimdall_first(self):
        """RULING 88 (c): under heimdall_first the second step-A verdict is Grok confirming Heimdall's passes: Grok's own
        batch (8) and no deadline, the move-on rule kept; under today it stays a Heimdall family's (2 clips, 120 s)."""
        self.assertEqual(PK._second_bounds(type("R", (), {"routing": "today"})()),
                         (PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S))
        self.assertEqual(PK._second_bounds(type("R", (), {"routing": "heimdall_first"})()), (PK.PRESCREEN_BATCH, None))
        got = []

        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
                 deadline_s=None, kind=None, failover=None):
            got.append((len(chunk), batch, deadline_s, kind, failover))
            return {m["moment_id"]: {"backend": "xai:grok"} for m in chunk}, {m["moment_id"]: [] for m in chunk}, \
                set(), set()
        router = type("R", (), {"routing": "heimdall_first", "backends": {
            "heimdall:qwen": type("B", (), {"vendor": "heimdall/qwen", "family": "qwen"})(),
            "xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}})()
        ms = [dict(m, moment_id=f"m{i}") for i, m in enumerate(self.MS * 3)][:9]
        saved = PK.prescreen
        PK.prescreen = fake
        try:
            PK.second_screen(router, {m["moment_id"]: m for m in ms}, {m["moment_id"]: {"backend": "heimdall:qwen"}
                                                                       for m in ms}, {}, ctx())
        finally:
            PK.prescreen = saved
        self.assertEqual(sorted(got), [(1, 8, None, "step_a_second", True), (8, 8, None, "step_a_second", True)])

    def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
        """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
        flagged with ORDER 06:22): no verdict off the writers keeps the clip out."""
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], angle_from=("xai:grok", "xai", "grok"), unavailable={("openai", "y")})
        out = rig.run()
        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith(PK.HELD))           # ruling 102
        self.assertIn("gives no answer for ['y'] (HELD, ruling 102", out["tried"][0]["why"])
        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "z"])

    def test_when_no_swap_fits_the_line_up_re_lines_and_the_clip_stays_out(self):     # audit 0640 C1, glm P2-9
        rig = Rig(self.MS, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], uncuttable={"z"},   # z never offered
                  angle_from=("xai:grok", "xai", "grok"), a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])     # nothing else fits: no second line-up is judged
        self.assertIn("no swap fits the line-up rules: re-lined", out["tried"][0]["why"])
        self.assertEqual(out["prescreen"]["rescreen_failed"], {"y": ["REFERENT_OUTSIDE"]})
        self.assertIsNone(out["package"])

    def test_a_chunk_whose_second_screen_raises_fails_closed(self):     # audit 0640 C1, qwen P1-1 / glm P1-3
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        router = type("R", (), {"backends": {"xai:grok": B("xai", "grok")}})()

        def boom(*a, **k):
            raise RuntimeError("the router is unreachable")
        saved = PK.prescreen
        PK.prescreen = boom
        try:
            two, fail = PK.second_screen(router, {m["moment_id"]: m for m in self.MS},
                                         {m["moment_id"]: {"backend": "xai:grok"} for m in self.MS}, {}, ctx())
        finally:
            PK.prescreen = saved
        self.assertEqual(two, {})
        self.assertEqual(sorted(fail), ["h", "x", "y", "z"])
        self.assertTrue(all(f[0].startswith(f"{PK.HELD}: no step-A verdict (RuntimeError") for f in fail.values()))

    def test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor(self):
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        router = type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall",
                                                                                                  "deepseek")}})()
        ms = {m["moment_id"]: m for m in self.MS}
        a_by = {"h": {"backend": "xai:grok"}, "x": {"backend": "xai:grok"}, "y": {"backend": "nowhere:model"},
                "z": {"backend": "heimdall:deepseek"}}
        seen, calls = [], []

        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None, batch=None,
                 deadline_s=None, kind=None, failover=None):
            seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
            calls.append((batch, deadline_s))
            name = "heimdall:deepseek"          # off xai for h and x; for z (first verdict heimdall) the SAME vendor
            return {m["moment_id"]: {"backend": name} for m in chunk}, {m["moment_id"]: [] for m in chunk}, set(), set()
        saved = PK.prescreen
        PK.prescreen = fake
        try:
            two, fail = PK.second_screen(router, ms, a_by, {}, ctx())
        finally:
            PK.prescreen = saved
        self.assertEqual(sorted(seen), [(["heimdall"], ["z"]), (["xai"], ["h", "x"])])   # grouped by first vendor
        self.assertEqual(sorted(two), ["h", "x"])
        self.assertTrue(fail["y"][0].startswith("STEP_A_UNKNOWN_BACKEND: the first verdict's back-end 'nowhere:model'"))
        self.assertTrue(fail["z"][0].startswith("STEP_A_SAME_VENDOR"))
        self.assertEqual(set(calls), {(PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S)})   # ruling 82
        self.assertEqual((PK.SECOND_VERDICT_BATCH, PK.SECOND_VERDICT_DEADLINE_S), (2, 120.0))

    def test_ruling_82_the_second_vendor_step_a_fails_over_down_the_chain(self):
        """RULING 82 (20:02 Nov 13): off the first verdict's vendor (xAI), deepseek -> glm-5.3-flash -> qwen3.8-27b,
        each call bounded by 120 s; a model that is down, past the deadline, or answers out of contract hands over to
        the next; all three failing is no verdict (never cached, never a pass)."""
        import tempfile
        import context_integrity as CI
        sys.path.insert(0, os.path.join(REPO, "tests", "providers"))
        from test_providers import Fake, router as mk_router
        from test_gates import CTX, a_item
        good = json.dumps({"excerpts": [a_item(lb) for lb in CTX]})
        with tempfile.TemporaryDirectory() as d:
            x = Fake("xai:grok", "xai", answer=good, family="grok")
            ds = Fake("heimdall:deepseek", "heimdall", fail="503 from the gateway", family="deepseek")
            glm = Fake("heimdall:glm", "heimdall", answer="not one JSON object", family="glm")
            qw = Fake("heimdall:qwen", "heimdall", answer=good, family="qwen")
            r = mk_router(d, [x, ds, glm, qw], {"context_verdict": ["xai:grok", "heimdall:deepseek", "heimdall:glm",
                                                                      "heimdall:qwen"]})
            asked = []
            inner = r.call
            r.call = lambda role, prompt, *a, **k: (asked.append(k.get("deadline_s")), inner(role, prompt, *a, **k))[1]
            got, backend = CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
            self.assertEqual((backend, x.calls, ds.calls, glm.calls, qw.calls), ("heimdall:qwen", 0, 1, 1, 1))
            self.assertEqual(set(asked), {120.0})                      # every call of the chain bounded
            self.assertEqual(sorted(got), sorted(CTX))
            asked.clear()
            with self.assertRaises(ValueError):                        # without failover: as before, the bad answer
                CI.step_a(r, CTX, {"xai"}, writer_family={"grok"})    # raises (the first verdict's path)
            self.assertEqual(asked, [None])                            # and is never bounded there
            asked.clear()
            qw.answer = "still not JSON"
            with self.assertRaises(P_ProviderError()):                 # all three spent: no verdict (law L-m)
                CI.step_a(r, CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
            self.assertEqual(set(asked), {120.0})

        class Stubborn:                                                # audit 2005 C2 (glm): a router that returns
            calls = 0                                                  # a model it was told to skip

            def call(self, role, prompt, *a, **k):
                Stubborn.calls += 1
                import providers
                return providers.Reply("not JSON", "heimdall:deepseek", "heimdall")
        with self.assertRaises(P_ProviderError()):                     # never a loop, the documented error
            CI.step_a(Stubborn(), CTX, {"xai"}, writer_family={"grok"}, deadline_s=120.0, failover=True)
        self.assertEqual(Stubborn.calls, 2)


def P_ProviderError():
    import providers
    return providers.ProviderError


class TestRuling53Reposted(unittest.TestCase):
    """RULING 53 (08:06): the same speech re-posted by a second channel is ONE moment, the original publisher's kept and
    credited: equal text after normalisation, or 80 % of the words TIME-aligned (the same words in order at one clock
    offset). The 07:14 build's pair: CNBC Television (20:55 UTC Nov 12) and Strategy (MicroStrategy) (02:57 UTC Nov
    13), the same 13.9 s. Audit 0816 C1 (qwen P0): two speakers saying near-identical words are never merged."""
    SPEECH = "I don't really think Bitcoin and crypto are partisan issues, right? Bitcoin is about markets."

    def m(self, mid, ch, text, hours_ago, vid=None):
        return dict(pm(mid, ch, 13.0, vid=vid), text=text, words=[0, len(text.split()) - 1],
                    published_at=(NOW - timedelta(hours=hours_ago)).isoformat())

    def timed(self, vid, words, t0, gaps):
        t, toks = t0, []
        for w, g in zip(words, gaps):
            toks.append({"word": w, "start": round(t, 3), "end": round(t + g * 0.8, 3)})
            t += g
        return E.Source(vid, "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", tuple(toks),
                        timing="word", file_head=False, vod=True)

    def test_the_original_publishers_moment_is_kept_and_the_copy_recorded(self):
        orig, copy = self.m("o", "CNBC", self.SPEECH, 10), self.m("c", "STRATEGY", self.SPEECH.upper(), 4)
        kept, dup = PK.reposted_once([copy, orig, pm("z", "Z", 9.0)], {})
        self.assertEqual([m["moment_id"] for m in kept], ["o", "z"])        # the earliest published, order kept
        self.assertIn("the same speech as o (CNBC", dup["c"])
        self.assertIn("equal text after normalisation", dup["c"])

    def test_a_re_post_aligns_in_time_and_two_speakers_never_merge(self):
        words = self.SPEECH.split()                                        # 15 words
        rhythm = [0.31, 0.22, 0.4, 0.28, 0.35, 0.3, 0.45, 0.26, 0.33, 0.5, 0.29, 0.37, 0.24, 0.41, 0.3, 0.3, 0.3]
        src = {"vA": self.timed("vA", words, 100.0, rhythm),
               "vB": self.timed("vB", words + ["and", "more", "after"], 2.5, rhythm)}   # the same audio, +3 words
        a = self.m("a", "A", self.SPEECH, 9, vid="vA")
        b = dict(self.m("b", "B", self.SPEECH + " and more after", 3, vid="vB"), words=[0, 16])
        kept, dup = PK.reposted_once([a, b], src)
        self.assertEqual((list(dup), [m["moment_id"] for m in kept]), (["b"], ["a"]))
        self.assertIn("15 of the shorter's 15 words time-aligned", dup["b"])
        gold, silver = "Bitcoin is the new gold. It is digital.", "Bitcoin is the new silver. It is digital."
        src2 = {"vG": self.timed("vG", gold.split(), 5.0, [0.4] * 8),            # qwen's P0: 7 of 8 words equal,
                "vS": self.timed("vS", silver.split(), 5.0, [0.25] * 8)}         # another speaker's rhythm
        kept, dup = PK.reposted_once([self.m("g", "A", gold, 9, vid="vG"), self.m("s", "B", silver, 3, vid="vS")], src2)
        self.assertEqual(dup, {})
        kept, dup = PK.reposted_once([self.m("g", "A", gold, 9), self.m("s", "B", silver, 3)], {})
        self.assertEqual(dup, {})                                          # no timings: only equal text merges
        spliced = words[:5] + ["seven", "words", "of", "the", "re-poster's", "own", "talk"] + words[5:]
        src3 = {"vA": src["vA"], "vC": self.timed("vC", spliced, 2.5, rhythm[:5] + [0.3] * 7 + rhythm[5:])}
        c = dict(self.m("c", "C", " ".join(spliced), 3, vid="vC"), words=[0, len(spliced) - 1])
        kept, dup = PK.reposted_once([a, c], src3)                         # audit 0816 C2, glm P1-1: a copy spliced
        self.assertEqual(dup, {})                                          # mid-speech sits at two clock offsets

    def test_only_a_second_channel_and_a_readable_time_first(self):
        kept, dup = PK.reposted_once([self.m("a", "A", self.SPEECH, 9), self.m("b", "A", self.SPEECH, 3)], {})
        self.assertEqual(dup, {})                                          # one channel twice: not this rule
        nodate = dict(self.m("u", "B", self.SPEECH, 0), published_at=None)
        kept, dup = PK.reposted_once([nodate, self.m("d", "A", self.SPEECH, 2)], {})
        self.assertEqual(list(dup), ["u"])                                 # no readable time is never preferred
        naive = dict(self.m("n", "B", self.SPEECH, 0), published_at="2026-11-01T00:00:00")
        kept, dup = PK.reposted_once([self.m("d", "A", self.SPEECH, 2), naive], {})
        self.assertEqual(list(dup), ["d"])                                 # no zone: read as UTC (the earliest)

    def test_the_build_never_offers_the_copy_and_records_it(self):
        ms = [pm("h", "A", 12.0), self.m("x", "B", self.SPEECH, 10), pm("y", "C", 13.0), pm("z", "D", 13.0),
              self.m("w", "E", self.SPEECH, 2)]
        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(list(out["reposted"]), ["w"])
        self.assertNotIn("id=w ", next(p for r, p in rig.prompts if r == "angle_write"))
        self.assertEqual(out["usable"], 5)                                 # usable keeps its meaning


class TestProposal1PoolFill(unittest.TestCase):
    """PROPOSAL 1 (pending the orchestrator): the 07:14 build's angles held 4 clips that formed no line-up (36.52 s
    < 36.7 s; a short clip mid-order), while 3 cleared clips were never offered. The pool completes such an angle."""

    def test_an_angle_that_forms_no_line_up_is_completed_from_the_pool(self):
        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
        for m in ms:
            m["hook_onset"] = {"pass": m["moment_id"] not in ("s", "y")}   # as at 07:14: those two cannot open
        by = {m["moment_id"]: m for m in ms}
        a = angle(["h", "x", "s", "y"], "h")                          # the 07:14 shape: short "s" mid-order
        self.assertIsNone(PK.lineup_for(a, by, need_onset=True))      # 8.8 + 13.9 + 13.8 = 36.5 s < 36.7 s
        segs, added = PK.pool_fill(a, by)
        self.assertEqual([m["moment_id"] for m in segs][:3], ["h", "x", "y"])     # the angle's own first
        self.assertEqual(added, ["z"])                                            # the pool's clip after them
        self.assertTrue(PK.lineup_ok(segs)[0])
        self.assertEqual(PK.pool_fill(a, {k: by[k] for k in ("h", "x", "s", "y")}), (None, None))   # nothing to add
        lone = angle(["s", "y"], "s")                                  # neither can open: the pool would supply the
        self.assertEqual(PK.pool_fill(lone, by), (None, None))        # hook and a clip, more than half: no fill
        more = dict(pm("q", "F", 9.0), hook_onset={"pass": True})     # the preferred (fewest-clip) line-up has one
        pair = angle(["x", "y", "q"], "x")                            # own clip; the half rule is part of the search,
        segs, added = PK.pool_fill(pair, dict(by, q=more))            # so a line-up with half its own still comes
        self.assertGreaterEqual(2 * sum(m["moment_id"] in ("x", "y", "q") for m in segs), len(segs), segs)

    def test_the_pool_adds_only_its_best_swap_top_candidates(self):         # audit 0830 C2, qwen P2-1
        own = [dict(pm("h", "A", 8.8), hook_onset={"pass": True}), dict(pm("x", "B", 13.9), hook_onset={"pass": True})]
        shorts = [dict(pm(f"s{i}", f"S{i}", 5.0, rank=20.0 - i), hook_onset={"pass": False}) for i in range(10)]
        fit = dict(pm("f", "F", 14.5, rank=5.0), hook_onset={"pass": False})   # the only clip that reaches 36.7 s
        by = {m["moment_id"]: m for m in own + shorts + [fit]}
        a = angle(["h", "x"], "h")
        self.assertEqual(PK.pool_fill(a, by), (None, None))          # "f" ranks 11th: outside SWAP_TOP (10)
        by["f"] = dict(fit, rank_score=30.0)                          # in the top 10: it completes the angle
        segs, added = PK.pool_fill(a, by)
        self.assertEqual(([m["moment_id"] for m in segs], added), (["h", "x", "f"], ["f"]))

    def test_ruling_54_the_proposer_is_told_each_clips_placement_limits(self):
        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5),
              pm("o", "F", 7.3)]
        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"},
                  hooks={"o": (5, 5, 5), "z": (5, 5, 5)})             # o and z can open: rated as passing hooks
        rig.run()
        p = next(p for r, p in rig.prompts if r == "angle_write")
        self.assertIn('id=o | F | 7.3 s | under 8 s: only the hook or the LAST clip | "', p)   # audit 0855 C1, qwen
        self.assertIn('id=s | C | 6.9 s | under 8 s: only the LAST clip | "', p)            # short, cannot open
        self.assertIn('id=y | D | 13.8 s | cannot open (never the hook) | "', p)
        self.assertIn('id=z | E | 9.5 s | "', p)                       # no limit, nothing added
        self.assertIn('marked "only the hook or the LAST\nclip" is the first or the LAST id', p)
        self.assertIn('a clip marked "cannot open" is never the hook', p)
        short_opener = dict(pm("b", "F", 7.3), hook_onset={"pass": True})   # the 08:46 build's only formable hook
        self.assertEqual(PK.placement(short_opener), " | under 8 s: only the hook or the LAST clip")
        both = [short_opener] + [dict(m, hook_onset={"pass": True}) for m in (pm("c", "G", 13.9), pm("w", "H", 9.5))] + \
            [dict(pm("a", "I", 6.9), hook_onset={"pass": False})]     # 7.3 + 13.9 + 9.5 + 6.9 = 37.6 s
        segs = PK.lineup_for(angle(["b", "c", "w", "a"], "b"), {m["moment_id"]: m for m in both}, need_onset=True)
        self.assertEqual([m["moment_id"] for m in segs], ["b", "c", "w", "a"])   # lineup_for agrees: a short hook

    def test_the_build_records_the_pool_fill_and_judges_the_line_up(self):
        ms = [pm("h", "A", 8.8), pm("x", "B", 13.9), pm("s", "C", 6.9), pm("y", "D", 13.8), pm("z", "E", 9.5)]
        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
        out = rig.run()
        self.assertEqual(out["tried"][0]["pool_filled"], ["z"])
        self.assertEqual(rig.medley_calls[0][:3], ["h", "x", "y"])
        self.assertIsNotNone(out["package"])


class TestRuling57Fresh(unittest.TestCase):
    """RULING 57 (09:59): with a 72 h window, a line-up with at least one clip from the last 24 h is preferred over one
    with none, then the newest clips. The build stops at its first passing package, so the preference decides what is
    TRIED first: inside an angle and across angles. RULING 76 (18:08 Nov 13) superseded the 72 h window: a moment over
    12 h old is expired and never offered (the line-up preference itself is unchanged, and moot inside 12 h)."""

    def at(self, mid, ch, dur, hours_ago, **kw):
        return dict(pm(mid, ch, dur, **kw), published_at=(NOW - timedelta(hours=hours_ago)).isoformat(),
                    hook_onset={"pass": True})

    def test_a_line_up_with_a_fresh_clip_is_tried_first(self):
        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
              self.at("z", "D", 13.0, 5)]                                  # only z is under 24 h
        by = {m["moment_id"]: m for m in ms}
        a = angle(["h", "x", "y", "z"], "h")
        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by, need_onset=True)], ["h", "x", "y"])
        segs = PK.lineup_for(a, by, need_onset=True, now=NOW)              # without now: the proposer's earliest
        self.assertIn("z", [m["moment_id"] for m in segs])                 # with now: a fresh clip first
        self.assertTrue(PK.fresh_key(segs, NOW)[0])
        old = dict(by, z=self.at("z", "D", 13.0, 40))                      # nothing fresh: the newest clips next
        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, old, need_onset=True, now=NOW)], ["h", "x", "z"])
        self.assertFalse(PK.fresh_key([dict(ms[0], published_at=None)], NOW)[0])   # no readable time: never fresh
        unknown = [dict(m, published_at=None) for m in ms[:3]]              # audit 1006 C1 (qwen P1): all unknown
        self.assertLess(PK.fresh_key(unknown, NOW), PK.fresh_key(ms[:3], NOW))   # ranks below 50-70 h, never newest

    def test_the_angle_with_a_fresh_line_up_is_judged_first(self):
        """Since ruling 76: the 13-70 h moments are expired, never offered to the angle writer, and the line-up is
        built from the 12 h pool."""
        ms = [self.at("h", "A", 12.0, 13), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
              self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
        rig = Rig(ms, [["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])
        self.assertEqual(out["angles"][0]["hook"], "f")
        prompt = next(p for r, p in rig.prompts if r == "angle_write")
        for old in ("h", "x", "y"):
            self.assertNotIn(f"id={old} ", prompt)                            # never offered
            self.assertIn("ruling 76 (a)", out["unusable"][old])


class TestRuling41Search(unittest.TestCase):
    """Ruling 41 (04:58): when the clips-alone verdict fails, the segments rated below the bar are swapped at their
    place for the next by score from the whole cleared pool (a hook for the next hook, a clip for the next clip), the
    ones rated 4-5 kept; up to 8 line-ups per build; the bar unchanged."""

    def pool(self, *spec):
        out = {}
        for mid, ch, dur, rank, h2s in spec:
            m = dict(pm(mid, ch, dur, rank=rank), hook_onset={"pass": True})
            m["scores"] = dict(m["scores"], hook_first_2s=h2s)
            out[mid] = m
        return out

    def test_a_clip_below_the_bar_is_swapped_at_its_place_for_the_next_clip_by_rank(self):
        p = self.pool(("h", "A", 12.0, 9.0, 4), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
                      ("z", "D", 13.0, 5.0, 3), ("w", "E", 13.0, 8.0, 3), ("v", "B", 13.0, 9.5, 3))
        segs = [p["h"], p["x"], p["y"]]
        new, swaps = PK.swap_lineup(segs, {"x"}, p)
        self.assertEqual([m["moment_id"] for m in new], ["h", "v", "y"])     # v: the best rank, x's place, B again
        self.assertEqual(swaps, {"x": "v"})
        new, swaps = PK.swap_lineup(segs, {"x"}, p, avoid={"v"})
        self.assertEqual([m["moment_id"] for m in new], ["h", "w", "y"])     # then the next by rank
        self.assertTrue(PK.lineup_ok(new)[0])

    def test_a_hook_below_the_bar_is_swapped_for_the_next_hook_by_score(self):
        p = self.pool(("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
                      ("g", "D", 12.0, 1.0, 5), ("k", "E", 12.0, 9.9, 2))
        new, swaps = PK.swap_lineup([p["h"], p["x"], p["y"]], {"h"}, p)
        self.assertEqual(swaps, {"h": "g"})                                  # by hook_first_2s, not by rank
        p["g"]["hook_onset"] = {"pass": False}                               # a hook must still open (G17a)
        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], {"h"}, p)[1], {"h": "k"})

    def test_the_place_s_own_rule_comes_before_the_cap(self):        # audit 0510 C1, glm P1-3
        spec = [("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 1.0, 3), ("y", "C", 13.0, 9.0, 3)]
        spec += [(f"s{i}", f"S{i}", 5.0, 9.0 - i / 100, 3) for i in range(12)]        # 12 short clips ranked higher
        spec += [("f", "F", 14.0, 2.0, 3)]                                          # a full clip, ranked below them
        p = self.pool(*spec)
        new, swaps = PK.swap_lineup([p["h"], p["x"], p["y"]], {"x"}, p)              # x's place is not the last
        self.assertEqual(swaps, {"x": "f"})

    def test_no_swap_when_nothing_fits_the_line_up_rules(self):
        p = self.pool(("h", "A", 12.0, 9.0, 3), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
                      ("s", "D", 3.0, 9.0, 3))                               # 12 + 3 + 13 = 28 s < the medley's seconds
        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], {"x"}, p), (None, None))
        self.assertEqual(PK.swap_lineup([p["h"], p["x"], p["y"]], set(), p), (None, None))

    def test_lineup_for_s_own_line_ups_pass_lineup_ok(self):
        p = self.pool(("h", "A", 12.0, 9.0, 4), ("x", "B", 14.0, 9.0, 3), ("y", "C", 13.0, 9.0, 3),
                      ("z", "D", 13.0, 9.0, 3), ("w", "E", 6.0, 9.0, 3))
        for order in (["h", "x", "y", "z"], ["h", "w", "x", "y"], ["x", "h", "z", "w"]):
            segs = PK.lineup_for(angle(order, order[0]), p, need_onset=True, need_stand_alone=True)
            if segs is not None:
                self.assertEqual(PK.lineup_ok(segs), (True, "ok"), order)

    def test_a_failed_angle_never_swaps_its_hook_and_the_search_stops_at_8_line_ups(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
        rig = Rig(ms, [["h", "x", "y", "z"], ["g", "x", "y", "z"]],
                  [(False, [], None, "none"), (True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual([c[0] for c in rig.medley_calls], ["h", "g"])     # ruling 59 (c): h's angle ends, g's next
        self.assertIn("no through-line", out["tried"][0]["why"])
        self.assertIsNotNone(out["package"])
        many = [pm(c, c.upper(), 13.0) for c in "abcdefghijklmnop"]
        fails = [(False, [], {"clip_01": 2}, Rig.LINE)] * 12
        rig = Rig(many, [list("abcdefgh"), list("ijklmnop"), list("aceg")], fails, [])
        out = rig.run()
        self.assertEqual(len(rig.medley_calls), PK.LINEUPS_PER_BUILD)       # 8, over every angle
        self.assertEqual(out["search"]["lineups"], 8)
        self.assertTrue(all(c[0] in ("a", "i") for c in rig.medley_calls))  # each line-up keeps its angle's hook

class TestRuling37QuestionHook(unittest.TestCase):
    """Ruling 37: a clip ending on a question may be the HOOK only; the clips-alone verdict judges the join after it,
    which must be followable with no bridge (no bridge may follow a question; the render's R1 reads the sealed
    gates.medley flagged list)."""

    Q = "Why does Bitcoin keep falling every time Nvidia does?"

    def ms(self):
        return [dict(pm("h", "A", 12.0), text=self.Q), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 14.0)]

    def test_the_question_hook_test(self):
        self.assertTrue(PK.question_hook([{"text": self.Q + "  "}]))
        self.assertFalse(PK.question_hook([{"text": "Bitcoin is money."}]))
        self.assertFalse(PK.question_hook([]))

    def test_a_flagged_join_after_a_question_hook_re_lines_without_that_clip(self):
        rig = Rig(self.ms(), ["h", "x", "y", "z"], [(True, ["hook -> clip_01"], None, Rig.LINE),
                                                    (True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "y", "z"]])          # x dropped, never bridged
        self.assertIn("ruling 37", out["tried"][0]["why"])
        self.assertIsNotNone(out["package"])
        self.assertEqual(out["package"]["segments"][0]["text"], self.Q)

    def test_a_flagged_join_between_clips_is_bridged_as_usual(self):
        rig = Rig(self.ms(), ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)],
                  [{"text": "Next, a show on chips.", "cites": ["y"], "why": "no referent"}])
        out = rig.run()
        self.assertEqual(rig.write_calls[0][1][0], 1)                                     # the bridge after clip 1
        self.assertIsNotNone(out["package"])

    def test_ly_shape_refuses_a_question_hook_whose_first_join_was_flagged(self):
        pk = medley_pk(bridge="hook -> clip_01", after=0, flagged=["hook -> clip_01"], intro="Next, on chips.")
        pk["segments"][0]["text"] = self.Q
        ok, why = PK.ly_shape(pk)
        self.assertFalse(ok)
        self.assertTrue(any("ruling 37" in w for w in why), why)
        pk = medley_pk(flagged=[])                                     # must-pass (audit 0500 C1, glm): a question
        pk["segments"][0]["text"] = self.Q                             # hook, its first join followable, no bridge
        self.assertEqual(PK.ly_shape(pk), (True, []))
        self.assertEqual(PK.joins(PK.labels(4))[0], "hook -> clip_01")  # the join R1 reads, in production labels


class TestRuling34Screen(unittest.TestCase):
    """Ruling 34 (render side merged at 55315124): the topic test is the miner's about-Bitcoin screen the pin seals;
    the hook must pass it itself, a clip may complete the previous claim, and the MEDLEY must name Bitcoin once."""

    def check(self, *texts):
        return PK.stand_alone_check([{"text": t} for t in texts])

    def test_the_screen_is_the_topic_and_the_medley_must_name_bitcoin(self):
        r = self.check("The halving cut the new supply in half.", "Saylor keeps buying.", "Sats are the unit.")
        self.assertEqual([x["topic"]["pass"] for x in r["rows"]], [True, True, True])      # the screen, each one
        self.assertFalse(r["medley_names_bitcoin"]["pass"])                                  # but no "Bitcoin"
        self.assertFalse(r["ok"])
        r = self.check("The halving cut the new supply in half.", "Saylor keeps buying Bitcoin.",
                       "That was 25 % of the float.")                                       # completes the claim
        self.assertTrue(r["ok"], r["rows"])
        self.assertEqual(r["medley_names_bitcoin"]["segments"], ["clip_01"])
        self.assertEqual(r["screen"], E.BTC_SCREEN.pattern)
        r = self.check("Bitcoin is the hardest money.", "Saylor keeps buying.", "Sats are the unit.")
        self.assertTrue(r["ok"], r["rows"])                                                  # the hook alone names it
        self.assertEqual(r["medley_names_bitcoin"]["segments"], ["hook"])
        r = self.check("Gold is the oldest money.", "Bitcoin is the newest.", "Bitcoin wins.")
        self.assertFalse(r["ok"])                                                            # the hook must pass
        self.assertIn("the hook does not pass the miner's about-Bitcoin screen", r["rows"][0]["topic"]["why"])

    def test_a_moment_with_no_place_under_the_topic_rule_is_left_out(self):
        self.assertIn("ruling 34", PK.no_topic({"text": "Gold is the oldest money."}))
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
              dict(pm("g", "E", 13.0), text="But gold is the oldest money.")]          # fails BOTH rules
        out = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None]).run()
        self.assertIn("clip opens on 'but'", out["no_role"]["g"])
        self.assertIn("ruling 34", out["no_role"]["g"])                                 # both reasons named
        for t in ("Saylor keeps buying.", "That was 25 % of the float.", "Bitcoin is money."):
            self.assertIsNone(PK.no_topic({"text": t}), t)

    def test_every_medley_seals_the_screen_and_the_recompute_needs_it(self):
        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0))}
        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
                  "caption": {"text": "three clips", "cites": []}}
        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
        self.assertEqual(pk["btc_screen"], {"pattern": E.BTC_SCREEN.pattern, "source": E.BTC_SCREEN_SOURCE})
        pk["gates"] = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1}
                       for k in package_pin.required_gates(pk)}
        pk["gates"]["takeaway_value"]["text"] = package_pin.takeaway_line(pk)   # ruling 91: its takeaway, judged
        with self.assertRaises(package_pin.PinRefused):                 # no judged screen on the stand_alone row
            package_pin.to_pin(spk(pk), "test")
        pk["gates"]["stand_alone"]["screen"] = PK.stand_alone_check(pk["segments"])["screen"]   # what it judged
        pin = package_pin.to_pin(spk(pk), "test")
        mp = pin["moments_package"]
        self.assertEqual(mp["btc_screen"], pk["btc_screen"])
        args = (pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"])
        self.assertEqual(package_pin.seal(*args, mp.get("btc_screen")), mp["package_sha256"])   # check_pin_only's
        self.assertNotEqual(package_pin.seal(*args), mp["package_sha256"])                      # 7-argument call
        for bad in (None, {"pattern": "", "source": "s"}, {"pattern": "(", "source": "s"},
                    {"pattern": "x" * 501, "source": "s"}, {"pattern": "bitcoin"},
                    {"pattern": "bitcoin", "source": "s"}):         # compiles, but not the pattern it was judged with
            p = dict(spk(pk), btc_screen=bad)
            with self.assertRaises(package_pin.PinRefused):
                package_pin.to_pin(p, "test")


class TestAdReadBeforeTheAngle(unittest.TestCase):
    """The exclusion screen's deterministic part (moments.ad_read_marker) runs before step A, so no angle is built
    around a moment the package stage would refuse. The 03:39 build lost its line-up's hook to it after the write."""

    def test_the_marker_in_the_moment_or_the_sentence_before_it(self):
        import moments as M
        self.assertEqual(M.ad_read_marker("Bitcoin is money.", "Use my code at checkout. Link in the description."),
                         "ad-read marker 'Link in the description' in the sentence before it")
        self.assertEqual(M.ad_read_marker("This episode is sponsored by a wallet. Bitcoin is money.", ""),
                         "ad-read marker 'sponsored' in the moment")
        self.assertIsNone(M.ad_read_marker("Bitcoin is money.", "Link in the description. Bitcoin rose today."))
        self.assertIsNone(M.ad_read_marker("Bitcoin is money.", None))

    def test_ad_read_out_reads_the_same_context_as_the_exclusion_screen(self):
        import context_integrity as CI
        ctxs = {"a": ("Grab it now. Link in the description.", "x"), "b": ("Bitcoin rose today.", "x"),
                "c": (None, None)}
        saved = CI.context_around
        try:
            CI.context_around = lambda src, *a: ctxs[src]
            ms = [dict(pm(k, k.upper(), 12.0), sentences=[0, 0], words=[0, 1]) for k in ("a", "b", "c", "d")]
            got = PK.ad_read_out(ms, {"va": "a", "vb": "b", "vc": "c"})       # d has no Source: left to the package
        finally:
            CI.context_around = saved
        self.assertEqual(got, {"a": "ad-read marker 'Link in the description' in the sentence before it"})
        try:                                     # DIFFERENTIAL (audit 0352 C1, glm): the package stage's own screen,
            CI.context_around = lambda src, *a: ctxs[src]     # exclusion_for, on the same moments and context
            never = type("R", (), {"call": lambda *a, **k: (_ for _ in ()).throw(AssertionError("no model call"))})()
            v = PK.exclusion_for(never, ms[0], {"va": "a", "vb": "b"}, {})
            self.assertEqual((v["verdict"], v["why"], v["backend"]), ("exclude", got["a"], "deterministic"))
            with self.assertRaisesRegex(AssertionError, "no model call"):      # b: no marker, so the package stage
                PK.exclusion_for(never, ms[1], {"va": "a", "vb": "b"}, {})      # goes past its deterministic part to
            self.assertNotIn("b", got)                                          # the model verdict; nor refused here
            bad = [dict(ms[0], sentences=[0])]                                  # a field the lookup cannot read:
            self.assertEqual(PK.ad_read_out(bad, {"va": "a"}), {})              # left to the package stage (qwen C2)
        finally:
            CI.context_around = saved

    def test_build_leaves_an_ad_read_moment_out_before_the_angle(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0)]
        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
        saved = PK.ad_read_out
        try:
            PK.ad_read_out = lambda ms_, sources: {"q": "ad-read marker 'promo code' in the moment"}
            out = rig.run()
        finally:
            PK.ad_read_out = saved
        self.assertEqual(out["ad_read"], {"q": "ad-read marker 'promo code' in the moment"})
        self.assertFalse(any("id=q " in p for role, p in rig.prompts if role == "angle_write"))
        self.assertIsNotNone(out["package"])


class TestNoVoiceRealGates(unittest.TestCase):
    """Audit 2240 C2 (glm N8): a no-voice package through the REAL VO-fidelity and context-integrity decisions (canned
    model replies, no stubbed gate): every required row, the medley rows included, exactly PASS, and the pin is
    written."""

    def test_a_no_voice_package_can_pass_every_gate_and_pin(self):
        import context_integrity as CI
        import vo_fidelity as VF
        from test_gates import a_item, c_item
        by = {m["moment_id"]: dict(m, text=t) for m, t in (
            (pm("h", "A", 15.0), "Bitcoin is a global free market."), (pm("x", "B", 17.0), "Nobody can stop Bitcoin."),
            (pm("y", "C", 18.0), "Bitcoin rules apply to everyone."))}
        fields = {"takeaway": None, "bridge": None, "bridge_after": None,
                  "title": {"text": "The market no government owns", "cites": []},
                  "caption": {"text": "no ruler, just rules", "cites": []},
                  "no_voice": {"why": "the takeaway failed its gates twice (test)", "added_clip": None,
                               "lineup_before": ["h", "x", "y"]}}
        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y), no voice")
        labs = [sg["label"] for sg in pk["segments"]]
        med = dict(verdict(labs), flagged=[], backend="xai:grok", measured=True, replayed=False)
        pk["medley"] = med
        cheap, det, dup, rt_ok, r4_res = PK.cheap_checks(pk, {}, [], NOW)
        self.assertEqual(cheap, [])                                # 50 s of clips + the tail: 64.3 s, no VO line
        T0 = {t: "no" for t in VF.COMMENTARY_TESTS}
        lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
        r = Canned(fidelity_verdict=[{"claims": [
            {"line": x["slot"], "words": x["text"], "class": "commentary", "claim": "c", "supported": "n/a",
             "support": [], "tests": T0} for x in lines]}])
        fid = VF.check(r, PK.fidelity_segments(pk, {}), lines, "heimdall", 7, {"channels": ["A", "B", "C"]}, [],
                       "deepseek")
        self.assertTrue(fid["ok"], fid["violations"])
        ctx_ = {lb: {"text": CI.mark([("before.", False), (sg["text"], True), ("after.", False)]), "title": "t",
                     "channel": sg["channel"]} for lb, sg in zip(labs, pk["segments"])}
        import itertools
        rel = [{"labels": [a, b], "relation": "none"} for a, b in itertools.combinations(labs, 2)]   # every pair
        B = {"takeaways": [{"label": lb, "asserts": "p", "certainty": "certain", "polarity": "neutral"} for lb in labs],
             "relations": rel}
        rc = Canned(context_verdict=[{"excerpts": [a_item(lb) for lb in labs]}, {"pairs": [c_item(lb) for lb in labs]}],
                    viewer_takeaway=[B, B])
        cx = CI.check_contexts(rc, pk, ctx_, writer_vendor="heimdall", writer_family="deepseek")
        self.assertTrue(cx["ok"], cx.get("violations"))
        a_lab = {lb: dict(Rig.A_OK) for lb in labs}
        exc = {sg["moment_id"]: {"verdict": "keep", "measured": True, "replayed": False, "backend": "xai:grok"}
               for sg in pk["segments"]}
        tru = {sg["moment_id"]: {"ok": True, "edges": {"cuttable": True}, "replayed": False, "model": "scribe_v1"}
               for sg in pk["segments"]}
        coh = dict(med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
        pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
                                   shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"},
                                   stand=PK.stand_alone_check(pk["segments"]),
                                   visual=[{"measured": True, "replayed": False, "backend": "xai_vision:grok-4.7",
                                            "flags": []} for _ in pk["segments"]],      # ruling 70
                                   out_edge=[dict(Rig.OUT_EDGE_OK) for _ in pk["segments"]])   # RULING 162 (1)
        self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))

    def test_a_published_time_without_an_offset_fails_before_any_paid_verdict(self):
        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0))}
        by["x"] = dict(by["x"], published_at="2026-11-12T01:00:00")         # naive: no offset
        fields = {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None, "bridge_after": None,
                  "title": {"text": "No ruler", "cites": []}, "caption": {"text": "three clips", "cites": []}}
        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
        pk["medley"] = {"measured": True, "flagged": []}
        cheap = PK.cheap_checks(pk, {}, [], NOW)[0]
        self.assertTrue(any(v["rule"] == "RECENCY" and "segment 1" in v["detail"] for v in cheap), cheap)


class TestInventoryRows(unittest.TestCase):
    def test_the_two_medley_rows(self):
        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
               "backend": "x", "replayed": False, "measured": True}
        coh = {"backend": "x", "replayed": False, "measured": True}
        args = (fid, [], True, (True, ""), {"ok": True, "measured": True, "replayed": False, "backends": {}},
                {"hook": {"backend": "x", "replayed": False}}, {"h": {"verdict": "keep", "measured": True,
                                                                      "replayed": False}},
                {"h": {"ok": True, "edges": {"cuttable": True}, "replayed": False, "model": "s"}}, True, coh)
        self.assertNotIn("medley", PK.inventory(*args))
        g = PK.inventory(*args, medley=(True, {"backend": "x", "replayed": False, "measured": True, "flagged": []}),
                         shape=(True, []))
        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("PASS", "PASS"))
        g = PK.inventory(*args, medley=(False, {"measured": False, "flagged": None}), shape=(False, ["two bridges"]))
        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("NOT RUN", "FAIL"))
        self.assertEqual(g["ly_shape"]["why"], ["two bridges"])


class TestReportedCost(unittest.TestCase):
    def test_the_ledger_keeps_the_vendors_own_figure_beside_the_estimate(self):
        import tempfile
        import providers as P
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "SPEND.json")
            r = P.Router(env_path=None, spend_path=path, limit_usd=10.0)
            b = r.backends["xai:grok-4.20-0309-reasoning"]
            r._settle(None, b, {"in": 1000, "out": 1000, "usd_reported": 0.002}, 0.03, "check")
            r._settle(None, b, {"in": 1000, "out": 1000}, 0.03, "check")
            led = json.load(open(path))
            self.assertAlmostEqual(led["usd_estimate"], 0.06, places=6)
            self.assertAlmostEqual(led["usd_reported"], 0.002, places=8)
            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.03, places=6)
            self.assertEqual(led["by_backend"][b.name]["reported_calls"], 1)
        self.assertEqual(P._reported(None), {})
        self.assertEqual(P._reported(True), {})
        self.assertEqual(P._reported(-1), {})
        self.assertEqual(P._reported(float("inf")), {})      # audit 2030 C3 (glm P2-1): a finite figure only
        self.assertEqual(P._reported(float("nan")), {})
        self.assertEqual(P._reported(0.5), {"usd_reported": 0.5})


class TestRuling91MedleyHalf(unittest.TestCase):
    """RULING 91, its MEDLEY half ('22:53' Nov 13): "The same value verdict also applies to a MEDLEY's takeaway going
    forward: a medley that loses its takeaway falls back to L-y's no-voice shape only if its clips meet the seconds;
    otherwise the takeaway may be rewritten once." The row "takeaway_value" was agreed with the integrator (05:5x ET
    Nov 14): status PASS, replayed false, "text" the takeaway it judged. ITEM 2 (orchestrator 09:35 ET Nov 24: "One
    write, one judge ... no retry loop") withdraws the rewrite: a lost takeaway is NO closing line, the no-voice shape
    when the clips meet the seconds, else the line-up rests."""
    SHORT = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]          # 39 s: under 45.7 s with no VO line
    FITS = [pm("h", "A", 16.0), pm("x", "B", 16.0), pm("y", "C", 16.0)]           # 48 s: 62.3 s with no VO line
    NEW = ("Nobody bends these rules, and that is exactly why they keep working for everyone who holds them "
           "anywhere.")                                                            # 18 words: lands 39 s of clips
    MED = [(True, [], None, Rig.LINE)]
    ALONE = [{"takeaway": {"text": t, "cites": []}} for t in (       # replies for the line written alone: ITEM 2
        #   never asks for them (they stay unconsumed on the router)
        "Nobody gets to bend these rules, and that is exactly why they last when it counts.",
        "Nobody gets to bend these rules, and that is precisely why they hold when it counts.",
        "Nobody gets to bend these rules, which is exactly why they hold up when it counts.")]
    LOST4 = [{"adds": "no", "why": "it restates clip_02"}] * 4        # value answers for up to 4 writes: ITEM 2 asks ONE

    def test_a_takeaway_that_earns_its_place_ships_with_its_row_bound_to_its_text(self):
        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None])
        pk = rig.run()["package"]
        row = pk["gates"]["takeaway_value"]
        self.assertEqual((row["status"], row["replayed"], row["n"]), ("PASS", False, 1))
        self.assertEqual(row["text"], pk["vo"]["bridges"][-1])                   # the line it judged is the one spoken
        self.assertEqual(row["answers"], {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes"})
        self.assertEqual((row["words"], row["cap"]), (16, 20))
        self.assertEqual(rig.value_calls[0]["segs"], ["h", "x", "y"])            # the medley's clips, in play order
        self.assertIn("heimdall", rig.value_calls[0]["wv"])                      # off the writer's vendor and family
        self.assertIn("deepseek", rig.value_calls[0]["wf"])
        self.assertEqual(pk["checks"]["value"]["text"], Rig.LINE)
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertEqual(mp["gates"]["takeaway_value"]["text"], mp["edl_vo"]["bridges"][-1]["text"])
        self.assertEqual(package_pin.takeaway_line(mp), Rig.LINE)

    def test_a_lost_takeaway_on_clips_that_meet_the_seconds_ships_no_voice_and_no_paid_gate_judged_it(self):
        """RULING 162 (2) with ITEM 2: the value grade is a requirement; ONE write, ONE judge; when it loses, NO closing
        line: L-y's no-voice shape with its one flag. The three replies for the line alone are never asked for."""
        rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=self.LOST4, lines=self.ALONE)
        out = rig.run()
        pk = out["package"]
        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])   # its OWN clips, none added
        self.assertEqual((pk["vo"]["intro"], pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]), (None, [], []))
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
        self.assertIn("ruling 91", pk["no_voice"]["why"])
        self.assertIn("adds no", pk["no_voice"]["why"])
        self.assertIsNone(pk["no_voice"]["added_clip"])
        self.assertEqual((pk["no_voice"]["value"]["adds"], pk["no_voice"]["value"]["text"]),
                         ("no", Rig.LINE))                                       # the one write's loss is named
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
        self.assertNotIn("takeaway_value", pk["gates"])                          # no takeaway: no row
        self.assertTrue(NV_FLAG_OK(pk["gates"]), pk["gates"])                    # RULING 162 (2): its one flag
        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))  # ITEM 2: one write, one judge
        self.assertEqual(len(rig.router.answers["angle_write"]), 3)              # the replies for it alone: unasked
        self.assertIn("item 2", out["tried"][0]["why"])
        att = out["tried"][0]["attempts"][0]
        self.assertEqual(att["value"]["adds"], "no")
        self.assertNotIn("verdict_classes", att)                                 # asked before any paid gate
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
        self.assertIn("ruling 91", pk["checks"]["coherence"]["note"])

    def test_a_lost_takeaway_on_short_clips_is_never_rewritten_and_the_line_up_rests(self):
        """REPLACES 'a lost takeaway on short clips gets one rewrite alone, told why' (ruling 91's one rewrite is
        withdrawn by ITEM 2: "no retry loop"): on 39 s of clips no no-voice line-up lands, so the line-up rests after
        its one write; the rewrite offered is never asked for, no prompt tells the loss."""
        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
                  values=[{"adds": "no", "no_restate": "no", "why": "it restates the clips"}])
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE])        # one write, one judge
        self.assertEqual(len(rig.write_calls), 1)
        self.assertFalse([p for r, p in rig.prompts if r == "angle_write" and "Your takeaway was refused" in p])
        self.assertEqual(rig.router.answers["angle_write"], [{"takeaway": {"text": self.NEW, "cites": []}}])
        tried = out["tried"][0]
        self.assertIn("ruling 91: the takeaway did not earn its place", tried["why"])
        self.assertIn("no one clip of the angle lands", tried["no_voice"]["why_not"])
        self.assertEqual([x["text"] for x in tried["value_lost"]], [Rig.LINE])

    def test_a_lost_takeaway_takes_the_one_no_voice_shape_with_the_added_clip(self):
        """The orchestrator's 07:30 ruling (A): "the no-voice shape is one shape whatever removed the takeaway (two
        failed writes, or the value verdict's no): clips back to back, the sign-off, and the added clip when the seconds
        need it, each added clip passing every clip gate and the joins as usual." No rewrite is spent."""
        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # 39 s + z = 52 s with no VO line
        rig = Rig(ms, ["h", "x", "y", "z"], self.MED * 2, [None], values=self.LOST4, lines=self.ALONE)
        out = rig.run()
        pk = out["package"]
        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])
        self.assertEqual(pk["no_voice"]["added_clip"], "z")
        self.assertIn("one clip added (z)", pk["no_voice"]["why"])
        self.assertEqual(pk["no_voice"]["value"]["adds"], "no")
        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])          # the new line-up judged on the clips alone
        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))  # ITEM 2: one write, one judge
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
        self.assertTrue(NV_FLAG_OK(pk["gates"]), pk["gates"])
        self.assertNotIn("takeaway_value", pk["gates"])
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})

    def test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite(self):
        """As on ruling 3's path: the added clip's line-up fails the clips-alone verdict, so there is no package, and
        the takeaway is not rewritten (a no-voice line-up existed)."""
        ms = self.SHORT + [pm("z", "D", 13.0)]
        rig = Rig(ms, ["h", "x", "y", "z"], self.MED + [(False, [], {"clip_03": 2}, Rig.LINE)], [None],
                  values=self.LOST4, lines=self.ALONE)
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual(len(rig.value_calls), 1)                                # ITEM 2: one write, then
        self.assertIn("ruling 91", out["tried"][0]["why"])
        self.assertIn("fails on the clips alone", out["tried"][0]["why"])

    def test_a_doomed_clip_is_never_the_added_clip(self):
        """Audit 0734 C1 (qwen's condition): z fails exclusion in angle 1's line-up, so it is doomed for the whole build.
        Angle 2's takeaway then loses its value verdict on 39 s of clips: nv_order skips z, so no no-voice line-up
        exists, and (ITEM 2: no rewrite) the line-up rests; z is never judged in a line-up again."""
        ms = self.SHORT + [pm("z", "D", 13.0)]
        rig = Rig(ms, [["h", "z", "y"], ["h", "x", "y", "z"]], self.MED * 2, [None, None], excluded={"z"},
                  lines=[{"takeaway": {"text": self.NEW, "cites": []}}], values=[{"adds": "no"}])
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertIn("'z': 'exclusion'", out["tried"][0]["why"])                # doomed in angle 1
        self.assertEqual(rig.medley_calls, [["h", "z", "y"], ["h", "x", "y"]])   # never added back
        self.assertIn("no one clip of the angle lands", out["tried"][-1]["no_voice"]["why_not"])
        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE])      # one write, no rewrite

    def test_a_lone_caption_failure_with_a_clip_failing_its_gate_ends_cleanly(self):
        """Audit 0734 C2 (grok): the no-voice line-up's caption fails alone AND its added clip fails exclusion. The
        clip's gate ends it first (return None before any verdict is read): no fixed caption, no unbound name."""
        restore = self.contexts_pass()
        try:
            rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None],
                      values=self.LOST4, lines=self.ALONE, caption=self.UPPER, excluded={"z"})
            out = rig.run()
        finally:
            restore()
        self.assertIsNone(out["package"])
        nv = out["tried"][0]["no_voice"]
        self.assertEqual(nv["why_not"], "a clip fails exclusion, the second pass or CUTTABLE")
        self.assertNotIn("caption_fallback", nv)

    def test_a_value_loss_leaves_a_registered_line_up_to_the_registry(self):
        """Audit 0734 C2 (glm): on ruling 91's path too, the only clip that would land the seconds forms a registered
        line-up, so it is left to the registry (ruling 66): no no-voice line-up exists, the reason is recorded, and
        (ITEM 2: no rewrite) the line-up rests."""
        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED, [None],
                  lines=[{"takeaway": {"text": self.NEW, "cites": []}}], values=[{"adds": "no"}],
                  registered={("h", "x", "y", "z"): {"key": "h+x+y+z", "state": "resting", "until": None,
                                                     "source": "proof/ledger_x", "index": 0}})
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])                    # h+x+y+z never judged
        self.assertIsNone(out["package"])
        nv = out["tried"][0]["no_voice"]
        self.assertEqual(nv["registered_skipped"], ["h+x+y+z"])
        self.assertIn("left to the registry", nv["why_not"])
        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE])      # one write, no rewrite

    def test_the_first_loss_ends_the_line_up_when_no_no_voice_line_up_exists(self):
        """REPLACES 'a second loss ends the line-up when no no-voice line-up exists' (ITEM 2: one write): no clip of the
        angle can be added (h, x, y are all it has), so the FIRST loss ends the line-up; the three rewrites offered are
        never asked for and never judged."""
        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None],
                  lines=[{"takeaway": {"text": self.NEW, "cites": []}}] + self.ALONE[:2],
                  values=[{"adds": "no"}, {"missed": "no"}, {"adds": "no"}, {"adds": "no"}])
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE])       # one judge, on the one write
        self.assertEqual(len(rig.router.answers["angle_write"]), 3)              # the rewrites: never asked for
        self.assertIn("no one clip of the angle lands", out["tried"][0]["no_voice"]["why_not"])   # then no shape
        self.assertIn("ruling 91", out["why_none"])

    def test_no_verdict_is_a_loss(self):
        rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"measured": False}])
        pk = rig.run()["package"]
        self.assertIn("no verdict", pk["no_voice"]["why"])
        self.assertFalse(pk["no_voice"]["value"]["measured"])
        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
                  values=[{"measured": False}, {"measured": False}])
        out = rig.run()
        self.assertIsNone(out["package"])                                       # nothing measured is never a pass
        self.assertEqual(len(rig.value_calls), 1)                               # ITEM 2: no second write to judge

    def test_ruling_3_is_unchanged_and_no_value_verdict_judges_a_takeaway_its_cheap_gates_refuse(self):
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None], takeaways=bad)
        out = rig.run()
        self.assertEqual(rig.value_calls, [])                                    # refused by house style first
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
        self.assertEqual(out["package"]["no_voice"]["added_clip"], "z")          # ruling 3 may still add a clip
        self.assertNotIn("value", out["package"]["no_voice"])

    @staticmethod
    def contexts_pass():
        """context_integrity stubbed to a measured pass (the fixed caption's own context run calls it directly);
        returns the restore function."""
        import context_integrity as CI
        saved = (CI.check_contexts, CI.contexts_from_sources)
        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
                                             "backends": {"B": "xai", "C": "xai"}}
        CI.contexts_from_sources = lambda *a, **k: {}

        def restore():
            CI.check_contexts, CI.contexts_from_sources = saved
        return restore

    UPPER = "Nobody Bends These Rules."                           # house style: a caption is all lowercase
    FIXED = "nobody bends the rules\na / b / c"                   # ruling 65 (b): the title lowercase, then the shows

    def test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption(self):
        """The orchestrator's 07:30 ruling (C): "on a no-voice path, when only the caption fails its gates, ruling 65
        (b)'s fixed caption is used and the line-up goes on (caption_fallback: true, as there)."""
        restore = self.contexts_pass()
        try:
            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=self.LOST4, lines=self.ALONE,
                      caption=self.UPPER)
            out = rig.run()
        finally:
            restore()
        pk = out["package"]
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
        self.assertTrue(pk["caption_fallback"])
        self.assertEqual(pk["caption"], self.FIXED)
        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "caption"), self.FIXED)
        self.assertEqual(pk["title"], "Nobody bends the rules")                  # the title as written and gated
        cf = out["tried"][0]["no_voice"]["caption_fallback"]
        self.assertEqual((cf["written"], cf["fixed"]), (self.UPPER, self.FIXED))
        self.assertTrue(cf["refused"])
        self.assertTrue(NV_FLAG_OK(pk["gates"]), pk["gates"])
        self.assertIn("ruling 65 b", pk["checks"]["fidelity"]["backend"])        # no model judged the fixed line
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertTrue(mp["caption_fallback"])
        self.assertEqual(mp["caption"], self.FIXED)

    def test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption(self):
        restore = self.contexts_pass()
        try:
            bad = TestRuling66Amended().failing("caption", "it says the clips agree", "VERDICT_NO")
            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=self.LOST4, lines=self.ALONE,
                      fids=[bad])
            out = rig.run()
        finally:
            restore()
        pk = out["package"]
        self.assertTrue(pk["caption_fallback"])
        self.assertEqual(pk["caption"], self.FIXED)
        self.assertTrue(NV_FLAG_OK(pk["gates"]), pk["gates"])
        self.assertEqual(out["tried"][0]["no_voice"]["caption_fallback"]["refused"][0]["rule"], "VERDICT_NO")

    def test_c_a_failing_title_still_holds_and_so_do_a_title_and_caption_together(self):
        """"The title keeps ruling 65 (c)": no fixed title. A title failing alone, or with the caption, holds."""
        restore = self.contexts_pass()
        try:
            title_bad = TestRuling66Amended().failing("title", "it names no show", "VERDICT_NO")
            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad])
            out = rig.run()
            self.assertIsNone(out["package"])
            self.assertIn("title / caption fail", out["tried"][0]["no_voice"]["why_not"])
            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad],
                      caption=self.UPPER)                                       # both lines fail: no lone caption
            out = rig.run()
            self.assertIsNone(out["package"])
            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
        finally:
            restore()

    def test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends(self):
        """As there (ruling 65 b): the fixed line has no model verdict, but context integrity on the package as it will
        be sealed still decides. A failing run ends the line-up; nothing ships unchecked."""
        import context_integrity as CI
        saved = (CI.check_contexts, CI.contexts_from_sources)
        failing = {"ok": False, "violations": [{"rule": "STRONGER", "segment": "hook", "detail": "x"}], "measured": True,
                   "replayed": False, "backends": {"B": "xai", "C": "xai"}}
        unmeasured = {"ok": False, "violations": [], "measured": False, "replayed": False,     # audit 0734 C3 (grok):
                      "error": "ProviderError: no verdict", "backends": {}}                    # nothing measured
        for run in (failing, unmeasured):
            CI.check_contexts = lambda *a, **k: dict(run)
            CI.contexts_from_sources = lambda *a, **k: {}
            try:
                rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=self.LOST4, lines=self.ALONE,
                          caption=self.UPPER)
                out = rig.run()
            finally:
                CI.check_contexts, CI.contexts_from_sources = saved
            self.assertIsNone(out["package"], run)
            nv = out["tried"][0]["no_voice"]
            self.assertIn("the fixed caption", nv["why_not"], run)
            self.assertEqual(nv["caption_fallback"]["fixed"], self.FIXED, run)

    def test_c_ruling_3s_no_voice_path_takes_the_fixed_caption_too(self):
        """(C) covers either no-voice path: the takeaway failed its gates twice (ruling 3), clip z is added, and the
        latest write's caption, failing alone, becomes the fixed line."""
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        restore = self.contexts_pass()
        try:
            rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
                      takeaways=bad, caption=self.UPPER)
            out = rig.run()
        finally:
            restore()
        pk = out["package"]
        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
        self.assertEqual(pk["no_voice"]["added_clip"], "z")
        self.assertTrue(pk["caption_fallback"])
        self.assertEqual(pk["caption"], "nobody bends the rules\na / b / c / d")
        self.assertEqual(rig.value_calls, [])                                  # house style refused both takeaways first

    def test_the_real_verdict_runs_inside_the_build_and_its_row_seals(self):
        """build() with package.takeaway_value itself (not the Rig's stub), only the router faked: a clear yes seals
        the row from the real record; an answer out of contract is rejected and is no verdict (the no-voice shape)."""
        yes = {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "a point of its own"}
        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], real_value=True)
        rig.router.answers["coherence_verdict"] = [yes]
        pk = rig.run()["package"]
        row = pk["gates"]["takeaway_value"]
        self.assertEqual((row["status"], row["text"], row["by"], row["words"]), ("PASS", Rig.LINE,
                                                                                 "fake:coherence_verdict", 16))
        self.assertEqual(rig.value_calls, [])                                    # the stub never ran
        package_pin.to_pin(spk(pk), "test")
        rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], real_value=True)
        rig.router.answers["coherence_verdict"] = ["not json"]
        pk = rig.run()["package"]
        self.assertIn("no verdict", pk["no_voice"]["why"])
        self.assertEqual(rig.router.rejected, ["fake:coherence_verdict"])

    def test_a_takeaway_refused_by_fidelity_gets_no_alone_gate_and_no_rewrite(self):
        """REPLACES 'the rewrite after a takeaway alone is judged on its own new text' (audit 0608 C2): its premise (two
        full writes, the takeaway alone, then ruling 91's forced rewrite through takeaway_alone_gates) is gone with
        ITEM 2. The takeaway failing the fidelity verdict in its ONE write is never rewritten, and takeaway_alone_gates
        never runs: its own fidelity check is never called."""
        import context_integrity as CI
        import vo_fidelity as VF
        seen = []

        def one(router, segs, lns, *a, **k):              # takeaway_alone_gates' own VF.check: must never run
            seen.append([ln["text"] for ln in lns])
            return {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
                    "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
                    "verdict": {"ok": True, "violations": [], "classes": {lns[0]["slot"]: ["commentary"]},
                                "claims": []}}
        saved = (VF.check, CI.check_contexts, CI.contexts_from_sources)
        VF.check = one
        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
                                             "backends": {"B": "xai", "C": "xai"}}
        CI.contexts_from_sources = lambda *a, **k: {}
        try:
            failing = TestRuling66Amended().failing()
            rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None, None], fids=[failing],
                      lines=[{"takeaway": {"text": self.NEW, "cites": []}}], values=[{}])
            out = rig.run()
        finally:
            VF.check, CI.check_contexts, CI.contexts_from_sources = saved
        self.assertIsNone(out["package"])
        self.assertEqual(seen, [])                                               # no alone gate ever ran
        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE])
        self.assertEqual(len(rig.write_calls), 1)
        self.assertFalse([a for a in out["tried"][0]["attempts"] if a.get("takeaway_alone")])
        self.assertEqual(rig.router.answers["angle_write"], [{"takeaway": {"text": self.NEW, "cites": []}}])

    def test_the_line_up_records_every_takeaway_with_its_value(self):
        """Every takeaway written is recorded with its value verdict; with ITEM 2 a line-up writes ONE."""
        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
                  values=[{"short": "no"}])
        out = rig.run()
        self.assertEqual([(t["write"], t["value"]["ok"], t["value"]["short"]) for t in out["takeaways"]],
                         [(1, False, "no")])
        self.assertIsNone(out["package"])                                        # its loss: no line, no shape (39 s)

class TestTakeawayValueVerdict(unittest.TestCase):
    """package.takeaway_value: the spotlight's value contract (spotlight.parse_value) over a medley's clips."""
    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
    LINE = "Nobody bends these rules, so nobody has to trust anyone to keep them."
    YES = {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "a point the clips do not make"}

    def ask(self, answer, line=LINE):
        r = Canned(coherence_verdict=[answer] if answer is not None else [])
        prompts, inner = [], r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append((role, prompt, a, k)), inner(role, prompt, *a, **k))[1]
        return r, PK.takeaway_value(r, self.SEGS, ctx(), line, {"heimdall"}, {"deepseek"}), prompts

    def test_four_clear_yeses_inside_the_cap_pass_off_the_writers(self):
        r, v, prompts = self.ask(self.YES)
        self.assertTrue(v["ok"] and v["measured"])
        self.assertEqual((v["text"], v["words"], v["cap"], v["backend"]), (self.LINE, 13, 20, "fake:coherence_verdict"))
        self.assertEqual(r.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})])   # never the writer's vendor
        self.assertEqual(prompts[0][2][:2], (400, 7))                                     # one verdict per text: seed 7

    def test_any_answer_short_of_a_clear_yes_fails(self):
        for k in ("adds", "no_restate", "missed", "short"):
            r, v, _ = self.ask(dict(self.YES, **{k: "no"}))
            self.assertTrue(v["measured"], k)
            self.assertFalse(v["ok"], k)

    def test_the_cap_is_counted_in_code(self):
        long_ = " ".join(["rules"] * 21)
        r, v, _ = self.ask(self.YES, line=long_)                                 # the model said "short": yes
        self.assertEqual((v["words"], v["ok"]), (21, False))
        r, v, _ = self.ask(self.YES, line=" ".join(["rules"] * 20))
        self.assertTrue(v["ok"])

    def test_an_answer_out_of_contract_is_no_verdict_and_is_rejected(self):
        for bad in ({"adds": "maybe", "no_restate": "yes", "missed": "yes", "short": "yes", "why": "w"},
                    {"adds": "yes", "no_restate": "yes", "missed": "yes", "short": "yes"},           # no why
                    dict(self.YES, extra="yes"), "not json"):
            r, v, _ = self.ask(bad)
            self.assertEqual((v["measured"], v["ok"]), (False, False), bad)
            self.assertEqual(r.rejected, ["fake:coherence_verdict"], bad)       # never served again

    def test_no_back_end_is_no_verdict_and_nothing_is_rejected(self):
        r, v, _ = self.ask(None)
        self.assertEqual((v["measured"], v["ok"], r.rejected), (False, False, []))
        self.assertIn("ProviderError", v["why"])

    def test_the_prompt_shows_every_clip_in_play_order_then_the_line_and_the_cap(self):
        segs = [dict(m, text=f'Bitcoin "{m["moment_id"]}" said.') for m in self.SEGS]
        r = Canned(coherence_verdict=[self.YES])
        seen, inner = [], r.call
        r.call = lambda role, prompt, *a, **k: (seen.append(prompt), inner(role, prompt, *a, **k))[1]
        PK.takeaway_value(r, segs, ctx(), 'He said "rules".', set(), set())
        p = seen[0]
        self.assertLess(p.index("CLIP 1 (on A)"), p.index("CLIP 2 (on B)"))
        self.assertLess(p.index("CLIP 3 (on C)"), p.index("LINE:"))
        self.assertIn("CLIP 2 (on B): \"Bitcoin 'x' said.\"", p)                # quotes inside a quote are neutralised
        self.assertIn("LINE: \"He said 'rules'.\"", p)
        self.assertIn('"short": is the line 20 words or fewer?', p)
        self.assertIn("SECURITY", p)                                             # the quotes are untrusted data


class TestTakeawayValueRow(unittest.TestCase):
    """package_pin's half of the row (agreed with the integrator 05:5x ET Nov 14)."""

    def pk(self, **kw):
        return TestMedleyPackageAndPin().build(**kw)

    def test_required_only_for_a_medley_that_carries_a_takeaway(self):
        pk = self.pk()
        self.assertIn("takeaway_value", package_pin.required_gates(pk))
        nv = dict(pk, vo=dict(pk["vo"], bridges=[], bridges_after_clip=[]), no_voice={"why": "x"})
        self.assertNotIn("takeaway_value", package_pin.required_gates(nv))       # the no-voice shape: no row
        self.assertNotIn("takeaway_value", package_pin.required_gates({"shape": "medley"}))
        self.assertNotIn("takeaway_value", package_pin.required_gates(dict(pk, shape=None)))   # only a medley's
        self.assertNotIn("takeaway_value", package_pin.required_gates({"shape": "spotlight", "vo": {"closing": "x"}}))

    def test_the_takeaway_is_the_line_after_the_last_clip_never_the_bridge(self):
        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
        pk = self.pk(bridge=b, k=1, n=4)
        self.assertEqual(package_pin.takeaway_line(pk), "No ruler, just rules nobody gets to bend.")
        pk["gates"] = TestMedleyPackageAndPin().gates(pk)
        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
        self.assertEqual(package_pin.takeaway_line(mp), "No ruler, just rules nobody gets to bend.")
        self.assertIn("takeaway_value", package_pin.required_gates(mp))
        self.assertIsNone(package_pin.takeaway_line(dict(mp, vo_jobs={"bridge_1": "connection"})))

    def test_the_row_must_judge_exactly_the_takeaway_that_ships(self):
        pk = self.pk()
        t = pk["vo"]["bridges"][-1]
        for bad in ({"text": "Another line."}, {"text": t + " "}, {"text": None}, {"text": t, "status": "FAIL"},
                    {"text": t, "status": "NOT RUN"}, {"text": t, "replayed": True}, {"text": t, "replayed": None}):
            g = TestMedleyPackageAndPin().gates(pk)
            g["takeaway_value"] = dict(g["takeaway_value"], **bad)
            with self.assertRaises(package_pin.PinRefused, msg=bad) as cm:
                package_pin.to_pin(spk(dict(pk, gates=g)), "test")
            self.assertIn("takeaway_value", str(cm.exception))
        g = TestMedleyPackageAndPin().gates(pk)
        g.pop("takeaway_value")
        with self.assertRaises(package_pin.PinRefused) as cm:
            package_pin.to_pin(spk(dict(pk, gates=g)), "test")
        self.assertIn("takeaway_value: missing", str(cm.exception))
        package_pin.to_pin(spk(dict(pk, gates=TestMedleyPackageAndPin().gates(pk))), "test")   # the right row: pins


class TestRuling109Channels(unittest.TestCase):
    """RULING 109 (free gates first) on the medley's 3-channel rule (orchestrator 08:56 ET Nov 15: "one channel cannot
    make a medley ... run the SPOTLIGHT path"): a pool of fewer than 3 channels after the free stages ends the medley
    before any paid verdict, with the record the rule on the cleared moments returns; 3 channels are screened and
    packaged as before; a build from a ruling-66 candidate keeps its own path."""
    ALL = ["h", "x", "y", "z"]

    def pool(self, chans):
        return [pm(mid, ch, 12.0 + i) for i, (mid, ch) in enumerate(zip(self.ALL, chans))]

    def test_one_or_two_channels_ask_nothing(self):
        for chans in ("AAAA", "AABB"):
            rig = Rig(self.pool(chans), self.ALL, [], [])
            out = rig.run()
            self.assertEqual((rig.screens, rig.events, rig.hook_calls, rig.visual_calls, rig.medley_calls),
                             ([], [], [], [], []), chans)                  # no step A, no call of any kind
            n = len(set(chans))
            self.assertEqual(out["why_none"], f"the pool spans {n} channel(s) after the free stages: a medley needs 3; "
                                              f"no paid verdict (ruling 109)")
            self.assertEqual((out["package"], out["usable"], out["prescreen"]["cleared"], out["ruling_109"]),
                             (None, 4, 0, {"channels": n, "pool": 4}))

    def test_the_channels_are_counted_after_the_free_stages(self):
        off = dict(pm("w", "C", 12.0), text="The weather was lovely at the lake today.")   # a third channel, but no
        rig = Rig(self.pool("AABB") + [off], self.ALL, [], [])                             # place under the topic rule
        out = rig.run()
        self.assertEqual((rig.screens, rig.events), ([], []))
        self.assertIn("w", out["no_role"])
        self.assertEqual((out["usable"], out["ruling_109"]), (5, {"channels": 2, "pool": 4}))

    def test_the_record_has_the_shape_the_rule_on_the_cleared_moments_returns(self):
        gate = Rig(self.pool("AABB"), self.ALL, [], []).run()
        late = Rig(self.pool("ABCD"), self.ALL, [], [],
                   a_fail={("xai", "y"): ["REFERENT_OUTSIDE"], ("xai", "z"): ["REFERENT_OUTSIDE"]}).run()
        self.assertEqual(late["why_none"], "2 moments cleared step A from fewer than 3 channels")   # the rule, after
        self.assertEqual(set(gate) - {"ruling_109"}, set(late))                                     # step A was paid
        self.assertEqual(set(gate["prescreen"]), set(late["prescreen"]))
        self.assertEqual(set(gate["scorer"]), set(late["scorer"]))

    def test_the_guard_finds_no_open_work_and_the_registry_no_line_up(self):
        import candidates as CA
        import proof_ledger as PLG
        gate = Rig(self.pool("AABB"), self.ALL, [], []).run()
        self.assertEqual(PLG.open_work(gate, {}), 0)                        # ruling 107 (1): nothing asked or undone
        reg = CA.new_registry()
        self.assertEqual((CA.seed(reg, gate, "proof/ledger_x"), reg["candidates"]), ([], {}))   # ruling 66: none kept

    def test_three_channels_are_screened_and_packaged_as_before(self):
        rig = Rig(self.pool("ABCA"), self.ALL, [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.screens[0], ("xai:grok", self.ALL))
        self.assertIsNotNone(out["package"])
        self.assertNotIn("ruling_109", out)

    def test_a_build_from_a_candidate_keeps_its_own_path(self):
        c = PK.load_candidate(TestRuling66Candidate().record())
        rig = Rig(self.pool("AABB"), self.ALL, [], [], candidate=c)
        out = rig.run()
        self.assertEqual(rig.screens, [("xai:grok", self.ALL)])           # screened as before this gate
        self.assertNotIn("ruling_109", out)


def ledgered(*ms):
    """The pool's moments as ledger_build makes them: each with its own id and the LEDGER's id kept as
    mined.ledger_moment_id ("L" + its id here), the id the stories file names (ruling 118 (4))."""
    return [dict(m, mined={"ledger_moment_id": "L" + m["moment_id"]}) for m in ms]


class TestRuling118StoryFirst(unittest.TestCase):
    """RULING 118 (4) (orchestrator 05:40 ET Nov 16), STORY-FIRST LINE-UPS: an angle source that builds a line-up INSIDE
    ONE STORY (the hook and every clip from the same story, 3 channels), ahead of the angle writer, every gate unchanged;
    the receipts session's stories file is read only; no file: the build as before."""
    GROUP = {"group": ["deepseek/deepseek-v4.1-flash", "minimax/minimax-m3.1-flash"]}
    MS = ledgered(pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
    STORY = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lgone"])]     # the file names LEDGER ids

    def file(self, stories, models=GROUP):
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.remove(os.path.join(d, f)) for f in os.listdir(d)] and None or os.rmdir(d))
        p = os.path.join(d, "latest.json")
        with open(p, "w") as f:
            json.dump({"generated_at": "2026-11-16T13:43:27Z", "prompt_version": "st1-x", "models": models,
                       "stories": [{"story_id": sid, "headline": hl, "channels": 3, "n_claims": 6,
                                    "moments": [{"moment_id": m, "video_id": "v" + m, "channel_name": "c",
                                                 "published_at": "2026-11-16T10:00:00Z", "claims": []} for m in ms]}
                                   for sid, hl, ms in stories]}, f)
        return p

    def rig(self, ms, writer, stories, **kw):
        rig = Rig(ms, writer, [(False, [], None, "none")] * 20, [], **kw)
        rig.stories_path = self.file(stories) if stories is not None else "/nonexistent/stories/latest.json"
        return rig

    def test_every_swap_of_a_story_line_up_stays_inside_its_story(self):
        ms = self.MS + ledgered(pm("w", "F", 13.0, rank=5.0))             # in the story, ranked under the pool's z, q
        story = [("S-1", "Bitcoin's own story", ["Lh", "Lx", "Ly", "Lw"])]
        rig = self.rig(ms, ["h", "x", "y", "z", "q"], story)               # a weak clip: swapped inside the story
        rig.medleys = [(False, [], {"clip_02": 2}, Rig.LINE)] + [(False, [], None, "none")] * 6
        out = rig.run()
        mine = [lu for r in out["tried"] if r["angle"] == 1 for lu in [r["lineup"]] if lu]
        self.assertEqual(mine[:2], [["h", "x", "y"], ["h", "x", "w"]], out["tried"])
        rig = self.rig(ms, ["h", "x", "y", "z", "q"], story, angle_from=("xai:grok", "xai", "grok"),
                       a_fail={("openai", "y"): ["REFERENT_OUTSIDE"]})    # a clip failing its re-screen: the same
        rig.medleys, rig.writes = [(True, [], None, Rig.LINE)] * 2, [None, None]
        out = rig.run()
        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "w"]])
        self.assertIn("swapped {'y': 'w'}", out["tried"][0]["why"])
        self.assertEqual(out["package"]["models"]["angle"], "story S-1 (the stories file)")   # who made its angle

    def test_a_candidates_build_reads_no_stories(self):
        med = {"through_line": "Nobody controls the rules.", "clips": {"hook": 4, "clip_01": 4, "clip_02": 4},
               "flagged": [], "measured": True, "replayed": False, "backend": "xai:grok"}
        c = PK.load_candidate({"tried": [{"angle": 1, "text": "W", "lineup": ["h", "z", "q"], "supply_exception": None,
                                          "medley": med, "medley_ok": True}],
                               "angles": [{"angle": "W", "moments": ["h", "x", "y", "z", "q"], "hook": "h"}],
                               "angle_backend": "heimdall:deepseek", "angle_tried": []}, source="proof/ledger_x")
        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY, candidate=c)
        out = rig.run()
        self.assertNotIn("stories", out)
        self.assertEqual((rig.medley_calls[0], out["tried"][0]["text"]), (["h", "z", "q"], "W"))   # its own, as judged

    def test_the_files_ledger_ids_become_this_builds_ids(self):
        """The receipts session names the LEDGER's ids; this build's moments carry them as mined.ledger_moment_id (a
        trimmed variant its parent's), and a ledger row dropped as a duplicate of a kept one stands for the kept one.
        Builds 41-57 compared the two kinds of id directly and matched nothing."""
        pool = {"b1": {"mined": {"ledger_moment_id": "L1"}}, "b1~trim": {"mined": {"ledger_moment_id": "L1"}},
                "b2": {"mined": {"ledger_moment_id": "L2"}}, "b4": {}}
        st = PK.in_pool_ids([{"story_id": "S", "headline": "h", "moment_ids": ["L3", "Ldup", "L1", "L2"]}], pool,
                            {"Ldup": "L2"})
        self.assertEqual(st, [{"story_id": "S", "headline": "h", "moment_ids": ["b2", "b1", "b1~trim"],
                               "ledger_ids": ["L3", "Ldup", "L1", "L2"]}])
        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], [("S-1", "By build ids", ["h", "x", "y"])]).run()
        self.assertEqual(out["stories"]["matched"], [{"story_id": "S-1", "ledger_ids": 3, "in_pool": 0, "cleared": 0}])
        self.assertTrue(all("story" not in a for a in out["angles"]))          # build ids are not the file's ids
        self.assertIn("NO ID OF THE STORIES FILE NAMES A MOMENT OF THIS BUILD'S POOL", out["stories"]["warning"])
        self.assertEqual(out["stories"]["aliases"], "not supplied")              # the rig passes no ledger_aliases
        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY).run()     # the file's ledger ids: matched,
        self.assertEqual(out["stories"]["matched"], [{"story_id": "S-1", "ledger_ids": 4, "in_pool": 3, "cleared": 3}])
        self.assertNotIn("warning", out["stories"])                               # no warning

    def test_the_file_is_read_in_its_writers_shape_or_not_at_all(self):
        self.assertEqual(PK.read_stories(None), ([], {"path": None, "read": False, "why": "no stories file named"}))
        st, rec = PK.read_stories("/nonexistent/stories/latest.json")
        self.assertEqual((st, rec["read"], rec["why"]), ([], False, "no file"))
        p = self.file([("S-1", "  Bitcoin   falls ", ["a", "b", "a"])])
        st, rec = PK.read_stories(p)
        self.assertEqual(st, [{"story_id": "S-1", "headline": "Bitcoin falls", "moment_ids": ["a", "b"]}])
        self.assertEqual((rec["read"], rec["generated_at"], rec["models"], rec["stories"]),
                         (True, "2026-11-16T13:43:27Z", self.GROUP, 1))
        for bad in ([], {"stories": {}}, {"stories": [{"story_id": "S-1", "headline": "h", "moments": "a"}]},
                    {"stories": [{"story_id": "S-1", "headline": " ", "moments": []}]},
                    {"stories": [{"story_id": "", "headline": "h", "moments": []}]},
                    {"stories": [{"story_id": "S-1", "headline": "h", "moments": [{"moment_id": 3}]}]},
                    {"stories": [{"story_id": "S-1", "headline": "h", "moments": []}, "S-2"]}):
            with open(p, "w") as f:
                json.dump(bad, f)
            st, rec = PK.read_stories(p)
            self.assertEqual((st, rec["read"]), ([], False), bad)          # the whole file, never part of it
        with open(p, "w") as f:
            f.write("{")
        self.assertEqual(PK.read_stories(p)[1]["why"], "unreadable (JSONDecodeError)")

    def test_one_angle_a_story_on_its_best_passing_hook_new_channels_first_and_the_angle_contract(self):
        pool = {m["moment_id"]: m for m in [pm("h", "A", 12.0), pm("x", "B", 14.0, rank=5.0), pm("y", "C", 13.0, rank=6.0),
                                            pm("w", "A", 11.0, rank=9.0), pm("z", "D", 13.0)]}
        st = [{"story_id": "S-1", "headline": "One", "moment_ids": ["h", "w", "x", "y", "gone"]},
              {"story_id": "S-2", "headline": "Two", "moment_ids": ["h", "w", "z"]},          # two channels
              {"story_id": "S-3", "headline": "Three", "moment_ids": ["y", "w", "z"]},        # no passing hook
              {"story_id": "S-6", "headline": "Six", "moment_ids": ["x", "z", "gone"]},       # two cleared moments
              {"story_id": "S-4", "headline": "Four", "moment_ids": ["h", "y", "z"]},
              {"story_id": "S-5", "headline": "Five", "moment_ids": ["h", "y", "z"]}]         # over k
        angles, rec = PK.story_angles(st, pool, [pool["x"], pool["h"]], k=2)               # the passing hooks, best first
        self.assertEqual(angles, [{"angle": "One", "moments": ["x", "h", "y", "w"], "hook": "x", "story": "S-1"},
                                  {"angle": "Four", "moments": ["h", "z", "y"], "hook": "h", "story": "S-4"}])
        self.assertEqual((rec[0]["cleared"], rec[0]["channels"]), (4, 3))                  # "gone" is not in the pool
        self.assertTrue(rec[1]["why"].startswith("not an angle: angle 1: >= 3 channels"), rec[1])
        self.assertEqual(rec[2]["why"], "no passing hook among its cleared moments")
        self.assertEqual(rec[3]["why"], "not an angle: angle 1: 3-8 distinct offered ids")     # the contract's 3
        self.assertEqual(rec[5]["why"], "2 story angle(s) already")
        for a in angles:                                                                  # the writer's own contract
            PK.check_angles({"angles": [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"],
                                         "support": {m: "s" for m in a["moments"]}}]}, pool, 1, hooks={"x", "h"})

    def test_a_story_angle_chooses_only_inside_its_story(self):
        pool = {m["moment_id"]: m for m in self.MS}
        by = {"S-1": ["h", "x", "gone"]}
        self.assertEqual(set(PK.story_pool({"story": "S-1"}, pool, by)), {"h", "x"})
        self.assertEqual(PK.story_pool({"story": "S-9"}, pool, by), {})                  # a story it does not hold
        self.assertIs(PK.story_pool({"angle": "w", "hook": "h"}, pool, by), pool)         # the writer's: as before

    def test_the_story_angle_is_tried_first_and_its_line_ups_stay_inside_its_story(self):
        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
        out = rig.run()
        self.assertEqual(out["angles"][0], {"angle": "Bitcoin's own story", "moments": ["h", "x", "y"], "hook": "h",
                                            "story": "S-1"})
        self.assertNotIn("story", out["angles"][1])                                      # the writer's, after it
        self.assertEqual((out["stories"]["read"], out["stories"]["angles"][0]["angle"]), (True, 1))
        self.assertEqual(out["tried"][0]["angle"], 1)
        mine = [r["lineup"] for r in out["tried"] if r["angle"] == 1 and r["lineup"]]
        self.assertTrue(mine and all(set(lu) <= {"h", "x", "y"} for lu in mine), out["tried"])
        self.assertEqual(rig.medley_calls[0], mine[0])                                    # judged first, as any line-up

    def test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it(self):
        ms = ledgered(pm("h", "A", 10.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 13.0), pm("q", "E", 13.0))
        out = self.rig(ms, ["h", "z", "q", "x"], [("S-1", "A short story", ["Lh", "Lx", "Ly"])]).run()
        self.assertEqual(out["angles"][0]["story"], "S-1")
        mine = [r for r in out["tried"] if r["angle"] == 1]
        self.assertTrue(mine)
        for r in mine:                                    # 28 s of its own clips: no line-up, never the pool's z or q
            self.assertIsNone(r["lineup"], r)
            self.assertNotIn("pool_filled", r)

    def test_the_join_table_of_a_story_angle_is_asked_only_of_its_story(self):
        ids = [m["moment_id"] for m in self.MS]
        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY,
                       joins={(a, b): True for a in ids for b in ids if a != b})
        out = rig.run()
        self.assertEqual(rig.join_calls[0], ["h", "x", "y"])                             # the story angle's: its story
        self.assertEqual(set(rig.join_calls[1]), set(ids))                               # the writer's: the pool
        self.assertTrue(all(set(r["lineup"]) <= {"h", "x", "y"} for r in out["tried"] if r["angle"] == 1 and r["lineup"]))

    def test_the_stories_grouping_models_never_judge_its_line_ups(self):
        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
        rig.router.backends["heimdall:qwen"].model = "minimax/minimax-m3.1-flash"        # a back-end running one of them
        seen, jt = [], rig.join_table
        rig.join_table = lambda router, ms_, c, wv, wf=None, **k: (seen.append((set(wv), set(wf or ()))),
                                                                   jt(router, ms_, c, wv, wf, **k))[1]
        out = rig.run()
        self.assertEqual(out["stories"]["writers"], {"vendors": ["heimdall"], "families": ["qwen"]})
        self.assertTrue(seen and all("heimdall" in wv and "qwen" in wf for wv, wf in seen), seen)

    def test_no_file_no_story_of_three_channels_or_no_writer_builds_as_before(self):
        out = self.rig(self.MS, ["h", "x", "y", "z", "q"], None).run()
        self.assertEqual((out["stories"]["read"], out["stories"]["why"]), (False, "no file"))
        self.assertTrue(all("story" not in a for a in out["angles"]))
        ms = self.MS + ledgered(pm("w", "A", 11.0))
        out = self.rig(ms, ["h", "x", "y", "z", "q"], [("S-2", "Two channels", ["Lh", "Lw", "Lx"])]).run()
        self.assertTrue(out["stories"]["angles"][0]["why"].startswith("not an angle"))
        self.assertTrue(all("story" not in a for a in out["angles"]))
        self.assertNotIn("stories", Rig(self.MS, ["h", "x", "y", "z", "q"], [(False, [], None, "none")] * 4, []).run())
        rig = self.rig(self.MS, ["h", "x", "y", "z", "q"], self.STORY)
        rig.router.answers["angle_write"] = ["{", "{"]                               # the writer gives no angle:
        out = rig.run()                                                              # the build stops, as before
        self.assertTrue(out["why_none"].startswith("no readable angles"))
        self.assertEqual((out["angles"], rig.medley_calls), ([], []))

    def test_a_story_angles_line_up_is_never_kept_as_a_candidate(self):
        med = {"measured": True, "replayed": False}
        rec = {"angle_backend": "heimdall:deepseek",
               "angles": [{"angle": "S", "moments": ["h", "x", "y"], "hook": "h", "story": "S-1"},
                          {"angle": "W", "moments": ["h", "x", "y", "z"], "hook": "h"}],
               "tried": [{"angle": 1, "text": "S", "lineup": ["h", "x", "y"], "medley_ok": True, "medley": med},
                         {"angle": 2, "text": "W", "lineup": ["h", "x", "z"], "medley_ok": True, "medley": med}]}
        self.assertEqual(PK.load_candidate(rec)["index"], 1)                             # the writer's line-up
        with self.assertRaisesRegex(ValueError, "story 'S-1'"):
            PK.load_candidate(rec, 0)
        rec["angles"][1]["story"] = "S-2"
        with self.assertRaisesRegex(ValueError, "no line-up in this record passed"):
            PK.load_candidate(rec)


class TestRuling123SixteenNineHook(unittest.TestCase):
    """RULING 123 (2) (orchestrator 14:05 ET Nov 16): when no hook passes for both formats, a hook whose ONLY refusal is
    ruling 93's 9:16 crop (a lower third the crop would cut mid-word) opens a package sealed formats ['16x9']; a
    both-format hook always wins; as a clip its refusal stands."""
    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
    CUT = {"burned_in": [{"kind": "lower_third", "text": "IN THIS EPISODE...", "whole_in_16x9": True, "in_9x16": "cut",
                          "covers_speaker": False}]}

    def rec(self, **kw):
        base = {"version": VP.VERSION, "measured": True, "flags": [], "burned_in": self.CUT["burned_in"]}
        return dict(base, **kw)

    def test_only_a_crop_refusal_qualifies(self):
        lt = self.CUT["burned_in"][0]
        self.assertTrue(VP.crop_only(self.rec()).startswith("a lower_third the 9:16 crop would cut through mid-word"))
        for bad in (dict(lt, kind="ticker"), dict(lt, covers_speaker=True), dict(lt, whole_in_16x9=False)):
            self.assertIsNone(VP.crop_only(self.rec(burned_in=[bad])), bad)
        self.assertIsNone(VP.crop_only(self.rec(burned_in=[dict(lt, in_9x16="whole")])))    # nothing refused at all
        self.assertIsNone(VP.crop_only(self.rec(version="visual-2")))
        self.assertIsNone(VP.crop_only(self.rec(measured=False)))
        tp = {"kind": "third_person", "text": "a still of a CEO", "why": "w"}
        self.assertIsNone(VP.crop_only(self.rec(flags=[tp])))                                # ruling 70 still refuses

    def test_with_no_both_format_hook_it_opens_a_package_sealed_16x9_only(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"h": self.CUT}).run()
        self.assertIn("h", out["hook_pool"]["sixteen_nine_only"]["hooks"])
        self.assertEqual(out["hook_pool"]["passing"], ["h"])
        self.assertIsNotNone(out["package"])
        self.assertEqual(out["package"]["segments"][0]["moment_id"], "h")
        import package_pin
        self.assertEqual(package_pin.formats_of(out["package"]["segments"]), ["16x9"])        # sealed 16:9 only

    def test_a_both_format_hook_always_wins(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], visuals={"h": self.CUT},
                  hooks={"x": (5, 5, 5)}).run()
        self.assertNotIn("sixteen_nine_only", out["hook_pool"])
        self.assertEqual(out["hook_pool"]["passing"], ["x"])
        self.assertIn("h", out["hook_pool"]["visual_blocked"])

    def test_a_second_16x9_only_opener_is_still_refused_as_a_clip(self):
        """Two hooks refused only by the crop and none for both formats: both may open, but in a line-up the one that
        plays as a CLIP keeps its ruling-93 refusal (only the hook is excused)."""
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)] * 4, [None, None],
                  visuals={"h": self.CUT, "x": self.CUT}, hooks={"x": (5, 5, 5)})
        out = rig.run()
        self.assertEqual(set(out["hook_pool"]["sixteen_nine_only"]["hooks"]), {"h", "x"})
        self.assertTrue(any("x: ruling 93" in (r.get("why") or "") for r in out["tried"]), out["tried"])
        for lu in rig.write_calls:                                    # nothing is written for a line-up with x as a clip
            self.assertNotIn("x", lu[0][1:])
        self.assertTrue(out["package"] is None or "x" not in [s["moment_id"] for s in out["package"]["segments"][1:]])

    def test_as_a_clip_its_refusal_stands(self):
        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)] * 3, [None, None],
                  visuals={"y": self.CUT}).run()
        self.assertNotIn("sixteen_nine_only", out["hook_pool"])
        self.assertTrue(out["package"] is None or "y" not in [s["moment_id"] for s in out["package"]["segments"]])
        self.assertTrue(any("y: ruling 93" in (r.get("why") or "") for r in out["tried"]), out["tried"])


if __name__ == "__main__":
    unittest.main()
