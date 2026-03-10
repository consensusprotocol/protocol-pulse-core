# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.

# PROTOCOL PULSE — GOSPEL: P3 SENTIMENT + INTELLIGENCE DASHBOARDS
# Branch: feature/p3-sentiment-intel | Created: 2026-03-09

---

## WHAT THIS IS
Two pages already have templates but serve empty/stub data.
Wire them with real intelligence: sentiment analyzer service (Claude classifies every
article), daily report cron, signal strength composite, narrative intelligence engine,
entity relationship tracker, anomaly detection. The AI brain of Protocol Pulse.

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-sentiment-intel --phase0
Ask all 3 LLMs: "What are the most advanced AI-powered sentiment and market intelligence
features for a Bitcoin media platform in 2026? What NLP techniques, visualizations,
and real-time signals distinguish world-class financial intelligence platforms?"
Incorporate top P0 ideas before building.

## THE LAWS
### LAW 1: Sentiment is calculated from real articles — never fake or static
- Every new article gets sentiment classified within 60s of creation
- Batch re-classify last 100 articles on service restart (catch-up)
- Use claude-haiku-4-5 for speed/cost (not Sonnet — high volume)
- Store in articles table: sentiment TEXT, sentiment_confidence REAL, sentiment_at DATETIME

### LAW 2: SSE for real-time sentiment stream — not polling
/api/stream/sentiment → SSE endpoint, pushes on every new classification
Browser shows new sentiment badge appearing on article as it's classified
Smooth CSS fade-in animation on new sentiment badges

### LAW 3: Narrative intelligence is the key differentiator
Go beyond "bullish/bearish" → identify WHAT NARRATIVE is driving sentiment
Narratives: "ETF flows", "halving cycle", "regulatory clarity", "mining capitulation",
"institutional adoption", "Lightning growth", "miner selling pressure", etc.
Claude extracts narrative label from article body — not just positive/negative

### LAW 4: Anomaly detection fires loud
If sentiment score drops/rises > 20 points in 2hrs: log anomaly, show banner alert
Store in intelligence_events table, show on dashboard with timestamp
"⚠ SENTIMENT ANOMALY DETECTED — bullish→bearish shift in 90min" style alert

## ARCHITECTURE

### Database Additions
```sql
-- Add to articles table if not present:
ALTER TABLE articles ADD COLUMN sentiment TEXT;
ALTER TABLE articles ADD COLUMN sentiment_confidence REAL;
ALTER TABLE articles ADD COLUMN narrative_label TEXT;
ALTER TABLE articles ADD COLUMN importance_score INTEGER DEFAULT 50;

CREATE TABLE IF NOT EXISTS sentiment_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date DATE UNIQUE,
  overall_sentiment TEXT,        -- bullish|bearish|neutral
  score INTEGER,                 -- 0-100
  bullish_pct REAL,
  bearish_pct REAL,
  neutral_pct REAL,
  narrative TEXT,                -- 2-para Claude-generated narrative
  top_bullish_signals TEXT,      -- JSON array of strings
  top_bearish_signals TEXT,      -- JSON array of strings
  dominant_narrative TEXT,       -- e.g., "ETF inflows driving optimism"
  anomaly_detected INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS intelligence_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT,               -- sentiment_anomaly|narrative_shift|price_correlation
  severity TEXT,                 -- info|warning|critical
  description TEXT,
  data_snapshot TEXT,            -- JSON
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment, published_at);
CREATE INDEX IF NOT EXISTS idx_articles_narrative ON articles(narrative_label);
```

### Services

services/sentiment_analyzer.py
  classify_article(article_id):
    - Pull title + summary from DB
    - claude-haiku-4-5: classify as bullish/bearish/neutral + extract narrative label
    - Return {sentiment, confidence, narrative_label, importance_score}
    - Update articles table

  generate_daily_report():
    - Query last 50 articles' sentiments
    - Calculate percentages + composite score
    - Claude Sonnet: write 2-para narrative about today's Bitcoin discourse
    - Detect anomalies vs yesterday's score
    - Save to sentiment_reports table

  batch_classify(hours=6):
    - Classify all unclassified articles in last N hours
    - Run every 2hrs via cron

services/intelligence_service.py
  get_trending_topics(hours=24):
    - Titles + summaries of last N hours articles
    - claude-haiku: extract top 10 topics + count + sentiment per topic
    - Cache 30min in memory

  get_entity_tracker(hours=48):
    - Named entity extraction from recent articles
    - People, orgs, coins, protocols
    - [{entity, type, mention_count, sentiment, trend: up/down/stable}]

  get_signal_strength():
    - Components (each 0-100, weighted):
      price_momentum: 20% — 24h BTC price change → score
      sentiment_score: 40% — from latest sentiment_report
      article_volume: 15% — 24h count vs 7-day avg
      hashrate_trend: 15% — from mempool.space
      fear_greed: 10% — https://api.alternative.me/fng/
    - Composite: weighted average
    - Cache 5min

  detect_anomalies():
    - Compare last 2hrs sentiment vs 24hr baseline
    - If |delta| > 20: save intelligence_event, return alert

Cron jobs:
  */30 * * * * python3 -m services.sentiment_analyzer batch --hours=1
  55 23 * * * python3 -m services.sentiment_analyzer daily_report

### /sentiment Page Upgrades
Wire route to pass: latest_report, score_history (7 days), top_signals,
recent_articles (with sentiment), dominant_narrative, anomaly_events.

New widgets in template:
- Animated sentiment gauge: SVG arc 0-100, color lerps red→orange→green
- 7-day score sparkline: Canvas, gold line, today highlighted
- Narrative intelligence card: "This week's dominant narrative: [X]" with explanation
- Top signals: bullish (green ▲) + bearish (red ▼) bullet lists
- Recent articles: each has BULLISH/BEARISH/NEUTRAL badge + narrative tag
- Anomaly alert banner (if active): pulsing red border, dismissible
- SSE connection: new article classifications appear live with fade-in

### /intelligence Page Upgrades
Wire route to pass: signal_strength, trending_topics, entities,
recent_articles, btc_price, article_count_24h, intelligence_events.

New widgets:
- Signal Strength composite: big number + label + animated radial gauge
  Red = FEAR, Orange = CAUTION, Yellow = NEUTRAL, Green = CONFIDENCE, Cyan = EUPHORIA
- Component breakdown: 5 mini-gauges showing each signal component
- Trending topics cloud: CSS-based, font-size 12-36px proportional to count
  Color: red = bearish topic, green = bullish, white = neutral
- Entity tracker table: entity | type | mentions | sentiment | trend arrow
- Narrative timeline: last 7 days dominant narratives as horizontal timeline
- Intelligence events: recent anomalies/shifts with severity indicators
- Article stream: live feed, sorted by importance_score DESC
- Fear & Greed widget: Alternative.me index with historical gauge

## VERIFICATION
- [ ] GET /sentiment → HTTP 200, real sentiment score displayed
- [ ] GET /intelligence → HTTP 200, signal strength calculated
- [ ] python3 -m services.sentiment_analyzer batch --hours=24 classifies articles
- [ ] python3 -m services.intelligence_service signal → returns composite score
- [ ] SSE stream at /api/stream/sentiment connects and pushes events
- [ ] Trending topics show real keywords from DB
- [ ] Entity tracker shows real extracted entities
- [ ] Signal strength components all calculate
- [ ] Fear & Greed index loads from Alternative.me
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-sentiment-intel
