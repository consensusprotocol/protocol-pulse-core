#!/usr/bin/env python3
"""
Backfill v2: regenerate images for articles that have <25KB placeholder files.
Skips articles with real images (>25KB). Uses Grok as primary via updated image_service.
Run from ~/protocol_pulse: python3 backfill_images.py
"""
import os, sys, time, logging
sys.path.insert(0, '/home/ultron/protocol_pulse')
from dotenv import load_dotenv
load_dotenv('/home/ultron/protocol_pulse/.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backfill')

STATIC_ROOT = '/home/ultron/protocol_pulse/static'
REAL_IMAGE_MIN_BYTES = 25 * 1024   # anything < 25KB is a placeholder
SLEEP_BETWEEN = 5                   # 5s between calls — Grok has no tight rate limit

from app import app, db
from models import Article
from pp_services.image_service import ImageGenerationService

def is_real_image(url):
    """Return True if the cover_image_url points to a real (non-placeholder) image."""
    if not url or 'default-header' in url:
        return False
    if url.startswith('/static/'):
        path = os.path.join(STATIC_ROOT, url.lstrip('/static/'))
        if os.path.exists(path):
            size = os.path.getsize(path)
            return size >= REAL_IMAGE_MIN_BYTES
    return False

def main():
    img_service = ImageGenerationService()
    with app.app_context():
        articles = Article.query.order_by(Article.id).all()
        to_fix = []
        for a in articles:
            if not is_real_image(a.cover_image_url):
                to_fix.append(a)
        logger.info(f"Articles needing real images: {len(to_fix)} / {len(articles)} total")

        success = 0
        failed = 0
        for i, article in enumerate(to_fix):
            logger.info(f"[{i+1}/{len(to_fix)}] id={article.id}: {article.title[:70]}")
            try:
                new_image = img_service.generate_article_header_image(
                    title=article.title,
                    category=article.category
                )
                if new_image:
                    # Verify the saved file is a real image
                    if new_image.startswith('/static/'):
                        path = os.path.join(STATIC_ROOT, new_image.lstrip('/static/'))
                        size = os.path.getsize(path) if os.path.exists(path) else 0
                        if size < REAL_IMAGE_MIN_BYTES:
                            logger.warning(f"  SKIP: generated file is only {size}B (placeholder), not updating DB")
                            failed += 1
                            if i < len(to_fix) - 1:
                                time.sleep(SLEEP_BETWEEN)
                            continue
                    article.cover_image_url = new_image
                    db.session.commit()
                    _p = os.path.join(STATIC_ROOT, new_image.lstrip("/static/"))
                    _kb = os.path.getsize(_p)//1024 if os.path.exists(_p) else 0
                    logger.info(f"  OK: {new_image} ({_kb}KB)")
                    success += 1
                else:
                    logger.warning(f"  FAIL: service returned None")
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
