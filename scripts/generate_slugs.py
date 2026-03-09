#!/usr/bin/env python3
"""
generate_slugs.py — One-time migration to add slugs to all existing articles.
Law 4: Every article gets a URL-safe slug derived from its title.

Run from project root:
  python3 scripts/generate_slugs.py [--dry-run]

Safe to re-run: skips articles that already have a slug.
"""

import re
import sys
import os
import hashlib
import logging

# Project root
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_slugs")

DRY_RUN = "--dry-run" in sys.argv


def _title_to_slug(title: str, article_id: int) -> str:
    """Generate a URL-safe slug from title. Appends short hash for uniqueness."""
    base = re.sub(r'[^a-z0-9]+', '-', title.lower().strip()).strip('-')
    base = base[:80]  # max 80 chars before hash
    short_hash = hashlib.md5(f"{article_id}:{title}".encode()).hexdigest()[:6]
    return f"{base}-{short_hash}"


def run():
    from app import app
    from app import db
    from models import Article

    with app.app_context():
        # First: add slug column if it doesn't exist (SQLite ALTER TABLE)
        try:
            db.engine.execute("ALTER TABLE articles ADD COLUMN slug VARCHAR(300)")
            logger.info("Added slug column to articles table")
        except Exception:
            pass  # Column already exists

        try:
            db.engine.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_articles_slug ON articles(slug)")
            logger.info("Created unique index on articles.slug")
        except Exception:
            pass

        # Fetch articles without slug
        articles = Article.query.filter(
            (Article.slug == None) | (Article.slug == '')
        ).all()

        logger.info(f"Found {len(articles)} articles without slug")

        if DRY_RUN:
            logger.info("DRY RUN — showing first 10 slugs:")
            for a in articles[:10]:
                slug = _title_to_slug(a.title, a.id)
                logger.info(f"  [{a.id}] {a.title[:60]} → {slug}")
            return

        updated = 0
        skipped = 0
        for a in articles:
            slug = _title_to_slug(a.title, a.id)
            # Check for conflicts
            existing = Article.query.filter_by(slug=slug).first()
            if existing and existing.id != a.id:
                slug = f"{slug}-{a.id}"
            a.slug = slug
            updated += 1

            if updated % 100 == 0:
                db.session.commit()
                logger.info(f"  Progress: {updated}/{len(articles)}")

        db.session.commit()
        logger.info(f"Done — {updated} articles slugged, {skipped} skipped")


if __name__ == "__main__":
    run()
