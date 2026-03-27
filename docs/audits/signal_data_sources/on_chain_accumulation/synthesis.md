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

**Accumulation Signal Relevance:**
- `coin-days-destroyed`: HODLer conviction proxy. Low CDD = long-term holders not selling
- `utxo-count`: Rising UTXOs = more discrete holding events, accumulation proxy
- `n-unique-addresses`: Wallet growth signals new entrants accumulating

---

#### SOURCE U-2: Blockchair API
| Field | Value |
|-------|-------|
| **Exact URL** | `https://api.blockchair.com/bitcoin/stats` |
| **Address Lookup** | `https://api.blockchair.com/bitcoin/dashboards/address/{address}` |
| **UTXO Outputs** | `https://api.blockchair.com/bitcoin/outputs?q=is_spent(false)` |
| **Auth** | None required (free tier) |
| **Rate Limit** | 30 req/min free, 1 req/sec safe sustained |
| **Update Freq** | Near real-time (block-by-block) |
| **Quality Score** | 9/10 |

**Key Fields from `/bitcoin/stats`:**
```
utxos                         → Total unspent outputs count
circulation                   → Total BTC in circulation  
transactions_24h              → Daily transaction volume
largest_transaction_24h       → Whale movement proxy
mempool_transactions          → Pending tx count
mempool_tps                   → Network throughput
blocks_24h                    → Block production rate
average_transaction_fee_24h   → Network demand signal
```

**Key Fields from `/bitcoin/outputs` (UTXO-level):**
```
spending_block_id             → NULL if unspent (accumulation)
value                         → UTXO size in satoshis
block_id                      → Age derivation possible
recipient                     → Address-level tracking
```

---

#### SOURCE U-3: Mempool.space API
| Field | Value |
|-------|-------|
| **Exact URL** | `https://mempool.space/api/v1/` |
| **Auth** | None required |
| **Rate Limit** | 60 req/min anonymous |
| **Update Freq** | Real-time (WebSocket available) |
| **Quality Score** | 7-8/10 |

**Key Accumulation Endpoints:**
```
https://mempool.space/api/v1/mining/blocks/timestamp/{timestamp}
https://mempool.space/api/blocks
https://mempool.space/api/address/{address}
https://mempool.space/api/address/{address}/utxo
https://mempool.space/api/v1/difficulty-adjustment
https://mempool.space/api/v1/fees/mempool-blocks
```

**Key Fields:**
```
/api/address/{address}/utxo:
  txid          → Transaction ID
  value         → Satoshi value held
  status.confirmed → Confirmation state
  status.block_time → Age calculation anchor

/api/blocks:
  tx_count      → Block fullness
  size          → Block size
  timestamp     → Block time
```

---

### MAJORITY SOURCES (2/3 Models)

---

#### SOURCE M-1: Glassnode Free Tier
| Field | Value |
|-------|-------|
| **Exact URL** | `https://api.glassnode.com/v1/metrics/addresses/active_count?a=BTC` |
| **Auth** | Free API key required — register at `https://studio.glassnode.com/account/api` |
| **Rate Limit** | 10 req/day free tier |
| **Update Freq** | Weekly (free tier), Daily (paid) |
| **Quality Score** | 8/10 (free tier severely limited) |

**Free Tier Endpoints (confirmed working):**
```
https://api.glassnode.com/v1/metrics/addresses/active_count?a=BTC
https://api.glassnode.com/v1/metrics/market/price_usd_close?a=BTC
https://api.glassnode.com/v1/metrics/transactions/count?a=BTC
https://api.glassnode.com/v1/metrics/blockchain/utxo_count?a=BTC
```

**NOTE:** HODL Waves, SOPR, MVRV, Realized Cap — ALL PAYWALLED. Free tier is a preview only.

---

#### SOURCE M-2: CryptoQuant Free Tier
| Field | Value |
|-------|-------|
| **Exact URL** | `https://api.cryptoquant.com/v1/btc/network-data/active-addresses` |
| **Auth** | Free API key at `https://cryptoquant.com/account/api-management` |
| **Rate Limit** | 100 req/day (free tier) |
| **Update Freq** | Daily |
| **Quality Score** | 7/10 (free tier) |

**Free Tier Endpoints:**
```
https://api.cryptoquant.com/v1/btc/network-data/active-addresses
https://api.cryptoquant.com/v1/btc/network-data/transactions-count
https://api.cryptoquant.com/v1/btc/exchange-flows/inflow (LIMITED)
```

**NOTE:** Exchange net flows, miner flows, entity-level accumulation — PAYWALLED.

---

#### SOURCE M-3: Dune Analytics (Public Queries)
| Field | Value |
|-------|-------|
| **Exact URL** | `https://api.dune.com/api/v1/query/{query_id}/results` |
| **Auth** | Free API key at `https://dune.com/settings/api` |
| **Rate Limit** | 40 req/hour free tier |
| **Update Freq** | Query-dependent (community maintained) |
| **Quality Score** | 8/10 for custom cohort analysis |

**Useful Public Query IDs (Bitcoin Accumulation):**
```
Query 1269346  → Bitcoin UTXO Age Distribution
Query 2274840  → BTC Wallet Cohort Analysis  
Query 1995088  → Long-Term Holder Supply
Query 2156789  → Bitcoin Exchange Balance Tracking
```

**Access pattern:**
```
https://api.dune.com/api/v1/query/1269346/results?limit=1000
```

---

#### SOURCE M-4: BitInfoCharts (Scraping)
| Field | Value |
|-------|-------|
| **Exact URL** | `https://bitinfocharts.com/comparison/bitcoin-activeaddresses.html` |
| **Auth** | None (scraping, no official API) |
| **Rate Limit** | Respect crawl delay, 1 req/5sec minimum |
| **Update Freq** | Daily |
| **Quality Score** | 6/10 (scraping fragility, ToS gray area) |

**Scrapeable Pages:**
```
https://bitinfocharts.com/comparison/bitcoin-activeaddresses.html
https://bitinfocharts.com/comparison/bitcoin-sentbyaddress.html
https://bitinfocharts.com/comparison/bitcoin-transactions.html
https://bitinfocharts.com/comparison/bitcoin-median_transaction_fee.html
```

---

## SECTION 2: UNIQUE FINDINGS PER MODEL

### What GEMINI Found That Others Missed

**1. Complete Blockchain.com Chart Endpoint Taxonomy**
Gemini provided the most exhaustive enumeration of Blockchain.com chart names including several accumulation-critical ones others omitted:

```
# GEMINI-EXCLUSIVE ENDPOINTS (not listed by GPT-4o or Grok):
https://api.blockchain.info/charts/mempool-count?format=json
https://api.blockchain.info/charts/mempool-growth?format=json
https://api.blockchain.info/charts/mempool-size?format=json
https://api.blockchain.info/charts/cost-per-transaction?format=json
https://api.blockchain.info/charts/total-transaction-fees?format=json
https://api.blockchain.info/charts/transactions-per-second?format=json
https://api.blockchain.info/charts/avg-block-size?format=json
```

**Signal Value:** `mempool-growth` combined with `cost-per-transaction` creates a demand-pressure indicator. Accumulation phases often show rising mempool with flat/falling fees — organic buying without panic urgency.

**2. Blockchair Address Clustering Methodology**
Gemini uniquely noted that Blockchair's address dashboard implicitly clusters related wallets via common-input-ownership heuristic, accessible without authentication at:
```
https://api.blockchair.com/bitcoin/dashboards/address/{address}
```
This enables poor-man's entity-level tracking by manually tracing `first_seen_receiving` and `last_seen_spending` fields.

---

### What GPT-4O Found That Others Missed

**1. Explicit WebSocket Stream Reference**
GPT-4o was the only model to explicitly flag the Blockchain.com WebSocket API as a real-time accumulation signal source:
```
wss://ws.blockchain.info/inv
# Subscribe to new unconfirmed transactions:
{"op": "unconfirmed_sub"}
# Subscribe to address activity:
{"op": "addr_sub", "addr": "{address}"}
```
**Signal Value:** Real-time monitoring of large unconfirmed inputs to known cold wallet addresses before block confirmation — 10-15 minute edge over block-confirmed data.

**2. Node RPC as Data Source**
GPT-4o flagged self-hosted Bitcoin Core RPC as a zero-cost, zero-rate-limit accumulation data source — the only model to mention it:
```bash
# If running Bitcoin Core node:
bitcoin-cli getblockchaininfo
bitcoin-cli listunspent
bitcoin-cli gettxoutsetinfo  # Full UTXO set snapshot
bitcoin-cli getblockstats {hash} '["utxo_increase","total_out","totalfee"]'
```
**Signal Value:** `gettxoutsetinfo` gives complete UTXO set statistics. `getblockstats` provides per-block UTXO delta — the most granular accumulation signal available at zero cost with zero rate limits.

**3. Explicit Mention of Manual Glassnode/CryptoQuant CSV Download**
GPT-4o acknowledged the manual download workflow as a legitimate (if labor-intensive) free data acquisition method — important for backtesting when API limits prevent historical pulls.

---

### What GROK Found That Others Missed

**1. Structured Comparison Table Format**
Grok uniquely provided a rate-limit breakdown distinguishing anonymous vs. authenticated free tiers — specifically calling out Glassnode's 10 req/day free limit vs. CryptoQuant's 100 req/day, critical for pipeline architecture decisions.

**2. Specific Dune Analytics Query IDs**
Grok was the only model to provide actual usable Dune query IDs for Bitcoin accumulation analysis — the difference between "Dune exists" and "here's what to actually run."

**3. Blockchair UTXO Output Filter Query**
Grok uniquely identified the filtered UTXO endpoint:
```
https://api.blockchair.com/bitcoin/outputs?q=is_spent(false)
```
This enables direct unspent output enumeration — a genuine accumulation proxy without needing paid tools.

**4. Explicit Free Glassnode Endpoint List**
Grok was more specific about which Glassnode endpoints actually work on free tier:
```
/v1/metrics/blockchain/utxo_count        ← Grok-identified, others missed
/v1/metrics/market/price_usd_close       ← Confirmed free
/v1/metrics/transactions/count           ← Confirmed free
/v1/metrics/addresses/active_count       ← All models confirmed
```

---

## SECTION 3: PRIORITY RANKINGS

### P0 — CRITICAL (Build First, Zero Cost, No Auth, High Signal)

| Rank | Source | URL | Why P0 |
|------|--------|-----|--------|
| P0-1 | **Blockchain.com CDD** | `https://api.blockchain.info/charts/coin-days-destroyed?timespan=2years&format=json` | Direct HODLer conviction metric. No auth. Reliable uptime. |
| P0-2 | **Blockchain.com UTXO Count** | `https://api.blockchain.info/charts/utxo-count?timespan=2years&format=json` | Rising UTXO count = accumulation fragmentation signal |
| P0-3 | **Blockchair Network Stats** | `https://api.blockchair.com/bitcoin/stats` | Real-time composite view. Best free single endpoint. |
| P0-4 | **Blockchair Unspent Outputs** | `https://api.blockchair.com/bitcoin/outputs?q=is_spent(false)&limit=100` | Direct UTXO enumeration, no auth required |
| P0-5 | **Mempool.space Address UTXO** | `https://mempool.space/api/address/{address}/utxo` | Per-address holding age calculation anchor |
| P0-6 | **Bitcoin Core RPC** | `bitcoin-cli gettxoutsetinfo` | Zero rate limits if self-hosted. Complete UTXO set. |

---

### P1 — HIGH VALUE (Require Free Account or Light Scraping)

| Rank | Source | URL | Why P1 |
|------|--------|-----|--------|
| P1-1 | **Glassnode Free Tier** | `https://api.glassnode.com/v1/metrics/blockchain/utxo_count?a=BTC` | Free key unlocks 4 confirmed endpoints. Brand-name data. |
| P1-2 | **Dune Analytics** | `https://api.dune.com/api/v1/query/1269346/results` | Community UTXO age queries. Best free cohort analysis available. |
| P1-3 | **CryptoQuant Free Tier** | `https://api.cryptoquant.com/v1/btc/network-data/active-addresses` | 100 req/day. Exchange inflow glimpse. |
| P1-4 | **Blockchain.com WebSocket** | `wss://ws.blockchain.info/inv` | Real-time mempool monitoring. 10-min edge on accumulation moves. |

---

### P2 — SUPPLEMENTARY (Useful but Fragile or Noisy)

| Rank | Source | URL | Why P2 |
|------|--------|-----|-----