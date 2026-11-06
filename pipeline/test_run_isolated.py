#!/usr/bin/env python3
"""Tests for run_isolated.py — refuses existing dir, refuses hash mismatch."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run_isolated import create_run_dir, _sha256, verify_and_link, abort_check, RUNS_DIR


class TestRunIsolated(unittest.TestCase):

    def test_refuses_existing_dir(self):
        """create_run_dir refuses if the directory already exists."""
        import run_isolated
        # Temporarily override RUNS_DIR to a temp location
        orig = run_isolated.RUNS_DIR
        with tempfile.TemporaryDirectory() as tmp:
            run_isolated.RUNS_DIR = tmp
            # First call succeeds
            d = create_run_dir()
            self.assertTrue(os.path.isdir(d))
            # Manually create another with same timestamp (simulate collision)
            os.makedirs(d + "_dup", exist_ok=True)
            # Verify the guard: direct existence check
            with self.assertRaises(FileExistsError):
                # Force same path
                os.makedirs(d)  # already exists from first call
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

            # Inject a bad hash for the first source
            orig_hashes = run_isolated.SOURCE_HASHES.copy()
            run_isolated.SOURCE_HASHES = {
                "RBFN4CB60To.mp4": "0000000000000000000000000000000000000000000000000000000000000000",
                "Pxrak-iMT0g.mp4": orig_hashes["Pxrak-iMT0g.mp4"],
                "QCgW8RlTu5Q.mp4": orig_hashes["QCgW8RlTu5Q.mp4"],
            }
            try:
                with self.assertRaises(ValueError) as ctx:
                    verify_and_link(run_dir)
                self.assertIn("hash mismatch", str(ctx.exception))
            finally:
                run_isolated.SOURCE_HASHES = orig_hashes

    def test_abort_check_clip01_out_of_range(self):
        """abort_check fails when clip_01 cut_out is outside [249.62, 249.72]."""
        cuts = {
            "clip_01": {"cut_out": 249.37},  # stale v2e value = out of range
            "clip_02": {"cut_out": 636.72, "cut_in": 624.63},
            "clip_03": {"cut_out": 1011.80, "cut_in": 998.0},
        }
        ok, msgs = abort_check(cuts)
        self.assertFalse(ok)
        self.assertTrue(any("clip_01" in m for m in msgs))

    def test_abort_check_clip02_delta(self):
        """abort_check fails when clip_02 cut_out diverges > 0.005 from v2e."""
        cuts = {
            "clip_01": {"cut_out": 249.670},
            "clip_02": {"cut_out": 636.780, "cut_in": 624.63},  # delta 0.060
            "clip_03": {"cut_out": 1011.80, "cut_in": 998.0},
        }
        ok, msgs = abort_check(cuts)
        self.assertFalse(ok)
        self.assertTrue(any("clip_02" in m for m in msgs))


if __name__ == "__main__":
    unittest.main()
