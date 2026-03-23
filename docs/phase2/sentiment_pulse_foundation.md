# Sentiment Pulse — Phase 2 F2 Foundation

## Overview
Influence-weighted NLP across X, Nostr, Reddit — real-time score -100 to +100.
Async engine integrated into Sentinel daemon via importlib, updating every 30s.

## Data Sources
1. **X (Nitter)**: Reuse existing scraper pattern from x_spaces_scraper/. Target TIER1 handles.
2. **Nostr**: Direct relay connection wss://relay.damus.io. Filter kind:1 notes with #bitcoin/#btc tags.
3. **Reddit**: Public JSON endpoints (r/Bitcoin/new.json, r/CryptoCurrency/search.json). No auth needed.
4. **GitHub**: bitcoin/bitcoin commit activity as dev sentiment proxy.

## Influence Weighting
- Tier 1 (OG/Builder, weight 3.0): Known builders, verified devs, 5+ year BTC history
- Tier 2 (Amplifier, weight 1.5): High-reach accounts >10K followers
- Tier 3 (Retail, weight 0.5): Everyone else

## Scoring Formula
- `weighted_positive_count - weighted_negative_count`, normalized to -100/+100
- Rolling 7-day max/min for normalization
- Smoothed with 30-min EMA
- Posts need >2 keyword matches to score (filter noise)

## Output Schema (SentinelState.sentiment)
```json
{
  "score": 0.0,
  "score_30m_ago": 0.0,
  "trend": "stable",
  "source_breakdown": {"x": 0.0, "nostr": 0.0, "reddit": 0.0},
  "volume_24h": 0,
  "top_entities": [],
  "tier1_signal": false,
  "updated_at": 0.0
}
```

## Audit Decisions
- Keyword heuristic is sufficient for v1 (no embeddings needed — speed > accuracy)
- Single Tier 1 account capped at 15% max influence per cycle (anti-domination)
- Nostr relay failure: graceful skip, log warning, use cached data
- False positive guard: require minimum 2 keyword matches per post
- Reddit: 5-min cache to respect rate limits
