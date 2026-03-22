Below is a hard-nosed 2026-level review of the spec. I’m treating the current gospel as a strong v1 foundation, but not yet “world-class financial intelligence platform.” It has sentiment, narratives, anomaly detection, and dashboards—but it is still mostly a reporting layer. To become exceptional, it needs to evolve into a real-time intelligence system with explainability, forecasting, personalization, event correlation, and operational rigor.

---

# Executive verdict

**Current spec quality:** good foundation, not yet elite.  
**Biggest gap:** it classifies articles, but does not yet produce a **decision-grade intelligence graph** that answers:
- what changed,
- why it changed,
- who is driving it,
- whether it matters,
- what historically happens next,
- and who should be alerted.

Right now it is “AI-enhanced sentiment dashboard.”  
For 2026, it should be “real-time Bitcoin narrative intelligence operating system.”

---

# 1. MISSING FEATURES

## 1) Multi-dimensional sentiment, not just bullish/bearish/neutral
The current schema is too coarse. Financial intelligence in 2026 should separate:
- **market sentiment**: bullish / bearish / neutral
- **policy sentiment**: favorable / hostile / uncertain
- **institutional sentiment**: accumulation / caution / distribution
- **miner sentiment**
- **developer/ecosystem sentiment**
- **retail sentiment**
- **macro spillover sentiment**

A single article can be bullish for price but bearish for miners, or positive for adoption but negative for regulation. You need **aspect-based sentiment analysis** and **stakeholder-targeted sentiment**.

### Add:
- `sentiment_dimensions JSON`
- `target_entities JSON`
- `time_horizon TEXT` (`intraday|short_term|medium_term|structural`)
- `market_impact_direction TEXT`
- `market_impact_magnitude REAL`

This turns sentiment into something traders and analysts can actually use.

---

## 2) Event extraction + causal intelligence
Narrative labels are good, but still too shallow. The system should extract:
- **event type**: ETF approval, SEC action, exchange outage, treasury purchase, mining difficulty adjustment, sovereign adoption, protocol upgrade
- **causal claim**: “ETF inflows are driving price optimism”
- **confidence in causality**
- **linked market variables**: price, volume, funding, hashrate, ETF flows, stablecoin issuance

This enables “why” dashboards instead of just “what people are saying.”

### Add:
- `event_type`
- `event_entities`
- `causal_driver`
- `causal_confidence`
- `linked_market_signals JSON`

And a service:
- `services/event_intelligence.py`

---

## 3) Narrative lifecycle tracking
The spec extracts a narrative label per article, but does not model **narrative emergence, acceleration, saturation, decay, and reversal**.

World-class intelligence platforms track:
- first seen timestamp
- velocity of mentions
- sentiment by narrative over time
- cross-source spread
- persistence half-life
- narrative conflict pairs
- narrative regime shifts

Example:
- “regulatory clarity” rising for 3 days
- “miner selling pressure” collapsing
- “ETF flows” still dominant but decelerating

### Add table:
```sql
CREATE TABLE narrative_timeseries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts DATETIME,
  narrative_label TEXT,
  mention_count INTEGER,
  avg_sentiment_score REAL,
  momentum_score REAL,
  source_diversity REAL,
  novelty_score REAL
);
```

This is a major missing differentiator.

---

## 4) Source credibility and influence weighting
Not all articles should count equally. A reposted low-quality blog and a major institutional note should not have equal impact.

Need:
- source authority score
- author credibility score
- originality score
- syndication detection / duplicate clustering
- recency decay
- engagement proxy if available
- market-moving source boost

### Add:
- `source_authority_score`
- `duplicate_cluster_id`
- `originality_score`
- `influence_weight`

Then compute sentiment and narrative aggregates using weighted scoring, not raw counts.

---

## 5) Cross-modal intelligence
By 2026, “media platform intelligence” should not be text-only. Missing:
- YouTube transcript ingestion
- podcast transcript ingestion
- X/Twitter post clustering from trusted accounts
- SEC filings / press release parsing
- FOMC / regulator speech transcript parsing
- earnings call snippets from public miners / exchanges

Even if phase 1 stays article-first, the architecture should support **multi-modal source adapters**.

### Add abstraction:
- `content_items` or `intel_documents` table with `source_type`
Instead of overloading `articles` forever.

---

## 6) Predictive analytics / forward-looking signals
Current spec is descriptive. 2026 products need:
- probability of sentiment continuation over next 6h / 24h
- probability of narrative breakout
- expected volatility regime shift
- confidence interval around signal strength
- “historically similar days” retrieval

### Add:
- `forecast_score_6h`
- `forecast_score_24h`
- `regime_classification`
- `historical_analog_ids`

This can be a lightweight model first, not necessarily a giant ML stack.

---

## 7) Explainability layer
If Claude says “bearish / ETF outflows narrative,” users need to know why.

Need:
- evidence snippets from article
- extracted rationale
- confidence decomposition
- model version used
- prompt version used
- fallback classifier used
- audit trail for reclassification

### Add:
```sql
ALTER TABLE articles ADD COLUMN sentiment_rationale TEXT;
ALTER TABLE articles ADD COLUMN sentiment_evidence TEXT; -- JSON array of quotes/spans
ALTER TABLE articles ADD COLUMN sentiment_model TEXT;
ALTER TABLE articles ADD COLUMN sentiment_prompt_version TEXT;
ALTER TABLE articles ADD COLUMN sentiment_revision INTEGER DEFAULT 1;
```

Without this, the system will feel opaque and hard to trust.

---

## 8) User personalization and alerting
Missing entirely:
- watchlists: narratives, entities, sources
- custom anomaly thresholds
- “alert me when BlackRock + ETF flows + bullish sentiment spike”
- digest personalization by role: trader, journalist, allocator, miner, policy analyst
- timezone-aware daily reports
- portfolio-aware sentiment overlays

This is a major monetization and retention gap.

---

## 9) Correlation and lead-lag analysis
The current anomaly logic is simplistic. A world-class system should detect:
- sentiment leading price
- price leading sentiment
- narrative leading ETF flows
- hashrate changes lagging miner sentiment
- source clusters preceding volatility spikes

Need rolling lead-lag and Granger-style heuristics, even if lightweight.

### Add event types:
- `lead_lag_signal`
- `narrative_price_divergence`
- `sentiment_price_divergence`

This is where intelligence becomes alpha.

---

## 10) Contrarian / divergence signals
Very valuable and missing:
- bullish media sentiment while price weakens
- bearish headlines while ETF flows remain strong
- narrative concentration risk: too much consensus around one story
- source disagreement index

These are often more useful than raw sentiment.

### Add metrics:
- `dispersion_score`
- `consensus_score`
- `contrarian_signal_score`
- `source_disagreement_score`

---

## 11) Knowledge graph / entity relationship graph
The spec mentions entity relationship tracker, but not the actual graph model.

Need:
- entity co-mention graph
- relation types: invests_in, criticizes, regulates, partners_with, accumulates, liquidates
- temporal graph changes
- graph centrality
- “new relationship detected” events

This is a huge differentiator for institutional users.

---

## 12) Backtesting and signal quality measurement
No serious intelligence product should ship without measuring whether its signals are useful.

Need:
- precision/recall on anomaly detection
- sentiment-to-price correlation by horizon
- narrative breakout predictive value
- false positive rates by source
- model drift monitoring
- human review queue for low-confidence outputs

Without this, the team will have no idea whether the “AI brain” is actually working.

---

# 2. CUTTING-EDGE 2026 TOOLS

Below are concrete tools/protocols/techniques that should be considered.

## LLM / NLP stack
- **Anthropic Claude Haiku 4.5** for high-volume classification, as spec says
- **Claude Sonnet 4.5** for report synthesis and difficult low-confidence reclassification
- **OpenAI text-embedding-4 / equivalent 2026 embedding model** for semantic clustering and retrieval
- **Cohere Rerank v4** or equivalent for evidence ranking in explainability
- **spaCy 4.x financial pipelines** for deterministic NER fallback
- **GLiNER / modern zero-shot NER** for flexible entity extraction
- **Instructor / PydanticAI / Outlines** for schema-constrained structured outputs
- **vLLM** or **SGLang** if self-hosting smaller extraction models for cheap deterministic tasks
- **BERTopic 2026 variants** or **Top2Vec-style topic discovery** for unsupervised narrative emergence
- **sentence-transformers finance-tuned embeddings** for duplicate detection and clustering
- **Presidio** or equivalent if any privacy-sensitive text enters the pipeline

## Streaming / real-time infra
- **SSE is fine for browser fanout**, but also add:
  - **WebSockets** for authenticated personalized streams
  - **NATS JetStream** or **Redpanda** for internal event bus
  - **Cloudflare Queues / Durable Objects** or **Upstash Kafka** for lightweight edge-friendly eventing
- **Server-sent events for public stream**, **WebSocket for premium/private watchlists**
- **CDC/event sourcing** patterns for article classification lifecycle

## Data / analytics
- **DuckDB** for local analytical rollups and report generation
- **ClickHouse** for time-series + event analytics if scale grows
- **Apache Arrow / Polars** for fast in-process analytics
- **TimescaleDB** if staying in Postgres and wanting hypertables
- **dbt** for reproducible intelligence metric transformations
- **Feast** or lightweight feature store if predictive models are added

## Graph / relationship intelligence
- **Neo4j** or **Memgraph** for entity relationship graph
- If avoiding separate graph DB, use **Postgres + pgvector + recursive CTEs** for a simpler first pass
- **GraphRAG-style retrieval** for “why is this entity suddenly important?”

## Search / retrieval
- **pgvector** for semantic similarity and analog day retrieval
- **Meilisearch / Typesense** for blazing-fast faceted search over narratives/entities
- **BM25 + vector hybrid retrieval** for evidence and historical analogs

## Visualization
- **Observable Plot**, **ECharts 6**, or **Apache ECharts GL** for advanced interactive charts
- **D3 only where custom is necessary**
- **Sigma.js / Cytoscape.js** for entity relationship graph
- **WebGL-based heatmaps** for high-density timeline views
- **Motion One / Framer Motion** for fluid microinteractions
- **View Transitions API** for seamless dashboard state changes

## ML / anomaly detection
- **River** for online anomaly detection and streaming stats
- **Kats** / **Merlion** / **PyOD** for time-series anomaly detection
- **ruptures** for change-point detection
- **prophet-like tools are too basic alone**; use online z-score + change-point + narrative divergence ensemble

## Observability / eval
- **OpenTelemetry** end-to-end traces
- **Langfuse / Helicone / Braintrust** for LLM tracing, prompt versioning, evals
- **Arize Phoenix** for model drift and extraction quality
- **Great Expectations** or **Soda** for data quality checks

---

# 3. UX ELEVATION

## 1) “Why now?” intelligence cards
Every major signal should answer:
- what changed
- compared to what baseline
- what is driving it
- what entities are involved
- what historically happened next

Example:
> “Bullish sentiment +18 vs 24h baseline, driven by ETF flow coverage and BlackRock mentions. Similar setups preceded above-average 24h volatility in 7 of the last 10 cases.”

That feels 2027. A gauge alone does not.

---

## 2) Live narrative tape
A real-time horizontally scrolling or stacked “narrative tape”:
- ETF flows ↑
- miner selling pressure ↓
- regulatory clarity ↑
- exchange solvency concerns ↑

Each item pulses on update, can be clicked, and expands into evidence. This is much more alive than a static dashboard.

---

## 3) Explainable hover states
Hover any sentiment badge and show:
- confidence
- rationale
- evidence quote
- narrative
- importance
- source weight

This makes AI output feel inspectable, not magical.

---

## 4) Narrative map / constellation
A graph or force-map showing:
- narratives
- linked entities
- sentiment color
- momentum size
- relationship edges

Users can visually see “ETF flows” connected to BlackRock, IBIT, inflows, institutional adoption. This is a premium-feeling UX.

---

## 5) Time-travel replay mode
A slider to replay the last 24h / 7d:
- sentiment score changes
- narratives emerging
- anomalies firing
- entities rising/falling

This is extremely compelling for analysts and journalists.

---

## 6) Divergence radar
A dedicated visual for:
- media sentiment vs price
- sentiment vs ETF flows
- narrative momentum vs article volume
- source consensus vs market reaction

This is where users discover non-obvious opportunities.

---

## 7) Personalized command palette
A command bar:
- “Show me bearish miner narratives in the last 12h”
- “Alert me if ETF narrative weakens while price rises”
- “Compare today to the last halving month”

Natural-language dashboard interaction is table stakes by 2026.

---

## 8) Progressive disclosure
Default dashboard should be clean and executive-level.  
Advanced users can expand:
- methodology
- model confidence
- source weighting
- raw evidence
- historical analogs

This broadens product appeal without dumbing it down.

---

## 9) Ambient intelligence notifications
Subtle but high-end:
- live favicon pulse on anomaly
- lock-screen style in-app toast
- desktop push for premium users
- “market regime changed” full-width banner with one-click drilldown

---

## 10) Mobile-first intelligence cards
Not just responsive charts. Build:
- swipeable narrative cards
- compact anomaly feed
- tap-to-expand evidence
- haptic-feeling microanimations
- offline-cached morning brief

---

# 4. PERFORMANCE WINS

## 1) Move from cron-centric to event-driven
Current cron jobs are okay, but classification should be event-driven:
- article created → enqueue classification job immediately
- classification complete → publish event
- dashboard cache invalidated
- anomaly detector runs incrementally
- report aggregates update continuously

Cron should be fallback, not primary.

### Recommended flow
`article_ingested -> queue -> classify -> persist -> publish sentiment.classified -> update aggregates -> anomaly check -> SSE/WebSocket push`

This will be faster and more reliable.

---

## 2) Separate hot path from cold path
Hot path:
- article classification
- SSE push
- latest aggregates
- anomaly detection

Cold path:
- daily report generation
- historical recomputation
- graph centrality
- analog retrieval
- backtesting

Do not let expensive report generation block real-time updates.

---

## 3) Incremental aggregates instead of repeated scans
Don’t recalculate from last 50 articles every time. Maintain rolling materialized aggregates:
- 15m
- 1h
- 2h
- 24h
- 7d

This reduces DB load and improves anomaly speed.

### Add table:
```sql
CREATE TABLE sentiment_rollups (
  bucket_start DATETIME,
  bucket_size TEXT, -- 15m|1h|1d
  article_count INTEGER,
  weighted_score REAL,
  bullish_pct REAL,
  bearish_pct REAL,
  neutral_pct REAL,
  dominant_narrative TEXT,
  narrative_entropy REAL,
  PRIMARY KEY (bucket_start, bucket_size)
);
```

---

## 4) Idempotent job processing
Classification jobs must be idempotent:
- dedupe by article_id + model_version + prompt_version
- safe retries
- dead-letter queue
- poison message handling
- timeout and fallback classifier

Without this, restarts and retries will create chaos.

---

## 5) Confidence-based routing
Use cheap-fast model for most articles, escalate only when:
- confidence < threshold
- article importance high
- source authority high
- article contains conflicting signals
- article is unusually long/complex

This massively reduces cost while improving quality.

---

## 6) Semantic deduplication
Many crypto articles are rewrites. Cluster near-duplicates before expensive LLM work:
- hash title/summary
- embedding similarity threshold
- canonical article selection
- inherit or lightly adapt classification

This can cut costs dramatically.

---

## 7) Multi-layer caching
Need:
- in-memory cache for latest dashboard
- Redis/KeyDB for shared cache
- edge cache for public report pages
- stale-while-revalidate for non-critical widgets

Cache invalidation should be event-driven from classification completion.

---

## 8) Backpressure and rate limiting
If article volume spikes:
- queue depth monitoring
- degrade gracefully to “classification pending”
- prioritize high-authority sources
- batch low-priority articles
- preserve anomaly detection on weighted subset

This matters during major market events.

---

## 9) Data model future-proofing
The spec is overloading `articles`. That’s okay short-term, but intelligence systems usually outgrow this quickly.

Better:
- `articles` = source content metadata
- `article_intelligence` = model outputs/versioned analyses
- `intelligence_events` = derived alerts
- `narrative_timeseries` = aggregate trends
- `entity_graph_edges` = relationships

This avoids schema pain later.

---

## 10) Full observability
Track:
- classification latency p50/p95/p99
- queue lag
- SSE connection count
- anomaly false positive rate
- model confidence distribution
- reclassification rate
- cost per 1k articles
- cache hit ratio

This should be in the spec, not left to chance.

---

# 5. MONETIZATION / GROWTH

## 1) Premium alerting tiers
Strong monetization opportunity:
- free: daily summary + delayed dashboard
- pro: real-time anomaly alerts, entity watchlists, narrative alerts
- institutional: API access, lead-lag analytics, custom thresholds, export/webhooks

This feature set naturally supports subscription packaging.

---

## 2) Shareable intelligence cards
Every anomaly or daily report should generate a beautiful share card:
- branded
- timestamped
- key metric
- dominant narrative
- QR / link back

This drives organic distribution on X, Telegram, and newsletters.

---

## 3) Embeddable widgets
Offer:
- “Bitcoin Sentiment Index”
- “Dominant Narrative Today”
- “Anomaly Alert Feed”

Embeds can drive backlinks, awareness, and B2B licensing.

---

## 4) API productization
This should not just be a dashboard. Expose:
- `/api/intel/sentiment/latest`
- `/api/intel/narratives/trending`
- `/api/intel/entities`
- `/api/intel/anomalies`
- `/api/intel/forecast`

Charge for API tiers. This is likely the highest-leverage monetization path.

---

## 5) Personalized morning brief
Email / push / Telegram:
- “What changed overnight”
- top narratives
- anomalies
- entities to watch
- confidence and forecast

This is sticky and habit-forming.

---

## 6) Team collaboration features
For paid teams:
- shared watchlists
- saved views
- annotations
- internal comments on anomalies
- Slack/Discord/webhook delivery

This increases expansion revenue.

---

## 7) Historical intelligence reports
Premium users should be able to ask:
- “What was sentiment during the ETF approval week?”
- “Show all miner capitulation spikes in the last 2 years”
- “Compare this week to post-halving month 1”

This creates deep research value.

---

## 8) Reputation / trust layer
Publicly expose methodology and confidence. Trust is a growth engine in financial products.  
A “How this signal is computed” panel can materially improve conversion.

---

# 6. SECURITY / PRIVACY

## 1) Prompt injection / content poisoning defenses
You are feeding article text into LLMs. Articles can contain malicious instructions or adversarial text.

Need:
- strict prompt isolation
- schema-constrained outputs
- no tool use in classification path
- content sanitization
- max token and truncation rules
- adversarial content tests

This is a real risk.

---

## 2) Supply-chain trust for external APIs
You depend on:
- mempool.space
- fear & greed API
- LLM APIs

Need:
- retries and circuit breakers
- signed or validated responses where possible
- fallback providers
- stale cache behavior
- provenance metadata on external signals

---

## 3) Abuse protection on SSE/WebSocket endpoints
Real-time streams can be abused.

Need:
- connection caps per IP/user
- auth for premium/private streams
- heartbeat/timeout handling
- replay protection if event IDs are used
- CDN/proxy compatibility
- origin checks / CSRF considerations for authenticated streams

---

## 4) Auditability of AI outputs
Financial intelligence needs traceability.

Store:
- model version
- prompt version
- classification timestamp
- source text hash
- output schema version
- reclassification reason

This is essential for debugging and trust.

---

## 5) Data retention and privacy policy
If user personalization/watchlists/alerts are added:
- encrypt user preferences at rest
- minimize PII
- retention windows
- export/delete support
- role-based access for internal analysts

---

## 6) Secrets and key isolation
Separate API keys by environment and service.  
Rate-limit and budget-guard LLM usage to prevent runaway cost or abuse.

---

## 7) Integrity checks for article mutations
If article content changes after classification:
- detect content hash mismatch
- mark intelligence stale
- trigger reclassification

Otherwise your sentiment can silently drift from the underlying content.

---

## 8) Financial disclaimer / non-advice boundaries
If predictive analytics and alerts are added, legal/product language matters:
- not investment advice
- methodology transparency
- confidence and uncertainty display
- no false precision

---

# 7. TOP 5 P0 ADDITIONS

## 1) [VERSIONED INTELLIGENCE PIPELINE + EXPLAINABILITY]
Add a separate versioned intelligence record per article with rationale, evidence snippets, model version, prompt version, and confidence decomposition. This makes every classification auditable, debuggable, and trustworthy instead of opaque.
**Why it’s P0:** Without explainability and versioning, the AI layer will be fragile, hard to improve, and difficult for users to trust—especially in financial contexts.

---

## 2) [EVENT-DRIVEN REAL-TIME ARCHITECTURE]
Replace cron-first thinking with an event pipeline: article ingestion triggers queue-based classification, aggregate updates, anomaly checks, and SSE/WebSocket fanout. Cron remains only as catch-up and repair.
**Why it’s P0:** This is the difference between a dashboard that updates eventually and a true real-time intelligence product.

---

## 3) [NARRATIVE TIMESERIES + LIFECYCLE TRACKING]
Track each narrative over time with momentum, novelty, source diversity, sentiment, and decay. Surface emerging, accelerating, peaking, and fading narratives—not just labels on individual articles.
**Why it’s P0:** Narrative intelligence is explicitly the product differentiator; without lifecycle tracking, you only have tagging, not intelligence.

---

## 4) [WEIGHTED SIGNAL QUALITY MODEL]
Introduce source authority, duplicate clustering, originality, article importance, and confidence-based weighting into all aggregate scores and anomaly detection. Not all articles should influence the market intelligence layer equally.
**Why it’s P0:** Raw article counts produce noisy, gameable, low-trust signals. Weighted intelligence is mandatory for institutional-grade quality.

---

## 5) [DIVERGENCE + LEAD/LAG INTELLIGENCE]
Add detection for sentiment/price divergence, narrative/flow divergence, and rolling lead-lag relationships with market variables. Surface “consensus is rising but price is not confirming” and similar high-value signals.
**Why it’s P0:** These are the signals users actually pay for because they are more actionable than simple bullish/bearish summaries.

---

# Additional schema upgrades I strongly recommend

## Article intelligence split
Instead of only mutating `articles`, add:

```sql
CREATE TABLE IF NOT EXISTS article_intelligence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id INTEGER NOT NULL,
  model_task TEXT NOT NULL, -- sentiment|narrative|entity|event
  model_name TEXT NOT NULL,
  model_version TEXT,
  prompt_version TEXT,
  output_json TEXT NOT NULL,
  confidence REAL,
  rationale TEXT,
  evidence_json TEXT,
  source_text_hash TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  superseded_by INTEGER,
  UNIQUE(article_id, model_task, model_name, prompt_version, source_text_hash)
);
```

## Rollups
```sql
CREATE TABLE IF NOT EXISTS sentiment_rollups (
  bucket_start DATETIME NOT NULL,
  bucket_size TEXT NOT NULL,
  weighted_score REAL,
  bullish_pct REAL,
  bearish_pct REAL,
  neutral_pct REAL,
  article_count INTEGER,
  source_weight_sum REAL,
  dominant_narrative TEXT,
  narrative_entropy REAL,
  anomaly_score REAL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (bucket_start, bucket_size)
);
```

## Entity graph
```sql
CREATE TABLE IF NOT EXISTS entity_edges (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_a TEXT NOT NULL,
  entity_b TEXT NOT NULL,
  relation_type TEXT,
  weight REAL DEFAULT 1,
  sentiment REAL,
  first_seen DATETIME,
  last_seen DATETIME,
  mention_count INTEGER DEFAULT 1
);
```

## User alerts
```sql
CREATE TABLE IF NOT EXISTS user_intel_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  alert_type TEXT NOT NULL,
  config_json TEXT NOT NULL,
  channel TEXT NOT NULL, -- email|push|webhook|telegram
  enabled INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

# Final blunt assessment

The current spec is a **strong dashboard implementation spec**, but not yet a **world-class intelligence platform spec**.

If you build it exactly as written, you’ll get:
- article-level sentiment,
- a daily report,
- some anomaly banners,
- a decent dashboard.

If you add the P0 items above, you’ll get:
- a real-time, explainable, weighted, narrative-aware intelligence engine,
- with premium-grade alerts,
- stronger trust,
- better monetization,
- and a much clearer path to becoming the “Bloomberg terminal for Bitcoin media narratives.”

If you want, I can next turn this into a **revised 2026 gospel spec** with:
- upgraded architecture,
- exact DB migrations,
- event schemas,
- API contracts,
- queue topology,
- model routing rules,
- and a phased implementation plan.