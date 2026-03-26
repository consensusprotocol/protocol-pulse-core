"""
PCAF V1 — Data Collector
=========================
Background thread: reads /tmp/sentinel_state.json every 60s, builds PyG graph,
saves as .pkl to data/pcaf_training/.

IMPORT RULE: Load via importlib.util — never `from services.pcaf_data_collector import ...`
"""

import json
import logging
import os
import pickle
import time
from datetime import datetime
from pathlib import Path

import torch
from torch_geometric.data import Data

logger = logging.getLogger("pcaf_data_collector")

STATE_FILE = "/tmp/sentinel_state.json"
TRAINING_DIR = Path(__file__).resolve().parent.parent / "data" / "pcaf_training"
# Keep 90 days of snapshots max
MAX_AGE_DAYS = 90


class DataCollector:
    """Collects sentinel state snapshots and converts them to PyG Data objects."""

    def __init__(self, state_file: str = STATE_FILE, training_dir: Path = TRAINING_DIR):
        self.state_file = state_file
        self.training_dir = training_dir
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self._running = False

    def build_graph(self, state: dict) -> Data:
        """Build a PyG Data object from a sentinel state dict."""
        nodes = []       # list of [8-dim feature vectors]
        node_types = []   # for debugging: "TX", "FEE_BAND", "POOL", "NETWORK"
        edge_src = []
        edge_dst = []

        node_idx = 0

        # ── MEMPOOL TX nodes (whale txs > 10 BTC, max 200) ──
        whale_txs = state.get("mempool", {}).get("whale_txs", [])
        tx_start_idx = node_idx
        for tx in whale_txs[:200]:
            features = [
                float(tx.get("value_btc", tx.get("value", 0))),  # value_btc
                float(tx.get("fee_rate", 0)),        # fee_rate_svb
                float(tx.get("vsize", 0)),           # size_vbytes
                float(tx.get("rbf", 0)),             # rbf_flag
                float(tx.get("age", 0)),             # age_seconds
                float(tx.get("is_replacement", 0)),  # is_replacement
                float(tx.get("output_count", 2)),    # output_count
                float(tx.get("input_count", 1)),     # input_count
            ]
            nodes.append(features)
            node_types.append("TX")
            node_idx += 1
        tx_end_idx = node_idx

        # ── FEE BAND nodes (10 bands from histogram) ──
        fee_histogram = state.get("mempool", {}).get("fee_histogram", [])
        mempool_vsize = max(float(state.get("mempool", {}).get("vsize", 1)), 1.0)
        fee_start_idx = node_idx
        # Parse fee histogram into bands
        bands = self._parse_fee_bands(fee_histogram)
        for band in bands[:10]:
            features = [
                float(band.get("min_fee", 0)),
                float(band.get("max_fee", 0)),
                float(band.get("tx_count", 0)),
                float(band.get("vsize_total", 0)),
                float(band.get("pct_of_mempool", 0)),
                0.0, 0.0, 0.0,  # pad to 8
            ]
            nodes.append(features)
            node_types.append("FEE_BAND")
            node_idx += 1
        fee_end_idx = node_idx

        # ── POOL nodes (from recent blocks) ──
        recent_blocks = state.get("network", {}).get("recent_blocks", [])
        pool_map = {}  # pool_name → {hashrate_pct, blocks_10, blocks_100, ...}
        for i, block in enumerate(recent_blocks[:100]):
            pool = block.get("pool", block.get("extras", {}).get("pool", {}).get("name", "Unknown"))
            if pool not in pool_map:
                pool_map[pool] = {"blocks_10": 0, "blocks_100": 0, "fees": []}
            pool_map[pool]["blocks_100"] += 1
            if i < 10:
                pool_map[pool]["blocks_10"] += 1
            pool_map[pool]["fees"].append(float(block.get("fee", 0)))

        pool_start_idx = node_idx
        total_100 = max(len(recent_blocks[:100]), 1)
        for pool_name, pdata in list(pool_map.items())[:20]:
            hr_pct = pdata["blocks_100"] / total_100 * 100
            avg_fee = sum(pdata["fees"]) / max(len(pdata["fees"]), 1)
            features = [
                hr_pct,
                float(pdata["blocks_10"]),
                float(pdata["blocks_100"]),
                1.0 if pool_name != "Unknown" else 0.0,  # known_pool_flag
                avg_fee,
                0.0,  # orphan_rate_proxy
                0.0, 0.0,  # pad to 8
            ]
            nodes.append(features)
            node_types.append("POOL")
            node_idx += 1
        pool_end_idx = node_idx

        # ── NETWORK node (1 global node) ──
        net = state.get("network", {})
        network_idx = node_idx
        network_features = [
            float(net.get("hashrate_3d", 0)) / 1e18,  # normalize to EH
            float(net.get("next_difficulty_adj_pct", 0)),
            float(net.get("avg_block_time_10", 600)),
            float(state.get("mempool", {}).get("count", 0)),
            float(state.get("mempool", {}).get("vsize", 0)) / 1e6,  # MB
            float(fee_histogram[0].get("min_fee", 0) if isinstance(fee_histogram[0], dict) else fee_histogram[0]) if fee_histogram else 0.0,  # next_block_fee approx
            0.0, 0.0,  # pad to 8
        ]
        nodes.append(network_features)
        node_types.append("NETWORK")
        node_idx += 1

        # ── EDGES ──

        # 1. TX → FEE_BAND (if tx fee_rate in band range)
        for ti in range(tx_start_idx, tx_end_idx):
            tx_fee = nodes[ti][1]  # fee_rate_svb
            for fi in range(fee_start_idx, fee_end_idx):
                if nodes[fi][0] <= tx_fee <= nodes[fi][1]:
                    edge_src.append(ti)
                    edge_dst.append(fi)
                    break

        # 2. TX → POOL (first tx links to first pool for simplicity in v1)
        # In production, would check if tx was in block mined by pool
        pool_list = list(range(pool_start_idx, pool_end_idx))
        for ti in range(tx_start_idx, min(tx_end_idx, tx_start_idx + 50)):
            if pool_list:
                edge_src.append(ti)
                edge_dst.append(pool_list[ti % len(pool_list)])

        # 3. FEE_BAND → NETWORK
        for fi in range(fee_start_idx, fee_end_idx):
            edge_src.append(fi)
            edge_dst.append(network_idx)

        # 4. POOL → NETWORK
        for pi in range(pool_start_idx, pool_end_idx):
            edge_src.append(pi)
            edge_dst.append(network_idx)

        # 5. TX → TX (prefix-based approximation, max 50 edges)
        tx_count = tx_end_idx - tx_start_idx
        tx_edges = 0
        for i in range(tx_start_idx, tx_end_idx):
            for j in range(i + 1, min(tx_end_idx, i + 5)):
                if tx_edges >= 50:
                    break
                # Connect nearby transactions (temporal proximity ≈ UTXO relation)
                edge_src.append(i)
                edge_dst.append(j)
                edge_src.append(j)
                edge_dst.append(i)
                tx_edges += 2
            if tx_edges >= 50:
                break

        # Build tensors
        if not nodes:
            # Empty graph fallback — single dummy node
            nodes = [[0.0] * 8]
            node_types = ["EMPTY"]

        x = torch.tensor(nodes, dtype=torch.float32)

        if edge_src:
            edge_index = torch.tensor([edge_src, edge_dst], dtype=torch.long)
        else:
            edge_index = torch.zeros((2, 0), dtype=torch.long)

        data = Data(x=x, edge_index=edge_index)
        data.node_types = node_types
        data.snapshot_time = time.time()

        return data

    def _parse_fee_bands(self, histogram: list) -> list:
        """Parse fee histogram into 10 bands. Accepts both dict-format and flat format."""
        if not histogram:
            return [{"min_fee": 0, "max_fee": 0, "tx_count": 0,
                     "vsize_total": 0, "pct_of_mempool": 0}]

        # Dict-format: [{"min_fee": 1, "max_fee": 5, "vsize": 0, "count": 0}, ...]
        if isinstance(histogram[0], dict):
            total_vsize = sum(float(b.get("vsize", 0)) for b in histogram) or 1.0
            bands = []
            for b in histogram[:10]:
                vs = float(b.get("vsize", 0))
                bands.append({
                    "min_fee": float(b.get("min_fee", 0)),
                    "max_fee": float(b.get("max_fee", 0)),
                    "tx_count": int(b.get("count", 0)),
                    "vsize_total": vs,
                    "pct_of_mempool": (vs / total_vsize) * 100,
                })
            return bands

        # Flat format: [fee_rate, vsize, fee_rate, vsize, ...]
        bands = []
        total_vsize = 0
        entries = []
        for i in range(0, len(histogram) - 1, 2):
            fee_rate = float(histogram[i])
            vsize = float(histogram[i + 1])
            entries.append((fee_rate, vsize))
            total_vsize += vsize

        if not entries:
            return [{"min_fee": 0, "max_fee": 0, "tx_count": 0,
                     "vsize_total": 0, "pct_of_mempool": 0}]

        entries.sort(key=lambda e: e[0])
        chunk = max(len(entries) // 10, 1)
        for i in range(0, len(entries), chunk):
            chunk_entries = entries[i:i + chunk]
            if not chunk_entries:
                continue
            min_fee = chunk_entries[0][0]
            max_fee = chunk_entries[-1][0]
            vsize_total = sum(e[1] for e in chunk_entries)
            bands.append({
                "min_fee": min_fee,
                "max_fee": max_fee,
                "tx_count": len(chunk_entries),
                "vsize_total": vsize_total,
                "pct_of_mempool": (vsize_total / max(total_vsize, 1)) * 100,
            })

        return bands[:10]

    def save_snapshot(self, data: Data) -> None:
        """Save a PyG Data object as a timestamped pickle."""
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = self.training_dir / f"{ts}.pkl"
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def get_corpus_stats(self) -> dict:
        """Return stats about collected training data."""
        files = sorted(self.training_dir.glob("*.pkl"))
        if not files:
            return {"count": 0, "size_bytes": 0, "oldest": None, "newest": None}
        total_size = sum(f.stat().st_size for f in files)
        return {
            "count": len(files),
            "size_bytes": total_size,
            "oldest": files[0].stem,
            "newest": files[-1].stem,
        }

    def cleanup_old(self):
        """Remove snapshots older than MAX_AGE_DAYS."""
        cutoff = time.time() - (MAX_AGE_DAYS * 86400)
        for f in self.training_dir.glob("*.pkl"):
            if f.stat().st_mtime < cutoff:
                f.unlink()

    def run(self):
        """Main collection loop — runs as daemon thread. Catches all exceptions."""
        self._running = True
        logger.info("PCAF data collector started. Training dir: %s", self.training_dir)

        while self._running:
            try:
                if not os.path.exists(self.state_file):
                    time.sleep(10)
                    continue

                with open(self.state_file, "r") as f:
                    state = json.load(f)

                data = self.build_graph(state)
                self.save_snapshot(data)

                stats = self.get_corpus_stats()
                if stats["count"] % 100 == 0:
                    logger.info("PCAF training corpus: %d snapshots, %.1f MB",
                                stats["count"], stats["size_bytes"] / 1e6)

                # Cleanup old files every 1000 snapshots
                if stats["count"] % 1000 == 0:
                    self.cleanup_old()

            except Exception as e:
                logger.warning("PCAF data collector error: %s", e)

            time.sleep(60)

    def stop(self):
        self._running = False
