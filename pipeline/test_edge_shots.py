#!/usr/bin/env python3
"""G19 EDGE SHOTS (recut run 6 V1): no hard shot change inside a talking head outside its speech, measured on
the finished video. Must-fail on run 6's own final (Natalie's next shot in clip_02's last 3 frames); must-pass
on the replay whose prepare held her shot (runs/..._replay_*); synthetic cases for the rules.
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_edge_shots.py"""
import glob
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import edge_shots as E  # noqa: E402
from test_shot_snap import _clip  # noqa: E402

RUN6 = os.path.join(REPO, "runs", "pinned_20261111_123750")


class TestSynthetic(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="g19_")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_rules(self):
        final = _clip(os.path.join(self.tmp, "f.mp4"), [("red", 0), ("blue", 60), ("green", 72)], dur=6.0)
        segs = [{"label": "hook", "type": "talking_head", "start": 0.0, "end": 3.0},
                {"label": "clip_01", "type": "talking_head", "start": 3.0, "end": 6.0}]
        rec = {"hook": {"speech_on_s": 0.3, "speech_off_s": 2.2}, "clip_01": {"speech_on_s": 0.3, "speech_off_s": 2.7}}
        ok, rows = E.gate_g19(final, segs, rec, 24)
        self.assertFalse(ok)                                   # blue at 2.5 s: after the hook's last word
        self.assertEqual(rows[0]["foreign_shot_at"], [2.5])
        self.assertTrue(rows[1]["pass"])                       # green at 3.0 s is the cut itself
        ok, rows = E.gate_g19(final, segs, {"hook": rec["hook"]}, 24)
        self.assertFalse(rows[1]["pass"])                      # no speech record: fail closed ...
        ok, rows = E.gate_g19(final, segs[1:], {}, 24)
        self.assertFalse(ok)                                   # ... and the gate fails


@unittest.skipUnless(os.path.exists(os.path.join(RUN6, "out", "segment.mp4")), "run 6 not on this machine")
class TestRun6(unittest.TestCase):
    """Run 6's speech spans from its own cut table (pause_in.end / pause_out.start relative to cut_in)."""

    def records(self, run):
        cuts = json.load(open(os.path.join(run, "cuts_final.json")))
        return {c["clip_id"]: {"speech_on_s": c["pause_in"]["end"] - c["cut_in"] + float(c.get("lead_in_pad_s") or 0),
                               "speech_off_s": c["pause_out"]["start"] - c["cut_in"] + float(c.get("lead_in_pad_s") or 0)}
                for c in cuts}

    def test_run6_final_fails_at_clip_02_and_the_snapped_replay_passes(self):
        segs = json.load(open(os.path.join(RUN6, "qa", "concat_manifest_16x9.json")))["segments"]
        ok, rows = E.gate_g19(os.path.join(RUN6, "out", "segment.mp4"), segs, self.records(RUN6), 24)
        self.assertFalse(ok, rows)
        bad = {r["segment"]: r["foreign_shot_at"] for r in rows if not r["pass"]}
        self.assertEqual(list(bad), ["clip_02"])
        self.assertTrue(bad["clip_02"] and all(41.1 < t < 41.34 for t in bad["clip_02"]), bad)   # NVIDIA/AMD/MICRON
        rep = sorted(glob.glob(RUN6 + "_replay_*"))
        if rep and os.path.exists(os.path.join(rep[-1], "out", "segment.mp4")):
            segs2 = json.load(open(os.path.join(rep[-1], "qa", "concat_manifest_16x9.json")))["segments"]
            ok2, rows2 = E.gate_g19(os.path.join(rep[-1], "out", "segment.mp4"), segs2, self.records(rep[-1]), 24)
            self.assertTrue(ok2, rows2)


if __name__ == "__main__":
    unittest.main()
