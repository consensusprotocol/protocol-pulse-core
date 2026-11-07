#!/usr/bin/env python3
import json
import os
import tempfile
import unittest

from editorial_gate import evaluate_editorial_gate, run_gate

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "editorial_gate_real_cases.json")


def _cases():
    with open(FIXTURE) as f:
        data = json.load(f)
    return {c["id"]: c for c in data["cases"]}


class TestEditorialGateRealMaterial(unittest.TestCase):
    def test_missing_review_fails_closed(self):
        case = _cases()["saved_v2f_progressive_story"]
        gate = evaluate_editorial_gate(case["edl"], None)
        self.assertEqual(gate["verdict"], "HOLD")
        self.assertFalse(gate["laws"]["L0_REVIEW"]["pass"])

    def test_bad_saved_proof_holds_on_filler_and_progression(self):
        case = _cases()["bad_pinned_proof"]
        gate = evaluate_editorial_gate(case["edl"], case["review"])
        self.assertEqual(gate["verdict"], case["expected_verdict"])

        failed = {name for name, rec in gate["laws"].items() if not rec["pass"]}
        for expected in case["expected_failed_laws"]:
            self.assertIn(expected, failed)

        self.assertTrue(gate["laws"]["LAW_1_NEW_INFORMATION"]["pass"])
        self.assertFalse(gate["laws"]["LAW_2_VO_HAS_A_JOB"]["pass"])
        self.assertTrue(gate["laws"]["LAW_3_CONCRETE_TAKEAWAY"]["pass"])
        self.assertFalse(gate["laws"]["LAW_4_SEQUENCE_PROGRESSES"]["pass"])

        reasons = " ".join(gate["laws"]["LAW_2_VO_HAS_A_JOB"]["reasons"])
        self.assertIn("known filler VO rejected", reasons)
        self.assertIn("This story is unfolding right now", reasons)

    def test_known_filler_cannot_be_overridden_by_reviewer(self):
        case = _cases()["bad_pinned_proof"]
        review = json.loads(json.dumps(case["review"]))
        review["vo_jobs"]["intro"] = {
            "job": "context",
            "why": "Reviewer claims it is useful.",
            "earned": True,
        }
        review["sequence"]["progresses"] = True
        gate = evaluate_editorial_gate(case["edl"], review)
        self.assertEqual(gate["verdict"], "HOLD")
        self.assertFalse(gate["laws"]["LAW_2_VO_HAS_A_JOB"]["pass"])

    def test_saved_v2f_progression_passes_all_four_laws(self):
        case = _cases()["saved_v2f_progressive_story"]
        gate = evaluate_editorial_gate(case["edl"], case["review"])
        self.assertEqual(gate["verdict"], case["expected_verdict"])
        failed = [name for name, rec in gate["laws"].items() if not rec["pass"]]
        self.assertEqual(failed, case["expected_failed_laws"])

    def test_each_post_hook_clip_requires_new_information_judgment(self):
        case = _cases()["saved_v2f_progressive_story"]
        review = json.loads(json.dumps(case["review"]))
        review["clips"] = review["clips"][:-1]
        gate = evaluate_editorial_gate(case["edl"], review)
        self.assertEqual(gate["verdict"], "HOLD")
        self.assertFalse(gate["laws"]["LAW_1_NEW_INFORMATION"]["pass"])
        self.assertIn(
            "missing new-information judgment",
            " ".join(gate["laws"]["LAW_1_NEW_INFORMATION"]["reasons"]),
        )

    def test_non_filler_body_vo_requires_allowed_job(self):
        case = _cases()["saved_v2f_progressive_story"]
        review = json.loads(json.dumps(case["review"]))
        review["vo_jobs"].pop("bridge_1")
        gate = evaluate_editorial_gate(case["edl"], review)
        self.assertEqual(gate["verdict"], "HOLD")
        self.assertFalse(gate["laws"]["LAW_2_VO_HAS_A_JOB"]["pass"])
        self.assertIn(
            "requires a job judgment",
            " ".join(gate["laws"]["LAW_2_VO_HAS_A_JOB"]["reasons"]),
        )

    def test_gate_writes_storyboard_before_any_factory_stage(self):
        case = _cases()["bad_pinned_proof"]
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "EDITORIAL_REVIEW.json"), "w") as f:
                json.dump(case["review"], f)
            gate = run_gate(td, case["edl"])
            self.assertEqual(gate["verdict"], "HOLD")
            self.assertTrue(os.path.exists(os.path.join(td, "EDITORIAL_GATE.json")))
            storyboard = os.path.join(td, "STORYBOARD.md")
            self.assertTrue(os.path.exists(storyboard))
            with open(storyboard) as f:
                text = f.read()
            self.assertIn("Editorial verdict:** HOLD", text)
            self.assertIn("LAW_2_VO_HAS_A_JOB: FAIL", text)
            self.assertIn("LAW_4_SEQUENCE_PROGRESSES: FAIL", text)


if __name__ == "__main__":
    unittest.main()
