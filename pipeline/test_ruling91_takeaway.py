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

TAKE = "No ruler, just rules nobody gets to bend."         # item 2 (Nov 24): one sentence


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
                    mock.patch.object(run_fresh, "out_edges", side_effect=lambda run, edl: self.edges), \
                    mock.patch.object(editorial_gate, "run_gate", side_effect=Reached):
                try:
                    run_fresh.stage_validate(run)
                except Reached:
                    return "reached the editorial gate", run.prov
                except run_fresh.Hold as h:
                    return f"HOLD: {h}", run.prov
            return "returned", run.prov

    edges = []                                       # ruling 162 (1)'s re-ask, stubbed: no segment asked

    def test_ruling_162_a_takeaway_without_its_live_pass_holds(self):
        """RULING 162 (2) (orchestrator 07:45 ET Nov 24): the closing line's VALUE is a requirement again (ruling 150
        reversed): no row, a non-PASS (FLAGGED included), a replayed verdict or one on another draft HOLDS before the
        editorial gate; it is no longer a flag."""
        for gates in (None, {}, live(status="FAIL"), live(replayed=True), live(text="Another draft of the line."),
                      live(status="FLAGGED", flags=["The closing line may not say much."])):
            got, prov = self.run_stage(medley(gates))
            self.assertTrue(got.startswith("HOLD: ruling 162 (2): the closing voiceover line may not be voiced"), got)
            self.assertIs(prov.get("takeaway_value", {}).get("pass"), False, got)
            self.assertNotIn("review_flags", prov)

    def test_ruling_162_a_line_of_ours_that_lists_the_sources_holds(self):
        line = "Bitcoin, in the words of Simply Bitcoin and Yahoo Finance, in their own clips."
        e = medley(live(text=line), bridges=[{"text": line, "after_clip": 2}])
        e["clips"] = [{"index": 1, "channel": "Simply Bitcoin"}, {"index": 2, "channel": "Yahoo Finance"}]
        got, prov = self.run_stage(e)
        self.assertTrue(got.startswith("HOLD: ruling 162 (2) / item 2: a voiceover line of ours fails the lexical "
                                       "check"), got)
        self.assertIn("the closing line 'Bitcoin, in the words of", got)
        for part in ("names 'Simply Bitcoin'", "names 'Yahoo Finance'", "says 'in the words of'"):
            self.assertIn(part, got)
        self.assertEqual(prov["our_lines"]["pass"], False)
        e["vo"]["bridges"] = [{"text": "Same question, from a miner's side.", "after_clip": 1}]     # a clean bridge,
        got, prov = self.run_stage(e)                                                          # no takeaway
        self.assertEqual(got, "reached the editorial gate")
        self.assertEqual(prov["our_lines"], {"pass": True, "faults": []})

    def test_ruling_162_an_open_out_edge_holds_and_an_unanswered_one_is_unverified(self):
        """The question runs at the cut now (orchestrator 09:45 ET Nov 24: after the deterministic edge check):
        check_out_edges holds on its answers."""
        def edge(seg, complete, measured=True, why="w"):
            return {"segment": seg, "complete": complete, "finishes_at": None, "why": why, "measured": measured}
        run = types.SimpleNamespace(dir="/nonexistent", prov={})
        for edges, want in (([edge("hook", False, why="the same story is told next"), edge("clip_01", True)],
                             "ruling 162 (1): a clip ends while the speaker's thought carries on: hook (the same "
                             "story is told next)"),
                            ([edge("hook", True), edge("clip_01", None, False, "no answer: URLError")],
                             "UNVERIFIED (ruling 160 (2a)): the OUT-edge check (ruling 162 (1)) could not be "
                             "answered for clip_01 (no answer: URLError)"),
                            ([edge("hook", False, why="w0"), edge("clip_01", None, False, "no answer: URLError")],
                             "ruling 162 (1): a clip ends while the speaker's thought carries on: hook (w0); "
                             "and UNVERIFIED (ruling 160 (2a)), the check could not be answered for clip_01 (no "
                             "answer: URLError)")):
            with mock.patch.object(run_fresh, "out_edges", return_value=edges):
                with self.assertRaises(run_fresh.Hold) as cm:
                    run_fresh.check_out_edges(run, medley(live()), [])
            self.assertEqual(str(cm.exception), want)
            self.assertEqual(run.prov["out_edge"], edges)
        with mock.patch.object(run_fresh, "out_edges", return_value=[edge("hook", True), edge("clip_01", True)]):
            self.assertEqual(len(run_fresh.check_out_edges(run, medley(live()), [])), 2)
        got, prov = self.run_stage(medley(live()))                       # validate no longer asks it
        self.assertEqual(got, "reached the editorial gate")
        self.assertNotIn("out_edge", prov)

    def test_with_its_verdict_or_no_takeaway_the_stage_goes_on(self):
        for edl in (medley(live()), medley(None, bridges=[])):
            got, prov = self.run_stage(edl)
            self.assertEqual(got, "reached the editorial gate")
            self.assertIs(prov["takeaway_value"]["pass"], True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
