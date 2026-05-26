"""
SOVEREIGN INTEL TERMINAL - Protocol Pulse
==========================================
The definitive version. Best of all approaches.

WHAT WE TOOK FROM EACH:

CLAUDE: Regime detection, signal structure (observation → action → invalidation),
        priority levels, edge decay concept

CHATGPT: Hard rule that LLM never invents, data provenance as first-class,
         backtest harness requirement, signal scorecard, "receipts over vibes"

GROK: Modular fetcher architecture, extensible signal registry,
      multi-source aggregation pattern

GEMINI: Two-tier output concept (free brief vs premium delta),
        automated publishing hooks

WHAT WE REJECTED:
- Made-up historical accuracy numbers
- Placeholder data masquerading as signals  
- GPU wattage theater
- APIs that don't exist or require expensive access
- ML without clean time-series data first

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SOVEREIGN INTEL TERMINAL                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  INGEST          │  COMPUTE           │  DETECT         │  DELIVER         │
│  ─────────       │  ─────────         │  ─────────      │  ─────────       │
│  • CoinGecko     │  • Z-Scores        │  • Regime       │  • Signal Board  │
│  • Mempool       │  • Percentiles     │  • Anomalies    │  • IC Memo       │
│  • Fear/Greed    │  • Deltas          │  • Triggers     │  • Alerts (TG)   │
│  • (FRED roadmap)│  • Correlations    │  • Divergences  │  • Premium Delta │
├─────────────────────────────────────────────────────────────────────────────┤
│                              SQLITE DATABASE                                │
│  datapoints │ signals │ regimes │ backtests │ alerts │ reports            │
└─────────────────────────────────────────────────────────────────────────────┘

HARD RULES:
1. Every metric comes from a fetchable source
2. Every claim traces to a stored datapoint  
3. LLM narrates computed results - never invents
4. No accuracy claims without backtest data
5. Honest about limitations

PHILOSOPHY:
"The goal is not to be right. The goal is to be early AND honest."
"""

import os
import json
import sqlite3
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SovereignIntel")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = "data/sovereign_intel.db"

# Signal thresholds - these are configurable
SIGNAL_CONFIG = {
    "fear_greed": {
        "extreme_fear": 25,
        "fear": 40,
        "greed": 60,
        "extreme_greed": 75,
    },
    "funding": {
        "zscore_threshold": 2.0,
    },
    "mempool": {
        "congestion_threshold": 100000,
        "low_fee_threshold": 10,
    },
    "difficulty": {
        "significant_change": 5.0,
    },
    "price": {
        "strong_trend_30d": 20,
        "moderate_trend_30d": 5,
    }
}


# ============================================================================
# ENUMS AND DATA STRUCTURES
# ============================================================================

class SignalStrength(Enum):
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    EXTREME = 4


class Direction(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Regime(Enum):
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    CAPITULATION = "capitulation"
    EUPHORIA = "euphoria"
    RANGING = "ranging"


@dataclass
class Signal:
    """A signal with full provenance."""
    name: str
    category: str
    direction: Direction
    strength: SignalStrength
    
    # The data (with receipts)
    metric: str
    value: float
    zscore: Optional[float]
    percentile: Optional[float]
    datapoints_used: int
    
    # The intelligence (derived from data)
    observation: str
    implication: str
    action: str
    invalidation: str
    
    # Meta
    edge_decay_hours: int
    source: str
    timestamp: str
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["direction"] = self.direction.value
        d["strength"] = self.strength.value
        return d


@dataclass  
class RegimeAssessment:
    """Current market regime with reasoning."""
    regime: Regime
    confidence: float
    reasons: List[str]
    signals_used: List[str]
    timestamp: str


# ============================================================================
# DATABASE
# ============================================================================

def init_db() -> sqlite3.Connection:
    """Initialize database with full schema."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    conn.executescript("""
        -- Raw datapoints with provenance
        CREATE TABLE IF NOT EXISTS datapoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            source TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            raw_json TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_dp_metric_ts ON datapoints(metric, ts_utc DESC);
        
        -- Triggered signals
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            direction TEXT NOT NULL,
            strength INTEGER NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            zscore REAL,
            percentile REAL,
            datapoints_used INTEGER,
            observation TEXT,
            implication TEXT,
            action TEXT,
            invalidation TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_sig_ts ON signals(ts_utc DESC);
        
        -- Regime assessments
        CREATE TABLE IF NOT EXISTS regimes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            regime TEXT NOT NULL,
            confidence REAL NOT NULL,
            reasons_json TEXT,
            signals_json TEXT
        );
        
        -- Backtest results (for future use - we won't fake these)
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_name TEXT NOT NULL,
            run_date TEXT NOT NULL,
            lookback_days INTEGER,
            sample_size INTEGER,
            triggered_count INTEGER,
            win_count INTEGER,
            loss_count INTEGER,
            win_rate REAL,
            avg_return_5d REAL,
            avg_return_14d REAL,
            notes TEXT
        );
        
        -- Alerts sent
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            signal_name TEXT NOT NULL,
            channel TEXT NOT NULL,
            message TEXT,
            sent INTEGER DEFAULT 0
        );
        
        -- Generated reports
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_utc TEXT NOT NULL,
            report_type TEXT NOT NULL,
            content TEXT,
            signals_json TEXT,
            regime_json TEXT
        );
    """)
    
    conn.commit()
    return conn


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================================
# DATA INGESTION
# ============================================================================

class DataIngester:
    """
    Fetches data from real, working APIs and stores with full provenance.
    """
    
    def __init__(self):
        self.endpoints = {
            "coingecko": "https://api.coingecko.com/api/v3",
            "mempool": "https://mempool.space/api",
            "fear_greed": "https://api.alternative.me/fng",
        }
        self._cache = {}
        self._cache_ts = {}
    
    def _fetch(self, url: str, cache_seconds: int = 60) -> Optional[Dict]:
        """Fetch with caching to respect rate limits."""
        now = datetime.now().timestamp()
        
        if url in self._cache:
            if now - self._cache_ts.get(url, 0) < cache_seconds:
                return self._cache[url]
        
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            self._cache[url] = data
            self._cache_ts[url] = now
            return data
        except Exception as e:
            logger.error(f"Fetch failed {url}: {e}")
            return None
    
    def _store(self, source: str, metric: str, value: float, raw: Any = None):
        """Store datapoint with full provenance."""
        conn = get_db()
        conn.execute(
            "INSERT INTO datapoints (ts_utc, source, metric, value, raw_json) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), source, metric, value, 
             json.dumps(raw) if raw else None)
        )
        conn.commit()
        conn.close()
        logger.debug(f"Stored: {source}/{metric} = {value}")
    
    def ingest_price(self) -> bool:
        """BTC price and market data from CoinGecko."""
        data = self._fetch(
            f"{self.endpoints['coingecko']}/coins/bitcoin?localization=false&tickers=false&community_data=false&developer_data=false",
            cache_seconds=60
        )
        
        if not data:
            return False
        
        md = data.get("market_data", {})
        
        metrics = {
            "btc_price": md.get("current_price", {}).get("usd"),
            "btc_change_1h": md.get("price_change_percentage_1h_in_currency", {}).get("usd"),
            "btc_change_24h": md.get("price_change_percentage_24h"),
            "btc_change_7d": md.get("price_change_percentage_7d"),
            "btc_change_30d": md.get("price_change_percentage_30d"),
            "btc_volume_24h": md.get("total_volume", {}).get("usd"),
            "btc_mcap": md.get("market_cap", {}).get("usd"),
            "btc_ath_change": md.get("ath_change_percentage", {}).get("usd"),
        }
        
        for metric, value in metrics.items():
            if value is not None:
                self._store("coingecko", metric, float(value))
        
        logger.info("Price data ingested")
        return True
    
    def ingest_derivatives(self) -> bool:
        """Derivatives data from CoinGecko."""
        data = self._fetch(f"{self.endpoints['coingecko']}/derivatives", cache_seconds=300)
        
        if not data:
            return False
        
        # Filter BTC perpetuals
        btc_perps = [
            d for d in data 
            if 'BTC' in (d.get('symbol') or '').upper() 
            and ('PERP' in (d.get('symbol') or '').upper() or 'USD' in (d.get('symbol') or '').upper())
        ]
        
        if btc_perps:
            # Funding rates
            funding_rates = [
                float(d.get('funding_rate') or 0) 
                for d in btc_perps[:20] 
                if d.get('funding_rate') is not None
            ]
            if funding_rates:
                self._store("coingecko", "funding_rate_avg", statistics.mean(funding_rates), 
                           {"sample_size": len(funding_rates)})
            
            # Open interest
            oi_values = [
                float(d.get('open_interest') or 0)
                for d in btc_perps
                if d.get('open_interest') is not None
            ]
            if oi_values:
                self._store("coingecko", "open_interest_total", sum(oi_values),
                           {"sample_size": len(oi_values)})
        
        logger.info("Derivatives data ingested")
        return True
    
    def ingest_mempool(self) -> bool:
        """Network data from mempool.space."""
        success = True
        
        # Mempool stats
        data = self._fetch(f"{self.endpoints['mempool']}/mempool", cache_seconds=60)
        if data:
            self._store("mempool", "mempool_tx_count", data.get("count", 0))
            self._store("mempool", "mempool_vsize", data.get("vsize", 0))
        else:
            success = False
        
        # Fees
        data = self._fetch(f"{self.endpoints['mempool']}/v1/fees/recommended", cache_seconds=60)
        if data:
            self._store("mempool", "fee_fastest", data.get("fastestFee", 0))
            self._store("mempool", "fee_half_hour", data.get("halfHourFee", 0))
            self._store("mempool", "fee_hour", data.get("hourFee", 0))
            self._store("mempool", "fee_economy", data.get("economyFee", 0))
        else:
            success = False
        
        # Difficulty
        data = self._fetch(f"{self.endpoints['mempool']}/v1/difficulty-adjustment", cache_seconds=600)
        if data:
            self._store("mempool", "difficulty_change", data.get("difficultyChange", 0))
            self._store("mempool", "difficulty_progress", data.get("progressPercent", 0))
            self._store("mempool", "difficulty_blocks_remaining", data.get("remainingBlocks", 0))
        else:
            success = False
        
        logger.info("Mempool data ingested")
        return success
    
    def ingest_sentiment(self) -> bool:
        """Fear & Greed from Alternative.me."""
        data = self._fetch(f"{self.endpoints['fear_greed']}/?limit=30", cache_seconds=1800)
        
        if not data or not data.get("data"):
            return False
        
        records = data["data"]
        current = records[0]
        
        self._store("alternative_me", "fear_greed", int(current.get("value", 50)))
        
        # Store 7-day average if we have enough data
        if len(records) >= 7:
            avg_7d = statistics.mean([int(r["value"]) for r in records[:7]])
            self._store("alternative_me", "fear_greed_7d_avg", avg_7d)
        
        logger.info("Sentiment data ingested")
        return True
    
    def ingest_all(self) -> Dict[str, bool]:
        """Run complete ingestion cycle."""
        results = {
            "price": self.ingest_price(),
            "derivatives": self.ingest_derivatives(),
            "mempool": self.ingest_mempool(),
            "sentiment": self.ingest_sentiment(),
        }
        
        success_count = sum(results.values())
        logger.info(f"Ingestion complete: {success_count}/{len(results)} sources")
        
        return results


# ============================================================================
# SIGNAL COMPUTATION
# ============================================================================

class SignalComputer:
    """
    Computes signals from stored datapoints.
    Every signal has full provenance.
    """
    
    def __init__(self):
        self.min_datapoints_for_zscore = 15
        self.min_datapoints_for_percentile = 10
    
    def _get_history(self, metric: str, days: int = 60) -> List[Tuple[str, float]]:
        """Get historical values for a metric."""
        conn = get_db()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? AND ts_utc >= ? ORDER BY ts_utc",
            (metric, cutoff)
        )
        results = [(r[0], r[1]) for r in cursor.fetchall()]
        conn.close()
        return results
    
    def _get_latest(self, metric: str) -> Optional[Tuple[str, float]]:
        """Get most recent value for a metric."""
        conn = get_db()
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc DESC LIMIT 1",
            (metric,)
        )
        result = cursor.fetchone()
        conn.close()
        return (result[0], result[1]) if result else None
    
    def _zscore(self, value: float, history: List[float]) -> Optional[float]:
        """Calculate z-score. Returns None if insufficient data."""
        if len(history) < self.min_datapoints_for_zscore:
            return None
        
        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        
        return (value - mean) / stdev if stdev > 0 else 0.0
    
    def _percentile(self, value: float, history: List[float]) -> Optional[float]:
        """Calculate percentile. Returns None if insufficient data."""
        if len(history) < self.min_datapoints_for_percentile:
            return None
        
        below = len([h for h in history if h < value])
        return (below / len(history)) * 100
    
    def _store_signal(self, signal: Signal):
        """Store a triggered signal."""
        conn = get_db()
        conn.execute(
            """INSERT INTO signals 
               (ts_utc, name, category, direction, strength, metric, value, 
                zscore, percentile, datapoints_used, observation, implication, action, invalidation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (signal.timestamp, signal.name, signal.category, signal.direction.value,
             signal.strength.value, signal.metric, signal.value, signal.zscore,
             signal.percentile, signal.datapoints_used, signal.observation,
             signal.implication, signal.action, signal.invalidation)
        )
        conn.commit()
        conn.close()
    
    def compute_fear_greed_signal(self) -> Optional[Signal]:
        """Fear & Greed extreme detection."""
        latest = self._get_latest("fear_greed")
        if not latest:
            return None
        
        ts, value = latest
        history = self._get_history("fear_greed", days=60)
        history_values = [h[1] for h in history]
        
        zscore = self._zscore(value, history_values)
        percentile = self._percentile(value, history_values)
        
        # Get trend
        latest_avg = self._get_latest("fear_greed_7d_avg")
        trend = "stable"
        if latest_avg:
            trend = "improving" if value > latest_avg[1] else "declining" if value < latest_avg[1] else "stable"
        
        cfg = SIGNAL_CONFIG["fear_greed"]
        
        if value <= cfg["extreme_fear"]:
            return Signal(
                name="Extreme Fear",
                category="sentiment",
                direction=Direction.BULLISH,
                strength=SignalStrength.STRONG if value <= 20 else SignalStrength.MODERATE,
                metric="fear_greed",
                value=value,
                zscore=zscore,
                percentile=percentile,
                datapoints_used=len(history_values),
                observation=f"Fear & Greed at {value:.0f} ({trend}). Below {cfg['extreme_fear']} threshold.",
                implication="Market in fear. Historically correlates with buying opportunities. Retail panic selling.",
                action="Consider accumulation. Scale in over 2-4 weeks. Don't try to catch exact bottom.",
                invalidation="Major systemic event (exchange failure, regulatory ban, macro crash).",
                edge_decay_hours=168,
                source="alternative.me",
                timestamp=ts
            )
        
        elif value >= cfg["extreme_greed"]:
            return Signal(
                name="Extreme Greed",
                category="sentiment",
                direction=Direction.BEARISH,
                strength=SignalStrength.STRONG if value >= 85 else SignalStrength.MODERATE,
                metric="fear_greed",
                value=value,
                zscore=zscore,
                percentile=percentile,
                datapoints_used=len(history_values),
                observation=f"Fear & Greed at {value:.0f} ({trend}). Above {cfg['extreme_greed']} threshold.",
                implication="Market euphoria. Historically correlates with corrections. Retail FOMO.",
                action="Take profits on leveraged positions. Tighten stops. Do NOT FOMO.",
                invalidation="Structural supply shock (ETF demand exceeding miner supply).",
                edge_decay_hours=72,
                source="alternative.me",
                timestamp=ts
            )
        
        return None
    
    def compute_funding_signal(self) -> Optional[Signal]:
        """Funding rate anomaly detection."""
        latest = self._get_latest("funding_rate_avg")
        if not latest:
            return None
        
        ts, value = latest
        history = self._get_history("funding_rate_avg", days=60)
        history_values = [h[1] for h in history]
        
        zscore = self._zscore(value, history_values)
        percentile = self._percentile(value, history_values)
        
        if zscore is None:
            return None  # Not enough data
        
        cfg = SIGNAL_CONFIG["funding"]
        
        if zscore >= cfg["zscore_threshold"]:
            return Signal(
                name="Funding: Overleveraged Longs",
                category="derivatives",
                direction=Direction.BEARISH,
                strength=SignalStrength.STRONG if zscore >= 2.5 else SignalStrength.MODERATE,
                metric="funding_rate_avg",
                value=value * 100,  # Convert to percentage for display
                zscore=zscore,
                percentile=percentile,
                datapoints_used=len(history_values),
                observation=f"Funding at {value*100:.4f}% ({zscore:.1f}σ above 60-day mean).",
                implication="Market heavily long on leverage. Elevated liquidation cascade risk.",
                action="Reduce long exposure. Consider hedging. Wait for funding to normalize.",
                invalidation="New ATH with sustained spot volume and ETF inflows.",
                edge_decay_hours=24,
                source="coingecko",
                timestamp=ts
            )
        
        elif zscore <= -cfg["zscore_threshold"]:
            return Signal(
                name="Funding: Overleveraged Shorts",
                category="derivatives",
                direction=Direction.BULLISH,
                strength=SignalStrength.STRONG if zscore <= -2.5 else SignalStrength.MODERATE,
                metric="funding_rate_avg",
                value=value * 100,
                zscore=zscore,
                percentile=percentile,
                datapoints_used=len(history_values),
                observation=f"Funding at {value*100:.4f}% ({abs(zscore):.1f}σ below 60-day mean).",
                implication="Market heavily short. Short squeeze conditions present. Positive carry for longs.",
                action="Look for long entries on dips. Shorts are paying you to be long.",
                invalidation="Major macro deterioration or exchange failure.",
                edge_decay_hours=24,
                source="coingecko",
                timestamp=ts
            )
        
        return None
    
    def compute_mempool_signal(self) -> Optional[Signal]:
        """Network congestion detection."""
        latest_tx = self._get_latest("mempool_tx_count")
        latest_fee = self._get_latest("fee_fastest")
        
        if not latest_tx:
            return None
        
        ts, tx_count = latest_tx
        fee = latest_fee[1] if latest_fee else 0
        
        history = self._get_history("mempool_tx_count", days=30)
        history_values = [h[1] for h in history]
        
        zscore = self._zscore(tx_count, history_values)
        percentile = self._percentile(tx_count, history_values)
        
        cfg = SIGNAL_CONFIG["mempool"]
        
        if tx_count >= cfg["congestion_threshold"]:
            return Signal(
                name="Network Congestion",
                category="network",
                direction=Direction.NEUTRAL,
                strength=SignalStrength.MODERATE,
                metric="mempool_tx_count",
                value=tx_count,
                zscore=zscore,
                percentile=percentile,
                datapoints_used=len(history_values),
                observation=f"Mempool at {tx_count:,.0f} txs. Fastest fee: {fee:.0f} sat/vB.",
                implication="Network under heavy load. Settlement delays likely. Fees elevated.",
                action="Delay non-urgent transactions. Use Lightning for small payments.",
                invalidation="Mempool clears within 6-12 hours.",
                edge_decay_hours=12,
                source="mempool.space",
                timestamp=ts
            )
        
        elif fee <= cfg["low_fee_threshold"] and fee > 0:
            return Signal(
                name="Low Fee Window",
                category="network",
                direction=Direction.NEUTRAL,
                strength=SignalStrength.WEAK,
                metric="fee_fastest",
                value=fee,
                zscore=None,
                percentile=None,
                datapoints_used=len(history_values),
                observation=f"Fees at {fee:.0f} sat/vB. Mempool: {tx_count:,.0f} txs.",
                implication="Excellent window for on-chain operations. Low settlement costs.",
                action="Consolidate UTXOs. Open Lightning channels. Move to cold storage.",
                invalidation="Fee spike from demand surge.",
                edge_decay_hours=6,
                source="mempool.space",
                timestamp=ts
            )
        
        return None
    
    def compute_difficulty_signal(self) -> Optional[Signal]:
        """Mining difficulty adjustment signal."""
        latest = self._get_latest("difficulty_change")
        if not latest:
            return None
        
        ts, value = latest
        
        # Get blocks remaining
        blocks_remaining = self._get_latest("difficulty_blocks_remaining")
        blocks = blocks_remaining[1] if blocks_remaining else "N/A"
        
        cfg = SIGNAL_CONFIG["difficulty"]
        
        if abs(value) >= cfg["significant_change"]:
            if value > 0:
                return Signal(
                    name="Difficulty Surge",
                    category="mining",
                    direction=Direction.BULLISH,
                    strength=SignalStrength.MODERATE,
                    metric="difficulty_change",
                    value=value,
                    zscore=None,
                    percentile=None,
                    datapoints_used=1,
                    observation=f"Difficulty projecting +{value:.1f}% in ~{blocks} blocks.",
                    implication="Strong miner confidence. Hashrate increasing. Long-term bullish.",
                    action="Bullish for long-term holders. Miners investing in future.",
                    invalidation="Energy cost spike or regulatory crackdown on mining.",
                    edge_decay_hours=336,
                    source="mempool.space",
                    timestamp=ts
                )
            else:
                return Signal(
                    name="Difficulty Drop",
                    category="mining",
                    direction=Direction.BEARISH,
                    strength=SignalStrength.MODERATE,
                    metric="difficulty_change",
                    value=value,
                    zscore=None,
                    percentile=None,
                    datapoints_used=1,
                    observation=f"Difficulty projecting {value:.1f}% in ~{blocks} blocks.",
                    implication="Miner stress or capitulation. Hashrate declining. Watch for selling.",
                    action="Monitor for miner selling pressure. Could signal local bottom forming.",
                    invalidation="Hashrate stabilizes within 2 weeks.",
                    edge_decay_hours=336,
                    source="mempool.space",
                    timestamp=ts
                )
        
        return None
    
    def compute_all_signals(self) -> List[Signal]:
        """Compute all signals from current data."""
        signals = []
        
        computers = [
            self.compute_fear_greed_signal,
            self.compute_funding_signal,
            self.compute_mempool_signal,
            self.compute_difficulty_signal,
        ]
        
        for compute in computers:
            try:
                signal = compute()
                if signal:
                    signals.append(signal)
                    self._store_signal(signal)
            except Exception as e:
                logger.error(f"Signal computation error: {e}")
        
        # Sort by strength
        signals.sort(key=lambda s: s.strength.value, reverse=True)
        
        return signals


# ============================================================================
# REGIME DETECTION
# ============================================================================

class RegimeDetector:
    """
    Determines current market regime from multiple signals.
    Uses voting system with weighted inputs.
    """
    
    def detect(self, signals: List[Signal]) -> RegimeAssessment:
        """Determine regime from signals and price data."""
        votes = defaultdict(float)
        reasons = []
        signals_used = []
        
        # Get price momentum from stored data
        conn = get_db()
        
        cursor = conn.execute(
            "SELECT value FROM datapoints WHERE metric = 'btc_change_30d' ORDER BY ts_utc DESC LIMIT 1"
        )
        row = cursor.fetchone()
        change_30d = row[0] if row else 0
        
        cursor = conn.execute(
            "SELECT value FROM datapoints WHERE metric = 'btc_change_7d' ORDER BY ts_utc DESC LIMIT 1"
        )
        row = cursor.fetchone()
        change_7d = row[0] if row else 0
        
        conn.close()
        
        cfg = SIGNAL_CONFIG["price"]
        
        # Price momentum votes
        if change_30d >= cfg["strong_trend_30d"] and change_7d >= 10:
            votes["EUPHORIA"] += 2
            reasons.append(f"Strong uptrend (30d: +{change_30d:.1f}%)")
        elif change_30d <= -cfg["strong_trend_30d"] and change_7d <= -10:
            votes["CAPITULATION"] += 2
            reasons.append(f"Strong downtrend (30d: {change_30d:.1f}%)")
        elif change_30d >= cfg["moderate_trend_30d"]:
            votes["RISK_ON"] += 1
            reasons.append(f"Moderate uptrend (30d: +{change_30d:.1f}%)")
        elif change_30d <= -cfg["moderate_trend_30d"]:
            votes["RISK_OFF"] += 1
            reasons.append(f"Moderate downtrend (30d: {change_30d:.1f}%)")
        else:
            votes["RANGING"] += 0.5
            reasons.append(f"Sideways (30d: {change_30d:+.1f}%)")
        
        # Signal votes
        for signal in signals:
            signals_used.append(signal.name)
            
            if signal.category == "sentiment":
                if "Fear" in signal.name and signal.direction == Direction.BULLISH:
                    votes["CAPITULATION"] += 2
                    votes["ACCUMULATION"] += 1
                    reasons.append("Extreme fear (sentiment)")
                elif "Greed" in signal.name and signal.direction == Direction.BEARISH:
                    votes["EUPHORIA"] += 2
                    votes["DISTRIBUTION"] += 1
                    reasons.append("Extreme greed (sentiment)")
            
            elif signal.category == "derivatives":
                if "Longs" in signal.name:
                    votes["DISTRIBUTION"] += 1.5
                    reasons.append("Overleveraged longs (derivatives)")
                elif "Shorts" in signal.name:
                    votes["ACCUMULATION"] += 1.5
                    reasons.append("Overleveraged shorts (derivatives)")
        
        # Determine winner
        if not votes:
            return RegimeAssessment(
                regime=Regime.RANGING,
                confidence=0.3,
                reasons=["Insufficient signals"],
                signals_used=[],
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        winner = max(votes, key=votes.get)
        total_votes = sum(votes.values())
        confidence = min(0.9, votes[winner] / total_votes) if total_votes > 0 else 0.3
        
        assessment = RegimeAssessment(
            regime=Regime[winner],
            confidence=confidence,
            reasons=reasons[:4],  # Top 4 reasons
            signals_used=signals_used,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Store regime assessment
        conn = get_db()
        conn.execute(
            "INSERT INTO regimes (ts_utc, regime, confidence, reasons_json, signals_json) VALUES (?, ?, ?, ?, ?)",
            (assessment.timestamp, assessment.regime.value, assessment.confidence,
             json.dumps(assessment.reasons), json.dumps(assessment.signals_used))
        )
        conn.commit()
        conn.close()
        
        return assessment


# ============================================================================
# REPORT GENERATION
# ============================================================================

class ReportGenerator:
    """
    Generates reports from computed data.
    Never invents - only narrates what was computed.
    """
    
    def _get_market_snapshot(self) -> Dict[str, Any]:
        """Get current market state from stored data."""
        conn = get_db()
        
        metrics = [
            "btc_price", "btc_change_24h", "btc_change_7d", "btc_change_30d",
            "btc_volume_24h", "fear_greed", "funding_rate_avg", "mempool_tx_count",
            "fee_fastest", "difficulty_change", "open_interest_total"
        ]
        
        snapshot = {}
        for metric in metrics:
            cursor = conn.execute(
                "SELECT value, ts_utc FROM datapoints WHERE metric = ? ORDER BY ts_utc DESC LIMIT 1",
                (metric,)
            )
            row = cursor.fetchone()
            if row:
                snapshot[metric] = {"value": row[0], "ts": row[1]}
        
        # Get data provenance stats
        cursor = conn.execute("SELECT COUNT(*) FROM datapoints")
        snapshot["_total_datapoints"] = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(DISTINCT metric) FROM datapoints")
        snapshot["_unique_metrics"] = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT MIN(ts_utc), MAX(ts_utc) FROM datapoints")
        row = cursor.fetchone()
        snapshot["_date_range"] = {"min": row[0], "max": row[1]}
        
        conn.close()
        return snapshot
    
    def generate_signal_board(self, signals: List[Signal]) -> str:
        """Generate signal board table."""
        if not signals:
            return "No signals triggered."
        
        lines = [
            f"{'Signal':<35} {'Value':>12} {'Z-Score':>10} {'Dir':>8} {'Strength':>10}",
            "─" * 80
        ]
        
        for sig in signals:
            z_str = f"{sig.zscore:.2f}σ" if sig.zscore is not None else "N/A"
            dir_icon = "↑" if sig.direction == Direction.BULLISH else "↓" if sig.direction == Direction.BEARISH else "→"
            strength_str = sig.strength.name.lower()
            
            lines.append(
                f"{sig.name:<35} {sig.value:>12.4f} {z_str:>10} {dir_icon:>8} {strength_str:>10}"
            )
        
        return "\n".join(lines)
    
    def generate_full_report(self, signals: List[Signal], regime: RegimeAssessment) -> str:
        """Generate complete intelligence report."""
        snapshot = self._get_market_snapshot()
        now = datetime.now(timezone.utc).strftime("%B %d, %Y %H:%M UTC")
        
        # Determine overall bias
        bullish = len([s for s in signals if s.direction == Direction.BULLISH])
        bearish = len([s for s in signals if s.direction == Direction.BEARISH])
        bias = "BULLISH" if bullish > bearish else "BEARISH" if bearish > bullish else "NEUTRAL"
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SOVEREIGN INTEL TERMINAL - PREMIUM BRIEF                  ║
║                              {now}                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│ REGIME: {regime.regime.value.upper():<15} │ BIAS: {bias:<10} │ CONFIDENCE: {regime.confidence*100:.0f}%         │
│ Reason: {', '.join(regime.reasons[:2])[:58]:<58}   │
└─────────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
MARKET SNAPSHOT (all values from stored datapoints)
═══════════════════════════════════════════════════════════════════════════════
"""
        
        if "btc_price" in snapshot:
            report += f"  BTC: ${snapshot['btc_price']['value']:,.0f}\n"
        
        changes = []
        if "btc_change_24h" in snapshot:
            changes.append(f"24h: {snapshot['btc_change_24h']['value']:+.2f}%")
        if "btc_change_7d" in snapshot:
            changes.append(f"7d: {snapshot['btc_change_7d']['value']:+.2f}%")
        if "btc_change_30d" in snapshot:
            changes.append(f"30d: {snapshot['btc_change_30d']['value']:+.2f}%")
        if changes:
            report += f"  {' │ '.join(changes)}\n"
        
        if "btc_volume_24h" in snapshot:
            report += f"  24h Volume: ${snapshot['btc_volume_24h']['value']/1e9:.2f}B\n"
        
        report += "\n"
        
        if "fear_greed" in snapshot:
            fg = snapshot["fear_greed"]["value"]
            classification = "Extreme Fear" if fg <= 25 else "Fear" if fg <= 40 else "Neutral" if fg <= 60 else "Greed" if fg <= 75 else "Extreme Greed"
            report += f"  Fear & Greed: {fg:.0f} ({classification})\n"
        
        if "funding_rate_avg" in snapshot:
            report += f"  Funding Rate: {snapshot['funding_rate_avg']['value']*100:.4f}%\n"
        
        if "mempool_tx_count" in snapshot:
            report += f"  Mempool: {snapshot['mempool_tx_count']['value']:,.0f} txs\n"
        
        if "fee_fastest" in snapshot:
            report += f"  Fast Fee: {snapshot['fee_fastest']['value']:.0f} sat/vB\n"
        
        if "difficulty_change" in snapshot:
            report += f"  Next Difficulty: {snapshot['difficulty_change']['value']:+.2f}%\n"
        
        report += f"""
═══════════════════════════════════════════════════════════════════════════════
SIGNAL BOARD ({len(signals)} active)
═══════════════════════════════════════════════════════════════════════════════
{self.generate_signal_board(signals)}

═══════════════════════════════════════════════════════════════════════════════
ACTIONABLE INTELLIGENCE
═══════════════════════════════════════════════════════════════════════════════
"""
        
        if signals:
            for i, sig in enumerate(signals, 1):
                priority = "🔴" if sig.strength.value >= 3 else "🟡" if sig.strength.value >= 2 else "🟢"
                dir_icon = "↑" if sig.direction == Direction.BULLISH else "↓" if sig.direction == Direction.BEARISH else "→"
                
                report += f"""
  {i}. {priority} {sig.name} {dir_icon}
     ├─ OBSERVATION: {sig.observation}
     ├─ IMPLICATION: {sig.implication}
     ├─ ACTION: {sig.action}
     ├─ INVALIDATION: {sig.invalidation}
     └─ Data: {sig.datapoints_used} points │ Edge decay: {sig.edge_decay_hours}h │ Source: {sig.source}
"""
        else:
            report += "\n  No significant signals. Markets in equilibrium.\n"
        
        # Regime checklist
        checklists = {
            Regime.ACCUMULATION: [
                "Scale into positions during fear spikes",
                "Prioritize spot over leverage",
                "Set DCA schedule if not active",
                "Move coins to cold storage"
            ],
            Regime.DISTRIBUTION: [
                "Take profits at target levels",
                "Reduce or eliminate leverage",
                "Raise stops to protect gains",
                "Do NOT FOMO into breakouts"
            ],
            Regime.EUPHORIA: [
                "This is NOT the time to buy",
                "Scale out remaining positions",
                "Secure profits to cold storage",
                "Prepare dry powder for correction"
            ],
            Regime.CAPITULATION: [
                "This is where generational wealth is made",
                "Begin accumulation if dry powder available",
                "Scale in slowly - don't catch exact bottom",
                "Ignore the noise - focus on signal"
            ],
            Regime.RISK_ON: [
                "Trend is favorable for longs",
                "Use pullbacks as entry opportunities",
                "Monitor leverage for crowding",
                "Trail stops as position develops"
            ],
            Regime.RISK_OFF: [
                "Reduce risk exposure",
                "Favor cash/stables over positions",
                "Watch for capitulation signals",
                "Prepare shopping list"
            ],
            Regime.RANGING: [
                "Exercise patience - no clear edge",
                "Avoid large new positions",
                "Focus on improving systems",
                "Wait for regime clarity"
            ]
        }
        
        report += f"""
═══════════════════════════════════════════════════════════════════════════════
OPERATOR CHECKLIST ({regime.regime.value.upper()})
═══════════════════════════════════════════════════════════════════════════════
"""
        for item in checklists.get(regime.regime, checklists[Regime.RANGING]):
            report += f"  ☐ {item}\n"
        
        # Triggers
        if signals:
            report += """
═══════════════════════════════════════════════════════════════════════════════
TRIGGERS (what would change my mind)
═══════════════════════════════════════════════════════════════════════════════
"""
            for sig in signals[:3]:
                report += f"  • {sig.name}: {sig.invalidation}\n"
        
        # Data provenance
        report += f"""
═══════════════════════════════════════════════════════════════════════════════
DATA PROVENANCE
═══════════════════════════════════════════════════════════════════════════════
  Total Datapoints: {snapshot['_total_datapoints']:,}
  Unique Metrics: {snapshot['_unique_metrics']}
  Date Range: {snapshot['_date_range']['min'][:10] if snapshot['_date_range']['min'] else 'N/A'} to {snapshot['_date_range']['max'][:10] if snapshot['_date_range']['max'] else 'N/A'}

HONEST LIMITATIONS (what we don't have)
═══════════════════════════════════════════════════════════════════════════════
  • Exchange flows (need Glassnode/CryptoQuant - $$$)
  • ETF flows (need Bloomberg terminal or paid scraper)
  • Options flow (need Deribit API or paid aggregator)
  • Liquidation data (need exchange APIs with historical access)
  • Backtest results (need 30+ days of data collection first)

═══════════════════════════════════════════════════════════════════════════════
SOVEREIGNTY REMINDER
═══════════════════════════════════════════════════════════════════════════════
  This is intelligence, not financial advice.
  Self-custody your Bitcoin. Not your keys, not your coins.
  Every claim above traces to a stored datapoint.
  
  SOVEREIGN INTEL TERMINAL │ Receipts Over Vibes │ Signal Over Noise
═══════════════════════════════════════════════════════════════════════════════
"""
        return report


# ============================================================================
# MAIN ENGINE
# ============================================================================

class SovereignIntelTerminal:
    """The complete intelligence system."""
    
    def __init__(self):
        init_db()
        self.ingester = DataIngester()
        self.computer = SignalComputer()
        self.regime = RegimeDetector()
        self.reporter = ReportGenerator()
    
    def ingest(self) -> Dict[str, bool]:
        """Run data ingestion only."""
        return self.ingester.ingest_all()
    
    def analyze(self) -> Dict[str, Any]:
        """Run analysis on stored data."""
        signals = self.computer.compute_all_signals()
        regime = self.regime.detect(signals)
        report = self.reporter.generate_full_report(signals, regime)
        
        # Store report
        conn = get_db()
        conn.execute(
            "INSERT INTO reports (ts_utc, report_type, content, signals_json, regime_json) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), "full", report,
             json.dumps([s.to_dict() for s in signals]),
             json.dumps({"regime": regime.regime.value, "confidence": regime.confidence, "reasons": regime.reasons}))
        )
        conn.commit()
        conn.close()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "regime": regime.regime.value,
            "regime_confidence": regime.confidence,
            "signals_triggered": len(signals),
            "signals": [s.to_dict() for s in signals],
            "report": report
        }
    
    def run(self) -> Dict[str, Any]:
        """Full cycle: ingest + analyze."""
        self.ingest()
        return self.analyze()


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys
    
    terminal = SovereignIntelTerminal()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "ingest":
            result = terminal.ingest()
            print(json.dumps(result, indent=2))
        elif cmd == "analyze":
            result = terminal.analyze()
            print(result["report"])
        elif cmd == "run":
            result = terminal.run()
            print(result["report"])
        else:
            print("Usage: python sovereign_intel_terminal.py [ingest|analyze|run]")
    else:
        result = terminal.run()
        print(result["report"])
        
        # Save JSON
        with open("data/sovereign_report.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print("\n✅ Full report saved to data/sovereign_report.json")


# ============================================================================
# ADDITIONS FROM GROK - LEGITIMATE IMPROVEMENTS ONLY
# ============================================================================

class BacktestEngine:
    """
    Backtest signals against stored historical data.
    Only reports what the data actually shows - no invented numbers.
    """
    
    def __init__(self):
        self.min_samples = 30  # Need at least 30 datapoints for meaningful backtest
    
    def backtest_threshold_signal(
        self, 
        signal_metric: str, 
        price_metric: str = "btc_price",
        threshold_type: str = "below",  # "below" or "above"
        threshold_value: float = 25,
        forward_days: int = 7
    ) -> Dict[str, Any]:
        """
        Backtest a threshold-based signal.
        
        Example: When fear_greed drops below 25, what happens to BTC 
        price over the next 7 days?
        
        Returns actual statistics from stored data.
        """
        conn = get_db()
        
        # Get signal metric history
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc",
            (signal_metric,)
        )
        signal_data = cursor.fetchall()
        
        # Get price history
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc",
            (price_metric,)
        )
        price_data = cursor.fetchall()
        conn.close()
        
        if len(signal_data) < self.min_samples or len(price_data) < self.min_samples:
            return {
                "status": "insufficient_data",
                "signal_metric": signal_metric,
                "samples": len(signal_data),
                "required": self.min_samples,
                "message": f"Need {self.min_samples}+ datapoints. Currently have {len(signal_data)}. Keep collecting."
            }
        
        # Convert to dict for easier lookup
        price_dict = {row[0][:10]: row[1] for row in price_data}  # Date -> Price
        
        # Find all instances where signal triggered
        triggers = []
        for ts, value in signal_data:
            triggered = False
            if threshold_type == "below" and value <= threshold_value:
                triggered = True
            elif threshold_type == "above" and value >= threshold_value:
                triggered = True
            
            if triggered:
                trigger_date = ts[:10]
                triggers.append({
                    "date": trigger_date,
                    "signal_value": value,
                    "price_at_trigger": price_dict.get(trigger_date)
                })
        
        if len(triggers) < 3:
            return {
                "status": "insufficient_triggers",
                "signal_metric": signal_metric,
                "triggers_found": len(triggers),
                "message": "Need at least 3 trigger instances for meaningful backtest."
            }
        
        # Calculate forward returns for each trigger
        results = []
        for trigger in triggers:
            if not trigger["price_at_trigger"]:
                continue
            
            trigger_date = datetime.fromisoformat(trigger["date"])
            forward_date = (trigger_date + timedelta(days=forward_days)).strftime("%Y-%m-%d")
            
            forward_price = price_dict.get(forward_date)
            if forward_price and trigger["price_at_trigger"]:
                pct_change = ((forward_price - trigger["price_at_trigger"]) / trigger["price_at_trigger"]) * 100
                results.append({
                    "trigger_date": trigger["date"],
                    "signal_value": trigger["signal_value"],
                    "entry_price": trigger["price_at_trigger"],
                    "exit_price": forward_price,
                    "pct_change": pct_change,
                    "win": pct_change > 0
                })
        
        if len(results) < 3:
            return {
                "status": "insufficient_results",
                "signal_metric": signal_metric,
                "results_found": len(results),
                "message": "Not enough complete trigger->outcome pairs in data."
            }
        
        # Calculate statistics
        wins = len([r for r in results if r["win"]])
        losses = len(results) - wins
        win_rate = wins / len(results)
        avg_return = statistics.mean([r["pct_change"] for r in results])
        
        return {
            "status": "success",
            "signal_metric": signal_metric,
            "threshold_type": threshold_type,
            "threshold_value": threshold_value,
            "forward_days": forward_days,
            "total_triggers": len(results),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "avg_return_pct": avg_return,
            "best_return": max(r["pct_change"] for r in results),
            "worst_return": min(r["pct_change"] for r in results),
            "results": results,
            "note": "These are ACTUAL results from stored data, not estimates."
        }
    
    def backtest_zscore_signal(
        self,
        signal_metric: str,
        price_metric: str = "btc_price",
        zscore_threshold: float = 2.0,
        direction: str = "above",  # "above" or "below"
        forward_days: int = 7,
        lookback_days: int = 60
    ) -> Dict[str, Any]:
        """
        Backtest a z-score based signal.
        
        Example: When funding rate is >2σ above mean, what happens next?
        """
        conn = get_db()
        
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc",
            (signal_metric,)
        )
        signal_data = [(row[0], row[1]) for row in cursor.fetchall()]
        
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc",
            (price_metric,)
        )
        price_data = cursor.fetchall()
        conn.close()
        
        if len(signal_data) < self.min_samples:
            return {
                "status": "insufficient_data",
                "samples": len(signal_data),
                "required": self.min_samples
            }
        
        price_dict = {row[0][:10]: row[1] for row in price_data}
        
        # Calculate rolling z-scores and find triggers
        triggers = []
        for i in range(lookback_days, len(signal_data)):
            window = [signal_data[j][1] for j in range(i - lookback_days, i)]
            current = signal_data[i][1]
            ts = signal_data[i][0]
            
            mean = statistics.mean(window)
            stdev = statistics.stdev(window) if len(window) > 1 else 0
            
            if stdev == 0:
                continue
            
            zscore = (current - mean) / stdev
            
            triggered = False
            if direction == "above" and zscore >= zscore_threshold:
                triggered = True
            elif direction == "below" and zscore <= -zscore_threshold:
                triggered = True
            
            if triggered:
                triggers.append({
                    "date": ts[:10],
                    "value": current,
                    "zscore": zscore,
                    "price_at_trigger": price_dict.get(ts[:10])
                })
        
        if len(triggers) < 3:
            return {
                "status": "insufficient_triggers",
                "triggers_found": len(triggers)
            }
        
        # Calculate forward returns
        results = []
        for trigger in triggers:
            if not trigger["price_at_trigger"]:
                continue
            
            trigger_date = datetime.fromisoformat(trigger["date"])
            forward_date = (trigger_date + timedelta(days=forward_days)).strftime("%Y-%m-%d")
            
            forward_price = price_dict.get(forward_date)
            if forward_price:
                pct_change = ((forward_price - trigger["price_at_trigger"]) / trigger["price_at_trigger"]) * 100
                results.append({
                    "trigger_date": trigger["date"],
                    "zscore": trigger["zscore"],
                    "pct_change": pct_change,
                    "win": pct_change > 0 if direction == "below" else pct_change < 0
                })
        
        if len(results) < 3:
            return {"status": "insufficient_results", "results_found": len(results)}
        
        wins = len([r for r in results if r["win"]])
        
        return {
            "status": "success",
            "signal_metric": signal_metric,
            "zscore_threshold": zscore_threshold,
            "direction": direction,
            "forward_days": forward_days,
            "total_triggers": len(results),
            "wins": wins,
            "losses": len(results) - wins,
            "win_rate": wins / len(results),
            "avg_return_pct": statistics.mean([r["pct_change"] for r in results]),
            "results": results
        }


class CorrelationTracker:
    """
    Track cross-asset correlations over time.
    Legitimate institutional analysis.
    """
    
    def compute_rolling_correlation(
        self,
        metric_a: str,
        metric_b: str,
        window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Compute rolling correlation between two metrics.
        """
        conn = get_db()
        
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc",
            (metric_a,)
        )
        data_a = {row[0][:10]: row[1] for row in cursor.fetchall()}
        
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc",
            (metric_b,)
        )
        data_b = {row[0][:10]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        # Find overlapping dates
        common_dates = sorted(set(data_a.keys()) & set(data_b.keys()))
        
        if len(common_dates) < window_days:
            return {
                "status": "insufficient_data",
                "common_datapoints": len(common_dates),
                "required": window_days
            }
        
        # Get aligned values
        values_a = [data_a[d] for d in common_dates]
        values_b = [data_b[d] for d in common_dates]
        
        # Calculate correlation
        n = len(values_a)
        mean_a = sum(values_a) / n
        mean_b = sum(values_b) / n
        
        numerator = sum((values_a[i] - mean_a) * (values_b[i] - mean_b) for i in range(n))
        denom_a = sum((v - mean_a) ** 2 for v in values_a) ** 0.5
        denom_b = sum((v - mean_b) ** 2 for v in values_b) ** 0.5
        
        if denom_a == 0 or denom_b == 0:
            return {"status": "error", "message": "Zero variance in data"}
        
        correlation = numerator / (denom_a * denom_b)
        
        # Store correlation
        conn = get_db()
        conn.execute(
            """INSERT INTO correlations 
               (ts_utc, metric_a, metric_b, correlation, window_days, interpretation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), metric_a, metric_b,
             correlation, window_days, self._interpret_correlation(correlation))
        )
        conn.commit()
        conn.close()
        
        return {
            "status": "success",
            "metric_a": metric_a,
            "metric_b": metric_b,
            "correlation": correlation,
            "window_days": window_days,
            "datapoints": len(common_dates),
            "interpretation": self._interpret_correlation(correlation),
            "date_range": f"{common_dates[0]} to {common_dates[-1]}"
        }
    
    def _interpret_correlation(self, corr: float) -> str:
        """Interpret correlation strength."""
        abs_corr = abs(corr)
        direction = "positive" if corr > 0 else "negative"
        
        if abs_corr >= 0.8:
            strength = "very strong"
        elif abs_corr >= 0.6:
            strength = "strong"
        elif abs_corr >= 0.4:
            strength = "moderate"
        elif abs_corr >= 0.2:
            strength = "weak"
        else:
            strength = "negligible"
        
        return f"{strength} {direction} correlation"


# Add to SovereignIntelTerminal class
def run_backtests(self) -> Dict[str, Any]:
    """Run backtests on all defined signals."""
    backtester = BacktestEngine()
    
    results = {}
    
    # Backtest Fear & Greed extreme fear
    results["fear_greed_extreme_fear"] = backtester.backtest_threshold_signal(
        signal_metric="fear_greed",
        threshold_type="below",
        threshold_value=25,
        forward_days=7
    )
    
    # Backtest Fear & Greed extreme greed
    results["fear_greed_extreme_greed"] = backtester.backtest_threshold_signal(
        signal_metric="fear_greed",
        threshold_type="above",
        threshold_value=75,
        forward_days=7
    )
    
    # Backtest funding rate anomaly
    results["funding_zscore"] = backtester.backtest_zscore_signal(
        signal_metric="funding_rate_avg",
        zscore_threshold=2.0,
        direction="above",
        forward_days=3
    )
    
    return results


def compute_correlations(self) -> Dict[str, Any]:
    """Compute cross-asset correlations."""
    tracker = CorrelationTracker()
    
    results = {}
    
    # BTC price vs Fear & Greed
    results["btc_vs_fear_greed"] = tracker.compute_rolling_correlation(
        "btc_price", "fear_greed", window_days=30
    )
    
    # BTC price vs funding rate
    results["btc_vs_funding"] = tracker.compute_rolling_correlation(
        "btc_price", "funding_rate_avg", window_days=30
    )
    
    return results


# Monkey-patch the methods onto the class
SovereignIntelTerminal.run_backtests = run_backtests
SovereignIntelTerminal.compute_correlations = compute_correlations


# ============================================================================
# MACRO DATA - FRED INTEGRATION (Grok's correction applied)
# ============================================================================

class MacroDataIngester:
    """
    Fetch macro data from FRED (Federal Reserve Economic Data).
    Free API key from fred.stlouisfed.org
    
    Key series:
    - DGS10: 10-Year Treasury Yield
    - DGS2: 2-Year Treasury Yield  
    - DTWEXBGS: Trade Weighted Dollar Index
    - GOLDAMGBD228NLBM: Gold Price
    - CPIAUCSL: CPI (inflation)
    """
    
    def __init__(self):
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
        self.api_key = os.environ.get("FRED_API_KEY")
    
    def _fetch_series(self, series_id: str, limit: int = 30) -> Optional[List[Dict]]:
        """Fetch a FRED series."""
        if not self.api_key:
            logger.warning("FRED_API_KEY not set - macro data unavailable")
            return None
        
        try:
            url = f"{self.base_url}?series_id={series_id}&api_key={self.api_key}&file_type=json&limit={limit}&sort_order=desc"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("observations", [])
        except Exception as e:
            logger.error(f"FRED fetch error for {series_id}: {e}")
            return None
    
    def _store(self, source: str, metric: str, value: float, raw: Any = None):
        """Store datapoint."""
        conn = get_db()
        conn.execute(
            "INSERT INTO datapoints (ts_utc, source, metric, value, raw_json) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), source, metric, value,
             json.dumps(raw) if raw else None)
        )
        conn.commit()
        conn.close()
    
    def ingest_yields(self) -> bool:
        """Fetch Treasury yields."""
        success = True
        
        # 10-Year Treasury
        obs = self._fetch_series("DGS10", limit=1)
        if obs and obs[0].get("value") != ".":
            try:
                value = float(obs[0]["value"])
                self._store("fred", "us10y_yield", value, obs[0])
                logger.info(f"Stored US10Y: {value}%")
            except (ValueError, KeyError):
                success = False
        else:
            success = False
        
        # 2-Year Treasury
        obs = self._fetch_series("DGS2", limit=1)
        if obs and obs[0].get("value") != ".":
            try:
                value = float(obs[0]["value"])
                self._store("fred", "us2y_yield", value, obs[0])
                logger.info(f"Stored US2Y: {value}%")
            except (ValueError, KeyError):
                success = False
        
        return success
    
    def ingest_yield_curve(self) -> bool:
        """Calculate yield curve (10Y - 2Y spread)."""
        conn = get_db()
        
        cursor = conn.execute(
            "SELECT value FROM datapoints WHERE metric = 'us10y_yield' ORDER BY ts_utc DESC LIMIT 1"
        )
        row_10y = cursor.fetchone()
        
        cursor = conn.execute(
            "SELECT value FROM datapoints WHERE metric = 'us2y_yield' ORDER BY ts_utc DESC LIMIT 1"
        )
        row_2y = cursor.fetchone()
        conn.close()
        
        if row_10y and row_2y:
            spread = row_10y[0] - row_2y[0]
            self._store("fred", "yield_curve_spread", spread, {"us10y": row_10y[0], "us2y": row_2y[0]})
            logger.info(f"Stored yield curve spread: {spread:.2f}%")
            return True
        
        return False
    
    def ingest_dollar_index(self) -> bool:
        """Fetch Trade Weighted Dollar Index."""
        obs = self._fetch_series("DTWEXBGS", limit=1)
        if obs and obs[0].get("value") != ".":
            try:
                value = float(obs[0]["value"])
                self._store("fred", "dxy_index", value, obs[0])
                logger.info(f"Stored DXY: {value}")
                return True
            except (ValueError, KeyError):
                pass
        return False
    
    def ingest_gold(self) -> bool:
        """Fetch Gold price from FRED."""
        obs = self._fetch_series("GOLDAMGBD228NLBM", limit=1)
        if obs and obs[0].get("value") != ".":
            try:
                value = float(obs[0]["value"])
                self._store("fred", "gold_price", value, obs[0])
                logger.info(f"Stored Gold: ${value}")
                return True
            except (ValueError, KeyError):
                pass
        return False
    
    def ingest_all(self) -> Dict[str, bool]:
        """Ingest all macro data."""
        if not self.api_key:
            logger.warning("FRED_API_KEY not set - skipping macro ingest")
            return {"status": "skipped", "reason": "no_api_key"}
        
        results = {
            "yields": self.ingest_yields(),
            "yield_curve": self.ingest_yield_curve(),
            "dollar": self.ingest_dollar_index(),
            "gold": self.ingest_gold(),
        }
        
        success_count = sum(1 for v in results.values() if v is True)
        logger.info(f"Macro ingest complete: {success_count}/{len(results)}")
        
        return results


# ============================================================================
# ENHANCED CORRELATION TRACKER (with macro pairs)
# ============================================================================

class EnhancedCorrelationTracker(CorrelationTracker):
    """
    Extended correlation tracker with macro pairs.
    """
    
    def compute_all_correlations(self) -> Dict[str, Any]:
        """Compute all relevant correlation pairs."""
        results = {}
        
        # Crypto correlations
        pairs = [
            ("btc_price", "fear_greed"),
            ("btc_price", "funding_rate_avg"),
            ("btc_price", "mempool_tx_count"),
        ]
        
        # Macro correlations (if FRED data available)
        macro_pairs = [
            ("btc_price", "us10y_yield"),
            ("btc_price", "yield_curve_spread"),
            ("btc_price", "dxy_index"),
            ("btc_price", "gold_price"),
        ]
        
        for metric_a, metric_b in pairs + macro_pairs:
            try:
                result = self.compute_rolling_correlation(metric_a, metric_b, window_days=30)
                key = f"{metric_a}_vs_{metric_b}"
                results[key] = result
            except Exception as e:
                logger.debug(f"Correlation {metric_a}/{metric_b} failed: {e}")
        
        return results


# ============================================================================
# MACRO SIGNAL COMPUTER
# ============================================================================

class MacroSignalComputer:
    """
    Compute signals from macro data.
    """
    
    def _get_latest(self, metric: str) -> Optional[Tuple[str, float]]:
        """Get most recent value for a metric."""
        conn = get_db()
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = ? ORDER BY ts_utc DESC LIMIT 1",
            (metric,)
        )
        result = cursor.fetchone()
        conn.close()
        return (result[0], result[1]) if result else None
    
    def compute_yield_curve_signal(self) -> Optional[Signal]:
        """
        Yield curve inversion/steepening signal.
        
        Inverted curve (negative spread) historically bearish for risk assets short-term,
        but steepening from inversion can signal recovery.
        """
        latest = self._get_latest("yield_curve_spread")
        if not latest:
            return None
        
        ts, spread = latest
        
        # Deep inversion
        if spread <= -0.5:
            return Signal(
                name="Yield Curve: Deep Inversion",
                category="macro",
                direction=Direction.BEARISH,
                strength=SignalStrength.MODERATE,
                metric="yield_curve_spread",
                value=spread,
                zscore=None,
                percentile=None,
                datapoints_used=1,
                observation=f"Yield curve spread at {spread:.2f}% (10Y-2Y). Deep inversion.",
                implication="Historically signals recession risk. Risk assets may face headwinds.",
                action="Monitor for steepening as potential bull signal. Reduce risk exposure.",
                invalidation="Curve steepens above 0%.",
                edge_decay_hours=336,  # 2 weeks
                source="fred",
                timestamp=ts
            )
        
        # Steepening from inversion (bullish)
        elif 0 < spread <= 0.5:
            return Signal(
                name="Yield Curve: Steepening",
                category="macro",
                direction=Direction.BULLISH,
                strength=SignalStrength.WEAK,
                metric="yield_curve_spread",
                value=spread,
                zscore=None,
                percentile=None,
                datapoints_used=1,
                observation=f"Yield curve spread at {spread:.2f}% (10Y-2Y). Recently un-inverted.",
                implication="Steepening from inversion historically bullish for risk assets.",
                action="Monitor for confirmation. Consider adding risk exposure.",
                invalidation="Curve re-inverts below 0%.",
                edge_decay_hours=336,
                source="fred",
                timestamp=ts
            )
        
        return None
    
    def compute_dxy_signal(self) -> Optional[Signal]:
        """
        Dollar strength/weakness signal.
        Strong dollar typically bearish for BTC (inversely correlated).
        """
        # Need historical data for z-score
        conn = get_db()
        cursor = conn.execute(
            "SELECT ts_utc, value FROM datapoints WHERE metric = 'dxy_index' ORDER BY ts_utc DESC LIMIT 60"
        )
        history = cursor.fetchall()
        conn.close()
        
        if len(history) < 15:
            return None
        
        current = history[0][1]
        ts = history[0][0]
        values = [h[1] for h in history]
        
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        zscore = (current - mean) / stdev if stdev > 0 else 0
        
        if zscore >= 2.0:
            return Signal(
                name="Dollar: Extreme Strength",
                category="macro",
                direction=Direction.BEARISH,
                strength=SignalStrength.MODERATE,
                metric="dxy_index",
                value=current,
                zscore=zscore,
                percentile=None,
                datapoints_used=len(values),
                observation=f"DXY at {current:.1f} ({zscore:.1f}σ above 60-day mean).",
                implication="Strong dollar historically headwind for BTC. Inverse correlation.",
                action="Reduce BTC exposure or hedge. Wait for dollar weakness.",
                invalidation="DXY drops below mean.",
                edge_decay_hours=168,
                source="fred",
                timestamp=ts
            )
        
        elif zscore <= -2.0:
            return Signal(
                name="Dollar: Extreme Weakness",
                category="macro",
                direction=Direction.BULLISH,
                strength=SignalStrength.MODERATE,
                metric="dxy_index",
                value=current,
                zscore=zscore,
                percentile=None,
                datapoints_used=len(values),
                observation=f"DXY at {current:.1f} ({abs(zscore):.1f}σ below 60-day mean).",
                implication="Weak dollar historically tailwind for BTC. Liquidity seeking yield.",
                action="Favorable environment for BTC. Consider adding exposure.",
                invalidation="DXY rises above mean.",
                edge_decay_hours=168,
                source="fred",
                timestamp=ts
            )
        
        return None
    
    def compute_btc_gold_correlation_signal(self) -> Optional[Signal]:
        """
        BTC-Gold correlation signal.
        When BTC correlates highly with gold, "digital gold" narrative strengthening.
        """
        conn = get_db()
        cursor = conn.execute(
            "SELECT correlation FROM correlations WHERE metric_a = 'btc_price' AND metric_b = 'gold_price' ORDER BY ts_utc DESC LIMIT 1"
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        corr = result[0]
        
        if corr >= 0.7:
            return Signal(
                name="BTC-Gold: High Correlation",
                category="macro",
                direction=Direction.BULLISH,
                strength=SignalStrength.WEAK,
                metric="btc_gold_correlation",
                value=corr,
                zscore=None,
                percentile=None,
                datapoints_used=30,
                observation=f"BTC-Gold correlation at {corr:.2f} (strong positive).",
                implication="'Digital gold' narrative strengthening. Institutional safe-haven positioning.",
                action="Favorable macro narrative. Monitor for continuation.",
                invalidation="Correlation breaks down below 0.4.",
                edge_decay_hours=336,
                source="computed",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        return None


# ============================================================================
# INTEGRATE INTO MAIN ENGINE
# ============================================================================

def ingest_macro_data(self) -> Dict[str, Any]:
    """Ingest macro data from FRED."""
    macro_ingester = MacroDataIngester()
    return macro_ingester.ingest_all()


def compute_macro_signals(self) -> List[Signal]:
    """Compute macro-based signals."""
    computer = MacroSignalComputer()
    signals = []
    
    computers = [
        computer.compute_yield_curve_signal,
        computer.compute_dxy_signal,
        computer.compute_btc_gold_correlation_signal,
    ]
    
    for compute in computers:
        try:
            signal = compute()
            if signal:
                signals.append(signal)
        except Exception as e:
            logger.error(f"Macro signal error: {e}")
    
    return signals


def run_full_with_macro(self) -> Dict[str, Any]:
    """Full cycle including macro data."""
    # Standard ingest
    self.ingester.ingest_all()
    
    # Macro ingest
    macro_results = ingest_macro_data(self)
    
    # Compute standard signals
    signals = self.computer.compute_all_signals()
    
    # Compute macro signals
    macro_signals = compute_macro_signals(self)
    signals.extend(macro_signals)
    
    # Compute correlations
    corr_tracker = EnhancedCorrelationTracker()
    correlations = corr_tracker.compute_all_correlations()
    
    # Sort all signals by strength
    signals.sort(key=lambda s: s.strength.value, reverse=True)
    
    # Detect regime
    regime = self.regime.detect(signals)
    
    # Generate report
    report = self.reporter.generate_full_report(signals, regime)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "regime": regime.regime.value,
        "regime_confidence": regime.confidence,
        "signals_triggered": len(signals),
        "signals": [s.to_dict() for s in signals],
        "correlations": correlations,
        "macro_ingest": macro_results,
        "report": report
    }


# Monkey-patch onto main class
SovereignIntelTerminal.ingest_macro_data = ingest_macro_data
SovereignIntelTerminal.compute_macro_signals = compute_macro_signals
SovereignIntelTerminal.run_full_with_macro = run_full_with_macro


# ============================================================================
# UPDATED CLI WITH MACRO SUPPORT
# ============================================================================

if __name__ == "__main__":
    import sys
    
    terminal = SovereignIntelTerminal()
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "ingest":
            result = terminal.ingest()
            # Also try macro ingest
            try:
                macro_result = terminal.ingest_macro_data()
                result["macro"] = macro_result
            except Exception as e:
                result["macro"] = {"error": str(e)}
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "analyze":
            result = terminal.analyze()
            print(result["report"])
        elif cmd == "run":
            # Use full run with macro if FRED key available
            if os.environ.get("FRED_API_KEY"):
                result = terminal.run_full_with_macro()
            else:
                result = terminal.run()
            print(result["report"])
        elif cmd == "macro":
            # Macro-only ingest
            result = terminal.ingest_macro_data()
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "backtest":
            result = terminal.run_backtests()
            print(json.dumps(result, indent=2, default=str))
        elif cmd == "correlations":
            result = terminal.compute_correlations()
            print(json.dumps(result, indent=2, default=str))
        else:
            print("Usage: python sovereign_intel_terminal.py [ingest|analyze|run|macro|backtest|correlations]")
    else:
        # Default: full cycle with macro
        if os.environ.get("FRED_API_KEY"):
            result = terminal.run_full_with_macro()
        else:
            result = terminal.run()
        print(result["report"])
        
        # Save JSON
        with open("data/sovereign_report.json", "w") as f:
            json.dump(result, f, indent=2, default=str)
        print("\n✅ Full report saved to data/sovereign_report.json")
