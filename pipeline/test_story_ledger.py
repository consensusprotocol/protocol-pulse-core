#!/usr/bin/env python3
"""DEC-9: three fresh runs must be three genuinely different stories. A story delivered to the approval chat is
recorded by its counted evidence statements (pipeline/story_ledger.py); the next auto run never selects an event
resting on one of them, whatever the story engine calls it this time.
Run: cd ~/protocol_pulse && python3 -m pytest -q pipeline/test_story_ledger.py"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

PIPELINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE)

import story_ledger  # noqa: E402
from test_editorial_robust import FakeLLM, Orchestration, _no_release  # noqa: E402
from test_same_event_merge import Q_YAHOO, cand, verdict  # noqa: E402


def _entry(run, vid, chunks, quote, headline="h"):
    import story_semantics as sm
    return {"run": run, "headline": headline, "evidence": [{"video_id": vid, "chunk_ids": chunks, "quote": quote,
                                                             "quote_tokens": sm._norm(quote).split()}]}


class TestDeliveredMatch(unittest.TestCase):
    def test_same_statement_reworded_headline_is_the_delivered_story(self):
        led = [_entry("fresh_1", "YAH", ["YAH:1-2"], Q_YAHOO, "Bitcoin ETFs shed $1.3B")]
        c = cand("Bitcoin falls amid tech selloff", [verdict("YAH", "yahoo", "YAH:1-2", True, Q_YAHOO)], 0.9)
        self.assertEqual(story_ledger.delivered_match(c, led)["run"], "fresh_1")

    def test_other_statement_or_not_counted_is_not(self):
        led = [_entry("fresh_1", "YAH", ["YAH:1-2"], Q_YAHOO)]
        other = cand("Strategy buys", [verdict("YAH", "yahoo", "YAH:1-2", True, "Strategy purchased 1,036 Bitcoin")], 0.9)
        topic = cand("T", [verdict("YAH", "yahoo", "YAH:1-2", False, Q_YAHOO, "TOPIC_ONLY")], 0.9)
        self.assertIsNone(story_ledger.delivered_match(other, led))
        self.assertIsNone(story_ledger.delivered_match(topic, led))


class TestRecord(unittest.TestCase):
    def test_record_is_idempotent_per_run_and_needs_evidence(self):
        tmp = tempfile.mkdtemp(prefix="ledger_")
        self.addCleanup(shutil.rmtree, tmp, True)
        run = os.path.join(tmp, "fresh_20261111_120000")
        os.makedirs(run)
        ev = _entry("x", "YAH", ["YAH:1-2"], Q_YAHOO)["evidence"]
        json.dump({"selected": {"headline": "H", "short_label": "s", "underlying_event": "u", "evidence": ev}},
                  open(os.path.join(run, "TOPIC_SELECTION.json"), "w"))
        path = os.path.join(tmp, "ledger.jsonl")
        self.assertEqual(story_ledger.record(run, path)["run"], "fresh_20261111_120000")
        self.assertIsNone(story_ledger.record(run, path))                      # second call: no new line
        self.assertEqual(len(story_ledger.entries(path)), 1)
        json.dump({"selected": {"headline": "H", "evidence": []}}, open(os.path.join(run, "TOPIC_SELECTION.json"), "w"))
        os.rename(run, run + "b")
        with self.assertRaises(ValueError):
            story_ledger.record(run + "b", path)


class TestRecordIfApproved(unittest.TestCase):
    def test_only_an_auto_run_delivered_hold_for_approval_in_both_formats(self):
        import telegram
        tmp = tempfile.mkdtemp(prefix="ledger_")
        self.addCleanup(shutil.rmtree, tmp, True)
        run = os.path.join(tmp, "fresh_20261111_130000")
        os.makedirs(run)
        ev = _entry("x", "YAH", ["YAH:1-2"], Q_YAHOO)["evidence"]
        json.dump({"selected": {"headline": "H", "evidence": ev}}, open(os.path.join(run, "TOPIC_SELECTION.json"), "w"))
        path = os.path.join(tmp, "ledger.jsonl")

        def dlv(c16, c9, option=None):
            return {"option": option, "messages": [{"format": "16x9", "caption": c16}, {"format": "9x16", "caption": c9},
                                                   {"sheet": "contact_sheet_16x9.jpg"}]}
        ok = telegram.HOLD_OK + " | details"
        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, ok), "pinned", path))
        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, telegram.REVIEW + " - 1 failing"), "auto", path))
        self.assertIsNone(story_ledger.record_if_approved(run, dlv(ok, ok, option="A"), "auto", path))
        self.assertEqual(story_ledger.entries(path), [])
        self.assertEqual(story_ledger.record_if_approved(run, dlv(ok, ok), "auto", path)["run"], "fresh_20261111_130000")


class TestLedgerInSelection(Orchestration):
    """The selection harness's 'Democrats win Congress' story qualifies on coverage; once its evidence is in the
    ledger, the same universe yields no producible story and the record says why."""

    def test_delivered_event_is_excluded_with_its_ledger_run(self):
        import editorial_select as es
        path = os.path.join(self.tmp, "ledger.jsonl")
        with mock.patch.object(story_ledger, "LEDGER", path):
            with self.assertRaises(es.NoProducibleStory):                     # first pass: qualifies, infra hold
                self.select(FakeLLM(), release_gpu0_for_whisper=_no_release)
            c = [c for c in self.topic()["candidates"] if c["headline"].startswith("Democrats")][0]
            self.assertTrue(c["decision"].startswith("INFRA_HOLD"), c["decision"])
            import story_semantics as sm
            ev = [{"video_id": v["video_id"], "chunk_ids": v["supporting_chunk_ids"], "quote": v["evidence_quote"],
                   "quote_tokens": sm._norm(v["evidence_quote"]).split()}
                  for v in c["coverage"]["verdicts"] if v["counted_as_same_event"]][:1]
            with open(path, "w") as f:
                f.write(json.dumps({"run": "fresh_prev", "headline": "Democrats took Congress", "evidence": ev}) + "\n")
            with self.assertRaises(es.NoProducibleStory) as cm:
                self.select(FakeLLM(), release_gpu0_for_whisper=_no_release)
            self.assertNotIn("infrastructure", str(cm.exception))             # nothing left to transcribe
            t = self.topic()
            c = [c for c in t["candidates"] if c["headline"].startswith("Democrats")][0]
            self.assertTrue(c["decision"].startswith("already delivered (story ledger: fresh_prev"), c["decision"])
            self.assertEqual(t["story_ledger"]["excluded"][0]["ledger_run"], "fresh_prev")


if __name__ == "__main__":
    unittest.main()
