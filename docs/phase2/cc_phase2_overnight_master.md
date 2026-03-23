Read ~/protocol_pulse/PIPELINE_LAWS.md.
Read ~/protocol_pulse/docs/VISUAL_DESIGN_SYSTEM.md.
Read ~/protocol_pulse/docs/QWEN_CONTEXT_BIBLE.md.
Read ~/protocol_pulse/docs/intelligence_terminal_v1_spec.md.
Read ~/protocol_pulse/docs/phase2/convergence_detection_v1_spec.md (first 50 lines — architecture patterns to follow).
Read ~/protocol_pulse/services/sentinel.py (imports + SentinelState dataclass only — lines 1-120).
Read ~/protocol_pulse/core/blueprints/intelligence.py.
Read ~/protocol_pulse/core/templates/intelligence_terminal.html (first 100 lines — CSS vars + panel structure).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTONOMOUS OVERNIGHT BUILD — PHASE 2 FEATURES F2–F5
Protocol Pulse Intelligence Terminal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MISSION: Build 4 Phase 2 features sequentially, fully autonomously.
No confirmation needed at any step. No pausing. No asking questions.
Each feature: write foundation doc → run cross-LLM audit → implement → test → commit → next.
If a feature fails its tests, document in QWEN Bible, commit what works, continue to next.

INVIOLABLE RULES FOR ALL FEATURES:
1. NEVER use `from services.X import Y` anywhere in services/*.py files.
   ALWAYS use importlib.util.spec_from_file_location() with Path(__file__).resolve().parent.
   This is PERMANENT. Violation breaks the intelligence blueprint. See QWEN_CONTEXT_BIBLE.md.
2. Gunicorn must always run from ~/protocol_pulse/core/ — never from root.
3. Every bug found: document in QWEN_CONTEXT_BIBLE.md before moving on.
4. All new files: git add + commit + push after each feature, not at the end.
5. Three.js is GLOBALLY BANNED. Network graph uses D3.js force simulation only.
6. No ML models in Phase 2. All features are deterministic/rule-based.

WRITE PROGRESS LOG to ~/protocol_pulse/logs/phase2_overnight.log after each milestone.
Format: [TIMESTAMP] [FEATURE] [STATUS] message

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE F2 — SENTIMENT PULSE
"Influence-weighted NLP across X, Nostr, Reddit — real-time score -100 to +100"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP F2-1: Write foundation doc
Save to: docs/phase2/sentiment_pulse_foundation.md

Foundation doc must specify:
- Data sources: X (Nitter scraper — existing infra at x_spaces_scraper/),
  Nostr (direct relay connections: wss://relay.damus.io, wss://relay.nostr.info),
  Reddit API (r/Bitcoin, r/CryptoCurrency — public JSON endpoint, no auth needed:
  https://www.reddit.com/r/Bitcoin/new.json?limit=25),
  GitHub (bitcoin/bitcoin commit activity proxy for dev sentiment)
- Influence weighting: 3 tiers.
  Tier 1 (OG/Builder, weight 3.0): accounts with >5yr Bitcoin-specific history, verified
  developers. Seed list: npub of known builders from existing x_spaces_scraper TIER1 handles.
  Tier 2 (Amplifier, weight 1.5): high-reach accounts >10K followers posting Bitcoin content.
  Tier 3 (Retail, weight 0.5): everyone else.
- Scoring formula: weighted_positive_count - weighted_negative_count, normalized to -100/+100
  using rolling 7-day max/min for normalization. Smoothed with 30-min EMA.
- Sentiment classification: use keyword + simple heuristic scoring (no ML).
  Positive keywords: accumulate, bullish, buy, hodl, orange, sovereign, freedom, ATH, moon
  Negative keywords: dump, crash, ban, scam, sell, bearish, regulation, seized, dead
  Neutral: most posts. Only posts with >2 keyword matches in either direction get scored.
- Update frequency: 30 seconds
- Output: SentinelState.sentiment dict with:
  score: float (-100 to +100)
  score_30m_ago: float (for trend direction)
  trend: str ("rising" | "falling" | "stable")
  source_breakdown: {x: float, nostr: float, reddit: float}
  volume_24h: int (total posts scored)
  top_entities: list[str] (top 5 most-mentioned: addresses, people, topics)
  tier1_signal: bool (True if any Tier 1 account posted in last 30 min)
  updated_at: float

STEP F2-2: Run cross-LLM audit (product + build combined, 1 cycle each to save time)
Write audit script: utils/sentiment_pulse_audit.py
Run it. Two models (GPT-4o + Grok), 6 questions:
Q1: Is keyword heuristic good enough or does this need embeddings? Defend your answer.
Q2: What is the biggest false positive risk in the sentiment score? Design the guard rail.
Q3: Nostr relay connections — what happens when relays go down? Design the fallback.
Q4: The influence weight system — how do we prevent a single Tier 1 account from
    dominating the score? Design the normalization.
Q5: How does this integrate with the Convergence Engine? Which convergence pattern
    signals does sentiment feed? Be specific about the data contract.
Q6: Frontend panel design — what is the minimum viable but genuinely impressive
    Sentiment Pulse panel? Describe exact layout, every data element, every state.

Save cycle 1 results to: docs/audits/sentiment_pulse_audit_2026-03-23.md
Synthesize findings. Update foundation doc with key audit decisions.

STEP F2-3: Implement

FILES TO CREATE:
  services/sentiment_engine.py — async sentiment collector + scorer
    class SentimentEngine:
      async def collect_x(session) → list[dict]  # uses existing nitter scraper pattern
      async def collect_nostr(session) → list[dict]  # direct relay websocket
      async def collect_reddit(session) → list[dict]  # public JSON API
      async def collect_github(session) → dict  # commit count delta as proxy
      def score_post(text, author_tier) → float  # keyword heuristic
      def compute_sentiment_state(posts) → dict  # full sentiment output
      async def run_cycle(session) → dict  # called every 30s from sentinel

    NOSTR implementation:
      Connect to wss://relay.damus.io via websockets
      Send: ["REQ", "bitcoin-sentiment", {"kinds": [1], "#t": ["bitcoin", "btc"], "limit": 50, "since": unix_30m_ago}]
      Receive events, parse content, apply scoring
      Disconnect after receiving events (don't hold persistent connection — too expensive)
      Fallback: if relay unreachable, skip nostr source, log warning

    REDDIT implementation:
      GET https://www.reddit.com/r/Bitcoin/new.json?limit=25
      GET https://www.reddit.com/r/CryptoCurrency/search.json?q=bitcoin&sort=new&limit=25
      Use headers: {'User-Agent': 'ProtocolPulse/1.0'}
      Parse title + selftext. No auth needed for public endpoints.
      Cache 5 min (Reddit rate limit is strict)

    X implementation:
      Reuse existing nitter scraper pattern from x_spaces_scraper/
      Target TIER1 handles from existing config
      Parse last 30 min of posts
      If nitter unreachable: skip X source, log warning

  data/sentiment_config.yaml — tier classifications, keyword lists, weights
    Keywords loaded from here, not hardcoded.

MODIFY:
  services/sentinel.py
    Add sentiment field to SentinelState:
      sentiment: dict = field(default_factory=lambda: {
          "score": 0.0, "score_30m_ago": 0.0, "trend": "stable",
          "source_breakdown": {"x": 0.0, "nostr": 0.0, "reddit": 0.0},
          "volume_24h": 0, "top_entities": [], "tier1_signal": False,
          "updated_at": 0.0
      })
    Load SentimentEngine using importlib.util (same pattern as convergence_engine)
    Run sentiment cycle every 30s in main loop (after convergence, before state write)
    Update convergence signal SHR_4_sentiment_trending_up based on sentiment.score

  core/blueprints/intelligence.py
    Add sentiment to SSE stream payload (always present, even if zeros)
    Add GET /api/intelligence/sentiment endpoint (auth gated)

  core/templates/intelligence_terminal.html
    Add SENTIMENT PULSE panel (bottom-center per spec zone map)
    Panel shows:
      - Large score number: -100 to +100, color green(>20)/amber(-20 to 20)/red(<-20)
      - Trend arrow: ↑ rising / ↓ falling / → stable
      - Source breakdown: X ██░ 45% | Nostr ███ 60% | Reddit █░░ 22% (mini bars)
      - TIER 1 SIGNAL indicator: pulsing amber dot if tier1_signal=True
      - Volume: "2,847 posts/24h"
    JS: updateSentiment(state.sentiment) called from updateState()
    Empty state: "COLLECTING..." with blinking cursor

STEP F2-4: Tests
TEST 1: python3 -c "
import sys, asyncio; sys.path.insert(0,'.')
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('se', str(Path('services/sentiment_engine.py')))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
engine = mod.SentimentEngine()
# Test keyword scoring
score = engine.score_post('Bitcoin is bullish, accumulating heavily', 2)
assert score > 0, f'Expected positive score got {score}'
print('TEST 1 PASS: keyword scoring works')
"

TEST 2: python3 -c "
import sys, asyncio; sys.path.insert(0,'.')
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('se', str(Path('services/sentiment_engine.py')))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
engine = mod.SentimentEngine()
# Test Reddit fetch (live, no auth)
async def run():
    import aiohttp
    async with aiohttp.ClientSession() as s:
        posts = await engine.collect_reddit(s)
    print(f'Reddit: {len(posts)} posts fetched')
    assert len(posts) >= 0  # 0 is ok if rate limited
    print('TEST 2 PASS: Reddit fetch works (or gracefully returns [])')
asyncio.run(run())
"

TEST 3: python3 -c "
import sys; sys.path.insert(0,'.')
src = open('services/sentiment_engine.py').read()
assert 'from services.' not in src, 'FAIL: services.* import found'
print('TEST 3 PASS: no services.* imports')
"

TEST 4: Verify SSE contains sentiment key:
curl -s -N http://localhost:5000/api/intelligence/stream --max-time 4 | grep -c '"sentiment"'
# must be >= 1

STEP F2-5: Commit
git add services/sentiment_engine.py data/sentiment_config.yaml
git add services/sentinel.py core/blueprints/intelligence.py
git add core/templates/intelligence_terminal.html docs/QWEN_CONTEXT_BIBLE.md
git add docs/phase2/sentiment_pulse_foundation.md docs/audits/sentiment_pulse_audit_2026-03-23.md
git add utils/sentiment_pulse_audit.py
git commit -m "feat(sentiment): Phase 2 F2 — Sentiment Pulse · X+Nostr+Reddit influence-weighted NLP"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE F3 — CBDC & SOVEREIGN INTELLIGENCE LAYER
"50-jurisdiction threat map · CBDC tracker · self-custody health · capital flight signals"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP F3-1: Write foundation doc
Save to: docs/phase2/sovereign_layer_foundation.md

Foundation doc must specify:
- Jurisdiction data: static JSON database of 50 jurisdictions, each with:
  {country, iso2, bitcoin_status: "legal"|"restricted"|"hostile"|"banned",
   cbdc_status: "none"|"research"|"pilot"|"live"|"mandatory",
   capital_controls: "none"|"moderate"|"severe"|"closed",
   trend: "improving"|"stable"|"deteriorating",
   last_updated: date, notes: str}
  Seed data from: Atlantic Council CBDC tracker (public),
  Chainalysis Geography of Cryptocurrency (public summary),
  Known hostile jurisdictions: China(banned), Egypt(hostile), Qatar(hostile)
  Known friendly: El Salvador(legal+BTC tender), Portugal(legal+tax free), Switzerland

- Live monitoring (what actually polls vs static):
  LIVE (polled): BIS CBDC tracker RSS https://www.bis.org/rss.htm (filter CBDC)
  LIVE (polled): Exchange reserve ratio — already in sentinel via mempool.space wallets
  LIVE (polled): Coin Days Destroyed — mempool.space/api/v1/mining/blocks (compute from blocks)
  LIVE (polled): Coinjoin volume — mempool.space/api/v1/mining/blocks (detect coinjoin pattern)
  STATIC (updated manually or on alert): jurisdiction classifications

- Self-custody health metrics:
  exchange_reserve_ratio: (known exchange wallet balances / 21M) * 100
  cdd_7d_avg: coin days destroyed 7-day average (vs 30-day baseline)
  coinjoin_volume_7d: estimated weekly coinjoin transaction count
  taproot_adoption_pct: % of outputs using taproot (from mempool.space stats)
  lightning_capacity_btc: from existing sentinel data

- Output: SentinelState.sovereign dict with:
  top_alerts: list[dict] (CBDC/regulatory alerts from BIS/RSS, last 5)
  jurisdiction_map: list[dict] (all 50, for frontend rendering)
  custody_health: dict (exchange_reserve_ratio, cdd_signal, coinjoin_signal, taproot_pct)
  capital_flight_signal: bool (True if P2P or CDD anomaly detected)
  updated_at: float

STEP F3-2: Run cross-LLM audit
Write: utils/sovereign_layer_audit.py
5 questions, 1 cycle, GPT-4o + Grok:
Q1: Static jurisdiction database — how do we keep it fresh without manual updates?
    What automated signal can detect a jurisdiction change before it's widely reported?
Q2: Exchange reserve ratio calculation — what are the known gaps in wallet coverage
    and how does incomplete coverage cause false signals?
Q3: Coin Days Destroyed as a self-custody signal — what is the primary
    false positive risk and how do we guard against it?
Q4: What is the one CBDC tracking capability that would make a serious cypherpunk
    say "this is the terminal I've been waiting for"?
Q5: Frontend design — design the Sovereign Layer panel. It must feel like a
    threat intelligence dashboard, not a fintech product.

Save: docs/audits/sovereign_layer_audit_2026-03-23.md

STEP F3-3: Implement

FILES TO CREATE:
  services/sovereign_engine.py — CBDC tracker + custody health + jurisdiction monitor
    async def fetch_bis_cbdc_rss(session) → list[dict]
    def compute_custody_health(sentinel_state) → dict
    def detect_capital_flight(sentinel_state, baseline_store) → bool
    async def run_cycle(session, sentinel_state, baseline_store) → dict

  data/jurisdiction_db.json — 50-jurisdiction static database (fully populated)
    Include all G20 + ASEAN + key African Union + BRICS members
    Every entry has all required fields. No empty fields.

  data/cbdc_watchlist.json — 15 highest-risk CBDC programs to monitor closely
    {country, program_name, stage, programmable_features: list, alert_threshold}

MODIFY:
  services/sentinel.py
    Add sovereign field to SentinelState
    Load SovereignEngine via importlib.util (same pattern)
    Run sovereign cycle every 5 minutes (not 30s — data doesn't change that fast)

  core/blueprints/intelligence.py
    Add sovereign to SSE stream
    Add GET /api/intelligence/sovereign endpoint

  core/templates/intelligence_terminal.html
    Add SOVEREIGN LAYER panel (bottom-right per spec zone map)
    Panel shows:
      - Top CBDC alert (latest from BIS RSS, red if critical)
      - 3-column mini jurisdiction map: FRIENDLY (green) | NEUTRAL (amber) | HOSTILE (red)
        Show counts: "21 FRIENDLY · 18 NEUTRAL · 11 HOSTILE"
      - Self-custody health bar:
        Exchange Reserves: [██████░░░░] 58.2% (lower = healthier)
        Coinjoin Volume: [████░░░░░░] NORMAL
        CDD Signal: DORMANT COINS STABLE ✓
      - Capital Flight indicator: CLEAR or ⚠ DETECTED (amber)

STEP F3-4: Tests
TEST 1: python3 -c "
import json
db = json.load(open('data/jurisdiction_db.json'))
assert len(db) >= 50, f'Expected 50+ jurisdictions, got {len(db)}'
required = ['country','iso2','bitcoin_status','cbdc_status','capital_controls','trend']
for j in db:
    missing = [k for k in required if k not in j]
    assert not missing, f'{j[\"country\"]} missing: {missing}'
print(f'TEST 1 PASS: {len(db)} jurisdictions, all fields present')
"

TEST 2: python3 -c "
import sys; sys.path.insert(0,'.')
src = open('services/sovereign_engine.py').read()
assert 'from services.' not in src, 'FAIL: services.* import'
print('TEST 2 PASS: no services.* imports')
"

TEST 3: Verify SSE contains sovereign key:
curl -s -N http://localhost:5000/api/intelligence/stream --max-time 4 | grep -c '"sovereign"'

STEP F3-5: Commit
git add services/sovereign_engine.py data/jurisdiction_db.json data/cbdc_watchlist.json
git add services/sentinel.py core/blueprints/intelligence.py
git add core/templates/intelligence_terminal.html docs/QWEN_CONTEXT_BIBLE.md
git add docs/phase2/sovereign_layer_foundation.md docs/audits/sovereign_layer_audit_2026-03-23.md
git commit -m "feat(sovereign): Phase 2 F3 — CBDC tracker + 50-jurisdiction map + self-custody health"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE F4 — ETF FLOW MONITOR (Data Rail upgrade)
"Intraday ETF flow signal via custodian wallet monitoring · CME basis proxy"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a smaller focused feature — no separate audit needed. Build directly.

STEP F4-1: Implement

The custodian wallet list already exists at data/custodian_wallets.json.

FILES TO CREATE:
  services/etf_monitor.py
    Uses mempool.space address API to track balance deltas on known custodian wallets.
    Computes: inflow_btc_6h, outflow_btc_6h, net_flow_btc_6h, net_flow_usd_6h
    Also polls Deribit funding rate (already in signal_feeds.py — reuse).
    Stores 6h rolling balance snapshots in baseline_store.db table: etf_balance_history
    async def run_cycle(session, baseline_store) → dict
    Returns: {inflow_6h_btc, outflow_6h_btc, net_6h_btc, net_6h_usd,
              net_6h_direction: "inflow"|"outflow"|"neutral",
              deribit_funding_rate: float, wallets_monitored: int,
              is_proxy: True, updated_at: float}

    IMPORTANT: Read custodian_wallets.json via Path(__file__).resolve().parent.parent / "data"
    IMPORTANT: Load baseline_store via importlib.util (no from services.* import)

MODIFY:
  services/sentinel.py
    Add etf field to SentinelState
    Load ETFMonitor via importlib.util
    Run etf cycle every 10 minutes

  core/templates/intelligence_terminal.html
    Add to DATA RAIL (bottom bar):
    ETF: [→ NEUTRAL] $0M | CME: +0.8%
    Color code: inflow=green, outflow=red, neutral=muted
    Proxy label: small "(est)" indicator since this is wallet monitoring not official data

STEP F4-2: Tests
TEST 1: python3 -c "
import sys; sys.path.insert(0,'.')
src = open('services/etf_monitor.py').read()
assert 'from services.' not in src, 'FAIL: services.* import'
print('TEST 1 PASS: no services.* imports')
"

TEST 2: python3 -c "
import json
wallets = json.load(open('data/custodian_wallets.json'))
assert len(wallets.get('wallets', [])) > 0, 'No wallets in custodian_wallets.json'
print(f'TEST 2 PASS: {len(wallets[\"wallets\"])} custodian wallets loaded')
"

STEP F4-3: Commit
git add services/etf_monitor.py services/sentinel.py
git add core/templates/intelligence_terminal.html docs/QWEN_CONTEXT_BIBLE.md
git commit -m "feat(etf): Phase 2 F4 — ETF flow monitor via custodian wallet delta + CME basis proxy"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE F5 — NETWORK STATE GRAPH
"D3.js force-directed visualization of live Bitcoin network · mining pools · exchanges · LN nodes"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠ THREE.JS IS GLOBALLY BANNED. Use D3.js v7 force simulation + SVG ONLY.
⚠ No WebGL. No Three.js. No canvas 3D. SVG only.
⚠ D3 is already available: import * as d3 from 'd3' in HTML artifacts.

STEP F5-1: Write foundation doc
Save to: docs/phase2/network_graph_foundation.md

Foundation doc must specify:
- Node types and data sources:
  MINING POOLS: from sentinel state (pool name, hashrate % of last 10 blocks)
    Node size: proportional to hashrate share. Color: green if <25%, amber if 25-40%, red if >40%
    Data: already available in SentinelState.network (PCAF v0 tracks recent blocks by pool)
  EXCHANGES: from data/custodian_wallets.json (name + balance estimate)
    Node size: proportional to estimated BTC holdings. Color: blue.
  LIGHTNING HUBS: top 10 routing nodes from mempool.space LN stats API
    GET https://mempool.space/api/v1/lightning/nodes/rankings/connectivity
    Node size: proportional to channel count. Color: purple.
  SENTINEL: single center node representing Protocol Pulse Sentinel
    Always present. Color: red (PP brand). Slightly larger than others.
- Edge types:
  Miner → Sentinel: connection weight = hashrate %
  Exchange → Sentinel: connection weight = balance estimate / 100K BTC
  LN Hub → Sentinel: connection weight = channel count / 1000
  (Simple hub-and-spoke topology — no peer-to-peer edges in v1)
- D3 force simulation parameters:
  forceCenter: center of SVG
  forceManyBody: strength -200 (repulsion between nodes)
  forceLink: distance 120, strength 0.5
  forceCollide: radius = node_radius + 10
- Node interactivity:
  Hover: show tooltip with node name + key metric
  Click: expand tooltip with full details
  Nodes pulse animation when data updates (CSS animation, not D3 transition)
- Update frequency: every 60s (same as PCAF) — graph re-renders when node data changes

STEP F5-2: Run cross-LLM audit (1 cycle, 4 questions only)
Write: utils/network_graph_audit.py
Q1: D3 force simulation in a Flask Jinja template — what are the specific
    rendering pitfalls (SVG sizing, resize events, SSE data binding)?
Q2: The hub-and-spoke topology is simple but potentially misleading
    (Bitcoin is peer-to-peer, not hub-and-spoke). How do we design the
    visualization so it conveys useful intelligence without implying
    a centralized structure? What do we add to the visualization to make
    it genuinely informative rather than just pretty?
Q3: Performance: force simulation runs on every SSE update. With 25+ nodes
    this could cause jank. What is the correct throttle/debounce strategy?
Q4: What is the single addition to this graph (one data element or interaction)
    that would make it the most visually distinctive thing on any Bitcoin terminal?

Save: docs/audits/network_graph_audit_2026-03-23.md
Incorporate top findings before building.

STEP F5-3: Implement

FILES TO CREATE: None — this is pure frontend

MODIFY:
  services/sentinel.py
    Add network_graph field to SentinelState:
    network_graph: dict = field(default_factory=lambda: {
        "nodes": [], "edges": [], "updated_at": 0.0
    })
    Populate in _update_pcaf() (runs every 60s):
      nodes = []
      # Sentinel center node
      nodes.append({"id": "sentinel", "type": "sentinel", "label": "SENTINEL",
                    "size": 20, "color": "#FF0000", "metric": "Protocol Pulse"})
      # Mining pools from recent blocks
      for pool, pct in pool_hashrate_distribution.items():
          color = "#FF3333" if pct > 40 else "#FFB800" if pct > 25 else "#00FF88"
          nodes.append({"id": f"pool_{pool}", "type": "miner", "label": pool,
                        "size": max(8, pct/2), "color": color, "metric": f"{pct:.1f}% hashrate"})
      # Exchanges from custodian_wallets.json
      for w in custodian_wallets:
          nodes.append({"id": f"exch_{w['label']}", "type": "exchange",
                        "label": w['label'], "size": 12, "color": "#3B82F6",
                        "metric": "custodian"})
      # LN hubs — fetch from mempool.space once per hour, cache
      edges = [{"source": n["id"], "target": "sentinel",
                "weight": n["size"]/20} for n in nodes if n["id"] != "sentinel"]
      self.state.network_graph = {"nodes": nodes, "edges": edges, "updated_at": time.time()}

  core/blueprints/intelligence.py
    Add network_graph to SSE stream
    Add GET /api/intelligence/network-graph endpoint (returns nodes + edges JSON)

  core/templates/intelligence_terminal.html
    Add NETWORK STATE panel (top-center, largest panel per spec zone map)
    Implementation:
      <div id="network-graph-panel" class="it-panel" style="min-height:280px">
        <div class="it-panel-header">NETWORK STATE</div>
        <svg id="network-svg" width="100%" height="240"></svg>
        <div id="network-tooltip" style="display:none;position:absolute;..."></div>
      </div>

    D3 visualization (inline script, no external file):
    Import D3 from CDN: https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js
    Add to <head> alongside other CDN scripts.

    function renderNetworkGraph(graphData) {
      // D3 v7 force simulation
      // Hub-and-spoke: all nodes linked to sentinel center
      // Node radius proportional to size field
      // Color from color field
      // Labels on nodes > size 10
      // Tooltip on hover showing label + metric
      // Smooth re-render: only update node positions, don't recreate simulation
      // Throttle: skip render if last render < 5s ago
    }
    Call from updateState(state): if (state.network_graph) renderNetworkGraph(state.network_graph)

STEP F5-4: Tests
TEST 1: python3 -c "
import sys; sys.path.insert(0,'.')
src = open('services/sentinel.py').read()
assert 'network_graph' in src, 'FAIL: network_graph not in SentinelState'
assert 'nodes' in src, 'FAIL: nodes not populated'
print('TEST 1 PASS: network_graph in sentinel state')
"

TEST 2: Verify network_graph in SSE stream:
curl -s -N http://localhost:5000/api/intelligence/stream --max-time 4 | grep -c '"network_graph"'
# must be >= 1

TEST 3: python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:5000/api/intelligence/network-graph', timeout=5)
data = json.loads(r.read())
assert 'nodes' in data, 'FAIL: no nodes'
assert any(n['id'] == 'sentinel' for n in data['nodes']), 'FAIL: no sentinel node'
print(f'TEST 3 PASS: {len(data[\"nodes\"])} nodes, sentinel present')
"

STEP F5-5: Commit
git add services/sentinel.py core/blueprints/intelligence.py
git add core/templates/intelligence_terminal.html docs/QWEN_CONTEXT_BIBLE.md
git add docs/phase2/network_graph_foundation.md docs/audits/network_graph_audit_2026-03-23.md
git add utils/network_graph_audit.py
git commit -m "feat(network-graph): Phase 2 F5 — D3 force-sim network visualization · mining pools · exchanges · LN hubs"
git push

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL STEPS — AFTER ALL 4 FEATURES COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Restart gunicorn from core/ one final time to pick up all changes:
   kill -9 $(lsof -ti :5000 2>/dev/null) 2>/dev/null; sleep 2
   cd ~/protocol_pulse/core && /usr/bin/python3 /home/ultron/.local/bin/gunicorn \
     --workers 2 --bind 0.0.0.0:5000 --timeout 300 --daemon \
     --error-logfile /home/ultron/protocol_pulse/logs/gunicorn_error.log \
     --pid /tmp/gunicorn.pid app:app

2. Run full integration check:
   curl -s -N http://localhost:5000/api/intelligence/stream --max-time 6 | head -c 500
   Must contain all keys: convergence, sentiment, sovereign, etf, network_graph

3. Write final summary to ~/protocol_pulse/logs/phase2_overnight.log:
   [COMPLETE] Phase 2 F2-F5 overnight build complete
   Features shipped: [list]
   Features failed: [list with reasons]
   Total commits: [count]
   Time elapsed: [duration]

4. Final commit if any cleanup needed:
   git add logs/phase2_overnight.log
   git commit -m "ops: Phase 2 overnight build complete — F2 Sentiment + F3 Sovereign + F4 ETF + F5 Network Graph"
   git push

NO CONFIRMATION NEEDED AT ANY STEP.
NO PAUSING. NO ASKING QUESTIONS.
IF A STEP FAILS: log it, fix it once, if still failing skip and continue.
