"""
Polymarket Intelligence Service — Real-time prediction market data.
Free API, no auth required. Filters for Bitcoin/crypto/macro markets.
Feeds directly into Cross-Signal Divergence Engine.
"""
import requests, logging
from datetime import datetime

logger = logging.getLogger('polymarket')

POLYMARKET_API = 'https://gamma-api.polymarket.com'

# Bitcoin/macro relevant tags on Polymarket
RELEVANT_TAGS = ['Crypto', 'Bitcoin', 'Fed', 'Economy', 'Geopolitics', 'US Politics']

def get_bitcoin_markets(limit=10):
    """Fetch active Polymarket markets relevant to Bitcoin/macro."""
    try:
        # Search for crypto/bitcoin markets
        resp = requests.get(
            f'{POLYMARKET_API}/markets',
            params={
                'limit': 50,
                'active': 'true',
                'closed': 'false',
            },
            timeout=8
        )
        if not resp.ok:
            return []
        
        markets = resp.json()
        
        # Filter for relevant markets
        keywords = ['bitcoin', 'btc', 'crypto', 'fed', 'rate', 'inflation', 
                    'etf', 'halving', 'saylor', 'blackrock', 'recession', 'trump']
        
        filtered = []
        for m in markets:
            q = m.get('question', '').lower()
            if any(k in q for k in keywords):
                filtered.append({
                    'question': m.get('question', ''),
                    'slug': m.get('slug', ''),
                    'volume': float(m.get('volume', 0) or 0),
                    'liquidity': float(m.get('liquidity', 0) or 0),
                    'end_date': m.get('endDate', ''),
                    'outcomes': _parse_outcomes(m),
                })
        
        # Sort by volume descending
        filtered.sort(key=lambda x: x['volume'], reverse=True)
        return filtered[:limit]
    
    except Exception as e:
        logger.error(f'[Polymarket] Fetch failed: {e}')
        return []

def _parse_outcomes(market):
    """Extract Yes/No probabilities from market."""
    try:
        tokens = market.get('tokens', [])
        outcomes = {}
        for t in tokens:
            outcome = t.get('outcome', '')
            price = float(t.get('price', 0) or 0)
            outcomes[outcome] = round(price * 100, 1)  # Convert to %
        return outcomes
    except:
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
            return 50  # Neutral default
        
        bullish_signals = 0
        bearish_signals = 0
        
        for m in markets:
            outcomes = m.get('outcomes', {})
            q = m.get('question', '').lower()
            yes_prob = outcomes.get('Yes', 50)
            
            # Classify as bullish or bearish signal
            bullish_keywords = ['etf', 'approve', 'above', 'higher', 'rate cut', 
                               'halving', 'saylor', 'blackrock', 'reach', 'exceed']
            bearish_keywords = ['below', 'crash', 'recession', 'ban', 'hike',
                               'fail', 'reject', 'regulation']
            
            is_bullish_question = any(k in q for k in bullish_keywords)
            is_bearish_question = any(k in q for k in bearish_keywords)
            
            weight = max(1, m['volume'] / 10000)  # Weight by volume
            
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
