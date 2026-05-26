"""
WHALE COORDINATION DETECTION — Phase 3 F1
==========================================
Detects synchronized large UTXO movement from taint-linked clusters.
Cross-references with social sentiment tier1_signal for elevation.

Load via importlib.util — never 'from pp_services.whale_coordination_engine import ...'
"""

import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("sentinel.whale_coord")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = str(_DATA_DIR / "sentinel_alerts.db")

WHALE_THRESHOLD_BTC = 100
COORDINATION_WINDOW = 90 * 60  # 90 minutes
COORDINATION_MIN_TXS = 3


class WhaleCoordinationEngine:
    """Detect synchronized whale movements via taint-linked UTXO clustering."""

    def analyze(self, whale_txs: list, tier1_social_active: bool = False) -> dict:
        """
        Analyze whale txs for coordination patterns.

        Args:
            whale_txs: list of dicts from SentinelState.mempool.whale_txs
            tier1_social_active: whether tier1 social signal is active

        Returns:
            dict matching SentinelState.whale_coordination schema
        """
        now = time.time()
        cutoff = now - COORDINATION_WINDOW

        # Filter to recent large txs
        recent_whales = []
        for tx in whale_txs:
            tx_btc = tx.get("value", 0) / 1e8 if isinstance(tx.get("value"), (int, float)) else 0
            if tx_btc < WHALE_THRESHOLD_BTC:
                continue
            tx_time = tx.get("time", tx.get("firstSeen", now))
            if isinstance(tx_time, (int, float)) and tx_time < cutoff:
                continue
            dest = tx.get("address", tx.get("to", ""))
            if not dest:
                vout = tx.get("vout", [])
                for o in vout:
                    a = o.get("scriptpubkey_address", o.get("address", ""))
                    if a:
                        dest = a
                        break
            recent_whales.append({
                "btc": round(tx_btc, 2),
                "address": dest,
                "time": tx_time if isinstance(tx_time, (int, float)) else now,
            })

        tx_count = len(recent_whales)
        total_btc = sum(w["btc"] for w in recent_whales)

        # Check taint linking via dark_pool_addresses table
        taint_linked = False
        if tx_count >= 2:
            taint_linked = self._check_taint_link(recent_whales)

        # Determine signal
        if tx_count >= COORDINATION_MIN_TXS and taint_linked and tier1_social_active:
            signal = "WATCH"
        elif tx_count >= COORDINATION_MIN_TXS or taint_linked:
            signal = "NOTE"
        else:
            signal = "CLEAR"

        return {
            "signal": signal,
            "tx_count_90min": tx_count,
            "taint_linked": taint_linked,
            "tier1_social_active": tier1_social_active,
            "total_btc_90min": round(total_btc, 2),
            "updated_at": now,
        }

    def _check_taint_link(self, whales: list) -> bool:
        """Check if 2+ whale destinations appear in dark_pool_addresses table."""
        addresses = [w["address"] for w in whales if w["address"]]
        if len(addresses) < 2:
            return False

        try:
            conn = sqlite3.connect(_DB_PATH)
            placeholders = ",".join("?" * len(addresses))
            cur = conn.execute(
                f"SELECT COUNT(DISTINCT address) FROM dark_pool_addresses WHERE address IN ({placeholders})",
                addresses,
            )
            row = cur.fetchone()
            conn.close()
            return row[0] >= 2 if row else False
        except Exception as e:
            logger.warning("Taint link check failed: %s", e)
            return False
