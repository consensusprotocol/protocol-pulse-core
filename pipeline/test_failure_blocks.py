#!/usr/bin/env python3
"""Addendum 2 item 6 (failure blocks delivery), on the release contract of 2026-11-11 (red-team A).

Each test builds a complete AUTHORISED run dir (test_release_auth.make_run), sabotages one element, and verifies
that telegram.deliver_run refuses before anything is sent:
  (a) a required gate row deleted from GATE_REPORT.json after the attestation
  (b) a required gate row set to FAIL (re-attested: the attestation itself is HOLD)
  (c) the mp4 modified after the attestation (digest mismatch)
  (d) the attestation removed (the old VERIFIED_BY_ORCHESTRATOR marker is gone; this is its replacement)
  (e) a legacy GATE_FAIL.txt / truthy gate_results_*.json no longer authorise anything
No Telegram calls are made: the sender is injected and must never be called."""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import release_auth as RA  # noqa: E402
import telegram as TG  # noqa: E402
from test_release_auth import edit_json, make_run, passing_rows  # noqa: E402


class TestFailureBlocksDelivery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="failure_blocks_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def refused(self, rd, needle):
        sent = []
        with self.assertRaises(RuntimeError) as ctx:
            TG.deliver_run(rd, send=lambda kind, path, fields, data=None: sent.append(kind) or 1)
        self.assertEqual(sent, [])
        self.assertIn(needle, str(ctx.exception))

    def test_a_deleted_gate_row_blocks(self):
        rd = make_run(self.tmp)
        edit_json(os.path.join(rd, "GATE_REPORT.json"), lambda d: d["rows"]["16x9"].pop("G18_word_for_word"))
        self.refused(rd, "GATE_REPORT.json rows / evidence differ")

    def test_b_failing_gate_blocks(self):
        rows = passing_rows()
        rows["9x16"]["G9_tail"] = "FAIL"
        self.refused(make_run(self.tmp, rows=rows), "9x16 G9_tail: FAIL")

    def test_c_modified_mp4_after_attestation_blocks(self):
        rd = make_run(self.tmp)
        with open(os.path.join(rd, "out", "segment.mp4"), "ab") as f:
            f.write(b"\0" * 16)
        self.refused(rd, "out/segment.mp4: changed since it was attested")

    def test_d_no_attestation_blocks(self):
        rd = make_run(self.tmp)
        os.remove(os.path.join(rd, "ATTESTATION.json"))
        self.refused(rd, "no readable attestation")

    def test_e_legacy_markers_authorise_nothing(self):
        rd = make_run(self.tmp, attest=False)
        open(os.path.join(rd, "VERIFIED_BY_ORCHESTRATOR"), "w").write("verified")
        for fmt in ("16x9", "9x16"):
            json.dump({"all_pass": True}, open(os.path.join(rd, "qa", f"gate_results_{fmt}.json"), "w"))
        self.refused(rd, "no readable attestation")
        with self.assertRaises(RuntimeError):
            TG.send_telegram_preview(rd)
        self.assertFalse(RA.authorise(rd)[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
