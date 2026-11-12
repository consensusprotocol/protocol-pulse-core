#!/usr/bin/env python3
"""pipeline/backtest.py (orchestrator order 2026-11-11 '21:10'): every saved universe through editorial selection only,
with its own transcript records, existing word records only (no download, no GPU swap), its own story-engine
items and 'now' pinned to its run.
unit   saved-day discovery and priority; the story items rebuilt from a day's candidates; word sources (a store word
       record first, else a run's large-v3 transcript, else the gate text); select_story's hooks: with
       transcript_fn / words_fn it never acquires, transcribes or releases GPU0
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_backtest.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)
import backtest as B  # noqa: E402
import transcript_store as ts  # noqa: E402
from test_editorial_robust import FakeLLM, Orchestration  # noqa: E402


def _saved(started="2026-11-10T09:31:52+00:00", shas=True):
    return {"started": started, "today": started[:10],
            "universe": [{"video_id": "VIDAAAAAAA1", "channel": "X", "channel_id": "UCx", "title": "t",
                          "published_at": started, "age_h": 3.0, "transcript_sha256": "ab" * 32 if shas else None}],
            "story_engine": {"generated_at": "2026-11-10T09:10:00+00:00"},
            "candidates": [{"origin": "story_engine", "engine_rank": 1, "engine_score": 50, "headline": "H1",
                            "summary": "S1", "source_domain": "d.com", "age_h": 2.0},
                           {"origin": "transcript_cluster", "headline": "C1"}]}


class TestDays(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="btdays_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _day(self, name, saved):
        os.makedirs(os.path.join(self.tmp, name))
        json.dump(saved, open(os.path.join(self.tmp, name, "TOPIC_SELECTION.json"), "w"))

    def test_only_days_with_a_saved_universe_count_and_the_priority_day_leads(self):
        self._day("fresh_20261112_000000", _saved("2026-11-12T00:00:00+00:00"))
        self._day("fresh_20261110_093150", _saved())
        self._day("fresh_20261106_133059", {"started": "2026-11-06T13:30:59+00:00", "universe": []})
        self._day("fresh_20261107_064831", _saved("2026-11-07T06:48:31+00:00", shas=False))
        names = [os.path.basename(d) for d in B.saved_days(self.tmp)]
        self.assertEqual(names, ["fresh_20261110_093150", "fresh_20261112_000000"])

    def test_the_story_items_are_the_days_own(self):
        st = B.stories_of(_saved())
        self.assertEqual(st["generated_at"], "2026-11-10T09:10:00+00:00")
        self.assertEqual([s["headline"] for s in st["stories"]], ["H1"])               # clusters are re-derived
        self.assertEqual(st["stories"][0]["freshness_minutes"], 120)


class TestWordSources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="btwords_")
        self.saved = (ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR)
        ts.STORE_DIR = self.tmp
        ts.TRANSCRIPTS_DIR = os.path.join(self.tmp, "transcripts")
        ts.STATE_DIR = os.path.join(self.tmp, "state")
        ts.MEDIA_DIR = os.path.join(self.tmp, "media")
        self.runs = os.path.join(self.tmp, "runs")

    def tearDown(self):
        ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_store_then_run_transcript_then_the_gate(self):
        words = [{"word": w + ".", "start": i, "end": i + 0.5} for i, w in enumerate(["One", "Two", "Three"])]
        os.makedirs(os.path.join(self.runs, "pinned_x", "transcripts"))
        json.dump({"words": words}, open(os.path.join(self.runs, "pinned_x", "transcripts", "RUNVIDAAAA1.json"), "w"))
        fn = B.offline_words(self.runs)
        r, st = fn("RUNVIDAAAA1")
        self.assertTrue(st.startswith("run transcript"))
        self.assertEqual((r["words"], r["transcript_method"]), (words, "run_transcript:large-v3"))
        r, st = fn("NOWORDSAAA1")
        self.assertIsNone(r)
        self.assertIn("no word record", st)
        vid = "STOREVIDAA1"                                   # a sentence-ready store record wins over the run's
        meta = {"schema": 1, "video_id": vid, "canonical_url": ts.canonical_url(vid), "channel_id": "UCfakefake03",
                "channel_name": "Fake", "exact_title": "t", "published_at": "2026-11-10T00:00:00+00:00", "duration": 9}
        os.makedirs(ts._vdir(vid))
        ts._store(ts._make_record(meta, "whisper_words", "fake", ts.sentences_from_words(words), extra={"words": words}))
        json.dump({"words": words}, open(os.path.join(self.runs, "pinned_x", "transcripts", f"{vid}.json"), "w"))
        r, st = fn(vid)
        self.assertEqual((st, r["transcript_method"]), ("store whisper_words", "whisper_words"))


class TestHooks(Orchestration):
    def test_with_the_hooks_selection_never_acquires_transcribes_or_releases_gpu0(self):
        import editorial_select as es
        calls = {"acquire": 0, "release": 0, "words": []}
        orig = ts.acquire

        def no_acquire(*a, **k):
            calls["acquire"] += 1
            raise AssertionError("backtest must not acquire")

        def release(llm, **kw):
            calls["release"] += 1
            raise AssertionError("backtest must not release GPU0")

        def words_fn(vid):
            calls["words"].append(vid)
            return None, "backtest: no word record (a live run would transcribe it)"
        import story_semantics as sm
        from test_editorial_robust import NOW, FakeEmbedder
        saved_release = sm.release_gpu0_for_whisper
        ts.acquire, sm.release_gpu0_for_whisper = no_acquire, release
        try:
            with self.assertRaises(es.NoProducibleStory):
                es.select_story(self.run_dir, log=lambda s: None, embedder=FakeEmbedder(), llm=FakeLLM(),
                                universe_fn=lambda h: self.uni, stories_path=self.stories, topup=False, now=NOW,
                                transcript_fn=ts.canonical_transcript, words_fn=words_fn)
        finally:
            ts.acquire, sm.release_gpu0_for_whisper = orig, saved_release
        self.assertEqual((calls["acquire"], calls["release"]), (0, 0))
        self.assertTrue(calls["words"])                          # the coverage-qualified story asked for words
        t = self.topic()
        dem = [c for c in t["candidates"] if c["headline"].startswith("Democrats")][0]
        self.assertIn("no word record", json.dumps(dem.get("clip_quality") or dem.get("decision")))


if __name__ == "__main__":
    unittest.main()
