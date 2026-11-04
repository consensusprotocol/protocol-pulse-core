#!/usr/bin/env python3
"""
backfill_slugs.py — Set a unique slug on every published article with slug=NULL/empty/numeric.

Uses direct sqlite3 (not Flask ORM) to guarantee atomic persistence.
Slug rules: slugify(title), max 80 chars, dedupe with -2/-3, empty title → brief-{id}.

Usage:
    python3 scripts/backfill_slugs.py                          # run against production DB
    python3 scripts/backfill_slugs.py --dry-run                # preview only
    python3 scripts/backfill_slugs.py --db /path/to/db.db      # custom DB path
"""
import os, sys, re, sqlite3, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_DEFAULT = os.path.expanduser("~/protocol_pulse/instance/protocol_pulse.db")


def slugify(title, max_len=80):
    s = re.sub(r'[^\w\s-]', '', (title or '').lower())
    s = re.sub(r'[-\s]+', '-', s).strip('-')
    return s[:max_len] if s else ''


def main():
    dry_run = '--dry-run' in sys.argv
    db_path = DB_DEFAULT
    for i, arg in enumerate(sys.argv):
        if arg == '--db' and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]

    if not os.path.exists(db_path):
        print(f"ERROR: DB not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Load existing slugs
    c.execute("SELECT slug FROM articles WHERE slug IS NOT NULL AND slug != ''")
    all_slugs = {r['slug'] for r in c.fetchall()}

    # Find articles needing slugs
    c.execute("""
        SELECT id, title, slug FROM articles
        WHERE published = 1
        AND (slug IS NULL OR slug = '')
        ORDER BY id
    """)
    null_empty = [(r['id'], r['title'], r['slug']) for r in c.fetchall()]

    # Also find numeric-only slugs
    c.execute("""
        SELECT id, title, slug FROM articles
        WHERE published = 1
        AND slug IS NOT NULL AND slug != ''
    """)
    numeric = [(r['id'], r['title'], r['slug']) for r in c.fetchall()
               if r['slug'] and r['slug'].isdigit()]

    articles = null_empty + numeric
    logger.info("Found %d articles needing slugs (dry_run=%s)", len(articles), dry_run)

    updated = 0
    for aid, title, old_slug in articles:
        slug = slugify(title)
        if not slug or slug.isdigit():
            slug = f"brief-{aid}"

        base = slug
        counter = 2
        while slug in all_slugs:
            slug = f"{base}-{counter}"
            counter += 1

        if dry_run:
            logger.info("[DRY] ID %d: slug='%s' (title: %s)", aid, slug, (title or '')[:50])
        else:
            c.execute("UPDATE articles SET slug = ? WHERE id = ?", (slug, aid))
            all_slugs.add(slug)
            updated += 1

    if not dry_run:
        conn.commit()

    # Final count
    c.execute("""
        SELECT COUNT(*) as cnt FROM articles
        WHERE published = 1 AND (slug IS NULL OR slug = '')
    """)
    remaining = c.fetchone()['cnt']

    conn.close()
    print(f"\n{'DRY RUN ' if dry_run else ''}SUMMARY: {updated} slugs set, {len(articles)} processed")
    print(f"Published articles with NULL/empty slug remaining: {remaining}")


if __name__ == '__main__':
    main()
