#!/usr/bin/env python3
"""
Test: newsletter_engine.send_newsletter() records to newsletter_sends DB.

Monkeypatches _resend_post to avoid real emails.
Uses a copy of production DB at /tmp/nl_test/.
"""
import json
import os
import shutil
import sqlite3
import sys
import types

# Project root
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Ensure logs dir exists
os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)

TEST_DIR = "/tmp/nl_test"
PROD_DB = "/home/ultron/protocol_pulse/instance/protocol_pulse.db"
TEST_DB = os.path.join(TEST_DIR, "protocol_pulse.db")


def setup():
    os.makedirs(TEST_DIR, exist_ok=True)
    shutil.copy2(PROD_DB, TEST_DB)
    print(f"[setup] Copied production DB to {TEST_DB}")
    # Verify newsletter_sends is empty
    conn = sqlite3.connect(TEST_DB)
    count = conn.execute("SELECT count(*) FROM newsletter_sends").fetchone()[0]
    print(f"[setup] newsletter_sends rows before test: {count}")
    conn.close()


class FakeResponse:
    """Mock requests.Response for _resend_post."""
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = json.dumps(data)

    def json(self):
        return self._data


def test_success():
    """Test: 200 response -> message IDs captured -> DB row written."""
    print("\n=== TEST 1: Successful send (fake 200) ===")

    # Set a dummy key so the engine doesn't bail on init
    os.environ["RESEND_API_KEY"] = "re_test_dummy_key_for_monkeypatch"
    # Re-import to pick up the key
    if "services.newsletter_engine" in sys.modules:
        del sys.modules["services.newsletter_engine"]
    import services.newsletter_engine as ne

    # Monkeypatch _resend_post
    call_log = []
    def fake_resend_post(url, key, payload, timeout=30):
        call_log.append({"url": url, "count": len(payload)})
        ids = [{"id": f"test-msg-{i}"} for i in range(len(payload))]
        return FakeResponse(200, {"data": ids})

    original = ne._resend_post
    ne._resend_post = fake_resend_post

    try:
        engine = ne.NewsletterEngine()
        result = engine.send_newsletter(
            to_emails=["alice@test.io", "bob@test.io", "carol@test.io"],
            subject="Test Subject $99,999",
            html="<h1>Test</h1>",
            article_ids=[101, 202, 303],
            db_path=TEST_DB,
        )
        print(f"[result] {json.dumps(result, indent=2)}")
        assert result["success"] is True, f"Expected success, got {result}"
        assert result["sent"] == 3, f"Expected 3 sent, got {result['sent']}"
        assert len(result["message_ids"]) == 3, f"Expected 3 IDs, got {result['message_ids']}"
        assert result["message_ids"][0] == "test-msg-0"

        # Check DB
        conn = sqlite3.connect(TEST_DB)
        row = conn.execute(
            "SELECT subject, resend_batch_id, resend_message_id, recipient_count, "
            "open_count, click_count, sent_at, article_ids FROM newsletter_sends "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()

        print(f"[DB row] subject={row[0]}")
        print(f"[DB row] resend_batch_id={row[1]}")
        print(f"[DB row] resend_message_id={row[2]}")
        print(f"[DB row] recipient_count={row[3]}")
        print(f"[DB row] open_count={row[4]}, click_count={row[5]}")
        print(f"[DB row] sent_at={row[6]}")
        print(f"[DB row] article_ids={row[7]}")

        assert row[0] == "Test Subject $99,999", f"Subject mismatch: {row[0]}"
        assert row[3] == 3, f"Recipient count mismatch: {row[3]}"
        msg_ids = json.loads(row[2])
        assert len(msg_ids) == 3, f"Message IDs count mismatch: {msg_ids}"
        art_ids = json.loads(row[7])
        assert art_ids == [101, 202, 303], f"Article IDs mismatch: {art_ids}"
        assert row[4] == 0 and row[5] == 0, "open/click should be 0"

        print("[PASS] test_success")
        return True
    finally:
        ne._resend_post = original


def test_failure():
    """Test: 422 response -> no DB row written, errors returned."""
    print("\n=== TEST 2: Failed send (fake 422) ===")

    os.environ["RESEND_API_KEY"] = "re_test_dummy_key_for_monkeypatch"
    if "services.newsletter_engine" in sys.modules:
        del sys.modules["services.newsletter_engine"]
    import services.newsletter_engine as ne

    # Count rows before
    conn = sqlite3.connect(TEST_DB)
    count_before = conn.execute("SELECT count(*) FROM newsletter_sends").fetchone()[0]
    conn.close()

    def fake_resend_post_fail(url, key, payload, timeout=30):
        return FakeResponse(422, {"error": "Invalid API key"})

    original = ne._resend_post
    ne._resend_post = fake_resend_post_fail

    try:
        engine = ne.NewsletterEngine()
        result = engine.send_newsletter(
            to_emails=["fail@test.io"],
            subject="Should Fail",
            html="<h1>Fail</h1>",
            article_ids=[999],
            db_path=TEST_DB,
        )
        print(f"[result] {json.dumps(result, indent=2)}")
        assert result["success"] is False, f"Expected failure, got {result}"
        assert result["sent"] == 0
        assert result.get("errors") is not None

        # Check no new row
        conn = sqlite3.connect(TEST_DB)
        count_after = conn.execute("SELECT count(*) FROM newsletter_sends").fetchone()[0]
        conn.close()
        assert count_after == count_before, f"Row count changed: {count_before} -> {count_after}"

        print("[PASS] test_failure")
        return True
    finally:
        ne._resend_post = original


def _get_ne():
    """Fresh import of newsletter_engine with dummy key."""
    os.environ["RESEND_API_KEY"] = "re_test_dummy_key_for_monkeypatch"
    if "services.newsletter_engine" in sys.modules:
        del sys.modules["services.newsletter_engine"]
    import services.newsletter_engine as ne
    return ne


def _fake_resend_ok(url, key, payload, timeout=30):
    ids = [{"id": f"ok-{i}"} for i in range(len(payload))]
    return FakeResponse(200, {"data": ids})


def _last_article_ids_in_db():
    conn = sqlite3.connect(TEST_DB)
    row = conn.execute(
        "SELECT article_ids FROM newsletter_sends ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def test_dispatcher_path():
    """TEST 3a — DISPATCHER PATH: get_todays_articles -> generate_html -> send_newsletter(html=...)
    records the correct article IDs (the ones that went into that HTML).
    This is the exact sequence core/app.py _newsletter_daily_dispatch runs.
    """
    print("\n=== TEST 3a: Dispatcher path records correct article IDs ===")
    ne = _get_ne()
    original = ne._resend_post
    ne._resend_post = _fake_resend_ok
    try:
        engine = ne.NewsletterEngine()

        # Simulate the dispatcher: get_todays_articles returns article dicts with IDs
        fake_articles = [
            {"id": 3544, "title": "A", "summary": "a", "url": "u", "image": "", "category": "Bitcoin"},
            {"id": 3543, "title": "B", "summary": "b", "url": "u", "image": "", "category": "Bitcoin"},
            {"id": 3542, "title": "C", "summary": "c", "url": "u", "image": "", "category": "Bitcoin"},
        ]
        # Call the exact dispatcher sequence:
        html = engine.generate_html(fake_articles, "Test summary sentence one.", {"price": 87000, "change": 1.5})
        result = engine.send_newsletter(
            to_emails=["dispatcher@test.io"],
            subject="Dispatcher",
            html=html,
            db_path=TEST_DB,
        )
        print(f"[result] success={result['success']}, sent={result['sent']}")
        ids = _last_article_ids_in_db()
        print(f"[DB] article_ids={ids}")
        assert ids == [3544, 3543, 3542], f"Expected [3544,3543,3542], got {ids}"
        print("[PASS] test_dispatcher_path")
        return True
    finally:
        ne._resend_post = original


def test_stale_render():
    """TEST 3b — STALE: render A, then send_newsletter(html=different html) records []."""
    print("\n=== TEST 3b: Stale render records [] ===")
    ne = _get_ne()
    original = ne._resend_post
    ne._resend_post = _fake_resend_ok
    try:
        engine = ne.NewsletterEngine()

        # Render HTML A with articles
        fake_articles = [
            {"id": 999, "title": "Old", "summary": "old", "url": "u", "image": "", "category": "Bitcoin"},
        ]
        _html_a = engine.generate_html(fake_articles, "Old summary.", {"price": 80000, "change": -1})

        # Send with DIFFERENT html — IDs should be []
        result = engine.send_newsletter(
            to_emails=["stale@test.io"],
            subject="Stale",
            html="<h1>Completely different HTML</h1>",
            db_path=TEST_DB,
        )
        print(f"[result] success={result['success']}, sent={result['sent']}")
        ids = _last_article_ids_in_db()
        print(f"[DB] article_ids={ids}")
        assert ids == [], f"Expected [], got {ids}"
        print("[PASS] test_stale_render")
        return True
    finally:
        ne._resend_post = original


def test_explicit_ids_win():
    """TEST 3c — Explicit article_ids arg always wins over rendered IDs."""
    print("\n=== TEST 3c: Explicit article_ids wins ===")
    ne = _get_ne()
    original = ne._resend_post
    ne._resend_post = _fake_resend_ok
    try:
        engine = ne.NewsletterEngine()

        # Render with articles [10,20]
        fake_articles = [
            {"id": 10, "title": "X", "summary": "x", "url": "u", "image": "", "category": "Bitcoin"},
            {"id": 20, "title": "Y", "summary": "y", "url": "u", "image": "", "category": "Bitcoin"},
        ]
        html = engine.generate_html(fake_articles, "Summary.", {"price": 90000, "change": 0})

        # Send with that html BUT explicit article_ids override
        result = engine.send_newsletter(
            to_emails=["explicit@test.io"],
            subject="Explicit",
            html=html,
            article_ids=[777, 888],
            db_path=TEST_DB,
        )
        print(f"[result] success={result['success']}, sent={result['sent']}")
        ids = _last_article_ids_in_db()
        print(f"[DB] article_ids={ids}")
        assert ids == [777, 888], f"Expected [777,888], got {ids}"
        print("[PASS] test_explicit_ids_win")
        return True
    finally:
        ne._resend_post = original


def test_no_html_path():
    """TEST 3d — No-html path: send_newsletter with no html calls get_todays_articles
    internally, which calls generate_html, so IDs are captured.
    We mock get_todays_articles to avoid needing the ORM.
    """
    print("\n=== TEST 3d: No-html path records fetched IDs ===")
    ne = _get_ne()
    original_resend = ne._resend_post
    ne._resend_post = _fake_resend_ok
    try:
        engine = ne.NewsletterEngine()

        fake_articles = [
            {"id": 401, "title": "A", "summary": "a", "url": "u", "image": "", "category": "Bitcoin"},
            {"id": 402, "title": "B", "summary": "b", "url": "u", "image": "", "category": "Bitcoin"},
        ]
        # Mock get_todays_articles and generate_ai_summary to avoid DB/LLM
        engine.get_todays_articles = lambda *a, **kw: fake_articles
        engine.generate_ai_summary = lambda *a, **kw: "Mock summary sentence."
        engine.get_btc_price = lambda: {"price": 85000, "change": 0.5}

        result = engine.send_newsletter(
            to_emails=["nohtml@test.io"],
            subject="No-HTML Path",
            db_path=TEST_DB,
        )
        print(f"[result] success={result['success']}, sent={result['sent']}")
        ids = _last_article_ids_in_db()
        print(f"[DB] article_ids={ids}")
        assert ids == [401, 402], f"Expected [401,402], got {ids}"
        print("[PASS] test_no_html_path")
        return True
    finally:
        ne._resend_post = original_resend


if __name__ == "__main__":
    setup()
    results = []
    results.append(("test_success", test_success()))
    results.append(("test_failure", test_failure()))
    results.append(("test_dispatcher_path", test_dispatcher_path()))
    results.append(("test_stale_render", test_stale_render()))
    results.append(("test_explicit_ids_win", test_explicit_ids_win()))
    results.append(("test_no_html_path", test_no_html_path()))
    print(f"\n{'='*40}")
    for name, ok in results:
        print(f"  {name}: {'PASS' if ok else 'FAIL'}")
    if all(ok for _, ok in results):
        print(f"ALL {len(results)} TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
