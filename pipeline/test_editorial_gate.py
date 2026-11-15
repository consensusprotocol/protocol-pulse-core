#!/usr/bin/env python3
import json
import os
import tempfile
import unittest

from editorial_gate import evaluate_editorial_gate, run_gate
from select_passages import _generate_vo_script

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

    def test_shared_auto_pin_generator_emits_no_body_vo_by_default(self):
        case = _cases()["saved_v2f_progressive_story"]
        edl = json.loads(json.dumps(case["edl"]))
        edl["vo"] = _generate_vo_script(
            edl["topic"], edl["hook"]["text"], edl["clips"],
            [c["channel"] for c in edl["clips"]],
        )
        self.assertIsNone(edl["vo"]["intro"])
        self.assertEqual(edl["vo"]["bridges"], [])

        # Same real progressive material with the shared AUTO/PIN default body-VO
        # must satisfy Law 2 and retain the human-affirmed Law 4 progression.
        review = json.loads(json.dumps(case["review"]))
        review["vo_jobs"] = {}
        gate = evaluate_editorial_gate(edl, review)
        self.assertTrue(gate["laws"]["LAW_2_VO_HAS_A_JOB"]["pass"], gate)
        self.assertTrue(gate["laws"]["LAW_4_SEQUENCE_PROGRESSES"]["pass"], gate)
        self.assertEqual(gate["verdict"], "READY_FOR_RENDER")

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


class TestSpotlightLaws2And3(unittest.TestCase):
    """Law L-ab / ruling 91 (found on the first spotlight render, 3f481f5a, 2026-11-14): the medley review is
    inconclusive on one moment, so a spotlight's LAW 2 (its closing line has a job) and LAW 3 (its takeaway) read the
    builder's sealed rows: closing_value / closing_fidelity / closing_context for the line, stands_alone / hook_own for
    the moment, each exactly PASS and live. Must-fail: any of them missing, not PASS or replayed. A medley unchanged."""
    REVIEW = {"inconclusive": True, "inconclusive_reason": "only one clip and a single voiceover line"}
    LINE = "Most people focus on the buy. The leaving is the story."

    def edl(self, line=LINE, shape="spotlight", **rows):
        gates = {r: {"status": "PASS", "replayed": False} for r in
                 ("stands_alone", "hook_own", "closing_value", "closing_fidelity", "closing_context")}
        for r, v in rows.items():
            if v is None:
                gates.pop(r)
            else:
                gates[r] = dict(gates[r], **v)
        return {"package_type": "moments", "package_shape": shape, "clips": [],
                "vo": {"intro": line, "bridges": []}, "moments_gates": gates}

    def laws(self, edl):
        g = evaluate_editorial_gate(edl, self.REVIEW)["laws"]
        return g["LAW_2_VO_HAS_A_JOB"]["pass"], g["LAW_3_CONCRETE_TAKEAWAY"]["pass"]

    def test_the_sealed_rows_judge_the_line_and_the_moment(self):
        self.assertEqual(self.laws(self.edl()), (True, True))
        self.assertEqual(self.laws(self.edl(line=None, closing_value=None)), (True, True))   # zero-line spotlight

    def test_a_missing_failed_or_replayed_row_fails(self):
        for row in ("closing_value", "closing_fidelity", "closing_context"):
            for bad in (None, {"status": "FAIL"}, {"replayed": True}, {"replayed": None}):
                with self.subTest(row=row, bad=bad):
                    self.assertEqual(self.laws(self.edl(**{row: bad})), (False, False))
        for row in ("stands_alone", "hook_own"):
            for bad in (None, {"status": "NOT RUN"}, {"replayed": True}):
                with self.subTest(row=row, bad=bad):
                    self.assertEqual(self.laws(self.edl(**{row: bad})), (True, False))

    def test_a_medley_still_needs_the_review(self):
        self.assertEqual(self.laws(self.edl(shape=None)), (False, False))

    def test_a_judgment_the_review_does_give_stands(self):     # the sealed rows only fill the review's silence
        review = {"vo_jobs": {"intro": {"job": "context", "why": "restates the clip", "earned": False}},
                  "takeaway": {"text": "selling early", "concrete": False, "supported": True}}
        g = evaluate_editorial_gate(self.edl(), review)["laws"]   # every sealed row PASS and live
        self.assertEqual((g["LAW_2_VO_HAS_A_JOB"]["pass"], g["LAW_3_CONCRETE_TAKEAWAY"]["pass"]), (False, False))


if __name__ == "__main__":
    unittest.main()
