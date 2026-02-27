#!/usr/bin/env python3
"""
audit_article_images.py — Scan latest N articles, flag banned/duplicate images,
auto-replace where possible, emit summary.

Usage:
    python scripts/audit_article_images.py                   # Audit latest 50 (report only)
    python scripts/audit_article_images.py --limit 100       # Audit latest 100
    python scripts/audit_article_images.py --fix             # Auto-replace flagged images
    python scripts/audit_article_images.py --fix --limit 20  # Fix latest 20
"""

import os
import sys
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_HEADER = "/static/images/default-header.png"


def get_db_session():
    from app import app, db
    ctx = app.app_context()
    ctx.push()
    return db.session, ctx


def main():
    parser = argparse.ArgumentParser(description="Audit latest article images for banned/duplicate/quality issues")
    parser.add_argument("--limit", type=int, default=50, help="Number of latest articles to scan (default 50)")
    parser.add_argument("--fix", action="store_true", help="Auto-replace flagged images via AI regeneration")
    parser.add_argument("--published-only", action="store_true", help="Only audit published articles")
    args = parser.parse_args()

    session, ctx = get_db_session()

    try:
        from models import Article
        from services.articles.image_guard import check_image_bytes, remember_accepted

        query = Article.query
        if args.published_only:
            query = query.filter(Article.published == True)
        query = query.order_by(
            Article.published_at.desc().nullslast(),
            Article.created_at.desc()
        )
        articles = query.limit(args.limit).all()

        print("\n" + "=" * 70)
        print("IMAGE AUDIT — latest %d articles" % len(articles))
        print("=" * 70)

        ok_count = 0
        no_image_count = 0
        default_count = 0
        banned_list = []
        dup_list = []
        low_quality_list = []
        missing_list = []

        for a in articles:
            url = (a.header_image_url or "").strip()

            if not url:
                no_image_count += 1
                missing_list.append(a)
                continue

            if url == DEFAULT_HEADER:
                default_count += 1
                continue

            filepath = url.lstrip("/")
            if not os.path.exists(filepath):
                missing_list.append(a)
                continue

            # Read file and run guard
            try:
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                verdict = check_image_bytes(img_bytes, title_hint=a.title)
            except Exception as e:
                logger.warning("Could not check article %d: %s", a.id, e)
                continue

            if verdict.ok:
                ok_count += 1
                # Update phash in DB if column exists
                if hasattr(a, 'image_phash') and verdict.phash and not a.image_phash:
                    a.image_phash = verdict.phash
                    a.image_status = "ok"
            else:
                reason = verdict.reason
                if "banned" in reason:
                    banned_list.append((a, reason))
                elif "duplicate" in reason:
                    dup_list.append((a, reason))
                else:
                    low_quality_list.append((a, reason))

        # Commit any phash updates
        session.commit()

        # --- Report ---
        print("  OK (passed guard):     %d" % ok_count)
        print("  Default placeholder:   %d" % default_count)
        print("  Missing/no image:      %d" % len(missing_list))
        print("  BANNED:                %d" % len(banned_list))
        print("  DUPLICATE:             %d" % len(dup_list))
        print("  LOW QUALITY:           %d" % len(low_quality_list))
        print("=" * 70)

        if banned_list:
            print("\nBANNED images:")
            for a, reason in banned_list:
                print("  ID %4d | %s" % (a.id, a.title[:55]))
                print("           %s" % reason)

        if dup_list:
            print("\nDUPLICATE images:")
            for a, reason in dup_list:
                print("  ID %4d | %s" % (a.id, a.title[:55]))
                print("           %s" % reason)

        if low_quality_list:
            print("\nLOW QUALITY images:")
            for a, reason in low_quality_list:
                print("  ID %4d | %s" % (a.id, a.title[:55]))
                print("           %s" % reason)

        # --- Auto-fix ---
        flagged = banned_list + dup_list + low_quality_list
        if args.fix and flagged:
            print("\n--- AUTO-REPLACING %d flagged images ---" % len(flagged))
            from services.image_service import generate_article_header_image

            replaced = 0
            failed = 0
            for a, _reason in flagged:
                try:
                    status_out = {}  # type: dict
                    new_url = generate_article_header_image(a.title, _image_status_out=status_out)
                    img_status = status_out.get("image_status", "ok")
                    img_phash = status_out.get("image_phash", "")

                    if new_url and new_url != DEFAULT_HEADER:
                        a.header_image_url = new_url
                        if hasattr(a, 'image_status'):
                            a.image_status = img_status
                        if hasattr(a, 'image_phash'):
                            a.image_phash = img_phash
                        session.commit()
                        logger.info("Replaced article %d image: %s", a.id, new_url)
                        replaced += 1
                    else:
                        a.header_image_url = DEFAULT_HEADER
                        if hasattr(a, 'image_status'):
                            a.image_status = "needs_regen"
                        session.commit()
                        failed += 1
                except Exception as e:
                    logger.error("Failed to replace article %d: %s", a.id, e)
                    failed += 1

            print("  Replaced: %d" % replaced)
            print("  Failed:   %d" % failed)
        elif flagged and not args.fix:
            print("\n%d flagged images. Use --fix to auto-replace." % len(flagged))

        print("\nAudit complete.")

    finally:
        ctx.pop()


if __name__ == "__main__":
    main()
