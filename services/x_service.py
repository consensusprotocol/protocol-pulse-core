import os
_TWEETS_ENABLED = os.environ.get('ENABLE_TWEETS', 'false').lower() == 'true'

import hashlib
import logging
import json
import re
import sqlite3
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
try:
    import tweepy
except ImportError:
    tweepy = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)

# ============================================================
# GLOBAL POSTING GATE — every posting path MUST call this
# ============================================================
_GATE_DB = Path("/home/ultron/protocol_pulse/data/x_post_ledger.db")
_POSTED_HASHES_FILE = Path("/home/ultron/protocol_pulse/data/posted_tweets.json")
_MAX_POSTS_PER_24H = 8
_MIN_GAP_HOURS = 2
_SIMILARITY_THRESHOLD = 0.50
_SIMILARITY_WINDOW_HOURS = 72


def _content_hash(text: str) -> str:
    """MD5 hash of normalized tweet text (first 100 chars, lowered, stripped)."""
    return hashlib.md5(text.strip().lower()[:100].encode()).hexdigest()


def _load_posted_hashes() -> set:
    """Load persistent set of posted tweet content hashes.

    Handles both legacy format (flat list of strings) and new format
    (list of {hash, timestamp} dicts).
    """
    if _POSTED_HASHES_FILE.exists():
        try:
            data = json.loads(_POSTED_HASHES_FILE.read_text())
            if not isinstance(data, list):
                return set()
            hashes = set()
            for entry in data:
                if isinstance(entry, str):
                    hashes.add(entry)  # Legacy format
                elif isinstance(entry, dict) and "hash" in entry:
                    hashes.add(entry["hash"])
            return hashes
        except (json.JSONDecodeError, TypeError):
            return set()
    return set()


def _load_posted_entries() -> list:
    """Load the full entries list (preserves timestamps)."""
    if _POSTED_HASHES_FILE.exists():
        try:
            data = json.loads(_POSTED_HASHES_FILE.read_text())
            if not isinstance(data, list):
                return []
            entries = []
            for entry in data:
                if isinstance(entry, str):
                    entries.append({"hash": entry, "timestamp": None})  # Migrate legacy
                elif isinstance(entry, dict):
                    entries.append(entry)
            return entries
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _save_posted_hash(h: str, tweet_text: str = "", format_type: str = "") -> None:
    """Append a content hash with timestamp to the persistent posted tweets file."""
    from datetime import datetime, timezone
    entries = _load_posted_entries()
    existing_hashes = {e["hash"] for e in entries if isinstance(e, dict) and "hash" in e}
    if h not in existing_hashes:
        entry = {
            "hash": h,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if tweet_text:
            entry["text_preview"] = tweet_text[:80]
        if format_type:
            entry["format_type"] = format_type
        entries.append(entry)
    _POSTED_HASHES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _POSTED_HASHES_FILE.write_text(json.dumps(entries, indent=2))

# Narrative categories for angle diversity
ANGLE_CATEGORIES = [
    "macro_monetary",       # Macro/monetary policy signal
    "onchain_metric",       # On-chain metric insight
    "institutional_flow",   # Institutional flow (ETF, treasury)
    "geopolitical",         # Geopolitical Bitcoin signal
    "historical_pattern",   # Historical pattern/precedent
    "network_fundamentals", # Network fundamentals (hashrate, difficulty)
    "sovereignty_freedom",  # Sovereignty/freedom framing
    "contrarian_take",      # Contrarian take on mainstream narrative
]

# ============================================================
# CONCEPT TAXONOMY — fixed keyword list for concept-level dedup
# ============================================================
CONCEPT_TAXONOMY = {
    "fear_greed_index":     ["fear index", "extreme fear", "fear & greed", "fng", "fear greed"],
    "etf_flows":            ["etf", "inflow", "outflow", "blackrock", "fidelity", "ibit"],
    "stablecoin_power":     ["stablecoin", "usdt", "usdc", "tether", "180b", "treasury backing"],
    "macro_fed":            ["fed ", "federal reserve", "interest rate", "powell", "monetary policy"],
    "geopolitical":         ["iran", "war ", "sanctions", "tariff", "geopolit", "china", "russia"],
    "institutional_buying": ["saylor", "microstrategy", "strategy ", "corporate treasury"],
    "mining_hashrate":      ["mining", "hashrate", "miner", "difficulty", "exahash"],
    "dollar_debasement":    ["dollar", "inflation", "debasement", "fiat", "printing", "dxy"],
    "on_chain":             ["on-chain", "wallet", "utxo", "hodl", "accumulation", "cold storage"],
    "lightning_network":    ["lightning", "layer 2", "l2 ", "payment channel"],
    "regulatory":           ["sec ", "regulation", "congress", "legislation", "gensler"],
    "petrodollar":          ["petrodollar", "yuan", "reserve currency", "brics"],
    "historical_cycle":     ["cycle", "halving", "4 year", "previous cycle", "last time", "historically"],
    "sovereignty":          ["sovereignty", "self-custody", "censor", "confiscat", "freedom"],
    "whale_activity":       ["whale", "large wallet", "exchange outflow", "cold storage move"],
    "network_health":       ["node count", "decentraliz", "protocol upgrade"],
    "privacy":              ["privacy", "coinjoin", "kyc", "surveillance", "mixer"],
    "adoption":             ["adoption", "merchant accept", "el salvador"],
    "price_action":         ["price", "rally", "dump", "all-time high", "correction", " dip", " ath "],
    "other":                [],
}

_CONCEPT_COOLDOWN_HOURS = 8


def extract_concept(tweet_text: str) -> str:
    """Extract the core narrative concept from a tweet using keyword matching."""
    text = tweet_text.lower()
    for concept, keywords in CONCEPT_TAXONOMY.items():
        if any(kw in text for kw in keywords):
            return concept
    return "other"


def _init_gate_db():
    """Ensure the post ledger table exists."""
    _GATE_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_GATE_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS x_post_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posted_at TEXT NOT NULL,
            tweet_text TEXT NOT NULL,
            source TEXT DEFAULT 'unknown',
            angle_category TEXT,
            concept TEXT,
            allowed INTEGER DEFAULT 1,
            reason TEXT
        )
    """)
    # Migrate: add concept column if missing (existing DBs)
    try:
        conn.execute("ALTER TABLE x_post_ledger ADD COLUMN concept TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()
    conn.close()


def _keyword_set(text: str) -> set:
    """Extract significant words from text for similarity check."""
    stop = {"the","a","an","is","are","was","were","and","or","but","in","on","at",
            "to","of","for","with","this","that","it","as","by","not","no","from",
            "has","have","had","will","would","could","should","just","more","than"}
    return set(w.lower() for w in re.findall(r"\w+", text) if w.lower() not in stop and len(w) > 3)


def _text_similarity(a: str, b: str) -> float:
    """Keyword overlap fraction between two texts."""
    wa, wb = _keyword_set(a), _keyword_set(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def can_post_tweet(text: str, source: str = "unknown", angle_category: str = None) -> tuple:
    """
    Global gate. Every posting path MUST call this before posting.
    Returns (allowed: bool, reason: str).

    Rules:
    1. Max 3 posts per 24 hours across ALL posting services
    2. Minimum 4 hours between any two posts
    3. 40% similarity threshold against last 48h posts
    4. No hashtags (strip them if present)
    5. No duplicate angle category same day
    6. Logs every check (allowed or blocked) with reason
    """
    _init_gate_db()
    now = datetime.now(timezone.utc)

    # Rule 0: Persistent content-hash dedup (catches exact/near-exact duplicates across ALL time)
    h = _content_hash(text)
    if h in _load_posted_hashes():
        reason = f"BLOCKED: duplicate content hash {h[:8]}... — this text was already posted"
        logger.warning("[X GATE] %s | source=%s | %s", "BLOCKED", source, reason)
        return (False, reason)

    conn = sqlite3.connect(str(_GATE_DB))

    try:
        # Rule 1: Max 3 posts per 24 hours
        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        count_24h = conn.execute(
            "SELECT COUNT(*) FROM x_post_ledger WHERE posted_at >= ? AND allowed = 1",
            (cutoff_24h,)
        ).fetchone()[0]
        if count_24h >= _MAX_POSTS_PER_24H:
            reason = f"BLOCKED: {count_24h}/{_MAX_POSTS_PER_24H} posts in 24h — daily limit reached"
            _log_gate(conn, now, text, source, angle_category, allowed=False, reason=reason)
            return (False, reason)

        # Rule 2: Minimum 4 hours gap
        last_row = conn.execute(
            "SELECT posted_at FROM x_post_ledger WHERE allowed = 1 ORDER BY posted_at DESC LIMIT 1"
        ).fetchone()
        if last_row:
            last_time = datetime.fromisoformat(last_row[0])
            if last_time.tzinfo is None:
                last_time = last_time.replace(tzinfo=timezone.utc)
            gap_hours = (now - last_time).total_seconds() / 3600
            if gap_hours < _MIN_GAP_HOURS:
                reason = f"BLOCKED: {gap_hours:.1f}h since last post — minimum {_MIN_GAP_HOURS}h gap required"
                _log_gate(conn, now, text, source, angle_category, allowed=False, reason=reason)
                return (False, reason)

        # Rule 3: Similarity check against last 48h
        cutoff_48h = (now - timedelta(hours=_SIMILARITY_WINDOW_HOURS)).isoformat()
        recent_rows = conn.execute(
            "SELECT tweet_text FROM x_post_ledger WHERE posted_at >= ? AND allowed = 1",
            (cutoff_48h,)
        ).fetchall()
        for (old_text,) in recent_rows:
            sim = _text_similarity(text, old_text)
            if sim >= _SIMILARITY_THRESHOLD:
                reason = f"BLOCKED: {sim:.0%} similarity with recent post — threshold {_SIMILARITY_THRESHOLD:.0%}"
                _log_gate(conn, now, text, source, angle_category, allowed=False, reason=reason)
                return (False, reason)

        # Rule 4: Concept dedup — no same concept within 72 hours
        concept = extract_concept(text)
        if concept != "other":
            cutoff_72h = (now - timedelta(hours=_CONCEPT_COOLDOWN_HOURS)).isoformat()
            same_concept_rows = conn.execute(
                "SELECT posted_at, tweet_text FROM x_post_ledger "
                "WHERE posted_at >= ? AND allowed = 1 AND concept = ?",
                (cutoff_72h, concept)
            ).fetchall()
            if same_concept_rows:
                last_post = same_concept_rows[-1]
                reason = (
                    f"BLOCKED: concept '{concept}' already used in last 72h — "
                    f"last post: {last_post[1][:60]}..."
                )
                _log_gate(conn, now, text, source, angle_category, allowed=False, reason=reason, concept=concept)
                return (False, reason)

        # Rule 5: Angle diversity — no duplicate category same day
        if angle_category:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            same_angle = conn.execute(
                "SELECT COUNT(*) FROM x_post_ledger WHERE posted_at >= ? AND allowed = 1 AND angle_category = ?",
                (today_start, angle_category)
            ).fetchone()[0]
            if same_angle > 0:
                reason = f"BLOCKED: angle '{angle_category}' already used today — pick a different category"
                _log_gate(conn, now, text, source, angle_category, allowed=False, reason=reason)
                return (False, reason)

        # All checks passed — record hash to prevent future duplicate
        _save_posted_hash(h, tweet_text=text, format_type=angle_category or source)
        reason = f"ALLOWED: post {count_24h + 1}/{_MAX_POSTS_PER_24H} today, source={source}"
        _log_gate(conn, now, text, source, angle_category, allowed=True, reason=reason)
        return (True, reason)

    finally:
        conn.close()


def _log_gate(conn, now, text, source, angle_category, allowed, reason, concept=None):
    """Log every gate check to the ledger."""
    if concept is None:
        concept = extract_concept(text)
    conn.execute(
        "INSERT INTO x_post_ledger (posted_at, tweet_text, source, angle_category, concept, allowed, reason) VALUES (?,?,?,?,?,?,?)",
        (now.isoformat(), text[:500], source, angle_category, concept, 1 if allowed else 0, reason)
    )
    conn.commit()
    level = logging.INFO if allowed else logging.WARNING
    logger.log(level, "[X GATE] %s | source=%s | %s", "ALLOWED" if allowed else "BLOCKED", source, reason)


def get_recent_angles(days: int = 1) -> list:
    """Return angle categories used in the last N days. Used by tweet generators for diversity."""
    _init_gate_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(str(_GATE_DB))
    rows = conn.execute(
        "SELECT angle_category FROM x_post_ledger WHERE posted_at >= ? AND allowed = 1 AND angle_category IS NOT NULL",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_banned_concepts(hours: int = 72) -> list:
    """Return concepts posted in the last N hours (for prompt injection into LLM)."""
    _init_gate_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    conn = sqlite3.connect(str(_GATE_DB))
    rows = conn.execute(
        "SELECT DISTINCT concept FROM x_post_ledger "
        "WHERE posted_at >= ? AND allowed = 1 AND concept IS NOT NULL",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [r[0] for r in rows if r[0] != "other"]


def get_available_angles() -> list:
    """Return angle categories NOT yet used today."""
    used = set(get_recent_angles(days=1))
    return [a for a in ANGLE_CATEGORIES if a not in used]


def _strip_hashtags(text):
    """Remove all hashtags from text - Protocol Pulse never uses hashtags."""
    if not text:
        return text
    return re.sub(r'#\w+\s*', '', text).strip()

class XService:
    def __init__(self):
        self.client = None
        self.client_v2 = None
        self.openai_client = None
        
        try:
            api_key = os.environ.get("TWITTER_API_KEY", "")
            api_secret = os.environ.get("TWITTER_API_SECRET", "")
            access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
            access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")
            bearer = os.environ.get("TWITTER_BEARER_TOKEN", "")
            
            if api_key and api_secret and access_token and access_secret:
                import tweepy
                auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
                self.client = tweepy.API(auth)
                self.client_v2 = tweepy.Client(
                    bearer_token=bearer,
                    consumer_key=api_key,
                    consumer_secret=api_secret,
                    access_token=access_token,
                    access_token_secret=access_secret,
                    wait_on_rate_limit=False
                )
                logging.info("X/Twitter clients initialized successfully")
            else:
                logging.warning("X/Twitter API keys not fully configured")
        except Exception as e:
            logging.error(f"X/Twitter client init failed: {e}")
        
        self.openai_client = (OpenAI(api_key=os.environ.get('OPENAI_API_KEY')) if OpenAI and os.environ.get('OPENAI_API_KEY') else None)
        
    def get_feedback(self, handle):
        if not self.client:
            return [{'id': 'mock_id', 'text': f'Mock tweet from @{handle}', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
        try:
            tweets = self.client.search_recent_tweets(query=f'from:{handle} -is:retweet', max_results=10, expansions='referenced_tweets.id').data or []
            filtered = []
            for tweet in tweets:
                if not hasattr(tweet, 'referenced_tweets') or not tweet.referenced_tweets:
                    relevance = self._is_relevant(tweet.text)
                    if relevance['is_relevant']:
                        filtered.append({'id': tweet.id, 'text': tweet.text, 'is_relevant': True, 'topic': relevance['topic'], 'nuance': relevance['nuance']})
            return filtered
        except Exception as e:
            logging.error(f"X API error: {e}")
            return [{'id': 'mock_id', 'text': f'Mock tweet from @{handle}', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
    
    def _is_relevant(self, text):
        if not self.openai_client:
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
        if len(text.split()) < 10 or any(m in text.lower() for m in ['lol', '😂', 'meme']):
            return {'is_relevant': False}
        try:
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': f"Analyze tweet: '{text}'. Is it relevant to Web3/Bitcoin/DeFi? If yes, extract topic and nuance. Return JSON: {{'is_relevant': bool, 'topic': str, 'nuance': str}}"}],
                max_tokens=100
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Relevance analysis error: {e}")
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}

    def post_article_tweet(self, article, base_url=''):
        """Route article tweets through unified quality gate + global rate gate."""
        if not self.client and not self.client_v2:
            logging.warning("Twitter API not configured - skipping tweet")
            return None
        if not _TWEETS_ENABLED:
            logging.info('[TWEETS DISABLED] Skipping article tweet')
            return None
        try:
            from services.unified_post_gate import unified_post_gate
            result = unified_post_gate.process_article_post(
                article.id,
                article.title,
                getattr(article, 'summary', '') or ''
            )
            if result.get("approved") and result.get("tweet_text"):
                tweet_text = _strip_hashtags(result["tweet_text"][:280])
                # Global gate check
                allowed, reason = can_post_tweet(tweet_text, source="article_tweet", angle_category="institutional_flow")
                if not allowed:
                    logger.warning("[X GATE REJECT] article_tweet | %s", reason)
                    return None
                if self.client_v2:
                    r = self.client_v2.create_tweet(text=tweet_text)
                    return str(r.data["id"]) if r and r.data else None
                elif self.client:
                    response = self.client.update_status(tweet_text)
                    return response.id
            else:
                logging.info(f"Tweet rejected by quality gate: {result.get('rejection_reason', 'unknown')}")
                return None
        except Exception as e:
            logging.error(f"Failed to post tweet: {e}")
            return None

    # ... rest of your velocity and video methods stay the same ...

    def get_upload_status(self):
        return {
            'configured': self.client is not None,
            'v2_available': self.client_v2 is not None,
            'can_post_video': self.client is not None
        }

    def post_reply(self, tweet_id, text, source: str = "reply"):
        """
        Post a reply to a tweet (for Zap-Comment / Diplomat bridge).
        Replies bypass the daily post count but still go through similarity check.
        Returns reply tweet id or None.
        """
        text = _strip_hashtags(text)
        if len(text) > 280:
            text = text[:277] + "..."
        try:
            if self.client_v2:
                if not _TWEETS_ENABLED:
                    logging.info('[TWEETS DISABLED]')
                    return None
                r = self.client_v2.create_tweet(text=text, in_reply_to_tweet_id=str(tweet_id))
                if r and r.data and getattr(r.data, "id", None):
                    return str(r.data.id)
            if self.client:
                resp = self.client.update_status(status=text, in_reply_to_status_id=str(tweet_id))
                return str(resp.id) if resp else None
        except Exception as e:
            logging.error("post_reply failed: %s", e)
        return None

    def _get_branded_pulse_path(self):
        """Path to Protocol Pulse branded logo (cover + pulse). Fallback to main logo if brand asset missing."""
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        brand_path = os.path.join(base, "static", "images", "brand", "pp-pulse-brand.png")
        if os.path.isfile(brand_path):
            return brand_path
        fallback = os.path.join(base, "static", "images", "protocol-pulse-logo.png")
        return fallback if os.path.isfile(fallback) else None

    def post_dual_image_news(self, text, cover_url, dry_run=False, source="dual_image_news"):
        """
        Post a breaking-news tweet with two images: (1) cover/header from the story, (2) Protocol Pulse branded pulse logo.
        Returns tweet id or None. If dry_run=True, returns dict with draft text without posting.
        """
        text = _strip_hashtags(text)
        if len(text) > 280:
            text = text[:277] + "..."
        branded_path = self._get_branded_pulse_path()
        if not branded_path:
            logging.warning("No branded pulse image found; dual-image post may fail.")
        if dry_run:
            return {
                "dry_run": True,
                "text": text,
                "cover_url": cover_url,
                "branded_path": branded_path,
                "message": "Would post to X with 2 images (cover + branded)." if self.client else "X API not configured."
            }
        # Global gate check
        allowed, reason = can_post_tweet(text, source=source)
        if not allowed:
            logger.warning("[X GATE REJECT] %s | %s", source, reason)
            return None
        if not self.client:
            logging.warning("X API not configured - skipping dual-image post")
            return None
        try:
            media_ids = []
            if cover_url:
                r = requests.get(cover_url, timeout=15)
                r.raise_for_status()
                ext = "jpg" if "jpeg" in (r.headers.get("content-type") or "").lower() or cover_url.lower().endswith((".jpg", ".jpeg")) else "png"
                with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                    tmp.write(r.content)
                    tmp.flush()
                    try:
                        media_ids.append(self.client.media_upload(tmp.name).media_id_string)
                    finally:
                        try:
                            os.unlink(tmp.name)
                        except OSError:
                            pass
            if branded_path:
                media_ids.append(self.client.media_upload(branded_path).media_id_string)
            if not media_ids:
                logging.warning("No media uploaded for dual-image post; posting text only.")
            response = self.client.update_status(status=text, media_ids=media_ids)
            return response.id
        except Exception as e:
            logging.error("Dual-image news post failed: %s", e)
            return None

# Backward compatibility functions

    def post_tweet(self, text: str, image_path: str = None, source: str = "unknown",
                   angle_category: str = None, bypass_gate: bool = False) -> dict:
        """Post a simple tweet, optionally with an image. All posts go through global gate."""
        if not self.client_v2:
            return {"error": "Twitter client not initialized"}

        text = _strip_hashtags(text)

        # Global gate check
        if not bypass_gate:
            allowed, reason = can_post_tweet(text, source=source, angle_category=angle_category)
            if not allowed:
                logger.warning("[X GATE REJECT] %s | %s", source, reason)
                return {"error": reason, "gate_blocked": True}

        try:
            if image_path:
                media = self.client.media_upload(image_path)
                response = self.client_v2.create_tweet(text=text, media_ids=[media.media_id])
            else:
                response = self.client_v2.create_tweet(text=text)

            return {"success": True, "tweet_id": response.data['id']}
        except Exception as e:
            return {"error": str(e)}


# Backward compatibility functions
def get_social_feedback(topic):
    """Get social feedback for backward compatibility"""
    return {
        'sentiment': 'neutral',
        'sentiment_score': 0.5,
        'key_insights': [f"Mock insight about {topic}", "Community discussion ongoing", "Market watching closely"],
        'source': 'stubbed_data'
    }


# ============================================================
# MODULE-LEVEL WRAPPERS — used by Comment Radar & Engagement Engine
# ============================================================
_x_instance = None

def _get_x():
    global _x_instance
    if _x_instance is None:
        _x_instance = XService()
    return _x_instance

def post_tweet(text, image_path=None, source="module_wrapper", angle_category=None):
    """Post a tweet. Returns dict with 'id' or None."""
    x = _get_x()
    return x.post_tweet(text, image_path, source=source, angle_category=angle_category)

def reply_to_tweet(tweet_id, text, source="reply"):
    """Reply to a tweet. Returns dict with 'id' or None."""
    x = _get_x()
    return x.post_reply(tweet_id, text, source=source)

def quote_tweet(text, url=None, source="quote_tweet"):
    """Post a quote tweet (text + url). Returns dict with 'id' or None."""
    x = _get_x()
    if url:
        text = f"{text} {url}".strip()[:280]
    return x.post_tweet(text, source=source)
