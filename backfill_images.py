#!/usr/bin/env python3
"""
Backfill v3: regenerate images for articles with NULL/empty/default/tiny placeholder files.
Routes through image_guard (phash dedup) via get_pexels_image.
Run from ~/protocol_pulse: python3 backfill_images.py
"""
import os, sys, time, logging
sys.path.insert(0, '/home/ultron/protocol_pulse')
sys.path.insert(0, '/home/ultron/protocol_pulse/core')
sys.path.insert(0, '/home/ultron/protocol_pulse/services')
from dotenv import load_dotenv
load_dotenv('/home/ultron/protocol_pulse/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backfill')

STATIC_ROOT = '/home/ultron/protocol_pulse/static'
REAL_IMAGE_MIN_BYTES = 25 * 1024
SLEEP_BETWEEN = 3

from app import app, db
from models import Article
from services.pexels_image import get_pexels_image

def is_real_image(url):
    """Return True if the cover_image_url points to a real (non-placeholder) image."""
    if not url or 'default-header' in url:
        return False
    # Remote URLs (pexels, etc) are valid
    if url.startswith('http'):
        return True
    if url.startswith('/static/'):
        path = os.path.join(STATIC_ROOT, url.lstrip('/static/'))
        if os.path.exists(path):
            return os.path.getsize(path) >= REAL_IMAGE_MIN_BYTES
    return False

def main():
    with app.app_context():
        articles = Article.query.filter(Article.published == True).order_by(Article.id).all()
        to_fix = [a for a in articles if not is_real_image(a.cover_image_url)]
        logger.info(f"Articles needing real images: {len(to_fix)} / {len(articles)} total")

        # Load DB phashes for dedup
        ph_rows = db.session.execute(
            db.text("SELECT image_phash FROM articles WHERE image_phash IS NOT NULL AND image_phash != ''")
        ).fetchall()
        db_phashes = {r[0] for r in ph_rows}
        session_phashes = set()

        success = 0
        failed = 0
        for i, article in enumerate(to_fix):
            logger.info(f"[{i+1}/{len(to_fix)}] id={article.id}: {article.title[:70]}")
            try:
                url, phash = get_pexels_image(
                    article.title or "bitcoin",
                    article.category or "bitcoin",
                    article_id=article.id,
                    db_phashes=db_phashes,
                    session_phashes=session_phashes,
                )
                if url and "default-header" not in url:
                    article.cover_image_url = url
                    article.header_image_url = url
                    if phash and hasattr(article, 'image_phash'):
                        article.image_phash = phash
                    db.session.commit()
                    logger.info(f"  OK: {url[:60]}")
                    success += 1
                else:
                    logger.warning(f"  FAIL: service returned {url}")
                    failed += 1
            except Exception as e:
                logger.error(f"  ERROR: {e}")
                db.session.rollback()
                failed += 1
            if i < len(to_fix) - 1:
                time.sleep(SLEEP_BETWEEN)

        logger.info(f"DONE: {success} updated, {failed} failed/skipped")

if __name__ == '__main__':
    main()
