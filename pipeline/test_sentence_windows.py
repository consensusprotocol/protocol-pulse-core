#!/usr/bin/env python3
"""1d (PBX review 2026-11-11): selection proposes SENTENCE-ALIGNED windows of one to three whole
sentences within the 8-12 s hook / 12-20 s clip budgets, and a window the sentence law rejects is
replaced by the next-ranked legal window, never by moving a cut.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_sentence_windows.py"""
import json
import os
import shutil
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


def _dump(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f)


def _load(path):
    with open(path) as f:
        return json.load(f)


def _sentences(tag, t, gaps, per=12):
    """Sentences of `per` words (0.30 s words, 0.05 s word gaps); gaps[i] = silence after sentence i."""
    ws = []
    for si, gap in enumerate(gaps):
        for wi in range(per):
            ws.append({"word": f"{tag}s{si}w{wi}" + ("." if wi == per - 1 else ""), "start": round(t, 2),
                       "end": round(t + 0.30, 2)})
            t += 0.35
        t += gap - 0.05
    return ws


class TestNextRankedFallback(unittest.TestCase):
    """Windows are declared exactly where their text is (12-word sentences: 2 = 8.8 s hook, 3 = 13.45 s
    clip). BBB sentence 4 runs straight into sentence 5 (no pause): no window may end or start there."""
    OFF = {"AAA": 95.0, "BBB": 495.0}

    def setUp(self):
        self.words = {"AAA": _sentences("a", 2.0, [0.5] * 8),
                      "BBB": _sentences("b", 2.0, [0.5, 0.5, 0.5, 0.5, 0.05, 0.5, 0.5, 0.5, 0.5, 0.5])}

    def window(self, vid, s0, s1, kind, score):
        ws = [w for w in self.words[vid] if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1]
        st, en = ws[0]["start"] + self.OFF[vid], ws[-1]["end"] + self.OFF[vid]
        return {"kind": kind, "video_id": vid, "channel": {"AAA": "The Bitcoin Layer", "BBB": "BTC Sessions"}[vid],
                "start": round(st, 2), "end": round(en, 2), "duration": round(en - st, 2), "score": score * 20,
                "clip_score": score, "text": " ".join(w["word"] for w in ws)}

    def run_select(self, chosen, pool):
        import select_passages as sp
        rd = tempfile.mkdtemp(prefix="fb_")
        self.addCleanup(shutil.rmtree, rd, True)
        os.makedirs(os.path.join(rd, "sources"))
        os.makedirs(os.path.join(rd, "transcripts"))
        _dump(os.path.join(rd, "passages.json"), {"chosen": chosen, "passages": pool})

        def fake_dl(vid, start, end, run_dir, pad=15.0):
            path = os.path.join(run_dir, "sources", f"{vid}.wav")
            _synth(path, self.words[vid], dur=self.words[vid][-1]["end"] + 5.0)
            return (path, self.OFF[vid])

        def fake_tx(path, vid, run_dir):
            rec = {"words": self.words[vid]}
            _dump(os.path.join(run_dir, "transcripts", f"{vid}.json"), rec)
            return rec
        orig = (sp._download_window, sp._whisper_transcribe)
        sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
        try:
            ok = sp.select_and_build_edl("test", "bitcoin", rd)
        finally:
            sp._download_window, sp._whisper_transcribe = orig
        edl = _load(os.path.join(rd, "edl.json")) if ok else None
        return ok, edl, _load(os.path.join(rd, "SELECT_BOUNDARIES.json"))

    def test_rejected_clip_is_replaced_by_the_next_legal_window(self):
        hook, bad, short, alt = (self.window("AAA", 5, 6, "hook", 4.5), self.window("BBB", 2, 4, "clip", 4.0),
                                 self.window("BBB", 0, 1, "clip", 3.9), self.window("BBB", 6, 8, "clip", 3.8))
        ok, edl, report = self.run_select([hook, bad], [hook, bad, short, alt])
        self.assertTrue(ok, report)
        self.assertEqual((edl["hook"]["first_word"], edl["hook"]["last_word"]), ("as5w0", "as6w11."))
        clip = edl["clips"][0]
        self.assertEqual((clip["first_word"], clip["last_word"]), ("bs6w0", "bs8w11."), report)
        rej = next(r for r in report if r.get("video_id") == "BBB" and r["result"].startswith("rejected"))
        self.assertIn("OUT", rej["result"], report)          # rejected for its missing pause, nothing else
        self.assertTrue(any(r.get("fallback") and r["result"] == "accepted" for r in report), report)
        # the higher-ranked 8.8 s window is below the 12 s clip budget: never tried
        self.assertFalse(any(r["window_full_video_s"][0] == short["start"] for r in report), report)

    def test_a_window_taken_by_a_fallback_is_never_used_twice(self):
        # slot 1 (bad) falls back to 'alt'; slot 2 is the editor's own choice of that same window -> skipped
        hook, bad, alt = (self.window("AAA", 5, 6, "hook", 4.5), self.window("BBB", 2, 4, "clip", 4.0),
                          self.window("BBB", 6, 8, "clip", 3.8))
        ok, edl, report = self.run_select([hook, bad, alt], [hook, bad, alt])
        self.assertTrue(ok, report)
        keys = [(c["video_id"], c["word_start"]) for c in edl["clips"]]
        self.assertEqual(keys, [("BBB", self.words["BBB"][6 * 12]["start"])], report)

    def test_budget_holds_for_the_locked_words_not_the_declared_window(self):
        # declared as 13.5 s, but its text is two sentences (8.8 s): the cut clip would be under budget
        hook, liar, alt = (self.window("AAA", 5, 6, "hook", 4.5), self.window("BBB", 6, 7, "clip", 4.0),
                           self.window("BBB", 6, 8, "clip", 3.8))
        liar["end"] = round(liar["start"] + 13.5, 2)
        liar["duration"] = 13.5
        ok, edl, report = self.run_select([hook, liar], [hook, liar, alt])
        self.assertTrue(ok, report)
        rej = next(r for r in report if r.get("slot") == 1 and r["result"].startswith("rejected"))
        self.assertIn("locked words span 8.8 s, outside the clip budget", rej["result"], report)
        self.assertEqual(edl["clips"][0]["last_word"], "bs8w11.", report)


if __name__ == "__main__":
    unittest.main()
