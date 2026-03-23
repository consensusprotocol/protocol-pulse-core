# F-P2-7: Miner Stress & Capitulation Model — Foundation Document

## Purpose
Quantitative miner health score (0-100) that predicts capitulation before it happens.
100 = miners thriving, 0 = mass capitulation.

## Inputs (all from SentinelState or mempool.space)
- hashrate_3d: declining = stress
- difficulty_adj_pct: negative = stress
- mempool fee softness: low fees = miner revenue down
- block_time_avg: high = hashrate dropping
- coinbase_to_exchange_ratio: from dark_pool_engine miner wallet classification

## Score Formula (Rule-Based Weighted Sum)
```
score = 100
if hashrate_3d declining >5%:   score -= 20
if hashrate_3d declining >15%:  score -= 20 (additional)
if difficulty_adj < -3%:        score -= 15
if difficulty_adj < -8%:        score -= 15 (additional)
if next_block_fee < 5 sat/vB for >2h: score -= 10
if avg_block_time > 750s:       score -= 10
if coinbase_to_exchange > 2x avg: score -= 20
score = max(0, min(100, score))
```

## Labels
- score >= 70: HEALTHY
- score >= 30: STRESSED
- score >= 15: CAPITULATION_WATCH
- score < 15:  CAPITULATION_CRITICAL

## Historical Context
- Store daily score in baseline_store.db
- If score is lowest in 90 days: add "90-DAY LOW" label

## Output Schema (SentinelState.miner_health)
```json
{
  "score": 82,
  "label": "HEALTHY",
  "components": {"hashrate": -0, "difficulty": -0, "fees": -10, "block_time": -0, "coinbase_ratio": -0},
  "is_90d_low": false,
  "updated_at": 0.0
}
```

## Integration
- Load via importlib.util in sentinel.py
- Run every 10 minutes (poll_counter % 120)
- Display: "MINER: [████████░░] 82/100 HEALTHY" in SENTINEL CORE panel
