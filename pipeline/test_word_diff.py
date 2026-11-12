#!/usr/bin/env python3
"""G18 WORD-FOR-WORD (mission 4a): the final says exactly the locked sentences. Must-fail: yesterday's
final (PBX review of pinned_20261110_150345): clip_01 starts on a clipped "above 81,000" and runs into
"All right, you've probably seen people celebrating" (D2/D3a); clip_02 starts on "days of course" (D3b).
Run (GPU parts): cd ~/protocol_pulse && CUDA_VISIBLE_DEVICES=0 python3 -m pytest -q pipeline/test_word_diff.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
FIX = os.path.join(REPO, "tests", "fixtures", "pulse_20261110")

import word_diff as W  # noqa: E402


class TestCanonical(unittest.TestCase):
    """Two whisper passes over the SAME audio render numbers and disfluent repeats differently (measured on
    the Nov 10 fixture); both sides are canonicalised alike, real word changes still count."""

    def test_asr_renderings_of_the_same_words_are_equal(self):
        for a, b in (("It went from above $81 ,000 after the election.", "it went from above 81,000 after the election"),
                     ("U .S. Bitcoin ETFs had about $1 .3 billion", "US Bitcoin ETFs had about one point three billion dollars"),
                     ("around $74 000, around the 50 weekly MA", "around seventy four thousand dollars around the fifty weekly MA"),
                     ("241 House winners and 50 senators", "two hundred forty one house winners and fifty senators"),
                     ("up still 25 % off the lows", "up still twenty five percent off the lows")):
            self.assertEqual(W.diff(a, b), [], (a, b))

    def test_a_repeat_only_difference_is_kept_as_evidence(self):
        """GPT-cut F05: a disfluent repeat rendered differently is NOT removed from the comparison; it is a
        repeat-only difference (gone with collapse=True) that gate_g18 decides by the audio (span_matches)."""
        a, b = "days. Of course, of course, Bitcoin dropped", "days of course bitcoin dropped"
        self.assertNotEqual(W.diff(a, b), [])
        self.assertEqual(W.diff(a, b, collapse=True), [])
        self.assertNotEqual(W.diff("bitcoin is falling", "bitcoin is falling bitcoin is falling"), [])

    def test_units_and_signs_are_not_erased(self):
        """GPT-cut F04: five percent vs five dollars, -5% vs +5%, $5 vs 5% differ; only a '$' formatting
        difference (whisper writes '$74,000' for a spoken 'seventy-four thousand') is tolerated."""
        for a, b in (("bitcoin fell five percent today", "bitcoin fell five dollars today"),
                     ("it moved -5% on the day", "it moved +5% on the day"),
                     ("it costs $5", "it costs 5%")):
            self.assertNotEqual(W.diff(a, b), [], (a, b))
        self.assertEqual(W.diff("around $74,000 today", "around 74 000 today"), [])
        self.assertEqual(W.diff("it fell -5%", "it fell minus five percent"), [])

    def test_a_half_written_or_spoken_is_the_same_number(self):
        """Recut run 6 G18 clip_02: the final was heard as 'five and a half percent', the source span as
        '5 .5%' (the same audio). Equal both ways; any real difference in the number still counts."""
        for a, b in (("dropping 5 .5%, pushing it", "dropping five and a half percent pushing it"),
                     ("dropping five and a half percent, pushing it", "dropping 5.5% pushing it"),
                     ("up two and a half percent", "up 2.5 percent")):
            self.assertEqual(W.diff(a, b), [], (a, b))
        for a, b in (("dropping 5.5%", "dropping five percent"),            # the half is missing
                     ("dropping 5%", "dropping five and a half percent"),   # a half was added
                     ("dropping 6.5%", "dropping five and a half percent"),
                     ("a year and a half ago", "a year ago")):              # not after a number: words count
            self.assertNotEqual(W.diff(a, b), [], (a, b))
        self.assertEqual(W.norm("a year and a half"), ["a", "year", "and", "a", "half"])

    def test_missing_added_and_changed_words_count(self):
        d = W.diff("It went from above $81,000 after the election. That was the week.",
                   "81,000 after the election. That was the week. All right, you've probably seen")
        self.assertIn(("delete", "it went from above", ""), d)
        self.assertIn(("insert", "", "all right you've probably seen"), d)   # canon keeps apostrophes (M1)
        self.assertEqual(W.diff("the market fell", "the market rose"), [("replace", "fell", "rose")])
        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply"), [("insert", "", "fell sharply")])
        self.assertEqual(W.diff("bitcoin fell", "bitcoin fell fell sharply", collapse=True), [("insert", "", "sharply")])

    def test_edges_compare_the_first_and_last_two_words(self):
        self.assertEqual(W.edges("But I don't check it. Many times.", "but i don't check it many times"), [])
        self.assertEqual(W.edges("It went from above $81,000. Just last week.",
                                 "above 81,000. Just last week. All right, people celebrating"),
                         [("start", "it went", "above 81000"), ("end", "last week", "people celebrating")])


class TestSpanMatches(unittest.TestCase):
    """span_matches (sentence_law): the final's segment IS the source span when, gain removed, no 150 ms run of
    speech frames differs by more than 6 dB. Synthetic speech-like bursts; must-pass: the same span with a gain,
    a quiet bed and a codec round trip; must-fail: the same span with 300 ms of it repeated (a concat defect)."""

    @classmethod
    def setUpClass(cls):
        import numpy as np
        import subprocess
        cls.tmp = tempfile.mkdtemp(prefix="span_")
        sr, rng = 16000, np.random.default_rng(7)
        t = np.arange(int(sr * 6.0)) / sr
        env = np.zeros_like(t)
        k = 0.2
        while k < 5.8:                                       # syllable-like bursts of varying length and level
            d = rng.uniform(0.08, 0.25)
            env[(t >= k) & (t < k + d)] = rng.uniform(0.2, 0.9)
            k += d + rng.uniform(0.05, 0.2)
        src = env * np.sin(2 * np.pi * 220 * t) * (1 + 0.3 * np.sin(2 * np.pi * 3 * t))
        bed = 0.003 * rng.standard_normal(len(t))

        def wav(name, x):
            path = os.path.join(cls.tmp, name)
            raw = path + ".f32"
            x.astype(np.float32).tofile(raw)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", raw,
                            "-c:a", "aac", "-b:a", "192k", path], check=True)
            return path
        cls.src = wav("src.m4a", src)
        cls.same = wav("same.m4a", 0.5 * src + bed)                              # gain + bed + codec
        rep = np.concatenate([src[:int(sr * 3.0)], src[int(sr * 2.7):int(sr * 3.0)], src[int(sr * 3.0):]])[:len(src)]
        cls.repeat = wav("repeat.m4a", 0.5 * rep + bed)                          # 300 ms repeated at 3.0 s
        # cycle-2 #4: a word copied INTO the longest interior pause, nothing after it moves
        quiet = env == 0
        best, run_start = (0, 0), None
        for i in range(int(sr * 0.5), int(sr * 5.4)):
            if quiet[i] and run_start is None:
                run_start = i
            elif not quiet[i] and run_start is not None:
                best = max(best, (i - run_start, run_start))
                run_start = None
        n, at = best
        ins = src.copy()
        w = min(n - int(sr * 0.02), int(sr * 0.15))
        burst = next(i for i in range(int(sr * 0.2), len(env)) if env[i] > 0)
        ins[at + int(sr * 0.01):at + int(sr * 0.01) + w] = src[burst:burst + w]
        cls.pause_insert = wav("pause_insert.m4a", 0.5 * ins + bed)
        cls.pause_ms = n * 1000 // sr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_same_span_matches_and_a_repeat_does_not(self):
        import sentence_law as L
        ok, det = L.span_matches(self.src, self.same, 0.0, 5.9, 0.0)
        self.assertTrue(ok, det)
        ok, det = L.span_matches(self.src, self.repeat, 0.0, 5.9, 0.0)
        self.assertFalse(ok, det)

    def test_a_word_inserted_into_a_pause_is_seen(self):
        """cycle-2 #4: the longest interior pause gets a copy of a word; nothing after it moves."""
        import sentence_law as L
        self.assertGreaterEqual(self.pause_ms, 120, "fixture needs a pause to insert into")
        ok, det = L.span_matches(self.src, self.pause_insert, 0.0, 5.9, 0.0)
        self.assertFalse(ok, det)


RUN_CUT = os.path.join(REPO, "runs", "pinned_20261111_172202_replay_cut1329")


@unittest.skipUnless(all(os.path.exists(os.path.join(RUN_CUT, p)) for p in ("out/segment.mp4", "cuts_final.json",
                                                                           "qa/concat_manifest_16x9.json")),
                     "Nov 11 replay run not on this machine")
class TestSpanMatchesRealSpeech(unittest.TestCase):
    """claude-fable cycle 2 F8: the repeat adjudication on REAL speech. must-pass: the corrected Nov 10 cut's
    clip_02 in its final IS its source span; must-fail: the same final with 300 ms of clip_02's speech repeated
    mid-segment (a concat defect: everything after it moves), trimmed back to the same length."""

    def test_the_real_segment_matches_and_a_real_repeat_does_not(self):
        import subprocess
        import sentence_law as L
        segs = {s_["label"]: s_ for s_ in json.load(open(os.path.join(RUN_CUT, "qa", "concat_manifest_16x9.json")))["segments"]}
        cut = {c["clip_id"]: c for c in json.load(open(os.path.join(RUN_CUT, "cuts_final.json")))}["clip_02"]
        seg, src = segs["clip_02"], os.path.join(RUN_CUT, "sources", f"{cut['video_id']}.mp4")
        final = os.path.join(RUN_CUT, "out", "segment.mp4")
        pad = float(cut.get("lead_in_pad_s") or 0)
        ok, det = L.span_matches(src, final, cut["cut_in"], cut["cut_out"], float(seg["start"]), pad)
        self.assertTrue(ok, det)
        tmp = tempfile.mkdtemp(prefix="span_real_")
        self.addCleanup(shutil.rmtree, tmp, True)
        t = round((seg["start"] + seg["end"]) / 2, 3)
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    final], capture_output=True, text=True).stdout)
        rep = os.path.join(tmp, "repeat.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", final, "-filter_complex",
                        f"[0:a]atrim=0:{t},asetpts=N/SR/TB[a1];[0:a]atrim={t - 0.3}:{t},asetpts=N/SR/TB[r];"
                        f"[0:a]atrim={t},asetpts=N/SR/TB[a2];[a1][r][a2]concat=n=3:v=0:a=1,atrim=0:{dur}[a]",
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", rep], check=True)
        ok, det = L.span_matches(src, rep, cut["cut_in"], cut["cut_out"], float(seg["start"]), pad)
        self.assertFalse(ok, det)


def _clips():
    """Yesterday's three clips: the editor's sentences locked on today's transcripts (as the G16 fixture),
    and the source span each was cut from."""
    import sentence_law as L
    tmp = tempfile.mkdtemp(prefix="g18_")
    try:
        shutil.copytree(os.path.join(FIX, "run", "transcripts"), os.path.join(tmp, "t"))
        for f in os.listdir(os.path.join(FIX, "selection", "transcripts_punctuated")):
            shutil.copy(os.path.join(FIX, "selection", "transcripts_punctuated", f), os.path.join(tmp, "t"))
        edl = json.load(open(os.path.join(FIX, "run", "edl.json")))
        sel = {p["video_id"]: p for p in json.load(open(os.path.join(FIX, "selection", "B3_chosen.json")))["chosen"]}
        cuts = {c["clip_id"]: c for c in json.load(open(os.path.join(FIX, "run", "cuts_final.json")))}
        out = {}
        for label, seg in [("hook", edl["hook"])] + [(f"clip_{c['index']:02d}", c) for c in edl["clips"]]:
            words = json.load(open(os.path.join(tmp, "t", f"{seg['video_id']}.json")))["words"]
            i0, i1, _ = L.anchor(words, sel[seg["video_id"]]["text"])
            out[label] = {"lock_text": " ".join(w["word"] for w in words[i0:i1 + 1]),
                          "source": os.path.join(FIX, "audio", f"src_{seg['video_id']}.flac"),
                          "cut_in": cuts[label]["cut_in"], "cut_out": cuts[label]["cut_out"]}
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(os.path.exists("/dev/nvidia0"), "whisper large-v3 needs a GPU")
class TestYesterdaysFinal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        segs = json.load(open(os.path.join(FIX, "run", "concat_manifest_16x9.json")))["segments"]
        cls.ok, rows = W.gate_g18(os.path.join(FIX, "audio", "out_16x9.flac"), segs, _clips())
        cls.rows = {r["segment"]: r for r in rows}

    def test_gate_fails(self):
        self.assertFalse(self.ok, self.rows)

    def test_clip01_clipped_start_and_run_on_fail(self):            # D3a + D2
        r = self.rows["clip_01"]
        self.assertFalse(r["pass"], r)
        self.assertEqual([e[0] for e in r["edges"]], ["start", "end"], r)
        self.assertIn("celebrating", r["edges"][1][2], r)
        self.assertIn(("insert", "", "above"), r["identity"], r)    # the clipped fragment is in the final only

    def test_clip02_start_inside_days_fails(self):                  # D3b
        r = self.rows["clip_02"]
        self.assertFalse(r["pass"], r)
        self.assertEqual(r["edges"][0][:2], ("start", "of course"), r)
        self.assertTrue(r["edges"][0][2].startswith("days"), r)

    def test_hook_words_are_intact(self):
        # D1 (the hook's onset) is acoustic and caught by G16/G17; its words are all there. The lock's own
        # ASR rendering of the fast "73,400, 500" differs from the final's: reported, not gated.
        r = self.rows["hook"]
        self.assertTrue(r["pass"], r)
        self.assertTrue(r["lock_diff_reported"], r)


if __name__ == "__main__":
    unittest.main()
