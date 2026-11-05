#!/usr/bin/env python3
"""
IMAGE WATCHDOG — runs every 5 minutes via cron.
Finds articles with NULL/empty/default cover images and generates replacements
via the guarded pexels_image path (phash dedup, image_guard checks).

Pexels and Unsplash URLs are VALID cover images — do NOT replace them.

Cron: */5 * * * * /usr/bin/python3 /home/ultron/protocol_pulse/scripts/image_watchdog.py >> /home/ultron/protocol_pulse/logs/image_watchdog.log 2>&1
"""
import os, sys, time, logging

os.chdir("/home/ultron/protocol_pulse")
sys.path.insert(0, "/home/ultron/protocol_pulse")
sys.path.insert(0, "/home/ultron/protocol_pulse/core")
sys.path.insert(0, "/home/ultron/protocol_pulse/services")

for line in open(".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

logging.basicConfig(
    level=logging.INFO,
    format="[img_watchdog] %(asctime)s %(message)s",
)
log = logging.getLogger("img_watchdog")

from app import app, db
from models import Article

with app.app_context():
    # Only fix truly broken images: NULL, empty, or default placeholder.
    # Pexels and Unsplash URLs are VALID — leave them alone.
    broken = Article.query.filter(db.or_(
        Article.cover_image_url == None,
        Article.cover_image_url == '',
        Article.cover_image_url.like('%default-header%'),
    )).filter(Article.published == True).order_by(
        Article.created_at.desc()
    ).limit(20).all()

    if not broken:
        log.info("All published articles have valid images. Nothing to do.")
        sys.exit(0)

    log.info(f"Found {len(broken)} articles with missing/default images")

    # Load existing phashes for dedup
    all_phashes_rows = db.session.execute(
        db.text("SELECT image_phash FROM articles WHERE image_phash IS NOT NULL AND image_phash != ''")
    ).fetchall()
    db_phashes = {r[0] for r in all_phashes_rows}
    session_phashes = set()

    try:
        from services.image_service import ImageGenerationService
    except ImportError:
        log.error("Cannot import ImageGenerationService — aborting")
        sys.exit(1)

    img_svc = ImageGenerationService()
    fixed = 0
    for a in broken:
        try:
            url, phash = img_svc.generate_article_header_image_with_phash(
                title=a.title or "bitcoin",
                category=a.category or "bitcoin",
            )
            if url and "default-header" not in url:
                a.cover_image_url = url
                a.header_image_url = url
                if phash and hasattr(a, 'image_phash'):
                    a.image_phash = phash
                db.session.commit()
                fixed += 1
                log.info(f"  FIXED: id={a.id} {a.title[:50]} -> {url[:60]}")
            else:
                log.warning(f"  SKIP: id={a.id} {a.title[:50]} (no suitable image)")
            time.sleep(2)
        except Exception as e:
            log.error(f"  ERROR: id={a.id} {a.title[:50]} -> {e}")
            time.sleep(5)

    log.info(f"Done: {fixed}/{len(broken)} fixed")
