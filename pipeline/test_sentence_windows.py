#!/usr/bin/env python3
"""1d (PBX review 2026-11-11): selection proposes SENTENCE-ALIGNED windows of one to three whole
sentences within the 8-12 s hook / 12-20 s clip budgets, and a window the sentence law rejects is
replaced by the next-ranked legal window, never by moving a cut.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_sentence_windows.py"""
import json
import os
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import editorial_select as es  # noqa: E402


def _w(word, t, d=0.3):
    return {"word": word, "start": round(t, 2), "end": round(t + d, 2)}


class TestSentenceSplitting(unittest.TestCase):
    def test_abbreviation_is_not_a_sentence_end(self):
        # whisper writes "U .S." as two tokens; the Nov 10 Natalie window was counted as 4 sentences
        ws = [_w(x, i * 0.4) for i, x in enumerate(
            ["By", "the", "weekend.", "U", ".S.", "Bitcoin", "ETFs", "had", "outflows.", "And", "then."])]
        self.assertEqual(es._word_sentences(ws), [(0, 2), (3, 8), (9, 10)])

    def test_trailing_ellipsis_is_not_a_sentence_end(self):
        ws = [_w(x, i * 0.4) for i, x in enumerate(["So", "anyway...", "it", "fell."])]
        self.assertEqual(es._word_sentences(ws), [(0, 3)])

    def test_question_never_ends_a_window(self):
        self.assertFalse(es._ends_statement("really?"))
        self.assertTrue(es._ends_statement("week."))
        self.assertFalse(es._ends_statement("U.S."))


class TestBudgets(unittest.TestCase):
    def test_budget_constants(self):
        self.assertEqual((es.HOOK_MIN_S, es.HOOK_MAX_S), (8.0, 12.0))
        self.assertEqual((es.CLIP_MIN_S, es.CLIP_MAX_S), (12.0, 20.0))
        self.assertEqual(es.MAX_WINDOW_SENTENCES, 3)

    def test_expansion_stops_at_three_sentences(self):
        # five short sentences (2.0 s each); anchor = sentence 2; a 9-12 s window would need 5 sentences
        ws, t = [], 0.0
        for s in range(5):
            for k in range(4):
                ws.append(_w(f"S{s}w{k}" if k == 0 else f"s{s}w{k}" + ("." if k == 3 else ""), t))
                t += 0.5
            t += 0.3
        sents = es._word_sentences(ws)
        anchor = {"w0": 8, "w1": 11, "start": ws[8]["start"], "end": ws[11]["end"]}
        win, why, span = es.expanded_window(ws, sents, anchor, 9.0, 12.0, lambda txt: (True, "ok"))
        self.assertIsNone(win)
        self.assertLessEqual(span["n_sentences"], 3, span)
        self.assertTrue(any("sentences; direction closed" in c["detail"] for c in span["expansion"]), span)


def _synth(path, words, dur=45.0, sr=16000):
    import numpy as np
    import wave
    x = np.random.default_rng(3).normal(0, 0.0005, int(dur * sr))
    for w in words:
        a, b = int(w["start"] * sr), int(w["end"] * sr)
        x[a:b] += 0.1 * np.sin(2 * np.pi * 300 * np.arange(b - a) / sr)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def _sentences(tag, t, gaps):
    """Sentences of 6 words (0.30 s words, 0.05 s word gaps); gaps[i] = silence after sentence i."""
    ws = []
    for si, gap in enumerate(gaps):
        for wi in range(6):
            ws.append({"word": f"{tag}s{si}w{wi}" + ("." if wi == 5 else ""), "start": round(t, 2),
                       "end": round(t + 0.30, 2)})
            t += 0.35
        t += gap - 0.05
    return ws


class TestNextRankedFallback(unittest.TestCase):
    def test_rejected_clip_is_replaced_by_the_next_legal_window(self):
        import select_passages as sp
        # BBB sentence 6 runs straight into sentence 7 (no pause): a clip ending there is not cuttable
        words = {"AAA": _sentences("a", 2.0, [0.5] * 8), "BBB": _sentences("b", 2.0, [0.5] * 6 + [0.05, 0.5])}

        def text(vid, s0, s1):
            return " ".join(w["word"] for w in words[vid]
                            if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1)

        with tempfile.TemporaryDirectory() as rd:
            os.makedirs(os.path.join(rd, "sources"))
            os.makedirs(os.path.join(rd, "transcripts"))
            hook = {"kind": "hook", "video_id": "AAA", "channel": "The Bitcoin Layer", "start": 110.0, "end": 119.0,
                    "duration": 9.0, "score": 90, "clip_score": 4.5, "text": text("AAA", 5, 6)}
            bad = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
                   "duration": 14.0, "score": 80, "clip_score": 4.0, "text": text("BBB", 4, 6)}
            alt = {"kind": "clip", "video_id": "BBB", "channel": "BTC Sessions", "start": 497.5, "end": 510.0,
                   "duration": 12.5, "score": 70, "clip_score": 3.8, "text": text("BBB", 0, 2)}
            json.dump({"chosen": [hook, bad], "passages": [hook, bad, alt]},
                      open(os.path.join(rd, "passages.json"), "w"))

            def fake_dl(vid, start, end, run_dir, pad=15.0):
                path = os.path.join(run_dir, "sources", f"{vid}.wav")
                _synth(path, words[vid])
                return (path, 95.0 if vid == "AAA" else 495.0)

            def fake_tx(path, vid, run_dir):
                rec = {"words": words[vid]}
                json.dump(rec, open(os.path.join(run_dir, "transcripts", f"{vid}.json"), "w"))
                return rec
            orig = (sp._download_window, sp._whisper_transcribe)
            sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
            try:
                self.assertTrue(sp.select_and_build_edl("test", "bitcoin", rd))
            finally:
                sp._download_window, sp._whisper_transcribe = orig
            edl = json.load(open(os.path.join(rd, "edl.json")))
            report = json.load(open(os.path.join(rd, "SELECT_BOUNDARIES.json")))
            clip = edl["clips"][0]
            self.assertEqual((clip["first_word"], clip["last_word"]), ("bs0w0", "bs2w5."), clip)
            rejected = [r for r in report if r["result"].startswith("rejected")]
            self.assertTrue(rejected and "OUT" in rejected[0]["result"], report)
            self.assertTrue(any(r.get("fallback") and r["result"] == "accepted" for r in report), report)


if __name__ == "__main__":
    unittest.main()
