#!/usr/bin/env python3
"""
migrate_published_at.py — Add published_at column and backfill existing published articles.

Safe to run multiple times (idempotent).

Usage:
    python scripts/migrate_published_at.py
"""

import os
import sys
import sqlite3
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def get_db_path():
    db_url = os.environ.get("DATABASE_URL", "sqlite:///protocol_pulse.db")
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "")
        if "?" in path:
            path = path.split("?")[0]
        return path
    logger.error("This script only supports SQLite. DATABASE_URL: %s", db_url)
    sys.exit(1)


def main():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        logger.error("Database not found at %s", db_path)
        sys.exit(1)

    logger.info("Database: %s", db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(article)")
    columns = [row[1] for row in cursor.fetchall()]

    if "published_at" in columns:
        logger.info("Column 'published_at' already exists — skipping ALTER TABLE.")
    else:
        logger.info("Adding 'published_at' column to article table...")
        cursor.execute("ALTER TABLE article ADD COLUMN published_at DATETIME")
        logger.info("Column added.")

    # Backfill: set published_at = created_at for published articles that don't have it
    cursor.execute("""
        UPDATE article
        SET published_at = created_at
        WHERE published = 1 AND published_at IS NULL
    """)
    backfilled = cursor.rowcount
    logger.info("Backfilled %d published articles with published_at = created_at.", backfilled)

    conn.commit()
    conn.close()
    logger.info("Migration complete.")


if __name__ == "__main__":
    main()
