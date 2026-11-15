#!/usr/bin/env python3
"""Ruling 106 (d) (orchestrator 2026-11-14 '20:21'), THE ALARM: one plain text line to PBX's Telegram review chat,
'PULSE CHECK NEEDS A DECISION: <one sentence>. Waiting since <time>.', at most one per issue and at most one an hour
in total, enforced in code. Must-fail: a second alarm inside the hour is refused (nothing sent). Every test uses a
fake sender and a temporary log: nothing here reaches the network."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import telegram as T  # noqa: E402


class TestAlarm(unittest.TestCase):
    def setUp(self):
        self.log = os.path.join(tempfile.mkdtemp(prefix="alarm_test_"), "alarms.jsonl")
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return 1000 + len(self.sent)

    def alarm(self, issue, now, sentence="A finished spotlight is waiting for a launch decision", send=None):
        return T.send_alarm(issue, sentence, "20:09 ET", send=send or self.send, now=now, log_path=self.log)

    def test_the_line_is_exact(self):
        self.assertEqual(self.alarm("spotlight-3f481f5a", 10_000.0, sentence="One video is ready."), 1001)
        self.assertEqual(self.sent, ["PULSE CHECK NEEDS A DECISION: One video is ready. Waiting since 20:09 ET."])

    def test_a_second_alarm_inside_the_hour_is_refused(self):
        self.alarm("issue-a", 10_000.0)
        with self.assertRaises(T.AlarmRefused):
            self.alarm("issue-b", 10_000.0 + T.ALARM_GAP_S - 1)          # a different issue, 59:59 later
        self.assertEqual(len(self.sent), 1)                               # nothing sent
        self.alarm("issue-b", 10_000.0 + T.ALARM_GAP_S)                   # an hour later it may go
        self.assertEqual(len(self.sent), 2)

    def test_one_alarm_per_issue_ever(self):
        self.alarm("issue-a", 10_000.0)
        with self.assertRaises(T.AlarmRefused):
            self.alarm("issue-a", 10_000.0 + 5 * T.ALARM_GAP_S)
        self.assertEqual(len(self.sent), 1)

    def test_an_unknown_outcome_counts_and_a_refusal_does_not(self):
        def rejected(text):
            raise T.SendRejected("STOP: Telegram sendMessage refused: 400 Bad Request")

        def unknown(text):
            raise RuntimeError("STOP: Telegram sendMessage: outcome unknown (Timeout)")
        with self.assertRaises(T.SendRejected):
            self.alarm("issue-a", 10_000.0, send=rejected)               # not sent: not recorded
        self.alarm("issue-a", 10_001.0)                                   # so it may be retried at once
        with self.assertRaises(RuntimeError):
            self.alarm("issue-b", 10_001.0 + T.ALARM_GAP_S, send=unknown)  # an hour after the send: unknown, it counts
        with self.assertRaises(T.AlarmRefused):
            self.alarm("issue-c", 10_001.0 + T.ALARM_GAP_S + 60)
        outcomes = [json.loads(line)["outcome"] for line in open(self.log)]
        self.assertEqual(outcomes, ["sent", "unknown"])

    def test_a_malformed_line_is_refused_and_nothing_sent(self):
        for issue, sentence in (("", "x"), ("issue", ""), ("issue", "two\nlines"), ("a\nb", "x")):
            with self.subTest(issue=issue, sentence=sentence):
                with self.assertRaises(T.AlarmRefused):
                    self.alarm(issue, 10_000.0, sentence=sentence)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
