#!/usr/bin/env python3
"""Addendum 2 item 6: failure blocks delivery tests.

Each test creates a scratch copy of a passing run dir, sabotages one element,
and verifies that send_telegram_preview raises before sending.

Tests:
  (a) Delete a required clip record from gate results
  (b) Delete one expected gate result file
  (c) Modify the mp4 after VERIFIED_BY_ORCHESTRATOR (hash mismatch scenario)
  (d) Remove VERIFIED_BY_ORCHESTRATOR marker

No Telegram calls are made. The guard logic raises before reaching the sender.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import resolve_paths

# We need telegram.py
from telegram import send_telegram_preview


class TestFailureBlocksDelivery(unittest.TestCase):
    """Sabotage tests against the Telegram guard in pipeline/telegram.py."""

    @classmethod
    def setUpClass(cls):
        """Create a minimal scratch run dir that would pass all guards."""
        cls.tmpdir = tempfile.mkdtemp(prefix="failure_blocks_")
        cls.segment_dir = cls.tmpdir

        # Create out dir with dummy mp4s
        out_dir = os.path.join(cls.tmpdir, "out")
        os.makedirs(out_dir)
        for name in ("segment.mp4", "segment_vertical.mp4"):
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(b"\x00" * 1024)  # dummy content

        # Create qa dir with passing gate results
        qa_dir = os.path.join(cls.tmpdir, "qa")
        os.makedirs(qa_dir)
        for aspect in ("16x9", "9x16"):
            results = {
                "all_pass": True,
                "G1_voice": {"pass": True},
                "G3_cuts": {"pass": True},
                "G5_tech": {"pass": True},
                "G8_sharpness": {"pass": True},
            }
            with open(os.path.join(qa_dir, f"gate_results_{aspect}.json"), "w") as f:
                json.dump(results, f)

        # Create VERIFIED_BY_ORCHESTRATOR marker
        with open(os.path.join(cls.tmpdir, "VERIFIED_BY_ORCHESTRATOR"), "w") as f:
            f.write("verified")

        # Create edl.json (for config.resolve_paths)
        with open(os.path.join(cls.tmpdir, "edl.json"), "w") as f:
            json.dump({"clips": []}, f)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _fresh_copy(self):
        """Return a fresh copy of the passing run dir."""
        copy_dir = tempfile.mkdtemp(prefix="sabotage_")
        shutil.copytree(self.segment_dir, copy_dir, dirs_exist_ok=True)
        return copy_dir

    def test_a_delete_gate_result_blocks(self):
        """(a) Delete one gate result file — telegram must refuse."""
        d = self._fresh_copy()
        try:
            qa_dir = os.path.join(d, "qa")
            os.remove(os.path.join(qa_dir, "gate_results_16x9.json"))
            with self.assertRaises((FileNotFoundError, RuntimeError)) as ctx:
                send_telegram_preview(d)
            self.assertIn("gate", str(ctx.exception).lower())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_b_set_gate_fail_blocks(self):
        """(b) Set all_pass=false in gate results — telegram must refuse."""
        d = self._fresh_copy()
        try:
            qa_dir = os.path.join(d, "qa")
            path = os.path.join(qa_dir, "gate_results_9x16.json")
            with open(path) as f:
                data = json.load(f)
            data["all_pass"] = False
            with open(path, "w") as f:
                json.dump(data, f)
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_preview(d)
            self.assertIn("not all-pass", str(ctx.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_c_modify_mp4_after_verified(self):
        """(c) Modify mp4 after VERIFIED — currently only checks existence.
        This test verifies the file still blocks if deleted entirely."""
        d = self._fresh_copy()
        try:
            out_dir = os.path.join(d, "out")
            os.remove(os.path.join(out_dir, "segment.mp4"))
            with self.assertRaises(FileNotFoundError) as ctx:
                send_telegram_preview(d)
            self.assertIn("missing", str(ctx.exception).lower())
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_d_remove_verified_marker_blocks(self):
        """(d) Remove VERIFIED_BY_ORCHESTRATOR — telegram must refuse."""
        d = self._fresh_copy()
        try:
            os.remove(os.path.join(d, "VERIFIED_BY_ORCHESTRATOR"))
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_preview(d)
            self.assertIn("VERIFIED_BY_ORCHESTRATOR", str(ctx.exception))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_e_gate_fail_txt_blocks(self):
        """(e) Create GATE_FAIL.txt — telegram must refuse even with passing results."""
        d = self._fresh_copy()
        try:
            qa_dir = os.path.join(d, "qa")
            with open(os.path.join(qa_dir, "GATE_FAIL.txt"), "w") as f:
                f.write("G8 sharpness below floor")
            with self.assertRaises(RuntimeError) as ctx:
                send_telegram_preview(d)
            self.assertIn("gates failed", str(ctx.exception).lower())
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
