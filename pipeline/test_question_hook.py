#!/usr/bin/env python3
"""Ruling 37 (orchestrator 2026-11-13 '03:42'): edl_rules R1 NO_QUESTION_HOOK is relaxed for moments pins: a hook may end
on a question when the clips-alone verdict and the blind coherence check pass the join that follows it; a question
ending stays refused for every non-hook clip.
must-pass  a moments hook ending on '?' with the sealed gates: medley PASS live with 'hook -> clip_01' not flagged,
           coherence PASS live (another join flagged does not matter); pinned.build_edl carries the sealed gates
must-fail  that join flagged; either verdict missing, not PASS, replayed or unstated; no flagged list; a non-hook clip
           of a moments pin ending on '?'; any question hook outside a bound moments package (story path unchanged)"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
from edl_rules import rule_r1  # noqa: E402

LIVE = {"status": "PASS", "by": "xai:grok", "replayed": False, "n": 1}


def moments(hook="Is Bitcoin finished after six red weeks?", clip1="No, it has done this before.",
            clip2="Every cycle looked like this.", medley=None, coherence=None, **extra):
    gates = {"medley": dict(LIVE, flagged=[]) if medley is None else medley,
             "coherence": dict(LIVE) if coherence is None else coherence}
    return {"hook": {"text": hook}, "clips": [{"index": 1, "text": clip1}, {"index": 2, "text": clip2}],
            "package_type": "moments", "moments_package_sha256": "ab" * 32, "moments_gates": gates, **extra}


class TestQuestionHook(unittest.TestCase):
    def test_a_question_hook_passes_when_both_verdicts_pass_the_join_after_it(self):
        ok, why = rule_r1(moments())
        self.assertTrue(ok, why)
        self.assertIn("R1 PASS (ruling 37): the hook ends on a question", why)
        ok, why = rule_r1(moments(medley=dict(LIVE, flagged=["clip_01 -> clip_02"])))   # another join: not this rule's
        self.assertTrue(ok, why)

    def test_the_join_flagged_or_a_verdict_not_live_and_passing_fails(self):
        bad = [({"medley": dict(LIVE, flagged=["hook -> clip_01"])}, "flagged the join that follows it"),
               ({"medley": dict(LIVE, status="FAIL", flagged=[])}, "clips-alone verdict is not on the pin"),
               ({"medley": dict(LIVE, replayed=True, flagged=[])}, "clips-alone verdict is not on the pin"),
               ({"medley": {"status": "PASS", "flagged": []}}, "clips-alone verdict is not on the pin"),   # unstated
               ({"medley": dict(LIVE)}, "clips-alone verdict is not on the pin"),                         # no list
               ({"medley": dict(LIVE, flagged=None)}, "clips-alone verdict is not on the pin"),
               ({"coherence": dict(LIVE, status="FAIL")}, "blind coherence check did not pass"),
               ({"coherence": dict(LIVE, replayed=True)}, "blind coherence check did not pass"),
               ({"coherence": {"status": "PASS"}}, "blind coherence check did not pass")]
        for kw, why_part in bad:
            with self.subTest(kw=kw):
                ok, why = rule_r1(moments(**kw))
                self.assertFalse(ok, why)
                self.assertIn("R1 FAIL (ruling 37)", why)
                self.assertIn(why_part, why)
        # batch 59 cycle 2 C1 (glm, qwen): the shared reason does not say WHICH condition fired, so each failing row is
        # a minimal pair: the same row with exactly that one field made right passes
        pairs = [({"medley": {"status": "PASS", "flagged": []}}, {"medley": {"status": "PASS", "flagged": [], "replayed": False}}),
                 ({"medley": dict(LIVE)}, {"medley": dict(LIVE, flagged=[])}),
                 ({"medley": dict(LIVE, flagged=None)}, {"medley": dict(LIVE, flagged=[])}),
                 ({"medley": dict(LIVE, status="FAIL", flagged=[])}, {"medley": dict(LIVE, status="PASS", flagged=[])}),
                 ({"medley": dict(LIVE, replayed=True, flagged=[])}, {"medley": dict(LIVE, replayed=False, flagged=[])}),
                 ({"medley": dict(LIVE, flagged=["hook -> clip_01"])}, {"medley": dict(LIVE, flagged=["clip_01 -> clip_02"])}),
                 ({"coherence": {"status": "PASS"}}, {"coherence": {"status": "PASS", "replayed": False}}),
                 ({"coherence": dict(LIVE, replayed=True)}, {"coherence": dict(LIVE, replayed=False)})]
        for bad_kw, good_kw in pairs:
            with self.subTest(pair=bad_kw):
                self.assertEqual((rule_r1(moments(**bad_kw))[0], rule_r1(moments(**good_kw))[0]), (False, True))
        for gates in (None, {}, [], {"medley": dict(LIVE, flagged=[])}, {"coherence": dict(LIVE)}):
            with self.subTest(gates=gates):
                e = moments()
                e["moments_gates"] = gates
                self.assertFalse(rule_r1(e)[0])

    def test_a_question_ending_stays_refused_for_every_non_hook_clip(self):
        for clips in (("Is that the bottom?", "It held."), ("It held.", "Is that the bottom?  ")):
            with self.subTest(clips=clips):
                ok, why = rule_r1(moments(hook="Bitcoin fell six weeks in a row.", clip1=clips[0], clip2=clips[1]))
                self.assertFalse(ok, why)
                self.assertIn("a question ending is refused for every non-hook clip", why)
        ok, why = rule_r1(moments(clip1="Is that the bottom?"))       # with a passing question hook too
        self.assertFalse(ok, why)

    def test_outside_a_bound_moments_package_r1_is_unchanged(self):
        story = moments()
        for k in ("package_type", "moments_package_sha256"):
            with self.subTest(drop=k):
                e = {kk: v for kk, v in story.items() if kk != k}
                ok, why = rule_r1(e)
                self.assertFalse(ok)
                self.assertTrue(why.startswith("R1 FAIL: hook ends with question"), why)
        e = {"hook": {"text": "Bitcoin fell."}, "clips": [{"index": 1, "text": "Is that the bottom?"}]}
        self.assertEqual(rule_r1(e), (True, "R1 PASS: hook ends on a statement"))   # the story path: hook only
        self.assertEqual(rule_r1(moments(hook="Bitcoin fell six weeks.")),
                         (True, "R1 PASS: hook ends on a statement"))


class TestBuildEdlCarriesTheSealedGates(unittest.TestCase):
    def test_moments_gates_is_the_package_gates(self):
        import pinned
        tmp = tempfile.mkdtemp(prefix="r37_")
        self.addCleanup(shutil.rmtree, tmp, True)
        tpath = os.path.join(tmp, "t.json")
        words = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25}
                 for i, w in enumerate("Is Bitcoin finished now ? No it held .".split())]
        with open(tpath, "w") as f:
            json.dump({"words": words}, f)
        gates = {"medley": dict(LIVE, flagged=[]), "coherence": dict(LIVE)}
        mp = {"type": "moments", "title": "t", "caption": "c", "package_sha256": "ab" * 32, "gates": gates,
              "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True},
              "sources_30s_before": ["https://youtu.be/?v=AAAAAAAAAAA", "https://youtu.be/?v=AAAAAAAAAAA"],
              "edl_vo": {"intro": None, "bridges": []}}
        seg = {"video_id": "AAAAAAAAAAA", "channel": "X", "time_coords": "youtube", "start": 0.0, "end": 1.0}
        pin = {"label": "bitcoin", "story_id": "s", "moments_package": mp,
               "segments": [dict(seg, role="hook"), dict(seg, role="clip", start=1.5, end=2.6)]}
        acq = {"AAAAAAAAAAA": {"path": "unused.mp4", "offset": 0.0, "transcript": {"words": words},
                               "transcript_path": tpath, "provenance": {}}}

        def vr(s, a):
            i0, i1 = (0, 3) if s["role"] == "hook" else (5, 7)
            return {"start_file": s["start"], "end_file": s["end"], "source_duration": 10.0, "words": words[i0:i1 + 1],
                    "text": " ".join(w["word"] for w in words[i0:i1 + 1]), "first_word": words[i0]["word"],
                    "last_word": words[i1]["word"], "i0": i0, "i1": i1, "transcript_word_straddles_boundary": [],
                    "edge_words_from": "test"}
        with mock.patch.object(pinned, "validate_range", vr), \
                mock.patch("select_passages._generate_vo_script", return_value={"intro": None, "bridges": []}), \
                mock.patch("select_passages.build_vertical_overrides", return_value={}):
            edl, _, _ = pinned.build_edl(pin, acq, registry=[{"display_name": "X", "channel_id": "UCx"}],
                                         log=lambda *a: None)
        self.assertEqual(edl["moments_gates"], gates)
        self.assertEqual(edl["moments_package_sha256"], "ab" * 32)


if __name__ == "__main__":
    unittest.main()
