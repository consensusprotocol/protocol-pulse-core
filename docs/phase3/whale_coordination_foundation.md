# F-P3-1: Whale Coordination Detection — Foundation Document

## Purpose
Detect synchronized large UTXO movements from taint-linked clusters + social signal correlation.

## Algorithm (Rule-Based)
1. 3+ whale txs (>100 BTC) within 90-minute window
2. Check destinations against dark_pool_addresses SQLite table
3. If 2+ destinations appear in same table with overlapping time windows: taint-linked
4. Cross-reference with sentiment_engine tier1_signal for elevation

## Signal Levels
- CLEAR: No coordination detected
- NOTE: Coordination detected but no social correlation
- WATCH: Coordination + tier1_social_active

## Output Schema (SentinelState.whale_coordination)
```json
{
  "signal": "CLEAR|NOTE|WATCH",
  "tx_count_90min": 0,
  "taint_linked": false,
  "tier1_social_active": false,
  "total_btc_90min": 0.0,
  "updated_at": 0.0
}
```

## Integration
- Load via importlib.util in sentinel.py
- Run every 5 minutes
- Display in MEMPOOL LIVE panel alongside dark pool indicator
