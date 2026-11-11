#!/usr/bin/env python3
"""DEC-13 (orchestrator 2026-11-11 18:00): candidates come from the channels' own conversation FIRST.
must-produce  today's saved universe (tests/fixtures/dec13_20261111: the fresh run of 21:39 UTC, 4,284 chunks,
              rebuilt from the store by transcript sha): the $74K pullback statements (Coin Bureau "Bitcoin's
              recent drop stalled ...", Altcoin Daily, Bitcoin Magazine; with Marty Bent) form ONE cluster of 4
              channels that passes the free Bitcoin screen in the 48 h tier and reaches the model; the ETF-outflow
              statements (Coin Bureau, Bitcoin Magazine) form one 2-channel cluster in the 72 h tier. The old rule
              (>= 3 channels, the 8 widest clusters) put neither in any cluster.
must-not      two channels on different events never form one cluster: Bloomberg's Fed-hike statement and Natalie
              Brunell's ETF-outflow statement (real); disjoint statements (synthetic)
order         clusters are evaluated first; wire headlines only after every cluster tier is exhausted; a producible
              cluster leaves the wire headlines unevaluated (no model call)
screen        an off-brand cluster (no Bitcoin statement) costs no model call
cache         a validated reply is reused for the identical request; another request asks again
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_dec13_clusters.py"""
import json
import os
import re
import sys
import unittest

import numpy as np

PIPELINE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(PIPELINE)
sys.path.insert(0, PIPELINE)
import editorial_select as es  # noqa: E402
import story_semantics as sm  # noqa: E402
import transcript_store as ts  # noqa: E402
from test_editorial_robust import FakeLLM, Orchestration, TXT  # noqa: E402

FIX = os.path.join(REPO, "tests", "fixtures", "dec13_20261111", "universe.json")
S74 = {"UJFQBaMh3yg:3190-33590", "R-iKNbc7-zk:572160-603509", "jbDqdLytkNM:233170-264260"}
SETF = {"UJFQBaMh3yg:222640-253830", "jbDqdLytkNM:199870-232940"}
FED, NATALIE_ETF = "HRIjtvWogyE:6021215-6054081", "lusJ1m-J0Mc:66350-96350"


def _today():
    """The fresh run's exact chunks + vectors, or None when the store is not on this machine."""
    fx = json.load(open(FIX))
    chunks, vecs = [], []
    for u in fx["universe"]:
        if not u["transcript_sha256"]:
            continue
        try:
            rec = next((r for r in ts.transcript_records(u["video_id"])
                        if r["transcript_sha256"] == u["transcript_sha256"]), None)
        except (OSError, ValueError):
            return None
        p = rec and os.path.join(sm.EMB_DIR, u["video_id"],
                                 f"{u['transcript_sha256'][:16]}.{sm.EMBED_REVISION[:12]}.npz")
        if rec is None or not os.path.exists(p):
            return None
        cs = ts.chunks(rec)
        z = np.load(p, allow_pickle=False)
        if list(z["ids"]) != [c["chunk_id"] for c in cs]:
            return None
        for c in cs:
            c["age_h"], c["layout_eligible"] = u["age_h"], u["layout_eligible"]
        chunks += cs
        vecs.append(z["vecs"])
    return (chunks, np.vstack(vecs)) if len(chunks) == fx["n_chunks"] else None


class TestTodaysUniverse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        got = _today()
        if got is None:
            raise unittest.SkipTest("today's editorial store (transcripts + embeddings) is not on this machine")
        cls.chunks, cls.vecs = got
        cls.groups = sm.emergent_clusters(cls.chunks, cls.vecs, min_channels=es.MIN_COVERAGE_CHANNELS,
                                          max_clusters=None)

    def _ids(self, g):
        return {self.chunks[i]["chunk_id"] for i in g["chunk_idx"]}

    def _holding(self, ids):
        return [g for g in self.groups if ids <= self._ids(g)]

    def test_the_74k_pullback_statements_form_one_cluster_that_reaches_the_model(self):
        (g,) = self._holding(S74)
        e = es.cluster_entry(self.chunks, self.vecs, g)
        self.assertEqual(e["channels"], ["Altcoin Daily", "Bitcoin Magazine", "Coin Bureau",
                                         "Marty Bent (Rabbit Hole Recap)"])
        self.assertEqual(e["screen"], "48h")
        self.assertEqual(e["bitcoin_channels"]["48h"], ["Altcoin Daily", "Coin Bureau"])
        self.assertEqual(len(e["statements"]), 4)                      # one statement per channel, in the ledger

    def test_the_etf_outflow_statements_form_a_72h_cluster(self):
        (g,) = self._holding(SETF)
        e = es.cluster_entry(self.chunks, self.vecs, g)
        self.assertEqual(e["channels"], ["Bitcoin Magazine", "Coin Bureau"])
        self.assertEqual(e["screen"], "72h")                           # Bitcoin Magazine's statement is 50 h old

    def test_the_old_rule_let_neither_reach_the_model(self):
        old = sm.emergent_clusters(self.chunks, self.vecs)              # >= 3 channels, the 8 widest
        self.assertFalse([g for g in old if (S74 | SETF) & self._ids(g)])

    def test_two_channels_on_different_events_never_form_one_cluster(self):
        self.assertFalse([g for g in self.groups if {FED, NATALIE_ETF} <= self._ids(g)])


def _chunk(cid, ch, text, age_h=6.0):
    return {"chunk_id": cid, "video_id": cid.split(":")[0], "channel_id": f"UC{ch}", "channel_name": ch,
            "text": text, "age_h": age_h, "layout_eligible": True}


class TestScreenSynthetic(unittest.TestCase):
    def test_disjoint_statements_never_cluster(self):
        chunks = [_chunk(f"VIDAAAAAAA{i}:0-30000", "A", "MARA sold bitcoin") for i in range(3)] + \
                 [_chunk(f"VIDBBBBBBB{i}:0-30000", "B", "ECB rate judgment") for i in range(3)]
        vecs = np.array([[1.0, 0.0]] * 3 + [[0.0, 1.0]] * 3, np.float32)
        self.assertEqual(sm.emergent_clusters(chunks, vecs, min_channels=2, max_clusters=None), [])

    def test_the_screen_counts_bitcoin_statements_by_tier(self):
        chunks = [_chunk("VIDAAAAAAA1:0-30000", "A", "Bitcoin fell to 74 thousand", 10.0),
                  _chunk("VIDBBBBBBB1:0-30000", "B", "BTC slid again today", 60.0),
                  _chunk("VIDCCCCCCC1:0-30000", "C", "markets fell today", 5.0)]
        vecs = np.ones((3, 2), np.float32)
        g = {"chunk_idx": [0, 1, 2], "channels": ["UCA", "UCB", "UCC"]}
        e = es.cluster_entry(chunks, vecs, g)
        self.assertEqual((e["screen"], e["bitcoin_channels"]["48h"], e["bitcoin_channels"]["72h"]), ("72h", ["A"], ["A", "B"]))
        chunks[2]["text"] = "13,597 bitcoins sold"                     # plural counts (Heimdall batch13 F2)
        self.assertEqual(es.cluster_entry(chunks, vecs, g)["bitcoin_channels"]["48h"], ["A", "C"])
        chunks[2]["text"] = "markets fell today"
        chunks[1]["age_h"] = 80.0                                      # beyond the 72 h universe: stopped
        self.assertTrue(es.cluster_entry(chunks, vecs, g)["screen"].startswith("Bitcoin screen:"))


class ClusterLLM(FakeLLM):
    """Labels any cluster as the verified current development (its quote is verbatim in the first excerpt)."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.prompts = []

    def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
        self.prompts.append(prompt[:200])
        if prompt.startswith("These transcript excerpts"):
            cid = re.search(r'<excerpt id="([^"]+)"', prompt).group(1)
            return {"is_specific_event": True, "headline": "Democrats took the House and the Senate in the midterms.",
                    "summary": "Congress flipped.", "event_date": "2026-11-04",
                    "current_development_quote": " ".join(TXT.split()[:12]), "current_development_chunk_id": cid,
                    "member_chunk_ids": [cid]}
        return super().chat_json(prompt, max_tokens, validate, attempts)


def _refuse(llm, **kw):
    raise RuntimeError("GPU0 release not proven: test")


class TestPoolOrder(Orchestration):
    def test_clusters_are_evaluated_first_then_the_wire_headlines(self):
        with self.assertRaises(es.NoProducibleStory):
            self.select(ClusterLLM(), release_gpu0_for_whisper=_refuse)
        t = self.topic()
        self.assertEqual([(p["pool"], p["evaluated"]) for p in t["pools"]],
                         [("channel_clusters_48h", True), ("channel_clusters_72h", True), ("wire_headlines", True)])
        cl = [c for c in t["candidates"] if c["origin"] == "transcript_cluster"]
        self.assertEqual(len(cl), 1)
        self.assertTrue(cl[0]["decision"].startswith("INFRA_HOLD"), cl[0]["decision"])
        self.assertEqual(t["evaluation_order"][0], cl[0]["headline"])          # before any wire headline
        wire = [c for c in t["candidates"] if c["headline"].startswith("Democrats win")][0]
        self.assertEqual(wire["coverage"]["status"], "done")
        (e,) = [e for e in t["emergent_clusters"] if e.get("candidate")]
        self.assertEqual((e["screen"], e["claim"], e["gate"]), ("48h", cl[0]["headline"], cl[0]["decision"]))
        counted = {v["video_id"] for v in cl[0]["coverage"]["verdicts"] if v["counted_as_same_event"]}
        self.assertTrue(counted <= {c.split(":")[0] for c in cl[0]["cluster_member_chunk_ids"]})   # own statements

    def test_a_producible_cluster_leaves_the_wire_headlines_unasked(self):
        llm = ClusterLLM()
        saved = (es._clip_quality, ts.acquire)

        def acquire(vid, **kw):
            return {"transcript_method": "whisper_words_punct", "words": [{"word": "x.", "start": 0, "end": 1}],
                    "transcript_sha256": "x"}, "cached"
        es._clip_quality = lambda c, *a, **k: {"producible": True, "chosen": [], "candidates": [],
                                                "mean_chosen_score": 5.0}
        ts.acquire = acquire
        try:
            label, rec = self.select(llm, release_gpu0_for_whisper=lambda llm, **kw: {"free_mib": 20000})
        finally:
            es._clip_quality, ts.acquire = saved
        t = self.topic()
        self.assertEqual(t["selected"]["origin"], "transcript_cluster")
        self.assertEqual([(p["pool"], p["evaluated"]) for p in t["pools"]],
                         [("channel_clusters_48h", True), ("channel_clusters_72h", False), ("wire_headlines", False)])
        for c in t["candidates"]:
            if c["origin"] == "story_engine":
                self.assertEqual(c["decision"], "not evaluated: the channel_clusters_48h pool produced a story (DEC-13 a)")
                self.assertNotIn("query", c)
        self.assertFalse([p for p in llm.prompts if "PARSEFAIL" in p or "Democrats win Congress" in p])

    def test_an_off_brand_cluster_costs_no_model_call(self):
        for rec in self.uni:                                        # the same three channels, no Bitcoin statement
            vid = rec["video_id"]
            m = json.load(open(os.path.join(ts._vdir(vid), "meta.json")))
            os.unlink(ts.canonical_transcript(vid)["_path"])
            segs = [{"start": i * 6.0, "end": i * 6.0 + 5.8,
                     "text": "Our sponsor makes the best coffee grinder and the battery lasts all week. "}
                    for i in range(30)]
            ts._store(ts._make_record(m, "yt_auto:en-orig", "fake", segs))
        llm = ClusterLLM()
        with self.assertRaises(es.NoProducibleStory):
            self.select(llm, release_gpu0_for_whisper=_refuse)
        t = self.topic()
        self.assertTrue(t["emergent_clusters"])
        self.assertTrue(all(e["gate"].startswith("Bitcoin screen:") for e in t["emergent_clusters"]))
        self.assertFalse([p for p in llm.prompts if p.startswith("These transcript excerpts")])


class TestLLMCache(unittest.TestCase):
    def test_a_validated_reply_is_reused_for_the_identical_request_only(self):
        import tempfile
        import shutil
        tmp = tempfile.mkdtemp(prefix="llmcache_")
        saved = sm.LLM_CACHE_DIR
        sm.LLM_CACHE_DIR = tmp
        try:
            L = sm.LocalLLM.__new__(sm.LocalLLM)
            L.model, L.calls, L.cache_hits, L.digest = "fake-model", 0, 0, "sha256:aaaa"
            posts = []

            def post(prompt, max_tokens, seed):
                posts.append(prompt)
                return '{"verdict": "CURRENT_EVENT"}'
            L._post = post
            self.assertEqual(L.chat_json("prompt A"), {"verdict": "CURRENT_EVENT"})
            self.assertEqual(L.chat_json("prompt A"), {"verdict": "CURRENT_EVENT"})
            self.assertEqual((len(posts), L.cache_hits), (1, 1))
            L.chat_json("prompt B")
            L.chat_json("prompt A", max_tokens=99)
            self.assertEqual(len(posts), 3)

            L.digest = "sha256:bbbb"                                   # re-pulled weights: old replies unseen
            L.chat_json("prompt A")
            self.assertEqual(len(posts), 4)
            L.digest = None                                            # unknown weights: nothing cached
            L.chat_json("prompt C")
            L.chat_json("prompt C")
            self.assertEqual(len(posts), 6)

            def strict(o):
                raise ValueError("no longer valid")
            L.digest = "sha256:aaaa"
            with self.assertRaises(sm.LLMParseError):                  # a cached reply is re-validated
                L.chat_json("prompt A", validate=strict)
        finally:
            sm.LLM_CACHE_DIR = saved
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
