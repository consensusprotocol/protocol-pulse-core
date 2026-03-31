# CONVERGENCE ENGINE V1 — CROSS-LLM AUDIT SYNTHESIS
## 4-Model Consensus: Gemini 2.5 Pro + GPT-4o + Grok 3 + Perplexity
## Date: March 29, 2026

---

## UNANIMOUS AGREEMENT (all 4 models)

### 1. Architecture: Three-Layer Signal System
All four models independently arrived at the same three-layer architecture:
- **Layer 1: signals_raw** — append-only immutable event store
- **Layer 2: signals_normalized** — computed domain scores on 0-100 scale
- **Layer 3: convergence_state** — cross-domain regime detection

### 2. Core Indices
All four models agree on these three proprietary indices:
- **MinerConviction (MCX)** — miner behavior under stress
- **ExchangePressure (EPX)** — exchange absorption vs distribution
- **InsiderHeat (IHX)** — political/insider salience and timing

### 3. No LLM in Scoring Loop
Universal agreement: scores must be deterministic formula outputs.
LLMs may label/explain AFTER scores are computed, never during.

### 4. Explainability Mandate
Every score must ship with:
- `headline` — one-sentence human summary
- `drivers[]` — what's pushing the score up
- `counterweights[]` — what's pushing it down
- `confidence` — data coverage metric (0-1)
- `features` — named sub-metric values for reproducibility

### 5. Current Product is "Intelligence-Shaped UI"
All four identified the same symptoms:
- "No narrative data yet"
- "No entity data"
- Score buckets pinned at neutral
- Article stream contaminated with non-Bitcoin content
- Explanations read like templates, not source-grounded reasoning

---

## KEY DIFFERENCES BETWEEN MODELS

### Gemini
- Most code-forward: provided complete Python implementations
- Proposed SQL schema (PostgreSQL-style) + SQLAlchemy models
- Included convergence_orb_api.js for 3D WebGL visualization
- Suggested routes_splitter.py utility for the 574KB routes.py problem
- Added SignalAlertService + IntelligenceAuditEngine (confidence ledger)
- Recommended Three.js Glassmorphic Shader for the Orb

### ChatGPT (GPT-4o)
- Most architecturally thorough: 5-layer backend specification
- Strongest on entity resolution and ontology requirements
- Clearest product positioning: "signal topology product"
- Best visualization spec: force-directed convergence graph
- Explicit on what to STOP doing (no X account rotation, no Three.js)
- Provided exact Pydantic response models and computation service boundaries
- Most granular formula specs (z-score based sub-metrics)

### Perplexity
- Most data-source specific: exact API endpoints and field names
- Best freshness/TTL specification per signal type
- Strongest on quality flags and degradation rules
- Recommended starting with ExchangePressure first (highest-frequency)
- Most detailed raw table schema (fetch_run_id, parse_status, lag_seconds)
- Provided exact API response shape with JSON examples

### Grok
- Strongest on business strategy: 90-day executable plan
- Best monetization framework: Commander → Enterprise → Sponsors
- Most emphatic on Bitcoin-only positioning as moat
- Clearest "claim to fame" articulation: "The Signal Orb"
- Practical on GPU utilization: local Whisper + Qwen for self-learning
- Simplest visualization approach: D3/SVG before 3D

---

## IMPLEMENTATION DECISION MATRIX

| Decision | Chosen Approach | Source |
|----------|----------------|--------|
| Database | SQLite (existing) with SQLAlchemy models | All (adapted from Gemini's PostgreSQL) |
| Signal computation | Deterministic weighted formulas | All agree |
| API framework | Flask blueprint (not FastAPI yet) | GPT-4o + practical constraint |
| Visualization | D3/SVG force graph first, 3D later | Grok + GPT-4o |
| Scoring scale | 0-100 with direction (-1/0/+1) | All agree |
| Refresh cadence | Every 5 minutes (cron) | All agree |
| Entity resolution | Deferred to V2 (table created, not populated) | GPT-4o recommendation |
| routes.py split | Deferred (too risky during engine build) | Practical |
| X Spaces integration | Optional feed, not backbone | GPT-4o + Grok |
| Confidence threshold | < 0.25 = don't render | GPT-4o + Perplexity |

---

## RISK ASSESSMENT

### Build Risks
1. **DB migration on live system** — Mitigated: db.create_all() only adds new tables
2. **Blueprint conflicts** — Mitigated: new blueprint at /api/v1/, no overlap with existing routes
3. **Data staleness** — Mitigated: confidence degrades with freshness; UI shows "updated X ago"
4. **Import cycles** — Mitigated: lazy imports in normalizer, separate models file

### Product Risks
1. **Fabricated scores persist** — Fixed: no score without features_json + explanation_json
2. **Overfit to current data** — Fixed: z_score and percentile fields for baseline comparison
3. **Commander value unclear** — Fixed: matrix endpoint gives free tier summary; convergence/graph gives Commander depth

---

## FILES TO CREATE

1. `core/models_intelligence.py` — 4 SQLAlchemy models (SignalRaw, SignalNormalized, ConvergenceState, EntityRegistry)
2. `services/signal_normalizer_service.py` — 3 indices + convergence computer + verify_engine()
3. `core/blueprints/intelligence_api_v1.py` — 5 API endpoints with fallback live computation
4. `scripts/migrate_and_run_convergence.py` — migration + cycle runner

## FILES TO MODIFY

5. `core/app.py` — register blueprint + import models
6. `crontab` — add */5 convergence cycle

## BUILD ORDER

1. Create models → 2. Migrate DB → 3. Create normalizer → 4. Verify standalone → 5. Create API blueprint → 6. Register in app.py → 7. Restart gunicorn → 8. Test all endpoints → 9. Add cron → 10. Commit + push
