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
import os
import sys
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

W = lambda n: " ".join(["word"] * n)


def angle(ms, hook, text="Nobody controls Bitcoin."):
    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}


def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
    js = PK.joins(labs)
    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
                          if j in flagged else "same subject"} for j in js}}


def reply(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin.", hook=None):
    """The clips-alone JUDGE's raw reply (ruling 52): the hook's three parts, the clips after the hook, the joins."""
    js = PK.joins(labs)
    h = (ratings or {}).get("hook", 5)
    return {"through_line": line, "hook": dict({"scroll": h, "alone": h, "setup": h}, **(hook or {})),
            "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs[1:]},
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
    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
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

    def test_ruling_52_the_hook_is_rated_on_its_own_job_in_three_parts(self):
        prompts = []
        r = Canned(coherence_verdict=[reply(self.LABS, hook={"setup": 3})])
        call = r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
        self.assertFalse(ok)                              # one part under the bar: the hook's derived rating is 3
        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
        self.assertIn("lowest of scroll / alone / setup", v["hook_rule"])
        for part in ('"scroll"', '"alone"', '"setup"', "first 2-3 seconds", "wants the next clip",
                     "For each clip AFTER the hook", '"clip_01": 1, "clip_02": 1'):
            self.assertIn(part, prompts[0])
        self.assertNotIn('"hook": 1', prompts[0])         # the hook is not asked for a through-line rating
        ok, v, _ = self.run_it(reply(self.LABS, hook={"scroll": 4, "alone": 4, "setup": 4}))
        self.assertTrue(ok)                               # every part at the bar of 4
        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
        ok, v, _ = self.run_it(reply(self.LABS, ratings={"hook": 5, "clip_01": 3}))
        self.assertFalse(ok)                              # the clips keep their own rating and bar

    def test_out_of_contract_is_not_measured_and_rejected(self):
        good = reply(self.LABS)
        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
                    dict(good, vo_point=5),
                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}),            # the hook among the clips
                    dict(good, hook={"scroll": 5, "alone": 5}),                           # a part missing (ruling 52)
                    dict(good, hook={"scroll": 5, "alone": 5, "setup": 6}),
                    dict(good, hook={"scroll": "5", "alone": 5, "setup": 5}),
                    {k: x for k, x in good.items() if k != "hook"}):
            ok, v, r = self.run_it(bad)
            self.assertFalse(ok)
            self.assertFalse(v["measured"])
            self.assertIsNone(v["flagged"])
            self.assertEqual(r.rejected, ["fake:coherence_verdict"])


class TestCoherenceHookRating(unittest.TestCase):
    """The orchestrator's answer (09:59): ruling 52's hook rating applies to the coherence verdict after the takeaway as
    well. ONE definition of the hook's job (HOOK_QUESTION) in both verdicts; the hook's rating derived, never free-form."""
    PK_ = {"title": "Nobody bends the rules", "caption": "three clips",
           "vo": {"intro": None, "bridges": ["No ruler, just rules."], "bridges_after_clip": [2], "signoff": "S"},
           "segments": [{"label": "hook", "channel": "A", "text": "Bitcoin a."},
                        {"label": "clip_01", "channel": "B", "text": "Bitcoin b."},
                        {"label": "clip_02", "channel": "C", "text": "Bitcoin c."}]}

    def reply(self, hook=None, clips=None, vo=5, line="Nobody can change the rules of Bitcoin."):
        return {"through_line": line, "hook": dict({"scroll": 5, "alone": 5, "setup": 5}, **(hook or {})),
                "clips": dict({"clip_01": 5, "clip_02": 5}, **(clips or {})), "vo_point": vo}

    def run_it(self, reply):
        r = Canned(coherence_verdict=[reply])
        prompts = []
        call = r.call
        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        ok, v = PK.coherence(r, self.PK_, {"heimdall"}, writer_family={"deepseek"})
        return ok, v, r, prompts

    def test_the_hook_is_rated_on_its_own_job_and_derived(self):
        ok, v, _, prompts = self.run_it(self.reply(hook={"setup": 3}))
        self.assertFalse(ok)
        self.assertEqual((v["clips"]["hook"], v["hook"]), (3, {"scroll": 5, "alone": 5, "setup": 3}))
        self.assertIn(PK.HOOK_QUESTION, prompts[0])                 # the one definition, as in the clips-alone verdict
        self.assertIn(PK.HOOK_QUESTION, PK.MEDLEY_PROMPT)
        self.assertIn("For each clip AFTER the hook", prompts[0])
        self.assertIn('"clips": {"clip_01": 1, "clip_02": 1}', prompts[0])
        ok, v, _, _ = self.run_it(self.reply(hook={"scroll": 4, "alone": 4, "setup": 4}))
        self.assertTrue(ok)
        self.assertEqual(v["clips"], {"hook": 4, "clip_01": 5, "clip_02": 5})
        self.assertFalse(self.run_it(self.reply(clips={"clip_02": 3}))[0])      # clips and vo_point as before
        self.assertFalse(self.run_it(self.reply(vo=3))[0])

    def test_out_of_contract_is_not_measured(self):
        good = self.reply()
        for bad in ({k: x for k, x in good.items() if k != "hook"}, dict(good, hook={"scroll": 5, "alone": 5}),
                    dict(good, clips={"hook": 5, "clip_01": 5, "clip_02": 5}), dict(good, hook={"scroll": 5, "alone": 5,
                                                                                               "setup": 0})):
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
            lo, hi = map(int, re.search(r'"takeaway": (\d+)-(\d+) words', prompts[0]).groups())
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
        self.assertIn(f'"takeaway": {lo}-{hi} words in short declarative sentences', prompts[0])
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
        self.assertEqual(package_pin.required_gates(pk)[-5:], ("medley", "ly_shape", "house_style", "hook_onset",
                                                               "stand_alone"))
        pk["gates"] = self.gates(pk)
        pin = package_pin.to_pin(spk(pk), "test")
        self.assertEqual(pin["label"], "bitcoin")     # the render's STAND_ALONE subject rests on it (audit 0310 C2)
        self.assertNotIn("stand_alone", package_pin.required_gates({"shape": "story"}))   # medleys only (glm P2-1)
        mp = pin["moments_package"]
        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
        self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
        self.assertEqual(mp["shape"], "medley")
        for missing in ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"):
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


class Rig:
    """build() with every model and the network stubbed: the LOOP CONTROL under test (audit 2030 C1, glm P2-6).
    medleys: the clips-alone verdicts in call order, each (ok, flagged, ratings, through_line); writes: the writer's
    bridges in call order (None = no bridge / declined)."""

    LINE = "Nobody gets to bend these rules, and that is exactly why they hold when it counts."
    A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
            "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}

    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
                 spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
                 trim_fail=(), hooks=None, hook_err=None, verdicts=None):
        import providers as P
        self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
        self.takeaways, self.spend = list(takeaways or []), spend
        self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
        self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
        self.verdicts = verdicts                           # ruling 56: {pid: verdict} in the integrator's file shape
        self.hooks, self.hook_err, self.hook_calls = dict(hooks or {}), hook_err, []   # ruling 59 (a): {id: (s, a, u)}
        self.medley_calls, self.write_calls, self.prompts = [], [], []
        self.a_fail, self.unavailable = dict(a_fail or {}), set(unavailable)   # step A per (vendor, moment id)
        self.screens, self.events, self.a_seen = [], [], []
        self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
        many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
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
                  batch=PK.PRESCREEN_BATCH, store=None, log=print, cache=None):
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
                fails[mid] = ["STEP_A_UNAVAILABLE: ProviderError"]
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
            sc, al, se = self.hooks.get(m["moment_id"], (5, 5, 5))
            out[m["moment_id"]] = {"scroll": sc, "alone": al, "setup": se, "rating": min(sc, al, se),
                                   "why": f"why {m['moment_id']}", "backend": "xai:grok", "cached": False}
        return out, None

    def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
        self.medley_calls.append([m["moment_id"] for m in segs])
        ok, flagged, ratings, line = self.medleys.pop(0)
        labs = PK.labels(len(segs))
        v = verdict(labs, flagged, ratings, line)
        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False)

    def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
        if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
            raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
        self.write_calls.append(([m["moment_id"] for m in segs], join))
        self.write_avoid.append(avoid_vendor)
        self.a_seen.append({m["moment_id"]: a_by[m["moment_id"]]["backend"] for m in segs})
        b = self.writes.pop(0)
        fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
                  "bridge_after": join[0] if join is not None and b is not None else None,
                  "title": {"text": "Nobody bends the rules", "cites": []},
                  "caption": {"text": "nobody bends these rules", "cites": []},
                  "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
        return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields

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
            "paid_gates": lambda *a, **k: (fid, cx),
            "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
                                                         "keep", "measured": True, "replayed": False,
                                                         "backend": "xai:grok"},
            "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
                                                     "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
            "hook_onset_for": self.onset,
            "hook_ratings": self.rate_hooks,
            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
                                                             "replayed": False}),
        }
        kw, path = {}, None
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
        try:
            for k, v in stubs.items():
                setattr(PK, k, v)
            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
                            spend=self.spend, **kw)
        finally:
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

    def test_no_voice_when_the_takeaway_fails_twice_on_clips_that_hold_alone(self):
        """Ruling 3 (22:40): clips back to back and the sign-off, NOT dropped; one clip added to land 60-70 s."""
        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], takeaways=bad)
        out = rig.run()
        pk = out["package"]
        self.assertIsNotNone(pk)
        self.assertEqual(len(rig.write_calls), 2)                  # both takeaways failed (takeaway-opener)
        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])   # 39 s + z: 52 s
        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])   # the new line-up judged on the clips alone
        self.assertEqual((pk["vo"]["intro"], pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]), (None, [], []))
        self.assertEqual(pk["no_voice"]["added_clip"], "z")
        self.assertEqual([x["slot"] for x in pk["lines"]], ["title", "caption"])
        self.assertAlmostEqual(pk["runtime_s_estimate"], 52.0 + PK.FINAL_TAIL_S, places=2)
        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
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

    def fake(self, calls, fail=frozenset()):
        import context_integrity as CI
        from test_gates import a_item

        def step_a(router_, contexts, wv, seed=7, writer_family=None):
            calls.append((sorted(contexts), seed))
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
            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # a new show date
            calls.clear()
            a_by, _, _, _ = PK.prescreen(self.router(), ms[:3], srcs, ctx(), {"xai"}, {"grok"}, cache=cache)
            self.assertEqual(sorted(sum((c[0] for c in calls), [])), ["m00", "m01", "m02"])   # never the writer's
            self.assertEqual({a["backend"] for a in a_by.values()}, {"heimdall:deepseek"})     # vendor's verdict

    def test_a_failed_batch_is_no_verdict_never_cached_and_says_why(self):
        import tempfile
        ms, srcs = self.pool(10)
        calls = []
        self.fake(calls, fail={"m09"})                                    # the miner's best batch fails
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "c.json")
            a_by, fails, _, _ = PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(len(a_by), 2)                                # the other batch (2) only
            self.assertEqual(fails["m09"], ["STEP_A_UNAVAILABLE: RuntimeError: the batch reply was out of contract"])
            with open(cache) as f:
                self.assertEqual(len(json.load(f)), 2)                    # a failure is never remembered
            calls.clear()
            PK.prescreen(self.router(), ms, srcs, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual(len(sum((c[0] for c in calls), [])), 8)      # asked again, the 8 only


class TestRuling59HookFirst(unittest.TestCase):
    """RULING 59 (11:00): HOOK FIRST. Every cleared, cuttable moment that can open is rated on the hook's own job (ruling
    52's question) in one batched call, cached; only a hook rated >= 4 opens; the angles are written FOR the passing
    hooks and tried best hook first; with no passing hook the build stops before any line-up, listing the best three."""

    def canned(self, *replies):
        c = Canned(coherence_verdict=list(replies))
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        c.backends = {"fake:coherence_verdict": B("fake", "fake")}
        return c

    def test_one_batched_call_rates_every_hook_and_the_rating_is_derived_and_cached(self):
        import tempfile
        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
        reply = {"hooks": {"a": {"scroll": 5, "alone": 4, "setup": 5, "why": "w a"},
                           "b": {"scroll": 5, "alone": 2, "setup": 5, "why": "needs what came before"}}}
        with tempfile.TemporaryDirectory() as d:
            cache = os.path.join(d, "HOOK_CACHE.json")
            c = self.canned(reply)
            got, err = PK.hook_ratings(c, ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertIsNone(err)
            self.assertEqual(c.calls, [("coherence_verdict", {"heimdall"}, {"deepseek"})])   # ONE call, off the writers
            self.assertEqual((got["a"]["rating"], got["b"]["rating"]), (4, 2))   # the lowest part (ruling 52)
            self.assertEqual(got["b"]["why"], "needs what came before")
            again, err = PK.hook_ratings(self.canned(), ms, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual((err, again["a"]["rating"], again["a"]["cached"]), (None, 4, True))   # no call at all
            new = [dict(ms[0], text="Bitcoin is a new text now."), ms[1]]
            c = self.canned({"hooks": {"a": {"scroll": 3, "alone": 3, "setup": 3, "why": "w"}}})
            got, _ = PK.hook_ratings(c, new, ctx(), {"heimdall"}, {"deepseek"}, cache=cache)
            self.assertEqual((len(c.calls), got["a"]["rating"], got["b"]["cached"]), (1, 3, True))   # its new text only

    def test_the_prompt_asks_ruling_52s_question_of_each_candidate_alone(self):
        ms = [pm("a", "A", 12.0), pm("b", "B", 12.0)]
        prompts = []
        c = self.canned({"hooks": {k: {"scroll": 5, "alone": 5, "setup": 5, "why": "w"} for k in "ab"}})
        call = c.call
        c.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
        PK.hook_ratings(c, ms, ctx(), set(), set())
        self.assertIn(PK.HOOK_QUESTION, prompts[0])                       # ONE definition of the hook's job
        self.assertIn('CANDIDATE id="a"', prompts[0])
        self.assertIn('CANDIDATE id="b"', prompts[0])
        self.assertIn("Judge each one ALONE", prompts[0])

    def test_a_reply_out_of_contract_is_asked_once_more_then_nothing_is_rated(self):
        ms = [pm("a", "A", 12.0)]
        ok = {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4, "why": "w"}}}
        c = self.canned({"hooks": {"a": {"scroll": 9, "alone": 4, "setup": 4, "why": "w"}}}, ok)
        got, err = PK.hook_ratings(c, ms, ctx(), set(), set())
        self.assertEqual((err, got["a"]["rating"], len(c.calls), len(c.rejected)), (None, 4, 2, 1))
        for bad in ({"hooks": {}}, {"hooks": {"a": {"scroll": 4, "alone": 4, "setup": 4}}}, {"x": 1}, "no json"):
            got, err = PK.hook_ratings(self.canned(bad, bad), ms, ctx(), set(), set())
            self.assertEqual(got, {})
            self.assertIn("Error", err)
        got, err = PK.hook_ratings(self.canned(), ms, ctx(), set(), set())   # unavailable: no verdict (law L-m)
        self.assertEqual(got, {})
        self.assertIn("ProviderError", err)

    def test_only_a_hook_rated_4_or_more_opens(self):
        m = dict(pm("a", "A", 12.0), hook_onset={"pass": True})
        self.assertTrue(PK.can_open(m))                                   # not rated yet: as before ruling 59
        for rating, ok in ((4, True), (5, True), (3, False), (None, False)):
            r = dict(m, hook_rating={"rating": rating})
            self.assertEqual(PK.can_open(r), ok, rating)
            self.assertEqual(PK.placement(r), "" if ok else " | cannot open (never the hook)")
        self.assertFalse(PK.can_open(dict(m, hook_rating=None)))
        self.assertFalse(PK.can_open(dict(m, hook_rating={"rating": True})))
        self.assertFalse(PK.can_open(dict(m, text="And Bitcoin is money.")))   # the render's hook rule
        self.assertFalse(PK.lineup_ok([dict(m, hook_rating={"rating": 3}), pm("x", "B", 14.0), pm("y", "C", 13.0)])[0])

    def test_a_line_up_opens_on_its_angles_own_hook_and_never_swaps_it(self):
        ms = [dict(pm(k, k.upper(), d), hook_onset={"pass": True}, hook_rating={"rating": 5})
              for k, d in (("a", 12.0), ("b", 14.0), ("c", 13.0), ("d", 13.0))]
        by = {m["moment_id"]: m for m in ms}
        by["b"]["scores"] = dict(by["b"]["scores"], hook_first_2s=99)     # a stronger opener elsewhere
        segs = PK.lineup_for(angle(["b", "a", "c", "d"], "a"), by, need_onset=True, hook_only=True)
        self.assertEqual(segs[0]["moment_id"], "a")
        low = dict(by, a=dict(by["a"], hook_rating={"rating": 3}))
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
                  hooks={"h": (3, 4, 4), "x": (2, 5, 5), "y": (4, 3, 4), "z": (1, 1, 1)})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertTrue(out["why_none"].startswith("no hook in the pool (ruling 59 d): none of the 4 moments"))
        self.assertEqual([b["moment_id"] for b in out["hook_pool"]["best"]], ["h", "y", "x"])
        self.assertEqual([b["rating"] for b in out["hook_pool"]["best"]], [3, 3, 2])
        self.assertIn("A 3 (scroll 3, alone 4, setup 4): why h", out["why_none"])
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
                  hooks={"h": (4, 4, 4), "x": (5, 5, 5), "y": (3, 3, 3), "z": (3, 4, 5)})
        out = rig.run()
        p = next(p for r, p in rig.prompts if r == "angle_write")
        self.assertIn("THE HOOKS", p)
        self.assertLess(p.index("id=x | rated 5"), p.index("id=h | rated 4"))    # best first
        self.assertNotIn("id=y | rated", p)
        self.assertIn("id=y | C | 13.0 s | cannot open (never the hook) | ", p)
        self.assertIn("up to 1 for EACH hook above, at most 3 in all", p)
        self.assertEqual(rig.medley_calls[0][0], "x")                   # the x angle, though the writer gave it second
        self.assertEqual(out["hook_pool"]["passing"], ["x", "h"])
        self.assertIsNotNone(out["package"])

    def test_an_angle_not_written_for_a_passing_hook_is_out_of_contract(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
        rig = Rig(ms, ["y", "h", "x", "z"], [(True, [], None, Rig.LINE)], [None], hooks={"y": (3, 3, 3)})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertIn("is not one of THE HOOKS", out["why_none"])           # the first reply, rejected
        self.assertEqual((len(rig.router.rejected), sum(r == "angle_write" for r, _ in rig.prompts)), (1, 2))
        self.assertEqual(rig.medley_calls, [])


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


class TestOrder0622StepAFromBothVendors(unittest.TestCase):
    """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
    after a write swaps out that clip only, and the line-up carries on."""
    MS = TestBuildLoop.MS

    def test_every_cuttable_clip_is_screened_by_the_second_vendor_before_the_angle_step(self):
        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None],      # the writer never sees y
                  a_fail={("heimdall", "y"): ["REFERENT_OUTSIDE"]})
        out = rig.run()
        self.assertEqual(rig.screens[0], ("xai:grok", ["h", "x", "y", "z"]))          # the first screen, off heimdall
        self.assertEqual(rig.screens[1], ("heimdall:deepseek", ["h", "x", "y", "z"]))  # the second, off xai
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
        self.assertTrue(out["prescreen"]["second_vendor"]["y"].startswith("FAIL: STEP_A_UNAVAILABLE"))
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
        self.assertEqual(len(rig.screens), 2)                      # and no re-screen was needed after the write
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
        self.assertEqual(rig.screens[2], ("openai:gpt", ["h", "x", "y"]))         # every verdict on a writer's vendor
        self.assertEqual(rig.screens[3], ("openai:gpt", ["z"]))                   # only what changed is re-judged

    def test_a_re_screen_that_gives_no_verdict_is_never_a_pass(self):
        """The old branch read the stale verdict back when the re-screen returned nothing for a clip (a fail-open,
        flagged with ORDER 06:22): no verdict off the writers keeps the clip out."""
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)],
                  [None, None], angle_from=("xai:grok", "xai", "grok"), unavailable={("openai", "y")})
        out = rig.run()
        self.assertEqual(list(out["prescreen"]["rescreen_failed"]), ["y"])
        self.assertTrue(out["prescreen"]["rescreen_failed"]["y"][0].startswith("STEP_A_UNAVAILABLE"))
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
        self.assertTrue(all(f[0].startswith("STEP_A_UNAVAILABLE: RuntimeError") for f in fail.values()))

    def test_second_screen_fails_closed_on_an_unknown_back_end_or_the_same_vendor(self):
        B = lambda v, f: type("B", (), {"vendor": v, "family": f})()
        router = type("R", (), {"backends": {"xai:grok": B("xai", "grok"), "heimdall:deepseek": B("heimdall",
                                                                                                  "deepseek")}})()
        ms = {m["moment_id"]: m for m in self.MS}
        a_by = {"h": {"backend": "xai:grok"}, "x": {"backend": "xai:grok"}, "y": {"backend": "nowhere:model"},
                "z": {"backend": "heimdall:deepseek"}}
        seen = []

        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print, cache=None):
            seen.append((sorted(wv), [m["moment_id"] for m in chunk]))
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
        rig = Rig(ms, ["h", "x", "s", "y"], [(True, [], None, Rig.LINE)], [None], no_hook={"s", "y"})
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
    TRIED first: inside an angle and across angles."""

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
        ms = [self.at("h", "A", 12.0, 50), self.at("x", "B", 14.0, 60), self.at("y", "C", 13.0, 70),
              self.at("f", "D", 12.0, 3), self.at("g", "E", 14.0, 4), self.at("k", "F", 13.0, 6)]
        rig = Rig(ms, [["h", "x", "y"], ["f", "g", "k"]], [(True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls[0], ["f", "g", "k"])             # the writer's 2nd angle, fresh, first
        self.assertEqual(out["angles"][0]["hook"], "f")


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

    def test_a_low_rated_hook_is_never_swapped_and_the_search_stops_at_8_line_ups(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
        rig = Rig(ms, [["h", "x", "y", "z"], ["g", "x", "y", "z"]],
                  [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual([c[0] for c in rig.medley_calls], ["h", "g"])     # ruling 59 (c): h's angle ends, g's next
        self.assertIn("written for this hook (ruling 59 c)", out["tried"][0]["why"])
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
                                   stand=PK.stand_alone_check(pk["segments"]))
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


if __name__ == "__main__":
    unittest.main()
