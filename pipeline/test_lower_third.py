#!/usr/bin/env python3
"""RULING 93 (orchestrator 2026-11-13 '23:59'): DEC-12d is measured per clip, not per channel. The render side:
- the 9:16 single crop must not cut a lower third mid-word where a crop inside the face-safe range keeps every element
  wholly in or wholly out (vertical_layout.lower_third_spans / single_crop; render_vertical._shot_vf reads crop_x);
- G10 runs on every clip (qa_gates.g10_clip_ids), still monitoring.
Must-fail on the published 0c68b589 CNBC clip (the protected first-pass reference's prepared clip_01): the old crop
(x 94, face-centred) cuts the 'CNBC EXCLUSIVE' tag; before the banner a face-safe crop clears it and the rule takes it;
over the whole shot none does (the banner from 6.2 s), so the old crop stays and the shot is recorded cut.
No GPU (CUDA_VISIBLE_DEVICES=). Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES= python3 -m pytest -q pipeline/test_lower_third.py"""
import json
import os
import sys
import unittest

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
sys.path.insert(1, os.path.join(REPO, "segment_v1"))
import qa_gates  # noqa: E402
import render_vertical as RV  # noqa: E402
import vertical_layout as VL  # noqa: E402

REF = "/home/ultron/protocol_pulse/references/pulse_fresh_2026-11-13"
CLIP = os.path.join(REF, "qa", "final_clip_01.mp4")
W, H, CW = 1920, 1080, 607
FACE = [0.04, 397, 358]                 # [area fraction, cx, cy]: the CNBC speaker (box side ~288 px)


class TestSingleCrop(unittest.TestCase):
    def test_no_lower_third_keeps_todays_crop(self):
        x, rec = VL.single_crop([FACE], [], W, H)
        self.assertEqual((x, rec["moved_px"], rec["cut"]), (94, 0, False))           # face_cx - 303

    def test_a_cut_word_moves_the_crop_to_the_nearest_face_safe_clear_x(self):
        x, rec = VL.single_crop([FACE], [(70, 240)], W, H)                          # the tag under the left edge
        self.assertFalse(rec["cut"])
        self.assertTrue(x <= 70 or x >= 240)
        lo, hi = rec["face_safe_x"]
        self.assertTrue(lo <= x <= hi)
        side = (FACE[0] * W * H) ** 0.5                                               # the face stays inside, with
        self.assertGreaterEqual(FACE[1] - side / 2 - x, VL.FACE_MARGIN_FRAC * CW - 1)   # its margin
        self.assertGreaterEqual(x + CW - (FACE[1] + side / 2), VL.FACE_MARGIN_FRAC * CW - 1)

    def test_no_clear_face_safe_crop_keeps_todays_and_records_the_cut(self):
        x, rec = VL.single_crop([FACE], [(0, 1900)], W, H)                            # one element wider than any crop
        self.assertEqual((x, rec["cut"], rec["moved_px"]), (94, True, 0))

    def test_no_face_samples_gives_no_x_and_the_renderer_keeps_its_own(self):   # batch 74 c1 consensus
        x, rec = VL.single_crop([], [(70, 240)], W, H)
        self.assertEqual((x, rec["why"]), (None, "no face samples"))
        self.assertIn("crop=607:1080:94:0", RV._shot_vf({"class": "single", "face_cx": 397, "crop_x": x}, W, H))

    def test_the_renderer_reads_the_plans_crop_x(self):
        shot = {"class": "single", "face_cx": 397, "crop_x": 21}
        self.assertIn("crop=607:1080:21:0", RV._shot_vf(shot, W, H))
        self.assertIn("crop=607:1080:94:0", RV._shot_vf({"class": "single", "face_cx": 397}, W, H))   # no plan x
        self.assertIn("crop=607:1080:94:0", RV._shot_vf(dict(shot, crop_x=5000), W, H))  # out of range: today's


class TestG10OnEveryClip(unittest.TestCase):
    def test_every_talking_head_whatever_its_channel(self):
        segs = [{"label": "hook", "type": "talking_head"}, {"label": "vo_intro", "type": "vo"},
                {"label": "clip_01", "type": "talking_head"}, {"label": "shoutout", "type": "shoutout"}]
        self.assertEqual(qa_gates.g10_clip_ids(segs), {"hook", "clip_01"})


@unittest.skipUnless(os.path.exists(CLIP), "the protected first-pass reference's prepared clip_01")
class TestPublishedCnbcClip(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import cv2
        lay = json.load(open(os.path.join(REF, "VERTICAL_LAYOUT.json")))["clip_01"]
        cls.faces = [s["faces"][0] for s in lay["samples"] if s.get("faces")]
        cap = cv2.VideoCapture(CLIP)
        fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
        cls.spans = {}
        for s in lay["samples"]:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(s["t"] * fps)))
            ok, fr = cap.read()
            if ok:
                cls.spans[s["t"]] = VL.lower_third_spans(fr)
        cls.published_x = max(0, min(W - CW, int(np.median([f[1] for f in cls.faces])) - CW // 2))

    def spans_until(self, t1):
        return sorted({x for t, sp in self.spans.items() if t < t1 for x in sp})

    def test_the_published_crop_cuts_the_lower_third(self):
        self.assertEqual(self.published_x, 94)
        cut = [s for s in self.spans_until(6.0) if s[0] < 94 < s[1] or s[0] < 94 + CW < s[1]]
        self.assertTrue(cut, "the old crop cuts the CNBC EXCLUSIVE tag")

    def test_before_the_banner_the_rule_clears_it(self):
        x, rec = VL.single_crop(self.faces, self.spans_until(6.0), W, H)
        self.assertFalse(rec["cut"], rec)
        self.assertNotEqual(x, self.published_x)
        self.assertTrue(7 <= x <= 33, (x, rec))                                      # measured DoD 23:51

    def test_over_the_whole_shot_no_crop_clears_it_and_the_cut_is_recorded(self):
        x, rec = VL.single_crop(self.faces, self.spans_until(99.0), W, H)
        self.assertEqual((x, rec["cut"]), (self.published_x, True))
        self.assertTrue(rec["cut_spans"])


if __name__ == "__main__":
    unittest.main()
