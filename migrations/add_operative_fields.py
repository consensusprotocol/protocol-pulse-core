"""
Migration: Add Phase 7 operative rank fields to User model
Run this script to add new columns to existing database

Usage: python migrations/add_operative_fields.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from sqlalchemy import text
import logging
import hashlib
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    with app.app_context():
        columns_to_add = [
            ("operative_rank", "INTEGER DEFAULT 1"),
            ("drill_completions", "INTEGER DEFAULT 0"),
            ("brief_clicks", "INTEGER DEFAULT 0"),
            ("operative_slug", "VARCHAR(100)"),
            ("crm_synced_at", "TIMESTAMP"),
            ("last_drill_at", "TIMESTAMP"),
            ("last_brief_at", "TIMESTAMP")
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                db.session.execute(text(f'ALTER TABLE "user" ADD COLUMN {column_name} {column_type}'))
                db.session.commit()
                logger.info(f"Added column: {column_name}")
            except Exception as e:
                db.session.rollback()
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    logger.info(f"Column {column_name} already exists, skipping")
                else:
                    logger.warning(f"Could not add column {column_name}: {e}")
        
        logger.info("Column migration completed")
        backfill_slugs()


def backfill_slugs():
    """Generate operative slugs for existing users using raw SQL"""
    with app.app_context():
        try:
            result = db.session.execute(text('SELECT id, username, email FROM "user" WHERE operative_slug IS NULL'))
            users = result.fetchall()
            logger.info(f"Found {len(users)} users without slugs")
            
            for user in users:
                user_id, username, email = user
                base = username.lower().replace(' ', '-')[:20]
                base = ''.join(c for c in base if c.isalnum() or c == '-')
                unique_hash = hashlib.md5(f"{email}{user_id}{time.time()}".encode()).hexdigest()[:6]
                slug = f"{base}-{unique_hash}"
                
                db.session.execute(
                    text('UPDATE "user" SET operative_slug = :slug WHERE id = :user_id'),
                    {"slug": slug, "user_id": user_id}
                )
                logger.info(f"Generated slug for user {user_id}: {slug}")
            
            db.session.commit()
            logger.info(f"Backfilled {len(users)} user slugs")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Backfill failed: {e}")


if __name__ == "__main__":
    run_migration()
