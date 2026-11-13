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
        r = Canned(coherence_verdict=[verdict(self.LABS)])
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
        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
        self.assertTrue(ok)
        self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
        self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)

    def test_no_through_line_or_a_weak_clip_fails(self):
        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])

    def test_out_of_contract_is_not_measured_and_rejected(self):
        good = verdict(self.LABS)
        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
                    dict(good, vo_point=5),
                    dict(good, clips={"hook": 5, "clip_01": 5})):
            ok, v, r = self.run_it(bad)
            self.assertFalse(ok)
            self.assertFalse(v["measured"])
            self.assertIsNone(v["flagged"])
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
                 trim_fail=()):
        import providers as P
        self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
        self.takeaways, self.spend = list(takeaways or []), spend
        self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
        self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
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
                  batch=PK.PRESCREEN_BATCH, store=None, log=print):
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
            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
                                                             "replayed": False}),
        }
        saved = {k: getattr(PK, k) for k in stubs}
        try:
            for k, v in stubs.items():
                setattr(PK, k, v)
            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent",
                            spend=self.spend)
        finally:
            for k, v in saved.items():
                setattr(PK, k, v)


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

    def test_a_hook_without_80_ms_of_genuine_quiet_gives_way_and_none_means_no_line_up(self):
        """Batch pin #1, held 01:39 ET Nov 13 (G17a: 30 ms of genuine lead before the hook). A moment opens a medley
        only when its hook onset was measured and passed; the proposer's hook gives way to the angle's next."""
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h"})
        pk = rig.run()["package"]
        self.assertNotEqual(pk["segments"][0]["moment_id"], "h")
        self.assertEqual(pk["gates"]["hook_onset"]["status"], "PASS")
        self.assertEqual(pk["gates"]["hook_onset"]["lead_ms"], 200)
        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"h", "x", "y", "z"})
        out = rig.run()
        self.assertIsNone(out["package"])
        self.assertEqual(rig.medley_calls, [])                    # nothing paid for a line-up that cannot open
        self.assertIn("no line-up", out["tried"][0]["why"])

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
    clip scorer's verdict is pending at the render; the pin seals trimmed_leading and untrimmed_start."""

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
                         "Bitcoin had six negative weeks back to back in its whole history."):             # no opener
            m, srcs = self.moment(sentence)
            self.assertIsNone(PK.trim_variant(m, srcs), sentence)
        self.assertEqual(PK.TRIM_WORDS, package_pin.TRIM_WORDS)
        m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
        self.assertIsNone(PK.trim_variant(m, srcs))

    def test_strict_by_default_and_pending_at_the_render_only_on_the_switch(self):
        m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
        v = PK.trim_variant(m, srcs)
        line = [{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}]
        self.assertFalse(PK.TRIM_SCORER_PENDING)                      # the default: the render's check, no scorer
        r = PK.stand_alone_check(line)
        self.assertFalse(r["ok"])                                     # a trimmed segment fails closed, never sealed
        self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
        self.assertEqual(r["scorer_pending"], [])
        saved = PK.TRIM_SCORER_PENDING
        try:                                                          # the orchestrator's explicit yes only
            PK.TRIM_SCORER_PENDING = True
            r = PK.stand_alone_check(line)
        finally:
            PK.TRIM_SCORER_PENDING = saved
        self.assertTrue(r["ok"], r["rows"])
        self.assertEqual(r["scorer_pending"], ["clip_01"])
        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row

    def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
        segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
                dict(pm("x", "B", 14.0), text="Bitcoin keeps every promise it ever made to me.",
                     trimmed_leading="But", untrimmed_start=0.0, start=0.3),
                dict(pm("y", "C", 13.0), text="Bitcoin wins in the end, every single time.")]
        by = {m["moment_id"]: m for m in segs}
        fields = {"takeaway": {"text": "No ruler, just rules nobody gets to bend.", "cites": []}, "bridge": None,
                  "bridge_after": None, "title": {"text": "No ruler.", "cites": []},
                  "caption": {"text": "three clips", "cites": []}}
        pk = PK.assemble_medley(["h", "x", "y"], by, fields, ctx(), "medley (L-y)")
        self.assertEqual((pk["segments"][1]["trimmed_leading"], pk["segments"][1]["untrimmed_start"]), ("But", 0.0))
        pk["gates"] = TestMedleyPackageAndPin().gates(pk)
        pin = package_pin.to_pin(spk(pk), "test")
        s1 = pin["segments"][1]
        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
        self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
        mp = pin["moments_package"]
        args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
        self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
        other = [dict(x) for x in pin["segments"]]
        other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0}):
            p = spk(pk)
            p["segments"][1] = dict(p["segments"][1], **bad)
            with self.assertRaises(package_pin.PinRefused):
                package_pin.to_pin(p, "test")
        self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
        p = spk(pk)                                                       # ^ refused, never raised (glm P0-8)
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
            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"})
            out = rig.run()
            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
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

        def fake(router_, chunk, sources, ctx_, wv, wf, n=None, store=None, log=print):
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

    def test_the_build_swaps_a_low_rated_hook_and_stops_at_8_line_ups(self):
        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0), pm("g", "E", 12.0)]
        rig = Rig(ms, ["h", "x", "y", "z"], [(False, [], {"hook": 3}, Rig.LINE), (True, [], None, Rig.LINE)], [None])
        out = rig.run()
        self.assertEqual(rig.medley_calls[0][0], "h")
        self.assertNotEqual(rig.medley_calls[1][0], "h")                    # the hook rated 3 was swapped
        self.assertIn("swapped", out["tried"][0]["why"])
        self.assertIsNotNone(out["package"])
        many = [pm(c, c.upper(), 13.0) for c in "abcdefghijklmnop"]
        fails = [(False, [], {"clip_01": 2}, Rig.LINE)] * 12
        rig = Rig(many, [list("abcdefgh"), list("ijklmnop"), list("aceg")], fails, [])
        out = rig.run()
        self.assertEqual(len(rig.medley_calls), PK.LINEUPS_PER_BUILD)       # 8, over every angle
        self.assertEqual(out["search"]["lineups"], 8)


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
