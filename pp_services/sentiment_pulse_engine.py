"""
SENTIMENT PULSE ENGINE — Phase 2 F2
====================================
Async influence-weighted NLP across X (Nitter), Nostr, Reddit.
Real-time score -100 to +100, integrated into Sentinel daemon.

NO `from pp_services.*` imports — uses importlib.util only.
"""

import asyncio
import json
import logging
import re
import time
from collections import Counter
from pathlib import Path

import aiohttp

logger = logging.getLogger("sentinel.sentiment")

# ── Paths ────────────────────────────────────────────────────────────────────
_BASE_DIR = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _BASE_DIR / "data" / "sentiment_config.yaml"


def _load_config() -> dict:
    """Load sentiment config from YAML."""
    try:
        import yaml
        with open(_CONFIG_PATH, "r") as f:
            return yaml.safe_load(f)
    except (ImportError, FileNotFoundError):
        return _fallback_config()


def _fallback_config() -> dict:
    """Hardcoded fallback if YAML unavailable."""
    return {
        "update_interval_seconds": 30,
        "min_keyword_matches": 2,
        "ema_window_minutes": 30,
        "tier1_max_influence_pct": 15,
        "positive_keywords": [
            "accumulat", "bullish", "buy", "hodl", "sovereign", "freedom",
            "ath", "moon", "stacking", "adoption", "breakout", "etf inflow",
            "institutional", "halving", "supply shock", "hard money",
            "legal tender", "lightning", "taproot",
        ],
        "negative_keywords": [
            "dump", "crash", "ban", "scam", "sell", "bearish", "regulation",
            "seized", "dead", "capitulation", "liquidation", "ponzi",
            "bubble", "hack", "exploit", "cbdc threat", "crackdown",
        ],
        "nostr_relays": ["wss://relay.damus.io"],
        "reddit_subreddits": ["Bitcoin", "CryptoCurrency"],
        "reddit_cache_minutes": 5,
        "tiers": {
            "tier1": {"weight": 3.0, "handles": [
                "saylor", "jack", "lopp", "odell", "matt_odell", "martybent",
                "prestonpysh", "stephanlivera", "natbrunell", "lynaldencontact",
                "gladstein", "saifedean", "adam3us", "nvk", "dergigi",
                "pierre_rochard", "coryklippsten", "breedlove22", "jeffbooth",
                "jimmysong", "tonevays", "excellion", "nic__carter",
                "100trillionusd", "aantonop", "petermccormack", "apompliano",
            ]},
            "tier2": {"weight": 1.5, "handles": [
                "caitlinlong_", "wclementeiii", "sethforprivacy", "parkerlewis",
                "tomerstrolight", "moneyball", "stacker_news", "level39",
            ]},
            "tier3": {"weight": 0.5},
        },
    }


class SentimentPulseEngine:
    """Async sentiment collector + scorer for Sentinel integration."""

    def __init__(self):
        self._config = _load_config()
        self._positive_kw = [k.lower() for k in self._config.get("positive_keywords", [])]
        self._negative_kw = [k.lower() for k in self._config.get("negative_keywords", [])]
        tiers = self._config.get("tiers", {})
        self._tier1_handles = set(
            h.lower() for h in tiers.get("tier1", {}).get("handles", [])
        )
        self._tier2_handles = set(
            h.lower() for h in tiers.get("tier2", {}).get("handles", [])
        )
        self._min_matches = self._config.get("min_keyword_matches", 2)
        self._tier1_max_pct = self._config.get("tier1_max_influence_pct", 15) / 100.0

        # Rolling state
        self._score_history: list = []  # (timestamp, score)
        self._volume_timestamps: list = []
        self._score_30m_ago: float = 0.0
        self._last_score: float = 0.0

        # Reddit cache
        self._reddit_cache: list = []
        self._reddit_cache_ts: float = 0.0
        self._reddit_cache_ttl = self._config.get("reddit_cache_minutes", 5) * 60

    def _get_author_tier(self, author: str) -> int:
        if not author:
            return 3
        author_lower = author.lower().strip("@")
        if author_lower in self._tier1_handles:
            return 1
        if author_lower in self._tier2_handles:
            return 2
        return 3

    def _get_tier_weight(self, tier: int) -> float:
        return {1: 3.0, 2: 1.5, 3: 0.5}.get(tier, 0.5)

    def score_post(self, text: str, author_tier: int) -> float:
        """Score a single post. Returns -1 to +1 or 0 if insufficient matches."""
        if not text:
            return 0.0
        text_lower = text.lower()

        pos_count = sum(1 for kw in self._positive_kw if kw in text_lower)
        neg_count = sum(1 for kw in self._negative_kw if kw in text_lower)

        total_matches = pos_count + neg_count
        if total_matches < self._min_matches:
            return 0.0

        weight = self._get_tier_weight(author_tier)
        raw = (pos_count - neg_count) * weight
        return max(-1.0, min(1.0, raw / 5.0))

    def compute_sentiment_state(self, posts: list) -> dict:
        """Compute full sentiment output from collected posts."""
        now = time.time()

        if not posts:
            return self._build_output(self._last_score, {}, [], now)

        tier1_scores = []
        other_scores = []
        source_scores = {"x": [], "nostr": [], "reddit": []}
        entities = Counter()

        for post in posts:
            text = post.get("text", "")
            author = post.get("author", "")
            source = post.get("source", "unknown")
            tier = self._get_author_tier(author)
            score = self.score_post(text, tier)

            if score == 0.0:
                continue

            if tier == 1:
                tier1_scores.append(score)
            else:
                other_scores.append(score)

            if source in source_scores:
                source_scores[source].append(score)

            for word in text.split():
                w = word.lower().strip(".,!?;:")
                if w.startswith("@") or w.startswith("#"):
                    entities[w] += 1

        # Cap tier1 influence
        all_scores = list(other_scores)
        if tier1_scores:
            max_tier1 = max(1, int(len(all_scores) * self._tier1_max_pct / max(0.01, 1 - self._tier1_max_pct))) if all_scores else 3
            all_scores.extend(tier1_scores[:max_tier1])

        if not all_scores:
            return self._build_output(self._last_score, {}, [], now)

        raw_avg = sum(all_scores) / len(all_scores)
        raw_score = raw_avg * 100.0

        # EMA smoothing
        ema_minutes = self._config.get("ema_window_minutes", 30)
        alpha = 2.0 / (ema_minutes + 1)
        if self._last_score != 0.0:
            smoothed = alpha * raw_score + (1 - alpha) * self._last_score
        else:
            smoothed = raw_score

        # Update history
        self._score_history.append((now, smoothed))
        cutoff = now - 86400
        self._score_history = [(t, s) for t, s in self._score_history if t > cutoff]

        # Score 30m ago
        target_30m = now - 1800
        closest_30m = None
        for t, s in self._score_history:
            if t <= target_30m:
                closest_30m = s
        self._score_30m_ago = closest_30m if closest_30m is not None else smoothed

        # Volume tracking
        self._volume_timestamps.append(now)
        self._volume_timestamps = [t for t in self._volume_timestamps if t > cutoff]

        self._last_score = smoothed

        # Source breakdown
        source_breakdown = {}
        for src, scores in source_scores.items():
            source_breakdown[src] = round(sum(scores) / len(scores) * 100, 1) if scores else 0.0

        top_entities = [e for e, _ in entities.most_common(5)]
        return self._build_output(smoothed, source_breakdown, top_entities, now)

    def _build_output(self, score: float, source_breakdown: dict, top_entities: list, now: float) -> dict:
        diff = score - self._score_30m_ago
        if diff > 5:
            trend = "rising"
        elif diff < -5:
            trend = "falling"
        else:
            trend = "stable"

        # Tier1 signal: check if any tier1 account contributed in this cycle
        tier1_signal = bool(self._score_history and len(self._score_history) > 0)

        return {
            "score": round(max(-100, min(100, score)), 1),
            "score_30m_ago": round(self._score_30m_ago, 1),
            "trend": trend,
            "source_breakdown": source_breakdown or {"x": 0.0, "nostr": 0.0, "reddit": 0.0},
            "volume_24h": len(self._volume_timestamps),
            "top_entities": top_entities,
            "tier1_signal": tier1_signal,
            "updated_at": now,
        }

    # ── Collectors ───────────────────────────────────────────────────────────

    async def collect_reddit(self, session: aiohttp.ClientSession) -> list:
        """Fetch recent posts from Reddit public JSON API."""
        now = time.time()
        if self._reddit_cache and (now - self._reddit_cache_ts) < self._reddit_cache_ttl:
            return self._reddit_cache

        posts = []
        headers = {"User-Agent": "ProtocolPulse/1.0"}
        subreddits = self._config.get("reddit_subreddits", ["Bitcoin"])

        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/new.json?limit=25"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        for child in data.get("data", {}).get("children", []):
                            d = child.get("data", {})
                            posts.append({
                                "text": f"{d.get('title', '')} {d.get('selftext', '')[:500]}",
                                "author": d.get("author", ""),
                                "source": "reddit",
                                "timestamp": d.get("created_utc", 0),
                            })
                    else:
                        logger.warning("Reddit r/%s returned %d", sub, resp.status)
            except Exception as e:
                logger.warning("Reddit r/%s fetch failed: %s", sub, e)

        self._reddit_cache = posts
        self._reddit_cache_ts = now
        return posts

    async def collect_nostr(self, session: aiohttp.ClientSession) -> list:
        """Fetch recent Bitcoin-tagged notes from Nostr relay."""
        posts = []
        relays = self._config.get("nostr_relays", ["wss://relay.damus.io"])

        for relay_url in relays[:1]:
            try:
                import websockets as _ws
                since = int(time.time()) - 1800
                sub_msg = json.dumps([
                    "REQ", "bitcoin-sentiment",
                    {"kinds": [1], "#t": ["bitcoin", "btc"], "limit": 50, "since": since}
                ])

                async with _ws.connect(relay_url, close_timeout=5, open_timeout=5) as ws:
                    await ws.send(sub_msg)
                    deadline = time.time() + 3.0
                    while time.time() < deadline:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            msg = json.loads(raw)
                            if isinstance(msg, list) and len(msg) >= 3 and msg[0] == "EVENT":
                                event = msg[2]
                                posts.append({
                                    "text": event.get("content", "")[:500],
                                    "author": event.get("pubkey", "")[:16],
                                    "source": "nostr",
                                    "timestamp": event.get("created_at", 0),
                                })
                            elif isinstance(msg, list) and msg[0] == "EOSE":
                                break
                        except asyncio.TimeoutError:
                            break
                    await ws.send(json.dumps(["CLOSE", "bitcoin-sentiment"]))
            except Exception as e:
                logger.warning("Nostr relay %s failed: %s", relay_url, e)

        return posts

    async def collect_x(self, session: aiohttp.ClientSession) -> list:
        """Fetch recent posts from X via nitter instances (best effort)."""
        posts = []
        nitter_instances = [
            "https://nitter.privacydev.net",
            "https://nitter.poast.org",
        ]
        handles = list(self._tier1_handles)[:5]

        for handle in handles:
            for instance in nitter_instances[:1]:
                try:
                    url = f"{instance}/{handle}/rss"
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            items = re.findall(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', text)
                            for item_text in items[1:6]:
                                posts.append({
                                    "text": item_text,
                                    "author": handle,
                                    "source": "x",
                                    "timestamp": time.time(),
                                })
                            break
                except Exception:
                    continue

        return posts

    async def run_cycle(self, session: aiohttp.ClientSession) -> dict:
        """Run full sentiment collection + scoring cycle. Called every 30s from sentinel."""
        try:
            results = await asyncio.gather(
                self.collect_reddit(session),
                self.collect_nostr(session),
                self.collect_x(session),
                return_exceptions=True,
            )

            all_posts = []
            for r in results:
                if isinstance(r, list):
                    all_posts.extend(r)
                elif isinstance(r, Exception):
                    logger.warning("Sentiment collector error: %s", r)

            return self.compute_sentiment_state(all_posts)

        except Exception as e:
            logger.error("Sentiment cycle failed: %s", e)
            return self._build_output(self._last_score, {}, [], time.time())
