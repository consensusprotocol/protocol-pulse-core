#!/usr/bin/env python3
"""Tests for the fresh-topic generalization (run_fresh / cut_accept / clip_contract /
select_passages coords / intro-optional renderers). Must-fail fixtures come from the
v2f reference sources (read-only). Run: python3 -m pytest pipeline/test_fresh.py -q
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)

REF = os.path.join(REPO, "references", "v2f_2026-11-06")
REF_RUN = os.path.join(REF, "run")
SRC = lambda vid: os.path.join(REF_RUN, "sources", f"{vid}.mp4")
HAVE_REF = os.path.exists(SRC("RBFN4CB60To"))
HAVE_GPU = os.environ.get("CUDA_VISIBLE_DEVICES") == "0"


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ── B: select_passages keeps EDL times in source-file coordinates ──

class TestSelectCoords(unittest.TestCase):
    def test_edl_times_are_source_file_coords(self):
        import select_passages as sp
        with tempfile.TemporaryDirectory() as rd:
            passages = {"chosen": [
                {"video_id": "AAA", "channel": "The Bitcoin Layer", "start": 110.0, "end": 121.0,
                 "duration": 11.0, "score": 9, "text": "Statement one."},
                {"video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
                 "duration": 14.0, "score": 5, "text": "Statement two."}]}
            json.dump(passages, open(os.path.join(rd, "passages.json"), "w"))

            def fake_dl(vid, start, end, run_dir, pad=15.0):
                return (os.path.join(run_dir, "sources", f"{vid}.mp4"), start - pad)

            def fake_tx(path, vid, run_dir):
                # whisper words in LOCAL (downloaded file) seconds: both windows start
                # 15 s before the passage, so the passage begins near local t=15
                ws, t = [], 14.0
                for i in range(60):
                    w = "word." if i % 6 == 5 else "word"
                    ws.append({"word": w, "start": round(t, 2), "end": round(t + 0.3, 2)})
                    t += 0.35
                return {"words": ws}

            orig = (sp._download_window, sp._whisper_transcribe)
            sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
            try:
                self.assertTrue(sp.select_and_build_edl("test", "bitcoin", rd))
            finally:
                sp._download_window, sp._whisper_transcribe = orig
            edl = json.load(open(os.path.join(rd, "edl.json")))
            for seg in [edl["hook"]] + edl["clips"]:
                self.assertEqual(seg["time_coords"], "source_file")
                off = seg["source_window_offset_s"]
                self.assertIn(off, (95.0, 495.0))
                # source-file coords: well inside the ~40 s downloaded window, never full-video
                self.assertLess(seg["word_start"], 60.0, seg)
                self.assertLess(seg["word_end"], 60.0, seg)


# ── intro-optional renderer support (shared helper) ──

class TestVerifyVoVoice(unittest.TestCase):
    def test_intro_less_manifest_ok(self):
        from config import verify_vo_voice
        m = {"signoff": {"stem_wav": "s.wav", "voice_id": "V", "model_id": "M"}}
        self.assertEqual(verify_vo_voice(m), ("V", "M"))

    def test_mismatch_raises(self):
        from config import verify_vo_voice
        m = {"intro": {"stem_wav": "i.wav", "voice_id": "V", "model_id": "M"},
             "signoff": {"stem_wav": "s.wav", "voice_id": "X", "model_id": "M"}}
        with self.assertRaises(RuntimeError):
            verify_vo_voice(m)

    def test_empty_raises(self):
        from config import verify_vo_voice
        with self.assertRaises(RuntimeError):
            verify_vo_voice({})

    def test_v2f_manifest_same_voice(self):
        from config import verify_vo_voice
        m = json.load(open(os.path.join(REF_RUN, "vo_audio", "VO_MANIFEST.json")))
        self.assertEqual(verify_vo_voice(m), (m["intro"]["voice_id"], m["intro"]["model_id"]))

    def test_vertical_intro_requirement_is_conditional(self):
        src = open(os.path.join(PIPELINE, "render_vertical.py")).read()
        self.assertNotIn('# Intro VO — fail-closed: intro is required', src)
        self.assertIn('if edl.get("vo", {}).get("intro"):\n        if not os.path.exists(vo_intro_mp4)', src)
        for f in ("render16.py", "render_vertical.py"):
            self.assertNotIn('vo_manifest["intro"]["voice_id"]', open(os.path.join(PIPELINE, f)).read())


# ── C: cut acceptance (acoustic) — v2f fixtures ──

@unittest.skipUnless(HAVE_REF, "v2f reference sources not present")
class TestCutAcceptAcoustic(unittest.TestCase):
    def check(self, vid, a, b):
        from cut_accept import check_cut_acoustics
        return check_cut_acoustics(SRC(vid), a, b)

    def test_approved_cuts_pass(self):
        for vid, a, b in [("RBFN4CB60To", 0.0, 9.52), ("RBFN4CB60To", 624.63, 636.72),
                          ("QCgW8RlTu5Q", 998.00, 1011.80)]:
            ok, d = self.check(vid, a, b)
            self.assertTrue(ok, (vid, a, b, d))

    def test_mustfail_thinks_9_13(self):
        ok, d = self.check("RBFN4CB60To", 0.0, 9.13)
        self.assertFalse(ok)
        self.assertFalse(d["out"]["pass"])

    def test_mustfail_magnitude_249_37(self):
        ok, d = self.check("Pxrak-iMT0g", 238.55, 249.37)
        self.assertFalse(ok)
        self.assertFalse(d["out"]["pass"])

    def test_mustfail_themselves_997_25(self):
        ok, d = self.check("QCgW8RlTu5Q", 997.25, 1011.80)
        self.assertFalse(ok)
        self.assertFalse(d["in"]["pass"])

    def test_one_time_exception_not_available_in_fresh_mode(self):
        ok, _ = self.check("Pxrak-iMT0g", 238.55, 249.63)
        self.assertFalse(ok)

    def test_cutter_outpoints_too_close_rejected(self):
        for vid, a, b in [("RBFN4CB60To", 624.63, 636.78), ("QCgW8RlTu5Q", 998.00, 1012.13),
                          ("Pxrak-iMT0g", 238.55, 249.67)]:
            ok, _ = self.check(vid, a, b)
            self.assertFalse(ok, (vid, b))


class TestEdgeWordHelpers(unittest.TestCase):
    def test_words_match(self):
        from cut_accept import words_match
        self.assertTrue(words_match("magnitude.", "magnitude."))
        self.assertTrue(words_match("The", "the"))
        self.assertTrue(words_match("prison", "pris"))
        self.assertFalse(words_match("themselves", "a"))
        self.assertFalse(words_match("", "a"))
        self.assertFalse(words_match("it", "its's"))

    def test_spoken_tokens_currency(self):
        from cut_accept import spoken_tokens
        self.assertEqual(spoken_tokens(["above", "$40", "trillion."])[-1], "dollars")
        self.assertEqual(spoken_tokens(["$5"]), ["5", "dollars"])
        self.assertEqual(spoken_tokens(["5%"]), ["5", "percent"])


@unittest.skipUnless(HAVE_REF and HAVE_GPU, "needs v2f reference + CUDA_VISIBLE_DEVICES=0")
class TestEdgeWordsWhisper(unittest.TestCase):
    def test_approved_clips_and_mustfail_head(self):
        from cut_accept import check_edge_words
        from acoustic import apply_fades
        with tempfile.TemporaryDirectory() as td:
            for cid, fw, lw in [("hook", "The", "thinks."), ("clip_01", "The", "magnitude."),
                                ("clip_02", "One", "dollars."), ("clip_03", "a", "have.")]:
                ok, d = check_edge_words(os.path.join(REF_RUN, "qa", f"final_{cid}.mp4"),
                                         fw, lw, td, cid)
                self.assertTrue(ok, d)
            raw, fin = os.path.join(td, "raw.mp4"), os.path.join(td, "fin.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "992.25", "-i",
                            SRC("QCgW8RlTu5Q"), "-ss", "5.0", "-t", "14.55", "-vf",
                            "scale=1920:1080", "-r", "24", "-c:v", "libx264", "-preset",
                            "veryfast", "-c:a", "aac", "-ar", "48000", "-ac", "2", raw], check=True)
            apply_fades(raw, fin)
            ok, d = check_edge_words(fin, "a", "have.", td, "mf")
            self.assertFalse(ok, d)
            self.assertFalse(d["first_pass"])


# ── D: clip-preparation contract ──

@unittest.skipUnless(HAVE_REF, "v2f reference not present")
class TestClipContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.td = tempfile.mkdtemp(prefix="clipcontract_")

        def ext(a, dur, out, vf="scale=1920:1080,setsar=1:1", r=24, vid="RBFN4CB60To"):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(max(0, a - 5)), "-i",
                            SRC(vid), "-ss", str(a - max(0, a - 5)), "-t", str(dur), "-vf", vf,
                            "-r", str(r), "-vsync", "cfr", "-c:v", "libx264", "-preset",
                            "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-ar", "48000", "-ac", "2", out], check=True)
        cls.unfaded_in = os.path.join(cls.td, "unfaded_in.mp4")
        ext(624.63, 12.09, cls.unfaded_in)
        cls.unfaded_out = os.path.join(cls.td, "unfaded_out.mp4")
        ext(238.55, 10.82, cls.unfaded_out, vid="Pxrak-iMT0g")
        cls.p720 = os.path.join(cls.td, "p720.mp4")
        ext(0.0, 9.52, cls.p720, vf="scale=1280:720")
        cls.f30 = os.path.join(cls.td, "f30.mp4")
        ext(0.0, 9.52, cls.f30, r=30)

    def test_v2f_finals_pass(self):
        from clip_contract import check_clip
        for cid, dur in [("hook", 9.52), ("clip_01", 11.08), ("clip_02", 12.09), ("clip_03", 13.80)]:
            ok, d = check_clip(os.path.join(REF_RUN, "qa", f"final_{cid}.mp4"), dur)
            self.assertTrue(ok, d)

    def test_mustfail_unfaded_head(self):
        from clip_contract import check_clip
        ok, d = check_clip(self.unfaded_in, 12.09)
        self.assertFalse(ok)
        self.assertTrue(any("fade-in" in e for e in d["errors"]))

    def test_mustfail_unfaded_tail(self):
        from clip_contract import check_clip
        ok, d = check_clip(self.unfaded_out, 10.82)
        self.assertFalse(ok)
        self.assertTrue(any("fade-out" in e for e in d["errors"]))

    def test_mustfail_720p(self):
        from clip_contract import check_clip
        ok, d = check_clip(self.p720, 9.52)
        self.assertFalse(ok)
        self.assertTrue(any("resolution" in e for e in d["errors"]))

    def test_mustfail_30fps(self):
        from clip_contract import check_clip
        ok, d = check_clip(self.f30, 9.52)
        self.assertFalse(ok)
        self.assertTrue(any("fps" in e for e in d["errors"]))

    def test_mustfail_wrong_duration(self):
        from clip_contract import check_clip
        ok, d = check_clip(os.path.join(REF_RUN, "qa", "final_clip_02.mp4"), 11.50)
        self.assertFalse(ok)
        self.assertTrue(any("duration" in e for e in d["errors"]))


# ── run_fresh orchestration rules ──

class TestRunFreshRules(unittest.TestCase):
    def test_topic_terms(self):
        from run_fresh import topic_terms
        t = topic_terms("Bitcoin erases post-election gains as Wall Street selloff triggers "
                        "over $1 billion in crypto liquidations")
        self.assertNotIn("bitcoin", t)
        self.assertNotIn("billion", t)
        self.assertNotIn("over", t)
        self.assertIn("election", t)
        self.assertNotIn("530m", topic_terms("ETFs post $530M outflows"))

    def test_verdict_rules(self):
        from run_fresh import verdict_for, VERDICT_CANDIDATE, VERDICT_HOLD
        ok_rows = {"G1_voice": "PASS", "G8_sharpness": "FLAG/LIMITED (x)",
                   "G9_tail": "FLAG (APPROVED KNOWN EXCEPTION ...)",
                   "G14_frame_similarity": "LIMITED (not valid)",
                   "G11_parity(run_gates)": "NOT RUN BY run_gates (no horiz) — see G11 below"}
        self.assertEqual(verdict_for(ok_rows)[0], VERDICT_CANDIDATE)
        for bad in ("FAIL", "HOLD(inconclusive)", "SKIPPED (no horiz_mp4)",
                    "FAIL (fallback occurred)"):
            self.assertEqual(verdict_for({**ok_rows, "Gx": bad})[0], VERDICT_HOLD, bad)

    def test_no_publishing_path(self):
        src = open(os.path.join(PIPELINE, "run_fresh.py")).read()
        self.assertNotRegex(src, r"^\s*(from|import)\s+telegram", )
        import run_fresh  # noqa: F401
        self.assertNotIn("telegram", sys.modules)
        self.assertNotIn("telegram_drop", sys.modules)

    def test_fallback_regex(self):
        from run_fresh import FALLBACK_RE
        self.assertEqual(FALLBACK_RE.findall("  WARNING: reframe failed for clip_02, using original\n"),
                         ["clip_02"])


# ── protected reference & run_isolated untouched ──

class TestProtected(unittest.TestCase):
    def test_run_isolated_unchanged_from_reference_tag(self):
        tagged = subprocess.run(["git", "show", "ref-v2f-2026-11-06:pipeline/run_isolated.py"],
                                cwd=REPO, capture_output=True, check=True).stdout
        self.assertEqual(hashlib.sha256(tagged).hexdigest(),
                         _sha(os.path.join(PIPELINE, "run_isolated.py")))

    @unittest.skipUnless(HAVE_REF, "reference not present")
    def test_frozen_reference_checksums(self):
        r = subprocess.run(["sha256sum", "--quiet", "-c", "SHA256SUMS"], cwd=REF,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
