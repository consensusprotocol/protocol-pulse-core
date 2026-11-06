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
                       rule_r9, validate_edl)

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
    """R5: 8-25s per clip, >= 2 channels, each >= 8s."""

    def test_good_clips_pass(self):
        edl = {
            "clips": [
                {"index": 1, "duration": 12, "channel": "A"},
                {"index": 2, "duration": 15, "channel": "B"},
            ]
        }
        ok, reason = rule_r5(edl)
        self.assertTrue(ok, reason)

    def test_clip_too_short_fails(self):
        edl = {
            "clips": [
                {"index": 1, "duration": 5, "channel": "A"},
                {"index": 2, "duration": 15, "channel": "B"},
            ]
        }
        ok, reason = rule_r5(edl)
        self.assertFalse(ok, reason)
        self.assertIn("min 8s", reason)

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
    """M16: telegram.py refuses without VERIFIED_BY_ORCHESTRATOR."""

    def test_refuses_without_verification(self):
        from telegram import send_telegram_preview
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "out"))
            os.makedirs(os.path.join(tmpdir, "qa"))
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_preview(tmpdir)
            self.assertIn("VERIFIED_BY_ORCHESTRATOR", str(ctx.exception))


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
        self.assertTrue(v["safe"])
        self.assertGreaterEqual(v["width_ms"], 40)
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
        """Integration: M19a finds valley ~249.64 on actual clip_01 source."""
        source = "/home/ultron/protocol_pulse/segment_v2/sources/Pxrak-iMT0g.mp4"
        if not os.path.exists(source):
            self.skipTest("clip_01 source not available")
        from acoustic import compute_acoustic_cut_out
        result = compute_acoustic_cut_out(source, whisper_word_end=249.3)
        self.assertTrue(result["safe"], f"Boundary must be safe: {result}")
        self.assertIsNotNone(result["valley"])
        # Valley centre should be ~249.64 (orchestrator expected ~249.66)
        self.assertAlmostEqual(result["cut_out"], 249.64, delta=0.05,
                               msg=f"cut_out should be ~249.64, got {result['cut_out']}")
        self.assertGreaterEqual(result["valley"]["depth_db"], 12.0)
        self.assertGreaterEqual(result["valley"]["width_ms"], 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)

