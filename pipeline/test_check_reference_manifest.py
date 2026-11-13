#!/usr/bin/env python3
"""check_reference_manifest (order 2026-11-12 '20:30' (c)): a protected reference is exactly its SHA256SUMS.
Must-fail: a changed byte, a missing file, an added file, an unreadable or empty manifest. Pass: the untouched copy.
SKIP (2): no manifest. On this machine also the real references/pulse_moments_2026-11-12 (read-only, untouched)."""
import hashlib
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_reference_manifest import check  # noqa: E402

REAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references", "pulse_moments_2026-11-12")


class TestReferenceManifest(unittest.TestCase):
    def setUp(self):
        self.ref = tempfile.mkdtemp(prefix="refman_")
        os.makedirs(os.path.join(self.ref, "out"))
        rows = []
        for rel, data in (("edl.json", b'{"vo": {"intro": null}}'), ("out/segment.mp4", b"\x00\x01video")):
            with open(os.path.join(self.ref, rel), "wb") as f:
                f.write(data)
            rows.append(f"{hashlib.sha256(data).hexdigest()}  ./{rel}")
        with open(os.path.join(self.ref, "SHA256SUMS"), "w") as f:
            f.write("\n".join(rows) + "\n")

    def tearDown(self):
        shutil.rmtree(self.ref)

    def test_the_untouched_copy_passes(self):
        self.assertEqual(check(self.ref), (0, [], 2))

    def test_a_changed_byte_fails(self):
        with open(os.path.join(self.ref, "out", "segment.mp4"), "ab") as f:
            f.write(b"\x00")
        rc, bad, _ = check(self.ref)
        self.assertEqual((rc, bad), (1, ["changed out/segment.mp4"]))

    def test_a_missing_file_fails(self):
        os.remove(os.path.join(self.ref, "edl.json"))
        self.assertEqual(check(self.ref)[:2], (1, ["missing edl.json"]))

    def test_an_added_file_fails(self):
        with open(os.path.join(self.ref, "out", "segment_v2.mp4"), "wb") as f:
            f.write(b"x")
        self.assertEqual(check(self.ref)[:2], (1, ["added out/segment_v2.mp4"]))

    def test_a_bad_or_empty_manifest_fails(self):
        with open(os.path.join(self.ref, "SHA256SUMS"), "a") as f:
            f.write("not a manifest line\n")
        rc, bad, _ = check(self.ref)
        self.assertEqual(rc, 1)
        self.assertIn("manifest line 3 unreadable", bad)
        open(os.path.join(self.ref, "SHA256SUMS"), "w").close()
        rc, bad, _ = check(self.ref)
        self.assertEqual(rc, 1)
        self.assertIn("manifest lists no file", bad)

    def test_no_manifest_is_a_skip(self):
        os.remove(os.path.join(self.ref, "SHA256SUMS"))
        self.assertEqual(check(self.ref)[0], 2)

    @unittest.skipUnless(os.path.isfile(os.path.join(REAL, "SHA256SUMS")), "the moments reference not on this machine")
    def test_the_real_reference_is_intact(self):
        rc, bad, n = check(REAL)
        self.assertEqual((rc, bad), (0, []))
        self.assertGreaterEqual(n, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
