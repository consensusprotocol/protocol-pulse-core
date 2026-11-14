#!/usr/bin/env python3
"""E-FAIL-036 (2026-11-11): YouTube caption records keep HTML entities ('S&amp;P', '&gt;&gt;' speaker marks; 391 of
586 caption records in the store), so a model that quotes the words it read ('S&P 500') never matched the
excerpt verbatim and a channel's evidence went uncounted. Chunk text is read as the words the entities stand for
(transcript_store.chunks; the immutable record is never rewritten), the quote normaliser decodes too, and the
embedding cache is versioned so vectors match the decoded text.
must-fail  the real Altcoin Daily excerpt (fresh run 2026-11-12 00:14 UTC, yt_auto R-iKNbc7-zk:447120-478710) under the
           old normalisation: the model's quote '... 95% exposure to the S&P 500 and 5% to Bitcoin.' is not found
must-pass  the same quote against the same excerpt now; a synthetic caption record's chunks read 'S&P 500', '>> so'
E-FAIL-037 word-level records joined split Whisper tokens with a space ('$81 ,000'): Natalie Brunell's verbatim quote
           '... above $81,000 after the election to below $75,000 ...' failed; read whole it counts
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_caption_entities.py"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import story_semantics as sm  # noqa: E402
import transcript_store as ts  # noqa: E402

FIX = os.path.join(REPO, "tests", "fixtures", "entities_20261111", "altcoin_sp500_quote.json")


def _old_norm(s):                       # the normaliser before E-FAIL-036 (no entity decoding)
    return re.sub(r"[^a-z0-9 ]+", "", re.sub(r"\s+", " ", (s or "").lower())).strip()


class TestRealQuote(unittest.TestCase):
    def test_the_altcoin_sp500_quote_counts_once_entities_are_read(self):
        fx = json.load(open(FIX))
        raw = fx["excerpt"]["text"]
        self.assertIn("S&amp;P", raw)
        q = _old_norm(fx["evidence_quote"])
        self.assertNotIn(q, _old_norm(raw))                                   # must-fail: the old reading
        self.assertTrue(sm.quote_in(fx["evidence_quote"], [raw]))             # must-pass: decoded
        self.assertTrue(sm.quote_in(fx["evidence_quote"], [ts.html.unescape(raw)]))


class TestSplitWhisperTokens(unittest.TestCase):
    """E-FAIL-037: word-level records join Whisper tokens with spaces, so '$81,000' was stored as '$81 ,000'
    (also 'U .S.', '$1 .3 billion') and a verbatim quote of the number never matched."""
    def test_the_natalie_81000_quote_counts_once_split_tokens_are_read_whole(self):
        fx = json.load(open(os.path.join(os.path.dirname(FIX), "natalie_81000_quote.json")))
        raw = fx["excerpt"]["text"]
        self.assertIn("$81 ,000", raw)
        self.assertNotIn(_old_norm(fx["evidence_quote"]), _old_norm(raw))   # must-fail: the old reading
        self.assertTrue(sm.quote_in(fx["evidence_quote"], [ts.read_text(raw)]))   # must-pass: read whole
        self.assertTrue(sm.quote_in(fx["evidence_quote"], [raw]))           # and the quote check itself joins

    def test_only_a_token_split_is_joined(self):
        self.assertEqual(ts.read_text("$81 ,000 and U .S. and $1 .3 billion"), "$81,000 and U.S. and $1.3 billion")
        self.assertEqual(ts.read_text("the end. Next one, and more"), "the end. Next one, and more")


class TestChunksDecode(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="entities_")
        self.saved = (ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR)
        ts.STORE_DIR = self.tmp
        ts.TRANSCRIPTS_DIR = os.path.join(self.tmp, "transcripts")
        ts.STATE_DIR = os.path.join(self.tmp, "state")
        ts.MEDIA_DIR = os.path.join(self.tmp, "media")

    def tearDown(self):
        ts.STORE_DIR, ts.TRANSCRIPTS_DIR, ts.STATE_DIR, ts.MEDIA_DIR = self.saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_caption_chunks_read_entities_as_words_and_the_record_is_unchanged(self):
        vid = "ENTITYAAAA1"
        meta = {"schema": 1, "video_id": vid, "canonical_url": ts.canonical_url(vid),
                "channel_id": "UCfakefakefakefakefake02", "channel_name": "Fake Captions", "exact_title": "show",
                "published_at": "2026-11-11T00:00:00+00:00", "duration": 600}
        segs = [{"start": 0.0, "end": 20.0, "text": "&gt;&gt; so the strategy starts with 95% exposure"},
                {"start": 20.0, "end": 40.0, "text": "to the S&amp;P 500 and 5% to Bitcoin. It&#39;s simple."}]
        rec = ts._make_record(meta, "yt_auto:en-orig", "fake captions", segs)
        os.makedirs(ts._vdir(vid))
        ts._store(rec)
        stored = ts.canonical_transcript(vid)                                 # hash-checked on read: unchanged
        self.assertIn("S&amp;P", stored["segments"][1]["text"])
        text = " ".join(c["text"] for c in ts.chunks(stored))
        self.assertIn(">> so the strategy", text)
        self.assertIn("the S&P 500 and 5% to Bitcoin. It's simple.", text)
        self.assertNotIn("&amp;", text)


class TestClusterClaimIsTheEvent(unittest.TestCase):
    """E-FAIL-038 (2026-11-12 fresh run): query derivation re-read two channel claims as other events (the election
    sell-off / ETF-outflow claim became 'the US held its elections on November 8th', an invented date; the $74K claim
    became a Schwab listing from the label summary). A cluster's query is derived from the claim alone and its
    underlying_event IS the claim; a wire item is derived exactly as before. On the real model (4 calls, recorded
    in the DoD 20:13): Natalie Brunell and Coin Bureau then both count for the election sell-off claim."""
    class Fake:
        model = "fake"

        def __init__(self):
            self.prompts = []

        def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
            self.prompts.append(prompt)
            obj = {"underlying_event": "The US held its general elections on November 8th, 2026.",
                   "bitcoin_relevance": 5, "importance": 4, "action": "sell-off", "affected_object": "Bitcoin",
                   "event_date": "2026-11-08", "event_recency": "current", "entities": [], "concepts": [],
                   "must_not_confuse_with": []}
            if validate:
                validate(obj)
            return obj

    def test_a_cluster_claim_is_its_event_and_a_wire_item_is_unchanged(self):
        claim = "Following the US elections, Bitcoin experienced a sell-off and net outflows from US Bitcoin ETFs."
        L = self.Fake()
        q = sm.derive_story_query(L, {"origin": "transcript_cluster", "headline": claim,
                                      "summary": "Schwab added Solana and Avalanche.", "source_domain": "transcript cluster"},
                                  "2026-11-11")
        self.assertEqual(q["underlying_event"], claim)
        self.assertEqual(q["underlying_event_derived"], "The US held its general elections on November 8th, 2026.")
        self.assertNotIn("Schwab", L.prompts[0])                       # the summary never reaches the model
        self.assertIn(sm.CLUSTER_NOTE, L.prompts[0])
        q = sm.derive_story_query(L, {"origin": "story_engine", "headline": "Wire headline",
                                      "summary": "Schwab added Solana and Avalanche.", "source_domain": "x.com"},
                                  "2026-11-11")
        self.assertEqual(q["underlying_event"], "The US held its general elections on November 8th, 2026.")
        self.assertNotIn("underlying_event_derived", q)
        self.assertIn("Schwab", L.prompts[1])
        self.assertEqual(L.prompts[1], sm.DERIVE_PROMPT.format(today="2026-11-11", headline="Wire headline",
                                                               summary="Schwab added Solana and Avalanche.",
                                                               source="x.com"))      # wire prompts byte-identical


class TestEmbeddingCacheVersion(unittest.TestCase):
    def test_vectors_are_cached_under_the_decoded_text_version(self):
        tmp = tempfile.mkdtemp(prefix="embv_")
        saved = sm.EMB_DIR
        sm.EMB_DIR = tmp
        try:
            E = sm.Embedder.__new__(sm.Embedder)
            E.encode = lambda texts, query=False, batch=64: np.ones((len(texts), 4), np.float32)
            rec = {"video_id": "ENTITYAAAA1", "transcript_sha256": "ab" * 32}
            E.chunk_vectors(rec, [{"chunk_id": "ENTITYAAAA1:0-30000", "text": "x"}])
            names = os.listdir(os.path.join(tmp, "ENTITYAAAA1"))
            self.assertEqual(len(names), 1)
            self.assertTrue(names[0].endswith(".t2.npz"), names)
        finally:
            sm.EMB_DIR = saved
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
