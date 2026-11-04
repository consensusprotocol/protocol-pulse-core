#!/usr/bin/env python3
"""
regenerate_card_images.py — Replace header_html_ placeholder images with Pexels stock.

Targets: published articles whose cover_image_url contains 'header_html_' or is NULL.
Strategy: 90% Pexels stock keyed on title keywords, 10% local pool fallback.
Uses article.id as hash seed so the 6 homepage cards always get 6 distinct images.

Usage:
    cd ~/worktrees/site-fix/core && python3 ../scripts/regenerate_card_images.py
    cd ~/worktrees/site-fix/core && python3 ../scripts/regenerate_card_images.py --dry-run
"""
import os, sys, logging
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
# Load production env for API keys
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/protocol_pulse/.env'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def main():
    dry_run = '--dry-run' in sys.argv

    os.environ.setdefault('DATABASE_URL',
        'sqlite:////home/ultron/protocol_pulse/instance/protocol_pulse.db')

    from app import app, db
    import models

    with app.app_context():
        # Find articles with header_html_ images or NULL cover
        bad = models.Article.query.filter(
            models.Article.published == True,
            db.or_(
                models.Article.cover_image_url.like('%header_html_%'),
                models.Article.cover_image_url.is_(None),
                models.Article.cover_image_url == '',
                models.Article.cover_image_url == '/static/images/default-header.png',
            )
        ).order_by(models.Article.created_at.desc()).all()

        logger.info("Found %d articles needing image repair", len(bad))
        if not bad:
            print("No articles need image repair.")
            return

        from services.pexels_image import get_pexels_image

        repaired = 0
        failed = 0
        seen_urls = set()

        for a in bad:
            old_url = a.cover_image_url or a.header_image_url or '(none)'
            new_url = get_pexels_image(a.title or 'bitcoin', a.category or 'bitcoin', article_id=a.id)

            # Ensure uniqueness: if we already assigned this URL, try next page offset
            attempt = 0
            while new_url in seen_urls and attempt < 5:
                attempt += 1
                new_url = get_pexels_image(a.title or 'bitcoin', a.category or 'bitcoin', article_id=a.id + attempt * 100)

            if new_url and new_url != '/static/images/default-header.png':
                seen_urls.add(new_url)
                if dry_run:
                    logger.info("[DRY] ID %d: %s -> %s", a.id, old_url[:60], new_url[:80])
                else:
                    a.cover_image_url = new_url
                    a.header_image_url = new_url
                    db.session.commit()
                    logger.info("OK ID %d: %s", a.id, new_url[:80])
                repaired += 1
            else:
                logger.warning("FAIL ID %d: Pexels returned default", a.id)
                failed += 1

        print(f"\n{'DRY RUN ' if dry_run else ''}SUMMARY: {repaired} repaired, {failed} failed, {len(bad)} total")


if __name__ == '__main__':
    main()
