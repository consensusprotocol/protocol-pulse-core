Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/intelligence_terminal_v1_spec.md (sections 3 and 8 only).
Read ~/protocol_pulse/docs/phase_ml/pcaf_v1_foundation.md.
Read ~/protocol_pulse/docs/phase_ml/tpa_foundation.md.
Read ~/protocol_pulse/services/sentinel.py (imports + SentinelState + _update_pcaf lines only).
Read ~/protocol_pulse/services/pcaf_v1_PENDING.md.
Read ~/protocol_pulse/services/tpa_PENDING.md.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ML SESSION — PCAF V1 GNN + TEMPORAL PREDICTIVE ANALYTICS
Protocol Pulse Intelligence Terminal · The Unprecedented Features
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ENVIRONMENT:
  PyTorch 2.6.0 + CUDA 12.4: INSTALLED ✅
  torch_geometric: NOT INSTALLED — install first
  numpy 1.25.2, scipy 1.13.1: INSTALLED ✅
  GPU 0: RTX 4090 24GB (some VRAM used by other tasks)
  GPU 1: RTX 4090 24GB (~22GB free)

INVIOLABLE RULES:
1. NEVER `from services.X import Y` — always importlib.util path loading
2. GUNICORN must start from ~/protocol_pulse/core/
3. PCAF v1 must fall back to PCAF v0 if model file missing or GPU error
4. TPA runs on CPU only (no GPU needed — Monte Carlo is fast on CPU)
5. Both features write to QWEN_CONTEXT_BIBLE.md for every bug found
6. Commit after each major milestone, not just at the end

WRITE PROGRESS LOG: ~/protocol_pulse/logs/ml_session.log

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 0 — INSTALL torch_geometric
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pip install torch_geometric --break-system-packages

Then install required extras (try each, skip if fails):
pip install pyg_lib torch_scatter torch_sparse \
  -f https://data.pyg.org/whl/torch-2.6.0+cu124.html \
  --break-system-packages

Verify: python3 -c "import torch_geometric; print('pyg:', torch_geometric.__version__)"

If pyg_lib/scatter/sparse fail (they often do on non-standard builds):
torch_geometric works without them for our architecture.
Just confirm: python3 -c "from torch_geometric.nn import SAGEConv; print('SAGEConv OK')"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CROSS-LLM AUDIT (PCAF v1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Write: utils/pcaf_v1_audit.py
Run: python3 utils/pcaf_v1_audit.py
Save results: docs/audits/pcaf_v1_audit_2026-03-23.md

BRIEF to GPT-4o + Grok (parallel, 1 cycle):

---PCAF V1 AUDIT BRIEF---
You are auditing the PCAF v1 GNN anomaly detection system before implementation.
Read the foundation doc carefully. Answer 5 questions as a senior ML engineer.

Foundation doc: [PASTE full contents of docs/phase_ml/pcaf_v1_foundation.md]

Q1 — ARCHITECTURE VALIDATION:
GraphSAGE autoencoder for unsupervised anomaly detection in Bitcoin mempool graphs.
Is this the right architecture? What are the top 2 failure modes that will cause
the model to produce useless anomaly scores in production? Give specific fixes.

Q2 — DATA QUALITY RISK:
The training corpus is built from SentinelState snapshots (mempool + pool data).
What data quality issues will corrupt the training set and how do we detect them?
Specifically: what happens when mempool.space API returns stale data or the
WebSocket drops? How does this manifest in training data and model behavior?

Q3 — COLD START PROBLEM:
The model needs 24h of data before first training. During that period, PCAF v0
runs. What specific data quality checks should gate the switch from v0 to v1?
Minimum: what must be true about the training corpus before v1 is deployed?

Q4 — GRAPH CONSTRUCTION CORRECTNESS:
Review the graph construction spec (nodes: TX, FEE_BAND, POOL, NETWORK; edges as
described). What is the single most important graph feature that is missing from
this specification that would significantly improve anomaly detection accuracy?

Q5 — INFERENCE LATENCY:
The spec claims <50ms inference on GPU for a graph of ~220 nodes and ~600 edges.
Verify this estimate. What are the actual bottlenecks (data prep, forward pass,
threshold lookup) and what is the realistic p99 latency in production?
---END PCAF BRIEF---

Synthesize into: docs/audits/pcaf_v1_audit_2026-03-23.md
Key outputs needed:
  - Confirmed architecture (GraphSAGE autoencoder or recommended alternative)
  - Data quality gate thresholds (what must be true before v1 deploys)
  - Any missing graph features to add
  - Confirmed latency estimate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — CROSS-LLM AUDIT (TPA)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Write: utils/tpa_audit.py
Run: python3 utils/tpa_audit.py
Save results: docs/audits/tpa_audit_2026-03-23.md

BRIEF to GPT-4o + Grok:

---TPA AUDIT BRIEF---
You are auditing the Temporal Predictive Analytics scenario simulation engine.
Read the foundation doc. Answer 5 questions.

Foundation doc: [PASTE full contents of docs/phase_ml/tpa_foundation.md]

Q1 — SCENARIO DESIGN:
Review the 5 named scenarios and their precursor signals. Which scenario has the
weakest signal-to-noise ratio (most likely to fire incorrectly)? Which has the
strongest? Redesign the weakest scenario's signal set to be more reliable.

Q2 — PROBABILITY CALIBRATION:
The base probabilities (28%, 18%, 4%, 32%, 18%) were described as "calibrated
against historical cycles." What is the most rigorous defensible methodology
for setting these priors given only 4-5 historical Bitcoin cycles? Be specific
about the statistical approach.

Q3 — MONTE CARLO CORRECTNESS:
Review the Monte Carlo process. The spec says 10,000 iterations with ±20%
signal jitter to produce confidence intervals. Is ±20% the right jitter amount?
What distribution should the jitter follow (uniform? normal? beta?)?
Write the exact numpy code for the correct simulation.

Q4 — CONTRADICTION MATRIX:
The spec says S1 and S2 are negatively correlated (institutional adoption vs
regulatory crackdown). Design the complete contradiction matrix for all 5
scenarios. Which pair has the strongest inverse correlation? Which scenarios
can actually coexist?

Q5 — VIRAL SHAREABILITY:
The spec says "the share URL is the thing that gets posted to X and goes viral."
Design the exact share mechanism: what data is in the URL, what does the landing
page look like for someone who clicks a shared scenario link, and what is the
one visual element that makes people screenshot it?
---END TPA BRIEF---

Synthesize into: docs/audits/tpa_audit_2026-03-23.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — BUILD PCAF V1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Apply audit findings, then implement in this order:

FILE 1: services/pcaf_v1_model.py
  GNN Autoencoder architecture.
  class ChainStateEncoder(torch.nn.Module):
    - 3-layer SAGEConv encoder
    - Input: node features dim 8, hidden 64→128→256
    - Global mean pooling → 128-dim graph embedding
    - Linear bottleneck → 32-dim latent
  class ChainStateDecoder(torch.nn.Module):
    - Mirror of encoder: 32→256→128→64→8
    - Output: reconstructed node features
  class ChainStateAutoencoder(torch.nn.Module):
    - Combines encoder + decoder
    - forward() returns (reconstructed_features, latent)
    - anomaly_score() returns float 0-100 based on MSE vs threshold
  All modules use ReLU activation, no BatchNorm (small graphs)
  TorchScript compatible: no Python-only constructs in forward()

FILE 2: services/pcaf_data_collector.py
  Runs as background thread started at sentinel boot.
  Every 60s: reads /tmp/sentinel_state.json → builds PyG Data object → saves pkl.
  class DataCollector:
    def build_graph(self, state: dict) -> Data  # torch_geometric.data.Data
    def save_snapshot(self, data: Data) -> None  # saves to data/pcaf_training/
    def get_corpus_stats(self) -> dict  # count, size, age range
    def run(self) -> None  # main loop, catches all exceptions
  Graph construction: EXACTLY as specified in foundation doc.
  All node types padded to 8 features. All edge types included.
  Handle missing data gracefully: if whale_txs empty → TX nodes = empty tensor.

FILE 3: services/pcaf_trainer.py
  Training script (run manually, not at boot).
  def load_corpus(data_dir) → list[Data]
  def train_model(corpus, device='cuda:1') → ChainStateAutoencoder
    - Use GPU 1 (device index 1) — dedicated for training
    - Log training progress every 10 epochs
    - Save checkpoint every 20 epochs to data/pcaf_v1_checkpoint.pt
    - Early stopping: patience=10, monitor val_loss
  def calibrate_thresholds(model, val_corpus) → dict
    - Run model on validation set
    - Compute percentile distribution
    - Return {note_threshold, watch_threshold, critical_threshold}
  def export_model(model, output_path='data/pcaf_v1.pt') → None
    - Export as TorchScript
    - Verify: reload and run one forward pass
  def run_training_pipeline() → None
    - Full pipeline: load → split → train → calibrate → export → save thresholds

FILE 4: services/pcaf_v1_engine.py
  Real-time inference engine.
  Load via importlib.util — never `from services.pcaf_v1_engine import ...`

  class PCAFv1Engine:
    def __init__(self):
      self.model = None  # loaded lazily on first inference
      self.thresholds = None
      self.device = 'cuda:1' if available else 'cpu'
      self._model_path = Path(__file__).parent.parent / 'data' / 'pcaf_v1.pt'
      self._threshold_path = Path(__file__).parent.parent / 'data' / 'pcaf_v1_thresholds.json'

    def is_ready(self) -> bool
      # True if model file + threshold file both exist

    def load(self) -> None
      # Loads TorchScript model + thresholds. Logs model metadata.

    def score(self, state: dict) -> dict
      # Main interface. Returns pcaf_v1 state dict (same schema as pcaf_v0).
      # If not ready or inference fails: returns v0 fallback with model_version="v0_fallback"
      # Builds graph from state → forward pass → anomaly score → tier

    def _build_graph(self, state: dict) -> Data  # same logic as DataCollector
    def _to_anomaly_score(self, mse: float) -> int  # 0-100 based on thresholds

FILE 5: Modify services/sentinel.py
  Load PCAFv1Engine via importlib.util (add to existing _load_svc pattern).
  Add pcaf_v1 field to SentinelState (schema from foundation doc).
  Add DataCollector startup in __init__: start as daemon thread.
  In _update_pcaf(): try v1 first, fall back to v0.
    if self._pcaf_v1_engine.is_ready():
        result = self._pcaf_v1_engine.score(self.state.to_dict())
        self.state.pcaf_v1 = result
    else:
        # keep running v0, v1 not yet trained
        pass
  Note: do NOT replace pcaf_v0 — run both in parallel during transition.
  pcaf_v1 in SSE stream shows "model_version": "v0_fallback" until trained.

TESTS FOR PCAF V1:
  T1: pip install succeeded, SAGEConv importable
  T2: Model instantiates, forward pass on random data succeeds
      python3 -c "
      from torch_geometric.data import Data
      import torch, importlib.util
      from pathlib import Path
      spec = importlib.util.spec_from_file_location('m',
          str(Path('services/pcaf_v1_model.py')))
      mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
      model = mod.ChainStateAutoencoder()
      # fake graph: 10 nodes, 8 features, 15 edges
      x = torch.randn(10, 8)
      ei = torch.randint(0, 10, (2, 15))
      data = Data(x=x, edge_index=ei)
      out, latent = model(data.x, data.edge_index)
      assert out.shape == x.shape, f'Bad output shape: {out.shape}'
      print('T2 PASS: model forward pass correct shape')
      "
  T3: DataCollector builds valid graph from live sentinel state
  T4: Collector writes pkl files to data/pcaf_training/
  T5: No `from services.` imports in any pcaf_v1_*.py file
  T6: PCAFv1Engine.is_ready() returns False when model file absent
  T7: PCAFv1Engine.score() returns v0_fallback when is_ready() is False
  T8: sentinel.py imports clean from core/

COMMIT after T1-T8 pass:
  git add services/pcaf_v1_model.py services/pcaf_data_collector.py
  git add services/pcaf_trainer.py services/pcaf_v1_engine.py
  git add services/sentinel.py docs/audits/pcaf_v1_audit_2026-03-23.md
  git add docs/phase_ml/pcaf_v1_foundation.md utils/pcaf_v1_audit.py
  git commit -m "feat(pcaf-v1): GNN autoencoder + data collector + trainer + inference engine · v0 fallback"
  git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — BUILD TPA (Temporal Predictive Analytics)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Apply audit findings, then implement:

FILE 1: data/tpa_scenarios.json
  Complete scenario definitions for all 5 scenarios as specified in foundation doc.
  Each scenario: id, name, description, base_probability, signals list,
  contradiction_partners list.
  All 27 precursor signals defined with: signal_id, description,
  sentinel_state_path (dot-notation), threshold, probability_delta,
  decay_days (default 30).

FILE 2: data/tpa_scenario_correlations.json
  Complete contradiction matrix from audit Q4 findings.

FILE 3: data/tpa_calibration.json
  Run calibration against CoinGecko 4-year price history.
  Fetch: GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1460
  Map historical periods to scenario outcomes.
  Output: base_probabilities for each scenario with confidence intervals.
  Store results here. If CoinGecko rate-limits, use reasonable priors from
  foundation doc as fallback and mark calibration_method: "prior_only".

FILE 4: services/tpa_engine.py
  Load via importlib.util. CPU only.

  class TPAEngine:
    def __init__(self):
      self.scenarios = []  # loaded from tpa_scenarios.json
      self.correlations = {}
      self.calibration = {}
      self._last_evaluation = 0.0
      self._load_config()

    def _load_config(self) -> None
      # Load scenarios, correlations, calibration from data/
      # Validate: all required fields present, probabilities sum to 100

    def check_signal(self, signal: dict, state: dict) -> tuple[bool, float]
      # Returns (confirmed, strength 0-1)
      # Navigates state dict using signal.sentinel_state_path (dot notation)
      # Applies threshold comparison, returns strength as ratio

    def evaluate_scenarios(self, state: dict) -> list[dict]
      # Main evaluation. Returns updated scenario list.
      # For each scenario: apply signal checks → update probability
      # Apply contradiction matrix → normalize → Monte Carlo CI

    def run_monte_carlo(self, base_probs: dict, n_iter=10000) -> dict
      # Returns {scenario_id: {p10, p50, p90}} confidence intervals
      # Jitter: Normal distribution, sigma = 0.15 * signal_strength
      # Per audit Q3 recommendation

    def run_cycle(self, state: dict) -> dict
      # Called every 6h from sentinel. Returns full tpa state dict.
      # Checks data quality before running.

    def get_share_snapshot(self, scenario_id: str) -> dict
      # Returns shareable snapshot: scenario probs + top confirmed signals
      # Designed for URL encoding

FILE 5: core/templates/scenarios.html
  Dedicated page at /intelligence/scenarios.
  War room aesthetic — same CSS as intelligence_terminal.html.
  5 scenario cards as designed in foundation doc.
  Each card: scenario name, probability bar, trend arrow, confirmed signals.
  Click to expand: full signal list with confirmation status.
  Share button: generates /intelligence/scenarios/snapshot/<hash> URL.
  Update: SSE connection to /api/intelligence/tpa/stream (2s refresh on
  probability changes — only pushes if probability changed by >0.5%).
  "TRACK THIS SCENARIO" button: calls POST /api/intelligence/tpa/track.

FILE 6: core/templates/scenario_snapshot.html
  Public-facing page for shared scenario URLs.
  No auth required. Shows single scenario with current probabilities.
  Branded. Clean. The thing that spreads.

FILE 7: Modify services/sentinel.py
  Add tpa field to SentinelState (schema from foundation doc).
  Load TPAEngine via importlib.util.
  Run TPA every 6 hours (poll_counter % 4320 == 0).

FILE 8: Modify core/blueprints/intelligence.py
  GET  /intelligence/scenarios → scenarios.html
  GET  /api/intelligence/tpa → full tpa state JSON (auth gated)
  GET  /api/intelligence/tpa/stream → SSE with tpa state (2s, auth gated)
  POST /api/intelligence/tpa/track → store scenario tracking preference
  GET  /intelligence/scenarios/snapshot/<snapshot_id> → scenario_snapshot.html (public)
  POST /api/intelligence/tpa/snapshot → generate shareable snapshot, return URL

TESTS FOR TPA:
  T1: tpa_scenarios.json loads, all 5 scenarios present, all signals defined
  T2: TPAEngine.check_signal() returns correct (bool, float) for mock state
  T3: Monte Carlo: 5 runs produce consistent p50 (variance < 3%)
  T4: Probabilities sum to 100% after normalization
  T5: Contradiction matrix: S1+S2 can't both be >40% simultaneously
      (inject mock state where all S1 and S2 signals fire, verify normalization)
  T6: TPAEngine.run_cycle() returns valid tpa state dict
  T7: No `from services.` imports
  T8: SSE stream includes tpa key after sentinel integration
  T9: /intelligence/scenarios page renders (curl returns 200)
  T10: /intelligence/scenarios/snapshot/test returns 200

COMMIT after T1-T10 pass:
  git add services/tpa_engine.py data/tpa_scenarios.json
  git add data/tpa_scenario_correlations.json data/tpa_calibration.json
  git add core/templates/scenarios.html core/templates/scenario_snapshot.html
  git add core/blueprints/intelligence.py services/sentinel.py
  git add docs/audits/tpa_audit_2026-03-23.md utils/tpa_audit.py
  git add docs/phase_ml/tpa_foundation.md
  git commit -m "feat(tpa): Temporal Predictive Analytics — 5 scenario Monte Carlo engine · shareable probability tree"
  git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — FINAL INTEGRATION + FIRST TRAINING RUN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Restart gunicorn from core/ with all new changes:
   kill -9 $(lsof -ti :5000 2>/dev/null) 2>/dev/null; sleep 2
   cd ~/protocol_pulse/core && /usr/bin/python3 /home/ultron/.local/bin/gunicorn \
     --workers 2 --bind 0.0.0.0:5000 --timeout 300 --daemon \
     --error-logfile /home/ultron/protocol_pulse/logs/gunicorn_error.log \
     app:app

2. Verify SSE stream contains all new keys:
   curl -s -N http://localhost:5000/api/intelligence/stream --max-time 5 \
     | python3 -c "import sys,json; d=json.loads(sys.stdin.read().split('data: ')[1].split('\n')[0]); print('Keys:', sorted(d.keys()))"

3. Verify data collector is running:
   python3 -c "
   import time, os
   time.sleep(70)  # wait one collection cycle
   files = os.listdir('/home/ultron/protocol_pulse/data/pcaf_training/')
   print(f'Training snapshots collected: {len(files)}')
   assert len(files) >= 1, 'No snapshots collected — collector not running'
   print('PASS: data collector active')
   "

4. Start first PCAF v1 training run in background (when ≥24h of data exists):
   Write a tmux session launcher:
   tmux new-session -d -s pcaf_training \
     'cd ~/protocol_pulse && python3 services/pcaf_trainer.py 2>&1 | tee logs/pcaf_training.log; echo TRAINING_COMPLETE >> logs/pcaf_training.log'
   echo "Training session started. Check: tail -f ~/protocol_pulse/logs/pcaf_training.log"
   Note: training should NOT run immediately — the trainer.py should check
   if ≥ 1440 snapshots exist. If not, print instructions and exit gracefully.

5. Verify TPA is running:
   curl -s http://localhost:5000/api/intelligence/tpa
   Verify: 5 scenarios present, probabilities sum to ~100%

6. Verify scenarios page:
   curl -s http://localhost:5000/intelligence/scenarios | grep -c "scenario"

7. Write completion log:
   echo "[$(date -u)] [ML_SESSION] COMPLETE: PCAF v1 + TPA both deployed.
   Data collector running. First training queued for when ≥1440 snapshots exist.
   TPA: 5 scenarios live, Monte Carlo running every 6h.
   Next steps: await 24h data collection, trigger training, v1 model deploys." \
   >> ~/protocol_pulse/logs/ml_session.log

8. Final commit:
   git add -f logs/ml_session.log
   git commit -m "ops: ML session complete — PCAF v1 data collection active · TPA 5 scenarios live · training queued"
   git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QWEN BIBLE LAW — ML EDITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For every ML-specific bug found (CUDA OOM, torch_geometric import, graph
construction error, training divergence, etc.):
Document in docs/QWEN_CONTEXT_BIBLE.md under:
  ## ML SESSION — PCAF V1 + TPA — 2026-03-23
Before moving on. The Bible is the permanent record.
