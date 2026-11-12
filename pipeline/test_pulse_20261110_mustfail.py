#!/usr/bin/env python3
"""MUST-FAIL fixture: PBX's review of runs/pinned_20261110_150345 (Telegram 67444/67445, 2026-11-11).

EXPECTED ON HEAD 7a76a5c5 (before the checks land): every DEFECT test FAILS, because no check exists
that catches the defect or the existing path accepts it; the CONTROL tests (v2f card passes G12/G15,
clip_02 out edge is clean) document what must keep passing. A green run means the checks landed.
Never invert an assertion to make it pass. Fixture: tests/fixtures/pulse_20261110 (copies; the run dir
is never modified). No GPU, no model calls: Yahoo Finance's unpunctuated window transcript is read the
way today's pipeline produces it (selection/transcripts_punctuated, pipeline/punctuation.py).

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
        for f in os.listdir(os.path.join(FIX, "selection", "transcripts_punctuated")):   # today's punctuation layer
            shutil.copy(os.path.join(FIX, "selection", "transcripts_punctuated", f), os.path.join(cls.tmp, "transcripts"))
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
        cls.ok, table = L.gate_g16(cls.tmp, source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
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
        self.assertEqual(got, {"hook": ("Bitcoin", "take."), "clip_01": ("It", "week."), "clip_02": ("of", "times.")})


class TestD1HookOnset(_G16Fixture):
    def test_g16_in_fails_without_lead_in_pad(self):
        r = self.rows["hook"]["in"]
        self.assertFalse(r["pass"], f"D1: G16 must reject a file-head hook with <80 ms genuine lead-in and no pad: {r}")
        self.assertLess(r["genuine_lead_ms"], 80, r)

    def test_g17a_head_fails(self):
        self.assertFalse(self.g17["hook"]["lead_ok"], f"D1: G17a must see <80 ms genuine lead-in: {self.g17['hook']}")


class TestD2Clip01Out(_G16Fixture):
    def test_g16_out_fails(self):
        r = self.rows["clip_01"]["out"]
        self.assertFalse(r["pass"], f"D2: clip_01 out 33.71 runs into the next sentence: {r}")
        # for the right reason: the locked sentence ends at 'week.' and yesterday's cut runs past it into
        # "All right, you've probably seen ..." (DEC-10: the 120 ms pause after 'week.' is now a legal cut, so
        # the failure is the cut lying 2.3 s outside it, no longer "not cuttable")
        self.assertEqual(r["after_word"], "week.", r)
        self.assertIn("outside the legal range", r["why"], r)


class TestD3Edges(_G16Fixture):
    def test_d3a_clip01_in_fails(self):
        r = self.rows["clip_01"]["in"]
        self.assertFalse(r["pass"], f"D3a: clip_01 in 15.13 starts on '81', not 'It': {r}")
        self.assertEqual(r["before_word"], "It", r)
        self.assertIn("outside the legal range", r["why"], r)
        # DEC-10: the mid-video lead quota is calibrated to v2f (0 ms), so G17a no longer judges this clip's
        # 10 ms lead; the defect fails on the sentence boundary (above), which is what PBX heard ("81")

    def test_d3b_clip02_in_fails(self):
        # The speaker says "...past few days. Of course, of course, Bitcoin dropped ..."; the editor's text
        # (one "Of course") anchors on the REPEATED "of course", so the locked start is not a sentence start
        # ('course' | 'of'). The removed model adjudicator had called that gap a sentence end; with the
        # punctuation layer it is not one. Yesterday's cut at 14.93 lands inside "days" on top of that.
        r = self.rows["clip_02"]["in"]
        self.assertFalse(r["pass"], f"D3b: clip_02 in 14.93 lands inside 'days': {r}")
        self.assertEqual((r["after_word"], r["before_word"]), ("course", "of"), r)
        self.assertIn("does not end a sentence", r["why"], r)
        # DEC-10: G17a no longer judges a mid-video lead (v2f: 0 ms); the defect fails on the boundary above

    def test_d3c_clip02_out_control_passes(self):
        self.assertTrue(self.rows["clip_02"]["out"]["pass"], f"CONTROL D3c: clean out edge must pass G16: {self.rows['clip_02']['out']}")
        self.assertTrue(self.g17["clip_02"]["tail_ok"], f"CONTROL D3c: clean tail must pass G17a: {self.g17['clip_02']}")


class TestG17bRenderedEdges(_G16Fixture):
    """G17b: the render may add silence but must not eat a word. Yesterday's render was faithful to its
    (wrong) cuts, so G17b PASSES on it (D1 is a source lead-in problem: G16 + G17a). A render whose
    fade eats the hook's opening word must FAIL."""

    def _run(self, audio):
        L = _law()
        segs = json.load(open(os.path.join(FIX, "run", "concat_manifest_16x9.json")))["segments"]
        cuts = json.load(open(os.path.join(FIX, "run", "cuts_final.json")))
        ok, table = L.gate_g17_output(audio, segs, cuts, self.tmp,
                                      source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
        return ok, {r["segment"]: r for r in table}

    def test_faithful_render_passes(self):
        ok, rows = self._run(os.path.join(FIX, "audio", "out_16x9.flac"))
        self.assertTrue(rows["hook"]["head_ok"], rows["hook"])

    def _variant(self, name, af):
        out = os.path.join(self.tmp, name)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(FIX, "audio", "out_16x9.flac"),
                        "-af", af, out], check=True)
        return self._run(out)[1]["hook"]

    def test_render_that_eats_the_opening_word_fails(self):
        # the first 160 ms muted: ~70 ms of 'Bitcoin' (onset ~0.09 s) lost, < 85 % of the word left
        row = self._variant("eaten.flac", "volume=enable='between(t,0,0.16)':volume=0")
        self.assertFalse(row["head_ok"], row)

    def test_standard_20ms_fade_passes(self):
        row = self._variant("fade20.flac", "afade=t=in:st=0:d=0.02")
        self.assertTrue(row["head_ok"], row)


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


class TestUnpunctuatedTranscript(unittest.TestCase):
    """E-FAIL-013: the per-gap model adjudicator called 19 of 19 Yahoo Finance gaps sentence ends ('the |
    Wolf', 'of | all', 'pretty | massively'; docs/audits/pulse-sentence-law/1b_fix_punctuation/
    ADJUDICATOR_EVIDENCE_yahoo_sweep.jsonl). No model opinion decides a boundary any more: an unpunctuated
    stretch has none (fail closed); punctuation comes from pipeline/punctuation.py at transcription time."""

    @classmethod
    def setUpClass(cls):
        cls.L = _law()
        cls.sa = cls.L.SourceAudio(os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac"))
        cls.raw = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))["words"]
        cls.punct = json.load(open(os.path.join(FIX, "selection", "transcripts_punctuated",
                                                "36HPi9UZPOc.json")))["words"]

    def gap(self, words, a, b):
        key = lambda w: w["word"].rstrip(".,?!").lower()
        return next(i for i in range(len(words) - 1) if key(words[i]) == a and key(words[i + 1]) == b)

    def test_unpunctuated_gap_is_never_a_boundary(self):
        b = self.L.boundary(self.sa, self.raw, self.gap(self.raw, "times", "i"))
        self.assertFalse(b["valid"], b)
        self.assertIn("unpunctuated", b["reason"], b)
        self.assertFalse(hasattr(self.L, "Adjudicator"))

    def test_the_adjudicators_false_sentence_ends_are_rejected(self):
        for a, b_ in (("the", "wolf"), ("wolf", "of"), ("of", "all"), ("i", "am"), ("is", "up"), ("but", "i"),
                      ("pretty", "massively")):
            b = self.L.boundary(self.sa, self.punct, self.gap(self.punct, a, b_))
            self.assertIsNotNone(b.get("pause"), (a, b_, b))          # the speaker does pause there ...
            self.assertFalse(b["valid"], (a, b_, b))                  # ... but no sentence ends
            self.assertIn("does not end a sentence", b["reason"], (a, b_, b))

    def test_true_sentence_ends_with_a_pause_are_boundaries(self):
        for a, b_ in (("hack", "but"), ("times", "i")):
            b = self.L.boundary(self.sa, self.punct, self.gap(self.punct, a, b_))
            self.assertTrue(b["valid"], (a, b_, b))


class _Fake:
    """faster-whisper stand-in for the punctuation reference decode."""

    def __init__(self, text):
        self.text, self.calls, self.kw = text, 0, {}

    def transcribe(self, path, **kw):
        from types import SimpleNamespace as NS
        self.calls += 1
        self.kw = kw
        return [NS(words=[NS(word=" " + t) for t in self.text.split()])], None


class TestPunctuationLayer(unittest.TestCase):
    def words(self, text):
        return [{"word": t, "start": i * 0.4, "end": i * 0.4 + 0.3} for i, t in enumerate(text.split())]

    def test_marks_move_only_onto_aligned_words_and_words_never_change(self):
        import punctuation as P
        w = self.words("a lot has happened over the past few days of course of course bitcoin dropped hard")
        ref = [{"word": t} for t in "A lot has happened over the past few days. Of course, Bitcoin dropped hard.".split()]
        out, moved = P.transfer(w, ref)
        self.assertEqual([P._key(x["word"]) for x in out], [P._key(x["word"]) for x in w])
        self.assertEqual([(x["start"], x["end"]) for x in out], [(x["start"], x["end"]) for x in w])
        ends = [x["word"] for x in out if _law().is_terminal(x["word"])]
        self.assertEqual(ends, ["days.", "hard."])               # no boundary inside the dropped repetition

    def test_alignment_key_contract(self):
        # cross-LLM M1: the key that aligns the two decodes: case and punctuation fold away, the curly
        # apostrophe equals the straight one, apostrophes stay ("it's" and "its" are different words),
        # digits stay, a pure-punctuation token has no key (never receives a mark)
        import punctuation as P
        self.assertEqual(P._key("Hello,"), P._key("hello"))
        self.assertEqual(P._key("Mr."), "mr")
        self.assertEqual(P._key("it’s"), P._key("it's"))
        self.assertNotEqual(P._key("it's"), P._key("its"))
        self.assertEqual(P._key("$74,000"), "74000")
        for t in ("—", "...", "-", "", None):
            self.assertEqual(P._key(t), "")
        out, moved = P.transfer(self.words("so - it fell"), [{"word": w} for w in "So, - it fell.".split()])
        self.assertEqual([w["word"] for w in out], ["so,", "-", "it", "fell."])   # '-' got no mark

    def test_ensure_leaves_a_punctuated_transcript_alone(self):
        import punctuation as P
        rec = {"words": self.words("It fell. " * 40)}
        fake = _Fake("unused")
        self.assertIs(P.ensure(rec, "x.wav", fake), rec)
        self.assertEqual(fake.calls, 0)

    def test_ensure_records_provenance_and_uses_the_neutral_prompt(self):
        import punctuation as P
        rec = {"words": self.words("so it fell over the weekend and then it bounced")}
        fake = _Fake("So it fell over the weekend. And then it bounced.")
        out = P.ensure(rec, "x.wav", fake)
        self.assertEqual(fake.kw.get("initial_prompt"), P.PROMPT)
        self.assertEqual([x["word"] for x in out["words"]][5:7], ["weekend.", "and"])
        self.assertEqual(out["punctuation"]["source"], "asr_reference")
        self.assertFalse(out["punctuation"]["still_unpunctuated"])

    @unittest.skipUnless(os.environ.get("CUDA_VISIBLE_DEVICES") == "0", "whisper large-v3 needs GPU0")
    def test_yahoo_fixture_is_reproduced_from_the_audio(self):
        import punctuation as P
        from faster_whisper import WhisperModel
        raw = json.load(open(os.path.join(FIX, "run", "transcripts", "36HPi9UZPOc.json")))
        want = json.load(open(os.path.join(FIX, "selection", "transcripts_punctuated", "36HPi9UZPOc.json")))
        import gpu0
        got = P.ensure(raw, os.path.join(FIX, "audio", "src_36HPi9UZPOc.flac"),
                       gpu0.whisper("large-v3"))         # L-r: through swap_to, under the session's GPU0 lease
        self.assertEqual([w["word"] for w in got["words"]], [w["word"] for w in want["words"]])


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
    @classmethod
    def setUpClass(cls):
        cls.S = tempfile.mkdtemp(prefix="g15_")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.S, ignore_errors=True)

    NOV10 = ["DataDash", "Natalie Brunell", "Yahoo Finance"]
    V2F_CH = ["The Bitcoin Layer", "Bitcoin Magazine", "BTC Sessions"]

    def _gates(self, mp4, segs, channels):
        import gates as G
        import qa_gates as Q
        ok15, d15 = G.gate_g15(mp4, segs, self.S, channels=channels)
        ok12, d12 = Q.gate_g12(mp4, segs, len(channels), self.S)
        return ok15, ok12, d15, d12

    def _card(self, p):
        return [{"label": "shoutout", "type": "shoutout", "start": 0.0, "end": _dur(p)}]

    def test_yesterdays_card_fails_g15_on_the_squashed_avatars_inside_round_rings(self):
        # DEC-11 measured: yesterday's RINGS are round and where the layout puts them (G12 now counts 3 of 3);
        # the D4 defect is the 1280x720 video thumbnail squashed into each disc, which G15 fails
        for fmt in ("16x9", "9x16"):
            p = os.path.join(FIX, "video", f"shoutout_{fmt}.mp4")
            ok15, ok12, d15, d12 = self._gates(p, self._card(p), self.NOV10)
            self.assertFalse(ok15, f"G15 passed yesterday's {fmt} card")
            self.assertTrue(d15["ring_aspect_ok"], d15["rings"][:3])
            self.assertFalse(d15["avatar_ok"], d15["avatars"][:3])
            self.assertTrue(ok12, d12)

    def test_v2f_finals_pass_g15_and_g12(self):
        for out, man in (("segment.mp4", "concat_manifest_16x9.json"), ("segment_vertical.mp4", "concat_manifest_9x16.json")):
            segs = json.load(open(os.path.join(V2F, "qa", man)))["segments"]
            ok15, ok12, d15, d12 = self._gates(os.path.join(V2F, "out", out), segs, self.V2F_CH)
            self.assertTrue(ok15 and ok12, f"v2f {out}: G15 {ok15} G12 {ok12} {d15.get('avatars', [])[:3]}")

    def test_a_squeezed_card_fails_g15_on_ring_aspect(self):
        p = os.path.join(FIX, "video", "shoutout_16x9.mp4")
        sq = os.path.join(self.S, "squeezed_16x9.mp4")       # rings drawn 80 % wide: a warped card
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", "scale=iw*0.8:ih,pad=1920:1080:(ow-iw)/2:0",
                        "-c:v", "libx264", "-crf", "18", "-an", sq], check=True)
        ok15, _, d15, _ = self._gates(sq, self._card(sq), self.NOV10)
        self.assertFalse(ok15)
        self.assertFalse(d15["ring_aspect_ok"], d15["rings"][:3])

    def test_g15_fails_closed_without_the_credited_channels(self):
        import gates as G
        p = os.path.join(FIX, "video", "shoutout_16x9.mp4")
        for channels in (None, []):
            ok15, d15 = G.gate_g15(p, self._card(p), self.S, channels=channels)
            self.assertFalse(ok15, channels)
            self.assertFalse(d15["avatar_ok"], channels)

    def test_three_rings_for_four_credited_channels_fail_g12(self):
        import qa_gates as Q
        p = os.path.join(FIX, "video", "shoutout_16x9.mp4")
        ok12, d12 = Q.gate_g12(p, self._card(p), 4, self.S)
        self.assertFalse(ok12, d12)

    @unittest.skipUnless(all(os.path.isfile(os.path.join(REPO, "runs", "pinned_20261111_172202", f)) for f in
                             ("out/segment.mp4", "out/segment_vertical.mp4", "qa/transitions_timeline.json")),
                         "Nov 11 DEC-10 recut not on this machine")
    def test_todays_four_avatar_card_passes_g15_and_g12(self):
        run = os.path.join(REPO, "runs", "pinned_20261111_172202")
        tl = json.load(open(os.path.join(run, "qa", "transitions_timeline.json")))["timeline"]
        for out in ("segment.mp4", "segment_vertical.mp4"):
            ok15, ok12, d15, d12 = self._gates(os.path.join(run, "out", out), tl, self.NOV10 + ["Bitcoin Magazine"])
            self.assertTrue(ok15 and ok12, f"today {out}: G15 {ok15} {d15.get('avatars', [])[:4]} G12 {d12}")

    def test_shoutout_refuses_a_thumbnail_avatar(self):
        import shoutout
        with self.assertRaisesRegex(ValueError, "square"):
            shoutout.validate_avatar(os.path.join(FIX, "video", "natalie_brunell.jpg"))

    def test_shoutout_accepts_a_registered_square_avatar(self):
        # positive control: the v2f BTC Sessions avatar (approved, square) must be accepted
        import shoutout
        reg = {c["display_name"]: c for c in json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))}
        shoutout.validate_avatar(reg["BTC Sessions"]["avatar_path"])

    def test_unregistered_channel_stops(self):
        import shoutout
        with self.assertRaisesRegex(FileNotFoundError, "no verified avatar"):
            shoutout._find_avatar("/nonexistent", "Not A Registered Channel")

    def test_avatar_sha_mismatch_stops(self):
        import shoutout
        reg = json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))
        bad = [dict(c) for c in reg]
        e = next(c for c in bad if c["display_name"] == "Natalie Brunell")
        e["avatar_sha256_prefix"] = "0" * 16
        orig = json.load
        with mock.patch.object(shoutout.json, "load", side_effect=lambda f: bad if f.name.endswith("channels.json") else orig(f)):
            with self.assertRaisesRegex(RuntimeError, "sha256 prefix"):
                shoutout._find_avatar("/nonexistent", "Natalie Brunell")

    def test_no_thumbnail_or_placeholder_fallback(self):
        import shoutout
        src = inspect.getsource(shoutout)
        self.assertFalse('meta.get("thumbnail")' in src, "video-thumbnail fallback still in shoutout.py")
        self.assertFalse("placeholder" in src.lower(), "generated placeholder avatar still in shoutout.py")


if __name__ == "__main__":
    unittest.main()
