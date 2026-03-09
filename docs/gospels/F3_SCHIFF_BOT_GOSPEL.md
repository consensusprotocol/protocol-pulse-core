# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Build -> 2-cycle LLM audit (Gemini+GPT4o+Grok parallel) -> Second pass -> Merge.
# ------------------------------------------------------------

# PROTOCOL PULSE — GOSPEL: F3 SCHIFF-BOT HYPOCRISY METRIC
# Status: GOSPEL. Load into EVERY Claude Code session touching Schiff-Bot.
# Branch: feature/f3-schiff-bot
# Created: 2026-03-09

---

## WHAT THIS FEATURE IS

Peter Schiff is the internet's most consistent Bitcoin critic and gold advocate.
He also manages a bank (Euro Pacific Bank) and publicly traded funds.
The Schiff-Bot tracks the gap between what Schiff says publicly vs. what his
funds actually do — producing a real-time "Hypocrisy Score" (0-100).

This is Protocol Pulse's most viral feature candidate. It doesn't need to be
mean — it just needs to be accurate, data-driven, and perpetually updated.

Target page: /schiff or /brian (Brian = the bot's persona name)

---

## THE LAWS

### LAW 1: Data only from public, verifiable sources
- SEC EDGAR API (free, no API key): https://data.sec.gov
- Only 13F filings (institutional holdings) and public filings
- Never speculate or invent data — only report what EDGAR says
- If EDGAR is down, serve last cached data — never show stale >7 days old

### LAW 2: The Hypocrisy Score formula is fixed
```
HYPOCRISY_SCORE = (
    gold_holding_pct * 0.35 +       # What % of portfolio is gold ETFs/miners
    anti_btc_tweet_rate * 0.30 +    # Public anti-Bitcoin statements (manual seed)
    no_btc_holding_pct * 0.20 +     # 0% BTC in any filing = 20 points
    gold_vs_btc_perf_gap * 0.15     # How much gold underperformed BTC YTD
) → normalized 0-100
```
Do NOT change this formula without PBX approval.
The formula is deliberately simple and explainable.

### LAW 3: Brian is the persona, not Peter
- The bot is named "Brian" — a fictional gold maximalist analyst
- Brian analyzes Peter Schiff's public filings
- This keeps it editorial, not personal attack
- Brian's tone: dry, analytical, slightly amused

### LAW 4: EDGAR API — free, no auth, respect rate limits
- Base URL: https://data.sec.gov
- CIK lookup: https://data.sec.gov/submissions/CIK{10-digit-padded}.json
- Filings: https://data.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F
- Rate limit: max 10 requests/second — implement 200ms delay between calls
- User-Agent header REQUIRED: "Protocol Pulse contact@protocolpulse.io"

### LAW 5: Cache aggressively
- 13F filings update quarterly — cache for 24 hours minimum
- Score recalculates daily at 00:00 UTC
- Never hit EDGAR more than once per hour for same filing

---

## ARCHITECTURE

### File Map
```
~/protocol_pulse/
├── core/
│   ├── services/
│   │   └── schiff_service.py     ← EDGAR fetcher, score calculator
│   └── routes.py                 ← /schiff, /brian routes + API endpoints
├── templates/
│   └── schiff_bot.html           ← Schiff-Bot page
└── cron/
    └── schiff_cron.py            ← daily score update
```

### Score Calculation Pipeline
```
Daily cron → schiff_service.update_score()
  → fetch_13f_holdings(schiff_cik)   ← EDGAR API
  → parse_holdings(filing_xml)
  → calculate_gold_pct(holdings)
  → fetch_btc_vs_gold_ytd()          ← /api/btc-price + gold price API
  → calculate_hypocrisy_score(components)
  → store in schiff_hypocrisy table
  → update cached score JSON
```

### Schiff CIK Research
- Euro Pacific Asset Management: needs EDGAR CIK lookup
- Search: https://www.sec.gov/cgi-bin/browse-edgar?company=euro+pacific&action=getcompany
- Cache the CIK in config — it never changes

---

## DATABASE

```sql
CREATE TABLE IF NOT EXISTS schiff_hypocrisy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score REAL NOT NULL,                    -- 0-100
    gold_holding_pct REAL,
    anti_btc_tweet_rate REAL,
    no_btc_holding_pct REAL,
    gold_vs_btc_perf_gap REAL,
    total_aum_usd REAL,
    btc_holdings_usd REAL DEFAULT 0,
    gold_holdings_usd REAL,
    filing_date DATE,
    filing_type TEXT DEFAULT '13F-HR',
    calculated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_sources TEXT                       -- JSON list of source URLs used
);

CREATE TABLE IF NOT EXISTS schiff_public_statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement TEXT NOT NULL,
    platform TEXT,                          -- 'twitter', 'podcast', 'interview'
    statement_date DATE,
    anti_btc_score INTEGER DEFAULT 1,       -- 1=anti-BTC, 0=neutral
    source_url TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## PAGE SPEC (schiff_bot.html)

### Visual Identity
- Dark terminal aesthetic (matches Oracle/Briefing)
- Header: "BRIAN — HYPOCRISY ANALYST"
- Subheader: "Tracking the gap between what gold bugs say and what the data shows"

### Layout
```
┌─────────────────────────────────────────────┐
│  📊 HYPOCRISY SCORE                         │
│                                              │
│           [SCORE GAUGE: 0-100]              │
│                 87 / 100                    │
│         "Severely Hypocritical"             │
│                                              │
├──────────────────────────────────────────────┤
│  SCORE BREAKDOWN                             │
│  Gold Holdings:    35% → 35pts/35            │
│  Anti-BTC Rate:    High → 28pts/30           │
│  BTC Holdings:     $0  → 20pts/20            │
│  Perf Gap:         BTC+180% vs Gold+8% → 12 │
├──────────────────────────────────────────────┤
│  PORTFOLIO SNAPSHOT (from EDGAR 13F)        │
│  As of: Q4 2025 filing                      │
│  [Holdings table: name, value, % of AUM]    │
├──────────────────────────────────────────────┤
│  RECENT STATEMENTS (seed manually)          │
│  "Bitcoin is not money" — [date] [source]   │
│  [chart: score over time]                   │
└─────────────────────────────────────────────┘
```

### Score Labels
- 0-20: "Principled Consistency"
- 21-40: "Mild Inconsistency"
- 41-60: "Notable Hypocrisy"
- 61-80: "High Hypocrisy"
- 81-100: "Severely Hypocritical"

---

## FLASK ROUTES

```python
@app.route('/schiff')
@app.route('/brian')
def schiff_bot():
    score = schiff_service.get_latest_score()
    history = schiff_service.get_score_history(days=90)
    return render_template('schiff_bot.html', score=score, history=history)

@app.route('/api/schiff/score')
def schiff_score_api():
    return jsonify(schiff_service.get_latest_score())

@app.route('/api/schiff/refresh', methods=['POST'])
@require_admin
def schiff_refresh():
    result = schiff_service.update_score()
    return jsonify(result)
```

---

## SEED DATA (manual statements — add 10+ on first build)

```python
SEED_STATEMENTS = [
    {"statement": "Bitcoin is not money, it's a speculative asset", "date": "2024-01-15", "platform": "twitter"},
    {"statement": "Gold is the only real store of value", "date": "2024-02-20", "platform": "podcast"},
    # ... add more from public record
]
```

---

## VERIFICATION CRITERIA

- [ ] /schiff returns HTTP 200 with score gauge visible
- [ ] EDGAR API call succeeds with User-Agent header
- [ ] Hypocrisy Score is 0-100 and recalculates daily
- [ ] Portfolio table populated from 13F data
- [ ] Score history chart shows 90-day trend
- [ ] `/api/schiff/score` returns JSON with all components
- [ ] regression_test.sh: zero FAILs

---

## CLAUDE CODE PROMPT

```
Read ~/protocol_pulse/docs/gospels/F3_SCHIFF_BOT_GOSPEL.md (THIS FILE).

Branch: feature/f3-schiff-bot (create from main).

BUILD:
1. Look up Euro Pacific Asset Management CIK on EDGAR
2. Create core/services/schiff_service.py (EDGAR fetcher + score calc)
3. Create DB migration for schiff_hypocrisy + schiff_public_statements tables
4. Seed 10 public statements manually
5. Test EDGAR API call with correct User-Agent header
6. Create templates/schiff_bot.html per gospel spec
7. Add /schiff, /brian, /api/schiff/* routes
8. Create cron/schiff_cron.py (daily score update)
9. Verify score calculates to plausible 60-90 range
10. regression_test.sh: zero FAILs
11. git commit + push to feature/f3-schiff-bot
```

---

## LLM TRIFECTA AUDIT NOTES

### Claude Gap Analysis:
- RISK: 13F filings are quarterly — score may be stale between filings
- RISK: Euro Pacific may not have 13F obligations if AUM < $100M
- MISSING: Gold price API (need free source — Metals API, or Yahoo Finance)
- MISSING: Score sharing button (Twitter/Nostr share card with score image)
- VIRAL HOOK: Add "Share this score" button with auto-generated image

### For Gemini: "Is the hypocrisy formula defensible? What are the legal/editorial risks?"
### For Grok: "Verify EDGAR free API rate limits. Does Euro Pacific file 13F? What's their CIK?"
