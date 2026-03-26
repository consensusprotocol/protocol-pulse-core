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
    {"name": "TFTC", "url": "https://feeds.simplecast.com/mGJ8uw1O", "host": "Marty Bent", "tier": 1, "color": "#ff6b35", "category": "podcast"},
    {"name": "Stephan Livera", "url": "https://feeds.simplecast.com/KV8z39iS", "host": "Stephan Livera", "tier": 1, "color": "#4a90d9", "category": "podcast"},
    {"name": "What Bitcoin Did", "url": "https://feeds.simplecast.com/tEJEubMT", "host": "Peter McCormack", "tier": 1, "color": "#f7931a", "category": "podcast"},
    {"name": "Bitcoin Audible", "url": "https://feeds.megaphone.fm/SWN4978045882", "host": "Guy Swann", "tier": 1, "color": "#9b59b6", "category": "podcast"},
    {"name": "The Bitcoin Layer", "url": "https://feeds.simplecast.com/BdGT7E3F", "host": "Nik Bhatia", "tier": 1, "color": "#3498db", "category": "podcast"},
    {"name": "Simply Bitcoin", "url": "https://feeds.simplecast.com/7V5b8Zag", "host": "Nico Moran", "tier": 2, "color": "#e74c3c", "category": "podcast"},
    {"name": "Bitcoin Magazine Podcast", "url": "https://feeds.megaphone.fm/bitcoin-magazine", "host": "Bitcoin Magazine", "tier": 1, "color": "#f7931a", "category": "podcast"},
    {"name": "Citadel Dispatch", "url": "https://feeds.simplecast.com/M6LkF8NN", "host": "Matt Odell", "tier": 1, "color": "#27ae60", "category": "podcast"},
    {"name": "Natalie Brunell", "url": "https://feeds.simplecast.com/6Z1iM0Fg", "host": "Natalie Brunell", "tier": 1, "color": "#e91e63", "category": "podcast"},
    {"name": "Rabbit Hole Recap", "url": "https://feeds.simplecast.com/Dh1oHsHZ", "host": "Marty Bent", "tier": 1, "color": "#ff6b35", "category": "podcast"},
    {"name": "Preston Pysh / TIP", "url": "https://feeds.simplecast.com/WXOL8WUD", "host": "Preston Pysh", "tier": 1, "color": "#2c3e50", "category": "podcast"},
]

YOUTUBE_CHANNELS = [
    {"name": "Bitcoin Magazine", "channel_id": "UCvRRgjjKvabNkSP0w3QdW3A", "tier": 1, "color": "#f7931a", "category": "video"},
    {"name": "Coin Bureau", "channel_id": "UCqK_GSMbpiV8spgD3ZGloSw", "tier": 1, "color": "#00d4aa", "category": "video"},
    {"name": "What Bitcoin Did", "channel_id": "UCBcRF18a7Qf58cCRy5xuWwQ", "tier": 1, "color": "#f7931a", "category": "video"},
    {"name": "Simply Bitcoin", "channel_id": "UCm7SUL4HMiM3UFEWP-E_Qhg", "tier": 2, "color": "#e74c3c", "category": "video"},
    {"name": "Robert Breedlove", "channel_id": "UCFmHIftfI9HRaL6r3zScKOg", "tier": 1, "color": "#1abc9c", "category": "video"},
    {"name": "Natalie Brunell", "channel_id": "UCIl1wX8yxEjkbCFBKbhAqeg", "tier": 1, "color": "#e91e63", "category": "video"},
    {"name": "Bitcoin Audible", "channel_id": "UCJz4rEsEHpx9ht7a5JIHh5g", "tier": 1, "color": "#9b59b6", "category": "video"},
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

    if api_key:
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
    else:
        # Fallback: try RSS (deprecated, may return 404)
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_config['channel_id']}"
        try:
            feed = _fetch_feed(url)
            for entry in feed.entries[:10]:
                title = entry.get('title', '').strip()
                if not title or is_excluded(title):
                    continue
                vid_id = entry.get('yt_videoid', '')
                pub_date = _parse_rss_date(entry)
                episodes.append({
                    'guid': vid_id or _make_guid(entry, url),
                    'title': title,
                    'description': _clean_html(entry.get('summary', '') or '')[:500],
                    'video_url': f"https://www.youtube.com/watch?v={vid_id}" if vid_id else entry.get('link', ''),
                    'source_url': entry.get('link', ''),
                    'thumbnail_url': f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg" if vid_id else None,
                    'duration': '',
                    'published_at': pub_date,
                    'signal_score': compute_signal_score(title, desc, channel_config.get('tier', 2), pub_date),
                })
        except Exception as e:
            logger.error(f"[YouTube] RSS fallback failed {channel_config['name']}: {e}")

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
    """Get three-column feed data for the Media Hub template."""
    import models

    # Podcasts — RSS episodes with audio
    podcasts = (
        models.MediaEpisode.query
        .join(models.MediaFeed)
        .filter(models.MediaFeed.feed_type == 'rss')
        .order_by(models.MediaEpisode.published_at.desc())
        .limit(limit_per_col)
        .all()
    )

    # Videos — YouTube episodes
    videos = (
        models.MediaEpisode.query
        .join(models.MediaFeed)
        .filter(models.MediaFeed.feed_type == 'youtube')
        .order_by(models.MediaEpisode.published_at.desc())
        .limit(limit_per_col)
        .all()
    )

    def ep_to_dict(ep):
        feed = ep.feed
        return {
            'id': ep.id,
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

    return {
        'podcasts': [ep_to_dict(ep) for ep in podcasts],
        'videos': [ep_to_dict(ep) for ep in videos],
    }


def get_ticker_items(limit: int = 30) -> List[dict]:
    """Get latest items across all feeds for the scrolling ticker."""
    import models

    items = (
        models.MediaEpisode.query
        .join(models.MediaFeed)
        .order_by(models.MediaEpisode.published_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for ep in items:
        feed = ep.feed
        icon = '🎙' if feed and feed.feed_type == 'rss' else '🎬'
        link = ep.source_url or ep.video_url or ep.audio_url or '#'
        result.append({
            'icon': icon,
            'title': ep.title,
            'source': feed.name if feed else '',
            'url': link,
            'score': ep.signal_score or 0,
            'time': _time_ago(ep.published_at) if ep.published_at else '',
        })

    return result


def get_feed_stats() -> dict:
    """Get aggregate stats for the hero section."""
    import models

    feed_count = models.MediaFeed.query.filter_by(active=True).count()
    episode_count = models.MediaEpisode.query.count()
    podcast_count = models.MediaEpisode.query.join(models.MediaFeed).filter(models.MediaFeed.feed_type == 'rss').count()
    video_count = models.MediaEpisode.query.join(models.MediaFeed).filter(models.MediaFeed.feed_type == 'youtube').count()

    return {
        'feed_count': feed_count,
        'episode_count': episode_count,
        'podcast_count': podcast_count,
        'video_count': video_count,
    }


def _time_ago(dt: datetime) -> str:
    """Human-readable time ago string."""
    if not dt:
        return ''
    diff = datetime.utcnow() - dt
    secs = int(diff.total_seconds())
    if secs < 60:
        return 'now'
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


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
