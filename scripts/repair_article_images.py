#!/usr/bin/env python3
"""
repair_article_images.py — Audit and repair broken article header images.

Detects: missing files, placeholder URLs, tiny/corrupt files, old Unsplash URLs.
Uses image_guard to prevent banned/duplicate/low-quality replacements.

SAFETY RULE: Never overwrite a non-missing image with a placeholder.

Usage:
    python scripts/repair_article_images.py              # Report only
    python scripts/repair_article_images.py --fix        # Fix broken paths to default
    python scripts/repair_article_images.py --regenerate # Re-generate broken images via AI
    python scripts/repair_article_images.py --regenerate --published-only  # Only fix published articles
"""

import os
import sys
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_HEADER = "/static/images/default-header.png"
OLD_UNSPLASH_DEFAULT = "https://images.unsplash.com/photo-1639762681485-074b7f938ba0"
MIN_IMAGE_SIZE_BYTES = 5000  # Images smaller than 5KB are likely broken/placeholder


def get_db_session():
    from app import app, db
    ctx = app.app_context()
    ctx.push()
    return db.session, ctx


def _classify_image(url):
    """Classify an image URL. Returns (status, reason)."""
    if not url or not url.strip():
        return "no_image", "no URL set"

    url = url.strip()

    if url == DEFAULT_HEADER:
        return "default", "using default-header.png"

    # Old Unsplash default
    if "unsplash.com" in url:
        return "broken", "old Unsplash URL (not a local file)"

    # External URLs that aren't local files
    if url.startswith("http://") or url.startswith("https://"):
        return "broken", "external URL: %s" % url[:80]

    # Local file — check existence and size
    filepath = url.lstrip("/")
    if not os.path.exists(filepath):
        return "broken", "file missing from disk"

    size = os.path.getsize(filepath)
    if size < MIN_IMAGE_SIZE_BYTES:
        return "broken", "file too small (%d bytes) — likely placeholder/corrupt" % size

    return "ok", "exists (%s bytes)" % "{:,}".format(size)


def _check_existing_image_guard(filepath):
    """Run image_guard on an existing OK file. Returns verdict or None."""
    try:
        from pp_services.articles.image_guard import check_image_bytes
        with open(filepath, "rb") as f:
            img_bytes = f.read()
        return check_image_bytes(img_bytes)
    except ImportError:
        return None
    except Exception as e:
        logger.warning("image_guard check failed for %s: %s", filepath, e)
        return None


def audit_images(session, published_only=False):
    from models import Article
    query = session.query(Article)
    if published_only:
        query = query.filter(Article.published == True)
    articles = query.all()

    results = {
        'total': len(articles),
        'ok': [],
        'default': [],
        'no_image': [],
        'broken': [],
        'banned': [],
        'duplicate': [],
    }

    for a in articles:
        status, reason = _classify_image(a.header_image_url)
        a._image_reason = reason

        # If the file exists and is OK, also run image_guard to detect banned/duplicate
        if status == "ok":
            filepath = a.header_image_url.lstrip("/")
            verdict = _check_existing_image_guard(filepath)
            if verdict is not None and not verdict.ok:
                if "banned" in verdict.reason:
                    status = "banned"
                    a._image_reason = "image_guard: %s" % verdict.reason
                elif "duplicate" in verdict.reason:
                    status = "duplicate"
                    a._image_reason = "image_guard: %s" % verdict.reason
                else:
                    status = "broken"
                    a._image_reason = "image_guard: %s" % verdict.reason

        if status in ("banned", "duplicate"):
            results[status].append(a)
        else:
            results[status].append(a)

    return results


def print_report(results):
    print("\n" + "=" * 70)
    print("ARTICLE IMAGE AUDIT REPORT")
    print("=" * 70)
    print("Total articles:      %d" % results['total'])
    print("Image OK:            %d" % len(results['ok']))
    print("Using default:       %d" % len(results['default']))
    print("No image set:        %d" % len(results['no_image']))
    print("BROKEN/PLACEHOLDER:  %d" % len(results['broken']))
    print("BANNED (by guard):   %d" % len(results.get('banned', [])))
    print("DUPLICATE (by guard):%d" % len(results.get('duplicate', [])))
    print("=" * 70)

    if results['broken']:
        print("\nBROKEN IMAGES (need repair):")
        print("-" * 70)
        for a in results['broken']:
            pub = "PUB" if a.published else "DRF"
            print("  [%s] ID %4d | %s" % (pub, a.id, a.title[:50].ljust(50)))
            print("           Reason: %s" % a._image_reason)
            if a.header_image_url:
                print("           URL: %s" % a.header_image_url[:80])
        print()

    for cat in ('banned', 'duplicate'):
        items = results.get(cat, [])
        if items:
            print("\n%s IMAGES (%d articles):" % (cat.upper(), len(items)))
            print("-" * 70)
            for a in items[:10]:
                pub = "PUB" if a.published else "DRF"
                print("  [%s] ID %4d | %s" % (pub, a.id, a.title[:50]))
                print("           Reason: %s" % a._image_reason)
            if len(items) > 10:
                print("  ... and %d more" % (len(items) - 10))
            print()

    if results['no_image']:
        print("\nNO IMAGE SET (%d articles):" % len(results['no_image']))
        print("-" * 70)
        for a in results['no_image'][:10]:
            pub = "PUB" if a.published else "DRF"
            print("  [%s] ID %4d | %s" % (pub, a.id, a.title[:60]))
        if len(results['no_image']) > 10:
            print("  ... and %d more" % (len(results['no_image']) - 10))
        print()


def fix_broken_to_default(session, results):
    """Set broken/no-image URLs to the default header.
    SAFETY: Never overwrite a non-missing image with a placeholder."""
    fixed = 0
    skipped = 0
    for a in results['broken'] + results['no_image']:
        old_url = a.header_image_url
        # Safety: if the file actually exists on disk and is a real image, do NOT overwrite
        if old_url and old_url.strip() and old_url != DEFAULT_HEADER:
            filepath = old_url.lstrip("/")
            if os.path.exists(filepath) and os.path.getsize(filepath) > MIN_IMAGE_SIZE_BYTES:
                logger.info("SKIP article %d — existing image on disk: %s", a.id, filepath)
                skipped += 1
                continue
        a.header_image_url = DEFAULT_HEADER
        logger.info("Fixed article %d: %s -> %s", a.id, old_url or '(none)', DEFAULT_HEADER)
        fixed += 1

    if fixed:
        session.commit()
        logger.info("Committed %d fixes to database (skipped %d with existing images).", fixed, skipped)
    else:
        logger.info("No broken images found — nothing to fix.")
    return fixed


def regenerate_images(session, results, published_only=False):
    """Re-generate broken/missing/banned/duplicate images via AI with image_guard checks."""
    from pp_services.image_service import generate_article_header_image

    targets = results['broken'] + results['no_image'] + results.get('banned', []) + results.get('duplicate', [])
    if published_only:
        targets = [a for a in targets if a.published]

    if not targets:
        logger.info("No articles need image regeneration.")
        return 0

    logger.info("Regenerating images for %d articles...", len(targets))

    # Counters
    fixed_ok = 0
    fixed_stock = 0
    flagged_needs_regen = 0
    banned_replaced = 0
    dup_replaced = 0

    for i, a in enumerate(targets, 1):
        reason_tag = getattr(a, '_image_reason', '')
        is_banned = 'banned' in reason_tag.lower()
        is_dup = 'duplicate' in reason_tag.lower()

        logger.info("[%d/%d] Article %d: %s", i, len(targets), a.id, a.title[:60])

        # Safety: never overwrite a non-missing image that is OK
        old_url = a.header_image_url
        if old_url and old_url != DEFAULT_HEADER and not is_banned and not is_dup:
            filepath = old_url.lstrip("/")
            if os.path.exists(filepath) and os.path.getsize(filepath) > MIN_IMAGE_SIZE_BYTES:
                logger.info("  SKIP — existing valid image on disk")
                continue

        try:
            status_out = {}  # type: dict
            new_url = generate_article_header_image(a.title, _image_status_out=status_out)
            img_status = status_out.get("image_status", "ok")
            img_phash = status_out.get("image_phash", "")

            if new_url and new_url != DEFAULT_HEADER and os.path.exists(new_url.lstrip("/")):
                a.header_image_url = new_url
                if hasattr(a, 'image_status'):
                    a.image_status = img_status
                if hasattr(a, 'image_phash'):
                    a.image_phash = img_phash
                session.commit()
                logger.info("  OK: %s", new_url)
                fixed_ok += 1
                if is_banned:
                    banned_replaced += 1
                if is_dup:
                    dup_replaced += 1
            elif img_status == "needs_regen":
                # Guard rejected all attempts — mark for future regen
                a.header_image_url = DEFAULT_HEADER
                if hasattr(a, 'image_status'):
                    a.image_status = "needs_regen"
                session.commit()
                logger.warning("  FLAGGED needs_regen: all attempts rejected by guard")
                flagged_needs_regen += 1
            else:
                logger.warning("  FAIL: generation returned %s, setting default", new_url)
                a.header_image_url = DEFAULT_HEADER
                session.commit()
                fixed_stock += 1
        except Exception as e:
            logger.error("  ERROR: %s", e)
            a.header_image_url = DEFAULT_HEADER
            session.commit()
            fixed_stock += 1

    print("\n" + "=" * 70)
    print("REPAIR SUMMARY")
    print("=" * 70)
    print("  fixed_ok:            %d" % fixed_ok)
    print("  fixed_stock:         %d" % fixed_stock)
    print("  flagged_needs_regen: %d" % flagged_needs_regen)
    print("  banned_replaced:     %d" % banned_replaced)
    print("  dup_replaced:        %d" % dup_replaced)
    print("=" * 70)

    return fixed_ok


def main():
    parser = argparse.ArgumentParser(description="Audit and repair article header images")
    parser.add_argument('--fix', action='store_true', help='Fix broken paths to default image')
    parser.add_argument('--regenerate', action='store_true', help='Re-generate broken images via AI')
    parser.add_argument('--published-only', action='store_true', help='Only process published articles')
    args = parser.parse_args()

    session, ctx = get_db_session()

    try:
        results = audit_images(session, published_only=args.published_only)
        print_report(results)

        needs_repair = (len(results['broken']) + len(results['no_image'])
                        + len(results.get('banned', [])) + len(results.get('duplicate', [])))

        if args.regenerate:
            print("\nREGENERATING %d images via AI..." % needs_repair)
            regenerate_images(session, results, published_only=args.published_only)
        elif args.fix:
            print("\nFIXING %d broken paths to default..." % needs_repair)
            fix_broken_to_default(session, results)
        else:
            if needs_repair:
                print("%d articles need image repair." % needs_repair)
                print("  --fix          Set broken paths to default image")
                print("  --regenerate   Re-generate images via AI (uses OpenAI API)")
                print("  --published-only  Only process published articles")
    finally:
        ctx.pop()


if __name__ == "__main__":
    main()
