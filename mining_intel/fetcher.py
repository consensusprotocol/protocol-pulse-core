"""
Multi-Source Mining Intel Fetcher
==================================
Fetches RSS from Blockware Intelligence, Hashrate Index, and Compass Mining.
Filters for posts from the last 7 days, deduplicates via URL cache.
"""

import json
import logging
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
PROCESSED_URLS_FILE = CACHE_DIR / "processed_urls.json"

RSS_SOURCES = [
    {
        "name": "Blockware Intelligence",
        "url": "https://blockwareintelligence.substack.com/feed",
        "slug": "blockware",
    },
    {
        "name": "Hashrate Index",
        "url": "https://hashrateindex.com/blog/feed",
        "slug": "hashrate_index",
    },
    {
        "name": "Compass Mining",
        "url": "https://compassmining.io/education/feed",
        "slug": "compass_mining",
    },
]

HEADERS = {
    "User-Agent": "ProtocolPulse/1.0 (mining intel aggregator)"
}


def _load_processed_urls() -> dict:
    """Load the processed URLs cache. Returns {url: iso_datetime_processed}."""
    if PROCESSED_URLS_FILE.exists():
        try:
            return json.loads(PROCESSED_URLS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_processed_urls(cache: dict):
    PROCESSED_URLS_FILE.write_text(json.dumps(cache, indent=2))


def _parse_pub_date(entry) -> datetime | None:
    """Extract publication date from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass
    # Fallback: try parsing published string
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(raw).replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _extract_summary(entry) -> str:
    """Extract a clean text summary from a feed entry."""
    # Try content first, then summary
    raw = ""
    if hasattr(entry, "content") and entry.content:
        raw = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        raw = entry.summary or ""
    if raw:
        soup = BeautifulSoup(raw, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        return text[:500]
    return ""


def fetch_rss_source(source: dict, cutoff: datetime) -> list[dict]:
    """
    Fetch and parse a single RSS source.
    Returns list of post dicts newer than cutoff.
    """
    name = source["name"]
    url = source["url"]
    posts = []

    try:
        logger.info(f"Fetching RSS: {name} ({url})")
        feed = feedparser.parse(url, request_headers=HEADERS)

        if feed.bozo and not feed.entries:
            logger.warning(f"Feed parse error for {name}: {feed.bozo_exception}")
            return []

        for entry in feed.entries:
            pub_date = _parse_pub_date(entry)
            if not pub_date:
                continue
            if pub_date < cutoff:
                continue

            link = entry.get("link", "")
            if not link:
                continue

            author = entry.get("author", "")
            if not author and hasattr(entry, "authors") and entry.authors:
                author = entry.authors[0].get("name", "")

            posts.append({
                "title": entry.get("title", "Untitled"),
                "url": link,
                "summary": _extract_summary(entry),
                "published_date": pub_date.isoformat(),
                "author": author,
                "source_name": name,
                "source_slug": source["slug"],
            })

        logger.info(f"  {name}: {len(posts)} posts in last 7 days (of {len(feed.entries)} total)")

    except Exception as e:
        logger.error(f"Error fetching {name}: {e}")

    return posts


def scrape_article_text(url: str, max_chars: int = 12000) -> str:
    """
    Scrape the full article text from a URL using requests + BeautifulSoup.
    Returns clean text content, truncated to max_chars.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Remove script, style, nav, footer elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Try article-specific selectors first
        article = (
            soup.find("article")
            or soup.find("div", class_="post-content")
            or soup.find("div", class_="entry-content")
            or soup.find("div", class_="blog-content")
            or soup.find("main")
        )

        if article:
            text = article.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        text = "\n".join(lines)

        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [truncated]"

        return text

    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return ""


def fetch_all(days: int = 7) -> list[dict]:
    """
    Fetch posts from all RSS sources within the last N days.
    Skips already-processed URLs.
    Returns list of post dicts with scraped content.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    processed = _load_processed_urls()
    all_posts = []

    for source in RSS_SOURCES:
        posts = fetch_rss_source(source, cutoff)
        for post in posts:
            if post["url"] in processed:
                logger.debug(f"  Skipping (already processed): {post['title'][:60]}")
                continue
            all_posts.append(post)

    logger.info(f"Total new posts across all sources: {len(all_posts)}")

    # Scrape full text for each new post
    for post in all_posts:
        logger.info(f"  Scraping: {post['title'][:60]}...")
        post["full_text"] = scrape_article_text(post["url"])
        word_count = len(post["full_text"].split()) if post["full_text"] else 0
        post["word_count"] = word_count
        logger.info(f"    Scraped {word_count} words")

    return all_posts


def mark_processed(urls: list[str]):
    """Mark URLs as processed in the cache."""
    cache = _load_processed_urls()
    now = datetime.now(timezone.utc).isoformat()
    for url in urls:
        cache[url] = now
    _save_processed_urls(cache)
    logger.info(f"Marked {len(urls)} URLs as processed (total cached: {len(cache)})")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    posts = fetch_all()
    for p in posts:
        print(f"[{p['source_name']}] {p['title']} ({p['published_date'][:10]})")
        print(f"  URL: {p['url']}")
        print(f"  Words: {p.get('word_count', 0)}")
        print()
