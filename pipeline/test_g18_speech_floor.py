#!/usr/bin/env python3
"""The verifier's row 20 (docs/audits/FIX_VERIFICATION_2026-11-24.md): G18's audio check held afd8977d clip 1 (the
'bottomed'/'bottom' reading ruling 143 sends to the audio) on three NEAR-SILENT frames between words (-82, -73 and -80
dBFS; 1.0-4.8 dB apart: AAC codec noise) while every frame of speech matched within 1 dB. word_diff.same_speech_audio
compares the frames within SPEECH_RANGE_DB of the span's median level (and above sentence_law's -90 dBFS floor), at the
same 1 dB, the same +-2 hops, every kept frame compared. Real data, run pinned_20261124_033952 (read only):
must-pass  clip 1 as rendered (span_fidelity's old verdict fails it: the reason for the change); a lossless copy of it
must-fail  the word 'bottom' (source 19.40-19.82 s) 3 dB down; the same word silenced; a span with no audible frame
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_g18_speech_floor.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import sentence_law as L  # noqa: E402
import word_diff as WD  # noqa: E402

RUN = "/home/ultron/protocol_pulse/runs/pinned_20261124_033952"
BOTTOM = (19.40, 19.82)                       # the source seconds of 'bottom' / 'bottomed' (the verifier's drill)


def _cut():
    with open(os.path.join(RUN, "cuts_final.json")) as f:
        c = {x["clip_id"]: x for x in json.load(f)}["clip_01"]
    t0 = float(c["cut_in"]) + float(c.get("fade_in_ms") or 0) / 1000
    t1 = float(c["cut_out"]) - float(c.get("fade_out_ms") or 0) / 1000
    return c, t0, t1, os.path.join(RUN, "sources", f"{c['video_id']}.mp4"), os.path.join(RUN, "qa", "final_clip_01.mp4")


@unittest.skipUnless(os.path.exists(os.path.join(RUN, "qa", "final_clip_01.mp4")), "run pinned_20261124_033952")
class TestRealClip(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="g18floor_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.c, self.t0, self.t1, self.src, self.prep = _cut()

    def judge(self, clip):
        return WD.same_speech_audio(self.src, clip, self.t0, self.t1, float(self.c["cut_in"]),
                                    float(self.c.get("lead_in_pad_s") or 0.0))

    def doctored(self, name, af):
        """A lossless copy of the prepared clip's audio, the filter applied (the clip's own clock: source - cut_in)."""
        out = os.path.join(self.d, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.prep, "-vn", "-af", af, "-c:a", "pcm_s16le", out],
                       check=True, timeout=120)
        return out

    def test_the_clip_as_rendered_passes_on_its_speech(self):
        old_ok, old = L.span_fidelity(self.src, self.prep, self.t0, self.t1, float(self.c["cut_in"]), 0.0)
        self.assertEqual((old_ok, old["worst_db"]), (False, 4.83))                 # the hold the verifier found
        ok, det = self.judge(self.prep)
        self.assertTrue(ok, det)
        self.assertLessEqual(det["worst_db"], 1.0)
        self.assertEqual(det["floor_dbfs"], -60.0)                       # the span's 90th percentile -15.0, less 45
        self.assertGreater(det["compared_frames"], 700)

    def test_a_lossless_copy_passes_and_the_word_3_db_down_or_silenced_holds(self):
        a, b = (round(t - float(self.c["cut_in"]), 3) for t in BOTTOM)
        ok, det = self.judge(self.doctored("copy.wav", "anull"))
        self.assertTrue(ok, det)                                                    # control: the copy alone passes
        ok, det = self.judge(self.doctored("down3.wav", f"volume=enable='between(t,{a},{b})':volume=-3dB"))
        self.assertFalse(ok, det)
        self.assertGreater(det["worst_db"], 2.5)
        ok, det = self.judge(self.doctored("muted.wav", f"volume=enable='between(t,{a},{b})':volume=0"))
        self.assertFalse(ok, det)
        self.assertGreater(det["worst_db"], 20.0)

    def test_a_word_inserted_where_the_source_is_quiet_holds(self):
        """batch 129 c1 (gemma): the clip's own speech is compared where the source is quiet: a 0.2 s tone at -20 dBFS
        laid into the pause at source 21.6 s (the near-silent frames the change stops comparing) fails."""
        a = round(21.55 - float(self.c["cut_in"]), 3)
        tone = os.path.join(self.d, "tone.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.2",
                        "-af", "volume=-20dB", "-ac", "2", tone], check=True, timeout=60)
        ins = os.path.join(self.d, "inserted.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.prep, "-i", tone, "-filter_complex",
                        f"[1:a]adelay={int(a * 1000)}|{int(a * 1000)}[t];[0:a][t]amix=inputs=2:normalize=0:duration=first",
                        "-vn", "-c:a", "pcm_s16le", ins], check=True, timeout=120)
        ok, det = self.judge(ins)
        self.assertFalse(ok, det)
        self.assertGreater(det["worst_db"], 20.0)

    def test_a_span_with_no_audible_frame_is_no_proof(self):
        silent = self.doctored("silent.wav", "volume=0")
        ok, det = WD.same_speech_audio(silent, silent, 1.0, 2.0, 0.0)
        self.assertEqual((ok, det["why"]), (False, "no audible source frame in the span"))


class TestMostlyPause(unittest.TestCase):
    """batch 129 c1 (glm): a span that is mostly pause must not sink the floor into the pause's codec noise. Synthetic:
    2 s of a tone at speech level (-13.5 dBFS RMS) then 8 s of noise near -80 dBFS; the 'clip' is the same audio
    through AAC and back. The
    span's median sits in the noise (a median floor would compare it); its 90th percentile is the tone."""

    def test_the_pause_is_not_compared_and_a_change_in_the_tone_is(self):
        d = tempfile.mkdtemp(prefix="g18pause_")
        self.addCleanup(shutil.rmtree, d, True)
        src, aac, back, down = (os.path.join(d, n) for n in ("src.wav", "c.m4a", "clip.wav", "down.wav"))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",                 # a tone at speech level
                        "aevalsrc=0.3*sin(2*PI*300*t):s=48000:d=2", "-f", "lavfi", "-i",       # (-13.5 dBFS RMS)
                        "anoisesrc=color=white:amplitude=0.0001:sample_rate=48000:duration=8", "-filter_complex",
                        "[0:a][1:a]concat=n=2:v=0:a=1", "-ac", "2", src], check=True, timeout=60)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:a", "aac", "-b:a", "96k", aac], check=True, timeout=60)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", aac, "-c:a", "pcm_s16le", back], check=True, timeout=60)
        import numpy as np
        _, ds = L.SourceAudio(src).sl(0.1, 9.9)
        self.assertLess(float(np.median(ds[ds > -90])), -60.0)          # the median is the pause
        ok, det = WD.same_speech_audio(src, back, 0.1, 9.9, 0.0)
        self.assertTrue(ok, det)
        self.assertGreater(det["floor_dbfs"], -70.0)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", back, "-af", "volume=enable='between(t,0.5,1.0)':volume=-3dB",
                        "-c:a", "pcm_s16le", down], check=True, timeout=60)
        ok, det = WD.same_speech_audio(src, down, 0.1, 9.9, 0.0)
        self.assertFalse(ok, det)                                       # the tone 3 dB down for 0.5 s


@unittest.skipUnless(os.path.exists(os.path.join(RUN, "GATE_REPORT.json")), "run pinned_20261124_033952")
class TestRealG18(unittest.TestCase):
    """RULING 163 (3) (orchestrator 08:22 ET Nov 24): G18 itself on afd8977d's own run, both finals, the audio check REAL:
    nothing is stubbed but the transcriber, which returns the run's recorded decodes (G18's own record of what Whisper
    heard; the verifier's drill20 did the same). Must-pass: G18 PASSES both formats, clip 1's 'bottomed' / 'bottom' a
    word form decided by the audio. Must-fail: the same run with 'bottom' 3 dB down in the prepared clip HOLDS."""

    def g18(self, prepared_clip_01=None):
        with open(os.path.join(RUN, "edl.json")) as f:
            edl = json.load(f)
        with open(os.path.join(RUN, "cuts_final.json")) as f:
            cuts = json.load(f)
        with open(os.path.join(RUN, "GATE_REPORT.json")) as f:
            rep = json.load(f)
        locks = {"hook": edl["hook"].get("selection_lock"),
                 **{f"clip_{c['index']:02d}": c.get("selection_lock") for c in edl["clips"]}}
        clips = {c["clip_id"]: {"lock_text": (locks.get(c["clip_id"]) or {}).get("text", ""),     # run_fresh's own
                                "source": os.path.join(RUN, "sources", f"{c['video_id']}.mp4"),   # g18_clips
                                "cut_in": c["cut_in"], "cut_out": c["cut_out"],
                                "pad_s": float(c.get("lead_in_pad_s") or 0.0),
                                "adjudicated": bool((locks.get(c["clip_id"]) or {}).get("adjudication")),
                                "alternatives": (locks.get(c["clip_id"]) or {}).get("alternatives"),
                                "prepared": os.path.join(RUN, "qa", f"final_{c['clip_id']}.mp4"),
                                "fade_in_s": float(c.get("fade_in_ms") or 0) / 1000,
                                "fade_out_s": float(c.get("fade_out_ms") or 0) / 1000} for c in cuts}
        if prepared_clip_01:
            clips["clip_01"]["prepared"] = prepared_clip_01
        out = {}
        for fmt, final in (("16x9", "segment.mp4"), ("9x16", "segment_vertical.mp4")):
            with open(os.path.join(RUN, "qa", f"concat_manifest_{fmt}.json")) as f:
                segs = json.load(f)["segments"]
            rows = {r["segment"]: r for r in rep["G18"][fmt]}
            by = {x["label"]: x for x in segs}

            class Recorded:
                def span(self, path, start, end):
                    for lab, x in by.items():
                        if path.endswith(final) and abs(x["start"] - start) < 1e-6:
                            return rows[lab]["heard"]
                    for lab, c in clips.items():
                        if path == c["source"] and abs(float(c["cut_in"]) - start) < 1e-6:
                            return rows[lab]["source_span_heard"]
                    raise KeyError((path, start, end))
            out[fmt] = WD.gate_g18(os.path.join(RUN, "out", final), segs, clips, transcriber=Recorded())
        return out

    def test_g18_passes_the_real_clip_on_its_real_audio(self):
        for fmt, (ok, rows) in self.g18().items():
            row = {r["segment"]: r for r in rows}["clip_01"]
            self.assertTrue(ok, (fmt, rows))
            self.assertEqual([list(x) for x in row["identity_small_words"]], [["replace", "bottomed", "bottom"]])
            self.assertIs(row["omission_adjudication"]["same_audio"], True)
            self.assertLessEqual(row["omission_adjudication"]["worst_db"], 1.0)

    def test_the_same_run_with_the_word_3_db_down_holds(self):
        d = tempfile.mkdtemp(prefix="g18real_")
        self.addCleanup(shutil.rmtree, d, True)
        c, _, _, _, prep = _cut()
        a, b = (round(t - float(c["cut_in"]), 3) for t in BOTTOM)
        down = os.path.join(d, "down3.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", prep, "-vn", "-af",
                        f"volume=enable='between(t,{a},{b})':volume=-3dB", "-c:a", "pcm_s16le", down],
                       check=True, timeout=120)
        for fmt, (ok, rows) in self.g18(prepared_clip_01=down).items():
            row = {r["segment"]: r for r in rows}["clip_01"]
            self.assertFalse(ok, fmt)
            self.assertFalse(row["pass"])
            self.assertIs(row["omission_adjudication"]["same_audio"], False)
            self.assertEqual([list(x) for x in row["identity"]], [["replace", "bottomed", "bottom"]])


if __name__ == "__main__":
    unittest.main()
