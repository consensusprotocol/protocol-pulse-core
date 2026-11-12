#!/usr/bin/env python3
"""pipeline/context_integrity.py (law L-s, the orchestrator's rulings 3 / 5 / 6) and pipeline/vo_fidelity.py (law
L-o 11 / L-t, the 05:25 classification A / B / C / D): the DECISION RULES, with canned model replies on a fake router
(unit fixtures; the exam corpus is pipeline_pp_tests'). Offline."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
import context_integrity as CI  # noqa: E402
import providers as P  # noqa: E402
import vo_fidelity as VF  # noqa: E402


class Canned:
    """A router stand-in: answers each role from a queue; records (role, avoid_vendor, avoid_family)."""

    def __init__(self, **answers):
        self.answers, self.calls, self.rejected = {k: list(v) for k, v in answers.items()}, [], []

    def call(self, role, prompt, max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None,
             avoid_family=None):
        self.calls.append((role, avoid_vendor, avoid_family))
        q = self.answers.get(role)
        if not q:
            raise P.ProviderError(f"{role}: no canned answer")
        text = q.pop(0)
        return P.Reply(text if isinstance(text, str) else json.dumps(text), f"fake:{role}", "fake")

    def reject(self, reply, why=""):
        self.rejected.append(reply.backend)
        return False


PKG = {"segments": [{"label": "hook", "video_id": "v1", "channel": "Coin Bureau", "text": "Bitcoin held its 200-day average."},
                    {"label": "clip_01", "video_id": "v2", "channel": "Natalie Brunell", "text": "ETF outflows hit $1.3 billion."}],
       "vo": {"intro": "Here's the thing.", "bridges": [], "bridges_after_clip": [], "signoff": "Clips today from ..."},
       "title": "Bitcoin: Coin Bureau and Natalie Brunell", "caption": "Clips from Coin Bureau, Natalie Brunell."}
CTX = {lb: {"text": CI.mark([("before.", False), (s["text"], True), ("after.", False)]), "title": "t",
            "channel": s["channel"]} for lb, s in (("hook", PKG["segments"][0]), ("clip_01", PKG["segments"][1]))}


def a_item(label, **kw):
    d = {"label": label, "speaker_changes_inside": "no", "view": "own_sincere", "referents": [], "conditions": [],
         "retraction": "none", "time_ok": "yes", "proposition": "p", "certainty": "certain", "speaker_is": "uncertain",
         "speaker_evidence": ""}
    d.update(kw)
    return d


def c_item(label, **kw):
    d = {"label": label, "entails": "yes", "dropped_limit": "", "added_by": "", "same_polarity": "yes",
         "stronger_certainty": "no", "raising_words": ""}
    d.update(kw)
    return d


def b_items(cert="certain"):
    return [{"label": lb, "asserts": "p", "certainty": cert, "polarity": "neutral"} for lb in ("hook", "clip_01")]


def run(a=None, b=None, b0=None, c=None, relations=None, pkg=PKG, ctx=CTX):
    A = {"excerpts": a or [a_item("hook"), a_item("clip_01")]}
    rel = relations if relations is not None else [{"labels": ["hook", "clip_01"], "relation": "none"}]
    B = {"takeaways": b or b_items(), "relations": rel}
    B0 = {"takeaways": b0 or b_items(), "relations": rel}
    C = {"pairs": c or [c_item("hook"), c_item("clip_01")]}
    r = Canned(context_verdict=[A, C], viewer_takeaway=[B0, B])
    return CI.check_contexts(r, pkg, ctx, writer_vendor="openai", writer_family="gpt"), r


class TestContextDecision(unittest.TestCase):
    def test_a_clean_package_passes_and_no_judged_step_runs_on_the_writers_vendor_or_family(self):
        res, r = run()
        self.assertTrue(res["ok"], res["violations"])
        self.assertTrue(res["measured"])
        judged = [c for c in r.calls if c[0] != "viewer_takeaway" or c[1] is not None]
        self.assertTrue(all(v == "openai" and f == "gpt" for _, v, f in judged), r.calls)

    def test_every_failure_class_fails(self):
        cases = [
            ({"a": [a_item("hook", view="attributed"), a_item("clip_01")]}, "NOT_OWN_SINCERE"),
            ({"a": [a_item("hook", view="sarcastic"), a_item("clip_01")]}, "NOT_OWN_SINCERE"),
            ({"a": [a_item("hook", speaker_changes_inside="uncertain"), a_item("clip_01")]}, "SPEAKER_CHANGE"),
            ({"a": [a_item("hook", referents=[{"word": "it", "refers_to": "the ETF", "inside": False,
                                               "changes_assertion": "yes"}]), a_item("clip_01")]}, "REFERENT_OUTSIDE"),
            ({"a": [a_item("hook", referents=[{"word": "it", "refers_to": "the ETF", "inside": False,
                                               "changes_assertion": "uncertain"}]), a_item("clip_01")]},
             "REFERENT_OUTSIDE"),
            ({"a": [a_item("hook", conditions=[{"text": "if the Fed cuts", "inside": False}]), a_item("clip_01")]},
             "CONDITION_OUTSIDE"),
            ({"a": [a_item("hook", retraction="later says he misspoke"), a_item("clip_01")]}, "RETRACTION"),
            ({"a": [a_item("hook", certainty="uncertain"), a_item("clip_01")]}, "UNCERTAIN"),
            ({"a": [a_item("hook", time_ok="no"), a_item("clip_01")]}, "STALE_TIME"),
            ({"a": [a_item("hook", time_ok="uncertain"), a_item("clip_01")]}, "STALE_TIME"),
            ({"c": [c_item("hook", entails="uncertain"), c_item("clip_01")]}, "NOT_ENTAILED"),
            ({"c": [c_item("hook", entails="no", dropped_limit="back in 2021"), c_item("clip_01")],
              "ctx": dict(CTX, hook=dict(CTX["hook"], text=CI.mark([("That was back in 2021.", False),
                                                                    (PKG["segments"][0]["text"], True)])))},
             "NOT_ENTAILED"),
            ({"c": [c_item("hook", added_by="Coin Bureau and Natalie Brunell"), c_item("clip_01")]}, "NOT_ENTAILED"),
            ({"c": [c_item("hook", same_polarity="uncertain"), c_item("clip_01")]}, "POLARITY"),
            ({"c": [c_item("hook", stronger_certainty="uncertain"), c_item("clip_01")]}, "STRONGER"),
            ({"c": [c_item("hook", stronger_certainty="yes", raising_words="Here's the thing"), c_item("clip_01")],
              "b0": [dict(b_items()[0], certainty="likely"), b_items()[1]]}, "STRONGER"),
            ({"relations": [{"labels": ["hook", "clip_01"], "relation": "answering"}]}, "FALSE_RELATION"),
            ({"relations": [{"labels": ["hook", "clip_01"], "relation": "uncertain"}]}, "FALSE_RELATION"),
        ]
        for kw, rule in cases:
            res, _ = run(**{k: v for k, v in kw.items()})
            self.assertFalse(res["ok"], rule)
            self.assertIn(rule, {v["rule"] for v in res["violations"]}, (rule, res["violations"]))

    def test_rulings_3_5_6_uncited_disagreements_are_notes_never_failures(self):
        # ruling 3: STRONGER with no cited words, or the clip alone already certain -> a note
        for c in (c_item("hook", stronger_certainty="yes"),
                  c_item("hook", stronger_certainty="yes", raising_words="Here's the thing")):
            res, _ = run(c=[c, c_item("clip_01")])
            self.assertTrue(res["ok"], res["violations"])
            self.assertTrue(res.get("notes"))
        # ruling 3: cited words that are NOT the video's own -> a note
        res, _ = run(c=[c_item("hook", stronger_certainty="yes", raising_words="the bottom is in"), c_item("clip_01")],
                     b0=[dict(b_items()[0], certainty="likely"), b_items()[1]])
        self.assertTrue(res["ok"], res["violations"])
        # ruling 5: entails "no" with no limit, or a limit that is not the context's own words -> a note
        for lim in ("", "for that to emerge"):
            res, _ = run(c=[c_item("hook", entails="no", dropped_limit=lim), c_item("clip_01")])
            self.assertTrue(res["ok"], (lim, res["violations"]))
        # ruling 5: an added claim cited in words that do not name the speaker's show -> a note
        res, _ = run(c=[c_item("hook", added_by="Here's the thing"), c_item("clip_01")])
        self.assertTrue(res["ok"], res["violations"])
        # ruling 3 (referent): outside, but resolving it differently does not change the assertion -> passes
        res, _ = run(a=[a_item("hook", referents=[{"word": "it", "refers_to": "recent hacks", "inside": False,
                                                    "changes_assertion": "no"}]), a_item("clip_01")])
        self.assertTrue(res["ok"], res["violations"])

    def test_an_unreadable_or_incomplete_step_is_not_measured_and_fails(self):
        r = Canned(context_verdict=["not json"], viewer_takeaway=[])
        res = CI.check_contexts(r, PKG, CTX, writer_vendor="openai")
        self.assertEqual((res["ok"], res["measured"], res["violations"][0]["rule"]), (False, False, "CONTEXT_UNAVAILABLE"))
        for kw in ({"a": [a_item("hook")]},                                      # step A skipped a segment
                   {"relations": []},                                            # a pair not rated (audit C5)
                   {"relations": [{"labels": ["hook", "clip_01"], "relation": "none"}] * 2},   # rated twice
                   {"a": [{k: v for k, v in a_item("hook").items() if k != "time_ok"}, a_item("clip_01")]}):   # no default
            res, _ = run(**kw)
            self.assertFalse(res["ok"], kw)
            self.assertIn("CONTEXT_UNAVAILABLE", {v["rule"] for v in res["violations"]}, kw)

    def test_a_relation_inside_one_video_is_allowed(self):
        same = dict(PKG, segments=[dict(PKG["segments"][0]), dict(PKG["segments"][1], video_id="v1")])
        res, _ = run(pkg=same, relations=[{"labels": ["hook", "clip_01"], "relation": "same_conversation"}])
        self.assertTrue(res["ok"], res["violations"])

    def test_the_view_follows_the_renderer_and_the_selection_marks_survive_escaping(self):
        pk = dict(PKG, vo={"intro": "INTRO", "bridges": ["AFTER ONE"], "bridges_after_clip": [1], "signoff": "S"})
        v = CI.package_view(pk)
        self.assertLess(v.index('label="hook"'), v.index("INTRO"))         # the intro plays AFTER the hook
        self.assertLess(v.index('label="clip_01"'), v.index("AFTER ONE"))
        marked = CI.mark([("a <b>", False), ("sel", True)])
        self.assertIn("<selected>sel</selected>", marked)
        self.assertNotIn("<b>", marked)

    def test_a_speaker_is_verified_only_by_host_and_verbatim_evidence_inside_the_selection(self):
        inside = CI.mark([("Hi.", False), ("Welcome back to my channel. Bitcoin is money.", True)])
        self.assertTrue(CI.speaker_verified({"speaker_is": "host", "speaker_evidence": "welcome back to my channel"},
                                            inside))
        self.assertFalse(CI.speaker_verified({"speaker_is": "host", "speaker_evidence": "welcome to the show"}, inside))
        self.assertFalse(CI.speaker_verified({"speaker_is": "guest", "speaker_evidence": "welcome back to my channel"},
                                             inside))
        outside = CI.mark([("Welcome back to my channel everyone.", False), ("Bitcoin is money.", True)])
        self.assertFalse(CI.speaker_verified({"speaker_is": "host", "speaker_evidence": "welcome back to my channel"},
                                             outside))                 # evidence before the clip names nobody in it


class TestFidelityVerdict(unittest.TestCase):
    SEGS = {"m1": {"show": "Coin Bureau", "speaker": None, "names": [], "video_id": "v1",
                   "text": "Bitcoin dropped to $73,000 and found support at its 200-day moving average."},
            "m2": {"show": "Stephan Livera", "speaker": "Stephan Livera", "names": ["Stephan Livera"], "video_id": "v2",
                   "text": "I think Bitcoin is by far the most undervalued asset in the entire financial system."}}
    LINES = [{"slot": "intro", "text": "Coin Bureau says Bitcoin found support at its 200-day moving average.",
              "cites": ["m1"]}]
    T0 = {t: "no" for t in VF.COMMENTARY_TESTS}

    @staticmethod
    def claim(line, words, cls, claim="c", sup="yes", support=(), tests=None):
        return {"line": line, "words": words, "class": cls, "claim": claim, "supported": sup, "support": list(support),
                "tests": tests if tests is not None else {}}

    def verdict(self, claims, lines=None):
        r = Canned(fidelity_verdict=[{"claims": claims}])
        return VF.check(r, self.SEGS, lines or self.LINES, writer_vendor="openai", writer_family="gpt"), r

    def test_an_attribution_with_verbatim_support_passes(self):
        res, r = self.verdict([self.claim("intro", self.LINES[0]["text"], "attribution", support=[
            {"segment": "m1", "words": "found support at its 200-day moving average"}])])
        self.assertTrue(res["ok"], res["violations"])
        self.assertEqual(r.calls, [("fidelity_verdict", "openai", "gpt")])

    def test_host_commentary_passes_on_the_five_tests_alone(self):
        lines = [{"slot": "intro", "text": "So is Bitcoin still cheap at these levels?", "cites": []}]
        res, _ = self.verdict([self.claim("intro", lines[0]["text"], "commentary", sup="n/a", tests=self.T0)], lines)
        self.assertTrue(res["ok"], res["violations"])
        for t in VF.COMMENTARY_TESTS:
            res, _ = self.verdict([self.claim("intro", lines[0]["text"], "commentary", sup="n/a",
                                              tests=dict(self.T0, **{t: "uncertain"}))], lines)
            self.assertIn("COMMENTARY", {v["rule"] for v in res["violations"]}, t)

    def test_commentary_that_carries_a_fact_is_judged_strict(self):
        lines = [{"slot": "intro", "text": "Bitcoin is at 126K now, the bottom is in.", "cites": ["m1"]}]
        res, _ = self.verdict([self.claim("intro", lines[0]["text"], "commentary", sup="n/a", tests=self.T0)], lines)
        self.assertIn("NOT_COMMENTARY", {v["rule"] for v in res["violations"]})

    def test_every_sentence_needs_a_claim_and_an_empty_verdict_fails(self):
        lines = [{"slot": "intro", "text": "Coin Bureau says Bitcoin found support. So is it cheap?", "cites": ["m1"]}]
        half = [self.claim("intro", "Coin Bureau says Bitcoin found support.", "attribution",
                           support=[{"segment": "m1", "words": "found support at its"}])]
        for claims in ([], half):
            res, _ = self.verdict(claims, lines)
            self.assertIn("VERDICT_INCOMPLETE", {v["rule"] for v in res["violations"]}, claims)

    def test_supports_must_be_verbatim_three_words_from_the_lines_own_cites(self):
        for sup in ([{"segment": "m1", "words": "found strong support"}],          # not verbatim
                    [{"segment": "m1", "words": "Bitcoin"}],                       # one word
                    [{"segment": "m2", "words": "the most undervalued asset"}],    # not this line's cite
                    []):
            res, _ = self.verdict([self.claim("intro", self.LINES[0]["text"], "attribution", support=sup)])
            self.assertIn("VERDICT_UNVERIFIED", {v["rule"] for v in res["violations"]}, sup)
        for sup, rule in (("no", "VERDICT_NO"), ("uncertain", "VERDICT_UNCERTAIN")):
            res, _ = self.verdict([self.claim("intro", self.LINES[0]["text"], "attribution", sup=sup)])
            self.assertIn(rule, {v["rule"] for v in res["violations"]})

    def test_production_claims_cite_the_manifest(self):
        lines = [{"slot": "caption", "text": "Clips from Coin Bureau and Stephan Livera.", "cites": []}]
        ok = [self.claim("caption", lines[0]["text"], "production",
                         support=[{"segment": "manifest", "words": "Links to every source are below"}])]
        res, _ = self.verdict(ok, lines)
        self.assertTrue(res["ok"], res["violations"])

    def test_no_verdict_is_a_failure_and_not_measured(self):
        res = VF.check(Canned(), self.SEGS, self.LINES, writer_vendor="openai")
        self.assertEqual((res["ok"], res["measured"]), (False, False))
        self.assertEqual(res["verdict"]["violations"][0]["rule"], "VERDICT_UNAVAILABLE")
        res = VF.check(Canned(fidelity_verdict=[{"claims": [{"line": ["intro"]}]}]), self.SEGS, self.LINES, "openai")
        self.assertEqual(res["verdict"]["violations"][0]["rule"], "VERDICT_UNAVAILABLE")    # malformed: no crash


class TestDeterministicRules(unittest.TestCase):
    SEGS = TestFidelityVerdict.SEGS

    def rules(self, text, cites, levels=None, segs=None):
        r = VF.check_deterministic(segs or self.SEGS, [{"slot": "intro", "text": text, "cites": cites}],
                                   current_levels=levels)
        return {v["rule"] for v in r["violations"]}

    def test_attribution_needs_a_verified_speaker_and_the_clips_own_hedge(self):
        self.assertEqual(self.rules("Stephan Livera thinks Bitcoin is undervalued.", ["m2"]), set())
        self.assertIn("HEDGE", self.rules("Stephan Livera says Bitcoin is undervalued.", ["m2"]))
        unverified = dict(self.SEGS, m2=dict(self.SEGS["m2"], speaker=None, names=[]))
        self.assertIn("ATTRIBUTION", self.rules("Stephan Livera thinks Bitcoin is undervalued.", ["m2"], segs=unverified))
        self.assertEqual(self.rules("Next, on Stephan Livera's show.", ["m2"], segs=unverified), set())
        self.assertIn("ATTRIBUTION", self.rules("She says Bitcoin is undervalued.", ["m2"]))

    def test_names_numbers_quotes_relations_and_imperatives(self):
        self.assertIn("NAME", self.rules("Michael Saylor Warns Of Incoming Crash", ["m1"]))
        self.assertEqual(self.rules("Why The Dollar Is Losing To Bitcoin", ["m1"]), set())
        self.assertIn("NUMBER", self.rules("Seven countries hold Bitcoin.", ["m1"]))
        self.assertIn("QUOTE", self.rules("Coin Bureau calls it 'a crash'.", ["m1"]))
        self.assertIn("RELATION", self.rules("Both agree Bitcoin is undervalued.", ["m1", "m2"]))
        self.assertEqual(self.rules("Next, Coin Bureau on how Bitcoin responded to the rate hike.", ["m1"]), set())
        self.assertIn("IMPERATIVE", self.rules("It's time to buy.", ["m1"]))
        self.assertEqual(self.rules("Short-term holders are selling.", ["m1"]), set())

    def test_price_now_reads_history_forecasts_and_counts(self):
        self.assertIn("PRICE_NOW", self.rules("Bitcoin just set an all-time high at $126,000.", ["m1"], [73000.0]))
        self.assertIn("PRICE_NOW", self.rules("Since 2022, Bitcoin is at $126,000.", ["m1"], [73000.0]))
        self.assertNotIn("PRICE_NOW", self.rules("Strategy now holds 640,000 bitcoin.", ["m1"], [73000.0]))
        self.assertEqual(VF.price_now("From the 2022 low, Bitcoin ran from 16K to 126K", [73000.0]), [])
        self.assertEqual(VF.price_now("Bitcoin could hit 150,000", [73000.0]), [])


if __name__ == "__main__":
    unittest.main()
