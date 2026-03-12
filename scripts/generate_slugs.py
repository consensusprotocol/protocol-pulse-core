#!/usr/bin/env python3
"""
Protocol Pulse — Generate slugs for all existing articles (Law 4).

Creates URL-safe slugs from article titles. Appends short hash for uniqueness.
Idempotent — skips articles that already have a slug.

Usage: python3 scripts/generate_slugs.py [--dry-run]
"""

import os
import re
import sys
import hashlib
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_slugs")

DRY_RUN = "--dry-run" in sys.argv


def slugify(title, article_id=None):
    """Convert title to URL-safe slug with short hash for uniqueness."""
    slug = title.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')[:80] or 'untitled'
    if article_id is not None:
        short_hash = hashlib.md5(f"{article_id}:{title}".encode()).hexdigest()[:6]
        slug = f"{slug}-{short_hash}"
    return slug


def main():
    from app import app, db
    from models import Article

    with app.app_context():
        # Ensure slug column exists
        try:
            db.session.execute(db.text(
                "ALTER TABLE articles ADD COLUMN slug VARCHAR(300)"
            ))
            db.session.commit()
            logger.info("Added slug column to articles table")
        except Exception:
            db.session.rollback()
            logger.info("slug column already exists")

        # Create unique index if not exists
        try:
            db.session.execute(db.text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_articles_slug ON articles(slug)"
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()

        articles = Article.query.filter(
            db.or_(Article.slug.is_(None), Article.slug == '')
        ).all()
        logger.info(f"Found {len(articles)} articles without slugs")

        if DRY_RUN:
            logger.info("DRY RUN — showing first 10 slugs:")
            for a in articles[:10]:
                slug = slugify(a.title or f"article-{a.id}", a.id)
                logger.info(f"  [{a.id}] {(a.title or '')[:60]} → {slug}")
            return

        seen_slugs = set()
        # Pre-load existing slugs
        existing = db.session.execute(db.text(
            "SELECT slug FROM articles WHERE slug IS NOT NULL AND slug != ''"
        )).fetchall()
        for row in existing:
            seen_slugs.add(row[0])

        updated = 0
        for article in articles:
            slug = slugify(article.title or f"article-{article.id}", article.id)
            if slug in seen_slugs:
                slug = f"{slug}-{article.id}"
            seen_slugs.add(slug)
            article.slug = slug
            updated += 1

            if updated % 100 == 0:
                db.session.commit()
                logger.info(f"  Progress: {updated}/{len(articles)}")

        db.session.commit()
        logger.info(f"Generated slugs for {updated} articles")


if __name__ == "__main__":
    main()
