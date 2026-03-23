# Phase 2 Feature F3 — CBDC & Sovereign Intelligence Layer

## Foundation Document

### Purpose

Monitor global sovereign posture toward Bitcoin, track CBDC rollout risk, surface self-custody health indicators, and detect capital-flight signals. Provides the data layer for the `/sovereignty` dashboard and terminal sovereign panel.

---

### Data Sources

| Source | Type | Refresh | Notes |
|--------|------|---------|-------|
| `data/jurisdiction_db.json` | Static (manual) | Monthly | 50 jurisdictions with BTC status, CBDC stage, capital controls, trend |
| `data/cbdc_watchlist.json` | Static (manual) | Monthly | 15 highest-risk CBDC programs with programmable feature inventory |
| BIS RSS (`bis.org/rss.htm`) | Live (async) | Per cycle (~30 min) | Filtered for CBDC keywords; critical flag on surveillance/mandatory terms |
| Sentinel state (dict) | Live (injected) | Per cycle | On-chain signals: exchange reserves, CDD, CoinJoin volume, Taproot % |
| mempool.space API | Live (future) | 5 min | Taproot adoption percentage (placeholder until wired) |

### Live vs Static Monitoring

- **Static**: Jurisdiction DB and CBDC watchlist are curated JSON files updated manually on regulatory changes. No API dependency.
- **Live**: BIS RSS fetched async with graceful fallback to cached results on failure. Sentinel state injected from external on-chain monitors when available.
- **Hybrid**: `run_cycle()` merges both static summaries and live feeds into a single output dict each cycle.

### Self-Custody Health Metrics

| Metric | Source | Signal Levels |
|--------|--------|---------------|
| Exchange Reserve Ratio | Sentinel / placeholder (58.2%) | Lower = more self-custody |
| CDD 90-day Z-Score | Sentinel | STABLE / ELEVATED / DORMANT |
| CoinJoin Volume (BTC) | Sentinel | NORMAL / HIGH / LOW |
| Taproot Adoption % | mempool.space / placeholder (5.0%) | Higher = better privacy tooling |

### Capital Flight Detection

Heuristics (all require sentinel state injection):

1. Exchange inflow z-score > 3.0 standard deviations
2. P2P premium > 15% in any hostile jurisdiction
3. Stablecoin outflow z-score > 2.5

Returns boolean signal. Future: per-jurisdiction breakdown with source attribution.

### Output Schema (`run_cycle()` return)

```json
{
  "top_alerts": [
    {"title": "...", "link": "...", "published": "...", "is_critical": true}
  ],
  "jurisdiction_summary": {
    "friendly_count": 32,
    "neutral_count": 12,
    "hostile_count": 6
  },
  "custody_health": {
    "exchange_reserve_ratio": 58.2,
    "cdd_signal": "STABLE",
    "coinjoin_signal": "NORMAL",
    "taproot_pct": 5.0
  },
  "capital_flight_signal": false,
  "updated_at": 1711152000.0
}
```

### Audit Decisions

1. **No `from services.*` imports** — `sovereign_engine.py` uses `importlib.util` and `pathlib.Path` only to avoid circular import chains in the Flask app.
2. **Graceful degradation** — Every external fetch (BIS RSS) has try/except with fallback to cached or empty data. Engine never crashes the caller.
3. **Placeholder values** — Exchange reserve ratio (58.2%), Taproot % (5.0%) are placeholders until Glassnode/CryptoQuant/mempool.space integrations ship in P3.
4. **Jurisdiction counts** — "friendly" = `legal`, "neutral" = `restricted`, "hostile" = `hostile` + `banned`. Simple bucketing; weighted scoring deferred to P3.
5. **CBDC watchlist alert thresholds** — `high` for programs with programmable money + surveillance features or large populations; `medium` for advanced pilots; `low` for small-scale or early-stage.
6. **Capital flight detection** — Conservative thresholds (z > 3.0, premium > 15%) to minimize false positives. Will tune after live data integration.
