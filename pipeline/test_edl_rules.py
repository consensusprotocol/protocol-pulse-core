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


if __name__ == "__main__":
    unittest.main(verbosity=2)
