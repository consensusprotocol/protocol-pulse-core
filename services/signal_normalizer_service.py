"""
Signal Normalizer Service — Three Core Proprietary Indices
==========================================================
Reads from signals_raw + existing data sources (signals.json, sovereign_context).
Writes scored signals to signals_normalized table.

Indices:
  1. MinerConviction (MCX) — miner behavior under stress
  2. ExchangePressure (EPX) — exchange absorption vs distribution
  3. InsiderHeat (IHX) — political/insider salience

All formulas are deterministic and explainable.
No LLM in the scoring loop. Every score has drivers + counterweights.

Usage:
    from services.signal_normalizer_service import SignalNormalizer
    normalizer = SignalNormalizer()
    normalizer.compute_all()

Cron: */5 * * * * cd ~/protocol_pulse && python3 services/signal_normalizer_service.py
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("signal_normalizer")

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
SIGNALS_PATH = BASE_DIR / "data" / "signals.json"
CONTEXT_PATH = BASE_DIR / "data" / "sovereign_context" / "latest.json"

# ── Helpers ────────────────────────────────────────────────────────────────

def _clamp(val, lo=0.0, hi=100.0):
    return max(lo, min(hi, val))


def _safe_get(d, *keys, default=None):
    """Nested dict access: _safe_get(d, 'a', 'b') → d['a']['b']"""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d if d is not None else default


def _load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def _direction(score):
    if score >= 60:
        return 1
    elif score < 40:
        return -1
    return 0


def _state_label(score):
    if score >= 80:
        return "extreme"
    elif score >= 60:
        return "elevated"
    elif score >= 40:
        return "neutral"
    elif score >= 20:
        return "low"
    return "very_low"


# ═══════════════════════════════════════════════════════════════════════════
# MinerConviction (MCX)
# ═══════════════════════════════════════════════════════════════════════════

def compute_miner_conviction(signals: dict, context: dict) -> dict:
    """
    Detect whether miners are accumulating, distributing, or under stress.
    
    High MCX = miners expanding despite weak tape (generational bottom signal).
    Low MCX = miners capitulating (distribution / forced selling).
    
    Inputs:
      - hashrate (mempool.space / blockchain.com)
      - difficulty adjustment (mempool.space)
      - miner-to-exchange flows (sovereign_context on_chain)
      - fee share (mempool fees vs subsidy)
      - price change (CoinGecko)
    """
    drivers = []
    counterweights = []
    features = {}
    raw_ids = []

    # --- Sub-metric 1: Hashrate trend ---
    hashrate_eh = _safe_get(signals, 'hashrate', 'raw_eh', default=0)
    # We don't have 7d change directly, but we have the current value
    # Use difficulty adjustment as a proxy for hashrate growth
    diff_adj_pct = _safe_get(signals, 'difficulty_adjustment', 'percent', default=0)
    features['difficulty_next_adj_pct'] = diff_adj_pct
    features['hashrate_eh'] = hashrate_eh

    hashrate_score = _clamp(50 + 2.5 * float(diff_adj_pct))
    if diff_adj_pct > 3:
        drivers.append(f"Difficulty adjustment +{diff_adj_pct:.1f}% (hashrate growing)")
    elif diff_adj_pct < -3:
        counterweights.append(f"Difficulty adjustment {diff_adj_pct:.1f}% (hashrate declining)")

    # --- Sub-metric 2: Miner reserve / on-chain accumulation ---
    accumulation_score_raw = _safe_get(context, 'on_chain', 'accumulation_score', default=50)
    features['accumulation_score'] = accumulation_score_raw
    reserve_score = _clamp(float(accumulation_score_raw))
    if accumulation_score_raw > 60:
        drivers.append(f"On-chain accumulation score {accumulation_score_raw}")
    elif accumulation_score_raw < 40:
        counterweights.append(f"On-chain accumulation weak ({accumulation_score_raw})")

    # --- Sub-metric 3: Distribution pressure (coin days destroyed) ---
    cdd_7d = _safe_get(context, 'on_chain', 'coin_days_destroyed_7d', default=0)
    features['coin_days_destroyed_7d'] = cdd_7d
    # High CDD = old coins moving = potential distribution = bearish for conviction
    # Normalize against typical range (rough: 5M-50M)
    outflow_score = _clamp(100 - ((float(cdd_7d) - 5_000_000) / 45_000_000) * 100) if cdd_7d else 50
    if cdd_7d and float(cdd_7d) > 30_000_000:
        counterweights.append(f"Coin days destroyed elevated ({cdd_7d:,.0f})")
    elif cdd_7d and float(cdd_7d) < 10_000_000:
        drivers.append("Old coins dormant (low CDD)")

    # --- Sub-metric 4: Fee economics ---
    fee_high = _safe_get(signals, 'recommended_fees', 'fastest', default=0)
    features['fee_fastest_sat_vb'] = fee_high
    # Higher fees = more demand = bullish for miners
    fee_score = _clamp(20 + float(fee_high) * 0.8)  # 0-100 sat/vB maps roughly
    if fee_high and float(fee_high) > 50:
        drivers.append(f"Fee pressure elevated ({fee_high} sat/vB)")

    # --- Sub-metric 5: Price context (stress bonus) ---
    price_change_24h = _safe_get(signals, 'btc_price', 'change_24h', default=0)
    price_change_7d = _safe_get(context, 'btc', 'change_7d', default=0)
    features['price_change_24h'] = price_change_24h
    features['price_change_7d'] = price_change_7d

    # Stress bonus: miners expanding while price drops = high conviction
    stress_bonus = 0
    if float(price_change_7d or 0) < -3 and float(diff_adj_pct) > 0:
        stress_bonus = 8
        drivers.append(f"Miners expanding despite -{abs(float(price_change_7d)):.1f}% price (stress resilience)")

    # --- FINAL FORMULA ---
    # Weights: hashrate 0.22, reserve 0.20, distribution 0.18, fee 0.08, hashrate_econ 0.14
    # + 0.18 for general on-chain health
    hashprice_score = _clamp(50 + float(price_change_7d or 0) * 1.5)
    features['hashprice_score'] = hashprice_score

    raw_score = (
        0.22 * hashrate_score +
        0.20 * reserve_score +
        0.18 * outflow_score +
        0.08 * fee_score +
        0.14 * hashprice_score +
        0.18 * _clamp(accumulation_score_raw)
        + stress_bonus
    )
    score = _clamp(raw_score)

    # Build explanation
    explanation = {
        "headline": _mcx_headline(score, drivers, counterweights),
        "drivers": drivers if drivers else ["No strong bullish miner signals"],
        "counterweights": counterweights if counterweights else ["No significant headwinds"],
    }

    return {
        "signal_key": "miner_conviction",
        "signal_family": "miner",
        "score": round(score, 2),
        "raw_value": round(raw_score, 4),
        "direction": _direction(score),
        "state_label": _state_label(score),
        "confidence": _mcx_confidence(features),
        "features": features,
        "explanation": explanation,
        "raw_ids": raw_ids,
        "sample_size": sum(1 for v in features.values() if v),
    }


def _mcx_headline(score, drivers, counterweights):
    if score >= 75:
        return "Miners expanding with high conviction"
    elif score >= 60:
        return "Miner behavior constructive"
    elif score >= 40:
        return "Miner signals mixed"
    elif score >= 25:
        return "Miner stress indicators elevated"
    return "Miner capitulation risk"


def _mcx_confidence(features):
    """Confidence based on data coverage."""
    filled = sum(1 for v in features.values() if v is not None and v != 0)
    total = len(features)
    base = filled / total if total > 0 else 0.3
    return round(min(0.95, max(0.05, base)), 2)


# ═══════════════════════════════════════════════════════════════════════════
# ExchangePressure (EPX)
# ═══════════════════════════════════════════════════════════════════════════

def compute_exchange_pressure(signals: dict, context: dict) -> dict:
    """
    Detect whether exchanges are absorbing BTC or acting as distribution venues.
    
    High EPX = supply tightening (BTC leaving exchanges, stablecoins entering).
    Low EPX = distribution heavy (BTC flooding exchanges, sell pressure).
    
    Inputs:
      - exchange volume (CoinGecko / signals.json)
      - whale moves (signals.json)
      - funding rate / open interest (Deribit / Binance)
      - stablecoin context (sovereign_context)
      - fear & greed (sentiment proxy)
    """
    drivers = []
    counterweights = []
    features = {}

    # --- Sub-metric 1: Funding rate (derivatives pressure) ---
    funding = _safe_get(context, 'futures', 'funding_rate', default=0)
    features['funding_rate'] = funding
    # Positive funding = longs paying shorts = bullish bias
    # Very high funding = overheated = bearish
    funding_val = float(funding or 0)
    if abs(funding_val) < 0.001:
        funding_score = 50  # neutral
    elif funding_val > 0.03:
        funding_score = 25  # overheated
        counterweights.append(f"Funding rate elevated ({funding_val:.4f})")
    elif funding_val > 0:
        funding_score = 65  # mildly bullish
        drivers.append(f"Positive funding ({funding_val:.4f})")
    else:
        funding_score = 70  # negative funding = bearish sentiment = contrarian bullish
        drivers.append(f"Negative funding rate ({funding_val:.4f}) — bearish crowd positioning")

    # --- Sub-metric 2: Open interest ---
    oi_btc = _safe_get(context, 'futures', 'open_interest', default=0)
    features['open_interest_btc'] = oi_btc
    oi_score = 50  # neutral default
    if oi_btc:
        # High OI with negative funding = squeeze potential
        if float(oi_btc) > 100000 and funding_val < 0:
            oi_score = 75
            drivers.append("High OI with negative funding — squeeze setup")

    # --- Sub-metric 3: Whale activity ---
    whale_count = _safe_get(signals, 'whale_moves', 'count', default=0)
    whale_btc = _safe_get(signals, 'whale_moves', 'total_btc', default=0)
    features['whale_tx_count'] = whale_count
    features['whale_total_btc'] = whale_btc
    # More whale moves could be accumulation or distribution
    # Use fear & greed as context: whale moves during fear = accumulation
    fg_value = int(_safe_get(signals, 'fear_greed', 'value', default=50))
    features['fear_greed'] = fg_value

    if whale_count and int(whale_count) > 5 and fg_value < 30:
        whale_score = 80
        drivers.append(f"Whale accumulation during fear (F&G: {fg_value})")
    elif whale_count and int(whale_count) > 10 and fg_value > 70:
        whale_score = 30
        counterweights.append(f"Elevated whale moves during greed (potential distribution)")
    else:
        whale_score = 55

    # --- Sub-metric 4: Options put/call ratio ---
    pcr = _safe_get(context, 'options', 'put_call_ratio', default=None)
    features['put_call_ratio'] = pcr
    if pcr and float(pcr) > 0:
        pcr_val = float(pcr)
        # High PCR = more puts = bearish hedging = contrarian bullish
        if pcr_val > 0.7:
            pcr_score = 70
            drivers.append(f"Elevated put/call ratio ({pcr_val:.2f}) — hedging activity")
        elif pcr_val < 0.3:
            pcr_score = 35
            counterweights.append(f"Low put/call ratio ({pcr_val:.2f}) — complacency")
        else:
            pcr_score = 50
    else:
        pcr_score = 50

    # --- Sub-metric 5: Exchange volume context ---
    binance_vol = _safe_get(signals, 'exchange_volume', 'binance_btc', default=0)
    coinbase_vol = _safe_get(signals, 'exchange_volume', 'coinbase_btc', default=0)
    features['exchange_volume_btc'] = float(binance_vol or 0) + float(coinbase_vol or 0)
    vol_score = 50  # neutral without historical baseline

    # --- Sub-metric 6: Long/short ratio ---
    ls_ratio = _safe_get(context, 'futures', 'long_short_ratio', default=None)
    features['long_short_ratio'] = ls_ratio
    if ls_ratio and float(ls_ratio) > 0:
        ls_val = float(ls_ratio)
        if ls_val > 2.0:
            ls_score = 35  # crowded longs = risky
            counterweights.append(f"Long/short ratio crowded ({ls_val:.2f})")
        elif ls_val < 0.8:
            ls_score = 72  # more shorts than longs = contrarian bullish
            drivers.append(f"Short-heavy positioning ({ls_val:.2f})")
        else:
            ls_score = 50
    else:
        ls_score = 50

    # --- FINAL FORMULA ---
    raw_score = (
        0.22 * funding_score +
        0.12 * oi_score +
        0.25 * whale_score +
        0.15 * pcr_score +
        0.10 * vol_score +
        0.16 * ls_score
    )
    score = _clamp(raw_score)

    explanation = {
        "headline": _epx_headline(score),
        "drivers": drivers if drivers else ["Exchange flows neutral"],
        "counterweights": counterweights if counterweights else ["No significant sell pressure"],
    }

    return {
        "signal_key": "exchange_pressure",
        "signal_family": "exchange",
        "score": round(score, 2),
        "raw_value": round(raw_score, 4),
        "direction": _direction(score),
        "state_label": _state_label(score),
        "confidence": _epx_confidence(features),
        "features": features,
        "explanation": explanation,
        "raw_ids": [],
        "sample_size": sum(1 for v in features.values() if v is not None and v != 0),
    }


def _epx_headline(score):
    if score >= 75:
        return "Exchange pressure easing — supply tightening"
    elif score >= 60:
        return "Exchange flows constructive"
    elif score >= 40:
        return "Exchange pressure mixed"
    elif score >= 25:
        return "Distribution pressure building"
    return "Heavy distribution — sell pressure dominant"


def _epx_confidence(features):
    filled = sum(1 for v in features.values() if v is not None and v != 0)
    total = len(features)
    return round(min(0.92, max(0.05, filled / total)), 2)


# ═══════════════════════════════════════════════════════════════════════════
# InsiderHeat (IHX)
# ═══════════════════════════════════════════════════════════════════════════

def compute_insider_heat(signals: dict, context: dict) -> dict:
    """
    Detect clustering of insider/political activity around BTC-adjacent assets.
    
    High IHX = elevated insider/policy heat (risk or opportunity).
    Low IHX = quiet insider environment.
    
    Inputs:
      - Polymarket probabilities (sovereign_context)
      - Narrative momentum (sovereign_context)
      - Active alerts / pattern matches (sovereign_context)
      - Fear & Greed as context
    
    Note: STOCK Act disclosure data will be wired separately via
    panopticon_service when that feed is production-stable.
    """
    drivers = []
    counterweights = []
    features = {}

    # --- Sub-metric 1: Polymarket probability ---
    poly_prob = _safe_get(context, 'polymarket', 'top_probability', default=None)
    poly_market = _safe_get(context, 'polymarket', 'top_market', default="unknown")
    poly_sentiment = _safe_get(context, 'polymarket', 'macro_sentiment', default="neutral")
    features['polymarket_probability'] = poly_prob
    features['polymarket_sentiment'] = poly_sentiment

    if poly_prob and float(poly_prob) > 0:
        prob_val = float(poly_prob)
        # High probability on BTC-relevant market = insider alignment
        poly_score = _clamp(prob_val * 100) if prob_val < 1 else _clamp(prob_val)
        if prob_val > 0.7 or prob_val > 70:
            drivers.append(f"Prediction market conviction high: {poly_market} ({prob_val})")
        elif prob_val < 0.3 or (prob_val < 30 and prob_val > 1):
            counterweights.append(f"Prediction market unconvinced ({prob_val})")
    else:
        poly_score = 50

    # --- Sub-metric 2: Narrative momentum ---
    narrative_sentiment = _safe_get(context, 'narrative', 'sentiment', default="neutral")
    article_count = _safe_get(context, 'narrative', 'article_count', default=0)
    features['narrative_sentiment'] = narrative_sentiment
    features['article_count'] = article_count

    sentiment_map = {"very_bullish": 85, "bullish": 70, "neutral": 50, "bearish": 30, "very_bearish": 15}
    narrative_score = sentiment_map.get(str(narrative_sentiment), 50)
    if int(article_count or 0) > 10:
        narrative_score = min(100, narrative_score + 10)
        drivers.append(f"High article volume ({article_count}) with {narrative_sentiment} sentiment")

    # --- Sub-metric 3: Active alerts / patterns ---
    active_alerts = _safe_get(context, 'active_alerts', default=[])
    pattern_matches = _safe_get(context, 'pattern_matches', default=[])
    features['active_alert_count'] = len(active_alerts) if isinstance(active_alerts, list) else 0
    features['pattern_match_count'] = len(pattern_matches) if isinstance(pattern_matches, list) else 0

    alert_score = _clamp(40 + len(active_alerts) * 10 + len(pattern_matches) * 8)
    if len(active_alerts) > 2:
        drivers.append(f"{len(active_alerts)} active intelligence alerts")
    if len(pattern_matches) > 1:
        drivers.append(f"{len(pattern_matches)} historical pattern matches detected")

    # --- Sub-metric 4: KOL sentiment divergence ---
    kol_sentiment = _safe_get(context, 'kol', 'sentiment_score', default=50)
    kol_post_count = _safe_get(context, 'kol', 'post_count_24h', default=0)
    features['kol_sentiment'] = kol_sentiment
    features['kol_post_count_24h'] = kol_post_count

    kol_score = _clamp(float(kol_sentiment or 50))
    if int(kol_post_count or 0) > 100 and float(kol_sentiment or 50) > 70:
        drivers.append(f"KOL cluster bullish ({kol_sentiment}) with high activity ({kol_post_count} posts)")
    elif int(kol_post_count or 0) > 50 and float(kol_sentiment or 50) < 30:
        counterweights.append(f"KOL cluster bearish ({kol_sentiment})")

    # --- Sub-metric 5: Fear & Greed context ---
    fg = int(_safe_get(signals, 'fear_greed', 'value', default=50))
    features['fear_greed'] = fg
    # Extreme fear + bullish insiders = highest insider heat signal
    fg_score = 50
    if fg < 20:
        fg_score = 75  # fear creates divergence opportunity
        drivers.append(f"Extreme fear (F&G: {fg}) — potential insider divergence")
    elif fg > 80:
        fg_score = 30
        counterweights.append(f"Extreme greed (F&G: {fg}) — caution warranted")

    # --- FINAL FORMULA ---
    raw_score = (
        0.24 * poly_score +
        0.20 * narrative_score +
        0.18 * alert_score +
        0.22 * kol_score +
        0.16 * fg_score
    )
    score = _clamp(raw_score)

    explanation = {
        "headline": _ihx_headline(score),
        "drivers": drivers if drivers else ["Insider environment quiet"],
        "counterweights": counterweights if counterweights else ["No significant policy risk"],
        "disclaimer": "Pattern detection, not misconduct allegation",
    }

    return {
        "signal_key": "insider_heat",
        "signal_family": "insider",
        "score": round(score, 2),
        "raw_value": round(raw_score, 4),
        "direction": _direction(score),
        "state_label": _state_label(score),
        "confidence": _ihx_confidence(features),
        "features": features,
        "explanation": explanation,
        "raw_ids": [],
        "sample_size": sum(1 for v in features.values() if v is not None and v != 0),
    }


def _ihx_headline(score):
    if score >= 75:
        return "Insider heat elevated — high policy/narrative activity"
    elif score >= 60:
        return "Insider signals active"
    elif score >= 40:
        return "Insider environment neutral"
    elif score >= 25:
        return "Insider signals subdued"
    return "Insider heat quiet — low policy activity"


def _ihx_confidence(features):
    filled = sum(1 for v in features.values() if v is not None and v != 0)
    total = len(features)
    return round(min(0.88, max(0.05, filled / total)), 2)


# ═══════════════════════════════════════════════════════════════════════════
# Main Normalizer Class
# ═══════════════════════════════════════════════════════════════════════════

class SignalNormalizer:
    """Compute all three core signals and persist to DB."""

    def __init__(self):
        self.signals = _load_json(SIGNALS_PATH)
        self.context = _load_json(CONTEXT_PATH)

    def reload_data(self):
        self.signals = _load_json(SIGNALS_PATH)
        self.context = _load_json(CONTEXT_PATH)

    def compute_all(self) -> List[dict]:
        """Compute all three indices. Returns list of result dicts."""
        self.reload_data()
        results = []

        for compute_fn in [compute_miner_conviction, compute_exchange_pressure, compute_insider_heat]:
            try:
                result = compute_fn(self.signals, self.context)
                results.append(result)
                log.info(
                    "%s: %.1f (%s, dir=%d, conf=%.2f)",
                    result['signal_key'], result['score'],
                    result['state_label'], result['direction'], result['confidence']
                )
            except Exception as e:
                log.error("Failed computing %s: %s", compute_fn.__name__, e)

        return results

    def compute_and_persist(self):
        """Compute all signals and write to signals_normalized table."""
        # Lazy import to avoid circular deps
        sys.path.insert(0, str(BASE_DIR / "core"))
        import sys as _sys2; _sys2.path.insert(0, str(BASE_DIR / "core")); from app import app, db as flask_db
        from models_intelligence import SignalNormalized as SNModel

        results = self.compute_all()
        now = datetime.utcnow()

        with app.app_context():
            for r in results:
                entry = SNModel(
                    id=str(uuid.uuid4()),
                    signal_key=r['signal_key'],
                    signal_family=r['signal_family'],
                    computed_at=now,
                    window_start=now - timedelta(hours=1),
                    window_end=now,
                    raw_value=r['raw_value'],
                    score_0_100=r['score'],
                    direction=r['direction'],
                    confidence=r['confidence'],
                    freshness_seconds=0,  # will be recomputed from raw event age
                    sample_size=r['sample_size'],
                    features_json=json.dumps(r['features']),
                    contributing_raw_ids_json=json.dumps(r.get('raw_ids', [])),
                    explanation_json=json.dumps(r['explanation']),
                    state_label=r['state_label'],
                    regime_direction="bullish" if r['direction'] == 1 else "bearish" if r['direction'] == -1 else "neutral",
                )
                flask_db.session.add(entry)

            flask_db.session.commit()
            log.info("Persisted %d normalized signals", len(results))

        return results


# ═══════════════════════════════════════════════════════════════════════════
# Convergence Computer
# ═══════════════════════════════════════════════════════════════════════════

def compute_convergence(signals_list: List[dict]) -> dict:
    """
    Compute convergence state from a list of normalized signal results.
    
    Convergence = weighted agreement across signals.
    Fragmentation = disagreement / entropy.
    """
    if not signals_list:
        return {"convergence_score": 0, "error": "no signals"}

    scores = [s['score'] for s in signals_list]
    directions = [s['direction'] for s in signals_list]
    confidences = [s['confidence'] for s in signals_list]

    # Agreement: how many signals push same direction
    bullish = sum(1 for d in directions if d == 1)
    bearish = sum(1 for d in directions if d == -1)
    total = len(directions)

    max_aligned = max(bullish, bearish)
    agreement = max_aligned / total if total > 0 else 0

    # Dispersion: standard deviation of scores
    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = variance ** 0.5
    dispersion = min(1.0, std_dev / 50)  # normalize

    # Mean confidence
    mean_conf = sum(confidences) / len(confidences)

    # Participation rate
    participation = total / max(total, 3)  # dynamic: denominator = max(actual, 3 minimum)

    # Convergence formula (all 4 LLMs agreed on this structure)
    convergence = 100 * (
        0.45 * agreement +
        0.20 * mean_conf +
        0.20 * (1 - dispersion) +
        0.15 * participation
    )
    convergence = _clamp(convergence)

    fragmentation = _clamp(dispersion * 100)
    momentum = _clamp(mean_score)
    conviction = _clamp(convergence * mean_conf)

    # Determine dominant thesis
    aligned = [s for s in signals_list if s['direction'] == (1 if bullish >= bearish else -1)]
    conflicting = [s for s in signals_list if s not in aligned]
    dominant_dir = 1 if bullish >= bearish else -1 if bearish > bullish else 0

    # Thesis key
    if dominant_dir == 1 and any(s['signal_key'] == 'miner_conviction' and s['score'] > 65 for s in aligned):
        thesis_key = "miner_absorption_under_fear"
        thesis_label = "Miner absorption under fear"
    elif dominant_dir == -1:
        thesis_key = "distribution_risk"
        thesis_label = "Distribution risk elevated"
    elif agreement > 0.7:
        thesis_key = "broad_alignment"
        thesis_label = "Broad cross-domain alignment"
    else:
        thesis_key = "mixed_regime"
        thesis_label = "Mixed signals — no dominant thesis"

    # Explainability
    driver_headlines = [s['explanation']['headline'] for s in aligned if 'explanation' in s]
    counter_headlines = [s['explanation']['headline'] for s in conflicting if 'explanation' in s]

    # Alerts
    alerts = []
    if convergence > 85:
        alerts.append({"key": "convergence_alert", "severity": "high", "label": f"{max_aligned} domains converging"})
    elif convergence > 65:
        alerts.append({"key": "convergence_watch", "severity": "watch", "label": f"{max_aligned} domains aligned"})

    # UI payload for graph/orb
    import math
    nodes = []
    for i, s in enumerate(signals_list):
        theta = i * (2 * math.pi / len(signals_list))
        distance = (100 - s['score']) / 100  # higher score = closer to center
        nodes.append({
            "id": s['signal_key'],
            "label": s['signal_family'].capitalize(),
            "family": s['signal_family'],
            "score": s['score'],
            "direction": s['direction'],
            "confidence": s['confidence'],
            "x": round(distance * math.cos(theta), 4),
            "y": round(distance * math.sin(theta), 4),
            "radius": round(10 + s['confidence'] * 10, 1),
            "distance_to_center": round(distance, 4),
            "status": "aligned" if s in aligned else "conflicting",
            "headline": s['explanation'].get('headline', ''),
        })

    # Edges (pairwise agreement)
    edges = []
    for i, s1 in enumerate(signals_list):
        for j, s2 in enumerate(signals_list):
            if i >= j:
                continue
            weight = 1.0 - abs(s1['score'] - s2['score']) / 100
            relation = "agreement" if s1['direction'] == s2['direction'] else "disagreement"
            edges.append({
                "source": s1['signal_key'],
                "target": s2['signal_key'],
                "weight": round(weight, 3),
                "relation": relation,
            })

    return {
        "convergence_score": round(convergence, 2),
        "fragmentation_score": round(fragmentation, 2),
        "momentum_score": round(momentum, 2),
        "conviction_score": round(conviction, 2),
        "dominant_thesis_key": thesis_key,
        "dominant_thesis_label": thesis_label,
        "dominant_direction": dominant_dir,
        "confidence": round(mean_conf, 3),
        "aligned_signals": [s['signal_key'] for s in aligned],
        "conflicting_signals": [s['signal_key'] for s in conflicting],
        "alerts": alerts,
        "explainability": {
            "headline": thesis_label,
            "drivers": driver_headlines,
            "counterweights": counter_headlines,
        },
        "ui_payload": {
            "layout_mode": "force_graph",
            "nodes": nodes,
            "edges": edges,
            "center": {"thesis_key": thesis_key, "label": thesis_label, "score": round(convergence, 1)},
        },
        "regime_label": thesis_key,
        "participating_signals": total,
        "total_expected_signals": max(total, 3),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Verification
# ═══════════════════════════════════════════════════════════════════════════

def verify_engine():
    """Regression test — must pass before any commit."""
    normalizer = SignalNormalizer()
    results = normalizer.compute_all()
    for r in results:
        assert 0 <= r['score'] <= 100, f"{r['signal_key']} score out of bounds: {r['score']}"
        assert r['direction'] in (-1, 0, 1), f"{r['signal_key']} invalid direction"
        assert 0 <= r['confidence'] <= 1, f"{r['signal_key']} confidence out of bounds"
        assert r['explanation']['headline'], f"{r['signal_key']} missing headline"
        assert r['features'], f"{r['signal_key']} missing features"
    log.info("VERIFICATION PASSED: All %d signals valid", len(results))

    # Test convergence
    conv = compute_convergence(results)
    assert 0 <= conv['convergence_score'] <= 100, "Convergence out of bounds"
    assert conv['ui_payload']['nodes'], "Missing graph nodes"
    log.info("VERIFICATION PASSED: Convergence engine valid (score=%.1f)", conv['convergence_score'])

    return results, conv


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results, conv = verify_engine()
    print(f"\n=== SIGNAL SCORES ===")
    for r in results:
        print(f"  {r['signal_key']}: {r['score']:.1f} ({r['state_label']}, dir={r['direction']}, conf={r['confidence']:.2f})")
        print(f"    → {r['explanation']['headline']}")
    print(f"\n=== CONVERGENCE ===")
    print(f"  Score: {conv['convergence_score']:.1f}")
    print(f"  Thesis: {conv['dominant_thesis_label']}")
    print(f"  Aligned: {conv['aligned_signals']}")
    print(f"  Conflicting: {conv['conflicting_signals']}")
