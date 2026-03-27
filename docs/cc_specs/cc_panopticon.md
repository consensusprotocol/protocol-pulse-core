Read VISUAL_DESIGN_SYSTEM.md and PIPELINE_LAWS.md.

BUILD: The PANOPTICON Dashboard — "They watch us. Now we watch them."

A real-time intelligence dashboard tracking known insider trading patterns,
congressional disclosures, whale wallet movements, and geopolitical financial signals.
Cross-referenced with on-chain Bitcoin data and Polymarket prediction markets.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THREE TIERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIER 1 — CONFIRMED (STOCK Act Disclosures)
Public mandatory filings. 45-day window. 100% legal to display.
Data source: https://efts.house.gov/LATEST/search-index?q=%22bitcoin%22&dateRange=custom
Also: https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure
Parse XML/JSON, filter for: Bitcoin, crypto, ETF, fintech, Coinbase, BlackRock iShares, MicroStrategy
Display: Congressman name, chamber, party, ticker/asset, trade type (buy/sell), amount range, date filed, date traded, days between vote and trade

TIER 2 — FLAGGED (Statistical Correlation)
Trades that statistically correlate with privileged information.
Not accusations — computed patterns. Label as "PATTERN DETECTED."
Logic: if a congress member trades crypto/ETF assets within 30 days of:
  - Committee hearing on digital assets they participated in
  - Legislative vote on crypto regulation
  - Known private briefing (track via hearing schedules: congress.gov/committees)
Then flag as: "Trade within [N] days of [event] — correlation flagged for research"

TIER 3 — WATCH LIST (Publicly Documented Historical Patterns)
People whose trading has been publicly covered by Bloomberg, WSJ, Forbes as suspicious.
Sources: Unusual Whales data, Capitol Trades, public reporting.
Known high-pattern individuals (publicly documented, not our accusation):
- Nancy Pelosi / Paul Pelosi (covered extensively by Bloomberg, WSJ)
- Congress members on House Financial Services Committee
- Senate Banking Committee members
Display: historical trade timeline, asset categories, performance vs S&P 500

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REAL-TIME FEED (keeps dashboard active all day):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

These streams keep PANOPTICON live even when no new insider trades file:

1. WHALE TRACKER — Known public Bitcoin wallets (Saylor/MSTR, ETF custody, exchange cold wallets)
   API: mempool.space/api/address/{address}/txs — free, no auth
   Alert when: whale wallet receives/sends >100 BTC
   Cross-reference with: Polymarket Bitcoin price markets, KOL sentiment

2. DARK MONEY MONITOR — Offshore LLC and shell company patterns
   Source: FARA filings (DOJ), FinCEN suspicious activity (public summaries)
   Cross-reference with legislative activity
   Display as: "Foreign-linked entity active in [sector] — [N] lobbying contacts this month"

3. NATION-STATE SIGNAL — Macro sovereign moves
   Currency interventions: track via forex API (exchangerate.host — free)
   Bond market stress: 10Y Treasury yield, inverted curve alerts
   Sovereign BTC purchases: news scraping + on-chain confirmation
   Display: "Japan intervened in yen — historical BTC correlation: +12% 30d forward"

4. GEOPOLITICAL ALERT FEED — Live
   Source: our existing article/KOL pipeline + GDELT project (free news event database)
   Filter: sanctions, CBDCs, capital controls, Bitcoin bans/adoptions
   Every geopolitical event gets a "Bitcoin Signal" tag: bullish/bearish/neutral
   Rationale displayed: 1-sentence sovereign money case

5. CORRELATION TIMELINE — The unique Protocol Pulse feature
   When ANY of the above fires:
   - Pull the congressional trade history of related legislators
   - Pull Polymarket market on related legislation
   - Pull our KOL sentiment on the same topic
   - Display as a unified timeline: "Senator X sold tech stocks 3 days before bill. Polymarket gave bill 65% passage probability. 3 KOLs mentioned the bill."
   - Add "Make the Bitcoin Case" button: one-click generates a cypherpunk argument for self-custody based on this specific event

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TECHNICAL BUILD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Backend:
- services/panopticon_service.py — data fetcher for all tiers
- Data sources: efts.house.gov (disclosures), mempool.space (whale), exchangerate.host (forex)
- Cron: every 30 minutes for disclosures, every 5 min for whale tracker
- SQLite table: panopticon_events (id, tier, entity, event_type, asset, amount, date, correlation_score, notes)

Frontend: templates/panopticon.html
- Route: /panopticon (Commander tier only, free tier sees teaser with CLASSIFIED overlays)
- Design: dark terminal aesthetic, red/amber/green tier colors
- Hero: "PANOPTICON — They watch us. Now we watch them." with live counter of events today
- Three column layout: CONFIRMED | FLAGGED | FEED
- Live ticker at top: latest whale movement or disclosure
- Correlation Timeline: expandable cards per event
- Each disclosure card: person photo (from congress.gov), trade details, days-to-vote counter, "View Correlation" button

IMPORTANT LEGAL/FRAMING NOTE:
- CONFIRMED tier: raw public data, no editorial
- FLAGGED tier: always labeled "PATTERN FOR RESEARCH — NOT VERIFIED"  
- WATCH LIST: link to original Bloomberg/WSJ sources, we do not make accusations
- Every page: disclaimer "All data from public sources. Correlation shown for research purposes."

Flask route: /panopticon -> render_template('panopticon.html')
API routes:
- /api/panopticon/disclosures -> recent STOCK Act filings filtered for crypto
- /api/panopticon/whale-alerts -> recent large wallet movements
- /api/panopticon/correlations -> cross-reference timeline events
- /api/panopticon/geopolitical -> nation-state and macro signals

After building:
git add -A && git commit -m "feat(panopticon): PANOPTICON intelligence dashboard — congressional disclosures, whale tracking, geopolitical signals, correlation timeline" && git push
