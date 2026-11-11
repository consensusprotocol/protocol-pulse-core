#!/usr/bin/env python3
"""DEC-1 (orchestrator, delegated by PBX, 2026-11-11): the gates PBX's approved v2f reference failed
(G3c, G5, G8, G9) are calibrated to the reference's own measured worst value per format, no margin.
Each test: the frozen reference PASSES, and a fixture just beyond it FAILS. The reference is read only;
modified copies are written to a temp dir. Run: python3 -m pytest -q pipeline/test_dec1_calibration.py"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, os.path.join(REPO, "segment_v1"))
sys.path.insert(0, PIPELINE)                      # run_fresh (no module name is shared with segment_v1)
REF = os.path.join(REPO, "references", "v2f_2026-11-06", "run")
OUT = {"16x9": os.path.join(REF, "out", "segment.mp4"), "9x16": os.path.join(REF, "out", "segment_vertical.mp4")}
MAN = {f: os.path.join(REF, "qa", f"concat_manifest_{f}.json") for f in OUT}
HAVE_REF = all(os.path.exists(p) for p in list(OUT.values()) + list(MAN.values()))


def Q():
    import qa_gates
    return qa_gates


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def segs(fmt):
    return json.load(open(MAN[fmt]))["segments"]


def g8_sources(fmt):
    """Production wiring (run_fresh.stage_gates): 16:9 -> prepared clips, 9:16 -> vertical clips."""
    pre = "final" if fmt == "16x9" else "vert"
    return {c: os.path.join(REF, "qa", f"{pre}_{c}.mp4") for c in ("hook", "clip_01", "clip_02", "clip_03")}


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, timeout=600)


@unittest.skipUnless(HAVE_REF, "frozen v2f reference not present")
class TestDec1(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="dec1_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_constants_are_the_reference_measurements(self):
        q = Q()
        self.assertEqual(q.G3C_VALLEY_DEPTH_DB, {"16x9": 11.63, "9x16": 11.65})
        self.assertEqual(q.G5_TRUE_PEAK_MAX_DBFS, {"16x9": -2.0, "9x16": -1.3})
        self.assertEqual(q.G8_SHARPNESS_FLOOR, {"16x9": 27.56, "9x16": 10.84})
        # DEC-12a (orchestrator 2026-11-11 14:45) replaced DEC-1's G9 floors (14.33 / 14.77): v2f's measured tail
        # luma minus the MEASURED re-encode spread of the locked outro (test_g9_floor.py proves the derivation)
        self.assertEqual(q.G9_LUMA_FLOOR, {"16x9": 14.2857, "9x16": 14.7315})

    def test_reference_passes_every_calibrated_gate(self):
        q = Q()
        for fmt in OUT:
            self.assertTrue(quiet(q.gate_g3c, OUT[fmt], segs(fmt), self.tmp, fmt=fmt)[0], f"G3c {fmt}")
            self.assertTrue(quiet(q.gate_g5, OUT[fmt], fmt)[0], f"G5 {fmt}")
            self.assertTrue(quiet(q.gate_g8, OUT[fmt], segs(fmt), self.tmp, source_clips=g8_sources(fmt),
                                  fmt=fmt)[0], f"G8 {fmt}")
            self.assertTrue(quiet(q.gate_g9, OUT[fmt], self.tmp, fmt=fmt)[0], f"G9 {fmt}")

    def test_g3c_just_beyond_fails(self):
        # the hook's last 150 ms 1 dB louder: the tail rise crosses speech - 11.63 dB
        q = Q()
        hook = next(s for s in segs("16x9") if s["label"] == "hook")
        t0 = hook["end"] - 0.15
        p = os.path.join(self.tmp, "g3c.mp4")
        ffmpeg("-i", OUT["16x9"], "-c:v", "copy", "-af",
               f"volume=enable='between(t,{t0:.3f},{hook['end']:.3f})':volume=1.122", "-c:a", "aac", "-b:a", "192k", p)
        ok, table = quiet(q.gate_g3c, p, segs("16x9"), self.tmp, fmt="16x9")
        self.assertFalse(next(r for r in table if r["segment"] == "hook")["pass"])

    def test_g5_just_beyond_fails(self):
        q = Q()
        p = os.path.join(self.tmp, "g5.mp4")
        # +1.5 dB (an AAC re-encode moves inter-sample peaks; loudness stays within -14 +/- 1)
        ffmpeg("-i", OUT["9x16"], "-c:v", "copy", "-af", "volume=1.5dB", "-c:a", "aac", "-b:a", "192k", p)
        ok, d = quiet(q.gate_g5, p, "9x16")
        self.assertFalse(d["tp_ok"], d)

    def _static(self, name, target_var, w, h):
        """Lossless 1 s static video whose centre Laplacian variance (G8's measure) ~= target_var."""
        import cv2
        import numpy as np
        q = Q()
        base = cv2.GaussianBlur(np.random.default_rng(1).normal(0, 1, (h, w)).astype(np.float32), (0, 0), 3)
        gain = 10.0
        for _ in range(40):
            img = np.clip(128 + gain * base, 0, 255).astype(np.uint8)
            gain *= (target_var / max(q._laplacian_centre(img), 1e-6)) ** 0.5
        img = np.clip(128 + gain * base, 0, 255).astype(np.uint8)
        png, out = os.path.join(self.tmp, name + ".png"), os.path.join(self.tmp, name + ".mkv")
        cv2.imwrite(png, img)
        ffmpeg("-loop", "1", "-i", png, "-t", "1", "-r", "24", "-c:v", "ffv1", "-pix_fmt", "gray", out)
        return out, q._laplacian_centre(img)

    def test_g8_just_beyond_fails(self):
        # With DEC-3 the floor binds only when the SOURCE is above it, so the fixture is: source just
        # above the calibrated floor, output just below it, render/source ratio well above 0.85.
        q = Q()
        for fmt, (w, h) in (("16x9", (1920, 1080)), ("9x16", (1080, 1920))):
            floor = q.G8_SHARPNESS_FLOOR[fmt]
            src, sv = self._static(f"src_{fmt}", floor + 1.0, w, h)
            below, bv = self._static(f"below_{fmt}", floor - 0.5, w, h)
            above, av = self._static(f"above_{fmt}", floor + 0.5, w, h)
            self.assertTrue(bv < floor < av < sv and bv / sv >= 0.85, (fmt, sv, bv, av))
            seg = [{"label": "clip_x", "type": "talking_head", "start": 0.0, "end": 1.0}]
            ok_b, tb = quiet(q.gate_g8, below, seg, self.tmp, source_clips={"clip_x": src}, fmt=fmt)
            ok_a, ta = quiet(q.gate_g8, above, seg, self.tmp, source_clips={"clip_x": src}, fmt=fmt)
            self.assertFalse(ok_b, (fmt, tb))
            self.assertFalse(tb[0]["floor_pass"], (fmt, tb))
            self.assertTrue(tb[0]["degradation_pass"], (fmt, tb))
            self.assertTrue(ok_a, (fmt, ta))

    def test_g9_just_beyond_fails(self):
        q = Q()
        p = os.path.join(self.tmp, "g9.mp4")
        ffmpeg("-sseof", "-3", "-i", OUT["16x9"], "-vf", "eq=brightness=-0.006", "-c:v", "libx264", "-crf", "12",
               "-preset", "veryfast", "-c:a", "copy", p)
        ok, d = quiet(q.gate_g9, p, self.tmp, fmt="16x9")
        self.assertFalse(ok, d)
        self.assertEqual(str(d["luma_ok"]), "False", d)          # numpy bool or bool; None/0 fail
        self.assertLess(d["mean_luma"], q.G9_LUMA_FLOOR["16x9"], d)


class TestTailRows(unittest.TestCase):
    """Heimdall DEC-1 audit: G9_tail is the calibrated gate alone; a conform fallback (not the locked
    outro the floor was measured on) fails its own row, so the run still holds."""

    def test_luma_pass_on_a_fallback_outro_fails_outro_locked(self):
        import run_fresh as rf          # verdict_for: run_fresh's existing verdict (HOLD on any FAIL row)
        self.assertEqual(rf.tail_rows(True, True), {"G9_tail": "PASS", "outro_locked": "FAIL"})
        self.assertEqual(rf.verdict_for(rf.tail_rows(True, True))[0], rf.VERDICT_HOLD)

    def test_rows_follow_their_own_inputs(self):
        import run_fresh as rf
        self.assertEqual(rf.tail_rows(True, False), {"G9_tail": "PASS", "outro_locked": "PASS"})
        self.assertEqual(rf.tail_rows(False, False), {"G9_tail": "FAIL", "outro_locked": "PASS"})
        self.assertEqual(rf.verdict_for(rf.tail_rows(False, False))[0], rf.VERDICT_HOLD)   # luma fail holds
        self.assertEqual(rf.verdict_for(rf.tail_rows(True, False))[0], rf.VERDICT_CANDIDATE)


if __name__ == "__main__":
    unittest.main()
