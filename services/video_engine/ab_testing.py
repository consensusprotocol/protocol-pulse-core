"""
A/B TESTING FRAMEWORK
======================
Test different content variations and automatically promote winners.

Test Types:
  - Headlines: Different titles for the same article
  - Thumbnails: Different header images
  - Tweet phrasing: Different social copy
  - Posting times: Same content at different times

Tracking:
  - Click-through rates (CTR)
  - Engagement rates
  - Read time
  - Share count

Usage:
    from services.video_engine.ab_testing import ABTestManager
    manager = ABTestManager()
    test = manager.create_test("headline", article_id=123, variants=[
        {"headline": "Bitcoin Hits $100K", "weight": 0.5},
        {"headline": "BTC Breaks Six Figures", "weight": 0.5},
    ])
    variant = manager.get_variant(test_id, user_session_id)
    manager.record_event(test_id, variant_id, "click")
    winner = manager.evaluate_test(test_id)
"""

import os
import json
import sqlite3
import random
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from math import sqrt

logger = logging.getLogger("ABTesting")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "video_engine" / "ab_testing.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Statistical significance threshold
SIGNIFICANCE_THRESHOLD = 0.95  # 95% confidence
MIN_SAMPLE_SIZE = 30           # Minimum events per variant before evaluation
AUTO_PROMOTE_AFTER_HOURS = 48  # Auto-evaluate after 48 hours


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_ab_db():
    """Initialize A/B testing database."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_type TEXT NOT NULL,
            name TEXT NOT NULL,
            article_id INTEGER,
            status TEXT NOT NULL DEFAULT 'active',
            winner_variant_id INTEGER,
            created_at TEXT NOT NULL,
            evaluated_at TEXT,
            metadata TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            content TEXT NOT NULL,
            weight REAL DEFAULT 0.5,
            is_control INTEGER DEFAULT 0,
            metadata TEXT DEFAULT '{}',
            FOREIGN KEY (test_id) REFERENCES tests(id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            variant_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            value REAL DEFAULT 1.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (test_id) REFERENCES tests(id),
            FOREIGN KEY (variant_id) REFERENCES variants(id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            variant_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(test_id, session_id),
            FOREIGN KEY (test_id) REFERENCES tests(id),
            FOREIGN KEY (variant_id) REFERENCES variants(id)
        );

        CREATE INDEX IF NOT EXISTS idx_events_test ON events(test_id);
        CREATE INDEX IF NOT EXISTS idx_events_variant ON events(variant_id);
        CREATE INDEX IF NOT EXISTS idx_assignments_test ON assignments(test_id);
        CREATE INDEX IF NOT EXISTS idx_tests_status ON tests(status);
    """)
    conn.commit()
    conn.close()


init_ab_db()


class ABTestManager:
    """Manage A/B tests, variant assignment, and evaluation."""

    def create_test(self, test_type: str, name: str,
                   variants: List[Dict],
                   article_id: int = None,
                   metadata: Dict = None) -> int:
        """Create a new A/B test.

        Args:
            test_type: "headline", "thumbnail", "tweet", "posting_time"
            name: Human-readable test name
            variants: List of {"name": str, "content": str, "weight": float}
            article_id: Associated article ID (optional)
            metadata: Extra context

        Returns:
            test_id
        """
        conn = _get_conn()
        now = datetime.utcnow().isoformat()

        cursor = conn.execute(
            """INSERT INTO tests (test_type, name, article_id, status, created_at, metadata)
               VALUES (?, ?, ?, 'active', ?, ?)""",
            (test_type, name, article_id, now, json.dumps(metadata or {}))
        )
        test_id = cursor.lastrowid

        for i, variant in enumerate(variants):
            conn.execute(
                """INSERT INTO variants (test_id, name, content, weight, is_control)
                   VALUES (?, ?, ?, ?, ?)""",
                (test_id,
                 variant.get("name", f"Variant {chr(65 + i)}"),
                 json.dumps(variant.get("content", variant)),
                 variant.get("weight", 1.0 / len(variants)),
                 1 if i == 0 else 0)  # First variant is control
            )

        conn.commit()
        conn.close()

        logger.info(f"Created A/B test: {name} ({test_type}, {len(variants)} variants)")
        return test_id

    def get_variant(self, test_id: int, session_id: str) -> Optional[Dict]:
        """Get the assigned variant for a session. Creates assignment if needed.

        Uses deterministic hashing for consistent assignment.
        """
        conn = _get_conn()

        # Check existing assignment
        existing = conn.execute(
            "SELECT variant_id FROM assignments WHERE test_id = ? AND session_id = ?",
            (test_id, session_id)
        ).fetchone()

        if existing:
            variant = conn.execute(
                "SELECT * FROM variants WHERE id = ?",
                (existing["variant_id"],)
            ).fetchone()
            conn.close()
            if variant:
                return dict(variant)
            return None

        # Get test variants
        variants = conn.execute(
            "SELECT * FROM variants WHERE test_id = ? ORDER BY id",
            (test_id,)
        ).fetchall()

        if not variants:
            conn.close()
            return None

        # Deterministic assignment based on session hash
        hash_input = f"{test_id}:{session_id}".encode()
        hash_val = int(hashlib.md5(hash_input).hexdigest(), 16)
        total_weight = sum(v["weight"] for v in variants)
        normalized = hash_val % 1000 / 1000.0

        cumulative = 0.0
        selected = variants[0]
        for v in variants:
            cumulative += v["weight"] / total_weight
            if normalized <= cumulative:
                selected = v
                break

        # Record assignment
        conn.execute(
            """INSERT OR IGNORE INTO assignments
               (test_id, session_id, variant_id, created_at)
               VALUES (?, ?, ?, ?)""",
            (test_id, session_id, selected["id"],
             datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

        return dict(selected)

    def record_event(self, test_id: int, variant_id: int,
                    session_id: str, event_type: str,
                    value: float = 1.0):
        """Record an event (impression, click, read, share, etc.)."""
        conn = _get_conn()
        conn.execute(
            """INSERT INTO events
               (test_id, variant_id, session_id, event_type, value, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (test_id, variant_id, session_id, event_type, value,
             datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()

    def evaluate_test(self, test_id: int) -> Dict:
        """Evaluate test results and determine winner.

        Uses conversion rate comparison with basic statistical significance.
        """
        conn = _get_conn()

        test = conn.execute(
            "SELECT * FROM tests WHERE id = ?", (test_id,)
        ).fetchone()

        if not test:
            conn.close()
            return {"error": "Test not found"}

        variants = conn.execute(
            "SELECT * FROM variants WHERE test_id = ?", (test_id,)
        ).fetchall()

        results = []
        for variant in variants:
            vid = variant["id"]

            # Count events by type
            stats = conn.execute(
                """SELECT event_type, COUNT(*) as count, SUM(value) as total
                   FROM events
                   WHERE test_id = ? AND variant_id = ?
                   GROUP BY event_type""",
                (test_id, vid)
            ).fetchall()

            event_map = {s["event_type"]: {
                "count": s["count"],
                "total": s["total"]
            } for s in stats}

            impressions = event_map.get("impression", {}).get("count", 0)
            clicks = event_map.get("click", {}).get("count", 0)
            reads = event_map.get("read", {}).get("count", 0)
            shares = event_map.get("share", {}).get("count", 0)

            ctr = clicks / impressions if impressions > 0 else 0
            read_rate = reads / clicks if clicks > 0 else 0

            results.append({
                "variant_id": vid,
                "variant_name": variant["name"],
                "is_control": bool(variant["is_control"]),
                "impressions": impressions,
                "clicks": clicks,
                "reads": reads,
                "shares": shares,
                "ctr": round(ctr, 4),
                "read_rate": round(read_rate, 4),
                "composite_score": round(
                    ctr * 0.4 + read_rate * 0.3 + (shares / max(impressions, 1)) * 0.3, 4),
            })

        conn.close()

        # Sort by composite score
        results.sort(key=lambda x: x["composite_score"], reverse=True)

        # Check if we have enough data
        total_impressions = sum(r["impressions"] for r in results)
        sufficient_data = all(
            r["impressions"] >= MIN_SAMPLE_SIZE for r in results)

        # Determine winner
        winner = None
        confidence = 0.0

        if results and sufficient_data and len(results) >= 2:
            best = results[0]
            second = results[1]

            if best["impressions"] > 0 and second["impressions"] > 0:
                # Z-test for proportions
                p1 = best["ctr"]
                p2 = second["ctr"]
                n1 = best["impressions"]
                n2 = second["impressions"]

                p_pool = (best["clicks"] + second["clicks"]) / (n1 + n2)
                if p_pool > 0 and p_pool < 1:
                    se = sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
                    if se > 0:
                        z = (p1 - p2) / se
                        # Rough confidence from z-score
                        if abs(z) > 2.576:
                            confidence = 0.99
                        elif abs(z) > 1.96:
                            confidence = 0.95
                        elif abs(z) > 1.645:
                            confidence = 0.90
                        else:
                            confidence = 0.5 + abs(z) * 0.25

                if confidence >= SIGNIFICANCE_THRESHOLD:
                    winner = best

        evaluation = {
            "test_id": test_id,
            "test_name": test["name"] if test else "",
            "test_type": test["test_type"] if test else "",
            "total_impressions": total_impressions,
            "sufficient_data": sufficient_data,
            "confidence": round(confidence, 3),
            "significance_threshold": SIGNIFICANCE_THRESHOLD,
            "winner": winner,
            "variants": results,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

        # Auto-promote winner if confident
        if winner:
            self._promote_winner(test_id, winner["variant_id"])
            evaluation["status"] = "winner_promoted"
        elif sufficient_data:
            evaluation["status"] = "no_significant_difference"
        else:
            evaluation["status"] = "insufficient_data"

        return evaluation

    def _promote_winner(self, test_id: int, variant_id: int):
        """Mark test as complete and record winner."""
        conn = _get_conn()
        conn.execute(
            """UPDATE tests SET status = 'completed',
               winner_variant_id = ?, evaluated_at = ?
               WHERE id = ?""",
            (variant_id, datetime.utcnow().isoformat(), test_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Test {test_id}: winner promoted (variant {variant_id})")

    def auto_evaluate_expired(self):
        """Auto-evaluate tests that have been running too long."""
        conn = _get_conn()
        cutoff = (datetime.utcnow() - timedelta(
            hours=AUTO_PROMOTE_AFTER_HOURS)).isoformat()

        expired = conn.execute(
            """SELECT id FROM tests
               WHERE status = 'active' AND created_at < ?""",
            (cutoff,)
        ).fetchall()
        conn.close()

        evaluated = []
        for test in expired:
            result = self.evaluate_test(test["id"])
            evaluated.append(result)

        return evaluated

    def get_active_tests(self) -> List[Dict]:
        """Get all active A/B tests."""
        conn = _get_conn()
        tests = conn.execute(
            """SELECT t.*, COUNT(DISTINCT e.session_id) as unique_sessions,
                      COUNT(e.id) as total_events
               FROM tests t
               LEFT JOIN events e ON e.test_id = t.id
               WHERE t.status = 'active'
               GROUP BY t.id
               ORDER BY t.created_at DESC"""
        ).fetchall()
        conn.close()
        return [dict(t) for t in tests]

    def get_test_history(self, limit: int = 20) -> List[Dict]:
        """Get recent test history with results."""
        conn = _get_conn()
        tests = conn.execute(
            """SELECT t.*, v.name as winner_name
               FROM tests t
               LEFT JOIN variants v ON v.id = t.winner_variant_id
               ORDER BY t.created_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(t) for t in tests]

    def create_headline_test(self, article_id: int,
                            headlines: List[str]) -> int:
        """Convenience: create a headline A/B test."""
        variants = [
            {"name": f"Headline {chr(65 + i)}", "content": h}
            for i, h in enumerate(headlines)
        ]
        return self.create_test(
            test_type="headline",
            name=f"Headline test for article {article_id}",
            variants=variants,
            article_id=article_id,
        )

    def create_tweet_test(self, topic: str,
                         tweets: List[str]) -> int:
        """Convenience: create a tweet phrasing A/B test."""
        variants = [
            {"name": f"Tweet {chr(65 + i)}", "content": t}
            for i, t in enumerate(tweets)
        ]
        return self.create_test(
            test_type="tweet",
            name=f"Tweet test: {topic[:50]}",
            variants=variants,
        )
