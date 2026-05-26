"""
DARK POOL OTC TAINT ANALYSIS — Phase 2 F6
==========================================
Tracks large UTXO movements (>100 BTC) not destined for known exchange or
miner wallets. Clusters within 4h windows signal institutional OTC positioning.
Lightweight address-reuse taint tracking via SQLite.

Load via importlib.util — never 'from pp_services.dark_pool_engine import ...'
"""

import json
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger("sentinel.dark_pool")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_PATH = str(_DATA_DIR / "sentinel_alerts.db")

# Thresholds
WHALE_TX_THRESHOLD_BTC = 100
DARK_POOL_CLUSTER_MIN = 3
WINDOW_4H = 4 * 3600
REUSE_WINDOW_72H = 72 * 3600


class DarkPoolEngine:
    """Rule-based dark pool OTC detection via whale tx destination classification."""

    def __init__(self, custodian_wallets_path=None, miner_wallets_path=None):
        self._known_addresses = set()
        self._load_known_addresses(
            custodian_wallets_path or str(_DATA_DIR / "custodian_wallets.json"),
            miner_wallets_path or str(_DATA_DIR / "miner_wallets.json"),
        )
        self._init_db()

    def _load_known_addresses(self, custodian_path: str, miner_path: str):
        """Load exchange + miner addresses into exclusion set."""
        for path in (custodian_path, miner_path):
            try:
                with open(path) as f:
                    data = json.load(f)
                for w in data.get("wallets", []):
                    addr = w.get("address", "").strip()
                    if addr:
                        self._known_addresses.add(addr)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.warning("Failed to load wallet file %s: %s", path, e)

    def _init_db(self):
        """Create dark_pool_addresses table if it doesn't exist."""
        try:
            conn = sqlite3.connect(_DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dark_pool_addresses (
                    address TEXT PRIMARY KEY,
                    first_seen REAL NOT NULL,
                    last_seen REAL NOT NULL,
                    tx_count INTEGER DEFAULT 1,
                    total_btc REAL DEFAULT 0.0
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Dark pool DB init failed: %s", e)

    def _is_known_address(self, addr: str) -> bool:
        """Check if address belongs to a known exchange or miner."""
        return addr in self._known_addresses

    def _track_address_reuse(self, addr: str, btc_value: float) -> int:
        """Track address in SQLite, return total tx_count for this address."""
        now = time.time()
        try:
            conn = sqlite3.connect(_DB_PATH)
            conn.execute(
                "INSERT OR IGNORE INTO dark_pool_addresses (address, first_seen, last_seen, tx_count, total_btc) "
                "VALUES (?, ?, ?, 1, ?)",
                (addr, now, now, btc_value),
            )
            conn.execute(
                "UPDATE dark_pool_addresses SET last_seen = ?, tx_count = tx_count + 1, total_btc = total_btc + ? "
                "WHERE address = ? AND first_seen < ?",
                (now, btc_value, addr, now),
            )
            cur = conn.execute(
                "SELECT tx_count FROM dark_pool_addresses WHERE address = ?", (addr,)
            )
            row = cur.fetchone()
            conn.commit()
            conn.close()
            return row[0] if row else 1
        except Exception as e:
            logger.error("Address reuse tracking failed: %s", e)
            return 1

    def _cleanup_old_entries(self):
        """Remove entries older than 72h to keep DB lean."""
        cutoff = time.time() - REUSE_WINDOW_72H
        try:
            conn = sqlite3.connect(_DB_PATH)
            conn.execute(
                "DELETE FROM dark_pool_addresses WHERE last_seen < ?", (cutoff,)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Dark pool cleanup failed: %s", e)

    def analyze(self, whale_txs: list) -> dict:
        """
        Analyze whale transactions for dark pool activity.

        Args:
            whale_txs: list of dicts with keys: txid, value (satoshis),
                       vout (list of {scriptpubkey_address, value})

        Returns:
            dict matching SentinelState.dark_pool schema
        """
        now = time.time()
        cutoff_4h = now - WINDOW_4H

        self._cleanup_old_entries()

        dark_pool_candidates = []
        exchange_count = 0

        for tx in whale_txs:
            tx_value_btc = tx.get("value", 0) / 1e8 if isinstance(tx.get("value"), (int, float)) else 0
            if tx_value_btc < WHALE_TX_THRESHOLD_BTC:
                continue

            tx_time = tx.get("time", tx.get("firstSeen", now))
            if isinstance(tx_time, (int, float)) and tx_time < cutoff_4h:
                continue

            vout = tx.get("vout", [])
            if not vout:
                dest_addr = tx.get("address", tx.get("to", ""))
                if dest_addr:
                    if self._is_known_address(dest_addr):
                        exchange_count += 1
                    else:
                        reuse_count = self._track_address_reuse(dest_addr, tx_value_btc)
                        dark_pool_candidates.append({
                            "address": dest_addr[:12] + "...",
                            "btc": round(tx_value_btc, 2),
                            "reuse_count": reuse_count,
                        })
                continue

            for output in vout:
                addr = output.get("scriptpubkey_address", output.get("address", ""))
                out_btc = output.get("value", 0) / 1e8 if isinstance(output.get("value"), (int, float)) else 0
                if not addr or out_btc < WHALE_TX_THRESHOLD_BTC:
                    continue

                if self._is_known_address(addr):
                    exchange_count += 1
                else:
                    reuse_count = self._track_address_reuse(addr, out_btc)
                    dark_pool_candidates.append({
                        "address": addr[:12] + "...",
                        "btc": round(out_btc, 2),
                        "reuse_count": reuse_count,
                    })

        tx_count_4h = len(dark_pool_candidates)
        volume_4h = sum(c["btc"] for c in dark_pool_candidates)
        total_flow = exchange_count + tx_count_4h
        exchange_pct = round((exchange_count / total_flow * 100) if total_flow > 0 else 0, 1)

        has_reuse = any(c["reuse_count"] > 1 for c in dark_pool_candidates)

        if tx_count_4h >= DARK_POOL_CLUSTER_MIN:
            signal = "ACCUMULATION"
        elif has_reuse:
            signal = "WATCH"
        else:
            signal = "CLEAR"

        top_dest = sorted(dark_pool_candidates, key=lambda x: x["btc"], reverse=True)[:3]

        return {
            "signal": signal,
            "volume_4h_btc": round(volume_4h, 2),
            "tx_count_4h": tx_count_4h,
            "top_destinations": [d["address"] for d in top_dest],
            "exchange_pct": exchange_pct,
            "updated_at": now,
        }
