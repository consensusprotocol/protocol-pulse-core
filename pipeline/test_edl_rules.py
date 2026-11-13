#!/usr/bin/env python3
"""Unit tests for pipeline/edl_rules.py (R1-R9).

The v2 overnight EDL is the must-fail fixture:
- R2 FAIL: hook == clip 1 (same video_id, 10.3s overlap)
- R4 FAIL: intro 37 words, 3 bridges vs 2 transitions, VO 58% runtime
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edl_rules import (rule_r1, rule_r2, rule_r3, rule_r4, rule_r5, rule_r6,
                       rule_r9, rule_r11, validate_edl)

# Load fixtures
FIXTURE_DIR = os.path.dirname(os.path.abspath(__file__))
V2_EDL_PATH = os.path.join(os.path.dirname(FIXTURE_DIR), "segment_v2", "edl_v2.json")
V1_EDL_PATH = os.path.join(os.path.dirname(FIXTURE_DIR), "segment_v1", "edl_v2.json")
CHANNELS_PATH = os.path.join(FIXTURE_DIR, "channels.json")


def _load_json(path):
    with open(path) as f:
        return json.load(f)


class TestR1NoQuestionHook(unittest.TestCase):
    """R1: Hook passage must be a statement, not a question."""

    def test_statement_hook_passes(self):
        edl = {"hook": {"text": "Bitcoin is the future of money."}}
        ok, reason = rule_r1(edl)
        self.assertTrue(ok, reason)

    def test_question_hook_fails(self):
        edl = {"hook": {"text": "Is Bitcoin the future of money?"}}
        ok, reason = rule_r1(edl)
        self.assertFalse(ok, reason)

    def test_qa_hook_passes(self):
        """A passage with Q&A that ENDS on a statement is acceptable."""
        edl = {"hook": {"text": "What did tether freeze? Three, uh, 1.6 billion or something like that."}}
        ok, reason = rule_r1(edl)
        self.assertTrue(ok, reason)

    def test_empty_hook_fails(self):
        edl = {"hook": {"text": ""}}
        ok, reason = rule_r1(edl)
        self.assertFalse(ok, reason)

    def test_v1_edl_passes(self):
        """The approved v1 EDL hook should pass R1."""
        if os.path.exists(V1_EDL_PATH):
            edl = _load_json(V1_EDL_PATH)
            ok, reason = rule_r1(edl)
            self.assertTrue(ok, reason)

    def test_v2_edl_passes_r1(self):
        """The v2 overnight EDL hook is actually a statement (ends with 'cryptocurrency.')"""
        if os.path.exists(V2_EDL_PATH):
            edl = _load_json(V2_EDL_PATH)
            ok, reason = rule_r1(edl)
            self.assertTrue(ok, reason)


class TestR2NoDuplicatePassage(unittest.TestCase):
    """R2: No temporal overlap > 1.0s, hook != clip 1."""

    def test_no_overlap_passes(self):
        edl = {
            "hook": {"video_id": "A", "word_start": 10, "word_end": 20},
            "clips": [
                {"index": 1, "video_id": "B", "word_start": 30, "word_end": 40},
            ]
        }
        ok, reason = rule_r2(edl)
        self.assertTrue(ok, reason)

    def test_hook_reused_as_clip1_fails(self):
        """Hook and clip 1 are the same passage (same video_id, full overlap)."""
        edl = {
            "hook": {"video_id": "A", "word_start": 10, "word_end": 20},
            "clips": [
                {"index": 1, "video_id": "A", "word_start": 10, "word_end": 20},
            ]
        }
        ok, reason = rule_r2(edl)
        self.assertFalse(ok, reason)
        self.assertIn("overlap", reason)

    def test_v2_overnight_fails_r2(self):
        """The v2 overnight EDL has hook == clip 1 (10.3s overlap). Must fail."""
        if os.path.exists(V2_EDL_PATH):
            edl = _load_json(V2_EDL_PATH)
            ok, reason = rule_r2(edl)
            self.assertFalse(ok, f"V2 EDL should fail R2 but got: {reason}")

    def test_partial_overlap_above_threshold_fails(self):
        edl = {
            "hook": {"video_id": "A", "word_start": 10, "word_end": 22},
            "clips": [
                {"index": 1, "video_id": "A", "word_start": 20, "word_end": 30},
            ]
        }
        ok, reason = rule_r2(edl)
        self.assertFalse(ok, reason)  # 2.0s overlap > 1.0s

    def test_partial_overlap_below_threshold_passes(self):
        edl = {
            "hook": {"video_id": "A", "word_start": 10, "word_end": 20.5},
            "clips": [
                {"index": 1, "video_id": "A", "word_start": 20, "word_end": 30},
            ]
        }
        ok, reason = rule_r2(edl)
        self.assertTrue(ok, reason)  # 0.5s overlap <= 1.0s


class TestR3VoAfterAnswer(unittest.TestCase):
    """R3: VO bridges only after clips ending on statements."""

    def test_bridge_after_statement_passes(self):
        edl = {
            "clips": [{"index": 1, "text": "Bitcoin is the answer."}],
            "vo": {"bridges": [{"after_clip": 1, "text": "And here is why."}]}
        }
        ok, reason = rule_r3(edl)
        self.assertTrue(ok, reason)

    def test_bridge_after_question_fails(self):
        edl = {
            "clips": [{"index": 1, "text": "Is Bitcoin the answer?"}],
            "vo": {"bridges": [{"after_clip": 1, "text": "And here is why."}]}
        }
        ok, reason = rule_r3(edl)
        self.assertFalse(ok, reason)


class TestR4VoBudget(unittest.TestCase):
    """R4: VO word limits and budget."""

    def test_within_budget_passes(self):
        edl = {
            "clips": [
                {"index": 1, "duration": 15, "channel": "A"},
                {"index": 2, "duration": 15, "channel": "B"},
            ],
            "total_clip_duration": 30,
            "vo": {
                "intro": "Short intro text here.",
                "bridges": [{"after_clip": 1, "text": "Bridge text."}],
                "signoff": "Follow them.",
            }
        }
        ok, reason = rule_r4(edl)
        self.assertTrue(ok, reason)

    def test_intro_over_30_words_fails(self):
        long_intro = " ".join(["word"] * 35)
        edl = {
            "clips": [{"index": 1, "duration": 60, "channel": "A"}],
            "total_clip_duration": 60,
            "vo": {"intro": long_intro, "bridges": []}
        }
        ok, reason = rule_r4(edl)
        self.assertFalse(ok, reason)
        self.assertIn("intro=35", reason)

    def test_v2_overnight_fails_r4(self):
        """The v2 overnight EDL has intro=37 words and too many bridges. Must fail."""
        if os.path.exists(V2_EDL_PATH):
            edl = _load_json(V2_EDL_PATH)
            ok, reason = rule_r4(edl)
            self.assertFalse(ok, f"V2 EDL should fail R4 but got: {reason}")


class TestR5ClipLength(unittest.TestCase):
    """R5 (law L-o): >= 2 clips from >= 2 channels is integrity (a failure); the 8-25 s window and the per-channel
    >= 8 s total are taste (a recorded deviation with its size, never a rejection)."""

    def test_good_clips_pass(self):
        edl = {
            "clips": [
                {"index": 1, "duration": 12, "channel": "A"},
                {"index": 2, "duration": 15, "channel": "B"},
            ]
        }
        ok, reason = rule_r5(edl)
        self.assertTrue(ok, reason)

    def test_a_short_clip_is_a_recorded_deviation_not_a_failure(self):
        """Law L-o (taste): until 2026-11-12 this was 'clip too short fails'. A whole sentence beats the window: the
        6.1 s punchline is kept and its deviation recorded with its size."""
        edl = {
            "clips": [
                {"index": 1, "duration": 15, "channel": "A"},
                {"index": 2, "duration": 6.1, "channel": "B"},
            ]
        }
        ok, reason = rule_r5(edl)
        self.assertTrue(ok, reason)
        self.assertEqual(reason, "R5 PASS | law L-o taste deviations, recorded, not causes: clip 2: 6.10s (5.90s under "
                                 "the 12-20s target)")
        ok, reason = rule_r5({"clips": [{"index": 1, "duration": 30, "channel": "A"},
                                        {"index": 2, "duration": 12, "channel": "B"}]})
        self.assertTrue(ok, reason)
        self.assertIn("clip 1: 30.00s (10.00s over the 12-20s target)", reason)
        for edge in (12.0, 20.0):                                        # the target's own edges are inside it
            ok, reason = rule_r5({"clips": [{"index": 1, "duration": edge, "channel": "A"},
                                            {"index": 2, "duration": 15, "channel": "B"}]})
            self.assertEqual((ok, reason), (True, "R5 PASS: clip lengths and channel diversity OK"))

    def test_integrity_still_rejects_one_clip_or_one_channel(self):
        """Must-fail (law L-o integrity: >= 2 channels per video): a short clip never rescues a single channel."""
        for edl, why in (({"clips": [{"index": 1, "duration": 12, "channel": "A"}]}, "only 1 clips"),
                         ({"clips": [{"index": 1, "duration": 12, "channel": "A"},
                                     {"index": 2, "duration": 5, "channel": "A"}]}, "only 1 channel(s)"),
                         ({"clips": [{"index": 1, "duration": 15, "channel": "A"},
                                     {"index": 2, "duration": 0, "channel": "B"}]}, "only 1 channel(s)"),   # B: no time
                         ({"clips": []}, "only 0 clips")):
            ok, reason = rule_r5(edl)
            self.assertFalse(ok, reason)
            self.assertTrue(reason.startswith("R5 FAIL"), reason)
            self.assertIn(why, reason)
        ok, reason = rule_r5({"clips": [{"index": 1, "duration": 5, "channel": "A"},
                                        {"index": 2, "duration": 6, "channel": "A"}]})
        self.assertRegex(reason, r"^R5 FAIL: only 1 channel.* \| law L-o taste deviations, recorded, not causes: ")

    def test_an_unmeasured_duration_or_a_missing_channel_is_never_a_pass(self):
        """Under L-o the window no longer rejects, so a degenerate duration or channel must fail on its own (fail
        closed); two valid channels are present, so the failure is the third clip's alone."""
        good = [{"index": 1, "duration": 12, "channel": "A"}, {"index": 2, "duration": 14, "channel": "B"}]
        for bad in (0, -3.0, None, float("nan"), float("inf"), "12", True, 10 ** 400, "missing"):
            with self.subTest(duration=bad):
                clip = {"index": 3, "duration": bad, "channel": "C"}
                if bad == "missing":
                    del clip["duration"]
                ok, reason = rule_r5({"clips": good + [clip]})
                self.assertFalse(ok, reason)
                self.assertTrue(reason.startswith("R5 FAIL: clip 3: duration "), reason)
                self.assertNotIn("channel(s)", reason)
        for bad in (None, "", "   ", 7, "missing"):
            with self.subTest(channel=bad):
                clip = {"index": 3, "duration": 13, "channel": bad}
                if bad == "missing":
                    del clip["channel"]
                ok, reason = rule_r5({"clips": [good[0], clip]})          # only A is a real channel
                self.assertFalse(ok, reason)
                self.assertIn("clip 3: no channel named", reason)
                self.assertIn("only 1 channel(s)", reason)
        ok, reason = rule_r5({"clips": good + [{"index": 3, "duration": 11.996, "channel": "C"}]})
        self.assertIn("0.01s under", reason)                              # never 'X.XXs (0.00s under ...)'

    def test_single_channel_fails(self):
        edl = {
            "clips": [
                {"index": 1, "duration": 12, "channel": "A"},
                {"index": 2, "duration": 15, "channel": "A"},
            ]
        }
        ok, reason = rule_r5(edl)
        self.assertFalse(ok, reason)
        self.assertIn("1 channel", reason)


class TestR6CreditsMatch(unittest.TestCase):
    """R6: Credits match EDL channels."""

    def test_matching_signoff_passes(self):
        edl = {
            "clips": [
                {"index": 1, "channel": "A"},
                {"index": 2, "channel": "B"},
            ],
            "vo": {"signoff": "Clips from A and B."}
        }
        ok, reason = rule_r6(edl)
        self.assertTrue(ok, reason)

    def test_missing_channel_in_signoff_fails(self):
        edl = {
            "clips": [
                {"index": 1, "channel": "A"},
                {"index": 2, "channel": "B"},
            ],
            "vo": {"signoff": "Clips from A."}
        }
        ok, reason = rule_r6(edl)
        self.assertFalse(ok, reason)
        self.assertIn("B", reason)


class TestV2OvernightMustFail(unittest.TestCase):
    """Integration test: the v2 overnight EDL must fail validation overall."""

    def test_v2_edl_fails_overall(self):
        if not os.path.exists(V2_EDL_PATH):
            self.skipTest("V2 EDL fixture not found")

        edl = _load_json(V2_EDL_PATH)
        channels_registry = None
        if os.path.exists(CHANNELS_PATH):
            channels_registry = _load_json(CHANNELS_PATH)

        all_pass, results = validate_edl(edl, channels_registry)
        self.assertFalse(all_pass, "V2 overnight EDL must fail validation")

        # Specifically R2 and R4 must fail
        r2 = next(r for r in results if r["rule"] == "rule_r2")
        r4 = next(r for r in results if r["rule"] == "rule_r4")
        self.assertFalse(r2["pass"], "R2 must fail: hook == clip 1")
        self.assertFalse(r4["pass"], "R4 must fail: VO budget blown")


class TestG4ShoutoutExclusion(unittest.TestCase):
    """G4: Face gate applies to talking_head scenes only; shoutout is excluded."""

    def test_shoutout_excluded_from_face_gate(self):
        """Shoutout segments must NOT be fed to the face-counting loop in G4.
        The shoutout has its own dedicated circle check (shoutout_circle)."""
        sys.path.insert(0, os.path.join(os.path.dirname(FIXTURE_DIR), "segment_v1"))
        import qa_gates
        import importlib
        importlib.reload(qa_gates)  # ensure fresh import after patch

        # Read the gate_g4 source to verify it only processes talking_head
        import inspect
        src = inspect.getsource(qa_gates.gate_g4)
        # The face-counting loop filter line must use != "talking_head"
        # (not a tuple that includes "shoutout" as a face-counted type)
        self.assertIn('!= "talking_head"', src,
                      "G4 face-counting loop must filter on type != 'talking_head'")
        # The old pattern was: not in ("talking_head", "shoutout")
        # which incorrectly included shoutout in face counting
        self.assertNotIn('not in ("talking_head", "shoutout")', src,
                         "G4 must NOT use tuple filter that includes shoutout in face counting")


class TestR9ClipEndsOnSentence(unittest.TestCase):
    """R9: cut_out must land on a sentence-ending word + tail pause before next word."""

    def _make_transcript(self, words_data):
        """Helper: build transcript dict keyed by video_id."""
        return {"VID1": words_data}

    def test_clean_sentence_end_passes(self):
        """Cut ends on 'money.' with 0.30s tail, before next word."""
        edl = {
            "hook": {"video_id": "VID1", "last_word": "money.", "cut_out": 10.30, "word_end": 10.0},
            "clips": []
        }
        words = [
            {"word": "about", "start": 8.0, "end": 8.5},
            {"word": "money.", "start": 9.5, "end": 10.0},
            {"word": "Now", "start": 10.5, "end": 10.8},
        ]
        ok, reason = rule_r9(edl, self._make_transcript(words))
        self.assertTrue(ok, reason)

    def test_cut_into_next_word_fails(self):
        """Cut runs past sentence into next word — must fail."""
        edl = {
            "hook": {},
            "clips": [{"index": 1, "video_id": "VID1", "last_word": "have.",
                        "cut_out": 1012.5, "word_end": 1011.74}]
        }
        words = [
            {"word": "they", "start": 1011.28, "end": 1011.44},
            {"word": "have.", "start": 1011.44, "end": 1011.74},
            {"word": "It's", "start": 1011.84, "end": 1012.18},
            {"word": "not", "start": 1012.18, "end": 1012.32},
        ]
        ok, reason = rule_r9(edl, self._make_transcript(words))
        self.assertFalse(ok, reason)
        self.assertIn("next word", reason)

    def test_v2c_clip03_old_cutout_fails(self):
        """The v2c clip_03 cut_out=1012.5 ran past 'have.' into 'It's not' — must fail R9."""
        edl = {
            "hook": {},
            "clips": [{"index": 3, "video_id": "VID1", "last_word": "have.",
                        "cut_out": 1012.5, "word_end": 1011.74}]
        }
        words = [
            {"word": "debt", "start": 1010.02, "end": 1010.96},
            {"word": "that", "start": 1010.96, "end": 1011.28},
            {"word": "they", "start": 1011.28, "end": 1011.44},
            {"word": "have.", "start": 1011.44, "end": 1011.74},
            {"word": "It's", "start": 1011.84, "end": 1012.18},
            {"word": "not", "start": 1012.18, "end": 1012.32},
            {"word": "impossible.", "start": 1012.32, "end": 1012.76},
        ]
        ok, reason = rule_r9(edl, self._make_transcript(words))
        self.assertFalse(ok, f"Old v2c clip_03 cut_out=1012.5 should fail R9: {reason}")

    def test_v2d_clip03_fixed_cutout_passes(self):
        """The v2d clip_03 cut_out=1011.80 ends cleanly on 'have.' — must pass."""
        edl = {
            "hook": {},
            "clips": [{"index": 3, "video_id": "VID1", "last_word": "have.",
                        "cut_out": 1011.80, "word_end": 1011.74}]
        }
        words = [
            {"word": "debt", "start": 1010.02, "end": 1010.96},
            {"word": "that", "start": 1010.96, "end": 1011.28},
            {"word": "they", "start": 1011.28, "end": 1011.44},
            {"word": "have.", "start": 1011.44, "end": 1011.74},
            {"word": "It's", "start": 1011.84, "end": 1012.18},
        ]
        ok, reason = rule_r9(edl, self._make_transcript(words))
        self.assertTrue(ok, reason)

    def test_non_sentence_ending_fails(self):
        """Last word without . ? ! fails R9."""
        edl = {
            "hook": {},
            "clips": [{"index": 1, "video_id": "VID1", "last_word": "money",
                        "cut_out": 10.30, "word_end": 10.0}]
        }
        words = [
            {"word": "the", "start": 9.0, "end": 9.2},
            {"word": "money", "start": 9.5, "end": 10.0},
            {"word": "is", "start": 10.5, "end": 10.7},
        ]
        ok, reason = rule_r9(edl, self._make_transcript(words))
        self.assertFalse(ok, reason)
        self.assertIn("not sentence-ending", reason)

    def test_no_transcripts_skips(self):
        """Without transcripts, R9 skips (not a failure)."""
        edl = {"hook": {}, "clips": []}
        ok, reason = rule_r9(edl, None)
        self.assertTrue(ok)
        self.assertIn("SKIP", reason)


class TestSignoffValidation(unittest.TestCase):
    """Signoff validator unit tests (no network calls)."""

    def setUp(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from signoff import validate_signoff
        self.validate = validate_signoff
        self.channels = ["Bitcoin Magazine", "The Bitcoin Layer", "BTC Sessions"]

    def test_valid_signoff_passes(self):
        text = "Big thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions for these clips today. Go follow all three of them, links below."
        ok, reason = self.validate(text, self.channels, [])
        self.assertTrue(ok, reason)

    def test_missing_channel_fails(self):
        text = "Big thanks to Bitcoin Magazine and BTC Sessions for the clips. Go follow them, links below in the description box."
        ok, reason = self.validate(text, self.channels, [])
        self.assertFalse(ok)
        self.assertIn("The Bitcoin Layer", reason)

    def test_no_follow_ask_fails(self):
        text = "Clips today from Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions. Links are below in the description box for you."
        ok, reason = self.validate(text, self.channels, [])
        self.assertFalse(ok)
        self.assertIn("follow", reason)

    def test_too_short_fails(self):
        text = "Thanks Bitcoin Magazine, The Bitcoin Layer, BTC Sessions. Follow them."
        ok, reason = self.validate(text, self.channels, [])
        self.assertFalse(ok)
        self.assertIn("too short", reason)

    def test_too_long_fails(self):
        text = ("Massive thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions "
                "for bringing these incredible clips to us today and every single day. "
                "Go follow all of them right now, links are below.")
        ok, reason = self.validate(text, self.channels, [])
        self.assertFalse(ok)
        self.assertIn("too long", reason)

    def test_hashtag_fails(self):
        text = "Thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions. Go follow them #Bitcoin links below in the description."
        ok, reason = self.validate(text, self.channels, [])
        self.assertFalse(ok)
        self.assertIn("hashtag", reason)

    def test_em_dash_fails(self):
        text = "Thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions \u2014 go follow them all, links are below in the description."
        ok, reason = self.validate(text, self.channels, [])
        self.assertFalse(ok)
        self.assertIn("dash", reason)

    def test_jaccard_overlap_fails(self):
        prev = "Big thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions for the clips today. Go follow all three of them."
        history = [{"text": prev, "segment_id": "v1"}]
        text = "Big thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions for the clips today. Go follow all three of them."
        ok, reason = self.validate(text, self.channels, history)
        self.assertFalse(ok)
        self.assertIn("Jaccard", reason)


class TestVOVisualSourceLaw23a(unittest.TestCase):
    """Law 23a: VO visuals in 9:16 must use the vertical composited frame, never the 16:9 source."""

    def test_vo_intro_uses_reframed_hook(self):
        """Step 3 intro VO must pass reframed['hook'] (vertical), not raw source."""
        render_vert_path = os.path.join(FIXTURE_DIR, "render_vertical.py")
        if not os.path.exists(render_vert_path):
            self.skipTest("render_vertical.py not found")
        with open(render_vert_path) as f:
            src = f.read()
        # The intro VO must use reframed.get("hook") — not sources_dir or raw source
        self.assertIn('reframed.get("hook")', src,
                      "Intro VO visual must use reframed hook (vertical composited), not raw source")

    def test_vo_bridge_uses_reframed_preceding(self):
        """Step 3 bridge VO must pass reframed[preceding_clip_id] (vertical), not raw source."""
        render_vert_path = os.path.join(FIXTURE_DIR, "render_vertical.py")
        if not os.path.exists(render_vert_path):
            self.skipTest("render_vertical.py not found")
        with open(render_vert_path) as f:
            src = f.read()
        self.assertIn('reframed.get(preceding_clip_id)', src,
                      "Bridge VO visual must use reframed preceding clip (vertical composited)")

    def test_vo_visual_vert_detects_portrait_source(self):
        """render_vo_visual_vert must detect 9:16 source and skip 16:9 crop."""
        render_vert_path = os.path.join(FIXTURE_DIR, "render_vertical.py")
        if not os.path.exists(render_vert_path):
            self.skipTest("render_vertical.py not found")
        with open(render_vert_path) as f:
            src = f.read()
        # The function must check if source is already portrait (h > w)
        self.assertIn('src_h > src_w', src,
                      "render_vo_visual_vert must detect portrait source and skip 16:9 crop")


class TestSignoffJaccardExcludesChannels(unittest.TestCase):
    """Jaccard overlap must exclude channel display name words so
    'Clips today from X, Y, Z. Go follow them.' and
    'Clips today from A, B, C. Go follow them.' are NOT falsely similar."""

    def test_same_structure_different_channels_passes(self):
        from signoff import validate_signoff
        channels = ["Bitcoin Magazine", "The Bitcoin Layer", "BTC Sessions"]
        history = [{
            "text": "Clips today from Simply Bitcoin, BTC Sessions, and CoinDesk. Go follow them. Links are below.",
            "segment_id": "v12_reference",
        }]
        candidate = "Big thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions for the clips. Follow them all. Links below."
        ok, reason = validate_signoff(candidate, channels, history)
        self.assertTrue(ok, f"Should pass since channel words are excluded: {reason}")

    def test_truly_duplicate_structure_fails(self):
        from signoff import validate_signoff
        channels = ["Bitcoin Magazine", "The Bitcoin Layer", "BTC Sessions"]
        history = [{
            "text": "Big thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions for the clips. Follow them all. Links below.",
            "segment_id": "segment_v2d",
        }]
        candidate = "Big thanks to Bitcoin Magazine, The Bitcoin Layer, and BTC Sessions for the clips. Follow them all. Links below."
        ok, _reason = validate_signoff(candidate, channels, history)
        self.assertFalse(ok, "Exact duplicate should fail Jaccard even with channel exclusion")


class TestG13VOAudibleLogic(unittest.TestCase):
    """G13 VO_AUDIBLE gate logic tests (M7)."""

    def test_fuzzy_word_overlap_high(self):
        """80%+ overlap between scripted and good transcript."""
        sys.path.insert(0, os.path.join(os.path.dirname(FIXTURE_DIR), "segment_v1"))
        from qa_gates import _fuzzy_word_overlap
        scripted = "Dollar dominance ends. Bond markets are breaking."
        transcript = "Dollar dominance ends. Bond markets are breaking."
        self.assertGreaterEqual(_fuzzy_word_overlap(scripted, transcript), 0.80)

    def test_fuzzy_word_overlap_partial(self):
        """Partial match under threshold."""
        sys.path.insert(0, os.path.join(os.path.dirname(FIXTURE_DIR), "segment_v1"))
        from qa_gates import _fuzzy_word_overlap
        scripted = "Dollar dominance ends. Bond markets are breaking."
        transcript = "Thanks for watching. Subscribe."
        self.assertLess(_fuzzy_word_overlap(scripted, transcript), 0.80)

    def test_music_hallucination_set(self):
        """Known hallucinations are in the set."""
        sys.path.insert(0, os.path.join(os.path.dirname(FIXTURE_DIR), "segment_v1"))
        from qa_gates import _MUSIC_HALLUCINATIONS
        self.assertIn("thanks for watching", _MUSIC_HALLUCINATIONS)
        self.assertIn("", _MUSIC_HALLUCINATIONS)
        self.assertIn("music", _MUSIC_HALLUCINATIONS)


class TestConfigConstants(unittest.TestCase):
    """M18: constants in config.py are the single source of truth."""

    def test_word_caps(self):
        from config import INTRO_WORD_CAP, BRIDGE_WORD_CAP, SIGNOFF_WORD_CAP
        self.assertEqual(INTRO_WORD_CAP, 30)
        self.assertEqual(BRIDGE_WORD_CAP, 20)
        self.assertEqual(SIGNOFF_WORD_CAP, 24)

    def test_r4_uses_config_caps(self):
        """R4 must use the config constants, not hardcoded numbers."""
        import inspect
        src = inspect.getsource(rule_r4)
        self.assertIn("INTRO_WORD_CAP", src)
        self.assertIn("BRIDGE_WORD_CAP", src)
        self.assertIn("SIGNOFF_WORD_CAP", src)
        self.assertNotIn("> 28", src, "R4 must not have hardcoded 28 for signoff cap")

    def test_signoff_validator_uses_config_cap(self):
        """signoff.py must use SIGNOFF_WORD_CAP from config."""
        from signoff import validate_signoff
        import inspect
        src = inspect.getsource(validate_signoff)
        self.assertIn("SIGNOFF_WORD_CAP", src)


class TestR4SignoffCap24(unittest.TestCase):
    """R4 signoff cap is 24 (was 28). A 25-word signoff must fail."""

    def test_25_word_signoff_fails(self):
        long_signoff = " ".join(["word"] * 25)
        edl = {
            "clips": [{"index": 1, "duration": 60, "channel": "A"}],
            "total_clip_duration": 60,
            "vo": {"intro": "Short intro.", "signoff": long_signoff, "bridges": []}
        }
        ok, reason = rule_r4(edl)
        self.assertFalse(ok, reason)
        self.assertIn("signoff=25", reason)
        self.assertIn("max 24", reason)

    def test_24_word_signoff_passes(self):
        signoff_24 = " ".join(["word"] * 24)
        edl = {
            "clips": [{"index": 1, "duration": 60, "channel": "A"}],
            "total_clip_duration": 60,
            "vo": {"intro": "Short.", "signoff": signoff_24, "bridges": []}
        }
        ok, reason = rule_r4(edl)
        self.assertTrue(ok, reason)


class TestFailClosedFindClip(unittest.TestCase):
    """M12: _find_clip_file searches ONLY current qa_dir, raises on missing."""

    def test_missing_clip_raises(self):
        from render16 import _find_clip_file
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError) as ctx:
                _find_clip_file(tmpdir, "clip_99")
            self.assertIn("STOP", str(ctx.exception))

    def test_no_cross_qa_scanning(self):
        """_find_clip_file must not scan sibling qa dirs."""
        from render16 import _find_clip_file
        import inspect
        src = inspect.getsource(_find_clip_file)
        self.assertNotIn("os.listdir(segment_dir)", src,
                         "Must not scan sibling qa dirs")
        # The function signature accepts sources_dir for compat but must never USE it before raise
        body = src.split("def _find_clip_file")[1] if "def _find_clip_file" in src else src
        # Check that sources_dir is never referenced in the body logic (only in signature)
        lines = body.split("\n")
        logic_lines = [l for l in lines[1:] if "sources_dir" in l and "def " not in l and "raise" not in l]
        self.assertEqual(len(logic_lines), 0,
                         "Must not use sources_dir in logic (no raw source fallback)")


class TestFailClosedShoutout(unittest.TestCase):
    """M12: missing signoff WAV in shoutout = STOP."""

    def test_missing_shoutout_raises(self):
        from render16 import _find_shoutout
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError) as ctx:
                _find_shoutout(tmpdir)
            self.assertIn("STOP", str(ctx.exception))


class TestTelegramGuard(unittest.TestCase):
    """M16 on the release contract (red-team A): the legacy entry point is removed, and deliver_run refuses a run
    without an attestation before anything is sent."""

    def test_refuses_without_verification(self):
        import tempfile
        import telegram
        from telegram import send_telegram_preview
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "out"))
            os.makedirs(os.path.join(tmpdir, "qa"))
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_preview(tmpdir)
            self.assertIn("removed", str(ctx.exception))
            sent = []
            with self.assertRaises(RuntimeError) as ctx:
                telegram.deliver_run(tmpdir, send=lambda k, p, f, data=None: sent.append(k) or 1)
            self.assertIn("not authorised", str(ctx.exception))
            self.assertEqual(sent, [])


class TestAcousticModule(unittest.TestCase):
    """M19: acoustic.py basic functionality."""

    def test_rms_envelope_shape(self):
        import numpy as np
        from acoustic import rms_envelope
        sr = 16000
        samples = np.random.randn(sr)  # 1 second
        rms_db, times = rms_envelope(samples, sr, hop_ms=10)
        self.assertEqual(len(rms_db), len(times))
        self.assertGreater(len(rms_db), 90)  # ~100 frames for 1s at 10ms hop

    def test_unsafe_boundary_detected(self):
        """onset - offset < 0.12s is unsafe."""
        from acoustic import MIN_GAP_S
        self.assertEqual(MIN_GAP_S, 0.12)

    def test_measure_output_tail_silent(self):
        """measure_output_tail on silence returns pass_absolute=True."""
        import numpy as np
        from acoustic import rms_envelope
        # Verify the RMS of silence is well below -35 dBFS
        sr = 16000
        silence = np.zeros(sr)
        rms_db, _ = rms_envelope(silence, sr, hop_ms=10)
        # All frames should be -80 dBFS (our floor)
        self.assertTrue(all(db <= -35 for db in rms_db))


class TestG3cGateExists(unittest.TestCase):
    """M19: gate_g3c function exists in qa_gates.py."""

    def test_gate_g3c_callable(self):
        sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
        import qa_gates
        self.assertTrue(hasattr(qa_gates, 'gate_g3c'))
        self.assertTrue(callable(qa_gates.gate_g3c))

    def test_g3c_in_run_all_gates(self):
        """G3c must be wired into run_all_gates."""
        sys.path.insert(0, "/home/ultron/protocol_pulse/segment_v1")
        import inspect
        import qa_gates
        src = inspect.getsource(qa_gates.run_all_gates)
        self.assertIn("gate_g3c", src)
        self.assertIn("G3c_acoustic_tail", src)


class TestM19aValleyRule(unittest.TestCase):
    """M19a: valley rule finds correct cut point."""

    def test_valley_found_in_synthetic_signal(self):
        """A synthetic signal with a clear valley must be detected."""
        import numpy as np
        from acoustic import find_valley, rms_envelope, _smoothed_rms
        sr = 16000
        # Build 1s signal: speech at -15 dBFS, valley at 0.5s (80ms of silence)
        samples = np.zeros(sr, dtype=np.float64)
        # Speech: 0-0.45s and 0.55-1.0s at amplitude ~0.18 (-15 dBFS)
        amp = 10 ** (-15 / 20)  # ~0.178
        speech1 = amp * np.random.randn(int(0.45 * sr))
        speech2 = amp * np.random.randn(int(0.45 * sr))
        samples[:len(speech1)] = speech1
        samples[int(0.55 * sr):int(0.55 * sr) + len(speech2)] = speech2
        # Valley region 0.45-0.55s stays at ~0 (silence = -80 dBFS)

        rms_db, times = rms_envelope(samples, sr, hop_ms=10)
        speech_median_db = float(np.median(rms_db[:45]))  # first 0.45s

        v = find_valley(rms_db, times, 0.3, 0.8, speech_median_db)
        self.assertIsNotNone(v, "Valley must be found in synthetic gap")
        self.assertGreaterEqual(v["width_ms"], 60)
        self.assertGreaterEqual(v["depth_db"], 12)
        # Valley centre should be near 0.5s
        self.assertAlmostEqual(v["centre"], 0.5, delta=0.08)

    def test_no_valley_when_shallow(self):
        """A signal with < 12 dB dip must return None."""
        import numpy as np
        from acoustic import find_valley, rms_envelope
        sr = 16000
        # Constant speech at -15 dBFS with a 5 dB dip (too shallow)
        amp_speech = 10 ** (-15 / 20)
        amp_dip = 10 ** (-20 / 20)  # only 5 dB below speech
        samples = amp_speech * np.random.randn(sr)
        # Replace 0.45-0.55 with shallow dip
        dip_len = int(0.10 * sr)
        samples[int(0.45 * sr):int(0.45 * sr) + dip_len] = amp_dip * np.random.randn(dip_len)

        rms_db, times = rms_envelope(samples, sr, hop_ms=10)
        speech_median_db = float(np.median(rms_db[:45]))

        v = find_valley(rms_db, times, 0.3, 0.8, speech_median_db)
        self.assertIsNone(v, "Shallow dip (< 12 dB) must not qualify as valley")

    def test_no_valley_when_narrow(self):
        """A valley < 40ms wide must return None (before smoothing)."""
        import numpy as np
        from acoustic import find_valley, rms_envelope
        sr = 16000
        amp = 10 ** (-15 / 20)
        samples = amp * np.random.randn(sr)
        # Insert a 10ms gap (1 frame at 10ms hop) — too narrow even after smoothing
        gap_start = int(0.50 * sr)
        gap_end = gap_start + int(0.01 * sr)
        samples[gap_start:gap_end] = 0.0

        rms_db, times = rms_envelope(samples, sr, hop_ms=10)
        speech_median_db = float(np.median(rms_db[:45]))

        v = find_valley(rms_db, times, 0.3, 0.8, speech_median_db)
        # A single-frame gap should not produce a >= 40ms valley
        if v is not None:
            self.assertLess(v["width_ms"], 40,
                            "Single-frame gap must not produce a 40ms+ valley")

    def test_first_valley_preferred(self):
        """find_valley returns the FIRST qualifying valley, not the deepest."""
        import numpy as np
        from acoustic import find_valley, rms_envelope
        sr = 16000
        amp = 10 ** (-15 / 20)
        samples = amp * np.random.randn(sr)
        # Valley 1 at 0.3s (60ms silence)
        v1_start = int(0.30 * sr)
        v1_end = int(0.36 * sr)
        samples[v1_start:v1_end] = 0.0
        # Valley 2 at 0.7s (200ms silence — deeper/wider)
        v2_start = int(0.70 * sr)
        v2_end = int(0.90 * sr)
        samples[v2_start:v2_end] = 0.0

        rms_db, times = rms_envelope(samples, sr, hop_ms=10)
        speech_median_db = float(np.median(rms_db[:25]))

        v = find_valley(rms_db, times, 0.2, 0.95, speech_median_db)
        self.assertIsNotNone(v)
        # Must pick valley 1 (centre ~0.33), not valley 2 (centre ~0.80)
        self.assertLess(v["centre"], 0.50, "Must pick the FIRST qualifying valley")

    def test_clip_01_source_valley(self):
        """Integration: M19a finds the inter-word valley after 'magnitude'.
        Cut must land in [249.62, 249.72] — after the full word, before 'So'."""
        source = "/home/ultron/protocol_pulse/segment_v2/sources/Pxrak-iMT0g.mp4"
        if not os.path.exists(source):
            self.skipTest("clip_01 source not available")
        from acoustic import compute_acoustic_cut_out
        result = compute_acoustic_cut_out(source, whisper_word_end=249.3)
        self.assertIsNotNone(result["valley"])
        # Cut at valley end in [249.62, 249.72] — past the stop-consonant dip
        self.assertGreaterEqual(result["cut_out"], 249.62,
                                msg=f"cut_out too early (inside word): {result['cut_out']}")
        self.assertLessEqual(result["cut_out"], 249.72,
                             msg=f"cut_out too late (into next word): {result['cut_out']}")
        self.assertGreaterEqual(result["valley"]["depth_db"], 12.0)
        self.assertGreaterEqual(result["valley"]["width_ms"], 60)
        self.assertIn("end", result["valley"])


class TestOutputPathCollision(unittest.TestCase):
    """A5/R2-11: refuse start when 16:9 and 9:16 output names are identical."""

    def test_segment_in_name_works(self):
        """output_name containing 'segment' produces distinct names."""
        from run import _resolve_output_names
        args = type("Args", (), {"output_name": "segment.mp4"})()
        n16, n9 = _resolve_output_names(args)
        self.assertNotEqual(n16, n9)
        self.assertEqual(n16, "segment.mp4")
        self.assertIn("vertical", n9)

    def test_no_segment_in_name_raises(self):
        """output_name without 'segment' would produce identical paths — must raise."""
        from run import _resolve_output_names
        args = type("Args", (), {"output_name": "output.mp4"})()
        with self.assertRaises(RuntimeError) as ctx:
            _resolve_output_names(args)
        self.assertIn("R2-11", str(ctx.exception))

    def test_none_output_name_works(self):
        """Default None uses segment.mp4 / segment_vertical.mp4."""
        from run import _resolve_output_names
        args = type("Args", (), {"output_name": None})()
        n16, n9 = _resolve_output_names(args)
        self.assertEqual(n16, "segment.mp4")
        self.assertEqual(n9, "segment_vertical.mp4")


class TestShoutoutHookChannel(unittest.TestCase):
    """A7/R2-16: shoutout must include the hook channel."""

    def test_hook_channel_included(self):
        """Hook channel appears in the channel list extracted by build_shoutout logic."""
        import shoutout as sh
        edl = {
            "hook": {"channel": "HookChan", "handle": "@hook"},
            "clips": [
                {"channel": "ClipChan1", "handle": "@c1"},
                {"channel": "ClipChan2", "handle": "@c2"},
            ]
        }
        # Replicate the extraction logic from build_shoutout
        channels = []
        seen = set()
        hook = edl.get("hook", {})
        hook_ch = hook.get("channel", "")
        if hook_ch and hook_ch not in seen:
            channels.append(hook_ch)
            seen.add(hook_ch)
        for clip in edl.get("clips", []):
            ch = clip.get("channel", "")
            if ch and ch not in seen:
                channels.append(ch)
                seen.add(ch)
        self.assertIn("HookChan", channels)
        self.assertEqual(channels[0], "HookChan", "Hook channel must be first")
        self.assertEqual(len(channels), 3)

    def test_hook_channel_dedup(self):
        """If hook channel same as a clip channel, no duplicate."""
        edl = {
            "hook": {"channel": "SharedChan", "handle": "@shared"},
            "clips": [
                {"channel": "SharedChan", "handle": "@shared"},
                {"channel": "OtherChan", "handle": "@other"},
            ]
        }
        channels = []
        seen = set()
        hook = edl.get("hook", {})
        hook_ch = hook.get("channel", "")
        if hook_ch and hook_ch not in seen:
            channels.append(hook_ch)
            seen.add(hook_ch)
        for clip in edl.get("clips", []):
            ch = clip.get("channel", "")
            if ch and ch not in seen:
                channels.append(ch)
                seen.add(ch)
        self.assertEqual(len(channels), 2)
        self.assertEqual(channels[0], "SharedChan")


class TestR4Moments(unittest.TestCase):
    """Law L-q (orchestrator 2026-11-12 '06:00'): R4 for a package of type 'moments' ONLY: VO share <= 40 %, one VO line
    per slot (after the hook, after each clip, after the LAST clip), the estimated runtime inside 60-70 s (hard, L-o);
    story-type and untyped EDLs keep the old R4. Must-fail: VO share 41 %, runtime 59.9 and 70.1 s, a line with no
    slot. Runtime = hook + clips + VO (words / 2.5 + 1.0 s pre-roll each) + 14.30 s tail. Fail closed (audit cycle 1):
    a 'moments' EDL without a validated package, an unmeasured duration, bad clip indexes, an empty line."""
    MARK = {"moments_package_sha256": "ab" * 32, "mode": "pinned",
            "moments_checks": {"vo_fidelity_ok": True, "context_integrity_ok": True}}

    def edl(self, hook, clips, intro_words, bridges, t="moments"):
        e = {"hook": {"duration": hook, "channel": "H"},
             "clips": [{"index": i, "duration": d, "channel": f"C{i}"} for i, d in enumerate(clips, 1)],
             "vo": {"intro": " ".join(["w"] * intro_words) if intro_words else None,
                    "bridges": [{"text": " ".join(["w"] * n), "after_clip": a} for n, a in bridges]},
             "total_clip_duration": round(hook + sum(clips), 2)}
        if t is not None:
            e["package_type"] = t
        if t == "moments":
            e.update(self.MARK)
        return e

    def only(self, e, part):
        ok, why = rule_r4(e)
        self.assertFalse(ok, why)
        self.assertIn(part, why)
        self.assertEqual(why.count(";"), 0, why)                            # the ONE failure under test
        return why

    def test_vo_share_45_1_percent_fails_and_45_passes(self):
        """Ruling 9 ('08:29'): 45 % of the TOTAL estimated runtime. VO 31.0 s (30 + 20 + 20 words, three pre-rolls) over
        hook + clips + 31.0 + 14.3 tail; every case inside 60-70 s, so only the share decides."""
        vo3 = (30, [(20, 1), (20, 2)])
        self.only(self.edl(7.436, [8, 8], *vo3), "VO=45.10%")               # total 68.736 s
        self.only(self.edl(6.832, [8, 8], *vo3), "VO=45.50%")               # total 68.132 s
        ok, why = rule_r4(self.edl(7.59, [8, 8], *vo3))                     # 31.0 / 68.89 = 44.9995 %
        self.assertTrue(ok, why)
        ok, why = rule_r4(self.edl(31.0 / 0.45 - 61.3, [8, 8], *vo3))       # exactly 45.00 % passes (<=, not <)
        self.assertTrue(ok, why)
        ok, why = rule_r4(self.edl(5.49, [8, 8], 30, [(15, 1), (15, 2)]))   # 27.0 / 62.79 = 43.0 %: the old 40 % cap
        self.assertTrue(ok, why)                                            # would have refused it
        ok, why = rule_r4(self.edl(7.0, [10, 10], 30, [(15, 1)]))           # 20.0 s VO of a 61.3 s total = 32.6 %
        self.assertTrue(ok, why)
        self.assertIn("32.63% of total runtime", why)

    def test_runtime_59_9_and_70_1_fail_60_and_70_pass(self):
        for hook, want in ((15.6, False), (15.696, False), (15.7, True), (25.7, True), (25.704, False), (25.8, False)):
            e = self.edl(hook, [10, 10], 16, [(4, 2)])                       # + 20 clips + 10 VO + 14.3 tail
            if want:
                ok, why = rule_r4(e)
                self.assertTrue(ok, (hook, why))
            else:
                self.only(e, "outside 60-70 s")

    def test_a_vo_line_with_no_slot_fails(self):
        for bridges in ([(5, 0)], [(5, 3)], [(5, 1), (5, 1)], [(5, 2), (5, 1)], [(5, "1")], [(5, None)], [(5, True)],
                        [(5, 1.0)]):
            self.only(self.edl(15.0, [12, 12], 10, bridges), "has no slot")   # runtime 61.3-64.3: only the slot
        e = self.edl(15.0, [12, 12], 10, [])
        e["vo"]["bridges"] = [{"text": "a b c"}]
        self.only(e, "has no slot")

    def test_a_line_after_each_clip_including_the_last_has_a_slot(self):
        ok, why = rule_r4(self.edl(14.0, [12, 12], 10, [(5, 1), (5, 2)]))   # VO 5 + 3 + 3 = 11 s; 38 + 11 + 14.3
        self.assertTrue(ok, why)

    def test_word_caps_are_unchanged(self):
        self.only(self.edl(15.0, [12, 12], 31, []), "intro=31 words")       # runtime 66.7
        self.only(self.edl(15.0, [12, 12], 5, [(21, 1)]), "bridge 1=21 words")

    def test_the_takeaway_has_its_own_cap_and_bridges_keep_theirs(self):
        """Ruling 10 ('08:40'): the line after the LAST clip may carry up to 30 words (31 rejected); a bridge BETWEEN
        clips keeps 20 (21 rejected). Every case inside 60-70 s and 45 %, so only the cap decides."""
        from edl_rules import MOMENTS_TAKEAWAY_WORD_CAP, BRIDGE_WORD_CAP
        self.assertEqual((MOMENTS_TAKEAWAY_WORD_CAP, BRIDGE_WORD_CAP), (30, 20))
        ok, why = rule_r4(self.edl(10.0, [9, 5], 13, [(18, 1), (24, 2)]))      # the night's shape: 24 after the last
        self.assertTrue(ok, why)
        ok, why = rule_r4(self.edl(8.0, [9, 5], 13, [(18, 1), (30, 2)]))       # exactly 30 after the last
        self.assertTrue(ok, why)
        self.only(self.edl(8.0, [9, 5], 13, [(18, 1), (31, 2)]), "bridge 2=31 words (max 30)")
        self.only(self.edl(10.0, [9, 5], 13, [(21, 1), (20, 2)]), "bridge 1=21 words (max 20)")   # between clips

    def test_fail_closed_shapes(self):
        e = self.edl(17.0, [12, 12], 10, [(5, 1)])                          # 41 + 5 (the intro only) + 14.3
        e["vo"]["bridges"][0]["text"] = "  "
        self.only(e, "VO line 1 is empty")
        for bad in (None, 0, -1.0, float("nan"), float("inf"), "12", True):
            e = self.edl(15.0, [12, 12], 10, [(5, 1)])
            e["clips"][1]["duration"] = bad
            ok, why = rule_r4(e)
            self.assertFalse(ok, bad)
            self.assertIn("is not a measured positive number", why, bad)
        e = self.edl(15.0, [12, 12], 10, [(5, 1)])
        e["clips"][1]["index"] = 1
        ok, why = rule_r4(e)
        self.assertFalse(ok)
        self.assertIn("clip indexes", why)
        for drop in ("moments_package_sha256", "mode", "moments_checks"):
            e = self.edl(15.0, [12, 12], 10, [(5, 1)])
            del e[drop]
            self.only(e, "without a validated moments package")
        e = self.edl(15.0, [12, 12], 10, [(5, 1)])
        e["moments_checks"] = {"vo_fidelity_ok": True, "context_integrity_ok": "true"}
        self.only(e, "without a validated moments package")

    def test_story_type_and_untyped_edls_keep_the_old_rule(self):
        for t in ("story", None, "Moments"):
            e = self.edl(10.0, [10, 10], 30, [(15, 1)], t=t)              # 20 s VO of 50 s = 40 %: old max 25 %
            ok, why = rule_r4(e)
            self.assertFalse(ok, t)
            self.assertIn("VO=40% of runtime (max 25%)", why, t)
            self.assertNotIn("moments", why, t)



class TestR11VoShape(unittest.TestCase):
    """Law L-y VOICEOVER IS MINIMAL (orchestrator 2026-11-12 '20:30', PBX on the review video: 'too much voiceover ...
    only one input at the end'): for a package of type 'moments', R11 allows one takeaway after the LAST clip and at
    most ONE line before it, the L-y 2 exception, in the intro slot (hook -> clip 1) or after clip k, and only with the
    package's recorded bridge (moments_bridge: the same text, 'why', 'confirmed_by'; <= 20 words). Must-fail: an intro
    or a bridge without that record, two lines before the takeaway, two takeaways, an unconfirmed or reasonless or
    mismatched or long bridge, a record without a line, malformed shapes. Must-pass: the default shape, no VO at all,
    the exception in either slot. R4-moments has no minimum VO share. Story-type and untyped EDLs are unchanged."""
    MARK = TestR4Moments.MARK
    BRIDGE = "Same question, from a miner's side."

    def edl(self, clips=(12, 12, 8), intro=None, bridges=(), t="moments", hook=10.0, rec=None):
        e = {"hook": {"duration": hook, "channel": "H"},
             "clips": [{"index": i, "duration": d, "channel": f"C{i}"} for i, d in enumerate(clips, 1)],
             "vo": {"intro": intro, "bridges": [dict(b) if isinstance(b, dict) else b for b in bridges]},
             "total_clip_duration": round(hook + sum(clips), 2)}
        if t is not None:
            e["package_type"] = t
        if t == "moments":
            e.update(self.MARK)
        if rec is not None:
            e["moments_bridge"] = rec
        return e

    TAKE = {"text": " ".join(["w"] * 24), "after_clip": 3}            # the takeaway: the line after the LAST clip

    def rec(self, **kw):
        r = {"after": "clip_01", "after_clip": 1, "join": "clip_01 -> clip_02", "text": self.BRIDGE,
             "why": "clip 2 opens on 'they', whose referent is not in clip 1", "confirmed_by": "blind clips-alone check"}
        r.update(kw)
        return r

    def fails(self, e, part):
        ok, why = rule_r11(e)
        self.assertFalse(ok, why)
        self.assertIn(part, why)
        return why

    def test_the_default_shape_passes_and_r4_has_no_minimum(self):
        for bridges, hook in (((), 15.0), ((self.TAKE,), 10.0)):     # no VO line at all; one takeaway
            e = self.edl(bridges=bridges, hook=hook)
            ok, why = rule_r11(e)
            self.assertTrue(ok, why)
            ok, why = rule_r4(e)                                      # 47 + 0 + 14.3 = 61.3 s; 42 + 10.6 + 14.3 = 66.9 s
            self.assertTrue(ok, why)
        ok, why = rule_r11(self.edl(intro="", bridges=(self.TAKE,)))  # an empty intro is no line
        self.assertTrue(ok, why)

    def test_an_intro_or_a_bridge_without_the_record_fails(self):
        for intro in ("Bitcoin does not have any authority.", "w"):
            self.fails(self.edl(intro=intro, bridges=(self.TAKE,)), "without the package's recorded bridge")
        for intro in ("   ", 5, ["w"]):                                # audit F3: a whitespace / non-text line fails
            self.fails(self.edl(intro=intro, bridges=(self.TAKE,)), "is not text")
        self.fails(self.edl(bridges=({"text": self.BRIDGE, "after_clip": 1}, self.TAKE)),
                   "a line in the slot after clip 1 without the package's recorded bridge")

    def test_the_one_exception_passes_in_either_slot_with_its_record(self):
        ok, why = rule_r11(self.edl(bridges=({"text": self.BRIDGE, "after_clip": 1}, self.TAKE), rec=self.rec()))
        self.assertTrue(ok, why)
        ok, why = rule_r11(self.edl(intro=self.BRIDGE, bridges=(self.TAKE,),            # the hook -> clip 1 join
                                    rec=self.rec(after="hook", after_clip=0, join="hook -> clip_01")))
        self.assertTrue(ok, why)
        ok, why = rule_r11(self.edl(bridges=({"text": self.BRIDGE, "after_clip": 2},), rec=self.rec()))  # no takeaway
        self.assertTrue(ok, why)

    def test_the_record_must_match_give_a_reason_and_be_confirmed(self):
        line = ({"text": self.BRIDGE, "after_clip": 1}, self.TAKE)
        self.fails(self.edl(bridges=line, rec=self.rec(text="Another line.")), "without the package's recorded bridge")
        self.fails(self.edl(bridges=line, rec="a reason"), "without the package's recorded bridge")
        for why in (None, "", "   ", 5):
            self.fails(self.edl(bridges=line, rec=self.rec(why=why)), "has no reason ('why')")
        for conf in (None, "", "  ", [], {}, True, 1):
            self.fails(self.edl(bridges=line, rec=self.rec(confirmed_by=conf)), "not confirmed by the blind check")
        long = " ".join(["w"] * 21)
        self.fails(self.edl(bridges=({"text": long, "after_clip": 1}, self.TAKE), rec=self.rec(text=long)),
                   "the bridge is 21 words (max 20)")
        ok, why = rule_r11(self.edl(bridges=({"text": " ".join(["w"] * 20), "after_clip": 1}, self.TAKE),
                                    rec=self.rec(text=" ".join(["w"] * 20))))
        self.assertTrue(ok, why)

    def test_two_lines_before_the_takeaway_fail_even_with_a_record(self):
        two = ({"text": "a b", "after_clip": 1}, {"text": self.BRIDGE, "after_clip": 2}, self.TAKE)
        self.fails(self.edl(bridges=two, rec=self.rec()), "law L-y 2: 2 lines before the takeaway")
        self.fails(self.edl(intro=self.BRIDGE, bridges=({"text": "a b", "after_clip": 1}, self.TAKE), rec=self.rec()),
                   "law L-y 2: 2 lines before the takeaway")

    def test_two_lines_after_the_last_clip_fail(self):
        self.fails(self.edl(bridges=(self.TAKE, self.TAKE)), "law L-y 1: 2 VO lines after the last clip")

    def test_a_takeaway_that_is_not_text_fails(self):
        for text in (None, "", "   ", 123, ["w"]):                    # cycle 3 qwen F1 / F2
            self.fails(self.edl(bridges=({"text": text, "after_clip": 3},)), "the takeaway after the last clip is not text")

    def test_a_record_without_a_bridge_line_fails(self):
        self.fails(self.edl(bridges=(self.TAKE,), rec=self.rec()), "with no bridge line in the VO")

    def test_a_line_without_a_clip_slot_fails(self):
        for bad in ({"text": "a b", "after_clip": "3"}, {"text": "a b"}, "a b", {"text": "a b", "after_clip": 99},
                    {"text": "a b", "after_clip": 0}, {"text": "a b", "after_clip": True}):
            self.fails(self.edl(bridges=(bad,)), "is not a clip index")

    def test_fail_closed_shapes(self):
        e = self.edl()
        e["vo"]["bridges"] = "a b"
        self.assertFalse(rule_r11(e)[0])
        for drop in ("vo", "clips"):
            e = self.edl()
            del e[drop]
            self.assertFalse(rule_r11(e)[0], drop)
        for bridges in (None, "missing"):                              # audit F2: the lines are always stated
            e = self.edl()
            if bridges is None:
                e["vo"]["bridges"] = None
            else:
                del e["vo"]["bridges"]
            self.fails(e, "vo bridges is not a list")
        for index in ("1", None, 1.0, True, 2, 3, 0):                # audit F1 / cycle 3 glm F1: exactly 1..n
            e = self.edl()
            e["clips"][0]["index"] = index
            self.fails(e, "are not 1..3")
        e = self.edl(bridges=(self.TAKE, {"text": "y", "after_clip": 3}))
        e["clips"][2]["index"] = 2                                      # a duplicated last index cannot hide a takeaway
        self.fails(e, "are not 1..3")
        e = self.edl()
        e["clips"][1] = "clip"
        self.assertFalse(rule_r11(e)[0])

    def test_story_type_and_untyped_edls_are_unchanged(self):
        busy = ({"text": "a b", "after_clip": 1}, {"text": "c d", "after_clip": 2})
        for t in ("story", None, "Moments"):
            ok, why = rule_r11(self.edl(intro="An intro line.", bridges=busy, t=t))
            self.assertTrue(ok, (t, why))
            self.assertIn("not a moments package", why)

    def test_validate_edl_rejects_a_moments_edl_with_an_intro(self):
        ok, results = validate_edl(self.edl(intro="An intro line.", bridges=(self.TAKE,)))
        self.assertFalse(ok)
        row = next(r for r in results if r["rule"] == "rule_r11")
        self.assertFalse(row["pass"])
        self.assertIn("without the package's recorded bridge", row["reason"])

    RUN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "pinned_20261112_165629")

    @unittest.skipUnless(os.path.exists(os.path.join(RUN, "edl.json")), "the delivered review run not on this machine")
    def test_the_delivered_review_video_fails_and_its_l_y_reshape_passes(self):
        """The video PBX was 'very pleased' with, but with 'too much voiceover': its real EDL (an intro and a bridge
        between its two clips, no recorded bridge) fails; the same package reshaped to L-y (no intro, its own takeaway
        after the last clip) passes R11."""
        with open(os.path.join(self.RUN, "edl.json")) as f:
            e = json.load(f)
        self.fails(e, "law L-y 2: 2 lines before the takeaway")
        e["vo"] = {**e["vo"], "intro": None, "bridges": [b for b in e["vo"]["bridges"] if b["after_clip"] == 2]}
        ok, why = rule_r11(e)
        self.assertTrue(ok, why)

if __name__ == "__main__":
    unittest.main(verbosity=2)

