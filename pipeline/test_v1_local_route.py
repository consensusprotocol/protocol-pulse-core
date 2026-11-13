#!/usr/bin/env python3
"""Law L-x for V1 (order 2026-11-12 '20:30' (d)): visual_check._call_any routes a model named 'ollama:<name>' to the
LOCAL back-end (Ollama on Ultron's GPU0, loaded through gpu0.swap_to under the caller's lease, law L-r) and every
other name to the Heimdall gateway, unchanged. CPU tests: the routing, and that the local route refuses (gpu0
LeaseMissing, a Gpu0Stop that a run turns into a HOLD naming the cause) before any request when the GPU0 lease is
not held. The local model's QUALITY is measured separately, on the labelled V1 cases, before it may sit on the panel."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu0  # noqa: E402
import visual_check as VC  # noqa: E402


class TestLocalRoute(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.saved = (VC._call_local, VC._call, VC._request, VC._call_xai)
        VC._call_local = lambda p, t, m, timeout: self.calls.append(("local", m)) or ('{"answers": {}}', {})
        VC._call_xai = lambda p, t, m, timeout: self.calls.append(("xai", m)) or ('{"answers": {}}', {})
        VC._request = lambda p, t, m: ("req", m)
        VC._call = lambda req, timeout: self.calls.append(("heimdall", req[1])) or ('{"answers": {}}', {})

    def tearDown(self):
        VC._call_local, VC._call, VC._request, VC._call_xai = self.saved

    def test_ollama_names_go_local_xai_names_to_xai_and_every_other_name_to_heimdall(self):
        VC._call_any("x.jpg", "q", VC.LOCAL_VISION, 5)
        VC._call_any("x.jpg", "q", "xai:grok-4.3", 5)
        for m in VC.VISION_MODELS:
            VC._call_any("x.jpg", "q", m, 5)
        self.assertEqual(self.calls, [("local", "ollama:gemma3:27b"), ("xai", "xai:grok-4.3")]
                         + [("heimdall", m) for m in VC.VISION_MODELS])

    def test_an_unparseable_empty_or_failed_reply_from_a_new_route_is_no_answer(self):
        """Audit batch 43 cycle 3 (consensus): the xAI and local replies go through the same fail-closed parsers: garbage,
        an empty reply or a route error give no answers, and every checklist line is then 'missing' (not ok)."""
        def boom(*a, **k):
            raise OSError("route down")
        for name, reply in (("garbage", lambda p, t, m, timeout: ("I think it looks fine!", {})),
                            ("empty", lambda p, t, m, timeout: ("", {})), ("error", boom)):
            for model, attr in (("xai:grok-4.3", "_call_xai"), (VC.LOCAL_VISION, "_call_local")):
                setattr(VC, attr, reply)
                answers, raw = VC.ask_vision("x.jpg", "9x16", model=model, attempts=2)
                self.assertEqual(answers, {}, (name, model))
                self.assertIn("unparseable", raw, (name, model))
                ok, rows = VC.verdict(answers, "9x16")
                self.assertFalse(ok)
                self.assertTrue(all(r["answer"] == "missing" for r in rows.values()), (name, model))

    def test_the_default_panel_is_unchanged(self):
        self.assertEqual(VC.VISION_MODELS, ("qwen/qwen3.8-27b", "nvidia/nemotron-3.5-super-vl"))
        self.assertTrue(VC.LOCAL_VISION.startswith("ollama:") and VC.LOCAL_VISION not in VC.VISION_MODELS)


@unittest.skipIf(gpu0.held(), "a GPU session holds the lease: the refusal is tested in a CPU session")
class TestLocalRouteNeedsTheLease(unittest.TestCase):
    def test_no_lease_no_load_no_request(self):
        import urllib.request
        img = os.path.join(tempfile.mkdtemp(prefix="v1local_"), "f.jpg")
        open(img, "wb").write(b"\xff\xd8\xff\xd9")
        sent, real = [], urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: sent.append(a) or real(*a, **k)   # audit batch 43: count requests
        try:
            with self.assertRaises(gpu0.Gpu0Stop):
                VC._call_local(img, "q", VC.LOCAL_VISION, 5)
            with self.assertRaises(gpu0.Gpu0Stop):                     # not swallowed as a route error: a run HOLDs
                VC.ask_vision(img, "16x9", model=VC.LOCAL_VISION, attempts=1)
        finally:
            urllib.request.urlopen = real
        self.assertEqual(sent, [])                                     # nothing reached Ollama (or anything else)


if __name__ == "__main__":
    unittest.main(verbosity=2)
