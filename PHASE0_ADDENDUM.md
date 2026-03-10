# PHASE 0 ADDENDUM — p3-sentiment-intel
# Generated: 2026-03-09
# Based on C0_SYNTHESIS.md top additions

## WHAT WE WILL IMPLEMENT (Filtered for feasibility within a single session)

### FROM PHASE 0 SYNTHESIS — INCORPORATED:

---

### 1. Multi-Dimensional Sentiment Analysis [CRITICAL — IMPLEMENTING]
Instead of simple bullish/bearish, Claude Haiku extracts:
- Primary sentiment (bullish/bearish/neutral)
- Target stakeholder dimension (retail/institutional/miner/developer)
- Market impact magnitude (1-10 scale)
- Narrative label (ETF flows, halving cycle, regulatory clarity, etc.)

**How**: Extended `classify_article()` prompt returns JSON with all dimensions.
DB: `sentiment_dimensions TEXT` (JSON), `market_impact_magnitude REAL` on articles table.

---

### 2. Predictive Sentiment Forecasting (Lightweight) [HIGH IMPACT — PARTIAL]
No ML models (too heavy for one session). Instead:
- Rolling weighted average of last 6h sentiment scores → trend direction
- Simple regression slope calculation from 7-day history → forecast label
- Display as "trajectory": ACCELERATING_BULLISH / DECELERATING_BULLISH / NEUTRAL / ACCELERATING_BEARISH / DECELERATING_BEARISH

**How**: Computed in `get_signal_strength()` from `sentiment_snapshots` table data.

---

### 3. Event Extraction [OPERATIONAL — IMPLEMENTING]
Claude Haiku extracts structured events from article content:
- Event type: regulatory / institutional_move / technical_development / price_action / mining_event
- Impact score (1-10)
- Affected entities

**How**: Part of `classify_article()` extended output. Stored as `narrative_label` (event type) and `importance_score`.

---

### 4. Advanced Anomaly Detection [INTELLIGENCE — IMPLEMENTING]
Multivariate detection beyond simple 20-point threshold:
- Velocity component: rate of change per hour (not just absolute delta)
- Volume component: articles volume spike vs 7-day average
- Narrative coherence: if dominant narrative shifts, flag as narrative anomaly
- All anomalies stored in `intelligence_events` table

**How**: `detect_anomalies()` in `intelligence_service.py` checks all 3 vectors.

---

### 5. Source Trust Scoring [SECURITY/QUALITY — IMPLEMENTING]
Weight sentiment by source credibility:
- Known Bitcoin media (bitcoinmagazine.com, coindesk.com, decrypt.co): weight 1.0
- Unknown/generic domains: weight 0.7
- AI-generated or aggregate sources: weight 0.5

**How**: `_get_source_trust_score(source_url)` function in sentiment_analyzer.py.
Sentiment composite accounts for weighted articles, not raw average.

---

### 6. Narrative Coherence Tracking [INSIGHT — IMPLEMENTING]
Track which narratives are dominant across recent articles:
- Count articles per narrative_label in last 24h, 7d
- Identify rising narratives (24h > 7d_daily_avg)
- Identify declining narratives

**How**: `get_narrative_timeline()` in intelligence_service.py. Displayed on /intelligence.

---

### 7. SSE with Reconnect Logic [LAW 2 — IMPLEMENTING]
SSE stream at `/api/stream/sentiment` with:
- Exponential backoff reconnect in browser JS
- Heartbeat every 30s (comment event `:`  )
- Proper `retry:` header for browser reconnect

---

### 8. Prompt Injection Defense [SECURITY — IMPLEMENTING]
Before passing article content to Claude:
- Strip/escape HTML tags from content
- Truncate to max 2000 chars
- Wrap in explicit XML-delimited context markers
- System prompt explicitly warns Claude about untrusted content

**How**: `_sanitize_for_llm(text)` in sentiment_analyzer.py

---

## NOT IMPLEMENTING (infrastructure/scope constraints):
- Kafka/Redpanda event bus (requires infra setup)
- PostgreSQL/TimescaleDB/Weaviate (SQLite is the stack)
- Personalized RL dashboards (requires user tracking infra)
- Podcast audio transcription (separate system already exists)
- Edge computing (Cloudflare Workers) — not in scope
- WebSocket full duplex (SSE is sufficient per gospel LAW 2)

## DESIGN DECISIONS:
- Public `/intelligence` page: new route pointing to upgraded intelligence_dashboard.html
- Multi-dimensional sentiment: stored as TEXT (JSON) in articles.sentiment_dimensions
- Cron runs via `cron` or direct invocation; no Redis required
- All CSS animations only (law) — SVG gauge arc, keyframe animations
