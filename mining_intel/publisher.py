"""
Publisher — Article Publisher via Replit Relay
===============================================
Publishes Mining Intel articles to Protocol Pulse database
using the same mechanism as existing article pipelines.
Includes Grok fact-checking gate and Pexels cover image.
"""

import json
import logging
import requests
import re
from datetime import datetime, timezone

from relay import get_key, run as relay_run, query_db

logger = logging.getLogger(__name__)


def fetch_pexels_cover(query: str) -> str | None:
    """Fetch a cover image from Pexels API."""
    api_key = get_key("PEXELS_API_KEY")
    if not api_key:
        logger.warning("PEXELS_API_KEY not available — using fallback image")
        return "https://images.pexels.com/photos/844124/pexels-photo-844124.jpeg?auto=compress&cs=tinysrgb&h=650&w=940"

    try:
        r = requests.get(
            f"https://api.pexels.com/v1/search?query={query}&per_page=5&orientation=landscape",
            headers={"Authorization": api_key},
            timeout=10
        )
        photos = r.json().get("photos", [])
        if photos:
            # Pick a random-ish photo to avoid always using the same one
            import hashlib
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            idx = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(photos)
            return photos[idx]["src"]["large"]
    except Exception as e:
        logger.warning(f"Pexels fetch failed: {e}")

    return "https://images.pexels.com/photos/844124/pexels-photo-844124.jpeg?auto=compress&cs=tinysrgb&h=650&w=940"


def fact_check_with_grok(article: dict) -> dict:
    """
    Run the article through Grok fact-checking gate.
    Same pattern as GrokReviewService in services/grok_review_service.py.
    Returns article dict with fact_check_result added.
    """
    api_key = get_key("XAI_API_KEY")
    if not api_key:
        logger.warning("XAI_API_KEY not available — skipping Grok fact-check")
        article["fact_check_result"] = {
            "approved": False,
            "decision": "SKIP",
            "score": 0,
            "reason": "Grok not configured"
        }
        return article

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

        title = article.get("title", "")
        content = article.get("body_html", "")[:8000]

        prompt = f"""You are the FINAL EDITORIAL GATE at Protocol Pulse, a Bitcoin intelligence publication.
Fact-check this Mining Intel article using your REAL-TIME knowledge.

TODAY'S DATE: {datetime.now(timezone.utc).strftime('%B %d, %Y')}

=== ARTICLE TO REVIEW ===
TITLE: {title}
CATEGORY: Mining Intel

CONTENT:
{content}

=== FACT-CHECK REQUIREMENTS ===
1. Are mining metrics (hashrate, difficulty, fees) in the right ballpark for today?
2. Are any claims about miners, pools, or network events verifiable?
3. Does the article fabricate specific numbers not from cited sources?
4. Is the headline accurate?

IMPORTANT: This article uses data from mempool.space and Blockware Intelligence.
Trust cited source data. Only reject if the article adds FALSE information.

Respond in JSON:
{{
    "approved": true or false,
    "score": 0-100 (below 70 = reject),
    "critical_errors": ["list of fabricated or wrong claims"],
    "issues": ["concerns or inaccuracies"],
    "suggestions": ["improvements"],
    "fact_check_notes": "detailed findings",
    "revised_title": "corrected title or null"
}}"""

        response = client.chat.completions.create(
            model="grok-3-latest",
            messages=[
                {"role": "system", "content": "You are a Bitcoin mining fact-checker for Protocol Pulse. Today is March 2026. Respond only in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2500
        )

        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        result.setdefault("approved", result.get("score", 0) >= 70)
        result.setdefault("critical_errors", [])

        if result.get("critical_errors"):
            result["approved"] = False

        result["decision"] = "APPROVE" if result["approved"] else "REJECT"

        # Apply revised title if provided
        if result.get("revised_title") and not result["approved"]:
            logger.info(f"Grok suggests revised title: {result['revised_title']}")

        article["fact_check_result"] = result
        logger.info(f"Grok review: score={result.get('score')}, decision={result['decision']}")

        if result.get("critical_errors"):
            for err in result["critical_errors"]:
                logger.warning(f"  CRITICAL: {err}")

        return article

    except Exception as e:
        logger.error(f"Grok fact-check error: {e}")
        article["fact_check_result"] = {
            "approved": False,
            "decision": "ERROR",
            "score": 0,
            "reason": str(e)
        }
        return article


def check_duplicate(title: str) -> bool:
    """Check if a similar article already exists in the last 10 published."""
    try:
        result = query_db(
            "SELECT title FROM articles WHERE published=1 ORDER BY id DESC LIMIT 10"
        )
        if not result:
            return False

        recent = json.loads(result)
        title_lower = title.lower()
        for row in recent:
            existing = row.get("title", "").lower()
            # Simple keyword overlap check
            title_words = set(re.findall(r'\w+', title_lower))
            existing_words = set(re.findall(r'\w+', existing))
            if len(title_words) > 0:
                overlap = len(title_words & existing_words) / len(title_words)
                if overlap > 0.6:
                    logger.warning(f"Potential duplicate: '{title}' vs '{existing}' (overlap: {overlap:.0%})")
                    return True
        return False
    except Exception as e:
        logger.warning(f"Duplicate check failed: {e}")
        return False


def publish_article(article: dict) -> dict:
    """
    Publish article to Protocol Pulse database via Replit relay.
    Matches the Article model schema exactly.
    """
    title = article.get("title", "").replace("'", "''")
    content = article.get("body_html", "").replace("'", "''")
    summary = article.get("subtitle", "").replace("'", "''")
    category = article.get("category", "Mining Intel")
    tags = ",".join(article.get("tags", ["mining"]))
    cover_url = article.get("cover_image_url", "").replace("'", "''")
    seo_title = article.get("seo_title", title[:60]).replace("'", "''")
    seo_desc = article.get("seo_description", summary[:155]).replace("'", "''")
    sources = article.get("sources", [])
    source_attr = ", ".join(sources) if sources else "mempool.space"
    author = "Protocol Pulse Intelligence"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    sql = f"""INSERT INTO articles (title, content, summary, author, category, tags,
        source_type, published, published_at, created_at, updated_at,
        cover_image_url, seo_title, seo_description)
    VALUES ('{title}', '{content}', '{summary}', '{author}', '{category}', '{tags}',
        'mining_intel', 1, '{now}', '{now}', '{now}',
        '{cover_url}', '{seo_title}', '{seo_desc}')"""

    try:
        # Use a Python script approach for complex SQL to avoid escaping issues
        import base64
        script = f"""
import json, sys
sys.path.insert(0, '.')
from app import db
from models import Article
from datetime import datetime

a = Article(
    title={json.dumps(article.get('title', ''))},
    content={json.dumps(article.get('body_html', ''))},
    summary={json.dumps(article.get('subtitle', ''))},
    author="Protocol Pulse Intelligence",
    category="Mining Intel",
    tags={json.dumps(tags)},
    source_type="mining_intel",
    published=True,
    published_at=datetime.utcnow(),
    cover_image_url={json.dumps(article.get('cover_image_url', ''))},
    seo_title={json.dumps(seo_title.replace("''", "'"))},
    seo_description={json.dumps(seo_desc.replace("''", "'"))}
)
db.session.add(a)
db.session.commit()
print(json.dumps({{"id": a.id, "title": a.title, "published": True}}))
"""
        script_b64 = base64.b64encode(script.encode()).decode()
        cmd = f"python3 -c \"import base64;exec(base64.b64decode('{script_b64}').decode())\""
        result = relay_run(cmd, timeout=30)

        if result:
            try:
                pub_result = json.loads(result)
                logger.info(f"Published article #{pub_result.get('id')}: {pub_result.get('title')}")
                return {"success": True, "article_id": pub_result.get("id"), "result": pub_result}
            except json.JSONDecodeError:
                if "OK" in result or result.strip():
                    logger.info(f"Article published (raw result: {result[:100]})")
                    return {"success": True, "result": result}

        logger.error(f"Publish failed — relay returned: {result}")
        return {"success": False, "error": result or "Empty relay response"}

    except Exception as e:
        logger.error(f"Publish error: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    print("Publisher module loaded. Use publish_article(article_dict) to publish.")
