#!/usr/bin/env python3
"""
x_daily_top_article.py
Posts the top Protocol Pulse article of the day to X (Twitter).
- Picks highest read_count article published in last 24h
- Falls back to latest article if no reads yet
- Generates a 1200x675 custom X card image via Grok/DALL-E
- Posts with cypherpunk voice and article link
- Runs once daily at 14:00 ET
"""

import os, sys, re, json, logging, time, base64
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path("/home/ultron/protocol_pulse")
sys.path.insert(0, str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("x_top_article")

# X/Twitter image dimensions
X_IMAGE_WIDTH  = 1200
X_IMAGE_HEIGHT = 675

SITE_URL = "https://protocolpulse.io"


def get_top_article():
    """Get top article of the day by read_count, fallback to latest."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        from app import app
        import models
        
        with app.app_context():
            cutoff = datetime.utcnow() - timedelta(hours=24)
            
            # Try top by read_count
            article = (
                models.Article.query
                .filter(models.Article.published == True)
                .filter(models.Article.created_at >= cutoff)
                .order_by(models.Article.read_count.desc(), models.Article.created_at.desc())
                .first()
            )
            
            # Fallback to overall latest
            if not article:
                article = (
                    models.Article.query
                    .filter(models.Article.published == True)
                    .order_by(models.Article.created_at.desc())
                    .first()
                )
            
            if article:
                return {
                    "id": article.id,
                    "title": article.title,
                    "summary": article.summary or "",
                    "category": article.category or "Bitcoin",
                    "slug": article.slug or str(article.id),
                    "cover_image_url": article.cover_image_url or "",
                    "read_count": article.read_count or 0,
                }
        return None
    except Exception as e:
        logger.error(f"get_top_article failed: {e}")
        return None


def generate_x_card_image(article: dict) -> str | None:
    """
    Generate a 1200x675 X card image for the article.
    Uses Grok (xAI) image generation.
    Returns local file path or None.
    """
    try:
        import urllib.request as _req
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        
        xai_key = os.getenv("XAI_API_KEY")
        if not xai_key:
            logger.warning("XAI_API_KEY not set — skipping X card image")
            return None
        
        title = article["title"][:80]
        category = article["category"]
        
        prompt = (
            f"Professional Bitcoin intelligence media card, 1200x675 pixels. "
            f"Category: {category}. Topic: {title}. "
            f"Dark cinematic background (#0a0a0a), dramatic red accent lighting (#CC2222), "
            f"high contrast, editorial photography style, no text overlaid. "
            f"Moody, authoritative, financial news aesthetic. "
            f"Bitcoin motif subtle in background. Ultra-sharp, 4K quality."
        )
        
        payload = json.dumps({
            "model": "grok-2-image-1212",
            "prompt": prompt,
            "n": 1,
            "size": "1792x1024",  # closest to 1200x675 ratio
        }).encode()
        
        req = _req.Request(
            "https://api.x.ai/v1/images/generations",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {xai_key}"
            }
        )
        with _req.urlopen(req, timeout=30) as r:
            result = json.loads(r.read())
        
        img_url = result["data"][0].get("url")
        if not img_url:
            return None
        
        # Download the image
        out_path = BASE / "static" / "images" / "x_cards" / f"x_card_{article['id']}.jpg"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        req2 = _req.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with _req.urlopen(req2, timeout=20) as r:
            img_data = r.read()
        
        out_path.write_bytes(img_data)
        logger.info(f"X card image saved: {out_path} ({len(img_data)//1024}KB)")
        return str(out_path)
        
    except Exception as e:
        logger.warning(f"X card image generation failed: {e}")
        return None


def compose_tweet(article: dict) -> str:
    """Generate cypherpunk tweet copy for the article."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        slug = article.get("slug", str(article["id"]))
        url = f"{SITE_URL}/articles/{slug}"
        
        prompt = f"""Write a single X (Twitter) post for this Protocol Pulse article.
        
Article: {article["title"]}
Category: {article["category"]}
Summary: {article["summary"][:200]}
Link: {url}

Rules:
- Max 240 chars including the URL (URL = 23 chars)
- So max 217 chars of text
- Voice: authoritative, cypherpunk, signal-dense
- One sharp insight or provocative question
- ABSOLUTELY NO hashtags. Zero. Not #Bitcoin, not #BTC, not any. X algorithms penalize hashtags. Never use them.
- End with the URL on its own line
- No em dashes in the tweet (Twitter strips them oddly)

Return ONLY the tweet text, nothing else."""

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.8
        )
        tweet = resp.choices[0].message.content.strip()
        
        # Ensure URL is in the tweet
        if url not in tweet:
            tweet = tweet.rstrip() + f"\n{url}"
        
        return tweet[:280]
        
    except Exception as e:
        logger.error(f"Tweet composition failed: {e}")
        slug = article.get("slug", str(article["id"]))
        return f"{article['title'][:180]}\n{SITE_URL}/articles/{slug}"


def post_to_x(tweet_text: str, image_path: str = None) -> bool:
    """Post tweet via X API v2 with optional image."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        
        api_key    = os.getenv("X_API_KEY", "")
        api_secret = os.getenv("X_API_SECRET", "")
        acc_token  = os.getenv("X_ACCESS_TOKEN", "")
        acc_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "")
        
        if not all([api_key, api_secret, acc_token, acc_secret]):
            logger.error("Missing X API credentials")
            return False
        
        import tweepy
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=acc_token,
            access_token_secret=acc_secret
        )
        
        media_id = None
        if image_path and os.path.exists(image_path):
            try:
                auth = tweepy.OAuth1UserHandler(api_key, api_secret, acc_token, acc_secret)
                api_v1 = tweepy.API(auth)
                media = api_v1.media_upload(filename=image_path)
                media_id = media.media_id_string
                logger.info(f"Image uploaded: media_id={media_id}")
            except Exception as img_err:
                logger.warning(f"Image upload failed: {img_err}")
        
        kwargs = {"text": tweet_text}
        if media_id:
            kwargs["media_ids"] = [media_id]
        
        resp = client.create_tweet(**kwargs)
        tweet_id = resp.data["id"]
        logger.info(f"Tweet posted: https://x.com/ProtocolPulse/status/{tweet_id}")
        print(f"SUCCESS: https://x.com/ProtocolPulse/status/{tweet_id}")
        return True
        
    except Exception as e:
        logger.error(f"X post failed: {e}")
        return False


def _already_posted_article(article_id: int) -> bool:
    """Check if this article was already posted to X (by article_id in the log)."""
    log_path = BASE / "logs" / "x_publisher.log"
    if not log_path.exists():
        return False
    try:
        for line in log_path.read_text().strip().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("article_id") == article_id and entry.get("success"):
                    logger.info(f"Article {article_id} already posted successfully — skipping")
                    return True
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.warning(f"Could not check article post history: {e}")
    return False


def run_daily_top_article():
    """Main entry: find top article, generate image, tweet it."""
    logger.info("Starting X daily top article publisher...")

    article = get_top_article()
    if not article:
        logger.error("No article found")
        return

    logger.info(f"Top article: [{article['id']}] {article['title'][:60]} (reads: {article['read_count']})")

    # Article-level dedup: don't tweet the same article twice
    if _already_posted_article(article["id"]):
        return

    # Compose tweet
    tweet = compose_tweet(article)
    logger.info(f"Tweet ({len(tweet)} chars):\n{tweet}")

    # Global gate check — respect the unified rate limit + similarity dedup
    try:
        sys.path.insert(0, str(BASE))
        from services.x_service import can_post_tweet
        allowed, reason = can_post_tweet(tweet, source="x_daily_top_article", angle_category="institutional_flow")
        if not allowed:
            logger.warning(f"GATE BLOCKED: {reason}")
            return
    except Exception as e:
        logger.warning(f"Gate check import failed (allowing): {e}")

    # Generate X-optimized card image
    image_path = generate_x_card_image(article)

    # Post
    success = post_to_x(tweet, image_path)

    # Log result
    log_path = BASE / "logs" / "x_publisher.log"
    with open(log_path, "a") as f:
        f.write(json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "article_id": article["id"],
            "title": article["title"],
            "success": success,
            "tweet_len": len(tweet),
        }) + "\n")


# Alias for scheduler import compatibility
main = run_daily_top_article

if __name__ == "__main__":
    run_daily_top_article()
