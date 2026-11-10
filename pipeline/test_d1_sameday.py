#!/usr/bin/env python3
"""D1 same-day date bug must-fail test.

BUG: parse_event_date("2026-11-09") returns midnight UTC, which is earlier than a
source published at 2026-11-09T14:30:00+00:00. The old datetime comparison
discards same-day events as "hallucinated."

FIX: Compare .date() not full datetimes, so same-day model dates are never
discarded as hallucinated.

Run: cd pipeline && python3 -m pytest test_d1_sameday.py -v
"""
import os
import sys
import unittest
from datetime import datetime, timezone

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PIPELINE_DIR)

from story_semantics import grounded_event_date, parse_event_date


class TestParseEventDate(unittest.TestCase):
    def test_full_date_returns_midnight(self):
        d = parse_event_date("2026-11-09")
        self.assertEqual(d.year, 2026)
        self.assertEqual(d.month, 11)
        self.assertEqual(d.day, 9)

    def test_partial_month(self):
        d = parse_event_date("2026-11")
        self.assertEqual(d.month, 11)
        self.assertEqual(d.day, 28)

    def test_garbage(self):
        self.assertIsNone(parse_event_date("last week"))
        self.assertIsNone(parse_event_date(""))
        self.assertIsNone(parse_event_date(None))


class TestD1SameDayNotDiscarded(unittest.TestCase):
    """The core D1 bug: a model date of "2026-11-09" (midnight) must NOT be
    discarded as hallucinated when the source was published on 2026-11-09
    afternoon. Same calendar day = same event, not hallucination."""

    def test_same_day_afternoon_publish(self):
        """Model says '2026-11-09', source published 2026-11-09 14:30 UTC.
        Old bug: midnight < 14:30 -> discarded. Fix: same .date() -> kept."""
        q = {"event_date": "2026-11-09", "event_recency": "current"}
        source_pub = datetime(2026, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        now = datetime(2026, 11, 10, 6, 0, 0, tzinfo=timezone.utc)
        out = grounded_event_date(q, source_pub, now, window_hours=72)
        self.assertFalse(out["model_date_discarded"],
                         "Same-day model date must NOT be discarded as hallucinated")

    def test_same_day_late_night_publish(self):
        """Model says '2026-11-09', source published 2026-11-09 23:59 UTC."""
        q = {"event_date": "2026-11-09"}
        source_pub = datetime(2026, 11, 9, 23, 59, 0, tzinfo=timezone.utc)
        now = datetime(2026, 11, 10, 6, 0, 0, tzinfo=timezone.utc)
        out = grounded_event_date(q, source_pub, now, window_hours=72)
        self.assertFalse(out["model_date_discarded"])

    def test_previous_day_still_discarded(self):
        """Model says '2026-11-08', source published 2026-11-09. Should still
        be discarded — model date is genuinely older."""
        q = {"event_date": "2026-11-08"}
        source_pub = datetime(2026, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        now = datetime(2026, 11, 10, 6, 0, 0, tzinfo=timezone.utc)
        out = grounded_event_date(q, source_pub, now, window_hours=72)
        self.assertTrue(out["model_date_discarded"],
                        "Model date one day before source publish should be discarded")

    def test_future_model_date_not_discarded(self):
        """Model says '2026-11-10', source published 2026-11-09. Future model
        date should not be discarded (it's newer, not older)."""
        q = {"event_date": "2026-11-10"}
        source_pub = datetime(2026, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        now = datetime(2026, 11, 10, 6, 0, 0, tzinfo=timezone.utc)
        out = grounded_event_date(q, source_pub, now, window_hours=72)
        self.assertFalse(out["model_date_discarded"])


if __name__ == "__main__":
    unittest.main()
