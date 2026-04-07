"""
Pro On-Chain Metrics Service
Derives institutional-grade metrics from available data sources.
Falls back to CryptoQuant API when key is configured.

Metrics:
- SSR (Stablecoin Supply Ratio): BTC Market Cap / Stablecoin Market Cap
- MPI (Miner Position Index): approximated from CDD + hashrate trends
- Entity-adjusted metrics: derived from active addresses + NVT
"""
import os
import json
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger('pro_metrics')

BASE_DIR = Path(__file__).resolve().parent.parent
CONTEXT_PATH = Path('/home/ultron/protocol_pulse/data/sovereign_context/latest.json')
METRICS_CACHE = Path('/home/ultron/protocol_pulse/data/pro_metrics_cache.json')

CRYPTOQUANT_KEY = os.environ.get('CRYPTOQUANT_API_KEY', '')
HEADERS = {'User-Agent': 'ProtocolPulse/2.0'}


def _get_json(url, headers=None, timeout=8):
    try:
        r = requests.get(url, headers=headers or HEADERS, timeout=timeout)
        if r.ok:
            return r.json()
    except Exception as e:
        log.warning("GET %s failed: %s", url, e)
    return None


def _load_context():
    """Load latest sovereign context."""
    try:
        with open(CONTEXT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _load_cache():
    """Load cached metrics."""
    try:
        if METRICS_CACHE.exists():
            with open(METRICS_CACHE) as f:
                cache = json.load(f)
            # Cache valid for 10 minutes
            ts = cache.get('timestamp', '')
            if ts:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
                if age < 600:
                    return cache
    except Exception:
        pass
    return None


def _save_cache(metrics):
    """Save metrics cache."""
    try:
        metrics['timestamp'] = datetime.now(timezone.utc).isoformat()
        with open(METRICS_CACHE, 'w') as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# SSR — Stablecoin Supply Ratio
# ═══════════════════════════════════════════════════════════════════════

def _fetch_btc_mcap_direct():
    """Fetch BTC market cap directly from CoinGecko as fallback."""
    data = _get_json(
        'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_market_cap=true'
    )
    if data and 'bitcoin' in data:
        return data['bitcoin'].get('usd_market_cap', 0) or 0
    return 0


def fetch_ssr():
    """
    SSR = BTC Market Cap / Total Stablecoin Market Cap

    Low SSR (< 5) = massive stablecoin purchasing power relative to BTC = bullish
    High SSR (> 15) = BTC overvalued relative to available stablecoin liquidity = caution
    Normal range: 5-12
    """
    ctx = _load_context()
    btc_mcap = ctx.get('btc', {}).get('market_cap', 0) or 0

    # Fallback: fetch directly if latest.json is stale
    if not btc_mcap:
        btc_mcap = _fetch_btc_mcap_direct()

    if not btc_mcap:
        return None
    
    # Try CryptoQuant API first
    if CRYPTOQUANT_KEY:
        try:
            data = _get_json(
                'https://api.cryptoquant.com/v1/btc/market-data/stablecoin-supply-ratio',
                headers={'Authorization': f'Bearer {CRYPTOQUANT_KEY}', **HEADERS}
            )
            if data and 'result' in data:
                entries = data['result'].get('data', [])
                if entries:
                    return {
                        'value': round(entries[-1].get('ssr', 0), 2),
                        'source': 'cryptoquant',
                    }
        except Exception:
            pass
    
    # Derive from CoinGecko stablecoin market caps
    stable_mcap = 0

    # Try getting USDT + USDC market caps
    stable_data = _get_json(
        'https://api.coingecko.com/api/v3/simple/price?ids=tether,usd-coin,dai,first-digital-usd&vs_currencies=usd&include_market_cap=true'
    )
    if stable_data:
        for coin in ['tether', 'usd-coin', 'dai', 'first-digital-usd']:
            mcap = stable_data.get(coin, {}).get('usd_market_cap', 0)
            if mcap:
                stable_mcap += mcap
    
    # Fallback: use approximate known values if CoinGecko rate-limited
    if stable_mcap < 1e9:
        # Approximate stablecoin market cap (USDT ~$140B, USDC ~$45B, DAI ~$5B, others ~$15B)
        stable_mcap = 205_000_000_000  # ~$205B approximate
        source = 'estimated'
    else:
        source = 'coingecko_derived'
    
    ssr = btc_mcap / stable_mcap if stable_mcap > 0 else 0
    
    # Classify
    if ssr < 4:
        signal = 'VERY BULLISH'
        desc = 'Massive stablecoin dry powder relative to BTC — strong buying potential'
    elif ssr < 7:
        signal = 'BULLISH'
        desc = 'Healthy stablecoin reserves available for BTC purchasing'
    elif ssr < 12:
        signal = 'NEUTRAL'
        desc = 'Balanced stablecoin-to-BTC ratio'
    elif ssr < 18:
        signal = 'CAUTIOUS'
        desc = 'BTC market cap stretching relative to stablecoin liquidity'
    else:
        signal = 'BEARISH'
        desc = 'Very low stablecoin purchasing power relative to BTC — overextended'
    
    return {
        'value': round(ssr, 2),
        'btc_market_cap': btc_mcap,
        'stablecoin_market_cap': stable_mcap,
        'signal': signal,
        'description': desc,
        'source': source,
    }


# ═══════════════════════════════════════════════════════════════════════
# MPI — Miner Position Index
# ═══════════════════════════════════════════════════════════════════════

def fetch_mpi():
    """
    MPI approximation: are miners selling more than normal?
    
    Uses CDD (Coin Days Destroyed) as a proxy for old-coin selling behavior.
    When CDD is high relative to historical average, miners are likely distributing.
    
    MPI > 2: Heavy miner selling (bearish)
    MPI 0-2: Normal miner behavior
    MPI < 0: Miners accumulating (bullish)
    
    Real MPI = miner outflow / 365d MA(miner outflow)
    Our approximation: CDD_7d / baseline_CDD × hashrate_factor
    """
    ctx = _load_context()
    
    # Try CryptoQuant API first
    if CRYPTOQUANT_KEY:
        try:
            data = _get_json(
                'https://api.cryptoquant.com/v1/btc/miner-data/miner-position-index?window=day&limit=1',
                headers={'Authorization': f'Bearer {CRYPTOQUANT_KEY}', **HEADERS}
            )
            if data and 'result' in data:
                entries = data['result'].get('data', [])
                if entries:
                    return {
                        'value': round(entries[-1].get('mpi', 0), 3),
                        'source': 'cryptoquant',
                    }
        except Exception:
            pass
    
    # Derive from CDD + hashrate
    on_chain = ctx.get('on_chain', {})
    cdd_7d = on_chain.get('coin_days_destroyed_7d', 0) or 0
    network = ctx.get('network', {})
    hashrate = network.get('hashrate_eh', 0) or 0

    # Fallback: fetch CDD from Blockchair directly
    if not cdd_7d:
        bc = _get_json("https://api.blockchair.com/bitcoin/stats", timeout=12)
        if bc and "data" in bc:
            cdd_7d = bc["data"].get("cdd_24h", 0) or 0

    # Fallback: fetch hashrate from mempool.space
    if not hashrate:
        hr = _get_json("https://mempool.space/api/v1/mining/hashrate/3d", timeout=10)
        if hr and "currentHashrate" in hr:
            hashrate = round(float(hr["currentHashrate"]) / 1e18, 1)

    if not cdd_7d:
        return None
    
    # Baseline CDD (historical average ~5-8M per 7d in normal conditions)
    baseline_cdd = 6_000_000
    
    # CDD ratio: how much above/below normal
    cdd_ratio = cdd_7d / baseline_cdd if baseline_cdd > 0 else 1.0
    
    # Hashrate factor: higher hashrate = miners are healthy/accumulating
    # Normalize to ~1.0 at 1000 EH/s (current era)
    hashrate_factor = 1.0
    if hashrate > 0:
        hashrate_factor = min(1.2, max(0.8, 1000 / hashrate))
    
    # MPI approximation
    mpi = (cdd_ratio - 1.0) * hashrate_factor
    
    # Classify
    if mpi > 2.0:
        signal = 'BEARISH'
        desc = 'Heavy old-coin movement — miners likely distributing into strength'
    elif mpi > 0.5:
        signal = 'CAUTIOUS'
        desc = 'Above-average coin age destruction — some miner selling'
    elif mpi > -0.5:
        signal = 'NEUTRAL'
        desc = 'Normal miner behavior — no anomalous selling pattern'
    else:
        signal = 'BULLISH'
        desc = 'Low coin age destruction — miners holding/accumulating'
    
    return {
        'value': round(mpi, 3),
        'cdd_7d': cdd_7d,
        'cdd_ratio': round(cdd_ratio, 2),
        'hashrate_eh': hashrate,
        'signal': signal,
        'description': desc,
        'source': 'derived_cdd_hashrate',
    }


# ═══════════════════════════════════════════════════════════════════════
# DORMANCY FLOW (approximated)
# ═══════════════════════════════════════════════════════════════════════

def fetch_dormancy_flow():
    """
    Dormancy Flow = Market Cap / (CDD × Price)
    When high: market cap is large relative to spending of old coins = bullish
    When low: old coins are being spent aggressively = potential top
    """
    ctx = _load_context()
    btc = ctx.get('btc', {})
    on_chain = ctx.get('on_chain', {})

    price = btc.get('price', 0) or 0
    market_cap = btc.get('market_cap', 0) or 0
    cdd_7d = on_chain.get('coin_days_destroyed_7d', 0) or 0

    # Fallback: fetch price/mcap directly from CoinGecko
    if not price or not market_cap:
        data = _get_json(
            'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_market_cap=true'
        )
        if data and 'bitcoin' in data:
            if not price:
                price = data['bitcoin'].get('usd', 0) or 0
            if not market_cap:
                market_cap = data['bitcoin'].get('usd_market_cap', 0) or 0

    # Fallback: fetch CDD from Blockchair directly
    if not cdd_7d:
        bc = _get_json("https://api.blockchair.com/bitcoin/stats", timeout=12)
        if bc and "data" in bc:
            cdd_7d = bc["data"].get("cdd_24h", 0) or 0

    if not all([price, market_cap, cdd_7d]):
        return None
    
    # Daily CDD approximation
    cdd_daily = cdd_7d / 7
    
    # Dormancy flow
    denominator = cdd_daily * price
    if denominator <= 0:
        return None
    
    flow = market_cap / denominator
    
    # Classify (thresholds based on historical data)
    if flow > 1_000_000:
        signal = 'VERY BULLISH'
        desc = 'Extreme dormancy — old coins are NOT moving, strong hodl conviction'
    elif flow > 200_000:
        signal = 'BULLISH'
        desc = 'High dormancy flow — long-term holders are holding tight'
    elif flow > 50_000:
        signal = 'NEUTRAL'
        desc = 'Normal dormancy flow — balanced market behavior'
    else:
        signal = 'BEARISH'
        desc = 'Low dormancy flow — old coins moving aggressively, potential distribution'
    
    return {
        'value': round(flow, 0),
        'signal': signal,
        'description': desc,
        'source': 'derived',
    }


# ═══════════════════════════════════════════════════════════════════════
# MASTER FETCH — all pro metrics
# ═══════════════════════════════════════════════════════════════════════

def fetch_all_pro_metrics():
    """Fetch all professional on-chain metrics."""
    # Check cache first
    cached = _load_cache()
    if cached:
        return cached
    
    metrics = {
        'ssr': fetch_ssr(),
        'mpi': fetch_mpi(),
        'dormancy_flow': fetch_dormancy_flow(),
    }
    
    _save_cache(metrics)
    return metrics
