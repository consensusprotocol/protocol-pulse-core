#!/usr/bin/env python3
"""Law L-e (2026-11-11, gospel SENTENCE LAW "punctuation is added at transcription time"): the editorial word pass
(transcript_store.acquire prefer_words) reads sentences only from a sentence-ready record: the verbatim
whisper_words decode where it needs no restoration, else a whisper_words_punct record whose marks come from a
prompted large-v3 reference decode of the same audio, onto aligned words only (pipeline/punctuation.py).
must-fail  Altcoin Daily Ov5jg52HqIY's stored verbatim record (fresh run 2026-11-11 21:39 UTC): 373 words with no
           sentence mark, so its verified quote read as one 35.28 s 'sentence' (134.80-170.08) and no window existed
must-pass  the same words after restoration (the real large-v3 batched reference decode, frozen as
           Ov5jg52HqIY.reference_words.json): identical word keys and timings; the quote's sentence is 161.14-170.08,
           "Even thinking about the seasonality, ... the midterms.", and with its sentence-initial capital transferred
           (audit batch13 U-1) it is a valid 8.94 s hook window; without the capital it was rejected as lower-case
unit       acquire upgrades a stored raw record once (the raw record stays), a failed restoration is not
           sentence-ready, select_passages' reference decode keeps its own settings
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_punct_word_pass.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import editorial_select as E  # noqa: E402
import punctuation as P  # noqa: E402
import transcript_store as ts  # noqa: E402

FIX = os.path.join(REPO, "tests", "fixtures", "punct_20261111")
QUOTE = "there's been a scare after the blue wave of the midterms. The market is bearish."


def _fixture(name):
    return json.load(open(os.path.join(FIX, f"Ov5jg52HqIY.{name}.json")))


def _quote_window(words, lo=E.HOOK_MIN_S, hi=E.HOOK_MAX_S):
    """The production window rule (expanded_window), no adjacent sentence admitted."""
    sents = E._word_sentences(words)
    anc = E.align_quote(QUOTE, words, 130, 200)
    return E.expanded_window(words, sents, anc, lo, hi, lambda t: (False, "test: no adjacent sentence"))


class TestAltcoinDailyFixture(unittest.TestCase):
    def test_the_verbatim_record_reads_a_35_s_run_on_sentence(self):
        raw = _fixture("whisper_words")
        self.assertFalse(ts.sentence_ready(raw))
        for lo, hi in ((E.HOOK_MIN_S, E.HOOK_MAX_S), (E.CLIP_MIN_S, E.CLIP_MAX_S)):   # the fresh run's ledger
            w, why, span = _quote_window(raw["words"], lo, hi)
            self.assertIsNone(w)
            self.assertEqual((span["start"], span["end"], span["duration"]), (134.8, 170.08, 35.28))
            self.assertEqual(why, f"quote sentence(s) 35.28 s > maximum {hi} s")

    def test_the_restored_record_ends_its_sentences(self):
        raw, pun = _fixture("whisper_words"), _fixture("whisper_words_punct")
        ref = _fixture("reference_words")["words"]
        out, moved = P.transfer(raw["words"], ref)
        marks_only = [dict(w) for w in out]
        out, cased = P.transfer_case(out, ref)
        self.assertEqual(out, pun["words"])                    # the fixture is exactly what the code produces
        self.assertEqual((moved, cased), (92, 41))
        self.assertTrue(ts.sentence_ready(pun))
        self.assertEqual([(P._key(a["word"]), a["start"], a["end"]) for a in raw["words"]],
                         [(P._key(b["word"]), b["start"], b["end"]) for b in pun["words"]])   # words never change
        self.assertEqual(pun["punctuation"]["verbatim_transcript_sha256"], raw["transcript_sha256"])
        self.assertIn("large-v3", pun["punctuation"]["model"])
        self.assertNotIn("distil", pun["punctuation"]["model"])
        w, why, span = _quote_window(pun["words"])
        self.assertEqual((span["start"], span["end"], span["duration"]), (161.14, 170.08, 8.94))
        self.assertIsNone(why)                                 # a valid hook window
        self.assertTrue(w["text"].startswith("Even thinking about the seasonality,"))
        w, why, span = _quote_window(marks_only)               # marks without the capital: rejected as lower-case
        self.assertIn("lower-case", why)

    def test_case_transfer_only_follows_a_sentence_end(self):
        words = [{"word": w} for w in "it fell. so what i mean, the market is up. U.S. stocks rose".split()]
        ref = [{"word": w} for w in "It fell. So what I mean, The market is up. U.S. Stocks rose".split()]
        out, cased = P.transfer_case(words, ref)
        self.assertEqual(" ".join(w["word"] for w in out), "it fell. So what i mean, the market is up. U.S. stocks rose")
        self.assertEqual(cased, 1)            # not the first word, not after a comma, not after 'U.S.', never lower-cases
        words = [{"word": w} for w in "he left. jerome said".split()]       # only the verbatim ends a sentence there
        out, cased = P.transfer_case(words, [{"word": w} for w in "He left, Jerome said".split()])
        self.assertEqual((out[2]["word"], cased), ("jerome", 0))           # both decodes must agree (Heimdall batch13)
        out, cased = P.transfer_case([{"word": " so"}, {"word": "x."}, {"word": " so "}],
                                     [{"word": "So"}, {"word": "x."}, {"word": "So"}])
        self.assertEqual([w["word"] for w in out], [" so", "x.", " So "])  # only the first letter changes


class FakeRef:
    """A reference decode: the same words with sentence punctuation."""
    def __init__(self, words):
        self.words, self.calls, self.kwargs = words, 0, None

    def transcribe(self, path, **kw):
        self.calls += 1
        self.kwargs = kw

        class W:
            def __init__(self, w):
                self.word = w

        class S:
            def __init__(self, ws):
                self.words = ws
        return [S([W(w) for w in self.words])], None


class TestAcquireUpgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="punctwp_")
        self.saved = (ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR, ts.download_audio, ts._reference)
        ts.STORE_DIR = self.tmp
        ts.TRANSCRIPTS_DIR = os.path.join(self.tmp, "transcripts")
        ts.STATE_DIR = os.path.join(self.tmp, "state")
        ts.MEDIA_DIR = os.path.join(self.tmp, "media")
        self.vid = "PUNCTAAAAA1"
        self.meta = {"schema": 1, "video_id": self.vid, "canonical_url": ts.canonical_url(self.vid),
                     "channel_id": "UCfakefakefakefakefake01", "channel_name": "Fake Channel",
                     "exact_title": "show", "published_at": "2026-11-11T00:00:00+00:00", "duration": 600}
        os.makedirs(ts._vdir(self.vid))
        ts._write_once(os.path.join(ts._vdir(self.vid), "meta.json"), self.meta)
        self.plain = [f"word{i}" for i in range(130)]                 # 130 words, no mark: needs restoration
        words = [{"word": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(self.plain)]
        ts._store(ts._make_record(self.meta, "whisper_words", "fake distil", ts.sentences_from_words(words),
                                  extra={"words": words}))
        audio = os.path.join(self.tmp, "a.m4a")
        open(audio, "wb").write(b"fake audio")

        def fake_download(video_id):
            p = os.path.join(self.tmp, f"{video_id}.m4a")
            shutil.copy(audio, p)
            return p
        ts.download_audio = fake_download
        self.ref = FakeRef([w + ("." if i % 10 == 9 else "") for i, w in enumerate(self.plain)])

    def tearDown(self):
        (ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR, ts.download_audio, ts._reference) = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_stored_raw_record_is_restored_once_and_kept(self):
        ts._reference = lambda: self.ref
        raw = ts.canonical_transcript(self.vid)
        self.assertFalse(ts.sentence_ready(raw))
        r, st = ts.acquire(self.vid, prefer_words=True)
        self.assertEqual((st, r["transcript_method"]), ("cached+punctuation", "whisper_words_punct"))
        self.assertTrue(ts.sentence_ready(r))
        self.assertEqual(r["punctuation"]["marks_transferred"], 13)
        self.assertEqual(r["punctuation"]["cases_transferred"], 0)          # the fake reference is lower-case
        self.assertEqual(r["punctuation"]["verbatim_transcript_sha256"], raw["transcript_sha256"])
        self.assertEqual(len(E._word_sentences(r["words"])), 13)
        self.assertEqual(self.ref.kwargs, {"language": "en", "word_timestamps": True, "initial_prompt": P.PROMPT,
                                           "batch_size": ts.WHISPER_BATCH})
        methods = sorted(x["transcript_method"] for x in ts.transcript_records(self.vid))
        self.assertEqual(methods, ["whisper_words", "whisper_words_punct"])        # the verbatim record stays
        r2, st2 = ts.acquire(self.vid, prefer_words=True)
        self.assertEqual((st2, r2["transcript_method"], self.ref.calls), ("cached", "whisper_words_punct", 1))

    def test_a_failed_restoration_is_not_sentence_ready(self):
        def boom():
            raise RuntimeError("CUDA out of memory (simulated)")
        ts._reference = boom
        r, st = ts.acquire(self.vid, prefer_words=True)
        self.assertEqual((st, r["transcript_method"]), ("punctuation_failed", "whisper_words"))
        self.assertFalse(ts.sentence_ready(r))                 # editorial_select treats it as a failure
        self.assertIn("out of memory", ts.LAST_ERROR[self.vid])


class TestOneWhisperModelAtATime(unittest.TestCase):
    """Heimdall batch13: the word pass's GPU0 arbitration proves 7 GB free, so distil-large-v3 and the large-v3
    reference are never resident together (stubbed models, no GPU)."""
    def test_loading_one_drops_the_other(self):
        import types
        fw = types.ModuleType("faster_whisper")
        fw.WhisperModel = type("WM", (), {"__init__": lambda self, name, **kw: setattr(self, "name", name)})
        fw.BatchedInferencePipeline = type("BP", (), {"__init__": lambda self, model: setattr(self, "model", model)})
        saved = (sys.modules.get("faster_whisper"), os.environ.get("CUDA_VISIBLE_DEVICES"), ts._WHISPER, ts._REFERENCE)
        sys.modules["faster_whisper"], os.environ["CUDA_VISIBLE_DEVICES"] = fw, "0"
        ts._WHISPER = ts._REFERENCE = None
        try:
            a = ts._whisper()
            self.assertEqual((a.model.name, ts._REFERENCE), (ts.WHISPER_MODEL, None))
            self.assertIs(ts._whisper(), a)
            b = ts._reference()
            self.assertEqual((b.model.name, ts._WHISPER), (ts.REFERENCE_MODEL, None))
            ts._whisper()
            self.assertIsNone(ts._REFERENCE)
        finally:
            mod, cvd, ts._WHISPER, ts._REFERENCE = saved
            if mod is None:
                sys.modules.pop("faster_whisper", None)
            else:
                sys.modules["faster_whisper"] = mod
            if cvd is None:
                os.environ.pop("CUDA_VISIBLE_DEVICES", None)
            else:
                os.environ["CUDA_VISIBLE_DEVICES"] = cvd


class TestSelectPassagesReferenceUnchanged(unittest.TestCase):
    def test_default_settings_are_select_passages_verbatim_decode(self):
        ref = FakeRef(["Hello."])
        P.reference_decode("x.wav", ref)
        self.assertEqual(ref.kwargs, {"language": "en", "word_timestamps": True, "initial_prompt": P.PROMPT,
                                      "beam_size": 5, "vad_filter": False})

    def test_select_passages_never_transfers_case(self):
        words = [{"word": w} for w in ("word " * 130).split()]
        ref = FakeRef([w + ("." if i % 10 == 9 else "") for i, w in enumerate(("Word " * 130).split())])
        out = P.ensure({"words": words}, "x.wav", ref)               # select_passages' call: case=False
        self.assertNotIn("cases_transferred", out["punctuation"])
        self.assertFalse([w for w in out["words"] if w["word"][:1].isupper()])


if __name__ == "__main__":
    unittest.main()
