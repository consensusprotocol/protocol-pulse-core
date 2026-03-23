# PCAF V1 — PREDICTIVE CHAIN-STATE ANOMALY FORECASTING
# Foundation Document · Protocol Pulse Intelligence Terminal
# ML Session — GNN-based anomaly detection
# Created: 2026-03-23

---

## WHAT WE'RE BUILDING

PCAF v0 is deterministic rules — it detects anomalies that already match known
patterns. PCAF v1 is a Graph Neural Network that learns the normal structure of
Bitcoin's chain-state and flags deviations before they become detectable by rules.

The difference: PCAF v0 says "hashrate dropped 20% — that's a known bad pattern."
PCAF v1 says "the mempool graph topology looks like it did 47 minutes before the
last 3 fee spikes — probability 73% of congestion in the next 90 minutes."

This is the feature that makes Protocol Pulse a prediction engine, not a detection
engine.

---

## ML ARCHITECTURE DECISION

### Why GNN (not LSTM, not CNN, not Transformer)

Bitcoin's chain-state is fundamentally a GRAPH:
- Nodes: unconfirmed transactions, UTXOs, mining pool identifiers, fee bands
- Edges: transaction ancestry (inputs → outputs), fee relationships,
  temporal ordering (mempool arrival sequence)
- The interesting signal is in the TOPOLOGY, not just the time series

A time-series model (LSTM) would treat fee rates as a sequence and miss that
a specific cluster of large transactions is creating unusual UTXO pressure.
A GNN sees the full structural picture.

### Specific Architecture: GNN Autoencoder (Unsupervised)

**Why unsupervised:** We have no labeled "this was an anomaly" dataset.
PCAF v0 has been running but its labels are based on the same rules we're
trying to transcend. We need to learn what "normal" looks like and flag
deviations — this is exactly what autoencoder anomaly detection does.

**Architecture:**
```
Input Graph (chain-state snapshot)
    ↓
GNN Encoder (3-layer GraphSAGE)
    → Node embeddings: 256-dim
    → Graph-level embedding: 128-dim (global mean pooling)
    ↓
Bottleneck (32-dim latent)
    ↓
GNN Decoder (3-layer GraphSAGE)
    → Reconstructed node features
    ↓
Reconstruction Error → Anomaly Score
```

High reconstruction error = the current chain-state is unusual = potential anomaly.

**Why GraphSAGE over GCN or GAT:**
- GraphSAGE handles inductive learning (new nodes not seen in training)
- Bitcoin's mempool constantly has new transaction nodes — transductive methods fail
- GraphSAGE's neighborhood sampling is efficient enough for real-time inference

---

## GRAPH CONSTRUCTION

### What One "Graph Snapshot" Looks Like

Every 60 seconds, build a graph from current SentinelState:

**Nodes (feature vectors):**

1. MEMPOOL_TX nodes (one per whale tx >10 BTC, max 200 nodes):
   Features: [value_btc, fee_rate_svb, size_vbytes, rbf_flag, age_seconds,
              is_replacement, output_count, input_count]
   → 8-dimensional node feature

2. FEE_BAND nodes (10 nodes, one per fee band from histogram):
   Features: [min_fee, max_fee, tx_count, vsize_total, pct_of_mempool]
   → 5-dimensional node feature (pad to 8 with zeros)

3. POOL nodes (one per mining pool seen in last 10 blocks):
   Features: [hashrate_pct, blocks_last_10, blocks_last_100, known_pool_flag,
              avg_fee_earned, orphan_rate_proxy]
   → 6-dimensional node feature (pad to 8)

4. NETWORK node (1 node — global network state):
   Features: [hashrate_3d_eh, difficulty_adj_pct, avg_block_time,
              mempool_count, mempool_vsize, next_block_fee]
   → 6-dimensional (pad to 8)

**Edges:**

1. TX → FEE_BAND: if tx.fee_rate falls in fee_band range (weight: 1.0)
2. TX → POOL: if tx was in last block mined by this pool (weight: 0.8)
3. FEE_BAND → NETWORK: all fee bands connect to global node (weight: 0.5)
4. POOL → NETWORK: all pools connect to global node (weight: pool.hashrate_pct)
5. TX → TX: if they share a UTXO ancestor (weight: 0.9, max 50 edges)
   (Use bloom filter approximation from txid prefix matching — exact UTXO
   ancestry too expensive, prefix match captures ~70% of real relationships)

**Result:** Graph with ~220 nodes, ~600 edges. Sparse. Efficient.

---

## TRAINING PIPELINE

### Phase 1: Data Collection (Run First — 7 Days Minimum)

The sentinel already writes state to /tmp/sentinel_state.json every 5s.
We need a collector that snapshots this into a training corpus.

**Collector:** services/pcaf_data_collector.py
- Runs alongside sentinel
- Every 60 seconds: reads current SentinelState, builds graph, saves to:
  ~/protocol_pulse/data/pcaf_training/YYYYMMDD_HHMMSS.pkl
- Each .pkl: serialized PyTorch Geometric Data object
- Target: 10,080 snapshots (7 days × 24h × 60min)
- Storage estimate: ~2KB per snapshot × 10,080 = ~20MB total

**Bootstrap strategy for immediate training:**
Don't wait 7 days. Use 24 hours of collected data to train a first model,
then retrain weekly as more data accumulates. A model trained on 24h of data
will catch gross anomalies. A model trained on 30 days catches subtle ones.

### Phase 2: Model Training

**Training script:** services/pcaf_trainer.py
- Loads all .pkl files from data/pcaf_training/
- Splits: 80% train, 10% val, 10% test (chronological split, not random)
- Loss: Mean Squared Error of node feature reconstruction
- Optimizer: AdamW, lr=1e-3, weight_decay=1e-4
- Scheduler: CosineAnnealingLR
- Batch size: 32 graphs
- Epochs: 50 (early stopping on val loss)
- GPU: CUDA device 0 (RTX 4090, dedicated to PCAF)

**Training time estimate:**
- 10,080 samples, batch 32 = 315 batches/epoch
- ~0.5s/batch on RTX 4090 = ~2.5min/epoch
- 50 epochs = ~2 hours total
- Can run overnight while sentinel serves v0

### Phase 3: Anomaly Score Calibration

After training, establish the "normal" reconstruction error distribution:
- Run model on validation set (10% of training data = "normal" samples)
- Compute percentile distribution of reconstruction errors
- Set thresholds:
  - NOTE: error > 70th percentile
  - WATCH: error > 90th percentile
  - CRITICAL: error > 99th percentile
- Save thresholds to: data/pcaf_v1_thresholds.json

---

## INFERENCE PIPELINE (Real-Time)

**Inference flow (every 60s, replaces PCAF v0 eval):**

1. Read SentinelState → build graph (< 10ms)
2. Load model from disk (cached in memory after first load)
3. Forward pass: graph → reconstruction error (< 50ms on GPU)
4. Compare to thresholds → anomaly score 0-100
5. If score > threshold: fire alert via existing AlertDispatcher

**GPU allocation:** CUDA device 0 during inference (shared with other tasks).
Model is small (~2MB) — stays in VRAM permanently after first load.

**TorchScript export:** After training, export model to TorchScript for:
- Faster inference (no Python overhead)
- No need to load full PyTorch training stack at runtime
- Export: torch.jit.script(model).save('data/pcaf_v1.pt')

**Fallback:** If inference fails (GPU OOM, model file missing), automatically
fall back to PCAF v0 rule-based scoring. Never go dark.

---

## MODEL VERSIONING

data/
  pcaf_v1.pt               — current production TorchScript model
  pcaf_v1_thresholds.json  — current calibrated thresholds
  pcaf_v1_metadata.json    — training date, dataset size, val loss, architecture
  pcaf_v1_prev.pt          — previous model (rollback if needed)
  pcaf_training/           — raw training snapshots (rolling 90-day retention)

**Retraining schedule:** Weekly, Sunday 04:00 UTC (maintenance window).
If new model val_loss < current model val_loss × 1.05: deploy.
Otherwise: keep current model, log regression warning.

---

## INTEGRATION WITH SENTINELSTATE

**Schema (backward compatible with v0):**

```python
pcaf_v1: dict = field(default_factory=lambda: {
    # Same fields as pcaf_v0 (drop-in replacement in SSE stream)
    "anomaly_score": 0,          # 0-100, replaces v0 score
    "confidence_pct": 0,         # model confidence (reconstruction error percentile)
    "top_signal": "",            # which node cluster drove the score
    "active_rules": [],          # v1: most anomalous node type names
    # New v1 fields
    "model_version": "v1",       # "v0" if fallback active
    "reconstruction_error": 0.0, # raw MSE for debugging
    "graph_nodes": 0,            # size of input graph
    "graph_edges": 0,
    "inference_ms": 0,           # inference latency
    "training_date": "",         # when model was last trained
    "updated_at": 0.0,
})
```

Frontend: zero changes needed. The anomaly bar, PCAF score display, and
alert thresholds all work with the new v1 schema.

---

## FILES TO CREATE / MODIFY

NEW:
  services/pcaf_data_collector.py  — snapshot collector (runs alongside sentinel)
  services/pcaf_trainer.py          — training pipeline (run manually / scheduled)
  services/pcaf_v1_engine.py        — inference engine (load model + score)
  services/pcaf_v1_model.py         — GNN autoencoder architecture definition
  data/pcaf_v1_thresholds.json      — calibrated thresholds (created by trainer)
  data/pcaf_training/               — directory for training snapshots

MODIFY:
  services/sentinel.py
    - Add pcaf_v1 field to SentinelState
    - Load PCAFv1Engine via importlib.util
    - In _update_pcaf(): try v1 inference first, fall back to v0
    - Start data collector thread at boot (alongside sentinel)

  core/templates/intelligence_terminal.html
    - SENTINEL CORE panel: show "v1" badge when v1 model active
    - Add inference_ms display (shows model is actually running)
    - Add training_date display

---

## DEPENDENCIES TO INSTALL

pip install torch-geometric --break-system-packages
# torch-geometric requires torch scatter and sparse:
pip install pyg-lib torch-scatter torch-sparse -f \
  https://data.pyg.org/whl/torch-2.6.0+cu124.html \
  --break-system-packages

Verify: python3 -c "import torch_geometric; print(torch_geometric.__version__)"

---

## SUCCESS CRITERIA

1. Data collector runs for 24h, produces ≥ 1,440 training snapshots
2. Model trains to convergence (val loss plateau) in < 4 hours on RTX 4090
3. Inference latency < 100ms per graph on CUDA
4. Anomaly score on normal state: 0-30 (below NOTE threshold)
5. Anomaly score during simulated hashrate shock: > 70 (WATCH threshold)
6. v1 fires on existing PCAF v0 test cases (regression: all 5 original tests pass)
7. Fallback to v0 works when model file is deleted
8. TorchScript export successful, inference from .pt file matches Python model

