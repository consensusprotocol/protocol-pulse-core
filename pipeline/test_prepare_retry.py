#!/usr/bin/env python3
"""Nov 11 recut, clip_02: the machine-placed cut_out 37.87 (inside the locked pause, cut_accept-clean) sat on
a tick, so the prepared clip failed the unchanged clip contract's fade-out check (edge -56.8 dB vs ref -71.8).
Real prepare at 37.84 / 37.80 passes. stage_prepare now moves ONLY the failing edge to the next legal point
of the same pause and re-checks with the real contract; human cut tables never move.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_prepare_retry.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import run_fresh as rf  # noqa: E402

FAIL_OUT = {"errors": ["fade-out missing (edge -56.8 dB vs ref -71.8 dB)"]}


class TestFadeRetry(unittest.TestCase):
    def setUp(self):
        self.rd = tempfile.mkdtemp(prefix="fretry_")
        self.addCleanup(shutil.rmtree, self.rd, True)
        os.makedirs(os.path.join(self.rd, "transcripts"))
        lock = {"i0": 0, "i1": 1}
        json.dump({"hook": {"selection_lock": lock}, "clips": [{"index": 2, "selection_lock": lock}]},
                  open(os.path.join(self.rd, "edl.json"), "w"))
        json.dump({"words": []}, open(os.path.join(self.rd, "transcripts", "NAT.json"), "w"))
        self.run = rf.Run(self.rd)
        self.run.mode = "pinned"
        self.run.machine_cuts = True
        self.c = {"clip_id": "clip_02", "video_id": "NAT", "cut_in": 24.65, "cut_out": 37.87, "cut_duration": 13.22}
        self.prepared = []

    def go(self, contract_ok_at, cand_out=(37.88, 37.87, 37.86, 37.85, 37.84, 37.83), d1=FAIL_OUT):
        def prerender(run_dir, cuts):
            self.prepared.append(cuts[0]["cut_out"])

        def check(path, dur):
            out = self.prepared[-1]
            return (True, {"errors": []}) if out in contract_ok_at else (False, FAIL_OUT)
        with mock.patch.object(rf.L, "cut_candidates", return_value={"out": list(cand_out), "in": [24.65]}), \
                mock.patch.object(rf.L, "edge_plan", return_value={}), \
                mock.patch.object(rf.L, "SourceAudio", return_value=None), \
                mock.patch("cut_accept.check_cut_acoustics", return_value=(True, {})):
            return rf._retry_fade_edges(self.run, self.c, d1, prerender, check, 24, 20)

    def test_failing_out_edge_moves_to_the_next_legal_point_that_passes(self):
        ok, d = self.go(contract_ok_at={37.84})
        self.assertTrue(ok, d)
        self.assertEqual((self.c["cut_in"], self.c["cut_out"], self.c["cut_duration"]), (24.65, 37.84, 13.19))
        self.assertEqual(self.prepared, [37.88, 37.86, 37.85, 37.84])           # nearest first, current skipped
        self.assertEqual([t["cut_out"] for t in self.c["contract_retries"]], [37.88, 37.86, 37.85, 37.84])

    def test_no_legal_point_passes_restores_the_original_and_holds(self):
        ok, d = self.go(contract_ok_at=set())
        self.assertFalse(ok)
        self.assertEqual(self.c["cut_out"], 37.87)
        self.assertEqual(self.prepared[-1], 37.87)                             # the clip on disk is the original

    def test_human_cut_tables_never_move(self):
        self.run.machine_cuts = False
        ok, d = self.go(contract_ok_at={37.84})
        self.assertFalse(ok)
        self.assertEqual((self.c["cut_out"], self.prepared), (37.87, []))

    def test_non_fade_failures_are_not_retried(self):
        ok, d = self.go(contract_ok_at={37.84}, d1={"errors": ["duration 12.10 s vs expected 13.22 s"]})
        self.assertFalse(ok)
        self.assertEqual(self.prepared, [])


class TestGpu0Release(unittest.TestCase):
    """Nov 11 recut run 3 OOM'd in prepare: another session had loaded a 22 GB model on the shared GPU0
    Ollama. Whisper stages now release GPU0 first, like the editorial stage."""

    def run_(self):
        r = rf.Run(tempfile.mkdtemp(prefix="gpu0_"))
        self.addCleanup(shutil.rmtree, r.dir, True)
        return r

    def test_unprovable_release_is_an_infrastructure_hold(self):
        import story_semantics as sm
        with mock.patch.object(sm, "LocalLLM", return_value=object()), \
                mock.patch.object(sm, "release_gpu0_for_whisper", side_effect=RuntimeError("GPU0 release not proven")):
            with self.assertRaises(rf.Hold) as cm:
                rf.free_gpu0_for_whisper(self.run_(), "prepare")
        self.assertIn("infrastructure: prepare", str(cm.exception))

    def test_release_is_recorded(self):
        import story_semantics as sm
        run = self.run_()
        with mock.patch.object(sm, "LocalLLM", return_value=object()), \
                mock.patch.object(sm, "release_gpu0_for_whisper", return_value={"free_mib": 20000}):
            rf.free_gpu0_for_whisper(run, "gates")
        self.assertEqual(run.prov["gpu0_release"]["gates"], {"free_mib": 20000})


if __name__ == "__main__":
    unittest.main()
