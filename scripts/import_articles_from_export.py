#!/usr/bin/env python3
"""
One-time import: load articles/all_articles_export.json into the Article table.
Run from repo root: python scripts/import_articles_from_export.py
"""
import json
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

def parse_dt(s):
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    s = str(s).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:26], fmt)
        except ValueError:
            continue
    return None

def main():
    export_path = REPO_ROOT / "articles" / "all_articles_export.json"
    if not export_path.exists():
        print("Missing", export_path)
        return 1
    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    articles_data = data.get("articles", [])
    if not articles_data:
        print("No 'articles' key or empty list")
        return 1

    from app import app, db
    import models

    with app.app_context():
        created = 0
        skipped = 0
        total = len(articles_data)
        for a in articles_data:
            try:
                created_at = parse_dt(a.get("created_at"))
                updated_at = parse_dt(a.get("updated_at"))
                title = (a.get("title") or "")[:200]
                content = a.get("content") or ""
                if not title:
                    continue
                # Skip if already exists (prefer id match; then title match)
                existing = None
                if a.get("id"):
                    existing = models.Article.query.get(a.get("id"))
                if not existing:
                    existing = models.Article.query.filter_by(title=title).first()
                if existing:
                    skipped += 1
                    continue
                art = models.Article(
                    id=a.get("id"),
                    title=title,
                    content=content,
                    summary=(a.get("summary") or "")[:5000] or None,
                    author=(a.get("author") or "Protocol Pulse AI")[:100],
                    category=(a.get("category") or "Web3")[:50],
                    tags=(a.get("tags") or "")[:500] or None,
                    source_url=(a.get("source_url") or "")[:500] or None,
                    source_type=(a.get("source_type") or "")[:50] or None,
                    featured=bool(a.get("featured")),
                    published=bool(a.get("published", True)),
                    created_at=created_at,
                    updated_at=updated_at,
                    seo_title=(a.get("seo_title") or "")[:200] or None,
                    seo_description=(a.get("seo_description") or "")[:300] or None,
                    substack_url=(a.get("substack_url") or "")[:500] or None,
                    header_image_url=(a.get("header_image_url") or "")[:500] or None,
                    video_url=(a.get("video_url") or "")[:500] or None,
                )
                db.session.add(art)
                created += 1
            except Exception as e:
                print("Skip article id", a.get("id"), e)
                db.session.rollback()
                continue
            if (created % 100) == 0:
                db.session.commit()
                print(f"Imported {created}/{total} (skipped {skipped})...")
        db.session.commit()
        # SQLite: ensure sequence is past max id so future inserts don't conflict
        if created > 0:
            max_id = max(a.get("id", 0) for a in articles_data)
            try:
                from sqlalchemy import text
                db.session.execute(text("UPDATE sqlite_sequence SET seq = :n WHERE name = 'article'"), {"n": max_id})
                db.session.commit()
            except Exception:
                pass
        print(f"DONE: Imported {created} articles, skipped {skipped} (already exist).")
    return 0

if __name__ == "__main__":
    sys.exit(main())
