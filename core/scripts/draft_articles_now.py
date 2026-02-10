"""
Trigger article drafting pipeline once (force, no cooldown). Generated article is published live.
Run from project root: venv/bin/python -m core.scripts.draft_articles_now
Or from core/: python scripts/draft_articles_now.py
"""
import os
import sys

if __name__ == "__main__":
    core_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    os.chdir(core_dir)

from app import app
from services.automation import generate_article_with_tracking


def main():
    with app.app_context():
        result = generate_article_with_tracking(force=True)
    if result.get("success"):
        print("OK — Article published:", result.get("title"), "| id:", result.get("article_id"))
    elif result.get("skipped"):
        print("SKIP —", result.get("message", "Cooldown or another process"))
    else:
        print("FAIL —", result.get("error", "Unknown error"))
        sys.exit(1)


if __name__ == "__main__":
    main()
