# PCAF v1 — GNN + RL Chain-State Trajectory Simulation
## STATUS: PENDING — Requires Dedicated ML Session

### Spec Summary
- Graph Neural Network for chain-state representation
- Reinforcement Learning for trajectory prediction
- Requires: PyTorch/TensorFlow, CUDA training pipeline, labeled dataset generation
- Model versioning and inference optimization
- Integration: replaces rule-based PCAF v0 anomaly scoring

### Prerequisites
- GPU-enabled training environment
- Historical chain-state dataset (30d minimum)
- GNN architecture selection (GCN vs GAT vs GraphSAGE)
- Training pipeline: data loading → feature extraction → model training → evaluation
- Inference optimization: ONNX export or TorchScript for sub-100ms inference

### Integration Point
- SentinelState.pcaf_v0 → SentinelState.pcaf_v1
- Backward compatible: v1 score replaces v0, same schema
- Fallback: if v1 inference fails, fall back to v0 rules
