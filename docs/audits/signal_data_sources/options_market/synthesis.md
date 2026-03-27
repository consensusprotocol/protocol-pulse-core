# MASTER DATA SOURCE REPORT: FREE BITCOIN OPTIONS MARKET INTELLIGENCE

---

## SECTION 1: UNANIMOUS & MAJORITY FREE SOURCES (ALL THREE MODELS AGREED)

### UNANIMOUS SOURCES (3/3 Models)

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Quality | Consensus Score |
|--------|-----------|------|------------|------------|-------------|---------|-----------------|
| **Deribit Book Summary** | `https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option` | None | 20 req/s | `instrument_name`, `open_interest`, `mark_iv`, `bid_iv`, `ask_iv`, `volume`, `underlying_price` | ~8ms real-time | 10/10 | ★★★ |
| **Deribit Instruments** | `https://www.deribit.com/api/v2/public/get_instruments?currency=BTC&kind=option&expired=false` | None | 20 req/s | `instrument_name`, `expiration_timestamp`, `strike`, `option_type`, `is_active` | On demand | 10/10 | ★★★ |
| **Deribit DVOL Index** | `https://www.deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=1` | None | 20 req/s | `volatility`, `timestamp`, resolution options: 1/60/3600/43200 | 1 min | 9/10 | ★★★ |
| **OKX Open Interest** | `https://www.okx.com/api/v5/public/open-interest?instType=OPTION&uly=BTC-USD` | None | 20 req/2s | `instId`, `oi`, `oiCcy`, `ts` | Real-time | 8/10 | ★★★ |
| **Binance Options OI** | `https://eapi.binance.com/eapi/v1/openInterest?underlyingAsset=BTC&expiration=241227` | None | 1200 req/min | `symbol`, `sumOpenInterest`, `timestamp` | Real-time | 7/10 | ★★★ |

### MAJORITY SOURCES (2/3 Models)

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Quality | Who Found It |
|--------|-----------|------|------------|------------|-------------|---------|--------------|
| **Deribit Historical Volatility** | `https://www.deribit.com/api/v2/public/get_historical_volatility?currency=BTC` | None | 20 req/s | `30d_vol`, `timestamp` | Daily | 9/10 | Gemini + Grok |
| **Deribit Ticker (per instrument)** | `https://www.deribit.com/api/v2/public/ticker?instrument_name=BTC-27DEC24-50000-C` | None | 20 req/s | `iv`, `oi`, `last`, `bid`, `ask`, `delta`, `gamma`, `vega`, `theta` | Real-time | 9/10 | GPT-4o + Grok |
| **CME Group FTP/Daily Bulletin** | `https://www.cmegroup.com/ftp/settle/` or `ftp://ftp.cmegroup.com/settle/` | None | Manual/Low | `strike_price`, `open_interest` (put/call split), `settlement_price` | Daily EOD | 6/10 | Gemini + GPT-4o |
| **Bybit Options Tickers** | `https://api.bybit.com/v5/market/tickers?category=option&baseCoin=BTC` | None | 10 req/s | `symbol`, `openInterest`, `impliedVolatility`, `bid1Price`, `ask1Price` | Real-time | 7/10 | Gemini + Grok |

---

## SECTION 2: UNIQUE FINDINGS BY MODEL

### GEMINI UNIQUE DISCOVERIES

**1. CME FTP Direct Access (Structured)**
- URL: `ftp://ftp.cmegroup.com/settle/btic`
- What's unique: Gemini specifically identified the raw FTP server path for the BTIC (Bitcoin Index) settlement files — not just the web page. This gives you machine-readable EOD data including put/call OI splits, settlement prices, and volume for regulated CME Bitcoin options. Institutional-grade data completely free.
- Signal value: Critical for tracking TradFi/institutional positioning which dominates large strike levels

**2. IV Skew Signal Decomposition**
- Gemini was the ONLY model to explicitly define and operationalize the **25-delta risk reversal formula**: `IV(25Δ call) - IV(25Δ put)`
- This is not a source but a derived signal construction methodology that GPT-4o and Grok omitted entirely
- Actionable: You must pull `delta` field from Deribit ticker endpoint and filter for instruments where `|delta| ≈ 0.25` to compute this correctly

**3. IV Term Structure Construction Methodology**
- Gemini explicitly defined how to build term structure: ATM options plotted across expiration dates
- Defined contango vs backwardation interpretation framework
- No other model provided this signal construction logic

---

### GPT-4O UNIQUE DISCOVERIES

**1. Bitcoin Optech Newsletter**
- URL: `https://bitcoinops.org/en/newsletters/`
- What's unique: Developer-level technical analysis from Bitcoin core contributors. Contains protocol-level intelligence that precedes market moves (e.g., Lightning capacity changes, mempool congestion signals that affect on-chain settlement costs for options)
- Signal value: Low frequency but extremely high alpha — qualitative leading indicator

**2. Nostr Protocol Relays**
- Relay example: `wss://relay.damus.io` or `wss://nos.lol`
- What's unique: Decentralized real-time information network used by Bitcoin-native traders and developers. No censorship, no delay. Trader sentiment, whale position disclosure, and market color flows through Nostr before hitting mainstream crypto Twitter
- Signal value: Unconventional sentiment layer — requires NLP processing
- Caveat: Signal-to-noise ratio is low; requires filtering by known pubkeys of credible traders

**3. CryptoQuant Free Tier as Glassnode Approximation**
- URL: `https://cryptoquant.com/`
- What's unique: GPT-4o explicitly positioned CryptoQuant's free tier as a structured alternative to paid Glassnode for on-chain metrics that correlate with options positioning (exchange flows, miner selling, funding rates)
- Free endpoint: `https://api.cryptoquant.com/v1/btc/exchange-flows` (limited free tier)

---

### GROK UNIQUE DISCOVERIES

**1. Deribit Ticker Per-Instrument Greeks**
- URL: `https://www.deribit.com/api/v2/public/ticker?instrument_name={INSTRUMENT}`
- What's unique: Grok was most explicit about pulling ALL Greeks per instrument: `delta`, `gamma`, `vega`, `theta` from the ticker endpoint. This is the data needed to construct a **GEX (Gamma Exposure)** surface — a signal that identifies dealer hedging pressure zones
- Signal construction: `GEX = gamma × OI × spot² × 0.01` summed across all strikes
- No other model mentioned GEX as a constructable free signal

**2. Most Complete Rate Limit Documentation**
- Grok provided the most precise rate limit breakdown: Binance at 1200 req/min vs Deribit at 20 req/s — actionable for pipeline architecture
- Also noted Bybit at 10 req/s limitation not flagged by others

**3. Expiration-Specific Binance Endpoint**
- URL: `https://eapi.binance.com/eapi/v1/openInterest?underlyingAsset=BTC&expiration=241227`
- What's unique: Grok flagged the expiration parameter requirement — without it the Binance endpoint returns an error. GPT-4o listed a broken version of this URL. Critical implementation detail.

---

## SECTION 3: PRIORITY RANKING

### P0 — MISSION CRITICAL (Build first, highest signal density)

| Priority | Source | Why P0 | Signals Enabled |
|----------|---------|--------|-----------------|
| **P0-1** | Deribit Book Summary API | Only free source with full OI by strike + IV for ALL active contracts in single call | OI by Strike, Put/Call Ratio, Max Pain, IV Surface |
| **P0-2** | Deribit Ticker (per instrument) | Only free source for full Greeks per contract | GEX, Vanna, Charm exposure maps |
| **P0-3** | Deribit DVOL Index | Bitcoin's VIX equivalent — free and direct | IV Term Structure baseline, Vol regime detection |
| **P0-4** | Deribit Instruments List | Required to enumerate all active contracts before querying ticker | Enables systematic polling of full surface |
| **P0-5** | Deribit Historical Volatility | Realized vol baseline required for IV premium calculation | IV vs RV spread, vol risk premium signal |

### P1 — HIGH VALUE (Add second, meaningful signal augmentation)

| Priority | Source | Why P1 | Signals Enabled |
|----------|---------|--------|-----------------|
| **P1-1** | OKX Open Interest | Second largest BTC options venue — cross-venue OI aggregation catches whales who split positions | Aggregated OI, cross-venue Put/Call |
| **P1-2** | Bybit Options Tickers | Growing venue, different participant mix than Deribit | Venue divergence signal |
| **P1-3** | Binance Options OI | Retail-heavy venue, useful for contrarian signals | Retail vs professional positioning divergence |
| **P1-4** | CME FTP Settlement Data | TradFi institutional positioning, physically separate participant base | Institutional vs crypto-native options positioning spread |

### P2 — SUPPLEMENTARY (Add third, context and edge cases)

| Priority | Source | Why P2 | Signals Enabled |
|----------|---------|--------|-----------------|
| **P2-1** | CryptoQuant Free Tier | On-chain flows that lead options positioning | Exchange inflows preceding large OI buildups |
| **P2-2** | Bitcoin Optech Newsletter | Protocol-level intelligence | Qualitative leading indicator for vol events |
| **P2-3** | Nostr Relays | Unfiltered market participant communication | Sentiment signal requiring NLP pipeline |
| **P2-4** | Deribit WebSocket Stream | Real-time streaming vs polling — reduces latency from ~2s to ~8ms | Time-sensitive gamma scalping signals |

---

## SECTION 4: PYTHON CODE — PRIMARY FREE DATA FETCH (NO API KEY)

```python
"""
Bitcoin Options Market Intelligence - Master Free Data Fetcher
No API keys required. Fetches: OI by Strike, Put/Call Ratio,
Max Pain, IV Surface, Term Structure, DVOL
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time


# ── CONFIG ────────────────────────────────────────────────────────────────────
DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
OKX_BASE     = "https://www.okx.com/api/v5/public"
BYBIT_BASE   = "https://api.bybit.com/v5/market"
HEADERS      = {"Accept": "application/json", "User-Agent": "BTC-Options-Audit/1.0"}
SLEEP        = 0.1  # 10 req/s stays well under Deribit 20 req/s limit


# ── STEP 1: FETCH ALL ACTIVE BTC OPTION INSTRUMENTS ──────────────────────────
def fetch_instruments() -> list[dict]:
    """Returns list of all active BTC option instruments from Deribit."""
    url = f"{DERIBIT_BASE}/get_instruments"
    params = {"currency": "BTC", "kind": "option", "expired": "false"}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    instruments = resp.json()["result"]
    print(f"[instruments] Found {len(instruments)} active BTC options contracts")
    return instruments


# ── STEP 2: FETCH FULL BOOK SUMMARY (OI + IV FOR ALL CONTRACTS) ──────────────
def fetch_book_summary() -> pd.DataFrame:
    """
    Single call returns OI, mark_iv, bid_iv, ask_iv, volume for ALL
    active BTC options. This is the workhorse endpoint.
    """
    url = f"{DERIBIT_BASE}/get_book_summary_by_currency"
    params = {"currency": "BTC", "kind": "option"}
    resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()["result"]

    df = pd.DataFrame(data)

    # Parse instrument name: BTC-DDMMMYY-STRIKE-TYPE
    # Example: BTC-27DEC24-50000-C
    parsed = df["instrument_name"].str.extract(
        r"BTC-(\d{1,2})([A-Z]{3})(\d{2})-(\d+)-([CP])"
    )
    parsed.columns = ["day", "month", "year", "strike", "option_type"]
    df["strike"]      = parsed["strike"].astype(float)
    df["option_type"] = parsed["option_type"].map({"C": "call", "P": "put"})
    df["expiry_str"]  = parsed["day"] + parsed["month"] + "20" + parsed["year"]
    df["expiry_dt"]   = pd.to_datetime(df["expiry_str"], format="%d%b%Y")

    # Ensure numeric types
    for col in ["open_interest", "mark_iv", "bid_iv", "ask_iv", "volume"]:
        df[col] = pd.to_numeric(df.get(col, 0), errors="coerce").fillna(0)

    df["underlying_price"] = pd.to_numeric(
        df["underlying_price"], errors="coerce"
    ).ffill()

    print(f"[book_summary] Parsed {len(df)} contracts across "
          f"{df['expiry_dt'].nunique()} expiries")
    return df


# ── STEP 3: COMPUTE PUT/CALL RATIO ───────────────────────────────────────────
def compute_put_call_ratio(df: pd.DataFrame) -> dict:
    """
    Computes Put/Call ratio by OI and by Volume.
    Split by expiry and aggregated total.
    Values > 1.0 indicate bearish sentiment (more put OI than call OI).
    """
    calls = df[df["option_type"] == "call"]
    puts  = df[df["option_type"] == "put"]

    total_call_oi  = calls["open_interest"].sum()
    total_put_oi   = puts["open_interest"].sum()
    total_call_vol = calls["volume"].sum()
    total_put_vol  = puts["volume"].sum()

    pcr_oi  = total_put_oi  / total_call_oi  if total_call_oi  > 0 else np.nan
    pcr_vol = total_put_vol / total_call_vol if total_call_vol > 0 else np.nan

    # Per-expiry breakdown
    per_expiry = []
    for expiry, group in df.groupby("expiry_dt"):
        c = group[group["option_type"]