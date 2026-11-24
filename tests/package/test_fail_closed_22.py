"""THE VERIFIER'S ROW 22 (FIX_VERIFICATION_2026-11-24, ruling 160 (2a): "FAIL CLOSED ON HARD CHECKS"): the exclusion
screen (ad read, not about Bitcoin) given NO answer by any model excludes the clip, unmeasured (UNVERIFIED: never a
pass). The code was right, and nothing caught it breaking: changed to KEEP a clip when no model answers, every project
test still passed (the verifier's mutation res22b). Here every way the model fails is driven through the real
moments.exclusion_verdict with only its model call (providers.call_parsed) stubbed, in both passes."""
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "pipeline"))
import moments as M  # noqa: E402
import providers as P  # noqa: E402

CLIP = "Bitcoin is the hardest money ever made, and the market is only starting to price that in."


class TestNoAnswerExcludes(unittest.TestCase):
    def test_every_failure_excludes_unmeasured(self):
        for err in (P.ProviderError("exclusion_verdict: every back-end unavailable"), P.SpendLimit("the stop"),
                    ValueError("the verdict does not match its contract"), TypeError("None")):
            for soft in (False, True):                  # the clean pass and the never-empty pass (ruling 146 (3))
                with mock.patch.object(P, "call_parsed", mock.Mock(side_effect=err)) as call:
                    v = M.exclusion_verdict(None, CLIP, "The show is back.", "", before_marker_soft=soft)
                self.assertEqual(call.call_count, 1, (err, soft))          # the model was asked, and failed
                self.assertEqual((v["verdict"], v["measured"], v["backend"]), ("exclude", False, None), (err, soft))
                self.assertIn("no readable verdict", v["why"])

    def test_an_answer_still_keeps(self):
        """The control: the same clip with an answer in contract is kept (the stub reaches the real parse)."""
        import types

        def fake(router, role, prompt, parse, n, seed, avoid_model=None):
            return types.SimpleNamespace(backend="heimdall:qwen", replayed=False), parse(
                '{"risks": [], "about_bitcoin": "yes", "why": "the speaker\'s own view"}')
        with mock.patch.object(P, "call_parsed", fake):
            v = M.exclusion_verdict(None, CLIP, "", "")
        self.assertEqual((v["verdict"], v["measured"]), ("keep", True))


if __name__ == "__main__":
    unittest.main()
