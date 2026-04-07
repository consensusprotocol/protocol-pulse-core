"""
PROTOCOL PULSE — MEDIA FEED SERVICE
Aggregates 15 RSS podcast feeds + 7 YouTube channels into SQLite cache.
Background sync via threading. Signal score on ingest. AI summaries via Claude Haiku.

Created: 2026-03-25
"""

import os
import re
import time
import hashlib
import logging
import threading
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── FEED REGISTRY ────────────────────────────────────────────────────────────

PODCAST_FEEDS = [
    {"name": "Cypherpunk'd", "url": "https://anchor.fm/s/fa724db8/podcast/rss", "host": "PBX", "tier": 1, "color": "#f7931a", "category": "podcast"},
    {"name": "Protocol Pulse", "url": "https://feed.podbean.com/protocolpulse/feed.xml", "host": "Protocol Pulse", "tier": 1, "color": "#dc2626", "category": "podcast"},
    {"name": "TFTC", "url": "https://tftc.io/feed/", "host": "Marty Bent", "tier": 1, "color": "#ff6b35", "category": "podcast"},
    {"name": "Stephan Livera", "url": "https://anchor.fm/s/7d083a4/podcast/rss", "host": "Stephan Livera", "tier": 1, "color": "#4a90d9", "category": "podcast"},
    {"name": "What Bitcoin Did", "url": "https://www.whatbitcoindid.com/podcast?format=rss", "host": "Peter McCormack", "tier": 1, "color": "#f7931a", "category": "podcast"},
    {"name": "Bitcoin Audible", "url": "https://bitcoinaudible.com/?feed=podcast", "host": "Guy Swann", "tier": 1, "color": "#9b59b6", "category": "podcast"},
    {"name": "The Bitcoin Layer", "url": "https://anchor.fm/s/14978d30/podcast/rss", "host": "Nik Bhatia", "tier": 1, "color": "#3498db", "category": "podcast"},
    {"name": "Simply Bitcoin", "url": "https://anchor.fm/s/717a2198/podcast/rss", "host": "Nico Moran", "tier": 2, "color": "#e74c3c", "category": "podcast"},
    {"name": "Bitcoin Magazine Podcast", "url": "https://bitcoinmagazine.com/.rss/full/", "host": "Bitcoin Magazine", "tier": 1, "color": "#f7931a", "category": "podcast"},
    {"name": "Citadel Dispatch", "url": "https://serve.podhome.fm/CitadelDispatch", "host": "Matt Odell", "tier": 1, "color": "#27ae60", "category": "podcast"},
    {"name": "Natalie Brunell", "url": "https://rss.libsyn.com/shows/344543/destinations/2813255.xml", "host": "Natalie Brunell", "tier": 1, "color": "#e91e63", "category": "podcast"},
    {"name": "Rabbit Hole Recap", "url": "https://feeds.fountain.fm/0EAzqUaM4qqanDr1qNuK", "host": "Marty Bent & ODELL", "tier": 1, "color": "#ff6b35", "category": "podcast"},
    {"name": "Preston Pysh / TIP", "url": "https://rss.art19.com/the-investors-podcast", "host": "Preston Pysh", "tier": 1, "color": "#2c3e50", "category": "podcast"},
]

YOUTUBE_CHANNELS = [
    {"name": "Blockware Solutions", "channel_id": "UC678LSROK47l__G-pMnOMgA", "tier": 1, "color": "#3498db", "category": "video"},
    {"name": "Bitcoin Magazine", "channel_id": "UCtOV5M-T3GcsJAq8QKaf0lg", "tier": 1, "color": "#f7931a", "category": "video"},
    {"name": "Coin Bureau", "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw", "tier": 1, "color": "#00d4aa", "category": "video"},
    {"name": "What Bitcoin Did", "channel_id": "UCtvg5cXLY_tHDJeBoRySBtg", "tier": 1, "color": "#f7931a", "category": "video"},
    {"name": "Simply Bitcoin", "channel_id": "UCB6Q0S1gUHXMe5-Jjx0_laQ", "tier": 2, "color": "#e74c3c", "category": "video"},
    {"name": "Robert Breedlove", "channel_id": "UC43_LTf5Z4lbRjKCq0sIAVg", "tier": 1, "color": "#1abc9c", "category": "video"},
    {"name": "Natalie Brunell", "channel_id": "UCru3nlhzHrbgK21x0MdB_eg", "tier": 1, "color": "#e91e63", "category": "video"},
    {"name": "Bitcoin Audible", "channel_id": "UClG-wqz-OuXfzbpqwJd3fVA", "tier": 1, "color": "#9b59b6", "category": "video"},
    {"name": "Bitcoin Boomers", "channel_id": "UCOp_-d0z7r-s02CWsJTbVoA", "tier": 1, "color": "#f39c12", "category": "video"},
    {"name": "Cypherpunk'd", "channel_id": "UC4BPphH-KN4F9ev7Ekt0zew", "tier": 1, "color": "#dc2626", "category": "video"},
]

# ─── SIGNAL SCORE ──────────────────────────────────────────────────────────────

# Keywords that boost signal score
SIGNAL_KEYWORDS = {
    # High-signal macro terms (weight 15)
    'etf': 15, 'halving': 15, 'fed': 15, 'regulation': 15, 'strategic reserve': 15,
    'blackrock': 12, 'microstrategy': 12, 'saylor': 12, 'treasury': 12,
    # Protocol terms (weight 10)
    'lightning': 10, 'taproot': 10, 'nostr': 10, 'self-custody': 10, 'mining': 10,
    'hashrate': 10, 'difficulty': 10, 'mempool': 10,
    # Market terms (weight 8)
    'all-time high': 8, 'ath': 8, 'bull': 8, 'bear': 8, 'accumulation': 8,
    'whale': 8, 'on-chain': 8, 'hodl': 8,
    # General bitcoin (weight 5)
    'bitcoin': 5, 'btc': 5, 'satoshi': 5, 'block': 5, 'node': 5,
}

EXCLUDED_TERMS = ['jill', 'orange is the new jill', 'orange is the nw jill']


def compute_signal_score(title: str, description: str, tier: int = 2,
                         published_at=None) -> int:
    """Compute 0-100 signal score: source_tier*40 + sentiment*40 + recency*20.

    - source_tier (40 pts): T1=40, T2=24, T3=12
    - sentiment (40 pts): keyword density mapped to 0-40 range
    - recency  (20 pts): <6h=20, <24h=16, <3d=10, <7d=5, older=0
    """
    text = f"{title} {description}".lower()

    # ── Source Tier Component (0-40) ──
    tier_score = {1: 40, 2: 24, 3: 12}.get(tier, 16)

    # ── Sentiment/Keyword Component (0-40) ──
    keyword_raw = 0
    for kw, weight in SIGNAL_KEYWORDS.items():
        if kw in text:
            keyword_raw += weight
    # Normalize dynamically based on actual max achievable keyword score
    max_kw = sum(SIGNAL_KEYWORDS.values()) or 1
    sentiment_score = min(int(keyword_raw * 40 / max_kw), 40)

    # ── Recency Component (0-20) ──
    recency_score = 0
    if published_at:
        try:
            age_hours = (datetime.utcnow() - published_at).total_seconds() / 3600
            if age_hours < 6:
                recency_score = 20
            elif age_hours < 24:
                recency_score = 16
            elif age_hours < 72:
                recency_score = 10
            elif age_hours < 168:
                recency_score = 5
        except Exception:
            pass

    return min(tier_score + sentiment_score + recency_score, 100)


def is_excluded(title: str) -> bool:
    """Check if content should be filtered out."""
    t = title.lower()
    return any(exc in t for exc in EXCLUDED_TERMS)


# ─── FEED PARSING ──────────────────────────────────────────────────────────────

def _clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    return re.sub(r'<[^>]*>', '', text).strip()


def _parse_duration(entry) -> str:
    """Extract duration from RSS entry."""
    if hasattr(entry, 'itunes_duration'):
        return entry.itunes_duration
    for field in ('duration', 'podcast_duration'):
        if hasattr(entry, field):
            return str(getattr(entry, field))
    return ''


def _extract_audio_url(entry) -> Optional[str]:
    """Extract audio URL from RSS entry."""
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if hasattr(enc, 'type') and enc.type and enc.type.startswith('audio/'):
                return enc.href
    if hasattr(entry, 'links'):
        for link in entry.links:
            if link.get('type', '').startswith('audio/'):
                return link.href
    return None


def _parse_rss_date(entry) -> Optional[datetime]:
    """Parse RSS date to datetime."""
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            import calendar
            return datetime.utcfromtimestamp(calendar.timegm(entry.published_parsed))
        except Exception:
            pass
    return None


def _make_guid(entry, feed_url: str) -> str:
    """Generate a stable unique ID for an RSS entry."""
    raw = entry.get('id') or entry.get('link') or entry.get('title', '')
    return hashlib.sha256(f"{feed_url}:{raw}".encode()).hexdigest()[:40]


def _fetch_feed(url: str):
    """Fetch RSS feed with proper user-agent (feedparser alone fails on some hosts)."""
    import requests as req
    try:
        r = req.get(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; ProtocolPulse/1.0)'}, timeout=20)
        if r.status_code == 200 and len(r.text) > 100:
            return feedparser.parse(r.text)
    except Exception:
        pass
    # Fallback to feedparser's own fetcher
    return feedparser.parse(url)


def parse_rss_feed(feed_config: dict) -> List[dict]:
    """Parse an RSS feed and return list of episode dicts."""
    try:
        feed = _fetch_feed(feed_config['url'])
    except Exception as e:
        logger.error(f"Failed to parse RSS {feed_config['name']}: {e}")
        return []

    episodes = []
    cover = None
    try:
        if hasattr(feed.feed, 'image') and feed.feed.image:
            cover = feed.feed.image.get('href')
        elif hasattr(feed.feed, 'itunes_image'):
            img = feed.feed.itunes_image
            cover = img.get('href') if isinstance(img, dict) else img
    except Exception:
        pass

    for entry in feed.entries[:15]:
        title = entry.get('title', '').strip()
        if not title or is_excluded(title):
            continue

        desc = _clean_html(entry.get('description', '') or entry.get('summary', ''))
        if len(desc) > 500:
            desc = desc[:497] + '...'

        pub_date = _parse_rss_date(entry)
        audio = _extract_audio_url(entry)

        # Episode-level thumbnail
        thumb = None
        if hasattr(entry, 'image') and entry.image:
            thumb = entry.image.get('href')
        elif hasattr(entry, 'itunes_image'):
            img = entry.itunes_image
            thumb = img.get('href') if isinstance(img, dict) else img
        if not thumb:
            thumb = cover

        episodes.append({
            'guid': _make_guid(entry, feed_config['url']),
            'title': title,
            'description': desc,
            'audio_url': audio,
            'source_url': entry.get('link', ''),
            'thumbnail_url': thumb,
            'duration': _parse_duration(entry),
            'published_at': pub_date,
            'signal_score': compute_signal_score(title, desc, feed_config.get('tier', 2), pub_date),
        })

    return episodes


def parse_youtube_rss(channel_config: dict) -> List[dict]:
    """Fetch latest videos from YouTube channel via Data API v3 (RSS deprecated)."""
    import requests as req
    api_key = os.environ.get('YOUTUBE_API_KEY')

    episodes = []

    # RSS FIRST (free, unlimited) — API only if RSS returns 0
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_config['channel_id']}"
    try:
        feed = _fetch_feed(rss_url)
        for entry in feed.entries[:10]:
            title = entry.get('title', '').strip()
            if not title or is_excluded(title):
                continue
            vid_id = entry.get('yt_videoid', '')
            desc = _clean_html(entry.get('summary', '') or '')[:500]
            pub_date = _parse_rss_date(entry)
            episodes.append({
                'guid': vid_id or _make_guid(entry, rss_url),
                'title': title,
                'description': desc,
                'video_url': f"https://www.youtube.com/watch?v={vid_id}" if vid_id else entry.get('link', ''),
                'source_url': entry.get('link', ''),
                'thumbnail_url': f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None,
                'duration': '',
                'published_at': pub_date,
                'signal_score': compute_signal_score(title, desc, channel_config.get('tier', 2), pub_date),
            })
    except Exception as e:
        logger.warning(f"[YouTube] RSS failed {channel_config['name']}: {e}")

    # API fallback only if RSS got nothing
    if not episodes and api_key:
        try:
            resp = req.get(
                'https://www.googleapis.com/youtube/v3/search',
                params={
                    'key': api_key,
                    'channelId': channel_config['channel_id'],
                    'part': 'snippet',
                    'order': 'date',
                    'maxResults': 10,
                    'type': 'video',
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get('items', []):
                    snippet = item.get('snippet', {})
                    title = snippet.get('title', '').strip()
                    if not title or is_excluded(title):
                        continue

                    vid_id = item.get('id', {}).get('videoId', '')
                    desc = _clean_html(snippet.get('description', ''))
                    if len(desc) > 500:
                        desc = desc[:497] + '...'

                    pub_str = snippet.get('publishedAt', '')
                    pub_date = None
                    if pub_str:
                        try:
                            pub_date = datetime.strptime(pub_str[:19], '%Y-%m-%dT%H:%M:%S')
                        except Exception:
                            pass

                    thumb = snippet.get('thumbnails', {}).get('high', {}).get('url') or \
                            (f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None)

                    episodes.append({
                        'guid': vid_id,
                        'title': title,
                        'description': desc,
                        'video_url': f"https://www.youtube.com/watch?v={vid_id}" if vid_id else '',
                        'source_url': f"https://www.youtube.com/watch?v={vid_id}" if vid_id else '',
                        'thumbnail_url': thumb,
                        'duration': '',
                        'published_at': pub_date,
                        'signal_score': compute_signal_score(title, desc, channel_config.get('tier', 2), pub_date),
                    })
            else:
                logger.warning(f"[YouTube] API {resp.status_code} for {channel_config['name']}")
        except Exception as e:
            logger.error(f"[YouTube] API error {channel_config['name']}: {e}")
    # (RSS fallback removed — RSS is now primary above)

    return episodes


# ─── DATABASE SYNC ─────────────────────────────────────────────────────────────

def ensure_tables():
    """Create tables if they don't exist."""
    from app import db
    db.create_all()


def sync_all_feeds(app=None):
    """Sync all RSS + YouTube feeds to database. Run in background thread."""
    if app is None:
        from app import app as flask_app
        app = flask_app

    with app.app_context():
        from app import db
        import models

        ensure_tables()
        total_new = 0

        # --- RSS Podcasts ---
        for fc in PODCAST_FEEDS:
            try:
                # Ensure feed row exists
                feed = models.MediaFeed.query.filter_by(url=fc['url']).first()
                if not feed:
                    feed = models.MediaFeed(
                        name=fc['name'], url=fc['url'], feed_type='rss',
                        category=fc['category'], host=fc.get('host', ''),
                        color=fc.get('color', '#dc2626'), tier=fc.get('tier', 2),
                    )
                    db.session.add(feed)
                    db.session.flush()

                episodes = parse_rss_feed(fc)
                new_count = 0
                for ep in episodes:
                    existing = models.MediaEpisode.query.filter_by(guid=ep['guid']).first()
                    if existing:
                        continue
                    me = models.MediaEpisode(
                        feed_id=feed.id,
                        guid=ep['guid'],
                        title=ep['title'],
                        description=ep['description'],
                        audio_url=ep.get('audio_url'),
                        source_url=ep.get('source_url'),
                        thumbnail_url=ep.get('thumbnail_url'),
                        duration=ep.get('duration', ''),
                        published_at=ep.get('published_at'),
                        signal_score=ep.get('signal_score', 0),
                    )
                    db.session.add(me)
                    new_count += 1

                feed.last_synced = datetime.utcnow()
                feed.episode_count = models.MediaEpisode.query.filter_by(feed_id=feed.id).count() + new_count
                db.session.commit()
                total_new += new_count
                if new_count:
                    logger.info(f"[MediaSync] {fc['name']}: +{new_count} episodes")
            except Exception as e:
                db.session.rollback()
                logger.error(f"[MediaSync] RSS error {fc['name']}: {e}")

        # --- YouTube Channels ---
        for yc in YOUTUBE_CHANNELS:
            try:
                yt_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={yc['channel_id']}"
                feed = models.MediaFeed.query.filter_by(url=yt_url).first()
                if not feed:
                    feed = models.MediaFeed(
                        name=yc['name'], url=yt_url, feed_type='youtube',
                        category=yc['category'], host=yc['name'],
                        color=yc.get('color', '#dc2626'), tier=yc.get('tier', 2),
                    )
                    db.session.add(feed)
                    db.session.flush()

                episodes = parse_youtube_rss(yc)
                new_count = 0
                for ep in episodes:
                    existing = models.MediaEpisode.query.filter_by(guid=ep['guid']).first()
                    if existing:
                        continue
                    me = models.MediaEpisode(
                        feed_id=feed.id,
                        guid=ep['guid'],
                        title=ep['title'],
                        description=ep['description'],
                        video_url=ep.get('video_url'),
                        source_url=ep.get('source_url'),
                        thumbnail_url=ep.get('thumbnail_url'),
                        duration=ep.get('duration', ''),
                        published_at=ep.get('published_at'),
                        signal_score=ep.get('signal_score', 0),
                    )
                    db.session.add(me)
                    new_count += 1

                feed.last_synced = datetime.utcnow()
                feed.episode_count = models.MediaEpisode.query.filter_by(feed_id=feed.id).count() + new_count
                db.session.commit()
                total_new += new_count
                if new_count:
                    logger.info(f"[MediaSync] YouTube {yc['name']}: +{new_count} videos")
            except Exception as e:
                db.session.rollback()
                logger.error(f"[MediaSync] YouTube error {yc['name']}: {e}")

        logger.info(f"[MediaSync] Complete. {total_new} new items across all feeds.")
        return total_new


_sync_lock = threading.Lock()
_sync_in_progress = False


def sync_feeds_background(app=None):
    """Fire-and-forget background sync with guard against duplicate threads."""
    global _sync_in_progress
    with _sync_lock:
        if _sync_in_progress:
            logger.info("[MediaSync] Sync already in progress, skipping duplicate.")
            return None
        _sync_in_progress = True

    def _run():
        global _sync_in_progress
        try:
            sync_all_feeds(app)
        finally:
            with _sync_lock:
                _sync_in_progress = False

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


# ─── AI SUMMARIES ──────────────────────────────────────────────────────────────

def generate_ai_summaries(app=None, batch_size: int = 20):
    """Generate Claude Haiku summaries for episodes missing them."""
    if app is None:
        from app import app as flask_app
        app = flask_app

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.warning("[MediaAI] No ANTHROPIC_API_KEY, skipping summaries")
        return 0

    with app.app_context():
        from app import db
        import models
        import requests as req

        unsummarized = models.MediaEpisode.query.filter(
            models.MediaEpisode.summary_ai.is_(None),
            models.MediaEpisode.description.isnot(None),
            models.MediaEpisode.description != '',
        ).order_by(models.MediaEpisode.published_at.desc()).limit(batch_size).all()

        if not unsummarized:
            return 0

        count = 0
        for ep in unsummarized:
            try:
                feed = models.MediaFeed.query.get(ep.feed_id)
                feed_name = feed.name if feed else 'Unknown'

                resp = req.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'content-type': 'application/json',
                    },
                    json={
                        'model': 'claude-3-haiku-20240307',
                        'max_tokens': 100,
                        'messages': [{
                            'role': 'user',
                            'content': f'Write exactly one sentence (max 30 words) summarizing this Bitcoin podcast episode for traders. Be specific about the signal — what matters for price action or protocol development. No fluff.\n\nShow: {feed_name}\nTitle: {ep.title}\nDescription: {ep.description[:400]}'
                        }],
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    summary = data.get('content', [{}])[0].get('text', '').strip()
                    if summary:
                        ep.summary_ai = summary[:300]
                        db.session.commit()
                        count += 1
                else:
                    logger.warning(f"[MediaAI] API {resp.status_code} for ep {ep.id}")

                time.sleep(0.5)  # Rate limit courtesy
            except Exception as e:
                logger.error(f"[MediaAI] Summary error for ep {ep.id}: {e}")

        logger.info(f"[MediaAI] Generated {count} summaries")
        return count


# ─── QUERY HELPERS ─────────────────────────────────────────────────────────────

def get_feed_matrix(limit_per_col: int = 20) -> dict:
    # Caps per source + interleaves for variety
    import models
    MAX_PER_SOURCE = 3

    def ep_to_dict(ep):
        feed = ep.feed
        return {
            'id': ep.id,
            'guid': ep.guid or '',
            'title': ep.title,
            'description': ep.description or '',
            'summary_ai': ep.summary_ai or '',
            'audio_url': ep.audio_url,
            'video_url': ep.video_url,
            'source_url': ep.source_url,
            'thumbnail_url': ep.thumbnail_url,
            'duration': ep.duration or '',
            'published_at': ep.published_at.isoformat() if ep.published_at else '',
            'signal_score': ep.signal_score or 0,
            'feed_name': feed.name if feed else '',
            'feed_host': feed.host if feed else '',
            'feed_color': feed.color if feed else '#dc2626',
            'feed_type': feed.feed_type if feed else '',
            'feed_tier': feed.tier if feed else 2,
        }

    def build_varied_list(feed_type, limit):
        feeds = (models.MediaFeed.query
                 .filter_by(feed_type=feed_type, active=True)
                 .filter(models.MediaFeed.episode_count > 0)
                 .order_by(models.MediaFeed.tier.asc(), models.MediaFeed.last_synced.desc())
                 .all())
        buckets = []
        seen_titles = set()
        seen_sources = {}  # name -> count, cap per source NAME not feed_id
        for feed in feeds:
            src_name = feed.name or 'unknown'
            if seen_sources.get(src_name, 0) >= MAX_PER_SOURCE:
                continue  # already have enough from this source name
            eps = (models.MediaEpisode.query
                   .filter_by(feed_id=feed.id)
                   .order_by(models.MediaEpisode.published_at.desc())
                   .limit(MAX_PER_SOURCE).all())
            bucket = []
            for ep in eps:
                key = (ep.title or '').lower().strip()[:50]
                if key not in seen_titles and ep.title and seen_sources.get(src_name, 0) < MAX_PER_SOURCE:
                    seen_titles.add(key)
                    seen_sources[src_name] = seen_sources.get(src_name, 0) + 1
                    bucket.append(ep_to_dict(ep))
            if bucket:
                buckets.append(bucket)
        result = []
        for i in range(MAX_PER_SOURCE):
            for bucket in buckets:
                if i < len(bucket) and len(result) < limit:
                    result.append(bucket[i])
        return result

    return {
        'podcasts': build_varied_list('rss', limit_per_col),
        'videos': build_varied_list('youtube', limit_per_col),
        'kol': _get_kol_items(limit_per_col),
    }




def _get_kol_items(limit: int = 20) -> List[dict]:
    import json as _json, os as _os, models
    items: List[dict] = []
    # Find project root by looking for data/ directory
    here = _os.path.abspath(_os.path.dirname(__file__))
    root = here
    for _ in range(4):
        candidate = _os.path.join(root, "data", "sovereign_context", "latest.json")
        if _os.path.exists(candidate):
            break
        root = _os.path.dirname(root)
    else:
        candidate = ""
    try:
        if not candidate or not _os.path.exists(candidate): raise FileNotFoundError(candidate)
        ctx = _json.load(open(candidate))
        ts = ctx.get("timestamp", "")[:10]
        btc = ctx.get("btc", {}) if isinstance(ctx.get("btc"), dict) else {}
        price = btc.get("price")
        change = float(btc.get("change_24h") or 0)
        if price:
            d2 = "bullish" if change > 0 else "bearish" if change < 0 else "neutral"
            items.append({"title": f"BTC ${float(price):,.0f} ({change:+.2f}%)", "excerpt": f"Bitcoin trading at ${float(price):,.0f}, {change:+.2f}% in 24 hours.", "source": "MARKET", "direction": d2, "timestamp": ts, "type": "signal"})
        fg = ctx.get("fear_greed", {}) if isinstance(ctx.get("fear_greed"), dict) else {}
        fgv = fg.get("value")
        fglabel = fg.get("label", "")
        if fgv is not None:
            fgv = int(fgv)
            fd = "bearish" if fgv<45 else "neutral" if fgv<55 else "bullish"
            items.append({"title": f"Fear & Greed: {fgv}/100", "excerpt": f"Market sentiment at {fgv}/100 - {fglabel}. Extreme fear historically signals accumulation opportunity.", "source": "SENTIMENT", "direction": fd, "timestamp": ts, "type": "signal"})
        net = ctx.get("network", {}) if isinstance(ctx.get("network"), dict) else {}
        hr = net.get("hashrate_eh")
        adj = net.get("next_adj_pct")
        if hr: items.append({"title": f"Hashrate: {float(hr):.0f} EH/s", "excerpt": f"Bitcoin network hashrate at {float(hr):.0f} EH/s" + (f". Next difficulty adj: {float(adj):+.2f}%." if adj else "."), "source": "NETWORK", "direction": "bullish", "timestamp": ts, "type": "signal"})
        ef = ctx.get("exchange_flow", "")
        if ef: items.append({"title": f"Exchange Flow: {str(ef).title()}", "excerpt": f"Net exchange flow: {ef}.", "source": "ON-CHAIN", "direction": "bullish" if "out" in str(ef).lower() else "bearish" if "in" in str(ef).lower() else "neutral", "timestamp": ts, "type": "signal"})
        whales = ctx.get("whale_alerts", [])
        if isinstance(whales, list) and whales: items.append({"title": f"{len(whales)} Whale Transactions", "excerpt": f"{len(whales)} large Bitcoin transactions detected.", "source": "WHALE WATCH", "direction": "neutral", "timestamp": ts, "type": "signal"})
        poly = ctx.get("polymarket", {}) if isinstance(ctx.get("polymarket"), dict) else {}
        prob = poly.get("top_probability")
        mkt = poly.get("top_market", "")
        if prob and mkt: items.append({"title": f"Polymarket: {float(prob):.1f}%", "excerpt": f"{mkt}: {float(prob):.1f}% probability.", "source": "POLYMARKET", "direction": "neutral", "timestamp": ts, "type": "signal"})
        macro = ctx.get("macro", {}) if isinstance(ctx.get("macro"), dict) else {}
        gold = macro.get("gold_price"); sp = macro.get("sp500")
        if gold or sp: items.append({"title": "Macro Snapshot", "excerpt": (f"Gold: ${float(gold):,.0f}. " if gold else "") + (f"S&P 500: {float(sp):,.0f}." if sp else ""), "source": "MACRO", "direction": "neutral", "timestamp": ts, "type": "signal"})
        options = ctx.get("options", {}) if isinstance(ctx.get("options"), dict) else {}
        pcr = options.get("put_call_ratio"); dvol = options.get("dvol"); mp = options.get("max_pain")
        if pcr: items.append({"title": f"Options: P/C {float(pcr):.3f}", "excerpt": f"Put/call ratio {float(pcr):.3f}" + (f", DVOL {float(dvol):.1f}%" if dvol else "") + (f", max pain ${float(mp):,.0f}" if mp else "") + ".", "source": "OPTIONS", "direction": "bearish" if pcr>0.9 else "neutral", "timestamp": ts, "type": "signal"})
        futures = ctx.get("futures", {}) if isinstance(ctx.get("futures"), dict) else {}
        fr = futures.get("funding_rate"); basis = futures.get("annualized_basis")
        if fr is not None: items.append({"title": f"Funding Rate: {float(fr)*100:.5f}%", "excerpt": f"Perpetual funding rate {float(fr)*100:.5f}%" + (f", annualized basis {float(basis):.2f}%" if basis else "") + ".", "source": "FUTURES", "direction": "bullish" if float(fr)<0 else "neutral" if abs(float(fr))<0.0001 else "bearish", "timestamp": ts, "type": "signal"})
        narrative = ctx.get("narrative", {}) if isinstance(ctx.get("narrative"), dict) else {}
        theme = narrative.get("dominant_theme", ""); sent = narrative.get("sentiment", "")
        if theme: items.append({"title": f"Narrative: {theme}", "excerpt": f"Dominant market narrative: {theme}. Overall sentiment: {sent}.", "source": "SOVEREIGN AI", "direction": sent if sent in ["bullish","bearish"] else "neutral", "timestamp": ts, "type": "signal"})
        stage = ctx.get("stage_brief", {}) if isinstance(ctx.get("stage_brief"), dict) else {}
        brief_text = stage.get("narrative", "")
        if brief_text and len(brief_text) > 30: items.append({"title": "Stage Brief", "excerpt": str(brief_text)[:250], "source": "STAGE", "direction": "neutral", "timestamp": ts, "type": "signal"})
    except Exception as e: logger.warning(f"[KOL] latest.json error: {e}")
    if len(items) < limit:
        try:
            arts = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(limit - len(items)).all()
            for a in arts:
                excerpt = (a.summary or a.content or "")[:180].strip()
                if excerpt: items.append({"title": a.title, "excerpt": excerpt, "source": "PROTOCOL PULSE", "direction": "neutral", "timestamp": (a.created_at.isoformat() if a.created_at else "")[:10], "type": "article", "slug": a.slug or f"article-{a.id}"})
        except Exception as e: logger.warning(f"[KOL] article fallback: {e}")
    return items[:limit]




def get_feed_stats() -> dict:
    import models
    try:
        total_feeds = models.MediaFeed.query.filter_by(active=True).count()
        total_eps = models.MediaEpisode.query.count()
        pod_eps = models.MediaEpisode.query.join(models.MediaFeed).filter(models.MediaFeed.feed_type=="rss").count()
        vid_eps = models.MediaEpisode.query.join(models.MediaFeed).filter(models.MediaFeed.feed_type=="youtube").count()
        return {"feed_count": total_feeds, "episode_count": total_eps, "podcast_count": pod_eps, "video_count": vid_eps}
    except Exception as e:
        logger.warning(f"get_feed_stats error: {e}")
        return {"feed_count": 0, "episode_count": 0, "podcast_count": 0, "video_count": 0}


class MediaFeedService:
    """Class wrapper around module-level functions for routes.py compatibility."""

    def __init__(self, app=None):
        self._app = app

    def sync_all_feeds(self, app=None):
        return sync_all_feeds(app or self._app)

    def sync_feeds_background(self, app=None):
        return sync_feeds_background(app or self._app)

    def get_feed_matrix(self, limit_per_col: int = 20) -> dict:
        return get_feed_matrix(limit_per_col)

    def get_ticker_items(self, limit: int = 30) -> List[dict]:
        return get_ticker_items(limit)

    def get_feed_stats(self) -> dict:
        return get_feed_stats()

    def generate_ai_summaries(self, app=None, batch_size: int = 20):
        return generate_ai_summaries(app or self._app, batch_size)

    def start_feed_polling(self, app=None):
        return start_feed_polling(app or self._app)

    @staticmethod
    def compute_signal_score(title, description, tier=2, published_at=None):
        return compute_signal_score(title, description, tier, published_at)


# ─── 15-MINUTE AUTO-POLL SCHEDULER ───────────────────────────────────────────

_poll_timer = None
_poll_started = False
POLL_INTERVAL = 15 * 60  # 15 minutes


def _poll_loop(app):
    """Recurring sync: runs every POLL_INTERVAL seconds."""
    global _poll_timer
    try:
        sync_all_feeds(app)
    except Exception as e:
        logger.error(f"[MediaPoll] Sync error: {e}")
    _poll_timer = threading.Timer(POLL_INTERVAL, _poll_loop, args=(app,))
    _poll_timer.daemon = True
    _poll_timer.start()


def start_feed_polling(app=None):
    """Start the 15-minute background feed polling loop. Safe to call multiple times."""
    global _poll_started
    if _poll_started:
        return
    _poll_started = True
    if app is None:
        from app import app as flask_app
        app = flask_app
    logger.info(f"[MediaPoll] Starting feed polling every {POLL_INTERVAL // 60}min")
    # Initial sync after 10s delay (let app finish startup)
    t = threading.Timer(10, _poll_loop, args=(app,))
    t.daemon = True
    t.start()
