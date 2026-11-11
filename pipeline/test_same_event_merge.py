#!/usr/bin/env python3
"""Mission 4b: SAME-EVENT MERGE in AUTO mode. Nov 10 (runs/fresh_20261110_093150/TOPIC_SELECTION.json): the
story engine split one event into 'Bitcoin ETFs shed $1.3B' (#13) and 'Bitcoin Falls Amid Tech Selloff' (#20).
Both counted the SAME Yahoo Finance statement; #20 reached one channel ("coverage 1 < 2") and #13 failed on
hook quality. The hand fix re-judged the not-counted quotes against ONE merged event and DataDash counted.
Here: candidates whose counted evidence includes the same statement (same video, shared chunk, shared run of
words) are grouped deterministically (no model asked 'same event?'), their verdicts pooled, the not-counted
ones re-judged against one merged query, and the coverage decision recomputed.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_same_event_merge.py"""
import os
import sys
import unittest

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import editorial_select as es  # noqa: E402
import story_semantics as sm  # noqa: E402
from test_window_review import RoutedLLM  # noqa: E402


def verdict(vid, channel_id, chunk, counted, quote="", verdict_="CURRENT_EVENT"):
    return {"video_id": vid, "channel": channel_id, "channel_id": channel_id, "layout_eligible": True,
            "counted_as_same_event": counted, "verdict": verdict_, "evidence_quote": quote,
            "supporting_chunk_ids": [chunk] if counted else [], "title": f"{vid} show",
            "published_at": "2026-11-09T12:00:00+00:00", "canonical_url": f"https://youtu.be/{vid}",
            "transcript_sha256": "x", "transcript_method": "whisper_words", "retrieval_score": 0.7,
            "excerpts": [{"chunk_id": chunk, "start": 0.0, "end": 30.0, "text": quote or "unrelated words here"}]}


def cand(headline, verdicts, importance):
    return {"origin": "story_engine", "engine_rank": 1, "engine_score": 50, "headline": headline,
            "summary": headline, "source_domain": "x.com", "age_h": 5.0, "source_published": "2026-11-09T10:00:00+00:00",
            "query": {"underlying_event": headline, "short_label": headline[:20], "event_recency": "current"},
            "importance": {"importance_score": importance}, "importance_gate": [], "event_date_grounding": {},
            "coverage": {"verdicts": verdicts}}


Q_YAHOO = "Bitcoin dropped pretty massively over the weekend alongside the tech selloff"
Q_NAT = "It went from above 81,000 after the election to below 75,000 by the weekend"
Q_DD = "But we've seen a really nice decline here on Bitcoin, 16 percent so far"


class MergeLLM(RoutedLLM):
    """RoutedLLM + the story-query derivation prompt."""

    def chat_json(self, prompt, max_tokens=700, validate=None, attempts=3):
        if prompt.startswith(sm.DERIVE_PROMPT.split("{")[0][:40]):
            self.prompts.append(prompt)
            return {"underlying_event": "Bitcoin fell below $75k over the weekend amid a tech selloff and ETF outflows",
                    "short_label": "Bitcoin price dip", "bitcoin_relevance": 5, "importance": 4, "event_recency": "current"}
        return super().chat_json(prompt, max_tokens, validate, attempts)


class TestSameEventGroups(unittest.TestCase):
    def test_candidates_sharing_a_counted_passage_are_one_event(self):
        etf = cand("ETFs shed $1.3B", [verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO)], 0.85)
        drop = cand("Bitcoin drops below $74K", [verdict("NAT", "natalie", "NAT:3-4", True, Q_NAT)], 0.91)
        tech = cand("Bitcoin falls amid tech selloff", [verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO),
                                                         verdict("NAT", "natalie", "NAT:3-4", True, Q_NAT)], 0.91)
        other = cand("Coinbase gets a bank charter", [verdict("COI", "coin", "COI:9-9", True, "charter")], 0.7)
        self.assertEqual(es._same_event_groups([etf, drop, tech, other]), [[0, 1, 2]])

    def test_shared_video_but_different_passage_is_not_enough(self):
        a = cand("A", [verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO)], 0.8)
        b = cand("B", [verdict("YAH", "yahoo", "YAH:5-6", True, "something else entirely")], 0.8)
        self.assertEqual(es._same_event_groups([a, b]), [])

    def test_not_counted_evidence_never_links(self):
        a = cand("A", [verdict("YAH", "yahoo", "YAH:1-2", False, Q_YAHOO, "TOPIC_ONLY")], 0.8)
        b = cand("B", [verdict("YAH", "yahoo", "YAH:1-2", False, Q_YAHOO, "TOPIC_ONLY")], 0.8)
        self.assertEqual(es._same_event_groups([a, b]), [])


    def test_same_chunk_but_different_statements_is_not_enough(self):
        """A roundup show can state two events inside one chunk; only a shared STATEMENT links them."""
        a = cand("A", [verdict("YAH", "yahoo", "YAH:1-2", True, "Strategy purchased 1,036 Bitcoin this week")], 0.8)
        b = cand("B", [verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO)], 0.8)
        self.assertEqual(es._same_event_groups([a, b]), [])

    def test_nov10_real_counted_evidence_groups_exactly_the_split_story(self):
        """The real counted verdicts of every Nov 10 candidate that had any (#11, #13, #19, #20)."""
        real = {
            11: [("xZz4ikZmHEU", ["xZz4ikZmHEU:637900-694990", "xZz4ikZmHEU:744560-795090"],
                  "The investors reassessed the durability of the entire AI theme."),
                 ("vqFt75tN3AI", ["vqFt75tN3AI:388510-418940"], "the number is what, like $13 trillion have been "
                  "wiped out of the AI kind of build out stocks right now"),
                 ("lusJ1m-J0Mc", ["lusJ1m-J0Mc:33490-67150", "lusJ1m-J0Mc:146350-200300"], "investors are getting "
                  "nervous about how much these companies are spending on AI compared with what they're actually earning."),
                 ("W2LIxB2kAH0", ["W2LIxB2kAH0:2494720-2525589"], "if those higher interest rates continue to bite "
                  "into the AI into AI's capability to continue financing")],
            13: [("36HPi9UZPOc", ["36HPi9UZPOc:32719-64149", "36HPi9UZPOc:64159-94310"], Q_YAHOO),
                 ("lusJ1m-J0Mc", ["lusJ1m-J0Mc:67150-105440"],
                  "U.S. Bitcoin ETFs had about $1.3 billion in net outflows just last week.")],
            19: [("_cGepHL1Rf0", ["_cGepHL1Rf0:60210-95730"], "Strategy purchased 1,036 Bitcoin, taking them over 850,000 Bitcoin.")],
            20: [("36HPi9UZPOc", ["36HPi9UZPOc:32719-64149", "36HPi9UZPOc:64159-94310"], Q_YAHOO)]}
        order = []
        for i in range(23):
            vs = []
            for vid, chunks, q in real.get(i, []):
                v = verdict(vid, vid, chunks[0], True, q)
                v["supporting_chunk_ids"] = chunks
                vs.append(v)
            order.append(cand(f"c{i}", vs, 0.5))
        self.assertEqual(es._same_event_groups(order), [[13, 20]])


class TestMergeEvent(unittest.TestCase):
    """Nov 10 in miniature: each story alone counts ONE channel; merged and re-judged, DataDash counts too."""

    def setUp(self):
        self.by_cid = {c: {"display_name": c.title(), "channel_id": c} for c in ("yahoo", "natalie", "datadash")}
        self.uni = [{"video_id": v, "title": f"{v} show", "channel": c, "published_at": "2026-11-09T12:00:00+00:00"}
                    for v, c in (("YAH", "yahoo"), ("NAT", "natalie"), ("DD", "datadash"))]
        self.etf = cand("ETFs shed $1.3B", [verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO)], 0.85)
        self.drop = cand("Bitcoin drops below $74K", [verdict("NAT", "natalie", "NAT:3-4", True, Q_NAT),
                                                       verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO),
                                                       verdict("DD", "datadash", "DD:5-6", False, Q_DD, "CURRENT_EVENT")], 0.91)

    def test_merged_candidate_counts_the_rejudged_channel_and_qualifies(self):
        llm = MergeLLM(on_event=[Q_YAHOO, Q_NAT, Q_DD], second_quote=Q_DD)
        merged = es._merge_event([self.etf, self.drop], llm, self.uni, self.by_cid, "2026-11-10", lambda s: None)
        self.assertEqual(merged["origin"], "same_event_merge")
        self.assertEqual(merged["headline"], "Bitcoin drops below $74K")               # the most important member
        self.assertEqual(merged["query"]["short_label"], "Bitcoin price dip")         # one derived query
        self.assertEqual(merged["coverage"]["rejudged_for_merge"], 1)                 # only the not-counted verdict
        self.assertEqual(sorted(merged["coverage"]["channels"]), ["Datadash", "Natalie", "Yahoo"])
        self.assertEqual(merged["decision"], "coverage_qualified")
        for m in (self.etf, self.drop):
            self.assertTrue(m["decision"].startswith("merged into the same-event candidate"), m["decision"])

    def test_one_verdict_per_video_and_counted_ones_are_kept_without_a_new_call(self):
        llm = MergeLLM(on_event=[], second_quote=None)                                # the re-judge says UNRELATED
        merged = es._merge_event([self.etf, self.drop], llm, self.uni, self.by_cid, "2026-11-10", lambda s: None)
        vids = [v["video_id"] for v in merged["coverage"]["verdicts"]]
        self.assertEqual(sorted(vids), ["DD", "NAT", "YAH"])                           # pooled, deduplicated
        self.assertEqual(sorted(merged["coverage"]["channels"]), ["Natalie", "Yahoo"])  # DataDash did not count
        self.assertEqual(sum(p.startswith("You verify whether") for p in llm.prompts), 1)


if __name__ == "__main__":
    unittest.main()
