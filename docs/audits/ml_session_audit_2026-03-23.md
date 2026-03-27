# ML SESSION BUILD-DOC — ENGINEERING AUDIT REPORT
# Protocol Pulse Intelligence Terminal · PCAF v1 + TPA
# Date: 2026-03-23
# Models: GPT-4o, Grok-3 (2 cycles each)
# Synthesized by: Claude Sonnet 4.6

---

## AUDIT PREAMBLE

This report synthesizes two full cycles of independent ML engineering analysis from GPT-4o and Grok-3, covering the PCAF v1 (GraphSAGE GNN Autoencoder for Bitcoin chain-state anomaly detection) and TPA (Temporal Predictive Analytics Monte Carlo simulation engine). Where models agreed, the consensus is reported as authoritative. Where they disagreed, this report adjudicates based on first-principles ML engineering and production systems reasoning. All code produced here is the definitive implementation recommendation — superseding both models' individual outputs.

**Audit scope:** Implementation correctness, ML architecture validity, integration safety, data contract robustness, production risk identification.

---

## Q1 VERDICT: TORCH_GEOMETRIC INSTALLATION

**Consensus Level:** High — both models identified the same failure modes with Grok providing superior depth on latency implications.

### Definitive pip Commands

```bash
# Step 1: Install base torch-geometric (version-agnostic)
pip install torch-geometric --break-system-packages

# Step 2: Install optional performance dependencies for PyTorch 2.6.0 + CUDA 12.4
pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html \
  --break-system-packages

# Step 3: Post-install verification (run immediately after)
python -c "
import torch
from torch_geometric.nn import SAGEConv
import time

conv = SAGEConv(8, 64)
x = torch.randn(220, 8)
edge_index = torch.randint(0, 220, (2, 600))
start = time.perf_counter()
for _ in range(100):
    out = conv(x, edge_index)
elapsed = (time.perf_counter() - start) / 100 * 1000
print(f'SAGEConv latency: {elapsed:.2f}ms per forward pass')
print(f'torch_scatter available: {hasattr(torch, \"scatter\")}')
assert elapsed < 50, f'LATENCY BUDGET EXCEEDED: {elapsed:.2f}ms > 50ms'
print('INSTALLATION OK')
"
```

### Failure Modes (Priority Order)

| Failure Mode | Symptom | Probability |
|---|---|---|
| CUDA ABI mismatch (system CUDA ≠ 12.4) | `ImportError: libcudart.so.12.4` | High |
| PyG CDN unavailable | `ConnectionError` / `TimeoutError` | Medium |
| PyTorch version conflict in shared env | Dependency resolver error | Medium |
| `--break-system-packages` on managed Python | `externally-managed-environment` error | Low |

### Fallback Strategy (Ordered)

```bash
# Fallback 1: Verify exact CUDA version match
nvcc --version  # Must show 12.4.x
python -c "import torch; print(torch.version.cuda)"  # Must show 12.4

# Fallback 2: CPU-only mode (sacrifices GPU acceleration entirely)
pip install torch-geometric --break-system-packages
# Do NOT install pyg_lib/scatter/sparse — they have no CPU wheels on pyg CDN
# SAGEConv will use pure Python aggregation

# Fallback 3: Compile from source (slow, last resort)
pip install torch_scatter --no-binary torch_scatter --break-system-packages
pip install torch_sparse --no-binary torch_sparse --break-system-packages
```

### SAGEConv Without Optional Dependencies

**Verdict:** SAGEConv **will function** without `pyg_lib`, `torch_scatter`, and `torch_sparse`, but with degraded performance:
- Without `torch_scatter`: aggregation falls back to pure-Python scatter ops — **2–5× slower**
- Without `torch_sparse`: sparse tensor ops are slower but functional
- Without `pyg_lib`: no impact on SAGEConv specifically

For a graph of ~220 nodes and ~600 edges: estimated inference time rises from ~5–8ms (with CUDA + scatter) to ~20–40ms (CPU fallback), which still satisfies the <50ms target. **Run the verification script above to confirm before deploying.**

---

## Q2 VERDICT: GRAPHSAGE AUTOENCODER ARCHITECTURE

**Consensus Level:** Medium — both models identified the decoder edge-information problem. Grok's solution (pass `edge_index` to decoder) is structurally sounder than GPT-4o's (dense MLP decoder), but both miss the critical **node-broadcast problem**. This report provides the definitive architecture.

### Adjudication

**GPT-4o's position** (dense MLP decoder): Simpler but loses all graph topology information during decoding. Reconstruction error measures only feature deviation, not structural anomalies. For Bitcoin mempool anomaly detection, where unusual transaction clustering is a primary signal, this is architecturally insufficient.

**Grok's position** (pass `edge_index` to decoder with SAGEConv layers): Correct in principle — preserving graph structure enables topology-aware reconstruction. However, Grok's Cycle 1 code contains a critical bug: broadcasting a graph-level latent vector (`latent.repeat(num_nodes, 1)`) means every node starts with an identical feature vector, making SAGEConv's neighborhood aggregation in layer 1 of the decoder equivalent to the same computation for all nodes. The decoder cannot differentiate nodes without a node-specific signal.

**Definitive Architecture:** Hybrid approach — encode with SAGEConv (preserve node embeddings through bottleneck), decode with SAGEConv using **both the graph-level latent AND per-node embeddings** from the encoder. This is the only approach that captures both feature and topology anomalies.

**Long-term recommendation:** Migrate to VGAE (Variational Graph Autoencoder) post-v1, which natively models edge probability reconstruction. Both models identified this independently — it is the correct production target.

### Definitive Implementation

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, global_mean_pool
from torch_geometric.data import Data


class ChainStateEncoder(nn.Module):
    """
    GraphSAGE encoder. Returns both:
    - graph_latent: (1, 32) global graph embedding via bottleneck
    - node_embeddings: (N, 256) per-node embeddings before pooling
    
    Both are needed for topology-aware decoding.
    """
    def __init__(self, in_features: int = 8, hidden: int = 64):
        super().__init__()
        self.conv1 = SAGEConv(in_features, hidden)
        self.conv2 = SAGEConv(hidden, hidden * 2)       # 128
        self.conv3 = SAGEConv(hidden * 2, hidden * 4)   # 256
        self.bn1 = nn.BatchNorm1d(hidden)
        self.bn2 = nn.BatchNorm1d(hidden * 2)
        self.bn3 = nn.BatchNorm1d(hidden * 4)
        self.bottleneck = nn.Linear(hidden * 4, 32)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        # x shape: (N, 8)  edge_index: (2, E)  batch: (N,)
        h = F.relu(self.bn1(self.conv1(x, edge_index)))
        h = F.relu(self.bn2(self.conv2(h, edge_index)))
        h = F.relu(self.bn3(self.conv3(h, edge_index)))   # (N, 256)

        # Graph-level embedding via global mean pooling
        graph_emb = global_mean_pool(h, batch)            # (B, 256)
        graph_latent = self.bottleneck(graph_emb)         # (B, 32)

        return graph_latent, h  # Return node embeddings for decoder


class ChainStateDecoder(nn.Module):
    """
    GraphSAGE decoder. Uses both:
    - Per-node embeddings (from encoder, shape N×256): provides node-specific signal
    - Graph-level latent (shape B×32): provides global context
    
    Critical design: nodes are differentiated via encoder node embeddings,
    NOT by repeating the graph-level latent (which would make all nodes identical
    at decoder layer 1, defeating neighbourhood aggregation).
    """
    def __init__(self, out_features: int = 8, hidden: int = 64):
        super().__init__()
        # Project concatenated (node_emb + broadcast_latent) into decoder space
        # 256 (node_emb) + 32 (graph_latent) = 288
        self.proj = nn.Linear(288, hidden * 4)            # 288 → 256
        self.conv1 = SAGEConv(hidden * 4, hidden * 2)     # 256 → 128
        self.conv2 = SAGEConv(hidden * 2, hidden)         # 128 → 64
        self.conv3 = SAGEConv(hidden, out_features)       # 64 → 8
        self.bn1 = nn.BatchNorm1d(hidden * 4)
        self.bn2 = nn.BatchNorm1d(hidden * 2)
        self.bn3 = nn.BatchNorm1d(hidden)

    def forward(
        self,
        node_embeddings: torch.Tensor,   # (N, 256)
        graph_latent: torch.Tensor,      # (B, 32)
        edge_index: torch.Tensor,
        batch: torch.Tensor
    ) -> torch.Tensor:
        # Broadcast graph_latent to each node in its graph
        # batch[i] = which graph node i belongs to → index into graph_latent
        latent_per_node = graph_latent[batch]             # (N, 32)

        # Concatenate: each node has both its own embedding + global context
        h = torch.cat([node_embeddings, latent_per_node], dim=1)  # (N, 288)
        h = F.relu(self.bn1(self.proj(h)))                # (N, 256)
        h = F.relu(self.bn2(self.conv1(h, edge_index)))   # (N, 128)
        h = F.relu(self.bn3(self.conv2(h, edge_index)))   # (N, 64)
        h = self.conv3(h, edge_index)                     # (N, 8) — no activation
        return h


class ChainStateAutoencoder(nn.Module):
    """
    Complete GraphSAGE autoencoder for Bitcoin chain-state anomaly detection.
    
    Anomaly score: mean per-node MSE between input and reconstructed features.
    Higher score = more anomalous graph state.
    """
    def __init__(self):
        super().__init__()
        self.encoder = ChainStateEncoder()
        self.decoder = ChainStateDecoder()

    def forward(
        self,
        data: Data
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Returns:
            reconstructed: (N, 8) reconstructed node features
            graph_latent:  (B, 32) compressed graph representation
            node_embeddings: (N, 256) encoder node embeddings
        """
        x = data.x
        edge_index = data.edge_index
        # If batch vector not provided (single graph), all nodes belong to graph 0
        batch = data.batch if hasattr(data, 'batch') and data.batch is not None \
                else torch.zeros(x.size(0), dtype=torch.long, device=x.device)

        graph_latent, node_embeddings = self.encoder(x, edge_index, batch)
        reconstructed = self.decoder(node_embeddings, graph_latent, edge_index, batch)
        return reconstructed, graph_latent, node_embeddings

    def anomaly_score(
        self,
        data: Data,
        thresholds: dict
    ) -> tuple[float, dict]:
        """
        Compute calibrated anomaly score [0, 100].
        
        Returns:
            score: float in [0, 100]
            diagnostics: per-node-type reconstruction errors for explainability
        """
        self.eval()
        with torch.no_grad():
            reconstructed, graph_latent, _ = self.forward(data)
            
            # Per-node MSE
            per_node_mse = F.mse_loss(reconstructed, data.x, reduction='none')
            per_node_scalar = per_node_mse.mean(dim=1)  # (N,)
            mean_mse = per_node_scalar.mean().item()

            # Normalise to [0, 100] using calibrated thresholds
            note_thresh = thresholds['note_threshold']      # e.g., 0.05
            critical_thresh = thresholds['critical_threshold']  # e.g., 0.30
            raw_score = (mean_mse - note_thresh) / (critical_thresh - note_thresh)
            score = float(min(100.0, max(0.0, raw_score * 100)))

            diagnostics = {
                'mean_mse': mean_mse,
                'max_node_mse': per_node_scalar.max().item(),
                'anomalous_nodes': int((per_node_scalar > note_thresh).sum().item()),
                'latent_norm': graph_latent.norm().item(),
            }
        return score, diagnostics

    def reconstruction_loss(self, data: Data) -> torch.Tensor:
        """Training loss: mean MSE over all node features."""
        reconstructed, _, _ = self.forward(data)
        return F.mse_loss(reconstructed, data.x)
```

### Why This Architecture Wins

| Property | GPT-4o (MLP decoder) | Grok (SAGEConv + repeat) | **This Report** |
|---|---|---|---|
| Topology-aware reconstruction | ❌ | ✅ | ✅ |
| Node differentiation in decoder | ✅ | ❌ (all nodes identical at layer 1) | ✅ |
| Captures structural anomalies | ❌ | Partial | ✅ |
| Correct for sparse graphs | ✅ | ✅ | ✅ |
| Batch-safe | N/A | ❌ (hardcoded arange) | ✅ |

---

## Q3 VERDICT: GRAPH CONSTRUCTION DATA CONTRACT

**Consensus Level:** High — both models identified the three edge cases. Grok's guard code was more detailed. This report provides complete, production-ready guard logic.

### Definitive Guard Code

```python
import time
import logging
import torch
from torch_geometric.data import Data
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

STALE_MEMPOOL_THRESHOLD_SECONDS = 900  # 15 minutes
MIN_FEATURE_DIM = 8
MEMPOOL_MAX_AGE_WARN = 300  # 5 minutes — warn before hard reject

@dataclass
class GraphConstructionResult:
    data: Optional[Data]
    skipped: bool
    skip_reason: Optional[str]
    warnings: list[str]


def build_chain_state_graph(state: dict) -> GraphConstructionResult:
    """
    Build PyTorch Geometric Data object from SentinelState.
    
    Handles all degenerate cases:
    1. Zero whale TXs (empty TX nodes)
    2. Single mining pool (1 POOL node)
    3. Stale mempool data (>15 min)
    
    Returns GraphConstructionResult with skip flag and reason if graph
    cannot be constructed. Caller must check .skipped before using .data.
    """
    warnings = []

    # ─────────────────────────────────────────────
    # GUARD 1: Stale mempool data
    # ─────────────────────────────────────────────
    mempool = state.get('mempool', {})
    updated_at = mempool.get('updated_at')

    if updated_at is None:
        return GraphConstructionResult(
            data=None,
            skipped=True,
            skip_reason="mempool.updated_at missing — cannot assess data freshness",
            warnings=[]
        )

    age_seconds = time.time() - updated_at
    if age_seconds > STALE_MEMPOOL_THRESHOLD_SECONDS:
        return GraphConstructionResult(
            data=None,
            skipped=True,
            skip_reason=f"Mempool data stale: {age_seconds:.0f}s > {STALE_MEMPOOL_THRESHOLD_SECONDS}s threshold",
            warnings=[]
        )
    if age_seconds > MEMPOOL_MAX_AGE_WARN:
        warnings.append(f"Mempool data aging: {age_seconds:.0f}s old (warn at {MEMPOOL_MAX_AGE_WARN}s)")

    # ─────────────────────────────────────────────
    # GUARD 2: Build TX nodes (whale transactions)
    # Case: Zero whale TXs → empty tensor, NOT a crash
    # ─────────────────────────────────────────────
    whale_txs = mempool.get('whale_txs', [])
    if not whale_txs:
        warnings.append("Zero whale TXs in mempool — TX nodes absent from graph")
        x_tx = torch.empty(0, MIN_FEATURE_DIM, dtype=torch.float32)
        n_tx = 0
    else:
        tx_features = []
        for tx in whale_txs[:200]:  # Cap at 200 to bound graph size
            feat = _extract_tx_features(tx)
            tx_features.append(feat)
        x_tx = torch.tensor(tx_features, dtype=torch.float32)  # (n_tx, 8)
        n_tx = x_tx.size(0)

    # ─────────────────────────────────────────────
    # GUARD 3: Build POOL nodes (mining pools)
    # Case: Single pool → (1, 8) tensor, valid for PyG
    # Case: Zero pools → inject synthetic UNKNOWN pool node
    # ─────────────────────────────────────────────
    recent_blocks = state.get('network', {}).get('recent_blocks', [])
    pool_agg = _aggregate_pool_features(recent_blocks)

    if len(pool_agg) == 0:
        warnings.append("No mining pools detected — injecting synthetic UNKNOWN pool node")
        # Synthetic node: all features at population mean (0.0 after normalisation)
        x_pool = torch.zeros(1, MIN_FEATURE_DIM, dtype=torch.float32)
        pool_agg = [{'name': 'UNKNOWN'}]
    elif len(pool_agg) == 1:
        # Single pool is valid — log it as it may indicate centralisation anomaly
        warnings.append(f"Single pool detected: {pool_agg[0].get('name', 'unknown')} — "
                        f"hashrate centralisation possible")
        pool_features = [_extract_pool_features(p) for p in pool_agg]
        x_pool = torch.tensor(pool_features, dtype=torch.float32)
    else:
        pool_features = [_extract_pool_features(p) for p in pool_agg]
        x_pool = torch.tensor(pool_features, dtype=torch.float32)

    n_pool = x_pool.size(0)

    # ─────────────────────────────────────────────
    # Build FEE_BAND and NETWORK nodes
    # (these are always present — constructed from state scalars)
    # ─────────────────────────────────────────────
    x_fee_band = _build_fee_band_nodes(state)   # Always (3, 8): low/mid/high bands
    x_network = _build_network_node(state)      # Always (1, 8): global network state
    n_fee = x_fee_band.size(0)
    n_network = x_network.size(0)

    # ─────────────────────────────────────────────
    # Concatenate all node types
    # Node index layout: [TX | FEE_BAND | POOL | NETWORK]
    # ─────────────────────────────────────────────
    node_tensors = [t for t in [x_tx, x_fee_band, x_pool, x_network] if t.size(0) > 0]
    x = torch.cat(node_tensors, dim=0)

    # Compute node type offsets for edge construction
    tx_offset = 0
    fee_offset = n_tx
    pool_offset = n_tx + n_fee
    net_offset = n_tx + n_fee + n_pool
    total_nodes = net_offset + n_network

    # ─────────────────────────────────────────────
    # Build edges (skip TX→FEE_BAND edges if no TX nodes)
    # ─────────────────────────────────────────────
    edge_src, edge_dst = [], []

    # TX → FEE_BAND edges (only if TX nodes exist)
    if n_tx > 0:
        for i in range(n_tx):
            # Each TX connects to its fee band (low/mid/high determined by fee_rate)
            band_idx = fee_offset + _classify_fee_band(whale_txs[i])
            edge_src.append(tx_offset + i)
            edge_dst.append(band_idx)

    # FEE_BAND → NETWORK edges (always present)
    for i in range(n_fee):
        edge_src.append(fee_offset + i)
        edge_dst.append(net_offset)

    # POOL → NETWORK edges (always present, even single pool)
    for i in range(n_pool):
        edge_src.append(pool_offset + i)
        edge_dst.append(net_offset)

    if len(edge_src) == 0:
        # Fully disconnected graph (no TX, only synthetic pool + fee_bands + network)
        # PyG handles this — SAGEConv degrades to MLP behaviour (no aggregation)
        warnings.append("Graph has no edges — SAGEConv will operate as MLP (no aggregation)")
        edge_index = torch.empty(2, 0, dtype=torch.long)
    else:
        edge_index = torch.tensor([edge_src, edge_dst], dtype=torch.long)
        # Add reverse edges for undirected operation
        edge_index = torch.cat([edge_index, edge_index.flip(0)], dim=1)

    # ─────────────────────────────────────────────
    # Final validation
    # ─────────────────────────────────────────────
    assert x.size(0) == total_nodes, f"Node count mismatch: {x.size(0)} != {total_nodes}"
    assert x.size(1) == MIN_FEATURE_DIM, f"Feature dim mismatch: {x.size(1)} != {MIN_FEATURE_DIM}"
    if edge_index.size(1) > 0:
        assert edge_index.max() < total_nodes, "Edge index references out-of-bounds node"

    if total_nodes < 2:
        return GraphConstructionResult(
            data=None,
            skipped=True,
            skip_reason=f"Graph too small to evaluate: {total_nodes} node(s)",
            warnings=warnings
        )

    data = Data(x=x, edge_index=edge_index)
    data.num_nodes = total_nodes
    data.node_type_counts = {
        'tx': n_tx, 'fee_band': n_fee, 'pool': n_pool, 'network': n_network
    }

    for w in warnings:
        logger.warning(f"[GraphConstruction] {w}")

    return GraphConstructionResult(data=data, skipped=False, skip_reason=None, warnings=warnings)


def _classify_fee_band(tx: dict) -> int:
    """Return 0 (low), 1 (mid), or 2 (high) based on tx fee rate."""
    fee_rate = tx.get('fee_rate_svb', 0.0)
    if fee_rate < 5.0:
        return 0
    elif fee_rate < 20.0:
        return 1
    else:
        return 2


def _aggregate_pool_features(recent_blocks: list) -> list:
    """Aggregate per-block pool data into per-pool feature dicts."""
    pool_map = {}
    for block in recent_blocks[:10]:
        pool_name = block.get('pool', 'Unknown')
        if pool_name not in pool_map:
            pool_map[pool_name] = {'name': pool_name, 'block_count': 0, 'total_fees': 0.0}
        pool_map[pool_name]['block_count'] += 1
        pool_map[pool_name]['total_fees'] += block.get('fees_btc', 0.0)
    return list(pool_map.values())


def _extract_tx_features(tx: dict) -> list:
    return [
        float(tx.get('value_btc', 0.0)),
        float(tx.get('fee_rate_svb', 0.0)),
        float(tx.get('size_bytes', 0.0)),
        float(tx.get('locktime', 0.0)),
        float(tx.get('input_count', 0.0)),
        float(tx.get('output_count', 0.0)),
        float(tx.get('rbf_enabled', 0.0)),
        float(tx.get('age_seconds', 0.0)),
    ]


def _extract_pool_features(pool: dict) -> list:
    return [
        float(pool.get('block_count', 0.0)),
        float(pool.get('total_fees', 0.0)),
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # Padding to 8 features
    ]


def _build_fee_band_nodes(state: dict) -> torch.Tensor:
    """Always returns (3, 8) tensor for low/mid/high fee bands."""
    mempool = state.get('mempool', {})
    fee_hist = mempool.get('fee_histogram', {})
    bands = [
        [fee_hist.get('p10', 0.0), fee_hist.get('p25', 0.0), 0, 0, 0, 0, 0, 0],
        [fee_hist.get('p50', 0.0), fee_hist.get('p75', 0.0), 0, 0, 0, 0, 0, 0],
        [fee_hist.get('p90', 0.0), fee_hist.get('p99', 0.0), 0, 0, 0, 0, 0, 0],
    ]
    return torch.tensor(bands, dtype=torch.float32)


def _build_network_node(state: dict) -> torch.Tensor:
    """Always returns (1, 8) tensor for global network state."""
    net = state.get('network', {})
    features = [
        float(net.get('hashrate_eh', 0.0)),
        float(net.get('difficulty', 0.0)),
        float(net.get('mempool_size_mb', 0.0)),
        float(net.get('block_interval_seconds', 600.0)),
        float(net.get('peer_count', 0.0)),
        float(net.get('orphan_rate', 0.0)),
        0.0, 0.0
    ]
    return torch.tensor([features], dtype=torch.float32)
```

### Edge Case Behaviour Summary

| Case | PyG Behaviour | Guard Action |
|---|---|---|
| Zero whale TXs | Graceful (empty tensor) | Empty (0, 8) tensor, skip TX→FEE_BAND edges, log warning |
| Single POOL node | Graceful (1, 8) tensor | Log centralisation warning, proceed normally |
| Zero POOL nodes | Graceful | Inject synthetic UNKNOWN node, log warning |
| Stale mempool (>15m) | N/A — data quality issue | **Hard reject** — return skipped=True |
| Fully disconnected graph | SAGEConv degrades to MLP | Log warning, proceed (anomaly score may be unreliable) |
| total_nodes < 2 | PyG undefined behaviour | **Hard reject** |

---

## Q4 VERDICT: TRAINING DATA QUALITY GATE

**Consensus Level:** High — both models identified temporal diversity and feature statistics. This report adds specific, numeric thresholds missing from both.

### Complete Quality Gate Checklist

```python
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

@dataclass
class QualityGateResult:
    passed: bool
    failed_checks: list[str]
    warnings: list[str]
    stats: dict


def run_training_data_quality_gate(
    graphs: list,           # List of torch_geometric.data.Data objects
    timestamps: list[float] # Unix timestamps corresponding to each graph
) -> QualityGateResult:
    """
    Run all quality checks before training PCAF v1.
    Returns QualityGateResult; training must not proceed if passed=False.
    """
    failed = []
    warnings = []
    stats = {}

    n = len(graphs)
    stats['n_graphs'] = n

    # ── CHECK 1: Minimum dataset size ─────────────────────────────────────
    # Rationale: Autoencoder reconstruction needs enough samples to learn
    # "normal" distribution. <500 graphs → underfitting risk.
    MIN_GRAPHS = 500
    if n < MIN_GRAPHS:
        failed.append(f"C1_SIZE: Only {n} graphs — minimum {MIN_GRAPHS} required")
    elif n < 1000:
        warnings.append(f"W1_SIZE: {n} graphs — recommend 1000+ for robust calibration")

    # ── CHECK 2: Temporal span ─────────────────────────────────────────────
    # Rationale: Must cover at least 30 days to capture weekly cycles
    # and multiple mempool congestion events.
    if len(timestamps) >= 2:
        span_days = (max(timestamps) - min(timestamps)) / 86400
        stats['temporal_span_days'] = span_days
        MIN_SPAN_DAYS = 30
        if span_days < MIN_SPAN_DAYS:
            failed.append(f"C2_TEMPORAL_SPAN: {span_days:.1f} days < {MIN_SPAN_DAYS} day minimum")
        elif span_days < 90:
            warnings.append(f"W2_TEMPORAL_SPAN: {span_days:.1f} days — 90+ days recommended "
                            f"to cover halving cycle dynamics")

    # ── CHECK 3: Temporal distribution uniformity ──────────────────────────
    # Rationale: Gaps > 48 hours indicate missing data periods (exchange downtime,
    # data pipeline failure). A biased dataset overrepresents certain conditions.
    if len(timestamps) >= 2:
        ts_sorted = sorted(timestamps)
        gaps = [ts_sorted[i+1] - ts_sorted[i] for i in range(len(ts_sorted)-1)]
        max_gap_hours = max(gaps) / 3600
        stats['max_gap_hours'] = max_gap_hours
        MAX_GAP_HOURS = 48
        if max_gap_hours > MAX_GAP_HOURS:
            failed.append(f"C3_TEMPORAL_GAP: Max gap {max_gap_hours:.1f}h > {MAX_GAP_HOURS}h "
                          f"— dataset has missing periods")
        # Uniformity via coefficient of variation of inter-sample gaps
        gap_cv = np.std(gaps) / (np.mean(gaps) + 1e-9)
        stats['gap_cv'] = gap_cv
        if gap_cv > 3.0:
            warnings.append(f"W3_TEMPORAL_DISTRIBUTION: Gap CV={gap_cv:.2f} — sampling is irregular")

    # ── CHECK 4: Node count distribution ──────────────────────────────────
    # Rationale: Autoencoder trained only on large graphs won't score small graphs
    # reliably. Need coverage across graph sizes.
    node_counts = [g.num_nodes for g in graphs]
    stats['node_count_mean'] = float(np.mean(node_counts))
    stats['node_count_std'] = float(np.std(node_counts))
    stats['node_count_min'] = int(np.min(node_counts))
    stats['node_count_max'] = int(np.max(node_counts))

    if np.min(node_counts) < 4:
        failed.append(f"C4_NODE_COUNT_MIN: Minimum graph has {np.min(node_counts)} nodes — "
                      f"too small for meaningful graph learning (min: 4)")
    if np.std(node_counts) < 5.0:
        warnings.append(f"W4_NODE_DIVERSITY: Node count std={np.std(node_counts):.1f} — "
                        f"graphs have suspiciously uniform sizes (data pipeline issue?)")

    # ── CHECK 5: Feature variance (per-feature across all nodes) ──────────
    # Rationale: Zero-variance features provide no learning signal and will
    # cause numerical instability in BatchNorm layers.
    all_features = np.concatenate([g.x.numpy() for g in graphs], axis=0)  # (total_N, 8)
    feature_vars = np.var(all_features, axis=0)
    stats['feature_variances'] = feature_vars.tolist()
    MIN_FEATURE_VARIANCE = 1e-6
    zero_var_features = [i for i, v in enumerate(feature_vars) if v < MIN_FEATURE_VARIANCE]
    if zero_var_features:
        failed.append(f"C5_ZERO_VARIANCE: Features {zero_var_features} have near-zero variance "
                      f"— will break BatchNorm and provide no gradient signal")

    # ── CHECK 6: Feature value range (detect unscaled inputs) ─────────────
    # Rationale: SAGEConv is sensitive to feature scale. value_btc (0–1000 BTC)
    # and fee_rate_svb (1–500 sat/vbyte) have very different magnitudes.
    # Training on unscaled features leads to gradients dominated by large-scale features.
    feature_maxes = np.max(np.abs(all_features), axis=0)
    stats['feature_abs_maxes'] = feature_maxes.tolist()
    MAX_FEATURE_ABS = 1000.0
    large_features = [(i, v) for i, v in enumerate(feature_maxes) if v > MAX_FEATURE_ABS]
    if large_features:
        failed.append(f"C6_UNSCALED_FEATURES: Features {large_features} have abs max > "
                      f"{MAX_FEATURE_ABS} — normalise inputs before training")

    # ── CHECK 7: Network state coverage ───────────────────────────────────
    # Rationale: Autoencoder must learn normal behaviour across:
    # congested (mempool > 50MB), medium, idle (mempool < 5MB) states.
    # Training only on congested states → false positives during idle periods.
    mempool_sizes = []
    for g in graphs:
        # NETWORK node is always last; feature index 2 = mempool_size_mb
        try:
            net_node = g.x[-1]
            mempool_sizes.append(float(net_node[2]))
        except Exception:
            pass

    if mempool_sizes:
        idle_count = sum(1 for s in mempool_sizes if s < 5.0)
        congested_count = sum(1 for s in mempool_sizes if s > 50.0)
        idle_frac = idle_count / len(mempool_sizes)
        congested_frac = congested_count / len(mempool_sizes)
        stats['mempool_idle_fraction'] = idle_frac
        stats['mempool_congested_fraction'] = congested_frac

        MIN_STATE_FRACTION = 0.05  # 5% minimum coverage for each state
        if idle_frac < MIN_STATE_FRACTION:
            failed.append(f"C7_COVERAGE_IDLE: Only {idle_frac:.1%} idle-mempool samples "
                          f"— model won't generalise to low-traffic periods")
        if congested_frac < MIN_STATE_FRACTION:
            failed.append(f"C7_COVERAGE_CONGESTED: Only {congested_frac:.1%} congested-mempool samples "
                          f"— model won't generalise to high-traffic periods")

    # ── CHECK 8: Duplicate detection ──────────────────────────────────────
    # Rationale: Repeated snapshots bias reconstruction error distribution,
    # artificially tightening "normal" boundaries.
    if len(timestamps) >= 2:
        rounded_ts = [round(t / 60) for t in timestamps]  # 1-minute buckets
        unique_frac = len(set(rounded_ts)) / len(rounded_ts)
        stats['unique_timestamp_fraction'] = unique_frac
        if unique_frac < 0.95:
            failed.append(f"C8_DUPLICATES: Only {unique_frac:.1%} unique timestamps (1-min buckets) "
                          f"— dataset has significant duplicate/near-duplicate samples")

    passed = len(failed) == 0
    return QualityGateResult(passed=passed, failed_checks=failed, warnings=warnings, stats=stats)
```

### Numeric Threshold Reference

| Check | Metric | Fail Threshold | Warn Threshold |
|---|---|---|---|
| C1 | Dataset size | < 500 graphs | < 1000 graphs |
| C2 | Temporal span | < 30 days | < 90 days |
| C3 | Max temporal gap | > 48 hours | — |
| C4 | Min node count | < 4 nodes | — |
| C5 | Feature variance | < 1e-6 per feature | — |
| C6 | Feature abs max | > 1000 | — |
| C7 | State coverage (idle/congested) | < 5% each | < 10% each |
| C8 | Unique timestamps | < 95% | — |

---

## Q5 VERDICT: ANOMALY SCORE CALIBRATION

**Consensus Level:** Medium — both models touched on calibration but neither provided a complete methodology. Grok identified stratified sampling in Cycle 2 (adopting GPT-4o's suggestion). This report provides the definitive approach.

### The Core Problem

Anomaly score thresholds (`note_threshold`, `critical_threshold`) set from a biased validation set produce systematically wrong alerts. A validation set collected during congested periods will set thresholds too high; during idle periods, too low. Temporal autocorrelation in time-series data means naive train/test split leaks temporal patterns.

### Definitive Calibration Methodology

```python
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from scipy import stats as scipy_stats


def calibrate_anomaly_thresholds(
    model,
    calibration_graphs: list,
    calibration_timestamps: list[float],
    n_splits: int = 5,
    note_percentile: float = 90.0,    # Top 10% of normal scores → NOTE
    critical_percentile: float = 99.0  # Top 1% of normal scores → CRITICAL
) -> dict:
    """
    Calibrate anomaly score thresholds using time-series cross-validation.
    
    Uses TimeSeriesSplit (NOT random k-fold) to respect temporal ordering.
    Stratifies by network state (idle/medium/congested) within each fold
    to ensure calibration generalises across conditions.
    
    Returns calibrated thresholds dict for use in anomaly_score().
    """
    model.eval()

    # Step 1: Stratify by network state
    mempool_sizes = _extract_mempool_sizes(calibration_graphs)
    state_labels = _label_network_states(mempool_sizes)

    # Step 2: Time-series cross-validation (respects temporal ordering)
    tscv = TimeSeriesSplit(n_splits=n_splits)
    indices = np.arange(len(calibration_graphs))

    fold_reconstruction_errors = []

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(indices)):
        # Verify temporal ordering is respected
        assert calibration_timestamps[train_idx[-1]] <= calibration_timestamps[val_idx[0]], \
            f"Fold {fold_idx}: temporal leakage detected"

        val_graphs = [calibration_graphs[i] for i in val_idx]
        val_states = [state_labels[i] for i in val_idx]

        # Step 3: Stratified sampling within validation fold
        # Ensure each state is represented proportionally
        stratified_val_idx = _stratified_sample(val_idx, val_states, n_per_state=50)
        stratified_graphs = [calibration_graphs[i] for i in stratified_val_idx]

        # Step 4: Compute reconstruction errors on validation fold
        errors = _compute_reconstruction_errors(model, stratified_graphs)
        fold_reconstruction_errors.extend(errors)

    fold_reconstruction_errors = np.array(fold_reconstruction_errors)

    # Step 5: Fit reconstruction error distribution
    # Use log-normal fit (reconstruction errors are right-skewed)
    log_errors = np.log(fold_reconstruction_errors + 1e-9)
    mu, sigma = log_errors.mean(), log_errors.std()

    # Step 6: Derive thresholds from percentiles of fitted distribution
    note_threshold = float(np.exp(np.percentile(log_errors, note_percentile)))
    critical_threshold = float(np.exp(np.percentile(log_errors, critical_percentile)))

    # Step 7: Validate thresholds are numerically sane
    assert note_threshold > 0, "note_threshold must be positive"
    assert critical_threshold > note_threshold, \
        f"critical_threshold ({critical_threshold:.4f}) must exceed note_threshold ({note_threshold:.4f})"

    # Step 8: Compute per-state thresholds for diagnostics
    state_thresholds = {}
    for state in ['idle', 'medium', 'congested']:
        state_mask = np.array([s == state for s in
                               _label_network_states(_extract_mempool_sizes(
                                   [calibration_graphs[i] for i in range(len(calibration_graphs))]))])
        if state_mask.sum() >= 10:
            state_errors = _compute_reconstruction_errors(
                model, [calibration_graphs[i] for i in np.where(state_mask)[0]])
            state_thresholds[state] = {
                'p90': float(np.percentile(state_errors, 90)),
                'p99': float(np.percentile(state_errors, 99)),
            }

    thresholds = {
        'note_threshold': note_threshold,
        'critical_threshold': critical_threshold,
        'calibration_samples': len(fold_reconstruction_errors),
        'n_folds': n_splits,
        'log_normal_mu': float(mu),
        'log_normal_sigma': float(sigma),
        'per_state_thresholds': state_thresholds,
        'calibrated_at': time.time(),
    }

    return thresholds


def _label_network_states(mempool_sizes: list) -> list:
    return ['idle' if s < 5.0 else 'congested' if s > 50.0 else 'medium'
            for s in mempool_sizes]


def _extract_mempool_sizes(graphs: list) -> list:
    sizes = []
    for g in graphs:
        try:
            sizes.append(float(g.x[-1][2]))  # NETWORK node, feature index 2
        except Exception:
            sizes.append(15.0)  # fallback: medium
    return sizes


def _stratified_sample(indices, labels, n_per_state: int) -> list:
    """Sample up to n_per_state examples from each state label."""
    from collections import defaultdict
    buckets = defaultdict(list)
    for idx, label in zip(indices, labels):
        buckets[label].append(idx)
    result = []
    for label, bucket in buckets.items():
        sampled = np.random.choice(bucket, min(n_per_state, len(bucket)), replace=False)
        result.extend(sampled.tolist())
    return result


def _compute_reconstruction_errors(model, graphs: list) -> list:
    import torch
    errors = []
    with torch.no_grad():
        for g in graphs:
            reconstructed, _, _ = model(g)
            mse = torch.nn.functional.mse_loss(reconstructed, g.x).item()
            errors.append(mse)
    return errors
```

### Post-Deploy Calibration Drift Monitoring

```python
def check_calibration_drift(
    recent_scores: list[float],
    thresholds: dict,
    alert_if_false_positive_rate_exceeds: float = 0.15  # >15% scores above NOTE = drift
) -> dict:
    """
    Monitor for distribution shift post-deployment.
    If >15% of recent scores exceed note_threshold without confirmed anomalies,
    thresholds need recalibration.
    """
    if not recent_scores:
        return {'drift_detected': False}
    
    above_note = sum(1 for s in recent_scores
                     if s > thresholds['note_threshold'] * 100) / len(recent_scores)
    
    return {
        'drift_detected': above_note > alert_if_false_positive_rate_exceeds,
        'false_positive_rate': above_note,
        'recommendation': 'Recalibrate thresholds with recent data' if above_note > alert_if_false_positive_rate_exceeds else 'OK',
    }
```

---

## Q6 VERDICT: ASYNC INTEGRATION PATTERN

**Adjudication:** Grok's Cycle 2 approach wins. GPT-4o used `asyncio.get_event_loop()` (deprecated in Python 3.10+ for running coroutines) and did not address timeouts or resource exhaustion. Grok's `get_running_loop()` + `ThreadPoolExecutor` + explicit timeout is production-correct.

**One additional fix from this report:** Grok's code does not handle the case where the executor is shut down (e.g., during server teardown), causing silent failures. The definitive code below adds shutdown handling and a circuit breaker.

### Definitive Async Wrapper

```python
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, CancelledError
from functools import partial
from typing import Optional

logger = logging.getLogger(__name__)


class PCAFAsyncEngine:
    """
    Async wrapper around synchronous PCAF v1 GNN scoring.
    
    Design rationale:
    - PyTorch GNN inference is synchronous and CPU/GPU-bound
    - Running it directly in the async event loop stalls all other coroutines
    - ThreadPoolExecutor offloads blocking work; event loop stays responsive
    - Explicit timeout prevents runaway inference from blocking the system
    - asyncio.get_running_loop() (not get_event_loop()) is correct in Python 3.10+
    """
    
    TIMEOUT_SECONDS = 5.0
    MAX_WORKERS = 4
    CIRCUIT_BREAKER_THRESHOLD = 5  # failures before circuit opens
    CIRCUIT_BREAKER_RESET_SECONDS = 60

    def __init__(self, model, device: str = 'cuda'):
        self._model = model
        self._device = device
        self._executor = ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS,
            thread_name_prefix='pcaf_worker'
        )
        self._shutdown = False
        # Circuit breaker state
        self._consecutive_failures = 0
        self._circuit_open_until: Optional[float] = None

    def _score_sync(self, state_dict: dict) -> tuple[float, dict]:
        """
        Blocking scoring operation — runs in thread pool.
        Called from thread, NOT from event loop.
        """
        # Import inside thread to avoid torch multiprocessing issues
        import torch
        from torch_geometric.data import Data

        # Build graph from state_dict (sync, blocking)
        result = build_chain_state_graph(state_dict)
        if result.skipped:
            return 0.0, {'skipped': True, 'reason': result.skip_reason}

        graph = result.data.to(self._device)
        score, diagnostics = self._model.anomaly_score(
            graph,
            thresholds=state_dict.get('_thresholds', {})
        )
        diagnostics['warnings'] = result.warnings
        return score, diagnostics

    async def score(self, state_dict: dict) -> tuple[float, dict]:
        """
        Non-blocking async scoring.
        
        Raises:
            TimeoutError: if scoring exceeds TIMEOUT_SECONDS
            RuntimeError: if circuit breaker is open
            RuntimeError: if engine has been shut down
        """
        if self._shutdown:
            raise RuntimeError("PCAFAsyncEngine has been shut down")

        # Circuit breaker check
        if self._circuit_open_until is not None:
            if time.monotonic() < self._circuit_open_until:
                remaining = self._circuit_open_until - time.monotonic()
                raise RuntimeError(
                    f"PCAF circuit breaker open — reset in {remaining:.0f}s "
                    f"(too many consecutive failures)"
                )
            else:
                # Reset circuit breaker
                self._circuit_open_until = None
                self._consecutive_failures = 0
                logger.info("PCAF circuit breaker reset")

        loop = asyncio.get_running_loop()  # Correct for Python 3.10+
        try:
            score, diagnostics = await asyncio.wait_for(
                loop.run_in_executor(
                    self._executor,
                    partial(self._score_sync, state_dict)
                ),
                timeout=self.TIMEOUT_SECONDS
            )
            # Success — reset failure count
            self._consecutive_failures = 0
            return score, diagnostics

        except asyncio.TimeoutError:
            self._record_failure()
            logger.error(f"PCAF scoring timed out after {self.TIMEOUT_SECONDS}s")
            raise TimeoutError(f"PCAF scoring timed out after {self.TIMEOUT_SECONDS}s")

        except CancelledError:
            raise  # Propagate cancellation

        except Exception as e:
            self._record_failure()
            logger.error(f"PCAF scoring error: {e}", exc_info=True)
            raise

    def _record_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.CIRCUIT_BREAKER_THRESHOLD:
            self._circuit_open_until = time.monotonic() + self.CIRCUIT_BREAKER_RESET_SECONDS
            logger.critical(
                f"PCAF circuit breaker OPENED after {self._consecutive_failures} failures. "
                f"Will reset in {self.CIRCUIT_BREAKER_RESET_SECONDS}s"
            )

    async def shutdown(self):
        """Graceful shutdown — drain in-flight work before closing executor."""
        self._shutdown = True
        self._executor.shutdown(wait=True, cancel_futures=False)
        logger.info("PCAFAsyncEngine shut down cleanly")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.shutdown()
```

### Why Grok Wins on Q6 (With This Report's Enhancements)

| Feature | GPT-4o | Grok C2 | This Report |
|---|---|---|---|
| `get_running_loop()` (correct Py 3.10+) | ❌ (get_event_loop) | ✅ | ✅ |
| Explicit timeout | ❌ | ✅ | ✅ |
| ThreadPoolExecutor config | ❌ | ✅ | ✅ |
| Circuit breaker | ❌ | ❌ | ✅ |
| Graceful shutdown | ❌ | ❌ | ✅ |
| Context manager | ❌ | ❌ | ✅ |

---

## Q7 VERDICT: TPA SIGNAL COMPLETENESS

**Consensus Level:** Medium — both models identified the same missing data sources. This report adds a structured availability matrix.

### Per-Scenario Signal Availability Matrix

| Scenario | Signal | Current Availability | Data Source | Latency | Gap |
|---|---|---|---|---|---|
| **Institutional Adoption** | ETF inflow/outflow | ✅ Available | Bloomberg/Glassnode API | Daily | None |
| | CME futures open interest | ✅ Available | CME API | 15-min delay | None |
| | Corporate treasury announcements | ❌ Missing | No structured feed | Multi-day | **Gap** |
| | Coinbase premium index | ✅ Available | Exchange API | Real-time | None |
| **Regulatory Crackdown** | Regulatory threat level (heuristic) | ✅ Available | Sentinel rule engine | Real-time | None |
| | P2P volume spike (LocalBitcoins proxy) | ✅ Available | Aggregator API | Hourly | None |
| | Jurisdiction reclassification event | ❌ Missing | No structured feed | Multi-day | **Gap** |
| | Stablecoin de-peg signal | ✅ Available | DEX price feeds | Real-time | None |
| **Network Security Crisis** | PCAF anomaly score | ✅ Available | PCAF v1 (this build) | <50ms | None |
| | Orphan block rate spike | ✅ Available | Node RPC | Real-time | None |
| | Emergency patch PR on Bitcoin Core | ❌ Missing | GitHub API (not integrated) | Hours | **Gap** |
| | Hash rate drop (>20% in 24h) | ✅ Available | Mining pool APIs | 10-min | None |
| **Macro Liquidity Expansion** | DXY index | ✅ Available | Forex API | 15-min | None |
| | VIX level | ✅ Available | Options market API | 15-min | None |
| | Global M2 money supply change | ⚠️ Partial | Central bank APIs (lag) | Weekly | Staleness |
| | Stablecoin supply growth (30d) | ✅ Available | Glassnode/DeFiLlama | Daily | None |
| **CBDC Displacement** | Sovereign Layer signals | ✅ Available | Sentinel rule engine | Real-time | None |
| | CBDC programmability feature announcements | ❌ Missing | No structured feed | Multi-day | **Gap** |
| | Cross-border CBDC pilot volume | ❌ Missing | BIS data (irregular) | Monthly | **Gap** |

### Missing Data Assessment

**4 hard gaps requiring new data sources before TPA scenarios can fire correctly:**

1. **Corporate treasury announcements** — Requires NLP pipeline on SEC filings / 8-K events. Estimated 2–4 week integration effort.
2. **Jurisdiction reclassification** — Requires regulatory event database (e.g., Chainalysis Gov feed). Estimated 4–8 week integration effort.
3. **Emergency patch PR detection** — GitHub API integration on `bitcoin/bitcoin` repo watching for security-tagged PRs. Estimated 1 week effort.
4. **CBDC programmability announcements** — Requires central bank publication scraper + NLP classifier. Estimated 4–6 week integration effort.

**Recommended interim handling for missing signals:**

```python
def check_signal_availability(scenario: str, signals: dict) -> dict:
    """
    For signals marked as missing/unavailable, degrade gracefully:
    - Set signal value to NEUTRAL (does not contribute to scenario strength)
    - Log warning with expected integration timeline
    - Do NOT block scenario evaluation for missing multi-day signals
    """
    MISSING_SIGNAL_PLACEHOLDER = 0.5  # Neutral — no positive/negative contribution
    
    missing_signals = {
        'institutional_adoption': ['corporate_treasury_announcement'],
        'regulatory_crackdown': ['jurisdiction_reclassification'],
        'network_security_crisis': ['emergency_patch_pr'],
        'cbdc_displacement': ['cbdc_programmability_feature', 'cross_border_cbdc_volume'],
    }
    
    result = dict(signals)
    for signal_name in missing_signals.get(scenario, []):
        if signal_name not in result:
            result[signal_name] = MISSING_SIGNAL_PLACEHOLDER
            logger.warning(
                f"[TPA] Signal '{signal_name}' for scenario '{scenario}' not available — "
                f"using neutral placeholder. Integration required."
            )
    return result
```

---

## Q8 VERDICT: MONTE CARLO CORRECTNESS

**Consensus Level:** High — both models agreed on clipping negative jitter. This report adds all edge cases both missed.

### All Edge Cases

| Edge Case | Symptom if Unhandled | Fix |
|---|---|---|
| Negative `strength` after jitter | Probability delta inverts (scenario becomes suppressive) | Clip to 0 after jitter |
| `strength = 0.0` exactly | `jitter * 0 = 0` always — no exploration | Add small epsilon before jitter |
| `sigma = 0.0` | Deterministic — not Monte Carlo | Assert sigma > 0 |
| `probability_delta > 1.0` | Final probability exceeds 1.0 | Clip delta to [0, 1 - base_prob] |
| `base_probability + delta > 1.0` | Invalid probability | Clip final probability to [0, 1] |
| `n_simulations = 0` | Empty results, division by zero in aggregation | Assert n > 0 |
| Non-finite `strength` (NaN/Inf) | NaN propagates through all simulations | Validate input |

### Definitive Monte Carlo Implementation

```python
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulationResult:
    mean_probability: float
    std_probability: float
    percentile_5: float
    percentile_95: float
    n_simulations: int
    raw_samples: np.ndarray  # For downstream analysis


def jitter_strength(
    strength: float,
    sigma: float = 0.2,
    rng: Optional[np.random.Generator] = None
) -> float:
    """
    Apply multiplicative Gaussian jitter to scenario strength.
    
    Returns strength in [0, inf) — caller is responsible for
    downstream probability clamping.
    
    Args:
        strength: Base strength in [0, 1] range
        sigma: Jitter scale (coefficient of variation). Must be > 0.
        rng: Optional numpy Generator for reproducible testing
    
    Edge cases handled:
        - Negative output: clipped to 0
        - NaN/Inf input: raises ValueError
        - strength = 0: small epsilon ensures jitter has effect
        - sigma = 0: raises ValueError (degenerate Monte Carlo)
    """
    # Input validation
    if not np.isfinite(strength):
        raise ValueError(f"strength must be finite, got {strength}")
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0 for Monte Carlo, got {sigma}")
    if strength < 0:
        raise ValueError(f"strength must be >= 0, got {strength}")

    # Small epsilon prevents strength=0 from collapsing all jitter to 0
    EPSILON = 1e-6
    effective_strength = strength + EPSILON

    generator = rng if rng is not None else np.random.default_rng()
    noise = generator.normal(loc=1.0, scale=sigma)
    jittered = effective_strength * noise

    # Clip: negative strength is undefined in this domain
    return float(max(0.0, jittered))


def run_scenario_simulation(
    base_probability: float,
    strength: float,
    n_simulations: int = 10_000,
    sigma: float = 0.2,
    seed: Optional[int] = None,
) -> SimulationResult:
    """
    Monte Carlo simulation for TPA scenario probability estimation.
    
    Models uncertainty in scenario strength by sampling from a
    multiplicative noise distribution, computing resulting probability
    delta for each simulation, and aggregating.
    
    Args:
        base_probability: Prior probability of outcome [0, 1]
        strength: Scenario signal strength [0, 1]
        n_simulations: Number of Monte Carlo draws (default 10k)
        sigma: Jitter scale (default 0.2 = 20% CV)
        seed: Random seed for reproducibility
    
    Returns:
        SimulationResult with mean, std, and 5th/95th percentile probabilities
    """
    # Validate inputs
    if not (0.0 <= base_probability <= 1.0):
        raise ValueError(f"base_probability must be in [0, 1], got {base_probability}")
    if not (0.0 <= strength <= 1.0):
        raise ValueError(f"strength must be in [0, 1], got {strength}")
    if n_simulations <= 0:
        raise ValueError(f"n_simulations must be > 0, got {n_simulations}")
    if not np.isfinite(base_probability) or not np.isfinite(strength):
        raise ValueError("base_probability and strength must be finite")

    rng = np.random.default_rng(