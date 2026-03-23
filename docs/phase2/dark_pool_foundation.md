# F-P2-6: Dark Pool OTC Taint Analysis — Foundation Document

## Purpose
Track institutional OTC positioning on-chain before it hits reported data.
Watches for large UTXO movements (>100 BTC) that don't go to known exchange
wallets. Clusters of such moves within 4h windows signal institutional positioning.

## Data Sources
- **Whale transactions**: SentinelState.mempool.whale_txs (>50 BTC, already collected)
- **Exchange exclusion list**: data/custodian_wallets.json
- **Miner exclusion list**: data/miner_wallets.json

## Algorithm (Rule-Based, No ML)
1. For each whale tx (>100 BTC) in last 4h: check if destination is known exchange
2. If NOT exchange and NOT miner: classify as "dark pool candidate"
3. If 3+ dark pool candidates within 4h: fire DARK_POOL_ACCUMULATION signal
4. Compute: dark_pool_volume_4h_btc, dark_pool_tx_count_4h, exchange_destination_pct

## Taint Tracking (Lightweight)
- For each dark pool candidate destination: store in SQLite
- If same address receives multiple large inputs within 72h: elevate to WATCH
- No full blockchain taint analysis — too expensive

## Output Schema (SentinelState.dark_pool)
```json
{
  "signal": "CLEAR|WATCH|ACCUMULATION",
  "volume_4h_btc": 0.0,
  "tx_count_4h": 0,
  "top_destinations": [],
  "exchange_pct": 0.0,
  "updated_at": 0.0
}
```

## Signal Thresholds
- CLEAR: <3 dark pool candidates in 4h
- WATCH: address reuse detected within 72h
- ACCUMULATION: 3+ dark pool candidates in 4h window

## Integration
- Load via importlib.util in sentinel.py (no from services.*)
- Run every 5 minutes (poll_counter % 60 == 0)
- Display in MEMPOOL LIVE panel of intelligence_terminal.html
