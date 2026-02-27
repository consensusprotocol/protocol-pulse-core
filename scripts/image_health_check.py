#!/usr/bin/env python3
"""
image_health_check.py — Quick diagnostic for article image health.

Usage:
    python scripts/image_health_check.py

Checks:
  1. Default header image exists on disk
  2. static/images/headers/ directory exists and has files
  3. Published articles with broken or missing images
  4. Summary stats
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_HEADER = "/static/images/default-header.png"
HEADERS_DIR = "static/images/headers"


def check_mark(ok):
    return "PASS" if ok else "FAIL"


def main():
    print("\n" + "=" * 50)
    print("IMAGE HEALTH CHECK")
    print("=" * 50)

    issues = 0

    # Check 1: Default header exists
    default_exists = os.path.exists(DEFAULT_HEADER.lstrip("/"))
    print(f"\n[{check_mark(default_exists)}] Default header image: {DEFAULT_HEADER}")
    if not default_exists:
        print("       FIX: Place a default header image at static/images/default-header.png")
        issues += 1

    # Check 2: Headers directory
    headers_exists = os.path.isdir(HEADERS_DIR)
    if headers_exists:
        header_files = [f for f in os.listdir(HEADERS_DIR) if f.endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        print(f"[{check_mark(True)}] Headers directory: {HEADERS_DIR}/ ({len(header_files)} images)")
    else:
        print(f"[{check_mark(False)}] Headers directory: {HEADERS_DIR}/ — MISSING")
        print("       FIX: mkdir -p static/images/headers")
        header_files = []
        issues += 1

    # Check 3: Database article images
    try:
        from app import app, db
        from models import Article

        with app.app_context():
            published = Article.query.filter_by(published=True).all()
            all_articles = Article.query.all()

            broken_published = []
            broken_unpublished = []
            no_image = []

            for a in all_articles:
                url = (a.header_image_url or "").strip()
                if not url:
                    no_image.append(a)
                    continue
                if url == DEFAULT_HEADER:
                    continue
                filepath = url.lstrip("/")
                if not os.path.exists(filepath):
                    if a.published:
                        broken_published.append(a)
                    else:
                        broken_unpublished.append(a)

            pub_ok = len(broken_published) == 0
            print(f"\n[{check_mark(pub_ok)}] Published articles with broken images: {len(broken_published)}")
            if broken_published:
                for a in broken_published[:5]:
                    print(f"       ID {a.id}: {a.header_image_url}")
                if len(broken_published) > 5:
                    print(f"       ... and {len(broken_published) - 5} more")
                issues += len(broken_published)

            unp_ok = len(broken_unpublished) == 0
            print(f"[{check_mark(unp_ok)}] Unpublished articles with broken images: {len(broken_unpublished)}")
            if broken_unpublished:
                issues += len(broken_unpublished)

            print(f"\n--- Summary ---")
            print(f"Total articles:     {len(all_articles)}")
            print(f"Published:          {len(published)}")
            print(f"With images:        {len(all_articles) - len(no_image)}")
            print(f"No image set:       {len(no_image)}")
            print(f"Header files on disk: {len(header_files)}")

    except Exception as e:
        print(f"\n[FAIL] Database check: {e}")
        print("       (Run this from the project root on Replit)")
        issues += 1

    print(f"\n{'=' * 50}")
    if issues == 0:
        print("ALL CHECKS PASSED")
    else:
        print(f"{issues} ISSUE(S) FOUND — run repair_article_images.py to fix")
    print("=" * 50 + "\n")

    return 0 if issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
