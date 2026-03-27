# MASTER DATA SOURCE REPORT: Bitcoin Exchange Pressure Signal

---

## SECTION 1: UNANIMOUS & MAJORITY FREE SOURCES (ALL MODELS AGREED)

### UNANIMOUS SOURCES (All 3 Models Identified)

| # | Name | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Consensus Quality |
|---|------|-----------|------|------------|------------|-------------|-------------------|
| 1 | **Mempool.space Address API** | `https://mempool.space/api/address/{ADDRESS}` | None | ~10 req/min | `chain_stats.funded_txo_sum`, `chain_stats.spent_txo_sum`, `balance`, `txs` | Real-time (~10min blocks) | 9/10 |
| 2 | **Blockchain.com Netflow Chart** | `https://api.blockchain.info/charts/exchange-netflow?timespan=30days&format=json` | None | ~1 req/10sec | `values[].x` (timestamp), `values[].y` (BTC netflow) | Daily | 7/10 |
| 3 | **DIY Coinbase Premium Index** | Binance: `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` + Coinbase: `https://api.coinbase.com/v2/prices/BTC-USD/spot` | None | Binance: 1200/min; Coinbase: 10/sec | `price` (both endpoints, compute spread) | Real-time | 8/10 |
| 4 | **CryptoQuant Free Tier** | `https://api.cryptoquant.com/v1/btc/exchange-flows/netflow` | Free API Key | 60-100 req/day | `netflow_total`, `inflow`, `outflow` | Daily (delayed on free) | 7/10 |
| 5 | **Glassnode Free Tier** | `https://api.glassnode.com/v1/metrics/exchange/balance_total` | Free API Key | 10 req/day | `total_balance`, `v` (value), `t` (timestamp) | Daily (T+1 on free) | 7/10 |
| 6 | **Stablecoin Supply Tracking (USDT via Etherscan)** | `https://api.etherscan.io/api?module=stats&action=tokensupply&contractaddress=0xdac17f958d2ee523a2206206994597c13d831ec7&apikey=YourApiKey` | Free API Key | 5 req/sec | `result` (total supply in wei) | ~5 min | 6/10 |
| 7 | **Bybit Proof of Reserves** | `https://www.bybit.com/user/assets/proof-of-reserves` (web) / Internal: `https://www.bybit.com/api/v5/asset/get-proof-of-reserves` | None (public) | Unofficial, ~5 req/min | `walletBalance` per coin, `BTC` balance | Snapshot/Monthly | 6/10 |

---

### MAJORITY SOURCES (2 of 3 Models Identified)

| # | Name | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Quality |
|---|------|-----------|------|------------|------------|-------------|---------|
| 8 | **Binance Known Hot Wallet Monitoring** | `https://mempool.space/api/address/34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo` (Binance Hot #1) | None | ~10 req/min | `funded_txo_sum`, `spent_txo_sum`, `tx_count` | Real-time | 8/10 |
| 9 | **USDC Supply via Circle Transparency** | `https://www.circle.com/en/transparency` | None (manual scrape) | None specified | `total_issued`, `total_redeemed` | Monthly | 5/10 |
| 10 | **Blockchain.com Address Balance API** | `https://blockchain.info/balance?active={ADDRESS}&format=json` | None | ~1 req/sec | `final_balance`, `total_received`, `total_sent` | Real-time | 7/10 |

---

## SECTION 2: WHAT EACH MODEL UNIQUELY FOUND

### GEMINI — Unique Contributions

**1. Mempool WebSocket for Pre-Confirmation Exchange Sweep Detection**
- URL: `wss://mempool.space/api/v1/ws`
- Concept: Exchange consolidation sweeps have signature patterns (`vin.length > 50`, `vout.length < 3`). Monitoring the mempool catches these *before* on-chain confirmation, giving ~10-minute lead time over block-confirmed data.
- Why it matters: This is a **leading indicator**, not lagging. No other model found this.
- Implementation signal: Filter unconfirmed transactions by input count as proxy for exchange activity.

**2. DIY Coinbase Premium as a Structured Computation (Not Just Raw Price)**
- Gemini was the only model to provide the exact mathematical formula explicitly:
- `premium = ((coinbase_price / binance_price) - 1) * 100`
- And correctly identified this as an institutional demand proxy (Coinbase = US institutional; Binance = global retail).

**3. Etherscan Stablecoin Mint Tracking as Exchange Pressure Proxy**
- Specific contract address provided: `0xdac17f958d2ee523a2206206994597c13d831ec7` (USDT on ETH)
- Rationale: Stablecoin minting onto exchanges = dry powder arriving = buy pressure incoming. Burning = exit from ecosystem.

---

### GPT-4o — Unique Contributions

**1. Tether Transparency Page as a Manual Signal Source**
- URL: `https://tether.to/en/transparency/`
- While low-frequency (monthly), GPT-4o correctly identified attestation data as a macro-level exchange pressure proxy that the others underweighted.

**2. Bybit Public Time Endpoint as Availability Check**
- URL: `https://api.bybit.com/v2/public/time`
- Minor but useful: GPT-4o flagged this as a lightweight API health check before running heavier reserve queries.

**3. Glassnode Active Address Count as Supplementary Pressure Signal**
- URL: `https://studio.glassnode.com/metrics?a=BTC&m=addresses.ActiveCount`
- Reasoning: Active address spikes often precede exchange inflow events. Indirect but correlated signal.

**Warning — GPT-4o Errors Identified:**
- Listed `https://api.blockchain.com/v3/exchange/netflow` — **this endpoint does not exist in this form**. Correct URL is `https://api.blockchain.info/charts/exchange-netflow?format=json`.
- Provided incomplete Blockchain.info example that truncates mid-sentence.
- Bybit example (`https://api.bybit.com/v2/public/time`) returns server time only, not reserve data — misleading framing.

---

### GROK — Unique Contributions

**1. Specific Known Exchange Wallet Addresses Compiled**
- Grok provided the most specific address list:
  - Binance Hot Wallet #14: `3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb`
  - Binance Cold Wallet #1: `34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo`
- This is operationally superior — you can track specific wallets rather than relying on aggregate chart APIs.

**2. Multi-Exchange Comparison Framework**
- Grok explicitly framed the Coinbase Premium as a *spread computation* requiring simultaneous polling of both endpoints, and noted this requires timestamp alignment to avoid stale price artifacts.

**3. Most Complete Rate Limit Documentation**
- Grok provided the most accurate rate limit specifications across all sources, specifically noting CryptoQuant free tier is 100 req/day (vs Gemini's 60/min claim which appears to conflate paid tier limits).

---

## SECTION 3: PRIORITY RANKING

### P0 — CRITICAL (Implement Immediately, No Key Required)

| Priority | Source | URL | Reason |
|----------|--------|-----|--------|
| **P0-1** | Mempool.space Known Exchange Wallets | `https://mempool.space/api/address/34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo` | Real-time, no auth, direct on-chain ground truth |
| **P0-2** | DIY Coinbase Premium Index | Binance: `https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT` + Coinbase: `https://api.coinbase.com/v2/prices/BTC-USD/spot` | Real-time institutional demand signal, zero friction |
| **P0-3** | Mempool WebSocket (Exchange Sweep Detection) | `wss://mempool.space/api/v1/ws` | Only leading indicator on this list — pre-confirmation alpha |
| **P0-4** | Blockchain.com Netflow Chart | `https://api.blockchain.info/charts/exchange-netflow?timespan=30days&format=json` | Reliable daily aggregate, no auth required |

### P1 — HIGH VALUE (Requires Free Registration)

| Priority | Source | URL | Reason |
|----------|--------|-----|--------|
| **P1-1** | CryptoQuant Free Tier Netflow | `https://api.cryptoquant.com/v1/btc/exchange-flows/netflow` | Best structured exchange flow data at free tier |
| **P1-2** | Glassnode Free Tier Exchange Balance | `https://api.glassnode.com/v1/metrics/exchange/balance_total` | Industry-standard metric, T+1 lag acceptable for daily signals |
| **P1-3** | Etherscan USDT Supply Tracker | `https://api.etherscan.io/api?module=stats&action=tokensupply&contractaddress=0xdac17f958d2ee523a2206206994597c13d831ec7` | Stablecoin dry powder proxy, 5-min updates |

### P2 — SUPPLEMENTARY (Lower Frequency / Manual)

| Priority | Source | URL | Reason |
|----------|--------|-----|--------|
| **P2-1** | Bybit Proof of Reserves | `https://www.bybit.com/user/assets/proof-of-reserves` | Monthly snapshot, useful for structural trend only |
| **P2-2** | Tether Transparency Attestations | `https://tether.to/en/transparency/` | Monthly, macro context only |
| **P2-3** | USDC Circle Transparency | `https://www.circle.com/en/transparency` | Monthly, corroborating stablecoin signal |
| **P2-4** | Blockchain.info Address Balance | `https://blockchain.info/balance?active={ADDRESS}&format=json` | Useful for spot-checking specific wallets |

---

## SECTION 4: PRIMARY FREE DATA FETCH — NO API KEY PYTHON CODE

```python
"""
Bitcoin Exchange Pressure Signal Collector
No API Key Required — P0 Sources Only
Fetches: On-chain wallet flows, Coinbase Premium, Netflow Chart
"""

import requests
import json
import websocket
import time
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# CONFIG: Known Exchange Wallet Addresses
# Source: Community-verified via multiple blockchain explorers
# ─────────────────────────────────────────────
EXCHANGE_WALLETS = {
    "Binance_Hot_1":  "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
    "Binance_Hot_14": "3LYJfcfHPXYJreMsASk2jkn69LWEYKzexb",
    "Bitfinex_Cold":  "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97",
}

MEMPOOL_BASE     = "https://mempool.space/api"
BINANCE_TICKER   = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
COINBASE_TICKER  = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
BLOCKCHAIN_CHART = (
    "https://api.blockchain.info/charts/exchange-netflow"
    "?timespan=30days&format=json&sampled=true"
)

HEADERS = {"User-Agent": "Mozilla/5.0 (BTC-Signal-Research/1.0)"}

# ─────────────────────────────────────────────
# MODULE 1: On-Chain Exchange Wallet Flow
# ─────────────────────────────────────────────
def fetch_wallet_flows(wallets: dict) -> dict:
    """
    Fetches funded/spent totals for known exchange wallets.
    Returns net flow estimate per wallet.
    Mempool.space: No auth, ~10 req/min soft limit.
    """
    results = {}
    for name, address in wallets.items():
        url = f"{MEMPOOL_BASE}/address/{address}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            chain    = data.get("chain_stats", {})
            mempool  = data.get("mempool_stats", {})

            funded_confirmed   = chain.get("funded_txo_sum", 0)    # satoshis in
            spent_confirmed    = chain.get("spent_txo_sum", 0)     # satoshis out
            funded_unconfirmed = mempool.get("funded_txo_sum", 0)  # pending in
            spent_unconfirmed  = mempool.get("spent_txo_sum", 0)   # pending out

            # Convert satoshis → BTC (1 BTC = 100,000,000 sats)
            net_confirmed   = (funded_confirmed - spent_confirmed) / 1e8
            net_unconfirmed = (funded_unconfirmed - spent_unconfirmed) / 1e8

            results[name] = {
                "address":          address,
                "net_btc_confirmed":   round(net_confirmed, 8),
                "net_btc_unconfirmed": round(net_unconfirmed, 8),
                "tx_count_confirmed":  chain.get("tx_count", 0),
                "tx_count_pending":    mempool.get("tx_count", 0),
                "timestamp_utc":       datetime.now(timezone.utc).isoformat(),
            }

            print(f"[WALLET] {name}: net_confirmed={net_confirmed:.4f} BTC | "
                  f"pending={net_unconfirmed:.4f} BTC | "
                  f"txs={chain.get('tx_count',0)}")

            time.sleep(0.5)  # Respect soft rate limit

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {name} ({address}): {e}")
            results[name] = {"error": str(e)}

    return results


# ─────────────────────────────────────────────
# MODULE 2: Coinbase Premium Index
# Signal: Positive premium = US institutional buying
#         Negative premium = Institutional distribution / selling
# ─────────────────────────────────────────────
def fetch_coinbase_premium() ->