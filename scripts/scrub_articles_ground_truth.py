#!/usr/bin/env python3
"""One-off scrub: set published=False for articles mentioning 6.25 BTC or under 1200 words.
Ground truth: Feb 2026, block reward is 3.125 BTC.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app, db
import models


def word_count(text: str) -> int:
    """Count words in content (strip HTML)."""
    if not text:
        return 0
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return len(clean.split())


def main() -> int:
    with app.app_context():
        articles = models.Article.query.all()
        total = len(articles)
        unpublish = 0
        for a in articles:
            content = (a.content or "") + " " + (a.title or "")
            wc = word_count(a.content or "")
            if "6.25 BTC" in content or wc < 1200:
                if a.published:
                    a.published = False
                    unpublish += 1
        db.session.commit()
        print(f"Scrubbed {total} articles: set published=False for {unpublish} (6.25 BTC or <1200 words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
