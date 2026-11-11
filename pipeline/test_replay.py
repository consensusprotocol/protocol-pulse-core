#!/usr/bin/env python3
"""Orchestrator 08:30 ET (direction 4): replay an existing run's tail on a copy with the production functions.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_replay.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import replay  # noqa: E402
import run_fresh as rf  # noqa: E402


def _fake_run(root):
    rd = os.path.join(root, "pinned_20261111_000000")
    for sub in ("sources", "transcripts", "out", "qa", "VERIFY"):
        os.makedirs(os.path.join(rd, sub))
    for p, body in (("sources/VID.mp4", "source bytes"), ("transcripts/VID.json", "{}"), ("out/segment.mp4", "old"),
                    ("out/segment_vertical.mp4", "old"), ("qa/final_hook.mp4", "prepared"),
                    ("GATE_REPORT.json", "{}"), ("TELEGRAM_DELIVERY.json", "{}"), ("VERIFY/x.jpg", "v")):
        open(os.path.join(rd, p), "w").write(body)
    json.dump([{"clip_id": "hook"}], open(os.path.join(rd, "cuts_final.json"), "w"))
    json.dump({"mode": "pinned"}, open(os.path.join(rd, "status.json"), "w"))
    json.dump({"run_dir": rd}, open(os.path.join(rd, "PROVENANCE.json"), "w"))
    json.dump({"pin": {"machine_cuts": True}}, open(os.path.join(rd, "PINNED_DECISION.json"), "w"))
    return rd


class TestCopy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="replay_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.rd = _fake_run(self.tmp)

    def test_sources_are_linked_outputs_are_fresh_deliveries_never_copied(self):
        dst = replay.make_copy(self.rd, "render", stamp="T1")
        same = lambda p: os.stat(os.path.join(self.rd, p)).st_ino == os.stat(os.path.join(dst, p)).st_ino
        self.assertTrue(same("sources/VID.mp4"))                       # read-only input: hard link
        self.assertFalse(same("qa/final_hook.mp4"))                    # rebuilt by prepare: a real copy
        for gone in ("out/segment.mp4", "out/segment_vertical.mp4", "GATE_REPORT.json", "TELEGRAM_DELIVERY.json", "VERIFY"):
            self.assertFalse(os.path.exists(os.path.join(dst, gone)), gone)
        dst2 = replay.make_copy(self.rd, "gates", stamp="T2")          # gates measure the existing finals
        self.assertTrue(os.path.exists(os.path.join(dst2, "out/segment.mp4")))
        with self.assertRaises(SystemExit):
            replay.make_copy(self.rd, "gates", stamp="T2")             # never overwrite a replay


class TestReplayVerdict(unittest.TestCase):
    def test_an_unexpected_exception_is_a_hold_with_its_reason(self):
        tmp = tempfile.mkdtemp(prefix="replay_")
        self.addCleanup(shutil.rmtree, tmp, True)
        rd = _fake_run(tmp)
        with mock.patch.object(rf, "run_tail", side_effect=RuntimeError("render crashed")), \
                mock.patch.object(rf, "write_report", lambda run: None):
            dst, verdict = replay.replay(rd, "gates", vision=False, stamp="T3")
        self.assertEqual(verdict, rf.VERDICT_HOLD)
        st = json.load(open(os.path.join(dst, "status.json")))
        self.assertTrue(any("replay: RuntimeError: render crashed" in h for h in st["holds"]), st["holds"])
        self.assertEqual(open(os.path.join(dst, "VERDICT.txt")).read().strip(), rf.VERDICT_HOLD)


class TestRunTail(unittest.TestCase):
    """main and replay share run_fresh.run_tail: a replay from `start` runs exactly the later stages."""

    def run_tail(self, start):
        tmp = tempfile.mkdtemp(prefix="tail_")
        self.addCleanup(shutil.rmtree, tmp, True)
        run = rf.Run(tmp)
        calls = []
        rows = {"16x9": {"G1": "PASS"}, "9x16": {"G1": "PASS"}}

        def gates(run_, *a):
            calls.append("gates")
            json.dump({"rows": rows}, open(os.path.join(tmp, "GATE_REPORT.json"), "w"))
            return rows, {}, {}
        with mock.patch.object(rf, "stage_prepare", lambda r, c: calls.append("prepare")), \
                mock.patch.object(rf, "stage_layout", lambda r, c: calls.append("layout")), \
                mock.patch.object(rf, "stage_render", lambda r: calls.append("render") or ("f16", "m16", "f9", "m9")), \
                mock.patch.object(rf, "stage_gates", gates), \
                mock.patch("verify_pack.build", lambda d, vision=True: calls.append(f"verify:{vision}") or {}):
            rf.run_tail(run, [], start=start, vision=(start != "gates"))
        return calls, run

    def test_each_start_runs_only_the_later_stages(self):
        self.assertEqual(self.run_tail("prepare")[0], ["prepare", "layout", "render", "gates", "verify:True"])
        self.assertEqual(self.run_tail("render")[0], ["render", "gates", "verify:True"])
        calls, run = self.run_tail("gates")
        self.assertEqual(calls, ["gates", "verify:False"])
        self.assertEqual(run.status["verdict"], rf.VERDICT_CANDIDATE)


if __name__ == "__main__":
    unittest.main()
