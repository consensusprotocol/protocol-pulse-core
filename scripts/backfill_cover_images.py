#!/usr/bin/env python3
"""
Protocol Pulse — Backfill cover_image_url (BUG 4 fix)

Step 1: Copy header_image_url → cover_image_url where cover is NULL but header exists
Step 2: For articles still NULL, fetch from Pexels API using title keywords
Step 3: Idempotent — skips articles that already have cover_image_url

Usage:
  python3 scripts/backfill_cover_images.py          # from project root
  python3 scripts/backfill_cover_images.py --dry-run # preview only
"""

import os
import sys
import re
import time
import logging
import argparse

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("backfill_cover_images")

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"
RATE_LIMIT_DELAY = 1.5  # seconds between Pexels calls


def extract_keywords(title):
    """Extract meaningful search keywords from article title."""
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'shall', 'can', 'to', 'of', 'in', 'for',
        'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
        'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
        'where', 'why', 'how', 'all', 'both', 'each', 'few', 'more', 'most',
        'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        'so', 'than', 'too', 'very', 'just', 'and', 'but', 'or', 'if', 'its',
        'new', 'what', 'this', 'that', 'it', 'up',
    }
    words = re.sub(r'[^a-zA-Z\s]', '', title.lower()).split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return ' '.join(keywords[:5]) or 'bitcoin cryptocurrency'


def search_pexels(query):
    """Search Pexels for a cover image. Returns URL or None."""
    if not PEXELS_API_KEY:
        return None
    import requests
    try:
        resp = requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            photos = data.get("photos", [])
            if photos:
                return photos[0]["src"]["large2x"]
        else:
            logger.warning(f"Pexels returned {resp.status_code} for query '{query}'")
    except Exception as e:
        logger.warning(f"Pexels error for '{query}': {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Backfill article cover images")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    from app import app, db
    from models import Article

    with app.app_context():
        # ── Step 1: SQL migration — copy header_image_url to cover_image_url ──
        logger.info("Step 1: Copying header_image_url → cover_image_url where cover is NULL...")
        if not args.dry_run:
            result = db.session.execute(db.text("""
                UPDATE articles
                SET cover_image_url = header_image_url
                WHERE (cover_image_url IS NULL OR cover_image_url = '')
                  AND header_image_url IS NOT NULL
                  AND header_image_url != ''
                  AND header_image_url LIKE 'http%'
            """))
            db.session.commit()
            logger.info(f"  Step 1 done: {result.rowcount} articles updated from header_image_url")
        else:
            count = db.session.execute(db.text("""
                SELECT COUNT(*) FROM articles
                WHERE (cover_image_url IS NULL OR cover_image_url = '')
                  AND header_image_url IS NOT NULL
                  AND header_image_url != ''
                  AND header_image_url LIKE 'http%'
            """)).scalar()
            logger.info(f"  Step 1 [DRY RUN]: would update {count} articles")

        # ── Step 2: Pexels backfill for remaining NULL articles ──
        if not PEXELS_API_KEY:
            logger.warning("PEXELS_API_KEY not set — skipping Step 2 (Pexels backfill)")
            return

        nulls = Article.query.filter(
            db.or_(Article.cover_image_url.is_(None), Article.cover_image_url == '')
        ).all()
        logger.info(f"Step 2: {len(nulls)} articles still missing cover_image_url, searching Pexels...")

        updated = 0
        for article in nulls:
            keywords = extract_keywords(article.title or "")
            url = search_pexels(keywords)
            if url:
                if not args.dry_run:
                    article.cover_image_url = url
                    db.session.commit()
                logger.info(f"  [{article.id}] → {url[:80]}...")
                updated += 1
            else:
                logger.info(f"  [{article.id}] No Pexels result for: {keywords}")
            time.sleep(RATE_LIMIT_DELAY)

        logger.info(f"Step 2 done: {updated}/{len(nulls)} articles backfilled from Pexels")


if __name__ == "__main__":
    main()
