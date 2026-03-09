# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.

# PROTOCOL PULSE — GOSPEL: P3 MINING INTEL
# Branch: feature/p3-mining-intel | Created: 2026-03-09

---

## WHAT THIS IS
Bitcoin mining intelligence vertical. Monitors Blockware Intelligence + other mining
sources via RSS. Auto-generates original Protocol Pulse mining analysis articles.
Hosts a /mining hub page that is THE definitive Bitcoin mining intelligence destination —
live hashrate, ASIC profitability calculator, difficulty tracker, pool concentration,
and Curated Mining CTA (john@curatedmining.com).

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-mining-intel --phase0
Ask all 3 LLMs: "What are the most advanced 2026 Bitcoin mining intelligence features?
What data sources, calculators, and visualizations would make a mining hub page
the go-to resource for serious miners and mining investors?"
Incorporate top P0 ideas before building.

## THE LAWS
### LAW 1: Original articles only — never plagiarize
- Monitor RSS feeds for TOPIC INSPIRATION only
- Never copy or paraphrase source content
- Always write original Protocol Pulse analysis enriched with live on-chain data
- Include: current hashrate, difficulty, BTC price, miner revenue in every article

### LAW 2: mempool.space WebSocket for live hashrate (not polling)
- Connect: wss://mempool.space/api/v1/ws
- Send: {"action": "want", "data": ["stats"]} on connect
- Receive live block data → calculate rolling hashrate
- Fall back to REST if WS fails: GET https://mempool.space/api/v1/mining/hashrate/3d

### LAW 3: ASIC profitability is user-configurable
- Electricity cost: user inputs $/kWh (default 0.06)
- Hash rate: user selects ASIC model OR enters TH/s manually
- Calculate: daily revenue - daily electricity cost = daily profit in USD + BTC
- Show break-even BTC price at given electricity cost

### LAW 4: Never link to Pexels or stock imagery
- All visuals: cyberpunk CSS-drawn charts, SVG diagrams, or real data visualizations
- No stock images on /mining page

## ARCHITECTURE

### RSS Monitor — services/mining_intel_monitor.py
Sources (check every 6hrs via cron):
  - Blockware Intelligence Substack RSS: https://blockwareintelligence.substack.com/feed
  - Hashrate Index: https://hashrateindex.com/blog/rss.xml
  - Bitcoin Magazine mining tag (if RSS available)

For each new item:
1. Store in mining_intel_seen table (URL as unique key — dedup)
2. Extract: title only (NOT full content — respect copyright)
3. Fetch live data: hashrate, difficulty, BTC price, miner revenue
4. Call Claude Sonnet to generate original 800-1200 word article:
   Topic = inspired by RSS title, NOT copied from it
   Enrich with live data. Protocol Pulse cypherpunk voice.
5. Save to articles table: category="mining", source_type="mining_intel"
6. Log to activity_log

Database:
```sql
CREATE TABLE IF NOT EXISTS mining_intel_seen (
  id INTEGER PRIMARY KEY,
  source_url TEXT UNIQUE,
  source_title TEXT,
  source_name TEXT,
  article_id_generated INTEGER,
  processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Cron: 0 */6 * * * source ~/protocol_pulse/.env && python3 -m services.mining_intel_monitor >> logs/mining_intel.log 2>&1

### /mining Hub Page
Template: mining_hub.html
Route: GET /mining

SECTION 1 — LIVE MINING COMMAND CENTER (top, refreshes via WebSocket/SSE):
Hash Rate: EH/s (WebSocket from mempool.space, animated counter)
Difficulty: formatted with epoch progress bar (% through current epoch)
Next Adjustment: days + hours + predicted % change (red=higher, green=lower)
Block Subsidy: 3.125 BTC + USD equivalent
Hash Price: USD per PH/day (miner revenue metric — calculate from coinmetrics-style formula)
Sats per Hash: inverse metric for hardcore miners
Block Height: live, counting up
Mempool: fee rates Low/Mid/High sat/vB

SECTION 2 — ASIC PROFITABILITY CALCULATOR
Interactive calculator widget:
- ASIC Model dropdown: Antminer S21 Pro (234 TH/s, 3500W), Antminer S19 XP (140 TH/s, 3010W),
  Whatsminer M60S (186 TH/s, 3441W), Custom (enter TH/s + watts manually)
- Electricity cost: slider $0.02 - $0.20/kWh
- Pool fee: 0-2%
OUTPUT (updates live as inputs change):
  Daily BTC earned | Daily USD revenue | Daily electricity cost | Daily profit/loss
  Monthly profit/loss | Break-even BTC price | Payback period (months at current price)
All math client-side JS. Uses live BTC price from /api/btc-price proxy.

SECTION 3 — HASHRATE CHART (30-day trend)
Canvas-drawn line chart. Cyan color. EH/s on Y-axis. Data from /api/charts/hashrate-history.
Show: ATH hashrate line (dashed gold), current (cyan), 7-day MA (white dim)

SECTION 4 — MINING POOL DISTRIBUTION
Pie chart: top 10 pools last 7 days (mempool.space /api/v1/mining/pools/1w)
Color-coded. Show HHI (Herfindahl-Hirschman Index) as concentration risk indicator.
If top 3 pools > 51%: red WARNING: "Mining centralization risk"

SECTION 5 — MINING INTEL ARTICLES
Latest 8 articles with category=mining. Same card grid as /articles.
"MORE MINING INTEL →" links to /articles?category=mining

SECTION 6 — EXISTING TOOLS ROW
Link cards to: Mining Risk Calculator, Operator Costs, Solo Slayers, Dossier

SECTION 7 — CURATED MINING CTA
Full-width dark glass panel. Red top border.
"⚡ WHITE-GLOVE BITCOIN MINING SETUP"
"Curated Mining manages your hardware acquisition, hosting, and optimization.
LLC partnership structure. Section 179 tax deduction. Zero hassle."
CTA button: "Contact John" → mailto:john@curatedmining.com
Subtext: "Built for serious capital allocators. Not retail."

## VERIFICATION
- [ ] python3 -m services.mining_intel_monitor runs, writes ≥1 article to DB
- [ ] GET /mining → HTTP 200 with live hashrate data from mempool.space
- [ ] ASIC calculator updates as user changes inputs
- [ ] Pool distribution chart renders real data
- [ ] Mining Intel articles section shows real DB data
- [ ] Curated Mining CTA is prominent, email link works
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-mining-intel
