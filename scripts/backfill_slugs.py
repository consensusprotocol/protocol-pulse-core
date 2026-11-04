#!/usr/bin/env python3
"""
backfill_slugs.py — Set a unique slug on every published article with slug=NULL or numeric.

Idempotent: skips rows that already have a valid non-numeric slug.
Slug rules: slugify(title), max 80 chars, dedupe with -2/-3 suffix, never numeric-only.

Usage:
    cd ~/worktrees/site-fix/core && python3 ../scripts/backfill_slugs.py --dry-run
    cd ~/worktrees/site-fix/core && python3 ../scripts/backfill_slugs.py
"""
import os, sys, re, logging

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def slugify(title, max_len=80):
    """Convert title to URL slug: lowercase, alphanumeric + hyphens, max_len chars."""
    s = re.sub(r'[^\w\s-]', '', (title or '').lower())
    s = re.sub(r'[-\s]+', '-', s).strip('-')
    return s[:max_len] if s else ''


def main():
    dry_run = '--dry-run' in sys.argv

    os.environ.setdefault('DATABASE_URL',
        'sqlite:////home/ultron/protocol_pulse/instance/protocol_pulse.db')

    from app import app, db
    import models

    with app.app_context():
        # Load all existing slugs for dedup
        all_slugs = set()
        rows = db.session.query(models.Article.slug).filter(
            models.Article.slug.isnot(None),
            models.Article.slug != ''
        ).all()
        for (s,) in rows:
            all_slugs.add(s)

        # Find articles needing slugs: published, slug is NULL or empty or numeric-only
        articles = models.Article.query.filter(
            models.Article.published == True,
            db.or_(
                models.Article.slug.is_(None),
                models.Article.slug == '',
                # numeric-only slugs are ambiguous with the int route
            )
        ).order_by(models.Article.id).all()

        # Also grab articles with numeric-only slugs
        numeric_slug_articles = models.Article.query.filter(
            models.Article.published == True,
            models.Article.slug.isnot(None),
            models.Article.slug != '',
        ).all()
        numeric_slug_articles = [a for a in numeric_slug_articles
                                  if a.slug and a.slug.isdigit()]

        articles = articles + numeric_slug_articles

        logger.info("Found %d articles needing slugs (dry_run=%s)", len(articles), dry_run)

        updated = 0
        for a in articles:
            slug = slugify(a.title)
            if not slug or slug.isdigit():
                slug = f"article-{a.id}"

            # Dedupe
            base = slug
            counter = 2
            while slug in all_slugs:
                slug = f"{base}-{counter}"
                counter += 1

            if dry_run:
                logger.info("[DRY] ID %d: slug='%s' (title: %s)", a.id, slug, (a.title or '')[:50])
            else:
                a.slug = slug
                all_slugs.add(slug)
                updated += 1

        if not dry_run:
            db.session.commit()

        print(f"\n{'DRY RUN ' if dry_run else ''}SUMMARY: {updated} slugs {'would be ' if dry_run else ''}set, "
              f"{len(articles)} articles processed")

        # Count remaining NULL/numeric slugs
        remaining = models.Article.query.filter(
            models.Article.published == True,
            db.or_(
                models.Article.slug.is_(None),
                models.Article.slug == '',
            )
        ).count()
        print(f"Published articles with NULL/empty slug remaining: {remaining}")


if __name__ == '__main__':
    main()
