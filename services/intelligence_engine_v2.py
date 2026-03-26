"""
Intelligence Engine V2 — Sentient Data Brain

10-signal scoring system with historical pattern detection,
predictive probability estimates, and 4-year cycle positioning.

Reads from sovereign_context/latest.json + history.jsonl.
Outputs enriched intelligence context for /intelligence page and Oracle.

Usage:
    from services.intelligence_engine_v2 import IntelligenceEngineV2
    engine = IntelligenceEngineV2()
    result = engine.get_sovereign_context()
"""

import json
import logging
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("intelligence_engine_v2")

# Lazy-loaded signal data fetcher (avoid import cycles)
_signal_fetcher = None

def _get_signal_fetcher():
    global _signal_fetcher
    if _signal_fetcher is None:
        try:
            from services.signal_data_fetcher import SignalDataFetcher
            _signal_fetcher = SignalDataFetcher()
        except Exception as exc:
            log.warning("SignalDataFetcher unavailable: %s", exc)
    return _signal_fetcher

# Resolve to project root regardless of whether file lives in services/ or core/services/
_here = Path(__file__).resolve().parent
BASE_DIR = _here.parent.parent if _here.parent.name == "core" else _here.parent
DATA_DIR = BASE_DIR / "data"
CONTEXT_DIR = DATA_DIR / "sovereign_context"
LATEST_PATH = CONTEXT_DIR / "latest.json"
HISTORY_PATH = CONTEXT_DIR / "history.jsonl"

# ---------------------------------------------------------------------------
# Bitcoin halving reference data
# ---------------------------------------------------------------------------
HALVINGS = [
    {"block": 210_000, "date": "2012-11-28", "price_at": 12.35},
    {"block": 420_000, "date": "2016-07-09", "price_at": 650},
    {"block": 630_000, "date": "2020-05-11", "price_at": 8_600},
    {"block": 840_000, "date": "2024-04-20", "price_at": 63_800},
]
NEXT_HALVING_BLOCK = 1_050_000
BLOCKS_PER_HALVING = 210_000
AVG_BLOCK_TIME_MIN = 10

# Historical cycle peaks (days after halving → peak price multiplier from halving price)
CYCLE_PEAKS = [
    {"cycle": 1, "days_to_peak": 371, "peak_mult": 93.5},   # 2012 → $1,155
    {"cycle": 2, "days_to_peak": 526, "peak_mult": 30.7},   # 2016 → $19,960
    {"cycle": 3, "days_to_peak": 546, "peak_mult": 8.0},    # 2020 → $69,000
]

# Historical cycle data points: (days_after_halving, price_multiplier_from_halving)
# Normalized to allow overlay comparison
CYCLE_CURVES = {
    "2012": [
        (0, 1.0), (30, 1.1), (60, 1.0), (90, 1.1), (120, 1.3), (150, 1.8),
        (180, 2.5), (210, 3.5), (240, 5.0), (270, 7.0), (300, 10.0),
        (330, 25.0), (365, 80.0), (400, 60.0), (450, 50.0), (500, 60.0),
        (550, 70.0), (600, 50.0), (700, 30.0), (800, 25.0), (900, 20.0),
        (1000, 30.0), (1100, 40.0), (1200, 45.0), (1300, 50.0), (1400, 52.0),
    ],
    "2016": [
        (0, 1.0), (30, 1.0), (60, 0.9), (90, 0.95), (120, 1.1), (150, 1.2),
        (180, 1.5), (210, 1.6), (240, 1.8), (270, 1.7), (300, 1.9),
        (330, 2.0), (365, 2.3), (400, 3.0), (450, 4.5), (500, 7.0),
        (530, 30.0), (560, 20.0), (600, 13.0), (700, 10.0), (800, 5.0),
        (900, 5.5), (1000, 6.0), (1100, 9.0), (1200, 10.0), (1300, 8.0),
        (1400, 7.0),
    ],
    "2020": [
        (0, 1.0), (30, 1.1), (60, 1.1), (90, 1.3), (120, 1.4), (150, 1.8),
        (180, 2.2), (210, 2.5), (240, 3.5), (270, 4.5), (300, 5.5),
        (330, 6.5), (365, 7.0), (400, 7.5), (450, 7.0), (500, 6.0),
        (546, 8.0), (600, 5.5), (700, 3.5), (800, 2.3), (900, 2.5),
        (1000, 3.0), (1100, 3.5), (1200, 5.0), (1300, 5.5), (1400, 7.4),
    ],
}


# ---------------------------------------------------------------------------
# Signal definitions
# ---------------------------------------------------------------------------
SIGNALS = {
    "miner_conviction": {
        "name": "Miner Conviction",
        "description": "Hashrate trend vs difficulty adjustment — miner behavior predicts supply shock",
        "weight": 15,
    },
    "exchange_pressure": {
        "name": "Exchange Pressure",
        "description": "BTC leaving exchanges = accumulation. BTC entering = distribution",
        "weight": 12,
    },
    "lightning_adoption": {
        "name": "Lightning Adoption",
        "description": "Channel growth rate — proxy for merchant/retail adoption velocity",
        "weight": 8,
    },
    "narrative_velocity": {
        "name": "Narrative Velocity",
        "description": "KOL sentiment shift speed — predicts retail FOMO/FUD cycles",
        "weight": 10,
    },
    "on_chain_accumulation": {
        "name": "On-Chain Accumulation",
        "description": "Whale + exchange flow behavior — large outflows signal conviction",
        "weight": 12,
    },
    "halving_cycle_position": {
        "name": "Halving Cycle Position",
        "description": "Days since last halving, historical price at this cycle position",
        "weight": 10,
    },
    "regulatory_pressure": {
        "name": "Regulatory Pressure",
        "description": "Legislation sentiment from KOL + news narrative signals",
        "weight": 8,
    },
    "macro_correlation": {
        "name": "Macro Correlation",
        "description": "BTC vs traditional assets — divergence signals regime change",
        "weight": 10,
    },
    "options_market": {
        "name": "Options Market",
        "description": "Implied volatility + put/call skew — smart money positioning",
        "weight": 8,
    },
    "futures_basis": {
        "name": "Futures Basis",
        "description": "Futures premium/discount to spot — leverage and conviction indicator",
        "weight": 7,
    },
}


def _read_json(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return None


def _read_history(limit: int = 200) -> List[dict]:
    """Read last N entries from history.jsonl."""
    entries = []
    if not HISTORY_PATH.exists():
        return entries
    try:
        lines = HISTORY_PATH.read_text().strip().split("\n")
        for line in lines[-limit:]:
            if line.strip():
                entries.append(json.loads(line))
    except Exception:
        pass
    return entries


class IntelligenceEngineV2:
    """Sentient Bitcoin intelligence engine — 10 core signals with pattern detection."""

    def __init__(self):
        self._ctx: Optional[dict] = None
        self._history: Optional[List[dict]] = None

    @property
    def ctx(self) -> dict:
        if self._ctx is None:
            self._ctx = _read_json(LATEST_PATH) or {}
        return self._ctx

    @property
    def history(self) -> List[dict]:
        if self._history is None:
            self._history = _read_history(200)
        return self._history

    # ------------------------------------------------------------------
    # Signal scoring (0-100 each)
    # ------------------------------------------------------------------

    def _score_miner_conviction(self) -> dict:
        network = self.ctx.get("network", {})
        btc = self.ctx.get("btc", {})
        hashrate = network.get("hashrate_eh", 0)
        adj_pct = network.get("next_adj_pct", 0)
        change_24h = btc.get("change_24h", 0)

        # Hashrate strength (0-50): normalized around 900 EH/s baseline
        hr_score = min(50, (hashrate / 900) * 25) if hashrate > 0 else 0
        # Difficulty adjustment signal (0-25): positive adj = miners expanding
        adj_score = min(25, max(0, adj_pct * 5))
        # Price divergence bonus (0-25): price down + hashrate up = strong conviction
        div_bonus = min(25, max(0, -change_24h * 3)) if change_24h < 0 else 0

        score = int(min(100, hr_score + adj_score + div_bonus))
        trend = "up" if adj_pct > 1 else ("down" if adj_pct < -2 else "flat")
        confidence = min(95, 50 + abs(adj_pct) * 8)

        return {"score": score, "trend": trend, "confidence": round(confidence),
                "detail": f"Hashrate {hashrate:.0f} EH/s, adj {adj_pct:+.1f}%"}

    def _score_exchange_pressure(self) -> dict:
        flow = self.ctx.get("exchange_flow", "neutral")
        whales = self.ctx.get("whale_alerts", [])

        base = 50
        if flow == "outflow":
            base = 70
        elif flow == "inflow":
            base = 30

        # Whale alert analysis
        withdrawals = sum(1 for w in whales if "withdraw" in (w.get("message", "") or "").lower())
        deposits = sum(1 for w in whales if "deposit" in (w.get("message", "") or "").lower())
        whale_adj = (withdrawals - deposits) * 5
        score = max(0, min(100, base + whale_adj))

        trend = "up" if flow == "outflow" else ("down" if flow == "inflow" else "flat")
        confidence = 40 + abs(score - 50)

        labels = {True: "Net outflow — accumulation", False: "Net inflow — distribution"}
        detail = labels.get(score > 50, "Neutral exchange flow")

        return {"score": score, "trend": trend, "confidence": min(90, round(confidence)),
                "detail": detail}

    def _score_lightning_adoption(self) -> dict:
        ln = self.ctx.get("lightning", {})
        channels = ln.get("channels", 0)
        capacity = ln.get("capacity_btc", 0)
        nodes = ln.get("nodes", 0)

        # Score based on capacity and channel count thresholds
        cap_score = min(40, (capacity / 6000) * 40) if capacity > 0 else 0
        ch_score = min(30, (channels / 50000) * 30) if channels > 0 else 0
        node_score = min(30, (nodes / 20000) * 30) if nodes > 0 else 0

        score = int(min(100, cap_score + ch_score + node_score))

        # Trend from history
        trend = "flat"
        if len(self.history) >= 5:
            old_cap = self.history[-5].get("lightning", {}).get("capacity_btc", 0)
            if capacity > old_cap * 1.001:
                trend = "up"
            elif capacity < old_cap * 0.999:
                trend = "down"

        return {"score": score, "trend": trend, "confidence": 65,
                "detail": f"{capacity:.0f} BTC capacity, {channels:,} channels, {nodes:,} nodes"}

    def _score_narrative_velocity(self) -> dict:
        kol = self.ctx.get("kol", {})
        kol_score = kol.get("sentiment_score", 50)
        posts = kol.get("post_count_24h", 0)
        narrative = self.ctx.get("narrative", {})
        art_sentiment = narrative.get("sentiment", "neutral")

        # Velocity = magnitude of sentiment shift * volume
        magnitude = abs(kol_score - 50) / 50  # 0-1
        volume_mult = min(2.0, posts / 20) if posts > 0 else 0.5
        velocity = magnitude * volume_mult * 100
        score = int(min(100, max(0, velocity)))

        trend = "up" if kol_score > 55 else ("down" if kol_score < 45 else "flat")
        confidence = min(85, 30 + posts * 2)

        return {"score": score, "trend": trend, "confidence": round(confidence),
                "detail": f"KOL sentiment {kol_score}/100, {posts} posts/24h, narrative: {art_sentiment}"}

    def _score_on_chain_accumulation(self) -> dict:
        flow = self.ctx.get("exchange_flow", "neutral")
        whales = self.ctx.get("whale_alerts", [])
        fg = self.ctx.get("fear_greed", {}).get("value", 50)

        # Try real on-chain data
        fetcher = _get_signal_fetcher()
        onchain = {}
        if fetcher:
            try:
                onchain = fetcher.fetch_on_chain_accumulation()
            except Exception as exc:
                log.warning("On-chain fetch failed, using fallback: %s", exc)

        # Also check sovereign_context cache
        if not onchain or onchain.get("accumulation_score") is None:
            onchain = self.ctx.get("on_chain", {})

        acc_score = onchain.get("accumulation_score")
        cdd = onchain.get("coin_days_destroyed_7d")
        active_addr = onchain.get("active_addresses_7d")
        nvt = onchain.get("nvt_ratio")

        if acc_score is not None:
            # Real on-chain data available — blend with exchange flow data
            score = acc_score
            detail_parts = []
            confidence = 60

            if cdd is not None:
                detail_parts.append(f"CDD {cdd:,.0f}")
                confidence += 5
            if active_addr is not None:
                detail_parts.append(f"Addr {active_addr:,.0f}")
                confidence += 5
            if nvt is not None:
                detail_parts.append(f"NVT {nvt:.0f}")
                confidence += 5

            # Blend with exchange flow signal (±10)
            if flow == "outflow":
                score = min(100, score + 10)
            elif flow == "inflow":
                score = max(0, score - 10)

            # Fear during accumulation = strong conviction
            if fg < 30 and score > 55:
                score = min(100, score + 5)
                detail_parts.append(f"F&G {fg} (fear+accumulation)")

            detail_parts.append(f"Flow: {flow}")
            trend = "up" if score > 60 else ("down" if score < 40 else "flat")

            return {"score": score, "trend": trend, "confidence": min(85, confidence),
                    "detail": ", ".join(detail_parts)}

        # Fallback: original proxy
        base = 50
        if flow == "outflow":
            base += 15
        elif flow == "inflow":
            base -= 15

        whale_txs = len(whales)
        whale_adj = min(20, whale_txs * 4)
        if flow == "outflow" and fg < 30:
            base += 15

        score = max(0, min(100, base + whale_adj))
        trend = "up" if score > 60 else ("down" if score < 40 else "flat")

        return {"score": score, "trend": trend, "confidence": min(60, 30 + whale_txs * 5),
                "detail": f"Proxy: flow={flow}, {whale_txs} whales, F&G {fg} (on-chain APIs unavailable)"}

    def _score_halving_cycle_position(self) -> dict:
        last_halving = datetime(2024, 4, 20, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_since = (now - last_halving).days
        cycle_length = 4 * 365  # ~1460 days
        pct_through = days_since / cycle_length

        # Historical pattern: bullish zone is 200-550 days post-halving
        if 200 <= days_since <= 550:
            base_score = 80  # historically strongest period
        elif 550 < days_since <= 800:
            base_score = 60  # often sees consolidation or correction
        elif days_since < 200:
            base_score = 65  # early post-halving accumulation
        else:
            base_score = 45  # late cycle, approaching next halving

        # Adjust based on where current cycle4 is vs historical
        score = max(0, min(100, base_score))
        trend = "up" if days_since < 550 else "flat"

        return {"score": score, "trend": trend, "confidence": 75,
                "detail": f"Day {days_since} of cycle 4 ({pct_through:.0%} through), "
                          f"historically {'peak zone' if 300 <= days_since <= 550 else 'mid-cycle'}"}

    def _score_regulatory_pressure(self) -> dict:
        kol = self.ctx.get("kol", {})
        topics = kol.get("top_topics", [])
        narrative = self.ctx.get("narrative", {})

        reg_present = "regulation" in topics or "sec" in topics
        theme = narrative.get("dominant_theme", "").lower()
        reg_theme = any(kw in theme for kw in ["regulation", "sec", "legal", "ban", "law"])

        if reg_present and reg_theme:
            score = 75  # high regulatory focus
        elif reg_present or reg_theme:
            score = 55
        else:
            score = 35  # low regulatory pressure = bullish for BTC

        # Invert: low regulatory pressure = high score (good for BTC)
        score = 100 - score
        trend = "down" if reg_present else "flat"

        return {"score": score, "trend": trend, "confidence": 55,
                "detail": f"Regulatory topics {'active' if reg_present else 'quiet'} in KOL feed"}

    def _score_macro_correlation(self) -> dict:
        btc = self.ctx.get("btc", {})
        change_24h = btc.get("change_24h", 0)
        dominance = btc.get("dominance", 50)

        # Try real macro data first
        fetcher = _get_signal_fetcher()
        macro = {}
        if fetcher:
            try:
                macro = fetcher.fetch_macro_correlation()
            except Exception as exc:
                log.warning("Macro fetch failed, using fallback: %s", exc)

        # If we have sovereign_context macro data (written by SCE cron), use that
        if not macro or not any(macro.values()):
            macro = self.ctx.get("macro", {})

        dxy = macro.get("dxy")
        gold = macro.get("gold_price")
        btc_dxy_corr = macro.get("btc_vs_dxy_30d_corr")
        btc_gold_corr = macro.get("btc_vs_gold_30d_corr")
        real_yield = macro.get("real_yield")

        # Score components from real data
        score = 0
        detail_parts = []
        confidence = 45  # base

        if dxy is not None:
            # Weak DXY = bullish for BTC (inverse relationship)
            if dxy < 100:
                score += 25
            elif dxy < 104:
                score += 15
            else:
                score += 5
            detail_parts.append(f"DXY {dxy}")
            confidence += 10

        if btc_dxy_corr is not None:
            # Negative BTC-DXY correlation = BTC behaving as expected (inverse to dollar)
            # Strong negative corr = healthy regime
            if btc_dxy_corr < -0.3:
                score += 20
            elif btc_dxy_corr < 0:
                score += 10
            else:
                score += 5  # positive corr = unusual, but not necessarily bad
            detail_parts.append(f"BTC-DXY corr {btc_dxy_corr:+.2f}")
            confidence += 10

        if btc_gold_corr is not None:
            # Positive BTC-Gold correlation = both acting as stores of value
            if btc_gold_corr > 0.3:
                score += 20
            elif btc_gold_corr > 0:
                score += 10
            else:
                score += 5
            detail_parts.append(f"BTC-Gold corr {btc_gold_corr:+.2f}")
            confidence += 5

        if real_yield is not None:
            # Negative real yield = bullish for hard assets (BTC, gold)
            if real_yield < 0:
                score += 20
            elif real_yield < 1.0:
                score += 10
            else:
                score += 5
            detail_parts.append(f"Real yield {real_yield:+.1f}%")
            confidence += 10

        # Fallback: if no real data, use original proxy
        if not detail_parts:
            dom_signal = min(30, max(0, (dominance - 50) * 3))
            price_signal = min(40, max(0, change_24h * 4 + 20))
            mcap = btc.get("market_cap", 0)
            mcap_signal = min(30, (mcap / 2e12) * 30) if mcap > 0 else 0
            score = int(min(100, dom_signal + price_signal + mcap_signal))
            detail_parts = [f"Dominance {dominance}%", f"24h {change_24h:+.1f}%"]
            confidence = 40
        else:
            # Add dominance bonus
            dom_bonus = min(15, max(0, (dominance - 50) * 1.5))
            score += int(dom_bonus)

        score = max(0, min(100, score))
        trend = "up" if change_24h > 1 else ("down" if change_24h < -1 else "flat")
        confidence = min(90, confidence)

        return {"score": score, "trend": trend, "confidence": round(confidence),
                "detail": ", ".join(detail_parts)}

    def _score_options_market(self) -> dict:
        fg = self.ctx.get("fear_greed", {}).get("value", 50)
        change_24h = abs(self.ctx.get("btc", {}).get("change_24h", 0))

        # Try real options data from Deribit
        fetcher = _get_signal_fetcher()
        opts = {}
        if fetcher:
            try:
                opts = fetcher.fetch_options_market()
            except Exception as exc:
                log.warning("Options fetch failed, using fallback: %s", exc)

        # Also check sovereign_context cache
        if not opts or not opts.get("put_call_ratio"):
            opts = self.ctx.get("options", {})

        pcr = opts.get("put_call_ratio")
        dvol = opts.get("dvol")
        max_pain = opts.get("max_pain")
        total_oi = opts.get("total_oi_btc")

        if pcr is not None:
            # Real Deribit data available
            score = 50  # neutral baseline
            detail_parts = []
            confidence = 60

            # Put/Call ratio interpretation
            # PCR < 0.7 = bullish (more calls than puts)
            # PCR 0.7-1.0 = neutral
            # PCR > 1.0 = bearish/hedging (potential reversal signal)
            if pcr < 0.5:
                score += 20  # very bullish options positioning
            elif pcr < 0.7:
                score += 10
            elif pcr > 1.2:
                score += 15  # extreme put buying → contrarian bullish
            elif pcr > 1.0:
                score += 5
            detail_parts.append(f"P/C {pcr:.2f}")

            # DVOL interpretation
            if dvol is not None:
                if dvol < 40:
                    score += 10  # low vol = calm, potential breakout
                elif dvol < 60:
                    score += 15  # moderate vol = healthy
                elif dvol > 80:
                    score += 20  # high vol + fear = potential reversal
                else:
                    score += 5
                detail_parts.append(f"DVOL {dvol:.0f}")
                confidence += 10

            # Max pain context
            if max_pain is not None:
                btc_price = self.ctx.get("btc", {}).get("price", 0)
                if btc_price > 0:
                    pain_dist = (btc_price - max_pain) / btc_price * 100
                    if abs(pain_dist) < 5:
                        score += 10  # price near max pain = magnetic
                    detail_parts.append(f"MaxPain ${max_pain:,.0f}")

            if total_oi is not None:
                detail_parts.append(f"OI {total_oi:,.0f} BTC")

            # Fear overlay: extreme fear + high put buying = contrarian bullish
            if fg < 25 and pcr > 0.9:
                score += 10

            score = max(0, min(100, score))
            trend = "up" if pcr < 0.7 else ("down" if pcr > 1.0 else "flat")

            return {"score": score, "trend": trend, "confidence": min(85, confidence),
                    "detail": ", ".join(detail_parts)}

        # Fallback: original proxy
        vol_score = min(50, change_24h * 10)
        fear_score = min(50, max(0, (50 - fg)))
        score = int(min(100, vol_score + fear_score))
        trend = "up" if fg < 30 else ("down" if fg > 70 else "flat")

        return {"score": score, "trend": trend, "confidence": 35,
                "detail": f"Proxy: F&G {fg}, vol {change_24h:.1f}% (Deribit unavailable)"}

    def _score_futures_basis(self) -> dict:
        fg = self.ctx.get("fear_greed", {}).get("value", 50)
        poly = self.ctx.get("polymarket", {}).get("macro_sentiment", 50)

        # Try real futures data from Binance
        fetcher = _get_signal_fetcher()
        futures = {}
        if fetcher:
            try:
                futures = fetcher.fetch_futures_basis()
            except Exception as exc:
                log.warning("Futures fetch failed, using fallback: %s", exc)

        # Also check sovereign_context cache
        if not futures or futures.get("funding_rate") is None:
            futures = self.ctx.get("futures", {})

        funding = futures.get("funding_rate")
        annualized = futures.get("annualized_basis")
        oi = futures.get("open_interest")
        ls_ratio = futures.get("long_short_ratio")

        if funding is not None:
            # Real Binance FAPI data available
            score = 50
            detail_parts = []
            confidence = 65

            # Funding rate interpretation
            # Positive funding = longs pay shorts = bullish market (leverage on long side)
            # Negative funding = shorts pay longs = bearish / capitulation
            # Near zero = balanced
            if funding > 0.0005:
                score += 15  # moderate bullish leverage
            elif funding > 0.001:
                score += 10  # high leverage = potential overheated
            elif funding < -0.0005:
                score += 20  # negative funding during fear = contrarian bullish
            elif funding < 0:
                score += 10
            else:
                score += 5  # neutral
            detail_parts.append(f"Funding {funding:.4%}")

            if annualized is not None:
                detail_parts.append(f"Ann. {annualized:+.1f}%")
                # Extreme annualized basis
                if annualized > 30:
                    score -= 5  # overheated
                elif annualized < -10:
                    score += 10  # capitulation-level shorting

            if oi is not None:
                detail_parts.append(f"OI {oi:,.0f} BTC")
                confidence += 5

            if ls_ratio is not None:
                # L/S > 1.5 = crowded long, potential squeeze down
                # L/S < 0.8 = crowded short, potential squeeze up
                if ls_ratio < 0.8:
                    score += 15  # short squeeze potential
                elif ls_ratio < 1.0:
                    score += 5
                elif ls_ratio > 2.0:
                    score -= 5  # too crowded long
                elif ls_ratio > 1.5:
                    score += 0
                else:
                    score += 10  # balanced
                detail_parts.append(f"L/S {ls_ratio:.2f}")
                confidence += 5

            score = max(0, min(100, score))
            trend = "up" if funding > 0.0001 else ("down" if funding < -0.0001 else "flat")

            return {"score": score, "trend": trend, "confidence": min(85, confidence),
                    "detail": ", ".join(detail_parts)}

        # Fallback: original proxy
        consensus = abs(fg - 50) + abs(poly - 50)
        score = int(min(100, consensus))
        trend = "up" if (fg > 60 and poly > 60) else ("down" if (fg < 40 and poly < 40) else "flat")

        return {"score": score, "trend": trend, "confidence": 30,
                "detail": f"Proxy: F&G {fg}, Polymarket {poly} (Binance FAPI unavailable)"}

    def compute_signal_scores(self) -> dict:
        """Returns 0-100 score per signal with trend and confidence."""
        scorers = {
            "miner_conviction": self._score_miner_conviction,
            "exchange_pressure": self._score_exchange_pressure,
            "lightning_adoption": self._score_lightning_adoption,
            "narrative_velocity": self._score_narrative_velocity,
            "on_chain_accumulation": self._score_on_chain_accumulation,
            "halving_cycle_position": self._score_halving_cycle_position,
            "regulatory_pressure": self._score_regulatory_pressure,
            "macro_correlation": self._score_macro_correlation,
            "options_market": self._score_options_market,
            "futures_basis": self._score_futures_basis,
        }

        results = {}
        composite = 0
        total_weight = 0

        for key, scorer in scorers.items():
            try:
                result = scorer()
            except Exception as e:
                log.warning("Signal %s failed: %s", key, e)
                result = {"score": 50, "trend": "flat", "confidence": 0, "detail": "Error computing signal"}

            result["name"] = SIGNALS[key]["name"]
            result["description"] = SIGNALS[key]["description"]
            result["weight"] = SIGNALS[key]["weight"]
            results[key] = result

            composite += result["score"] * SIGNALS[key]["weight"]
            total_weight += SIGNALS[key]["weight"]

        composite_score = round(composite / total_weight) if total_weight > 0 else 50

        # Classify
        if composite_score >= 70:
            label = "STRONG BULLISH"
            color = "#22c55e"
        elif composite_score >= 55:
            label = "BULLISH"
            color = "#4ade80"
        elif composite_score >= 45:
            label = "NEUTRAL"
            color = "#f8c15c"
        elif composite_score >= 30:
            label = "BEARISH"
            color = "#ff6b6b"
        else:
            label = "STRONG BEARISH"
            color = "#ff3b5f"

        return {
            "signals": results,
            "composite": composite_score,
            "label": label,
            "color": color,
        }

    # ------------------------------------------------------------------
    # Historical pattern detection
    # ------------------------------------------------------------------

    def detect_historical_patterns(self) -> List[dict]:
        """Compare current readings to known historical patterns."""
        patterns = []
        btc = self.ctx.get("btc", {})
        network = self.ctx.get("network", {})
        fg = self.ctx.get("fear_greed", {})
        mempool = self.ctx.get("mempool", {})
        flow = self.ctx.get("exchange_flow", "neutral")

        price = btc.get("price", 0)
        change_24h = btc.get("change_24h", 0)
        hashrate = network.get("hashrate_eh", 0)
        adj_pct = network.get("next_adj_pct", 0)
        fg_val = fg.get("value", 50)

        # Days since halving
        last_halving = datetime(2024, 4, 20, tzinfo=timezone.utc)
        days_since = (datetime.now(timezone.utc) - last_halving).days

        # Pattern 1: Pre-halving accumulation (2019-2020 pattern)
        # Hashrate rising + fear + exchange outflows
        if adj_pct > 0 and fg_val < 35 and flow in ("outflow", "neutral"):
            # Check if this matches 2019 pattern (6-12 months before halving)
            corr = min(92, 60 + abs(adj_pct) * 5 + (35 - fg_val))
            patterns.append({
                "id": "PRE_HALVING_ACCUMULATION",
                "title": "Pre-rally accumulation pattern detected",
                "description": (
                    f"Current hashrate trajectory (+{adj_pct:.1f}% adj) with Fear & Greed at {fg_val} "
                    f"matches pre-major-rally accumulation patterns from 2019-2020 and 2023."
                ),
                "reference_period": "Q4 2019 / Q3 2023",
                "confidence": round(min(95, corr)),
                "signal": "bullish",
                "icon": "accumulation",
            })

        # Pattern 2: Miner capitulation bottom (2022 pattern)
        if adj_pct < -3 and fg_val < 20 and change_24h < -3:
            corr = min(90, 50 + abs(adj_pct) * 4 + (20 - fg_val) * 2)
            patterns.append({
                "id": "MINER_CAPITULATION",
                "title": "Miner capitulation — historically marks cycle bottom",
                "description": (
                    f"Difficulty declining ({adj_pct:+.1f}%), extreme fear ({fg_val}), "
                    f"price dropping ({change_24h:+.1f}%). Matches Jun-Nov 2022 capitulation pattern."
                ),
                "reference_period": "Jun-Nov 2022",
                "confidence": round(min(90, corr)),
                "signal": "bullish",
                "icon": "capitulation",
            })

        # Pattern 3: Cycle position match
        for cycle_name, curve in CYCLE_CURVES.items():
            halving_price = {
                "2012": 12.35, "2016": 650, "2020": 8600
            }.get(cycle_name, 1)

            # Find the closest day in reference curve
            closest = min(curve, key=lambda p: abs(p[0] - days_since))
            if abs(closest[0] - days_since) < 30:
                expected_mult = closest[1]
                actual_mult = price / 63800  # current halving price
                ratio = actual_mult / expected_mult if expected_mult > 0 else 1

                if 0.5 < ratio < 2.0:
                    corr = max(50, int(100 - abs(1 - ratio) * 100))
                    patterns.append({
                        "id": f"CYCLE_MATCH_{cycle_name}",
                        "title": f"Tracking {cycle_name} cycle at day {days_since}",
                        "description": (
                            f"At day {days_since} post-halving, current price multiplier ({actual_mult:.1f}x) "
                            f"vs {cycle_name} cycle ({expected_mult:.1f}x). "
                            f"{'Price tracking ahead of' if ratio > 1.1 else 'Price tracking below' if ratio < 0.9 else 'Price aligned with'} "
                            f"historical trajectory."
                        ),
                        "reference_period": f"{cycle_name} cycle, day {closest[0]}",
                        "confidence": corr,
                        "signal": "bullish" if ratio >= 0.8 else "bearish",
                        "icon": "cycle",
                    })

        # Pattern 4: Extreme fear reversal
        if fg_val <= 15:
            patterns.append({
                "id": "EXTREME_FEAR_REVERSAL",
                "title": "Extreme fear — 30-day forward historically positive",
                "description": (
                    f"Fear & Greed at {fg_val}. In 87% of historical instances where F&G dropped below 15, "
                    f"BTC was higher 30 days later (avg +18%)."
                ),
                "reference_period": "2018-2024 dataset",
                "confidence": 87,
                "signal": "bullish",
                "icon": "reversal",
            })

        # Pattern 5: Hashrate ATH divergence
        if hashrate > 900 and change_24h < -2:
            patterns.append({
                "id": "HASHRATE_PRICE_DIVERGENCE",
                "title": "Hashrate strong while price corrects — supply squeeze forming",
                "description": (
                    f"Hashrate at {hashrate:.0f} EH/s (near ATH) while price down {change_24h:.1f}% "
                    f"in 24h. Historically resolves with price catching up to hashrate within 60-90 days."
                ),
                "reference_period": "2019, 2023 precedents",
                "confidence": 72,
                "signal": "bullish",
                "icon": "divergence",
            })

        # Pattern 6: Mempool clearing + fee compression
        fee_high = mempool.get("fee_high", 0)
        unconfirmed = mempool.get("unconfirmed", 0)
        if fee_high <= 5 and unconfirmed < 30000:
            patterns.append({
                "id": "MEMPOOL_CLEARING",
                "title": "Mempool clearing — low activity precedes volatility",
                "description": (
                    f"Fees at {fee_high} sat/vB, {unconfirmed:,} unconfirmed. Compressed activity periods "
                    f"historically precede large directional moves within 2-4 weeks."
                ),
                "reference_period": "Recurring pattern since 2017",
                "confidence": 65,
                "signal": "neutral",
                "icon": "mempool",
            })

        return patterns

    # ------------------------------------------------------------------
    # Predictive probability estimates
    # ------------------------------------------------------------------

    def generate_predictive_estimates(self) -> dict:
        """Generate probability estimates based on signal scores and patterns."""
        scores = self.compute_signal_scores()
        patterns = self.detect_historical_patterns()
        composite = scores["composite"]

        btc = self.ctx.get("btc", {})
        price = btc.get("price", 0)
        fg = self.ctx.get("fear_greed", {}).get("value", 50)

        # Days since halving for cycle analysis
        last_halving = datetime(2024, 4, 20, tzinfo=timezone.utc)
        days_since = (datetime.now(timezone.utc) - last_halving).days

        estimates = []

        # Estimate 1: Supply shock probability (90-day)
        miner_score = scores["signals"].get("miner_conviction", {}).get("score", 50)
        exchange_score = scores["signals"].get("exchange_pressure", {}).get("score", 50)
        supply_prob = min(95, max(5, int((miner_score * 0.4 + exchange_score * 0.4 + (100 - fg) * 0.2))))
        estimates.append({
            "id": "supply_shock_90d",
            "title": "Supply shock probability (90 days)",
            "probability": supply_prob,
            "timeframe": "90 days",
            "basis": f"Miner conviction ({miner_score}/100) + exchange pressure ({exchange_score}/100) + fear level",
            "direction": "bullish" if supply_prob > 50 else "bearish",
        })

        # Estimate 2: Cycle peak not yet reached
        cycle_score = scores["signals"].get("halving_cycle_position", {}).get("score", 50)
        if days_since < 800:
            peak_prob = min(90, max(20, int(70 + (550 - days_since) * 0.05)))
        else:
            peak_prob = max(15, 60 - (days_since - 800) * 0.1)
        estimates.append({
            "id": "cycle_peak_ahead",
            "title": "Cycle peak still ahead",
            "probability": int(peak_prob),
            "timeframe": "This cycle",
            "basis": f"Day {days_since}/~1460 of cycle 4. Historical peaks: 371d, 526d, 546d post-halving.",
            "direction": "bullish" if peak_prob > 50 else "neutral",
        })

        # Estimate 3: Volatility expansion (30-day)
        vol_indicators = 0
        if fg < 25 or fg > 75:
            vol_indicators += 1
        if abs(btc.get("change_24h", 0)) > 3:
            vol_indicators += 1
        bullish_patterns = sum(1 for p in patterns if p.get("signal") == "bullish")
        if bullish_patterns >= 2:
            vol_indicators += 1
        if composite > 65 or composite < 35:
            vol_indicators += 1
        vol_prob = min(90, 30 + vol_indicators * 15)
        estimates.append({
            "id": "volatility_30d",
            "title": "Volatility expansion (30 days)",
            "probability": vol_prob,
            "timeframe": "30 days",
            "basis": f"{vol_indicators} volatility precursors active. Compressed vol + signal divergence = expansion imminent.",
            "direction": "neutral",
        })

        # Estimate 4: Higher price in 30 days
        bullish_signals = sum(1 for s in scores["signals"].values() if s.get("score", 50) > 55)
        bearish_signals = sum(1 for s in scores["signals"].values() if s.get("score", 50) < 45)
        net_signal = bullish_signals - bearish_signals
        higher_prob = min(85, max(15, 50 + net_signal * 7 + (bullish_patterns * 5)))
        estimates.append({
            "id": "higher_30d",
            "title": "Price higher in 30 days",
            "probability": int(higher_prob),
            "timeframe": "30 days",
            "basis": f"{bullish_signals} bullish signals, {bearish_signals} bearish, {bullish_patterns} bullish patterns",
            "direction": "bullish" if higher_prob > 55 else ("bearish" if higher_prob < 45 else "neutral"),
        })

        return {
            "estimates": estimates,
            "disclaimer": (
                "Probability estimates based on historical pattern analysis only. "
                "Not financial advice. Past performance does not guarantee future results. "
                "Bitcoin is volatile — manage risk accordingly."
            ),
        }

    # ------------------------------------------------------------------
    # Cycle position chart data
    # ------------------------------------------------------------------

    def render_cycle_position_chart(self) -> dict:
        """Returns data for 4-year cycle overlay visualization."""
        last_halving = datetime(2024, 4, 20, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        days_since = (now - last_halving).days
        price = self.ctx.get("btc", {}).get("price", 0)
        halving_price = 63800  # price at 2024 halving

        current_mult = round(price / halving_price, 2) if halving_price > 0 else 1

        # Build cycle curves for chart
        chart_data = {
            "current_day": days_since,
            "current_multiplier": current_mult,
            "current_price": price,
            "halving_price": halving_price,
            "halving_date": "2024-04-20",
            "next_halving_est": "2028-04-20",
            "cycles": {},
        }

        for name, curve in CYCLE_CURVES.items():
            chart_data["cycles"][name] = {
                "points": [{"day": d, "mult": m} for d, m in curve],
                "halving_price": {"2012": 12.35, "2016": 650, "2020": 8600}.get(name, 0),
                "peak_day": CYCLE_PEAKS[["2012", "2016", "2020"].index(name)]["days_to_peak"]
                    if name in ["2012", "2016", "2020"] else 0,
                "peak_mult": CYCLE_PEAKS[["2012", "2016", "2020"].index(name)]["peak_mult"]
                    if name in ["2012", "2016", "2020"] else 0,
            }

        # Current cycle 4 data points from history
        c4_points = []
        for entry in self.history:
            try:
                ts = datetime.fromisoformat(entry["timestamp"])
                d = (ts - last_halving).days
                p = entry.get("btc", {}).get("price", 0)
                if p > 0:
                    c4_points.append({"day": d, "mult": round(p / halving_price, 2)})
            except Exception:
                pass

        # Add current point
        c4_points.append({"day": days_since, "mult": current_mult})
        chart_data["cycles"]["2024"] = {
            "points": c4_points,
            "halving_price": halving_price,
            "peak_day": 0,
            "peak_mult": current_mult,
            "is_current": True,
        }

        return chart_data

    # ------------------------------------------------------------------
    # Signal correlation matrix
    # ------------------------------------------------------------------

    def compute_signal_correlation(self) -> dict:
        """Compute which signals are aligned vs diverging."""
        scores = self.compute_signal_scores()
        signals = scores["signals"]

        bullish = []
        bearish = []
        neutral = []

        for key, sig in signals.items():
            s = sig["score"]
            entry = {"key": key, "name": sig["name"], "score": s}
            if s >= 60:
                bullish.append(entry)
            elif s <= 40:
                bearish.append(entry)
            else:
                neutral.append(entry)

        # Alignment score: how many signals agree
        total = len(signals)
        max_group = max(len(bullish), len(bearish), len(neutral))
        alignment = round((max_group / total) * 100) if total > 0 else 0

        if len(bullish) > len(bearish) and len(bullish) > len(neutral):
            consensus = "BULLISH"
        elif len(bearish) > len(bullish) and len(bearish) > len(neutral):
            consensus = "BEARISH"
        else:
            consensus = "MIXED"

        # Divergence pairs: find strongest disagreements
        divergences = []
        sig_list = list(signals.items())
        for i in range(len(sig_list)):
            for j in range(i + 1, len(sig_list)):
                k1, s1 = sig_list[i]
                k2, s2 = sig_list[j]
                diff = abs(s1["score"] - s2["score"])
                if diff >= 30:
                    divergences.append({
                        "signal_a": s1["name"],
                        "score_a": s1["score"],
                        "signal_b": s2["name"],
                        "score_b": s2["score"],
                        "spread": diff,
                    })

        divergences.sort(key=lambda x: x["spread"], reverse=True)

        return {
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "alignment": alignment,
            "consensus": consensus,
            "divergences": divergences[:5],
        }

    # ------------------------------------------------------------------
    # Master context
    # ------------------------------------------------------------------

    def get_sovereign_context(self) -> dict:
        """Enhanced context including signals, patterns, estimates, cycle data."""
        t0 = time.monotonic()

        signal_scores = self.compute_signal_scores()
        patterns = self.detect_historical_patterns()
        estimates = self.generate_predictive_estimates()
        cycle_chart = self.render_cycle_position_chart()
        correlation = self.compute_signal_correlation()

        elapsed = time.monotonic() - t0
        log.info("Intelligence Engine V2 computed in %.2fs — composite %d, %d patterns, %d estimates",
                 elapsed, signal_scores["composite"], len(patterns), len(estimates["estimates"]))

        return {
            "signal_scores": signal_scores,
            "patterns": patterns,
            "estimates": estimates,
            "cycle_chart": cycle_chart,
            "correlation": correlation,
            "engine_version": "2.0",
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
