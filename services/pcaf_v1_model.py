"""
PCAF V1 — GNN Autoencoder Model Architecture
==============================================
GraphSAGE-based autoencoder for unsupervised anomaly detection on Bitcoin
chain-state graphs. High reconstruction error = anomalous chain state.

Architecture:
  Encoder: 3-layer SAGEConv (8→64→128→256) + global mean pool → 128-dim → 32-dim latent
  Decoder: Linear (32→256→128→64→8) mirrors encoder, reconstructs node features
  Anomaly score: MSE of reconstruction vs input features

IMPORT RULE: Load via importlib.util — never `from services.pcaf_v1_model import ...`
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, global_mean_pool


class ChainStateEncoder(nn.Module):
    """3-layer GraphSAGE encoder → graph-level embedding → latent bottleneck."""

    def __init__(self, in_dim: int = 8, hidden1: int = 64, hidden2: int = 128,
                 hidden3: int = 256, graph_dim: int = 128, latent_dim: int = 32):
        super().__init__()
        self.conv1 = SAGEConv(in_dim, hidden1)
        self.conv2 = SAGEConv(hidden1, hidden2)
        self.conv3 = SAGEConv(hidden2, hidden3)
        self.graph_proj = nn.Linear(hidden3, graph_dim)
        self.bottleneck = nn.Linear(graph_dim, latent_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor,
                batch: torch.Tensor = None) -> tuple:
        """Returns (node_embeddings_256d, latent_32d)."""
        h = F.relu(self.conv1(x, edge_index))
        h = F.relu(self.conv2(h, edge_index))
        h = F.relu(self.conv3(h, edge_index))  # [N, 256]

        # Graph-level: global mean pooling → project → bottleneck
        if batch is None:
            batch = torch.zeros(h.size(0), dtype=torch.long, device=h.device)
        g = global_mean_pool(h, batch)  # [B, 256]
        g = F.relu(self.graph_proj(g))  # [B, 128]
        latent = self.bottleneck(g)     # [B, 32]

        return h, latent


class ChainStateDecoder(nn.Module):
    """Mirror decoder: latent → broadcast to nodes → reconstruct features."""

    def __init__(self, latent_dim: int = 32, hidden3: int = 256,
                 hidden2: int = 128, hidden1: int = 64, out_dim: int = 8):
        super().__init__()
        self.expand = nn.Linear(latent_dim, hidden3)
        self.fc1 = nn.Linear(hidden3 * 2, hidden2)  # concat node emb + expanded latent
        self.fc2 = nn.Linear(hidden2, hidden1)
        self.fc3 = nn.Linear(hidden1, out_dim)

    def forward(self, node_embeddings: torch.Tensor, latent: torch.Tensor,
                batch: torch.Tensor = None) -> torch.Tensor:
        """Reconstruct node features from node embeddings + graph latent."""
        if batch is None:
            batch = torch.zeros(node_embeddings.size(0), dtype=torch.long,
                                device=node_embeddings.device)

        # Broadcast latent to each node
        latent_expanded = self.expand(latent)  # [B, 256]
        latent_per_node = latent_expanded[batch]  # [N, 256]

        # Concat node embeddings with broadcast latent
        combined = torch.cat([node_embeddings, latent_per_node], dim=1)  # [N, 512]

        h = F.relu(self.fc1(combined))  # [N, 128]
        h = F.relu(self.fc2(h))          # [N, 64]
        out = self.fc3(h)                # [N, 8]
        return out


class ChainStateAutoencoder(nn.Module):
    """Full autoencoder: encode graph → latent → decode → reconstruction error = anomaly."""

    def __init__(self, in_dim: int = 8, latent_dim: int = 32):
        super().__init__()
        self.encoder = ChainStateEncoder(in_dim=in_dim, latent_dim=latent_dim)
        self.decoder = ChainStateDecoder(latent_dim=latent_dim, out_dim=in_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor,
                batch: torch.Tensor = None) -> tuple:
        """
        Returns (reconstructed_features, latent).
        reconstructed_features has same shape as input x.
        """
        node_emb, latent = self.encoder(x, edge_index, batch)
        reconstructed = self.decoder(node_emb, latent, batch)
        return reconstructed, latent

    def reconstruction_error(self, x: torch.Tensor, edge_index: torch.Tensor,
                             batch: torch.Tensor = None) -> torch.Tensor:
        """Compute per-graph MSE reconstruction error."""
        reconstructed, _ = self.forward(x, edge_index, batch)
        # Per-node MSE
        node_mse = F.mse_loss(reconstructed, x, reduction='none').mean(dim=1)  # [N]
        # Aggregate per graph
        if batch is None:
            return node_mse.mean().unsqueeze(0)  # single graph
        from torch_geometric.nn import global_mean_pool as _gmp
        return _gmp(node_mse.unsqueeze(1), batch).squeeze(1)  # [B]
