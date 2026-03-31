#!/usr/bin/env python3
"""
IMAGE WATCHDOG — runs every 5 minutes via cron.
Finds ANY article with missing/broken/Pexels/Unsplash images and generates Grok replacements.
This is the PERMANENT fix. No article will ever show without an image again.

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
from image_service import ImageGenerationService

svc = ImageGenerationService()

with app.app_context():
    broken = Article.query.filter(db.or_(
        Article.cover_image_url == None,
        Article.cover_image_url == '',
        Article.cover_image_url.like('%pexels%'),
        Article.cover_image_url.like('%unsplash%'),
        Article.cover_image_url.like('%default-header%'),
    )).order_by(Article.created_at.desc()).all()

    if not broken:
        log.info("All articles have valid images. Nothing to do.")
        sys.exit(0)

    log.info(f"Found {len(broken)} articles with missing/broken images")

    fixed = 0
    for a in broken:
        try:
            result = svc.generate_article_header_image(
                title=a.title,
                category=a.category or "Bitcoin",
            )
            if result and "default-header" not in result:
                a.cover_image_url = result
                db.session.commit()
                fixed += 1
                log.info(f"  FIXED: {a.title[:50]} -> {result}")
            else:
                log.warning(f"  FAILED: {a.title[:50]} -> {result}")
            time.sleep(2)
        except Exception as e:
            log.error(f"  ERROR: {a.title[:50]} -> {e}")
            time.sleep(5)

    log.info(f"Done: {fixed}/{len(broken)} fixed")
