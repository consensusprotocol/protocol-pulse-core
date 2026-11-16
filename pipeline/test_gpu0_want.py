#!/usr/bin/env python3
"""gpu0_want (orchestrator order '13:05' ET Nov 16, pp-ingest's request R13): a build's GPU0 service says it wants the
card. A want counts while it is fresh, each service keeps its own, and done() clears it. Nothing here touches the GPU
or the lease."""
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu0_want as W  # noqa: E402


class TestWant(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="want_")
        self.addCleanup(shutil.rmtree, self.d)
        p = mock.patch.object(W, "DIR", os.path.join(self.d, "want"))
        p.start()
        self.addCleanup(p.stop)

    def test_a_want_counts_while_fresh_and_done_clears_it(self):
        self.assertEqual(W.wanted(), [])                                # not even the directory yet
        W.want("stand_alone_scorer")
        self.assertEqual(W.wanted(), ["stand_alone_scorer"])
        W.want("lock_precheck")
        self.assertEqual(W.wanted(), ["lock_precheck", "stand_alone_scorer"])
        W.done("stand_alone_scorer")
        W.done("stand_alone_scorer")                                    # twice: no error
        self.assertEqual(W.wanted(), ["lock_precheck"])

    def test_a_stale_want_does_not_count(self):
        W.want("stand_alone_scorer")
        old = time.time() - W.FRESH_S - 1                               # a service that died 91 s ago
        os.utime(os.path.join(W.DIR, "stand_alone_scorer.json"), (old, old))
        self.assertEqual(W.wanted(), [])
        self.assertEqual(W.wanted(now=old + 1), ["stand_alone_scorer"])
        W.want("stand_alone_scorer")                                    # the service is back: fresh again
        self.assertEqual(W.wanted(), ["stand_alone_scorer"])

    def test_names_are_checked_and_strays_ignored(self):
        for bad in ("", "../x", "Scorer", "a b", "x" * 41, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    W.want(bad)
        os.makedirs(W.DIR)
        for stray in ("notes.txt", "Bad Name.json", "x.json.123.tmp"):
            open(os.path.join(W.DIR, stray), "w").close()
        self.assertEqual(W.wanted(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
