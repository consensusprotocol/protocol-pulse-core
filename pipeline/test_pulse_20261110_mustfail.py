#!/usr/bin/env python3
"""MUST-FAIL fixture: PBX's review of runs/pinned_20261110_150345 (Telegram 67444/67445, 2026-11-11).

EXPECTED ON HEAD 7a76a5c5 (before the checks land): every DEFECT test FAILS, because no check exists
that catches the defect or the existing path accepts it; the CONTROL tests (v2f card passes G12/G15,
clip_02 out edge is clean) document what must keep passing. A green run means the checks landed.
Never invert an assertion to make it pass. Fixture: tests/fixtures/pulse_20261110 (copies; the run dir
is never modified). No GPU, no model calls: the unpunctuated-transcript adjudications are cached.

D1  hook opens on "Bitcoin" at source 0.000 with 60 ms of genuine room tone before the onset (30 ms of
    codec zero first) and no lead-in pad              -> G16 IN and G17a head FAIL
D2  clip_01 out 33.71 runs 2.4 s into the next sentence ("All right, you've probably seen people
    celebrating"); the sentence ends at 'week.'       -> G16 OUT FAIL
D3a clip_01 in 15.13 starts on "81" (sentence: "It went from above $81,000 ...") -> G16 IN + G17a FAIL
D3b clip_02 in 14.93 lands inside "days" (sentence: "Of course, Bitcoin dropped ...") -> G16 IN + G17a FAIL
D3c clip_02 out 34.36 is a CONTROL and must PASS: acoustically clean (pause 34.08-34.43, the 'I' onset
    is 34.44; whisper on the prepared clip ends "...many times."). The transcript word 'i' 33.92-34.46
    is a whisper timestamp error, not a defect.
T   ad7295ea/4cf5a31a tautology: expected words recomputed from the moved cut -> G16 lock FAIL
OFF window offset: yt-dlp is asked for '*54-100' but the offset recorded is 53.57 (source of D3)
D4  credits: the 'avatars' are 1280x720 video thumbnails squashed into circles -> G15 and G12 FAIL on
    yesterday's card and PASS on the frozen v2f finals; the shout-out builder must refuse a non-square
    avatar and must not fall back to a video thumbnail or a generated placeholder.
"""
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE_DIR)
sys.path.insert(0, PIPELINE_DIR)
sys.path.insert(0, os.path.join(REPO, "segment_v1"))
FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110")
V2F = os.path.join(REPO, "references", "v2f_2026-11-06", "run")


def _law():
    import sentence_law
    return sentence_law


def _dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True, check=True).stdout)


class _G16Fixture(unittest.TestCase):
    """Yesterday's cuts against selection locks built from the editor's B3 decision."""

    @classmethod
    def setUpClass(cls):
        L = _law()
        cls.tmp = tempfile.mkdtemp(prefix="pulse_20261110_")
        shutil.copytree(os.path.join(FIX, "run", "transcripts"), os.path.join(cls.tmp, "transcripts"))
        shutil.copy(os.path.join(FIX, "run", "cuts_final.json"), cls.tmp)
        edl = json.load(open(os.path.join(FIX, "run", "edl.json")))
        sel = {p["video_id"]: p for p in json.load(open(os.path.join(FIX, "selection", "B3_chosen.json")))["chosen"]}
        cls.locks = {}
        for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]:
            tpath = os.path.join(cls.tmp, "transcripts", f"{seg['video_id']}.json")
            words = json.load(open(tpath))["words"]
            p = sel[seg["video_id"]]
            i0, i1, r = L.anchor(words, p["text"])
            seg["selection_lock"] = L.make_lock(seg["video_id"], words, i0, i1, L.sha256_file(tpath), p["text"],
                                                [p["start"], p["end"]], r, "B3 (fixture)")
            cls.locks[label] = seg["selection_lock"]
        json.dump(edl, open(os.path.join(cls.tmp, "edl.json"), "w"), indent=1)
        adj = L.Adjudicator(cache_path=os.path.join(FIX, "selection", "sentence_adjudication.json"),
                            log_path=None, allow_model=False)
        cls.ok, table = L.gate_g16(cls.tmp, adj, source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
        cls.rows = {r["segment"]: r for r in table}
        cls.g17_ok, t17 = L.gate_g17_prepared(
            {c: os.path.join(FIX, "audio", f"prepared_{c}.flac") for c in ("hook", "clip_01", "clip_02")})
        cls.g17 = {r["segment"]: r for r in t17}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


class TestSelectionLockEdges(_G16Fixture):
    def test_locks_hold_the_editors_sentences(self):
        got = {k: (v["first_word"], v["last_word"]) for k, v in self.locks.items()}
        self.assertEqual(got, {"hook": ("Bitcoin", "take."), "clip_01": ("It", "week."), "clip_02": ("of", "times")})


class TestD1HookOnset(_G16Fixture):
    def test_g16_in_fails_without_lead_in_pad(self):
        r = self.rows["hook"]["in"]
        self.assertFalse(r["pass"], r)
        self.assertLess(r["genuine_lead_ms"], 80)

    def test_g17a_head_fails(self):
        self.assertFalse(self.g17["hook"]["lead_ok"], self.g17["hook"])


class TestD2Clip01Out(_G16Fixture):
    def test_g16_out_fails(self):
        self.assertFalse(self.rows["clip_01"]["out"]["pass"], self.rows["clip_01"]["out"])


class TestD3Edges(_G16Fixture):
    def test_d3a_clip01_in_fails(self):
        self.assertFalse(self.rows["clip_01"]["in"]["pass"], self.rows["clip_01"]["in"])
        self.assertFalse(self.g17["clip_01"]["lead_ok"], self.g17["clip_01"])

    def test_d3b_clip02_in_fails(self):
        self.assertFalse(self.rows["clip_02"]["in"]["pass"], self.rows["clip_02"]["in"])
        self.assertFalse(self.g17["clip_02"]["lead_ok"], self.g17["clip_02"])

    def test_d3c_clip02_out_control_passes(self):
        self.assertTrue(self.rows["clip_02"]["out"]["pass"], self.rows["clip_02"]["out"])
        self.assertTrue(self.g17["clip_02"]["tail_ok"], self.g17["clip_02"])


class TestTautology(_G16Fixture):
    def test_recomputed_expected_words_fail_the_lock(self):
        for c in ("clip_01", "clip_02"):
            self.assertTrue(any("recomputed" in e for e in self.rows[c]["errors"]), self.rows[c]["errors"])

    def test_gate_fails_overall(self):
        self.assertFalse(self.ok)

    def test_run_fresh_has_no_recompute_sync_or_wide_snap(self):
        import run_fresh
        src = inspect.getsource(run_fresh)
        for name in ("_recompute_edge_words", "_sync_edl_edge_words", "_snap_candidates"):
            self.assertNotIn(f"def {name}", src, f"{name} still present")

    def test_gates_stage_runs_g16_and_g17(self):
        import run_fresh
        src = inspect.getsource(run_fresh.stage_gates)
        self.assertIn("G16_sentence_boundary", src)
        self.assertIn("G17_onset_tail", src)


class TestWindowOffset(unittest.TestCase):
    def test_recorded_offset_equals_requested_section_start(self):
        import select_passages as sp
        tmp = tempfile.mkdtemp(prefix="dlwin_")
        seen = {}

        def fake_run(cmd, **kw):
            seen["section"] = cmd[cmd.index("--download-sections") + 1]
            out = cmd[cmd.index("-o") + 1]
            with open(out, "wb") as f:
                f.write(b"\0" * 200_000)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        try:
            with mock.patch.object(sp.subprocess, "run", side_effect=fake_run):
                path, off = sp._download_window("lusJ1m-J0Mc", 68.57, 85.41, tmp)
            start = float(seen["section"].lstrip("*").split("-")[0])
            self.assertAlmostEqual(off, start, places=3, msg=f"requested {seen['section']} recorded {off}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestD4Credits(unittest.TestCase):
    S = tempfile.mkdtemp(prefix="g15_")

    def _gates(self, mp4, segs):
        import gates as G
        import qa_gates as Q
        ok15, _ = G.gate_g15(mp4, segs, self.S)
        ok12, _ = Q.gate_g12(mp4, segs, 3, self.S)
        return ok15, ok12

    def test_yesterdays_card_fails_g15_and_g12(self):
        for fmt in ("16x9", "9x16"):
            p = os.path.join(FIX, "video", f"shoutout_{fmt}.mp4")
            ok15, ok12 = self._gates(p, [{"label": "shoutout", "type": "shoutout", "start": 0.0, "end": _dur(p)}])
            self.assertFalse(ok15, f"G15 passed yesterday's {fmt} card")
            self.assertFalse(ok12, f"G12 passed yesterday's {fmt} card")

    def test_v2f_finals_pass_g15_and_g12(self):
        for out, man in (("segment.mp4", "concat_manifest_16x9.json"), ("segment_vertical.mp4", "concat_manifest_9x16.json")):
            segs = json.load(open(os.path.join(V2F, "qa", man)))["segments"]
            ok15, ok12 = self._gates(os.path.join(V2F, "out", out), segs)
            self.assertTrue(ok15 and ok12, f"v2f {out}: G15 {ok15} G12 {ok12}")

    def test_shoutout_refuses_a_thumbnail_avatar(self):
        import shoutout
        with self.assertRaises(ValueError):
            shoutout.validate_avatar(os.path.join(FIX, "video", "natalie_brunell.jpg"))

    def test_no_thumbnail_or_placeholder_fallback(self):
        import shoutout
        src = inspect.getsource(shoutout)
        self.assertFalse('meta.get("thumbnail")' in src, "video-thumbnail fallback still in shoutout.py")
        self.assertFalse("placeholder" in src.lower(), "generated placeholder avatar still in shoutout.py")


if __name__ == "__main__":
    unittest.main()
