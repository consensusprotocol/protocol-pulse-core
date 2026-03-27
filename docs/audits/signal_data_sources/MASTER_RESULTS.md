# SIGNAL DATA SOURCE AUDIT - MASTER RESULTS

Generated: 2026-03-26 06:33 ET

## Miner Conviction
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
| 2 | Mempool.space Difficulty | `https://mempool.space/api/v1/difficulty-adjustment` | None | ~10 req/min | `progressPercent`, `difficultyChange`, `estimatedRetargetDate`, `remainingBlocks`, `previousRetar

---

## Exchange Pressure
# MASTER DATA SOURCE REPORT: Bitcoin Exchange Pressure Signal

---

## SECTION 1: UNANIMOUS & MAJORITY FREE SOURCES (ALL MODELS AGREED)

### UNANIMOUS SOURCES (All 3 Models Identified)

| # | Name | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Consensus Quality |
|---|------|-----------|------|------------|------------|-------------|-------------------|
| 1 | **Mempool.space Address API** | `https://mempool.space/api/address/{ADDRESS}` | None | ~10 req/min | `chain_stats.funded_txo_sum`, `chain_stats.spent_txo_sum`, `balance`, `txs` | Real-time (~10min blocks) | 9/10 |
| 2 | **Blockchain.com Netflow Chart** | `https://api.blockchain.info/charts/exchange-netflow?timespan=30days&format=json` | None | ~1 req/10sec | `values[].x` (timestamp), `values[].y` (BTC netflow) | Daily | 7/10 |
| 3 | **DIY Coinbase Premium Index** | Binance: `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` + Coinbase: `https://api.coinbase.com/v2/prices/BTC-USD/spot` | None | Binance: 1200/min; Coinbase: 10/sec | `price` (both endpoints, compute spread) | Real-time | 8/10 |
| 4 | **CryptoQuant Free Tier** | `https://api.cryptoquant.com/v1/btc/exchange-flows/netflow` | Free API Key | 60

---

## Lightning Adoption
# MASTER DATA SOURCE REPORT: LIGHTNING ADOPTION SIGNAL
**Classification:** Intelligence Synthesis | **Sources Audited:** 3 LLM Outputs | **Signal:** Lightning Network Adoption

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Confirmed)

These sources appeared across all three audits. Highest confidence in availability and reliability.

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Consensus Quality |
|--------|-----------|------|------------|------------|-------------|-------------------|
| Mempool.space Latest Stats | `https://mempool.space/api/v1/lightning/statistics/latest` | None | ~10 req/min (soft) | `total_capacity_btc`, `channel_count`, `node_count`, `tor_nodes`, `clearnet_nodes` | ~10 min | 9.3/10 |
| Mempool.space Historical | `https://mempool.space/api/v1/lightning/statistics/30d` | None | ~10 req/min (soft) | `total_capacity_btc[]`, `channel_count[]`, `avg_capacity_btc`, `med_capacity_btc` | Static pull | 9.3/10 |
| Mempool.space Node Rankings | `https://mempool.space/api/v1/lightning/nodes/rankings/capacity` | None | ~10 req/min (soft) | `publicKey`, `alias`, `capacity`, `channels`, `city`, `country` | Near real-time | 9.0/10 |
| 1ML Statisti

---

## Narrative Velocity
# MASTER DATA SOURCE REPORT: Bitcoin Narrative Velocity
## Synthesized from Gemini + GPT-4o + Grok Audits

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agreed)

These sources appeared across all three audits with consistent metadata. Highest confidence tier.

---

### SOURCE U-1: Reddit API / Pushshift

| Field | Value |
|---|---|
| **Primary URL** | `https://www.reddit.com/r/bitcoin/new.json` |
| **Pushshift URL** | `https://api.pushshift.io/reddit/search/submission/?subreddit=bitcoin` |
| **Auth** | OAuth2 for PRAW; None for raw JSON endpoint |
| **Rate Limit** | 60 req/min (authenticated PRAW); ~30 req/min (raw) |
| **Key Fields** | `title`, `selftext`, `score`, `num_comments`, `created_utc`, `upvote_ratio` |
| **Update Freq** | Real-time |
| **Subreddits** | r/Bitcoin, r/BitcoinMarkets, r/btc, r/CryptoCurrency |
| **Quality** | 8/10 |
| **Velocity Signal** | Comment velocity delta, score acceleration, crosspost spread rate |

**Critical Notes:**
- Pushshift availability is volatile as of 2024 — fallback to native Reddit API
- `created_utc` field is essential for time-series second derivative calculation
- `num_comments` growth rate over 1h/4h windows is stronger signal th

---

## On-Chain Accumulation
# MASTER DATA SOURCE REPORT: FREE BITCOIN ON-CHAIN ACCUMULATION SIGNALS

---

## SECTION 1: UNANIMOUS & MAJORITY FREE SOURCES (ALL MODELS AGREED)

### UNANIMOUS SOURCES (3/3 Models)

---

#### SOURCE U-1: Blockchain.com Charts API
| Field | Value |
|-------|-------|
| **Exact URL** | `https://api.blockchain.info/charts/{chart-name}?format=json&timespan={timespan}` |
| **Auth** | None required |
| **Rate Limit** | ~10 req/min (unenforced, self-throttle to 1 req/10sec) |
| **Update Freq** | Daily |
| **Quality Score** | 8/10 |

**Key Accumulation Endpoints:**
```
https://api.blockchain.info/charts/coin-days-destroyed?timespan=1year&format=json
https://api.blockchain.info/charts/utxo-count?timespan=1year&format=json
https://api.blockchain.info/charts/n-unique-addresses?timespan=1year&format=json
https://api.blockchain.info/charts/total-bitcoins?timespan=1year&format=json
https://api.blockchain.info/charts/estimated-transaction-volume-usd?timespan=1year&format=json
https://api.blockchain.info/charts/miners-revenue?timespan=1year&format=json
https://api.blockchain.info/charts/n-transactions?timespan=1year&format=json
```

**Key Fields:** `x` (Unix timestamp), `y` (metric value)

**Accum

---

## Halving Cycle Position
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

**Why it matters:** Every halving cycle calculation derives from block height. 210,000 blocks per epoch. Current height mod 210,000 = exact position in cycle. No API key, no rate limit e

---

## Regulatory Pressure
# MASTER DATA SOURCE REPORT: Bitcoin Regulatory Pressure Signal

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agreed)

These sources appeared across Gemini, GPT-4o, and Grok — highest confidence tier.

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Consensus Quality |
|--------|-----------|------|------------|------------|-------------|-------------------|
| Congress.gov API | `https://api.congress.gov/v3/bill?format=json` | API Key (Free at api.congress.gov/sign-up) | 1,000 req/hr | `title`, `latestAction.text`, `policyArea.name`, `sponsors`, `cosponsors.count` | Daily | 9/10 |
| SEC EDGAR Full-Text | `https://efts.sec.gov/LATEST/search-index` | None | ~10 req/sec (be conservative) | Filing text, `form` type (S-1, 19b-4, 497), `accessionNumber`, `cik` | Near real-time | 8/10 |
| Federal Register API | `https://www.federalregister.gov/api/v1/documents.json` | None | Generous, undocumented | `title`, `publication_date`, `agencies.name`, `abstract`, `html_url`, `document_number` | Daily | 9/10 |
| CFTC Press Releases | `https://www.cftc.gov/rss/PressRoom.xml` | None | N/A (RSS) | `title`, `link`, `pubDate`, `description` | As-needed | 7/10 |
| iShares IBI

---

## Macro Correlation
# MASTER DATA SOURCE REPORT
## Bitcoin Macro Correlation Signal — Free Data Pipeline Audit
### Synthesized from 3 LLM Audits (Gemini, GPT-4o, Grok)

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agreed)

These sources appeared across all three audits. Highest confidence in reliability and signal value.

---

### SOURCE U-1: FRED API
**Unanimous across Gemini, GPT-4o, Grok**

| Field | Detail |
|---|---|
| **Base URL** | `https://api.stlouisfed.org/fred/series/observations` |
| **Auth** | Free API key — register at `https://fred.stlouisfed.org/docs/api/api_key.html` |
| **Rate Limit** | 120 requests/min, ~1,000/day on free tier |
| **Key Series IDs** | `DGS10` (10yr Treasury Yield), `DTWEXBGS` (DXY Broad), `M2SL` (M2 Money Supply), `GOLDAMGBD228NLBM` (Gold Fix), `WALCL` (Fed Balance Sheet), `FEDFUNDS` (Fed Funds Rate), `CPIAUCSL` (CPI), `T10YIE` (10yr Breakeven Inflation) |
| **Key Fields Returned** | `date`, `value`, `realtime_start`, `realtime_end` |
| **Update Frequency** | Daily (yields), Weekly (M2, Fed Balance Sheet), Monthly (CPI) |
| **Quality Score** | Gemini: 10/10 · GPT-4o: 9/10 · Grok: 10/10 · **Consensus: 9.7/10** |
| **Priority** | **P0** |

**Why it matters for m

---

## Options Market
# MASTER DATA SOURCE REPORT: FREE BITCOIN OPTIONS MARKET INTELLIGENCE

---

## SECTION 1: UNANIMOUS & MAJORITY FREE SOURCES (ALL THREE MODELS AGREED)

### UNANIMOUS SOURCES (3/3 Models)

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Quality | Consensus Score |
|--------|-----------|------|------------|------------|-------------|---------|-----------------|
| **Deribit Book Summary** | `https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option` | None | 20 req/s | `instrument_name`, `open_interest`, `mark_iv`, `bid_iv`, `ask_iv`, `volume`, `underlying_price` | ~8ms real-time | 10/10 | ★★★ |
| **Deribit Instruments** | `https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option&expired=false` | None | 20 req/s | `instrument_name`, `expiration_timestamp`, `strike`, `option_type`, `is_active` | On demand | 10/10 | ★★★ |
| **Deribit DVOL Index** | `https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=1` | None | 20 req/s | `volatility`, `timestamp`, resolution options: 1/60/3600/43200 | 1 min | 9/10 | ★★★ |
| **OKX Open Interest** | `https://www.okx.com/api/v5/public/open-int

---

## Futures Basis
# MASTER DATA SOURCE REPORT: Bitcoin Futures Basis Signal
## Synthesized from 3 LLM Audits + Gap Analysis

---

## SECTION 1: UNANIMOUS SOURCES (All 3 Models Agree)

These are the highest-confidence sources. All three models independently verified these endpoints.

### TIER 1 PRIMARY — UNANIMOUS

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Consensus Quality |
|--------|-----------|------|------------|------------|-------------|-------------------|
| Binance Funding Rate | `https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1000` | None | 1200 req/min | `fundingRate`, `fundingTime` | 8 hours | 10/10 |
| Binance Open Interest | `https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT` | None | 1200 req/min | `openInterest` | Real-time | 9/10 |
| Binance Top L/S Position Ratio | `https://fapi.binance.com/fapi/v1/topLongShortPositionRatio?symbol=BTCUSDT&period=5m` | None | 1200 req/min | `longShortRatio`, `longPosition`, `shortPosition` | 5 min | 9/10 |
| Binance Global L/S Ratio | `https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m` | None | 1200 req/min | `longShortRatio`, `longAccount`, `shortAccount` |

---

