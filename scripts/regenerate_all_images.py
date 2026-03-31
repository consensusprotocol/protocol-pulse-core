#!/usr/bin/env python3
"""
Batch regenerate ALL article images with Grok AI.
Replaces every Pexels URL with a unique Grok-generated image.
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
from image_service import ImageGenerationService

svc = ImageGenerationService()
log.info(f"Grok key: {bool(svc.xai_key)}, DALL-E key: {bool(svc.openai_key)}")

with app.app_context():
    # Get all articles with Pexels URLs (or duplicated images)
    articles = Article.query.filter(
        Article.cover_image_url.like("%pexels%")
    ).order_by(Article.created_at.desc()).all()
    
    log.info(f"Found {len(articles)} articles with Pexels images to regenerate")
    
    success = 0
    failed = 0
    
    for i, art in enumerate(articles):
        try:
            log.info(f"[{i+1}/{len(articles)}] Generating image for: {art.title[:60]}")
            
            # Generate unique image
            result = svc.generate_article_header_image(
                title=art.title,
                category=art.category or "Bitcoin",
            )
            
            if result and "default-header" not in result:
                art.cover_image_url = result
                db.session.commit()
                success += 1
                log.info(f"  OK: {result}")
            else:
                failed += 1
                log.warning(f"  FAILED: got {result}")
            
            # Rate limit: 2 second delay between Grok calls
            time.sleep(2)
            
            # Progress checkpoint every 20 articles
            if (i + 1) % 20 == 0:
                log.info(f"=== PROGRESS: {i+1}/{len(articles)} done, {success} OK, {failed} failed ===")
                
        except Exception as e:
            failed += 1
            log.error(f"  ERROR: {e}")
            time.sleep(5)  # longer delay on error
    
    log.info(f"=== COMPLETE: {success} regenerated, {failed} failed out of {len(articles)} ===")
