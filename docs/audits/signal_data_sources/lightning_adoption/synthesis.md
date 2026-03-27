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
| 1ML Statistics | `https://1ml.com/statistics?json=true` | None | Low, undocumented | `total_nodes`, `total_channels`, `total_capacity`, `avg_capacity`, `channel_stats` | ~Hourly | 8.0/10 |
| Amboss.space GraphQL | `https://api.amboss.space/graphql` | None (limited) | 100 req/day free | `capacity`, `channels`, `nodes`, `getNetworkStats` | Real-time | 7.7/10 |
| BTCMap.org Merchant API | `https://btcmap.org/api/v2/places` | None | None observed | `merchant_count`, `ln_support`, `location`, `coordinates`, `created_at` | Real-time on edit | 7.7/10 |

---

## SECTION 2: MAJORITY SOURCES (2 of 3 Models Confirmed)

| Source | Exact URL | Auth | Rate Limit | Key Fields | Update Freq | Quality |
|--------|-----------|------|------------|------------|-------------|---------|
| Mempool.space All Timespans | `https://mempool.space/api/v1/lightning/statistics/1y` | None | ~10 req/min | Full historical arrays for all capacity/channel fields | Static pull | 9/10 |
| Mempool.space Channels | `https://mempool.space/api/v1/lightning/channels` | None | ~10 req/min | `channel_count`, `capacity`, `channel_details` | Real-time | 8/10 |
| Mempool.space Nodes | `https://mempool.space/api/v1/lightning/nodes` | None | ~10 req/min | `node_count`, `pubkey`, `alias` | Real-time | 8/10 |
| 1ML Node List | `https://1ml.com/node?json=true` | None | Low, undocumented | `node_list`, `capacity_per_node`, `channels_per_node` | Daily | 7/10 |
| Lightning Terminal Leaderboard | `https://terminal.lightning.engineering/v1/nodes/leaderboards` | None | Low, undocumented | `top_by_capacity.alias`, `top_by_channels.pub_key` | Daily | 7/10 |

---

## SECTION 3: UNIQUE FINDINGS PER MODEL

### GEMINI UNIQUE CONTRIBUTIONS

| Finding | URL | Why It Matters | Quality |
|---------|-----|----------------|---------|
| **Own LND Node REST API** | `https://YOUR_NODE:8080/v1/network/info` | Macaroon-auth local data. `graph_diameter`, `max_channel_size`, real peer-level view unavailable anywhere else | 10/10 for operator |
| **Own CLN Node REST** | `http://YOUR_NODE:PORT/v1/getinfo` | Core Lightning implementation-specific metrics, `num_pending_channels` distinct from LND | 10/10 for operator |
| **Nostr as Lightning Address DB** | Protocol-level (mentioned, truncated) | Mapping Lightning addresses to Nostr npubs gives user-level adoption signal, not network-level | 9/10 creative |
| **Mempool Historical `all` timespan** | `https://mempool.space/api/v1/lightning/statistics/all` | Full inception-to-date timeseries in single call, best for trend regression | 9/10 |
| **Node ranking by age** | `https://mempool.space/api/v1/lightning/nodes/rankings/age` | Oldest nodes = infrastructure stability signal, not just size | 8/10 |

**Gemini Verdict:** Most operationally precise. Identified self-hosted node APIs that deliver ground-truth data. Best for operators running infrastructure.

---

### GPT-4o UNIQUE CONTRIBUTIONS

| Finding | URL | Why It Matters | Quality |
|---------|-----|----------------|---------|
| **LNBig.com Routing Stats** | `https://lnbig.com/api` | LNBig is one of the largest routing node operators. Their public stats proxy large-operator routing health | 7/10 (URL needs verification) |
| **Structured Python function template** | N/A (code output) | First to provide production-ready `fetch_lightning_adoption()` function pattern with status code error handling | N/A |
| **Paid tool approximation mapping** | Conceptual | Explicitly mapped free sources to Glassnode/CryptoQuant/Nansen equivalents, useful for gap analysis framing | N/A |

**GPT-4o Verdict:** Most structured output. Weakest on URL precision (some endpoints unverified). Best for quick implementation scaffolding.

---

### GROK UNIQUE CONTRIBUTIONS

| Finding | URL | Why It Matters | Quality |
|---------|-----|----------------|---------|
| **Mempool channels endpoint explicit** | `https://mempool.space/api/v1/lightning/channels` | Only model to explicitly list channel-level detail endpoint separately from stats | 8/10 |
| **BTCMap v2 API (correct version)** | `https://btcmap.org/api/v2/places` | Gemini and GPT used v1. V2 is current and returns `ln_support` boolean filterable field | 9/10 |
| **Rate limit specificity** | Documented ~10 req/min on mempool | Most quantified rate limit estimate across all sources | High value |
| **Amboss free tier limit** | 100 req/day documented | Only model to document the specific daily cap on Amboss free tier | High value |
| **Merchant `ln_support` filter** | `?ln=true` query param on BTCMap | Filtering parameter for Lightning-only merchants, not just all Bitcoin merchants | 8/10 |

**Grok Verdict:** Most detail-accurate on URLs and constraints. Best for avoiding production failures due to undocumented rate limits.

---

## SECTION 4: PRIORITY RANKING

### P0 — CRITICAL (Build first, highest signal density)

| # | Source | URL | Rationale |
|---|--------|-----|-----------|
| P0-1 | Mempool.space Latest | `https://mempool.space/api/v1/lightning/statistics/latest` | Real-time, no auth, highest reliability, 5 core metrics in one call |
| P0-2 | Mempool.space Historical All | `https://mempool.space/api/v1/lightning/statistics/all` | Full time-series for trend modeling, regression, anomaly detection |
| P0-3 | Mempool.space Historical 30d | `https://mempool.space/api/v1/lightning/statistics/30d` | Rolling window for momentum signals |
| P0-4 | BTCMap Merchants (v2) | `https://btcmap.org/api/v2/places` | Only free source for real-world merchant Lightning adoption |
| P0-5 | 1ML Statistics | `https://1ml.com/statistics?json=true` | Independent network view cross-validates mempool data |

### P1 — HIGH VALUE (Add in second iteration)

| # | Source | URL | Rationale |
|---|--------|-----|-----------|
| P1-1 | Mempool Node Rankings (capacity) | `https://mempool.space/api/v1/lightning/nodes/rankings/capacity` | Concentration risk, Gini coefficient derivable |
| P1-2 | Mempool Node Rankings (channels) | `https://mempool.space/api/v1/lightning/nodes/rankings/channels` | Routing topology signal |
| P1-3 | Mempool Node Rankings (age) | `https://mempool.space/api/v1/lightning/nodes/rankings/age` | Infrastructure stability proxy |
| P1-4 | Amboss GraphQL | `https://api.amboss.space/graphql` | Cross-validation, routing fee market data on free tier |
| P1-5 | Lightning Terminal Leaderboard | `https://terminal.lightning.engineering/v1/nodes/leaderboards` | Institutional/professional operator tracking |
| P1-6 | 1ML Node List | `https://1ml.com/node?json=true` | Per-node distribution analysis |

### P2 — SUPPLEMENTARY (Add when P0+P1 are stable)

| # | Source | URL | Rationale |
|---|--------|-----|-----------|
| P2-1 | Mempool Channels Endpoint | `https://mempool.space/api/v1/lightning/channels` | Channel-level detail for size distribution analysis |
| P2-2 | LNBig Routing Stats | `https://lnbig.com/api` | Large operator view, URL needs prod verification |
| P2-3 | Own LND Node REST | `https://YOUR_NODE:8080/v1/network/info` | Ground truth if operating a node |
| P2-4 | Nostr Lightning Address Protocol | Relay-level scraping | User-level adoption, highest effort, highest novelty |

---

## SECTION 5: PRIMARY DATA FETCH — PYTHON (No API Key)

```python
import requests
import time
import json
from datetime import datetime
from typing import Optional

# ============================================================
# LIGHTNING ADOPTION SIGNAL — PRIMARY DATA FETCHER
# Sources: P0 tier only, no API keys required
# ============================================================

BASE_HEADERS = {
    "User-Agent": "LightningAdoptionSignal/1.0",
    "Accept": "application/json"
}

def safe_get(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Generic safe GET with error handling and rate-limit courtesy delay.
    Returns parsed JSON or None on failure.
    """
    try:
        time.sleep(0.5)  # Courtesy delay — respect soft rate limits
        response = requests.get(url, headers=BASE_HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"[HTTP ERROR] {url} → {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"[CONNECTION ERROR] {url} → {e}")
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] {url}")
    except json.JSONDecodeError:
        print(f"[JSON PARSE ERROR] {url}")
    return None


def fetch_mempool_latest() -> Optional[dict]:
    """
    P0-1: Mempool.space real-time Lightning network statistics.
    Returns: total_capacity_btc, channel_count, node_count, tor_nodes, clearnet_nodes
    """
    url = "https://mempool.space/api/v1/lightning/statistics/latest"
    data = safe_get(url)
    if data and "latest" in data:
        stats = data["latest"]
        return {
            "source": "mempool_latest",
            "timestamp": datetime.utcnow().isoformat(),
            "channel_count": stats.get("channel_count"),
            "node_count": stats.get("node_count"),
            "total_capacity_btc": stats.get("total_capacity") / 1e8 if stats.get("total_capacity") else None,
            "avg_capacity_sat": stats.get("avg_capacity"),
            "med_capacity_sat": stats.get("med_capacity"),
            "tor_nodes": stats.get("tor_nodes"),
            "clearnet_nodes": stats.get("clearnet_nodes"),
            "unannounced_nodes": stats.get("unannounced_nodes"),
        }
    return None


def fetch_mempool_historical(timespan: str = "30d") -> Optional[list]:
    """
    P0-2/P0-3: Mempool.space historical Lightning data.
    timespan options: '24h', '3d', '7d', '1m', '3m', '6m', '1y', '2y', '3y', 'all'
    Returns: list of timestamped snapshots
    """
    url = f"https://mempool.space/api/v1/lightning/statistics/{timespan}"
    data = safe_get(url)
    if data:
        return [
            {
                "added": entry.get("added"),
                "channel_count": entry.get("channel_count"),
                "node_count": entry.get("node_count"),
                "total_capacity_btc": entry.get("total_capacity") / 1e8 if entry.get("total_capacity") else None,
                "avg_capacity_sat": entry.get("avg_capacity"),
                "med_capacity_sat": entry.get("med_capacity"),
            }
            for entry in data
        ]
    return None


def fetch_1ml_statistics() -> Optional[dict]:
    """
    P0-5: 1ML.com network statistics — independent cross-validation.
    Returns: node_count, channel_count, capacity, avg/median channel size
    """
    url = "https://1ml.com/statistics?json=true"
    data = safe_get(url)
    if data:
        graph = data.get("graph_stats", data)  # Handle both response shapes
        return {
            "source": "1ml_statistics",
            "timestamp": datetime.utcnow().isoformat(),
            "total_nodes": graph.get("total_nodes") or data.get("nodecount"),
            "total_channels": graph.get("total_channels") or data.get("channelcount"),
            "total_capacity_btc": graph.get("total_capacity") or data.get("totalcapacity"),
            "avg_capacity_sat": graph.get("avg_capacity") or data.get("avgcapacity"),
            "med_capacity_sat": graph.get("med_capacity") or data.get("medcapacity"),
        }
    return None


def fetch_btcmap_lightning_merchants() -> Optional[dict]:
    """
    P0-4: BTCMap.org v2 — real-world Lightning merchant adoption.
    Returns: total_merchants, lightning_enabled_merchants, recent_additions
    """
    url = "https://btcmap.org/api/v2/elements"
    data = safe_get(url)
    if data:
        elements = data if isinstance(data, list) else data.get("elements", [])
        ln_merchants = [
            e for e in elements
            if isinstance(e, dict)
            and e.get("tags", {}).get("payment:lightning") == "yes"
        ]
        return {
            "source": "btcmap_merchants",
            "timestamp