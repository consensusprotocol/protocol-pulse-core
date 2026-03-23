# ML SESSION BUILD-DOC — ENGINEERING AUDIT REPORT
# Protocol Pulse Intelligence Terminal · PCAF v1 + TPA
# Date: 2026-03-23
# Models: GPT-4o, Grok-3 (2 cycles each)
# Synthesized by: Claude Sonnet 4.6

---

## AUDIT PREAMBLE

This report synthesizes two independent models across two reasoning cycles covering ten deep ML engineering questions about the PCAF v1 (GNN Autoencoder) and TPA (Temporal Predictive Analytics) implementation plan for Protocol Pulse's ML Session features. Where models agreed, that consensus is noted. Where they diverged, this audit rules on correctness. Where both missed something, this audit flags it as a **SYNTHESIS FINDING**. Every ruling is grounded in PyTorch Geometric documentation, PyTorch async semantics, and ML engineering best practices.

**Severity legend used throughout:** 🔴 CRITICAL (blocks deploy) · 🟠 IMPORTANT (fix before release) · 🟡 RECOMMENDED (quality improvement) · 🔵 SYNTHESIS FINDING (neither model caught this)

---

## Q1 VERDICT: TORCH_GEOMETRIC INSTALLATION

**Ruling: Grok-3 wins. GPT-4o's fallback claim is dangerously wrong.**

### What Both Models Got Right
Both models produced the same pip command, which is correct:

```bash
pip install torch_geometric --break-system-packages
pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html \
  --break-system-packages
```

Both correctly identified binary incompatibility and CUDA version mismatch as the primary failure modes.

### Critical Divergence — SAGEConv Without torch_scatter

GPT-4o stated: *"SAGEConv specifically can work without these extras, but performance might be suboptimal."*

This is **wrong and dangerous**. Grok-3 correctly identified this as a hard dependency failure. `SAGEConv`'s message-passing aggregation step calls `scatter_add` from `torch_scatter` internally. Without it, PyG will raise:

```
ImportError: 'scatter' requires the 'torch-scatter' package.
```

There is no graceful degradation path. GPT-4o's claim would give engineers false confidence and cause a complete model failure at runtime, not a slow model.

### Definitive Installation Strategy

**Step 1 — Sandbox verification (mandatory before CI/CD):**
```bash
# In isolated environment matching production
python -c "import torch; print(torch.__version__, torch.version.cuda)"
# Must output: 2.6.0  12.4

pip install torch_geometric --break-system-packages
pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html \
  --break-system-packages

# Smoke test
python -c "
from torch_geometric.nn import SAGEConv
import torch
conv = SAGEConv(8, 64)
x = torch.randn(5, 8)
edge_index = torch.tensor([[0,1,2],[1,2,3]], dtype=torch.long)
print('SAGEConv OK:', conv(x, edge_index).shape)
"
```

**Step 2 — Fallback if wheels are unavailable for torch 2.6.0+cu124:**

The PyG CDN lags new PyTorch releases by 4–8 weeks. If `No matching distribution found`:

```bash
# Option A: Downgrade to last known-good combination
pip install torch==2.3.0+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.3.0+cu121.html

# Option B: Build from source (slower, ~20min, but uses exact CUDA)
pip install torch_geometric --no-binary torch_geometric
TORCH_CUDA_ARCH_LIST="8.9" pip install torch_scatter torch_sparse \
  --no-binary torch_scatter,torch_sparse
# RTX 4090 = Compute Capability 8.9
```

**Step 3 — Hard deployment gate:**

Add this to the PCAF v1 startup health check. If this fails, refuse to start:

```python
def verify_pyg_installation() -> None:
    """
    Hard gate: PCAF v1 cannot start without torch_scatter.
    SAGEConv has no fallback path. Fail loudly at boot, not at inference time.
    """
    try:
        import torch_scatter
        from torch_geometric.nn import SAGEConv
        import torch
        # Minimal functional test — not just import check
        conv = SAGEConv(4, 8)
        x = torch.randn(3, 4)
        edge_index = torch.tensor([[0, 1], [1, 2]], dtype=torch.long)
        out = conv(x, edge_index)
        assert out.shape == (3, 8), "SAGEConv output shape mismatch"
    except ImportError as e:
        raise RuntimeError(
            f"PCAF v1 hard dependency missing: {e}. "
            "Install torch_scatter before deploying. There is no fallback."
        ) from e
    except Exception as e:
        raise RuntimeError(f"PyG smoke test failed: {e}") from e
```

### 🔵 SYNTHESIS FINDING — Q1
Neither model flagged that `--break-system-packages` is a Debian/Ubuntu-specific pip flag and will cause `pip` to error on systems using virtual environments or conda. The correct cross-platform approach: always install inside a `venv` or conda env and omit this flag. The flag should not appear in production deployment scripts.

---

## Q2 VERDICT: GRAPHSAGE AUTOENCODER ARCHITECTURE

**Ruling: Grok-3's architecture is more correct. The definitive answer requires one additional fix neither model fully implemented.**

### The Core Problem Both Models Identified (Correctly)

The original spec mirrors encoder layers in the decoder without passing `edge_index`. A decoder `SAGEConv` without edge information performs neighborhood aggregation over nothing — it degenerates to a linear layer. This is a **confirmed architectural bug** (see CONFIRMED BUGS #1).

### Why GPT-4o's Decoder is Incomplete

GPT-4o's forward pass:
```python
def forward(self, data):
    latent = self.encoder(x, edge_index)
    reconstructed = self.decoder(latent)  # ← edge_index never passed to decoder
    return reconstructed, latent
```
The decoder receives only `latent` — no `edge_index`, no `batch`. This is exactly the bug being discussed. GPT-4o diagnosed it but failed to fix it in code.

### Why Grok-3's Fix is Mostly Correct

Grok-3 passed `edge_index` and `batch` to the decoder and correctly expanded the graph-level latent to per-node representations via `latent[batch]`. This is the right approach. However, Grok-3's encoder uses a single global `fc` layer after pooling to reduce to 128, then a bottleneck to 32 — this is correct per spec.

### Definitive Architecture + Forward Pass

The definitive implementation addresses one issue Grok-3 missed: the `latent[batch]` expansion only works if batch indices are contiguous and correctly assigned. For a single-graph inference scenario (PCAF v1 processes one graph at a time), `batch` will be all zeros, and `latent[batch]` produces a repeated row — which is correct but should be made explicit.

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, global_mean_pool
from torch_geometric.data import Data


class ChainStateEncoder(nn.Module):
    """
    GraphSAGE encoder: node features → graph-level latent vector.
    Architecture: 8 → 64 → 128 → 256 (per node), then global pool → 128 → 32.
    """
    def __init__(self, in_channels: int = 8, latent_dim: int = 32):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, 64)
        self.conv2 = SAGEConv(64, 128)
        self.conv3 = SAGEConv(128, 256)
        self.pool_proj = nn.Linear(256, 128)
        self.bottleneck = nn.Linear(128, latent_dim)
        self.dropout = nn.Dropout(p=0.1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            latent: [num_graphs, latent_dim] — graph-level embedding
            node_x: [num_nodes, 256] — final node embeddings (for decoder skip)
        """
        x = F.relu(self.conv1(x, edge_index))
        x = self.dropout(x)
        x = F.relu(self.conv2(x, edge_index))
        x = self.dropout(x)
        node_x = F.relu(self.conv3(x, edge_index))  # [num_nodes, 256]

        graph_emb = global_mean_pool(node_x, batch)  # [num_graphs, 256]
        graph_emb = F.relu(self.pool_proj(graph_emb))  # [num_graphs, 128]
        latent = self.bottleneck(graph_emb)             # [num_graphs, 32]
        return latent, node_x


class ChainStateDecoder(nn.Module):
    """
    GraphSAGE decoder: latent vector → reconstructed node features.

    CRITICAL: edge_index and batch MUST be passed from the original graph.
    SAGEConv in the decoder is meaningless without edge_index — it degenerates
    to a linear layer with no neighborhood aggregation.
    """
    def __init__(self, latent_dim: int = 32, out_channels: int = 8):
        super().__init__()
        self.expand = nn.Linear(latent_dim, 256)
        self.conv1 = SAGEConv(256, 128)
        self.conv2 = SAGEConv(128, 64)
        self.conv3 = SAGEConv(64, out_channels)
        self.dropout = nn.Dropout(p=0.1)

    def forward(
        self,
        latent: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            latent: [num_graphs, latent_dim]
            edge_index: original graph edge indices [2, num_edges]
            batch: node-to-graph assignment [num_nodes]
        Returns:
            reconstructed: [num_nodes, out_channels]
        """
        # Expand graph-level latent to per-node representation
        # latent[batch] maps each node to its graph's latent vector
        node_latent = latent[batch]                          # [num_nodes, latent_dim]
        x = F.relu(self.expand(node_latent))                # [num_nodes, 256]

        # Graph-guided reconstruction — edge_index is essential here
        x = F.relu(self.conv1(x, edge_index))
        x = self.dropout(x)
        x = F.relu(self.conv2(x, edge_index))
        x = self.conv3(x, edge_index)                       # No activation on output
        return x


class ChainStateAutoencoder(nn.Module):
    """
    Full GNN autoencoder for Bitcoin chain state anomaly detection.
    Input: PyG Data object with heterogeneous node types padded to 8 features.
    Output: Reconstruction error → anomaly score 0-100.
    """
    def __init__(self, in_channels: int = 8, latent_dim: int = 32):
        super().__init__()
        self.encoder = ChainStateEncoder(in_channels, latent_dim)
        self.decoder = ChainStateDecoder(latent_dim, in_channels)

    def forward(
        self,
        data: Data,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            reconstructed: [num_nodes, in_channels]
            latent: [num_graphs, latent_dim]
        """
        x, edge_index, batch = data.x, data.edge_index, data.batch
        # Ensure batch exists for single-graph inference
        if batch is None:
            batch = torch.zeros(x.size(0), dtype=torch.long, device=x.device)

        latent, _ = self.encoder(x, edge_index, batch)
        reconstructed = self.decoder(latent, edge_index, batch)
        return reconstructed, latent

    def reconstruction_loss(self, data: Data) -> torch.Tensor:
        """MSE loss for training."""
        reconstructed, _ = self.forward(data)
        return F.mse_loss(reconstructed, data.x)

    @torch.no_grad()
    def anomaly_score(
        self,
        data: Data,
        p95_threshold: float,
        p99_threshold: float,
    ) -> dict:
        """
        Returns anomaly score 0-100 and severity tier.
        Thresholds must be calibrated on a representative validation set.
        """
        self.eval()
        reconstructed, latent = self.forward(data)
        per_node_mse = F.mse_loss(reconstructed, data.x, reduction='none').mean(dim=1)
        graph_mse = per_node_mse.mean().item()

        # Normalize to 0-100 against calibrated p99 threshold
        score = min(100.0, max(0.0, (graph_mse / p99_threshold) * 100.0))

        return {
            "score": round(score, 2),
            "raw_mse": graph_mse,
            "severity": (
                "CRITICAL" if graph_mse > p99_threshold else
                "ELEVATED" if graph_mse > p95_threshold else
                "NOMINAL"
            ),
            "latent_norm": latent.norm(dim=-1).mean().item(),
        }
```

### VGAE Recommendation Assessment

Grok-3 recommended switching to VGAE with GCN. This audit endorses this as a **future improvement** (see IMPROVEMENTS section) but not a blocker. GraphSAGE with the fixes above is deployable. VGAE adds implementation complexity (reparameterization trick, KL loss weighting, edge reconstruction head) that is out of scope for v1. Ship the fixed GraphSAGE autoencoder now; evaluate VGAE for v2.

---

## Q3 VERDICT: GRAPH CONSTRUCTION DATA CONTRACT

**Ruling: Grok-3's structure is better; GPT-4o's edge cases are incomplete. The definitive guard code is below.**

Both models identified the three failure cases correctly. GPT-4o's handling of stale mempool data (skip entirely and return `None`) is correct behavior. Grok-3's guard for case (b) stopped mid-sentence in the source material, so the definitive complete implementation is:

```python
import time
import logging
import torch
from torch_geometric.data import Data
from typing import Optional

logger = logging.getLogger(__name__)

# Sentinel values for data quality tracking
STALE_THRESHOLD_SECONDS = 900   # 15 minutes
MAX_WHALE_TXS = 200
NODE_FEATURE_DIM = 8


class GraphConstructionError(Exception):
    """Raised when graph cannot be constructed and inference must be skipped."""
    pass


def build_chain_state_graph(state: dict) -> Optional[Data]:
    """
    Build a PyG Data object from a SentinelState snapshot.

    Returns None if data is stale (caller must skip inference and log).
    Raises GraphConstructionError on unrecoverable structural failures.
    Degrades gracefully on missing optional node types.

    Node types (all padded to NODE_FEATURE_DIM=8):
        TX    — whale mempool transactions (0 to MAX_WHALE_TXS)
        FEE   — fee band nodes (always present, 6 bands)
        POOL  — mining pool nodes (1 to N)
        NET   — network-level singleton node (always 1)
    """

    # ── GUARD 1: Stale mempool data ──────────────────────────────────────────
    # If mempool data is >15 minutes old, the graph reflects a past state.
    # Inference on stale data produces misleading anomaly scores.
    # Action: return None — caller must log and skip this inference cycle.
    mempool = state.get("mempool", {})
    updated_at = mempool.get("updated_at", 0)
    data_age = time.time() - updated_at

    if data_age > STALE_THRESHOLD_SECONDS:
        logger.warning(
            "Skipping graph construction: mempool data is %.0fs old "
            "(threshold: %ds). Anomaly score will not be emitted this cycle.",
            data_age, STALE_THRESHOLD_SECONDS,
        )
        return None  # Caller must handle None — do not infer on stale state

    # ── GUARD 2: Zero whale TXs ───────────────────────────────────────────────
    # Empty TX node set is valid — PyG handles zero-row tensors correctly.
    # The graph remains connected via FEE/POOL/NET nodes.
    # Anomaly detection degrades (no TX topology signals) but does not crash.
    whale_txs = mempool.get("whale_txs", [])
    if len(whale_txs) == 0:
        logger.info(
            "No whale TXs in mempool. TX node set will be empty. "
            "Anomaly detection operating on fee/pool/network signals only."
        )
        tx_tensor = torch.zeros((0, NODE_FEATURE_DIM), dtype=torch.float32)
    else:
        tx_rows = []
        for tx in whale_txs[:MAX_WHALE_TXS]:
            row = [
                float(tx.get("value_btc", 0.0)),
                float(tx.get("fee_rate_svb", 0.0)),
                float(tx.get("size_vbytes", 0.0)),
                float(tx.get("rbf_flag", 0)),
                float(tx.get("age_seconds", 0.0)),
                float(tx.get("is_replacement", 0)),
                float(tx.get("output_count", 0)),
                float(tx.get("input_count", 0)),
            ]
            tx_rows.append(row)
        tx_tensor = torch.tensor(tx_rows, dtype=torch.float32)  # [N_tx, 8]

    # ── GUARD 3: Single mining pool ───────────────────────────────────────────
    # 1 POOL node is valid. PyG does not require multiple nodes per type.
    # SAGEConv aggregates over 0 neighbors for an isolated node — returns
    # self-features only, which is correct degenerate behavior.
    # Log at INFO so engineers can track pool concentration events.
    recent_blocks = state.get("network", {}).get("recent_blocks", [])
    if len(recent_blocks) == 0:
        logger.warning(
            "No recent blocks found. Using single synthetic POOL node with "
            "zero features. Pool-based anomaly signals unavailable."
        )
        pool_tensor = torch.zeros((1, NODE_FEATURE_DIM), dtype=torch.float32)
    else:
        pool_ids = {}
        for block in recent_blocks[:100]:
            pool_name = block.get("pool", "Unknown")
            if pool_name not in pool_ids:
                pool_ids[pool_name] = {
                    "hashrate_pct": 0.0,
                    "block_count_10": 0,
                    "block_count_100": 0,
                    "avg_fee_earned": 0.0,
                    "orphan_rate": 0.0,
                }
            pool_ids[pool_name]["block_count_100"] += 1

        if len(pool_ids) == 1:
            logger.info(
                "Only 1 mining pool detected (%s) in recent blocks. "
                "Pool diversity signals unavailable — possible centralization event.",
                list(pool_ids.keys())[0],
            )

        pool_rows = []
        for pool_name, stats in pool_ids.items():
            row = [
                stats["hashrate_pct"],
                float(stats["block_count_10"]),
                float(stats["block_count_100"]),
                1.0 if pool_name != "Unknown" else 0.0,
                stats["avg_fee_earned"],
                stats["orphan_rate"],
                0.0,  # reserved padding
                0.0,  # reserved padding
            ]
            pool_rows.append(row)
        pool_tensor = torch.tensor(pool_rows, dtype=torch.float32)

    # ── FEE BAND NODES (always required) ─────────────────────────────────────
    fee_bands = mempool.get("fee_bands", {})
    if not fee_bands:
        raise GraphConstructionError(
            "Fee band data missing from SentinelState. "
            "Cannot construct graph — fee bands are required anchor nodes."
        )
    fee_rows = _build_fee_band_rows(fee_bands)
    fee_tensor = torch.tensor(fee_rows, dtype=torch.float32)

    # ── NETWORK SINGLETON NODE (always 1) ─────────────────────────────────────
    net_row = _build_network_row(state.get("network", {}))
    net_tensor = torch.tensor([net_row], dtype=torch.float32)  # [1, 8]

    # ── ASSEMBLE GRAPH ────────────────────────────────────────────────────────
    n_tx = tx_tensor.size(0)
    n_fee = fee_tensor.size(0)
    n_pool = pool_tensor.size(0)
    n_net = net_tensor.size(0)

    x = torch.cat([tx_tensor, fee_tensor, pool_tensor, net_tensor], dim=0)
    edge_index = _build_edges(n_tx, n_fee, n_pool, n_net)

    # Validate: graph must have at least 1 node and edge_index must be in bounds
    assert x.size(0) > 0, "Graph has zero nodes — construction logic error"
    if edge_index.size(1) > 0:
        assert edge_index.max() < x.size(0), (
            f"Edge index out of bounds: max={edge_index.max()}, nodes={x.size(0)}"
        )

    return Data(
        x=x,
        edge_index=edge_index,
        num_nodes=x.size(0),
        # Metadata for logging/debugging — not used in forward pass
        meta={
            "n_tx": n_tx,
            "n_fee": n_fee,
            "n_pool": n_pool,
            "data_age_seconds": round(data_age, 1),
        },
    )


def _build_fee_band_rows(fee_bands: dict) -> list[list[float]]:
    """Build 8-feature rows for fee band nodes. Bands: 1-2, 2-5, 5-10, 10-20, 20-50, 50+."""
    band_keys = ["1-2", "2-5", "5-10", "10-20", "20-50", "50+"]
    rows = []
    for band in band_keys:
        b = fee_bands.get(band, {})
        rows.append([
            float(b.get("count", 0)),
            float(b.get("total_vbytes", 0)),
            float(b.get("avg_fee_rate", 0)),
            float(b.get("min_fee_rate", 0)),
            float(b.get("max_fee_rate", 0)),
            float(b.get("pct_of_mempool", 0)),
            0.0, 0.0,  # reserved
        ])
    return rows


def _build_network_row(network: dict) -> list[float]:
    """Build the single network singleton node's 8 features."""
    return [
        float(network.get("hashrate_th_s", 0.0)),
        float(network.get("difficulty", 0.0)),
        float(network.get("block_time_avg_s", 600.0)),
        float(network.get("mempool_size_mb", 0.0)),
        float(network.get("node_count", 0)),
        float(network.get("orphan_rate", 0.0)),
        0.0, 0.0,  # reserved
    ]


def _build_edges(n_tx: int, n_fee: int, n_pool: int, n_net: int) -> torch.Tensor:
    """
    Build edge_index for the heterogeneous graph.
    Offsets: TX=[0, n_tx), FEE=[n_tx, n_tx+n_fee),
             POOL=[n_tx+n_fee, n_tx+n_fee+n_pool), NET=[last]
    """
    edges = []
    fee_offset = n_tx
    pool_offset = n_tx + n_fee
    net_idx = n_tx + n_fee + n_pool  # singleton

    # TX → FEE edges (each TX node connects to its fee band)
    # Simplified: connect each TX to all fee bands (dense; refine with actual band lookup)
    for i in range(n_tx):
        for j in range(n_fee):
            edges.append([i, fee_offset + j])
            edges.append([fee_offset + j, i])

    # POOL → NET edges
    for k in range(n_pool):
        edges.append([pool_offset + k, net_idx])
        edges.append([net_idx, pool_offset + k])

    # FEE → NET edges
    for j in range(n_fee):
        edges.append([fee_offset + j, net_idx])
        edges.append([net_idx, fee_offset + j])

    if not edges:
        # Degenerate graph — self-loop on NET node to prevent empty edge_index
        logger.warning("No inter-node edges constructed. Adding self-loop on NET node.")
        edges.append([net_idx, net_idx])

    return torch.tensor(edges, dtype=torch.long).t().contiguous()
```

### 🔵 SYNTHESIS FINDING — Q3
Neither model addressed what happens when `edge_index` references node indices that fall outside the assembled `x` tensor — a **silent data corruption bug** that produces wrong embeddings without raising an exception. The `assert edge_index.max() < x.size(0)` guard above catches this at construction time rather than allowing a corrupted forward pass.

---

## Q4 VERDICT: TRAINING DATA QUALITY GATE

**Ruling: Synthesis of both models. GPT-4o provided the right checklist categories; Grok-3 provided numeric thresholds. Neither was complete alone.**

### Complete Quality Gate Checklist

All checks must pass before training is permitted. Implement as a preflight function that returns a structured report with PASS/FAIL/WARN per check.

```python
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class QualityGateResult:
    passed: bool
    check_name: str
    value: float
    threshold: float
    severity: str  # "FAIL", "WARN", "PASS"
    message: str


def run_training_data_quality_gate(
    snapshots: list[dict],
) -> tuple[bool, list[QualityGateResult]]:
    """
    Run all training data quality checks. Returns (all_passed, results).
    Training must not proceed if any FAIL result is present.
    """
    results = []

    # ── CHECK 1: Minimum snapshot count ──────────────────────────────────────
    # Rationale: <500 graphs insufficient to learn reconstruction baseline.
    # GNN autoencoders need diversity across fee regimes and pool compositions.
    n = len(snapshots)
    results.append(QualityGateResult(
        passed=n >= 500,
        check_name="minimum_snapshot_count",
        value=float(n),
        threshold=500.0,
        severity="FAIL" if n < 500 else "WARN" if n < 1000 else "PASS",
        message=f"Dataset has {n} snapshots (minimum 500, recommended 1000+)"
    ))

    # ── CHECK 2: Temporal coverage — hours of day ─────────────────────────────
    # Rationale: Bitcoin mempool patterns differ dramatically by UTC hour.
    # Training only on Asian or US market hours will bias the anomaly baseline.
    # Require at least 20 of 24 hours represented.
    timestamps = [s.get("mempool", {}).get("updated_at", 0) for s in snapshots]
    from datetime import datetime, timezone
    hours_seen = set(
        datetime.fromtimestamp(ts, tz=timezone.utc).hour
        for ts in timestamps if ts > 0
    )
    hours_coverage = len(hours_seen)
    results.append(QualityGateResult(
        passed=hours_coverage >= 20,
        check_name="temporal_coverage_hours",
        value=float(hours_coverage),
        threshold=20.0,
        severity="FAIL" if hours_coverage < 16 else "WARN" if hours_coverage < 20 else "PASS",
        message=f"Dataset covers {hours_coverage}/24 hours of day"
    ))

    # ── CHECK 3: Temporal coverage — days of week ─────────────────────────────
    # Rationale: Weekend mempool behavior (lower volume, different fee curves)
    # is systematically different. All 7 days required.
    weekdays_seen = set(
        datetime.fromtimestamp(ts, tz=timezone.utc).weekday()
        for ts in timestamps if ts > 0
    )
    results.append(QualityGateResult(
        passed=len(weekdays_seen) == 7,
        check_name="temporal_coverage_weekdays",
        value=float(len(weekdays_seen)),
        threshold=7.0,
        severity="FAIL" if len(weekdays_seen) < 5 else "WARN" if len(weekdays_seen) < 7 else "PASS",
        message=f"Dataset covers {len(weekdays_seen)}/7 days of week"
    ))

    # ── CHECK 4: Event type distribution (no single regime dominates) ─────────
    # Rationale: If 80% of snapshots are taken during mempool congestion events,
    # the model learns that congestion = normal, failing to flag it as anomalous.
    # Hard cap: no single labeled regime > 30% of dataset.
    regimes = [s.get("regime", "unknown") for s in snapshots]
    from collections import Counter
    regime_counts = Counter(regimes)
    max_regime_pct = max(regime_counts.values()) / n if n > 0 else 1.0
    dominant_regime = regime_counts.most_common(1)[0][0]
    results.append(QualityGateResult(
        passed=max_regime_pct <= 0.30,
        check_name="event_distribution_balance",
        value=max_regime_pct,
        threshold=0.30,
        severity="FAIL" if max_regime_pct > 0.50 else "WARN" if max_regime_pct > 0.30 else "PASS",
        message=f"Dominant regime '{dominant_regime}' = {max_regime_pct:.1%} of data"
    ))

    # ── CHECK 5: Feature variance (avoid static/degenerate features) ──────────
    # Rationale: A feature that never varies provides zero discriminative signal.
    # Any feature with variance < 0.001 is effectively constant — likely a
    # data pipeline bug (field not being populated).
    all_features = []
    for s in snapshots:
        graph = s.get("_graph_features", None)
        if graph is not None:
            all_features.append(graph)

    min_variance = 1.0  # Will be overwritten
    low_variance_features = []
    if all_features:
        feature_matrix = np.array(all_features)  # [N, 8]
        variances = np.var(feature_matrix, axis=0)
        min_variance = float(variances.min())
        low_variance_features = [
            f"feature_{i}" for i, v in enumerate(variances) if v < 0.001
        ]

    results.append(QualityGateResult(
        passed=len(low_variance_features) == 0,
        check_name="feature_variance_floor",
        value=min_variance,
        threshold=0.001,
        severity="FAIL" if len(low_variance_features) > 2 else "WARN" if low_variance_features else "PASS",
        message=(
            f"Low-variance features: {low_variance_features}" if low_variance_features
            else "All features have sufficient variance"
        )
    ))

    # ── CHECK 6: Snapshot freshness (no future timestamps, no ancient data) ───
    now = time.time()
    stale_snapshots = sum(1 for ts in timestamps if now - ts > 30 * 86400)
    future_snapshots = sum(1 for ts in timestamps if ts > now + 3600)
    stale_pct = stale_snapshots / n if n > 0 else 0.0
    results.append(QualityGateResult(
        passed=stale_pct < 0.05 and future_snapshots == 0,
        check_name="snapshot_freshness",
        value=stale_pct,
        threshold=0.05,
        severity="FAIL" if future_snapshots > 0 else "WARN" if stale_pct >= 0.05 else "PASS",
        message=(
            f"{stale_snapshots} snapshots >30 days old ({stale_pct:.1%}), "
            f"{future_snapshots} future timestamps"
        )
    ))

    # ── CHECK 7: Minimum graph size diversity ─────────────────────────────────
    # Rationale: If all training graphs have similar node counts, the model won't
    # generalize to congestion events (large graphs) vs quiet periods (small).
    node_counts = [s.get("_node_count", 0) for s in snapshots]
    if node_counts and max(node_counts) > 0:
        node_count_cv = np.std(node_counts) / (np.mean(node_counts) + 1e-8)
    else:
        node_count_cv = 0.0
    results.append(QualityGateResult(
        passed=node_count_cv >= 0.20,
        check_name="graph_size_diversity",
        value=node_count_cv,
        threshold=0.20,
        severity="WARN" if node_count_cv < 0.20 else "PASS",
        message=f"Graph size coefficient of variation: {node_count_cv:.3f}"
    ))

    all_passed = all(r.severity != "FAIL" for r in results)
    return all_passed, results
```

---

## Q5 VERDICT: ANOMALY SCORE CALIBRATION

**Ruling: Synthesis. GPT-4o correctly identified stratified temporal sampling; Grok-3 correctly identified rolling windows. Both are needed. Neither addressed the cold-start calibration problem.**

### The Core Flaw: Static Thresholds on a Non-Stationary Signal

Bitcoin mempool reconstruction error is non-stationary. A threshold calibrated during a quiet period will fire constantly during a congestion regime, and vice versa. Any calibration that produces a single static p95/p99 value from a single pass over a validation set will degrade within days.

### Definitive Calibration Methodology

```python
import numpy as np
from collections import deque
from datetime import datetime, timezone


class AnomalyScoreCalibrator:
    """
    Two-layer anomaly score calibration:
    Layer 1 — Offline: Stratified temporal calibration on validation set.
    Layer 2 — Online: Rolling window adaptation to recent baseline.

    Why both? Offline calibration anchors the baseline to diverse conditions.
    Online rolling windows prevent drift as network conditions evolve.
    """

    def __init__(
        self,
        offline_window_days: int = 30,
        online_window_hours: int = 24,
        online_update_interval_min: int = 60,
        cold_start_default_p95: float = 0.15,
        cold_start_default_p99: float = 0.35,
    ):
        self.cold_start_p95 = cold_start_default_p95
        self.cold_start_p99 = cold_start_default_p99
        self._offline_thresholds: dict[str, float] = {}
        self._online_buffer: deque = deque(maxlen=online_window_hours * 60)
        self._online_p95: float = cold_start_default_p95
        self._online_p99: float = cold_start_default_p99
        self._calibrated: bool = False

    def calibrate_offline(self, validation_mse_records: list[dict]) -> dict:
        """
        Stratified temporal calibration on validation data.

        Args:
            validation_mse_records: List of {
                "mse": float,
                "timestamp": int,      # unix timestamp
                "hour_utc": int,       # 0-23
                "weekday": int,        # 0=Mon, 6=Sun
                "regime": str,         # "normal", "congestion", "quiet"
            }

        The validation set MUST pass the Q4 quality gate first.
        If it doesn't represent all hours/days, calibration thresholds
        will be biased toward over- or under-represented periods.
        """
        if not validation_mse_records:
            raise ValueError("Cannot calibrate on empty validation set")

        mse_values = np.array([r["mse"] for r in validation_mse_records])

        # Stratify by time-of-day (4 quartiles: night/morning/afternoon/evening)
        strata = {
            "night":     [r["mse"] for r in validation_mse_records if 0  <= r["hour_utc"] < 6],
            "morning":   [r["mse"] for r in validation_mse_records if 6  <= r["hour_utc"] < 12],
            "afternoon": [r["mse"] for r in validation_mse_records if 12 <= r["hour_utc"] < 18],
            "evening":   [r["mse"] for r in validation_mse_records if 18 <= r["hour_utc"] < 24],
        }

        # Warn if any stratum has <50 samples (threshold will be unreliable)
        for stratum, values in strata.items():
            if len(values) < 50:
                import logging
                logging.getLogger(__name__).warning(
                    "Stratum '%s' has only %d validation samples. "
                    "Calibration threshold for this period may be unreliable.",
                    stratum, len(values),
                )

        # Global thresholds from stratified percentiles
        # Use the HIGHER of: global percentile vs max stratum-specific percentile
        # This prevents a quiet stratum from setting a threshold that fires
        # constantly during active periods.
        global_p95 = float(np.percentile(mse_values, 95))
        global_p99 = float(np.percentile(mse_values, 99))

        stratum_p95 = max(
            (float(np.percentile(v, 95)) for v in strata.values() if len(v) >= 10),
            default=global_p95,
        )
        stratum_p99 = max(
            (float(np.percentile(v, 99)) for v in strata.values() if len(v) >= 10),
            default=global_p99,
        )

        self._offline_thresholds = {
            "p95": max(global_p95, stratum_p95 * 0.8),  # Blend global + stratum
            "p99": max(global_p99, stratum_p99 * 0.8),
            "n_samples": len(mse_values),
            "calibration_date": datetime.now(timezone.utc).isoformat(),
        }

        # Initialize online buffer with offline baseline
        self._online_p95 = self._offline_thresholds["p95"]
        self._online_p99 = self._offline_thresholds["p99"]
        self._calibrated = True

        return self._offline_thresholds

    def update_online(self, mse: float) -> None:
        """
        Update rolling window with new inference MSE.
        Called on every inference cycle (every ~1 minute).
        Thresholds adapt without drifting away from offline anchor.
        """
        self._online_buffer.append(mse)

        if len(self._online_buffer) >= 60:  # Minimum 1 hour of data
            recent = np.array(self._online_buffer)
            rolling_p95 = float(np.percentile(recent, 95))
            rolling_p99 = float(np.percentile(recent, 99))

            # Anchor constraint: online threshold cannot deviate >3x from offline
            # This prevents the model from "calibrating away" legitimate anomalies
            # during prolonged anomaly events (the self-suppression problem).
            anchor_p95 = self._offline_thresholds.get("p95", self.cold_start_p95)
            anchor_p99 = self._offline_thresholds.get("p99", self.cold_start_p99)

            self._online_p95 = min(rolling_p95, anchor_p95 * 3.0)
            self._online_p99 = min(rolling_p99, anchor_p99 * 3.0)

    @property
    def current_thresholds(self) -> dict:
        """Live thresholds to pass to anomaly_score()."""
        if not self._calibrated:
            # Cold-start: use conservative defaults until calibrated
            return {
                "p95": self.cold_start_p95,
                "p99": self.cold_start_p99,
                "source": "cold_start_default",
            }
        return {
            "p95": self._online_p95,
            "p99": self._online_p99,
            "source": "calibrated",
        }
```

### 🔵 SYNTHESIS FINDING — Q5: The Self-Suppression Problem

Neither model identified the **calibration self-suppression problem**: if an anomaly event persists for hours (e.g., a major fee spike lasting 6 hours), the rolling online window will incorporate those anomalous MSE values as "normal," causing the threshold to rise and suppress future alerts for the same event. The `anchor_p99 * 3.0` ceiling in the code above prevents this by refusing to let online adaptation raise the threshold more than 3× above the offline-calibrated baseline.

---

## Q6 VERDICT: ASYNC INTEGRATION PATTERN

**Ruling: Grok-3 wins on implementation detail. Both models chose the correct pattern (run_in_executor). Grok-3's ThreadPoolExecutor configuration prevents a critical production failure mode.**

### Why Grok-3 Wins

GPT-4o's implementation uses `asyncio.get_event_loop()` directly, which is deprecated in Python 3.10+ and raises a `DeprecationWarning` (becoming an error in future versions). It also uses no thread pool cap, meaning under burst load, the executor creates unlimited threads, causing thread starvation.

Grok-3's use of a bounded `ThreadPoolExecutor` is correct. However, it also requires two fixes: the `asyncio.get_event_loop()` call should be replaced with `asyncio.get_running_loop()`, and exception handling should be more specific.

### Definitive Async Wrapper

```python
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

logger = logging.getLogger(__name__)

# PCAF v1 inference target: <50ms. Hard timeout at 200ms to prevent
# thread pool exhaustion under load. If inference exceeds this, the
# model is either on CPU or the graph is pathologically large.
INFERENCE_TIMEOUT_SECONDS = 0.200
THREAD_POOL_MAX_WORKERS = 4  # Match to CPU core count, not GPU count


class PCAFAsyncEngine:
    """
    Async wrapper for PCAF v1 GNN inference.

    Design: PCAF v1 uses PyTorch + CUDA. PyTorch's CUDA operations
    release the GIL during GPU execution, making thread-based async
    viable (unlike pure-Python CPU operations). run_in_executor
    offloads the blocking call to a thread while the event loop
    continues processing other Sentinel events.

    Why not ProcessPoolExecutor? Model state (autoencoder weights,
    calibrator) cannot be efficiently shared across processes without
    pickling overhead that would dominate the <50ms budget.
    """

    def __init__(
        self,
        pcaf_v1_engine,  # The synchronous ChainStateAutoencoder + calibrator
        max_workers: int = THREAD_POOL_MAX_WORKERS,
        timeout_s: float = INFERENCE_TIMEOUT_SECONDS,
    ):
        self._engine = pcaf_v1_engine
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="pcaf_inference",
        )
        self._timeout = timeout_s
        self._inference_count = 0
        self._timeout_count = 0

    async def async_score(self, state_dict: dict) -> Optional[dict]:
        """
        Non-blocking PCAF v1 inference call.

        Returns anomaly score dict or None on timeout/failure.
        Never raises — Sentinel must continue operating even if PCAF fails.
        Sentinel should treat None as "score unavailable" and not emit
        a network security signal for that cycle.
        """
        loop = asyncio.get_running_loop()  # Not get_event_loop() — deprecated in 3.10+
        self._inference_count += 1

        try:
            t0 = time.monotonic()
            result = await asyncio.wait_for(
                loop.run_in_executor(self._executor, self._score_sync, state_dict),
                timeout=self._timeout,
            )
            elapsed_ms = (time.monotonic() - t0) * 1000
            if elapsed_ms > 100:  # Warn if approaching timeout
                logger.warning(
                    "PCAF inference slow: %.1fms (target <50ms, timeout %dms)",
                    elapsed_ms, self._timeout * 1000,
                )
            return result

        except asyncio.TimeoutError:
            self._timeout_count += 1
            logger.error(
                "PCAF inference timeout after %.0fms. "
                "Timeout rate: %d/%d (%.1f%%). "
                "Check GPU availability and graph size.",
                self._timeout * 1000,
                self._timeout_count,
                self._inference_count,
                100 * self._timeout_count / self._inference_count,
            )
            return None

        except Exception as e:
            logger.exception("PCAF inference failed unexpectedly: %s", e)
            return None

    def _score_sync(self, state_dict: dict) -> dict:
        """
        Synchronous inference — runs in thread pool.
        This is the only method that touches the GPU.
        """
        return self._engine.score(state_dict)

    async def shutdown(self) -> None:
        """Graceful shutdown — wait for in-flight inferences to complete."""
        self._executor.shutdown(wait=True)
        logger.info(
            "PCAF async engine shutdown. Total inferences: %d, Timeouts: %d",
            self._inference_count, self._timeout_count,
        )
```

### 🔵 SYNTHESIS FINDING — Q6
Neither model addressed the **GPU context threading issue**: PyTorch's CUDA context is not thread-safe by default. If multiple inference requests arrive simultaneously and `max_workers > 1`, two threads may attempt concurrent CUDA operations, causing non-deterministic results or crashes. The fix is to ensure the `ThreadPoolExecutor` uses `max_workers=1` for GPU inference (serializing requests) or to use `torch.cuda.stream()` context managers to isolate operations per thread. For the single-model PCAF v1 use case, `max_workers=1` is the safe default; increase only with explicit stream isolation.

---

## Q7 VERDICT: TPA SIGNAL COMPLETENESS

**Ruling: Both models identified the same gaps. Grok-3 provided better prioritization. Synthesis produces the definitive signal availability matrix.**

### Per-Scenario Signal Availability Matrix

| Scenario | Signal | Source | Status | Build Estimate |
|---|---|---|---|---|
| **Institutional Adoption** | ETF daily inflows (BTC spot) | Bloomberg/custom scraper | ✅ Present | — |
| | CME futures open interest delta | CME public API | ✅ Present | — |
| | Stablecoin minting events | On-chain (Etherscan) | ✅ Present | — |
| | Corporate treasury announcements | SEC 8-K RSS + NLP | ❌ Missing | 3–5 days |
| | BTC options skew (Deribit) | Deribit API | ❌ Missing | 1 day |
| **Regulatory Crackdown** | Regulatory threat level index | Internal scoring | ✅ Present | — |
| | P2P volume proxy | LocalBitcoins/HodlHodl API | ✅ Present | — |
| | BIS/ECB coordination language | BIS/ECB RSS + keyword NLP | ❌ Missing | 3–5 days |
| | FATF plenary outcomes | Manual + FATF RSS | ❌ Missing | 2 days |
| **Network Security** | PCAF anomaly score | PCAF v1 (this build) | ⚠️ In Progress | Current sprint |
| | Orphan block rate | mempool.space API | ✅ Present | — |
| | Emergency patch PRs (Bitcoin Core) | GitHub API (PR labels) | ❌ Missing | **1–2 hours** |
| | Hash rate geographic concentration | Mining pool API | ✅ Present | — |
| **Macro Liquidity** | DXY (US Dollar Index) | FRED API / Yahoo Finance | ✅ Present | — |
| | Gold spot price | Metals API | ✅ Present | — |
| | VIX | CBOE / Yahoo Finance | ✅ Present | — |
| | US10Y yield | FRED API | ❌ Missing | 2 hours |
| **CBDC Displacement** | Sovereign CBDC launch alerts | BIS CBDC tracker RSS | ✅ Present | — |
| | P2P volume (repeat) | See above | ✅ Present | — |
| | Retail payment volume shift | ECB/Fed data (quarterly) | ❌ Missing | Low priority |

### Priority-Ordered Missing Signal Remediation

**P0 — Fix in hours (critical data gaps):**
1. **GitHub API — Emergency Patch PR Detection** (1–2h): Monitor `bitcoin/bitcoin` for PRs labeled `security` or `critical`. This is the only source for 0-day network security signals. Absence means Network Security scenario has a blind spot to the most severe threat class.
2. **US10Y Yield** (2h): Already available from FRED API; simply not integrated. Required for Macro Liquidity to distinguish risk-off moves from BTC-specific selling.

**P1 — Fix within sprint:**
3. Corporate treasury announcements (SEC EDGAR RSS + keyword match)
4. FATF outcome detection (FATF RSS feed + regime change classifier)

**P2 — Backlog:**
5. BIS/ECB coordination language (NLP pipeline required)
6. Deribit options skew (separate API contract needed)

---

## Q8 VERDICT: MONTE CARLO CORRECTNESS

**Ruling: Both models agreed on the core fix (clip negative jitter to 0). The definitive implementation adds distribution validation and seed control that neither model included.**

```python
import numpy as np
from typing import Optional


class MonteCarloSignalSimulator:
    """
    Monte Carlo simulation for TPA scenario probability estimation.

    Design choices:
    - Jitter is multiplicative (not additive) to preserve signal scale-invariance.
    - Negative jitter clipped to 0: signal strength is a non-negative probability-
      like value [0, 1]. Negative values are non-physical and indicate sampling
      noise that should not propagate to scenario probability calculation.
    - Seed control: required for reproducible audit trails of generated outputs.
    """

    def __init__(self, n_simulations: int = 1000, seed: Optional[int] = None):
        self.n_simulations = n_simulations
        self.rng = np.random.default_rng(seed)  # Not np.random.seed() — deprecated global state

    def jitter_strength(
        self,
        strength: float,
        jitter_std: float = 0.2,
    ) -> float:
        """
        Apply multiplicative Gaussian jitter to a signal strength value.

        Args:
            strength: Base signal strength [0.0, 1.0]
            jitter_std: Standard deviation of multiplicative noise (default 0.2 = 20%)

        Returns:
            Jittered strength, clipped to [0.0, 1.0].

        Edge cases handled:
        - Negative jitter result → clipped to 0.0 (not physically meaningful)
        - Jitter > 1.0 → clipped to 1.0 (strength is a probability-like value)
        - strength = 0.0 → returns 0.0 regardless of jitter (zero signal stays zero)
        - strength < 0.0 → raises ValueError (caller data contract violation)
        - jitter_std < 0.0 → raises ValueError (std cannot be negative)
        """
        if strength < 0.0:
            raise ValueError(f"Signal strength must be >= 0, got {strength}")
        if jitter_std < 0.0:
            raise ValueError(f"Jitter std must be >= 0, got {jitter_std}")
        if strength == 0.0:
            return 0.0

        multiplier = self.rng.normal(loc=1.0, scale=jitter_std)
        jittered = strength * multiplier
        return float(np.clip(jittered, 0.0, 1.0))  # Enforce [0, 1] range

    def run_scenario_simulation(
        self,
        signals: dict[str, float],
        signal_weights: dict[str, float],
        scenario_threshold: float = 0.6,
    ) -> dict:
        """
        Run N Monte Carlo simulations of scenario probability given signal strengths.

        Args:
            signals: {signal_name: strength_value} — current observed strengths
            signal_weights: {signal_name: weight} — importance of each signal
            scenario_threshold: Weighted sum threshold above which scenario fires

        Returns:
            {
                "probability": float,       # P(scenario fires) across simulations
                "mean_score": float,        # Mean weighted score
                "p5_score": float,
                "p95_score": float,
                "n_simulations": int,
            }
        """
        if not signals:
            raise ValueError("signals dict cannot be empty")

        # Validate weights sum approximately to 1.0
        total_weight = sum(signal_weights.get(k, 1.0) for k in signals)
        if not (0.5 <= total_weight <= 1.5):
            import logging
            logging.getLogger(__name__).warning(
                "Signal weights sum to %.3f (expected ~1.0). "
                "Scenario probabilities may be mis-scaled.", total_weight
            )

        scores = []
        for _ in range(self.n_simulations):
            weighted_score = 0.0
            for signal_name, strength in signals.items():
                weight = signal_weights.get(signal_name, 1.0 / len(signals))
                jittered = self.jitter_strength(strength)
                weighted_score += weight * jittered
            scores.append(weighted_score)

        scores_arr = np.array(scores)
        fires = scores_arr >= scenario_threshold

        return {
            "probability": float(fires.mean()),
            "mean_score": float(scores_arr.mean()),
            "p5_score": float(np.percentile(scores_arr, 5)),
            "p95_score": float(np.percentile(scores_arr, 95)),
            "n_simulations": self.n_simulations,
            "threshold": scenario_threshold,
            "confidence_interval_width": float(
                np.percentile(scores_arr, 95) - np.percentile(scores_arr, 5)
            ),
        }
```

### 🔵 SYNTHESIS FINDING — Q8
Neither model flagged **jitter parameter sensitivity**. With `jitter_std=0.2` (20% noise) and only `n_simulations=1000`, the 95% confidence interval on a 50% probability estimate is approximately ±3.1% (by binomial statistics). For the TPA's scenario alert thresholds (typically ~0.6), this means the system can flip between "alert" and "no alert" purely due to sampling noise. Increasing to `n_simulations=5000` reduces this to ±1.4%, which is more appropriate for a financial alerting system. This is a **recommended change** (see IMPROVEMENTS).

---

## Q9 VERDICT: TPA SHARE URL SECURITY

**Ruling: GPT-4o's structure was correct. Neither model provided a complete implementation. The definitive mechanism is below.**

### Definitive Snapshot Persistence Mechanism

The core requirements: immutability (snapshot reflects state at time of creation), expiration (stale data must not persist), unforgeable URLs (no enumeration attacks), and no PII exposure in the URL itself.

```python
import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Optional


# Load from environment — never hardcode
SNAPSHOT_SECRET_KEY = os.environ["PCAF_SNAPSHOT_SECRET_KEY"]
SNAPSHOT_TTL_SECONDS = 86400  # 24 hours
SNAPSHOT_MAX_SIZE_BYTES = 64 * 1024  # 64KB max payload per snapshot


@dataclass
class TPASnapshot:
    snapshot_id: str         # UUID4 — the URL token
    created_at: float        # Unix timestamp
    expires_at: float        # created_at + TTL
    payload_hash: str        # HMAC-SHA256 of payload — tamper detection
    payload: dict            # The actual TPA state to render


class TPASnapshotStore:
    """
    Snapshot persistence for shareable TPA URLs.

    Security model:
    - URL contains UUID4 only — not guessable (122 bits of entropy)
    - Payload is HMAC-signed — server verifies on every read
    - 24-hour TTL — expired snapshots are rejected at read time
    - No user data in URL — snapshot ID does not encode session info
    - Enumeration resistant — sequential IDs are not used

    Storage: Replace _store dict with Redis for production.
    Redis key: "tpa_snapshot:{snapshot_id}", TTL: SNAPSHOT_TTL_SECONDS
    """

    def __init__(self):
        self._store: dict[str, TPASnapshot] = {}  # Replace with Redis in production

    def create_snapshot(self, tpa_state: dict) -> str:
        """
        Persist a TPA state snapshot. Returns the share URL token (UUID).

        Raises:
            ValueError: If payload exceeds size limit
        """
        payload_bytes = json.dumps(tpa_state, sort_keys=True).encode("utf-8")
        if len(payload_bytes) > SNAPSHOT_MAX_SIZE_BYTES:
            raise ValueError(
                f"Snapshot payload {len(payload_bytes)} bytes exceeds "
                f"limit of {SNAPSHOT_MAX_SIZE_BYTES} bytes"
            )

        snapshot_id = str(uuid.uuid4())  # Cryptographically random, not sequential
        created_at = time.time()
        expires_at = created_at + SNAPSHOT_TTL_SECONDS

        # HMAC ensures payload cannot be modified after creation
        payload_hash = hmac.new(
            SNAPSHOT_SECRET_KEY.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        snapshot = TPASnapshot(
            snapshot_id=snapshot_id,
            created_at=created_at,
            expires_at=expires_at,
            payload_hash=payload_hash,
            payload=tpa_state,
        )

        self._store[snapshot_id] = snapshot
        return snapshot_id

    def retrieve_snapshot(self, snapshot_id: str) -> Optional[dict]:
        """
        Retrieve and validate a snapshot by ID.

        Returns None if: expired, not found, or tampered.
        Never reveals which failure mode occurred (timing-safe).
        """
        snapshot = self._store.get(snapshot_id)

        if snapshot is None:
            return None  # Not found — same response as expired (no oracle)

        # Expiry check
        if time.time() > snapshot.expires_at:
            del self._store[snapshot_id]
            return None

        # Tamper detection — re-compute HMAC and compare
        payload_bytes = json.dumps(snapshot.payload, sort_keys=True).encode("utf-8")
        expected_hash = hmac.new(
            SNAPSHOT_SECRET_KEY.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, snapshot.payload_hash):
            # Log as security event — payload was modified after creation
            import logging
            logging.getLogger(__name__).error(
                "SECURITY: Snapshot %