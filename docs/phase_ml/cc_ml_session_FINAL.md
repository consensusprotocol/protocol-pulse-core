# ML SESSION — PCAF V1 GNN + TEMPORAL PREDICTIVE ANALYTICS
# Protocol Pulse Intelligence Terminal · The Unprecedented Features
# AUDIT-HARDENED BUILD DOCUMENT · 2026-03-23
# All changes from original marked: # AUDIT FIX: [description]

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENVIRONMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
  PyTorch 2.6.0 + CUDA 12.4: INSTALLED ✅
  torch_geometric: NOT INSTALLED — install first (Step 0)
  numpy 1.25.2, scipy 1.13.1: INSTALLED ✅
  GPU 0: RTX 4090 24GB (some VRAM used by other tasks)
  GPU 1: RTX 4090 24GB (~22GB free) — DEDICATED TO PCAF v1
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVIOLABLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
1. NEVER `from services.X import Y` — always importlib.util path loading
2. GUNICORN must start from ~/protocol_pulse/core/
3. PCAF v1 must fall back to PCAF v0 if model file missing or GPU error
4. TPA runs on CPU only (no GPU needed — Monte Carlo is fast on CPU)
5. Both features write to QWEN_CONTEXT_BIBLE.md for every bug found
6. Commit after each major milestone, not just at the end
7. # AUDIT FIX: [Q1-SYNTHESIS] Never use --break-system-packages in
   production scripts. All pip installs run inside the project venv.
   Activate venv first: source ~/protocol_pulse/venv/bin/activate
8. # AUDIT FIX: [Q6-SYNTHESIS] PCAF GPU inference is serialized:
   ThreadPoolExecutor max_workers=1 for GPU ops. Increase only with
   explicit torch.cuda.stream() isolation per thread.
9. # AUDIT FIX: [Q2] Decoder MUST receive edge_index and batch from
   the original graph. A SAGEConv decoder without edge_index degenerates
   to a linear layer — the architectural bug that kills anomaly detection.
```

```
WRITE PROGRESS LOG: ~/protocol_pulse/logs/ml_session.log
```

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 0 — INSTALL torch_geometric (AUDIT-HARDENED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```bash
# AUDIT FIX: [Q1-SYNTHESIS] Activate venv first. Never install into system Python.
# The --break-system-packages flag is Debian-specific and wrong for venv installs.
source ~/protocol_pulse/venv/bin/activate

# Verify PyTorch version matches wheel index exactly before installing
python3 -c "import torch; print(torch.__version__, torch.version.cuda)"
# Must output: 2.6.0  12.4
# If output differs, wheels below will fail — see FALLBACK STRATEGY

# AUDIT FIX: [Q1] torch_scatter is a HARD DEPENDENCY for SAGEConv.
# GPT-4o was wrong: SAGEConv cannot run without torch_scatter.
# There is NO graceful degradation path. Install in this exact order:
pip install torch_geometric

pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html

# FUNCTIONAL SMOKE TEST — not just import check
# AUDIT FIX: [Q1] Import-only checks give false confidence. Run actual conv pass.
python3 - <<'SMOKE'
try:
    import torch_scatter
    from torch_geometric.nn import SAGEConv
    import torch

    conv = SAGEConv(8, 64)
    x = torch.randn(5, 8)
    edge_index = torch.tensor([[0, 1, 2, 1], [1, 2, 3, 0]], dtype=torch.long)
    out = conv(x, edge_index)
    assert out.shape == (5, 64), f"Wrong shape: {out.shape}"
    print("SMOKE TEST PASS: SAGEConv forward pass OK, shape", out.shape)
except ImportError as e:
    print(f"HARD FAILURE: {e}")
    print("torch_scatter is required. SAGEConv has NO fallback path.")
    print("PCAF v1 cannot deploy without this. Do not proceed.")
    raise SystemExit(1)
SMOKE
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 0 — FALLBACK STRATEGY (if wheels unavailable for torch 2.6.0+cu124)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
# AUDIT FIX: [Q1] PyG CDN lags new PyTorch releases by 4-8 weeks.
# If you see "No matching distribution found", use one of these strategies:

OPTION A — Downgrade to last known-good PyTorch+CUDA combination:
  pip install torch==2.3.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121
  pip install pyg_lib torch_scatter torch_sparse \
    -f https://data.pyg.org/whl/torch-2.3.0+cu121.html
  # RTX 4090 has CUDA compute capability 8.9, compatible with cu121

OPTION B — Build from source (~20 min, uses exact CUDA version):
  pip install torch_geometric --no-binary torch_geometric
  TORCH_CUDA_ARCH_LIST="8.9" \
    pip install torch_scatter torch_sparse \
    --no-binary torch_scatter,torch_sparse
  # RTX 4090 = Compute Capability 8.9

After either fallback: re-run the smoke test above.
Record result in ~/protocol_pulse/logs/ml_session.log before continuing.
```

```bash
# Log installation result
echo "[$(date -u)] [STEP_0] torch_geometric install complete. \
Smoke test: $(python3 -c 'from torch_geometric.nn import SAGEConv; \
import torch; c=SAGEConv(4,8); \
x=torch.randn(3,4); ei=torch.tensor([[0,1],[1,2]],dtype=torch.long); \
print(c(x,ei).shape)')" \
>> ~/protocol_pulse/logs/ml_session.log
```

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — PCAF V1 AUDIT (COMPLETE — REFERENCE REPORT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
The two-cycle GPT-4o + Grok-3 audit has been completed. Report is at:
  docs/audits/pcaf_v1_audit_2026-03-23.md

Key confirmed findings incorporated into this build document:

ARCHITECTURE: GraphSAGE Autoencoder confirmed with one critical fix.
  The original decoder spec did NOT pass edge_index — this collapses
  SAGEConv to a linear layer. Fix is in FILE 1 below. [Q2 VERDICT]

DATA QUALITY: 7 quality gates defined. All must PASS before training.
  Temporal coverage, event balance, feature variance, staleness checks.
  Full implementation in FILE 3 (pcaf_trainer.py). [Q4 VERDICT]

COLD START: Conservative defaults until offline calibration complete.
  p95=0.15, p99=0.35 as cold-start thresholds. [Q5 VERDICT]

LATENCY: Confirmed <50ms on GPU for ~220 nodes / ~600 edges.
  Hard timeout at 200ms in async wrapper. [Q6 VERDICT]

MISSING GRAPH FEATURE: Temporal TX ordering edges improve detection.
  Added as edge type 6 in graph construction. [Q3/Q4 SYNTHESIS]

VGAE: Recommended for v2. GraphSAGE autoencoder ships as v1. [Q2]

Full audit script preserved at: utils/pcaf_v1_audit.py
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — TPA AUDIT (COMPLETE — REFERENCE REPORT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
Audit report at: docs/audits/tpa_audit_2026-03-23.md

Key confirmed findings incorporated into this build document:

MONTE CARLO: n_simulations=1000 insufficient. Use 5000.
  With 1000 iterations, CI width on 50% probability ≈ ±3.1% — enough
  to flip alert/no-alert on sampling noise alone. 5000 → ±1.4%. [Q8]

JITTER: Multiplicative Gaussian, sigma=0.2, clip to [0,1].
  Negative jitter is non-physical. Zero signals stay zero. [Q8 VERDICT]

CONTRADICTION MATRIX: Full 5×5 matrix defined in tpa_scenario_correlations.json.
  Strongest: S3↔S1 (-20%). S2↔S1 (-15%). [Q4 VERDICT]

WEAKEST SCENARIO: CBDC Displacement has lowest SNR. [Q1 VERDICT]
  Redesigned signal set in tpa_scenarios.json.

CALIBRATION: Beta distribution fitting against 4 historical cycles.
  Stored in data/tpa_calibration.json with confidence intervals. [Q2]

SHARE URL: UUID4 tokens, HMAC-SHA256 signing, 24h TTL.
  Secret key from environment variable PCAF_SNAPSHOT_SECRET_KEY. [Q9]

MISSING SIGNALS P0: GitHub emergency patch PR detection + US10Y yield.
  Both added to FILE 1 (tpa_scenarios.json). [Q7 VERDICT]

Full audit script preserved at: utils/tpa_audit.py
```

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — BUILD PCAF V1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Apply all audit findings. Implement files in this order. Each file is
complete — write exactly as shown, no placeholders.

---

## FILE 1: services/pcaf_v1_model.py

```python
"""
PCAF v1 — GNN Autoencoder for Bitcoin chain-state anomaly detection.
GraphSAGE encoder/decoder architecture.

AUDIT FIX: [Q2] Decoder receives edge_index + batch from original graph.
  Original spec omitted this. A SAGEConv without edge_index degenerates
  to a linear layer with no neighborhood aggregation. This was the single
  most dangerous architectural bug in the original spec.

AUDIT FIX: [Q1] Hard dependency check at module load time.
  Fails loudly if torch_scatter is missing — no silent degradation.
"""

# AUDIT FIX: [Q1] Hard dependency gate — fail at import, not at inference
def _verify_dependencies() -> None:
    try:
        import torch_scatter  # noqa: F401
        from torch_geometric.nn import SAGEConv  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            f"PCAF v1 hard dependency missing: {e}. "
            "torch_scatter is required — SAGEConv has no fallback path. "
            "Run: pip install torch_scatter "
            "-f https://data.pyg.org/whl/torch-2.6.0+cu124.html"
        ) from e

_verify_dependencies()

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, global_mean_pool
from torch_geometric.data import Data


class ChainStateEncoder(nn.Module):
    """
    GraphSAGE encoder: node features → graph-level latent vector.
    Architecture: 8 → 64 → 128 → 256 (per node), global pool → 128 → 32.

    AUDIT FIX: [Q2] Returns (latent, node_x) — node embeddings preserved
    for potential skip connections in decoder (not used in v1, ready for v2).
    """

    def __init__(self, in_channels: int = 8, latent_dim: int = 32):
        super().__init__()
        self.conv1 = SAGEConv(in_channels, 64)
        self.conv2 = SAGEConv(64, 128)
        self.conv3 = SAGEConv(128, 256)
        self.pool_proj = nn.Linear(256, 128)
        self.bottleneck = nn.Linear(128, latent_dim)
        # AUDIT FIX: [Q2] Dropout added per audit recommendation.
        # Original spec: "no BatchNorm (small graphs)" — correct, kept.
        # Dropout rate 0.1 is conservative for production inference.
        self.dropout = nn.Dropout(p=0.1)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
    ) -> tuple:
        """
        Args:
            x: [num_nodes, in_channels]
            edge_index: [2, num_edges]
            batch: [num_nodes] node-to-graph assignment

        Returns:
            latent: [num_graphs, latent_dim]
            node_x: [num_nodes, 256] final node embeddings
        """
        x = F.relu(self.conv1(x, edge_index))
        x = self.dropout(x)
        x = F.relu(self.conv2(x, edge_index))
        x = self.dropout(x)
        node_x = F.relu(self.conv3(x, edge_index))  # [num_nodes, 256]

        graph_emb = global_mean_pool(node_x, batch)      # [num_graphs, 256]
        graph_emb = F.relu(self.pool_proj(graph_emb))    # [num_graphs, 128]
        latent = self.bottleneck(graph_emb)               # [num_graphs, latent_dim]
        return latent, node_x


class ChainStateDecoder(nn.Module):
    """
    GraphSAGE decoder: latent vector → reconstructed node features.

    AUDIT FIX: [Q2] CRITICAL — edge_index and batch MUST be passed here.
    The original spec showed a decoder that only received 'latent'.
    Without edge_index, SAGEConv performs no neighborhood aggregation
    and the autoencoder cannot learn graph topology — anomaly detection fails.

    The latent[batch] expansion maps each node to its graph's latent vector,
    giving the decoder per-node starting points for reconstruction.
    For single-graph inference (PCAF v1 standard case), batch is all zeros
    and latent[batch] produces a repeated row — correct degenerate behavior.
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
        # latent[batch]: each node gets its graph's latent vector
        node_latent = latent[batch]                          # [num_nodes, latent_dim]
        x = F.relu(self.expand(node_latent))                # [num_nodes, 256]

        # AUDIT FIX: [Q2] edge_index passed to all decoder convolutions
        x = F.relu(self.conv1(x, edge_index))
        x = self.dropout(x)
        x = F.relu(self.conv2(x, edge_index))
        x = self.conv3(x, edge_index)  # No activation on final output layer
        return x


class ChainStateAutoencoder(nn.Module):
    """
    Full GNN autoencoder for Bitcoin chain-state anomaly detection.

    Input:  PyG Data object, heterogeneous nodes padded to 8 features.
    Output: (reconstructed_features, latent) from forward().
             anomaly score dict from anomaly_score().

    TorchScript compatible: no Python-only constructs in forward().
    AUDIT FIX: [Q2] batch=None handled explicitly — required for single-graph
    inference where DataLoader does not set batch attribute.
    """

    def __init__(self, in_channels: int = 8, latent_dim: int = 32):
        super().__init__()
        self.encoder = ChainStateEncoder(in_channels, latent_dim)
        self.decoder = ChainStateDecoder(latent_dim, in_channels)

    def forward(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
    ) -> tuple:
        """
        AUDIT FIX: [Q2] Signature changed from forward(data) to
        forward(x, edge_index, batch) for TorchScript compatibility.
        TorchScript cannot handle dynamic Data attribute access reliably.
        Caller unpacks Data before calling forward().

        Returns:
            reconstructed: [num_nodes, in_channels]
            latent: [num_graphs, latent_dim]
        """
        latent, _ = self.encoder(x, edge_index, batch)
        reconstructed = self.decoder(latent, edge_index, batch)
        return reconstructed, latent

    def reconstruction_loss(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
    ) -> torch.Tensor:
        """MSE loss for training. Per-node then mean-reduced."""
        reconstructed, _ = self.forward(x, edge_index, batch)
        return F.mse_loss(reconstructed, x)

    @torch.no_grad()
    def anomaly_score(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        batch: torch.Tensor,
        p95_threshold: float,
        p99_threshold: float,
    ) -> dict:
        """
        Returns anomaly score 0-100 and severity tier.

        AUDIT FIX: [Q5] Thresholds are parameters — not hardcoded constants.
        Caller passes current calibrated thresholds from AnomalyScoreCalibrator.
        This allows online threshold adaptation without model reload.

        Score normalization: (mse / p99_threshold) × 100, clipped to [0, 100].
        A graph reconstructed at exactly p99 error → score 100.
        A perfectly reconstructed graph → score 0.
        """
        self.eval()
        reconstructed, latent = self.forward(x, edge_index, batch)

        # Per-node MSE, then graph-level mean
        per_node_mse = F.mse_loss(
            reconstructed, x, reduction='none'
        ).mean(dim=1)
        graph_mse = per_node_mse.mean().item()

        # AUDIT FIX: [Q5] p99_threshold guard — prevent division by zero
        # during cold start before calibration completes
        safe_threshold = max(p99_threshold, 1e-8)
        score = min(100.0, max(0.0, (graph_mse / safe_threshold) * 100.0))

        return {
            "score": round(score, 2),
            "raw_mse": round(graph_mse, 6),
            "severity": (
                "CRITICAL"  if graph_mse > p99_threshold else
                "ELEVATED"  if graph_mse > p95_threshold else
                "NOMINAL"
            ),
            "latent_norm": round(latent.norm(dim=-1).mean().item(), 4),
            "per_node_max_mse": round(per_node_mse.max().item(), 6),
        }
```

---

## FILE 2: services/pcaf_data_collector.py

```python
"""
PCAF v1 Data Collector.
Runs as daemon thread started at Sentinel boot.
Every 60s: reads /tmp/sentinel_state.json → builds PyG Data → saves pkl.

AUDIT FIX: [Q3] Full guard code for all 3 failure modes:
  - Stale mempool data (>15min) → skip snapshot, log warning
  - Zero whale TXs → valid empty tensor, log INFO
  - Single pool → valid, log INFO (possible centralization event)

AUDIT FIX: [Q3-SYNTHESIS] edge_index bounds validation added.
  Original spec had no guard against edge_index referencing out-of-bounds
  nodes — a silent data corruption bug.

AUDIT FIX: [Q3] Added temporal TX ordering edges (edge type 6).
  Audit identified this as the most valuable missing graph feature.
  Captures arrival-sequence relationships between mempool transactions.
"""

import json
import logging
import os
import pickle
import threading
import time
from pathlib import Path
from typing import Optional

import torch
from torch_geometric.data import Data

logger = logging.getLogger(__name__)

# Constants
STALE_THRESHOLD_SECONDS = 900       # 15 minutes — AUDIT FIX: [Q3]
MAX_WHALE_TXS = 200
NODE_FEATURE_DIM = 8
COLLECTION_INTERVAL_SECONDS = 60
SENTINEL_STATE_PATH = Path("/tmp/sentinel_state.json")
TRAINING_DATA_DIR = Path(__file__).parent.parent / "data" / "pcaf_training"


class GraphConstructionError(Exception):
    """Raised when graph cannot be constructed. Caller skips this cycle."""
    pass


class DataCollector:
    """
    Background thread that collects SentinelState snapshots for PCAF v1 training.

    AUDIT FIX: [Q3] All exception types caught individually in run().
    Original had bare except — masked data corruption bugs silently.
    """

    def __init__(self, data_dir: Path = TRAINING_DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._running = False
        self._snapshot_count = 0
        self._skip_count = 0
        self._error_count = 0
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start collector as daemon thread. Called once at Sentinel boot."""
        self._running = True
        self._thread = threading.Thread(
            target=self.run,
            name="pcaf_data_collector",
            daemon=True,
        )
        self._thread.start()
        logger.info("PCAF data collector started. Writing to: %s", self.data_dir)

    def stop(self) -> None:
        self._running = False

    def build_graph(self, state: dict) -> Optional[Data]:
        """
        Build PyG Data object from SentinelState snapshot.
        Returns None if data is stale. Raises GraphConstructionError on
        unrecoverable structural failures. Degrades gracefully on missing
        optional node types (TX, POOL).

        AUDIT FIX: [Q3] Guard 1: Stale data check — return None, do not infer.
        AUDIT FIX: [Q3] Guard 2: Zero whale TXs — valid empty tensor, log INFO.
        AUDIT FIX: [Q3] Guard 3: Single pool — valid, log INFO.
        AUDIT FIX: [Q3-SYNTHESIS] edge_index bounds validation.
        """
        mempool = state.get("mempool", {})

        # ── GUARD 1: Stale mempool data ──────────────────────────────────────
        updated_at = mempool.get("updated_at", 0)
        data_age = time.time() - updated_at
        if data_age > STALE_THRESHOLD_SECONDS:
            logger.warning(
                "Skipping snapshot: mempool data is %.0fs old (threshold: %ds). "
                "No snapshot will be saved for this cycle.",
                data_age, STALE_THRESHOLD_SECONDS,
            )
            return None

        # ── TX NODES ─────────────────────────────────────────────────────────
        # GUARD 2: Zero whale TXs → empty tensor, graph still valid
        whale_txs = mempool.get("whale_txs", [])
        if len(whale_txs) == 0:
            logger.info(
                "No whale TXs in mempool. TX node set empty. "
                "Graph operates on fee/pool/network signals only."
            )
            tx_tensor = torch.zeros((0, NODE_FEATURE_DIM), dtype=torch.float32)
        else:
            tx_rows = []
            for tx in whale_txs[:MAX_WHALE_TXS]:
                tx_rows.append([
                    float(tx.get("value_btc", 0.0)),
                    float(tx.get("fee_rate_svb", 0.0)),
                    float(tx.get("size_vbytes", 0.0)),
                    float(tx.get("rbf_flag", 0)),
                    float(tx.get("age_seconds", 0.0)),
                    float(tx.get("is_replacement", 0)),
                    float(tx.get("output_count", 0)),
                    float(tx.get("input_count", 0)),
                ])
            tx_tensor = torch.tensor(tx_rows, dtype=torch.float32)

        # ── FEE BAND NODES (required anchor nodes) ────────────────────────────
        fee_bands = mempool.get("fee_bands", {})
        if not fee_bands:
            raise GraphConstructionError(
                "Fee band data missing. Fee bands are required anchor nodes. "
                "Cannot construct graph this cycle."
            )
        fee_tensor = torch.tensor(
            self._build_fee_band_rows(fee_bands),
            dtype=torch.float32,
        )

        # ── POOL NODES ────────────────────────────────────────────────────────
        # GUARD 3: Single pool → valid, log INFO
        recent_blocks = state.get("network", {}).get("recent_blocks", [])
        if len(recent_blocks) == 0:
            logger.warning(
                "No recent blocks. Using synthetic zero POOL node. "
                "Pool-based anomaly signals unavailable this cycle."
            )
            pool_tensor = torch.zeros((1, NODE_FEATURE_DIM), dtype=torch.float32)
        else:
            pool_stats = self._aggregate_pool_stats(recent_blocks)
            if len(pool_stats) == 1:
                logger.info(
                    "Single mining pool detected (%s). "
                    "Pool diversity signals unavailable. "
                    "Possible centralization event — flag for review.",
                    list(pool_stats.keys())[0],
                )
            pool_tensor = torch.tensor(
                self._build_pool_rows(pool_stats),
                dtype=torch.float32,
            )

        # ── NETWORK SINGLETON NODE ─────────────────────────────────────────────
        net_tensor = torch.tensor(
            [self._build_network_row(state.get("network", {}))],
            dtype=torch.float32,
        )

        # ── ASSEMBLE ──────────────────────────────────────────────────────────
        n_tx   = tx_tensor.size(0)
        n_fee  = fee_tensor.size(0)
        n_pool = pool_tensor.size(0)
        # n_net  = 1 always

        x = torch.cat([tx_tensor, fee_tensor, pool_tensor, net_tensor], dim=0)
        edge_index = self._build_edges(n_tx, n_fee, n_pool, whale_txs)

        # AUDIT FIX: [Q3-SYNTHESIS] Bounds validation — prevents silent
        # data corruption from edge_index referencing non-existent nodes
        if edge_index.size(1) > 0:
            max_idx = edge_index.max().item()
            if max_idx >= x.size(0):
                raise GraphConstructionError(
                    f"Edge index out of bounds: max_idx={max_idx}, "
                    f"num_nodes={x.size(0)}. Graph construction logic error."
                )

        return Data(
            x=x,
            edge_index=edge_index,
            num_nodes=x.size(0),
            # Metadata stored as graph-level attributes for quality gate
            snapshot_timestamp=torch.tensor([time.time()]),
            n_tx=torch.tensor([n_tx]),
            n_fee=torch.tensor([n_fee]),
            n_pool=torch.tensor([n_pool]),
            data_age_s=torch.tensor([data_age]),
        )

    def _build_fee_band_rows(self, fee_bands: dict) -> list:
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
                0.0, 0.0,  # reserved padding
            ])
        return rows

    def _build_network_row(self, network: dict) -> list:
        return [
            float(network.get("hashrate_th_s", 0.0)),
            float(network.get("difficulty", 0.0)),
            float(network.get("block_time_avg_s", 600.0)),
            float(network.get("mempool_size_mb", 0.0)),
            float(network.get("node_count", 0)),
            float(network.get("orphan_rate", 0.0)),
            0.0, 0.0,  # reserved padding
        ]

    def _aggregate_pool_stats(self, recent_blocks: list) -> dict:
        pool_stats = {}
        for block in recent_blocks[:100]:
            name = block.get("pool", "Unknown")
            if name not in pool_stats:
                pool_stats[name] = {
                    "count_10": 0, "count_100": 0,
                    "avg_fee": 0.0, "orphan": 0.0,
                }
            pool_stats[name]["count_100"] += 1
        return pool_stats

    def _build_pool_rows(self, pool_stats: dict) -> list:
        rows = []
        total = sum(s["count_100"] for s in pool_stats.values()) or 1
        for name, stats in pool_stats.items():
            hashrate_pct = stats["count_100"] / total
            rows.append([
                hashrate_pct,
                float(stats["count_10"]),
                float(stats["count_100"]),
                1.0 if name != "Unknown" else 0.0,
                stats["avg_fee"],
                stats["orphan"],
                0.0, 0.0,  # reserved padding
            ])
        return rows

    def _build_edges(
        self,
        n_tx: int,
        n_fee: int,
        n_pool: int,
        whale_txs: list,
    ) -> torch.Tensor:
        """
        Build edge_index for heterogeneous graph.

        Node index offsets:
          TX:   [0,          n_tx)
          FEE:  [n_tx,       n_tx + n_fee)
          POOL: [n_tx+n_fee, n_tx+n_fee+n_pool)
          NET:  [n_tx+n_fee+n_pool] (singleton)

        Edge types (bidirectional unless noted):
          1. TX → FEE_BAND  (fee_rate membership)
          2. TX → POOL      (block inclusion)
          3. FEE → NET      (all fee bands to global)
          4. POOL → NET     (all pools to global)
          5. TX → TX        (UTXO ancestry proxy via txid prefix)
          6. TX → TX        (temporal arrival order, max 50 edges)
               AUDIT FIX: [Q3] Added edge type 6 — temporal ordering.
               Audit identified this as highest-value missing feature.

        All edges are bidirectional (undirected graph for SAGEConv).
        """
        fee_offset  = n_tx
        pool_offset = n_tx + n_fee
        net_idx     = n_tx + n_fee + n_pool

        edges = []

        # Edge type 1: TX → FEE_BAND (dense: each TX connects to all bands)
        for i in range(n_tx):
            for j in range(n_fee):
                edges += [[i, fee_offset + j], [fee_offset + j, i]]

        # Edge type 3: FEE → NET
        for j in range(n_fee):
            edges += [[fee_offset + j, net_idx], [net_idx, fee_offset + j]]

        # Edge type 4: POOL → NET
        for k in range(n_pool):
            edges += [[pool_offset + k, net_idx], [net_idx, pool_offset + k]]

        # Edge type 5: TX → TX (UTXO ancestry proxy — txid prefix match)
        if n_tx > 1:
            txids = [tx.get("txid", "")[:8] for tx in whale_txs[:n_tx]]
            prefix_groups: dict = {}
            for i, prefix in enumerate(txids):
                if prefix not in prefix_groups:
                    prefix_groups[prefix] = []
                prefix_groups[prefix].append(i)
            for members in prefix_groups.values():
                if len(members) > 1:
                    for a in range(len(members)):
                        for b in range(a + 1, min(len(members), a + 6)):
                            edges += [
                                [members[a], members[b]],
                                [members[b], members[a]],
                            ]

        # Edge type 6: TX temporal ordering (arrival sequence)
        # AUDIT FIX: [Q3] New edge type — most valuable missing feature.
        # Captures mempool arrival sequence relationships.
        # Limit to 50 sequential edges to keep graph sparse.
        if n_tx > 1:
            sorted_txs = sorted(
                range(min(n_tx, len(whale_txs))),
                key=lambda i: whale_txs[i].get("age_seconds", 0),
                reverse=True,  # oldest first
            )
            max_temporal_edges = 50
            edge_count = 0
            for idx in range(len(sorted_txs) - 1):
                if edge_count >= max_temporal_edges:
                    break
                a, b = sorted_txs[idx], sorted_txs[idx + 1]
                edges += [[a, b], [b, a]]
                edge_count += 1

        if not edges:
            # Degenerate: self-loop on NET node prevents empty edge_index
            logger.warning("No edges constructed. Adding self-loop on NET node.")
            edges = [[net_idx, net_idx]]

        return torch.tensor(edges, dtype=torch.long).t().contiguous()

    def save_snapshot(self, data: Data) -> None:
        """Save PyG Data object as pkl. Filename encodes timestamp for ordering."""
        timestamp = int(time.time())
        filename = self.data_dir / f"{timestamp}.pkl"
        with open(filename, "wb") as f:
            pickle.dump(data, f)
        self._snapshot_count += 1

    def get_corpus_stats(self) -> dict:
        """Return count, total size, and age range of collected snapshots."""
        files = sorted(self.data_dir.glob("*.pkl"))
        if not files:
            return {"count": 0, "size_mb": 0.0, "oldest_ts": 0, "newest_ts": 0}
        total_bytes = sum(f.stat().st_size for f in files)
        # Timestamps encoded in filenames as unix epoch
        timestamps = []
        for f in files:
            try:
                timestamps.append(int(f.stem))
            except ValueError:
                pass
        return {
            "count": len(files),
            "size_mb": round(total_bytes / 1_048_576, 2),
            "oldest_ts": min(timestamps) if timestamps else 0,
            "newest_ts": max(timestamps) if timestamps else 0,
        }

    def run(self) -> None:
        """
        Main collection loop. Runs forever as daemon thread.

        AUDIT FIX: [Q3] Exceptions caught individually — not bare except.
        GraphConstructionError → skip cycle (expected, log INFO).
        json.JSONDecodeError → skip cycle (transient, log WARNING).
        FileNotFoundError → skip cycle (sentinel_state.json not written yet).
        All others → log ERROR with traceback, increment error count, continue.
        """
        logger.info("PCAF DataCollector: collection loop started.")
        while self._running:
            cycle_start = time.monotonic()
            try:
                if not SENTINEL_STATE_PATH.exists():
                    logger.debug("sentinel_state.json not yet written. Waiting.")
                    time.sleep(COLLECTION_INTERVAL_SECONDS)
                    continue

                with open(SENTINEL_STATE_PATH, "r") as f:
                    state = json.load(f)

                graph = self.build_graph(state)
                if graph is None:
                    self._skip_count += 1
                else:
                    self.save_snapshot(graph)
                    logger.debug(
                        "Snapshot saved. Total: %d nodes=%d edges=%d",
                        self._snapshot_count,
                        graph.num_nodes,
                        graph.edge_index.size(1),
                    )

            except GraphConstructionError as e:
                self._skip_count += 1
                logger.info("Graph construction skipped: %s", e)
            except json.JSONDecodeError as e:
                self._skip_count += 1
                logger.warning("sentinel_state.json malformed: %s", e)
            except FileNotFoundError:
                logger.debug("sentinel_state.json not found this cycle.")
            except Exception as e:
                self._error_count += 1
                logger.error(
                    "DataCollector unexpected error (count=%d): %s",
                    self._error_count, e, exc_info=True,
                )
                # AUDIT FIX: [Q10-FIRST-DEPLOY] Back off on repeated errors
                # to prevent tight error loops consuming CPU
                if self._error_count > 10:
                    time.sleep(min(self._error_count * 5, 300))

            # Sleep for remainder of interval
            elapsed = time.monotonic() - cycle_start
            sleep_time = max(0.0, COLLECTION_INTERVAL_SECONDS - elapsed)
            time.sleep(sleep_time)

        logger.info(
            "PCAF DataCollector stopped. Collected=%d Skipped=%d Errors=%d",
            self._snapshot_count, self._skip_count, self._error_count,
        )
```

---

## FILE 3: services/pcaf_trainer.py

```python
"""
PCAF v1 Training Pipeline.
Run manually or via scheduled tmux session. NOT imported at Sentinel boot.

AUDIT FIX: [Q4] Full 7-check training data quality gate runs before training.
  Training is blocked if any FAIL-severity check fails.
  Original spec had no quality gate.

AUDIT FIX: [Q5] AnomalyScoreCalibrator with offline + online layers.
  Original spec: single-pass static thresholds. Replaced with stratified
  temporal calibration to handle non-stationary Bitcoin mempool behavior.

AUDIT FIX: [Q5-SYNTHESIS] Self-suppression prevention: online threshold
  cannot exceed 3× offline anchor, preventing calibration drift during
  prolonged anomaly events.

AUDIT FIX: [Q10-FIRST-DEPLOY] Trainer checks for ≥500 snapshots before
  starting. Exits gracefully with clear instructions if insufficient data.
"""

import json
import logging
import os
import pickle
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch_geometric.data import Data, DataLoader

# AUDIT FIX: [Q1] importlib loading — NEVER `from services.pcaf_v1_model import`
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "pcaf_v1_model",
    Path(__file__).parent / "pcaf_v1_model.py",
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
ChainStateAutoencoder = _mod.ChainStateAutoencoder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pcaf_trainer")

DATA_DIR        = Path(__file__).parent.parent / "data" / "pcaf_training"
CHECKPOINT_DIR  = Path(__file__).parent.parent / "data"
MODEL_OUT       = CHECKPOINT_DIR / "pcaf_v1.pt"
THRESHOLDS_OUT  = CHECKPOINT_DIR / "pcaf_v1_thresholds.json"
METADATA_OUT    = CHECKPOINT_DIR / "pcaf_v1_metadata.json"


# ─────────────────────────────────────────────────────────────────────────────
# TRAINING DATA QUALITY GATE
# AUDIT FIX: [Q4] All 7 checks. FAIL blocks training. WARN logs but continues.
# ─────────────────────────────────────────────────────────────────────────────

def run_training_data_quality_gate(
    snapshots: list,
) -> tuple:
    """
    Run all quality checks on the training corpus.
    Returns (all_passed: bool, results: list[dict]).
    Training MUST NOT proceed if any result has severity='FAIL'.
    """
    results = []
    n = len(snapshots)

    def _check(name, passed, value, threshold, fail_sev, warn_sev, message):
        sev = "FAIL" if not passed and fail_sev else \
              "WARN" if not passed else "PASS"
        # Use fail_sev/warn_sev thresholds for graduated severity
        results.append({
            "check": name, "passed": passed,
            "value": value, "threshold": threshold,
            "severity": sev, "message": message,
        })

    # Check 1: Minimum count
    _check(
        "minimum_snapshot_count",
        n >= 500,
        float(n), 500.0,
        fail_sev=(n < 500),
        warn_sev=(n < 1000),
        message=f"{n} snapshots (min 500, recommended 1000+)",
    )

    # Check 2: Temporal coverage — hours of day
    timestamps = []
    for s in snapshots:
        ts_tensor = getattr(s, "snapshot_timestamp", None)
        if ts_tensor is not None:
            timestamps.append(float(ts_tensor[0]))
    hours_seen = set(
        datetime.fromtimestamp(ts, tz=timezone.utc).hour
        for ts in timestamps if ts > 0
    )
    _check(
        "temporal_coverage_hours",
        len(hours_seen) >= 20,
        float(len(hours_seen)), 20.0,
        fail_sev=(len(hours_seen) < 16),
        warn_sev=(len(hours_seen) < 20),
        message=f"Covers {len(hours_seen)}/24 hours of day",
    )

    # Check 3: Temporal coverage — days of week
    weekdays_seen = set(
        datetime.fromtimestamp(ts, tz=timezone.utc).weekday()
        for ts in timestamps if ts > 0
    )
    _check(
        "temporal_coverage_weekdays",
        len(weekdays_seen) == 7,
        float(len(weekdays_seen)), 7.0,
        fail_sev=(len(weekdays_seen) < 5),
        warn_sev=(len(weekdays_seen) < 7),
        message=f"Covers {len(weekdays_seen)}/7 days of week",
    )

    # Check 4: Graph size diversity (coefficient of variation)
    # AUDIT FIX: [Q4] Ensures training set includes both quiet and congestion states
    node_counts = [s.num_nodes for s in snapshots]
    if node_counts and max(node_counts) > 0:
        cv = float(np.std(node_counts) / (np.mean(node_counts) + 1e-8))
    else:
        cv = 0.0
    _check(
        "graph_size_diversity",
        cv >= 0.20,
        cv, 0.20,
        fail_sev=False,  # Warning only — training can proceed
        warn_sev=(cv < 0.20),
        message=f"Graph size CV={cv:.3f} (recommend ≥0.20 for regime diversity)",
    )

    # Check 5: Feature variance — detect static/degenerate features
    # AUDIT FIX: [Q4] Any feature with var<0.001 is effectively constant → data bug
    feature_variances = None
    low_var_features = []
    if n >= 10:
        try:
            all_x = torch.cat([s.x for s in snapshots[:500]], dim=0).numpy()
            feature_variances = np.var(all_x, axis=0)
            low_var_features = [
                f"feature_{i}" for i, v in enumerate(feature_variances)
                if v < 0.001
            ]
        except Exception as e:
            logger.warning("Feature variance check failed: %s", e)
    _check(
        "feature_variance_floor",
        len(low_var_features) == 0,
        float(len(low_var_features)), 0.0,
        fail_sev=(len(low_var_features) > 2),
        warn_sev=(len(low_var_features) > 0),
        message=(
            f"Low-variance features: {low_var_features}" if low_var_features
            else "All features have sufficient variance"
        ),
    )

    # Check 6: Snapshot freshness
    now = time.time()
    stale = sum(1 for ts in timestamps if ts > 0 and (now - ts) > 30 * 86400)
    future = sum(1 for ts in timestamps if ts > now + 3600)
    stale_pct = stale / n if n > 0 else 0.0
    _check(
        "snapshot_freshness",
        stale_pct < 0.05 and future == 0,
        stale_pct, 0.05,
        fail_sev=(future > 0),
        warn_sev=(stale_pct >= 0.05),
        message=f"{stale} stale (>{stale_pct:.1%}), {future} future timestamps",
    )

    # Check 7: Minimum useful corpus (24h equivalent)
    # AUDIT FIX: [Q10-FIRST-DEPLOY] Gate for first-deploy scenario
    _check(
        "minimum_24h_coverage",
        n >= 1440,
        float(n), 1440.0,
        fail_sev=False,  # WARN only — 500 snapshots allows bootstrap training
        warn_sev=(n < 1440),
        message=(
            f"{n} snapshots. <1440 = bootstrap model only. "
            "Retrain after 7 days for production quality."
        ),
    )

    all_passed = all(r["severity"] != "FAIL" for r in results)
    return all_passed, results


# ─────────────────────────────────────────────────────────────────────────────
# ANOMALY SCORE CALIBRATOR
# AUDIT FIX: [Q5] Two-layer calibration: offline (stratified) + online (rolling)
# AUDIT FIX: [Q5-SYNTHESIS] Self-suppression prevention via anchor ceiling
# ─────────────────────────────────────────────────────────────────────────────

class AnomalyScoreCalibrator:
    """
    Offline calibration: stratified temporal percentiles on validation set.
    Online adaptation: rolling window that cannot drift >3× from offline anchor.
    """

    COLD_START_P95 = 0.15
    COLD_START_P99 = 0.35

    def __init__(self):
        self._offline_p95: float = self.COLD_START_P95
        self._offline_p99: float = self.COLD_START_P99
        self._online_p95: float  = self.COLD_START_P95
        self._online_p99: float  = self.COLD_START_P99
        self._calibrated: bool   = False
        self._online_buffer: list = []
        self._online_buffer_max: int = 1440  # 24h of 1-min cycles

    def calibrate_offline(self, val_mse_records: list) -> dict:
        """
        Stratified temporal calibration on validation MSE records.

        Args:
            val_mse_records: list of {"mse": float, "timestamp": float}

        AUDIT FIX: [Q5] Uses max(global, stratum-specific) thresholds to
        prevent a quiet stratum from setting a threshold that fires constantly
        during active periods (the non-stationarity problem).
        """
        if len(val_mse_records) < 50:
            logger.warning(
                "Only %d validation records. Calibration unreliable. "
                "Using cold-start defaults.", len(val_mse_records)
            )
            return self.thresholds

        mse_vals = np.array([r["mse"] for r in val_mse_records])

        # Stratify by hour-of-day quartiles
        strata = {"night": [], "morning": [], "afternoon": [], "evening": []}
        for r in val_mse_records:
            h = datetime.fromtimestamp(r["timestamp"], tz=timezone.utc).hour
            key = "night" if h < 6 else "morning" if h < 12 \
                  else "afternoon" if h < 18 else "evening"
            strata[key].append(r["mse"])

        for stratum, values in strata.items():
            if len(values) < 50:
                logger.warning(
                    "Stratum '%s' has %d samples. Threshold for this "
                    "period may be unreliable.", stratum, len(values)
                )

        global_p95 = float(np.percentile(mse_vals, 95))
        global_p99 = float(np.percentile(mse_vals, 99))

        # AUDIT FIX: [Q5] Take max of global vs stratum-specific percentiles
        stratum_p95_vals = [
            float(np.percentile(v, 95))
            for v in strata.values() if len(v) >= 10
        ]
        stratum_p99_vals = [
            float(np.percentile(v, 99))
            for v in strata.values() if len(v) >= 10
        ]

        self._offline_p95 = max(
            global_p95,
            max(stratum_p95_vals, default=global_p95) * 0.8,
        )
        self._offline_p99 = max(
            global_p99,
            max(stratum_p99_vals, default=global_p99) * 0.8,
        )
        self._online_p95 = self._offline_p95
        self._online_p99 = self._offline_p99
        self._calibrated = True

        logger.info(
            "Calibration complete. p95=%.6f p99=%.6f (n=%d)",
            self._offline_p95, self._offline_p99, len(mse_vals),
        )
        return self.thresholds

    def update_online(self, mse: float) -> None:
        """
        Rolling window update. Called once per inference cycle.

        AUDIT FIX: [Q5-SYNTHESIS] Anchor constraint: online threshold
        cannot exceed 3× offline anchor. Prevents self-suppression during
        prolonged anomaly events (e.g. 6-hour fee spike that would otherwise
        cause the system to normalize anomalous MSE as baseline).
        """
        self._online_buffer.append(mse)
        if len(self._online_buffer) > self._online_buffer_max:
            self._online_buffer.pop(0)

        if len(self._online_buffer) >= 60:
            recent = np.array(self._online_buffer)
            rolling_p95 = float(np.percentile(recent, 95))
            rolling_p99 = float(np.percentile(recent, 99))

            # Anchor ceiling — never drift more than 3× from offline calibration
            self._online_p95 = min(rolling_p95, self._offline_p95 * 3.0)
            self._online_p99 = min(rolling_p99, self._offline_p99 * 3.0)

    @property
    def thresholds(self) -> dict:
        return {
            "p95": self._online_p95,
            "p99": self._online_p99,
            "offline_p95": self._offline_p95,
            "offline_p99": self._offline_p99,
            "source": "calibrated" if self._calibrated else "cold_start_default",
            "calibrated_at": datetime.now(timezone.utc).isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# CORPUS LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_corpus(data_dir: Path = DATA_DIR) -> list:
    """Load all .pkl snapshots. Sort chronologically by filename timestamp."""
    files = sorted(data_dir.glob("*.pkl"))
    if not files:
        logger.error("No training snapshots found at %s", data_dir)
        return []

    corpus = []
    errors = 0
    for f in files:
        try:
            with open(f, "rb") as fh:
                data = pickle.load(fh)
            if isinstance(data, Data) and data.x is not None and data.x.size(0) > 0:
                corpus.append(data)
            else:
                logger.debug("Skipping malformed snapshot: %s", f.name)
        except Exception as e:
            errors += 1
            logger.warning("Failed to load %s: %s", f.name, e)

    logger.info(
        "Loaded %d snapshots (%d errors) from %s",
        len(corpus), errors, data_dir,
    )
    return corpus


# ─────────────────────────────────────────────────────────────────────────────
# MODEL TRAINING
# ─────────────────────────────────────────────────────────────────────────────

def train_model(
    corpus: list,
    device: str = "cuda:1",
) -> tuple:
    """
    Train ChainStateAutoencoder on corpus.

    AUDIT FIX: [Q4] Chronological split enforced — no random shuffle.
    Random splitting leaks temporal information: a model trained on
    data from hour N+1 and tested on hour N has seen the future.

    Returns (model, calibrator).
    """
    # Chronological split
    n = len(corpus)
    n_train = int(n * 0.80)
    n_val   = int(n * 0.10)
    train_corpus = corpus[:n_train]
    val_corpus   = corpus[n_train:n_train + n_val]
    test_corpus  = corpus[n_train + n_val:]

    logger.info(
        "Split: train=%d val=%d test=%d (chronological)",
        len(train_corpus), len(val_corpus), len(test_corpus),
    )

    # AUDIT FIX: [Q10-FIRST-DEPLOY] Verify device availability before training
    if device.startswith("cuda"):
        if not torch.cuda.is_available():
            logger.warning("CUDA not available. Falling back to CPU.")
            device = "cpu"
        else:
            device_idx = int(device.split(":")[-1]) if ":" in device else 0
            if device_idx >= torch.cuda.device_count():
                logger.warning(
                    "GPU %d not available (%d GPUs found). Using cuda:0.",
                    device_idx, torch.cuda.device_count(),
                )
                device = "cuda:0"

    dev = torch.device(device)
    logger.info("Training on device: %s", dev)

    model = ChainStateAutoencoder().to(dev)
    optimizer = AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=50, eta_min=1e-5)

    train_loader = DataLoader(train_corpus, batch_size=32, shuffle=True)
    val_loader   = DataLoader(val_corpus,