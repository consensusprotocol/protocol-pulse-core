#!/usr/bin/env python3
"""
regenerate_card_images.py — Replace placeholder/duplicate card images with diverse Pexels stock.

All image selection routed through services/articles/image_guard.py for
perceptual-hash dedup, ban-list, and quality checks.

Usage:
    cd ~/worktrees/site-fix/core && python3 ../scripts/regenerate_card_images.py
    cd ~/worktrees/site-fix/core && python3 ../scripts/regenerate_card_images.py --dry-run
    cd ~/worktrees/site-fix/core && python3 ../scripts/regenerate_card_images.py --homepage-only
"""
import os, sys, logging, io

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
# Also add repo root so image_guard can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/protocol_pulse/.env'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def mean_brightness_url(url, timeout=8):
    """Return mean brightness (0-255) for a URL-based image. Returns 255 on failure."""
    try:
        from PIL import Image
        import requests
        r = requests.get(url, timeout=timeout, stream=True)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert('L')
        pixels = list(img.getdata())
        return sum(pixels) / len(pixels) if pixels else 255
    except Exception as e:
        logger.warning("brightness check failed for %s: %s", url[:60], e)
        return 255


def main():
    dry_run = '--dry-run' in sys.argv
    homepage_only = '--homepage-only' in sys.argv

    os.environ.setdefault('DATABASE_URL',
        'sqlite:////home/ultron/protocol_pulse/instance/protocol_pulse.db')

    from app import app, db
    import models

    with app.app_context():
        if homepage_only:
            featured = models.Article.query.filter_by(published=True).order_by(
                models.Article.importance_score.desc().nullslast(),
                models.Article.created_at.desc()
            ).limit(3).all()
            recent = models.Article.query.filter_by(published=True).order_by(
                models.Article.created_at.desc()
            ).limit(12).all()
            seen_ids = set()
            articles = []
            for a in featured + recent:
                if a.id not in seen_ids:
                    seen_ids.add(a.id)
                    articles.append(a)
            articles = articles[:12]
        else:
            articles = models.Article.query.filter(
                models.Article.published == True,
                db.or_(
                    models.Article.cover_image_url.like('%header_html_%'),
                    models.Article.cover_image_url.is_(None),
                    models.Article.cover_image_url == '',
                    models.Article.cover_image_url == '/static/images/default-header.png',
                )
            ).order_by(models.Article.created_at.desc()).all()

        logger.info("Processing %d articles (homepage_only=%s)", len(articles), homepage_only)

        from services.image_service import ImageGenerationService
        img_svc = ImageGenerationService()

        repaired = 0
        skipped = 0
        results = []

        for a in articles:
            old_url = a.cover_image_url or a.header_image_url or ''
            needs_regen = False

            if not old_url or 'header_html_' in old_url or old_url == '/static/images/default-header.png':
                needs_regen = True
                reason = "placeholder"
            else:
                # Skip remote URLs — they need regeneration too
                if old_url.startswith('http'):
                    needs_regen = True
                    reason = "remote_url"
                else:
                    reason = "ok (local)"

            if not needs_regen:
                results.append({'id': a.id, 'title': a.title[:50], 'url': old_url[:60],
                                'brightness': 'ok', 'action': 'skip', 'phash': a.image_phash or ''})
                skipped += 1
                continue

            new_url, new_phash = img_svc.generate_article_header_image_with_phash(
                title=a.title or 'bitcoin', category=a.category or 'bitcoin')

            if new_url and new_url != '/static/images/default-header.png':
                if dry_run:
                    logger.info("[DRY] ID %d: %s -> %s (phash=%s)",
                                a.id, reason, new_url[:60], new_phash or '?')
                else:
                    a.cover_image_url = new_url
                    a.header_image_url = new_url
                    if new_phash and hasattr(a, 'image_phash'):
                        a.image_phash = new_phash
                    db.session.commit()
                    logger.info("OK ID %d: phash=%s %s",
                                a.id, new_phash or '?', new_url[:70])
                results.append({'id': a.id, 'title': a.title[:50], 'url': new_url[:80],
                                'brightness': 'n/a', 'action': 'regen',
                                'phash': new_phash or ''})
                repaired += 1
            else:
                logger.warning("FAIL ID %d: image service returned default", a.id)
                results.append({'id': a.id, 'title': a.title[:50], 'url': old_url[:60],
                                'brightness': '?', 'action': 'fail', 'phash': ''})

        print(f"\n{'DRY RUN ' if dry_run else ''}SUMMARY: {repaired} repaired, {skipped} skipped, {len(articles)} total")
        print("\nResults:")
        for r in results:
            print(f"  ID {r['id']:5d} | {r['action']:5s} | bright={r['brightness']:>5s} | phash={r['phash'][:16]:16s} | {r['title']}")
            if r['action'] == 'regen':
                print(f"         {r['url']}")


if __name__ == '__main__':
    main()
