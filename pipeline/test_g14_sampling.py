#!/usr/bin/env python3
"""DEC-12e (orchestrator 2026-11-11 14:45): G14 samples only where the transcript has speech, outside declared
transition / VO intervals; an inconclusive sample is re-taken at the nearest speech point; a segment passes
with >= 3 conclusive matching samples and zero conclusive mismatches. Threshold unchanged.
must-pass  the corrected Nov 10 cut (its one inconclusive sample sat in a 0.6 s pause of Yahoo's speech)
must-fail  a real 2-frame (83 ms) AV slip inside a segment
HOLD       a segment with fewer than 3 conclusive samples (its audio silenced)
Run: cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_g14_sampling.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import gates as G  # noqa: E402

RUN = os.path.join(REPO, "runs", "pinned_20261111_172202_replay_cut1329")
NEEDED = ("out/segment.mp4", "qa/g14_manifest_16x9.json", "cuts_final.json")


@unittest.skipUnless(all(os.path.exists(os.path.join(RUN, p)) for p in NEEDED) and os.path.isdir(os.path.join(RUN, "sources"))
                     and os.path.isdir(os.path.join(RUN, "transcripts")), "Nov 11 replay run not on this machine")
class TestG14Sampling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="g14s_")
        cuts = json.load(open(os.path.join(RUN, "cuts_final.json")))

        def words(vid):
            return [{"start": float(w["start"]), "end": float(w["end"])}
                    for w in json.load(open(os.path.join(RUN, "transcripts", f"{vid}.json")))["words"]]
        cls.src = {c["clip_id"]: {"path": os.path.join(RUN, "sources", f"{c['video_id']}.mp4"),
                                  "cut_in": c["cut_in"], "words": words(c["video_id"])} for c in cuts}
        cls.man = os.path.join(RUN, "qa", "g14_manifest_16x9.json")
        cls.segs = {s["label"]: s for s in json.load(open(cls.man))["segments"]}
        cls.final = os.path.join(RUN, "out", "segment.mp4")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _audio_variant(self, name, afilter):
        out = os.path.join(self.tmp, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.final, "-filter_complex", afilter, "-map", "0:v",
                        "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out], check=True)
        return out

    def _gate(self, path):
        return G.gate_g14(path, self.man, source_clips=self.src, qa_dir=self.tmp)

    def _verdicts(self, det):
        return {d["label"]: d["segment_verdict"] for d in det if "segment_verdict" in d}

    def test_the_corrected_cut_passes_with_its_pause_sample_retaken(self):
        ok, det = self._gate(self.final)
        self.assertTrue(ok, self._verdicts(det))
        self.assertTrue(any(d.get("retake_of") for d in det))          # the pause sample was re-taken
        for d in det:
            if "segment_verdict" in d:
                self.assertGreaterEqual(d["conclusive_matches"], G.G14_MIN_CONCLUSIVE)

    def test_a_two_frame_av_slip_inside_a_segment_fails(self):
        c2 = self.segs["clip_02"]
        t = round((c2["start"] + c2["end"]) / 2, 3)                      # slip mid clip_02: audio 83 ms late
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    self.final], capture_output=True, text=True).stdout)
        slipped = self._audio_variant("slip.mp4", f"[0:a]atrim=0:{t},asetpts=N/SR/TB[a1];"
                                                   f"[0:a]atrim={t},asetpts=N/SR/TB[a2];"
                                                   f"aevalsrc=0|0:d={2 / 24:.6f}:s=48000[z];"
                                                   f"[a1][z][a2]concat=n=3:v=0:a=1,atrim=0:{dur}[a]")
        ok, det = self._gate(slipped)
        self.assertFalse(ok)
        self.assertEqual(self._verdicts(det).get("clip_02"), "FAIL", self._verdicts(det))

    def test_a_segment_with_fewer_than_three_conclusive_samples_holds(self):
        c1 = self.segs["clip_01"]
        silenced = self._audio_variant("silenced.mp4", f"[0:a]volume=enable='between(t,{c1['start']},{c1['end']})':"
                                                       f"volume=0[a]")
        ok, det = self._gate(silenced)
        self.assertFalse(ok)
        v = self._verdicts(det)
        self.assertEqual(v.get("clip_01"), "HOLD", v)
        self.assertFalse(any(d.get("status") == "FAIL" for d in det if d.get("label") == "clip_01"), det)


if __name__ == "__main__":
    unittest.main()
