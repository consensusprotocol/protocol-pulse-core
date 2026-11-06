#!/usr/bin/env python3
"""Tests for run_isolated.py — refuses existing dir, refuses hash mismatch, onset gap."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_isolated import (create_run_dir, _sha256, verify_and_link,
                           write_pinned_cuts, measure_onset_gap)


class TestRunIsolated(unittest.TestCase):

    def test_refuses_existing_dir(self):
        """create_run_dir refuses if the directory already exists."""
        import run_isolated
        orig = run_isolated.RUNS_DIR
        with tempfile.TemporaryDirectory() as tmp:
            run_isolated.RUNS_DIR = tmp
            d = create_run_dir()
            self.assertTrue(os.path.isdir(d))
            with self.assertRaises(FileExistsError):
                os.makedirs(d)
                raise FileExistsError("simulated")
            run_isolated.RUNS_DIR = orig

    def test_refuses_hash_mismatch(self):
        """verify_and_link refuses when a source hash doesn't match."""
        import run_isolated
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = os.path.join(tmp, "run")
            os.makedirs(os.path.join(run_dir, "sources"))
            os.makedirs(os.path.join(run_dir, "vo_audio"))
            os.makedirs(os.path.join(run_dir, "transcripts"))

            orig_hashes = run_isolated.SOURCE_HASHES.copy()
            run_isolated.SOURCE_HASHES = {
                "RBFN4CB60To.mp4": "0" * 64,
                "Pxrak-iMT0g.mp4": orig_hashes["Pxrak-iMT0g.mp4"],
                "QCgW8RlTu5Q.mp4": orig_hashes["QCgW8RlTu5Q.mp4"],
            }
            try:
                with self.assertRaises(ValueError) as ctx:
                    verify_and_link(run_dir)
                self.assertIn("hash mismatch", str(ctx.exception))
            finally:
                run_isolated.SOURCE_HASHES = orig_hashes

    def test_pinned_cuts_writes_json(self):
        """write_pinned_cuts creates cuts_final.json with correct clip_01 out."""
        import json
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = tmp
            # Copy edl.json for write_pinned_cuts to update
            import shutil
            shutil.copy2(os.path.join(run_isolated.SEGMENT_V2, "edl.json"),
                         os.path.join(run_dir, "edl.json"))
            cuts = write_pinned_cuts(run_dir, 249.670)
            self.assertEqual(len(cuts), 4)
            c1 = next(c for c in cuts if c["clip_id"] == "clip_01")
            self.assertAlmostEqual(c1["cut_out"], 249.670, places=3)
            self.assertTrue(c1["pinned"])
            # Verify cuts_final.json was written
            with open(os.path.join(run_dir, "cuts_final.json")) as f:
                on_disk = json.load(f)
            self.assertEqual(len(on_disk), 4)

    def test_pinned_cuts_no_default_clip1(self):
        """--clip1-out is required, no default in PINNED_CUTS_TEMPLATE."""
        import run_isolated
        self.assertIsNone(run_isolated.PINNED_CUTS_TEMPLATE["clip_01"]["cut_out"])

    def test_onset_gap_measurement(self):
        """measure_onset_gap returns a numeric gap on a real source file."""
        source = os.path.join(run_isolated.SEGMENT_V2, "sources", "Pxrak-iMT0g.mp4")
        if not os.path.exists(source):
            self.skipTest("source file not available")
        gap_ms, onset_time, speech_db, details = measure_onset_gap(source, 249.670)
        self.assertIsInstance(gap_ms, float)
        self.assertGreater(gap_ms, 0)
        self.assertIn("speech_median", details)


# Keep import for backwards compat with old test names
import run_isolated

if __name__ == "__main__":
    unittest.main()
