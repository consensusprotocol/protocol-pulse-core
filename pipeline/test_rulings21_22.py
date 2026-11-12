#!/usr/bin/env python3
"""Rulings 21 and 22 (orchestrator 2026-11-12 '13:06'), on the Nov 12 re-run's real files (runs/pinned_20261112_165629).
RULING 21: G3c is measured on the PREPARED clip (speech stem), like G17c, not on the final where the music bed and
           loudness normalisation sit under the pause and move with the VO timeline.
  must-pass  clip_02's tail on its prepared clip (the run's final failed it under the bed)
  must-fail  a prepared clip whose tail runs into the next word
RULING 22: a G18 identity difference that only OMITS or REPEATS locked words is decided by the audio (the prepared
           clip's interior is the source span: -90 dBFS floor, 1 dB); a substituted or added word fails on text.
  must-pass  clip_01: the final's decode dropped "it's not, you know," and the prepared clip is the source's audio
  must-fail  a truncated clip (0.5 s removed) fails acoustically; a substituted word fails; an added word fails
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_rulings21_22.py"""
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
sys.path.insert(1, os.path.join(REPO, "segment_v1"))
import word_diff as WD  # noqa: E402

RUN = os.path.join(REPO, "runs", "pinned_20261112_165629")
NEED = ("out/segment.mp4", "qa/concat_manifest_16x9.json", "qa/final_clip_01.mp4", "qa/final_clip_02.mp4",
        "cuts_final.json", "edl.json", "sources")


class TestOmittedOrRepeatedOnly(unittest.TestCase):
    def test_the_text_cases(self):
        lock = "the good news is it's not you know its success is not dependent"
        self.assertTrue(WD._omitted_or_repeated_only(lock, "the good news is its success is not dependent"))
        self.assertTrue(WD._omitted_or_repeated_only(lock, "the good news is it's not it's not you know its success "
                                                           "is not dependent"))               # a repeat
        self.assertFalse(WD._omitted_or_repeated_only(lock, "the good news is it's not you know its progress is "
                                                            "not dependent"))                 # substituted
        self.assertFalse(WD._omitted_or_repeated_only(lock, "the great good news is it's not you know its success "
                                                            "is not dependent"))              # added
        self.assertFalse(WD._omitted_or_repeated_only(lock, lock))                         # no difference: nothing


@unittest.skipUnless(all(os.path.exists(os.path.join(RUN, p)) for p in NEED), "the Nov 12 re-run not on this machine")
class TestOnTheNov12ReRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="r2122_")
        cls.cuts = {c["clip_id"]: c for c in json.load(open(os.path.join(RUN, "cuts_final.json")))}
        cls.segs = json.load(open(os.path.join(RUN, "qa", "concat_manifest_16x9.json")))["segments"]
        cls.prepared = {c: os.path.join(RUN, "qa", f"final_{c}.mp4") for c in cls.cuts}
        edl = json.load(open(os.path.join(RUN, "edl.json")))
        cls.lock1 = edl["clips"][0]["selection_lock"]

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _g3c(self, prepared):
        import qa_gates
        return qa_gates.gate_g3c(os.path.join(RUN, "out", "segment.mp4"), self.segs, self.tmp, fmt="16x9",
                                 source_clips=prepared)

    def test_r21_clip_02_tail_passes_on_its_prepared_clip(self):
        ok, table = self._g3c(self.prepared)
        row = next(r for r in table if r.get("segment") == "clip_02")
        self.assertTrue(row.get("pass"), table)

    def test_r21_a_prepared_tail_running_into_the_next_word_fails(self):
        c = self.cuts["clip_02"]
        dur = c["cut_out"] - c["cut_in"]
        bad = os.path.join(self.tmp, "clip_02_runs_on.mp4")             # 0.4 s later: ends inside 'Okay,'
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{c['cut_in'] + 0.4:.3f}", "-t", f"{dur:.3f}", "-i",
                        os.path.join(RUN, "sources", f"{c['video_id']}.mp4"), "-c:v", "libx264", "-c:a", "aac",
                        bad], check=True)
        ok, table = self._g3c({**self.prepared, "clip_02": bad})
        row = next(r for r in table if r.get("segment") == "clip_02")
        self.assertFalse(row.get("pass"), row)

    def _g18(self, heard, prepared=None):
        c = self.cuts["clip_01"]
        clips = {"clip_01": {"lock_text": self.lock1["text"], "source": os.path.join(RUN, "sources",
                                                                                      f"{c['video_id']}.mp4"),
                             "cut_in": c["cut_in"], "cut_out": c["cut_out"], "pad_s": 0.0,
                             "alternatives": self.lock1.get("alternatives"), "prepared": prepared or self.prepared["clip_01"],
                             "fade_in_s": c.get("fade_in_ms", 0) / 1000, "fade_out_s": c.get("fade_out_ms", 0) / 1000}}
        segs = [{"label": "clip_01", "type": "talking_head", "start": 0.0, "end": c["cut_out"] - c["cut_in"]}]

        class Tr:
            def span(self, media, t0, t1):
                return heard if media == "final.mp4" else "the good news about bitcoin"
        return WD.gate_g18("final.mp4", segs, clips, transcriber=Tr())

    OMITTED = ("I think the good news about Bitcoin is its success is not dependent upon who's in the White House "
               "or who's controlling the Senate or the House of Representatives in the US.")

    def test_r22_an_omission_only_decode_is_decided_by_the_audio(self):
        ok, rows = self._g18(self.OMITTED)
        self.assertTrue(ok, rows)
        self.assertTrue(rows[0]["omission_adjudication"]["same_audio"])
        self.assertEqual(rows[0]["identity_omitted_only"], [("delete", "it's not you know", "")])

    def test_r22_a_truncated_clip_fails_acoustically(self):
        p = self.prepared["clip_01"]
        bad = os.path.join(self.tmp, "clip_01_cut.mp4")                  # 0.5 s removed at 3.0 s
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-filter_complex",
                        "[0:a]atrim=0:3,asetpts=N/SR/TB[a1];[0:a]atrim=3.5,asetpts=N/SR/TB[a2];"
                        "[a1][a2]concat=n=2:v=0:a=1[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
                        "-shortest", bad], check=True)
        ok, rows = self._g18(self.OMITTED, prepared=bad)
        self.assertFalse(ok, rows)
        self.assertFalse(rows[0]["omission_adjudication"]["same_audio"])

    def test_r22_a_substituted_or_added_word_fails_on_text(self):
        for heard in (self.OMITTED.replace("success", "progress"), self.OMITTED.replace("good news", "great good news")):
            ok, rows = self._g18(heard)
            self.assertFalse(ok, rows)
            self.assertNotIn("omission_adjudication", rows[0])


if __name__ == "__main__":
    unittest.main()
