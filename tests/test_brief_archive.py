#!/usr/bin/env python3
"""
Test: morning_brief._archive_brief_to_db() writes to daily_brief table.
Uses /tmp/nl_test DB copy. No network calls.
"""
import json
import os
import shutil
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TEST_DIR = "/tmp/nl_test"
PROD_DB = "/home/ultron/protocol_pulse/instance/protocol_pulse.db"
TEST_DB = os.path.join(TEST_DIR, "protocol_pulse.db")


def setup():
    os.makedirs(TEST_DIR, exist_ok=True)
    shutil.copy2(PROD_DB, TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    count = conn.execute("SELECT count(*) FROM daily_brief").fetchone()[0]
    print(f"[setup] daily_brief rows before test: {count}")
    conn.close()


def test_archive():
    print("\n=== TEST 1: Archive a brief ===")

    from services.morning_brief import _archive_brief_to_db

    brief = {
        "generated_at": "2026-11-09T23:00:00+00:00",
        "date": "Monday, November 09, 2026",
        "btc_price": "$87,500",
        "sentiment": "bullish",
        "sentiment_reasoning": "Hashrate ATH, institutional accumulation",
        "dominant_narratives": ["Institutional accumulation deepens", "ETF inflows accelerate", "Mining difficulty ATH"],
        "trending_language": ["conviction", "stack sats", "sovereign"],
        "key_stats_today": {"tweets_analyzed": 45, "nostr_signals": 12},
        "generated_by": "test",
    }

    _archive_brief_to_db(brief, db_path=TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    row = conn.execute(
        "SELECT id, headline, body, signals_json, status, created_at "
        "FROM daily_brief ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    print(f"[DB row] id={row[0]}")
    print(f"[DB row] headline={row[1]}")
    print(f"[DB row] body length={len(row[2])}")
    print(f"[DB row] signals_json={row[3]}")
    print(f"[DB row] status={row[4]}")
    print(f"[DB row] created_at={row[5]}")

    assert row[1] == "Institutional accumulation deepens", f"Headline mismatch: {row[1]}"
    assert row[4] == "generated", f"Status mismatch: {row[4]}"

    body = json.loads(row[2])
    assert body["sentiment"] == "bullish"

    signals = json.loads(row[3])
    assert signals["generated_by"] == "test"

    print("[PASS] test_archive")
    return True


def test_dedupe():
    print("\n=== TEST 2: Deduplicate same-day brief ===")

    from services.morning_brief import _archive_brief_to_db

    conn = sqlite3.connect(TEST_DB)
    count_before = conn.execute("SELECT count(*) FROM daily_brief").fetchone()[0]
    conn.close()

    # Same brief as test 1
    brief = {
        "generated_at": "2026-11-09T23:00:00+00:00",
        "date": "Monday, November 09, 2026",
        "btc_price": "$87,500",
        "sentiment": "bullish",
        "sentiment_reasoning": "Hashrate ATH, institutional accumulation",
        "dominant_narratives": ["Institutional accumulation deepens", "ETF inflows accelerate", "Mining difficulty ATH"],
        "trending_language": ["conviction", "stack sats", "sovereign"],
        "key_stats_today": {"tweets_analyzed": 45, "nostr_signals": 12},
        "generated_by": "test",
    }

    _archive_brief_to_db(brief, db_path=TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    count_after = conn.execute("SELECT count(*) FROM daily_brief").fetchone()[0]
    conn.close()

    assert count_after == count_before, f"Dedupe failed: {count_before} -> {count_after}"
    print("[PASS] test_dedupe")
    return True


if __name__ == "__main__":
    setup()
    ok1 = test_archive()
    ok2 = test_dedupe()
    print(f"\n{'='*40}")
    if ok1 and ok2:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
