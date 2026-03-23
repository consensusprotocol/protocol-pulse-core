# F-P3-3: Privacy Tech Pulse — Foundation Document

## Purpose
Track Bitcoin privacy technology adoption: Coinjoin volume, Tor node %, Taproot adoption, Nostr growth.

## Data Sources
- Coinjoin: mempool.space blocks (heuristic: multiple equal-value outputs)
- Taproot: mempool.space/api/v1/statistics
- Tor nodes: bitnodes.io/api/v1/snapshots/latest/ (6h cache)
- Nostr: sentinel's existing relay connection event count
- Silent Payments: heuristic OP_RETURN SP marker detection

## Sovereignty Index (0-100 composite)
Weighted average of all metrics vs their baseline values.

## Output Schema (SentinelState.privacy_tech)
```json
{
  "coinjoin_signal": "NORMAL|ELEVATED|SPIKE",
  "coinjoin_7d_btc": 0.0,
  "taproot_tx_pct": 0.0,
  "taproot_utxo_pct": 0.0,
  "tor_node_pct": 0.0,
  "nostr_24h_events": 0,
  "sp_7d_count": 0,
  "sovereignty_index": 50.0,
  "updated_at": 0.0
}
```

## Integration
- Load via importlib.util
- Run every 1 hour
- Small panel showing sovereignty_index gauge
