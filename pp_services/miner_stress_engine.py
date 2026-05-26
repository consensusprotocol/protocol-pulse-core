"""
MINER STRESS & CAPITULATION MODEL — Phase 2 F7
===============================================
Quantitative miner health score 0-100. Predicts capitulation before it happens.
Rule-based weighted sum using hashrate, difficulty, fees, block time, and miner flows.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("miner_stress_engine")

_svc_dir = Path(__file__).resolve().parent
_data_dir = _svc_dir.parent / "data"
_baseline_db = str(_data_dir / "baseline_store.db")


class MinerStressEngine:
    """Compute miner health score and capitulation signals."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Ensure miner_health_history table exists in baseline_store.db."""
        try:
            conn = sqlite3.connect(_baseline_db)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS miner_health_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    score INTEGER NOT NULL,
                    components_json TEXT,
                    recorded_at REAL NOT NULL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Miner stress DB init failed: %s", e)

    def compute_score(self, network_state: dict, mempool_state: dict,
                      hashrate_24h_ago: float = None,
                      miner_to_exchange_ratio: float = None,
                      miner_to_exchange_7d_avg: float = None) -> dict:
        """
        Compute miner health score 0-100.

        Args:
            network_state: SentinelState.network dict
            mempool_state: SentinelState.mempool dict
            hashrate_24h_ago: Previous hashrate for decline detection
            miner_to_exchange_ratio: Current ratio of miner outflows to exchanges
            miner_to_exchange_7d_avg: 7-day average of that ratio

        Returns:
            dict with score, label, components, is_90d_low
        """
        score = 100
        components = {}
        now = time.time()

        # Component 1: Hashrate decline (3d)
        hashrate_3d = network_state.get("hashrate_3d", 0)
        if hashrate_24h_ago and hashrate_24h_ago > 0 and hashrate_3d > 0:
            hr_change_pct = ((hashrate_3d - hashrate_24h_ago) / hashrate_24h_ago) * 100
            if hr_change_pct < -15:
                score -= 40
                components["hashrate_decline"] = {"value": round(hr_change_pct, 1), "penalty": -40}
            elif hr_change_pct < -5:
                score -= 20
                components["hashrate_decline"] = {"value": round(hr_change_pct, 1), "penalty": -20}
            else:
                components["hashrate_decline"] = {"value": round(hr_change_pct, 1), "penalty": 0}
        else:
            components["hashrate_decline"] = {"value": 0, "penalty": 0}

        # Component 2: Difficulty adjustment
        diff_adj = network_state.get("difficulty", 0.0)
        if diff_adj < -8:
            score -= 30
            components["difficulty_adj"] = {"value": round(diff_adj, 2), "penalty": -30}
        elif diff_adj < -3:
            score -= 15
            components["difficulty_adj"] = {"value": round(diff_adj, 2), "penalty": -15}
        else:
            components["difficulty_adj"] = {"value": round(diff_adj, 2), "penalty": 0}

        # Component 3: Fee softness (next-block fee)
        fee_hist = mempool_state.get("fee_histogram", [])
        next_block_fee = 0
        if fee_hist:
            for band in reversed(fee_hist):
                if band.get("count", 0) > 0:
                    next_block_fee = band.get("min_fee", 0)
                    break
        if next_block_fee < 5:
            score -= 10
            components["fee_softness"] = {"value": next_block_fee, "penalty": -10}
        else:
            components["fee_softness"] = {"value": next_block_fee, "penalty": 0}

        # Component 4: Block time anomaly
        avg_block_time = network_state.get("avg_block_time_10", 600)
        if avg_block_time > 750:
            score -= 10
            components["block_time"] = {"value": round(avg_block_time, 1), "penalty": -10}
        else:
            components["block_time"] = {"value": round(avg_block_time, 1), "penalty": 0}

        # Component 5: Miner-to-exchange ratio spike
        if (miner_to_exchange_ratio is not None and miner_to_exchange_7d_avg is not None
                and miner_to_exchange_7d_avg > 0):
            ratio_multiple = miner_to_exchange_ratio / miner_to_exchange_7d_avg
            if ratio_multiple > 2.0:
                score -= 20
                components["miner_exchange_flow"] = {"value": round(ratio_multiple, 2), "penalty": -20}
            else:
                components["miner_exchange_flow"] = {"value": round(ratio_multiple, 2), "penalty": 0}
        else:
            components["miner_exchange_flow"] = {"value": 0, "penalty": 0}

        # Clamp
        score = max(0, min(100, score))

        # Determine label
        if score < 15:
            label = "CAPITULATION_CRITICAL"
        elif score < 30:
            label = "CAPITULATION_WATCH"
        elif score < 60:
            label = "STRESSED"
        else:
            label = "HEALTHY"

        # Check 90-day low
        is_90d_low = self._check_90d_low(score)

        # Store score
        self._store_score(score, components)

        return {
            "score": score,
            "label": label,
            "components": components,
            "is_90d_low": is_90d_low,
            "updated_at": now,
        }

    def _check_90d_low(self, current_score: int) -> bool:
        """Check if current score is the lowest in 90 days."""
        try:
            cutoff = time.time() - 90 * 86400
            conn = sqlite3.connect(_baseline_db)
            row = conn.execute(
                "SELECT MIN(score) FROM miner_health_history WHERE recorded_at > ?",
                (cutoff,)
            ).fetchone()
            conn.close()
            if row and row[0] is not None:
                return current_score <= row[0]
            return True  # First entry = automatically a 90d low
        except Exception:
            return False

    def _store_score(self, score: int, components: dict):
        """Store score in history for trend tracking."""
        try:
            conn = sqlite3.connect(_baseline_db)
            conn.execute(
                "INSERT INTO miner_health_history (score, components_json, recorded_at) VALUES (?, ?, ?)",
                (score, json.dumps(components), time.time())
            )
            # Keep last 2000 entries (~200 days at 10min intervals)
            conn.execute(
                "DELETE FROM miner_health_history WHERE id NOT IN "
                "(SELECT id FROM miner_health_history ORDER BY id DESC LIMIT 2000)"
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("Failed to store miner health score: %s", e)
