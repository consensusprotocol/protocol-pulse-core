Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/intelligence_terminal_v1_spec.md.
Read ~/protocol_pulse/docs/phase2/cc_phase2_overnight_master.md (for context on F2-F5 already built).
Read ~/protocol_pulse/services/sentinel.py (imports + SentinelState only — lines 1-130).
Read ~/protocol_pulse/core/blueprints/intelligence.py.
Read ~/protocol_pulse/logs/phase2_overnight.log (if it exists — check what F2-F5 completed).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROTOCOL PULSE INTELLIGENCE TERMINAL — FULL BUILD PIPELINE TO COMPLETION
Autonomous build of all remaining features. No confirmation needed. Ever.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PIPELINE STATUS — CHECK FIRST
Before starting, check what F2-F5 completed from the overnight run:
1. Read ~/protocol_pulse/logs/phase2_overnight.log
2. Check which of these exist:
   - services/sentiment_engine.py
   - services/sovereign_engine.py
   - services/etf_monitor.py
   - D3 network graph in core/templates/intelligence_terminal.html
3. For any F2-F5 feature NOT completed: run it now using the specs in
   docs/phase2/cc_phase2_overnight_master.md before proceeding.
4. Log status: [TIMESTAMP] [PIPELINE] Starting full pipeline. F2-F5 status: [...]

WRITE PROGRESS LOG to ~/protocol_pulse/logs/full_pipeline.log
Format: [HH:MM UTC] [FEATURE_ID] [STATUS: STARTED|COMPLETE|FAILED] [notes]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INVIOLABLE RULES — APPLY TO EVERY FEATURE IN THIS PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. IMPORT RULE (PERMANENT): Never `from services.X import Y` in services/*.py.
   Always importlib.util.spec_from_file_location() with Path(__file__).resolve().parent.
   Violation breaks the intelligence blueprint. See QWEN_CONTEXT_BIBLE.md.

2. THREE.JS BANNED GLOBALLY. All visualization: D3.js + SVG only.

3. NO ML IN FEATURES MARKED [RULE-BASED]. PCAF v1 GNN and TPA are the ONLY
   features that use ML — and they are explicitly flagged SKIP in this pipeline.

4. EVERY NEW FILE: test imports clean from core/ before integrating into sentinel.

5. EVERY FEATURE: foundation doc → cross-LLM audit (GPT-4o + Grok, 2 questions
   minimum) → implement → tests → commit → next. No skipping audit.

6. AUDIT SCRIPTS: save to utils/[feature]_audit.py. Results to docs/audits/.

7. GUNICORN: always from ~/protocol_pulse/core/. Never from root.

8. QWEN BIBLE: document every new bug pattern before moving on.

9. FAILURE POLICY: if a feature fails tests after 2 fix attempts, log the failure,
   commit what works, and continue to the next feature.

10. COMMIT CADENCE: git add + commit + push after EVERY feature. Never batch.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMPLETED (Phase 1):
  ✅ F-P1-1: Sentinel daemon + mempool live + PCAF v0 + 3-tier alerts + war room UI
  ✅ F-P1-2: Three-tier alert system + voice synthesis (Telegram + ElevenLabs)

COMPLETED (Phase 2 F1):
  ✅ F-P2-1: Convergence Detection — 6-pattern Matrix Layer

OVERNIGHT BUILD (Phase 2 F2-F5) — check logs, complete if needed:
  ⬜ F-P2-2: Sentiment Pulse
  ⬜ F-P2-3: Sovereign/CBDC Layer
  ⬜ F-P2-4: ETF Flow Monitor
  ⬜ F-P2-5: Network State Graph

THIS PIPELINE BUILDS (in order):
  F-P2-6: Dark Pool OTC Taint Analysis [RULE-BASED]
  F-P2-7: Miner Stress & Capitulation Model [RULE-BASED]
  F-P3-1: Whale Coordination Detection [RULE-BASED]
  F-P3-2: Jurisdiction Regulatory Intelligence Engine [RULE-BASED]
  F-P3-3: Privacy Tech Pulse [RULE-BASED]
  F-P3-4: P2P Exchange Volume Aggregator [RULE-BASED]
  F-P3-5: DeFi BTC Collateralization Monitor [RULE-BASED]
  F-P3-6: War Room UI Polish — full immersive layout, multi-panel drill-down
  F-P3-7: Backtesting Interface — run PCAF patterns against historical data
  F-P3-8: External API Layer — REST + WebSocket for institutional access
  F-P3-9: Alert History & Analytics — full alert log, precision tracking
  SKIP: PCAF v1 GNN [NEEDS DEDICATED ML SESSION — FLAG AND SKIP]
  SKIP: Temporal Predictive Analytics [NEEDS DEDICATED ML SESSION — FLAG AND SKIP]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P2-6: DARK POOL OTC TAINT ANALYSIS
"Track institutional OTC positioning on-chain before it hits reported data"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase2/dark_pool_foundation.md
Spec:
- What it does: watches for large UTXO movements (>100 BTC) that don't go to known
  exchange wallets. These are likely OTC desk flows. Flags clusters of such moves
  within 4h windows as potential institutional positioning.
- Data: mempool.space whale_txs feed (already in SentinelState — >50 BTC txs)
  + data/custodian_wallets.json (exchange addresses to exclude)
  + data/miner_wallets.json (miner addresses to exclude)
- Algorithm (rule-based, no ML):
  1. For each whale tx (>100 BTC) in last 4h: check if destination is known exchange
  2. If NOT exchange and NOT miner: classify as "dark pool candidate"
  3. If 3+ dark pool candidates within 4h: fire DARK_POOL_ACCUMULATION signal
  4. Compute: dark_pool_volume_4h_btc, dark_pool_tx_count_4h,
     exchange_destination_pct (what % IS going to exchanges — inversion signal)
- Taint tracking: simple address graph (not full blockchain taint — too expensive).
  For each dark pool candidate destination address: check if it appears again within
  72h. If same address receives multiple large inputs: elevate to WATCH.
- Output: SentinelState.dark_pool dict with:
  signal: "CLEAR"|"WATCH"|"ACCUMULATION"
  volume_4h_btc: float
  tx_count_4h: int
  top_destinations: list[str] (top 3 destination addresses, truncated)
  exchange_pct: float (% of whale flows going to exchanges — if high = distribution)
  updated_at: float

AUDIT: utils/dark_pool_audit.py — 2 models, 4 questions:
Q1: The "not exchange, not miner" heuristic for OTC detection — what is the
    false positive rate and what common transaction types will be misclassified?
Q2: Address reuse tracking within 72h — what is the minimum viable implementation
    that doesn't require a full blockchain UTXO database?
Q3: What threshold for dark_pool_tx_count triggers meaningful signal vs noise?
    Give a data-backed recommendation based on average daily whale tx frequency.
Q4: How does this feed into the Convergence Engine WAP pattern (Whale Accumulation)?
    Write the exact signal update code.

IMPLEMENT:
  services/dark_pool_engine.py
    Load via importlib.util in sentinel (NO from services.*)
    class DarkPoolEngine:
      def __init__(self, custodian_wallets_path, miner_wallets_path)
      def analyze(self, whale_txs: list, known_addresses: set) -> dict
      def _is_known_address(self, addr: str) -> bool
      def _track_address_reuse(self, addr: str, db_path: str) -> int
    SQLite table: dark_pool_addresses(address, first_seen, last_seen, tx_count, total_btc)
    Load address lists from JSON files at init — no live fetching needed

  Modify sentinel.py:
    Add dark_pool to SentinelState
    Load DarkPoolEngine via importlib.util
    Run every 5 minutes

  Modify intelligence_terminal.html:
    Add dark pool indicator to MEMPOOL LIVE panel (not a separate panel):
    "DARK POOL: [CLEAR ✓]" or "DARK POOL: [⚠ ACCUMULATION 847 BTC / 6 txs]"

TESTS:
  T1: DarkPoolEngine.analyze() returns correct signal with mock whale_txs
  T2: Known exchange addresses correctly filtered out
  T3: No from services.* imports
  T4: SSE stream contains dark_pool key

COMMIT: "feat(dark-pool): Phase 2 F6 — OTC taint analysis via whale tx destination classification"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P2-7: MINER STRESS & CAPITULATION MODEL
"Quantitative miner health score — predicts capitulation before it happens"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase2/miner_stress_foundation.md
Spec:
- Miner Health Score: composite 0-100 (100 = miners thriving, 0 = mass capitulation)
- Inputs (all already available in SentinelState or mempool.space):
  hashrate_3d: declining = stress
  difficulty_adj_pct: negative = stress
  mempool fee softness: low fees = miner revenue down = stress
  block_time_avg: high avg = hashrate dropping = stress
  coinbase_to_exchange_ratio: from dark_pool_engine (miner wallet classification)
    Uses data/miner_wallets.json — ratio of miner wallet outputs going to exchanges
- Score formula (rule-based weighted sum):
  score = 100
  if hashrate_3d declining >5%: score -= 20
  if hashrate_3d declining >15%: score -= 20 (additional)
  if difficulty_adj < -3%: score -= 15
  if difficulty_adj < -8%: score -= 15 (additional)
  if next_block_fee < 5 sat/vB for >2h: score -= 10
  if avg_block_time > 750s: score -= 10
  if coinbase_to_exchange_ratio > 2x 7d avg: score -= 20
  score = max(0, min(100, score))
- Capitulation threshold: score < 30 = WATCH, score < 15 = CRITICAL
- Historical context: store daily score in baseline_store.db
  If score is lowest in 90 days: add "90-DAY LOW" label
- Output: SentinelState.miner_health dict:
  score: int (0-100)
  label: "HEALTHY"|"STRESSED"|"CAPITULATION_WATCH"|"CAPITULATION_CRITICAL"
  components: dict (each factor's contribution)
  is_90d_low: bool
  updated_at: float

AUDIT: utils/miner_stress_audit.py — 2 models, 3 questions:
Q1: The weighted score formula — which weights are most likely wrong
    given Bitcoin's historical miner capitulation events? Cite specific events.
Q2: Coinbase-to-exchange ratio as a signal — what are the data quality risks
    given that miner_wallets.json only has a few known addresses?
Q3: How does this integrate with MCC pattern in the Convergence Engine?
    Specifically: which MCC signals does this replace or supplement?

IMPLEMENT:
  services/miner_stress_engine.py — load via importlib.util
  Add miner_health to SentinelState
  Run every 10 minutes
  Add MINER HEALTH panel to SENTINEL CORE panel in intelligence_terminal.html:
    "MINER: [████████░░] 82/100 HEALTHY" (color coded)
    If CAPITULATION_WATCH: amber. If CRITICAL: red flash.

TESTS: T1-score formula, T2-no from services.*, T3-SSE key present

COMMIT: "feat(miner-stress): Phase 2 F7 — miner health score 0-100 · capitulation early warning"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-1: WHALE COORDINATION DETECTION
"Detects synchronized large UTXO movement from taint-linked clusters + social signal"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/whale_coordination_foundation.md

Spec:
- Coordination detection: 3+ whale txs (>100 BTC) within 90-minute window
  where destination addresses share taint (appeared in same transaction historically)
- Taint check (lightweight — no full blockchain scan):
  Use dark_pool_addresses SQLite table from F-P2-6
  If 2+ of the whale tx destinations appear in same table with overlapping time windows:
  classify as "taint-linked" → coordination signal
- Social correlation: cross-reference with sentiment_engine.tier1_signal
  If whale coordination detected AND tier1_signal=True: elevate to WATCH
  If tier1_signal=False: NOTE only
- Output: SentinelState.whale_coordination dict:
  signal: "CLEAR"|"NOTE"|"WATCH"
  tx_count_90min: int
  taint_linked: bool
  tier1_social_active: bool
  total_btc_90min: float
  updated_at: float

AUDIT: utils/whale_coordination_audit.py — 3 questions:
Q1: The taint-linking approach using only the dark_pool_addresses table —
    how often will this miss genuine coordination and how often will it falsely flag?
Q2: How does this feature avoid double-counting with WAP-1 in the Convergence Engine?
    They both watch large UTXO movement — what is the exact differentiation?
Q3: What is the minimum coordination event size that makes this signal actionable
    vs noise? Defend with a frequency analysis of historical whale activity.

IMPLEMENT:
  services/whale_coordination_engine.py — load via importlib.util
  Add whale_coordination to SentinelState
  Run every 5 minutes
  Add coordination indicator to MEMPOOL LIVE panel (alongside dark pool)

COMMIT: "feat(whale-coord): Phase 3 F1 — whale coordination detection via taint-linked UTXO clustering"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-2: JURISDICTION REGULATORY INTELLIGENCE ENGINE
"50-jurisdiction legislative monitoring · NLP classification · 24h update latency"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/regulatory_intelligence_foundation.md

Spec:
- Monitoring sources (all free, RSS/public):
  BIS: https://www.bis.org/rss.htm (filter: crypto, CBDC, digital currency)
  ECB: https://www.ecb.europa.eu/rss/news.rss
  Federal Reserve: https://www.federalreserve.gov/feeds/press_all.xml
  IMF Blog: https://www.imf.org/en/Blogs/rss (filter: crypto, digital assets)
  CoinDesk Regulation: https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml
  Bitcoin Magazine Policy: https://bitcoinmagazine.com/.rss/full/
  Known hostile jurisdiction news: use jurisdiction_db.json to seed country RSS

- NLP classification (rule-based keyword matching):
  HOSTILE keywords: ban, prohibit, illegal, restrict, seize, freeze, AML, enforcement
  FRIENDLY keywords: legal tender, regulate, approve, license, ETF, approved, framework
  NEUTRAL: everything else
  Classification: each article gets label + confidence (keyword match count / total words)
  Only articles with confidence > 0.01 get classified (filters pure noise)

- Output: SentinelState.regulatory dict:
  recent_alerts: list[dict] (last 10 classified articles, last 24h)
  jurisdiction_updates: list[str] (jurisdictions mentioned in recent hostile/friendly articles)
  threat_level: "LOW"|"MEDIUM"|"HIGH" (based on hostile article count in last 24h)
  last_hostile_event: dict | None
  last_friendly_event: dict | None
  updated_at: float

- Jurisdiction classification updates:
  When a hostile article mentions a jurisdiction: flag that jurisdiction in
  jurisdiction_db.json as "pending_review" — don't auto-update, just flag.
  Write flag to: data/jurisdiction_review_queue.json
  This preserves data integrity while surfacing potential changes.

AUDIT: utils/regulatory_intel_audit.py — 3 questions:
Q1: RSS-based monitoring — what are the 3 most likely false positives
    (benign articles that get classified as hostile) and how do we filter them?
Q2: The jurisdiction_review_queue approach — is "pending_review" the right
    data model or is there a better way to handle jurisdiction classification changes?
Q3: What regulatory event in Bitcoin's history would this system have caught
    earliest? Use that as a calibration check for the keyword list.

IMPLEMENT:
  services/regulatory_intel_engine.py — load via importlib.util
  data/regulatory_feeds.json — list of RSS feed URLs with metadata
  data/jurisdiction_review_queue.json — created at runtime if needed
  Add regulatory to SentinelState
  Run every 30 minutes
  Update existing SOVEREIGN LAYER panel with regulatory threat level indicator

COMMIT: "feat(reg-intel): Phase 3 F2 — regulatory intelligence engine · 50-jurisdiction NLP monitoring"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-3: PRIVACY TECH PULSE
"Coinjoin volume · Tor node % · Taproot adoption · Nostr growth · Silentpayments"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/privacy_tech_foundation.md

Spec — all data from mempool.space + public APIs:
- Coinjoin volume: GET https://mempool.space/api/v1/mining/blocks
  Detect coinjoin heuristic: tx with multiple equal-value outputs + many inputs
  Compute: coinjoin_tx_count_7d, coinjoin_btc_volume_7d, vs 30d baseline
- Taproot adoption: GET https://mempool.space/api/v1/statistics
  taproot_tx_pct: percentage of confirmed txs using taproot outputs
  taproot_utxo_pct: percentage of UTXO set using taproot
- Tor Bitcoin nodes: GET https://bitnodes.io/api/v1/snapshots/latest/
  Parse: tor_node_count, total_node_count → tor_pct
  Cache 6h (bitnodes.io is slow)
- Nostr growth: count events from sentinel's Nostr relay connection
  nostr_events_24h: count of kind:1 events tagged #bitcoin in last 24h
  From existing sentiment_engine.collect_nostr() — reuse that connection
- Silentpayments: heuristic — count SP-compatible transactions
  Any tx with OP_RETURN containing SP marker bytes (0x04 prefix)
  sp_tx_7d_count, sp_adoption_trend: "growing"|"stable"|"declining"

- Output: SentinelState.privacy_tech dict:
  coinjoin_signal: "NORMAL"|"ELEVATED"|"SPIKE" (vs 30d baseline)
  coinjoin_7d_btc: float
  taproot_tx_pct: float
  taproot_utxo_pct: float
  tor_node_pct: float
  nostr_24h_events: int
  sp_7d_count: int
  sovereignty_index: float (0-100, composite of all metrics)
  updated_at: float

NO AUDIT NEEDED for this feature — pure data aggregation, no design decisions.

IMPLEMENT:
  services/privacy_tech_engine.py — load via importlib.util
  Add privacy_tech to SentinelState
  Run every 1 hour (most metrics are slow-moving)
  Add PRIVACY TECH panel to intelligence_terminal.html:
    Small panel showing sovereignty_index gauge (0-100)
    Taproot: 67% | Tor: 18% | Coinjoin: NORMAL | Nostr: 2,847/24h

COMMIT: "feat(privacy-tech): Phase 3 F3 — privacy tech pulse · sovereignty index · taproot/coinjoin/Tor/Nostr"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-4: P2P EXCHANGE VOLUME AGGREGATOR
"Non-KYC P2P volume by region · capital flight signal · 1-hour buckets"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/p2p_volume_foundation.md

Spec:
- HodlHodl (primary): https://hodlhodl.com/api/v1/offers — already in signal_feeds.py
  Parse offer counts by currency/country as volume proxy
- LocalBitcoins historical: API deprecated — use cached public data as baseline only
- Bisq: no public API — skip
- Volume proxy methodology: offer count is not volume, but is a reliable proxy.
  Offer count * median_offer_size = estimated volume.
  median_offer_size default: 0.05 BTC (conservative estimate)
- Regional aggregation using jurisdiction_db.json iso2 codes
- Capital flight signal: if P2P offer count in any jurisdiction classified
  "hostile" or "banned" spikes >200% vs 7d avg: fire capital_flight signal
- Output: SentinelState.p2p_volume dict:
  total_offers: int
  by_region: dict (top 10 regions by offer count)
  capital_flight_jurisdictions: list[str] (jurisdictions with spike)
  signal: "CLEAR"|"ELEVATED"|"CAPITAL_FLIGHT"
  updated_at: float

NO AUDIT NEEDED — simple data aggregation.

IMPLEMENT:
  Extend services/sovereign_engine.py with p2p_volume methods (don't create new file)
  Update SentinelState.sovereign to include p2p_volume sub-dict
  Update sovereign panel in HTML to show top 3 P2P regions

COMMIT: "feat(p2p-volume): Phase 3 F4 — P2P exchange volume aggregator · capital flight signal"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-5: DEFI BTC COLLATERALIZATION MONITOR
"WBTC + cbBTC on Ethereum · Bitcoin-as-collateral demand in DeFi"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/defi_btc_foundation.md

Spec:
- WBTC supply: GET https://api.llama.fi/protocol/wrapped-bitcoin
  Parse: currentChainTvls.Ethereum — total WBTC locked
- cbBTC: GET https://api.llama.fi/protocol/coinbase-wrapped-btc
- Total BTC-backed assets on DeFi: WBTC + cbBTC (in BTC terms)
- Mint/burn rate: compare current vs previous reading to get 24h delta
- Interpretation:
  Rising WBTC/cbBTC = more BTC being used as DeFi collateral = demand signal
  Falling = BTC leaving DeFi = risk-off or self-custody migration
- Output: SentinelState.defi_btc dict:
  wbtc_supply_btc: float
  cbbtc_supply_btc: float
  total_btc_in_defi: float
  delta_24h_btc: float
  signal: "ACCUMULATING"|"NEUTRAL"|"DECLINING"
  updated_at: float

NO AUDIT NEEDED.

IMPLEMENT:
  Extend services/etf_monitor.py with defi_btc methods
  Add defi_btc to ETF panel in HTML: "DeFi BTC: 153,420 BTC (+240 24h)"
  Run every 30 minutes

COMMIT: "feat(defi-btc): Phase 3 F5 — WBTC + cbBTC collateral monitor · DeFi BTC demand signal"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-6: WAR ROOM UI POLISH
"Full immersive layout · drill-down on every data element · multi-panel coherence"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/war_room_ui_foundation.md

Spec — pure frontend, no backend changes:
- Audit the current intelligence_terminal.html.
  Read the full file. Identify every panel. List what's present and what's still
  showing placeholder/stub values after F2-F5 and this pipeline.
- Layout coherence:
  Ensure all panels are actually in the grid (not just HTML stubs)
  Ensure CSS grid produces the correct 6-zone layout from the spec zone map
  Ensure all SSE keys have corresponding JS updateX() functions
  Ensure all panels have proper empty states (not just blank)
- Drill-down interactions:
  Every panel: clicking the panel header expands a detail overlay showing
  raw signal values, last updated timestamps, and data source labels
  This overlay uses existing CSS variables — no new design system
- Alert Rail enhancement:
  CRITICAL alerts: flash entire page border red for 2 seconds (CSS animation)
  WATCH alerts: amber pulse on Alert Rail only
  NOTE count badge: shows number, clicking opens alert history modal
- Data freshness indicators:
  Every data value: if last_updated > 2x expected refresh interval, show
  value in muted gray with "~" prefix (already specced — verify it's implemented)
- Keyboard shortcuts:
  [C] jump to Convergence panel
  [S] jump to Sentinel Core
  [M] jump to Mempool Live
  [?] show keyboard shortcut help overlay
- Mobile: at <768px, stack panels vertically, hide network graph, show alert rail only

NO AUDIT NEEDED — pure CSS/JS polish.

IMPLEMENT: All changes to core/templates/intelligence_terminal.html only.
Thorough QA: check every panel renders, every SSE key updates its panel,
no JavaScript errors in browser console (test via curl + visual check).

COMMIT: "feat(war-room): Phase 3 F6 — full UI polish · drill-down · alert rail · keyboard shortcuts"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-7: ALERT HISTORY & PRECISION TRACKING
"Full alert log · precision metrics · user-rated relevance · 90-day performance"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/alert_history_foundation.md

Spec:
- All alerts already stored in sentinel_alerts.db (from Phase 1)
- This feature adds: GET /intelligence/alerts — full alert history page
  Not a modal. A full page: protocolpulse.io/intelligence/alerts
  Shows: paginated alert list, each with tier/rule/message/timestamp/ack status
  Filters: by tier (CRITICAL/WATCH/NOTE), by rule, by date range
- Precision tracking:
  For each CRITICAL/WATCH alert: add "Was this right?" thumbs up/down button
  Store user votes in alerts table: user_vote TEXT ("correct"|"false_positive"|null)
  Running precision score: correct / (correct + false_positive) * 100
  Display on main terminal: "PCAF Precision: 73% (11 rated)"
- Alert stats page at /intelligence/alerts/stats:
  CRITICAL precision %, WATCH precision %, total fired by type last 30d,
  most common rule triggers, average time from WATCH to CRITICAL

AUDIT: utils/alert_history_audit.py — 2 questions:
Q1: User-rated precision — how do we prevent gaming/noise in the rating system?
    What minimum sample size makes the precision score meaningful?
Q2: What is the single most useful alert analytics view that would help PBX
    tune alert thresholds? Design that specific view.

IMPLEMENT:
  Add alert_history and alert_stats routes to core/blueprints/intelligence.py
  Add templates: core/templates/alert_history.html, alert_stats.html
  Add vote endpoint: POST /api/intelligence/alerts/<id>/vote
  Update sentinel_alerts.db schema: ALTER TABLE alerts ADD COLUMN user_vote TEXT
  Add precision display to main terminal Alert Rail

COMMIT: "feat(alert-history): Phase 3 F7 — alert log · precision tracking · user-rated relevance"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-8: EXTERNAL API LAYER
"Authenticated REST + WebSocket for institutional access · rate-limited · versioned"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/external_api_foundation.md

Spec — authenticated API for Commander+ subscribers:
- Authentication: API key (UUID4, stored in users table, generated on demand)
  Header: X-PP-API-Key: <key>
  Rate limit: 100 req/min for Commander, 1000 req/min for Sovereign tier
- Endpoints (all return JSON, all require auth):
  GET /api/v1/state — full SentinelState snapshot
  GET /api/v1/mempool — mempool panel data
  GET /api/v1/convergence — full convergence state
  GET /api/v1/alerts — last 50 alerts with pagination
  GET /api/v1/sentiment — current sentiment state
  GET /api/v1/sovereign — sovereign layer state
  GET /api/v1/network — network graph nodes + edges
  WS  /api/v1/stream — WebSocket equivalent of SSE stream
- Rate limiting: use Flask-Limiter (already installed, see gunicorn logs)
  Store rate limit state in memory (acceptable for Phase 3)
- API key management:
  GET /intelligence/api — API key management page (auth gated)
  POST /api/v1/keys/generate — generate new API key for current user
  DELETE /api/v1/keys/<key> — revoke API key
- Documentation page: GET /api/v1/docs — JSON schema of all endpoints
  Returns: {endpoints: [{path, method, auth_required, rate_limit, response_schema}]}

AUDIT: utils/external_api_audit.py — 3 questions:
Q1: WebSocket in a gunicorn sync worker environment — what breaks and how do we fix it?
    (gevent? eventlet? separate websocket process?)
Q2: API key storage in the users table — what is the minimum viable security model?
    Hashing, rotation, scope restrictions — what do we need vs what is overkill?
Q3: What is the single most likely abuse vector for this API once it's live,
    and how do we prevent it without adding complexity that blocks legitimate use?

IMPLEMENT:
  Add API key column to users table: ALTER TABLE users ADD COLUMN api_key TEXT UNIQUE
  Add all v1 endpoints to core/blueprints/intelligence.py
  Add API management page template
  WebSocket: implement as SSE stream fallback (skip true WS for now — too complex
  with sync gunicorn. Document as "WebSocket-compatible SSE stream" — close enough.)
  Rate limit using Flask-Limiter decorators

COMMIT: "feat(api-layer): Phase 3 F8 — external REST API · auth · rate limiting · institutional access"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
F-P3-9: BACKTESTING INTERFACE
"Run any PCAF pattern or Convergence Event against historical data"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FOUNDATION DOC: docs/phase3/backtesting_foundation.md

Spec:
- What it does: replay historical alert patterns against stored signal data
  to show what the system would have said at any point in the past.
  This validates signal quality and demonstrates product credibility.
- Data available for backtest:
  signal_baselines.db: rolling 30-day signal history (grows from now forward)
  sentinel_alerts.db: alert history (grows from now forward)
  External: CoinGecko price history API (free, 365 days):
  GET https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=365
- Backtesting engine (minimal viable):
  For any stored alert: show the BTC price at alert time, and the price 24h/7d/30d later
  This answers: "When PCAF fired this WATCH alert, what happened to price afterward?"
  Store this as: alert_outcomes in sentinel_alerts.db
  Compute daily via background job: for each alert > 24h old with no outcome recorded,
  fetch historical price and compute price_at_alert, price_24h_later, price_7d_later,
  outcome: "correct_bullish"|"correct_bearish"|"no_move"|"too_early"
- Backtesting page: GET /intelligence/backtest
  Shows table of all CRITICAL + WATCH alerts with price outcomes
  Columns: date, type, rule, price_at_alert, +24h%, +7d%, outcome
  Summary stats: avg +24h% after CRITICAL, avg +7d% after WATCH, hit rate by rule

NO AUDIT NEEDED — primarily data presentation.

IMPLEMENT:
  Add alert_outcomes column to sentinel_alerts.db
  Add background job in sentinel that runs price lookback daily (uses CoinGecko history)
  Add /intelligence/backtest route + template
  Template: clean table, sortable by column, no extra chrome

COMMIT: "feat(backtest): Phase 3 F9 — alert backtesting · price outcome tracking · signal validation"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SKIP — DEDICATED ML SESSIONS REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SKIP: PCAF v1 — GNN + RL chain-state trajectory simulation
  Requires: PyTorch/TensorFlow, CUDA training pipeline, labeled dataset generation,
  model versioning, inference optimization. Dedicated session with ML infra setup.
  Write placeholder file: services/pcaf_v1_PENDING.md with spec summary.
  Log: [PIPELINE] PCAF v1 GNN — SKIPPED, requires dedicated ML session.

SKIP: Temporal Predictive Analytics — scenario simulation engine
  Requires: Monte Carlo simulation, scenario probability calibration, historical
  Bitcoin cycle training data, interactive UI. Dedicated session.
  Write placeholder file: services/tpa_PENDING.md with spec summary.
  Log: [PIPELINE] TPA — SKIPPED, requires dedicated ML session.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETION SEQUENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After all features complete:

1. FULL INTEGRATION TEST:
   Restart gunicorn from core/
   Run this check:
   python3 -c "
   import urllib.request, json
   r = urllib.request.urlopen('http://localhost:5000/api/intelligence/state', timeout=5)
   state = json.loads(r.read())
   required_keys = ['network','pcaf_v0','alerts','convergence','sentiment',
                    'sovereign','dark_pool','miner_health','whale_coordination',
                    'regulatory','privacy_tech','network_graph']
   missing = [k for k in required_keys if k not in state]
   print('MISSING:', missing if missing else 'NONE')
   print('PRESENT:', [k for k in required_keys if k in state])
   "
   Note: this endpoint requires Commander auth — test via localhost bypass if needed.

2. SSE COMPLETENESS CHECK:
   curl -s -N http://localhost:5000/api/intelligence/stream --max-time 5 | head -c 1000
   Verify all keys present in stream.

3. WRITE COMPLETION SUMMARY to ~/protocol_pulse/logs/full_pipeline.log:
   [COMPLETE] Protocol Pulse Intelligence Terminal — Full Build Pipeline Complete
   Features shipped: [list each]
   Features skipped (ML): PCAF v1 GNN, Temporal Predictive Analytics
   Total commits: [git log --oneline since pipeline start | wc -l]
   Build started: [from log]
   Build ended: [now]

4. FINAL COMMIT:
   git add logs/full_pipeline.log services/pcaf_v1_PENDING.md services/tpa_PENDING.md
   git commit -m "ops: Intelligence Terminal Phase 2+3 complete — 11 features shipped · 2 ML features flagged"
   git push

5. QWEN BIBLE FINAL ENTRY:
   Append to docs/QWEN_CONTEXT_BIBLE.md:
   ## FULL PIPELINE COMPLETION — [date]
   All Phase 2+3 rule-based features complete.
   Services architecture: all new engines load via importlib.util from sentinel.py.
   Pending ML sessions: PCAF v1 GNN (services/pcaf_v1_PENDING.md),
   TPA scenario engine (services/tpa_PENDING.md).
   Terminal URL: https://protocolpulse.io/intelligence
   API base: https://protocolpulse.io/api/v1/

