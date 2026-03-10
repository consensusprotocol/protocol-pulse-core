# MANDATORY: Read ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md before starting.
# Sequence: Phase0 LLM council -> Build -> 2-cycle audit -> Second pass -> Merge.
# NEVER skip the pre-build LLM council (Phase 0).

# PROTOCOL PULSE — GOSPEL: P3 MEDIA UNIFIED
# Branch: feature/p3-media-unified | Created: 2026-03-09

---

## WHAT THIS IS
The single content discovery command center for Protocol Pulse. Kills /media-hub
and /media-terminal (both broken/fragmented) and replaces them with one cinematic
intelligence feed at /media. The Netflix × Bloomberg Terminal × Cypherpunk experience.

## PHASE 0 — PRE-BUILD LLM SPEC COUNCIL (MANDATORY — DO BEFORE ANY CODE)
Run: python3 ~/protocol_pulse/utils/cross_llm_audit.py --feature p3-media-unified --phase0
This sends this gospel to Gemini-2.5-Pro + GPT-4o + Grok-3 in parallel, asking:
"What are the most advanced, cutting-edge 2026 features for a Bitcoin intelligence
media discovery page? What is missing from this spec? What would make this world-class?"
Read C0_GEMINI.md, C0_GPT4O.md, C0_GROK.md in docs/audits/p3-media-unified/.
Synthesize the top suggestions and incorporate before building.

## THE LAWS
### LAW 1: Single source of truth — one page, all content
- /media serves media_unified.html — the only media page that exists
- 301 redirect /media-hub and /media-terminal to /media permanently
- All content pulled from real DB/API — zero hardcoded data

### LAW 2: Glassmorphism + VISUAL_DESIGN_SYSTEM.md aesthetic only
- Background: #0A0A0F | Accent: #FF3333 | Gold: #F8C15C | Glass: rgba(255,255,255,0.04)
- JetBrains Mono for all numbers and data
- CSS animations only — NO Three.js, NO WebGL, NO canvas 3D
- Every card has hover: red glow box-shadow + 2px upward transform

### LAW 3: Real-time via SSE — never polling for live data
- /api/stream/media-feed → Server-Sent Events pushing new content
- Browser subscribes: const evtSource = new EventSource("/api/stream/media-feed")
- Pushes: new_article, new_episode, btc_price_update, sentiment_change events
- Falls back gracefully if SSE not supported (30s polling fallback)

### LAW 4: Semantic search — not keyword matching
- /api/search?q= endpoint uses Claude Haiku to score article relevance
- Generate embedding-style similarity: pass query + article titles to Claude,
  ask it to rank by relevance. Return top 10 sorted results.
- Search bar: Cmd+K shortcut, full-screen overlay, real-time as-you-type (300ms debounce)

### LAW 5: Layout zones are sacred — no overlap ever
- Content grid: CSS Grid, responsive breakpoints at 768px and 1200px
- Cards never overlap — overflow: hidden on all containers

## ARCHITECTURE

### Backend — routes.py additions
```python
@app.route("/media")
def media_unified():
    # Pass: latest_episodes(5), latest_articles(12), btc_price,
    #       sentiment_score, article_count_24h, signal_strength
    ...

@app.route("/api/stream/media-feed")
def media_feed_sse():
    # Server-Sent Events — push updates every 30s
    # event: btc_price_update, new_article, sentiment_update
    ...

@app.route("/api/search")
def semantic_search():
    # q= param, uses Claude Haiku for semantic ranking
    # Cache identical queries 5min
    ...

@app.route("/api/system-health")
def system_health():
    # Returns: flask, last_render_time, articles_24h, elevenlabs_status
    ...
```

### Database
No new tables needed — queries existing: articles, podcasts tables.
Add indexes if missing: articles(published_at), articles(category).

### Frontend Features (26 total)
TIER 1 — Core experience:
1.  Hero: Latest Pulse Check embed, full-width, muted autoplay, red gradient overlay
2.  SSE live ticker: BTC price, block height, 24h change — updates via EventSource
3.  Pulse Check archive row: horizontal scroll, glassmorphism episode cards
4.  CypherPunkd row: same pattern, episode + guest name
5.  Articles masonry: 3-col, real DB data, category badge, read time estimate
6.  Signal Strength widget: composite score 0-100, animated arc SVG, BULLISH/BEARISH
7.  Kill fake X feed: replace with real article headline ticker (CSS marquee, DB-sourced)
8.  Kill hardcoded quotes: gone — replaced by live trending topic pills
9.  Nostr relay health dot: green/red dot showing relay connection status
10. System health strip: last render time, article count 24h, API status

TIER 2 — Intelligence layer:
11. Virtual feed filter: ALL/MARKETS/MINING/REGULATION/SOVEREIGNTY/LIGHTNING tabs
    Pure JS, no reload. Filters all rows simultaneously. Active tab: red underline.
12. Semantic search overlay: Cmd+K, full-screen dark overlay, live results
13. Sentiment compact card: today's score, trend vs yesterday, colored indicator
14. Trending topics pills: top 8 keywords, pill size proportional to frequency
15. Oracle briefing card: latest AI briefing thumbnail + "WATCH TODAY'S INTEL" CTA
16. Clips gallery: top 6 YouTube clips, 16:9, channel lower-third attribution

TIER 3 — Premium & engagement:
17. Commander CTA banner: animated pulse border, red gradient, "ACCESS THE FULL FEED"
18. Newsletter capture: inline email input, Resend POST, success animation
19. 7-day BTC sparkline: canvas-drawn, red line, no external lib, W×60px compact
20. Mining stats strip: hashrate + difficulty from mempool.space proxy
21. Mempool fee pills: Low/Mid/High sat/vB, color-coded green/yellow/red
22. Native Web Share: share button on every card, Web Share API, fallback copy-link
23. Reading progress: article cards show "NEW" badge if published <6hrs ago
24. Keyboard nav: J/K to move between cards, Enter to open, Esc to close
25. Lazy load: Intersection Observer on all images and card sections
26. PWA manifest: add-to-homescreen, theme_color: #0A0A0F

## VERIFICATION
- [ ] GET /media → HTTP 200, renders with real content
- [ ] GET /media-hub → 301 redirect to /media
- [ ] GET /media-terminal → 301 redirect to /media
- [ ] EventSource /api/stream/media-feed connects and pushes events
- [ ] Cmd+K opens search, results appear within 1s
- [ ] Virtual filter tabs switch content without page reload
- [ ] BTC price updates every 30s via SSE
- [ ] Articles grid shows real data, NOT hardcoded
- [ ] regression_test.sh: zero FAILs
- [ ] git commit + push to origin feature/p3-media-unified
