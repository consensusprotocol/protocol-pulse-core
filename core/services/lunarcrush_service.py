"""
lunarcrush_service.py — LunarCrush social sentiment for Commander Hub.
Provides social intelligence: Bitcoin galaxy score, social volume, Alt Rank, trending posts.
Cached 15min (social data is fast-moving but does not need second-by-second polling).

Graceful degradation: when LUNARCRUSH_API_KEY is unset or the API is unreachable,
every getter returns {'available': False, 'source': 'lunarcrush', ...} — no crashes.
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

LUNAR_KEY = os.environ.get('LUNARCRUSH_API_KEY', '')
BASE = 'https://lunarcrush.com/api4/public'
CACHE_TTL = 900  # 15 minutes

_cache: dict = {}


def _get(path: str):
    """Call LunarCrush API with caching. Returns dict on success, None on any failure."""
    if not LUNAR_KEY:
        return None
    entry = _cache.get(path)
    if entry and (time.time() - entry['ts']) < CACHE_TTL:
        return entry['data']
    try:
        r = requests.get(
            f'{BASE}{path}',
            headers={'Authorization': f'Bearer {LUNAR_KEY}'},
            timeout=10,
        )
        if r.status_code == 200:
            d = r.json()
            _cache[path] = {'data': d, 'ts': time.time()}
            return d
        logger.warning('LunarCrush %s: %s', r.status_code, path)
        return None
    except Exception as e:
        logger.warning('LunarCrush error: %s', e)
        return None


def get_btc_social() -> dict:
    """Bitcoin social metrics: galaxy score, alt rank, social volume, sentiment."""
    d = _get('/coins/btc/v1')
    if not d:
        return {'available': False, 'source': 'lunarcrush'}
    coin = (d.get('data') or {})
    return {
        'galaxy_score':       coin.get('galaxy_score'),
        'alt_rank':           coin.get('alt_rank'),
        'social_volume_24h':  coin.get('social_volume_24h'),
        'social_engagement':  coin.get('social_engagement'),
        'sentiment':          coin.get('sentiment'),
        'social_dominance':   coin.get('social_dominance'),
        'source': 'lunarcrush',
        'available': True,
    }


def get_trending_topics() -> dict:
    """Top trending Bitcoin posts/topics on social right now."""
    d = _get('/topic/bitcoin/v1')
    if not d:
        return {'top_posts': [], 'available': False, 'source': 'lunarcrush'}
    posts = ((d.get('data') or {}).get('posts') or [])[:5]
    return {
        'top_posts': [
            {
                'title': p.get('title', '') or p.get('post_title', ''),
                'score': p.get('interactions_24h', 0) or p.get('interactions', 0),
            }
            for p in posts
        ],
        'available': True,
        'source': 'lunarcrush',
    }


def get_hub_widget_data() -> dict:
    """Single call returning all LunarCrush data for the Commander Hub widget."""
    return {
        'btc_social': get_btc_social(),
        'trending': get_trending_topics(),
        'source': 'lunarcrush',
        'available': bool(LUNAR_KEY),
    }
