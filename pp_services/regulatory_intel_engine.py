"""
JURISDICTION REGULATORY INTELLIGENCE ENGINE — Phase 3 F2
========================================================
50-jurisdiction legislative monitoring via RSS feeds with rule-based
NLP keyword classification. 24h update latency.

Load via importlib.util — never 'from pp_services.regulatory_intel_engine import ...'
"""

import json
import logging
import time
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger("sentinel.regulatory")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# RSS feed sources
RSS_FEEDS = [
    {"url": "https://www.bis.org/rss.htm", "source": "BIS"},
    {"url": "https://www.ecb.europa.eu/rss/news.rss", "source": "ECB"},
    {"url": "https://www.federalreserve.gov/feeds/press_all.xml", "source": "Federal Reserve"},
    {"url": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml", "source": "CoinDesk"},
    {"url": "https://bitcoinmagazine.com/.rss/full/", "source": "Bitcoin Magazine"},
]

# Keyword sets for classification
HOSTILE_KEYWORDS = {
    "ban", "prohibit", "illegal", "restrict", "seize", "freeze",
    "aml", "enforcement", "crackdown", "criminal", "sanctions",
    "shutdown", "confiscate", "money laundering", "terror financing",
}
FRIENDLY_KEYWORDS = {
    "legal tender", "regulate", "approve", "license", "etf",
    "approved", "framework", "adoption", "legitimize", "integrate",
    "stablecoin regulation", "digital asset framework", "bitcoin reserve",
}
CRYPTO_FILTER = {
    "bitcoin", "crypto", "cryptocurrency", "digital currency", "cbdc",
    "digital asset", "stablecoin", "blockchain", "defi", "mining",
}

CONFIDENCE_THRESHOLD = 0.01


class RegulatoryIntelEngine:
    """Rule-based regulatory intelligence via RSS keyword classification."""

    def __init__(self):
        self._cache = []  # Recent classified articles
        self._cache_ts = 0.0
        self._review_queue_path = str(_DATA_DIR / "jurisdiction_review_queue.json")

    async def run_cycle(self, session) -> dict:
        """
        Fetch RSS feeds, classify articles, return regulatory state.

        Args:
            session: aiohttp.ClientSession

        Returns:
            dict matching SentinelState.regulatory schema
        """
        now = time.time()
        new_articles = []

        for feed in RSS_FEEDS:
            try:
                articles = await self._fetch_feed(session, feed["url"], feed["source"])
                new_articles.extend(articles)
            except Exception as e:
                logger.warning("RSS fetch failed for %s: %s", feed["source"], e)

        # Classify and filter
        classified = []
        for article in new_articles:
            result = self._classify(article)
            if result:
                classified.append(result)

        # Merge with cache, keep last 24h
        cutoff_24h = now - 86400
        self._cache = [a for a in self._cache if a.get("timestamp", 0) > cutoff_24h]
        # Deduplicate by title
        existing_titles = {a["title"] for a in self._cache}
        for c in classified:
            if c["title"] not in existing_titles:
                self._cache.append(c)
                existing_titles.add(c["title"])

        self._cache_ts = now

        # Compute threat level
        hostile_count = sum(1 for a in self._cache if a["classification"] == "HOSTILE")
        friendly_count = sum(1 for a in self._cache if a["classification"] == "FRIENDLY")

        if hostile_count >= 5:
            threat_level = "HIGH"
        elif hostile_count >= 2:
            threat_level = "MEDIUM"
        else:
            threat_level = "LOW"

        # Get jurisdiction updates
        jurisdictions = set()
        for a in self._cache:
            if a["classification"] in ("HOSTILE", "FRIENDLY"):
                jurisdictions.update(a.get("jurisdictions", []))

        # Last events
        hostile_events = [a for a in self._cache if a["classification"] == "HOSTILE"]
        friendly_events = [a for a in self._cache if a["classification"] == "FRIENDLY"]
        last_hostile = hostile_events[-1] if hostile_events else None
        last_friendly = friendly_events[-1] if friendly_events else None

        # Flag jurisdictions for review
        if hostile_events:
            self._update_review_queue(hostile_events)

        return {
            "recent_alerts": self._cache[-10:],
            "jurisdiction_updates": list(jurisdictions)[:20],
            "threat_level": threat_level,
            "last_hostile_event": last_hostile,
            "last_friendly_event": last_friendly,
            "updated_at": now,
        }

    async def _fetch_feed(self, session, url: str, source: str) -> list:
        """Fetch and parse RSS feed, return list of article dicts."""
        import aiohttp
        articles = []
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()

            root = ET.fromstring(text)
            # Handle both RSS and Atom feeds
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            items = root.findall(".//item") or root.findall(".//atom:entry", ns)
            for item in items[:20]:  # Last 20 items per feed
                title = ""
                description = ""
                link = ""
                pub_date = ""

                # RSS format
                t = item.find("title")
                if t is not None and t.text:
                    title = t.text.strip()
                d = item.find("description")
                if d is not None and d.text:
                    description = d.text.strip()
                l = item.find("link")
                if l is not None and l.text:
                    link = l.text.strip()
                p = item.find("pubDate")
                if p is not None and p.text:
                    pub_date = p.text.strip()

                # Atom format fallback
                if not title:
                    t = item.find("atom:title", ns)
                    if t is not None and t.text:
                        title = t.text.strip()

                if title:
                    articles.append({
                        "title": title,
                        "description": description[:500],
                        "link": link,
                        "source": source,
                        "pub_date": pub_date,
                        "timestamp": time.time(),
                    })
        except ET.ParseError:
            logger.warning("XML parse error for %s", url)
        except Exception as e:
            logger.warning("Feed fetch error for %s: %s", url, e)

        return articles

    def _classify(self, article: dict) -> dict:
        """Classify article as HOSTILE/FRIENDLY/NEUTRAL using keyword matching."""
        text = (article.get("title", "") + " " + article.get("description", "")).lower()
        words = text.split()
        total_words = len(words) if words else 1

        # First check if it's crypto-related
        is_crypto = any(kw in text for kw in CRYPTO_FILTER)
        if not is_crypto:
            return None

        hostile_count = sum(1 for kw in HOSTILE_KEYWORDS if kw in text)
        friendly_count = sum(1 for kw in FRIENDLY_KEYWORDS if kw in text)

        hostile_conf = hostile_count / total_words
        friendly_conf = friendly_count / total_words

        if hostile_conf > CONFIDENCE_THRESHOLD and hostile_count > friendly_count:
            classification = "HOSTILE"
            confidence = round(hostile_conf, 4)
        elif friendly_conf > CONFIDENCE_THRESHOLD and friendly_count > hostile_count:
            classification = "FRIENDLY"
            confidence = round(friendly_conf, 4)
        else:
            classification = "NEUTRAL"
            confidence = 0.0

        # Extract jurisdiction mentions
        jurisdictions = self._extract_jurisdictions(text)

        article["classification"] = classification
        article["confidence"] = confidence
        article["jurisdictions"] = jurisdictions
        return article

    def _extract_jurisdictions(self, text: str) -> list:
        """Extract country/jurisdiction mentions from text."""
        known = [
            "united states", "china", "india", "russia", "brazil", "japan",
            "south korea", "germany", "uk", "france", "nigeria", "turkey",
            "el salvador", "singapore", "hong kong", "switzerland", "canada",
            "australia", "mexico", "argentina", "indonesia", "thailand",
            "vietnam", "philippines", "pakistan", "bangladesh", "egypt",
            "south africa", "kenya", "uae", "dubai", "qatar", "bahrain",
            "european union", "eu", "sec", "cftc", "fed", "ecb", "bis",
        ]
        found = []
        for j in known:
            if j in text:
                found.append(j.title())
        return found[:5]

    def _update_review_queue(self, hostile_events: list):
        """Flag jurisdictions from hostile events for manual review."""
        try:
            queue = []
            try:
                with open(self._review_queue_path) as f:
                    queue = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            existing = {(q["jurisdiction"], q["source"]) for q in queue}
            for event in hostile_events:
                for j in event.get("jurisdictions", []):
                    key = (j, event.get("source", ""))
                    if key not in existing:
                        queue.append({
                            "jurisdiction": j,
                            "source": event.get("source"),
                            "title": event.get("title", "")[:100],
                            "flagged_at": time.time(),
                            "status": "pending_review",
                        })

            with open(self._review_queue_path, "w") as f:
                json.dump(queue[-100:], f, indent=2)
        except Exception as e:
            logger.warning("Review queue update failed: %s", e)
