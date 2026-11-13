#!/usr/bin/env python3
"""Law L-x for V1 (order 2026-11-12 '20:30' (d)): visual_check._call_any routes a model named 'xai:<name>' to the xAI
vendor and every other name to the Heimdall gateway, unchanged; a garbage, empty or failed reply from the new route is
'no answer' (fail closed). There is no local vision route: GPU0's Ollama is called only through
story_semantics.LocalLLM (law L-r; test_gpu0 TestNoDirectLoaders), and the local candidate gemma3:27b failed the V1
cases (0 of 5 must-fail caught). The candidates' QUALITY is measured on the labelled V1 cases before any is seated."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import visual_check as VC  # noqa: E402


class TestVendorRoute(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.saved = (VC._call, VC._request, VC._call_xai)
        VC._call_xai = lambda p, t, m, timeout: self.calls.append(("xai", m)) or ('{"answers": {}}', {})
        VC._request = lambda p, t, m: ("req", m)
        VC._call = lambda req, timeout: self.calls.append(("heimdall", req[1])) or ('{"answers": {}}', {})

    def tearDown(self):
        VC._call, VC._request, VC._call_xai = self.saved

    def test_xai_names_go_to_xai_and_every_other_name_to_heimdall(self):
        VC._call_any("x.jpg", "q", "xai:grok-4.3", 5)
        for m in VC.VISION_MODELS:
            VC._call_any("x.jpg", "q", m, 5)
        self.assertEqual(self.calls, [("xai", "xai:grok-4.3")] + [("heimdall", m) for m in VC.VISION_MODELS])

    def test_no_local_route_and_the_default_panel_is_unchanged(self):
        self.assertFalse(hasattr(VC, "_call_local"))
        self.assertEqual(VC.VISION_MODELS, ("qwen/qwen3.8-27b", "nvidia/nemotron-3.5-super-vl"))

    def test_an_unparseable_empty_or_failed_reply_from_the_new_route_is_no_answer(self):
        """Audit batch 43 cycle 3 (consensus): garbage, an empty reply or a route error give no answers, and every
        checklist line is then 'missing' (not ok)."""
        def boom(*a, **k):
            raise OSError("route down")
        for name, reply in (("garbage", lambda p, t, m, timeout: ("I think it looks fine!", {})),
                            ("empty", lambda p, t, m, timeout: ("", {})), ("error", boom)):
            VC._call_xai = reply
            answers, raw = VC.ask_vision("x.jpg", "9x16", model="xai:grok-4.3", attempts=2)
            self.assertEqual(answers, {}, name)
            self.assertIn("unparseable", raw, name)
            ok, rows = VC.verdict(answers, "9x16")
            self.assertFalse(ok)
            self.assertTrue(all(r["answer"] == "missing" for r in rows.values()), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
