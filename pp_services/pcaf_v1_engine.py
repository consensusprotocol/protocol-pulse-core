"""
PCAF V1 — Real-Time Inference Engine
======================================
Loads the trained TorchScript model + calibrated thresholds.
Scores chain-state graphs for anomalies. Falls back to v0 schema if model
not available or inference fails.

IMPORT RULE: Load via importlib.util — never `from pp_services.pcaf_v1_engine import ...`
"""

import asyncio
import importlib.util
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import torch
import torch.nn.functional as F
from torch_geometric.data import Data

logger = logging.getLogger("pcaf_v1_engine")

_svc_dir = Path(__file__).resolve().parent


def _load_data_collector_mod():
    spec = importlib.util.spec_from_file_location(
        "_pcaf_data_collector", str(_svc_dir / "pcaf_data_collector.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_model_class():
    spec = importlib.util.spec_from_file_location(
        "_pcaf_v1_model", str(_svc_dir / "pcaf_v1_model.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ChainStateAutoencoder


class PCAFv1Engine:
    """Real-time PCAF v1 inference. Falls back to v0 schema if not ready."""

    def __init__(self):
        self.model = None
        self.thresholds = None
        self.device = "cpu"  # default safe
        self._model_path = _svc_dir.parent / "models" / "pcaf_v1.pt"
        self._threshold_path = _svc_dir.parent / "models" / "pcaf_v1_thresholds.json"
        self._metadata_path = _svc_dir.parent / "models" / "pcaf_v1_metadata.json"
        self._graph_builder = None  # lazy init
        self._last_load_attempt = 0
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Try to use GPU 1 if available
        if torch.cuda.is_available() and torch.cuda.device_count() > 1:
            self.device = "cuda:1"
        elif torch.cuda.is_available():
            self.device = "cuda:0"

    def is_ready(self) -> bool:
        """True if model + thresholds both exist on disk."""
        return self._model_path.exists() and self._threshold_path.exists()

    def load(self) -> None:
        """Load TorchScript model + thresholds from disk."""
        if not self.is_ready():
            logger.debug("PCAF v1 model/thresholds not found — v0 fallback active")
            return

        # Don't retry loading more than once per 60s
        now = time.time()
        if now - self._last_load_attempt < 60 and self.model is None:
            return
        self._last_load_attempt = now

        try:
            # Load thresholds
            with open(self._threshold_path, "r") as f:
                self.thresholds = json.load(f)

            # Load model — check if it's TorchScript or state_dict
            mode_file = self._model_path.with_suffix(".mode")
            if mode_file.exists() and mode_file.read_text().strip() == "state_dict":
                AutoEncoder = _load_model_class()
                self.model = AutoEncoder(in_dim=8, latent_dim=32)
                self.model.load_state_dict(
                    torch.load(str(self._model_path), map_location=self.device))
            else:
                self.model = torch.jit.load(str(self._model_path), map_location=self.device)

            self.model = self.model.to(self.device)
            self.model.eval()

            # Load metadata for training date
            self._metadata = {}
            if self._metadata_path.exists():
                with open(self._metadata_path, "r") as f:
                    self._metadata = json.load(f)

            logger.info("PCAF v1 model loaded successfully (device=%s, training=%s)",
                        self.device, self._metadata.get("training_date", "unknown"))

        except Exception as e:
            logger.error("Failed to load PCAF v1 model: %s", e)
            self.model = None
            self.thresholds = None

    def score(self, state: dict) -> dict:
        """
        Main interface. Returns pcaf_v1 state dict.
        If not ready or inference fails: returns v0_fallback schema.
        """
        # Try to load if not loaded
        if self.model is None:
            self.load()

        if self.model is None or self.thresholds is None:
            return self._v0_fallback()

        try:
            t0 = time.time()
            data = self._build_graph(state)
            data = data.to(self.device)

            with torch.no_grad():
                recon, latent = self.model(data.x, data.edge_index)
                mse = F.mse_loss(recon, data.x).item()

            anomaly_score = self._to_anomaly_score(mse)
            inference_ms = round((time.time() - t0) * 1000, 1)

            # Determine top signal (which node type has highest error)
            with torch.no_grad():
                node_errors = F.mse_loss(recon, data.x, reduction='none').mean(dim=1)
            top_signal = self._identify_top_signal(node_errors, data)

            # Determine active rules (node types with above-average error)
            active_rules = self._identify_active_rules(node_errors, data)

            return {
                "anomaly_score": anomaly_score,
                "confidence_pct": min(anomaly_score + 10, 100) if anomaly_score > 0 else 0,
                "top_signal": top_signal,
                "active_rules": active_rules,
                "model_version": "v1",
                "reconstruction_error": round(mse, 8),
                "graph_nodes": int(data.x.size(0)),
                "graph_edges": int(data.edge_index.size(1)),
                "inference_ms": inference_ms,
                "training_date": getattr(self, "_metadata", {}).get("training_date", ""),
                "updated_at": time.time(),
            }

        except Exception as e:
            logger.warning("PCAF v1 inference failed: %s — falling back to v0", e)
            return self._v0_fallback()

    async def score_async(self, state: dict) -> dict:
        """Async wrapper around score() — runs in thread pool with 2s timeout."""
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(self._executor, self.score, state),
            timeout=2.0
        )

    def _build_graph(self, state: dict) -> Data:
        """Build PyG graph from state dict — same logic as DataCollector."""
        if self._graph_builder is None:
            mod = _load_data_collector_mod()
            self._graph_builder = mod.DataCollector()
        return self._graph_builder.build_graph(state)

    def _to_anomaly_score(self, mse: float) -> int:
        """Convert raw MSE to 0-100 anomaly score using calibrated thresholds."""
        t = self.thresholds
        note = t.get("note_threshold", 0.01)
        watch = t.get("watch_threshold", 0.05)
        critical = t.get("critical_threshold", 0.1)

        if mse <= note:
            # 0-30 range: normal
            return int(mse / max(note, 1e-10) * 30)
        elif mse <= watch:
            # 30-55: NOTE level
            ratio = (mse - note) / max(watch - note, 1e-10)
            return int(30 + ratio * 25)
        elif mse <= critical:
            # 55-85: WATCH level
            ratio = (mse - watch) / max(critical - watch, 1e-10)
            return int(55 + ratio * 30)
        else:
            # 85-100: CRITICAL level
            overshoot = min((mse - critical) / max(critical, 1e-10), 1.0)
            return int(85 + overshoot * 15)

    def _identify_top_signal(self, node_errors: torch.Tensor, data: Data) -> str:
        """Identify which node type contributes most to anomaly score."""
        node_types = getattr(data, "node_types", [])
        if not node_types or len(node_types) != node_errors.size(0):
            return "unknown"

        type_errors = {}
        for i, ntype in enumerate(node_types):
            if ntype not in type_errors:
                type_errors[ntype] = []
            type_errors[ntype].append(node_errors[i].item())

        if not type_errors:
            return "unknown"

        # Find type with highest average error
        top_type = max(type_errors, key=lambda t: sum(type_errors[t]) / len(type_errors[t]))
        avg_err = sum(type_errors[top_type]) / len(type_errors[top_type])
        return f"{top_type} anomaly (err={avg_err:.4f})"

    def _identify_active_rules(self, node_errors: torch.Tensor, data: Data) -> list:
        """Identify node types with above-average error."""
        node_types = getattr(data, "node_types", [])
        if not node_types:
            return []

        overall_mean = node_errors.mean().item()
        type_errors = {}
        for i, ntype in enumerate(node_types):
            if ntype not in type_errors:
                type_errors[ntype] = []
            type_errors[ntype].append(node_errors[i].item())

        active = []
        for ntype, errs in type_errors.items():
            avg = sum(errs) / len(errs)
            if avg > overall_mean * 1.5:  # 50% above average
                active.append(f"{ntype}: elevated ({avg:.4f})")

        return active

    def _v0_fallback(self) -> dict:
        """Return v0-compatible schema when v1 is not available."""
        return {
            "anomaly_score": 0,
            "confidence_pct": 0,
            "top_signal": "",
            "active_rules": [],
            "model_version": "v0_fallback",
            "reconstruction_error": 0.0,
            "graph_nodes": 0,
            "graph_edges": 0,
            "inference_ms": 0,
            "training_date": "",
            "updated_at": time.time(),
        }
