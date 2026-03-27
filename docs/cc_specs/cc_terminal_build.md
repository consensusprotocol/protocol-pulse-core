Read VISUAL_DESIGN_SYSTEM.md and PIPELINE_LAWS.md.
Then run cross_llm_audit.py audit on templates/signal_terminal.html (or whatever the /signal-terminal template is) with these 8 questions before building anything.

AUDIT QUESTIONS:
1. What data streams does Protocol Pulse uniquely collect that no Bloomberg/WSJ competitor has?
2. What would make a sophisticated Bitcoin investor pay $49/month for this terminal over free alternatives?
3. What real-time signal combinations would create genuine alpha (predictive value)?
4. What open-source 2024-2026 algorithms on GitHub could enhance pattern recognition here?
5. What is the most visually impressive real-time data visualization for Bitcoin intelligence?
6. What would a $500/mo Bloomberg terminal user immediately notice is missing from our current version?
7. How should we present on-chain data, mempool data, and social sentiment together for maximum insight?
8. What is the single most differentiated feature we could build with our existing data infrastructure?

AFTER AUDIT — BUILD THE SIGNAL TERMINAL:

The /signal-terminal page must be THE flagship product. World-class. Here is the spec:

DESIGN: Dark glass morphism, red/black/white Protocol Pulse brand, JetBrains Mono,
animated particle backgrounds, Bloomberg-level data density but more beautiful.

MUST HAVE SECTIONS:
1. TOP BAR: Live BTC price (large, red if down/green if up), 24h change%, mempool fee rate,
   block countdown, timestamp. Updates every 10s.

2. INTELLIGENCE FEED (main left panel): Real-time Oracle signals, curated articles from our DB,
   Satomi AI analysis snippets. Each item has timestamp, source, signal type badge.

3. MARKET INTEL (right panel): 
   - BTC/USD live chart (use lightweight-charts library from CDN)
   - Fear & Greed index with gauge visualization
   - Lightning Network capacity (from /api/charts/price-history or mempool.space)
   - Mining hashrate trend
   - Exchange netflow indicator

4. MEMPOOL HEATMAP: Visual representation of pending transactions by fee rate.
   Color coded: red=high fee, green=low fee. Pulls from /api/charts/mempool-data.

5. SOVEREIGN SIGNAL MATRIX: Our proprietary indicator combining:
   - Price momentum (7d, 30d)
   - On-chain supply shock (exchange outflows)
   - Miner capitulation index
   - Social sentiment score (from our pipeline)
   Display as a radar chart with 6 axes.

6. KOL PULSE: Live curated tweets from top Bitcoin accounts (from kol_pulse_item table).
   Max 24h old. Real-time scroll animation. Clickable links.

7. SATOMI ORACLE EMBED: Small widget at bottom right with "Ask Satomi" button that
   opens the oracle in a modal overlay.

8. PREMIUM GATE: If user is not authenticated or not Commander tier,
   show locked sections with "Unlock Commander Access" CTA.
   Free users see: price ticker + top 3 articles only.
   Commander: everything.

ROUTES: Check routes.py for @app.route('/signal-terminal').
Update it to pass all necessary data:
- btc_price, btc_change_24h
- mempool_data  
- recent_articles (from DB)
- kol_items (from kol_pulse_item, max 24h)
- fear_greed_score
- pipeline_sentiment

After building:
git add templates/signal_terminal.html core/routes.py
git commit -m "feat(terminal): world-class Signal Terminal — Bloomberg-level Bitcoin intelligence dashboard"
git push
