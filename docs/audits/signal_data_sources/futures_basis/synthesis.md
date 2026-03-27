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
| Binance Global L/S Ratio | `https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m` | None | 1200 req/min | `longShortRatio`, `longAccount`, `shortAccount` | 5 min | 8/10 |
| Binance Liquidations | `https://fapi.binance.com/fapi/v1/allForceOrders?symbol=BTCUSDT&limit=100` | None | 1200 req/min | `price`, `origQty`, `side` | Real-time | 8/10 |
| Bybit Funding History | `https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=200` | None | 120 req/min | `fundingRate`, `fundingRateTimestamp` | 8 hours | 9/10 |
| OKX Funding Rate | `https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USD-SWAP` | None | 20 req/sec | `fundingRate`, `fundingTime`, `nextFundingRate` | 8 hours | 8/10 |

---

## SECTION 2: MAJORITY SOURCES (2 of 3 Models Found)

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Found By |
|--------|-----------|------|------------|------------|-------------|----------|
| Binance Top L/S Account Ratio | `https://fapi.binance.com/fapi/v1/topLongShortAccountRatio?symbol=BTCUSDT&period=5m` | None | 1200 req/min | `longShortRatio`, `longAccount`, `shortAccount` | 5 min | Gemini + Grok |
| Bybit Open Interest | `https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=5min` | None | 120 req/min | `openInterest`, `timestamp` | 5 min | Gemini + Grok |
| OKX Open Interest | `https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USD-SWAP` | None | 20 req/sec | `oi`, `oiCcy`, `ts` | Real-time | GPT4o + Grok |
| CME Bitcoin Futures | `https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.html` | None | Scrape only | Settlement prices, term structure | Daily | GPT4o + Grok |
| Coinglass Aggregated | `https://open-api.coinglass.com/public/v2/funding` | Free API key | 10 req/min | Cross-exchange funding rates | Real-time | GPT4o + Grok |

---

## SECTION 3: UNIQUE FINDINGS PER MODEL

### What GEMINI Found That Others Missed

**1. Annualized Basis Formula — Explicit Calculation Framework**
No other model provided this. Critical for signal normalization:
```
Annualized Rate % = fundingRate × 3 × 365 × 100
(for 8-hour Binance funding cycles = 3 periods/day)
```

**2. Futures Term Structure Signal — Contango vs Backwardation**
Gemini was the only model to explicitly flag the **shape of the curve** as a distinct signal layer:
- Contango (futures > spot) = healthy bull
- Backwardation (futures < spot) = panic/capitulation signal
- Endpoint for Binance quarterly futures mark price:
  `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT_251226`

**3. Side Field Decoding on Liquidations**
```
BUY = short liquidation (short squeezed out)
SELL = long liquidation (long blown out)
```
Only Gemini explicitly documented this reversal which is counterintuitive and commonly misread.

**4. OI Confirmation Framework**
- Rising OI + Rising Price = Bullish confirmation
- Rising OI + Falling Price = Bearish confirmation
- Falling OI + Any direction = Deleveraging, trend weakening

---

### What GPT-4o Found That Others Missed

**1. CME Group as Institutional Basis Source**
URL: `https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.html`
CME futures represent **institutional money** and carry a different basis premium than perp markets. The spread between CME futures and spot is the **"CME Premium"** — a unique institutional sentiment gauge not available on crypto-native exchanges. GPT-4o was the only model to flag this.

**2. Nostr Relays as Alternative Data Feed**
Unconventional but noted: decentralized financial data broadcast via Nostr protocol. Experimental but worth monitoring for crowdsourced derivatives commentary.

**3. Explicit Python Function Structure**
GPT-4o provided the cleanest modular function pattern for multi-exchange aggregation, making it the most copy-paste-ready output for rapid prototyping.

---

### What GROK Found That Others Missed

**1. Binance OI History Endpoint (Not Just Spot OI)**
```
https://fapi.binance.com/fapi/v1/openInterestHist?symbol=BTCUSDT&period=5m&limit=500
```
This returns **historical OI timeseries** — critical for trend analysis. The other models only cited the real-time snapshot endpoint. This is a major gap they missed.

**2. Bybit L/S Ratio (Not Just Funding)**
```
https://api.bybit.com/v5/market/account-ratio?category=linear&symbol=BTCUSDT&period=1h&limit=200
```

**3. Rate Limit Precision**
Grok provided the most precise rate limit data:
- Binance FAPI: 1200 req/min per IP (weight-based system)
- Bybit: 120 req/min per IP
- OKX: 20 req/sec per IP

**4. Deribit for Options-Derived Basis**
```
https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=future
```
Auth: None | Rate Limit: 20 req/sec
Key Fields: `mark_price`, `underlying_price`, `basis` (direct field)
**Only Grok identified Deribit as a free source with a native `basis` field** — this is the most direct futures basis data point in the entire audit.

---

## SECTION 4: COMPLETE MASTER URL TABLE WITH PRIORITY RANKING

### P0 — CRITICAL (Build Without These = No Signal)

| Priority | Source | Exact URL | Auth | Rate Limit | Key Basis Fields |
|----------|---------|-----------|------|------------|-----------------|
| P0 | Binance Perp Funding Rate | `https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1000` | None | 1200/min | `fundingRate`, `fundingTime` |
| P0 | Binance Mark Price (Basis Calc) | `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT` | None | 1200/min | `markPrice`, `indexPrice`, `lastFundingRate` |
| P0 | Binance Spot Price | `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` | None | 1200/min | `price` |
| P0 | Binance OI Historical | `https://fapi.binance.com/fapi/v1/openInterestHist?symbol=BTCUSDT&period=5m&limit=500` | None | 1200/min | `sumOpenInterest`, `sumOpenInterestValue` |
| P0 | Deribit Futures Basis (Direct) | `https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=future` | None | 20 req/sec | `basis`, `mark_price`, `underlying_price` |
| P0 | Bybit Funding History | `https://api.bybit.com/v5/market/funding/history?category=linear&symbol=BTCUSDT&limit=200` | None | 120/min | `fundingRate`, `fundingRateTimestamp` |

### P1 — HIGH VALUE (Add After P0 Stable)

| Priority | Source | Exact URL | Auth | Rate Limit | Key Fields |
|----------|---------|-----------|------|------------|------------|
| P1 | OKX Funding Rate | `https://www.okx.com/api/v5/public/funding-rate?instId=BTC-USD-SWAP` | None | 20 req/sec | `fundingRate`, `nextFundingRate` |
| P1 | Binance Liquidations | `https://fapi.binance.com/fapi/v1/allForceOrders?symbol=BTCUSDT&limit=100` | None | 1200/min | `price`, `origQty`, `side` |
| P1 | Binance Top L/S Position | `https://fapi.binance.com/fapi/v1/topLongShortPositionRatio?symbol=BTCUSDT&period=5m` | None | 1200/min | `longShortRatio` |
| P1 | Binance Global L/S Ratio | `https://fapi.binance.com/fapi/v1/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m` | None | 1200/min | `longShortRatio` |
| P1 | Bybit L/S Account Ratio | `https://api.bybit.com/v5/market/account-ratio?category=linear&symbol=BTCUSDT&period=1h&limit=200` | None | 120/min | `buyRatio`, `sellRatio` |
| P1 | OKX Open Interest | `https://www.okx.com/api/v5/public/open-interest?instType=SWAP&instId=BTC-USD-SWAP` | None | 20 req/sec | `oi`, `oiCcy` |
| P1 | Deribit BTC Options Summary | `https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option` | None | 20 req/sec | `mark_iv`, `underlying_price` |

### P2 — SUPPLEMENTARY (Enrichment Layer)

| Priority | Source | Exact URL | Auth | Rate Limit | Key Fields |
|----------|---------|-----------|------|------------|------------|
| P2 | CME BTC Futures (Scrape) | `https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.html` | None | Scrape | Settlement, term structure |
| P2 | Coinglass Funding Agg | `https://open-api.coinglass.com/public/v2/funding` | Free Key | 10 req/min | Cross-exchange funding |
| P2 | Binance Quarterly Futures | `https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT_251226` | None | 1200/min | `markPrice`, `indexPrice` |
| P2 | Bybit Open Interest Hist | `https://api.bybit.com/v5/market/open-interest?category=linear&symbol=BTCUSDT&intervalTime=5min` | None | 120/min | `openInterest`, `timestamp` |

---

## SECTION 5: PRODUCTION PYTHON CODE — NO API KEY REQUIRED

```python
"""
Bitcoin Futures Basis Signal Aggregator
Sources: Binance FAPI, Bybit, OKX, Deribit
No API keys required for any endpoint
"""

import requests
import time
import json
from datetime import datetime, timezone
from typing import Optional

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BasisSignalBot/1.0)",
    "Accept": "application/json"
}
TIMEOUT = 10  # seconds

# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────
def safe_get(url: str, params: dict = None) -> Optional[dict]:
    """Safe HTTP GET with error handling and rate limit respect."""
    try:
        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"[HTTP ERROR] {url} → {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"[CONN ERROR] {url} → {e}")
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] {url}")
    except json.JSONDecodeError:
        print(f"[JSON ERROR] {url}")
    return None


def annualize_funding(rate: float, periods_per_day: int = 3) -> float:
    """
    Convert raw funding rate to annualized percentage.
    Binance/Bybit/OKX default = 8-hour intervals = 3 periods/day.
    Formula: rate × periods_per_day × 365 × 100
    """
    return rate * periods_per_day * 365 * 100


# ─────────────────────────────────────────────
# P0: BINANCE — MARK PRICE + FUNDING (Core Basis)
# ─────────────────────────────────────────────
def get_binance_premium_index() -> dict:
    """
    Returns mark price, index price, and last funding rate.
    Basis = (markPrice - indexPrice) / indexPrice × 100
    """
    url = "https://fapi