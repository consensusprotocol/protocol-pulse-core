#!/usr/bin/env python3
"""
migrate_image_guard_columns.py — Add image_status and image_phash columns to the article table.

Usage:
    python scripts/migrate_image_guard_columns.py

Safe to run multiple times (uses try/except for each ALTER).
"""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    from app import app, db

    columns = [
        ("image_status", "VARCHAR(30) DEFAULT 'ok'"),
        ("image_phash", "VARCHAR(64)"),
    ]

    with app.app_context():
        conn = db.engine.connect()
        for col_name, col_type in columns:
            try:
                conn.execute(db.text(
                    "ALTER TABLE article ADD COLUMN %s %s" % (col_name, col_type)
                ))
                conn.commit() if hasattr(conn, "commit") else None
                logger.info("Added column: article.%s (%s)", col_name, col_type)
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("Column article.%s already exists — skipping.", col_name)
                else:
                    logger.warning("Could not add column article.%s: %s", col_name, e)
        conn.close()

    logger.info("Migration complete.")


if __name__ == "__main__":
    main()
