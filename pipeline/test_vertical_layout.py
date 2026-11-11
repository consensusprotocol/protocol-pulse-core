#!/usr/bin/env python3
"""DEC-2 / DEC-5 (orchestrator, delegated by PBX, 2026-11-11): the 9:16 is a speaker-centred reframe by
default; 2-3 people get stacked bands; the safe frame only for a shared screen ('screen') or an
unidentifiable speaker, flagged. Layouts are per SHOT. Fixture: the Nov 10 prepared clips at 360p
(face-area rules are fractions of the frame, so they are scale-invariant).
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_vertical_layout.py"""
import copy
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110", "video")
CLIP = {c: os.path.join(FIX, f"prepared_{c}_360p.mp4") for c in ("hook", "clip_01", "clip_02")}


def V():
    import vertical_layout
    return vertical_layout


class TestClassifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plans = {c: V().classify(p) for c, p in CLIP.items()}

    def classes(self, c):
        return [s["class"] for s in self.plans[c]["shots"]]

    def test_chart_with_face_cam_is_screen(self):           # DataDash hook (face-cam 0.4 % of frame)
        self.assertEqual(self.classes("hook"), ["screen"])
        self.assertTrue(self.plans["hook"]["flagged"])

    def test_standing_host_is_single(self):                  # Yahoo Finance (face 1.6 % of frame)
        self.assertEqual(self.classes("clip_02"), ["single"])
        self.assertFalse(self.plans["clip_02"]["flagged"])

    def test_cutaways_are_their_own_shots(self):             # Natalie: chart | talking head | Capitol
        self.assertEqual(self.classes("clip_01"), ["screen", "single", "screen"])
        sh = self.plans["clip_01"]["shots"]
        self.assertAlmostEqual(sh[1]["start"], 105 / 24, places=3)    # the cut frame, not a sample time
        self.assertAlmostEqual(sh[2]["start"], 393 / 24, places=3)


class TestLayoutTruth(unittest.TestCase):
    """G4s: a label must match the re-measured picture (never the label itself)."""

    @classmethod
    def setUpClass(cls):
        cls.plans = {c: V().classify(p) for c, p in CLIP.items()}

    def test_correct_labels_pass(self):
        ok, table = V().gate_g4s(self.plans, CLIP)
        self.assertTrue(ok, [r for r in table if not r["pass"]])

    def test_talking_head_mislabelled_as_screen_fails(self):           # DEC-2 must-fail
        bad = copy.deepcopy(self.plans)
        for sh in bad["clip_02"]["shots"]:
            sh["class"] = "screen"
        ok, table = V().gate_g4s(bad, CLIP)
        self.assertFalse(ok)
        self.assertFalse(next(r for r in table if r["segment"] == "clip_02")["label_ok"])

    def test_screen_mislabelled_as_single_fails(self):
        bad = copy.deepcopy(self.plans)
        bad["hook"]["shots"][0].update({"class": "single", "face_cx": 320})
        ok, table = V().gate_g4s(bad, CLIP)
        self.assertFalse(next(r for r in table if r["segment"] == "hook")["label_ok"])


class TestStackGeometry(unittest.TestCase):
    """Stacked bands: every face lies inside its own band, at 40 % of the band height unless the frame
    edge clamps it (band positions are measured per face, never a fixed height)."""

    def crops(self, vf):
        import re
        return [tuple(int(v) for v in m) for m in re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", vf)]

    def test_each_face_inside_its_band(self):
        import render_vertical as RV
        for cls, cxs, cys in (("stack2", [500, 1400], [380, 520]), ("stack3", [300, 960, 1650], [300, 650, 120])):
            crops = self.crops(RV._shot_vf({"class": cls, "band_cx": cxs, "band_cy": cys}, 1920, 1080))
            self.assertEqual(len(crops), int(cls[-1]))
            for (w, h, x, y), cx, cy in zip(crops, cxs, cys):
                self.assertTrue(x <= cx <= x + w and y <= cy <= y + h, (cls, (w, h, x, y), cx, cy))
                if 0 < y and y + h < 1080:
                    self.assertAlmostEqual((cy - y) / h, 0.4, delta=0.01)


class TestCaptionNote(unittest.TestCase):
    """DEC-2/DEC-5: a safe frame is flagged in the caption with its layout, never silent."""

    def edl(self, hook_shots, clip_shots):
        mk = lambda shots: {"shots": shots, "flagged": any(s["flagged"] for s in shots)}
        return {"hook": {"channel": "DataDash", "vertical_layout": mk(hook_shots)},
                "clips": [{"index": 1, "channel": "Natalie Brunell", "vertical_layout": mk(clip_shots)}]}

    def shot(self, cls, a, b):
        return {"start": a, "end": b, "class": cls, "flagged": cls in ("screen", "uncertain")}

    def test_every_safe_frame_shot_is_named_with_its_layout(self):
        note = V().layout_note(self.edl([self.shot("screen", 0, 9.4)],
                                        [self.shot("screen", 0, 4.375), self.shot("single", 4.375, 16.375),
                                         self.shot("uncertain", 16.375, 17.2)]))
        self.assertIn("9:16 SAFE FRAME hook (DataDash): layout=screen 0.00-9.40 s", note)
        self.assertIn("clip_01 (Natalie Brunell): layout=screen 0.00-4.38 s; "
                      "layout=uncertain (speaker unidentified) 16.38-17.20 s", note)
        self.assertNotIn("single", note)

    def test_all_reframed_is_silent_and_unmeasured_is_reported(self):
        self.assertEqual(V().layout_note(self.edl([self.shot("single", 0, 9)], [self.shot("stack2", 0, 15)])), "")
        e = self.edl([self.shot("single", 0, 9)], [])
        del e["clips"][0]["vertical_layout"]
        self.assertIn("clip_01 (Natalie Brunell): layout NOT MEASURED", V().layout_note(e))


class TestSafeFrameTruth(unittest.TestCase):
    """G4s on the 9:16 picture (CPU encode). D5 must-fail: Yahoo Finance's standing host (single) shown
    as the letterbox safe frame, as the Nov 10 9:16 did; must-pass: the same shot as a speaker crop."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="g4s_")
        cls.src = os.path.join(cls.tmp, "clip_02.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", CLIP["clip_02"], "-t", "4", "-vf", "scale=1920:1080",
                        "-r", "24", "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-an", cls.src],
                       check=True)
        cls.plan = V().classify(cls.src)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def render(self, vf, name):
        out = os.path.join(self.tmp, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.src, "-vf", vf, "-c:v", "libx264", "-crf", "20",
                        "-preset", "veryfast", "-pix_fmt", "yuv420p", out], check=True)
        return out

    def g4s(self, vert):
        return V().gate_g4s({"clip_02": self.plan}, {"clip_02": self.src}, vert_final=vert,
                            vert_segments=[{"label": "clip_02", "start": 0.0}])

    def test_talking_head_shown_as_safe_frame_fails(self):        # D5 must-fail
        import render_vertical as RV
        self.assertEqual([s["class"] for s in self.plan["shots"]], ["single"])
        ok, table = self.g4s(self.render(RV.LETTERBOX_VF, "letterbox.mp4"))
        self.assertFalse(ok, table)
        self.assertTrue(table[0]["vertical_safe_frame"], table)

    def test_talking_head_cropped_passes(self):
        import render_vertical as RV
        ok, table = self.g4s(self.render(RV._shot_vf(self.plan["shots"][0], 1920, 1080), "crop.mp4"))
        self.assertTrue(ok, table)
        self.assertFalse(table[0]["vertical_safe_frame"], table)


@unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "NVENC render needs GPU0")
class TestReframeAuto(unittest.TestCase):
    """End to end on a 1080p copy of Natalie's clip: 1080x1920, same duration, the chart and Capitol
    shots are safe frames, the talking-head shot is a crop (no blurred bands)."""

    def test_per_shot_render(self):
        import cv2
        import render_vertical as RV
        tmp = tempfile.mkdtemp(prefix="reframe_")
        try:
            src = os.path.join(tmp, "clip_01.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", CLIP["clip_01"], "-f", "lavfi", "-i",
                            "anullsrc=r=48000:cl=stereo", "-shortest", "-vf", "scale=1920:1080", "-r", "24",
                            "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-c:a", "aac", src], check=True)
            plan = V().classify(src)
            out = os.path.join(tmp, "vert.mp4")
            ok, summary = RV.reframe_auto(src, out, "clip_01", plan)
            self.assertTrue(ok, summary)
            w, h, fps, dur = V()._probe(out)
            self.assertEqual((w, h), (1080, 1920))
            self.assertAlmostEqual(dur, plan["duration"], delta=1 / 24 + 0.03)
            for sh in plan["shots"]:
                tm = (sh["start"] + sh["end"]) / 2
                safe, m = V().is_safe_frame(V()._frame(out, tm), V()._frame(src, tm))
                self.assertEqual(safe, sh["class"] in V().SAFE_FRAME, (sh, m))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
