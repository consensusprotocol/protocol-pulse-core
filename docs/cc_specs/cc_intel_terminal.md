Read VISUAL_DESIGN_SYSTEM.md and PIPELINE_LAWS.md.
Then read templates/intelligence_terminal.html fully.
Then run utils/cross_llm_audit.py on templates/intelligence_terminal.html with these 8 questions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTELLIGENCE TERMINAL — COMPETITIVE AUDIT + ALPHA EXPANSION
Goal: Transform this from a Bitcoin dashboard into a $5,000/month
intelligence product we give away at $49. Compete with Bloomberg,
Glassnode, CryptoQuant, Santiment. Beat them on Bitcoin-native alpha.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATA WE ALREADY COLLECT (use all of it):
- Real-time BTC price, 24h/7d/30d change
- Mempool fee rates (1-75+ sat/vB) and congestion bands
- Network hashrate (EH/s), difficulty, block height, next adjustment
- Lightning Network capacity and channel count
- Fear & Greed index
- KOL tweet sentiment (kol_pulse_item table, last 24h)
- Published articles (1,300+) with sentiment scores
- Exchange netflow signals (from pipeline)
- Whale transaction alerts
- Miner health scores
- Dark pool signals
- PCAF anomaly score (our own proprietary metric)
- Stage brief data (daily narrative)
- Nostr signal feed
- On-chain accumulation signals

AUDIT QUESTIONS — Each model answers independently, then cross-validates:

1. COMPETITIVE GAP: What do Bloomberg Terminal, Glassnode, CryptoQuant,
   and Santiment charge $500-$2000/month for that we could replicate or
   BEAT with our existing data infrastructure? Be specific — name the
   exact metrics, charts, and signals.

2. CROSS-SIGNAL ALPHA: What are the 5 most powerful COMBINATIONS of our
   existing data streams that would produce genuinely predictive signals?
   For example: hashrate up + exchange outflows up + Fear&Greed < 20 =
   historically precedes supply shock. Give 5 specific, backtestable
   combinations with historical Bitcoin context.

3. PROPRIETARY MOAT: What data does Protocol Pulse collect that NO OTHER
   intelligence platform has access to? How do we productize that uniquely?
   (Think: our KOL sentiment scoring, our PCAF anomaly, our article
   narrative tracking across 1,300+ articles)

4. VISUAL ALPHA: What are the 3 most visually distinctive and information-
   dense displays we could add to the terminal that would make a hedge fund
   analyst say "I've never seen this before"? Think beyond price charts.

5. PREDICTIVE LAYER: Given our data, what early warning indicators exist
   that typically precede major BTC price moves by 24-72 hours? Which of
   these can we calculate from our existing pipeline without new data sources?

6. NARRATIVE INTELLIGENCE: We have 1,300+ articles with sentiment and topic
   data. What narrative pattern analysis could we run across this corpus that
   would produce unique market intelligence? (Topic momentum, sentiment
   divergence from price, narrative lead/lag analysis)

7. ALGORITHMIC EDGE: Which open-source 2024-2026 models from HuggingFace or
   GitHub (TimeMixer, PatchTST, Chronos, TimeGPT, etc) could we deploy on
   our 4x RTX 4090 infrastructure RIGHT NOW to add genuine ML-powered signals
   without disrupting the render pipeline? Give specific model names, GitHub
   repos, and GPU requirements.

8. THE $5000/MONTH FEATURE: What single feature, buildable in one CC session,
   would make a serious Bitcoin investor say "I would pay $5,000/month for
   this"? It must use our existing data. It must be technically feasible.
   It must be genuinely unique.

AFTER AUDIT — BUILD THE HIGHEST CONSENSUS WINS:

Based on what Gemini + GPT-4o + Grok agree on unanimously, implement:

PHASE 1 (build this session):
1. SOVEREIGN SIGNAL MATRIX — radar chart with 6 axes combining our unique
   signals: Miner Health, Exchange Pressure, Narrative Momentum, On-Chain
   Accumulation, Lightning Growth, Social Divergence. Each axis 0-100.
   Color: red=bearish, amber=neutral, green=bullish. This is our PCAF visual.

2. NARRATIVE MOMENTUM TRACKER — scan our last 50 articles for topic clusters.
   Show which narratives are accelerating vs decelerating. If "mining" articles
   spike while price is flat, that's a leading indicator. Real-time.

3. CROSS-SIGNAL DIVERGENCE ALERT — when 3+ of our signals diverge from their
   historical correlation, surface a "DIVERGENCE DETECTED" alert with the
   specific signals and historical context. This is the Bloomberg killer.

4. EARLY WARNING FEED — top 5 current early warning indicators from our data,
   each with confidence score, historical precedent, and 24-72h timeframe.

PHASE 2 (spec for next CC):
- TimeMixer integration for price pattern recognition
- KOL narrative lead/lag analyzer
- Article sentiment vs price divergence tracker

DESIGN: Everything must match intelligence_terminal.html existing style.
Dark glass panels, red/amber/green signal colors, JetBrains Mono data.
No placeholder data — wire real APIs or show loading states.

After building:
git add templates/intelligence_terminal.html core/routes.py
git commit -m "feat(intel): sovereign signal matrix, narrative momentum, cross-signal divergence, early warning"
git push
