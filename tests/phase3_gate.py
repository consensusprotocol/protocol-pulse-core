#!/usr/bin/env python3
"""
PHASE 3 GATE TEST — Cross-Session Visitor Memory
5 returning visitor scenarios — all must pass.
Tests: fingerprint hashing, memory persistence, returning context injection,
       new visitor (no false memory), 30-day expiry.
"""

import os
import sys
import json
import time
import unittest
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "oracle"))

from oracle_memory import make_fingerprint, load_visitor, save_visitor, DB_PATH, _get_conn


class Phase3VisitorMemory(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Use a test DB to avoid polluting production."""
        # Backup original path and override
        import oracle_memory
        cls._orig_db = oracle_memory.DB_PATH
        cls._test_db = cls._orig_db.parent / "visitor_memory_test.db"
        oracle_memory.DB_PATH = cls._test_db
        # Clean slate
        if cls._test_db.exists():
            cls._test_db.unlink()

    @classmethod
    def tearDownClass(cls):
        """Restore original DB path and clean up test DB."""
        import oracle_memory
        oracle_memory.DB_PATH = cls._orig_db
        if cls._test_db.exists():
            cls._test_db.unlink()

    def test_01_fingerprint_deterministic(self):
        """Fingerprint is deterministic and 32 chars."""
        fp1 = make_fingerprint("192.168.1.1", "Mozilla/5.0", "abc123")
        fp2 = make_fingerprint("192.168.1.1", "Mozilla/5.0", "abc123")
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 32)
        # Different inputs → different fingerprint
        fp3 = make_fingerprint("10.0.0.1", "Chrome/99", "xyz")
        self.assertNotEqual(fp1, fp3)

    def test_02_no_pii_stored(self):
        """Fingerprint hash cannot be reversed to IP."""
        fp = make_fingerprint("192.168.1.100", "Mozilla/5.0 Firefox", "token42")
        self.assertNotIn("192.168", fp)
        self.assertNotIn("Firefox", fp)
        self.assertNotIn("token42", fp)

    def test_03_mid_setup_return(self):
        """Scenario 1: Visitor was mid-Coldcard setup, returns and gets context."""
        fp = make_fingerprint("1.2.3.4", "TestAgent", "setup_user")
        save_visitor(fp, {
            "personality": "ANALYTICAL",
            "session_summaries": ["User was setting up Coldcard, reached PIN step"],
            "setup_device": "coldcard",
            "setup_step": 3,
            "topics_seen": ["coldcard", "setup", "tamper", "seed"],
            "products_shown": [],
        })
        loaded = load_visitor(fp)
        self.assertIsNotNone(loaded, "Memory should load for recent visitor")
        self.assertEqual(loaded["session_count"], 1)
        self.assertEqual(loaded["setup_device"], "coldcard")
        self.assertEqual(loaded["setup_step"], 3)
        self.assertIn("coldcard", loaded["topics_seen"])
        self.assertIn("Coldcard", loaded["session_summaries"][0])

    def test_04_question_asker_returns(self):
        """Scenario 2: Visitor asked wallet questions, returns and topics are remembered."""
        fp = make_fingerprint("5.6.7.8", "TestAgent", "question_user")
        save_visitor(fp, {
            "personality": "AMIABLE",
            "session_summaries": ["User asked about cold wallets, self custody, and UTXOs"],
            "topics_seen": ["wallet", "custody", "utxo", "bitcoin"],
            "products_shown": ["coldcard"],
        })
        loaded = load_visitor(fp)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["session_count"], 1)
        self.assertIn("wallet", loaded["topics_seen"])
        self.assertIn("custody", loaded["topics_seen"])
        self.assertIn("coldcard", loaded["products_shown"])

    def test_05_node_setup_return(self):
        """Scenario 3: Visitor was setting up a node, returns with context."""
        fp = make_fingerprint("9.10.11.12", "TestAgent", "node_user")
        save_visitor(fp, {
            "personality": "DRIVER",
            "session_summaries": ["User setting up Umbrel node on Raspberry Pi"],
            "setup_device": "umbrel",
            "setup_step": 2,
            "topics_seen": ["node", "umbrel", "raspberry", "bitcoin"],
            "products_shown": [],
        })
        loaded = load_visitor(fp)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["setup_device"], "umbrel")
        self.assertIn("Umbrel", loaded["session_summaries"][0])

    def test_06_new_visitor_no_false_memory(self):
        """Scenario 4: New visitor should NOT get any returning context."""
        fp = make_fingerprint("99.99.99.99", "BrandNewAgent", "fresh_user")
        loaded = load_visitor(fp)
        self.assertIsNone(loaded, "New visitor must return None — no false memory")

    def test_07_expired_memory(self):
        """Scenario 5: Memory older than 30 days should expire."""
        fp = make_fingerprint("88.88.88.88", "OldAgent", "expired_user")
        # Save with timestamp 31 days ago
        import oracle_memory
        conn = oracle_memory._get_conn()
        old_ts = int(time.time()) - (31 * 86400)
        conn.execute("""
            INSERT OR REPLACE INTO visitor_memory
                (fingerprint, last_seen, session_count, personality,
                 session_summaries, setup_device, setup_step, topics_seen, products_shown)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (fp, old_ts, 5, "EXPRESSIVE", '["Old chat about mining"]', None, 0, '["mining"]', '[]'))
        conn.commit()
        conn.close()

        loaded = load_visitor(fp)
        self.assertIsNone(loaded, "Memory >30 days old must expire")

    def test_08_session_count_increments(self):
        """Session count increments on each save."""
        fp = make_fingerprint("7.7.7.7", "CountAgent", "counter")
        save_visitor(fp, {"personality": "AMIABLE", "session_summaries": ["s1"]})
        save_visitor(fp, {"personality": "AMIABLE", "session_summaries": ["s1", "s2"]})
        save_visitor(fp, {"personality": "AMIABLE", "session_summaries": ["s1", "s2", "s3"]})
        loaded = load_visitor(fp)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["session_count"], 3)

    def test_09_max_3_summaries(self):
        """Only the last 3 summaries are kept."""
        fp = make_fingerprint("6.6.6.6", "SummaryAgent", "summary_test")
        save_visitor(fp, {
            "personality": "AMIABLE",
            "session_summaries": ["s1", "s2", "s3", "s4", "s5"],
        })
        loaded = load_visitor(fp)
        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded["session_summaries"]), 3)
        self.assertEqual(loaded["session_summaries"], ["s3", "s4", "s5"])

    def test_10_context_injection_format(self):
        """Verify the context injection builds correctly for a returning visitor."""
        fp = make_fingerprint("3.3.3.3", "CtxAgent", "ctx_user")
        save_visitor(fp, {
            "personality": "DRIVER",
            "session_summaries": ["Discussed Coldcard setup, reached step 3"],
            "setup_device": "coldcard",
            "setup_step": 3,
            "topics_seen": ["coldcard", "setup", "bitcoin"],
            "products_shown": ["sparrow"],
        })
        loaded = load_visitor(fp)
        self.assertIsNotNone(loaded)

        # Simulate the context injection logic from oracle_dialogue_engine
        days_ago = int((time.time() - loaded["last_seen"]) / 86400)
        summaries = loaded.get("session_summaries", [])
        topics = loaded.get("topics_seen", [])
        products = loaded.get("products_shown", [])
        setup = loaded.get("setup_device")
        step = loaded.get("setup_step", 0)

        memory_ctx = [f"RETURNING VISITOR — session #{loaded['session_count']}, last seen {days_ago} day(s) ago"]
        if summaries:
            memory_ctx.append(f"Prior sessions: {' | '.join(summaries[-2:])}")
        if setup and step > 0:
            memory_ctx.append(f"Was setting up: {setup} (reached step {step})")
        if topics:
            memory_ctx.append(f"Already knows about: {', '.join(topics[-8:])}")
        if products:
            memory_ctx.append(f"Products already discussed: {', '.join(products)}")

        ctx = "\n".join(memory_ctx)
        self.assertIn("RETURNING VISITOR", ctx)
        self.assertIn("session #1", ctx)
        self.assertIn("coldcard", ctx.lower())
        self.assertIn("step 3", ctx)
        self.assertIn("sparrow", ctx)
        print(f"  Context injection preview:\n{ctx}")


def run_gate():
    print("=" * 60)
    print("PHASE 3 GATE — Cross-Session Visitor Memory")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Phase3VisitorMemory)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"PHASE 3 GATE: PASS ({passed}/{total})")
        print("All returning visitor scenarios verified.")
    else:
        print(f"PHASE 3 GATE: FAIL ({passed}/{total})")
        print("Fix failures before proceeding.")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_gate())
