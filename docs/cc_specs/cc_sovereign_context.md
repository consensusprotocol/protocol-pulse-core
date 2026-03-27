Read PIPELINE_LAWS.md and VISUAL_DESIGN_SYSTEM.md.

BUILD: services/sovereign_context_engine.py

THE CONCEPT: A continuously-running intelligence brain that reads ALL data streams,
maintains a unified world-state snapshot, detects cross-stream patterns, and emits
SOVEREIGN ALERTS when multiple streams confirm the same signal.

Every other system reads from this engine: Oracle briefings, Stage content,
article generator, intelligence terminal, PANOPTICON dashboard.

DATA STREAMS TO UNIFY:
1. BTC price + 24h/7d change (price_service.py)
2. Fear & Greed index (alternative.me)
3. Mempool: fee rates, congestion, unconfirmed txs (mempool.space)
4. Hashrate + difficulty + next adjustment (mempool.space)
5. Lightning capacity + channels (mempool.space)
6. KOL sentiment: last 50 posts from kol_pulse_item table, scored
7. Article corpus: last 20 published articles, topic clusters, sentiment
8. Polymarket: crypto/macro markets, Yes/No probabilities, volume
9. Exchange netflow signals (from pipeline cache)
10. PCAF anomaly score (from video_pipeline_v3/cache/active_signal.json)
11. Stage brief: latest narrative from video_pipeline_v3/data/stage_briefs/latest.json
12. Nostr signal feed (from x_spaces_scraper if available)
13. Whale alerts (from data/sovereign_intel.db if available)

ARCHITECTURE:
- Class: SovereignContextEngine
- Method: build_world_state() -> dict — assembles everything into one JSON
- Method: detect_patterns(world_state) -> list[Alert] — finds cross-stream signals
- Method: emit_alerts(alerts) — writes to data/sovereign_alerts.db + logs
- Method: run_cycle() — called every 5 minutes by cron/watchdog
- Saves snapshot to: data/sovereign_context/latest.json (always current)
- Keeps rolling history: data/sovereign_context/history.jsonl (append-only)

PATTERN DETECTION RULES (implement all):
1. ACCUMULATION SIGNAL: hashrate UP + exchange outflows UP + FG < 30 → "Stealth accumulation detected"
2. SUPPLY SHOCK PRECURSOR: hashrate UP + price DOWN + miner revenue stable → "Miners not capitulating — supply shock risk"
3. NARRATIVE DIVERGENCE: article sentiment BULLISH + KOL sentiment BEARISH → "Narrative split — watch for resolution"
4. POLYMARKET CONFIRMATION: Polymarket crypto market probability changes >10% in 1hr + KOL mention → "Market consensus shifting"
5. MEMPOOL PRESSURE: fees > 50 sat/vB + Lightning capacity growing → "On-chain congestion — Lightning demand increasing"
6. FEAR CAPITULATION: FG < 15 + exchange inflows spike + price DOWN >5% → "Extreme fear — historically bullish 30-day forward"
7. CROSS-ASSET DIVERGENCE: any 3+ signals diverge from their 30-day baseline simultaneously → "DIVERGENCE ALERT — major move probable 24-72h"

WORLD STATE JSON SCHEMA:
{
  "timestamp": "ISO8601",
  "block_height": 942000,
  "btc": {"price": 71000, "change_24h": 1.2, "change_7d": -3.1, "market_cap": 0, "dominance": 55},
  "fear_greed": {"value": 25, "label": "Extreme Fear"},
  "mempool": {"fee_low": 1, "fee_mid": 8, "fee_high": 35, "unconfirmed": 14000, "size_mb": 180},
  "network": {"hashrate_eh": 968, "difficulty": 0, "next_adj_pct": 2.3, "next_adj_blocks": 1200},
  "lightning": {"capacity_btc": 5200, "channels": 65000, "nodes": 18000},
  "kol": {"sentiment_score": 62, "top_topics": ["etf", "halving", "regulation"], "post_count_24h": 847},
  "narrative": {"dominant_theme": "ETF inflows", "sentiment": "bullish", "article_count": 12},
  "polymarket": {"macro_sentiment": 68, "top_market": "Will BTC hit $100k by Q2?", "top_probability": 34},
  "pcaf_score": 35,
  "exchange_flow": "neutral",
  "active_alerts": [],
  "pattern_matches": []
}

INTEGRATION POINTS:
- Oracle: avatar_server.py reads latest.json on every /oracle/speak call to enrich Satomi's context
- Stage: daily_producer.py reads latest.json for narrative awareness
- Intelligence Terminal: /api/sovereign-context endpoint serves latest.json to frontend
- PANOPTICON: reads pattern_matches for cross-reference with congressional trades

CRON SETUP:
Add to crontab: */5 * * * * python3 /home/ultron/protocol_pulse/services/sovereign_context_engine.py --cycle >> /home/ultron/protocol_pulse/logs/sovereign_context.log 2>&1

Also add a Flask route: GET /api/sovereign-context -> returns latest.json

After building:
1. Run one cycle manually to verify: python3 services/sovereign_context_engine.py --cycle
2. Check output: cat data/sovereign_context/latest.json | python3 -m json.tool | head -30
3. git add -A && git commit -m "feat(sovereign-context): unified intelligence brain — all data streams → pattern detection → sovereign alerts" && git push
