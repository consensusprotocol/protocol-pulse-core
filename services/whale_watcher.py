"""
Whale watcher service.

Monitors mempool.space for large Bitcoin transfers and returns normalized whale rows.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)


class WhaleWatcher:
    def fetch_live_whales(self, min_btc: float = 10.0) -> List[Dict[str, Any]]:
        whales: List[Dict[str, Any]] = []
        try:
            mempool_resp = requests.get("https://mempool.space/api/mempool/recent", timeout=12)
            if mempool_resp.ok:
                for tx in mempool_resp.json():
                    btc_value = float(tx.get("value", 0) or 0) / 100_000_000
                    if btc_value >= min_btc:
                        whales.append(
                            {
                                "txid": tx.get("txid"),
                                "btc": round(btc_value, 4),
                                "fee": tx.get("fee", 0),
                                "time": int(datetime.utcnow().timestamp() * 1000),
                                "status": "pending",
                            }
                        )

            blocks_resp = requests.get("https://mempool.space/api/blocks", timeout=12)
            if blocks_resp.ok:
                for block in (blocks_resp.json() or [])[:5]:
                    block_id = block.get("id")
                    if not block_id:
                        continue
                    for start_idx in (0, 25):
                        try:
                            txs_resp = requests.get(
                                f"https://mempool.space/api/block/{block_id}/txs/{start_idx}",
                                timeout=15,
                            )
                            if not txs_resp.ok:
                                continue
                            for tx in txs_resp.json():
                                outputs = tx.get("vout") or []
                                total_out = sum((o or {}).get("value", 0) for o in outputs)
                                btc_value = float(total_out) / 100_000_000
                                if btc_value >= min_btc:
                                    whales.append(
                                        {
                                            "txid": tx.get("txid"),
                                            "btc": round(btc_value, 4),
                                            "fee": tx.get("fee", 0),
                                            "time": int(block.get("timestamp", 0) * 1000),
                                            "status": "confirmed",
                                            "block": block.get("height"),
                                        }
                                    )
                        except Exception:
                            continue
        except Exception as e:
            logger.warning("whale watcher fetch failed: %s", e)

        seen = set()
        unique: List[Dict[str, Any]] = []
        for w in whales:
            txid = str(w.get("txid") or "").strip()
            if not txid or txid in seen:
                continue
            seen.add(txid)
            unique.append(w)
        unique.sort(key=lambda x: float(x.get("btc", 0) or 0), reverse=True)
        return unique[:50]


whale_watcher = WhaleWatcher()

