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



@unittest.skipUnless(all(os.path.exists(os.path.join(RUN, p)) for p in ("out/segment_vertical.mp4", "qa/g14_manifest_9x16.json",
                                                                        "cuts_final.json"))
                     and os.path.isdir(os.path.join(RUN, "sources")), "Nov 11 replay run not on this machine")
class TestG14AudioOffsetVertical(TestG14Sampling):
    """Addendum '22:15' item 4: G14_audio_offset (the 9:16 final, frames=False, run_fresh.stage_gates) gets its own
    fixtures: must-pass the corrected Nov 10 cut's vertical; must-fail the same real 2-frame audio slip; HOLD on a
    segment with fewer than 3 conclusive samples (its audio silenced)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.man = os.path.join(RUN, "qa", "g14_manifest_9x16.json")
        cls.segs = {s["label"]: s for s in json.load(open(cls.man))["segments"]}
        cls.final = os.path.join(RUN, "out", "segment_vertical.mp4")

    def _gate(self, path):
        return G.gate_g14(path, self.man, source_clips=self.src, qa_dir=self.tmp, frames=False)

    def test_the_corrected_cut_passes_with_its_pause_sample_retaken(self):
        ok, det = self._gate(self.final)
        self.assertTrue(ok, self._verdicts(det))
        for d in det:
            if "segment_verdict" in d:
                self.assertGreaterEqual(d["conclusive_matches"], G.G14_MIN_CONCLUSIVE)


NOV12 = os.path.join(REPO, "runs", "pinned_20261112_135315")


@unittest.skipUnless(all(os.path.exists(os.path.join(NOV12, p)) for p in ("out/segment.mp4", "out/segment_vertical.mp4",
                     "qa/g14_manifest_16x9.json", "qa/g14_manifest_9x16.json", "cuts_final.json", "edl.json")),
                     "the Nov 12 moments run not on this machine")
class TestRulings13And11(unittest.TestCase):
    """Ruling 13 (orchestrator 2026-11-12 '10:02'): a G14 window is a sample only if >= 60 % of it is LOCKED
    speech (the lock's word timestamps minus the cut's measured pauses); below that it is not a sample (not pass,
    not fail, not counted). Ruling 11 ('08:55'): a clear region shorter than 6.75 s gets its samples spread
    evenly at a stride >= 0.75 s. The requirement is unchanged: >= 3 conclusive samples, every conclusive one in
    sync, fewer = HOLD. Fixture: the Nov 12 moments render (clip_02 is 4.666 s; under the old layout its near-end
    window over the pause after 'ever.' 'matched' 2.8 s away).
    must-pass  that render: clip_02 measured on its 4 speech windows, the near-end window is not a sample
    must-fail  clip_02's audio 200 ms late (a real offset)
    HOLD       clip_02 with only 2 qualifying windows; a 2 s clear region (not measurable)"""
    frames = True
    final_name, man_name = "segment.mp4", "g14_manifest_16x9.json"

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="g14r13_")
        cuts = json.load(open(os.path.join(NOV12, "cuts_final.json")))
        speech = G.g14_run_speech(NOV12, cuts)                          # exactly what run_fresh passes
        cls.src = {c["clip_id"]: {"path": os.path.join(NOV12, "sources", f"{c['video_id']}.mp4"),
                                  "cut_in": c["cut_in"], "words": speech[c["clip_id"]]} for c in cuts}
        cls.man = os.path.join(NOV12, "qa", cls.man_name)
        cls.segs = {s["label"]: s for s in json.load(open(cls.man))["segments"]}
        cls.final = os.path.join(NOV12, "out", cls.final_name)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _gate(self, path, man=None, src=None):
        return G.gate_g14(path, man or self.man, source_clips=src or self.src, qa_dir=self.tmp, frames=self.frames)

    def _seg(self, det, label):
        return next(d for d in det if d.get("label") == label and "segment_verdict" in d)

    def test_the_short_clip_is_measured_on_its_speech_windows_and_passes(self):
        ok, det = self._gate(self.final)
        self.assertTrue(ok, [d for d in det if "segment_verdict" in d])
        c2 = self._seg(det, "clip_02")
        self.assertEqual((c2["layout"], c2["segment_verdict"]), ("even", "PASS"), c2)
        self.assertGreaterEqual(c2["conclusive_matches"], G.G14_MIN_CONCLUSIVE)
        near_end = self.segs["clip_02"]["end"] - 0.5 - 0.1               # the window that 'matched' 2.8 s away
        self.assertFalse(any(d.get("label") == "clip_02" and abs(d.get("output_time", -9) - near_end) < 0.01
                             for d in det), "the near-end window over the pause is still a sample")

    def test_a_real_200_ms_offset_on_the_short_clip_fails(self):
        c2 = self.segs["clip_02"]
        a, b = c2["start"], c2["end"]
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    self.final], capture_output=True, text=True).stdout)
        out = os.path.join(self.tmp, "late200.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.final, "-filter_complex",
                        f"[0:a]atrim=0:{a},asetpts=N/SR/TB[a1];aevalsrc=0|0:d=0.2:s=48000[z];"
                        f"[0:a]atrim={a}:{b - 0.2},asetpts=N/SR/TB[a2];[0:a]atrim={b},asetpts=N/SR/TB[a3];"
                        f"[a1][z][a2][a3]concat=n=4:v=0:a=1,atrim=0:{dur}[a]", "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out], check=True)
        ok, det = self._gate(out)
        self.assertFalse(ok)
        self.assertEqual(self._seg(det, "clip_02")["segment_verdict"], "FAIL")

    def test_two_qualifying_windows_hold(self):
        src = dict(self.src, clip_02=dict(self.src["clip_02"], words=[{"start": 16.0, "end": 17.4}]))
        ok, det = self._gate(self.final, src=src)
        c2 = self._seg(det, "clip_02")
        self.assertFalse(ok)
        self.assertEqual((c2["speech_windows"], c2["segment_verdict"]), (2, "HOLD"), c2)

    def test_a_2_s_clear_region_is_not_measurable(self):
        self.assertEqual(G.g14_even_offsets(2.0), [])
        self.assertEqual(G.g14_even_offsets(2.149), [])
        self.assertEqual(len(G.g14_even_offsets(2.151)), 3)                # 0.05 .. 1.551: three at >= 0.75 s
        offs = G.g14_even_offsets(4.666)
        self.assertEqual(len(offs), 6)
        self.assertTrue(all(b - a >= G.G14_MIN_STRIDE_S for a, b in zip(offs, offs[1:])))
        m = json.load(open(self.man))
        for sg in m["segments"]:
            if sg["label"] == "clip_02":
                sg["end"] = round(sg["start"] + 2.0, 3)
        short = os.path.join(self.tmp, f"short_{self.man_name}")
        json.dump(m, open(short, "w"))
        ok, det = self._gate(self.final, man=short)
        c2 = self._seg(det, "clip_02")
        self.assertFalse(ok)
        self.assertEqual((c2["speech_windows"], c2["segment_verdict"]), (0, "HOLD"), c2)

    def test_locked_speech_is_the_lock_minus_the_measured_pauses(self):
        words = [{"start": 1.0, "end": 1.5}, {"start": 1.5, "end": 2.4}, {"start": 2.6, "end": 3.0}]
        self.assertEqual(G.g14_locked_speech(words, 1, 2, [(2.2, 2.7)]),
                         [{"start": 1.5, "end": 2.2}, {"start": 2.7, "end": 3.0}])


class TestRulings13And11Vertical(TestRulings13And11):
    """The same fixtures on the 9:16 final (G14_audio_offset: frames=False)."""
    frames = False
    final_name, man_name = "segment_vertical.mp4", "g14_manifest_9x16.json"


if __name__ == "__main__":
    unittest.main()
