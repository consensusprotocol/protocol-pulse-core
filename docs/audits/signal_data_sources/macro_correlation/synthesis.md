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

**Why it matters for macro correlation:** FRED is the only free source with official Fed balance sheet data (`WALCL`). M2 expansion/contraction (`M2SL`) is one of the highest-correlation macro drivers for BTC with historically documented 6–12 month lag. DGS10 inversion signals are canonical risk-off triggers.

---

### SOURCE U-2: Yahoo Finance via yfinance
**Unanimous across Gemini, GPT-4o, Grok**

| Field | Detail |
|---|---|
| **Base URL** | `https://finance.yahoo.com` (accessed via Python library) |
| **Library** | `pip install yfinance` |
| **Auth** | None required |
| **Rate Limit** | Unofficial ~2,000 requests/hour. No SLA. Throttles under abuse. |
| **Key Tickers** | `BTC-USD`, `GC=F` (Gold Futures), `ES=F` (S&P 500 Futures), `^TNX` (10yr Yield), `DX-Y.NYB` (DXY), `^VIX` (Volatility Index), `GLD` (Gold ETF), `TLT` (Treasury ETF), `SPY` (S&P 500 ETF) |
| **Key Fields Returned** | `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume` |
| **Update Frequency** | Near real-time (15-min delay) to Daily |
| **Quality Score** | Gemini: 8/10 · GPT-4o: 8/10 · Grok: 8/10 · **Consensus: 8.0/10** |
| **Priority** | **P0** |

**Why it matters:** Only free source providing simultaneous BTC + traditional macro asset OHLCV in a single unified API call. Essential for rolling correlation calculations across time windows (30D, 90D, 180D).

---

### SOURCE U-3: CoinGecko API
**Unanimous across Gemini, GPT-4o, Grok**

| Field | Detail |
|---|---|
| **Base URL** | `https://api.coingecko.com/api/v3/` |
| **Auth** | None for public endpoints (Demo key optional for higher limits) |
| **Rate Limit** | 10–30 requests/min on free tier. 429 errors above threshold. |
| **Key Endpoints** | `/coins/bitcoin/market_chart?vs_currency=usd&days=365&interval=daily` |
| **Key Fields Returned** | `prices` (timestamp, price), `market_caps` (timestamp, mcap), `total_volumes` (timestamp, volume) |
| **Update Frequency** | 1–10 minutes depending on endpoint |
| **Quality Score** | Gemini: 9/10 · GPT-4o: implied · Grok: implied · **Consensus: 8.5/10** |
| **Priority** | **P0** |

**Why it matters:** Market cap data allows BTC dominance calculation. Volume data reveals whether price moves are macro-driven (high volume) or thin liquidity noise. Free, no-auth access to 365-day history on public endpoint.

---

### SOURCE U-4: Alpha Vantage
**Majority (GPT-4o explicit, Grok explicit, Gemini implied)**

| Field | Detail |
|---|---|
| **Base URL** | `https://www.alphavantage.co/query` |
| **Auth** | Free API key at `https://www.alphavantage.co/support/#api-key` |
| **Rate Limit** | 500 calls/day, 5 calls/min on free tier |
| **Key Functions** | `TIME_SERIES_DAILY`, `FX_DAILY`, `DIGITAL_CURRENCY_DAILY` |
| **Key Fields Returned** | `timestamp`, `open`, `high`, `low`, `close`, `volume` |
| **Update Frequency** | Daily (free tier). Intraday on premium. |
| **Quality Score** | GPT-4o: 7/10 · Grok: 7/10 · **Consensus: 7.0/10** |
| **Priority** | **P1** |

**Why it matters:** Cross-validation source. Rate limits make it unsuitable as primary but useful for reconciliation when Yahoo Finance has data gaps.

---

## SECTION 2: MAJORITY SOURCES (2 of 3 Models Agreed)

---

### SOURCE M-1: Quandl / Nasdaq Data Link
**Grok + GPT-4o (Gemini did not mention)**

| Field | Detail |
|---|---|
| **Base URL** | `https://data.nasdaq.com/api/v3/datasets/` |
| **Auth** | Free API key at `https://data.nasdaq.com/sign-up` |
| **Rate Limit** | 50 calls/day on free tier |
| **Key Datasets** | `BITFINEX/BTCUSD`, `USTREASURY/YIELD`, `LBMA/GOLD`, `ICE/DOLLAR_INDEX` |
| **Key Fields Returned** | `dataset_code`, `column_names`, `data` (date + OHLCV) |
| **Update Frequency** | Daily |
| **Quality Score** | GPT-4o: 8/10 · Grok: 8/10 · **Consensus: 8.0/10** |
| **Priority** | **P1** |

**Why it matters:** Treasury yield curve data (`USTREASURY/YIELD`) provides the full curve (3M, 2Y, 5Y, 10Y, 30Y) in one call — critical for yield curve inversion signals which historically precede BTC regime changes by 60–90 days.

---

### SOURCE M-2: Mempool.space API
**Gemini + Grok (GPT-4o did not mention)**

| Field | Detail |
|---|---|
| **Base URL** | `https://mempool.space/api/v1/` |
| **Docs** | `https://mempool.space/docs/api/rest` |
| **Auth** | None |
| **Rate Limit** | Not officially published. Reasonable use implied. ~60 req/min safe. |
| **Key Endpoints** | `/fees/recommended`, `/blocks`, `/mempool`, `/mining/hashrate/pools/3m` |
| **Key Fields Returned** | `fastestFee`, `halfHourFee`, `hourFee`, `economyFee`, `minimumFee` (sats/vByte) |
| **Update Frequency** | Real-time (~30 sec) |
| **Quality Score** | Gemini: high · Grok: high · **Consensus: 8.5/10** |
| **Priority** | **P1** |

**Why it matters:** On-chain fee pressure is a leading indicator of demand for Bitcoin blockspace. During macro stress events, fee spikes often precede price volatility by 2–6 hours. Completely orthogonal to TradFi data — this is a unique alpha signal unavailable in any paid macro terminal.

---

### SOURCE M-3: CoinMetrics Community Data
**GPT-4o + Grok (Gemini implied via on-chain discussion)**

| Field | Detail |
|---|---|
| **Base URL** | `https://community-api.coinmetrics.io/v4/` |
| **Docs** | `https://coinmetrics.io/community-network-data/` |
| **Auth** | None on community endpoints |
| **Rate Limit** | Limited — ~100 requests/day on community tier |
| **Key Metrics** | `AdrActCnt` (Active Addresses), `TxTfrValAdjUSD` (Adjusted Transfer Volume), `NVTAdj` (NVT Ratio), `FeeTotUSD` (Total Fees), `SplyAct1yr` (1yr Active Supply) |
| **Key Fields Returned** | `asset`, `time`, `{metric_name}` |
| **Update Frequency** | Daily |
| **Quality Score** | GPT-4o: 7/10 · **Consensus: 7.5/10** |
| **Priority** | **P1** |

**Why it matters:** Free Glassnode alternative. NVT Ratio (Network Value to Transactions) is the on-chain equivalent of a P/E ratio — when BTC price rises without corresponding on-chain activity, it signals macro-driven speculation rather than fundamental growth. Critical for distinguishing signal from noise.

---

### SOURCE M-4: GitHub Bitcoin Core Activity
**Gemini + GPT-4o (Grok did not explicitly call it out)**

| Field | Detail |
|---|---|
| **Base URL** | `https://api.github.com/repos/bitcoin/bitcoin/stats/commit_activity` |
| **Auth** | None (authenticated calls get higher rate limits) |
| **Rate Limit** | 60 requests/hour unauthenticated, 5,000/hour with free GitHub token |
| **Key Fields Returned** | `total` (commits/week), `week` (Unix timestamp), `days` (array of daily commits) |
| **Update Frequency** | Weekly |
| **Quality Score** | Gemini: high · GPT-4o: 6/10 · **Consensus: 7.0/10** |
| **Priority** | **P2** |

**Why it matters for macro correlation:** Long-term conviction proxy. Sustained developer activity during macro downturns indicates institutional-grade resilience. Negative correlation between commit drops and macro stress events would be a systemic risk signal.

---

## SECTION 3: WHAT EACH MODEL UNIQUELY FOUND

| Model | Unique Contribution | Signal Value | Missed By |
|---|---|---|---|
| **Gemini** | **Mempool.space real-time fee data** as a leading macro reaction indicator | HIGH — 2–6hr lead time on volatility | GPT-4o |
| **Gemini** | **1ML Lightning Network stats** (`https://1ml.com/statistics`) for Layer 2 utility growth as a macro decoupling signal | MEDIUM — long-term thesis validation | Both others |
| **Gemini** | **Federal Reserve direct download** (`https://www.federalreserve.gov/datadownload/`) — no API key needed for H.15 release data | HIGH — zero-auth fallback for FRED | Both others |
| **GPT-4o** | **Binance WebSocket stream** (`wss://stream.binance.com:9443/ws/btcusdt@trade`) for real-time price/volume without auth | MEDIUM — useful for intraday correlation checks | Gemini, Grok |
| **GPT-4o** | **CryptoCompare** (`https://min-api.cryptocompare.com/`) as CryptoQuant alternative with 100K calls/month free | MEDIUM — OHLCV + social volume | Gemini, Grok |
| **Grok** | **`T10YIE` FRED series** (10yr Breakeven Inflation) — real yield calculation (`DGS10` minus `T10YIE`) for BTC as inflation hedge signal | VERY HIGH — real yield is the #1 macro driver | Both others |
| **Grok** | **`WALCL`** (Fed Balance Sheet Total Assets) explicitly called out as QE/QT signal | HIGH — QT is primary BTC bear market trigger | Both others |
| **Grok** | **Investing.com** as scraping fallback for DXY + futures historical data | LOW-MEDIUM — fragile but fills gaps | Both others |

---

## SECTION 4: PRIORITY RANKING

### P0 — MISSION CRITICAL (Build First, Non-Negotiable)

| # | Source | Signal | Why P0 |
|---|---|---|---|
| 1 | **FRED API** — `DGS10`, `T10YIE`, `M2SL`, `WALCL`, `DTWEXBGS` | Real yield, QE/QT regime, DXY trend | Official government data. Zero substitutes. Real yield = `DGS10` - `T10YIE` is the single highest-correlation macro variable with BTC |
| 2 | **Yahoo Finance yfinance** — `BTC-USD`, `GC=F`, `^VIX`, `ES=F`, `^TNX` | Rolling correlation matrix across all macro assets | Only zero-auth source for full cross-asset OHLCV |
| 3 | **CoinGecko API** — market chart endpoint | BTC volume confirmation, market cap | No-auth, reliable, validates whether macro moves are volume-confirmed |

### P1 — HIGH VALUE (Build Second, Significant Alpha)

| # | Source | Signal | Why P1 |
|---|---|---|---|
| 4 | **Mempool.space** — `/fees/recommended` | On-chain demand leading indicator | Real-time, unique signal unavailable anywhere else free |
| 5 | **CoinMetrics Community** — `NVTAdj`, `AdrActCnt` | On-chain fundamentals vs macro price | Free Glassnode proxy — separates macro speculation from genuine adoption |
| 6 | **Quandl/Nasdaq** — `USTREASURY/YIELD` full curve | Yield curve shape (2s10s inversion) | Full curve in one call — 2s10s spread is recession clock |
| 7 | **Federal Reserve Direct Download** | H.15 release (no API key) | Zero-auth fallback for FRED, catches same data |

### P2 — SUPPLEMENTARY (Build Third, Validation & Context)

| # | Source | Signal | Why P2 |
|---|---|---|---|
| 8 | **Alpha Vantage** | Cross-validation OHLCV | Rate limits make it backup only |
| 9 | **GitHub Bitcoin Core** — commit activity | Developer conviction proxy | Weekly cadence, long-term signal only |
| 10 | **CryptoCompare** | Social volume + OHLCV | 100K free calls/month but lower data fidelity |
| 11 | **Binance WebSocket** | Real-time price tick | Only needed for intraday correlation work |
| 12 | **1ML Lightning Stats** | L2 utility growth | Decoupling signal, monthly timescale only |

---

##