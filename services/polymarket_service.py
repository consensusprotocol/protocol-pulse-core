"""
Polymarket Intelligence Service — Real-time prediction market data.
Free API, no auth required. Multi-search for Bitcoin/crypto/macro markets.
Feeds directly into Cross-Signal Divergence Engine.
"""
import requests, logging, json as _json
from datetime import datetime

logger = logging.getLogger('polymarket')

POLYMARKET_API = 'https://gamma-api.polymarket.com'

RELEVANT_TAGS = ['Crypto', 'Bitcoin', 'Fed', 'Economy', 'Geopolitics', 'US Politics']


def get_bitcoin_markets(limit=10):
    """Fetch active Polymarket markets relevant to Bitcoin/crypto/macro via multiple searches."""
    try:
        all_markets = {}

        # Multiple targeted searches
        queries = ['bitcoin', 'crypto', 'ethereum', 'fed rate', 'etf', 'recession',
                   'stablecoin', 'coinbase', 'inflation', 'tariff']

        for q in queries:
            try:
                resp = requests.get(
                    f'{POLYMARKET_API}/markets',
                    params={'limit': 20, 'active': 'true', 'closed': 'false', '_q': q},
                    timeout=6
                )
                if resp.ok:
                    for m in resp.json():
                        slug = m.get('slug', '')
                        if slug and slug not in all_markets:
                            all_markets[slug] = m
            except Exception:
                continue

        markets = list(all_markets.values())

        # Aggressive exclusion
        exclude = ['nba', 'nfl', 'mlb', 'nhl', 'fifa', 'world cup', 'champions league',
                   'premier league', 'serie a', 'soccer', 'football', 'basketball',
                   'jesus', 'rihanna', 'album', 'movie', 'oscar', 'grammy',
                   'super bowl', 'celebrity', 'kardashian', 'tiktok', 'convicted',
                   'carti', 'kanye', 'drake', 'taylor swift', 'beyonce',
                   'before gta', 'gta vi', 'gta 6']

        # Must contain at least one relevant term
        relevant = ['bitcoin', 'btc', 'crypto', 'ethereum', 'eth', 'defi', 'stablecoin',
                    'coinbase', 'binance', 'etf', 'halving', 'mining', 'blockchain',
                    'fed ', 'federal reserve', 'interest rate', 'rate cut', 'rate hike',
                    'inflation', 'recession', 'gdp', 'tariff', 'treasury', 'sec ',
                    'regulation', 'blackrock', 'saylor', 'microstrategy', 'digital asset',
                    'dollar', 'gold price', 'stock market']

        filtered = []
        for m in markets:
            q = m.get('question', '').lower()
            if any(x in q for x in exclude):
                continue
            if not any(r in q for r in relevant):
                continue
            filtered.append({
                'question': m.get('question', ''),
                'slug': m.get('slug', ''),
                'volume': float(m.get('volume', 0) or 0),
                'liquidity': float(m.get('liquidity', 0) or 0),
                'end_date': m.get('endDate', ''),
                'outcomes': _parse_outcomes(m),
            })

        filtered.sort(key=lambda x: x['volume'], reverse=True)
        return filtered[:limit]

    except Exception as e:
        logger.error(f'[Polymarket] Fetch failed: {e}')
        return []


def _parse_outcomes(market):
    """Extract Yes/No probabilities from market."""
    try:
        raw_names = market.get('outcomes', [])
        raw_prices = market.get('outcomePrices', [])
        if isinstance(raw_names, str):
            raw_names = _json.loads(raw_names)
        if isinstance(raw_prices, str):
            raw_prices = _json.loads(raw_prices)
        outcomes = {}
        for name, price_str in zip(raw_names, raw_prices):
            outcomes[name] = round(float(price_str or 0) * 100, 1)
        return outcomes
    except Exception:
        return {}


def get_macro_sentiment_score():
    """
    Derive a macro sentiment score (0-100) from Polymarket crypto markets.
    High score = market expects bullish macro (rate cuts, BTC ETF approval, etc)
    Low score = market expects bearish macro
    """
    try:
        markets = get_bitcoin_markets(20)
        if not markets:
            return 50

        bullish_signals = 0
        bearish_signals = 0

        for m in markets:
            outcomes = m.get('outcomes', {})
            q = m.get('question', '').lower()
            yes_prob = outcomes.get('Yes', 50)

            bullish_keywords = ['etf', 'approve', 'above', 'higher', 'rate cut',
                               'halving', 'saylor', 'blackrock', 'reach', 'exceed']
            bearish_keywords = ['below', 'crash', 'recession', 'ban', 'hike',
                               'fail', 'reject', 'regulation']

            is_bullish_question = any(k in q for k in bullish_keywords)
            is_bearish_question = any(k in q for k in bearish_keywords)

            weight = max(1, m['volume'] / 10000)

            if is_bullish_question:
                bullish_signals += (yes_prob / 100) * weight
            elif is_bearish_question:
                bearish_signals += (yes_prob / 100) * weight

        total = bullish_signals + bearish_signals
        if total == 0:
            return 50

        score = (bullish_signals / total) * 100
        return round(score)

    except Exception as e:
        logger.error(f'[Polymarket] Sentiment score failed: {e}')
        return 50


def get_top_market_by_volume():
    """Get single most-traded Bitcoin/crypto market for dashboard widget."""
    markets = get_bitcoin_markets(5)
    return markets[0] if markets else None
