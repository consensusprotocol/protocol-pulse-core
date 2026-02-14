#!/usr/bin/env python3
"""
Delete all Article rows and any dependent rows that reference article.id.
Use when clearing stale/incorrect content (e.g. pre-halving block reward claims).
Requires --confirm to run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db
import models


def delete_all_articles(dry_run: bool = False) -> tuple[int, int]:
    """
    Delete dependent rows then all articles. Returns (dependent_deleted, articles_deleted).
    """
    with app.app_context():
        # Tables that reference article.id (must clear or delete before Article)
        # LaunchSequence, SentimentReport, SarahBrief, EmergencyFlash
        dependent_deleted = 0

        for model, attr in [
            (models.LaunchSequence, "article_id"),
            (models.SentimentReport, "article_id"),
            (models.SarahBrief, "article_id"),
            (models.EmergencyFlash, "article_id"),
        ]:
            q = db.session.query(model).filter(getattr(model, attr).isnot(None))
            count = q.count()
            if count and not dry_run:
                q.delete(synchronize_session=False)
            dependent_deleted += count

        article_count = models.Article.query.count()
        if article_count and not dry_run:
            models.Article.query.delete()
        db.session.commit()
        return dependent_deleted, article_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete all articles and dependent rows.")
    parser.add_argument("--confirm", action="store_true", help="Required to actually delete.")
    parser.add_argument("--dry-run", action="store_true", help="Only report counts, do not delete.")
    args = parser.parse_args()

    if not args.confirm and not args.dry_run:
        print("Refusing to delete without --confirm. Use --dry-run to see counts only.")
        return 1

    dep, arts = delete_all_articles(dry_run=args.dry_run)
    if args.dry_run:
        print(f"Dry run: would remove {dep} dependent row(s) and {arts} article(s).")
    else:
        print(f"Deleted {dep} dependent row(s) and {arts} article(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
