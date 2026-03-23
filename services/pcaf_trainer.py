#!/usr/bin/env python3
"""
PCAF V1 — Training Pipeline
=============================
Loads collected training snapshots, trains GraphSAGE autoencoder, calibrates
anomaly thresholds, exports TorchScript model.

Usage:
    python3 services/pcaf_trainer.py              # full training pipeline
    python3 services/pcaf_trainer.py --min-samples 100  # override minimum

Run from ~/protocol_pulse/. Uses GPU 1 (cuda:1) for training.

IMPORT RULE: Load via importlib.util — never `from services.pcaf_trainer import ...`
"""

import argparse
import importlib.util
import json
import logging
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

logger = logging.getLogger("pcaf_trainer")
logging.basicConfig(level=logging.INFO,
                    format="[PCAF_TRAIN %(levelname)s] %(asctime)s — %(message)s")

BASE = Path(__file__).resolve().parent.parent
TRAINING_DIR = BASE / "data" / "pcaf_training"
MODEL_PATH = BASE / "data" / "pcaf_v1.pt"
THRESHOLD_PATH = BASE / "data" / "pcaf_v1_thresholds.json"
METADATA_PATH = BASE / "data" / "pcaf_v1_metadata.json"
CHECKPOINT_DIR = BASE / "data"
LOG_PATH = BASE / "logs" / "pcaf_training.log"

# Minimum samples before training is allowed
MIN_SAMPLES_DEFAULT = 1440  # 24 hours of 60s snapshots


def _load_model_class():
    """Load ChainStateAutoencoder via importlib to obey the import rule."""
    spec = importlib.util.spec_from_file_location(
        "pcaf_v1_model", str(Path(__file__).resolve().parent / "pcaf_v1_model.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ChainStateAutoencoder


def load_corpus(data_dir: Path = TRAINING_DIR) -> list:
    """Load all .pkl training snapshots, sorted chronologically."""
    files = sorted(data_dir.glob("*.pkl"))
    corpus = []
    for f in files:
        try:
            with open(f, "rb") as fh:
                data = pickle.load(fh)
            if isinstance(data, Data) and data.x is not None and data.x.size(0) > 0:
                corpus.append(data)
        except Exception as e:
            logger.warning("Skipping corrupt file %s: %s", f.name, e)
    logger.info("Loaded %d valid snapshots from %s", len(corpus), data_dir)
    return corpus


def check_data_quality(corpus: list) -> dict:
    """Validate training corpus quality before training."""
    if not corpus:
        return {"ok": False, "reason": "Empty corpus"}

    # Check node count distribution
    node_counts = [d.x.size(0) for d in corpus]
    median_nodes = np.median(node_counts)
    # Flag if >20% of samples have very few nodes (< 5)
    sparse_pct = sum(1 for n in node_counts if n < 5) / len(corpus) * 100

    # Check for NaN/Inf in features
    nan_count = sum(1 for d in corpus if torch.isnan(d.x).any() or torch.isinf(d.x).any())

    ok = sparse_pct < 20 and nan_count == 0 and len(corpus) >= 100
    return {
        "ok": ok,
        "count": len(corpus),
        "median_nodes": float(median_nodes),
        "sparse_pct": round(sparse_pct, 1),
        "nan_count": nan_count,
        "reason": "OK" if ok else f"sparse={sparse_pct:.0f}%, nan={nan_count}",
    }


def train_model(corpus: list, device: str = "cuda:1",
                epochs: int = 50, batch_size: int = 32,
                lr: float = 1e-3, patience: int = 10) -> tuple:
    """Train the autoencoder. Returns (model, train_losses, val_losses)."""
    AutoEncoder = _load_model_class()

    # Chronological split: 80/10/10
    n = len(corpus)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    train_set = corpus[:train_end]
    val_set = corpus[train_end:val_end]
    test_set = corpus[val_end:]

    logger.info("Split: train=%d, val=%d, test=%d", len(train_set), len(val_set), len(test_set))

    if not torch.cuda.is_available() or not _device_available(device):
        logger.warning("CUDA device %s not available, falling back to CPU", device)
        device = "cpu"

    dev = torch.device(device)
    model = AutoEncoder(in_dim=8, latent_dim=32).to(dev)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False)

    best_val_loss = float("inf")
    patience_counter = 0
    train_losses = []
    val_losses = []

    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        for batch in train_loader:
            batch = batch.to(dev)
            optimizer.zero_grad()
            recon, _ = model(batch.x, batch.edge_index, batch.batch)
            loss = F.mse_loss(recon, batch.x)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_loss += loss.item()
            n_batches += 1

        scheduler.step()
        avg_train = epoch_loss / max(n_batches, 1)
        train_losses.append(avg_train)

        # Validate
        model.eval()
        val_loss = 0.0
        n_val = 0
        with torch.no_grad():
            for batch in val_loader:
                batch = batch.to(dev)
                recon, _ = model(batch.x, batch.edge_index, batch.batch)
                loss = F.mse_loss(recon, batch.x)
                val_loss += loss.item()
                n_val += 1

        avg_val = val_loss / max(n_val, 1)
        val_losses.append(avg_val)

        if epoch % 10 == 0 or epoch == 1:
            logger.info("Epoch %d/%d — train_loss=%.6f, val_loss=%.6f, lr=%.2e",
                        epoch, epochs, avg_train, avg_val, scheduler.get_last_lr()[0])

        # Checkpoint every 20 epochs
        if epoch % 20 == 0:
            ckpt_path = CHECKPOINT_DIR / f"pcaf_v1_checkpoint_e{epoch}.pt"
            torch.save(model.state_dict(), ckpt_path)
            logger.info("Checkpoint saved: %s", ckpt_path)

        # Early stopping
        if avg_val < best_val_loss:
            best_val_loss = avg_val
            patience_counter = 0
            # Save best model state
            torch.save(model.state_dict(), CHECKPOINT_DIR / "pcaf_v1_best.pt")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info("Early stopping at epoch %d (patience=%d)", epoch, patience)
                break

    # Load best model
    model.load_state_dict(torch.load(CHECKPOINT_DIR / "pcaf_v1_best.pt", map_location=dev))
    return model, train_losses, val_losses


def calibrate_thresholds(model, val_corpus: list, device: str = "cuda:1") -> dict:
    """Compute anomaly score thresholds from validation set reconstruction errors."""
    if not torch.cuda.is_available() or not _device_available(device):
        device = "cpu"
    dev = torch.device(device)
    model = model.to(dev)
    model.eval()

    errors = []
    with torch.no_grad():
        for data in val_corpus:
            data = data.to(dev)
            recon, _ = model(data.x, data.edge_index)
            mse = F.mse_loss(recon, data.x).item()
            errors.append(mse)

    errors = np.array(errors)
    thresholds = {
        "note_threshold": float(np.percentile(errors, 70)),
        "watch_threshold": float(np.percentile(errors, 90)),
        "critical_threshold": float(np.percentile(errors, 99)),
        "error_mean": float(np.mean(errors)),
        "error_std": float(np.std(errors)),
        "error_p50": float(np.median(errors)),
        "calibration_samples": len(errors),
        "calibrated_at": time.time(),
    }
    logger.info("Thresholds — NOTE: %.6f, WATCH: %.6f, CRITICAL: %.6f",
                thresholds["note_threshold"], thresholds["watch_threshold"],
                thresholds["critical_threshold"])
    return thresholds


def export_model(model, output_path: Path = MODEL_PATH, device: str = "cuda:1") -> None:
    """Export model as TorchScript and verify."""
    if not torch.cuda.is_available() or not _device_available(device):
        device = "cpu"
    dev = torch.device(device)
    model = model.to(dev).eval()

    # TorchScript trace with dummy data
    dummy_x = torch.randn(10, 8, device=dev)
    dummy_ei = torch.randint(0, 10, (2, 20), device=dev)

    try:
        # Use torch.jit.trace for PyG compatibility
        traced = torch.jit.trace(model, (dummy_x, dummy_ei), check_trace=False)
        traced.save(str(output_path))
        logger.info("TorchScript model saved to %s", output_path)
    except Exception as e:
        logger.warning("TorchScript trace failed (%s), saving state_dict instead", e)
        torch.save(model.state_dict(), output_path)
        # Write a flag so the engine knows it's a state_dict, not TorchScript
        meta_flag = output_path.with_suffix(".mode")
        meta_flag.write_text("state_dict")
        logger.info("State dict saved to %s (TorchScript fallback)", output_path)

    # Verify
    logger.info("Verifying saved model...")
    try:
        if output_path.with_suffix(".mode").exists():
            AutoEncoder = _load_model_class()
            loaded = AutoEncoder(in_dim=8, latent_dim=32)
            loaded.load_state_dict(torch.load(str(output_path), map_location="cpu"))
        else:
            loaded = torch.jit.load(str(output_path), map_location="cpu")
        test_x = torch.randn(5, 8)
        test_ei = torch.randint(0, 5, (2, 8))
        out, lat = loaded(test_x, test_ei)
        assert out.shape == test_x.shape, f"Shape mismatch: {out.shape} vs {test_x.shape}"
        logger.info("Verification PASSED — model loads and produces correct shape")
    except Exception as e:
        logger.error("Verification FAILED: %s", e)
        raise


def run_training_pipeline(min_samples: int = MIN_SAMPLES_DEFAULT,
                          device: str = "cuda:1") -> None:
    """Full pipeline: load → validate → train → calibrate → export."""
    logger.info("=" * 60)
    logger.info("PCAF V1 TRAINING PIPELINE START")
    logger.info("=" * 60)

    # Load corpus
    corpus = load_corpus()
    if len(corpus) < min_samples:
        logger.info("Insufficient data: %d/%d snapshots. "
                     "Collect more data (1 snapshot/min, need %d min = %.1f hours).",
                     len(corpus), min_samples, min_samples, min_samples / 60)
        logger.info("Data collector is running. Training will be possible in ~%.1f hours.",
                     (min_samples - len(corpus)) / 60)
        return

    # Quality check
    quality = check_data_quality(corpus)
    logger.info("Data quality: %s", json.dumps(quality, indent=2))
    if not quality["ok"]:
        logger.error("Data quality check failed: %s", quality["reason"])
        return

    # Train
    t0 = time.time()
    model, train_losses, val_losses = train_model(corpus, device=device)
    train_time = time.time() - t0
    logger.info("Training completed in %.1f minutes", train_time / 60)

    # Calibrate
    n = len(corpus)
    val_set = corpus[int(n * 0.8):int(n * 0.9)]
    thresholds = calibrate_thresholds(model, val_set, device=device)
    with open(THRESHOLD_PATH, "w") as f:
        json.dump(thresholds, f, indent=2)
    logger.info("Thresholds saved to %s", THRESHOLD_PATH)

    # Export
    export_model(model, MODEL_PATH, device=device)

    # Save metadata
    metadata = {
        "training_date": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "dataset_size": len(corpus),
        "final_train_loss": train_losses[-1] if train_losses else 0,
        "final_val_loss": val_losses[-1] if val_losses else 0,
        "best_val_loss": min(val_losses) if val_losses else 0,
        "epochs_trained": len(train_losses),
        "training_time_s": round(train_time, 1),
        "device": device,
        "architecture": "ChainStateAutoencoder(in=8, latent=32, SAGEConv x3)",
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("=" * 60)
    logger.info("PCAF V1 TRAINING COMPLETE")
    logger.info("Model: %s", MODEL_PATH)
    logger.info("Thresholds: %s", THRESHOLD_PATH)
    logger.info("Metadata: %s", METADATA_PATH)
    logger.info("=" * 60)


def _device_available(device_str: str) -> bool:
    """Check if a CUDA device is available."""
    if not device_str.startswith("cuda"):
        return True
    try:
        idx = int(device_str.split(":")[1]) if ":" in device_str else 0
        return idx < torch.cuda.device_count()
    except Exception:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PCAF v1 training pipeline")
    parser.add_argument("--min-samples", type=int, default=MIN_SAMPLES_DEFAULT,
                        help=f"Minimum training samples (default: {MIN_SAMPLES_DEFAULT})")
    parser.add_argument("--device", default="cuda:1", help="Training device")
    args = parser.parse_args()

    # File logging
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(str(LOG_PATH))
    fh.setFormatter(logging.Formatter("[PCAF_TRAIN %(levelname)s] %(asctime)s — %(message)s"))
    logger.addHandler(fh)

    run_training_pipeline(min_samples=args.min_samples, device=args.device)
