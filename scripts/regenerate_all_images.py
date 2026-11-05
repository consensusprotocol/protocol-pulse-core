#!/usr/bin/env python3
"""
Batch regenerate article images that are broken (NULL/empty/default).
Routes through image_guard (phash dedup) via get_pexels_image.

Pexels URLs are VALID — this script does NOT replace them.

Run: nohup python3 scripts/regenerate_all_images.py >> logs/image_regen.log 2>&1 &
"""
import os, sys, time, logging

os.chdir("/home/ultron/protocol_pulse")
sys.path.insert(0, "/home/ultron/protocol_pulse")
sys.path.insert(0, "/home/ultron/protocol_pulse/core")
sys.path.insert(0, "/home/ultron/protocol_pulse/services")

# Load .env
for line in open(".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

logging.basicConfig(
    level=logging.INFO,
    format="[img_regen] %(asctime)s %(message)s",
    handlers=[
        logging.FileHandler("logs/image_regen.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("img_regen")

from app import app, db
from models import Article
from services.pexels_image import get_pexels_image

with app.app_context():
    # Only fix truly broken: NULL, empty, or default placeholder
    articles = Article.query.filter(db.or_(
        Article.cover_image_url == None,
        Article.cover_image_url == '',
        Article.cover_image_url.like('%default-header%'),
    )).filter(Article.published == True).order_by(
        Article.created_at.desc()
    ).all()

    log.info(f"Found {len(articles)} articles with missing/default images")

    # Load DB phashes for dedup
    ph_rows = db.session.execute(
        db.text("SELECT image_phash FROM articles WHERE image_phash IS NOT NULL AND image_phash != ''")
    ).fetchall()
    db_phashes = {r[0] for r in ph_rows}
    session_phashes = set()

    success = 0
    failed = 0

    for i, art in enumerate(articles):
        try:
            log.info(f"[{i+1}/{len(articles)}] Generating image for: {art.title[:60]}")

            url, phash = get_pexels_image(
                art.title or "bitcoin",
                art.category or "bitcoin",
                article_id=art.id,
                db_phashes=db_phashes,
                session_phashes=session_phashes,
            )

            if url and "default-header" not in url:
                art.cover_image_url = url
                art.header_image_url = url
                if phash and hasattr(art, 'image_phash'):
                    art.image_phash = phash
                db.session.commit()
                success += 1
                log.info(f"  OK: {url[:60]}")
            else:
                failed += 1
                log.warning(f"  FAILED: got {url}")

            time.sleep(3)

            if (i + 1) % 20 == 0:
                log.info(f"=== PROGRESS: {i+1}/{len(articles)} done, {success} OK, {failed} failed ===")

        except Exception as e:
            failed += 1
            log.error(f"  ERROR: {e}")
            time.sleep(5)

    log.info(f"=== COMPLETE: {success} regenerated, {failed} failed out of {len(articles)} ===")
