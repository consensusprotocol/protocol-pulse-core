#!/usr/bin/env python3
"""Ruling 91's MEDLEY half on the live path (law L-ab (91), orchestrator 2026-11-13 '22:53'; the row agreed with the
builder 2026-11-14): run_fresh.stage_validate HOLDs a medley whose takeaway carries no sealed, live value verdict on
that very line (edl_rules.takeaway_value), after the EDL rules and BEFORE the editorial gate, and records the verdict in
PROVENANCE (takeaway_value). With the verdict, or with no takeaway (L-y's no-voice shape), the stage goes on.
Must-fail on the old run_fresh: it never asked, so every case below reached the editorial gate."""
import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import edl_rules  # noqa: E402
import editorial_gate  # noqa: E402
import run_fresh  # noqa: E402

TAKE = "No ruler. Just rules nobody gets to bend."


class Reached(Exception):
    """The editorial gate was called: stage_validate had passed ruling 91."""


def medley(gates, bridges=None):
    e = {"package_type": "moments", "mode": "pinned", "moments_package_sha256": "ab" * 32,
         "moments_checks": {"vo_fidelity_ok": True, "context_integrity_ok": True},
         "clips": [{"index": 1}, {"index": 2}],
         "vo": {"intro": None, "bridges": [{"text": TAKE, "after_clip": 2}] if bridges is None else bridges}}
    if gates is not None:
        e["moments_gates"] = gates
    return e


def live(**kw):
    r = {"status": "PASS", "by": "xai:grok-4.20-0309-reasoning", "replayed": False, "n": 1, "text": TAKE}
    r.update(kw)
    return {"takeaway_value": r}


class TestStageValidateRuling91(unittest.TestCase):

    def run_stage(self, edl):
        """stage_validate on this EDL, the EDL rules passed (stubbed) and the editorial gate a sentinel."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "edl.json"), "w") as f:
                json.dump(edl, f)
            run = types.SimpleNamespace(dir=d, prov={})
            with mock.patch.object(edl_rules, "validate_edl", return_value=(True, [])), \
                    mock.patch.object(editorial_gate, "run_gate", side_effect=Reached):
                try:
                    run_fresh.stage_validate(run)
                except Reached:
                    return "reached the editorial gate", run.prov
                except run_fresh.Hold as h:
                    return f"HOLD: {h}", run.prov
            return "returned", run.prov

    def test_a_takeaway_without_its_verdict_holds_before_the_editorial_gate(self):
        for gates in (None, {}, live(status="FAIL"), live(replayed=True), live(text="Another draft of the line.")):
            got, prov = self.run_stage(medley(gates))
            self.assertTrue(got.startswith("HOLD: ruling 91 (medley)"), (gates, got))
            self.assertIs(prov.get("takeaway_value", {}).get("pass"), False, got)

    def test_with_its_verdict_or_no_takeaway_the_stage_goes_on(self):
        for edl in (medley(live()), medley(None, bridges=[])):
            got, prov = self.run_stage(edl)
            self.assertEqual(got, "reached the editorial gate")
            self.assertIs(prov["takeaway_value"]["pass"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
