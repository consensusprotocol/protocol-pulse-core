#!/usr/bin/env python3
"""RULING 148 (1) (orchestrator 2026-11-18 '09:38'): "a line-up of 30.0 s or more may seal; between 30.0 and 36.7 s it
carries the flag 'This video runs NN seconds, shorter than usual.' ... Under 30 s still refused." The builder seals that
as a FLAGGED gates.runtime row. The render:
G5        a moments run whose sealed pin carries that row is accepted from 44.3 s (the 30.0 s line-up floor + the format's
          14.3 s tail) to 72 s; every other run keeps ruling 12's 58-72 s; a spotlight keeps 28-50 s
R4        its runtime finding adds no second sentence where the pin flags it; elsewhere it is named as the length, never
          as the voiceover; a voiceover finding keeps its sentence"""
import json
import os
import shutil
import sys
import tempfile
import types
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
sys.path.insert(0, os.path.join(REPO, "segment_v1"))
import edl_rules  # noqa: E402
import qa_gates  # noqa: E402
import run_fresh as RF  # noqa: E402

SENT = "This video runs 57 seconds, shorter than usual."
FLAGGED = {"status": "FLAGGED", "flags": [SENT], "replayed": False, "runtime_s_estimate": 56.8}
VOICE = "The voiceover runs over its length limit."
LENGTH = "The video's estimated length is outside the usual 60 to 70 seconds."
RUNTIME = "estimated runtime 56.800 s outside 60-70 s (hook + clips 33.89 + VO 8.61 + tail 14.3)"


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="r148_")
        self.addCleanup(shutil.rmtree, self.root, True)

    def run_dir(self, row=None, raw=None, edl=None):
        d = tempfile.mkdtemp(dir=self.root)
        with open(os.path.join(d, "edl.json"), "w") as f:
            json.dump({"package_type": "moments"} if edl is None else edl, f)
        if raw is None and row is not None:
            raw = json.dumps({"pin": {"moments_package": {"gates": {"runtime": row, "hook_onset": {"status": "PASS"}}}}})
        if raw is not None:
            with open(os.path.join(d, "PINNED_DECISION.json"), "w") as f:
                f.write(raw)
        return d


class TestTheSealedRow(Base):
    def test_a_flagged_row_is_read(self):
        self.assertEqual(edl_rules.flagged_runtime_row(self.run_dir(FLAGGED)), FLAGGED)

    def test_anything_else_reads_none(self):
        for label, kw in (("PASS", {"row": {"status": "PASS", "replayed": False}}),
                          ("replayed", {"row": {**FLAGGED, "replayed": True}}),
                          ("replay unknown", {"row": {k: v for k, v in FLAGGED.items() if k != "replayed"}}),
                          ("no flags", {"row": {**FLAGGED, "flags": []}}),
                          ("a blank flag", {"row": {**FLAGGED, "flags": [" "]}}),
                          ("no pinned decision", {}),
                          ("unreadable", {"raw": "{not json"}),
                          ("gates not an object", {"raw": json.dumps({"pin": {"moments_package": {"gates": ["x"]}}})}),
                          ("no pin", {"raw": json.dumps({"mode": "pinned"})}),
                          ("a row that is a string", {"row": "FLAGGED"}),          # audit 115 c1 (qwen F1)
                          ("a row that is None", {"raw": json.dumps({"pin": {"moments_package": {"gates": {"runtime": None}}}})})):
            with self.subTest(label):
                self.assertIsNone(edl_rules.flagged_runtime_row(self.run_dir(**kw)))


class TestG5Window(Base):
    NORMAL = ((58.0, 72.0), (60.0, 70.0))

    def window(self, d):
        return qa_gates.g5_window(os.path.join(d, "edl.json"))

    def test_a_flagged_runtime_accepts_from_44_3_s(self):
        (lo, hi), target = self.window(self.run_dir(FLAGGED))
        self.assertAlmostEqual(lo, 44.3, places=6)
        self.assertEqual((hi, target), (72.0, (60.0, 70.0)))
        self.assertTrue(lo <= 56.8 <= hi)                       # this morning's 33.89 s line-up, about 57 s
        self.assertFalse(lo <= 44.0 <= hi)                       # under a 30 s line-up's final: still refused

    def test_every_other_run_keeps_58_to_72_s(self):
        for label, d in (("no row", self.run_dir()),
                         ("a PASS row", self.run_dir({"status": "PASS", "replayed": False})),
                         ("a replayed row", self.run_dir({**FLAGGED, "replayed": True})),
                         ("not a moments EDL", self.run_dir(FLAGGED, edl={"package_type": "story"}))):
            with self.subTest(label):
                self.assertEqual(self.window(d), self.NORMAL)

    def test_a_spotlight_keeps_its_own_window(self):
        d = self.run_dir(FLAGGED, edl={"package_type": "moments", "package_shape": "spotlight"})
        self.assertEqual(self.window(d), (qa_gates.G5_SPOTLIGHT_S, qa_gates.G5_SPOTLIGHT_S))


class TestR4Sentences(Base):
    def reason(self, *f):
        return "R4 FAIL (moments): " + "; ".join(f)

    def test_a_flagged_short_runtime_adds_no_sentence(self):
        self.assertEqual(RF.r4_sentences(self.run_dir(FLAGGED), self.reason(RUNTIME)), [])

    def test_an_unflagged_runtime_is_named_as_the_length(self):
        self.assertEqual(RF.r4_sentences(self.run_dir(), self.reason(RUNTIME)), [LENGTH])

    def test_a_voiceover_finding_keeps_its_sentence(self):
        vo = "VO=46.10% of total runtime (max 45%, moments)"
        slot = "VO line 2 has no slot (after_clip 5: one line after each clip index)"
        for label, d, reason, want in (
                ("share alone", self.run_dir(), self.reason(vo), [VOICE]),
                ("share + flagged runtime", self.run_dir(FLAGGED), self.reason(vo, RUNTIME), [VOICE]),
                ("slot + flagged runtime", self.run_dir(FLAGGED), self.reason(slot, RUNTIME), [VOICE]),
                ("share + unflagged runtime", self.run_dir(), self.reason(vo, RUNTIME), [VOICE, LENGTH]),
                ("a story pin's R4", self.run_dir(), "VO=31% of runtime (max 25%)", [VOICE])):
            with self.subTest(label):
                self.assertEqual(RF.r4_sentences(d, reason), want)

    def test_validate_flags_through_r4_sentences(self):
        run = types.SimpleNamespace(dir=self.run_dir(FLAGGED), status={}, prov={})
        RF.flag_soft_rules(run, {"package_type": "moments"},
                           [{"rule": "rule_r4", "pass": False, "reason": self.reason(RUNTIME)},
                            {"rule": "rule_r1", "pass": True, "reason": "R1 PASS"}])
        self.assertEqual(run.status.get("review_flags"), None)        # the pin's own sentence is the one PBX reads
        run2 = types.SimpleNamespace(dir=self.run_dir(), status={}, prov={})
        RF.flag_soft_rules(run2, {"package_type": "moments"},
                           [{"rule": "rule_r4", "pass": False, "reason": self.reason(RUNTIME)}])
        self.assertEqual(run2.status["review_flags"], [LENGTH])


if __name__ == "__main__":
    unittest.main()
