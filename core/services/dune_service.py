"""
dune_service.py — Dune Analytics integration for Commander Hub.
Provides on-chain intelligence: whale movements, accumulation signals, exchange flows.
Uses Dune's pre-built query results endpoint. Cached 30min (on-chain data is slow-moving).

Graceful degradation: when DUNE_API_KEY is unset or the API is unreachable,
every getter returns {'available': False, 'source': 'dune', ...} — no crashes.
"""
import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

DUNE_API_KEY = os.environ.get('DUNE_API_KEY', '')
DUNE_BASE = 'https://api.dune.com/api/v1'
CACHE_TTL = 1800  # 30 minutes

_cache: dict = {}


def _get(path: str, params: dict | None = None):
    """Call Dune API with caching. Returns dict on success, None on any failure."""
    if not DUNE_API_KEY:
        return None
    cache_key = path + repr(sorted((params or {}).items()))
    entry = _cache.get(cache_key)
    if entry and (time.time() - entry['ts']) < CACHE_TTL:
        return entry['data']
    try:
        r = requests.get(
            f'{DUNE_BASE}{path}',
            headers={'X-Dune-API-Key': DUNE_API_KEY},
            params=params or {},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            _cache[cache_key] = {'data': data, 'ts': time.time()}
            return data
        logger.warning('Dune API %s: %s', r.status_code, path)
        return None
    except Exception as e:
        logger.warning('Dune API error: %s', e)
        return None


def get_whale_movements(limit: int = 10) -> dict:
    """BTC transfers >$1M in last 24h. Returns transfers + total volume."""
    data = _get('/query/3295438/results', {'limit': limit})
    if not data:
        return {
            'transfers': [],
            'total_volume_usd': 0,
            'count': 0,
            'source': 'dune',
            'available': False,
        }
    rows = (data.get('result') or {}).get('rows', []) or []
    return {
        'transfers': rows[:limit],
        'total_volume_usd': sum((r.get('amount_usd') or 0) for r in rows),
        'count': len(rows),
        'source': 'dune',
        'available': True,
    }


def get_accumulation_signal() -> dict:
    """Addresses net-adding BTC in last 7d (accumulation vs distribution signal)."""
    data = _get('/query/2453430/results', {'limit': 5})
    if not data:
        return {
            'rows': [],
            'signal': 'unknown',
            'source': 'dune',
            'available': False,
        }
    rows = (data.get('result') or {}).get('rows', []) or []
    return {
        'rows': rows[:5],
        'signal': (rows[0].get('signal', 'neutral') if rows else 'neutral'),
        'source': 'dune',
        'available': True,
    }


def get_exchange_flows() -> dict:
    """BTC exchange net flow (7d). Positive = inflow (bearish), negative = outflow (bullish)."""
    data = _get('/query/2571822/results', {'limit': 1})
    if not data:
        return {
            'net_flow_btc': 0,
            'signal': 'neutral',
            'source': 'dune',
            'available': False,
        }
    rows = (data.get('result') or {}).get('rows', []) or []
    if not rows:
        return {
            'net_flow_btc': 0,
            'signal': 'neutral',
            'source': 'dune',
            'available': False,
        }
    flow = rows[0].get('net_flow_btc', 0) or 0
    return {
        'net_flow_btc': round(float(flow), 2),
        'signal': 'bearish' if flow > 1000 else ('bullish' if flow < -1000 else 'neutral'),
        'source': 'dune',
        'available': True,
    }


def get_hub_widget_data() -> dict:
    """Single call returning all Dune data for the Commander Hub widget."""
    return {
        'whale_movements': get_whale_movements(5),
        'exchange_flows': get_exchange_flows(),
        'accumulation': get_accumulation_signal(),
        'source': 'dune',
        'available': bool(DUNE_API_KEY),
    }
