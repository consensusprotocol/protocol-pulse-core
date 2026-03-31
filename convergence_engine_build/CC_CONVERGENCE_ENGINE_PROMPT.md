Read ~/protocol_pulse/PIPELINE_LAWS.md first.

═══════════════════════════════════════════════════════════════════════
MISSION: CONVERGENCE ENGINE V1 — THREE-LAYER SIGNAL ARCHITECTURE
═══════════════════════════════════════════════════════════════════════
Audited by Gemini 2.5 Pro, GPT-4o, Grok 3, and Perplexity.
All four models agree on this architecture. Implement exactly as spec'd.

GOAL: Replace all placeholder/fabricated intelligence scores with
a real, auditable, three-layer signal system that powers the
Sovereign Signal Matrix and Commander terminal.

Files you will CREATE (4 new files):
1. core/models_intelligence.py — 4 SQLAlchemy models
2. services/signal_normalizer_service.py — 3 proprietary indices
3. core/blueprints/intelligence_api_v1.py — 5 API endpoints
4. scripts/migrate_and_run_convergence.py — migration + cycle runner

Files you will MODIFY (2 files):
5. core/app.py — register new blueprint + import models
6. crontab — add convergence cycle every 5 min

DO NOT TOUCH: routes.py, assembler.py, daily_producer.py, tts_engine.py

═══════════════════════════════════════════════════════════════════════
STEP 0 — AUDIT WHAT EXISTS (read before writing anything)
═══════════════════════════════════════════════════════════════════════

cat ~/protocol_pulse/data/signals.json | python3 -m json.tool | head -40
cat ~/protocol_pulse/data/sovereign_context/latest.json | python3 -m json.tool | head -60
head -100 ~/protocol_pulse/services/intelligence_engine_v2.py
head -50 ~/protocol_pulse/core/signal_data_fetcher.py
ls ~/protocol_pulse/core/blueprints/
grep -n 'class.*db.Model' ~/protocol_pulse/core/models.py | tail -10

═══════════════════════════════════════════════════════════════════════
STEP 1 — CREATE core/models_intelligence.py
═══════════════════════════════════════════════════════════════════════

Create ~/protocol_pulse/core/models_intelligence.py with these 4 models:

### SignalRaw (append-only event store)
- id: String(64) PK, default uuid4
- source_family: String(32) NOT NULL, indexed (onchain/exchange/insider/macro/miner/whale/social)
- source_name: String(64) NOT NULL, indexed
- source_event_id: String(128) nullable
- observed_at: DateTime NOT NULL, indexed
- ingested_at: DateTime NOT NULL, default utcnow
- topic: String(32) NOT NULL, indexed
- entity_type: String(32) nullable, indexed
- entity_id: String(128) nullable, indexed
- entity_name: String(255) nullable
- asset: String(32) default "BTC", indexed
- market: String(32) nullable
- region: String(32) nullable
- polarity: Float nullable (-1.0 to +1.0)
- magnitude: Float nullable
- confidence: Float NOT NULL default 0.5
- horizon: String(16) NOT NULL default "swing"
- title: String(500) nullable
- summary: Text nullable
- url: String(1000) nullable
- raw_payload_json: Text NOT NULL
- extracted_facts_json: Text nullable
- tags_json: Text nullable
- dedupe_key: String(255) NOT NULL, unique, indexed
- is_valid: Boolean NOT NULL default True, indexed
- invalid_reason: String(255) nullable
- freshness_seconds: Integer nullable
- quality_flag: String(20) NOT NULL default "unreviewed"

### SignalNormalized (computed scores)
- id: String(64) PK, default uuid4
- signal_key: String(64) NOT NULL, indexed (miner_conviction/exchange_pressure/insider_heat)
- signal_family: String(32) NOT NULL, indexed
- computed_at: DateTime NOT NULL, indexed
- window_start: DateTime NOT NULL
- window_end: DateTime NOT NULL
- subject_type: String(32) NOT NULL default "global", indexed
- subject_id: String(128) NOT NULL default "global:bitcoin", indexed
- asset: String(32) default "BTC", indexed
- raw_value: Float NOT NULL
- score_0_100: Float NOT NULL (0-100 scale)
- z_score: Float nullable
- percentile: Float nullable
- direction: Integer NOT NULL default 0 (-1/0/+1)
- confidence: Float NOT NULL (0-1)
- freshness_seconds: Integer NOT NULL
- sample_size: Integer NOT NULL default 0
- methodology_version: String(32) NOT NULL default "v1.0.0"
- features_json: Text NOT NULL (the named feature vector — REQUIRED)
- contributing_raw_ids_json: Text NOT NULL default "[]"
- explanation_json: Text nullable (structured {headline, drivers[], counterweights[]})
- is_anomalous: Boolean NOT NULL default False
- state_label: String(32) nullable (very_low/low/neutral/elevated/extreme)
- regime_direction: String(16) nullable (bullish/bearish/neutral)

### ConvergenceState (regime engine)
- id: String(64) PK
- computed_at: DateTime NOT NULL, indexed
- regime_key: String(64) NOT NULL default "btc_global", indexed
- asset: String(32) NOT NULL default "BTC", indexed
- convergence_score: Float NOT NULL (0-100)
- fragmentation_score: Float NOT NULL (0-100)
- momentum_score: Float NOT NULL (0-100)
- conviction_score: Float NOT NULL (0-100)
- dominant_thesis_key: String(128) nullable
- dominant_thesis_label: String(255) nullable
- dominant_direction: Integer NOT NULL default 0
- confidence: Float NOT NULL
- aligned_signal_keys_json: Text NOT NULL default "[]"
- conflicting_signal_keys_json: Text NOT NULL default "[]"
- cluster_state_json: Text NOT NULL default "{}"
- thesis_candidates_json: Text NOT NULL default "[]"
- explainability_json: Text NOT NULL default "{}"
- alert_flags_json: Text NOT NULL default "[]"
- ui_payload_json: Text NOT NULL default "{}" (graph nodes/edges for Orb)
- state_changed: Boolean NOT NULL default False
- previous_state_id: String(64) nullable
- regime_label: String(64) nullable
- persistence_bars: Integer NOT NULL default 0
- methodology_version: String(32) NOT NULL default "v1.0.0"
- window_start: DateTime NOT NULL
- window_end: DateTime NOT NULL
- participating_signals: Integer NOT NULL default 0
- total_expected_signals: Integer NOT NULL default 6

### EntityRegistry (canonical entities)
- id: String(128) PK
- entity_type: String(32) NOT NULL indexed
- canonical_name: String(255) NOT NULL indexed
- display_name: String(255) NOT NULL
- slug: String(255) NOT NULL unique indexed
- primary_asset: String(32) nullable default "BTC"
- region: String(32) nullable
- tags_json: Text nullable
- aliases_json: Text nullable
- metadata_json: Text nullable
- is_active: Boolean NOT NULL default True indexed
- created_at: DateTime NOT NULL default utcnow

IMPORT from core import db. Use uuid4 for default IDs.

═══════════════════════════════════════════════════════════════════════
STEP 2 — CREATE services/signal_normalizer_service.py
═══════════════════════════════════════════════════════════════════════

This is the brain. Three deterministic indices computed from
data/signals.json + data/sovereign_context/latest.json.

NO LLM in the scoring loop. Every score is a weighted formula.

### MinerConviction (signal_key: miner_conviction, family: miner)
Inputs from signals.json + sovereign_context:
- difficulty_adjustment.percent → hashrate proxy
- on_chain.accumulation_score → reserve trend
- on_chain.coin_days_destroyed_7d → distribution pressure
- recommended_fees.fastest → fee economics
- btc_price.change_24h + btc.change_7d → price context
- STRESS BONUS: +8 if price_7d < -3 AND difficulty > 0

Formula:
  0.22 * hashrate_score(50 + 2.5 * diff_adj_pct) +
  0.20 * reserve_score(accumulation_score) +
  0.18 * outflow_score(inverse CDD) +
  0.08 * fee_score(20 + fees * 0.8) +
  0.14 * hashprice_score(50 + price_7d * 1.5) +
  0.18 * accumulation_score
  + stress_bonus
All clamped 0-100.

Direction: ≥60 → +1, <40 → -1, else 0
State labels: ≥80 extreme, ≥60 elevated, ≥40 neutral, ≥20 low, <20 very_low

EVERY result must include:
  explanation: {headline, drivers[], counterweights[]}
  features: {all named sub-metrics with values}
  confidence: data coverage ratio

### ExchangePressure (signal_key: exchange_pressure, family: exchange)
Inputs:
- futures.funding_rate → derivatives pressure
- futures.open_interest → OI context
- whale_moves.count + total_btc + fear_greed → whale activity
- options.put_call_ratio → hedging
- exchange_volume → volume context
- futures.long_short_ratio → positioning

Formula:
  0.22 * funding_score +
  0.12 * oi_score +
  0.25 * whale_score +
  0.15 * pcr_score +
  0.10 * vol_score +
  0.16 * ls_score

### InsiderHeat (signal_key: insider_heat, family: insider)
Inputs:
- polymarket.top_probability → prediction market conviction
- narrative.sentiment + article_count → narrative momentum
- active_alerts + pattern_matches → alert activity
- kol.sentiment_score + post_count_24h → KOL heat
- fear_greed → context

Formula:
  0.24 * poly_score +
  0.20 * narrative_score +
  0.18 * alert_score +
  0.22 * kol_score +
  0.16 * fg_score

### Convergence Computer
Takes list of signal results, computes:
  agreement = max(bullish, bearish) / total
  dispersion = std_dev(scores) / 50
  mean_conf = avg(confidences)
  participation = total / 6

  convergence_score = 100 * (0.45*agreement + 0.20*mean_conf + 0.20*(1-dispersion) + 0.15*participation)

Builds graph nodes (x/y from polar coords), edges (pairwise score diff).
Determines thesis key from signal combination patterns.

### Include verify_engine() self-test:
  All scores 0-100, direction in (-1,0,1), confidence 0-1
  All explanations have headline + drivers

Make it runnable standalone:
  python3 services/signal_normalizer_service.py
  → prints all scores + convergence

═══════════════════════════════════════════════════════════════════════
STEP 3 — CREATE core/blueprints/intelligence_api_v1.py
═══════════════════════════════════════════════════════════════════════

Blueprint name: intel_api_v1

5 endpoints:

GET /api/v1/intelligence/signals/latest
  → latest score per signal_key with headline, drivers, counterweights
  → params: asset, keys (CSV), subject_id

GET /api/v1/intelligence/signals/history
  → time series for one signal
  → params: signal_key (required), range (1h/6h/24h/7d/30d), limit

GET /api/v1/intelligence/convergence/latest
  → full convergence state with thesis, alerts, explainability
  → params: regime_key, asset

GET /api/v1/intelligence/convergence/graph
  → graph nodes/edges payload for Orb/Web visualization

GET /api/v1/intelligence/matrix
  → Sovereign Signal Matrix composite (combines signals + convergence)
  → This is the single API that the public intelligence page consumes

All endpoints fall back to live computation if no DB rows exist yet.

═══════════════════════════════════════════════════════════════════════
STEP 4 — CREATE scripts/migrate_and_run_convergence.py
═══════════════════════════════════════════════════════════════════════

Single script that:
1. Imports Flask app + new models
2. Calls db.create_all() (won't touch existing tables)
3. Verifies all 4 tables exist via inspector
4. Runs full convergence cycle:
   - compute_all() on normalizer
   - compute_convergence() on results
   - persist both to DB
   - print summary to stdout

Flags: --migrate-only, --cycle-only, or both (default)

═══════════════════════════════════════════════════════════════════════
STEP 5 — MODIFY core/app.py
═══════════════════════════════════════════════════════════════════════

Add to app.py imports section:
  from core.models_intelligence import SignalRaw, SignalNormalized, ConvergenceState, EntityRegistry

Add blueprint registration (AFTER existing blueprint registrations):
  from core.blueprints.intelligence_api_v1 import intel_api_v1
  app.register_blueprint(intel_api_v1)

═══════════════════════════════════════════════════════════════════════
STEP 6 — CRON SETUP
═══════════════════════════════════════════════════════════════════════

Add convergence cycle to crontab (check first, don't duplicate):
  */5 * * * * cd ~/protocol_pulse && /usr/bin/python3 scripts/migrate_and_run_convergence.py --cycle-only >> logs/convergence_cycle.log 2>&1

═══════════════════════════════════════════════════════════════════════
STEP 7 — VERIFICATION (DO NOT SKIP)
═══════════════════════════════════════════════════════════════════════

1. Run migration:
   cd ~/protocol_pulse && python3 scripts/migrate_and_run_convergence.py
   → must show ✅ for all 4 tables + convergence score

2. Run normalizer standalone:
   cd ~/protocol_pulse && python3 services/signal_normalizer_service.py
   → must show all 3 signal scores + convergence + VERIFICATION PASSED

3. Restart gunicorn:
   kill -HUP $(pgrep -f "gunicorn.*app:app" | grep -v golds | head -1)

4. Test all 5 API endpoints:
   curl -s http://localhost:5000/api/v1/intelligence/signals/latest | python3 -m json.tool | head -30
   curl -s http://localhost:5000/api/v1/intelligence/signals/history?signal_key=miner_conviction | python3 -m json.tool | head -20
   curl -s http://localhost:5000/api/v1/intelligence/convergence/latest | python3 -m json.tool | head -30
   curl -s http://localhost:5000/api/v1/intelligence/convergence/graph | python3 -m json.tool | head -40
   curl -s http://localhost:5000/api/v1/intelligence/matrix | python3 -m json.tool | head -40

   ALL must return 200 with real data. No empty arrays. No null scores.

5. Run second cycle to verify persistence:
   python3 scripts/migrate_and_run_convergence.py --cycle-only
   curl -s http://localhost:5000/api/v1/intelligence/signals/history?signal_key=miner_conviction | python3 -c "import sys,json; d=json.load(sys.stdin); print('Points:', d.get('point_count', 0))"
   → must show point_count >= 2

6. Verify crontab:
   crontab -l | grep convergence

═══════════════════════════════════════════════════════════════════════
STEP 8 — COMMIT
═══════════════════════════════════════════════════════════════════════

git add core/models_intelligence.py services/signal_normalizer_service.py core/blueprints/intelligence_api_v1.py scripts/migrate_and_run_convergence.py core/app.py
git commit -m "feat(intelligence): three-layer convergence engine — signals_raw/normalized/convergence_state models, MinerConviction+ExchangePressure+InsiderHeat indices, 5 API endpoints, auto-cycle cron"
git push

═══════════════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════════════
- NO LLM in the scoring loop. Formulas only.
- Every score must have features_json + explanation_json
- If data is missing, set confidence < 0.3, NOT score = 50
- If confidence < 0.25, do not render in UI (add note in explanation)
- Never say "Bullish 73" without evidence in drivers[]
- All scores 0-100, all confidences 0-1, all directions -1/0/+1
- DO NOT modify routes.py — use blueprint only
- DO NOT touch video pipeline files
