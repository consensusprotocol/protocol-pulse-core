# MASTER DATA SOURCE REPORT: Bitcoin Miner Conviction Signals

---

## EXECUTIVE SUMMARY

Three LLM audits synthesized across Gemini, GPT-4o, and Grok. This report extracts consensus sources, unique findings, and brutal gaps versus paid alternatives. **Signal target: Miner Conviction** — measuring whether miners are accumulating, selling, or capitulating based on hashrate trajectory, revenue sustainability, wallet flows, and difficulty-adjusted profitability.

---

## SECTION 1: COMPLETE FREE SOURCE REGISTRY

### 1A. UNANIMOUS CONSENSUS SOURCES (All 3 Models Agree)

| # | Name | Exact URL | Auth | Rate Limit | Key Fields for Miner Conviction | Update Freq | Consensus Quality |
|---|------|-----------|------|------------|--------------------------------|-------------|-------------------|
| 1 | Mempool.space Hashrate | `https://mempool.space/api/v1/mining/hashrate/all` | None | ~10 req/min | `hashrates[].avgHashrate`, `hashrates[].timestamp`, `currentHashrate` | ~10 min | 9.3/10 |
| 2 | Mempool.space Difficulty | `https://mempool.space/api/v1/difficulty-adjustment` | None | ~10 req/min | `progressPercent`, `difficultyChange`, `estimatedRetargetDate`, `remainingBlocks`, `previousRetarget` | Per block | 9.5/10 |
| 3 | Mempool.space Mining Pools | `https://mempool.space/api/v1/mining/pools/1w` | None | ~10 req/min | `pools[].name`, `pools[].share`, `pools[].blockCount`, `pools[].rank` | Daily | 9.0/10 |
| 4 | Mempool.space Blocks | `https://mempool.space/api/v1/blocks` | None | ~10 req/min | `reward`, `extras.totalFees`, `extras.medianFee`, `extras.pool.name`, `timestamp` | Per block | 9.2/10 |
| 5 | Mempool.space Address | `https://mempool.space/api/address/{address}` | None | ~10 req/min | `chain_stats.funded_txo_sum`, `chain_stats.spent_txo_sum`, `mempool_stats.tx_count` | Per TX | 8.8/10 |
| 6 | Blockchain.com Hashrate Chart | `https://api.blockchain.info/charts/hash-rate?timespan=1year&format=json` | None | ~5 req/sec | `values[].x` (timestamp), `values[].y` (TH/s) | Daily | 7.3/10 |
| 7 | BTC.com Pool Stats | `https://pool.btc.com/v1/pool-stats` | None | Unknown | `hashrate`, `share_percentage`, `pool_name` | Daily | 8.0/10 |
| 8 | ASIC Miner Value | `https://www.asicminervalue.com/` | None (scrape) | Polite scraping | `profitability_usd_day`, `efficiency_wth`, `model_name`, `breakeven_price` | Daily | 6.5/10 |

---

### 1B. MAJORITY CONSENSUS SOURCES (2 of 3 Models Agree)

| # | Name | Exact URL | Auth | Rate Limit | Key Fields for Miner Conviction | Update Freq | Quality |
|---|------|-----------|------|------------|--------------------------------|-------------|---------|
| 9 | Mempool.space Block by Height | `https://mempool.space/api/block-height/{height}` | None | ~10 req/min | `reward`, `extras.totalFees`, `extras.miner`, `size`, `weight` | Per block | 9.0/10 |
| 10 | Blockchain.com Quick Hashrate | `https://blockchain.info/q/hashrate` | None | ~5 req/sec | Raw hashrate value (GH/s) | Daily | 7.0/10 |
| 11 | Blockchain.com Block Count | `https://blockchain.info/q/getblockcount` | None | ~5 req/sec | Current block height (difficulty epoch calc) | Real-time | 7.0/10 |
| 12 | Blockchain.com Miner Revenue Chart | `https://api.blockchain.info/charts/miners-revenue?timespan=1year&format=json` | None | ~5 req/sec | `values[].y` (USD revenue/day) | Daily | 7.5/10 |
| 13 | Blockchain.com Difficulty Chart | `https://api.blockchain.info/charts/difficulty?timespan=1year&format=json` | None | ~5 req/sec | `values[].y` (difficulty value) | Per retarget | 7.5/10 |
| 14 | Coin Metrics Community API | `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=HashRate,RevHashNtv,DiffMean&frequency=1d` | None | 10 req/min | `HashRate`, `RevHashNtv` (native miner revenue per hash), `DiffMean`, `FeeTotNtv` | Daily | 8.5/10 |
| 15 | Luxor Hashrate Index GraphQL | `https://api.hashrateindex.com/graphql` | None (free tier) | Unspecified | `btcHashprice`, `btcHashvalue`, `btcNetworkHashrate`, `btcDifficulty` | Daily | 9.0/10 |
| 16 | SEC EDGAR Miner Filings | `https://efts.sec.gov/LATEST/search-index?q=%22bitcoin+mining%22&dateRange=custom&startdt=2024-01-01&forms=10-Q,10-K` | None | Public | BTC holdings, production rate, opex, breakeven cost | Quarterly | 8.0/10 |

---

### 1C. SINGLE-MODEL UNIQUE FINDS (High Value — Do Not Ignore)

| # | Name | Exact URL | Found By | Key Fields | Why It Matters |
|---|------|-----------|----------|------------|----------------|
| 17 | Mempool.space WebSocket | `wss://mempool.space/api/v1/ws` | Gemini | Real-time block events, fee spikes, block interval variance | **Only real-time miner revenue stream available free** |
| 18 | Mempool.space Pool Period | `https://mempool.space/api/v1/mining/pools/3m` | Grok | 3-month pool hashrate share trends | Longer conviction window than 1w |
| 19 | Bitcoin Core RPC `getnetworkhashps` | `http://127.0.0.1:8332` (local node) | GPT-4o | `getnetworkhashps`, `getmininginfo`, `getblocktemplate` | **Ground truth — no API intermediary** |
| 20 | Mempool.space Mining Pool Detail | `https://mempool.space/api/v1/mining/pool/{slug}/hashrate` | Grok | Per-pool hashrate over time for specific pools (AntPool, Foundry, etc.) | Pool-level conviction, not just network |
| 21 | Mempool.space Block Subsidy History | `https://mempool.space/api/v1/mining/reward-stats/144` | Gemini | `totalReward`, `totalFee`, `totalTx` over last 144 blocks (≈1 day) | Fee ratio to subsidy — forward miner sustainability |
| 22 | Nostr Relay Mining Events | `wss://relay.damus.io` | GPT-4o | Miner sentiment broadcasts, pool announcements | Qualitative conviction signal (experimental) |
| 23 | Blockchain.com Miner Cost Per TX | `https://api.blockchain.info/charts/cost-per-transaction?format=json` | Grok | `values[].y` (USD cost/tx) | Margin compression indicator |
| 24 | Blockchain.com Hash Rate Distribution | `https://api.blockchain.info/charts/pools?timespan=4days&format=json` | Grok | Pool distribution, Nakamoto coefficient proxy | Miner concentration risk |

---

## SECTION 2: WHAT EACH MODEL UNIQUELY CONTRIBUTED

### GEMINI — Unique Contributions
```
STRENGTH: Infrastructure depth and real-time data architecture
UNIQUE FINDS:
  1. WebSocket feed (wss://mempool.space/api/v1/ws) — only model to identify 
     real-time block subscription for instant miner revenue data
  2. Block-level fee decomposition (extras.totalFees, extras.avgFee vs medianFee)
  3. Known miner wallet tracking methodology (specific address examples)
  4. SEC EDGAR filing extraction workflow for public miner financials
  5. ASIC Miner Value scraping methodology with BeautifulSoup pattern

METHODOLOGY ADVANTAGE: Tiered framework with quality scoring per field
WEAKNESS: Some URLs were partial/conceptual rather than fully tested
```

### GPT-4O — Unique Contributions
```
STRENGTH: Breadth of source categories, included node-level data
UNIQUE FINDS:
  1. Bitcoin Core RPC interface (local node) — ground truth without API dependency
  2. Nostr relay as qualitative sentiment layer (experimental but novel)
  3. CryptoCompare as Glassnode approximation
  4. Minerstat API (https://api.minerstat.com/v2/stats) — unique to this model
  5. GitHub repository mining (bitcoin/bitcoin repo data scripts)

METHODOLOGY ADVANTAGE: Identified the self-hosted node path others ignored
WEAKNESS: Several URLs unverified or returned to homepages (BTC.com /stats/pool
          resolves to HTML not JSON). Least technically rigorous URL validation.
```

### GROK — Unique Contributions
```
STRENGTH: Most complete table format, best field-level documentation
UNIQUE FINDS:
  1. Per-pool hashrate history endpoint (mempool.space/api/v1/mining/pool/{slug}/hashrate)
  2. Extended timeframes — identified 3m, 6m pool windows not just 1w
  3. Blockchain.com cost-per-transaction chart URL
  4. Blockchain.com hash rate distribution (pools) chart
  5. Most explicit rate limit estimates across all sources
  6. Identified Satoshi genesis address as a test case for the address API

METHODOLOGY ADVANTAGE: Best structured output, most copy-paste ready
WEAKNESS: Less creative in Tier 2, some sources repeated from Tier 1 with 
          minor variations
```

---

## SECTION 3: PRIORITY RANKINGS

### P0 — CRITICAL (Build Signal First, Zero Gaps Acceptable)

| Priority | Source | URL | Conviction Metric It Enables |
|----------|--------|-----|------------------------------|
| P0-1 | Mempool.space Hashrate History | `https://mempool.space/api/v1/mining/hashrate/all` | Hash ribbon construction, 30d/60d MA crossover |
| P0-2 | Mempool.space Difficulty Adjustment | `https://mempool.space/api/v1/difficulty-adjustment` | Difficulty death spiral detection, miner exit signal |
| P0-3 | Coin Metrics Community API | `https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc&metrics=HashRate,RevHashNtv,DiffMean&frequency=1d` | Revenue-per-hash (breakeven proximity) |
| P0-4 | Luxor Hashrate Index | `https://api.hashrateindex.com/graphql` | Hashprice (USD/PH/day) — the single best miner margin metric |
| P0-5 | Mempool.space WebSocket | `wss://mempool.space/api/v1/ws` | Real-time fee/reward ratio, block interval anomaly detection |

### P1 — HIGH VALUE (Add Within First Sprint)

| Priority | Source | URL | Conviction Metric It Enables |
|----------|--------|-----|------------------------------|
| P1-1 | Mempool.space Pool Distribution | `https://mempool.space/api/v1/mining/pools/3m` | Pool exit detection (capitulation precursor) |
| P1-2 | Blockchain.com Miner Revenue | `https://api.blockchain.info/charts/miners-revenue?timespan=1year&format=json` | Historical revenue drawdown analysis |
| P1-3 | Mempool.space Block-Level Fees | `https://mempool.space/api/v1/blocks` | Fee-to-subsidy ratio (post-halving sustainability) |
| P1-4 | Blockchain.com Difficulty | `https://api.blockchain.info/charts/difficulty?timespan=2years&format=json` | Long-cycle difficulty trend |
| P1-5 | ASIC Miner Value (scrape) | `https://www.asicminervalue.com/` | Hardware-level breakeven, efficiency curve |
| P1-6 | SEC EDGAR Filings | `https://efts.sec.gov/LATEST/search-index?q=%22bitcoin+mining%22&forms=10-Q,10-K` | Institutional miner BTC treasury changes |

### P2 — SUPPLEMENTARY (Nice to Have, Lower ROI)

| Priority | Source | URL | Conviction Metric It Enables |
|----------|--------|-----|------------------------------|
| P2-1 | Known Miner Wallet Addresses | `https://mempool.space/api/address/{address}` | Direct wallet-level conviction (UTXO accumulation) |
| P2-2 | Blockchain.com Cost Per TX | `https://api.blockchain.info/charts/cost-per-transaction?format=json` | Margin compression proxy |
| P2-3 | Bitcoin Core RPC (local node) | `http://127.0.0.1:8332` | Ground truth, zero latency (requires infrastructure) |
| P2-4 | Minerstat API | `https://api.minerstat.com/v2/stats` | Secondary hashrate validation |
| P2-5 | Mempool.space Per-Pool Hashrate | `https://mempool.space/api/v1/mining/pool/{slug}/hashrate` | Individual pool trend isolation |

---

## SECTION 4: PYTHON CODE — PRIMARY FREE DATA FETCH (NO API KEY)

```python
"""
Bitcoin Miner Conviction Signal Aggregator
All P0 + P1 sources. Zero API keys required.
"""

import requests
import json
import time
import pandas as pd
from datetime import datetime, timezone
import websocket
import threading
from typing import Optional


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "MinerConvictionBot/1.0 (research; contact@example.com)",
    "Accept": "application/json"
}
REQUEST_DELAY = 0.5  # seconds between calls — be a good citizen


def safe_get(url: str, params: dict = None) -> Optional[dict]:
    """Rate-limited GET with error handling."""
    try:
        time.sleep(REQUEST_DELAY)
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"[HTTP ERROR] {url} → {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR] {url} → {e}")
        return None
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] {url}")
        return None
    