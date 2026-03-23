# F-P3-5: DeFi BTC Collateralization Monitor — Foundation Document

## Purpose
Track WBTC + cbBTC supply on Ethereum as a Bitcoin-as-collateral demand signal.

## Data Sources
- WBTC: https://api.llama.fi/protocol/wrapped-bitcoin
- cbBTC: https://api.llama.fi/protocol/coinbase-wrapped-btc

## Interpretation
- Rising supply = more BTC used as DeFi collateral = demand signal
- Falling supply = risk-off or self-custody migration

## Output Schema (SentinelState.defi_btc)
```json
{
  "wbtc_supply_btc": 153420.0,
  "cbbtc_supply_btc": 12000.0,
  "total_btc_in_defi": 165420.0,
  "delta_24h_btc": 240.0,
  "signal": "ACCUMULATING|NEUTRAL|DECLINING",
  "updated_at": 0.0
}
```

## Integration
- Extends services/etf_monitor.py (no new file)
- Run every 30 minutes
