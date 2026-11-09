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


if __name__ == "__main__":
    setup()
    ok1 = test_success()
    ok2 = test_failure()
    print(f"\n{'='*40}")
    if ok1 and ok2:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
        sys.exit(1)
