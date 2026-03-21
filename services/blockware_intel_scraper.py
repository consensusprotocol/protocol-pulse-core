#!/usr/bin/env python3
"""
blockware_intel_scraper.py
Scrapes Blockware Intelligence newsletter (free tier) from their website,
extracts key insights, and spins up a Protocol Pulse article with editorial
reframing — original sourcing, original voice, no detectable scraping.
Runs daily at 09:15 ET (after morning brief).
"""

import os, sys, re, json, logging, time
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request, urllib.parse

BASE = Path("/home/ultron/protocol_pulse")
sys.path.insert(0, str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("blockware_intel")

# Blockware free newsletter URL (public)
BLOCKWARE_URLS = [
    "https://www.blockwareintelligence.com/bitcoin-mining-insights",
    "https://www.blockwareintelligence.com/macro-intelligence",
    "https://blockwareintelligence.substack.com",
]

# Paid newsletter via BeehiiV public feed if available
BLOCKWARE_FEED = "https://blockwareintelligence.beehiiv.com/feed"

def fetch_latest_blockware():
    """Fetch latest Blockware content from public sources."""
    content_items = []
    
    # Try RSS/feed first
    for feed_url in [BLOCKWARE_FEED]:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            # Parse RSS items
            items = re.findall(r"<item>(.*?)</item>", raw, re.DOTALL)
            for item in items[:3]:
                title = re.search(r"<title><!\[CDATA\[(.*?)\]\]>", item) or re.search(r"<title>(.*?)</title>", item)
                desc = re.search(r"<description><!\[CDATA\[(.*?)\]\]>", item) or re.search(r"<description>(.*?)</description>", item)
                link = re.search(r"<link>(.*?)</link>", item)
                pub = re.search(r"<pubDate>(.*?)</pubDate>", item)
                if title:
                    content_items.append({
                        "title": title.group(1).strip(),
                        "description": re.sub(r"<[^>]+>", "", desc.group(1)).strip()[:1000] if desc else "",
                        "url": link.group(1).strip() if link else feed_url,
                        "date": pub.group(1).strip() if pub else "",
                        "source": "Blockware Intelligence"
                    })
            if content_items:
                logger.info(f"Fetched {len(content_items)} items from {feed_url}")
                break
        except Exception as e:
            logger.warning(f"Feed {feed_url}: {e}")
    
    # Fallback: scrape public website
    if not content_items:
        for url in BLOCKWARE_URLS:
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                })
                with urllib.request.urlopen(req, timeout=10) as r:
                    html = r.read().decode("utf-8", errors="ignore")
                
                # Extract article titles and snippets
                h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.DOTALL | re.IGNORECASE)
                h3s = re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.DOTALL | re.IGNORECASE)
                paras = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
                
                clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
                headlines = [clean(h) for h in (h2s + h3s) if len(clean(h)) > 20][:5]
                snippets = [clean(p) for p in paras if len(clean(p)) > 60][:8]
                
                if headlines:
                    content_items.append({
                        "title": headlines[0] if headlines else "Blockware Intelligence: Weekly Bitcoin Mining & Macro Update",
                        "description": " ".join(snippets[:3]),
                        "url": url,
                        "date": datetime.utcnow().isoformat(),
                        "source": "Blockware Intelligence"
                    })
                    break
            except Exception as e:
                logger.warning(f"Scrape {url}: {e}")
    
    return content_items


def generate_blockware_article(item: dict) -> dict | None:
    """Use LLM to reframe Blockware intel into Protocol Pulse article."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""You are Al Ingle, senior editor at Protocol Pulse. You have received raw intelligence from a mining and macro research source. Your job is to synthesize this into a Protocol Pulse article — adding your own analysis, Bitcoin-native context, and editorial perspective.

SOURCE INTELLIGENCE:
Headline: {item["title"]}
Content: {item["description"][:800]}
Source: {item["source"]}
Date: {item["date"]}

Write a Protocol Pulse Intel article that:
1. Uses the raw data as a jumping-off point — do not repeat it verbatim
2. Adds analysis that a sovereign Bitcoin holder would find valuable
3. Connects the data to broader macro/monetary context
4. Has a cypherpunk edge — what does this mean for financial sovereignty?
5. Cites the source properly at the end

Voice: Matt Taibbi's edge + Lyn Alden's precision.

FORMAT:
<h1 class="article-header">[Sharp headline — not a copy of source headline]</h1>
<div class="tldr-section"><em><strong>TL;DR: [2 sentences]</strong></em></div>
<p class="article-paragraph">[Hook]</p>
<p class="article-paragraph">[The data/facts — reframed]</p>
<p class="article-paragraph">[Analysis paragraph 1]</p>
<p class="article-paragraph">[Analysis paragraph 2 with <strong>one shareable line</strong>]</p>
<p class="article-paragraph">[Bitcoin/sovereignty angle]</p>
<p class="article-paragraph">[Close]</p>
<h2 class="article-header">Source Intelligence</h2>
<ul class="sources-list"><li><a href="{item["url"]}">{item["source"]}</a></li></ul>

350-450 words. Clean HTML only."""

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        content = resp.choices[0].message.content
        
        import re as _re
        title_m = _re.search(r"<h1[^>]*>([^<]+)</h1>", content)
        tldr_m = _re.search(r"TL;DR:\s*([^<]+)", content)
        
        return {
            "title": title_m.group(1).strip() if title_m else item["title"],
            "content": content,
            "summary": tldr_m.group(1).strip()[:280] if tldr_m else item["description"][:200],
            "category": "Mining Intel",
            "source_url": item["url"],
            "source_type": "intel_synthesis",
        }
    except Exception as e:
        logger.error(f"Article generation failed: {e}")
        return None


def publish_blockware_article():
    """Main entry point — scrape, generate, publish."""
    logger.info("Starting Blockware Intel scraper...")
    
    items = fetch_latest_blockware()
    if not items:
        logger.warning("No Blockware content found")
        return
    
    item = items[0]
    logger.info(f"Processing: {item['title'][:60]}")
    
    article_data = generate_blockware_article(item)
    if not article_data:
        return
    
    # Publish via Flask app context
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        from app import app, db
        import models
        
        with app.app_context():
            # Deduplicate — don't publish if same source URL published in last 48h
            cutoff = datetime.utcnow() - timedelta(hours=48)
            existing = models.Article.query.filter(
                models.Article.source_url == item["url"],
                models.Article.created_at >= cutoff
            ).first()
            if existing:
                logger.info(f"Already published from this source: {existing.id}")
                return
            
            article = models.Article(
                title=article_data["title"],
                content=article_data["content"],
                summary=article_data["summary"],
                category=article_data["category"],
                source_url=article_data["source_url"],
                source_type=article_data["source_type"],
                author="Al Ingle",
                published=True,
            )
            db.session.add(article)
            db.session.flush()
            article.slug = models.Article.make_slug(article.title, article.id)
            db.session.commit()
            logger.info(f"Published article {article.id}: {article.title[:60]}")
            print(f"SUCCESS: [{article.id}] {article.title}")
    except Exception as e:
        logger.error(f"Publish failed: {e}")


if __name__ == "__main__":
    publish_blockware_article()
