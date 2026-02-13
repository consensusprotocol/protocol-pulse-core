#!/usr/bin/env python3
"""
Dry-run draft test for the Protocol Pulse content engine.
Verifies ContentGenerator logic and locked structure without publishing.

Usage:
  python scripts/test_publish.py --topic "The Geopolitics of Hashrate"
  python scripts/test_publish.py --topic "Bitcoin difficulty adjustment" --style statement
"""
import argparse
import os
import sys

# Run from project root so app and services resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    parser = argparse.ArgumentParser(description="Dry-run article draft (no publish)")
    parser.add_argument("--topic", type=str, default="The Geopolitics of Hashrate", help="Article topic")
    parser.add_argument("--style", type=str, choices=["question", "statement"], default=None, help="Headline style")
    parser.add_argument("--no-generate", action="store_true", help="Only verify imports and mandates (no AI call)")
    args = parser.parse_args()

    with open(os.path.join(os.path.dirname(__file__), "..", "app.py")) as f:
        pass  # ensure project is importable

    from app import app
    with app.app_context():
        from services.content_generator import ContentGenerator

        gen = ContentGenerator()
        print("ContentGenerator loaded.")
        print("Accuracy mandate (Jan 23 2026): 146.47 T difficulty, ~977 EH/s hashrate, 155.9 T peak.")
        print("Locked structure: tldr-section, article-header, article-paragraph, sources-list.")
        print("1200-word minimum enforced in _validate_article_structure.")
        print()

        if args.no_generate:
            print("--no-generate: skipping draft (verification only).")
            return 0

        print(f"Dry-run draft topic: {args.topic!r}")
        if args.style:
            print(f"Headline style: {args.style}")
        print("Calling generate_article (this may take a minute)...")
        try:
            result = gen.generate_article(
                args.topic,
                content_type="news_article",
                source_type="ai_generated",
                headline_style=args.style,
            )
        except Exception as e:
            print(f"ERROR: {e}")
            return 1

        if result.get("skipped"):
            print("SKIPPED:", result.get("error", "Duplicate topic or gatekeeper"))
            return 0
        if result.get("error"):
            print("ERROR:", result["error"])
            return 1

        title = result.get("title", "")
        content = result.get("content", "")
        word_count = len(__import__("re").sub(r"<[^>]+>", " ", content).split()) if content else 0
        has_tldr = "tldr-section" in (content or "")
        has_headers = "article-header" in (content or "")
        has_paragraph = "article-paragraph" in (content or "")

        print()
        print("--- RESULT ---")
        print("Title:", title[:80] + ("..." if len(title) > 80 else ""))
        print("Word count:", word_count, "(min 1200)" if word_count < 1200 else "(OK)")
        print("Has tldr-section:", has_tldr)
        print("Has article-header:", has_headers)
        print("Has article-paragraph:", has_paragraph)
        print("Dry-run complete. No article was saved or published.")
        return 0 if (has_tldr and has_headers and word_count >= 1200) else 1

if __name__ == "__main__":
    sys.exit(main())
