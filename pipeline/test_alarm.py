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



class TestWatchdogLine(unittest.TestCase):
    """The session watchdog's line (orchestrator order 05:55 ET Nov 16): 'WATCHDOG <session>: <what> (since <time>)',
    at most one per session an hour, none 00:00-07:00 ET except IDLE_WITH_WORK and SPEND, enforced in telegram.py.
    A fake sender and a temporary log: nothing reaches the network."""

    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo as _Z
    DAY = _dt(2026, 11, 16, 10, 0, tzinfo=_Z("America/New_York")).timestamp()
    NIGHT = _dt(2026, 11, 16, 3, 0, tzinfo=_Z("America/New_York")).timestamp()
    SEVEN = _dt(2026, 11, 16, 7, 0, tzinfo=_Z("America/New_York")).timestamp()

    def setUp(self):
        self.log = os.path.join(tempfile.mkdtemp(prefix="watchdog_line_"), "watchdog_lines.jsonl")
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return 2000 + len(self.sent)

    def line(self, key, now, kinds=("LOOP",), text=None, send=None):
        return T.send_watchdog(key, kinds, text or f"{key}: LOOP: the same command 5 times (since 09:50 ET)",
                               send=send or self.send, now=now, log_path=self.log)

    def test_one_plain_line_headed_watchdog(self):
        self.assertEqual(self.line("pipeline_a", self.DAY), 2001)
        self.assertEqual(self.sent, ["WATCHDOG pipeline_a: LOOP: the same command 5 times (since 09:50 ET)"])

    def test_one_line_per_session_an_hour_other_sessions_free(self):
        self.line("pipeline_a", self.DAY)
        with self.assertRaises(T.WatchdogRefused):
            self.line("pipeline_a", self.DAY + T.WATCHDOG_GAP_S - 1)   # 59:59 later: held, nothing sent
        self.line("pipeline_b", self.DAY + 60)                          # another session is not held
        self.line("pipeline_a", self.DAY + T.WATCHDOG_GAP_S)            # an hour later it may go
        self.assertEqual(len(self.sent), 3)

    def test_the_night_carries_only_idle_with_work_and_spend(self):
        for kinds in (("LOOP",), ("STUCK",), ("LONG_TURN",), ("CONTEXT",), ("IDLE_WITH_WORK", "LOOP")):
            with self.assertRaises(T.WatchdogRefused):
                self.line(f"pipeline_{len(kinds)}{kinds[-1]}", self.NIGHT, kinds=kinds)
        self.line("pipeline_pp_wordpass", self.NIGHT, kinds=("IDLE_WITH_WORK",))
        self.line("spend:80%", self.NIGHT, kinds=("SPEND",))
        self.line("pipeline_c", self.SEVEN, kinds=("LOOP",))            # 07:00 ET: day again
        self.assertEqual(len(self.sent), 3)

    def test_malformed_lines_and_unknown_kinds_are_refused(self):
        for key, kinds, text in (("", ("LOOP",), "x"), ("k", ("LOOP",), "a\nb"), ("k\nx", ("LOOP",), "x"),
                                 ("k", (), "x"), ("k", ("WHATEVER",), "x"), ("k", ("LOOP",), "  ")):
            with self.assertRaises(T.WatchdogRefused):
                T.send_watchdog(key, kinds, text, send=self.send, now=self.DAY, log_path=self.log)
        self.assertEqual(self.sent, [])

    def test_an_unknown_outcome_counts_and_a_refusal_does_not(self):
        def rejected(text):
            raise T.SendRejected("STOP: Telegram sendMessage refused: 400 Bad Request")

        def unknown(text):
            raise RuntimeError("STOP: Telegram sendMessage: outcome unknown (Timeout)")
        with self.assertRaises(T.SendRejected):
            self.line("pipeline_a", self.DAY, send=rejected)            # not sent: not recorded
        self.line("pipeline_a", self.DAY + 1)                           # so it may go at once
        with self.assertRaises(RuntimeError):
            self.line("pipeline_b", self.DAY + 2, send=unknown)
        with self.assertRaises(T.WatchdogRefused):
            self.line("pipeline_b", self.DAY + 60)                      # an unknown outcome counts
        self.assertEqual([json.loads(x)["outcome"] for x in open(self.log)], ["sent", "unknown"])

    def test_a_long_line_is_cut_and_marked(self):
        self.line("pipeline_a", self.DAY, text="x" * 2000)
        self.assertEqual(len(self.sent[0]), T.WATCHDOG_MAX)
        self.assertTrue(self.sent[0].startswith("WATCHDOG x") and self.sent[0].endswith("..."))


if __name__ == "__main__":
    unittest.main()
