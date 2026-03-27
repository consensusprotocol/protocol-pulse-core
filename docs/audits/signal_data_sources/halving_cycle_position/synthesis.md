# MASTER DATA SOURCE REPORT: Bitcoin Halving Cycle Position Signal
## Synthesized from 3 LLM Audits | Free Sources Only | Production-Ready

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agreed)

These sources appeared across Gemini, GPT-4o, and Grok — highest confidence, use immediately.

---

### SOURCE U-1: Mempool.space API
| Field | Value |
|-------|-------|
| **URL** | `https://mempool.space/api/v1/blocks/tip/height` |
| **Auth** | None |
| **Rate Limit** | ~10 req/min (unofficial, no enforcement documented) |
| **Key Fields** | `height` (integer, current block height) |
| **Update Freq** | Real-time (~every 10 minutes per block) |
| **Quality Score** | 9.5/10 |
| **Halving Relevance** | **CRITICAL** — Block height is the atomic unit of halving calculation |
| **Additional Endpoints** | `https://mempool.space/api/v1/difficulty-adjustment` → `remainingBlocks`, `remainingTime`, `progressPercent` |
| **Additional Endpoints** | `https://mempool.space/api/blocks` → full block metadata array |

**Why it matters:** Every halving cycle calculation derives from block height. 210,000 blocks per epoch. Current height mod 210,000 = exact position in cycle. No API key, no rate limit enforcement, open source infrastructure.

---

### SOURCE U-2: CoinGecko API
| Field | Value |
|-------|-------|
| **URL** | `https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=max&interval=daily` |
| **Auth** | None (Demo tier, free) |
| **Rate Limit** | 10–30 req/min on free tier (varies by server load) |
| **Key Fields** | `prices[][]` (timestamp, USD price), `market_caps[][]`, `total_volumes[][]` |
| **Update Freq** | Daily (free tier), 1–5 min (Pro) |
| **Quality Score** | 9/10 |
| **Halving Relevance** | HIGH — Historical price across all 4 halving cycles, enables cycle-relative price analysis |
| **Additional Endpoints** | `https://api.coingecko.com/api/v3/coins/bitcoin` → `market_data.circulating_supply`, `market_data.max_supply` |

---

### SOURCE U-3: Yahoo Finance via yfinance Library
| Field | Value |
|-------|-------|
| **URL** | PyPI: `https://pypi.org/project/yfinance/` | Ticker: `BTC-USD` |
| **Auth** | None |
| **Rate Limit** | ~2,000 req/hr per IP (unofficial, scrape-based) |
| **Key Fields** | `Open`, `High`, `Low`, `Close`, `Volume`, `Dividends`, `Stock Splits` |
| **Update Freq** | Daily (1d interval), 1m to 1h intraday available |
| **Quality Score** | 8/10 |
| **Halving Relevance** | MEDIUM-HIGH — OHLCV history from 2014 covers 3 complete halving cycles |
| **Caveat** | Not an official API. Yahoo can break it without notice. Use as backup, not primary. |

---

### SOURCE U-4: FRED API (St. Louis Federal Reserve)
| Field | Value |
|-------|-------|
| **Base URL** | `https://api.stlouisfed.org/fred/series/observations` |
| **Auth** | Free API key required — register at `https://fred.stlouisfed.org/docs/api/api_key.html` |
| **Rate Limit** | 120 req/min |
| **Key Fields** | See series table below |
| **Update Freq** | Daily to Monthly depending on series |
| **Quality Score** | 10/10 for macro context |
| **Halving Relevance** | MEDIUM — Macro conditions modulate halving cycle signal strength |

**Critical FRED Series for Halving Context:**

| Series ID | Description | URL Param |
|-----------|-------------|-----------|
| `M2SL` | M2 Money Supply | `series_id=M2SL` |
| `DGS10` | 10-Year Treasury Yield | `series_id=DGS10` |
| `WALCL` | Fed Balance Sheet (Total Assets) | `series_id=WALCL` |
| `DTWEXBGS` | US Dollar Index (Broad) | `series_id=DTWEXBGS` |
| `CPIAUCSL` | CPI Inflation | `series_id=CPIAUCSL` |

---

### SOURCE U-5: Blockchain.com API
| Field | Value |
|-------|-------|
| **URL** | `https://api.blockchain.info/charts/total-bitcoins?timespan=all&format=json` |
| **Auth** | None |
| **Rate Limit** | ~10 req/min (strict enforcement noted by GPT-4o and Gemini) |
| **Key Fields** | `values[].x` (Unix timestamp), `values[].y` (circulating BTC) |
| **Update Freq** | Daily |
| **Quality Score** | 8/10 |
| **Halving Relevance** | HIGH — Circulating supply directly encodes emission schedule; supply curve inflection at each halving |
| **Additional Endpoints** | `https://api.blockchain.info/charts/market-price?timespan=all&format=json` — full price history |
| **Additional Endpoints** | `https://blockchain.info/q/getblockcount` — raw block height integer |

---

## SECTION 2: MAJORITY SOURCES (2 of 3 Models Agreed)

---

### SOURCE M-1: Alternative.me Fear & Greed Index
| Field | Value |
|-------|-------|
| **URL** | `https://api.alternative.me/fng/?limit=0` |
| **Auth** | None |
| **Rate Limit** | ~60 req/min |
| **Key Fields** | `data[].value` (0–100 score), `data[].value_classification` (Extreme Fear → Extreme Greed), `data[].timestamp` |
| **Update Freq** | Daily |
| **Quality Score** | 8/10 |
| **Halving Relevance** | MEDIUM — Sentiment extremes historically correlate with halving cycle phases (extreme fear = accumulation zone, extreme greed = distribution) |
| **Found by** | Gemini + Grok |

---

### SOURCE M-2: BitcoinCharts Historical Data Dumps
| Field | Value |
|-------|-------|
| **URL** | `http://api.bitcoincharts.com/v1/csv/bitstampUSD.csv.gz` |
| **Auth** | None |
| **Rate Limit** | None (static file downloads) |
| **Key Fields** | `timestamp`, `price`, `amount` (trade-level granularity) |
| **Update Freq** | Static (data through ~2021, useful for historical cycle analysis) |
| **Quality Score** | 6/10 (age limitation) |
| **Halving Relevance** | MEDIUM — Tick-level data for halvings 1, 2, 3 (2012, 2016, 2020) |
| **Found by** | Grok + GPT-4o |

---

## SECTION 3: UNIQUE FINDINGS PER MODEL

### What Gemini Found That Others Missed

**1. Mempool.space Difficulty Adjustment Endpoint (Unique Endpoint Discovery)**
- URL: `https://mempool.space/api/v1/difficulty-adjustment`
- Returns: `remainingBlocks`, `remainingTime`, `progressPercent`, `difficultyChange`, `estimatedRetargetDate`
- **This is the single most useful endpoint for halving cycle position** — it gives you percentage completion within current epoch directly. Neither GPT-4o nor Grok cited this specific endpoint.

**2. Bitcoin Core Full Node RPC as Ground Truth**
- Gemini was most explicit about the architecture: run `bitcoind`, query via JSON-RPC
- Commands: `getblockcount`, `getblockhash`, `getblock`, `getmempoolinfo`
- Cost: Free software + ~$200 Raspberry Pi + 550GB storage
- **Significance:** Zero trust assumptions, no API dependency, no rate limits, no downtime risk

**3. Bitcoinity Data (CSV Export)**
- URL: `http://data.bitcoinity.org/export_data.csv?c=e&data_type=price&t=l&timespan=all`
- Auth: None
- Format: CSV with `Time`, `Price (USD)`
- No other model cited this source

**4. GitHub Static Datasets as a Source Category**
- Concept: curated Bitcoin datasets committed to repos
- Example: `https://github.com/sr-gi/bitcoin-blocks`
- Gemini introduced this as a source category, not just individual APIs

---

### What GPT-4o Found That Others Missed

**1. CoinMarketCap Free Tier (with Caveats)**
- URL: `https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest`
- Auth: Free API key at `https://coinmarketcap.com/api/`
- Rate Limit: 10,000 calls/month on free tier
- Key Fields: Historical OHLCV, circulating supply, market cap
- **Note:** Free tier has significant data restrictions — historical OHLCV requires paid plan. GPT-4o listed this without adequately flagging the limitation. Treat with skepticism for historical halving cycle data.

**2. Bitcoin Core Node RPC via Python Library**
- GPT-4o specifically cited `python-bitcoinrpc` library (`bitcoinrpc.authproxy.AuthServiceProxy`)
- Provided cleaner Python implementation than other models
- URL: `https://developer.bitcoin.org/reference/rpc/`

**3. Most Explicit Rate Limit Documentation**
- GPT-4o was most precise about Blockchain.com's "1 request per second" enforcement
- Added important context: caching is recommended given strict limits

---

### What Grok Found That Others Missed

**1. Mempool.space Hashrate Endpoint**
- URL: `https://mempool.space/api/v1/mining/hashrate/3y`
- Key Fields: Hashrate over time, difficulty over time
- **Halving Relevance:** Hashrate trajectory predicts miner capitulation phases within cycle — post-halving hashrate drops signal miner stress, recovery signals renewed confidence

**2. Stock-to-Flow Ratio as Computed Signal (Not Just Data)**
- Grok explicitly modeled S2F = `circulating_supply / annual_new_issuance`
- Annual new issuance = `block_subsidy * 52,560` (blocks/year at 10 min/block)
- This is a **derived signal** from free data, not available as a direct free API endpoint

**3. Blockchain.com Circulating Supply Endpoint Specifically Cited**
- URL: `https://api.blockchain.info/charts/total-bitcoins?timespan=all&format=json`
- Grok was alone in explicitly connecting this to S2F computation

**4. Most Complete Rate Limit Honesty**
- Grok flagged that Mempool.space has no official documented rate limit — others implied limits without sourcing them
- Added caveat that CoinGecko free tier varies "10–50 req/min based on server load" — more accurate than Gemini's "10–30"

---

## SECTION 4: PRIORITY RANKINGS

### P0 — Mission Critical (Build First, Use Daily)

| Rank | Source | Why P0 |
|------|--------|--------|
| P0-1 | **Mempool.space `/api/v1/blocks/tip/height`** | Block height = ground truth of cycle position. No auth. Real-time. |
| P0-2 | **Mempool.space `/api/v1/difficulty-adjustment`** | Direct cycle progress percentage. Unique to Gemini's audit. |
| P0-3 | **Blockchain.com `/charts/total-bitcoins`** | Circulating supply enables S2F computation and emission schedule verification |
| P0-4 | **Blockchain.info `/q/getblockcount`** | Backup block height source. Single integer response. Zero parsing overhead. |

**Rule:** If you can only use 4 sources, use these. They give you: current cycle position (%), blocks remaining to halving, circulating supply, and a redundant height check.

---

### P1 — High Value (Add Within First Sprint)

| Rank | Source | Why P1 |
|------|--------|--------|
| P1-1 | **CoinGecko Market Chart** | Historical price across all 4 cycles. Enables cycle-normalized price analysis. |
| P1-2 | **FRED API (M2SL + WALCL)** | Macro liquidity context — halving signal is much stronger in loose monetary conditions |
| P1-3 | **Alternative.me F&G Index** | Sentiment overlay on cycle position — powerful combined signal |
| P1-4 | **Mempool.space `/api/v1/mining/hashrate/3y`** | Hashrate trajectory reveals miner phase within cycle |

---

### P2 — Nice to Have (Add in Second Sprint)

| Rank | Source | Why P2 |
|------|--------|--------|
| P2-1 | **yfinance BTC-USD** | OHLCV backup, useful for volatility calculations; fragile as unofficial scraper |
| P2-2 | **BitcoinCharts CSV dumps** | Historical tick data for cycles 1–3; static file, no maintenance needed |
| P2-3 | **Bitcoinity CSV export** | Additional historical price series; redundant but useful for cross-validation |
| P2-4 | **FRED DGS10 + DTWEXBGS** | Dollar strength and yield curve as macro modifiers |
| P2-5 | **Bitcoin Core Node RPC** | Ground truth but requires infrastructure investment |

---

## SECTION 5: PYTHON CODE — PRIMARY FREE DATA FETCH (No API Key Required)

```python
"""
Bitcoin Halving Cycle Position Signal
Primary Free Data Fetch — No API Keys Required
Synthesized from 3 LLM Audits (Gemini, GPT-4o, Grok)
"""

import requests
import time
from datetime import datetime, timezone
from typing import Dict, Any

# ============================================================
# CONSTANTS
# ============================================================
BLOCKS_PER_HALVING = 210_000
HALVING_BLOCK_HEIGHTS = [0, 210_000, 420_000, 630_000, 840_000, 1_050_000]
INITIAL_SUBSIDY_BTC = 50.0
APPROX_BLOCKS_PER_YEAR = 52_560  # 6 blocks/hr * 24 * 365

# ============================================================
# P0: BLOCK HEIGHT + CYCLE POSITION (Mempool.space)
# ============================================================

def get_block_height() -> int:
    """
    P0 Primary: Current Bitcoin block height.
    Source: Mempool.space API
    Auth: None | Rate: ~10 req/min
    """
    url = "https://mempool.space/api/v1/blocks/tip/height"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return int(response.text.strip())
    except Exception as e:
        print(f"[WARN] Mempool primary height failed: {e}. Trying backup...")
        return get_block_height_backup()

def get_block_height_backup() -> int:
    """
    P0 Backup: Blockchain