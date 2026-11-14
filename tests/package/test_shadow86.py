#!/usr/bin/env python3
"""RULING 86 (orchestrator 21:18 Nov 13): the shadow's side-by-side (tests/package/shadow86.py). Offline: a
synthetic SHADOW86.jsonl in a temporary build directory and a temporary streak file."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shadow86 as SH  # noqa: E402

CLIP = "Bitcoin only dropped like five, six percent while tech stocks fell much further that week."
PROMPT = ('Judge this moment. <before>...</before> <moment>"' + CLIP + '"</moment> Return {"risks": [], '
          '"about_bitcoin": "yes|no|uncertain", "why": "..."}')


def line(h, g, prompt=PROMPT):
    return {"role": "exclusion_verdict", "prompt": prompt, "deciding": {"backend": "heimdall:z-ai/glm-5.3-flash",
            "text": json.dumps(h)}, "shadow": {"backend": "xai:grok", "text": json.dumps(g), "usd_reported": 0.01}}


KEEP = {"risks": [], "about_bitcoin": "yes", "why": "w"}
EXCL = {"risks": ["imperative"], "about_bitcoin": "yes", "why": "w"}


class TestShadow(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.d.name, "SHADOW86.json")

    def tearDown(self):
        self.d.cleanup()

    def build(self, name, lines, pin):
        b = os.path.join(self.d.name, name)
        os.makedirs(b)
        with open(os.path.join(b, "SHADOW86.jsonl"), "w") as f:
            f.write("".join(json.dumps(x) + "\n" for x in lines))
        res = {"package": {"segments": [{"text": CLIP}]}, "pin": {"path": "x"}} if pin else \
            {"package": {"segments": [{"text": CLIP}]}}           # a package the pin stage refused is no pin
        return b, res

    def test_a_pin_grok_would_have_stopped_and_the_streak(self):
        b, res = self.build("b1", [line(KEEP, KEEP), line(KEEP, EXCL)], pin=True)
        s = SH.report(b, res, path=self.state)
        self.assertEqual((s["differ"], s["on_pin_differ"], s["would_seal_under_grok"], s["clean_streak"]),
                         (1, 1, False, 0))
        md = open(os.path.join(b, "SHADOW86.md")).read()
        self.assertIn("| exclusion | moment | True | False | looser | yes |", md)   # Heimdall passed what Grok failed
        for i in range(3):                                                           # three clean pins in a row
            b, res = self.build(f"c{i}", [line(KEEP, KEEP)], pin=True)
            self.assertEqual(SH.report(b, res, path=self.state)["clean_streak"], i + 1)
        self.assertEqual(SH.clean_streak(self.state), 3)
        b, res = self.build("n", [line(KEEP, EXCL)], pin=False)                      # no pin: the streak stays
        self.assertIsNone(SH.report(b, res, path=self.state)["would_seal_under_grok"])
        self.assertEqual(SH.clean_streak(self.state), 3)

    def test_unreadable_answers_and_missing_shadows_are_counted_never_clean(self):
        bad = dict(line(KEEP, KEEP), shadow={"backend": "xai:grok", "error": "Unavailable: xAI down"})
        b, res = self.build("b", [bad, line(KEEP, KEEP)], pin=True)
        s = SH.report(b, res, missing=1, path=self.state)
        self.assertEqual((s["not_compared"], s["missing"], s["clean_streak"]), (1, 1, 0))
        self.assertEqual(SH.clean_streak(os.path.join(self.d.name, "none.json")), 0)

    def test_missing_shadows_on_a_pin_never_say_it_would_seal(self):
        """Audit 0108 C1 (glm): a sealed pin whose shadow answers are all missing was verified by nothing."""
        b, res = self.build("b9", [{"role": "exclusion_verdict", "prompt": PROMPT,
                                    "deciding": {"backend": "heimdall:z-ai/glm-5.3-flash", "text": json.dumps(KEEP)}}],
                            pin=True)
        out = SH.report(b, res, missing=1, path=self.state)
        self.assertIsNone(out["would_seal_under_grok"])

    def test_a_sealed_spotlight_is_a_pin_too(self):
        """RULING 90: a spotlight pin is judged by the shadow like a medley pin (ruling 86's "the first pin sealed")."""
        seg = [{"text": CLIP}]
        self.assertEqual(SH.pin_texts({"pin": None, "spotlight_pin": {"story_id": "s"},
                                       "spotlight": {"package": {"segments": seg}}}),
                         SH.pin_texts({"pin": {"story_id": "m"}, "package": {"segments": seg}}))
        self.assertEqual(len(SH.pin_texts({"pin": {"story_id": "m"}, "package": {"segments": seg},
                                           "spotlight_pin": {"story_id": "s"},
                                           "spotlight": {"package": {"segments": seg}}})), 2)
        self.assertEqual(SH.pin_texts({"spotlight": {"package": {"segments": seg}}}), [])   # not sealed: no pin


if __name__ == "__main__":
    unittest.main()
