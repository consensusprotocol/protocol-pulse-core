# F-P3-9: Backtesting Interface — Foundation Document

## Purpose
Run historical alerts against price data to validate signal quality.

## Data
- Alert history: sentinel_alerts.db (growing)
- Price history: CoinGecko API (365 days free)
- For each alert: price_at_alert, price_24h_later, price_7d_later

## DB Changes
- ALTER TABLE alerts ADD COLUMN price_at_alert REAL
- ALTER TABLE alerts ADD COLUMN price_24h_later REAL
- ALTER TABLE alerts ADD COLUMN price_7d_later REAL
- ALTER TABLE alerts ADD COLUMN outcome TEXT

## Outcome Classification
- correct_bullish: price rose >2% after WATCH alert
- correct_bearish: price fell >2% after sell signal
- no_move: price within +/-2%
- pending: not enough time elapsed

## Routes
- GET /intelligence/backtest — backtest page
- GET /api/intelligence/backtest — backtest data JSON

## Background Job
- Daily: for alerts >24h old with no outcome, fetch CoinGecko history
- Compute price deltas and classify outcome
