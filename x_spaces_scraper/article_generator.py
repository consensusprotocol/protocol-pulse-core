"""
article_generator.py — Generate Protocol Pulse articles from X Space transcripts.

Uses Claude API to produce 600-800 word Bitcoin-focused articles
with title, summary, key quotes, analysis, and tags.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

ARTICLES_DIR = Path(__file__).parent / "articles"
ARTICLES_DIR.mkdir(exist_ok=True)

SYSTEM_PROMPT = """\
You are a senior journalist at Protocol Pulse, a Bitcoin-first media platform.
Your writing style is:
- Direct, informed, no-fluff — like a seasoned financial journalist
- Bitcoin-maximalist lens: evaluate everything through sound money principles
- Use "When" not "If" framing for Bitcoin adoption narratives
- Data-driven where possible, cite specific numbers from the transcript
- Never use clickbait or sensationalism — let the signal speak
- Professional tone, no emojis

Output format: JSON with these exact keys:
{
  "title": "Headline (max 100 chars, compelling but factual)",
  "summary": "2-3 sentence TL;DR for the article card",
  "content": "Full HTML article body, 600-800 words. Use <h2>, <p>, <blockquote> tags. Include 3-5 direct quotes from speakers wrapped in <blockquote>. End with analysis section.",
  "tags": ["tag1", "tag2", ...],
  "key_quotes": ["quote1 — Speaker", "quote2 — Speaker", ...],
  "seo_title": "SEO-optimized title (max 60 chars)",
  "seo_description": "Meta description (max 155 chars)"
}

Rules:
- Title should reference the Space topic, not generic "Bitcoin discussion"
- Include speaker attribution for all quotes
- Tags: always include "bitcoin" and "x-spaces", plus 2-3 topic-specific tags
- Content must be valid HTML (no markdown)
- Analysis section should connect the discussion to broader Bitcoin narratives
- If transcript is mostly noise/short, still produce a concise article but note limited content
"""


def generate_article(
    transcript: dict,
    space_meta: dict,
    model: str = "claude-sonnet-4-20250514",
) -> Optional[dict]:
    """
    Generate a PP-style article from a Space transcript.

    Args:
        transcript: dict with "text", "word_count", "duration_s", etc.
        space_meta: dict with "space_id", "title", "host", "date", "participant_count"
        model: Claude model to use

    Returns:
        Article dict ready for publishing, or None on failure.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return None

    client = anthropic.Anthropic(api_key=api_key)

    # Truncate very long transcripts to stay within context
    text = transcript.get("text", "")
    if len(text) > 50000:
        text = text[:50000] + "\n\n[... transcript truncated for length]"

    user_prompt = f"""Generate a Protocol Pulse article from this X Space transcript.

SPACE METADATA:
- Title: {space_meta.get('title', 'Untitled Space')}
- Host: @{space_meta.get('host', 'unknown')}
- Date: {space_meta.get('date', 'unknown')}
- Participants: {space_meta.get('participant_count', 'unknown')}
- Duration: {transcript.get('duration_s', 'unknown')} seconds
- Word count: {transcript.get('word_count', 0)} words

TRANSCRIPT:
{text}

Generate the article as JSON. Remember: 600-800 words, Bitcoin-first angle, 3-5 direct quotes."""

    try:
        logger.info(f"Generating article for Space '{space_meta.get('title', space_meta.get('space_id'))}'...")
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.endswith("```"):
                raw = raw[:-3]

        article = json.loads(raw)

        # Enrich with metadata
        article["space_id"] = space_meta.get("space_id", "")
        article["space_url"] = space_meta.get("url", f"https://twitter.com/i/spaces/{space_meta.get('space_id', '')}")
        article["space_host"] = space_meta.get("host", "unknown")
        article["space_date"] = space_meta.get("date", "")
        article["space_participants"] = space_meta.get("participant_count", 0)
        article["generated_at"] = datetime.utcnow().isoformat()
        article["source_type"] = "x_spaces"
        article["transcript_words"] = transcript.get("word_count", 0)

        # Save to articles dir
        filename = f"article_{space_meta.get('space_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        out_path = ARTICLES_DIR / filename
        out_path.write_text(json.dumps(article, indent=2))
        logger.info(f"Article saved: {out_path}")

        return article

    except json.JSONDecodeError as e:
        logger.error(f"Claude returned invalid JSON: {e}")
        logger.debug(f"Raw response: {raw[:500]}")
        return None
    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return None
    except Exception as e:
        logger.error(f"generate_article error: {e}")
        return None


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python article_generator.py <transcript_cache_file.json>")
        sys.exit(1)

    transcript_file = Path(sys.argv[1])
    if not transcript_file.exists():
        print(f"File not found: {transcript_file}")
        sys.exit(1)

    transcript = json.loads(transcript_file.read_text())
    meta = {
        "space_id": transcript.get("space_id", "test"),
        "title": "Test Space",
        "host": "test_user",
        "date": datetime.utcnow().isoformat(),
        "participant_count": 100,
        "url": f"https://twitter.com/i/spaces/{transcript.get('space_id', 'test')}",
    }
    article = generate_article(transcript, meta)
    if article:
        print(f"\nGenerated: {article['title']}")
        print(f"Tags: {article.get('tags', [])}")
        print(f"Summary: {article.get('summary', '')}")
    else:
        print("Article generation failed.")
